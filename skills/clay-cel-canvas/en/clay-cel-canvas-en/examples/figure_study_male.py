"""Worked example: figure studies of an adult man in three classical poses.

Usage: python figure_study_male.py <anime|illust|painterly> <output.png> [width_px] [standing|seated|reclining]

Same machinery as figure_study.py (draw_figure), with the male physique, the head from
portrait_male.py and poses of its own. Pelvic detail are not modelled; as in
classical sculpture and academic figure drawing, each pose hides the lower pelvis
with something natural: a cloth held at the hip, a raised thigh, a leg drawn
forward.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_study  # noqa: E402
import portrait_male  # noqa: E402
from atelier import Camera  # noqa: E402
from atelier.mannequin import MALE, Pose, Reach  # noqa: E402
from atelier.sculpt import Ellipsoid, RoundBox, facing, hanging_cloth, rotation  # noqa: E402

MAN = figure_study.Sitter(
    physique=MALE, head=portrait_male, head_chin=portrait_male.CHIN, head_units=portrait_male.HEAD_UNITS,
    skin={"skin": "#EFC9AE", "skin_shadow": "#C99080", "skin_deep": "#A9705F", "flush": "#E2A08C",
          "chest_tone": "#C98C7E", "chest_mark": "#A86A5E", "hair": portrait_male.PALETTE["hair"]},
    chest_mark=0.0032)

LINEN = ("#F1ECE3", "#B5AAC0")       # colour, shadow colour


def held_cloth(scene, marks):
    """A cloth held at the left hip, hanging across the front of the hips."""
    pelvis, frame = marks["pelvis"], marks["pelvis_frame"]
    start = marks["left_wrist"] + frame @ (-0.02, 0.025, -0.035)     # behind the fingers that grip it
    end = pelvis + frame @ (-0.15, -0.10, 0.07)
    hanging_cloth(scene, "cloth", start, end, (0.0, -0.03, -0.42), np.random.default_rng(3))
    return (("cloth", *LINEN),)


STANDING = figure_study.Setting(
    aspect=1.6,
    camera=Camera(eye=(0.0, -4.9, 1.12), target=(0.02, 0, 0.95), focal=3560, center=(500, 760)),
    pose=Pose(
        pelvis=(-0.03, 0.0, 0.935),
        pelvis_frame=rotation(12, 0, 7), chest_frame=rotation(6, 2, -5), head_frame=rotation(-8, 3, 4),
        left_hand=Reach((0.17, -0.12, 0.94), (0.5, 1, 0.1), (-0.3, -0.3, -1), (0.9, -0.3, 0), 0.6),
        right_hand=Reach((-0.28, 0.0, 0.88), (0.1, 1, 0), (0.0, -0.1, -1), (-1, 0.1, 0), 0.35),
        left_foot=Reach((0.18, -0.10, 0.124), (-0.25, -1, 0.1), (0.35, -1, 0), (0, 0, 1), 0.3),
        right_foot=Reach((-0.08, 0.0, 0.088), (0, -1, 0), (-0.35, -1, 0), (0, 0, 1), 0.0)),
    props=(("floor", RoundBox((0, 0.4, -0.05), (2.5, 1.5, 0.05), 0.01), "floor", "floor_shadow"),),
    extras=held_cloth,
)

# The raised thigh crosses toward the middle of the body, so from this camera it
# passes in front of the lower pelvis; the forearm rests over the knee.
SEATED = figure_study.Setting(
    aspect=1.2,
    camera=Camera(eye=(0.45, -2.7, 1.3), target=(-0.02, -0.12, 0.62), focal=1900, center=(500, 590)),
    pose=Pose(
        pelvis=(-0.02, 0.10, 0.58),
        pelvis_frame=rotation(-12, -6, 0), chest_frame=rotation(-2, 12, -3), head_frame=rotation(12, 10, 3),
        left_hand=Reach((0.054, -0.33, 0.699), (0.9, 0.6, 0.2), (0.0, -0.4, -1), (0.4, -0.6, 0.4), 0.45),
        right_hand=Reach((-0.314, 0.212, 0.532), (-0.3, 1, 0), (-0.2, 0.9, -0.2), (0, 0, 1), 0.15),
        left_foot=Reach((-0.05, -0.50, 0.31), (-0.15, -1, 0.6), (0.0, -1, 0), (0, 0, 1), 0.2),
        right_foot=Reach((-0.32, -0.30, 0.11), (-0.2, -0.6, 0.8), (-0.3, -1, 0), (0, 0, 1), 0.2)),
    props=(("floor", RoundBox((0, 0.4, -0.05), (2.5, 1.8, 0.05), 0.01), "floor", "floor_shadow"),
           ("seat", RoundBox((0.0, 0.10, 0.23), (0.36, 0.30, 0.23), 0.06), "couch", "couch_shadow"),
           ("seat", RoundBox((-0.05, -0.50, 0.10), (0.16, 0.13, 0.10), 0.03), "couch", "couch_shadow"),
           ("cloth", RoundBox((0.0, 0.10, 0.465), (0.35, 0.29, 0.022), 0.02), "linen", "linen_shadow")),
    # The left wrist lies just past the raised knee, so the forearm rests over it.
)

RECLINING = figure_study.Setting(
    aspect=0.66,
    camera=Camera(eye=(0.12, -2.9, 1.25), target=(0.12, 0.1, 0.66), focal=1500, center=(475, 340)),
    pose=Pose(
        pelvis=(0.12, 0.18, 0.60),
        pelvis_frame=facing(up=(-1, 0, 0.12), front=(0.1, -0.85, 0.5)),
        chest_frame=facing(up=(-0.78, 0.05, 0.63), front=(0.05, -0.95, 0.3)),
        head_frame=facing(up=(-0.18, 0.05, 0.98), front=(0.25, -0.97, 0.0)),
        left_hand=Reach((0.187, -0.120, 0.850), (0.1, 0.6, 1), (1, -0.3, -0.25), (0, -0.25, 0.97), 0.7),
        right_hand=Reach((-0.66, -0.12, 0.60), (0.0, 0.4, -1), (0.6, -0.8, 0.0), (0, 0, 1), 0.35),
        left_foot=Reach((0.62, -0.20, 0.57), (0.2, -1, 0.3), (1, -0.2, -0.2), (0, -0.8, 0.6), 0.4),
        right_foot=Reach((0.981, 0.121, 0.53), (0.0, -1, 0.3), (1, 0, -0.1), (0, -1, 0.3), 0.4)),
    props=(("couch", RoundBox((0.10, 0.25, 0.22), (1.25, 0.45, 0.22), 0.08), "couch", "couch_shadow"),
           ("back", RoundBox((0.10, 0.64, 0.70), (1.25, 0.12, 0.30), 0.10), "couch", "couch_shadow"),
           ("sheet", RoundBox((0.05, 0.20, 0.445), (1.12, 0.44, 0.014), 0.01), "linen", "linen_shadow"),
           ("pillow", Ellipsoid((-0.86, 0.26, 0.56), (0.25, 0.26, 0.13)), "linen", "linen_shadow"),
           ("pillow", Ellipsoid((-0.92, 0.36, 0.72), (0.21, 0.22, 0.14)), "linen", "linen_shadow")),
    room="hanging",
    # The left hand lies flat over the raised thigh with the thumb tucked, so
    # nothing hangs into the gap between the thighs.
)

SETTINGS = {"standing": STANDING, "seated": SEATED, "reclining": RECLINING}


def draw(style_name, width_px, pose_name="standing"):
    return figure_study.draw_figure(style_name, width_px, SETTINGS[pose_name], MAN)


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width, sys.argv[4] if len(sys.argv) > 4 else "standing")
    picture.save(output)
    print(f"saved {output}")
