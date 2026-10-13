#!/usr/bin/env python3
"""Character turnaround: one adult woman from five angles, front to back.

    python turnaround3d.py --style all --preview --out out/

The figure is built in 3D (rig3d, head3d, wardrobe3d), so every angle comes
from the same body, outfit and hair; only the camera yaw changes.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

import numpy as np

from codeillust import background, head3d, rig3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character
from codeillust.config import rgb
from codeillust.figure3d import Figure3D, draw_figure3d

SCENE_NAME = "turnaround3d"
CANVAS_UNITS = (1600.0, 1100.0)
FLOOR_Y = 1010.0
SPACING = 300.0
YAWS = (0.0, 0.75, np.pi / 2, 2.35, np.pi)          # front, three-quarter, side, back three-quarter, back
FIGURE = Figure3D(character=adult_face(default_character()), build=rig3d.FEMALE_FULLER, pose=rig3d.CONTRAPPOSTO,
                  hair=head3d.LONG_HAIR, outfit=wardrobe3d.OUTFITS["crop_top_hot_pants"], head_height=118.0,
                  ground=FLOOR_Y)


def compose(painter):
    background.vertical_gradient(painter.canvas, rgb("#EEE8DE"), rgb("#CFC5B6"))
    for index, yaw in enumerate(YAWS):
        draw_figure3d(painter, replace(FIGURE, yaw=yaw, position=(200.0 + index * SPACING, 500.0)))
    painter.canvas.shade_subject_as_one = False


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
