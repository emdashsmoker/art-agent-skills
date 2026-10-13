#!/usr/bin/env python3
"""Office scene: a woman typing on a laptop at a desk by the windows.

    python desk_worker3d.py --style all --preview --out out/

The figure, the chair, the desk and the laptop share one scene camera and one depth buffer, so the
desk hides her legs and her hands rest on the keys in front of her body.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import head3d, interior, props3d, rig3d, scene3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette
from codeillust.figure3d import Figure3D

SCENE_NAME = "desk_worker3d"
ROOM = interior.office()
DESK, CHAIR = ROOM.places["desk"], ROOM.places["chair"]
LAPTOP_DEPTH = 0.92        # head heights from the desk centre toward the user (keys about one head in front of her)
BLOUSE = wardrobe3d.fabric("#F3EEE6", "#B9B2C4", "#5E5A6C", "#FFFFFF")
SLACKS = wardrobe3d.fabric("#3E4A62", "#1E2638", "#0C101C", "#62708E")
WORKER = Figure3D(character=replace(adult_face(replace(default_character(), palette=figure_palette())),
                                    gaze=(0.0, 0.10), eye_open=0.9),
                  build=rig3d.FEMALE_AVERAGE, pose=rig3d.SIT_TYPE, hair=head3d.PONYTAIL_HAIR, head_scale=1.08,
                  outfit=replace(wardrobe3d.OUTFITS["t_shirt_jeans"],
                                 colors={"top": BLOUSE, "bottom": SLACKS, "shoes": wardrobe3d.BLACK,
                                         "sole": wardrobe3d.GREY}))
CAMERA = scene3d.SceneCamera(target=(-0.8, -3.3, -3.2), origin=(500.0, 660.0), scale=140.0, yaw=0.62, pitch=0.13,
                             distance=20.0)


def compose(painter):
    items = [scene3d.seated(WORKER, CHAIR),
             scene3d.on_top(props3d.laptop(lid_angle=1.85, screen="code"), DESK, offset=(0.0, 0.0, LAPTOP_DEPTH))]
    interior.draw_room(painter, CAMERA, ROOM, items)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, description=__doc__)
