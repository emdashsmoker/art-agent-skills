"""Interiors seen from a standing person's eye height: subjects "cafe", "room", "bedroom" and "bathroom".

The room is a box measured in centimetres (X right, Y up, Z away from the viewer) and the camera
looks straight ahead from `camera.eye_height`, so every line that runs into the room meets one
vanishing point on the horizon (`camera.horizon_y`). A figure placed on that horizon
("place": "horizon") has its eyes at the camera's height: it stands in the room.

What fills the room is a list of items, like the desk's objects:
  on the walls   window (with the view outside, panes, sill, optional curtains), frame, menu, shelf, mirror, sconce, towel
  on the floor   counter, table, chair, stool, sofa, bookshelf, rug, plant, floor_lamp, bed, nightstand, table_lamp,
                 bathtub, vanity, shower (a glass screen)
  on the walls   `room.wall_tiles` {"height", "size"} tiles the three walls from the floor up
  overhead       pendant
"time": "day" lights the room from its windows; "night" darkens it, shows the night outside and
lets the lamps glow. "weather" (rain, snow) shows through the windows.
"""
import cv2
import numpy as np

import kit
import relief
from figure import Figure
from painter import Scene, run_hook
from raster import blur, ellipse, fill, fill_many, mask_box, mix, multiply, over, rgb, screen, stroke
from subject_desk import Camera, paint_box, paint_plant, rotate_y
from weather import apply_weather

UNIT_SHARE = 0.19
FOCUS = {"wall": 0.08, "floor": 0.15, "window": 0.3, "item": 0.45}
OCCLUSION = 0.35           # darkening along the room's inner edges
NIGHT = {"tint": "#2E3460", "amount": 0.55}
GLOW_RADIUS = 0.10         # lamp glow radius (share of the picture width)
WASH_RADIUS, WASH_OPACITY = 0.45, 0.28   # at night: the warm light a lamp spreads over the room
SUN_DIRECTION = np.array([0.18, -1.0, -1.15])   # sunlight through a back-wall window: down and toward us
SUN_OPACITY = 0.30


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light), seed=spec["seed"], spec=spec)
    fig.focus = np.full(fig.size, FOCUS["wall"], np.float32)
    return fig


def make_camera(size, spec):
    cam = spec["camera"]
    return Camera(size, {"center_x": cam.get("center_x", 0.5), "center_y": cam["horizon_y"], "focal": cam["focal"],
                         "position": [cam.get("x", 0.0), cam["eye_height"], 0.0], "pitch_deg": 0.0})


def note_focus(scene, mask, level):
    scene.fig.focus = np.where(mask > 0.5, np.maximum(level, scene.fig.focus), scene.fig.focus).astype(np.float32)


def tone(scene, group, name):
    return rgb(scene.style["palette"][group][name])


def night(scene):
    return scene.fig.spec.get("time", "day") == "night"


# ------------------------------------------------------------------ the shell
def room_box(spec):
    room = spec["room"]
    half, top, back, near = room["width"] / 2, room["height"], room["depth"], room["near"]
    return half, top, back, near


def paint_shell(scene, camera):
    """Ceiling, side walls, back wall and floor; soft shadow along the inner edges. Returns the floor mask."""
    spec = scene.fig.spec
    half, top, back, near = room_box(spec)
    wall, floor = scene.style["palette"]["room_wall"], scene.style["palette"]["room_floor"]
    # The wall turned from the lamp is darker than the one facing it.
    lit_side = -1 if scene.fig.light[0] < 0 else 1
    side_shade = {lit_side: 0.15, -lit_side: 0.40}
    faces = [
        ("ceiling", [(-half, top, near), (half, top, near), (half, top, back), (-half, top, back)], rgb(wall["ceiling"])),
        ("left", [(-half, 0, near), (-half, 0, back), (-half, top, back), (-half, top, near)],
         mix(rgb(wall["base"]), rgb(wall["shadow"]), side_shade[-1])),
        ("right", [(half, 0, back), (half, 0, near), (half, top, near), (half, top, back)],
         mix(rgb(wall["base"]), rgb(wall["shadow"]), side_shade[1])),
        ("back", [(-half, 0, back), (half, 0, back), (half, top, back), (-half, top, back)], rgb(wall["base"])),
    ]
    masks = {}
    for name, corners, color in faces:
        masks[name] = fill(scene.size, camera.project(corners))
        over(scene.image, color, masks[name])
    floor_mask = fill(scene.size, camera.project([(-half, 0, near), (half, 0, near), (half, 0, back), (-half, 0, back)]))
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    horizon = camera.project([(0, 0, back)])[0][1]
    near_share = np.clip((rows - horizon) / max(scene.size[0] - horizon, 1.0), 0.0, 1.0)
    ramp = mix(mix(rgb(floor["base"]), rgb(floor["shadow"]), 0.35), rgb(floor["base"]), near_share[..., None])
    over(scene.image, np.broadcast_to(ramp, scene.image.shape), floor_mask)
    paint_floor_pattern(scene, camera, floor_mask)
    # Skirting board along the walls.
    trim = rgb(scene.style["palette"]["room_trim"]["base"])
    for path in ([(-half, 4, near), (-half, 4, back), (half, 4, back), (half, 4, near)],):
        points = camera.project(path)
        over(scene.image, trim, stroke(scene.size, points, max(scene.size[1] * 0.004, 1.5)) * (1 - floor_mask))
    # Ambient occlusion: corners and the joins of walls, floor and ceiling hold a little shadow.
    if scene.shade_on:
        edges = [[(-half, 0, back), (half, 0, back), (half, top, back), (-half, top, back), (-half, 0, back)],
                 [(-half, 0, near), (-half, 0, back)], [(half, 0, near), (half, 0, back)],
                 [(-half, top, near), (-half, top, back)], [(half, top, near), (half, top, back)]]
        dark = np.zeros(scene.size, np.float32)
        for path in edges:
            dark = np.maximum(dark, stroke(scene.size, camera.project(path), scene.size[1] * 0.012))
        multiply(scene.image, rgb(wall["shadow"]), blur(dark, scene.size[1] * 0.012), OCCLUSION)
    if scene.lines_on:
        for path in ([(-half, 0, back), (half, 0, back), (half, top, back), (-half, top, back), (-half, 0, back)],
                     [(-half, 0, near), (-half, 0, back)], [(half, 0, near), (half, 0, back)],
                     [(-half, top, near), (-half, top, back)], [(half, top, near), (half, top, back)]):
            points = camera.project(path)
            scene.ink(points, 1.3, "room_wall", "line", np.ones(len(points)), 0.6)
    for name, mask in list(masks.items()) + [("floor", floor_mask)]:
        kit.register(scene, f"room_{name}", mask)
    note_focus(scene, floor_mask, FOCUS["floor"])
    return floor_mask


def paint_floor_pattern(scene, camera, floor_mask):
    """Wooden planks running into the room, or a checker of tiles."""
    spec = scene.fig.spec
    half, _, back, near = room_box(spec)
    floor = spec["room"].get("floor", "planks")
    tones = scene.style["palette"]["room_floor"]
    rng = np.random.default_rng(scene.fig.seed + 17)
    if floor == "tiles":
        size = spec["room"].get("tile", 60.0)
        squares = []
        for i, x in enumerate(np.arange(-half, half, size)):
            for j, z in enumerate(np.arange(near - (near % size), back, size)):
                if (i + j) % 2 == 0:
                    squares.append(camera.project([(x, 0, max(z, near)), (x + size, 0, max(z, near)), (x + size, 0, min(z + size, back)),
                                                   (x, 0, min(z + size, back))]))
        over(scene.image, rgb(tones["alt"]), fill_many(scene.size, squares) * floor_mask, 0.85)
        return
    if not scene.lines_on and not scene.shade_on:
        return
    plank = spec["room"].get("plank", 18.0)
    joints = []
    for x in np.arange(-half, half + 0.1, plank):
        joints.append((camera.project([(x, 0, near), (x, 0, back)]), 1.0))
        for z in np.arange(near + rng.uniform(0, 120), back, 120.0):
            joints.append((camera.project([(x, 0, z), (min(x + plank, half), 0, z)]), 1.0))
    lines = np.clip(sum(stroke(scene.size, path, width) for path, width in joints), 0.0, 1.0)
    over(scene.image, rgb(tones["line"]), lines * floor_mask, 0.30)


