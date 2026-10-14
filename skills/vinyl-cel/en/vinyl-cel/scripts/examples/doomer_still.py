#!/usr/bin/env python3
"""Doomer set, still life: a kitchen windowsill at night: an ashtray with a burning cigarette, a glass of
tea in a metal holder, an old radio-cassette player and a tape, the radiator under the sill, and the block
across the courtyard in the window.

    python doomer_still.py --style all --preview --out out/
    python doomer_still.py --style anime --grade none        # without the doomer colour grade

The wall is lit like the objects (outdoor.light_plane with an ambient); the view in the window is drawn
after that, so the lit windows outside stay bright.
"""
import _toolkit  # noqa: F401  (sets the import path)

import numpy as np

from codeillust import furniture3d, interior, outdoor, props3d, scene3d, studio
from codeillust.config import rgb
from codeillust.props3d import cm

SCENE_NAME = "doomer_still"
SEED = 61
WALL_Z = -2.0                                         # the back wall; the room opens toward +z
SILL_HEIGHT, SILL_DEPTH, SILL_WIDTH = cm(88.0), cm(30.0), cm(190.0)
WINDOW = (cm(-75.0), cm(75.0), cm(235.0), SILL_HEIGHT + cm(2.0))   # x0, x1, top, bottom
WALL = (cm(-260.0), cm(260.0), cm(270.0))                         # x0, x1, height
NIGHT_FRAME = rgb("#454B54")                          # a white window frame in a dark kitchen
VIEW_DETAIL = 0.7                                     # painterly: the windows across the yard stay windows
AMBIENT = np.array([0.34, 0.37, 0.48], dtype=np.float32)
KITCHEN_LAMP = outdoor.Lamp(at=(cm(-150.0), -cm(150.0), WALL_Z + cm(120.0)), color=rgb("#F2B070"), reach=cm(110.0),
                            strength=1.1)
WINDOW_GLOW = outdoor.Lamp(at=(0.0, -cm(160.0), WALL_Z - cm(20.0)), color=rgb("#7E96B8"), reach=cm(70.0), strength=0.6)
ON_SILL = {"ashtray": (-0.55, 0.15, 0.0), "tea": (1.05, 0.05, 0.0), "player": (-2.55, -0.10, 0.18),
           "tape": (0.30, 0.42, -0.5)}                # x, z on the sill top (head heights) and turn
CAMERA = scene3d.SceneCamera(target=(-0.5, -SILL_HEIGHT - 0.5, WALL_Z + 0.7), origin=(640.0, 560.0), scale=185.0,
                             yaw=-0.30, pitch=0.22, distance=8.0)
LAMP_LIGHT = (-0.75, -0.45, 0.48)                     # cel shading from the kitchen lamp, left and in front
CANVAS_UNITS = (1333.0, 1000.0)


def compose(painter):
    canvas = painter.canvas
    rng = np.random.default_rng(SEED)
    lamps = [KITCHEN_LAMP, WINDOW_GLOW]
    x0, x1, height = WALL
    wall = interior.Surface(((x0, -height, WALL_Z), (x1, -height, WALL_Z), (x1, 0.0, WALL_Z), (x0, 0.0, WALL_Z)),
                            interior.wallpaper(x1 - x0, height, rng, stripe=cm(11.0)), interior.BACK)
    floor = interior.Surface(((x0, 0.0, WALL_Z), (x1, 0.0, WALL_Z), (x1, 0.0, WALL_Z + 8.0), (x0, 0.0, WALL_Z + 8.0)),
                             interior.paint(x1 - x0, 8.0, rgb("#6E5A48"), rng), interior.UP)
    for surface, normal in ((wall, interior.BACK), (floor, interior.UP)):
        covered = interior.draw_surface(canvas, CAMERA, surface)
        if covered is not None:
            outdoor.light_plane(canvas, CAMERA, lamps, surface.corners[0], normal, ambient=AMBIENT, mask=covered)
    left, right, top, bottom = WINDOW
    view = interior.window(right - left, top - bottom, "panel_night", rng, frame=NIGHT_FRAME)
    glass = interior.Surface(((left, -top, WALL_Z + 0.01), (right, -top, WALL_Z + 0.01), (right, -bottom, WALL_Z + 0.01),
                              (left, -bottom, WALL_Z + 0.01)), view, interior.BACK)
    interior.keep_detail(canvas, interior.draw_surface(canvas, CAMERA, glass), VIEW_DETAIL)
    sill = scene3d.Placed(furniture3d.windowsill(SILL_WIDTH, SILL_DEPTH, SILL_HEIGHT), at=(0.0, 0.0, WALL_Z + SILL_DEPTH / 2))
    radiator = scene3d.Placed(furniture3d.radiator(), at=(0.0, 0.0, WALL_Z + cm(9.0)))
    objects = {"ashtray": props3d.ashtray(seed=SEED), "tea": props3d.tea_glass(seed=SEED),
               "player": props3d.cassette_player(), "tape": props3d.cassette()}
    items = [sill, radiator] + [scene3d.on_top(objects[key], sill, offset=(x, 0.0, z), yaw=turn)
                                for key, (x, z, turn) in ON_SILL.items()]
    scene3d.draw_scene3d(painter, CAMERA, items, lighting=outdoor.night_lighting(CAMERA, AMBIENT, lamps))


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=LAMP_LIGHT, description=__doc__, grade="doomer")
