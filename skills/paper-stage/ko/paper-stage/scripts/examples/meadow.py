"""Example: a summer hillside with cumulus clouds, a path and a tree (daylight landscape).

Shows atmospheric perspective by colour alone: every hill farther away is lighter,
bluer and plainer, and detail is spent only on the nearest ground.

Usage: python examples/meadow.py --style anime|illust|painterly --out meadow.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, fx, geometry as geo, scenery, shading as sh
from codepainter.color import light_of, mix, shadow_of
from codepainter.styles import finish, get_style, line_color

WIDTH, HEIGHT = 1280, 896
HORIZON = int(HEIGHT * 0.52)
LIGHT = (-0.55, -0.65, 0.5)
SKY_TOP, SKY_LOW = "#2f79d0", "#bfe3f6"
HILLS = [                       # far to near: (skyline y, relief, colour, seed, tilt)
    (HORIZON - 20, 60, "#8fb4d6", 1, 0),
    (HORIZON + 30, 46, "#7fb08a", 2, 40),
    (HORIZON + 110, 40, "#62a04e", 3, -50),
    (HORIZON + 230, 34, "#4f9238", 4, 60),
]
GRASS_NEAR = "#3f8030"          # darkest blades; lighter ones are mixed toward yellow-green


def paint_sky(painting, style):
    backdrop.gradient(painting, SKY_TOP, SKY_LOW, end=(0, HORIZON))
    for center, width, height, seed in (((300, 250), 520, 210, 1), ((930, 190), 420, 170, 2), ((1180, 330), 300, 110, 3),
                                        ((620, 395), 260, 70, 4), ((90, 400), 240, 80, 5)):
        cloud, lumps = scenery.puffs(painting, center, width, height, count=11, seed=seed)
        painting.fill(cloud, "#ffffff")
        whole = sh.lighting(cloud, LIGHT, bevel=height * 0.45)       # the heap as one mass first
        painting.fill(sh.shadow_from_light(whole, 0.28, style.edge_softness + 0.10) * cloud, "#b9cfe8", 0.7)
        for lump in lumps[::2]:                                      # then a hint of the single lumps
            lit = sh.lighting(lump, LIGHT)
            painting.fill(sh.blur(sh.shadow_from_light(lit, 0.0, 0.15) * lump, 3.0) * cloud, "#b9cfe8", 0.35)
        base = cloud * sh.linear_ramp(painting.shape, (0, center[1] - height * 0.25), (0, center[1] + height * 0.12))
        painting.fill(base, "#9fb9dc", 0.6)                          # the flat base sits in the cloud's own shade
        painting.fill(sh.rim(cloud, (-0.6, -0.8), 5, 1.5), "#fffdf2", 0.9)


def paint_hills(painting, style):
    for index, (skyline, relief, color, seed, tilt) in enumerate(HILLS):
        outline = scenery.ridge(painting.shape, skyline, relief, roughness=0.32, seed=seed, tilt=tilt)
        mask = painting.mask(outline)
        painting.part(mask, color)
        painting.fill(mask * sh.linear_ramp(painting.shape, (0, skyline - relief), (0, skyline + 170)), shadow_of(color, (0.75, 0.85, 0.80)), 0.35)
        painting.fill(sh.rim(mask, (-0.3, -1.0), 10, 3), light_of(color, "#f4ffb0", 0.45), 0.7)   # sunlit crest
        if index > 0:
            rng = np.random.default_rng(seed)
            for x in rng.uniform(0, WIDTH, 5 + index * 3):           # bushes along each crest, smaller when farther
                size = 16 + index * 16
                bush, _ = scenery.puffs(painting, (x, skyline + rng.uniform(-10, 30)), size * 2.4, size, count=5, seed=int(x))
                painting.fill(bush * mask + bush * (1 - mask) * 0.9, shadow_of(color, (0.7, 0.85, 0.8)), 0.85)
        if style.line_width > 0 and index >= 2:
            painting.outline(outline, 1.6 * style.line_width, line_color(style, color), closed=False)


def paint_path(painting, style):
    course = geo.smooth([(690, HORIZON + 236), (650, HORIZON + 275), (735, HORIZON + 330), (560, HEIGHT + 60)])
    path = painting.mask(geo.tube(course, [4, 12, 38, 150], caps=(True, False), count=60))
    painting.fill(path, "#d9c08a")
    painting.fill(path * sh.linear_ramp(painting.shape, (0, HORIZON + 260), (0, HEIGHT)), "#b8975c", 0.5)
    painting.fill(sh.rim(path, (1.0, 0.2), 6, 2), "#8a6a3a", 0.6)
    return path


def paint_tree(painting, style, foot, size, seed):
    trunk = geo.tube(geo.smooth([foot, (foot[0] + size * 0.04, foot[1] - size * 0.45), (foot[0] - size * 0.03, foot[1] - size * 0.95)]),
                     [size * 0.085, size * 0.06, size * 0.035], caps=(False, True))
    shadow = sh.ground_shadow(painting.mask(geo.ellipse((foot[0], foot[1] - size * 0.2), size * 0.55, size * 0.2)), lean=0.7, squash=0.16, softness=5)
    painting.fill(shadow, "#1f4a2a", 0.5, "multiply")
    trunk_mask = painting.mask(trunk)
    painting.part(trunk_mask, "#6a4a30")
    painting.fill(sh.shadow_from_light(sh.lighting(trunk_mask, LIGHT), 0.2, style.edge_softness + 0.03) * trunk_mask, "#3f2a1c", 0.85)
    crown_center = (foot[0] - size * 0.02, foot[1] - size * 0.82)
    crown, clumps = scenery.foliage(painting, crown_center, size * 1.15, size * 0.80, count=18, seed=seed)
    leaf = "#3f8a34"
    painting.part(crown, leaf)
    for clump in clumps:                                             # every clump: lit crown, shaded belly
        lit = sh.lighting(clump, LIGHT)
        painting.fill(clump, leaf, 0.9)
        painting.fill(sh.shadow_from_light(lit, 0.22, style.edge_softness + 0.05) * clump, shadow_of(leaf, (0.55, 0.75, 0.8)), 0.75)
        painting.fill((1 - sh.shadow_from_light(lit, 0.62, style.edge_softness + 0.08)) * clump, light_of(leaf, "#e6ff8a", 0.5), 0.7)
    lit_all = sh.lighting(crown, LIGHT, bevel=size * 0.3)
    painting.fill(sh.shadow_from_light(lit_all, 0.15, 0.25) * crown, shadow_of(leaf, (0.5, 0.7, 0.8)), 0.45)
    if style.line_width > 0:
        ink = line_color(style, leaf)
        painting.outline_mask(crown, 2.6 * style.line_width, ink)
        painting.outline_mask(trunk_mask, 2.2 * style.line_width, line_color(style, "#6a4a30"), keep=1.0 - crown)


def paint_foreground(painting, style, path):
    off_path = 1.0 - path
    for root, tip, bend in scenery.blades((0, HEIGHT * 0.84, WIDTH, HEIGHT + 20), 520, 60, seed=6, lean=0.15):
        tone = mix(GRASS_NEAR, "#a8d85a", np.random.default_rng(int(root[0])).uniform(0.0, 0.8))
        painting.stroke(geo.bent_line(root, tip, bend), 3.6, tone, taper=(0.0, 0.9), layer="color", clip=off_path)
    for x, y, scale in scenery.scatter((0, HORIZON + 250, WIDTH, HEIGHT), 150, seed=12, near_scale=1.0, far_scale=0.25):
        color = ["#fff4d0", "#ffd24a", "#ff8fa8", "#ffffff"][int(x * 7 + y) % 4]
        painting.fill(painting.mask(geo.ellipse((x, y), 7 * scale + 1, 5.5 * scale + 1, count=12)) * off_path, color, 0.95)


def render(style_name, seed=0):
    style = get_style(style_name)
    painting = Painting(WIDTH, HEIGHT)
    paint_sky(painting, style)
    painting.snapshot("1 sky")
    paint_hills(painting, style)
    painting.snapshot("2 hills")
    path = paint_path(painting, style)
    paint_tree(painting, style, (1010, HORIZON + 330), 300, seed=5)
    paint_tree(painting, style, (250, HORIZON + 200), 130, seed=8)
    painting.snapshot("3 path and trees")
    paint_foreground(painting, style, path)
    painting.snapshot("4 foreground")
    image = finish(painting, style, seed=seed)
    painting.stages["5 finish"] = image
    return painting, image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="anime", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="meadow.png")
    parser.add_argument("--sheet", default=None)
    args = parser.parse_args()
    painting, image = render(args.style)
    painting.save(args.out, image)
    if args.sheet:
        fx.stage_sheet(painting.stages, args.sheet, columns=5)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
