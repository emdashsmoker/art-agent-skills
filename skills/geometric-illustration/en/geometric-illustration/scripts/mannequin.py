"""Construction mannequin: sphere-swept solids turned into drawable fields.

Why: figure artists build bodies and hands from simple solids (spheres and
tapered cylinders) before inking contours (the Loomis and Bridgman method).
A sphere-swept solid stays sphere-swept under orthographic projection, so its
2D footprint, front depth and silhouette are closed-form fields. That gives
silhouettes that blend like clay, form shading from real depth, occlusion
contours where one form passes in front of another, and self-shadowing,
all with numpy. There is no mesh and no 3D package.

Units are head widths with the head center as origin (y down, z toward the
viewer), the same as frames.BodyFrame.
"""
from dataclasses import dataclass, field, replace
from typing import Optional

import cv2
import numpy as np

import raster
from scene import Drawable

EPS = 1e-6
OUTSIDE_FALLOFF = 3.0       # depth drop per unit distance outside a solid (keeps max() from lifting neighbours)
BBOX_PAD = 0.08             # head widths of padding around a form's bounding box
COARSE_AREA = 350_000       # boxes larger than this (px) evaluate fields on a 2x coarser grid
FAR = 1e3
WINDOW_PAD = 0.06           # head widths evaluated beyond a solid's radius (covers lines and blending)
LINE_LIGHT_GAIN = 0.9       # silhouette lines thicken by this fraction on the side away from the light
LINE_BASE = 0.65
INTERIOR_LINE_K = 0.7       # occlusion contours are thinner than the silhouette
CONTOUR_DEPTH_EPS = 0.015   # a piece must sit this far in front to draw its contour over another
SELECT_EDGE_PX = 0.5        # a non-selected piece hides a selected one only within this distance of its silhouette
QUIET_KEEP = ('hand_',)     # pieces whose contours survive quiet zones
CAP_LENGTH = 0.25           # elliptical segments: end cap length as a fraction of the section half-width
MITER_REACH = 0.5           # how far (in segment lengths) a section may be extrapolated into a bend's wedge
MITER_MIN_COS = 0.3         # sharper folds than this between chain segments fall back to caps
SWEEP_SPACING = 0.2         # ellipsoid sweeps: spacing as a fraction of the thinnest section
SHADOW_STEPS = 10
SHADOW_REACH = 0.16         # longest self-shadow in head widths (longer reads as dirt at illustration scale)
SHADOW_BIAS = 0.012         # head widths; avoids self-shadow acne on smooth curvature
SHADOW_SOFT = 0.02          # head widths; blur of the self-shadow so cel edges follow the smooth form
NORMAL_SMOOTH = 0.02        # head widths; height-field smoothing before normals (hides blend creases)


@dataclass
class Solid:
    """Sphere (b is None) or tapered capsule from a (radius ra) to b (radius rb), 3D points.

    Elliptical capsule: with da/db set, the cross-section is an ellipse whose radius along the
    direction lat (latb at b) is ra (rb) and whose radius across it is da (db). A torso is wider
    than it is deep; round sections force it to be built from several overlapping chains,
    whose creases show up as stripes in the shading.
    """
    a: np.ndarray
    ra: float
    b: Optional[np.ndarray] = None
    rb: Optional[float] = None
    da: Optional[float] = None
    db: Optional[float] = None
    lat: Optional[np.ndarray] = None
    latb: Optional[np.ndarray] = None
    prev_dir: Optional[np.ndarray] = None   # axis of the previous segment in a chain (mitred joint)
    next_dir: Optional[np.ndarray] = None   # axis of the next segment
    axes: Optional[np.ndarray] = None       # ellipsoid: 3x3, columns are the semi-axis vectors

    def ends(self):
        """(centre, bounding radius) of each end."""
        if self.axes is not None:
            return [(self.a, float(np.linalg.norm(self.axes, axis=0).max()))]
        out = [(self.a, max(self.ra, self.da or 0.0))]
        if self.b is not None:
            out.append((self.b, max(self.rb, self.db or 0.0)))
        return out

    def mapped(self, f):
        """The same solid moved by an affine point map f (directions follow its linear part)."""
        if self.axes is not None:
            o = f(np.zeros(3))
            return replace(self, a=f(self.a), axes=np.stack([f(c) - o for c in self.axes.T], axis=1))
        if self.lat is None:
            return replace(self, a=f(self.a), b=None if self.b is None else f(self.b))
        o = f(np.zeros(3))

        def direction(v):
            return None if v is None else f(v) - o
        return replace(self, a=f(self.a), b=f(self.b), lat=f(self.lat) - o, latb=f(self.latb) - o,
                       prev_dir=direction(self.prev_dir), next_dir=direction(self.next_dir))


