"""Still life: solids of revolution and fruit on a table, described as a list of objects.

Positions and sizes in the spec are fractions of the canvas width, so the same
arrangement renders at any resolution. Objects are painted back to front by
the height of their base on the table.
"""
import cv2
import numpy as np

import kit
import relief
from figure import Figure
from painter import Scene, run_hook
from raster import blur, ellipse, fill, mix, multiply, noise, over, rgb, screen, smooth, stroke, taper

# Radius along the height of each named lathe shape, as a share of the widest radius.
PROFILES = {
    "bottle": [0.34, 0.30, 0.28, 0.28, 0.28, 0.29, 0.33, 0.47, 0.74, 0.93, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.99, 0.95],
    "vase": [0.52, 0.44, 0.40, 0.46, 0.64, 0.86, 0.98, 1.0, 0.94, 0.82, 0.66, 0.52, 0.44, 0.46],
    "jar": [0.62, 0.58, 0.66, 0.86, 0.97, 1.0, 1.0, 1.0, 0.99, 0.96, 0.90],
    "cup": [1.0, 0.99, 0.97, 0.95, 0.92, 0.88, 0.82, 0.72],
}
# Height-to-width ratio of horizontal circles as seen by the viewer looking slightly down.
VIEW_TILT = 0.26
FOCUS_OBJECT, FOCUS_TABLE = 0.7, 0.25
# Layout unit used for blur radii and ink scaling: one fifth of the canvas width.
UNIT_SHARE = 0.19
# Wood grain: height of one streak in px, and how many tone changes run along the table.
GRAIN_ROW_PX, GRAIN_COLUMNS = 3, 9
# Bowl wall follows a circle arc; 0.92 leaves a base about 0.4 of the rim radius wide.
BOWL_CURVE = 0.92


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light),
                 seed=spec["seed"], spec=spec)
    fig.focus = np.zeros(fig.size, np.float32)
    return fig


def note_focus(scene, mask, level):
    """Raise the brushwork detail budget where an object sits."""
    scene.fig.focus = np.maximum(scene.fig.focus, np.where(mask > 0.5, level, 0.0).astype(np.float32))


# ------------------------------------------------------------------ setting
def paint_wall(scene):
    """Back wall: a dark gradient with a pool of light on the lamp side."""
    wall = scene.style["palette"]["wall"]
    scene.image[:] = kit.vertical_gradient(scene.size, [(0.0, wall["top"]), (1.0, wall["bottom"])])
    height, width = scene.size
    pool_x = width * (0.25 if scene.fig.light[0] < 0 else 0.75)
    pool = blur(fill(scene.size, ellipse((pool_x, height * 0.30), width * 0.30, height * 0.36, 64)), width * 0.10)
    screen(scene.image, rgb(wall["glow"]), pool, 0.55 if scene.shade_on else 0.0)
    cloud = noise(scene.size, width * 0.22, scene.fig.seed + 11, 3)
    scene.image *= (1.0 + 0.22 * (cloud - 0.5) * scene.shade_on)[..., None]


