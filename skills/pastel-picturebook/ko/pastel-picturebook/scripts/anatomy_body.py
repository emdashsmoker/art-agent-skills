"""Body anatomy: a posed female figure, seen from the front or the back, as relief parts.

Units are head units (1.0 = half the face width), measured from the pit of the
neck, x to the screen's right, y down. The figure is about 7.5 head-heights
tall. Every part is a tube around a bone or a centre line, so the silhouette
and the shading both come from the same few numbers. On top of the tubes lie
"swellings": soft bumps for the forms that are flesh rather than bone (breast,
belly, buttock, calf, shoulder blade).

A pose is a set of absolute angles (degrees from straight down; positive swings
the lower end outward, away from the body's midline; above 90 the limb points
up) plus optional foreshortening per bone (1 = in the picture plane, 0.5 =
pointing half toward or away from the viewer).
"""
from dataclasses import dataclass, field

import numpy as np

import relief
from anatomy_hand import build_hand

# Torso centre line: distance down the spine (from the shoulder line) and half-width there.
# The silhouette is an hourglass: ribcage, waist, high hip (pelvic crest), low hip (thigh bone head).
# It starts at the base of the neck and widens to the shoulders, so its own outline is the slope of
# the trapezius. Below the widest hip it narrows into the V of the crotch, between the thighs.
TORSO_LEVELS = np.array([-0.40, -0.05, 0.50, 1.10, 1.75, 2.50, 3.30, 3.90, 4.50, 5.20, 5.80, 6.30, 6.75, 7.05])
TORSO_WIDTHS = np.array([0.60, 1.12, 1.33, 1.28, 1.24, 1.07, 0.93, 1.06, 1.36, 1.64, 1.74, 1.62, 1.05, 0.40])
# How strongly each body-shape multiplier acts at each torso level.
SHAPE_WEIGHTS = {
    "shoulders": np.array([0.3, 1.0, 0.9, 0.6, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    "waist": np.array([0.0, 0.0, 0.0, 0.0, 0.2, 0.7, 1.0, 0.7, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0]),
    "hips": np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.8, 1.0, 1.0, 1.0, 0.6, 0.0]),
}
# Named heights along the spine, same measure as TORSO_LEVELS.
SHOULDER_DROP, BUST_LEVEL, WAIST_LEVEL, NAVEL_LEVEL, HIP_LEVEL, CROTCH_LEVEL = 0.30, 1.65, 3.30, 3.95, 5.45, 6.50
SHOULDER_HALF, HIP_HALF = 1.40, 0.86
# The arm bone starts this far below the shoulder line, so the deltoid's top meets the shoulder slope.
ARM_ROOT_LEVEL = 0.46
# The spine is traced from this level (above the shoulder line, into the neck) downward.
SPINE_TOP = -0.60
NECK_HALF = 0.43
# Fillet size (head units) where body parts flow into each other.
BLEND = 0.35
# Height (head units) at which a breast or buttock counts as solid at its edge.
ROUND_EDGE = 0.03
# Bone lengths.
UPPER_ARM, FOREARM, HAND = 3.35, 2.80, 1.80
THIGH, SHIN = 5.45, 4.70
# Half-widths along each bone, root to end (outer side, inner side where they differ).
UPPER_ARM_WIDTHS = np.array([0.52, 0.50, 0.44, 0.39, 0.35])
FOREARM_WIDTHS = np.array([0.35, 0.39, 0.365, 0.31, 0.265])
THIGH_OUTER = np.array([0.88, 0.93, 0.87, 0.73, 0.58, 0.49])
THIGH_INNER = np.array([0.86, 0.90, 0.80, 0.64, 0.50, 0.45])
SHIN_OUTER = np.array([0.47, 0.56, 0.55, 0.42, 0.31, 0.27])
SHIN_INNER = np.array([0.45, 0.50, 0.52, 0.40, 0.29, 0.26])
# Cross-sections: a torso is a flattened oval, limbs are nearly round.
TORSO_ROUNDNESS, LIMB_ROUNDNESS = 0.46, 0.88

# Foot seen from the front: the instep runs toward the viewer, so it shows short and widening.
FOOT_FRONT_LENGTH = 0.86
FOOT_FRONT_WIDTHS = np.array([0.25, 0.31, 0.39, 0.41])
# Toes, big toe first: (offset across the foot, + = toward the other foot; radius; reach past the ball).
TOES = ((0.27, 0.115, 0.12), (0.07, 0.085, 0.16), (-0.09, 0.078, 0.13), (-0.23, 0.070, 0.09), (-0.35, 0.062, 0.04))
# Foot seen from behind: the heel, with the forefoot hidden in front of it.
HEEL_LENGTH, HEEL_WIDTHS = 0.50, np.array([0.23, 0.27, 0.30])
# A closed shoe hides the toes: one tapering form.
SHOE_LENGTH, SHOE_WIDTHS = 1.15, np.array([0.25, 0.32, 0.38, 0.24])

# Swellings: (level down the spine, offset from the spine, radius x, radius y, depth, softness).
# An offset other than 0 puts one on each side.
FRONT_SWELLINGS = {
    "ribs": (2.55, 0.55, 0.55, 0.50, 0.05, 2.0),
    "belly": (4.65, 0.0, 0.80, 0.62, 0.11, 2.0),
    "hip_bone": (4.55, 1.02, 0.26, 0.20, 0.06, 2.0),
    "mound": (6.00, 0.0, 0.42, 0.36, 0.07, 2.0),
}
BACK_SWELLINGS = {
    "shoulder_blade": (0.95, 0.72, 0.50, 0.62, 0.10, 2.0),
    "loin": (3.60, 0.50, 0.34, 0.80, 0.06, 2.0),
    "dimple": (4.72, 0.42, 0.12, 0.10, -0.04, 2.0),
}
# Breast and buttock share one shape: a swelling that rises gently from above and turns under sharply below.
# aside = offset from the spine, drop = below the reference level, rise = how much longer the upper slope is.
BREAST = {"level": BUST_LEVEL, "aside": 0.68, "drop": 0.40, "radius_x": 0.72, "radius_y": 0.64, "rise": 1.9, "fall": 0.80,
          "widen": 0.55, "depth": 0.56}
