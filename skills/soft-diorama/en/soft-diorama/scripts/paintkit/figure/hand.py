"""Hands: a palm, four fingers and a thumb, posed by per-finger curl.

Flat (back of the hand or palm toward the viewer), a curled finger is drawn
shorter (it points toward or away from the viewer); a fully curled one becomes a
folded stub at the knuckle. That is enough to read as open, relaxed, pointing, a
fist and so on, without modeling every joint.

A hand can also roll about its own length, up to edge-on. Every point then has
a depth off the palm plane (palm thickness, curled fingers, the thumb), and the
roll turns that depth into sideways offset: seen from the thumb or little-finger
side the curled fingers fan out toward the palm side and the palm is a thin slab.
"""
from dataclasses import dataclass

import numpy as np

from .. import raster
from ..color import adjust, mix
from .look import skin_line, skin_shadow
from .skin import Part, paint_parts

# Local hand space: origin at the wrist center, +y toward the fingertips,
# +x toward the thumb. Unit = hand length (wrist to middle fingertip).
_PALM = [(-0.125, -0.10), (0.125, -0.10), (0.150, 0.02), (0.215, 0.13), (0.235, 0.30), (0.215, 0.47),
         (0.150, 0.535), (0.040, 0.560), (-0.070, 0.545), (-0.170, 0.500), (-0.215, 0.420), (-0.200, 0.200),
         (-0.140, 0.02)]
# name: (knuckle x, knuckle y, rest angle, extra angle at full spread, length, width)
_FINGERS = {
    'index': (0.150, 0.500, 4.0, 9.0, 0.420, 0.098),
    'middle': (0.040, 0.530, 0.5, 2.0, 0.470, 0.100),
    'ring': (-0.068, 0.515, -4.0, -6.0, 0.435, 0.094),
    'pinky': (-0.165, 0.465, -9.0, -15.0, 0.345, 0.082),
}
_THUMB_OPEN = [(0.130, 0.080), (0.265, 0.250), (0.345, 0.390), (0.385, 0.500)]
_THUMB_FOLDED = [(0.150, 0.100), (0.215, 0.290), (0.110, 0.400), (-0.020, 0.430)]
_THUMB_WIDTH = 0.118
_FOLD_AT = 0.7                # curl above this draws the finger as a folded stub
_KNUCKLE_RISE = 0.060         # how far a folded finger's knuckle stands above the palm edge
_FOLD_REACH = 0.210           # how far a folded finger lies back over the palm
_FORESHORTEN = 0.5            # how much a half-curled finger shortens
# Depth off the palm plane (local units, + toward the palm side), used once the hand rolls.
_PALM_THICKNESS = ([-0.10, 0.15, 0.35, 0.50, 0.56], [0.085, 0.115, 0.100, 0.075, 0.065])   # y -> half thickness
_CURL_DEPTH = 0.9             # how far toward the palm side a curled fingertip sits (share of its true offset)
_FOLDED_DEPTH = {'back': (0.0, 0.14, 0.26), 'palm': (0.06, 0.20, 0.26)}
_FOLDED_LOOP_Y = (-0.08, 0.03, -0.13)        # a folded finger from the side: out, over, back down
_FOLDED_LOOP_DEPTH = (0.0, 0.17, 0.26)
_THUMB_DEPTH_OPEN = (0.04, 0.12, 0.19, 0.23)
# A resting thumb lies along the index finger, in front of the palm; a rolled hand shows that, not the
# spread thumb of the flat view (which would stick out sideways like a stick).
_THUMB_RESTING = [(0.120, 0.060), (0.190, 0.240), (0.200, 0.360), (0.170, 0.460)]
_THUMB_DEPTH_RESTING = (0.06, 0.16, 0.22, 0.25)
_ROLLED_SPREAD = 0.7          # how much a rolled hand closes its spread fingers (at edge-on)
_WEB_FROM = 0.3               # resting share of the thumb above which its ball joins the palm outline
_THUMB_DEPTH_FOLDED = (0.06, 0.15, 0.22, 0.24)
_EDGE_ORDER = 0.3             # |sideways share of depth| above which parts layer by depth, not the flat order

