"""Bust portrait of a young man in a semi-real webtoon manner: fitted light knit, city lights behind."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Gradient, Hair, compose, geom, studio, wardrobe as w

brief = Brief.from_answers(style="webtoon", framing="bust", lighting="studio", sex="male", hair_style="crop",
                           fringe="textured", hair_color="#26201f", eye_color="#5b4636", expression="gentle",
                           jaw="sharp", skin="light", mood="calm", message="퇴근길 도시의 불빛 앞, 여유 있는 시선", seed=12)


def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    with canvas.layer(depth=0.95):          # dusk street, out of focus: a gradient and soft lights
        canvas.add(geom.rect(0, 0, W, H), Gradient.linear((0, 0), (0, H), ["#2e3550", "#6a5a78", "#c99a86"]), "sky", unlit=True)
        rng = canvas.rng
        for _ in range(26):
            x, y, r = rng.uniform(0, W), rng.uniform(H * 0.35, H * 0.85), rng.uniform(W * 0.02, W * 0.05)
            color = ["#ffd9a0", "#ffb37a", "#a8c8ff", "#ffe8c8"][rng.integers(4)]
            canvas.add(geom.ellipse(x, y, r, r), color, "bokeh", unlit=True, alpha=rng.uniform(0.25, 0.55))
    figure = Figure(sex="male", pose="relaxed", turn=30, heads=7.7, head_scale=1.06, hands={"l": "relaxed", "r": "relaxed"})
    figure.set_pose(head=(3, -22, -3))
    character = brief.character(figure, hair=Hair("crop", "textured", brief.hair_color, seed=brief.seed),
                                outfit=[w.top("#d9cfbf", "long", neck=6.62, ease=0.025, detail=w.neckline("v", 0.2, 0.15)),
                                        w.pants("#3a3f4c")])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **compose.framing(canvas, "bust", x=W * 0.52))
    return {"views": [view]}


if __name__ == "__main__":
    studio.run(build, brief, "portrait_male.png")
