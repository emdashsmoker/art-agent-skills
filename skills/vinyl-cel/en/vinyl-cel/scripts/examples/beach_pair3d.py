#!/usr/bin/env python3
"""Finished 3D figure scene: an adult couple on the beach, she in a bikini, he waving.

    python beach_pair3d.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import background, head3d, rig3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette, male_face
from codeillust.config import Material, rgb
from codeillust.figure3d import Figure3D, draw_figure3d

SCENE_NAME = "beach_pair3d"
HORIZON_Y = 540.0
SHORE_Y = 860.0
FLOOR_Y = 1250.0
CLOUDS = [((820.0, 540.0), 520.0, 250.0, 50), ((150.0, 520.0), 360.0, 150.0, 30)]
SWIMSUIT = Material(base=rgb("#E8455A"), shadow=rgb("#8E1E44"), line=rgb("#4E0E26"), light=rgb("#FF8C8C"))
TRUNKS = Material(base=rgb("#2E8FB8"), shadow=rgb("#145878"), line=rgb("#08283A"), light=rgb("#6EC4E4"))
DARK_HAIR = Material(base=rgb("#2E2422"), shadow=rgb("#140E10"), line=rgb("#0A0608"), accent=rgb("#4A3C38"),
                     light=rgb("#6A5652"))
WOMAN = adult_face(replace(default_character(), palette=figure_palette()))
MAN = male_face(replace(default_character(), palette=replace(figure_palette(), hair=DARK_HAIR,
                                                             hair_highlight=rgb("#7A6A66"))))
HER = Figure3D(character=WOMAN, build=rig3d.FEMALE_FULLER, pose=rig3d.HAND_ON_HIP, hair=head3d.LONG_HAIR,
               outfit=replace(wardrobe3d.OUTFITS["bikini"], colors={"top": SWIMSUIT}),
               position=(340.0, 600.0), head_height=128.0, yaw=0.45, ground=FLOOR_Y)
HIM = Figure3D(character=MAN, build=rig3d.MALE_ATHLETIC, pose=rig3d.WAVE, hair=head3d.MALE_SHORT_HAIR,
               outfit=replace(wardrobe3d.OUTFITS["swim_trunks"], colors={"bottom": TRUNKS}),
               position=(690.0, 560.0), head_height=134.0, yaw=-0.35, ground=FLOOR_Y - 30.0)


def compose(painter):
    background.beach(painter.canvas, painter.light, HORIZON_Y, SHORE_Y, CLOUDS)
    draw_figure3d(painter, HIM)        # he stands a step further back, so he is drawn first
    draw_figure3d(painter, HER)
    painter.canvas.shade_subject_as_one = False


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, description=__doc__)
