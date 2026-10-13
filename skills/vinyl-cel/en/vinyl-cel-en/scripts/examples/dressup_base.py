#!/usr/bin/env python3
"""Dress-up base: one body in the neutral A-pose, shown in every registered outfit.

Each panel is the same Figure with only `outfit` changed, which is the point of
the base: the body is built once and outfits are layers on top of it.

    python dressup_base.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import background, rig_figure, studio
from codeillust.character import adult_face, default_character, figure_palette, long_straight_hair
from codeillust.config import rgb

SCENE_NAME = "dressup_base"
CANVAS_UNITS = (1333.0, 1000.0)
BACKDROP = (rgb("#E9E4DC"), rgb("#CFC6BA"))
HEAD_HEIGHT = 120.0                 # 7.5 heads fill the canvas height with a small margin
PELVIS_Y = 470.0
GROUND_Y = 935.0
BASE = rig_figure.Figure(
    character=adult_face(replace(default_character(), palette=figure_palette(), hair=long_straight_hair())),
    pose=rig_figure.A_POSE, head_height=HEAD_HEIGHT, body=rig_figure.HOURGLASS, ground_y=GROUND_Y)
PANELS = [(380.0, rig_figure.FigureOutfit.BIKINI), (950.0, rig_figure.FigureOutfit.SUNDRESS)]


def compose(painter):
    canvas = painter.canvas
    background.vertical_gradient(canvas, *BACKDROP)
    for pelvis_x, outfit in PANELS:
        rig_figure.draw_figure(painter, replace(BASE, pelvis=(pelvis_x, PELVIS_Y), outfit=outfit))
    canvas.shade_subject_as_one = False      # two separate figures


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
