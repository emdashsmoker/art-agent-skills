"""Oil example (doomer mood): a woman standing at an overpass railing just after sunset, with panel apartment blocks
and the steam of a striped chimney in the distance.

The camera sits at waist height and looks slightly up. The horizon passes at chest height, so buildings and chimneys
rise behind the figure.
The sun set below the horizon on the right warms only the steam and the right contour of the figure, and the rest
sinks into a gray-blue evening.
The only warm colors are the afterglow, a streetlight just switched on and a faded red scarf. Mood values are in
references/mood-doomer.md.
Process: evening sky → sun halo → far apartment silhouettes → chimney and steam → far snowfield → railing →
streetlight → figure → oil pass → color grading.
Run: python oil_doomer_overpass.py [output_dir] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, figure, garment, io, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import oil  # noqa: E402

WIDTH, HEIGHT = 1600, 1200
HORIZON_Y = 600.0
SUN = (1300.0, 615.0)                 # sun just set below the horizon
WOMAN_PELVIS, WOMAN_UNIT = (560.0, 960.0), 170.0
WOMAN_TURN = 35.0                     # body turned 3/4 toward the chimney (screen right)
PARAPET_TOP, HANDRAIL_Y = 840.0, 735.0   # height of the concrete parapet top and the steel handrail above it
PARAPET_JOINT, POST_GAP = 300.0, 300.0   # joint spacing of the parapet slabs, spacing of the handrail posts
CHIMNEYS = ((1130.0, 110.0, 44.0), (1350.0, 200.0, 38.0))   # (x, top y, bottom half-width)
CHIMNEY_STROKE_MARGIN = 10.0          # width by which vertical strokes extend past the chimney outline
SUNSET_LIGHT = (0.85, -0.3)
SUNSET_LIGHT_3D = (0.8, -0.3, -0.15)

# Palette: gray-blue evening sky and concrete dominate. Afterglow orange appears only on the horizon and the
# sun-side edge of the steam.
SKY_TOP, SKY_MID, SKY_LOW, SUNSET = "#2a3442", "#5a5a68", "#9a7a78", "#d8925e"
SUN_CORE = "#ffd9a8"
BLOCK_FAR, BLOCK_NEAR, WINDOW_WARM = "#4e5464", "#3a4050", "#e9b86a"
CHIMNEY_RED, CHIMNEY_WHITE, CHIMNEY_SHADE = "#8e4a43", "#b9b3ad", "#3a3640"
STEAM, STEAM_SHADE, STEAM_LIT = "#aaa7b2", "#6a6876", "#f0b98a"
SNOW_FAR, SNOW_NEAR = "#6a6f7c", "#454b56"
IRON, IRON_LIT = "#1e2228", "#9a6a4a"
CONCRETE, CONCRETE_SHADE, CONCRETE_TOP = "#4b5058", "#363a42", "#8a7a74"
LAMP_GLOW = "#ffbf7a"

OIL_INK = ch.Ink(line_width=1.5, line_scale=0.7, line_opacity=0.3, body_shadow=0.5, face_shadow=0.22,
                 hair_shadow=0.5, shadow_soft=0.45, light_opacity=0.5).lit_from(SUNSET_LIGHT, SUNSET_LIGHT_3D)
WOMAN = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, skin="#efcdb8", skin_shade="#a88088", skin_deep="#7a5560",
                                           skin_light="#ffe0c8", hair="#3a2622", hair_shade="#1c1214",
                                           hair_light="#8a5a46", line_hair="#140c0c", line_skin="#6a4448"))
COAT = garment.long_coat(coat="#5b5257", scarf="#8a3b35", legs="#2c2a30", boots="#2a201c", length=2.1,
                         scarf_tail=True)


def make_woman():
    """Arms down, looking far toward the chimney. The camera is at waist height, so it looks slightly up at the
    body."""
    return ch.place(WOMAN, WOMAN_PELVIS, WOMAN_UNIT, WOMAN_TURN, elevation=-4.0, head_pitch=-3.0, ink=OIL_INK,
                    outfit=COAT, head=-4.0, head_turn=16.0, arm_l=(7.0, 3.0), arm_r=(9.0, 5.0), leg_l=(4.0, 1.0),
                    leg_r=(3.0, 0.0))


# ---------- sky and distance ----------

def paint_sky(cv):
    sky = cv.shape(g.rect(0, 0, WIDTH, HORIZON_Y + 40))
    cv.direct(sky, angle=-6)
    cv.fill(cv.full(), Linear([(0.0, SKY_TOP), (0.55, SKY_MID), (0.85, SKY_LOW), (1.0, SUNSET)], (0, 0),
                              (0, HORIZON_Y)))
    cv.fill(cv.shape(g.ellipse(SUN[0], SUN[1], 700, 260), soft=260), SUNSET, opacity=0.8, blend=Blend.SCREEN)
    cv.fill(cv.shape(g.ellipse(SUN[0], SUN[1] - 10, 120, 50), soft=70), SUN_CORE, opacity=0.8, blend=Blend.SCREEN)
    # Low cloud bands: only the sun-side undersides are warmed.
    for y, x0, x1 in ((180.0, -50.0, 900.0), (300.0, 500.0, 1700.0), (420.0, -50.0, 700.0)):
        band = cv.shape(g.ellipse((x0 + x1) / 2, y, (x1 - x0) / 2, 26), soft=30)
        cv.fill(band, SKY_TOP, opacity=0.35)
        cv.fill(cv.shape(g.ellipse((x0 + x1) / 2 + 80, y + 14, (x1 - x0) / 2 * 0.8, 10), soft=14), SKY_LOW,
                opacity=0.3)


def paint_blocks(cv, rng):
    """Two layers of far panel apartment silhouettes rising above the horizon. The farther layer sinks more into the
    sky color."""
    for color, top_range, lit in ((BLOCK_FAR, (520.0, 580.0), 0.05), (BLOCK_NEAR, (470.0, 560.0), 0.09)):
        x = -40.0
        while x < WIDTH:
            width, top = rng.uniform(120.0, 260.0), rng.uniform(*top_range) - 40.0
            cv.fill(cv.shape(g.rect(x, top, width, HORIZON_Y - top + 16)), color)
            for wy in np.arange(top + 8, HORIZON_Y + 20, 11.0):
                for wx in np.arange(x + 6, x + width - 6, 9.0):
                    if rng.random() < lit:
                        cv.fill(cv.shape(g.rect(wx, wy, 4.0, 5.0)), WINDOW_WARM, opacity=0.8)
            x += width + rng.uniform(20.0, 90.0)


def paint_chimney(cv, x, top, half):
    """A chimney wrapped in alternating red and white bands. The half away from the sun (left) is in shade."""
    base = PARAPET_TOP
    outline = g.polygon([(x - half, base), (x - half * 0.62, top), (x + half * 0.62, top), (x + half, base)])
    body = cv.shape(outline)
    bands = 9
    for index in range(bands):
        y0 = top + (base - top) * index / bands
        cv.fill(cv.shape(g.rect(x - half - 2, y0, half * 2 + 4, (base - top) / bands + 1)),
                CHIMNEY_RED if index % 2 == 0 else CHIMNEY_WHITE, clip=body)
    cv.fill(body, Linear([CHIMNEY_SHADE, CHIMNEY_SHADE, SKY_LOW], (x - half, 0), (x + half, 0)), opacity=0.5)
    cv.fill(body, SKY_MID, opacity=0.15)
    # Vertical strokes extend just past the chimney edges. Horizontal strokes starting at an edge would drag
    # the stripe colors sideways.
    margin = CHIMNEY_STROKE_MARGIN
    cv.direct(cv.shape(g.polygon([(x - half - margin, base), (x - half * 0.62 - margin, top),
                                  (x + half * 0.62 + margin, top), (x + half + margin, base)])), angle=90)


def paint_steam(cv, rng, x, top, drift):
    """Steam masses drifting up and left from the chimney top and growing. Only the sun-side undersides take the
    afterglow."""
    for index in range(16):
        t = index / 15.0
        cx = x - drift * t ** 1.2 + rng.normal(0.0, 12.0)
        cy = top - 20 - 110 * t ** 0.7 + rng.normal(0.0, 8.0)
        radius = 34 + 110 * t
        puff = cv.shape(g.blob(cx, cy, radius, 0.3, 8, rng), soft=10 + 20 * t)
        cv.direct(puff, angle=-12)
        cv.fill(puff, STEAM, opacity=0.9 - 0.5 * t)
        cv.fill(cv.form_shadow(puff, (-0.6, -0.8), 0.5, soft=0.5), STEAM_SHADE, opacity=0.4)
        cv.fill(cv.form_light(puff, (0.7, 0.6), 0.25, soft=0.5), STEAM_LIT, opacity=0.6 - 0.3 * t)


def paint_far_ground(cv, rng):
    """The far snowfield seen past the railing and the streetlights of a distant road."""
    ground = cv.shape(g.rect(0, HORIZON_Y, WIDTH, PARAPET_TOP - HORIZON_Y + 10))
    cv.direct(ground, angle=0)
    cv.fill(ground, Linear([SNOW_FAR, SNOW_NEAR], (0, HORIZON_Y), (0, PARAPET_TOP)))
    cv.fill(cv.shape(g.ellipse(SUN[0], HORIZON_Y + 20, 640, 60), soft=60), SUNSET, opacity=0.35, blend=Blend.SCREEN)
    for x in np.linspace(80.0, 1000.0, 9):
        y = HORIZON_Y + 12 + rng.uniform(0.0, 6.0)
        cv.fill(cv.shape(g.ellipse(x, y, 3.0, 3.0)), LAMP_GLOW)
        cv.fill(cv.shape(g.ellipse(x, y, 16.0, 12.0), soft=10), LAMP_GLOW, opacity=0.35, blend=Blend.SCREEN)


# ---------- overpass ----------

def paint_parapet(cv):
    """The overpass railing behind the figure: a concrete slab wall, its sunlit top, slab joints, and the steel
    handrail and posts above."""
    wall = cv.shape(g.rect(0, PARAPET_TOP, WIDTH, HEIGHT - PARAPET_TOP))
    cv.direct(wall, angle=2)
    cv.fill(wall, Linear([CONCRETE, CONCRETE_SHADE], (0, PARAPET_TOP), (0, HEIGHT)))
    cv.fill(cv.shape(g.rect(0, PARAPET_TOP, WIDTH, 22)), Linear([CONCRETE, CONCRETE_TOP], (0, 0), (WIDTH, 0)))
    for x in np.arange(PARAPET_JOINT * 0.6, WIDTH, PARAPET_JOINT):
        cv.fill(cv.shape(g.rect(x - 3, PARAPET_TOP + 22, 6, HEIGHT - PARAPET_TOP)), CONCRETE_SHADE)
        # Water stains running down from the joints.
        cv.fill(cv.shape(g.rect(x + 8, PARAPET_TOP + 22, 70, 260), soft=26), CONCRETE_SHADE, opacity=0.45)
    for x in np.arange(POST_GAP * 0.35, WIDTH, POST_GAP):
        cv.fill(cv.shape(g.rect(x - 6, HANDRAIL_Y, 12, PARAPET_TOP - HANDRAIL_Y)), IRON)
    cv.fill(cv.shape(g.rect(0, HANDRAIL_Y - 7, WIDTH, 14)), IRON)
    cv.fill(cv.shape(g.rect(WIDTH * 0.5, HANDRAIL_Y - 7, WIDTH * 0.5, 4)), Linear([IRON, IRON_LIT], (WIDTH * 0.5, 0),
                                                                                (WIDTH, 0)), opacity=0.8)


def paint_lamp(cv):
    """A streetlight on the railing at screen right. Just after sunset, a dim orange that has just come on."""
    x = 1480.0
    cv.fill(cv.shape(g.rect(x - 9, 60, 18, PARAPET_TOP - 60)), IRON)
    cv.stroke(g.spline([(x, 70), (x - 30, 30), (x - 110, 26)], closed=False), IRON, width=9)
    cv.fill(cv.shape(g.ellipse(x - 120, 34, 38, 12)), IRON)
    cv.fill(cv.shape(g.ellipse(x - 120, 42, 22, 6)), LAMP_GLOW)
    cv.fill(cv.shape(g.ellipse(x - 120, 60, 140, 110), soft=110), LAMP_GLOW, opacity=0.35, blend=Blend.SCREEN)


def silhouette(cv, model):
    """Figure silhouette merging the body masses and clothing pieces."""
    paths = [path for _, group in model.body.groups() for path in group]
    paths += [path for piece in model.outfit for path in piece.paths]
    return figure.shape_of(cv, paths)


def main(out_dir="out", scale=1.0, seed=137):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv)
    paint_blocks(cv, rng)
    for (x, top, half), drift in zip(CHIMNEYS, (620.0, 480.0)):
        paint_chimney(cv, x, top, half)
        paint_steam(cv, rng, x, top, drift)
    paint_far_ground(cv, rng)
    paint_parapet(cv)
    paint_lamp(cv)
    woman = make_woman()
    ch.paint_figure(cv, woman)
    # Inside the figure silhouette, strokes run vertically. Without a direction, horizontal strokes would
    # spill past the coat outline into the background.
    cv.direct(silhouette(cv, woman), angle=85)
    io.save(cv.guide_image(), out_dir / "overpass_1_underpainting_guide.png")
    head = woman.body.joint("head")
    focus = cv.shape(g.ellipse(head[0], head[1] + 60, 220, 260), soft=60)
    image = oil.render(cv, brush_radii=(20.0, 9.0, 4.0, 2.0), detail=focus, relief=0.4, color_jitter=0.035)
    image = post.grade(image, shadows="#0e1a26", highlights="#ffd9a0", amount=0.14, contrast=1.06, saturation=0.8)
    return io.save(post.vignette(image, strength=0.36), out_dir / "oil_doomer_overpass.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
