"""Path construction helpers.

Why: artists think in "smooth run, sharp corner, tapered line". These helpers let
scene code say that directly; the bezier handles are derived from the points.
All coordinates are design units (the Canvas applies the device scale).
"""
import math

import numpy as np
import skia

CATMULL_HANDLE = 1.0 / 6.0     # Catmull-Rom to cubic-bezier handle length
SAMPLES_PER_SEGMENT = 12


def _handles(p0, p1, p2, p3):
    c1 = (p1[0] + (p2[0] - p0[0]) * CATMULL_HANDLE, p1[1] + (p2[1] - p0[1]) * CATMULL_HANDLE)
    c2 = (p2[0] - (p3[0] - p1[0]) * CATMULL_HANDLE, p2[1] - (p3[1] - p1[1]) * CATMULL_HANDLE)
    return c1, c2


def _append_run(path, points):
    count = len(points)
    for i in range(count - 1):
        c1, c2 = _handles(points[max(i - 1, 0)], points[i], points[i + 1], points[min(i + 2, count - 1)])
        path.cubicTo(c1[0], c1[1], c2[0], c2[1], points[i + 1][0], points[i + 1][1])


def runs(run_list, closed=True):
    """Path from smooth runs. Each run is a list of points; runs join at sharp corners."""
    path = skia.Path()
    path.moveTo(*run_list[0][0])
    for run in run_list:
        _append_run(path, [tuple(p) for p in run])
    if closed:
        path.close()
    return path


def blob(points):
    """Fully smooth closed curve through points (no corners)."""
    pts = [tuple(p) for p in points]
    count = len(pts)
    path = skia.Path()
    path.moveTo(*pts[0])
    for i in range(count):
        c1, c2 = _handles(pts[(i - 1) % count], pts[i], pts[(i + 1) % count], pts[(i + 2) % count])
        path.cubicTo(c1[0], c1[1], c2[0], c2[1], *pts[(i + 1) % count])
    path.close()
    return path


def polygon(points):
    path = skia.Path()
    path.addPoly([skia.Point(float(x), float(y)) for x, y in points], True)
    return path


def ellipse(cx, cy, rx, ry=None, angle=0.0):
    ry = rx if ry is None else ry
    path = skia.Path()
    path.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    return rotate(path, angle, (cx, cy)) if angle else path


def rect(x0, y0, x1, y1, radius=0.0):
    path = skia.Path()
    if radius:
        path.addRoundRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), radius, radius)
    else:
        path.addRect(skia.Rect.MakeLTRB(x0, y0, x1, y1))
    return path


def sample(points, per_segment=SAMPLES_PER_SEGMENT):
    """Polyline samples along a smooth run."""
    pts = np.asarray(points, np.float64)
    count = len(pts)
    if count < 2:
        return pts
    out = []
    for i in range(count - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, count - 1)]
        c1 = p1 + (p2 - p0) * CATMULL_HANDLE
        c2 = p2 - (p3 - p1) * CATMULL_HANDLE
        for t in np.linspace(0, 1, per_segment, endpoint=(i == count - 2)):
            u = 1 - t
            out.append(u ** 3 * p1 + 3 * u * u * t * c1 + 3 * u * t * t * c2 + t ** 3 * p2)
    return np.asarray(out)


def taper(points, width, start=0.0, end=0.0, peak=0.5, smooth=True):
    """Closed outline of a pen-like stroke that swells toward `peak` and tapers at the tips.

    start / end are the width fractions kept at each tip (0 = needle point, 1 = blunt).
    """
    line = sample(points) if smooth else np.asarray(points, np.float64)
    tangent = np.gradient(line, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    t = np.linspace(0, 1, len(line))
    rise = start + (1 - start) * np.sin(np.clip(t / max(peak, 1e-6), 0, 1) * math.pi / 2)
    fall = end + (1 - end) * np.sin(np.clip((1 - t) / max(1 - peak, 1e-6), 0, 1) * math.pi / 2)
    half = 0.5 * width * np.where(t < peak, rise, fall)
    outline = np.concatenate([line + normal * half[:, None], (line - normal * half[:, None])[::-1]])
    return polygon(outline)


def ribbon(points, widths):
    """Stroke outline with an explicit width at every control point (hair locks, folds)."""
    line = sample(points)
    t_ctrl = np.linspace(0, 1, len(widths))
    half = 0.5 * np.interp(np.linspace(0, 1, len(line)), t_ctrl, widths)
    tangent = np.gradient(line, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    outline = np.concatenate([line + normal * half[:, None], (line - normal * half[:, None])[::-1]])
    return polygon(outline)


def mirror(points, axis_x):
    return [(2 * axis_x - x, y) for x, y in points]


def symmetric(half_points, axis_x):
    """Closed point loop from one half (listed top to bottom); on-axis points are not doubled."""
    half = [tuple(p) for p in half_points]
    other = [p for p in mirror(half, axis_x)[::-1] if abs(p[0] - axis_x) > 1e-6]
    return half + other


def offset(path, dx, dy):
    moved = skia.Path(path)
    moved.offset(dx, dy)
    return moved


def rotate(path, degrees, pivot):
    matrix = skia.Matrix()
    matrix.setRotate(degrees, pivot[0], pivot[1])
    moved = skia.Path(path)
    moved.transform(matrix)
    return moved


def scale(path, sx, sy=None, pivot=(0.0, 0.0)):
    matrix = skia.Matrix()
    matrix.setScale(sx, sx if sy is None else sy, pivot[0], pivot[1])
    moved = skia.Path(path)
    moved.transform(matrix)
    return moved


def union(*paths):
    result = paths[0]
    for other in paths[1:]:
        result = skia.Op(result, other, skia.kUnion_PathOp)
    return result


def intersect(a, b):
    return skia.Op(a, b, skia.kIntersect_PathOp)


def subtract(a, b):
    return skia.Op(a, b, skia.kDifference_PathOp)


def contour_path(mask, level=0.5, simplify=1.2, smooth=True, min_area=30.0):
    """Trace a mask outline back into a path (device pixels). Used to redraw rasters as clean shapes."""
    import cv2
    binary = (mask > level).astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    path = skia.Path()
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        approx = cv2.approxPolyDP(contour, simplify, True)[:, 0, :].astype(float)
        if len(approx) < 3:
            continue
        path.addPath(blob(approx) if smooth and len(approx) > 3 else polygon(approx))
    return path
