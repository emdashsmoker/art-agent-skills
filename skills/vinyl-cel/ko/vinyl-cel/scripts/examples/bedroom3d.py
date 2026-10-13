#!/usr/bin/env python3
"""Bedroom scene: a woman lying on her front on the bed, chin on her hands, with a laptop and a glass of
juice beside her.

    python bedroom3d.py --style all --preview --out out/

A figure lying down is set onto the bed by the parts of the body that hang lowest (figure3d.ground_points),
so the pose needs no height of its own: Placed.at is a point on the mattress.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

import numpy as np

from codeillust import head3d, interior, props3d, rig3d, scene3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character
from codeillust.figure3d import Figure3D

SCENE_NAME = "bedroom3d"
ROOM = interior.bedroom()
BED = ROOM.places["bed"]
LOUNGEWEAR = wardrobe3d.Outfit3D(("trousers", "hoodie"),
                                 {"top": wardrobe3d.fabric("#E8B850", "#A87A2A", "#5A3E12", "#FFDC8A"),
                                  "trim": wardrobe3d.fabric("#D8A440", "#986C22", "#4E340E"),
                                  "bottom": wardrobe3d.GREY})
WOMAN = Figure3D(character=replace(adult_face(default_character()), smile=0.55, gaze=(0.0, 0.08)),
                 build=rig3d.FEMALE_AVERAGE, pose=rig3d.LIE_FRONT, hair=head3d.LONG_HAIR, head_scale=1.08,
                 outfit=LOUNGEWEAR)
WOMAN_AT = (0.0, -1.2)                    # x, z of her pelvis on the mattress (bed frame); she faces the foot end
LAPTOP_AT = (1.1, 0.8, np.pi - 0.6)       # x, z from the middle of the duvet and turn: open toward her face
GLASS_AT = (-0.45, 0.0, 0.25)             # on the nightstand, beside the lamp
CAMERA = scene3d.SceneCamera(target=(0.6, -2.6, -0.6), origin=(666.0, 520.0), scale=125.0, yaw=0.62, pitch=0.36,
                             distance=16.0)
CANVAS_UNITS = (1333.0, 1000.0)          # landscape: a bed is wider than it is tall


def compose(painter):
    x, z, turn = LAPTOP_AT
    at = np.asarray(scene3d.anchor(BED, "lie_front")) + scene3d.rot_y(BED.yaw) @ np.array([WOMAN_AT[0], 0.0, WOMAN_AT[1]])
    items = [scene3d.Placed(WOMAN, at=tuple(at), yaw=BED.yaw),
             scene3d.on_top(props3d.laptop(lid_angle=1.85, screen="video"), BED, offset=(x, 0.0, z), yaw=turn,
                            key="duvet"),
             scene3d.on_top(props3d.drinking_glass(0.6), ROOM.places["nightstand"], offset=GLASS_AT)]
    interior.draw_room(painter, CAMERA, ROOM, items)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
