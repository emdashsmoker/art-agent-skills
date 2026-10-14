"""Character in a city street, theatrical-anime manner: painted background + cel figure + compositing.

The street is built in one-point perspective with dressed facades, lamps and wires; buildings cast the low sun's
shadows. The figure is sized from the same camera so she stands in the scene.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, city, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="scene", style="anime_film", purpose="concept", lighting="golden_hour", background="city",
                           hair_style="bob", fringe="swept", hair_color="#2a2530", eye_color="#5f7fa8", pose="walk",
                           message="someone walking a sunset street on the way home", seed=11)
WALLS = ["#c9a27e", "#a9b7a0", "#b98b7a", "#d3c6a6", "#8fa3b5", "#c2a0a0"]


def build(canvas, light, brief):
    from atelier import light as make_light
    light = make_light("golden_hour", azimuth=-58, elevation=22, haze_strength=0.5)
    W, H = canvas.width, canvas.height
    horizon = H * 0.47
    sc.sky(canvas, "#5a7fb8", "#f6d2a4", horizon, glow=(W * 0.5, horizon - 20, W * 0.3))
    sc.clouds(canvas, 0.3, 0, horizon * 0.8, color="#ffe9cf", shadow="#b08fa6", seed=3, wispy=0.5)
    sc.skyline(canvas, horizon + 3, H * 0.26, "#7a7f9a", depth=0.88, seed=4)
    camera = sc.Perspective(canvas, horizon, eye=1.5, focal=1.05)
    with canvas.layer(depth=0.6):
        canvas.add(camera.ground_quad(-60, 60, 1.0, 300), "#9a8f8a", "ground", normal=(0, -1, 0.05))
    city.road(camera, -3.4, 3.4, 1.0, 300, color="#5f5c62", crossing=7.5)
    city.sidewalk(camera, -7.0, -3.4, 1.0, 300, color="#a89c94")
    city.sidewalk(camera, 3.4, 7.0, 1.0, 300, color="#a89c94")
    buildings = []
    for side in (-1, 1):
        z = 70.0
        for i in range(9):                  # far to near, so nearer buildings overlap farther ones
            width, depth = 8.0, [7.0, 9.0, 6.0][i % 3]
            height = [9.5, 13.0, 16.5, 7.5, 12.0][(i * 2 + (side > 0)) % 5]
            x = 7.2 if side > 0 else -7.2 - width
            buildings.append(city.building(camera, x, z - depth, width, depth, height, WALLS[(i + (side > 0) * 3) % len(WALLS)],
                                           kind=["apartment", "old", "apartment", "house"][(i + side) % 4], light=light,
                                           sky="#e8c9a8", awning=["#2f5f6f", None, "#a8433a"][i % 3], seed=i * 3 + (side > 0)))
            z -= depth + 0.5
    poles = []
    for z in (52, 36, 22, 10):
        city.lamp(camera, 3.9, z, height=5.2)
        poles.append(city.utility_pole(camera, -3.9, z + 4, height=8.0))
    city.wires(camera, [p[0] for p in poles])
    city.wires(camera, [p[1] for p in poles], sag=0.7)
    city.car(camera, 1.6, 16, "#d8d4cc", sky="#e8c9a8")
    for k, (x, z) in enumerate([(5.0, 13), (-5.2, 18), (4.6, 27)]):
        city.pedestrian(camera, x, z, color=["#3d4a5c", "#8a5a44", "#2c2c30"][k], seed=k)
    city.cast_shadows(camera, light, buildings)
    distance = 5.2                          # metres from the camera to the figure
    scale = camera.scale(distance)          # design units per metre at that distance
    foot_x, foot_y = camera.point(-1.5, 0.0, distance)
    figure = Figure(pose="walk", turn=-28, heads=7.7)
    figure.set_pose(head=(0, 16, 0))
    character = brief.character(figure, hair=Hair("bob", "swept", brief.hair_color),
                                outfit=[w.top("#efe9dc", "long"), w.skirt("#3a3f55", hem=2.4),
                                        w.coat("#b89a72", hem=2.9, detail=w.open_front("#efe9dc")), w.shoes("#2a2428")])
    sc.contact_shadow(canvas, foot_x + 0.5 * scale, foot_y - 4, 1.3 * scale, 0.16 * scale, strength=0.6)
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, foot_x, ground_y=foot_y, height=1.66 * scale, light=light)
    return {"views": [view], "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "scene_anime_film.png")