@dataclass
class Piece:
    """Solids blended into one smooth form (a limb, a torso, a finger).

    Pieces form a tree. Only the first `attach_n` solids blend into the parent
    (a shoulder into the torso, a finger root into the palm); the rest of the
    piece meets other forms with a hard edge, so a hand resting on a hip keeps
    its contour and stays a separate form on the hip.
    """
    name: str
    solids: list
    k: float = 0.05                 # smooth blend radius between the piece's own solids
    parent: Optional[str] = None
    attach_k: float = 0.05          # smooth blend radius with the parent
    attach_n: int = 1
    contours: bool = True           # draw occlusion contours over other pieces
    skip_contour_with: list = field(default_factory=list)
    contour_eps: Optional[float] = None   # depth lead needed before a contour is inked (soft forms: larger)


def sphere(c, r):
    return Solid(np.asarray(c, float), float(r))


def cone(a, b, ra, rb):
    return Solid(np.asarray(a, float), float(ra), np.asarray(b, float), float(rb))


def ellipse_cone(a, b, wa, da, wb, db, lat_a, lat_b, prev_dir=None, next_dir=None):
    """Capsule with elliptical sections: half-width w along lat, half-depth d across it.

    prev_dir / next_dir: axes of the neighbouring segments of a chain. Given, the joint is
    mitred (the segments meet on the bisector) instead of capped.
    """
    def vec(v):
        return None if v is None else np.asarray(v, float)
    return Solid(np.asarray(a, float), float(wa), np.asarray(b, float), float(wb), float(da), float(db),
                 np.asarray(lat_a, float), np.asarray(lat_b, float), vec(prev_dir), vec(next_dir))


def ellipsoid(c, axes):
    """Ellipsoid at c; axes: three semi-axis vectors (any orientation)."""
    return Solid(np.asarray(c, float), float(np.linalg.norm(axes, axis=1).max()),
                 axes=np.asarray(axes, float).T.copy())


def ellipsoid_sweep(centres, widths, heights, lats, spacing=SWEEP_SPACING, smooth=1.5):
    """Flat form with elliptical sections (a foot, a palm) as a dense row of ellipsoids.

    Sections (centre, half-width along lat, half-height across it) are interpolated along
    the path and smoothed like tube(). Each ellipsoid reaches min(width, height) along the
    path, so the two ends round off like a capsule of the thinner dimension. Unlike a mitred
    chain of elliptical segments, the footprint and depth of an ellipsoid are exact from any
    view, so the form holds up seen end-on (a foot pointing at the viewer) and around bends.
    """
    pts = np.asarray(centres, float)
    w, h = np.asarray(widths, float), np.asarray(heights, float)
    lat = np.asarray(lats, float).reshape(-1, 3) * np.ones((len(pts), 1))
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    step = spacing * float(np.minimum(w, h).min())
    s = np.linspace(0.0, arc[-1], max(int(np.ceil(arc[-1] / max(step, EPS))), 1) + 1)
    dense = np.stack([np.interp(s, arc, pts[:, k]) for k in range(3)], axis=1)
    wd, hd = np.interp(s, arc, w), np.interp(s, arc, h)
    ld = np.stack([np.interp(s, arc, lat[:, k]) for k in range(3)], axis=1)
    if smooth > 0 and len(dense) > 2:
        half = int(3 * smooth / spacing) + 1
        kern = np.exp(-0.5 * (np.arange(-half, half + 1) * spacing / smooth) ** 2)
        kern /= kern.sum()

        def blur(v):
            return np.convolve(np.pad(v, half, mode='edge'), kern, mode='valid')
        inner = slice(1, -1)
        for arr in (dense, ld):
            sm = np.stack([blur(arr[:, k]) for k in range(3)], axis=1)
            arr[inner] = sm[inner]
    tan = np.gradient(dense, axis=0)
    out = []
    for c, t, l, wi, hi in zip(dense, tan, ld, wd, hd):
        t = t / max(np.linalg.norm(t), EPS)
        e1 = l - np.dot(l, t) * t
        e1 = e1 / max(np.linalg.norm(e1), EPS)
        e2 = np.cross(t, e1)
        out.append(ellipsoid(c, [e1 * wi, e2 * hi, t * min(wi, hi)]))
    return out


def chain(points, radii):
    """Consecutive tapered capsules through points with the given radii (a limb profile)."""
    pts = [np.asarray(p, float) for p in points]
    return [cone(pts[i], pts[i + 1], radii[i], radii[i + 1]) for i in range(len(pts) - 1)]


