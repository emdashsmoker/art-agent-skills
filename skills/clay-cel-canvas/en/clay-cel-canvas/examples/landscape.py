"""Worked example: lake and mountains at dusk, in any of the three styles.

Usage: python landscape.py <anime|illust|painterly> <output.png> [width_px]

Depth comes from three habits: far things are paler and bluer, overlap goes
back to front, and detail is saved for the foreground.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atelier import STYLES, Art, ellipse, mix, spline  # noqa: E402

# ---- plan -------------------------------------------------------------------
ASPECT = 0.62                      # wide format
HORIZON = 360                      # y of the far shoreline
LIGHT = (0.55, -0.45, 0.70)        # low sun on the right
SUN = (690, 250)

PALETTE = {
    "sky_top": "#3B4C8A", "sky_mid": "#E58C6B", "sky_low": "#FFD9A0", "sun": "#FFF3C9",
    "cloud": "#F7A58B", "cloud_shadow": "#8E6FA8",
    "far": "#7C86B8", "mid": "#4F5C8E", "near": "#2C3560",
    "water": "#5A6FA6", "water_glow": "#FFC48A",
    "pine": "#1B2440", "boat": "#2A1F33", "shore": "#1F2A4A",
}


def ridge(rng, left, right, base_y, height, peaks):
    """Closed mountain silhouette: random peaks along a base line."""
    xs = np.linspace(left, right, peaks * 2 + 1)
    xs[1:-1] += rng.uniform(-0.3, 0.3, len(xs) - 2) * (right - left) / (peaks * 2)
    is_peak = np.arange(len(xs)) % 2 == 1
    ys = base_y - height * np.where(is_peak, rng.uniform(0.55, 1.0, len(xs)),
                                    rng.uniform(0.10, 0.35, len(xs)))
    top = [(x, y, True) if peak else (x, y) for x, y, peak in zip(xs, ys, is_peak)]
    return spline([(left, base_y + 40, True)] + top + [(right, base_y + 40, True)], closed=True)


def pine(art, x, base_y, height):
    """Pine tree: stacked triangles that widen toward the ground."""
    tiers = 5
    for tier in range(tiers):
        top = base_y - height * (1 - tier / (tiers + 1))
        bottom = top + height * 0.34
        half = height * 0.07 * (tier + 1.6)
        # Backlit at dusk, so the trees stay flat silhouettes.
        art.part(np.array([(x, top), (x + half, bottom), (x - half, bottom)], float),
                 PALETTE["pine"], shade=False, outline=False)


def draw_sky(art):
    art.paint(art.everywhere(), PALETTE["sky_top"])
    art.paint(art.ramp((0, 40), (0, HORIZON - 120)), PALETTE["sky_mid"])
    art.paint(art.ramp((0, HORIZON - 170), (0, HORIZON)), PALETTE["sky_low"])
    art.light(art.blob(SUN, 260), PALETTE["sun"], 0.55)
    art.paint(art.shape(ellipse(*SUN, 34, 34)), PALETTE["sun"])

    # Clouds: noise stretched sideways, kept only in a band of the sky.
    band = art.ramp((0, 40), (0, 150)) * (1 - art.ramp((0, 200), (0, 300)))
    clouds = art.threshold(art.noise(150) * 0.6 + art.noise(40) * 0.4, 0.52, 0.04) * band
    art.paint(clouds, PALETTE["cloud"], 0.9)
    art.shadow(clouds * (1 - art.move(clouds, 0, -10)), PALETTE["cloud_shadow"], 0.5)


def draw_mountains(art):
    layers = ((PALETTE["far"], HORIZON, 110, 5), (PALETTE["mid"], HORIZON + 6, 150, 3),
              (PALETTE["near"], HORIZON + 14, 95, 3))
    masks = []
    for depth, (color, base, height, peaks) in enumerate(layers):
        left, right = (-60, 640) if depth == 1 else ((420, 1060) if depth == 2 else (-60, 1060))
        masks.append(art.part(ridge(art.rng, left, right, base, height, peaks), color,
                              bulge=60, outline=(depth > 0)))
        if depth == 0:
            art.blur(2.0)                       # only the farthest layer goes soft
    return np.maximum.reduce(masks)


def draw_lake(art):
    water = art.shape(np.array([(0, HORIZON + 14), (1000, HORIZON + 14),
                                (1000, 700), (0, 700)], float))
    art.part(water, PALETTE["water"], shade=False, outline=False)
    art.paint(water * (1 - art.ramp((0, HORIZON), (0, HORIZON + 160))), PALETTE["mid"], 0.55)
    glow = art.blob((SUN[0], HORIZON + 60), 220) * water
    art.light(glow, PALETTE["water_glow"], 0.5)
    for _ in range(46):                          # glints: short horizontal dashes
        x = art.rng.normal(SUN[0], 70)
        y = art.rng.uniform(HORIZON + 22, 600)
        half = art.rng.uniform(8, 34) * (0.5 + (y - HORIZON) / 300)
        art.mark(np.array([(x - half, y), (x + half, y)], float),
                 mix(PALETTE["water_glow"], "#FFFFFF", 0.4), 2.4, opacity=0.8)
    return water


def draw_foreground(art):
    boat = art.part(spline([(300, 470, True), (392, 470, True), (376, 486), (316, 486)],
                           closed=True), PALETTE["boat"], shade=False)
    art.mark(np.array([(346, 470), (346, 426)], float), PALETTE["boat"], 2.6, "none")
    art.shadow(art.move(boat, 0, 14) * (1 - boat), opacity=0.5)

    shore = art.part(spline([(-20, 640, True), (-20, 560), (120, 548), (260, 578), (420, 604),
                             (560, 640, True)], closed=True), PALETTE["shore"], bulge=30)
    for x, base, height in ((70, 566, 250), (150, 560, 190), (226, 580, 150), (20, 575, 310)):
        pine(art, x, base, height)
    return shore


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=11)
    draw_sky(art)
    draw_mountains(art)
    draw_lake(art)
    draw_foreground(art)
    art.focus_on(art.blob((346, 470), 110))
    art.focus_on(art.blob(SUN, 90) * 0.5)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
