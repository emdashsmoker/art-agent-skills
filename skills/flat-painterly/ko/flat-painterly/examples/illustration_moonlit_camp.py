"""일러스트풍 예제: 달밤의 호숫가 야영.

공정: 색면 설계(제한 팔레트) → 뒤에서 앞으로 평면 도형 쌓기 → 점묘 그라데이션으로 명암 → 인쇄 질감 패스.
윤곽선 없이 색면의 명도 차이만으로 형태를 구분한다. 부드러운 명암은 grain 점묘로만 표현한다.
실행: python illustration_moonlit_camp.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, io  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import illustration  # noqa: E402

WIDTH, HEIGHT = 1200, 1600
MOON_CENTER, MOON_RADIUS = (770, 430), 175

# 팔레트: 남색 계열 6단계가 화면의 9할을 차지한다. 크림색 달과 주황 텐트만 난색이라 시선이 그 둘을 오간다.
SKY_BANDS = ["#0e1838", "#142352", "#1b3068", "#23417e", "#2c5590"]
MOON, MOON_SHADE = "#fcecc9", "#e2bf8e"
STAR = "#f6e7c4"
PEAK_FAR, PEAK_MID, PEAK_NEAR = "#3d6aa0", "#2a4c84", "#1c3566"
SNOW, SNOW_SHADE = "#eef3f7", "#9db8d8"
FOREST_FAR, FOREST_NEAR = "#173258", "#0d2040"
LAKE, LAKE_DEEP = "#2a5d92", "#173a6a"
GROUND, GROUND_LIT = "#08152e", "#14284c"
TENT, TENT_SHADE, TENT_DOOR = "#f59340", "#c8541f", "#ffd98a"
FIRE_GLOW = "#ffb04a"


def stipple(cv, shape, color, opacity=1.0, clip=None, blend=Blend.NORMAL):
    """점묘 명암. 부드럽게 흐린 형태를 입자로 바꿔 찍으면 색 수를 늘리지 않고 계조가 생긴다."""
    cv.fill(shape, color, opacity=opacity, clip=clip, grain=1.0, blend=blend)


def paint_sky(cv, rng):
    band_height = 1000 / len(SKY_BANDS)
    for index, band_color in enumerate(SKY_BANDS):
        top = index * band_height
        cv.fill(cv.shape(g.rect(0, top, WIDTH, band_height + 2)), band_color)
        if index > 0:
            # 띠 경계를 점묘로 풀어 계단식 색면이 거칠게 섞이게 한다.
            stipple(cv, cv.shape(g.rect(0, top - 50, WIDTH, 100), soft=26), band_color, clip=None)
            cv.fill(cv.shape(g.rect(0, top + 48, WIDTH, band_height)), band_color)
    for radius, opacity in ((330, 0.10), (255, 0.14)):
        cv.fill(cv.shape(g.ellipse(*MOON_CENTER, radius)), MOON, opacity=opacity)
    for _ in range(90):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, 820) ** 1.0
        if np.hypot(x - MOON_CENTER[0], y - MOON_CENTER[1]) < MOON_RADIUS + 40:
            continue
        cv.fill(cv.shape(g.ellipse(x, y, rng.uniform(1.2, 3.2))), STAR, opacity=rng.uniform(0.5, 1.0))
    for x, y, size in ((210, 190, 16), (1010, 120, 13), (420, 420, 11), (1090, 640, 12), (130, 560, 10)):
        sparkle = g.spline([(x, y - size), (x + size * 0.18, y - size * 0.18), (x + size, y),
                            (x + size * 0.18, y + size * 0.18), (x, y + size), (x - size * 0.18, y + size * 0.18),
                            (x - size, y), (x - size * 0.18, y - size * 0.18)], closed=True,
                           corners=(0, 2, 4, 6))
        cv.fill(cv.shape(sparkle), STAR)


def paint_moon(cv, rng):
    moon = cv.shape(g.ellipse(*MOON_CENTER, MOON_RADIUS))
    cv.fill(moon, MOON)
    stipple(cv, cv.form_shadow(moon, (-0.7, -0.7), amount=0.5, soft=0.5), MOON_SHADE, clip=moon)
    for dx, dy, radius in ((-60, -50, 34), (40, 30, 46), (-30, 70, 22), (80, -70, 20), (-95, 25, 16)):
        crater = cv.shape(g.ellipse(MOON_CENTER[0] + dx, MOON_CENTER[1] + dy, radius, radius * 0.9))
        cv.fill(crater, MOON_SHADE, opacity=0.55, clip=moon)


def paint_peak(cv, outline, body, snow_line=None, light_side=None):
    """산 1개. 오른쪽 위 달빛을 받는 면과 그늘면을 점묘로 나눈다."""
    peak = cv.shape(g.polygon(outline))
    cv.fill(peak, body)
    if light_side is not None:
        stipple(cv, cv.shape(g.polygon(light_side), soft=34), "#6f9bc9", opacity=0.55, clip=peak)
    if snow_line is not None:
        snow = cv.shape(g.polygon(snow_line))
        cv.fill(snow, SNOW, clip=peak)
        shade_outline = np.array(snow_line, np.float64)
        shade_outline[:, 0] -= 46
        stipple(cv, cv.shape(g.polygon(shade_outline), soft=16), SNOW_SHADE, clip=snow & peak)


def paint_mountains(cv):
    paint_peak(cv, [(-20, 1010), (-20, 800), (120, 700), (230, 760), (330, 660), (470, 800), (600, 1010)], PEAK_FAR)
    paint_peak(cv, [(700, 1010), (860, 760), (960, 690), (1040, 760), (1130, 720), (1220, 800), (1220, 1010)],
               PEAK_FAR)
    main_peak = [(180, 1030), (420, 700), (520, 560), (580, 470), (640, 540), (700, 520), (800, 700),
                 (900, 820), (1040, 1030)]
    snow = [(440, 676), (520, 560), (580, 470), (640, 540), (700, 520), (772, 650), (720, 700), (676, 640),
            (630, 720), (580, 650), (530, 720), (490, 660)]
    lit = [(580, 470), (640, 540), (700, 520), (800, 700), (900, 820), (1040, 1030), (760, 1030)]
    paint_peak(cv, main_peak, PEAK_MID, snow_line=snow, light_side=lit)
    paint_peak(cv, [(-20, 1040), (-20, 900), (100, 830), (200, 900), (300, 860), (430, 1040)], PEAK_NEAR)
    paint_peak(cv, [(840, 1040), (980, 880), (1060, 920), (1140, 850), (1220, 900), (1220, 1040)], PEAK_NEAR)


def pine_outline(x, base_y, height, tiers=6, lean=0.0):
    """양식화한 침엽수 윤곽. 아래로 갈수록 넓어지는 층을 톱니 모양으로 쌓는다."""
    width = height * 0.36
    left, right = [], []
    for tier in range(tiers):
        top = base_y - height + height * 0.92 * tier / tiers
        bottom = base_y - height + height * 0.92 * (tier + 1) / tiers
        reach = width * (tier + 1) / tiers / 2.0
        inner = reach * 0.45
        shift = lean * (1.0 - tier / tiers)
        right += [(x + shift + (inner if tier else 0.0), top), (x + shift + reach, bottom)]
        left += [(x + shift - (inner if tier else 0.0), top), (x + shift - reach, bottom)]
    trunk = height * 0.025
    return np.array(right + [(x + trunk, base_y - height * 0.08), (x + trunk, base_y), (x - trunk, base_y),
                             (x - trunk, base_y - height * 0.08)] + left[::-1])


def paint_pine(cv, x, base_y, height, body, lit=None):
    tree = cv.shape(pine_outline(x, base_y, height))
    cv.fill(tree, body)
    if lit is not None:
        side = cv.shape(g.rect(x + height * 0.02, base_y - height, height * 0.4, height), soft=height * 0.05)
        stipple(cv, side, lit, opacity=0.8, clip=tree)


def paint_forest(cv, rng):
    for x in np.arange(-10, WIDTH + 40, 46):
        paint_pine(cv, x + rng.uniform(-10, 10), 1060, rng.uniform(90, 150), FOREST_FAR)


def paint_lake(cv, rng):
    lake = cv.shape(g.rect(0, 1050, WIDTH, 360))
    cv.fill(lake, LAKE)
    stipple(cv, cv.shape(g.rect(0, 1180, WIDTH, 200), soft=50), LAKE_DEEP, clip=lake)
    for x in np.arange(-10, WIDTH + 40, 46):
        mirror = pine_outline(x + rng.uniform(-10, 10), 1052, rng.uniform(50, 80))
        mirror[:, 1] = 2 * 1052 - mirror[:, 1]
        cv.fill(cv.shape(mirror), FOREST_FAR, opacity=0.55, clip=lake)
    for index in range(26):
        y = 1066 + index * 9.0
        half = 22 + index * 5.0 + rng.uniform(-18, 18)
        x = MOON_CENTER[0] + rng.uniform(-26, 26)
        cv.fill(cv.shape(g.rect(x - half, y, half * 2, 3.4, 1.7)), MOON, opacity=0.9 - index * 0.02, clip=lake)


def paint_foreground(cv):
    shore = g.spline([(-20, 1330), (200, 1268), (470, 1290), (700, 1340), (960, 1300), (1220, 1250),
                      (1220, 1620), (-20, 1620)], closed=True, corners=(5, 6, 7, 0))
    ground = cv.shape(shore)
    cv.fill(ground, GROUND)
    stipple(cv, cv.shape(g.ellipse(430, 1300, 330, 90), soft=40), GROUND_LIT, clip=ground)

    # 모닥불 빛이 땅과 텐트에 번진다. 난색 점묘가 남색 화면에서 유일한 온기다.
    stipple(cv, cv.shape(g.ellipse(560, 1395, 210, 70), soft=46), FIRE_GLOW, opacity=0.9, clip=ground)

    tent = g.Frame(origin=(360, 1400), unit=150)
    body = cv.shape(g.polygon(tent([(-1.0, 0.0), (0.0, -1.15), (1.0, 0.0)])))
    cv.fill(body, TENT)
    cv.fill(cv.shape(g.polygon(tent([(-1.0, 0.0), (0.0, -1.15), (-0.18, 0.0)]))), TENT_SHADE)
    stipple(cv, cv.shape(g.polygon(tent([(0.0, -1.15), (1.0, 0.0), (0.5, 0.0)])), soft=14), TENT_SHADE,
            opacity=0.7, clip=body)
    cv.fill(cv.shape(g.polygon(tent([(-0.18, 0.0), (0.0, -0.72), (0.3, 0.0)]))), TENT_DOOR)
    cv.stroke(tent([(0.0, -1.15), (0.0, -1.3)]), TENT_SHADE, width=5)

    fire = g.Frame(origin=(640, 1408), unit=34)
    for log_angle in (-16, 16):
        cv.fill(cv.shape(g.transform(g.rect(-1.5, -0.2, 3.0, 0.4, 0.2) * fire.unit, rotate=log_angle)
                         + fire.origin), "#3a2418")
    cv.fill(cv.shape(g.spline(fire([(0.0, -2.3), (0.55, -1.2), (0.85, -0.4), (0.0, 0.0), (-0.85, -0.4),
                                    (-0.4, -1.1)]), closed=True, corners=(0,))), TENT)
    cv.fill(cv.shape(g.spline(fire([(0.05, -1.4), (0.4, -0.6), (0.0, -0.05), (-0.4, -0.5)]), closed=True,
                              corners=(0,))), TENT_DOOR)

    paint_pine(cv, 95, 1600, 1010, FOREST_NEAR, lit=GROUND_LIT)
    paint_pine(cv, -20, 1620, 760, GROUND)
    paint_pine(cv, 1090, 1600, 760, FOREST_NEAR, lit=GROUND_LIT)
    paint_pine(cv, 1190, 1620, 560, GROUND)


def main(out_dir="out", scale=1.0, seed=3):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    paint_sky(cv, rng)
    paint_moon(cv, rng)
    paint_mountains(cv)
    paint_forest(cv, rng)
    paint_lake(cv, rng)
    paint_foreground(cv)
    io.save(cv.guide_image(), out_dir / "illustration_1_flat_guide.png")
    image = illustration.render(cv)
    return io.save(image, out_dir / "illustration_moonlit_camp.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
