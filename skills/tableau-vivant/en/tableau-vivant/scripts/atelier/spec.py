"""Declarative picture spec (a dict / JSON file) -> finished image.

The spec is the record of every decision made in the planning stage, so a picture can be
re-rendered, varied or handed to someone else. See references/spec.md for every field.
"""
import json
import numpy as np

from .scene import Scene
from .styles import render_style

# Outdoor presets: set_landscape arguments + optional forest + a default camera for figure-less views.
LANDSCAPES = {
    "meadow": dict(landscape=dict(ground="meadow", hills=1.2, ridges=3, clouds=0.45, tufts=160, rocks=4, path=True),
                   forest=dict(count=26, kinds=("broadleaf",), area=(-45, 45, 14, 70), min_distance=5.0, grouping=0.5),
                   camera=dict(eye=(0, -9, 1.7), target=(0, 30, 2.2), fov=46)),
    "hills": dict(landscape=dict(ground="grass", hills=5.0, ridges=4, clouds=0.5, flat_radius=8.0, tufts=110, rocks=9, path=True),
                  forest=dict(count=36, kinds=("broadleaf", "cypress"), area=(-60, 60, 12, 75), min_distance=4.5, grouping=0.5),
                  camera=dict(eye=(0, -10, 3.0), target=(0, 40, 2.0), fov=48)),
    "mountain_lake": dict(landscape=dict(ground="grass", hills=1.5, mountains=24.0, water_level=-0.8, basin=(4.0, 15.0, 27.0), ridges=3,
                                         snow_line=13.0, clouds=0.35, haze_distance=95.0, mountain_start=0.37, flat_radius=9.0, tufts=130, rocks=10),
                          forest=dict(count=80, kinds=("pine",), area=(-60, 60, 9, 66), min_distance=3.2, height=(6.0, 12.0), grouping=0.6),
                          camera=dict(eye=(0, -9, 3.4), target=(0, 40, 7.5), fov=56)),
    "seaside": dict(landscape=dict(ground="sand", hills=0.5, water_level=-0.4, shore=(4.0, 0.10), ridges=0, clouds=0.4, flat_radius=6.0, tufts=30, rocks=5),
                    forest=dict(count=6, kinds=("palm",), area=(-12, 12, 2, 7), min_distance=5.0, height=(6.0, 9.0), clearing=5.0),
                    camera=dict(eye=(0, -7, 2.8), target=(0, 30, 0.0), fov=48)),
    "forest": dict(landscape=dict(ground="grass", hills=1.0, ridges=0, clouds=0.3, haze_distance=45.0, tufts=150, rocks=6, path=True),
                   forest=dict(count=60, kinds=("broadleaf", "birch", "pine"), area=(-35, 35, 2, 60), min_distance=3.2, height=(7.0, 13.0), clearing=3.5),
                   camera=dict(eye=(0, -7, 1.7), target=(0, 20, 3.0), fov=50)),
    "desert": dict(landscape=dict(ground="sand", hills=4.0, ridges=2, clouds=0.1, roughness=0.15, haze_distance=160.0, rocks=8),
                   forest=None, camera=dict(eye=(0, -10, 2.0), target=(0, 40, 2.0), fov=50)),
    "snow": dict(landscape=dict(ground="snow", hills=2.5, mountains=24.0, ridges=3, clouds=0.5, snow_line=-10.0, rocks=7),
                 forest=dict(count=40, kinds=("pine",), area=(-50, 50, 10, 70), min_distance=3.5, height=(6.0, 11.0), grouping=0.6),
                 camera=dict(eye=(0, -10, 2.0), target=(0, 40, 5.0), fov=50)),
    "garden": dict(landscape=dict(ground="meadow", hills=0.4, ridges=2, clouds=0.4, flat_radius=14.0, tufts=70, path=True),
                   forest=dict(count=10, kinds=("cypress", "sakura"), area=(-22, 22, 8, 40), min_distance=5.0, height=(5.0, 9.0)),
                   camera=dict(eye=(0, -8, 1.7), target=(0, 20, 2.0), fov=46)),
    "city": dict(landscape=dict(ground="asphalt", hills=0.0, ridges=0, clouds=0.3, haze_distance=160.0, flat_radius=200.0),
                 forest=None, city=dict(count=18), camera=dict(eye=(1.2, -7, 1.7), target=(-0.5, 40, 8.0), fov=58)),
    # post-war panel-block estates (the doomer pictures): snow-covered yard, or a road between the blocks
    "estate": dict(landscape=dict(ground="snow", hills=0.0, ridges=0, clouds=0.8, flat_radius=200.0, haze_distance=140.0,
                                  snow_line=-10.0),
                   forest=None, estate=dict(layout="courtyard"), camera=dict(eye=(0, -8, 1.7), target=(0, 40, 9.0), fov=56)),
    "estate_street": dict(landscape=dict(ground="snow", hills=0.0, ridges=0, clouds=0.8, flat_radius=200.0, haze_distance=110.0,
                                         snow_line=-10.0),
                          forest=None, estate=dict(layout="street"), camera=dict(eye=(1.5, -6, 1.6), target=(-0.5, 60, 6.0), fov=56)),
    "plain": dict(landscape=dict(ground="grass", hills=0.5, ridges=2, clouds=0.45, tufts=120), forest=None,
                  camera=dict(eye=(0, -9, 1.7), target=(0, 30, 2.0), fov=46)),
}


