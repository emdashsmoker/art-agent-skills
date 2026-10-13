#!/usr/bin/env python3
"""Fast sanity checks for the toolkit. Run after changing any rig or style code.

    python selftest.py

Exits non-zero on the first failed check. These checks catch structural
mistakes (bald spots, eyes off the face, non-reproducible output); they do
not judge beauty, which still needs a look at the render.
"""
import hashlib
import importlib.util
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR / "examples"))

from codeillust import background, city, rig_figure, rig_hand, studio, terrain  # noqa: E402
from codeillust.canvas import Canvas  # noqa: E402
from codeillust.character import Head, adult_face, default_character, default_palette  # noqa: E402
from codeillust.config import DEFAULT_LIGHT, STYLES, StyleName, rgb  # noqa: E402
from codeillust.figure import draw_character  # noqa: E402
from codeillust.finish import figure_mask  # noqa: E402
from codeillust.geometry import ellipse  # noqa: E402
from codeillust.painter import Painter  # noqa: E402
from codeillust.relief import FRONT, Relief  # noqa: E402

TEST_PX_PER_UNIT = 0.4
MIN_FIGURE_SHARE = 0.30       # the subject must dominate a portrait
MIN_EYES_ON_FACE = 0.90       # share of eye pixels that lie on the face
MAX_BALD_SHARE = 0.01         # skull above the hairline must be covered by hair
MIN_IMAGE_CONTRAST = 0.08     # standard deviation of a non-empty picture
MIN_STYLE_DIFFERENCE = 0.02   # mean absolute difference between two styles
HAIRLINE_Y = -0.35            # head units; above this only hair may show
LENGTH_TOLERANCE = 1e-6       # limb lengths must survive any pose exactly
EXAMPLE_SCENES = ("landscape_lake", "city_dusk", "still_life", "hand_study", "full_body", "swimwear_beach",
                  "dressup_base", "turnaround3d", "beach_pair3d", "desk_setup3d", "desk_worker3d", "living_game3d",
                  "cafe3d", "props_sheet3d", "bedroom3d", "doomer_man", "doomer_woman", "doomer_pair",
                  "doomer_establishing", "doomer_city", "doomer_landscape", "doomer_still", "night_desk",
                  "sunny_reading", "dusk_bench", "beach_sunset")
REPRODUCED_EXAMPLES = ("still_life", "turnaround3d", "desk_worker3d")
TEST3D_PX_PER_UNIT = 0.5
TEST3D_YAWS = (0.0, 1.2, 3.1416)
GARMENT_NAMES = ("cloth", "shoes")
MIN_HOLE_PX = 3               # skin islands smaller than this are anti-aliasing, not a hole
REACH_TOLERANCE = 1e-3        # head heights between a reached wrist and its target
EXAMPLE_PX_PER_UNIT = 0.3
FAR_EYE = 1e6                 # head heights: an eye this far is orthographic in effect
SDF_DEPTH_TOLERANCE = 0.01    # head heights between a traced front face and its true depth
MIN_OBJECT_PX = 20            # an object builder must cover at least this many pixels
MAX_HELD_DISTANCE = 0.8       # head heights from the wrist to the centre of a held object
SEAT_TOLERANCE = 0.05         # head heights of difference in sole height between sitting poses
MAX_BARE_SHARE = 0.001        # share of a room frame the shell may leave unpainted
MIN_SCREEN_CHANGE = 0.15      # a lit screen must differ this much (RGB) from the dark panel under it
PROP_BUILDERS = tuple(("props3d", name) for name in (
    "laptop", "monitor", "keyboard", "mouse", "phone", "tablet", "headphones", "game_controller", "mug", "paper_cup",
    "book", "book_stack", "desk_lamp", "potted_plant", "television", "drinking_glass", "cigarette", "ashtray",
    "tea_glass", "cassette", "cassette_player"))
FURNITURE_BUILDERS = tuple(("furniture3d", name) for name in (
    "desk", "office_chair", "sofa", "low_cabinet", "coffee_table", "cafe_table", "cafe_chair", "counter", "bookshelf",
    "pendant_lamp", "floor_lamp", "rug", "bed", "radiator", "windowsill"))
STREET_BUILDERS = tuple(("street3d", name) for name in ("street_lamp", "power_pole", "bench", "bus_stop", "birch"))
MAX_SINK = 0.06               # head heights a body part may hang below the floor a figure is set on (FLOOR_SLACK)
MIN_LYING_SPAN = 5.0          # head heights between the body parts a figure lying on its back rests on
MIN_GLASS_SHOW = 0.25         # how much of the backdrop's brightness must show through a clear glass
STRING_TOLERANCE = 1e-3       # head heights a bikini string may sit nearer the skin than its clearance
PAINT_SMALL_FACE = 0.95       # painterly detail a small face must earn (the finest brush layer)
THIGH_TOP = 0.17              # head heights from a thigh's axis to just under its top surface
GAP_SIDES = (-0.103, 0.103)            # head heights: two forms a hair's width apart (0.006 at the middle)
GAP_CAPS = (-0.15, 0.15)               # and two small forms closing the gap above and below
MAX_CUFF_PX = 20                       # cuff pixels that may show at the edge of a pocket
RING_MAJOR, RING_MINOR = 0.04, 0.015   # head heights: a ring with a hole smaller than a closable gap
BACK_LIGHT = (0.0, -0.45, -0.89)        # light from behind the figure, a little above
GRADE_MAX_CHROMA = 0.6        # share of a saturated patch's colourfulness the doomer grade may keep
ROUND_TRIP_TOLERANCE = 1e-4   # canvas units and head heights a pixel may move on its way to the world and back
ROUND_TRIP_PIXELS = ((40, 60, -10.0), (150, 200, 5.0), (260, 330, 20.0))   # row, column, view depth
NIGHT_DARK = 0.6              # a night-lit object away from any lamp keeps at most this share of its brightness
EMBER_BRIGHT = 0.6            # an ember must stay this bright (max channel) in a dark night scene
WARM_GRADE_MIN_CHROMA = 0.75  # share of a saturated patch's colourfulness a warm grade must keep
VIEW_DARK_SKY = 0.25          # mean luma of the top of a night window view stays below this
VIEW_BRIGHT_DISC = 0.85       # the moon or sun disc in a window view reaches this luma
LAMP_WALL_GAIN = 1.3          # a wall next to a room lamp is at least this much brighter than its far end
MIN_THIN_OVERLAP = 0.99       # a thin far sweep with touching spheres must cover what fine stepping covers
THIN_SPEEDUP = 4              # and use at least this many times fewer spheres
STRAP_TOLERANCE = 0.01        # head heights a shoulder strap may stand off or sink into the shoulder


def compose(painter):
    background.vertical_gradient(painter.canvas, (0.55, 0.75, 0.95), (0.85, 0.93, 1.0))
    draw_character(painter, default_character())


def render(style, directory, name):
    path = Path(directory) / f"{name}.png"
    canvas = studio.render(compose, style, path, px_per_unit=TEST_PX_PER_UNIT)
    return canvas, hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    print(("PASS  " if condition else "FAIL  ") + message)
    if not condition:
        sys.exit(1)


