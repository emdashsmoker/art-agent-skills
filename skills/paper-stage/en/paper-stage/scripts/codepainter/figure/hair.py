"""Hair: one mass behind the head, a cap over the skull, and pointed locks in front.

Drawn hair is a design of clumps. Each lock is a pointed
shape shaded as its own ribbon; fine strands and a streaked highlight are laid
over the clumps to suggest the fibres.
"""
from dataclasses import dataclass, field

import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..color import adjust, light_of, mix, rgb, shadow_of
from ..styles import line_color, shade_form

HAIR_VOLUME = 0.058          # how far the hair stands off the skull at the top
HAT_PRESSED = 0.5            # share of HAIR_VOLUME left under a hat, so no tuft stands out above it
HAIR_LIFT = 0.03             # front locks float slightly in front of the forehead
HIGHLIGHT_STREAKS = 64
STRAND_SPACING = 0.020       # head units between strands at style.strands = 1
BACK_STRANDS = 46            # strands across the back mass at style.strands = 1
GUIDE_POINTS = 60
FLYAWAYS = 9                 # loose strands outside the silhouette at style.strands = 1
PROFILE_NEAR_WIDTH = 0.53   # back of the skull plus hair, seen in profile
SHORT_PROFILE_NEAR_WIDTH = 0.51   # cropped hair lies close to the skull
FAR_LOCK_CLEARS = 0.45      # profile amount by which the far side lock has moved behind the ear
FAR_LOCK_BEHIND = 0.04      # profile amount past which the far side lock is drawn behind the head
FLYAWAY_BACK_ONLY = 0.20    # profile amount past which loose strands leave the face side alone
FAR_BANG_X = 0.08           # face-plane x of a bang tip past which the bang lies on the far side of the forehead
FAR_BANG_BEHIND = 0.62      # profile amount past which far-side bangs have gone round behind the forehead
PROFILE_BANG_ROOTS = ((0.30, 0.16), (0.10, 0.04))   # every bang's root line in full profile: (front, back) of the skull top
# Profile hairline: over the ear, close behind it, down to the nape, then out over the base of the skull.
EAR_HAIRLINE = [(0.0, 0.45), (-0.16, 0.475), (-0.175, 0.64), (-0.28, 0.83), (-0.44, 0.75)]
HEM_LENGTH = {"long": (0.16, 0.36), "bob": (0.04, 0.12), "short": (0.03, 0.09), "tied": (0.02, 0.05)}   # pointed ends below the mass
# Every hairstyle builds on a base cut (the mass behind the head, its side hair and hem) and adds its own parts.
STYLE_BASE = {"long": "long", "bob": "bob", "short": "short", "wavy": "long", "ponytail": "tied", "bun": "tied",
              "two_block": "short", "slick": "short"}
STYLE_VOLUME = {"short": 1.6, "wavy": 1.15, "ponytail": 0.5, "bun": 0.5, "two_block": 1.45, "slick": 1.0}   # x HAIR_VOLUME
TIED_TIGHTEN = 0.035        # hair pulled back into a tail or bun lies this much closer to the skull at the sides
TIED_PROFILE_NEAR_WIDTH = 0.50
WAVE_AMPLITUDE, WAVE_COUNT, WAVE_FROM = 0.045, 2.5, 0.55   # wavy hair: sideways swing, waves down the length, start height
WAVE_POINTS = 18            # points each side of a wavy mass is resampled to before the waves are laid on
TAIL = {"root": (0.46, 0.30), "tip": (0.66, 1.40), "half": 0.10, "belly": 0.55, "back_root": (0.0, 0.36), "back_tip": (0.0, 1.45)}
BUN = {"center": (0.47, -0.07, 0.10), "radius": (0.16, 0.15), "back_center": (0.0, 0.10), "back_radius": (0.17, 0.15)}
TIE_SIZE = (0.075, 0.03)    # across and along a hair tie, head units
BLOCK_LINE = 0.30           # two-block cut: head y below which the sides and back are clipped short
BLOCK_TIPS = (0.09, 0.06)   # the longer top hangs over the cut in pointed tips: (spacing, length) in head units
BUZZ_SKIN = 0.30            # share of skin showing through clipped hair
BUZZ_SHADOW = 0.035         # head units of shade the overhanging top throws on the clipped hair
HANG_START = 0.95           # head units below the crown where long hair leaves the head and hangs free
HANG_BLEND = 0.60           # head units over which hanging hair turns fully toward the ground
GRAVITY_SHARE = 0.35        # share of a lying head's tilt that hanging hair takes back to droop toward the ground
LYING_LENGTH = 0.55         # share of its hanging length that hair keeps once it rests on the ground and gathers
GRAVITY_TILT = (30.0, 70.0)  # head tilt in degrees over which gravity takes over; an upright head is left alone


