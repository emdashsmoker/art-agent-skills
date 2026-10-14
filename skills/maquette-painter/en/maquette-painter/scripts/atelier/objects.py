"""Objects: still-life pieces and simple props.

Vessels are solids of revolution: a half-profile is mirrored into a silhouette, shaded as a
rounded form, and given an elliptical mouth so the viewing angle reads correctly.
Every object sits on (x, base_y) and lays its shadow flat on the table: the silhouette is sheared
along the light and squashed by the view angle, darkest where the object touches the surface.
Call use_light(light) once per scene so shadows follow the scene light; otherwise light_from is used.
"""
import cv2
import numpy as np

from . import geom
from .core import Gradient, fractal_noise, mix, normals_from_height, to_rgb

VIEW_TILT = 0.24          # how open ellipses look: ry = rx * VIEW_TILT (eye slightly above the table)
RECEIVERS = ("table", "cloth", "plate", "book")       # surfaces a shadow may fall on
SHADOW_STRENGTH = 0.8

PROFILES = {   # (radius, height) pairs from base to mouth, as fractions of the object's width / height
    "vase": [(0.30, 0.0), (0.50, 0.12), (0.50, 0.32), (0.30, 0.62), (0.17, 0.80), (0.24, 1.0)],
    "bottle": [(0.36, 0.0), (0.38, 0.05), (0.38, 0.55), (0.16, 0.72), (0.13, 0.96), (0.16, 1.0)],
    "jug": [(0.34, 0.0), (0.50, 0.18), (0.48, 0.5), (0.30, 0.78), (0.34, 1.0)],
    "bowl": [(0.22, 0.0), (0.40, 0.25), (0.50, 1.0)],
    "cup": [(0.34, 0.0), (0.42, 0.3), (0.50, 1.0)],
    "glass": [(0.30, 0.0), (0.34, 0.1), (0.42, 1.0)],
    "pot": [(0.40, 0.0), (0.50, 0.3), (0.50, 0.8), (0.42, 1.0)],
    "candle": [(0.5, 0.0), (0.5, 1.0)],
}

_scene_light = {"light": None}


def use_light(light):
    """Make every following object lay its shadow according to this scene Light."""
    _scene_light["light"] = light


def _projection(light_from):
    """(shear, squash): screen offset of a shadow point per unit of height above the table."""
    light = _scene_light["light"]
    if light is None:
        lx, ly, lz = (-0.57, -0.67, 0.48) if light_from != "right" else (0.57, -0.67, 0.48)
    else:
        lx, ly, lz = (float(v) for v in light.direction)
    rise = max(-ly, 0.12)                                  # sine of the elevation
    flat = np.hypot(lx, lz) + 1e-6
    length = flat / rise                                   # shadow length per unit height
    return -lx / flat * length, -lz / flat * length * VIEW_TILT


def floor_shadow(canvas, shape, base_y, light_from="left", strength=SHADOW_STRENGTH, contact=None):
    """Lay an object's silhouette flat on the table as its shadow.

    shape    the object's outline (path) or a coverage mask
    contact  (x, half-width) of the footprint: adds the dark contact shadow right under the object
    """
    shear, squash = _projection(light_from)
    mask = canvas.mask(shape) if not isinstance(shape, np.ndarray) else shape
    s = canvas.scale
    base = base_y * s
    # A point h pixels above the base lands shear*h to the side and squash*h further back (up on screen).
    warp = np.float32([[1, -shear, shear * base], [0, squash, base * (1 - squash)]])
    flat = cv2.warpAffine(mask, warp, (canvas.W, canvas.H))
    soft = cv2.GaussianBlur(flat, (0, 0), 3 * s)
    reach = np.clip((base - np.arange(canvas.H, dtype=np.float32)[:, None]) / (abs(squash) * 400 * s + 1), 0, 1)
    shadow = flat * (1 - reach) + soft * reach                     # the penumbra widens away from the object
    receivers = canvas.region_mask(*RECEIVERS).astype(np.float32)
    canvas.shade(shadow * receivers * (1 - mask), strength)
    if contact is not None:
        x, half = contact
        foot = geom.ellipse(x, base_y, half * 1.05, max(half * VIEW_TILT * 1.1, 1.0))
        canvas.occlude(foot, 0.85, blur=half * 0.12, clip=receivers)


