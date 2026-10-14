"""Hard-surface props for still lifes: flat-faced solids, cylinders, discs, tilted frustums,
inset screen content and cast shadows.

Why: devices, cups and plates are machined shapes with flat faces and crisp rims. The
mannequin engine (round, blended forms) suits fruit and bodies; hard surfaces are drawn
the way an illustrator draws them: each visible face is one plane with one normal, so it
takes a single value of light; a cylinder turns its normal across its width; edges are
inked. Points are table coordinates (y = 0 on the table top, up is negative y, z toward
the viewer) projected by the still-life camera (a pitch looking down at the table).
"""
import cv2
import numpy as np

import geom
import raster
from palette import line_color
from scene import Drawable

FACE_EPS = 0.03                  # faces turned further away than this are culled
EDGE_K = 0.7                     # face edges are inked thinner than silhouettes


class View:
    """Still-life camera: pitch about x, then the body frame to pixels."""

    def __init__(self, frame, pitch):
        self.frame = frame
        c, s = np.cos(pitch), np.sin(pitch)
        self.R = np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])

    def view(self, pts):
        return np.atleast_2d(np.asarray(pts, float)) @ self.R.T

    def px(self, pts):
        return self.frame.map(self.view(pts)[:, :2])

    def normal(self, n):
        n = np.asarray(n, float)
        return self.R @ (n / np.linalg.norm(n))

    def depth(self, p):
        """Larger is nearer the viewer: the draw order of props on the table."""
        return float(self.view(p)[0, 2])


def hsv(h, s=0.85, v=1.0):
    """Hue in turns -> RGB (for RGB lighting gradients)."""
    px = np.uint8([[[int(h % 1.0 * 180) % 180, int(s * 255), int(v * 255)]]])
    return cv2.cvtColor(px, cv2.COLOR_HSV2RGB)[0, 0].astype(np.float32) / 255


def flat_normals(poly, n):
    """Constant normal patch over a polygon's bounding box."""
    x0, y0 = np.floor(poly.min(axis=0)).astype(int) - 2
    x1, y1 = np.ceil(poly.max(axis=0)).astype(int) + 2
    arr = np.empty((max(y1 - y0, 1), max(x1 - x0, 1), 3), np.float32)
    arr[:] = n
    return raster.Patch(int(y0), int(x0), arr)


def _outline(poly, width):
    return geom.stroke_polygon(np.vstack([poly, poly[:1]]), width)


# ---------------------------------------------------------------- flat-faced solids

BOX_FACES = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
BOTTOM, TOP, BACK, RIGHT, FRONT, LEFT = range(6)


def box_verts(corner, ex, ey, ez):
    """Parallelepiped from a corner and three edge vectors (ey is usually 'up': negative y)."""
    c, ex, ey, ez = (np.asarray(v, float) for v in (corner, ex, ey, ez))
    return np.array([c, c + ex, c + ex + ez, c + ez, c + ey, c + ex + ey, c + ex + ez + ey, c + ez + ey])


def table_box(cx, cz, width, height, depth, yaw=0.0, base_y=0.0):
    """Box standing on the table, turned by yaw around the vertical: (verts, u, v) with u, v its axes."""
    u = np.array([np.cos(yaw), 0.0, np.sin(yaw)])
    v = np.array([-np.sin(yaw), 0.0, np.cos(yaw)])
    corner = np.array([cx, base_y, cz]) - u * width / 2 - v * depth / 2
    return box_verts(corner, u * width, (0.0, -height, 0.0), v * depth), u, v


def solid(name, group, z, view, verts, faces, color, lw, face_colors=None, ink=True, opacity=1.0):
    """Visible faces of a convex polyhedron, each a flat plane with its own normal."""
    verts = np.asarray(verts, float)
    center = verts.mean(axis=0)
    out = []
    for k, f in enumerate(faces):
        p = verts[f]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        if np.dot(n, p.mean(axis=0) - center) < 0:
            n = -n
        nv = view.normal(n)
        if nv[2] <= FACE_EPS:
            continue
        poly = view.px(p)
        col = np.asarray((face_colors or {}).get(k, color), np.float32)
        out.append(Drawable(f'{name}_f{k}', group, z, fill=[poly], color=col, normal_map=flat_normals(poly, nv),
                            strokes=[_outline(poly, lw * EDGE_K)] if ink else [], line_color=line_color(col),
                            opacity=opacity))
    return out


def face_point(quad, s, t):
    """Point on a parallelogram face (p0, p1, _, p3): s along p0->p1, t along p0->p3."""
    p0, p1, p3 = (np.asarray(quad[i], float) for i in (0, 1, 3))
    return p0 + (p1 - p0) * s + (p3 - p0) * t


def inset(view, quad, s0, s1, t0, t1, lift=0.0, normal=None):
    """Projected sub-rectangle of a face (screens, keys, labels); lift moves it off the face."""
    pts = np.array([face_point(quad, s, t) for s, t in ((s0, t0), (s1, t0), (s1, t1), (s0, t1))])
    if lift and normal is not None:
        pts = pts + np.asarray(normal, float) * lift
    return view.px(pts)


# ---------------------------------------------------------------- round hard surfaces

def _circle(cx, y, cz, r, a0=0.0, a1=2 * np.pi, n=48):
    a = np.linspace(a0, a1, n, endpoint=(a1 - a0) < 2 * np.pi - 1e-6)
    return np.stack([cx + r * np.cos(a), np.full(n, y), cz + r * np.sin(a)], axis=1)


