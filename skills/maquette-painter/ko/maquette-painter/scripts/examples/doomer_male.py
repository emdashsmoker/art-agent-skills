"""Doomer portrait: a young man in a black beanie and hoodie smoking under a sodium lamp on a winter night.

Behind him an empty lot runs to two prefabricated blocks with a few windows still lit; the street lamp over his
shoulder rims his cap and cheek in orange while the rest of him sinks into the blue dark. Snow falls in two bands.
The doomer style drains the colour, blooms the lights and lays film grain over everything.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, city, compose, light as make_light, props, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="portrait", style="doomer", format="portrait", framing="bust", composition="thirds_left",
                           lighting="night", background="city", mood="melancholic", sex="male", hair_style="beanie",
                           hair_color="#2a2a30", eye_color="#5a5248", expression="tired", jaw="balanced", beard="stubble",
                           skin="light", outfit="hoodie", palette="doomer", message="겨울밤 가로등 아래서 담배를 문 사람", seed=101)
SODIUM = "#ffb468"
SKY = "#2a3346"


def build(canvas, light, brief):
    light = make_light("night", azimuth=58, elevation=24, color=SODIUM, shadow_tint="#3a4560", haze=SKY,
                       haze_strength=0.6, rim=0.5)
    W, H = canvas.width, canvas.height
    horizon = H * 0.6
    sc.sky(canvas, "#090c16", SKY, horizon, glow=(W * 0.86, H * 0.2, W * 0.4), glow_color="#6a5040")
    camera = sc.Perspective(canvas, horizon, eye=1.6, focal=1.0, yaw=8)
    with canvas.layer(depth=0.97):
        canvas.add(camera.ground_quad(-200, 200, 1, 400), "#5a6070", "snow", normal=(0, -1, 0.05))
    for x, z, width, storeys, seed in ((-62, 85, 48, 9, 1), (8, 120, 72, 12, 2)):
        city.building(camera, x, z, width, 12, storeys * city.PANEL_STOREY + 0.8, "#6e6c68", kind="panel", light=light,
                      night=True, sky=SKY, seed=seed)
    city.lamp(camera, 5.2, 10, height=6.2, night=True, glow=SODIUM)
    sc.weather(canvas, "snow", near=0.15, amount=0.9, wind=0.15, seed=brief.seed)

    figure = Figure(sex="male", pose="relaxed", turn=22, heads=7.8, head_scale=1.04)
    figure.set_pose(head=(9, -14, -2))
    character = brief.character(figure, hair=Hair("beanie", "none", brief.hair_color, seed=brief.seed), gaze=(-0.15, -0.1),
                                outfit=[w.hoodie("#1d1e23", strings="#b8b2a6"), w.pants("#26272c")])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **compose.framing(canvas, "bust", x=W * 0.42))
    style = character.face.style
    lip = character.face.pts([(style["mouth_w"] * 0.45, style["mouth_y"] - 0.01)])[0]
    unit = view.unit
    tip = props.cigarette(canvas, lip, (lip[0] + unit * 0.3, lip[1] + unit * 0.12), unit * 0.034)
    props.smoke(canvas, tip[0], tip[1], unit * 1.6, drift=0.1, alpha=0.4, seed=brief.seed)
    sc.weather(canvas, "snow", near=0.8, amount=0.35, wind=0.15, seed=brief.seed + 1)
    return {"views": [view], "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "doomer_male.png")