@dataclass
class HairPlan:
    back: np.ndarray                                   # closed curve behind the head (pixels)
    back_guides: tuple                                 # (far path, near path) crown -> hem, for strand flow
    cap: np.ndarray                                    # closed curve over the skull top (pixels)
    locks: list = field(default_factory=list)          # front locks, back to front (closed pixel curves)
    whorl: np.ndarray = None                           # point the hair flows away from (pixels)
    behind: list = field(default_factory=list)         # locks drawn with the back mass, hidden by the head
    knots: list = field(default_factory=list)          # tail or bun, drawn behind the back mass (pixels)
    ties: list = field(default_factory=list)           # bands round the knots
    knots_back: list = field(default_factory=list)     # the same knots for a figure seen from behind, drawn over the mass
    ties_back: list = field(default_factory=list)
    buzz: np.ndarray = None                            # clipped hair under a two-block cut (closed pixel curve)
    block: np.ndarray = None                           # region above the cut line (closed pixel curve)
    flow: list = field(default_factory=list)           # strand paths combed back from an open hairline


def base_cut(spec):
    """The base cut a hairstyle builds on: long, bob, short or tied."""
    if spec.hair_style not in STYLE_BASE:
        raise ValueError(f"unknown hair_style: {spec.hair_style}")
    return STYLE_BASE[spec.hair_style]


def silhouette_widths(frame, spec):
    """Half-widths of the hair silhouette on the far and near side (the near side shows more skull)."""
    far, near = geo.lerp(0.445, 0.43, frame.turn), geo.lerp(0.445, 0.475, frame.turn)
    base = base_cut(spec)
    profile_near = {"short": SHORT_PROFILE_NEAR_WIDTH, "tied": TIED_PROFILE_NEAR_WIDTH}.get(base, PROFILE_NEAR_WIDTH)
    if base == "tied":
        far, near = far - TIED_TIGHTEN, near - TIED_TIGHTEN
    return far, geo.lerp(near, profile_near, frame.profile)


def _blend(points, profile_points, amount):
    """Point lists keyed for a three-quarter head, moved toward their profile keys."""
    if amount <= 0:
        return points
    return [tuple(geo.lerp(np.array(a), np.array(b), amount)) for a, b in zip(points, profile_points)]


def _back_sides(frame, spec):
    """Far side (crown -> hem), hem, near side (hem -> crown) of the back mass, in head units."""
    far, near = silhouette_widths(frame, spec)
    v = -_volume(spec)
    top_far = [(-0.02, v), (0.22, v + 0.033), (0.375, 0.11), (far, 0.33)]
    top_near = [(-near, 0.33), (-0.40, 0.11), (-0.25, v + 0.033)]
    # In profile the face side of the mass stops at the hairline and falls behind the ear.
    side_top_far = [(-0.02, v), (0.22, v + 0.033), (0.34, 0.12), (0.29, 0.30)]
    side_top_near = [(-near, 0.33), (-0.47, 0.11), (-0.28, v + 0.033)]
    base = base_cut(spec)
    if base == "long":
        length = 2.05
        far_side = top_far + [(far + 0.01, 0.62), (far - 0.015, 0.95), (far + 0.03, 1.30), (far + 0.07, 1.65), (far + 0.02, length)]
        hem = [(0.12, length + 0.05)]
        near_side = [(-near + 0.16, length + 0.02), (-near - 0.08, 1.65), (-near - 0.04, 1.28),
                     (-near + 0.005, 0.94), (-near - 0.01, 0.62)] + top_near
        side_far = side_top_far + [(0.10, 0.55), (-0.05, 0.85), (-0.04, 1.25), (0.00, 1.62), (0.0, length)]
        side_hem = [(-0.22, length + 0.05)]
        side_near = [(-near + 0.14, length + 0.02), (-near - 0.10, 1.65), (-near - 0.08, 1.28),
                     (-near - 0.04, 0.94), (-near - 0.02, 0.62)] + side_top_near
    elif base == "bob":                # ends tuck in under the jaw
        length = 1.04
        far_side = top_far + [(far + 0.035, 0.62), (far + 0.04, 0.86), (far - 0.04, length)]
        hem = [(0.0, length - 0.06)]
        near_side = [(-near + 0.05, length + 0.03), (-near - 0.05, 0.86), (-near - 0.035, 0.62)] + top_near
        side_far = side_top_far + [(0.12, 0.55), (-0.02, 0.82), (0.0, length)]
        side_hem = [(-0.24, length - 0.04)]
        side_near = [(-near + 0.12, length + 0.02), (-near - 0.06, 0.86), (-near - 0.03, 0.62)] + side_top_near
    elif base == "short":              # cropped at the nape, close over the ears
        length = 0.78
        far_side = top_far + [(far - 0.03, 0.50), (far - 0.11, length - 0.04)]
        hem = [(0.0, length)]
        near_side = [(-near + 0.12, length - 0.04), (-near + 0.03, 0.50)] + top_near
        side_far = side_top_far + [(0.10, 0.48), (-0.10, 0.72)]
        side_hem = [(-0.22, length + 0.02)]                 # the crop ends on the nape, tucked into the neck
        side_near = [(-0.30, length + 0.05), (-near + 0.07, 0.74)] + side_top_near
    else:                              # tied: pulled back tight and gathered at the back (the knot is drawn on its own)
        length = 0.80
        far_side = top_far + [(far - 0.02, 0.50), (far - 0.10, length - 0.06)]
        hem = [(0.0, length)]
        near_side = [(-near + 0.10, length - 0.06), (-near + 0.02, 0.50)] + top_near
        side_far = side_top_far + [(0.10, 0.48), (-0.10, 0.72)]
        side_hem = [(-0.22, length)]
        side_near = [(-0.30, length + 0.03), (-near + 0.07, 0.74)] + side_top_near
    sides = (_blend(far_side, side_far, frame.profile), _blend(hem, side_hem, frame.profile),
             _blend(near_side, side_near, frame.profile))
    if spec.hair_style == "wavy":
        sides = (_wave(sides[0], 1.0), sides[1], _wave(sides[2][::-1], -1.0)[::-1])
    return sides


