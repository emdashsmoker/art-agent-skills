"""Garments fitted to the mannequin body in 3D (upper-body and full figures).

Why: a garment drawn as a flat polygon follows only a few torso angles, so it never looks worn.
Here the knit top is the torso grown by the knit thickness and cut at the armholes; the belt is
a ring around the waist section; the skirt is a cloth surface hung from the waist that rests on
the hips and falls at a fixed slope, so hips and legs never poke through it. Rings below the eye
level dip at the front (a mild perspective), the cue illustrators use to show that a band wraps
around the body. Coordinates: rest-pose torso coordinates (rig_anatomy) mapped to the posed body
with rig_anatomy._torso_point; head-width units, y down, z toward the viewer.
"""
from dataclasses import replace

import cv2
import numpy as np

import geom
import mannequin as M
import raster
import rig_anatomy as A
from palette import darken, lighten, line_color
from rig_body import edge_stroke
from scene import Drawable

# view: rings below this level dip at the front (perspective of an eye at chest height)
EYE_Y = 1.6
VIEW_DIST = 11.0                 # head widths from the eye to the figure

# knit top
TOP_EASE = 0.035                 # knit thickness and ease over the torso (head widths)
TOP_MASK_SMOOTH, TOP_MASK_EDGE = 0.025, 4.0   # turned top: armhole smoothing (head widths) and edge sharpness
TOP_CUT_LINE = 1.1                # turned top: armhole line width (of the line weight)
TOP_NORMAL_BLUR = 0.16           # head widths: knit evens out the small forms under it (cleavage, under-bust crease)
CHEST_PIECES = ('breasts', 'pecs')
TOP_PIECES = ('torso', 'torso_soft') + CHEST_PIECES
ARMHOLE = [(0.355, 1.09), (0.45, 1.25)]                 # rest (x, y) from the collar base toward the armpit
ARMPIT_Y = 1.46
TOP_HEM_Y = 2.68                 # tucked under the belt
CLIP_FAR = 1.6                   # clip polygon reaches past the silhouette (the form makes the side edge)
TOP_COLLAR_MARGIN = 0.06         # turned figure: the knit kept this far beside the collar above the armholes
RIB_COUNT = 17                   # ribs across the front

# turtleneck collar: the neck grown by the folded knit, rising out of the top
COLLAR_EASE = 0.05               # folded knit is thicker than the body knit
COLLAR_TOP_Y = 0.74              # rim height at the sides (just under the jaw)
COLLAR_JOIN_Y = 1.00             # where the collar meets the armhole edge
COLLAR_FRONT_DROP = 0.05         # rim and fold dip at the front: the ring reads as wrapping the neck
COLLAR_FOLD = 0.45               # bottom of the folded band, as a fraction of the way from the rim to the join
COLLAR_ATTACH_K = 0.06           # blend of the collar into the shoulders
COLLAR_CLIP_MARGIN = 0.02        # clip runs just outside the collar so its own outline makes the side edge
COLLAR_FILLET = 0.07             # radius of the curve that turns the collar side into the armhole edge
COLLAR_RIB_COUNT = 11
COLLAR_INNER_DARKEN = 0.55
RIB_TOP_Y = 1.0
RIB_LEVELS = 60
RIB_SAMPLES = 160                # samples across a rib row
RIB_SLOPE_CAP = 4.0              # steeper surface near the outline counts as this slope (ribs crowd, never pile up)
RIB_SMOOTH = 4.0                 # levels: Gaussian smoothing of each rib along its length
RIB_HEIGHT_BLUR = 0.05           # head widths: rib spacing reads the large form, not small bumps

# belt
BELT_TOP_Y, BELT_BOTTOM_Y = 2.60, 2.70
BELT_EASE = TOP_EASE + 0.025
BUCKLE_RX, BUCKLE_RY = 0.07, 0.055

# skirt
SKIRT_TOP_Y = 2.62               # under the belt
SKIRT_EASE = 0.05
SKIRT_STEP = 0.04                # rest levels between skirt rings
SKIRT_MIN_SLOPE = 0.03           # sideways fall per unit length below the hips
SKIRT_DEPTH_SLOPE_K = 0.6        # front and back fall less than the sides
SKIRT_SMOOTH = 6.0               # levels: Gaussian smoothing of the skirt profile (no ridges in the shading)
CONTAIN_SIDE = 0.9               # body points nearer the side than this (fraction of the half-width) widen the skirt
CONTAIN_MAX_DEPTH = 1.6          # the skirt deepens at most this much to hold a forward leg
SKIRT_PIECES = ('torso_soft', 'glutes', 'leg_-1', 'leg_1')
HANG_Y = 3.62                    # rest level of the widest hips: the cloth hangs plumb below it
HANG_BLEND = 0.8                 # rest units over which the skirt turns from the pelvis tilt to plumb
CONE_SAMPLES = 3                 # spheres per body cone when fitting the skirt (limb sweeps are short cones)
SKIRT_THETA_EXTRA = 0.45         # radians past the side, so the outline is covered when folds turn it
SKIRT_THETA_STEPS = 180
SKIRT_SUPERSAMPLE = 4
FOLD_COUNT = 7                   # folds around the whole skirt
FOLD_DEPTH = 0.18                # radial depth of a fold at the hem (fraction of the radius)
FOLD_LINE_LENGTH = 0.42          # fold valley ink runs this fraction of the hip-to-hem length up from the hem
FOLD_LINE_FACING = 0.3           # valley ink only where the cloth faces the viewer
NORMAL_BLUR = 0.025              # head widths: smooths the facets of the painted skirt mesh


# ---------------------------------------------------------------- shared geometry

