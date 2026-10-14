"""Backgrounds for figure scenes: beach, bedroom, office, night street, cafe, park, panel block.

Each set paints the whole canvas behind the figures and returns a SetInfo: where the floor
meets the far wall or the sea (horizon), the colour of the ground for cast shadows, and a colour
grade to apply to the finished image so the figures sit in the same light.

    info = sets.SETS["beach"](painting, style)
    ... draw figures ...
    image = finish(painting, style); image = fx.grade(image, **info.grade)
"""
from dataclasses import dataclass, field

import numpy as np

from . import backdrop, fx, scenery
from . import geometry as geo
from . import shading as sh
from .color import mix, rgb, shadow_of
from .styles import line_color


@dataclass
class SetInfo:
    horizon: float                         # pixel row where the floor or sea meets the background
    ground: str                            # floor colour, for the shadows figures throw on it
    grade: dict = field(default_factory=dict)
    ambient: tuple = None                  # (colour, amount) multiplied over the figures: the set's light level
    rim: tuple = None                      # (colour, amount, side) of a light catching the figures' edges; side -1 left, 1 right


RIM_WIDTH = 0.0045           # set rim light width as a share of the canvas height
RIM_SOFT_ANIME, RIM_SOFT = 0.35, 0.6   # rim blur as a share of its width


def light_figures(painting, figures, info, style):
    """Put figures drawn in plain studio light into the set's light: ambient tint and a coloured rim."""
    if info.ambient is not None:
        color, amount = info.ambient
        painting.fill(figures, color, amount, "multiply")
    if info.rim is not None:
        color, amount, side = info.rim
        width = painting.shape[0] * RIM_WIDTH
        # Even in cel style the rim fades into the form a little; a hard band of even width reads as an outline.
        band = sh.rim(figures, (side, -0.3), width, softness=width * (RIM_SOFT_ANIME if style.name == "anime" else RIM_SOFT))
        painting.fill(band, color, amount, "screen")


def _soft(style, height):
    return 0.0 if style.name == "anime" else height * 0.006


def beach(painting, style, horizon=0.44, seed=3):
    """Midday sea and sand: blue sky with crisp clouds, a headland, glinting water, a foam line."""
    height, width = painting.shape
    y = horizon * height
    backdrop.gradient(painting, "#4ea6e0", "#d7eef7", end=(0, y))
    cloud = scenery.clouds(painting.shape, coverage=0.30, scale=1.2, seed=seed, softness=0.02 if style.name == "anime" else 0.08,
                           band=(0, y * 0.95))
    painting.fill(cloud, "#ffffff", 0.9)
    painting.fill(cloud * sh.linear_ramp(painting.shape, (0, 0), (0, y)), "#b9d3e8", 0.35)
    land = painting.mask(scenery.ridge(painting.shape, y - height * 0.025, height * 0.03, seed=seed + 1, tilt=-height * 0.05)) \
        * (sh.linear_ramp(painting.shape, (width * 0.45, 0), (0, 0)))
    painting.fill(land, "#7f9fb3", 0.8)
    sea_bottom = y + height * 0.14
    rows = np.arange(height, dtype=np.float32)[:, None]
    sea = ((rows >= y) & (rows < sea_bottom)).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    ramp = sh.linear_ramp(painting.shape, (0, y), (0, sea_bottom))[..., None]
    painting.color[:] = painting.color * (1 - sea[..., None]) + (rgb("#1d6f9f") * (1 - ramp) + rgb("#3cb6c2") * ramp) * sea[..., None]
    rng = np.random.default_rng(seed)
    for _ in range(140):                                          # glints on the water, thinner far away
        gy = rng.uniform(y + 2, sea_bottom - 4)
        near = (gy - y) / (sea_bottom - y)
        gx, length = rng.uniform(0, width), width * (0.004 + 0.02 * near) * rng.uniform(0.5, 1.5)
        painting.stroke(np.array([(gx, gy), (gx + length, gy)]), 0.8 + 2.2 * near, "#ffffff", taper=(0.4, 0.4),
                        opacity=rng.uniform(0.35, 0.8), layer="color")
    shore = np.stack([np.linspace(-5, width + 5, 200), sea_bottom + scenery.noise_line(200, 0.6, seed=seed) * height * 0.012], axis=1)
    sand = painting.mask(np.vstack([shore, [[width + 5, height + 5], [-5, height + 5]]]))
    painting.fill(sand, "#ead4a4")
    painting.fill(sand * sh.linear_ramp(painting.shape, (0, sea_bottom), (0, height)), "#d9b981", 0.6)
    backdrop.mottle(painting, "#c9a36e", amount=0.18, scale=2.0, seed=seed)
    wet = painting.mask(np.vstack([shore, (shore + [0, height * 0.035])[::-1]]))
    painting.fill(wet, "#b99a72", 0.55)
    painting.stroke(shore, height * 0.006, "#ffffff", taper=(0.0, 0.0), opacity=0.9, layer="color")
    painting.stroke(shore + [0, height * 0.012], height * 0.003, "#ffffff", taper=(0.2, 0.2), opacity=0.6, layer="color")
    return SetInfo(horizon=y, ground="#b48d5c", grade=dict(saturation=1.05, highlights=("#fff4dc", 0.05)))