def _speckle(canvas, clip, size, density, color, alpha, rng):
    """Small dots (lenticels, pores) inside a shape."""
    ys, xs = np.nonzero(clip > 0.5)
    if len(xs) == 0:
        return
    for _ in range(int(len(xs) * density / max(size * canvas.scale, 1) ** 2)):
        i = rng.integers(len(xs))
        x, y = xs[i] / canvas.scale, ys[i] / canvas.scale
        canvas.tint(geom.ellipse(x, y, size * rng.uniform(0.6, 1.2), size * rng.uniform(0.5, 1.0)), color,
                    alpha=alpha * rng.uniform(0.5, 1.0), clip=clip)


# ---------------------------------------------------------------- vessels
def revolve(canvas, x, base_y, width, height, color, profile="vase", region=None, gloss=0.3, outline=None,
            opening=True, inside=None, light_from="left", cast=True):
    """A turned vessel. profile: key of PROFILES or a list of (radius fraction, height fraction)."""
    prof = PROFILES[profile] if isinstance(profile, str) else profile
    right = [(x + r * width, base_y - h * height) for r, h in prof]
    left = [(2 * x - px, py) for px, py in right][::-1]
    foot_r, mouth_r = prof[0][0] * width, prof[-1][0] * width
    foot = [(x + foot_r * np.cos(a), base_y + foot_r * VIEW_TILT * np.sin(a)) for a in np.linspace(np.pi, 0, 7)[1:-1]]
    body = geom.runs([right, [right[-1], left[0]], left, [left[-1]] + foot + [right[0]]])
    region = region or (profile if isinstance(profile, str) else "vessel")
    if cast:
        floor_shadow(canvas, body, base_y, light_from, contact=(x, foot_r))
    canvas.add(body, color, region, form="round", gloss=gloss, outline=outline)
    if opening:
        top_y = base_y - height
        rim = geom.ellipse(x, top_y, mouth_r, mouth_r * VIEW_TILT)
        dark = to_rgb(color) * 0.4 if inside is None else to_rgb(inside)
        inner = Gradient.linear((x, top_y - mouth_r * VIEW_TILT), (x, top_y + mouth_r * VIEW_TILT),
                                [(0, dark * 0.6), (1, np.clip(dark * 1.5, 0, 1))])
        canvas.add(rim, inner, region, normal=(0, -0.4, 0.9), outline=outline)
        lip = np.clip(to_rgb(color) * 1.35 + 0.08, 0, 1)                   # the rim catches the light
        canvas.ink(rim, lip, stroke=max(width * 0.012, 1.0), alpha=0.8)
    return body


def sphere(canvas, x, base_y, radius, color, region="sphere", gloss=0.3, outline=None, light_from="left", squash=1.0):
    path = geom.ellipse(x, base_y - radius * squash, radius, radius * squash)
    floor_shadow(canvas, path, base_y, light_from, contact=(x, radius * 0.6))
    canvas.add(path, color, region, form="round", gloss=gloss, outline=outline)
    return path