# detail level -> (long side in pixels, supersampling)
DETAIL = {"draft": (640, 1), "standard": (1024, 2), "fine": (1536, 2), "max": (2048, 2)}
DEFAULT_ASPECT = "4:5"


def canvas_size(canvas):
    """Resolve width/height from explicit numbers or from aspect ('3:4', '16:9', ...) and detail level."""
    long_side, supersample = DETAIL[canvas.get("detail", "standard")]
    if "width" in canvas and "height" in canvas:
        return int(canvas["width"]), int(canvas["height"]), canvas.get("supersample", supersample)
    a, b = (float(v) for v in str(canvas.get("aspect", DEFAULT_ASPECT)).split(":"))
    scale = long_side / max(a, b)
    snap = lambda v: int(round(v * scale / 8) * 8)          # multiples of 8 keep downsampling exact
    return snap(a), snap(b), canvas.get("supersample", supersample)


def build_scene(spec):
    canvas = spec.get("canvas", {})
    width, height, supersample = canvas_size(canvas)
    scene = Scene(width, height, canvas.get("seed", 7), supersample)
    env = dict(spec.get("environment", {"type": "plain_color"}))
    kind = env.pop("type", "plain_color")
    default_camera = None
    if kind == "studio":
        scene.set_studio(**env)
    elif kind == "room":
        scene.set_room(**env)
    elif kind == "landscape":
        preset = LANDSCAPES[env.pop("preset", "meadow")]
        forest = env.pop("forest", preset["forest"])
        city = env.pop("city", preset.get("city"))
        estate = env.pop("estate", preset.get("estate"))
        scene.set_landscape(**{**preset["landscape"], **env})
        if forest:
            scene.add_forest(**forest)
        if city:
            scene.add_city(**city)
        if estate:
            scene.add_estate(**estate)
        default_camera = preset["camera"]
    elif kind == "plain_color":
        scene.set_background(env.get("color", (1, 1, 1)))
    else:
        raise KeyError(f"unknown environment type '{kind}'")
    for tree in spec.get("trees", []):
        scene.add_tree(**tree)
    # props first, so people can face them ("facing": "table"); props held in a hand come after the people
    held = [prop for prop in spec.get("props", []) if prop.get("held_by")]
    for prop in spec.get("props", []):
        if not prop.get("held_by"):
            scene.add_prop(**prop)
    for figure in spec.get("figures", []):
        scene.add_figure(**figure)
    for pair in spec.get("pairs", []):
        scene.add_pair(**pair)
    for group in spec.get("groups", []):
        scene.add_group(**group)
    for prop in held:
        scene.add_prop(**prop)
    for light in spec.get("lights", []):
        scene.add_light(**light)
    camera = spec.get("camera")
    if camera is None:
        people_in = spec.get("figures") or spec.get("pairs") or spec.get("groups")
        if default_camera and not people_in:
            camera = default_camera
        elif spec.get("pairs") or spec.get("groups") or len(spec.get("figures", [])) > 1:
            camera = {"fit": "all", "pitch": 4.0, "fill": 0.85}
        elif spec.get("figures"):
            camera = {"subject": spec["figures"][0].get("name", "figure")}
        else:
            camera = {"fit": "all", "pitch": 18.0}
    scene.set_camera(**camera)
    if spec.get("light"):
        scene.set_light(**spec["light"])
    return scene


def render(spec, style=None):
    """Render a spec. `style` overrides spec['style'] (a name or a dict with 'name' + parameters)."""
    scene = build_scene(spec)
    frame = scene.frame()
    return paint(frame, spec, style), frame


def paint(frame, spec, style=None):
    """Paint an existing Frame; lets one scene be tried in several styles without rebuilding it."""
    chosen = style if style is not None else spec.get("style", "clay")
    chosen = {"name": chosen} if isinstance(chosen, str) else dict(chosen)
    name = chosen.pop("name")
    return render_style(frame, name, post_options=spec.get("post"), **chosen)


def save(image, path):
    from PIL import Image
    Image.fromarray((np.clip(image, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
