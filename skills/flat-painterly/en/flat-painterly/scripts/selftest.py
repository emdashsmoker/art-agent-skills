"""Install check and engine self-test. Run it once before painting a scene.

Usage: python selftest.py
If dependencies are missing, it prints the install command and exits. When every check passes, it prints 'OK'.
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
        sys.exit("missing packages: " + ", ".join(missing) + "\ninstall: pip install " + " ".join(missing))


def check_engine():
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codepaint import Blend, Canvas, Linear, Perspective, Radial, color, figure, io, motifs, props
    from codepaint import solids as s3
    from codepaint import geometry as g
    from codepaint.styles import anime, illustration, oil, watercolor

    # color
    assert np.allclose(color.rgb("#ff8000"), [1.0, 128 / 255, 0.0])
    assert np.allclose(color.rgb("#fff"), [1.0, 1.0, 1.0])
    assert color.luminance(color.shade("#e08040")) < color.luminance(color.rgb("#e08040"))
    try:
        color.rgb("#12345")
    except ValueError:
        pass
    else:
        raise AssertionError("an invalid color string was accepted")

    # paths
    square = g.spline([(0, 0), (10, 0), (10, 10), (0, 10)], closed=True, corners=(0, 1, 2, 3))
    assert abs(abs(g.signed_area(square)) - 100.0) < 1e-6, "breaking all 4 corners must give a square"
    frame = g.Frame(origin=(100, 50), unit=10, rotate=90)
    assert np.allclose(frame.point(1, 0), (100, 60)), "a clockwise 90 degrees on screen must move right to down"
    assert np.allclose(frame.mirrored().point(1, 0), (100, 40))

    # shapes and paint
    cv = Canvas(200, 200, scale=1.0, background="#000000")
    disc = cv.shape(g.ellipse(100, 100, 50))
    area = float(disc.mask.sum())
    assert abs(area - np.pi * 50 ** 2) / (np.pi * 50 ** 2) < 0.01, "circle area is off by more than 1%"
    cv.fill(disc, "#ffffff")
    assert cv.image()[100, 100].min() > 0.99 and cv.image()[5, 5].max() < 0.01
    cv.fill(cv.shape(g.rect(0, 0, 200, 200)), "#ff0000", clip=disc, blend=Blend.MULTIPLY)
    assert np.allclose(cv.image()[100, 100], [1, 0, 0], atol=0.01), "multiply blend result differs"
    assert cv.image()[5, 5].max() < 0.01, "paint landed outside clip"
    shadow = cv.form_shadow(disc, (-1, -1), amount=0.4)
    fraction = float(shadow.mask.sum()) / area
    assert 0.35 < fraction < 0.45, f"shadow area ratio differs from amount: {fraction:.2f}"
    assert shadow.mask[130 - shadow.y0, 130 - shadow.x0] > 0.9, "shadow is not on the side away from the light"
    rim = cv.edge_light(disc, (0, -1), width=8)
    assert rim.mask[55 - rim.y0, 100 - rim.x0] > 0.9 and rim.mask[145 - rim.y0, 100 - rim.x0] < 0.1, \
        "rim light is not on the light-facing contour"
    cv.fill(disc, Linear(["#000000", "#ffffff"], (50, 0), (150, 0)))
    assert cv.image()[100, 60].mean() < cv.image()[100, 140].mean()
    cv.fill(disc, Radial(["#ffffff", "#000000"], (100, 100), 50))
    assert cv.image()[100, 100].mean() > cv.image()[100, 140].mean()
    cv.stroke([(20, 20), (180, 20)], "#00ff00", width=6, taper=(0, 1, 0))
    assert cv.image()[20, 100, 1] > 0.9 and cv.image()[20, 22, 1] < 0.5, "line ends do not taper"
    empty = cv.shape(g.rect(500, 500, 10, 10))
    cv.fill(empty, "#ffffff")  # off-screen shapes must be ignored without errors
    cv.fill(cv.contour(empty, 2.0), "#ffffff")  # the same holds for outlines of parts cut off by the frame (feet in a knee-up composition)

    layer = Canvas(200, 200, background=None)
    layer.fill(layer.shape(g.ellipse(100, 100, 30)), "#0000ff")
    assert layer.alpha[100, 100] > 0.99 and layer.alpha[5, 5] == 0.0
    cv.paste(layer)
    assert np.allclose(cv.image()[100, 100], [0, 0, 1], atol=0.01)
    assert Canvas.from_image(cv.image(), 200, 200).rgb.shape == cv.rgb.shape
    assert io.crop(cv.image(), (50, 50, 150, 100), 1.0, zoom=2.0).shape == (100, 200, 3)
    assert io.sheet([cv.image()] * 3, columns=2).shape[1] > 400

    # body rig: bone lengths must keep head-count proportions in any pose
    unit = 40.0
    body = figure.Figure(g.Frame((100, 200), unit), hip_tilt=9, chest_tilt=-7, spine=-4,
                         arm_l=(150, 215), arm_r=(35, -60), leg_l=(6, 0), leg_r=(-4, 14))
    for start, end, bone in (("shoulder_l", "elbow_l", "upper_arm"), ("elbow_r", "wrist_r", "forearm"),
                             ("hip_l", "knee_l", "thigh"), ("knee_r", "ankle_r", "shin")):
        length = np.linalg.norm(np.subtract(body.joint(start), body.joint(end)))
        assert abs(length - figure.BONE_LENGTH[bone] * unit) < 1e-6, f"{bone} length changes with the pose"
    assert body.joint("head")[1] < body.joint("shoulder_mid")[1] < body.joint("pelvis")[1] < body.joint("knee_l")[1]
    assert body.joint("elbow_l")[1] < body.joint("shoulder_l")[1], "the elbow of an arm raised to 150 degrees is not above the shoulder"
    short = figure.Figure(g.Frame((100, 200), unit), stretch={"thigh_l": 0.5})
    assert abs(np.linalg.norm(np.subtract(short.joint("hip_l"), short.joint("knee_l")))
               - figure.BONE_LENGTH["thigh"] * unit * 0.5) < 1e-6
    dropped = figure.Figure(g.Frame((100, 200), unit), shoulder_drop=0.12)
    assert abs(dropped.joint("shoulder_l")[1] - figure.Figure(g.Frame((100, 200), unit)).joint("shoulder_l")[1]
               - 0.12 * unit) < 1e-6, "shoulder_drop does not lower the shoulder joint"
    base = figure.Figure(g.Frame((100, 200), unit), stretch={"neck": 0.72})
    head_top = base.joint("head")[1] - 0.5 * unit
    sole = max(path[:, 1].max() for path in base.foot("l", view="bare_front"))
    assert abs((sole - head_top) / unit - 8.04) < 0.05, f"full figure measured to the bare sole is not eight heads: {(sole - head_top) / unit:.2f}"
    assert len(base.foot("r", view="bare_front")) == 6 and len(base.foot("r", view="bare_back")) == 1
    toes = base.toes("l")
    assert len(toes) == 5 and all(len(pair) == 2 for pair in toes)
    widths = [np.ptp(toe[:, 0]) for toe, _ in toes]
    assert widths[0] == max(widths), "the big toe is not the thickest"
    tips = [toe[:, 1].max() for toe, _ in toes]
    assert tips[0] > tips[-1], "the big toe tip is not ahead of the little toe"
    lying = figure.Figure(g.Frame((200, 100), unit, rotate=-90))
    assert lying.joint("head")[0] < lying.joint("pelvis")[0] and abs(lying.joint("head")[1] - 100) < 1e-6, \
        "the head of a rig rotated 90 degrees counterclockwise is not on screen left"
    silhouette = figure.shape_of(cv, [path for paths in body.parts().values() for path in paths])
    assert silhouette.mask.max() > 0.99
    sleeve = figure.shape_of(cv, body.limb("forearm", "r", scale=1.5)).mask.sum()
    assert sleeve > figure.shape_of(cv, body.limb("forearm", "r")).mask.sum(), "scale is not applied to thickness"

    # hands: bent fingers seen from the back of the hand get shorter, and joint coordinates consist of the
    # root and 3 joints
    hand_frame = g.Frame((100, 100), 80)
    flat, bent = figure.hand_open(hand_frame), figure.hand_open(hand_frame, curl=0.8)

    def reach(hand):
        return np.linalg.norm(np.subtract(hand.joints["middle"][-1], hand.joints["middle"][0]))

    assert len(flat.joints["index"]) == 4 and set(flat.parts) == {"palm", "index", "middle", "ring", "pinky", "thumb"}
    assert reach(bent) < reach(flat) * 0.6, "bent fingers do not get shorter"
    assert abs(reach(flat) - 0.45 * 80) < 1e-6, "the open middle finger is not 0.45 of the hand length"
    side = figure.hand_side(hand_frame, curl=1.0)
    assert side.joints["index"][-1][0] < side.joints["index"][0][0], "side-view fingers do not bend toward the palm"
    assert len(side.paths()) > 10

    # perspective: evenly spaced points approach the vanishing point with distance, and depth-parallel lines
    # meet at the vanishing point
    view = Perspective(vanish=(500, 300), eye_height=1.6, focal=800)
    near, far, farther = view.project(-4, 0, 5), view.project(-4, 0, 20), view.project(-4, 0, 5000)
    assert near[0] < far[0] < 500 and near[1] > far[1] > 300
    assert abs(farther[0] - 500) < 1.0 and abs(farther[1] - 300) < 1.0, "far points do not converge on the vanishing point"
    assert abs(view.project(3, 1.6, 7)[1] - 300) < 1e-6, "a point at eye level is not on the horizon"
    assert abs(view.scale_at(10) - 80) < 1e-6
    assert len(view.side_wall_grid(-4, 5, 15, 0, 9, 4, 3)) == 12
    try:
        view.project(0, 0, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("depth 0 was accepted")

    # solids: only faces toward the camera are visible, and every cylinder piece normal must point outward
    camera = s3.Camera(eye=(0, 30, -60), target=(0, 0, 0), focal=1000, center=(500, 300))
    cube = s3.box((0, 0, 0), (10, 10, 10))
    assert {face.name for face in camera.visible_faces(cube)} == {"front", "top"}, "visible faces of a box seen from front and above differ"
    turned = cube.rotated(yaw=30)
    assert "right" in {face.name for face in camera.visible_faces(turned)}, "with positive yaw the right face does not turn into view"
    assert turned.face("front").normal[0] < 0, "with positive yaw the front does not turn toward screen left"
    tilted = cube.rotated(pitch=30)
    assert tilted.face("top").normal[2] > 0, "with positive pitch the top does not tip back"
    can = s3.cylinder((0, 0, 0), 5, 10, segments=32)
    for face in can.faces:
        if face.name == "side":
            outward = face.center - np.array([0, face.center[1], 0])
            assert np.dot(face.normal, outward) > 0, "cylinder side normals point inward"
    side_visible = [face for face in camera.visible_faces(can) if face.name == "side"]
    assert 14 <= len(side_visible) <= 18, f"visible side pieces of a cylinder seen from the front are not half: {len(side_visible)}"
    lying = s3.slab((0, 0, 0), (8, 16, 1), 1.0).rotated(pitch=90)
    assert lying.face("front").normal[1] > 0.99, "the front of a slab laid down with pitch 90 does not face up"
    top = cube.face("top")
    assert np.allclose(top.point(0, 0), (-5, 5, 5)) and np.allclose(top.point(1, 1), (5, 5, -5)), \
        "u, v directions of the box top differ from the docs"
    near, far = camera.project((0, 0, -10)), camera.project((0, 0, 10))
    assert near[1] > far[1] and camera.scale_at((0, 0, -10)) > camera.scale_at((0, 0, 10))
    assert np.allclose(camera.project((0, 0, 0)), (500, 300)), "the target point is not at the screen center"
    try:
        camera.project((0, 30, -70))
    except ValueError:
        pass
    else:
        raise AssertionError("a point behind the camera was accepted")
    sketch = Canvas(1000, 600, scale=0.5, background="#ffffff")
    shapes = s3.draw(sketch, camera, cube, {"front": "#ff0000", "*": "#0000ff"}, (-0.5, 0.8, -0.4), line="#000000")
    assert set(shapes) == {"front", "top", "silhouette"}
    shade_front = s3.face_color("#808080", (0, 0, -1), (0, 1, 0))
    shade_top = s3.face_color("#808080", (0, 1, 0), (0, 1, 0))
    assert color.luminance(shade_top) > color.luminance(shade_front), "the face toward the light is not brighter"
    desk = props.laptop((0, 0, 0), yaw=20)
    assert set(desk.solids) == {"base", "lid"} and set(desk.faces) == {"screen", "deck"}
    assert desk.faces["screen"].normal[2] < 0, "the laptop screen does not face the camera"
    lamp = props.desk_lamp((0, 0, 20))
    lamp.draw(sketch, camera, {"base": "#333333", "shade": "#333333", "arm": "#333333"}, (0, 1, 0))
    props.keycaps(sketch, camera, props.keyboard((0, 0, 0)).faces["keys"], "#eeeeee")
    ring = sketch.contour(sketch.shape(g.ellipse(500, 300, 100)), 6)
    assert ring.mask[(300 - 100) // 2 + 1 - ring.y0, 500 // 2 - ring.x0] > 0.9, "contour does not make a band on the outline"
    assert ring.mask[300 // 2 - ring.y0, 500 // 2 - ring.x0] < 0.01, "contour fills the whole inside of the shape"

    # 3D rig: the front view matches the planar rig, and turning changes the near side and the paint order
    from codepaint.figure3d import MALE_DEPTH, Figure3D
    from codepaint.head3d import FEMALE_HEAD, HairStyle, Head3D, Lock
    frame = g.Frame((400, 800), 150)
    planar_pose = dict(hip_tilt=-6, chest_tilt=4, spine=-1, head=-3, arm_l=(11, 5), arm_r=(13, 3), leg_l=(6, 1),
                       leg_r=(3, -1), stretch={"neck": 0.72}, shoulder_drop=0.12)
    flat, solid = figure.Figure(frame, **planar_pose), Figure3D(frame, **planar_pose)
    for name in flat.joints:
        assert np.allclose(flat.joint(name), solid.joint(name)), f"joints at turn 0 differ from the planar rig: {name}"
    assert np.allclose(flat.torso()[0], solid.torso()[0]), "torso outline at turn 0 differs from the planar rig"
    assert [name for name, _ in solid.groups()] == ["body"], "limbs are not one mass with the body in front view"
    side = Figure3D(frame, build=figure.MALE, depth=MALE_DEPTH, turn=90)
    assert side.depth_of(side.joints3["shoulder_l"]) < side.depth_of(side.joints3["shoulder_r"]), \
        "the _l side is not nearer at turn 90"
    order = [name for name, _ in side.groups()]
    assert order[0] == "arm_r" and order[-1] == "arm_l" and "leg_l" not in order, f"profile paint order differs: {order}"
    assert side.facing((0, 0, -1)) < 0.01 and side.facing((-1, 0, 0)) > 0.99, "the facing direction at turn 90 is not screen right"
    back = Figure3D(frame, turn=180)
    assert np.isclose(back.joint("wrist_l")[0] - 400, 400 - Figure3D(frame).joint("wrist_l")[0]), "the back view is not mirrored left to right"
    assert len(Figure3D(frame).toes("l")) == 5 and back.toes("l") == [], "toes are visible outside the front view"
    raised = Figure3D(frame, foot_pitch={"l": 30})
    assert raised.foot("l")[0][:, 1].max() > Figure3D(frame).foot("l")[0][:, 1].max(), "raising the heel does not lower the toes"
    seated = Figure3D(frame, turn=30, swing={"leg_l": (90, 0), "leg_r": (90, 0)})
    assert "leg_l" in [name for name, _ in seated.groups()], "the near seated leg is not painted apart from the body"
    assert seated.joints3["knee_l"][2] < -1.9, "raising the thigh 90 degrees does not bring the knee forward"

    # 3D head: frontal face table coordinates land unchanged, and turning hides the far eye and closes the
    # face area
    style = HairStyle(thickness=0.12, hairline=((0, -0.45), (90, 0.1), (180, 0.8)),
                      locks=(Lock((0, -0.9), (0, 0.1), 0.3), Lock((180, -0.7), (180, 1.0), 0.5)))
    head_frame = g.Frame((300, 300), 50)
    front_head = Head3D(head_frame, FEMALE_HEAD)
    assert np.allclose(front_head.face().point(0.45, 0.4), head_frame.point(0.45, 0.4)), "frontal face coordinates are off"
    assert len(front_head.silhouette()) == 2 and front_head.face_window(style) is not None
    layers = front_head.locks(style)
    assert len(layers["front"]) == 1 and len(layers["back"]) == 1, "front and back hair layers are not split in front view"
    profile = Head3D(head_frame, FEMALE_HEAD, yaw=90)
    assert profile.face().facing(-0.45, 0.4) > 0.1 > profile.face().facing(0.45, 0.4), "the far eye remains in profile"
    assert profile.ear("l")[2] > 0.5 > profile.ear("r")[2], "the near ear does not come forward in profile"
    assert profile.nose_tip()[0] > max(path[:, 0].max() for path in profile.silhouette()) - 1.0, "the nose tip is not on the profile outline"
    behind = Head3D(head_frame, FEMALE_HEAD, yaw=180)
    assert behind.face_window(style) is None and len(behind.locks(style)["back"]) == 1, "the face area remains in the back view"

    # clothing: torso garments are wider than the body, hems cover walking legs, and capes hang behind the
    # body in front view
    from codepaint import character, garment
    from codepaint.stage import Stage
    dressed = Figure3D(frame, build=figure.MALE, depth=MALE_DEPTH)
    shirt = garment.loft(dressed, ("thorax", -0.18), ("pelvis", -0.3), 0.08).outline()
    assert np.ptp(shirt[:, 0]) > np.ptp(dressed.torso()[0][:, 0]), "the shirt is narrower than the torso"
    walker = Figure3D(frame, swing={"leg_l": (25, 5), "leg_r": (-20, -30)})
    skirt = garment.loft(walker, ("pelvis", -0.6), None, 0.04, hem=garment.Hem(3.2, 0.3))
    knee_z = walker.local_point("pelvis", 0, 0, 0)[2] + walker.joints3["knee_l"][2]
    hem_front = min(section.cz - section.front for section in skirt.sections if section.y > 1.8)
    assert hem_front < knee_z, "the knee of the walking front leg leaves the skirt hem"
    front_cape = garment.mage_robe()(Figure3D(frame))[-1]
    back_cape = garment.mage_robe()(Figure3D(frame, turn=180))[-1]
    assert front_cape.group == "cape" and front_cape.facing < 0 < back_cape.facing, "the cape does not hang behind the back"
    pieces = character._merged([piece for piece in garment.casual_shirt()(dressed) if piece.merge == "pants"])
    assert len(pieces) == 1, "trouser waist and legs do not merge into one piece"

    # stage: feet touch the floor, a reached wrist meets its target, and held-back masses can be painted later
    stage = Stage((500, 900), 100, elevation=5)
    target = np.array([0.6, -5.0, -0.6])
    walker_model = stage.place(character.FEMALE, 0.0, 0.0, 30.0, reach={"arm_r": target})
    assert np.linalg.norm(stage.joint_world(walker_model, "wrist_r") - target) < 0.02, "the reached wrist does not meet the target"
    soles = [stage.to_world(walker_model, point)[1] for side in "lr" for point in walker_model.body._foot_cloud(side)]
    assert abs(max(soles)) < 1e-6, "the sole does not touch the floor (y 0)"
    assert np.allclose(stage.project([walker_model.world])[0], walker_model.body.joint("pelvis")), "stage and rig projections disagree"
    from codepaint.stage import ELBOW_POLE
    default_pole = stage.place(character.FEMALE, 0.0, 0.0, 30.0, reach={"arm_r": target}, poles={"arm_r": ELBOW_POLE})
    assert np.allclose(stage.joint_world(default_pole, "elbow_r"), stage.joint_world(walker_model, "elbow_r")), \
        "an elbow with poles set to ELBOW_POLE differs from the default"
    inward = stage.place(character.FEMALE, 0.0, 0.0, 30.0, reach={"arm_r": target}, poles={"arm_r": (-0.5, 1.0, 0.0)})
    assert np.linalg.norm(stage.joint_world(inward, "wrist_r") - target) < 0.02, "with poles the wrist does not meet the target"
    assert stage.to_world(inward, inward.body.joints3["elbow_r"])[0] < stage.joint_world(walker_model, "elbow_r")[0], \
        "the elbow of an inner pole does not move toward the body"
    holder = stage.place(character.MALE, 0.0, 0.0, -20.0, fists={"arm_l": target}, grips=("l",))
    assert np.linalg.norm(stage.fist_world(holder, "l") - target) < 0.001, "the fist center aligned by fists does not meet the target"
    crowded = [stage.place(character.MALE, x, 0.0, 0.0) for x in (0.0, 1.2)]
    assert any(hit.part == "torso" for hit in stage.collisions(crowded)), "an arm piercing the torso was not found"
    touching = stage.collisions([stage.place(character.MALE, x, 0.0, 0.0) for x in (0.0, 2.2)])
    assert touching and all(hit.part != "torso" for hit in touching), "two arms overlapping outside the torso were not found as arm-to-arm penetration"
    assert stage.collisions([stage.place(character.MALE, x, 0.0, 0.0) for x in (0.0, 4.0)]) == [], \
        "penetration found between two people standing apart"
    sitter = stage.place(character.MALE, 1.0, 0.0, -80.0, outfit=garment.casual_shirt(), reach={"arm_r": target},
                         swing={"leg_l": (88, 0), "leg_r": (88, 0)})
    small = Canvas(1000, 1000, scale=0.25, background=None)
    character.paint_figure(small, sitter, defer=("arm_r",))
    before = small.alpha.sum()
    character.paint_deferred(small, sitter, ("arm_r",))
    assert small.alpha.sum() > before, "the held-back arm could not be painted later"
    clasp = stage.place(character.FEMALE, 0.0, 0.0, 0.0, grips=("r",), palm_out=("r",))
    plain = stage.place(character.FEMALE, 0.0, 0.0, 0.0, grips=("r",))
    flipped = character.choose_hand(clasp, "r")[0].joints["index"][-1][0] - clasp.body.joint("wrist_r")[0]
    normal = character.choose_hand(plain, "r")[0].joints["index"][-1][0] - plain.body.joint("wrist_r")[0]
    assert flipped * normal < 0, "palm_out does not flip the finger direction of the closed hand"

    # face and hair templates: the default face is the default for the sex, restyle changes the face shape
    # too, and moving head coordinates to body coordinates keeps the screen position
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
            "moving head coordinates to body coordinates changes the screen position"
        pierced = straight = 0
        for lock in (lock for lock in soft.hair.locks if lock.drape):
            points = [center + matrix @ point for point, _ in model.head.lock_samples(soft.hair, lock,
                                                                                   hairstyles.DRAPE_SAMPLES)]
            straight += sum(model.body.inside_torso(point) for point in points)
            pierced += sum(model.body.inside_torso(point) for point in hairstyles.drape(model.body, points, lock.drape))
        assert straight > 0 and pierced == 0, f"long hair locks pierce the torso: {straight} points straight, {pierced} points after drape"
    plain = character.place(character.FEMALE, (200, 300), 80, 30.0)
    plain_layers = hairstyles.lock_layers(plain)
    assert [len(plain_layers[name]) for name in ("back", "front")] == \
        [len(paths) for paths in plain.head.locks(character.FEMALE.hair).values()] and not plain_layers["tucked"], \
        "layers of hair without drape changed"
    turned = character.place(soft, (200, 300), 80, 20.0, head_turn=22.0)
    assert hairstyles.lock_layers(turned)["tucked"], "no long lock passing behind the face was found at 3/4 view"
    pink = character.restyle(character.FEMALE, hair_color=hairstyles.HAIR_COLORS["pink"])
    assert (pink.palette.hair, pink.palette.line_hair) == ("#efa2ba", "#682840") and \
        replace(pink.palette, hair=character.FEMALE.palette.hair, hair_shade=character.FEMALE.palette.hair_shade,
                hair_light=character.FEMALE.palette.hair_light, line_hair=character.FEMALE.palette.line_hair) == \
        character.FEMALE.palette, "the hair color changed palette entries beyond the four hair colors"

    # style passes and reproducibility
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
        assert first.shape == (160, 240, 3), f"{name}: output size differs"
        assert 0.0 <= first.min() and first.max() <= 1.0, f"{name}: values out of range"
        assert np.array_equal(first, second), f"{name}: results differ with the same seed"
        assert not np.array_equal(first, render(scene(4))), f"{name}: the seed does not affect the result"


if __name__ == "__main__":
    check_dependencies()
    check_engine()
    print("OK")
