#!/usr/bin/env python3
"""Light scenes, beach at sunset: two people walking barefoot along the shore toward the low sun, which lays
a gold path on the sea and lights the side of them that faces it.
    python beach_sunset.py --style anime --out out/
    python beach_sunset.py --style all --preview --out out/
The beach is the painted background (background.beach) with a sunset sky, sun and sun path laid over it at
the camera's horizon (outdoor.horizon_y); the figures are 3D items under outdoor.night_lighting, which here
only warms them. Her stride is shortened so the forward thigh stays inside the skirt.
"""
import _toolkit  # noqa: F401  (sets the import path)
from dataclasses import replace

import numpy as np

from codeillust import background, head3d, outdoor, rig3d, scene3d, shading, studio, wardrobe3d
from codeillust.character import adult_face, default_character, figure_palette, male_face
from codeillust.config import Material, rgb
from codeillust.figure3d import Figure3D

SCENE_NAME = "beach_sunset"
M = outdoor.metres
SEED = 57

SKY_STOPS = ((0.0, rgb("#343A78")), (0.45, rgb("#9A6A98")), (0.78, rgb("#F29C74")), (1.0, rgb("#FFD49A")))
SEA = (rgb("#4A4C86"), rgb("#8A7CA8"))
SAND = (rgb("#E9BE9C"), rgb("#C99478"))
SUN_COLOR = rgb("#FFE8B8")
SUN_DISC = rgb("#FFF8E8")
SUN_X, SUN_RISE, SUN_RADIUS = 1010.0, 14.0, 40.0         # canvas x, height above the horizon, radius
SHORE_BELOW_HORIZON = 120.0                              # canvas units from the horizon to the waterline
PATH_WIDTH = 70.0                                        # half width of the sun's path on the water at the shore

DARK_HAIR = Material(base=rgb("#2E2422"), shadow=rgb("#140E10"), line=rgb("#0A0608"), accent=rgb("#4A3C38"),
                     light=rgb("#6A5652"))
LEG_JOINTS = ("hip_left", "knee_left", "ankle_left", "hip_right", "knee_right", "ankle_right")
SKIRT_STRIDE = 0.55                                       # a shorter stride keeps the forward thigh inside the skirt
STROLL = replace(rig3d.WALK, rotations={name: tuple(v * SKIRT_STRIDE for v in angles) if name in LEG_JOINTS else angles
                                        for name, angles in rig3d.WALK.rotations.items()})
WOMAN = Figure3D(character=replace(adult_face(replace(default_character(), palette=figure_palette())), smile=0.7),
                 build=rig3d.FEMALE_AVERAGE, pose=STROLL, hair=head3d.LONG_HAIR, head_scale=1.08,
                 outfit=replace(wardrobe3d.OUTFITS["sundress"],
                                colors={"top": wardrobe3d.fabric("#F6EEE4", "#C8B4B0", "#6A5658", "#FFFFFF"),
                                        "accent": wardrobe3d.fabric("#E07A6A", "#A04A40", "#4E1E1A"),
                                        "shoes": wardrobe3d.fabric("#E8B894", "#B88466", "#5A3A28")}))
MAN = Figure3D(character=replace(male_face(replace(default_character(), palette=replace(figure_palette(), hair=DARK_HAIR))),
                                 smile=0.6),
               build=rig3d.MALE_SLIM, pose=rig3d.WALK, hair=head3d.MALE_SHORT_HAIR, head_scale=1.05,
               outfit=replace(wardrobe3d.OUTFITS["hoodie_shorts"],
                              colors={"top": wardrobe3d.fabric("#6E8EB8", "#44628C", "#1E2E48", "#9EB8DA"),
                                      "trim": wardrobe3d.fabric("#6E8EB8", "#44628C", "#1E2E48", "#9EB8DA"),
                                      "bottom": wardrobe3d.fabric("#E8E0D0", "#B4A894", "#5A5244", "#FFFFFF"),
                                      "shoes": wardrobe3d.fabric("#E8B894", "#B88466", "#5A3A28"),
                                      "sole": wardrobe3d.fabric("#E8B894", "#B88466", "#5A3A28")}))

AMBIENT = np.array([0.74, 0.64, 0.76])
WALK_YAW = 0.85                                           # walking toward the sun, three-quarter to the camera
CAMERA = scene3d.SceneCamera(target=(0.0, -M(0.9), 0.0), origin=(500.0, 560.0), scale=84.0, yaw=0.25, pitch=0.02,
                             distance=M(12.0))
CEL_LIGHT = (0.80, -0.30, 0.20)             # the low sun on their right, a little behind
CANVAS_UNITS = (1333.0, 1000.0)


def sky_and_sea(canvas, light, horizon):
    shore = horizon + SHORE_BELOW_HORIZON
    background.beach(canvas, light, horizon, shore, (), sea=SEA, sand=SAND, foam=rgb("#FFF0E0"))
    xs, ys = canvas.grid()
    t = np.clip(ys / horizon, 0.0, 1.0)
    sky = np.zeros(ys.shape + (3,), np.float32)
    for (t0, c0), (t1, c1) in zip(SKY_STOPS, SKY_STOPS[1:]):
        inside = (t >= t0) & (t <= t1)
        k = ((t[inside] - t0) / (t1 - t0))[:, None]
        sky[inside] = c0 * (1 - k) + c1 * k
    canvas.blend(1.0 - shading.smoothstep(horizon - 0.8, horizon + 0.8, ys), sky)
    sun = (SUN_X, horizon - SUN_RISE)
    background.sun_glow(canvas, sun, SUN_RADIUS * 9, SUN_COLOR, 0.55)
    disc = canvas.soft_ellipse(sun, SUN_RADIUS, SUN_RADIUS) * (1.0 - shading.smoothstep(horizon - 0.8, horizon + 0.8, ys))
    canvas.blend(shading.smoothstep(0.2, 0.6, disc), SUN_DISC)
    # The sun's path: glints on the water under the sun, wider toward the shore.
    depth = np.clip((ys - horizon) / SHORE_BELOW_HORIZON, 0.0, 1.0)
    width = 8.0 + PATH_WIDTH * depth
    path = (1.0 - shading.smoothstep(0.4, 1.0, np.abs(xs - SUN_X) / width)) * (ys > horizon) * (ys < shore)
    sparkle = shading.smoothstep(0.45, 0.85, canvas.noise(6.0, octaves=2))
    canvas.blend(path * (0.35 + 0.65 * sparkle), SUN_COLOR, 0.8)


def compose(painter):
    horizon = outdoor.horizon_y(CAMERA)
    sky_and_sea(painter.canvas, painter.light, horizon)
    sun_lamp = outdoor.Lamp(at=(M(60.0), -M(6.0), -M(80.0)), color=rgb("#FFB474"), reach=M(110.0), strength=0.45)
    items = [scene3d.Placed(WOMAN, at=(-M(0.2), 0.0, M(0.45)), yaw=WALK_YAW),
             scene3d.Placed(MAN, at=(M(0.75), 0.0, -M(0.45)), yaw=WALK_YAW)]
    scene3d.draw_scene3d(painter, CAMERA, items, lighting=outdoor.night_lighting(CAMERA, AMBIENT, [sun_lamp]))


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, light=CEL_LIGHT, description=__doc__,
                   grade="golden_hour")