def bedroom(painting, style, floor=0.80, seed=4):
    """Warm evening bedroom: plaster wall, a slanted patch of window light, a curtain, a wooden floor."""
    height, width = painting.shape
    y = floor * height
    backdrop.gradient(painting, "#e8d5c2", "#c7a993", end=(width * 0.3, y))
    backdrop.mottle(painting, "#b8957c", amount=0.22, scale=1.0, seed=seed)
    backdrop.window_light(painting, (width * 0.08, height * 0.10), (width * 0.30, height * 0.38), slant=0.30,
                          color="#ffd9a0", opacity=0.32, softness=_soft(style, height))
    backdrop.glow(painting, (width * 0.92, height * 0.40), height * 0.45, "#ffcf8a", opacity=0.35)
    drape = geo.smooth([(width * 0.84, -10), (width + 10, -10), (width + 10, y), (width * 0.87, y), (width * 0.86, height * 0.5)],
                       closed=True, corners=(0, 1, 2, 3))
    cloth = painting.mask(drape)
    painting.fill(cloth, "#8a4a4e")
    for x in np.linspace(width * 0.865, width * 0.99, 5):         # folds: dark wedge with a lit edge beside it
        fold = painting.mask(geo.lock((x - 8, -10), (x + 8, -10), (x, y), belly=0.8))
        painting.fill(fold * cloth, "#5c2c33", 0.7)
        painting.fill(sh.shift(fold, -14, 0) * cloth, "#b06a68", 0.35)
    rows = np.arange(height, dtype=np.float32)[:, None]
    ground = (rows >= y).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(ground, "#7a5640")
    for k, x in enumerate(np.linspace(-width * 0.6, width * 1.6, 14)):    # planks run toward the viewer
        painting.stroke(np.array([(width / 2 + (x - width / 2) * 0.25, y), (x, height)]), 1.5, "#5c3e2c", taper=(0.0, 0.0),
                        opacity=0.6, layer="color", clip=ground)
    painting.fill(ground * sh.linear_ramp(painting.shape, (0, y), (0, height)), "#3e2a20", 0.35)
    painting.fill(((rows >= y - height * 0.025) & (rows < y)).astype(np.float32) * np.ones((1, width)), "#efe6dc")   # skirting
    return SetInfo(horizon=y, ground="#4a3226", grade=dict(saturation=1.04, shadows=("#3a2440", 0.10), highlights=("#ffe2b8", 0.08)),
                   ambient=("#f3d6bf", 0.25), rim=("#ffd08a", 0.45, 1.0))


