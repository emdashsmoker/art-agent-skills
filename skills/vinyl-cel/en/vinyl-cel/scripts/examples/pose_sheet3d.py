#!/usr/bin/env python3
"""Pose sheet: every 3D pose preset without objects on the same figure, four rows.

    python pose_sheet3d.py --style anime --preview --out out/

Poses that place a hand on a target (hand on hip, arms crossed, think, peace,
point, cheer, hands behind) solve the arm by inverse kinematics, so they adapt
to any build. Poses on the floor (kneel, kneel_sit, lie_back, lie_front) are set down
on whichever body parts hang lowest, so the same ground line works for every row.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import background, head3d, rig3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character
from codeillust.config import rgb
from codeillust.figure3d import Figure3D, draw_figure3d, stool

SCENE_NAME = "pose_sheet3d"
CANVAS_UNITS = (1700.0, 3250.0)
ROWS = (("stand", "contrapposto", "hand_on_hip", "arms_crossed", "walk", "sit", "wave"),
        ("point", "think", "hands_behind", "cheer", "peace", "a_pose"),
        ("run", "hands_in_pockets", "kneel", "kneel_sit"))
FLOORS = (880.0, 1820.0, 2760.0)
SPACING = 225.0
YAW = 0.5
LYING = (("lie_back", 425.0, 1.35), ("lie_front", 1275.0, 1.15))   # name, pelvis x, yaw (a side view shows the length)
LYING_FLOOR = 3180.0
FIGURE = Figure3D(character=adult_face(default_character()), build=rig3d.FEMALE_AVERAGE, hair=head3d.PONYTAIL_HAIR,
                  outfit=wardrobe3d.OUTFITS["t_shirt_jeans"], head_height=105.0, yaw=YAW, head_scale=1.08)


def compose(painter):
    background.vertical_gradient(painter.canvas, rgb("#E9E4DC"), rgb("#C9C0B4"))
    for row, (names, floor) in enumerate(zip(ROWS, FLOORS)):
        for index, name in enumerate(names):
            props = (stool,) if name == "sit" else ()
            figure = replace(FIGURE, pose=rig3d.POSES[name], props=props, ground=floor,
                             position=(130.0 + index * SPACING, floor - 400.0))
            draw_figure3d(painter, figure)
    for name, x, yaw in LYING:
        draw_figure3d(painter, replace(FIGURE, pose=rig3d.POSES[name], yaw=yaw, ground=LYING_FLOOR,
                                       position=(x, LYING_FLOOR - 100.0)))
    painter.canvas.shade_subject_as_one = False


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
