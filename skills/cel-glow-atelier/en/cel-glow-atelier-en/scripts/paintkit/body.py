"""paintkit.body: proportions, build, poses and the 2D skeleton.

Pure geometry in head units (1.0 = crown to chin), measured from the pelvis
center. A Pose is a handful of angles; `solve_skeleton` turns it into joint
positions. Nothing here paints; figure.py does.

Angles are in degrees. For limbs 0 points straight down and positive
swings toward the viewer's right; for the spine 0 points straight up and
positive leans toward the viewer's right. "left"/"right" always mean the
viewer's left and right.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, replace

import numpy as np

# ---------------------------------------------------------------------------
# Proportions (head units). Standing height: about 7.2 heads (female plan),
# 7.5 heads (male plan).
# ---------------------------------------------------------------------------
SPINE_LOW = 0.80          # pelvis center -> waist
SPINE_HIGH = 1.12         # waist -> shoulder line
NECK_RISE = 0.15          # shoulder line -> pit of the neck
NECK_LENGTH = 0.40        # pit of the neck -> skull pivot
SKULL_TO_EYES = 0.30
SHOULDER_HALF = 0.490
SHOULDER_DROP = 0.115
HIP_HALF = 0.300
HIP_DROP = 0.05
UPPER_ARM, FOREARM, HAND_LENGTH = 1.18, 1.00, 0.66
THIGH, SHIN = 1.84, 1.70
NECK_WIDTH = (0.315, 0.252, 0.242)      # base, middle, under the jaw
# Width profiles: (position along the segment 0-1, diameter).
UPPER_ARM_WIDTH = ((0.0, 0.290), (0.25, 0.272), (0.70, 0.230), (1.0, 0.215))
FOREARM_WIDTH = ((0.0, 0.215), (0.20, 0.236), (0.60, 0.186), (0.90, 0.142), (1.0, 0.144))
THIGH_WIDTH = ((0.0, 0.600), (0.10, 0.606), (0.30, 0.565), (0.55, 0.460), (0.80, 0.352), (1.0, 0.306))
SHIN_WIDTH = ((0.0, 0.306), (0.10, 0.322), (0.27, 0.356), (0.50, 0.292), (0.75, 0.202), (0.93, 0.160),
              (1.0, 0.168))
# Sideways bow of a limb's centerline (position, offset toward the outside).
# Muscles do not sit symmetrically on the bone: the outer thigh arcs, the
# calf swells high on the outside and lower on the inside. Without this
# every limb is a straight tube.
THIGH_BOW = ((0.0, 0.0), (0.30, 0.016), (0.65, 0.022), (1.0, 0.0))
SHIN_BOW = ((0.0, 0.0), (0.20, 0.026), (0.45, -0.006), (0.80, -0.004), (1.0, 0.0))
FOREARM_BOW = ((0.0, 0.0), (0.25, 0.014), (1.0, 0.0))
# Right half of the torso outline, top to bottom. Chest points are measured
# from the shoulder line (y down the spine), pelvis points from the pelvis
# center. Third value: which build factor scales the point's width.
CHEST_SIDE = ((0.115, -0.175, "neck"), (0.215, -0.130, "neck"), (0.395, -0.050, "shoulders"),
              (0.500, 0.045, "shoulders"), (0.445, 0.270, "shoulders"), (0.452, 0.520, "bust"),
              (0.385, 0.800, "waist"), (0.290, 1.060, "waist"))
PELVIS_SIDE = ((0.405, -0.480, "hips"), (0.540, -0.150, "hips"),
               (0.605, 0.130, "hips"), (0.560, 0.350, "hips"), (0.180, 0.430, "hips"))
CROTCH_Y = 0.385
BUST_CENTER = (0.212, 0.550)      # chest frame
BUST_RADIUS = 0.212
# How far in front of the turning axis things sit (for Pose.turn).
DEPTH = {"bust": 0.30, "chest": 0.20, "belly": 0.24, "crotch": 0.12}
MAX_TURN_DEG = 40.0
# Front view of a foot flat on the ground: short and wide, big toe on the inner (-x) side.
FOOT_SHAPE = np.array([[-0.078, -0.05], [0.078, -0.05], [0.118, 0.10], [0.140, 0.20], [0.105, 0.275],
                       [0.000, 0.300], [-0.090, 0.280], [-0.112, 0.18], [-0.100, 0.08]], np.float32)
# On heels the foot points down, so more of its length shows from the front.
FOOT_HEELED = np.array([[-0.070, -0.05], [0.070, -0.05], [0.100, 0.20], [0.092, 0.40], [0.050, 0.520],
                        [0.000, 0.560], [-0.050, 0.520], [-0.092, 0.40], [-0.100, 0.20]], np.float32)
SIDES = {"left": -1.0, "right": 1.0}
# Handy wrist targets for `reach_*` (viewer's-right side; mirror x for the left).
# Poses name them ("hip"), so each body plan can place them on its own body.
REACH = {
    "hip": (0.610, -0.250),
    "front": (0.075, 0.050),
    "wave": (1.380, -2.620),
    "by_face": (0.700, -2.200),
    "chest": (0.120, -1.380),
    "behind_head": (0.400, -3.050),
    "crown": (0.230, -2.930),
    "lap": (0.100, 0.160),
    "pocket": (0.420, -0.080),
}


@dataclass(frozen=True)
class BodyPlan:
    """Every proportion of one body type. `female` uses the constants above."""
    spine_low: float = SPINE_LOW
    spine_high: float = SPINE_HIGH
    neck_rise: float = NECK_RISE
    neck_length: float = NECK_LENGTH
    skull_to_eyes: float = SKULL_TO_EYES
    shoulder_half: float = SHOULDER_HALF
    shoulder_drop: float = SHOULDER_DROP
    hip_half: float = HIP_HALF
    hip_drop: float = HIP_DROP
    upper_arm: float = UPPER_ARM
    forearm: float = FOREARM
    hand_length: float = HAND_LENGTH
    thigh: float = THIGH
    shin: float = SHIN
    neck_width: tuple = NECK_WIDTH
    upper_arm_width: tuple = UPPER_ARM_WIDTH
    forearm_width: tuple = FOREARM_WIDTH
    thigh_width: tuple = THIGH_WIDTH
    shin_width: tuple = SHIN_WIDTH
    thigh_bow: tuple = THIGH_BOW
    shin_bow: tuple = SHIN_BOW
    forearm_bow: tuple = FOREARM_BOW
    chest_side: tuple = CHEST_SIDE
    pelvis_side: tuple = PELVIS_SIDE
    crotch_y: float = CROTCH_Y
    bust_center: tuple = BUST_CENTER
    bust_radius: float = BUST_RADIUS
    bust_dome: float = 0.90           # height of the bust form relative to its radius
    bust_slope: float = 0.32          # how far the upper bust eases into the chest
    bust_aspect: float = 1.0          # width / height of the bust form (wide, flat plates for chest muscles)
    foot_shape: np.ndarray = field(default_factory=lambda: FOOT_SHAPE)
    foot_heeled: np.ndarray = field(default_factory=lambda: FOOT_HEELED)
    hand_widen: float = 1.0           # finger and palm thickness
    reach: dict = None

    def target(self, name: str) -> tuple:
        table = self.reach or REACH
        if name not in table:
            raise ValueError(f"unknown reach target '{name}', expected one of {sorted(table)}")
        return table[name]


FOOT_SCALE_MALE = np.array([1.12, 1.10], np.float32)
PLANS = {
    "female": BodyPlan(),
    # Broad shoulders and a narrow pelvis (V taper), thicker neck and limbs,
    # flat chest muscles in place of the bust, larger hands and feet.
    "male": BodyPlan(
        spine_low=0.84, spine_high=1.16, neck_rise=0.14, neck_length=0.34, shoulder_half=0.660,
        shoulder_drop=0.170, hip_half=0.245, upper_arm=1.24, forearm=1.06, hand_length=0.72, thigh=1.95, shin=1.82,
        neck_width=(0.430, 0.345, 0.325),
        upper_arm_width=((0.0, 0.400), (0.18, 0.385), (0.50, 0.335), (0.80, 0.285), (1.0, 0.262)),
        forearm_width=((0.0, 0.262), (0.20, 0.292), (0.55, 0.236), (0.88, 0.182), (1.0, 0.182)),
        thigh_width=((0.0, 0.560), (0.12, 0.565), (0.40, 0.505), (0.75, 0.405), (1.0, 0.345)),
        shin_width=((0.0, 0.350), (0.10, 0.370), (0.28, 0.400), (0.52, 0.320), (0.78, 0.240), (0.94, 0.205),
                    (1.0, 0.215)),
        thigh_bow=((0.0, 0.0), (0.35, 0.012), (0.70, 0.016), (1.0, 0.0)),
        shin_bow=((0.0, 0.0), (0.25, 0.030), (0.50, -0.004), (1.0, 0.0)),
        forearm_bow=((0.0, 0.0), (0.25, 0.020), (1.0, 0.0)),
        chest_side=((0.150, -0.180, "neck"), (0.300, -0.120, "neck"), (0.560, -0.050, "shoulders"),
                    (0.700, 0.080, "shoulders"), (0.630, 0.320, "shoulders"), (0.590, 0.540, "bust"),
                    (0.500, 0.820, "waist"), (0.465, 1.080, "waist")),
        pelvis_side=((0.455, -0.480, "hips"), (0.470, -0.150, "hips"), (0.485, 0.130, "hips"),
                     (0.440, 0.350, "hips"), (0.170, 0.430, "hips")),
        crotch_y=0.400, bust_center=(0.240, 0.400), bust_radius=0.250, bust_dome=0.16, bust_slope=0.0,
        bust_aspect=1.40,
        foot_shape=FOOT_SHAPE * FOOT_SCALE_MALE, foot_heeled=FOOT_HEELED * FOOT_SCALE_MALE, hand_widen=1.15,
        reach={"hip": (0.540, -0.250), "front": (0.080, 0.060), "wave": (1.500, -2.750),
               "by_face": (0.760, -2.300), "chest": (0.140, -1.450), "behind_head": (0.420, -3.180),
               "crown": (0.250, -3.050), "lap": (0.100, 0.160), "pocket": (0.400, -0.060)}),
}


def plan_for(gender: str) -> BodyPlan:
    if gender not in PLANS:
        raise ValueError(f"unknown gender '{gender}', expected one of {list(PLANS)}")
    return PLANS[gender]


@dataclass
class Build:
    """Body shape as multipliers of the default figure (1.0 = default)."""
    bust: float = 1.0
    waist: float = 1.0
    hips: float = 1.0
    shoulders: float = 1.0
    legs: float = 1.0             # leg length
    muscle: float = 1.0           # limb thickness and how strongly muscles are modeled

    def scale(self, key: str) -> float:
        if key == "bust":         # the ribcage widens only a little with the bust
            return 1.0 + 0.10 * (self.bust - 1.0)
        return getattr(self, key, 1.0)


@dataclass
class Pose:
    spine: float = 0.0            # lean of the lower back
    chest: float = 0.0            # lean of the upper body
    neck: float = 0.0             # lean of the neck (the head follows)
    hip_tilt: float = 0.0         # positive lowers the viewer's-right hip
    shoulder_tilt: float = 0.0    # positive lowers the viewer's-right shoulder
    turn: float = 0.0             # body turned about its vertical axis; positive faces the viewer's right
    arm_left: tuple = (-9.0, -5.0)     # (upper arm, forearm) angles
    arm_right: tuple = (9.0, 5.0)
    leg_left: tuple = (-2.5, -1.0)     # (thigh, shin) angles
    leg_right: tuple = (2.5, 1.0)
    arm_left_scale: tuple = (1.0, 1.0)   # below 1 foreshortens a segment (limb toward the viewer)
    arm_right_scale: tuple = (1.0, 1.0)
    leg_left_scale: tuple = (1.0, 1.0)
    leg_right_scale: tuple = (1.0, 1.0)
    hand_left: str = "relaxed"
    hand_right: str = "relaxed"
    hand_left_view: str = "back"
    hand_right_view: str = "back"
    # Wrist targets: a name from REACH ("hip"), [x, y] in head units from
    # the pelvis center, or [joint, dx, dy] relative to a leg joint
    # (["knee_right", 0.1, -0.1]). When set, the arm angles are solved from
    # the target, which is easier than guessing angles.
    reach_left: tuple | str | None = None
    reach_right: tuple | str | None = None
    elbow_left: float = 1.0       # 1 = natural elbow (low and away from the body), -1 = the other solution
    elbow_right: float = 1.0
    hand_left_angle: float | None = None    # direction the fingers point; None follows the forearm
    hand_right_angle: float | None = None
    hand_left_roll: float = 0.0   # turn about the hand's long axis; positive shows the thumb side (see hand.Hand)
    hand_right_roll: float = 0.0
    hand_left_pitch: float = 0.0  # fingers tipped toward the viewer (0-75)
    hand_right_pitch: float = 0.0
    foot_left: float = -14.0      # which way the toes point
    foot_right: float = 14.0
    behind: tuple = ()            # arms drawn behind the torso, e.g. ("left",)
    front: tuple = ()             # arms drawn over the head and hair
    first_leg: str = "left"       # the leg drawn first ends up behind the other
    legs_front: bool = False      # legs drawn over the torso (thighs coming toward the viewer: sitting)
    seat: float | None = None     # height of a seat under the pelvis (head units below the pelvis center)
    support: str | None = None    # furniture the pose needs: "stool" (seated) or "pillar" (leaning)


POSES = {
    "standing": Pose(),
    "contrapposto": Pose(spine=-4.0, chest=5.0, neck=-3.0, hip_tilt=-7.0, shoulder_tilt=4.0,
                         reach_right="hip", hand_right="together", hand_right_angle=-28.0,
                         arm_left=(-8.0, -3.0), leg_right=(1.0, 0.0), leg_left=(-10.0, 3.0),
                         foot_left=-24.0, first_leg="left"),
    "akimbo": Pose(reach_left="hip", reach_right="hip", hand_left="together",
                   hand_right="together", hand_left_angle=28.0, hand_right_angle=-28.0,
                   leg_left=(-6.0, -2.0), leg_right=(6.0, 2.0)),
    "wave": Pose(chest=-2.0, neck=3.0, shoulder_tilt=-4.0, reach_right="wave",
                 hand_right="open", hand_right_view="palm", hand_right_angle=172.0,
                 arm_left=(-7.0, -3.0), leg_left=(-3.0, -1.0), leg_right=(4.0, 1.0)),
    "clasped": Pose(reach_left="front", reach_right="front", hand_left="together",
                    hand_right="together", hand_left_angle=38.0, hand_right_angle=-38.0,
                    leg_left=(-1.5, 0.0), leg_right=(1.5, 0.0)),
    "peace": Pose(chest=2.0, neck=-4.0, hip_tilt=-3.0, reach_right="by_face",
                  arm_right_scale=(0.45, 0.66), hand_right="peace", hand_right_view="palm",
                  hand_right_angle=176.0, front=("right",),
                  arm_left=(-12.0, -6.0), leg_left=(-7.0, 1.0), leg_right=(2.0, 0.0)),
    # One hand behind the head, the other on the raised hip: the classic S-curve.
    "showcase": Pose(spine=-6.0, chest=7.0, neck=-5.0, hip_tilt=-9.0, shoulder_tilt=6.0,
                  reach_right="hip", hand_right="together", hand_right_angle=-30.0,
                  reach_left="crown", arm_left_scale=(0.92, 0.78), hand_left="relaxed",
                  hand_left_angle=120.0, leg_right=(1.0, 0.0), leg_left=(-13.0, 6.0), foot_left=-26.0),
    # Mid-stride: the front leg steps toward the midline, the back leg is
    # foreshortened, arms swing opposite to the legs.
    "walk": Pose(spine=3.0, chest=-4.0, neck=2.0, hip_tilt=6.0, shoulder_tilt=-5.0,
                 leg_left=(6.5, -4.5), leg_right=(1.0, 4.0), leg_right_scale=(0.97, 0.74),
                 arm_left=(-17.0, -5.0), arm_right=(9.0, 15.0), arm_right_scale=(1.0, 0.90),
                 foot_left=-4.0, foot_right=12.0,
                 first_leg="right"),
    # Seated on a stool, knees together and slanted to one side.
    "sitting": Pose(spine=2.0, chest=-2.0, neck=2.0, shoulder_tilt=-2.0,
                    leg_left=(9.0, 16.0), leg_right=(-3.0, 16.0), leg_left_scale=(0.42, 1.0),
                    leg_right_scale=(0.42, 1.0), foot_left=20.0, foot_right=26.0,
                    reach_left="lap", reach_right="lap", hand_left="together",
                    hand_right="together", hand_left_angle=55.0, hand_right_angle=-55.0,
                    legs_front=True, front=(), seat=0.50, first_leg="right", support="stool"),
    # Seated, the viewer's-right leg crossed over the other knee, hands resting on the top knee.
    "sitting_crossed": Pose(spine=3.0, chest=-3.0, neck=3.0, shoulder_tilt=-2.0, hip_tilt=2.0,
                            leg_left=(8.0, 14.0), leg_left_scale=(0.42, 1.0), leg_right=(-52.0, -20.0),
                            leg_right_scale=(0.48, 0.88), foot_left=18.0, foot_right=-34.0,
                            reach_left=("knee_right", 0.02, -0.16), reach_right=("knee_right", 0.20, -0.10),
                            hand_left="together", hand_right="together", hand_left_angle=75.0,
                            hand_right_angle=-70.0, legs_front=True, seat=0.50, first_leg="left",
                            support="stool"),
    # Leaning with the viewer's-left shoulder on a pillar, ankles crossed, the body a long diagonal.
    "lean": Pose(spine=-9.0, chest=-3.0, neck=9.0, hip_tilt=4.0, shoulder_tilt=5.0,
                 reach_right="hip", hand_right="together", hand_right_angle=-32.0, arm_left=(-3.0, 8.0),
                 leg_right=(7.0, 1.0), leg_left=(21.0, 9.0), foot_right=20.0, foot_left=10.0,
                 first_leg="right", support="pillar"),
    # Body turned away, head looking back toward the viewer.
    "three_quarter": Pose(turn=30.0, spine=-2.0, chest=3.0, hip_tilt=-4.0, shoulder_tilt=3.0,
                          arm_left=(-6.0, -10.0), arm_right=(5.0, 2.0), leg_left=(-2.0, 0.0),
                          leg_right=(6.0, -3.0), behind=("right",), first_leg="right"),
    # Arms folded under the chest: the viewer's-right forearm over the other, its hand on
    # the opposite upper arm; the other hand tucked away under it.
    "arms_crossed": Pose(spine=-2.0, chest=1.0, neck=-2.0, hip_tilt=-4.0, shoulder_tilt=2.0,
                         reach_left=("chest", 0.46, 1.00), reach_right=("chest", -0.50, 0.84),
                         hand_left="tucked", hand_right="grip", hand_right_angle=172.0, hand_right_roll=55.0,
                         leg_left=(-3.0, 1.0), leg_right=(5.0, -1.0), front=("left", "right")),
    # Hands in the front pockets, weight on one leg.
    "pockets": Pose(spine=-3.0, chest=3.0, neck=-3.0, hip_tilt=-6.0, shoulder_tilt=3.0,
                    reach_left="pocket", reach_right="pocket", hand_left="pocket", hand_right="pocket",
                    hand_left_angle=12.0, hand_right_angle=-12.0, leg_left=(-9.0, 3.0), leg_right=(2.0, 0.0),
                    foot_left=-16.0, first_leg="left"),
    # Both arms stretched up over the head, hands joined, the back arched.
    "stretch": Pose(spine=-3.0, chest=-4.0, neck=-4.0, hip_tilt=-6.0, shoulder_tilt=3.0,
                    reach_left=("skull", -0.06, -1.05), reach_right=("skull", 0.06, -1.05),
                    hand_left="together", hand_right="together", hand_left_angle=170.0, hand_right_angle=-170.0,
                    leg_left=(-6.0, 2.0), leg_right=(3.0, 0.0), foot_left=-12.0),
}


def _up(deg: float) -> np.ndarray:
    rad = np.deg2rad(deg)
    return np.array([np.sin(rad), -np.cos(rad)], np.float32)


def _down(deg: float) -> np.ndarray:
    rad = np.deg2rad(deg)
    return np.array([np.sin(rad), np.cos(rad)], np.float32)


def _across(deg: float) -> np.ndarray:
    rad = np.deg2rad(deg)
    return np.array([np.cos(rad), np.sin(rad)], np.float32)


def _from_dict(cls, name: str, values: dict):
    known = {f.name for f in fields(cls)}
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"unknown {name} keys {sorted(unknown)}; allowed: {sorted(known)}")
    return {k: tuple(v) if isinstance(v, list) else v for k, v in values.items()}


def make_pose(name: str = "standing", overrides: dict | None = None) -> Pose:
    if name not in POSES:
        raise ValueError(f"unknown front pose '{name}', expected one of {list(POSES)}")
    return replace(POSES[name], **_from_dict(Pose, "pose", overrides or {}))


def make_build(values: dict | None = None) -> Build:
    return Build(**_from_dict(Build, "build", values or {}))


def solve_arm(shoulder, target, outward: float, flip: float, scale=(1.0, 1.0), plan: BodyPlan = PLANS["female"]):
    """Two-bone reach: (upper arm angle, forearm angle) that put the wrist on `target`.

    Of the two possible elbow positions the natural one is taken: the elbow
    that ends up lower and further from the body. flip = -1 takes the other.
    """
    upper_len, fore_len = plan.upper_arm * scale[0], plan.forearm * scale[1]
    offset = np.asarray(target, np.float32) - shoulder
    distance = float(np.clip(np.linalg.norm(offset), abs(upper_len - fore_len) + 1e-3,
                             upper_len + fore_len - 1e-3))
    base = np.degrees(np.arctan2(offset[0], offset[1]))
    inner = np.degrees(np.arccos((upper_len ** 2 + distance ** 2 - fore_len ** 2) / (2 * upper_len * distance)))
    wrist = shoulder + offset / np.linalg.norm(offset) * distance
    options = []
    for bend in (1.0, -1.0):
        upper = base + inner * bend
        elbow = shoulder + _down(upper) * upper_len
        fore = np.degrees(np.arctan2(wrist[0] - elbow[0], wrist[1] - elbow[1]))
        options.append((elbow[0] * outward + elbow[1], float(upper), float(fore)))
    options.sort(reverse=True)
    _, upper, fore = options[0 if flip >= 0 else 1]
    return upper, fore


def turn_factors(pose: Pose):
    """(cos, sin) of the body turn, clamped to the range the rig can draw."""
    rad = np.deg2rad(float(np.clip(pose.turn, -MAX_TURN_DEG, MAX_TURN_DEG)))
    return float(np.cos(rad)), float(np.sin(rad))


def reach_point(target, sign: float, plan: BodyPlan, joints: dict):
    """Wrist target in head units. A named target is mirrored to the arm's
    side; [joint, dx, dy] is an offset from an already solved leg joint."""
    if isinstance(target, str):
        x, y = plan.target(target)
        return (x * sign, y)
    if isinstance(target[0], str):
        name, dx, dy = target
        if name not in joints:
            raise ValueError(f"unknown reach joint '{name}', expected one of {sorted(joints)}")
        return joints[name] + np.array([dx, dy], np.float32)
    return target


def solve_skeleton(pose: Pose, build: Build | None = None, plan: BodyPlan | None = None) -> dict:
    """Joint positions in head units, relative to the pelvis center."""
    build = build or Build()
    plan = plan or PLANS["female"]
    narrow, _ = turn_factors(pose)        # a turned body is narrower across
    j = {"pelvis": np.zeros(2, np.float32)}
    j["waist"] = j["pelvis"] + _up(pose.spine) * plan.spine_low
    j["chest"] = j["waist"] + _up(pose.chest) * plan.spine_high
    j["neck"] = j["chest"] + _up(pose.chest) * plan.neck_rise
    j["skull"] = j["neck"] + _up(pose.neck) * plan.neck_length
    j["eyes"] = j["skull"] + _up(pose.neck) * plan.skull_to_eyes
    shoulder_axis = _across(pose.chest + pose.shoulder_tilt)
    hip_axis = _across(pose.hip_tilt)
    # Legs first: an arm may reach for a knee.
    for side, sign in SIDES.items():
        hip = (j["pelvis"] + hip_axis * plan.hip_half * build.hips * narrow * sign
               + np.array([0.0, plan.hip_drop], np.float32))
        thigh, shin = getattr(pose, f"leg_{side}")
        scale = getattr(pose, f"leg_{side}_scale")
        knee = hip + _down(thigh) * plan.thigh * build.legs * scale[0]
        j[f"hip_{side}"], j[f"knee_{side}"] = hip, knee
        j[f"ankle_{side}"] = knee + _down(shin) * plan.shin * build.legs * scale[1]
    for side, sign in SIDES.items():
        reach = plan.shoulder_half * build.shoulders * narrow * sign
        shoulder = j["chest"] + shoulder_axis * reach - _up(pose.chest) * plan.shoulder_drop
        upper, fore = getattr(pose, f"arm_{side}")
        scale = getattr(pose, f"arm_{side}_scale")
        target = getattr(pose, f"reach_{side}")
        if target is not None:
            # "Away from the body" is +x for the right arm and -x for the left.
            upper, fore = solve_arm(shoulder, reach_point(target, sign, plan, j), sign,
                                    getattr(pose, f"elbow_{side}"), scale, plan)
        j[f"arm_angles_{side}"] = (upper, fore)
        elbow = shoulder + _down(upper) * plan.upper_arm * scale[0]
        j[f"shoulder_{side}"], j[f"elbow_{side}"] = shoulder, elbow
        j[f"wrist_{side}"] = elbow + _down(fore) * plan.forearm * scale[1]
    return j
