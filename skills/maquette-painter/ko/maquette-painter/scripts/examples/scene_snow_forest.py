"""A snowy forest path in soft pastel on blue-grey paper: snow-laden firs, falling snow, one walker in red.

The path is laid in perspective and bends away into the trees. Every fir is sized and layered by its distance,
carries snow on each branch tier, and fades into the falling snow with depth. The small red figure walking
away is the only warm colour and gives the trees their scale.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, geom, light as make_light, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="landscape", style="pastel", format="portrait", framing="full", view="back",
                           pose="walk", outfit="coat", lighting="overcast",
                           background="landscape", mood="calm", message="눈 내리는 숲길을 홀로 걷는 사람", seed=67)
PAPER = dict(paper="#8e99ae", grain=0.45)               # cool toned paper: the snow light reads warm against it
FOREST = dict(count=34, near=10.5, far=70.0, clear=2.6, spread=16.0)   # trees either side of the path, in metres


def path_x(z):
    """The path's centre line: it bends left, then right, as it runs into the wood."""
    return 0.9 * np.sin(z / 9.0) - 0.4


def build(canvas, light, brief):
    light = make_light("overcast", azimuth=-30, elevation=35, color="#f4f1ea", shadow_tint="#8a94b0", haze="#dfe4ec",
                       haze_strength=0.6)
    H, seed = canvas.height, brief.seed
    horizon = H * 0.47
    camera = sc.Perspective(canvas, horizon, eye=1.6, focal=1.35)
    sc.sky(canvas, "#aeb9c9", "#e3e7ee", horizon)
    sc.treeline(canvas, horizon + 4, H * 0.12, "#a9b4c2", depth=0.92, seed=seed)
    with canvas.layer(depth=0.7):
        canvas.add(camera.ground_quad(-60, 60, 1.0, 120), "#eef1f6", "snow", normal=(0, -1, 0.1))
    zs = np.linspace(1.0, 70, 90)
    left = [camera.point(path_x(z) - 1.0, 0, z) for z in zs]
    right = [camera.point(path_x(z) + 1.0, 0, z) for z in zs[::-1]]
    with canvas.layer(depth=0.6):
        canvas.add(geom.blob(left + right), "#cdd3dd", "path", normal=(0, -1, 0.1))
        for side in (-1, 1):                        # ruts: two faint grooves trodden along the path
            groove = [camera.point(path_x(z) + side * 0.35, 0, z) for z in zs]
            canvas.stroke(groove, 3.0, "#a9b1c0", start=0.1, end=1.0, alpha=0.5)
    rng = np.random.default_rng(seed)
    trees = []
    for _ in range(FOREST["count"]):
        z = rng.uniform(FOREST["near"], FOREST["far"])
        side = rng.choice((-1, 1))
        trees.append((z, path_x(z) + side * (FOREST["clear"] + rng.uniform(0, FOREST["spread"]) * (z / FOREST["far"]) ** 0.5),
                      rng.uniform(8.0, 14.0)))
    for i, (z, x, tall) in enumerate(sorted(trees, reverse=True)):     # far to near
        base = camera.point(x, 0, z)
        sc.conifer(canvas, base[0], base[1], tall * camera.scale(z), color="#2f4a44", depth=float(np.clip(z / 60, 0.2, 0.85)),
                   seed=seed + i, snow=0.65)
    sc.weather(canvas, "snow", near=0.15, amount=1.3, seed=seed)

    # ---- a walker in a red coat, small, going away along the path ----
    walk_z = 11.0
    foot_x, foot_y = camera.point(path_x(walk_z) + 0.2, 0, walk_z)
    figure = Figure(pose="walk", turn=172, heads=7.5)
    figure.set_pose(l_hip=(18, 0, 2), r_hip=(-8, 0, 2))      # a shorter stride keeps the legs inside the long coat
    walker = brief.character(figure, hair=Hair("bun", "none", "#3a2a24", seed=seed),
                             outfit=[w.pants("#3a3f4c"), w.coat("#b8362e", hem=2.4, sleeves="long", ease=0.12), w.shoes("#2a2420")])
    with canvas.layer(depth=0.55):                  # her footprints, back along the path toward us
        for k, z in enumerate(np.arange(walk_z - 0.45, 1.2, -0.38)):
            fx, fy = camera.point(path_x(z) + 0.2 + (0.09 if k % 2 else -0.09), 0, z)
            size = camera.scale(z)
            canvas.add(geom.ellipse(fx, fy, 0.055 * size, 0.13 * size * camera.eye / z), "#b3bccb", "path",
                       normal=(0, -1, 0.1))
    sc.contact_shadow(canvas, foot_x, foot_y - 1, 0.6 * camera.scale(walk_z), 0.1 * camera.scale(walk_z), strength=0.35)
    with canvas.layer(depth=0.3, group="figure"):
        view = walker.draw(canvas, foot_x, ground_y=foot_y, height=1.65 * camera.scale(walk_z), light=light)
    sc.weather(canvas, "snow", near=0.8, amount=0.7, seed=seed + 1)
    return {"views": [view], "light": light, "style_params": {"pastel": PAPER}}


if __name__ == "__main__":
    studio.run(build, brief, "scene_snow_forest.png")
