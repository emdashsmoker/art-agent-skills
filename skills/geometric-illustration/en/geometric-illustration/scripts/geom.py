"""Curve and stroke geometry.

Why: every visible mark in the picture (face contour, hair clump, lash line)
is a curve. Keeping curve math in one module lets the rig modules describe
shapes with a handful of control points instead of raw pixel lists.
"""
import numpy as np

SAMPLES_PER_SEGMENT = 18
CENTRIPETAL_ALPHA = 0.5  # 0.5 avoids cusps and self-intersections (Yuksel et al. 2011)
EPS = 1e-6


def catmull_rom(points, closed=False, samples=SAMPLES_PER_SEGMENT):
    """Smooth curve passing through every control point.

    How: centripetal Catmull-Rom was chosen over Bezier because a curve that
    passes through its control points is easier to author by coordinates.
    """
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return pts.copy()
    if closed:
        ext = np.vstack([pts[-1], pts, pts[0], pts[1]])
    else:
        ext = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    out = []
    for i in range(len(ext) - 3):
        out.append(_segment(ext[i:i + 4], samples))
    if not closed:
        out.append(pts[-1:])
    return np.vstack(out)


def _segment(p, samples):
    p0, p1, p2, p3 = p
    t0 = 0.0
    t1 = t0 + max(np.linalg.norm(p1 - p0) ** CENTRIPETAL_ALPHA, EPS)
    t2 = t1 + max(np.linalg.norm(p2 - p1) ** CENTRIPETAL_ALPHA, EPS)
    t3 = t2 + max(np.linalg.norm(p3 - p2) ** CENTRIPETAL_ALPHA, EPS)
    t = np.linspace(t1, t2, samples, endpoint=False)[:, None]
    a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
    a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
    a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
    b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
    b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
    return (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2


def bezier(p0, p1, p2, p3, n=40):
    """Cubic Bezier, used where tangent control matters more than pass-through."""
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def ellipse(cx, cy, rx, ry, n=72, rot=0.0, start=0.0, end=2 * np.pi):
    a = np.linspace(start, end, n, endpoint=(end - start) < 2 * np.pi - EPS)
    x, y = rx * np.cos(a), ry * np.sin(a)
    c, s = np.cos(rot), np.sin(rot)
    return np.stack([cx + x * c - y * s, cy + x * s + y * c], axis=1)


def arc_length(path):
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(path, n):
    """Even spacing keeps stroke width profiles independent of control point density."""
    s = arc_length(path)
    if s[-1] < EPS:
        return np.repeat(path[:1], n, axis=0)
    target = np.linspace(0, s[-1], n)
    return np.stack([np.interp(target, s, path[:, 0]), np.interp(target, s, path[:, 1])], axis=1)


def sub_path(path, t0, t1):
    """Portion of a path between normalized arc-length positions t0..t1."""
    s = arc_length(path)
    total = max(s[-1], EPS)
    n = max(int(len(path) * abs(t1 - t0)) + 2, 4)
    target = np.linspace(t0 * total, t1 * total, n)
    return np.stack([np.interp(target, s, path[:, 0]), np.interp(target, s, path[:, 1])], axis=1)


def normals(path):
    d = np.gradient(path, axis=0)
    length = np.linalg.norm(d, axis=1, keepdims=True)
    d = d / np.maximum(length, EPS)
    return np.stack([-d[:, 1], d[:, 0]], axis=1)


def taper(n, start=0.2, end=0.3, floor=0.0, power=1.0):
    """Pen-pressure profile in [floor, 1]: ramps in and out like a real stroke."""
    t = np.linspace(0, 1, n)
    up = np.clip(t / max(start, EPS), 0, 1) if start > 0 else np.ones(n)
    down = np.clip((1 - t) / max(end, EPS), 0, 1) if end > 0 else np.ones(n)
    prof = _smoothstep(np.minimum(up, down)) ** power
    return floor + (1 - floor) * prof


def _smoothstep(x):
    return x * x * (3 - 2 * x)


def stroke_polygon(path, widths):
    """Outline polygon of a variable-width stroke (widths = full width per point).

    The result is left edge forward + right edge backward, which raster.stroke_mask
    fills quad by quad (see Drawable.fill_mode='union').
    """
    path = np.asarray(path, float)
    w = np.broadcast_to(np.asarray(widths, float), (len(path),))
    nrm = normals(path)
    left = path + nrm * (w[:, None] / 2)
    right = path - nrm * (w[:, None] / 2)
    return np.vstack([left, right[::-1]])
