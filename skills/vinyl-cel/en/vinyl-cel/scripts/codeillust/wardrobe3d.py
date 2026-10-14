"""Clothes for 3D figures.

A garment is built from the body's own surface data (rig3d.TRUNK, ARM, LEG)
over a range, pushed outward by the cloth thickness, plus a few extra solids
(skirts, hoods, collars) and decal lines (seams, hems, pockets) that are
projected onto the figure and hidden where the figure covers them.

Positions along the trunk use rig3d.TRUNK_LANDMARKS (0 crotch .. 1 neck);
positions along limbs run 0 at the shoulder or hip to 1 at the wrist or ankle.
"""
from dataclasses import dataclass, field

import numpy as np

from .body3d import SMOOTH_BLEND, distance_to_solids, ellipsoid, section_sweep, sweep
from .config import Material, rgb
from .rig3d import (ARM, FEMALE_NECK, FOOT, LEG, MALE_NECK, SIDES, TRUNK_LANDMARKS, Sex, _cut_positions, neck_path,
                    torso_solids,
                    breast_shape, deltoid_shape,
                    glute_shape, limb_path, limb_scale, pec_shape, trapezius_frame, trapezius_shape, trunk_sections)

T = TRUNK_LANDMARKS
# Cloth offset from the skin (head heights). TIGHT must stay above the skin's own blend bulge
# (body3d.SMOOTH_BLEND / 4) or the skin swells through wherever two body forms meet.
TIGHT, FITTED, LOOSE, BULKY = 0.030, 0.040, 0.055, 0.08
CLOTH_GLOSS = 0.05


def fabric(hex_base, hex_shadow, hex_line, hex_light=None):
    return Material(base=rgb(hex_base), shadow=rgb(hex_shadow), line=rgb(hex_line),
                    light=rgb(hex_light) if hex_light else None)


# ---- building blocks -------------------------------------------------------------------------------
SHOULDER_LINE = 0.88   # a trunk piece reaching this landmark position covers the neck-to-shoulder slope


HIP_COVER_TOP = 0.36    # a layered trunk piece starting below this also covers the tops of the thighs
TRUNK_HEM_DROP = 0.05   # head heights below its hem section where a layered top ends
BOTTOMS_TOP = 0.42      # landmark position up to which trousers and skirts can lie under a top
CLEAR_BLEND = 0.06      # landmark distance over which a top eases from its own fit to clearing the bottoms


def over_bottoms(ctx, thickness):
    """Offset for a garment worn over bottoms: at least as far out as the thickest bottom plus a layer,
    where the two overlap, so a thin top (a tank top) never sinks into the waist of the jeans under it."""
    own = ctx.lift(thickness)
    if ctx.layer < 1:
        return own
    clear = ctx.lift(FITTED)
    if clear <= own:
        return own

    def offset(position):
        k = float(np.clip((BOTTOMS_TOP + CLEAR_BLEND - position) / CLEAR_BLEND, 0.0, 1.0))
        return own + (clear - own) * k * k * (3 - 2 * k)

    return offset


def trunk(ctx, start, end, thickness, slot, flare=None, name="cloth", cut=None):
    sections = trunk_sections(ctx.skeleton, ctx.build, start, end, over_bottoms(ctx, thickness), flare)
    covers_hips = ctx.layer >= 1 and start < HIP_COVER_TOP
    if covers_hips:
        # The trunk and the hip cover end on one flat hem; a rounded trunk end over a flat-cut hip cover
        # leaves a tab of cloth sticking out at the seat, plain to see on a seated figure.
        hem = hem_cut(ctx, start)
        cut = hem if cut is None else _either(hem, cut)
    solids = section_sweep(sections, ctx.material(slot), group=slot, name=name, gloss=CLOTH_GLOSS, cut=cut)
    if covers_hips:
        # Worn over bottoms and reaching below the hips: clear the trouser legs and seat as well.
        solids += hip_cover(ctx, start, thickness + (flare(start) if flare else 0.0), slot, top=end)
        # Hands in the front pockets go in under the top as well, down to its hem, sleeves and all.
        for pocket in pocket_hands(ctx, thickness, slot, sleeve_room=POCKET_SLEEVE_ROOM):
            pocket.cut = hem
            solids.append(pocket)
    if end >= SHOULDER_LINE:
        for _, sign in SIDES:
            center, radii, _ = trapezius_shape(ctx.build, sign)
            cover = ellipsoid(ctx.skeleton.point("chest", center), trapezius_frame(ctx.skeleton, ctx.build, sign),
                              tuple(r + ctx.lift(TIGHT) for r in radii), ctx.material(slot), group=slot, name=name,
                              gloss=CLOTH_GLOSS)
            cover.cut = cut
            solids.append(cover)
    return solids


SLEEVE_EASE_LENGTH = 0.22   # fraction of the arm over which a sleeve goes from close-fitting to its full ease
SLEEVE_HANG = 0.7           # share of a sleeve's ease that hangs below the arm
HEM_FLAT_END = 0.97         # sleeves and trouser legs ending before this share of the limb get a flat hem


def sleeve(ctx, side, start, end, thickness, slot, flare=0.0):
    """A sleeve: it lies close on top of the shoulder, eases out to its full looseness down the arm,
    and the slack hangs below the arm (gravity is +y in figure space)."""
    thickness = ctx.lift(thickness)
    close = min(ctx.lift(TIGHT), thickness)
    points, radii = limb_path(ctx.skeleton, side, ARM, ctx.build, start, end, 0.0,
                              limb_scale(ctx.build, "arm") * (1 + 0.12 * ctx.build.muscle * 0.5))
    along = np.array(_cut_positions(len(ARM) - 1, start, end)) / (len(ARM) - 1)
    ease = np.clip(along / SLEEVE_EASE_LENGTH, 0.0, 1.0)
    offset = close + (thickness - close) * ease * (3 - 2 * ease)
    radii = radii + offset + flare * np.linspace(0, 1, len(radii))
    points = points + np.outer(offset - close, (0.0, SLEEVE_HANG, 0.0))
    tube = sweep(points, radii, ctx.material(slot), group=slot, name="cloth", gloss=CLOTH_GLOSS)
    tube.cut = flat_hem(points) if end < HEM_FLAT_END else None
    if ctx.layer >= 1 and end >= SLEEVE_AT_WRIST and side in pocket_sides(ctx):
        # A long sleeve of a top whose hand is in a pocket goes into the top's pocket cover (trunk()).
        tuck = tuck_into_pocket(ctx, side)
        tube.cut = tuck if tube.cut is None else _either(tube.cut, tuck)
        tube.cut.lining = False
    solids = [tube]
    if start <= 0.05:
        # The shoulder muscle is wider than the arm; the sleeve head has to go over it.
        joint = f"shoulder_{side}"
        center, shape = deltoid_shape(ctx.build, side)
        solids.append(ellipsoid(ctx.skeleton.point(joint, center), ctx.skeleton.rotation[joint],
                                tuple(r + close for r in shape), ctx.material(slot), group=slot,
                                name="cloth", gloss=CLOTH_GLOSS))
    return solids


def leg(ctx, side, start, end, thickness, slot, flare=0.0):
    thickness = ctx.lift(thickness)
    points, radii = limb_path(ctx.skeleton, side, LEG, ctx.build, start, end, thickness,
                              limb_scale(ctx.build, "leg"))
    radii = radii + flare * np.linspace(0, 1, len(radii)) ** 2
    tube = sweep(points, radii, ctx.material(slot), group=slot, name="cloth", gloss=CLOTH_GLOSS)
    tube.cut = flat_hem(points) if end < HEM_FLAT_END else None
    return [tube]


def flat_hem(points):
    """Cut test that ends a sleeve or trouser leg in a flat opening at its last point. A sphere chain
    ends in a round cap, which makes short sleeves and shorts look like balloons."""
    end = np.asarray(points[-1], dtype=np.float64)
    direction = end - np.asarray(points[-2], dtype=np.float64)
    direction /= np.linalg.norm(direction) + 1e-9

    def cut(figure_points):
        return (figure_points - end) @ direction > 0.0

    return cut