# ------------------------------------------------------------------ walls: windows, pictures, boards, shelves
def wall_rect(spec, wall, a0, a1, y0, y1, inset=0.0):
    """Corners (bottom-left, bottom-right, top-right, top-left) of a rectangle on a wall.

    On the back wall a0..a1 run along X; on a side wall they run along Z (near to far).
    """
    half, _, back, _ = room_box(spec)
    if wall == "back":
        z = back - inset
        return np.array([(a0, y0, z), (a1, y0, z), (a1, y1, z), (a0, y1, z)], np.float64)
    x = (-half + inset) if wall == "left" else (half - inset)
    return np.array([(x, y0, a0), (x, y0, a1), (x, y1, a1), (x, y1, a0)], np.float64)


def outside_view(scene, camera, glass, item):
    """What shows through the glass: sky, the street's buildings or trees, lit windows at night, the weather."""
    tones = scene.style["palette"]["outside"]
    box = np.argwhere(glass > 0.5)
    if len(box) == 0:
        return
    (top, left), (bottom, right) = box.min(axis=0), box.max(axis=0)
    dark = night(scene)
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    ramp = np.clip((rows - top) / max(bottom - top, 1), 0, 1)[..., None]
    sky = mix(rgb(tones["night_top" if dark else "sky_top"]), rgb(tones["night_bottom" if dark else "sky_bottom"]), ramp)
    over(scene.image, np.broadcast_to(sky, scene.image.shape), glass)
    ground_y = camera.project([(0, 0, 3000)])[0][1] + (bottom - top) * 0.04
    rng = np.random.default_rng(scene.fig.seed + 29 + int(left))
    width = right - left
    shapes, lit = [], []
    if item.get("view", "street") == "street":
        x = left - rng.uniform(0, width * 0.1)
        while x < right:
            span = rng.uniform(0.12, 0.30) * width
            rise = rng.uniform(0.35, 0.95) * (ground_y - top + (bottom - top) * 0.3)
            shapes.append(np.array([(x, ground_y), (x + span, ground_y), (x + span, ground_y - rise), (x, ground_y - rise)]))
            for wy in np.arange(ground_y - rise + span * 0.12, ground_y - span * 0.15, span * 0.22):
                for wx in np.arange(x + span * 0.12, x + span - span * 0.15, span * 0.25):
                    if rng.random() < (0.45 if dark else 1.0):
                        lit.append(np.array([(wx, wy), (wx + span * 0.12, wy), (wx + span * 0.12, wy + span * 0.12), (wx, wy + span * 0.12)]))
            x += span + rng.uniform(0.0, 0.04) * width
        far = rgb(tones["far_night" if dark else "far"])
        over(scene.image, far, fill_many(scene.size, shapes) * glass)
        over(scene.image, rgb(tones["lit"] if dark else tones["window"]), fill_many(scene.size, lit) * glass, 0.9 if dark else 0.5)
        road = fill(scene.size, np.array([(left, ground_y), (right, ground_y), (right, bottom + 2), (left, bottom + 2)]))
        over(scene.image, rgb(tones["ground_night" if dark else "ground"]), road * glass)
    else:
        blobs = []
        for _ in range(int(width / max(scene.size[1] * 0.02, 1)) + 6):
            cx = rng.uniform(left, right)
            radius = rng.uniform(0.06, 0.16) * width + scene.size[1] * 0.01
            blobs.append(ellipse((cx, ground_y - radius * rng.uniform(0.3, 1.2)), radius, radius * 0.9, 24))
        over(scene.image, rgb(tones["trees_night" if dark else "trees"]), fill_many(scene.size, blobs) * glass)
        lawn = fill(scene.size, np.array([(left, ground_y), (right, ground_y), (right, bottom + 2), (left, bottom + 2)]))
        over(scene.image, rgb(tones["ground_night" if dark else "lawn"]), lawn * glass)
    weather = scene.fig.spec.get("weather")
    if weather:
        scene.image[:] = apply_weather(scene.image, weather, scene.fig.seed, glass)
    if scene.shade_on:
        # A pale reflection across the glass.
        band = fill(scene.size, np.array([(left + width * 0.15, top), (left + width * 0.45, top), (left + width * 0.10, bottom),
                                          (left - width * 0.20, bottom)]))
        screen(scene.image, rgb("#FFFFFF"), blur(band, width * 0.05) * glass, 0.10)


def paint_window(scene, camera, item, floor_mask):
    """A window: the view outside, panes, frame and sill; daylight on the floor; optional curtains."""
    spec = scene.fig.spec
    wall = item.get("wall", "back")
    corners = wall_rect(spec, wall, item["a0"], item["a1"], item["y0"], item["y1"], inset=0.5)
    outline = camera.project(corners)
    glass = fill(scene.size, outline)
    outside_view(scene, camera, glass, item)
    keep_lit(scene, glass)
    trim = scene.style["palette"]["room_trim"]
    center = corners.mean(axis=0)
    bar = max(item.get("frame", 5.0) * camera.scale(center), 1.5)
    cols, rows = item.get("panes", [2, 2])
    bars = [np.vstack([outline, outline[:1]])]
    for c in range(1, cols):
        share = c / cols
        bars.append(camera.project([corners[0] + (corners[1] - corners[0]) * share, corners[3] + (corners[2] - corners[3]) * share]))
    for r in range(1, rows):
        share = r / rows
        bars.append(camera.project([corners[0] + (corners[3] - corners[0]) * share, corners[1] + (corners[2] - corners[1]) * share]))
    frame = np.clip(sum(stroke(scene.size, path, bar) for path in bars), 0.0, 1.0)
    over(scene.image, rgb(trim["base"]), frame)
    kit.ink_edges(scene, frame, 1.0, "room_trim", "line")
    if wall == "back":
        paint_box(scene, camera, (center[0], item["y0"] - 3, center[2] - 8), (item["a1"] - item["a0"] + 24, 6, 16), "room_trim")
        if not night(scene) and scene.shade_on:
            # Sunlight through the glass falls on the floor toward us.
            direction = SUN_DIRECTION / np.linalg.norm(SUN_DIRECTION)
            patch = [point + direction * (point[1] / -direction[1]) for point in corners]
            pool = scene.soften(fill(scene.size, camera.project(patch)), 0.02)
            screen(scene.image, tone(scene, "outside", "sun"), blur(pool, scene.size[1] * 0.01) * floor_mask, SUN_OPACITY)
    if item.get("curtains"):
        paint_curtains(scene, camera, corners, wall)
    note_focus(scene, np.maximum(glass, frame), FOCUS["window"])
    kit.register(scene, f"window_{int(item['a0'])}", glass)