def main():
    with tempfile.TemporaryDirectory() as directory:
        canvases = {}
        for style in StyleName:
            canvas, first_hash = render(style.value, directory, f"{style.value}_a")
            _, second_hash = render(style.value, directory, f"{style.value}_b")
            check(first_hash == second_hash, f"{style.value}: same seed gives the same file")
            check(float(canvas.rgb.std()) > MIN_IMAGE_CONTRAST, f"{style.value}: image is not blank")
            canvases[style] = canvas

        canvas = canvases[StyleName.ANIME]
        figure = figure_mask(canvas)
        check(float(figure.mean()) > MIN_FIGURE_SHARE, "figure fills enough of the frame")

        eyes, face = canvas.part("eyes"), canvas.part("face")
        on_face = float((eyes * (face > 0.5)).sum() / (eyes.sum() + 1e-9))
        check(on_face > MIN_EYES_ON_FACE, f"eyes sit on the face ({on_face:.2f})")

        character = default_character()
        head = Head(character)
        _, ys = canvas.grid()
        above_hairline = ys < head.flat([(0.0, HAIRLINE_Y)])[0][1]
        bald = (face > 0.5) & above_hairline & (canvas.part("hair_front") < 0.5)
        bald_share = float(bald.sum() / ((face > 0.5).sum() + 1e-9))
        check(bald_share < MAX_BALD_SHARE, f"no bald scalp above the hairline ({bald_share:.3f})")

        names = list(StyleName)
        for first, second in zip(names, names[1:] + names[:1]):
            difference = float(np.abs(canvases[first].rgb - canvases[second].rgb).mean())
            check(difference > MIN_STYLE_DIFFERENCE,
                  f"{first.value} and {second.value} look different ({difference:.3f})")
    check_relief()
    check_skeleton()
    check_hand()
    check_body_shape()
    check_outfits()
    check_terrain()
    check_city()
    check_rig3d()
    check_figure3d()
    check_perspective()
    check_sdf()
    check_scene3d()
    check_held_objects()
    check_rooms()
    check_floor_contact()
    check_layout()
    check_glass()
    check_garment_fit()
    check_painterly_faces()
    check_gaps_and_shadows()
    check_doomer()
    check_light_scenes()
    check_examples()
    print("all checks passed")


def _luma(image):
    return image @ np.array([0.299, 0.587, 0.114], dtype=np.float32)


def check_relief():
    """A lit sphere must be brighter toward the light, and a form placed in front must earn a line."""
    skin = default_palette().skin
    renders = {}
    for style in (StyleName.ILLUST, StyleName.ANIME):
        canvas = Canvas(300.0, 300.0, 1.0, 1)
        painter = Painter(canvas, STYLES[style], DEFAULT_LIGHT)
        relief = Relief(canvas)
        relief.add("ball", canvas.mask(ellipse((150.0, 150.0), 100.0, 100.0)), skin)
        relief.add("front", canvas.mask(ellipse((190.0, 190.0), 40.0, 40.0)), skin, depth=FRONT)
        relief.render(painter)
        renders[style] = (canvas, relief)
    canvas, _ = renders[StyleName.ILLUST]
    luma = _luma(canvas.rgb)
    check(float(luma[90:130, 90:130].mean()) > float(luma[60:100, 190:220].mean()) + 0.02,
          "relief: the side of a sphere facing the light is brighter")
    canvas, relief = renders[StyleName.ANIME]
    check(float(relief.overlap_edge.sum()) > 50.0, "relief: a form in front leaves an overlap edge")
    ring = _luma(canvas.rgb)[150:160, 152:162].min()
    inside = _luma(canvas.rgb)[185:195, 185:195].mean()
    check(float(ring) < float(inside) - 0.1, "relief: the overlap edge is drawn as a line in cel styles")


def check_skeleton():
    """Poses may only rotate joints: every limb keeps its length."""
    expected = {("shoulder", "elbow"): rig_figure.UPPER_ARM, ("elbow", "wrist"): rig_figure.FOREARM,
                ("hip", "knee"): rig_figure.THIGH, ("knee", "ankle"): rig_figure.SHIN}
    for name in ("STANDING", "CONTRAPPOSTO", "HAND_ON_HIP", "ARM_RAISED"):
        figure = rig_figure.Figure(character=default_character(), pose=getattr(rig_figure, name), head_height=100.0)
        skeleton = rig_figure.Skeleton(figure)
        worst = 0.0
        for side in ("left", "right"):
            joints = skeleton.joints[side]
            for (start, end), length in expected.items():
                worst = max(worst, abs(np.linalg.norm(joints[end] - joints[start]) / 100.0 - length))
        check(worst < LENGTH_TOLERANCE, f"skeleton: limb lengths are constant in pose {name}")
    figure = rig_figure.Figure(character=default_character(), pose=rig_figure.STANDING, head_height=100.0,
                               pelvis=(0.0, 0.0))
    skeleton = rig_figure.Skeleton(figure)
    crown = skeleton.chin[1] - 100.0
    sole = skeleton.joints["left"]["ankle"][1] + 0.38 * 100.0
    heads = (sole - crown) / 100.0
    check(7.2 < heads < 7.8, f"skeleton: the standing figure is about 7.5 heads tall ({heads:.2f})")


def check_hand():
    """Finger proportions: the middle finger is longest and a curled finger looks shorter."""
    def visible_length(name, pose):
        points, _ = rig_hand._finger_segments(name, pose)
        return sum(np.linalg.norm(points[i + 1] - points[i]) for i in range(len(points) - 1))

    lengths = {name: visible_length(name, rig_hand.OPEN_HAND) for name in rig_hand.FINGERS}
    check(max(lengths, key=lengths.get) == "middle" and min(lengths, key=lengths.get) == "pinky",
          "hand: middle finger longest, little finger shortest")
    check(visible_length("ring", rig_hand.VICTORY_HAND) < 0.6 * visible_length("ring", rig_hand.OPEN_HAND),
          "hand: a folded finger is foreshortened")
    tips = [rig_hand._finger_segments(name, rig_hand.OPEN_HAND)[0][-1][1] for name in rig_hand.FINGERS]
    check(0.93 < max(tips) < 1.07, f"hand: wrist to middle fingertip is one hand unit ({max(tips):.3f})")


def _torso_half_widths(body):
    """Half widths of the torso outline at the waist and at the widest hip point (head heights)."""
    waist = [x * body.channel(ch) for x, _, _, ch in rig_figure.TORSO_HALF if ch == "waist"][0]
    hips = max(x * body.channel(ch) for x, _, _, ch in rig_figure.TORSO_HALF if ch == "hips")
    return waist, hips


def check_body_shape():
    """Shape presets must order sensibly, and the adult face must differ from the portrait face."""
    ratios = {}
    for name in ("SLENDER", "AVERAGE", "HOURGLASS"):
        waist, hips = _torso_half_widths(getattr(rig_figure, name))
        ratios[name] = waist / hips
    check(ratios["HOURGLASS"] < ratios["AVERAGE"], f"body: hourglass has the smaller waist-to-hip ratio {ratios}")
    check(min(ratios.values()) > 0.35, "body: no preset pinches the waist beyond a plausible shape")
    small = rig_figure.breast_geometry(rig_figure.AVERAGE, 1.0)
    large = rig_figure.breast_geometry(rig_figure.HOURGLASS, 1.0)
    check(large[1] > small[1] and large[0][0] - large[1] >= 0.0,
          "body: a fuller bust is larger and still leaves a gap at the midline")
    portrait, adult = default_character(), adult_face(default_character())
    check(adult.lower_face > 1.05 and adult.eye_half_width < portrait.eye_half_width,
          "face: the adult preset has a longer lower face and smaller eyes")


