"""Painterly (oil) example: midsummer fields and an oak tree (landscape).

Process: sky and clouds → far mountains → color bands of fields → path → tree and shadow → foreground grass and
flowers → stroke directions → oil pass.
Depth comes from three cues: bluer and paler colors with distance, field bands that narrow with distance, and a
large tree that frames the foreground.
Run: python oil_summer_fields.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, color, io, motifs, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import oil  # noqa: E402

WIDTH, HEIGHT = 1600, 1000
HORIZON = 470
LIGHT = (-0.7, -0.7)

# Palette: green and gold dominate. The blue of the sky supports them, and poppy red appears only as dots in
# the foreground grass.
SKY = [(0.0, "#3f7fd0"), (0.6, "#9cc8ee"), (1.0, "#e6f1f4")]
CLOUD = ("#ffffff", "#e3e8f0", "#a9b6d0")
MOUNTAIN_FAR, MOUNTAIN_NEAR, HAZE = "#9db3d6", "#7592b8", "#b9cfe0"
FIELDS = ["#b9c86a", "#e6c85a", "#8fb24e", "#d9b048", "#6f9a3e"]
PATH_LIT, PATH_SHADE = "#e9d2a4", "#b8946a"
OAK = ("#b6cc5a", "#5f9038", "#2a4f2c")
POPLAR = ("#9dbb58", "#557f3a", "#2f5230")
TRUNK, TRUNK_LIT = "#3f2c24", "#7a5a44"
SHADOW = "#2f4a3a"
GRASS = ["#4f7f34", "#6f9a3e", "#9dbb58", "#3a6030"]
POPPY, HOUSE, ROOF = "#e0442e", "#f4ecd8", "#b8543c"


def paint_sky(cv, rng):
    sky = cv.shape(g.rect(0, 0, WIDTH, HORIZON + 10))
    cv.fill(sky, Linear(SKY, (0, 0), (0, HORIZON)))
    cv.direct(sky, angle=-8)
    motifs.cumulus(cv, 1060, 330, 620, 250, light=LIGHT, palette=CLOUD, puffs=70, rng=rng)
    motifs.cumulus(cv, 360, 250, 320, 110, light=LIGHT, palette=CLOUD, puffs=30, rng=rng)


def paint_mountains(cv, rng):
    for base_color, peak, roughness in ((MOUNTAIN_FAR, 150, 0.55), (MOUNTAIN_NEAR, 90, 0.6)):
        top = motifs.ridge(-20, WIDTH + 20, HORIZON, peak, roughness, rng=rng)
        range_shape = cv.shape(np.vstack([top, [(WIDTH + 20, HORIZON + 6), (-20, HORIZON + 6)]]))
        cv.fill(range_shape, base_color)
        cv.fill(cv.form_light(range_shape, LIGHT, 0.3, soft=0.4), "#c9d6ea", opacity=0.5)
        cv.direct(range_shape, angle=15)


def paint_fields(cv):
    """Color bands of fields. Farther bands are narrower and paler, so the flat land recedes."""
    edges = [HORIZON, 500, 545, 610, 700, 830, HEIGHT + 20]
    for index in range(len(edges) - 1):
        top, bottom = edges[index], edges[index + 1]
        sway = 18 + index * 10
        outline = g.spline([(-20, top + sway * 0.3), (500, top - sway * 0.2), (1100, top + sway * 0.4),
                            (WIDTH + 20, top), (WIDTH + 20, bottom + 30), (-20, bottom + 30)], closed=True,
                           corners=(0, 3, 4, 5))
        band = cv.shape(outline)
        distance = 1.0 - index / (len(edges) - 2)
        # Farther fields mix in more sky color for aerial perspective.
        cv.fill(band, color.mix(FIELDS[index % len(FIELDS)], HAZE, 0.3 * distance))
        cv.fill(cv.mottle(band, 120, 0.45, 0.25), FIELDS[(index + 2) % len(FIELDS)], opacity=0.25)
        cv.direct(band, angle=3 - index)


def paint_path_and_house(cv):
    path = g.spline([(700, HEIGHT + 20), (760, 860), (640, 720), (560, 620), (610, 545), (640, 500),
                     (654, 500), (650, 548), (640, 625), (760, 720), (930, 850), (1010, HEIGHT + 20)],
                    closed=True, corners=(0, 5, 6, 11))
    road = cv.shape(path)
    cv.fill(road, PATH_LIT)
    cv.fill(cv.shape(g.spline([(700, HEIGHT + 20), (760, 860), (640, 720), (560, 620), (610, 545), (640, 500),
                               (646, 500), (626, 548), (590, 625), (690, 720), (800, 860), (790, HEIGHT + 20)],
                              closed=True, corners=(0, 5, 6, 11)), soft=6), PATH_SHADE, opacity=0.6, clip=road)
    cv.direct(road, angle=75)
    house = g.Frame(origin=(690, 478), unit=26)
    cv.fill(cv.shape(g.polygon(house([(-1.0, 0.0), (1.0, 0.0), (1.0, 0.9), (-1.0, 0.9)]))), HOUSE)
    cv.fill(cv.shape(g.polygon(house([(0.2, 0.0), (1.0, 0.0), (1.0, 0.9), (0.2, 0.9)]))), "#c9c0b0")
    cv.fill(cv.shape(g.polygon(house([(-1.2, 0.05), (-0.5, -0.8), (0.8, -0.8), (1.2, 0.05)]))), ROOF)


def paint_poplars(cv, rng):
    for x in np.arange(900, 1560, 74):
        height = rng.uniform(120, 165)
        x = x + rng.uniform(-12, 12)
        cv.stroke([(x, 512), (x, 512 - height * 0.3)], TRUNK, width=5)
        motifs.canopy(cv, x, 512 - height * 0.58, height * 0.36, height, light=LIGHT, palette=POPLAR, puffs=22,
                      puff_size=(0.32, 0.5), rng=rng)
        cv.fill(cv.shape(g.ellipse(x + height * 0.3, 515, height * 0.42, 6), soft=3), SHADOW, opacity=0.45,
                blend=Blend.MULTIPLY)


def paint_oak(cv, rng):
    """A large oak at the front left. The dark mass that frames the picture makes the distant fields look farther."""
    cast = cv.shape(g.spline([(250, 800), (520, 770), (900, 800), (860, 850), (420, 870)], closed=True), soft=14)
    cv.fill(cast, SHADOW, opacity=0.6, blend=Blend.MULTIPLY)
    cv.direct(cast, angle=4)
    trunk_spine = g.spline([(330, 830), (318, 690), (340, 560), (330, 470)], closed=False)
    trunk = cv.shape(*g.ribbon(trunk_spine, (84, 60, 50, 36)))
    cv.fill(trunk, TRUNK)
    cv.fill(cv.edge_light(trunk, LIGHT, width=14, soft=5), TRUNK_LIT, opacity=0.8)
    cv.direct(trunk, angle=88)
    for start, bend, end, width in (((335, 600), (420, 520), (520, 470), 26), ((330, 560), (240, 480), (150, 440), 24),
                                    ((335, 520), (360, 440), (420, 380), 18)):
        cv.stroke(g.spline([start, bend, end], closed=False), TRUNK, width=width, taper=(1, 0.7, 0.3))
    crown = motifs.canopy(cv, 330, 330, 640, 430, light=LIGHT, palette=OAK, puffs=60, rng=rng)
    cv.direct(crown, around=(330, 330))


def paint_foreground(cv, rng):
    motifs.grass(cv, (0, WIDTH), (860, HEIGHT + 10), 900, GRASS, blade=(22, 60), rng=rng)
    for _ in range(70):
        y = rng.uniform(880, HEIGHT - 6)
        size = 4.0 + 7.0 * (y - 880) / 120.0
        x = rng.choice([rng.uniform(0, 660), rng.uniform(1040, WIDTH)])
        cv.fill(cv.shape(g.blob(x, y, size, 0.3, 6, rng)), POPPY)
        cv.fill(cv.shape(g.ellipse(x, y, size * 0.25)), "#2a1a1a")


def paint_underpainting(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    paint_sky(cv, rng)
    paint_mountains(cv, rng)
    paint_fields(cv)
    paint_path_and_house(cv)
    paint_poplars(cv, rng)
    paint_oak(cv, rng)
    paint_foreground(cv, rng)
    return cv


def main(out_dir="out", scale=1.0, seed=29):
    out_dir = Path(out_dir)
    cv = paint_underpainting(scale, seed)
    io.save(cv.image(), out_dir / "fields_1_underpainting.png")
    image = oil.render(cv, brush_radii=(22.0, 10.0, 4.5, 2.4))
    image = post.grade(image, shadows="#243a5a", highlights="#fff2c8", amount=0.07, contrast=1.06, saturation=1.05)
    return io.save(post.vignette(image, strength=0.16), out_dir / "oil_summer_fields.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
