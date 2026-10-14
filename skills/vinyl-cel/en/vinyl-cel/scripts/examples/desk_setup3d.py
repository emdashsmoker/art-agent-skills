#!/usr/bin/env python3
"""Modern still life: a home-office desk with a laptop, a monitor, a keyboard and the small things round them.

    python desk_setup3d.py --style all --preview --out out/

The room is built here from interior's parts (a custom shell with a window), which is the way to
make a room the three presets do not cover. Every object is a props3d builder placed on the desk
top anchor, so moving the desk moves the whole set.
"""
import _toolkit  # noqa: F401  (sets the import path)
import numpy as np

from codeillust import furniture3d, interior, props3d, scene3d, studio
from codeillust.body3d import rot_y
from codeillust.config import rgb
from codeillust.interior import Room, Shell

SCENE_NAME = "desk_setup3d"
SHELL = Shell(-5.0, 9.0, -3.2, interior.ROOM_FRONT, props3d.cm(250.0))
WALL = rgb("#E6E9E2")
DESK = scene3d.Placed(furniture3d.desk(props3d.cm(140.0), props3d.cm(65.0)), at=(0.0, 0.0, SHELL.z0 + 1.55))
LAPTOP_AT = (-1.75, 0.25, 0.45)           # x, z on the desk top and turn of the laptop (ON_DESK)
LAPTOP_PORT_HEIGHT = props3d.cm(0.8)      # the charging port sits half way up the laptop's base
CHARGER_PLUG = (-0.72, -0.15)             # laptop-frame x, z of the charging port on its left side
CHARGER_ROUTE = ((-1.05, -0.55), (-1.6, -0.95), (-2.0, -1.36))   # desk-frame x, z of the cable on the desk top
CHARGER_DROP = (-2.1, -1.75)              # desk-frame x, z where it reaches the floor behind the desk
ON_DESK = (  # (builder, x, z on the desk top, turn) in the desk's frame; +z is the edge the user sits at
    (props3d.monitor("code"), 0.3, -0.55, 0.0),
    (props3d.keyboard(), 0.3, 0.55, 0.0),
    (props3d.mouse(), 1.75, 0.6, -0.1),
    (props3d.laptop(lid_angle=1.9, screen="desktop"), *LAPTOP_AT),
    (props3d.mug(body=props3d.surface("#4F7FB8", "#264E80", "#102640", "#8AB4E4")), 2.35, 0.25, 0.6),
    (props3d.phone("home"), -0.75, 0.9, -0.3),
    (props3d.headphones(), 2.1, -0.65, -0.5),
    (props3d.book_stack(3, seed=6), -2.6, -1.0, 0.15),
    (props3d.desk_lamp(), -1.0, -0.95, 0.5),
    (props3d.potted_plant(seed=10), 2.75, -0.95, 0.0),
)
CAMERA = scene3d.SceneCamera(target=(0.1, -3.9, SHELL.z0 + 1.6), origin=(666.0, 470.0), scale=178.0, yaw=0.30,
                             pitch=0.40, distance=12.0)
CANVAS_UNITS = (1333.0, 1000.0)          # landscape: a desk is wider than it is tall


def room():
    rng = np.random.default_rng(21)
    width, depth = SHELL.x1 - SHELL.x0, SHELL.z1 - SHELL.z0
    surfaces = interior.shell_surfaces(
        SHELL, interior.planks(width, depth, (rgb("#C8A27A"), rgb("#BC9670"), rgb("#D2AE88")), rng),
        interior.paint(width, SHELL.height, WALL, rng), interior.paint(depth, SHELL.height, WALL * 0.97, rng),
        interior.paint(depth, SHELL.height, WALL * 0.97, rng), interior.paint(width, depth, WALL * 0.93, rng))
    surfaces += interior.trims(SHELL, rgb("#FAFAF6"))
    surfaces.append(interior.on_left_wall(SHELL, -2.6, 2.6, props3d.cm(215.0), props3d.cm(90.0),
                                          interior.window(5.2, props3d.cm(125.0), "city", rng, panes=(2, 1))))
    surfaces.append(interior.on_back_wall(SHELL, -1.6, 2.2, props3d.cm(205.0), props3d.cm(150.0),
                                          interior.artwork(3.8, props3d.cm(55.0), rng)))
    items = [DESK] + [scene3d.on_top(item, DESK, offset=(x, 0.0, z), yaw=turn) for item, x, z, turn in ON_DESK]
    return Room(surfaces, items + [charger_cable()], {"desk": DESK})


def charger_cable():
    """Cable from the laptop's side over the desk top and its back edge, hanging down to the floor."""
    top = np.asarray(scene3d.anchor(DESK, "top"), dtype=np.float64)
    x, z, turn = LAPTOP_AT
    plug = top + np.array([x, -LAPTOP_PORT_HEIGHT, z]) + rot_y(turn) @ np.array([CHARGER_PLUG[0], 0.0, CHARGER_PLUG[1]])
    route = [top + np.array([rx, 0.0, rz]) for rx, rz in CHARGER_ROUTE]
    floor = np.array([top[0] + CHARGER_DROP[0], 0.0, top[2] + CHARGER_DROP[1]])
    return scene3d.Placed(props3d.cable([plug] + route + [floor]))


ROOM = room()


def compose(painter):
    interior.draw_room(painter, CAMERA, ROOM)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
