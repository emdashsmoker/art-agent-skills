"""애니메풍 예제: 성인 남성 전신 베이스(앞면, 뒷면).

여성 베이스(anime_figure_base.py)와 같은 공정으로 그린다. 머리부터 발끝까지 가리지 않는다.
공정: 머리 단위 안내선 → 자세(리그) → 몸 전체 덩어리 → 상반신 근육 → 하반신 근육 → 손과 발 → 얼굴 또는 뒷머리.
성인 남성 표지: 8등신 리그, 넓은 어깨와 좁은 골반, 각진 턱과 가는 눈, 울대뼈, 목빗근, 가슴근, 복근, 골반 V선.
사타구니는 여성 베이스와 같은 수준으로 처리한다. 세부 없는 둥근 덩어리의 빛과 그늘만 두고 성기의 세부는 그리지 않는다.
실행: python anime_figure_base_male.py [출력폴더] [scale]
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
UNIT = 176.0                      # 머리 높이(논리 단위)
PELVIS_Y = 760.0                  # 골반 중심의 화면 높이
NECK_STRETCH = 0.72
HEAD_TOP_Y = PELVIS_Y - (2.35 + 0.5 * NECK_STRETCH + 1.0) * UNIT

# 팔레트: 여성 베이스와 같은 종이 위에 조금 더 그을린 살빛. 짙은 갈색 머리가 화면을 조인다.
PAPER_TOP, PAPER_LOW, GUIDE = "#eef1f7", "#dde3ee", "#b9c3d8"
SKIN, SKIN_SHADE, SKIN_DEEP, SKIN_LIGHT = "#efc3a4", "#cf8f78", "#9c5a4c", "#fde6d4"
NIPPLE, NAIL = "#c98472", "#f6d8c8"
HAIR, HAIR_SHADE, HAIR_LIGHT = "#2b211d", "#17110f", "#6b5244"
IRIS_TOP, IRIS_MID, IRIS_LOW = "#1a1614", "#4a3a30", "#a08060"
LINE_SKIN, LINE_HAIR, LINE_DARK = "#6e3a30", "#0d0a09", "#1a0e0c"
LINE_WIDTH = 2.4

# 넓은 어깨와 흉곽, 좁은 허리와 골반, 굵은 팔다리와 목.
ADULT_MALE = figure.Build(shoulder=0.94, ribcage=0.8, waist=0.64, hip=0.7, arm=1.06, leg=1.0, neck=0.46)


@dataclass
class Model:
    """인물 1명: 몸 리그와 얼굴 좌표계(두개골 반지름이 1, 머리 높이는 이 단위로 2.3)."""
    body: figure.Figure
    head: g.Frame


def make_model(center_x, **pose):
    body = figure.Figure(g.Frame(origin=(center_x, PELVIS_Y), unit=UNIT), build=ADULT_MALE,
                         stretch={"neck": NECK_STRETCH}, shoulder_drop=0.14, **pose)
    head_angle = body.frame.rotate + body.angles["head"]
    return Model(body, g.Frame(body.head_frame().point(0.0, -0.06), unit=UNIT / 2.3, rotate=head_angle))


# 남성의 편한 선 자세는 여성보다 골반과 어깨의 기울기가 작다. 넓은 등근육 때문에 팔이 몸에서 조금 더 떨어진다.
FRONT = make_model(450.0, hip_tilt=-4, chest_tilt=3, spine=-1, head=-2,
                   arm_l=(14, 7), arm_r=(15, 5), leg_l=(6, 1), leg_r=(3, -1))
BACK = make_model(1160.0, hip_tilt=4, chest_tilt=-3, spine=1, head=2,
                  arm_l=(15, 5), arm_r=(14, 7), leg_l=(3, -1), leg_r=(6, 1))


# ---------- 공용 ----------

def paint_sheet(cv):
    cv.fill(cv.full(), Linear([PAPER_TOP, PAPER_LOW], (0, 0), (0, HEIGHT)))
    # 머리 단위 안내선. 정수리부터 발바닥까지 8칸이 8등신이다.
    for index in range(9):
        y = HEAD_TOP_Y + index * UNIT
        cv.stroke([(60, y), (WIDTH - 60, y)], GUIDE, width=1.4, opacity=0.8)
    cv.stroke([(805, 40), (805, HEIGHT - 40)], GUIDE, width=1.0, opacity=0.6)
    for model in (FRONT, BACK):
        x = model.body.joint("pelvis")[0]
        floor = HEAD_TOP_Y + 8.04 * UNIT
        cv.fill(cv.shape(g.ellipse(x + 20, floor + 4, 190, 24), soft=10), "#9aa4c0", opacity=0.45)


def cel_part(cv, shape, shadow=0.36, width=LINE_WIDTH):
    """살 덩어리 1개: 밑색 → 1단 그림자 → 밝은 면 → 바깥 윤곽선."""
    cv.fill(shape, SKIN)
    cv.fill(cv.form_shadow(shape, LIGHT, shadow), SKIN_SHADE)
    cv.fill(cv.form_light(shape, LIGHT, 0.1, soft=0.4), SKIN_LIGHT, opacity=0.6)
    cv.fill(cv.contour(shape, width), LINE_SKIN)
    return shape


def inner_line(cv, points, clip, width=1.6, taper=(0.1, 1, 0.1), color_value=LINE_SKIN, opacity=0.8):
    """몸 안쪽 선. 양 끝을 가늘게 풀어 윤곽선보다 약하게 보이게 한다."""
    cv.stroke(g.spline(points, closed=False), color_value, width=width, taper=taper, opacity=opacity, clip=clip)


def shade(cv, points, clip, color_value=SKIN_SHADE, opacity=1.0, soft=0.0):
    cv.fill(cv.shape(g.spline(points, closed=True), soft=soft), color_value, opacity=opacity, clip=clip)


def light_spot(cv, center, rx, ry, clip, angle=0.0, opacity=0.7):
    # 근육의 빛은 덩어리가 커서 가장자리를 크기에 비례해 풀어야 얼룩처럼 보이지 않는다.
    soft = max(min(rx, ry) * 0.5, 0.03) * UNIT
    cv.fill(cv.shape(g.ellipse(center[0], center[1], rx * UNIT, ry * UNIT, angle), soft=soft), SKIN_LIGHT,
            opacity=opacity, clip=clip)


def lit(side):
    """빛을 등진 쪽 팔다리의 빛은 약하게. 빛이 화면 왼쪽에서 오므로 l이 빛 쪽이다."""
    return 1.0 if (side == "l") == (LIGHT[0] < 0) else 0.4


def on_bone(body, start, end, t, out):
    """뼈 위의 점. t는 시작 관절에서 끝 관절까지 0-1, out은 몸 바깥쪽으로 벗어난 거리(머리 높이)."""
    a, b = np.array(body.joint(start)), np.array(body.joint(end))
    heading = (b - a) / np.linalg.norm(b - a)
    across = np.array([-heading[1], heading[0]])
    pelvis_x = body.joint("pelvis")[0]
    if np.dot(across, (a - (pelvis_x, a[1]))) < 0.0:
        across = -across
    return a + (b - a) * t + across * out * UNIT


def groin_volume(body):
    """사타구니의 단순한 둥근 덩어리. 세부 없이 빛과 그늘만 받는 면이다."""
    return g.ellipse(*body.on_pelvis(0.0, 0.47), UNIT * 0.1, UNIT * 0.14)


def relaxed_hand(body, side):
    # 늘어뜨린 손은 손바닥이 허벅지를 향한다. 손 좌표계가 아래를 보며 180도 돌아 있으므로 오른손만 뒤집는다.
    return figure.hand_side(body.hand_frame(side, flip=(side == "r")), curl=0.3)


def body_paths(body, back_view):
    """몸 전체를 한 덩어리로 칠할 윤곽. 발과 손바닥까지 넣어야 발목과 손목에 끊긴 선이 생기지 않는다."""
    foot_view = "bare_back" if back_view else "bare_front"
    paths = (body.neck() + body.torso()
             + [path for side in "lr" for bone in ("upper_arm", "forearm", "thigh", "shin")
                for path in body.limb(bone, side)]
             + [path for side in "lr" for path in body.foot(side, view=foot_view, turn=10)]
             + [path for side in "lr" for path in relaxed_hand(body, side).parts["palm"]])
    return paths if back_view else paths + [groin_volume(body)]


def paint_hands_and_feet(cv, body, body_shape, back_view):
    """손가락과 발의 세부. 손바닥과 발은 몸 덩어리에 이미 들어 있다."""
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
    """팔: 어깨세모근의 아래 경계, 위팔두갈래근 또는 세갈래근의 빛, 아래팔 바깥 근육의 선."""
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
    """다리: 넙다리 근육의 경계, 안쪽 무릎 위 물방울 근육, 무릎, 정강이, 종아리 두 갈래."""
    for side in "lr":
        sign = -1.0 if side == "l" else 1.0
        hip, knee, ankle = "hip_" + side, "knee_" + side, "ankle_" + side
        knee_point = np.array(body.joint(knee))
        if not back_view:
            # 넙다리빗근: 골반 바깥에서 안쪽 무릎으로 비스듬히 내려가는 긴 선.
            inner_line(cv, [on_bone(body, hip, knee, 0.05, 0.28), on_bone(body, hip, knee, 0.5, 0.0),
                            on_bone(body, hip, knee, 0.92, -0.22)], body_shape, width=1.4, opacity=0.5)
            inner_line(cv, [on_bone(body, hip, knee, 0.35, 0.38), on_bone(body, hip, knee, 0.85, 0.24)], body_shape,
                       width=1.3, opacity=0.4)
            # 안쪽 넓은근(무릎 위 안쪽의 물방울 덩어리).
            light_spot(cv, on_bone(body, hip, knee, 0.82, -0.12), 0.1, 0.13, body_shape, opacity=0.5 * lit(side))
            inner_line(cv, [on_bone(body, hip, knee, 0.72, -0.2), on_bone(body, hip, knee, 0.88, -0.24),
                            on_bone(body, hip, knee, 0.97, -0.12)], body_shape, width=1.3, opacity=0.55)
            light_spot(cv, knee_point + (0, -UNIT * 0.04), 0.07, 0.08, body_shape, opacity=0.5 * lit(side))
            inner_line(cv, [knee_point + (-UNIT * 0.09, UNIT * 0.13), knee_point + (0, UNIT * 0.17),
                            knee_point + (UNIT * 0.09, UNIT * 0.13)], body_shape, width=1.4, opacity=0.6)
            inner_line(cv, [on_bone(body, knee, ankle, 0.18, 0.0), on_bone(body, knee, ankle, 0.85, -0.03)],
                       body_shape, width=1.2, opacity=0.4)
            # 종아리 바깥 덩어리가 정강이 옆으로 볼록하다.
            inner_line(cv, [on_bone(body, knee, ankle, 0.12, 0.2), on_bone(body, knee, ankle, 0.38, 0.23),
                            on_bone(body, knee, ankle, 0.6, 0.12)], body_shape, width=1.3, opacity=0.45)
            continue
        # 뒷면: 넙다리 뒤 근육 두 갈래, 무릎 뒤 주름과 힘줄, 종아리 두 갈래와 아킬레스건.
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


# ---------- 앞면 ----------

def paint_front_upper(cv, model, body_shape):
    b = model.body
    shade(cv, model.head([(-0.8, 1.0), (0.9, 1.0), (0.8, 2.0), (0.1, 2.2), (-0.5, 1.9)]), body_shape)
    # 목: 귀 밑에서 목 밑 오목한 곳으로 모이는 목빗근 두 줄과 울대뼈.
    for sign in (-1.0, 1.0):
        inner_line(cv, [model.head.point(sign * 0.72, 1.2), b.on_thorax(sign * 0.12, -0.3), b.on_thorax(sign * 0.05, -0.02)],
                   body_shape, width=1.5, opacity=0.6)
    inner_line(cv, [b.on_thorax(-0.04, -0.4), b.on_thorax(0.0, -0.36), b.on_thorax(0.04, -0.4)], body_shape, width=1.6)
    light_spot(cv, b.on_thorax(0.0, -0.42), 0.035, 0.05, body_shape, opacity=0.6)
    for sign in (-1.0, 1.0):
        # 겨드랑이, 쇄골, 앞톱니근.
        shade(cv, [b.on_thorax(sign * 0.66, 0.16), b.on_thorax(sign * 0.86, 0.06), b.on_thorax(sign * 0.82, 0.62),
                   b.on_thorax(sign * 0.7, 0.5)], body_shape)
        inner_line(cv, [b.on_thorax(sign * 0.08, -0.03), b.on_thorax(sign * 0.4, -0.1), b.on_thorax(sign * 0.76, -0.04)],
                   body_shape, width=1.7)
        for row in range(3):
            y = 0.82 + row * 0.16
            inner_line(cv, [b.on_thorax(sign * 0.76, y), b.on_thorax(sign * 0.66, y + 0.08)], body_shape, width=1.2,
                       opacity=0.45)
        # 큰가슴근: 가슴뼈에서 겨드랑이까지 넓은 판. 아래 경계에 그늘 띠를 두고 위쪽에 빛을 둔다.
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
    """복근: 가운데 흰줄, 배곧은근의 양쪽 경계, 가로 마디 세 줄, 배꼽, 배빗근, 골반 V선."""
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
        # 배빗근과 골반 V선(엉덩뼈 능선에서 사타구니로 내려가는 선).
        inner_line(cv, [b.on_thorax(sign * 0.62, 1.12), b.on_pelvis(sign * 0.6, -0.8), b.on_pelvis(sign * 0.58, -0.42)],
                   body_shape, width=1.4, opacity=0.5)
        inner_line(cv, [b.on_pelvis(sign * 0.56, -0.44), b.on_pelvis(sign * 0.36, -0.12), b.on_pelvis(sign * 0.16, 0.24)],
                   body_shape, width=1.8, taper=(0.2, 1, 0.3), opacity=0.75)
        light_spot(cv, b.on_pelvis(sign * 0.5, -0.5), 0.05, 0.1, body_shape, angle=sign * -20, opacity=0.5)
    navel = b.on_pelvis(0.0, -0.72)
    cv.fill(cv.shape(g.ellipse(navel[0], navel[1], UNIT * 0.022, UNIT * 0.034)), SKIN_DEEP, clip=body_shape)


def paint_front_groin(cv, model, body_shape):
    """사타구니: 단순한 둥근 덩어리. 위쪽 빛과 아래쪽 그늘만 두고 안쪽 선은 긋지 않는다."""
    b = model.body
    volume = cv.shape(groin_volume(b)) & body_shape
    cv.fill(cv.form_shadow(volume, LIGHT, 0.4, soft=0.4), SKIN_SHADE, opacity=0.8)
    light_spot(cv, b.on_pelvis(-0.03, 0.4), 0.05, 0.06, volume, opacity=0.4)
    shade(cv, [b.on_pelvis(-0.2, 0.25), b.on_pelvis(0.2, 0.25), b.on_pelvis(0.14, 0.34), b.on_pelvis(-0.14, 0.34)],
          body_shape, opacity=0.35, soft=UNIT * 0.04)


def paint_face(cv, head):
    """성인 남성의 얼굴: 각진 턱과 평평한 턱 끝, 가늘고 긴 눈, 굵고 낮은 눈썹, 긴 콧대, 얇은 입술."""
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
    # 광대 아래에서 턱까지의 그늘. 남성은 양쪽 볼 모두 패여 보이게 한다.
    shade(cv, head([(0.97, 0.3), (0.92, 0.68), (0.66, 1.1), (0.34, 1.38), (0.5, 0.96), (0.68, 0.6), (0.74, 0.38)]), face)
    shade(cv, head([(-0.88, 0.66), (-0.66, 0.98), (-0.64, 0.82), (-0.74, 0.62)]), face, opacity=0.25, soft=UNIT * 0.02)
    shade(cv, head([(-0.24, 1.36), (0.24, 1.36), (0.13, 1.47), (-0.13, 1.47)]), face, opacity=0.6)
    # 콧대와 코끝 밑 그림자, 인중.
    inner_line(cv, head([(0.12, 0.34), (0.15, 0.7), (0.08, 0.9)]), face, width=1.9, taper=(0.1, 0.9, 1))
    shade(cv, head([(-0.1, 0.94), (0.12, 0.9), (0.14, 0.97), (-0.08, 0.99)]), face)
    inner_line(cv, head([(0.0, 1.0), (0.01, 1.08)]), face, width=1.2, opacity=0.4)
    # 입: 얇은 윗입술 선과 아랫입술 밑의 짧은 그늘.
    inner_line(cv, head([(-0.22, 1.14), (-0.06, 1.12), (0.08, 1.13), (0.22, 1.11)]), face, width=2.1,
               taper=(0.3, 1, 1, 0.3), color_value=LINE_DARK, opacity=1.0)
    shade(cv, head([(-0.1, 1.2), (0.1, 1.2), (0.06, 1.25), (-0.06, 1.25)]), face, opacity=0.7)
    for side in (head, head.mirrored()):
        draw_male_eye(cv, side.child(0.44, 0.38, unit=0.235), face)
        brow = side([(0.1, -0.02), (0.5, -0.12), (0.88, -0.06), (0.86, 0.02), (0.5, -0.04), (0.12, 0.06)])
        cv.fill(cv.shape(g.spline(brow, closed=True, corners=(0, 2, 3, 5))), LINE_HAIR)


def draw_male_eye(cv, eye, face):
    """남성의 눈: 높이가 폭의 3분의 1인 가는 꼴, 날개 없는 윗눈꺼풀, 홍채가 위아래로 조금 가려진다."""
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
    """짧은 머리. 앞면은 이마로 흘러내린 앞머리와 귀 앞 구레나룻, 뒷면은 목덜미에서 짧게 끝나는 뒷머리."""
    if back_view:
        points = [(-1.12, 0.3), (-1.16, -0.4), (-0.86, -1.08), (-0.2, -1.36), (0.5, -1.32), (1.0, -1.0), (1.18, -0.4),
                  (1.12, 0.3), (0.92, 0.72), (0.5, 0.96), (0.0, 1.04), (-0.5, 0.96), (-0.92, 0.72)]
        corners = ()
    else:
        # 오른쪽 가르마에서 왼쪽으로 쓸어 내린 앞머리. 굵은 가닥 세 개가 이마를 비스듬히 가로지른다.
        points = [(-1.04, 0.36), (-1.12, -0.2), (-1.18, -0.8), (-0.82, -1.3), (-0.2, -1.52), (0.5, -1.48),
                  (1.02, -1.18), (1.2, -0.64), (1.1, -0.1), (1.02, 0.36),   # 바깥 윤곽, 오른쪽 구레나룻 끝(9)
                  (0.92, 0.3), (0.9, -0.3),                                 # 구레나룻 안쪽
                  (0.62, -0.64),                                            # 가르마 쪽 이마선(12)
                  (0.3, -0.48), (0.1, -0.36), (-0.08, -0.18),               # 골(13) → 가닥 1 → 끝(15)
                  (-0.2, -0.46), (-0.38, -0.32), (-0.54, -0.14),            # 골(16) → 가닥 2 → 끝(18)
                  (-0.64, -0.42), (-0.8, -0.28), (-0.92, -0.06),            # 골(19) → 가닥 3 → 끝(21)
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


# ---------- 뒷면 ----------

def paint_back(cv):
    """뒷면: 등세모근, 어깨뼈, 넓은등근, 척추세움근, 허리 보조개, 엉덩이와 옆 오목한 곳, 넙다리 뒤, 종아리."""
    model, b = BACK, BACK.body
    body_shape = cel_part(cv, figure.shape_of(cv, body_paths(b, back_view=True)))
    shade(cv, model.head([(-0.8, 0.6), (0.8, 0.6), (0.7, 1.9), (0.0, 2.0), (-0.7, 1.9)]), body_shape, opacity=0.6)
    spine = [b.on_thorax(0.0, -0.3), b.on_thorax(-0.01, 0.5), b.on_thorax(0.0, 1.2), b.on_pelvis(0.01, -0.7),
             b.on_pelvis(0.0, -0.3)]
    inner_line(cv, spine, body_shape, width=2.0, taper=(0.2, 1, 1, 1, 0.3), opacity=0.6)
    for sign in (-1.0, 1.0):
        # 등세모근의 아래 경계: 어깨에서 등 가운데로 모이는 마름모의 아래 두 변.
        inner_line(cv, [b.on_thorax(sign * 0.6, 0.02), b.on_thorax(sign * 0.3, 0.5), b.on_thorax(sign * 0.04, 1.2)],
                   body_shape, width=1.4, opacity=0.45)
        # 어깨뼈와 가시아래근의 빛.
        inner_line(cv, [b.on_thorax(sign * 0.24, 0.2), b.on_thorax(sign * 0.28, 0.6), b.on_thorax(sign * 0.46, 0.9)],
                   body_shape, width=1.6, opacity=0.6)
        inner_line(cv, [b.on_thorax(sign * 0.3, 0.2), b.on_thorax(sign * 0.6, 0.12)], body_shape, width=1.3, opacity=0.45)
        light_spot(cv, b.on_thorax(sign * 0.48, 0.42), 0.16, 0.16, body_shape, opacity=0.55)
        # 넓은등근: 겨드랑이에서 허리로 쓸려 내려가는 큰 날개.
        inner_line(cv, [b.on_thorax(sign * 0.76, 0.36), b.on_thorax(sign * 0.6, 1.0), b.on_pelvis(sign * 0.36, -0.9)],
                   body_shape, width=1.5, opacity=0.5)
        # 척추세움근: 척추 골 양옆의 세로 덩어리.
        light_spot(cv, b.on_pelvis(sign * 0.15, -0.95), 0.07, 0.24, body_shape, opacity=0.3)
        cv.fill(cv.shape(g.ellipse(*b.on_pelvis(sign * 0.15, -0.27), UNIT * 0.022, UNIT * 0.028),
                         soft=UNIT * 0.015), SKIN_SHADE, opacity=0.7, clip=body_shape)
        # 엉덩이: 여성보다 작고 각진 덩이. 옆쪽의 오목한 곳이 근육을 드러낸다.
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