def body_frames(pose):
    chest = A.Frame3(np.asarray(pose.chest_pos, float), A.rot(*pose.chest))
    pelvis = A.Frame3(np.asarray(pose.pelvis_pos, float), A.rot(*pose.pelvis))
    return chest, pelvis


def perspective(points3):
    """Orthographic view plus the dip of points below the eye level that come toward the viewer."""
    p = np.atleast_2d(np.asarray(points3, float))
    return np.stack([p[:, 0], p[:, 1] + (p[:, 1] - EYE_Y) * p[:, 2] / VIEW_DIST], axis=1)


def loft_section(y):
    """Rest torso section at level y: (half-width, half-depth, depth centre)."""
    rows = A.loft_rows()
    w, d, zc = (np.interp(y, rows[:, 0], rows[:, k]) for k in (1, 2, 3))
    return w / 2, d / 2, zc


def torso_ring(chest, pelvis, y, ease, thetas):
    """Posed points of the torso section at rest level y grown by ease; theta 0 faces the viewer."""
    hw, hd, zc = loft_section(y)
    return np.array([A._torso_point(chest, pelvis, ((hw + ease) * np.sin(t), y, zc + (hd + ease) * np.cos(t)))
                     for t in thetas])


def front_point(chest, pelvis, x, y):
    """Posed point on the front of the torso at rest (x, y)."""
    hw, hd, zc = loft_section(y)
    f = np.clip(x / max(hw, 1e-6), -1, 1)
    return A._torso_point(chest, pelvis, (x, y, zc + hd * np.sqrt(1 - f * f)))


# ---------------------------------------------------------------- turned figures
#
# A turned figure (rig_figure.turned) keeps every rest-coordinate recipe: rings keep their body
# angles (theta 0 = the body's front), and only the visible part is chosen by the view. Front
# views take the classic front half, so their pictures stay exactly as before.

VIEW_ARC_SAMPLES = 720
FACING_MIN = 0.08                # a surface point counts as visible when its normal turns this much toward the viewer


def frame_weight(y):
    """Blend of the pelvis frame at rest level y (rig_anatomy._torso_point)."""
    t = np.clip((np.asarray(y, float) - A.CHEST_WEIGHT_Y[0]) / (A.CHEST_WEIGHT_Y[1] - A.CHEST_WEIGHT_Y[0]), 0, 1)
    return t * t * (3 - 2 * t)


def view_arc(ring_fn, n=32, turned=False):
    """Body angles of the half of a ring that faces the viewer, ordered left to right on screen.

    ring_fn(thetas) -> world points. The ends are the ring's outline points (extreme screen x), so
    a cut or a band built on the arc ends at the body's side whatever the turn.
    """
    if not turned:
        return np.linspace(-np.pi / 2, np.pi / 2, n)
    th = np.linspace(-np.pi, np.pi, VIEW_ARC_SAMPLES, endpoint=False)
    p = np.asarray(ring_fn(th))
    a, b = th[np.argmin(p[:, 0])], th[np.argmax(p[:, 0])]
    up = np.linspace(a, a + (b - a) % (2 * np.pi), 64)
    down = np.linspace(a, a - (a - b) % (2 * np.pi), 64)
    pick = up if np.asarray(ring_fn(up))[:, 2].mean() >= np.asarray(ring_fn(down))[:, 2].mean() else down
    return np.linspace(pick[0], pick[-1], n)


def torso_arc(chest, pelvis, y, ease, n=32, turned=False):
    """Visible half of the torso ring at rest level y (body angles)."""
    return view_arc(lambda th: torso_ring(chest, pelvis, y, ease, th), n, turned)


def surface_rest(chest, pelvis, pts_rest, back=False, lift=0.0):
    """Posed points and outward normals of rest (x, y) points on the front (or back) of the torso loft."""
    out, nrm = [], []
    for x, y in np.atleast_2d(np.asarray(pts_rest, float)):
        hw, hd, zc = loft_section(y)
        f = np.clip(x / max(hw, 1e-6), -0.999, 0.999)
        dz = hd * np.sqrt(1 - f * f) * (-1 if back else 1)
        n_rest = A.unit((x / max(hw, 1e-6) ** 2, 0.0, dz / max(hd, 1e-6) ** 2))
        p = np.array([x, y, zc + dz]) + n_rest * lift
        t = frame_weight(y)
        R = chest.R * (1 - t) + pelvis.R * t
        out.append(A._torso_point(chest, pelvis, p))
        nrm.append(A.unit(R @ n_rest))
    return np.array(out), np.array(nrm)


def rest_coords(chest, pelvis, world):
    """Inverse of rig_anatomy._torso_point for many world points (N x 3) -> rest points (N x 3).

    For a fixed frame blend t the map is affine (p = A_t r + b_t); t depends on the rest height,
    so a few fixed-point steps on t converge (the frames differ by small angles).
    """
    world = np.atleast_2d(np.asarray(world, float))
    c0, p0 = np.asarray(A.CHEST_ORIGIN, float), np.asarray(A.PELVIS_ORIGIN, float)
    bc = chest.origin - chest.R @ c0
    bp = pelvis.origin - pelvis.R @ p0
    y = world[:, 1].copy()
    rest = world
    for _ in range(4):
        t = frame_weight(y)[:, None, None]
        Am = chest.R[None] * (1 - t) + pelvis.R[None] * t
        b = bc[None] * (1 - t[:, :, 0]) + bp[None] * t[:, :, 0]
        rest = np.linalg.solve(Am, (world - b)[..., None])[..., 0]
        y = rest[:, 1]
    return rest


