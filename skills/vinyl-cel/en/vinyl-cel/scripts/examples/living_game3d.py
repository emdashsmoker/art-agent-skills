#!/usr/bin/env python3
"""Living room scene: a man playing a video game on the sofa, a woman beside him with a mug.

    python living_game3d.py --style all --preview --out out/

The television shows a lit game screen; the controller is held in both hands (rig3d.SIT_GAME with
props3d.held_controller), the mug in one hand (rig3d.SIT_MUG with props3d.held_mug).
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import head3d, interior, props3d, rig3d, scene3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette, male_face
from codeillust.config import Material, rgb
from codeillust.figure3d import Figure3D

SCENE_NAME = "living_game3d"
ROOM = interior.living_room()
SOFA = ROOM.places["sofa"]
DARK_HAIR = Material(base=rgb("#2E2422"), shadow=rgb("#140E10"), line=rgb("#0A0608"), accent=rgb("#4A3C38"),
                     light=rgb("#6A5652"))
HOODIE = wardrobe3d.fabric("#5E8F7A", "#2E5646", "#142A22", "#8EC0AA")
MAN = male_face(replace(default_character(), palette=replace(figure_palette(), hair=DARK_HAIR,
                                                             hair_highlight=rgb("#7A6A66"))))
GAMER = Figure3D(character=MAN, build=rig3d.MALE_SLIM, pose=rig3d.SIT_GAME, hair=head3d.MALE_MEDIUM_HAIR,
                 outfit=replace(wardrobe3d.OUTFITS["hoodie_jeans"],
                                colors={"top": HOODIE, "trim": wardrobe3d.fabric("#4E7C68", "#284A3C", "#12241C"),
                                        "bottom": wardrobe3d.DENIM, "shoes": wardrobe3d.WHITE, "sole": wardrobe3d.GREY}),
                 props=(props3d.held_controller(),))
WOMAN = Figure3D(character=adult_face(replace(default_character(), palette=figure_palette())),
                 build=rig3d.FEMALE_AVERAGE, pose=rig3d.SIT_MUG, hair=head3d.LONG_HAIR, head_scale=1.08,
                 outfit=replace(wardrobe3d.OUTFITS["t_shirt_jeans"],
                                colors={"top": wardrobe3d.fabric("#F2C6C8", "#B48288", "#5E3A42", "#FFE4E6"),
                                        "bottom": wardrobe3d.fabric("#3A4A6E", "#1C2640", "#0C1222", "#5E70A0"),
                                        "shoes": wardrobe3d.WHITE, "sole": wardrobe3d.GREY}),
                 props=(props3d.held_mug(body=props3d.surface("#F4C95D", "#B08A2A", "#5A4410", "#FFE89A")),))
CAMERA = scene3d.SceneCamera(target=(0.0, -3.2, -2.4), origin=(666.0, 560.0), scale=70.0, yaw=-0.24, pitch=0.14,
                             distance=20.0)
CANVAS_UNITS = (1333.0, 1000.0)          # landscape: the sofa and the television face each other across the room


def compose(painter):
    items = [scene3d.seated(GAMER, SOFA, "seat_1"), scene3d.seated(WOMAN, SOFA, "seat_0")]
    interior.draw_room(painter, CAMERA, ROOM, items)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
