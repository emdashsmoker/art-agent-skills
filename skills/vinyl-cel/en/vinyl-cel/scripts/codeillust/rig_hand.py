"""Hand rig: palm plus jointed fingers, built for the relief renderer.

Lengths are in hand units (wrist to middle fingertip = 1). The hand frame has
its origin at the wrist, +y toward the fingers and +x toward the thumb.
Finger proportions are fixed here, so a pose can only bend a hand, never
deform it.
"""
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .geometry import Frame, Taper, catmull_rom, ellipse, ribbon
from .relief import FRONT

# name: (knuckle x, knuckle y, length, width)
FINGERS = {
    "index": (0.150, 0.555, 0.385, 0.104),
    "middle": (0.048, 0.578, 0.425, 0.106),
    "ring": (-0.054, 0.558, 0.398, 0.100),
    "pinky": (-0.150, 0.505, 0.312, 0.088),
}
PHALANX_SHARES = (0.47, 0.30, 0.23)
THUMB_BASE = (0.125, 0.100)
THUMB_SEGMENTS = (0.240, 0.165, 0.150)      # metacarpal (inside the ball of the thumb), proximal, distal
THUMB_WIDTHS = (0.150, 0.124, 0.112, 0.094)
PALM_OUTLINE = ((-0.160, 0.00), (0.160, 0.00), (0.228, 0.16), (0.222, 0.40), (0.208, 0.555),
                (0.050, 0.605), (-0.120, 0.572), (-0.202, 0.505), (-0.226, 0.25))
PALM_THICKNESS = 0.42          # a palm is much flatter than it is wide
FINGER_TIP_TAPER = 0.82        # fingertip width as a share of the finger width
NAIL_SIZE = (0.62, 0.52)       # share of fingertip width, share of last phalanx length
# heart line, head line, life line (curves around the ball of the thumb)
PALM_CREASES = (((-0.205, 0.425), (-0.06, 0.445), (0.075, 0.525)), ((0.200, 0.415), (0.05, 0.36), (-0.13, 0.285)),
                ((0.190, 0.435), (0.075, 0.33), (0.035, 0.18), (0.045, 0.04)))
PALM_CREASE_OPACITY = 0.32
KNUCKLE_BUMP = 0.16            # share of a full hemisphere


class HandView(str, Enum):
    PALM = "palm"   # palm faces the viewer
    BACK = "back"   # back of the hand faces the viewer


@dataclass(frozen=True)
class HandPose:
    """spread: sideways angle at each knuckle (radians, positive toward the thumb).
    curl: 0 straight .. 1 folded into the palm. bend: in-plane curve of a finger."""

    spread: dict = field(default_factory=lambda: {"index": 0.10, "middle": 0.02, "ring": -0.07, "pinky": -0.17})
    curl: dict = field(default_factory=lambda: {"index": 0.0, "middle": 0.0, "ring": 0.0, "pinky": 0.0})
    bend: float = 0.0
    thumb_angle: float = 0.70     # radians away from the finger direction
    thumb_curl: float = 0.10


OPEN_HAND = HandPose(spread={"index": 0.17, "middle": 0.03, "ring": -0.11, "pinky": -0.27}, thumb_angle=0.80)
RELAXED_HAND = HandPose(spread={"index": 0.03, "middle": 0.0, "ring": -0.04, "pinky": -0.09},
                        curl={"index": 0.22, "middle": 0.30, "ring": 0.36, "pinky": 0.42}, bend=0.10,
                        thumb_angle=0.48, thumb_curl=0.22)
VICTORY_HAND = HandPose(spread={"index": 0.24, "middle": -0.10, "ring": -0.10, "pinky": -0.20},
                        curl={"index": 0.0, "middle": 0.0, "ring": 0.93, "pinky": 0.93},
                        thumb_angle=-0.15, thumb_curl=0.55)


def _capsule(start, end, width_start, width_end, samples=10):
    """Finger segment with round ends."""
    t = np.linspace(0.0, 1.0, samples)[:, None]
    center = np.asarray(start) * (1 - t) + np.asarray(end) * t
    body = ribbon(center, np.linspace(width_start, width_end, samples))
    return [body, ellipse(start, width_start / 2, width_start / 2, samples=24),
            ellipse(end, width_end / 2, width_end / 2, samples=24)]


def _finger_segments(name, pose):
    """Joint positions of one finger in hand units, shortened by curl (foreshortening)."""
    x, y, length, width = FINGERS[name]
    curl = pose.curl[name]
    angle = pose.spread[name]
    points = [np.array([x, y])]
    for index, share in enumerate(PHALANX_SHARES):
        # Curling toward the viewer shortens what is seen; later joints curl more.
        fold = np.clip(curl * (0.9 + 0.5 * index), 0.0, 1.45)
        visible = length * share * max(np.cos(fold), 0.12)
        angle += pose.bend * (0.6 + 0.4 * index) * (-1 if x > 0 else 1) * 0.5
        direction = np.array([np.sin(angle), np.cos(angle)])
        points.append(points[-1] + direction * visible)
    return points, width