BUTTOCK = {"level": HIP_LEVEL, "aside": 0.76, "drop": 0.28, "radius_x": 0.86, "radius_y": 0.88, "rise": 1.7, "fall": 0.86,
           "widen": 0.25, "depth": 0.62}
# Depth of the groove along the spine in the back view.
SPINE_FURROW = (0.12, 0.07)   # half-width, depth
# Kneecap (front) and calf muscle (back): (radius x, radius y, depth).
KNEECAP = (0.30, 0.34, 0.07)
# How much larger the near end of a limb pointing straight at the viewer looks (fake perspective).
NEAR_SWELL = 0.45
LOWER_LEG_SHARE = 0.5
# Raising an arm past RAISE_FROM degrees lifts the shoulder joint by up to RAISE_UP and draws it in by RAISE_IN (head units).
RAISE_FROM, RAISE_SPAN, RAISE_UP, RAISE_IN = 90.0, 60.0, 0.45, 0.25
FOOT_SHARE = 0.25
SEATED_THIGH_ROUNDNESS = 0.6
# A thigh counts as seated (lap light, lap folds, trousers over a lap) once it comes toward the viewer by this share of its length.
SEATED_SHARE = 0.5
# Trailing foot of a stride, heel lifted: its length as seen from the front.
TIPTOE_LENGTH = 0.55
CALF = (0.34, 0.95, 0.12)

# ------------------------------------------------------------ body builds
# Everything that differs between a woman's and a man's body, in one table each. Code reads
# these through `build[...]`; the module constants above are the female values.
FEMALE = {
    "TORSO_WIDTHS": TORSO_WIDTHS, "SHOULDER_HALF": SHOULDER_HALF, "HIP_HALF": HIP_HALF, "NECK_HALF": NECK_HALF,
    "UPPER_ARM": UPPER_ARM, "FOREARM": FOREARM, "HAND": HAND, "THIGH": THIGH, "SHIN": SHIN,
    "UPPER_ARM_WIDTHS": UPPER_ARM_WIDTHS, "FOREARM_WIDTHS": FOREARM_WIDTHS,
    "THIGH_OUTER": THIGH_OUTER, "THIGH_INNER": THIGH_INNER, "SHIN_OUTER": SHIN_OUTER, "SHIN_INNER": SHIN_INNER,
    "FRONT_SWELLINGS": FRONT_SWELLINGS, "BACK_SWELLINGS": BACK_SWELLINGS,
    "FRONT_ROUND": BREAST, "BACK_ROUND": BUTTOCK, "ROUND_JOINS_SILHOUETTE": True,
    "TORSO_ROUNDNESS": TORSO_ROUNDNESS, "FOOT_SCALE": 1.0, "HAND_WIDTH": 1.0, "CALF": CALF, "ARM_ROOT_LEVEL": ARM_ROOT_LEVEL,
}
# A man: wide shoulders and chest over a narrow waist and hips (the V), thicker neck and limbs,
# chest muscles in place of breasts, a ridged abdomen, a muscular back.
MALE = {
    **FEMALE,
    "TORSO_WIDTHS": np.array([0.80, 1.48, 1.74, 1.72, 1.62, 1.44, 1.32, 1.28, 1.28, 1.34, 1.36, 1.28, 0.95, 0.42]),
    "SHOULDER_HALF": 1.80, "HIP_HALF": 0.74, "NECK_HALF": 0.58, "ARM_ROOT_LEVEL": 0.66,
    "UPPER_ARM": 3.45, "FOREARM": 2.90, "HAND": 1.95, "THIGH": 5.55, "SHIN": 4.85,
    "UPPER_ARM_WIDTHS": np.array([0.70, 0.69, 0.60, 0.51, 0.45]),
    "FOREARM_WIDTHS": np.array([0.46, 0.53, 0.49, 0.39, 0.32]),
    "THIGH_OUTER": np.array([0.76, 0.88, 0.88, 0.76, 0.60, 0.52]),
    "THIGH_INNER": np.array([0.74, 0.82, 0.76, 0.64, 0.53, 0.48]),
    "SHIN_OUTER": np.array([0.52, 0.64, 0.62, 0.46, 0.35, 0.31]),
    "SHIN_INNER": np.array([0.50, 0.56, 0.58, 0.44, 0.33, 0.30]),
    "FRONT_SWELLINGS": {
        "abs_upper": (2.85, 0.27, 0.30, 0.34, 0.035, 2.5),
        "abs_middle": (3.50, 0.27, 0.30, 0.34, 0.035, 2.5),
        "abs_lower": (4.15, 0.26, 0.29, 0.36, 0.032, 2.5),
        "oblique": (3.95, 1.05, 0.30, 0.70, 0.07, 2.0),
        "serratus": (2.30, 1.22, 0.22, 0.40, 0.05, 2.0),
        "deltoid_front": (0.55, 1.50, 0.40, 0.55, 0.05, 2.0),
    },
    "BACK_SWELLINGS": {
        "trapezius": (0.10, 0.0, 1.00, 0.70, 0.12, 2.0),
        "shoulder_blade": (1.05, 0.82, 0.55, 0.70, 0.12, 2.0),
        "lat": (2.60, 1.12, 0.45, 1.20, 0.12, 2.0),
        "loin": (3.80, 0.42, 0.30, 0.95, 0.09, 2.0),
        "dimple": (4.85, 0.40, 0.12, 0.10, -0.04, 2.0),
    },
    # Chest muscle: wide, shallow, ending in a crisp lower edge.
    "FRONT_ROUND": {"level": 1.05, "aside": 0.82, "drop": 0.22, "radius_x": 0.82, "radius_y": 0.62, "rise": 1.6, "fall": 0.52,
                    "widen": 0.20, "depth": 0.18, "tilt": 12.0},
    "BACK_ROUND": {"level": HIP_LEVEL, "aside": 0.66, "drop": 0.38, "radius_x": 0.78, "radius_y": 0.80, "rise": 1.6, "fall": 0.80,
                   "widen": 0.15, "depth": 0.46},
    "ROUND_JOINS_SILHOUETTE": False,
    "TORSO_ROUNDNESS": 0.50, "FOOT_SCALE": 1.12, "HAND_WIDTH": 1.15, "CALF": (0.42, 1.00, 0.16),
}
BUILDS = {"female": FEMALE, "male": MALE}

