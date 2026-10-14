#!/usr/bin/env python3
"""Hand study: three poses on toned paper.

    python hand_study.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
import numpy as np

from codeillust import rig_hand, studio
from codeillust.character import default_palette
from codeillust.config import rgb
from codeillust.geometry import Frame, ribbon
from codeillust.relief import Relief

SCENE_NAME = "hand_study"
CANVAS_UNITS = (1333.0, 1000.0)
PAPER = rgb("#D9C9B2")
PAPER_SHADE = rgb("#B9A68E")
HAND_LENGTH = 500.0
FOREARM_LENGTH = 420.0          # how much arm is shown below each wrist
FOREARM_WIDTHS = (0.30, 0.44)
FOREARM_THICKNESS = 0.62        # matches the palm so the wrist shows no step   # share of the hand length at the wrist and at the cut
UP = np.pi                      # hand frame rotation that points the fingers up the page
# (wrist position, rotation, pose, view, mirror)
HANDS = [
    ((290.0, 800.0), UP - 0.10, rig_hand.OPEN_HAND, rig_hand.HandView.PALM, False),
    ((690.0, 240.0), 0.10, rig_hand.RELAXED_HAND, rig_hand.HandView.BACK, False),
    ((1050.0, 820.0), UP + 0.08, rig_hand.VICTORY_HAND, rig_hand.HandView.PALM, True),
]


def compose(painter):
    canvas = painter.canvas
    canvas.rgb[:] = PAPER
    canvas.blend(canvas.noise(300.0, octaves=3) * 0.5, PAPER_SHADE)
    skin = default_palette().skin
    relief = Relief(canvas)
    finishers = []
    for index, (wrist, rotation, pose, view, mirror) in enumerate(HANDS):
        frame = Frame(wrist, HAND_LENGTH, rotation)
        arm_end = frame.apply([(0.0, -FOREARM_LENGTH / HAND_LENGTH)])[0]
        arm = ribbon(np.linspace(wrist, arm_end, 12), np.linspace(*FOREARM_WIDTHS, 12) * HAND_LENGTH)
        relief.add(f"hand{index}", canvas.mask(arm), skin, thickness=FOREARM_THICKNESS)
        finishers.append(rig_hand.draw_hand(relief, painter, frame, skin, pose, view, mirror, name=f"hand{index}"))
    relief.render(painter)
    for finish in finishers:
        finish()
    canvas.importance = np.clip(relief.cover * 0.8, 0.0, 1.0)
    canvas.shade_subject_as_one = False      # three separate studies, not one figure


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
