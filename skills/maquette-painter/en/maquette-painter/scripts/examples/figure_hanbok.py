"""A woman in hanbok among peonies, as a Korean folk painting (minhwa): flat colour on aged paper.

She wears a yellow jeogori with a purple collar, white dongjeong and red ribbons (goreum) over a full red chima
tied high under the arms, hands folded at the waist. Peony bushes fill the foreground and a pale full moon hangs
over rounded hills, the usual furniture of a peony painting (morando).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, compose, geom, objects as ob, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="figure", style="minhwa", format="portrait", framing="full", composition="thirds_right",
                           pose="relaxed", outfit="hanbok", lighting="soft_front", background="landscape", mood="calm",
                           hair_style="bun", fringe="parted", hair_color="#1e1a1c", expression="gentle", palette="minhwa",
                           message="a woman in hanbok standing among peonies", seed=97)
PEONY = ["#e04a5a", "#f0a0b0", "#f6e6e0", "#c83a6a"]


def peony_bush(canvas, x, base_y, size, seed):
    """A peony clump: many small lobed leaves first, then big many-petalled blooms on top."""
    rng = np.random.default_rng(seed)
    with canvas.layer(depth=0.2):
        for k in range(34):                             # leaves: short rounded lobes spread over a low dome
            angle = rng.uniform(np.pi * 1.05, np.pi * 1.95)
            dist = size * rng.uniform(0.2, 0.62)
            cx, cy = x + np.cos(angle) * dist, base_y + np.sin(angle) * dist * 0.55
            length, turn = size * rng.uniform(0.1, 0.16), rng.uniform(-40, 40) + np.degrees(angle) + 90
            leaf = geom.rotate(geom.blob([(cx, cy - length), (cx + length * 0.38, cy - length * 0.2), (cx + length * 0.2, cy + length * 0.5),
                                          (cx, cy + length * 0.62), (cx - length * 0.2, cy + length * 0.5),
                                          (cx - length * 0.38, cy - length * 0.2)]), turn, (cx, cy))
            canvas.add(leaf, ["#3f6a44", "#4f7d4a", "#365a3c"][k % 3], "leaf", outline=(1.4, "#24402a"))
    for k in range(3):
        bx = x + rng.uniform(-0.4, 0.4) * size
        by = base_y - size * rng.uniform(0.38, 0.6)
        ob.flower(canvas, bx, by, size * rng.uniform(0.28, 0.34), petal=PEONY[(seed + k) % len(PEONY)], centre="#f2c64a",
                  petals=12, outline=(1.4, "#7a2a3a"), seed=seed + k, tilt=rng.uniform(0.15, 0.35), turn=rng.uniform(0, 60))


def build(canvas, light, brief):
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon = H * 0.62
    sc.sky(canvas, "#d9c9a0", "#efe2c2", horizon)
    sc.sun(canvas, W * 0.26, H * 0.2, W * 0.1, color="#f8f1dc")
    sc.mountains(canvas, horizon, H * 0.14, "#7f9a8a", depth=0.8, seed=seed, shape="rounded", roughness=0.3)
    sc.ground(canvas, horizon, "#cbbf92", far_color="#b9b48a", depth=0.6)
    framing = compose.framing(canvas, "full", x=W * 0.6, margin_bottom=0.06)
    sc.contact_shadow(canvas, W * 0.6, framing["ground_y"] - 2, W * 0.24, H * 0.02, strength=0.3)
    figure = Figure(pose="relaxed", turn=-18, heads=7.6)
    figure.set_pose(head=(6, -10, 3))
    for side in ("r", "l"):                             # hands brought together in front at the waist
        figure.reach(side, (0.08 if side == "r" else 0.02, 5.05, 0.95), anchor="waist")
    character = brief.character(figure, hair=Hair("bun", "parted", brief.hair_color, seed=seed),
                                outfit=[w.chima("#c43a48"), w.jeogori("#f2d16b", git="#6a3a7a", goreum="#c43a48")])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **framing)
    peony_bush(canvas, W * 0.16, H * 0.97, W * 0.34, seed)
    peony_bush(canvas, W * 0.92, H * 1.0, W * 0.24, seed + 7)
    return {"views": [view]}


if __name__ == "__main__":
    studio.run(build, brief, "figure_hanbok.png")
