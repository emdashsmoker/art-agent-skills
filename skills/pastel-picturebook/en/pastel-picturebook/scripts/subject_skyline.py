"""Skylines: subjects "rooftop" (a roof terrace over the city at sunset) and "fireworks" (a riverside at night under fireworks).

Measured in centimetres from a standing person's eye height, like the park and the interiors (X right, Y up,
Z away; the viewer's floor is Y = 0), so a figure placed on the horizon ("place": "horizon") stands on the
roof or the promenade. Buildings face the viewer squarely: each front is an upright rectangle.

  time        "sunset": a low sun behind the towers, warm streaky clouds, dark backlit buildings with rims
              "night": a dark sky with stars, windows lit, their light streaking down the river
  sky         sun_x, sun_y, sun_r (shares of the picture), clouds (0..1), stars (count, night)
  fireworks   bursts: {"x", "y", "r" (shares), "color", "kind": "trail" | "dots" | "willow", "tail": bool}
  skyline     layers far to near: {"z", "height": [low, high], "width": [low, high], "gap": [low, high], "haze"}
              (height = the top's height in cm above the viewer's floor; "base" = where the fronts stop)
  river       {"z0", "z1", "level"}: water from the viewer's edge out to the far bank, mirroring what stands beyond
  floor       {"kind": "roof" | "promenade", "tile"}: the paving out to the railing
  railing     {"z", "wall", "height", "posts", "glass"}: a low wall, posts and rails across the whole view (glass panes between)
  lights      string lights overhead: [{"from": [x, y, z], "to": [x, y, z], "sag", "bulbs"}]
  plants      potted plants on the floor [{"x", "z", "radius", "height"}]
"""
import cv2
import numpy as np

import kit
from figure import Figure
from interior import make_camera, paint_floor_plant
from painter import Scene, run_hook
from raster import blur, ellipse, fill, mask_box, mix, multiply, noise, over, rgb, screen, smoothstep, stroke, stroke_many, taper

UNIT_SHARE = 0.19
FOCUS = {"sky": 0.05, "city": 0.3, "water": 0.25, "floor": 0.2, "railing": 0.45, "item": 0.6}
NEAR = 60.0
FLOOR_PITCH = 380.0           # cm between floors of a building
WINDOW = (0.42, 0.78, 0.25, 0.75)   # a window inside its cell: across from..to, up from..to (shares of the cell)
CELL_WIDTH = 300.0            # cm between window columns
RIM_WIDTH = 1.4               # px of sunset light along a building's top edge


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light), seed=spec["seed"], spec=spec)
    fig.focus = np.full(fig.size, FOCUS["sky"], np.float32)
    return fig


def note_focus(scene, mask, level):
    scene.fig.focus = np.where(mask > 0.5, np.maximum(level, scene.fig.focus), scene.fig.focus).astype(np.float32)


def tone(scene, group, name):
    return rgb(scene.style["palette"][group][name])


def is_night(scene):
    return scene.fig.spec.get("time", "sunset") == "night"


def reach_at(scene, camera, z):
    """Half the width (cm) the picture shows at depth z, plus a margin."""
    return (scene.size[1] * 0.6) / camera.focal * z + abs(camera.position[0])


def cell_random(i, j, salt):
    """A repeatable random number 0..1 for each window cell (i, j) of a building."""
    value = np.sin(i * 12.9898 + j * 78.233 + salt * 37.719) * 43758.5453
    return value - np.floor(value)


# ------------------------------------------------------------------ sky
def paint_sky(scene, camera):
    """Sunset: violet to gold with the sun's glow and streaks of lit cloud. Night: deep blue with stars."""
    height, width = scene.size
    spec, sky = scene.fig.spec["sky"], scene.style["palette"]["sky"]
    horizon = camera.center[1] / height
    if is_night(scene):
        stops = [(0.0, sky["night_top"]), (horizon * 0.7, sky["night_middle"]), (horizon, sky["night_low"]), (1.0, sky["night_low"])]
        scene.image[:] = kit.vertical_gradient(scene.size, stops)
        if scene.shade_on:
            rng = np.random.default_rng(scene.fig.seed + 3)
            count = spec.get("stars", 160)
            stars = np.zeros(scene.size, np.float32)
            xs = rng.uniform(0, width, count).astype(int)
            ys = (rng.random(count) ** 1.5 * camera.center[1] * 0.8).astype(int)
            stars[ys, xs] = rng.uniform(0.3, 1.0, count)
            screen(scene.image, rgb("#FFFFFF"), cv2.dilate(stars, np.ones((2, 2), np.uint8)), 0.8)
        return
    stops = [(0.0, sky["top"]), (horizon * 0.45, sky["middle"]), (horizon * 0.82, sky["low"]), (horizon, sky["horizon"]), (1.0, sky["horizon"])]
    scene.image[:] = kit.vertical_gradient(scene.size, stops)
    sun = np.array([spec["sun_x"] * width, spec["sun_y"] * height])
    radius = spec["sun_r"] * width
    if scene.shade_on:
        halo = blur(fill(scene.size, ellipse(sun, radius * 7, radius * 4, 48)), radius * 6)
        screen(scene.image, rgb(sky["glow"]), halo, 0.85)
    paint_streak_clouds(scene, camera, sun)
    over(scene.image, rgb(sky["sun"]), fill(scene.size, ellipse(sun, radius, radius, 48)))


