"""Example: the doomer mood, the skill's signature look.

Seven pictures from one cold world, each in the style that suits it best:
a man, a woman, a two-shot, an establishing shot, a city, a landscape and a still life.
The world is grey concrete, overcast sky and snow; the one warm thing in each picture is a light.
Every picture ends with fx.doomer, which drains the colour but leaves warm lights alone.

Usage: python examples/doomer.py --cut man|woman|pair|establishing|city|landscape|still_life|all --out-dir doomer
       --style anime|illust|painterly overrides the style chosen for each cut.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, fx, geometry as geo, objects, raster, scenery, sets, shading as sh
from codepainter.color import mix, shadow_of
from codepainter.figure import PortraitSpec, draw_figure, draw_portrait
from codepainter.figure.body import MALE_BODY, BodySpec, make_pose
from codepainter.figure.frame import FACES
from codepainter.figure.palette import look
from codepainter.figure.stage import Actor, draw_actors, floor_shadows, frame
from codepainter.figure.wardrobe import WARDROBE
from codepainter.styles import finish, get_style, line_color, paint_part

PORTRAIT, BUST, LANDSCAPE = (1024, 1536), (1024, 1280), (1536, 1024)
HAT = "#4a4d55"                   # charcoal: a black beanie on black hair would read as a haircut
GREY_HOODIE = ("#3b3e45", "#2a2f38")
SNOW_FLAKES = 1400                # flakes over a whole picture
CONCRETE, CONCRETE_SHADE = "#9a9d97", "#5e6668"
SKY_HIGH, SKY_LOW = "#56656d", "#c3cac6"


# ---- people ------------------------------------------------------------------------------
def him(**extra):
    """The young man of the series: tired eyes, black hoodie, knitted beanie."""
    return PortraitSpec(**{**FACES["sharp_man"], **look("light", "black", "gray", "doomer"), "hat": "beanie", "hat_color": HAT,
                           "eye_open": 0.72, "expression": "sad", **extra})


def her(**extra):
    """The young woman of the series: pale, long black hair with a fringe, drooping eyes."""
    return PortraitSpec(**{**FACES["gentle"], **look("porcelain", "black", "gray", "doomer"), "hair_style": "long",
                           "bangs": "curtain", "eye_open": 0.80, "smile": 0.0, **extra})


def _finish(painting, style, importance=None, seed=0):
    return fx.doomer(finish(painting, style, seed=seed, importance=importance), seed=seed)


def man(style):
    """Waist shot under the yard lamp, turned a little away from it, eyes down, snow falling."""
    painting = Painting(*PORTRAIT)
    info = sets.panel_block(painting, style, horizon=0.70, lamp=0.86, seed=11)
    actor = Actor(him(), MALE_BODY, make_pose("stance", yaw=-22, head_tilt=7), WARDROBE["hoodie"])
    (actor.pose,) = frame([(actor.pose, actor.body)], painting.shape, "waist", centers=(0.40,))
    figures = draw_actors(painting, [actor], style)
    sets.light_figures(painting, figures, info, style)
    scenery.snowfall(painting, SNOW_FLAKES, seed=21, keep_clear=actor.masks["head"])
    return painting, _finish(painting, style, actor.masks["head"])


def woman(style):
    """Bust at a window-lit night yard: black turtleneck, fringe, eyes down."""
    painting = Painting(*BUST)
    info = sets.panel_block(painting, style, horizon=0.86, lamp=0.12, lit=0.30, seed=12)
    masks = draw_portrait(painting, her(turn_deg=-22, crown=(0.50, 0.12), head_size=0.46, earrings="stud", jewel="#c9c9cf",
                                        cloth="#1c1c22"), style)
    sets.light_figures(painting, masks["figure"], info, style)
    scenery.snowfall(painting, SNOW_FLAKES, seed=22, keep_clear=masks["head"])
    return painting, _finish(painting, style, masks["head"])


def pair(style):
    """Two people under one lamp, each turned away from the other."""
    painting = Painting(*LANDSCAPE)
    info = sets.panel_block(painting, style, horizon=0.68, lamp=0.53, seed=13)
    she = Actor(her(**dict(zip(("cloth", "cloth_second"), GREY_HOODIE))), BodySpec(),
                make_pose("contrapposto", yaw=-20, head_yaw=-45, head_tilt=8), WARDROBE["hoodie"], depth=-0.2)
    he = Actor(him(), MALE_BODY, make_pose("stance", yaw=20, head_yaw=40, head_tilt=6), WARDROBE["hoodie"])
    she.pose, he.pose = frame([(she.pose, she.body), (he.pose, he.body)], painting.shape, "knee", centers=(0.30, 0.74))
    figures = draw_actors(painting, [she, he], style)
    sets.light_figures(painting, figures, info, style)
    scenery.snowfall(painting, SNOW_FLAKES, seed=23, keep_clear=np.maximum(she.masks["head"], he.masks["head"]))
    return painting, _finish(painting, style, np.maximum(she.masks["head"], he.masks["head"]))


# ---- places ------------------------------------------------------------------------------
def overcast(painting, style, horizon, seed, low=SKY_LOW):
    """Flat winter sky: a dull gradient with faint cloud banks."""
    backdrop.gradient(painting, SKY_HIGH, low, end=(0, horizon))
    cloud = scenery.clouds(painting.shape, coverage=0.5, scale=0.8, seed=seed, softness=0.05 if style.name == "anime" else 0.14,
                           band=(0, horizon * 0.95))
    painting.fill(cloud, "#7a878d", 0.35)


def snowy_ground(painting, horizon, seed, near="#56636a"):
    """Snow from the horizon down, mottled with slush, darker toward the viewer in the dusk. Returns its mask."""
    height, width = painting.shape
    rows = np.arange(height, dtype=np.float32)[:, None]
    ground = (rows >= horizon).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(ground, "#c9cfcb")
    slush = sh.smoothstep(0.55, 0.75, fx.fbm(painting.shape, scale=2.0, seed=seed, stretch=(1.0, 4.0)))
    painting.fill(ground * slush, "#9aa19f", 0.5)
    painting.fill(ground * sh.linear_ramp(painting.shape, (0, horizon), (0, height)), near, 0.30)
    return ground


def footprints(painting, path, step, size, color="#5c6562", opacity=0.85):
    """A trail of footprints along a pixel path, left and right in turn, shrinking with the path's distance."""
    path = geo.as_points(path)
    count = max(int(geo.path_length(path) / step), 2)
    points = geo.resample(path, count)
    for index, (point, after) in enumerate(zip(points[:-1], points[1:])):
        along = (after - point) / max(np.linalg.norm(after - point), 1e-9)
        scale = 0.35 + 0.65 * (1.0 - index / count)          # the trail starts near the viewer
        offset = np.array([-along[1], along[0]]) * size * 0.9 * scale * (1 if index % 2 else -1)
        print_ = geo.ellipse(point + offset, size * 0.45 * scale, size * 0.22 * scale)
        painting.fill(painting.mask(print_), color, opacity)