def chest_cover(ctx, thickness, slot, bridge=True):
    """Fabric over the breasts (or a man's chest muscles); bridge spans the chest gap the way a top
    does (a bikini does not)."""
    thickness = ctx.lift(thickness)
    s = ctx.skeleton
    if ctx.build.sex is not Sex.FEMALE:
        return [ellipsoid(s.point("chest", center), s.rotation["chest"], tuple(r + thickness for r in radii),
                          ctx.material(slot), group=slot, name="cloth", gloss=CLOTH_GLOSS)
                for center, radii in (pec_shape(ctx.build, sign) for _, sign in SIDES)]
    solids = []
    for _, sign in SIDES:
        center, radii = breast_shape(ctx.build, sign)
        solids.append(ellipsoid(s.point("chest", center), s.rotation["chest"], tuple(r + thickness for r in radii),
                                ctx.material(slot), group=slot, name="cloth", gloss=CLOTH_GLOSS))
    if bridge:
        center, radii = breast_shape(ctx.build, 1.0)
        solids.append(ellipsoid(s.point("chest", (0.0, center[1] - 0.02, center[2] - 0.02)), s.rotation["chest"],
                                (center[0], radii[1] * 0.85, radii[2] * 0.75 + thickness), ctx.material(slot),
                                group=slot, name="cloth", gloss=CLOTH_GLOSS))
    return solids


def seat_cover(ctx, thickness, slot):
    """Fabric over the buttocks, for anything that covers the pelvis."""
    thickness = ctx.lift(thickness)
    s = ctx.skeleton
    solids = []
    for _, sign in SIDES:
        center, radii = glute_shape(ctx.build, sign)
        solids.append(ellipsoid(s.point("pelvis", center), s.rotation["pelvis"], tuple(r + thickness for r in radii),
                                ctx.material(slot), group=slot, name="cloth", gloss=CLOTH_GLOSS))
    return solids


def hem_cut(ctx, hem):
    """Cut test below a flat hem: the plane across the trunk at landmark position hem, lowered by
    TRUNK_HEM_DROP so a top keeps about the length its rounded end used to reach."""
    center, frame, _, _ = trunk_sections(ctx.skeleton, ctx.build, hem, hem + 1e-4)[0]
    down = frame[:, 1]
    level = float(center @ down) + TRUNK_HEM_DROP

    def cut(points):
        return points @ down > level

    return cut


def _either(first, second):
    def cut(points):
        return first(points) | second(points)

    return cut


def hip_cover(ctx, hem, thickness, slot, top=1.0):
    """Fabric over the tops of the thighs and the seat, above a hem: a top worn over trousers has to
    clear the bulges where the trouser legs and seat meet the hips, or the trousers show through it."""
    thickness = max(ctx.lift(thickness), ctx.lift(FITTED))
    s = ctx.skeleton
    pelvis, rotation = s.position["pelvis"], s.rotation["pelvis"]
    def height(position):
        point = trunk_sections(s, ctx.build, position, position + 1e-4)[0][0]
        return float((rotation.T @ (point - pelvis))[1])

    top_y = height(min(top, 0.999))
    below = hem_cut(ctx, hem)

    def below_hem(points):
        return below(points) | (((points - pelvis) @ rotation)[:, 1] < top_y)

    below_hem.lining = False        # a thin cover over the hips: its inside is never what shows under the hem

    solids = []
    for side, sign in SIDES:
        points, radii = limb_path(s, side, LEG, ctx.build, 0.0, 0.05, thickness, limb_scale(ctx.build, "leg"))
        solids.append(ellipsoid(points[0], np.eye(3), (radii[0],) * 3, ctx.material(slot), group=slot, name="cloth",
                                gloss=CLOTH_GLOSS))
        center, glute = glute_shape(ctx.build, sign)
        solids.append(ellipsoid(s.point("pelvis", center), rotation, tuple(r + thickness for r in glute),
                                ctx.material(slot), group=slot, name="cloth", gloss=CLOTH_GLOSS))
    for cover in solids:
        cover.cut = below_hem
    return solids


def ring_curve(ctx, position, offset, samples=40, front_only=False):
    """Closed curve round the trunk at a landmark position (used for hems and waistbands)."""
    section = trunk_sections(ctx.skeleton, ctx.build, position, position + 1e-4, offset)[0]
    center, frame, rx, rz = section
    angles = np.linspace(-np.pi / 2, np.pi / 2, samples) if front_only else np.linspace(0, 2 * np.pi, samples)
    return [center + frame @ np.array([rx * np.sin(a), 0.0, rz * np.cos(a)]) for a in angles]


def limb_ring(ctx, side, spec, position, offset, samples=24):
    points, radii = limb_path(ctx.skeleton, side, spec, ctx.build, position, min(position + 0.02, 1.0), offset,
                              limb_scale(ctx.build, "arm" if spec is ARM else "leg"))
    center, radius = points[0], radii[0]
    axis = points[-1] - points[0]
    axis /= np.linalg.norm(axis) + 1e-9
    helper = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, helper)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    return [center + (u * np.cos(a) + v * np.sin(a)) * radius for a in np.linspace(0, 2 * np.pi, samples)]


def chest_point(ctx, local):
    return ctx.skeleton.point("chest", local)


# ---- garments -------------------------------------------------------------------------------------
LAYER_GAP = 0.02    # each layer sits this much further out than the one under it (> CLOTH_BLEND / 4)
# Which layer a garment is worn on: 0 next to the skin or bottoms, 1 tops worn over them, 2 outerwear.
GARMENT_LAYERS = {"t_shirt": 1, "tank_top": 1, "dress_shirt": 1, "hoodie": 2, "suit_jacket": 2, "puffer": 3}


@dataclass
class Context:
    skeleton: object
    build: object
    colors: dict
    layer: int = 0      # position of the current garment in the outfit (later garments are worn over)
    _skin: list = field(default=None, repr=False)

    def material(self, slot):
        return self.colors[slot]

    def skin(self):
        """The bare torso's solids, for things that must lie on its surface (strings, straps)."""
        if self._skin is None:
            self._skin = torso_solids(self.skeleton, self.build, None)
        return self._skin

    def lift(self, thickness):
        return thickness + self.layer * LAYER_GAP


@dataclass
class Piece:
    solids: list = field(default_factory=list)
    decals: list = field(default_factory=list)     # see decal()


ANY_SURFACE = "any"


def decal(points, width, color, opacity=1.0, on=None):
    """A line drawn on the figure: width in head heights, color a slot name. on names the slot whose
    surface must be visible under it (default: the color slot); ANY_SURFACE for lines on the skin."""
    return (points, width, color, opacity, color if on is None else on)


def crop_top(ctx):
    solids = trunk(ctx, 0.58, 0.92, TIGHT, "top") + chest_cover(ctx, TIGHT * 1.4, "top")
    for side, _ in SIDES:
        solids += sleeve(ctx, side, 0.0, 0.16, TIGHT * 1.6, "top")
    decals = [decal(ring_curve(ctx, 0.58, TIGHT), 0.012, "top", 0.7)]
    return Piece(solids, decals)


TANK_STRAP = ((0.25, -0.34, 0.31), (0.28, -0.50, 0.24), (0.31, -0.66, 0.02), (0.29, -0.55, -0.30),
              (0.26, -0.36, -0.40))     # chest frame, right side: front edge, over the shoulder, back edge


def tank_top(ctx):
    solids = trunk(ctx, 0.36, 0.86, TIGHT, "top") + chest_cover(ctx, TIGHT * 1.4, "top")
    for _, sign in SIDES:
        width = ctx.build.shoulders
        solids += strap_over_skin(ctx, [chest_point(ctx, (sign * x * width, y, z)) for x, y, z in TANK_STRAP], "top")
    return Piece(solids, [decal(ring_curve(ctx, 0.36, TIGHT), 0.010, "top", 0.6)])


