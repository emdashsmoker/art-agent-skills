"""애니메풍 예제: 밤의 고층 아파트 창가에 선 여성(성인 누드 인체화).

공정: 창 밖 도시 → 뒷머리와 뒤쪽 팔 → 몸 덩어리(셀 그림자, 설계 그림자, 안쪽 선) → 얼굴 → 앞머리 → 커튼 → 손 → 촬영.
성인으로 읽히게 하는 표지: 8등신 리그, 작은 눈과 긴 턱의 얼굴, 뚜렷한 코와 입술, 성숙한 체형과 쇄골, 갈비, 골반뼈.
몸은 figure.Figure, 얼굴은 두개골 반지름을 1로 하는 좌표계에서 설계한다.
실행: python anime_city_window.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, figure, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1100, 1500
LIGHT = (-0.6, -0.5)        # 방 안 왼쪽 앞의 따뜻한 조명
RIM = (0.75, -0.45)         # 오른쪽 뒤 창에서 드는 차가운 도시 빛

# 팔레트: 남색 밤과 청록 도시 빛이 지배색. 살의 복숭아색만 따뜻하고 입술과 네온의 분홍이 강조색이다.
SKY = [(0.0, "#070a22"), (0.6, "#1a2050"), (0.9, "#3a2a6a"), (1.0, "#6a3a80")]
CITY = ["#141a40", "#0e1232", "#090c24"]
CITY_LIGHTS = ["#7fe0ff", "#ffd38a", "#ff7ab0", "#e6f2ff"]
ROOM = "#0b0d20"
SKIN, SKIN_SHADE, SKIN_DEEP, SKIN_LIGHT = "#f7d3bf", "#dc9b8f", "#b0656a", "#fff1e8"
NIPPLE, BLUSH = "#d98585", "#ff9aa0"
HAIR, HAIR_SHADE, HAIR_LIGHT = "#22263e", "#12142a", "#5a6aa0"
IRIS_TOP, IRIS_MID, IRIS_LOW = "#2a1a1a", "#7a3a2a", "#e0a060"
LIPS, LIPS_SHADE = "#d4707a", "#9a4050"
LINE_SKIN, LINE_HAIR, LINE_DARK = "#7a3e40", "#0a0b1a", "#1a0e14"
CURTAIN, CURTAIN_SHADE = "#e9eef8", "#a8b4d0"
GOLD = "#e8c27a"
LINE_WIDTH = 2.6

ADULT = figure.Build(shoulder=0.70, ribcage=0.60, waist=0.48, hip=0.82, arm=0.84, leg=1.06, neck=0.33)
BODY = figure.Figure(
    g.Frame(origin=(560, 990), unit=225), build=ADULT,
    hip_tilt=-11, chest_tilt=8, spine=-4, neck=-3, head=-9,
    arm_l=(150, 285), arm_r=(13, -6), leg_l=(5, -4), leg_r=(-4, 3), stretch={"forearm_r": 0.9, "neck": 0.72})
UNIT = BODY.frame.unit
# 얼굴 좌표계: 두개골 반지름이 1. 머리 높이는 이 단위로 2.3이며 리그의 머리보다 조금 크게 그린다.
# 애니메풍은 머리를 실제보다 약간 키워야 8등신 몸에서도 머리가 작아 보이지 않는다.
HEAD = g.Frame(BODY.head_frame().point(0.0, -0.06), unit=UNIT / 2.3, rotate=BODY.frame.rotate - 9)


# ---------- 배경 ----------

def paint_night(cv, rng):
    cv.fill(cv.full(), ROOM)
    window = cv.shape(g.rect(90, -20, 1030, 1560))
    cv.fill(window, Linear(SKY, (0, 0), (0, 1100)))
    horizon = 1080
    for layer, (base_color, height_range, width_range) in enumerate(
            ((CITY[0], (180, 420), (50, 110)), (CITY[1], (120, 300), (60, 140)), (CITY[2], (60, 200), (80, 170)))):
        x = 70.0
        while x < WIDTH + 20:
            width = rng.uniform(*width_range)
            top = horizon - rng.uniform(*height_range)
            cv.fill(cv.shape(g.rect(x, top, width, HEIGHT - top)), base_color, clip=window)
            for wy in np.arange(top + 10, HEIGHT, 13 + layer * 3):
                for wx in np.arange(x + 6, x + width - 6, 10 + layer * 3):
                    if rng.random() < 0.18:
                        cv.fill(cv.shape(g.rect(wx, wy, 4 + layer, 5 + layer)),
                                CITY_LIGHTS[int(rng.integers(len(CITY_LIGHTS)))], opacity=0.45 + 0.2 * layer,
                                clip=window)
            x += width + rng.uniform(4, 16)
    for _ in range(50):
        bokeh = cv.shape(g.ellipse(rng.uniform(90, WIDTH), rng.uniform(500, 1300), rng.uniform(10, 30)), soft=6)
        cv.fill(bokeh, CITY_LIGHTS[int(rng.integers(len(CITY_LIGHTS)))], opacity=0.25, blend=Blend.SCREEN,
                clip=window)
    # 창틀과 유리에 비친 방 안 조명.
    cv.fill(cv.shape(g.rect(60, -20, 34, HEIGHT + 40)), "#05060f")
    cv.fill(cv.shape(g.rect(820, -20, 20, HEIGHT + 40)), "#05060f")
    cv.fill(cv.shape(g.ellipse(240, 420, 160, 240), soft=90), "#ffb070", opacity=0.18, blend=Blend.SCREEN)


def paint_back_curtain(cv):
    """창 오른쪽에 바닥까지 늘어진 얇은 커튼. 도시 불빛이 비쳐 보이도록 반투명하게 칠한다."""
    drape = cv.shape(g.spline([(880, -20), (1120, -20), (1120, HEIGHT + 20), (930, HEIGHT + 20), (950, 1000),
                               (900, 500)], closed=True, corners=(0, 1, 2, 3)))
    cv.fill(drape, CURTAIN, opacity=0.3)
    for x in (910, 970, 1030, 1090):
        cv.stroke(g.spline([(x, -20), (x + 14, 600), (x + 30, HEIGHT + 20)], closed=False), CURTAIN_SHADE,
                  width=18, taper=(1, 0.8, 1), opacity=0.35, soft=6, clip=drape)


# ---------- 몸 ----------

def cel_part(cv, shape, shadow=0.36, line=LINE_SKIN, width=LINE_WIDTH):
    """살 덩어리 1개: 밑색 → 1단 그림자 → 밝은 면 → 바깥 윤곽선."""
    cv.fill(shape, SKIN)
    cv.fill(cv.form_shadow(shape, LIGHT, shadow), SKIN_SHADE)
    cv.fill(cv.form_light(shape, LIGHT, 0.1, soft=0.4), SKIN_LIGHT, opacity=0.6)
    cv.fill(cv.contour(shape, width), line)
    return shape


def inner_line(cv, points, clip, width=1.8, taper=(0.1, 1, 0.1), color_value=LINE_SKIN, opacity=0.85):
    """몸 안쪽 선. 양 끝을 가늘게 풀어 윤곽선보다 약하게 보이게 한다."""
    cv.stroke(g.spline(points, closed=False), color_value, width=width, taper=taper, opacity=opacity, clip=clip)


def designed_shadow(cv, points, clip, color_value=SKIN_SHADE, corners=()):
    cv.fill(cv.shape(g.spline(points, closed=True, corners=corners)), color_value, clip=clip)


def paint_back_hair(cv):
    back = [(-1.08, -0.4), (-0.78, -1.1), (0.1, -1.3), (0.94, -1.02), (1.24, -0.3), (1.26, 0.6), (1.16, 1.36),
            (0.8, 1.56), (0.3, 1.34), (-0.5, 1.2), (-1.02, 0.96), (-1.2, 0.2)]
    hair = cv.shape(g.spline(HEAD(back), closed=True))
    cv.fill(hair, HAIR_SHADE)
    cv.fill(cv.contour(hair, LINE_WIDTH), LINE_HAIR)


def paint_raised_hand(cv):
    """머리 뒤로 넘긴 손. 아래팔은 머리 뒤에 숨고 손가락 끝만 반대쪽 머리 위로 보인다."""
    hand = figure.hand_side(BODY.hand_frame("l", turn=10), curl=0.45)
    shape = figure.shape_of(cv, BODY.limb("forearm", "l") + hand.paths())
    cel_part(cv, shape, shadow=0.5)


def paint_body(cv):
    paths = (BODY.neck() + BODY.torso() + BODY.limb("upper_arm", "l") + BODY.limb("upper_arm", "r")
             + BODY.limb("forearm", "r") + BODY.limb("thigh", "l") + BODY.limb("thigh", "r")
             + BODY.limb("shin", "l") + BODY.limb("shin", "r"))
    body = figure.shape_of(cv, paths)
    cel_part(cv, body)

    # 설계 그림자: 턱 밑, 겨드랑이, 가슴 밑, 허리의 접힌 쪽, 사타구니 주름.
    # 턱 밑 그림자는 얼굴 좌표로 잡아야 머리 크기나 목 길이를 바꿔도 턱에 붙어 따라온다.
    designed_shadow(cv, HEAD([(-0.7, 1.0), (0.8, 1.0), (0.7, 1.9), (0.1, 2.1), (-0.4, 1.8)]), body)
    designed_shadow(cv, [BODY.on_thorax(-0.66, 0.0), BODY.on_thorax(-0.5, 0.12), BODY.on_thorax(-0.56, 0.5),
                         BODY.on_thorax(-0.72, 0.36)], body)
    designed_shadow(cv, [BODY.on_thorax(0.5, 0.1), BODY.on_thorax(0.72, 0.0), BODY.on_thorax(0.68, 0.9),
                         BODY.on_thorax(0.56, 0.7)], body)
    for sign in (-1.0, 1.0):
        cx, cy = BODY.on_thorax(sign * 0.33 - 0.02, 0.7)
        designed_shadow(cv, [(cx - UNIT * 0.3, cy + UNIT * 0.1), (cx + UNIT * 0.3, cy + UNIT * 0.08),
                             (cx + UNIT * 0.26, cy + UNIT * 0.34), (cx, cy + UNIT * 0.42),
                             (cx - UNIT * 0.26, cy + UNIT * 0.32)], body)
    designed_shadow(cv, [BODY.on_pelvis(0.42, -1.25), BODY.on_pelvis(0.62, -1.05), BODY.on_pelvis(0.66, -0.55),
                         BODY.on_pelvis(0.5, -0.7)], body)
    paint_breasts(cv, body)

    # 안쪽 선: 쇄골, 목 밑, 갈비 아치, 배 가운데 골, 배꼽, 골반뼈, 사타구니 주름, 무릎.
    for sign in (-1.0, 1.0):
        inner_line(cv, [BODY.on_thorax(sign * 0.1, -0.02), BODY.on_thorax(sign * 0.36, -0.09),
                        BODY.on_thorax(sign * 0.58, -0.04)], body)
        inner_line(cv, [BODY.on_thorax(sign * 0.12, 1.08), BODY.on_thorax(sign * 0.3, 1.22),
                        BODY.on_thorax(sign * 0.44, 1.42)], body, width=1.4, opacity=0.5)
        inner_line(cv, [BODY.on_pelvis(sign * 0.56, -0.5), BODY.on_pelvis(sign * 0.5, -0.32),
                        BODY.on_pelvis(sign * 0.34, -0.06)], body, width=1.5, opacity=0.6)
        knee = BODY.joint("knee_l" if sign < 0 else "knee_r")
        inner_line(cv, [(knee[0] - UNIT * 0.12, knee[1] + UNIT * 0.04), (knee[0], knee[1] + UNIT * 0.1),
                        (knee[0] + UNIT * 0.1, knee[1] + UNIT * 0.04)], body, width=1.4, opacity=0.6)
    inner_line(cv, [BODY.on_thorax(-0.03, -0.02), BODY.on_thorax(0.0, 0.06)], body, width=2.0)
    inner_line(cv, [BODY.on_pelvis(0.0, -1.2), BODY.on_pelvis(0.01, -0.9)], body, width=1.3, opacity=0.45)
    navel = BODY.on_pelvis(0.0, -0.7)
    cv.fill(cv.shape(g.ellipse(navel[0], navel[1], UNIT * 0.022, UNIT * 0.04)), SKIN_DEEP, clip=body)
    inner_line(cv, [(navel[0] - UNIT * 0.03, navel[1] - UNIT * 0.04), (navel[0], navel[1] - UNIT * 0.055),
                    (navel[0] + UNIT * 0.03, navel[1] - UNIT * 0.04)], body, width=1.4)
    # 목걸이: 쇄골 사이로 떨어지는 가는 사슬과 작은 펜던트.
    chain = g.spline([BODY.on_thorax(-0.2, -0.32), BODY.on_thorax(-0.12, 0.12), BODY.on_thorax(0.0, 0.26),
                      BODY.on_thorax(0.12, 0.12), BODY.on_thorax(0.21, -0.32)], closed=False)
    cv.stroke(chain, GOLD, width=1.6, clip=body)
    pendant = BODY.on_thorax(0.0, 0.3)
    cv.fill(cv.shape(g.ellipse(pendant[0], pendant[1], UNIT * 0.022, UNIT * 0.03)), GOLD)
    cv.stroke(g.ellipse(pendant[0], pendant[1], UNIT * 0.022, UNIT * 0.03), LINE_DARK, width=1.0, closed=True)
    return body


def paint_breasts(cv, body):
    """가슴: 둥근 덩어리마다 셀 그림자와 밝은 점을 따로 주고 아래 곡선에만 선을 긋는다."""
    for sign in (-1.0, 1.0):
        cx, cy = BODY.on_thorax(sign * 0.33 - 0.02, 0.68)
        outline = [(-0.27, -0.12), (0.0, -0.34), (0.27, -0.1), (0.3, 0.12), (0.03, 0.31), (-0.28, 0.12)]
        breast = cv.shape(g.spline([(cx + x * UNIT, cy + y * UNIT) for x, y in outline], closed=True))
        breast = breast & body
        cv.fill(breast, SKIN)
        cv.fill(cv.form_shadow(breast, LIGHT, 0.38), SKIN_SHADE)
        cv.fill(cv.shape(g.ellipse(cx - UNIT * 0.1, cy - UNIT * 0.12, UNIT * 0.08, UNIT * 0.05, -20), soft=4),
                SKIN_LIGHT, opacity=0.9, clip=breast)
        underline = [(cx - UNIT * 0.27, cy + UNIT * 0.1), (cx - UNIT * 0.1, cy + UNIT * 0.29),
                     (cx + UNIT * 0.12, cy + UNIT * 0.29), (cx + UNIT * 0.28, cy + UNIT * 0.1)]
        inner_line(cv, underline, body, width=2.2, taper=(0.1, 1, 1, 0.2))
        nipple = (cx + UNIT * 0.04, cy + UNIT * 0.06)
        cv.fill(cv.shape(g.ellipse(nipple[0], nipple[1], UNIT * 0.04, UNIT * 0.036)), NIPPLE, clip=breast)
        cv.fill(cv.shape(g.ellipse(nipple[0], nipple[1] + UNIT * 0.006, UNIT * 0.016)), SKIN_DEEP, opacity=0.6,
                clip=breast)


# ---------- 얼굴 ----------

def paint_face(cv):
    # 성인의 얼굴: 광대 아래로 볼이 홀쭉해지고 턱 끝이 길게 내려온다.
    right = [(0.0, -1.0), (0.6, -0.82), (0.93, -0.3), (0.95, 0.18), (0.86, 0.6), (0.6, 1.0), (0.26, 1.34)]
    chin = [(0.0, 1.45)]
    left = [(-x, y) for x, y in reversed(right[1:])]
    face = cv.shape(g.spline(HEAD(right + chin + left), closed=True))
    cv.fill(face, SKIN)
    cv.fill(cv.contour(face, LINE_WIDTH), LINE_SKIN)
    designed_shadow(cv, HEAD([(-1.05, -0.95), (1.05, -0.95), (1.0, 0.0), (0.6, -0.1), (0.2, -0.3), (-0.3, -0.18),
                              (-0.8, 0.02), (-1.0, -0.05)]), face)
    # 빛을 등진 쪽 볼과 턱선의 그림자가 광대뼈를 드러낸다.
    designed_shadow(cv, HEAD([(0.96, 0.3), (0.88, 0.62), (0.6, 1.02), (0.3, 1.3), (0.46, 0.92), (0.66, 0.56),
                              (0.7, 0.36)]), face)
    for cheek, strength in ((-0.55, 0.28), (0.55, 0.2)):
        blush = cv.shape(g.ellipse(*HEAD.point(cheek, 0.74), HEAD.length(0.2), HEAD.length(0.08)),
                         soft=HEAD.length(0.06))
        cv.fill(blush, BLUSH, opacity=strength, clip=face)

    # 코: 그늘 쪽 콧대 선과 코끝 밑 그림자.
    inner_line(cv, HEAD([(0.1, 0.42), (0.12, 0.72), (0.06, 0.86)]), face, width=1.8, taper=(0.1, 0.8, 1))
    designed_shadow(cv, HEAD([(-0.06, 0.9), (0.1, 0.86), (0.12, 0.93), (-0.04, 0.95)]), face, SKIN_SHADE)
    # 입술: 윗입술 선, 색이 있는 아랫입술, 아랫입술의 빛, 입꼬리.
    upper = HEAD([(-0.22, 1.1), (-0.08, 1.07), (0.0, 1.09), (0.08, 1.07), (0.22, 1.1)])
    lower = cv.shape(g.spline(HEAD([(-0.18, 1.12), (0.18, 1.12), (0.1, 1.2), (-0.1, 1.2)]), closed=True,
                              corners=(0, 1)))
    cv.fill(lower, LIPS, clip=face)
    cv.fill(cv.shape(g.ellipse(*HEAD.point(-0.04, 1.155), HEAD.length(0.05), HEAD.length(0.016))), "#ffd0d4",
            opacity=0.8, clip=face)
    cv.fill(cv.shape(g.spline(HEAD([(-0.2, 1.1), (0.0, 1.06), (0.2, 1.1), (0.0, 1.11)]), closed=True,
                              corners=(0, 2))), LIPS_SHADE, clip=face)
    inner_line(cv, upper, face, width=2.2, taper=(0.4, 1, 1, 1, 0.4), color_value=LINE_DARK)
    designed_shadow(cv, HEAD([(-0.1, 1.24), (0.12, 1.24), (0.06, 1.29), (-0.06, 1.29)]), face)
    for side in (HEAD, HEAD.mirrored()):
        draw_adult_eye(cv, side.child(0.45, 0.4, unit=0.24), face)
        brow = g.spline(side([(0.18, -0.02), (0.46, -0.12), (0.8, -0.04)]), closed=False)
        cv.stroke(brow, LINE_HAIR, width=3.0, taper=(0.7, 1, 0.1))
    # 귀걸이: 앞머리를 귀 뒤로 넘긴 쪽에만 보인다.
    ear = HEAD.point(-0.98, 0.62)
    cv.stroke([ear, (ear[0], ear[1] + HEAD.length(0.22))], GOLD, width=1.6)
    cv.fill(cv.shape(g.ellipse(ear[0], ear[1] + HEAD.length(0.26), HEAD.length(0.045))), GOLD)
    return face


def draw_adult_eye(cv, eye, face):
    """성인의 눈: 가로로 긴 아몬드 꼴, 반쯤 내린 눈꺼풀, 날개처럼 뻗은 눈꼬리 속눈썹."""
    white_outline = g.spline(eye([(-1.0, 0.05), (-0.55, -0.32), (0.1, -0.42), (0.7, -0.3), (1.08, -0.08),
                                  (0.7, 0.26), (0.0, 0.36), (-0.6, 0.26)]), closed=True, corners=(0, 4))
    white = cv.shape(white_outline) & face
    cv.fill(white, "#fbf4f2")
    cv.fill(cv.shape(g.ellipse(*eye.point(0.0, -0.48), eye.length(1.3), eye.length(0.3))), "#d8b8b8", clip=white)
    center = (-0.02, 0.02)
    iris_path = g.ellipse(*eye.point(*center), eye.length(0.44), eye.length(0.5), eye.rotate)
    iris = cv.shape(iris_path) & white
    cv.fill(iris, Linear([(0.0, IRIS_TOP), (0.5, IRIS_MID), (1.0, IRIS_LOW)], eye.point(0.0, -0.45),
                         eye.point(0.0, 0.5)))
    cv.fill(cv.shape(g.ellipse(*eye.point(*center), eye.length(0.18), eye.length(0.22), eye.rotate)), "#100808",
            clip=iris)
    cv.stroke(iris_path, IRIS_TOP, width=2.0, closed=True, clip=white)
    toward_light = 1.0 if eye.flip else -1.0
    cv.fill(cv.shape(g.ellipse(*eye.point(center[0] + 0.18 * toward_light, -0.14), eye.length(0.11))), "#ffffff",
            clip=white)
    # 윗눈꺼풀이 홍채 위쪽을 덮는다(반쯤 내린 눈).
    lid = [(-1.12, 0.06), (-0.72, -0.36), (0.0, -0.5), (0.72, -0.4), (1.2, -0.12), (1.5, -0.24), (1.12, 0.02),
           (0.7, -0.2), (0.0, -0.24), (-0.66, -0.12)]
    cv.fill(cv.shape(g.spline(eye(lid), closed=True, corners=(0, 5))), LINE_DARK)
    cv.stroke(g.spline(eye([(-0.7, 0.24), (0.0, 0.38), (0.72, 0.26), (1.04, 0.0)]), closed=False), LINE_SKIN,
              width=1.6, taper=(0.1, 1, 1, 0.3))
    cv.stroke(g.spline(eye([(-0.7, -0.7), (0.1, -0.86), (0.9, -0.66)]), closed=False), LINE_SKIN, width=1.6,
              taper=(0.2, 1, 0.2), opacity=0.8)


def paint_front_hair(cv):
    """옆 가르마의 단발. 화면 오른쪽은 귀를 덮어 길게, 왼쪽은 귀 뒤로 넘겨 짧게 둔다."""
    points = [(-1.16, -0.2), (-1.02, -0.86), (-0.44, -1.26), (0.26, -1.32), (0.9, -1.08), (1.24, -0.56),
              (1.28, 0.2), (1.22, 0.96), (1.12, 1.58),      # 오른쪽 옆머리 끝(턱선 아래)
              (0.88, 1.0), (0.8, 0.4),                      # 골
              (0.66, 0.1), (0.42, -0.06),                   # 쓸어 넘긴 앞머리 끝
              (0.3, -0.36), (-0.1, -0.56),                  # 가르마 쪽으로 올라감
              (-0.5, -0.58), (-0.86, -0.42),                # 이마를 드러낸 쪽
              (-1.0, -0.1), (-1.06, 0.36)]
    hair = cv.shape(g.spline(HEAD(points), closed=True, corners=(8, 10, 12, 16)))
    cv.fill(hair, HAIR)
    cv.fill(cv.form_shadow(hair, LIGHT, 0.4), HAIR_SHADE)
    band = [(-0.86, -0.6), (-0.5, -0.82), (-0.1, -0.92), (0.3, -0.86), (0.62, -0.7),
            (0.56, -0.62), (0.26, -0.74), (-0.1, -0.78), (-0.48, -0.7), (-0.82, -0.5)]
    cv.fill(cv.shape(g.spline(HEAD(band), closed=True, corners=(0, 4, 5, 9))), HAIR_LIGHT, clip=hair)
    for strand in ([(0.2, -1.1), (0.5, -0.6), (0.48, -0.1)], [(0.6, -0.96), (0.86, -0.3), (0.86, 0.6)],
                   [(0.9, -0.6), (1.06, 0.3), (1.0, 1.2)], [(-0.3, -1.0), (-0.66, -0.7), (-0.9, -0.3)]):
        cv.stroke(g.spline(HEAD(strand), closed=False), LINE_HAIR, width=1.5, taper=(0.1, 1, 0.1), clip=hair)
    cv.fill(cv.contour(hair, LINE_WIDTH), LINE_HAIR)
    cv.fill(cv.edge_light(hair, RIM, width=6), "#8fe8ff", opacity=0.8, clip=hair)


# ---------- 천과 손 ----------

def paint_cloth(cv):
    """창 커튼을 끌어와 골반에 두른다. 위쪽 끝은 골반뼈 아래를 지나고 아래로 길게 늘어진다."""
    hand = BODY.joint("wrist_r")
    outline = [(hand[0] - 10, hand[1] - 20), BODY.on_pelvis(0.4, -0.02), BODY.on_pelvis(-0.3, 0.06),
               BODY.on_pelvis(-0.98, -0.06), BODY.on_pelvis(-1.08, 0.7), (BODY.on_pelvis(-1.0, 0.0)[0] - 20, HEIGHT + 30),
               (BODY.on_pelvis(0.3, 0.0)[0], HEIGHT + 30), BODY.on_pelvis(0.36, 1.1), (hand[0] + 30, hand[1] + 90)]
    cloth = cv.shape(g.spline(outline, closed=True, corners=(0, 3, 5, 6)))
    cv.fill(cloth, CURTAIN)
    cv.fill(cv.form_shadow(cloth, LIGHT, 0.4), CURTAIN_SHADE)
    for end in (BODY.on_pelvis(-0.9, 0.3), BODY.on_pelvis(-0.7, 1.2), (BODY.on_pelvis(-0.5, 0)[0], HEIGHT),
                (BODY.on_pelvis(0.05, 0)[0], HEIGHT)):
        middle = ((hand[0] + end[0]) / 2.0, (hand[1] + end[1]) / 2.0 + UNIT * 0.1)
        cv.stroke(g.spline([(hand[0] - 6, hand[1] + 30), middle, end], closed=False), CURTAIN_SHADE, width=7,
                  taper=(0.2, 1, 0.4), clip=cloth)
    # 수건의 윗단은 한 번 접혀 두툼한 띠가 된다.
    fold = cv.shape(g.spline([outline[0], outline[1], outline[2], outline[3], BODY.on_pelvis(-1.0, 0.18),
                              BODY.on_pelvis(-0.3, 0.26), BODY.on_pelvis(0.4, 0.16), (hand[0] - 10, hand[1] + 10)],
                             closed=True, corners=(0, 3, 4, 7)))
    cv.fill(fold, "#f7f9fd", clip=cloth)
    cv.stroke(g.spline([BODY.on_pelvis(-1.0, 0.18), BODY.on_pelvis(-0.3, 0.26), BODY.on_pelvis(0.4, 0.16),
                        (hand[0] - 10, hand[1] + 10)], closed=False), CURTAIN_SHADE, width=4, clip=cloth)
    cv.fill(cv.contour(cloth, LINE_WIDTH * 0.8), "#4a5070")
    cv.fill(cv.edge_light(cloth, RIM, width=7), "#bff0ff", opacity=0.7, clip=cloth)


def paint_hand(cv):
    hand = figure.hand_side(BODY.hand_frame("r", turn=-8, flip=True), curl=0.82)
    for name in ("palm", "pinky", "ring", "middle", "index", "thumb"):
        part = figure.shape_of(cv, hand.parts[name])
        cv.fill(part, SKIN)
        cv.fill(cv.form_shadow(part, LIGHT, 0.35), SKIN_SHADE)
        cv.fill(cv.contour(part, 1.6), LINE_SKIN)


def paint_character(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    paint_back_hair(cv)
    paint_raised_hand(cv)
    paint_body(cv)
    paint_face(cv)
    paint_front_hair(cv)
    paint_cloth(cv)
    paint_hand(cv)
    return cv


def main(out_dir="out", scale=1.0, seed=53):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    background = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_night(background, rng)
    paint_back_curtain(background)
    character = paint_character(scale, seed)
    io.save(character.guide_image(), out_dir / "window_1_character_guide.png")
    anime.rim_light(character, RIM, width=5.0, tint="#9fefff", opacity=0.85)
    background.paste(character)
    image = anime.finish(background, diffusion=0.18, bloom=0.3, shadows="#1a1a4a", highlights="#ffe2d0")
    image = post.light_gradient(image, "#ffb070", (0.0, 0.2), (0.6, 0.6), strength=0.12)
    return io.save(post.vignette(image, strength=0.25), out_dir / "anime_city_window.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
