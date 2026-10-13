"""Example: a lake at dusk built only from engine primitives (no figure rig).

Usage: python examples/landscape.py --style painterly|anime|illust --out landscape.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, fx, geometry as geo, scenery, shading as sh
from codepainter.color import mix, shadow_of
from codepainter.styles import finish, get_style, line_color

WIDTH, HEIGHT = 1280, 896
HORIZON = int(HEIGHT * 0.60)
SKY_TOP, SKY_MID, SKY_LOW = "#22305e", "#c4677a", "#ffc37a"
SUN = (WIDTH * 0.68, HORIZON - HEIGHT * 0.06)   # just set behind the ranges: only its glow shows
LIGHT = (0.45, -0.55, 0.5)          # low sun from the right
RANGES = [                          # far to near: (skyline y, relief, colour, seed)
    (HORIZON - 105, 90, "#8a79a6", 1),
    (HORIZON - 55, 60, "#5d5a8c", 2),
    (HORIZON - 14, 34, "#38406e", 3),
]
SHORE, PINE = "#1d2440", "#141a30"


def paint_sky(painting, style):
    backdrop.gradient(painting, SKY_TOP, SKY_MID, end=(0, HORIZON * 0.72))
    low = sh.linear_ramp(painting.shape, (0, HORIZON * 0.55), (0, HORIZON))
    painting.fill(low, SKY_LOW)
    backdrop.glow(painting, SUN, HEIGHT * 0.55, "#ffd9a0", opacity=0.75)
    softness = 0.012 if style.name == "anime" else 0.07
    cloud = scenery.clouds(painting.shape, coverage=0.36, scale=1.1, seed=11, softness=softness,
                           band=(HEIGHT * 0.02, HORIZON * 0.86))
    painting.fill(cloud, "#6b5a8e", 0.9)
    # Dusk clouds are lit from below: the cloud mask slid upward leaves only the under-edges.
    underside = np.clip(cloud - sh.shift(cloud, 0, -14), 0.0, 1.0)
    painting.fill(sh.blur(underside, 2.0 if style.name == "anime" else 5.0), "#ffb07a", 0.95)


def paint_mountains(painting, style):
    for index, (skyline, relief, color, seed) in enumerate(RANGES):
        outline = scenery.ridge(painting.shape, skyline, relief, roughness=0.55, seed=seed)
        mask = painting.mask(outline)
        painting.part(mask, color)
        # Craggy slopes: stretched noise stands in for the facets turned away from the sun.
        crags = scenery.clouds(painting.shape, coverage=0.45, scale=2.6, seed=seed + 30, stretch=(1.6, 1.0),
                               softness=style.edge_softness + 0.01)
        painting.fill(crags * mask, shadow_of(color, style.shadow_tint), 0.8)
        # Haze gathers at the foot of each range and separates it from the next one.
        haze = sh.linear_ramp(painting.shape, (0, skyline - relief), (0, HORIZON)) * mask
        painting.fill(haze, SKY_LOW, 0.30 - 0.07 * index)
        painting.fill(sh.rim(mask, (0.5, -1.0), 3.0, 0.8), "#ffc99a", 0.7)
        if style.line_width > 0:
            painting.outline(outline, 2.0 * style.line_width, line_color(style, color), closed=False)


def paint_lake(painting):
    scenery.reflect(painting, HORIZON, HEIGHT - HORIZON, ripple=7.0, darken=0.18, tint="#1a2748", seed=5)
    rng = np.random.default_rng(8)
    for _ in range(70):                       # broken glints of the sun on the water
        y = rng.uniform(HORIZON + 6, HEIGHT * 0.93)
        spread = 30 + (y - HORIZON) * 0.55
        x = SUN[0] + rng.normal(0, spread)
        length = rng.uniform(14, 60) * (0.5 + (y - HORIZON) / (HEIGHT - HORIZON))
        glint = geo.needle((x - length / 2, y), (x + length / 2, y), rng.uniform(2.0, 4.5))
        painting.fill(painting.mask(glint), "#ffe2b0", rng.uniform(0.45, 0.9))


def paint_foreground(painting, style):
    shore = scenery.ridge(painting.shape, HEIGHT * 0.90, 26, roughness=0.5, seed=21, tilt=-70)
    mask = painting.mask(shore)
    painting.part(mask, SHORE)
    ink = line_color(style, PINE)
    for index, (x, size) in enumerate(((95, 470), (215, 360), (320, 250), (1180, 300))):
        base = (x, HEIGHT * 0.90 + 70 * x / WIDTH + 10)      # stand on the sloping shore
        for tier in scenery.conifer(base, size, size * 0.42, tiers=6, seed=index):
            tier_mask = painting.mask(tier)
            painting.part(tier_mask, PINE)
            painting.fill(sh.rim(tier_mask, (0.8, -0.5), 5.0, 1.0), "#c9788a", 0.55)   # last sunlight on the boughs
            if style.line_width > 0:
                painting.outline(tier, 1.6 * style.line_width, ink)
    for root, tip, bend in scenery.blades((0, HEIGHT * 0.90, WIDTH, HEIGHT), 420, 46, seed=4):
        painting.stroke(geo.bent_line(root, tip, bend), 3.2, mix(SHORE, "#3a3358", 0.5), taper=(0.0, 0.9), layer="color")


def render(style_name, seed=0):
    style = get_style(style_name)
    painting = Painting(WIDTH, HEIGHT)
    paint_sky(painting, style)
    painting.snapshot("1 sky")
    paint_mountains(painting, style)
    painting.snapshot("2 mountains")
    paint_lake(painting)
    painting.snapshot("3 lake")
    paint_foreground(painting, style)
    painting.snapshot("4 foreground")
    image = finish(painting, style, seed=seed)
    painting.stages["5 finish"] = image
    return painting, image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="painterly", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="landscape.png")
    parser.add_argument("--sheet", default=None)
    args = parser.parse_args()
    painting, image = render(args.style)
    painting.save(args.out, image)
    if args.sheet:
        fx.stage_sheet(painting.stages, args.sheet, columns=5)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
