"""Hand: a palm with five jointed fingers, seen flat (back of the hand or palm).

Fingers are walked joint by joint like the body skeleton. Curling a finger toward
the palm shows on a flat view as shortening, so each segment is scaled by the
cosine of its bend; a fully curled finger shrinks to its knuckle, which is how a
fist looks from the back.

Units are hand lengths (wrist to the tip of the middle finger).
"""
from dataclasses import dataclass

import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..color import mix, rgb, shadow_of
from ..styles import cast_softness_px, line_color, shade_form

# finger order: index, middle, ring, little
FINGER_BASES = [(0.150, 0.500), (0.050, 0.530), (-0.050, 0.512), (-0.146, 0.455)]   # (across, along)
FINGER_LENGTHS = [0.40, 0.45, 0.41, 0.32]
FINGER_HALF_WIDTHS = [0.054, 0.055, 0.052, 0.045]
FINGER_FAN = [9.0, 1.5, -6.0, -15.0]          # degrees from the hand axis at full spread
PHALANGES = (0.44, 0.31, 0.25)                # share of the finger length
FLEX = (80.0, 100.0, 70.0)                    # bend of the three joints at curl = 1
SIDEWAYS_DRIFT = 5.0                          # curled fingers lean toward the middle finger (degrees per joint)
TIP_TAPER = 0.80
PALM = [(-0.150, 0.0), (-0.200, 0.20), (-0.215, 0.42), (-0.150, 0.470), (-0.050, 0.520), (0.050, 0.540),
        (0.150, 0.520), (0.215, 0.455), (0.232, 0.20), (0.160, 0.0)]
THUMB_BASE = (0.120, 0.070)
THUMB_SEGMENTS = (0.215, 0.175, 0.140)        # metacarpal (inside the palm's flesh), then two phalanges
THUMB_HALF_WIDTHS = [0.090, 0.076, 0.062, 0.050]
THUMB_ANGLE = (22.0, 60.0)                    # from the hand axis: tucked .. stretched away
LINE_WIDTH = 0.022                            # outline width in hand lengths
FIGURE_HAND_LENGTH = 0.72                     # hand length on a full figure, in head heights
MIN_HAND_FORESHORTEN = 0.55                   # a hand drawn shorter than this share of its length stops reading as a hand


@dataclass
class HandPose:
    curl: tuple = (0.18, 0.24, 0.30, 0.36)    # index..little: 0 straight, 1 folded into the palm
    spread: float = 0.45                      # 0 fingers together .. 1 fanned out
    thumb: float = 0.45                       # 0 tucked along the palm .. 1 stretched away
    thumb_curl: float = 0.2


RELAXED = HandPose()
OPEN = HandPose(curl=(0.0, 0.0, 0.0, 0.03), spread=1.0, thumb=1.0, thumb_curl=0.0)
FIST = HandPose(curl=(1.0, 1.0, 1.0, 1.0), spread=0.1, thumb=0.1, thumb_curl=1.0)
POINT = HandPose(curl=(0.0, 0.95, 1.0, 1.0), spread=0.2, thumb=0.15, thumb_curl=0.9)
PEACE = HandPose(curl=(0.0, 0.0, 1.0, 1.0), spread=1.0, thumb=0.1, thumb_curl=1.0)
HAND_POSES = {"relaxed": RELAXED, "open": OPEN, "fist": FIST, "point": POINT, "peace": PEACE}


class HandFrame:
    """Maps hand units to pixels. thumb_side: +1 puts the thumb on the screen left of a hand pointing down.

    length scales the hand along its axis, width across it and every thickness. A hand pointing toward
    or away from the viewer shortens along its axis only; scaling it whole would shrink it to a child's hand.
    """

    def __init__(self, wrist, angle, length, thumb_side=1.0, width=None):
        radians = np.radians(angle)
        self.wrist = np.asarray(wrist, dtype=np.float64)
        self.along = np.array([np.sin(radians), np.cos(radians)])          # toward the fingertips
        self.across = np.array([-self.along[1], self.along[0]]) * thumb_side   # toward the thumb
        self.length = length
        self.width = length if width is None else width

    def place(self, points):
        pts = geo.as_points(points)
        return self.wrist + pts[:, :1] * self.across * self.width + pts[:, 1:] * self.along * self.length

    def px(self, units):
        return units * self.width


def _finger_joints(base, length, fan_angle, curl):
    """Joint positions of one finger in hand units, base to tip."""
    points = [np.array(base, dtype=np.float64)]
    bend, heading = 0.0, fan_angle
    for share, flex in zip(PHALANGES, FLEX):
        bend += flex * curl
        heading += -np.sign(fan_angle) * SIDEWAYS_DRIFT * curl
        seen = max(np.cos(np.radians(bend)), 0.0)                # a segment bent past 90 degrees hides behind the knuckle
        step = np.array([np.sin(np.radians(heading)), np.cos(np.radians(heading))]) * length * share * seen
        points.append(points[-1] + step)
    return np.array(points)