# ---------------------------------------------------------------- fruit
def apple(canvas, x, base_y, size, color="#c8372d", outline=None, light_from="left", leaf=True, seed=0):
    rng = np.random.default_rng(seed)
    r = size / 2
    body = geom.blob([(x, base_y - size * 0.86), (x + r * 0.62, base_y - size * 0.95), (x + r, base_y - size * 0.55),
                      (x + r * 0.7, base_y - size * 0.08), (x, base_y), (x - r * 0.7, base_y - size * 0.08),
                      (x - r, base_y - size * 0.55), (x - r * 0.62, base_y - size * 0.95)])
    floor_shadow(canvas, body, base_y, light_from, contact=(x, r * 0.55))
    base = to_rgb(color)
    canvas.add(body, mix(base, to_rgb("#d8c860"), 0.35), "apple", form="round", gloss=0.45, outline=outline)
    clip = canvas.mask(body)
    # Skin: red streaks running from the stalk over a yellow-green ground, then fine pale dots.
    for _ in range(int(14 + size * 0.1)):
        a = rng.uniform(-1.3, 1.3)
        top = (x + np.sin(a) * r * 0.25, base_y - size * 0.86)
        bottom = (x + np.sin(a) * r * 1.1, base_y - size * rng.uniform(0.05, 0.35))
        canvas.tint(geom.taper([top, ((top[0] + bottom[0]) / 2 + np.sin(a) * r * 0.3, base_y - size * 0.5), bottom],
                               size * rng.uniform(0.08, 0.18)), base * rng.uniform(0.85, 1.1), alpha=0.75, blur=size * 0.02,
                    clip=clip)
    canvas.tint(body, base, alpha=0.45, clip=clip)
    _speckle(canvas, clip, size * 0.008, 0.25, "#f3e0b0", 0.45, rng)
    canvas.shade(geom.ellipse(x, base_y - size * 0.88, r * 0.3, r * 0.12), 0.7, blur=size * 0.03, clip=body)
    canvas.stroke([(x, base_y - size * 0.86), (x + size * 0.04, base_y - size * 1.05), (x + size * 0.11, base_y - size * 1.14)],
                  size * 0.045, "#4a3020", start=0.8, end=0.5)
    if leaf:
        lx, ly = x + size * 0.1, base_y - size * 1.1
        canvas.add(geom.runs([[(lx, ly), (lx + size * 0.2, ly - size * 0.14), (lx + size * 0.38, ly - size * 0.05)],
                              [(lx + size * 0.38, ly - size * 0.05), (lx + size * 0.18, ly + size * 0.05), (lx, ly)]]),
                   "#4f7f3a", "leaf", form="round", outline=outline)
        canvas.stroke([(lx, ly), (lx + size * 0.2, ly - size * 0.05), (lx + size * 0.36, ly - size * 0.05)], size * 0.008,
                      "#3a5f2a", alpha=0.7)
    return body


def pear(canvas, x, base_y, size, color="#c9c24a", outline=None, light_from="left", seed=0):
    rng = np.random.default_rng(seed + 11)
    w = size * 0.4
    body = geom.blob([(x, base_y - size), (x + w * 0.45, base_y - size * 0.82), (x + w * 0.62, base_y - size * 0.58),
                      (x + w, base_y - size * 0.28), (x + w * 0.7, base_y - size * 0.03), (x, base_y),
                      (x - w * 0.7, base_y - size * 0.03), (x - w, base_y - size * 0.28), (x - w * 0.62, base_y - size * 0.58),
                      (x - w * 0.45, base_y - size * 0.82)])
    floor_shadow(canvas, body, base_y, light_from, contact=(x, w * 0.6))
    canvas.add(body, color, "pear", form="round", gloss=0.25, outline=outline)
    clip = canvas.mask(body)
    side = -1 if light_from != "right" else 1
    canvas.tint(geom.ellipse(x + side * w * 0.45, base_y - size * 0.35, w * 0.5, size * 0.25), "#d0743a", alpha=0.35,
                blur=size * 0.08, clip=clip)                                      # blush where the sun ripened it
    _speckle(canvas, clip, size * 0.006, 0.2, "#7a5a2a", 0.3, rng)
    canvas.stroke([(x, base_y - size * 0.99), (x + size * 0.03, base_y - size * 1.12)], size * 0.035, "#4a3020", start=0.8, end=0.5)
    return body


def citrus(canvas, x, base_y, size, color="#e8a02a", outline=None, light_from="left", lemon=False, seed=0):
    rng = np.random.default_rng(seed + 23)
    r = size / 2
    if lemon:
        body = geom.blob([(x - r * 1.25, base_y - r * 0.8), (x - r * 0.7, base_y - r * 1.5), (x + r * 0.7, base_y - r * 1.5),
                          (x + r * 1.3, base_y - r * 0.85), (x + r * 0.7, base_y - r * 0.05), (x - r * 0.7, base_y - r * 0.05)])
    else:
        body = geom.ellipse(x, base_y - r * 0.97, r, r * 0.97)
    floor_shadow(canvas, body, base_y, light_from, contact=(x, r * 0.7))
    canvas.add(body, color, "citrus", form="round", gloss=0.3, outline=outline)
    clip = canvas.mask(body)
    noise = fractal_noise(canvas.H, canvas.W, size * 0.025 * canvas.scale, 2, rng)
    bump = normals_from_height(noise * size * 0.012 * canvas.scale, 1.0)           # the dimpled peel
    inside = clip > 0.5
    canvas.normal[..., 0][inside] += bump[..., 0][inside] * 0.5
    canvas.normal[..., 1][inside] += bump[..., 1][inside] * 0.5
    return body