def paint_table(scene):
    """Table top seen from above, its front face below, wood grain along its length."""
    spec, tones = scene.fig.spec["table"], scene.style["palette"]["table"]
    height, width = scene.size
    back_y, front_y = spec["back_y"] * width, spec["front_y"] * width
    rows = np.arange(height, dtype=np.float32)[:, None] * np.ones((1, width), np.float32)
    top = np.clip(rows - back_y + 0.5, 0, 1) * np.clip(front_y - rows + 0.5, 0, 1)
    front = np.clip(rows - front_y + 0.5, 0, 1)
    depth = np.clip((rows - back_y) / max(front_y - back_y, 1), 0, 1)[..., None]
    over(scene.image, mix(rgb(tones["shadow"]), rgb(tones["base"]), depth * 0.8 + 0.2), top)
    over(scene.image, rgb(tones["deep"]), front)
    if scene.shade_on:
        rng = np.random.default_rng(scene.fig.seed + 3)
        # Why a stretched grid: wood grain is noise that is fine across the board and long along it.
        coarse = rng.random((height // GRAIN_ROW_PX, GRAIN_COLUMNS)).astype(np.float32)
        streaks = cv2.resize(coarse, (width, height), interpolation=cv2.INTER_CUBIC)
        streaks = (streaks - streaks.min()) / np.ptp(streaks)
        multiply(scene.image, rgb(tones["deep"]), np.clip(streaks * 2 - 0.9, 0, 1) * top, 0.28)
        seam = np.clip(1 - np.abs(rows - back_y) / (width * 0.012), 0, 1) * top
        multiply(scene.image, rgb(tones["deep"]), seam, 0.45)
        edge = np.clip(1 - np.abs(rows - front_y) / (width * 0.004), 0, 1)
        screen(scene.image, rgb(tones["light"]), edge, 0.5)
    note_focus(scene, np.maximum(top, front), FOCUS_TABLE)
    return top, front


def paint_cloth(scene, top, front):
    """Linen laid on the table and hanging over its front edge in folds."""
    spec = scene.fig.spec.get("cloth")
    if not spec:
        return
    height, width = scene.size
    table = scene.fig.spec["table"]
    back_y, front_y = table["back_y"] * width + width * 0.03, table["front_y"] * width
    left, right, drop = spec["left"] * width, spec["right"] * width, spec["drop"] * width
    xs = np.linspace(left, right, 24)
    hem = front_y + drop * (0.75 + 0.25 * np.sin(np.linspace(0, spec["folds"] * 2 * np.pi, 24) + 0.6))
    outline = np.vstack([[left + width * 0.05, back_y], [right - width * 0.02, back_y + width * 0.012],
                         [right, front_y], np.column_stack([xs[::-1], hem[::-1]]), [left, front_y]])
    mask = fill(scene.size, smooth(outline, samples=4, closed=True))
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    hang = np.clip((rows - front_y) / max(drop, 1), 0, 1)
    period = (right - left) / spec["folds"]
    ridges = np.sin(2 * np.pi * (cols - left) / period + 0.6 + 0.8 * hang) * hang
    creases = np.sin(2 * np.pi * (cols * 0.8 + rows * 0.6) / (period * 1.7)) * (1 - hang)
    surface = ridges * period * 0.22 + creases * period * 0.035
    part = relief.Part(mask, surface.astype(np.float32))
    kit.shade_solid(scene, part, "cloth", level=0.50, spread=0.45)
    kit.ink_edges(scene, mask, 2.2, "cloth", "line")
    note_focus(scene, mask, FOCUS_TABLE + 0.15)
    kit.register(scene, "cloth", mask)


# ------------------------------------------------------------------ objects
def cast_on_table(scene, x, base_y, radius, receiver):
    """Shadow of a standing object, thrown away from the lamp along the table."""
    toward = -np.sign(scene.fig.light[0])
    center = (x + toward * radius * 0.85, base_y + radius * VIEW_TILT * 0.25)
    kit.ground_shadow(scene, center, radius * 1.55, radius * VIEW_TILT * 1.25,
                      scene.style["palette"]["table"]["cast"], 0.62, 0.035, receiver)
    contact = (x + toward * radius * 0.12, base_y + radius * VIEW_TILT * 0.15)
    kit.ground_shadow(scene, contact, radius * 0.95, radius * VIEW_TILT * 0.8,
                      scene.style["palette"]["table"]["cast"], 0.55, 0.012, receiver)


def paint_lathe(scene, item, receiver):
    """Bottle, vase, jar or cup: a named profile turned around a vertical axis."""
    width = scene.size[1]
    x, base_y = item["x"] * width, item["base_y"] * width
    radius, tall = item["radius"] * width, item["height"] * width
    profile = np.array(PROFILES[item["kind"]]) * radius
    cast_on_table(scene, x, base_y, radius, receiver)
    part = relief.lathe(scene.size, x, base_y - tall, base_y, profile, tilt=VIEW_TILT)
    gloss = item.get("gloss", 0.0)
    mask = kit.shade_solid(scene, part, item["group"], level=0.34, spread=0.6, gloss=gloss, shininess=item.get("shininess", 60))
    tones = scene.style["palette"][item["group"]]
    mouth = ellipse((x, base_y - tall), profile[0], profile[0] * VIEW_TILT, 40)
    over(scene.image, rgb(tones["shadow"]), fill(scene.size, mouth))
    over(scene.image, rgb(tones.get("deep", tones["shadow"])), fill(scene.size, ellipse((x, base_y - tall), profile[0] * 0.72, profile[0] * VIEW_TILT * 0.72, 40)))
    if gloss > 0 and scene.shade_on:
        toward = np.sign(scene.fig.light[0])
        streak = [(x + toward * radius * 0.52, base_y - tall * 0.52), (x + toward * radius * 0.56, base_y - tall * 0.30),
                  (x + toward * radius * 0.52, base_y - tall * 0.10)]
        glint = stroke(scene.size, smooth(streak), radius * 0.13 * taper(29, 0.0, 0.0, 0.4))
        screen(scene.image, rgb(tones["light"]), scene.soften(glint, 0.006) * mask, gloss)
        echo = stroke(scene.size, smooth(streak) - [toward * radius * 1.0, 0], radius * 0.05 * taper(29, 0.0, 0.0, 0.5))
        screen(scene.image, rgb(tones["light"]), scene.soften(echo, 0.006) * mask, gloss * 0.35)
    if "label" in item:
        paint_label(scene, item, part, x, base_y, radius, tall)
    kit.ink_edges(scene, mask, 2.4, item["group"], "line")
    note_focus(scene, mask, FOCUS_OBJECT)
    kit.register(scene, f"{item['kind']}_{int(x)}", mask)


def paint_label(scene, item, part, x, base_y, radius, tall):
    """Paper label wrapped round a bottle: it takes the bottle's own shading."""
    label = item["label"]
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    top, bottom = base_y - tall * label["top"], base_y - tall * label["bottom"]
    cols = np.arange(scene.size[1], dtype=np.float32)[None, :]
    sag = radius * VIEW_TILT * np.sqrt(np.clip(1 - ((cols - x) / radius) ** 2, 0, None))
    band = np.clip(rows - (top + sag) + 0.5, 0, 1) * np.clip((bottom + sag) - rows + 0.5, 0, 1) * part.mask
    paper = relief.Part(band, part.height)
    kit.shade_solid(scene, paper, "label", level=0.36, spread=0.7)
    stripe = np.clip(rows - (top + sag + (bottom - top) * 0.62) + 0.5, 0, 1) * np.clip((top + sag + (bottom - top) * 0.74) - rows + 0.5, 0, 1)
    over(scene.image, rgb(scene.style["palette"]["label"]["accent"]), stripe * band, 0.85)


def paint_ball(scene, item, receiver, clip=None):
    """Round fruit: orange, apple, plum, lemon (an ellipsoid with an optional stem)."""
    width = scene.size[1]
    x, base_y = item["x"] * width, item["base_y"] * width
    rx, ry = item["rx"] * width, item["ry"] * width
    center = (x, base_y - ry)
    if receiver is not None:
        cast_on_table(scene, x, base_y - ry * 0.12, rx, receiver)
    part = relief.ellipsoid(scene.size, center, rx, ry, angle_deg=item.get("angle", 0.0))
    if item.get("tips"):
        turn = np.deg2rad(item.get("angle", 0.0))
        for end in (-1, 1):
            tip_center = np.array(center) + end * rx * 0.93 * np.array([np.cos(turn), np.sin(turn)])
            part = relief.union([part, relief.ellipsoid(scene.size, tip_center, rx * 0.16, ry * 0.22, angle_deg=item.get("angle", 0.0))])
    mask = kit.shade_solid(scene, part, item["group"], level=0.30, spread=0.7, gloss=item.get("gloss", 0.25),
                           shininess=item.get("shininess", 18), clip=clip)
    tones = scene.style["palette"][item["group"]]
    if scene.shade_on:
        toward = np.sign(scene.fig.light[0])
        bounce = relief.ellipsoid(scene.size, (x - toward * rx * 0.45, base_y - ry * 0.45), rx * 0.5, ry * 0.4).mask
        screen(scene.image, rgb(tones["base"]), scene.soften(bounce, 0.02) * mask, 0.22)
    if item.get("stem"):
        top = np.array([x - rx * 0.05, base_y - 2 * ry + ry * 0.12])
        dimple = fill(scene.size, ellipse(top + [0, ry * 0.05], rx * 0.22, ry * 0.09, 24))
        multiply(scene.image, rgb(tones["shadow"]), scene.soften(dimple, 0.008) * mask, 0.7)
        stem = smooth([top, top + [rx * 0.10, -ry * 0.30], top + [rx * 0.26, -ry * 0.52]])
        stem_mask = stroke(scene.size, stem, max(rx * 0.07, 2.0) * taper(len(stem), 0.9, 0.6))
        over(scene.image, rgb(scene.style["palette"]["stem"]["base"]), stem_mask if clip is None else stem_mask * clip)
    kit.ink_edges(scene, mask, 2.2, item["group"], "line", clip=clip)
    note_focus(scene, mask, FOCUS_OBJECT)
    kit.register(scene, f"{item['group']}_{int(x)}", part.mask)


def paint_pear(scene, item, receiver):
    """Pear: a leaning tube, narrow at the shoulder and heavy at the base."""
    width = scene.size[1]
    x, base_y = item["x"] * width, item["base_y"] * width
    tall, radius = item["height"] * width, item["radius"] * width
    lean = np.deg2rad(item.get("tilt_deg", 0.0))
    cast_on_table(scene, x, base_y - radius * 0.1, radius, receiver)
    foot = np.array([x, base_y - radius * 0.92])
    head = foot + (tall - radius * 1.2) * np.array([np.sin(lean), -np.cos(lean)])
    path = np.linspace(head, foot, 12)
    widths = radius * np.array([0.30, 0.36, 0.40, 0.44, 0.52, 0.68, 0.84, 0.95, 1.0, 1.0, 0.98, 0.94])
    part = relief.tube(scene.size, path, widths)
    mask = kit.shade_solid(scene, part, item["group"], level=0.30, spread=0.7, gloss=0.18, shininess=14)
    speckle = noise(scene.size, 2.5, scene.fig.seed + 13, 1)
    multiply(scene.image, rgb(scene.style["palette"][item["group"]]["shadow"]), (speckle > 0.78) * mask, 0.10 * scene.shade_on)
    tip = head + radius * 0.30 * np.array([np.sin(lean), -np.cos(lean)])
    stem = smooth([tip, tip + [radius * 0.10, -radius * 0.30], tip + [radius * 0.30, -radius * 0.50]])
    over(scene.image, rgb(scene.style["palette"]["stem"]["base"]), stroke(scene.size, stem, max(radius * 0.09, 2.0) * taper(len(stem), 0.8, 0.9)))
    kit.ink_edges(scene, mask, 2.2, item["group"], "line")
    note_focus(scene, mask, FOCUS_OBJECT)
    kit.register(scene, f"pear_{int(x)}", mask)


def paint_bowl(scene, item, receiver):
    """Bowl seen from above: inside, then its fruit, then the outside wall in front of the fruit."""
    width = scene.size[1]
    x, rim_y = item["x"] * width, item["rim_y"] * width
    radius, depth = item["radius"] * width, item["depth"] * width
    tones = scene.style["palette"][item["group"]]
    cast_on_table(scene, x, rim_y + depth, radius * 0.62, receiver)
    opening = fill(scene.size, ellipse((x, rim_y), radius, radius * VIEW_TILT, 72))
    cols = np.arange(scene.size[1], dtype=np.float32)[None, :]
    toward = np.sign(scene.fig.light[0])
    # Why: inside a bowl the wall nearest the lamp is the one in shadow.
    near_lamp = np.clip(0.5 + toward * (cols - x) / (2 * radius), 0, 1) * np.ones((scene.size[0], 1), np.float32)
    inside = mix(rgb(tones["base"]), rgb(tones["shadow"]), scene.edge(near_lamp)[..., None])
    over(scene.image, inside, opening)
    kit.ink_edges(scene, opening, 2.0, item["group"], "line")
    # Why one extra level above the rim: the wall's roundness must continue up to
    # the front arc of the opening, or the shading breaks under the rim.
    sweep = np.linspace(0.0, 1.0, 10)
    profile = radius * np.concatenate([[1.0], np.sqrt(1.0 - (BOWL_CURVE * sweep) ** 2)])
    levels = np.concatenate([[rim_y - radius * VIEW_TILT], rim_y + depth * sweep])
    wall = relief.lathe(scene.size, x, levels[0], levels[-1], profile, tilt=VIEW_TILT, levels=levels)
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    front_arc = rim_y + radius * VIEW_TILT * np.sqrt(np.clip(1 - ((cols - x) / radius) ** 2, 0, None))
    outside = np.clip(rows - front_arc + 0.5, 0, 1) * wall.mask
    visible_inside = np.clip(1.0 - outside, 0, 1)
    for fruit in item.get("fruit", []):
        placed = dict(fruit, x=item["x"] + fruit["dx"], base_y=item["rim_y"] + fruit["dy"])
        paint_ball(scene, placed, None, clip=visible_inside)
    body = relief.Part(outside * wall.mask, wall.height)
    mask = kit.shade_solid(scene, body, item["group"], level=0.34, spread=0.6, gloss=0.3, shininess=30)
    if scene.shade_on:
        lip = stroke(scene.size, np.column_stack([np.linspace(x - radius * 0.98, x + radius * 0.98, 60),
                                                  rim_y + radius * VIEW_TILT * np.sqrt(np.clip(1 - np.linspace(-0.98, 0.98, 60) ** 2, 0, None))]), 2.5)
        screen(scene.image, rgb(tones["light"]), lip, 0.6)
    kit.ink_edges(scene, mask, 2.4, item["group"], "line")
    note_focus(scene, np.maximum(mask, opening), FOCUS_OBJECT)
    kit.register(scene, f"bowl_{int(x)}", np.maximum(mask, opening))


# ------------------------------------------------------------------ a kitchen table at night
def paint_window(scene, item):
    """A window in the back wall at night: dark sky, the next panel block with a few lit windows, frame and sill.

    Its box (`x0`, `x1`, `y0`, `y1`) is in shares of the picture width like every still life position.
    """
    width = scene.size[1]
    tones = scene.style["palette"].get("window", {"sky_top": "#0B1020", "sky_low": "#2A3046", "wall": "#3A3E48", "lit": "#FFC46E",
                                                  "dark": "#1A1E28", "frame": "#C9C4B8", "frame_shadow": "#8E897E", "line": "#22201C"})
    x0, x1, y0, y1 = (item[key] * width for key in ("x0", "x1", "y0", "y1"))
    glass = fill(scene.size, np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    share = np.clip((rows - y0) / max(y1 - y0, 1.0), 0.0, 1.0)
    sky = mix(rgb(tones["sky_top"]), rgb(tones["sky_low"]), share[..., None])
    over(scene.image, np.broadcast_to(sky, scene.image.shape), glass)
    # The block across the yard: a wall filling the lower part of the window, a grid of windows, a few lit.
    top = y0 + (y1 - y0) * item.get("block_top", 0.3)
    block = glass * np.clip(rows - top + 0.5, 0.0, 1.0)
    over(scene.image, rgb(tones["wall"]), block)
    cols = np.arange(scene.size[1], dtype=np.float32)[None, :]
    pitch = (x1 - x0) / item.get("columns", 7)
    u, v = (cols - x0) / pitch, (rows - top) / (pitch * 0.85)
    cell = ((np.mod(u, 1.0) > 0.3) & (np.mod(u, 1.0) < 0.7) & (np.mod(v, 1.0) > 0.3) & (np.mod(v, 1.0) < 0.75)).astype(np.float32)
    luck = np.sin(np.floor(u) * 12.9898 + np.floor(v) * 78.233 + scene.fig.seed) * 43758.5453
    lit = cell * ((luck - np.floor(luck)) < item.get("lit", 0.25))
    over(scene.image, rgb(tones["dark"]), cell * block)
    over(scene.image, rgb(tones["lit"]), lit * block)
    if scene.shade_on:
        screen(scene.image, rgb(tones["lit"]), blur(lit * block, pitch * 0.15) * glass, 0.5)
    frame = max(width * 0.008, 2.0)
    bars = [np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]), np.array([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)]),
            np.array([(x0, y0 + (y1 - y0) * 0.33), (x1, y0 + (y1 - y0) * 0.33)])]
    wood = np.zeros(scene.size, np.float32)
    for bar in bars:
        np.maximum(wood, stroke(scene.size, bar, frame * 2), out=wood)
    over(scene.image, rgb(tones["frame"]), wood)
    sill = fill(scene.size, np.array([(x0 - frame * 2, y1 + frame), (x1 + frame * 2, y1 + frame), (x1 + frame * 3, y1 + frame * 3.5),
                                       (x0 - frame * 3, y1 + frame * 3.5)]))
    over(scene.image, rgb(tones["frame_shadow"]), sill)
    if "window" in scene.style["palette"]:
        kit.ink_edges(scene, np.maximum(wood, sill), 1.4, "window", "line")
    note_focus(scene, glass, FOCUS_TABLE)