def tube(points, radii, steps=4, smooth=1.0):
    """Smooth tapered tube through joint points (a finger, a toe).

    Each span is split into `steps` cones and the centres and radii are Gaussian-smoothed
    over `smooth` samples, so bent joints round off instead of showing their end spheres.
    The two end points stay where they are.
    """
    pts = np.asarray(points, float)
    rad = np.asarray(radii, float)
    t = np.linspace(0, len(pts) - 1, (len(pts) - 1) * steps + 1)
    i = np.minimum(t.astype(int), len(pts) - 2)
    f = (t - i)[:, None]
    dense = pts[i] * (1 - f) + pts[i + 1] * f
    r = rad[i] * (1 - f[:, 0]) + rad[i + 1] * f[:, 0]
    if smooth > 0 and len(dense) > 2:
        half = int(3 * smooth) + 1
        kern = np.exp(-0.5 * (np.arange(-half, half + 1) / smooth) ** 2)
        kern /= kern.sum()

        def blur(v):
            return np.convolve(np.pad(v, half, mode='edge'), kern, mode='valid')
        inner = slice(1, -1)
        smoothed = np.stack([blur(dense[:, k]) for k in range(3)], axis=1)
        dense[inner], r = smoothed[inner], np.concatenate([[r[0]], blur(r)[inner], [r[-1]]])
    return chain(dense, r)


# ---------------------------------------------------------------- view

def rotate_view(p, yaw, pitch=0.0):
    """Turn the body by yaw around the vertical axis (and pitch around x), orthographic view."""
    p = np.asarray(p, float)
    c, s = np.cos(yaw), np.sin(yaw)
    x, y, z = p[..., 0] * c + p[..., 2] * s, p[..., 1], -p[..., 0] * s + p[..., 2] * c
    if pitch:
        cp, sp = np.cos(pitch), np.sin(pitch)
        y, z = y * cp - z * sp, y * sp + z * cp
    return np.stack([x, y, z], axis=-1)


def view_solids(solids, yaw, pitch=0.0):
    return [s.mapped(lambda p: rotate_view(p, yaw, pitch)) for s in solids]


# ---------------------------------------------------------------- fields

def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def solid_fields(P, s):
    """Signed distance (2D footprint) and front depth of one solid on grid P (..., 2)."""
    if s.axes is not None:
        return _ellipsoid_fields(P, s)
    if s.da is not None:
        return _elliptic_fields(P, s)
    ax, ay, az = s.a
    if s.b is None:
        d = np.hypot(P[..., 0] - ax, P[..., 1] - ay) - s.ra
        return d, _depth(az, s.ra, d)
    bx, by, bz = s.b
    vx, vy = bx - ax, by - ay
    length = np.hypot(vx, vy)
    ra, rb = s.ra, s.rb
    if length <= abs(ra - rb) + EPS:   # seen end-on: the larger end sphere covers the smaller one
        big = s.a if ra >= rb else s.b
        r = max(ra, rb)
        d = np.hypot(P[..., 0] - big[0], P[..., 1] - big[1]) - r
        return d, _depth(big[2], r, d)
    ux, uy = vx / length, vy / length
    px, py = P[..., 0] - ax, P[..., 1] - ay
    along = px * ux + py * uy
    perp = np.abs(px * uy - py * ux)
    # exact 2D distance to an uneven capsule (Inigo Quilez)
    bb = (ra - rb) / length
    aa = np.sqrt(1 - bb * bb)
    kk = perp * -bb + along * aa
    d = np.where(kk < 0, np.hypot(perp, along) - ra,
                 np.where(kk > aa * length, np.hypot(perp, along - length) - rb, perp * aa + along * bb - ra))
    s_c, cap = _sweep_section(along, perp, length, ra, rb, bz - az)
    return d, az + (bz - az) * s_c + cap - np.maximum(d, 0) * OUTSIDE_FALLOFF


def _sweep_section(along, perp, length, ra, rb, dz=0.0, amp=1.0):
    """Front height of a sphere-swept cone: the sphere along the axis that reaches highest over P.

    The cone is the union of spheres c(s) with radius ra + (rb - ra) s. Over a point P the
    surface height is max over s of z(s) + amp * sqrt(g(s)), g(s) = r(s)^2 - |P - c(s)|^2.
    Without a depth slope the best s has a closed form; one Newton step then accounts for the
    axis tilting toward the viewer (dz). Taking the sphere at P's axial projection instead
    (the earlier shortcut) leaves a ripple at every joint of a long sweep.
    Returns (s, height above the axis at s, 0 outside the cone).
    """
    dr = rb - ra
    denom = length * length - dr * dr
    s0 = np.clip((dr * ra + length * along) / denom, 0, 1)

    def gap(sv):
        r = ra + dr * sv
        return r * r - (along - sv * length) ** 2 - perp * perp
    if dz:
        s0 = np.clip(s0 + dz * np.sqrt(np.maximum(gap(s0), 0)) / (amp * denom), 0, 1)
    return s0, np.sqrt(np.maximum(gap(s0), 0))


