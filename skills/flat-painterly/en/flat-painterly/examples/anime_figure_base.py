"""Anime style example: adult female full-body base (front, back).

A reference drawing of the body used before drawing clothes, swimwear or other poses. Drawn from head to toe without
covering.
Process: head-unit guides → pose (rig) → whole-body mass → upper body markers → lower body markers → hands and feet
→ face or back hair.
Adult markers: eight-head rig, a face with small eyes and a long jaw, collarbones, ribs and hip bones, a mature
build.
The groin of the lower body is rendered only as a round mass at the level of classical sculpture and anatomy plates,
without genital detail.
Run: python anime_figure_base.py [output_dir] [scale]
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, figure, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1600, 1600
LIGHT = (-0.6, -0.5)
UNIT = 176.0                      # head height (logical units)
PELVIS_Y = 760.0                  # screen height of the pelvis center
HEAD_TOP_Y = PELVIS_Y - 3.71 * UNIT   # crown height with the neck length factor of 0.72 applied

# Palette: one skin tone on light gray-blue paper. The navy of the hair tightens the frame.
PAPER_TOP, PAPER_LOW, GUIDE = "#eef1f7", "#dde3ee", "#b9c3d8"
SKIN, SKIN_SHADE, SKIN_DEEP, SKIN_LIGHT = "#f7d3bf", "#dc9b8f", "#b0656a", "#fff1e8"
NIPPLE, BLUSH = "#d98585", "#ff9aa0"
NAIL = "#f9dcd2"
HAIR, HAIR_SHADE, HAIR_LIGHT = "#22263e", "#12142a", "#5a6aa0"
IRIS_TOP, IRIS_MID, IRIS_LOW = "#2a1a1a", "#7a3a2a", "#e0a060"
LIPS, LIPS_SHADE = "#d4707a", "#9a4050"
LINE_SKIN, LINE_HAIR, LINE_DARK = "#7a3e40", "#0a0b1a", "#1a0e14"
LINE_WIDTH = 2.4

ADULT = figure.Build(shoulder=0.70, ribcage=0.60, waist=0.48, hip=0.82, arm=0.84, leg=1.06, neck=0.33)


@dataclass
class Model:
    """One person: body rig and face frame (skull radius 1, head height 2.3 in this unit)."""
    body: figure.Figure
    head: g.Frame


def make_model(center_x, **pose):
    # Lowering the shoulder joint slightly keeps the round cap of the upper arm from rising above the shoulder
    # line.
    body = figure.Figure(g.Frame(origin=(center_x, PELVIS_Y), unit=UNIT), build=ADULT,
                         stretch={"neck": 0.72}, shoulder_drop=0.12, **pose)
    head_angle = body.frame.rotate + body.angles["head"]
    return Model(body, g.Frame(body.head_frame().point(0.0, -0.06), unit=UNIT / 2.3, rotate=head_angle))


# The front is a relaxed standing pose with a little weight on the left leg (screen right). The back shows the
# same pose from behind.
FRONT = make_model(450.0, hip_tilt=-6, chest_tilt=4, spine=-1, head=-3,
                   arm_l=(11, 5), arm_r=(13, 3), leg_l=(6, 1), leg_r=(3, -1))
BACK = make_model(1160.0, hip_tilt=6, chest_tilt=-4, spine=1, head=3,
                  arm_l=(13, 3), arm_r=(11, 5), leg_l=(3, -1), leg_r=(6, 1))


# ---------- shared ----------

def paint_sheet(cv):
    cv.fill(cv.full(), Linear([PAPER_TOP, PAPER_LOW], (0, 0), (0, HEIGHT)))
    # Head-unit guides. Eight units from crown to sole make eight heads.
    for index in range(9):
        y = HEAD_TOP_Y + index * UNIT
        cv.stroke([(60, y), (WIDTH - 60, y)], GUIDE, width=1.4, opacity=0.8)
    cv.stroke([(805, 40), (805, HEIGHT - 40)], GUIDE, width=1.0, opacity=0.6)
    for model in (FRONT, BACK):
        x = model.body.joint("pelvis")[0]
        floor = HEAD_TOP_Y + 8.04 * UNIT
        cv.fill(cv.shape(g.ellipse(x + 20, floor + 4, 170, 22), soft=10), "#9aa4c0", opacity=0.45)


def cel_part(cv, shape, shadow=0.36, width=LINE_WIDTH):
    """One skin mass: base → first shadow → light side → outer outline."""
    cv.fill(shape, SKIN)
    cv.fill(cv.form_shadow(shape, LIGHT, shadow), SKIN_SHADE)
    cv.fill(cv.form_light(shape, LIGHT, 0.1, soft=0.4), SKIN_LIGHT, opacity=0.6)
    cv.fill(cv.contour(shape, width), LINE_SKIN)
    return shape


def inner_line(cv, points, clip, width=1.6, taper=(0.1, 1, 0.1), color_value=LINE_SKIN, opacity=0.8):
    """Inner body line. Both ends taper so it reads weaker than the outline."""
    cv.stroke(g.spline(points, closed=False), color_value, width=width, taper=taper, opacity=opacity, clip=clip)


def shade(cv, points, clip, color_value=SKIN_SHADE, opacity=1.0, soft=0.0):
    cv.fill(cv.shape(g.spline(points, closed=True), soft=soft), color_value, opacity=opacity, clip=clip)


def light_spot(cv, center, rx, ry, clip, angle=0.0, opacity=0.7):
    cv.fill(cv.shape(g.ellipse(center[0], center[1], rx * UNIT, ry * UNIT, angle), soft=UNIT * 0.03), SKIN_LIGHT,
            opacity=opacity, clip=clip)


def relaxed_hand(body, side):
    # A hanging hand has the palm toward the thigh. The hand frame looks down rotated 180 degrees, so only the
    # right hand is flipped.
    return figure.hand_side(body.hand_frame(side, flip=(side == "r")), curl=0.32)


def body_paths(body, back_view):
    """Outline for painting the whole body as one mass. Including feet and palms avoids broken lines at the ankles
    and wrists."""
    foot_view = "bare_back" if back_view else "bare_front"
    return (body.neck() + body.torso()
            + [path for side in "lr" for bone in ("upper_arm", "forearm", "thigh", "shin")
               for path in body.limb(bone, side)]
            + [path for side in "lr" for path in body.foot(side, view=foot_view, turn=10)]
            + [path for side in "lr" for path in relaxed_hand(body, side).parts["palm"]])


def paint_hands_and_feet(cv, body, body_shape, back_view):
    """Details of fingers and feet. Palms and feet are already in the body mass."""
    for side in "lr":
        hand = relaxed_hand(body, side)
        order = ("pinky", "ring", "middle", "index", "thumb")
        for name in (order[::-1] if back_view else order):
            part = figure.shape_of(cv, hand.parts[name])
            cv.fill(part, SKIN)
            cv.fill(cv.form_shadow(part, LIGHT, 0.35), SKIN_SHADE)
            cv.fill(cv.contour(part, 1.4), LINE_SKIN)
        ankle = np.array(body.joint("ankle_" + side))
        sign = -1.0 if side == "l" else 1.0
        if back_view:
            # Foot seen from behind: round heel and Achilles tendon.
            light_spot(cv, ankle + (0, UNIT * 0.34), 0.09, 0.07, body_shape, opacity=0.6)
            inner_line(cv, [ankle + (0, -UNIT * 0.2), ankle + (0, UNIT * 0.12)], body_shape, width=1.3, opacity=0.4)
            continue
        # Toes: painted one at a time from the little toe toward the big toe so the big toe comes in front,
        # with nails on top.
        for toe, nail in reversed(body.toes(side, turn=10)):
            digit = cv.shape(toe)
            cv.fill(digit, SKIN)
            cv.fill(cv.form_shadow(digit, LIGHT, 0.35), SKIN_SHADE)
            cv.fill(cv.form_light(digit, LIGHT, 0.15, soft=0.4), SKIN_LIGHT, opacity=0.6)
            cv.fill(cv.contour(digit, 1.3), LINE_SKIN)
            cv.fill(cv.shape(nail), NAIL, opacity=0.9)
            cv.stroke(nail, LINE_SKIN, width=0.8, closed=True, opacity=0.4)
        # Tendons on the instep and light on the inner ankle bone (the inner ankle bone is higher than the
        # outer).
        frame = g.Frame(tuple(ankle), UNIT, body.frame.rotate - sign * 10, flip=sign < 0)
        inner_line(cv, frame([(-0.02, 0.08), (-0.07, 0.3)]), body_shape, width=1.2, opacity=0.4)
        light_spot(cv, frame.point(-0.1, 0.0), 0.03, 0.04, body_shape, opacity=0.8)


# ---------- front ----------

def paint_front_upper(cv, model, body_shape):
    b = model.body
    shade(cv, model.head([(-0.7, 1.0), (0.8, 1.0), (0.7, 1.9), (0.1, 2.1), (-0.4, 1.8)]), body_shape)
    for sign in (-1.0, 1.0):
        # Armpits and inner arms, collarbones, rib arch.
        shade(cv, [b.on_thorax(sign * 0.5, 0.12), b.on_thorax(sign * 0.7, 0.04), b.on_thorax(sign * 0.66, 0.7),
                   b.on_thorax(sign * 0.55, 0.55)], body_shape)
        inner_line(cv, [b.on_thorax(sign * 0.1, -0.02), b.on_thorax(sign * 0.36, -0.09),
                        b.on_thorax(sign * 0.58, -0.04)], body_shape)
        inner_line(cv, [b.on_thorax(sign * 0.12, 1.08), b.on_thorax(sign * 0.3, 1.22),
                        b.on_thorax(sign * 0.44, 1.42)], body_shape, width=1.3, opacity=0.45)
    for sign in (-1.0, 1.0):
        cx, cy = b.on_thorax(sign * 0.33 - 0.02, 0.7)
        shade(cv, [(cx - UNIT * 0.3, cy + UNIT * 0.1), (cx + UNIT * 0.3, cy + UNIT * 0.08),
                   (cx + UNIT * 0.26, cy + UNIT * 0.34), (cx, cy + UNIT * 0.42), (cx - UNIT * 0.26, cy + UNIT * 0.32)],
              body_shape)
        outline = [(-0.27, -0.12), (0.0, -0.34), (0.27, -0.1), (0.3, 0.12), (0.03, 0.31), (-0.28, 0.12)]
        breast = cv.shape(g.spline([(cx + x * UNIT, cy + y * UNIT) for x, y in outline], closed=True)) & body_shape
        cv.fill(breast, SKIN)
        cv.fill(cv.form_shadow(breast, LIGHT, 0.38), SKIN_SHADE)
        light_spot(cv, (cx - UNIT * 0.1, cy - UNIT * 0.12), 0.08, 0.05, breast, angle=-20, opacity=0.9)
        inner_line(cv, [(cx - UNIT * 0.27, cy + UNIT * 0.1), (cx - UNIT * 0.1, cy + UNIT * 0.29),
                        (cx + UNIT * 0.12, cy + UNIT * 0.29), (cx + UNIT * 0.28, cy + UNIT * 0.1)], body_shape,
                   width=2.0, taper=(0.1, 1, 1, 0.2))
        nipple = (cx + UNIT * 0.04, cy + UNIT * 0.06)
        cv.fill(cv.shape(g.ellipse(nipple[0], nipple[1], UNIT * 0.038, UNIT * 0.034)), NIPPLE, clip=breast)
    inner_line(cv, [b.on_thorax(-0.03, -0.02), b.on_thorax(0.0, 0.06)], body_shape, width=1.8)
    inner_line(cv, [b.on_pelvis(0.0, -1.2), b.on_pelvis(0.01, -0.9)], body_shape, width=1.2, opacity=0.4)
    navel = b.on_pelvis(0.0, -0.7)
    cv.fill(cv.shape(g.ellipse(navel[0], navel[1], UNIT * 0.022, UNIT * 0.04)), SKIN_DEEP, clip=body_shape)


def paint_front_lower(cv, model, body_shape):
    """Lower body front: hip bones, groin creases, round form of the mons pubis, between the thighs, knees, calves,
    ankle bones."""
    b = model.body
    for sign in (-1.0, 1.0):
        # Light on the corners of the hip bones and the groin creases running down from them (V line).
        light_spot(cv, b.on_pelvis(sign * 0.54, -0.44), 0.05, 0.11, body_shape, angle=sign * -20, opacity=0.5)
        inner_line(cv, [b.on_pelvis(sign * 0.6, -0.44), b.on_pelvis(sign * 0.44, -0.1), b.on_pelvis(sign * 0.2, 0.28),
                        b.on_pelvis(sign * 0.08, 0.44)], body_shape, width=1.6, taper=(0.1, 1, 1, 0.3), opacity=0.7)
        # Border of the outer thigh muscle and the inner thigh shade.
        side = "l" if sign < 0 else "r"
        hip, knee = np.array(b.joint("hip_" + side)), np.array(b.joint("knee_" + side))
        thigh_dir = (knee - hip) / np.linalg.norm(knee - hip)
        across = np.array([-thigh_dir[1], thigh_dir[0]]) * -sign   # unit vector pointing to the outside of the leg
        inner_line(cv, [hip + across * UNIT * 0.3 + thigh_dir * UNIT * 0.6, hip + across * UNIT * 0.27 + thigh_dir * UNIT * 1.3,
                        knee + across * UNIT * 0.14 - thigh_dir * UNIT * 0.2], body_shape, width=1.3, opacity=0.4)
        shade(cv, [hip - across * UNIT * 0.05 + thigh_dir * UNIT * 0.4, hip - across * UNIT * 0.36 + thigh_dir * UNIT * 0.55,
                   knee - across * UNIT * 0.18 - thigh_dir * UNIT * 0.2, knee - across * UNIT * 0.06 - thigh_dir * UNIT * 0.4],
              body_shape, opacity=0.55, soft=UNIT * 0.04)
        # Knees: light on the kneecap, a short line below it, the round flesh of the inner knee.
        light_spot(cv, knee + (0, -UNIT * 0.05), 0.07, 0.08, body_shape, opacity=0.45)
        inner_line(cv, [knee + (-UNIT * 0.08, UNIT * 0.12), knee + (0, UNIT * 0.16), knee + (UNIT * 0.08, UNIT * 0.12)],
                   body_shape, width=1.4, opacity=0.6)
        inner_line(cv, [knee + (-sign * UNIT * 0.15, -UNIT * 0.1), knee + (-sign * UNIT * 0.18, UNIT * 0.05)],
                   body_shape, width=1.3, opacity=0.5)
        # Line of the front shin and the outer calf mass.
        ankle = np.array(b.joint("ankle_" + side))
        inner_line(cv, [knee + (0, UNIT * 0.3), (knee + ankle) / 2 + (sign * UNIT * 0.02, 0), ankle + (0, -UNIT * 0.3)],
                   body_shape, width=1.2, opacity=0.35)
    # Mons pubis: the soft round form at the lower end where the groin creases meet. Only a lit top and a
    # shaded bottom.
    mound = b.on_pelvis(0.0, 0.3)
    light_spot(cv, mound, 0.16, 0.12, body_shape, opacity=0.55)
    shade(cv, [b.on_pelvis(-0.16, 0.4), b.on_pelvis(0.16, 0.4), b.on_pelvis(0.05, 0.58), b.on_pelvis(-0.05, 0.58)],
          body_shape, opacity=0.5, soft=UNIT * 0.04)


def paint_face(cv, head):
    right = [(0.0, -1.0), (0.6, -0.82), (0.93, -0.3), (0.95, 0.18), (0.86, 0.6), (0.6, 1.0), (0.26, 1.34)]
    left = [(-x, y) for x, y in reversed(right[1:])]
    face = cv.shape(g.spline(head(right + [(0.0, 1.45)] + left), closed=True))
    cv.fill(face, SKIN)
    cv.fill(cv.contour(face, LINE_WIDTH), LINE_SKIN)
    shade(cv, head([(-1.05, -0.95), (1.05, -0.95), (1.0, 0.0), (0.6, -0.1), (0.2, -0.3), (-0.3, -0.18),
                    (-0.8, 0.02), (-1.0, -0.05)]), face)
    shade(cv, head([(0.96, 0.3), (0.88, 0.62), (0.6, 1.02), (0.3, 1.3), (0.46, 0.92), (0.66, 0.56), (0.7, 0.36)]), face)
    for cheek, strength in ((-0.55, 0.28), (0.55, 0.2)):
        cv.fill(cv.shape(g.ellipse(*head.point(cheek, 0.74), head.length(0.2), head.length(0.08)),
                         soft=head.length(0.06)), BLUSH, opacity=strength, clip=face)
    inner_line(cv, head([(0.1, 0.42), (0.12, 0.72), (0.06, 0.86)]), face, width=1.7, taper=(0.1, 0.8, 1))
    shade(cv, head([(-0.06, 0.9), (0.1, 0.86), (0.12, 0.93), (-0.04, 0.95)]), face)
    lower = cv.shape(g.spline(head([(-0.18, 1.12), (0.18, 1.12), (0.1, 1.2), (-0.1, 1.2)]), closed=True,
                              corners=(0, 1)))
    cv.fill(lower, LIPS, clip=face)
    cv.fill(cv.shape(g.spline(head([(-0.2, 1.1), (0.0, 1.06), (0.2, 1.1), (0.0, 1.11)]), closed=True,
                              corners=(0, 2))), LIPS_SHADE, clip=face)
    inner_line(cv, head([(-0.22, 1.1), (-0.08, 1.07), (0.0, 1.09), (0.08, 1.07), (0.22, 1.1)]), face, width=2.0,
               taper=(0.4, 1, 1, 1, 0.4), color_value=LINE_DARK, opacity=1.0)
    for side in (head, head.mirrored()):
        draw_adult_eye(cv, side.child(0.45, 0.4, unit=0.24), face)
        cv.stroke(g.spline(side([(0.18, -0.02), (0.46, -0.12), (0.8, -0.04)]), closed=False), LINE_HAIR, width=2.8,
                  taper=(0.7, 1, 0.1))


def draw_adult_eye(cv, eye, face):
    """An adult eye: a wide almond shape, a half-lowered upper lid, an outer corner sweeping out like a wing."""
    white = cv.shape(g.spline(eye([(-1.0, 0.05), (-0.55, -0.32), (0.1, -0.42), (0.7, -0.3), (1.08, -0.08),
                                   (0.7, 0.26), (0.0, 0.36), (-0.6, 0.26)]), closed=True, corners=(0, 4))) & face
    cv.fill(white, "#fbf4f2")
    iris_path = g.ellipse(*eye.point(-0.02, 0.02), eye.length(0.44), eye.length(0.5), eye.rotate)
    iris = cv.shape(iris_path) & white
    cv.fill(iris, Linear([(0.0, IRIS_TOP), (0.5, IRIS_MID), (1.0, IRIS_LOW)], eye.point(0.0, -0.45),
                         eye.point(0.0, 0.5)))
    cv.fill(cv.shape(g.ellipse(*eye.point(-0.02, 0.02), eye.length(0.18), eye.length(0.22), eye.rotate)), "#100808",
            clip=iris)
    toward_light = 1.0 if eye.flip else -1.0
    cv.fill(cv.shape(g.ellipse(*eye.point(0.16 * toward_light, -0.14), eye.length(0.11))), "#ffffff", clip=white)
    lid = [(-1.12, 0.06), (-0.72, -0.36), (0.0, -0.5), (0.72, -0.4), (1.2, -0.12), (1.5, -0.24), (1.12, 0.02),
           (0.7, -0.2), (0.0, -0.24), (-0.66, -0.12)]
    cv.fill(cv.shape(g.spline(eye(lid), closed=True, corners=(0, 5))), LINE_DARK)
    cv.stroke(g.spline(eye([(-0.7, 0.24), (0.0, 0.38), (0.72, 0.26), (1.04, 0.0)]), closed=False), LINE_SKIN,
              width=1.5, taper=(0.1, 1, 1, 0.3))


def bob(cv, head, back_view):
    """Bob. The front has side-parted bangs, the back covers the back of the head and ends at the nape."""
    if back_view:
        points = [(-1.2, -0.2), (-1.0, -0.9), (-0.4, -1.28), (0.3, -1.3), (0.96, -0.98), (1.22, -0.3), (1.2, 0.5),
                  (1.08, 1.2), (0.7, 1.32), (0.3, 1.22), (-0.1, 1.3), (-0.5, 1.2), (-0.9, 1.26), (-1.16, 0.6)]
        corners = ()
    else:
        points = [(-1.16, -0.2), (-1.02, -0.86), (-0.44, -1.26), (0.26, -1.32), (0.9, -1.08), (1.24, -0.56),
                  (1.28, 0.2), (1.22, 0.96), (1.12, 1.58), (0.88, 1.0), (0.8, 0.4), (0.66, 0.1), (0.42, -0.06),
                  (0.3, -0.36), (-0.1, -0.56), (-0.5, -0.58), (-0.86, -0.42), (-1.0, -0.1), (-1.06, 0.36)]
        corners = (8, 10, 12, 16)
    hair = cv.shape(g.spline(head(points), closed=True, corners=corners))
    cv.fill(hair, HAIR)
    cv.fill(cv.form_shadow(hair, LIGHT, 0.4), HAIR_SHADE)
    band = [(-0.86, -0.6), (-0.5, -0.82), (-0.1, -0.92), (0.3, -0.86), (0.62, -0.7),
            (0.56, -0.62), (0.26, -0.74), (-0.1, -0.78), (-0.48, -0.7), (-0.82, -0.5)]
    cv.fill(cv.shape(g.spline(head(band), closed=True, corners=(0, 4, 5, 9))), HAIR_LIGHT, clip=hair)
    strands = ([(0.0, -1.2), (0.1, 0.0), (0.0, 1.2)], [(-0.6, -1.05), (-0.8, 0.1), (-0.7, 1.15)],
               [(0.6, -1.05), (0.8, 0.1), (0.7, 1.2)]) if back_view else \
        ([(0.2, -1.1), (0.5, -0.6), (0.48, -0.1)], [(0.6, -0.96), (0.86, -0.3), (0.86, 0.6)],
         [(0.9, -0.6), (1.06, 0.3), (1.0, 1.2)], [(-0.3, -1.0), (-0.66, -0.7), (-0.9, -0.3)])
    for strand in strands:
        cv.stroke(g.spline(head(strand), closed=False), LINE_HAIR, width=1.4, taper=(0.1, 1, 0.1), clip=hair)
    cv.fill(cv.contour(hair, LINE_WIDTH), LINE_HAIR)


def paint_front(cv):
    model, b = FRONT, FRONT.body
    bob_back = cv.shape(g.spline(model.head([(-1.08, -0.4), (-0.78, -1.1), (0.1, -1.3), (0.94, -1.02), (1.24, -0.3),
                                             (1.26, 0.6), (1.16, 1.36), (0.8, 1.56), (0.3, 1.34), (-0.5, 1.2),
                                             (-1.02, 0.96), (-1.2, 0.2)]), closed=True))
    cv.fill(bob_back, HAIR_SHADE)
    body_shape = cel_part(cv, figure.shape_of(cv, body_paths(b, back_view=False)))
    paint_front_upper(cv, model, body_shape)
    paint_front_lower(cv, model, body_shape)
    paint_hands_and_feet(cv, b, body_shape, back_view=False)
    paint_face(cv, model.head)
    bob(cv, model.head, back_view=False)


# ---------- back ----------

def paint_back(cv):
    """Back: shoulder blades, spine groove, lower back dimples, the two buttocks and the crease under them, back of
    the knees, calves."""
    model, b = BACK, BACK.body
    body_shape = cel_part(cv, figure.shape_of(cv, body_paths(b, back_view=True)))
    shade(cv, model.head([(-0.8, 0.6), (0.8, 0.6), (0.7, 1.9), (0.0, 2.0), (-0.7, 1.9)]), body_shape, opacity=0.6)
    spine = [b.on_thorax(0.0, -0.3), b.on_thorax(-0.01, 0.5), b.on_thorax(0.0, 1.2), b.on_pelvis(0.01, -0.7),
             b.on_pelvis(0.0, -0.3)]
    inner_line(cv, spine, body_shape, width=2.0, taper=(0.2, 1, 1, 1, 0.3), opacity=0.55)
    for sign in (-1.0, 1.0):
        # Shoulder blades: inner edge line and light on top.
        inner_line(cv, [b.on_thorax(sign * 0.2, 0.2), b.on_thorax(sign * 0.24, 0.6), b.on_thorax(sign * 0.4, 0.86)],
                   body_shape, width=1.5, opacity=0.55)
        light_spot(cv, b.on_thorax(sign * 0.4, 0.38), 0.14, 0.18, body_shape, opacity=0.55)
        cv.fill(cv.shape(g.ellipse(*b.on_pelvis(sign * 0.17, -0.27), UNIT * 0.024, UNIT * 0.03), soft=UNIT * 0.015),
                SKIN_SHADE, opacity=0.7, clip=body_shape)
        # Buttocks: separate shadow and light for each round mass, with the crease under the buttocks drawn
        # below.
        # Only shadow and light are laid on top without repainting the base, so they join the shadow of the
        # whole body.
        cheek = cv.shape(g.ellipse(*b.on_pelvis(sign * 0.39, 0.18), UNIT * 0.43, UNIT * 0.41)) & body_shape
        cv.fill(cv.form_shadow(cheek, LIGHT, 0.26), SKIN_SHADE)
        light_spot(cv, b.on_pelvis(sign * 0.42 - 0.08, 0.04), 0.12, 0.09, cheek, opacity=0.6)
        fold = [b.on_pelvis(sign * 0.05, 0.56), b.on_pelvis(sign * 0.3, 0.62), b.on_pelvis(sign * 0.6, 0.5)]
        shade(cv, fold + [b.on_pelvis(sign * 0.5, 0.66), b.on_pelvis(sign * 0.26, 0.72), b.on_pelvis(sign * 0.06, 0.66)],
              body_shape, opacity=0.6, soft=UNIT * 0.03)
        inner_line(cv, fold, body_shape, width=2.2, taper=(0.3, 1, 0.1), opacity=1.0)
        side = "l" if sign < 0 else "r"
        knee, ankle = np.array(b.joint("knee_" + side)), np.array(b.joint("ankle_" + side))
        # The horizontal crease behind the knee and the tendons on both sides, the two round heads of the
        # calf.
        inner_line(cv, [knee + (-UNIT * 0.12, UNIT * 0.02), knee + (0, UNIT * 0.04), knee + (UNIT * 0.12, UNIT * 0.02)],
                   body_shape, width=1.4, opacity=0.6)
        for offset in (-1.0, 1.0):
            inner_line(cv, [knee + (offset * UNIT * 0.13, -UNIT * 0.12), knee + (offset * UNIT * 0.14, UNIT * 0.12)],
                       body_shape, width=1.2, opacity=0.4)
        light_spot(cv, knee + (-UNIT * 0.04, UNIT * 0.45), 0.07, 0.18, body_shape, opacity=0.4)
        inner_line(cv, [knee + (0, UNIT * 0.3), (knee + ankle) / 2, ankle + (0, -UNIT * 0.25)], body_shape, width=1.2,
                   opacity=0.35)
    cleft = [b.on_pelvis(0.0, -0.22), b.on_pelvis(0.02, 0.15), b.on_pelvis(0.0, 0.56)]
    inner_line(cv, cleft, body_shape, width=2.2, taper=(0.1, 1, 0.8), opacity=1.0)
    paint_hands_and_feet(cv, b, body_shape, back_view=True)
    # Back hair and the tips of the ears.
    for sign in (-1.0, 1.0):
        ear = cv.shape(g.ellipse(*model.head.point(sign * 0.98, 0.45), model.head.length(0.14),
                                 model.head.length(0.24)))
        cel_part(cv, ear, shadow=0.4, width=1.6)
    neck = figure.shape_of(cv, b.neck())
    shade(cv, model.head([(-0.5, 1.0), (0.5, 1.0), (0.45, 1.6), (-0.45, 1.6)]), neck, opacity=0.6)
    bob(cv, model.head, back_view=True)


def main(out_dir="out", scale=1.0, seed=59):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sheet(cv)
    paint_front(cv)
    paint_back(cv)
    io.save(cv.guide_image(), out_dir / "base_1_guide.png")
    image = anime.finish(cv, diffusion=0.08, bloom=0.0, grade_amount=0.04, aberration=0.0, grain=0.01)
    return io.save(post.vignette(image, strength=0.06), out_dir / "anime_figure_base.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
