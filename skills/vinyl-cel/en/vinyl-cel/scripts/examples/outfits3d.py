#!/usr/bin/env python3
"""Wardrobe sheet: the women's and men's outfit presets on the four body builds.

    python outfits3d.py --style anime --preview --out out/

Outfits are layered garments (wardrobe3d.GARMENTS) made as offset copies of the
body, so any outfit fits any build and pose.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import background, head3d, rig3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, male_face
from codeillust.config import Material, rgb
from codeillust.figure3d import Figure3D, draw_figure3d

SCENE_NAME = "outfits3d"
CANVAS_UNITS = (1600.0, 1900.0)
FLOORS = (900.0, 1830.0)
SPACING = 225.0
YAW = 0.45
DARK_HAIR = Material(base=rgb("#3A2E2C"), shadow=rgb("#1C1416"), line=rgb("#0E0A0C"), accent=rgb("#5A4844"),
                     light=rgb("#7A6460"))
WOMAN = adult_face(default_character())
MAN = male_face(replace(default_character(), palette=replace(default_character().palette, hair=DARK_HAIR,
                                                             hair_highlight=rgb("#8A7A76"))))
ROWS = (
    ((WOMAN, "crop_top_hot_pants", rig3d.FEMALE_FULLER, head3d.LONG_HAIR, "contrapposto"),
     (WOMAN, "hoodie_jeans", rig3d.FEMALE_AVERAGE, head3d.PONYTAIL_HAIR, "stand"),
     (WOMAN, "hoodie_shorts", rig3d.FEMALE_AVERAGE, head3d.BOB_HAIR, "peace"),
     (WOMAN, "tank_top_jeans", rig3d.FEMALE_FULLER, head3d.PONYTAIL_HAIR, "hand_on_hip"),
     (WOMAN, "sundress", rig3d.FEMALE_AVERAGE, head3d.LONG_HAIR, "hands_behind"),
     (WOMAN, "bikini", rig3d.FEMALE_FULLER, head3d.LONG_HAIR, "contrapposto"),
     (WOMAN, "t_shirt_jeans", rig3d.FEMALE_AVERAGE, head3d.BOB_HAIR, "think")),
    ((MAN, "shirt_trousers", rig3d.MALE_SLIM, head3d.MALE_MEDIUM_HAIR, "point"),
     (MAN, "swim_trunks", rig3d.MALE_ATHLETIC, head3d.MALE_SHORT_HAIR, "cheer"),
     (MAN, "suit", rig3d.MALE_ATHLETIC, head3d.MALE_SHORT_HAIR, "stand"),
     (MAN, "suit", rig3d.MALE_SLIM, head3d.MALE_MEDIUM_HAIR, "arms_crossed"),
     (MAN, "t_shirt_jeans", rig3d.MALE_ATHLETIC, head3d.MALE_SHORT_HAIR, "hand_on_hip"),
     (MAN, "hoodie_jeans", rig3d.MALE_SLIM, head3d.MALE_MEDIUM_HAIR, "walk")),
)


def compose(painter):
    background.vertical_gradient(painter.canvas, rgb("#E9E4DC"), rgb("#C9C0B4"))
    for row, floor in zip(ROWS, FLOORS):
        for index, (character, outfit, build, hair, pose) in enumerate(row):
            draw_figure3d(painter, Figure3D(character=character, build=build, pose=rig3d.POSES[pose], hair=hair,
                                            outfit=wardrobe3d.OUTFITS[outfit], position=(130.0 + index * SPACING, 500.0),
                                            head_height=110.0, yaw=YAW, ground=floor))
    painter.canvas.shade_subject_as_one = False


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