def cylinder(name, group, z, view, cx, cz, base_y, height, r0, r1, color, lw, top_color=None, rim=0.0,
             liquid=None, opacity=1.0):
    """Upright cylinder or frustum: the front half of its side plus its top seen from above.

    The side normal turns across the width (analytic, so the cel edge falls where a real
    cylinder's terminator does). rim > 0 makes an open vessel; liquid = (color, depth below rim).
    """
    unit = view.frame.unit
    top_y = base_y - height
    bottom = _circle(cx, base_y, cz, r0, 0, np.pi)
    upper = _circle(cx, top_y, cz, r1, 0, np.pi)
    side = np.vstack([view.px(bottom), view.px(upper)[::-1]])
    ax = view.px([(cx, base_y, cz)])[0]
    at = view.px([(cx, top_y, cz)])[0]
    x0, y0 = np.floor(side.min(axis=0)).astype(int) - 2
    x1, y1 = np.ceil(side.max(axis=0)).astype(int) + 2
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    t = np.clip((ys - ax[1]) / min(at[1] - ax[1], -1e-3), 0, 1)
    r = (r0 + (r1 - r0) * t) * unit
    u = np.clip((xs - ax[0]) / np.maximum(r, 1e-3), -1, 1)
    w = np.sqrt(1 - u * u)
    n = np.stack([u, np.full_like(u, (r1 - r0) / height) * w, w], axis=-1) @ view.R.T
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    col = np.asarray(color, np.float32)
    lc = line_color(col)
    out = [Drawable(f'{name}_side', group, z, fill=[side], color=col, normal_map=raster.Patch(int(y0), int(x0), n.astype(np.float32)),
                    strokes=[_outline(side, lw)], line_color=lc, opacity=opacity)]
    up = view.normal((0.0, -1.0, 0.0))
    top = view.px(_circle(cx, top_y, cz, r1))
    tc = np.asarray(top_color if top_color is not None else color, np.float32)
    out.append(Drawable(f'{name}_top', group, z + 0.001, fill=[top], color=tc, normal_map=flat_normals(top, up),
                        strokes=[_outline(top, lw * EDGE_K)], line_color=lc, opacity=opacity))
    if rim > 0:
        inner = view.px(_circle(cx, top_y, cz, r1 - rim))
        out.append(Drawable(f'{name}_inside', group, z + 0.002, fill=[inner], color=col * 0.62,
                            normal_map=flat_normals(inner, view.normal((0.0, 0.3, 1.0))), opacity=opacity))
        if liquid is not None:
            lcol, depth = liquid
            surf = view.px(_circle(cx, top_y + depth, cz, r1 - rim * 1.2))
            out.append(Drawable(f'{name}_liquid', 'liquid', z + 0.003, fill=[surf], color=np.asarray(lcol, np.float32),
                                normal_map=flat_normals(surf, up), clip=[f'{name}_inside']))
    return out


def disc(name, group, z, view, cx, cz, base_y, r, thickness, color, lw, well=None):
    """Plate or saucer: a very short cylinder with an optional shallow well (radius fraction)."""
    out = cylinder(name, group, z, view, cx, cz, base_y, thickness, r * 0.96, r, color, lw)
    if well:
        inner = view.px(_circle(cx, base_y - thickness, cz, r * well))
        out.append(Drawable(f'{name}_well', group, z + 0.002, fill=[inner], color=np.asarray(color, np.float32) * 0.93,
                            normal_map=flat_normals(inner, view.normal((0.0, -1.0, 0.15))),
                            strokes=[_outline(inner, lw * 0.5)], line_color=line_color(color)))
    return out


def frustum_hull(view, a, ra, b, rb, n=40):
    """Silhouette of a tilted frustum (lamp shade, cup seen at an angle): hull of its end circles."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    axis = (b - a) / np.linalg.norm(b - a)
    e1 = np.cross(axis, (0.0, 0.0, 1.0))
    if np.linalg.norm(e1) < 1e-3:
        e1 = np.cross(axis, (1.0, 0.0, 0.0))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ca = a + ra * (np.outer(np.cos(ang), e1) + np.outer(np.sin(ang), e2))
    cb = b + rb * (np.outer(np.cos(ang), e1) + np.outer(np.sin(ang), e2))
    pa, pb = view.px(ca), view.px(cb)
    hull = cv2.convexHull(np.vstack([pa, pb]).astype(np.float32)).reshape(-1, 2).astype(float)
    return hull, pb


# ---------------------------------------------------------------- shadows and light

def cast_shadow(name, view, pts3, reach, feather, clip=('table',), opacity=0.8):
    """Shadow on the table: every point slides away from the light by its height (reach per unit)."""
    p = np.asarray(pts3, float).copy()
    h = np.maximum(-p[:, 1], 0.0)
    p += h[:, None] * np.asarray(reach, float)
    p[:, 1] = 0.0
    hull = cv2.convexHull(view.px(p).astype(np.float32)).reshape(-1, 2).astype(float)
    return Drawable(f'{name}_cast', 'shadow', 0, fill=[hull], kind='shadow', clip_vis=list(clip),
                    feather=feather, opacity=opacity)


def cylinder_points(cx, cz, base_y, height, r0, r1):
    return np.vstack([_circle(cx, base_y, cz, r0, n=16), _circle(cx, base_y - height, cz, r1, n=16)])


def glow(name, center_px, rx, ry, color, opacity, z, feather=None):
    """Soft emissive light (lamp pool, screen spill, LED glow)."""
    return Drawable(name, 'emissive', z, fill=[geom.ellipse(center_px[0], center_px[1], rx, ry, 48)],
                    color=np.asarray(color, np.float32), opacity=opacity, feather=feather or max(rx, ry) * 0.6,
                    casts=False, receives=False)
