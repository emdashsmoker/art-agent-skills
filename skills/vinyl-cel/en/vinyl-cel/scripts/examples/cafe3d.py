#!/usr/bin/env python3
"""Cafe scene: a woman at a window table checking her phone, a take-away cup in front of her.

    python cafe3d.py --style all --preview --out out/

The phone is held by props3d.held_phone in the rig3d.SIT_PHONE pose; its screen faces her, so the
camera sees its back and her fingers round it.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import head3d, interior, props3d, rig3d, scene3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette
from codeillust.config import Material, rgb
from codeillust.figure3d import Figure3D

SCENE_NAME = "cafe3d"
ROOM = interior.cafe()
TABLE, CHAIR = ROOM.places["table"], ROOM.places["chair_2"]
AUBURN = Material(base=rgb("#8A4A32"), shadow=rgb("#4E2418"), line=rgb("#2A120C"), accent=rgb("#A65E42"),
                  light=rgb("#C88866"))
CARDIGAN = wardrobe3d.fabric("#D8C0A0", "#9A7E64", "#4E3E30", "#F4E2C8")
WOMAN = Figure3D(character=replace(adult_face(replace(default_character(),
                                                      palette=replace(figure_palette(), hair=AUBURN,
                                                                      hair_highlight=rgb("#E0A88A")))),
                                   gaze=(0.0, 0.12), eye_open=0.85, smile=0.6),
                 build=rig3d.FEMALE_AVERAGE, pose=rig3d.SIT_PHONE, hair=head3d.BOB_HAIR, head_scale=1.08,
                 outfit=wardrobe3d.Outfit3D(("skirt", "hoodie", "flats"),
                                            {"top": CARDIGAN, "trim": wardrobe3d.fabric("#C4AA88", "#8A6E54", "#463626"),
                                             "bottom": wardrobe3d.OLIVE,
                                             "shoes": wardrobe3d.fabric("#8A5A3C", "#4E2E1C", "#24140C")}),
                 props=(props3d.held_phone(screen="chat"),))
CAMERA = scene3d.SceneCamera(target=(-2.6, -3.3, -2.0), origin=(500.0, 660.0), scale=118.0, yaw=0.38, pitch=0.12,
                             distance=18.0)


def compose(painter):
    items = [scene3d.seated(WOMAN, CHAIR),
             scene3d.on_top(props3d.paper_cup(), TABLE, offset=(0.75, 0.0, 0.5)),
             scene3d.on_top(props3d.book(cover=props3d.BOOK_COLORS[3]), TABLE, offset=(-0.6, 0.0, 0.1), yaw=0.5),
             scene3d.on_top(props3d.drinking_glass(0.7), TABLE, offset=(0.3, 0.0, 0.65))]
    interior.draw_room(painter, CAMERA, ROOM, items)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, description=__doc__)
