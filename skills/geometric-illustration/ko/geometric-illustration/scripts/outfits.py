"""Outfit recipes for the clothed figure (upper-body and full framing).

Why: each outfit is a short recipe over the garment blocks (garment_kit): which body pieces a
layer covers, how much cloth thickness it adds, where it is cut, and the few lines an
illustrator draws on it (hems, seams, pockets, lapels). All cut lines are given in rest torso
coordinates (rig_anatomy: x across, y down from the head centre, head widths) or as points
along a limb, so every outfit follows any pose.

Layers (z): swimwear, innerwear and sleeveless tops sit under the re-drawn arms; anything with
sleeves sits above them and is hidden only where a bare hand or forearm passes in front.
"""
from dataclasses import dataclass, replace

import numpy as np

import garment3d as G
import geom
import rig_anatomy as A
import garment_kit as K
from palette import darken

Z_UNDER_BOTTOM, Z_UNDER_TOP = 1.95, 2.0          # swimwear, innerwear, crop top: under the arms
Z_BOTTOM, Z_BELT = 2.1, 2.3                       # trousers, jeans, joggers
Z_SHIRT, Z_TOP = 2.55, 2.6                        # sleeved layers: over the arms (bare hands block them)
HALTER_NECK_Y, HALTER_EASE, HALTER_W = 0.86, 0.01, 0.022   # halter tie: height on the neck, offset, width
HALTER_VIA = (0.20, 1.12)                          # rest point the halter passes on its way up
HALTER_WRAP = 1.6                                  # radians the string is followed past the side of the neck
NECK_FIT_MAX = 1.35                                # a measured neck ring is at most this much wider than the cone
Z_HOOD = -0.5                                     # behind the neck and shoulders, in front of the back hair
HOOD_Y, HOOD_REACH, HOOD_R = 0.92, 0.40, 0.19     # the hood lies in a horseshoe round the back of the neck
HOOD_ARC = (0.40, 1.60)                            # fractions of pi: from beside the neck round the back
HOOD_RIM_Y, HOOD_RIM_W, HOOD_RIM_DROP = 0.90, 0.07, 0.14   # the rim band round the neck: height, width, front scoop
NECK_BASE_Y = 0.93                # where the shoulders meet the neck at the sides: an open neckline starts here
SHOES = {'turtleneck_sleeveless': 'pumps', 'bikini': 'none', 'innerwear': 'none', 'crop_hotpants': 'sneakers',
         'tee_jeans': 'sneakers', 'suit': 'pumps', 'hoodie_joggers': 'sneakers', 'swim_trunks': 'none',
         'shirt_slacks': 'pumps', 'knit_coat': 'pumps', 'polo_shorts': 'sneakers', 'tank_shorts': 'sneakers',
         'denim_jacket': 'sneakers', 'track_suit': 'sneakers'}
TORSO = ('torso', 'torso_soft', 'breasts', 'pecs')    # either chest form; only one exists per build
LEGS = ('leg_-1', 'leg_1')
HIPS = ('torso', 'torso_soft', 'glutes')
SHORTS_MAX = 0.6                  # legs cut shorter than this (fraction of the thigh) are shorts
INSEAM_TOP = 3.98                 # rest level where the inseam of shorts starts
TRUNKS_WAIST_Y, TRUNKS_LENGTH = 3.02, 0.45   # rest waist level; legs end 45% down the thigh
TRUNKS_STRIPE_THETA = 1.25                   # radians round the leg from the front: the side stripe
BRIDGE_NECK = (1.05, -0.70, -0.06)  # chest frame (x in neck radii): the bridge starts beside the neck, below the neckline
BRIDGE_TOP, BRIDGE_R = 0.50, (0.10, 0.60)  # bridge end: below the arm top by this fraction of its radius; radii
SLEEVE_START = 0.6                # the sleeve form starts inside the cap (fraction of SHOULDER_CAP): no gap, no top arc
CAP_ATTACH_K = 0.14               # the cap melts into the shoulders like the body's own arm root
TEE_SLEEVE_EASE = 0.09            # a tee sleeve is a loose tube: tight sleeves read as puff sleeves
SHOULDER_CAP = 0.22               # the top of the sleeve (fraction of the upper arm) is part of the top's body
NECK_CUT_EASE = 0.08              # neckline cuts follow this ring round the neck (at least the cloth's ease)
JACKET_NECK_Y = 0.92              # the jacket collar wraps the neck just below the shirt collar (0.88)
OPEN_TOP_Y = 0.80                 # an open front reaches above the collar ring: no sliver of collar across the throat
NECK_RAMP_RUN = 0.40              # head units: past the ring's ends a neckline cut eases onto the shoulder this far
NECK_RAMP_RISE = 0.01             # head units above the cloth's ease: where the eased cut ends over the shoulder
NECK_RAMP_STEPS = 9               # points on each eased ramp
HEM_MARGIN = 0.02                 # a limb hem cut reaches this far past the tube (its rounded end must not show)
LIMB_FOOT_REACH, LIMB_FOOT_MARGIN = 0.5, 0.08   # turned figure: a hem cut stays on its limb, this far down and wide
LOOSE_BUST = 0.8                  # loose tops soften the bust form they hang from
FORM_EDGE_MARGIN_PX = 0.5         # an edge line drawn to the cloth outline stops this far inside it
LONG_SLEEVE, POCKET_SLEEVE = 1.5, 2.04   # a long sleeve of a hand in a pocket reaches past the wrist
LEG_BLOCK_GAP = 0.12              # (of the limb) a bare leg hides other cloth only from this far past its hem


@dataclass
class Ctx:
    fb: object
    body: object
    pieces: list
    joints: dict
    pose: object
    pal: object
    lw: float
    rng: object
    chest: object = None
    pelvis: object = None
    res: object = None                # the body's FormResult: depth for straps that wrap round the body

    def __post_init__(self):
        self.chest, self.pelvis = G.body_frames(self.pose)
        self.neck = G.NeckAxis(self.pose, self.chest)
        pocket = [f'hand_{s}' for s in (-1, 1) if self.pose.arms[s].hand == 'pocket']   # hidden in the cloth
        self.arms = [p.name for p in self.pieces if p.name.startswith(('arm_', 'hand_'))
                     and not p.name.startswith(tuple(pocket) or ('\0',))]
        self.turned = abs(getattr(self.pose, 'turn', 0.0)) > 1e-9
        # bare legs hide the cloth of the other leg where they pass in front (turned or seated figures)
        self.overlap_legs = list(LEGS) if self.turned or self.pose.prop == 'chair' else []
        self.cloth_covers = []           # grown torso pieces of the tops: they hide the lifted bare arms behind them

    def cover(self, pieces):
        """Registers a top's grown torso pieces. The figure draws its arms above the clothes; a turned
        figure's far arm passes behind the torso cloth, and there the cloth must hide it."""
        self.cloth_covers += [replace(p, contours=False, skip_contour_with=[]) for p in pieces]

    def piece(self, name):
        return next(p for p in self.pieces if p.name == name)

    def surf(self, pts):
        return K.surface_px(self.body, self.chest, self.pelvis, pts)

    def j(self, key, s):
        return self.joints[f'{key}_{s}']

    # -- turned figures: rest-coordinate recipes drawn only where they face the viewer --

    def arc(self, y, ease, n=32):
        """Body angles of the visible half of the torso ring at rest level y."""
        return G.torso_arc(self.chest, self.pelvis, y, ease, n, self.turned)

    def facing(self, pts_rest, back=False):
        """True where rest points on the front (or back) of the torso face the viewer."""
        if not self.turned:
            return np.full(len(pts_rest), not back)
        return G.surface_rest(self.chest, self.pelvis, pts_rest, back)[1][:, 2] > G.FACING_MIN

    def paths(self, rest_list, n=24, back=False):
        """Pixel paths of rest-coordinate polylines on the torso front (or back), visible parts only.

        Front view: the classic smoothing of the projected points. Turned: the polyline is
        smoothed in rest coordinates, sampled densely and split where it turns away.
        """
        if not self.turned:
            return [] if back else [K.smooth_path(self.surf(p), n) for p in rest_list]
        out = []
        for p in rest_list:
            rest = K.smooth_path(np.asarray(p, float), max(n, 8) * 4)
            pts, nrm = G.surface_rest(self.chest, self.pelvis, rest, back)
            out += K.visible_runs(self.body.map(pts[:, :2]), nrm[:, 2] > G.FACING_MIN)
        return out

    def strap_rest(self, name, group, z, segments, width, color, clip=None, lift=0.012):
        """A strap through rest-coordinate stretches on the torso: [(points, 'front'|'back'|'free'), ...].
        'free' points are rest (x, y, z) points off the loft (the top of the shoulder).

        The points are lifted off the loft, their depth is taken from the drawn body where they face
        the viewer, and K.strap hides the rest.
        """
        pts, nrm = [], []
        for rest, side in segments:
            rest = np.asarray(rest, float)
            if side == 'free':                           # rest 3D points off the loft (over the shoulder)
                p = np.array([A._torso_point(self.chest, self.pelvis, q) for q in rest])
                n = np.tile(self.chest.R @ A.unit((0.0, -1.0, 0.05)), (len(p), 1))
            else:
                r = K.smooth_path(rest, max(len(rest), 2) * 12) if len(rest) > 1 else rest
                p, n = G.surface_rest(self.chest, self.pelvis, r, side == 'back', lift)
            pts.append(p)
            nrm.append(n)
        pts, nrm = np.vstack(pts), np.vstack(nrm)
        snap = nrm[:, 2] > G.FACING_MIN
        if snap.any():
            pts[snap] = K.surface_points(self.res, self.body, self.body.map(pts[snap][:, :2]), lift)
        return K.strap(name, group, z, pts, self.body.px(width), color, self.lw, self.res, self.body, normals=nrm,
                       clip=clip)

    def patch(self, name, group, z, rest_poly, color, form_px=0.0, back=False):
        """A small flat shape on the torso (tie, collar point, pocket flap): [] where it faces away."""
        if not self.turned:
            return [] if back else [K.patch_shape(name, group, z, self.surf(rest_poly), color, self.lw, form_px)]
        if not self.facing([np.mean(rest_poly, axis=0)], back)[0]:
            return []
        pts = G.surface_rest(self.chest, self.pelvis, rest_poly, back)[0]
        return [K.patch_shape(name, group, z, self.body.map(pts[:, :2]), color, self.lw, form_px)]

    def points(self, rest_pts, back=False):
        """Pixels of rest points on the torso front (or back) that face the viewer (front view: all front)."""
        if not self.turned:
            return [] if back else list(self.surf(rest_pts))
        pts, nrm = G.surface_rest(self.chest, self.pelvis, rest_pts, back)
        return [q for q, n in zip(self.body.map(pts[:, :2]), nrm) if n[2] > G.FACING_MIN]

    def rest_keep(self, front, back=()):
        """keep_fn for K.form_garment: pixels whose surface lies in rest outlines (front and back)."""
        return lambda res: K.rest_mask(res, self.body, self.chest, self.pelvis, front, back)


