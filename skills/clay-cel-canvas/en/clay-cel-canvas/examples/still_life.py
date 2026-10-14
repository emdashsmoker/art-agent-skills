"""Worked example: still life with bottle, pitcher, fruit and cloth.

Usage: python still_life.py <anime|illust|painterly> <output.png> [width_px]

Each object is drawn in its own coordinates (base centre at the origin) and set
on the table with art.place(), so objects can be moved or resized freely.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atelier import STYLES, Art, ellipse, spline, symmetric  # noqa: E402

# ---- plan -------------------------------------------------------------------
ASPECT = 0.8
LIGHT = (-0.60, -0.50, 0.62)       # window light from the upper left
TABLE_BACK = 470                   # y where the table meets the wall
TABLE_FRONT = 742                  # y of the front edge
SHADOW_SHIFT = (58, 10)            # cast shadows fall to the lower right
OBJECT_FOCUS = 0.7                 # objects stay crisper than wall and table

PALETTE = {
    "wall": "#2B2622", "wall_light": "#6A5744", "table": "#7A4E2E", "table_front": "#4A2D1B",
    "cloth": "#E6DCC8", "cloth_shadow": "#9C8FA6",
    "bottle": "#1E3D2C", "bottle_light": "#9FD0A8",
    "pitcher": "#E9E3D5", "pitcher_band": "#3F5C92",
    "apple": "#B5302A", "apple_blush": "#D9A23B", "pear": "#C7B544", "pear_blush": "#C9773A",
    "lemon": "#EACB3C", "grape": "#5A2B63", "grape_light": "#C7A6E0", "stem": "#5B4326",
    "warm_shadow": "#7D6A7C", "deep_shadow": "#5A4C62",
}


def cast_shadow(art, table, width, depth=16):
    """Shadow of the object at the origin, lying on the table to the lower right."""
    shadow = art.shape(ellipse(SHADOW_SHIFT[0], SHADOW_SHIFT[1] - 4, width * 0.62, depth))
    art.shadow(art.feather(shadow, 5) * table, PALETTE["deep_shadow"], 0.85)


def draw_room(art):
    art.paint(art.everywhere(), PALETTE["wall"])
    art.paint(art.blob((250, 180), 620), PALETTE["wall_light"], 0.75)
    table = art.shape(np.array([(0, TABLE_BACK), (1000, TABLE_BACK), (1000, TABLE_FRONT),
                                (0, TABLE_FRONT)], float))
    art.part(table, PALETTE["table"], shade=False, outline=False)
    art.shadow(table * (1 - art.ramp((0, TABLE_BACK), (0, TABLE_BACK + 60))),
               PALETTE["warm_shadow"], 0.6)
    art.light(table * art.blob((260, 640), 420), "#FFD9A8", 0.25)
    front = np.array([(0, TABLE_FRONT), (1000, TABLE_FRONT), (1000, 800), (0, 800)], float)
    art.part(front, PALETTE["table_front"], shade=False)
    art.light(art.brush(np.array([(0, TABLE_FRONT + 2), (1000, TABLE_FRONT + 2)], float), 5, "none"),
              "#FFD9A8", 0.35)
    return table


def draw_cloth(art, table):
    outline = [(470, 560, True), (560, 528), (700, 512), (860, 510), (1010, 530, True),
               (1010, 810, True), (900, 810), (860, 786), (800, 806), (740, 780), (680, 800),
               (622, 770), (586, 790, True), (560, TABLE_FRONT), (520, 690), (488, 630)]
    cloth = art.part(spline(outline, closed=True), PALETTE["cloth"], bulge=36,
                     shadow_tint=PALETTE["cloth_shadow"])
    # Folds run from under the pitcher toward the table edge, then drop over it.
    folds = ([(610, 560), (650, 650), (636, TABLE_FRONT), (628, 800)],
             [(750, 540), (792, 650), (768, TABLE_FRONT), (772, 800)],
             [(890, 532), (936, 650), (922, TABLE_FRONT), (884, 800)])
    for points in folds:
        curve = spline(points)
        art.shadow(art.feather(art.brush(curve, 30), 4) * cloth, PALETTE["cloth_shadow"], 0.7)
        art.light(art.feather(art.move(art.brush(curve, 16), -24, 0), 4) * cloth, "#FFFFFF", 0.4)
    hanging = cloth * art.ramp((0, TABLE_FRONT - 4), (0, TABLE_FRONT + 8))
    art.shadow(hanging, PALETTE["cloth_shadow"], 0.5)        # the part below the table edge
    return cloth


def draw_bottle(art):
    """Dark glass bottle, 430 tall; origin at the centre of its base."""
    half = [(0, -430), (17, -430, True), (19, -410), (15, -400), (15, -300), (28, -250),
            (58, -205), (62, -150), (62, -14), (52, 0, True), (0, 0)]
    body = art.part(spline(symmetric(half, 0), closed=True), PALETTE["bottle"],
                    shadow_tint=PALETTE["deep_shadow"])
    art.light(art.brush(spline([(-40, -180), (-44, -100), (-40, -24)]), 11) * body,
              PALETTE["bottle_light"], 0.75)
    art.light(art.brush(spline([(-8, -395), (-9, -330), (-14, -262)]), 6) * body,
              PALETTE["bottle_light"], 0.7)
    art.light(art.brush(spline([(46, -170), (49, -90), (45, -20)]), 8) * body,
              "#C98A4A", 0.30)                                 # table colour bouncing back
    art.light(art.shape(ellipse(-36, -196, 6, 12, 20)) * body, "#FFFFFF", 0.9)
    art.mark(np.array([(-17, -412), (17, -412)], float), "#0F2118", 5, "none")
    return body


def draw_pitcher(art):
    """Ceramic pitcher, 250 tall; origin at the centre of its base."""
    handle = art.tube([(70, -200, 20), (132, -190, 22), (150, -130, 20), (118, -70, 18),
                       (82, -62, 16)])
    art.part(handle, PALETTE["pitcher"], bulge=10, shadow_tint=PALETTE["warm_shadow"])
    half = [(0, -250), (58, -250, True), (64, -238), (52, -205), (70, -150), (96, -90),
            (92, -30), (70, 0, True), (0, 0)]
    curve = spline(symmetric(half, 0), closed=True)
    body = art.part(curve, PALETTE["pitcher"], shadow_tint=PALETTE["warm_shadow"])
    spout = art.part(spline([(-52, -252, True), (-92, -262, True), (-58, -215)], closed=True),
                     PALETTE["pitcher"], bulge=10, shadow_tint=PALETTE["warm_shadow"])
    art.erase_line(art.shape(ellipse(-52, -236, 12, 16)))
    band = art.shape(spline([(-110, -128), (0, -112), (110, -128), (110, -98), (0, -82),
                             (-110, -98)], closed=True)) * body
    art.paint(band, PALETTE["pitcher_band"], 0.9)
    art.paint(art.shape(ellipse(0, -247, 55, 9)) * body, "#3A3430", 0.85)   # dark opening
    art.light(art.shape(ellipse(-48, -150, 12, 34, 12)) * body, "#FFFFFF", 0.7)
    return np.maximum.reduce([body, handle, spout])


def draw_apple(art):
    """Apple, radius about 62; origin at the centre of its base."""
    curve = spline([(0, -112), (30, -124), (62, -100), (66, -52), (44, -8), (0, 0), (-44, -8),
                    (-66, -52), (-62, -100), (-30, -124)], closed=True)
    body = art.part(curve, PALETTE["apple"], shadow_tint=PALETTE["deep_shadow"])
    art.paint(art.blob((28, -40), 46) * body, PALETTE["apple_blush"], 0.45)
    art.shadow(art.shape(ellipse(0, -114, 20, 8)) * body, PALETTE["deep_shadow"], 0.7)
    art.mark(spline([(0, -112), (4, -132), (14, -146)]), PALETTE["stem"], 5, "end")
    art.light(art.shape(ellipse(-28, -84, 12, 8, -30)) * body, "#FFFFFF", 0.8)
    art.light(art.brush(spline([(34, -12), (54, -40), (58, -70)]), 7) * body, "#E7A46A", 0.3)
    return body


def draw_pear(art):
    """Pear, 150 tall; origin at the centre of its base."""
    curve = spline([(4, -150), (24, -138), (30, -104), (56, -62), (58, -24), (30, 0), (-24, 0),
                    (-54, -24), (-54, -62), (-24, -104), (-16, -138)], closed=True)
    body = art.part(curve, PALETTE["pear"], shadow_tint=PALETTE["warm_shadow"])
    art.paint(art.blob((26, -44), 50) * body, PALETTE["pear_blush"], 0.4)
    art.mark(spline([(4, -148), (2, -170), (12, -184)]), PALETTE["stem"], 5, "end")
    art.light(art.shape(ellipse(-24, -66, 10, 20, -15)) * body, "#FFFFFF", 0.6)
    return body


def draw_lemon(art):
    """Lemon lying on its side; origin at the centre of its base."""
    curve = spline([(-70, -34, True), (-44, -62), (0, -70), (46, -60), (72, -32, True),
                    (46, -6), (0, 0), (-44, -8)], closed=True)
    body = art.part(curve, PALETTE["lemon"], shadow_tint="#B98A5A")
    art.light(art.shape(ellipse(-20, -50, 18, 8, -8)) * body, "#FFFFFF", 0.65)
    return body


def draw_grapes(art):
    """Bunch of grapes trailing to the right; origin at the base of the bunch."""
    berries = [(x, y) for row, y in enumerate((-12, -34, -56, -76))
               for x in np.arange(-48 + row * 12, 60 - row * 6, 25)]
    berries += [(70, -8), (92, -4), (112, 2)]
    art.mark(spline([(-10, -78), (-22, -104), (-44, -118)]), PALETTE["stem"], 5, "end")
    masks = []
    for x, y in sorted(berries, key=lambda berry: berry[1]):     # back row first
        x, y = x + art.rng.uniform(-3, 3), y + art.rng.uniform(-3, 3)
        berry = art.part(ellipse(x, y, 14, 15), PALETTE["grape"], shadow_tint=PALETTE["deep_shadow"])
        art.light(art.shape(ellipse(x - 5, y - 6, 3.2, 3.2)), PALETTE["grape_light"], 0.9)
        art.light(art.brush(spline([(x + 3, y + 10), (x + 9, y + 5), (x + 11, y - 2)]), 3) * berry,
                  PALETTE["grape_light"], 0.35)
        masks.append(berry)
    return np.maximum.reduce(masks)


# object, table position, scale, shadow width
ARRANGEMENT = (
    (draw_bottle, (330, 610), 1.0, 130),
    (draw_pitcher, (590, 628), 1.0, 190),
    (draw_apple, (170, 668), 1.0, 130),
    (draw_pear, (790, 668), 1.0, 115),
    (draw_lemon, (440, 712), 0.95, 140),
    (draw_grapes, (880, 716), 1.0, 150),
)


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=5)
    table = draw_room(art)
    cloth = draw_cloth(art, table)
    ground = np.maximum(table, cloth)
    for draw_object, position, scale, shadow_width in ARRANGEMENT:
        with art.place(at=position, scale=scale):
            cast_shadow(art, ground, shadow_width)
            art.focus_on(art.feather(draw_object(art), 6) * OBJECT_FOCUS)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