def surface_sides(res, body, chest, pelvis):
    """Rest coordinates of the visible surface of a form, per pixel of its box: (x, y, front?)."""
    hh, ww = res.height.shape
    ys, xs = np.mgrid[res.box[0]:res.box[0] + hh, res.box[1]:res.box[1] + ww].astype(np.float64)
    u = (xs - body.origin[0]) / body.unit
    v = (ys - body.origin[1]) / body.unit
    u -= body.lean * v
    world = np.stack([u.ravel(), v.ravel(), res.height.astype(np.float64).ravel()], axis=1)
    rest = rest_coords(chest, pelvis, world)
    zc = np.interp(rest[:, 1], A.loft_rows()[:, 0], A.loft_rows()[:, 3])
    return rest[:, 0].reshape(hh, ww), rest[:, 1].reshape(hh, ww), (rest[:, 2] >= zc).reshape(hh, ww)


def patch_of(mask, y0, x0):
    return raster.Patch(int(y0), int(x0), mask.astype(np.float32))


# ---------------------------------------------------------------- turtleneck collar

class NeckAxis:
    """Posed neck cone (rig_anatomy torso_pieces): rings around it at a given height."""

    def __init__(self, pose, chest):
        self.base = chest.p(A.NECK_BASE_LOCAL)
        self.top = np.asarray(pose.head_pos, float) + A.HEAD_TO_NECK
        self.axis = self.top - self.base
        u = self.axis / np.linalg.norm(self.axis)
        self.turn = getattr(pose, 'turn', 0.0)
        self.turned = abs(self.turn) > 1e-9
        R = A.rot(self.turn)                               # body angles: theta 0 is the body's front
        across, front = R @ np.array([1.0, 0.0, 0.0]), R @ np.array([0.0, 0.0, 1.0])
        e1 = across - np.dot(across, u) * u
        self.e1 = e1 / np.linalg.norm(e1)                  # across the neck, toward the figure's left
        self.e2 = np.cross(u, self.e1)
        if np.dot(self.e2, front) < 0:                      # toward the body's front (the viewer, unturned)
            self.e2 = -self.e2
        # a neckline lying on the shoulders is level with the chest, even when the neck leans
        self.level_e1 = chest.d((1.0, 0.0, 0.0)) / np.linalg.norm(chest.d((1.0, 0.0, 0.0)))
        e2 = self.e2 - np.dot(self.e2, self.level_e1) * self.level_e1
        self.level_e2 = e2 / np.linalg.norm(e2)

    def arc(self, y, ease, n=32, drop=0.0, level=False):
        """Body angles of the visible half of the ring at height y (front view: -pi/2..pi/2)."""
        return view_arc(lambda th: self.ring(y, ease, th, drop, level), n, self.turned)

    def t_at(self, y):
        return (y - self.base[1]) / self.axis[1]

    def radius(self, t, ease):
        r0, r1 = A.NECK_RADII
        return r0 + (r1 - r0) * t + ease

    def point(self, t):
        return self.base + self.axis * t

    def ring(self, y, ease, thetas, drop=0.0, level=False):
        """World points around the neck at height y; theta 0 faces the viewer, drop lowers the front.
        level: the ring lies level with the chest (a neckline on the shoulders), else square to the neck."""
        t = self.t_at(y)
        c, r = self.point(t), self.radius(t, ease)
        e1, e2 = (self.level_e1, self.level_e2) if level else (self.e1, self.e2)
        th = np.asarray(thetas, float)[:, None]
        return c + r * (np.sin(th) * e1 + np.cos(th) * e2) + np.array([0.0, 1.0, 0.0]) * drop * np.cos(th)


def collar_piece(neck):
    """The collar as one cone from inside the shoulders to the rim, blended into the torso."""
    t0, t1 = -0.05, neck.t_at(COLLAR_TOP_Y)
    return M.Piece('collar', [M.cone(neck.point(t0), neck.point(t1), neck.radius(t0, COLLAR_EASE),
                                     neck.radius(t1, COLLAR_EASE))], k=0.0, parent='torso',
                   attach_k=COLLAR_ATTACH_K, attach_n=1)


def collar_rim(neck, n=40):
    """Front rim of the collar, left to right (world points)."""
    return neck.ring(COLLAR_TOP_Y, COLLAR_EASE, np.linspace(-np.pi / 2, np.pi / 2, n), COLLAR_FRONT_DROP)


def collar_side(neck, s, y, margin):
    """Point beside the collar (side s) at height y, margin outside its knit (head units)."""
    return neck.ring(y, COLLAR_EASE + margin, [s * np.pi / 2])[0, :2]


def collar_sides(neck):
    """Straight clip edges beside the collar, from the start of the shoulder curve up to the rim."""
    top = COLLAR_JOIN_Y - 2 * COLLAR_FILLET
    return [np.array([collar_side(neck, s, top, COLLAR_CLIP_MARGIN), collar_side(neck, s, COLLAR_TOP_Y, COLLAR_CLIP_MARGIN)])
            for s in (-1, 1)]


def build_collar_inner(neck, body, pal, lw, z_back):
    """Inside of the collar: shows only beside the neck, which covers it (z behind the body)."""
    ring = neck.ring(COLLAR_TOP_Y, COLLAR_EASE, np.linspace(0, 2 * np.pi, 64), COLLAR_FRONT_DROP)
    back = neck.ring(COLLAR_TOP_Y, COLLAR_EASE, np.linspace(np.pi / 2, 3 * np.pi / 2, 32), COLLAR_FRONT_DROP)
    cloth = pal['cloth']
    return Drawable('collar_inner', 'cloth', z_back, fill=[body.map(ring[:, :2])], color=darken(cloth, COLLAR_INNER_DARKEN),
                    casts=False, strokes=[geom.stroke_polygon(body.map(back[:, :2]), lw * 0.9)],
                    line_color=line_color(cloth))