def _section(r, dr, lat, t, n):
    """Seen across the axis t, an elliptical section (radius r along lat, dr across it) shows a
    half-width w, and its front depth at screen offset u is skew * u + amp * sqrt(w^2 - u^2)."""
    e1 = lat - np.dot(lat, t) * t
    e1 = e1 / max(np.linalg.norm(e1), EPS)
    e2 = np.cross(t, e1)
    m11, m12 = r * np.dot(e1, n), dr * np.dot(e2, n)
    m21, m22 = r * e1[2], dr * e2[2]
    A = max(m11 * m11 + m12 * m12, EPS)
    return np.sqrt(A), (m11 * m21 + m12 * m22) / A, abs(m11 * m22 - m12 * m21) / A


def _elliptic_fields(P, s):
    """Elliptical-section segment with short (squashed) end caps.

    A lofted torso is a chain of these. Round caps of radius = half-width would reach far into
    the narrower neighbours (a wide hip section swelling up into the waist) and bend the
    designed outline; short caps (CAP_LENGTH x half-width) keep the outline on the table.
    """
    a3, b3 = np.asarray(s.a, float), np.asarray(s.b, float)
    v = b3 - a3
    length = np.hypot(v[0], v[1])
    t = v / max(np.linalg.norm(v), EPS)
    if length < EPS:                                   # end-on: a round blob of the larger section
        return solid_fields(P, Solid(a3, max(s.ra, s.da, s.rb, s.db)))
    ux, uy = v[0] / length, v[1] / length
    n = np.array([uy, -ux, 0.0])
    ra, ska, ama = _section(s.ra, s.da, np.asarray(s.lat, float), t, n)
    rb, skb, amb = _section(s.rb, s.db, np.asarray(s.latb, float), t, n)
    px, py = P[..., 0] - a3[0], P[..., 1] - a3[1]
    along = px * ux + py * uy
    u = px * uy - py * ux
    perp = np.abs(u)
    # a joint with a neighbour is mitred: this segment owns the side of the bisector line facing
    # it, its section extrapolated slightly into the wedge a bend opens; an open end gets a cap
    start_m = _miter(s.prev_dir, (ux, uy))
    end_m = _miter(s.next_dir, (ux, uy))
    tt = along / length
    if start_m is None:
        tt = np.maximum(tt, 0)
    if end_m is None:
        tt = np.minimum(tt, 1)
    tt = np.clip(tt, -MITER_REACH, 1 + MITER_REACH)
    w = np.maximum(ra + (rb - ra) * tt, EPS)
    side_d = (perp - w) / np.sqrt(1 + ((rb - ra) / length) ** 2)
    beyond = np.zeros_like(along)
    if start_m is None:
        beyond = np.maximum(beyond, -along)
    if end_m is None:
        beyond = np.maximum(beyond, along - length)
    end_r = np.where(along < 0, ra, rb)
    cap_len = CAP_LENGTH * end_r
    d = np.where(beyond > 0, _ellipse_distance(beyond, perp, cap_len, end_r), side_d)
    if start_m is not None:                       # outside the start mitre: the previous segment's
        d = np.where(px * start_m[0] + py * start_m[1] < 0, FAR, d)
    if end_m is not None:
        qx, qy = P[..., 0] - b3[0], P[..., 1] - b3[1]
        d = np.where(qx * end_m[0] + qy * end_m[1] > 0, FAR, d)
    w_cap = np.where(beyond > 0, end_r * np.sqrt(np.clip(1 - (beyond / cap_len) ** 2, 0, 1)), w)
    tc = np.clip(tt, 0, 1)
    depth = (a3[2] + v[2] * tt + (ska + (skb - ska) * tc) * np.clip(u, -w_cap, w_cap)
             + (ama + (amb - ama) * tc) * np.sqrt(np.maximum(w_cap * w_cap - perp * perp, 0))
             - np.maximum(np.where(d >= FAR, 0, d), 0) * OUTSIDE_FALLOFF)
    depth = np.where(d >= FAR, -FAR, depth)
    return d, depth


