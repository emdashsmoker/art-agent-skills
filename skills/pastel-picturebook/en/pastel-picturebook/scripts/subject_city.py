"""City street in one-point perspective, by day or by night.

The street is a small 3D model in metres (X right, Y up, Z away from the
viewer). Every wall, window, road marking and pole is a flat polygon in that
space, projected to the canvas and painted far to near. Because sizes are
real, perspective does all the shrinking and converging by itself.

At night every light source is also written to a glow layer. At the end the
glow layer blooms (soft halos) and is mirrored into the wet road: a light on a
wall at height h above its base reflects h below that base, so each screen
column is mirrored about the line where the building meets the ground.
"""
import cv2
import numpy as np

import kit
import relief
from figure import Figure
from painter import Scene, run_hook
from raster import blur, fill, fill_many, mask_box, mix, multiply, noise, over, rgb, screen, smoothstep, stroke, stroke_many, taper

UNIT_SHARE = 0.19
FOCUS = {"sky": 0.05, "ground": 0.3, "building": 0.55, "detail": 0.75}
# Nothing nearer than this (m) is drawn; it would project off the canvas.
NEAR_CLIP = 1.6
FLOOR_HEIGHT, WINDOW_PITCH, SHOP_HEIGHT = 3.0, 2.2, 3.4
# How far a building's shadow reaches on the ground per metre of height (sideways, along the street).
SHADOW_REACH = (0.55, 0.25)
# Share of windows lit by day (reflecting sky); the night share is a setting.
DAY_LIT_SHARE = 0.18
# Night: lamp arm reach over the road (m), lamp height (m), radius of its light pool on the ground (m).
LAMP_REACH, LAMP_HEIGHT, LAMP_POOL = 1.6, 8.4, 4.5
# Bloom: (blur radius as a share of canvas width, strength) for a tight and a wide halo.
BLOOM = ((0.004, 0.9), (0.025, 0.55))
# Reflections are smeared downward over this share of the canvas height, as on wet asphalt.
STREAK_SHARE = 0.06
# Shop signs carry 2 to 5 glyph blocks, stacked like the characters of a vertical sign.
GLYPHS = (2, 6)
# Width (m) of one pane of a shop window.
SHOP_PANE = 2.4
NIGHT_FOLIAGE_LEVEL = 0.85


class Camera:
    """Pinhole camera at eye height looking down the street."""

    def __init__(self, size, spec):
        height, width = size
        self.center = np.array([spec["vanish_x"] * width, spec["horizon_y"] * height])
        self.focal = spec["focal"] * width
        self.eye = spec["eye_height"]

    def project(self, points):
        pts = np.atleast_2d(np.asarray(points, np.float64))
        z = np.maximum(pts[:, 2], NEAR_CLIP)
        return np.column_stack([self.center[0] + self.focal * pts[:, 0] / z,
                                self.center[1] - self.focal * (pts[:, 1] - self.eye) / z])


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light),
                 seed=spec["seed"], spec=spec)
    fig.focus = np.full(fig.size, FOCUS["sky"], np.float32)
    return fig


def emit(scene, mask, color, strength):
    """Record a light source in the glow layer (night only)."""
    if scene.glow is not None and scene.shade_on:
        box = mask_box(mask)
        if box is not None:
            scene.glow[box] += mask[box][..., None] * np.asarray(color, np.float32) * strength


def night_style(style):
    """The style with its night colours laid over the day ones."""
    palette = dict(style["palette"])
    for group in ("city", "foliage", "trunk"):
        if f"{group}_night" in palette:
            palette[group] = {**palette[group], **palette[f"{group}_night"]}
    return {**style, "palette": palette}


def note_focus(scene, mask, level):
    scene.fig.focus = np.where(mask > 0.5, level, scene.fig.focus).astype(np.float32)


def haze(scene, color, depth):
    """Fade a colour toward the haze with distance: air is not transparent."""
    street = scene.fig.spec["street"]
    veil = (min(depth / street["length"], 1.0) ** 0.8) * street["haze"] * scene.shade_on
    return mix(np.asarray(color, np.float32), rgb(scene.style["palette"]["city"]["haze"]), veil)


