"""Worked example: a winter field under a low grey sky, for doomer.py.

Usage: python doomer_landscape.py <anime|illust|painterly> <output.png> [width_px]
(doomer.py draws it with the doomer grade: python doomer.py <style> <out> <width> landscape)

A wide view at eye height: a power line walks off toward a town of prefab blocks on
the horizon, birches stand in the snow on the right, a trodden path leads away, dry
grass pokes through the snow up close. Pylons and birches are placed in metres and
projected, so they shrink correctly with distance.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atelier import STYLES, Art, ellipse, spline  # noqa: E402
from scenes import bare_tree, keep_fine_lines, panel_block  # noqa: E402

# ---- plan -------------------------------------------------------------------------------
ASPECT = 0.5                       # a wide panorama
LIGHT = (0.4, -0.5, 0.75)
HORIZON = 300.0
CENTRE_X = 500.0
FOCAL = 700.0                      # canvas units per metre at one metre away
EYE = 1.7                          # metres above the snow
PYLON_HEIGHT = 30.0
PYLONS = ((-40.0, 70.0), (-14.4, 150.0), (24.0, 270.0), (81.6, 450.0), (168.0, 720.0), (290.0, 1100.0))
PYLON_BEFORE = (-52.8, 30.0)       # the pylon behind the viewer's left shoulder, where the wires come from
ARMS = ((0.72, 0.30), (0.88, 0.22))            # cross arms: share of height, half span as a share of height
WIRE_SAG = 0.05                    # sag at mid span, as a share of the span's length on the canvas
BIRCHES = ((7.0, 30.0, 15.0, 2.0), (10.5, 34.0, 13.0, -3.0), (13.0, 27.0, 16.0, 4.0), (16.5, 38.0, 12.0, -1.0))
TOWN = (760.0, 990.0)              # canvas x span of the town on the horizon
FOREST = (-10.0, 540.0)            # canvas x span of the far spruce line
TUFTS = 34
CROWS = ((300, 110, 9), (336, 96, 7), (372, 124, 6))
SUN = (500, 150)                   # a pale disc behind the cloud

PALETTE = {
    "sky": "#333744", "sky_low": "#9A999F", "cloud": "#5C5F6C", "sun": "#E2DAC6",
    "snow_far": "#B3B9C5", "snow": "#D6DBE3", "drift": "#8A91A2", "path": "#7A8194",
    "forest": "#2F3542", "steel": "#24262E", "wire": "#1E2027", "birch": "#DAD8D0",
    "birch_mark": "#2A2A30", "twig": "#3A3337", "grass": "#4C4239", "crow": "#15161B",
}


def project(x, height, z):
    """Ground position (x across, z away, metres) and height above the snow to canvas units."""
    return CENTRE_X + FOCAL * x / z, HORIZON + FOCAL * (EYE - height) / z


def draw_sky(art):
    art.paint(art.everywhere(), PALETTE["sky"])
    art.paint(art.ramp((0, 0), (0, HORIZON)), PALETTE["sky_low"])
    clouds = art.threshold(art.noise(220, 4), 0.55, 0.12)
    art.paint(clouds * (1 - art.ramp((0, HORIZON - 160), (0, HORIZON))), PALETTE["cloud"], 0.45)
    art.light(art.blob(SUN, 140), PALETTE["sun"], 0.25)
    art.paint(art.feather(art.shape(ellipse(*SUN, 24, 24)), 6), PALETTE["sun"], 0.5)


def draw_horizon(art):
    """Spruces on the left, the town on the right, each faded by distance."""
    x = FOREST[0]
    spruces = []
    while x < FOREST[1]:
        height = art.rng.uniform(8, 22)
        spruces.append(np.array([(x - height * 0.3, HORIZON + 2), (x, HORIZON - height), (x + height * 0.3, HORIZON + 2)]))
        x += art.rng.uniform(4, 10)
    art.paint(art.shapes(spruces), PALETTE["forest"])
    x = TOWN[0]
    while x < TOWN[1]:
        width, floors = art.rng.uniform(36, 80), int(art.rng.integers(9, 17))
        height = floors * 3.2
        panel_block(art, (x, HORIZON - height, x + width, HORIZON + 2), floors, max(int(width / 5), 1),
                    haze=0.4, haze_colour=PALETTE["sky_low"])
        x += width + art.rng.uniform(4, 24)
    stack = np.array([(TOWN[0] + 40, HORIZON), (TOWN[0] + 50, HORIZON), (TOWN[0] + 48, HORIZON - 90),
                      (TOWN[0] + 42, HORIZON - 90)])
    art.paint(art.shape(stack), PALETTE["forest"], 0.8)
    art.paint(art.feather(art.shape(ellipse(TOWN[0] + 110, HORIZON - 104, 80, 14)), 12), PALETTE["sky_low"], 0.6)


def draw_field(art):
    field = art.shape(np.array([(-10, HORIZON), (1010, HORIZON), (1010, art.units_high + 10),
                                (-10, art.units_high + 10)]))
    art.paint(field, PALETTE["snow"])
    art.paint(field * (1 - art.ramp((0, HORIZON), (0, HORIZON + 60))), PALETTE["snow_far"])
    for x, y, rx, ry in ((260, 360, 300, 14), (760, 410, 360, 18), (420, 470, 420, 22)):    # drifts
        art.paint(art.feather(art.shape(ellipse(x, y, rx, ry)), ry), PALETTE["drift"], 0.3)
    path = spline([(560, art.units_high + 10), (520, 450), (430, 380), (400, 330), (440, HORIZON + 4)])
    art.paint(art.feather(art.brush(path, 40, "end"), 4), PALETTE["path"], 0.55)
    return field


def pylon(art, x, z):
    """A lattice steel tower: tapered legs, cross arms, X bracing, wire points returned."""
    foot_left, foot_right = project(x - 3.5, 0, z), project(x + 3.5, 0, z)
    top = project(x, PYLON_HEIGHT, z)
    width = max(90 / z, 0.8)
    left_leg = np.array([foot_left, (top[0] - (foot_right[0] - foot_left[0]) * 0.08, top[1])])
    right_leg = np.array([foot_right, (top[0] + (foot_right[0] - foot_left[0]) * 0.08, top[1])])
    for leg in (left_leg, right_leg):
        art.mark(leg, PALETTE["steel"], width, "none")
    levels = np.linspace(0, 1, 7)
    for low, high in zip(levels[:-1], levels[1:]):
        a, b = left_leg[0] + (left_leg[1] - left_leg[0]) * low, right_leg[0] + (right_leg[1] - right_leg[0]) * low
        c, d = left_leg[0] + (left_leg[1] - left_leg[0]) * high, right_leg[0] + (right_leg[1] - right_leg[0]) * high
        art.mark(np.array([a, d]), PALETTE["steel"], width * 0.5, "none")
        art.mark(np.array([b, c]), PALETTE["steel"], width * 0.5, "none")
    points = []
    for share, half in ARMS:
        y = project(x, PYLON_HEIGHT * share, z)[1]
        span = FOCAL * PYLON_HEIGHT * half / z
        art.mark(np.array([(top[0] - span, y), (top[0] + span, y)]), PALETTE["steel"], width * 0.8, "none")
        for side in (-1, 1):
            end = np.array([top[0] + side * span * 0.9, y + FOCAL * 1.6 / z])      # insulator hangs below
            art.mark(np.array([(end[0], y), end]), PALETTE["steel"], width * 0.5, "none")
            points.append(end)
    return points


def wire_points(x, z):
    """Where the wires hang on a pylon (for the one outside the frame)."""
    top_x = project(x, PYLON_HEIGHT, z)[0]
    return [np.array([top_x + side * FOCAL * PYLON_HEIGHT * half * 0.9 / z,
                      project(x, PYLON_HEIGHT * share, z)[1] + FOCAL * 1.6 / z])
            for share, half in ARMS for side in (-1, 1)]


def draw_power_line(art):
    previous = wire_points(*PYLON_BEFORE)
    for x, z in PYLONS:
        current = pylon(art, x, z)
        for start, end in zip(previous, current):
            middle = (start + end) / 2 + (0, WIRE_SAG * np.hypot(*(end - start)))
            art.mark(spline([tuple(start), tuple(middle), tuple(end)]), PALETTE["wire"], 1.3, "none")
        previous = current


def birch(art, x, z, height, lean):
    """A white trunk with dark marks and a crown of fine dark twigs."""
    foot, top = np.array(project(x, 0, z)), np.array(project(x + lean * 0.1, height, z))
    width = FOCAL * 0.3 / z
    trunk = art.brush(np.array([foot, top]), width, "end")
    art.part(trunk, PALETTE["birch"], bulge=width * 0.5)
    for share in art.rng.uniform(0.05, 0.85, 14):
        y = foot + (top - foot) * share
        art.mark(np.array([y - (width * 0.4, 0), y + (width * art.rng.uniform(-0.1, 0.4), 0)]),
                 PALETTE["birch_mark"], width * 0.18, "both")
    for share, angle in ((0.38, lean - 28), (0.5, lean + 26), (0.62, lean - 18), (0.74, lean + 14)):
        start = foot + (top - foot) * share
        bare_tree(art, tuple(start), np.hypot(*(top - foot)) * 0.26, PALETTE["twig"], depth=3, spread=24,
                  angle=angle, width=width * 0.28)


def draw_grass(art):
    for _ in range(TUFTS):
        x, y = art.rng.uniform(0, 1000), art.rng.uniform(430, art.units_high + 4)
        tuft = art.rng.uniform(0.6, 1.6)
        for _ in range(int(art.rng.integers(2, 8))):
            blade = art.rng.uniform(-35, 35)
            length = art.rng.uniform(8, 28) * tuft * (y - HORIZON) / 200
            tip = (x + length * np.sin(np.radians(blade)), y - length * np.cos(np.radians(blade)))
            art.mark(np.array([(x, y), tip]), PALETTE["grass"], 1.6, "end", opacity=0.85)


def draw_crows(art):
    for x, y, size in CROWS:
        art.mark(spline([(x - size, y - size * 0.4), (x - size * 0.4, y - size * 0.1), (x, y + size * 0.15)]),
                 PALETTE["crow"], 2.0, "start")
        art.mark(spline([(x, y + size * 0.15), (x + size * 0.4, y - size * 0.1), (x + size, y - size * 0.4)]),
                 PALETTE["crow"], 2.0, "end")


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=23)
    draw_sky(art)
    draw_horizon(art)
    draw_field(art)
    art.blur(1)
    draw_power_line(art)
    for x, z, height, lean in sorted(BIRCHES, key=lambda birch_plan: -birch_plan[1]):
        birch(art, x, z, height, lean)
    draw_grass(art)
    draw_crows(art)
    keep_fine_lines(art)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    draw(style_name, width).save(output)
    print(f"saved {output}")
