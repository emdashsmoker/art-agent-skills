"""Painterly renderers: oil (stroke-based) and watercolor (pigment simulation).

Why: a painting is a re-description of the same scene with a physical medium.
Both renderers start from the soft-shaded layers and then imitate the medium:
- oil: curved brush strokes of decreasing size (Hertzmann 1998, "Painterly
  Rendering with Curved Brush Strokes of Multiple Sizes"), bristle streaks by
  line integral convolution, impasto relief and canvas weave.
- watercolor: transparent washes with pigment density modulation, edge
  darkening, granulation and wobble (after Bousseau et al. 2006,
  "Interactive watercolor rendering with temporal coherence and abstraction"),
  graphite under-drawing and unpainted paper margins.
"""
import cv2
import numpy as np

import raster
import styles
from raster import blur, hex_rgb, mix

# oil parameters: background brushes scale with the canvas, figure brushes with the head width
OIL_BG_BRUSHES = (0.026, 0.013, 0.007)          # fraction of canvas width
OIL_FIG_BRUSHES = (0.085, 0.042, 0.021, 0.011)  # fraction of head width
OIL_ERROR_T = 0.11          # summed RGB error; must exceed the stroke color jitter
OIL_BLUR_FACTOR = 0.6
OIL_MAX_STEPS = 10
OIL_MIN_STEPS = 3
OIL_CURVE_FILTER = 0.65
OIL_VALUE_JITTER = 0.022     # strokes vary in value more than in hue, like remixed paint
OIL_HUE_JITTER = 0.008
OIL_DETAIL_KEEP = 0.65      # how much of the precise render survives inside eyes and lips
OIL_SKIN_KEEP = 0.30        # skin is blended smoother than cloth and background
OIL_BUSY_KEEP = 0.40        # small busy details (windows, rims, fruit edges) keep this much of the precise render
OIL_SCENE_BG_BRUSHES = (0.014, 0.008, 0.0045)   # scene skies take smaller strokes than a portrait backdrop
LIC_LENGTH = 9
CANVAS_PERIOD = 4.0

# watercolor parameters
WC_PAPER = '#F7F3EA'
WC_EDGE_DARKEN = 0.55
WC_GRANULATION = 0.18
WC_TURBULENCE = 0.22
WC_WOBBLE_PX = 2.2
WC_PENCIL = '#55545E'


# ======================================================================= oil

def orientation_field(img, sigma, rng):
    """Stroke tangent field from the smoothed structure tensor (strokes follow forms)."""
    lum = raster.luminance(img).astype(np.float32)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    jxx, jxy, jyy = blur(gx * gx, sigma), blur(gx * gy, sigma), blur(gy * gy, sigma)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2
    coherence = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)
    coherence = coherence / (coherence.max() + 1e-6)
    # flat areas get a gently wandering default direction instead of noise
    drift = raster.value_noise(lum.shape, lum.shape[1] * 0.35, rng) * 0.6 + np.pi * 0.30
    w = np.clip(coherence * 25, 0, 1)
    tx = w * np.cos(theta) + (1 - w) * np.cos(drift)
    ty = w * np.sin(theta) + (1 - w) * np.sin(drift)
    norm = np.sqrt(tx * tx + ty * ty) + 1e-6
    return (tx / norm).astype(np.float32), (ty / norm).astype(np.float32)


