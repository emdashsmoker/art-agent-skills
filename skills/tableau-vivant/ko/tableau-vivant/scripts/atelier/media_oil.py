"""Oil family: the picture is rebuilt from brush strokes, coarse to fine.

Each layer compares the canvas with a blurred reference and lays a stroke where they
disagree. Strokes follow the form (around or along the surface), carry bristle streaks,
and leave ridges that catch the light. One engine covers alla prima oil, impasto,
impressionism, pointillism, pastel and gouache by changing the stroke vocabulary.
"""
import numpy as np
import cv2
from numba import njit

from .shade import downsample
from .noise import fractal_noise, rng
from . import media_common as mc

BRISTLE_SPACING = 0.34       # bristle streak pitch as a fraction of brush radius
MIN_STROKE_POINTS = 2
FINE_BRUSH_PX = 3.5          # below this radius a stroke is drawn as a single mark, without bristle streaks


def direction_field(F, along_form=False, swirl_scale=3.0, smooth=3.0, swirl=0.3):
    """Stroke angle per output pixel. On surfaces strokes wrap the form; in open sky and backdrops they
    run near-horizontal, wandering by `swirl` (0 = level strokes, 1 = full turbulent swirl)."""
    g = F.g
    n = downsample(g["normal"], g)
    mask = F.mask > 0.5
    cam = g["camera"]
    nx, ny = n @ cam.right, -(n @ cam.up)                  # screen-space projection (y down)
    angle = np.arctan2(ny, nx) + (0 if along_form else np.pi / 2)
    h, w = mask.shape
    wander = (fractal_noise((h, w), max(h, w) / swirl_scale, F.seed, 61, octaves=2) - 0.5) * np.pi * 1.6 * swirl
    flat = np.hypot(nx, ny) < 0.12                          # surface facing the viewer: no clear direction
    angle = np.where(mask & ~flat, angle, wander)
    # smooth on the double angle so opposite directions do not cancel
    c = cv2.GaussianBlur(np.cos(2 * angle).astype(np.float32), (0, 0), smooth)
    s = cv2.GaussianBlur(np.sin(2 * angle).astype(np.float32), (0, 0), smooth)
    return (0.5 * np.arctan2(s, c)).astype(np.float32)


@njit(cache=True)
def _trace(x0, y0, angle, ref, canvas, radius, max_len, min_len, curvature):
    """Follow the direction field from (x0, y0); stop when the stroke colour stops improving the canvas."""
    h, w = angle.shape
    pts = np.zeros((max_len + 1, 2), np.float32)
    pts[0, 0], pts[0, 1] = x0, y0
    cr, cg, cb = ref[int(y0), int(x0), 0], ref[int(y0), int(x0), 1], ref[int(y0), int(x0), 2]
    x, y = x0, y0
    ldx, ldy = 0.0, 0.0
    count = 1
    for i in range(1, max_len + 1):
        a = angle[int(y), int(x)]
        dx, dy = np.cos(a), np.sin(a)
        if i > 1 and ldx * dx + ldy * dy < 0:
            dx, dy = -dx, -dy
        dx = curvature * dx + (1 - curvature) * ldx
        dy = curvature * dy + (1 - curvature) * ldy
        norm = np.sqrt(dx * dx + dy * dy)
        if norm < 1e-6:
            break
        dx, dy = dx / norm, dy / norm
        x, y = x + radius * dx, y + radius * dy
        if x < 0 or y < 0 or x >= w - 1 or y >= h - 1:
            break
        ix, iy = int(x), int(y)
        if i > min_len:
            d_ref = abs(ref[iy, ix, 0] - cr) + abs(ref[iy, ix, 1] - cg) + abs(ref[iy, ix, 2] - cb)
            d_can = abs(ref[iy, ix, 0] - canvas[iy, ix, 0]) + abs(ref[iy, ix, 1] - canvas[iy, ix, 1]) + \
                abs(ref[iy, ix, 2] - canvas[iy, ix, 2])
            if d_ref > d_can:
                break
        pts[count, 0], pts[count, 1] = x, y
        count += 1
        ldx, ldy = dx, dy
    return pts[:count]