def _wave(points, outward):
    """A side of the mass (crown first) resampled and swung in and out below WAVE_FROM. outward: +1 far, -1 near side."""
    dense = geo.resample(np.array(points, dtype=np.float64), WAVE_POINTS)
    y = dense[:, 1]
    span = max(y.max() - WAVE_FROM, 1e-6)
    swing = np.sin(2.0 * np.pi * WAVE_COUNT * (y - WAVE_FROM) / span) * sh.smoothstep(WAVE_FROM, WAVE_FROM + 0.25, y)
    dense[:, 0] += outward * WAVE_AMPLITUDE * swing
    return [tuple(point) for point in dense]


def _wave_lock(curve, root, tip, waves=1.5, amplitude=0.30):
    """A lock (closed pixel curve) swung sideways along its length, as wavy hair falls. amplitude: share of the lock width."""
    axis = tip - root
    length = max(np.linalg.norm(axis), 1e-9)
    along = axis / length
    across = np.array([-along[1], along[0]])
    position = np.clip((curve - root) @ along / length, 0.0, 1.0)
    width = np.abs((curve - root) @ across).max()
    swing = np.sin(2.0 * np.pi * waves * position) * position * amplitude * width * 2.0
    return curve + across * swing[:, None]


def _hang(frame, points):
    """Head-local points; below HANG_START they swing back toward the ground once the head lies down.

    The head rig tilts everything with the head, so on a lying figure long hair would run along the body.
    """
    pts = np.array(points, dtype=np.float64)
    lying = float(sh.smoothstep(*np.radians(GRAVITY_TILT), abs(frame.tilt)))
    if lying <= 0:
        return points
    pivot = np.array([0.0, HANG_START])
    below = np.maximum(pts[:, 1] - HANG_START, 0.0)
    pts[:, 1] -= below * (1.0 - LYING_LENGTH) * lying          # resting on the ground, it no longer hangs at full length
    # place() mirrors a left-facing head before it tilts, so the turn back flips with the side
    angle = -frame.tilt * frame.side * GRAVITY_SHARE * lying * sh.smoothstep(HANG_START, HANG_START + HANG_BLEND, pts[:, 1])
    offset = pts - pivot
    turned = np.stack([offset[:, 0] * np.cos(angle) - offset[:, 1] * np.sin(angle),
                       offset[:, 0] * np.sin(angle) + offset[:, 1] * np.cos(angle)], axis=1)
    return [tuple(point) for point in turned + pivot]


def _volume(spec):
    """Short hair stands up off the crown; long hair lies flatter; tied hair is pulled tight; a hat presses it flat."""
    if getattr(spec, "hat", None):
        return HAIR_VOLUME * HAT_PRESSED
    return HAIR_VOLUME * STYLE_VOLUME.get(spec.hair_style, 1.0)


def _bang_defs(spec):
    """Bang locks on the face plane: (root_a, root_b, tip, bend, belly). Far side is +x."""
    if spec.bangs == "swept":
        part = np.array([-0.10, 0.0])                      # side parting on the near half of the crown
        return part, [
            (part + (0.03, 0.0), (0.17, 0.0), (0.262, 0.490), -0.13, 0.20),      # main sweep to the far temple
            (part + (-0.10, 0.02), (-0.02, 0.0), (-0.200, 0.455), 0.12, 0.18),  # near bang
            (part + (0.0, 0.0), (0.11, 0.0), (0.150, 0.462), -0.14, 0.18),      # second sweep over the far brow
            (part + (-0.03, 0.0), (0.05, 0.0), (0.030, 0.405), -0.10, 0.16),    # short centre bang
        ]
    if spec.bangs == "curtain":                            # both sides fall away from a centre parting
        part = np.array([0.0, 0.0])
        return part, [
            (part + (0.0, -0.01), (0.27, 0.13), (0.262, 0.54), -0.10, 0.22),     # wide roots hide the hairline
            (part + (0.0, -0.01), (-0.27, 0.13), (-0.262, 0.54), 0.10, 0.22),
            (part + (0.01, 0.0), (0.13, 0.02), (0.205, 0.46), -0.16, 0.18),
            (part + (-0.01, 0.0), (-0.13, 0.02), (-0.205, 0.46), 0.16, 0.18),
        ]
    if spec.bangs == "textured":                           # short pointed fringe pushed to one side, forehead open
        part = np.array([-0.12, 0.0])
        return part, [
            (part + (0.05, -0.02), (0.26, 0.02), (0.330, 0.300), -0.22, 0.24),    # long sweep to the far temple
            (part + (0.0, -0.02), (0.16, 0.0), (0.190, 0.285), -0.24, 0.22),
            (part + (-0.02, 0.0), (0.08, 0.0), (0.060, 0.265), -0.20, 0.18),
            (part + (-0.11, 0.03), (-0.03, 0.0), (-0.205, 0.255), 0.18, 0.18),    # short flick on the near side
        ]
    if spec.bangs == "none":                               # forehead open, the hair combed back from the hairline
        return np.array([-0.10, 0.0]), []
    raise ValueError(f"unknown bangs: {spec.bangs}")