def face(scene, camera, corners, color, depth, shade=0.0, ink=True):
    """Paint one flat polygon given by 3D corners. `shade` 0..1 = how far it turns from the sun."""
    tones = scene.style["palette"]["city"]
    outline = camera.project(corners)
    mask = fill(scene.size, outline)
    box = mask_box(mask)
    if box is None:
        return mask
    lit = np.asarray(color, np.float32)
    dark = lit * rgb(tones["shade_tint"])
    top, bottom = outline[:, 1].min(), outline[:, 1].max()
    rows = np.arange(box[0].start, box[0].stop, dtype=np.float32)[:, None]
    ramp = np.clip((rows - top) / max(bottom - top, 1), 0, 1) * np.ones((1, box[1].stop - box[1].start), np.float32)
    amount = scene.edge(np.clip(shade * 0.85 + ramp * 0.22, 0, 1), box)
    tint = mix(haze(scene, lit, depth), haze(scene, dark, depth), amount[..., None])
    target = scene.image[box]
    target += (tint - target) * mask[box][..., None]
    if ink:
        scene.ink(np.vstack([outline, outline[:1]]), 1.8, "city", "line", np.ones(len(outline) + 1), 0.8)
    return mask


# ------------------------------------------------------------- sky and ground
def paint_sky(scene, camera):
    tones = scene.style["palette"]["city"]
    height, width = scene.size
    horizon = camera.center[1] / height
    scene.image[:] = kit.vertical_gradient(scene.size, [(0.0, tones["sky_top"]), (horizon, tones["sky_low"]), (1.0, tones["sky_low"])])
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    puffs = noise(scene.size, width * 0.20, scene.fig.seed + 5, 4)
    band = smoothstep(rows, height * 0.05, height * 0.20) * (1 - smoothstep(rows, camera.center[1] * 0.80, camera.center[1]))
    density = np.clip((puffs - (1 - scene.fig.spec["sky"]["clouds"])) * 5.0, 0, 1) * band
    cloud = scene.edge(density) if scene.shade_on else (density > 0.5).astype(np.float32)
    over(scene.image, rgb(tones["cloud"]), cloud)
    if scene.shade_on:
        belly = scene.edge(np.clip(np.roll(density, -int(height * 0.03), axis=0) * 1.5 - 0.6, 0, 1)) * cloud
        over(scene.image, rgb(tones["cloud_shadow"]), belly, 0.8)
    if scene.glow is not None:
        paint_stars(scene, camera, 1.0 - cloud)


def paint_stars(scene, camera, clear):
    """Small points of light in the upper sky, fewer toward the glow of the city at the horizon."""
    rng = np.random.default_rng(scene.fig.seed + 23)
    height, width = scene.size
    count = scene.fig.spec["night"]["stars"]
    xs = rng.uniform(0, width, count).astype(int)
    ys = (rng.random(count) ** 1.6 * camera.center[1] * 0.85).astype(int)
    stars = np.zeros(scene.size, np.float32)
    stars[ys, xs] = rng.uniform(0.3, 1.0, count)
    stars = cv2.dilate(stars, np.ones((2, 2), np.uint8)) * clear
    screen(scene.image, rgb("#FFFFFF"), stars, 0.9)


def paint_ground(scene, camera):
    """Road, sidewalks, lane markings and a crosswalk."""
    street, tones = scene.fig.spec["street"], scene.style["palette"]["city"]
    road, far = street["road_half_width"], street["length"]
    ground = face(scene, camera, [(-60, 0, NEAR_CLIP), (60, 0, NEAR_CLIP), (60, 0, far * 4), (-60, 0, far * 4)],
                  rgb(tones["sidewalk"]), 10, ink=False)
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    toward_far = 1 - np.clip((rows - camera.center[1]) / max(scene.size[0] - camera.center[1], 1), 0, 1)
    asphalt = mix(rgb(tones["road"]), rgb(tones["haze"]), (toward_far ** 3 * 0.8 * scene.shade_on)[..., None])
    road_mask = fill(scene.size, camera.project([(-road, 0, NEAR_CLIP), (road, 0, NEAR_CLIP), (road, 0, far * 4), (-road, 0, far * 4)]))
    over(scene.image, asphalt * np.ones((1, scene.size[1], 1), np.float32), road_mask)
    marks = []
    for z in np.arange(12.0, far, 9.0):
        marks.append(camera.project([(-0.09, 0, z), (0.09, 0, z), (0.09, 0, z + 4.0), (-0.09, 0, z + 4.0)]))
    start = street["crosswalk_z"]
    for x in np.arange(-road + 0.5, road - 0.5, 1.0):
        marks.append(camera.project([(x, 0, start), (x + 0.5, 0, start), (x + 0.5, 0, start + 3.5), (x, 0, start + 3.5)]))
    for side in (-1, 1):
        marks.append(camera.project([(side * road, 0, NEAR_CLIP), (side * (road + 0.18), 0, NEAR_CLIP),
                                     (side * (road + 0.18), 0, far), (side * road, 0, far)]))
    over(scene.image, rgb(tones["mark"]), fill_many(scene.size, marks), 0.9)
    note_focus(scene, ground, FOCUS["ground"])
    return ground