def t_shirt(ctx):
    solids = trunk(ctx, 0.24, 0.93, FITTED, "top") + chest_cover(ctx, FITTED, "top")
    for side, _ in SIDES:
        solids += sleeve(ctx, side, 0.0, 0.22, FITTED, "top", flare=0.015)
    return Piece(solids, [decal(ring_curve(ctx, 0.24, FITTED), 0.012, "top", 0.6)])


def hoodie(ctx):
    solids = trunk(ctx, 0.15, 0.96, BULKY, "top", flare=lambda t: 0.04 * (1 - t)) + chest_cover(ctx, BULKY, "top")
    for side, _ in SIDES:
        solids += sleeve(ctx, side, 0.0, 0.96, LOOSE, "top", flare=0.015)
        solids += sleeve(ctx, side, 0.92, 1.0, LOOSE * 1.2, "trim")              # ribbed cuff
    solids += trunk(ctx, 0.13, 0.20, BULKY * 1.1, "trim")                         # ribbed hem
    solids += hood(ctx)
    pocket = [chest_point(ctx, p) for p in ((-0.30, 0.70, 0.38), (-0.26, 0.42, 0.42), (0.26, 0.42, 0.42),
                                            (0.30, 0.70, 0.38))]
    strings = [[chest_point(ctx, (sign * 0.10, -0.52, 0.32)), chest_point(ctx, (sign * 0.11, -0.10, 0.44 if
                ctx.build.sex is Sex.FEMALE else 0.40))] for _, sign in SIDES]
    decals = [decal(pocket, 0.012, "trim", 0.8, on="top")] + [decal(line, 0.014, "trim", 0.9, on="top")
                                                              for line in strings]
    return Piece(solids, decals)


HOOD_COLLAR = ((0.0, -0.62, -0.30), (0.40, 0.26, 0.22))   # chest-local centre and radii of the hood's collar roll
HOOD_SPAN = (0.93, 0.64)                     # trunk positions where the lowered hood starts and where its point ends
HOOD_HALF_WIDTHS = (0.36, 0.40, 0.36, 0.26, 0.12)   # head heights, from the neck down to the rounded point
HOOD_HALF_THICKNESS = 0.045                  # the hood is two layers of cloth lying flat
HOOD_GAP = 0.03                              # head heights the hood stands off the back: its edges cast a shadow


def hood(ctx):
    """A lowered hood: the roll round the back of the neck, and the hood itself lying flat down the upper
    back as its own layer (one blended lump disappears into the back, and the hoodie reads as a sweater)."""
    s = ctx.skeleton
    collar_center, collar_radii = HOOD_COLLAR
    collar = ellipsoid(s.point("chest", collar_center), s.rotation["chest"], collar_radii, ctx.material("top"),
                       group="top", name="cloth", gloss=CLOTH_GLOSS)
    lift = ctx.lift(BULKY) + HOOD_HALF_THICKNESS + HOOD_GAP
    points = []
    for position in np.linspace(*HOOD_SPAN, len(HOOD_HALF_WIDTHS)):
        center, frame, _, rz = trunk_sections(s, ctx.build, position, position + 1e-4, lift)[0]
        points.append(center - frame[:, 2] * rz)                 # on the back, one layer out
    points = np.array(points)
    sections = []
    for index, (point, half_width) in enumerate(zip(points, HOOD_HALF_WIDTHS)):
        along = points[min(index + 1, len(points) - 1)] - points[max(index - 1, 0)]
        along /= np.linalg.norm(along)
        sections.append((point, _frame(along, -s.rotation["chest"][:, 2]), half_width, HOOD_HALF_THICKNESS))
    back = section_sweep(sections, ctx.material("top"), step=0.03, overlap=2.5, group="top_hood", name="cloth",
                         gloss=CLOTH_GLOSS)
    return [collar] + back


COLLAR_GAP = 0.03       # head heights between the neck and the collar band's centre line


COLLAR_HEIGHT = -0.62   # chest-frame y of the collar band at the front of the neck
COLLAR_TIP_AT = 0.84    # trunk position where the collar points end (just above the upper chest)
COLLAR_TIP_ANGLE = 0.22  # radians either side of the front where the collar points end


def _frame(y_axis, z_hint):
    """Orthonormal frame (columns) whose y runs along y_axis and whose z is closest to z_hint."""
    y = np.asarray(y_axis, dtype=np.float64)
    y = y / (np.linalg.norm(y) + 1e-9)
    z = np.asarray(z_hint, dtype=np.float64) - y * (y @ np.asarray(z_hint, dtype=np.float64))
    z = z / (np.linalg.norm(z) + 1e-9)
    return np.stack([np.cross(y, z), y, z], axis=1)
COLLAR_SPAN = 2.2       # radians either side of the front the collar band reaches


def dress_shirt(ctx):
    s = ctx.skeleton
    solids = trunk(ctx, 0.20, 0.97, FITTED, "top") + chest_cover(ctx, FITTED, "top")   # up under the collar
    for side, _ in SIDES:
        solids += sleeve(ctx, side, 0.0, 0.97, TIGHT * 1.2, "top", flare=0.01)
    # The collar band stands round the neck above the shirt's top edge, a little lower at the front.
    radius = (MALE_NECK if ctx.build.sex is Sex.MALE else FEMALE_NECK) * 1.05 + COLLAR_GAP
    collar = [chest_point(ctx, (radius * np.sin(a), COLLAR_HEIGHT - 0.06 * (1 - np.cos(a)) / 2,
                                -0.02 + radius * np.cos(a))) for a in np.linspace(-COLLAR_SPAN, COLLAR_SPAN, 13)]
    solids.append(sweep(collar, [0.045] * len(collar), ctx.material("top"), group="top_collar", name="cloth"))
    buttons = [chest_point(ctx, (0.0, y, 0.40 if ctx.build.sex is Sex.MALE else 0.42)) for y in
               np.linspace(-0.40, 0.60, 6)]
    placket = [decal(buttons, 0.010, "top", 0.5)]
    # Collar points: thin flaps from the front of the band down onto the chest, outlined.
    lift = ctx.lift(FITTED) + 0.012
    points = []
    for _, sign in SIDES:
        root = chest_point(ctx, (sign * 0.02, COLLAR_HEIGHT + 0.03, radius + 0.01))
        tip = _ring(ctx, COLLAR_TIP_AT, [sign * COLLAR_TIP_ANGLE], lift)[0]
        side = _ring(ctx, 0.96, [sign * 0.75], lift)[0]
        along = tip - root
        normal = s.rotation["chest"] @ np.array([0.0, -0.35, 1.0])
        solids.append(ellipsoid((root + tip) / 2, _frame(along, normal), (0.06, float(np.linalg.norm(along)) / 2 + 0.015,
                                                                         0.012), ctx.material("top"), group="top_collar",
                                name="cloth", gloss=CLOTH_GLOSS))
        points.append(decal([root, tip, side], 0.012, "top", 0.9))
    return Piece(solids, placket + points + [decal([b, b + s.rotation["chest"] @ np.array([0.0, 0.008, 0.0])], 0.022,
                                                   "trim", 0.9, on="top") for b in buttons])


JACKET_V = (-0.58, 0.62, 0.21)        # chest frame: collar y, button y, half width of the opening at the collar


def jacket_opening(ctx):
    """Cut test for the V-shaped front opening of a jacket (chest frame)."""
    s = ctx.skeleton
    origin, frame = s.position["chest"], s.rotation["chest"]
    top, bottom, half = JACKET_V

    def cut(points):
        local = (points - origin) @ frame
        width = half * np.clip((bottom - local[:, 1]) / (bottom - top), 0.0, 1.0)
        return (local[:, 2] > 0.05) & (np.abs(local[:, 0]) < width) & (local[:, 1] < bottom)

    return cut