def plan_hair(frame, spec):
    far_side, hem, near_side = (_hang(frame, part) for part in _back_sides(frame, spec))
    corners = (len(far_side) - 1, len(far_side) + len(hem))
    back = geo.smooth(frame.place(far_side + hem + near_side), closed=True, corners=corners)
    far_guide = geo.resample(geo.smooth(frame.place(far_side)), GUIDE_POINTS)
    near_guide = geo.resample(geo.smooth(frame.place(far_side[:1] + near_side[::-1])), GUIDE_POINTS)

    far, near = silhouette_widths(frame, spec)
    v = -_volume(spec)
    # Cap: skull top down to the hairline. The hairline rides on the face so it turns with it.
    dome_far = frame.place(_blend([(-0.02, v), (0.22, v + 0.033), (0.375, 0.11), (far - 0.005, 0.30), (far - 0.03, 0.46)],
                                  [(-0.02, v), (0.20, v + 0.033), (0.33, 0.12), (0.34, 0.20), (0.33, 0.24)], frame.profile))
    hairline = frame.face([(0.27, 0.31), (0.15, 0.215), (0.0, 0.195), (-0.15, 0.215), (-0.27, 0.31)])
    dome_near = frame.place(_blend([(-near + 0.05, 0.55), (-near, 0.33), (-0.40, 0.11), (-0.25, v + 0.033)],
                                   [(-near + 0.03, 0.55), (-near, 0.33), (-0.47, 0.11), (-0.28, v + 0.033)], frame.profile))
    if frame.profile > 0:
        # Turned away from the viewer, the hairline wraps round the ear and down to the nape.
        start = (-near + 0.03, 0.55)
        around_ear = frame.place(_blend([start] * len(EAR_HAIRLINE), EAR_HAIRLINE, frame.profile))
        dome_near = np.vstack([around_ear, dome_near])
    cap = geo.smooth(np.vstack([dome_far, hairline, dome_near]), closed=True)

    # Side hair hugs the silhouette, so it is placed in head units.
    base = base_cut(spec)
    if spec.hair_style == "two_block":   # the sides are clipped: no locks, the skin shows through
        side_defs, side_profile = [], []
    elif base == "tied":                 # thin wisps left loose at the temples
        side_defs = [
            ((far - 0.06, 0.25), (far - 0.015, 0.31), (far - 0.035, 0.68), -0.04, 0.05),
            ((-near + 0.06, 0.25), (-near + 0.015, 0.31), (-near + 0.035, 0.68), 0.04, 0.05),
        ]
        side_profile = [((-0.18, 0.27), (-0.10, 0.30), (-0.14, 0.60)), ((0.0, 0.30), (0.06, 0.33), (0.05, 0.66))]
    elif base == "short":                # only short sideburns; the ears stay in view
        side_defs = [
            ((far - 0.10, 0.22), (far - 0.004, 0.36), (far - 0.05, 0.56), -0.03, 0.12),
            ((-near + 0.22, 0.16), (-near + 0.03, 0.30), (-near + 0.11, 0.54), 0.05, 0.14),
        ]
        # in profile: a sideburn in front of the ear and a tuft down the back of the skull to the nape
        side_profile = [((-0.06, 0.24), (0.08, 0.34), (0.00, 0.54)), ((-0.30, 0.16), (-0.50, 0.30), (-0.34, 0.83))]
    else:
        side_tip = 1.12 if base == "long" else 0.92
        side_defs = [
            ((far - 0.12, 0.24), (far - 0.004, 0.40), (far - 0.055, side_tip - 0.14), -0.03, 0.12),     # far side lock
            ((-near + 0.25, 0.16), (-near + 0.035, 0.30), (-near + 0.205, 0.80), 0.06, 0.15),          # near temple mass
            ((-near + 0.20, 0.30), (-near + 0.05, 0.42), (-near + 0.15, side_tip), 0.04, 0.12),       # near side lock
        ]
        # in profile all three fall behind the ear; the near side lock hangs over the nape
        side_profile = [((-0.18, 0.27), (-0.03, 0.38), (-0.15, side_tip - 0.14)),
                        ((-0.30, 0.17), (-0.50, 0.32), (-0.40, 0.80)),
                        ((-0.17, 0.47), (-0.52, 0.36), (-0.30, side_tip))]
    locks, behind = [], []
    for index, ((root_a, root_b, tip, bend, belly), keys) in enumerate(zip(side_defs, side_profile)):
        far_lock = index == 0
        # Past the three-quarter key the far lock goes round behind the face: it is drawn with the
        # back mass, so the head hides it and only what hangs past the jaw shows.
        amount = sh.smoothstep(0.0, FAR_LOCK_CLEARS, frame.profile) if far_lock else frame.profile
        root_a, root_b, tip = _hang(frame, _blend([root_a, root_b, tip], keys, float(amount)))
        a, b, t = frame.place([root_a, root_b, tip])
        curve = geo.lock(a, b, t, bend * frame.side, belly)    # mirroring the head flips the bend
        if spec.hair_style == "wavy":
            curve = _wave_lock(curve, (a + b) / 2, t)
        (behind if far_lock and frame.profile > FAR_LOCK_BEHIND else locks).append(curve)
    part, bang_defs = _bang_defs(spec)
    for root_a, root_b, tip, bend, belly in bang_defs:
        a, b, t = frame.face([root_a, root_b, tip], lift=HAIR_LIFT)
        if frame.profile > 0:
            # Seen from the side both roots fall on the skull top and the lock would thin to a line;
            # the root nearer the parting goes to the front of the skull, the other further back.
            root_front, root_back = frame.place(PROFILE_BANG_ROOTS)
            a_key, b_key = (root_front, root_back) if abs(root_a[0]) <= abs(root_b[0]) else (root_back, root_front)
            a, b = geo.lerp(a, a_key, frame.profile), geo.lerp(b, b_key, frame.profile)
        far_bang = tip[0] > FAR_BANG_X and frame.profile > FAR_BANG_BEHIND
        (behind if far_bang else locks).append(geo.lock(a, b, t, bend * frame.side, belly))
    plan = HairPlan(back=back, back_guides=(far_guide, near_guide), cap=cap, locks=locks,
                    whorl=frame.face([part])[0], behind=behind)
    _plan_knots(frame, spec, plan)
    if spec.hair_style == "two_block":
        plan.buzz = cap
        spacing, length = BLOCK_TIPS
        across = np.arange(1.5, -1.5 - 1e-9, -spacing / 2)
        edge = [(x, BLOCK_LINE + (length if index % 2 else 0.0)) for index, x in enumerate(across)]
        plan.block = frame.place([(-1.5, -0.6), (1.5, -0.6)] + edge)
    if not bang_defs:
        plan.flow = _flow_paths(frame, v)
    return plan