def paint_ground_shadows(scene, camera, blocks, ground):
    """Shadows the sunless-side buildings throw across the street (none at night)."""
    if not scene.shade_on or scene.glow is not None:
        return
    tones = scene.style["palette"]["city"]
    side = -np.sign(scene.fig.light[0])
    shapes = []
    for block in blocks:
        if np.sign(block["x"]) != -side:
            continue
        reach, drift = block["height"] * SHADOW_REACH[0], block["height"] * SHADOW_REACH[1]
        x = block["x"]
        shapes.append(camera.project([(x, 0, block["z0"]), (x + side * reach, 0, block["z0"] + drift),
                                      (x + side * reach, 0, block["z1"] + drift), (x, 0, block["z1"])]))
    shadow = scene.soften(fill_many(scene.size, shapes), 0.006) * ground
    multiply(scene.image, rgb(tones["shade_tint"]), shadow, 0.9)


def paint_far_skyline(scene, camera):
    """Hazy towers where the street ends, so it does not stop at a bare horizon."""
    street, tones = scene.fig.spec["street"], scene.style["palette"]["city"]
    rng = np.random.default_rng(scene.fig.seed + 17)
    z = street["length"] * 1.25
    towers = []
    for x in np.arange(-70.0, 70.0, 9.0):
        wide, tall = rng.uniform(7, 12), rng.uniform(18, 60)
        towers.append(camera.project([(x, 0, z), (x + wide, 0, z), (x + wide, tall, z), (x, tall, z)]))
    over(scene.image, mix(rgb(tones["walls"][2]), rgb(tones["haze"]), 0.72 * scene.shade_on + 0.2), fill_many(scene.size, towers))


# ---------------------------------------------------------------- buildings
def lay_out_blocks(spec, rng):
    """Rows of buildings along both sides of the street, as plain boxes."""
    street = spec["street"]
    blocks = []
    for side in (-1, 1):
        z = street["first_building_z"] + rng.uniform(0, 3)
        while z < street["length"]:
            depth = rng.uniform(*street["building_depth"])
            blocks.append({"x": side * street["building_line"], "z0": z, "z1": z + depth,
                           "height": rng.uniform(*street["building_height"]), "tone": int(rng.integers(0, 1 << 30)),
                           "seed": int(rng.integers(0, 1 << 30))})
            z += depth + (rng.uniform(1.5, 3.0) if rng.random() < 0.25 else 0.0)
    return sorted(blocks, key=lambda block: -block["z0"])


def window_quads(block, rng, lit_share):
    """Window rectangles on the street wall, as (corners, lit?) in 3D."""
    floors = int((block["height"] - SHOP_HEIGHT) / FLOOR_HEIGHT)
    columns = max(int((block["z1"] - block["z0"]) / WINDOW_PITCH), 1)
    pitch = (block["z1"] - block["z0"]) / columns
    x = block["x"]
    quads = []
    for floor in range(floors):
        y0 = SHOP_HEIGHT + floor * FLOOR_HEIGHT + 0.9
        for column in range(columns):
            z0 = block["z0"] + (column + 0.22) * pitch
            quads.append(([(x, y0, z0), (x, y0, z0 + pitch * 0.56), (x, y0 + 1.45, z0 + pitch * 0.56), (x, y0 + 1.45, z0)],
                          rng.random() < lit_share))
    return quads