def check_outfits():
    """Every outfit is registered, and swimwear covers the chest and the pelvis."""
    missing = [outfit.value for outfit in rig_figure.FigureOutfit if outfit not in rig_figure.OUTFITS]
    check(not missing, f"outfits: every FigureOutfit has a drawing routine (missing: {missing})")
    figure = rig_figure.Figure(character=adult_face(default_character()), pose=rig_figure.A_POSE,
                               pelvis=(500.0, 650.0), head_height=158.0, body=rig_figure.HOURGLASS,
                               outfit=rig_figure.FigureOutfit.BIKINI)
    canvas = Canvas(1000.0, 1333.0, 0.4, 1)
    painter = Painter(canvas, STYLES[StyleName.ILLUST], DEFAULT_LIGHT)
    relief, skeleton = rig_figure.draw_figure(painter, figure)
    covered = relief.visible("swim")
    points = [skeleton.chest.apply([rig_figure.breast_geometry(figure.body, sign)[0]])[0] for sign in (-1.0, 1.0)]
    points.append(skeleton.pelvis.apply([(0.0, 0.15)])[0])
    hits = [float(covered[int(canvas.px(y)), int(canvas.px(x))]) for x, y in points]
    check(all(hit > 0.5 for hit in hits), f"outfits: the bikini covers both breasts and the pelvis {hits}")


def check_terrain():
    """The projected terrain must leave no hole below the horizon and must contain a lake."""
    canvas = Canvas(1333.0, 1000.0, 0.3, 3)
    heightmap, sea_level = terrain.alpine_lake_heightmap(canvas.rng)
    light = np.array([-0.55, -0.30, 0.78])
    color, ground, water = terrain.colorize(heightmap, sea_level, canvas.rng, light / np.linalg.norm(light))
    camera = terrain.Camera(eye_height=85.0, horizon=540.0)
    land, lake, _ = terrain.render(canvas, ground, color, water, camera)
    below = land[int(canvas.px(camera.horizon)) + 4:]
    check(float(below.mean()) > 0.999, f"terrain: no holes below the horizon ({below.mean():.4f})")
    check(0.03 < float(lake.mean()) < 0.6, f"terrain: a lake is visible ({lake.mean():.3f})")
    check(float(heightmap.max()) > 300.0, "terrain: mountains reach their peak height")


def check_city():
    """Lines running down the street must meet at the vanishing point."""
    camera = city.StreetCamera()
    far = camera.project([(-9.0, 0.0, 1e7), (9.0, 30.0, 1e7), (0.0, 1.6, 50.0)])
    error = float(np.abs(far - np.asarray(camera.vanishing_point)).max())
    check(error < 0.01, f"city: parallel street lines converge on the vanishing point ({error:.4f})")
    near, deep = camera.project([(9.0, 0.0, 10.0), (9.0, 0.0, 40.0)])
    check(near[0] > deep[0] and near[1] > deep[1], "city: nearer ground points sit lower and further out")
    building = city.Building(side=1, near=10.0, depth=30.0, height=40.0, wall=np.array([0.4, 0.4, 0.5]),
                             lit_share=0.5)
    _, glow = city.facade_texture(np.random.default_rng(1), building, np.array([0.9, 0.6, 0.5]))
    check(0.05 < float(glow.mean()) < 0.35, f"city: about half the windows are lit ({glow.mean():.3f})")


def check_examples():
    """Every example scene must run, and one of them must be reproducible."""
    with tempfile.TemporaryDirectory() as directory:
        for name in EXAMPLE_SCENES:
            spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / "examples" / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            size = getattr(module, "CANVAS_UNITS", (1000.0, 1333.0))
            hashes = []
            for attempt in range(2 if name in REPRODUCED_EXAMPLES else 1):
                path = Path(directory) / f"{name}_{attempt}.png"
                canvas = studio.render(module.compose, "illust", path, px_per_unit=EXAMPLE_PX_PER_UNIT,
                                       units_size=size)
                hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
            check(float(canvas.rgb.std()) > MIN_IMAGE_CONTRAST, f"example {name}: renders a picture")
            if len(hashes) == 2:
                check(hashes[0] == hashes[1], f"example {name}: same seed gives the same file")


def check_rig3d():
    """Every 3D pose on every build keeps bone lengths and proper rotations, and reaches its targets."""
    from codeillust import rig3d
    from codeillust.body3d import Skeleton3D
    builds = {"female_average": rig3d.FEMALE_AVERAGE, "female_fuller": rig3d.FEMALE_FULLER,
              "male_slim": rig3d.MALE_SLIM, "male_athletic": rig3d.MALE_ATHLETIC}
    worst_length, worst_rotation, worst_reach = 0.0, 0.0, 0.0
    for build in builds.values():
        joint_list = rig3d.joints(build)
        parents = {j.name: j for j in joint_list}
        for pose in rig3d.POSES.values():
            skeleton = rig3d.pose_skeleton(Skeleton3D, joint_list, pose)
            for joint in joint_list:
                if joint.parent is None:
                    continue
                length = np.linalg.norm(skeleton.position[joint.name] - skeleton.position[joint.parent])
                worst_length = max(worst_length, abs(length - np.linalg.norm(parents[joint.name].offset)))
                rotation = skeleton.rotation[joint.name]
                worst_rotation = max(worst_rotation, float(np.abs(rotation.T @ rotation - np.eye(3)).max()),
                                     abs(float(np.linalg.det(rotation)) - 1.0))
            for side, reach in pose.reach.items():
                target = skeleton.point(*reach.target)
                worst_reach = max(worst_reach, float(np.linalg.norm(skeleton.position[f"wrist_{side}"] - target)))
    check(worst_length < LENGTH_TOLERANCE, f"rig3d: every pose keeps every bone length ({worst_length:.2e})")
    check(worst_rotation < 1e-6, f"rig3d: every joint rotation stays a proper rotation ({worst_rotation:.2e})")
    check(worst_reach < REACH_TOLERANCE, f"rig3d: hands reach their targets ({worst_reach:.2e})")
    mirror, worst_mirror = np.diag([-1.0, 1.0, 1.0]), 0.0
    joint_list = rig3d.joints(rig3d.MALE_ATHLETIC)
    for pose in rig3d.POSES.values():
        skeleton = rig3d.pose_skeleton(Skeleton3D, joint_list, pose)
        flipped = rig3d.pose_skeleton(Skeleton3D, joint_list, rig3d.mirrored(pose))
        for name, position in skeleton.position.items():
            other = name.replace("_left", "_x").replace("_right", "_left").replace("_x", "_right")
            worst_mirror = max(worst_mirror, float(np.linalg.norm(mirror @ position - flipped.position[other])))
    check(worst_mirror < REACH_TOLERANCE, f"rig3d: a mirrored pose is the exact mirror image ({worst_mirror:.2e})")
    check(len(rig3d.POSES) >= 13, f"rig3d: {len(rig3d.POSES)} pose presets")


def _render3d(figure):
    from codeillust.figure3d import draw_figure3d
    canvas = Canvas(420.0, 560.0, TEST3D_PX_PER_UNIT, 7)
    painter = Painter(canvas, STYLES[StyleName.ANIME], DEFAULT_LIGHT)
    _, image, _, _ = draw_figure3d(painter, figure)
    return canvas, image


