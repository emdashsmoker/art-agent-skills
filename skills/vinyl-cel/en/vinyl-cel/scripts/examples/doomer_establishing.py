#!/usr/bin/env python3
"""Doomer set, establishing shot: a district of panel blocks at dusk under low cloud, power lines
crossing the snowfield in front, a trodden path and one small figure walking home along it.

    python doomer_establishing.py --style all --preview --out out/
    python doomer_establishing.py --style anime --grade none        # without the doomer colour grade

The figure is small on purpose: in a wide shot the place is the subject and the person sets its scale.
"""
import _toolkit  # noqa: F401  (sets the import path)

import numpy as np

from codeillust import outdoor, props3d, rig3d, scene3d, street3d, studio, wardrobe3d
from codeillust.character import default_character, male_face
from codeillust.figure3d import Figure3D

SCENE_NAME = "doomer_establishing"
M = outdoor.metres
SEED = 31
WALKER = Figure3D(character=male_face(default_character()), build=rig3d.MALE_SLIM, pose=rig3d.WALK,
                  outfit=wardrobe3d.OUTFITS["winter_beanie"], head_scale=1.05)
WALKER_AT, WALKER_TURN = (M(2.4), M(-14.0)), np.pi + 0.25     # walking away from us, toward the blocks
PATH = ((M(-2.0), M(6.0)), (M(1.0), M(-8.0)), (M(4.0), M(-22.0)), (M(10.0), M(-45.0)), (M(18.0), M(-80.0)))
BLOCKS = ((M(-95.0), M(-140.0), M(100.0), 9, 0.2), (M(40.0), M(-175.0), M(90.0), 12, -0.25),
          (M(-210.0), M(-270.0), M(80.0), 16, 0.5), (M(175.0), M(-290.0), M(110.0), 9, -0.55),
          (M(-30.0), M(-380.0), M(120.0), 14, 0.0), (M(95.0), M(-430.0), M(80.0), 16, 0.3))
POLES = ((M(-26.0), M(-6.0)), (M(-4.0), M(-14.0)), (M(18.0), M(-22.0)), (M(40.0), M(-30.0)), (M(62.0), M(-38.0)))
BIRCHES = ((M(-20.0), M(-26.0), 2), (M(-27.0), M(-34.0), 5), (M(-14.0), M(-40.0), 8), (M(34.0), M(-48.0), 3))
LAMPS = ((M(-14.0), M(-60.0)), (M(16.0), M(-70.0)), (M(46.0), M(-82.0)))
CAMERA = scene3d.SceneCamera(target=(M(8.0), -M(2.0), M(-60.0)), origin=(640.0, 560.0), scale=4.2, yaw=0.12,
                             pitch=0.09, distance=M(75.0))
HAZE = outdoor.Fog(color=outdoor.FOG_DUSK.color, distance=M(420.0), horizon_band=70.0, horizon_strength=0.5)
DUSK_LIGHT = (-0.55, -0.45, -0.70)                   # the last light low behind the blocks
CANVAS_UNITS = (1333.0, 1000.0)


def compose(painter):
    rng = np.random.default_rng(SEED)
    extent = M(800.0)
    half = extent / 2
    path = [(x + half, z + half) for x, z in PATH]                   # plane coordinates run 0..extent
    ground = outdoor.snow_texture(rng, outdoor.DUSK, extent, paths=[(path, M(1.6))])
    blocks = [outdoor.panel_block((x, z), length, floors, rng, light=outdoor.DUSK, yaw=yaw)
              for x, z, length, floors, yaw in BLOCKS]
    poles = [scene3d.Placed(street3d.power_pole(lean=0.04 * ((k % 3) - 1)), at=(x, 0.0, z), yaw=-0.35)
             for k, (x, z) in enumerate(POLES)]
    lamps = [scene3d.Placed(street3d.street_lamp(), at=(x, 0.0, z), yaw=0.0) for x, z in LAMPS]
    birches = [scene3d.Placed(street3d.birch(seed=seed), at=(x, 0.0, z)) for x, z, seed in BIRCHES]
    world = outdoor.World(light=outdoor.DUSK, sky=outdoor.DUSK_SKY, fog=HAZE,
                          ground=outdoor.ground_plane(ground, extent), blocks=blocks,
                          lamps=[street3d.lamp_light(lamp, strength=0.9) for lamp in lamps],
                          items=poles + lamps + birches + [scene3d.Placed(WALKER, at=(WALKER_AT[0], 0.0, WALKER_AT[1]),
                                                                yaw=WALKER_TURN)],
                          wires=street3d.wires_between(poles), clouds=0.35)
    outdoor.draw_world(painter, CAMERA, world, rng)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=DUSK_LIGHT, description=__doc__, grade="doomer")