# ---------------------------------------------------------------- knit top

def grow(solid, ease):
    """A solid thickened by `ease` (cloth over the body)."""
    if solid.axes is not None:                       # ellipsoid: every semi-axis grows by the ease
        lengths = np.linalg.norm(solid.axes, axis=0)
        return replace(solid, ra=solid.ra + ease, axes=solid.axes * ((lengths + ease) / lengths))
    g = replace(solid, ra=solid.ra + ease)
    if solid.rb is not None:
        g = replace(g, rb=solid.rb + ease)
    if solid.da is not None:
        g = replace(g, da=solid.da + ease, db=solid.db + ease)
    return g


def grown(pieces, ease):
    """Torso pieces grown by the knit thickness (the chest form draws no contour of its own on the knit)."""
    out = []
    for pc in pieces:
        solids = [grow(s, ease) for s in pc.solids]
        out.append(M.Piece(pc.name, solids, pc.k, pc.parent, pc.attach_k, pc.attach_n,
                           pc.contours and pc.name not in CHEST_PIECES, list(pc.skip_contour_with), pc.contour_eps))
    return out


def knit_normals(patch, sigma_px):
    """Normals blurred so only the large forms show through the knit (no stain-like hollows)."""
    arr = cv2.GaussianBlur(patch.arr, (0, 0), sigma_px)
    arr /= np.linalg.norm(arr, axis=2, keepdims=True) + 1e-6
    return raster.Patch(patch.y0, patch.x0, arr.astype(np.float32))


def armhole_paths(chest, pelvis, neck, margin=COLLAR_CLIP_MARGIN):
    """Edges (left, right) from the collar side, round the shoulder curve, down the armhole to the armpit.

    The collar side and the armhole edge would meet at a corner; a point up the collar and a
    point along the armhole replace it, so the curve leaves the collar tangent to its side
    and the collar seems to flow into the shoulder of the top. margin 0 puts the start on
    the collar outline (the ink); the clip uses a small margin outside it.
    """
    hw = loft_section(ARMPIT_Y)[0] + TOP_EASE
    out = []
    for s in (-1, 1):
        rest = [front_point(chest, pelvis, s * x, y)[:2] for x, y in ARMHOLE + [(hw, ARMPIT_Y)]]
        corner = collar_side(neck, s, COLLAR_JOIN_Y, margin)
        along = rest[0] - corner
        turn = corner + along * min(1.0, COLLAR_FILLET / max(np.linalg.norm(along), 1e-6))
        lead = [collar_side(neck, s, COLLAR_JOIN_Y - k * COLLAR_FILLET, margin) for k in (2, 1)]
        out.append(geom.catmull_rom(np.array(lead + [turn] + rest)))
    return out


def top_clip(chest, pelvis, neck):
    """Region the top covers (head units): between the armholes, up the collar to its rim, down to the hem."""
    left, right = armhole_paths(chest, pelvis, neck)

    def at(x, y):
        return front_point(chest, pelvis, x, y)[:2]
    tops = [collar_side(neck, s, COLLAR_TOP_Y, COLLAR_CLIP_MARGIN) for s in (-1, 1)]
    collar = np.vstack([tops[0], collar_rim(neck)[:, :2], tops[1]])
    far = [at(CLIP_FAR, ARMPIT_Y), at(CLIP_FAR, TOP_HEM_Y), at(-CLIP_FAR, TOP_HEM_Y), at(-CLIP_FAR, ARMPIT_Y)]
    return np.vstack([left[::-1], collar, right, far])


def torso_rows(chest, pelvis, body, turned=False):
    """Rib rows across the visible torso: (levels, 2 ends, xy px)."""
    levels = np.linspace(RIB_TOP_Y, TOP_HEM_Y, RIB_LEVELS)
    return np.array([body.map(torso_ring(chest, pelvis, y, TOP_EASE, ends(torso_arc(chest, pelvis, y, TOP_EASE, 2, turned)))
                              [:, :2]) for y in levels])