def paint_curtains(scene, camera, corners, wall):
    """Two drapes hanging in folds either side of the window, from a rod above it."""
    bl, br, tr, tl = corners
    along = (br - bl) / np.linalg.norm(br - bl)
    rod_left, rod_right = tl + [0, 22, 0] - along * 50, tr + [0, 22, 0] + along * 50
    unit = camera.scale((bl + tr) / 2)
    for start, sign in ((rod_left, 1.0), (rod_right, -1.0)):
        folds = []
        for k in range(4):
            top = start + along * sign * (8 + k * 15)
            # The drape fans out a little toward the floor.
            bottom = top + along * sign * 6 * (k - 1.5) / 1.5
            bottom[1] = 2.0
            path = camera.project(np.linspace(top, bottom, 5))
            folds.append(relief.tube(scene.size, path, np.full(5, 9.5 * unit), roundness=0.5, cap_start=False, cap_end=False))
        drape = relief.union(folds, blend=2.0 * unit)
        kit.shade_solid(scene, drape, "curtain", level=0.35, spread=0.5)
        kit.ink_edges(scene, drape.mask, 1.4, "curtain", "line")
        note_focus(scene, drape.mask, FOCUS["item"])
    rod = camera.project([rod_left, rod_right])
    over(scene.image, tone(scene, "lamp", "base"), stroke(scene.size, rod, max(2.5 * unit, 1.5)))


def paint_frame(scene, camera, item, floor_mask):
    """A framed picture on the wall: a mat and a few abstract shapes."""
    spec = scene.fig.spec
    wall = item.get("wall", "back")
    corners = wall_rect(spec, wall, item["a0"], item["a1"], item["y0"], item["y1"], inset=1.0)
    outline = camera.project(corners)
    mask = fill(scene.size, outline)
    art = scene.style["palette"]["art"]
    over(scene.image, rgb(art["frame"]), mask)
    inner = corners.mean(axis=0) + (corners - corners.mean(axis=0)) * 0.86
    paper = fill(scene.size, camera.project(inner))
    over(scene.image, rgb(art["paper"]), paper)
    span = inner[1] - inner[0]
    rise = inner[3] - inner[0]
    circle_center = inner[0] + span * 0.38 + rise * 0.58
    radius = np.linalg.norm(span) * 0.22
    disc = [circle_center + span / np.linalg.norm(span) * radius * np.cos(t) + rise / np.linalg.norm(rise) * radius * np.sin(t)
            for t in np.linspace(0, 2 * np.pi, 36)]
    over(scene.image, rgb(art["a"]), fill(scene.size, camera.project(disc)) * paper)
    band = [inner[0] + span * 0.1 + rise * 0.18, inner[0] + span * 0.9 + rise * 0.30, inner[0] + span * 0.9 + rise * 0.42,
            inner[0] + span * 0.1 + rise * 0.30]
    over(scene.image, rgb(art["b"]), fill(scene.size, camera.project(band)) * paper, 0.9)
    kit.ink_edges(scene, mask, 1.4, "room_trim", "line")
    note_focus(scene, mask, FOCUS["item"])


def paint_menu(scene, camera, item, floor_mask):
    """A chalk menu board: a dark panel with a title and rows of dishes and prices."""
    spec = scene.fig.spec
    corners = wall_rect(spec, item.get("wall", "back"), item["a0"], item["a1"], item["y0"], item["y1"], inset=1.0)
    mask = fill(scene.size, camera.project(corners))
    board = scene.style["palette"]["board"]
    over(scene.image, rgb(board["base"]), mask)
    bl, br, tr, tl = corners
    span, rise = br - bl, tl - bl
    chalk = []
    unit = camera.scale(corners.mean(axis=0))
    chalk.append((camera.project([tl + span * 0.25 - rise * 0.14, tl + span * 0.75 - rise * 0.14]), 2.4 * unit))
    rng = np.random.default_rng(scene.fig.seed + 5)
    for k in range(6):
        v = 0.70 - k * 0.11
        chalk.append((camera.project([bl + span * 0.10 + rise * v, bl + span * rng.uniform(0.45, 0.68) + rise * v]), 1.2 * unit))
        chalk.append((camera.project([bl + span * 0.80 + rise * v, bl + span * 0.90 + rise * v]), 1.2 * unit))
    over(scene.image, rgb(board["chalk"]), np.clip(sum(stroke(scene.size, path, max(width, 1.0)) for path, width in chalk), 0, 1) * mask, 0.8)
    frame = np.clip(stroke(scene.size, np.vstack([camera.project(corners), camera.project(corners[:1])]), max(2.5 * unit, 1.5)), 0, 1)
    over(scene.image, rgb(board["frame"]), frame)
    note_focus(scene, mask, FOCUS["item"])


def small_vessel(scene, camera, base, radius, height, group, color=None):
    """A cup, jar or bottle standing at `base` (cm): a short lathe in its group's colours."""
    top_px = camera.project([base + [0, height, 0]])[0]
    bottom_px = camera.project([base])[0]
    scale = camera.scale(base)
    rim_px = camera.project([base + [0, height, -radius]])[0]
    tilt = float(np.clip((rim_px[1] - top_px[1]) / max(radius * scale, 1e-6), 0.03, 0.6))
    body = relief.lathe(scene.size, top_px[0], top_px[1], bottom_px[1], np.full(5, radius * scale), tilt=tilt)
    if color is not None:
        # A small coloured jar: its own colour, the half turned from the lamp in shadow.
        over(scene.image, rgb(color), body.mask)
        cols = np.arange(scene.size[1], dtype=np.float32)[None, :]
        away = (cols - top_px[0]) * np.sign(scene.fig.light[0] or 1.0) < 0
        multiply(scene.image, tone(scene, group, "shadow"), body.mask * away, 0.45 * scene.shade_on)
    else:
        kit.shade_solid(scene, body, group, level=0.35, spread=0.5, gloss=0.3, shininess=30)
    kit.ink_edges(scene, body.mask, 1.0, group, "line")
    return body.mask


def paint_shelf(scene, camera, item, floor_mask):
    """Wall shelves (boards) holding a row of jars and cups."""
    spec = scene.fig.spec
    _, _, back, _ = room_box(spec)
    jars = scene.style["palette"]["jars"]
    colors = [jars[key] for key in sorted(jars) if key not in ("shadow", "line")]
    rng = np.random.default_rng(scene.fig.seed + 13)
    for level in item.get("levels", [150.0, 190.0]):
        z = back - 13
        paint_box(scene, camera, ((item["a0"] + item["a1"]) / 2, level - 1.5, z), (item["a1"] - item["a0"], 3.0, 24.0), "desk")
        x = item["a0"] + 6
        while x < item["a1"] - 6:
            radius, height = rng.uniform(3.0, 5.5), rng.uniform(8, 20)
            small_vessel(scene, camera, np.array([x + radius, level, z]), radius, height, "jars", colors[int(rng.integers(len(colors)))])
            x += radius * 2 + rng.uniform(2, 6)


# ------------------------------------------------------------------ furniture
def floor_shadow(scene, camera, footprint, floor_mask, opacity=0.35, reach=0.0):
    """A soft shadow on the floor round an object's footprint (cm polygon at y = 0), pushed away from the lamp."""
    if not scene.shade_on:
        return
    lx, _, lz = scene.fig.light
    offset = np.array([-lx, 0.0, lz]) * reach
    hull = camera.project(np.vstack([footprint, footprint + offset]))
    hull = cv2.convexHull(hull.astype(np.float32))[:, 0, :]
    shadow = blur(fill(scene.size, hull), scene.size[1] * 0.006)
    multiply(scene.image, tone(scene, "room_floor", "cast"), shadow * floor_mask, opacity)


