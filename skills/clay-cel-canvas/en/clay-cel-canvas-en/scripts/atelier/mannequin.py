"""Mannequin: an adult human body built from solid forms, posed like a figure.

Two physiques are ready: FEMALE (about 1.68 m) and MALE (about 1.80 m), both
eight heads high. A pose says where the pelvis is and which way the pelvis,
chest and head face, then where each hand and foot goes. Elbows and knees are
found by inverse kinematics, so every bone keeps its length whatever the pose;
a target out of reach is pulled in and reported. build() adds the body to a
sculpt.Scene and returns landmarks for painting afterwards (chin, chest marks,
navel, joints). dress() covers chosen body regions with clothing that follows
the body exactly.

World axes: x to the viewer's right, y away from the viewer, z up; metres.
Body frames: local x is the figure's left, local -y its front, local z up the
spine. A frame with no rotation faces the viewer.
"""
from dataclasses import dataclass
from enum import Enum

import numpy as np

from .sculpt import Capsule, Ellipsoid, Offset, RoundBox, Sphere, facing


class Trunk(Enum):
    FEMALE = "female"
    MALE = "male"


@dataclass(frozen=True)
class Physique:
    """Proportions in metres. Positions on the trunk are in the chest or pelvis frame."""
    trunk: Trunk
    head_length: float           # chin to crown
    thigh: float
    shin: float
    upper_arm: float
    forearm: float
    waist_pivot: float           # pelvis origin (between the hip joints) to the chest origin
    hip_joint: tuple
    shoulder_joint: tuple        # low enough that the arm's round top meets the shoulder line
    deltoid: tuple               # centre, then radii
    neck_base: tuple
    neck_length: float
    neck_radii: tuple            # at the base, at the top
    chin: tuple                  # in the head frame, from the neck base
    skull: tuple
    skull_radii: tuple
    arm_radii: tuple             # shoulder, elbow (upper arm), elbow (forearm), forearm belly, wrist
    thigh_radii: tuple           # hip, knee
    shin_radii: tuple            # knee, ankle
    calf_radii: tuple
    hand_scale: float
    foot_scale: float
    chest_tone: float                # radius of the painted chest tone


FEMALE = Physique(
    trunk=Trunk.FEMALE, head_length=0.215, thigh=0.405, shin=0.400, upper_arm=0.280, forearm=0.235,
    waist_pivot=0.19, hip_joint=(0.088, 0.0, -0.005), shoulder_joint=(0.150, 0.012, 0.266),
    deltoid=((0.150, 0.012, 0.262), (0.042, 0.046, 0.056)),
    neck_base=(0.0, 0.020, 0.300), neck_length=0.10, neck_radii=(0.046, 0.037),
    chin=(0.0, -0.050, 0.075), skull=(0.0, 0.035, 0.185), skull_radii=(0.074, 0.090, 0.102),
    arm_radii=(0.044, 0.033, 0.035, 0.032, 0.023), thigh_radii=(0.088, 0.048),
    shin_radii=(0.047, 0.026), calf_radii=(0.042, 0.040, 0.12),
    hand_scale=1.0, foot_scale=1.0, chest_tone=0.017)

MALE = Physique(
    trunk=Trunk.MALE, head_length=0.230, thigh=0.435, shin=0.430, upper_arm=0.300, forearm=0.255,
    waist_pivot=0.20, hip_joint=(0.086, 0.0, -0.005), shoulder_joint=(0.180, 0.012, 0.296),
    deltoid=((0.184, 0.012, 0.292), (0.056, 0.060, 0.068)),
    neck_base=(0.0, 0.020, 0.325), neck_length=0.115, neck_radii=(0.062, 0.054),
    chin=(0.0, -0.052, 0.090), skull=(0.0, 0.035, 0.205), skull_radii=(0.080, 0.096, 0.108),
    arm_radii=(0.052, 0.038, 0.040, 0.041, 0.028), thigh_radii=(0.094, 0.054),
    shin_radii=(0.053, 0.030), calf_radii=(0.051, 0.048, 0.13),
    hand_scale=1.10, foot_scale=1.08, chest_tone=0.0105)

