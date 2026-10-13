"""수채화 예제(두머 분위기): 눈 내리는 해 질 녘에 올려다본 9층 패널 아파트 1동(도시화).

카메라를 땅에서 올려 기울인 solids 카메라라 세로선이 위로 모이는 3점 투시가 된다.
켜진 창은 벽 물칠에서 빼 둔 종이 자리에 노랑을 얹는다. 곱하기 겹칠에서는 밝은 색을 어두운 벽 위에 올릴 수 없다.
돌출 발코니는 상자로 붙이고 일부는 제각각의 유리 틀로 막았다. 따뜻한 색은 창과 현관등, 가로등뿐이다.
분위기 값은 references/mood-doomer.md.
공정: 하늘 물칠 → 벽(켜진 창 자리를 비움) → 층 이음매와 꺼진 창 → 켜진 창 → 발코니 → 지붕 위 기계실과 안테나 →
현관 차양과 등 → 눈 마당, 길, 의자 → 앞쪽 맨가지 → 가로등 → 눈송이 → 수채화 패스 → 색 보정.
실행: python watercolor_doomer_block.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402

WIDTH, HEIGHT = 1300, 1700
CAMERA = s3.Camera(eye=(0.0, 1.6, 0.0), target=(6.0, 14.0, 34.0), focal=900.0, center=(650.0, 850.0))
LIGHT = (-0.4, 0.6, -0.6)            # 흐린 하늘의 확산광. 정면 벽이 옆면보다 조금 밝다
FLOOR_HEIGHT_M = 2.8
FLOORS, COLUMNS = 9, 16
# 동은 화면 오른쪽에 두고 정면을 오른쪽 앞으로 돌려 왼쪽 끝 벽(창 없는 박공벽)과 오른쪽으로 물러나는 긴 정면을 함께 보인다.
BLOCK_CENTER, BLOCK_SIZE, BLOCK_YAW = (18.0, FLOORS * FLOOR_HEIGHT_M / 2, 32.0), (46.0, FLOORS * FLOOR_HEIGHT_M, 12.0), -30.0
LIT_RATIO, TV_RATIO = 0.17, 0.02
BALCONY_COLUMNS = (2, 6, 9, 13)      # 발코니가 달린 칸(1칸 폭)
ENTRANCES = (3, 11)                  # 현관이 있는 칸
LAMP_POST = (-2.5, 12.0, 6.5)        # 가로등 (x, z, 높이)
FLAKES = 260

# 팔레트: 회청색 하늘과 콘크리트가 지배색, 눈은 종이 흰색. 난색은 창, 현관등, 가로등 3곳뿐이다.
SKY_TOP, SKY_LOW = "#6f7b93", "#c4aaa0"
WALL, WALL_SIDE, SEAM = "#a3abb6", "#7f8896", "#5c6472"
WINDOW_DARK, WINDOW_WARM, WINDOW_TV = "#626c7c", "#f3c977", "#9cc0d6"
BALCONY, BALCONY_GLASS, BALCONY_FRAME = "#857a74", "#7a8aa0", "#6a5446"
ROOF, ANTENNA = "#6a7180", "#3a3f4a"
CANOPY, DOOR, BULB = "#6f7684", "#3e4450", "#ffd28a"
SNOW_SHADE, PATH, BENCH = "#c3ccd8", "#a9b3c2", "#5a4c46"
BRANCH, LAMP_POLE, SODIUM = "#343944", "#3c414c", "#f2a65a"


def make_block():
    return s3.box(BLOCK_CENTER, BLOCK_SIZE).rotated(yaw=BLOCK_YAW, about=(BLOCK_CENTER[0], 0.0, BLOCK_CENTER[2]))


def cell(column, row, inset_u=0.26, top=0.3, bottom=0.78):
    """정면의 (칸, 층) 창 자리를 면 좌표 사각형으로. row 0은 맨 위층."""
    return ((column + inset_u) / COLUMNS, (row + top) / FLOORS, (column + 1 - inset_u) / COLUMNS, (row + bottom) / FLOORS)


def window_plan(rng):
    """칸마다 창 상태(dark, warm, tv). 1층의 현관 칸은 비운다."""
    plan = {}
    for column in range(COLUMNS):
        for row in range(FLOORS):
            if row == FLOORS - 1 and column in ENTRANCES:
                continue
            roll = rng.random()
            plan[(column, row)] = "tv" if roll < TV_RATIO else "warm" if roll < LIT_RATIO else "dark"
    return plan


# ---------- 하늘과 벽 ----------

def ground_line():
    """지평선(눈높이의 아주 먼 점)의 화면 높이. 하늘 물칠은 여기서 끝나고 아래는 눈 덮인 땅."""
    eye = CAMERA.eye
    return CAMERA.project((eye[0], eye[1], eye[2] + 1e5))[1]


def paint_sky(cv, rng):
    horizon = ground_line()
    watercolor.wash(cv, g.rect(-40, -40, WIDTH + 80, horizon + 40), Linear([SKY_TOP, SKY_LOW], (0, 0), (0, horizon)),
                    opacity=0.7, soft=12, rough=10)
    # 눈구름의 짙은 얼룩.
    for _ in range(5):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, horizon * 0.5)
        watercolor.wash(cv, g.blob(x, y, rng.uniform(160, 320), 0.3, 7, rng, stretch=(1.8, 0.6)), SKY_TOP,
                        opacity=0.3, soft=40, rough=20)


def paint_walls(cv, block, plan):
    """벽 물칠. 켜진 창은 종이 자리로 비우고 나중에 노랑을 얹는다."""
    front = block.face("front")
    lit = None
    for (column, row), state in plan.items():
        if state != "dark":
            shape = cv.shape(CAMERA.region(front, *cell(column, row)))
            lit = shape if lit is None else lit | shape
    for face in CAMERA.visible_faces(block):
        color = {"front": WALL, "top": ROOF}.get(face.name, WALL_SIDE)
        wall = cv.roughen(cv.shape(CAMERA.path(face.vertices), soft=1.5), 2.5)
        # 하늘 물칠 위에 곱하면 지평선 위아래로 벽 색이 갈리므로 벽 자리를 먼저 종이색으로 덮는다.
        cv.fill(wall, "#ffffff")
        if face.name == "front" and lit is not None:
            wall = wall - lit
        cv.fill(wall, color, opacity=0.85, blend=Blend.MULTIPLY)
        # 벽 아래쪽은 눈의 반사광이 덜 닿아 한 번 더 겹칠한다.
        if face.name != "top":
            low = CAMERA.path([face.point(0.0, 0.55), face.point(1.0, 0.55), face.point(1.0, 1.0), face.point(0.0, 1.0)])
            cv.fill(cv.shape(low, soft=40) & wall, SEAM, opacity=0.25, blend=Blend.MULTIPLY)
    return front


def paint_windows(cv, front, plan):
    for row in range(1, FLOORS):
        cv.stroke(CAMERA.path([front.point(0.0, row / FLOORS), front.point(1.0, row / FLOORS)]), SEAM, width=1.2,
                  opacity=0.5, blend=Blend.MULTIPLY)
    for column in range(0, COLUMNS + 1, 2):
        cv.stroke(CAMERA.path([front.point(column / COLUMNS, 0.0), front.point(column / COLUMNS, 1.0)]), SEAM,
                  width=1.0, opacity=0.35, blend=Blend.MULTIPLY)
    colors = {"dark": WINDOW_DARK, "warm": WINDOW_WARM, "tv": WINDOW_TV}
    for (column, row), state in plan.items():
        path = CAMERA.region(front, *cell(column, row))
        watercolor.wash(cv, path, colors[state], opacity=0.9 if state == "dark" else 0.75, soft=1.2, rough=1.5)
        if state != "dark":
            center = path.mean(axis=0)
            spread = np.ptp(path[:, 0]) * 1.4
            watercolor.wash(cv, g.ellipse(center[0], center[1], spread, spread * 0.8), colors[state], opacity=0.18,
                            soft=spread * 0.5, rough=4)


def paint_balconies(cv, block, rng):
    """돌출 발코니: 정면에 붙인 얕은 상자. 절반은 집집마다 다른 색 틀의 유리로 막았다."""
    front = block.face("front")
    normal = front.normal
    for column in BALCONY_COLUMNS:
        for row in range(1, FLOORS - 1):
            u0, v0, u1, v1 = (column + 0.08) / COLUMNS, (row + 0.62) / FLOORS, (column + 0.92) / COLUMNS, (row + 1.0) / FLOORS
            corners = front.region(u0, v0, u1, v1)
            outer = corners + normal * 1.0
            glazed = rng.random() < 0.5
            parapet = CAMERA.path([outer[0], outer[1], outer[2], outer[3]])
            # 아래에서 올려다보므로 발코니 바닥판의 밑면이 어두운 띠로 보인다.
            underside = CAMERA.path([corners[3], corners[2], outer[2], outer[3]])
            watercolor.wash(cv, underside, SEAM, opacity=0.8, soft=1.0, rough=1.2, cover=True)
            watercolor.wash(cv, parapet, BALCONY_GLASS if glazed else BALCONY, opacity=0.85, soft=1.0, rough=1.2,
                            cover=True)
            if glazed:
                for t in np.linspace(0.0, 1.0, 4):
                    top = outer[0] + (outer[1] - outer[0]) * t
                    low = outer[3] + (outer[2] - outer[3]) * t
                    cv.stroke(CAMERA.path([top, low]), BALCONY_FRAME, width=1.4, opacity=0.8)


def paint_roof(cv, block):
    """지붕 위 TV 안테나. 아래에서 올려다보므로 지붕 면과 기계실은 난간에 가려 보이지 않는다."""
    top = block.face("top")
    for u in (0.1, 0.45, 0.85):
        base = top.point(u, 0.9)
        cv.stroke(CAMERA.path([base, base + np.array([0.0, 3.5, 0.0])]), ANTENNA, width=1.6)
        for level in (2.6, 3.1, 3.5):
            cv.stroke(CAMERA.path([base + np.array([-1.0, level, 0.0]), base + np.array([1.0, level, 0.0])]), ANTENNA,
                      width=1.2)


def paint_end_wall(cv, block):
    """창 없는 박공벽의 패널 이음매 격자. 패널 아파트의 끝 벽에서 가장 또렷하게 보인다."""
    face = block.face("left")
    for row in range(1, FLOORS):
        cv.stroke(CAMERA.path([face.point(0.0, row / FLOORS), face.point(1.0, row / FLOORS)]), SEAM, width=1.4,
                  opacity=0.6, blend=Blend.MULTIPLY)
    for column in range(1, 4):
        cv.stroke(CAMERA.path([face.point(column / 4, 0.0), face.point(column / 4, 1.0)]), SEAM, width=1.4,
                  opacity=0.6, blend=Blend.MULTIPLY)


def paint_entrances(cv, front):
    """현관: 문, 차양, 차양 밑의 등. 현관 위 계단실 창은 반 층 어긋나 있다."""
    for column in ENTRANCES:
        door = CAMERA.region(front, (column + 0.3) / COLUMNS, (FLOORS - 0.75) / FLOORS, (column + 0.7) / COLUMNS, 1.0)
        watercolor.wash(cv, door, DOOR, opacity=0.95, soft=1.0, rough=1.2)
        lip = front.region((column + 0.1) / COLUMNS, (FLOORS - 0.85) / FLOORS, (column + 0.9) / COLUMNS,
                           (FLOORS - 0.78) / FLOORS)
        canopy = np.vstack([lip[:2], lip[1] + front.normal * 1.6, lip[0] + front.normal * 1.6])
        watercolor.wash(cv, CAMERA.path(canopy), CANOPY, opacity=0.95, soft=1.0, rough=1.2, cover=True)
        bulb = CAMERA.project(front.point((column + 0.5) / COLUMNS, (FLOORS - 0.74) / FLOORS) + front.normal * 0.3)
        watercolor.wash(cv, g.ellipse(bulb[0], bulb[1], 70, 60), BULB, opacity=0.35, soft=30, rough=6)
        cv.fill(cv.shape(g.ellipse(bulb[0], bulb[1], 4, 3)), "#ffffff")


# ---------- 마당 ----------

def paint_yard(cv, rng):
    """눈 덮인 마당은 종이로 두고 그늘과 밟힌 길만 칠한다."""
    horizon = ground_line()
    watercolor.wash(cv, g.rect(-40, horizon, WIDTH + 80, HEIGHT - horizon + 40), Linear([SNOW_SHADE, "#ffffff"],
                    (0, horizon), (0, HEIGHT)), opacity=0.45, soft=6, rough=6)
    for offset in (-34.0, 34.0):
        track = g.spline([(300 + offset * 2.4, HEIGHT + 40), (470 + offset, 1500), (560 + offset * 0.5, 1400),
                          (640, horizon + 30)], closed=False)
        cv.stroke(track, PATH, width=34, taper=(1.0, 0.1), opacity=0.45, soft=5)
    for _ in range(18):
        x, y = rng.uniform(0, WIDTH), rng.uniform(1320, HEIGHT)
        watercolor.wash(cv, g.ellipse(x, y, rng.uniform(40, 120), rng.uniform(6, 14)), SNOW_SHADE, opacity=0.4, soft=4,
                        rough=4)
    # 눈 쌓인 의자: 다리와 등받이만 칠하고 앉는 판의 눈은 종이로 남긴다.
    for x in (860.0, 1010.0):
        cv.stroke([(x, 1505), (x, 1560)], BENCH, width=7)
    for y in (1430.0, 1455.0):
        cv.stroke([(830, y), (1040, y)], BENCH, width=9)
    cv.stroke([(820, 1500), (1050, 1500)], BENCH, width=5, opacity=0.6)


def paint_tree(cv, rng):
    """화면 왼쪽 위로 들어온 앞쪽 나무의 맨가지. 마른 붓으로 가장 어둡게 그린다."""
    trunk = [(-30, 1180), (60, 900), (120, 620), (150, 380)]
    cv.stroke(g.spline(trunk, closed=False), BRANCH, width=34, taper=(1.0, 0.5))
    for _ in range(26):
        t = rng.uniform(0.2, 1.0)
        start = np.array(trunk[0]) + (np.array(trunk[-1]) - np.array(trunk[0])) * t
        angle = rng.uniform(-80.0, 10.0)
        length = rng.uniform(120, 420) * (1.2 - t * 0.5)
        end = start + length * np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
        middle = (start + end) / 2 + rng.normal(0.0, length * 0.1, 2)
        cv.stroke(g.spline([start, middle, end], closed=False), BRANCH, width=rng.uniform(3, 9), taper=(1.0, 0.05))
        for _ in range(3):
            twig = end + rng.normal(0.0, length * 0.2, 2)
            cv.stroke([middle * 0.4 + end * 0.6, twig], BRANCH, width=1.5, taper=(1.0, 0.0), opacity=0.85)


def paint_lamp(cv):
    x, z, height = LAMP_POST
    base, top = CAMERA.project((x, 0.0, z)), CAMERA.project((x, height, z))
    head = CAMERA.project((x - 1.2, height - 0.2, z))
    cv.stroke([base, top], LAMP_POLE, width=12, taper=(1.0, 0.7))
    cv.stroke(g.spline([top, (top[0] - 20, top[1] - 20), head], closed=False), LAMP_POLE, width=6)
    watercolor.wash(cv, g.ellipse(head[0], head[1] + 24, 90, 80), SODIUM, opacity=0.3, soft=36, rough=6)
    cv.fill(cv.shape(g.ellipse(head[0], head[1] + 6, 16, 6)), "#fff4dc")


def paint_snow(cv, rng):
    """눈송이: 칠을 마친 위에 흰 점을 덮어 종이색으로 되돌린다."""
    for _ in range(FLAKES):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT)
        radius = 1.5 + rng.random() ** 3 * 5.0
        cv.fill(cv.shape(g.ellipse(x, y, radius, radius), soft=radius * 0.4), "#ffffff", opacity=0.85)


def main(out_dir="out", scale=1.0, seed=151):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    block = make_block()
    plan = window_plan(rng)
    paint_sky(cv, rng)
    front = paint_walls(cv, block, plan)
    paint_windows(cv, front, plan)
    paint_balconies(cv, block, rng)
    paint_roof(cv, block)
    paint_end_wall(cv, block)
    paint_entrances(cv, front)
    paint_yard(cv, rng)
    paint_tree(cv, rng)
    paint_lamp(cv)
    paint_snow(cv, rng)
    io.save(cv.guide_image(), out_dir / "block_1_underpainting_guide.png")
    image = watercolor.render(cv, wobble=1.2, bleed=0.45, edge=0.5, turbulence=0.2)
    image = post.grade(image, shadows="#1a2a3a", highlights="#ffe8c8", amount=0.08, saturation=0.9)
    return io.save(image, out_dir / "watercolor_doomer_block.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
