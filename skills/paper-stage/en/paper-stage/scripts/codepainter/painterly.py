"""Painterly pass: repaints an image as layers of brush strokes, large to small.

Method (after Hertzmann, "Painterly Rendering with Curved Brush Strokes of Multiple
Sizes", SIGGRAPH 1998): start from a toned ground, and for each brush size lay a
stroke wherever the canvas still differs from the (blurred) source. Strokes follow
the edges of the forms, so big shapes are blocked in loosely and only areas that
need it receive small, precise strokes. The result keeps gaps, overlaps and lost
edges that a blur filter cannot produce.
"""
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from .color import luminance, rgb
from .shading import blur

REFERENCE_HEIGHT = 1000.0                     # brush sizes below are given for this canvas height
DRAW_SUPERSAMPLE = 2                          # strokes are drawn enlarged and shrunk, since PIL does not anti-alias
MIN_STROKE_STEPS = 2
CURVATURE_FILTER = 0.7                        # 1 = follow the flow exactly, lower = stiffer strokes
FLOW_FALLBACK_WEIGHT = 2e-4                   # strength of the default direction against image edges
FLOW_WANDER = np.radians(75.0)                # how far the default direction drifts across flat areas
DEFAULT_FLOW_ANGLE = np.radians(62.0)         # hatch direction in flat areas (a right hand's natural diagonal)
IMPORTANCE_GAIN = 0.55                        # error threshold falls by this share where importance = 1


@dataclass(frozen=True)
class BrushLayer:
    radius: float          # brush radius in pixels at the reference height
    threshold: float       # repaint a grid cell when its mean colour error (summed over RGB) exceeds this
    steps: int             # maximum stroke length, in steps of one radius
    jitter: float          # per-stroke colour variation: the "broken colour" of real paint
    focus_only: bool = False   # lay this layer only where importance is high (eyes, mouth)


# Large to small: block in, shape, refine, accent. Jitter must stay below threshold / 3,
# or every stroke would itself count as an error and be painted over again.
BRUSH_LAYERS = (
    BrushLayer(34.0, 0.00, 6, 0.022),
    BrushLayer(17.0, 0.13, 8, 0.020),
    BrushLayer(8.5, 0.13, 10, 0.014),
    BrushLayer(4.2, 0.13, 10, 0.008),
    BrushLayer(2.2, 0.15, 9, 0.004),
    BrushLayer(1.3, 0.15, 8, 0.0, focus_only=True),
)


def flow_field(source, scale, seed=0):
    """Angle of the stroke direction at every pixel: along edges, a wandering diagonal where flat."""
    from .fx import fbm
    luma = blur(luminance(source), 3.0 * scale)
    grad_y, grad_x = np.gradient(luma)
    default = DEFAULT_FLOW_ANGLE + (fbm(luma.shape, scale=0.7, octaves=2, seed=seed) - 0.5) * 2.0 * FLOW_WANDER
    normal_x, normal_y = -np.sin(default), np.cos(default)
    # Structure tensor, smoothed wide so edge directions spread into the flat areas next to them.
    sigma = 10.0 * scale
    j_xx = blur(grad_x * grad_x, sigma) + FLOW_FALLBACK_WEIGHT * normal_x ** 2
    j_yy = blur(grad_y * grad_y, sigma) + FLOW_FALLBACK_WEIGHT * normal_y ** 2
    j_xy = blur(grad_x * grad_y, sigma) + FLOW_FALLBACK_WEIGHT * normal_x * normal_y
    gradient_angle = 0.5 * np.arctan2(2.0 * j_xy, j_xx - j_yy)
    return (gradient_angle + np.pi / 2).astype(np.float32)


def _pick_stroke_starts(error, cell, threshold_map):
    """One candidate per grid cell, at the pixel of largest error, kept if the cell's mean error is high."""
    height, width = error.shape
    rows, cols = height // cell, width // cell
    blocks = error[:rows * cell, :cols * cell].reshape(rows, cell, cols, cell).transpose(0, 2, 1, 3)
    flat = blocks.reshape(rows, cols, cell * cell)
    worst = flat.argmax(axis=2)
    ys = np.arange(rows)[:, None] * cell + worst // cell
    xs = np.arange(cols)[None, :] * cell + worst % cell
    keep = flat.mean(axis=2) > threshold_map[ys, xs]
    return np.stack([xs[keep], ys[keep]], axis=1).astype(np.float64)


