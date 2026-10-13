"""Classical standing figure study in an old-master manner (adult figure, contrapposto with one hand in the hair).

Anatomy comes from the construction mannequin; the painting manner comes from the style preset.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, compose, scenery as sc, studio

brief = Brief.from_answers(subject="figure", style="renaissance", framing="full", pose="allure", outfit="none",
                           lighting="rembrandt", palette="earth", hair_style="updo", fringe="parted", hair_color="#7a5230",
                           skin="light", expression="gentle", message="고전 조각의 균형을 지닌 인체", seed=7)


def build(canvas, light, brief):
    from atelier import light as make_light
    light = make_light("rembrandt", azimuth=-45, elevation=38, wrap=0.2, shadow_tint="#6a5648")
    W, H = canvas.width, canvas.height
    horizon = H * 0.66
    # Evening sky, far hills and dark ground, low in contrast so the figure carries the picture.
    sc.sky(canvas, "#2f3a48", "#b89a6a", horizon)
    sc.mountains(canvas, horizon, H * 0.12, "#5a6258", depth=0.9, seed=3, facets=0.4)
    sc.hills(canvas, horizon + 10, H * 0.04, "#4a4a38", depth=0.7, seed=4)
    sc.ground(canvas, horizon + 20, "#3a3226", far_color="#544a36", depth=0.45)
    figure = Figure(pose="allure", turn=-18, heads=7.8, hands={"l": "relaxed", "r": "relaxed"}, bust=1.1)
    character = brief.character(figure, hair=Hair("updo", "parted", brief.hair_color, side=0.55, strand=0.4))
    placement = compose.framing(canvas, "full", x=W * 0.5)
    sc.contact_shadow(canvas, placement["x"] + 30, placement["ground_y"] - 6, W * 0.42, strength=0.7)
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **placement)
    return {"views": [view], "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "figure_classical.png")
