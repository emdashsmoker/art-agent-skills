"""Rainy night street in a retro cel-anime manner: a woman under a red umbrella on wet, light-streaked asphalt.

The street is one-point perspective with lit windows, shop signs and lamps. The umbrella rests on her shoulder
and tilts back, so its open inside frames her head. Rain falls in two bands (behind her and before the lens), and
the wet road mirrors every lit thing standing on it, her included.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from atelier import Brief, Figure, Hair, city, light as make_light, props, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="scene", style="retro_anime", format="portrait", framing="full",
                           composition="thirds_right", pose="relaxed", outfit="coat", lighting="night", background="city",
                           mood="melancholic", hair_style="long", fringe="swept", hair_color="#1f1b26", eye_color="#6d5a8a",
                           finish="glow", message="비 오는 밤, 젖은 거리에 우산을 쓰고 홀로 선 사람", seed=31)
WALLS = ["#4d5468", "#5b5468", "#465a62", "#62586a", "#4a4f5e"]
SKY = "#2a3358"


def build(canvas, light, brief):
    light = make_light("night", azimuth=-35, elevation=38, color="#c8c4e8", shadow_tint="#6c6a9c", haze="#3a4372",
                       haze_strength=0.55)
    W, H = canvas.width, canvas.height
    horizon = H * 0.43
    sc.sky(canvas, "#0f1430", "#3a4372", horizon, glow=(W * 0.42, horizon, W * 0.35), glow_color="#6a5a8a")
    camera = sc.Perspective(canvas, horizon, eye=1.25, focal=1.0, centre_x=W * 0.42)
    with canvas.layer(depth=0.6):
        canvas.add(camera.ground_quad(-60, 60, 0.5, 300), "#2c2d3a", "road", normal=(0, -1, 0.05))
    city.road(camera, -3.2, 3.2, 0.5, 300, color="#2a2b36", line="#5c5c68", crossing=None)
    city.sidewalk(camera, -6.4, -3.2, 0.5, 300, color="#3a3a46")
    city.sidewalk(camera, 3.2, 6.4, 0.5, 300, color="#3a3a46")
    buildings = []
    for side in (-1, 1):
        z = 80.0
        for i in range(10):                 # far to near so nearer blocks overlap farther ones
            width, depth = 7.0, [6.0, 8.0, 5.0][i % 3]
            height = [10.0, 14.0, 8.0, 12.0, 16.0][(i * 2 + (side > 0)) % 5]
            x = 6.6 if side > 0 else -6.6 - width
            buildings.append(city.building(camera, x, z - depth, width, depth, height, WALLS[(i + 2 * (side > 0)) % len(WALLS)],
                                           kind=["apartment", "old", "apartment"][(i + side) % 3], light=light, night=True,
                                           sky=SKY, awning=["#7a2f3a", None, "#2f5f6f"][i % 3], seed=i * 5 + (side > 0)))
            z -= depth + 0.4
    for z in (44, 28, 16):
        city.lamp(camera, 3.6, z, height=5.0, night=True, glow="#ffd59a")
        city.lamp(camera, -3.6, z + 8, height=5.0, night=True, glow="#ffd59a")
    city.car(camera, -1.5, 22, "#8a2f2f", night=True, sky=SKY, facing=-1)
    city.pedestrian(camera, 4.6, 19, color="#1c1e28", seed=2)
    city.pedestrian(camera, -4.8, 30, color="#22242e", seed=5)
    city.cast_shadows(camera, light, buildings)
    sc.weather(canvas, "rain", near=0.12, amount=1.2, wind=0.12, seed=brief.seed)

    distance = 3.0                          # metres from the camera to her feet
    scale = camera.scale(distance)
    foot_x, foot_y = camera.point(0.75, 0.0, distance)
    figure = Figure(pose="relaxed", turn=-18, heads=7.6)
    figure.set_pose(head=(4, -10, 4), l_shoulder=(0, 0, 8))
    figure.reach("r", (0.05, 5.55, 0.62), anchor="chest")             # grip held in front of the chest
    figure.hands = {"r": "fist", "l": "relaxed"}
    character = brief.character(figure, hair=Hair("long", "swept", brief.hair_color, wave=0.15, seed=brief.seed),
                                expression="gentle", gaze=(-0.15, 0.05),
                                outfit=[w.top("#d9d2c6", "long", detail=w.neckline("v", 0.18, 0.16)),
                                        w.skirt("#2c2f44", hem=2.3),
                                        w.coat("#b49a78", hem=2.6, detail=w.open_front("#d9d2c6")), w.shoes("#1b1a20")])
    sc.contact_shadow(canvas, foot_x, foot_y - 3, 0.9 * scale, 0.14 * scale, strength=0.55)
    with canvas.layer(depth=0.3, group="figure"):
        view = character.place(canvas, foot_x, ground_y=foot_y, height=1.66 * scale)
        character.build(view)                                           # relief first: the fist's place is known
        fist = view.group_mask("hand_r") > 0.5
        ys, xs = np.nonzero(fist)
        grip = (xs.mean() / canvas.scale, ys.mean() / canvas.scale)
        head, unit = view.joint("head"), view.unit
        # The umbrella rests on her right shoulder and leans back: its inside frames her head.
        canopy = dict(hand=grip, centre=(head[0] - unit * 0.75, head[1] - unit * 1.3), radius=unit * 2.6,
                      color="#c8403a", inner="#9a3036", view=0.42, outline=1.4)
        props.umbrella(canvas, part="back", **canopy)
        character.paint(view, light=light, self_shadow=0.45)
        props.umbrella(canvas, part="front", clip=1.0 - fist.astype("float32"), **canopy)
    ground = canvas.region_mask("road", "sidewalk", "ground", "crossing", "kerb")
    sc.wet_reflection(canvas, ground.astype("float32"), light, strength=0.5, streak=1.2, glow=0.9, seed=brief.seed)
    sc.weather(canvas, "rain", near=0.75, amount=0.9, wind=0.12, seed=brief.seed + 1)
    return {"views": [view], "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "scene_rain_night.png")