def paint_ashtray(scene, item, receiver):
    """A heavy glass ashtray: a low rim round a shallow dish, butts in it and a lit cigarette resting on the rim."""
    import smoking
    width = scene.size[1]
    x, base_y, radius = item["x"] * width, item["base_y"] * width, item["radius"] * width
    tall = radius * 0.32
    cast_on_table(scene, x, base_y, radius, receiver)
    part = relief.lathe(scene.size, x, base_y - tall, base_y, np.array([1.0, 1.0, 0.98, 0.94, 0.88]) * radius, tilt=VIEW_TILT)
    group = item.get("group", "ashtray")
    mask = kit.shade_solid(scene, part, group, level=0.34, spread=0.6, gloss=0.6, shininess=60)
    tones = scene.style["palette"][group]
    rim = ellipse((x, base_y - tall), radius, radius * VIEW_TILT, 48)
    dish = ellipse((x, base_y - tall + radius * 0.02), radius * 0.74, radius * 0.74 * VIEW_TILT, 48)
    over(scene.image, rgb(tones["light"]), fill(scene.size, rim), 0.55)
    over(scene.image, rgb(tones["shadow"]), fill(scene.size, dish))
    over(scene.image, rgb(tones["ash"]), fill(scene.size, ellipse((x, base_y - tall + radius * 0.04), radius * 0.5, radius * 0.5 * VIEW_TILT, 32)), 0.8)
    rng = np.random.default_rng(scene.fig.seed + 71)
    unit = radius / 1.4
    for k in range(item.get("butts", 3)):
        angle = rng.uniform(0, 2 * np.pi)
        center = np.array([x + np.cos(angle) * radius * 0.35, base_y - tall + np.sin(angle) * radius * 0.35 * VIEW_TILT])
        heading = rng.uniform(-0.6, 0.6)
        end = center + np.array([np.cos(heading), np.sin(heading) * VIEW_TILT]) * unit * 0.45 * rng.choice([-1, 1])
        smoking.paint_cigarette(scene, center, end, unit * 0.8, lit=False)
        over(scene.image, rgb(tones["ash"]), fill(scene.size, ellipse(end, unit * 0.07, unit * 0.06, 10)), 0.9)
    if item.get("lit", True):
        # The lit one rests in a notch of the rim, its lit end out over the table.
        notch = np.array([x + radius * 0.85, base_y - tall + radius * 0.25 * VIEW_TILT])
        tip = notch + np.array([unit * 0.85, unit * 0.12])
        _, ember = smoking.paint_cigarette(scene, notch - np.array([unit * 0.4, unit * 0.05]), tip, unit)
        smoking.paint_smoke(scene, ember, unit, scene.fig.seed + 73, item.get("smoke", 1.6), drift=-0.15)
    kit.ink_edges(scene, mask, 2.0, group, "line")
    note_focus(scene, mask, FOCUS_OBJECT)


