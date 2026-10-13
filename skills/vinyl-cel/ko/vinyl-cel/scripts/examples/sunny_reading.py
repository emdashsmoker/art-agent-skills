#!/usr/bin/env python3
"""Light scenes, late afternoon: a woman on the sofa by the window with a mug, looking out at the low sun;
its light warms the window side of the room, the rest stays in soft cool daylight.
    python sunny_reading.py --style illust --out out/
    python sunny_reading.py --style all --preview --out out/
Daylight is an ambient near 1 (outdoor.draw_lit_room) plus a broad warm "lamp" standing in for the sun by
the window; the sun patch on the floor is a view surface, painted after the light.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

import numpy as np

from codeillust import furniture3d, head3d, interior, outdoor, props3d, rig3d, scene3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette
from codeillust.config import rgb
from codeillust.figure3d import Figure3D
from codeillust.props3d import cm

SCENE_NAME = "sunny_reading"
SEED = 33
SHELL = interior.Shell(-9.0, 9.0, -7.0, interior.ROOM_FRONT, cm(250.0))
WALL = rgb("#F1E6D4")
WINDOW_BOX = (-7.4, -2.2, cm(220.0), cm(70.0))     # x0, x1, top, bottom on the back wall
SOFA_AT = (2.6, -5.0)                              # against the back wall, facing the camera

KNIT = wardrobe3d.fabric("#9DB89A", "#5E7E62", "#2A3E2C", "#CDE2C8")
WOMAN = Figure3D(character=replace(adult_face(replace(default_character(), palette=figure_palette())),
                                   gaze=(-0.35, 0.02), eye_open=0.85),     # looking out of the window
                 build=rig3d.FEMALE_AVERAGE, pose=rig3d.SIT_MUG, hair=head3d.BOB_HAIR, head_scale=1.08,
                 outfit=replace(wardrobe3d.OUTFITS["hoodie_jeans"],
                                colors={"top": KNIT, "trim": KNIT, "bottom": wardrobe3d.DENIM,
                                        "shoes": wardrobe3d.WHITE, "sole": wardrobe3d.GREY}),
                 props=(props3d.held_mug(body=props3d.surface("#F4C95D", "#B08A2A", "#5A4410", "#FFE89A")),))

# Light: soft cool daylight everywhere, the low sun warming the window side of the room.
AMBIENT = np.array([0.80, 0.82, 0.90])
SUN = outdoor.Lamp(at=(-4.6, -cm(115.0), SHELL.z0 + 2.4), color=rgb("#FFB870"), reach=5.0, strength=0.85)
LAMPS = (SUN,)

CAMERA = scene3d.SceneCamera(target=(-0.2, -3.7, -4.6), origin=(666.0, 470.0), scale=118.0, yaw=-0.28, pitch=0.10,
                             distance=20.0)
CEL_LIGHT = (-0.78, -0.42, 0.46)             # from the window side, a little in front so her face reads
CANVAS_UNITS = (1333.0, 1000.0)


def room_surfaces(rng):
    s = SHELL
    width, depth = s.x1 - s.x0, s.z1 - s.z0
    floor = interior.planks(width, depth, (rgb("#C49464"), rgb("#B58456"), rgb("#D0A070")), rng)
    surfaces = interior.shell_surfaces(s, floor, interior.paint(width, s.height, WALL, rng),
                                       interior.paint(depth, s.height, WALL * 0.97, rng),
                                       interior.paint(depth, s.height, WALL * 0.97, rng),
                                       interior.paint(width, depth, WALL * 0.93, rng))
    surfaces += interior.trims(s, rgb("#FAF6EE"))
    x0, x1, top, bottom = WINDOW_BOX
    for x in (x0 - 1.1, x1 - 0.2):
        surfaces.append(interior.on_back_wall(s, x, x + 1.3, cm(232.0), cm(40.0),
                                              interior.curtain(1.3, cm(192.0), rgb("#F2E2C2"))))
    surfaces.append(interior.on_back_wall(s, 0.6, 4.6, cm(182.0), cm(128.0), interior.artwork(4.0, cm(54.0), rng)))
    return surfaces


def window_views(rng):
    x0, x1, top, bottom = WINDOW_BOX
    view = interior.window(x1 - x0, top - bottom, "golden", rng, frame=rgb("#F4F0E8"))
    return [interior.on_back_wall(SHELL, x0, x1, top, bottom, view), interior.sunlight(SHELL, x0, x1, top, bottom, (2, 1))]


def items():
    sofa = scene3d.Placed(furniture3d.sofa(), at=(SOFA_AT[0], 0.0, SOFA_AT[1]))
    table = scene3d.Placed(furniture3d.coffee_table(), at=(SOFA_AT[0] + 1.8, 0.0, SOFA_AT[1] + 3.6))   # clear of her legs
    return [scene3d.Placed(furniture3d.rug(cm(240.0), cm(170.0)), at=(SOFA_AT[0] - 0.5, 0.0, SOFA_AT[1] + 3.2)),
            sofa, table, scene3d.seated(WOMAN, sofa, "seat_0"),
            scene3d.on_top(props3d.book_stack(2, seed=8), table, offset=(0.9, 0.0, 0.1), yaw=0.3),
            scene3d.on_top(props3d.book(cover=props3d.BOOK_COLORS[2]), table, offset=(-0.9, 0.0, 0.0), yaw=-0.4),
            scene3d.Placed(furniture3d.floor_lamp(), at=(SOFA_AT[0] + 5.2, 0.0, SHELL.z0 + 0.9)),
            scene3d.Placed(furniture3d.bookshelf(), at=(7.6, 0.0, SHELL.z0 + 0.7))]


def compose(painter):
    rng = np.random.default_rng(SEED)
    surfaces = room_surfaces(rng)
    outdoor.draw_lit_room(painter, CAMERA, surfaces, window_views(rng), items(), LAMPS, AMBIENT)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=CEL_LIGHT, description=__doc__,
                   grade="late_sun")