def _ellipsoid_fields(P, s):
    """Ellipsoid seen along z: exact front depth; footprint distance to first order.

    The ellipsoid is p^T Q p <= 1 (Q = (A A^T)^-1). Along a viewing ray the depth solves a
    quadratic; its discriminant vanishes on the outline, the ellipse x^T S x = 1 with S the
    Schur complement of Q's depth row.
    """
    A = s.axes
    Q = np.linalg.inv(A @ A.T)
    x, y = P[..., 0] - s.a[0], P[..., 1] - s.a[1]
    q22 = Q[2, 2]
    S = Q[:2, :2] - np.outer(Q[:2, 2], Q[:2, 2]) / q22
    g = S[0, 0] * x * x + 2 * S[0, 1] * x * y + S[1, 1] * y * y
    f = np.sqrt(np.maximum(g, 0))
    gx, gy = S[0, 0] * x + S[0, 1] * y, S[0, 1] * x + S[1, 1] * y
    grad = np.hypot(gx, gy) / np.maximum(f, EPS)
    d = np.where(f > EPS, (f - 1) / np.maximum(grad, EPS), -1.0 / np.sqrt(np.linalg.eigvalsh(S).max()))
    b = Q[2, 0] * x + Q[2, 1] * y
    depth = s.a[2] + (-b + np.sqrt(np.maximum(q22 * (1 - g), 0))) / q22 - np.maximum(d, 0) * OUTSIDE_FALLOFF
    return d, depth


def _miter(neighbour, axis2d):
    """2D normal of the bisector line at a joint (None: open end, or a fold too sharp to mitre)."""
    if neighbour is None:
        return None
    nb = np.asarray(neighbour[:2], float)
    if np.linalg.norm(nb) < EPS:
        return None
    nb = nb / np.linalg.norm(nb)
    m = nb + np.asarray(axis2d)
    if np.dot(nb, axis2d) < MITER_MIN_COS or np.linalg.norm(m) < EPS:
        return None
    return m / np.linalg.norm(m)


def _ellipse_distance(x, y, ax, ay):
    """First-order signed distance to an axis-aligned ellipse (exact on the axes, smooth elsewhere)."""
    f = np.sqrt((x / ax) ** 2 + (y / ay) ** 2)
    grad = np.sqrt((x / ax ** 2) ** 2 + (y / ay ** 2) ** 2) / np.maximum(f, EPS)
    return (f - 1) / np.maximum(grad, EPS)


def _depth(zc, r, d):
    """Front depth of a round cross-section of radius r, driven by the exact distance d.

    Using the distance (not the distance to the axis) keeps the depth profile and the
    footprint consistent, so joints between tapered segments do not show seams.
    """
    q = np.clip(r + d, 0, None)
    return zc + np.sqrt(np.maximum(r * r - q * q, 0)) - np.maximum(d, 0) * OUTSIDE_FALLOFF


def piece_fields(P, solids, k):
    """Smooth union of solids on grid P. Each solid is evaluated only inside its own window.

    Outside every window the distance stays FAR (empty) and the depth stays -FAR, which is
    exact for coverage and lines because both only depend on values near a surface.
    """
    d = np.full(P.shape[:2], FAR, np.float32)
    h = np.full(P.shape[:2], -FAR, np.float32)
    xs_axis, ys_axis = P[0, :, 0], P[:, 0, 1]
    for s in solids:
        ends = s.ends()
        pts = [c for c, _ in ends]
        r = max(rr for _, rr in ends) + k + WINDOW_PAD
        lo = np.min([p[:2] for p in pts], axis=0) - r
        hi = np.max([p[:2] for p in pts], axis=0) + r
        x0, x1 = np.searchsorted(xs_axis, lo[0]), np.searchsorted(xs_axis, hi[0])
        y0, y1 = np.searchsorted(ys_axis, lo[1]), np.searchsorted(ys_axis, hi[1])
        if x1 <= x0 or y1 <= y0:
            continue
        win = (slice(y0, y1), slice(x0, x1))
        ds, hs = solid_fields(P[win], s)
        d[win] = smin(d[win], ds, k)
        h[win] = smax(h[win], hs, k)
    return d, h


# ---------------------------------------------------------------- drawables

@dataclass
class FormResult:
    drawables: list
    sdf_px: np.ndarray
    height: np.ndarray
    box: tuple