DEFAULT_POSE = {
    "shoulder_tilt": 3.0, "pelvis_tilt": -6.0,
    "arm_left": {"upper": 8.0, "fore": 4.0, "hand": 2.0},
    "arm_right": {"upper": 10.0, "fore": 6.0, "hand": 4.0},
    "leg_left": {"thigh": 1.0, "shin": -1.0, "foot": 14.0},
    "leg_right": {"thigh": 7.0, "shin": -9.0, "foot": 24.0},
    "hand_left": "relaxed", "hand_right": "relaxed",
}
SIDES = ((-1, "left"), (1, "right"))


def heading(angle_deg):
    """Unit vector for a bone hanging at `angle_deg` from straight down (positive = toward +x)."""
    turn = np.deg2rad(angle_deg)
    return np.array([np.sin(turn), np.cos(turn)])


@dataclass
class Body:
    """A posed body in pixels: relief parts by name, plus landmarks for details and clothing."""
    unit: float
    view: str = "front"
    sex: str = "female"
    parts: dict = field(default_factory=dict)      # name -> relief.Part
    hands: dict = field(default_factory=dict)      # "left"/"right" -> anatomy_hand.Hand
    marks: dict = field(default_factory=dict)      # landmark name -> (x, y) px
    spine: np.ndarray = None                       # torso centre line (N, 2) px
    spine_widths: np.ndarray = None                # half-width (px) at each spine point
    spine_levels: np.ndarray = None                # distance down the spine (head units) at each point
    swell: np.ndarray = None                       # height (px) of all swellings, to add onto the fused trunk
    reach: dict = field(default_factory=dict)      # "leg_left" etc. -> depth (px) each bone gains toward the viewer
    arm_order: tuple = ("left", "right")           # arms laid on the body in this order: the last lies on top
    turn: float = 0.0                              # body turned this many degrees (3/4 view); + turns the front to the screen's right
    far: str = None                                # with a turn: the side ("left"/"right") that moves away from the viewer
    spine_half: np.ndarray = None                  # with a turn: the torso's own half-widths (px) before projection
    roundness: float = TORSO_ROUNDNESS             # torso depth as a share of its half-width
    posed: tuple = ()                              # arms placed by a reach or raised in front of the face
    behind_clothes: tuple = ()                     # arms swung behind the body: the clothes cover their hands
    seated: tuple = ()                             # legs whose thighs come well toward the viewer (sitting facing us)
    tiptoe: tuple = ()                             # trailing legs of a stride, heel up (their outline stays behind)


class Skeleton:
    """Turns a pose into joint positions in head units (origin = pit of the neck)."""

    def __init__(self, pose, hip_scale=1.0, leg_scale=1.0, build=FEMALE, widths=None):
        self.pose = pose
        self.hip_scale = hip_scale
        self.leg_scale = leg_scale
        self.build = build
        # A turned body (3/4 view): points in the body's middle plane squeeze toward the spine by cos(turn);
        # points on its front surface also slide toward the turn by their depth times sin(turn).
        self.turn = float(pose.get("turn", 0.0))
        self.cos, self.sin = np.cos(np.deg2rad(self.turn)), np.sin(np.deg2rad(self.turn))
        self.widths = build["TORSO_WIDTHS"] if widths is None else widths
        top_turn, low_turn = pose["shoulder_tilt"], pose["pelvis_tilt"]
        self.shoulder_line = np.array([0.0, SHOULDER_DROP])
        # The spine bends from the shoulders' tilt to the pelvis' tilt: an S or C curve, as in contrapposto.
        levels = np.linspace(SPINE_TOP, TORSO_LEVELS[-1], 28)
        turns = top_turn + (low_turn - top_turn) * np.clip(levels / HIP_LEVEL, 0, 1) ** 1.2
        steps = np.diff(levels, prepend=SPINE_TOP)[:, None] * np.array([heading(turn) for turn in turns])
        self.spine = self.shoulder_line + SPINE_TOP * heading(top_turn) + np.cumsum(steps, axis=0)
        self.levels = levels
        self.turns = turns

    def on_spine(self, level, aside=0.0):
        """Point at `level` down the spine, shifted `aside` head units toward the screen's right."""
        index = np.interp(level, self.levels, np.arange(len(self.levels)))
        low = int(np.floor(index))
        high = min(low + 1, len(self.levels) - 1)
        point = self.spine[low] + (self.spine[high] - self.spine[low]) * (index - low)
        turn = np.deg2rad(np.interp(level, self.levels, self.turns))
        return point + aside * np.array([np.cos(turn), -np.sin(turn)])

    def flat(self, points):
        """Points of the body's middle plane (joints, the spine) as seen with the body turned."""
        points = np.array(points, np.float64)
        if self.turn:
            points[..., 0] = points[..., 0] * self.cos
        return points

    def unflat(self, point):
        """Inverse of `flat` for one point (a reach target seen in the picture)."""
        point = np.array(point, np.float64)
        if self.turn:
            point[0] = point[0] / self.cos
        return point

    def surface(self, level, aside=0.0, sign=1.0):
        """A point on the torso's front (sign +1) or back (-1) surface, `aside` head units off the middle, as seen."""
        point = self.on_spine(level, aside)
        if not self.turn:
            return point
        half = max(float(np.interp(level, TORSO_LEVELS, self.widths)), 1e-3)
        depth = self.build["TORSO_ROUNDNESS"] * half * np.sqrt(max(1.0 - (aside / half) ** 2, 0.0))
        return np.array([point[0] * self.cos + sign * depth * self.sin, point[1]])

    def arm(self, side, angles=None):
        """Joints of one arm: shoulder, elbow, wrist. side = -1 (screen left) or +1.

        `angles` overrides the pose's angles for this arm (used while solving a reach).
        """
        angles = angles or self.pose["arm_left" if side < 0 else "arm_right"]
        squeeze = angles.get("foreshorten", (1.0, 1.0))
        build = self.build
        shoulder = self.on_spine(build["ARM_ROOT_LEVEL"], side * build["SHOULDER_HALF"])
        # A raised arm lifts the shoulder girdle: the joint rides up and in as the arm passes the horizontal.
        lift = np.clip((angles["upper"] - RAISE_FROM) / RAISE_SPAN, 0.0, 1.0)
        shoulder = shoulder + lift * np.array([-side * RAISE_IN, -RAISE_UP])
        elbow = shoulder + build["UPPER_ARM"] * squeeze[0] * heading(side * angles["upper"])
        wrist = elbow + build["FOREARM"] * squeeze[1] * heading(side * angles["fore"])
        return shoulder, elbow, wrist

    def leg(self, side):
        """Joints of one leg: hip, knee, ankle."""
        angles = self.pose["leg_left" if side < 0 else "leg_right"]
        squeeze = angles.get("foreshorten", (1.0, 1.0))
        build = self.build
        hip = self.on_spine(HIP_LEVEL, side * build["HIP_HALF"] * self.hip_scale)
        knee = hip + build["THIGH"] * self.leg_scale * squeeze[0] * heading(side * angles["thigh"])
        ankle = knee + build["SHIN"] * self.leg_scale * squeeze[1] * heading(side * angles["shin"])
        return hip, knee, ankle


