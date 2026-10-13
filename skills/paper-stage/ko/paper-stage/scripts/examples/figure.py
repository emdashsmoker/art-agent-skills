"""Example: a full figure, clothed or as a figure study, seen from the front or from behind.

Usage: python examples/figure.py --build female|male
                                 --outfit bikini|bodycon|slip_dress|top_and_jeans|swimsuit|trunks|shirtless_jeans|
                                          lingerie|lingerie_stockings|crop_top_shorts|hoodie|hoodie_shorts|suit|nude
                                 --pose hand_on_hip|contrapposto|arm_behind_head|arms_up|walk|walk_side|stance|back|stand|
                                        sit|sit_side|sit_front|kneel|kneel_side|seiza|lie_back|lie_side
                                 --yaw 0..90 (or negative) --style anime|illust|painterly --out figure.png

--yaw turns the body (45 three-quarter, 90 profile); the head turns with it.
Sitting poses get a chair, lying poses a bed; both are framed to fit the canvas.

The rig has no genital forms, so a man seen from the front with nothing on reads as a mannequin;
--outfit trunks dresses him in short trunks.
"""
import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, geometry as geo, shading as sh
from codepainter.figure import PortraitSpec
from codepainter.figure import props
from codepainter.figure.body import MALE_BODY, POSES, BodySpec, Skeleton, draw_figure, make_pose
from codepainter.figure.stage import frame, rest_hands
from codepainter.figure.frame import MASCULINE
from codepainter.figure.wardrobe import WARDROBE
from codepainter.styles import finish, get_style

WIDTH, HEIGHT = 1024, 1536
FLOOR_Y = int(HEIGHT * 0.86)
FULL_LENGTH = dict(root=(0.50, 0.475), unit=0.105)       # whole figure standing on the floor
STUDY_LENGTH = dict(root=(0.47, 0.715), unit=0.168)      # cropped above the knees, for figure studies


def paint_room(painting, style, with_floor):
    backdrop.gradient(painting, "#6f5a48", "#2e2622", start=(0, 0), end=(WIDTH * 0.8, HEIGHT))
    backdrop.mottle(painting, "#8a6a4a", amount=0.35, scale=1.0, seed=4)
    backdrop.glow(painting, (WIDTH * 0.05, HEIGHT * 0.12), HEIGHT * 0.75, "#ffd9a0", opacity=0.42)
    backdrop.window_light(painting, (WIDTH * 0.03, HEIGHT * 0.10), (WIDTH * 0.40, HEIGHT * 0.46), slant=0.34,
                          color="#ffe6b8", opacity=0.30, softness=0.0 if style.name == "anime" else HEIGHT * 0.008)
    drape = geo.smooth([(WIDTH * 0.76, -20), (WIDTH + 20, -20), (WIDTH + 20, HEIGHT + 20), (WIDTH * 0.82, HEIGHT + 20),
                        (WIDTH * 0.79, HEIGHT * 0.6)], closed=True, corners=(0, 1, 2, 3))
    cloth = painting.mask(drape)
    painting.fill(cloth, "#4f5a3c")
    rng = np.random.default_rng(5)
    for x in np.linspace(WIDTH * 0.81, WIDTH * 0.98, 6):            # long folds: a dark wedge with a lit edge beside it
        fold = painting.mask(geo.lock((x - 14, -10), (x + 14, -10), (x + rng.uniform(-20, 20), HEIGHT * rng.uniform(0.8, 1.02)), belly=0.8))
        painting.fill(fold * cloth, "#2f3826", 0.7)
        painting.fill(sh.shift(fold, -22, 0) * cloth, "#7b8658", 0.35)
    if with_floor:
        floor = np.zeros(painting.shape, dtype=np.float32)
        floor[FLOOR_Y:] = 1.0
        painting.fill(floor, "#4a3a30")
        painting.fill(floor * sh.linear_ramp(painting.shape, (0, FLOOR_Y), (0, HEIGHT)), "#2a201c", 0.6)


CLOTH = {"slip_dress": "#a8323e", "bikini": "#d8455a", "bodycon": "#1f2430", "trunks": "#2c3a52", "lingerie": "#1c1a22",
         "lingerie_stockings": "#7a1f2b", "crop_top_shorts": "#f1ede4", "hoodie": "#4a4f57", "hoodie_shorts": "#b8a0c8",
         "suit": "#2b3140"}
