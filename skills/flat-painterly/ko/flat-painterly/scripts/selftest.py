"""설치 확인과 엔진 자가 점검. 장면을 그리기 전에 한 번 실행한다.

사용: python selftest.py
의존성이 빠졌으면 설치 명령을 안내하고 종료한다. 모든 점검을 통과하면 'OK'를 출력한다.
"""
import importlib
import sys
from pathlib import Path

REQUIRED = {"numpy": "numpy", "cv2": "opencv-python-headless"}


def check_dependencies():
    missing = []
    for module, package in REQUIRED.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        sys.exit("누락된 패키지: " + ", ".join(missing) + "\n설치: pip install " + " ".join(missing))


def check_engine():
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codepaint import Blend, Canvas, Linear, Perspective, Radial, color, figure, io, motifs, props
    from codepaint import solids as s3
    from codepaint import geometry as g
    from codepaint.styles import anime, illustration, oil, watercolor

    # 색
    assert np.allclose(color.rgb("#ff8000"), [1.0, 128 / 255, 0.0])
    assert np.allclose(color.rgb("#fff"), [1.0, 1.0, 1.0])
    assert color.luminance(color.shade("#e08040")) < color.luminance(color.rgb("#e08040"))
    try:
        color.rgb("#12345")
    except ValueError:
        pass
    else:
        raise AssertionError("잘못된 색 문자열을 거르지 못함")

    # 경로
    square = g.spline([(0, 0), (10, 0), (10, 10), (0, 10)], closed=True, corners=(0, 1, 2, 3))
    assert abs(abs(g.signed_area(square)) - 100.0) < 1e-6, "모서리 4개를 모두 꺾으면 정사각형이어야 함"
    frame = g.Frame(origin=(100, 50), unit=10, rotate=90)
    assert np.allclose(frame.point(1, 0), (100, 60)), "화면에서 시계 방향 90도면 오른쪽이 아래로 가야 함"
    assert np.allclose(frame.mirrored().point(1, 0), (100, 40))

    # 형태와 칠
    cv = Canvas(200, 200, scale=1.0, background="#000000")
    disc = cv.shape(g.ellipse(100, 100, 50))
    area = float(disc.mask.sum())
    assert abs(area - np.pi * 50 ** 2) / (np.pi * 50 ** 2) < 0.01, "원 면적이 1% 넘게 어긋남"
    cv.fill(disc, "#ffffff")
    assert cv.image()[100, 100].min() > 0.99 and cv.image()[5, 5].max() < 0.01
    cv.fill(cv.shape(g.rect(0, 0, 200, 200)), "#ff0000", clip=disc, blend=Blend.MULTIPLY)
    assert np.allclose(cv.image()[100, 100], [1, 0, 0], atol=0.01), "곱하기 합성 결과가 다름"
    assert cv.image()[5, 5].max() < 0.01, "clip 밖이 칠해짐"
    shadow = cv.form_shadow(disc, (-1, -1), amount=0.4)
    fraction = float(shadow.mask.sum()) / area
    assert 0.35 < fraction < 0.45, f"그림자 면적 비율이 amount와 다름: {fraction:.2f}"
    assert shadow.mask[130 - shadow.y0, 130 - shadow.x0] > 0.9, "그림자가 빛 반대쪽에 있지 않음"
    rim = cv.edge_light(disc, (0, -1), width=8)
    assert rim.mask[55 - rim.y0, 100 - rim.x0] > 0.9 and rim.mask[145 - rim.y0, 100 - rim.x0] < 0.1, \
        "빛 테두리가 빛을 향한 윤곽에 있지 않음"
    cv.fill(disc, Linear(["#000000", "#ffffff"], (50, 0), (150, 0)))
    assert cv.image()[100, 60].mean() < cv.image()[100, 140].mean()
    cv.fill(disc, Radial(["#ffffff", "#000000"], (100, 100), 50))
    assert cv.image()[100, 100].mean() > cv.image()[100, 140].mean()
    cv.stroke([(20, 20), (180, 20)], "#00ff00", width=6, taper=(0, 1, 0))
    assert cv.image()[20, 100, 1] > 0.9 and cv.image()[20, 22, 1] < 0.5, "선 끝이 가늘어지지 않음"
    empty = cv.shape(g.rect(500, 500, 10, 10))
    cv.fill(empty, "#ffffff")  # 화면 밖 형태는 오류 없이 무시되어야 한다
    cv.fill(cv.contour(empty, 2.0), "#ffffff")  # 화면 밖으로 잘린 부품의 윤곽선(무릎 위 구도의 발)도 마찬가지

    layer = Canvas(200, 200, background=None)
    layer.fill(layer.shape(g.ellipse(100, 100, 30)), "#0000ff")
    assert layer.alpha[100, 100] > 0.99 and layer.alpha[5, 5] == 0.0
    cv.paste(layer)
    assert np.allclose(cv.image()[100, 100], [0, 0, 1], atol=0.01)
    assert Canvas.from_image(cv.image(), 200, 200).rgb.shape == cv.rgb.shape
    assert io.crop(cv.image(), (50, 50, 150, 100), 1.0, zoom=2.0).shape == (100, 200, 3)
    assert io.sheet([cv.image()] * 3, columns=2).shape[1] > 400

    # 인체 리그: 어떤 자세에서도 뼈 길이가 등신 비례를 유지해야 한다
    unit = 40.0
    body = figure.Figure(g.Frame((100, 200), unit), hip_tilt=9, chest_tilt=-7, spine=-4,
                         arm_l=(150, 215), arm_r=(35, -60), leg_l=(6, 0), leg_r=(-4, 14))
    for start, end, bone in (("shoulder_l", "elbow_l", "upper_arm"), ("elbow_r", "wrist_r", "forearm"),
                             ("hip_l", "knee_l", "thigh"), ("knee_r", "ankle_r", "shin")):
        length = np.linalg.norm(np.subtract(body.joint(start), body.joint(end)))
        assert abs(length - figure.BONE_LENGTH[bone] * unit) < 1e-6, f"{bone} 길이가 자세에 따라 변함"
    assert body.joint("head")[1] < body.joint("shoulder_mid")[1] < body.joint("pelvis")[1] < body.joint("knee_l")[1]
    assert body.joint("elbow_l")[1] < body.joint("shoulder_l")[1], "150도로 든 팔의 팔꿈치가 어깨 위에 있지 않음"
    short = figure.Figure(g.Frame((100, 200), unit), stretch={"thigh_l": 0.5})
    assert abs(np.linalg.norm(np.subtract(short.joint("hip_l"), short.joint("knee_l")))
               - figure.BONE_LENGTH["thigh"] * unit * 0.5) < 1e-6
    dropped = figure.Figure(g.Frame((100, 200), unit), shoulder_drop=0.12)
    assert abs(dropped.joint("shoulder_l")[1] - figure.Figure(g.Frame((100, 200), unit)).joint("shoulder_l")[1]
               - 0.12 * unit) < 1e-6, "shoulder_drop이 어깨 관절을 내리지 않음"
    base = figure.Figure(g.Frame((100, 200), unit), stretch={"neck": 0.72})
    head_top = base.joint("head")[1] - 0.5 * unit
    sole = max(path[:, 1].max() for path in base.foot("l", view="bare_front"))
    assert abs((sole - head_top) / unit - 8.04) < 0.05, f"맨발 기준 전신이 8등신이 아님: {(sole - head_top) / unit:.2f}"
    assert len(base.foot("r", view="bare_front")) == 6 and len(base.foot("r", view="bare_back")) == 1
    toes = base.toes("l")
    assert len(toes) == 5 and all(len(pair) == 2 for pair in toes)
    widths = [np.ptp(toe[:, 0]) for toe, _ in toes]
    assert widths[0] == max(widths), "엄지발가락이 가장 굵지 않음"
    tips = [toe[:, 1].max() for toe, _ in toes]
    assert tips[0] > tips[-1], "엄지발가락 끝이 새끼발가락보다 앞에 있지 않음"
    lying = figure.Figure(g.Frame((200, 100), unit, rotate=-90))
    assert lying.joint("head")[0] < lying.joint("pelvis")[0] and abs(lying.joint("head")[1] - 100) < 1e-6, \
        "반시계 90도로 눕힌 리그의 머리가 화면 왼쪽에 있지 않음"
    silhouette = figure.shape_of(cv, [path for paths in body.parts().values() for path in paths])
    assert silhouette.mask.max() > 0.99
    sleeve = figure.shape_of(cv, body.limb("forearm", "r", scale=1.5)).mask.sum()
    assert sleeve > figure.shape_of(cv, body.limb("forearm", "r")).mask.sum(), "scale이 굵기에 반영되지 않음"

    # 손: 굽히면 손등 쪽에서 본 손가락이 짧아지고 마디 좌표는 뿌리와 마디 3개로 이루어진다
    hand_frame = g.Frame((100, 100), 80)
    flat, bent = figure.hand_open(hand_frame), figure.hand_open(hand_frame, curl=0.8)

    def reach(hand):
        return np.linalg.norm(np.subtract(hand.joints["middle"][-1], hand.joints["middle"][0]))

    assert len(flat.joints["index"]) == 4 and set(flat.parts) == {"palm", "index", "middle", "ring", "pinky", "thumb"}
    assert reach(bent) < reach(flat) * 0.6, "굽힌 손가락이 짧아지지 않음"
    assert abs(reach(flat) - 0.45 * 80) < 1e-6, "편 가운뎃손가락 길이가 손 길이의 0.45가 아님"
    side = figure.hand_side(hand_frame, curl=1.0)
    assert side.joints["index"][-1][0] < side.joints["index"][0][0], "옆모습 손가락이 손바닥 쪽으로 굽지 않음"
    assert len(side.paths()) > 10

    # 투시: 같은 간격의 점이 멀수록 소실점에 가까워지고 깊이 방향 평행선은 소실점에서 만난다
    view = Perspective(vanish=(500, 300), eye_height=1.6, focal=800)
    near, far, farther = view.project(-4, 0, 5), view.project(-4, 0, 20), view.project(-4, 0, 5000)
    assert near[0] < far[0] < 500 and near[1] > far[1] > 300
    assert abs(farther[0] - 500) < 1.0 and abs(farther[1] - 300) < 1.0, "먼 점이 소실점으로 수렴하지 않음"
    assert abs(view.project(3, 1.6, 7)[1] - 300) < 1e-6, "눈높이의 점이 지평선 위에 있지 않음"
    assert abs(view.scale_at(10) - 80) < 1e-6
    assert len(view.side_wall_grid(-4, 5, 15, 0, 9, 4, 3)) == 12
    try:
        view.project(0, 0, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("깊이 0을 거르지 못함")

    # 입체: 카메라를 향한 면만 보이고 원기둥의 모든 조각 법선이 바깥을 향해야 한다
    camera = s3.Camera(eye=(0, 30, -60), target=(0, 0, 0), focal=1000, center=(500, 300))
    cube = s3.box((0, 0, 0), (10, 10, 10))
    assert {face.name for face in camera.visible_faces(cube)} == {"front", "top"}, "정면 위에서 본 상자의 보이는 면이 다름"
    turned = cube.rotated(yaw=30)
    assert "right" in {face.name for face in camera.visible_faces(turned)}, "yaw 양수에서 오른쪽 면이 돌아 나오지 않음"
    assert turned.face("front").normal[0] < 0, "yaw 양수에서 정면이 화면 왼쪽으로 돌지 않음"
    tilted = cube.rotated(pitch=30)
    assert tilted.face("top").normal[2] > 0, "pitch 양수에서 윗면이 뒤로 넘어가지 않음"
    can = s3.cylinder((0, 0, 0), 5, 10, segments=32)
    for face in can.faces:
        if face.name == "side":
            outward = face.center - np.array([0, face.center[1], 0])
            assert np.dot(face.normal, outward) > 0, "원기둥 옆면 법선이 안쪽을 향함"
    side_visible = [face for face in camera.visible_faces(can) if face.name == "side"]
    assert 14 <= len(side_visible) <= 18, f"앞에서 본 원기둥의 옆면 조각 수가 절반이 아님: {len(side_visible)}"
    lying = s3.slab((0, 0, 0), (8, 16, 1), 1.0).rotated(pitch=90)
    assert lying.face("front").normal[1] > 0.99, "pitch 90으로 눕힌 판의 정면이 위를 향하지 않음"
    top = cube.face("top")
    assert np.allclose(top.point(0, 0), (-5, 5, 5)) and np.allclose(top.point(1, 1), (5, 5, -5)), \
        "상자 윗면의 u, v 방향이 문서와 다름"
    near, far = camera.project((0, 0, -10)), camera.project((0, 0, 10))
    assert near[1] > far[1] and camera.scale_at((0, 0, -10)) > camera.scale_at((0, 0, 10))
    assert np.allclose(camera.project((0, 0, 0)), (500, 300)), "목표점이 화면 중심에 오지 않음"
    try:
        camera.project((0, 30, -70))
    except ValueError:
        pass
    else:
        raise AssertionError("카메라 뒤의 점을 거르지 못함")
    sketch = Canvas(1000, 600, scale=0.5, background="#ffffff")
    shapes = s3.draw(sketch, camera, cube, {"front": "#ff0000", "*": "#0000ff"}, (-0.5, 0.8, -0.4), line="#000000")
    assert set(shapes) == {"front", "top", "silhouette"}
    shade_front = s3.face_color("#808080", (0, 0, -1), (0, 1, 0))
    shade_top = s3.face_color("#808080", (0, 1, 0), (0, 1, 0))
    assert color.luminance(shade_top) > color.luminance(shade_front), "빛을 향한 면이 더 밝지 않음"
    desk = props.laptop((0, 0, 0), yaw=20)
    assert set(desk.solids) == {"base", "lid"} and set(desk.faces) == {"screen", "deck"}
    assert desk.faces["screen"].normal[2] < 0, "노트북 화면이 카메라 쪽을 향하지 않음"
    lamp = props.desk_lamp((0, 0, 20))
    lamp.draw(sketch, camera, {"base": "#333333", "shade": "#333333", "arm": "#333333"}, (0, 1, 0))
    props.keycaps(sketch, camera, props.keyboard((0, 0, 0)).faces["keys"], "#eeeeee")
    ring = sketch.contour(sketch.shape(g.ellipse(500, 300, 100)), 6)
    assert ring.mask[(300 - 100) // 2 + 1 - ring.y0, 500 // 2 - ring.x0] > 0.9, "contour가 윤곽에 띠를 만들지 않음"
    assert ring.mask[300 // 2 - ring.y0, 500 // 2 - ring.x0] < 0.01, "contour가 형태 안쪽 전체를 채움"

    # 3차원 리그: 정면은 평면 리그와 같고, 돌리면 가까운 쪽과 그리는 순서가 바뀐다
    from codepaint.figure3d import MALE_DEPTH, Figure3D
    from codepaint.head3d import FEMALE_HEAD, HairStyle, Head3D, Lock
    frame = g.Frame((400, 800), 150)
    planar_pose = dict(hip_tilt=-6, chest_tilt=4, spine=-1, head=-3, arm_l=(11, 5), arm_r=(13, 3), leg_l=(6, 1),
                       leg_r=(3, -1), stretch={"neck": 0.72}, shoulder_drop=0.12)
    flat, solid = figure.Figure(frame, **planar_pose), Figure3D(frame, **planar_pose)
    for name in flat.joints:
        assert np.allclose(flat.joint(name), solid.joint(name)), f"turn 0의 관절이 평면 리그와 다름: {name}"
    assert np.allclose(flat.torso()[0], solid.torso()[0]), "turn 0의 몸통 윤곽이 평면 리그와 다름"
    assert [name for name, _ in solid.groups()] == ["body"], "정면에서 팔다리가 몸과 한 덩어리가 아님"
    side = Figure3D(frame, build=figure.MALE, depth=MALE_DEPTH, turn=90)
    assert side.depth_of(side.joints3["shoulder_l"]) < side.depth_of(side.joints3["shoulder_r"]), \
        "turn 90에서 _l 쪽이 가깝지 않음"
    order = [name for name, _ in side.groups()]
    assert order[0] == "arm_r" and order[-1] == "arm_l" and "leg_l" not in order, f"옆모습의 칠하는 순서가 다름: {order}"
    assert side.facing((0, 0, -1)) < 0.01 and side.facing((-1, 0, 0)) > 0.99, "turn 90의 정면 방향이 화면 오른쪽이 아님"
    back = Figure3D(frame, turn=180)
    assert np.isclose(back.joint("wrist_l")[0] - 400, 400 - Figure3D(frame).joint("wrist_l")[0]), "뒷면이 좌우로 뒤집히지 않음"
    assert len(Figure3D(frame).toes("l")) == 5 and back.toes("l") == [], "발가락이 정면에서만 보이지 않음"
    raised = Figure3D(frame, foot_pitch={"l": 30})
    assert raised.foot("l")[0][:, 1].max() > Figure3D(frame).foot("l")[0][:, 1].max(), "뒤꿈치를 들어도 발끝이 내려가지 않음"
    seated = Figure3D(frame, turn=30, swing={"leg_l": (90, 0), "leg_r": (90, 0)})
    assert "leg_l" in [name for name, _ in seated.groups()], "앉은 가까운 다리가 몸과 따로 칠해지지 않음"
    assert seated.joints3["knee_l"][2] < -1.9, "허벅지를 90도 들어도 무릎이 앞으로 나오지 않음"

    # 3차원 머리: 정면의 얼굴 표 좌표는 그대로 찍히고, 돌리면 먼 눈이 사라지고 얼굴 자리가 닫힌다
    style = HairStyle(thickness=0.12, hairline=((0, -0.45), (90, 0.1), (180, 0.8)),
                      locks=(Lock((0, -0.9), (0, 0.1), 0.3), Lock((180, -0.7), (180, 1.0), 0.5)))
    head_frame = g.Frame((300, 300), 50)
    front_head = Head3D(head_frame, FEMALE_HEAD)
    assert np.allclose(front_head.face().point(0.45, 0.4), head_frame.point(0.45, 0.4)), "정면 얼굴 좌표가 어긋남"
    assert len(front_head.silhouette()) == 2 and front_head.face_window(style) is not None
    layers = front_head.locks(style)
    assert len(layers["front"]) == 1 and len(layers["back"]) == 1, "정면에서 앞머리와 뒷머리 층이 나뉘지 않음"
    profile = Head3D(head_frame, FEMALE_HEAD, yaw=90)
    assert profile.face().facing(-0.45, 0.4) > 0.1 > profile.face().facing(0.45, 0.4), "옆모습에서 먼 눈이 남음"
    assert profile.ear("l")[2] > 0.5 > profile.ear("r")[2], "옆모습에서 가까운 귀가 앞으로 나오지 않음"
    assert profile.nose_tip()[0] > max(path[:, 0].max() for path in profile.silhouette()) - 1.0, "코끝이 옆 윤곽에 없음"
    behind = Head3D(head_frame, FEMALE_HEAD, yaw=180)
    assert behind.face_window(style) is None and len(behind.locks(style)["back"]) == 1, "뒷면에서 얼굴 자리가 남음"

    # 옷: 몸통 옷은 몸보다 넓고, 아랫단은 걷는 다리를 덮고, 망토는 정면에서 몸 뒤에 걸린다
    from codepaint import character, garment
    from codepaint.stage import Stage
    dressed = Figure3D(frame, build=figure.MALE, depth=MALE_DEPTH)
    shirt = garment.loft(dressed, ("thorax", -0.18), ("pelvis", -0.3), 0.08).outline()
    assert np.ptp(shirt[:, 0]) > np.ptp(dressed.torso()[0][:, 0]), "셔츠가 몸통보다 좁음"
    walker = Figure3D(frame, swing={"leg_l": (25, 5), "leg_r": (-20, -30)})
    skirt = garment.loft(walker, ("pelvis", -0.6), None, 0.04, hem=garment.Hem(3.2, 0.3))
    knee_z = walker.local_point("pelvis", 0, 0, 0)[2] + walker.joints3["knee_l"][2]
    hem_front = min(section.cz - section.front for section in skirt.sections if section.y > 1.8)
    assert hem_front < knee_z, "걷는 앞다리의 무릎이 치마 아랫단 밖으로 나감"
    front_cape = garment.mage_robe()(Figure3D(frame))[-1]
    back_cape = garment.mage_robe()(Figure3D(frame, turn=180))[-1]
    assert front_cape.group == "cape" and front_cape.facing < 0 < back_cape.facing, "망토가 등 뒤에 걸리지 않음"
    pieces = character._merged([piece for piece in garment.casual_shirt()(dressed) if piece.merge == "pants"])
    assert len(pieces) == 1, "바지 허리와 가랑이가 한 조각으로 합쳐지지 않음"

    # 무대: 발이 바닥에 닿고, reach한 손목이 목표에 닿고, 미룬 덩어리를 나중에 칠할 수 있다
    stage = Stage((500, 900), 100, elevation=5)
    target = np.array([0.6, -5.0, -0.6])
    walker_model = stage.place(character.FEMALE, 0.0, 0.0, 30.0, reach={"arm_r": target})
    assert np.linalg.norm(stage.joint_world(walker_model, "wrist_r") - target) < 0.02, "reach한 손목이 목표에 닿지 않음"
    soles = [stage.to_world(walker_model, point)[1] for side in "lr" for point in walker_model.body._foot_cloud(side)]
    assert abs(max(soles)) < 1e-6, "발바닥이 바닥(y 0)에 닿지 않음"
    assert np.allclose(stage.project([walker_model.world])[0], walker_model.body.joint("pelvis")), "무대와 리그의 투영이 어긋남"
    from codepaint.stage import ELBOW_POLE
    default_pole = stage.place(character.FEMALE, 0.0, 0.0, 30.0, reach={"arm_r": target}, poles={"arm_r": ELBOW_POLE})
    assert np.allclose(stage.joint_world(default_pole, "elbow_r"), stage.joint_world(walker_model, "elbow_r")), \
        "poles를 ELBOW_POLE로 준 팔꿈치가 기본값과 다름"
    inward = stage.place(character.FEMALE, 0.0, 0.0, 30.0, reach={"arm_r": target}, poles={"arm_r": (-0.5, 1.0, 0.0)})
    assert np.linalg.norm(stage.joint_world(inward, "wrist_r") - target) < 0.02, "poles를 주면 손목이 목표에 닿지 않음"
    assert stage.to_world(inward, inward.body.joints3["elbow_r"])[0] < stage.joint_world(walker_model, "elbow_r")[0], \
        "안쪽 pole의 팔꿈치가 몸 안쪽으로 가지 않음"
    holder = stage.place(character.MALE, 0.0, 0.0, -20.0, fists={"arm_l": target}, grips=("l",))
    assert np.linalg.norm(stage.fist_world(holder, "l") - target) < 0.001, "fists로 맞춘 주먹 가운데가 목표에 닿지 않음"
    crowded = [stage.place(character.MALE, x, 0.0, 0.0) for x in (0.0, 1.2)]
    assert any(hit.part == "torso" for hit in stage.collisions(crowded)), "몸통을 뚫은 팔을 찾지 못함"
    touching = stage.collisions([stage.place(character.MALE, x, 0.0, 0.0) for x in (0.0, 2.2)])
    assert touching and all(hit.part != "torso" for hit in touching), "몸통 밖에서 겹친 두 팔을 팔끼리의 관통으로 찾지 못함"
    assert stage.collisions([stage.place(character.MALE, x, 0.0, 0.0) for x in (0.0, 4.0)]) == [], \
        "떨어져 선 두 사람에서 관통을 찾음"
    sitter = stage.place(character.MALE, 1.0, 0.0, -80.0, outfit=garment.casual_shirt(), reach={"arm_r": target},
                         swing={"leg_l": (88, 0), "leg_r": (88, 0)})
    small = Canvas(1000, 1000, scale=0.25, background=None)
    character.paint_figure(small, sitter, defer=("arm_r",))
    before = small.alpha.sum()
    character.paint_deferred(small, sitter, ("arm_r",))
    assert small.alpha.sum() > before, "미룬 팔을 나중에 칠하지 못함"
    clasp = stage.place(character.FEMALE, 0.0, 0.0, 0.0, grips=("r",), palm_out=("r",))
    plain = stage.place(character.FEMALE, 0.0, 0.0, 0.0, grips=("r",))
    flipped = character.choose_hand(clasp, "r")[0].joints["index"][-1][0] - clasp.body.joint("wrist_r")[0]
    normal = character.choose_hand(plain, "r")[0].joints["index"][-1][0] - plain.body.joint("wrist_r")[0]
    assert flipped * normal < 0, "palm_out이 쥔 손의 손가락 방향을 뒤집지 않음"

    # 얼굴과 머리 템플릿: 기본 얼굴은 성별 기본값, restyle은 얼굴형까지 바꾸고 머리 좌표를 몸 좌표로 옮겨도 화면 자리가 같다
    from dataclasses import replace

    from codepaint import faces, hairstyles
    assert character.face_spec(character.FEMALE) is faces.FEMALE_MATURE
    assert character.face_spec(character.MALE) is faces.MALE_CLEAN
    soft = character.restyle(character.FEMALE, face=faces.FEMALE_SOFT, hair=hairstyles.LONG_STRAIGHT)
    assert soft.head is faces.FEMALE_SOFT.head and soft.hair is hairstyles.LONG_STRAIGHT and soft.palette is \
        character.FEMALE.palette
    for turn in (0.0, 90.0, 180.0):
        model = character.place(soft, (200, 300), 80, turn, elevation=4.0, head_turn=20.0, head=5.0)
        center, matrix = hairstyles.head_to_body(model)
        probe = np.array([0.3, 1.2, -0.4])
        assert np.allclose(model.head.project([probe])[0], model.body.project(center + matrix @ probe), atol=1e-6), \
            "머리 좌표를 몸 좌표로 옮기면 화면 자리가 바뀜"
        pierced = straight = 0
        for lock in (lock for lock in soft.hair.locks if lock.drape):
            points = [center + matrix @ point for point, _ in model.head.lock_samples(soft.hair, lock,
                                                                                   hairstyles.DRAPE_SAMPLES)]
            straight += sum(model.body.inside_torso(point) for point in points)
            pierced += sum(model.body.inside_torso(point) for point in hairstyles.drape(model.body, points, lock.drape))
        assert straight > 0 and pierced == 0, f"긴 머리 다발이 몸통을 뚫음: 곧게 {straight}점, 드레이프 뒤 {pierced}점"
    plain = character.place(character.FEMALE, (200, 300), 80, 30.0)
    plain_layers = hairstyles.lock_layers(plain)
    assert [len(plain_layers[name]) for name in ("back", "front")] == \
        [len(paths) for paths in plain.head.locks(character.FEMALE.hair).values()] and not plain_layers["tucked"], \
        "drape 없는 머리의 층이 달라짐"
    turned = character.place(soft, (200, 300), 80, 20.0, head_turn=22.0)
    assert hairstyles.lock_layers(turned)["tucked"], "3/4 각도에서 얼굴 뒤를 지나는 긴 다발을 찾지 못함"
    pink = character.restyle(character.FEMALE, hair_color=hairstyles.HAIR_COLORS["pink"])
    assert (pink.palette.hair, pink.palette.line_hair) == ("#efa2ba", "#682840") and \
        replace(pink.palette, hair=character.FEMALE.palette.hair, hair_shade=character.FEMALE.palette.hair_shade,
                hair_light=character.FEMALE.palette.hair_light, line_hair=character.FEMALE.palette.line_hair) == \
        character.FEMALE.palette, "머리색이 머리 4색 밖의 팔레트를 바꿈"

    # 화풍 패스와 재현성
    def scene(seed):
        canvas = Canvas(240, 160, scale=1.0, seed=seed)
        canvas.fill(canvas.full(), Linear(["#3060c0", "#f0c080"], (0, 0), (0, 160)))
        motifs.cumulus(canvas, 120, 120, 120, 70, puffs=12)
        motifs.canopy(canvas, 200, 110, 60, 50, puffs=8, rng=canvas.rng)
        motifs.grass(canvas, (0, 240), (140, 160), 20, ["#4f7f34"], rng=canvas.rng)
        anime.cel(canvas, g.ellipse(60, 110, 24), "#e05030", "#902030", 0.4, "#301018")
        watercolor.wash(canvas, g.blob(180, 60, 30, rng=canvas.rng), "#80c0a0")
        canvas.direct(canvas.full(), angle=0)
        return canvas

    for name, render in (("oil", oil.render), ("watercolor", watercolor.render),
                         ("illustration", illustration.render), ("anime", anime.finish)):
        first, second = render(scene(3)), render(scene(3))
        assert first.shape == (160, 240, 3), f"{name}: 출력 크기가 다름"
        assert 0.0 <= first.min() and first.max() <= 1.0, f"{name}: 값 범위를 벗어남"
        assert np.array_equal(first, second), f"{name}: 같은 시드에서 결과가 달라짐"
        assert not np.array_equal(first, render(scene(4))), f"{name}: 시드가 결과에 반영되지 않음"


if __name__ == "__main__":
    check_dependencies()
    check_engine()
    print("OK")