def trace_stroke(x, y, radius, ref, canvas, tx, ty, region_id):
    """Follow the tangent field until the canvas already matches the reference better.

    Strokes also stop at material boundaries, the way a painter cuts in around a figure.
    """
    h, w = ref.shape[:2]
    color = ref[y, x]
    start_region = region_id[y, x]
    pts = [(x, y)]
    px, py, pdx, pdy = float(x), float(y), 0.0, 0.0
    for i in range(OIL_MAX_STEPS):
        ix, iy = int(px), int(py)
        if i >= OIL_MIN_STEPS:
            if np.abs(ref[iy, ix] - canvas[iy, ix]).sum() < np.abs(ref[iy, ix] - color).sum():
                break
        dx, dy = tx[iy, ix], ty[iy, ix]
        if dx * pdx + dy * pdy < 0:
            dx, dy = -dx, -dy
        if i > 0:
            dx, dy = OIL_CURVE_FILTER * dx + (1 - OIL_CURVE_FILTER) * pdx, OIL_CURVE_FILTER * dy + (1 - OIL_CURVE_FILTER) * pdy
            n = (dx * dx + dy * dy) ** 0.5 + 1e-6
            dx, dy = dx / n, dy / n
        px, py = px + radius * dx, py + radius * dy
        if not (0 <= px < w - 1 and 0 <= py < h - 1) or region_id[int(py), int(px)] != start_region:
            break
        pts.append((px, py))
        pdx, pdy = dx, dy
    return np.array(pts), color


def region_blur(src, groups, sigma):
    """Blur inside each material region only (normalized convolution), so hair never bleeds into sky."""
    out = np.zeros_like(src)
    for m in groups.values():
        weight = blur(m, sigma)
        out += m[..., None] * blur(src * m[..., None], sigma) / np.maximum(weight, 1e-4)[..., None]
    return out