def floor_lines(block, camera):
    """Thin ledges under each row of windows: they give a plain wall its storeys."""
    floors = int((block["height"] - SHOP_HEIGHT) / FLOOR_HEIGHT)
    x = block["x"]
    return [camera.project([(x, SHOP_HEIGHT + floor * FLOOR_HEIGHT + 0.62, block["z0"]),
                            (x, SHOP_HEIGHT + floor * FLOOR_HEIGHT + 0.62, block["z1"]),
                            (x, SHOP_HEIGHT + floor * FLOOR_HEIGHT + 0.80, block["z1"]),
                            (x, SHOP_HEIGHT + floor * FLOOR_HEIGHT + 0.80, block["z0"])]) for floor in range(floors)]


def paint_rooftop(scene, camera, block, rng, wall_color):
    """Roof clutter against the sky: a water tank or a stair hut on some buildings."""
    if rng.random() > 0.55:
        return
    x, side, tall = block["x"], np.sign(block["x"]), block["height"]
    z = rng.uniform(block["z0"] + 1.0, max(block["z1"] - 3.5, block["z0"] + 1.2))
    wide, high = rng.uniform(2.0, 3.2), rng.uniform(1.6, 2.6)
    inset = x + side * rng.uniform(0.8, 2.0)
    color = wall_color * 0.82
    face(scene, camera, [(inset, tall, z), (inset + side * wide, tall, z), (inset + side * wide, tall + high, z), (inset, tall + high, z)], color, z, 0.45)
    shade = 1.0 if side != -np.sign(scene.fig.light[0]) else 0.0
    face(scene, camera, [(inset, tall, z), (inset, tall, z + wide), (inset, tall + high, z + wide), (inset, tall + high, z)], color, z, shade)


def paint_block(scene, camera, block):
    """One building: front, street wall, roof trim, shop floor, windows, a sign."""
    tones = scene.style["palette"]["city"]
    rng = np.random.default_rng(block["seed"])
    x, z0, z1, tall = block["x"], block["z0"], block["z1"], block["height"]
    side = np.sign(x)
    wall_color = rgb(tones["walls"][block["tone"] % len(tones["walls"])])
    sun_side = -np.sign(scene.fig.light[0])
    wall_shade = 1.0 if side != sun_side else 0.0
    front = face(scene, camera, [(x, 0, z0), (x + side * 30, 0, z0), (x + side * 30, tall, z0), (x, tall, z0)], wall_color, z0, 0.45)
    paint_rooftop(scene, camera, block, rng, wall_color)
    wall = face(scene, camera, [(x, 0, z0), (x, 0, z1), (x, tall, z1), (x, tall, z0)], wall_color, z0, wall_shade)
    trim = wall_color * 0.72
    face(scene, camera, [(x, tall - 0.7, z0), (x, tall - 0.7, z1), (x, tall, z1), (x, tall, z0)], trim, z0, wall_shade, ink=False)
    face(scene, camera, [(x, 0, z0), (x, 0, z1), (x, SHOP_HEIGHT, z1), (x, SHOP_HEIGHT, z0)], wall_color * 0.55, z0, wall_shade, ink=False)
    glass, lit_glass = haze(scene, rgb(tones["glass"]), z0), haze(scene, rgb(tones["glass_lit"]), z0)
    night = scene.glow is not None
    quads = window_quads(block, rng, scene.fig.spec["night"]["lit"] if night else DAY_LIT_SHARE)
    dark = fill_many(scene.size, [camera.project(corners) for corners, lit in quads if not lit])
    bright = fill_many(scene.size, [camera.project(corners) for corners, lit in quads if lit])
    multiply(scene.image, rgb(tones["shade_tint"]), fill_many(scene.size, floor_lines(block, camera)) * wall, 0.45)
    over(scene.image, glass, dark * wall, 0.92)
    over(scene.image, lit_glass, bright * wall, 0.92)
    emit(scene, bright * wall, rgb(tones["glass_lit"]), 0.25)
    if night:
        paint_storefront(scene, camera, block, rng)
    awning = rgb(tones["awnings"][block["tone"] % len(tones["awnings"])])
    face(scene, camera, [(x, SHOP_HEIGHT - 0.5, z0 + 0.6), (x, SHOP_HEIGHT - 0.5, z1 - 0.6),
                         (x - side * 1.3, SHOP_HEIGHT - 1.1, z1 - 0.6), (x - side * 1.3, SHOP_HEIGHT - 1.1, z0 + 0.6)],
         awning, z0, wall_shade * 0.6)
    if rng.random() < 0.7:
        paint_sign(scene, camera, block, rng)
    note_focus(scene, np.maximum(front, wall), FOCUS["building"])
    scene.fig.shapes[f"block_{int(z0)}_{int(side)}"] = camera.project([(x, 0, z0), (x, 0, z1), (x, tall, z1), (x, tall, z0)])