def _plan_knots(frame, spec, plan):
    """Tail or bun of tied hair, for the turned head and for a figure seen from behind."""
    if spec.hair_style not in ("ponytail", "bun"):
        return
    turn = np.sin(frame.theta)                 # 0 front .. 1 side: the knot comes round from behind the head
    if spec.hair_style == "ponytail":
        half = TAIL["half"]
        across = np.array([np.cos(turn * np.pi / 2), -np.sin(turn * np.pi / 2)]) * half
        root = np.array([-TAIL["root"][0] * turn, TAIL["root"][1] + 0.02 * turn])
        tip = np.array([-TAIL["tip"][0] * turn, TAIL["tip"][1]])
        a, b, t = frame.place(_hang(frame, [tuple(root + across), tuple(root - across), tuple(tip)]))
        plan.knots.append(geo.lock(a, b, t, 0.10 * turn * frame.side, TAIL["belly"]))
        tie_size = (geo.lerp(TIE_SIZE[0], TIE_SIZE[1], turn), geo.lerp(TIE_SIZE[1], TIE_SIZE[0], turn))
        plan.ties.append(geo.ellipse(frame.place([tuple(root)])[0], frame.px(tie_size[0]), frame.px(tie_size[1])))
        back_root, back_tip = np.array(TAIL["back_root"]), np.array(TAIL["back_tip"])
        a, b, t = frame.place(_hang(frame, [tuple(back_root + (half * 1.2, 0.0)), tuple(back_root - (half * 1.2, 0.0)),
                                            tuple(back_tip)]))
        plan.knots_back.append(geo.lock(a, b, t, 0.0, TAIL["belly"]))
        plan.ties_back.append(geo.ellipse(frame.place([tuple(back_root)])[0], frame.px(TIE_SIZE[0] * 1.2), frame.px(TIE_SIZE[1])))
        return
    x, y_front, y_side = BUN["center"]
    center = frame.place([(-x * turn, geo.lerp(y_front, y_side, turn))])[0]
    plan.knots.append(geo.ellipse(center, frame.px(BUN["radius"][0]), frame.px(BUN["radius"][1])))
    plan.knots_back.append(geo.ellipse(frame.place([BUN["back_center"]])[0], frame.px(BUN["back_radius"][0]),
                                       frame.px(BUN["back_radius"][1])))


