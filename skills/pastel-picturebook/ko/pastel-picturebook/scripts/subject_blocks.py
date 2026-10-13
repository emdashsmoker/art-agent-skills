"""Housing blocks: subjects "panelka" (a courtyard between panel apartment blocks at night) and "outskirts"
(the empty field at the edge of town: pylons marching to the horizon, the blocks far away).

Measured in centimetres from a standing person's eye height, like the park and the skyline (X right, Y up,
Z away), so a figure placed on the horizon ("place": "horizon") stands in the courtyard or the field.

  sky        night or dusk: a low overcast lit from below by the town (`sky.clouds`, `sky.stars`)
  ground     snow (`ground.snow` true) or dry grass, a trodden path {"path": [[x, z], ...], "width"}, tyre `ruts` [x, ...]
  blocks     panel buildings: {"face": "front" (a wall facing the viewer at `z`, from `x0` to `x1`)
             or "side" (a wall at `x` running from `z0` to `z1`), "floors", "lit", "balconies", "doors", "salt"}
  poles      utility poles [{"x", "z", "height"}]; `wires` hang between neighbours (`wires.sag`, `wires.count`)
  lamps      sodium street lamps [{"x", "z", "height", "arm" (+1 reaches right, -1 left)}] with pools of light
  birches    bare birches [{"x", "z", "height"}]
  swing      a playground swing {"x", "z"}
  pylons     transmission towers in a line {"x", "z0", "spacing", "count", "height"} with three wires between them
  crows      {"perched": count on the wires, "flying": count}
"""
import cv2
import numpy as np

import kit
from figure import Figure
from interior import make_camera
from painter import Scene, run_hook
from raster import blur, ellipse, fill, mask_box, mix, multiply, noise, over, rgb, screen, smooth, smoothstep, stroke, stroke_many, taper

UNIT_SHARE = 0.19
FOCUS = {"sky": 0.05, "ground": 0.2, "block": 0.3, "near": 0.5}
NEAR = 60.0
FLOOR = 280.0                  # cm per storey
CELL = 330.0                   # cm per panel (one window across)
WINDOW = (0.28, 0.72, 0.30, 0.82)   # window inside its panel: across from..to, up from..to (shares)
BALCONY = (0.10, 0.90, 0.00, 0.40)  # a balcony's front inside its panel
SEAM = 3.0                     # cm, joint between panels
PARAPET = 120.0                # cm of wall above the top floor
GLOW = 0.006                   # lit window glow (share of the picture width)


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


def night(scene):
    return scene.fig.spec.get("time", "night") == "night"


def reach_at(scene, camera, z):
    return (scene.size[1] * 0.6) / camera.focal * z + abs(camera.position[0])