def _thumb_segments(pose):
    points = [np.array(THUMB_BASE)]
    angle = pose.thumb_angle
    for index, length in enumerate(THUMB_SEGMENTS):
        direction = np.array([np.sin(angle), np.cos(angle)])
        points.append(points[-1] + direction * length * (1.0 - 0.25 * pose.thumb_curl * index))
        angle -= pose.thumb_curl * 0.9
    return points


def draw_hand(relief, painter, frame, material, pose=RELAXED_HAND, view=HandView.BACK, mirror=False,
              name="hand", depth=0.0, nail_color=None, detail_color=None, turn=1.0):
    """Add a hand to the relief. frame maps hand units to the canvas (scale = hand length).

    mirror=True flips the thumb to the other side (the other hand).
    turn narrows the hand as it rotates edge-on to the viewer: 1.0 flat to the
    viewer, about 0.6 for a hand hanging at the side of a standing figure.
    Returns a callable that draws nails or palm creases; call it after relief.render().
    """
    canvas = relief.canvas
    flip = np.array([(-1.0 if mirror else 1.0) * turn, 1.0])

    def place(points):
        return frame.apply(np.asarray(points, dtype=np.float64) * flip)

    palm = canvas.mask(catmull_rom(place(PALM_OUTLINE), closed=True))
    relief.add(name, palm, material, thickness=PALM_THICKNESS, depth=depth)

    fingertips = {}
    # Folded fingers lie on the palm: in a palm view they are in front, in a back view behind.
    order = sorted(FINGERS, key=lambda n: pose.curl[n])
    for finger in order:
        points, width = _finger_segments(finger, pose)
        widths = np.linspace(width, width * FINGER_TIP_TAPER, len(points)) * frame.scale
        shapes = []
        for index in range(len(points) - 1):
            shapes += _capsule(place([points[index]])[0], place([points[index + 1]])[0],
                               widths[index], widths[index + 1])
        folded = pose.curl[finger] > 0.6
        finger_depth = FRONT if folded and view is HandView.PALM else depth
        relief.add(name, canvas.mask(*shapes), material, depth=finger_depth)
        if view is HandView.BACK:
            knuckle = ellipse(place([points[0]])[0], width * frame.scale * 0.56, width * frame.scale * 0.50)
            relief.bump(canvas.mask(knuckle), KNUCKLE_BUMP)
        fingertips[finger] = (points[-2], points[-1], widths[-1], folded)

    thumb = _thumb_segments(pose)
    thumb_widths = np.array(THUMB_WIDTHS) * frame.scale
    shapes = []
    for index in range(len(thumb) - 1):
        shapes += _capsule(place([thumb[index]])[0], place([thumb[index + 1]])[0],
                           thumb_widths[index], thumb_widths[index + 1])
    thumb_over_palm = pose.thumb_angle < 0.2
    thumb_depth = FRONT if thumb_over_palm and view is HandView.PALM else depth
    relief.add(name, canvas.mask(*shapes), material, depth=thumb_depth)
    fingertips["thumb"] = (thumb[-2], thumb[-1], thumb_widths[-1], False)

    def finish():
        if view is HandView.BACK:
            _draw_nails(painter, place, fingertips, nail_color, material, relief.visible(name))
        else:
            color = material.line if detail_color is None else detail_color
            for crease in PALM_CREASES:
                painter.stroke(catmull_rom(place(crease)), frame.scale * 0.009, color, Taper.BOTH,
                               PALM_CREASE_OPACITY, clip=relief.visible(name))

    return finish


def _draw_nails(painter, place, fingertips, nail_color, material, visible):
    color = (material.light if material.light is not None else material.base) if nail_color is None else nail_color
    canvas = painter.canvas
    for joint, tip, width, folded in fingertips.values():
        if folded:
            continue
        joint_c, tip_c = place([joint])[0], place([tip])[0]
        axis = tip_c - joint_c
        length = np.linalg.norm(axis) + 1e-9
        center = joint_c + axis * 0.72
        rotation = np.arctan2(axis[1], axis[0]) - np.pi / 2
        nail = Frame(center, 1.0, rotation).apply(
            ellipse((0.0, 0.0), width * NAIL_SIZE[0] / 2, length * NAIL_SIZE[1] / 2, samples=24))
        mask = canvas.mask(nail) * visible     # a hand hidden behind cloth shows no nails
        canvas.blend(mask, color, 0.75)
        canvas.blend(np.clip(mask - np.roll(mask, 1, axis=0), 0.0, 1.0), material.line, 0.35)