def paint_sign(scene, camera, block, rng):
    """A vertical shop sign standing out from the wall, with blocks of lettering; lit at night."""
    tones = scene.style["palette"]["city"]
    x, side, z0, z1 = block["x"], np.sign(block["x"]), block["z0"], block["z1"]
    sign_z = rng.uniform(z0 + 1.0, z1 - 1.0)
    base = rng.uniform(4.5, max(block["height"] - 5.0, 5.0))
    color = rgb(tones["signs"][int(rng.integers(0, len(tones["signs"])))])
    out, tall = 1.1, 3.4
    board = face(scene, camera, [(x, base, sign_z), (x - side * out, base, sign_z), (x - side * out, base + tall, sign_z),
                                 (x, base + tall, sign_z)], color, sign_z, 0.3)
    count = int(rng.integers(*GLYPHS))
    pitch = (tall - 0.4) / count
    glyphs = []
    for k in range(count):
        y = base + 0.2 + k * pitch + pitch * 0.15
        glyphs.append(camera.project([(x - side * 0.25, y, sign_z), (x - side * (out - 0.25), y, sign_z),
                                      (x - side * (out - 0.25), y + pitch * 0.7, sign_z), (x - side * 0.25, y + pitch * 0.7, sign_z)]))
    letters = fill_many(scene.size, glyphs) * board
    over(scene.image, haze(scene, rgb(tones["glyph"]), sign_z), letters, 0.85)
    emit(scene, board, color, 0.55)
    emit(scene, letters, rgb(tones["glyph"]), 0.35)


def paint_storefront(scene, camera, block, rng):
    """Night: a lit shop window along the ground floor and the light it spills onto the pavement."""
    tones = scene.style["palette"]["city"]
    x, side, z0, z1 = block["x"], np.sign(block["x"]), block["z0"], block["z1"]
    if rng.random() > scene.fig.spec["night"]["shops"]:
        return
    color = rgb(tones["shop_light"])
    # Panes between mullions, the lower ones lit warmer: a shop interior, not a light box.
    panes = []
    count = max(int((z1 - z0 - 1.6) / SHOP_PANE), 1)
    pitch = (z1 - z0 - 1.6) / count
    for k in range(count):
        start = z0 + 0.8 + k * pitch + 0.12
        panes.append(camera.project([(x, 0.45, start), (x, 0.45, start + pitch - 0.24), (x, SHOP_HEIGHT - 1.0, start + pitch - 0.24),
                                     (x, SHOP_HEIGHT - 1.0, start)]))
    window = fill_many(scene.size, panes)
    box = mask_box(window)
    if box is None:
        return
    rows = np.arange(box[0].start, box[0].stop, dtype=np.float32)[:, None, None]
    top, bottom = box[0].start, box[0].stop
    inside = mix(rgb(tones["shop_deep"]), color, np.clip((rows - top) / max(bottom - top, 1), 0, 1) * 0.7 + 0.3)
    target = scene.image[box]
    target += (np.broadcast_to(inside, target.shape) - target) * window[box][..., None] * 0.92
    emit(scene, window, color, 0.30)
    spill = fill(scene.size, camera.project([(x, 0, z0 + 0.5), (x, 0, z1 - 0.5), (x - side * 2.6, 0, z1 + 0.5), (x - side * 2.6, 0, z0 - 0.5)]))
    spill = blur(spill, scene.size[1] * 0.006)
    screen(scene.image, color, spill, 0.35)