def suit_jacket(ctx):
    opening = jacket_opening(ctx)
    solids = (trunk(ctx, 0.14, 0.95, LOOSE, "outer", flare=lambda t: 0.02 * (1 - t), cut=opening)
              + [_with_cut(solid, opening) for solid in chest_cover(ctx, LOOSE, "outer")])
    for side, _ in SIDES:
        solids += sleeve(ctx, side, -0.02, 0.95, TIGHT * 1.3, "outer", flare=0.01)
    # Opening of the jacket: lapel edges from the collar down to the button, and the shirt and tie inside.
    lapels = [[chest_point(ctx, p) for p in ((sign * 0.20, -0.58, 0.20), (sign * 0.30, -0.30, 0.40),
                                             (sign * 0.10, 0.40, 0.44), (0.0, 0.62, 0.42))] for _, sign in SIDES]
    decals = [decal(line, 0.016, "outer_line", 1.0, on="outer") for line in lapels]
    decals.append(decal([chest_point(ctx, (0.0, 0.62, 0.42)), chest_point(ctx, (0.0, 1.05, 0.36))], 0.012,
                        "outer_line", 0.8, on="outer"))
    return Piece(solids, decals)


def _with_cut(solid, cut):
    solid.cut = cut
    return solid


def tie(ctx):
    points = [chest_point(ctx, p) for p in ((0.0, -0.52, 0.30), (0.0, -0.30, 0.42), (0.0, 0.10, 0.45),
                                            (0.0, 0.45, 0.43))]
    widths = np.array([0.05, 0.06, 0.075, 0.08])
    frame = ctx.skeleton.rotation["chest"]
    return Piece(section_sweep([(p, frame, w, 0.02) for p, w in zip(points, widths)], ctx.material("accent"),
                               step=0.02, group="accent", name="cloth"))


HEM_RING_MIN = 0.15     # leg length (share of the leg) below which trousers get no hem line
SHORTS_LENGTH = 0.45    # trousers with legs shorter than this share of the leg get a front seam
SEAM_TOP = 0.30         # trunk position where the front seam starts (below the waistband)
SEAM_BOTTOM = 0.06      # trunk position where it ends, above the crotch (a seam into the crotch reads as an arrow)
SEAM_SAMPLES = 8
SEAM_WIDTH = 0.010
SEAM_OPACITY = 0.6


POCKET_HAND = (0.06, 0.26, 0.12)  # half sizes of the fabric over a hand in a pocket, in the wrist frame
POCKET_ALONG = 0.26               # head heights from the wrist along the fingers to the middle of that fabric
POCKET_NEAR = 0.12                # a hand this close to the hips (and in front of them) is in a front pocket
POCKET_SPAN = (-0.45, 0.55)       # pelvis-local heights between which a hand can be in a front pocket
POCKET_SLEEVE_ROOM = 0.20         # head heights a top's pocket cover reaches back up the forearm
POCKET_SLEEVE_WIDEN = 0.35        # extra half width per head height of that reach (room for the cuff)
SLEEVE_AT_WRIST = 0.9             # a sleeve ending past this share of the arm reaches the wrist
POCKET_TUCK = 0.04                # head heights above the wrist where a sleeve going into a pocket ends


def pocket_sides(ctx):
    """Sides whose hand sits in a front pocket (hands_in_pockets)."""
    s = ctx.skeleton
    sides = []
    for side, _ in SIDES:
        frame = s.rotation[f"wrist_{side}"]
        center = s.position[f"wrist_{side}"] + frame @ np.array([0.0, POCKET_ALONG, 0.0])
        local = (center - s.position["pelvis"]) @ s.rotation["pelvis"]
        if local[2] <= 0.0 or not POCKET_SPAN[0] < local[1] < POCKET_SPAN[1]:
            continue
        if distance_to_solids(center[None], ctx.skin())[0] > POCKET_NEAR:
            continue
        sides.append(side)
    return sides


def pocket_hands(ctx, thickness, slot, sleeve_room=0.0):
    """Cloth over each hand that sits in a front pocket (hands_in_pockets): the hand is under the fabric,
    so the trousers bulge round it instead of the hand lying on top of them. sleeve_room (head heights)
    makes room for a sleeve end: the cover reaches that far back up the forearm and widens to take it
    (a top worn over the trousers, whose sleeves go into the pocket with the hands)."""
    s = ctx.skeleton
    lift = ctx.lift(thickness)
    half_x, half_y, half_z = POCKET_HAND
    half_y += sleeve_room / 2
    widen = sleeve_room * POCKET_SLEEVE_WIDEN
    solids = []
    for side in pocket_sides(ctx):
        frame = s.rotation[f"wrist_{side}"]
        center = s.position[f"wrist_{side}"] + frame @ np.array([0.0, POCKET_ALONG - sleeve_room / 2, 0.0])
        solids.append(ellipsoid(center, frame, (half_x + lift + widen, half_y + lift, half_z + lift + widen),
                                ctx.material(slot), group=slot, name="cloth", gloss=CLOTH_GLOSS))
    return solids


def tuck_into_pocket(ctx, side):
    """Cut test for a sleeve whose hand is in a pocket under a top: the sleeve ends just above the wrist,
    inside the top's pocket cover, so no cuff sticks out of the cloth."""
    s = ctx.skeleton
    wrist, elbow = s.position[f"wrist_{side}"], s.position[f"elbow_{side}"]
    along = (wrist - elbow) / (np.linalg.norm(wrist - elbow) + 1e-9)
    end = wrist - along * POCKET_TUCK

    def cut(points):
        return (points - end) @ along > 0.0

    cut.lining = False
    return cut


def trousers(ctx, length=1.0, thickness=FITTED, flare=0.0, slot="bottom"):
    solids = trunk(ctx, 0.0, 0.40, thickness, slot) + seat_cover(ctx, thickness, slot) + pocket_hands(ctx, thickness, slot)
    decals = [decal(ring_curve(ctx, 0.40, thickness), 0.014, slot, 0.6)]
    for side, _ in SIDES:
        solids += leg(ctx, side, 0.0, length, thickness, slot, flare)
        if length >= HEM_RING_MIN:      # very short legs: the hem is the outline itself
            decals.append(decal(limb_ring(ctx, side, LEG, max(length - 0.01, 0.0), thickness), 0.012, slot, 0.6))
    if length < SHORTS_LENGTH:
        decals.append(front_seam(ctx, thickness, slot))
    return Piece(solids, decals)


def front_seam(ctx, thickness, slot):
    """The front seam from below the waistband down toward the crotch: on shorts it tells the two legs
    apart where the cloth between them is one smooth surface."""
    s = ctx.skeleton
    lift = ctx.lift(thickness)
    points = []
    for position in np.linspace(SEAM_TOP, SEAM_BOTTOM, SEAM_SAMPLES):
        center, frame, _, rz = trunk_sections(s, ctx.build, position, position + 1e-4, lift)[0]
        points.append(center + frame[:, 2] * rz)
    return decal(points, SEAM_WIDTH, slot, SEAM_OPACITY)


def jeans(ctx):
    piece = trousers(ctx, 0.98, FITTED, 0.02)
    s = ctx.skeleton
    for _, sign in SIDES:      # front pocket openings
        piece.decals.append(decal([s.point("pelvis", p) for p in ((sign * 0.20, -0.32, 0.40), (sign * 0.40, -0.10, 0.38),
                                                                    (sign * 0.56, -0.22, 0.30))], 0.010, "bottom", 0.7))
    return piece


HOT_PANTS_LEG = 0.19     # share of the leg the legs of hot pants cover: the openings sit just below the crotch


def hot_pants(ctx):
    return trousers(ctx, HOT_PANTS_LEG, TIGHT * 1.3)


def swim_trunks(ctx):
    return trousers(ctx, 0.30, FITTED, 0.0)


SKIRT_LAP_BEND = (0.35, 1.0)   # radians the thighs lift from the pelvis's down axis: from the first the skirt
                               # starts to follow them, from the second it lies along them over the lap
SKIRT_FLARE = (0.12, 0.10)     # head heights the skirt widens and deepens per third of its length (standing)
SKIRT_LAP_FLARE = (0.05, 0.03)  # the same for a skirt lying over the thighs (it spreads less)