def office(painting, style, floor=0.80, seed=5):
    """Daytime office: a glass wall onto a city skyline, mullions, a plant, grey carpet."""
    height, width = painting.shape
    y = floor * height
    backdrop.gradient(painting, "#9fc1df", "#e4edf5", end=(0, y))
    far = painting.mask(scenery.skyline(painting.shape, y * 0.92, heights=(height * 0.10, height * 0.38),
                                        widths=(width * 0.05, width * 0.12), seed=seed))
    painting.fill(far, "#8ea3bb", 0.85)
    near = painting.mask(scenery.skyline(painting.shape, y * 0.98, heights=(height * 0.05, height * 0.22),
                                         widths=(width * 0.07, width * 0.16), seed=seed + 1))
    painting.fill(near, "#6f86a1", 0.9)
    stripes = (np.sin(np.arange(width) / max(width * 0.006, 1.0)) > 0.6).astype(np.float32)[None, :] * np.ones((height, 1))
    painting.fill(np.maximum(far, near) * stripes, "#c9d8e6", 0.25)
    frame_color = "#3b414b"
    for x in np.linspace(0, width, 6):                            # the glass wall's mullions and rail
        painting.fill(painting.mask([(x - width * 0.006, 0), (x + width * 0.006, 0), (x + width * 0.006, y), (x - width * 0.006, y)]),
                      frame_color)
    painting.fill(painting.mask([(0, y - height * 0.33), (width, y - height * 0.33), (width, y - height * 0.32), (0, y - height * 0.32)]),
                  frame_color, 0.8)
    rows = np.arange(height, dtype=np.float32)[:, None]
    ground = (rows >= y).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(ground, "#5f6670")
    painting.fill(ground * sh.linear_ramp(painting.shape, (0, y), (0, height)), "#3a3f47", 0.4)
    backdrop.mottle(painting, "#4b525c", amount=0.12, scale=3.0, seed=seed)
    pot = [(width * 0.86, y - height * 0.12), (width * 0.95, y - height * 0.12), (width * 0.94, y + height * 0.02),
           (width * 0.87, y + height * 0.02)]
    leaves, clumps = scenery.foliage(painting, (width * 0.905, y - height * 0.26), width * 0.16, height * 0.30, count=18, seed=seed)
    for index, clump in enumerate(clumps):
        painting.fill(clump, mix("#2f6b45", "#5aa36a", index / len(clumps)))
    if style.line_width > 0:
        painting.outline_mask(leaves, 2.0 * style.line_width, line_color(style, rgb("#2f6b45")))
    painting.fill(painting.mask(pot), "#e9e4dc")
    painting.fill(painting.mask(pot) * sh.linear_ramp(painting.shape, (width * 0.86, 0), (width * 0.95, 0)), "#b8b2a8", 0.6)
    return SetInfo(horizon=y, ground="#30353c", grade=dict(saturation=0.98, highlights=("#f2f7ff", 0.06)))


