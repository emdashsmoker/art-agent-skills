"""Anime style example: a man standing in a room with morning sunlight (adult nude figure, front view).

Same workflow as the female scene (anime_city_window.py).
Process: window and room → back arm and hand → body masses (cel shadows, designed shadows, muscle lines) → face →
hair → towel → front hand
      → light bars from the blinds → backlit rim → compositing.
Adult male markers: eight-head rig, broad shoulders, an angular jaw and narrow eyes, Adam's apple and
sternocleidomastoid, pectorals and abdominals, pelvic V line.
Run: python anime_morning_light.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Shape, figure, io, motifs, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1100, 1500
LIGHT = (-0.7, -0.45)       # morning sun from the window on screen left
RIM = (-0.85, -0.2)         # light from the same window settles on the left contour of the body

# Palette: cream sunlight and warm walls dominate. The teal of the plant is the complement, and the skin is
# the deepest warm color in the frame.
WALL, WALL_SHADE = "#f1e2cc", "#d9bfa2"
SKY_TOP, SKY_LOW = "#fff6dc", "#ffd9a0"
BLIND, BLIND_SHADE = "#fbf3e2", "#d8c2a2"
LEAF = ("#9fd0a0", "#4f9a7a", "#2a5f58")
POT = "#c97a52"
SUN = "#ffe8b0"
SKIN, SKIN_SHADE, SKIN_DEEP, SKIN_LIGHT = "#eab896", "#c7856c", "#93523f", "#fde2cc"
NIPPLE = "#c07a64"
HAIR, HAIR_SHADE, HAIR_LIGHT = "#3a2a22", "#1e1612", "#8a6a50"
IRIS_TOP, IRIS_MID, IRIS_LOW = "#1a1210", "#5a3a26", "#c09060"
LINE_SKIN, LINE_HAIR, LINE_DARK = "#6a3426", "#120c0a", "#1a0e0c"
TOWEL, TOWEL_SHADE, TOWEL_DEEP = "#f4f1ea", "#c6c1b6", "#8f8a80"
LINE_WIDTH = 2.6

ADULT_MALE = figure.Build(shoulder=0.94, ribcage=0.8, waist=0.64, hip=0.7, arm=1.06, leg=1.0, neck=0.46)
# The arm on screen right is raised to sweep back the hair, and the left arm hangs down. The weight rests on
# the right leg.
BODY = figure.Figure(
    g.Frame(origin=(560, 1000), unit=222), build=ADULT_MALE,
    hip_tilt=6, chest_tilt=-5, spine=2, neck=1, head=4,
    arm_l=(15, 6), arm_r=(142, 280), leg_l=(4, 0), leg_r=(-2, 2),
    stretch={"neck": 0.72, "forearm_r": 0.9}, shoulder_drop=0.14)
UNIT = BODY.frame.unit
HEAD = g.Frame(BODY.head_frame().point(0.0, -0.06), unit=UNIT / 2.3, rotate=BODY.frame.rotate + 4)


# ---------- background ----------

def paint_room(cv, rng):
    cv.fill(cv.full(), Linear([WALL, WALL_SHADE], (0, 0), (WIDTH, HEIGHT)))
    # A large window on screen left with blinds half raised.
    window = cv.shape(g.rect(-20, 80, 520, 1100))
    cv.fill(window, Linear([SKY_TOP, SKY_LOW], (0, 80), (0, 1180)))
    for _ in range(14):
        x, y = rng.uniform(0, 500), rng.uniform(700, 1150)
        cv.fill(cv.shape(g.ellipse(x, y, rng.uniform(30, 90), rng.uniform(20, 40)), soft=20), "#f0d8b0",
                opacity=0.5, clip=window)
    for index in range(16):
        y = 80 + index * 28
        slat = cv.shape(g.rect(-20, y, 520, 16))
        cv.fill(slat, BLIND, clip=window)
        cv.fill(cv.shape(g.rect(-20, y + 12, 520, 4)), BLIND_SHADE, clip=window)
    cv.stroke([(-20, 80), (500, 80)], BLIND_SHADE, width=8)
    cv.fill(cv.shape(g.rect(492, 60, 24, 1140)), "#c9a882")
    cv.fill(cv.shape(g.rect(-20, 1170, 540, 26)), "#c9a882")
    # Bars of light entering from the window and falling on the wall and floor.
    for index in range(7):
        y = 520 + index * 70
        beam = np.array([(500, y), (WIDTH + 40, y + 300), (WIDTH + 40, y + 330), (500, y + 20)])
        cv.fill(cv.shape(beam, soft=6), SUN, opacity=0.45, blend=Blend.SCREEN)
    # A potted plant in the right corner.
    cv.fill(cv.shape(g.polygon([(900, 1260), (1060, 1260), (1040, 1460), (920, 1460)])), POT)
    motifs.canopy(cv, 980, 1080, 300, 320, light=LIGHT, palette=LEAF, puffs=26, puff_size=(0.18, 0.32), rng=rng)


# ---------- body ----------

def cel_part(cv, shape, shadow=0.38, width=LINE_WIDTH):
    """One skin mass: base → first shadow → light side → outer outline."""
    cv.fill(shape, SKIN)
    cv.fill(cv.form_shadow(shape, LIGHT, shadow), SKIN_SHADE)
    cv.fill(cv.form_light(shape, LIGHT, 0.1, soft=0.4), SKIN_LIGHT, opacity=0.6)
    cv.fill(cv.contour(shape, width), LINE_SKIN)
    return shape


def inner_line(cv, points, clip, width=1.8, taper=(0.1, 1, 0.1), color_value=LINE_SKIN, opacity=0.8):
    cv.stroke(g.spline(points, closed=False), color_value, width=width, taper=taper, opacity=opacity, clip=clip)


def shade(cv, points, clip, color_value=SKIN_SHADE, opacity=1.0, soft=0.0):
    cv.fill(cv.shape(g.spline(points, closed=True), soft=soft), color_value, opacity=opacity, clip=clip)


def light_spot(cv, center, rx, ry, clip, angle=0.0, opacity=0.7):
    soft = max(min(rx, ry) * 0.5, 0.03) * UNIT
    cv.fill(cv.shape(g.ellipse(center[0], center[1], rx * UNIT, ry * UNIT, angle), soft=soft), SKIN_LIGHT,
            opacity=opacity, clip=clip)


def on_bone(start, end, t, out):
    """A point on a bone. t runs 0-1 from the start joint to the end joint, out is the offset away from the body
    (head heights)."""
    a, b = np.array(BODY.joint(start)), np.array(BODY.joint(end))
    heading = (b - a) / np.linalg.norm(b - a)
    across = np.array([-heading[1], heading[0]])
    if np.dot(across, a - (BODY.joint("pelvis")[0], a[1])) < 0.0:
        across = -across
    return a + (b - a) * t + across * out * UNIT


def paint_raised_hand(cv):
    """Hand swept back into the hair. Forearm and hand hide behind the head, and only the elbow end of the forearm
    shows beside the head."""
    hand = figure.hand_side(BODY.hand_frame("r", turn=-10, flip=True), curl=0.5)
    cel_part(cv, figure.shape_of(cv, BODY.limb("forearm", "r") + hand.paths()), shadow=0.5)


def paint_body(cv):
    paths = (BODY.neck() + BODY.torso() + BODY.limb("upper_arm", "l") + BODY.limb("upper_arm", "r")
             + BODY.limb("forearm", "l") + BODY.limb("thigh", "l") + BODY.limb("thigh", "r")
             + BODY.limb("shin", "l") + BODY.limb("shin", "r"))
    body = cel_part(cv, figure.shape_of(cv, paths))
    shade(cv, HEAD([(-0.8, 1.0), (0.9, 1.0), (0.8, 2.0), (0.1, 2.2), (-0.5, 1.9)]), body)
    # Sternocleidomastoid, Adam's apple, collarbones.
    for sign in (-1.0, 1.0):
        inner_line(cv, [HEAD.point(sign * 0.72, 1.2), BODY.on_thorax(sign * 0.12, -0.3),
                        BODY.on_thorax(sign * 0.05, -0.02)], body, width=1.6, opacity=0.6)
        inner_line(cv, [BODY.on_thorax(sign * 0.08, -0.03), BODY.on_thorax(sign * 0.4, -0.1),
                        BODY.on_thorax(sign * 0.76, -0.04)], body, width=1.9)
    inner_line(cv, [BODY.on_thorax(-0.04, -0.4), BODY.on_thorax(0.0, -0.36), BODY.on_thorax(0.04, -0.4)], body)
    # Armpit of the raised arm and the opposite armpit.
    shade(cv, [BODY.on_thorax(0.62, 0.0), BODY.on_thorax(0.86, -0.1), BODY.on_thorax(0.84, 0.66),
               BODY.on_thorax(0.7, 0.56)], body)
    shade(cv, [BODY.on_thorax(-0.66, 0.16), BODY.on_thorax(-0.86, 0.06), BODY.on_thorax(-0.82, 0.62),
               BODY.on_thorax(-0.7, 0.5)], body)
    for sign in (-1.0, 1.0):
        lower = [BODY.on_thorax(sign * 0.04, 0.6), BODY.on_thorax(sign * 0.3, 0.7), BODY.on_thorax(sign * 0.56, 0.62),
                 BODY.on_thorax(sign * 0.72, 0.34)]
        shade(cv, lower + [BODY.on_thorax(sign * 0.62, 0.74), BODY.on_thorax(sign * 0.3, 0.82),
                           BODY.on_thorax(sign * 0.04, 0.74)], body, opacity=0.85, soft=UNIT * 0.02)
        inner_line(cv, lower, body, width=2.2, taper=(0.3, 1, 1, 0.2))
        light_spot(cv, BODY.on_thorax(sign * 0.36 - 0.05, 0.3), 0.2, 0.12, body, opacity=0.5)
        nipple = BODY.on_thorax(sign * 0.42, 0.52)
        cv.fill(cv.shape(g.ellipse(nipple[0], nipple[1], UNIT * 0.026, UNIT * 0.022)), NIPPLE, clip=body)
        for row in range(3):
            y = 0.82 + row * 0.16
            inner_line(cv, [BODY.on_thorax(sign * 0.76, y), BODY.on_thorax(sign * 0.66, y + 0.08)], body,
                       width=1.3, opacity=0.45)
    inner_line(cv, [BODY.on_thorax(0.0, 0.1), BODY.on_thorax(0.0, 0.6)], body, width=1.6, opacity=0.6)
    paint_abdomen(cv, body)
    paint_limb_muscles(cv, body)
    return body


def paint_abdomen(cv, body):
    inner_line(cv, [BODY.on_thorax(0.0, 0.78), BODY.on_pelvis(0.0, -0.95), BODY.on_pelvis(0.0, -0.4)], body,
               width=1.7, opacity=0.65)
    for sign in (-1.0, 1.0):
        inner_line(cv, [BODY.on_thorax(sign * 0.3, 0.84), BODY.on_thorax(sign * 0.33, 1.2),
                        BODY.on_pelvis(sign * 0.3, -0.8), BODY.on_pelvis(sign * 0.18, -0.35)], body, width=1.5,
                   opacity=0.45)
        for start, end in (((0.04, 1.0), (0.3, 0.98)), ((0.04, 1.26), (0.32, 1.24))):
            inner_line(cv, [BODY.on_thorax(sign * start[0], start[1]), BODY.on_thorax(sign * end[0], end[1])], body,
                       width=1.5, opacity=0.5)
        inner_line(cv, [BODY.on_pelvis(sign * 0.04, -0.98), BODY.on_pelvis(sign * 0.3, -1.0)], body, width=1.4,
                   opacity=0.45)
        for y in (0.9, 1.12):
            light_spot(cv, BODY.on_thorax(sign * 0.17 - 0.03, y), 0.08, 0.06, body, opacity=0.45)
        inner_line(cv, [BODY.on_thorax(sign * 0.62, 1.12), BODY.on_pelvis(sign * 0.6, -0.8),
                        BODY.on_pelvis(sign * 0.58, -0.42)], body, width=1.5, opacity=0.5)
        inner_line(cv, [BODY.on_pelvis(sign * 0.56, -0.44), BODY.on_pelvis(sign * 0.4, -0.2)], body, width=1.9,
                   taper=(0.2, 1, 0.6), opacity=0.75)
    navel = BODY.on_pelvis(0.0, -0.72)
    cv.fill(cv.shape(g.ellipse(navel[0], navel[1], UNIT * 0.022, UNIT * 0.034)), SKIN_DEEP, clip=body)


def paint_limb_muscles(cv, body):
    shoulder, elbow, wrist = "shoulder_l", "elbow_l", "wrist_l"
    inner_line(cv, [on_bone(shoulder, elbow, 0.08, -0.2), on_bone(shoulder, elbow, 0.36, -0.1),
                    on_bone(shoulder, elbow, 0.5, 0.2)], body, width=1.7, opacity=0.6)
    light_spot(cv, on_bone(shoulder, elbow, 0.2, 0.05), 0.12, 0.14, body, opacity=0.5)
    light_spot(cv, on_bone(shoulder, elbow, 0.66, 0.0), 0.08, 0.2, body, opacity=0.45)
    inner_line(cv, [on_bone(elbow, wrist, 0.05, 0.12), on_bone(elbow, wrist, 0.4, 0.06),
                    on_bone(elbow, wrist, 0.75, 0.0)], body, width=1.4, opacity=0.45)
    # Raised arm: the border of biceps and triceps runs from the armpit to the elbow.
    inner_line(cv, [on_bone("shoulder_r", "elbow_r", 0.15, 0.0), on_bone("shoulder_r", "elbow_r", 0.8, 0.02)], body,
               width=1.5, opacity=0.5)
    for side in "lr":
        hip, knee = "hip_" + side, "knee_" + side
        inner_line(cv, [on_bone(hip, knee, 0.4, 0.36), on_bone(hip, knee, 0.85, 0.24)], body, width=1.4, opacity=0.4)
        light_spot(cv, on_bone(hip, knee, 0.82, -0.12), 0.1, 0.13, body, opacity=0.4 if side == "l" else 0.2)
        inner_line(cv, [on_bone(hip, knee, 0.72, -0.2), on_bone(hip, knee, 0.88, -0.24),
                        on_bone(hip, knee, 0.97, -0.12)], body, width=1.4, opacity=0.55)


# ---------- face and hair ----------

def paint_face(cv):
    right = [(0.0, -1.0), (0.62, -0.84), (0.95, -0.3), (0.97, 0.22), (0.92, 0.68), (0.66, 1.1), (0.3, 1.4)]
    chin = [(0.13, 1.47), (-0.13, 1.47)]
    left = [(-x, y) for x, y in reversed(right[1:])]
    for sign in (-1.0, 1.0):
        ear = cv.shape(g.ellipse(*HEAD.point(sign * 0.98, 0.42), HEAD.length(0.15), HEAD.length(0.27)))
        cel_part(cv, ear, shadow=0.4, width=1.7)
    face = cv.shape(g.spline(HEAD(right + chin + left), closed=True, corners=(4, 7, 8, 11)))
    cv.fill(face, SKIN)
    cv.fill(cv.contour(face, LINE_WIDTH), LINE_SKIN)
    shade(cv, HEAD([(-1.05, -0.95), (1.05, -0.95), (1.0, -0.1), (0.6, -0.2), (0.2, -0.32), (-0.3, -0.26),
                    (-0.8, -0.1), (-1.0, -0.12)]), face)
    shade(cv, HEAD([(0.97, 0.3), (0.92, 0.68), (0.66, 1.1), (0.34, 1.38), (0.5, 0.96), (0.68, 0.6), (0.74, 0.38)]), face)
    shade(cv, HEAD([(-0.24, 1.36), (0.24, 1.36), (0.13, 1.47), (-0.13, 1.47)]), face, opacity=0.6)
    inner_line(cv, HEAD([(0.12, 0.34), (0.15, 0.7), (0.08, 0.9)]), face, width=2.0, taper=(0.1, 0.9, 1))
    shade(cv, HEAD([(-0.1, 0.94), (0.12, 0.9), (0.14, 0.97), (-0.08, 0.99)]), face)
    # A slight smile: one mouth corner rises.
    inner_line(cv, HEAD([(-0.24, 1.12), (-0.06, 1.13), (0.1, 1.12), (0.24, 1.07)]), face, width=2.2,
               taper=(0.3, 1, 1, 0.3), color_value=LINE_DARK, opacity=1.0)
    shade(cv, HEAD([(-0.1, 1.2), (0.1, 1.2), (0.06, 1.25), (-0.06, 1.25)]), face, opacity=0.7)
    for side in (HEAD, HEAD.mirrored()):
        draw_eye(cv, side.child(0.44, 0.38, unit=0.235), face)
        brow = side([(0.1, -0.02), (0.5, -0.14), (0.88, -0.08), (0.86, 0.0), (0.5, -0.06), (0.12, 0.06)])
        cv.fill(cv.shape(g.spline(brow, closed=True, corners=(0, 2, 3, 5))), LINE_HAIR)
    return face


def draw_eye(cv, eye, face):
    white = cv.shape(g.spline(eye([(-1.0, 0.02), (-0.5, -0.28), (0.2, -0.34), (0.8, -0.22), (1.1, -0.04),
                                   (0.7, 0.2), (0.0, 0.26), (-0.6, 0.18)]), closed=True, corners=(0, 4))) & face
    cv.fill(white, "#f8f2ee")
    iris = cv.shape(g.ellipse(*eye.point(0.0, 0.0), eye.length(0.4), eye.length(0.44), eye.rotate)) & white
    cv.fill(iris, Linear([(0.0, IRIS_TOP), (0.5, IRIS_MID), (1.0, IRIS_LOW)], eye.point(0.0, -0.4),
                         eye.point(0.0, 0.4)))
    cv.fill(cv.shape(g.ellipse(*eye.point(0.0, 0.0), eye.length(0.16), eye.length(0.2), eye.rotate)), "#080606",
            clip=iris)
    toward_light = 1.0 if eye.flip else -1.0
    cv.fill(cv.shape(g.ellipse(*eye.point(0.14 * toward_light, -0.12), eye.length(0.08))), "#ffffff", clip=white)
    lid = [(-1.1, 0.04), (-0.7, -0.32), (0.0, -0.44), (0.8, -0.32), (1.16, -0.06), (0.8, -0.2), (0.0, -0.26),
           (-0.66, -0.14)]
    cv.fill(cv.shape(g.spline(eye(lid), closed=True, corners=(0, 4))), LINE_DARK)
    cv.stroke(g.spline(eye([(-0.6, 0.18), (0.0, 0.28), (0.7, 0.2)]), closed=False), LINE_SKIN, width=1.3,
              taper=(0.1, 1, 0.2), opacity=0.7)


def paint_hair(cv):
    """Wet hair swept back by hand. The forehead shows and only a few strands fall onto it."""
    points = [(-1.04, 0.36), (-1.12, -0.2), (-1.2, -0.8), (-0.86, -1.36), (-0.2, -1.58), (0.5, -1.54),
              (1.04, -1.22), (1.22, -0.66), (1.1, -0.1), (1.02, 0.36),
              (0.92, 0.3), (0.9, -0.32), (0.7, -0.66), (0.3, -0.76), (-0.1, -0.8), (-0.5, -0.74),
              (-0.82, -0.6), (-0.92, -0.3), (-0.94, 0.3)]
    hair = cv.shape(g.spline(HEAD(points), closed=True, corners=(0, 9, 10, 18)))
    cv.fill(hair, HAIR)
    cv.fill(cv.form_shadow(hair, LIGHT, 0.4), HAIR_SHADE)
    for strand in ([(-0.7, -0.7), (-0.4, -1.2), (0.2, -1.5)], [(-0.3, -0.78), (0.0, -1.2), (0.6, -1.4)],
                   [(0.2, -0.76), (0.5, -1.1), (0.96, -1.1)], [(-0.9, -0.4), (-0.96, -0.9), (-0.6, -1.36)]):
        cv.stroke(g.spline(HEAD(strand), closed=False), HAIR_LIGHT, width=2.4, taper=(0.1, 1, 0.1), opacity=0.8,
                  clip=hair)
        cv.stroke(g.spline(HEAD(strand), closed=False), LINE_HAIR, width=1.2, taper=(0.1, 1, 0.1), opacity=0.7,
                  clip=hair)
    cv.fill(cv.contour(hair, LINE_WIDTH), LINE_HAIR)
    # Two wet strands falling onto the forehead.
    for lock in ([(-0.2, -0.8), (-0.3, -0.5), (-0.22, -0.2)], [(0.04, -0.8), (0.06, -0.55), (0.14, -0.34)]):
        spine = g.spline(HEAD(lock), closed=False)
        strand = cv.shape(*g.ribbon(spine, (HEAD.length(0.12), HEAD.length(0.08), 0.0)))
        cv.fill(strand, HAIR)
        cv.fill(cv.contour(strand, 1.4), LINE_HAIR)


# ---------- towel and hand ----------

def paint_towel(cv):
    """A towel around the waist. It hangs from the pelvis to mid-thigh, and folds gather toward the tucked end above
    the left hip."""
    top = [BODY.on_pelvis(-0.84, -0.28), BODY.on_pelvis(-0.3, -0.22), BODY.on_pelvis(0.3, -0.24),
           BODY.on_pelvis(0.86, -0.32)]
    bottom = [BODY.on_pelvis(0.98, 1.5), BODY.on_pelvis(0.3, 1.62), BODY.on_pelvis(-0.4, 1.58), BODY.on_pelvis(-1.0, 1.42)]
    towel = cv.shape(g.spline(top + bottom, closed=True, corners=(0, 3, 4, 7)))
    cv.fill(towel, TOWEL)
    cv.fill(cv.form_shadow(towel, LIGHT, 0.42, soft=0.2), TOWEL_SHADE)
    knot = BODY.on_pelvis(-0.56, -0.16)
    for end, bend in ((BODY.on_pelvis(0.7, 1.52), 0.12), (BODY.on_pelvis(0.1, 1.6), 0.08),
                      (BODY.on_pelvis(-0.5, 1.56), 0.04)):
        middle = ((knot[0] + end[0]) / 2 + UNIT * bend, (knot[1] + end[1]) / 2)
        fold = g.spline([knot, middle, end], closed=False)
        cv.stroke(fold, TOWEL_SHADE, width=10, taper=(0.2, 1, 0.6), clip=towel)
        cv.stroke(fold, TOWEL_DEEP, width=2.2, taper=(0.2, 1, 0.2), opacity=0.55, clip=towel)
    flap = cv.shape(g.spline([BODY.on_pelvis(-0.8, -0.28), BODY.on_pelvis(-0.32, -0.23), BODY.on_pelvis(-0.56, 0.16)],
                             closed=True, corners=(0, 1, 2)))
    cv.fill(flap, "#fbfaf6")
    cv.fill(cv.contour(flap, 1.6), TOWEL_DEEP)
    cv.fill(cv.contour(towel, LINE_WIDTH * 0.8), TOWEL_DEEP)
    return towel


def paint_hand(cv):
    hand = figure.hand_side(BODY.hand_frame("l", flip=False), curl=0.35)
    for name in ("palm", "pinky", "ring", "middle", "index", "thumb"):
        part = figure.shape_of(cv, hand.parts[name])
        cv.fill(part, SKIN)
        cv.fill(cv.form_shadow(part, LIGHT, 0.35), SKIN_SHADE)
        cv.fill(cv.contour(part, 1.6), LINE_SKIN)


def paint_blind_light(cv):
    """Sunlight through the gaps of the blinds falls on the body in diagonal stripes. Painted only inside the figure
    silhouette."""
    silhouette = Shape(cv.alpha.copy(), 0, 0)
    for index in range(9):
        y = 330 + index * 92
        band = np.array([(0, y), (WIDTH, y + 330), (WIDTH, y + 362), (0, y + 32)])
        cv.fill(cv.shape(band, soft=5), SUN, opacity=0.35, blend=Blend.SCREEN, clip=silhouette)


def paint_character(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    back = cv.shape(g.spline(HEAD([(-1.1, -0.4), (-0.8, -1.3), (0.2, -1.6), (1.0, -1.3), (1.24, -0.4), (1.14, 0.6),
                                   (0.6, 0.8), (-0.6, 0.8), (-1.14, 0.6)]), closed=True))
    cv.fill(back, HAIR_SHADE)
    paint_raised_hand(cv)
    paint_body(cv)
    paint_face(cv)
    paint_hair(cv)
    paint_towel(cv)
    paint_hand(cv)
    paint_blind_light(cv)
    return cv


def main(out_dir="out", scale=1.0, seed=67):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    background = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_room(background, rng)
    character = paint_character(scale, seed)
    io.save(character.guide_image(), out_dir / "morning_1_character_guide.png")
    anime.rim_light(character, RIM, width=5.0, tint="#fff1c8", opacity=0.85)
    background.paste(character)
    image = anime.finish(background, diffusion=0.2, bloom=0.35, shadows="#5a3a3a", highlights="#fff2d8")
    image = post.light_gradient(image, "#ffe6b0", (0.0, 0.3), (0.7, 0.7), strength=0.15)
    return io.save(post.vignette(image, strength=0.18), out_dir / "anime_morning_light.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