def grapes(canvas, x, base_y, size, color="#5a3a7a", outline=None, light_from="left", seed=0):
    """A bunch built berry by berry, back to front, each with the pale bloom of real grapes."""
    rng = np.random.default_rng(seed)
    r = size * 0.11
    berries = []
    for row in range(5):
        count = [3, 4, 4, 3, 2][row]
        for i in range(count):
            berries.append((x + (i - (count - 1) / 2) * r * 1.7 + rng.normal(0, r * 0.2),
                            base_y - size * 0.72 + row * r * 1.5 + rng.normal(0, r * 0.15)))     # lowest berries rest on the surface
    outline_all = geom.union(*[geom.ellipse(bx, by, r, r * 0.96) for bx, by in berries])
    floor_shadow(canvas, outline_all, base_y, light_from, contact=(x, size * 0.2))
    canvas.stroke([(x, base_y - size * 0.86), (x + size * 0.03, base_y - size * 1.0)], size * 0.03, "#5a4028", start=0.8)
    bloom = mix(to_rgb(color), to_rgb("#c9c4d8"), 0.55)
    for bx, by in berries:
        tone = np.clip(to_rgb(color) * rng.uniform(0.85, 1.15), 0, 1)
        berry = geom.ellipse(bx, by, r, r * 0.96)
        canvas.add(berry, tone, "grape", form="round", gloss=0.5, outline=outline)
        canvas.tint(geom.ellipse(bx + r * 0.25, by + r * 0.2, r * 0.8, r * 0.7), bloom, alpha=0.3, blur=r * 0.3,
                    clip=canvas.mask(berry))
    canvas.occlude(geom.ellipse(x, base_y - size * 0.25, size * 0.3, size * 0.3), 0.35, blur=size * 0.1,
                   clip=canvas.mask(outline_all))


def plate(canvas, x, base_y, width, color="#f1eee6", outline=None, light_from="left"):
    ry = width / 2 * VIEW_TILT
    rim = geom.ellipse(x, base_y - ry * 0.35, width / 2, ry)
    floor_shadow(canvas, rim, base_y, light_from, strength=0.5, contact=(x, width * 0.4))
    canvas.add(rim, color, "plate", normal=(0, -0.55, 0.83), outline=outline, gloss=0.25)
    canvas.add(geom.ellipse(x, base_y - ry * 0.3, width * 0.36, ry * 0.7), np.clip(to_rgb(color) * 0.93, 0, 1), "plate",
               normal=(0, -0.75, 0.66))
    canvas.ink(geom.ellipse(x, base_y - ry * 0.3, width * 0.36, ry * 0.7), np.clip(to_rgb(color) * 0.8, 0, 1),
               stroke=max(width * 0.004, 0.8), alpha=0.6)


def book(canvas, x, base_y, width, thickness, depth, cover="#7a2f2f", pages="#efe6d0", outline=None, skew=0.35):
    """A closed book lying flat, drawn as an oblique box (skew shifts the far edge sideways)."""
    dx, dy = depth * skew, depth * VIEW_TILT * 1.6
    top = geom.polygon([(x, base_y - thickness), (x + width, base_y - thickness),
                        (x + width + dx, base_y - thickness - dy), (x + dx, base_y - thickness - dy)])
    front = geom.rect(x, base_y - thickness, x + width, base_y)
    side = geom.polygon([(x + width, base_y - thickness), (x + width + dx, base_y - thickness - dy),
                         (x + width + dx, base_y - dy), (x + width, base_y)])
    floor_shadow(canvas, geom.union(top, front, side), base_y, contact=(x + width / 2, width * 0.5))
    canvas.add(side, cover, "book", normal=(0.8, 0, 0.6), outline=outline)
    canvas.add(front, pages, "book", normal=(0, 0, 1), outline=outline)
    for k in range(1, 6):                                           # page edges
        y = base_y - thickness * k / 6
        canvas.stroke([(x + width * 0.04, y), (x + width, y)], max(thickness * 0.02, 0.6), to_rgb(pages) * 0.82, alpha=0.6)
    canvas.add(geom.rect(x, base_y - thickness, x + width * 0.04, base_y), cover, "book", normal=(0, 0, 1))
    canvas.add(top, cover, "book", normal=(0, -0.85, 0.5), outline=outline)


