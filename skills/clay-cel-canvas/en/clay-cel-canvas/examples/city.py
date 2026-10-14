"""Worked example: rainy evening street in one-point perspective.

Usage: python city.py <anime|illust|painterly> <output.png> [width_px]

The street is modelled in metres (x right, y down from eye level, z into the
picture) and projected onto the canvas. Everything that recedes - facades,
windows, road markings, reflections - comes out of the same project() function,
which is what keeps the perspective consistent.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atelier import STYLES, Art, ellipse, mix, spline  # noqa: E402

# ---- plan -------------------------------------------------------------------
ASPECT = 1.25
LIGHT = (0.0, -0.8, 0.6)
VIEW = (500, 575, 1.1)              # crop some of the empty foreground
VANISH = (470.0, 720.0)            # vanishing point on the canvas = eye level
FOCAL = 430.0                      # canvas units per metre at one metre distance
EYE = 1.6                          # eye height above the road, metres
ROAD_HALF = 5.5                    # half width of the road
FACADE = 9.0                       # distance of the building fronts from the centre line
NEAR, FAR = 5.0, 170.0             # depth range of the street
FLOOR = 3.2                        # storey height
SHOP = 4.2                         # ground floor height
SMEAR_METRES = 4.0                 # how far a reflection stretches toward the viewer
SMEAR_STEPS = 6

PALETTE = {
    "sky_top": "#23264F", "sky_mid": "#8E4F86", "sky_low": "#F2A070",
    "haze": "#B9788F", "building": ("#2A2E52", "#34345E", "#263048", "#3A3157"),
    "window_dark": "#1B2038", "road": "#1F2238", "walk": "#34364F", "marking": "#C9CDE0",
    "lit": ("#FFD27A", "#FFD27A", "#FFC06A", "#BFE6FF", "#FF9FB8"),
    "neon": ("#FF4F8B", "#36E0D0", "#FFB02E", "#8C7BFF"),
    "lamp": "#FFE2A8", "pole": "#15172A", "umbrella": "#E0413A", "coat": "#16182B",
}


def project(x, y, z):
    """Street position in metres (y measured down from eye level) to canvas units."""
    return (VANISH[0] + FOCAL * x / z, VANISH[1] + FOCAL * y / z)


def wall_quad(side, z0, z1, y0, y1):
    """Rectangle on a street-facing facade (plane x = side * FACADE)."""
    x = side * FACADE
    return np.array([project(x, y0, z0), project(x, y0, z1), project(x, y1, z1),
                     project(x, y1, z0)], float)


def cross_quad(x0, x1, y0, y1, z):
    """Rectangle facing the viewer (plane z = constant)."""
    return np.array([project(x0, y0, z), project(x1, y0, z), project(x1, y1, z),
                     project(x0, y1, z)], float)


def ground_quad(x0, x1, z0, z1):
    """Rectangle lying on the road."""
    return np.array([project(x0, EYE, z0), project(x1, EYE, z0), project(x1, EYE, z1),
                     project(x0, EYE, z1)], float)


def reflect(art, mirrored, z, wet, color, opacity):
    """Light a wet road with the mirror image of a lamp, sign or window at depth z.

    The mirror image is smeared downward, as lights stretch on wet asphalt; the
    nearer the light, the longer the smear.
    """
    scale = FOCAL / z
    smeared = mirrored.copy()
    for step in range(1, SMEAR_STEPS + 1):
        fade = 1 - step / (SMEAR_STEPS + 1)
        shift = SMEAR_METRES * scale * step / SMEAR_STEPS
        smeared = np.maximum(smeared, art.move(mirrored, 0, shift) * fade)
    art.light(art.feather(smeared, max(0.25 * scale, 3)) * wet, color, opacity)


def plan_buildings(rng, side):
    """Row of buildings along one side: (z0, z1, height), nearest first."""
    row, z = [], NEAR
    while z < FAR:
        depth = rng.uniform(9, 17)
        row.append((z, z + depth, rng.uniform(13, 44)))
        z += depth + (6.0 if rng.random() < 0.2 else 0.0)        # sometimes a side street
    return row


def draw_sky(art):
    art.paint(art.everywhere(), PALETTE["sky_top"])
    art.paint(art.ramp((0, 60), (0, VANISH[1] - 220)), PALETTE["sky_mid"])
    art.paint(art.ramp((0, VANISH[1] - 330), (0, VANISH[1])), PALETTE["sky_low"])
    band = art.ramp((0, 120), (0, 300)) * (1 - art.ramp((0, 420), (0, 600)))
    clouds = art.threshold(art.noise(170) * 0.65 + art.noise(45) * 0.35, 0.5, 0.06) * band
    art.paint(clouds, "#5B3F7A", 0.55)
    towers = []                                                    # skyline at the far end
    for _ in range(14):
        x, height = art.rng.uniform(-40, 40), art.rng.uniform(40, 120)
        towers.append(cross_quad(x, x + art.rng.uniform(8, 18), EYE - height, EYE, 420.0))
    art.paint(art.shapes(towers), mix(PALETTE["building"][0], PALETTE["haze"], 0.6))
    art.blur(1.5)


def draw_ground(art):
    road = art.shape(ground_quad(-ROAD_HALF, ROAD_HALF, 0.9, FAR * 3))
    walks = art.shapes([ground_quad(side * ROAD_HALF, side * FACADE, 0.9, FAR * 3)
                        for side in (-1, 1)])
    art.paint(np.maximum(road, walks), PALETTE["walk"])
    art.paint(road, PALETTE["road"])
    wet = np.maximum(road, walks)
    art.light(wet * (1 - art.ramp((0, VANISH[1]), (0, VANISH[1] + 190))), PALETTE["sky_low"], 0.45)
    stripes = [ground_quad(x, x + 0.6, 9.0, 12.5) for x in np.arange(-5.0, 5.0, 1.25)]
    dashes = [ground_quad(-0.08, 0.08, z, z + 3) for z in np.arange(15, 120, 7.0)]
    art.paint(art.shapes(stripes + dashes) * road, PALETTE["marking"], 0.8)
    for side in (-1, 1):                                          # kerb
        kerb = np.array([project(side * ROAD_HALF, EYE, z) for z in (0.9, FAR * 3)], float)
        art.line(kerb, "#6C6F8C", 1.6, "none")
    return road, wet


def facade_windows(rng, side, z0, z1, height):
    """Window quads of one facade, split into lit (by colour index) and dark."""
    lit, dark = {}, []
    floors = int((height - SHOP) / FLOOR)
    for floor in range(floors):
        top = EYE - SHOP - floor * FLOOR
        for z in np.arange(z0 + 1.2, z1 - 2.0, 2.6):
            quad = wall_quad(side, z, z + 1.5, top - 2.4, top - 0.8)
            if rng.random() < 0.42:
                lit.setdefault(int(rng.integers(len(PALETTE["lit"]))), []).append(quad)
            else:
                dark.append(quad)
    return lit, dark


def draw_building(art, side, z0, z1, height, wet):
    depth_haze = min(z0 / FAR, 1.0) * 0.75
    color = mix(PALETTE["building"][int(art.rng.integers(4))], PALETTE["haze"], depth_haze)
    top = EYE - height
    art.part(cross_quad(side * FACADE, side * 60, top, EYE, z0), mix(color, "#000000", 0.25),
             shade=False, line_width=1.4)
    wall = art.part(wall_quad(side, z0, z1, top, EYE), color, shade=False, line_width=1.4)

    lit, dark = facade_windows(art.rng, side, z0, z1, height)
    if dark:
        art.paint(art.shapes(dark), mix(PALETTE["window_dark"], PALETTE["haze"], depth_haze), 0.9)
    shop_color = int(art.rng.integers(len(PALETTE["lit"])))
    for bay in np.arange(z0 + 0.8, z1 - 2.4, 3.2):               # shop front, bay by bay
        lit.setdefault(shop_color, []).append(wall_quad(side, bay, bay + 2.7, EYE - 3.1, EYE - 0.5))
    for index, quads in lit.items():
        glass = art.shapes(quads)
        art.paint(glass, mix(PALETTE["lit"][index], PALETTE["haze"], depth_haze * 0.5))
        art.light(art.feather(glass, 4), PALETTE["lit"][index], 0.35)
    mirrored = art.shape(wall_quad(side, z0 + 0.8, z1 - 0.8, EYE + 0.5, EYE + 3.1))
    reflect(art, mirrored, (z0 + z1) / 2, wet, PALETTE["lit"][shop_color], 0.45)
    return wall


def draw_sign(art, side, z, wet):
    """Neon sign sticking out over the pavement, with its reflection."""
    color = PALETTE["neon"][int(art.rng.integers(len(PALETTE["neon"])))]
    low, high = art.rng.uniform(4.6, 6.0), art.rng.uniform(8.0, 12.0)
    inner, outer = side * (FACADE - 1.5), side * FACADE
    sign = art.shape(cross_quad(inner, outer, EYE - high, EYE - low, z))
    art.paint(sign, color)
    art.light(art.feather(sign, 9), color, 0.8)
    mirrored = art.shape(cross_quad(inner, outer, EYE + low, EYE + high, z))
    reflect(art, mirrored, z, wet, color, 0.6)


def draw_lamp(art, side, z, wet):
    x = side * (ROAD_HALF + 0.4)
    foot, head = project(x, EYE, z), project(x, EYE - 6.5, z)
    arm = project(x - side * 1.4, EYE - 6.8, z)
    width = 0.16 * FOCAL / z
    art.mark(np.array([foot, head]), PALETTE["pole"], width, "none")
    art.mark(np.array([head, arm]), PALETTE["pole"], width * 0.8, "none")
    art.light(art.blob(arm, 1.9 * FOCAL / z), PALETTE["lamp"], 0.9)
    art.paint(art.shape(ellipse(*arm, 0.28 * FOCAL / z, 0.14 * FOCAL / z)), "#FFFFFF")
    pool = project(x - side * 1.4, EYE, z)
    art.light(art.shape(ellipse(*pool, 3.2 * FOCAL / z, 0.5 * FOCAL / z)) * wet, PALETTE["lamp"], 0.3)
    return head


def draw_walker(art, x, z, wet):
    """Small figure under an umbrella, seen from behind; gives the street its scale."""
    unit = FOCAL / z                                   # canvas units per metre at this depth
    with art.place(at=project(x, EYE, z), scale=unit):
        legs = art.tube([(-0.09, -0.85, 0.2), (-0.1, -0.4, 0.15), (-0.11, 0.0, 0.1)])
        legs = np.maximum(legs, art.tube([(0.09, -0.85, 0.2), (0.12, -0.4, 0.15), (0.15, 0.0, 0.1)]))
        body = art.tube([(0, -1.5, 0.34), (0, -1.15, 0.46), (0, -0.8, 0.5)])
        art.part(np.maximum(legs, body), PALETTE["coat"], shade=False)
        art.mark(np.array([(0.18, -1.2), (0.2, -2.0)], float), PALETTE["pole"], 0.03, "none")
        canopy = spline([(-0.62, -1.82, True), (-0.3, -2.14), (0.2, -2.2), (0.72, -2.12),
                         (1.02, -1.82, True), (0.6, -1.9), (0.2, -1.84), (-0.2, -1.9)],
                        closed=True)
        umbrella = art.part(canopy, PALETTE["umbrella"], bulge=0.2)
        art.light(umbrella * art.blob((0.0, -2.2), 0.6), "#FFB0A0", 0.5)
        mirrored = art.tube([(0, 0.05, 0.4), (0, 1.5, 0.5)])
        art.shadow(art.feather(mirrored, 0.12) * wet, "#3A3550", 0.8)
        art.focus_on(art.blob((0.1, -1.2), 2.4))


def draw_rain(art):
    drops = []
    for _ in range(170):
        x, y = art.rng.uniform(0, 1000), art.rng.uniform(0, art.units_high)
        length = art.rng.uniform(18, 46)
        drops.append(art.brush(np.array([(x, y), (x - length * 0.18, y + length)], float), 1.3))
    art.light(np.maximum.reduce(drops), "#DCE6FF", 0.22)


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=4,
              view=VIEW)
    draw_sky(art)
    road, wet = draw_ground(art)
    rows = [(side, building) for side in (-1, 1) for building in plan_buildings(art.rng, side)]
    for side, (z0, z1, height) in sorted(rows, key=lambda row: -row[1][0]):   # far to near
        draw_building(art, side, z0, z1, height, wet)
        if art.rng.random() < 0.7:
            draw_sign(art, side, art.rng.uniform(z0 + 1, z1 - 1), wet)
    heads = {side: [draw_lamp(art, side, z, wet) for z in np.arange(88, 9, -13.0)]
             for side in (-1, 1)}
    for side, tops in heads.items():                              # sagging overhead wires
        for a, b in zip(tops[:-1], tops[1:]):
            middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + abs(b[1] - a[1]) * 0.12 + 4)
            art.line(spline([a, middle, b]), PALETTE["pole"], 1.2, "none")
    draw_walker(art, 2.3, 8.5, wet)
    draw_rain(art)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