MALE_OUTFITS = ('tee_jeans', 'suit', 'hoodie_joggers', 'swim_trunks', 'shirt_slacks', 'knit_coat', 'polo_shorts',
                'tank_shorts', 'denim_jacket', 'track_suit')
MALE_SHOES = {'suit': 'oxfords', 'shirt_slacks': 'oxfords', 'knit_coat': 'oxfords'}
FEMALE_OUTFITS = tuple(k for k in SHOES if k != 'swim_trunks')


def outfit_types(sex='female'):
    return MALE_OUTFITS if sex == 'male' else FEMALE_OUTFITS


SHOE_TYPES = ('pumps', 'sneakers', 'oxfords', 'none')


def shoes_for(kind, sex='female', override=None):
    """Shoes of an outfit (spec outfit.shoes overrides: flat shoes for a walk in the snow, say)."""
    if override is not None:
        if override not in SHOE_TYPES:
            raise ValueError(f"unknown outfit.shoes '{override}' (use {', '.join(SHOE_TYPES)})")
        return override
    return MALE_SHOES.get(kind, SHOES[kind]) if sex == 'male' else SHOES[kind]


# ---------------------------------------------------------------- shared constructions

def limb_cut_point(ctx, limb, s, frac):
    """Point along a limb: 'leg' frac 0 hip .. 1 knee .. 2 ankle; 'arm' 0 shoulder .. 1 elbow .. 2 wrist."""
    a, b, c = ((ctx.j('hip', s), ctx.j('knee', s), ctx.j('ankle', s)) if limb == 'leg'
               else (ctx.j('shoulder', s), ctx.j('elbow', s), ctx.j('wrist', s)))
    return a + (b - a) * frac if frac <= 1 else b + (c - b) * (frac - 1)


def tubes(ctx, garment, limb, prefix, frac, ease):
    """Cut the grown limbs of a garment at frac along the limb: (garment, cut polygons, hem arcs px)."""
    cuts, hems, out = [], [], []
    for p in garment:
        s = next((s for s in (-1, 1) if p.name == f'{prefix}{limb}_{s}'), None)
        if s is None:
            out.append(p)
            continue
        point = limb_cut_point(ctx, limb, s, frac)
        nxt = limb_cut_point(ctx, limb, s, frac + 0.15)
        piece = K.truncate(p, point, extra=0.25)
        out.append(piece)
        toward = ctx.body.map([nxt[:2]])[0] - ctx.body.map([point[:2]])[0]
        cut = K.limb_cut(ctx.body, piece, point, HEM_MARGIN, toward)
        if ctx.turned:                       # limbs overlap on screen: a hem cut must not cut the other limb
            r = max(max(sd.ra, sd.rb if sd.rb is not None else sd.ra) for sd in piece.solids[-3:])
            end = point + (nxt - point) / max(np.linalg.norm(nxt - point), 1e-9) * LIMB_FOOT_REACH
            reach = K.to_px(ctx.body, np.array([point, end]))
            cut = (cut, geom.stroke_polygon(geom.resample(reach, 8), np.full(8, ctx.body.px(2 * r + LIMB_FOOT_MARGIN))))
        cuts.append(cut)
        hems.append(K.to_px(ctx.body, K.limb_ring(piece, point, 0.0, K.front_arc())))
    return out, cuts, hems


def neck_cut(ctx, y, ease, drop):
    """Removes the neck above a neckline ring (y at the sides, dropping at the front)."""
    # one ring radius for every layer: an inner layer cut narrower than the outer one would show beside it
    r = max(ease, NECK_CUT_EASE)
    arc = K.to_px(ctx.body, ctx.neck.ring(y, r, ctx.neck.arc(y, r, 32, drop, level=True), drop, level=True), dip=False)
    up = np.array([0.0, -1.0])
    # Past the ring's ends the cut eases up onto the shoulder: the cloth grown over the trapezius stands
    # above the ring there, so a cut going straight up from the ends would leave a step beside the neck.
    # The curve flattens as it leaves the neck, so it meets the shoulder line without a corner.
    side = np.array([1.0 if arc[-1][0] >= arc[0][0] else -1.0, 0.0])
    t = np.linspace(0.0, 1.0, NECK_RAMP_STEPS)[1:, None]
    rise = ease + NECK_RAMP_RISE                          # the cloth over the trapezius stands about its ease higher
    ramp = side * ctx.body.px(NECK_RAMP_RUN) * t + up * ctx.body.px(rise) * (1.0 - (1.0 - t) ** 2)
    left = arc[0] + ramp * np.array([-1.0, 1.0])          # mirrored: outward at the first end
    right = arc[-1] + ramp
    reach = up * ctx.body.px(K.CUT_REACH)
    return np.vstack([left[::-1][:1] + reach, left[::-1], arc, right, right[-1:] + reach]), arc


def neck_blocker(ctx):
    """The bare neck as a blocker: cloth behind it (the far strap of a turned figure) stays hidden.
    Cloth is drawn over the body whatever its depth, so without it the far strap shows in front of the neck."""
    soft = next(p for p in ctx.pieces if p.name == 'torso_soft')
    solids = [s for s in soft.solids if np.linalg.norm(s.a - ctx.neck.base) < 1e-6]
    return replace(soft, name='neck_block', solids=solids, contours=False, skip_contour_with=[])


def without_neck(ctx, garment):
    """Garment copies without the body's neck cone (an open neckline leaves the neck bare)."""
    out = []
    for p in garment:
        if p.name.endswith('torso_soft'):
            p = replace(p, solids=[s for s in p.solids if np.linalg.norm(s.a - ctx.neck.base) > 1e-6])
        out.append(p)
    return out


def waist_cut(ctx, y, ease):
    """Removes everything above the front waist ring at rest level y; returns (cut, waistline px)."""
    th = ctx.arc(y, ease)
    return (K.torso_cut(ctx.body, ctx.chest, ctx.pelvis, y, ease, upward=True, thetas=th),
            K.to_px(ctx.body, G.torso_ring(ctx.chest, ctx.pelvis, y, ease, th)))


def hem_cut(ctx, y, ease):
    """Removes everything below the front torso ring at rest level y; returns (cut, hem px)."""
    th = ctx.arc(y, ease)
    return (K.torso_cut(ctx.body, ctx.chest, ctx.pelvis, y, ease, upward=False, thetas=th),
            K.to_px(ctx.body, G.torso_ring(ctx.chest, ctx.pelvis, y, ease, th)))


def ring_line(ctx, y, ease):
    return K.to_px(ctx.body, G.torso_ring(ctx.chest, ctx.pelvis, y, ease, ctx.arc(y, ease)))


def mirrored(pts):
    """Rest points given for the figure's left (x > 0) -> (left, right) lists."""
    return [(x, y) for x, y in pts], [(-x, y) for x, y in pts]