def _flow_paths(frame, top):
    """Strand paths combed from an open hairline back over the skull (no bangs to carry them)."""
    turn = np.sin(frame.theta)
    paths = []
    for x in np.linspace(-0.26, 0.26, 11):
        y = 0.195 + 0.45 * x ** 2 * (1.0 + 0.3 * abs(x))         # follows the hairline round the temples
        start = frame.face([(x, y)])[0]
        end = frame.place([(x * 0.55 - 0.30 * turn, top * 0.3)])[0]
        mid = (start + end) / 2 + (frame.place([(0.0, -0.04)])[0] - frame.place([(0.0, 0.0)])[0])
        paths.append(geo.smooth([start, mid, end]))
    return paths


# ---- fine detail ----------------------------------------------------------------
def _strand_colors(base, style):
    dark = adjust(shadow_of(base, style.shadow_tint, 1.0), value=0.72)
    light = light_of(base, (1.0, 0.88, 0.80), 0.38)
    return dark, light


def _draw_strands(painting, paths, frame, style, base, clip, rng, lit=None):
    """Thin flow lines, some darker and some lighter than the mass, tapered at both ends."""
    dark, light = _strand_colors(base, style)
    for path in paths:
        start, end = rng.uniform(0.04, 0.45), rng.uniform(0.62, 0.98)
        lighter = rng.random() < 0.4
        painting.stroke(geo.subpath(path, start, end), frame.px(rng.uniform(0.0022, 0.0048)),
                        light if lighter else dark, taper=(0.4, 0.45),
                        opacity=rng.uniform(0.22, 0.42) if lighter else rng.uniform(0.30, 0.55),
                        layer="color", clip=clip if lit is None or not lighter else clip * lit)


def _lock_strand_paths(curve, whorl, frame, style, rng):
    """Flow lines that leave the whorl, cross the cap and run down one lock."""
    tip = len(curve) // 2
    edge_a, edge_b = curve[:tip + 1], curve[tip:][::-1]
    root_width = np.linalg.norm(edge_a[0] - edge_b[0])
    count = int(np.clip(root_width / frame.px(STRAND_SPACING) * style.strands, 1, 16))
    paths = []
    for blend in (np.arange(count) + rng.uniform(0.2, 0.8, count)) / count:
        inner = geo.lerp(edge_a, edge_b, blend)
        jitter = rng.normal(0.0, frame.px(0.01), 2)
        paths.append(geo.smooth(np.vstack([whorl + jitter, inner[::5], inner[-1:]])))
    return paths


def _highlight_band(painting, frame, spec, whorl):
    """Light band across the crown built from fine streaks that follow the hair flow.

    A solid band reads as a headband; streaks pointing away from the whorl read as glossy hair.
    """
    rng = np.random.default_rng(spec.seed + 1)
    angles = np.linspace(np.radians(208), np.radians(332), HIGHLIGHT_STREAKS)
    fade = np.sin(np.linspace(0.0, np.pi, HIGHLIGHT_STREAKS)) ** 0.6       # the band thins out toward its ends
    ring = np.array([0.0, 0.40]) + np.stack([np.cos(angles) * 1.14, np.sin(angles)], axis=1) * 0.292
    band = np.zeros(painting.shape, dtype=np.float32)
    for center, strength in zip(frame.place(ring), fade):
        if rng.random() > 0.88:                                        # gaps keep the band from looking stamped
            continue
        flow = center - whorl
        flow = flow / max(np.linalg.norm(flow), 1e-9)
        length = frame.px(rng.uniform(0.05, 0.11)) * strength
        offset = frame.px(rng.uniform(-0.008, 0.008))
        streak = geo.needle(center + flow * (offset - length / 2), center + flow * (offset + length / 2),
                            frame.px(rng.uniform(0.012, 0.020)))
        band = np.maximum(band, painting.mask(streak))
    return band


def draw_flyaways(painting, frame, spec, style, plan):
    """A few loose strands outside the silhouette; they break the helmet-like outline."""
    rng = np.random.default_rng(spec.seed + 3)
    center = frame.place([(0.0, 0.5)])[0]
    color = rgb(spec.hair)
    # Turned far, the face-side guide runs over the cheek; loose strands only fly off the back of the head.
    guides = plan.back_guides if frame.profile < FLYAWAY_BACK_ONLY else plan.back_guides[1:]
    for index in range(int(FLYAWAYS * style.strands)):
        guide = guides[index % len(guides)]
        start = rng.uniform(0.18, 0.36)          # stay beside the head; lower down they read as scratches on clothes
        path = geo.subpath(guide, start, start + rng.uniform(0.12, 0.20))
        normal = geo.normals(path)
        if normal[0] @ (path[0] - center) < 0:            # make the normal point away from the head
            normal = -normal
        drift = np.linspace(0.0, 1.0, len(path)) ** 1.6 * frame.px(rng.uniform(0.012, 0.04))
        painting.stroke(path + normal * drift[:, None], frame.px(rng.uniform(0.0018, 0.003)), color,
                        taper=(0.2, 0.7), opacity=0.8, layer="color")


