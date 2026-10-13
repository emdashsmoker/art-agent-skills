#!/usr/bin/env python3
"""Full figure on the beach: an adult woman in a bikini, hand on hip.

    python swimwear_beach.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import background, rig_figure, studio
from codeillust.character import adult_face, default_character, figure_palette, long_windy_hair
from codeillust.config import Material, rgb

SCENE_NAME = "swimwear_beach"
HORIZON_Y = 560.0
SHORE_Y = 900.0
GROUND_Y = 1262.0
CLOUDS = [((830.0, 560.0), 520.0, 260.0, 50), ((140.0, 540.0), 360.0, 150.0, 30)]
SWIMSUIT = Material(base=rgb("#E8455A"), shadow=rgb("#8E1E44"), line=rgb("#4E0E26"), light=rgb("#FF8C8C"))
FIGURE = rig_figure.Figure(
    character=adult_face(replace(default_character(), palette=figure_palette(), hair=long_windy_hair())),
    pose=rig_figure.HAND_ON_HIP, pelvis=(500.0, 650.0), head_height=158.0,
    outfit=rig_figure.FigureOutfit.BIKINI, body=rig_figure.HOURGLASS, outfit_material=SWIMSUIT,
    ground_y=GROUND_Y)


def compose(painter):
    background.beach(painter.canvas, painter.light, HORIZON_Y, SHORE_Y, CLOUDS)
    rig_figure.draw_figure(painter, FIGURE)
    # Bright midday light: the portrait-style dark side would muddy the legs in painterly renders.
    painter.canvas.shade_subject_as_one = False


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, description=__doc__)
