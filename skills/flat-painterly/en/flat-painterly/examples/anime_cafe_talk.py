"""Anime style example: two people talking face to face at a cafe window (casual wear, two-shot).

Both figures stand on one stage.Stage and share one view. They sit facing each other, each turned 10 degrees toward
the viewer so both faces show (the shot-reverse-shot framing of film). The near arm resting on the table is painted
after the table top.
Process: room and window → chairs → table legs → figures (without near arms, window-light rim) → table top and cups
→ near arms → compositing finish.
Run: python anime_cafe_talk.py [output_dir] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, garment, io, motifs, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 2400, 1500
STAGE = Stage(origin=(1200.0, 1400.0), unit=172.0, elevation=6.0)
SEAT_GAP = 3.0                     # distance from the table center to each person's pelvis (head heights)
TABLE_TOP, TABLE_RADIUS = -3.42, 1.05
CUPS = {"l": (-0.48, -0.12), "r": (0.52, 0.1)}       # world (x, z) of the cups
CUP_RADIUS, CUP_HEIGHT = 0.21, 0.34
WINDOW = (560.0, 120.0, 1840.0, 1010.0)             # inside of the window frame (x0, y0, x1, y1)
WINDOW_LIGHT_A, WINDOW_LIGHT_B = (0.85, -0.3), (-0.85, -0.3)

# Palette: cream walls in afternoon sun and dark wood. Accents are the green outside and the sky blue and sage
# of the two outfits.
WALL_TOP, WALL_LOW, WALL_SHADE = "#efe2cc", "#d9c3a4", "#b89d7c"
SKY_TOP, SKY_LOW, GLASS_GLOW = "#cfe6f2", "#fbf3df", "#fffaf0"
FRAME, FRAME_SHADE, FLOOR, FLOOR_LINE = "#6b4a33", "#4a3222", "#8a6446", "#6f4d35"
WOOD, WOOD_SHADE, WOOD_LIGHT, WOOD_LINE = "#9a6a45", "#6e4a30", "#c08a5c", "#3e2818"
TABLE_TOP_COLOR, TABLE_EDGE, TABLE_LINE = "#e8dccb", "#bfae98", "#5a4636"
CUP, CUP_SHADE, COFFEE, CUP_LINE = "#fbf7f0", "#d8cfc2", "#5a3a26", "#6a5a4a"
LEAF, LEAF_SHADE, LEAF_LIGHT, POT = "#5f8f4a", "#3d6233", "#a6c97a", "#c96f4a"
LAMP, LAMP_GLOW = "#2f2a26", "#ffe2a8"

HER = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, hair="#5a3526", hair_shade="#3a2018", hair_light="#9a6248",
                                         line_hair="#1e100a", iris=("#2a1810", "#6a4028", "#c89060")))
HIM = replace(ch.MALE, palette=replace(ch.MALE.palette, hair="#1c1a20", hair_shade="#0c0b10", hair_light="#4a4658"))
HER_OUTFIT = garment.casual_knit(knit="#a9bf9a", pants="#5d5348", shoes="#3a2a20")
HIM_OUTFIT = garment.casual_shirt(shirt="#8fb3d1", pants="#3c3f48", shoes="#e9e5dc")
SEATED = dict(leg_l=(2.0, 0.0), leg_r=(3.0, 1.0))


def cup_target(side):
    """Where the wrist goes, in front of the cup handle (world coordinates). Pulled back a little toward the person
    so the hand sits beside the cup."""
    x, z = CUPS[side]
    toward = -1.0 if side == "l" else 1.0
    return np.array([x + toward * 0.62, TABLE_TOP - 0.1, z - 0.1])


def lap_target(x_sign, seat_x, z):
    """On the thigh where the far hand rests (world coordinates). About half a thigh length toward the knee."""
    return np.array([seat_x + x_sign * 1.1, SEAT_HEIGHT - 0.5, z])


SEAT_HEIGHT = -2.3      # world y of the seated pelvis (almost the value set by shin and foot length)


def make_people():
    """She looks right from screen left, he looks left from screen right. Near arms go to the cups, far arms rest on
    the thighs."""
    her = STAGE.place(HER, -SEAT_GAP, 0.0, 78.0, outfit=HER_OUTFIT, lean=8.0, head=-3.0, head_turn=-6.0,
                      reach={"arm_l": cup_target("l"), "arm_r": lap_target(1.0, -SEAT_GAP, 0.3)},
                      swing={"leg_l": (86.0, -6.0), "leg_r": (88.0, 4.0)}, **SEATED)
    him = STAGE.place(HIM, SEAT_GAP, 0.15, -80.0, outfit=HIM_OUTFIT, lean=12.0, head=4.0, head_turn=8.0,
                      reach={"arm_r": cup_target("r"), "arm_l": lap_target(-1.0, SEAT_GAP, 0.45)},
                      swing={"leg_l": (84.0, 2.0), "leg_r": (88.0, -6.0)}, **SEATED)
    return her, him


# ---------- room ----------

def paint_room(cv, rng):
    floor_y = STAGE.point(0.0, 0.0, 3.2)[1]
    cv.fill(cv.full(), Linear([WALL_TOP, WALL_LOW], (0, 0), (0, floor_y)))
    paint_window(cv, rng)
    cv.fill(cv.shape(g.rect(0, floor_y, WIDTH, HEIGHT - floor_y)), Linear([FLOOR, "#6a4a33"], (0, floor_y), (0, HEIGHT)))
    for index in range(7):
        y = floor_y + (HEIGHT - floor_y) * (index / 7.0) ** 1.4
        cv.stroke([(0, y), (WIDTH, y)], FLOOR_LINE, width=1.4, opacity=0.6)
    cv.fill(cv.shape(g.rect(0, floor_y - 18, WIDTH, 18)), WALL_SHADE)
    paint_plant(cv, rng, 2160.0, floor_y)
    paint_lamp(cv)


def paint_window(cv, rng):
    x0, y0, x1, y1 = WINDOW
    glass = cv.shape(g.rect(x0, y0, x1 - x0, y1 - y0))
    cv.fill(glass, Linear([SKY_TOP, SKY_LOW], (0, y0), (0, y1)))
    # Trees outside the window: painted softly so they sit behind the figures indoors.
    for cx, cy, w, h in ((760, 780, 520, 420), (1530, 820, 620, 460), (1180, 900, 420, 260)):
        motifs.canopy(cv, cx, cy, w, h, light=(0.4, -0.8), palette=("#cfe3b0", "#9fc48a", "#7fa86e"), rng=rng)
    cv.fill(glass, GLASS_GLOW, opacity=0.35)
    cv.fill(cv.shape(g.ellipse((x0 + x1) / 2, y0 + 360, 700, 420), soft=180), "#ffffff", opacity=0.45, clip=glass)
    for x in np.linspace(x0, x1, 4)[1:-1]:
        cv.fill(cv.shape(g.rect(x - 10, y0, 20, y1 - y0)), FRAME)
    cv.fill(cv.shape(g.rect(x0, y0 + (y1 - y0) * 0.38 - 9, x1 - x0, 18)), FRAME)
    outer = cv.shape(g.rect(x0 - 34, y0 - 34, x1 - x0 + 68, y1 - y0 + 68)) - glass
    cv.fill(outer, FRAME)
    cv.fill(cv.shape(g.rect(x0 - 50, y1 + 20, x1 - x0 + 100, 26)), FRAME_SHADE)


def paint_plant(cv, rng, x, floor_y):
    pot = cv.shape(g.polygon([(x - 90, floor_y - 210), (x + 90, floor_y - 210), (x + 70, floor_y), (x - 70, floor_y)]))
    cv.fill(pot, POT)
    cv.fill(cv.form_shadow(pot, (-0.6, -0.5), 0.4), "#9a4a30")
    motifs.canopy(cv, x - 10, floor_y - 420, 360, 420, light=(-0.6, -0.6), palette=(LEAF_LIGHT, LEAF, LEAF_SHADE), rng=rng)


def paint_lamp(cv):
    cx = 1200.0
    cv.stroke([(cx, 0), (cx, 190)], LAMP, width=3)
    shade = cv.shape(g.polygon([(cx - 26, 190), (cx + 26, 190), (cx + 120, 300), (cx - 120, 300)]))
    cv.fill(shade, LAMP)
    cv.fill(cv.shape(g.ellipse(cx, 304, 96, 18)), LAMP_GLOW)
    cv.fill(cv.shape(g.ellipse(cx, 420, 360, 220), soft=120), LAMP_GLOW, opacity=0.35, blend=Blend.SCREEN)


# ---------- furniture ----------

def paint_box(cv, x_range, y_range, z_range, colors=(WOOD, WOOD_SHADE, WOOD_LIGHT)):
    base, shade, light = colors
    tone = {"top": light, "front": base, "back": base, "left": shade, "right": shade, "bottom": shade}
    for name, path, _ in STAGE.box(x_range, y_range, z_range):
        face = cv.shape(path)
        cv.fill(face, tone[name])
        cv.fill(cv.contour(face, 1.4), WOOD_LINE, opacity=0.8)


def paint_chair(cv, model):
    """A backrest behind the person, a seat under the hips, legs at the four corners of the seat."""
    x, seat_y, z = model.world[0], model.world[1] + 0.44, model.world[2]
    back = -1.0 if x < 0 else 1.0
    span = (x - 0.7, x + 0.7) if back < 0 else (x - 0.7, x + 0.7)
    for leg_x in (span[0] + 0.08, span[1] - 0.08):
        for leg_z in (z - 0.6, z + 0.6):
            paint_box(cv, (leg_x - 0.05, leg_x + 0.05), (seat_y, 0.0), (leg_z - 0.05, leg_z + 0.05))
    paint_box(cv, span, (seat_y, seat_y + 0.14), (z - 0.68, z + 0.68))
    post_x = x + back * 0.62
    paint_box(cv, (post_x - 0.07, post_x + 0.07), (seat_y - 1.9, seat_y), (z - 0.62, z + 0.62))


def paint_table_base(cv):
    cv.fill(cv.shape(STAGE.ellipse((0.0, 0.0), 1.1, 0.0, radius_z=0.8), soft=20), "#3a2618", opacity=0.35)
    foot = STAGE.ellipse((0.0, 0.0), 0.62, 0.0)
    cv.fill(cv.shape(foot), WOOD_SHADE)
    stem = STAGE.cylinder((0.0, 0.0), 0.11, TABLE_TOP + 0.1, -0.05)
    shape = cv.shape(stem["side"])
    cv.fill(shape, Linear([WOOD_SHADE, WOOD, WOOD_SHADE], (1180, 0), (1220, 0)))
    cv.fill(cv.contour(shape, 1.4), WOOD_LINE)


def paint_table_top(cv):
    rim = STAGE.cylinder((0.0, 0.0), TABLE_RADIUS, TABLE_TOP, TABLE_TOP + 0.09)
    edge = cv.shape(rim["side"])
    cv.fill(edge, TABLE_EDGE)
    top = cv.shape(rim["top"])
    cv.fill(top, TABLE_TOP_COLOR)
    cv.fill(cv.shape(STAGE.ellipse((0.15, 0.0), 0.7, TABLE_TOP, radius_z=0.5), soft=30), "#ffffff", opacity=0.35,
            clip=top)
    cv.fill(cv.contour(edge | top, 2.0), TABLE_LINE)


def paint_cup(cv, side):
    x, z = CUPS[side]
    saucer = cv.shape(STAGE.ellipse((x, z), CUP_RADIUS * 1.9, TABLE_TOP - 0.01))
    cv.fill(saucer, CUP_SHADE)
    cv.fill(cv.contour(saucer, 1.2), CUP_LINE)
    body = STAGE.cylinder((x, z), CUP_RADIUS, TABLE_TOP - CUP_HEIGHT, TABLE_TOP - 0.02)
    side_shape = cv.shape(body["side"])
    cv.fill(side_shape, CUP)
    cv.fill(cv.form_shadow(side_shape, (-0.6, -0.4), 0.4), CUP_SHADE)
    top = cv.shape(body["top"])
    cv.fill(top, CUP_SHADE)
    cv.fill(cv.shape(STAGE.ellipse((x, z), CUP_RADIUS * 0.82, TABLE_TOP - CUP_HEIGHT + 0.03)), COFFEE)
    cv.fill(cv.contour(side_shape | top, 1.4), CUP_LINE)
    handle_x = x + (-1.0 if side == "l" else 1.0) * CUP_RADIUS
    handle = STAGE.project([(handle_x, TABLE_TOP - CUP_HEIGHT * 0.75, z), (handle_x + (-0.1 if side == "l" else 0.1),
                            TABLE_TOP - CUP_HEIGHT * 0.5, z), (handle_x, TABLE_TOP - CUP_HEIGHT * 0.25, z)])
    cv.stroke(g.spline(handle, closed=False), CUP_LINE, width=5)
    cv.stroke(g.spline(handle, closed=False), CUP, width=2.5)
    steam = STAGE.project([(x, TABLE_TOP - CUP_HEIGHT - 0.05, z), (x + 0.08, TABLE_TOP - CUP_HEIGHT - 0.3, z),
                           (x - 0.06, TABLE_TOP - CUP_HEIGHT - 0.55, z), (x + 0.04, TABLE_TOP - CUP_HEIGHT - 0.8, z)])
    cv.stroke(g.spline(steam, closed=False), "#ffffff", width=9, taper=(0.2, 1, 0.6, 0), opacity=0.45, soft=4)


# ---------- figures ----------

def paint_person(scale, seed, model, defer, light):
    """Paint one figure on a transparent canvas and put a rim light on the window-side contour."""
    layer = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    ch.paint_figure(layer, model, defer=defer)
    anime.rim_light(layer, light, width=4.0, tint="#fff3d6", opacity=0.8)
    return layer


def main(out_dir="out", scale=1.0, seed=83):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_room(cv, rng)
    her, him = make_people()
    for model in (her, him):
        x, z = model.world[0], model.world[2]
        cv.fill(cv.shape(STAGE.ellipse((x + 0.5 * np.sign(-x), z), 1.3, 0.0, radius_z=0.7), soft=24), "#3a2618",
                opacity=0.35)
        paint_chair(cv, model)
    paint_table_base(cv)
    cv.paste(paint_person(scale, seed, her, ("arm_l",), WINDOW_LIGHT_A))
    cv.paste(paint_person(scale, seed + 1, him, ("arm_r",), WINDOW_LIGHT_B))
    paint_table_top(cv)
    for side in "lr":
        paint_cup(cv, side)
    ch.paint_deferred(cv, her, ("arm_l",))
    ch.paint_deferred(cv, him, ("arm_r",))
    io.save(cv.guide_image(), out_dir / "cafe_1_guide.png")
    image = anime.finish(cv, diffusion=0.18, bloom=0.3, shadows="#4a3a3a", highlights="#fff2dc")
    image = post.light_gradient(image, "#ffe9c0", (0.5, 0.1), (0.5, 0.8), strength=0.12)
    return io.save(post.vignette(image, strength=0.16), out_dir / "anime_cafe_talk.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
