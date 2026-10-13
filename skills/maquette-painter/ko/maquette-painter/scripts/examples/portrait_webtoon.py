"""Half-length portrait in a semi-real webtoon manner, with a custom pose and an interior background."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Gradient, Hair, compose, geom, studio, wardrobe as w

brief = Brief.from_answers(style="webtoon", framing="half", lighting="soft_front", hair_style="medium", fringe="parted",
                           hair_color="#4a2f2a", eye_color="#4f6f8f", expression="gentle", mood="romantic",
                           message="창가의 오후, 부드러운 빛", seed=6)


def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    with canvas.layer(depth=0.95):          # interior wall with a bright window on the left
        canvas.add(geom.rect(0, 0, W, H), Gradient.linear((0, 0), (W, 0), ["#f1e6d6", "#d9c7b6"]), "wall", unlit=True)
        canvas.add(geom.rect(W * 0.05, H * 0.08, W * 0.36, H * 0.62),
                   Gradient.linear((0, H * 0.08), (0, H * 0.62), ["#eaf4fb", "#fdf3df"]), "window", unlit=True)
        for x in (W * 0.05, W * 0.205, W * 0.36):
            canvas.add(geom.rect(x - 5, H * 0.08, x + 5, H * 0.62), "#b9a892", "frame", unlit=True)
        canvas.add(geom.rect(W * 0.05, H * 0.34, W * 0.36, H * 0.35), "#b9a892", "frame", unlit=True)
    figure = Figure(pose="hand_on_hip", turn=20, heads=7.7, hands={"r": "relaxed", "l": "grace"})
    figure.set_pose(head=(4, -26, -5), l_shoulder=(10, 0, 10), l_elbow=(25, 0, 0))
    character = brief.character(figure, hair=Hair("medium", "parted", brief.hair_color, wave=0.6),
                                outfit=[w.top("#e9e1d3", "long", detail=w.neckline("v", 0.34, 0.19)), w.skirt("#5a6b62", hem=2.6)])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **compose.framing(canvas, "half", x=W * 0.6))
    return {"views": [view]}


if __name__ == "__main__":
    studio.run(build, brief, "portrait_webtoon.png")