def night_street(painting, style, horizon=0.62, seed=6):
    """City at night: dark sky, blocks with lit windows, street lamps, glowing shop fronts, a wet road."""
    height, width = painting.shape
    y = horizon * height
    backdrop.gradient(painting, "#0a0f24", "#3b2c5c", end=(0, y))
    rng = np.random.default_rng(seed)
    for base, tone, heights in ((y * 0.95, "#232846", (0.18, 0.45)), (y, "#161a30", (0.10, 0.32))):
        block = painting.mask(scenery.skyline(painting.shape, base, heights=(height * heights[0], height * heights[1]),
                                              widths=(width * 0.06, width * 0.14), seed=int(rng.integers(100))))
        painting.fill(block, tone)
        lit = np.zeros(painting.shape, dtype=np.float32)
        for _ in range(260):
            wx, wy = rng.uniform(0, width), rng.uniform(base - height * 0.45, base - height * 0.02)
            cell = painting.mask([(wx, wy), (wx + width * 0.008, wy), (wx + width * 0.008, wy + height * 0.012), (wx, wy + height * 0.012)])
            lit = np.maximum(lit, cell * block * (rng.random() < 0.45))
        painting.fill(lit, "#ffd38a", 0.85)
        painting.fill(sh.blur(lit, height * 0.004), "#ffb060", 0.4, "screen")
    shops = np.zeros(painting.shape, dtype=np.float32)
    for x0 in rng.uniform(0, width, 5):
        shops = np.maximum(shops, painting.mask([(x0, y - height * 0.07), (x0 + width * 0.09, y - height * 0.07),
                                                 (x0 + width * 0.09, y), (x0, y)]))
    painting.fill(shops, "#ff9f6e", 0.7)
    painting.fill(sh.blur(shops, height * 0.03), "#ff7a8a", 0.35, "screen")
    rows = np.arange(height, dtype=np.float32)[:, None]
    road = (rows >= y).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(road, "#1a1c2b")
    lamps = [width * f for f in (0.12, 0.47, 0.83)]
    for x in lamps:
        top = y - height * 0.40
        painting.stroke(np.array([(x, y), (x, top)]), height * 0.006, "#11131f", taper=(0.0, 0.0), layer="color")
        backdrop.glow(painting, (x, top), height * 0.22, "#ffcf8a", opacity=0.55)
        painting.fill(painting.mask(geo.ellipse((x, top), height * 0.010, height * 0.007)), "#fff4d6")
        streak = painting.mask([(x - width * 0.012, y), (x + width * 0.012, y), (x + width * 0.03, height), (x - width * 0.03, height)])
        painting.fill(sh.blur(streak, height * 0.01) * road, "#ffc27a", 0.30, "screen")          # reflection on the wet road
    backdrop.bokeh(painting, ["#ffcf8a", "#ff8fa3", "#8fd0ff"], count=26, radius=(0.01, 0.035), opacity=0.35, seed=seed)
    painting.fill(road * sh.linear_ramp(painting.shape, (0, y), (0, height)), "#07080f", 0.35)
    return SetInfo(horizon=y, ground="#05060c",
                   grade=dict(contrast=1.05, saturation=1.08, shadows=("#1a1440", 0.18), highlights=("#ffd9a8", 0.08)),
                   ambient=("#8c86b8", 0.45), rim=("#ffc27a", 0.45, 1.0))


