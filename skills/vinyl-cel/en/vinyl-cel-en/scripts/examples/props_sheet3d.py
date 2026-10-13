#!/usr/bin/env python3
"""Object sheet: every modern object of props3d on one table-less floor, in one perspective (the glass is clear).

    python props_sheet3d.py --style anime --preview --out out/

A catalogue for picking objects and checking them after a change. The objects stand on the floor
plane of one SceneCamera, so the rows recede toward a common vanishing point.
"""
import _toolkit  # noqa: F401  (sets the import path)

from codeillust import background, props3d, scene3d, studio
from codeillust.config import rgb

SCENE_NAME = "props_sheet3d"
CANVAS_UNITS = (1400.0, 1000.0)
TURN = 0.25                      # every object is turned a little so its sides show
ROWS = ((("television", -0.3, -2.8),),
        (("monitor", -3.4, -0.6), ("keyboard", -0.4, -0.4), ("mouse", 1.3, -0.4), ("laptop", 3.6, -0.6)),
        (("tablet", -3.6, 1.3), ("phone", -1.6, 1.3), ("headphones", 0.0, 1.3), ("game_controller", 1.9, 1.9),
         ("mug", 3.0, 1.3), ("paper_cup", 4.0, 1.3)),
        (("book_stack", -3.2, 3.2), ("desk_lamp", -1.0, 3.2), ("potted_plant", 1.0, 3.4), ("drinking_glass", 2.6, 3.3)))
CABLE = ((3.4, 0.0, 2.9), (4.3, 0.0, 3.1), (3.9, 0.0, 3.7), (4.7, 0.0, 4.0))   # a loose cable on the floor
CAMERA = scene3d.SceneCamera(target=(0.0, -0.6, 0.4), origin=(700.0, 520.0), scale=118.0, pitch=0.42, distance=26.0)


def compose(painter):
    background.vertical_gradient(painter.canvas, rgb("#E9E4DC"), rgb("#C9C0B4"))
    items = [scene3d.Placed(getattr(props3d, name)(), at=(x, 0.0, z), yaw=0.0 if name == "television" else TURN)
             for row in ROWS for name, x, z in row]
    scene3d.draw_scene3d(painter, CAMERA, items + [scene3d.Placed(props3d.cable(CABLE))])
    painter.canvas.shade_subject_as_one = False


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