# pose: (thumb, index, middle, ring, pinky) curl 0..1, spread 0..1, thumb reach 0..1
POSES = {
    'open': ((0.0, 0.0, 0.0, 0.0, 0.0), 1.0, 1.0),
    'relaxed': ((0.0, 0.22, 0.28, 0.34, 0.40), 0.25, 0.45),
    'fist': ((1.0, 1.0, 1.0, 1.0, 1.0), 0.0, 0.0),
    'point': ((1.0, 0.0, 1.0, 1.0, 1.0), 0.0, 0.0),
    'peace': ((1.0, 0.0, 0.0, 1.0, 1.0), 1.0, 0.0),
    'thumbs_up': ((0.0, 1.0, 1.0, 1.0, 1.0), 0.0, 1.35),
}


@dataclass
class HandSpec:
    pose: str = 'relaxed'        # key of POSES
    view: str = 'back'           # 'back' (nails, knuckles) | 'palm' (creases); figures also take 'rest'
    nails: str = ''              # nail polish color; empty = natural
    roll: float = 0.0            # draw_hand only: degrees turned about the hand's length. 0 flat, 90 edge-on;
                                 # positive brings the thumb edge toward the viewer


@dataclass
class HandOrientation:
    """How the hand's own axes lie toward the viewer (the screen axis across the hand and the view axis).
    across: screen share of the thumb axis (1 flat, 0 edge-on). palm: screen shift per unit of depth
    toward the palm side. thumb_depth, palm_depth: how far the thumb axis and the palm side point at the viewer."""
    across: float = 1.0
    palm: float = 0.0
    thumb_depth: float = 0.0
    palm_depth: float = -1.0

    @classmethod
    def from_roll(cls, view, roll):
        angle = np.radians(np.clip(roll, -90.0, 90.0))
        face = 1.0 if view == 'palm' else -1.0      # the palm side points toward (+) or away from the viewer
        return cls(across=float(np.cos(angle)), palm=float(-face * np.sin(angle)),
                   thumb_depth=float(np.sin(angle)), palm_depth=float(face * np.cos(angle)))


class _HandFrame:
    """Maps local hand coordinates to canvas pixels."""

    def __init__(self, wrist, direction_deg, length, thumb_side, orientation=None):
        a = np.radians(direction_deg)
        self.origin = np.asarray(wrist, np.float64)
        self.along = np.array([np.sin(a), np.cos(a)])                     # toward the fingertips
        self.across = thumb_side * np.array([np.cos(a), -np.sin(a)])      # toward the thumb
        self.length = length
        self.orientation = orientation or HandOrientation()

    def pts(self, local, depth=None):
        """Local (x, y) points, with an optional depth off the palm plane per point, to px."""
        local = np.asarray(local, np.float64).reshape(-1, 2)
        x = local[:, :1] * self.orientation.across
        if depth is not None:
            x = x + np.asarray(depth, np.float64).reshape(-1, 1) * self.orientation.palm
        return self.origin + self.length * (x * self.across + local[:, 1:] * self.along)

    def pt(self, x, y, depth=0.0):
        return self.pts([(x, y)], [depth])[0]

    def depth_of(self, local, depth):
        """Mean nearness to the viewer of a part (for layering a rolled hand)."""
        local = np.asarray(local, np.float64).reshape(-1, 2)
        return float(np.mean(local[:, 0] * self.orientation.thumb_depth + np.asarray(depth) * self.orientation.palm_depth))


