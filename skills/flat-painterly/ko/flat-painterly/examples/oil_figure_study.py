"""회화풍(유화) 예제: 창가의 인체 습작. 성인 여성의 고전 회화풍 인체 습작 입상.

공정: 자세(리그 각도) → 살의 큰 덩어리와 명암 → 해부 표지(쇄골, 가슴, 배꼽, 무릎) → 천과 머리 → 유화 패스.
비례는 figure.Figure가 보장한다. 장면 코드는 자세, 살의 명암, 표지의 위치만 결정한다.
실행: python oil_figure_study.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Radial, figure, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import oil  # noqa: E402

WIDTH, HEIGHT = 1100, 1500
LIGHT = (-0.75, -0.6)   # 왼쪽 창에서 드는 빛

# 팔레트: 어두운 갈색 배경 위에 따뜻한 살빛 하나만 밝게 둔다. 천의 청회색이 살의 주황을 받친다.
WALL_DARK, WALL_GLOW = "#1e1410", "#74503a"
SKIN, SKIN_LIGHT, SKIN_SHADE, SKIN_DEEP = "#e3ab88", "#fbe2c8", "#9c5a44", "#552a26"
SKIN_ROSE = "#d6806e"
CLOTH, CLOTH_SHADE, CLOTH_DEEP = "#dfe3e6", "#93a0ac", "#55606c"
HAIR, HAIR_LIGHT = "#22140f", "#7a4a30"
LIPS, EYE = "#a63c3c", "#24160f"

# 무릎 위에서 자르는 4분의 3 입상. 한쪽 다리에 체중을 실어 골반선과 어깨선이 반대로 기운다.
FULLER = figure.Build(shoulder=0.70, ribcage=0.61, waist=0.50, hip=0.83, arm=0.86, leg=1.08, neck=0.34)
BODY = figure.Figure(
    g.Frame(origin=(560, 1010), unit=236), build=FULLER,
    hip_tilt=-12, chest_tilt=9, spine=-5, neck=-4, head=-13,
    arm_l=(140, 290), arm_r=(10, -16), leg_l=(4, -6), leg_r=(-4, 2), stretch={"thigh_l": 0.96})
UNIT = BODY.frame.unit


def paint_room(cv):
    # 빛 받는 쪽 살은 어두운 벽 앞에, 그늘진 쪽 살은 밝은 벽 앞에 두어 윤곽이 양쪽 모두 읽히게 한다.
    cv.fill(cv.full(), Radial([WALL_GLOW, WALL_DARK], (900, 620), 900))
    cv.fill(cv.shape(g.rect(-50, -50, 420, HEIGHT + 100), soft=160), "#120b08", opacity=0.7)
    cv.direct(cv.full(), angle=-72)


def flesh(cv, paths, shadow=0.48, deep=0.22, highlight=0.12):
    """살 덩어리 1개: 밑색 → 부드러운 그늘 → 짙은 그늘 → 밝은 면. 합친 형태를 돌려준다."""
    shape = figure.shape_of(cv, paths)
    cv.fill(shape, SKIN)
    cv.fill(cv.form_shadow(shape, LIGHT, shadow, soft=0.4), SKIN_SHADE, opacity=0.85)
    cv.fill(cv.form_shadow(shape, LIGHT, deep, soft=0.3), SKIN_DEEP, opacity=0.6)
    cv.fill(cv.form_light(shape, LIGHT, highlight, soft=0.5), SKIN_LIGHT, opacity=0.85)
    # 그늘 쪽 윤곽에 붉은 반사광을 얹으면 살이 배경에 묻히지 않고 둥글게 돌아간다.
    cv.fill(cv.edge_light(shape, (-LIGHT[0], 0.2), width=UNIT * 0.035, soft=UNIT * 0.02), SKIN_ROSE, opacity=0.55)
    return shape


def mark(cv, center, rx, ry, paint, opacity, clip, soft, angle=0.0):
    """가장자리가 풀린 타원 얼룩. 뼈와 근육이 살 아래에서 만드는 완만한 밝기 변화를 표현한다.

    rx, ry, soft는 머리 높이 단위다.
    """
    shape = cv.shape(g.ellipse(center[0], center[1], rx * UNIT, ry * UNIT, angle), soft=soft * UNIT)
    cv.fill(shape, paint, opacity=opacity, clip=clip)


def paint_back_hair(cv):
    """등 뒤로 넘긴 긴 머리. 그늘 쪽 어깨 뒤로 흘러 살의 밝은 윤곽을 받쳐 준다."""
    head = BODY.head_frame()
    mass = g.spline(head([(-0.46, -0.1), (-0.36, -0.5), (0.0, -0.64), (0.4, -0.5), (0.56, -0.05), (0.66, 0.6),
                          (0.9, 1.3), (0.84, 2.0), (0.5, 2.2), (0.3, 1.5), (0.2, 0.7), (-0.2, 0.6),
                          (-0.5, 0.4)]), closed=True)
    hair = cv.shape(mass)
    cv.fill(hair, HAIR)
    cv.fill(cv.form_light(hair, LIGHT, 0.14, soft=0.4), HAIR_LIGHT, opacity=0.55)
    cv.direct(hair, angle=75)


def paint_raised_forearm(cv):
    hand = figure.hand_side(BODY.hand_frame("l", turn=24), curl=0.5)
    flesh(cv, BODY.limb("forearm", "l") + hand.paths(), shadow=0.5)


def paint_legs(cv):
    for side in ("l", "r"):
        leg = flesh(cv, BODY.limb("thigh", side) + BODY.limb("shin", side), shadow=0.45)
        knee = BODY.joint("knee_" + side)
        mark(cv, (knee[0] - 8, knee[1] - 6), 0.15, 0.17, SKIN_LIGHT, 0.5, leg, 0.06)
    # 뒤로 물러난 다리는 체중을 실은 다리의 그늘에 들어가 한 단계 어둡다.
    back_leg = figure.shape_of(cv, BODY.limb("thigh", "l"))
    inner = cv.shape(g.ellipse(*BODY.joint("knee_r"), UNIT * 0.55, UNIT * 2.4), soft=UNIT * 0.2)
    cv.fill(inner, SKIN_DEEP, opacity=0.45, clip=back_leg)


def paint_breast(cv, trunk, sign):
    """가슴 1개. 빛 쪽 윗면은 밝고 아래 바깥쪽은 그늘지며 몸통에 초승달 그림자를 드리운다."""
    cx, cy = BODY.on_thorax(sign * 0.35 - 0.03, 0.68)
    cast = cv.shape(g.ellipse(cx + UNIT * 0.05, cy + UNIT * 0.1, UNIT * 0.31, UNIT * 0.3), soft=UNIT * 0.04)
    cv.fill(cast, SKIN_SHADE, opacity=0.75, clip=trunk)
    outline = [(-0.27, -0.14), (0.0, -0.36), (0.26, -0.12), (0.31, 0.12), (0.04, 0.31), (-0.28, 0.13)]
    breast = cv.shape(g.spline([(cx + x * UNIT, cy + y * UNIT) for x, y in outline], closed=True),
                      soft=UNIT * 0.03)
    cv.fill(breast, SKIN, clip=trunk)
    cv.fill(cv.form_shadow(breast, LIGHT, 0.42, soft=0.45), SKIN_SHADE, opacity=0.8, clip=trunk)
    cv.fill(cv.form_shadow(breast, LIGHT, 0.14, soft=0.35), SKIN_DEEP, opacity=0.35, clip=trunk)
    cv.fill(cv.form_light(breast, LIGHT, 0.16, soft=0.5), SKIN_LIGHT, opacity=0.9, clip=trunk)
    mark(cv, (cx + UNIT * 0.035, cy + UNIT * 0.06), 0.055, 0.05, SKIN_ROSE, 0.8, trunk, 0.018)


def paint_trunk(cv):
    trunk = flesh(cv, BODY.neck() + BODY.torso() + BODY.limb("upper_arm", "l") + BODY.limb("upper_arm", "r"),
                  shadow=0.46, deep=0.2)
    # 목과 쇄골: 목 밑 오목한 자리와 좌우로 뻗는 쇄골의 밝은 능선.
    mark(cv, BODY.on_thorax(0.0, 0.0), 0.07, 0.06, SKIN_SHADE, 0.6, trunk, 0.025)
    for sign in (-1.0, 1.0):
        collar = g.spline([BODY.on_thorax(sign * 0.09, -0.03), BODY.on_thorax(sign * 0.36, -0.1),
                           BODY.on_thorax(sign * 0.62, -0.05)], closed=False)
        cv.stroke(collar, SKIN_SHADE, width=UNIT * 0.045, taper=(0.4, 1, 0.3), opacity=0.5, soft=UNIT * 0.018,
                  clip=trunk)
        cv.stroke(g.transform(collar, translate=(0, -UNIT * 0.045)), SKIN_LIGHT, width=UNIT * 0.04,
                  taper=(0.4, 1, 0.3), opacity=0.55, soft=UNIT * 0.018, clip=trunk)
    neck_shadow = cv.shape(g.spline([BODY.on_thorax(-0.2, -0.6), BODY.on_thorax(0.3, -0.62),
                                     BODY.on_thorax(0.26, -0.12), BODY.on_thorax(0.02, -0.02),
                                     BODY.on_thorax(-0.12, -0.3)], closed=True), soft=UNIT * 0.03)
    cv.fill(neck_shadow, SKIN_SHADE, opacity=0.6, clip=trunk)

    for sign in (-1.0, 1.0):
        paint_breast(cv, trunk, sign)
    mark(cv, BODY.on_thorax(-0.01, 0.6), 0.05, 0.3, SKIN_SHADE, 0.4, trunk, 0.05)

    # 배: 갈비뼈 아치, 가운데 세로 골, 배꼽, 아랫배의 둥근 면, 골반뼈 모서리.
    for sign in (-1.0, 1.0):
        arch = g.spline([BODY.on_thorax(sign * 0.06, 1.04), BODY.on_thorax(sign * 0.3, 1.2),
                         BODY.on_thorax(sign * 0.5, 1.5)], closed=False)
        cv.stroke(arch, SKIN_SHADE, width=UNIT * 0.09, taper=(0.3, 1, 0.2), opacity=0.3, soft=UNIT * 0.04,
                  clip=trunk)
    mark(cv, BODY.on_pelvis(0.0, -1.0), 0.03, 0.45, SKIN_SHADE, 0.35, trunk, 0.035)
    navel = BODY.on_pelvis(0.0, -0.72)
    mark(cv, navel, 0.032, 0.055, SKIN_DEEP, 0.9, trunk, 0.012)
    mark(cv, (navel[0] - UNIT * 0.02, navel[1] + UNIT * 0.08), 0.07, 0.035, SKIN_LIGHT, 0.5, trunk, 0.02)
    mark(cv, BODY.on_pelvis(-0.1, -0.32), 0.32, 0.22, SKIN_LIGHT, 0.35, trunk, 0.09)
    for sign in (-1.0, 1.0):
        mark(cv, BODY.on_pelvis(sign * 0.52, -0.42), 0.06, 0.16, SKIN_LIGHT, 0.45, trunk, 0.04, angle=sign * -22)
        lower_pelvis = g.spline([BODY.on_pelvis(sign * 0.6, -0.3), BODY.on_pelvis(sign * 0.36, 0.05),
                          BODY.on_pelvis(sign * 0.1, 0.34)], closed=False)
        cv.stroke(lower_pelvis, SKIN_SHADE, width=UNIT * 0.05, taper=(0.2, 1, 0.6), opacity=0.4, soft=UNIT * 0.02,
                  clip=trunk)
    # 올린 팔의 겨드랑이와 어깨 근육의 경계.
    mark(cv, BODY.on_thorax(-0.62, 0.2), 0.05, 0.15, SKIN_SHADE, 0.7, trunk, 0.03, angle=-25)
    mark(cv, BODY.on_thorax(0.66, 0.3), 0.05, 0.3, SKIN_DEEP, 0.4, trunk, 0.03, angle=6)
    return trunk


def paint_cloth(cv):
    """골반에 걸쳐 흘러내린 천. 오른손이 골반 옆에서 쥐고 있다."""
    hold = BODY.joint("wrist_r")
    top = [BODY.on_pelvis(-0.88, 0.1), BODY.on_pelvis(-0.4, 0.3), BODY.on_pelvis(0.2, 0.16),
           BODY.on_pelvis(0.86, -0.1)]
    fall = [(hold[0] + UNIT * 0.32, hold[1] + UNIT * 0.3), (hold[0] + UNIT * 0.5, HEIGHT + 40),
            (hold[0] - UNIT * 0.9, HEIGHT + 40), (hold[0] - UNIT * 0.75, hold[1] + UNIT * 1.6)]
    under = [BODY.on_pelvis(0.1, 0.95), BODY.on_pelvis(-0.5, 0.78), BODY.on_pelvis(-0.95, 0.5)]
    cloth = cv.shape(g.spline(top + fall + under, closed=True, corners=(0, 3)))
    cv.fill(cloth, CLOTH)
    cv.fill(cv.form_shadow(cloth, LIGHT, 0.45, soft=0.35), CLOTH_SHADE, opacity=0.85)
    # 주름은 쥔 손에서 부채꼴로 퍼진다. 주름마다 어두운 골과 그 왼쪽의 밝은 능선을 짝지어 그린다.
    ends = [BODY.on_pelvis(-0.8, 0.2), BODY.on_pelvis(-0.7, 0.55), BODY.on_pelvis(-0.2, 0.85),
            (hold[0] - UNIT * 0.5, HEIGHT), (hold[0] - UNIT * 0.1, HEIGHT), (hold[0] + UNIT * 0.3, HEIGHT)]
    for end in ends:
        middle = ((hold[0] + end[0]) / 2.0, (hold[1] + end[1]) / 2.0 + UNIT * 0.12)
        fold = g.spline([(hold[0] - UNIT * 0.05, hold[1] + UNIT * 0.2), middle, end], closed=False)
        cv.stroke(fold, CLOTH_DEEP, width=UNIT * 0.08, taper=(0.2, 1, 0.5), opacity=0.7, soft=UNIT * 0.025,
                  clip=cloth)
        cv.stroke(g.transform(fold, translate=(-UNIT * 0.07, -UNIT * 0.03)), "#f7f8f9", width=UNIT * 0.06,
                  taper=(0.2, 1, 0.5), opacity=0.8, soft=UNIT * 0.02, clip=cloth)
    cv.direct(cloth, angle=65)


def paint_front_arm(cv):
    hand = figure.hand_side(BODY.hand_frame("r", turn=-12, flip=True), curl=0.8)
    arm = flesh(cv, BODY.limb("forearm", "r") + hand.paths(), shadow=0.5)
    # 팔꿈치에서 위팔과 아래팔의 명암이 끊기지 않도록 이음매를 살빛으로 풀어 준다.
    elbow = BODY.joint("elbow_r")
    upper = figure.shape_of(cv, BODY.limb("upper_arm", "r"))
    mark(cv, (elbow[0] - UNIT * 0.04, elbow[1]), 0.17, 0.2, SKIN, 0.9, arm | upper, 0.07)
    mark(cv, (elbow[0] + UNIT * 0.08, elbow[1]), 0.08, 0.24, SKIN_SHADE, 0.7, arm | upper, 0.05)


def paint_face(cv, face):
    head = BODY.head_frame()
    for cheek, strength in ((-0.17, 0.5), (0.2, 0.3)):
        mark(cv, head.point(cheek, 0.14), 0.09, 0.06, SKIN_ROSE, strength, face, 0.035)
    for side in (head, head.mirrored()):
        mark(cv, side.point(0.165, -0.04), 0.105, 0.06, SKIN_SHADE, 0.75, face, 0.02)
        eye = cv.shape(g.spline(side([(0.075, -0.012), (0.16, -0.042), (0.255, -0.018), (0.165, 0.008)]),
                                closed=True, corners=(0, 2)))
        cv.fill(eye, "#cdbcae", clip=face)
        cv.fill(cv.shape(g.ellipse(*side.point(0.165, -0.02), UNIT * 0.03)), EYE, clip=eye)
        # 반쯤 내린 윗눈꺼풀. 속눈썹 선이 눈의 윗변을 따라 굵게 지나간다.
        cv.stroke(g.spline(side([(0.07, -0.012), (0.16, -0.048), (0.265, -0.02)]), closed=False), EYE,
                  width=UNIT * 0.02, taper=(0.5, 1, 0.8))
        cv.stroke(g.spline(side([(0.08, -0.06), (0.165, -0.092), (0.25, -0.06)]), closed=False), SKIN_SHADE,
                  width=UNIT * 0.012, opacity=0.7, clip=face)
        cv.stroke(g.spline(side([(0.06, -0.125), (0.17, -0.165), (0.29, -0.115)]), closed=False), HAIR,
                  width=UNIT * 0.024, taper=(0.7, 1, 0.3), opacity=0.9, clip=face)
    # 코는 윤곽선 없이 빛 받는 콧등과 그늘진 옆면, 코 밑 그림자로만 드러낸다.
    cv.stroke(g.spline(head([(-0.015, -0.03), (-0.02, 0.1), (-0.012, 0.17)]), closed=False), SKIN_LIGHT,
              width=UNIT * 0.035, opacity=0.75, soft=UNIT * 0.012, clip=face)
    cv.stroke(g.spline(head([(0.035, -0.02), (0.045, 0.12), (0.062, 0.185)]), closed=False), SKIN_SHADE,
              width=UNIT * 0.04, opacity=0.7, soft=UNIT * 0.015, clip=face)
    mark(cv, head.point(0.015, 0.205), 0.062, 0.022, SKIN_DEEP, 0.7, face, 0.01)
    lips = cv.shape(g.spline(head([(-0.105, 0.29), (-0.04, 0.262), (0.0, 0.274), (0.04, 0.262), (0.105, 0.29),
                                   (0.05, 0.335), (-0.05, 0.335)]), closed=True, corners=(0, 4)))
    cv.fill(lips, LIPS, clip=face)
    cv.stroke(g.spline(head([(-0.105, 0.29), (0.0, 0.298), (0.105, 0.29)]), closed=False), "#4a1c1c",
              width=UNIT * 0.012, clip=face)
    mark(cv, head.point(-0.02, 0.316), 0.03, 0.012, "#e08a80", 0.7, lips, 0.006)
    mark(cv, head.point(0.0, 0.375), 0.07, 0.02, SKIN_SHADE, 0.55, face, 0.012)


def paint_head(cv):
    head = BODY.head_frame()
    face = flesh(cv, BODY.head(), shadow=0.42, deep=0.12)
    paint_face(cv, face)
    top = cv.shape(g.spline(head([(-0.4, 0.0), (-0.44, -0.3), (-0.26, -0.54), (0.04, -0.6), (0.32, -0.5),
                                  (0.45, -0.24), (0.44, 0.1), (0.35, -0.16), (0.16, -0.34), (-0.08, -0.33),
                                  (-0.3, -0.22)]), closed=True, corners=(0, 6)))
    cv.fill(top, HAIR)
    cv.fill(cv.form_light(top, LIGHT, 0.2, soft=0.4), HAIR_LIGHT, opacity=0.8)
    # 어깨 앞으로 넘어온 머리 가닥이 쇄골을 지나 가슴 옆으로 흘러내린다.
    for points, widths in (([(0.4, 0.05), (0.52, 0.6), (0.72, 1.2), (0.7, 1.75)], (0.16, 0.2, 0.15, 0.0)),
                           ([(0.34, 0.0), (0.4, 0.5), (0.5, 0.95), (0.44, 1.4)], (0.1, 0.13, 0.1, 0.0)),
                           ([(-0.4, -0.05), (-0.46, 0.2), (-0.4, 0.45)], (0.06, 0.07, 0.0))):
        spine = g.spline(head(points), closed=False)
        lock = cv.shape(*g.ribbon(spine, [width * UNIT for width in widths]))
        cv.fill(lock, HAIR)
        cv.stroke(g.transform(spine, translate=(-UNIT * 0.02, 0)), HAIR_LIGHT, width=UNIT * 0.02,
                  taper=(0, 1, 0), opacity=0.7, clip=lock)
    cv.direct(face, angle=80)


def paint_underpainting(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_room(cv)
    paint_back_hair(cv)
    paint_raised_forearm(cv)
    paint_legs(cv)
    trunk = paint_trunk(cv)
    paint_cloth(cv)
    paint_front_arm(cv)
    paint_head(cv)
    cv.direct(trunk, angle=82)
    return cv


def main(out_dir="out", scale=1.0, seed=13):
    out_dir = Path(out_dir)
    cv = paint_underpainting(scale, seed)
    io.save(cv.guide_image(), out_dir / "figure_1_underpainting_guide.png")
    focus = cv.shape(g.ellipse(560, 560, 420, 640), soft=60)
    image = oil.render(cv, brush_radii=(22.0, 10.0, 4.5, 2.2), detail=focus, relief=0.4, color_jitter=0.035)
    image = post.grade(image, shadows="#2a1c2a", highlights="#ffe6c4", amount=0.08, contrast=1.05)
    return io.save(post.vignette(image, strength=0.3), out_dir / "oil_figure_study.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