# ---------------------------------------------------------------- furniture
def paint_poles(scene, camera):
    """Utility poles with sagging wires along one sidewalk."""
    street, tones = scene.fig.spec["street"], scene.style["palette"]["city"]
    x = -np.sign(scene.fig.light[0]) * -1 * (street["road_half_width"] + 0.8)
    tops = []
    for z in np.arange(street["length"] * 0.9, street["first_pole_z"] - 1, -street["pole_spacing"]):
        thick = 0.14
        pole = camera.project([(x - thick, 0, z), (x + thick, 0, z), (x + thick, 9.0, z), (x - thick, 9.0, z)])
        arm = camera.project([(x - 1.1, 8.0, z), (x + 1.1, 8.0, z), (x + 1.1, 8.2, z), (x - 1.1, 8.2, z)])
        color = haze(scene, rgb(tones["pole"]), z)
        over(scene.image, color, fill_many(scene.size, [pole, arm]))
        tops.append(z)
        if scene.glow is not None:
            paint_lamp(scene, camera, x, z)
    wires = []
    for offset in (-1.0, 0.0, 1.0):
        for z_far, z_near in zip(tops[:-1], tops[1:]):
            steps = np.linspace(0, 1, 14)
            sag = 0.7 * np.sin(np.pi * steps)
            points = np.column_stack([np.full(14, x + offset), 8.1 - sag, z_far + (z_near - z_far) * steps])
            path = camera.project(points)
            wires.append((path, np.clip(18.0 / points[:, 2], 0.6, 2.2)))
        near = tops[-1]
        points = np.column_stack([np.full(10, x + offset), 8.1 - 0.5 * np.sin(np.pi * np.linspace(0, 0.5, 10)), np.linspace(near, NEAR_CLIP + 0.3, 10)])
        wires.append((camera.project(points), np.clip(18.0 / points[:, 2], 0.6, 3.0)))
    over(scene.image, rgb(tones["pole"]), stroke_many(scene.size, wires), 0.85)


def paint_lamp(scene, camera, pole_x, z):
    """Night: a street lamp on an arm over the road, and the pool of light under it."""
    tones = scene.style["palette"]["city"]
    toward_road = -np.sign(pole_x)
    lamp_x = pole_x + toward_road * LAMP_REACH
    arm = camera.project([(pole_x, LAMP_HEIGHT - 0.1, z), (lamp_x, LAMP_HEIGHT, z), (lamp_x, LAMP_HEIGHT + 0.15, z), (pole_x, LAMP_HEIGHT + 0.05, z)])
    over(scene.image, haze(scene, rgb(tones["pole"]), z), fill(scene.size, arm))
    head = camera.project([(lamp_x - 0.35, LAMP_HEIGHT - 0.12, z), (lamp_x + 0.35, LAMP_HEIGHT - 0.12, z),
                           (lamp_x + 0.35, LAMP_HEIGHT + 0.05, z), (lamp_x - 0.35, LAMP_HEIGHT + 0.05, z)])
    bulb = fill(scene.size, head)
    color = rgb(tones["lamp"])
    over(scene.image, color, bulb)
    emit(scene, bulb, color, 1.6)
    turn = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    ring = np.column_stack([lamp_x + LAMP_POOL * np.cos(turn), np.zeros(40), z + LAMP_POOL * np.sin(turn)])
    pool = blur(fill(scene.size, camera.project(ring)), scene.size[1] * 0.012)
    screen(scene.image, color, pool, 0.30)
    emit(scene, pool, color, 0.06)


def paint_cars(scene, camera):
    """Night: a few distant cars, red tail lights going away on one lane, headlights coming on the other."""
    spec, tones = scene.fig.spec, scene.style["palette"]["city"]
    rng = np.random.default_rng(scene.fig.seed + 29)
    road = spec["street"]["road_half_width"]
    cars = []
    for lane, kind in ((road * 0.5, "tail"), (-road * 0.5, "head")):
        for z in rng.uniform(25, spec["street"]["length"] * 0.8, spec["night"]["cars"]):
            cars.append((z, lane, kind))
    for z, lane, kind in sorted(cars, key=lambda car: -car[0]):
        body = camera.project([(lane - 0.9, 0.2, z), (lane + 0.9, 0.2, z), (lane + 0.85, 1.35, z), (lane - 0.85, 1.35, z)])
        over(scene.image, haze(scene, rgb(tones["car"]), z), fill(scene.size, body))
        color = rgb(tones["tail_light" if kind == "tail" else "head_light"])
        for offset in (-0.65, 0.65):
            light = camera.project([(lane + offset - 0.18, 0.62, z), (lane + offset + 0.18, 0.62, z),
                                    (lane + offset + 0.18, 0.80, z), (lane + offset - 0.18, 0.80, z)])
            spot = fill(scene.size, light)
            over(scene.image, color, spot)
            emit(scene, spot, color, 2.2 if kind == "head" else 1.4)