def cafe(painting, style, floor=0.80, seed=7):
    """Afternoon cafe: cream wall over a wooden wainscot, a big window onto a bright street, pendant lamps, tiled floor."""
    height, width = painting.shape
    y = floor * height
    rows = np.arange(height, dtype=np.float32)[:, None]
    backdrop.gradient(painting, "#efe2cc", "#d9c3a4", end=(0, y))
    backdrop.mottle(painting, "#c8ad8a", amount=0.14, scale=1.2, seed=seed)
    # window onto the street: bright, slightly blown out, crossed by its frame
    x0, x1, top, sill = width * 0.06, width * 0.46, height * 0.12, y - height * 0.30
    glass = painting.mask([(x0, top), (x1, top), (x1, sill), (x0, sill)])
    backdrop.gradient(painting, "#cfe6f2", "#fbf3df", start=(0, top), end=(0, sill))   # the wall is painted over it below
    street = painting.mask(scenery.skyline(painting.shape, sill, heights=(height * 0.06, height * 0.20),
                                           widths=(width * 0.04, width * 0.09), seed=seed))
    painting.fill(street * glass, "#e6d8c6", 0.8)
    wall = (1.0 - glass) * (rows < y)
    painting.fill(wall, "#ead9bf")
    painting.fill(wall * sh.linear_ramp(painting.shape, (width, 0), (0, 0)), "#cdb08c", 0.35)
    backdrop.mottle(painting, "#c4a682", amount=0.10, scale=1.4, seed=seed + 1)
    frame_color = "#5a4030"
    for x in (x0, (x0 + x1) / 2, x1):
        painting.fill(painting.mask([(x - width * 0.006, top), (x + width * 0.006, top), (x + width * 0.006, sill),
                                     (x - width * 0.006, sill)]), frame_color)
    for yy in (top, sill):
        painting.fill(painting.mask([(x0 - width * 0.01, yy - height * 0.006), (x1 + width * 0.01, yy - height * 0.006),
                                     (x1 + width * 0.01, yy + height * 0.008), (x0 - width * 0.01, yy + height * 0.008)]), frame_color)
    backdrop.glow(painting, ((x0 + x1) / 2, (top + sill) / 2), height * 0.55, "#fff1d0", opacity=0.30)
    # wooden wainscot along the lower wall
    panel_top = y - height * 0.22
    panel = ((rows >= panel_top) & (rows < y)).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(panel, "#8a5e3e")
    for x in np.arange(0, width, width * 0.07):
        painting.fill(painting.mask([(x, panel_top + height * 0.02), (x + width * 0.055, panel_top + height * 0.02),
                                     (x + width * 0.055, y - height * 0.015), (x, y - height * 0.015)]), "#7a5034", 0.8)
    painting.fill(((rows >= panel_top - height * 0.008) & (rows < panel_top + height * 0.004)).astype(np.float32)
                  * np.ones((1, width)), "#5e3e2a")
    # pendant lamps hanging from the ceiling, each throwing a warm pool
    for x in (width * 0.62, width * 0.86):
        drop = height * 0.20
        painting.stroke(np.array([(x, -5), (x, drop)]), max(height * 0.002, 1.0), "#3a2a22", taper=(0.0, 0.0), layer="color")
        shade = [(x - width * 0.035, drop + height * 0.05), (x - width * 0.012, drop), (x + width * 0.012, drop),
                 (x + width * 0.035, drop + height * 0.05)]
        painting.fill(painting.mask(shade), "#2f3a36")
        painting.fill(painting.mask(geo.ellipse((x, drop + height * 0.052), width * 0.03, height * 0.008)), "#fff2c8")
        backdrop.glow(painting, (x, drop + height * 0.06), height * 0.30, "#ffcf8a", opacity=0.35)
    # tiled floor
    ground = (rows >= y).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(ground, "#b9a48a")
    for k, x in enumerate(np.linspace(-width * 0.6, width * 1.6, 16)):
        painting.stroke(np.array([(width / 2 + (x - width / 2) * 0.3, y), (x, height)]), 1.2, "#8e7a62", taper=(0.0, 0.0),
                        opacity=0.6, layer="color", clip=ground)
    for t in np.linspace(0.0, 1.0, 6) ** 1.8:
        yy = y + t * (height - y)
        painting.stroke(np.array([(0, yy), (width, yy)]), 1.2, "#8e7a62", taper=(0.0, 0.0), opacity=0.5, layer="color")
    painting.fill(ground * sh.linear_ramp(painting.shape, (0, y), (0, height)), "#5e4a38", 0.30)
    return SetInfo(horizon=y, ground="#5a4634", grade=dict(saturation=1.03, highlights=("#fff0d4", 0.07), shadows=("#3a2a2a", 0.06)),
                   ambient=("#f6e3c8", 0.18), rim=("#fff0cc", 0.40, -1.0))


