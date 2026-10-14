#!/usr/bin/env python3
"""Doomer set, man: a man in a beanie and a down jacket smoking under a street lamp at night, a panel
block with a few lit windows behind him, light snow falling.

    python doomer_man.py --style all --preview --out out/
    python doomer_man.py --style anime --grade none        # without the doomer colour grade

The outdoor world (sky, snow, blocks, lamp light, haze, snowfall) is an outdoor.World drawn by
outdoor.draw_world; the street lamp is a street3d prop whose bulb also lights the ground and the figure.
"""
import _toolkit  # noqa: F401  (sets the import path)

import numpy as np

from codeillust import head3d, outdoor, props3d, rig3d, scene3d, street3d, studio, wardrobe3d
from codeillust.character import default_character, male_face
from codeillust.figure3d import Figure3D

SCENE_NAME = "doomer_man"
M = outdoor.metres
SEED = 7
MAN = Figure3D(character=male_face(default_character()), build=rig3d.MALE_SLIM, pose=rig3d.STAND_SMOKE,
               hair=head3d.MALE_SHORT_HAIR, outfit=wardrobe3d.OUTFITS["winter_beanie"], head_scale=1.05,
               props=(props3d.held_cigarette("right", seed=SEED),))
MAN_AT, MAN_TURN = (M(-1.3), M(1.2)), 0.35          # x, z; he turns his front a little toward image-right
LAMP_HEIGHT, LAMP_ARM = props3d.cm(560.0), props3d.cm(110.0)    # a courtyard lamp, lower than a street's
LAMPS = ((M(0.6), M(-1.6)), (M(8.0), M(-14.0)), (M(14.0), M(-26.0)), (M(20.0), M(-40.0)))   # his lamp, then a row
BLOCKS = ((M(-10.0), M(-90.0), M(110.0), 10, 0.0),  # x, z, length, floors, yaw
          (M(85.0), M(-130.0), M(70.0), 12, -1.25))
CAMERA = scene3d.SceneCamera(target=(0.0, -M(2.2), 0.0), origin=(600.0, 740.0), scale=50.0, yaw=0.30, pitch=-0.06,
                             distance=M(9.0))
LAMP_LIGHT = (0.35, -0.86, 0.36)                    # cel shading from the lamp above and to the right
CANVAS_UNITS = (1000.0, 1333.0)


def compose(painter):
    rng = np.random.default_rng(SEED)
    lamps = [scene3d.Placed(street3d.street_lamp(LAMP_HEIGHT, LAMP_ARM), at=(x, 0.0, z), yaw=np.pi) for x, z in LAMPS]
    blocks = [outdoor.panel_block((x, z), length, floors, rng, light=outdoor.NIGHT, yaw=yaw)
              for x, z, length, floors, yaw in BLOCKS]
    extent = M(400.0)
    world = outdoor.World(light=outdoor.NIGHT, sky=outdoor.NIGHT_SKY, fog=outdoor.FOG_NIGHT,
                          ground=outdoor.ground_plane(outdoor.snow_texture(rng, outdoor.NIGHT, extent), extent),
                          blocks=blocks, lamps=[street3d.lamp_light(lamp, strength=1.3) for lamp in lamps],
                          items=lamps + [scene3d.Placed(MAN, at=(MAN_AT[0], 0.0, MAN_AT[1]), yaw=MAN_TURN)],
                          snow=outdoor.SNOW_LIGHT)
    outdoor.draw_world(painter, CAMERA, world, rng)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=LAMP_LIGHT, description=__doc__, grade="doomer")
