"""Worked example: a kitchen windowsill late at night, for doomer.py.

Usage: python doomer_still_life.py <anime|illust|painterly> <output.png> [width_px]
(doomer.py draws it with the doomer grade: python doomer.py <style> <out> <width> still_life)

An old painted window looks across the yard at a prefab block with a few lit windows,
snow falling outside. On the sill: tea in a glass in a metal holder, an ashtray with a
cigarette still burning, a cassette tape leaning on the frame. Painting order is back
to front: the view outside, the wall with the window opening cut out, the frame, the
sill and radiator, then the objects.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atelier import STYLES, Art, ellipse, spline, symmetric  # noqa: E402
from head_props import draw_cigarette, draw_smoke  # noqa: E402
from scenes import panel_block, snowfall  # noqa: E402

# ---- plan -------------------------------------------------------------------------------
ASPECT = 0.8
LIGHT = (-0.65, -0.45, 0.62)       # a kitchen lamp off the frame, upper left
OPENING = (150.0, -20.0, 850.0, 515.0)       # window opening in the wall: left, top, right, bottom
FRAME = 28.0                       # width of the frame's bars
MULLION_X, TRANSOM_Y = 500.0, 150.0
VENT = (178.0, 8.0, 486.0, 136.0)  # the small vent pane inside the upper left pane
SILL_TOP = ((100, 515), (900, 515), (935, 588), (65, 588))
SILL_FRONT = ((65, 588), (935, 588), (935, 614), (65, 614))
RADIATOR = (292.0, 652.0, 712.0, 34.0)       # left, top, right, rib spacing
BLOCK_ACROSS = ((40.0, 140.0, 980.0, 720.0), 11, 16, (2, 3, 7, 8, 12, 13))   # box, floors, columns, balconies
GLASS_AT, ASHTRAY_AT, CASSETTE_AT = (330.0, 566.0), (540.0, 574.0), (800.0, 566.0)
CASSETTE_LEAN = -6.0               # degrees: leaning back against the frame
RESTING_DROOP = -14.0              # the cigarette rests on the rim, tip raised
SHADOW_SHIFT = (34.0, 6.0)         # cast shadows fall to the right, away from the lamp
OBJECT_FOCUS = 0.7

PALETTE = {
    "night": "#0E1320", "night_low": "#2B2836", "street_glow": "#FFA858",
    "wall": "#38403B", "wall_low": "#232925", "lamp": "#E3A262", "frame": "#C9C3B6", "frame_shadow": "#8E8A88",
    "sill": "#C3BEB2", "sill_front": "#9C978E", "radiator": "#B5B0A4", "frost": "#DCE5EF",
    "metal": "#8F929B", "metal_dark": "#4E5059", "glass": "#B9C6CC", "tea": "#7E3F16", "tea_top": "#5A2A0E",
    "ash_glass": "#6E7B86", "ash": "#5C5C60", "butt": "#C99A62", "paper": "#EDEAE2",
    "shell": "#2B2C32", "label": "#D9D3C1", "stripe": "#C2553A", "reel": "#EDEBE6", "tape": "#4A2E22",
    "ink": "#2A2A30", "tulle": "#E8EBF0", "shadow": "#20231F",
}


def _rect(left, top, right, bottom):
    return np.array([(left, top), (right, top), (right, bottom), (left, bottom)], float)


def draw_outside(art):
    """The night beyond the glass: sky, the block across the yard, a lamp's glow, snow."""
    art.paint(art.everywhere(), PALETTE["night"])
    art.paint(art.ramp((0, 0), (0, OPENING[3])), PALETTE["night_low"])
    box, floors, columns, balconies = BLOCK_ACROSS
    panel_block(art, box, floors, columns, balconies=balconies, lit=(0.2, 0.06))
    art.light(art.blob((790, 470), 170), PALETTE["street_glow"], 0.35)
    art.blur(2)
    snowfall(art)


def draw_wall(art):
    """The kitchen wall round the opening, warm near the lamp, darker low down."""
    wall = 1 - art.shape(_rect(*OPENING))
    art.paint(wall, PALETTE["wall"])
    art.paint(wall * art.ramp((0, 500), (0, 800)), PALETTE["wall_low"], 0.7)
    art.light(wall * art.blob((-120, 260), 760), PALETTE["lamp"], 0.35)
    return wall


