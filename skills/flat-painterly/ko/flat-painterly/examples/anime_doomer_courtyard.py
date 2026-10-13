"""애니메풍 배경 예제(두머 분위기): 겨울 해 질 녘 패널 아파트 단지 안마당의 설정샷(인물 없는 와이드 배경).

세 동의 9층과 5층 패널 아파트를 solids 카메라로 2점 투시해 세우고 면 위 좌표로 창, 발코니, 층 이음매를 붙인다.
안마당에는 아치형 놀이 기구 철골, 그네 틀, 차고 줄, 자작나무, 막 켜진 나트륨 가로등 하나, 화면 위를 가로지르는 트롤리 전선.
해는 맞은편 동 뒤로 졌고 카메라를 향한 벽은 모두 그늘이다. 따뜻한 색은 창과 가로등, 지평선의 남은 노을뿐이다.
분위기 값은 references/mood-doomer.md.
공정: 하늘 → 먼 굴뚝과 증기 → 동(먼 것부터, 벽, 이음매, 창, 발코니) → 차고 → 눈 마당과 발자국 길 → 놀이 기구 →
가로등 빛 웅덩이 → 자작나무 → 가로등 → 전선 → 촬영 마감 → 색 보정.
실행: python anime_doomer_courtyard.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1920, 1080
CAMERA = s3.Camera(eye=(0.0, 1.7, 0.0), target=(6.0, 13.0, 100.0), focal=1000.0, center=(960.0, 600.0))
DUSK_LIGHT = (0.3, 0.5, 0.8)         # 맞은편 동 뒤로 진 해. 카메라를 향한 벽은 그늘이 된다
FLOOR_HEIGHT_M = 2.8
# 동: (가운데 x, z, 폭 x, 깊이 z, 층수, 창 칸 수 {면 이름: 칸})
BLOCKS = (
    (-26.0, 75.0, 12.0, 100.0, 9, {"right": 34, "front": 4}),
    (18.0, 170.0, 120.0, 12.0, 9, {"front": 42}),
    (48.0, 62.0, 12.0, 56.0, 5, {"left": 20, "front": 4}),
)
GARAGES = (14.0, 74.0, 8)            # 차고 줄의 시작 x, z, 칸 수
GARAGE_SIZE = (3.4, 2.4, 6.0)
LAMP_AT, LAMP_HEIGHT = (-3.5, 17.0), 7.0
BIRCHES = ((-9.5, 16.0, 8.0), (-14.0, 30.0, 9.0), (16.0, 44.0, 10.0), (27.0, 36.0, 9.0))   # (x, z, 높이)
CAR_AT, CAR_YAW = (7.5, 10.5), 12.0   # 눈 덮인 채 세워 둔 승용차
# 차 옆모습(미터, x 앞뒤 길이, y 높이)과 옆창. 각진 세단의 보닛, 앞유리, 지붕, 뒷유리, 트렁크.
CAR_PROFILE = ((-2.1, 0.15), (2.1, 0.15), (2.1, 0.8), (1.0, 0.86), (0.45, 1.36), (-0.95, 1.36), (-1.45, 0.88),
               (-2.1, 0.84))
CAR_WINDOW = ((0.9, 0.9), (0.4, 1.3), (-0.9, 1.3), (-1.3, 0.92))
CAR_WIDTH = 1.65
SNOW_FACING, GLASS_FACING = 0.95, 0.3   # 면 법선의 위 성분: 이보다 크면 눈 덮인 면, 그 사이는 유리
BENCH_AT = (-4.6, 9.0)
CHIMNEY = (75.0, 900.0, 140.0)       # 먼 열병합 발전소 굴뚝 (x, z, 높이)

# 팔레트: 회청색 하늘과 콘크리트, 그늘진 눈이 지배색. 난색은 창, 가로등, 지평선 노을 띠뿐이다.
SKY_TOP, SKY_MID, SKY_LOW, AFTERGLOW = "#18202d", "#334052", "#6a6672", "#c08a64"
CLOUD, CLOUD_LIT = "#2a3444", "#8a6a62"
WALL, WALL_SIDE, WALL_TOP, SEAM = "#4a5260", "#3b4250", "#6a7280", "#2a303a"
WINDOW_DARK, WINDOW_WARM, WINDOW_TV, BALCONY = "#232a35", "#f0c070", "#8fb3c9", "#30373f"
GARAGE, GARAGE_DOOR, GARAGE_ROOF = "#4d4a4c", "#3a3436", "#7d838c"
SNOW, SNOW_SHADE, SNOW_PATH = "#8f9aa8", "#6b7685", "#56606e"
METAL, METAL_RED = "#22262c", "#6a3432"
CAR, CAR_GLASS, CAR_SNOW = "#5a6470", "#1c2129", "#b8c0ca"
BENCH = "#3a3532"
BIRCH, BIRCH_MARK, BRANCH = "#c9ccd0", "#22252a", "#2c2a2e"
SODIUM, SODIUM_GLOW, SODIUM_CORE = "#f2a65a", "#ffcf8a", "#fff1d0"
STEAM, STEAM_LIT = "#8a8e9a", "#c8a08a"
INK = "#14171c"


def horizon_y():
    eye = CAMERA.eye
    return CAMERA.project((eye[0], eye[1], eye[2] + 1e5))[1]


# ---------- 하늘 ----------

def paint_sky(cv, rng):
    # 노을 띠는 맞은편 동의 지붕선 바로 위에 둔다. 지평선은 동에 가려 보이지 않는다.
    x, z, _, depth, floors, _ = BLOCKS[1]
    roof = CAMERA.project((x, floors * FLOOR_HEIGHT_M, z - depth / 2))[1]
    cv.fill(cv.full(), Linear([(0.0, SKY_TOP), (0.5, SKY_MID), (0.82, SKY_LOW), (1.0, AFTERGLOW)], (0, 0),
                              (0, roof + 20)))
    horizon = horizon_y()
    for _ in range(6):
        x, y = rng.uniform(0, WIDTH), rng.uniform(60, horizon * 0.6)
        length = rng.uniform(500, 1000)
        cloud = cv.shape(g.spline([(x - length / 2, y), (x - length / 5, y - 18), (x + length / 3, y - 14),
                                   (x + length / 2, y + 4), (x, y + 14)], corners=(0, 3)))
        cv.fill(cloud, CLOUD)
        cv.fill(cv.shape(g.rect(x - length / 2, y + 4, length, 12)), CLOUD_LIT, opacity=0.6, clip=cloud)
    x, z, height = CHIMNEY
    base, top = CAMERA.project((x, 0.0, z)), CAMERA.project((x, height, z))
    half = CAMERA.scale_at((x, 0.0, z)) * 4.0
    cv.fill(cv.shape(g.polygon([(base[0] - half, base[1]), (top[0] - half * 0.6, top[1]), (top[0] + half * 0.6, top[1]),
                                (base[0] + half, base[1])])), "#4a4c58")
    for index in range(10):
        t = index / 9.0
        puff = cv.shape(g.blob(top[0] - 180 * t, top[1] - 14 - 50 * t ** 0.7, 10 + 38 * t, 0.3, 8, rng), soft=6)
        cv.fill(puff, STEAM, opacity=0.6 - 0.35 * t)
        cv.fill(cv.form_light(puff, (0.7, 0.5), 0.3, soft=0.5), STEAM_LIT, opacity=0.3)


# ---------- 동 ----------

def make_block(x, z, width, depth, floors):
    height = floors * FLOOR_HEIGHT_M
    return s3.box((x, height / 2, z), (width, height, depth))


def paint_facade(cv, rng, face, floors, columns):
    """면 1개: 층 이음매, 창(켜진 창 몇 개와 푸른 TV 창), 칸 3개 중 1개의 발코니."""
    for row in range(1, floors):
        cv.stroke(CAMERA.path([face.point(0.0, row / floors), face.point(1.0, row / floors)]), SEAM, width=1.0,
                  opacity=0.6)
    for column in range(columns):
        for row in range(floors):
            u0, v0 = (column + 0.28) / columns, (row + 0.3) / floors
            u1, v1 = (column + 0.72) / columns, (row + 0.75) / floors
            roll = rng.random()
            color = WINDOW_TV if roll < 0.015 else WINDOW_WARM if roll < 0.16 else WINDOW_DARK
            cv.fill(cv.shape(CAMERA.region(face, u0, v0, u1, v1)), color)
            if column % 3 == 1:
                rail = CAMERA.region(face, (column + 0.12) / columns, (row + 0.72) / floors,
                                     (column + 0.88) / columns, (row + 0.98) / floors)
                cv.fill(cv.shape(rail), BALCONY)


def paint_blocks(cv, rng):
    solids = [(make_block(x, z, w, d, floors), floors, columns) for x, z, w, d, floors, columns in BLOCKS]
    ordered = CAMERA.order([solid for solid, _, _ in solids])
    lookup = {id(solid): (floors, columns) for solid, floors, columns in solids}
    paint = {"top": WALL_TOP, "front": WALL, "left": WALL_SIDE, "right": WALL_SIDE, "*": WALL}
    for solid in ordered:
        floors, columns = lookup[id(solid)]
        shapes = s3.draw(cv, CAMERA, solid, paint, DUSK_LIGHT, line=SEAM, width=1.4, ambient=0.75, highlight=0.0)
        for face in CAMERA.visible_faces(solid):
            if face.name in columns:
                paint_facade(cv, rng, face, floors, columns[face.name])
        # 땅에 가까운 벽은 눈의 반사광을 덜 받아 어둡다. 아랫단을 흐린 띠로 눌러 동을 땅에 세운다.
        foot = CAMERA.project(solid.center * np.array([1.0, 0.0, 1.0]))[1]
        cv.fill(cv.shape(g.rect(0, foot - 90, WIDTH, 130), soft=40), SEAM, opacity=0.45, clip=shapes["silhouette"])


def paint_garages(cv):
    """철문이 달린 낮은 차고 줄. 지붕에 눈."""
    x0, z, count = GARAGES
    width, height, depth = GARAGE_SIZE
    for index in range(count):
        cx = x0 + index * width
        solid = s3.box((cx, height / 2, z), (width - 0.05, height, depth))
        shapes = s3.draw(cv, CAMERA, solid, {"top": GARAGE_ROOF, "*": GARAGE}, DUSK_LIGHT, line=SEAM, width=1.0,
                         ambient=0.75, highlight=0.0)
        if "front" in shapes:
            door = CAMERA.region(solid.face("front"), 0.12, 0.2, 0.88, 1.0)
            cv.fill(cv.shape(door), GARAGE_DOOR if index % 3 else METAL_RED)


# ---------- 마당 ----------

def paint_yard(cv, rng):
    horizon = horizon_y()
    ground = cv.shape(g.rect(0, horizon - 2, WIDTH, HEIGHT - horizon + 2))
    cv.fill(ground, Linear([SNOW_SHADE, SNOW], (0, horizon), (0, HEIGHT)))
    # 밟혀 다져진 발자국 길: 가까운 쪽에서 동 입구들로 갈라진다.
    for points in (((-2.0, 3.0), (2.0, 20.0), (-14.0, 50.0), (-20.0, 80.0)),
                   ((2.0, 20.0), (14.0, 60.0), (20.0, 100.0), (22.0, 150.0)),
                   ((2.0, 20.0), (30.0, 40.0), (42.0, 50.0))):
        path = CAMERA.path([(x, 0.0, z) for x, z in points])
        width = CAMERA.scale_at((points[0][0], 0.0, points[0][1])) * 0.9
        cv.stroke(g.spline(path, closed=False), SNOW_PATH, width=width, taper=(1.0, 0.1), opacity=0.6)
    for _ in range(40):
        x, z = rng.uniform(-30.0, 60.0), rng.uniform(4.0, 120.0)
        spot = CAMERA.project((x, 0.0, z))
        radius = CAMERA.scale_at((x, 0.0, z)) * rng.uniform(0.6, 1.6)
        cv.fill(cv.shape(g.ellipse(spot[0], spot[1], radius * 2.0, radius * 0.4), soft=radius * 0.3), SNOW, opacity=0.5)


def paint_playground(cv):
    """아치형 정글짐과 그네 틀: 철관을 3차원 점열로 투영한 굵은 선."""
    cx, cz = 8.0, 34.0
    for offset in np.linspace(-2.0, 2.0, 5):
        arc = [(cx + offset, 2.2 * np.sin(t), cz + 2.2 * np.cos(t)) for t in np.linspace(-np.pi / 2, np.pi / 2, 24)]
        cv.stroke(CAMERA.path(arc), METAL_RED, width=CAMERA.scale_at((cx, 0.0, cz)) * 0.08)
    for angle in np.linspace(-np.pi / 2 + 0.3, np.pi / 2 - 0.3, 5):
        rung = [(cx - 2.0, 2.2 * np.sin(angle + np.pi / 2), cz + 2.2 * np.cos(angle + np.pi / 2)),
                (cx + 2.0, 2.2 * np.sin(angle + np.pi / 2), cz + 2.2 * np.cos(angle + np.pi / 2))]
        cv.stroke(CAMERA.path(rung), METAL, width=CAMERA.scale_at((cx, 0.0, cz)) * 0.06)
    sx, sz = -1.0, 22.0
    for x in (sx - 1.6, sx + 1.6):
        for dz in (-0.9, 0.9):
            cv.stroke(CAMERA.path([(x, 0.0, sz + dz), (x, 2.5, sz)]), METAL, width=CAMERA.scale_at((x, 0.0, sz)) * 0.08)
    cv.stroke(CAMERA.path([(sx - 1.6, 2.5, sz), (sx + 1.6, 2.5, sz)]), METAL, width=CAMERA.scale_at((sx, 0.0, sz)) * 0.08)
    for x in (sx - 0.4, sx + 0.4):
        cv.stroke(CAMERA.path([(x, 2.5, sz), (x, 0.5, sz)]), METAL, width=1.2)
    cv.stroke(CAMERA.path([(sx - 0.45, 0.5, sz), (sx + 0.45, 0.5, sz)]), METAL, width=4.0)


def car_solid(profile, width):
    """옆모습 윤곽(x 길이 방향, y 위)을 차 폭만큼 밀어낸 입체를 세워 둔 자리와 방향으로 옮긴다."""
    x, z = CAR_AT
    solid = s3.prism(profile, width).moved((0.0, 0.0, -width / 2.0))
    return solid.rotated(yaw=90.0 + CAR_YAW).moved((x, 0.0, z))


def paint_car(cv):
    """눈 덮인 채 세워 둔 각진 승용차: 옆모습 윤곽을 밀어낸 차체, 옆창, 위를 향한 면의 눈, 차 밑 그림자.

    바퀴는 눈에 묻혀 보이지 않는 것으로 두고 차체 아랫단을 땅에 붙인다. 틈을 두면 차가 떠 보인다.
    """
    x, z = CAR_AT
    scale = CAMERA.scale_at((x, 0.0, z))
    center = CAMERA.project((x, 0.0, z))
    cv.fill(cv.shape(g.ellipse(center[0], center[1], scale * 2.6, scale * 0.6), soft=scale * 0.3), INK, opacity=0.5)
    body = car_solid(CAR_PROFILE, CAR_WIDTH)
    s3.draw(cv, CAMERA, body, CAR, DUSK_LIGHT, line=INK, width=1.2, ambient=0.7, highlight=0.0)
    # 위를 향한 보닛, 지붕, 트렁크에는 눈, 비스듬한 앞유리와 뒷유리는 어두운 유리.
    for face in CAMERA.visible_faces(body):
        if face.normal[1] > SNOW_FACING:
            cv.fill(cv.shape(CAMERA.path(face.vertices)), CAR_SNOW)
        elif face.normal[1] > GLASS_FACING:
            cv.fill(cv.shape(CAMERA.path(face.vertices)), CAR_GLASS)
    glass = car_solid(CAR_WINDOW, CAR_WIDTH + 0.04)
    s3.draw(cv, CAMERA, glass, {"front": CAR_GLASS, "back": CAR_GLASS}, DUSK_LIGHT, ambient=1.0, highlight=0.0)
    for center_x in (-1.35, 1.35):
        wheel = [(center_x + 0.34 * np.cos(t), 0.3 + 0.34 * np.sin(t)) for t in np.linspace(0.0, np.pi, 12)]
        s3.draw(cv, CAMERA, car_solid(wheel, CAR_WIDTH + 0.06), {"front": INK, "back": INK}, DUSK_LIGHT,
                ambient=1.0, highlight=0.0)


def paint_bench(cv):
    """눈 쌓인 나무 의자: 등받이 판 2장과 앉는 판 2장, 다리."""
    x, z = BENCH_AT
    for dx in (-0.8, 0.8):
        cv.stroke(CAMERA.path([(x + dx, 0.0, z - 0.1), (x + dx, 0.45, z - 0.1)]), BENCH,
                  width=CAMERA.scale_at((x, 0.0, z)) * 0.1)
        cv.stroke(CAMERA.path([(x + dx, 0.0, z + 0.25), (x + dx, 0.95, z + 0.25)]), BENCH,
                  width=CAMERA.scale_at((x, 0.0, z)) * 0.1)
    for y, dz in ((0.45, -0.15), (0.45, 0.1), (0.7, 0.25), (0.9, 0.25)):
        slat = s3.box((x, y, z + dz), (1.9, 0.06, 0.16))
        s3.draw(cv, CAMERA, slat, {"top": CAR_SNOW, "*": BENCH}, DUSK_LIGHT, ambient=0.7, highlight=0.0)


def paint_lamp_pool(cv):
    x, z = LAMP_AT
    center = CAMERA.project((x, 0.0, z))
    radius = CAMERA.scale_at((x, 0.0, z)) * 7.0
    cv.fill(cv.shape(g.ellipse(center[0], center[1], radius, radius * 0.25), soft=radius * 0.4), SODIUM, opacity=0.8,
            blend=Blend.SCREEN)


def paint_birch(cv, rng, x, z, height):
    """흰 줄기와 검은 껍질 무늬, 위로 갈수록 가늘게 갈라지는 맨가지."""
    base, top = CAMERA.project((x, 0.0, z)), CAMERA.project((x + 0.3, height, z))
    width = CAMERA.scale_at((x, 0.0, z)) * 0.3
    trunk = cv.shape(*g.ribbon(g.densify(np.array([base, top]), 10), (width, width * 0.35)))
    cv.fill(trunk, BIRCH)
    cv.fill(cv.form_shadow(trunk, (0.6, -0.3), 0.45), "#8a8e96")
    for _ in range(int(height * 2)):
        t = rng.uniform(0.05, 0.9)
        y = base[1] + (top[1] - base[1]) * t
        mark_x = base[0] + (top[0] - base[0]) * t
        cv.stroke([(mark_x - width * 0.5, y), (mark_x + width * 0.2, y + 2)], BIRCH_MARK, width=2.0, clip=trunk)
    for _ in range(26):
        t = rng.uniform(0.3, 0.98)
        start = np.array(base) + (np.array(top) - np.array(base)) * t
        angle = rng.uniform(-150.0, -30.0)
        length = CAMERA.scale_at((x, 0.0, z)) * rng.uniform(1.2, 3.0) * (1.2 - t)
        end = start + length * np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
        middle = (start + end) / 2 + rng.normal(0.0, length * 0.08, 2)
        cv.stroke(g.spline([start, middle, end], closed=False), BRANCH, width=max(width * 0.35, 1.6), taper=(1.0, 0.1))
        for twig in range(3):
            tip = end + rng.normal(0.0, length * 0.25, 2) - np.array([0.0, length * 0.2])
            cv.stroke([end * 0.7 + start * 0.3, tip], BRANCH, width=1.2, taper=(1.0, 0.0), opacity=0.8)


def paint_lamp(cv):
    x, z = LAMP_AT
    base, top = CAMERA.project((x, 0.0, z)), CAMERA.project((x, LAMP_HEIGHT, z))
    head = CAMERA.project((x + 1.2, LAMP_HEIGHT - 0.2, z))
    scale = CAMERA.scale_at((x, 0.0, z))
    cv.stroke([base, top], METAL, width=scale * 0.16, taper=(1.0, 0.7))
    cv.stroke(g.spline([top, (top[0] + scale * 0.5, top[1] - scale * 0.3), head], closed=False), METAL,
              width=scale * 0.08)
    cv.fill(cv.shape(g.ellipse(head[0], head[1], scale * 0.45, scale * 0.14)), METAL)
    cv.fill(cv.shape(g.ellipse(head[0], head[1] + scale * 0.1, scale * 0.3, scale * 0.08)), SODIUM_CORE)
    cv.fill(cv.shape(g.ellipse(head[0], head[1] + scale * 0.4, scale * 2.4, scale * 2.0), soft=scale * 1.6),
            SODIUM_GLOW, opacity=0.55, blend=Blend.SCREEN)


def paint_wires(cv):
    """화면 위를 가로지르는 트롤리버스 전선 두 가닥과 오른쪽 가장자리의 지지 기둥."""
    pole_x = WIDTH - 70.0
    cv.fill(cv.shape(g.rect(pole_x - 12, 0, 24, HEIGHT)), INK)
    for y0, y1 in ((120.0, 70.0), (150.0, 98.0)):
        cv.stroke(g.spline([(-20, y0), (WIDTH * 0.45, y0 + 40), (pole_x, y1)], closed=False), INK, width=2.6)
    cv.stroke([(pole_x, 84.0), (pole_x - 160, 84.0)], INK, width=5.0)


def main(out_dir="out", scale=1.0, seed=149):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv, rng)
    paint_yard(cv, rng)
    paint_blocks(cv, rng)
    paint_garages(cv)
    paint_playground(cv)
    paint_lamp_pool(cv)
    for x, z, height in sorted(BIRCHES, key=lambda tree: -tree[1]):
        paint_birch(cv, rng, x, z, height)
    paint_lamp(cv)
    paint_bench(cv)
    paint_car(cv)
    paint_wires(cv)
    io.save(cv.guide_image(), out_dir / "courtyard_1_guide.png")
    image = anime.finish(cv, diffusion=0.2, bloom=0.4, shadows="#0e1a2a", highlights="#ffcf8a", grade_amount=0.14,
                         grain=0.025)
    image = post.grade(image, contrast=1.04, saturation=0.82)
    return io.save(post.vignette(image, strength=0.3), out_dir / "anime_doomer_courtyard.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