def disc_with_rim(scene, camera, center, radius, height, thickness, group, rim_tone="shadow"):
    """A round top seen from beside it: the rim's band below, the top's ellipse, both outlined. Returns their mask."""
    top_ring = camera.project(circle_points(center, radius, height))
    low_ring = camera.project(circle_points(center, radius, height - thickness))
    rim = fill(scene.size, low_ring)
    top = fill(scene.size, top_ring)
    # The band between the two rings: everything under the top's ellipse down to the lower one.
    band = cv2.convexHull(np.vstack([top_ring, low_ring]).astype(np.float32))[:, 0, :]
    side = fill(scene.size, band)
    over(scene.image, tone(scene, group, rim_tone), np.maximum(rim, side))
    over(scene.image, tone(scene, group, "base"), top)
    if scene.lines_on:
        hull = np.vstack([band, band[:1]])
        scene.ink(hull, 1.3, group, "line", np.ones(len(hull)), 0.9)
        scene.ink(np.vstack([top_ring, top_ring[:1]]), 1.0, group, "line", np.ones(len(top_ring) + 1), 0.7)
    return np.maximum(side, top)


def circle_points(center, radius, y, count=48):
    turn = np.linspace(0, 2 * np.pi, count, endpoint=False)
    return np.column_stack([center[0] + radius * np.cos(turn), np.full(count, y), center[1] + radius * np.sin(turn)])


def paint_counter(scene, camera, item, floor_mask):
    """A bar counter: panelled front, a wooden top, an espresso machine and cups on it."""
    x0, x1, z, depth = item["a0"], item["a1"], item["z"], item.get("depth", 60.0)
    height = item.get("height", 105.0)
    middle = ((x0 + x1) / 2, height / 2, z + depth / 2)
    floor_shadow(scene, camera, np.array([(x0, 0, z), (x1, 0, z), (x1, 0, z + depth), (x0, 0, z + depth)]), floor_mask, 0.35, 25)
    faces = paint_box(scene, camera, middle, (x1 - x0, height, depth), "counter")
    front = faces.get("front")
    if front is not None and scene.lines_on:
        for x in np.arange(x0 + 30, x1 - 10, 30):
            scene.ink(camera.project([(x, 6, z - 0.1), (x, height - 8, z - 0.1)]), 1.0, "counter", "line", np.ones(2), 0.5)
    paint_box(scene, camera, ((x0 + x1) / 2, height + 2, z + depth / 2 - 2), (x1 - x0 + 8, 4, depth + 6), "desk")
    if item.get("machine", True):
        paint_espresso(scene, camera, x1 - 48, height + 4, z + depth / 2 + 6)
    for k in range(item.get("cups", 4)):
        small_vessel(scene, camera, np.array([x0 + 25 + k * 16, height + 4, z + 12]), 4.0, 8.0, "mug")
    mask = np.maximum.reduce(list(faces.values()))
    note_focus(scene, mask, FOCUS["item"])
    kit.register(scene, f"counter_{int(x0)}", mask)


def paint_espresso(scene, camera, x, y, z):
    """An espresso machine on the counter: steel body, dark control band, two group heads over a drip tray, cups on top."""
    body = paint_box(scene, camera, (x, y + 24, z), (58, 48, 40), "device")
    front = z - 20.2
    band = [(x - 28, y + 36, front), (x + 28, y + 36, front), (x + 28, y + 46, front), (x - 28, y + 46, front)]
    over(scene.image, tone(scene, "device", "deep"), fill(scene.size, camera.project(band)))
    for k in (-1, 1):
        gauge = camera.project([(x + k * 9, y + 41, front - 0.1)])[0]
        over(scene.image, tone(scene, "device", "base"), fill(scene.size, ellipse(gauge, 2.2 * camera.scale((x, y, z)), 2.2 * camera.scale((x, y, z)), 16)))
    paint_box(scene, camera, (x, y + 2, z - 24), (52, 4, 12), "device")
    for k in (-14, 14):
        head = np.array([x + k, y + 22, z - 26])
        small_vessel(scene, camera, head, 4.0, 8.0, "lamp")
        handle = camera.project([head + [0, 2, 0], head + [k * 0.6, 1, -10]])
        over(scene.image, tone(scene, "lamp", "base"), stroke(scene.size, handle, max(1.6 * camera.scale(head), 1.0)))
        small_vessel(scene, camera, np.array([x + k, y + 4, z - 26]), 3.5, 6.0, "mug")
    for k in range(3):
        small_vessel(scene, camera, np.array([x - 16 + k * 16, y + 48, z + 4]), 4.0, 7.0, "mug")
    return body


def paint_table(scene, camera, item, floor_mask):
    """A round café table on a pedestal, with cups on it."""
    x, z = item["x"], item["z"]
    radius, height = item.get("radius", 35.0), item.get("height", 74.0)
    floor_shadow(scene, camera, circle_points((x, z), radius * 0.9, 0.0), floor_mask, 0.30, 20)
    base = fill(scene.size, camera.project(circle_points((x, z), radius * 0.55, 1.0)))
    over(scene.image, tone(scene, "lamp", "base"), base)
    pole = camera.project([(x, 2, z), (x, height - 3, z)])
    over(scene.image, tone(scene, "lamp", "base"), stroke(scene.size, pole, max(3.0 * camera.scale((x, height / 2, z)), 1.5)))
    top = disc_with_rim(scene, camera, (x, z), radius, height, 3.0, "desk", "deep")
    if scene.shade_on:
        screen(scene.image, rgb("#FFFFFF"), blur(fill(scene.size, camera.project(circle_points((x - radius * 0.3, z - radius * 0.1), radius * 0.35,
                                                                                        height + 0.1))), 3.0) * top, 0.18)
    for k in range(item.get("cups", 1)):
        turn = 2.4 * k + 0.6
        small_vessel(scene, camera, np.array([x + radius * 0.45 * np.cos(turn), height, z + radius * 0.45 * np.sin(turn)]), 4.5, 8.0, "mug")
    mask = np.maximum(base, top)
    note_focus(scene, mask, FOCUS["item"])
    kit.register(scene, f"table_{int(x)}_{int(z)}", mask)


def paint_chair(scene, camera, item, floor_mask):
    """A simple wooden chair: four legs, a seat and a back, turned by `angle` (0 = its back toward the room's back)."""
    x, z, angle = item["x"], item["z"], item.get("angle", 0.0)
    seat_y, half = 45.0, 21.0
    floor_shadow(scene, camera, rotate_y(np.array([(x - half, 0, z - half), (x + half, 0, z - half), (x + half, 0, z + half),
                                                    (x - half, 0, z + half)]), np.array([x, 0, z]), angle), floor_mask, 0.25, 10)
    center = np.array([x, 0.0, z])
    parts = [((-half + 2, seat_y / 2, -half + 2), (3, seat_y, 3)), ((half - 2, seat_y / 2, -half + 2), (3, seat_y, 3)),
             ((-half + 2, seat_y / 2, half - 2), (3, seat_y, 3)), ((half - 2, seat_y / 2, half - 2), (3, seat_y, 3)),
             ((0, seat_y + 2, 0), (2 * half, 4, 2 * half)), ((0, seat_y + 22, half - 1.5), (2 * half, 36, 3))]
    placed = []
    for offset, size in parts:
        local = rotate_y(np.array([[offset[0] + x, offset[1], offset[2] + z]]), center, angle)[0]
        placed.append((camera.depth(local), local, size))
    for _, local, size in sorted(placed, key=lambda part: -part[0]):
        faces = paint_box(scene, camera, tuple(local), size, "chair", angle)
        note_focus(scene, np.maximum.reduce(list(faces.values())), FOCUS["item"])