def paint_tea_glass(scene, item, receiver):
    """Tea in a faceted glass in a metal holder with a handle; a spoon leaning in it."""
    width = scene.size[1]
    x, base_y, radius, tall = item["x"] * width, item["base_y"] * width, item["radius"] * width, item["height"] * width
    cast_on_table(scene, x, base_y, radius, receiver)
    glass = relief.lathe(scene.size, x, base_y - tall, base_y, np.linspace(1.0, 0.84, 8) * radius, tilt=VIEW_TILT)
    tones = scene.style["palette"]
    over(scene.image, rgb(tones["tea"]["base"]), glass.mask)
    kit.shade_solid(scene, relief.Part(glass.mask * (np.arange(scene.size[0])[:, None] > base_y - tall * 0.88), glass.height),
                    "tea", level=0.4, spread=0.6, gloss=0.5, shininess=40)
    holder_top = base_y - tall * 0.62
    holder = relief.lathe(scene.size, x, holder_top, base_y + radius * 0.04, np.array([0.99, 0.9, 0.86, 0.88, 0.95, 1.02]) * radius * 1.06,
                          tilt=VIEW_TILT)
    kit.shade_solid(scene, holder, "holder", level=0.36, spread=0.5, gloss=0.9, shininess=70)
    if scene.shade_on:
        rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
        cols = np.arange(scene.size[1], dtype=np.float32)[None, :]
        lace = (np.sin((cols - x) / (radius * 0.14)) * np.sin((rows - holder_top) / (radius * 0.14)) > 0.55).astype(np.float32)
        over(scene.image, rgb(tones["holder"]["shadow"]), lace * holder.mask * (rows > holder_top + radius * 0.15), 0.6)
    side = 1.0 if item.get("handle", "right") == "right" else -1.0
    handle = smooth([(x + side * radius * 1.0, holder_top + tall * 0.08), (x + side * radius * 1.55, holder_top + tall * 0.22),
                     (x + side * radius * 1.5, holder_top + tall * 0.45), (x + side * radius * 0.98, holder_top + tall * 0.52)], samples=8)
    over(scene.image, rgb(tones["holder"]["base"]), stroke(scene.size, handle, radius * 0.16))
    rim = ellipse((x, base_y - tall), radius, radius * VIEW_TILT, 40)
    over(scene.image, rgb(tones["tea"]["light"]), fill(scene.size, rim), 0.35)
    spoon = np.array([(x - radius * 0.25, base_y - tall + radius * 0.2), (x + radius * 0.3, base_y - tall - radius * 1.2)])
    over(scene.image, rgb(tones["holder"]["light"]), stroke(scene.size, spoon, radius * 0.07 * taper(2, 1.0, 1.0)))
    over(scene.image, rgb(tones["holder"]["light"]), fill(scene.size, ellipse(spoon[1], radius * 0.08, radius * 0.13, 12)))
    kit.ink_edges(scene, np.maximum(glass.mask, holder.mask), 2.0, "holder", "line")
    note_focus(scene, np.maximum(glass.mask, holder.mask), FOCUS_OBJECT)


