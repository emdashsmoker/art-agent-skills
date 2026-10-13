"""Anime bust portrait. Run: python portrait_anime.py [--rough | --buffers | --styles a,b | --out file.png]

The standard order for a figure picture: background (far to near) -> character -> paint.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Gradient, compose, geom, studio

brief = Brief.from_answers(style="anime_cel", framing="bust", view="three_quarter", lighting="studio",
                           hair_style="long", fringe="swept", hair_color="#3b2c44", eye_color="#c47a2c",
                           expression="gentle", outfit="coat", message="차분하고 단단한 인상의 성인 여성")


def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    with canvas.layer(depth=0.95):          # quiet graded wall; two large shapes frame the head
        canvas.add(geom.rect(0, 0, W, H), Gradient.linear((0, 0), (0, H), ["#cfdde6", "#efe6da"]), "wall", unlit=True)
        canvas.add(geom.ellipse(W * 0.66, H * 0.36, W * 0.36), "#f6efe2", "disc", unlit=True)
        canvas.add(geom.rect(0, H * 0.78, W, H), "#c9d3d6", "band", unlit=True)
    character = brief.character()
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **compose.framing(canvas, brief.framing, x=W * 0.48))
    return {"views": [view]}


if __name__ == "__main__":
    studio.run(build, brief, "portrait_anime.png")