PHYSIQUES = {"female": FEMALE, "male": MALE}

# Finger knuckles along the thumb-side axis, length, root radius (scaled by hand_scale).
FINGERS = ((0.027, 0.075, 0.0088), (0.009, 0.083, 0.0092), (-0.009, 0.077, 0.0086),
           (-0.025, 0.060, 0.0076))
PHALANGES = (0.46, 0.30, 0.24)
FINGER_FLEX = (50.0, 75.0, 45.0)      # degrees each joint bends when curl = 1
FINGER_FAN = 3.5                      # how much the fingers spread from the middle one
THUMB = ((0.042, 0.016), (0.032, 0.0118), (0.027, 0.0106))   # bone length, radius
# Forefoot, in (toward the big toe, forward, up) from the ankle: centre, radii.
# The row of toes is wider than the arch, so the ball of the foot widens to carry
# it; without it the outer toes stick out past the foot and look broken off.
FOREFOOT = ((-0.004, 0.120, -0.052), (0.036, 0.036, 0.018))
FOREFOOT_BLEND = 0.02
# Toes: offset toward the big toe, set-back, length, radius (scaled by foot_scale).
TOES = ((0.021, 0.000, 0.046, 0.0125), (0.000, 0.004, 0.040, 0.0086),
        (-0.014, 0.010, 0.034, 0.0080), (-0.026, 0.018, 0.029, 0.0074),
        (-0.036, 0.027, 0.022, 0.0068))

# Melting: how far joints are rounded.
TORSO_BLEND = 0.06
LIMB_BLEND = 0.035
DIGIT_BLEND = 0.008
KNEE_BLEND = 0.012             # small: a large blend adds volume and swells the knee
KNEE_REACH = 0.14
BREAST_BLEND = 0.055           # wide: the upper slope melts into the chest, the lower curve stays round
GRAVITY_SHIFT = 0.022          # how far breasts settle when the chest is not upright
MUSCLE_BLEND = 0.03            # muscles melt in widely, so they read as swellings and not lumps
PEC_BLEND = 0.022              # narrower: the lower edge of the chest muscle should keep a crease

# Body regions, for dress().
REGIONS = ("neck", "chest", "breast", "abdomen", "pelvis", "shoulder", "upper_arm", "forearm", "hand", "thigh",
           "shin", "foot")
SHIRT = ("chest", "breast", "abdomen", "shoulder", "upper_arm", "forearm")
TROUSERS = ("pelvis", "thigh", "shin")


@dataclass(frozen=True)
class Reach:
    """Where a hand or foot goes.

    target: wrist or ankle position.
    bend: direction the elbow or knee points.
    forward: direction of the fingers or toes.
    back: direction the back of the hand or the top of the foot faces.
    curl: hand 0 flat .. 1 fist; foot 0 flat .. 1 toes fully pointed.
    """
    target: tuple
    bend: tuple
    forward: tuple
    back: tuple
    curl: float = 0.3


@dataclass(frozen=True)
class Pose:
    """pelvis: position between the hip joints. The frames are rotation matrices
    (sculpt.rotation or sculpt.facing) for the pelvis, the chest and the head.
    bust scales the breasts of the female trunk."""
    pelvis: tuple
    pelvis_frame: np.ndarray
    chest_frame: np.ndarray
    head_frame: np.ndarray
    left_hand: Reach
    right_hand: Reach
    left_foot: Reach
    right_foot: Reach
    bust: float = 1.0


def _unit(vector):
    vector = np.asarray(vector, float)
    return vector / np.linalg.norm(vector)


def _bend_toward(direction, toward, degrees):
    """Turn a unit direction toward another by an angle; returns both turned."""
    angle = np.radians(degrees)
    toward = _unit(toward - direction * (toward @ direction))
    return (direction * np.cos(angle) + toward * np.sin(angle),
            toward * np.cos(angle) - direction * np.sin(angle))


