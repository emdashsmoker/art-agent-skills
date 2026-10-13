"""애니메풍 예제(두머 분위기): 눈 내리는 밤, 패널 아파트 단지 앞 버스 정류장에 혼자 선 남자.

화면 오른쪽 위 밖의 나트륨 가로등이 유일한 따뜻한 빛이다. 빛 원뿔 안의 눈송이와 인물의 오른쪽 윤곽만 주황으로 빛나고
나머지는 탁한 회청색 밤에 잠긴다. 분위기 값은 references/mood-doomer.md.
공정: 밤하늘 → 패널 아파트 2동(1점 투시 정면 벽과 창 격자) → 젖은 차도와 눈 인도 → 정류장(무대 투영) →
인물(투명 층, 등 쪽 빛 테두리) → 빛 원뿔과 빛 웅덩이 → 가로등 기둥 → 눈송이 → 촬영 마감 → 색 보정.
실행: python anime_doomer_bus_stop.py [출력폴더] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Perspective, garment, io, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1200, 1600
STAGE = Stage(origin=(600.0, 1490.0), unit=128.0, elevation=4.0)
MAN_AT, MAN_TURN = (-0.7, 0.0), 24.0           # 세계 (x, z)와 몸 방향. 가로등 쪽(화면 오른쪽)으로 조금 돈다
HORIZON_Y = 640.0
VIEW = Perspective((WIDTH * 0.5, HORIZON_Y), eye_height=1.6, focal=900.0)   # 정류장 뒤 단지(미터)
LAMP_HEAD = (900.0, 120.0)                      # 가로등 머리. 화면 위 가장자리 가까이
LAMP_POLE_X = 1080.0
POOL = (640.0, 1500.0)                          # 빛 웅덩이 가운데(인물 발밑)
LAMP_LIGHT = (0.55, -0.85)                      # 화면 빛 방향(가로등 쪽)
LAMP_LIGHT_3D = (0.45, -0.8, -0.4)
FLAKES = 520
FLOOR_HEIGHT_M = 2.8                            # 패널 아파트 한 층 높이(미터)

# 팔레트: 탁한 회청색 밤이 지배색. 따뜻한 색은 나트륨 주황과 창 노랑 2종뿐이고 TV 창 하나만 차가운 청색으로 빛난다.
NIGHT_TOP, NIGHT_LOW, CITY_GLOW = "#0b1018", "#253041", "#5a4a4a"
PANEL_FAR, PANEL_NEAR, PANEL_SEAM = "#242b36", "#2e3642", "#161b22"
WINDOW_DARK, WINDOW_WARM, WINDOW_TV, BALCONY = "#1a2029", "#e9b86a", "#8fb3c9", "#262d37"
ROAD, ROAD_WET, CURB = "#161b22", "#2a3038", "#59606b"
SNOW, SNOW_SHADE, SNOW_FAR = "#59626e", "#3a424d", "#4a525d"
SHELTER, SHELTER_LINE, GLASS = "#3b424c", "#14181e", "#6f8296"
SODIUM, SODIUM_GLOW, SODIUM_CORE = "#f2a65a", "#ffcf8a", "#fff1d0"
POLE = "#1a1d22"
BUS_SIGN, BUS_SIGN_BAND = "#4d5a6c", "#8d97a3"

STREET_INK = ch.Ink(line_width=2.2, body_shadow=0.46, face_shadow=0.22, hair_shadow=0.48, light_opacity=0.45) \
    .lit_from(LAMP_LIGHT, LAMP_LIGHT_3D)
MAN = replace(ch.MALE, palette=replace(ch.MALE.palette, skin="#e6c3ab", skin_shade="#a8807a", skin_deep="#7a5250",
                                       skin_light="#ffe2c4", hair="#1d1b20", hair_shade="#0c0b0f",
                                       hair_light="#4a4650", line_hair="#08080a", line_skin="#5a3a36"))
PARKA = garment.long_coat(coat="#383c43", scarf="#6b5d55", legs="#22252b", boots="#1b1a19", length=1.6, belt=False,
                          scarf_tail=False)


def make_man():
    """팔을 내리고 고개를 조금 숙인 채 버스를 기다리는 자세."""
    return STAGE.place(MAN, MAN_AT[0], MAN_AT[1], MAN_TURN, outfit=PARKA, ink=STREET_INK, head=-3.0, head_turn=-14.0,
                       head_pitch=9.0, arm_l=(9.0, 5.0), arm_r=(8.0, 4.0), leg_l=(4.0, 1.0), leg_r=(3.0, 0.0))


# ---------- 배경 ----------

def paint_sky(cv):
    cv.fill(cv.full(), Linear([NIGHT_TOP, NIGHT_LOW], (0, 0), (0, HORIZON_Y)))
    # 도시 불빛이 낮은 구름에 비친 탁한 빛.
    cv.fill(cv.shape(g.ellipse(WIDTH * 0.35, HORIZON_Y - 60, 900, 260), soft=220), CITY_GLOW, opacity=0.45,
            blend=Blend.SCREEN)


def paint_panel_block(cv, rng, x_left, x_right, z, floors, columns, wall, lit_ratio):
    """카메라를 마주 보는 패널 아파트 1동: 벽, 층마다 이음매, 창 격자(켜진 창 몇 개), 발코니 띠."""
    top = floors * FLOOR_HEIGHT_M
    cv.fill(cv.shape(VIEW.front_wall(x_left, x_right, z, 0.0, top)), wall)
    for floor in range(1, floors):
        y = floor * FLOOR_HEIGHT_M
        cv.stroke(VIEW.path([(x_left, y, z), (x_right, y, z)]), PANEL_SEAM, width=1.2, opacity=0.7)
    for column in range(0, columns + 1, 2):
        x = x_left + (x_right - x_left) * column / columns
        cv.stroke(VIEW.path([(x, 0.0, z), (x, top, z)]), PANEL_SEAM, width=1.0, opacity=0.5)
    cells = VIEW.front_wall_grid(x_left, x_right, z, 0.0, top, columns, floors, margin=0.28)
    for index, cell in enumerate(cells):
        roll = rng.random()
        if roll < lit_ratio * 0.08:
            color = WINDOW_TV
        elif roll < lit_ratio:
            color = WINDOW_WARM
        else:
            color = WINDOW_DARK
        cv.fill(cv.shape(cell), color, opacity=0.9 if color != WINDOW_DARK else 1.0)
        if color != WINDOW_DARK:
            center = cell.mean(axis=0)
            glow = VIEW.scale_at(z) * 1.6
            cv.fill(cv.shape(g.ellipse(center[0], center[1], glow, glow * 0.8), soft=glow * 0.7), color, opacity=0.25,
                    blend=Blend.SCREEN)
        # 칸 3개 중 1개는 창 아래 발코니 난간 띠를 덧댄다.
        if (index // floors) % 3 == 1 and index % floors > 0:
            low = cell[:, 1].max()
            cv.fill(cv.shape(g.rect(cell[:, 0].min() - 2, low - (low - cell[:, 1].min()) * 0.35,
                                    np.ptp(cell[:, 0]) + 4, (low - cell[:, 1].min()) * 0.35)), BALCONY)


def paint_blocks(cv, rng):
    paint_panel_block(cv, rng, -48.0, 6.0, 60.0, 9, 30, PANEL_FAR, 0.16)
    paint_panel_block(cv, rng, 2.0, 46.0, 40.0, 5, 22, PANEL_NEAR, 0.2)


def paint_ground(cv):
    """먼 인도, 젖은 차도(가로등 빛이 길게 비침), 연석, 정류장 앞 눈 인도."""
    far_walk = VIEW.ground(-60.0, 60.0, 14.0, 40.0)
    cv.fill(cv.shape(far_walk), SNOW_FAR)
    road = cv.shape(VIEW.ground(-60.0, 60.0, 5.5, 14.0))
    cv.fill(road, Linear([ROAD_WET, ROAD], (0, HORIZON_Y), (0, VIEW.project(0, 0, 5.5)[1])))
    cv.fill(cv.shape(g.rect(LAMP_HEAD[0] - 60, VIEW.project(0, 0, 14.0)[1], 120,
                            VIEW.project(0, 0, 5.5)[1] - VIEW.project(0, 0, 14.0)[1]), soft=30), SODIUM, opacity=0.3,
            blend=Blend.SCREEN, clip=road)
    curb_y = VIEW.project(0, 0, 5.5)[1]
    cv.fill(cv.shape(g.rect(0, curb_y - 6, WIDTH, 12)), CURB)
    walk = cv.shape(g.rect(0, curb_y + 6, WIDTH, HEIGHT - curb_y))
    cv.fill(walk, Linear([SNOW_SHADE, SNOW], (0, curb_y), (0, HEIGHT)))
    # 밟혀 녹은 발자국 길.
    for x0, x1 in ((80, 520), (760, 1150)):
        cv.stroke(g.spline([(x0, HEIGHT), ((x0 + x1) / 2, curb_y + 160), (x1, curb_y + 40)], closed=False), SNOW_SHADE,
                  width=40, taper=(1.0, 0.3), opacity=0.5, soft=8)


def paint_shelter(cv):
    """화면 왼쪽에 걸친 정류장: 뒷유리, 기둥, 얇은 지붕, 의자, 노선 표지판. 인물과 같은 무대 시선으로 투영.

    정류장 전체를 인물 뒤에 두면 유리판이 화면을 덮어 단지가 가려지므로 오른쪽 끝만 화면에 걸친다.
    """
    left, right, back_z = -9.0, -3.4, 2.6
    glass = cv.shape(STAGE.project([(left, -10.6, back_z), (right, -10.6, back_z), (right, -1.2, back_z),
                                    (left, -1.2, back_z)]))
    cv.fill(glass, GLASS, opacity=0.22)
    cv.fill(cv.contour(glass, 2.0), SHELTER_LINE, opacity=0.8)
    for z in (back_z, 0.4):
        cv.stroke(STAGE.project([(right, 0.0, z), (right, -11.0, z)]), SHELTER, width=10 if z == back_z else 12)
    for name, path, _ in STAGE.box((left - 0.4, right + 0.4), (-11.5, -11.0), (0.2, back_z + 0.3)):
        cv.fill(cv.shape(path), SHELTER if name != "front" else SHELTER_LINE)
    for name, path, _ in STAGE.box((left, right - 0.4), (-2.2, -1.95), (1.7, 2.4)):
        cv.fill(cv.shape(path), SHELTER)
        cv.fill(cv.contour(cv.shape(path), 1.4), SHELTER_LINE)
    sign = cv.shape(STAGE.project([(right - 0.1, -10.0, 0.4), (right + 1.2, -10.0, 0.4), (right + 1.2, -8.8, 0.4),
                                   (right - 0.1, -8.8, 0.4)]))
    cv.fill(sign, BUS_SIGN)
    band = STAGE.project([(right + 0.05, -9.7, 0.4), (right + 1.05, -9.7, 0.4), (right + 1.05, -9.45, 0.4),
                          (right + 0.05, -9.45, 0.4)])
    cv.fill(cv.shape(band), BUS_SIGN_BAND)
    cv.fill(cv.contour(sign, 2.0), SHELTER_LINE)


def paint_wires(cv):
    """화면 위를 가로지르는 트롤리버스 전선 2가닥. 가운데가 조금 처진다."""
    for y0, y1, sag in ((150.0, 210.0, 26.0), (178.0, 236.0, 26.0)):
        cv.stroke(g.spline([(-20, y0), (WIDTH * 0.5, (y0 + y1) / 2 + sag), (WIDTH + 20, y1)], closed=False), POLE,
                  width=2.2, opacity=0.9)


# ---------- 빛 ----------

def paint_pool(cv):
    """인물보다 먼저: 눈 위의 빛 웅덩이와 가로등 반대쪽(왼쪽 아래)으로 눕는 인물 그림자."""
    cv.fill(cv.shape(g.ellipse(POOL[0] + 80, POOL[1] - 20, 600, 190), soft=150), SODIUM, opacity=0.7,
            blend=Blend.SCREEN)
    shadow = g.polygon([(POOL[0] - 70, POOL[1] - 4), (POOL[0] + 70, POOL[1] + 6), (POOL[0] - 330, HEIGHT + 30),
                        (POOL[0] - 520, HEIGHT + 30)])
    cv.fill(cv.shape(shadow, soft=24), "#0a0c10", opacity=0.5)
    cv.fill(cv.shape(g.ellipse(POOL[0], POOL[1] + 6, 120, 26), soft=14), "#0a0c10", opacity=0.55)


def paint_cone(cv):
    """가로등 머리에서 인물 쪽으로 퍼지는 빛 원뿔."""
    left, right = (POOL[0] - 520, POOL[1] + 40), (POOL[0] + 520, POOL[1] + 40)
    cone = cv.shape(g.polygon([LAMP_HEAD, right, left]), soft=90)
    cv.fill(cone, SODIUM_GLOW, opacity=0.14, blend=Blend.SCREEN)


def paint_lamp(cv):
    """화면 오른쪽 위에 걸친 가로등: 빛 번짐을 먼저 깔고 그 위에 기둥, 팔, 등갓 실루엣과 아래로 향한 등 유리.

    등갓을 빛 번짐보다 먼저 칠하면 번짐에 묻혀 등 유리만 허공에 뜬 원반처럼 보인다.
    """
    x, y = LAMP_HEAD
    cv.fill(cv.shape(g.ellipse(x, y + 10, 230, 170), soft=160), SODIUM, opacity=0.6, blend=Blend.SCREEN)
    cv.stroke([(LAMP_POLE_X, HEIGHT), (LAMP_POLE_X, 170)], POLE, width=22, taper=(1.0, 0.75))
    cv.stroke(g.spline([(LAMP_POLE_X, 180), (LAMP_POLE_X - 30, 96), (x + 110, 70), (x + 60, 82)], closed=False), POLE,
              width=12)
    hood = cv.shape(g.spline([(x - 92, y + 18), (x - 60, y - 14), (x + 40, y - 30), (x + 88, y - 8), (x + 70, y + 12)],
                             corners=(0, 4)))
    cv.fill(hood, POLE)
    cv.fill(cv.edge_light(hood, (0.2, -1.0), width=3.0), SODIUM, opacity=0.5)
    lens = cv.shape(g.ellipse(x - 6, y + 14, 74, 11, angle=-6))
    cv.fill(lens, SODIUM_CORE)
    cv.fill(cv.shape(g.ellipse(x - 6, y + 22, 120, 40), soft=30), SODIUM_GLOW, opacity=0.5, blend=Blend.SCREEN)


def paint_snow(cv, rng):
    """눈송이: 먼 것은 작고 흐리며 빛 원뿔 안의 것은 주황 흰빛, 밖은 회청 흰빛."""
    apex = np.array(LAMP_HEAD)
    for _ in range(FLAKES):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT)
        near = rng.random() ** 3
        radius = 1.4 + near * 6.0
        reach = (y - apex[1]) / (POOL[1] - apex[1])
        inside = 0.0 < reach < 1.0 and abs(x - (apex[0] + (POOL[0] - apex[0]) * reach)) < 520 * reach
        color = SODIUM_CORE if inside else "#c9d2dc"
        cv.fill(cv.shape(g.ellipse(x, y, radius, radius), soft=radius * (0.4 + near)), color,
                opacity=(0.85 if inside else 0.45) * (0.5 + 0.5 * near))


# ---------- 인물 ----------

def paint_person(scale, seed, model):
    """인물을 투명 층에 칠하고 가로등 쪽 윤곽에 주황 빛 테두리를 두른다."""
    layer = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    ch.paint_figure(layer, model)
    anime.rim_light(layer, LAMP_LIGHT, width=5.0, tint=SODIUM_GLOW, opacity=0.85)
    return layer


def main(out_dir="out", scale=1.0, seed=131):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv)
    paint_blocks(cv, rng)
    paint_ground(cv)
    paint_shelter(cv)
    paint_pool(cv)
    man = make_man()
    cv.paste(paint_person(scale, seed, man))
    paint_cone(cv)
    paint_wires(cv)
    paint_lamp(cv)
    paint_snow(cv, rng)
    io.save(cv.guide_image(), out_dir / "bus_stop_1_guide.png")
    image = anime.finish(cv, diffusion=0.22, bloom=0.45, shadows="#0e1a2a", highlights="#ffcf8a", grade_amount=0.14,
                         grain=0.03)
    image = post.grade(image, contrast=1.04, saturation=0.82)
    return io.save(post.vignette(image, strength=0.38), out_dir / "anime_doomer_bus_stop.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