def paint_streak_clouds(scene, camera, sun):
    """Long thin clouds: dark violet bellies, edges lit gold and pink nearest the sun."""
    height, width = scene.size
    amount, sky = scene.fig.spec["sky"].get("clouds", 0.4), scene.style["palette"]["sky"]
    if amount <= 0:
        return
    stretched = cv2.resize(noise((max(height // 4, 8), max(width // 40, 8)), 3.0, scene.fig.seed + 5, 3), (width, height),
                           interpolation=cv2.INTER_CUBIC)
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    band = smoothstep(rows, height * 0.04, height * 0.12) * (1 - smoothstep(rows, camera.center[1] * 0.82, camera.center[1] * 0.97))
    density = np.clip((stretched - (1.0 - amount)) * 5.0, 0.0, 1.0) * band
    cloud = scene.edge(density) if scene.shade_on else (density > 0.5).astype(np.float32)
    near_sun = np.exp(-(((cols - sun[0]) / (width * 0.35)) ** 2 + ((rows - sun[1]) / (height * 0.3)) ** 2))
    over(scene.image, mix(rgb(sky["cloud"]), rgb(sky["cloud_warm"]), near_sun[..., None] * 0.7), cloud, 0.95)
    if scene.shade_on:
        under = np.clip(cloud - np.roll(cloud, -max(int(height * 0.006), 1), axis=0), 0, 1)
        over(scene.image, rgb(sky["cloud_lit"]), blur(under, 1.0) * (0.3 + 0.7 * near_sun), 0.9)


def paint_fireworks(scene, camera):
    """Bursts of light: rays drooping under gravity, brightest at their tips, a glow and a halo on the smoke."""
    bursts = scene.fig.spec.get("fireworks", [])
    height, width = scene.size
    rng = np.random.default_rng(scene.fig.seed + 7)
    for burst in bursts:
        center = np.array([burst["x"] * width, burst["y"] * height])
        radius = burst["r"] * width
        color = rgb(burst["color"])
        kind = burst.get("kind", "trail")
        droop = {"trail": 0.12, "dots": 0.08, "willow": 0.55}[kind]
        rays = burst.get("rays", 64)
        inner, outer, sparks = [], [], []
        for k in range(rays):
            turn = 2 * np.pi * k / rays + rng.uniform(-0.04, 0.04)
            reach = radius * rng.uniform(0.82, 1.0)
            heading = np.array([np.cos(turn), np.sin(turn)])
            t = np.linspace(0.12, 1.0, 14)
            path = center + heading[None, :] * reach * t[:, None] + np.array([0.0, 1.0])[None, :] * droop * radius * (t ** 2)[:, None]
            thick = max(radius * 0.012, 1.0)
            if kind == "dots":
                # A peony: stars along each ray, biggest and densest at its end.
                for share in np.sort(rng.uniform(0.25, 1.0, 4)):
                    point = path[int(round(share * (len(path) - 1)))] + rng.normal(0, radius * 0.015, 2)
                    sparks.append(ellipse(point, thick * (0.4 + 1.4 * share), thick * (0.4 + 1.4 * share), 10))
            else:
                inner.append((path[:7], thick * taper(7, 0.0, 0.6, 1.0)))
                outer.append((path[6:], thick * taper(len(path) - 6, 0.6, 1.0, 1.0) * (1.6 if kind == "willow" else 1.2)))
                if rng.random() < 0.35:
                    tip = path[-1] + rng.normal(0, radius * 0.05, 2)
                    sparks.append(ellipse(tip, thick, thick, 8))
        layer = np.zeros(scene.size, np.float32)
        if inner:
            layer = np.maximum(layer, stroke_many(scene.size, inner) * 0.45)
            layer = np.maximum(layer, stroke_many(scene.size, outer))
        for spark in sparks:
            np.maximum(layer, fill(scene.size, spark), out=layer)
        if scene.shade_on:
            halo = blur(fill(scene.size, ellipse(center, radius * 1.15, radius * 1.15, 48)), radius * 0.45)
            screen(scene.image, color, halo, 0.22)
            screen(scene.image, color, np.clip(blur(layer, radius * 0.03) * 1.6, 0.0, 1.0), 0.9)
        screen(scene.image, mix(color, rgb("#FFFFFF"), 0.55), layer, 1.0)
        if burst.get("tail"):
            base_y = camera.center[1]
            ys = np.linspace(base_y, center[1] + radius * 0.15, 16)
            xs = center[0] + np.sin(np.linspace(0, 3 * np.pi, 16)) * radius * 0.02
            trail = stroke(scene.size, np.column_stack([xs, ys]), max(radius * 0.01, 1.0) * taper(16, 0.0, 1.0, 1.0))
            screen(scene.image, mix(color, rgb("#FFFFFF"), 0.4), trail, 0.7)


# ------------------------------------------------------------------ the city
def paint_city_floor(scene, camera):
    """Below the horizon, before any building: the haze over the far streets."""
    height = scene.size[0]
    rows = np.arange(height, dtype=np.float32)[:, None]
    below = np.clip(rows - camera.center[1] + 0.5, 0.0, 1.0) * np.ones((1, scene.size[1]), np.float32)
    city = scene.style["palette"]["city_night" if is_night(scene) else "city"]
    fall = np.clip((rows - camera.center[1]) / (height * 0.25), 0.0, 1.0)
    color = mix(rgb(city["haze"]), rgb(city["base"]), fall[..., None])
    over(scene.image, np.broadcast_to(color, scene.image.shape), below)


def lay_out_layer(scene, camera, layer, index, rng):
    """Buildings of one skyline layer, left to right: (x0, x1, top) in cm, plus a setback or an antenna."""
    reach = reach_at(scene, camera, layer["z"])
    x = -reach - rng.uniform(0, layer["width"][1])
    blocks = []
    while x < reach:
        wide = rng.uniform(*layer["width"])
        top = rng.uniform(*layer["height"])
        extra = rng.random()
        blocks.append({"x0": x, "x1": x + wide, "top": top, "setback": extra < 0.3, "antenna": 0.3 <= extra < 0.45,
                       "salt": index * 1000 + len(blocks)})
        x += wide + rng.uniform(*layer.get("gap", (0.0, 0.0)))
    return blocks


def paint_skyline(scene, camera):
    """Layers of buildings far to near: veiled by haze far away, windows on the nearer ones."""
    spec = scene.fig.spec
    night = is_night(scene)
    city = scene.style["palette"]["city_night" if night else "city"]
    rng = np.random.default_rng(scene.fig.seed + 11)
    height, width = scene.size
    lights = np.zeros(scene.size, np.float32)
    whole = np.zeros(scene.size, np.float32)
    for index, layer in enumerate(spec.get("skyline", [])):
        z = layer["z"]
        base = layer.get("base", spec.get("city_base", -6000.0))
        haze = layer.get("haze", 0.0) * scene.shade_on
        face_tone = mix(rgb(city["face"]), rgb(city["haze"]), haze)
        for block in lay_out_layer(scene, camera, layer, index, rng):
            parts = [(block["x0"], block["x1"], block["top"])]
            if block["setback"]:
                inset = (block["x1"] - block["x0"]) * 0.22
                parts.append((block["x0"] + inset, block["x1"] - inset, block["top"] + FLOOR_PITCH * rng.uniform(2, 6)))
            for x0, x1, top in parts:
                (left, upper), (right, lower) = camera.project([(x0, top, z), (x1, base, z)])
                if right < 0 or left > width or upper > height:
                    continue
                outline = np.array([(left, upper), (right, upper), (right, lower), (left, lower)])
                mask = fill(scene.size, outline)
                shade = mix(face_tone, mix(rgb(city["shade"]), rgb(city["haze"]), haze), rng.uniform(0.0, 0.5))
                over(scene.image, shade, mask)
                windows = window_mask(scene, camera, outline, z, block["salt"], night)
                if windows is not None:
                    glass, lit = windows
                    over(scene.image, mix(rgb(city["glass"]), rgb(city["haze"]), haze), glass * mask, 0.8)
                    lit = lit * mask
                    over(scene.image, mix(rgb(city["window_lit"]), rgb(city["haze"]), haze * 0.5), lit)
                    lights = np.maximum(lights, lit * (1.0 - haze * 0.5))
                if not night and scene.shade_on and haze < 0.6:
                    rim = stroke(scene.size, np.array([(left, upper), (right, upper)]), RIM_WIDTH)
                    over(scene.image, rgb(city["rim"]), rim, 0.7 * (1.0 - haze))
                if scene.lines_on and haze < 0.4:
                    scene.ink(np.vstack([outline, outline[:1]]), 1.0, "city", "line", np.ones(5), 0.5 * (1.0 - haze))
                whole = np.maximum(whole, mask)
            if block["antenna"]:
                foot = camera.project([((block["x0"] + block["x1"]) / 2, block["top"], z)])[0]
                tip = camera.project([((block["x0"] + block["x1"]) / 2, block["top"] + FLOOR_PITCH * 4, z)])[0]
                over(scene.image, face_tone, stroke(scene.size, np.array([foot, tip]), 1.4))
                if night:
                    beacon = fill(scene.size, ellipse(tip, 2.2, 2.2, 10))
                    over(scene.image, rgb(city["beacon"]), beacon)
                    lights = np.maximum(lights, beacon)
    if scene.shade_on and lights.max() > 0:
        screen(scene.image, rgb(city["window_lit"]), np.clip(blur(lights, width * 0.004) * 1.4, 0.0, 1.0), 0.6 if night else 0.3)
    note_focus(scene, whole, FOCUS["city"])
    return whole


def window_mask(scene, camera, outline, z, salt, night):
    """The window grid of an upright front (glass, lit), or None when the windows would be smaller than a pixel."""
    scale = camera.focal / z
    pitch_x, pitch_y = CELL_WIDTH * scale, FLOOR_PITCH * scale
    if pitch_y < 2.5:
        return None
    box = mask_box(fill(scene.size, outline), pad=1)
    if box is None:
        return None
    left, upper = outline[0]
    rows = np.arange(box[0].start, box[0].stop, dtype=np.float32)[:, None]
    cols = np.arange(box[1].start, box[1].stop, dtype=np.float32)[None, :]
    u, v = (cols - left) / pitch_x, (rows - upper) / pitch_y
    across, up = u - np.floor(u), v - np.floor(v)
    inside = ((across > WINDOW[0]) & (across < WINDOW[1]) & (up > WINDOW[2]) & (up < WINDOW[3])).astype(np.float32)
    share = scene.fig.spec.get("lit", 0.5 if night else 0.12)
    lit = inside * (cell_random(np.floor(u), np.floor(v), salt) < share)
    glass, light = np.zeros(scene.size, np.float32), np.zeros(scene.size, np.float32)
    glass[box], light[box] = inside, lit
    return glass, light


# ------------------------------------------------------------------ the river
def paint_river(scene, camera):
    """Water from the near edge to the far bank: everything beyond mirrored, lights drawn into streaks."""
    setup = scene.fig.spec.get("river")
    if not setup:
        return
    height, width = scene.size
    water_tones = scene.style["palette"]["water"]
    level = setup.get("level", -250.0)
    waterline = camera.project([(0, level, setup["z1"])])[0][1]
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    water = np.clip(rows - waterline + 0.5, 0.0, 1.0)
    depth = np.clip((rows - waterline) / max(height - waterline, 1.0), 0.0, 1.0)
    swell = setup.get("ripple", 0.004) * width * depth
    phase = noise(scene.size, width * 0.05, scene.fig.seed + 13, 2) * 6.0
    map_x = cols + swell * np.sin(rows * 0.9 / (1.0 + 2.5 * depth) + phase)
    map_y = waterline - (rows - waterline) / 0.85
    mirrored = cv2.remap(scene.image, map_x.astype(np.float32), map_y.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if scene.shade_on:
        # Lights on rippled water stretch down toward the viewer.
        bright = np.clip((mirrored.max(axis=2, keepdims=True) - 0.45) * 1.8, 0.0, 1.0) * mirrored
        streak = cv2.GaussianBlur(bright, (0, 0), sigmaX=1.2, sigmaY=height * 0.012)
        mirrored = np.clip(mirrored + streak * 0.9, 0.0, 1.0)
    mirrored = mix(mirrored, rgb(water_tones["deep"]), (0.3 + 0.35 * depth)[..., None])
    over(scene.image, mirrored, water)
    if scene.shade_on:
        rng = np.random.default_rng(scene.fig.seed + 17)
        dashes = []
        for _ in range(setup.get("waves", 140)):
            fall = rng.random() ** 0.8
            y = waterline + 3 + fall * (height - waterline)
            x, half = rng.uniform(0, width), width * rng.uniform(0.01, 0.05) * (0.3 + fall)
            dashes.append((np.array([[x - half, y], [x + half, y]]), (0.8 + 1.4 * fall) * taper(2, 1.0, 1.0)))
        screen(scene.image, rgb(water_tones["light"]), stroke_many(scene.size, dashes) * water, 0.25)
        bank = np.clip(1.0 - np.abs(rows - waterline) / 2.0, 0.0, 1.0)
        over(scene.image, rgb(water_tones["bank"]), bank, 0.8)
    note_focus(scene, water, FOCUS["water"])


# ------------------------------------------------------------------ where the viewer stands
def paint_floor(scene, camera):
    """The roof's concrete tiles or the promenade's paving, from the viewer out to the railing. Returns its mask."""
    setup, rail = scene.fig.spec["floor"], scene.fig.spec["railing"]
    tones = scene.style["palette"]["floor"]
    height, width = scene.size
    reach = reach_at(scene, camera, rail["z"])
    outline = camera.project([(-reach, 0, NEAR), (reach, 0, NEAR), (reach, 0, rail["z"]), (-reach, 0, rail["z"])])
    mask = fill(scene.size, outline)
    rows = np.arange(height, dtype=np.float32)[:, None]
    far_row = outline[2][1]
    near = np.clip((rows - far_row) / max(height - far_row, 1.0), 0.0, 1.0)
    color = mix(rgb(tones["far"]), rgb(tones["base"]), (near ** 0.7)[..., None])
    over(scene.image, np.broadcast_to(color, scene.image.shape), mask)
    if scene.shade_on:
        tile = setup.get("tile", 60.0)
        joints = []
        z = NEAR
        while z < rail["z"]:
            joints.append((camera.project([(-reach, 0, z), (reach, 0, z)]), max(1.2 * camera.focal / z, 0.5)))
            z += tile
        x = -np.floor(reach / tile) * tile
        while x < reach:
            joints.append((camera.project([(x, 0, NEAR), (x, 0, rail["z"])]), np.array([1.6, 0.6])))
            x += tile
        multiply(scene.image, rgb(tones["joint"]), stroke_many(scene.size, joints) * mask, 0.5)
        multiply(scene.image, rgb(tones["joint"]), smoothstep(noise(scene.size, 2.0, scene.fig.seed + 19, 1), 0.6, 0.8) * mask, 0.12)
        cols = np.arange(width, dtype=np.float32)[None, :]
        if is_night(scene):
            # The bursts tint the paving with their colours.
            colors = [rgb(burst["color"]) for burst in scene.fig.spec.get("fireworks", [])]
            if colors:
                screen(scene.image, np.mean(colors, axis=0), mask * (1.0 - near * 0.7), 0.18)
        else:
            # The low sun lays a warm path of light across the floor toward the viewer.
            sun_x = scene.fig.spec["sky"]["sun_x"] * width
            path = np.exp(-((cols - sun_x) / (width * (0.06 + 0.12 * near))) ** 2)
            screen(scene.image, tone(scene, "sky", "glow"), path * mask * (1.0 - near * 0.5), 0.45)
    note_focus(scene, mask, FOCUS["floor"])
    return mask


def paint_railing(scene, camera):
    """A low wall across the view, posts and rails on it; dark against the bright sky behind."""
    rail = scene.fig.spec["railing"]
    height, width = scene.size
    z = rail["z"]
    reach = reach_at(scene, camera, z)
    scale = camera.focal / z
    whole = np.zeros(scene.size, np.float32)
    if rail.get("wall", 0) > 0:
        wall = fill(scene.size, camera.project([(-reach, 0, z), (reach, 0, z), (reach, rail["wall"], z), (-reach, rail["wall"], z)]))
        over(scene.image, tone(scene, "railing", "wall"), wall)
        cap = fill(scene.size, camera.project([(-reach, rail["wall"], z - 6), (reach, rail["wall"], z - 6),
                                               (reach, rail["wall"] + 8, z - 6), (-reach, rail["wall"] + 8, z - 6)]))
        over(scene.image, tone(scene, "railing", "cap"), cap)
        if scene.shade_on:
            rows = np.arange(height, dtype=np.float32)[:, None]
            top_row = camera.project([(0, rail["wall"], z)])[0][1]
            fall = np.clip((rows - top_row) / max(rail["wall"] * scale, 1.0), 0.0, 1.0) * np.ones((1, width), np.float32)
            multiply(scene.image, tone(scene, "railing", "shadow"), fall * wall, 0.45)
        kit.ink_edges(scene, np.maximum(wall, cap), 1.2, "railing", "line", opacity=0.7)
        whole = np.maximum(whole, np.maximum(wall, cap))
    bars = []
    bottom = rail.get("wall", 0.0) + 8.0
    x = -np.floor(reach / rail["posts"]) * rail["posts"]
    post = max(5.0 * scale, 1.5)
    while x <= reach:
        bars.append((camera.project([(x, bottom, z), (x, rail["height"], z)]), post))
        x += rail["posts"]
    for y, size in ((rail["height"], 6.0), (bottom + (rail["height"] - bottom) * 0.5, 3.5)):
        bars.append((camera.project([(-reach, y, z), (reach, y, z)]), max(size * scale, 1.2)))
    if rail.get("glass"):
        # Glass panels between the posts: the city shows through, tinted, with a few slanting reflections.
        pane = fill(scene.size, camera.project([(-reach, bottom, z), (reach, bottom, z), (reach, rail["height"], z), (-reach, rail["height"], z)]))
        over(scene.image, tone(scene, "railing", "glass"), pane, 0.22)
        if scene.shade_on:
            rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
            slant = np.mod((cols + rows * 0.8) / (width * 0.11), 1.0)
            screen(scene.image, tone(scene, "railing", "shine"), pane * smoothstep(slant, 0.0, 0.04) * (1 - smoothstep(slant, 0.08, 0.16)), 0.25)
        whole = np.maximum(whole, pane)
    metal = stroke_many(scene.size, bars)
    over(scene.image, tone(scene, "railing", "metal"), metal)
    if scene.shade_on:
        top = stroke(scene.size, camera.project([(-reach, rail["height"] + 2.0, z), (reach, rail["height"] + 2.0, z)]), max(2.0 * scale, 0.8))
        over(scene.image, tone(scene, "railing", "shine"), top * metal, 0.8)
    whole = np.maximum(whole, metal)
    note_focus(scene, whole, FOCUS["railing"])
    return whole


def paint_string_lights(scene, camera):
    """Strings of bulbs hung overhead: a sagging wire, small warm bulbs and their glow."""
    strings = scene.fig.spec.get("lights", [])
    if not strings:
        return
    wires, bulbs = [], np.zeros(scene.size, np.float32)
    for string in strings:
        start, end = np.array(string["from"], np.float64), np.array(string["to"], np.float64)
        t = np.linspace(0.0, 1.0, 40)
        points = start + (end - start) * t[:, None] - np.array([0.0, 1.0, 0.0]) * string["sag"] * 4.0 * (t * (1 - t))[:, None]
        path = camera.project(points)
        wires.append((path, 1.2))
        for k in np.linspace(0, len(points) - 1, string["bulbs"]).astype(int):
            radius = max(4.0 * camera.focal / max(points[k][2], NEAR), 1.2)
            bulb_at = path[k] + [0, radius * 1.2]
            np.maximum(bulbs, fill(scene.size, ellipse(bulb_at, radius, radius * 1.25, 12)), out=bulbs)
    over(scene.image, tone(scene, "lights", "wire"), stroke_many(scene.size, wires), 0.9)
    if scene.shade_on:
        screen(scene.image, tone(scene, "lights", "glow"), np.clip(blur(bulbs, scene.size[1] * 0.006) * 2.0, 0.0, 1.0), 0.8)
    over(scene.image, tone(scene, "lights", "bulb"), bulbs)
    note_focus(scene, bulbs, FOCUS["item"])


# ------------------------------------------------------------------ the picture
def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    camera = make_camera(fig.size, fig.spec)
    paint_sky(scene, camera)
    paint_fireworks(scene, camera)
    run_hook(extras, "after_background", scene)
    paint_city_floor(scene, camera)
    paint_skyline(scene, camera)
    paint_river(scene, camera)
    floor = paint_floor(scene, camera)
    paint_railing(scene, camera)
    for plant in sorted(fig.spec.get("plants", []), key=lambda item: -item["z"]):
        paint_floor_plant(scene, camera, plant, floor)
    paint_string_lights(scene, camera)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
