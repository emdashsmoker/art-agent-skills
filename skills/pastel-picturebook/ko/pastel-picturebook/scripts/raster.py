"""Raster primitives: curves, antialiased masks, tapered strokes, compositing.

Everything the painter needs is built from four ideas:
  curve  -> smooth polyline through control points
  mask   -> float32 coverage map (0..1) of a filled polygon or stroke
  over   -> composite a colour through a mask
  field  -> per-pixel scalar maps (blur, noise, pseudo-lighting)

Images are float32 RGB in 0..1, shape (H, W, 3). Points are (x, y) pixels.
"""
import cv2
import numpy as np

# Why: cv2 antialiasing alone leaves stair-steps on long shallow curves.
SUPERSAMPLE = 3
# cv2 takes fixed-point coordinates; 4 bits = 1/16 px precision.
SUBPIXEL_BITS = 4
SUBPIXEL_SCALE = 1 << SUBPIXEL_BITS


# ----------------------------------------------------------------- colour
def rgb(hex_color):
    """'#RRGGBB' -> float32 array in 0..1."""
    value = hex_color.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def mix(color_a, color_b, amount):
    """Linear blend of two colours (or images)."""
    return color_a + (color_b - color_a) * amount


# ------------------------------------------------------------------ curves
def smooth(points, samples=14, alpha=0.5, closed=False):
    """Centripetal Catmull-Rom spline through the control points (any dimension).

    Why centripetal: it never overshoots or loops on unevenly spaced points,
    which hand-placed anatomy points always are. `closed` returns a loop.
    """
    ctrl = np.asarray(points, np.float64)
    if len(ctrl) < 3:
        steps = np.linspace(0.0, 1.0, samples)[:, None]
        return ctrl[0] + (ctrl[-1] - ctrl[0]) * steps
    if closed:
        ctrl = np.vstack([ctrl[-1], ctrl, ctrl[0], ctrl[1]])
    else:
        ctrl = np.vstack([2 * ctrl[0] - ctrl[1], ctrl, 2 * ctrl[-1] - ctrl[-2]])
    pieces = []
    for i in range(len(ctrl) - 3):
        p0, p1, p2, p3 = ctrl[i:i + 4]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        t = np.linspace(t1, t2, samples, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        pieces.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    pieces.append(ctrl[-2][None, :])
    return np.vstack(pieces)


def resample(path, count):
    """Re-space a polyline to `count` points at equal arc length."""
    path = np.asarray(path, np.float64)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    dist = np.concatenate([[0.0], np.cumsum(seg)])
    target = np.linspace(0.0, dist[-1], count)
    return np.stack([np.interp(target, dist, path[:, k]) for k in range(path.shape[1])], axis=1)


def join(*paths):
    """Concatenate paths into one outline; the seams stay as sharp corners."""
    return np.vstack([np.asarray(p, np.float64) for p in paths])


def ellipse(center, radius_x, radius_y, count=48, angle_deg=0.0):
    """Closed ellipse outline."""
    t = np.linspace(0.0, 2 * np.pi, count, endpoint=False)
    pts = np.stack([np.cos(t) * radius_x, np.sin(t) * radius_y], axis=1)
    rot = np.deg2rad(angle_deg)
    turn = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
    return pts @ turn.T + np.asarray(center, np.float64)


def taper(count, start=0.0, end=0.0, peak_at=0.5, power=1.0):
    """Width profile 0..1 along a stroke: `start` -> 1 at `peak_at` -> `end`.

    Why: a line that swells and thins reads as hand-drawn; constant width reads as CAD.
    """
    t = np.linspace(0.0, 1.0, count)
    rise = start + (1 - start) * np.sin(0.5 * np.pi * np.clip(t / max(peak_at, 1e-6), 0, 1)) ** power
    fall = end + (1 - end) * np.sin(0.5 * np.pi * np.clip((1 - t) / max(1 - peak_at, 1e-6), 0, 1)) ** power
    return np.where(t <= peak_at, rise, fall)


# ------------------------------------------------------------------- masks
def _crop_box(points, shape, pad):
    height, width = shape
    x0 = int(max(np.floor(points[:, 0].min()) - pad, 0))
    y0 = int(max(np.floor(points[:, 1].min()) - pad, 0))
    x1 = int(min(np.ceil(points[:, 0].max()) + pad, width))
    y1 = int(min(np.ceil(points[:, 1].max()) + pad, height))
    return x0, y0, x1, y1


def fill(shape, polygon):
    """Antialiased coverage mask of one closed polygon. shape = (H, W)."""
    polygon = np.asarray(polygon, np.float64)[:, :2]
    out = np.zeros(shape, np.float32)
    x0, y0, x1, y1 = _crop_box(polygon, shape, 2)
    if x1 <= x0 or y1 <= y0:
        return out
    big = np.zeros(((y1 - y0) * SUPERSAMPLE, (x1 - x0) * SUPERSAMPLE), np.uint8)
    local = (polygon - [x0, y0]) * SUPERSAMPLE * SUBPIXEL_SCALE
    cv2.fillPoly(big, [np.round(local).astype(np.int32)], 255, lineType=cv2.LINE_AA, shift=SUBPIXEL_BITS)
    small = cv2.resize(big, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    out[y0:y1, x0:x1] = small.astype(np.float32) / 255.0
    return out


def fill_many(shape, polygons):
    """Union mask of several polygons."""
    out = np.zeros(shape, np.float32)
    for polygon in polygons:
        np.maximum(out, fill(shape, polygon), out=out)
    return out


def stroke(shape, path, widths):
    """Antialiased mask of a variable-width stroke.

    How: one thick round-capped segment per step. A ribbon polygon would be
    shorter code but self-intersects (and punches holes) on tight curves.
    """
    path = np.asarray(path, np.float64)[:, :2]
    widths = np.broadcast_to(np.asarray(widths, np.float64), (len(path),))
    out = np.zeros(shape, np.float32)
    x0, y0, x1, y1 = _crop_box(path, shape, int(widths.max()) + 3)
    if x1 <= x0 or y1 <= y0:
        return out
    big = np.zeros(((y1 - y0) * SUPERSAMPLE, (x1 - x0) * SUPERSAMPLE), np.uint8)
    local = np.round((path - [x0, y0]) * SUPERSAMPLE * SUBPIXEL_SCALE).astype(np.int32)
    for i in range(len(local) - 1):
        thickness = int(round(0.5 * (widths[i] + widths[i + 1]) * SUPERSAMPLE))
        if thickness < 1:
            continue
        cv2.line(big, tuple(local[i]), tuple(local[i + 1]), 255, thickness,
                 lineType=cv2.LINE_AA, shift=SUBPIXEL_BITS)
    small = cv2.resize(big, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    out[y0:y1, x0:x1] = small.astype(np.float32) / 255.0
    return out


def stroke_many(shape, strokes):
    """Union mask of (path, widths) pairs."""
    out = np.zeros(shape, np.float32)
    for path, widths in strokes:
        np.maximum(out, stroke(shape, path, widths), out=out)
    return out


def shift(mask, dx, dy):
    """Translate a mask (used for cast shadows and offset highlights)."""
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(mask, matrix, (mask.shape[1], mask.shape[0]))


def blur(field, sigma):
    """Gaussian blur of a mask or image."""
    if sigma <= 0:
        return field
    return cv2.GaussianBlur(field, (0, 0), sigma)


def smoothstep(field, low, high):
    """Soft threshold: 0 below `low`, 1 above `high`."""
    t = np.clip((field - low) / max(high - low, 1e-6), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# -------------------------------------------------------------- compositing
def mask_box(mask, pad=0):
    """(row slice, column slice) of the rectangle that holds every non-zero pixel, or None if empty.

    Why: most layers touch a small part of the canvas; blending only that
    rectangle makes a picture of hundreds of layers many times faster.
    """
    rows = np.flatnonzero(mask.any(axis=1))
    if len(rows) == 0:
        return None
    cols = np.flatnonzero(mask.any(axis=0))
    height, width = mask.shape
    return (slice(max(rows[0] - pad, 0), min(rows[-1] + 1 + pad, height)),
            slice(max(cols[0] - pad, 0), min(cols[-1] + 1 + pad, width)))


def _window(image, color, mask):
    """Crop image, colour and mask to the mask's bounding box."""
    box = mask_box(mask)
    if box is None:
        return None
    color = np.asarray(color)
    return image[box], (color[box] if color.ndim == 3 else color), mask[box]


def over(image, color, mask, opacity=1.0):
    """Normal blend: lay `color` (RGB or image) on `image` through `mask`. In place."""
    window = _window(image, color, mask)
    if window is not None:
        target, tint, cover = window
        target += (tint - target) * (cover * opacity)[..., None]
    return image


def multiply(image, color, mask, opacity=1.0):
    """Multiply blend: darken toward `color` through `mask`. In place."""
    window = _window(image, color, mask)
    if window is not None:
        target, tint, cover = window
        target *= 1.0 - (cover * opacity)[..., None] * (1.0 - tint)
    return image


def screen(image, color, mask, opacity=1.0):
    """Screen blend: lighten toward white by `color` through `mask`. In place."""
    window = _window(image, color, mask)
    if window is not None:
        target, tint, cover = window
        target += (1.0 - target) * tint * (cover * opacity)[..., None]
    return image


# ------------------------------------------------------------------ fields
def noise(shape, cell, seed, octaves=3):
    """Smooth value noise in 0..1; `cell` = size in px of the largest blobs."""
    rng = np.random.default_rng(seed)
    height, width = shape
    total = np.zeros(shape, np.float32)
    weight_sum = 0.0
    for octave in range(octaves):
        size = max(cell / (2 ** octave), 1.0)
        grid = rng.random((int(height / size) + 2, int(width / size) + 2)).astype(np.float32)
        layer = cv2.resize(grid, (width, height), interpolation=cv2.INTER_CUBIC)
        weight = 0.5 ** octave
        total += layer * weight
        weight_sum += weight
    return np.clip(total / weight_sum, 0.0, 1.0)


def inflate_normals(mask, sigma):
    """Pseudo surface normals of a flat shape, as if it were a puffed cushion.

    How: blur the mask into a height dome, take its slope. This is the idea of
    Johnston's Lumo (2002): a 2D region outline is enough to fake 3D lighting.
    Returns (nx, ny, nz) fields.
    """
    height = blur(mask, sigma)
    slope_x = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) * sigma
    slope_y = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) * sigma
    nz = np.ones_like(height) * 0.5
    norm = np.sqrt(slope_x ** 2 + slope_y ** 2 + nz ** 2)
    return -slope_x / norm, -slope_y / norm, nz / norm


def lambert(mask, light, sigma):
    """Light amount 0..1 on an inflated shape; `light` = (x, y, z) toward the lamp."""
    nx, ny, nz = inflate_normals(mask, sigma)
    lx, ly, lz = np.asarray(light, np.float32) / np.linalg.norm(light)
    return np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)


# ---------------------------------------------------------------------- io
def save(path, image):
    """Write a float RGB image as PNG."""
    data = (np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(data, cv2.COLOR_RGB2BGR))