def paint_stool(scene, camera, item, floor_mask):
    """A bar stool: three thin legs and a round seat."""
    x, z = item["x"], item["z"]
    height, radius = item.get("height", 75.0), item.get("radius", 17.0)
    floor_shadow(scene, camera, circle_points((x, z), radius, 0.0), floor_mask, 0.25, 12)
    legs = []
    for turn in (np.pi / 2, np.pi / 2 + 2.1, np.pi / 2 - 2.1):
        foot = (x + radius * 0.9 * np.cos(turn), 0, z + radius * 0.9 * np.sin(turn))
        legs.append((camera.project([foot, (x, height - 4, z)]), max(1.6 * camera.scale(foot), 1.0)))
    over(scene.image, tone(scene, "lamp", "base"), np.clip(sum(stroke(scene.size, path, width) for path, width in legs), 0, 1))
    seat = disc_with_rim(scene, camera, (x, z), radius, height, 5.0, "chair")
    note_focus(scene, seat, FOCUS["item"])


def paint_sofa(scene, camera, item, floor_mask):
    """A sofa against a wall: base, back, arms and seat cushions."""
    x, z, angle = item["x"], item["z"], item.get("angle", 0.0)
    width, depth = item.get("width", 200.0), item.get("depth", 90.0)
    center = np.array([x, 0.0, z + depth / 2])
    floor_shadow(scene, camera, rotate_y(np.array([(x - width / 2, 0, z), (x + width / 2, 0, z), (x + width / 2, 0, z + depth),
                                                    (x - width / 2, 0, z + depth)]), center, angle), floor_mask, 0.35, 25)
    pieces = [((0, 42, depth - 12), (width, 84, 24)),                                     # back
              ((0, 21, depth / 2), (width - 8, 42, depth - 4)),                           # base
              ((-width / 2 + 11, 31, depth / 2), (22, 62, depth)),                         # arms
              ((width / 2 - 11, 31, depth / 2), (22, 62, depth))]
    cushion_w = (width - 44) / 2
    for k in (-1, 1):
        pieces.append(((k * cushion_w / 2, 47, depth / 2 - 8), (cushion_w - 3, 12, depth - 30)))
    placed = []
    for offset, size in pieces:
        local = rotate_y(np.array([[x + offset[0], offset[1], z + offset[2]]]), center, angle)[0]
        placed.append((camera.depth(local + [0, 0, -size[2] / 2]), local, size))
    masks = []
    for _, local, size in sorted(placed, key=lambda part: -part[0]):
        masks.extend(paint_box(scene, camera, tuple(local), size, "sofa", angle).values())
    mask = np.maximum.reduce(masks)
    note_focus(scene, mask, FOCUS["item"])
    kit.register(scene, f"sofa_{int(x)}", mask)


def paint_bookshelf(scene, camera, item, floor_mask):
    """A bookcase against the wall: its frame, shelves and rows of books."""
    x, z = item["x"], item["z"]
    width, height, depth = item.get("width", 90.0), item.get("height", 190.0), item.get("depth", 32.0)
    floor_shadow(scene, camera, np.array([(x - width / 2, 0, z), (x + width / 2, 0, z), (x + width / 2, 0, z + depth),
                                          (x - width / 2, 0, z + depth)]), floor_mask, 0.35, 25)
    faces = paint_box(scene, camera, (x, height / 2, z + depth / 2), (width, height, depth), "shelf_wood")
    inner = [(x - width / 2 + 3, 3, z + 0.2), (x + width / 2 - 3, 3, z + 0.2), (x + width / 2 - 3, height - 3, z + 0.2),
             (x - width / 2 + 3, height - 3, z + 0.2)]
    over(scene.image, tone(scene, "shelf_wood", "deep"), fill(scene.size, camera.project(inner)))
    books = scene.style["palette"]["books"]
    colors = [books[key] for key in sorted(books) if key != "line"]
    rng = np.random.default_rng(scene.fig.seed + 41)
    shelves = item.get("shelves", 5)
    step = (height - 6) / shelves
    spines = {color: [] for color in colors}
    for s in range(shelves):
        floor_y = 3 + s * step
        board = [(x - width / 2 + 3, floor_y, z + 0.3), (x + width / 2 - 3, floor_y, z + 0.3), (x + width / 2 - 3, floor_y + 2.5, z + 0.3),
                 (x - width / 2 + 3, floor_y + 2.5, z + 0.3)]
        over(scene.image, tone(scene, "shelf_wood", "base"), fill(scene.size, camera.project(board)))
        bx = x - width / 2 + 5
        while bx < x + width / 2 - 8:
            thick, tall = rng.uniform(2.5, 5.0), rng.uniform(0.55, 0.85) * step
            if rng.random() < 0.12:
                bx += thick * 2
                continue
            color = colors[int(rng.integers(len(colors)))]
            spines[color].append(camera.project([(bx, floor_y + 2.5, z + 1), (bx + thick, floor_y + 2.5, z + 1), (bx + thick, floor_y + 2.5 + tall, z + 1),
                                                 (bx, floor_y + 2.5 + tall, z + 1)]))
            bx += thick + 0.4
    for color, polygons in spines.items():
        if polygons:
            over(scene.image, rgb(color), fill_many(scene.size, polygons))
    mask = np.maximum.reduce(list(faces.values()))
    kit.ink_edges(scene, mask, 1.6, "shelf_wood", "line")
    note_focus(scene, mask, FOCUS["item"])
    kit.register(scene, f"bookshelf_{int(x)}", mask)


def paint_rug(scene, camera, item, floor_mask):
    """A rug on the floor: field, border band and a darker centre motif."""
    x, z = item["x"], item["z"]
    width, depth = item.get("width", 200.0), item.get("depth", 140.0)
    tones = scene.style["palette"]["rug"]
    def quad(inset):
        return camera.project([(x - width / 2 + inset, 0.3, z + inset), (x + width / 2 - inset, 0.3, z + inset),
                               (x + width / 2 - inset, 0.3, z + depth - inset), (x - width / 2 + inset, 0.3, z + depth - inset)])
    outer = fill(scene.size, quad(0))
    over(scene.image, rgb(tones["border"]), outer)
    over(scene.image, rgb(tones["base"]), fill(scene.size, quad(12)))
    motif = fill(scene.size, camera.project(circle_points((x, z + depth / 2), min(width, depth) * 0.25, 0.4)))
    over(scene.image, rgb(tones["motif"]), motif, 0.8)
    kit.ink_edges(scene, outer, 1.2, "rug", "line")
    note_focus(scene, outer, FOCUS["floor"])


def paint_floor_lamp(scene, camera, item, floor_mask):
    """A standing lamp: a round foot, a pole and a drum shade; it glows when lit."""
    x, z = item["x"], item["z"]
    height = item.get("height", 160.0)
    floor_shadow(scene, camera, circle_points((x, z), 16.0, 0.0), floor_mask, 0.3, 30)
    foot = fill(scene.size, camera.project(circle_points((x, z), 14.0, 2.0)))
    over(scene.image, tone(scene, "lamp", "base"), foot)
    pole = camera.project([(x, 2, z), (x, height - 25, z)])
    over(scene.image, tone(scene, "lamp", "base"), stroke(scene.size, pole, max(1.8 * camera.scale((x, height / 2, z)), 1.2)))
    top_px, bottom_px = camera.project([(x, height, z)])[0], camera.project([(x, height - 32, z)])[0]
    scale = camera.scale((x, height, z))
    shade = relief.lathe(scene.size, top_px[0], top_px[1], bottom_px[1], np.linspace(15 * scale, 22 * scale, 5), tilt=0.12)
    kit.shade_solid(scene, shade, "shade", level=0.3, spread=0.5)
    kit.ink_edges(scene, shade.mask, 1.4, "shade", "line")
    if item.get("on", night(scene)):
        keep_lit(scene, shade.mask)
        scene.glows.append(((top_px + bottom_px) / 2, tone(scene, "lamp", "bulb")))
    note_focus(scene, shade.mask, FOCUS["item"])