# ------------------------------------------------------------ reaching
# The point of a hand that touches a target: the middle of the palm, this share of the hand length past the wrist.
GRASP_SHARE = 0.30
# The shoulder rises with the arm, which moves the target relative to it: a few rounds settle both.
REACH_ROUNDS = 4
# An arm stretched toward a target out of reach stops just short of straight, so the elbow keeps a direction.
STRAIGHT_SHARE = 0.995
# Which of the two elbow positions a reach takes: the one farthest out from the body, in toward it, lower or higher.
BENDS = {"out": (0, 1.0), "in": (0, -1.0), "down": (1, 1.0), "up": (1, -1.0)}


def hand_length(build, angles):
    """Hand length (head units) as drawn: a hand reaching toward the viewer is seen along its length, shorter."""
    if angles.get("toward", (0, 0))[1]:
        return build["HAND"] * (0.70 + 0.30 * angles.get("foreshorten", (1.0, 1.0))[1])
    return build["HAND"]


def angle_of(vector, side):
    """Bone angle (degrees, the pose's convention for this side) of a direction in head units."""
    return side * np.degrees(np.arctan2(vector[0], vector[1]))


def elbow_for(shoulder, wrist, upper, fore, side, bend):
    """Elbow of a two-bone arm from shoulder to wrist; `bend` picks one of the two solutions (see BENDS)."""
    span = wrist - shoulder
    distance = np.clip(np.linalg.norm(span), abs(upper - fore) + 1e-3, (upper + fore) * STRAIGHT_SHARE)
    along = span / max(np.linalg.norm(span), 1e-6)
    # Law of cosines: how far along the span the elbow sits, and how far off it.
    reach = (upper ** 2 - fore ** 2 + distance ** 2) / (2 * distance)
    off = np.sqrt(max(upper ** 2 - reach ** 2, 0.0))
    normal = np.array([-along[1], along[0]])
    candidates = [shoulder + along * reach + normal * off, shoulder + along * reach - normal * off]
    axis, sign = BENDS[bend]
    # "out" and "in" are measured across the body: the side's own direction is outward.
    score = [sign * (point[axis] * (side if axis == 0 else 1.0)) for point in candidates]
    return candidates[int(np.argmax(score))], shoulder + along * distance


def solve_arm(bones, side, angles, target):
    """Arm angles that put the middle of the palm on `target` (head units from the neck pit).

    Why: touching something (a partner's hand, a shoulder, one's own chin) by hand-tuned angles
    takes many renders; solving the two-bone arm puts the hand there in one. The wrist stays
    straight unless the arm gives `wrist` (degrees, added to the forearm's angle).
    """
    solved = {key: value for key, value in angles.items() if key != "reach"}
    solved.setdefault("upper", 10.0)
    solved.setdefault("fore", 6.0)
    # A given "hand" angle is kept as the hand's own direction (a hand draped over a shoulder points down).
    fixed_hand = angles.get("hand")
    squeeze = solved.get("foreshorten", (1.0, 1.0))
    upper, fore = bones.build["UPPER_ARM"] * squeeze[0], bones.build["FOREARM"] * squeeze[1]
    grasp = GRASP_SHARE * hand_length(bones.build, solved)
    target = bones.unflat(target)
    for _ in range(REACH_ROUNDS):
        shoulder = bones.arm(side, solved)[0]
        hand_angle = fixed_hand if fixed_hand is not None else solved["fore"] + solved.get("wrist", 0.0)
        wrist = np.asarray(target, np.float64) - grasp * heading(side * hand_angle)
        if solved.get("bend") == "straight":
            # A straight arm reaching less far than its length points partly toward the viewer: both bones shorten.
            span = wrist - shoulder
            share = min(np.linalg.norm(span) / (upper + fore), 1.0)
            solved["foreshorten"] = [squeeze[0] * share, squeeze[1] * share]
            elbow, wrist = shoulder + span * upper / (upper + fore) * min(1.0, (upper + fore) / max(np.linalg.norm(span), 1e-6)), wrist
        else:
            elbow, wrist = elbow_for(shoulder, wrist, upper, fore, side, solved.get("bend", "out"))
        # An arm raised past straight up stays above 90 degrees (not -180): the shoulder lift reads it that way.
        solved["upper"] = (angle_of(elbow - shoulder, side) + 90.0) % 360.0 - 90.0
        solved["fore"] = angle_of(wrist - elbow, side)
    solved["hand"] = fixed_hand if fixed_hand is not None else solved["fore"] + solved.get("wrist", 0.0)
    return solved


