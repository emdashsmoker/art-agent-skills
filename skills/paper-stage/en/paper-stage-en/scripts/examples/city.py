"""Example: a city street at dusk in one-point perspective.

Shows how depth is built without 3D: every wall is a four-cornered shape whose far
edge is pulled toward one vanishing point, and windows are laid on it through a
perspective mapping so they shrink with distance.

Usage: python examples/city.py --style anime|illust|painterly --out city.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, fx, geometry as geo, scenery, shading as sh
from codepainter.color import mix, shadow_of
from codepainter.styles import finish, get_style, line_color

WIDTH, HEIGHT = 1280, 896
VANISH = (WIDTH * 0.54, HEIGHT * 0.60)
SKY_TOP, SKY_MID, SKY_LOW = "#1c2552", "#7a4f8a", "#ff9e6b"
LIT = ["#ffd98a", "#ffc46a", "#fff0c0", "#ffb070"]
# (near, far, height, wall colour) per building, listed from the viewer into the distance
LEFT_BLOCK = [(0.00, 0.30, 900, "#4a4f78"), (0.30, 0.48, 1150, "#5b4a70"), (0.48, 0.62, 800, "#3f5a80"),
              (0.62, 0.74, 1300, "#4f4470"), (0.74, 0.86, 900, "#3a4a70")]
RIGHT_BLOCK = [(0.00, 0.26, 1050, "#6a4a66"), (0.26, 0.44, 780, "#46507c"), (0.44, 0.60, 1250, "#5a4672"),
               (0.60, 0.73, 860, "#3d5682"), (0.73, 0.86, 1100, "#4b4672")]
LEFT_BASE, RIGHT_BASE = (-260, HEIGHT + 60), (WIDTH + 300, HEIGHT + 60)
ROAD_REACH = 0.93            # share of the way to the vanishing point covered by road markings


def paint_sky(painting, style):
    backdrop.gradient(painting, SKY_TOP, SKY_MID, end=(0, VANISH[1] * 0.8))
    painting.fill(sh.linear_ramp(painting.shape, (0, VANISH[1] * 0.5), (0, VANISH[1])), SKY_LOW)
    backdrop.glow(painting, VANISH, HEIGHT * 0.5, "#ffd0a0", opacity=0.6)
    cloud = scenery.clouds(painting.shape, coverage=0.3, scale=1.3, seed=8, softness=0.015 if style.name == "anime" else 0.07,
                           band=(0, VANISH[1] * 0.9))
    painting.fill(cloud, "#5a4a86", 0.85)
    painting.fill(sh.blur(np.clip(cloud - sh.shift(cloud, 0, -10), 0, 1), 2.5), "#ffa987", 0.9)
    far = painting.mask(scenery.skyline(painting.shape, VANISH[1] + 4, heights=(30, 150), widths=(18, 60), seed=3))
    painting.fill(far, "#3a3566")
    painting.fill(far * sh.linear_ramp(painting.shape, (0, VANISH[1] - 150), (0, VANISH[1])), "#a0607a", 0.55)   # haze at the foot
    rng = np.random.default_rng(4)
    for _ in range(140):                                                        # far windows are only dots
        x, y = rng.uniform(0, WIDTH), rng.uniform(VANISH[1] - 140, VANISH[1])
        painting.fill(painting.mask(geo.ellipse((x, y), 1.6, 1.6, count=8)) * far, LIT[rng.integers(len(LIT))], 0.9)


def paint_block(painting, style, block, base, seed):
    reflections = np.zeros(painting.shape, dtype=np.float32)
    for index, (near, far, height, color) in reversed(list(enumerate(block))):   # far buildings first
        quad = scenery.street_wall(base, VANISH, near, far, height)
        wall = painting.mask(quad)
        painting.part(wall, color)
        # the wall darkens toward the viewer, where less of the sky glow reaches it
        toward_viewer = sh.linear_ramp(painting.shape, (VANISH[0], 0), (base[0], 0))
        painting.fill(wall * toward_viewer, shadow_of(color, style.shadow_tint), 0.7)
        painting.fill(wall * sh.linear_ramp(painting.shape, (0, VANISH[1] - 60), (0, VANISH[1] + 120)), "#ff9e6b", 0.18)
        depth = 1.0 - (near + far) / 2
        columns = max(int(round((far - near) * 22)), 2)
        rows = max(int(round(height / 115)), 3)
        scenery.windows(painting, quad, columns, rows, LIT, lit=0.42, seed=seed + index, inset=(0.05, 0.04, 0.95, 0.80))
        shop = scenery.windows(painting, quad, max(columns // 2, 1), 1, LIT, lit=0.9, margin=0.10, seed=seed + 50 + index,
                               inset=(0.04, 0.84, 0.96, 0.975))
        reflections = np.maximum(reflections, shop)
        mapping = geo.quad_map(quad)
        cornice = mapping([(0, 0), (1, 0), (1, 0.022), (0, 0.022)])
        painting.fill(painting.mask(cornice), mix(color, "#ffd0b0", 0.35))
        if style.line_width > 0:
            painting.outline(quad, (1.2 + 2.2 * depth) * style.line_width, line_color(style, color))
    return reflections


def paint_street(painting, style, shop_light):
    road = np.array([(VANISH[0] - 6, VANISH[1]), (VANISH[0] + 6, VANISH[1]), (WIDTH * 1.02, HEIGHT + 4), (-WIDTH * 0.02, HEIGHT + 4)])
    mask = painting.mask(road)
    painting.part(mask, "#2a2c44")
    painting.fill(mask * (1 - sh.linear_ramp(painting.shape, (0, VANISH[1]), (0, VANISH[1] + 200))), "#ff9e6b", 0.35)
    # Map only the nearer stretch of road: a quad that closes to a point has no usable far edge.
    far_left, far_right = geo.lerp(road[3], road[0], ROAD_REACH), geo.lerp(road[2], road[1], ROAD_REACH)
    mapping = geo.quad_map([far_left, far_right, road[2], road[3]])
    for cell in geo.grid_cells(1, 14, margin=0.0, inset=(0.492, 0.0, 0.508, 1.0)):    # dashed centre line
        dash = cell.copy(); dash[2:, 1] -= (cell[2, 1] - cell[0, 1]) * 0.45
        painting.fill(painting.mask(mapping(dash)), "#e8e2c8", 0.8)
    for side in (0.16, 0.84):                                                       # kerbs
        kerb = mapping([(side - 0.012, 0.0), (side + 0.012, 0.0), (side + 0.012, 1.0), (side - 0.012, 1.0)])
        painting.fill(painting.mask(kerb), "#6a6a86", 0.9)
    # wet road: shop lights smear straight down into it
    streaks = sh.blur(sh.shift(shop_light, 0, 46), 1.0)
    for step in (90, 150, 220):
        streaks = np.maximum(streaks, sh.shift(shop_light, 0, step) * 0.6)
    streaks = ndi.gaussian_filter(streaks, (38, 1.5))          # blurred along the fall only
    painting.fill(streaks * mask, "#ffcf80", 0.55)


def paint_lamps(painting, style):
    for side_base, sign in ((LEFT_BASE, 1.0), (RIGHT_BASE, -1.0)):
        base = np.array(side_base) + [sign * 330, 0]
        for position in (0.20, 0.45, 0.62, 0.75, 0.84):
            scale = 1.0 - position
            foot = base + (np.array(VANISH) - base) * position
            top = foot - [0, 420 * scale]
            arm = top + [sign * 46 * scale, 6 * scale]
            painting.stroke(np.array([foot, top]), max(7 * scale, 1.2), "#161a2c", taper=(0, 0), layer="color")
            painting.stroke(geo.bent_line(top, arm, -0.3 * sign), max(5 * scale, 1.0), "#161a2c", taper=(0, 0.2), layer="color")
            backdrop.glow(painting, arm, 150 * scale, "#ffe2a0", opacity=0.75)
            painting.fill(painting.mask(geo.ellipse(arm, 9 * scale + 1, 7 * scale + 1)), "#fff6d8")


def render(style_name, seed=0):
    style = get_style(style_name)
    painting = Painting(WIDTH, HEIGHT)
    paint_sky(painting, style)
    painting.snapshot("1 sky and far city")
    shops = np.maximum(paint_block(painting, style, LEFT_BLOCK, LEFT_BASE, 10),
                       paint_block(painting, style, RIGHT_BLOCK, RIGHT_BASE, 30))
    painting.snapshot("2 buildings")
    paint_street(painting, style, shops)
    painting.snapshot("3 street")
    paint_lamps(painting, style)
    painting.snapshot("4 lamps")
    image = finish(painting, style, seed=seed)
    painting.stages["5 finish"] = image
    return painting, image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="anime", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="city.png")
    parser.add_argument("--sheet", default=None)
    args = parser.parse_args()
    painting, image = render(args.style)
    painting.save(args.out, image)
    if args.sheet:
        fx.stage_sheet(painting.stages, args.sheet, columns=5)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