def draw_window(art):
    """Painted wooden frame, a vent pane, frost in the pane corners, a tulle curtain."""
    left, top, right, bottom = OPENING
    half = FRAME / 2
    panes = art.shape(_rect(*OPENING))
    for corner in ((left, bottom), (right, bottom), (MULLION_X, bottom), (MULLION_X, TRANSOM_Y)):
        art.light(art.feather(art.shape(ellipse(*corner, 90, 60)), 40) * panes, PALETTE["frost"], 0.35)
    for start, end in (((560, 40), (700, 300)), ((610, 40), (720, 240))):          # glass catches the lamp
        art.light(art.feather(art.brush(np.array([start, end], float), 14), 8) * panes, PALETTE["frost"], 0.12)
    bars = [_rect(left, top, left + FRAME, bottom), _rect(right - FRAME, top, right, bottom),
            _rect(left, bottom - FRAME, right, bottom), _rect(MULLION_X - half, top, MULLION_X + half, bottom),
            _rect(left, TRANSOM_Y - half, MULLION_X, TRANSOM_Y + half)]
    frame = art.part(art.shapes(bars), PALETTE["frame"], bulge=8, shadow_tint=PALETTE["frame_shadow"])
    vent_left, vent_top, vent_right, vent_bottom = VENT
    vent = art.shapes([_rect(vent_left, vent_top, vent_right, vent_top + 14),
                       _rect(vent_left, vent_bottom - 14, vent_right, vent_bottom),
                       _rect(vent_left, vent_top, vent_left + 14, vent_bottom),
                       _rect(vent_right - 14, vent_top, vent_right, vent_bottom)])
    art.part(vent, PALETTE["frame"], bulge=5, shadow_tint=PALETTE["frame_shadow"])
    art.part(art.shape(ellipse(MULLION_X + 22, 330, 6, 16)), PALETTE["metal"], bulge=4)     # latch
    for x in np.arange(96, 270, 26):                                   # tulle: soft vertical folds
        fold = spline([(x, -20), (x + 6, 200), (x - 4, 400), (x + 3, 520)])
        art.light(art.feather(art.brush(fold, 16), 8), PALETTE["tulle"], 0.10)
    return frame


def draw_sill(art):
    top = art.part(np.array(SILL_TOP, float), PALETTE["sill"], shade=False)
    art.shadow(top * (1 - art.ramp((0, 515), (0, 545))), PALETTE["shadow"], 0.35)
    art.part(np.array(SILL_FRONT, float), PALETTE["sill_front"], shade=False)
    left, rib_top, right, spacing = RADIATOR
    ribs = [np.array(spline([(x, rib_top + 14, True), (x + 4, rib_top), (x + spacing - 10, rib_top),
                             (x + spacing - 6, rib_top + 14, True), (x + spacing - 6, art.units_high + 10, True),
                             (x, art.units_high + 10, True)], closed=True))
            for x in np.arange(left, right, spacing)]
    art.part(art.shapes(ribs), PALETTE["radiator"], bulge=10)
    art.shadow(art.shape(_rect(left - 20, 614, right + 20, 640)), PALETTE["shadow"], 0.5)
    return top


def cast_shadow(art, sill, width):
    shadow = art.shape(ellipse(SHADOW_SHIFT[0], SHADOW_SHIFT[1] - 4, width * 0.6, 12))
    art.shadow(art.feather(shadow, 5) * sill, PALETTE["shadow"], 0.7)


