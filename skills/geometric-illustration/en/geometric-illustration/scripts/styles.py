"""Style renderers: turn resolved layers into a finished picture.

Why: the same line, flat, shadow and highlight layers become anime cel, soft
illustration, oil or watercolor by changing only how the layers are combined.
That mirrors a digital painter's layer stack (multiply shadows, screen
highlights, line on top) and keeps the rig style-agnostic.
"""
import cv2
import numpy as np

import raster
from raster import blur, hex_rgb, mix

NO_SHADE_GROUPS = ('bg', 'lash', 'brow', 'sky', 'emissive', 'scenery', 'screen')   # designed or self-lit colors
BACKDROP_GROUPS = ('bg', 'sky')
CEL_EDGE = 0.012          # anti-aliased width of a cel shadow boundary (in lambert units)
SHAPE_EDGE = 0.10         # same for designed shadow shapes (their values are blurred coverage)
BODY_SHAPE_EDGE = 0.05    # mannequin bodies: crisper self-shadow edges (their coverage is blurred more)
SIMPLIFY_GROUPS = ('body',)       # mannequin bodies only; faces keep their small designed shadows
SHADOW_SIMPLIFY = 0.035   # head widths: lit slivers narrower than twice this inside body shadows are filled
SHADOW_HOLE_AREA = 0.05   # head widths squared: smaller enclosed lit islands on the body join the shadow
LIT_CORE = 0.6            # shadow amount below which a pixel counts as the lit core of an island
ISLAND_HALO = 0.02        # head widths: soft rim around a filled island that is filled with it


def backdrop(layers):
    """Coverage of the backdrop (portrait background or scene sky): painted loosely, framed by margins."""
    out = np.zeros(layers.flat.shape[:2], np.float32)
    for g in BACKDROP_GROUPS:
        if g in layers.groups:
            out = np.maximum(out, layers.groups[g])
    return out


def light_vector(spec):
    v = np.asarray(spec['light']['direction'], np.float32)
    return v / np.linalg.norm(v)


def lambert(layers, light):
    """Raw N.L in [-1, 1]; negative values mean the surface turns away from the light."""
    return (layers.normal * light).sum(axis=2)


def group_map(layers, table):
    """Per-pixel value from a {group: value, 'default': value} table."""
    out = np.zeros(layers.flat.shape[:2], np.float32)
    total = np.zeros_like(out)
    for g, vis in layers.groups.items():
        out += vis * float(table.get(g, table['default']))
        total += vis
    return out + np.clip(1 - total, 0, 1) * float(table['default'])


def shade_mask(layers):
    """Pixels that receive shading (everything except background and ink-like parts)."""
    m = np.ones(layers.flat.shape[:2], np.float32)
    for g in NO_SHADE_GROUPS:
        if g in layers.groups:
            m -= layers.groups[g]
    return np.clip(m, 0, 1)


def tint_map(layers, spec):
    tints = spec['shadow_tint']
    default = hex_rgb(tints['default'])
    out = np.zeros(layers.flat.shape, np.float32)
    total = np.zeros(layers.flat.shape[:2], np.float32)
    for g, vis in layers.groups.items():
        out += vis[..., None] * hex_rgb(tints.get(g, tints['default']))
        total += vis
    out += np.clip(1 - total, 0, 1)[..., None] * default
    return out


def cel(x, threshold, edge=CEL_EDGE, below=True):
    """Hard step with a 1-2 px anti-aliased edge."""
    t = np.clip((threshold - x) / edge + 0.5, 0, 1) if below else np.clip((x - threshold) / edge + 0.5, 0, 1)
    return t * t * (3 - 2 * t)


def multiply_shadow(img, tint, amount):
    return img * (1 - amount[..., None] * (1 - tint))


def screen(img, color, amount):
    return 1 - (1 - img) * (1 - color * amount[..., None])


def apply_lines(img, layers, opacity=1.0, tint=None):
    a = layers.line_a * opacity
    color = layers.line_rgb if tint is None else mix(layers.line_rgb, tint, 0.5)
    return img * (1 - a[..., None]) + color * a[..., None]


def rim_light(layers, spec, light):
    """Back light catching silhouette edges on the side opposite the key light."""
    n = layers.normal
    rim_dir = np.array([-light[0], -light[1] * 0.3], np.float32)
    rim_dir /= np.linalg.norm(rim_dir)
    facing = np.clip(n[..., 0] * rim_dir[0] + n[..., 1] * rim_dir[1], 0, 1)
    edge = np.clip(1 - n[..., 2], 0, 1) ** 1.5
    return facing * edge


