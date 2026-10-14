"""Worked example: summer meadow with cumulus clouds and a large tree.

Usage: python meadow.py <anime|illust|painterly> <output.png> [width_px]

Clouds and foliage use one idea: a pile of overlapping balls, each shaded as a
sphere. Background art carries no outlines, so parts are added with
outline=False.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atelier import STYLES, Art, ellipse, spline  # noqa: E402

# ---- plan -------------------------------------------------------------------
ASPECT = 0.7
LIGHT = (0.50, -0.62, 0.60)        # high sun on the right
HORIZON = 430
PUFF_ATTEMPTS = 20                 # tries per ball before giving up on a pile

PALETTE = {
    "sky_top": "#2E7BD0", "sky_low": "#BFE4F8",
    "cloud": "#FFFFFF", "cloud_shadow": "#A9C2E6",
    "mountain": "#8FB4D9", "hill_far": "#7FB98A", "hill_near": "#5FA85C",
    "field": "#7CC254", "field_near": "#3F8F3A", "path": "#E8D8AE", "path_shadow": "#C9A97C",
    "trunk": "#6B4A32", "leaf": "#3E9444", "leaf_light": "#9BD45A", "leaf_shadow": "#56679A",
    "wall": "#F6EEDC", "roof": "#C8553D", "flower": ("#FFFFFF", "#FFE066", "#FF8FA3"),
}


def puffs(rng, center_x, base_y, width, height, count):
    """Balls that pile into a cumulus shape: tall in the middle, low at the ends.

    Every new ball must touch one already placed, so the pile never falls apart.
    """
    balls = []
    for attempt in range(count * PUFF_ATTEMPTS):
        if len(balls) == count:
            break
        along = rng.uniform(-1, 1) if balls else 0.0
        middle = 1 - along * along
        radius = rng.uniform(0.20, 0.36) * height * (0.45 + 0.55 * middle)
        x = center_x + along * width / 2
        y = base_y - radius * 0.75 - rng.uniform(0, 1) * middle * height * 0.6
        touching = any(np.hypot(x - bx, y - by) < (radius + br) * 0.75 for bx, by, br in balls)
        if touching or not balls:
            balls.append((x, y, radius))
    return sorted(balls, key=lambda ball: ball[1])      # upper balls first, lower in front


def draw_cloud(art, center_x, base_y, width, height, count):
    masks = []
    for x, y, radius in puffs(art.rng, center_x, base_y, width, height, count):
        masks.append(art.part(ellipse(x, y, radius * 1.2, radius), PALETTE["cloud"],
                              outline=False, shadow_tint=PALETTE["cloud_shadow"]))
    cloud = np.maximum.reduce(masks)
    underside = cloud * art.ramp((0, base_y - height * 0.45), (0, base_y + 10))
    art.shadow(underside, PALETTE["cloud_shadow"], 0.8)
    return cloud


def draw_sky(art):
    art.paint(art.everywhere(), PALETTE["sky_top"])
    art.paint(art.ramp((0, 40), (0, HORIZON)), PALETTE["sky_low"])
    for center_x, base_y, width, height, count in ((640, 395, 300, 70, 9), (120, 380, 240, 60, 8)):
        draw_cloud(art, center_x, base_y, width, height, count)
    art.blur(2.2)                                    # far clouds go soft
    draw_cloud(art, 290, 290, 470, 230, 22)
    draw_cloud(art, 880, 210, 260, 120, 12)
    art.blur(0.8)


def draw_land(art):
    mountain = [(-20, HORIZON + 90, True), (-20, 395), (90, 372, True), (210, 400),
                (330, 380, True), (470, 412), (640, 398), (1020, 420), (1020, HORIZON + 90, True)]
    art.part(spline(mountain, closed=True), PALETTE["mountain"], shade=False, outline=False)
    far = [(-20, 600, True), (-20, 430), (140, 408), (300, 420), (450, 446), (620, 430),
           (800, 416), (1020, 432), (1020, 600, True)]
    hill = art.part(spline(far, closed=True), PALETTE["hill_far"], bulge=40, outline=False)
    near = [(-20, 720, True), (-20, 474), (160, 452), (380, 470), (560, 456), (760, 470),
            (1020, 458), (1020, 720, True)]
    field = art.part(spline(near, closed=True), PALETTE["field"], shade=False, outline=False)
    art.paint(field * art.ramp((0, 520), (0, 700)), PALETTE["field_near"], 0.85)
    art.paint(field * art.threshold(art.noise(90), 0.55, 0.12), PALETTE["hill_near"], 0.35)
    return hill, field


def draw_house(art):
    """Small house; origin at the middle of its base."""
    art.part(np.array([(-24, 0), (24, 0), (24, -26), (-24, -26)], float), PALETTE["wall"],
             bulge=6)
    art.part(np.array([(-30, -24), (0, -48), (30, -24)], float), PALETTE["roof"], bulge=6)
    art.paint(art.shapes([np.array([(-6, 0), (4, 0), (4, -15), (-6, -15)], float),
                          np.array([(10, -10), (19, -10), (19, -19), (10, -19)], float)]),
              "#6B4A32")


def draw_path(art, field):
    left = [(250, 720), (350, 610), (470, 530), (520, 486), (532, 462)]
    right = [(548, 462), (566, 486), (580, 530), (560, 610), (620, 720)]
    path = art.shape(spline([(250, 720, True)] + left[1:] + right[:-1] + [(620, 720, True)],
                            closed=True)) * field
    art.paint(path, PALETTE["path"])
    art.shadow(path * (1 - art.move(path, 10, 0)), PALETTE["path_shadow"], 0.7)
    return path


def draw_tree(art, field):
    """Large tree; trunk base at the origin, about 420 tall."""
    shade_on_grass = art.shape(ellipse(-60, 14, 190, 30)) * field
    art.shadow(art.feather(shade_on_grass, 6), PALETTE["leaf_shadow"], 0.75)
    trunk = art.tube([(0, 10, 54), (-4, -70, 36), (4, -150, 30), (-10, -230, 20)])
    for branch in ([(0, -120, 22), (50, -180, 14), (90, -230, 8)],
                   [(-2, -150, 20), (-52, -200, 12), (-96, -236, 7)]):
        trunk = np.maximum(trunk, art.tube(branch))
    art.part(trunk, PALETTE["trunk"], bulge=12)
    masks = []
    for x, y, radius in puffs(art.rng, 0, -170, 380, 250, 30):
        masks.append(art.part(ellipse(x, y, radius * 1.1, radius), PALETTE["leaf"],
                              outline=False, shadow_tint=PALETTE["leaf_shadow"]))
    canopy = np.maximum.reduce(masks)
    art.shadow(canopy * art.ramp((0, -260), (0, -150)), PALETTE["leaf_shadow"], 0.55)
    lit_side = canopy * (1 - art.move(canopy, -26, 30))            # upper right rim
    art.paint(lit_side, PALETTE["leaf_light"], 0.55)
    sparkle = art.threshold(art.noise(9, 2), 0.66, 0.03) * canopy
    art.paint(sparkle * art.ramp((-200, -100), (160, -330)), PALETTE["leaf_light"], 0.7)
    art.outline(np.maximum(canopy, trunk), "#1F4A2A", 1.8)
    return canopy


def draw_meadow_detail(art, field, path):
    grass = field * (1 - path)
    blades_dark, blades_light = [], []
    for _ in range(420):
        x, depth = art.rng.uniform(0, 1000), art.rng.uniform(0, 1) ** 0.6
        y = 500 + depth * 205
        length = 6 + depth * 30
        blade = np.array([(x, y), (x + art.rng.uniform(-0.3, 0.3) * length, y - length)], float)
        (blades_light if art.rng.random() < 0.5 else blades_dark).append((blade, 1.4 + depth * 2.6))
    for blades, color in ((blades_dark, "#2F7A33"), (blades_light, "#A5DC62")):
        mask = np.maximum.reduce([art.brush(blade, width, "end") for blade, width in blades])
        art.paint(mask * grass, color, 0.85)
    for color in PALETTE["flower"]:
        dots = []
        for _ in range(60):
            x, depth = art.rng.uniform(0, 1000), art.rng.uniform(0, 1)
            radius = 1.6 + depth * 3.4
            dots.append(ellipse(x, 500 + depth * 195, radius, radius * 0.8, samples=12))
        art.paint(art.shapes(dots) * grass, color)


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=21)
    draw_sky(art)
    hill, field = draw_land(art)
    with art.place(at=(232, 428), scale=0.9):
        draw_house(art)
    path = draw_path(art, field)
    draw_meadow_detail(art, field, path)
    with art.place(at=(790, 600)):
        canopy = draw_tree(art, field)
    art.focus_on(art.feather(canopy, 20) * 0.5)
    art.focus_on(art.blob((232, 410), 60))
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