def _finger_path(name, curl, spread, view):
    """Local centerline (start, mid, tip), width, folded flag and depth of each point off the palm plane."""
    kx, ky, rest, fan, length, width = _FINGERS[name]
    angle = np.radians(rest + fan * spread)
    direction = np.array([np.sin(angle), np.cos(angle)])
    knuckle = np.array([kx, ky])
    folded = curl > _FOLD_AT
    if folded and view == 'palm':
        # Curled onto the palm: the visible segment runs from the knuckle back down toward the wrist.
        path = [knuckle + _KNUCKLE_RISE * direction, knuckle - 0.07 * direction, knuckle - _FOLD_REACH * direction]
        return np.array(path), width * 1.04, folded, np.array(_FOLDED_DEPTH['palm'])
    if folded:
        # From the back only the knuckle shows as a bump on the top edge.
        path = [knuckle - 0.10 * direction, knuckle, knuckle + _KNUCKLE_RISE * direction]
        return np.array(path), width * 1.08, folded, np.array(_FOLDED_DEPTH['back'])
    shortened = 1.0 - _FORESHORTEN * curl
    reach = length * shortened
    lean = np.array([-np.sign(kx - 0.04) * 0.012, 0.0])                   # tips drift toward the middle finger
    path = [knuckle - 0.08 * direction, knuckle + 0.5 * reach * direction + 0.4 * lean,
            knuckle + reach * direction + lean]
    # The length lost to foreshortening went toward the palm side: that offset shows once the hand rolls.
    tip_depth = _CURL_DEPTH * length * np.sqrt(max(0.0, 1.0 - shortened ** 2))
    return np.array(path), width, folded, np.array([0.0, 0.3 * tip_depth, tip_depth])


def _palm_depth(sideways):
    """Depth of each palm outline point that pushes it outward once the hand rolls: the palm's thickness."""
    outline = np.array(_PALM)
    half = np.interp(outline[:, 1], *_PALM_THICKNESS)
    return np.sign(outline[:, 0]) * half * (1.0 if sideways >= 0 else -1.0)