def joint_marks(pose, shape=None, sex="female"):
    """Joints of a pose (head units from the neck pit), for reaches aimed at one's own body.

    Arms whose reach is already a point (head units) are solved first, so one hand can aim at the other arm.
    """
    pose = {**DEFAULT_POSE, **pose}
    shape = shape or {}
    bones = Skeleton(pose, shape.get("hips", 1.0), shape.get("legs", 1.0), BUILDS[sex])
    for side, name in SIDES:
        reach = pose[f"arm_{name}"].get("reach")
        if reach is not None and not isinstance(reach, dict):
            pose[f"arm_{name}"] = solve_arm(bones, side, pose[f"arm_{name}"], reach)
        elif reach is not None:
            # Not placed yet: stand in with the resting arm.
            pose[f"arm_{name}"] = {**DEFAULT_POSE[f"arm_{name}"], **{key: value for key, value in pose[f"arm_{name}"].items() if key != "reach"}}
    marks = {}
    for side, name in SIDES:
        angles = pose[f"arm_{name}"]
        for joint, point in zip(("shoulder", "elbow", "wrist"), bones.arm(side)):
            marks[f"{joint}_{name}"] = point
        hand_angle = angles.get("hand", angles.get("fore", 0.0))
        marks[f"hand_{name}"] = marks[f"wrist_{name}"] + GRASP_SHARE * hand_length(BUILDS[sex], angles) * heading(side * hand_angle)
        for joint, point in zip(("hip", "knee", "ankle"), bones.leg(side)):
            marks[f"{joint}_{name}"] = point
    for label, level in (("pit", -0.30), ("bust", BUST_LEVEL), ("waist", WAIST_LEVEL), ("navel", NAVEL_LEVEL), ("hips", HIP_LEVEL)):
        marks[label] = bones.on_spine(level)
    return marks


def teardrop(size, center, unit, form, tilt_deg=0.0):
    """Height of a breast or buttock: a long gentle slope above, a short full turn below.

    Above the centre the form spreads `rise` times its radius and widens as it
    climbs (it merges into the chest or the lower back); below, it turns under
    within `fall` times its radius, which gives the short crescent of shadow.
    """
    rows, cols = np.mgrid[0:size[0], 0:size[1]].astype(np.float32)
    turn = np.deg2rad(tilt_deg)
    dx, dy = cols - center[0], rows - center[1]
    # `tilt_deg` turns the form, so its lower edge can rise toward the armpit (a chest muscle).
    dx, dy = dx * np.cos(turn) + dy * np.sin(turn), -dx * np.sin(turn) + dy * np.cos(turn)
    down = dy / (form["radius_y"] * unit)
    above = down < 0
    widen = np.where(above, 1.0 + form["widen"] * np.clip(-down / form["rise"], 0, 1), 1.0)
    across = dx / (form["radius_x"] * unit * widen)
    down = np.where(above, down / form["rise"], down / form["fall"])
    inside = np.clip(1.0 - across ** 2 - down ** 2, 0.0, None)
    # Below the centre the surface stays full until close to the edge, then turns: a lower power keeps it round.
    power = np.where(above, 1.6, 0.75)
    return (form["depth"] * unit * inside ** power).astype(np.float32)


def torso_widths(shape, build=FEMALE):
    """Torso half-widths after applying the body-shape multipliers (shoulders, waist, hips)."""
    widths = build["TORSO_WIDTHS"].copy()
    for name, weight in SHAPE_WEIGHTS.items():
        widths = widths * (1.0 + (shape.get(name, 1.0) - 1.0) * weight)
    return widths


def foot_front(size, ankle, unit, side, turn_deg, length=1.0):
    """Bare foot seen from the front: instep widening to the ball, then a row of toes.

    `length` below 1 shortens the foot as seen: a heel lifted off the ground points the foot down and away.
    """
    forward = heading(side * turn_deg) * np.array([1.0, 0.80]) * length
    ball = ankle + FOOT_FRONT_LENGTH * unit * forward
    across = np.array([forward[1], -forward[0]]) / max(np.linalg.norm(forward), 1e-6)
    parts = [relief.tube(size, np.linspace(ankle, ball, 4), FOOT_FRONT_WIDTHS * unit, roundness=0.72)]
    # `across` points to the screen's right, so the other foot lies along -side.
    for offset, radius, reach in TOES:
        center = ball - side * across * offset * unit + forward * reach * unit
        parts.append(relief.ellipsoid(size, center, radius * unit, radius * 1.25 * unit))
    return relief.union(parts)


def foot_back(size, ankle, unit, side, turn_deg):
    """Foot seen from behind: the heel under the ankle."""
    down = heading(side * turn_deg * 0.3)
    return relief.tube(size, np.linspace(ankle, ankle + HEEL_LENGTH * unit * down, 3), HEEL_WIDTHS * unit, roundness=0.8)


def shoe(size, ankle, unit, side, turn_deg, length=1.0):
    """Closed shoe: one tapering form from the ankle to the toe (`length` as in foot_front)."""
    toe = ankle + SHOE_LENGTH * unit * heading(side * turn_deg) * np.array([1.0, 0.78]) * length
    return relief.tube(size, np.linspace(ankle, toe, 4), SHOE_WIDTHS * unit, roundness=0.7)