def band(ctx, name, group, z, y0, y1, ease, color, buckle=False):
    """A belt or waistband wrapping the torso between rest levels y0 and y1."""
    th = ctx.arc((y0 + y1) / 2, ease, 48)
    top = K.to_px(ctx.body, G.torso_ring(ctx.chest, ctx.pelvis, y0, ease, th))
    bottom = K.to_px(ctx.body, G.torso_ring(ctx.chest, ctx.pelvis, y1, ease, th))
    poly = np.vstack([top, bottom[::-1]])
    d = K.patch_shape(name, group, z, poly, color, ctx.lw)
    d.normal_map = G.ring_normals(poly, top[0][0], top[-1][0])
    out = [d]
    if buckle and (not ctx.turned or ctx.facing([(0.0, (y0 + y1) / 2)])[0]):
        c = (top[len(top) // 2] + bottom[len(bottom) // 2]) / 2
        if ctx.turned:                                   # the buckle sits at the body's front, not mid-view
            c = K.to_px(ctx.body, G.torso_ring(ctx.chest, ctx.pelvis, (y0 + y1) / 2, ease, [0.0]))[0]
        r = ctx.body.px(0.045)
        rect = np.array([c + (-r, -r * 0.8), c + (r, -r * 0.8), c + (r, r * 0.8), c + (-r, r * 0.8)])
        out.append(K.patch_shape(name + '_buckle', 'metal', z + 0.01, rect, ctx.pal['metal'], ctx.lw))
    return out


# ---------------------------------------------------------------- trousers family

def trousers(ctx, name, color, waist_y, length, ease, leg_ease=None):
    """Two grown legs joined at the hips, cut at the waist and at `length` along the legs.

    The body's soft crotch fill is left out: under trousers it would hang between the legs.
    """
    g = K.garment_pieces(ctx.pieces, ('torso', 'glutes') + LEGS, ease, 'g_' + name + '_',
                         ease_by={l: leg_ease or ease for l in LEGS})
    sides = [s for p in g for s in (-1, 1) if p.name == f'g_{name}_leg_{s}']     # the order tubes returns hems in
    g, cuts, hems = tubes(ctx, g, 'leg', 'g_' + name + '_', length, ease)
    wc, waist = waist_cut(ctx, waist_y, ease)
    if length < SHORTS_MAX and not ctx.turned:    # nothing of short trousers hangs below the line across both hems
        left, right = sorted(hems, key=lambda h: h[:, 0].mean())
        left = left if left[0][0] < left[-1][0] else left[::-1]          # outer -> inner
        right = right if right[0][0] < right[-1][0] else right[::-1]     # inner -> outer
        far = ctx.body.px(1.0)
        cuts.append(np.vstack([left, right, right[-1] + (0, far), left[0] + (0, far)]))
        inseam = []
        for back in (False, True):                                       # the inseam: a small inverted V
            if ctx.facing([(0.0, INSEAM_TOP)], back)[0]:
                crotch = K.to_px(ctx.body, G.surface_rest(ctx.chest, ctx.pelvis, [(0.0, INSEAM_TOP)], back)[0])[0] \
                    if ctx.turned else ctx.surf([(0.0, INSEAM_TOP)])[0]
                inseam = [np.array([crotch, left[-1]]), np.array([crotch, right[0]])]
    elif length < SHORTS_MAX:
        inseam = turned_inseam(ctx, dict(zip(sides, hems)))
    else:
        inseam = []
    lines = [K.lines(name + '_hems', Z_BOTTOM + 0.02, hems, ctx.lw, color, k=K.EDGE_K, clip=[name])]
    if inseam:
        lines.append(K.lines(name + '_inseam', Z_BOTTOM + 0.02, inseam, ctx.lw, color, k=0.8, clip=[name], taper=(0.3, 0.0)))
    drawables, res = K.form_garment(ctx.fb, ctx.body, name, 'skirt', Z_BOTTOM, g, color,
                                    blockers=K.occluders(ctx.pieces, ctx.arms) + bare_legs(ctx, length), cuts=[wc] + cuts)
    return drawables + lines, waist


def turned_inseam(ctx, hem_by_side):
    """Shorts of a turned figure: the near leg's opening meets the far one along a line from the crotch
    to the inner end of the near hem. Without it the two loose legs read as one skirt."""
    near = max((-1, 1), key=lambda s: ctx.j('hip', s)[2])          # z points at the viewer
    hem, far_hem = hem_by_side[near], hem_by_side[-near]
    end = min((hem[0], hem[-1]), key=lambda q: abs(q[0] - far_hem[:, 0].mean()))
    for back in (False, True):
        if ctx.facing([(0.0, INSEAM_TOP)], back)[0]:
            crotch = K.to_px(ctx.body, G.surface_rest(ctx.chest, ctx.pelvis, [(0.0, INSEAM_TOP)], back)[0])[0]
            return [np.array([crotch, end])]
    return []


def bare_legs(ctx, length):
    """The legs below a hem, as occluders of the cloth of the other leg (turned or seated figures only).

    They start a little past the hem: at the hem itself the cloth and the leg meet and the cloth must win.
    """
    out = []
    for s in (-1, 1):
        if f'leg_{s}' not in ctx.overlap_legs or length + LEG_BLOCK_GAP >= 2.0:
            continue
        leg = ctx.piece(f'leg_{s}')
        out.append(replace(K.trim_start(leg, limb_cut_point(ctx, 'leg', s, length + LEG_BLOCK_GAP)), contours=False,
                           skip_contour_with=[]))
    return out


def fly_and_pockets(ctx, name, color, waist_y, crotch_y, z):
    """Jeans-style front: fly stitching and two scooped front pockets."""
    fly = [(0.05, waist_y + 0.08), (0.06, crotch_y - 0.22), (0.02, crotch_y - 0.12), (-0.02, crotch_y - 0.10)]
    paths = ctx.paths([fly])
    for s in (-1, 1):
        paths += ctx.paths([[(s * 0.28, waist_y + 0.04), (s * 0.36, waist_y + 0.22), (s * 0.52, waist_y + 0.32),
                             (s * 0.66, waist_y + 0.30)]])
    back = [[(-0.80, waist_y + 0.16), (0.0, waist_y + 0.30), (0.80, waist_y + 0.16)],     # yoke (seen when turned)
            [(0.0, waist_y + 0.30), (0.0, crotch_y - 0.12)]]                                # centre back seam
    for s in (-1, 1):                                                                       # patch pockets
        back.append([(s * 0.16, waist_y + 0.34), (s * 0.54, waist_y + 0.30), (s * 0.54, waist_y + 0.66),
                     (s * 0.36, waist_y + 0.76), (s * 0.18, waist_y + 0.70), (s * 0.16, waist_y + 0.34)])
    paths += ctx.paths(back, back=True)
    return K.lines(name + '_front', z, paths, ctx.lw, color, clip=[name])


def leg_fronts(ctx, name, color, frac0, frac1, z, ease):
    """Lines running down the front of each leg (trouser creases)."""
    paths = []
    for s in (-1, 1):
        g = ctx.piece(f'leg_{s}')
        if not ctx.turned:
            pts = [K.limb_ring(g, limb_cut_point(ctx, 'leg', s, f), ease, [0.0])[0] for f in np.linspace(frac0, frac1, 12)]
            paths.append(K.to_px(ctx.body, np.array(pts)))
            continue
        for back in (0.0, np.pi):                         # the crease runs down the front and the back of the leg
            pts, vis = [], []
            for f in np.linspace(frac0, frac1, 12):
                th = limb_view_thetas(ctx, g, limb_cut_point(ctx, 'leg', s, f), [back])
                pts.append(K.limb_ring(g, limb_cut_point(ctx, 'leg', s, f), ease, th)[0])
                vis.append(np.cos(th[0]) > G.FACING_MIN * 4)
            paths += K.visible_runs(K.to_px(ctx.body, np.array(pts)), vis)
    return K.lines(name + '_creases', z, paths, ctx.lw, color, k=0.5, clip=[name], taper=(0.3, 0.1))


def knee_folds(ctx, name, color, z, ease):
    """Two short curved wrinkles at the front of each knee (denim bunches there)."""
    paths = []
    for s in (-1, 1):
        g = ctx.piece(f'leg_{s}')
        for f, th in ((0.92, 0.25), (1.08, -0.2)):
            point = limb_cut_point(ctx, 'leg', s, f)
            ths = np.linspace(-0.55 + th, 0.35 + th, 8)
            if not ctx.turned:
                paths.append(K.to_px(ctx.body, K.limb_ring(g, point, ease, ths)))
                continue
            ths = limb_view_thetas(ctx, g, point, ths)
            paths += K.visible_runs(K.to_px(ctx.body, K.limb_ring(g, point, ease, ths)), np.cos(ths) > G.FACING_MIN)
    return K.lines(name + '_knees', z, paths, ctx.lw, color, k=0.45, clip=[name], taper=(0.4, 0.4))


def limb_view_thetas(ctx, piece, point, thetas_body):
    """Limb-ring angles (K.ring: theta 0 faces the viewer) for angles measured from the body's front."""
    c = K.limb_ring(piece, point, 0.0, [0.0, np.pi / 2])
    centre = (c[0] + K.limb_ring(piece, point, 0.0, [np.pi])[0]) / 2
    e2, e1 = A_unit(c[0] - centre), A_unit(c[1] - centre)
    front = ctx.pelvis.R @ np.array([0.0, 0.0, 1.0])
    return np.arctan2(np.dot(front, e1), np.dot(front, e2)) + np.asarray(thetas_body, float)


def A_unit(v):
    return v / max(np.linalg.norm(v), 1e-9)


# ---------------------------------------------------------------- tops family

def sleeved_top(ctx, name, color, ease, sleeve_frac, sleeve_ease, neck_y, neck_drop, hem_y, z, group='cloth',
                hip_pieces=False, front_cuts=(), normal_blur=K.LOOSE_BLUR, bust=LOOSE_BUST, neck=False):
    """A top with sleeves.

    The body of the top and each sleeve are separate forms: the hem, neckline and openings cut
    only the body, a cuff only its sleeve (a hanging sleeve passes the hem line). A sleeve is
    hidden where the top's body or a bare hand is in front of it.
    front_cuts: rest outlines removed from the front of the body (an open jacket front).
    """
    prefix = 'g_' + name + '_'
    cap_ease = max(ease, sleeve_ease)
    torso = K.garment_pieces(ctx.pieces, TORSO + (('glutes',) if hip_pieces else ()) + ('arm_-1', 'arm_1'), ease,
                             prefix, bust_scale=bust, ease_by={'arm_-1': cap_ease, 'arm_1': cap_ease})
    for i, p in enumerate(torso):                        # the shoulder caps belong to the body of the top: one
        for s in (-1, 1):                                # rounded shoulder line, the sleeve seam below it
            if p.name == f'{prefix}arm_{s}':
                torso[i] = replace(K.truncate(p, limb_cut_point(ctx, 'arm', s, SHOULDER_CAP)), attach_k=CAP_ATTACH_K)
    if not neck:                                         # only a collar that climbs the neck keeps the neck form
        torso = without_neck(ctx, torso)
    torso += shoulder_bridges(ctx, prefix, cap_ease)
    ctx.cover(torso)
    nc, neckline = neck_cut(ctx, neck_y, ease, neck_drop)
    hc, hem = hem_cut(ctx, hem_y, ease)
    sleeved = [f'arm_{s}' for s in (-1, 1) if ctx.pose.arms[s].hand == 'pocket' and sleeve_frac > LONG_SLEEVE]
    bare = K.occluders(ctx.pieces, [n for n in ctx.arms if n.startswith('hand_')]
                       + [a for a in ('arm_-1', 'arm_1') if a not in sleeved])     # a pocketed arm is all sleeve
    extra = [] if ctx.turned else [ctx.surf(c) for c in front_cuts]
    cut_fn = ctx.rest_keep(front_cuts) if ctx.turned and front_cuts else None
    out, _ = K.form_garment(ctx.fb, ctx.body, name, group, z, torso, color, blockers=bare,
                            cuts=[nc, hc] + extra, normal_blur=normal_blur, cut_fn=cut_fn)
    cuffs, sleeves = [], []
    for s in (-1, 1):
        sprefix = prefix + 'sleeve_'                     # its own names: the cap in the top's body is also an arm
        arm = K.garment_pieces(ctx.pieces, (f'arm_{s}',), sleeve_ease, sprefix)
        arm = [K.trim_start(p, limb_cut_point(ctx, 'arm', s, SHOULDER_CAP * SLEEVE_START)) for p in arm]
        frac = sleeve_frac
        if ctx.pose.arms[s].hand == 'pocket' and sleeve_frac > LONG_SLEEVE:   # the cuff goes into the pocket too
            frac = POCKET_SLEEVE
        arm, cuts, hems = tubes(ctx, arm, 'arm', sprefix, frac, sleeve_ease)
        blockers = bare + [replace(p, contours=False) for p in torso]
        sname = f'{name}_sleeve_{s}'
        d, _ = K.form_garment(ctx.fb, ctx.body, sname, group, z + 0.001, arm, color, blockers=blockers, cuts=cuts,
                              normal_blur=normal_blur)
        out += d
        cuffs += [(h, sname) for h in hems]
        sleeves.append(sname)
    return out, dict(neckline=neckline, hem=hem, cuffs=cuffs, sleeves=sleeves)


def shoulder_bridges(ctx, prefix, ease):
    """Cloth spans the dip between the neck slope and the top of the arm: one cone per side from the
    side of the neck to the top of the shoulder, so the shoulder line of a sleeved top runs straight
    to the sleeve instead of rising into a puff."""
    import mannequin as M
    import rig_anatomy as A
    out = []
    for s in (-1, 1):
        x, y, z = A.SHOULDER_LOCAL
        r0 = A.UPPER_ARM_PROFILE['r'][0]
        a = ctx.chest.p((s * A.NECK_RADII[0] * BRIDGE_NECK[0], BRIDGE_NECK[1], BRIDGE_NECK[2]))   # beside the neck
        b = ctx.chest.p((s * (x - 0.04), y - r0 * BRIDGE_TOP, z))
        out.append(M.Piece(f'{prefix}bridge_{s}', [M.cone(a, b, BRIDGE_R[0] + ease, r0 * BRIDGE_R[1] + ease)], k=0.0,
                           parent=prefix + 'torso', attach_k=0.10, attach_n=1, contours=False))
    return out


def cuff_lines(name, z, edges, lw, color, k=K.EDGE_K):
    return [K.lines(f'{name}_{i}', z, [h], lw, color, k=k, clip=[sname]) for i, (h, sname) in enumerate(edges)]


def fitted_top(ctx, name, color, ease, keep_rest, hem_y, z, edges_rest=(), group='cloth', edges_to_form=False,
               back_rest=(), back_edges=()):
    """A sleeveless body-tight top: grown torso kept inside a rest-coordinate outline.

    edges_to_form: edge lines run up to the cloth's own outline (straps that pass over the
    shoulder line); otherwise they are clipped to the body.
    back_rest, back_edges: outlines and edges on the back (drawn when the figure turns).
    """
    g = without_neck(ctx, K.garment_pieces(ctx.pieces, TORSO, ease, 'g_' + name + '_'))
    ctx.cover(g)
    keep, keep_fn = None, None
    if ctx.turned:
        keep_fn = ctx.rest_keep([K.smooth_path(np.array(closed(k)), 64) for k in keep_rest],
                                [K.smooth_path(np.array(closed(k)), 64) for k in back_rest])
    else:
        keep = [K.smooth_path(ctx.surf(closed(k)), 64) for k in keep_rest]
    cuts = []
    if hem_y is not None:
        cuts.append(hem_cut(ctx, hem_y, ease)[0])
    blockers = [neck_blocker(ctx)] if ctx.turned else []     # a far strap passes behind the neck
    drawables, res = K.form_garment(ctx.fb, ctx.body, name, group, z, g, color, blockers=blockers, keep=keep,
                                    cuts=cuts, keep_fn=keep_fn)
    edge = ctx.paths(edges_rest, 32) + ctx.paths(back_edges, 32, back=True)
    if edges_to_form and res is not None:
        edge = [r for e in edge for r in inside_form(res, e)]
    drawables.append(K.lines(name + '_edges', z + 0.01, edge, ctx.lw, color, k=1.0,
                             clip=None if edges_to_form else ['body']))
    return drawables


def inside_form(res, path_px, margin_px=FORM_EDGE_MARGIN_PX):
    """Stretches of a pixel path inside a form's outline (an edge line that stops at the cloth's edge)."""
    path_px = geom.resample(np.asarray(path_px, float), max(int(np.sum(np.hypot(*np.diff(path_px, axis=0).T))), 2))
    y0, x0 = res.box[0], res.box[1]
    hh, ww = res.sdf_px.shape
    inside = []
    for q in path_px:
        i, j = int(round(q[1])) - y0, int(round(q[0])) - x0
        inside.append(0 <= i < hh and 0 <= j < ww and res.sdf_px[i, j] < -margin_px)
    return [r for r in K.visible_runs(path_px, inside)]


def closed(pts):
    return list(pts) + [pts[0]]


# ---------------------------------------------------------------- outfits

def turtleneck_skirt(ctx, outfit, z):
    ctx.cover(G.grown([p for p in ctx.pieces if p.name in G.TOP_PIECES], G.TOP_EASE))
    out = G.build_top(ctx.fb, ctx.body, ctx.pieces, ctx.pose, ctx.pal, ctx.lw, z['cloth'], z['collar_back'])
    if ctx.pose.prop == 'chair':                         # seated: the skirt lies over the lap
        out += lap_skirt(ctx, ctx.pal['skirt'], z['skirt'])
    else:
        out += G.build_skirt(ctx.fb, ctx.body, ctx.pieces, ctx.pose, outfit, ctx.pal, ctx.lw, ctx.rng, z['skirt'])
    return out + G.build_belt(ctx.body, ctx.pose, ctx.pal, ctx.lw, z['belt'])


def lap_skirt(ctx, color, z, name='skirt'):
    """A skirt on a seated figure: hips and thighs grown by the cloth, bridged over the lap, ending at the knees.

    Why not the hanging skirt: seated, the cloth rests on the thighs instead of falling from the hips;
    it reads as one surface from the waist to the knees, its hem a curve across the knees.
    """
    import mannequin as M
    prefix = f'g_{name}_'
    g = K.garment_pieces(ctx.pieces, ('torso', 'glutes') + LEGS, G.SKIRT_EASE, prefix)
    g, cuts, hems = tubes(ctx, g, 'leg', prefix, LAP_HEM, G.SKIRT_EASE)
    hips = (ctx.j('hip', -1) + ctx.j('hip', 1)) / 2
    knees = (ctx.j('knee', -1) + ctx.j('knee', 1)) / 2
    gap = np.linalg.norm(ctx.j('hip', 1) - ctx.j('hip', -1)) / 2
    a = hips + np.array([0.0, LAP_DROP, 0.0])
    b = a + (knees - a) * LAP_HEM
    g.append(M.Piece(prefix + 'lap', [M.cone(a, b, gap + G.SKIRT_EASE, gap * LAP_TAPER + G.SKIRT_EASE)], k=0.0,
                     parent=prefix + 'torso', attach_k=0.08, attach_n=1, contours=False))
    wc, _ = waist_cut(ctx, G.SKIRT_TOP_Y, G.SKIRT_EASE)
    drawables, _ = K.form_garment(ctx.fb, ctx.body, name, 'skirt', z, g, color,
                                  blockers=K.occluders(ctx.pieces, ctx.arms) + bare_legs(ctx, LAP_HEM), cuts=[wc] + cuts)
    return drawables + [K.lines(f'{name}_hems', z + 0.01, hems, ctx.lw, color, k=K.EDGE_K, clip=[name])]


LAP_HEM = 0.92                    # the seated skirt ends this far toward the knees
LAP_DROP = 0.10                   # the lap bridge sits a little below the hip joints
LAP_TAPER = 0.85                  # and narrows toward the knees


CUP_TRIANGLE = [(0.24, 1.47), (0.40, 1.70), (0.53, 1.95), (0.30, 2.03), (0.05, 2.00), (0.10, 1.72)]
BRIEF_LOW = [(0.72, 3.30), (0.36, 3.40), (0.0, 3.44), (-0.36, 3.40), (-0.72, 3.30), (-0.72, 3.40), (-0.52, 3.58),
             (-0.28, 3.82), (-0.10, 4.03), (0.0, 4.07), (0.10, 4.03), (0.28, 3.82), (0.52, 3.58), (0.72, 3.40)]
# the back of the bottoms covers the seat down to the fold under the buttocks
BRIEF_LOW_BACK = [(0.72, 3.30), (0.36, 3.38), (0.0, 3.42), (-0.36, 3.38), (-0.72, 3.30), (-0.72, 3.40), (-0.62, 3.70),
                  (-0.44, 3.98), (-0.20, 4.08), (0.0, 4.10), (0.20, 4.08), (0.44, 3.98), (0.62, 3.70), (0.72, 3.40)]
BIKINI_BAND_Y = 1.99
NAPE_TAIL = 0.16                  # the halter bow's tails hang this far below the nape (seen from behind)


BUST_CENTRE = (0.255, 1.78)       # rest centre of the standard breast form: cups scale about it
BASE_BREAST_R = 0.20


def bust_fit(pts):
    """Cup outline points scaled to the build's breast form (the standard build keeps them as drawn)."""
    k = A.BREAST[2] / BASE_BREAST_R
    drop = A.BREAST[0][1] + 0.02
    if abs(k - 1) < 1e-9 and abs(drop) < 1e-9:
        return list(pts)
    cx, cy = BUST_CENTRE
    return [(np.sign(x) * cx + (x - np.sign(x) * cx) * k if x else x, cy + drop + (y - cy) * k) for x, y in pts]


def bikini(ctx, outfit, z):
    color, lw = ctx.pal['cloth'], ctx.lw
    cup = bust_fit(CUP_TRIANGLE)
    cups = [cup, [(-x, y) for x, y in cup]]
    out = fitted_top(ctx, 'bikini_top', color, 0.012, cups, None, Z_UNDER_TOP, edges_rest=[closed(c) for c in cups])
    for s in (-1, 1):                                                  # halter strings and back band
        out += halter(ctx, f'bikini_halter_{s}', s, ctx.surf([(s * cup[0][0], cup[0][1])])[0], color, apex=cup[0])
        if ctx.turned:                                                 # the band runs round the back
            side = G.loft_section(BIKINI_BAND_Y)[0]
            out += ctx.strap_rest(f'bikini_band_{s}', 'cloth', Z_UNDER_TOP + 0.02,
                                  [([(s * 0.53, 1.97), (s * side, BIKINI_BAND_Y)], 'front'),
                                   ([(s * side, BIKINI_BAND_Y), (0.0, BIKINI_BAND_Y)], 'back')], 0.022, color)
            continue
        side = ctx.surf([(s * 0.53, 1.97), (s * 0.66, 1.99)])
        out.append(K.ribbon(f'bikini_band_{s}', 'cloth', Z_UNDER_TOP + 0.02, side, ctx.body.px(0.022), color, lw, clip=['body']))
    center = ctx.points([(-0.06, 2.0), (0.06, 2.0)])
    if len(center) == 2:
        out.append(K.ribbon('bikini_center', 'cloth', Z_UNDER_TOP + 0.02, np.array(center), ctx.body.px(0.02), color, lw))
    out += briefs(ctx, 'bikini_bottom', color, BRIEF_LOW, 0.012, back_outline=BRIEF_LOW_BACK)
    for s in (-1, 1):                                                  # side ties
        knots = ctx.points([(s * 0.72, 3.33)])
        if not knots:
            continue
        knot = knots[0]
        for k, dx in enumerate((0.03, -0.02)):
            tail = knot + ctx.body.px(np.array([s * dx, 0.16]))
            out.append(K.ribbon(f'bikini_tie_{s}_{k}', 'cloth', Z_UNDER_BOTTOM + 0.03,
                                np.array([knot, (knot + tail) / 2 + (ctx.body.px(s * 0.02), 0), tail]),
                                ctx.body.px(0.018), color, lw))
    return out


def neck_fit_radius(ctx, y):
    """Radius of a ring at neck height y that touches the drawn neck outline (head widths).

    Why measured: the neck cone melts into the trapezius, so the drawn neck is wider than the
    cone; a ring on the bare cone would turn away inside the outline and the string would stop
    on open skin. The measurement is capped so the shoulder slope cannot inflate the ring.
    """
    t = ctx.neck.t_at(y)
    c, r = ctx.neck.point(t), ctx.neck.radius(t, 0.0)
    res, body = ctx.res, ctx.body
    c_px = body.map([c[:2]])[0]
    y0, x0 = res.box[0], res.box[1]
    hh, ww = res.height.shape
    across = np.hypot(*(body.map([(c + ctx.neck.e1)[:2]])[0] - c_px)) / body.unit   # e1 as drawn (foreshortened)
    widths = []
    for s in (-1, 1):
        d = body.map([(c + s * ctx.neck.e1)[:2]])[0] - c_px
        d /= max(np.linalg.norm(d), 1e-9)
        for k in range(int(body.px(r * NECK_FIT_MAX * 2))):
            i, j = int(round(c_px[1] + d[1] * k)) - y0, int(round(c_px[0] + d[0] * k)) - x0
            if not (0 <= i < hh and 0 <= j < ww) or res.sdf_px[i, j] >= 0:
                widths.append(k / body.unit / max(across, 1e-6))
                break
    measured = np.mean(widths) if widths else r
    return float(np.clip(measured, r, r * NECK_FIT_MAX))


def halter(ctx, name, s, start_px, color, apex=(0.24, 1.47)):
    """A string from a cup up the chest to the side of the neck, then round the back of the neck.

    The string is one 3D path: up the chest on the visible surface, then a ring round the neck
    that touches the drawn outline. The neck hides the run round the nape, so the string turns
    away exactly at the neck outline, the way a halter tie reads from the front.
    """
    width = ctx.body.px(HALTER_W)
    neck, t = ctx.neck, ctx.neck.t_at(HALTER_NECK_Y)
    c, r = neck.point(t), neck_fit_radius(ctx, HALTER_NECK_Y) + HALTER_EASE
    th = s * np.linspace(np.pi / 2, np.pi / 2 + HALTER_WRAP, 24)[:, None]
    radial = np.sin(th) * neck.e1 + np.cos(th) * neck.e2
    ring = c + r * radial
    if ctx.turned:                         # the chest run as rest points: hidden where the chest turns away
        rest = K.smooth_path(np.array([(s * apex[0], apex[1]), (s * HALTER_VIA[0], HALTER_VIA[1])]), 40)
        front, up = G.surface_rest(ctx.chest, ctx.pelvis, rest, False, HALTER_EASE)
        seen = up[:, 2] > G.FACING_MIN
        if seen.any():
            front[seen] = K.surface_points(ctx.res, ctx.body, ctx.body.map(front[seen][:, :2]), HALTER_EASE)
        bridge = np.linspace(front[-1], ring[0], 8)[1:-1]
        front, up = np.vstack([front, bridge]), np.vstack([up, np.linspace(up[-1], radial[0], 8)[1:-1]])
        out = K.strap(name, 'cloth', Z_UNDER_TOP + 0.02, np.vstack([front, ring]), width, color, ctx.lw, ctx.res,
                      ctx.body, normals=np.vstack([up, radial]))
        nape = neck.point(t) - r * neck.e2                 # the bow's tails hang from the nape
        tail = np.array([nape, nape + np.array([s * 0.03, NAPE_TAIL * 0.5, 0.0]), nape + np.array([s * 0.05, NAPE_TAIL, 0.0])])
        back_n = np.tile(-neck.e2, (3, 1))
        return out + K.strap(name + '_tail', 'cloth', Z_UNDER_TOP + 0.02, tail, width * 0.9, color, ctx.lw, ctx.res,
                             ctx.body, normals=back_n)
    via = ctx.surf([(s * HALTER_VIA[0], HALTER_VIA[1])])[0]
    side = ctx.body.map([ring[0][:2]])[0]
    front_px = K.dense_px(K.smooth_path(np.array([start_px, via, side]), 40))[:-1]
    front = K.surface_points(ctx.res, ctx.body, front_px, HALTER_EASE)
    up = np.tile([0.0, 0.0, 1.0], (len(front), 1))
    return K.strap(name, 'cloth', Z_UNDER_TOP + 0.02, np.vstack([front, ring]), width, color, ctx.lw, ctx.res, ctx.body,
                   normals=np.vstack([up, radial]))


def briefs(ctx, name, color, outline, ease, lace=None, back_outline=None):
    """Bottoms that hug the hips: grown hips and upper legs kept inside an outline (and a back outline)."""
    g = K.garment_pieces(ctx.pieces, HIPS + LEGS, ease, 'g_' + name + '_')
    for i, p in enumerate(g):
        for s in (-1, 1):
            if p.name.endswith(f'leg_{s}'):
                g[i] = K.truncate(p, limb_cut_point(ctx, 'leg', s, 0.35))
    back_outline = back_outline or outline
    if ctx.turned:
        keep, keep_fn = None, ctx.rest_keep([np.array(closed(outline))], [np.array(closed(back_outline))])
    else:
        keep, keep_fn = [ctx.surf(closed(outline))], None
    drawables, _ = K.form_garment(ctx.fb, ctx.body, name, 'cloth', Z_UNDER_BOTTOM, g, color, keep=keep, keep_fn=keep_fn)
    edges = ctx.paths([closed(outline)], 64) + ctx.paths([closed(back_outline)], 64, back=True)
    drawables.append(K.lines(name + '_edges', Z_UNDER_BOTTOM + 0.01, edges, ctx.lw, color, k=1.0, clip=['body']))
    return drawables


def scallops(path_px, size_px, outward_px):
    """Lace edge: a chain of small arcs along a path."""
    path_px = np.asarray(path_px, float)
    length = np.sum(np.hypot(*np.diff(path_px, axis=0).T))
    n = max(int(length / size_px), 2)
    out = np.array(geom.resample(path_px, n * 6 + 1))
    for i in range(len(out)):
        phase = (i % 6) / 6.0
        out[i] = out[i] + np.asarray(outward_px) * np.sin(np.pi * phase)
    return out


CUP_DEMI = [(0.05, 1.80), (0.16, 1.67), (0.32, 1.60), (0.50, 1.64), (0.56, 1.82), (0.50, 1.99), (0.28, 2.04),
            (0.05, 2.03)]
CUP_TOP_N = 6                     # CUP_DEMI points from the centre over the top to the side
BRIEF_LACE = [(0.78, 3.18), (0.40, 3.24), (0.0, 3.26), (-0.40, 3.24), (-0.78, 3.18), (-0.78, 3.34), (-0.56, 3.56),
              (-0.30, 3.84), (-0.11, 4.03), (0.0, 4.07), (0.11, 4.03), (0.30, 3.84), (0.56, 3.56), (0.78, 3.34)]
BRIEF_LACE_BACK = [(0.78, 3.18), (0.40, 3.22), (0.0, 3.24), (-0.40, 3.22), (-0.78, 3.18), (-0.78, 3.34), (-0.66, 3.68),
                   (-0.46, 3.98), (-0.20, 4.08), (0.0, 4.10), (0.20, 4.08), (0.46, 3.98), (0.66, 3.68), (0.78, 3.34)]
BACK_HW = 0.95                    # back outlines reach past the side (the front/back split at the side ends them)
SHOULDER_TOP_Y, SHOULDER_TOP_Z = 0.90, -0.10   # rest point on top of the trapezius a strap passes over


def innerwear(ctx, outfit, z):
    color, lace, lw = ctx.pal['cloth'], ctx.pal['accent'], ctx.lw
    cup = bust_fit(CUP_DEMI)
    cups = [cup, [(-x, y) for x, y in cup]]
    strap_root = bust_fit([(0.46, 1.61)])[0]          # the strap leaves the top of the cup
    hw = G.loft_section(2.08)[0] + 0.03
    band_rest = [(-hw, 2.00), (0.0, 2.00), (hw, 2.00), (hw, 2.12), (0.0, 2.12), (-hw, 2.12)]   # mid points keep the edges straight
    cup_tops = [[c[-1]] + c[:CUP_TOP_N] for c in cups]          # the band covers the lower cup edge
    wide = [(-BACK_HW, 2.00), (BACK_HW, 2.00), (BACK_HW, 2.12), (-BACK_HW, 2.12)]
    out = fitted_top(ctx, 'bra', color, 0.012, cups + [band_rest], None, Z_UNDER_TOP,
                     edges_rest=cup_tops + [[(-hw, 2.00), (0.0, 2.00), (hw, 2.00)], [(-hw, 2.12), (0.0, 2.12), (hw, 2.12)]],
                     back_rest=[wide], back_edges=[[(-BACK_HW, 2.00), (BACK_HW, 2.00)], [(-BACK_HW, 2.12), (BACK_HW, 2.12)]])
    for s in (-1, 1):
        for top in ctx.paths([[(s * x, y) for x, y in cup[:4]]]):
            out.append(K.lines(f'bra_lace_{s}', Z_UNDER_TOP + 0.02, [scallops(top, ctx.body.px(0.04),
                                                                              (0, -ctx.body.px(0.012)))],
                               lw, lace, k=0.7, clip=['body']))
        if ctx.turned:                           # up the chest, over the shoulder, down to the back band
            out += ctx.strap_rest(f'bra_strap_{s}', 'cloth', Z_UNDER_TOP + 0.02,
                                  [([(s * strap_root[0], strap_root[1]), (s * 0.45, 1.30), (s * 0.40, 1.07)], 'front'),
                                   ([(s * 0.40, SHOULDER_TOP_Y, SHOULDER_TOP_Z)], 'free'),
                                   ([(s * 0.38, 1.10), (s * 0.34, 1.50), (s * 0.30, 2.00)], 'back')], 0.024, color)
            continue
        strap = np.vstack([ctx.surf([(s * strap_root[0], strap_root[1])]), ctx.surf([(s * 0.45, 1.30)]),
                           ctx.surf([(s * 0.40, 1.07)])])
        out.append(K.ribbon(f'bra_strap_{s}', 'cloth', Z_UNDER_TOP + 0.02, K.smooth_path(strap, 16),
                            ctx.body.px(0.024), color, lw, clip=['body']))
    out += briefs(ctx, 'innerwear_brief', color, BRIEF_LACE, 0.012, back_outline=BRIEF_LACE_BACK)
    for waist in ctx.paths([[(0.78, 3.18), (0.40, 3.24), (0.0, 3.26), (-0.40, 3.24), (-0.78, 3.18)]], 40):
        out.append(K.lines('brief_lace', Z_UNDER_BOTTOM + 0.02, [scallops(waist, ctx.body.px(0.04),
                                                                           (0, ctx.body.px(0.014)))],
                           lw, lace, k=0.7, clip=['body']))
    return out


# the strap tops (y 0.80) lie past the shoulder outline, so the form's own outline ends the strap
TANK = [(0.25, 0.80), (0.39, 0.80), (0.40, 1.22), (0.58, 1.46), (0.66, 1.70), (0.62, 2.50),
        (-0.62, 2.50), (-0.66, 1.70), (-0.58, 1.46), (-0.40, 1.22), (-0.39, 0.80), (-0.25, 0.80),
        (-0.23, 1.02), (-0.14, 1.26), (0.0, 1.36), (0.14, 1.26), (0.23, 1.02)]
TANK_BACK = [(0.25, 0.80), (0.39, 0.80), (0.40, 1.22), (0.58, 1.46), (0.66, 1.70), (0.62, 2.50),     # higher back neckline
             (-0.62, 2.50), (-0.66, 1.70), (-0.58, 1.46), (-0.40, 1.22), (-0.39, 0.80), (-0.25, 0.80),
             (-0.23, 1.02), (-0.14, 1.12), (0.0, 1.15), (0.14, 1.12), (0.23, 1.02)]


def crop_hotpants(ctx, outfit, z):
    top, denim, lw = ctx.pal['cloth'], ctx.pal['skirt'], ctx.lw
    # strap edges start above the shoulder line: the cloth outline ends them, so each strap is
    # inked on both sides up to where it passes over the shoulder
    neck = [(0.25, 0.78), (0.25, 0.96), (0.23, 1.02), (0.14, 1.26), (0.0, 1.36), (-0.14, 1.26), (-0.23, 1.02),
            (-0.25, 0.96), (-0.25, 0.78)]
    arm_l = [(0.39, 0.78), (0.39, 0.98), (0.40, 1.22), (0.58, 1.46)]
    back_neck = [(0.25, 0.78), (0.25, 0.96), (0.23, 1.02), (0.14, 1.12), (0.0, 1.15), (-0.14, 1.12), (-0.23, 1.02),
                 (-0.25, 0.96), (-0.25, 0.78)]
    arms = [arm_l, [(-x, y) for x, y in arm_l]]
    out = fitted_top(ctx, 'crop', top, 0.025, [TANK], 2.40, Z_UNDER_TOP, edges_rest=[neck] + arms, edges_to_form=True,
                     back_rest=[TANK_BACK], back_edges=[back_neck] + arms)
    out.append(K.lines('crop_hem', Z_UNDER_TOP + 0.01, [ring_line(ctx, 2.40, 0.025)], lw, top, k=1.0, clip=['crop']))
    shorts, waist = trousers(ctx, 'shorts', denim, 3.05, 0.22, 0.035)
    out += shorts
    out += band(ctx, 'shorts_band', 'skirt', Z_BOTTOM + 0.01, 3.05, 3.14, 0.04, denim)
    out.append(fly_and_pockets(ctx, 'shorts', darken(denim, 0.15), 3.05, 3.94, Z_BOTTOM + 0.02))
    button = ctx.points([(0.0, 3.095)])
    if button:
        out.append(K.dots('shorts_button', Z_BOTTOM + 0.03, button, ctx.body.px(0.018), ctx.pal['metal'], lw))
    return out


def tee_jeans(ctx, outfit, z):
    tee, denim, lw = ctx.pal['cloth'], ctx.pal['skirt'], ctx.lw
    jeans, waist = trousers(ctx, 'jeans', denim, 2.98, 1.97, 0.045)
    out = jeans + band(ctx, 'jeans_band', 'skirt', Z_BOTTOM + 0.01, 2.98, 3.08, 0.05, denim)
    out.append(fly_and_pockets(ctx, 'jeans', darken(denim, 0.15), 2.98, 3.94, Z_BOTTOM + 0.02))
    out.append(knee_folds(ctx, 'jeans', darken(denim, 0.2), Z_BOTTOM + 0.02, 0.045))
    shirt, edges = sleeved_top(ctx, 'tee', tee, 0.06, 0.42, TEE_SLEEVE_EASE, NECK_BASE_Y, 0.13, 3.30, Z_TOP)
    out += shirt
    band_y = NECK_BASE_Y + 0.05
    neck_band = K.to_px(ctx.body, ctx.neck.ring(band_y, 0.10, ctx.neck.arc(band_y, 0.10, 32, 0.16), 0.16), dip=False)
    out.append(K.lines('tee_lines', Z_TOP + 0.01, [edges['neckline'], neck_band, edges['hem']], lw, tee, k=K.EDGE_K,
                       clip=['tee']))
    out += cuff_lines('tee_cuff', Z_TOP + 0.011, edges['cuffs'], lw, tee)
    return out


def suit(ctx, outfit, z):
    wool, shirt_c, tie_c, lw = ctx.pal['cloth'], ctx.pal['shirt'], ctx.pal['tie'], ctx.lw
    trousers_d, waist = trousers(ctx, 'trousers', wool, 2.70, 1.96, 0.06)
    out = trousers_d + [leg_fronts(ctx, 'trousers', darken(wool, 0.25), 0.2, 1.9, Z_BOTTOM + 0.02, 0.06)]
    out += band(ctx, 'suit_belt', 'leather', Z_BELT, 2.70, 2.78, 0.07, ctx.pal['belt'], buckle=True)
    shirt, sedges = sleeved_top(ctx, 'shirt', shirt_c, 0.025, 1.95, 0.035, 0.88, 0.07, 2.74, Z_SHIRT, neck=True)
    out += shirt
    out.append(K.lines('shirt_collar', Z_SHIRT + 0.003, [sedges['neckline']], lw, shirt_c, k=0.9, clip=['shirt']))
    out += cuff_lines('shirt_cuff', Z_SHIRT + 0.002, sedges['cuffs'], lw, shirt_c, k=0.8)
    out += tie(ctx, tie_c, shirt_c)
    v_open = [(-0.21, 0.90), (-0.20, 1.02), (0.0, 2.62), (0.20, 1.02), (0.21, 0.90)]
    cutaway = [(0.0, 2.75), (0.40, 3.80), (-0.40, 3.80)]
    jacket, jedges = sleeved_top(ctx, 'jacket', wool, 0.07, 1.90, 0.06, JACKET_NECK_Y, 0.0, 3.72, Z_TOP, hip_pieces=True,
                                 neck=True, front_cuts=[v_open, cutaway])
    out += jacket
    lapels = []
    for s in (-1, 1):
        lapels += (ctx.paths([[(s * 0.20, 1.02), (s * 0.10, 1.82), (0.0, 2.62)],
                              [(s * 0.22, 1.05), (s * 0.31, 1.24), (s * 0.41, 1.40)]])
                   + ctx.paths([[(s * 0.41, 1.40), (s * 0.35, 1.47)]], 6)
                   + ctx.paths([[(s * 0.35, 1.47), (s * 0.34, 1.80), (s * 0.20, 2.25), (s * 0.03, 2.60)]])
                   + ctx.paths([[(s * 0.30, 3.26), (s * 0.62, 3.24)]], 8)
                   + ctx.paths([[(0.0, 2.75), (s * 0.40, 3.78)]], 12))
    lapels += ctx.paths([[(0.28, 1.86), (0.48, 1.84)]], 6)
    lapels += ctx.paths([[(0.0, 1.14), (0.0, 3.40)], [(0.0, 3.40), (0.03, 3.72)]], 24, back=True)   # back seam, vent
    out.append(K.lines('jacket_lines', Z_TOP + 0.01, lapels + [jedges['hem']], lw, wool, k=0.75, clip=['jacket']))
    out += cuff_lines('jacket_cuff', Z_TOP + 0.011, jedges['cuffs'], lw, wool, k=0.75)
    button = ctx.points([(0.03, 2.70)])
    if button:
        out.append(K.dots('jacket_button', Z_TOP + 0.02, button, ctx.body.px(0.025), darken(wool, 0.4), lw))
    return out


def tie(ctx, tie_c, shirt_c):
    body = ctx.body
    knot = [(-0.045, 1.02), (0.045, 1.02), (0.03, 1.10), (-0.03, 1.10)]
    blade = [(-0.035, 1.10), (0.035, 1.10), (0.065, 2.30), (0.0, 2.42), (-0.065, 2.30)]
    out = (ctx.patch('tie_blade', 'cloth', Z_SHIRT + 0.01, blade, tie_c, form_px=body.px(0.04))
           + ctx.patch('tie_knot', 'cloth', Z_SHIRT + 0.015, knot, darken(tie_c, 0.08)))
    for s in (-1, 1):
        out += ctx.patch(f'collar_point_{s}', 'cloth', Z_SHIRT + 0.02, [(s * 0.02, 1.03), (s * 0.15, 0.93), (s * 0.19, 1.15)],
                         shirt_c)
    return out


def hoodie_joggers(ctx, outfit, z):
    knit, jog, cord, lw = ctx.pal['cloth'], ctx.pal['skirt'], ctx.pal['accent'], ctx.lw
    joggers, waist = trousers(ctx, 'joggers', jog, 2.86, 1.95, 0.08)
    out = joggers + band(ctx, 'joggers_band', 'skirt', Z_BOTTOM + 0.01, 2.86, 2.98, 0.09, jog)
    for s in (-1, 1):                                                  # ankle cuffs
        g = ctx.piece(f'leg_{s}')
        top = K.to_px(ctx.body, K.limb_ring(g, limb_cut_point(ctx, 'leg', s, 1.85), 0.07, K.front_arc()))
        out.append(K.lines(f'joggers_cuff_{s}', Z_BOTTOM + 0.02, [top], lw, jog, k=0.8, clip=['joggers']))
        out.append(K.gathers(Z_BOTTOM + 0.02, top, (0, -1), 4, ctx.body.px(0.12), lw, darken(jog, 0.2), ['joggers'],
                             ctx.rng, f'joggers_gather_{s}'))
    hood = hood_piece(ctx)
    z_hood = Z_TOP + 0.05 if abs(ctx.pose.turn) > np.pi / 2 else Z_HOOD      # seen from behind the hood lies on top
    res = ctx.fb.build('hood', 'cloth', z_hood, hood, color=knit, line_color=darken(knit, 0.55), self_shadow=False)
    if res is not None:
        out += res.drawables
    out.append(hood_rim(ctx, knit))
    top, edges = sleeved_top(ctx, 'hoodie', knit, 0.11, 1.92, 0.09, HOOD_RIM_Y + 0.02, HOOD_RIM_DROP, 3.45, Z_TOP,
                             hip_pieces=True)
    out += top
    band_top = ring_line(ctx, 3.33, 0.11)
    paths = [edges['neckline'], edges['hem'], band_top]
    out += cuff_lines('hoodie_cuff', Z_TOP + 0.011, edges['cuffs'], lw, knit, k=0.8)
    for s in (-1, 1):
        paths += ctx.paths([[(s * 0.42, 2.74), (s * 0.48, 2.90), (s * 0.56, 3.12), (s * 0.58, 3.33)]], 16)
    paths += ctx.paths([[(-0.42, 2.74), (0.42, 2.74)]], 12)
    out.append(K.lines('hoodie_lines', Z_TOP + 0.01, paths, lw, knit, k=0.8, clip=['hoodie']))
    out.append(K.gathers(Z_TOP + 0.01, band_top, (0, -1), 7, ctx.body.px(0.14), lw, darken(knit, 0.25), ['hoodie'],
                         ctx.rng, 'hoodie_gathers'))
    for s in (-1, 1):                                                  # drawstrings
        ends = ctx.points([(s * 0.09, HOOD_RIM_Y + HOOD_RIM_W + HOOD_RIM_DROP + 0.02), (s * 0.11, 1.62)])
        if len(ends) < 2:
            continue
        start, end = ends
        mid = (start + end) / 2 + (ctx.body.px(s * 0.015), 0)
        out.append(K.ribbon(f'hoodie_cord_{s}', 'cloth', Z_TOP + 0.02, np.array([start, mid, end]), ctx.body.px(0.018),
                            cord, lw, clip=None))
    return out


def hood_rim(ctx, color):
    """Edge of the hood lying round the neck: a band that scoops down at the front."""
    th = ctx.neck.arc(HOOD_RIM_Y, 0.06, 40, HOOD_RIM_DROP)
    inner = K.to_px(ctx.body, ctx.neck.ring(HOOD_RIM_Y, 0.06, th, HOOD_RIM_DROP), dip=False)
    outer = K.to_px(ctx.body, ctx.neck.ring(HOOD_RIM_Y + HOOD_RIM_W, 0.13, th, HOOD_RIM_DROP + HOOD_RIM_W), dip=False)
    return K.patch_shape('hood_rim', 'cloth', Z_TOP + 0.005, np.vstack([inner, outer[::-1]]), color, ctx.lw,
                         form_px=ctx.body.px(0.05))


def hood_piece(ctx):
    """The hood lying back: a horseshoe of soft forms behind the neck and on the shoulders."""
    import mannequin as M
    neck = ctx.neck
    c = neck.point(neck.t_at(HOOD_Y))
    thetas = np.linspace(HOOD_ARC[0] * np.pi, HOOD_ARC[1] * np.pi, 11)
    centres = c + HOOD_REACH * (np.sin(thetas)[:, None] * neck.e1 + np.cos(thetas)[:, None] * neck.e2)
    solids = [M.sphere(p, HOOD_R) for p in centres]
    return [M.Piece('hood', solids, k=0.10)]


def swim_trunks(ctx, outfit, z):
    """Board-short trunks: mid-thigh legs, a drawstring waistband and a side stripe."""
    color, lw = ctx.pal['skirt'], ctx.lw
    trunks, waist = trousers(ctx, 'trunks', color, TRUNKS_WAIST_Y, TRUNKS_LENGTH, 0.05)
    out = trunks + band(ctx, 'trunks_band', 'skirt', Z_BOTTOM + 0.01, TRUNKS_WAIST_Y, TRUNKS_WAIST_Y + 0.10, 0.055,
                        darken(color, 0.15))
    for s in (-1, 1):
        for start in ctx.points([(s * 0.05, TRUNKS_WAIST_Y + 0.06)]):
            end = start + ctx.body.px(np.array([s * 0.03, 0.22]))
            out.append(K.ribbon(f'trunks_cord_{s}', 'cloth', Z_BOTTOM + 0.03, np.array([start, (start + end) / 2, end]),
                                ctx.body.px(0.016), ctx.pal['accent'], lw))
        g = ctx.piece(f'leg_{s}')
        stripe, vis = [], []
        for f in np.linspace(0.0, TRUNKS_LENGTH - 0.02, 10):
            point = limb_cut_point(ctx, 'leg', s, f)
            th = limb_view_thetas(ctx, g, point, [s * TRUNKS_STRIPE_THETA]) if ctx.turned else [s * TRUNKS_STRIPE_THETA]
            stripe.append(K.limb_ring(g, point, 0.05, th)[0])
            vis.append(np.cos(th[0]) > G.FACING_MIN)
        for run in K.visible_runs(K.to_px(ctx.body, np.array(stripe)), vis):
            out.append(K.lines(f'trunks_stripe_{s}', Z_BOTTOM + 0.02, [run], lw,
                               ctx.pal['accent'], k=2.2, clip=['trunks'], taper=(0.0, 0.0)))
    return out


# ---------------------------------------------------------------- v5 outfits (men's range; most fit both)

def collar_points(ctx, name, z, color, spread=0.15):
    """Two pointed shirt-collar flaps meeting under the chin."""
    out = []
    for s in (-1, 1):
        out += ctx.patch(f'{name}_{s}', 'cloth', z, [(s * 0.02, 1.03), (s * spread, 0.93), (s * (spread + 0.04), 1.15)], color)
    return out


def placket(ctx, name, z, color, top_y, bottom_y, buttons, lw_k=0.7):
    """A front opening line with buttons down it (shirts, polos, coats)."""
    out = [K.lines(f'{name}_placket', z, ctx.paths([[(0.012, top_y), (0.012, bottom_y)]]), ctx.lw, color, k=lw_k,
                   clip=[name])]
    dots = ctx.points([(0.0, y) for y in np.linspace(top_y + 0.08, bottom_y - 0.1, buttons)])
    if dots:
        out.append(K.dots(f'{name}_buttons', z + 0.01, dots, ctx.body.px(0.018), darken(color, 0.75), ctx.lw))
    return out


def shirt_slacks(ctx, outfit, z):
    """Dress shirt tucked into slim slacks with a belt; collar open at the neck, cuffs at the wrists."""
    shirt_c, wool, lw = ctx.pal['shirt'], ctx.pal['skirt'], ctx.lw
    slacks, waist = trousers(ctx, 'slacks', wool, 2.84, 1.96, 0.05)
    out = slacks + [leg_fronts(ctx, 'slacks', darken(wool, 0.25), 0.2, 1.9, Z_BOTTOM + 0.02, 0.05)]
    out += band(ctx, 'slacks_belt', 'leather', Z_BELT, 2.84, 2.92, 0.06, ctx.pal['belt'], buckle=True)
    shirt, edges = sleeved_top(ctx, 'shirt', shirt_c, 0.04, 1.95, 0.045, NECK_BASE_Y - 0.02, 0.10, 2.92, Z_SHIRT)
    out += shirt
    out.append(K.lines('shirt_lines', Z_SHIRT + 0.01, [edges['neckline']], lw, shirt_c, k=0.9, clip=['shirt']))
    out += cuff_lines('shirt_cuff', Z_SHIRT + 0.011, edges['cuffs'], lw, shirt_c, k=0.8)
    out += collar_points(ctx, 'shirt_collar', Z_SHIRT + 0.02, shirt_c, 0.17)
    out += placket(ctx, 'shirt', Z_SHIRT + 0.012, shirt_c, 1.12, 2.84, 5)
    yoke = ctx.paths([[(-0.55, 1.20), (0.0, 1.30), (0.55, 1.20)]], back=True)      # back yoke seam (turned views)
    if yoke:
        out.append(K.lines('shirt_back', Z_SHIRT + 0.01, yoke, lw, shirt_c, k=0.6, clip=['shirt']))
    return out


COAT_HEM_Y, COAT_FLARE, COAT_FOLDS = 5.45, 0.92, 0.06   # a knee-length coat: nearly straight, shallow folds
COAT_TOP_Y = 2.74                          # the coat's skirt starts under its belt
SWEATER_NECK_DROP, SWEATER_RIB_W = 0.10, 0.04   # a crew neck under the coat and its knit rib band


def knit_coat(ctx, outfit, z):
    """A knit sweater under a belted knee-length coat, trousers below."""
    knit, coat_c, wool, lw = ctx.pal['shirt'], ctx.pal['cloth'], ctx.pal['skirt'], ctx.lw
    pants, waist = trousers(ctx, 'trousers', wool, 2.86, 1.96, 0.05)
    out = pants
    # a crew neck at the base of the neck: a neckline above it would cut the neckless torso flat
    sweater, sedges = sleeved_top(ctx, 'sweater', knit, 0.07, 1.92, 0.07, NECK_BASE_Y, SWEATER_NECK_DROP, 3.05, Z_SHIRT)
    out += sweater
    _, rib = neck_cut(ctx, NECK_BASE_Y + SWEATER_RIB_W, 0.07, SWEATER_NECK_DROP)
    out.append(K.lines('sweater_rib', Z_SHIRT + 0.01, [sedges['neckline'], rib], lw, knit, k=0.8, clip=['sweater']))
    v_open = [(-0.24, OPEN_TOP_Y), (-0.20, 1.10), (0.0, 2.02), (0.20, 1.10), (0.24, OPEN_TOP_Y)]
    # the collar wraps the neck behind the open front, as on the jacket: a flat top would end in a step at the neck
    coat, cedges = sleeved_top(ctx, 'coat', coat_c, 0.11, 1.90, 0.09, JACKET_NECK_Y, 0.0, 2.86, Z_TOP, neck=True,
                               front_cuts=[v_open])          # the body ends under the belt: one coat
    out += coat
    if ctx.pose.prop == 'chair':
        out += lap_skirt(ctx, coat_c, Z_TOP - 0.02, name='coat_skirt')
    else:
        out += G.build_skirt(ctx.fb, ctx.body, ctx.pieces, ctx.pose,
                             {'skirt_length': COAT_HEM_Y, 'skirt_flare': COAT_FLARE, 'skirt_folds': COAT_FOLDS},
                             ctx.pal, lw, ctx.rng, Z_TOP - 0.02, name='coat_skirt', color=coat_c, top_y=COAT_TOP_Y)
    out += band(ctx, 'coat_belt', 'cloth', Z_TOP + 0.02, 2.66, 2.80, 0.13, darken(coat_c, 0.85), buckle=True)
    lapels = []
    for s in (-1, 1):
        lapels += ctx.paths([[(s * 0.24, 0.94), (s * 0.30, 1.30), (s * 0.44, 1.46)], [(s * 0.44, 1.46), (s * 0.20, 2.02)]])
    lapels += ctx.paths([[(0.0, 2.02), (0.0, 2.66)]])
    out.append(K.lines('coat_lines', Z_TOP + 0.01, lapels, lw, coat_c, k=0.8, clip=['coat']))
    out.append(K.lines('coat_skirt_lines', Z_TOP + 0.01, ctx.paths([[(0.02, 2.80), (0.02, COAT_HEM_Y - 0.1)]]),
                       lw, coat_c, k=0.8, clip=['coat_skirt']))
    out += cuff_lines('coat_cuff', Z_TOP + 0.011, cedges['cuffs'], lw, coat_c, k=0.8)
    return out


def polo_shorts(ctx, outfit, z):
    """A polo shirt (knit collar, two-button placket) and knee-length chino shorts."""
    polo, chino, lw = ctx.pal['cloth'], ctx.pal['skirt'], ctx.lw
    shorts, waist = trousers(ctx, 'shorts', chino, 2.94, 0.48, 0.05, leg_ease=0.07)
    out = shorts + band(ctx, 'shorts_band', 'skirt', Z_BOTTOM + 0.01, 2.94, 3.03, 0.055, chino)
    out.append(fly_and_pockets(ctx, 'shorts', darken(chino, 0.2), 2.94, 3.94, Z_BOTTOM + 0.02))
    top, edges = sleeved_top(ctx, 'polo', polo, 0.06, 0.40, TEE_SLEEVE_EASE, NECK_BASE_Y - 0.02, 0.10, 3.32, Z_TOP)
    out += top
    out.append(K.lines('polo_lines', Z_TOP + 0.01, [edges['neckline'], edges['hem']], lw, polo, k=K.EDGE_K, clip=['polo']))
    out += cuff_lines('polo_cuff', Z_TOP + 0.011, edges['cuffs'], lw, polo)
    out += collar_points(ctx, 'polo_collar', Z_TOP + 0.02, polo, 0.20)
    out += placket(ctx, 'polo', Z_TOP + 0.012, polo, 1.10, 1.52, 2)
    return out


SINGLET = [(0.27, 0.80), (0.43, 0.80), (0.45, 1.10), (0.58, 1.50), (0.70, 1.72), (0.66, 3.40),
           (-0.66, 3.40), (-0.70, 1.72), (-0.58, 1.50), (-0.45, 1.10), (-0.43, 0.80), (-0.27, 0.80),
           (-0.26, 1.02), (-0.14, 1.28), (0.0, 1.34), (0.14, 1.28), (0.26, 1.02)]
SINGLET_BACK = [(0.27, 0.80), (0.43, 0.80), (0.45, 1.10), (0.58, 1.50), (0.70, 1.72), (0.66, 3.40),
                (-0.66, 3.40), (-0.70, 1.72), (-0.58, 1.50), (-0.45, 1.10), (-0.43, 0.80), (-0.27, 0.80),
                (-0.26, 1.02), (-0.14, 1.14), (0.0, 1.18), (0.14, 1.14), (0.26, 1.02)]


def tank_shorts(ctx, outfit, z):
    """A sports singlet with deep armholes and loose running shorts with a side stripe."""
    top, shorts_c, accent, lw = ctx.pal['cloth'], ctx.pal['skirt'], ctx.pal['accent'], ctx.lw
    neck = [(0.27, 0.78), (0.27, 0.96), (0.26, 1.02), (0.14, 1.28), (0.0, 1.34), (-0.14, 1.28), (-0.26, 1.02),
            (-0.27, 0.96), (-0.27, 0.78)]
    back_neck = [(0.27, 0.78), (0.27, 0.96), (0.26, 1.02), (0.14, 1.14), (0.0, 1.18), (-0.14, 1.14), (-0.26, 1.02),
                 (-0.27, 0.96), (-0.27, 0.78)]
    arm = [(0.43, 0.78), (0.45, 1.10), (0.58, 1.50), (0.70, 1.72)]
    arms = [arm, [(-x, y) for x, y in arm]]
    out = fitted_top(ctx, 'singlet', top, 0.04, [SINGLET], 3.30, Z_UNDER_TOP, edges_rest=[neck] + arms, edges_to_form=True,
                     back_rest=[SINGLET_BACK], back_edges=[back_neck] + arms)
    out.append(K.lines('singlet_hem', Z_UNDER_TOP + 0.01, [ring_line(ctx, 3.30, 0.04)], lw, top, k=1.0, clip=['singlet']))
    shorts, waist = trousers(ctx, 'shorts', shorts_c, 2.98, 0.42, 0.07, leg_ease=0.10)
    out += shorts + band(ctx, 'shorts_band', 'skirt', Z_BOTTOM + 0.01, 2.98, 3.08, 0.075, darken(shorts_c, 0.85))
    for s in (-1, 1):
        g = ctx.piece(f'leg_{s}')
        stripe, vis = [], []
        for f in np.linspace(0.0, 0.40, 10):
            point = limb_cut_point(ctx, 'leg', s, f)
            th = limb_view_thetas(ctx, g, point, [s * TRUNKS_STRIPE_THETA]) if ctx.turned else [s * TRUNKS_STRIPE_THETA]
            stripe.append(K.limb_ring(g, point, 0.10, th)[0])
            vis.append(np.cos(th[0]) > G.FACING_MIN)
        runs = K.visible_runs(K.to_px(ctx.body, np.array(stripe)), vis)
        if runs:
            out.append(K.band_stripe(f'shorts_stripe_{s}', Z_BOTTOM + 0.02, runs, ctx.body.px(STRIPE_W), accent, ['shorts']))
    return out


def denim_jacket(ctx, outfit, z):
    """A tee under an open waist-length denim jacket (chest pockets, buttoned plackets), jeans."""
    tee, denim, jeans_c, lw = ctx.pal['shirt'], ctx.pal['cloth'], ctx.pal['skirt'], ctx.lw
    jeans, waist = trousers(ctx, 'jeans', jeans_c, 2.98, 1.97, 0.045)
    out = jeans + band(ctx, 'jeans_band', 'skirt', Z_BOTTOM + 0.01, 2.98, 3.08, 0.05, jeans_c)
    out.append(fly_and_pockets(ctx, 'jeans', darken(jeans_c, 0.15), 2.98, 3.94, Z_BOTTOM + 0.02))
    shirt, edges = sleeved_top(ctx, 'tee', tee, 0.06, 0.42, TEE_SLEEVE_EASE, NECK_BASE_Y, 0.13, 3.30, Z_SHIRT)
    out += shirt
    out.append(K.lines('tee_lines', Z_SHIRT + 0.01, [edges['neckline'], edges['hem']], lw, tee, k=K.EDGE_K, clip=['tee']))
    opening = [(-0.20, OPEN_TOP_Y), (-0.18, 1.10), (-0.16, 3.40), (0.16, 3.40), (0.18, 1.10), (0.20, OPEN_TOP_Y)]
    jacket, jedges = sleeved_top(ctx, 'jacket', denim, 0.09, 1.92, 0.08, JACKET_NECK_Y, 0.0, 3.22, Z_TOP, neck=True,
                                 front_cuts=[opening])
    out += jacket
    lines = []
    for s in (-1, 1):
        lines += ctx.paths([[(s * 0.20, 0.92), (s * 0.32, 1.10), (s * 0.22, 1.24)],                 # collar
                            [(s * 0.24, 1.52), (s * 0.50, 1.52), (s * 0.48, 1.74), (s * 0.24, 1.72), (s * 0.24, 1.52)],
                            [(s * 0.20, 1.40), (s * 0.62, 1.38)],                                     # yoke seam
                            [(s * 0.37, 1.74), (s * 0.40, 3.08)], [(s * 0.24, 3.08), (s * 0.70, 3.06)]])
    lines += ctx.paths([[(-0.62, 1.30), (0.0, 1.42), (0.62, 1.30)]], back=True)
    out.append(K.lines('jacket_lines', Z_TOP + 0.01, lines + [jedges['hem']], lw, denim, k=0.75, clip=['jacket']))
    dots = ctx.points([(s * 0.20, y) for s in (-1, 1) for y in (1.30, 1.80, 2.30, 2.80)])
    if dots:
        out.append(K.dots('jacket_buttons', Z_TOP + 0.02, dots, ctx.body.px(0.02), ctx.pal['metal'], lw))
    out += cuff_lines('jacket_cuff', Z_TOP + 0.011, jedges['cuffs'], lw, denim, k=0.8)
    return out


TRACK_STRIPE = 1.0                # radians round a limb from its front: the stripe down the outer side
STRIPE_W, ZIP_W = 0.035, 0.016    # head widths: a sports stripe and a zipper tape


def track_suit(ctx, outfit, z):
    """A zip track jacket with a stand collar and sleeve stripes, matching track pants with side stripes."""
    knit, accent, lw = ctx.pal['cloth'], ctx.pal['accent'], ctx.lw
    pants, waist = trousers(ctx, 'pants', knit, 2.88, 1.95, 0.07)
    out = pants + band(ctx, 'pants_band', 'skirt', Z_BOTTOM + 0.01, 2.88, 2.98, 0.08, knit)
    jacket, edges = sleeved_top(ctx, 'jacket', knit, 0.09, 1.92, 0.08, 0.86, 0.02, 3.22, Z_TOP, neck=True)
    out += jacket
    band_top = ring_line(ctx, 3.10, 0.09)
    zipper = ctx.paths([[(0.0, 0.92), (0.0, 3.20)]])
    out.append(K.lines('jacket_lines', Z_TOP + 0.01, [edges['neckline'], edges['hem'], band_top], lw, knit, k=0.8,
                       clip=['jacket']))
    if zipper:
        out.append(K.band_stripe('jacket_zip', Z_TOP + 0.012, zipper, ctx.body.px(ZIP_W), accent, ['jacket']))
    out += cuff_lines('jacket_cuff', Z_TOP + 0.011, edges['cuffs'], lw, knit, k=0.8)
    for s in (-1, 1):                                          # stripes down the outside of sleeves and legs
        for limb, fracs, ease, clip, zz, name in (('arm', (0.25, 1.85), 0.09, f'jacket_sleeve_{s}', Z_TOP + 0.012, 'sleeve'),
                                                   ('leg', (0.05, 1.85), 0.07, 'pants', Z_BOTTOM + 0.02, 'leg')):
            g = ctx.piece(f'{limb}_{s}')
            pts, vis = [], []
            for f in np.linspace(*fracs, 24):
                point = limb_cut_point(ctx, limb, s, f)
                th = limb_view_thetas(ctx, g, point, [s * TRACK_STRIPE]) if ctx.turned else [s * TRACK_STRIPE]
                pts.append(K.limb_ring(g, point, ease, th)[0])
                vis.append(np.cos(th[0]) > G.FACING_MIN)
            runs = K.visible_runs(K.to_px(ctx.body, np.array(pts)), vis)
            if runs:
                out.append(K.band_stripe(f'{name}_stripe_{s}', zz, runs, ctx.body.px(STRIPE_W), accent, [clip]))
    return out


RECIPES = {'turtleneck_sleeveless': turtleneck_skirt, 'swim_trunks': swim_trunks, 'bikini': bikini, 'innerwear': innerwear,
           'crop_hotpants': crop_hotpants, 'tee_jeans': tee_jeans, 'suit': suit, 'hoodie_joggers': hoodie_joggers,
           'shirt_slacks': shirt_slacks, 'knit_coat': knit_coat, 'polo_shorts': polo_shorts, 'tank_shorts': tank_shorts,
           'denim_jacket': denim_jacket, 'track_suit': track_suit}


def build_outfit(kind, ctx, outfit, z):
    if kind not in RECIPES:
        raise ValueError(f"unknown outfit type '{kind}' (use {', '.join(RECIPES)})")
    return RECIPES[kind](ctx, outfit, z)
