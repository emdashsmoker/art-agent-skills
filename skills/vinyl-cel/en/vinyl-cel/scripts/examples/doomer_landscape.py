#!/usr/bin/env python3
"""Doomer set, landscape: a snowfield on an overcast day, a line of power poles marching to the horizon,
clumps of bare birches, and the blocks of a far district standing low on the horizon.

    python doomer_landscape.py --style all --preview --out out/
    python doomer_landscape.py --style anime --grade none        # without the colour grade

Daylight uses the doomer_day grade: grey-green and cold, almost no warm light.
"""
import _toolkit  # noqa: F401  (sets the import path)

import numpy as np

from codeillust import outdoor, scene3d, street3d, studio

SCENE_NAME = "doomer_landscape"
M = outdoor.metres
SEED = 53
POLE_LINE = ((M(-9.0), M(-7.0)), (M(260.0), M(-620.0)))   # first and last pole (x, z)
POLE_COUNT = 14
BIRCH_CLUMPS = ((M(-34.0), M(-60.0), 7), (M(46.0), M(-120.0), 5), (M(-90.0), M(-210.0), 6), (M(14.0), M(-34.0), 2))
CLUMP_SPREAD = M(6.0)
BLOCKS = ((M(-260.0), M(-1100.0), M(120.0), 12, 0.1), (M(-90.0), M(-1250.0), M(90.0), 16, 0.0),
          (M(80.0), M(-1180.0), M(140.0), 9, -0.1), (M(240.0), M(-1300.0), M(100.0), 12, 0.2))
HAZE = outdoor.Fog(color=outdoor.FOG_OVERCAST.color, distance=M(2200.0), horizon_band=40.0, horizon_strength=0.3)
PATH = ((M(-4.0), M(30.0)), (M(-2.0), M(-20.0)), (M(30.0), M(-120.0)), (M(90.0), M(-300.0)))   # a track beside the line
CAMERA = scene3d.SceneCamera(target=(0.0, -M(3.0), M(-40.0)), origin=(560.0, 560.0), scale=6.0, yaw=-0.05,
                             pitch=-0.01, distance=M(40.0))
DAY_LIGHT = (-0.30, -0.80, 0.52)                     # soft light from high in the overcast
CANVAS_UNITS = (1333.0, 1000.0)


def compose(painter):
    rng = np.random.default_rng(SEED)
    (x0, z0), (x1, z1) = POLE_LINE
    poles = [scene3d.Placed(street3d.power_pole(lean=0.05 * np.sin(k * 1.7)), at=(x0 + (x1 - x0) * t, 0.0,
                                                                                  z0 + (z1 - z0) * t), yaw=0.42)
             for k, t in enumerate(np.linspace(0.0, 1.0, POLE_COUNT))]
    birches = []
    for x, z, count in BIRCH_CLUMPS:
        for index in range(count):
            dx, dz = rng.normal(0.0, CLUMP_SPREAD, 2)
            height = props_height(rng)
            birches.append(scene3d.Placed(street3d.birch(height, seed=int(rng.integers(1000))), at=(x + dx, 0.0, z + dz),
                                          yaw=float(rng.uniform(0, 2 * np.pi))))
    blocks = [outdoor.panel_block((x, z), length, floors, rng, light=outdoor.OVERCAST, yaw=yaw)
              for x, z, length, floors, yaw in BLOCKS]
    extent = M(3000.0)
    track = [(x + extent / 2, z + extent / 2) for x, z in PATH]          # plane coordinates run 0..extent
    world = outdoor.World(light=outdoor.OVERCAST, sky=outdoor.OVERCAST_SKY, fog=HAZE,
                          ground=outdoor.ground_plane(outdoor.snow_texture(rng, outdoor.OVERCAST, extent, paths=[(track, M(1.2))]),
                                                      extent),
                          blocks=blocks, items=poles + birches, wires=street3d.wires_between(poles, sag=M(0.9)),
                          clouds=0.25)
    outdoor.draw_world(painter, CAMERA, world, rng)


def props_height(rng):
    """Birches of a clump differ in height: 7 to 13 metres."""
    return M(float(rng.uniform(7.0, 13.0)))


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=DAY_LIGHT, description=__doc__,
                   grade="doomer_day")
