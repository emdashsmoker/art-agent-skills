"""Masks: shapes become float32 (H, W) arrays in 0..1, and everything else
(shadows, highlights, clipping) is arithmetic on those arrays.

Set operations:  intersection a*b   union np.maximum(a,b)   difference a*(1-b)
"""
import cv2
import numpy as np

from . import config, geometry

# cv2 drawing takes fixed-point coordinates; 4 fractional bits = 1/16 px precision.
_SHIFT_BITS = 4
_FIXED = 1 << _SHIFT_BITS


def _fixed(points, supersample):
    return np.round(np.asarray(points, np.float64) * supersample * _FIXED).astype(np.int32)


def _downsample(big, size):
    width, height = size
    small = cv2.resize(big, (width, height), interpolation=cv2.INTER_AREA)
    return small.astype(np.float32) / 255.0


def polygon_mask(size, polygons):
    """Fill one or more polygons (list of (N,2) arrays) into a mask."""
    width, height = size
    ss = config.SUPERSAMPLE
    big = np.zeros((height * ss, width * ss), np.uint8)
    for poly in polygons:
        if len(poly) >= 3:
            cv2.fillPoly(big, [_fixed(poly, ss)], 255, lineType=cv2.LINE_AA, shift=_SHIFT_BITS)
    return _downsample(big, size)


def blob_mask(size, points, smooth=True):
    """Closed shape through control points (smooth) or straight polygon."""
    outline = geometry.spline(points, closed=True) if smooth else np.asarray(points, np.float64)
    return polygon_mask(size, [outline])


def ellipse_mask(size, cx, cy, rx, ry, rotation_deg=0.0):
    return polygon_mask(size, [geometry.ellipse_points(cx, cy, rx, ry, rotation_deg, 96)])


def ribbon_pieces(points, width, profile='taper', smooth=True):
    """Centerline + half-widths for a variable-width band.

    points: control points of the centerline. width: full width in px at profile=1.
    Returns (centers (N,2), half_widths (N,)).
    """
    line = geometry.spline(points) if smooth and len(points) > 2 else np.asarray(points, np.float64)
    line = geometry.resample(line, step=config.RIBBON_STEP_PX)
    half = 0.5 * width * geometry.width_along(profile, len(line))
    return line, half


def contour_pieces(points, left, right, bend=0.0):
    """Centerline + separate half-widths for a band whose two edges differ (a limb, a vase side).

    points: polyline of the centerline (joints). left / right: [(t, distance_px), ...]
    with t in 0..1 along the line; "left" is the left-hand side when walking from the
    first point to the last. bend: px radius that rounds the corners of the centerline.
    Returns (centers (N,2), left_half (N,), right_half (N,)).
    """
    line = geometry.resample(np.asarray(points, np.float64), step=config.RIBBON_STEP_PX)
    if bend > 0 and len(line) > 4:
        sigma = bend / config.RIBBON_STEP_PX
        reach = int(sigma * 3) + 1
        axis = np.arange(-reach, reach + 1)
        kernel = np.exp(-0.5 * (axis / sigma) ** 2)
        kernel /= kernel.sum()
        # Extend both ends in a straight line so smoothing leaves the end points in place.
        head = line[0] + (line[0] - line[1]) * np.arange(reach, 0, -1)[:, None]
        tail = line[-1] + (line[-1] - line[-2]) * np.arange(1, reach + 1)[:, None]
        padded = np.vstack([head, line, tail])
        line = np.stack([np.convolve(padded[:, k], kernel, mode='valid') for k in (0, 1)], axis=1)
    t = geometry.arc_length(line)
    t = t / max(t[-1], 1e-6)
    halves = []
    for side in (left, right):
        stations = np.asarray(side, np.float64)
        halves.append(np.interp(t, stations[:, 0], stations[:, 1]))
    return line, halves[0], halves[1]


def ribbon_mask(size, strokes):
    """Rasterize ribbons. strokes: list of (centers, half_widths), or
    (centers, left_half_widths, right_half_widths) for bands with unequal sides.

    Each segment is drawn as a convex quad plus a round join. One big outline
    polygon would be faster but tears where a wide band curves tightly.
    """
    width, height = size
    ss = config.SUPERSAMPLE
    big = np.zeros((height * ss, width * ss), np.uint8)
    for stroke in strokes:
        line, half_left = stroke[0], stroke[1]
        half_right = stroke[2] if len(stroke) > 2 else half_left
        if len(line) < 2:
            continue
        normal = geometry.normals(line)
        left = _fixed(line + normal * half_left[:, None], ss)
        right = _fixed(line - normal * half_right[:, None], ss)
        center = _fixed(line, ss)
        radius = np.round(np.minimum(half_left, half_right) * ss * _FIXED).astype(np.int32)
        for i in range(len(line) - 1):
            quad = np.array([left[i], left[i + 1], right[i + 1], right[i]], np.int32)
            cv2.fillPoly(big, [quad], 255, lineType=cv2.LINE_AA, shift=_SHIFT_BITS)
            if radius[i] > _FIXED // 2:
                cv2.circle(big, tuple(int(v) for v in center[i]), int(radius[i]), 255, -1,
                           lineType=cv2.LINE_AA, shift=_SHIFT_BITS)
    return _downsample(big, size)