def hand_shapes(frame, pose=RELAXED):
    """Closed pixel curves of the palm, the four fingers and the thumb, plus the finger joints."""
    fingers, joints = [], []
    for base, length, half, fan, curl in zip(FINGER_BASES, FINGER_LENGTHS, FINGER_HALF_WIDTHS, FINGER_FAN, pose.curl):
        skeleton = _finger_joints(base, length, fan * (0.25 + 0.75 * pose.spread), curl)
        start = skeleton[0] - np.array([0.0, 0.10])              # root sinks into the palm so the join is hidden
        path = frame.place(np.vstack([start, skeleton]))
        widths = frame.px(np.array([half, half, half * 0.94, half * 0.88, half * TIP_TAPER]))
        fingers.append(geo.tube(geo.smooth(path) if len(path) > 2 else path, widths, caps=(False, True), count=30))
        joints.append(frame.place(skeleton))
    angle = np.interp(pose.thumb, [0.0, 1.0], THUMB_ANGLE)
    points = [np.array(THUMB_BASE)]
    for index, segment in enumerate(THUMB_SEGMENTS):
        if index > 0:
            angle -= (30.0 if index == 1 else 45.0) * pose.thumb_curl     # the thumb folds across the palm
        points.append(points[-1] + np.array([np.sin(np.radians(angle)), np.cos(np.radians(angle))]) * segment)
    thumb_path = frame.place(points)
    thumb = geo.tube(geo.smooth(thumb_path), frame.px(np.array(THUMB_HALF_WIDTHS)), caps=(True, True), count=30)
    palm = geo.smooth(frame.place(PALM), closed=True, corners=(0, len(PALM) - 1))
    return {"palm": palm, "fingers": fingers, "thumb": thumb, "joints": joints, "thumb_joints": thumb_path}


def hand_mask(painting, shapes):
    return np.maximum.reduce([painting.mask(curve) for curve in [shapes["palm"], shapes["thumb"]] + shapes["fingers"]])


def draw_finger_gaps(painting, shapes, ink, width):
    """Lines between neighbouring fingers; without them a small hand reads as a mitten."""
    inside = sh.blur(hand_mask(painting, shapes), 1.0) * (1.0 - painting.mask(shapes["palm"]))
    for finger in shapes["fingers"]:
        painting.outline_mask(painting.mask(finger), width, ink, contrast=0.2, keep=inside)


def draw_hand(painting, wrist, angle, length, skin, style, light=sh.DEFAULT_LIGHT, pose=RELAXED,
              thumb_side=1.0, view="back", forearm=0.6):
    """Draw one hand as a study. view: "back" shows nails and knuckles, "palm" shows the creases.

    forearm: length of forearm to include behind the wrist, in hand lengths (0 for none).
    Returns the hand mask.
    """
    frame = HandFrame(wrist, angle, length, thumb_side)
    shapes = hand_shapes(frame, pose)
    skin_color = rgb(skin)
    shadow = shadow_of(skin_color, (0.93, 0.77, 0.79), style.shadow_depth)
    ink = line_color(style, skin_color, "#4a2a2e")
    width = frame.px(LINE_WIDTH) * style.line_width
    soft = cast_softness_px(style, painting)
    light2d = np.asarray(light[:2]) / max(np.linalg.norm(light[:2]), 1e-9)

    base_parts = [shapes["palm"]]
    if forearm > 0:
        arm = geo.tube(frame.place([(0.0, -forearm), (0.0, 0.04)]), frame.px(np.array([0.205, 0.180, 0.158])), caps=(False, False))
        base_parts.append(arm)
    palm = np.maximum.reduce([painting.mask(curve) for curve in base_parts])
    painting.part(palm, skin_color)
    shade_form(painting, palm, skin_color, style, light, bevel=frame.px(0.12), shadow_color=shadow,
               threshold=style.shadow_threshold - 0.12)
    if width > 0:
        painting.outline_mask(palm, width, ink)
    total = palm.copy()

    # Fingers go on from the little finger to the index so each overlaps its neighbour the natural way.
    order = list(range(3, -1, -1))
    pieces = [shapes["fingers"][i] for i in order] + [shapes["thumb"]]
    if view == "palm":                                   # seen from the palm, the thumb's root lies under the fingers
        pieces = [shapes["thumb"]] + [shapes["fingers"][i] for i in order]
    outside_palm = 1.0 - sh.blur(painting.mask(shapes["palm"]), frame.px(0.012))
    for curve in pieces:
        mask = painting.mask(curve)
        free = mask * outside_palm                       # the root of a finger is the palm itself: leave it untouched
        offset = -light2d * frame.px(0.025) + [0.0, frame.px(0.012)]
        painting.fill(sh.cast_shadow(free, total, offset, soft) * (1.0 - mask), shadow, 0.8)
        painting.part(free, skin_color)
        painting.erase_lines(mask)                       # the palm's edge must not cut across the finger it carries
        shade_form(painting, free, skin_color, style, light, shadow_color=shadow, threshold=style.shadow_threshold - 0.10,
                   height=sh.inflate(mask, bevel=frame.px(0.05)))
        if width > 0:
            painting.outline_mask(mask, width, ink, keep=outside_palm)
        total = np.maximum(total, mask)

    _draw_hand_details(painting, frame, shapes, pose, skin_color, shadow, ink, style, view, total)
    return total