def collar_rows(neck, body):
    """Rib rows around the visible collar, rim down to the join: (levels, 2 ends, xy px)."""
    levels = np.linspace(COLLAR_TOP_Y, COLLAR_JOIN_Y, RIB_LEVELS // 3)
    return np.array([body.map(neck.ring(y, COLLAR_EASE, ends(neck.arc(y, COLLAR_EASE, 2)))[:, :2]) for y in levels])


def ends(thetas):
    return (thetas[0], thetas[-1])


def top_rest_mask(res, body, chest, pelvis, neck):
    """Turned figure: the knit top kept between the armholes on front and back (rest coordinates)."""
    rx, ry, _ = surface_sides(res, body, chest, pelvis)
    collar = neck.radius(0.0, COLLAR_EASE) + TOP_COLLAR_MARGIN
    hw = loft_section(ARMPIT_Y)[0] + TOP_EASE
    limit = np.interp(ry, [ARMHOLE[0][1] - 0.2, ARMHOLE[0][1], ARMHOLE[1][1], ARMPIT_Y, ARMPIT_Y + 0.01],
                      [max(collar, ARMHOLE[0][0]), ARMHOLE[0][0], ARMHOLE[1][0], hw, CLIP_FAR])
    keep = ((np.abs(rx) <= limit) & (ry <= TOP_HEM_Y)).astype(np.float32)
    # the rest coordinates come from a creased height field: a wide blur and a re-sharpened edge
    # turn the stair-stepped armhole into a smooth cut
    soft = cv2.GaussianBlur(keep, (0, 0), body.px(TOP_MASK_SMOOTH))
    return np.clip((soft - 0.5) * TOP_MASK_EDGE + 0.5, 0, 1).astype(np.float32)


def cut_edge_line(cut, cover, width_px):
    """Ink along the edge of a cut inside a form (px coverage).

    The armhole of a turned top is cut by rest coordinates read back from the form's own surface.
    Its line is drawn on that edge: a line traced along the rest-coordinate armhole sits on a
    slightly different surface and runs over the bare skin of the armpit.
    """
    kept = (cut > 0.5).astype(np.uint8)
    inside = cv2.erode((cover > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
    dist = cv2.distanceTransform(kept, cv2.DIST_L2, 3)
    line = np.clip(width_px / 2 - dist + 1.0, 0, 1) * kept * inside
    return line.astype(np.float32)


def rib_paths(res, height_px, rows, count, unit):
    """Knit ribs that run down the surface (px paths).

    Each row crosses the front of the form. Along it the ribs sit at equal steps of surface
    length (from the height field), so they spread over the bust, crowd toward the sides and
    gather at the waist, the way a stretched rib knit reads.
    """
    y0, x0 = res.box[0], res.box[1]
    hh, ww = height_px.shape
    height_px = cv2.GaussianBlur(height_px, (0, 0), max(1.0, RIB_HEIGHT_BLUR * unit))
    fractions = (np.arange(count) + 0.5) / count
    ribs = np.full((count, len(rows), 2), np.nan)
    for j, ends in enumerate(rows):
        t = np.linspace(0, 1, RIB_SAMPLES)
        pts = ends[0] + (ends[1] - ends[0]) * t[:, None]
        ii = np.clip(np.round(pts[:, 1]).astype(int) - y0, 0, hh - 1)
        jj = np.clip(np.round(pts[:, 0]).astype(int) - x0, 0, ww - 1)
        inside = res.sdf_px[ii, jj] < 0
        if inside.sum() < 4:
            continue
        pts, h = pts[inside], height_px[ii, jj][inside]
        step = np.hypot(*np.diff(pts, axis=0).T)
        rise = np.minimum(np.abs(np.diff(h)), step * RIB_SLOPE_CAP)
        arc = np.concatenate([[0.0], np.cumsum(np.hypot(step, rise))])
        for k, f in enumerate(fractions):
            ribs[k, j] = [np.interp(f * arc[-1], arc, pts[:, 0]), np.interp(f * arc[-1], arc, pts[:, 1])]
    paths = []
    for rib in ribs:
        ok = ~np.isnan(rib[:, 0])
        if ok.sum() < 4:
            continue
        r = rib[ok]
        r[:, 0] = cv2.GaussianBlur(r[:, 0].reshape(-1, 1), (1, 0), RIB_SMOOTH).ravel()
        paths.append(r)
    return paths


def build_top(fb, body, pieces, pose, pal, lw, z, z_inner):
    """Sleeveless rib-knit turtleneck: body and collar are one knit form cut at the armholes."""
    chest, pelvis = body_frames(pose)
    neck = NeckAxis(pose, chest)
    cloth = pal['cloth']
    cl = line_color(cloth)
    form = grown([p for p in pieces if p.name in TOP_PIECES], TOP_EASE) + [collar_piece(neck)]
    res = fb.build('cloth', 'cloth', z, form, color=cloth, line_color=cl, self_shadow=False)
    main = res.drawables[0]
    main.normal_map = knit_normals(main.normal_map, body.px(TOP_NORMAL_BLUR))
    h, w = main.mask.arr.shape
    if neck.turned:
        cut = top_rest_mask(res, body, chest, pelvis, neck)
        cut_line = cut_edge_line(cut, main.mask.arr, lw * TOP_CUT_LINE)
    else:
        clip = raster.fill_mask([body.map(top_clip(chest, pelvis, neck))], fb.shape)
        cut = raster.crop_patch(clip, main.mask.y0, main.mask.x0, h, w)
    main.mask = patch_of(main.mask.arr * cut, main.mask.y0, main.mask.x0)
    lines = main.line_mask.arr * cut
    if neck.turned:                          # the armholes are drawn along the cut itself (see cut_edge_line)
        lines = np.maximum(lines, cut_line)
    main.line_mask = patch_of(lines, main.line_mask.y0, main.line_mask.x0)
    rim = body.map(neck.ring(COLLAR_TOP_Y, COLLAR_EASE, neck.arc(COLLAR_TOP_Y, COLLAR_EASE, 40, COLLAR_FRONT_DROP),
                             COLLAR_FRONT_DROP)[:, :2]) if neck.turned else body.map(collar_rim(neck)[:, :2])
    fold_y = COLLAR_TOP_Y + COLLAR_FOLD * (COLLAR_JOIN_Y - COLLAR_TOP_Y)
    fold = body.map(neck.ring(fold_y, COLLAR_EASE, neck.arc(fold_y, COLLAR_EASE, 40, COLLAR_FRONT_DROP),
                              COLLAR_FRONT_DROP)[:, :2])
    armholes = [] if neck.turned else [body.map(p) for p in armhole_paths(chest, pelvis, neck, 0.0)]
    main.strokes = ([edge_stroke(p, lw, 1.1, 0.15, 0.0) for p in armholes]
                    + [edge_stroke(rim, lw, 1.0, 0.05, 0.05), edge_stroke(fold, lw, 0.8, 0.15, 0.15)])
    main.receives_hair = False
    height = res.height * body.unit
    paths = (rib_paths(res, height, torso_rows(chest, pelvis, body, neck.turned), RIB_COUNT, body.unit)
             + rib_paths(res, height, collar_rows(neck, body), COLLAR_RIB_COUNT, body.unit))
    ribs = [geom.stroke_polygon(p, lw * 0.35 * geom.taper(len(p), 0.15, 0.0)) for p in paths]
    edges = [] if neck.turned else [geom.stroke_polygon(body.map(p), lw * 1.1) for p in collar_sides(neck)]
    return list(res.drawables) + [
        Drawable('cloth_ribs', 'cloth', z + 0.01, fill=None, strokes=ribs, clip=['cloth'], line_color=lighten(cl, 0.2)),
        Drawable('cloth_edges', 'cloth', z + 0.02, fill=None, strokes=edges, clip=['cloth'], line_color=cl),
        build_collar_inner(neck, body, pal, lw, z_inner)]


# ---------------------------------------------------------------- belt

def belt_band(chest, pelvis, n=48, turned=False):
    """Belt outline in head units (perspective) and the ring centre and half-width at mid height."""
    thetas = torso_arc(chest, pelvis, (BELT_TOP_Y + BELT_BOTTOM_Y) / 2, BELT_EASE, n, turned)
    top = perspective(torso_ring(chest, pelvis, BELT_TOP_Y, BELT_EASE, thetas))
    bottom = perspective(torso_ring(chest, pelvis, BELT_BOTTOM_Y, BELT_EASE, thetas))
    return np.vstack([top, bottom[::-1]])


def ring_normals(poly_px, left_px, right_px):
    """Normals of a band wrapped around a vertical cylinder, over the band's bounding box."""
    x0, y0 = np.floor(poly_px.min(axis=0)).astype(int) - 2
    x1, y1 = np.ceil(poly_px.max(axis=0)).astype(int) + 2
    xs = np.arange(x0, x1, dtype=np.float32)
    u = np.clip((xs - (left_px + right_px) / 2) / max((right_px - left_px) / 2, 1.0), -0.98, 0.98)
    row = np.stack([u, np.zeros_like(u), np.sqrt(1 - u * u)], axis=1)
    return raster.Patch(int(y0), int(x0), np.repeat(row[None], y1 - y0, axis=0).astype(np.float32))


def build_belt(body, pose, pal, lw, z):
    chest, pelvis = body_frames(pose)
    turned = abs(getattr(pose, 'turn', 0.0)) > 1e-9
    poly = body.map(belt_band(chest, pelvis, turned=turned))
    mid = (BELT_TOP_Y + BELT_BOTTOM_Y) / 2
    arc = ends(torso_arc(chest, pelvis, mid, BELT_EASE, 2, turned))
    sides = body.map(perspective(torso_ring(chest, pelvis, mid, BELT_EASE, (arc[0], 0.0, arc[1]))))
    color = pal['belt']
    belt = Drawable('belt', 'leather', z, fill=[poly], color=color, line_color=line_color(color),
                    strokes=[geom.stroke_polygon(np.vstack([poly, poly[:1]]), lw * 0.8)],
                    normal_map=ring_normals(poly, sides[0][0], sides[2][0]))
    belt.receives_hair = False
    if turned and surface_rest(chest, pelvis, [(0.0, mid)])[1][0, 2] < FACING_MIN:
        return [belt]                                   # the buckle is on the far side
    c = sides[1]
    buckle = geom.ellipse(c[0], c[1], body.px(BUCKLE_RX), body.px(BUCKLE_RY), 24)
    return [belt, Drawable('buckle', 'metal', z + 0.01, fill=[buckle], color=pal['metal'],
                           strokes=[geom.stroke_polygon(np.vstack([buckle, buckle[:1]]), lw * 0.7)],
                           line_color=darken(pal['metal'], 0.4), form_radius=body.px(0.03), casts=False)]


# ---------------------------------------------------------------- skirt shape

class HangFrame:
    """Rest skirt coordinates -> world. Down to the hips the cloth moves with the posed pelvis;
    below, it hangs plumb (no pelvis roll), so a hip shift tilts the waistband, not the hem."""

    def __init__(self, chest, pelvis, turn=0.0):
        self.chest, self.pelvis = chest, pelvis
        self.hip_rest = np.array([0.0, HANG_Y, loft_section(HANG_Y)[2]])
        self.hip_world = A._torso_point(chest, pelvis, self.hip_rest)
        self.R = A.rot(turn)                        # a turned figure: the plumb part turns with the body

    @staticmethod
    def weight(y):
        t = np.clip((y - HANG_Y) / HANG_BLEND, 0, 1)
        return t * t * (3 - 2 * t)

    def to_world(self, rest):
        rest = np.asarray(rest, float)
        posed = A._torso_point(self.chest, self.pelvis, rest)
        w = self.weight(rest[1])
        return posed * (1 - w) + (self.hip_world + self.R @ (rest - self.hip_rest)) * w

    def to_rest(self, world):
        world = np.asarray(world, float)
        posed = np.asarray(A.PELVIS_ORIGIN, float) + self.pelvis.R.T @ (world - self.pelvis.origin)
        w = self.weight(posed[1])
        return posed * (1 - w) + (self.R.T @ (world - self.hip_world) + self.hip_rest) * w


def body_spheres(pieces, frame):
    """Hips, belly and legs as (rest centre, radius) spheres sampled along their solids."""
    out = []
    for pc in pieces:
        if pc.name not in SKIRT_PIECES:
            continue
        for s in pc.solids:
            if s.b is None:
                out.append((frame.to_rest(s.a), s.ra))
                continue
            for t in np.linspace(0, 1, CONE_SAMPLES):
                out.append((frame.to_rest(s.a + (s.b - s.a) * t), s.ra + (s.rb - s.ra) * t))
    return out


def level_points(y, spheres):
    """Rest (x, z) points of the body outline at level y: loft section plus sphere slices."""
    pts = []
    rows = A.loft_rows()
    if rows[0, 0] <= y <= rows[-1, 0]:
        hw, hd, zc = loft_section(y)
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        pts += list(zip(hw * np.sin(a), zc + hd * np.cos(a)))
    ring = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    for c, r in spheres:
        dy = abs(c[1] - y)
        if dy < r:
            rr = np.sqrt(r * r - dy * dy)
            pts += list(zip(c[0] + rr * np.cos(ring), c[2] + rr * np.sin(ring)))
    return np.array(pts) if pts else np.zeros((0, 2))


def drape(raw, slope, step, sign):
    """Cloth falls from every contact at a fixed slope: running envelope of the body extent."""
    out = raw.copy()
    for i in range(1, len(out)):
        out[i] = sign * max(sign * raw[i], sign * out[i - 1] + slope * step)
    return out


def skirt_rings(pieces, pose, hem_y, flare, top_y=SKIRT_TOP_Y):
    """Skirt sections per rest level: arrays (levels, cx, cz, a, b) in rest coordinates."""
    spheres = body_spheres(pieces, HangFrame(*body_frames(pose), getattr(pose, 'turn', 0.0)))
    levels = np.arange(top_y, hem_y + 1e-6, SKIRT_STEP)
    raw = np.zeros((len(levels), 4))                    # right, left, front, back
    for i, y in enumerate(levels):
        p = level_points(y, spheres)
        raw[i] = (p[:, 0].max() + SKIRT_EASE, p[:, 0].min() - SKIRT_EASE,
                  p[:, 1].max() + SKIRT_EASE, p[:, 1].min() - SKIRT_EASE)
    half = (raw[:, 0] - raw[:, 1]) / 2
    hip = int(np.argmax(half))
    slope = max(SKIRT_MIN_SLOPE, (flare - half[hip]) / max(hem_y - levels[hip], 1e-3))
    right = drape(raw[:, 0], slope, SKIRT_STEP, 1)
    left = drape(raw[:, 1], slope, SKIRT_STEP, -1)
    front = drape(raw[:, 2], slope * SKIRT_DEPTH_SLOPE_K, SKIRT_STEP, 1)
    back = drape(raw[:, 3], slope * SKIRT_DEPTH_SLOPE_K, SKIRT_STEP, -1)
    cx, a = (right + left) / 2, (right - left) / 2
    cz, b = (front + back) / 2, (front - back) / 2
    for i, y in enumerate(levels):
        a[i], b[i] = contain(level_points(y, spheres), cx[i], cz[i], a[i], b[i])
    cx, cz, a, b = (gaussian_1d(v, SKIRT_SMOOTH) for v in (cx, cz, a, b))
    return levels, cx, cz, np.maximum.accumulate(a), np.maximum.accumulate(b), levels[hip]


def contain(points, cx, cz, a, b):
    """Grow an ellipse until it holds the body points: depth first, so the front outline stays on
    the hips; whatever depth cannot hold (points at the sides) scales both axes."""
    if not len(points):
        return a, b
    ux = (points[:, 0] - cx) / a
    mid = np.abs(ux) < CONTAIN_SIDE
    if mid.any():
        need = (np.abs(points[mid, 1] - cz) / np.sqrt(1 - ux[mid] ** 2)).max() + SKIRT_EASE
        b = min(max(b, need), b * CONTAIN_MAX_DEPTH)
    reach = np.sqrt(ux ** 2 + ((points[:, 1] - cz) / b) ** 2).max()
    scale = max(1.0, reach)
    return a * scale, b * scale


def gaussian_1d(values, sigma):
    return cv2.GaussianBlur(np.asarray(values, np.float64).reshape(-1, 1), (1, 0), sigma).ravel()


def fold_field(thetas, levels, hip_y, hem_y, rng, fold_depth=FOLD_DEPTH):
    """Radial fold multiplier (levels x thetas): flat at the hips, deepest at the hem."""
    p1, p2, p3 = rng.uniform(0, 2 * np.pi, 3)               # three harmonics: folds of uneven size and spacing
    wave = (0.55 * np.cos(FOLD_COUNT * thetas + p1) + 0.30 * np.cos((FOLD_COUNT + 3) * thetas + p2)
            + 0.15 * np.cos((FOLD_COUNT - 3) * thetas + p3))
    t = np.clip((levels - hip_y) / max(hem_y - hip_y, 1e-3), 0, 1)
    depth = fold_depth * t * t * (3 - 2 * t)
    return 1 + depth[:, None] * wave[None, :], wave


def skirt_surface(pieces, pose, hem_y, flare, rng, top_y=SKIRT_TOP_Y, fold_depth=FOLD_DEPTH):
    """World points (levels x thetas x 3) of the skirt, its thetas and fold wave, and the hip level."""
    frame = HangFrame(*body_frames(pose), getattr(pose, 'turn', 0.0))
    levels, cx, cz, a, b, hip_y = skirt_rings(pieces, pose, hem_y, flare, top_y)
    side = np.pi / 2 + SKIRT_THETA_EXTRA
    centre = 0.0
    if abs(getattr(pose, 'turn', 0.0)) > 1e-9:            # the visible half is centred on the view, not the front
        arc = torso_arc(*body_frames(pose), HANG_Y, 0.0, 64, True)
        centre = (arc[0] + arc[-1]) / 2
    thetas = np.linspace(centre - side, centre + side, SKIRT_THETA_STEPS)
    folds, wave = fold_field(thetas, levels, hip_y, hem_y, rng, fold_depth)
    pts = np.zeros((len(levels), len(thetas), 3))
    for i, y in enumerate(levels):
        for j, t in enumerate(thetas):
            m = folds[i, j]
            pts[i, j] = frame.to_world((cx[i] + a[i] * m * np.sin(t), y, cz[i] + b[i] * m * np.cos(t)))
    return pts, thetas, wave, hip_y


# ---------------------------------------------------------------- skirt raster

def mesh_normals(pts):
    """Outward unit normals of a (levels x thetas) grid of world points."""
    du = np.gradient(pts, axis=1)
    dv = np.gradient(pts, axis=0)
    n = np.cross(du, dv)
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-9)
    return n


def paint_mesh(px, normals, depth, box, ss):
    """Painter's z-order fill of the grid quads: (coverage at ss x, normals at 1x) over box."""
    y0, x0, y1, x1 = box
    cover = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    nmap = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    quads = []
    for i in range(px.shape[0] - 1):
        for j in range(px.shape[1] - 1):
            q = np.array([px[i, j], px[i, j + 1], px[i + 1, j + 1], px[i + 1, j]])
            nq = normals[i:i + 2, j:j + 2].reshape(-1, 3).mean(axis=0)
            quads.append((depth[i:i + 2, j:j + 2].mean(), q, nq / max(np.linalg.norm(nq), 1e-9)))
    for _, q, nq in sorted(quads, key=lambda e: e[0]):
        rel = q - (x0, y0)
        cv2.fillConvexPoly(cover, np.round(rel * ss).astype(np.int32), 255)
        cv2.fillConvexPoly(nmap, np.round(rel).astype(np.int32), tuple(float(v) for v in nq))
    return cover, nmap


def smooth_normals(nmap, coverage, sigma):
    w = coverage.astype(np.float32)
    num = cv2.GaussianBlur(nmap * w[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(w, (0, 0), sigma)[..., None]
    n = np.where(den > 0.05, num / np.maximum(den, 1e-6), nmap)
    n[..., 2] = np.maximum(n[..., 2], 0.05)
    return (n / np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6)).astype(np.float32)


def coverage_sdf(cover_ss, ss):
    """Coverage (1x) and a signed distance in px (negative inside) from a supersampled mask."""
    inside = cv2.distanceTransform(cover_ss, cv2.DIST_L2, 3)
    outside = cv2.distanceTransform(255 - cover_ss, cv2.DIST_L2, 3)
    h, w = cover_ss.shape[0] // ss, cover_ss.shape[1] // ss
    sdf = cv2.resize((outside - inside) / ss, (w, h), interpolation=cv2.INTER_AREA)
    cov = cv2.resize(cover_ss.astype(np.float32) / 255, (w, h), interpolation=cv2.INTER_AREA)
    return cov, sdf


def fold_lines(px, normals, wave, hip_y, levels, lw):
    """Ink at the fold valleys facing the viewer, running up from the hem (px stroke polygons)."""
    valleys = [j for j in range(1, len(wave) - 1) if wave[j] < wave[j - 1] and wave[j] <= wave[j + 1]]
    start = int(np.searchsorted(levels, levels[-1] - FOLD_LINE_LENGTH * (levels[-1] - hip_y)))
    out = []
    for j in valleys:
        if normals[-1, j, 2] < FOLD_LINE_FACING:
            continue
        path = px[start:, j]
        if len(path) < 3:
            continue
        path = geom.resample(path, 24)
        out.append(geom.stroke_polygon(path, lw * 0.6 * geom.taper(24, 0.9, 0.05)))
    return out


def build_skirt(fb, body, pieces, pose, outfit, pal, lw, rng, z, name='skirt', color=None, top_y=SKIRT_TOP_Y):
    """A-line skirt hung from the waist: rests on the hips, falls at a slope, folds toward the hem.
    name, color, top_y: the same hanging cloth as the skirt of a long coat."""
    hem_y = outfit.get('skirt_length', 6.2)
    pts, thetas, wave, hip_y = skirt_surface(pieces, pose, hem_y, outfit.get('skirt_flare', 1.15), rng, top_y,
                                             outfit.get('skirt_folds', FOLD_DEPTH))
    levels = np.arange(top_y, hem_y + 1e-6, SKIRT_STEP)
    shape = pts.shape
    px = body.map(perspective(pts.reshape(-1, 3))).reshape(shape[0], shape[1], 2)
    normals = mesh_normals(pts)
    hgt, wid = fb.shape
    x0, y0 = np.maximum(np.floor(px.reshape(-1, 2).min(axis=0)).astype(int) - 4, 0)
    x1, y1 = np.ceil(px.reshape(-1, 2).max(axis=0)).astype(int) + 4
    x1, y1 = min(x1, wid), min(y1, hgt)
    box = (int(y0), int(x0), int(y1), int(x1))
    cover_ss, nmap = paint_mesh(px, normals, pts[..., 2], box, SKIRT_SUPERSAMPLE)
    cov, sdf = coverage_sdf(cover_ss, SKIRT_SUPERSAMPLE)
    nmap = smooth_normals(nmap, cov, max(1.0, body.px(NORMAL_BLUR)))
    lines = np.clip(fb._line_width(sdf) / 2 - np.abs(sdf) + 0.5, 0, 1)
    color = pal['skirt'] if color is None else color
    skirt = Drawable(name, 'skirt', z, color=color, line_color=line_color(color),
                     mask=patch_of(cov, y0, x0), line_mask=patch_of(lines, y0, x0),
                     normal_map=raster.Patch(int(y0), int(x0), nmap),
                     strokes=fold_lines(px, normals, wave, hip_y, levels, lw))
    skirt.receives_hair = False
    return [skirt]