def skirt_flared(ctx, length=1.35, slot="bottom"):
    s = ctx.skeleton
    # Follow the body exactly from the waist to the widest hip (its rounded flank), then flare out.
    fitted = trunk_sections(s, ctx.build, T["hip"], T["waist"], FITTED)
    hip_center, hip_frame, hip_rx, hip_rz = fitted[0]
    direction, frame, lap, lap_rz = _skirt_fall(ctx, hip_frame)
    # Over the lap the skirt runs along the thighs' centre line (between the hip joints), not the pelvis's.
    joints = sum(ctx.skeleton.position[f"hip_{side}"] for side, _ in SIDES) / len(SIDES)
    start = hip_center * (1.0 - lap) + joints * lap
    sections = []
    for k in (3, 2, 1):
        rx = hip_rx + (SKIRT_FLARE[0] * (1.0 - lap) + SKIRT_LAP_FLARE[0] * lap) * k
        rz = (hip_rz + SKIRT_FLARE[1] * k) * (1.0 - lap) + (lap_rz + SKIRT_LAP_FLARE[1] * k) * lap
        sections.append((start + direction * length * k / 3, frame, rx, rz))
    sections += fitted
    hem = flat_hem([sections[1][0], sections[0][0]])
    solids = section_sweep(sections, ctx.material(slot), step=0.03, group=slot, name="cloth", gloss=CLOTH_GLOSS,
                           cut=hem)
    # A thigh stepping forward pushes the skirt out instead of poking through it.
    for side, _ in SIDES:
        solids += leg(ctx, side, 0.0, 0.22, LOOSE, slot)
    return Piece(solids + seat_cover(ctx, LOOSE, slot))


def _skirt_fall(ctx, hip_frame):
    """Which way a skirt falls from the hips: straight down while standing, along the thighs over the
    lap when sitting (so the thighs do not pierce it). Returns (direction, section frame, lap share,
    thickness over the thighs)."""
    s = ctx.skeleton
    down = s.rotation["pelvis"] @ np.array([0.0, 1.0, 0.0])
    thighs = sum(s.position[f"knee_{side}"] - s.position[f"hip_{side}"] for side, _ in SIDES)
    thighs /= np.linalg.norm(thighs) + 1e-9
    bend = float(np.arccos(np.clip(down @ thighs, -1.0, 1.0)))
    lap = float(np.clip((bend - SKIRT_LAP_BEND[0]) / (SKIRT_LAP_BEND[1] - SKIRT_LAP_BEND[0]), 0.0, 1.0))
    lap = lap * lap * (3.0 - 2.0 * lap)
    if lap == 0.0:
        return down, hip_frame, 0.0, 0.0
    direction = down * (1.0 - lap) + thighs * lap
    direction /= np.linalg.norm(direction)
    across = s.rotation["pelvis"] @ np.array([1.0, 0.0, 0.0])
    depth = np.cross(across, direction)
    depth /= np.linalg.norm(depth)
    frame = np.stack([np.cross(direction, depth), direction, depth], axis=1)
    _, radii = limb_path(s, SIDES[0][0], LEG, ctx.build, 0.0, 0.25, ctx.lift(LOOSE), limb_scale(ctx.build, "leg"))
    return direction, frame, lap, float(radii.max())


def sundress(ctx):
    solids = trunk(ctx, T["waist"], 0.82, TIGHT, "top") + chest_cover(ctx, TIGHT * 1.3, "top")
    straps = [[chest_point(ctx, (sign * 0.28, 0.0, 0.34)), chest_point(ctx, (sign * 0.30, -0.42, 0.18)),
               chest_point(ctx, (sign * 0.28, -0.52, -0.10))] for _, sign in SIDES]
    for strap in straps:
        solids += strap_over_skin(ctx, strap, "top")
    piece = skirt_flared(ctx, 1.30, "top")
    belt = trunk(ctx, T["waist"] - 0.02, T["waist"] + 0.03, FITTED * 1.4, "accent")
    return Piece(solids + piece.solids + belt, [decal(ring_curve(ctx, 0.82, TIGHT, front_only=True), 0.012, "top",
                                                      0.5)])


def bikini(ctx):
    """Triangle top on halter and back strings, brief with side ties. Strings are thin solids that
    run over the body surface, so they stay whole from every angle."""
    solids = []
    for _, sign in SIDES:
        solids += bikini_cup(ctx, sign)
        solids += bikini_strings(ctx, sign)
    # The bottom is cut from a brief that covers the hips, seat and tops of the thighs: a low waistline
    # above, and leg openings that rise from the crotch to high on the hips (lower at the back).
    bottom = trunk(ctx, 0.0, 0.30, BIKINI_FIT, "top") + seat_cover(ctx, BIKINI_FIT, "top")
    for side, _ in SIDES:
        bottom += leg(ctx, side, 0.0, 0.06, BIKINI_FIT, "top")
    cut = bikini_cut(ctx)
    for solid in bottom:
        solid.cut = cut
    for _, sign in SIDES:
        solids += side_tie(ctx, sign)
    return Piece(solids + bottom, [])


CUP_TRIANGLE = ((-0.10, -1.02), (-0.95, 0.80), (1.05, 0.70))   # apex, inner and outer corner (breast radii, x outward)
STRING_RADIUS = 0.012
STRING_LIFT = 0.012          # head heights a string rides above the surface it follows
STRING_CLEARANCE = STRING_RADIUS + SMOOTH_BLEND / 4   # string axis to the skin, clear of the creases blending fills
STRING_SPACING = 0.015       # head heights between the points of a string laid over the skin
SURFACE_ROUNDS = 4           # push-out and smoothing rounds when laying a string over the skin
PUSH_STEPS = 3               # Newton steps of each push-out
CORNER_SEARCH = 24           # steps from a cup corner toward the triangle's centre
CUP_SHOWING = 0.8            # share of the cup's lift that must clear the skin for the cup to show
HALTER_ANGLES = (0.55, 1.6, 2.5, np.pi)   # round the base of the neck from the front to the knot at the back
HALTER_NECK_AT = 0.30        # share of the neck's length (base to head) where the halter goes round it
LEVEL_SAMPLES = 40           # trunk positions searched for the one level with a point
HUG_TOLERANCE = 0.003        # head heights a hugging strap may stand off its clearance
STRAP_HALF_WIDTH = 0.035     # head heights: half the width of a flat shoulder strap (tank tops, dresses)
STRAP_HALF_THICKNESS = 0.010
STRAP_PRESS = 0.005          # a strap lies this close to the skin: in the creases blending fills it presses in
STRAP_STEP = 0.02            # head heights between the slices of a strap
STRAP_OVERLAP = 2.5
PROBE = 0.004                # head heights of the finite difference that finds the way out of the skin