def paint_can(scene, item, receiver):
    """A drinks can: a straight cylinder, a printed band, the lid's rim catching the light."""
    width = scene.size[1]
    x, base_y, radius, tall = item["x"] * width, item["base_y"] * width, item["radius"] * width, item["height"] * width
    cast_on_table(scene, x, base_y, radius, receiver)
    profile = np.array([0.86, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.96]) * radius
    part = relief.lathe(scene.size, x, base_y - tall, base_y, profile, tilt=VIEW_TILT)
    group = item.get("group", "can")
    mask = kit.shade_solid(scene, part, group, level=0.34, spread=0.5, gloss=0.8, shininess=50)
    tones = scene.style["palette"][group]
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    cols = np.arange(scene.size[1], dtype=np.float32)[None, :]
    sag = radius * VIEW_TILT * np.sqrt(np.clip(1 - ((cols - x) / radius) ** 2, 0, None))
    band = np.clip(rows - (base_y - tall * 0.62 + sag) + 0.5, 0, 1) * np.clip((base_y - tall * 0.36 + sag) - rows + 0.5, 0, 1) * mask
    over(scene.image, rgb(tones["band"]), band, 0.85)
    lid = fill(scene.size, ellipse((x, base_y - tall), profile[0], profile[0] * VIEW_TILT, 40))
    over(scene.image, rgb(tones["light"]), lid, 0.6)
    kit.ink_edges(scene, mask, 2.0, group, "line")
    note_focus(scene, mask, FOCUS_OBJECT)


PAINTERS = {"bottle": paint_lathe, "vase": paint_lathe, "jar": paint_lathe, "cup": paint_lathe,
            "ball": paint_ball, "pear": paint_pear, "bowl": paint_bowl, "ashtray": paint_ashtray, "tea_glass": paint_tea_glass,
            "can": paint_can}


def base_height(item):
    """Where the object stands on the table (larger = nearer the viewer)."""
    return item["rim_y"] + item["depth"] if item["kind"] == "bowl" else item["base_y"]


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    paint_wall(scene)
    for item in fig.spec.get("wall_items", []):
        paint_window(scene, item)
    run_hook(extras, "after_background", scene)
    top, front = paint_table(scene)
    paint_cloth(scene, top, front)
    receiver = np.maximum(top, front)
    for item in sorted(fig.spec["objects"], key=base_height):
        PAINTERS[item["kind"]](scene, item, receiver)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