def swellings(size, bones, px, unit, view, shape, build=FEMALE, surface_px=None):
    """Every soft form of the trunk for this view, as height fields (pixels).

    `surface_px(level, aside)` places them on a turned body's surface (default: on the spine's plane).
    Returns (all swellings, the breasts or buttocks alone).
    """
    place = surface_px or (lambda level, aside: px(bones.on_spine(level, aside))[0])
    squeeze = bones.cos if bones.turn else 1.0
    total = np.zeros(size, np.float32)
    table = build["FRONT_SWELLINGS"] if view == "front" else build["BACK_SWELLINGS"]
    for level, aside, radius_x, radius_y, depth, softness in table.values():
        for sign in ((0,) if aside == 0 else (-1, 1)):
            center = place(level, sign * aside)
            total += relief.bump(size, center, radius_x * squeeze * unit, radius_y * unit, depth * unit, softness=softness)
    form = dict(build["FRONT_ROUND"]) if view == "front" else dict(build["BACK_ROUND"])
    if bones.turn:
        form["radius_x"] = form["radius_x"] * squeeze
    scale = shape.get("bust", 1.0) if view == "front" else shape.get("hips", 1.0)
    rounds = np.zeros(size, np.float32)
    for sign in (-1, 1):
        center = place(form["level"] + form["drop"], sign * form["aside"] * (1.0 if view == "front" else scale))
        rounds += teardrop(size, center, unit * scale, form, -sign * form.get("tilt", 0.0))
    total += rounds
    if view == "back":
        furrow = relief.tube(size, px([bones.on_spine(level) for level in np.linspace(0.1, 4.7, 10)]),
                             SPINE_FURROW[0] * unit, roundness=1.0)
        total -= furrow.height / max(SPINE_FURROW[0], 1e-6) * SPINE_FURROW[1]
    return total, rounds


def toward_viewer(angles, lengths, unit):
    """How far (pixels) each bone of a limb comes toward the viewer.

    A bone shortened by `foreshorten` points out of the picture; `toward` says which way
    (1 = toward the viewer, -1 = away, 0 = leave it flat). Without `toward` nothing moves,
    so a slightly shortened arm keeps its old look.
    """
    squeeze = angles.get("foreshorten", (1.0, 1.0))
    toward = angles.get("toward", (0.0, 0.0))
    return [sign * length * np.sqrt(max(1.0 - short ** 2, 0.0)) * unit for sign, length, short in zip(toward, lengths, squeeze)]


def nearer_end(angles, bone, count):
    """Width multipliers along a bone that points at the viewer: 1 at its far end, larger at its near end."""
    if angles.get("toward", (0, 0))[bone] <= 0:
        return np.ones(count)
    squeeze = angles.get("foreshorten", (1.0, 1.0))[bone]
    return np.linspace(1.0, 1.0 + NEAR_SWELL * (1.0 - squeeze), count)


def limb_depth(along, split, reach):
    """Depth gained along one tube drawn over a whole limb (0 at the root, `split` at the middle joint)."""
    first = np.clip(along / max(split, 1e-6), 0.0, 1.0)
    second = np.clip((along - split) / max(1.0 - split, 1e-6), 0.0, 1.0)
    return (reach[0] * first + reach[1] * second).astype(np.float32)


def bring_forward(bones, reach, ends):
    """Raise a two-bone limb (and what hangs from it) by the depth it gains along its length.

    Why: a seated figure's thighs, or a forearm reaching to the knee, come out of the picture;
    raising them makes them cover what lies behind and turns their top toward the light.
    """
    if not any(reach):
        return
    first, second = bones
    first.height = first.height + (first.along * reach[0] * (first.mask > 0)).astype(np.float32)
    second.height = second.height + ((reach[0] + second.along * reach[1]) * (second.mask > 0)).astype(np.float32)
    for part in ends:
        part.height = part.height + ((reach[0] + reach[1]) * (part.mask > 0)).astype(np.float32)


# A stride seen from the front (walking toward the viewer), at full amount: the leading leg reaches toward us,
# the trailing leg bends back with its heel up; the arms swing against the legs.
STRIDE_LEAD = {"thigh": 2.0, "shin": -1.0, "foot": 10.0, "short": (0.03, 0.0), "toward": [1, 0]}
STRIDE_TRAIL = {"thigh": 4.0, "shin": 2.0, "foot": 14.0, "short": (0.03, 0.09), "tiptoe": True}
STRIDE_ARM_BACK = {"upper": 5.0, "fore": 3.0, "hand": 2.0, "short": (0.10, 0.18), "toward": [-1, -1], "behind_clothes": True}
STRIDE_ARM_FRONT = {"upper": 9.0, "fore": -13.0, "hand": -6.0, "short": (0.10, 0.32), "toward": [1, 1]}


def stride_pose(pose):
    """Legs (and free arms) of a stride toward the viewer from `pose["stride"]`: {"lead": "left" or "right", "amount": 0-1, "arms": true}.

    Why one key: walking seen from the front is mostly depth (one leg toward us, one away), which the
    angles alone cannot show; the stride sets the shortening and its direction for every bone at once.
    Arms placed by a reach keep their own pose.
    """
    stride = pose["stride"]
    amount = float(stride.get("amount", 1.0))
    lead = stride.get("lead", "left")
    trail = "right" if lead == "left" else "left"

    def limb(preset):
        bone = {key: value for key, value in preset.items() if key != "short"}
        bone["foreshorten"] = [1.0 - preset["short"][0] * amount, 1.0 - preset["short"][1] * amount]
        return bone

    pose = dict(pose)
    pose[f"leg_{lead}"], pose[f"leg_{trail}"] = limb(STRIDE_LEAD), limb(STRIDE_TRAIL)
    if stride.get("arms", True):
        # The arm on the leading leg's side swings back, the other forward.
        for side, preset in ((lead, STRIDE_ARM_BACK), (trail, STRIDE_ARM_FRONT)):
            if "reach" not in pose[f"arm_{side}"]:
                pose[f"arm_{side}"] = limb(preset)
    return pose