def _trace_strokes(starts, reference, canvas, angle, radius, max_steps, rng):
    """Walk every stroke along the flow field at once. Returns (paths, lengths, colours)."""
    height, width = angle.shape
    count = len(starts)
    paths = np.zeros((count, max_steps + 1, 2))
    paths[:, 0] = starts
    lengths = np.ones(count, dtype=np.int64)
    ix, iy = starts[:, 0].astype(int), starts[:, 1].astype(int)
    colors = reference[iy, ix]
    direction = np.stack([np.cos(angle[iy, ix]), np.sin(angle[iy, ix])], axis=1)
    direction *= rng.choice([-1.0, 1.0], size=(count, 1))      # a flow line has no preferred sense
    alive = np.ones(count, dtype=bool)
    position = starts.copy()
    for step in range(1, max_steps + 1):
        position = position + direction * radius
        inside = (position[:, 0] >= 0) & (position[:, 0] < width) & (position[:, 1] >= 0) & (position[:, 1] < height)
        alive &= inside
        ix = np.clip(position[:, 0], 0, width - 1).astype(int)
        iy = np.clip(position[:, 1], 0, height - 1).astype(int)
        if step > MIN_STROKE_STEPS:
            # Stop once the stroke colour fits the source worse than what is already on the canvas.
            to_stroke = np.abs(reference[iy, ix] - colors).sum(axis=1)
            to_canvas = np.abs(reference[iy, ix] - canvas[iy, ix]).sum(axis=1)
            alive &= to_stroke <= to_canvas
        paths[alive, step] = position[alive]
        lengths[alive] = step + 1
        flow = np.stack([np.cos(angle[iy, ix]), np.sin(angle[iy, ix])], axis=1)
        flow *= np.sign(np.sum(flow * direction, axis=1, keepdims=True) + 1e-9)   # keep heading the same way
        direction = CURVATURE_FILTER * flow + (1.0 - CURVATURE_FILTER) * direction
        direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-9)
    return paths, lengths, colors


def _stroke_outline(points, radius):
    """Polygon of one brush mark: blunt where the brush lands, thinning where it lifts off."""
    points = np.asarray(points)
    count = len(points)
    tangent = np.gradient(points, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-9)
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    position = np.linspace(0.0, 1.0, count)
    half = radius * (1.0 - 0.55 * position ** 2)
    nose = points[0] - tangent[0] * radius * 0.7            # rounded start cap
    tail = points[-1] + tangent[-1] * radius * 0.8          # pointed lift-off
    left, right = points + normal * half[:, None], points - normal * half[:, None]
    return np.vstack([nose[None], left, tail[None], right[::-1]])


def _draw_strokes(image, relief, paths, lengths, colors, radius, jitter, rng):
    draw, draw_relief = ImageDraw.Draw(image), ImageDraw.Draw(relief)
    zoom = DRAW_SUPERSAMPLE
    noise = rng.normal(0.0, jitter, (len(paths), 3)) + rng.normal(0.0, jitter, (len(paths), 1))
    tones = (np.clip(colors + noise, 0.0, 1.0) * 255).astype(int)
    thickness = rng.integers(96, 224, len(paths))           # each stroke lays paint of a different thickness
    for index in rng.permutation(len(paths)):
        points = paths[index, :lengths[index]] * zoom
        color, level = tuple(tones[index]), int(thickness[index])
        if len(points) > 1:
            outline = [tuple(p) for p in _stroke_outline(points, radius * zoom)]
            draw.polygon(outline, fill=color)
            draw_relief.polygon(outline, fill=level)
        else:
            x, y = points[0]
            box = [x - radius * zoom, y - radius * zoom, x + radius * zoom, y + radius * zoom]
            draw.ellipse(box, fill=color)
            draw_relief.ellipse(box, fill=level)


