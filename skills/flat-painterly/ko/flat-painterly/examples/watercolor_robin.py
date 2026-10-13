"""회화풍(수채화) 예제: 꽃 핀 가지에 앉은 울새.

공정: 배경 번짐 → 가지와 꽃 → 새(옅은 밑칠 → 겹칠 → 마른 붓 세부) → 수채화 패스.
수채화는 밝은 색에서 어두운 색 순서로 쌓는다. 흰색 물감을 쓰지 않고 종이를 남겨 밝은 곳을 만든다.
실행: python watercolor_robin.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, io, motifs  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402
from codepaint.styles.watercolor import wash  # noqa: E402

WIDTH, HEIGHT = 1200, 1500
LIGHT = (-0.6, -0.8)

# 팔레트: 주황 가슴이 유일한 고채도 난색이다. 배경은 그 보색인 청록을 옅게 풀어 새를 띄운다.
WASH_TEAL, WASH_LILAC, WASH_ROSE = "#9fd0d2", "#c9c3e8", "#f6cfd2"
BREAST, BREAST_DEEP = "#f08a2e", "#d2521c"
BACK, BACK_DEEP = "#9a7a5c", "#5a4234"
BELLY_SHADE = "#b8b4c4"
INK = "#2e2622"
BRANCH, BRANCH_DEEP = "#8a6e5a", "#4a3830"
PETAL, PETAL_DEEP, STAMEN = "#f7b4c6", "#de5f8a", "#c23a5e"
LEAF, LEAF_DEEP = "#9cc070", "#55803f"

BIRD = g.Frame(origin=(650, 588), unit=250)


def paint_background(cv, rng):
    wash(cv, g.blob(600, 600, 430, 0.22, 10, rng, stretch=(1.0, 1.05)), WASH_TEAL, 0.6, soft=30, rough=22)
    wash(cv, g.blob(840, 900, 290, 0.3, 9, rng), WASH_LILAC, 0.55, soft=45, rough=20)
    wash(cv, g.blob(330, 930, 260, 0.3, 9, rng), WASH_ROSE, 0.8, soft=45, rough=20)
    wash(cv, g.blob(420, 380, 220, 0.3, 8, rng), WASH_LILAC, 0.45, soft=50, rough=20)
    # 물이 고였다 마른 자리(백런). 큰 번짐 안에 밝은 얼룩을 남긴다.
    for x, y, radius in ((760, 420, 90), (480, 760, 70), (900, 700, 60)):
        bloom = cv.roughen(cv.shape(g.blob(x, y, radius, 0.35, 8, rng), soft=14), 12, 18)
        cv.fill(bloom, "#ffffff", opacity=0.35)
    motifs.splatter(cv, (930, 1080), 150, 26, [WASH_TEAL, WASH_LILAC, PETAL_DEEP], rng=rng)
    motifs.splatter(cv, (230, 330), 110, 16, [WASH_ROSE, WASH_TEAL], rng=rng)


def branch_stroke(cv, points, widths):
    spine = g.spline(points, closed=False)
    outline = g.ribbon(spine, widths)[0]
    shape = wash(cv, outline, BRANCH, 0.9, soft=1.5, rough=3.0)
    cv.fill(cv.form_shadow(shape, LIGHT, 0.45, soft=0.25), BRANCH_DEEP, opacity=0.75, blend=Blend.MULTIPLY)
    cv.fill(cv.mottle(shape, 24, 0.35, 0.12), BRANCH_DEEP, opacity=0.5, blend=Blend.MULTIPLY)


def paint_branch(cv):
    branch_stroke(cv, [(-40, 1150), (280, 1010), (620, 842), (930, 690), (1240, 470)], (40, 34, 26, 18, 9))
    branch_stroke(cv, [(300, 1000), (250, 860), (150, 740), (120, 610)], (16, 12, 8, 3))
    branch_stroke(cv, [(930, 690), (1010, 560), (1000, 400), (1060, 270)], (14, 11, 8, 3))
    branch_stroke(cv, [(760, 774), (860, 850), (1000, 880), (1110, 960)], (12, 9, 7, 3))


def paint_blossom(cv, x, y, size, turn, rng):
    flower = g.Frame(origin=(x, y), unit=size, rotate=turn)
    for index in range(5):
        petal_frame = g.Frame(origin=(x, y), unit=size, rotate=turn + index * 72)
        outline = g.spline(petal_frame([(0.0, -0.12), (0.42, -0.5), (0.34, -1.0), (0.0, -0.9), (-0.34, -1.0),
                                        (-0.42, -0.5)]), closed=True)
        petal = wash(cv, outline, PETAL, rng.uniform(0.6, 0.9), soft=2.5, rough=3.0)
        # 꽃잎 안쪽은 물감이 중심으로 몰려 진하다.
        core = cv.shape(g.ellipse(*petal_frame.point(0.0, -0.3), size * 0.3, size * 0.34), soft=size * 0.14)
        cv.fill(core, PETAL_DEEP, opacity=0.55, clip=petal, blend=Blend.MULTIPLY)
    for index in range(7):
        angle = np.deg2rad(turn + index * 51 + rng.uniform(-10, 10))
        tip = flower.point(0.0, 0.0)[0] + np.cos(angle) * size * 0.34, flower.point(0.0, 0.0)[1] + np.sin(angle) * size * 0.34
        cv.stroke([(x, y), tip], STAMEN, width=1.4, opacity=0.8)
        cv.fill(cv.shape(g.ellipse(*tip, size * 0.05)), STAMEN)


def paint_bud(cv, x, y, size, turn):
    bud = g.Frame(origin=(x, y), unit=size, rotate=turn)
    wash(cv, g.spline(bud([(0.0, 0.3), (0.34, 0.0), (0.12, -0.55), (0.0, -0.7), (-0.12, -0.55), (-0.34, 0.0)]),
                      closed=True), PETAL_DEEP, 0.8, soft=1.5, rough=2.0)
    wash(cv, g.spline(bud([(0.0, 0.62), (0.26, 0.3), (0.0, 0.08), (-0.26, 0.3)]), closed=True), LEAF_DEEP, 0.85,
         soft=1.0, rough=1.5)


def paint_leaf(cv, x, y, size, turn):
    leaf = g.Frame(origin=(x, y), unit=size, rotate=turn)
    shape = wash(cv, g.spline(leaf([(0.0, 0.0), (0.34, -0.4), (0.0, -1.2), (-0.34, -0.4)]), closed=True,
                              corners=(0, 2)), LEAF, 0.85, soft=1.5, rough=2.5)
    cv.fill(cv.form_shadow(shape, LIGHT, 0.45, soft=0.3), LEAF_DEEP, opacity=0.6, blend=Blend.MULTIPLY)
    cv.stroke(g.spline(leaf([(0.0, -0.05), (0.03, -0.6), (0.0, -1.1)]), closed=False), LEAF_DEEP, width=1.5,
              taper=(1, 0.6, 0.1), opacity=0.7)


def paint_flowers(cv, rng):
    blossoms = [(150, 700, 52, 10), (110, 590, 40, 40), (245, 850, 46, 200), (1010, 520, 54, 20),
                (1000, 385, 44, 300), (1075, 265, 36, 100), (1010, 885, 48, 160), (1120, 965, 38, 60),
                (420, 945, 44, 250)]
    for x, y, size, turn in blossoms:
        paint_blossom(cv, x, y, size, turn, rng)
    for x, y, size, turn in ((205, 770, 30, -40), (960, 610, 28, 60), (900, 868, 26, 110), (1180, 520, 28, 50)):
        paint_bud(cv, x, y, size, turn)
    for x, y, size, turn in ((330, 985, 62, -60), (560, 870, 56, 150), (1100, 570, 60, 75), (180, 1055, 58, 215)):
        paint_leaf(cv, x, y, size, turn)


def paint_bird(cv):
    """새. 머리가 왼쪽 위, 꼬리가 오른쪽 아래. BIRD 좌표계의 단위는 몸통 길이의 절반쯤이다."""
    tail = g.spline(BIRD([(0.5, 0.02), (1.38, 0.5), (1.5, 0.72), (1.28, 0.74), (0.42, 0.36)]), closed=True,
                    corners=(2, 3))
    wash(cv, tail, BACK, 0.9, soft=2.0, rough=3.0, cover=True)
    for offset in (0.0, 0.1, 0.2):
        cv.stroke(g.spline(BIRD([(0.55, 0.12 + offset), (1.0, 0.4 + offset * 0.6), (1.4, 0.66 + offset * 0.2)]),
                           closed=False), BACK_DEEP, width=2.2, taper=(0.4, 1, 0.3), opacity=0.7)

    body_outline = g.spline(BIRD([(-0.62, -0.18), (-0.3, -0.5), (0.2, -0.46), (0.62, -0.1), (0.72, 0.22),
                                  (0.4, 0.5), (-0.1, 0.62), (-0.52, 0.42), (-0.7, 0.1)]), closed=True)
    head_outline = g.ellipse(*BIRD.point(-0.5, -0.5), BIRD.length(0.36), BIRD.length(0.34))
    silhouette = cv.shape(body_outline) | cv.shape(head_outline)

    # 밑칠: 배는 종이 흰색을 남기고 그늘만 옅게 넣는다.
    cv.fill(silhouette, "#ffffff")
    belly_shadow = cv.form_shadow(silhouette, LIGHT, 0.4, soft=0.35)
    cv.fill(belly_shadow, BELLY_SHADE, opacity=0.75, blend=Blend.MULTIPLY)

    # 가슴과 얼굴의 주황. 아래쪽 경계를 크게 흐려 젖은 종이에 번진 듯 배 쪽으로 풀어진다.
    breast = cv.shape(g.spline(BIRD([(-0.62, -0.82), (-0.34, -0.62), (-0.3, -0.3), (-0.14, 0.08), (-0.3, 0.38),
                                     (-0.62, 0.34), (-0.86, 0.0), (-0.9, -0.5)]), closed=True),
                      soft=BIRD.length(0.07))
    cv.fill(breast, BREAST, opacity=0.95, clip=silhouette, blend=Blend.MULTIPLY)
    cv.fill(cv.mottle(breast, 40, 0.45, 0.2), BREAST_DEEP, opacity=0.6, clip=silhouette, blend=Blend.MULTIPLY)

    # 등과 정수리의 갈색. 주황과 만나는 곳은 서로 스민다.
    back = cv.shape(g.spline(BIRD([(-0.66, -0.9), (-0.2, -0.95), (0.3, -0.6), (0.8, -0.1), (0.8, 0.3),
                                   (0.3, 0.12), (-0.1, -0.2), (-0.26, -0.56), (-0.46, -0.74)]), closed=True),
                    soft=BIRD.length(0.05))
    cv.fill(back, BACK, opacity=0.9, clip=silhouette, blend=Blend.MULTIPLY)

    wing_outline = g.spline(BIRD([(-0.18, -0.22), (0.3, -0.3), (0.74, 0.0), (1.0, 0.4), (0.5, 0.34),
                                  (0.0, 0.2)]), closed=True, corners=(3,))
    wing = wash(cv, wing_outline, BACK, 0.85, soft=2.0, rough=3.0, cover=True)
    cv.fill(cv.form_shadow(wing, LIGHT, 0.5, soft=0.3), BACK_DEEP, opacity=0.7, blend=Blend.MULTIPLY)
    for start, end in (((0.0, -0.04), (0.84, 0.3)), ((0.04, 0.08), (0.72, 0.32)), ((0.24, -0.18), (0.9, 0.22))):
        middle = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0 - 0.06)
        cv.stroke(g.spline(BIRD([start, middle, end]), closed=False), BACK_DEEP, width=2.4, taper=(0.3, 1, 0.2),
                  opacity=0.75, clip=wing)

    # 마른 붓 세부: 눈, 부리, 다리. 가장 어둡고 또렷한 부분이 시선을 모은다.
    cv.fill(cv.shape(g.spline(BIRD([(-0.82, -0.6), (-1.1, -0.48), (-0.82, -0.42)]), closed=True,
                              corners=(0, 1, 2))), INK, opacity=0.9)
    eye = BIRD.point(-0.6, -0.58)
    cv.fill(cv.shape(g.ellipse(*eye, BIRD.length(0.06))), INK)
    cv.fill(cv.shape(g.ellipse(eye[0] - BIRD.length(0.02), eye[1] - BIRD.length(0.022), BIRD.length(0.018))),
            "#ffffff")
    for x, foot in ((-0.1, 0.97), (0.16, 0.85)):
        cv.stroke(g.spline(BIRD([(x, 0.56), (x + 0.04, 0.75), (x - 0.02, foot)]), closed=False), INK, width=5.0,
                  taper=(1, 0.8, 0.8), opacity=0.85)
        for toe in (-0.16, -0.04, 0.1):
            cv.stroke(BIRD([(x - 0.02, foot), (x + toe, foot + 0.09)]), INK, width=3.6, taper=(1, 0.4),
                      opacity=0.85)


def main(out_dir="out", scale=1.0, seed=5):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    paint_background(cv, rng)
    paint_branch(cv)
    paint_flowers(cv, rng)
    paint_bird(cv)
    io.save(cv.guide_image(), out_dir / "watercolor_1_underpainting_guide.png")
    image = watercolor.render(cv)
    return io.save(image, out_dir / "watercolor_robin.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
