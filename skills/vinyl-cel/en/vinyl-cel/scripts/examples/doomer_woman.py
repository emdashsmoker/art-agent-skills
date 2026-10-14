#!/usr/bin/env python3
"""Doomer set, woman: a woman in headphones and a down jacket waits at a bus stop at night, looking at her
phone, snow falling on the empty road; a street lamp by the shelter, a panel block across the courtyard.

    python doomer_woman.py --style all --preview --out out/
    python doomer_woman.py --style anime --grade none        # without the doomer colour grade

The phone screen is drawn after the night lighting, so it stays bright and lights nothing but itself.
"""
import _toolkit  # noqa: F401  (sets the import path)

import numpy as np

from codeillust import outdoor, props3d, rig3d, scene3d, street3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character
from codeillust.figure3d import Figure3D

SCENE_NAME = "doomer_woman"
M = outdoor.metres
SEED = 11
WOMAN = Figure3D(character=adult_face(default_character()), pose=rig3d.SIT_PHONE,
                 outfit=wardrobe3d.OUTFITS["winter_headphones"], head_scale=1.08,
                 props=(props3d.held_phone("right", screen="chat"),))
STOP_YAW = 0.0                                      # the shelter opens toward +z, onto the road
ROAD_Z = M(6.0)                                     # the road runs along x in front of the shelter
LAMP_AT = (M(-5.0), M(-9.5))                        # behind the shelter, its head above the roof
BLOCKS = ((M(-140.0), M(-70.0), M(120.0), 9, 0.75), (M(-70.0), M(-170.0), M(90.0), 12, 0.75))
CAMERA = scene3d.SceneCamera(target=(0.0, -M(1.6), -M(0.35)), origin=(620.0, 800.0), scale=62.0, yaw=-0.7,
                             pitch=-0.03, distance=M(12.0))
LAMP_LIGHT = (0.20, -0.88, 0.42)
CANVAS_UNITS = (1000.0, 1333.0)


def compose(painter):
    rng = np.random.default_rng(SEED)
    stop = scene3d.Placed(street3d.bus_stop(), at=(0.0, 0.0, 0.0), yaw=STOP_YAW)
    lamp = scene3d.Placed(street3d.street_lamp(props3d.cm(560.0), props3d.cm(110.0)), at=(LAMP_AT[0], 0.0, LAMP_AT[1]), yaw=np.pi)
    blocks = [outdoor.panel_block((x, z), length, floors, rng, light=outdoor.NIGHT, yaw=yaw)
              for x, z, length, floors, yaw in BLOCKS]
    extent = M(400.0)
    road = outdoor.road_texture(rng, outdoor.NIGHT, extent, along="x")
    world = outdoor.World(light=outdoor.NIGHT, sky=outdoor.NIGHT_SKY, fog=outdoor.FOG_NIGHT,
                          ground=outdoor.ground_plane(road, extent, center=(0.0, ROAD_Z)), blocks=blocks,
                          lamps=[street3d.lamp_light(lamp, strength=1.2), street3d.shelter_light(stop)],
                          items=[stop, lamp, scene3d.seated(WOMAN, stop, "seat_1")], snow=outdoor.SNOW_HEAVY)
    outdoor.draw_world(painter, CAMERA, world, rng)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=LAMP_LIGHT, description=__doc__, grade="doomer")
