"""유화 예제(두머 분위기): 도시 끝 설원을 가로질러 멀어지는 송전탑 줄, 지평선의 단지와 굴뚝 증기(풍경화 파노라마).

송전탑은 1점 투시로 깊이를 정해 화면 왼쪽 앞에서 오른쪽 지평선으로 작아지며 늘어선다.
흐린 하늘 뒤의 창백한 해와 증기만 조금 데워지고 나머지는 회청색 겨울빛이다. 밟힌 길 위의 작은 사람 하나가 크기를 알려 준다.
분위기 값은 references/mood-doomer.md.
공정: 흐린 하늘과 해 무리 → 지평선의 단지 실루엣, 굴뚝, 증기 → 설원과 먼 덤불 줄 → 밟힌 길 → 송전탑(먼 것부터)과 전선 →
까마귀 → 걷는 사람 → 앞쪽 마른 풀 → 유화 패스 → 색 보정.
실행: python oil_doomer_pylons.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Perspective, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import oil  # noqa: E402

WIDTH, HEIGHT = 2000, 1100
HORIZON_Y = 650.0
VIEW = Perspective((1000.0, HORIZON_Y), eye_height=5.0, focal=900.0)   # 철둑 위에 선 눈높이
PYLON_DEPTHS = (26.0, 48.0, 84.0, 145.0, 250.0, 430.0)
PYLON_HEIGHT = 26.0
# 송전탑 줄: x = PYLON_LINE[0] + PYLON_LINE[1] * z. 화면 왼쪽 앞에서 지평선의 굴뚝 쪽(x 1400)으로 모인다.
PYLON_LINE = (-27.5, 0.444)
SUN = (1330.0, 430.0)
CHIMNEYS = ((1480.0, 430.0), (1600.0, 470.0))   # (x, 꼭대기 y). 지평선 위로 선 먼 굴뚝
WALKER = (-2.6, 42.0)                           # 길 위를 걷는 사람의 장면 (x, z)
CROWS = 9

# 팔레트: 흐린 회청색 하늘과 눈이 지배색. 해 무리와 증기 아랫면만 옅은 살구색이고 철탑과 까마귀가 가장 어둡다.
SKY_TOP, SKY_MID, SKY_LOW, SUN_HAZE, SUN_DISC = "#4f5664", "#7c8090", "#ada39e", "#d9b89a", "#f3e2c8"
CLOUD_DARK = "#454b58"
CITY, CITY_FAR, CHIMNEY_BAND = "#6a7080", "#858a98", "#9a6a62"
STEAM, STEAM_LIT = "#c9c8ce", "#ead2bc"
SNOW_FAR, SNOW_NEAR, SNOW_SHADE = "#a8afbb", "#d6dbe2", "#8e97a6"
SCRUB, PATH, GRASS = "#4a4a50", "#7d8697", "#7a6650"
STEEL, WIRE, CROW = "#23272e", "#2c3038", "#15171b"


def pylon_base(z):
    return PYLON_LINE[0] + PYLON_LINE[1] * z, z


# ---------- 하늘과 원경 ----------

def paint_sky(cv, rng):
    sky = cv.shape(g.rect(0, 0, WIDTH, HORIZON_Y + 10))
    cv.direct(sky, angle=-4)
    cv.fill(sky, Linear([(0.0, SKY_TOP), (0.55, SKY_MID), (1.0, SKY_LOW)], (0, 0), (0, HORIZON_Y)))
    cv.fill(cv.shape(g.ellipse(SUN[0], SUN[1], 520, 260), soft=240), SUN_HAZE, opacity=0.55, blend=Blend.SCREEN)
    cv.fill(cv.shape(g.ellipse(SUN[0], SUN[1], 46, 46), soft=10), SUN_DISC, opacity=0.7)
    # 층구름의 짙은 띠: 길고 얇게 겹친다.
    for _ in range(9):
        x, y = rng.uniform(-200, WIDTH), rng.uniform(40, HORIZON_Y * 0.6)
        cv.fill(cv.shape(g.ellipse(x, y, rng.uniform(300, 700), rng.uniform(18, 40)), soft=30), CLOUD_DARK,
                opacity=rng.uniform(0.25, 0.5))


def paint_city(cv, rng):
    """지평선 위의 낮은 단지 실루엣 두 겹. 먼 겹은 하늘빛에 거의 묻힌다."""
    for color, height_range, gap in ((CITY_FAR, (10.0, 30.0), (10.0, 40.0)), (CITY, (6.0, 22.0), (30.0, 90.0))):
        x = 900.0
        while x < WIDTH + 40:
            width, height = rng.uniform(30.0, 90.0), rng.uniform(*height_range)
            cv.fill(cv.shape(g.rect(x, HORIZON_Y - height, width, height + 4)), color)
            x += width + rng.uniform(*gap)
    for x, top in CHIMNEYS:
        body = cv.shape(g.polygon([(x - 9, HORIZON_Y), (x - 5, top), (x + 5, top), (x + 9, HORIZON_Y)]))
        cv.fill(body, CITY)
        for index in range(0, 8, 2):
            y0 = top + (HORIZON_Y - top) * index / 8
            cv.fill(cv.shape(g.rect(x - 10, y0, 20, (HORIZON_Y - top) / 8)), CHIMNEY_BAND, opacity=0.6, clip=body)
        for index in range(12):
            t = index / 11.0
            puff = cv.shape(g.blob(x - 360 * t, top - 20 - 130 * t ** 0.6, 16 + 80 * t, 0.3, 8, rng), soft=6 + 14 * t)
            cv.direct(puff, angle=-10)
            cv.fill(puff, STEAM, opacity=0.95 - 0.4 * t)
            cv.fill(cv.form_light(puff, (0.4, 0.9), 0.3, soft=0.5), STEAM_LIT, opacity=0.45)


# ---------- 설원 ----------

def paint_field(cv, rng):
    field = cv.shape(g.rect(0, HORIZON_Y, WIDTH, HEIGHT - HORIZON_Y))
    cv.direct(field, angle=1)
    cv.fill(field, Linear([SNOW_FAR, SNOW_NEAR], (0, HORIZON_Y), (0, HEIGHT)))
    # 땅의 완만한 굴곡이 남긴 그늘 띠. 가까울수록 굵다.
    for _ in range(10):
        z = rng.uniform(15.0, 300.0)
        y = VIEW.project(0.0, 0.0, z)[1]
        width = rng.uniform(300, 1200)
        cv.fill(cv.shape(g.ellipse(rng.uniform(0, WIDTH), y, width, 900.0 / z * 1.2), soft=900.0 / z),
                SNOW_SHADE, opacity=0.35)
    # 먼 덤불 줄: 지평선 조금 아래의 어두운 점선.
    for x in np.arange(0.0, 1100.0, 7.0):
        if rng.random() < 0.6:
            height = rng.uniform(3.0, 9.0)
            cv.fill(cv.shape(g.ellipse(x, HORIZON_Y + 12 - height / 2, 4.0, height)), SCRUB, opacity=0.7)


def paint_path(cv):
    """화면 아래에서 송전탑 줄을 따라 지평선 쪽으로 가는 밟힌 길."""
    points = [(-2.0, 8.0), (-2.4, 20.0), (-2.6, 42.0), (-1.0, 100.0), (4.0, 220.0)]
    path = g.spline(VIEW.path([(x, 0.0, z) for x, z in points]), closed=False)
    track = cv.shape(*g.ribbon(path, (150.0, 70.0, 30.0, 10.0, 3.0)))
    cv.direct(track, angle=-70)
    cv.fill(track, PATH, opacity=0.8)


# ---------- 송전탑 ----------

def pylon_parts(x, z):
    """송전탑 1기의 장면 좌표 부품: 다리 2개, 엇갈린 버팀, 팔 2단, 애자 끝점. 반환은 (선 목록, 팔 끝 목록)."""
    h = PYLON_HEIGHT
    half_base, half_waist, half_top = h * 0.16, h * 0.05, h * 0.035
    legs = [[(x - half_base, 0.0, z), (x - half_waist, h * 0.68, z), (x - half_top, h, z)],
            [(x + half_base, 0.0, z), (x + half_waist, h * 0.68, z), (x + half_top, h, z)]]
    lines = [(leg, 1.0) for leg in legs]
    levels = np.linspace(0.0, h * 0.68, 7)
    for low, high in zip(levels[:-1], levels[1:]):
        def half(y):
            return half_base + (half_waist - half_base) * y / (h * 0.68)
        lines.append(([(x - half(low), low, z), (x + half(high), high, z)], 0.5))
        lines.append(([(x + half(low), low, z), (x - half(high), high, z)], 0.5))
        lines.append(([(x - half(high), high, z), (x + half(high), high, z)], 0.45))
    tips = []
    for level, reach in ((h * 0.74, h * 0.34), (h * 0.88, h * 0.26)):
        lines.append(([(x - reach, level, z), (x + reach, level, z)], 0.8))
        lines.append(([(x - reach, level, z), (x - half_waist, level + h * 0.05, z)], 0.4))
        lines.append(([(x + reach, level, z), (x + half_waist, level + h * 0.05, z)], 0.4))
        for end in (x - reach * 0.95, x + reach * 0.95):
            lines.append(([(end, level, z), (end, level - h * 0.05, z)], 0.35))
            tips.append((end, level - h * 0.05, z))
    return lines, tips


def paint_pylons(cv):
    """먼 탑부터 칠하고 이웃한 탑의 같은 애자 끝을 처진 전선으로 잇는다."""
    previous = None
    for z in reversed(PYLON_DEPTHS):
        x, _ = pylon_base(z)
        lines, tips = pylon_parts(x, z)
        thickness = VIEW.scale_at(z) * 0.22
        for points, weight in lines:
            cv.stroke(VIEW.path(points), STEEL, width=max(thickness * weight, 0.8))
        if previous is not None:
            for near, far in zip(tips, previous):
                a, b = np.array(VIEW.project(*near)), np.array(VIEW.project(*far))
                sag = np.linalg.norm(b - a) * 0.06
                middle = (a + b) / 2 + np.array([0.0, sag])
                cv.stroke(g.spline([a, middle, b], closed=False), WIRE, width=max(thickness * 0.12, 0.8),
                          opacity=0.9)
        previous = tips
    # 가장 가까운 탑에서 화면 왼쪽 밖으로 나가는 전선.
    for tip in previous:
        a = np.array(VIEW.project(*tip))
        b = a + np.array([-700.0, 160.0])
        cv.stroke(g.spline([a, (a + b) / 2 + np.array([0.0, 60.0]), b], closed=False), WIRE, width=2.2)
    return previous


def paint_crows(cv, rng, perch_tips):
    """흐린 하늘을 나는 까마귀 몇 마리와 가까운 전선에 앉은 두 마리."""
    for _ in range(CROWS):
        x, y = rng.uniform(300, 1200), rng.uniform(120, 420)
        span = rng.uniform(10, 22)
        cv.stroke(g.spline([(x - span, y - span * 0.3), (x - span * 0.4, y - span * 0.1), (x, y + span * 0.15),
                            (x + span * 0.4, y - span * 0.1), (x + span, y - span * 0.35)], closed=False),
                  CROW, width=span * 0.18, taper=(0.2, 1.0, 1.0, 1.0, 0.2))
    for tip in perch_tips[:2]:
        a = np.array(VIEW.project(*tip)) + np.array([-180.0, 54.0])
        cv.fill(cv.shape(g.ellipse(a[0], a[1] - 9, 7, 10)), CROW)
        cv.fill(cv.shape(g.ellipse(a[0] + 4, a[1] - 20, 4.5, 4.5)), CROW)


def paint_walker(cv):
    """길 위의 작은 사람: 외투 실루엣과 머리, 발밑 그림자. 풍경의 크기를 알려 준다."""
    x, z = WALKER
    foot = VIEW.project(x, 0.0, z)
    scale = VIEW.scale_at(z)
    cv.fill(cv.shape(g.ellipse(foot[0] + scale * 0.3, foot[1], scale * 0.5, scale * 0.08)), SNOW_SHADE)
    body = g.polygon([(foot[0] - scale * 0.2, foot[1]), (foot[0] - scale * 0.24, foot[1] - scale * 1.4),
                      (foot[0] + scale * 0.24, foot[1] - scale * 1.4), (foot[0] + scale * 0.2, foot[1])])
    cv.fill(cv.shape(body), CROW)
    cv.fill(cv.shape(g.ellipse(foot[0], foot[1] - scale * 1.55, scale * 0.13, scale * 0.15)), CROW)


def paint_grass(cv, rng):
    """눈 위로 삐져나온 앞쪽 마른 풀. 화면 아래 가장자리를 눌러 깊이의 앞을 만든다."""
    for _ in range(220):
        x, y = rng.uniform(-20, WIDTH + 20), rng.uniform(HEIGHT - 120, HEIGHT + 10)
        length = rng.uniform(20, 70)
        lean = rng.uniform(-0.4, 0.4)
        cv.stroke([(x, y), (x + lean * length, y - length)], GRASS, width=rng.uniform(1.5, 3.0), taper=(1.0, 0.1),
                  opacity=0.85)


def main(out_dir="out", scale=1.0, seed=157):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv, rng)
    paint_city(cv, rng)
    paint_field(cv, rng)
    paint_path(cv)
    tips = paint_pylons(cv)
    paint_crows(cv, rng, tips)
    paint_walker(cv)
    paint_grass(cv, rng)
    io.save(cv.guide_image(), out_dir / "pylons_1_underpainting_guide.png")
    # 철탑과 전선은 가는 선이라 큰 붓에 뭉개진다. 가장 작은 붓을 탑 줄 둘레에 모은다.
    near_x, _ = pylon_base(PYLON_DEPTHS[0])
    near = VIEW.project(near_x, 0.0, PYLON_DEPTHS[0])
    detail = cv.shape(g.polygon([(near[0] - 420, HEIGHT), (near[0] - 420, 0), (1500, HORIZON_Y - 120),
                                 (1500, HORIZON_Y + 20)]), soft=40)
    image = oil.render(cv, brush_radii=(24.0, 11.0, 5.0, 2.2), detail=detail, relief=0.45, color_jitter=0.035)
    image = post.grade(image, shadows="#0e1a26", highlights="#ffd9a0", amount=0.1, contrast=1.05, saturation=0.78)
    return io.save(post.vignette(image, strength=0.3), out_dir / "oil_doomer_pylons.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