def _draw_stroke(canvas, height, pts, color, radius, generator, bristle_contrast, opacity, dab, relief=1.0):
    """One stroke = a bundle of thin bristle streaks with slightly different loads of paint."""
    if dab or len(pts) < MIN_STROKE_POINTS:
        # a dab: a single touch of the brush (pointillism, the smallest accents)
        c = np.clip(color * (1 + bristle_contrast * (generator.random() - 0.5) * 2), 0, 1)
        center = (int(round(pts[0, 0] * 8)), int(round(pts[0, 1] * 8)))
        cv2.circle(canvas, center, int(round(radius * 8)), c.tolist(), -1, cv2.LINE_AA, shift=3)
        cv2.circle(height, center, int(round(radius * 8)), float(0.4 + 0.6 * generator.random()), -1, cv2.LINE_AA, shift=3)
        return
    tangent = np.gradient(pts, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], 1)
    if radius < FINE_BRUSH_PX:
        n_bristles, thickness, offsets = 1, max(1, int(round(2 * radius))), np.zeros(1)     # a fine brush leaves one clean mark
    else:
        n_bristles = max(3, int(2 * radius / max(radius * BRISTLE_SPACING, 1.0)))
        thickness = max(1, int(round(2 * radius / n_bristles * 1.7)))
        offsets = np.linspace(-radius, radius, n_bristles) * 0.85
    taper = np.sin(np.linspace(0.2, np.pi - 0.2, len(pts))) ** 0.5       # stroke narrows at both ends
    for offset in offsets:
        line = pts + normal * (offset * taper)[:, None]
        c = np.clip(color * (1 + bristle_contrast * (generator.random() - 0.5) * 2), 0, 1)
        poly = np.round(line * 8).astype(np.int32).reshape(-1, 1, 2)
        if opacity >= 0.999:
            cv2.polylines(canvas, [poly], False, c.tolist(), thickness, cv2.LINE_AA, shift=3)
        else:
            x0, y0 = np.maximum(line.min(0).astype(int) - thickness - 2, 0)
            x1, y1 = line.max(0).astype(int) + thickness + 3
            patch = canvas[y0:y1, x0:x1]
            layer = patch.copy()
            cv2.polylines(layer, [poly - np.array([x0, y0], np.int32) * 8], False, c.tolist(), thickness, cv2.LINE_AA, shift=3)
            canvas[y0:y1, x0:x1] = patch * (1 - opacity) + layer * opacity
        cv2.polylines(height, [poly], False, float(0.35 + 0.65 * generator.random()) * relief, thickness, cv2.LINE_AA, shift=3)