def simplify_shadow(s, layers):
    """Fill the lit slivers between nearby body shadows so they read as one designed shape.

    A painter designs skin shadows as a few clean shapes; the raw form, cast and self-shadow
    union leaves thin lit gaps where they nearly meet. A grey-scale closing sized to the head
    fills the gaps. No opening: thin terminator bands along the silhouette are real shapes.
    """
    unit = getattr(layers, 'unit', None)
    masks = [layers.groups[g] for g in SIMPLIFY_GROUPS if g in layers.groups]
    if not unit or not masks:
        return s
    m = np.clip(np.sum(masks, axis=0), 0, 1)
    r = max(int(round(SHADOW_SIMPLIFY * unit)), 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    sm = cv2.morphologyEx(s.astype(np.float32), cv2.MORPH_CLOSE, k)
    # lit islands inside a shadow: found by their lit core (a soft halo would join them to the
    # big lit area), then filled together with that halo
    lit = ((sm < LIT_CORE) & (m > 0.5)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(lit, connectivity=4)
    small = np.where(stats[:, cv2.CC_STAT_AREA] < SHADOW_HOLE_AREA * unit * unit)[0]
    small = small[small > 0]
    if small.size:
        islands = np.isin(labels, small).astype(np.uint8)
        halo = max(int(round(ISLAND_HALO * unit)), 1)
        islands = cv2.dilate(islands, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * halo + 1, 2 * halo + 1)))
        sm = np.maximum(sm, islands.astype(np.float32))
    return s * (1 - m) + sm * m


def shadow_amount_cel(layers, lam, spec):
    thr = group_map(layers, spec['cel_threshold'])
    form = cel(lam, thr, CEL_EDGE * 4)
    cast = cel(layers.cast, 0.5, 0.1, below=False)
    body = layers.groups.get('body', 0.0)
    shape = cel(layers.shadow_shape, 0.5, SHAPE_EDGE + (BODY_SHAPE_EDGE - SHAPE_EDGE) * body, below=False)
    s = simplify_shadow(np.maximum.reduce([form, cast, shape]), layers)
    return s * shade_mask(layers), thr


def render_anime(layers, spec, pal):
    light = light_vector(spec)
    lam = lambert(layers, light)
    img = layers.flat.copy()
    tint = tint_map(layers, spec)
    s, thr = shadow_amount_cel(layers, lam, spec)
    img = multiply_shadow(img, tint, s)
    if 'hair' in layers.groups:  # second, deeper cel level gives hair its layered depth
        deep = cel(lam, thr - 0.35, CEL_EDGE * 4) * layers.groups['hair']
        img = multiply_shadow(img, tint, deep * 0.6)
    hl = layers.hl_a * cel(lam, thr + 0.15, CEL_EDGE * 4, below=False) * (1 - s)
    img = screen(img, layers.hl_rgb, cel(hl, 0.35, 0.1, below=False))
    img = apply_lines(img, layers)
    return np.clip(img, 0, 1)


def soft_shaded(layers, spec, shadow_k=1.0):
    """Soft gradient shading, highlights and rim light; no line art (shared by painterly styles)."""
    light = light_vector(spec)
    lam = lambert(layers, light)
    img = layers.flat.copy()
    tint = tint_map(layers, spec)
    thr = group_map(layers, spec['cel_threshold'])
    sm = shade_mask(layers)
    form = np.clip((thr + 0.18 - lam) / 0.40, 0, 1) ** 1.2
    cast = blur(layers.cast, 2.5)
    shape = blur(layers.shadow_shape, 2.0)
    s = simplify_shadow(np.maximum.reduce([form * 0.9, cast, shape]), layers) * sm * shadow_k
    img = multiply_shadow(img, tint, s)
    occl = blur(layers.cast, 8.0) * 0.25 * sm * shadow_k     # contact softness around cast shadows
    img = multiply_shadow(img, tint, occl)

    hl = blur(layers.hl_a, 1.2) * np.clip((lam - thr) / 0.3, 0, 1)
    img = screen(img, layers.hl_rgb, hl * 0.9)
    rim = rim_light(layers, spec, light) * sm * (1 - s * 0.7)
    rim_color = hex_rgb(spec['light']['rim_color'])
    img = screen(img, rim_color, np.clip(rim * spec['light']['rim_strength'] * 1.6, 0, 1))
    return img, s


def render_illustration(layers, spec, pal):
    """Soft shading, colored lines, rim light, bloom and gentle grading."""
    img, _ = soft_shaded(layers, spec)
    img = apply_lines(img, layers, opacity=0.85)
    img = bloom(img, 0.78, 14.0, 0.35)
    img = grade(img, shadows=hex_rgb('#3B3458'), highlights=hex_rgb('#FFF1E2'), amount=0.10)
    rng = np.random.default_rng(spec['canvas']['seed'])
    grain = (rng.random(img.shape[:2]).astype(np.float32) - 0.5) * 0.025
    return np.clip(img + grain[..., None], 0, 1)


def bloom(img, threshold, sigma, strength):
    lum = raster.luminance(img)
    bright = img * np.clip((lum - threshold) / (1 - threshold), 0, 1)[..., None]
    return screen(img, blur(bright, sigma), np.full(img.shape[:2], strength, np.float32))


def grade(img, shadows, highlights, amount):
    lum = raster.luminance(img)[..., None]
    toned = mix(img * mix(np.ones(3), shadows * 2.2, 0.5), img, lum)
    toned = mix(toned, 1 - (1 - toned) * (1 - highlights * 0.15), lum)
    return mix(img, toned, amount)
