"""Doomer portrait of a woman: black bob, black turtleneck and a long open coat, earphones in, arms folded
against the cold on a snowy night.

She stands at the right third in front of a long nine-storey block whose windows are lit one by one, with a row of
bare birches between her and the wall. A cold mercury light from the left catches her face; the lit windows keep
the only warm colour in the picture.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from atelier import Brief, Figure, Hair, city, compose, light as make_light, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="portrait", style="doomer", format="portrait", framing="three_quarter",
                           composition="thirds_right", pose="arms_crossed", lighting="night", background="city", mood="melancholic",
                           hair_style="bob", fringe="straight", hair_color="#121014", eye_color="#4a4a52", expression="tired",
                           skin="fair", outfit="turtleneck", palette="doomer", message="이어폰을 낀 채 눈 내리는 밤에 선 사람",
                           seed=113)
MERCURY = "#a4b4d4"
SKY = "#26304a"
WIRE = "#e8e6e0"


def earphones(canvas, view, character):
    """Wired earbuds: a thread from under each side of the bob, meeting at the chest and running into the coat."""
    face, unit = character.face, view.unit
    style = face.style
    meet = np.array(view.joint("neck")) + np.array([unit * 0.06, unit * 0.62])
    for side in (-1, 1):
        start = np.array(face.pts([(side * style["mouth_w"] * 2.3, style["mouth_y"] - 0.04)])[0])
        bend = (start + meet) / 2 + np.array([side * unit * 0.05, 0.0])
        canvas.stroke([tuple(start), tuple(bend), tuple(meet)], unit * 0.012, WIRE, start=0.9, end=0.9, alpha=0.85)
    tail = meet + np.array([unit * 0.03, unit * 0.45])
    canvas.stroke([tuple(meet), tuple(tail)], unit * 0.014, WIRE, start=0.9, end=0.6, alpha=0.85)


def build(canvas, light, brief):
    light = make_light("night", azimuth=-48, elevation=30, color=MERCURY, shadow_tint="#34405e", haze=SKY,
                       haze_strength=0.55, rim=0.3)
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon = H * 0.66
    sc.sky(canvas, "#0a0e1a", SKY, horizon)
    camera = sc.Perspective(canvas, horizon, eye=1.6, focal=0.9, yaw=-6)
    with canvas.layer(depth=0.97):
        canvas.add(camera.ground_quad(-200, 200, 1, 400), "#6a7284", "snow", normal=(0, -1, 0.05))
    city.building(camera, -70, 48, 110, 12, 9 * city.PANEL_STOREY + 0.8, "#706e6a", kind="panel", light=light,
                  night=True, sky=SKY, seed=seed)
    for k, x in enumerate((-16, -9.5, -3, 4.5, 11)):        # a row of birches along the path in front of the block
        z = 26 + (k % 2) * 3
        px, py = camera.point(x, 0, z)
        sc.bare_tree(canvas, px, py, 9.5 * camera.scale(z, x), birch=True, seed=seed + k, spread=0.42,
                     lean=0.02 * (k - 2), depth=0.45)
    sc.weather(canvas, "snow", near=0.2, amount=1.0, wind=-0.1, seed=seed)

    figure = Figure(pose="arms_crossed", turn=-24, heads=7.6, hands={"l": "hold", "r": "hold"})
    figure.set_pose(head=(4, 16, 2))
    character = brief.character(figure, hair=Hair("bob", "straight", brief.hair_color, seed=seed, gloss=0.2), gaze=(-0.3, -0.05),
                                outfit=[w.turtleneck("#18181c"), w.pants("#202024"),
                                        w.coat("#2c2b30", hem=2.4, detail=w.open_front("#18181c")), w.shoes("#141416")])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **compose.framing(canvas, "three_quarter", x=W * 0.64))
    earphones(canvas, view, character)
    sc.weather(canvas, "snow", near=0.8, amount=0.35, wind=-0.1, seed=seed + 1)
    return {"views": [view], "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "doomer_female.png")