SECOND = {"trunks": "#d8d2c6", "crop_top_shorts": "#5a7aa8", "hoodie_shorts": "#5a7aa8", "hoodie": "#4f6f9c"}


def render(outfit, pose_name, style_name, build="female", seed=3, yaw=None):
    style = get_style(style_name)
    male = build == "male"
    from_behind = POSES[pose_name].get("view") == "back"
    study = outfit == "nude"
    painting = Painting(WIDTH, HEIGHT)
    paint_room(painting, style, with_floor=not study)
    face = dict(MASCULINE, hair="#2a2022", skin="#e6bf9f", eye="#5a4430") if male else \
        dict(jaw=0.9, eye_open=0.9, smile=0.25, hair="#3a2a2c", eye="#7a5a34", lip="#b9565c", skin="#f2d2b8")
    spec = PortraitSpec(yaw=0.55 if study else -0.55, cloth=CLOTH.get(outfit, "#efe8dc"),
                        cloth_second=SECOND.get(outfit, "#39507a"), **face)
    framing = STUDY_LENGTH if study else FULL_LENGTH
    turn = 0.0 if from_behind or not study else 0.35        # a study reads better with the body slightly turned
    extra = {} if yaw is None else dict(yaw=yaw, turn=0.0)  # a real turn replaces the slight one
    pose = make_pose(pose_name, **{"turn": turn, **framing, **extra})
    body = MALE_BODY if male else BodySpec()
    dress = None if outfit == "nude" else WARDROBE[outfit]
    furniture = None
    if pose_name.startswith(("sit", "kneel", "seiza", "lie")):     # not standing: frame the whole pose, add its furniture
        (pose,) = frame([(pose, body)], painting.shape, "full", margin=0.10, floor=None if pose_name.startswith("lie") else HEIGHT * 0.93)
        if pose_name == "sit_front":           # hands on the knees whatever the shoulder width
            pose = rest_hands(pose, body, painting.shape)
        if abs(pose.lean) >= 60:               # stand the bed on the floor
            drop = HEIGHT * 0.93 - (pose.root[1] * HEIGHT + (pose.ground + props.BED_HEIGHT) * pose.unit * HEIGHT)
            pose = replace(pose, root=(pose.root[0], pose.root[1] + drop / HEIGHT))
        skeleton = Skeleton(pose, body, painting.shape)
        if abs(pose.lean) >= 60:
            furniture = props.bed(skeleton)
        elif skeleton.seated > 0.5 and pose.ground is None:
            furniture = props.chair(skeleton)
    if furniture is not None:
        back = props.draw(painting, skeleton, furniture, style)
    masks = draw_figure(painting, spec, body, pose, style, dress=dress)
    if furniture is not None:
        props.contact_shadows(painting, skeleton, masks["figure"], back, style)
        props.draw(painting, skeleton, furniture, style, layer="front")
    elif not study and pose_name.startswith(("sit", "kneel", "seiza")):
        props.floor_shadow(painting, Skeleton(pose, body, painting.shape), [masks["limbs"]["leg_l"], masks["limbs"]["leg_r"]], style)
    if not study and furniture is None and not pose_name.startswith(("sit", "kneel", "seiza", "lie")):   # stand on the floor
        feet = masks["limbs"]["leg_l"] + masks["limbs"]["leg_r"]
        floor = np.zeros(painting.shape, dtype=np.float32)
        floor[FLOOR_Y:] = 1.0
        painting.fill(sh.ground_shadow(feet, drop=0.0, squash=0.10, lean=0.5, softness=8) * floor * (1 - masks["figure"]),
                      "#1a1210", 0.6, "multiply")
    image = finish(painting, style, seed=seed, importance=masks["head"], detail=0.85 if study else 1.0)
    return painting, image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", default="female", choices=["female", "male"])
    parser.add_argument("--outfit", default="slip_dress", choices=list(WARDROBE) + ["nude"])
    parser.add_argument("--pose", default="hand_on_hip", choices=list(POSES))
    parser.add_argument("--style", default="illust", choices=["anime", "illust", "painterly"])
    parser.add_argument("--yaw", type=float, default=None, help="body turn in degrees; 90 is a profile")
    parser.add_argument("--out", default="figure.png")
    args = parser.parse_args()
    painting, image = render(args.outfit, args.pose, args.style, args.build, yaw=args.yaw)
    painting.save(args.out, image)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
