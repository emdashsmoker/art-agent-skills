"""Classical standing male figure in an old-master manner (adult, weight on one leg, one hand at the shoulder).

The same construction as the female figure with the male tables: broad shoulders over narrow hips,
chest plates, deltoids and the abdominal grid come from the mannequin; a knotted hip cloth keeps it classical.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, compose, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="figure", style="renaissance", framing="full", pose="david", outfit="drape",
                           lighting="rembrandt", palette="earth", sex="male", hair_style="crop", fringe="textured",
                           hair_color="#4a3322", skin="warm", expression="serious", beard="stubble",
                           message="a male body with the tension and weight shift of classical sculpture", seed=11)


def build(canvas, light, brief):
    from atelier import light as make_light
    light = make_light("rembrandt", azimuth=-48, elevation=40, wrap=0.15, shadow_tint="#5e4c40")
    W, H = canvas.width, canvas.height
    horizon = H * 0.68
    sc.sky(canvas, "#27303c", "#a88a5e", horizon)
    sc.mountains(canvas, horizon, H * 0.1, "#545a50", depth=0.9, seed=5, facets=0.4)
    sc.hills(canvas, horizon + 10, H * 0.035, "#44432f", depth=0.7, seed=6)
    sc.ground(canvas, horizon + 20, "#352e22", far_color="#4e4532", depth=0.45)
    figure = Figure(sex="male", pose="david", turn=16, heads=7.9, hands={"l": "relaxed", "r": "relaxed"})
    character = brief.character(figure, hair=Hair("crop", "textured", brief.hair_color, strand=0.4, seed=brief.seed),
                                outfit=[w.loincloth("#e4d9c2", length=1.05)])
    placement = compose.framing(canvas, "full", x=W * 0.5)
    sc.contact_shadow(canvas, placement["x"] + 30, placement["ground_y"] - 6, W * 0.42, strength=0.7)
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **placement)
    return {"views": [view], "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "figure_classical_male.png")