def draw_tea(art):
    """Tea in a glass, in a metal holder with a handle and a pierced band; spoon left in."""
    glass = art.shape(_rect(-34, -152, 34, -60))
    art.paint(glass, PALETTE["glass"], 0.35)
    tea = art.shape(_rect(-34, -128, 34, -60))
    art.part(tea, PALETTE["tea"], bulge=20, outline=False)
    art.paint(art.shape(ellipse(0, -128, 34, 6)), PALETTE["tea_top"])
    art.mark(np.array([(8, -126), (46, -206)], float), PALETTE["metal"], 4, "end")          # spoon handle
    art.line(spline([(-34, -152), (-34, -60)]), width=1.4)
    art.line(spline([(34, -152), (34, -60)]), width=1.4)
    art.light(art.brush(np.array([(-22, -146), (-22, -70)], float), 5) * glass, "#FFFFFF", 0.6)
    handle = art.tube([(40, -70, 9), (66, -64, 9), (70, -40, 9), (60, -22, 8), (40, -20, 8)])
    art.part(handle, PALETTE["metal"], bulge=6, shadow_tint=PALETTE["metal_dark"])
    sleeve = [(0, -78), (40, -78, True), (37, -68), (35, -16), (40, -8), (46, 0, True), (0, 0)]
    holder = art.part(spline(symmetric(sleeve, 0), closed=True), PALETTE["metal"], bulge=30,
                      shadow_tint=PALETTE["metal_dark"])
    holes = [ellipse(x, -44, 4, 12) for x in np.arange(-26, 30, 13)]
    art.paint(art.shapes(holes) * holder, PALETTE["metal_dark"], 0.9)
    art.light(art.brush(np.array([(-24, -74), (-26, -6)], float), 6) * holder, "#FFFFFF", 0.55)
    return np.maximum.reduce([glass, handle, holder])


def draw_ashtray(art):
    """A round glass ashtray with two stubbed-out butts and a cigarette burning on the rim."""
    side = art.part(spline([(-74, -22, True), (74, -22, True), (66, -2), (0, 3), (-66, -2)], closed=True),
                    PALETTE["ash_glass"], bulge=16)
    art.part(art.shape(ellipse(0, -22, 74, 17)), PALETTE["ash_glass"], bulge=6)
    art.paint(art.shape(ellipse(0, -21, 58, 11)), PALETTE["ash"])
    for start, end in (((-40, -22), (-12, -18)), ((-8, -26), (20, -20))):
        art.mark(np.array([start, end], float), PALETTE["paper"], 6, "none")
        art.mark(np.array([start, (start[0] + 9, start[1] + 1)], float), PALETTE["butt"], 6, "none")
    art.light(art.brush(spline([(-60, -26), (-20, -36), (30, -36)]), 4), "#FFFFFF", 0.5)
    identity = np.asarray
    tip = draw_cigarette(art, identity, (40, -30), droop=RESTING_DROOP)
    draw_smoke(art, identity, tip, drift=-50.0)
    return side


def draw_cassette(art):
    """A cassette tape standing on its edge: shell, label with a stripe, reels in the window."""
    shell = art.part(spline([(-75, -94, True), (75, -94, True), (75, 0, True), (-75, 0, True)], closed=True),
                     PALETTE["shell"], bulge=10)
    label = art.shape(_rect(-66, -86, 66, -32))
    art.paint(label, PALETTE["label"])
    art.paint(art.shape(_rect(-66, -46, 66, -38)), PALETTE["stripe"])
    for y, length in ((-76, 70), (-66, 44)):                            # pencilled title
        art.mark(spline([(-52, y), (-52 + length / 2, y - 2), (-52 + length, y)]), PALETTE["ink"], 1.6, "end")
    art.paint(art.shape(_rect(-42, -64, 42, -46)), PALETTE["shell"])
    for x in (-26, 26):
        art.paint(art.shape(ellipse(x, -55, 13, 13)), PALETTE["tape"])
        art.paint(art.shape(ellipse(x, -55, 6, 6)), PALETTE["reel"])
    art.part(art.shape(np.array([(-46, -22), (46, -22), (52, 0), (-52, 0)], float)), PALETTE["shell"], bulge=4)
    art.paint(art.shapes([ellipse(x, -10, 3, 3) for x in (-30, -12, 12, 30)]), PALETTE["ink"])
    return shell


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=31)
    draw_outside(art)
    draw_wall(art)
    draw_window(art)
    sill = draw_sill(art)
    for draw_object, at, angle, shadow_width in ((draw_cassette, CASSETTE_AT, CASSETTE_LEAN, 150),
                                                 (draw_tea, GLASS_AT, 0.0, 90),
                                                 (draw_ashtray, ASHTRAY_AT, 0.0, 150)):
        with art.place(at=at, angle=angle):
            cast_shadow(art, sill, shadow_width)
            art.focus_on(art.feather(draw_object(art), 6) * OBJECT_FOCUS)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    draw(style_name, width).save(output)
    print(f"saved {output}")