def _cloth_holes(image):
    """Skin islands completely ringed by garments: the body poking through the clothes."""
    import cv2
    names = np.array(image.names + ["(none)"])
    drawn = image.depth > -1e8
    label = np.where(drawn, names[np.clip(image.name_id, 0, None)], "(none)")
    skin = np.isin(label, ("body", "foot")) & drawn
    garment = np.isin(label, GARMENT_NAMES) & drawn
    count, components = cv2.connectedComponents(skin.astype(np.uint8), connectivity=8)
    holes = 0
    for index in range(1, count):
        island = components == index
        if island.sum() < MIN_HOLE_PX:
            continue
        ring = cv2.dilate(island.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~island
        if ring.any() and garment[ring].all():
            holes += 1
    return holes


def check_figure3d():
    """Every outfit preset covers the body from the front, side and back; figures stand about
    7.5 heads tall; faces show from the front and hide from behind."""
    from codeillust import head3d, rig3d, wardrobe3d
    from codeillust.character import male_face
    from codeillust.figure3d import Figure3D
    woman, man = adult_face(default_character()), male_face(default_character())
    holes = {}
    for name, outfit in wardrobe3d.OUTFITS.items():
        male = name in ("shirt_trousers", "swim_trunks", "suit")
        build = rig3d.MALE_ATHLETIC if male else rig3d.FEMALE_FULLER
        hair = head3d.MALE_SHORT_HAIR if male else head3d.PONYTAIL_HAIR
        for yaw in TEST3D_YAWS:
            figure = Figure3D(character=man if male else woman, build=build, pose=rig3d.CONTRAPPOSTO, hair=hair,
                              outfit=outfit, position=(210.0, 270.0), head_height=60.0, yaw=yaw)
            found = _cloth_holes(_render3d(figure)[1])
            if found:
                holes[f"{name}@{yaw:.1f}"] = found
    check(not holes, f"figure3d: no skin shows through any outfit at front, side and back {holes}")

    figure = Figure3D(character=woman, outfit=wardrobe3d.OUTFITS["t_shirt_jeans"], hair=head3d.PONYTAIL_HAIR,
                      position=(210.0, 270.0), head_height=60.0, pitch=0.0)
    canvas, image = _render3d(figure)
    rows = np.flatnonzero((image.depth > -1e8).any(axis=1))
    heads = (rows[-1] - rows[0] + 1) / canvas.px(60.0)
    check(7.0 < heads < 8.2, f"figure3d: the standing figure is about 7.5 heads tall ({heads:.2f})")
    eyes = canvas.part("eyes")
    on_face = float((eyes * (canvas.part("face") > 0.5)).sum() / (eyes.sum() + 1e-9))
    check(eyes.sum() > 0 and on_face > MIN_EYES_ON_FACE, f"figure3d: eyes sit on the 3D head ({on_face:.2f})")
    back_canvas, _ = _render3d(Figure3D(character=woman, hair=head3d.PONYTAIL_HAIR, position=(210.0, 270.0),
                                        head_height=60.0, yaw=3.1416))
    check(back_canvas.part("eyes").sum() == 0, "figure3d: no face features are drawn on the back of the head")


def check_perspective():
    """An eye far away must reproduce the orthographic picture; a near eye makes parallel lines converge."""
    from codeillust import head3d, rig3d, wardrobe3d
    from codeillust.body3d import Camera3D, DepthRenderer
    from codeillust.figure3d import Figure3D
    figure = Figure3D(character=adult_face(default_character()), pose=rig3d.HAND_ON_HIP, hair=head3d.LONG_HAIR,
                      outfit=wardrobe3d.OUTFITS["suit"], position=(210.0, 270.0), head_height=60.0, yaw=0.6)
    _, ortho = _render3d(figure)
    _, far = _render3d(replace(figure, distance=FAR_EYE))
    both = (ortho.depth > -1e8) & (far.depth > -1e8)
    changed = int(((ortho.depth > -1e8) ^ (far.depth > -1e8)).sum())
    error = float(np.abs(ortho.depth - far.depth)[both].max())
    check(changed == 0 and error < 1e-3,
          f"perspective: a far eye matches the orthographic depth ({changed} px, {error:.1e})")
    renderer = DepthRenderer(Canvas(200.0, 200.0, 1.0, 1), Camera3D(origin=(100.0, 100.0), scale=40.0, distance=8.0))
    xs, _, _ = renderer.project(np.array([[-1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [-1.0, 1.0, -1e7], [1.0, 1.0, -1e7]]))
    check(xs[1] - xs[0] > 80.0 and abs(xs[3] - xs[2]) < 0.01,
          "perspective: near points spread, far points meet at the centre")


def check_sdf():
    """Traced hard solids: a box and a cylinder seen head-on show their exact front depth."""
    from codeillust import sdf3d
    from codeillust.body3d import Camera3D, DepthRenderer
    for shape, front in ((sdf3d.Box((1.0, 0.5, 0.3), 0.05), 0.3), (sdf3d.Cylinder(0.4, 0.6, 0.05), 0.4),
                         (sdf3d.Slab((0.8, 0.5, 0.2), 0.1, 0.04), 0.2)):
        renderer = DepthRenderer(Canvas(200.0, 200.0, 1.0, 1), Camera3D(origin=(100.0, 100.0), scale=40.0))
        renderer.draw([sdf3d.sdf_solid(shape, (0.0, 0.0, 0.0), np.eye(3), default_palette().skin)])
        depth = float(renderer.depth[100, 100])
        check(abs(depth - front) < SDF_DEPTH_TOLERANCE, f"sdf: {type(shape).__name__} front depth {depth:.4f} = {front}")


def check_scene3d():
    """Every object and furniture builder renders, objects stand on what they rest on, and in one scene
    the nearer of two objects hides the further."""
    from codeillust import furniture3d, props3d, scene3d, street3d
    from codeillust.props3d import Prop3D
    empty = []
    builders = PROP_BUILDERS + FURNITURE_BUILDERS + STREET_BUILDERS
    modules = {"props3d": props3d, "furniture3d": furniture3d, "street3d": street3d}
    for module, name in builders:
        canvas = Canvas(300.0, 300.0, 0.5, 1)
        painter = Painter(canvas, STYLES[StyleName.ANIME], DEFAULT_LIGHT)
        item = getattr(modules[module], name)()
        low, high = _extent(item.solids)
        camera = scene3d.SceneCamera(target=tuple((low + high) / 2), origin=(150.0, 150.0),
                                     scale=200.0 / float(np.max(high - low)), pitch=0.3)
        _, image, _ = scene3d.draw_scene3d(painter, camera, [scene3d.Placed(item)])
        if not isinstance(item, Prop3D) or int((image.depth > -1e8).sum()) < MIN_OBJECT_PX:
            empty.append(name)
    check(not empty, f"scene3d: {len(builders)} object and furniture builders render ({empty or 'all'})")
    desk = scene3d.Placed(furniture3d.desk())
    mug = scene3d.on_top(props3d.mug(), desk)
    check(abs(mug.at[1] + furniture3d.DESK_HEIGHT) < 1e-9, "scene3d: an object put on a desk stands on its top")
    canvas = Canvas(300.0, 300.0, 1.0, 1)
    painter = Painter(canvas, STYLES[StyleName.ANIME], DEFAULT_LIGHT)
    near, far = props3d.mug(name="near"), props3d.book(name="far")
    _, image, _ = scene3d.draw_scene3d(painter, scene3d.SceneCamera(target=(0.0, -0.2, 0.0), origin=(150.0, 150.0),
                                                                    scale=200.0, pitch=0.0),
                                       [scene3d.Placed(near, at=(0.0, 0.0, 0.5)), scene3d.Placed(far)])
    center = image.names[image.name_id[int(canvas.px(150.0)), int(canvas.px(150.0))]]
    check(center == "near", f"scene3d: the nearer object hides the further one ({center})")
    canvas = Canvas(300.0, 300.0, 1.0, 1)
    painter = Painter(canvas, STYLES[StyleName.ANIME], DEFAULT_LIGHT)
    laptop = props3d.laptop(screen="game")
    _, image, _ = scene3d.draw_scene3d(painter, scene3d.SceneCamera(target=(0.0, -0.5, 0.0), origin=(150.0, 150.0),
                                                                    scale=150.0, pitch=0.25), [scene3d.Placed(laptop)])
    screen = laptop.screens[0].material
    lit = (image.material_id == [i for i, m in enumerate(image.materials) if m is screen][0]) & (image.depth > -1e8)
    shown = canvas.rgb[lit].mean(axis=0)
    check(lit.sum() > MIN_OBJECT_PX and float(np.abs(shown - screen.base).max()) > MIN_SCREEN_CHANGE,
          f"scene3d: the screen picture lands on the laptop screen ({int(lit.sum())} px)")


def _extent(solids):
    """Corners of a box round a list of solids (head heights)."""
    points = []
    for solid in solids:
        if getattr(solid, "points", None) is not None:
            points += [p + sign * r for p, r in zip(solid.points, solid.radii) for sign in (-1.0, 1.0)]
        else:
            reach = solid.shape.bound if hasattr(solid, "shape") else max(solid.radii)
            points += [solid.center - reach, solid.center + reach]
    points = np.array(points)
    return points.min(axis=0), points.max(axis=0)


def check_held_objects():
    """Held objects stay in the hand, and every sitting pose fits the same seat height."""
    from codeillust import props3d, rig3d
    from codeillust.body3d import Skeleton3D
    from codeillust.figure3d import lowest_sole
    worst = 0.0
    for pose, builder in ((rig3d.STAND_PHONE, props3d.held_phone()), (rig3d.SIT_PHONE, props3d.held_phone()),
                          (rig3d.STAND_MUG, props3d.held_mug()), (rig3d.SIT_MUG, props3d.held_mug())):
        skeleton = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.FEMALE_AVERAGE), pose)
        held = builder(skeleton, default_character())
        center = np.mean([solid.center for solid in held.solids], axis=0)
        worst = max(worst, float(np.linalg.norm(center - skeleton.position["wrist_right"])))
    check(worst < MAX_HELD_DISTANCE, f"held: phone and mug sit in the right hand ({worst:.2f} head heights)")
    skeleton = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.MALE_SLIM), rig3d.SIT_GAME)
    pad = props3d.held_controller()(skeleton, default_character())
    middle = (skeleton.position["wrist_left"] + skeleton.position["wrist_right"]) / 2
    offset = float(np.linalg.norm(np.mean([solid.center for solid in pad.solids], axis=0) - middle))
    check(offset < MAX_HELD_DISTANCE, f"held: the controller sits between both hands ({offset:.2f})")
    sit = lowest_sole(rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.FEMALE_AVERAGE), rig3d.SIT))
    spread = max(abs(lowest_sole(rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.FEMALE_AVERAGE), pose)) - sit)
                 for name, pose in rig3d.POSES.items() if name.startswith("sit"))
    check(spread < SEAT_TOLERANCE, f"held: every sitting pose fits the same seat height ({spread:.3f})")


