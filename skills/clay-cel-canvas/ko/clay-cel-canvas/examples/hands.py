"""Worked example: hand studies, and the hand rig other scenes reuse.

Usage: python hands.py <anime|illust|painterly> <output.png> [width_px]

A hand is drawn in its own coordinates: wrist centre at the origin, fingers
toward -y, 100 units from wrist to the tip of the middle finger. Place it with
art.place(at=wrist, scale=..., angle=..., flip=...). The drawing shows a right
hand from the back; flip=True gives the left hand, and a palm view is the same
hand mirrored with creases in place of nails.
"""
import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atelier import STYLES, Art, ellipse, spline  # noqa: E402

# ---- anatomy (hand length = 100) ---------------------------------------------
PHALANGES = (0.46, 0.30, 0.24)             # share of a finger taken by each bone
FINGERS = (                                # knuckle position, length, width
    ((-17.0, -53.0), 40.0, 10.5),          # index
    ((-5.5, -56.0), 44.0, 11.0),           # middle
    ((6.0, -54.0), 41.0, 10.5),            # ring
    ((16.5, -48.0), 32.0, 9.0),            # little
)
THUMB_BASE = (-11.0, -10.0)
THUMB_BONES = (23.0, 16.0, 14.0)
THUMB_WIDTHS = (25.0, 16.0, 13.5, 11.5)       # wide at the root: the ball of the thumb
PALM = [(-15, 4), (-22, -20), (-23, -48), (-18, -58), (-5.5, -61.5), (6, -59.5), (17, -53.5),
        (22, -45), (22, -28), (18, -8), (14, 4)]
WRIST = [(0, 46, 31), (0, 14, 28), (0, -6, 30)]

SKIN = "#FAE1D2"
SKIN_SHADOW = "#E6BCB4"
SKIN_LINE = "#B9796F"
GAP_SHADOW = "#C48A82"                     # dark seam between fingers that touch
NAIL = "#F9D0C8"
CUFF = "#3F5C82"


class Pose(NamedTuple):
    """Angles in degrees. Positive spread and curl turn clockwise on screen.

    stretch below 1 foreshortens a finger that points toward or away from the
    viewer; around 0.3 leaves only the knuckle stub of a folded finger.
    """
    spread: tuple = (-9.0, -3.0, 3.0, 11.0)
    curl: tuple = ((0, 0, 0),) * 4
    stretch: tuple = (1.0, 1.0, 1.0, 1.0)
    thumb_angle: float = -52.0
    thumb_curl: tuple = (0.0, 14.0, 10.0)
    thumb_stretch: float = 1.0


OPEN = Pose(spread=(-15.0, -5.0, 5.0, 17.0), thumb_angle=-54.0)
RELAXED = Pose(spread=(-5.0, -1.0, 3.0, 7.0), curl=((0, 4, 4), (0, 2, 2), (0, -2, -2), (0, -6, -6)),
               stretch=(0.86, 0.84, 0.82, 0.8), thumb_angle=-38.0)
# Folded fingers leave a knuckle stub; the thumb tucks in beside the index knuckle.
POINTING = Pose(spread=(-4.0, 0.0, 3.0, 6.0), stretch=(1.0, 0.3, 0.3, 0.3),
                thumb_angle=-30.0, thumb_curl=(0.0, 12.0, 10.0), thumb_stretch=0.72)
VICTORY = Pose(spread=(-14.0, 6.0, 4.0, 8.0), stretch=(1.0, 1.0, 0.3, 0.3),
               thumb_angle=-30.0, thumb_curl=(0.0, 12.0, 10.0), thumb_stretch=0.72)


def bone_chain(base, lengths, angle, curls):
    """Joint positions of a chain of bones; angle 0 points toward -y."""
    points = [np.array(base, float)]
    for length, curl in zip(lengths, curls):
        angle += curl
        turn = np.radians(angle)
        points.append(points[-1] + length * np.array([np.sin(turn), -np.cos(turn)]))
    return np.array(points)


def limb(joints, widths):
    """Tube control points for a finger: starts inside the palm, ends rounded."""
    start = joints[0] - (joints[1] - joints[0]) * 0.22
    end_dir = (joints[-1] - joints[-2]) / np.linalg.norm(joints[-1] - joints[-2])
    tip = joints[-1] - end_dir * widths[-1] / 2            # the round cap adds this back
    centres = [start, *joints[:-1], tip]
    return [(x, y, w) for (x, y), w in zip(centres, [widths[0], *widths])]


def hand_parts(art, pose):
    """Masks and joint positions for every part of the hand."""
    fingers = []
    for (base, length, width), spread, curl, stretch in zip(FINGERS, pose.spread, pose.curl,
                                                            pose.stretch):
        joints = bone_chain(base, [length * share * stretch for share in PHALANGES], spread, curl)
        widths = (width, width * 0.95, width * 0.88, width * 0.78)
        fingers.append((art.tube(limb(joints, widths)), joints, width))
    thumb_joints = bone_chain(THUMB_BASE, [b * pose.thumb_stretch for b in THUMB_BONES],
                              pose.thumb_angle, pose.thumb_curl)
    thumb = art.tube(limb(thumb_joints, THUMB_WIDTHS))
    palm = np.maximum(art.shape(spline(PALM, closed=True)), art.tube(WRIST))
    return palm, fingers, thumb, thumb_joints


