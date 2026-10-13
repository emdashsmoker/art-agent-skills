#!/usr/bin/env python3
"""Full figure: a young woman in a sundress, standing with a hand on her hip.

    python full_body.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

from codeillust import background, rig_figure, studio
from codeillust.character import default_character
from codeillust.config import rgb

SCENE_NAME = "full_body"
GROUND_Y = 1262.0
FIGURE = rig_figure.Figure(
    character=replace(default_character(), eye_half_width=0.21),
    pose=rig_figure.HAND_ON_HIP, pelvis=(500.0, 650.0), head_height=158.0,
    outfit=rig_figure.FigureOutfit.SUNDRESS, ground_y=GROUND_Y, head_scale=1.18)
CLOUDS = [((820.0, 760.0), 520.0, 300.0, 50), ((150.0, 620.0), 380.0, 180.0, 30)]
GROUND = (rgb("#8CCB62"), rgb("#4FA255"))


def compose(painter):
    canvas = painter.canvas
    background.summer_sky(canvas, CLOUDS, painter.light)
    _, ys = canvas.grid()
    ground = ys > GROUND_Y - 190.0
    depth = ((ys - (GROUND_Y - 190.0)) / 260.0).clip(0, 1)[..., None]
    canvas.blend(ground.astype("float32"), GROUND[0] * (1 - depth) + GROUND[1] * depth)
    rig_figure.draw_figure(painter, FIGURE)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, description=__doc__)
