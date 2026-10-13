"""애니메풍 예제: 해 질 녘 빈 승강장에 선 긴 생머리 여성(전신, 3/4 앞모습).

얼굴은 부드러운 인상(faces.FEMALE_SOFT), 머리는 긴 생머리(hairstyles.LONG_STRAIGHT), 머리색은 검정이다.
긴 머리의 앞 다발은 어깨를 타고 코트 앞으로, 뒤 다발은 등 뒤로 흐른다(drape). 왼쪽 낮은 해가 머리와 코트 윤곽을 데운다.
승강장은 1점 투시로 그리고 인물의 발이 닿는 깊이에서 투시 배율과 무대 배율을 맞춘다.
공정: 저녁 하늘과 구름 → 먼 동네 실루엣 → 승강장 바닥, 점자 블록, 선로 → 울타리 → 전차선 기둥과 전선 → 가로등과 의자 →
인물(투명 층, 해 쪽 빛 테두리) → 발밑 그림자 → 촬영 마감.
실행: python anime_long_hair_platform.py [출력폴더] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Perspective, faces, garment, hairstyles, io, motifs, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1200, 1600
HORIZON_Y = 560.0
VIEW = Perspective((960.0, HORIZON_Y), eye_height=1.6, focal=900.0)   # 승강장(미터). 소실점은 오른쪽
FEET_Z = 1.53                       # 인물이 선 깊이. 이 깊이의 투시 배율이 무대 배율(머리 높이 135)과 같다
STAGE = Stage(origin=(520.0, 1500.0), unit=135.0, elevation=4.0)
TURN = 20.0
PLATFORM_EDGE, PLATFORM_BACK = 1.6, -5.5      # 승강장 가장자리와 뒤 울타리의 x(미터)
LAMP_X, LAMP_HEIGHT = -2.4, 4.2
LAMP_DEPTHS = (6.0, 13.0, 20.0, 27.0, 34.0, 41.0, 48.0)
POLE_X, POLE_DEPTHS = 5.2, (6.0, 18.0, 30.0, 42.0, 54.0)
SUN_LIGHT, SUN_LIGHT_3D = (-0.85, -0.3), (-0.75, -0.3, -0.35)

# 팔레트: 보라에서 살구로 넘어가는 저녁 하늘이 지배색. 크림색 코트와 검은 긴 머리가 대비를 이루고
# 노란 점자 블록과 해 쪽 빛 테두리가 따뜻한 강조색이다.
SKY = [(0.0, "#2e3170"), (0.45, "#7a5a92"), (0.8, "#e48a7a"), (1.0, "#ffc08a")]
CLOUD = ("#ffd2a8", "#d88a8a", "#6a5a8a")
TOWN, TOWN_LIGHT = "#4a4064", "#ffd890"
POLE, LAMP, BENCH, PILLAR_SHADE = "#3a3448", "#fff4dc", "#6a5468", "#5a5068"
FLOOR_NEAR, FLOOR_FAR, TACTILE, EDGE = "#a89aa0", "#d8b8a8", "#f0c040", "#f4ece4"
FLOOR_LINE = "#8a7c88"
RAIL_BED, RAIL, METAL = "#4a4050", "#c8b0a0", "#2a2638"
SUN_GLOW = "#ffb070"

INK = ch.Ink(body_shadow=0.4, hair_shadow=0.45, light_opacity=0.5).lit_from(SUN_LIGHT, SUN_LIGHT_3D)
WOMAN = ch.restyle(ch.FEMALE, face=faces.FEMALE_SOFT, hair=hairstyles.LONG_STRAIGHT,
                   hair_color=hairstyles.HAIR_COLORS["black"])
WOMAN = replace(WOMAN, palette=replace(WOMAN.palette, iris=("#2a1a1a", "#6a3a2a", "#d89060")))
COAT = garment.long_coat(coat="#e6dccb", scarf="#5a6fa0", legs="#3a3448", boots="#4a3428", length=2.2,
                         scarf_tail=False)


def make_woman():
    """오른쪽 선로 쪽(전차가 올 쪽)으로 고개를 돌리고 선 자세."""
    return STAGE.place(WOMAN, 0.0, 0.0, TURN, outfit=COAT, ink=INK, head=-3.0, head_turn=22.0, head_pitch=-2.0,
                       arm_l=(9.0, 5.0), arm_r=(8.0, 4.0), leg_l=(4.0, 1.0), leg_r=(3.0, 0.0))


# ---------- 배경 ----------

def paint_sky(cv, rng):
    cv.fill(cv.full(), Linear(SKY, (0, 0), (0, HORIZON_Y)))
    cv.fill(cv.shape(g.ellipse(-80, HORIZON_Y - 40, 620, 300), soft=260), SUN_GLOW, opacity=0.55, blend=Blend.SCREEN)
    for cx, base, width, height in ((280, 300, 520, 150), (900, 220, 420, 120), (700, 420, 380, 90)):
        motifs.cumulus(cv, cx, base, width, height, light=(-0.9, 0.3), palette=CLOUD, puffs=40, rng=rng)


def paint_town(cv, rng):
    """지평선 위의 먼 동네 실루엣. 지붕선이 끊기지 않게 이어 붙이고 하늘빛에 묻히도록 옅게 칠한다."""
    x, points = 560.0, [(560.0, HORIZON_Y + 4)]
    while x < WIDTH + 40:
        width, height = rng.uniform(20.0, 70.0), rng.uniform(6.0, 34.0)
        points += [(x, HORIZON_Y - height), (x + width, HORIZON_Y - height)]
        x += width
    points.append((x, HORIZON_Y + 4))
    skyline = cv.shape(g.polygon(points))
    cv.fill(skyline, TOWN, opacity=0.75)
    for _ in range(40):
        wx, wy = rng.uniform(570.0, WIDTH), HORIZON_Y - rng.uniform(3.0, 24.0)
        cv.fill(cv.shape(g.rect(wx, wy, 2.5, 2.5)), TOWN_LIGHT, opacity=0.8, clip=skyline)


def paint_lamps(cv):
    """지붕 없는 승강장의 가로등 줄. 깊이로 작아지며 막 켜진 흰 등이 소실점으로 모인다."""
    for z in reversed(LAMP_DEPTHS):
        base, top = VIEW.project(LAMP_X, 0.0, z), VIEW.project(LAMP_X, LAMP_HEIGHT, z)
        width = max(16.0 / z * 4.0, 1.2)
        cv.stroke([base, top], POLE, width=width)
        head = VIEW.project(LAMP_X + 0.5, LAMP_HEIGHT - 0.1, z)
        cv.stroke([top, head], POLE, width=width * 0.7)
        radius = max(VIEW.scale_at(z) * 0.18, 2.0)
        cv.fill(cv.shape(g.ellipse(head[0], head[1] + radius * 0.4, radius, radius * 0.45)), LAMP)
        cv.fill(cv.shape(g.ellipse(head[0], head[1] + radius, radius * 4, radius * 3), soft=radius * 2.5), LAMP,
                opacity=0.35, blend=Blend.SCREEN)


def paint_fence(cv):
    """승강장 뒤쪽의 낮은 울타리: 기둥과 가로대 두 줄."""
    for height in (0.55, 1.1):
        cv.stroke(VIEW.path([(PLATFORM_BACK, height, 0.8), (PLATFORM_BACK, height, 120.0)]), POLE, width=2.4)
    for z in np.arange(1.5, 60.0, 2.5):
        cv.stroke([VIEW.project(PLATFORM_BACK, 0.0, z), VIEW.project(PLATFORM_BACK, 1.15, z)], POLE,
                  width=max(10.0 / z * 3.0, 1.0))


def paint_bench(cv):
    """인물 뒤 왼쪽의 빈 의자."""
    x0, x1, z0, z1 = -3.6, -3.1, 9.0, 12.0
    seat = VIEW.path([(x0, 0.45, z0), (x1, 0.45, z0), (x1, 0.45, z1), (x0, 0.45, z1)])
    cv.fill(cv.shape(seat), BENCH)
    back = VIEW.side_wall(x0, z0, z1, 0.55, 0.95)
    cv.fill(cv.shape(back), BENCH)
    for z in (z0 + 0.2, z1 - 0.2):
        cv.stroke([VIEW.project(x1 - 0.05, 0.0, z), VIEW.project(x1 - 0.05, 0.45, z)], POLE, width=3.0)


def paint_platform(cv):
    """승강장 바닥, 점자 블록, 흰 가장자리 선, 선로 바닥과 레일, 건너편 승강장."""
    floor = cv.shape(VIEW.ground(PLATFORM_BACK, PLATFORM_EDGE, 0.6, 120.0))
    cv.fill(floor, Linear([FLOOR_FAR, FLOOR_NEAR], (0, HORIZON_Y), (0, HEIGHT)))
    # 바닥 판의 이음매: 깊이 1.5미터마다 가로선. 멀수록 촘촘해져 바닥이 눕는다.
    for z in np.arange(1.5, 60.0, 1.5):
        cv.stroke(VIEW.path([(PLATFORM_BACK, 0.0, z), (PLATFORM_EDGE, 0.0, z)]), FLOOR_LINE, width=1.2,
                  opacity=min(0.6, 6.0 / z))
    cv.fill(cv.shape(VIEW.ground(PLATFORM_EDGE - 0.75, PLATFORM_EDGE - 0.45, 0.6, 120.0)), TACTILE)
    cv.fill(cv.shape(VIEW.ground(PLATFORM_EDGE - 0.12, PLATFORM_EDGE, 0.6, 120.0)), EDGE)
    side = VIEW.side_wall(PLATFORM_EDGE, 0.6, 120.0, -1.1, 0.0)
    cv.fill(cv.shape(side), RAIL_BED)
    cv.fill(cv.shape(VIEW.ground(PLATFORM_EDGE, 9.0, 0.6, 120.0, y=-1.1)), RAIL_BED)
    for x in (2.8, 4.3):
        cv.stroke(VIEW.path([(x, -1.0, 2.0), (x, -1.0, 120.0)]), RAIL, width=3.0)
    cv.fill(cv.shape(VIEW.ground(9.0, 16.0, 2.0, 120.0)), FLOOR_FAR)
    cv.fill(cv.shape(VIEW.side_wall(9.0, 2.0, 120.0, -1.1, 0.0)), PILLAR_SHADE)


def paint_catenary(cv):
    """선로 건너편의 전차선 기둥과 처진 전선 두 가닥."""
    tops = []
    for z in POLE_DEPTHS:
        base, top = VIEW.project(POLE_X, -1.1, z), VIEW.project(POLE_X, 5.8, z)
        cv.stroke([base, top], METAL, width=max(26.0 / z * 4.0, 1.5))
        arm_end = VIEW.project(3.4, 5.5, z)
        cv.stroke([VIEW.project(POLE_X, 5.5, z), arm_end], METAL, width=max(14.0 / z * 4.0, 1.0))
        tops.append(z)
    for height in (5.3, 5.0):
        for near, far in zip(tops[:-1], tops[1:]):
            a, b = np.array(VIEW.project(3.4, height, near)), np.array(VIEW.project(3.4, height, far))
            middle = (a + b) / 2 + np.array([0.0, np.linalg.norm(b - a) * 0.04])
            cv.stroke(g.spline([a, middle, b], closed=False), METAL, width=1.6)


# ---------- 인물 ----------

def paint_person(scale, seed, model):
    layer = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    ch.paint_figure(layer, model)
    anime.rim_light(layer, SUN_LIGHT, width=5.0, tint=SUN_GLOW, opacity=0.85)
    return layer


def paint_shadow(cv):
    """해 반대쪽(오른쪽 뒤)으로 길게 눕는 발밑 그림자."""
    foot = np.array(STAGE.point(0.0, 0.0, 0.0))
    shadow = g.polygon([foot + (-50, 8), foot + (50, -4), foot + (420, -80), foot + (360, -50)])
    cv.fill(cv.shape(shadow, soft=12), "#4a3a5a", opacity=0.5, blend=Blend.MULTIPLY)
    cv.fill(cv.shape(g.ellipse(foot[0], foot[1] + 4, 110, 18), soft=10), "#3a2a4a", opacity=0.5, blend=Blend.MULTIPLY)


def main(out_dir="out", scale=1.0, seed=181):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv, rng)
    paint_town(cv, rng)
    paint_platform(cv)
    paint_fence(cv)
    paint_catenary(cv)
    paint_lamps(cv)
    paint_bench(cv)
    paint_shadow(cv)
    woman = make_woman()
    cv.paste(paint_person(scale, seed, woman))
    io.save(cv.guide_image(), out_dir / "platform_1_guide.png")
    image = anime.finish(cv, diffusion=0.2, bloom=0.35, shadows="#2a2a5a", highlights="#ffe2c0", grade_amount=0.12)
    image = post.light_gradient(image, SUN_GLOW, (0.0, 0.35), (0.7, 0.6), strength=0.18)
    return io.save(post.vignette(image, strength=0.22), out_dir / "anime_long_hair_platform.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