def _smear_along_flow(field, angle, length, samples=7):
    """Average a field along the local stroke direction (cheap line integral convolution)."""
    height, width = angle.shape
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    cos_a, sin_a = np.cos(angle).astype(np.float32), np.sin(angle).astype(np.float32)
    total = np.zeros_like(field, dtype=np.float32)
    for offset in np.linspace(-length, length, samples):
        coords = [grid_y + sin_a * offset, grid_x + cos_a * offset]
        if field.ndim == 2:
            total += ndi.map_coordinates(field, coords, order=1, mode="nearest")
        else:
            for channel in range(field.shape[2]):
                total[..., channel] += ndi.map_coordinates(field[..., channel], coords, order=1, mode="nearest")
    return total / samples


def canvas_weave(shape, scale, seed):
    """Woven canvas texture as a height field around 0."""
    height, width = shape
    rng = np.random.default_rng(seed)
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    period = 3.2 * scale
    weave = np.sin(grid_x * 2 * np.pi / period) * np.sin(grid_y * 2 * np.pi / period)
    return weave * 0.5 + blur(rng.normal(0.0, 1.0, shape).astype(np.float32), 1.2 * scale) * 1.5


def _shrunk(image, size):
    return np.asarray(image.resize(size, Image.BOX), dtype=np.float32) / 255.0


def repaint(source, seed=0, importance=None, ground=None, detail=1.0, bristle=1.0, impasto=1.0, canvas=1.0,
            layers=BRUSH_LAYERS):
    """Repaint `source` (HxWx3) with brush strokes.

    importance: optional HxW map (0..1); 1 marks areas that deserve fine strokes (a face).
    ground: toned ground colour showing through gaps; default is a dulled average of the source.
    detail: >1 paints finer everywhere, <1 leaves it looser.
    bristle, impasto, canvas: strength of brush-hair streaks, paint relief and canvas weave (0 = off).
    """
    height, width = source.shape[:2]
    scale = height / REFERENCE_HEIGHT
    rng = np.random.default_rng(seed)
    angle = flow_field(source, scale, seed)
    if ground is None:
        ground = rgb(source.reshape(-1, 3).mean(axis=0)) * 0.55 + rgb("#6b5a4a") * 0.45
    big = (width * DRAW_SUPERSAMPLE, height * DRAW_SUPERSAMPLE)
    image = Image.new("RGB", big, tuple(int(c * 255) for c in rgb(ground)))
    relief = Image.new("L", big, 128)
    focus = np.zeros((height, width), dtype=np.float32) if importance is None else blur(importance, 6 * scale)

    for layer in layers:
        radius = layer.radius * scale
        reference = blur(source, radius * 0.45)
        painted = _shrunk(image, (width, height))
        error = np.abs(painted - reference).sum(axis=2)
        threshold_map = (layer.threshold / detail) * (1.0 - IMPORTANCE_GAIN * focus)
        if layer.focus_only:
            threshold_map = np.where(focus > 0.5, threshold_map, np.inf)
        starts = _pick_stroke_starts(error, max(int(round(radius)), 2), threshold_map)
        if len(starts) == 0:
            continue
        paths, lengths, colors = _trace_strokes(starts, reference, painted, angle, radius, layer.steps, rng)
        _draw_strokes(image, relief, paths, lengths, colors, radius, layer.jitter, rng)

    result = _shrunk(image, (width, height))
    thickness = _shrunk(relief, (width, height))
    if bristle > 0:
        # Brush hairs leave streaks along the stroke: smear fine noise along the flow.
        streaks = _smear_along_flow(rng.normal(0.0, 1.0, (height, width)).astype(np.float32), angle, 7.0 * scale)
        streaks /= max(float(streaks.std()), 1e-6)
        result = result * (1.0 + 0.022 * bristle * streaks[..., None])
        thickness = thickness + 0.04 * bristle * streaks
    surface = blur(thickness, 0.9 * scale)
    if canvas > 0:
        surface = surface + 0.010 * canvas * canvas_weave((height, width), scale, seed)
    if impasto > 0 or canvas > 0:
        # Light the paint surface from the upper left so stroke edges catch highlights and cast shade.
        grad_y, grad_x = np.gradient(surface)
        relief_light = -(grad_x * 0.62 + grad_y * 0.78) * 1.1 * max(impasto, 0.35)
        result = result * (1.0 + np.clip(relief_light, -0.22, 0.22)[..., None])
    return np.clip(result, 0.0, 1.0)
