"""애니메풍 예제: 여름 하늘 아래 고글에 손을 올린 비행사.

공정: 배경(하늘, 구름, 바다) → 인물 셀(자세 → 옷 → 얼굴 → 머리카락 → 손) → 합성 → 촬영.
몸은 figure.Figure로 자세를 잡고 얼굴은 두개골 반지름을 1로 하는 단위 좌표로 설계한다.
실행: python anime_sky_pilot.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, figure, io, motifs, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1600, 900
LIGHT = (-0.6, -0.8)  # 왼쪽 위 광원

# 팔레트: 하늘의 파랑이 지배색. 머리카락과 가죽 재킷의 적갈색이 보색으로 맞서고 목도리의 빨강이 강조색이다.
SKY = [(0.0, "#1b5fc4"), (0.5, "#4a98e6"), (0.82, "#a4d4f5"), (1.0, "#e3f3fc")]
CLOUD = ("#ffffff", "#d3e2f6", "#86a6d8")
SEA_FAR, SEA_NEAR = "#5aa4dc", "#1f5fae"
SKIN, SKIN_SHADE = "#ffdcc6", "#e9a48c"
HAIR, HAIR_SHADE, HAIR_LIGHT = "#b0502e", "#6e2a26", "#f0a070"
IRIS_TOP, IRIS_MID, IRIS_LOW = "#16402f", "#2f9a6a", "#a8f0c0"
JACKET, JACKET_SHADE, JACKET_LIGHT = "#8a5a3a", "#523026", "#c08a5a"
FUR, FUR_SHADE = "#f4ead8", "#c9b8a0"
SCARF, SCARF_SHADE = "#e5503f", "#a82f3c"
GLOVE, GLOVE_SHADE = "#d9b27a", "#9a7446"
BRASS, LENS_TOP, LENS_LOW = "#d8a84a", "#2f6fc0", "#bfe6fa"
LINE_SKIN, LINE_HAIR, LINE_DARK = "#8a4a3c", "#3d1a1a", "#2a1a1c"
BLUSH = "#ff9c94"
LINE_WIDTH = 3.0

# 허리 위 구도. 화면 오른쪽 팔을 들어 이마의 고글에 손을 올린다.
# 든 팔의 위팔은 화면 쪽으로 나와 있어 길이를 줄여 단축을 흉내 낸다.
BODY = figure.Figure(
    g.Frame(origin=(1060, 1160), unit=262), build=figure.FEMALE,
    chest_tilt=-5, spine=2, neck=0, head=-7,
    arm_l=(14, 4), arm_r=(52, 203), stretch={"upper_arm_r": 0.62, "forearm_r": 0.92})
# 얼굴 좌표계: 두개골 중심이 원점, 두개골 반지름이 1. 리그의 머리 높이는 이 단위로 2.37이다.
HEAD = g.Frame(BODY.head_frame().point(0.0, -0.08), unit=262 / 2.37, rotate=-7)


# ---------- 배경 ----------

def paint_background(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    cv.fill(cv.full(), Linear(SKY, (0, 0), (0, 760)))
    motifs.cumulus(cv, 400, 770, 680, 560, light=LIGHT, puffs=110, palette=CLOUD)
    motifs.cumulus(cv, 1470, 765, 220, 80, light=LIGHT, puffs=20, palette=CLOUD)
    # 먼 구름은 대기에 묻혀 하늘색에 가까워진다.
    cv.fill(cv.shape(g.rect(0, 620, WIDTH, 170), soft=40), "#d6ecfa", opacity=0.3)

    sea = cv.shape(g.rect(0, 770, WIDTH, 130))
    cv.fill(sea, Linear([SEA_FAR, SEA_NEAR], (0, 770), (0, 900)))
    cv.fill(cv.shape(g.rect(0, 768, WIDTH, 5), soft=1.5), "#eaf7ff", opacity=0.8)
    rng = np.random.default_rng(seed)
    for _ in range(140):
        y = rng.uniform(778, 898)
        depth = (y - 770) / 130.0
        glint = cv.shape(g.ellipse(rng.uniform(0, WIDTH), y, rng.uniform(10, 40) * (0.4 + depth),
                                   0.8 + 1.6 * depth))
        cv.fill(glint, "#d9f1ff", opacity=rng.uniform(0.25, 0.7))
    paint_biplane(cv, g.Frame(origin=(760, 210), unit=34, rotate=-8))
    return cv


def paint_biplane(cv, plane):
    """멀리 나는 복엽기 실루엣. 인물의 직업을 배경이 설명한다."""
    tone = "#3a5f9a"
    cv.fill(cv.shape(g.spline(plane([(-2.2, 0.0), (-0.6, -0.3), (1.4, -0.2), (1.9, 0.05), (1.3, 0.3),
                                     (-0.8, 0.25)]), closed=True)), tone)
    for wing_y in (-0.75, 0.3):
        cv.fill(cv.shape(g.polygon(plane([(-0.2, wing_y), (1.1, wing_y), (1.0, wing_y + 0.16),
                                          (-0.3, wing_y + 0.16)]))), tone)
    for strut_x in (0.0, 0.8):
        cv.stroke(plane([(strut_x, -0.7), (strut_x, 0.35)]), tone, width=2)
    cv.fill(cv.shape(g.polygon(plane([(-2.2, 0.0), (-2.5, -0.6), (-1.9, -0.55), (-1.6, -0.05)]))), tone)
    cv.stroke(plane([(1.95, -0.5), (1.95, 0.55)]), "#dfeefc", width=2.5, opacity=0.8)


# ---------- 인물 부품 ----------

def cel(cv, outline, base, shade=None, amount=0.0, line=None):
    return anime.cel(cv, outline, base, shade, amount, line, LINE_WIDTH, LIGHT)


def part(cv, points, base, shade=None, amount=0.0, line=None, corners=()):
    """통과점으로 셀 부품 1개를 그린다. 채운 형태를 돌려주어 추가 그림자의 clip으로 쓴다."""
    return cel(cv, g.spline(points, closed=True, corners=corners), base, shade, amount, line)


def lock(cv, frame, centerline, widths, base, shade, line, amount=0.4):
    """뿌리에서 끝으로 가늘어지는 띠 1개. 머리카락 가닥과 목도리 자락에 함께 쓴다."""
    spine = g.spline(frame(centerline), closed=False)
    outline = g.ribbon(spine, [frame.length(width) for width in widths])[0]
    shape = cv.shape(outline)
    cv.fill(shape, base)
    cv.fill(cv.form_shadow(shape, LIGHT, amount), shade)
    cv.stroke(outline, line, width=LINE_WIDTH, closed=True, light=LIGHT, contrast=0.45, jitter=0.15)
    cv.stroke(spine, line, width=1.5, taper=(0.0, 1.0, 0.0), clip=shape)
    return shape


def union_part(cv, paths, base, shade, amount, line):
    """겹치는 윤곽 여러 개를 한 부품으로 합쳐 칠하고 바깥 윤곽에만 선을 긋는다."""
    shape = figure.shape_of(cv, paths)
    cv.fill(shape, base)
    cv.fill(cv.form_shadow(shape, LIGHT, amount), shade)
    cv.fill(cv.edge_light(shape, (-LIGHT[0], -LIGHT[1]), width=LINE_WIDTH * 0.9), line)
    cv.fill(cv.edge_light(shape, LIGHT, width=LINE_WIDTH * 0.5), line)
    return shape


def draw_back_hair(cv):
    back = [(-0.6, -1.05), (0.2, -1.18), (0.88, -0.9), (1.2, -0.3), (1.22, 0.5), (1.0, 1.25), (0.3, 1.45),
            (-0.6, 1.4), (-1.1, 0.8), (-1.2, 0.0), (-1.05, -0.65)]
    part(cv, HEAD(back), HAIR_SHADE, line=LINE_HAIR)
    # 짧은 머리는 가닥이 짧고 끝이 위로 들린다. 뿌리를 겹쳐 한 덩어리로 흐르게 한다.
    lock(cv, HEAD, [(-0.7, 1.0), (-1.3, 1.25), (-1.85, 1.2), (-2.3, 0.95)], (0.6, 0.45, 0.26, 0.0), HAIR,
         HAIR_SHADE, LINE_HAIR)
    lock(cv, HEAD, [(-0.7, 0.55), (-1.4, 0.65), (-2.05, 0.5), (-2.6, 0.2)], (0.66, 0.5, 0.28, 0.0), HAIR,
         HAIR_SHADE, LINE_HAIR)
    lock(cv, HEAD, [(-0.7, 0.1), (-1.4, 0.08), (-2.0, -0.12), (-2.45, -0.45)], (0.62, 0.46, 0.26, 0.0), HAIR,
         HAIR_SHADE, LINE_HAIR)
    lock(cv, HEAD, [(-0.75, -0.35), (-1.3, -0.5), (-1.8, -0.75), (-2.1, -1.1)], (0.5, 0.36, 0.2, 0.0), HAIR,
         HAIR_SHADE, LINE_HAIR)


def draw_scarf_tails(cv):
    neck = g.Frame(BODY.on_thorax(-0.1, -0.2), unit=BODY.frame.unit)
    lock(cv, neck, [(-0.1, 0.0), (-0.8, -0.1), (-1.5, 0.15), (-2.3, -0.05), (-2.9, 0.25)],
         (0.24, 0.3, 0.27, 0.22, 0.14), SCARF, SCARF_SHADE, LINE_DARK, amount=0.35)
    lock(cv, neck, [(-0.1, 0.1), (-0.6, 0.3), (-1.1, 0.62), (-1.7, 0.62), (-2.1, 0.9)],
         (0.22, 0.28, 0.25, 0.2, 0.13), SCARF, SCARF_SHADE, LINE_DARK, amount=0.35)


def draw_body(cv):
    neck = figure.shape_of(cv, BODY.neck())
    cv.fill(neck, SKIN)
    under_chin = cv.shape(g.spline([BODY.on_thorax(-0.3, -0.75), BODY.on_thorax(0.3, -0.75),
                                    BODY.on_thorax(0.28, -0.3), BODY.on_thorax(-0.2, -0.22)], closed=True))
    cv.fill(under_chin, SKIN_SHADE, clip=neck)

    # 왼팔(화면 왼쪽)은 내려뜨린 채 화면 밖으로 나간다.
    union_part(cv, BODY.limb("upper_arm", "l", scale=1.3) + BODY.limb("forearm", "l", scale=1.25), JACKET,
               JACKET_SHADE, 0.4, LINE_DARK)

    b = BODY.build
    jacket = [(-0.3, -0.16), (0.3, -0.16), (b.shoulder + 0.12, -0.06), (b.shoulder + 0.14, 0.5),
              (b.ribcage + 0.2, 1.1), (b.ribcage + 0.16, 1.9), (-b.ribcage - 0.16, 1.9),
              (-b.ribcage - 0.2, 1.1), (-b.shoulder - 0.14, 0.5), (-b.shoulder - 0.12, -0.06)]
    torso = part(cv, [BODY.on_thorax(x, y) for x, y in jacket], JACKET, line=LINE_DARK, corners=(0, 1, 5, 6))
    # 가죽 재킷의 그림자: 목깃과 가슴이 드리우는 그늘, 빛 반대쪽 옆구리, 지퍼 여밈.
    for shade in ([(0.36, 0.1), (b.shoulder + 0.2, 0.2), (b.ribcage + 0.3, 1.2), (b.ribcage + 0.2, 2.0),
                   (0.42, 2.0), (0.5, 1.0)],
                  [(-0.5, 0.25), (0.35, 0.2), (0.3, 0.62), (-0.1, 0.78), (-0.55, 0.6)],
                  [(-0.75, 1.15), (-0.3, 1.3), (-0.36, 2.0), (-0.8, 2.0)]):
        cv.fill(cv.shape(g.spline([BODY.on_thorax(x, y) for x, y in shade], closed=True)), JACKET_SHADE,
                clip=torso)
    cv.stroke([BODY.on_thorax(0.04, -0.1), BODY.on_thorax(0.02, 1.95)], LINE_DARK, width=3.5, clip=torso)
    cv.stroke([BODY.on_thorax(0.09, 0.3), BODY.on_thorax(0.07, 1.95)], BRASS, width=3, opacity=0.9, clip=torso)
    pocket = [(-0.5, 0.95), (-0.12, 0.98), (-0.13, 1.12), (-0.5, 1.09)]
    cv.fill(cv.shape(g.polygon([BODY.on_thorax(x, y) for x, y in pocket])), JACKET_LIGHT, clip=torso)
    cv.stroke(g.polygon([BODY.on_thorax(x, y) for x, y in pocket]), LINE_DARK, width=2, closed=True, clip=torso)
    cv.fill(cv.edge_light(torso, LIGHT, width=9), JACKET_LIGHT, opacity=0.9)

    # 털 목깃: 가장자리를 거칠게 흔들어 털의 질감을 낸다.
    for sign in (-1.0, 1.0):
        collar = [(sign * 0.12, -0.3), (sign * 0.52, -0.3), (sign * 0.8, 0.0), (sign * 0.62, 0.52),
                  (sign * 0.2, 0.72), (sign * 0.06, 0.2)]
        fur = cv.roughen(cv.shape(g.spline([BODY.on_thorax(x, y) for x, y in collar], closed=True)), 7, 9)
        cv.fill(fur, FUR)
        cv.fill(cv.form_shadow(fur, LIGHT, 0.4), FUR_SHADE)
        cv.fill(cv.edge_light(fur, (-LIGHT[0], -LIGHT[1]), width=LINE_WIDTH), "#8a7a66")

    wrap = [(-0.3, -0.42), (0.3, -0.42), (0.36, -0.16), (0.0, -0.02), (-0.36, -0.16)]
    part(cv, [BODY.on_thorax(x, y) for x, y in wrap], SCARF, SCARF_SHADE, 0.4, LINE_DARK)


def draw_face(cv):
    # 성인 얼굴은 턱이 길고 눈이 작다. 눈 단위와 턱 길이로 나이대를 조절한다.
    right = [(0.0, -1.0), (0.62, -0.82), (0.96, -0.3), (0.98, 0.2), (0.88, 0.64), (0.6, 1.04), (0.28, 1.3)]
    chin = [(0.0, 1.4)]
    left = [(-x, y) for x, y in reversed(right[1:])]
    face = part(cv, HEAD(right + chin + left), SKIN, line=LINE_SKIN)

    brim_shadow = cv.shape(g.spline(HEAD([(-1.05, -0.95), (1.05, -0.95), (1.0, -0.12), (0.5, 0.0), (0.0, -0.1),
                                          (-0.5, 0.02), (-1.0, -0.1)]), closed=True))
    cv.fill(brim_shadow, SKIN_SHADE, clip=face)
    for cheek in (0.56, -0.56):
        blush = cv.shape(g.ellipse(*HEAD.point(cheek, 0.72), HEAD.length(0.24), HEAD.length(0.1)),
                         soft=HEAD.length(0.06))
        cv.fill(blush, BLUSH, opacity=0.32, clip=face)

    cv.stroke(g.spline(HEAD([(0.03, 0.74), (0.07, 0.86), (0.0, 0.9)]), closed=False), LINE_SKIN, width=2.4,
              taper=(0.2, 1, 0.6))
    mouth = g.spline(HEAD([(-0.2, 1.06), (-0.06, 1.1), (0.08, 1.09), (0.22, 1.02)]), closed=False)
    cv.stroke(mouth, LINE_SKIN, width=2.8, taper=(0.3, 1, 1, 0.3))
    cv.stroke(g.spline(HEAD([(-0.08, 1.17), (0.02, 1.19), (0.1, 1.165)]), closed=False), SKIN_SHADE, width=3.5,
              taper=(0.2, 1, 0.2))
    for side in (HEAD, HEAD.mirrored()):
        draw_eye(cv, side.child(0.47, 0.36, unit=0.27), face)
        brow = g.spline(side([(0.2, -0.02), (0.5, -0.12), (0.82, -0.02)]), closed=False)
        cv.stroke(brow, LINE_HAIR, width=4.0, taper=(0.6, 1, 0.2))
    return face


def draw_eye(cv, eye, face):
    """눈 1개. eye는 눈 중심이 원점이고 눈 반폭이 1인 좌표계. x 양의 방향이 눈꼬리다."""
    white_outline = g.spline(eye([(-1.0, 0.0), (-0.62, -0.42), (0.0, -0.6), (0.62, -0.52), (1.04, -0.14),
                                  (0.74, 0.46), (0.1, 0.64), (-0.62, 0.48)]), closed=True, corners=(0, 4))
    white = cv.shape(white_outline) & face
    cv.fill(white, "#ffffff")
    cv.fill(cv.shape(g.ellipse(*eye.point(0.0, -0.62), eye.length(1.3), eye.length(0.4))), "#c7d2ec", clip=white)

    center = (0.04, 0.02)
    iris = cv.shape(g.ellipse(*eye.point(*center), eye.length(0.56), eye.length(0.66), eye.rotate)) & white
    cv.fill(iris, Linear([(0.0, IRIS_TOP), (0.45, IRIS_MID), (1.0, IRIS_LOW)],
                         eye.point(center[0], -0.62), eye.point(center[0], 0.68)))
    cv.fill(cv.shape(g.ellipse(*eye.point(center[0], -0.6), eye.length(0.9), eye.length(0.5))),
            IRIS_TOP, opacity=0.75, clip=iris)
    cv.fill(cv.shape(g.ellipse(*eye.point(*center), eye.length(0.22), eye.length(0.3), eye.rotate)),
            "#0a1c14", clip=iris)
    cv.fill(cv.shape(g.ellipse(*eye.point(center[0], 0.42), eye.length(0.32), eye.length(0.17)),
                     soft=eye.length(0.05)), "#d9ffe6", opacity=0.7, clip=iris)
    ring = g.ellipse(*eye.point(*center), eye.length(0.56), eye.length(0.66), eye.rotate)
    cv.stroke(ring, IRIS_TOP, width=2.4, closed=True, clip=white)

    # 하이라이트는 광원 쪽에 맺히므로 좌우 눈에서 같은 화면 방향에 둔다.
    toward_light = 1.0 if eye.flip else -1.0
    cv.fill(cv.shape(g.ellipse(*eye.point(0.04 + 0.28 * toward_light, -0.3), eye.length(0.18), eye.length(0.22),
                               -20)), "#ffffff")
    cv.fill(cv.shape(g.ellipse(*eye.point(0.04 - 0.26 * toward_light, 0.32), eye.length(0.08))), "#ffffff",
            opacity=0.9)

    lash = [(-1.1, 0.06), (-0.72, -0.5), (-0.05, -0.78), (0.66, -0.7), (1.16, -0.36), (1.42, -0.02),
            (1.02, -0.14), (0.6, -0.48), (-0.05, -0.58), (-0.66, -0.36)]
    cv.fill(cv.shape(g.spline(eye(lash), closed=True, corners=(0, 5))), LINE_DARK)
    cv.stroke(g.spline(eye([(1.0, 0.14), (0.72, 0.5), (0.2, 0.66)]), closed=False), LINE_SKIN, width=2.2,
              taper=(1, 0.8, 0.2))
    cv.stroke(g.spline(eye([(-0.62, -0.8), (0.1, -1.02), (0.86, -0.86)]), closed=False), LINE_SKIN, width=1.8,
              taper=(0.2, 1, 0.2))


def draw_front_hair(cv):
    points = [(-1.1, -0.1), (-1.0, -0.7), (-0.55, -1.1), (0.1, -1.2), (0.68, -1.04), (1.06, -0.62), (1.14, -0.1),
              (1.08, 0.4), (0.96, 0.9),                      # 오른쪽 옆머리 끝
              (0.86, 0.4), (0.82, 0.0),                      # 골
              (0.7, 0.0), (0.5, 0.12),                       # 앞머리 끝 1
              (0.52, -0.1), (0.4, -0.36),                    # 골
              (0.2, -0.1), (-0.08, 0.1),                     # 끝 2
              (-0.02, -0.14), (-0.1, -0.42),                 # 골
              (-0.36, -0.12), (-0.62, 0.14),                 # 끝 3
              (-0.6, -0.1), (-0.62, -0.3),                   # 골
              (-0.84, 0.3), (-1.06, 0.92),                   # 왼쪽 옆머리 끝
              (-1.12, 0.4)]
    corners = (8, 10, 12, 14, 16, 18, 20, 22, 24)
    hair = part(cv, HEAD(points), HAIR, line=LINE_HAIR, corners=corners)
    shade_side = cv.shape(g.spline(HEAD([(0.75, -1.1), (1.2, -0.6), (1.2, 0.4), (1.0, 1.0), (0.88, 0.9),
                                         (0.96, 0.3), (0.92, -0.45)]), closed=True))
    cv.fill(shade_side, HAIR_SHADE, clip=hair)
    for tip in ([(0.42, -0.36), (0.5, -0.1), (0.5, 0.12), (0.64, -0.02)],
                [(-0.08, -0.42), (0.0, -0.14), (-0.08, 0.1), (0.12, -0.1)],
                [(-0.6, -0.3), (-0.58, -0.1), (-0.62, 0.14), (-0.44, -0.1)]):
        cv.fill(cv.shape(g.spline(HEAD(tip), closed=True, corners=(0, 2))), HAIR_SHADE, clip=hair)
    for strand in ([(0.4, -1.1), (0.5, -0.6), (0.52, 0.06)], [(-0.1, -1.16), (-0.12, -0.7), (-0.1, 0.02)],
                   [(-0.6, -1.0), (-0.66, -0.5), (-0.62, 0.08)], [(1.02, -0.3), (1.02, 0.3), (0.97, 0.8)],
                   [(-1.0, -0.2), (-0.98, 0.3), (-1.04, 0.82)]):
        cv.stroke(g.spline(HEAD(strand), closed=False), LINE_HAIR, width=1.6, taper=(0.2, 1, 0.2), clip=hair)
    for wisp in ([(0.22, -1.17), (0.0, -1.42), (-0.34, -1.4)], [(0.1, -1.18), (-0.04, -1.32), (-0.24, -1.3)]):
        cv.stroke(g.spline(HEAD(wisp), closed=False), HAIR, width=5.0, taper=(1, 0.7, 0))
        cv.stroke(g.spline(HEAD(wisp), closed=False), LINE_HAIR, width=1.2, taper=(1, 0.7, 0), opacity=0.6)


def draw_goggles(cv):
    """이마 위로 올려 쓴 고글. 렌즈에 하늘이 비쳐 화면의 파랑을 인물 안으로 끌어온다."""
    strap = g.spline(HEAD([(-1.08, -0.42), (-0.5, -0.66), (0.1, -0.72), (0.7, -0.62), (1.12, -0.36)]),
                     closed=False)
    cv.stroke(strap, LINE_DARK, width=HEAD.length(0.3))
    cv.stroke(strap, "#5a4034", width=HEAD.length(0.24))
    for sign in (-1.0, 1.0):
        center = HEAD.point(sign * 0.4, -0.66)
        rim = g.ellipse(*center, HEAD.length(0.36), HEAD.length(0.3), HEAD.rotate)
        cv.fill(cv.shape(rim), BRASS)
        cv.stroke(rim, LINE_DARK, width=LINE_WIDTH, closed=True, light=LIGHT, contrast=0.4)
        lens_path = g.ellipse(*center, HEAD.length(0.28), HEAD.length(0.22), HEAD.rotate)
        lens = cv.shape(lens_path)
        cv.fill(lens, Linear([LENS_TOP, LENS_LOW], HEAD.point(sign * 0.4, -0.9), HEAD.point(sign * 0.4, -0.44)))
        glint = cv.shape(g.polygon(HEAD([(sign * 0.4 - 0.26, -0.6), (sign * 0.4 - 0.06, -0.9),
                                         (sign * 0.4 + 0.06, -0.9), (sign * 0.4 - 0.14, -0.6)])))
        cv.fill(glint, "#ffffff", opacity=0.75, clip=lens)
        cv.stroke(lens_path, LINE_DARK, width=2.0, closed=True)
    cv.fill(cv.shape(g.rect(*HEAD.point(-0.07, -0.72), HEAD.length(0.14), HEAD.length(0.1))), BRASS)


def draw_raised_arm(cv):
    """고글에 올린 팔과 장갑 낀 손. 손은 손등이 보이는 방향이며 손가락을 모아 살짝 굽힌다."""
    union_part(cv, BODY.limb("upper_arm", "r", scale=1.3) + BODY.limb("forearm", "r", scale=1.25), JACKET,
               JACKET_SHADE, 0.42, LINE_DARK)
    wrist = BODY.limb_frame("wrist_r", "elbow_r")
    cuff = wrist([(-0.2, 0.0), (0.2, 0.0), (0.2, 0.26), (-0.2, 0.26)])
    cel(cv, g.spline(cuff, closed=True, corners=(0, 1, 2, 3)), FUR, FUR_SHADE, 0.35, LINE_DARK)

    hand = figure.hand_open(BODY.hand_frame("r", turn=-38), spread=0.45, curl=(0.22, 0.26, 0.3, 0.36),
                            thumb=0.7)
    glove = figure.shape_of(cv, hand.paths())
    for name in ("palm", "pinky", "ring", "middle", "index", "thumb"):
        finger = figure.shape_of(cv, hand.parts[name])
        cv.fill(finger, GLOVE)
        cv.fill(cv.form_shadow(finger, LIGHT, 0.35), GLOVE_SHADE)
        cv.fill(cv.edge_light(finger, (-LIGHT[0], -LIGHT[1]), width=2.2), LINE_DARK, opacity=0.8)
    cv.fill(cv.edge_light(glove, LIGHT, width=1.6), LINE_DARK)
    cv.fill(cv.edge_light(glove, (-LIGHT[0], -LIGHT[1]), width=LINE_WIDTH), LINE_DARK)


def paint_character(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    draw_scarf_tails(cv)
    draw_back_hair(cv)
    draw_body(cv)
    draw_face(cv)
    draw_front_hair(cv)
    draw_goggles(cv)
    draw_raised_arm(cv)
    return cv


# ---------- 합성과 촬영 ----------

def compose(background, character):
    anime.rim_light(character, LIGHT, width=3.0, tint="#fff6e0", opacity=0.6)
    background.paste(character)
    image = anime.finish(background)
    image = post.light_gradient(image, "#fff3c4", (0.0, 0.0), (0.7, 0.8), strength=0.12)
    return post.vignette(image, strength=0.12)


def main(out_dir="out", scale=1.0, seed=7):
    out_dir = Path(out_dir)
    background = paint_background(scale, seed)
    io.save(background.image(), out_dir / "anime_1_background.png")
    character = paint_character(scale, seed)
    io.save(character.guide_image(), out_dir / "anime_2_character_guide.png")
    image = compose(background, character)
    return io.save(image, out_dir / "anime_sky_pilot.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
