#!/usr/bin/env python3
"""Doomer set, city: a wet avenue at night running straight between rows of panel blocks, sodium lamps on
both kerbs going away to one vanishing point, trolleybus wires overhead, the lights mirrored in the road.

    python doomer_city.py --style all --preview --out out/
    python doomer_city.py --style anime --grade none        # without the doomer colour grade

One-point perspective: the camera looks straight down the road (yaw 0, pitch 0), so every line along the
road meets at the centre of the picture.
"""
import _toolkit  # noqa: F401  (sets the import path)

import numpy as np

from codeillust import outdoor, rig3d, scene3d, street3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character
from codeillust.figure3d import Figure3D

SCENE_NAME = "doomer_city"
M = outdoor.metres
SEED = 41
ROAD_WIDTH = M(16.0)
KERB_X = M(9.0)                                      # lamp poles stand just off the kerbs
LAMP_SPACING, LAMP_COUNT, FIRST_LAMP = M(32.0), 9, M(-6.0)
WIRE_HEIGHT, WIRE_LANES = M(6.2), (M(-3.0), M(-2.4), M(2.4), M(3.0))   # trolleybus contact wires over each lane
SPAN_SAG, WIRE_SAG = M(0.25), M(0.12)
BLOCK_SIDE_X = M(26.0)                               # the block facades stand back from the road
BLOCK_RUN = ((M(-30.0), M(70.0), 12), (M(-120.0), M(90.0), 16), (M(-225.0), M(80.0), 12), (M(-320.0), M(90.0), 16),
             (M(-420.0), M(80.0), 12))                # centre z, length along the road, floors
WALKER = Figure3D(character=adult_face(default_character()), pose=rig3d.WALK,
                  outfit=wardrobe3d.OUTFITS["winter_headphones"], head_scale=1.08)
WALKER_AT = (M(10.5), M(-48.0))
CAMERA = scene3d.SceneCamera(target=(M(0.8), -M(4.0), M(-30.0)), origin=(500.0, 700.0), scale=13.0, yaw=0.0,
                             pitch=0.0, distance=M(36.0))
LAMP_LIGHT = (0.0, -0.9, -0.42)
CANVAS_UNITS = (1000.0, 1333.0)


def compose(painter):
    rng = np.random.default_rng(SEED)
    lamps = []
    for index in range(LAMP_COUNT):
        z = FIRST_LAMP - index * LAMP_SPACING
        lamps += [scene3d.Placed(street3d.street_lamp(), at=(-KERB_X, 0.0, z), yaw=0.0),
                  scene3d.Placed(street3d.street_lamp(), at=(KERB_X, 0.0, z), yaw=np.pi)]
    blocks = []
    for z, length, floors in BLOCK_RUN:
        blocks += [outdoor.panel_block((-BLOCK_SIDE_X, z), length, floors, rng, yaw=np.pi / 2),
                   outdoor.panel_block((BLOCK_SIDE_X, z + M(20.0)), length, floors, rng, yaw=-np.pi / 2)]
    extent = M(900.0)
    road = outdoor.road_texture(rng, outdoor.NIGHT, extent, road_width=ROAD_WIDTH)
    world = outdoor.World(light=outdoor.NIGHT, sky=outdoor.NIGHT_SKY, fog=outdoor.FOG_NIGHT,
                          ground=outdoor.ground_plane(road, extent), blocks=blocks,
                          lamps=[street3d.lamp_light(lamp) for lamp in lamps],
                          items=lamps + [scene3d.Placed(WALKER, at=(WALKER_AT[0], 0.0, WALKER_AT[1]), yaw=np.pi)],
                          wires=trolley_wires(), wet=True)
    outdoor.draw_world(painter, CAMERA, world, rng)


def trolley_wires():
    """Span wires across the road between each pair of lamp poles, and the contact wires along each lane."""
    wires = []
    stops = [FIRST_LAMP - index * LAMP_SPACING for index in range(LAMP_COUNT)]
    for z in stops:
        wires.append(outdoor.catenary((-KERB_X, -WIRE_HEIGHT - M(0.6), z), (KERB_X, -WIRE_HEIGHT - M(0.6), z), SPAN_SAG))
    for x in WIRE_LANES:
        for near, far in zip(stops, stops[1:]):
            wires.append(outdoor.catenary((x, -WIRE_HEIGHT, near), (x, -WIRE_HEIGHT, far), WIRE_SAG))
    return wires


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=LAMP_LIGHT, description=__doc__, grade="doomer")