# ---- drawing --------------------------------------------------------------------
HEM_LOCKS = 8


def _hem_locks(painting, frame, spec, plan):
    """Pointed ends along the bottom of the hair; a straight-cut hem reads as a cape."""
    rng = np.random.default_rng(spec.seed + 4)
    far_end, near_end = plan.back_guides[0][-1], plan.back_guides[1][-1]
    ends = np.zeros(painting.shape, dtype=np.float32)
    edges = np.linspace(0.0, 1.0, HEM_LOCKS + 1)
    for start, stop in zip(edges[:-1], edges[1:]):
        a, b = geo.lerp(far_end, near_end, start - 0.03), geo.lerp(far_end, near_end, stop + 0.03)
        a, b = a - [0.0, frame.px(0.10)], b - [0.0, frame.px(0.10)]              # roots sit inside the mass
        low, high = HEM_LENGTH[base_cut(spec)]
        tip = (a + b) / 2 + [frame.px(rng.uniform(-0.03, 0.03)), frame.px(0.10 + rng.uniform(low, high))]
        ends = np.maximum(ends, painting.mask(geo.lock(a, b, tip, bend=rng.uniform(-0.08, 0.08), belly=0.25)))
    return ends


def buzz_color(spec):
    """Clipped hair: the hair colour with the skin showing through."""
    return mix(spec.hair, spec.skin, BUZZ_SKIN)


def _draw_knot(painting, frame, spec, style, light, curve, base, tie=None):
    """A tail or bun drawn as its own clump of hair, with its band. Returns its mask."""
    mask = painting.mask(curve)
    painting.part(mask, base)
    shade_form(painting, mask, base, style, light, bevel=frame.px(0.08))
    if style.strands > 0:
        rng = np.random.default_rng(spec.seed + 5)
        if len(curve) % 2:               # a lock (tail): strands run from the band to the tip
            tip = len(curve) // 2
            edges = (curve[:tip + 1], curve[tip:][::-1])
            paths = [geo.lerp(edges[0], edges[1], blend) for blend in rng.uniform(0.1, 0.9, 10)]
        else:                            # a bun: strands wind round it
            center = curve.mean(axis=0)
            paths = [geo.subpath(center + (curve - center) * scale, start, start + 0.55)
                     for scale, start in zip((0.85, 0.62, 0.40), rng.uniform(0.0, 0.45, 3))]
        _draw_strands(painting, paths, frame, style, base, mask, rng)
    if style.line_width > 0:
        painting.outline_mask(mask, frame.px(0.0060) * style.line_width, line_color(style, spec.hair))
    if tie is not None:
        band = painting.mask(tie)
        color = shadow_of(spec.cloth, style.shadow_tint, 0.3)
        painting.part(band, color)
        if style.line_width > 0:
            painting.outline_mask(band, frame.px(0.0045) * style.line_width, line_color(style, color))
        mask = np.maximum(mask, band)
    return mask


def _draw_knots(painting, frame, spec, style, light, knots, ties, base):
    masks = [_draw_knot(painting, frame, spec, style, light, knot, base, tie)
             for knot, tie in zip(knots, ties + [None] * (len(knots) - len(ties)))]
    return np.maximum.reduce(masks) if masks else np.zeros(painting.shape, dtype=np.float32)


def draw_back_hair(painting, frame, spec, style, light, plan, in_front=False):
    """The hair mass behind the head. in_front=True draws it for a figure seen from behind,
    where the same mass lies over the head and back in full light."""
    base = rgb(spec.hair) if in_front else shadow_of(spec.hair, style.shadow_tint, 0.6)   # behind the head it sits in shade
    knots = np.zeros(painting.shape, dtype=np.float32)
    if plan.knots and not in_front:      # a tail or bun behind the head goes behind the mass too
        knots = _draw_knots(painting, frame, spec, style, light, plan.knots, plan.ties, base)
    mask = painting.mask(plan.back)
    if plan.behind:
        mask = np.maximum.reduce([mask] + [painting.mask(curve) for curve in plan.behind])
    if in_front:
        mask = np.maximum(mask, _hem_locks(painting, frame, spec, plan))
    painting.part(mask, base)
    lit = shade_form(painting, mask, base, style, light, bevel=frame.px(0.16),
                     threshold=style.shadow_threshold + (0.0 if in_front else 0.1))
    if plan.buzz is not None:            # below the cut line the clipped hair lets the skin through
        clipped = mask * (1.0 - painting.mask(plan.block))
        painting.fill(clipped, buzz_color(spec) if in_front else shadow_of(buzz_color(spec), style.shadow_tint, 0.6))
    if in_front and style.highlight > 0:
        band = _highlight_band(painting, frame, spec, plan.whorl) * mask * sh.smoothstep(-0.05, 0.2, lit)
        painting.fill(sh.blur(band, frame.px(0.001 + 0.004 * style.gradient)),
                      light_of(base, (1.0, 0.90, 0.84), 0.55), 0.95 * style.highlight)
    if style.strands > 0:
        rng = np.random.default_rng(spec.seed + 2)
        far_guide, near_guide = plan.back_guides
        count = int(BACK_STRANDS * style.strands * (1.6 if in_front else 1.0))
        paths = [geo.lerp(far_guide, near_guide, blend) for blend in rng.uniform(0.02, 0.98, count)]
        _draw_strands(painting, paths, frame, style, base, mask, rng)
    if style.line_width > 0:
        width, ink = frame.px(0.0066) * style.line_width, line_color(style, spec.hair)
        if in_front or plan.behind:
            painting.outline_mask(mask, width, ink)       # the mass plus its pointed ends, traced as one shape
        else:
            painting.outline(plan.back, width, ink)
    if plan.knots_back and in_front:     # seen from behind, the tail or bun lies over the mass
        knots = _draw_knots(painting, frame, spec, style, light, plan.knots_back, plan.ties_back, base)
    return np.maximum(mask, knots)


