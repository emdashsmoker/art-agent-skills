"""애니메풍 예제: 여름 바다가 보이는 큰 창가에 선 긴 생머리 여성의 3/4 뒷모습(역광, 무릎 위 구도).

얼굴은 날카로운 인상(faces.FEMALE_SHARP), 머리는 긴 생머리, 머리색은 은발이다. 등 뒤로 흐른 다발(drape back)이
등을 덮고 창에서 드는 역광이 머리와 어깨 윤곽에 하늘색 빛 테두리를 만든다. 몸의 보이는 쪽은 대부분 그늘이다.
공정: 방 벽과 바닥 → 창밖(하늘, 적란운, 바다, 섬, 물비늘) → 창틀과 창살 → 창턱 → 얇은 커튼 →
인물(투명 층, 역광 테두리) → 창빛 번짐 → 촬영 마감.
실행: python anime_long_hair_window.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, faces, garment, hairstyles, io, motifs, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1600, 1100
WINDOW = (180.0, 60.0, 1420.0, 860.0)     # 창 안쪽 (x0, y0, x1, y1)
HORIZON_Y = 560.0
PELVIS, UNIT, TURN = (930.0, 1060.0), 205.0, 140.0
BACK_LIGHT, BACK_LIGHT_3D = (0.25, -0.9), (0.2, -0.5, 0.85)   # 창(관찰자 반대쪽)에서 드는 빛

# 팔레트: 한여름 하늘과 바다의 파랑이 지배색. 방 안은 역광으로 어두운 회보라, 은발과 흰 셔츠가 창빛을 받아 가장 밝다.
SKY = [(0.0, "#2a6cd0"), (0.6, "#7ab8ee"), (1.0, "#d8f0fc")]
CLOUD = ("#ffffff", "#d6e4f6", "#8aa6d4")
SEA_FAR, SEA_NEAR, ISLAND, SPARKLE = "#4a8ed6", "#1e5aa8", "#5a86b0", "#f4fbff"
WALL, WALL_LOW, FLOOR, FRAME, FRAME_LIGHT = "#6e6a86", "#57536e", "#4a3c3c", "#e8e6ee", "#ffffff"
CURTAIN = "#f2f6fc"
RIM = "#e6f6ff"

INK = ch.Ink(body_shadow=0.62, hair_shadow=0.55, light_opacity=0.2).lit_from(BACK_LIGHT, BACK_LIGHT_3D)
WOMAN = ch.restyle(ch.FEMALE, face=faces.FEMALE_SHARP, hair=hairstyles.LONG_STRAIGHT,
                   hair_color=hairstyles.HAIR_COLORS["silver"])
BLOUSE = garment.casual_shirt(shirt="#dfe7f2", pants="#34405e", shoes="#2a2a30")


def make_woman():
    """창 쪽(화면 안쪽 오른쪽)을 보고 선 3/4 뒷모습. 고개를 관찰자 쪽으로 조금 돌려 볼과 속눈썹이 보인다."""
    return ch.place(WOMAN, PELVIS, UNIT, TURN, elevation=2.0, head_pitch=6.0, ink=INK, outfit=BLOUSE, head=3.0,
                    head_turn=-15.0,
                    arm_l=(8.0, 4.0), arm_r=(9.0, 5.0), leg_l=(4.0, 1.0), leg_r=(3.0, 0.0))


# ---------- 방과 창 ----------

def paint_room(cv):
    """창 자리를 뺀 벽과 바닥. 창밖을 먼저 그린 뒤 덮어 창 밖으로 삐져나온 구름을 가린다."""
    x0, y0, x1, y1 = WINDOW
    wall = cv.full() - cv.shape(g.rect(x0, y0, x1 - x0, y1 - y0))
    cv.fill(wall, Linear([WALL, WALL_LOW], (0, 0), (0, HEIGHT)))
    cv.fill(cv.shape(g.rect(0, 960, WIDTH, HEIGHT - 960)), FLOOR)


def paint_view(cv, rng):
    """창밖: 하늘, 적란운, 수평선의 섬, 바다, 물비늘."""
    x0, y0, x1, y1 = WINDOW
    glass = cv.shape(g.rect(x0, y0, x1 - x0, y1 - y0))
    cv.fill(glass, Linear(SKY, (0, y0), (0, HORIZON_Y)))
    for cx, base, width, height in ((520, 420, 620, 300), (1180, 470, 420, 200), (900, 300, 300, 120)):
        motifs.cumulus(cv, cx, base, width, height, light=(0.3, -0.9), palette=CLOUD, puffs=60, rng=rng)
    island = motifs.ridge(860, 1260, HORIZON_Y, 50, roughness=0.6, rng=rng)
    cv.fill(cv.shape(np.vstack([island, [(1260, HORIZON_Y + 2), (860, HORIZON_Y + 2)]])), ISLAND)
    sea = cv.shape(g.rect(x0, HORIZON_Y, x1 - x0, y1 - HORIZON_Y))
    cv.fill(sea, Linear([SEA_FAR, SEA_NEAR], (0, HORIZON_Y), (0, y1)))
    for _ in range(140):
        t = rng.random() ** 1.6
        y = HORIZON_Y + 6 + t * (y1 - HORIZON_Y - 10)
        x = rng.uniform(x0, x1)
        length = 6 + 40 * t
        cv.fill(cv.shape(g.ellipse(x, y, length, 1.2 + 2.5 * t)), SPARKLE, opacity=0.4 + 0.4 * rng.random(),
                clip=sea)
    cv.fill(glass, "#ffffff", opacity=0.08)


def paint_frame(cv):
    """창틀, 가운데 창살 2개, 가로살 1개, 창턱."""
    x0, y0, x1, y1 = WINDOW
    outer = cv.shape(g.rect(x0 - 28, y0 - 28, x1 - x0 + 56, y1 - y0 + 56)) - cv.shape(g.rect(x0, y0, x1 - x0, y1 - y0))
    cv.fill(outer, FRAME)
    for x in np.linspace(x0, x1, 4)[1:-1]:
        cv.fill(cv.shape(g.rect(x - 9, y0, 18, y1 - y0)), FRAME)
        cv.fill(cv.shape(g.rect(x - 9, y0, 4, y1 - y0)), FRAME_LIGHT)
    cv.fill(cv.shape(g.rect(x0, y0 + 230, x1 - x0, 14)), FRAME)
    cv.fill(cv.shape(g.rect(x0 - 50, y1 + 20, x1 - x0 + 100, 30)), FRAME)
    cv.fill(cv.shape(g.rect(x0 - 50, y1 + 50, x1 - x0 + 100, 12)), WALL_LOW)


def paint_curtain(cv):
    """창 왼쪽에 모아 둔 얇은 커튼. 바다가 비치도록 반투명하게 겹친다."""
    x0, y0, _, y1 = WINDOW
    for offset, opacity in ((0.0, 0.55), (60.0, 0.4), (120.0, 0.3)):
        left = [(x0 - 40 + offset, y0 - 30), (x0 + offset - 10, y0 + 300), (x0 + offset + 20, y0 + 600),
                (x0 + offset, y1 + 60)]
        right = [(x0 + offset + 100, y1 + 60), (x0 + offset + 130, y0 + 600), (x0 + offset + 90, y0 + 300),
                 (x0 + offset + 70, y0 - 30)]
        cv.fill(cv.shape(g.spline(left + right, closed=True, corners=(0, 3, 4, 7)), soft=4), CURTAIN, opacity=opacity)


# ---------- 인물 ----------

def paint_person(scale, seed, model):
    layer = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    ch.paint_figure(layer, model)
    anime.rim_light(layer, BACK_LIGHT, width=6.0, tint=RIM, opacity=0.9)
    return layer


def main(out_dir="out", scale=1.0, seed=191):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_view(cv, rng)
    paint_room(cv)
    paint_frame(cv)
    paint_curtain(cv)
    woman = make_woman()
    cv.paste(paint_person(scale, seed, woman))
    x0, y0, x1, y1 = WINDOW
    cv.fill(cv.shape(g.ellipse((x0 + x1) / 2, y0 + 300, 760, 420), soft=260), "#ffffff", opacity=0.14,
            blend=Blend.SCREEN)
    io.save(cv.guide_image(), out_dir / "window_1_guide.png")
    image = anime.finish(cv, diffusion=0.24, bloom=0.4, shadows="#2a2a6a", highlights="#f4fbff", grade_amount=0.1)
    image = post.light_gradient(image, "#ffffff", (0.5, 0.2), (0.5, 0.9), strength=0.08)
    return io.save(post.vignette(image, strength=0.2), out_dir / "anime_long_hair_window.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