def _draw_hand_details(painting, frame, shapes, pose, skin, shadow, ink, style, view, clip):
    crease = mix(ink, shadow, 0.45)
    fine = frame.px(0.011)
    if view == "back":
        for joints, half, curl in zip(shapes["joints"], FINGER_HALF_WIDTHS, pose.curl):
            visible = max(np.cos(np.radians(sum(FLEX) * curl)), 0.0)
            across = frame.across * frame.px(half)
            # knuckle: a small soft shadow on its far side
            knuckle = geo.ellipse(joints[0] + frame.along * frame.px(0.012), frame.px(half * 0.8), frame.px(0.020))
            painting.fill(sh.blur(painting.mask(knuckle), frame.px(0.014)) * clip, shadow, 0.30)
            for joint in joints[1:3]:                                    # creases over the two finger joints
                if curl < 0.75:
                    painting.stroke(geo.bent_line(joint - across * 0.7, joint + across * 0.7, 0.10), fine, crease,
                                    taper=(0.3, 0.3), opacity=0.6, layer="color", clip=clip)
            if visible > 0.25:                                           # nail, only while the fingertip faces us
                tip, before = joints[3], joints[2]
                toward = (tip - before) / max(np.linalg.norm(tip - before), 1e-9)
                side = np.array([-toward[1], toward[0]])
                center = tip - toward * frame.px(0.028)
                nail = geo.smooth([center - side * frame.px(half * 0.62) - toward * frame.px(0.040),
                                   center - side * frame.px(half * 0.66) + toward * frame.px(0.020),
                                   center + toward * frame.px(0.046),
                                   center + side * frame.px(half * 0.66) + toward * frame.px(0.020),
                                   center + side * frame.px(half * 0.62) - toward * frame.px(0.040)], closed=True)
                painting.fill(painting.mask(nail) * clip, mix(skin, "#f3b6b0", 0.55), 0.9)
                painting.stroke(nail, fine * 0.8, crease, taper=(0.1, 0.1), opacity=0.5, layer="color", clip=clip)
        thumb = shapes["thumb_joints"]
        toward = (thumb[3] - thumb[2]) / max(np.linalg.norm(thumb[3] - thumb[2]), 1e-9)
        side = np.array([-toward[1], toward[0]])
        painting.stroke(geo.bent_line(thumb[2] - side * frame.px(0.04), thumb[2] + side * frame.px(0.04), 0.1), fine, crease,
                        taper=(0.3, 0.3), opacity=0.6, layer="color", clip=clip)
    else:
        # the three main palm creases
        for points in ([(0.20, 0.36), (0.02, 0.33), (-0.19, 0.39)], [(0.20, 0.30), (0.02, 0.24), (-0.16, 0.16)],
                       [(0.17, 0.33), (0.05, 0.20), (0.02, 0.04)]):
            painting.stroke(geo.smooth(frame.place(points)), fine * 1.2, crease, taper=(0.25, 0.4), opacity=0.7,
                            layer="color", clip=clip)
        for joints, half in zip(shapes["joints"], FINGER_HALF_WIDTHS):
            across = frame.across * frame.px(half)
            for joint in (joints[0] + frame.along * frame.px(0.03), joints[1], joints[2]):
                painting.stroke(geo.bent_line(joint - across * 0.75, joint + across * 0.75, -0.08), fine, crease,
                                taper=(0.3, 0.3), opacity=0.6, layer="color", clip=clip)
        pad = geo.ellipse(frame.place([(0.14, 0.18)])[0], frame.px(0.085), frame.px(0.15), angle=np.arctan2(frame.along[0], frame.along[1]) * -1)
        painting.fill(sh.blur(painting.mask(pad), frame.px(0.03)) * clip, mix(skin, "#f5a9a0", 0.5), 0.35)


# ---- hands on a full figure ------------------------------------------------------------
def figure_hand_frame(skeleton, side):
    wrist, tip = skeleton.joints[f"wrist_{side}"], skeleton.joints[f"hand_{side}"]
    along = tip - wrist
    angle = np.degrees(np.arctan2(along[0], along[1]))
    # Arms at rest turn the thumbs toward the body.
    thumb_side = 1.0 if side == "r" else -1.0
    full = skeleton.px(FIGURE_HAND_LENGTH)
    length = full
    if skeleton.yaw != 0.0:          # a hand pointing toward or away from the viewer reads shorter, never narrower
        length = max(np.linalg.norm(along), full * MIN_HAND_FORESHORTEN)
    return HandFrame(wrist - along / max(np.linalg.norm(along), 1e-9) * skeleton.px(0.03), angle, length, thumb_side,
                     width=full)


def figure_hand(painting, skeleton, side, pose=RELAXED):
    """Shapes and merged mask of a hand at the end of a figure's arm."""
    frame = figure_hand_frame(skeleton, side)
    shapes = hand_shapes(frame, pose)
    return frame, shapes, hand_mask(painting, shapes)
