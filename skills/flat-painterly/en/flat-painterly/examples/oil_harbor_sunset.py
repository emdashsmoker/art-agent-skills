"""Painterly (oil) example: sailboats in a harbor at sunset.

Process: underpainting (large color fields → details) → stroke directions → oil pass → finish.
The underpainting may be smooth. The oil pass creates the brush marks and paint thickness.
Run: python oil_harbor_sunset.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, io, motifs, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import oil  # noqa: E402

WIDTH, HEIGHT = 1600, 1000
HORIZON = 560
SUN = (1130, 505)

# Palette: complementary contrast of purple-navy shade and orange-yellow light. The brightest color is
# reserved for the sun and the glitter on the water.
SKY = [(0.0, "#232f66"), (0.45, "#7a4f86"), (0.75, "#e0705c"), (1.0, "#f9bf62")]
WATER = [(0.0, "#eea062"), (0.25, "#a5607e"), (0.6, "#3d4686"), (1.0, "#141f45")]
SUN_CORE, SUN_GLOW = "#fff6cf", "#ffc878"
CLOUD_DARK, CLOUD_MID, CLOUD_LIT = "#4a3f78", "#b65a78", "#ffab62"
LAND_FAR, LAND_NEAR, LAND_LIT = "#5a4a80", "#251f42", "#8a5a78"
HULL, HULL_LIT = "#17162c", "#5a3a4a"
SAIL_LIT, SAIL_SHADE = "#f7deb0", "#b07a6c"
GLITTER = "#ffe3a0"


def block_in(cv):
    """Stage 1: large color fields of sky, water and land. This stage decides the value structure."""
    sky = cv.shape(g.rect(0, 0, WIDTH, HORIZON))
    cv.fill(sky, Linear(SKY, (0, 0), (0, HORIZON)))
    cv.fill(cv.shape(g.ellipse(*SUN, 330, 230), soft=110), SUN_GLOW, opacity=0.75, blend=Blend.SCREEN)
    cv.fill(cv.shape(g.ellipse(*SUN, 58), soft=3), SUN_CORE)

    water = cv.shape(g.rect(0, HORIZON, WIDTH, HEIGHT - HORIZON))
    cv.fill(water, Linear(WATER, (0, HORIZON), (0, HEIGHT)))
    cv.direct(sky, angle=-8)
    cv.direct(cv.shape(g.ellipse(*SUN, 260, 200)), around=SUN)
    cv.direct(water, angle=0)


def paint_clouds(cv, rng):
    """Stage 2: banded clouds whose undersides glow toward the sun. Dark tops and bright bottoms read as backlight."""
    bands = [(260, 120, 420, 34), (820, 90, 520, 40), (1330, 170, 330, 30), (520, 250, 380, 30),
             (1050, 300, 460, 34), (180, 340, 300, 24), (1420, 380, 260, 22), (720, 400, 320, 20)]
    for x, y, half_width, half_height in bands:
        body = cv.roughen(cv.shape(g.blob(x, y, 1.0, 0.3, 11, rng, stretch=(half_width, half_height)), soft=6),
                          10, 40)
        warmth = y / HORIZON
        cv.fill(body, CLOUD_DARK if warmth < 0.45 else CLOUD_MID, opacity=0.9)
        belly = cv.roughen(cv.shape(g.blob(x + 20, y + half_height * 0.55, 1.0, 0.3, 9, rng,
                                           stretch=(half_width * 0.85, half_height * 0.45)), soft=5), 8, 30)
        cv.fill(belly, CLOUD_LIT, opacity=0.55 + 0.4 * warmth, clip=body)


def paint_land(cv, rng):
    """Stage 3: the headland on the left and the far islands. Aerial perspective moves them toward the sky color
    with distance."""
    far = motifs.ridge(900, 1600, HORIZON, 46, 0.55, rng=rng)
    cv.fill(cv.shape(np.vstack([far, [(1600, HORIZON + 2), (900, HORIZON + 2)]])), LAND_FAR)

    top = motifs.ridge(-20, 640, HORIZON, 150, 0.5, rng=rng)
    top[:, 1] = HORIZON - (HORIZON - top[:, 1]) * np.linspace(1.0, 0.04, len(top)) - 4
    cape = cv.shape(np.vstack([top, [(640, HORIZON + 3), (-20, HORIZON + 3)]]))
    cv.fill(cape, LAND_NEAR)
    cv.fill(cv.form_light(cape, (0.9, -0.4), amount=0.22, soft=0.3), LAND_LIT, opacity=0.8)
    cv.direct(cape, angle=20)
    for x in (150, 205, 250, 330, 372, 455):
        window = cv.shape(g.rect(x, HORIZON - 26 - 10 * np.sin(x), 7, 6))
        cv.fill(window, "#ffc46a")


def paint_water_light(cv, rng):
    """Stage 4: the path of light and reflections on the water. Broken horizontal touches create the movement of the
    surface."""
    for _ in range(170):
        depth = rng.uniform(0.0, 1.0) ** 1.4
        y = HORIZON + 8 + depth * (HEIGHT - HORIZON - 16)
        spread = 26 + 210 * depth
        x = SUN[0] + rng.normal(0.0, spread * 0.45)
        dab = cv.shape(g.ellipse(x, y, rng.uniform(10, 34) * (0.5 + depth), 2.0 + 4.5 * depth))
        cv.fill(dab, GLITTER if rng.random() < 0.7 else SUN_CORE, opacity=rng.uniform(0.55, 0.95))
    for _ in range(90):
        y = rng.uniform(HORIZON + 10, HEIGHT)
        depth = (y - HORIZON) / (HEIGHT - HORIZON)
        dab = cv.shape(g.ellipse(rng.uniform(0, WIDTH), y, rng.uniform(20, 70) * (0.4 + depth), 2.0 + 4.0 * depth))
        cv.fill(dab, "#c5678a" if rng.random() < 0.5 else "#262f6a", opacity=0.45)


def paint_boat(cv, x, waterline, size, rng):
    """One sailboat and its reflection in the water. size is the mast height."""
    boat = g.Frame(origin=(x, waterline), unit=size)
    for y in np.linspace(0.04, 0.95, 16):
        wobble = rng.normal(0.0, 0.03)
        shadow = cv.shape(g.ellipse(*boat.point(wobble, y), boat.length(0.36 * (1.0 - 0.45 * y)),
                                    boat.length(0.022)))
        cv.fill(shadow, HULL, opacity=0.8 * (1.0 - 0.6 * y))
    for y in np.linspace(0.2, 0.9, 7):
        glint = cv.shape(g.ellipse(*boat.point(0.1 + rng.normal(0.0, 0.04), y), boat.length(0.1),
                                   boat.length(0.016)))
        cv.fill(glint, SAIL_LIT, opacity=0.4)

    hull = cv.shape(g.spline(boat([(-0.42, -0.1), (0.46, -0.12), (0.34, 0.02), (-0.32, 0.02)]), closed=True,
                             corners=(0, 1, 2, 3)))
    cv.fill(hull, HULL)
    cv.fill(cv.shape(g.polygon(boat([(-0.42, -0.1), (0.46, -0.12), (0.44, -0.085), (-0.4, -0.065)]))), HULL_LIT)
    cv.stroke(boat([(0.02, -0.1), (0.02, -1.02)]), HULL, width=boat.length(0.016))
    main = cv.shape(g.spline(boat([(0.05, -0.98), (0.2, -0.55), (0.44, -0.17), (0.05, -0.17)]), closed=True,
                             corners=(0, 2, 3)))
    cv.fill(main, SAIL_LIT)
    cv.fill(cv.form_shadow(main, (0.9, -0.2), amount=0.35, soft=0.4), SAIL_SHADE, opacity=0.7)
    jib = cv.shape(g.spline(boat([(-0.01, -0.9), (-0.14, -0.5), (-0.36, -0.17), (-0.01, -0.17)]), closed=True,
                            corners=(0, 2, 3)))
    cv.fill(jib, SAIL_SHADE)
    cv.direct(main | jib, angle=78)


def paint_underpainting(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    block_in(cv)
    paint_clouds(cv, rng)
    paint_land(cv, rng)
    paint_water_light(cv, rng)
    paint_boat(cv, 1420, HORIZON + 22, 70, rng)
    paint_boat(cv, 540, 700, 250, rng)
    return cv


def main(out_dir="out", scale=1.0, seed=11):
    out_dir = Path(out_dir)
    cv = paint_underpainting(scale, seed)
    io.save(cv.image(), out_dir / "oil_1_underpainting.png")
    focus = cv.shape(g.ellipse(540, 600, 260, 300), soft=60) | cv.shape(g.ellipse(*SUN, 330, 140), soft=60) \
        | cv.shape(g.rect(0, HORIZON - 60, 700, 80), soft=20)
    image = oil.render(cv, brush_radii=(24.0, 11.0, 5.0, 2.4), detail=focus)
    image = post.grade(image, shadows="#2a2f6a", highlights="#ffd9a0", amount=0.08, contrast=1.05, saturation=1.0)
    return io.save(post.vignette(image, strength=0.18), out_dir / "oil_harbor_sunset.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
