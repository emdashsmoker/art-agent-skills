"""Two-shot in a semi-real webtoon manner: a couple at dusk, his arm around her shoulders, hers round his waist.

Both characters stand in one Ensemble: his hand is placed on her far shoulder, his arm passes behind
her back by the depth test, and each figure throws shadow and contact shade on the other.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Character, Ensemble, Figure, Gradient, Hair, compose, geom, studio, wardrobe as w

brief = Brief.from_answers(style="webtoon", framing="three_quarter", format="square", lighting="studio",
                           mood="romantic", message="퇴근길 노을 아래 어깨를 감싼 두 사람", seed=21)


def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    with canvas.layer(depth=0.95):          # dusk street, out of focus: a gradient and soft lights
        canvas.add(geom.rect(0, 0, W, H), Gradient.linear((0, 0), (0, H), ["#384064", "#7a6688", "#e0a487"]), "sky", unlit=True)
        rng = canvas.rng
        for _ in range(34):
            x, y, r = rng.uniform(0, W), rng.uniform(H * 0.3, H * 0.9), rng.uniform(W * 0.015, W * 0.045)
            color = ["#ffd9a0", "#ffb37a", "#a8c8ff", "#ffe8c8"][rng.integers(4)]
            canvas.add(geom.ellipse(x, y, r, r), color, "bokeh", unlit=True, alpha=rng.uniform(0.25, 0.55))
    man = Character(Figure(sex="male", pose="relaxed", turn=14, heads=7.8, head_scale=1.04), style="semi", jaw=0.6,
                    hair=Hair("crop", "textured", "#26201f", seed=brief.seed), skin="light", glasses="round",
                    palette={"iris": "#5b4636"}, expression="gentle",
                    outfit=[w.top("#c9d6e6", "long", neck=6.62, ease=0.025, detail=w.collar()), w.pants("#2c303c")])
    woman = Character(Figure(pose="relaxed", turn=-16, heads=7.6, head_scale=1.04), style="semi", jaw=0.8,
                      hair=Hair("long", "parted", "#4a2f2a", wave=0.4, seed=brief.seed), skin="fair",
                      palette={"iris": "#6a4a3a"}, expression="smile",
                      outfit=[w.top("#efe6d8", "long", detail=w.neckline("scoop", 0.24, 0.2)), w.skirt("#6a5a7a", hem=2.4)])
    woman.figure.set_pose(head=(4, 10, 6))                          # she leans her head toward him
    ensemble = Ensemble.from_framing(canvas, compose.framing(canvas, "three_quarter"), man)
    ensemble.add(man, W * 0.42, depth=-30)
    ensemble.add(woman, W * 0.60, size=0.95)
    ensemble.touch(man, "l", woman, "around_shoulder")
    ensemble.touch(woman, "r", man, "waist")           # her near arm goes round his waist instead of hanging in front of him
    with canvas.layer(depth=0.3, group="figure"):
        views = ensemble.draw(light=light)
    return {"views": views}


if __name__ == "__main__":
    studio.run(build, brief, "duo_couple.png")
