"""Anime style example: adult male full-body base (front, back).

Drawn with the same workflow as the female base (anime_figure_base.py), from head to toe without covering.
Process: head-unit guides → pose (rig) → whole-body mass → upper body muscles → lower body muscles → hands and feet
→ face or back hair.
Adult male markers: eight-head rig, broad shoulders and narrow pelvis, an angular jaw and narrow eyes, Adam's apple,
sternocleidomastoid, pectorals, abdominals, pelvic V line.
The groin gets the same treatment as the female base: only light and shade on a round mass without detail, and no
genital detail.
Run: python anime_figure_base_male.py [output_dir] [scale]
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
NECK_STRETCH = 0.72
HEAD_TOP_Y = PELVIS_Y - (2.35 + 0.5 * NECK_STRETCH + 1.0) * UNIT

# Palette: a slightly more tanned skin tone on the same paper as the female base. Dark brown hair tightens the
# frame.
PAPER_TOP, PAPER_LOW, GUIDE = "#eef1f7", "#dde3ee", "#b9c3d8"
SKIN, SKIN_SHADE, SKIN_DEEP, SKIN_LIGHT = "#efc3a4", "#cf8f78", "#9c5a4c", "#fde6d4"
NIPPLE, NAIL = "#c98472", "#f6d8c8"
HAIR, HAIR_SHADE, HAIR_LIGHT = "#2b211d", "#17110f", "#6b5244"
IRIS_TOP, IRIS_MID, IRIS_LOW = "#1a1614", "#4a3a30", "#a08060"
LINE_SKIN, LINE_HAIR, LINE_DARK = "#6e3a30", "#0d0a09", "#1a0e0c"
LINE_WIDTH = 2.4

# Broad shoulders and rib cage, narrow waist and pelvis, thick limbs and neck.
ADULT_MALE = figure.Build(shoulder=0.94, ribcage=0.8, waist=0.64, hip=0.7, arm=1.06, leg=1.0, neck=0.46)


@dataclass
class Model:
    """One person: body rig and face frame (skull radius 1, head height 2.3 in this unit)."""
    body: figure.Figure
    head: g.Frame


def make_model(center_x, **pose):
    body = figure.Figure(g.Frame(origin=(center_x, PELVIS_Y), unit=UNIT), build=ADULT_MALE,
                         stretch={"neck": NECK_STRETCH}, shoulder_drop=0.14, **pose)
    head_angle = body.frame.rotate + body.angles["head"]
    return Model(body, g.Frame(body.head_frame().point(0.0, -0.06), unit=UNIT / 2.3, rotate=head_angle))


# A relaxed male stance tilts the pelvis and shoulders less than the female one. Broad back muscles hold the
# arms a little farther from the body.
FRONT = make_model(450.0, hip_tilt=-4, chest_tilt=3, spine=-1, head=-2,
                   arm_l=(14, 7), arm_r=(15, 5), leg_l=(6, 1), leg_r=(3, -1))
BACK = make_model(1160.0, hip_tilt=4, chest_tilt=-3, spine=1, head=2,
                  arm_l=(15, 5), arm_r=(14, 7), leg_l=(3, -1), leg_r=(6, 1))


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
        cv.fill(cv.shape(g.ellipse(x + 20, floor + 4, 190, 24), soft=10), "#9aa4c0", opacity=0.45)


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
    # Muscle lights are large masses, so their edges loosen in proportion to size, or they look like stains.
    soft = max(min(rx, ry) * 0.5, 0.03) * UNIT
    cv.fill(cv.shape(g.ellipse(center[0], center[1], rx * UNIT, ry * UNIT, angle), soft=soft), SKIN_LIGHT,
            opacity=opacity, clip=clip)


def lit(side):
    """Light on limbs on the side away from the light stays weak. The light comes from screen left, so l is the lit
    side."""
    return 1.0 if (side == "l") == (LIGHT[0] < 0) else 0.4


def on_bone(body, start, end, t, out):
    """A point on a bone. t runs 0-1 from the start joint to the end joint, out is the offset away from the body
    (head heights)."""
    a, b = np.array(body.joint(start)), np.array(body.joint(end))
    heading = (b - a) / np.linalg.norm(b - a)
    across = np.array([-heading[1], heading[0]])
    pelvis_x = body.joint("pelvis")[0]
    if np.dot(across, (a - (pelvis_x, a[1]))) < 0.0:
        across = -across
    return a + (b - a) * t + across * out * UNIT


def groin_volume(body):
    """A simple round mass of the groin. A surface that takes only light and shade, without detail."""
    return g.ellipse(*body.on_pelvis(0.0, 0.47), UNIT * 0.1, UNIT * 0.14)


def relaxed_hand(body, side):
    # A hanging hand has the palm toward the thigh. The hand frame looks down rotated 180 degrees, so only the
    # right hand is flipped.
    return figure.hand_side(body.hand_frame(side, flip=(side == "r")), curl=0.3)


def body_paths(body, back_view):
    """Outline for painting the whole body as one mass. Including feet and palms avoids broken lines at the ankles
    and wrists."""
    foot_view = "bare_back" if back_view else "bare_front"
    paths = (body.neck() + body.torso()
             + [path for side in "lr" for bone in ("upper_arm", "forearm", "thigh", "shin")
                for path in body.limb(bone, side)]
             + [path for side in "lr" for path in body.foot(side, view=foot_view, turn=10)]
             + [path for side in "lr" for path in relaxed_hand(body, side).parts["palm"]])
    return paths if back_view else paths + [groin_volume(body)]


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
            light_spot(cv, ankle + (0, UNIT * 0.34), 0.09, 0.07, body_shape, opacity=0.6)
            inner_line(cv, [ankle + (0, -UNIT * 0.24), ankle + (0, UNIT * 0.12)], body_shape, width=1.5, opacity=0.5)
            continue
        for toe, nail in reversed(body.toes(side, turn=10)):
            digit = cv.shape(toe)
            cv.fill(digit, SKIN)
            cv.fill(cv.form_shadow(digit, LIGHT, 0.35), SKIN_SHADE)
            cv.fill(cv.form_light(digit, LIGHT, 0.15, soft=0.4), SKIN_LIGHT, opacity=0.6)
            cv.fill(cv.contour(digit, 1.3), LINE_SKIN)
            cv.fill(cv.shape(nail), NAIL, opacity=0.9)
            cv.stroke(nail, LINE_SKIN, width=0.8, closed=True, opacity=0.4)
        frame = g.Frame(tuple(ankle), UNIT, body.frame.rotate - sign * 10, flip=sign < 0)
        inner_line(cv, frame([(-0.02, 0.08), (-0.07, 0.3)]), body_shape, width=1.3, opacity=0.5)
        inner_line(cv, frame([(0.04, 0.1), (0.06, 0.3)]), body_shape, width=1.1, opacity=0.35)
        light_spot(cv, frame.point(-0.1, 0.0), 0.03, 0.04, body_shape, opacity=0.8)


def paint_arm_muscles(cv, body, body_shape, back_view):
    """Arms: lower border of the deltoid, light on the biceps or triceps, line of the outer forearm muscle."""
    for side in "lr":
        shoulder, elbow, wrist = "shoulder_" + side, "elbow_" + side, "wrist_" + side
        inner_line(cv, [on_bone(body, shoulder, elbow, 0.08, -0.2), on_bone(body, shoulder, elbow, 0.36, -0.1),
                        on_bone(body, shoulder, elbow, 0.5, 0.2)], body_shape, width=1.6, opacity=0.6)
        light_spot(cv, on_bone(body, shoulder, elbow, 0.2, 0.05), 0.12, 0.14, body_shape, opacity=0.5 * lit(side))
        light_spot(cv, on_bone(body, shoulder, elbow, 0.68, -0.04 if back_view else 0.0), 0.08, 0.2, body_shape,
                   opacity=0.45 * lit(side))
        inner_line(cv, [on_bone(body, shoulder, elbow, 0.62, 0.22), on_bone(body, shoulder, elbow, 0.9, 0.19)],
                   body_shape, width=1.3, opacity=0.45)
        inner_line(cv, [on_bone(body, elbow, wrist, 0.05, 0.12), on_bone(body, elbow, wrist, 0.4, 0.06),
                        on_bone(body, elbow, wrist, 0.75, 0.0)], body_shape, width=1.3, opacity=0.45)
        light_spot(cv, on_bone(body, elbow, wrist, 0.22, 0.08), 0.07, 0.16, body_shape, opacity=0.4 * lit(side))


def paint_leg_muscles(cv, body, body_shape, back_view):
    """Legs: borders of the thigh muscles, the teardrop muscle above the inner knee, knee, shin, the two heads of
    the calf."""
    for side in "lr":
        sign = -1.0 if side == "l" else 1.0
        hip, knee, ankle = "hip_" + side, "knee_" + side, "ankle_" + side
        knee_point = np.array(body.joint(knee))
        if not back_view:
            # Sartorius: a long line slanting from the outside of the pelvis to the inner knee.
            inner_line(cv, [on_bone(body, hip, knee, 0.05, 0.28), on_bone(body, hip, knee, 0.5, 0.0),
                            on_bone(body, hip, knee, 0.92, -0.22)], body_shape, width=1.4, opacity=0.5)
            inner_line(cv, [on_bone(body, hip, knee, 0.35, 0.38), on_bone(body, hip, knee, 0.85, 0.24)], body_shape,
                       width=1.3, opacity=0.4)
            # Vastus medialis (the teardrop mass above the inner knee).
            light_spot(cv, on_bone(body, hip, knee, 0.82, -0.12), 0.1, 0.13, body_shape, opacity=0.5 * lit(side))
            inner_line(cv, [on_bone(body, hip, knee, 0.72, -0.2), on_bone(body, hip, knee, 0.88, -0.24),
                            on_bone(body, hip, knee, 0.97, -0.12)], body_shape, width=1.3, opacity=0.55)
            light_spot(cv, knee_point + (0, -UNIT * 0.04), 0.07, 0.08, body_shape, opacity=0.5 * lit(side))
            inner_line(cv, [knee_point + (-UNIT * 0.09, UNIT * 0.13), knee_point + (0, UNIT * 0.17),
                            knee_point + (UNIT * 0.09, UNIT * 0.13)], body_shape, width=1.4, opacity=0.6)
            inner_line(cv, [on_bone(body, knee, ankle, 0.18, 0.0), on_bone(body, knee, ankle, 0.85, -0.03)],
                       body_shape, width=1.2, opacity=0.4)
            # The outer calf mass bulges beside the shin.
            inner_line(cv, [on_bone(body, knee, ankle, 0.12, 0.2), on_bone(body, knee, ankle, 0.38, 0.23),
                            on_bone(body, knee, ankle, 0.6, 0.12)], body_shape, width=1.3, opacity=0.45)
            continue
        # Back: the two hamstring heads, the crease and tendons behind the knee, the two heads of the calf and
        # the Achilles tendon.
        inner_line(cv, [on_bone(body, hip, knee, 0.35, 0.02), on_bone(body, hip, knee, 0.88, 0.04)], body_shape,
                   width=1.3, opacity=0.4)
        inner_line(cv, [knee_point + (-UNIT * 0.13, UNIT * 0.02), knee_point + (0, UNIT * 0.05),
                        knee_point + (UNIT * 0.13, UNIT * 0.02)], body_shape, width=1.4, opacity=0.6)
        for offset in (-1.0, 1.0):
            inner_line(cv, [knee_point + (offset * UNIT * 0.15, -UNIT * 0.14),
                            knee_point + (offset * UNIT * 0.15, UNIT * 0.12)], body_shape, width=1.2, opacity=0.4)
        for out, size in ((-0.08, 0.08), (0.09, 0.075)):
            light_spot(cv, on_bone(body, knee, ankle, 0.3, out * sign * -1), size, 0.17, body_shape,
                       opacity=0.4 * lit(side))
        inner_line(cv, [on_bone(body, knee, ankle, 0.14, 0.0), on_bone(body, knee, ankle, 0.42, 0.0)], body_shape,
                   width=1.2, opacity=0.4)
        inner_line(cv, [on_bone(body, knee, ankle, 0.08, 0.18), on_bone(body, knee, ankle, 0.32, 0.22),
                        on_bone(body, knee, ankle, 0.58, 0.1)], body_shape, width=1.3, opacity=0.45)
        inner_line(cv, [on_bone(body, knee, ankle, 0.08, -0.18), on_bone(body, knee, ankle, 0.3, -0.2),
                        on_bone(body, knee, ankle, 0.55, -0.08)], body_shape, width=1.3, opacity=0.45)


# ---------- front ----------

def paint_front_upper(cv, model, body_shape):
    b = model.body
    shade(cv, model.head([(-0.8, 1.0), (0.9, 1.0), (0.8, 2.0), (0.1, 2.2), (-0.5, 1.9)]), body_shape)
    # Neck: two sternocleidomastoid lines meeting from below the ears at the hollow at the base of the neck,
    # and the Adam's apple.
    for sign in (-1.0, 1.0):
        inner_line(cv, [model.head.point(sign * 0.72, 1.2), b.on_thorax(sign * 0.12, -0.3), b.on_thorax(sign * 0.05, -0.02)],
                   body_shape, width=1.5, opacity=0.6)
    inner_line(cv, [b.on_thorax(-0.04, -0.4), b.on_thorax(0.0, -0.36), b.on_thorax(0.04, -0.4)], body_shape, width=1.6)
    light_spot(cv, b.on_thorax(0.0, -0.42), 0.035, 0.05, body_shape, opacity=0.6)
    for sign in (-1.0, 1.0):
        # Armpits, collarbones, serratus.
        shade(cv, [b.on_thorax(sign * 0.66, 0.16), b.on_thorax(sign * 0.86, 0.06), b.on_thorax(sign * 0.82, 0.62),
                   b.on_thorax(sign * 0.7, 0.5)], body_shape)
        inner_line(cv, [b.on_thorax(sign * 0.08, -0.03), b.on_thorax(sign * 0.4, -0.1), b.on_thorax(sign * 0.76, -0.04)],
                   body_shape, width=1.7)
        for row in range(3):
            y = 0.82 + row * 0.16
            inner_line(cv, [b.on_thorax(sign * 0.76, y), b.on_thorax(sign * 0.66, y + 0.08)], body_shape, width=1.2,
                       opacity=0.45)
        # Pectoralis major: a broad plate from the sternum to the armpit. A shade band along the lower border
        # and light on top.
        lower = [b.on_thorax(sign * 0.04, 0.6), b.on_thorax(sign * 0.3, 0.7), b.on_thorax(sign * 0.56, 0.62),
                 b.on_thorax(sign * 0.72, 0.34)]
        shade(cv, lower + [b.on_thorax(sign * 0.62, 0.74), b.on_thorax(sign * 0.3, 0.82), b.on_thorax(sign * 0.04, 0.74)],
              body_shape, opacity=0.85, soft=UNIT * 0.02)
        inner_line(cv, lower, body_shape, width=2.0, taper=(0.3, 1, 1, 0.2))
        light_spot(cv, b.on_thorax(sign * 0.36 - 0.05, 0.3), 0.2, 0.12, body_shape, opacity=0.55)
        nipple = b.on_thorax(sign * 0.42, 0.52)
        cv.fill(cv.shape(g.ellipse(nipple[0], nipple[1], UNIT * 0.026, UNIT * 0.022)), NIPPLE, clip=body_shape)
    inner_line(cv, [b.on_thorax(0.0, 0.1), b.on_thorax(0.0, 0.6)], body_shape, width=1.5, opacity=0.6)


def paint_front_abdomen(cv, model, body_shape):
    """Abdominals: the linea alba, both borders of the rectus abdominis, three horizontal segment lines, navel,
    obliques, pelvic V line."""
    b = model.body
    inner_line(cv, [b.on_thorax(0.0, 0.78), b.on_pelvis(0.0, -0.95), b.on_pelvis(0.0, -0.5)], body_shape, width=1.6,
               opacity=0.65)
    for sign in (-1.0, 1.0):
        inner_line(cv, [b.on_thorax(sign * 0.3, 0.84), b.on_thorax(sign * 0.33, 1.2), b.on_pelvis(sign * 0.3, -0.8),
                        b.on_pelvis(sign * 0.18, -0.35)], body_shape, width=1.4, opacity=0.45)
        for start, end in (((0.04, 1.0), (0.3, 0.98)), ((0.04, 1.26), (0.32, 1.24))):
            inner_line(cv, [b.on_thorax(sign * start[0], start[1]), b.on_thorax(sign * end[0], end[1])], body_shape,
                       width=1.4, opacity=0.5)
        inner_line(cv, [b.on_pelvis(sign * 0.04, -0.98), b.on_pelvis(sign * 0.3, -1.0)], body_shape, width=1.3,
                   opacity=0.45)
        for y in (0.9, 1.12):
            light_spot(cv, b.on_thorax(sign * 0.17 - 0.03, y), 0.08, 0.06, body_shape, opacity=0.45)
        light_spot(cv, b.on_pelvis(sign * 0.15 - 0.03, -0.86), 0.07, 0.06, body_shape, opacity=0.4)
        # Obliques and the pelvic V line (the line running from the iliac crest down to the groin).
        inner_line(cv, [b.on_thorax(sign * 0.62, 1.12), b.on_pelvis(sign * 0.6, -0.8), b.on_pelvis(sign * 0.58, -0.42)],
                   body_shape, width=1.4, opacity=0.5)
        inner_line(cv, [b.on_pelvis(sign * 0.56, -0.44), b.on_pelvis(sign * 0.36, -0.12), b.on_pelvis(sign * 0.16, 0.24)],
                   body_shape, width=1.8, taper=(0.2, 1, 0.3), opacity=0.75)
        light_spot(cv, b.on_pelvis(sign * 0.5, -0.5), 0.05, 0.1, body_shape, angle=sign * -20, opacity=0.5)
    navel = b.on_pelvis(0.0, -0.72)
    cv.fill(cv.shape(g.ellipse(navel[0], navel[1], UNIT * 0.022, UNIT * 0.034)), SKIN_DEEP, clip=body_shape)


def paint_front_groin(cv, model, body_shape):
    """Groin: a simple round mass. Only a lit top and a shaded bottom, with no inner lines."""
    b = model.body
    volume = cv.shape(groin_volume(b)) & body_shape
    cv.fill(cv.form_shadow(volume, LIGHT, 0.4, soft=0.4), SKIN_SHADE, opacity=0.8)
    light_spot(cv, b.on_pelvis(-0.03, 0.4), 0.05, 0.06, volume, opacity=0.4)
    shade(cv, [b.on_pelvis(-0.2, 0.25), b.on_pelvis(0.2, 0.25), b.on_pelvis(0.14, 0.34), b.on_pelvis(-0.14, 0.34)],
          body_shape, opacity=0.35, soft=UNIT * 0.04)


def paint_face(cv, head):
    """Adult male face: an angular jaw and flat chin tip, long narrow eyes, thick low brows, a long nose bridge,
    thin lips."""
    right = [(0.0, -1.0), (0.62, -0.84), (0.95, -0.3), (0.97, 0.22), (0.92, 0.68), (0.66, 1.1), (0.3, 1.4)]
    chin = [(0.13, 1.47), (-0.13, 1.47)]
    left = [(-x, y) for x, y in reversed(right[1:])]
    outline = g.spline(head(right + chin + left), closed=True, corners=(4, 7, 8, 11))
    for sign in (-1.0, 1.0):
        ear = cv.shape(g.ellipse(*head.point(sign * 0.98, 0.42), head.length(0.15), head.length(0.27)))
        cel_part(cv, ear, shadow=0.4, width=1.6)
    face = cv.shape(outline)
    cv.fill(face, SKIN)
    cv.fill(cv.contour(face, LINE_WIDTH), LINE_SKIN)
    shade(cv, head([(-1.05, -0.95), (1.05, -0.95), (1.0, -0.1), (0.6, -0.2), (0.2, -0.32), (-0.3, -0.26),
                    (-0.8, -0.1), (-1.0, -0.12)]), face)
    # Shade from below the cheekbones to the jaw. On a male face both cheeks look hollow.
    shade(cv, head([(0.97, 0.3), (0.92, 0.68), (0.66, 1.1), (0.34, 1.38), (0.5, 0.96), (0.68, 0.6), (0.74, 0.38)]), face)
    shade(cv, head([(-0.88, 0.66), (-0.66, 0.98), (-0.64, 0.82), (-0.74, 0.62)]), face, opacity=0.25, soft=UNIT * 0.02)
    shade(cv, head([(-0.24, 1.36), (0.24, 1.36), (0.13, 1.47), (-0.13, 1.47)]), face, opacity=0.6)
    # Nose bridge, shadow under the nose tip, philtrum.
    inner_line(cv, head([(0.12, 0.34), (0.15, 0.7), (0.08, 0.9)]), face, width=1.9, taper=(0.1, 0.9, 1))
    shade(cv, head([(-0.1, 0.94), (0.12, 0.9), (0.14, 0.97), (-0.08, 0.99)]), face)
    inner_line(cv, head([(0.0, 1.0), (0.01, 1.08)]), face, width=1.2, opacity=0.4)
    # Mouth: a thin upper lip line and a short shade under the lower lip.
    inner_line(cv, head([(-0.22, 1.14), (-0.06, 1.12), (0.08, 1.13), (0.22, 1.11)]), face, width=2.1,
               taper=(0.3, 1, 1, 0.3), color_value=LINE_DARK, opacity=1.0)
    shade(cv, head([(-0.1, 1.2), (0.1, 1.2), (0.06, 1.25), (-0.06, 1.25)]), face, opacity=0.7)
    for side in (head, head.mirrored()):
        draw_male_eye(cv, side.child(0.44, 0.38, unit=0.235), face)
        brow = side([(0.1, -0.02), (0.5, -0.12), (0.88, -0.06), (0.86, 0.02), (0.5, -0.04), (0.12, 0.06)])
        cv.fill(cv.shape(g.spline(brow, closed=True, corners=(0, 2, 3, 5))), LINE_HAIR)


def draw_male_eye(cv, eye, face):
    """Male eye: a narrow shape one third as tall as it is wide, an upper lid without a wing, the iris slightly
    covered top and bottom."""
    white = cv.shape(g.spline(eye([(-1.0, 0.02), (-0.5, -0.28), (0.2, -0.34), (0.8, -0.22), (1.1, -0.04),
                                   (0.7, 0.2), (0.0, 0.26), (-0.6, 0.18)]), closed=True, corners=(0, 4))) & face
    cv.fill(white, "#f8f2ee")
    iris_path = g.ellipse(*eye.point(0.0, 0.0), eye.length(0.4), eye.length(0.44), eye.rotate)
    iris = cv.shape(iris_path) & white
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
    cv.stroke(g.spline(eye([(-0.6, -0.62), (0.1, -0.74), (0.86, -0.6)]), closed=False), LINE_SKIN, width=1.3,
              taper=(0.2, 1, 0.2), opacity=0.6)


def short_hair(cv, head, back_view):
    """Short hair. The front has bangs falling onto the forehead and sideburns in front of the ears, the back has
    back hair ending short at the nape."""
    if back_view:
        points = [(-1.12, 0.3), (-1.16, -0.4), (-0.86, -1.08), (-0.2, -1.36), (0.5, -1.32), (1.0, -1.0), (1.18, -0.4),
                  (1.12, 0.3), (0.92, 0.72), (0.5, 0.96), (0.0, 1.04), (-0.5, 0.96), (-0.92, 0.72)]
        corners = ()
    else:
        # Bangs swept left from a part on the right. Three thick strands cross the forehead diagonally.
        points = [(-1.04, 0.36), (-1.12, -0.2), (-1.18, -0.8), (-0.82, -1.3), (-0.2, -1.52), (0.5, -1.48),
                  (1.02, -1.18), (1.2, -0.64), (1.1, -0.1), (1.02, 0.36),   # outer contour, right sideburn tip (9)
                  (0.92, 0.3), (0.9, -0.3),                                 # inside of the sideburn
                  (0.62, -0.64),                                            # hairline on the part side (12)
                  (0.3, -0.48), (0.1, -0.36), (-0.08, -0.18),               # notch (13) → strand 1 → tip (15)
                  (-0.2, -0.46), (-0.38, -0.32), (-0.54, -0.14),            # notch (16) → strand 2 → tip (18)
                  (-0.64, -0.42), (-0.8, -0.28), (-0.92, -0.06),            # notch (19) → strand 3 → tip (21)
                  (-0.96, 0.3)]
        corners = (0, 9, 10, 11, 12, 13, 15, 16, 18, 19, 21)
    hair = cv.shape(g.spline(head(points), closed=True, corners=corners))
    cv.fill(hair, HAIR)
    cv.fill(cv.form_shadow(hair, LIGHT, 0.42), HAIR_SHADE)
    band = [(-0.82, -0.72), (-0.4, -0.96), (0.1, -1.04), (0.56, -0.92), (0.5, -0.84), (0.1, -0.94), (-0.4, -0.86),
            (-0.78, -0.62)]
    cv.fill(cv.shape(g.spline(head(band), closed=True, corners=(0, 3, 4, 7))), HAIR_LIGHT, clip=hair)
    strands = ([(0.0, -1.3), (0.06, -0.2), (0.0, 0.9)], [(-0.6, -1.1), (-0.76, -0.1), (-0.66, 0.8)],
               [(0.6, -1.1), (0.78, -0.1), (0.66, 0.8)]) if back_view else \
        ([(0.5, -1.3), (0.3, -0.8), (-0.04, -0.26)], [(0.2, -1.38), (-0.1, -0.8), (-0.5, -0.2)],
         [(-0.2, -1.36), (-0.56, -0.8), (-0.86, -0.12)], [(0.8, -1.0), (0.92, -0.5), (0.96, 0.2)])
    for strand in strands:
        cv.stroke(g.spline(head(strand), closed=False), LINE_HAIR, width=1.4, taper=(0.1, 1, 0.1), clip=hair)
    cv.fill(cv.contour(hair, LINE_WIDTH), LINE_HAIR)


def paint_front(cv):
    model, b = FRONT, FRONT.body
    body_shape = cel_part(cv, figure.shape_of(cv, body_paths(b, back_view=False)))
    paint_front_upper(cv, model, body_shape)
    paint_front_abdomen(cv, model, body_shape)
    paint_front_groin(cv, model, body_shape)
    paint_arm_muscles(cv, b, body_shape, back_view=False)
    paint_leg_muscles(cv, b, body_shape, back_view=False)
    paint_hands_and_feet(cv, b, body_shape, back_view=False)
    paint_face(cv, model.head)
    short_hair(cv, model.head, back_view=False)


# ---------- back ----------

def paint_back(cv):
    """Back: trapezius, shoulder blades, latissimus, erector spinae, lower back dimples, buttocks and the side
    hollows, back of the thighs, calves."""
    model, b = BACK, BACK.body
    body_shape = cel_part(cv, figure.shape_of(cv, body_paths(b, back_view=True)))
    shade(cv, model.head([(-0.8, 0.6), (0.8, 0.6), (0.7, 1.9), (0.0, 2.0), (-0.7, 1.9)]), body_shape, opacity=0.6)
    spine = [b.on_thorax(0.0, -0.3), b.on_thorax(-0.01, 0.5), b.on_thorax(0.0, 1.2), b.on_pelvis(0.01, -0.7),
             b.on_pelvis(0.0, -0.3)]
    inner_line(cv, spine, body_shape, width=2.0, taper=(0.2, 1, 1, 1, 0.3), opacity=0.6)
    for sign in (-1.0, 1.0):
        # Lower border of the trapezius: the two lower sides of the diamond that meets from the shoulders at
        # the middle of the back.
        inner_line(cv, [b.on_thorax(sign * 0.6, 0.02), b.on_thorax(sign * 0.3, 0.5), b.on_thorax(sign * 0.04, 1.2)],
                   body_shape, width=1.4, opacity=0.45)
        # Light on the shoulder blades and the infraspinatus.
        inner_line(cv, [b.on_thorax(sign * 0.24, 0.2), b.on_thorax(sign * 0.28, 0.6), b.on_thorax(sign * 0.46, 0.9)],
                   body_shape, width=1.6, opacity=0.6)
        inner_line(cv, [b.on_thorax(sign * 0.3, 0.2), b.on_thorax(sign * 0.6, 0.12)], body_shape, width=1.3, opacity=0.45)
        light_spot(cv, b.on_thorax(sign * 0.48, 0.42), 0.16, 0.16, body_shape, opacity=0.55)
        # Latissimus: a large wing sweeping down from the armpit to the waist.
        inner_line(cv, [b.on_thorax(sign * 0.76, 0.36), b.on_thorax(sign * 0.6, 1.0), b.on_pelvis(sign * 0.36, -0.9)],
                   body_shape, width=1.5, opacity=0.5)
        # Erector spinae: vertical masses on both sides of the spine groove.
        light_spot(cv, b.on_pelvis(sign * 0.15, -0.95), 0.07, 0.24, body_shape, opacity=0.3)
        cv.fill(cv.shape(g.ellipse(*b.on_pelvis(sign * 0.15, -0.27), UNIT * 0.022, UNIT * 0.028),
                         soft=UNIT * 0.015), SKIN_SHADE, opacity=0.7, clip=body_shape)
        # Buttocks: smaller, more angular masses than the female ones. The side hollows reveal the muscles.
        cheek = cv.shape(g.ellipse(*b.on_pelvis(sign * 0.34, 0.2), UNIT * 0.36, UNIT * 0.38)) & body_shape
        cv.fill(cv.form_shadow(cheek, LIGHT, 0.3), SKIN_SHADE)
        light_spot(cv, b.on_pelvis(sign * 0.36 - 0.08, 0.06), 0.1, 0.09, cheek, opacity=0.6)
        shade(cv, [b.on_pelvis(sign * 0.6, -0.08), b.on_pelvis(sign * 0.68, 0.02), b.on_pelvis(sign * 0.64, 0.26),
                   b.on_pelvis(sign * 0.56, 0.16)], body_shape, opacity=0.35, soft=UNIT * 0.05)
        fold = [b.on_pelvis(sign * 0.05, 0.56), b.on_pelvis(sign * 0.28, 0.6), b.on_pelvis(sign * 0.54, 0.5)]
        shade(cv, fold + [b.on_pelvis(sign * 0.44, 0.64), b.on_pelvis(sign * 0.24, 0.7), b.on_pelvis(sign * 0.06, 0.65)],
              body_shape, opacity=0.6, soft=UNIT * 0.03)
        inner_line(cv, fold, body_shape, width=2.2, taper=(0.3, 1, 0.1), opacity=1.0)
    cleft = [b.on_pelvis(0.0, -0.2), b.on_pelvis(0.02, 0.15), b.on_pelvis(0.0, 0.56)]
    inner_line(cv, cleft, body_shape, width=2.2, taper=(0.1, 1, 0.8), opacity=1.0)
    paint_arm_muscles(cv, b, body_shape, back_view=True)
    paint_leg_muscles(cv, b, body_shape, back_view=True)
    paint_hands_and_feet(cv, b, body_shape, back_view=True)
    for sign in (-1.0, 1.0):
        ear = cv.shape(g.ellipse(*model.head.point(sign * 0.98, 0.42), model.head.length(0.15),
                                 model.head.length(0.27)))
        cel_part(cv, ear, shadow=0.4, width=1.6)
    neck = figure.shape_of(cv, b.neck())
    shade(cv, model.head([(-0.5, 0.9), (0.5, 0.9), (0.45, 1.5), (-0.45, 1.5)]), neck, opacity=0.6)
    short_hair(cv, model.head, back_view=True)


def main(out_dir="out", scale=1.0, seed=61):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sheet(cv)
    paint_front(cv)
    paint_back(cv)
    io.save(cv.guide_image(), out_dir / "base_male_1_guide.png")
    image = anime.finish(cv, diffusion=0.08, bloom=0.0, grade_amount=0.04, aberration=0.0, grain=0.01)
    return io.save(post.vignette(image, strength=0.06), out_dir / "anime_figure_base_male.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
