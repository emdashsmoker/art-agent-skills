"""일러스트풍 예제: 가을 공원을 걷는 사람(전신).

공정: 자세(리그 각도) → 배경 색면 → 몸과 옷의 평면 도형 → 점묘 명암 → 인쇄 질감 패스.
전신 비례는 figure.Figure가 보장한다. 옷은 팔다리 윤곽의 굵기 배율과 관절 좌표를 이어 만든다.
실행: python illustration_autumn_walk.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, figure, io, motifs  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import illustration  # noqa: E402

WIDTH, HEIGHT = 1100, 1500
LIGHT = (-0.7, -0.7)
GROUND_Y = 1330

# 팔레트: 크림색 바탕에 주황-겨자 계열 단풍이 지배색. 코트의 청록이 보색 강조이고 베레모의 빨강은 초점에만 쓴다.
PAPER, SKY_WARM = "#f3e6cf", "#f7d9a8"
LEAF_PALETTES = [("#f2b84b", "#e08a3a", "#b85a2a"), ("#e9933f", "#cf6030", "#8f3a26"),
                 ("#f0cf6a", "#dba640", "#a8742e")]
TRUNK = "#5a3b30"
PATH, PATH_SHADE, GRASS = "#e3c79a", "#c9a56e", "#b9a04e"
SKIN, SKIN_SHADE = "#f0c2a0", "#d2916e"
COAT, COAT_SHADE, COAT_LIGHT = "#1f5a62", "#123a44", "#3f8a8a"
KNIT, TROUSERS, TROUSERS_SHADE = "#f1e3c8", "#2a2f4a", "#181c30"
SCARF, SCARF_SHADE = "#e3b23c", "#b57f24"
BERET, BOOT = "#c7402d", "#2a1c1a"
HAIR, HAIR_LIGHT = "#3a2420", "#6a4030"
CUP, CUP_BAND = "#f7f0e2", "#8a5a3a"

# 정면으로 걸어오는 자세. 앞으로 내디딘 다리에 체중이 실리고 뒤에 남은 다리는 정강이가 짧아 보인다.
BODY = figure.Figure(
    g.Frame(origin=(600, 742), unit=146), build=figure.FEMALE,
    hip_tilt=7, chest_tilt=-5, spine=1, head=4,
    arm_l=(13, 6), arm_r=(14, -128), leg_l=(-3, 1), leg_r=(6, -4),
    stretch={"shin_r": 0.82, "forearm_r": 0.82})
UNIT = BODY.frame.unit


def stipple(cv, shape, paint, opacity=1.0, clip=None):
    cv.fill(shape, paint, opacity=opacity, clip=clip, grain=1.0)


def paint_park(cv, rng):
    cv.fill(cv.full(), PAPER)
    stipple(cv, cv.shape(g.ellipse(560, 520, 620, 520), soft=120), SKY_WARM, opacity=0.9)
    ground = cv.shape(g.rect(0, 1180, WIDTH, HEIGHT - 1180))
    cv.fill(ground, GRASS)
    path = cv.shape(g.spline([(360, HEIGHT + 20), (470, 1300), (560, 1190), (640, 1190), (820, 1300),
                              (980, HEIGHT + 20)], closed=True, corners=(0, 5)))
    cv.fill(path, PATH)
    stipple(cv, cv.shape(g.rect(0, 1380, WIDTH, 160), soft=50), PATH_SHADE, clip=path)

    # 뒤에서 앞으로: 먼 나무는 작고 옅게, 가까운 나무는 화면 가장자리를 감싸도록 크게.
    trees = [(170, 1190, 260, 0), (930, 1195, 240, 2), (420, 1185, 170, 1), (760, 1185, 160, 0),
             (40, 1260, 430, 1), (1070, 1270, 460, 2)]
    for x, base, size, palette_index in trees:
        trunk = g.ribbon(g.spline([(x, base), (x + size * 0.03, base - size * 0.5), (x - size * 0.02,
                                                                                     base - size * 0.95)],
                                  closed=False), (size * 0.11, size * 0.07, size * 0.03))
        cv.fill(cv.shape(*trunk), TRUNK)
        motifs.canopy(cv, x, base - size * 1.05, size * 1.15, size * 0.95, light=LIGHT,
                      palette=LEAF_PALETTES[palette_index], puffs=26, rng=rng)
    for _ in range(46):
        x, y = rng.uniform(40, WIDTH - 40), rng.uniform(200, 1460)
        leaf = g.Frame(origin=(x, y), unit=rng.uniform(8, 15), rotate=rng.uniform(0, 360))
        shape = cv.shape(g.spline(leaf([(0, -1), (0.55, 0), (0, 1), (-0.55, 0)]), closed=True, corners=(0, 2)))
        cv.fill(shape, LEAF_PALETTES[int(rng.integers(3))][int(rng.integers(3))])


def paint_legs(cv):
    for side in ("r", "l"):   # 뒤에 남은 다리를 먼저 그린다
        leg = figure.shape_of(cv, BODY.limb("thigh", side, scale=1.25) + BODY.limb("shin", side, scale=1.5))
        cv.fill(leg, TROUSERS)
        stipple(cv, cv.form_shadow(leg, LIGHT, 0.4, soft=0.4), TROUSERS_SHADE, clip=leg)
        ankle = BODY.joint("ankle_" + side)
        boot = figure.shape_of(cv, BODY.foot(side, turn=10))
        shaft = cv.shape(g.rect(ankle[0] - UNIT * 0.17, ankle[1] - UNIT * 0.3, UNIT * 0.34, UNIT * 0.34, 8))
        cv.fill(boot | shaft, BOOT)
    # 뒤 다리는 앞 다리의 그늘에 들어간다.
    back_leg = figure.shape_of(cv, BODY.limb("thigh", "r", scale=1.25) + BODY.limb("shin", "r", scale=1.5))
    stipple(cv, cv.shape(g.rect(0, 0, WIDTH, HEIGHT)), TROUSERS_SHADE, opacity=0.5, clip=back_leg)


def paint_coat(cv):
    b = BODY.build
    # 무릎까지 내려오는 코트. 어깨는 흉곽 좌표, 밑단은 골반 좌표에 맞춰 몸의 기울기를 따라간다.
    outline = [BODY.on_thorax(-0.26, -0.2), BODY.on_thorax(0.26, -0.2), BODY.on_thorax(b.shoulder + 0.14, -0.04),
               BODY.on_thorax(b.ribcage + 0.22, 1.0), BODY.on_pelvis(b.hip + 0.16, 0.0),
               BODY.on_pelvis(b.hip + 0.34, 1.85), BODY.on_pelvis(0.2, 1.98), BODY.on_pelvis(-0.3, 1.9),
               BODY.on_pelvis(-b.hip - 0.3, 1.82), BODY.on_pelvis(-b.hip - 0.16, 0.0),
               BODY.on_thorax(-b.ribcage - 0.22, 1.0), BODY.on_thorax(-b.shoulder - 0.14, -0.04)]
    coat = cv.shape(g.spline(outline, closed=True, corners=(0, 1, 5, 8)))
    cv.fill(coat, COAT)
    stipple(cv, cv.form_shadow(coat, LIGHT, 0.4, soft=0.45), COAT_SHADE, clip=coat)
    # 열린 앞섶 사이로 니트와 바지가 보인다.
    opening = cv.shape(g.spline([BODY.on_thorax(-0.16, -0.16), BODY.on_thorax(0.16, -0.16),
                                 BODY.on_thorax(0.2, 1.0), BODY.on_pelvis(0.34, 1.95), BODY.on_pelvis(-0.22, 1.9),
                                 BODY.on_thorax(-0.14, 1.0)], closed=True, corners=(0, 1, 3, 4)))
    cv.fill(opening, KNIT, clip=coat)
    lower = cv.shape(g.polygon([BODY.on_pelvis(-1.2, -0.25), BODY.on_pelvis(1.2, -0.25), BODY.on_pelvis(1.2, 2.2),
                                BODY.on_pelvis(-1.2, 2.2)]))
    cv.fill(lower, TROUSERS, clip=opening & coat)
    stipple(cv, cv.shape(g.rect(*BODY.on_thorax(-0.2, 0.9), UNIT * 0.4, UNIT * 0.5), soft=14), SCARF_SHADE,
            opacity=0.35, clip=opening & coat)
    for sign in (-1.0, 1.0):
        lapel = [BODY.on_thorax(sign * 0.16, -0.16), BODY.on_thorax(sign * 0.5, 0.2),
                 BODY.on_thorax(sign * 0.2, 1.0)]
        cv.fill(cv.shape(g.polygon(lapel)), COAT_LIGHT, clip=coat)
    for button_y in (1.25, 1.75):
        cv.fill(cv.shape(g.ellipse(*BODY.on_thorax(0.42, button_y), UNIT * 0.045)), COAT_SHADE)
    return coat


def paint_sleeve(cv, side, hand, hand_order):
    sleeve = figure.shape_of(cv, BODY.limb("upper_arm", side, scale=1.45)
                             + BODY.limb("forearm", side, scale=1.4))
    cv.fill(sleeve, COAT)
    stipple(cv, cv.form_shadow(sleeve, LIGHT, 0.42, soft=0.4), COAT_SHADE, clip=sleeve)
    stipple(cv, cv.edge_light(sleeve, LIGHT, width=10, soft=4), COAT_LIGHT, clip=sleeve)
    for name in hand_order:
        finger = figure.shape_of(cv, hand.parts[name])
        cv.fill(finger, SKIN)
        cv.fill(cv.edge_light(finger, (-LIGHT[0], -LIGHT[1]), width=3.5), SKIN_SHADE)


def paint_arms(cv):
    relaxed = figure.hand_side(BODY.hand_frame("l", flip=True), curl=0.3)
    paint_sleeve(cv, "l", relaxed, ("palm", "pinky", "ring", "middle", "index", "thumb"))

    # 컵을 든 손: 컵을 먼저 그리고 손가락이 컵을 감싸도록 그 위에 그린다.
    grip_frame = BODY.hand_frame("r", turn=40)
    grip = figure.hand_side(grip_frame, curl=0.62)
    cup_frame = g.Frame(grip_frame.point(-0.3, -0.52), unit=UNIT, rotate=0)
    cup = cv.shape(g.polygon(cup_frame([(-0.2, -0.36), (0.2, -0.36), (0.15, 0.3), (-0.15, 0.3)])))
    cv.fill(cup, CUP)
    cv.fill(cv.shape(g.polygon(cup_frame([(-0.185, -0.12), (0.185, -0.12), (0.165, 0.14), (-0.165, 0.14)]))),
            CUP_BAND)
    cv.fill(cv.shape(g.rect(*cup_frame.point(-0.22, -0.44), UNIT * 0.44, UNIT * 0.1, 4)), CUP_BAND)
    paint_sleeve(cv, "r", grip, ("palm", "thumb", "pinky", "ring", "middle", "index"))


def paint_scarf(cv):
    wrap = cv.shape(g.spline([BODY.on_thorax(-0.34, -0.5), BODY.on_thorax(0.34, -0.52), BODY.on_thorax(0.44, -0.1),
                              BODY.on_thorax(0.0, 0.1), BODY.on_thorax(-0.44, -0.08)], closed=True))
    tail = cv.shape(*g.ribbon(g.spline([BODY.on_thorax(-0.2, -0.05), BODY.on_thorax(-0.3, 0.6),
                                        BODY.on_thorax(-0.22, 1.2)], closed=False),
                              (UNIT * 0.3, UNIT * 0.34, UNIT * 0.3)))
    for piece in (tail, wrap):
        cv.fill(piece, SCARF)
        stipple(cv, cv.form_shadow(piece, LIGHT, 0.4, soft=0.4), SCARF_SHADE, clip=piece)
    for stripe_y in (0.85, 1.0):
        cv.stroke([BODY.on_thorax(-0.4, stripe_y), BODY.on_thorax(-0.05, stripe_y + 0.03)], BERET, width=6,
                  clip=tail)


def paint_head(cv):
    head = BODY.head_frame()
    face = figure.shape_of(cv, BODY.head())
    cv.fill(face, SKIN)
    stipple(cv, cv.form_shadow(face, LIGHT, 0.35, soft=0.4), SKIN_SHADE, opacity=0.8, clip=face)
    for side in (head, head.mirrored()):
        cv.fill(cv.shape(g.ellipse(*side.point(0.16, 0.0), UNIT * 0.03, UNIT * 0.04)), HAIR, clip=face)
        cv.stroke(g.spline(side([(0.08, -0.1), (0.17, -0.13), (0.26, -0.09)]), closed=False), HAIR, width=3.5,
                  taper=(0.6, 1, 0.3))
        cv.fill(cv.shape(g.ellipse(*side.point(0.21, 0.15), UNIT * 0.075, UNIT * 0.045), soft=5), "#e98a78",
                opacity=0.5, clip=face)
    cv.stroke(g.spline(head([(0.0, 0.02), (0.035, 0.16), (0.0, 0.18)]), closed=False), SKIN_SHADE, width=3.5)
    cv.fill(cv.shape(g.spline(head([(-0.07, 0.29), (0.0, 0.275), (0.07, 0.29), (0.0, 0.325)]), closed=True,
                              corners=(0, 2))), BERET)
    fringe = cv.shape(g.spline(head([(-0.4, 0.05), (-0.42, -0.3), (-0.2, -0.5), (0.2, -0.5), (0.42, -0.3),
                                     (0.41, 0.08), (0.3, -0.2), (0.05, -0.27), (-0.1, -0.16), (-0.3, -0.2)]),
                               closed=True, corners=(0, 5, 8)))
    cv.fill(fringe, HAIR)
    stipple(cv, cv.edge_light(fringe, LIGHT, width=9, soft=4), HAIR_LIGHT, clip=fringe)
    beret = cv.shape(g.spline(head([(-0.5, -0.36), (-0.3, -0.66), (0.2, -0.74), (0.56, -0.56), (0.5, -0.32),
                                    (0.0, -0.4)]), closed=True))
    cv.fill(beret, BERET)
    stipple(cv, cv.form_shadow(beret, LIGHT, 0.4, soft=0.4), "#8a2a22", clip=beret)
    cv.stroke(head([(0.1, -0.72), (0.14, -0.82)]), BERET, width=7)


def paint_back_hair(cv):
    """코트보다 먼저 그리는 뒷머리와 목. 목도리와 코트 깃이 그 위를 덮는다."""
    head = BODY.head_frame()
    back_hair = cv.shape(g.spline(head([(-0.42, -0.2), (-0.3, -0.5), (0.3, -0.5), (0.44, -0.15), (0.5, 0.5),
                                        (0.3, 0.72), (-0.34, 0.7), (-0.5, 0.45)]), closed=True))
    cv.fill(back_hair, HAIR)
    cv.fill(figure.shape_of(cv, BODY.neck()), SKIN_SHADE)


def paint_figure(cv):
    # 발밑의 접지 그림자가 인물을 길 위에 세운다.
    stipple(cv, cv.shape(g.ellipse(640, GROUND_Y + 48, 190, 26), soft=10), PATH_SHADE)
    paint_legs(cv)
    paint_back_hair(cv)
    paint_coat(cv)
    paint_scarf(cv)
    paint_arms(cv)
    paint_head(cv)


def main(out_dir="out", scale=1.0, seed=17):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    paint_park(cv, rng)
    paint_figure(cv)
    io.save(cv.guide_image(), out_dir / "walk_1_flat_guide.png")
    return io.save(illustration.render(cv), out_dir / "illustration_autumn_walk.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