def _turned(frame, degrees_about_z, degrees_about_x=0.0):
    """A frame turned about its own vertical axis, then tipped about its side axis."""
    t, x = np.radians(degrees_about_z), np.radians(degrees_about_x)
    about_z = np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])
    about_x = np.array([[1, 0, 0], [0, np.cos(x), -np.sin(x)], [0, np.sin(x), np.cos(x)]])
    return frame @ about_z @ about_x


def two_bone(root, target, first, second, bend):
    """Middle joint and reachable end for a two-bone limb; also how far it fell short."""
    root, target = np.asarray(root, float), np.asarray(target, float)
    offset = target - root
    distance = float(np.linalg.norm(offset))
    direction = offset / max(distance, 1e-9)
    reach = np.clip(distance, abs(first - second) + 1e-4, first + second - 1e-4)
    along = (first * first - second * second + reach * reach) / (2 * reach)
    height = np.sqrt(max(first * first - along * along, 0.0))
    side = _unit(np.asarray(bend, float) - direction * (np.asarray(bend, float) @ direction))
    return root + direction * along + side * height, root + direction * reach, distance - reach


class Body:
    """Builds the forms of one figure into a scene."""

    def __init__(self, scene, physique, group="skin"):
        self.scene, self.p, self.group = scene, physique, group
        self.region, self.side = "chest", 0           # side: +1 left limb, -1 right limb, 0 trunk
        self.marks = {"strain": [], "forms": [], "form_sides": [], "chest_tone": physique.chest_tone}

    def add(self, shape, blend=0.0, anchor=None, reach=None):
        self.scene.add(shape, self.group, blend, anchor, reach)
        self.marks["forms"].append((self.region, shape, blend, anchor, reach))
        self.marks["form_sides"].append(self.side)

    # ---- trunk ---------------------------------------------------------------------
    def torso(self, pose):
        pelvis, p = np.asarray(pose.pelvis, float), pose.pelvis_frame
        chest_origin = pelvis + p @ (0, 0, self.p.waist_pivot)
        c = pose.chest_frame
        between = facing(p[:, 2] + c[:, 2], -(p[:, 1] + c[:, 1]))     # halfway between the two frames
        waist = (pelvis + p @ (0, 0.0, 0.172) + chest_origin) / 2
        if self.p.trunk is Trunk.FEMALE:
            self.female_trunk(pose, pelvis, p, chest_origin, c, waist, between)
        else:
            self.male_trunk(pelvis, p, chest_origin, c, waist, between)
        self.region = "neck"
        self.neck_and_skull(pose, chest_origin, c)
        return pelvis, p, chest_origin, c

    def female_trunk(self, pose, pelvis, p, chest_origin, c, waist, between):
        self.region = "pelvis"
        self.add(Ellipsoid(pelvis + p @ (0, 0.012, 0.035), (0.172, 0.105, 0.115), p))
        self.add(Ellipsoid(pelvis + p @ (0, -0.022, 0.112), (0.118, 0.084, 0.10), p), TORSO_BLEND)
        for side in (-1, 1):
            self.add(Ellipsoid(pelvis + p @ (side * 0.074, 0.064, -0.024), (0.090, 0.078, 0.098), p), 0.04)
            # The flare of the hips below the waist: what gives the figure its hourglass.
            self.add(Ellipsoid(pelvis + p @ (side * 0.122, 0.018, -0.045), (0.074, 0.082, 0.118), p), 0.05)
        self.region = "abdomen"
        self.add(Ellipsoid(waist, (0.102, 0.078, 0.078), between), TORSO_BLEND)
        self.region = "chest"
        self.add(Ellipsoid(chest_origin + c @ (0, 0.008, 0.13), (0.122, 0.088, 0.145), c), TORSO_BLEND)
        self.add(Ellipsoid(chest_origin + c @ (0, 0.006, 0.236), (0.126, 0.080, 0.070), c), 0.05)
        for side in (-1, 1):                          # shoulder girdle, sloping down to the tips
            self.add(Capsule(chest_origin + c @ (0, 0.016, 0.288), 0.046,
                             chest_origin + c @ (side * 0.128, 0.016, 0.270), 0.042), 0.05)
        for side in (-1, 1):                          # slope from the neck to the shoulders
            self.add(Capsule(chest_origin + c @ (side * 0.035, 0.03, 0.312), 0.043,
                             chest_origin + c @ (side * 0.13, 0.02, 0.290), 0.038), 0.04)
            # Collar bones: a faint ridge from the pit of the neck to each shoulder.
            self.add(Capsule(chest_origin + c @ (side * 0.022, -0.046, 0.292), 0.010,
                             chest_origin + c @ (side * 0.135, -0.016, 0.300), 0.009), 0.022)
        self.marks.update(pelvis=pelvis, chest=chest_origin,
                          navel=(pelvis + p @ (0, -0.104, 0.142), p @ (0, -1.0, 0.1)))
        self.breasts(pose, chest_origin, c)

    def breasts(self, pose, chest_origin, c):
        self.region = "breast"                       # its own region, so cups and bras can cover it alone
        settle = np.array([0.0, 0.0, -1.0]) - (-c[:, 2])          # gravity not along the spine
        chest_marks = []
        for side in (-1, 1):
            frame = _turned(c, side * 22, np.degrees(0.12))
            radii = np.array([0.058, 0.047, 0.054]) * pose.bust
            center = chest_origin + c @ (side * 0.082, -0.068, 0.118) + settle * GRAVITY_SHIFT * pose.bust
            self.add(Ellipsoid(center, radii, frame), BREAST_BLEND)
            front = frame @ (0, -1.0, -0.08)
            chest_marks.append((center + front / np.linalg.norm(front) * radii[1] * 0.98, front))
        self.marks["chest_marks"] = chest_marks
        self.marks["chest_tone"] = self.p.chest_tone * pose.bust

    def male_trunk(self, pelvis, p, chest_origin, c, waist, between):
        """Narrow hips, broad rib cage and back, flat chest muscles, a firm belly."""
        self.region = "pelvis"
        self.add(Ellipsoid(pelvis + p @ (0, 0.010, 0.040), (0.150, 0.100, 0.115), p))
        self.add(Ellipsoid(pelvis + p @ (0, -0.020, 0.122), (0.112, 0.082, 0.10), p), TORSO_BLEND)
        for side in (-1, 1):
            self.add(Ellipsoid(pelvis + p @ (side * 0.066, 0.066, -0.020), (0.078, 0.068, 0.088), p), 0.04)
            # The ridge over the hip bone that runs down toward the lower pelvis: the "V" of a fit man.
            self.add(Ellipsoid(pelvis + p @ (side * 0.094, -0.030, 0.108), (0.036, 0.050, 0.060), p), 0.04)
        self.region = "abdomen"
        self.add(Ellipsoid(waist, (0.122, 0.088, 0.085), between), TORSO_BLEND)
        for side in (-1, 1):                           # two columns of the belly muscle
            for z in (0.088, 0.036, -0.016):
                self.add(Ellipsoid(chest_origin + c @ (side * 0.029, -0.074, z), (0.028, 0.013, 0.022), c),
                         0.014)
        self.region = "chest"
        self.add(Ellipsoid(chest_origin + c @ (0, 0.010, 0.14), (0.142, 0.098, 0.165), c), TORSO_BLEND)
        self.add(Ellipsoid(chest_origin + c @ (0, 0.008, 0.252), (0.160, 0.090, 0.080), c), 0.05)
        for side in (-1, 1):
            # The broad back muscles under the arms: they make the torso taper to the waist.
            self.add(Ellipsoid(chest_origin + c @ (side * 0.118, 0.030, 0.170), (0.056, 0.074, 0.120), c), 0.05)
            # Shoulder girdle and trapezius stay below the neck base: set higher, they
            # climb the neck and leave the head sitting on the shoulders.
            self.add(Capsule(chest_origin + c @ (0, 0.020, 0.298), 0.048,
                             chest_origin + c @ (side * 0.155, 0.016, 0.292), 0.046), 0.05)
            self.add(Capsule(chest_origin + c @ (side * 0.042, 0.040, 0.312), 0.044,
                             chest_origin + c @ (side * 0.150, 0.028, 0.298), 0.042), 0.04)
            self.add(Capsule(chest_origin + c @ (side * 0.025, -0.052, 0.322), 0.011,
                             chest_origin + c @ (side * 0.160, -0.016, 0.328), 0.010), 0.022)
        chest_marks = []
        for side in (-1, 1):                           # chest muscles
            frame = _turned(c, side * 14)
            center = chest_origin + c @ (side * 0.066, -0.066, 0.212)
            radii = (0.080, 0.032, 0.060)
            self.add(Ellipsoid(center, radii, frame), PEC_BLEND)
            front = frame @ (0, -1.0, -0.15)
            point = center + frame @ (side * 0.017, -radii[1] * 0.92, -0.020)
            chest_marks.append((point, front / np.linalg.norm(front)))
        self.marks.update(pelvis=pelvis, chest=chest_origin, chest_marks=chest_marks,
                          navel=(pelvis + p @ (0, -0.100, 0.150), p @ (0, -1.0, 0.1)))

    def neck_and_skull(self, pose, chest_origin, c):
        base = chest_origin + c @ self.p.neck_base
        h = pose.head_frame
        bottom, top = self.p.neck_radii
        self.add(Capsule(base, bottom, base + h @ (0, 0.004, self.p.neck_length), top), 0.03, base, 0.08)
        if self.p.trunk is Trunk.MALE:                 # Adam's apple
            self.add(Sphere(base + h @ (0, -0.044, 0.062), 0.011), 0.012, base, 0.12)
        self.marks.update(neck=base, chin=base + h @ self.p.chin, head_up=h[:, 2], head_frame=h,
                          skull=base + h @ self.p.skull)

    # ---- limbs ---------------------------------------------------------------------
    def muscle(self, start, end, at, toward, radii, blend=MUSCLE_BLEND):
        """A long oval muscle lying along a limb, pushed out toward one side."""
        axis = end - start
        center = start + axis * at + toward * radii[0] * 0.35
        self.add(Ellipsoid(center, radii, facing(axis, toward)), blend, center, 0.25)

    def arm(self, side, reach, chest_origin, c):
        p = self.p
        self.region, self.side = "shoulder", side
        shoulder = chest_origin + c @ (side * p.shoulder_joint[0], *p.shoulder_joint[1:])
        # Deltoid: hangs below the shoulder line, so the outline runs smoothly into the arm.
        (dx, dy, dz), radii = p.deltoid
        self.add(Ellipsoid(chest_origin + c @ (side * dx, dy, dz), radii, c), 0.05)
        self.region = "upper_arm"
        elbow, wrist, short = two_bone(shoulder, reach.target, p.upper_arm, p.forearm, reach.bend)
        self._strain("hand", side, short)
        r_shoulder, r_elbow, r_elbow2, r_belly, r_wrist = p.arm_radii
        self.add(Capsule(shoulder, r_shoulder, elbow, r_elbow), LIMB_BLEND, shoulder, 0.12)
        if p.trunk is Trunk.MALE:
            axis = _unit(elbow - shoulder)
            back = _unit(np.asarray(reach.bend, float) - axis * (np.asarray(reach.bend, float) @ axis))
            self.muscle(shoulder, elbow, 0.58, -back, (0.036, 0.034, 0.095))       # biceps
            self.muscle(shoulder, elbow, 0.45, back, (0.038, 0.036, 0.11))         # triceps
        self.marks[f"{'left' if side > 0 else 'right'}_shoulder"] = shoulder
        self.region = "forearm"
        belly = elbow + (wrist - elbow) * 0.35
        self.add(Capsule(elbow, r_elbow2, belly, r_belly), 0.02, elbow, 0.05)
        self.add(Capsule(belly, r_belly, wrist, r_wrist), 0.02)
        self.region = "hand"
        self.hand(side, wrist, reach)
        self.side = 0
        name = "left" if side > 0 else "right"
        self.marks[f"{name}_elbow"], self.marks[f"{name}_wrist"] = elbow, wrist

    def hand(self, side, wrist, reach):
        s = self.p.hand_scale
        back = _unit(reach.back)
        forward = _unit(np.asarray(reach.forward, float) - back * (np.asarray(reach.forward, float) @ back))
        thumb_side = side * np.cross(forward, back)
        frame = np.column_stack([thumb_side, forward, back])
        self.add(RoundBox(wrist + forward * 0.048 * s - back * 0.002 * s,
                          (0.037 * s, 0.047 * s, 0.014 * s), 0.012 * s, frame), 0.02, wrist, 0.04 * s)
        for offset, length, radius in FINGERS:
            knuckle = wrist + forward * 0.093 * s + thumb_side * offset * s
            direction, normal = _unit(forward + thumb_side * offset * FINGER_FAN), back
            start, r = knuckle - direction * 0.008 * s, radius * s
            for bone, flex in zip(PHALANGES, FINGER_FLEX):
                direction, palm_side = _bend_toward(direction, -normal, flex * reach.curl)
                normal = -palm_side
                end = start + direction * length * s * bone
                self.add(Capsule(start, r, end, r * 0.9), DIGIT_BLEND * (2 if bone == PHALANGES[0] else 1),
                         start, 0.02 * s)
                start, r = end, r * 0.9
        base = wrist + forward * 0.022 * s + thumb_side * 0.026 * s - back * 0.012 * s
        direction = _unit(forward * 0.55 + thumb_side * 0.7 - back * 0.45)
        across = -thumb_side - back * 0.5
        start = base
        for (length, radius), flex in zip(THUMB, (8.0, 22.0, 22.0)):
            direction, _ = _bend_toward(direction, across, flex * reach.curl)
            end = start + direction * length * s
            self.add(Capsule(start, radius * s, end, radius * s * 0.92),
                     0.02 if start is base else DIGIT_BLEND, start, (0.05 if start is base else 0.02) * s)
            start = end

    def leg(self, side, reach, pelvis, p):
        q = self.p
        self.region, self.side = "thigh", side
        hip = pelvis + p @ (side * q.hip_joint[0], *q.hip_joint[1:])
        knee, ankle, short = two_bone(hip, reach.target, q.thigh, q.shin, reach.bend)
        self._strain("foot", side, short)
        self.marks[f"{'left' if side > 0 else 'right'}_hip"] = hip
        axis = _unit(ankle - hip)
        front = _unit(np.asarray(reach.bend, float) - axis * (np.asarray(reach.bend, float) @ axis))
        self.add(Capsule(hip, q.thigh_radii[0], knee, q.thigh_radii[1]), TORSO_BLEND, hip, 0.17)
        if q.trunk is Trunk.MALE:                      # front of the thigh, a little to the outside
            outside = _unit(np.cross(front, knee - hip)) * -side
            self.muscle(hip, knee, 0.52, _unit(front + outside * 0.4), (0.062, 0.058, 0.17))
        self.region = "shin"
        # Thigh and shin meet end to end at nearly the same radius, which is already
        # smooth; melting more shapes into the joint would swell it into a ball.
        self.add(Sphere(knee + front * 0.026, 0.020), 0.02, knee, KNEE_REACH)
        # One tapering shin, with the calf muscle as a long oval melted in behind it:
        # two rods meeting at the calf would leave a kink.
        self.add(Capsule(knee, q.shin_radii[0], ankle, q.shin_radii[1]), KNEE_BLEND, knee, KNEE_REACH)
        calf = knee + (ankle - knee) * 0.30 - front * 0.014
        self.add(Ellipsoid(calf, q.calf_radii, facing(ankle - knee, front)), 0.03, calf, 0.22)
        self.region = "foot"
        self.foot(side, ankle, reach)
        name = "left" if side > 0 else "right"
        self.marks[f"{name}_knee"], self.marks[f"{name}_ankle"] = knee, ankle
        self.side = 0

    def foot(self, side, ankle, reach):
        s = self.p.foot_scale
        up = _unit(reach.back)
        forward = _unit(np.asarray(reach.forward, float) - up * (np.asarray(reach.forward, float) @ up))
        forward, down = _bend_toward(forward, -up, 45.0 * reach.curl)     # point the toes down
        up = -down
        medial = -side * np.cross(up, forward)
        for offset in (0.022, -0.022):                # ankle bones
            self.add(Sphere(ankle + medial * offset * s, 0.015 * s), 0.012)
        self.add(Sphere(ankle - up * 0.040 * s - forward * 0.035 * s, 0.030 * s), 0.025, ankle, 0.08 * s)
        self.add(Capsule(ankle - up * 0.035 * s - forward * 0.02 * s, 0.030 * s,
                         ankle - up * 0.055 * s + forward * 0.13 * s + medial * 0.006 * s, 0.027 * s), 0.025)
        self.add(Capsule(ankle, 0.028 * s, ankle - up * 0.030 * s + forward * 0.08 * s, 0.026 * s), 0.03)
        (fm, ff, fu), radii = FOREFOOT
        self.add(Ellipsoid(ankle + (medial * fm + forward * ff + up * fu) * s, tuple(r * s for r in radii),
                           np.column_stack([medial, forward, up])), FOREFOOT_BLEND)
        ball = ankle - up * 0.058 * s + forward * 0.142 * s
        for offset, back, length, radius in TOES:
            start = ball + medial * offset * s - forward * back * s
            middle = start + forward * length * s * 0.55 - up * 0.003 * s
            tip = start + forward * length * s - up * 0.006 * s
            self.add(Capsule(start, radius * s, middle, radius * s * 0.95), DIGIT_BLEND, start, 0.02 * s)
            self.add(Capsule(middle, radius * s * 0.95, tip, radius * s * 0.88), DIGIT_BLEND * 0.6, middle,
                     0.012 * s)

    def _strain(self, limb, side, short):
        if short > 0.01:
            self.marks["strain"].append(f"{'left' if side > 0 else 'right'} {limb} short by {short:.3f} m")


