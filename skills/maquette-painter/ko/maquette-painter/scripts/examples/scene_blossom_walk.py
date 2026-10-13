"""A spring walk under a blossoming tree, as a woodblock print: flat colour, ink line, graded sky, falling petals.

A woman in a long-sleeved kimono (furisode) with a gold obi and a red paper parasol walks beneath a cherry in full
bloom. The parasol is the open
umbrella prop with many thin ribs and a shallow canopy; the petals are the falling-particle weather, in a far band
behind her and a near band across the picture. A few fallen petals lie on the path.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, geom, light as make_light, props, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="scene", style="ukiyo_e", format="portrait", framing="full",
                           composition="thirds_right", pose="walk", outfit="kimono", lighting="soft_front",
                           background="landscape", mood="calm", hair_style="bun", fringe="none", hair_color="#1c1a1e",
                           expression="gentle", palette="ukiyo", message="꽃잎이 흩날리는 봄길을 걷는 사람", seed=83)
BLOSSOM = "#f3c4cf"


def build(canvas, light, brief):
    light = make_light("soft_front", azimuth=-35, elevation=40, color="#fffaf0", shadow_tint="#c8b4c0", wrap=0.45)
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon = H * 0.6
    sc.sky(canvas, "#7fa6c4", "#f3ead8", horizon)
    sc.mountains(canvas, horizon, H * 0.16, "#8ea0b4", depth=0.85, seed=seed, shape="rounded", roughness=0.35)
    sc.hills(canvas, horizon + 6, H * 0.04, "#9cb48a", depth=0.7, seed=seed + 1)
    sc.ground(canvas, horizon + 10, "#c9c79a", far_color="#b8c49a", depth=0.6)
    far_l, far_r = (W * 0.49, horizon + 12), (W * 0.54, horizon + 12)     # the path narrows to a point far away
    path = geom.runs([[far_l, (W * 0.36, H * 0.76), (W * 0.12, H + 4)], [(W * 0.12, H + 4), (W * 1.08, H + 4)],
                      [(W * 1.08, H + 4), (W * 0.82, H * 0.8), far_r], [far_r, far_l]])
    with canvas.layer(depth=0.55):
        canvas.add(path, "#e6dcc4", "path", normal=(0, -1, 0.1), outline=1.5)
    for k in range(70):                                 # fallen petals on the path
        rng = np.random.default_rng(seed + k)
        x, y = rng.uniform(W * 0.2, W * 0.95), rng.uniform(H * 0.75, H * 0.99)
        canvas.add(geom.ellipse(x, y, 4.0, 2.2, rng.uniform(0, 180)), BLOSSOM, "petal", clip=path)
    sc.broadleaf(canvas, W * 0.08, H * 0.84, H * 0.95, color=BLOSSOM, trunk="#3a2a26", spread=1.05, seed=seed, depth=0.4,
                 outline=(2.0, "#8a5a66"), density=2.6)
    sc.weather(canvas, "petals", near=0.2, amount=1.2, wind=0.6, seed=seed)

    # ---- a woman walking with a parasol over her shoulder ----
    ground_y = H * 0.9
    figure = Figure(pose="walk", turn=-32, heads=7.6)
    figure.set_pose(head=(4, -10, 0), l_hip=(18, 0, 2), r_hip=(-8, 0, 2))
    figure.reach("r", (0.05, 5.6, 0.6), anchor="chest")
    figure.hands["r"] = "fist"
    character = brief.character(figure, hair=Hair("bun", "none", brief.hair_color, seed=seed),
                                outfit=[w.kimono("#2f4a7a", sleeves="furisode", pattern="blossom", seed=seed),
                                        w.obi("#d8a640", cord="#b8334a"), w.shoes("#f4f2ec")])
    sc.contact_shadow(canvas, W * 0.62, ground_y - 2, H * 0.13, H * 0.018, strength=0.35)
    with canvas.layer(depth=0.3, group="figure"):
        view = character.place(canvas, W * 0.62, ground_y=ground_y, height=H * 0.6)
        character.build(view)
        fist = view.group_mask("hand_r") > 0.5
        ys, xs = np.nonzero(fist)
        grip = (xs.mean() / canvas.scale, ys.mean() / canvas.scale)
        head, unit = view.joint("head"), view.unit
        parasol = dict(hand=grip, centre=(head[0] + unit * 0.55, head[1] - unit * 1.2), radius=unit * 2.4,
                       color="#c8443a", inner="#e07a5a", ribs=24, view=0.35, rise=0.38, shaft="#5a3a28", outline=1.6)
        props.umbrella(canvas, part="back", **parasol)
        character.paint(view, light=light)
        props.umbrella(canvas, part="front", clip=1.0 - fist.astype("float32"), **parasol)
    sc.weather(canvas, "petals", near=0.75, amount=0.8, wind=0.6, seed=seed + 1)
    return {"views": [view], "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "scene_blossom_walk.png")