def draw_front_hair(painting, frame, spec, style, light, plan, light2d, head, skin):
    base = rgb(spec.hair)
    shadow = adjust(shadow_of(base, style.shadow_tint, style.shadow_depth), value=0.88)
    ink = line_color(style, base)
    width = frame.px(0.0060) * style.line_width
    rng = np.random.default_rng(spec.seed)

    cap = painting.mask(plan.cap)
    if plan.buzz is not None:            # two-block: clipped sides first, the longer top over them
        clipped = buzz_color(spec)
        painting.part(cap, clipped)
        shade_form(painting, cap, rgb(clipped), style, light, bevel=frame.px(0.10))
        block = painting.mask(plan.block)
        overhang = sh.cast_shadow(block, cap * (1.0 - block), (0.0, frame.px(BUZZ_SHADOW)), frame.px(0.01))
        painting.fill(overhang, shadow_of(clipped, style.shadow_tint, style.shadow_depth), 0.8)
        cap = cap * block
    painting.part(cap, base)
    union = cap.copy()
    strand_paths = list(plan.flow)
    for curve in plan.locks:
        mask = painting.mask(curve)
        painting.part(mask, base)
        # Each lock is shaded as its own ribbon so clumps read as separate volumes.
        lit = sh.lighting(mask, light, bevel=frame.px(0.05))
        painting.fill(sh.shadow_from_light(lit, 0.08, style.edge_softness + 0.04) * mask, shadow, 0.8)
        if width > 0:
            tip = len(curve) // 2
            for edge in (curve[:tip + 1][::-1], curve[tip:]):       # both edges, drawn tip -> root
                painting.stroke(geo.subpath(edge, 0.0, 0.72), width, ink, taper=(0.10, 0.70))
        union = np.maximum(union, mask)
        if style.strands > 0:
            strand_paths += _lock_strand_paths(curve, plan.whorl, frame, style, rng)

    # Overall volume of the hair mass on top of the per-lock shading.
    lit = sh.lighting(union, light, bevel=frame.px(0.22))
    painting.fill(sh.shadow_from_light(lit, style.shadow_threshold - 0.10, style.edge_softness + 0.03) * union,
                  shadow, 0.7)
    if style.gradient > 0:
        # Light falls off across the head; skin colour glows through the thin tips near the face.
        top = frame.place([(-0.3, 0.0)])[0] if light2d[0] * frame.side < 0 else frame.place([(0.3, 0.0)])[0]
        far_end = top - light2d * frame.px(0.9)
        painting.fill(union * sh.linear_ramp(painting.shape, top, far_end), shadow, 0.55 * style.gradient)
        face_center = frame.face([(0.0, spec.eye_y)])[0]
        glow = (1.0 - sh.radial_ramp(painting.shape, face_center, frame.px(0.30))) ** 1.5
        painting.fill(union * glow * sh.blur(head, frame.px(0.02)), skin, 0.30)
    lit_side = sh.smoothstep(-0.05, 0.2, lit)
    if style.highlight > 0:
        band = _highlight_band(painting, frame, spec, plan.whorl) * union * lit_side
        painting.fill(sh.blur(band, frame.px(0.001 + 0.004 * style.gradient)),
                      light_of(base, (1.0, 0.90, 0.84), 0.55), 0.95 * style.highlight)
    if strand_paths:
        _draw_strands(painting, strand_paths, frame, style, base, union, rng, lit_side)
    if width > 0:
        painting.stroke(geo.subpath(plan.cap, 0.0, 0.27), width, ink, taper=(0.1, 0.3))
        painting.stroke(geo.subpath(plan.cap, 0.80, 1.0), width, ink, taper=(0.3, 0.1))
    return union