# ---------------------------------------------------------------- setting
def table(canvas, y, color="#8a5f3c", far_color=None, depth=0.5, edge=None, grain=0.5, seed=0, clip=None):
    """Table top filling the canvas below y, with wood grain running across; edge = front edge band thickness.

    clip  limits the table to a mask: laid after a sitter with her arms masked out, her forearms rest on it.
    """
    rng = np.random.default_rng(seed)
    s = canvas.scale
    with canvas.layer(depth=depth):
        top_h = canvas.H - int(y * s)
        if top_h <= 0:
            return
        base = to_rgb(color)
        far = to_rgb(far_color) if far_color is not None else base * 1.12
        ramp = np.linspace(0, 1, top_h, dtype=np.float32)[:, None, None]
        rgb = np.zeros((canvas.H, canvas.W, 3), np.float32)
        rgb[canvas.H - top_h:] = far * (1 - ramp) + base * ramp
        if grain:           # long streaks along the boards, finer toward the back
            small = rng.standard_normal((max(top_h // int(3 * s + 1), 2), max(canvas.W // int(120 * s + 1), 2))).astype(np.float32)
            streak = cv2.resize(small, (canvas.W, top_h), interpolation=cv2.INTER_CUBIC)
            rgb[canvas.H - top_h:] *= (1 + 0.07 * grain * np.clip(streak, -2, 2))[..., None]
        mask = np.zeros((canvas.H, canvas.W), np.float32)
        mask[canvas.H - top_h:] = 1.0
        if clip is not None:
            mask = mask * canvas.mask(clip)
        canvas.add(mask, np.clip(rgb, 0, 1), "table", normal=(0, -0.8, 0.6), gloss=0.15)
        canvas.occlude(geom.rect(0, y, canvas.width, y + 3), 0.6, blur=2.0, clip=clip)     # where table meets the wall
        if edge:
            canvas.add(geom.rect(0, canvas.height - edge, canvas.width, canvas.height), base * 0.7, "table", normal=(0, 0, 1))
            canvas.add(geom.rect(0, canvas.height - edge, canvas.width, canvas.height - edge + max(edge * 0.06, 1)),
                       np.clip(base * 1.3, 0, 1), "table", normal=(0, -0.7, 0.7))


def backdrop(canvas, top="#5c6470", bottom="#8a8f92", y=None, depth=0.9, glow=None, glow_color=None):
    """Plain graded wall behind a still life or portrait. glow=(x, y, radius) brightens the wall where the light falls."""
    y = canvas.height if y is None else y
    with canvas.layer(depth=depth):
        canvas.add(geom.rect(0, 0, canvas.width, y), Gradient.linear((0, 0), (0, y), [top, bottom]), "wall", unlit=True)
    if glow:
        gx, gy, radius = glow
        tone = glow_color or np.clip(to_rgb(bottom) * 1.35, 0, 1)
        canvas.tint(geom.ellipse(gx, gy, radius, radius * 0.8), tone, alpha=0.55, blur=radius * 0.5)


def cloth(canvas, points, color="#b8433a", depth=0.45, folds=1.0, seed=0, outline=None, region="cloth", flow=80.0):
    """A draped cloth: long folds running in direction `flow` (degrees, 90 = hanging down), soft between them."""
    rng = np.random.default_rng(seed)
    path = geom.blob(points) if len(points) > 4 else geom.polygon(points)
    s = canvas.scale
    size = int(np.hypot(canvas.W, canvas.H)) + 4
    # Folds: noise that changes quickly across the flow and slowly along it, rotated to the flow.
    across = rng.standard_normal((max(size // int(160 * s), 3), max(size // int(28 * s), 3))).astype(np.float32)
    field = cv2.GaussianBlur(cv2.resize(across, (size, size), interpolation=cv2.INTER_CUBIC), (0, 0), 4 * s)
    turn = cv2.getRotationMatrix2D((size / 2, size / 2), flow - 90, 1.0)
    field = cv2.warpAffine(field, turn, (size, size), borderMode=cv2.BORDER_REFLECT)
    oy, ox = (size - canvas.H) // 2, (size - canvas.W) // 2
    ridges = field[oy:oy + canvas.H, ox:ox + canvas.W]
    ridges = np.sign(ridges) * np.abs(ridges) ** 0.7                 # sharper crests, broad troughs
    ridges += (fractal_noise(canvas.H, canvas.W, 90 * s, 2, rng) - 0.5) * 0.8
    normal = normals_from_height(cv2.GaussianBlur(ridges, (0, 0), 1.5 * s) * 10 * s * folds, 1.0)
    with canvas.layer(depth=depth):
        canvas.add(canvas.mask(path), color, region, normal=normal, outline=None, soft=0.3)
        valley = np.clip(cv2.GaussianBlur(ridges, (0, 0), 8 * s) - ridges, 0, None)
        canvas.occlude(np.clip(valley * 0.6 * folds, 0, 0.6) * canvas.mask(path))
        if outline:
            canvas.ink(path, stroke=outline)
    return path


def flower(canvas, x, y, size, petal="#e8b7c8", centre="#e6b53a", petals=6, outline=None, seed=0, tilt=0.35, turn=0.0):
    """An open blossom. tilt 0 faces the viewer, 1 is seen edge-on; turn rotates the head (degrees).

    Petals are cupped ovals that narrow at the base, slightly different in size and angle, laid on a
    tilted disc so the far petals foreshorten.
    """
    rng = np.random.default_rng(seed)
    squash = 1 - 0.75 * tilt
    tone = to_rgb(petal)
    order = []
    for i in range(petals * 2 if petals < 8 else petals):
        layer = 0 if i < petals else 1
        angle = 2 * np.pi * (i % petals) / petals + rng.normal(0, 0.12) + layer * np.pi / petals
        order.append((np.sin(angle), angle, layer))
    order.sort()                              # far petals (top of the tilted disc) first
    for depth_key, angle, layer in order:
        length = size * (0.56 if layer == 0 else 0.4) * rng.uniform(0.85, 1.1)
        width = length * rng.uniform(0.38, 0.5)
        pts = []
        for t in np.linspace(0, 2 * np.pi, 16, endpoint=False):
            along = (1 - np.cos(t)) / 2 * length
            side = np.sin(t) * width * np.sqrt(np.clip(along / length, 0, 1)) * (1.15 - 0.4 * along / length)
            px = np.cos(angle) * along - np.sin(angle) * side
            py = (np.sin(angle) * along + np.cos(angle) * side) * squash
            c, s_ = np.cos(np.radians(turn)), np.sin(np.radians(turn))
            pts.append((x + px * c - py * s_, y + px * s_ + py * c))
        shade = 0.92 + 0.12 * layer - 0.08 * depth_key
        canvas.add(geom.blob(pts), np.clip(tone * shade, 0, 1), "petal", form="round", bulge=width * 0.5, outline=outline)
        tip = (x + np.cos(angle) * length * 0.75, y + np.sin(angle) * length * 0.75 * squash)
        canvas.stroke([(x, y), tip], max(size * 0.006, 0.6), tone * 0.8, start=0.8, end=0.8, alpha=0.35)
    core = geom.ellipse(x, y, size * 0.12, size * 0.12 * squash)
    canvas.add(core, centre, "petal", form="round", outline=outline)
    for _ in range(10):                                                   # stamens
        a, d = rng.uniform(0, 2 * np.pi), rng.uniform(0, 0.1) * size
        canvas.accent(geom.ellipse(x + np.cos(a) * d, y + np.sin(a) * d * squash, size * 0.014), np.clip(to_rgb(centre) * 0.6, 0, 1),
                      alpha=0.8)


def stem(canvas, start, end, color="#4f7a3a", width=4.0, bend=0.15, leaves=1, outline=None):
    """A curved stem from start up to end, with optional leaves."""
    sx, sy = start
    ex, ey = end
    mid = ((sx + ex) / 2 + (ey - sy) * bend, (sy + ey) / 2)
    canvas.add(geom.taper([start, mid, end], width, start=1.0, end=0.6), color, "stem", outline=outline)
    for i in range(leaves):
        t = 0.35 + 0.3 * i
        lx, ly = sx + (ex - sx) * t + (ey - sy) * bend * 0.8, sy + (ey - sy) * t
        side = 1 if i % 2 == 0 else -1
        size = abs(ey - sy) * 0.22
        canvas.add(geom.runs([[(lx, ly), (lx + side * size * 0.6, ly - size * 0.45), (lx + side * size, ly - size * 0.3)],
                              [(lx + side * size, ly - size * 0.3), (lx + side * size * 0.5, ly + size * 0.05), (lx, ly)]]),
                   color, "leaf", form="round", outline=outline)


# ---------------------------------------------------------------- light sources
def flame(canvas, x, y, size, color="#ffb347", halo=1.0):
    """A candle flame standing on (x, y), `size` tall: a white-hot core in a yellow teardrop with an orange edge,
    a blue foot, and a soft halo of light around it. It is unlit (it is the light), so it stays bright in any key.
    """
    w = size * 0.32
    tear = geom.blob([(x, y - size), (x + w * 0.55, y - size * 0.55), (x + w, y - size * 0.22), (x + w * 0.6, y),
                      (x, y + size * 0.06), (x - w * 0.6, y), (x - w, y - size * 0.22), (x - w * 0.55, y - size * 0.55)])
    body = Gradient.radial((x, y - size * 0.25), size * 0.75, [(0.0, "#fffdf4"), (0.35, "#ffe9a8"), (0.7, color),
                                                                 (1.0, mix(to_rgb(color), to_rgb("#c8401c"), 0.6))])
    with canvas.layer(depth=0.0):
        canvas.add(tear, body, "flame", unlit=True)
        canvas.add(geom.ellipse(x, y - size * 0.04, w * 0.28, size * 0.07), "#7f9ae0", "flame", unlit=True, alpha=0.45)
    if halo:
        canvas.accent(geom.ellipse(x, y - size * 0.4, size * 1.1), "#ffe2a6", alpha=0.35 * halo, blur=size * 0.45)
        canvas.accent(geom.ellipse(x, y - size * 0.4, size * 3.2), color, alpha=0.18 * halo, blur=size * 1.4)
    return tear


def candle(canvas, x, base_y, width, height, color="#efe4cc", lit=True, holder="#b08a4a", outline=None, seed=0):
    """A wax candle on a brass dish. The wax top holds a pale melt pool, a few drips run down the side and
    a dark wick carries the flame. Returns the flame's (x, y) foot so the scene light can be placed there.
    """
    rng = np.random.default_rng(seed)
    if holder:
        dish = [(0.95, 0.0), (1.0, 0.06), (0.62, 0.12), (0.4, 0.2), (0.36, 0.34)]
        revolve(canvas, x, base_y, width * 1.15, width * 0.42, holder, dish, region="holder", gloss=0.55,
                outline=outline, inside=np.clip(to_rgb(holder) * 0.7, 0, 1), cast=not lit)
        base_y = base_y - width * 0.42 * 0.3
    body = revolve(canvas, x, base_y, width, height, color, "candle", region="candle", gloss=0.12, outline=outline,
                   inside=np.clip(to_rgb(color) * 1.08 + 0.04, 0, 1), cast=not lit)
    top = base_y - height
    wax = np.clip(to_rgb(color) * 1.06 + 0.03, 0, 1)
    for _ in range(3):                                  # drips that ran over the rim and set
        dx = width * rng.uniform(-0.38, 0.38)
        run = height * rng.uniform(0.08, 0.3)
        canvas.add(geom.taper([(x + dx, top), (x + dx + width * 0.02, top + run)], width * rng.uniform(0.05, 0.08),
                              start=1.0, end=0.8), wax, "candle", form="round", keep_normal=0.6, clip=body)
    wick_top = (x + width * 0.03, top - width * 0.22)
    canvas.add(geom.taper([(x, top + width * 0.02), wick_top], max(width * 0.035, 0.8), start=1.0, end=0.6),
               "#2a1d16", "wick", form="round")
    if lit:
        flame(canvas, wick_top[0], wick_top[1] + width * 0.04, width * 1.3)
    return wick_top
