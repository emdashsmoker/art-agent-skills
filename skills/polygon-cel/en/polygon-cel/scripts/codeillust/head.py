"""Head construction: skull + jaw silhouette, ears.

How: the silhouette is the union of the projected cranium sphere (always a
circle under orthographic projection) and a smooth jaw loop through 3D
landmarks. The union is taken per scanline, which is exact for these
y-monotone shapes and needs no polygon boolean library.
"""
import cv2
import numpy as np

from . import config as cfg
from . import geom


def _x_extent(P, y):
    x0, y0 = P[:, 0], P[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    hit = (y0 <= y) != (y1 <= y)
    if not np.any(hit):
        return None
    t = (y - y0[hit]) / (y1[hit] - y0[hit])
    xs = x0[hit] + t * (x1[hit] - x0[hit])
    return xs.min(), xs.max()


def jaw_loop3d(shape, length=1.0):
    right = [(x, cfg.JAW_TOP + (y - cfg.JAW_TOP) * length, z) for x, y, z in cfg.JAW.get(shape, cfg.JAW["oval"])]
    left = [(-x, y, z) for x, y, z in reversed(right)]
    chin = right[-1]
    center = (0.0, chin[1] + 0.006, chin[2] + 0.01)
    return [(0.0, 0.36, 0.22)] + right + [center] + left


def head_outline(rig, shape="oval", length=1.0):
    """Projected head-local 2D silhouette polygon (skull + face); length stretches the jaw."""
    jaw2 = rig.rot3(jaw_loop3d(shape, length))[:, :2]
    jaw2 = geom.catmull_rom(jaw2, n_per_seg=16, closed=True)
    c = rig.rot3([(0.0, cfg.CRANIUM_Y, 0.0)])[0, :2]
    R = cfg.CRANIUM_R
    y_top, y_bot = c[1] - R, jaw2[:, 1].max()
    ys = np.linspace(y_top + 1e-4, y_bot - 1e-4, 520)
    left, right = [], []
    for y in ys:
        ext = []
        if abs(y - c[1]) < R:
            dx = np.sqrt(R * R - (y - c[1]) ** 2)
            ext.append((c[0] - dx, c[0] + dx))
        j = _x_extent(jaw2, y)
        if j is not None:
            ext.append(j)
        if not ext:
            continue
        left.append((min(e[0] for e in ext), y))
        right.append((max(e[1] for e in ext), y))
    P = np.vstack([[c[0], y_top], np.array(left), [[np.mean([left[-1][0], right[-1][0]]), y_bot]],
                   np.array(right)[::-1]])
    # Why convex hull: the raw union has a small concave notch where skull and
    # jaw meet; anime heads read as convex, and the far-cheek bump survives
    # as a hull vertex.
    hull = cv2.convexHull(P.astype(np.float32))[:, 0, :].astype(np.float64)
    P = geom.resample(hull, 0.004, closed=True)
    k = 4
    Ps = np.stack([np.convolve(np.r_[P[-k:, i], P[:, i], P[:k, i]], np.ones(2 * k + 1) / (2 * k + 1), "valid")
                   for i in range(2)], axis=1)
    return Ps


def ear_polys(rig):
    """Both ears as canvas polygons (drawn behind the face)."""
    shape = np.array([(0.0, -0.078), (0.030, -0.090), (0.052, -0.060), (0.050, 0.000),
                      (0.036, 0.055), (0.012, 0.085), (-0.012, 0.070), (-0.020, 0.0)])
    out = []
    for side in (-1, 1):
        anchor = rig.rot3([(side * 0.372, 0.655, -0.02)])[0, :2]
        sx = max(np.cos(rig.yaw + side * 0.35), 0.25)
        P = shape.copy()
        P[:, 0] *= side * sx
        out.append(rig.head2(geom.catmull_rom(anchor + P, 8, closed=True)))
    return out
