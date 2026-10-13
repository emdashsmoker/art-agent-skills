"""Lighting: geometry buffers + palette -> albedo, tone and a lit reference image.

The lit reference is never shown directly. Each medium reinterprets it
(tone bands for cel, washes for watercolor, stroke colours for oil).
"""
import numpy as np
import cv2

from .materials import gloss_of


DEFAULT_ALBEDO = (0.7, 0.7, 0.7)
SHADOW_SOFTEN_PX = 2.2       # at output resolution; hides shadow-map stair steps
AO_RADIUS_PX = 14
AO_STRENGTH = 0.55
AO_GROUND_GAP_M = 0.10         # deepest crease the floor, walls and terrain may show
AO_SMALL_SIGMA = 4.0          # blur width (px) on the reduced copy used for occlusion
SPECULAR_FLATTEN = 0.45


def _normalize(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def material_mask(g, name):
    """Pixels of one material (False everywhere if the material is not in view)."""
    if name not in g["materials"]:
        return np.zeros(g["mask"].shape, bool)
    return g["material"] == g["materials"].index(name)


def albedo_map(g, palette, painters=()):
    """Base colour per pixel: flat palette colours, then procedural painters (face paint, textures).

    Also fills g["gloss"] and g["shine"] (surface finish per pixel), which painters may refine.
    Returns (albedo, glow) where glow is (rgb, alpha) for marks that ignore shading, e.g. eye catchlights.
    """
    key = ("albedo", id(palette), tuple(id(p) for p in painters))
    if g.get("_albedo_key") == key:
        return g["_albedo"]
    out = np.ones(g["mask"].shape + (3,), np.float32)
    g["gloss"] = np.zeros(g["mask"].shape, np.float32)
    g["shine"] = np.ones(g["mask"].shape, np.float32)
    for index, name in enumerate(g["materials"]):
        sel = g["material"] == index
        out[sel] = palette.get(name, DEFAULT_ALBEDO)
        g["gloss"][sel], g["shine"][sel] = gloss_of(name)
    glow_rgb = np.ones_like(out)
    glow_alpha = np.zeros(g["mask"].shape, np.float32)
    for painter in painters:
        painter(g, out, glow_rgb, glow_alpha)
    if "bump" in g:            # painters may leave a height field: it tilts the normals before any lighting
        apply_bump(g, g.pop("bump"))
    g["_albedo_key"], g["_albedo"] = key, (out, (glow_rgb, glow_alpha))
    return g["_albedo"]


def apply_bump(g, height):
    """Tilt g["normal"] by a height field (metres, + = outward) painted on the surfaces.

    Screen-space surface gradient (Mikkelsen 2010): works on any surface without UVs or tangents,
    so muscle relief and other fine form read correctly under every light and in every style."""
    n, p = g["normal"], g["position"]
    dpdx, dpdy = np.gradient(p, axis=1), np.gradient(p, axis=0)
    dhdx, dhdy = np.gradient(height, axis=1), np.gradient(height, axis=0)
    # no gradient across object borders: the step from one surface to another is not relief
    part = g["part"]
    same = (np.roll(part, 1, 1) == part) & (np.roll(part, -1, 1) == part) & \
        (np.roll(part, 1, 0) == part) & (np.roll(part, -1, 0) == part) & g["mask"]
    dhdx, dhdy = dhdx * same, dhdy * same
    r1, r2 = np.cross(dpdy, n), np.cross(n, dpdx)
    det = np.sum(dpdx * r1, -1)
    grad = np.sign(det)[..., None] * (dhdx[..., None] * r1 + dhdy[..., None] * r2)
    bumped = np.abs(det)[..., None] * n - grad
    length = np.linalg.norm(bumped, axis=-1, keepdims=True)
    ok = (length[..., 0] > 1e-12) & same
    g["normal"] = np.where(ok[..., None], bumped / np.maximum(length, 1e-12), n).astype(n.dtype)


def add_glow(color, glow):
    rgb, alpha = glow
    return color * (1 - alpha[..., None]) + rgb * alpha[..., None]


def ambient_occlusion(g):
    """Cheap screen-space occlusion: pixels deeper than their neighbourhood get darker (creases, armpits).

    g["ao_group"] (optional, per pixel) splits the picture into occlusion groups: one per person, one per
    object, one for the floor, walls and terrain. A group only darkens itself; the others count as open
    space. Screen-space occlusion cannot tell a wall a metre behind a sofa from a crease, so without groups
    every figure and object leaves a dark rim on whatever lies behind it.
    """
    depth = np.where(g["mask"], g["depth"], np.nan)
    fill = np.nanmax(depth) if np.isfinite(depth).any() else 1.0
    d = np.where(np.isnan(depth), fill, depth).astype(np.float32)
    radius = AO_RADIUS_PX * g["supersample"]
    groups = g.get("ao_group")
    grouped = groups is not None
    if not grouped:
        groups = np.zeros(d.shape, np.int32)
    # the blur is wide and smooth, so it is taken on a reduced copy: one blur per group stays cheap
    factor = max(1, int(radius / AO_SMALL_SIGMA))
    h, w = d.shape
    small = (max(1, w // factor), max(1, h // factor))
    blurred = np.empty_like(d)
    for group in np.unique(groups):
        inside = groups == group
        reduced = cv2.resize(np.where(inside, d, fill), small, interpolation=cv2.INTER_AREA)
        sigma = radius / factor
        if grouped and group == 0:
            # floor, walls and terrain: a hill crest or a shoreline stands metres in front of the land beyond it.
            # Count no surface as more than AO_GROUND_GAP_M in front of the deepest one around it, over the
            # whole reach of the blur, so the land behind a crest gets no dark band (room corners keep theirs).
            window = 2 * int(np.ceil(4 * sigma)) + 3
            deepest = cv2.dilate(reduced, np.ones((window, window), np.uint8))
            reduced = np.maximum(reduced, deepest - AO_GROUND_GAP_M)
        field = cv2.resize(cv2.GaussianBlur(reduced, (0, 0), sigma), (w, h), interpolation=cv2.INTER_LINEAR)
        blurred[inside] = field[inside]
    # positive where the pixel sits behind the local average surface
    occlusion = np.clip((d - blurred) / 0.06, 0, 1)
    return 1.0 - AO_STRENGTH * occlusion * g["mask"]


def specular(g, soft_shadow):
    """Highlight strength per pixel from the surface finish (call after albedo_map has filled g['gloss'])."""
    if "gloss" not in g:
        return np.zeros(g["mask"].shape, np.float32)
    to_key = -_normalize(g["light_dir"])
    half = to_key[None, None] - g["view"]
    # flatten the half-vector: upright forms (bottles, limbs, vases) then catch the streak of light
    # a painter would give them, even under a high key light
    half = half * np.array([1.0, 1.0, SPECULAR_FLATTEN], np.float32)
    half = half / np.maximum(np.linalg.norm(half, axis=-1, keepdims=True), 1e-9)
    n_dot_h = np.clip(np.sum(g["normal"] * half, -1), 0, 1)
    facing = np.clip(g["normal"] @ to_key, 0, 1) > 0
    # broad sheen plus a small core, so glossy things get a readable hot spot
    lobe = n_dot_h ** g["shine"] + 0.6 * n_dot_h ** (g["shine"] * 6.0)
    return (g["gloss"] * lobe * facing * (0.25 + 0.75 * soft_shadow) * g["mask"]).astype(np.float32)


def lighting(g, key_dir=None, key_strength=1.0, ambient=0.35, rim=0.0, wrap=0.15):
    """Return (tone 0..1, lit_fraction 0..1). tone drives banding; lit_fraction is the soft shadow mask."""
    to_key = -_normalize(key_dir if key_dir is not None else g["light_dir"])
    n = g["normal"]
    n_dot_l = n @ to_key
    # wrap lighting keeps form readable in the shadow side (skin never goes to a hard 0)
    diffuse = np.clip((n_dot_l + wrap) / (1 + wrap), 0, 1)
    sigma = SHADOW_SOFTEN_PX * g["supersample"]
    soft_shadow = cv2.GaussianBlur(g["shadow"], (0, 0), sigma)
    lit = diffuse * soft_shadow
    sky = 0.5 + 0.5 * n[..., 2]                       # hemisphere ambient: more light from above
    ao = ambient_occlusion(g)
    tone = key_strength * lit + ambient * (0.6 + 0.4 * sky) * ao
    if rim:
        fresnel = 1.0 - np.clip(-np.sum(n * g["view"], axis=-1), 0, 1)
        tone = tone + rim * fresnel ** 3 * soft_shadow
    g["_soft_shadow"] = soft_shadow
    return np.clip(tone, 0, 1.5).astype(np.float32), lit.astype(np.float32)


def downsample(image, g):
    """Supersampled buffer -> output resolution (area filter = antialiasing)."""
    s = g["supersample"]
    if s == 1:
        return image
    h, w = image.shape[:2]
    return cv2.resize(image.astype(np.float32), (w // s, h // s), interpolation=cv2.INTER_AREA)