def paint_layer(canvas, src, radius, rng, region_id, groups, region=None):
    """One brush size: place strokes wherever the canvas still differs from the blurred source."""
    h, w = src.shape[:2]
    ref = region_blur(src, groups, OIL_BLUR_FACTOR * radius)
    tx, ty = orientation_field(ref, radius * 2.0, rng)
    step = max(int(radius), 1)
    gh, gw = h // step, w // step
    diff = np.abs(canvas.astype(np.float32) / 255.0 - ref).sum(axis=2)
    cell_err = cv2.resize(diff[:gh * step, :gw * step], (gw, gh), interpolation=cv2.INTER_AREA)
    if region is not None:
        cell_err *= cv2.resize(region[:gh * step, :gw * step], (gw, gh), interpolation=cv2.INTER_AREA) > 0.2
    ys, xs = np.nonzero(cell_err > OIL_ERROR_T)
    canvas_f = canvas.astype(np.float32) / 255.0
    thickness = max(int(round(radius * 2)), 1)
    for k in rng.permutation(len(ys)):
        cx = min(xs[k] * step + int(rng.integers(0, step)), w - 2)
        cy = min(ys[k] * step + int(rng.integers(0, step)), h - 2)
        pts, color = trace_stroke(cx, cy, radius, ref, canvas_f, tx, ty, region_id)
        jitter = 1 + rng.normal(0, OIL_VALUE_JITTER) + rng.normal(0, OIL_HUE_JITTER, 3)
        c = tuple(float(v) for v in np.clip(color * jitter * 255, 0, 255))
        poly = np.round(pts * 16).astype(np.int32)
        cv2.polylines(canvas, [poly], False, c, thickness, lineType=cv2.LINE_AA, shift=4)
        if len(pts) == 1:
            cv2.circle(canvas, (int(cx), int(cy)), max(thickness // 2, 1), c, -1, lineType=cv2.LINE_AA)
    return canvas


def busy_mask(img, unit):
    """Where the picture has small, dense detail (window grids, rims, fingers): edge density."""
    lum = np.clip(raster.luminance(img) * 255, 0, 255).astype(np.uint8)
    edges = cv2.Canny(lum, 40, 110).astype(np.float32) / 255.0
    density = blur(edges, max(unit * 0.03, 2.0))
    return np.clip(density * 6.0, 0, 1)


def region_ids(layers):
    """Integer map of the dominant material group per pixel."""
    names = sorted(layers.groups)
    stack = np.stack([layers.groups[n] for n in names], axis=0)
    return np.argmax(stack, axis=0).astype(np.int16)


def line_integral(noise, tx, ty, length):
    """Average noise along each pixel's local stroke direction (bristle streaks)."""
    h, w = noise.shape
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    acc = np.zeros_like(noise)
    for t in range(-length, length + 1):
        acc += cv2.remap(noise, gx + tx * t, gy + ty * t, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / (2 * length + 1)


def relief_shading(img, height, light, strength):
    gy, gx = np.gradient(height)
    n = np.dstack([-gx * strength, -gy * strength, np.ones_like(gx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    shade = (n * light).sum(axis=2) / light[2]
    spec = np.clip(shade - 1.0, 0, 1) ** 2
    return np.clip(img * (0.92 + 0.08 * shade)[..., None] + spec[..., None] * 0.35, 0, 1)


def render_oil(layers, spec, pal):
    rng = np.random.default_rng(spec['canvas']['seed'])
    h, w = layers.flat.shape[:2]
    base, _ = styles.soft_shaded(layers, spec)
    base = styles.grade(base, hex_rgb('#40302A'), hex_rgb('#FFE9C8'), 0.25)
    precise = styles.apply_lines(base, layers, opacity=0.55)
    src = styles.apply_lines(base, layers, opacity=0.18)     # faint drawing guides the strokes

    ground = np.full((h, w, 3), np.clip(base.mean(axis=(0, 1)) * 0.85 * 255, 0, 255), np.uint8)
    detail = blur(cv2.dilate(layers.detail, np.ones((9, 9), np.uint8)), 6)
    busy = busy_mask(precise, layers.unit)
    ids = region_ids(layers)
    bg = styles.backdrop(layers)
    figure = 1 - bg

    # background and figure are painted as separate passes and cut in, like a painter
    # blocking the background first and then laying the figure over it
    canvas_bg = ground.copy()
    for frac in (OIL_SCENE_BG_BRUSHES if getattr(layers, 'kind', 'figure') == 'scene' else OIL_BG_BRUSHES):
        canvas_bg = paint_layer(canvas_bg, src, max(frac * w, 2.0), rng, ids, layers.groups, bg)
    underpaint = region_blur(src, layers.groups, max(0.03 * layers.unit, 2.0))   # blocked-in local colors
    canvas = np.clip(underpaint * 255, 0, 255).astype(np.uint8)
    fine_region = np.maximum.reduce([detail, busy, layers.groups.get('skin', np.zeros((h, w), np.float32))])
    for i, frac in enumerate(OIL_FIG_BRUSHES):
        last = i == len(OIL_FIG_BRUSHES) - 1   # the finest brush only works on skin and facial features
        canvas = paint_layer(canvas, src, max(frac * layers.unit, 1.5), rng, ids, layers.groups,
                             fine_region if last else figure)
    edge = blur(figure, 1.2)[..., None]
    canvas = (canvas.astype(np.float32) * edge + canvas_bg.astype(np.float32) * (1 - edge)).astype(np.uint8)
    img = canvas.astype(np.float32) / 255.0
    skin = blur(layers.groups.get('skin', np.zeros((h, w), np.float32)), 2.0)
    img = mix(img, blur(precise, 1.5), (skin * OIL_SKIN_KEEP)[..., None])
    img = mix(img, precise, (detail * OIL_DETAIL_KEEP)[..., None])
    img = mix(img, blur(precise, 0.8), (busy * figure * OIL_BUSY_KEEP)[..., None])

    tx, ty = orientation_field(img, 3.0, rng)
    hairs = blur(rng.random((h, w)).astype(np.float32), 0.7)      # bristle grooves, slightly coherent
    bristle = line_integral(hairs, tx, ty, LIC_LENGTH)
    bristle = (bristle - bristle.mean()) / (bristle.std() + 1e-6)
    img = np.clip(img * (1 + 0.02 * bristle[..., None]), 0, 1)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    weave = np.sin(xs * 2 * np.pi / CANVAS_PERIOD) * np.sin(ys * 2 * np.pi / CANVAS_PERIOD)
    height = bristle * 0.5 + raster.luminance(blur(img, 0.8)) * 5.0 + weave * 0.3
    img = relief_shading(img, height, styles.light_vector(spec), 0.45)
    return np.clip(img, 0, 1)


# ================================================================ watercolor

def pigment(color, density):
    """Bousseau density model: d > 1 darkens like extra pigment, d < 1 thins the wash."""
    d = density[..., None]
    return np.clip(color - (color - color * color) * (d - 1), 0, 1)


def wobble(img, rng, amount):
    h, w = img.shape[:2]
    nx = (raster.value_noise((h, w), 40, rng, 2) - 0.5) * 2 * amount
    ny = (raster.value_noise((h, w), 40, rng, 2) - 0.5) * 2 * amount
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx + nx, gy + ny, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def edge_pooling(region_masks, radius):
    """Pigment collects where a wash dries: just inside every region boundary."""
    out = None
    for m in region_masks:
        inner = np.clip(m - blur(m, radius), 0, 1)
        out = inner if out is None else np.maximum(out, inner)
    return out


def paper_margin(shape, rng):
    """Irregular vignette: the background wash stops before the paper edge."""
    h, w = shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = (xs - w * 0.5) / (w * 0.5), (ys - h * 0.46) / (h * 0.5)
    r = np.sqrt(dx * dx * 1.05 + dy * dy)
    noise = raster.value_noise(shape, w * 0.08, rng, 3)
    return np.clip((0.98 - r + (noise - 0.5) * 0.35) / 0.08, 0, 1)


def render_watercolor(layers, spec, pal):
    rng = np.random.default_rng(spec['canvas']['seed'])
    h, w = layers.flat.shape[:2]
    paper = hex_rgb(WC_PAPER)

    base = mix(layers.flat, np.ones(3, np.float32), 0.10)      # washes are lighter than opaque paint
    light = styles.light_vector(spec)
    lam = styles.lambert(layers, light)
    thr = styles.group_map(layers, spec['cel_threshold'])
    sm = styles.shade_mask(layers)
    tint = styles.tint_map(layers, spec)
    shadow = np.maximum.reduce([np.clip((thr + 0.1 - lam) / 0.3, 0, 1), blur(layers.cast, 1.5),
                                blur(layers.shadow_shape, 1.5)]) * sm
    shadow = wobble(shadow, rng, WC_WOBBLE_PX * 1.5)

    regions = [wobble(v, rng, WC_WOBBLE_PX) for g, v in layers.groups.items() if g not in styles.BACKDROP_GROUPS]
    pooling = edge_pooling(regions + [shadow], max(w * 0.004, 2.0))
    turbulence = raster.value_noise((h, w), w * 0.06, rng, 3)
    granulation = raster.value_noise((h, w), 2.5, rng, 2)
    density = (1 + WC_TURBULENCE * (turbulence - 0.5) * 2 + WC_GRANULATION * (granulation - 0.5) * 2
               + WC_EDGE_DARKEN * pooling)

    wash = wobble(base, rng, WC_WOBBLE_PX)
    wash = multiply_glaze(wash, tint, shadow * 0.85)
    wash = pigment(wash, density)
    hl = blur(layers.hl_a, 1.0) * np.clip((lam - thr) / 0.3, 0, 1)
    wash = mix(wash, np.ones(3, np.float32), (hl * 0.45)[..., None])   # lifted paint shows paper

    figure = np.clip(1 - styles.backdrop(layers), 0, 1)
    margin = np.maximum(paper_margin((h, w), rng), figure)
    margin = wobble(margin, rng, 3.0)
    img = mix(np.ones(3, np.float32), wash, margin[..., None])

    fibers = raster.value_noise((h, w), 1.5, rng, 2)
    img = img * paper * (0.97 + 0.03 * fibers[..., None])

    pencil_a = wobble(layers.line_a, rng, 0.8) * (0.55 + 0.45 * raster.value_noise((h, w), 3, rng))
    pencil = hex_rgb(WC_PENCIL)
    img = img * (1 - pencil_a[..., None] * 0.55) + pencil * (pencil_a[..., None] * 0.55) * 0.9
    detail = blur(layers.detail, 1.0)
    img = mix(img, styles.apply_lines(img, layers, 0.6), (detail * 0.6)[..., None])
    return np.clip(img, 0, 1)


def multiply_glaze(img, tint, amount):
    return img * (1 - amount[..., None] * (1 - tint))
