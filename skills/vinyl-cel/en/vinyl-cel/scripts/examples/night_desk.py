#!/usr/bin/env python3
"""Light scenes, night desk: a woman typing on a laptop late at night, the screen lighting her face from the
front and a desk lamp warming the desk; the window behind her opens on towers under the moon.
    python night_desk.py --style illust --out out/          # illust keeps the face soft at this angle
    python night_desk.py --style all --preview --out out/
The room is lit like a night street (outdoor.draw_lit_room): walls and items keep ambient of their colour
and each lamp adds its own; the window view goes on after the light, so the city keeps its lit windows.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

import numpy as np

from codeillust import furniture3d, head3d, interior, outdoor, props3d, rig3d, scene3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette
from codeillust.config import rgb
from codeillust.figure3d import Figure3D
from codeillust.props3d import cm

SCENE_NAME = "night_desk"
SEED = 21
SHELL = interior.Shell(-7.0, 7.0, -7.5, interior.ROOM_FRONT, cm(250.0))
WALL = rgb("#E8DCC8")
DESK_AT = (0.0, -2.2)                        # x, z; the desk faces the camera (its user sits behind it)
CHAIR_AT = (0.0, -4.6)
LAPTOP_DEPTH = 0.92                          # head heights from the desk centre toward the user
WINDOW_BOX = (-3.2, 3.2, cm(225.0), cm(95.0))   # x0, x1, top, bottom on the back wall
DESK_TOP = furniture3d.DESK_HEIGHT

SPACE_GREY = props3d.surface("#5A5E66", "#33363C", "#16181C", "#8A8E96")   # a dark lid: a light one glares
HOODIE = wardrobe3d.fabric("#D49A92", "#9A5E5A", "#4A2626", "#F2C2B8")
WOMAN = Figure3D(character=replace(adult_face(replace(default_character(), palette=figure_palette())),
                                   gaze=(0.0, 0.08), eye_open=0.88),
                 build=rig3d.FEMALE_AVERAGE, pose=rig3d.SIT_TYPE, hair=head3d.PONYTAIL_HAIR, head_scale=1.08,
                 outfit=replace(wardrobe3d.OUTFITS["hoodie_jeans"],
                                colors={"top": HOODIE, "trim": HOODIE, "bottom": wardrobe3d.DENIM,
                                        "shoes": wardrobe3d.WHITE, "sole": wardrobe3d.GREY}))

# Light: the screen (pale cool, on the face), the desk lamp (warm, on the desk), the window (faint cool rim).
AMBIENT = np.array([0.36, 0.34, 0.42])
SCREEN = outdoor.Lamp(at=(0.0, -DESK_TOP - cm(14.0), DESK_AT[1] - LAPTOP_DEPTH - 0.3), color=rgb("#D2DEF8"),
                      reach=cm(50.0), strength=0.85)
DESK_LAMP = outdoor.Lamp(at=(-1.95, -DESK_TOP - cm(36.0), DESK_AT[1] - 0.25), color=rgb("#FFC07A"), reach=cm(75.0),
                         strength=1.15, cone=1.05)
WINDOW_GLOW = outdoor.Lamp(at=(0.0, -cm(170.0), SHELL.z0 + 0.4), color=rgb("#6C88C4"), reach=cm(80.0), strength=0.45)
LAMPS = (SCREEN, DESK_LAMP, WINDOW_GLOW)

CAMERA = scene3d.SceneCamera(target=(0.0, -4.5, -3.3), origin=(500.0, 640.0), scale=165.0, yaw=0.38, pitch=0.06,
                             distance=20.0)
CEL_LIGHT = (0.30, -0.20, 0.93)              # cel shading mostly from the screen in front of her
CANVAS_UNITS = (1000.0, 1333.0)


def room_surfaces(rng):
    s = SHELL
    width, depth = s.x1 - s.x0, s.z1 - s.z0
    floor = interior.planks(width, depth, (rgb("#9C6E48"), rgb("#8E623E"), rgb("#A87850")), rng)
    surfaces = interior.shell_surfaces(s, floor, interior.paint(width, s.height, WALL, rng),
                                       interior.paint(depth, s.height, WALL * 0.97, rng),
                                       interior.paint(depth, s.height, WALL * 0.97, rng),
                                       interior.paint(width, depth, WALL * 0.93, rng))
    surfaces += interior.trims(s, rgb("#F4EEE4"))
    for x in (WINDOW_BOX[0] - 1.2, WINDOW_BOX[1] - 0.1):
        surfaces.append(interior.on_back_wall(s, x, x + 1.3, cm(235.0), cm(60.0),
                                              interior.curtain(1.3, cm(175.0), rgb("#7C8FB0"))))
    surfaces.append(interior.on_left_wall(s, -6.0, -1.5, cm(200.0), cm(140.0), interior.artwork(4.5, cm(60.0), rng)))
    return surfaces


def window_views(rng):
    x0, x1, top, bottom = WINDOW_BOX
    view = interior.window(x1 - x0, top - bottom, "city_night", rng, frame=rgb("#3E4450"))
    return [interior.on_back_wall(SHELL, x0, x1, top, bottom, view)]


def items():
    desk = scene3d.Placed(furniture3d.desk(cm(130.0), cm(65.0)), at=(DESK_AT[0], 0.0, DESK_AT[1]), yaw=np.pi)
    chair = scene3d.Placed(furniture3d.office_chair(), at=(CHAIR_AT[0], 0.0, CHAIR_AT[1]))
    mug = props3d.mug(body=props3d.surface("#E07A5F", "#9A3E36", "#4E1A18", "#F8A890"))
    return [desk, chair, scene3d.seated(WOMAN, chair),
            scene3d.on_top(props3d.laptop(lid_angle=1.85, screen="code", shell=SPACE_GREY), desk,
                           offset=(0.0, 0.0, LAPTOP_DEPTH)),
            scene3d.on_top(props3d.desk_lamp(), desk, offset=(2.3, 0.0, -0.4), yaw=-0.5),   # shade toward her
            scene3d.on_top(mug, desk, offset=(-1.7, 0.0, 0.7)),
            scene3d.on_top(props3d.book_stack(3, seed=4), desk, offset=(2.0, 0.0, 0.9), yaw=0.2),
            scene3d.on_top(props3d.potted_plant(seed=6), desk, offset=(-2.2, 0.0, -0.6)),
            scene3d.on_top(props3d.headphones(), desk, offset=(-1.2, 0.0, -0.5), yaw=0.9)]


def compose(painter):
    rng = np.random.default_rng(SEED)
    surfaces = room_surfaces(rng)
    outdoor.draw_lit_room(painter, CAMERA, surfaces, window_views(rng), items(), LAMPS, AMBIENT)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=CEL_LIGHT, description=__doc__,
                   grade="cozy_night")