def step(field, low, high):
    """smoothstep whose edges may be arrays (a soft edge as wide as a pixel's footprint on a receding wall)."""
    t = np.clip((field - low) / np.maximum(high - low, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def cell_random(i, j, salt):
    value = np.sin(i * 12.9898 + j * 78.233 + salt * 37.719) * 43758.5453
    return value - np.floor(value)


def veil(scene, z):
    haze = scene.fig.spec.get("haze", {"distance": 20000.0, "amount": 0.6})
    return float(min(z / haze["distance"], 1.0) ** 0.8 * haze["amount"]) * scene.shade_on


# ------------------------------------------------------------------ sky and ground
def paint_sky(scene, camera):
    """A low overcast: dark above, lit from below near the horizon by the town; ragged cloud banks."""
    sky, spec = scene.style["palette"]["sky"], scene.fig.spec.get("sky", {})
    height, width = scene.size
    horizon = camera.center[1] / height
    key = "night" if night(scene) else "dusk"
    stops = [(0.0, sky[f"{key}_top"]), (horizon * 0.6, sky[f"{key}_middle"]), (horizon, sky[f"{key}_low"]), (1.0, sky[f"{key}_low"])]
    scene.image[:] = kit.vertical_gradient(scene.size, stops)
    if not scene.shade_on:
        return
    rows = np.arange(height, dtype=np.float32)[:, None]
    # Stratus: broad soft banks, stretched sideways, thicker toward the horizon; their undersides take the town's light.
    banks = cv2.resize(noise((max(height // 3, 8), max(width // 7, 8)), 5.0, scene.fig.seed + 3, 4), (width, height),
                       interpolation=cv2.INTER_CUBIC)
    band = smoothstep(rows, 0.0, camera.center[1] * 0.5) * (1.0 - smoothstep(rows, camera.center[1] * 0.85, camera.center[1]))
    amount = spec.get("clouds", 0.5)
    clouds = smoothstep(banks, 0.75 - amount * 0.5, 0.95 - amount * 0.3) * band * np.ones((1, width), np.float32)
    over(scene.image, rgb(sky[f"{key}_cloud"]), clouds, 0.6)
    under = np.clip(clouds - np.roll(clouds, -max(int(height * 0.02), 1), axis=0), 0.0, 1.0)
    lit = smoothstep(rows, camera.center[1] * 0.3, camera.center[1]) * np.ones((1, width), np.float32)
    over(scene.image, rgb(sky[f"{key}_lit"]), blur(under, 3.0) * lit, 0.45)
    count = spec.get("stars", 0)
    if count:
        rng = np.random.default_rng(scene.fig.seed + 5)
        stars = np.zeros(scene.size, np.float32)
        ys = (rng.random(count) ** 1.5 * camera.center[1] * 0.6).astype(int)
        stars[ys, rng.uniform(0, width, count).astype(int)] = rng.uniform(0.3, 0.9, count)
        screen(scene.image, rgb("#FFFFFF"), stars * (1.0 - clouds), 0.8)


def ground_coords(scene, camera):
    height, width = scene.size
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    drop = rows - camera.center[1]
    below = np.clip(drop + 0.5, 0.0, 1.0)
    z = camera.focal * camera.position[1] / np.maximum(drop, 0.5)
    x = camera.position[0] + (cols - camera.center[0]) * z / camera.focal
    return x, z, below


def paint_ground(scene, camera, ground):
    """Snow (or dry grass) from the horizon to the viewer, a trodden path, ruts of tyres, grass stalks."""
    setup, tones = scene.fig.spec.get("ground", {}), scene.style["palette"]["ground"]
    gx, gz, below = ground
    height = scene.size[0]
    rows = np.arange(height, dtype=np.float32)[:, None]
    near = np.clip((rows - camera.center[1]) / max(height - camera.center[1], 1.0), 0.0, 1.0)
    key = "snow" if setup.get("snow", True) else "grass"
    color = mix(rgb(tones[f"{key}_far"]), rgb(tones[f"{key}_near"]), (near ** 0.6)[..., None])
    over(scene.image, np.broadcast_to(color, scene.image.shape), below)
    if scene.shade_on:
        drifts = smoothstep(noise(scene.size, scene.size[1] * 0.03, scene.fig.seed + 7, 3), 0.4, 0.8)
        multiply(scene.image, rgb(tones[f"{key}_shadow"]), drifts * below * near, 0.35)
    path = setup.get("path")
    if path:
        points = np.array(path, np.float64)
        half = setup.get("width", 140.0) / 2
        dense = np.column_stack([np.interp(np.linspace(0, len(points) - 1, 40), np.arange(len(points)), points[:, k]) for k in range(2)])
        strip = []
        for (x0, z0), (x1, z1) in zip(dense[:-1], dense[1:]):
            strip.append(camera.project([(x0 - half, 0, z0), (x0 + half, 0, z0), (x1 + half, 0, z1), (x1 - half, 0, z1)]))
        trodden = np.zeros(scene.size, np.float32)
        for quad in strip:
            np.maximum(trodden, fill(scene.size, quad), out=trodden)
        trodden = blur(trodden, 2.0) * below
        over(scene.image, rgb(tones["path" if key == "snow" else "path_dirt"]), trodden, 0.8)
        if scene.shade_on:
            prints = smoothstep(noise(scene.size, 3.0, scene.fig.seed + 8, 1), 0.6, 0.75)
            multiply(scene.image, rgb(tones["snow_shadow"] if key == "snow" else tones["grass_shadow"]), prints * trodden, 0.4)
    ruts = setup.get("ruts")
    if ruts and scene.shade_on:
        # Tyre tracks pressed into the slush: darker, glossier strips along the road.
        tracks = []
        for offset in ruts:
            tracks.append(camera.project([(offset - 12, 0, NEAR * 2), (offset + 12, 0, NEAR * 2), (offset + 12, 0, 40000.0),
                                          (offset - 12, 0, 40000.0)]))
        lanes = np.zeros(scene.size, np.float32)
        for quad in tracks:
            np.maximum(lanes, fill(scene.size, quad), out=lanes)
        multiply(scene.image, rgb(tones["rut"]), blur(lanes, 1.5) * below, 0.55)
    if key == "grass" and scene.shade_on:
        rng = np.random.default_rng(scene.fig.seed + 9)
        tufts = []
        low = camera.focal * camera.position[1] / max(height - camera.center[1], 1.0)
        light = []
        for _ in range(setup.get("stalks", 900)):
            z = low * (2500.0 / low) ** rng.random()
            x = rng.uniform(-1, 1) * reach_at(scene, camera, z)
            tall, lean = rng.uniform(12, 40), rng.uniform(-10, 10)
            path = camera.project([(x, 0, z), (x + lean * 0.4, tall * 0.6, z), (x + lean, tall, z)])
            blade = (path, max(1.0 * camera.focal / z, 0.6) * taper(3, 1.0, 0.1, 0.0))
            (light if rng.random() < 0.35 else tufts).append(blade)
        over(scene.image, rgb(tones["stalk"]), stroke_many(scene.size, tufts) * below, 0.55)
        over(scene.image, rgb(tones["stalk_light"]), stroke_many(scene.size, light) * below, 0.5)
    note_focus(scene, below, FOCUS["ground"])


def light_pools(scene, camera, ground):
    """Warm pools of light on the ground under each lamp and in front of each lit entrance."""
    if not night(scene) or not scene.shade_on:
        return
    gx, gz, below = ground
    pools = np.zeros(scene.size, np.float32)
    for lamp in scene.fig.spec.get("lamps", []):
        head_x = lamp["x"] + lamp.get("arm", 1) * 120.0
        reach = lamp.get("height", 650.0) * 1.1
        distance = np.hypot(gx - head_x, (gz - lamp["z"]) * 1.0)
        pools = np.maximum(pools, np.exp(-(distance / reach) ** 2 * 2.0))
    screen(scene.image, tone(scene, "lamp", "pool"), pools * below, 0.75)


# ------------------------------------------------------------------ panel blocks
def facade_outline(block, top):
    """3D corners of a block's wall from the ground to `top`."""
    if block["face"] == "front":
        z = block["z"]
        return [(block["x0"], 0, z), (block["x1"], 0, z), (block["x1"], top, z), (block["x0"], top, z)]
    x = block["x"]
    return [(x, 0, block["z0"]), (x, 0, block["z1"]), (x, top, block["z1"]), (x, top, block["z0"])]


def facade_coords(camera, block, rows, cols):
    """For pixels of a wall: the position along it (cm), the height (cm) and the depth (cm)."""
    if block["face"] == "front":
        depth = np.full(rows.shape, block["z"], np.float32)
        along = camera.position[0] + (cols - camera.center[0]) * depth / camera.focal - block["x0"]
    else:
        offset = block["x"] - camera.position[0]
        depth = camera.focal * offset / np.where(np.abs(cols - camera.center[0]) < 0.5, 0.5, cols - camera.center[0])
        depth = np.where(depth > 0, depth, 1e9).astype(np.float32)
        along = depth - block["z0"]
    up = camera.position[1] - (rows - camera.center[1]) * depth / camera.focal
    return along.astype(np.float32), up.astype(np.float32), depth


def paint_block(scene, camera, block, glow):
    """One panel block: concrete wall with panel joints and streaks, rows of windows (a few lit), balconies,
    lit entrances on the ground floor, a parapet on top."""
    floors = block.get("floors", 9)
    top = floors * FLOOR + PARAPET
    outline = camera.project(facade_outline(block, top))
    mask = fill(scene.size, outline)
    box = mask_box(mask, pad=1)
    if box is None:
        return mask
    rows = np.arange(box[0].start, box[0].stop, dtype=np.float32)[:, None] * np.ones((1, box[1].stop - box[1].start), np.float32)
    cols = np.ones((box[0].stop - box[0].start, 1), np.float32) * np.arange(box[1].start, box[1].stop, dtype=np.float32)[None, :]
    along, up, depth = facade_coords(camera, block, rows, cols)
    footprint = depth / camera.focal          # cm per pixel on the wall
    side = block["face"] == "side"
    base = mix(tone(scene, "block", "wall"), tone(scene, "block", "shade"), 0.45 if side else 0.0)
    if not night(scene):
        base = mix(base, tone(scene, "block", "day"), 0.35)
    wall = np.broadcast_to(base, rows.shape + (3,)).copy()
    salt = block.get("salt", 1)
    if scene.shade_on:
        # Rain streaks down the concrete and the grime of decades.
        streaks = noise((rows.shape[0] // 6 + 2, rows.shape[1] + 2), 2.0, scene.fig.seed + salt, 2)
        streaks = cv2.resize(streaks, (rows.shape[1], rows.shape[0]), interpolation=cv2.INTER_LINEAR)
        wall = wall * (1.0 - 0.12 * step(streaks, 0.5, 0.85))[..., None]
        seam = np.maximum(SEAM, footprint * 0.8)
        joints = np.maximum(step(seam - np.abs(np.mod(along + CELL / 2, CELL) - CELL / 2), 0.0, footprint),
                            step(seam - np.abs(np.mod(up + FLOOR / 2, FLOOR) - FLOOR / 2), 0.0, footprint))
        wall = wall * (1.0 - 0.35 * joints * (up < floors * FLOOR))[..., None]
    target = scene.image[box]
    target += (wall - target) * mask[box][..., None]
    # Windows: one per panel above the ground floor; a few lit, warm or the cold blue of a television.
    col, floor = np.floor(along / CELL), np.floor(up / FLOOR)
    across, height_in = along / CELL - col, up / FLOOR - floor
    soft = np.clip(footprint / CELL, 0.01, 0.3)
    inside = (step(across, WINDOW[0] - soft, WINDOW[0]) * (1 - step(across, WINDOW[1], WINDOW[1] + soft)) *
              step(height_in, WINDOW[2] - soft, WINDOW[2]) * (1 - step(height_in, WINDOW[3], WINDOW[3] + soft)))
    inside = inside * (floor >= 1) * (floor < floors) * (along > 0)
    luck = cell_random(col, floor, salt)
    share = block.get("lit", 0.18 if night(scene) else 0.0)
    lit = inside * (luck < share)
    blue = inside * (luck >= share) * (luck < share + share * 0.25)
    dark = inside * (1.0 - (luck < share * 1.25))
    pane = mix(tone(scene, "block", "glass"), tone(scene, "block", "glass_day"), 0.0 if night(scene) else 1.0)
    target += (pane - target) * (dark * mask[box])[..., None]
    warm_choice = cell_random(col + 7, floor + 3, salt) < 0.5
    warm = np.where(warm_choice[..., None], tone(scene, "block", "lit"), tone(scene, "block", "lit_amber"))
    target += (warm - target) * (lit * mask[box])[..., None]
    target += (tone(scene, "block", "tv") - target) * (blue * mask[box])[..., None]
    if block.get("balconies") and scene.shade_on:
        rows_with = cell_random(col + 13, np.zeros_like(col), salt) < block["balconies"]
        front = (step(across, BALCONY[0], BALCONY[0] + soft) * (1 - step(across, BALCONY[1] - soft, BALCONY[1])) *
                 step(height_in, BALCONY[2], BALCONY[2] + soft) * (1 - step(height_in, BALCONY[3] - soft, BALCONY[3])))
        front = front * rows_with * (floor >= 1) * (floor < floors) * (along > 0)
        target += (mix(base, tone(scene, "block", "balcony"), 0.6) - target) * (front * mask[box])[..., None]
        edge = front * (1 - step(height_in, BALCONY[3] - soft * 3, BALCONY[3] - soft))
        target += (tone(scene, "block", "shade") - target) * (edge * 0.6 * mask[box])[..., None]
    lights = np.zeros(scene.size, np.float32)
    lights[box] = (lit + blue * 0.6) * mask[box]
    if block.get("doors") and night(scene):
        doors = []
        for k in range(block["doors"]):
            share_along = (k + 0.5) / block["doors"]
            if block["face"] == "front":
                x = block["x0"] + (block["x1"] - block["x0"]) * share_along
                corners = [(x - 70, 0, block["z"]), (x + 70, 0, block["z"]), (x + 70, 220, block["z"]), (x - 70, 220, block["z"])]
                bulb = (x, 250, block["z"] - 30)
            else:
                z = block["z0"] + (block["z1"] - block["z0"]) * share_along
                corners = [(block["x"], 0, z - 70), (block["x"], 0, z + 70), (block["x"], 220, z + 70), (block["x"], 220, z - 70)]
                bulb = (block["x"] - np.sign(block["x"]) * 30, 250, z)
            door = fill(scene.size, camera.project(corners))
            over(scene.image, tone(scene, "block", "door"), door)
            center = camera.project([bulb])[0]
            radius = max(10.0 * camera.focal / max(bulb[2], NEAR), 1.5)
            doors.append(fill(scene.size, ellipse(center, radius, radius, 12)))
        for bulb in doors:
            over(scene.image, tone(scene, "lamp", "head"), bulb)
            lights = np.maximum(lights, bulb)
    amount = veil(scene, float(np.median(depth)))
    if amount > 0:
        over(scene.image, tone(scene, "sky", "haze_night" if night(scene) else "haze_dusk"), mask, amount)
    glow += lights
    kit.ink_edges(scene, mask, 1.2, "block", "line", opacity=0.6)
    note_focus(scene, mask, FOCUS["block"])
    return mask


# ------------------------------------------------------------------ poles, wires, lamps, trees
def catenary(start, end, sag, count=24):
    """Points of a wire hanging between two 3D points, sagging `sag` cm at its middle."""
    t = np.linspace(0.0, 1.0, count)[:, None]
    points = np.asarray(start, np.float64) + (np.asarray(end, np.float64) - np.asarray(start, np.float64)) * t
    points[:, 1] -= sag * 4.0 * (t[:, 0] * (1.0 - t[:, 0]))
    return points


def wire_width(camera, points):
    return np.maximum(1.4 * camera.focal / np.maximum(points[:, 2], NEAR) * 0.6, 0.8)


def paint_poles(scene, camera):
    """Concrete utility poles with a crossarm; wires sag from one to the next and off the picture."""
    poles = scene.fig.spec.get("poles", [])
    if not poles:
        return np.zeros(scene.size, np.float32)
    setup = scene.fig.spec.get("wires", {})
    sag, count = setup.get("sag", 60.0), setup.get("count", 3)
    strokes, wires = [], []
    tips = []
    for pole in poles:
        height = pole.get("height", 900.0)
        x, z = pole["x"], pole["z"]
        scale = camera.focal / max(z, NEAR)
        foot, head = camera.project([(x, 0, z), (x, height, z)])
        strokes.append((np.array([foot, head]), np.array([30.0, 18.0]) * scale))
        arm = camera.project([(x - 110, height - 60, z), (x + 110, height - 60, z)])
        strokes.append((arm, 9.0 * scale))
        tips.append([(x - 100 + k * 200 / max(count - 1, 1), height - 70, z) for k in range(count)])
    for left, right in zip(tips[:-1], tips[1:]):
        for a, b in zip(left, right):
            wires.append(catenary(a, b, sag))
    # Wires leave the first and last pole toward the viewer and out of the picture.
    for end, toward in ((tips[0], -1), (tips[-1], 1)):
        for a in end:
            b = (a[0] + toward * 2500.0, a[1] + 150.0, max(a[2] - 2500.0, NEAR * 3))
            wires.append(catenary(a, b, sag * 1.5))
    mask = stroke_many(scene.size, strokes)
    over(scene.image, tone(scene, "pole", "base"), mask)
    kit.ink_edges(scene, mask, 1.0, "pole", "line", opacity=0.6)
    lines = stroke_many(scene.size, [(camera.project(w), wire_width(camera, w)) for w in wires])
    over(scene.image, tone(scene, "pole", "wire"), lines, 0.9)
    scene.wires = wires
    return np.maximum(mask, lines)


def paint_lamps(scene, camera, glow):
    """Sodium street lamps: a pole, a curved arm, a glowing head."""
    for lamp in scene.fig.spec.get("lamps", []):
        height, side = lamp.get("height", 650.0), lamp.get("arm", 1)
        x, z = lamp["x"], lamp["z"]
        scale = camera.focal / max(z, NEAR)
        pole = camera.project([(x, 0, z), (x, height, z)])
        arm = camera.project([(x, height - 40, z), (x + side * 60, height + 10, z), (x + side * 120, height, z)])
        mask = np.maximum(stroke(scene.size, pole, np.array([16.0, 10.0]) * scale), stroke(scene.size, smooth(arm, samples=6), 7.0 * scale))
        over(scene.image, tone(scene, "pole", "base"), mask)
        head_at = camera.project([(x + side * 120, height - 12, z)])[0]
        head = fill(scene.size, ellipse(head_at, max(26 * scale, 2.0), max(10 * scale, 1.2), 16))
        lit = night(scene)
        over(scene.image, tone(scene, "lamp", "head" if lit else "off"), head)
        if lit:
            glow += head * 1.5
            if scene.shade_on:
                cone = camera.project([(x + side * 120 - 15, height - 20, z), (x + side * 120 + 15, height - 20, z),
                                       (x + side * 120 + 260, 0, z), (x + side * 120 - 260, 0, z)])
                screen(scene.image, tone(scene, "lamp", "pool"), blur(fill(scene.size, cone), 6.0 * scale + 2.0), 0.18)
        note_focus(scene, mask, FOCUS["near"])


def birch_branches(rng, base, direction, length, width, depth, out):
    """Recursive thin branches: each splits into two narrower ones turned a little apart."""
    end = base + direction * length
    out.append((np.array([base, (base + end) / 2 + rng.normal(0, length * 0.05, 2), end]), width * taper(3, 1.0, 0.6, 0.0)))
    if depth == 0:
        return
    for turn in (rng.uniform(-0.6, -0.2), rng.uniform(0.2, 0.6)):
        cos, sin = np.cos(turn), np.sin(turn)
        rotated = np.array([direction[0] * cos - direction[1] * sin, direction[0] * sin + direction[1] * cos])
        birch_branches(rng, end, rotated, length * rng.uniform(0.6, 0.75), width * 0.65, depth - 1, out)


def paint_birches(scene, camera):
    """Bare birches: a pale trunk ringed with dark marks, a crown of thin dark branches."""
    tones = scene.style["palette"]["birch"]
    rng = np.random.default_rng(scene.fig.seed + 21)
    for tree in sorted(scene.fig.spec.get("birches", []), key=lambda tree: -tree["z"]):
        height = tree.get("height", 1300.0)
        x, z = tree["x"], tree["z"]
        scale = camera.focal / max(z, NEAR)
        lean = rng.uniform(-40, 40)
        trunk = camera.project([(x, 0, z), (x + lean * 0.5, height * 0.5, z), (x + lean, height * 0.85, z)])
        trunk = smooth(trunk, samples=8)
        widths = 28.0 * scale * taper(len(trunk), 1.0, 0.35, 0.0)
        body = stroke(scene.size, trunk, widths)
        over(scene.image, rgb(tones["bark"]), body)
        if scene.shade_on:
            marks = []
            for k in range(2, len(trunk) - 1, 2):
                half = widths[k] * rng.uniform(0.2, 0.5)
                marks.append((np.array([trunk[k] - [half, 0], trunk[k] + [half, rng.uniform(-1, 1)]]), max(2.0 * scale * 3, 0.8)))
            over(scene.image, rgb(tones["mark"]), stroke_many(scene.size, marks) * body, 0.85)
            shade = trunk + np.column_stack([widths * 0.25, np.zeros(len(trunk))])
            over(scene.image, rgb(tones["shade"]), stroke(scene.size, shade, widths * 0.45) * body, 0.5)
        branches = []
        for k in range(5):
            start = trunk[int(len(trunk) * rng.uniform(0.45, 0.95))]
            angle = rng.uniform(-1.1, 1.1)
            direction = np.array([np.sin(angle), -np.cos(angle)])
            birch_branches(rng, start, direction, height * 0.22 * scale, 9.0 * scale, 3, branches)
        over(scene.image, rgb(tones["twig"]), stroke_many(scene.size, [(p, np.maximum(w, 0.6)) for p, w in branches]), 0.9)
        kit.ink_edges(scene, body, 1.0, "birch", "line", opacity=0.5)
        note_focus(scene, body, FOCUS["near"])


def paint_swing(scene, camera):
    """A playground swing: two A-frames, the top bar, two chains and a seat."""
    setup = scene.fig.spec.get("swing")
    if not setup:
        return
    x, z = setup["x"], setup["z"]
    scale = camera.focal / max(z, NEAR)
    width, height = 260.0, 230.0
    parts = []
    for end in (-1, 1):
        ex = x + end * width / 2
        parts.append((camera.project([(ex, 0, z - 70), (ex, height, z)]), 7.0 * scale))
        parts.append((camera.project([(ex, 0, z + 70), (ex, height, z)]), 7.0 * scale))
    parts.append((camera.project([(x - width / 2, height, z), (x + width / 2, height, z)]), 8.0 * scale))
    seat_y = 55.0
    for chain in (-25, 25):
        parts.append((camera.project([(x + chain, height, z), (x + chain, seat_y, z)]), 2.0 * scale))
    parts.append((camera.project([(x - 32, seat_y, z), (x + 32, seat_y, z)]), 7.0 * scale))
    mask = stroke_many(scene.size, parts)
    over(scene.image, tone(scene, "pole", "metal"), mask)
    note_focus(scene, mask, FOCUS["near"])


# ------------------------------------------------------------------ outskirts
def pylon_points(x, z, height):
    """Lattice tower (cm): the two legs, the crossarm ends where the wires hang, the bracing between levels."""
    base, waist = 420.0, 110.0
    levels = np.linspace(0.0, height * 0.82, 7)
    half = base + (waist - base) * (levels / (height * 0.82))
    legs = [[(x - h, y, z) for h, y in zip(half, levels)] + [(x, height, z)],
            [(x + h, y, z) for h, y in zip(half, levels)] + [(x, height, z)]]
    braces = []
    for k in range(len(levels) - 1):
        braces.append([(x - half[k], levels[k], z), (x + half[k + 1], levels[k + 1], z)])
        braces.append([(x + half[k], levels[k], z), (x - half[k + 1], levels[k + 1], z)])
    arms, hangs = [], []
    for level, reach in ((height * 0.62, 820.0), (height * 0.82, 620.0)):
        arms.append([(x - reach, level, z), (x + reach, level, z)])
        arms.append([(x - reach, level, z), (x - waist, level + 140.0, z)])
        arms.append([(x + reach, level, z), (x + waist, level + 140.0, z)])
        for end in (-1, 1):
            hangs.append((x + end * reach, level - 160.0, z))
    return legs, braces, arms, hangs


def paint_pylons(scene, camera):
    """Transmission towers in a line to the horizon, wires sagging from tower to tower; crows on the wires."""
    setup = scene.fig.spec.get("pylons")
    if not setup:
        return
    tones = scene.style["palette"]["pole"]
    zs = [setup["z0"] + k * setup["spacing"] for k in range(setup["count"])]
    towers = []
    for k, z in enumerate(zs):
        x = setup["x"] + setup.get("drift", 0.0) * k
        towers.append(pylon_points(x, z, setup.get("height", 3200.0)))
    wires = []
    for (_, _, _, hangs_a), (_, _, _, hangs_b) in zip(towers[:-1], towers[1:]):
        for a, b in zip(hangs_a, hangs_b):
            wires.append(catenary(a, b, setup.get("sag", 450.0), 40))
    # From the nearest tower the wires run back over the viewer's head and out of the picture.
    for a in towers[0][3]:
        wires.append(catenary(a, (a[0] * 1.6, a[1] + 600.0, NEAR * 4), setup.get("sag", 450.0), 40))
    for legs, braces, arms, hangs in reversed(towers):
        z = legs[0][0][2]
        scale = camera.focal / max(z, NEAR)
        lines = [(camera.project(leg), max(14.0 * scale, 0.9)) for leg in legs]
        lines += [(camera.project(brace), max(5.0 * scale, 0.6)) for brace in braces]
        lines += [(camera.project(arm), max(8.0 * scale, 0.7)) for arm in arms]
        lines += [(camera.project([h, (h[0], h[1] + 160.0, h[2])]), max(6.0 * scale, 0.6)) for h in hangs]
        mask = stroke_many(scene.size, lines)
        over(scene.image, mix(rgb(tones["base"]), tone(scene, "sky", "haze_dusk"), veil(scene, z)), mask)
    over(scene.image, rgb(tones["wire"]), stroke_many(scene.size, [(camera.project(w), wire_width(camera, w) * 0.8) for w in wires]), 0.85)
    scene.wires = getattr(scene, "wires", []) + wires


def paint_crows(scene, camera):
    """Crows: dark birds perched along the wires and a few flying low."""
    setup = scene.fig.spec.get("crows")
    if not setup:
        return
    rng = np.random.default_rng(scene.fig.seed + 31)
    width = scene.size[1]
    birds = np.zeros(scene.size, np.float32)
    wires = getattr(scene, "wires", [])
    for _ in range(setup.get("perched", 0) if wires else 0):
        wire = wires[int(rng.integers(len(wires)))]
        point = wire[int(rng.integers(3, len(wire) - 3))]
        size = max(18.0 * camera.focal / max(point[2], NEAR), 2.0)
        at = camera.project([point])[0]
        body = ellipse(at + [0, -size * 0.55], size * 0.45, size * 0.6, 14)
        head = ellipse(at + [size * 0.25 * rng.choice([-1, 1]), -size * 1.15], size * 0.25, size * 0.25, 10)
        tail = np.array([at + [-size * 0.2, -size * 0.2], at + [size * 0.2, -size * 0.2], at + [0, size * 0.45]])
        for shape in (body, head, tail):
            np.maximum(birds, fill(scene.size, shape), out=birds)
    for _ in range(setup.get("flying", 0)):
        at = np.array([rng.uniform(0.1, 0.9) * width, rng.uniform(0.1, 0.4) * camera.center[1] * 2])
        span = width * rng.uniform(0.006, 0.014)
        wing = np.array([at + [-span, -span * 0.3], at + [-span * 0.4, -span * 0.05], at, at + [span * 0.4, -span * 0.05],
                         at + [span, -span * 0.35]])
        np.maximum(birds, stroke(scene.size, wing, max(span * 0.18, 1.2) * taper(5, 0.2, 0.2, 1.0)), out=birds)
    over(scene.image, tone(scene, "pole", "crow"), birds)


# ------------------------------------------------------------------ the picture
def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    camera = make_camera(fig.size, fig.spec)
    glow = np.zeros(fig.size, np.float32)
    paint_sky(scene, camera)
    run_hook(extras, "after_background", scene)
    ground = ground_coords(scene, camera)
    paint_ground(scene, camera, ground)
    # Far walls first: front walls by depth, side walls by their near end.
    blocks = sorted(fig.spec.get("blocks", []), key=lambda b: -(b["z"] if b["face"] == "front" else b["z0"]))
    for block in blocks:
        paint_block(scene, camera, block, glow)
    light_pools(scene, camera, ground)
    paint_pylons(scene, camera)
    paint_swing(scene, camera)
    paint_birches(scene, camera)
    paint_poles(scene, camera)
    paint_lamps(scene, camera, glow)
    paint_crows(scene, camera)
    if scene.shade_on and glow.max() > 0:
        halo = np.clip(blur(glow, fig.size[1] * GLOW) * 2.0, 0.0, 1.0)
        screen(scene.image, tone(scene, "lamp", "glow"), halo, 0.55)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
