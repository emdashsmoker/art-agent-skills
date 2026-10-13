"""Painterly (watercolor) example: a teapot, persimmons and grapes (still life).

Process: background wash → table → base wash per object (highlights stay as paper) → shade glazing → cast shadows →
details → watercolor pass.
Watercolor highlights are reserved paper. Leave those spots unpainted from the start.
Run: python watercolor_still_life.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, io, motifs  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402
from codepaint.styles.watercolor import wash  # noqa: E402

WIDTH, HEIGHT = 1200, 900
LIGHT = (-0.7, -0.7)
TABLE_Y = 610

# Palette: the celadon teapot is the largest mass. The orange of the persimmons is its complementary accent,
# and the purple of the grapes links to the shadow color.
BACK_WARM, BACK_COOL = "#e9d6c0", "#c9cfe6"
TABLE, TABLE_DEEP = "#ead9b6", "#c9a878"
POT, POT_DEEP = "#8fc4b4", "#3f7f7a"
PERSIMMON, PERSIMMON_DEEP, CALYX = "#f29a3c", "#c9521f", "#6f8a4a"
GRAPE, GRAPE_DEEP, STEM = "#8a6aa8", "#4a2f6a", "#7a5a3a"
SHADOW = "#7a70a8"


def glazed(cv, outline, base, deep, highlight=None, shadow=0.45, soft=2.0, rough=2.5):
    """One round object: base wash without the highlight area → mottling → shade glazing. Returns the painted shape."""
    body = cv.roughen(cv.shape(outline, soft=soft), rough, 20)
    painted = body if highlight is None else body - cv.shape(highlight, soft=4)
    cv.fill(body, "#ffffff")
    cv.fill(painted, base, opacity=0.9, blend=Blend.MULTIPLY)
    cv.fill(cv.mottle(painted, 46, 0.4, 0.2), base, opacity=0.4, blend=Blend.MULTIPLY)
    cv.fill(cv.form_shadow(body, LIGHT, shadow, soft=0.35), deep, opacity=0.75, clip=painted, blend=Blend.MULTIPLY)
    return body


def cast_shadow(cv, x, y, rx, ry):
    """Shadow an object casts on the table: a dark, narrow shadow at the contact point and a wide, pale one."""
    wide = cv.roughen(cv.shape(g.ellipse(x + rx * 0.35, y, rx, ry), soft=9), 6, 24)
    cv.fill(wide, SHADOW, opacity=0.55, blend=Blend.MULTIPLY)
    cv.fill(cv.shape(g.ellipse(x, y - ry * 0.2, rx * 0.62, ry * 0.4), soft=4), SHADOW, opacity=0.7,
            blend=Blend.MULTIPLY)


def paint_setting(cv, rng):
    wash(cv, g.blob(520, 380, 400, 0.22, 10, rng, stretch=(1.25, 0.8)), BACK_WARM, 0.8, soft=40, rough=24)
    wash(cv, g.blob(820, 330, 300, 0.3, 9, rng, stretch=(1.1, 0.8)), BACK_COOL, 0.5, soft=46, rough=22)
    table = g.spline([(60, TABLE_Y), (1140, TABLE_Y - 6), (1170, 830), (40, 842)], closed=True,
                     corners=(0, 1, 2, 3))
    wash(cv, table, Linear([TABLE, TABLE_DEEP], (0, TABLE_Y), (0, 860)), 0.85, soft=6, rough=9)
    cv.stroke(g.spline([(70, TABLE_Y + 2), (600, TABLE_Y - 2), (1130, TABLE_Y - 4)], closed=False), TABLE_DEEP,
              width=3, opacity=0.6, jitter=0.5)
    motifs.splatter(cv, (1010, 250), 110, 18, [BACK_COOL, PERSIMMON, GRAPE], rng=rng)


def paint_teapot(cv):
    pot = g.Frame(origin=(410, 520), unit=160)
    cast_shadow(cv, 470, 668, 250, 30)
    handle = g.ribbon(g.spline(pot([(0.86, -0.42), (1.4, -0.5), (1.5, 0.05), (0.92, 0.36)]), closed=False),
                      (36, 30, 30, 36))
    glazed(cv, handle[0], POT, POT_DEEP, shadow=0.5)
    spout = g.ribbon(g.spline(pot([(-0.86, 0.2), (-1.3, 0.0), (-1.52, -0.52)]), closed=False), (86, 52, 30))
    glazed(cv, spout[0], POT, POT_DEEP, shadow=0.5)
    body_outline = g.spline(pot([(-0.62, -0.74), (0.62, -0.74), (1.0, -0.2), (0.94, 0.5), (0.5, 0.9),
                                 (-0.5, 0.9), (-0.94, 0.5), (-1.0, -0.2)]), closed=True)
    highlight = g.ellipse(*pot.point(-0.46, -0.3), 34, 62, 24)
    body = glazed(cv, body_outline, POT, POT_DEEP, highlight)
    # The colors of the table and persimmons reflect on the underside of the teapot.
    bounce = cv.shape(g.ellipse(*pot.point(0.2, 0.72), 120, 30), soft=14)
    cv.fill(bounce, PERSIMMON, opacity=0.3, clip=body, blend=Blend.MULTIPLY)
    lid = glazed(cv, g.ellipse(*pot.point(0.0, -0.76), 104, 34), POT, POT_DEEP, shadow=0.4)
    cv.fill(cv.shape(g.ellipse(*pot.point(0.0, -0.7), 100, 16), soft=4), POT_DEEP, opacity=0.6, clip=lid,
            blend=Blend.MULTIPLY)
    glazed(cv, g.ellipse(*pot.point(0.0, -0.98), 26, 24), POT, POT_DEEP, g.ellipse(*pot.point(-0.05, -1.03), 7, 6))
    for band_y in (0.08, 0.2):
        band = g.spline(pot([(-0.97, band_y - 0.06), (0.0, band_y + 0.1), (0.96, band_y - 0.06)]), closed=False)
        cv.stroke(band, POT_DEEP, width=4, opacity=0.5, clip=body, jitter=0.4, blend=Blend.MULTIPLY)


def paint_persimmon(cv, x, y, size, turn):
    fruit = g.Frame(origin=(x, y), unit=size, rotate=turn)
    cast_shadow(cv, x + size * 0.2, y + size * 0.78, size * 1.05, size * 0.2)
    outline = g.spline(fruit([(-1.0, -0.1), (-0.6, -0.72), (0.0, -0.82), (0.6, -0.72), (1.0, -0.1), (0.8, 0.56),
                              (0.0, 0.8), (-0.8, 0.56)]), closed=True)
    body = glazed(cv, outline, PERSIMMON, PERSIMMON_DEEP, g.ellipse(*fruit.point(-0.42, -0.34), size * 0.16,
                                                                    size * 0.24, 30))
    for angle in range(0, 360, 90):
        leaf = g.Frame(origin=fruit.point(0.0, -0.68), unit=size * 0.42, rotate=turn + angle + 20)
        sepal = cv.shape(g.spline(leaf([(0.0, 0.1), (0.42, -0.4), (0.0, -1.0), (-0.42, -0.4)]), closed=True,
                                  corners=(2,)), soft=1.5)
        cv.fill(sepal, CALYX, opacity=0.9, clip=body | sepal, blend=Blend.MULTIPLY)
    cv.fill(cv.shape(g.ellipse(*fruit.point(0.0, -0.7), size * 0.09)), "#4a3a2a", opacity=0.85)


def paint_grapes(cv, rng):
    cast_shadow(cv, 760, 762, 190, 26)
    cv.stroke(g.spline([(700, 540), (716, 600), (740, 640)], closed=False), STEM, width=8, taper=(1, 0.7, 0.5),
              opacity=0.9)
    # Draw the back grapes first so the front ones overlap. Grapes shrink away from the stem, so the bunch
    # narrows downward.
    rows = [(650, 4), (690, 5), (730, 4), (764, 3)]
    for y, count in rows:
        for index in range(count):
            x = 740 + (index - (count - 1) / 2.0) * 46 + rng.uniform(-8, 8)
            radius = rng.uniform(24, 29)
            glazed(cv, g.ellipse(x, y + rng.uniform(-8, 8), radius, radius * 1.06), GRAPE, GRAPE_DEEP,
                   g.ellipse(x - radius * 0.35, y - radius * 0.4, radius * 0.2, radius * 0.26), soft=1.2, rough=1.5)


def main(out_dir="out", scale=1.0, seed=31):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    paint_setting(cv, rng)
    paint_teapot(cv)
    paint_persimmon(cv, 990, 640, 86, 8)
    paint_grapes(cv, rng)
    paint_persimmon(cv, 900, 742, 94, -12)
    io.save(cv.guide_image(), out_dir / "still_1_underpainting_guide.png")
    return io.save(watercolor.render(cv), out_dir / "watercolor_still_life.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