def climber(painting, foot, width, height, depth, color="#2e3236", line=1.0):
    """Arched climbing frame of a yard playground: parallel hoops with rungs, receding by `depth` pixels."""
    hoops = []
    for share in np.linspace(0.0, 1.0, 5):
        base = np.asarray(foot, dtype=np.float64) + [depth * share, -depth * 0.35 * share]
        scale = 1.0 - 0.25 * share
        hoops.append(geo.arc((base[0] + width * scale / 2, base[1]), width * scale / 2, height * scale, np.pi, 2 * np.pi, 24))
    for hoop in hoops:
        painting.stroke(hoop, line * 2.2, color, taper=(0.0, 0.0), layer="color")
        painting.stroke(hoop[8:17] - [0, line * 1.2], line * 1.4, "#dfe3df", taper=(0.3, 0.3), opacity=0.8, layer="color")
    for index in range(0, len(hoops[0]), 4):
        rung = np.array([hoop[index] for hoop in hoops])
        painting.stroke(rung, line * 1.4, color, taper=(0.0, 0.0), layer="color")


def establishing(style):
    """A yard between the blocks at dusk; one small figure under the only lamp, his trail behind him."""
    painting = Painting(*LANDSCAPE)
    height, width = painting.shape
    horizon = 0.60 * height
    vanish = (0.62 * width, horizon)
    overcast(painting, style, horizon, seed=31)
    far = painting.mask(scenery.skyline(painting.shape, horizon + 2, heights=(height * 0.06, height * 0.16),
                                        widths=(width * 0.05, width * 0.10), seed=32))
    painting.fill(far, "#8a9598")
    ground = snowy_ground(painting, horizon, seed=33)
    line = 1.3 * style.line_width * height / 1000.0
    across = [(0.50 * width, 0.31 * height), (1.04 * width, 0.31 * height), (1.04 * width, horizon), (0.50 * width, horizon)]
    lights = scenery.panel_facade(painting, across, 9, 22, seed=34, lit=0.24, shade=0.2, stairs_every=6, line_width=line)
    side = scenery.street_wall((-0.12 * width, 0.86 * height), vanish, 0.0, 0.70, 0.86 * height)
    lights = np.maximum(lights, scenery.panel_facade(painting, side, 14, 26, seed=35, lit=0.20, balcony_every=4,
                                                     stairs_every=9, line_width=line))
    painting.fill(sh.blur(lights, height * 0.004), "#ffb060", 0.35, "screen")
    for x, size, birch in ((0.86, 0.30, False), (0.95, 0.24, True), (0.54, 0.16, False)):
        scenery.bare_tree(painting, (x * width, horizon + height * 0.02 + size * 0.2 * height), size * height,
                          seed=int(x * 100), color="#2c2f33", birch=birch)
    climber(painting, (0.66 * width, 0.70 * height), 0.10 * width, 0.07 * height, 0.06 * width, line=height / 1000.0 * 1.6)
    lamp_foot = (0.42 * width, 0.74 * height)
    footprints(painting, [(0.12 * width, 1.02 * height), (0.25 * width, 0.88 * height), (0.40 * width, 0.765 * height)],
               step=height * 0.022, size=height * 0.022)
    scenery.sodium_lamp(painting, lamp_foot, 0.26 * height, side=1.0, ground=ground)
    unit = 0.012
    figure = draw_figure(painting, him(), MALE_BODY, make_pose("back", root=(0.405, 0.745 - 3.6 * unit), unit=unit),
                         style, dress=WARDROBE["hoodie"])
    scenery.snowfall(painting, SNOW_FLAKES // 2, seed=36)
    return painting, _finish(painting, style, sh.blur(figure["figure"], height * 0.02))


def block(painting, front, size, roof_depth, floors, bays, seed, lit, line):
    """One apartment block seen from above: front face, roof and the end wall in shade.

    front: bottom-left corner of the front face (pixels). size: (width, height) of the front face.
    roof_depth: (dx, dy) the roof runs back by. Returns (mask of the block, mask of its lit windows).
    """
    x, y = front
    w, h = size
    dx, dy = roof_depth
    face = [(x, y - h), (x + w, y - h), (x + w, y), (x, y)]
    roof = [(x + dx, y - h - dy), (x + w + dx, y - h - dy), (x + w, y - h), (x, y - h)]
    end = [(x + w, y - h), (x + w + dx, y - h - dy), (x + w + dx, y - dy), (x + w, y)]
    lights = scenery.panel_facade(painting, end, floors, 3, seed=seed + 1, lit=lit * 0.4, shade=0.6, line_width=line)
    lights = np.maximum(lights, scenery.panel_facade(painting, face, floors, bays, seed=seed, lit=lit, line_width=line,
                                                     stairs_every=bays // 3 if bays >= 9 else 0))
    top = painting.mask(roof)
    painting.part(top, "#7b8282")
    box = [(x + dx + w * 0.3, y - h - dy * 0.75), (x + dx + w * 0.42, y - h - dy * 0.75), (x + w * 0.42 + dx * 0.4, y - h - dy * 0.15),
           (x + w * 0.3 + dx * 0.4, y - h - dy * 0.15)]
    painting.fill(painting.mask(box), "#5f6667")                          # lift machine room on the roof
    whole = np.maximum.reduce([painting.mask(face), top, painting.mask(end)])
    return whole, lights


def chimney(painting, foot, height, width, seed, line):
    """Striped heating-plant chimney with smoke leaning away on the wind."""
    x, y = foot
    taper = width * 0.18
    bands = 9
    for index in range(bands):
        top, bottom = y - height * (index + 1) / bands, y - height * index / bands
        inset_top, inset_bottom = taper * (index + 1) / bands, taper * index / bands
        stripe = [(x - width / 2 + inset_top, top), (x + width / 2 - inset_top, top), (x + width / 2 - inset_bottom, bottom),
                  (x - width / 2 + inset_bottom, bottom)]
        painting.fill(painting.mask(stripe), "#a5574c" if index % 2 else "#d4d2c8")
    body = [(x - width / 2 + taper, y - height), (x + width / 2 - taper, y - height), (x + width / 2, y), (x - width / 2, y)]
    painting.fill(painting.mask(body) * sh.linear_ramp(painting.shape, (x - width / 2, 0), (x + width / 2, 0)), "#3d4448", 0.45)
    if line > 0:
        painting.outline(body, line, "#2a2e30")
    rng = np.random.default_rng(seed)
    for step in range(7):
        center = (x - step * width * 1.4 - rng.uniform(0, width * 0.5), y - height - width * (0.4 + step * 0.55))
        puff, _ = scenery.puffs(painting, center, width * (1.2 + step * 0.7), width * (0.9 + step * 0.35), count=7,
                                seed=seed + step, flat_base=False)
        painting.fill(sh.blur(puff, width * 0.15), "#e3e4df", 0.75 - step * 0.07)


def city(style):
    """The district from a high window: rows of blocks to the haze, a striped chimney, a low pale sun."""
    painting = Painting(*LANDSCAPE)
    height, width = painting.shape
    horizon = 0.36 * height
    backdrop.gradient(painting, "#5a6871", "#d8cdb6", end=(0, horizon))
    backdrop.glow(painting, (0.24 * width, horizon - 0.02 * height), 0.30 * height, "#f2c48a", opacity=0.45)
    rng = np.random.default_rng(41)
    line = 1.0 * style.line_width * height / 1000.0
    ground = snowy_ground(painting, horizon, seed=43, near="#6a767c")
    # Seen from high up the far yards are trodden grey and hazy, never brighter than the blocks standing in them.
    painting.fill(ground * (1.0 - sh.linear_ramp(painting.shape, (0, horizon), (0, height))), "#9ba3a2", 0.7)
    lights = np.zeros(painting.shape, dtype=np.float32)
    drawn = np.zeros(painting.shape, dtype=np.float32)
    rows = 6
    for row in range(rows):                                   # far rows first
        near = row / (rows - 1)
        scale = 0.18 + 0.82 * near ** 1.6
        base = horizon + (height * 1.08 - horizon) * near ** 1.25
        road = [(-2, base + height * 0.010 * scale), (width + 2, base + height * 0.010 * scale),
                (width + 2, base + height * 0.034 * scale), (-2, base + height * 0.034 * scale)]
        painting.fill(painting.mask(road), "#7b8380", 0.8)      # the street in front of each row, grey slush
        crowns = [geo.ellipse((cx, cy), height * 0.010 * scale * size, height * 0.006 * scale * size, count=10)
                  for cx, cy, size in scenery.scatter((0, base + height * 0.02 * scale, width, base + height * 0.06 * scale), 60,
                                                      seed=int(rng.integers(1000)), near_scale=1.6, far_scale=0.8)]
        painting.fill(raster.fill_many(crowns, painting.shape), "#4c5050", 0.6)   # bare yard trees seen from above
        x = -rng.uniform(0.0, 0.25) * width * scale
        while x < width:
            w = width * scale * rng.uniform(0.32, 0.55)
            floors = int(rng.choice([5, 9, 9, 12, 16]))
            h = floors * height * 0.030 * scale
            mask, lit = block(painting, (x, base), (w, h), (w * 0.10, height * 0.05 * scale), floors,
                              max(int(w / (height * 0.032 * scale)), 3), int(rng.integers(1000)), 0.24, line * scale)
            lights, drawn = np.maximum(lights, lit), np.maximum(drawn, mask)
            x += w * rng.uniform(1.15, 1.45)
        if near > 0.3:                                         # bare trees along the street, in front of the row
            for tree_x in rng.uniform(0.0, 1.0, 7) * width:
                scenery.bare_tree(painting, (tree_x, base + height * 0.030 * scale), height * 0.16 * scale,
                                  seed=int(rng.integers(1000)), color="#3a3e40", depth=3)
        if row == 1:
            chimney(painting, (0.70 * width, base - height * 0.01), 0.32 * height, 0.024 * width, seed=42, line=line)
        haze = (1.0 - near) * 0.55
        painting.fill(drawn, "#c6c8bf", haze * 0.5)            # air between the rows pales everything behind
    painting.fill(sh.blur(lights, height * 0.003), "#ffb060", 0.35, "screen")
    pole = (0.06 * width, 0.98 * height)
    for end in ((1.04 * width, 0.30 * height), (1.04 * width, 0.36 * height)):
        painting.stroke(scenery.wire((pole[0], 0.10 * height), end, height * 0.06), max(height * 0.002, 1.0), "#22262a",
                        taper=(0.0, 0.0), layer="color")
    painting.stroke(np.array([pole, (pole[0], 0.08 * height)]), height * 0.012, "#22262a", taper=(0.0, 0.0), layer="color")
    return painting, _finish(painting, style)


def pylon(painting, foot, height, color="#2b2f33"):
    """Lattice power pylon: two legs closing toward the top, cross bracing and two cross-arms. Returns the arm tips."""
    x, y = foot
    width = height * 0.30
    top = y - height
    legs = [np.array([(x - width / 2, y), (x - width * 0.08, top)]), np.array([(x + width / 2, y), (x + width * 0.08, top)])]
    thick = max(height * 0.012, 0.8)
    for leg in legs:
        painting.stroke(leg, thick, color, taper=(0.0, 0.0), layer="color")
    levels = np.linspace(0.0, 1.0, 7)
    left = [geo.lerp(legs[0][0], legs[0][1], t) for t in levels]
    right = [geo.lerp(legs[1][0], legs[1][1], t) for t in levels]
    for low in range(len(levels) - 1):
        for a, b in ((left[low], right[low + 1]), (right[low], left[low + 1]), (left[low], right[low])):
            painting.stroke(np.array([a, b]), thick * 0.45, color, taper=(0.0, 0.0), layer="color")
    tips = []
    for share, reach in ((0.80, 0.24), (0.93, 0.17)):
        center = geo.lerp(np.array([x, y]), np.array([x, top]), share)
        arm = np.array([center - [height * reach, 0.0], center + [height * reach, 0.0]])
        painting.stroke(arm, thick * 0.9, color, taper=(0.0, 0.0), layer="color")
        tips += [arm[0] + [0.0, height * 0.04], arm[1] + [0.0, height * 0.04]]
    return tips


def landscape(style):
    """Snowfield on the city's edge: a birch copse, pylons striding to the horizon, the blocks far away."""
    painting = Painting(*LANDSCAPE)
    height, width = painting.shape
    horizon = 0.58 * height
    overcast(painting, style, horizon, seed=51, low="#d2d4cc")
    sun = (0.70 * width, horizon - 0.06 * height)
    backdrop.glow(painting, sun, 0.30 * height, "#f0a860", opacity=0.75, mode="normal")
    painting.fill(painting.mask(geo.ellipse(sun, 0.028 * height, 0.028 * height)), "#ffd9a0", 0.9)   # the low sun through haze
    far = painting.mask(scenery.skyline(painting.shape, horizon + 1, heights=(height * 0.03, height * 0.07),
                                        widths=(width * 0.03, width * 0.07), seed=52))
    painting.fill(far * (sh.linear_ramp(painting.shape, (0.30 * width, 0), (0.95 * width, 0)) > 0.0), "#7f898b")
    treeline = painting.mask(scenery.ridge(painting.shape, horizon + 2, height * 0.012, seed=53))
    painting.fill(treeline, "#6f7775")
    ground = snowy_ground(painting, horizon + height * 0.008, seed=54, near="#7d8a90")
    rng = np.random.default_rng(55)
    for root, tip, bend in scenery.blades((0, horizon + height * 0.06, width, height), 420, height * 0.035, seed=56):
        painting.stroke(geo.bent_line(root, tip, bend), max(height * 0.0016, 1.0), "#8a7f66", taper=(0.0, 0.9),
                        opacity=0.65, layer="color", clip=ground)
    previous = None
    for share in (1.0, 0.62, 0.40, 0.26, 0.17, 0.11):          # pylons from the near right to the horizon
        foot = (0.40 * width + 0.62 * width * share, horizon + (0.95 * height - horizon) * share ** 1.3)
        tips = pylon(painting, foot, 0.62 * height * share ** 1.1 + 4.0)
        if previous is not None:
            for start, end in zip(previous, tips):
                painting.stroke(scenery.wire(end, start, height * 0.05 * share + 2.0), max(height * 0.0012, 0.8), "#30353a",
                                taper=(0.0, 0.0), layer="color")
        previous = tips
    for x, size in ((0.06, 0.56), (0.13, 0.48), (0.19, 0.60), (0.25, 0.40), (0.31, 0.34), (0.36, 0.26)):
        foot_y = horizon + height * (0.30 - 0.32 * (x - 0.06))
        scenery.bare_tree(painting, (x * width, foot_y), size * height, seed=int(rng.integers(1000)), color="#33302e",
                          birch=x in (0.13, 0.25), width=size * height * 0.022)
    for _ in range(9):                                          # a few crows
        cx, cy, wing = rng.uniform(0.42, 0.70) * width, rng.uniform(0.14, 0.30) * height, height * rng.uniform(0.006, 0.012)
        painting.stroke(np.array([(cx - wing, cy - wing * 0.4), (cx, cy), (cx + wing, cy - wing * 0.4)]), max(height * 0.0018, 1.0),
                        "#1f2224", taper=(0.2, 0.2), layer="color")
    scenery.snowfall(painting, SNOW_FLAKES // 3, seed=57, size=(0.6, 2.4))
    return painting, _finish(painting, style)


def still_life(style):
    """Kitchen sill at night: a glass of tea in a metal holder, a cassette, wired earphones; the block outside."""
    painting = Painting(*LANDSCAPE)
    height, width = painting.shape
    light = (-0.55, -0.45, 0.70)                              # a warm kitchen lamp up on the left
    painting.color[:] = np.asarray(shadow_of("#6e6a62", (0.5, 0.5, 0.55)))
    pane = [(0.12 * width, 0.03 * height), (0.90 * width, 0.03 * height), (0.90 * width, 0.52 * height), (0.12 * width, 0.52 * height)]
    glass = painting.mask(pane)
    view = Painting(width, height, "#2c3a44")                  # the night outside, seen only through the glass
    lights = scenery.panel_facade(view, [(0.04 * width, -0.02 * height), (0.98 * width, 0.06 * height), (0.98 * width, 0.60 * height),
                                         (0.04 * width, 0.60 * height)], 8, 15, seed=61, lit=0.32, shade=0.45, stairs_every=5,
                                  wall="#6c7476")
    view.fill(sh.blur(lights, height * 0.006), "#ffb060", 0.45, "screen")
    view.fill(np.ones(painting.shape, dtype=np.float32), "#1f2a33", 0.35)   # the night outside is darker than the wall it shows
    scenery.snowfall(view, 700, seed=62)
    mist = sh.linear_ramp(painting.shape, (0, 0.30 * height), (0, 0.52 * height))
    view.fill(mist * fx.fbm(painting.shape, scale=3.0, seed=63), "#cfd6d6", 0.45)   # breath of the kitchen on the glass
    painting.color += (view.color - painting.color) * glass[..., None]
    frame_color = "#d9d6cc"
    bars = ([(0.11, 0.02), (0.91, 0.02), (0.91, 0.045), (0.11, 0.045)], [(0.495, 0.03), (0.525, 0.03), (0.525, 0.52), (0.495, 0.52)],
            [(0.11, 0.02), (0.135, 0.02), (0.135, 0.53), (0.11, 0.53)], [(0.885, 0.02), (0.91, 0.02), (0.91, 0.53), (0.885, 0.53)])
    for bar in bars:
        paint_part(painting, np.array(bar) * [width, height], frame_color, style, light, line_width=1.6)
    sill_top = np.array([(0.0, 0.52), (1.0, 0.52), (1.03, 0.78), (-0.03, 0.78)]) * [width, height]
    sill_front = np.array([(-0.03, 0.78), (1.03, 0.78), (1.03, 0.85), (-0.03, 0.85)]) * [width, height]
    paint_part(painting, sill_top, "#cfcbc0", style, light, line_width=1.6)
    paint_part(painting, sill_front, "#a9a59b", style, light, line_width=1.6)
    painting.fill(painting.mask(np.array([(-0.03, 0.85), (1.03, 0.85), (1.03, 1.01), (-0.03, 1.01)]) * [width, height]), "#4b4a46")
    top = painting.mask(sill_top)
    # Normal blending keeps the lamp's warmth, which the doomer grade leaves alone only while it stays saturated.
    backdrop.glow(painting, (0.28 * width, 0.66 * height), 0.40 * height, "#f0a860", opacity=0.40, mode="normal")
    paint_cassette(painting, style, light, top, center=(0.70 * width, 0.67 * height), size=(0.15 * width, 0.075 * height))
    paint_tea(painting, style, light, top, foot=(0.34 * width, 0.70 * height), radius=0.062 * width)
    cord = geo.smooth(np.array([(0.45, 0.72), (0.53, 0.61), (0.50, 0.57), (0.45, 0.61), (0.50, 0.68), (0.58, 0.70),
                                (0.61, 0.74)]) * [width, height])
    painting.stroke(cord, height * 0.006, "#e8e6df", taper=(0.0, 0.0), layer="color")
    for bud in ((0.45 * width, 0.72 * height), (0.458 * width, 0.70 * height)):
        painting.fill(painting.mask(geo.ellipse(bud, 0.011 * width, 0.008 * width)), "#f2f0ea")
    return painting, _finish(painting, style)


def _sill_shadow(painting, mask, top):
    painting.fill(sh.ground_shadow(mask, lean=0.6, squash=0.18, softness=6.0) * top * (1.0 - mask), "#2a2a2e", 0.5, "multiply")


def paint_cassette(painting, style, light, top, center, size):
    """Audio cassette lying at a slant: dark shell, pale label, two reel hubs."""
    def place(points):
        return geo.transform(np.array(points) * [size[0] / 2, size[1] / 2], angle=np.radians(-8), translate=center)
    shell = place([(-1, -1), (1, -1), (1, 1), (-1, 1)])
    _sill_shadow(painting, painting.mask(shell), top)
    paint_part(painting, shell, "#2b2b30", style, light, line_width=1.8)
    painting.fill(painting.mask(place([(-0.86, -0.80), (0.86, -0.80), (0.86, 0.30), (-0.86, 0.30)])), "#d8cfb8")
    painting.fill(painting.mask(place([(-0.55, -0.40), (0.55, -0.40), (0.55, 0.05), (-0.55, 0.05)])), "#3a3a40")
    for side in (-1, 1):
        hub = place([(side * 0.40, -0.18)])[0]
        painting.fill(painting.mask(geo.ellipse(hub, size[1] * 0.16, size[1] * 0.16)), "#e8e2d2")


def paint_tea(painting, style, light, top, foot, radius):
    """Glass of tea in a metal holder with a handle, a spoon left in it; the kitchen lamp glows through the tea."""
    holder_height, glass_height = radius * 1.3, radius * 1.5
    holder = objects.paint_cylinder(painting, foot, radius * 1.04, holder_height, "#a29d92", style, light, squash=0.30)
    _sill_shadow(painting, holder["body"], top)
    rim = (foot[0], foot[1] - holder_height)
    cup = objects.paint_cylinder(painting, rim, radius, glass_height, "#c7802f", style, light, squash=0.30, hollow="#8a4a1c")
    painting.fill(cup["body"] * sh.linear_ramp(painting.shape, (foot[0] - radius, 0), (foot[0] + radius, 0)), "#f6c070", 0.55)
    painting.fill(painting.mask(geo.ellipse((foot[0] - radius * 0.5, rim[1] - glass_height * 0.55), radius * 0.08, glass_height * 0.32)),
                  "#fff2dc", 0.7)                                  # window light on the glass
    for band in (0.25, 0.65):                                      # the holder's pressed pattern
        y = foot[1] - holder_height * band
        painting.stroke(geo.arc((foot[0], y), radius * 1.04, radius * 0.30, 0.0, np.pi, 20), radius * 0.05, "#7c786f",
                        taper=(0.0, 0.0), opacity=0.6, layer="color", clip=holder["body"])
    handle = geo.arc((foot[0] + radius * 1.10, foot[1] - holder_height * 0.55), radius * 0.38, holder_height * 0.42,
                     -np.pi / 2, np.pi / 2, 16)
    painting.stroke(handle, radius * 0.12, "#86817a", taper=(0.0, 0.0), layer="color")
    painting.stroke(np.array([(foot[0] + radius * 0.35, rim[1] - glass_height * 1.45), (foot[0] - radius * 0.05, rim[1] - glass_height * 0.75)]),
                    radius * 0.09, "#cbc8bf", taper=(0.0, 0.0), layer="color")   # spoon


CUTS = {"man": (man, "illust"), "woman": (woman, "anime"), "pair": (pair, "anime"), "establishing": (establishing, "painterly"),
        "city": (city, "illust"), "landscape": (landscape, "painterly"), "still_life": (still_life, "painterly")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cut", default="all", choices=list(CUTS) + ["all"])
    parser.add_argument("--style", default=None, choices=["anime", "illust", "painterly"])
    parser.add_argument("--out-dir", default="doomer")
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (list(CUTS) if args.cut == "all" else [args.cut]):
        build, style_name = CUTS[name]
        painting, image = build(get_style(args.style or style_name))
        painting.save(str(out / f"doomer_{name}.png"), image)
        print(f"saved {out / f'doomer_{name}.png'}")


if __name__ == "__main__":
    main()
