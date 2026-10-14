"""Curve construction. Everything is in canvas units (canvas width = 1000).

A control point is (x, y) or (x, y, True). The third element marks a sharp
corner: the curve is smooth everywhere except at corners.
"""
import numpy as np

DEFAULT_SAMPLES_PER_SEGMENT = 16


def _split_flags(points):
    xy = np.array([[p[0], p[1]] for p in points], float)
    corner = np.array([len(p) > 2 and bool(p[2]) for p in points])
    return xy, corner


def _catmull_rom(xy, samples):
    """Open Catmull-Rom curve through every row of xy."""
    if len(xy) < 3:
        return xy.copy()
    padded = np.vstack([xy[0], xy, xy[-1]])
    t = np.linspace(0, 1, samples, endpoint=False)[:, None]
    pieces = []
    for i in range(len(xy) - 1):
        p0, p1, p2, p3 = padded[i:i + 4]
        pieces.append(0.5 * (2 * p1 + (p2 - p0) * t
                             + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                             + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    pieces.append(xy[-1:])
    return np.vstack(pieces)


def _catmull_rom_loop(xy, samples):
    """Closed Catmull-Rom curve with no corners."""
    wrapped = np.vstack([xy[-1], xy, xy[0], xy[1]])
    t = np.linspace(0, 1, samples, endpoint=False)[:, None]
    pieces = []
    for i in range(len(xy)):
        p0, p1, p2, p3 = wrapped[i:i + 4]
        pieces.append(0.5 * (2 * p1 + (p2 - p0) * t
                             + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                             + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    return np.vstack(pieces)


def spline(points, closed=False, samples=DEFAULT_SAMPLES_PER_SEGMENT):
    """Dense curve through control points, smooth except at flagged corners."""
    xy, corner = _split_flags(points)
    if closed and not corner.any():
        return _catmull_rom_loop(xy, samples)
    if closed:
        first = int(np.argmax(corner))          # start the loop on a corner
        xy = np.vstack([np.roll(xy, -first, axis=0), xy[first]])
        corner = np.append(np.roll(corner, -first), True)
    cuts = [0] + [i for i in range(1, len(xy) - 1) if corner[i]] + [len(xy) - 1]
    sections = [_catmull_rom(xy[a:b + 1], samples) for a, b in zip(cuts[:-1], cuts[1:])]
    return np.vstack([s[:-1] for s in sections[:-1]] + [sections[-1]])


def ellipse(cx, cy, rx, ry, angle=0.0, samples=72):
    """Dense closed ellipse; angle in degrees, clockwise on screen."""
    t = np.linspace(0, 2 * np.pi, samples, endpoint=False)
    pts = np.stack([rx * np.cos(t), ry * np.sin(t)], axis=1)
    return rotate(pts, angle, (0, 0)) + (cx, cy)


def mirror(points, axis_x):
    """Mirror control points left-right about x = axis_x, keeping corner flags."""
    return [(2 * axis_x - p[0], *p[1:]) for p in points]


def symmetric(half_points, axis_x):
    """Closed control polygon from one half: the half, then its mirror reversed.

    Points lying on the axis are not duplicated.
    """
    other = [p for p in mirror(half_points, axis_x) if abs(p[0] - axis_x) > 1e-6]
    return list(half_points) + other[::-1]


def rotate(points, degrees, center):
    """Rotate a dense (N, 2) array about center; positive is clockwise on screen."""
    a = np.radians(degrees)
    matrix = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (np.asarray(points, float) - center) @ matrix.T + center


def resample(points, step):
    """Re-space a dense curve so consecutive points are about `step` apart.

    Extra columns beyond x and y (such as a width) are carried along.
    """
    points = np.asarray(points, float)
    seg = np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1)
    dist = np.concatenate([[0], np.cumsum(seg)])
    if dist[-1] <= 0:
        return points[:1]
    count = max(int(dist[-1] / step) + 1, 2)
    at = np.linspace(0, dist[-1], count)
    return np.stack([np.interp(at, dist, points[:, k]) for k in range(points.shape[1])], axis=1)


def tube(points, samples=DEFAULT_SAMPLES_PER_SEGMENT):
    """Dense centre line with a width at every point, for limbs, fingers, trunks.

    Control points are (x, y, width). Returns an (N, 3) array of x, y, width.
    """
    points = np.asarray(points, float)
    centre = _catmull_rom(points[:, :2], samples)
    width = _catmull_rom(np.stack([points[:, 2], np.zeros(len(points))], axis=1), samples)[:, 0]
    return np.column_stack([centre, np.maximum(width, 0.0)])
