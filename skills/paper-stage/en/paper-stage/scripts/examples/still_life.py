"""Example: a table-top still life (bottle, bowl of fruit, pear, drapery).

Shows how rounded objects are built: a symmetric profile for anything turned on a
wheel, plain ellipses for fruit, a rim ellipse to open the top of a vessel.

Usage: python examples/still_life.py --style painterly|illust|anime --out still_life.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, fx, geometry as geo, shading as sh
from codepainter.color import light_of, mix, shadow_of
from codepainter.styles import finish, get_style, gloss, line_color, paint_part, shade_form

WIDTH, HEIGHT = 1280, 900
TABLE_Y = 500                       # back edge of the table
LIGHT = (-0.62, -0.50, 0.60)        # window on the left
WALL, CLOTH, WOOD = "#3a3230", "#d9cdb8", "#6a4630"


def cast(painting, mask, table, strength=0.55):
    """Every object anchors itself with a shadow thrown to the right, away from the window."""
    painting.fill(sh.ground_shadow(mask, lean=0.55, squash=0.20, softness=6.0) * table * (1.0 - mask),
                  "#2a2030", strength, "multiply")


def fruit(painting, style, table, center, radius_x, radius_y, color, stem=True, spot=0.8):
    curve = geo.ellipse(center, radius_x, radius_y, count=72)
    mask = painting.mask(curve)
    cast(painting, mask, table)
    paint_part(painting, curve, color, style, LIGHT, line_width=3.0)
    # light bouncing up from the cloth warms the lower edge inside the shadow
    painting.fill(sh.rim(mask, (0.5, 0.8), radius_x * 0.16, radius_x * 0.08), light_of(color, "#ffd9a8", 0.55), 0.45)
    gloss(painting, mask, LIGHT, size=0.14, color="#fff6e6", opacity=spot, softness=0.15 + 0.5 * style.gradient)
    if stem:
        top = (center[0] + radius_x * 0.05, center[1] - radius_y * 0.86)
        dimple = painting.mask(geo.ellipse(top, radius_x * 0.26, radius_y * 0.10))
        painting.fill(sh.blur(dimple, 3.0) * mask, shadow_of(color), 0.7)
        painting.stroke(geo.bent_line(top, (top[0] + radius_x * 0.22, top[1] - radius_y * 0.42), 0.2), radius_x * 0.07,
                        "#4a3320", taper=(0.0, 0.5), layer="color")
    return mask


def paint_room(painting, style):
    backdrop.gradient(painting, mix(WALL, "#5a4a40", 0.6), WALL, start=(0, 0), end=(WIDTH, TABLE_Y))
    backdrop.mottle(painting, "#5d5046", amount=0.35, scale=0.9, seed=2)
    backdrop.glow(painting, (WIDTH * 0.05, HEIGHT * 0.25), HEIGHT * 0.7, "#ffdcae", opacity=0.30)
    backdrop.window_light(painting, (WIDTH * 0.50, HEIGHT * 0.04), (WIDTH * 0.30, HEIGHT * 0.42), slant=0.45,
                          color="#ffe2b0", opacity=0.16, softness=0.0 if style.name == "anime" else 8.0)
    table_curve = np.array([(-10, TABLE_Y), (WIDTH + 10, TABLE_Y), (WIDTH + 10, HEIGHT + 10), (-10, HEIGHT + 10)], dtype=float)
    table = painting.mask(table_curve)
    painting.part(table, WOOD)
    painting.fill(table * sh.linear_ramp(painting.shape, (0, TABLE_Y), (0, HEIGHT)), shadow_of(WOOD), 0.5)
    # a cloth thrown across the table: one big shape, folds as darker and lighter wedges
    cloth_curve = geo.smooth([(120, TABLE_Y - 6), (700, TABLE_Y - 14), (1180, TABLE_Y - 4), (1300, 800), (1290, HEIGHT + 20),
                              (420, HEIGHT + 20), (60, 900), (20, 720)], closed=True)
    cloth = painting.mask(cloth_curve) * table
    painting.part(cloth, CLOTH)
    shade_form(painting, cloth, CLOTH, style, LIGHT, bevel=60, threshold=0.2)
    for start, end in (((300, TABLE_Y + 40), (220, HEIGHT)), ((980, TABLE_Y + 30), (1120, HEIGHT - 60))):
        crease = geo.needle(start, end, 70)                                  # two shallow creases where the cloth was folded
        painting.fill(sh.blur(painting.mask(crease), 14) * cloth, shadow_of(CLOTH, style.shadow_tint), 0.30)
        painting.fill(sh.blur(sh.shift(painting.mask(crease), -40, 0), 12) * cloth, "#fff8ea", 0.30)
    if style.line_width > 0:
        painting.outline(cloth_curve, 2.5 * style.line_width, line_color(style, CLOTH))
    painting.erase_lines(1.0 - table)
    return table


def paint_bottle(painting, style, table):
    axis, base = 330, TABLE_Y + 150
    glass = "#27483a"
    profile = [(22, base - 520), (24, base - 420), (30, base - 360), (78, base - 280), (84, base - 40), (70, base)]
    curve = geo.symmetric(profile, axis)
    mask = painting.mask(curve)
    cast(painting, mask, table, 0.6)
    paint_part(painting, curve, glass, style, LIGHT, line_width=3.0, threshold=0.25)
    # glass: a long window reflection down the lit side, a thin one on the far edge
    painting.fill(sh.blur(sh.rim(mask, (-1.0, 0.0), 26, 0) * sh.shift(mask, 12, 0), 2 + 5 * style.gradient), "#cfe9d6", 0.55)
    painting.fill(sh.rim(mask, (1.0, 0.0), 7, 2), "#8fc3a4", 0.5)
    label = painting.mask(np.array([(axis - 90, base - 220), (axis + 90, base - 220), (axis + 90, base - 110), (axis - 90, base - 110)], dtype=float)) * mask
    painting.fill(label, "#e8dcc0")
    painting.fill(label * sh.linear_ramp(painting.shape, (axis - 10, 0), (axis + 85, 0)), shadow_of("#e8dcc0", style.shadow_tint), 0.75)
    cork = np.array([(axis - 19, base - 552), (axis + 19, base - 552), (axis + 21, base - 516), (axis - 21, base - 516)], dtype=float)
    paint_part(painting, cork, "#b98a58", style, LIGHT, line_width=2.5, bevel=12)
    return mask


def paint_bowl(painting, style, table):
    axis, rim_y, base = 760, TABLE_Y + 70, TABLE_Y + 215
    glaze = "#3b6f8f"
    outer = geo.symmetric([(210, rim_y), (190, rim_y + 70), (120, base - 22), (64, base - 4), (60, base)], axis)
    bowl = painting.mask(outer)
    cast(painting, bowl, table, 0.6)
    inside = painting.mask(geo.ellipse((axis, rim_y), 210, 46))
    painting.part(inside, shadow_of(glaze))                                   # the far inner wall, seen over the rim
    if style.line_width > 0:
        painting.outline_mask(inside, 3.0 * style.line_width, line_color(style, glaze))
    fruits = [
        fruit(painting, style, table, (axis - 96, rim_y - 34), 74, 70, "#b93a2e"),
        fruit(painting, style, table, (axis + 92, rim_y - 30), 70, 66, "#d98a1f", stem=False),
        fruit(painting, style, table, (axis + 2, rim_y - 62), 78, 74, "#c9b03a"),
    ]
    front = bowl * (1.0 - inside) + bowl * inside * (sh.linear_ramp(painting.shape, (0, rim_y - 2), (0, rim_y + 2)))
    front = np.clip(front, 0.0, 1.0)
    painting.part(front, glaze)
    shade_form(painting, front, glaze, style, LIGHT, height=sh.inflate(bowl), threshold=0.25)
    gloss(painting, front, LIGHT, size=0.10, reach=0.55, color="#e6f3ff", opacity=0.7, softness=0.2 + 0.4 * style.gradient)
    painting.fill(sh.rim(front, (0.0, -1.0), 7, 1.5) * inside, light_of(glaze, amount=0.5), 0.8)   # lit lip of the rim
    if style.line_width > 0:
        painting.outline_mask(front, 3.0 * style.line_width, line_color(style, glaze))
    return np.maximum.reduce([bowl] + fruits)


def paint_pear_and_grapes(painting, style, table):
    pear = geo.symmetric([(10, TABLE_Y + 96), (34, TABLE_Y + 130), (44, TABLE_Y + 180), (82, TABLE_Y + 250),
                          (70, TABLE_Y + 312), (20, TABLE_Y + 326)], 1085)
    mask = painting.mask(pear)
    cast(painting, mask, table)
    paint_part(painting, pear, "#a8a83e", style, LIGHT, line_width=3.0)
    gloss(painting, mask, LIGHT, size=0.10, reach=0.35, color="#fbf6d0", opacity=0.7, softness=0.3)
    painting.stroke(geo.bent_line((1087, TABLE_Y + 98), (1104, TABLE_Y + 58), -0.25), 6, "#4a3320", taper=(0.0, 0.4), layer="color")
    rng = np.random.default_rng(11)
    centers = [(520 + column * 34 + (row % 2) * 17 + rng.uniform(-4, 4), TABLE_Y + 248 + row * 26 + rng.uniform(-3, 3))
               for row in range(4) for column in range(5 - row)]
    for center in sorted(centers, key=lambda c: c[1]):                        # nearer grapes overlap farther ones
        fruit(painting, style, table, center, 21, 20, "#5a2f6a", stem=False, spot=0.9)
    painting.stroke(geo.bent_line((560, TABLE_Y + 236), (604, TABLE_Y + 196), 0.3), 5, "#4a3320", taper=(0.2, 0.3), layer="color")


def render(style_name, seed=0):
    style = get_style(style_name)
    painting = Painting(WIDTH, HEIGHT)
    table = paint_room(painting, style)
    painting.snapshot("1 room and cloth")
    paint_bottle(painting, style, table)
    focus = paint_bowl(painting, style, table)
    painting.snapshot("2 bottle and bowl")
    paint_pear_and_grapes(painting, style, table)
    painting.snapshot("3 fruit")
    image = finish(painting, style, seed=seed, importance=focus, detail=1.1)
    painting.stages["4 finish"] = image
    return painting, image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="painterly", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="still_life.png")
    parser.add_argument("--sheet", default=None)
    args = parser.parse_args()
    painting, image = render(args.style)
    painting.save(args.out, image)
    if args.sheet:
        fx.stage_sheet(painting.stages, args.sheet, columns=4)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