def park(painting, style, horizon=0.62, seed=8):
    """Sunny park: blue sky with soft clouds, rows of trees, a lawn and a pale path winding toward the viewer."""
    height, width = painting.shape
    y = horizon * height
    rows = np.arange(height, dtype=np.float32)[:, None]
    backdrop.gradient(painting, "#5ea7df", "#d6ecf6", end=(0, y))
    cloud = scenery.clouds(painting.shape, coverage=0.28, scale=1.1, seed=seed, softness=0.02 if style.name == "anime" else 0.08,
                           band=(0, y * 0.8))
    painting.fill(cloud, "#ffffff", 0.85)
    rng = np.random.default_rng(seed)
    for depth, (tone, light) in enumerate((("#6f9a7a", "#8fb894"), ("#4f7f55", "#76a86a"))):
        base = y + height * (0.00 if depth == 0 else 0.03)
        count = 9 if depth == 0 else 6
        for x in np.linspace(-width * 0.05, width * 1.05, count) + rng.uniform(-width * 0.04, width * 0.04, count):
            size = height * (0.16 if depth == 0 else 0.26) * rng.uniform(0.8, 1.2)
            trunk = [(x - size * 0.05, base - size * 0.6), (x + size * 0.05, base - size * 0.6), (x + size * 0.06, base), (x - size * 0.06, base)]
            painting.fill(painting.mask(trunk), "#5b4636" if depth else "#7d7568")
            crown, clumps = scenery.foliage(painting, (x, base - size * 0.95), size * 1.1, size * 0.9, count=12, seed=int(rng.integers(1000)))
            painting.fill(crown, tone)
            for index, clump in enumerate(clumps):
                painting.fill(sh.shift(clump, -size * 0.04, -size * 0.04) * clump, light, 0.5 * index / len(clumps))
            if style.line_width > 0 and depth:
                painting.outline_mask(crown, 1.6 * style.line_width, line_color(style, rgb(tone)))
    lawn = (rows >= y).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(lawn, "#7cb35c")
    painting.fill(lawn * sh.linear_ramp(painting.shape, (0, y), (0, height)), "#4f8a3e", 0.45)
    backdrop.mottle(painting, "#5f9a48", amount=0.16, scale=2.4, seed=seed + 1)
    path = geo.smooth([(width * 0.47, y), (width * 0.53, y), (width * 0.66, y + (height - y) * 0.45), (width * 0.72, height + 5),
                       (width * 0.34, height + 5), (width * 0.44, y + (height - y) * 0.45)], closed=True, corners=(0, 1, 3, 4))
    walk = painting.mask(path) * lawn
    painting.fill(walk, "#e2d4b4")
    painting.fill(walk * sh.linear_ramp(painting.shape, (0, y), (0, height)), "#cbb994", 0.5)
    for root, tip, bend in scenery.blades((0, y + (height - y) * 0.3, width, height), 260, height * 0.025, seed=seed + 2):
        painting.stroke(geo.bent_line(root, tip, bend), max(height * 0.0015, 1.0), "#4f8a3e", taper=(0.0, 0.9),
                        opacity=0.55, layer="color", clip=lawn * (1.0 - walk))
    backdrop.glow(painting, (width * 0.15, -height * 0.05), height * 0.8, "#fff3d6", opacity=0.25)
    return SetInfo(horizon=y, ground="#3f6e32", grade=dict(saturation=1.06, highlights=("#fff6e0", 0.05)),
                   rim=("#fff4dc", 0.35, -1.0))


