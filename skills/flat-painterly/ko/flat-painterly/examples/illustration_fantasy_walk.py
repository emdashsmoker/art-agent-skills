"""일러스트풍 예제: 해 질 녘 들길을 손잡고 걷는 두 여행자(판타지 의상, 투샷).

마법사는 로브와 망토에 지팡이를 들고, 검사는 가벼운 갑옷과 망토에 칼을 찼다. 둘은 3/4 앞을 보며 같은 발로 걷고
안쪽 손은 stage.reach로 둘 사이의 한 점에서 맞잡는다. 망토 자락은 걸음 반대쪽으로 날린다.
공정: 하늘과 구름 → 먼 산과 들 → 길 → 먼 사람(검사) → 가까운 사람(마법사) → 지팡이 → 인쇄 질감 패스.
실행: python illustration_fantasy_walk.py [출력폴더] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, figure, garment, io, motifs  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import illustration  # noqa: E402

WIDTH, HEIGHT = 2200, 1500
STAGE = Stage(origin=(1050.0, 1390.0), unit=150.0, elevation=6.0)
TURN = 38.0
HORIZON_Y = 930.0
LATERAL = np.array([np.cos(np.deg2rad(TURN)), 0.0, np.sin(np.deg2rad(TURN))])   # 몸의 오른쪽 방향(세계)
FORWARD = np.array([np.sin(np.deg2rad(TURN)), 0.0, -np.cos(np.deg2rad(TURN))])  # 몸의 앞 방향(세계)

# 제한 팔레트: 저녁 하늘의 살구색과 보라, 들판의 청록, 길의 크림, 가장 어두운 남색.
SKY_HIGH, SKY_LOW, SUN = "#5d4a7a", "#f2a66b", "#fff0c4"
CLOUD = ("#ffd9a8", "#e59a7a", "#9a6a8a")
MOUNTAIN_FAR, MOUNTAIN_NEAR = "#8a7aa0", "#5f6f8a"
FIELD, FIELD_DARK, GRASS = "#4f8a7a", "#2f5a5a", ("#6aa08a", "#3f7a6a", "#2a5050")
PATH, PATH_EDGE = "#efd9b0", "#c9a87a"
STAFF, STAFF_LIGHT, GEM = "#5a3a2a", "#8a6040", "#7ad0e0"
SCABBARD, HILT = "#3a2a24", "#c9a24a"
PRINT_INK = ch.Ink(light=(0.6, -0.5), light3d=np.array([0.55, -0.5, -0.67]) / np.linalg.norm([0.55, -0.5, -0.67]),
                   line_width=2.4, line_opacity=0.9, body_shadow=0.32, face_shadow=0.16, hair_shadow=0.4,
                   light_opacity=0.35)

MAGE = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, hair="#e8d8b0", hair_shade="#b8a070", hair_light="#fff4d8",
                                          line_hair="#5a4428", iris=("#1a3a4a", "#2a7a8a", "#8ad0d0")))
KNIGHT = replace(ch.MALE, palette=replace(ch.MALE.palette, hair="#7a3a24", hair_shade="#4a2014", hair_light="#b86a40",
                                          line_hair="#2a1008"))
MAGE_OUTFIT = garment.mage_robe(robe="#3f5f8f", cape="#7a3048", sash="#e2b85a", boots="#5a3e2a", cape_drift=0.9)
KNIGHT_OUTFIT = garment.light_armor(tunic="#4f7a5a", metal="#8d98a6", leather="#7a5032", cape="#2f4060",
                                    legs="#3a3432", boots="#4a3022", cape_drift=1.0)
STRIDE = dict(swing={"leg_l": (20.0, 4.0), "leg_r": (-14.0, -30.0)}, foot_pitch={"r": 18.0}, lean=3.0)


def make_people():
    """검사가 오른쪽 뒤(먼 쪽), 마법사가 왼쪽 앞(가까운 쪽). 맞잡는 손은 둘 사이 엉덩이 높이에서 만난다."""
    knight_at = LATERAL * 0.95 + FORWARD * 0.1
    mage_at = -LATERAL * 0.95
    clasp = (knight_at + mage_at) / 2.0 + FORWARD * 0.45 + np.array([0.0, -3.0, 0.0])
    knight_swing = dict(STRIDE["swing"], arm_r=(-18.0, -6.0))
    mage_swing = dict(STRIDE["swing"], arm_l=(10.0, 38.0))
    knight = STAGE.place(KNIGHT, knight_at[0], knight_at[2], TURN, outfit=KNIGHT_OUTFIT, ink=PRINT_INK, head=3.0,
                         head_turn=-12.0, reach={"arm_l": clasp - LATERAL * 0.12}, arm_r=(12.0, 6.0),
                         swing=knight_swing, foot_pitch=STRIDE["foot_pitch"], lean=STRIDE["lean"], grips=("l",))
    mage = STAGE.place(MAGE, mage_at[0], mage_at[2], TURN, outfit=MAGE_OUTFIT, ink=PRINT_INK, head=-4.0,
                       head_turn=14.0, reach={"arm_r": clasp + LATERAL * 0.12}, arm_l=(30.0, 16.0), swing=mage_swing,
                       foot_pitch=STRIDE["foot_pitch"], lean=STRIDE["lean"], grips=("r", "l"))
    return knight, mage


# ---------- 들판 ----------

def paint_land(cv, rng):
    cv.fill(cv.full(), Linear([SKY_HIGH, SKY_LOW], (0, 0), (0, HORIZON_Y)), grain=1.0)
    cv.fill(cv.shape(g.ellipse(1700, HORIZON_Y - 40, 150, 150)), SUN, grain=1.0)
    for cx, base, width, height in ((420, 380, 520, 170), (1300, 300, 640, 190), (1900, 520, 420, 140)):
        motifs.cumulus(cv, cx, base, width, height, light=(0.7, 0.4), palette=CLOUD, rng=rng)
    for color, base, height, roughness in ((MOUNTAIN_FAR, HORIZON_Y + 10, 300, 0.5),
                                           (MOUNTAIN_NEAR, HORIZON_Y + 50, 150, 0.6)):
        top = motifs.ridge(-20, WIDTH + 20, base, height, roughness=roughness, rng=rng)
        outline = np.vstack([top, [(WIDTH + 20, HORIZON_Y + 120), (-20, HORIZON_Y + 120)]])
        cv.fill(cv.shape(outline), color, grain=1.0)
    field = cv.shape(g.rect(0, HORIZON_Y + 50, WIDTH, HEIGHT - HORIZON_Y - 50))
    cv.fill(field, Linear([FIELD, FIELD_DARK], (0, HORIZON_Y), (0, HEIGHT)), grain=1.0)
    # 길: 지평선 왼쪽에서 나와 화면 오른쪽 아래로 넓어진다. 두 사람이 걷는 방향과 같다.
    left = [(WIDTH + 200, HEIGHT), (WIDTH - 520, 1240), (WIDTH - 1100, 1080), (WIDTH - 1560, 1000),
            (WIDTH - 1820, HORIZON_Y + 56)]
    right = [(WIDTH - 1880, HORIZON_Y + 56), (WIDTH - 1700, 1010), (WIDTH - 1400, 1120), (WIDTH - 1000, 1300),
             (WIDTH - 700, HEIGHT)]
    road = cv.shape(g.spline(left + right, closed=True, corners=(0, 4, 5, 9)))
    cv.fill(road, PATH, grain=1.0)
    cv.fill(cv.contour(road, 3.0), PATH_EDGE)
    motifs.grass(cv, (0, WIDTH), (HORIZON_Y + 120, HEIGHT), 260, list(GRASS), blade=(10.0, 30.0), rng=rng)


def paint_staff(cv, mage):
    """지팡이: 마법사의 바깥손 주먹을 지나 땅에서 머리 위까지. 손가락 뒤로 지나가고 끝에 빛나는 돌."""
    fist = STAGE.fist_world(mage, "l")
    foot = fist + np.array([0.0, 3.0, 0.0]) + FORWARD * 0.5
    top = fist + (fist - foot) / np.linalg.norm(fist - foot) * 3.4
    line = STAGE.project([foot, top])
    hand = figure.shape_of(cv, ch.choose_hand(mage, "l")[0].paths())
    staff = cv.shape(*g.ribbon(g.densify(line, 8), 11.0))
    cv.fill(staff - hand, STAFF)
    cv.stroke(line, STAFF_LIGHT, width=3, opacity=0.7, clip=staff - hand)
    gem = STAGE.point(*top)
    cv.fill(cv.shape(g.ellipse(gem[0], gem[1], 22, 30)), GEM)
    cv.fill(cv.shape(g.ellipse(gem[0], gem[1], 70, 70), soft=40), GEM, opacity=0.35)
    return line


def paint_sword(cv, knight):
    """등에 멘 검: 오른쪽 어깨 위로 손잡이가 솟고 칼집은 등 뒤로 비스듬히 내려간다. 검사보다 먼저 칠한다."""
    shoulder, hip = STAGE.joint_world(knight, "shoulder_r"), STAGE.joint_world(knight, "hip_l")
    back = -FORWARD * 0.45
    start = shoulder + np.array([0.0, -0.75, 0.0]) + back + LATERAL * 0.15
    end = hip + back + np.array([0.0, 0.4, 0.0])
    cv.stroke(STAGE.project([start, end]), SCABBARD, width=15, taper=(1.0, 0.8))
    guard = STAGE.project([start - LATERAL * 0.22, start + LATERAL * 0.22])
    cv.stroke(guard, HILT, width=8)
    grip = STAGE.project([start, start + (start - end) / np.linalg.norm(start - end) * 0.5])
    cv.stroke(grip, SCABBARD, width=9)
    cv.fill(cv.shape(g.ellipse(*grip[-1], 10, 10)), HILT)


def main(out_dir="out", scale=1.0, seed=97):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_land(cv, rng)
    knight, mage = make_people()
    for model in STAGE.far_first((knight, mage)):
        x, z = model.world[0], model.world[2]
        cv.fill(cv.shape(STAGE.ellipse((x - 0.3, z + 0.3), 1.3, 0.0, radius_z=0.6), soft=14), FIELD_DARK, opacity=0.35)
    paint_sword(cv, knight)
    ch.paint_figure(cv, knight)
    ch.paint_figure(cv, mage)
    paint_staff(cv, mage)
    io.save(cv.guide_image(), out_dir / "fantasy_1_flat_guide.png")
    return io.save(illustration.render(cv), out_dir / "illustration_fantasy_walk.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
