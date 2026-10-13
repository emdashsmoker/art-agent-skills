#!/usr/bin/env python3
"""Still life: bottle, jug and fruit on a wooden table.

    python still_life.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
import numpy as np

from codeillust import stilllife as sl
from codeillust import studio
from codeillust.config import rgb
from codeillust.relief import Relief

SCENE_NAME = "still_life"
CANVAS_UNITS = (1333.0, 1000.0)
TABLE_BACK_Y = 610.0
TABLE_FRONT_Y = 930.0
CLOTH_OUTLINE = [(560.0, 660.0), (900.0, 640.0), (1260.0, 700.0), (1380.0, 860.0), (1300.0, 1040.0),
                 (900.0, 1050.0), (640.0, 960.0), (480.0, 800.0)]
BOTTLE = dict(axis_x=400.0, top_y=130.0, bottom_y=700.0,
              radius_points=[(0.0, 24.0), (0.05, 30.0), (0.08, 25.0), (0.36, 27.0), (0.56, 84.0), (1.0, 84.0)])
JUG = dict(axis_x=770.0, top_y=330.0, bottom_y=730.0,
           radius_points=[(0.0, 62.0), (0.12, 48.0), (0.50, 128.0), (0.82, 104.0), (1.0, 74.0)])
PEAR = dict(axis_x=560.0, top_y=650.0, bottom_y=830.0, base_roundness=0.75, top_roundness=0.8, mottle=0.6,
            radius_points=[(0.0, 14.0), (0.18, 32.0), (0.45, 44.0), (0.78, 78.0), (1.0, 64.0)])
JUG_BAND = (470.0, 500.0, rgb("#3A5FA8"))
LABEL = (470.0, 610.0)
LIGHT_AWAY = (1.0, 0.0)            # table shadows run to the right


def compose(painter):
    canvas = painter.canvas
    sl.room(canvas, TABLE_BACK_Y, TABLE_FRONT_Y)
    relief = Relief(canvas)
    sl.cloth(relief, "cloth", CLOTH_OUTLINE)
    shadows = []

    base, bottle = sl.lathe_object(relief, "bottle", material=sl.GLASS, gloss=1.0, top_roundness=0.3, **BOTTLE)
    sl.label(relief, "label", bottle, *LABEL)
    shadows.append((base, 84.0))
    base, jug = sl.lathe_object(relief, "jug", material=sl.CERAMIC, gloss=0.35, top_roundness=0.22, **JUG)
    sl.band(relief, jug, *JUG_BAND)
    sl.mouth(relief, "jug", (JUG["axis_x"], JUG["top_y"]), 62.0, sl.CERAMIC)
    shadows.append((base, 100.0))

    base, _ = sl.lathe_object(relief, "pear", material=sl.PEAR, gloss=0.3, depth=120.0, **PEAR)
    shadows.append((base, 70.0))
    shadows.append((sl.round_fruit(relief, "orange", (220.0, 790.0), 84.0, sl.ORANGE, squash=0.97, gloss=0.3,
                                   dimple=False, pores=3.0), 84.0))
    shadows.append((sl.round_fruit(relief, "apple", (960.0, 780.0), 92.0, sl.RED_APPLE), 92.0))
    shadows.append((sl.round_fruit(relief, "apple", (1130.0, 830.0), 78.0, sl.GREEN_APPLE), 78.0))
    shadows.append((sl.tilted_ellipse_fruit(relief, "lemon", (760.0, 880.0), 78.0, 54.0, -0.25, sl.LEMON,
                                            pores=2.0), 70.0))
    shadows.append((sl.grapes(relief, "grapes", (380.0, 800.0), 34, 26.0), 70.0))

    for base, half_width in shadows:
        sl.table_shadow(relief, base, half_width, LIGHT_AWAY)
    relief.render(painter)
    sl.stem(painter, (964.0, 708.0), 44.0, leaf=(64.0, -18.0))
    sl.stem(painter, (1134.0, 768.0), 34.0, lean=-0.3)
    sl.stem(painter, (PEAR["axis_x"], PEAR["top_y"] + 4.0), 40.0, lean=0.35)
    sl.stem(painter, (372.0, 800.0), 56.0, lean=-0.5)
    canvas.importance = np.clip(relief.cover * 0.6, 0.0, 1.0)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