def paint_pendant(scene, camera, item, floor_mask):
    """A pendant lamp hanging on its cord from the ceiling; it glows when lit."""
    spec = scene.fig.spec
    _, top, _, _ = room_box(spec)
    x, z = item["x"], item["z"]
    drop = item.get("drop", 90.0)
    radius = item.get("radius", 18.0)
    hang = top - drop
    cord = camera.project([(x, top, z), (x, hang + 14, z)])
    over(scene.image, tone(scene, "lamp", "base"), stroke(scene.size, cord, 1.2))
    top_px, bottom_px = camera.project([(x, hang + 16, z)])[0], camera.project([(x, hang, z)])[0]
    scale = camera.scale((x, hang, z))
    profile = np.array([0.18, 0.35, 0.62, 0.86, 1.0]) * radius * scale
    shade = relief.lathe(scene.size, top_px[0], top_px[1], bottom_px[1], profile, tilt=0.05)
    kit.shade_solid(scene, shade, "lamp", level=0.35, spread=0.5, gloss=0.4, shininess=30)
    kit.ink_edges(scene, shade.mask, 1.2, "lamp", "line")
    lit = item.get("on", True)
    if lit:
        bulb = fill(scene.size, ellipse(bottom_px, radius * scale * 0.8, radius * scale * 0.18, 24))
        over(scene.image, tone(scene, "lamp", "bulb"), bulb)
        keep_lit(scene, bulb)
        scene.glows.append((bottom_px + [0, radius * scale * 0.4], tone(scene, "lamp", "bulb")))
    note_focus(scene, shade.mask, FOCUS["item"])


def paint_floor_plant(scene, camera, item, floor_mask):
    """A potted plant on the floor (the desk's plant at room scale; it throws its own shadow)."""
    paint_plant(scene, camera, {**item, "radius": item.get("radius", 18.0), "height": item.get("height", 40.0)}, floor_mask)


# ------------------------------------------------------------------ bedroom
BED = {"width": 160.0, "length": 205.0, "frame": 30.0, "mattress": 24.0, "headboard": 115.0, "duvet_share": 0.70, "drop": 30.0}


def paint_parts(scene, camera, parts):
    """Boxes (centre, size, group) painted far to near. Returns their masks."""
    placed = sorted(parts, key=lambda part: -camera.depth(np.array(part[0]) + [0, 0, -part[1][2] / 2]))
    masks = []
    for center, size, group in placed:
        masks.extend(paint_box(scene, camera, tuple(center), size, group).values())
    return masks


def paint_bed(scene, camera, item, floor_mask):
    """A bed against the back wall: frame, upholstered headboard, mattress, two pillows, a duvet turned down
    at the top and hanging over the foot and the sides. `z` is the foot end (cm)."""
    x, z = item["x"], item["z"]
    width, length = item.get("width", BED["width"]), item.get("length", BED["length"])
    frame, mattress = BED["frame"], BED["mattress"]
    top = frame + mattress
    covered = length * item.get("duvet_share", BED["duvet_share"])
    floor_shadow(scene, camera, np.array([(x - width / 2 - 6, 0, z - 6), (x + width / 2 + 6, 0, z - 6), (x + width / 2 + 6, 0, z + length),
                                          (x - width / 2 - 6, 0, z + length)]), floor_mask, 0.40, 25)
    head = [((x, item.get("headboard", BED["headboard"]) / 2, z + length + 4), (width + 16, item.get("headboard", BED["headboard"]), 8), "headboard")]
    base = [((x, frame / 2, z + length / 2), (width + 8, frame, length + 4), "bed_wood"),
            ((x, frame + mattress / 2, z + length / 2), (width, mattress, length), "sheet")]
    pillows = [((x + side * width / 4, top + 9, z + length - 24), (width / 2 - 12, 18, 38), "pillow") for side in (-1, 1)]
    drop = BED["drop"]
    duvet = [((x, top + 4, z + covered / 2), (width + 10, 8, covered), "duvet"),
             ((x, top + 9, z + covered - 7), (width + 10, 2, 14), "sheet"),
             ((x - width / 2 - 5, top + 8 - drop / 2, z + covered / 2), (2, drop, covered), "duvet"),
             ((x + width / 2 + 5, top + 8 - drop / 2, z + covered / 2), (2, drop, covered), "duvet"),
             ((x, top + 8 - drop / 2, z - 1), (width + 12, drop, 2), "duvet")]
    masks = paint_parts(scene, camera, head) + paint_parts(scene, camera, base) + paint_parts(scene, camera, pillows)
    masks += paint_parts(scene, camera, duvet)
    mask = np.maximum.reduce(masks)
    note_focus(scene, mask, FOCUS["item"])
    kit.register(scene, f"bed_{int(x)}", mask)


def paint_nightstand(scene, camera, item, floor_mask):
    """A bedside table: a box with one drawer and a small knob."""
    x, z = item["x"], item["z"]
    width, depth, height = item.get("width", 46.0), item.get("depth", 40.0), item.get("height", 55.0)
    floor_shadow(scene, camera, np.array([(x - width / 2, 0, z), (x + width / 2, 0, z), (x + width / 2, 0, z + depth),
                                          (x - width / 2, 0, z + depth)]), floor_mask, 0.35, 15)
    faces = paint_box(scene, camera, (x, height / 2, z + depth / 2), (width, height, depth), "bed_wood")
    if scene.lines_on:
        seam = camera.project([(x - width / 2 + 3, height * 0.62, z - 0.1), (x + width / 2 - 3, height * 0.62, z - 0.1)])
        scene.ink(seam, 1.0, "bed_wood", "line", np.ones(2), 0.6)
    knob = camera.project([(x, height * 0.80, z - 0.2)])[0]
    radius = 1.6 * camera.scale((x, height, z))
    over(scene.image, tone(scene, "lamp", "base"), fill(scene.size, ellipse(knob, radius, radius, 12)))
    mask = np.maximum.reduce(list(faces.values()))
    note_focus(scene, mask, FOCUS["item"])


def paint_table_lamp(scene, camera, item, floor_mask):
    """A bedside lamp standing at height `y`: a round base and a drum shade; it glows when lit."""
    x, z, y = item["x"], item["z"], item.get("y", 55.0)
    small_vessel(scene, camera, np.array([x, y, z]), 5.5, 16.0, "shade")
    top_px, bottom_px = camera.project([(x, y + 40, z)])[0], camera.project([(x, y + 16, z)])[0]
    scale = camera.scale((x, y + 30, z))
    shade = relief.lathe(scene.size, top_px[0], top_px[1], bottom_px[1], np.linspace(10 * scale, 15 * scale, 5), tilt=0.12)
    kit.shade_solid(scene, shade, "shade", level=0.3, spread=0.5)
    kit.ink_edges(scene, shade.mask, 1.2, "shade", "line")
    if item.get("on", night(scene)):
        keep_lit(scene, shade.mask)
        scene.glows.append(((top_px + bottom_px) / 2, tone(scene, "lamp", "bulb")))
    note_focus(scene, shade.mask, FOCUS["item"])