def across(joints, index, reach):
    """Short curve across a finger at a joint: knuckle wrinkle or palm crease."""
    along = joints[index] - joints[index - 1]
    along = along / max(np.linalg.norm(along), 1e-6)
    side = np.array([-along[1], along[0]]) * reach
    return spline([joints[index] - side, joints[index] + along * reach * 0.25, joints[index] + side])


def draw_back_details(art, fingers, thumb_joints, pose):
    for (mask, joints, width), stretch in zip(fingers, pose.stretch):
        if stretch < 0.5:                                    # folded: only the knuckle shows
            art.line(across(joints, 1, width * 0.3), SKIN_LINE, 1.0)
            continue
        for joint in (1, 2):
            art.line(across(joints, joint, width * 0.3), SKIN_LINE, 1.0, opacity=0.8)
        along = joints[3] - joints[2]
        angle = np.degrees(np.arctan2(along[0], -along[1]))
        centre = joints[3] - along * 0.5
        nail = art.shape(ellipse(*centre, width * 0.34, np.linalg.norm(along) * 0.46, angle)) * mask
        art.paint(nail, NAIL)
        art.outline(nail, SKIN_LINE, 0.8)
        art.light(art.blob(centre - (1.2, 1.2), width * 0.28) * nail, "#FFFFFF", 0.45)
        knuckle = art.blob(joints[0] + (0, 1), width * 0.55)
        art.shadow(knuckle * (1 - art.move(knuckle, -2, -2)), SKIN_SHADOW, 0.6)
    if pose.thumb_stretch < 0.9:                             # tucked thumb: nail faces away
        return
    along = thumb_joints[3] - thumb_joints[2]
    angle = np.degrees(np.arctan2(along[0], -along[1]))
    nail = art.shape(ellipse(*(thumb_joints[3] - along * 0.45), 3.9, np.linalg.norm(along) * 0.38, angle))
    art.paint(nail, NAIL)
    art.outline(nail, SKIN_LINE, 0.8)
    art.line(across(thumb_joints, 2, 4.0), SKIN_LINE, 1.0, opacity=0.8)


def draw_palm_details(art, fingers, thumb_joints):
    for mask, joints, width in fingers:
        for joint in (0, 1, 2):
            art.line(across(joints, max(joint, 1), width * 0.34) if joint else
                     spline([joints[0] + (-width * 0.4, 9), joints[0] + (0, 11),
                             joints[0] + (width * 0.4, 9)]), SKIN_LINE, 1.0, opacity=0.8)
        art.light(art.blob(joints[3] - (joints[3] - joints[2]) * 0.4, width * 0.42) * mask,
                  "#FFFFFF", 0.3)
    creases = ([(-22, -44), (-8, -40), (8, -42), (20, -38)],        # heart line
               [(-22, -38), (-8, -30), (6, -24), (14, -18)],        # head line
               [(-20, -40), (-8, -28), (-4, -12), (-6, 2)])         # life line
    for points in creases:
        art.line(spline(points), SKIN_LINE, 1.2, opacity=0.85)
    art.shadow(art.blob((-12, -18), 15), SKIN_SHADOW, 0.35)          # ball of the thumb
    art.shadow(art.blob((12, -22), 13), SKIN_SHADOW, 0.25)


def draw_cuff(art):
    """Sleeve end that hides where the forearm stops."""
    art.part(np.array([(-21, 22), (21, 22), (24, 68), (-24, 68)], float), CUFF, bulge=8)


def skin_part(art, mask, join=None):
    """Flat skin shape with its outline; no line is drawn inside `join` (the arm it
    grows from), so hand and arm read as one."""
    art.part(mask, SKIN, shade=False, outline=False)
    hidden = None if join is None else 1 - art.grow(join, -1.5)
    art.outline(mask, art.line_color(SKIN), clip=hidden)


def separate(art, mask, clip, width=1.6):
    """Mark where a finger or toe lies against its neighbour.

    An ink line does this in styles with line art; a thin dark seam along the
    same edge does it in every style, so digits stay countable in paint.
    """
    seam = mask * (1 - art.grow(mask, -1.4)) * clip
    art.shadow(seam, GAP_SHADOW, 0.9)
    art.outline(mask, SKIN_LINE, width, clip=clip)


def hand_mask(parts):
    """Silhouette of the whole hand from the result of hand_parts()."""
    palm, fingers, thumb, _ = parts
    return np.maximum.reduce([palm, thumb] + [mask for mask, _, _ in fingers])


