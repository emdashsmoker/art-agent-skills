"""애니메풍 예제: 초여름 공원길을 손잡고 걸어오는 두 사람(투샷, 긴 머리 둘).

그녀는 성숙한 인상에 분홍 긴 생머리, 그는 온화한 인상에 남색 긴 머리다. 그녀의 앞 다발은 어깨를 타고 니트 앞으로,
그의 뒷머리는 목덜미를 덮는다(drape). 두 사람의 자리, 보폭, 맞잡은 손은 watercolor_street_walk.py에서 검증한 값이며
칠하기 전에 stage.collisions로 팔이 상대 몸을 뚫지 않는지 확인한다.
공정: 하늘과 적운 → 먼 숲 → 잔디와 길 → 길 양옆 나무(먼 것부터) → 나뭇잎 그늘과 햇빛 얼룩 → 가로등 → 발밑 그림자 →
그녀(맞잡은 팔은 미룸) → 그 → 그녀의 맞잡은 팔 → 촬영 마감.
실행: python anime_long_hair_walk.py [출력폴더] [scale]
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

WIDTH, HEIGHT = 2000, 1300
HORIZON_Y = 330.0
VIEW = Perspective((WIDTH * 0.5, HORIZON_Y), eye_height=1.6, focal=900.0)   # 공원(미터)
STAGE = Stage(origin=(1000.0, 1235.0), unit=125.0, elevation=3.0)
TURN = -20.0
HER_AT, HIM_AT = (-1.05, 0.05), (1.05, -0.15)
CLASP = np.array([-0.1, -4.25, -0.35])
CLASP_GAP = np.array([0.1, 0.0, 0.0])
INNER_POLE = (0.0, 1.0, 0.3)
STRIDE_HER = dict(swing={"leg_r": (12.0, 4.0), "leg_l": (-10.0, -16.0)}, leg_l=(4.0, 1.0), leg_r=(3.0, 0.0),
                  foot_pitch={"l": 12.0})
STRIDE_HIM = dict(swing={"leg_l": (12.0, 4.0), "leg_r": (-10.0, -16.0)}, leg_l=(3.0, 0.0), leg_r=(4.0, 1.0),
                  foot_pitch={"r": 12.0})
TREE_X, TREE_DEPTHS = 5.0, (5.0, 10.0, 16.0, 23.0, 31.0, 40.0, 52.0, 66.0)
LAMP_X, LAMP_DEPTHS = 3.0, (8.0, 20.0, 32.0, 44.0)
PATH_HALF = 2.4
SUN = (-0.6, -0.8)

# 팔레트: 초여름 잎의 초록과 하늘의 파랑이 지배색. 크림 길과 햇빛 얼룩이 밝은 무리이고
# 그녀의 분홍 머리가 초록의 보색 쪽 강조색이다.
SKY = [(0.0, "#3f86dc"), (1.0, "#cfeafb")]
CLOUD = ("#ffffff", "#dce8f6", "#9ab4d8")
LEAF = ("#9cd27a", "#5fa24e", "#2f6a3a")
TRUNK, TRUNK_SHADE = "#6a4a3a", "#3e2a22"
GRASS, GRASS_FAR = "#5aa04c", "#8cc472"
PATH, PATH_FAR, PATH_EDGE = "#e8dcc4", "#f2ead8", "#c4b08e"
LEAF_SHADOW, SUN_SPOT = "#6a8a6a", "#fff4c8"
POLE, LAMP = "#3a4048", "#f4f0e0"

HER = ch.restyle(ch.FEMALE, face=faces.FEMALE_MATURE, hair=hairstyles.LONG_STRAIGHT,
                 hair_color=hairstyles.HAIR_COLORS["pink"])
HER = replace(HER, palette=replace(HER.palette, iris=("#3a1a2a", "#9a4a6a", "#f0a0b8")))
HIM = ch.restyle(ch.MALE, face=faces.MALE_GENTLE, hair=hairstyles.MALE_LONG,
                 hair_color=hairstyles.HAIR_COLORS["navy"])
HER_OUTFIT = garment.casual_knit(knit="#f4ecd8", pants="#5a6a8a", shoes="#e8e2d6")
HIM_OUTFIT = garment.casual_shirt(shirt="#9cc0dc", pants="#3c4250", shoes="#2a2a30")


def make_people():
    """같은 보폭으로 걸으며 안쪽 손을 맞잡은 두 사람. 두 팔이 서로의 몸을 뚫지 않는지 확인한다."""
    him = STAGE.place(HIM, HIM_AT[0], HIM_AT[1], TURN, outfit=HIM_OUTFIT, head=-5.0, head_turn=-18.0, head_pitch=6.0,
                      fists={"arm_l": CLASP + CLASP_GAP}, poles={"arm_l": INNER_POLE}, arm_r=(10.0, 4.0),
                      grips=("l",), **STRIDE_HIM)
    her = STAGE.place(HER, HER_AT[0], HER_AT[1], TURN, outfit=HER_OUTFIT, head=6.0, head_turn=16.0, head_pitch=2.0,
                      fists={"arm_r": CLASP - CLASP_GAP}, poles={"arm_r": INNER_POLE}, arm_l=(9.0, 5.0),
                      grips=("r",), palm_out=("r",), in_front=("arm_r",), **STRIDE_HER)
    hits = STAGE.collisions([her, him])
    assert not hits, f"팔이 상대 몸을 뚫음: {hits}"
    return her, him


# ---------- 공원 ----------

def paint_sky(cv, rng):
    cv.fill(cv.full(), Linear(SKY, (0, 0), (0, HORIZON_Y + 60)))
    for cx, base, width, height in ((520, 200, 560, 200), (1500, 160, 480, 160)):
        motifs.cumulus(cv, cx, base, width, height, light=SUN, palette=CLOUD, puffs=50, rng=rng)


def paint_ground(cv):
    """잔디 바탕과 소실점으로 좁아지는 길, 길 가장자리 돌."""
    cv.fill(cv.shape(g.rect(0, HORIZON_Y, WIDTH, HEIGHT - HORIZON_Y)), Linear([GRASS_FAR, GRASS], (0, HORIZON_Y),
                                                                              (0, HEIGHT)))
    path = cv.shape(VIEW.ground(-PATH_HALF, PATH_HALF, 0.8, 200.0))
    cv.fill(path, Linear([PATH_FAR, PATH], (0, HORIZON_Y), (0, HEIGHT)))
    for x in (-PATH_HALF, PATH_HALF):
        cv.fill(cv.shape(VIEW.ground(x - 0.12, x + 0.12, 0.8, 200.0)), PATH_EDGE)


def paint_tree(cv, rng, x, z):
    """줄기와 잎 덩어리 하나. 깊이로 크기를 정한다."""
    scale = VIEW.scale_at(z)
    base, top = VIEW.project(x, 0.0, z), VIEW.project(x, 3.2, z)
    trunk = cv.shape(*g.ribbon(g.densify(np.array([base, top]), 8), (0.42 * scale, 0.26 * scale)))
    cv.fill(trunk, TRUNK)
    cv.fill(cv.form_shadow(trunk, SUN, 0.45), TRUNK_SHADE)
    crown = VIEW.project(x, 4.6, z)
    motifs.canopy(cv, crown[0], crown[1], 5.0 * scale, 3.6 * scale, light=SUN, palette=LEAF, puffs=36, rng=rng)


def paint_trees(cv, rng):
    for z in reversed(TREE_DEPTHS):
        for side in (-1.0, 1.0):
            paint_tree(cv, rng, side * TREE_X + rng.uniform(-0.4, 0.4), z + rng.uniform(-1.0, 1.0))


def paint_far_trees(cv, rng):
    """지평선을 막는 먼 숲. 하늘빛을 섞어 흐리게 칠한 잎 덩어리 줄."""
    far = tuple(color for color in ("#b4d8a4", "#8ab88a", "#6a9a7a"))
    for x in np.arange(-60.0, WIDTH + 60.0, 70.0):
        motifs.canopy(cv, x + rng.uniform(-20, 20), HORIZON_Y - rng.uniform(10, 30), rng.uniform(110, 170),
                      rng.uniform(60, 100), light=SUN, palette=far, puffs=12, rng=rng)


def paint_dapple(cv, rng):
    """길 위의 나뭇잎 그늘과 그 사이로 떨어진 햇빛 얼룩."""
    path = cv.shape(VIEW.ground(-PATH_HALF, PATH_HALF, 0.8, 200.0))
    for _ in range(26):
        z = 1.0 + rng.random() ** 1.5 * 40.0
        x = rng.uniform(-PATH_HALF, PATH_HALF)
        center, scale = VIEW.project(x, 0.0, z), VIEW.scale_at(z)
        cv.fill(cv.shape(g.ellipse(center[0], center[1], scale * 1.4, scale * 0.25), soft=scale * 0.2), LEAF_SHADOW,
                opacity=0.35, blend=Blend.MULTIPLY, clip=path)
    for _ in range(40):
        z = 1.0 + rng.random() ** 1.5 * 30.0
        x = rng.uniform(-PATH_HALF, PATH_HALF)
        center, scale = VIEW.project(x, 0.0, z), VIEW.scale_at(z)
        cv.fill(cv.shape(g.ellipse(center[0], center[1], scale * 0.25, scale * 0.06), soft=scale * 0.05), SUN_SPOT,
                opacity=0.7, blend=Blend.SCREEN, clip=path)


def paint_lamps(cv):
    for z in reversed(LAMP_DEPTHS):
        for side in (-1.0, 1.0):
            x = side * LAMP_X
            base, top = VIEW.project(x, 0.0, z), VIEW.project(x, 3.6, z)
            width = max(VIEW.scale_at(z) * 0.08, 1.2)
            cv.stroke([base, top], POLE, width=width)
            cv.fill(cv.shape(g.ellipse(top[0], top[1], width * 2.2, width * 2.6)), LAMP)


def paint_shadows(cv, models):
    """해 반대쪽(오른쪽 뒤)으로 눕는 발밑 그림자."""
    for model in models:
        x = model.body.joint("pelvis")[0]
        floor = STAGE.point(0.0, 0.0, model.world[2])[1]
        cv.fill(cv.shape(g.ellipse(x + 80, floor - 4, 230, 34), soft=14), "#4a5a4a", opacity=0.45, blend=Blend.MULTIPLY)


def main(out_dir="out", scale=1.0, seed=193):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv, rng)
    paint_far_trees(cv, rng)
    paint_ground(cv)
    paint_trees(cv, rng)
    paint_dapple(cv, rng)
    paint_lamps(cv)
    her, him = make_people()
    paint_shadows(cv, (her, him))
    ch.paint_figure(cv, her, defer=("arm_r",))
    ch.paint_figure(cv, him)
    ch.paint_deferred(cv, her, ("arm_r",))
    io.save(cv.guide_image(), out_dir / "walk_1_guide.png")
    image = anime.finish(cv, diffusion=0.2, bloom=0.3, shadows="#2a4a5a", highlights="#fff6dc", grade_amount=0.1)
    image = post.light_gradient(image, "#fff2c8", (0.0, 0.0), (0.6, 0.7), strength=0.14)
    return io.save(post.vignette(image, strength=0.18), out_dir / "anime_long_hair_walk.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
