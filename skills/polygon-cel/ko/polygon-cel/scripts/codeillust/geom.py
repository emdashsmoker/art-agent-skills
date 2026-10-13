"""Pure 2D geometry helpers (numpy only).

Why: every shape in the engine is a dense point list built from a few control
points. Keeping the math here lets construction modules stay declarative.
Coordinates are screen space: x right, y down.
"""
import numpy as np

EPS = 1e-9


def pts(p):
    """Coerce anything point-like into an (N, 2) float array."""
    return np.asarray(p, dtype=np.float64).reshape(-1, 2)


def catmull_rom(points, n_per_seg=12, closed=False, alpha=0.5):
    """Centripetal Catmull-Rom spline through control points.

    How: centripetal variant (alpha=0.5) avoids cusps and self loops that the
    uniform variant produces on unevenly spaced control points.
    """
    P = np.asarray(points, dtype=np.float64)
    if P.ndim == 1:
        P = P.reshape(-1, 2)
    if len(P) < 2:
        return P.copy()
    if closed:
        P = np.vstack([P[-1], P, P[0], P[1]])
    else:
        P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** alpha + EPS
        t2 = t1 + np.linalg.norm(p2 - p1) ** alpha + EPS
        t3 = t2 + np.linalg.norm(p3 - p2) ** alpha + EPS
        t = np.linspace(t1, t2, n_per_seg, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    res = np.vstack(out)
    if not closed:
        res = np.vstack([res, P[-2]])
    return res


def bezier(p0, p1, p2, p3, n=48):
    """Cubic Bezier sampled at n points (inclusive ends)."""
    t = np.linspace(0.0, 1.0, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, dtype=np.float64) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + (t ** 3) * p3


def arc_length(P, closed=False):
    P = pts(P)
    if closed:
        P = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(points, spacing, closed=False):
    """Uniform arc-length resampling. Keeps end points for open curves."""
    P = pts(points)
    if len(P) < 2:
        return P.copy()
    src = np.vstack([P, P[:1]]) if closed else P
    s = arc_length(P, closed)
    total = s[-1]
    if total < EPS:
        return P[:1].copy()
    n = max(int(np.ceil(total / spacing)), 3)
    t = np.linspace(0.0, total, n, endpoint=not closed)
    return np.column_stack([np.interp(t, s, src[:, 0]), np.interp(t, s, src[:, 1])])


def signed_area(P):
    P = pts(P)
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def tangents(P, closed=False):
    P = pts(P)
    if closed:
        t = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    else:
        t = np.gradient(P, axis=0)
    return t / (np.linalg.norm(t, axis=1, keepdims=True) + EPS)


def normals(P, closed=False):
    """Left normals (rotate tangent by +90 deg in screen space)."""
    t = tangents(P, closed)
    return np.column_stack([-t[:, 1], t[:, 0]])


def outward_normals(P):
    """Outward unit normals of a closed polygon regardless of winding."""
    n = normals(P, closed=True)
    return -n if signed_area(P) > 0 else n


def offset_closed(P, dist):
    """Offset a smooth closed polygon outward by dist (negative = inward)."""
    P = pts(P)
    return P + outward_normals(P) * dist


def ribbon_quads(P, widths, closed=False, shift=None):
    """Quads of a variable-width ribbon centered on P.

    shift: optional per-point offset of the ribbon center along the left normal.
    Returns (M, 4, 2) array; orientation is normalized later by the rasterizer.
    """
    P = pts(P)
    w = np.broadcast_to(np.asarray(widths, dtype=np.float64), (len(P),)) * 0.5
    n = normals(P, closed)
    c = P if shift is None else P + n * np.asarray(shift, dtype=np.float64)[:, None]
    L = c + n * w[:, None]
    R = c - n * w[:, None]
    idx = np.arange(len(P))
    nxt = np.roll(idx, -1)
    if not closed:
        idx, nxt = idx[:-1], nxt[:-1]
    return np.stack([L[idx], L[nxt], R[nxt], R[idx]], axis=1)


def ellipse(cx, cy, rx, ry, n=96, rot=0.0):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x, y = rx * np.cos(a), ry * np.sin(a)
    c, s = np.cos(rot), np.sin(rot)
    return np.column_stack([cx + c * x - s * y, cy + s * x + c * y])


def rot2(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def rotate(P, theta, center=(0.0, 0.0)):
    P = pts(P)
    c = np.asarray(center, dtype=np.float64)
    return (P - c) @ rot2(theta).T + c


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0 + EPS), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return np.asarray(a, dtype=np.float64) * (1 - t) + np.asarray(b, dtype=np.float64) * t


def tapered_widths(n, w_max, start_taper=0.2, end_taper=0.3, power=1.0):
    """Width profile for a stroke that thins toward both ends."""
    t = np.linspace(0, 1, n)
    head = smoothstep(0.0, max(start_taper, EPS), t) if start_taper > 0 else np.ones(n)
    tail = smoothstep(0.0, max(end_taper, EPS), 1 - t) if end_taper > 0 else np.ones(n)
    return w_max * (head * tail) ** power


def stroke_outline(spine, widths):
    """Closed polygon of a variable-width stroke (left side + reversed right)."""
    S = pts(spine)
    w = np.broadcast_to(np.asarray(widths, dtype=np.float64), (len(S),)) * 0.5
    n = normals(S)
    return np.vstack([S + n * w[:, None], (S - n * w[:, None])[::-1]])
