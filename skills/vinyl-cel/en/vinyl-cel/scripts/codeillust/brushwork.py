"""Stroke-based painterly rendering.

Follows the idea of Hertzmann (1998), "Painterly Rendering with Curved Brush
Strokes of Multiple Sizes" (https://dl.acm.org/doi/10.1145/280814.280951): repaint a reference image with brush strokes,
large brushes first, smaller brushes only where the painting still differs
from the reference. Strokes run along edges (perpendicular to the image
gradient), which is what makes the result look painted instead of blurred.
"""
import cv2
import numpy as np

BRUSH_RADII_UNITS = (30.0, 15.0, 7.5, 3.6, 1.8, 0.9)   # canvas units, large to small
STROKE_STEPS = (8, 8, 7, 6, 4, 3)                       # path points per stroke, per layer
ERROR_THRESHOLD = (0.0, 0.060, 0.055, 0.050, 0.045, 0.040)  # repaint where RGB distance exceeds this
DETAIL_FLOOR = (0.0, 0.0, 0.0, 0.25, 0.80, 0.95)        # finest layers only touch important regions (eyes, small faces)
RELIEF_GAIN = (1.0, 0.9, 0.55, 0.28, 0.10, 0.05)        # fine brushes carry less paint, so less relief
GRID_SPACING = 0.85                                # stroke starts per brush radius
COLOR_JITTER = 0.018
FLAT_GRADIENT = 0.004                              # below this the surface has no direction
DEFAULT_STROKE_ANGLE = -0.9                        # radians; hatching direction on flat areas
IMPASTO_STRENGTH = 0.9
CANVAS_WEAVE_UNITS = 3.2
CANVAS_WEAVE_STRENGTH = 0.035
ASSUMED_LIGHT = (-0.6, -0.8)


def paint(reference, detail, px_per_unit, rng, underpaint):
    """reference: HxWx3 float image. detail: HxW importance in 0..1 (1 = keep fine).
    Returns the painted HxWx3 float image."""
    reference = np.asarray(reference, dtype=np.float32)
    height, width = reference.shape[:2]
    painting = np.empty((height, width, 3), dtype=np.uint8)
    painting[:] = (np.asarray(underpaint) * 255).astype(np.uint8)
    relief = np.zeros((height, width), dtype=np.uint8)

    for layer, radius_units in enumerate(BRUSH_RADII_UNITS):
        radius = max(1.0, radius_units * px_per_unit)
        blurred = cv2.GaussianBlur(reference, (0, 0), radius * 0.5)
        starts = _stroke_starts(blurred, painting, detail, radius, layer, rng)
        if len(starts) == 0:
            continue
        paths = _stroke_paths(blurred, starts, radius, STROKE_STEPS[layer], rng)
        colors = blurred[starts[:, 1].astype(int), starts[:, 0].astype(int)]
        colors = np.clip(colors + rng.normal(0.0, COLOR_JITTER, (len(starts), 1)), 0.0, 1.0)
        _lay_strokes(painting, relief, paths, colors, radius, RELIEF_GAIN[layer], rng)

    result = painting.astype(np.float32) / 255.0
    result = _impasto(result, relief, px_per_unit)
    return _canvas_weave(result, px_per_unit)


def _stroke_starts(blurred, painting, detail, radius, layer, rng):
    height, width = blurred.shape[:2]
    step = max(1.0, radius * GRID_SPACING)
    xs = np.arange(step / 2, width, step)
    ys = np.arange(step / 2, height, step)
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.stack([grid_x.ravel(), grid_y.ravel()], axis=1)
    points += rng.uniform(-step / 2, step / 2, points.shape)
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    col, row = points[:, 0].astype(int), points[:, 1].astype(int)

    error = np.linalg.norm(painting.astype(np.float32) / 255.0 - blurred, axis=2)
    error = cv2.blur(error, (int(radius) | 1, int(radius) | 1))
    keep = (error[row, col] > ERROR_THRESHOLD[layer]) & (detail[row, col] >= DETAIL_FLOOR[layer])
    return points[keep]


def _stroke_paths(blurred, starts, radius, steps, rng):
    """Walk each stroke along the local edge direction. Returns (N, steps, 2)."""
    luma = cv2.cvtColor(blurred, cv2.COLOR_RGB2GRAY)
    grad_x = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    grad_y = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    height, width = luma.shape
    position = starts.copy()
    wobble = rng.normal(0.0, 0.35, len(starts))
    fallback = np.stack([np.cos(DEFAULT_STROKE_ANGLE + wobble), np.sin(DEFAULT_STROKE_ANGLE + wobble)], axis=1)
    previous = fallback.copy()
    path = [position.copy()]
    for _ in range(steps - 1):
        col = np.clip(position[:, 0], 0, width - 1).astype(int)
        row = np.clip(position[:, 1], 0, height - 1).astype(int)
        gx, gy = grad_x[row, col], grad_y[row, col]
        magnitude = np.sqrt(gx * gx + gy * gy)
        direction = np.stack([-gy, gx], axis=1) / (magnitude[:, None] + 1e-9)
        direction = np.where((magnitude > FLAT_GRADIENT)[:, None], direction, fallback)
        flip = np.sum(direction * previous, axis=1) < 0
        direction[flip] *= -1
        position = position + direction * radius
        previous = direction
        path.append(position.copy())
    return np.stack(path, axis=1)


def _lay_strokes(painting, relief, paths, colors, radius, relief_gain, rng):
    order = rng.permutation(len(paths))
    thickness = max(1, int(round(radius * 2)))
    heights = (rng.integers(60, 255, len(paths)) * relief_gain).astype(int)
    fixed = np.round(paths * 16).astype(np.int32)
    color_bytes = (colors * 255).astype(int)
    for index in order:
        points = fixed[index].reshape(-1, 1, 2)
        color = tuple(int(c) for c in color_bytes[index])
        cv2.polylines(painting, [points], False, color, thickness, cv2.LINE_AA, shift=4)
        cv2.polylines(relief, [points], False, int(heights[index]), thickness, cv2.LINE_AA, shift=4)


def _impasto(image, relief, px_per_unit):
    """Light the paint thickness so stroke edges catch light like real oil paint."""
    bump = cv2.GaussianBlur(relief.astype(np.float32) / 255.0, (0, 0), max(0.6, 0.6 * px_per_unit))
    grad_x = cv2.Sobel(bump, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    grad_y = cv2.Sobel(bump, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    lighting = -(grad_x * ASSUMED_LIGHT[0] + grad_y * ASSUMED_LIGHT[1]) * IMPASTO_STRENGTH
    return np.clip(image * (1.0 + lighting[..., None]), 0.0, 1.0)


def _canvas_weave(image, px_per_unit):
    height, width = image.shape[:2]
    period = max(2.0, CANVAS_WEAVE_UNITS * px_per_unit)
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    weave = np.sin(xs * 2 * np.pi / period) * np.sin(ys * 2 * np.pi / period)
    return np.clip(image * (1.0 + weave[..., None] * CANVAS_WEAVE_STRENGTH), 0.0, 1.0)
