#!/usr/bin/env python3
"""Light scenes, sunset: two people on a courtyard bench facing us, a cup in her hands, turned toward each
other; the lamps are just coming on, bare birches frame them and the blocks catch the last pink light under
a violet sky.
    python dusk_bench.py --style anime --out out/
    python dusk_bench.py --style all --preview --out out/
The lamps and birches are placed by where they land in the frame (world_x), so no trunk or pole stands
behind a head; the blocks stand 300 m off so the sky stays open above them.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

import numpy as np

from codeillust import head3d, outdoor, props3d, rig3d, scene3d, street3d, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette, male_face
from codeillust.config import Material, rgb
from codeillust.figure3d import Figure3D

SCENE_NAME = "dusk_bench"
M = outdoor.metres
SEED = 45

SUNSET_SKY = ((0.0, rgb("#2E3A70")), (0.42, rgb("#6C68A2")), (0.74, rgb("#E8907A")), (1.0, rgb("#FFC888")))
SUNSET = outdoor.replace_light(outdoor.DUSK, wall=rgb("#B48E8C"), seam=rgb("#8C6C70"), glass=rgb("#4C4468"),
                               balcony=rgb("#9A7A7E"), lit_share=0.22,
                               ambient=np.array([0.74, 0.66, 0.76], dtype=np.float32))
SUNSET_FOG = outdoor.Fog(color=rgb("#E2A08E"), distance=M(220.0), horizon_band=90.0, horizon_strength=0.55)
LAMP_COLOR = rgb("#FFC27A")

DARK_HAIR = Material(base=rgb("#2E2422"), shadow=rgb("#140E10"), line=rgb("#0A0608"), accent=rgb("#4A3C38"),
                     light=rgb("#6A5652"))
TOWARD_HIM = dict(head=(0.04, 0.0, -0.28))
TOWARD_HER = dict(head=(0.02, 0.0, 0.22))
WOMAN = Figure3D(character=replace(adult_face(replace(default_character(), palette=figure_palette())), eye_open=0.9),
                 build=rig3d.FEMALE_AVERAGE, hair=head3d.LONG_HAIR, head_scale=1.08,
                 pose=replace(rig3d.SIT_MUG, rotations={**rig3d.SIT_MUG.rotations, **TOWARD_HIM}),
                 outfit=replace(wardrobe3d.OUTFITS["t_shirt_jeans"],
                                colors={"top": wardrobe3d.fabric("#E8B04A", "#A87420", "#5A3A0C", "#FFD888"),
                                        "bottom": wardrobe3d.DENIM, "shoes": wardrobe3d.WHITE, "sole": wardrobe3d.GREY}),
                 props=(props3d.held_mug(body=props3d.surface("#F4F0E8", "#C4B8A8", "#6A5E50", "#FFFFFF")),))
MAN = Figure3D(character=male_face(replace(default_character(), palette=replace(figure_palette(), hair=DARK_HAIR))),
               build=rig3d.MALE_SLIM, hair=head3d.MALE_MEDIUM_HAIR, head_scale=1.05,
               pose=replace(rig3d.SIT, rotations={**rig3d.SIT.rotations, **TOWARD_HER}),
               outfit=replace(wardrobe3d.OUTFITS["shirt_trousers"],
                              colors={"top": wardrobe3d.fabric("#5A78A8", "#34507C", "#18263E", "#8AA6D2"),
                                      "trim": wardrobe3d.fabric("#5A78A8", "#34507C", "#18263E", "#8AA6D2"),
                                      "bottom": wardrobe3d.fabric("#4A4440", "#2A2624", "#121010", "#6E6862"),
                                      "shoes": wardrobe3d.BLACK, "sole": wardrobe3d.GREY}))

# Layout by where things land in the frame (canvas x, depth in metres), so the trunks and poles frame the
# pair instead of standing behind their heads (heads near canvas x 375 and 612).
LAMP_SPOTS = ((90.0, -2.2), (720.0, -18.0), (880.0, -26.0), (40.0, -40.0))
BIRCH_SPOTS = ((960.0, -4.5, 4), (150.0, -14.0, 7), (770.0, -21.0, 2), (240.0, -31.0, 9), (930.0, -43.0, 5),
               (820.0, -56.0, 3))
BLOCKS = ((M(-60.0), M(-300.0), M(150.0), 9, 0.15), (M(120.0), M(-340.0), M(120.0), 12, -0.5),
          (M(-260.0), M(-380.0), M(140.0), 9, 0.4))
CAMERA = scene3d.SceneCamera(target=(0.0, -M(1.0), 0.0), origin=(500.0, 900.0), scale=86.0, yaw=0.22, pitch=0.03,
                             distance=M(10.0))


def world_x(canvas_x, z_metres, low=-200.0, high=200.0):
    """World x (head heights) of the ground point at depth z that the camera puts at canvas_x."""
    z = M(z_metres)
    for _ in range(60):
        mid = (low + high) / 2
        xy, _ = CAMERA.project(np.array([[mid, 0.0, z]]))
        low, high = (mid, high) if xy[0][0] < canvas_x else (low, mid)
    return (low + high) / 2, z


LAMPS_AT = [world_x(x, z) for x, z in LAMP_SPOTS]
BIRCHES = [(*world_x(x, z), seed) for x, z, seed in BIRCH_SPOTS]
CEL_LIGHT = (-0.55, -0.55, 0.62)             # the lamp at her side and the glow of the sky in front of them
CANVAS_UNITS = (1000.0, 1333.0)


def compose(painter):
    rng = np.random.default_rng(SEED)
    bench = scene3d.Placed(street3d.bench(), at=(0.0, 0.0, 0.0))
    lamps = [scene3d.Placed(street3d.street_lamp(props3d.cm(520.0), props3d.cm(100.0)), at=(x, 0.0, z), yaw=0.0)
             for x, z in LAMPS_AT]
    birches = [scene3d.Placed(street3d.birch(props3d.cm(950.0), seed=seed), at=(x, 0.0, z)) for x, z, seed in BIRCHES]
    blocks = [outdoor.panel_block((x, z), length, floors, rng, light=SUNSET, yaw=yaw)
              for x, z, length, floors, yaw in BLOCKS]
    extent = M(400.0)
    ground = outdoor.ground_plane(outdoor.asphalt_texture(rng, extent, color=rgb("#8A7470")), extent)
    world = outdoor.World(light=SUNSET, sky=SUNSET_SKY, fog=SUNSET_FOG, ground=ground, blocks=blocks,
                          lamps=[street3d.lamp_light(lamp, color=LAMP_COLOR, strength=1.1) for lamp in lamps],
                          items=[bench] + lamps + birches + [scene3d.seated(WOMAN, bench, "seat_0", turn=0.18),
                                                             scene3d.seated(MAN, bench, "seat_1", turn=-0.18)])
    outdoor.draw_world(painter, CAMERA, world, rng)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=CEL_LIGHT, description=__doc__,
                   grade="golden_hour")