# ------------------------------------------------------------------ bathroom
def paint_wall_tiles(scene, camera):
    """Tiles on the three walls up to `room.wall_tiles.height` (cm): the tile colour, then its joints."""
    spec = scene.fig.spec
    setup = spec["room"].get("wall_tiles")
    if not setup:
        return
    half, _, back, near = room_box(spec)
    tile_height, size = setup.get("height", 130.0), setup.get("size", 30.0)
    tones = scene.style["palette"]["room_tile"]
    lit_side = -1 if scene.fig.light[0] < 0 else 1
    side_shade = {lit_side: 0.15, -lit_side: 0.40}
    walls = {"back": [(-half, 0, back), (half, 0, back), (half, tile_height, back), (-half, tile_height, back)],
             "left": [(-half, 0, near), (-half, 0, back), (-half, tile_height, back), (-half, tile_height, near)],
             "right": [(half, 0, back), (half, 0, near), (half, tile_height, near), (half, tile_height, back)]}
    shades = {"back": 0.0, "left": side_shade[-1], "right": side_shade[1]}
    joints = []
    for name, corners in walls.items():
        over(scene.image, mix(rgb(tones["base"]), rgb(tones["shadow"]), shades[name]), fill(scene.size, camera.project(corners)))
        for level in np.arange(size, tile_height + 0.1, size):
            a, b = np.array(corners[0], np.float64), np.array(corners[1], np.float64)
            joints.append(camera.project([a + [0, level, 0], b + [0, level, 0]]))
        if name == "back":
            for x in np.arange(-half + size, half, size):
                joints.append(camera.project([(x, 0, back), (x, tile_height, back)]))
        else:
            x = -half if name == "left" else half
            for depth in np.arange(near + size - near % size, back, size):
                joints.append(camera.project([(x, 0, depth), (x, tile_height, depth)]))
    lines = np.clip(sum(stroke(scene.size, path, 1.0) for path in joints), 0.0, 1.0)
    over(scene.image, rgb(tones["line"]), lines, 0.45)
    # The cap along the top of the tiling.
    cap = camera.project([walls["left"][3], walls["left"][2], walls["right"][3], walls["right"][2]])
    over(scene.image, rgb(tones["light"]), stroke(scene.size, cap, max(scene.size[1] * 0.003, 1.2)), 0.8)


def paint_bathtub(scene, camera, item, floor_mask):
    """A built-in bathtub against the back wall: white sides, the basin's hollow inside the rim, a tap."""
    x, z = item["x"], item["z"]
    width, depth, height = item.get("width", 170.0), item.get("depth", 75.0), item.get("height", 55.0)
    floor_shadow(scene, camera, np.array([(x - width / 2, 0, z), (x + width / 2, 0, z), (x + width / 2, 0, z + depth),
                                          (x - width / 2, 0, z + depth)]), floor_mask, 0.30, 15)
    faces = paint_box(scene, camera, (x, height / 2, z + depth / 2), (width, height, depth), "porcelain")
    rim = 8.0
    basin = camera.project([(x - width / 2 + rim, height + 0.1, z + rim), (x + width / 2 - rim, height + 0.1, z + rim),
                            (x + width / 2 - rim, height + 0.1, z + depth - rim), (x - width / 2 + rim, height + 0.1, z + depth - rim)])
    hollow = fill(scene.size, smooth_quad(basin))
    over(scene.image, tone(scene, "porcelain", "deep"), hollow)
    if scene.shade_on:
        rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
        far_edge, near_edge = basin[2:, 1].min(), basin[:2, 1].max()
        fall = np.clip((rows - far_edge) / max(near_edge - far_edge, 1.0), 0, 1) * np.ones((1, scene.size[1]), np.float32)
        over(scene.image, tone(scene, "porcelain", "base"), hollow * fall, 0.6)
    kit.ink_edges(scene, hollow, 1.0, "porcelain", "line")
    tap = camera.project([(x - width / 4, height + 22, z + depth - 0.5), (x - width / 4, height + 22, z + depth - 12),
                          (x - width / 4, height + 14, z + depth - 14)])
    over(scene.image, tone(scene, "metal", "base"), stroke(scene.size, tap, max(2.2 * camera.scale((x, height, z + depth)), 1.2)))
    mask = np.maximum.reduce(list(faces.values()))
    note_focus(scene, mask, FOCUS["item"])
    kit.register(scene, f"bathtub_{int(x)}", mask)


def smooth_quad(points, corner=0.18):
    """A quad with rounded corners (cut each corner and smooth): a basin's or a mirror's soft outline."""
    out = []
    count = len(points)
    for k in range(count):
        here, after = np.asarray(points[k], np.float64), np.asarray(points[(k + 1) % count], np.float64)
        out.extend([here + (after - here) * corner, here + (after - here) * (1 - corner)])
    return np.array(out)


def paint_vanity(scene, camera, item, floor_mask):
    """A washstand against the back wall: a cabinet with two doors, a stone top, a basin and a tap."""
    x, z = item["x"], item["z"]
    width, depth, height = item.get("width", 90.0), item.get("depth", 48.0), item.get("height", 82.0)
    floor_shadow(scene, camera, np.array([(x - width / 2, 0, z), (x + width / 2, 0, z), (x + width / 2, 0, z + depth),
                                          (x - width / 2, 0, z + depth)]), floor_mask, 0.30, 15)
    faces = paint_box(scene, camera, (x, height / 2, z + depth / 2), (width, height, depth), "vanity")
    if scene.lines_on:
        door = camera.project([(x, 6, z - 0.1), (x, height - 6, z - 0.1)])
        scene.ink(door, 1.0, "vanity", "line", np.ones(2), 0.6)
    top = paint_box(scene, camera, (x, height + 2, z + depth / 2 - 1), (width + 4, 4, depth + 2), "porcelain")
    basin = camera.project(circle_points((x, z + depth * 0.45), width * 0.26, height + 4.1))
    sink = fill(scene.size, basin)
    over(scene.image, tone(scene, "porcelain", "deep"), sink)
    kit.ink_edges(scene, sink, 1.0, "porcelain", "line")
    tap = camera.project([(x, height + 4, z + depth - 6), (x, height + 22, z + depth - 6), (x, height + 22, z + depth * 0.62)])
    over(scene.image, tone(scene, "metal", "base"), stroke(scene.size, tap, max(2.0 * camera.scale((x, height, z + depth)), 1.2)))
    mask = np.maximum.reduce(list(faces.values()) + list(top.values()))
    note_focus(scene, mask, FOCUS["item"])
    kit.register(scene, f"vanity_{int(x)}", mask)


def paint_mirror(scene, camera, item, floor_mask):
    """A mirror on the wall: a thin frame round pale glass with two slanted gleams."""
    spec = scene.fig.spec
    corners = wall_rect(spec, item.get("wall", "back"), item["a0"], item["a1"], item["y0"], item["y1"], inset=1.0)
    outline = camera.project(corners)
    frame = fill(scene.size, smooth_quad(outline, 0.08))
    over(scene.image, tone(scene, "metal", "base"), frame)
    inner = corners.mean(axis=0) + (corners - corners.mean(axis=0)) * 0.94
    glass = fill(scene.size, smooth_quad(camera.project(inner), 0.08))
    tones = scene.style["palette"]["mirror"]
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    top, bottom = outline[:, 1].min(), outline[:, 1].max()
    fall = np.clip((rows - top) / max(bottom - top, 1.0), 0, 1) * np.ones((1, scene.size[1]), np.float32)
    over(scene.image, mix(rgb(tones["top"]), rgb(tones["bottom"]), fall[..., None]), glass)
    if scene.shade_on:
        bl, br, tr, tl = inner
        for start, end, width in ((0.20, 0.42, 5.0), (0.52, 0.60, 2.5)):
            gleam = [bl + (br - bl) * start, bl + (br - bl) * end, tl + (tr - tl) * (end - 0.25), tl + (tr - tl) * (start - 0.25)]
            screen(scene.image, rgb(tones["gleam"]), blur(fill(scene.size, camera.project(gleam)), width) * glass, 0.35)
    kit.ink_edges(scene, frame, 1.2, "metal", "line")
    note_focus(scene, frame, FOCUS["item"])


