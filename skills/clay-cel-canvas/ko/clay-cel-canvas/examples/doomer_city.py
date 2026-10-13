"""Worked example: a street between prefab blocks on a snowy night, for doomer.py.

Usage: python doomer_city.py <anime|illust|painterly> <output.png> [width_px]
(doomer.py draws it with the doomer grade: python doomer.py <style> <out> <width> city)

One-point perspective as in city.py: the street is laid out in metres (x right, y down
from eye level, z away) and every receding thing comes out of project(). A long block
runs down the left side, face-on blocks close the view, sodium lamps and trolleybus
wires line the road, and snow falls over all of it.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atelier import STYLES, Art, spline  # noqa: E402
from scenes import BLOCK, keep_fine_lines, panel_block, snowfall  # noqa: E402

# ---- plan -------------------------------------------------------------------------------
ASPECT = 1.25
LIGHT = (0.5, -0.6, 0.6)
VANISH = (640.0, 860.0)            # vanishing point on the canvas = eye level
FOCAL = 430.0                      # canvas units per metre at one metre away
GROUND = 1.6                       # the road, metres below the eye
STOREY = 2.8
PLINTH = 0.8                       # ground floor raised above the street
BAY = 3.4                          # metres of facade per window
WINDOW = (0.95, 2.45, 0.9, 2.4)    # in a bay and a storey: from, to along; from, to above the floor
FACADE_X = -11.0                   # the long block's street face
FACADE_Z = (4.5, 160.0)
FACADE_FLOORS = 9
DOORS = (14.0, 42.0, 70.0, 98.0, 126.0)        # entrances along the facade, metres away
DOOR = (1.4, 2.2)                  # width, height
FAR_BLOCKS = ((-14.0, 30.0, 110.0, 16), (9.0, 62.0, 55.0, 14))   # face-on blocks: x from, x to, z, floors
ROAD = (-5.0, 5.0)
BANK = 0.9                         # snow banks along each side of the road
TRACKS = (-2.3, -1.3, 1.3, 2.3)    # tyre tracks in the slush
LAMP_X, LAMP_ARM_X, LAMP_HEIGHT = 6.4, 4.6, 8.0
LAMPS = (9.0, 18.0, 31.0, 50.0, 85.0)
WIRES = (-0.6, 0.6)                # trolleybus wires over the road
WIRE_HEIGHT = 6.0
NEAR, FAR = 3.0, 400.0
GROUND_NEAR = 1.0                  # the road starts this close, so it reaches past the frame's lower edge
LIT_SHARE = (0.16, 0.05)           # windows lit by a lamp, by a television
SMALL_WINDOW = 2.5                 # canvas units: a dark window smaller than this is not drawn

PALETTE = {
    "sky": "#0D111B", "sky_low": "#4E3D3A", "facade": "#5A5F6C", "facade_far": "#4A4E5C",
    "snow": "#8D95A7", "road": "#2B2E38", "track": "#1B1D25", "bank": "#A5ADBD",
    "pole": "#14161D", "lamp": "#FFA858", "wire": "#0C0E14", "door": "#E8B062", "canopy": "#2A2D36",
}


def project(x, y, z):
    """Street position in metres to canvas units."""
    return VANISH[0] + FOCAL * x / z, VANISH[1] + FOCAL * y / z


def projected(points):
    return np.array([project(*point) for point in points], float)


def facade_quad(z0, z1, below, above):
    """Rectangle on the long facade: from z0 to z1, between heights `below` and `above`
    above the street (metres)."""
    return projected([(FACADE_X, GROUND - above, z0), (FACADE_X, GROUND - above, z1),
                      (FACADE_X, GROUND - below, z1), (FACADE_X, GROUND - below, z0)])


def ground_quad(x0, x1, z0, z1):
    return projected([(x0, GROUND, z0), (x1, GROUND, z0), (x1, GROUND, z1), (x0, GROUND, z1)])


def draw_sky(art):
    art.paint(art.everywhere(), PALETTE["sky"])
    art.paint(art.ramp((0, VANISH[1] - 700), (0, VANISH[1])), PALETTE["sky_low"])


def draw_far_blocks(art):
    for x0, x1, z, floors in FAR_BLOCKS:                 # listed far to near
        top = GROUND - PLINTH - floors * STOREY
        box = (*project(x0, top, z), *project(x1, GROUND, z))
        panel_block(art, box, floors, max(int((x1 - x0) / BAY), 1), balconies=(1, 2, 5, 6), lit=LIT_SHARE,
                    haze=0.25, haze_colour=PALETTE["sky_low"])


def draw_ground(art):
    art.paint(art.shape(ground_quad(-60, 60, GROUND_NEAR, FAR)), PALETTE["snow"])
    art.paint(art.shape(ground_quad(*ROAD, GROUND_NEAR, FAR)), PALETTE["road"])
    for side in (-1, 1):
        edge = ROAD[1] * side
        art.paint(art.shape(ground_quad(min(edge, edge + side * BANK), max(edge, edge + side * BANK),
                                        GROUND_NEAR, FAR)), PALETTE["bank"])
    for x in TRACKS:
        art.paint(art.shape(ground_quad(x - 0.25, x + 0.25, GROUND_NEAR, FAR)), PALETTE["track"], 0.8)


def draw_facade(art):
    z0, z1 = FACADE_Z
    height = PLINTH + FACADE_FLOORS * STOREY
    wall = art.shape(facade_quad(z0, z1, 0, height))
    art.paint(wall, PALETTE["facade"])
    art.paint(wall * art.ramp(project(FACADE_X, 0, 20), project(FACADE_X, 0, z1)), PALETTE["facade_far"], 0.8)
    panes = {"window": [], "lit_warm": [], "lit_cold": []}
    along_from, along_to, low, high = WINDOW
    for bay in np.arange(z0, z1 - BAY, BAY):
        for floor in range(FACADE_FLOORS):
            base = PLINTH + floor * STOREY
            pane = facade_quad(bay + along_from, bay + along_to, base + low, base + high)
            pick = art.rng.random()
            kind = ("lit_warm" if pick < LIT_SHARE[0] else
                    "lit_cold" if pick < LIT_SHARE[0] + LIT_SHARE[1] else "window")
            if kind != "window" or np.ptp(pane[:, 1]) >= SMALL_WINDOW:
                panes[kind].append(pane)
    for floor in range(FACADE_FLOORS + 1):              # joints between the storeys
        line = facade_quad(z0, z1, PLINTH + floor * STOREY, PLINTH + floor * STOREY)[:2]
        art.mark(line, BLOCK["joint"], 1.6, "end", opacity=0.6)
    for kind, quads in panes.items():
        if quads:
            mask = art.shapes(quads) * wall
            art.paint(mask, BLOCK[kind])
            if kind != "window":
                art.light(art.feather(mask, 6), BLOCK[kind], 0.4)
    width, height_door = DOOR
    for z in DOORS:
        door = art.shape(facade_quad(z, z + width, 0, height_door))
        art.paint(door, PALETTE["door"])
        art.light(art.feather(door, 30 * 10 / z), PALETTE["door"], 0.6)
        art.paint(art.shape(facade_quad(z - 0.6, z + width + 0.6, height_door + 0.1, height_door + 0.5)),
                  PALETTE["canopy"])
    return wall


def draw_lamp(art, z):
    foot, top = project(LAMP_X, GROUND, z), project(LAMP_X, GROUND - LAMP_HEIGHT, z)
    head = np.array(project(LAMP_ARM_X, GROUND - LAMP_HEIGHT + 0.3, z))
    width = max(60 / z, 1.2)
    art.mark(np.array([foot, top]), PALETTE["pole"], width, "none")
    art.mark(spline([top, project((LAMP_X + LAMP_ARM_X) / 2, GROUND - LAMP_HEIGHT - 0.3, z), tuple(head)]),
             PALETTE["pole"], width * 0.7, "none")
    art.light(art.blob(head, 1800 / z), PALETTE["lamp"], 0.45)
    art.light(art.blob(head, 500 / z), PALETTE["lamp"], 0.9)
    circle = [(LAMP_ARM_X + 4 * np.cos(t), GROUND, z + 4 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 24)]
    pool = art.shape(projected([point for point in circle if point[2] > NEAR]))
    art.light(art.feather(pool, 400 / z), PALETTE["lamp"], 0.35)


def draw_wires(art):
    for x in WIRES:
        art.mark(projected([(x, GROUND - WIRE_HEIGHT, NEAR), (x, GROUND - WIRE_HEIGHT, FAR)]), PALETTE["wire"], 1.8,
                 "end")
    for z in LAMPS:                                    # spans from each pole across to the facade
        span = [project(LAMP_X, GROUND - LAMP_HEIGHT + 0.6, z), project(0, GROUND - WIRE_HEIGHT + 0.3, z),
                project(FACADE_X, GROUND - LAMP_HEIGHT + 0.2, z)]
        art.mark(spline(span), PALETTE["wire"], 1.2, "none", opacity=0.9)


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=11)
    draw_sky(art)
    draw_far_blocks(art)
    draw_ground(art)
    art.blur(1)
    wall = draw_facade(art)
    art.focus_on(art.feather(wall, 10) * 0.5)
    for z in sorted(LAMPS, reverse=True):
        draw_lamp(art, z)
    draw_wires(art)
    keep_fine_lines(art)
    snowfall(art)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    draw(style_name, width).save(output)
    print(f"saved {output}")