def check_rooms():
    """Each room fills the frame: walls, floor and ceiling leave no unpainted canvas."""
    from codeillust import interior, scene3d
    camera = scene3d.SceneCamera(target=(0.0, -3.0, -2.0), origin=(150.0, 200.0), scale=14.0, yaw=0.3, pitch=0.12,
                                 distance=20.0)
    for name in ("living_room", "office", "cafe", "bedroom"):
        canvas = Canvas(300.0, 400.0, 0.5, 1)
        canvas.rgb[:] = -1.0                         # anything left unpainted keeps this impossible colour
        room = getattr(interior, name)()
        for surface in room.surfaces:
            interior.draw_surface(canvas, camera, surface)
        bare = float((canvas.rgb < -0.5).any(axis=2).mean())
        check(bare < MAX_BARE_SHARE, f"rooms: the {name} shell covers the frame ({bare:.4f} bare)")



def check_floor_contact():
    """Every pose is set down without a body part sinking below the floor; a figure lying on its back
    rests on its head, back and heels at once."""
    from codeillust import head3d, rig3d, wardrobe3d
    from codeillust.figure3d import Figure3D, figure_parts, floor_level, ground_points, _lowest_points
    woman = adult_face(default_character())
    worst, span = 0.0, 0.0
    for name, pose in rig3d.POSES.items():
        parts = figure_parts(Figure3D(character=woman, pose=pose, hair=head3d.LONG_HAIR,
                                      outfit=wardrobe3d.OUTFITS["t_shirt_jeans"]))
        worst = max(worst, float(_lowest_points(parts.solids)[:, 1].max()) - floor_level(parts))
        if name == "lie_back":
            touching = ground_points(parts)
            span = float(np.ptp(touching[:, 2]))
    check(worst <= MAX_SINK, f"floor: no body part sinks below the floor in any pose ({worst:.3f})")
    check(span > MIN_LYING_SPAN, f"floor: lie_back rests on head, back and heels together ({span:.2f})")


def check_layout():
    """The overlap check finds a book pushed into a laptop and passes every room; a cable lies on what it
    is laid on."""
    from codeillust import furniture3d, interior, props3d, scene3d
    desk = scene3d.Placed(furniture3d.desk())
    clash = scene3d.overlaps([desk, scene3d.on_top(props3d.book(), desk), scene3d.on_top(props3d.laptop(), desk)])
    pairs = [(o.first, o.second) for o in clash]
    check(pairs == [("book", "laptop")], f"layout: the overlap check finds a book inside a laptop ({pairs})")
    found = {name: scene3d.overlaps(getattr(interior, name)().items)
             for name in ("living_room", "office", "cafe", "bedroom")}
    found = {name: clashes for name, clashes in found.items() if clashes}
    check(not found, f"layout: no objects pass into each other in the rooms ({found or 'none'})")
    cable = props3d.cable([(0.0, -1.0, 0.0), (1.0, -1.0, 0.5), (2.0, 0.0, 1.0)]).solids[0]
    lowest = cable.points[:, 1] + cable.radii
    check(abs(float(lowest[0]) + 1.0) < 1e-9 and abs(float(lowest[-1])) < 1e-9,
          "layout: a cable rests on the points it is laid through")


def check_glass():
    """A clear glass shows what is behind it: over a dark backdrop it stays darker than over a light one."""
    from codeillust import props3d, scene3d
    shown = []
    for backdrop in ("#202020", "#F0F0F0"):
        canvas = Canvas(200.0, 200.0, 1.0, 1)
        canvas.rgb[:] = np.asarray(rgb(backdrop), dtype=np.float32)
        painter = Painter(canvas, STYLES[StyleName.ANIME], DEFAULT_LIGHT)
        glass = props3d.drinking_glass(fill=0.0)
        camera = scene3d.SceneCamera(target=(0.0, -0.25, 0.0), origin=(100.0, 100.0), scale=400.0, pitch=0.0)
        scene3d.draw_scene3d(painter, camera, [scene3d.Placed(glass)])
        middle = canvas.rgb[int(canvas.px(80.0)):int(canvas.px(120.0)), int(canvas.px(90.0)):int(canvas.px(110.0))]
        shown.append(float(middle.mean()))
    through = (shown[1] - shown[0]) / float(np.mean(rgb("#F0F0F0")) - np.mean(rgb("#202020")))
    check(through > MIN_GLASS_SHOW, f"glass: the backdrop shows through a clear glass ({through:.2f})")