class FormBuilder:
    """Turns pieces (in view space) into a filled, shaded, inked Drawable."""

    def __init__(self, frame, shape, light, line_width):
        self.frame = frame            # BodyFrame: body units <-> pixels
        self.shape = shape            # canvas (h, w)
        self.light = np.asarray(light, float) / np.linalg.norm(light)
        self.lw = line_width

    @staticmethod
    def _extent(pieces):
        lo, hi = np.full(2, np.inf), np.full(2, -np.inf)
        for pc in pieces:
            for s in pc.solids:
                for c, r in s.ends():
                    lo = np.minimum(lo, c[:2] - r)
                    hi = np.maximum(hi, c[:2] + r)
        return lo, hi

    def _box(self, pieces):
        lo, hi = self._extent(pieces)
        p0 = self.frame.map([lo - BBOX_PAD])[0]
        p1 = self.frame.map([hi + BBOX_PAD])[0]
        h, w = self.shape
        x0, y0 = max(int(np.floor(p0[0])), 0), max(int(np.floor(p0[1])), 0)
        x1, y1 = min(int(np.ceil(p1[0])), w), min(int(np.ceil(p1[1])), h)
        return (y0, x0, y1, x1) if x1 > x0 and y1 > y0 else None

    def _grid(self, box):
        y0, x0, y1, x1 = box
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        u = self.frame.unit
        v = (ys - self.frame.origin[1]) / u
        return np.stack([(xs - self.frame.origin[0]) / u - self.frame.lean * v, v], axis=-1)

    def build(self, name, group, z, pieces, color=(1, 1, 1), line_color=None, casts=True, receives=True,
              self_shadow=True, select=None, select_fade=None, quiet_zones=(), gloss=None):
        """pieces: Piece tree (parents listed before children).

        select: names of pieces to keep; the result covers only where those pieces are the
        front-most form, fading out at the junction (used to lift arms or hands above clothes
        or hair while the full body stays underneath).
        select_fade: optional function(P) -> [0, 1] multiplier (e.g. fade a hand overlay up the forearm).
        quiet_zones: (center_xy, radius) discs in body units where no interior line is drawn, except
        the contours of pieces named with a QUIET_KEEP prefix (a covering hand keeps its outline).
        gloss: optional (color, power, opacity) for a Blinn specular highlight (glass, fruit skin).
        """
        box = self._box([p for p in pieces if p.name in select] if select else pieces)
        if box is None:
            return None
        P = self._grid(box)
        unit = self.frame.unit
        lo = (np.array([box[1], box[0]]) - self.frame.origin) / unit - BBOX_PAD * 4
        hi = (np.array([box[3], box[2]]) - self.frame.origin) / unit + BBOX_PAD * 4
        coarse = (box[2] - box[0]) * (box[3] - box[1]) > COARSE_AREA
        own, root = {}, {}
        for pc in pieces:
            plo, phi = self._extent([pc])
            if np.any(plo > hi) or np.any(phi < lo):          # far from this box: cannot affect it
                far = (np.full(P.shape[:2], FAR, np.float32), np.full(P.shape[:2], -FAR, np.float32))
                own[pc.name] = root[pc.name] = far
                continue
            own[pc.name] = self._fields(P, pc.solids, pc.k, coarse)
            if pc.parent:
                root[pc.name] = self._fields(P, pc.solids[:pc.attach_n], pc.k, coarse)
        children = {pc.name: [c for c in pieces if c.parent == pc.name] for pc in pieces}

        def joined(pc):
            d, h = own[pc.name]
            for c in children[pc.name]:
                rd, rh = root[c.name]
                cd, ch = joined(c)
                d = np.minimum(np.minimum(d, smin(own[pc.name][0], rd, c.attach_k)), cd)
                h = np.maximum(np.maximum(h, smax(own[pc.name][1], rh, c.attach_k)), ch)
            return d, h

        d, h = joined(pieces[0])
        sdf_px = d * unit
        cov = np.clip(0.5 - sdf_px, 0, 1).astype(np.float32)
        normal = self._normals(h * unit, cov)
        interior, kept = self._occlusion_lines(pieces, own, unit, P, h)
        for center, radius in quiet_zones:
            dist = np.hypot(P[..., 0] - center[0], P[..., 1] - center[1])
            interior *= np.clip((dist - radius) / (0.25 * radius), 0, 1)
        interior = np.maximum(interior, kept)
        lines = np.maximum(self._silhouette_line(sdf_px), interior)
        shade = self._self_shadow(h * unit, cov) if self_shadow else None
        if select is not None:
            weight = self._selection(pieces, own, select, unit)
            if select_fade is not None:
                weight = weight * select_fade(P)
            cov, lines = cov * weight, lines * weight
            shade = shade * weight if shade is not None else None
        y0, x0 = box[0], box[1]
        out = [Drawable(name, group, z, color=color, line_color=line_color, casts=casts, receives=receives,
                        mask=raster.Patch(y0, x0, cov.astype(np.float32)),
                        line_mask=raster.Patch(y0, x0, lines.astype(np.float32)),
                        normal_map=raster.Patch(y0, x0, normal))]
        if shade is not None:
            out.append(Drawable(name + '_selfshadow', group, 0, kind='shadow', clip_vis=[name],
                                mask=raster.Patch(y0, x0, shade.astype(np.float32))))
        if gloss is not None:
            color, power, opacity = gloss
            half = self.light + np.array([0.0, 0.0, 1.0])
            half /= np.linalg.norm(half)
            spec = np.clip((normal * half).sum(axis=2), 0, 1) ** power
            spec = np.clip((spec - 0.35) / 0.25, 0, 1) * cov * (1 - (shade if shade is not None else 0))
            out.append(Drawable(name + '_gloss', group, 0, kind='highlight', hl_color=color, opacity=opacity,
                                clip_vis=[name], mask=raster.Patch(y0, x0, spec.astype(np.float32))))
        return FormResult(out, sdf_px, h, box)

    @staticmethod
    def _fields(P, solids, k, coarse):
        """Piece fields, evaluated on every other pixel for large boxes and upsampled (fields are smooth)."""
        if not coarse:
            return piece_fields(P, solids, k)
        d, h = piece_fields(P[::2, ::2], solids, k)
        size = (P.shape[1], P.shape[0])
        return (cv2.resize(d.astype(np.float32), size, interpolation=cv2.INTER_LINEAR),
                cv2.resize(h.astype(np.float32), size, interpolation=cv2.INTER_LINEAR))

    @staticmethod
    def _selection(pieces, own, select, unit):
        sel = [own[p.name] for p in pieces if p.name in select]
        rest = [own[p.name] for p in pieces if p.name not in select]
        d_sel = np.minimum.reduce([f[0] for f in sel])
        h_sel = np.maximum.reduce([f[1] for f in sel])
        if not rest:
            return np.ones_like(d_sel)
        d_rest = np.minimum.reduce([f[0] for f in rest])
        # a piece's depth exists only on its own silhouette: piece_fields fills the whole solid window,
        # and that extrapolated depth would put a piece "in front" at pixels it does not cover
        h_rest = np.maximum.reduce([np.where(f[0] * unit < SELECT_EDGE_PX, f[1], -FAR) for f in rest])
        outside_rest = np.clip(d_rest * unit, 0, 1)
        in_front = np.clip((h_sel - h_rest) * unit * 0.25 + 0.5, 0, 1)
        near_sel = np.clip(1.0 - d_sel * unit, 0, 1)          # stay inside the selected forms (+1 px for the ink)
        return (np.maximum(outside_rest, in_front) * near_sel).astype(np.float32)

    def _normals(self, height_px, cov):
        """Normals from the smoothed height field; the blur is normalised by coverage so the
        silhouette keeps its roll-off and never averages with the empty background."""
        sigma = max(1.0, NORMAL_SMOOTH * self.frame.unit)
        w = np.clip(cov, 0, 1).astype(np.float32)
        num = cv2.GaussianBlur(height_px.astype(np.float32) * w, (0, 0), sigma)
        den = cv2.GaussianBlur(w, (0, 0), sigma)
        hp = np.where(den > 0.05, num / np.maximum(den, 1e-3), height_px).astype(np.float32)
        hp = cv2.GaussianBlur(hp, (0, 0), 1.0)
        gy, gx = np.gradient(hp)
        n = np.dstack([-gx, -gy, np.ones_like(gx)])
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        return n.astype(np.float32)

    def _line_width(self, sdf_px):
        gy, gx = np.gradient(sdf_px)
        g = np.hypot(gx, gy) + EPS
        l2 = self.light[:2] / (np.linalg.norm(self.light[:2]) + EPS)
        away = np.clip(-(gx * l2[0] + gy * l2[1]) / g, 0, 1)    # outward normal facing away from light
        return self.lw * (LINE_BASE + LINE_LIGHT_GAIN * away)

    def _silhouette_line(self, sdf_px):
        w = self._line_width(sdf_px)
        return np.clip(w / 2 - np.abs(sdf_px) + 0.5, 0, 1)

    def _window(self, pc, P, unit, pad_px=4):
        """Row/column slice of the grid covering one piece (contours can only appear there)."""
        lo, hi = self._extent([pc])
        x0 = int(np.searchsorted(P[0, :, 0], lo[0] - pad_px / unit))
        x1 = int(np.searchsorted(P[0, :, 0], hi[0] + pad_px / unit))
        y0 = int(np.searchsorted(P[:, 0, 1], lo[1] - pad_px / unit))
        y1 = int(np.searchsorted(P[:, 0, 1], hi[1] + pad_px / unit))
        # a window of one row or column (a piece grazing the box edge) has no contour to draw
        return (slice(y0, y1), slice(x0, x1)) if y1 - y0 >= 2 and x1 - x0 >= 2 else None

    def _occlusion_lines(self, pieces, own, unit, P, h_all):
        """Contour of piece i where it passes in front of piece j.

        Over its own parent a piece only inks its free part: the root solids that blend into
        the parent (a finger's first phalanx inside the palm) would otherwise draw knuckle arcs.
        Work is limited to the overlap of the two pieces' windows, and a contour is kept only
        where its piece is the front-most surface (a third form may cover it).
        Returns (contours, kept): kept holds the contours of QUIET_KEEP pieces.
        """
        out = np.zeros(own[pieces[0].name][0].shape, np.float32)
        kept = np.zeros_like(out)
        windows = {pc.name: self._window(pc, P, unit) for pc in pieces}
        coarse = P.shape[0] * P.shape[1] > COARSE_AREA
        for pi in pieces:
            wi = windows[pi.name]
            if not pi.contours or wi is None or own[pi.name][0][wi].min() > 2:
                continue
            di, hi = own[pi.name][0][wi], own[pi.name][1][wi]
            di_px = di * unit
            band = np.clip(self._line_width(di_px) * INTERIOR_LINE_K / 2 - np.abs(di_px) + 0.5, 0, 1)
            band *= np.clip((hi - h_all[wi] + CONTOUR_DEPTH_EPS) * unit * 0.5 + 1.0, 0, 1)   # visible only
            eps = pi.contour_eps if pi.contour_eps is not None else CONTOUR_DEPTH_EPS
            if not band.any():
                continue
            free_band = None
            if pi.parent and len(pi.solids) > pi.attach_n:
                fd, _ = self._fields(P[wi], pi.solids[pi.attach_n:], pi.k, coarse)
                free_band = band * np.clip(1.5 - fd * unit, 0, 1)
            for pj in pieces:
                wj = windows[pj.name]
                if pj is pi or wj is None or pj.name in pi.skip_contour_with:
                    continue
                ys = slice(max(wi[0].start, wj[0].start), min(wi[0].stop, wj[0].stop))
                xs = slice(max(wi[1].start, wj[1].start), min(wi[1].stop, wj[1].stop))
                if ys.stop <= ys.start or xs.stop <= xs.start:
                    continue
                local = (slice(ys.start - wi[0].start, ys.stop - wi[0].start),
                         slice(xs.start - wi[1].start, xs.stop - wi[1].start))
                use = free_band if (free_band is not None and pj.name == pi.parent) else band
                use = use[local]
                if not use.any():
                    continue
                dj, hj = own[pj.name][0][ys, xs], own[pj.name][1][ys, xs]
                inside_j = np.clip(-dj * unit - 1.0, 0, 1)
                in_front = np.clip((hi[local] - hj - eps) * unit * 0.5, 0, 1)
                acc = kept if pi.name.startswith(QUIET_KEEP) else out
                acc[ys, xs] = np.maximum(acc[ys, xs], use * inside_j * in_front)
        return out, kept

    def _self_shadow(self, height_px, cov):
        """Height-field shadows: a point is shadowed if the surface toward the light rises above the ray."""
        l = self.light
        l2 = (l[:2] / (np.linalg.norm(l[:2]) + EPS)).astype(np.float32)
        slope = l[2] / (np.linalg.norm(l[:2]) + EPS)
        hgt = np.where(cov > 0.01, height_px, -1e4).astype(np.float32)
        hh, ww = hgt.shape
        gx, gy = np.meshgrid(np.arange(ww, dtype=np.float32), np.arange(hh, dtype=np.float32))
        occl = np.zeros_like(hgt)
        bias = SHADOW_BIAS * self.frame.unit
        reach = SHADOW_REACH * self.frame.unit
        for s in range(1, SHADOW_STEPS + 1):
            dist = np.float32(reach * (s / SHADOW_STEPS) ** 1.5)
            sample = cv2.remap(hgt, gx + l2[0] * dist, gy + l2[1] * dist, cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=-1e4)
            occl = np.maximum(occl, np.clip((sample - hgt - dist * slope - bias) * 0.5, 0, 1))
        occl = cv2.GaussianBlur(occl, (0, 0), max(0.8, SHADOW_SOFT * self.frame.unit))
        return (occl * cov).astype(np.float32)