def build_body(size, pit_px, unit, pose, shape=None, view="front", sex="female"):
    """Construct the posed body as relief parts in pixels.

    shape  multipliers around 1.0 for "shoulders", "bust", "waist", "hips", "thighs", "legs" (leg length)
    view   "front" or "back": same skeleton, different soft forms and feet
    sex    "female" or "male": picks the table of proportions and soft forms (FEMALE, MALE)
    """
    pose = {**DEFAULT_POSE, **pose}
    if pose.get("stride"):
        pose = stride_pose(pose)
    shape = shape or {}
    build = BUILDS[sex]
    widths = torso_widths(shape, build)
    bones = Skeleton(pose, shape.get("hips", 1.0), shape.get("legs", 1.0), build, widths)
    for _, name in SIDES:
        if "reach" in pose[f"arm_{name}"]:
            pose[f"arm_{name}"] = solve_arm(bones, -1 if name == "left" else 1, pose[f"arm_{name}"], pose[f"arm_{name}"]["reach"])
    body = Body(unit=unit, view=view, sex=sex)
    body.posed = tuple(name for _, name in SIDES if "reach" in pose[f"arm_{name}"] or pose[f"arm_{name}"].get("front"))
    body.behind_clothes = tuple(name for _, name in SIDES if pose[f"arm_{name}"].get("behind_clothes"))

    def px(points):
        return np.asarray(pit_px, np.float64) + np.atleast_2d(bones.flat(points)) * unit

    def surface_px(level, aside=0.0):
        """A point on the visible surface of the torso (front, or back seen from behind), in pixels."""
        point = bones.surface(level, aside, 1.0 if view == "front" else -1.0)
        return np.asarray(pit_px, np.float64) + np.asarray(point, np.float64) * unit

    spine = np.array([bones.on_spine(level) for level in TORSO_LEVELS])
    body.spine, body.spine_widths, body.spine_levels = px(spine), widths * unit, TORSO_LEVELS
    if bones.turn:
        # Seen turned, an oval cross-section shows half-width sqrt((w cos)^2 + (depth sin)^2) about the spine.
        body.turn, body.far = bones.turn, ("right" if bones.turn > 0 else "left")
        body.spine_half, body.roundness = widths * unit, build["TORSO_ROUNDNESS"]
        body.spine_widths = np.sqrt((widths * bones.cos) ** 2 + (widths * build["TORSO_ROUNDNESS"] * bones.sin) ** 2) * unit
    torso = relief.tube(size, body.spine, body.spine_widths, roundness=build["TORSO_ROUNDNESS"], cap_start=False)
    neck_top = bones.on_spine(-0.36) + np.array([pose.get("neck_lean", 0.0), -1.45])
    neck = relief.tube(size, px([neck_top, bones.on_spine(-0.60), bones.on_spine(-0.20)]),
                       np.array([-0.03, 0.0, 0.08]) * unit + build["NECK_HALF"] * unit, roundness=LIMB_ROUNDNESS)
    body.parts["torso"] = relief.union([torso, neck], blend=BLEND * unit)
    body.swell, rounds = swellings(size, bones, px, unit, view, shape, build, surface_px if bones.turn else None)
    if build["ROUND_JOINS_SILHOUETTE"]:
        # A breast (or buttock) is wider than the ribcage (or pelvis) under it: its edge joins the silhouette.
        torso_part = body.parts["torso"]
        torso_part.mask = np.maximum(torso_part.mask, np.clip(rounds / (ROUND_EDGE * unit), 0.0, 1.0)).astype(np.float32)

    thigh_scale = shape.get("thighs", 1.0)
    for side, name in SIDES:
        hip, knee, ankle = (px(point)[0] for point in bones.leg(side))
        leg_pose = pose["leg_left" if side < 0 else "leg_right"]
        # A thigh pointing at the viewer looms larger toward its near end, the knee.
        near = nearer_end(leg_pose, 0, 6)
        outer, inner = (build["THIGH_OUTER"], build["THIGH_INNER"]) if side < 0 else (build["THIGH_INNER"], build["THIGH_OUTER"])
        # A thigh resting on a seat spreads: its top is broader and flatter than a standing thigh's.
        roundness = SEATED_THIGH_ROUNDNESS if near[-1] > 1.0 else LIMB_ROUNDNESS
        thigh = relief.tube(size, np.linspace(hip, knee, 6), outer * near * unit * thigh_scale, inner * near * unit * thigh_scale,
                            roundness)
        # The shin and foot hang at the knee's depth: they share part of its enlargement (all of it looks heavy).
        lower = 1.0 + (near[-1] - 1.0) * LOWER_LEG_SHARE
        outer, inner = (build["SHIN_OUTER"], build["SHIN_INNER"]) if side < 0 else (build["SHIN_INNER"], build["SHIN_OUTER"])
        shin = relief.tube(size, np.linspace(knee, ankle, 6), outer * lower * unit, inner * lower * unit, LIMB_ROUNDNESS)
        if view == "front":
            cap = near[-1] ** 2
            thigh.height += relief.bump(size, knee - [0, 0.12 * unit], KNEECAP[0] * cap * unit, KNEECAP[1] * cap * unit,
                                        KNEECAP[2] * cap * unit) * (thigh.mask > 0)
        else:
            belly = knee + (ankle - knee) * 0.28
            calf = build["CALF"]
            shin.height += relief.bump(size, belly, calf[0] * unit, calf[1] * unit, calf[2] * unit) * (shin.mask > 0)
        foot_turn = leg_pose["foot"]
        body.parts[f"thigh_{name}"], body.parts[f"shin_{name}"] = thigh, shin
        # Feet seen toes-first already look broad: they take less of the enlargement than the shins.
        foot_unit = unit * build["FOOT_SCALE"] * (1.0 + (near[-1] - 1.0) * FOOT_SHARE)
        # A trailing foot in a stride has its heel up: it points down and back, seen short from the front.
        length = TIPTOE_LENGTH if leg_pose.get("tiptoe") else 1.0
        if leg_pose.get("tiptoe"):
            body.tiptoe = body.tiptoe + (name,)
        if view == "front":
            body.parts[f"foot_{name}"] = foot_front(size, ankle, foot_unit, side, foot_turn, length)
        else:
            body.parts[f"foot_{name}"] = foot_back(size, ankle, foot_unit, side, foot_turn)
        body.parts[f"shoe_{name}"] = shoe(size, ankle, foot_unit, side, foot_turn, length)
        reach = toward_viewer(leg_pose, (build["THIGH"] * bones.leg_scale, build["SHIN"] * bones.leg_scale), unit)
        if reach[0] > SEATED_SHARE * build["THIGH"] * bones.leg_scale * unit:
            body.seated = body.seated + (name,)
        body.reach[f"leg_{name}"] = reach
        bring_forward([thigh, shin], reach, [body.parts[f"foot_{name}"], body.parts[f"shoe_{name}"]])
        if bones.turn and name != body.far:
            # Turned, the near leg stands in front of the far one where they cross.
            for part in (thigh, shin, body.parts[f"foot_{name}"], body.parts[f"shoe_{name}"]):
                part.height = (part.height + abs(bones.sin) * HIP_HALF * unit * (part.mask > 0)).astype(np.float32)
        body.marks.update({f"hip_{name}": hip, f"knee_{name}": knee, f"ankle_{name}": ankle})

        shoulder, elbow, wrist = (px(point)[0] for point in bones.arm(side))
        body.parts[f"upper_arm_{name}"] = relief.tube(size, np.linspace(shoulder, elbow, 5), build["UPPER_ARM_WIDTHS"] * unit,
                                                      roundness=LIMB_ROUNDNESS)
        body.parts[f"forearm_{name}"] = relief.tube(size, np.linspace(elbow, wrist, 5), build["FOREARM_WIDTHS"] * unit,
                                                    roundness=LIMB_ROUNDNESS)
        angles = pose["arm_left" if side < 0 else "arm_right"]
        hand_turn = 180.0 - side * angles["hand"]
        if bones.turn:
            # The hand follows its own direction as seen on the turned body.
            seen = bones.flat(heading(side * angles["hand"]))
            hand_turn = 180.0 - np.degrees(np.arctan2(seen[0], seen[1]))
        # A hand turned to show its palm (waving, a V sign) uses the palm-side skeleton: the thumb changes side.
        body.hands[name] = build_hand(size, wrist, hand_length(build, angles) * unit, hand_turn, pose[f"hand_{name}"], mirror=side > 0,
                                      forearm=False, view=pose.get(f"hand_{name}_view", "back"), width=build["HAND_WIDTH"])
        reach = toward_viewer(angles, (build["UPPER_ARM"], build["FOREARM"]), unit)
        body.reach[f"arm_{name}"] = reach
        bring_forward([body.parts[f"upper_arm_{name}"], body.parts[f"forearm_{name}"]], reach, [body.hands[name].whole])
        body.marks.update({f"shoulder_{name}": shoulder, f"elbow_{name}": elbow, f"wrist_{name}": wrist})
        front, back = build["FRONT_ROUND"], build["BACK_ROUND"]
        if bones.turn:
            body.marks[f"breast_{name}"] = surface_px(front["level"] + front["drop"], side * front["aside"])
            body.marks[f"buttock_{name}"] = surface_px(back["level"] + back["drop"], side * back["aside"])
            body.marks[f"hip_bone_{name}"] = surface_px(HIP_LEVEL - 1.05, side * 1.02)
            body.marks[f"blade_{name}"] = surface_px(0.95, side * 0.72)
        else:
            body.marks[f"breast_{name}"] = px(bones.on_spine(front["level"] + front["drop"], side * front["aside"]))[0]
            body.marks[f"buttock_{name}"] = px(bones.on_spine(back["level"] + back["drop"], side * back["aside"]))[0]
            body.marks[f"hip_bone_{name}"] = px(bones.on_spine(HIP_LEVEL - 1.05, side * 1.02))[0]
            body.marks[f"blade_{name}"] = px(bones.on_spine(0.95, side * 0.72))[0]

    knees = [body.marks["knee_left"], body.marks["knee_right"]]
    if all(name in body.seated for _, name in SIDES):
        # Seated facing us: the thighs hide the bottom of the trunk; nothing of it may show between the knees.
        rows = np.arange(size[0], dtype=np.float32)[:, None]
        cut = np.clip(min(knee[1] for knee in knees) - rows, 0.0, 1.0)
        torso_part = body.parts["torso"]
        torso_part.mask = (torso_part.mask * cut).astype(np.float32)
    # An arm marked "over" lies on top of the other (folded arms).
    body.arm_order = tuple(sorted(("left", "right"), key=lambda name: bool(pose[f"arm_{name}"].get("over", False))))
    if bones.turn and not any(pose[f"arm_{name}"].get("over") for _, name in SIDES):
        # Turned, the far arm is laid first: the near one lies over it.
        body.arm_order = (body.far, "left" if body.far == "right" else "right")
    for label, level in (("pit", -0.30), ("bust", BUST_LEVEL), ("waist", WAIST_LEVEL), ("navel", NAVEL_LEVEL),
                         ("hips", HIP_LEVEL), ("crotch", CROTCH_LEVEL), ("nape", -0.55), ("sacrum", 4.9)):
        body.marks[label] = surface_px(level) if bones.turn else px(bones.on_spine(level))[0]
    return body