def check_garment_fit():
    """Bikini strings lie on the skin without sinking in; a skirt covers the tops of seated thighs; hands
    in pockets are under the trousers."""
    from codeillust import rig3d, wardrobe3d
    from codeillust.body3d import Skeleton3D, distance_to_solids
    worst = np.inf
    for build in (rig3d.FEMALE_AVERAGE, rig3d.FEMALE_FULLER):
        for pose in (rig3d.STAND, rig3d.CONTRAPPOSTO, rig3d.SIT, rig3d.LIE_FRONT):
            skeleton = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(build), pose)
            context = wardrobe3d.Context(skeleton, build, wardrobe3d.OUTFITS["bikini"].colors)
            for _, sign in rig3d.SIDES:
                for string in wardrobe3d.bikini_strings(context, sign):
                    worst = min(worst, float(distance_to_solids(string.points, context.skin()).min()))
    check(worst > wardrobe3d.STRING_CLEARANCE - STRING_TOLERANCE,
          f"garments: bikini strings stay on the skin ({worst:.3f} from it)")
    off = 0.0
    for build in (rig3d.MALE_SLIM, rig3d.MALE_ATHLETIC, rig3d.FEMALE_FULLER):
        skeleton = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(build), rig3d.STAND)
        context = wardrobe3d.Context(skeleton, build, wardrobe3d.OUTFITS["tank_top_jeans"].colors)
        for _, sign in rig3d.SIDES:
            path = [wardrobe3d.chest_point(context, (sign * x * build.shoulders, y, z)) for x, y, z in wardrobe3d.TANK_STRAP]
            strap = wardrobe3d.over_skin(context, path, wardrobe3d.STRAP_HALF_THICKNESS + wardrobe3d.STRAP_PRESS, hug=True)
            gap = distance_to_solids(strap, context.skin()) - wardrobe3d.STRAP_HALF_THICKNESS
            off = max(off, float(np.abs(gap - wardrobe3d.STRAP_PRESS).max()))
    check(off < STRAP_TOLERANCE, f"garments: shoulder straps lie on the shoulder on every build ({off:.3f})")
    skeleton = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.FEMALE_AVERAGE), rig3d.SIT)
    skirt, _, _ = wardrobe3d.build(wardrobe3d.OUTFITS["sundress"], skeleton, rig3d.FEMALE_AVERAGE)
    up = -skeleton.rotation["pelvis"] @ np.array([0.0, 1.0, 0.0])
    tops = [skeleton.position[f"hip_{side}"] * (1 - t) + skeleton.position[f"knee_{side}"] * t + up * THIGH_TOP
            for side, _ in rig3d.SIDES for t in (0.2, 0.4, 0.6)]
    covered = float(distance_to_solids(np.array(tops), [solid for solid in skirt if solid.group == "top"]).max())
    check(covered < 0.0, f"garments: a skirt covers the tops of seated thighs ({covered:.3f})")
    skeleton = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.FEMALE_AVERAGE), rig3d.HANDS_IN_POCKETS)
    jeans, _, _ = wardrobe3d.build(wardrobe3d.OUTFITS["t_shirt_jeans"], skeleton, rig3d.FEMALE_AVERAGE)
    hands = rig3d.hand_solids(rig3d.HANDS_IN_POCKETS.hands)
    tips = np.array([solid.points[-1] for side, _ in rig3d.SIDES for solid in hands(skeleton, side, None)
                     if getattr(solid, "points", None) is not None])
    inside = float(distance_to_solids(tips, [solid for solid in jeans if solid.group == "bottom"]).max())
    check(inside < 0.0, f"garments: fingers in pockets stay under the trousers ({inside:.3f})")


def check_painterly_faces():
    """Painterly finishing gives a small face its finest brushes and leaves a large one as before."""
    from codeillust import finish
    importance = {}
    for name, span in (("small", 60.0), ("large", 200.0)):
        canvas = Canvas(400.0, 400.0, 1.0, 1)
        xs, ys = canvas.grid()
        canvas.remember("face", (np.hypot(xs - 200.0, ys - 200.0) < span / 2).astype(np.float32))
        importance[name] = float(finish._face_detail(canvas).max())
    check(importance["small"] > PAINT_SMALL_FACE and abs(importance["large"] - finish.FACE_DETAIL) < 1e-6,
          f"painterly: small faces get the finest brushes ({importance})")



def check_gaps_and_shadows():
    """A hair-width gap between soft forms is closed while a small hole in a rigid object stays open;
    sleeves of a top go into its pocket cover with the hands; floor shadows lean away from the light."""
    from codeillust import head3d, rig3d, sdf3d, wardrobe3d
    from codeillust.body3d import EMPTY, Camera3D, DepthRenderer, Sweep, ellipsoid
    from codeillust.figure3d import Figure3D, _shadow_lean, figure_parts
    canvas = Canvas(200.0, 200.0, 1.0, 1)
    renderer = DepthRenderer(canvas, Camera3D(origin=(100.0, 100.0), scale=400.0, yaw=0.0, pitch=0.0))
    skin = default_palette().skin
    # Two forms of different cloth groups (they do not melt together) a little apart, capped above and below.
    renderer.draw([ellipsoid((x, 0.0, 0.0), np.eye(3), (0.1, 0.2, 0.1), skin, group="top") for x in GAP_SIDES]
                  + [ellipsoid((0.0, y, 0.0), np.eye(3), (0.06, 0.04, 0.05), skin, group="bottom") for y in GAP_CAPS])
    soft = renderer.result()
    center = int(canvas.px(100.0))
    check(soft.depth[center, center] > EMPTY / 2, "gaps: a hair-width gap enclosed by soft forms is closed")
    canvas = Canvas(200.0, 200.0, 1.0, 1)
    renderer = DepthRenderer(canvas, Camera3D(origin=(100.0, 100.0), scale=400.0, yaw=0.0, pitch=0.0))
    ring = sdf3d.sdf_solid(sdf3d.Torus(RING_MAJOR, RING_MINOR), (0.0, 0.0, 0.0), sdf3d.turn_x(np.pi / 2), skin)
    renderer.draw([ring])
    rigid = renderer.result()
    check(rigid.depth[center, center] <= EMPTY / 2, "gaps: the hole of a small rigid ring stays open")
    figure = Figure3D(character=adult_face(default_character()), build=rig3d.MALE_SLIM, pose=rig3d.HANDS_IN_POCKETS,
                      hair=head3d.MALE_SHORT_HAIR, outfit=wardrobe3d.OUTFITS["hoodie_jeans"])
    parts = figure_parts(figure)
    cuffs = [solid.part for solid in parts.solids if solid.group == "trim" and isinstance(solid, Sweep)]
    showing = []
    for yaw in TEST3D_YAWS[:2]:
        canvas = Canvas(300.0, 600.0, 1.0, 1)
        renderer = DepthRenderer(canvas, Camera3D(origin=(150.0, 250.0), scale=60.0, yaw=yaw, pitch=0.16))
        renderer.draw(parts.solids)
        image = renderer.result()
        showing.append(int((np.isin(image.solid_id, cuffs) & (image.depth > EMPTY / 2)).sum()))
    check(len(cuffs) == 2 and max(showing) <= MAX_CUFF_PX,
          f"pockets: hoodie cuffs go into the pocket with the hands ({showing} px showing)")
    camera = Camera3D(origin=(0.0, 0.0), scale=100.0, yaw=0.0, pitch=0.0)
    view = type("View", (), {"camera": camera})()
    front, _ = _shadow_lean(view, DEFAULT_LIGHT)
    back, _ = _shadow_lean(view, BACK_LIGHT)
    check(front[1] < 0.0 < back[1], f"shadows: a floor shadow leans away from the light ({front}, {back})")



