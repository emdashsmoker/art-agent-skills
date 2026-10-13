"""2D construction geometry: curves, ribbons, transforms.

Everything is a polyline (N x 2 float array, x right, y down, pixels).
"""
import numpy as np
from scipy.interpolate import PchipInterpolator


def pts(p):
    return np.asarray(p, dtype=np.float64).reshape(-1, 2)


def catmull_rom(points, closed=False, samples=14):
    """Smooth curve through the control points.

    Repeat a control point twice to get a sharp corner there.
    """
    p = pts(points)
    if closed:
        p = np.vstack([p[-1], p, p[0], p[1]])
    else:
        p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    t = np.linspace(0, 1, samples, endpoint=False)[:, None]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        out.append(0.5 * (2 * p1 + (p2 - p0) * t
                          + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out = np.vstack(out)
    if not closed:
        out = np.vstack([out, p[-2]])
    return out


def bezier(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(q, float) for q in (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def ellipse(cx, cy, rx, ry, rot=0.0, n=48):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x, y = rx * np.cos(a), ry * np.sin(a)
    c, s = np.cos(rot), np.sin(rot)
    return np.stack([cx + x * c - y * s, cy + x * s + y * c], 1)


def transform(p, scale=1.0, rotate=0.0, translate=(0, 0), origin=(0, 0), mirror=False):
    """Scale and rotate about origin, then translate. rotate in radians, clockwise on screen."""
    q = pts(p) - origin
    if mirror:
        q = q * [-1, 1]
    q = q * scale
    c, s = np.cos(rotate), np.sin(rotate)
    q = np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c], 1)
    return q + origin + translate


def arc_length(p):
    d = np.linalg.norm(np.diff(p, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(d)])


def resample(p, step=None, n=None):
    """Re-space a polyline uniformly by arc length."""
    p = pts(p)
    s = arc_length(p)
    total = s[-1]
    if total < 1e-6:
        return p[:1].repeat(2, 0)
    if n is None:
        n = max(2, int(np.ceil(total / step)) + 1)
    u = np.linspace(0, total, n)
    return np.stack([np.interp(u, s, p[:, 0]), np.interp(u, s, p[:, 1])], 1)


def tangents(p):
    t = np.gradient(pts(p), axis=0)
    return t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)


def side_normals(p):
    """Unit normal n = (-ty, tx). For an axis pointing down the screen this is screen-left...
    side A of a ribbon lies along +n, side B along -n."""
    t = tangents(p)
    return np.stack([-t[:, 1], t[:, 0]], 1)


def chaikin(p, iterations=2):
    """Round the corners of a joint chain while keeping its end points."""
    p = pts(p)
    for _ in range(iterations):
        q = 0.75 * p[:-1] + 0.25 * p[1:]
        r = 0.25 * p[:-1] + 0.75 * p[1:]
        mid = np.empty((2 * len(q), 2))
        mid[0::2], mid[1::2] = q, r
        p = np.vstack([p[:1], mid, p[-1:]])
    return p


def profile(keys, t):
    """Smooth width profile. keys = [(t, value), ...] with t in 0..1; monotone between keys."""
    k = np.asarray(keys, float)
    return PchipInterpolator(k[:, 0], k[:, 1])(np.clip(t, k[0, 0], k[-1, 0]))


def lerp(a, b, t):
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def bbox_of(polys, pad, width, height):
    """Integer bounding box (x0, y0, x1, y1) of polygons, padded and clipped to the canvas."""
    allp = np.vstack([pts(p) for p in polys])
    x0 = int(max(0, np.floor(allp[:, 0].min() - pad)))
    y0 = int(max(0, np.floor(allp[:, 1].min() - pad)))
    x1 = int(min(width, np.ceil(allp[:, 0].max() + pad)))
    y1 = int(min(height, np.ceil(allp[:, 1].max() + pad)))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def offset_polygon(poly, distance):
    """Grow (+) or shrink (-) a smooth closed polygon along its vertex normals."""
    p = pts(poly)
    closed = np.vstack([p[-1], p, p[0]])
    t = closed[2:] - closed[:-2]
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return p + n * distance * (1.0 if area > 0 else -1.0)


class Ribbon:
    """A limb-like form: an axis polyline plus a half-width on each side.

    Gives the outline polygons for filling, the two side polylines for line art,
    and enough data for analytic cylinder shading.
    """

    def __init__(self, axis, width_a, width_b=None, step=4.0, round_start=True, round_end=True):
        axis = resample(axis, step=step)
        n = len(axis)
        t = arc_length(axis) / max(arc_length(axis)[-1], 1e-9)
        wa = self._expand(width_a, t)
        wb = wa if width_b is None else self._expand(width_b, t)
        nrm = side_normals(axis)
        self.axis, self.t, self.wa, self.wb = axis, t, wa, wb
        self.side_a = axis + nrm * wa[:, None]
        self.side_b = axis - nrm * wb[:, None]
        self.round_start, self.round_end = round_start, round_end
        self.n = n

    @staticmethod
    def _expand(w, t):
        if callable(w):
            return np.maximum(np.asarray(w(t), float), 0.0)
        w = np.asarray(w, float)
        if w.ndim == 0:
            return np.full_like(t, float(w))
        if w.ndim == 2:                       # list of (t, width) keys
            return np.maximum(profile(w, t), 0.0)
        return np.maximum(np.interp(t, np.linspace(0, 1, len(w)), w), 0.0)

    def cap(self, end):
        """Half-disc closing the ribbon; bulges outward along the axis."""
        i = 0 if end == 0 else -1
        a, b = self.side_a[i], self.side_b[i]
        c, r = (a + b) / 2, np.linalg.norm(a - b) / 2
        if r < 0.3:
            return None
        ang0 = np.arctan2(a[1] - c[1], a[0] - c[0])
        direction = 1.0 if end == 0 else -1.0
        # sweep from side A to side B on the outward side of the axis
        ang = ang0 + direction * np.linspace(0, np.pi, 14)
        tang = tangents(self.axis)[i] * (-1 if end == 0 else 1)
        arc = np.stack([c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)], 1)
        if np.dot(arc[7] - c, tang) < 0:      # picked the inward half, flip it
            ang = ang0 - direction * np.linspace(0, np.pi, 14)
            arc = np.stack([c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)], 1)
        return arc

    def polys(self):
        """Quads per segment plus caps. Union-filling these is robust at bends,
        where a single outline polygon would self-intersect."""
        a, b = self.side_a, self.side_b
        quads = [np.array([a[i], a[i + 1], b[i + 1], b[i]]) for i in range(self.n - 1)]
        for end, wanted in ((0, self.round_start), (1, self.round_end)):
            cap = self.cap(end) if wanted else None
            if cap is not None:
                quads.append(cap)
        return quads

    def outline_paths(self, cap_start=False, cap_end=False):
        """Open polylines to ink: both sides, optionally continued around the caps."""
        a, b = self.side_a.copy(), self.side_b.copy()
        if cap_end and self.round_end and self.cap(1) is not None:
            return [np.vstack([a, self.cap(1), b[::-1]])] if not cap_start else \
                   [np.vstack([a, self.cap(1), b[::-1], self.cap(0)[::-1][1:], a[:1]])]
        if cap_start and self.round_start and self.cap(0) is not None:
            return [np.vstack([b[::-1], self.cap(0)[::-1], a])]
        return [a, b]
