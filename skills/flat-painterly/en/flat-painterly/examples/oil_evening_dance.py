"""Oil example: two people dancing in a ballroom (formal wear, two-shot).

She spins holding the hand he raises above his head. stage.reach puts the held hands on one point above both heads,
and Hem's swirl and wave give the dress hem spinning ripples. The figures are painted with an Ink that nearly
removes lines, then go through the oil pass.
Process: dark room and chandelier light → polished floor and reflections → him (far side) → her → light on the held
hands → oil pass → color grading.
Run: python oil_evening_dance.py [output_dir] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Radial, garment, io, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import oil  # noqa: E402

WIDTH, HEIGHT = 1800, 1500
STAGE = Stage(origin=(860.0, 1380.0), unit=128.0, elevation=8.0)
CLASP = np.array([0.35, -8.15, 0.2])          # hands held above the heads (world coordinates)
FLOOR_Y = 1250.0

# Palette: a dark red-brown room and the gold of the chandelier. The one accent is the red dress, and he
# recedes in a chestnut suit.
ROOM_DARK, ROOM_MID, ROOM_WARM = "#1e1414", "#4a2a24", "#8a4a32"
GOLD, GOLD_GLOW, CANDLE = "#d8a24a", "#ffd890", "#fff2c8"
FLOOR_TOP, FLOOR_LOW, FLOOR_SHINE = "#5a3424", "#2a1812", "#e0a060"
COLUMN, COLUMN_SHADE = "#6a4436", "#3a2420"
OIL_INK = ch.Ink(light=(0.3, -0.9), light3d=np.array([0.3, -0.85, -0.45]) / np.linalg.norm([0.3, -0.85, -0.45]),
                 line_width=1.5, line_scale=0.7, line_opacity=0.28, body_shadow=0.42, face_shadow=0.2, hair_shadow=0.45,
                 shadow_soft=0.45, light_opacity=0.55)

DANCER = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, skin="#f3cdb4", skin_shade="#c0806e",
                                            skin_light="#fff0e0", line_skin="#8a5040", hair="#2a1610",
                                            hair_shade="#140a08", hair_light="#6a3a28", line_hair="#140a08"))
PARTNER = replace(ch.MALE, palette=replace(ch.MALE.palette, skin="#e2b494", skin_shade="#a8705a", line_skin="#6a3a2a",
                                           hair="#1a1210", hair_shade="#0a0606", hair_light="#4a3830"))
GOWN = garment.formal_dress(dress="#a8202c", shoes="#2a1210", length=3.75, flare=1.05, wave=0.09, swirl=55.0)
SUIT = garment.formal_suit(jacket="#3a2a2a", shirt="#efe6d8", tie="#5a1a20", shoes="#140c0a")


def make_dancers():
    """He stands a little behind on screen right and looks left. She looks at him and spins on her toes. The held
    hands are above both heads."""
    him = STAGE.place(PARTNER, 1.25, 0.45, -62.0, outfit=SUIT, ink=OIL_INK, head=-6.0, head_turn=-4.0,
                      head_pitch=4.0, reach={"arm_l": CLASP + np.array([0.12, 0.05, 0.0])},
                      arm_r=(38.0, 30.0), swing={"leg_l": (14.0, 6.0), "leg_r": (-12.0, -18.0), "arm_r": (-10.0, 20.0)},
                      leg_l=(4.0, 0.0), leg_r=(6.0, 2.0), foot_pitch={"r": 16.0}, lean=-3.0, grips=("l",),
                      in_front=("arm_l",))
    her = STAGE.place(DANCER, -0.35, 0.0, 28.0, outfit=GOWN, ink=OIL_INK, head=10.0, head_turn=38.0,
                      head_pitch=-10.0, reach={"arm_r": CLASP - np.array([0.12, -0.05, 0.0])},
                      arm_l=(84.0, 100.0), swing={"leg_r": (4.0, -4.0), "leg_l": (-6.0, -26.0), "arm_l": (10.0, 30.0)},
                      leg_l=(8.0, 2.0), leg_r=(2.0, 0.0), foot_pitch={"l": 40.0, "r": 22.0}, hip_tilt=-6.0,
                      chest_tilt=5.0, spine=-4.0, grips=("r",))
    return him, her


def paint_room(cv, rng):
    cv.fill(cv.full(), Linear([ROOM_DARK, ROOM_MID, ROOM_WARM], (0, 0), (0, FLOOR_Y)))
    cv.fill(cv.shape(g.ellipse(WIDTH * 0.5, 120, 900, 520), soft=260), GOLD_GLOW, opacity=0.35, blend=Blend.SCREEN)
    for x in (140.0, 520.0, 1280.0, 1660.0):
        column = cv.shape(g.rect(x - 60, 0, 120, FLOOR_Y))
        cv.fill(column, Linear([COLUMN_SHADE, COLUMN, COLUMN_SHADE], (x - 60, 0), (x + 60, 0)))
        cv.fill(column, ROOM_DARK, opacity=0.35 + 0.25 * (abs(x - WIDTH / 2) / (WIDTH / 2)))
    # Chandelier: a cluster of light at the top center and candle dots.
    cx, cy = WIDTH * 0.5, 150.0
    cv.fill(cv.shape(g.ellipse(cx, cy, 260, 90)), GOLD, opacity=0.8)
    for angle in np.linspace(0.0, 2.0 * np.pi, 12, endpoint=False):
        x, y = cx + 240 * np.cos(angle), cy + 70 * np.sin(angle)
        cv.fill(cv.shape(g.ellipse(x, y - 30, 9, 16)), CANDLE)
        cv.fill(cv.shape(g.ellipse(x, y - 30, 40, 40), soft=26), GOLD_GLOW, opacity=0.6, blend=Blend.SCREEN)
    floor = cv.shape(g.rect(0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y))
    cv.fill(floor, Linear([FLOOR_TOP, FLOOR_LOW], (0, FLOOR_Y), (0, HEIGHT)))
    cv.fill(cv.shape(g.ellipse(WIDTH * 0.5, FLOOR_Y + 60, 520, 70), soft=60), FLOOR_SHINE, opacity=0.45,
            blend=Blend.SCREEN)
    cv.fill(cv.shape(g.ellipse(WIDTH * 0.5, FLOOR_Y + 180, 700, 160), soft=120), Radial([GOLD_GLOW, ROOM_DARK],
                                                                                       (WIDTH * 0.5, FLOOR_Y + 180), 700),
            opacity=0.25, blend=Blend.SCREEN)


def paint_reflections(cv, models):
    """The two people reflected on the polished floor: soft columns of color running down from their feet."""
    for model, color in zip(models, ("#3a2626", "#a8202c")):
        x = model.body.joint("pelvis")[0]
        floor = STAGE.point(0.0, 0.0, model.world[2])[1]
        cv.fill(cv.shape(g.ellipse(x, floor + 8, 230, 34), soft=18), "#0e0808", opacity=0.55)
        cv.fill(cv.shape(g.rect(x - 140, floor + 20, 280, 220), soft=40), color, opacity=0.3)


def paint_glow(cv):
    x, y = STAGE.point(*CLASP)
    cv.fill(cv.shape(g.ellipse(x, y, 130, 130), soft=80), GOLD_GLOW, opacity=0.35, blend=Blend.SCREEN)


def main(out_dir="out", scale=1.0, seed=101):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_room(cv, rng)
    him, her = make_dancers()
    paint_reflections(cv, (him, her))
    for model in STAGE.far_first((him, her)):
        ch.paint_figure(cv, model)
    paint_glow(cv)
    io.save(cv.guide_image(), out_dir / "dance_1_underpainting_guide.png")
    focus = cv.shape(g.ellipse(*STAGE.point(0.3, -6.0, 0.2), 420, 560), soft=80)
    image = oil.render(cv, brush_radii=(20.0, 9.0, 4.0, 2.0), detail=focus, relief=0.45, color_jitter=0.04)
    image = post.grade(image, shadows="#1a0e14", highlights="#ffe2b4", amount=0.1, contrast=1.06)
    return io.save(post.vignette(image, strength=0.35), out_dir / "oil_evening_dance.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