def check_light_scenes():
    """The light scenes' parts: warm grades keep the colour the doomer grade takes away, the new window views
    hold a dark sky with a bright disc (and lit windows at night), and a room lit by its own lamp is brighter
    by the lamp while the window view keeps its own light."""
    from codeillust import grade, interior, outdoor, props3d, scene3d
    # Warm grades: a saturated patch keeps most of its colour, and more than under doomer; reproducible.
    def kept_chroma(name):
        results = []
        for _ in range(2):
            canvas = Canvas(100.0, 100.0, 1.0, 3)
            canvas.rgb[:] = 0.5
            canvas.rgb[30:70, 30:70] = rgb("#E03030")
            grade.apply(canvas, name)
            results.append(canvas.rgb.copy())
        patch = results[0][40:60, 40:60].mean(axis=(0, 1))
        source = rgb("#E03030")
        return float(patch.max() - patch.min()) / float(source.max() - source.min()), np.array_equal(*results)
    doomer_chroma, _ = kept_chroma("doomer")
    for name in ("cozy_night", "late_sun", "golden_hour"):
        chroma, same = kept_chroma(name)
        check(chroma > WARM_GRADE_MIN_CHROMA and chroma > doomer_chroma and same,
              f"grade: {name} keeps colour ({chroma:.2f} kept, doomer {doomer_chroma:.2f}) and is reproducible")
    # Window views: night has a dark sky, a bright moon and warm lit windows; golden runs from blue to gold.
    luma_weights = np.array([0.299, 0.587, 0.114], dtype=np.float32)
    night = interior.outdoor_view(6.0, 4.0, "city_night", np.random.default_rng(2))
    night_luma = night @ luma_weights
    lit = np.abs(night - rgb("#F6C980")).max(axis=2) < 0.02
    check(float(night_luma[: night.shape[0] // 10].mean()) < VIEW_DARK_SKY and float(night_luma.max()) > VIEW_BRIGHT_DISC
          and lit.any(), "view: city_night has a dark sky, a bright moon and lit windows")
    golden = interior.outdoor_view(6.0, 4.0, "golden", np.random.default_rng(2))
    top, low = golden[: golden.shape[0] // 10].mean(axis=(0, 1)), golden[golden.shape[0] // 2].mean(axis=0)
    check(top[2] > top[0] and low[0] > low[2] and float((golden @ luma_weights).max()) > VIEW_BRIGHT_DISC,
          "view: golden runs from a blue top to a gold horizon round a bright sun")
    # Lit room: the back wall is brighter by the lamp than at its far end, and the window view drawn after the
    # light is the same whether the room is dark or lit.
    shell = interior.Shell(-6.0, 6.0, -6.0, interior.ROOM_FRONT, 10.0)
    rng = np.random.default_rng(4)
    wall = np.full((8, 8, 3), 0.8, np.float32)
    surfaces = interior.shell_surfaces(shell, wall, wall, wall, wall, wall)
    views = [interior.on_back_wall(shell, -1.0, 1.0, 8.0, 5.0, interior.window(2.0, 3.0, "city_night", rng))]
    camera = scene3d.SceneCamera(target=(0.0, -4.0, -3.0), origin=(150.0, 100.0), scale=12.0, pitch=0.05,
                                 distance=30.0)
    lamp = outdoor.Lamp(at=(-4.5, -4.0, -5.0), color=np.ones(3), reach=2.0, strength=1.2)
    def room(lamps, ambient):
        canvas = Canvas(300.0, 200.0, 1.0, 1)
        outdoor.draw_lit_room(Painter(canvas, STYLES[StyleName.ANIME], DEFAULT_LIGHT), camera, surfaces, views,
                              [scene3d.Placed(props3d.mug(), at=(0.0, 0.0, -3.0))], lamps, ambient)
        return canvas
    lit_room, dark_room = room([lamp], np.full(3, 0.3)), room([], np.full(3, 0.3))
    (near_x, near_y), (far_x, far_y), (view_x, view_y) = camera.project(
        np.array([[-4.5, -4.0, shell.z0], [4.5, -4.0, shell.z0], [0.0, -6.5, shell.z0]]))[0]
    pixel = lambda canvas, x, y: canvas.rgb[int(canvas.px(y)), int(canvas.px(x))]
    near, far = float(pixel(lit_room, near_x, near_y).mean()), float(pixel(lit_room, far_x, far_y).mean())
    view_same = np.allclose(pixel(lit_room, view_x, view_y), pixel(dark_room, view_x, view_y))
    check(near > far * LAMP_WALL_GAIN and view_same,
          f"lit room: the wall by the lamp is brighter ({near:.2f} against {far:.2f}) and the view keeps its light")


def check_doomer():
    """The doomer set's parts: the colour grade, pixel to world round trips, night lighting that keeps
    lights bright, lamps and wires hung where their anchors are, the knit cap over the hair, cheap thin sweeps."""
    from codeillust import body3d, grade, outdoor, props3d, rig3d, scene3d, street3d, wardrobe3d
    from codeillust.body3d import EMPTY, Camera3D, DepthRenderer, sweep
    from codeillust.figure3d import Figure3D, figure_parts
    # Grade: a saturated patch loses most of its colour, blacks are lifted, and the result is reproducible.
    results = []
    for _ in range(2):
        canvas = Canvas(100.0, 100.0, 1.0, 3)
        canvas.rgb[:] = 0.0
        canvas.rgb[30:70, 30:70] = rgb("#E03030")
        grade.apply(canvas, "doomer")
        results.append(canvas.rgb.copy())
    patch = results[0][40:60, 40:60].mean(axis=(0, 1))
    chroma = float(patch.max() - patch.min()) / float(rgb("#E03030").max() - rgb("#E03030").min())
    check(chroma < GRADE_MAX_CHROMA and float(results[0][:10, 45:55].mean()) > 0.0
          and np.array_equal(results[0], results[1]),
          f"grade: doomer mutes colour ({chroma:.2f} kept), lifts black and is reproducible")
    # Round trips: a world point drawn at a pixel comes back from that pixel and its depth; ground pixels land
    # on y = 0 and project back onto themselves.
    camera = scene3d.SceneCamera(target=(0.0, -4.0, -20.0), origin=(200.0, 150.0), scale=10.0, yaw=0.3, pitch=0.05,
                                 distance=40.0)
    canvas = Canvas(400.0, 300.0, 1.0, 1)
    depths = np.full((canvas.height, canvas.width), EMPTY, dtype=np.float32)
    where = np.zeros_like(depths, dtype=bool)
    for row, col, depth in ROUND_TRIP_PIXELS:
        depths[row, col], where[row, col] = depth, True
    found = outdoor.world_points(canvas, camera, depths, where)
    back, back_depth = camera.project(found)
    rows, cols = np.nonzero(where)
    centers = (np.stack([cols, rows], axis=1) + 0.5) / canvas.px_per_unit
    error = float(max(np.abs(back - centers).max(), np.abs(back_depth - depths[rows, cols]).max()))
    ground, on_ground = outdoor.ground_points(canvas, camera)
    back, _ = camera.project(ground[::997])
    pixel_rows, pixel_cols = np.nonzero(on_ground)
    expected = (np.stack([pixel_cols, pixel_rows], axis=1)[::997] + 0.5) / canvas.px_per_unit
    ground_error = float(np.abs(back - expected).max())
    horizon = outdoor.horizon_y(camera)
    check(error < ROUND_TRIP_TOLERANCE and float(np.abs(ground[:, 1]).max()) < ROUND_TRIP_TOLERANCE
          and ground_error < ROUND_TRIP_TOLERANCE and abs(float(pixel_rows.min()) / canvas.px_per_unit - horizon) < 2.0,
          f"outdoor: pixels map to world points and back ({error:.1e}), onto the ground ({ground_error:.1e}) "
          f"below the horizon")
    # Night lighting: far from the lamp an object is dark, by the lamp it is lit, and the ember of a lit
    # cigarette (drawn after the lighting) stays bright.
    canvas = Canvas(300.0, 200.0, 1.0, 1)
    painter = Painter(canvas, STYLES[StyleName.ANIME], DEFAULT_LIGHT)
    lamp = outdoor.Lamp(at=(-2.0, -3.0, 0.0), color=np.ones(3), reach=1.5, strength=1.5)
    near, far = props3d.mug(name="near"), props3d.mug(name="far")
    smoke = props3d.cigarette(name="smoke")
    camera = scene3d.SceneCamera(target=(0.0, -0.3, 0.0), origin=(150.0, 100.0), scale=40.0, pitch=0.2, distance=40.0)
    items = [scene3d.Placed(near, at=(-2.0, 0.0, 0.0)), scene3d.Placed(far, at=(2.0, 0.0, 0.0)),
             scene3d.Placed(smoke, at=(0.0, 0.0, 0.0), yaw=np.pi / 2)]
    unlit = Canvas(300.0, 200.0, 1.0, 1)
    _, plain, _ = scene3d.draw_scene3d(Painter(unlit, STYLES[StyleName.ANIME], DEFAULT_LIGHT), camera, items)
    _, image, _ = scene3d.draw_scene3d(painter, camera, items,
                                       lighting=outdoor.night_lighting(camera, np.full(3, 0.15), [lamp]))
    def brightness(target, name):
        mask = (image.name_id == image.names.index(name)) & (image.depth > EMPTY / 2)
        return float(target.rgb[mask].mean())
    tip = np.asarray(items[2].at) + scene3d.rot_y(items[2].yaw) @ np.asarray(smoke.glows[0].point)
    (tip_x, tip_y), = camera.project(tip[None])[0]
    ember = float(canvas.rgb[int(canvas.px(tip_y)), int(canvas.px(tip_x))].max())
    far_share = brightness(canvas, "far") / brightness(unlit, "far")
    check(far_share < NIGHT_DARK and brightness(canvas, "near") > brightness(canvas, "far") and ember > EMBER_BRIGHT,
          f"night: away from the lamp objects darken ({far_share:.2f}), by it they are lit, the ember stays bright "
          f"({ember:.2f})")
    # Lamps and wires: the lamp light sits at the bulb, a bench seat is a seat, wires start and end at insulators.
    placed = scene3d.Placed(street3d.street_lamp(), at=(1.0, 0.0, 2.0), yaw=np.pi)
    light = street3d.lamp_light(placed)
    poles = [scene3d.Placed(street3d.power_pole(), at=(0.0, 0.0, 0.0)), scene3d.Placed(street3d.power_pole(),
                                                                                     at=(30.0, 0.0, -10.0))]
    wires = street3d.wires_between(poles)
    ends = all(np.allclose(wire[0], scene3d.anchor(poles[0], f"wire_{k}")) and
               np.allclose(wire[-1], scene3d.anchor(poles[1], f"wire_{k}")) for k, wire in enumerate(wires))
    sag = all(wire[len(wire) // 2][1] > max(wire[0][1], wire[-1][1]) for wire in wires)
    bench = street3d.bench()
    check(np.allclose(light.at, scene3d.anchor(placed, "bulb")) and len(wires) == 3 and ends and sag
          and "seat_0" in bench.anchors and "seat_0" in street3d.bus_stop().anchors,
          "street: lamp light at the bulb, wires hang between insulators, benches and shelters have seats")
    # Knit cap: seen from the front and from above-behind, the top of a capped head is the cap, not hair.
    figure = Figure3D(character=adult_face(default_character()), pose=rig3d.STAND,
                      outfit=wardrobe3d.OUTFITS["winter_beanie"])
    parts = figure_parts(figure)
    hat = figure.outfit.colors["hat"]
    tops = []
    for yaw in (0.0, 2.6):
        canvas = Canvas(200.0, 200.0, 1.0, 1)
        renderer = DepthRenderer(canvas, Camera3D(origin=(100.0, 100.0), scale=60.0, yaw=yaw, pitch=0.3))
        crown = parts.skeleton.point("head", (0.0, -0.5, -0.05))
        view = renderer.camera.to_view(crown[None])[0]
        renderer.camera = replace(renderer.camera, origin=(100.0 - view[0] * 60.0, 100.0 - view[1] * 60.0))
        renderer.draw(parts.solids)
        image = renderer.result()
        column = image.material_id[:, int(canvas.px(100.0))]
        drawn = np.nonzero(image.depth[:, int(canvas.px(100.0))] > EMPTY / 2)[0]
        tops.append(bool(drawn.size) and image.materials[int(column[drawn[0]])] is hat)
    check(all(tops), f"wardrobe: the knit cap covers the top of the head ({tops})")
    # Thin sweeps: spheres that just touch, when thinner than a pixel, cover what fine stepping covers.
    covers, counts = [], []
    subpixel_default = body3d.SWEEP_SUBPIXEL_RADIUS_PX
    for subpixel in (subpixel_default, 0.0):
        body3d.SWEEP_SUBPIXEL_RADIUS_PX = subpixel
        canvas = Canvas(200.0, 200.0, 1.0, 1)
        renderer = DepthRenderer(canvas, Camera3D(origin=(100.0, 100.0), scale=2.0, yaw=0.0, pitch=0.0, distance=500.0))
        twig = sweep([np.array([-30.0, 0.0, 0.0]), np.array([30.0, -10.0, 0.0])], [0.08, 0.05], default_palette().skin,
                     group="twig")
        calls = []
        original = renderer._sphere_rays
        renderer._sphere_rays = lambda *args, **kwargs: (calls.append(1), original(*args, **kwargs))
        renderer.draw([twig])
        covers.append(renderer.result().coverage > 0.1)
        counts.append(len(calls))
    body3d.SWEEP_SUBPIXEL_RADIUS_PX = subpixel_default
    overlap = float((covers[0] & covers[1]).sum() / max(1, (covers[0] | covers[1]).sum()))
    check(overlap > MIN_THIN_OVERLAP and counts[1] >= THIN_SPEEDUP * counts[0],
          f"sweeps: a thin far twig drawn with {counts[0]} spheres instead of {counts[1]} covers the same pixels "
          f"({overlap:.2f})")


if __name__ == "__main__":
    main()