def _cup_corner(ctx, sign, corner):
    """Figure-space point on the cup at a CUP_TRIANGLE corner. A corner that falls where the chest
    hides the cup is moved toward the triangle's centre until the cup there stands clear of the skin,
    so strings start at the visible corner instead of inside the chest."""
    (cx, cy, cz), radii = breast_shape(ctx.build, sign)
    lift = ctx.lift(TIGHT)
    rx, ry, rz = (r + lift for r in radii)
    start = np.asarray(CUP_TRIANGLE[corner], dtype=np.float64)
    toward = np.mean(CUP_TRIANGLE, axis=0) - start
    for share in np.linspace(0.0, 1.0, CORNER_SEARCH):
        u, v = start + toward * share
        x, y = cx + sign * u * radii[0], cy + v * radii[1]
        inside = 1.0 - ((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2
        if inside <= 0.0:
            continue
        point = ctx.skeleton.point("chest", (x, y, cz + rz * np.sqrt(inside)))
        if distance_to_solids(point[None], ctx.skin())[0] >= lift * CUP_SHOWING:
            return point
    raise ValueError(f"cup corner {corner} is hidden by the chest for this build")


def bikini_cup(ctx, sign):
    """The breast cover cut to a triangle: apex near the centre top, base under the breast."""
    s = ctx.skeleton
    center, radii = breast_shape(ctx.build, sign)
    cup = ellipsoid(s.point("chest", center), s.rotation["chest"], tuple(r + ctx.lift(TIGHT) for r in radii),
                    ctx.material("top"), group="top", name="cloth", gloss=CLOTH_GLOSS)
    corners = [(center[0] + sign * u * radii[0], center[1] + v * radii[1]) for u, v in CUP_TRIANGLE]
    origin, frame = s.position["chest"], s.rotation["chest"]

    def outside(points):
        local = (points - origin) @ frame
        x, y = local[:, 0], local[:, 1]
        signs = []
        for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
            signs.append((bx - ax) * (y - ay) - (by - ay) * (x - ax))
        signs = np.stack(signs)
        return ~((signs >= 0).all(axis=0) | (signs <= 0).all(axis=0))

    cup.cut = outside
    return [cup]


def _ring(ctx, position, angles, lift):
    """Points round the trunk surface at a landmark position (angle 0 front, +/- pi/2 the sides, pi the back)."""
    center, frame, rx, rz = trunk_sections(ctx.skeleton, ctx.build, position, position + 1e-4, lift)[0]
    return [center + frame @ np.array([rx * np.sin(a), 0.0, rz * np.cos(a)]) for a in angles]


def over_skin(ctx, path, clearance=STRING_CLEARANCE, hug=False):
    """Resample a path and lift every point that lies inside or too near the skin, so a string drawn
    along it rests on the body instead of sinking into breasts, collarbones or the neck. Points
    already clear stay where they are, so a string still bridges hollows such as the chest gap.
    hug=True also pulls points that stand off the body down onto it: a shoulder strap laid by fixed
    chest-frame points would otherwise hang in the air over a broad or narrow shoulder."""
    points = _resample(np.asarray(path, dtype=np.float64), STRING_SPACING)
    skin = ctx.skin()
    for _ in range(SURFACE_ROUNDS):
        points = _push_out(points, skin, clearance, hug)
        points[1:-1] = (points[:-2] + 2.0 * points[1:-1] + points[2:]) / 4.0
    return _push_out(points, skin, clearance, hug)


def _resample(path, spacing):
    lengths = np.linalg.norm(np.diff(path, axis=0), axis=1)
    along = np.concatenate([[0.0], np.cumsum(lengths)])
    count = max(2, int(np.ceil(along[-1] / spacing)) + 1)
    targets = np.linspace(0.0, along[-1], count)
    return np.stack([np.interp(targets, along, path[:, axis]) for axis in range(3)], axis=1)


def _push_out(points, solids, clearance, hug=False):
    points = points.copy()
    for _ in range(PUSH_STEPS):
        distance = distance_to_solids(points, solids)
        short = np.abs(distance - clearance) > HUG_TOLERANCE if hug else distance < clearance
        if not short.any():
            break
        points[short] = points[short] + _away_from_skin(points[short], solids) * (clearance - distance[short])[:, None]
    return points


def _away_from_skin(points, solids):
    """Unit directions in which the distance to the skin grows fastest (the skin's normals near it)."""
    gradient = np.stack([distance_to_solids(points + offset, solids) - distance_to_solids(points - offset, solids)
                         for offset in np.eye(3) * PROBE], axis=1)
    return gradient / (np.linalg.norm(gradient, axis=1, keepdims=True) + 1e-9)


def strap_over_skin(ctx, path, slot, half_width=STRAP_HALF_WIDTH, half_thickness=STRAP_HALF_THICKNESS):
    """A flat strap laid on the body along path: a ribbon whose face follows the skin. A round tube
    as wide as a strap stands up from the shoulder like a handle when seen against the sky."""
    points = over_skin(ctx, path, half_thickness + STRAP_PRESS, hug=True)
    normals = _away_from_skin(points, ctx.skin())
    sections = []
    for index, point in enumerate(points):
        tangent = points[min(index + 1, len(points) - 1)] - points[max(index - 1, 0)]
        tangent /= np.linalg.norm(tangent) + 1e-9
        normal = normals[index] - tangent * (normals[index] @ tangent)
        normal /= np.linalg.norm(normal) + 1e-9
        sections.append((point, np.stack([np.cross(tangent, normal), tangent, normal], axis=1), half_width,
                         half_thickness))
    return section_sweep(sections, ctx.material(slot), step=STRAP_STEP, overlap=STRAP_OVERLAP, group="top_strap",
                         name="cloth", gloss=CLOTH_GLOSS)


def _neck_ring(ctx, angles):
    """Points round the neck a little above its base (angle 0 front, pi the back), where a halter lies."""
    (base, top), (base_radius, top_radius) = neck_path(ctx.skeleton, ctx.build)
    center = base + (top - base) * HALTER_NECK_AT
    radius = base_radius + (top_radius - base_radius) * HALTER_NECK_AT + STRING_CLEARANCE
    frame = ctx.skeleton.rotation["chest"]
    return [center + frame @ np.array([radius * np.sin(a), 0.0, radius * np.cos(a)]) for a in angles]


def _trunk_position_at(ctx, point):
    """Trunk position (TRUNK_LANDMARKS scale) whose cross-section is level with a figure-space point."""
    positions = np.linspace(T["waist"], T["neck"], LEVEL_SAMPLES)
    down = ctx.skeleton.rotation["chest"] @ np.array([0.0, 1.0, 0.0])
    heights = [float((center - point) @ down)
               for center, *_ in (trunk_sections(ctx.skeleton, ctx.build, p, p + 1e-4)[0] for p in positions)]
    return float(positions[int(np.argmin(np.abs(heights)))])


def bikini_strings(ctx, sign):
    """Halter string from the cup apex round the back of the neck, back string from the outer corner
    round the ribs; both meet their partner at the centre of the back."""
    material = ctx.material("top")
    lift = ctx.lift(TIGHT) + STRING_LIFT
    apex = _cup_corner(ctx, sign, 0)
    halter = [apex] + _neck_ring(ctx, [sign * a for a in HALTER_ANGLES])
    outer = _cup_corner(ctx, sign, 2)
    back = [outer] + _ring(ctx, _trunk_position_at(ctx, outer), [sign * a for a in np.linspace(1.15, np.pi, 6)], lift)
    inner = _cup_corner(ctx, sign, 1)
    inner = [inner, (inner + _cup_corner(ctx, -sign, 1)) / 2]
    strings = [over_skin(ctx, path) for path in (halter, back, inner)]
    return [sweep(path, [STRING_RADIUS] * len(path), material, group="top_strap", name="cloth", gloss=CLOTH_GLOSS)
            for path in strings]


def side_tie(ctx, sign):
    """A small knot on the hip where the brief's side strings are tied, with two short loose ends."""
    material = ctx.material("top")
    lift = BIKINI_FIT + STRING_LIFT
    knot = _ring(ctx, T["hip"] + 0.03, [sign * np.pi / 2], lift)[0]
    down = ctx.skeleton.rotation["pelvis"] @ np.array([0.0, 1.0, 0.0])
    out = ctx.skeleton.rotation["pelvis"] @ np.array([sign, 0.0, 0.0])
    solids = [ellipsoid(knot, ctx.skeleton.rotation["pelvis"], (0.028, 0.034, 0.028), material, group="top_strap",
                        name="cloth", gloss=CLOTH_GLOSS)]
    for spread in (-0.35, 0.35):
        forward = ctx.skeleton.rotation["pelvis"] @ np.array([0.0, 0.0, spread])
        tail = [knot, knot + down * 0.07 + forward * 0.06 + out * 0.012, knot + down * 0.15 + forward * 0.08 + out * 0.02]
        solids.append(sweep(tail, [0.013, 0.011, 0.009], material, group="top_strap", name="cloth"))
    return solids


BIKINI_FIT = 0.032          # clears the skin's own blend bulge where hips and thighs meet
BIKINI_WAIST = -0.06        # pelvis-local y of the waistline
BIKINI_CROTCH = 0.40        # pelvis-local y where the leg openings meet
BIKINI_HIP = (-0.02, 0.16)  # pelvis-local y the leg openings reach at the side, front and back
BIKINI_HIP_X = 0.56         # half width at which the openings reach that height


def bikini_cut(ctx):
    pelvis, rotation = ctx.skeleton.position["pelvis"], ctx.skeleton.rotation["pelvis"]
    hips = 1.0 + (ctx.build.hips - 1.0) * 0.8

    def cut(points):
        x, y, z = ((points - pelvis) @ rotation).T
        backness = np.clip(0.5 - z / 0.4, 0.0, 1.0)
        side_y = BIKINI_HIP[0] + (BIKINI_HIP[1] - BIKINI_HIP[0]) * backness
        rise = np.clip(np.abs(x) / (BIKINI_HIP_X * hips), 0.0, 1.0) ** 0.8
        opening = BIKINI_CROTCH - (BIKINI_CROTCH - side_y) * rise
        return (y < BIKINI_WAIST) | (y > opening)

    return cut


def sneakers(ctx):
    s = ctx.skeleton
    solids = []
    for side, _ in SIDES:
        points = [s.point(f"ankle_{side}", p) for p, _ in FOOT]
        radii = np.array([r for _, r in FOOT]) + 0.03
        solids.append(sweep(points, radii, ctx.material("shoes"), group="shoes", name="shoes"))
        sole = [s.point(f"ankle_{side}", (x, y + 0.08, z)) for x, y, z in ((0, 0.06, -0.10), (0, 0.10, 0.25),
                                                                          (0, 0.10, 0.42))]
        solids.append(sweep(sole, [0.07, 0.07, 0.05], ctx.material("sole"), group="sole", name="shoes"))
    return Piece(solids)


def flats(ctx):
    s = ctx.skeleton
    solids = []
    for side, _ in SIDES:
        points = [s.point(f"ankle_{side}", p) for p, _ in FOOT[1:]]
        radii = np.array([r for _, r in FOOT[1:]]) + 0.012
        solids.append(sweep(points, radii, ctx.material("shoes"), group="shoes", name="shoes"))
    return Piece(solids)


def _shoes_fitted(ctx):
    s = ctx.skeleton
    solids = []
    for side, _ in SIDES:
        points = [s.point(f"ankle_{side}", p) for p, _ in FOOT]
        radii = np.array([r for _, r in FOOT]) + 0.018
        solids.append(sweep(points, radii, ctx.material("shoes"), group="shoes", name="shoes", gloss=0.5))
    return Piece(solids)


# ---- winter wear ------------------------------------------------------------------------------------
PUFFY = 0.13                                  # head heights a down jacket stands off the body
PUFFER_QUILT = (0.24, 0.38, 0.52, 0.66, 0.80)  # trunk positions of the quilting seams
PUFFER_SLEEVE_QUILT = (0.28, 0.48, 0.68)       # arm positions of the sleeve seams
PUFFER_COLLAR = (0.18, 0.055, 3)              # head heights the stand-up collar rises, roll radius, rolls stacked
QUILT_WIDTH = 0.012
QUILT_OPACITY = 0.75


def puffer(ctx):
    """Down jacket: thick quilted body and sleeves, knit cuffs, a stand-up collar zipped to the chin."""
    solids = trunk(ctx, 0.08, 0.98, PUFFY, "outer", flare=lambda t: 0.03 * (1 - t)) + chest_cover(ctx, PUFFY, "outer")
    for side, _ in SIDES:
        solids += sleeve(ctx, side, -0.02, 0.93, PUFFY * 0.75, "outer", flare=0.01)
        solids += sleeve(ctx, side, 0.90, 0.99, LOOSE, "trim")
    rise, roll, rolls = PUFFER_COLLAR
    radius = (MALE_NECK if ctx.build.sex is Sex.MALE else FEMALE_NECK) * 1.1 + roll + COLLAR_GAP
    for lift in np.linspace(0.0, rise, rolls):
        ring = [chest_point(ctx, (radius * np.sin(a), COLLAR_HEIGHT + 0.06 - lift, -0.02 + radius * np.cos(a)))
                for a in np.linspace(-np.pi, np.pi, 17)]
        solids.append(sweep(ring, [roll] * len(ring), ctx.material("outer"), group="outer_collar", name="cloth",
                            gloss=CLOTH_GLOSS))
    offset = ctx.lift(PUFFY) + 0.01
    decals = [decal(ring_curve(ctx, position, offset), QUILT_WIDTH, "outer_line", QUILT_OPACITY, on="outer")
              for position in PUFFER_QUILT]
    for side, _ in SIDES:
        decals += [decal(limb_ring(ctx, side, ARM, position, ctx.lift(PUFFY * 0.75)), QUILT_WIDTH, "outer_line",
                         QUILT_OPACITY, on="outer") for position in PUFFER_SLEEVE_QUILT]
    zipper = [chest_point(ctx, (0.0, COLLAR_HEIGHT + 0.10, radius + roll)), *ring_curve(ctx, 0.85, offset, 3, True)[1:2],
              *ring_curve(ctx, 0.10, offset, 3, True)[1:2]]
    decals.append(decal(zipper, QUILT_WIDTH * 1.4, "outer_line", 0.9, on="outer"))
    return Piece(solids, decals)


BEANIE_CROWN = ((0.0, -0.15, -0.07), (0.52, 0.60, 0.56))   # head-local centre and radii, over the hair cap
BEANIE_BRIM = (-0.24, 0.10)    # head-local y of the lower edge at the forehead and at the back (it sits lower behind)
BEANIE_CUFF = 0.17             # head heights the folded cuff reaches above the brim
BEANIE_CUFF_SCALE = 1.03       # the cuff is two folds of knit, a little proud of the crown
BEANIE_RIBS = 28               # knit ribs round the cuff
HEAD_REACH = 1.0               # head-local z of the points that define the brim's tilt (in front of and behind the head)


def beanie(ctx):
    """Knit cap pulled down over the hair, the brim lower at the back, with a folded cuff."""
    s = ctx.skeleton
    center, radii = BEANIE_CROWN
    front = np.array([0.0, BEANIE_BRIM[0], HEAD_REACH])
    back = np.array([0.0, BEANIE_BRIM[1], -HEAD_REACH])
    tilt = back - front
    down = np.array([0.0, -tilt[2], tilt[1]])
    down /= np.linalg.norm(down)
    if down[1] < 0:
        down = -down
    normal = s.rotation["head"] @ down
    brim = s.point("head", front)
    cuff_top = s.point("head", front - down * BEANIE_CUFF)

    def below(point):
        def cut(points):
            return (points - point) @ normal > 0.0
        cut.lining = False
        return cut

    def outside_cuff(points):
        return ((points - brim) @ normal > 0.0) | ((points - cuff_top) @ normal < 0.0)
    outside_cuff.lining = False

    crown = ellipsoid(s.point("head", center), s.rotation["head"], radii, ctx.material("hat"), group="hat",
                      name="cloth", gloss=CLOTH_GLOSS)
    crown.cut = below(brim)
    cuff = ellipsoid(s.point("head", center), s.rotation["head"], tuple(r * BEANIE_CUFF_SCALE for r in radii),
                     ctx.material("hat"), group="hat_cuff", name="cloth", gloss=CLOTH_GLOSS)
    cuff.cut = outside_cuff
    ribs = []
    for angle in np.linspace(0.0, 2 * np.pi, BEANIE_RIBS, endpoint=False):
        rim = _ellipse_rim(center, radii, front, down, angle, BEANIE_CUFF_SCALE)
        ribs.append(decal([s.point("head", rim), s.point("head", rim - down * BEANIE_CUFF * 0.85)], 0.008, "hat",
                          0.45))
    return Piece([crown, cuff], ribs)


def _ellipse_rim(center, radii, plane_point, down, angle, scale):
    """Head-local point where the ellipsoid (center, radii * scale) meets the brim plane, in direction angle."""
    direction = np.array([np.sin(angle), 0.0, np.cos(angle)])
    radii = np.asarray(radii) * scale
    lo, hi = 0.0, 2.0
    for _ in range(30):                                  # bisection along the plane from the centre outward
        mid = (lo + hi) / 2
        point = _on_plane(center, plane_point, down, direction * mid)
        inside = np.sum(((point - np.asarray(center)) / radii) ** 2) < 1.0
        lo, hi = (mid, hi) if inside else (lo, mid)
    return _on_plane(center, plane_point, down, direction * lo)


def _on_plane(center, plane_point, down, offset):
    point = np.asarray(center, dtype=np.float64) + offset
    return point - down * ((point - plane_point) @ down)


HEADPHONE_BAND = ((0.0, -0.04, -0.04), 0.70, 0.035)    # head-local centre of the band's arc, its radius, its thickness
HEADPHONE_CUP = ((0.60, 0.06, -0.04), (0.08, 0.19, 0.16))   # right cup centre and radii, head-local


def headphones(ctx):
    """Over-ear headphones worn on the head: a band over the crown and a cup over each ear."""
    s = ctx.skeleton
    center, radius, thickness = HEADPHONE_BAND
    arc = [s.point("head", (center[0] + radius * np.sin(a), center[1] - radius * np.cos(a) * 0.95, center[2]))
           for a in np.linspace(-1.2, 1.2, 13)]
    solids = [sweep(arc, [thickness] * len(arc), ctx.material("gear"), group="gear", name="headphones", gloss=0.3)]
    cup_center, cup_radii = HEADPHONE_CUP
    for _, sign in SIDES:
        x, y, z = cup_center
        solids.append(ellipsoid(s.point("head", (sign * x, y, z)), s.rotation["head"], cup_radii, ctx.material("gear"),
                                group="gear", name="headphones", gloss=0.3))
        hinge = [s.point("head", (sign * (x - 0.02), y - cup_radii[1] * 0.7, z)), arc[0 if sign < 0 else -1]]
        solids.append(sweep(hinge, [thickness * 0.8] * 2, ctx.material("gear"), group="gear", name="headphones"))
    return Piece(solids)


GARMENTS = {
    "crop_top": crop_top, "tank_top": tank_top, "t_shirt": t_shirt, "hoodie": hoodie, "dress_shirt": dress_shirt,
    "suit_jacket": suit_jacket, "tie": tie, "trousers": trousers, "jeans": jeans, "hot_pants": hot_pants,
    "swim_trunks": swim_trunks, "skirt": skirt_flared, "sundress": sundress, "bikini": bikini,
    "sneakers": sneakers, "flats": flats, "dress_shoes": _shoes_fitted,
    "puffer": puffer, "beanie": beanie, "headphones": headphones,
}


@dataclass(frozen=True)
class Outfit3D:
    """garments are built in order and GARMENT_LAYERS decides which sits over which; colors maps a slot
    ('top', 'bottom', 'outer', 'trim', 'accent', 'shoes', 'sole', 'outer_line') to a Material."""

    garments: tuple
    colors: dict


WHITE = fabric("#F7F6F2", "#B4B6C8", "#5A5C70", "#FFFFFF")
DENIM = fabric("#4A6FA5", "#2A3F66", "#18243C", "#7FA0CC")
BLACK = fabric("#34343C", "#16161C", "#08080C", "#5C5C68")
NAVY = fabric("#2E3A5C", "#161C30", "#0A0E1A", "#4E5E88")
GREY = fabric("#9A9CA6", "#5E606C", "#33343C", "#C8CAD2")
RED = fabric("#D84A50", "#8A1E3A", "#4A0E1E", "#FF8A80")
CORAL = fabric("#F07A6A", "#A8404A", "#5A1E26", "#FFB0A0")
CREAM = fabric("#F2E6D0", "#BFA894", "#6A5848", "#FFF8EA")
OLIVE = fabric("#7A8450", "#4A5030", "#283018", "#A8B078")
SKY = fabric("#8EC8E8", "#4E88B0", "#1E4466", "#C8E8FA")
LAVENDER = fabric("#B8A8E0", "#7464A8", "#3A3060", "#E0D8FA")
TAN = fabric("#C8A27A", "#8A6648", "#4A3424", "#E8C8A0")

OUTFITS = {
    "crop_top_hot_pants": Outfit3D(("crop_top", "hot_pants", "sneakers"),
                                   {"top": WHITE, "bottom": DENIM, "shoes": WHITE, "sole": GREY}),
    "hoodie_jeans": Outfit3D(("jeans", "hoodie", "sneakers"),
                             {"top": LAVENDER, "trim": fabric("#A090CC", "#605090", "#302850"), "bottom": DENIM,
                              "shoes": WHITE, "sole": GREY}),
    "hoodie_shorts": Outfit3D(("hot_pants", "hoodie", "sneakers"),
                              {"top": GREY, "trim": fabric("#7E808A", "#4A4C56", "#26272E"), "bottom": BLACK,
                               "shoes": WHITE, "sole": GREY}),
    "tank_top_jeans": Outfit3D(("jeans", "tank_top", "sneakers"),
                               {"top": CORAL, "bottom": DENIM, "shoes": WHITE, "sole": GREY}),
    "sundress": Outfit3D(("sundress", "flats"), {"top": CREAM, "accent": RED, "shoes": RED}),
    "bikini": Outfit3D(("bikini",), {"top": RED}),
    "t_shirt_jeans": Outfit3D(("jeans", "t_shirt", "sneakers"),
                              {"top": WHITE, "bottom": DENIM, "shoes": WHITE, "sole": GREY}),
    "shirt_trousers": Outfit3D(("trousers", "dress_shirt", "dress_shoes"),
                               {"top": SKY, "trim": WHITE, "bottom": TAN, "shoes": fabric("#5A3A28", "#2A1810",
                                                                                         "#140A06", "#8A6048")}),
    "swim_trunks": Outfit3D(("swim_trunks",), {"bottom": fabric("#2E8FB8", "#145878", "#08283A", "#6EC4E4")}),
    "winter_beanie": Outfit3D(("jeans", "t_shirt", "puffer", "beanie", "sneakers"),
                              {"top": GREY, "bottom": fabric("#3A4250", "#1E2430", "#0E1218"),
                               "outer": fabric("#2E3A34", "#18201C", "#0A0E0C", "#4E5E56"),
                               "outer_line": fabric("#1A221E", "#0E1210", "#060807"), "trim": BLACK,
                               "hat": fabric("#5A2E2E", "#341818", "#180A0A"), "shoes": BLACK, "sole": GREY}),
    "winter_headphones": Outfit3D(("jeans", "t_shirt", "puffer", "headphones", "sneakers"),
                                  {"top": WHITE, "bottom": BLACK,
                                   "outer": fabric("#B9B2A4", "#7C7466", "#3E3A32", "#DCD6CA"),
                                   "outer_line": fabric("#8A8274", "#5C5648", "#2E2A22"), "trim": GREY,
                                   "gear": BLACK, "shoes": WHITE, "sole": GREY}),
    "hoodie_beanie": Outfit3D(("jeans", "hoodie", "beanie", "sneakers"),
                              {"top": fabric("#3C4048", "#1E2026", "#0C0D10", "#5E626C"),
                               "trim": fabric("#2E3138", "#16181C", "#08090B"), "bottom": DENIM,
                               "hat": fabric("#2E3440", "#161A22", "#080A0E"), "shoes": WHITE, "sole": GREY}),
    "suit": Outfit3D(("trousers", "dress_shirt", "tie", "suit_jacket", "dress_shoes"),
                     {"top": WHITE, "trim": WHITE, "bottom": NAVY, "outer": NAVY, "outer_line": NAVY, "accent": RED,
                      "shoes": BLACK}),
}


def build(outfit, skeleton, body_build):
    """Solids and decals of an outfit on a posed body."""
    ctx = Context(skeleton, body_build, outfit.colors)
    solids, decals = [], []
    for name in outfit.garments:
        ctx.layer = GARMENT_LAYERS.get(name, 0)
        piece = GARMENTS[name](ctx)
        solids += piece.solids
        decals += piece.decals
    return solids, decals, ctx