def spine_at(body, level, aside=0.0, surface=True):
    """Point at `level` down the spine, `aside` head units toward the screen's right.

    Levels past the end of the torso continue straight along its last direction
    (used for hems and anything else that hangs below the hips). On a turned body `aside`
    is measured over the front surface (a neckline, buttons, a fly slide toward the turn);
    `surface=False` keeps it a plain offset from the spine (the outline).
    """
    last = len(body.spine) - 1
    index = np.interp(level, body.spine_levels, np.arange(last + 1))
    low = min(int(np.floor(index)), last - 1)
    share = index - low
    along = body.spine[low + 1] - body.spine[low]
    along = along / max(np.linalg.norm(along), 1e-6)
    point = body.spine[low] + (body.spine[low + 1] - body.spine[low]) * share
    point = point + along * max(level - body.spine_levels[-1], 0.0) * body.unit
    if body.turn and surface:
        half = max(float(np.interp(level, body.spine_levels, body.spine_half)) / body.unit, 1e-3)
        depth = body.roundness * half * np.sqrt(max(1.0 - (aside / half) ** 2, 0.0)) * (1.0 if body.view == "front" else -1.0)
        turn = np.deg2rad(body.turn)
        aside = aside * np.cos(turn) + depth * np.sin(turn)
    return point + aside * body.unit * np.array([along[1], -along[0]])


def spine_side(body, level, side, ease=0.0):
    """Point on the torso's outline at `level` down the spine. side = -1 (screen left) or +1."""
    width = np.interp(level, body.spine_levels, body.spine_widths) / body.unit + ease
    return spine_at(body, level, side * width, surface=False)