def finish_hand(art, parts, pose=OPEN, palm_side=False):
    """Everything on top of the skin: seams between fingers, nails, wrinkles, creases.

    Use this alone when the hand's skin was painted as part of a larger limb
    (arm and hand as one mask), so the wrist carries no seam.
    """
    palm, fingers, thumb, thumb_joints = parts
    between = art.grow(hand_mask(parts), -2.5) * (1 - palm)
    for mask in [m for m, _, _ in fingers] + [thumb]:
        separate(art, mask, between)
    if palm_side:
        draw_palm_details(art, fingers, thumb_joints)
    else:
        draw_back_details(art, fingers, thumb_joints, pose)


def draw_hand(art, pose=OPEN, palm_side=False, join=None):
    """Draw a hand in local coordinates and return its mask."""
    parts = hand_parts(art, pose)
    palm, fingers, thumb, _ = parts
    whole = hand_mask(parts)
    skin_part(art, whole, join)
    art.form_shadow(np.maximum(palm, thumb), bulge=16, tint=SKIN_SHADOW)
    for mask in [m for m, _, _ in fingers] + [thumb]:
        art.form_shadow(mask, tint=SKIN_SHADOW, clip=1 - palm)
    finish_hand(art, parts, pose, palm_side)
    return whole


# Side view, thumb toward the viewer: knuckle, length, width, extra curl of each finger.
SIDE_FINGERS = (
    ((10.0, -40.0), 32.0, 9.0, 26.0),      # little, most curled, drawn first
    ((7.0, -45.0), 41.0, 10.0, 17.0),      # ring
    ((3.0, -47.0), 44.0, 10.5, 8.0),       # middle
    ((-2.0, -46.0), 40.0, 11.0, 0.0),      # index, in front
)
SIDE_CURL = (20.0, 32.0, 18.0)             # relaxed curl at the three joints


def draw_hand_side(art, curl=SIDE_CURL, join=None):
    """Relaxed hand seen from the thumb side, as it hangs beside the body."""
    palm = np.maximum(art.tube([(0, 14, 25), (1, -20, 31), (0, -48, 25)]), art.tube(WRIST[:2]))
    masks = [palm]
    for index, (base, length, width, extra) in enumerate(SIDE_FINGERS):
        joints = bone_chain(base, [length * share for share in PHALANGES], 6 + extra * 0.5,
                            [curl[0] + extra * 0.5, curl[1], curl[2]])
        mask = art.tube(limb(joints, (width, width * 0.95, width * 0.88, width * 0.78)))
        in_front = index == len(SIDE_FINGERS) - 1
        if in_front:                         # the index joins the palm without a seam
            mask = np.maximum(mask, palm)
        skin_part(art, mask, join)
        finger = art.tube(limb(joints, (width, width * 0.95, width * 0.88, width * 0.78)))
        art.shadow(finger * (1 - art.grow(finger, -1.4)) * (1 - palm), GAP_SHADOW, 0.7)
        if in_front:
            art.form_shadow(palm, bulge=14, tint=SKIN_SHADOW)
            for joint in (1, 2):
                art.line(across(joints, joint, 3.2), SKIN_LINE, 1.0, opacity=0.8)
        else:
            art.shadow(mask, SKIN_SHADOW, 0.55)              # fingers behind stay darker
        masks.append(mask)
    thumb = bone_chain((1, -4), THUMB_BONES, 14, (0, 8, 6))
    thumb_mask = art.part(art.tube(limb(thumb, (21, 14.5, 12.5, 10.5))), SKIN, shade=False)
    art.form_shadow(thumb_mask, tint=SKIN_SHADOW)
    art.shadow(thumb_mask * (1 - art.grow(thumb_mask, -1.4)) * art.ramp((0, 0), (0, -14)),
               GAP_SHADOW, 0.7)
    art.erase_line(art.threshold(art.blob((1, 0), 17), 0.25, 0.1))   # thumb root melts into palm
    art.line(across(thumb, 2, 4.0), SKIN_LINE, 1.0, opacity=0.8)
    return np.maximum.reduce(masks + [thumb_mask])


# pose, palm side, position of the wrist, angle, flip
STUDIES = (
    (OPEN, False, (200, 440), -6, False),
    (OPEN, True, (520, 440), 6, True),
    (POINTING, False, (300, 930), 10, False),
    (VICTORY, False, (690, 930), -4, False),
)
STUDY_SCALE = 3.0


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=1.0, light=(-0.45, -0.55, 0.70), seed=2)
    art.paint(art.everywhere(), "#EDE3D2")
    art.paint(art.blob((500, 420), 800), "#F7F0E3", 0.8)
    for pose, palm_side, wrist, angle, flip in STUDIES:
        with art.place(at=wrist, scale=STUDY_SCALE, angle=angle, flip=flip):
            art.focus_on(art.feather(draw_hand(art, pose, palm_side), 4) * 0.8)
            draw_cuff(art)
    with art.place(at=(830, 150), scale=STUDY_SCALE, angle=176):
        art.focus_on(art.feather(draw_hand_side(art), 4) * 0.8)
        draw_cuff(art)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