def build_hand(cv, wrist, direction_deg, length, spec=None, thumb_side=1.0, forearm=0.0, attached=True,
               orientation=None):
    """Shapes of one hand as skin parts, back to front, plus the data needed for its details.

    Use this when the hand belongs to a larger body painted with paint_parts();
    call finish_hand() afterwards. For a hand on its own use draw_hand().
    attached: the wrist continues into an arm, so the palm fades in at the wrist.
    orientation: HandOrientation; None takes it from spec.view and spec.roll.
    """
    spec = spec or HandSpec()
    curls, spread, thumb_reach = POSES[spec.pose]
    orientation = orientation or HandOrientation.from_roll(spec.view, spec.roll)
    frame = _HandFrame(wrist, direction_deg, length, thumb_side, orientation)
    bulge = lambda width: 0.42 * width * length                           # noqa: E731 - tiny local helper

    palm = Part(cv.blob(frame.pts(_PALM, _palm_depth(orientation.palm))), bulge(0.30))
    if attached or forearm > 0:
        palm.root, palm.root_radius = tuple(frame.pt(0.0, -0.06)), 0.20 * length
    arm = []
    if forearm > 0:
        arm_mask = cv.ribbon(frame.pts([(0.0, 0.05), (0.0, -0.5 * forearm), (0.0, -forearm)]), 0.36 * length,
                             [0.72, 0.85, 1.0], smooth=False)
        arm = [Part(arm_mask, bulge(0.34))]
    rolled = abs(orientation.palm)                  # 0 flat .. 1 edge-on
    spread = spread * (1.0 - _ROLLED_SPREAD * rolled)
    fingers, folded_fingers, paths, depths = [], [], {}, {}
    for name, curl in zip(_FINGERS, curls[1:]):
        path, width, folded, depth = _finger_path(name, curl, spread, spec.view)
        if folded and rolled > 0.0:
            # Seen from the side a folded finger loops out from the knuckle and tucks back into the palm.
            kx, ky = _FINGERS[name][:2]
            loop = np.array([(kx, ky + dy) for dy in _FOLDED_LOOP_Y])
            path = path * (1.0 - rolled) + loop * rolled
            depth = depth * (1.0 - rolled) + np.array(_FOLDED_LOOP_DEPTH) * rolled
        mask = cv.ribbon(frame.pts(path, depth), width * length, 'finger', smooth=False)
        part = Part(mask, bulge(width), tuple(frame.pts(path[:1], depth[:1])[0]), 0.15 * length)
        (folded_fingers if folded else fingers).append(part)
        paths[name] = (path, width, folded, depth)
        depths[id(part)] = frame.depth_of(path, depth)
    thumb_folded, resting = curls[0] > _FOLD_AT, 0.0
    if thumb_folded:
        thumb_path, thumb_depth = np.array(_THUMB_FOLDED), np.array(_THUMB_DEPTH_FOLDED)
    else:
        base = np.array(_THUMB_OPEN[0])
        thumb_path = base + (np.array(_THUMB_OPEN) - base) * [0.55 + 0.45 * thumb_reach, 1.0]
        thumb_depth = np.array(_THUMB_DEPTH_OPEN)
        resting = rolled * float(np.clip((1.0 - thumb_reach) / 0.55, 0.0, 1.0))   # an open or raised thumb stays out
        thumb_path = thumb_path * (1.0 - resting) + np.array(_THUMB_RESTING) * resting
        thumb_depth = thumb_depth * (1.0 - resting) + np.array(_THUMB_DEPTH_RESTING) * resting
    thumb = Part(cv.ribbon(frame.pts(thumb_path, thumb_depth), _THUMB_WIDTH * length, 'finger'), bulge(_THUMB_WIDTH),
                 tuple(frame.pts(thumb_path[:1], thumb_depth[:1])[0]), 0.14 * length)
    depths[id(thumb)] = frame.depth_of(thumb_path, thumb_depth)

    if not thumb_folded and resting > _WEB_FROM:
        # The ball of the thumb fills the gap between a resting thumb and the palm edge.
        web = np.array([(0.10, 0.00), thumb_path[1], (thumb_path[1] + thumb_path[2]) / 2, (0.15, 0.48), (0.02, 0.30)])
        web_depth = [0.0, thumb_depth[1], (thumb_depth[1] + thumb_depth[2]) / 2, 0.03, 0.0]
        palm.mask = np.maximum(palm.mask, cv.blob(frame.pts(web, web_depth)))
    if abs(orientation.palm) > _EDGE_ORDER:
        # Rolled: fingers keep their side of the palm (they grow from its edge), the thumb goes in front
        # only while its edge faces the viewer, and each side is layered far to near.
        nearest_last = lambda group: sorted(group, key=lambda part: depths[id(part)])   # noqa: E731
        thumb_in_front = depths[id(thumb)] >= 0.0 and not (thumb_folded and spec.view == 'back')
        in_front = fingers + (folded_fingers if spec.view == 'palm' else []) + ([thumb] if thumb_in_front else [])
        behind = (folded_fingers if spec.view == 'back' else []) + ([] if thumb_in_front else [thumb])
        over_palm = nearest_last(in_front)
        parts = nearest_last(behind) + arm + [palm] + over_palm
        # Rolled fingers lie close together: the slits they enclose would be outlined as dark dashes.
        solid = np.maximum.reduce([palm.mask, thumb.mask] + [part.mask for part in fingers + folded_fingers])
        palm.mask = np.maximum(palm.mask, raster.fill_holes(solid) - solid)
    elif spec.view == 'palm':      # curled fingers and thumb lie on top of the palm
        over_palm = fingers + folded_fingers + [thumb]
        parts = arm + [palm] + over_palm
    else:                          # from the back they hide behind it
        over_palm = fingers + ([] if thumb_folded else [thumb])
        parts = ([thumb] if thumb_folded else []) + folded_fingers + arm + [palm] + over_palm
    covered = cv.empty()
    for part in over_palm:
        covered = np.maximum(covered, part.mask)
    return parts, dict(frame=frame, spec=spec, paths=paths, palm_only=palm.mask * (1.0 - covered))


def finish_hand(cv, details, skin, look, union):
    """Nails, knuckles and creases for a hand built with build_hand()."""
    _hand_details(cv, details['frame'], details['spec'], details['paths'], skin, look, union,
                  details['palm_only'])


