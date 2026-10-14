"""Curves and point transforms. Pure numpy, no rasterization here."""
import numpy as np

from . import config

_EPS = 1e-6


def spline(points, closed=False, samples=None):
    """Smooth curve through control points (centripetal Catmull-Rom).

    Centripetal parameterization is used because it never overshoots or loops
    between unevenly spaced control points, so hand-placed points stay safe.
    Returns (N, 2) float array.
    """
    pts = np.asarray(points, np.float64)
    samples = samples or config.SPLINE_SAMPLES
    if len(pts) < 3:
        return pts.copy()
    if closed:
        ext = np.vstack([pts[-1], pts, pts[0], pts[1]])
    else:
        ext = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    out = []
    u = np.linspace(0.0, 1.0, samples, endpoint=False)[:, None]
    for i in range(len(ext) - 3):
        p0, p1, p2, p3 = ext[i:i + 4]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0) ** 0.5, _EPS)
        t2 = t1 + max(np.linalg.norm(p2 - p1) ** 0.5, _EPS)
        t3 = t2 + max(np.linalg.norm(p3 - p2) ** 0.5, _EPS)
        t = t1 + u * (t2 - t1)
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    curve = np.vstack(out)
    if not closed:
        curve = np.vstack([curve, pts[-1]])
    return curve


def arc_length(poly):
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(poly, step=None, count=None):
    """Re-space a polyline evenly by arc length (by step in px, or by count)."""
    poly = np.asarray(poly, np.float64)
    dist = arc_length(poly)
    total = dist[-1]
    if total < _EPS:
        return poly[:1].repeat(2, axis=0)
    if count is None:
        count = max(int(np.ceil(total / (step or config.RIBBON_STEP_PX))) + 1, 2)
    target = np.linspace(0.0, total, count)
    return np.stack([np.interp(target, dist, poly[:, 0]),
                     np.interp(target, dist, poly[:, 1])], axis=1)


def normals(poly):
    """Unit left-hand normals of a polyline (per point)."""
    tangent = np.gradient(np.asarray(poly, np.float64), axis=0)
    length = np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), _EPS)
    tangent = tangent / length
    return np.stack([tangent[:, 1], -tangent[:, 0]], axis=1)


# --- width profiles ---------------------------------------------------------
# A profile maps t in 0..1 (start..end of a stroke) to a width factor 0..1.
# They model pen pressure: where the stroke is heavy and where it lifts off.

def _profile_taper(t):      # thin - thick - thin, the default inking stroke
    return np.sin(np.pi * t) ** 0.6


def _profile_in(t):         # heavy start, lifts off to a point (hair tip, lash)
    return np.cos(0.5 * np.pi * t) ** 0.8


def _profile_out(t):        # starts as a point, ends heavy
    return np.sin(0.5 * np.pi * t) ** 0.8


def _profile_flat(t):       # constant width with tiny rounded ends
    return np.clip(np.minimum(t, 1 - t) * 40.0, 0, 1) ** 0.5


def _profile_brush(t):      # quick attack, long release
    return np.clip(t * 6.0, 0, 1) ** 0.7 * np.cos(0.5 * np.pi * t ** 1.5) ** 0.9


def _profile_lock(t):       # hair lock: narrow root, full body, pointed tip
    return (0.35 + 0.65 * np.clip(t * 3.5, 0, 1)) * np.clip((1 - t) * 1.0, 0, 1) ** 0.55


def _profile_clump(t):     # hair clump: broad body that closes to a sharp point late
    body = 0.55 + 0.45 * np.clip(t * 4.0, 0, 1)
    tip = 1.0 - np.clip((t - 0.45) / 0.55, 0, 1) ** 1.7
    return body * tip


def _profile_finger(t):    # finger or toe: slight taper with a rounded tip
    return (1.0 - 0.20 * t) * np.sqrt(1.0 - np.clip((t - 0.84) / 0.16, 0, 1) ** 2)


PROFILES = {
    'taper': _profile_taper, 'in': _profile_in, 'out': _profile_out,
    'flat': _profile_flat, 'brush': _profile_brush, 'lock': _profile_lock,
    'clump': _profile_clump, 'finger': _profile_finger,
}


def width_along(profile, count):
    """Evaluate a profile name | callable | list of values at `count` points."""
    t = np.linspace(0.0, 1.0, count)
    if callable(profile):
        return np.asarray(profile(t), np.float64)
    if isinstance(profile, str):
        return PROFILES[profile](t)
    values = np.asarray(profile, np.float64)
    return np.interp(t, np.linspace(0.0, 1.0, len(values)), values)


# --- point helpers ----------------------------------------------------------

def ellipse_points(cx, cy, rx, ry, rotation_deg=0.0, count=48):
    a = np.linspace(0, 2 * np.pi, count, endpoint=False)
    pts = np.stack([rx * np.cos(a), ry * np.sin(a)], axis=1)
    return transform(pts, rotate_deg=rotation_deg, translate=(cx, cy))


def transform(points, scale=1.0, rotate_deg=0.0, translate=(0.0, 0.0), origin=(0.0, 0.0)):
    """Scale, then rotate (clockwise on screen, y down) about origin, then move."""
    pts = (np.asarray(points, np.float64) - origin) * np.asarray(scale, np.float64)
    a = np.radians(rotate_deg)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return pts @ rot.T + origin + np.asarray(translate, np.float64)


def mirror_x(points, axis_x=0.0):
    pts = np.asarray(points, np.float64).copy()
    pts[:, 0] = 2 * axis_x - pts[:, 0]
    return pts