def finish_night(scene, camera, ground):
    """Bloom every light, then mirror the lights into the wet road."""
    if scene.glow is None or not scene.shade_on:
        return
    height, width = scene.size
    glow = scene.glow
    halo = np.zeros_like(glow)
    for share, strength in BLOOM:
        halo += cv2.GaussianBlur(glow, (0, 0), width * share) * strength
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    street = scene.fig.spec["street"]
    base = camera.center[1] + camera.eye / street["building_line"] * np.abs(cols - camera.center[0])
    source = (glow * 0.8 + halo * 0.5 + scene.image * 0.10).astype(np.float32)
    wobble = (noise(scene.size, width * 0.01, scene.fig.seed + 31, 2) - 0.5) * width * 0.006
    map_x, map_y = (cols + wobble).astype(np.float32), (2 * base - rows).astype(np.float32)
    mirrored = cv2.remap(source, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    length = max(int(height * STREAK_SHARE), 3)
    streaked = cv2.blur(mirrored, (1, length), anchor=(0, 0))
    wet = scene.fig.spec["night"]["wet"] * ground * (rows > base)
    image = scene.image
    image[:] = 1.0 - (1.0 - image) * (1.0 - np.clip(streaked * wet[..., None], 0, 1))
    image[:] = 1.0 - (1.0 - image) * (1.0 - np.clip(halo, 0, 1))


def paint_trees(scene, camera):
    """Street trees on the sunny sidewalk: a trunk and a crown of overlapping balls."""
    street, tones = scene.fig.spec["street"], scene.style["palette"]
    x = -np.sign(scene.fig.light[0]) * (street["road_half_width"] + 1.0)
    rng = np.random.default_rng(scene.fig.seed + 9)
    for z in np.arange(street["length"] * 0.6, street["first_tree_z"] - 1, -street["tree_spacing"]):
        scale = camera.focal / z
        base, crown = camera.project([(x, 0, z), (x, 4.6, z)])
        trunk = np.array([base, (base + crown) / 2, crown])
        over(scene.image, haze(scene, rgb(tones["trunk"]["base"]), z), stroke(scene.size, trunk, 0.32 * scale * taper(3, 1.0, 0.6)))
        balls = [relief.ellipsoid(scene.size, crown + scale * np.array([rng.uniform(-1.4, 1.4), rng.uniform(-1.6, 0.6)]),
                                  scale * rng.uniform(1.2, 1.9), scale * rng.uniform(1.0, 1.6)) for _ in range(6)]
        crown_part = relief.union(balls)
        edge_noise = noise(scene.size, max(scale * 0.5, 3), int(rng.integers(1 << 30)), 2)
        crown_part.mask = (crown_part.mask * (blur(crown_part.mask, scale * 0.3) + edge_noise * 0.5 > 0.62)).astype(np.float32)
        # At night only the street lamps light the crowns, from below and the side: mostly shadow.
        kit.shade_solid(scene, crown_part, "foliage", level=0.50 if scene.glow is None else NIGHT_FOLIAGE_LEVEL, spread=0.45)
        kit.ink_edges(scene, crown_part.mask, 1.8, "foliage", "line")
        note_focus(scene, crown_part.mask, FOCUS["detail"])


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    night = fig.spec.get("night", {}).get("on", False)
    scene = Scene(fig, night_style(style) if night else style, seed, shade, lines)
    scene.glow = np.zeros(fig.size + (3,), np.float32) if night else None
    camera = Camera(fig.size, fig.spec["camera"])
    blocks = lay_out_blocks(fig.spec, np.random.default_rng(fig.seed))
    paint_sky(scene, camera)
    run_hook(extras, "after_background", scene)
    ground = paint_ground(scene, camera)
    paint_far_skyline(scene, camera)
    paint_ground_shadows(scene, camera, blocks, ground)
    for block in blocks:
        paint_block(scene, camera, block)
    if night:
        paint_cars(scene, camera)
    paint_trees(scene, camera)
    paint_poles(scene, camera)
    finish_night(scene, camera, ground)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
