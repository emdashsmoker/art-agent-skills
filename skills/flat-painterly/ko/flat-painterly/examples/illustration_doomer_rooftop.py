"""일러스트풍 예제(두머 분위기): 아파트 옥상에서 등 돌려 밤의 단지를 내려다보는 두 사람(투샷, 뒷모습).

단지는 solids 카메라로 높은 곳에서 내려다본 상자 패널 아파트 수십 채이고 켜진 창과 나트륨 가로등만 빛난다.
두 사람은 stage 무대에 뒷모습으로 서서 안쪽 손을 맞잡는다. 칠하기 전에 stage.collisions로 팔 관통을 확인한다.
색은 남색 계열 단계 색면과 점묘 그라데이션, 난색은 창 노랑과 가로등 주황 둘뿐이다. 분위기 값은 references/mood-doomer.md.
공정: 밤하늘 띠와 낮은 구름 → 먼 단지(상자, 켜진 창, 길의 가로등) → 옥상 바닥과 난간벽 → 안테나와 계단실 →
두 사람(뒷모습) → 인쇄 질감 패스.
실행: python illustration_doomer_rooftop.py [출력폴더] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, garment, io  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import illustration  # noqa: E402

WIDTH, HEIGHT = 1600, 1200
CITY_CAMERA = s3.Camera(eye=(0.0, 42.0, -30.0), target=(0.0, 10.0, 320.0), focal=1100.0, center=(800.0, 470.0))
CITY_LIGHT = (-0.3, 0.8, 0.5)         # 구름에 비친 도시 빛. 윗면과 먼 쪽 면이 조금 밝다
STAGE = Stage(origin=(800.0, 1130.0), unit=50.0, elevation=12.0)
HER_AT, HIM_AT = (-1.15, 0.0), (1.15, 0.05)   # 두 사람의 세계 (x, z). 맞잡은 두 팔이 서로 닿지 않을 만큼 띄운다
HER_TURN, HIM_TURN = 186.0, 174.0     # 뒷모습. 둘이 서로 쪽으로 6도씩 기운다
CLASP = np.array([0.0, -4.0, 0.3])     # 맞잡은 손(세계 좌표). 둘 사이 엉덩이 높이, 몸보다 조금 먼 쪽
CLASP_GAP = np.array([0.1, 0.0, 0.0])
INNER_POLE = (0.0, 1.0, 0.3)           # 안쪽 팔의 팔꿈치 방향. 바깥 성분 0으로 상대 쪽으로 꺾이지 않게 한다
PARAPET_Z, PARAPET_HEIGHT = 2.2, 3.0   # 두 사람 앞 난간벽의 깊이와 높이(머리 높이 단위)
BLOCK_ROWS = (48.0, 80.0, 118.0, 162.0, 215.0, 280.0, 360.0, 460.0, 590.0, 760.0)   # 동 줄의 깊이(미터)
FLOOR_HEIGHT_M = 2.8

# 제한 팔레트: 남색 단계 6색이 화면의 9할. 난색은 창 노랑과 가로등 주황뿐이다.
SKY_BANDS = ["#0c111c", "#111827", "#172033", "#1e2a3f", "#28344a"]
CLOUD_LOW, CLOUD_LIT = "#2a3346", "#5a4a4c"
BLOCK_TOP, BLOCK_WALL = "#3a4558", "#232c3b"
GROUND, ROAD = "#1a2230", "#141a24"
WINDOW_WARM, WINDOW_COLD, SODIUM = "#e9b86a", "#8fb3c9", "#f2a65a"
ROOF, ROOF_SNOW, PARAPET, PARAPET_TOP = "#262d39", "#5d6878", "#303a4a", "#4b5668"
METAL = "#0d1119"
PRINT_INK = ch.Ink(light=(0.2, -0.9), light3d=np.array([0.2, -0.8, 0.55]) / np.linalg.norm([0.2, -0.8, 0.55]),
                   line_width=2.0, line_opacity=0.85, body_shadow=0.5, face_shadow=0.2, hair_shadow=0.45,
                   light_opacity=0.3)

HER = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, skin="#d9b8a8", skin_shade="#8a7080", line_skin="#3a2a30",
                                         hair="#2a2024", hair_shade="#120e12", hair_light="#5a4650",
                                         line_hair="#0a080a"))
HIM = replace(ch.MALE, palette=replace(ch.MALE.palette, skin="#d4b09c", skin_shade="#86687a", line_skin="#36262a",
                                       hair="#1a1a20", hair_shade="#0a0a0e", hair_light="#44444e", line_hair="#060608"))
HER_COAT = garment.long_coat(coat="#4a4b5e", scarf="#7a6a5a", legs="#1e2230", boots="#1a1618", length=2.0,
                             scarf_tail=False)
HIM_COAT = garment.long_coat(coat="#2e3a46", scarf="#545c66", legs="#1a1e26", boots="#141214", length=1.6,
                             belt=False, scarf_tail=False)


def make_people():
    """나란히 서서 단지를 내려다보는 두 사람. 안쪽 손을 둘 사이에서 맞잡는다."""
    # 뒷모습이라 정면과 좌우가 바뀐다: 화면 왼쪽 그녀의 안쪽 손은 arm_l, 오른쪽 그의 안쪽 손은 arm_r.
    her = STAGE.place(HER, HER_AT[0], HER_AT[1], HER_TURN, outfit=HER_COAT, ink=PRINT_INK, head=5.0, head_pitch=10.0,
                      fists={"arm_l": CLASP - CLASP_GAP}, poles={"arm_l": INNER_POLE}, arm_r=(8.0, 4.0),
                      grips=("l",), palm_out=("l",), leg_l=(3.0, 0.0), leg_r=(4.0, 1.0))
    him = STAGE.place(HIM, HIM_AT[0], HIM_AT[1], HIM_TURN, outfit=HIM_COAT, ink=PRINT_INK, head=-2.0, head_pitch=8.0,
                      fists={"arm_r": CLASP + CLASP_GAP}, poles={"arm_r": INNER_POLE}, arm_l=(9.0, 5.0),
                      grips=("r",), leg_l=(4.0, 1.0), leg_r=(3.0, 0.0))
    hits = STAGE.collisions([her, him])
    assert not hits, f"팔이 상대 몸을 뚫음: {hits}"
    return her, him


def stipple(cv, shape, color, opacity=1.0, clip=None, blend=Blend.NORMAL):
    """점묘 명암. 흐린 형태를 입자로 찍어 색 수를 늘리지 않고 계조를 만든다."""
    cv.fill(shape, color, opacity=opacity, clip=clip, grain=1.0, blend=blend)


# ---------- 하늘과 단지 ----------

def horizon_y():
    """카메라의 지평선 화면 높이: 눈높이의 아주 먼 점."""
    eye = CITY_CAMERA.eye
    return CITY_CAMERA.project((eye[0], eye[1], eye[2] + 1e5))[1]


def paint_sky(cv, rng):
    horizon = horizon_y()
    band = (horizon + 40) / len(SKY_BANDS)
    for index, color in enumerate(SKY_BANDS):
        top = index * band
        cv.fill(cv.shape(g.rect(0, top, WIDTH, band + 2)), color)
        if index > 0:
            stipple(cv, cv.shape(g.rect(0, top - 30, WIDTH, 60), soft=18), color)
    # 도시 빛을 받은 낮은 층구름: 가늘고 긴 띠의 아랫가장자리만 난색으로 데워진다.
    for _ in range(7):
        x, y = rng.uniform(0, WIDTH), rng.uniform(60, horizon - 80)
        length = rng.uniform(500, 900)
        cloud = cv.shape(g.spline([(x - length / 2, y), (x - length / 4, y - 9), (x + length / 3, y - 7),
                                   (x + length / 2, y + 2), (x, y + 8)], corners=(0, 3)), soft=4)
        cv.fill(cloud, CLOUD_LOW)
        stipple(cv, cv.shape(g.rect(x - length / 2, y + 2, length, 8), soft=5), CLOUD_LIT, opacity=0.8, clip=cloud)
    stipple(cv, cv.shape(g.rect(0, horizon - 120, WIDTH, 140), soft=50), CLOUD_LIT, opacity=0.6)


def make_blocks(rng):
    """단지의 패널 아파트 상자 목록 [(입체, 층수)]. 줄마다 시야 폭 안에 9층 긴 동, 16층 탑, 5층 동을 섞어 세운다.

    무작위 x로 흩으면 가까운 줄의 동이 대부분 시야 밖에 떨어져 화면 아래가 빈다. 줄의 폭을 시야 폭에 맞춘다.
    """
    blocks = []
    kinds = ((60.0, 9, 12.0), (24.0, 16, 22.0), (80.0, 5, 12.0))
    for z in BLOCK_ROWS:
        half_view = (z - CITY_CAMERA.eye[2]) * 0.8
        x = -half_view + rng.uniform(0.0, 40.0)
        while x < half_view:
            length, floors, depth = kinds[int(rng.choice(3, p=(0.6, 0.12, 0.28)))]
            yaw = float(rng.choice((0.0, 90.0, 30.0), p=(0.55, 0.3, 0.15)))
            height = floors * FLOOR_HEIGHT_M
            center_z = z + rng.uniform(-8.0, 8.0)
            solid = s3.box((x, height / 2, center_z), (length, height, depth)).rotated(yaw=yaw, about=(x, 0.0, center_z))
            blocks.append((solid, floors))
            x += length * (0.4 if yaw == 90.0 else 1.0) + rng.uniform(25.0, 60.0)
    return blocks


def paint_windows(cv, rng, face, floors, lit_ratio):
    """면 1개의 켜진 창만 칠한다. 꺼진 창까지 그리면 먼 동이 회색 격자로 뭉친다."""
    columns = max(int(np.linalg.norm(face.vertices[1] - face.vertices[0]) / 3.2), 2)
    for row in range(floors):
        for column in range(columns):
            if rng.random() > lit_ratio:
                continue
            u0, v0 = (column + 0.3) / columns, (row + 0.3) / floors
            path = CITY_CAMERA.region(face, u0, v0, u0 + 0.4 / columns, v0 + 0.4 / floors)
            color = WINDOW_COLD if rng.random() < 0.1 else WINDOW_WARM
            cv.fill(cv.shape(path), color, opacity=0.95)


def paint_city(cv, rng):
    """먼 동부터 상자를 칠하고 보이는 옆면에 켜진 창, 동 사이 길에 가로등 줄."""
    horizon = horizon_y()
    cv.fill(cv.shape(g.rect(0, horizon, WIDTH, HEIGHT - horizon)), GROUND)
    for near, far in zip(BLOCK_ROWS[:-1], BLOCK_ROWS[1:]):
        z = (near + far) / 2.0
        half = (z - CITY_CAMERA.eye[2]) * 0.9
        road = CITY_CAMERA.path([(-half, 0.0, z - 4.0), (half, 0.0, z - 4.0), (half, 0.0, z + 4.0), (-half, 0.0, z + 4.0)])
        cv.fill(cv.shape(road), ROAD)
        for x in np.arange(-half, half, 34.0):
            spot = CITY_CAMERA.project((x, 0.0, z + 4.5))
            radius = float(np.clip(CITY_CAMERA.scale_at((x, 0.0, z)) * 2.4, 1.5, 12.0))
            cv.fill(cv.shape(g.ellipse(spot[0], spot[1], radius * 2.0, radius * 0.8), soft=radius * 0.8), SODIUM,
                    opacity=0.45, blend=Blend.SCREEN)
            cv.fill(cv.shape(g.ellipse(spot[0], spot[1], 1.4, 1.4)), SODIUM)
    blocks = make_blocks(rng)
    ordered = CITY_CAMERA.order([solid for solid, _ in blocks])
    floors_of = {id(solid): floors for solid, floors in blocks}
    for solid in ordered:
        s3.draw(cv, CITY_CAMERA, solid, {"top": BLOCK_TOP, "*": BLOCK_WALL}, CITY_LIGHT, ambient=0.6, highlight=0.0)
        for face in CITY_CAMERA.visible_faces(solid):
            if face.name not in ("top", "bottom"):
                paint_windows(cv, rng, face, floors_of[id(solid)], 0.14)


# ---------- 옥상 ----------

def paint_roof(cv, rng):
    """옥상 바닥(눈 덮인 자리와 녹은 자리), 두 사람 앞의 난간벽, 안테나, 계단실."""
    floor = STAGE.project([(-30.0, 0.0, -12.0), (30.0, 0.0, -12.0), (30.0, 0.0, PARAPET_Z), (-30.0, 0.0, PARAPET_Z)])
    floor_shape = cv.shape(floor)
    cv.fill(floor_shape, ROOF)
    for _ in range(14):
        x, z = rng.uniform(-16.0, 16.0), rng.uniform(-6.0, PARAPET_Z)
        patch = STAGE.ellipse((x, z), rng.uniform(1.0, 3.5), 0.0, radius_z=rng.uniform(0.4, 1.2))
        stipple(cv, cv.shape(patch, soft=8), ROOF_SNOW, opacity=0.8, clip=floor_shape)
    for name, path, _ in STAGE.box((-30.0, 30.0), (-PARAPET_HEIGHT, 0.0), (PARAPET_Z, PARAPET_Z + 0.6)):
        face = cv.shape(path)
        cv.fill(face, PARAPET_TOP if name == "top" else PARAPET)
        if name == "top":
            stipple(cv, face, ROOF_SNOW, opacity=0.7)
    # 계단실: 화면 오른쪽 가장자리에 걸친 상자. 문 위의 흐린 전구 하나.
    for name, path, _ in STAGE.box((11.5, 18.0), (-10.0, 0.0), (-4.0, 0.5)):
        cv.fill(cv.shape(path), PARAPET_TOP if name == "top" else PARAPET)
    door = STAGE.project([(12.6, 0.0, -4.0), (12.6, -6.4, -4.0), (14.8, -6.4, -4.0), (14.8, 0.0, -4.0)])
    cv.fill(cv.shape(door), METAL)
    bulb = STAGE.point(13.7, -7.2, -4.1)
    cv.fill(cv.shape(g.ellipse(bulb[0], bulb[1], 70, 70), soft=40), SODIUM, opacity=0.35, blend=Blend.SCREEN)
    cv.fill(cv.shape(g.ellipse(bulb[0], bulb[1], 5, 5)), WINDOW_WARM)
    paint_antennas(cv)


def paint_antennas(cv):
    """옥상 왼쪽의 TV 안테나 기둥 2개. 가로대가 위로 갈수록 짧다."""
    for x, z, height in ((-9.0, 0.6, 15.0), (-12.5, -1.5, 12.0)):
        cv.stroke(STAGE.project([(x, 0.0, z), (x, -height, z)]), METAL, width=4.0)
        for index, level in enumerate(np.linspace(height * 0.7, height, 4)):
            half = 2.0 - index * 0.4
            cv.stroke(STAGE.project([(x - half, -level, z), (x + half, -level, z)]), METAL, width=2.2)


def paint_people(cv, models):
    for model in STAGE.far_first(models):
        x, z = model.world[0], model.world[2]
        stipple(cv, cv.shape(STAGE.ellipse((x, z), 1.2, 0.0, radius_z=0.5), soft=10), "#0a0d14", opacity=0.6)
    for model in STAGE.far_first(models):
        ch.paint_figure(cv, model)


def main(out_dir="out", scale=1.0, seed=139):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv, rng)
    paint_city(cv, rng)
    paint_roof(cv, rng)
    her, him = make_people()
    paint_people(cv, (her, him))
    io.save(cv.guide_image(), out_dir / "rooftop_1_flat_guide.png")
    image = illustration.render(cv, paper_tint="#e9e4d8", ink_mottle=0.08)
    return io.save(image, out_dir / "illustration_doomer_rooftop.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