def panel_block(painting, style, horizon=0.74, seed=9, lamp=0.82, lit=0.22):
    """Doomer courtyard at dusk: overcast sky, prefabricated apartment blocks with a few lit windows,
    bare trees, a sodium street lamp and trampled snow. Finish the picture with fx.doomer.

    lamp: x of the street lamp as a share of the width; the figures take their warm rim from that side.
    lit: share of windows with the light on.
    Snow falling in front of the figures is added after them with scenery.snowfall.
    """
    height, width = painting.shape
    y = horizon * height
    rng = np.random.default_rng(seed)
    backdrop.gradient(painting, "#56656d", "#c3cac6", end=(0, y))
    cloud = scenery.clouds(painting.shape, coverage=0.45, scale=0.9, seed=seed, softness=0.03 if style.name == "anime" else 0.12,
                           band=(0, y * 0.9))
    painting.fill(cloud, "#7d8b91", 0.35)
    far = painting.mask(scenery.skyline(painting.shape, y - height * 0.02, heights=(height * 0.10, height * 0.22),
                                        widths=(width * 0.08, width * 0.16), seed=seed + 1))
    painting.fill(far, "#7f8b8e")
    line = 1.2 * style.line_width * height / 1000.0
    # A long block receding to the right, its end wall facing left, and a lower block across the yard.
    near = [(-0.06 * width, 0.06 * height), (0.60 * width, 0.27 * height), (0.60 * width, y), (-0.06 * width, y + 0.02 * height)]
    end = [(0.60 * width, 0.27 * height), (0.70 * width, 0.25 * height), (0.70 * width, y - 0.004 * height), (0.60 * width, y)]
    back = [(0.66 * width, 0.40 * height), (1.06 * width, 0.36 * height), (1.06 * width, y - 0.01 * height), (0.66 * width, y - 0.006 * height)]
    windows = scenery.panel_facade(painting, back, 7, 12, seed=seed + 2, lit=lit, wall="#8f938e", shade=0.25, line_width=line)
    windows = np.maximum(windows, scenery.panel_facade(painting, end, 12, 3, seed=seed + 3, lit=lit * 0.5, shade=0.55,
                                                      line_width=line))
    windows = np.maximum(windows, scenery.panel_facade(painting, near, 12, 22, seed=seed + 4, lit=lit, balcony_every=4,
                                                      stairs_every=7, line_width=line))
    painting.fill(sh.blur(windows, height * 0.004), "#ffb060", 0.35, "screen")
    rows = np.arange(height, dtype=np.float32)[:, None]
    ground = (rows >= y).astype(np.float32) * np.ones((1, width), dtype=np.float32)
    painting.fill(ground, "#c9cfcb")
    painting.fill(ground * sh.smoothstep(0.55, 0.75, fx.fbm(painting.shape, scale=2.0, seed=seed + 5, stretch=(1.0, 4.0))),
                  "#9aa19f", 0.55)
    track = painting.mask(geo.smooth([(0.30 * width, y), (0.42 * width, y), (0.75 * width, height + 5), (0.40 * width, height + 5)],
                                     closed=True, corners=(0, 1, 2, 3)))
    painting.fill(track * ground, "#7f8784", 0.55)                       # the trampled path is grey slush
    bank = ground * (1.0 - sh.smoothstep(y, y + height * 0.03, rows))      # dirty snow heaped against the blocks
    painting.fill(bank, "#8e9693", 0.5)
    painting.fill(ground * sh.linear_ramp(painting.shape, (0, y), (0, height)), "#56636a", 0.35)   # the near yard lies in dusk
    for x, size in ((0.10, 0.36), (0.46, 0.30), (0.93, 0.40)):
        scenery.bare_tree(painting, (x * width, y + height * 0.01), size * height, seed=int(rng.integers(1000)),
                          color="#2c2f33", birch=x < 0.2)
    painting.stroke(scenery.wire((-0.02 * width, 0.12 * height), (1.02 * width, 0.05 * height), height * 0.05), max(height * 0.0018, 1.0),
                    "#24282b", taper=(0.0, 0.0), layer="color")
    side = 1.0 if lamp >= 0.5 else -1.0
    scenery.sodium_lamp(painting, (lamp * width, y + height * 0.06), height * 0.42, side=-side, ground=ground)
    return SetInfo(horizon=y, ground="#5c666b", grade={}, ambient=("#a8b4ba", 0.30), rim=(scenery.SODIUM, 0.55, side))


SETS = {"beach": beach, "bedroom": bedroom, "office": office, "night_street": night_street, "cafe": cafe, "park": park,
        "panel_block": panel_block}
