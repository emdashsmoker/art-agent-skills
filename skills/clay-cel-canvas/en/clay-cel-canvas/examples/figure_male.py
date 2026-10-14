"""Worked example: full-length clothed man, built on the 3-D mannequin.

Usage: python figure_male.py <anime|illust|painterly> <output.png> [width_px]

Clothes are the body grown outward (mannequin.dress): a shirt over the chest
and belly, trousers over the hips and legs. Grown from the same forms, they
follow every curve and joint of the body. What the body does not have is added
as plain shapes: straight sleeves, a looser straight trouser leg below the
knee, a collar, a belt, shoes. A hand in a pocket is simply a hand pushed into
the trousers; the cloth in front of it hides the fingers.

The clothed man is built leaner than the figure study: narrower shoulders and
slimmer arms. Sleeves are plain tubes, so the arm muscles do not show through
the cloth; a sleeve grown from the arm would show every muscle and make the
figure look like a bodybuilder.
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_study  # noqa: E402
import figure_study_male  # noqa: E402
from atelier import Camera  # noqa: E402
from atelier.mannequin import MALE, TROUSERS, Pose, Reach, dress  # noqa: E402
from atelier.sculpt import Capsule, Ellipsoid, RoundBox, facing, rotation  # noqa: E402

LEAN = replace(MALE, shoulder_joint=(0.157, 0.012, 0.296),
               deltoid=((0.160, 0.012, 0.292), (0.050, 0.054, 0.064)),
               arm_radii=(0.047, 0.035, 0.037, 0.037, 0.026),
               thigh_radii=(0.084, 0.050), shin_radii=(0.049, 0.029), calf_radii=(0.046, 0.044, 0.13))
SITTER = replace(figure_study_male.MAN, physique=LEAN)
SHIRT_BODY = ("chest", "abdomen")  # the sleeves are separate tubes
SHIRT_FIT = 0.012                  # metres of cloth over the skin
SLEEVE = (0.060, 0.050, 0.041)     # radius at the shoulder, the elbow and the cuff
SLEEVE_BLEND = 0.03
# Cloth bridges the hollows between muscles. Kept small: every melt adds a little
# volume, and over dozens of overlapping forms a large value inflates the garment.
CLOTH_SMOOTH = 0.012
NECKLINE_CENTRE, NECKLINE = (0.0, -0.015, 0.0), (0.080, 0.105, 0.075)   # round cut at the neck base
V_CENTRE, V_RADII = (0.0, -0.100, -0.080), (0.032, 0.065, 0.100)        # the open front of the shirt
COLLAR_RADIUS = 0.011
SHOE = (0.050, 0.150, 0.042)       # half width, half length, half height: slim, not a block
SHOE_COVER = 0.006                 # the foot grown into the shoe, so no part of it pokes through
TROUSER_FIT = 0.012
TROUSER_KNEE = 0.064               # radius of the straight leg at the knee
TROUSER_HEM = 0.060                # radius of the straight leg at the ankle
TROUSER_DROP_FROM = 0.07           # metres above the knee where the straight leg begins
COLORS = {
    "shirt": ("#F4F4F2", "#B6BBD0"), "trousers": ("#3A3F52", "#232636"),
    "belt": ("#5A3B28", "#33221A"), "shoes": ("#2A2224", "#151012"),
}

POSE = Pose(
    pelvis=(-0.03, 0.0, 0.935),
    pelvis_frame=rotation(12, 0, 6), chest_frame=rotation(6, 2, -4), head_frame=rotation(-10, 2, 4),
    left_hand=Reach((0.165, -0.035, 0.955), (0.6, 1, 0.2), (-0.15, 0.1, -1), (1, -0.3, 0), 0.35),
    right_hand=Reach((-0.25, 0.01, 0.87), (0.1, 1, 0), (0.0, -0.1, -1), (-1, 0.1, 0), 0.35),
    left_foot=Reach((0.18, -0.10, 0.124), (-0.25, -1, 0.1), (0.35, -1, 0), (0, 0, 1), 0.3),
    right_foot=Reach((-0.08, 0.0, 0.098), (0, -1, 0), (-0.35, -1, 0), (0, 0, 1), 0.0))


def shoe(scene, ankle, reach):
    """Shoe as one rounded box around the whole foot: a box keeps its full height to
    the toe, where an oval would thin out and let the toes poke through."""
    up = np.asarray(reach.back, float) / np.linalg.norm(reach.back)
    forward = np.asarray(reach.forward, float) - up * (np.asarray(reach.forward, float) @ up)
    forward /= np.linalg.norm(forward)
    frame = facing(up, -forward)                       # local +y runs along the foot
    width, length, height = SHOE
    scene.add(RoundBox(ankle + forward * 0.078 - up * 0.052, (width, length, height), 0.030, frame), "shoes")
    scene.add(RoundBox(ankle + forward * 0.078 - up * 0.092, (width + 0.002, length + 0.004, 0.008), 0.006,
                       frame), "shoes", 0.008)         # the sole
    scene.add(Capsule(ankle - up * 0.02, 0.038, ankle - up * 0.045 + forward * 0.06, 0.042), "shoes", 0.03)


def open_collar(scene, marks):
    """Open the neck of the shirt and lay a collar round it.

    The shirt is the body grown outward, so it would also swallow the base of
    the neck and the top of the shoulders. Carve a round neckline and an open V
    out of it, then lay a rolled collar along the cut edge.
    """
    neck, chest = marks["neck"], marks["chest_frame"]
    scene.carve(Ellipsoid(neck + chest @ NECKLINE_CENTRE, NECKLINE, chest), "shirt", 0.006)
    scene.carve(Ellipsoid(neck + chest @ V_CENTRE, V_RADII, chest), "shirt", 0.006)
    path = [(0.0, 0.070, 0.006), (0.050, 0.052, 0.002), (0.074, 0.008, -0.006), (0.064, -0.040, -0.030),
            (0.040, -0.072, -0.072), (0.022, -0.082, -0.112)]   # back of the neck to the collar point
    for side in (-1, 1):
        points = [neck + chest @ (side * x, y, z) for x, y, z in path]
        for a, b in zip(points[:-1], points[1:]):
            scene.add(Capsule(a, COLLAR_RADIUS, b, COLLAR_RADIUS * 0.9), "shirt", 0.006)


def sleeves(scene, marks):
    """Straight sleeves from the shoulder to just above the wrist."""
    shoulder_radius, elbow_radius, cuff_radius = SLEEVE
    for side, name in ((1, "left"), (-1, "right")):
        x, y, z = LEAN.shoulder_joint
        shoulder = marks["chest"] + marks["chest_frame"] @ (side * x, y, z)
        elbow, wrist = marks[f"{name}_elbow"], marks[f"{name}_wrist"]
        cuff = wrist + (elbow - wrist) * 0.06
        scene.add(Capsule(shoulder, shoulder_radius, elbow, elbow_radius), "shirt", SLEEVE_BLEND,
                  shoulder, 0.15)
        scene.add(Capsule(elbow, elbow_radius, cuff, cuff_radius), "shirt", SLEEVE_BLEND, elbow, 0.08)


def clothes(scene, marks):
    dress(scene, marks, "shirt", SHIRT_BODY, SHIRT_FIT, smooth=CLOTH_SMOOTH)
    sleeves(scene, marks)
    open_collar(scene, marks)
    dress(scene, marks, "trousers", TROUSERS, TROUSER_FIT, smooth=CLOTH_SMOOTH)
    for side, foot in (("left", POSE.left_foot), ("right", POSE.right_foot)):
        knee, ankle = marks[f"{side}_knee"], marks[f"{side}_ankle"]
        # Starts above the knee so the cloth falls past the kneecap instead of wrapping it.
        scene.add(Capsule(knee + (0, 0, TROUSER_DROP_FROM), TROUSER_KNEE, ankle + (0, 0, 0.02), TROUSER_HEM),
                  "trousers", 0.03)
        shoe(scene, ankle, foot)
    dress(scene, marks, "shoes", ("foot",), SHOE_COVER, smooth=CLOTH_SMOOTH)
    pelvis, frame = marks["pelvis"], marks["pelvis_frame"]
    ring = [pelvis + frame @ (0.160 * np.sin(t), -0.118 * np.cos(t) + 0.004, 0.172)
            for t in np.radians(np.arange(-180, 181, 12))]
    for a, b in zip(ring[:-1], ring[1:]):
        scene.add(Capsule(a, 0.018, b, 0.018), "belt", 0.004)
    return tuple((group, *COLORS[group]) for group in ("shirt", "belt", "trousers", "shoes"))


SETTING = figure_study.Setting(
    aspect=1.6,
    # Near eye level: a camera at hip height looks up at the figure, the heroic
    # angle that makes anyone look big and strong.
    camera=Camera(eye=(0.0, -4.9, 1.45), target=(0.02, 0, 0.93), focal=3560, center=(500, 760)),
    pose=POSE,
    props=(("floor", RoundBox((0, 0.4, -0.05), (2.5, 1.5, 0.05), 0.01), "pavement", "pavement_shadow"),),
    room="dusk",
    extras=clothes,
)


def draw(style_name, width_px):
    return figure_study.draw_figure(style_name, width_px, SETTING, SITTER)


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
