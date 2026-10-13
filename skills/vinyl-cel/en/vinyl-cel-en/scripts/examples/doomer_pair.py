#!/usr/bin/env python3
"""Doomer set, two-shot: two people sit side by side on a courtyard bench at night, seen from behind,
looking up at the windows of the panel block across the yard; one smokes, a bare birch and a lamp beside them.

    python doomer_pair.py --style all --preview --out out/
    python doomer_pair.py --style anime --grade none        # without the doomer colour grade

The bench faces the block (yaw pi turns its front to -z), so the camera behind it sees the figures' backs.
"""
import _toolkit  # noqa: F401  (sets the import path)

from dataclasses import replace

import numpy as np

from codeillust import head3d, outdoor, props3d, rig3d, scene3d, street3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, male_face
from codeillust.figure3d import Figure3D

SCENE_NAME = "doomer_pair"
M = outdoor.metres
SEED = 23
LOOK_UP = dict(neck=(-0.10, 0, 0), head=(-0.16, 0, 0))     # both look up at the windows
MAN = Figure3D(character=male_face(default_character()), build=rig3d.MALE_SLIM,
               pose=replace(rig3d.SIT_SMOKE, rotations={**rig3d.SIT_SMOKE.rotations, **LOOK_UP}),
               hair=head3d.MALE_SHORT_HAIR, outfit=wardrobe3d.OUTFITS["winter_beanie"], head_scale=1.05,
               props=(props3d.held_cigarette("right", seed=SEED),))
WOMAN = Figure3D(character=adult_face(default_character()),
                 pose=replace(rig3d.SIT, rotations={**rig3d.SIT.rotations, **LOOK_UP, "head": (-0.16, 0.0, 0.10)}),
                 outfit=wardrobe3d.OUTFITS["winter_headphones"], head_scale=1.08)
BENCH_AT = (0.0, 0.0)
LAMP_AT = (M(1.0), M(-9.0))                       # ahead of them: they sit with the light beyond
BIRCH_AT = (M(6.5), M(-9.0))
BLOCKS = ((M(80.0), M(-195.0), M(160.0), 9, -0.39), (M(190.0), M(-250.0), M(90.0), 12, -0.8),
          (M(-25.0), M(-215.0), M(90.0), 9, 0.1))
CAMERA = scene3d.SceneCamera(target=(0.0, -M(1.0), 0.0), origin=(640.0, 680.0), scale=62.0, yaw=0.42, pitch=0.06,
                             distance=M(11.0))
LAMP_LIGHT = (0.25, -0.70, -0.67)                    # from the lamp ahead of them: their backs are in shade
CANVAS_UNITS = (1333.0, 1000.0)


def compose(painter):
    rng = np.random.default_rng(SEED)
    bench = scene3d.Placed(street3d.bench(), at=(BENCH_AT[0], 0.0, BENCH_AT[1]), yaw=np.pi)
    lamp = scene3d.Placed(street3d.street_lamp(props3d.cm(560.0), props3d.cm(110.0)), at=(LAMP_AT[0], 0.0, LAMP_AT[1]),
                          yaw=np.pi)
    birch = scene3d.Placed(street3d.birch(props3d.cm(900.0), seed=4), at=(BIRCH_AT[0], 0.0, BIRCH_AT[1]))
    blocks = [outdoor.panel_block((x, z), length, floors, rng, light=outdoor.replace_light(outdoor.NIGHT, lit_share=0.3),
                                  yaw=yaw) for x, z, length, floors, yaw in BLOCKS]
    extent = M(400.0)
    world = outdoor.World(light=outdoor.NIGHT, sky=outdoor.NIGHT_SKY, fog=outdoor.FOG_NIGHT,
                          ground=outdoor.ground_plane(outdoor.snow_texture(rng, outdoor.NIGHT, extent), extent),
                          blocks=blocks, lamps=[street3d.lamp_light(lamp, strength=1.2)],
                          items=[bench, lamp, birch, scene3d.seated(MAN, bench, "seat_1"),
                                 scene3d.seated(WOMAN, bench, "seat_0")])
    outdoor.draw_world(painter, CAMERA, world, rng)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=LAMP_LIGHT, description=__doc__, grade="doomer")