def paint_sconce(scene, camera, item, floor_mask):
    """A small wall light: a frosted capsule on the wall; it glows when lit."""
    spec = scene.fig.spec
    a, y = item["a"], item["y"]
    corners = wall_rect(spec, item.get("wall", "back"), a - 14, a + 14, y - 5, y + 5, inset=2.0)
    outline = smooth_quad(camera.project(corners), 0.3)
    lamp = fill(scene.size, outline)
    over(scene.image, tone(scene, "shade", "base"), lamp)
    kit.ink_edges(scene, lamp, 1.0, "shade", "line")
    if item.get("on", True):
        keep_lit(scene, lamp)
        scene.glows.append((outline.mean(axis=0), tone(scene, "lamp", "bulb")))
    note_focus(scene, lamp, FOCUS["item"])


def paint_shower(scene, camera, item, floor_mask):
    """A shower corner: the head on the back wall and a clear glass screen in front, with its metal edges."""
    spec = scene.fig.spec
    _, _, back, _ = room_box(spec)
    x0, x1, z = item["a0"], item["a1"], item["z"]
    height = item.get("height", 200.0)
    head = np.array([(x0 + x1) / 2, 195.0, back - 1])
    arm = camera.project([head + [0, 10, 0], head + [0, 10, -18], head + [0, 4, -20]])
    unit = camera.scale(head)
    over(scene.image, tone(scene, "metal", "base"), stroke(scene.size, arm, max(2.0 * unit, 1.2)))
    rose = camera.project(circle_points((head[0], back - 21), 8.0, head[1] + 2))
    over(scene.image, tone(scene, "metal", "shadow"), fill(scene.size, rose))
    corners = np.array([(x0, 0, z), (x1, 0, z), (x1, height, z), (x0, height, z)], np.float64)
    panel = fill(scene.size, camera.project(corners))
    tones = scene.style["palette"]["glass"]
    over(scene.image, rgb(tones["base"]), panel, tones.get("opacity", 0.18))
    if scene.shade_on:
        for start, end in ((0.12, 0.20), (0.26, 0.29)):
            streak = [corners[0] + (corners[1] - corners[0]) * start, corners[0] + (corners[1] - corners[0]) * end,
                      corners[3] + (corners[2] - corners[3]) * (end + 0.25), corners[3] + (corners[2] - corners[3]) * (start + 0.25)]
            screen(scene.image, rgb(tones["gleam"]), blur(fill(scene.size, camera.project(streak)), 3.0) * panel, 0.30)
    edges = [corners[[0, 3]], corners[[3, 2]], corners[[1, 2]]]
    over(scene.image, tone(scene, "metal", "base"), np.clip(sum(stroke(scene.size, camera.project(edge), max(1.6 * camera.scale(edge.mean(axis=0)), 1.0))
                                                               for edge in edges), 0, 1))
    note_focus(scene, panel, FOCUS["item"])


def paint_towel(scene, camera, item, floor_mask):
    """A towel folded over a wall rail: the rail, the cloth hanging from it with a hem stripe."""
    spec = scene.fig.spec
    wall = item.get("wall", "back")
    corners = wall_rect(spec, wall, item["a0"], item["a1"], item["y0"], item["y1"], inset=3.0)
    bl, br, tr, tl = corners
    rail = camera.project([tl + (tl - tr) * 0.12, tr + (tr - tl) * 0.12])
    unit = camera.scale(corners.mean(axis=0))
    over(scene.image, tone(scene, "metal", "base"), stroke(scene.size, rail, max(2.0 * unit, 1.2)))
    cloth = relief.Part(fill(scene.size, smooth_quad(camera.project(corners), 0.06)), None)
    cloth.height = (blur(cloth.mask, 6.0 * unit) * 6.0 * unit).astype(np.float32)
    kit.shade_solid(scene, cloth, "towel", level=0.35, spread=0.5)
    stripe = fill(scene.size, camera.project([bl + (tl - bl) * 0.12, br + (tr - br) * 0.12, br + (tr - br) * 0.18, bl + (tl - bl) * 0.18]))
    over(scene.image, tone(scene, "towel", "stripe"), stripe * cloth.mask, 0.9)
    kit.ink_edges(scene, cloth.mask, 1.2, "towel", "line")
    note_focus(scene, cloth.mask, FOCUS["item"])


WALL_ITEMS = {"window": paint_window, "frame": paint_frame, "menu": paint_menu, "shelf": paint_shelf,
              "mirror": paint_mirror, "sconce": paint_sconce, "towel": paint_towel}
FLOOR_ITEMS = {"counter": paint_counter, "table": paint_table, "chair": paint_chair, "stool": paint_stool, "sofa": paint_sofa,
               "bookshelf": paint_bookshelf, "rug": paint_rug, "floor_lamp": paint_floor_lamp, "pendant": paint_pendant,
               "plant": paint_floor_plant, "bed": paint_bed, "nightstand": paint_nightstand, "table_lamp": paint_table_lamp,
               "bathtub": paint_bathtub, "vanity": paint_vanity, "shower": paint_shower}



def item_depth(item):
    """Distance used to paint far items first; rugs lie under everything."""
    if item["kind"] == "rug":
        return 1e9
    z = item.get("z", 0.0) + item.get("depth", 0.0) * 0.5
    return z


# ------------------------------------------------------------------ light
def keep_lit(scene, mask):
    """Remember a light source (a window's view, a lamp) as painted now: night must not dim what still shows of it."""
    box = mask_box(mask)
    if box is not None:
        scene.lit.append((box, mask[box].copy(), scene.image[box].copy()))


def lit_mask(scene):
    """Where a remembered light source is still visible: its pixels were not painted over since."""
    keep = np.zeros(scene.size, np.float32)
    for box, mask, painted in scene.lit:
        unchanged = np.abs(scene.image[box] - painted).max(axis=-1) < 1e-5
        keep[box] = np.maximum(keep[box], mask * unchanged)
    return keep


def light_up(scene):
    """Night darkens the room except its windows and lamps; every lit lamp glows."""
    if night(scene):
        keep = lit_mask(scene)
        dim = mix(np.ones(3, np.float32), rgb(NIGHT["tint"]), NIGHT["amount"])
        dark = scene.image * dim
        scene.image[:] = scene.image + (dark - scene.image) * (1.0 - keep)[..., None]
    if not scene.shade_on:
        return
    width = scene.size[1]
    for center, color in scene.glows:
        # A bright halo round the lamp; at night also a broad warm wash over the room around it.
        for radius, opacity in ((GLOW_RADIUS, 0.55 if night(scene) else 0.25), (WASH_RADIUS, WASH_OPACITY if night(scene) else 0.0)):
            if opacity <= 0:
                continue
            glow = np.zeros(scene.size, np.float32)
            cv2.circle(glow, (int(center[0]), int(center[1])), int(width * radius * 0.35), 1.0, -1, cv2.LINE_AA)
            glow = blur(glow, width * radius * 0.5)
            glow = glow / max(float(glow.max()), 1e-6)
            screen(scene.image, color, glow, opacity)


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    scene.glows, scene.lit = [], []
    camera = make_camera(fig.size, fig.spec)
    floor_mask = paint_shell(scene, camera)
    paint_wall_tiles(scene, camera)
    run_hook(extras, "after_background", scene)
    items = fig.spec.get("items", [])
    for item in items:
        if item["kind"] in WALL_ITEMS:
            WALL_ITEMS[item["kind"]](scene, camera, item, floor_mask)
    floor_items = [item for item in items if item["kind"] in FLOOR_ITEMS]
    for item in sorted(floor_items, key=lambda item: -item_depth(item)):
        FLOOR_ITEMS[item["kind"]](scene, camera, item, floor_mask)
    unknown = [item["kind"] for item in items if item["kind"] not in WALL_ITEMS and item["kind"] not in FLOOR_ITEMS]
    if unknown:
        raise ValueError(f"unknown interior items {unknown}: use {sorted(WALL_ITEMS) + sorted(FLOOR_ITEMS)}")
    light_up(scene)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
