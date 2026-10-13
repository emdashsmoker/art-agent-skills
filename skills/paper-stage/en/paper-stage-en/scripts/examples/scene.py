"""Example: figures in a scene, two-shots and framing presets.

Usage: python examples/scene.py --scene beach|bedroom|office|night_street|cafe|park --style anime|illust|painterly --out scene.png

- beach: a couple holding hands on the shore, full shot.
- bedroom: a woman in lingerie lying on her side on a bed.
- office: a woman in a suit seated, a man standing behind her with a hand on her shoulder, knee shot.
- night_street: a couple in street clothes, her hand on his arm, waist shot.
- cafe: two friends seated across a small table, both in profile, full shot.
- park: a couple walking side by side holding hands, full shot.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, fx, sets
from codepainter.figure import PortraitSpec, props
from codepainter.figure.body import MALE_BODY, BodySpec, make_pose
from codepainter.figure.frame import MASCULINE
from codepainter.figure.hand import HandPose
from codepainter.figure.stage import Actor, draw_actors, floor_shadows, frame, reach
from codepainter.figure.wardrobe import WARDROBE
from codepainter.styles import finish, get_style

LANDSCAPE, PORTRAIT = (1536, 1024), (1024, 1536)
HER = dict(jaw=0.9, eye_open=0.9, smile=0.25, hair="#3a2a2c", eye="#7a5a34", lip="#b9565c", skin="#f2d2b8")
HIM = dict(MASCULINE, hair="#2a2022", skin="#e6bf9f", eye="#5a4430")
HOLD = HandPose(curl=(0.42, 0.48, 0.54, 0.60), spread=0.15, thumb=0.30, thumb_curl=0.3)   # fingers closing round an arm


def beach(painting):
    her = Actor(PortraitSpec(**HER, cloth="#e0455a"), BodySpec(), make_pose("contrapposto", yaw=20), WARDROBE["bikini"], depth=0.0)
    him = Actor(PortraitSpec(**HIM, cloth="#2c5a8a", cloth_second="#e9e4da"), MALE_BODY, make_pose("stance", yaw=-25),
                WARDROBE["trunks"], depth=-0.3)
    her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "full", centers=(0.40, 0.62))
    # their near hands meet between them, a little below the hips
    meet = _midpoint(painting, her, "r", him, "l")
    her.pose = reach(her.pose, her.body, "r", meet, painting.shape, depth=0.25)
    him.pose = reach(him.pose, him.body, "l", meet, painting.shape, depth=0.55)
    return "beach", [her, him]


def _midpoint(painting, a, side_a, b, side_b, drop=0.25):
    from codepainter.figure.body import Skeleton
    ska, skb = Skeleton(a.pose, a.body, painting.shape), Skeleton(b.pose, b.body, painting.shape)
    point = (ska.joints[f"hip_{side_a}"] + skb.joints[f"hip_{side_b}"]) / 2
    return point + [0.0, drop * ska.unit + (ska.joints["wrist_" + side_a][1] - ska.joints[f"hip_{side_a}"][1]) * 0.5]


def bedroom(painting):
    her = Actor(PortraitSpec(**HER, cloth="#1c1a22"), BodySpec(), make_pose("lie_side"), WARDROBE["lingerie_stockings"])
    (her.pose,) = frame([(her.pose, her.body)], painting.shape, "full", centers=(0.47,), margin=0.12)
    her.pose = _lift(her.pose, 0.06)
    from codepainter.figure.body import Skeleton
    her.props = [props.bed(Skeleton(her.pose, her.body, painting.shape))]
    return "bedroom", [her]


def _lift(pose, share):
    from dataclasses import replace
    return replace(pose, root=(pose.root[0], pose.root[1] + share))


def office(painting):
    from codepainter.figure.body import Skeleton
    her = Actor(PortraitSpec(**HER, cloth="#3a3a40"), BodySpec(), make_pose("sit", yaw=28), WARDROBE["suit"], depth=0.0)
    him = Actor(PortraitSpec(**HIM, cloth="#2b3140"), MALE_BODY, make_pose("stance", yaw=-20), WARDROBE["suit"], depth=-0.9)
    her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "knee", centers=(0.42, 0.66))
    sk = Skeleton(her.pose, her.body, painting.shape)
    her.props = [props.chair(sk, color="#2b2b30", cushion="#4a4a52")]
    shoulder = sk.joints["shoulder_r"] - [0.0, 0.14 * sk.unit]
    him.pose = reach(him.pose, him.body, "l", shoulder, painting.shape, depth=0.9 + sk.depth["shoulder_r"])
    him.over = ("hand_l",)
    return "office", [her, him]


def night_street(painting):
    from codepainter.figure.body import Skeleton
    her = Actor(PortraitSpec(**HER, cloth="#f1ede4", cloth_second="#5a7aa8"), BodySpec(), make_pose("contrapposto", yaw=22),
                WARDROBE["crop_top_shorts"], depth=-0.3)
    him = Actor(PortraitSpec(**HIM, cloth="#4a4f57", cloth_second="#4f6f9c"), MALE_BODY, make_pose("stance", yaw=-18),
                WARDROBE["hoodie"], depth=0.0)
    her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "waist", centers=(0.38, 0.64))
    sk = Skeleton(him.pose, him.body, painting.shape)
    # Her near arm is hidden behind him: a hand laid over his sleeve would float there with no arm.
    # She reaches across with her left hand, elbow down and forward, and holds the outer side of his arm.
    arm = sk.joints["shoulder_l"] * 0.42 + sk.joints["elbow_l"] * 0.58 - [0.10 * sk.unit, 0.0]
    her.pose = reach(her.pose, her.body, "l", arm, painting.shape, depth=0.3 + sk.depth["elbow_l"], pole=(-0.3, 0.7, 0.6))
    her.hands = {"l": HOLD}
    her.over = ("hand_l",)
    return "night_street", [her, him]


def cafe(painting):
    from codepainter.figure.body import Skeleton
    her = Actor(PortraitSpec(**HER, cloth="#c7445a", cloth_second="#3a3a40", expression="smile"), BodySpec(), make_pose("sit_side"),
                WARDROBE["hoodie_shorts"])
    him = Actor(PortraitSpec(**HIM, cloth="#e8e0d0", cloth_second="#3a5a8a", glasses="round"), MALE_BODY,
                make_pose("sit_side", yaw=-90), WARDROBE["hoodie"])
    her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "full", centers=(0.33, 0.69))
    sk_her, sk_him = Skeleton(her.pose, her.body, painting.shape), Skeleton(him.pose, him.body, painting.shape)
    # one table between them, given to her: its middle is half way to him
    middle = (sk_him.origin[0] - sk_her.origin[0]) / 2 / sk_her.unit
    her.props = [props.chair(sk_her), props.table(sk_her, reach=middle, half=1.0)]
    him.props = [props.chair(sk_him)]
    return "cafe", [her, him]


def park(painting):
    from codepainter.figure.body import Skeleton
    her = Actor(PortraitSpec(**HER, cloth="#b8a0c8", hair_style="ponytail"), BodySpec(), make_pose("walk_side"),
                WARDROBE["slip_dress"], depth=0.2)
    him = Actor(PortraitSpec(**HIM, cloth="#e8e0d0", cloth_second="#3a5a8a"), MALE_BODY, make_pose("walk_side"), WARDROBE["hoodie"])
    her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "full", centers=(0.42, 0.62))
    sk_her, sk_him = Skeleton(her.pose, her.body, painting.shape), Skeleton(him.pose, him.body, painting.shape)
    meet = (sk_her.joints["hip_l"] + sk_him.joints["hip_r"]) / 2 + [0.0, 0.6 * sk_her.unit]
    her.pose = reach(her.pose, her.body, "l", meet, painting.shape)
    him.pose = reach(him.pose, him.body, "r", meet, painting.shape)
    return "park", [her, him]


SCENES = {"beach": (beach, LANDSCAPE), "bedroom": (bedroom, LANDSCAPE), "office": (office, LANDSCAPE),
          "night_street": (night_street, PORTRAIT), "cafe": (cafe, LANDSCAPE), "park": (park, LANDSCAPE)}


def render(scene, style_name, seed=3):
    style = get_style(style_name)
    build, (width, height) = SCENES[scene]
    painting = Painting(width, height)
    set_name, actors = build(painting)
    info = sets.SETS[set_name](painting, style)
    figures = draw_actors(painting, actors, style)
    sets.light_figures(painting, figures, info, style)
    if set_name != "bedroom":
        floor_shadows(painting, actors, style, color=info.ground)
    image = finish(painting, style, seed=seed, importance=np.maximum.reduce([a.masks["head"] for a in actors]))
    return painting, fx.grade(image, **info.grade)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="beach", choices=list(SCENES))
    parser.add_argument("--style", default="anime", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="scene.png")
    args = parser.parse_args()
    painting, image = render(args.scene, args.style)
    painting.save(args.out, image)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