def draw_hand(cv, wrist, direction_deg, length, skin, look, spec=None, thumb_side=1.0, forearm=0.0):
    """Draw one hand. wrist: px. direction_deg: where the fingers point
    (0 = down, 90 = screen right, 180 = up). length: wrist to middle fingertip in px.
    thumb_side: +1 puts the thumb on the side that is screen-right when the
    fingers point down; -1 mirrors it.
    forearm: length of forearm to include behind the wrist, in hand lengths (for hand studies).
    Returns the hand mask.
    """
    parts, details = build_hand(cv, wrist, direction_deg, length, spec, thumb_side, forearm, attached=False)
    union = paint_parts(cv, parts, skin, look)
    finish_hand(cv, details, skin, look, union)
    return union


def _hand_details(cv, frame, spec, paths, skin, look, union, palm_only):
    """Nails and knuckle hints on the back; creases on the palm side."""
    line = skin_line(skin, look)
    shade = skin_shadow(skin, look.shade_depth)
    length = frame.length
    # Rolled toward edge-on, the face that carries the details turns away.
    shown = float(np.clip(abs(frame.orientation.palm_depth), 0.0, 1.0))
    creases = []
    for name, (path, width, folded, depth) in paths.items():
        knuckle, tip = path[0] + (path[1] - path[0]) * 0.16, path[2]
        knuckle_depth = depth[0] + (depth[1] - depth[0]) * 0.16
        axis, axis_depth = tip - knuckle, depth[2] - knuckle_depth
        side = np.array([axis[1], -axis[0]]) / max(np.hypot(*axis), 1e-6)
        if folded:
            continue
        for at in (0.40, 0.70):                       # finger joints
            center, center_depth = knuckle + axis * at, knuckle_depth + axis_depth * at
            creases.append((frame.pts([center - side * width * 0.36, center + axis * 0.012,
                                       center + side * width * 0.36], [center_depth] * 3), 0.010 * length, 'taper'))
        if spec.view == 'back':
            nail = cv.ribbon(frame.pts([knuckle + axis * 0.80, knuckle + axis * 0.955],
                                       [knuckle_depth + axis_depth * 0.80, knuckle_depth + axis_depth * 0.955]),
                             width * 0.62 * length, 'flat', smooth=False)
            tone = spec.nails or mix(adjust(skin, lightness=0.03, chroma=1.3, toward_hue=15.0, toward=0.5),
                                     '#ffffff', 0.25)
            cv.tint(nail * union, tone, 'normal', 0.9 * shown)
            cv.outline(nail, 0.9 * max(look.line_px, 0.6 * look.scale), line, opacity=0.5 * shown, clip=union)
    if spec.view == 'back':
        for name, (path, width, folded, depth) in paths.items():     # knuckle dimples
            bump = cv.ellipse(*frame.pt(*(path[0] + (path[1] - path[0]) * 0.20), depth[0] + (depth[1] - depth[0]) * 0.20),
                              0.030 * length * frame.orientation.across, 0.020 * length)
            cv.tint(raster.blur(bump, 0.008 * length) * union, shade, 'normal', 0.45 * shown)
    else:
        palm_lines = [[(0.20, 0.40), (0.05, 0.36), (-0.10, 0.40), (-0.19, 0.43)],      # heart line
                      [(0.215, 0.36), (0.08, 0.27), (-0.06, 0.24), (-0.16, 0.25)],     # head line
                      [(0.17, 0.42), (0.06, 0.30), (0.03, 0.14), (0.05, 0.02)]]        # life line
        palm_creases = cv.ribbons([(frame.pts(points), 0.012 * length, 'taper') for points in palm_lines])
        cv.tint(raster.blur(palm_creases, 0.5 * look.scale) * palm_only, line, 'normal', 0.45 * shown)
        pad = cv.ellipse(*frame.pt(0.13, 0.17), 0.10 * length * max(frame.orientation.across, 0.3), 0.15 * length,
                         np.degrees(np.arctan2(frame.along[1], frame.along[0])) - 70)
        cv.tint(raster.blur(pad, 0.03 * length) * palm_only, skin_shadow(skin, -0.4), 'normal', 0.5 * shown)
    opacity = (0.45 if spec.view == 'palm' else 0.28) * (1.0 if look.line_scale > 0 else 0.7) * shown
    cv.tint(raster.blur(cv.ribbons(creases), 0.5 * look.scale) * union, line, 'normal', opacity)