def paint(reference, angle, seed, ground=(0.45, 0.33, 0.24), brush_radii=(22, 11, 5.5, 2.8),
          error_threshold=0.05, focus=None, stroke_length=9, curvature=0.7, color_jitter=0.05, hue_jitter=0.0,
          bristle_contrast=0.10, impasto=0.5, weave=0.03, opacity=1.0, dabs=False, density=1.0, coverage=1.0):
    """Stroke-based painting of `reference`.

    focus: 0..1 map; finer layers only paint where focus allows (1 = every brush size).
    hue_jitter: independent RGB variation per stroke (broken colour). coverage < 1 leaves ground showing.
    """
    h, w = reference.shape[:2]
    generator = rng(seed, 71)
    canvas = np.empty((h, w, 3), np.float32)
    canvas[:] = np.asarray(ground, np.float32)
    height = np.zeros((h, w), np.float32)
    reference = np.ascontiguousarray(reference, np.float32)
    angle = np.ascontiguousarray(angle, np.float32)
    n_layers = len(brush_radii)
    for layer, radius in enumerate(brush_radii):
        ref = cv2.GaussianBlur(reference, (0, 0), max(radius * 0.45, 0.6))
        error = np.abs(canvas - ref).sum(-1)
        step = max(int(round(radius / density)), 2)
        ys = np.arange(step // 2, h - 1, step)
        xs = np.arange(step // 2, w - 1, step)
        gx, gy = np.meshgrid(xs, ys)
        gx = np.clip(gx + generator.integers(-step // 2, step // 2 + 1, gx.shape), 1, w - 2).ravel()
        gy = np.clip(gy + generator.integers(-step // 2, step // 2 + 1, gy.shape), 1, h - 2).ravel()
        cell_error = cv2.blur(error, (step, step))[gy, gx]
        keep = cell_error > (0 if layer == 0 else error_threshold)
        if layer == 0 and coverage < 1:
            keep &= generator.random(len(gx)) < coverage
        if focus is not None and layer > 0:
            needed = layer / max(n_layers - 1, 1)            # finer layers need more focus
            keep &= focus[gy, gx] >= needed - 0.26
        order = generator.permutation(np.flatnonzero(keep))
        min_len = 2 if layer == 0 else 1
        # broad strokes vary a lot; fine strokes are controlled, so detail stays clean
        weight = 1.0 if dabs else float(np.clip(radius / brush_radii[0], 0.0, 1.0) ** 0.6)
        for idx in order:
            x0, y0 = float(gx[idx]), float(gy[idx])
            pts = _trace(x0, y0, angle, ref, canvas, float(radius), stroke_length, min_len, curvature)
            base = ref[int(y0), int(x0)]
            # jitter relative to the colour itself so dark passages do not turn into confetti
            color = base * (1 + generator.normal(0, color_jitter * weight)) + \
                base.mean() * generator.normal(0, (color_jitter * 0.6 + hue_jitter) * weight, 3).astype(np.float32)
            _draw_stroke(canvas, height, pts, color, radius, generator, bristle_contrast * weight, opacity, dabs, weight)
    if impasto:      # light rakes across the paint ridges
        relief = cv2.GaussianBlur(height, (0, 0), 0.7)
        gxh = cv2.Sobel(relief, cv2.CV_32F, 1, 0, ksize=3)
        gyh = cv2.Sobel(relief, cv2.CV_32F, 0, 1, ksize=3)
        canvas = canvas * (1 + impasto * 0.12 * np.clip(-(gxh + gyh), -1, 1))[..., None]
    if weave:
        canvas = canvas * (1 + weave * mc.canvas_weave((h, w)))[..., None]
    return np.clip(canvas, 0, 1)


def render_oil(F, brush_radii=(26, 12, 6, 3, 1.6), ground=(0.42, 0.31, 0.22), error_threshold=0.045,
               stroke_length=9, curvature=0.7, color_jitter=0.05, hue_jitter=0.0, bristle_contrast=0.10,
               impasto=0.5, weave=0.03, along_form=False, terminator_saturation=0.3, contrast=1.0,
               saturation=1.0, focus_bias=0.0, dabs=False, density=1.0, coverage=1.0, opacity=1.0,
               detail_scale=None, edge_soften=0.0, fidelity=0.35, swirl=0.3):
    """detail_scale: multiply all brush radii (auto-scales with canvas size when None).
    fidelity: how tightly focal areas (faces, hands) are rendered; 0 = strokes only, 1 = fully resolved."""
    scale = detail_scale if detail_scale is not None else max(F.width, F.height) / 1024.0
    reference = mc.saturate(F.reference(terminator_saturation, contrast), saturation)
    if edge_soften:
        reference = mc.mix(reference, cv2.GaussianBlur(reference, (0, 0), edge_soften * scale), 0.6)
    angle = direction_field(F, along_form, swirl=swirl)
    focus = np.clip(cv2.GaussianBlur(F.focus, (0, 0), 4 * scale) + focus_bias, 0, 1)
    image = paint(reference, angle, F.seed, ground, tuple(r * scale for r in brush_radii), error_threshold, focus,
                  stroke_length, curvature, color_jitter, hue_jitter, bristle_contrast, impasto, weave, opacity,
                  dabs, density, coverage)
    return _tighten(image, reference, F, fidelity)


def _tighten(image, reference, F, fidelity):
    """Resolve focal areas toward the observed reference, as a painter does with a small brush on a face."""
    if not fidelity:
        return image
    amount = cv2.GaussianBlur(np.clip((F.focus - 0.7) / 0.3, 0, 1) * fidelity, (0, 0), 3.0)[..., None]
    return mix_keep_texture(image, reference, amount)


def mix_keep_texture(image, reference, amount):
    """Blend toward the reference but keep the canvas's fine paint texture."""
    texture = image - cv2.GaussianBlur(image, (0, 0), 1.5)
    return np.clip(mc.mix(image, reference + texture * 0.3, amount), 0, 1)


def render_classical(F, glaze=(1.0, 0.93, 0.78), varnish=0.30, sfumato=1.6, craquelure=0.35, chiaroscuro=1.2,
                     brush_radii=(16, 8, 4, 2, 1.2), umber=(0.20, 0.13, 0.08), vignette=0.35, saturation=0.88,
                     terminator_saturation=0.2, canvas_weave=0.02, finish=0.62, lost_edges=0.5):
    """Old-master oil: smooth blended flesh, soft and lost edges, deep warm shadows, aged varnish, fine cracks.

    finish: 0 = loose visible brushwork, 1 = enamel-smooth academic finish.
    lost_edges: how much shadow-side contours dissolve into the ground."""
    scale = max(F.width, F.height) / 1024.0
    reference = mc.saturate(F.reference(terminator_saturation, chiaroscuro), saturation)
    # shadows sink toward the warm umber underpainting
    value = mc.luminance(reference)[..., None]
    reference = mc.mix(np.asarray(umber, np.float32) + reference * 0.55, reference, mc.smoothstep(0.04, 0.40, value))
    # sfumato: soften contours, most where the form turns into shadow
    soft = cv2.GaussianBlur(reference, (0, 0), sfumato * scale)
    softer = cv2.GaussianBlur(reference, (0, 0), sfumato * 3.0 * scale)
    dark = 1 - mc.smoothstep(0.10, 0.45, mc.luminance(soft))[..., None]
    reference = mc.mix(mc.mix(reference, soft, 0.5), softer, dark * lost_edges)
    angle = direction_field(F, along_form=False, smooth=5.0)
    focus = np.clip(cv2.GaussianBlur(F.focus, (0, 0), 4 * scale) + 0.25, 0, 1)
    image = paint(reference, angle, F.seed, umber, tuple(r * scale for r in brush_radii), 0.025, focus,
                  stroke_length=7, curvature=0.6, color_jitter=0.02, bristle_contrast=0.03, impasto=0.15,
                  weave=canvas_weave)
    # glazing: many thin layers pull the brushwork together into continuous modelling
    amount = np.clip(finish * (0.55 + 0.45 * F.focus), 0, 1)[..., None]
    image = mix_keep_texture(image, reference, amount)
    image = image * mc.mix(np.ones(3, np.float32), np.asarray(glaze, np.float32), varnish * 1.6)
    h, w = image.shape[:2]
    if craquelure:
        # crack network: ridges of a cellular noise field, thin and dark
        cells = fractal_noise((h, w), 26 * scale, F.seed, 701, octaves=2)
        fine = fractal_noise((h, w), 9 * scale, F.seed, 702, octaves=2)
        ridge = np.minimum(np.abs(cells - 0.5), np.abs(fine - 0.5) * 1.4)
        cracks = np.clip(1 - ridge / 0.006, 0, 1) * np.clip(fractal_noise((h, w), 140 * scale, F.seed, 703, octaves=2) * 2 - 0.5, 0, 1)
        image = image * (1 - craquelure * 0.45 * cracks[..., None])
    if vignette:
        image = image * mc.vignette((h, w), vignette, 0.55)[..., None]
    return np.clip(image, 0, 1)


def render_pastel(F, tooth=0.55, brush_radii=(20, 10, 5, 2.5), paper_color=(0.78, 0.74, 0.68), softness=1.2):
    """Soft pastel: chalky strokes that skip over the paper tooth, blended with a finger."""
    scale = max(F.width, F.height) / 1024.0
    reference = mc.mix(F.reference(0.2), np.ones(3, np.float32), 0.10)
    angle = direction_field(F, along_form=True)
    focus = np.clip(cv2.GaussianBlur(F.focus, (0, 0), 4 * scale) + 0.1, 0, 1)
    image = paint(reference, angle, F.seed, paper_color, tuple(r * scale for r in brush_radii), 0.05, focus,
                  stroke_length=7, curvature=0.5, color_jitter=0.06, hue_jitter=0.02, bristle_contrast=0.22,
                  impasto=0.0, weave=0.0)
    image = mc.mix(image, cv2.GaussianBlur(image, (0, 0), softness * scale), 0.45)
    paper = mc.paper_height(image.shape[:2], F.seed, coarse=4.0)
    skip = np.clip((paper - (1 - tooth)) / 0.25, 0, 1)[..., None] * 0.55     # chalk misses the valleys
    return np.clip(mc.mix(image, np.asarray(paper_color, np.float32), skip), 0, 1)