def build(scene, pose, group="skin", physique=FEMALE):
    """Add a posed body to a scene; return its landmarks.

    Landmarks: chin, head_up, head_frame, skull (centre of the skull), neck,
    chest marks [(point, normal) x2], chest tone (radius), navel (point, normal), pelvis,
    pelvis_frame, chest, chest_frame, left/right shoulder, elbow, wrist, hip, knee,
    ankle, and forms (for dress()).
    'strain' lists hands or feet that could not reach their targets.
    """
    body = Body(scene, physique, group)
    pelvis, p, chest_origin, c = body.torso(pose)
    for side, hand, foot in ((1, pose.left_hand, pose.left_foot), (-1, pose.right_hand, pose.right_foot)):
        body.leg(side, foot, pelvis, p)
        body.arm(side, hand, chest_origin, c)
    marks = body.marks
    marks.update(skull_radii=physique.skull_radii, pelvis_frame=p, chest_frame=c,
                 leg_radii=(physique.thigh_radii, physique.shin_radii), arm_radius=physique.arm_radii[0])
    return marks


def dress(scene, marks, group, regions, thickness, smooth=0.0, side=None):
    """Cover body regions with a garment: the same forms grown by `thickness`, so the
    cloth follows every curve of the body and its joints melt the same way.

    smooth adds to every melt: cloth bridges small hollows (between muscles,
    between toes) instead of sinking into them, the way real fabric does.
    side (+1 left, -1 right) takes the limb forms of one side only, so a leg or
    sleeve can be its own group and get its own hem.
    """
    for (region, shape, blend, anchor, reach), form_side in zip(marks["forms"], marks["form_sides"]):
        if region in regions and (side is None or form_side == side):
            scene.add(Offset(shape, thickness), group, blend + smooth, anchor, reach)


def add_skull(scene, marks, group="head"):
    """A plain skull shape where the painted head goes: it hides what is behind the
    head and casts the head's shadow. Paint this group in the hair colour."""
    scene.add(Ellipsoid(marks["skull"], marks["skull_radii"], marks["head_frame"]), group)
