#!/usr/bin/env python3
"""Free-form scene example: a kitchen table by the window at night (doomer still life).

Shows how the scene ops and the finish presets work outside a JSON spec:
- the view out of the window is a second canvas built with the same urban ops a
  spec uses (panel_blocks, streetlamp, bare_tree, snow, fog), pasted through the
  glass panes;
- the cigarette and its smoke come from paintkit.props, the same code a figure uses;
- the table objects are boxes and cylinders on an objects.Stage (sizes in cm);
- scene.finish applies the "illust" chain with the "doomer" preset.

Usage: python doomer_still_life_example.py out.png
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from paintkit import backdrop as bd  # noqa: E402
from paintkit import core as pk  # noqa: E402
from paintkit import light as lt  # noqa: E402
from paintkit import objects as ob  # noqa: E402
from paintkit import props as pr  # noqa: E402
from paintkit import scene  # noqa: E402
from paintkit import scenery as sn  # noqa: E402
from paintkit import urban as ur  # noqa: E402

WIDTH, HEIGHT = 1500, 1100
UNIT = HEIGHT / 1100.0               # every pixel size below scales with the canvas
SEED = 7
PIXELS_PER_CM = 13.0 * UNIT
TABLE_ORIGIN = (760 * UNIT, 1000 * UNIT)
TABLE_BACK_Z = 34                    # cm: the table stands against the wall under the window
# Window opening in pixels (left, top, right): the bottom follows the table's back edge.
OPENING = (300 * UNIT, 40 * UNIT, 1200 * UNIT)
FRAME, MULLION, TRANSOM_Y = 30 * UNIT, 34 * UNIT, 300 * UNIT
WALL = ("#363c4a", "#3e4554", "#303642")
LINE = "#12141a"
# Toward the light: the window behind the table, a little above it.
WORLD_LIGHT = (0.10, 0.55, 0.83)
RIM_LIGHT = lt.light_vector(azimuth_deg=90, elevation_deg=30)
COLD, WARM = "#aebdd2", "#ffb35a"
RADIO = dict(center=(-36, 0, 15), size=(30, 10, 9))
TEA = dict(center=(14, 0, 9), radius=3.7, holder=6.2, glass=11.5, tea=9.8)
ASHTRAY = dict(center=(-3, 0, -11), radius=6.5, height=2.4)
PACK = dict(center=(27, 0, -14), size=(5.6, 2.2, 8.8))
MATCHES = dict(center=(37, 0, -3), size=(3.8, 1.5, 5.2))


# -- the view outside -----------------------------------------------------------
def outside_view() -> np.ndarray:
    """Night courtyard seen through the glass, built with the scene ops on its own canvas."""
    view = pk.Canvas(WIDTH, HEIGHT)
    sky = view.layer("sky")
    sn.sky(sky, "#121826", "#3a3346", horizon=0.78)
    blocks = view.layer("blocks")
    ur.panel_blocks(blocks, time="night", vanish=(0.62, 0.55), seed=SEED, blocks=[
        {"x": [0.06, 0.34], "base": 0.9, "top": 0.38, "floors": 12, "haze": 0.6, "lit": 0.22},
        {"x": [0.74, 0.99], "base": 0.9, "top": 0.42, "floors": 11, "haze": 0.65, "lit": 0.2},
        {"x": [0.36, 0.80], "base": 0.98, "top": 0.24, "floors": 13, "haze": 0.15, "side": -0.06,
         "balconies": True, "lit": 0.3},
    ])
    ur.fog(blocks, top=0.62, bottom=0.95, color="#2a2c3a", opacity=0.35)
    near = view.layer("near")
    ur.streetlamp(near, base=(0.22, 1.0), height=0.36, arm=1.0, glow=0.8)
    ur.bare_tree(near, base=(0.88, 1.06), height=0.62, color="#12151c", seed=SEED)
    ur.snow(view.layer("snow"), count=520, size=(0.0015, 0.006), opacity=0.8, wind=10, seed=SEED)
    return view.flatten()


# -- wall and window ------------------------------------------------------------
def window_geometry(stage: ob.Stage) -> dict:
    left, top, right = OPENING
    table_back = float(stage.project([(0, 0, TABLE_BACK_Z)])[0][1])
    bottom = table_back - 26 * UNIT
    inner = (left + FRAME, top + FRAME, right - FRAME, bottom - FRAME)
    mid = (left + right) / 2
    panes = [(inner[0], inner[1], mid - MULLION / 2, TRANSOM_Y - MULLION / 3),
             (mid + MULLION / 2, inner[1], inner[2], TRANSOM_Y - MULLION / 3),
             (inner[0], TRANSOM_Y + MULLION / 3, mid - MULLION / 2, inner[3]),
             (mid + MULLION / 2, TRANSOM_Y + MULLION / 3, inner[2], inner[3])]
    return dict(opening=(left, top, right, bottom), panes=panes, table_back=table_back, mid=mid)


def rect(x0, y0, x1, y1) -> np.ndarray:
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)


def paint_wall(canvas: pk.Canvas, win: dict) -> None:
    wall = canvas.layer("wall")
    bd.wash(wall, list(WALL), scale=420 * UNIT, seed=3)
    # Tiles beside the window, old and a little uneven.
    shape = canvas.shape
    left, top, right, bottom = win["opening"]
    tiles = np.zeros(shape, np.float32)
    tile = 46 * UNIT
    for y in np.arange(bottom - tile * 6, HEIGHT, tile):
        tiles = np.maximum(tiles, pk.stroke_mask(shape, (pk.resample(rect(0, y, WIDTH, y)[:2], 4), 1.4 * UNIT)))
    for x in np.arange(0, WIDTH, tile):
        tiles = np.maximum(tiles, pk.stroke_mask(shape, (pk.resample(np.array([[x, bottom - tile * 6], [x, HEIGHT]],
                                                                              np.float32), 4), 1.4 * UNIT)))
    lower = pk.fill_mask(shape, rect(0, bottom - tile * 6, WIDTH, HEIGHT))
    wall.paint(lower, "#3c4556", 0.6)
    wall.paint(tiles * lower, "#262b36", 0.7)
    # Window recess: the thick wall shows its inner sides, lit by the glass.
    recess = 22 * UNIT
    sides = [np.array([[left - recess, top - recess], [left, top], [left, bottom], [left - recess, bottom]]),
             np.array([[right + recess, top - recess], [right, top], [right, bottom], [right + recess, bottom]]),
             np.array([[left - recess, top - recess], [right + recess, top - recess], [right, top], [left, top]])]
    wall.paint(pk.fill_mask(shape, sides), "#5a6274")
    wall.paint(pk.fill_mask(shape, sides[:2]) * pk.linear_ramp(shape, (0, top), (0, bottom)), "#6c7588", 0.5)


def paint_window(canvas: pk.Canvas, win: dict) -> np.ndarray:
    """Glass panes with the outside, frost, sash frames and the sill. Returns the glass mask."""
    shape = canvas.shape
    glass = pk.fill_mask(shape, [rect(*pane) for pane in win["panes"]])
    layer = canvas.layer("outside")
    layer.paint(glass, outside_view())
    # Frost creeps up from the bottom of each pane.
    frost = np.zeros(shape, np.float32)
    grain = pk.smoothstep(0.45, 0.75, pk.noise(shape, 26 * UNIT, seed=SEED, octaves=3))
    for x0, y0, x1, y1 in win["panes"]:
        rise = pk.linear_ramp(shape, (0, y1), (0, y1 - (y1 - y0) * 0.35))
        frost = np.maximum(frost, pk.fill_mask(shape, rect(x0, y0, x1, y1)) * (1.0 - rise) * grain)
    layer.paint(pk.blur(frost, 2 * UNIT), "#cfd8e6", 0.45)
    sheen = pk.linear_ramp(shape, (win["opening"][0], win["opening"][1]), (win["opening"][2], win["opening"][3]))
    layer.paint(glass * (1.0 - sheen) ** 3, "#ffffff", 0.08)
    # Frames: everything in the opening that is not glass.
    left, top, right, bottom = win["opening"]
    frame = pk.fill_mask(shape, rect(left, top, right, bottom)) * (1.0 - glass)
    wood = canvas.layer("frame")
    wood.paint(frame, "#7f8592")
    wood.paint(np.clip(pk.blur(glass, 3 * UNIT) - glass, 0.0, 1.0) * frame * 3.0, COLD, 0.35)
    # The small upper-left vent pane (fortochka) has its own sash.
    x0, y0, x1, y1 = win["panes"][0]
    sash = 9 * UNIT
    corners = rect(x0 - sash, y0 - sash, x1 + sash, y1 + sash)
    edges = [(pk.resample(np.array([corners[i], corners[(i + 1) % 4]]), 8), 1.6 * UNIT) for i in range(4)]
    wood.paint(pk.stroke_mask(shape, edges), LINE, 0.6)
    for y in (y1 - 40 * UNIT, win["panes"][2][1] + 160 * UNIT):       # latches
        latch = rect(win["mid"] - 5 * UNIT, y, win["mid"] + 5 * UNIT, y + 26 * UNIT)
        wood.paint(pk.fill_mask(shape, latch), "#5b5446")
    wood.paint(lt.outline_mask(frame, 1.5 * UNIT), LINE, 0.55)
    # Sill: a board across the bottom of the opening, lit from the glass.
    sill = pk.fill_mask(shape, rect(left - 34 * UNIT, bottom - 4 * UNIT, right + 34 * UNIT, win["table_back"] + 2))
    wood.paint(sill, "#8d929c")
    wood.paint(sill * pk.linear_ramp(shape, (0, bottom), (0, win["table_back"])), "#5d6370", 0.6)
    wood.paint(lt.outline_mask(sill, 1.5 * UNIT), LINE, 0.5)
    return glass


def paint_curtain(canvas: pk.Canvas, win: dict) -> None:
    """Sheer tulle on the right: folds as soft stripes over the glass."""
    shape = canvas.shape
    left, top, right, bottom = win["opening"]
    x0, x1 = right - 210 * UNIT, right + 40 * UNIT
    ys = np.linspace(top - 30 * UNIT, bottom, 40)
    edge = x0 + 18 * UNIT * np.sin(ys / (90 * UNIT))
    body = pk.fill_mask(shape, np.vstack([np.stack([edge, ys], 1), [[x1, bottom], [x1, top - 30 * UNIT]]]))
    layer = canvas.layer("curtain")
    layer.paint(body, "#d9dee8", 0.18)
    folds = []
    for x in np.arange(x0 + 10 * UNIT, x1, 22 * UNIT):
        path = np.stack([x + 6 * UNIT * np.sin(ys / (60 * UNIT) + x), ys], 1)
        folds.append((pk.resample(path.astype(np.float32), 30), 5 * UNIT))
    layer.paint(pk.blur(pk.stroke_mask(shape, folds), 3 * UNIT) * body, "#e8ecf3", 0.22)
    rod = np.array([[left - 60 * UNIT, top - 32 * UNIT], [right + 60 * UNIT, top - 32 * UNIT]], np.float32)
    layer.paint(pk.stroke_mask(shape, (pk.resample(rod, 8), 4 * UNIT)), "#2a2c33")


# -- the table and what stands on it ----------------------------------------------
def paint_table(canvas: pk.Canvas, stage: ob.Stage, win: dict) -> None:
    layer = canvas.layer("table")
    faces = ob.box(stage, layer, center=(0, -3, -10), size=(220, 3, 2 * (TABLE_BACK_Z + 10)), color="#5e6a7c")
    top = faces["top"]
    cells = ob.grid(top, (0.0, 0.0, 1.0, 1.0), columns=22, rows=9, gap=0.0)
    checks = [cell for index, cell in enumerate(cells) if (index // 22 + index % 22) % 2 == 0]
    layer.paint(pk.fill_mask(canvas.shape, checks, ss=2) * top.mask(), "#738098", 0.55)   # oilcloth checks
    # Cold light from the window pools on the far half of the table.
    pool = pk.radial_ramp(canvas.shape, (win["mid"], win["table_back"]), 620 * UNIT, aspect=0.32)
    layer.paint(pool * top.mask(), COLD, 0.25)
    near = pk.linear_ramp(canvas.shape, (0, win["table_back"]), (0, HEIGHT))
    layer.paint(top.mask() * near, "#1c212c", 0.55)


def footprint(center, size) -> list:
    cx, cy, cz = center
    w, h, d = size
    return [(cx + sx * w / 2, cy + y, cz + sz * d / 2) for sx in (-1, 1) for sz in (-1, 1) for y in (0, h)]


def paint_shadows(canvas: pk.Canvas, stage: ob.Stage) -> None:
    layer = canvas.layer("shadows", mode="multiply")
    tea = TEA["center"]
    for corners in (footprint(RADIO["center"], RADIO["size"]),
                    footprint(tea, (TEA["radius"] * 2, TEA["glass"], TEA["radius"] * 2)),
                    footprint(ASHTRAY["center"], (ASHTRAY["radius"] * 2, ASHTRAY["height"], ASHTRAY["radius"] * 2)),
                    footprint(PACK["center"], PACK["size"]), footprint(MATCHES["center"], MATCHES["size"])):
        layer.paint(stage.ground_shadow(corners, softness=8 * UNIT), "#3a3f52", 0.65)


def ink(canvas: pk.Canvas, layer: pk.Layer, mask: np.ndarray) -> None:
    """Illust treatment for an object: cold rim from the window, then the ink line."""
    layer.paint(lt.rim(mask, RIM_LIGHT, 3 * UNIT, 1.5 * UNIT), COLD, 0.55)
    layer.paint(lt.outline_mask(mask, 2.0 * UNIT), LINE, 0.7)


def face_ellipse(face: ob.Face, cu, cv, ru, rv, n: int = 40) -> np.ndarray:
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return face.at(np.stack([cu + ru * np.cos(a), cv + rv * np.sin(a)], 1))


def paint_radio(canvas: pk.Canvas, stage: ob.Stage) -> None:
    """Portable radio cassette player: speakers, cassette door, lit tuning dial, handle, antenna."""
    shape = canvas.shape
    layer = canvas.layer("radio")
    cx, cy, cz = RADIO["center"]
    w, h, d = RADIO["size"]
    antenna = stage.project([(cx + w / 2 - 2, h, cz + 2), (cx + w / 2 + 9, h + 26, cz + 8)])
    layer.paint(pk.stroke_mask(shape, (pk.resample(antenna, 10), 0.35 * PIXELS_PER_CM)), "#a3a8b0")
    layer.paint(pk.fill_mask(shape, pk.ellipse(*antenna[1], 0.5 * PIXELS_PER_CM, 0.5 * PIXELS_PER_CM)), "#c3c8d0")
    handle = stage.project([(cx - w / 2 + 3, h, cz), (cx - w / 2 + 5, h + 4.5, cz), (cx + w / 2 - 5, h + 4.5, cz),
                            (cx + w / 2 - 3, h, cz)])
    layer.paint(pk.stroke_mask(shape, (pk.resample(pk.spline(handle), 30), 1.3 * PIXELS_PER_CM)), "#1a1b20")
    faces = ob.box(stage, layer, RADIO["center"], RADIO["size"], "#2a2b31", edge=0.25)
    front, top = faces["front"], faces["top"]
    mask = np.maximum.reduce([face.mask() for face in faces.values()])
    for cu in (0.17, 0.83):                          # speakers with a dotted grille
        cone = pk.fill_mask(shape, face_ellipse(front, cu, 0.58, 0.13, 0.39))
        layer.paint(cone, "#18191e")
        dots = ob.grid(front, (cu - 0.12, 0.22, cu + 0.12, 0.94), columns=9, rows=9, gap=0.55, radius=0.2)
        layer.paint(pk.fill_mask(shape, dots, ss=2) * cone, "#4a4d56")
    layer.paint(pk.fill_mask(shape, front.rect(0.35, 0.30, 0.65, 0.88, radius=0.3)), "#80848c")      # door
    layer.paint(pk.fill_mask(shape, front.rect(0.38, 0.40, 0.62, 0.70, radius=0.2)), "#1d1f25")      # window
    layer.paint(pk.fill_mask(shape, front.rect(0.44, 0.50, 0.56, 0.60)), "#4a3428")                  # tape
    for cu in (0.445, 0.555):
        layer.paint(pk.fill_mask(shape, face_ellipse(front, cu, 0.55, 0.028, 0.085)), "#c9ccd2")
        layer.paint(pk.fill_mask(shape, face_ellipse(front, cu, 0.55, 0.011, 0.033)), "#1d1f25")
    dial = front.rect(0.32, 0.08, 0.68, 0.22, radius=0.2)                                            # lit dial
    layer.paint(pk.fill_mask(shape, dial), "#e0a052")
    ticks = [front.rect(u, 0.11, u + 0.004, 0.19) for u in np.linspace(0.35, 0.65, 16)]
    layer.paint(pk.fill_mask(shape, ticks, ss=2), "#6a3a1a", 0.8)
    layer.paint(pk.fill_mask(shape, front.rect(0.51, 0.09, 0.515, 0.21)), "#b3261e")
    keys = ob.grid(top, (0.36, 0.25, 0.64, 0.75), columns=6, rows=1, gap=0.3, radius=0.2)
    for index, key in enumerate(keys):
        layer.paint(pk.fill_mask(shape, key, ss=2), "#b3261e" if index == 0 else "#a6a9b0")
    ink(canvas, layer, mask)
    glow = canvas.layer("radio_glow", mode="screen")
    glow.paint(pk.radial_ramp(shape, front.at([[0.5, 0.15]])[0], 90 * UNIT, aspect=0.5), WARM, 0.35)


def paint_tea(canvas: pk.Canvas, stage: ob.Stage) -> None:
    """Glass of tea in a metal holder, a spoon left in it."""
    shape = canvas.shape
    cx, cy, cz = TEA["center"]
    r = TEA["radius"]
    layer = canvas.layer("tea")
    spoon = stage.project([(cx - 0.6, TEA["tea"] - 1, cz + 0.5), (cx - 3.0, TEA["glass"] + 4.5, cz - 1.5)])
    layer.paint(pk.stroke_mask(shape, (pk.resample(spoon, 8), 0.45 * PIXELS_PER_CM)), "#b5b9c0")
    clear = ob.cylinder(stage, layer, (cx, 0.4, cz), r, TEA["glass"] - 0.4, "#9aa6b4", top_color="#b8c3d0")
    tea = ob.cylinder(stage, layer, (cx, 0.4, cz), r * 0.93, TEA["tea"] - 0.4, "#8a4214", top_color="#5a260a")
    layer.paint(tea["mask"], "#a8541c", 0.25)
    rim = pk.stroke_mask(shape, (pk.resample(np.vstack([clear["top"], clear["top"][:1]]), 64), 0.9 * UNIT))
    layer.paint(rim, "#e4ecf4", 0.8)
    holder = ob.cylinder(stage, layer, (cx, 0, cz), r * 1.06, TEA["holder"], "#8f8a80", taper=0.86)
    for y in (0.9, TEA["holder"] - 0.6):         # rolled bands of the holder
        ring = stage.project([(cx + np.cos(a) * r * 1.07, y, cz + np.sin(a) * r * 1.07)
                              for a in np.linspace(np.pi, 2 * np.pi, 24)])
        layer.paint(pk.stroke_mask(shape, (pk.resample(ring, 24), 0.35 * PIXELS_PER_CM)), "#5d5850")
    lattice = []
    for a in np.linspace(np.pi * 1.1, np.pi * 1.9, 7):
        lattice.append((pk.resample(stage.project([(cx + np.cos(a) * r * 1.07, 1.4, cz + np.sin(a) * r * 1.07),
                                                   (cx + np.cos(a) * r * 1.07, TEA["holder"] - 1.1,
                                                    cz + np.sin(a) * r * 1.07)]), 6), 0.25 * PIXELS_PER_CM))
    layer.paint(pk.stroke_mask(shape, lattice), "#5d5850", 0.8)
    handle = stage.project([(cx + r + 0.2, 1.5, cz), (cx + r + 2.4, 2.2, cz), (cx + r + 2.6, 4.6, cz),
                            (cx + r + 0.2, 5.4, cz)])
    layer.paint(pk.stroke_mask(shape, (pk.resample(pk.spline(handle), 20), 0.6 * PIXELS_PER_CM)), "#7c776e")
    ink(canvas, layer, np.maximum(clear["mask"], holder["mask"]))


def paint_ashtray(canvas: pk.Canvas, stage: ob.Stage) -> np.ndarray:
    """Pressed-glass ashtray with two stubs, ash, and a lit cigarette resting on the rim.
    Returns the tip of the lit cigarette in pixels."""
    shape = canvas.shape
    cx, cy, cz = ASHTRAY["center"]
    r, h = ASHTRAY["radius"], ASHTRAY["height"]
    layer = canvas.layer("ashtray")
    body = ob.cylinder(stage, layer, ASHTRAY["center"], r, h, "#6f7c88", top_color="#a7b3be", taper=0.92)
    bowl = stage.project([(cx + np.cos(a) * r * 0.72, h * 0.45, cz + np.sin(a) * r * 0.72)
                          for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)])
    layer.paint(pk.fill_mask(shape, bowl), "#3c434e")
    ob.pebble(stage, layer, (cx - 1.0, h * 0.45, cz + 0.8), (4.2, 0.7, 3.0), "#8b8a88")           # ash
    width = 0.8 * PIXELS_PER_CM
    for base, tip in (((cx - 3.2, h * 0.5, cz + 1.8), (cx - 1.4, h * 0.55, cz + 2.6)),
                      ((cx + 1.2, h * 0.5, cz + 2.4), (cx + 2.8, h * 0.6, cz + 1.0))):          # stubbed out
        pr.paint_cigarette(layer, *stage.project([base, tip]), width, LINE, 0.5)
        layer.paint(pk.radial_ramp(shape, stage.project([tip])[0], width * 1.4), "#2a2826", 0.8)  # crushed end
    base, tip = stage.project([(cx + r + 4.0, h + 0.1, cz - r * 0.55), (cx + 1.0, h * 0.85, cz - 0.6)])
    pr.paint_cigarette(layer, base, tip, width, LINE, 0.6)
    ink(canvas, layer, body["mask"])
    glow = canvas.layer("ember_glow", mode="screen")
    glow.paint(pk.radial_ramp(shape, tip, 70 * UNIT, aspect=0.6), WARM, 0.35)
    return tip


def paint_pack_and_matches(canvas: pk.Canvas, stage: ob.Stage) -> None:
    """A plain cigarette pack (no brand) and a box of matches lying on the cloth."""
    shape = canvas.shape
    layer = canvas.layer("pack")
    faces = ob.box(stage, layer, PACK["center"], PACK["size"], "#d3cdbf", edge=0.3)
    top = faces["top"]
    layer.paint(pk.fill_mask(shape, top.rect(0.0, 0.0, 1.0, 0.30)), "#93302a")
    layer.paint(pk.fill_mask(shape, face_ellipse(top, 0.5, 0.56, 0.16, 0.10)), "#b49a5a")
    ob.text_lines(top, layer, (0.2, 0.74, 0.8, 0.92), rows=2, colors=("#5a5048",), seed=SEED, indent=False)
    pack = np.maximum.reduce([face.mask() for face in faces.values()])
    ink(canvas, layer, pack)
    faces = ob.box(stage, layer, MATCHES["center"], MATCHES["size"], "#c4a06a", edge=0.3)
    layer.paint(pk.fill_mask(shape, faces["top"].rect(0.12, 0.10, 0.88, 0.90)), "#36598c")
    layer.paint(pk.fill_mask(shape, faces["top"].rect(0.30, 0.35, 0.70, 0.62)), "#e8e2d4")
    if "right" in faces:
        layer.paint(pk.fill_mask(shape, faces["right"].rect(0.08, 0.2, 0.92, 0.8)), "#5a3a26")       # striker
    ink(canvas, layer, np.maximum.reduce([face.mask() for face in faces.values()]))


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "doomer_still_life.png"
    canvas = pk.Canvas(WIDTH, HEIGHT)
    stage = ob.Stage(canvas.shape, TABLE_ORIGIN, PIXELS_PER_CM, yaw=10, pitch=16, light=WORLD_LIGHT)
    win = window_geometry(stage)
    paint_wall(canvas, win)
    paint_window(canvas, win)
    paint_curtain(canvas, win)
    paint_table(canvas, stage, win)
    paint_shadows(canvas, stage)
    # Back to front: larger z (farther from the viewer) first.
    paint_radio(canvas, stage)
    paint_tea(canvas, stage)
    paint_pack_and_matches(canvas, stage)
    tip = paint_ashtray(canvas, stage)
    smoke = canvas.layer("smoke")
    pr.smoke(smoke, tip, 560 * UNIT, 3.0 * UNIT, seed=SEED, color="#cdd5e0", opacity=0.6, drift=-0.12)
    pr.smoke(smoke, tip, 380 * UNIT, 2.0 * UNIT, seed=SEED + 1, color="#cdd5e0", opacity=0.45, drift=0.08)
    image = scene.finish(canvas, None, {"style": "illust", "finish": {"preset": "doomer"}, "seed": SEED})
    pk.save(image, out)
    print(f"[ok] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