# --- mask operations --------------------------------------------------------

def blur(mask, radius):
    """Gaussian blur; radius is the sigma in px. Works on masks and images."""
    if radius <= 0:
        return mask
    return cv2.GaussianBlur(mask, (0, 0), float(radius))


def shift(mask, dx, dy):
    """Translate a mask. Edge pixels are repeated, because a shape cut by the
    canvas border continues outside it; an empty border would fake a shadow there."""
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(mask, matrix, (mask.shape[1], mask.shape[0]),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def fill_holes(mask, threshold=0.5):
    """Fill the gaps a mask encloses completely (pin holes, islands of background inside a shape);
    gaps that open to the outside stay open."""
    solid = (mask > threshold).astype(np.uint8)
    padded = np.pad(1 - solid, 1, constant_values=1)            # a border of background around everything
    outside = np.zeros((padded.shape[0] + 2, padded.shape[1] + 2), np.uint8)
    cv2.floodFill(padded, outside, (0, 0), 2)
    enclosed = (padded[1:-1, 1:-1] == 1).astype(np.float32)
    return np.maximum(mask, enclosed)


def grow(mask, px):
    """Expand (px > 0) or shrink (px < 0) a mask by about |px| pixels."""
    if px == 0:
        return mask
    size = int(abs(px) * 2 + 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    return cv2.dilate(mask, kernel) if px > 0 else cv2.erode(mask, kernel)


def smoothstep(field, low, high):
    t = np.clip((field - low) / max(high - low, 1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def contours(mask, min_points=12, smoothing=4.0):
    """Closed outline polylines of a mask, smoothed to remove pixel stair-steps."""
    binary = (mask > 0.5).astype(np.uint8)
    found, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    lines = []
    for contour in found:
        pts = contour[:, 0, :].astype(np.float64) + 0.5
        if len(pts) < min_points:
            continue
        kernel_size = int(smoothing * 6) | 1
        if len(pts) > kernel_size:
            axis = np.arange(kernel_size) - kernel_size // 2
            kernel = np.exp(-0.5 * (axis / smoothing) ** 2)
            kernel /= kernel.sum()
            pad = kernel_size // 2
            wrapped = np.vstack([pts[-pad:], pts, pts[:pad]])
            pts = np.stack([np.convolve(wrapped[:, k], kernel, mode='valid') for k in (0, 1)], axis=1)
        lines.append(pts)
    return lines


# --- scalar fields ----------------------------------------------------------

def _grid(size):
    width, height = size
    return np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))


def linear_field(size, p0, p1):
    """0 at p0 rising to 1 at p1 (clamped), constant across the perpendicular."""
    xs, ys = _grid(size)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    t = ((xs - p0[0]) * dx + (ys - p0[1]) * dy) / max(dx * dx + dy * dy, 1e-6)
    return np.clip(t, 0.0, 1.0)


def radial_field(size, center, rx, ry=None, rotation_deg=0.0):
    """1 at center falling to 0 at the ellipse edge."""
    xs, ys = _grid(size)
    ry = ry or rx
    a = np.radians(rotation_deg)
    x, y = xs - center[0], ys - center[1]
    u = (x * np.cos(a) + y * np.sin(a)) / rx
    v = (-x * np.sin(a) + y * np.cos(a)) / ry
    return np.clip(1.0 - np.sqrt(u * u + v * v), 0.0, 1.0)


def noise_field(size, scale=64.0, octaves=4, seed=None, stretch=(1.0, 1.0)):
    """Smooth fractal value noise in 0..1. scale = size in px of the largest blobs.

    stretch=(sx, sy) elongates the noise, e.g. (6, 1) for horizontal streaks.
    """
    width, height = size
    rng = np.random.default_rng(config.DEFAULT_SEED if seed is None else seed)
    total = np.zeros((height, width), np.float32)
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        cell = max(scale / (2 ** octave), 1.0)
        gw = max(int(np.ceil(width / (cell * stretch[0]))) + 2, 2)
        gh = max(int(np.ceil(height / (cell * stretch[1]))) + 2, 2)
        grid = rng.random((gh, gw), dtype=np.float32)
        layer = cv2.resize(grid, (width, height), interpolation=cv2.INTER_CUBIC)
        total += amplitude * layer
        weight += amplitude
        amplitude *= 0.5
    return np.clip(total / weight, 0.0, 1.0)
