"""Full-body figure: a 2D jointed skeleton fleshed out with tapered tubes.

The skeleton is flat: every bone has a length and a screen angle, and joints are
found by walking the bones from the pelvis outward. Flesh is one tube per bone,
slightly bowed, with separate outer and inner thickness profiles so thighs,
calves and forearms swell where muscles sit and narrow at the joints. Parts that
belong together are merged into one mask and outlined once, which keeps joints
free of stray lines.

Units are head heights. Sides are screen sides: "l" is the viewer's left.
Angles are degrees from straight down, positive toward the screen right.
"""
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.interpolate import PchipInterpolator

from .. import geometry as geo
from .. import shading as sh
from ..color import rgb
from ..styles import ANIME, cast_softness_px, line_color, shade_form
from . import accessories, anatomy, face
from . import hair as hair_rig
from . import hand as hand_rig
from .frame import PortraitSpec, light_on_canvas
from .outfit import CHIN_SHADOW_DROP, PROFILE_CHIN_SHADOW
from .portrait import draw_head_back, draw_head_front, draw_rim_light, prepare_head

# ---- bone lengths (head heights) ------------------------------------------------
NECK = 0.40                  # shoulder line up to the head pivot; a long neck reads elegant
SPINE_UPPER = 1.45           # waist up to the shoulder line
SPINE_LOWER = 0.78           # hip joints up to the waist
THIGH, SHIN, FOOT = 1.95, 1.80, 0.36
UPPER_ARM, FOREARM = 1.36, 1.10
HIP_JOINT = (0.43, 0.08)     # hip joint offset from the pelvis centre: (share of the hip half-width, drop)
SHOULDER_DROP = 0.16         # shoulder joints sit below the shoulder line, so the deltoid tops out level with it
HEAD_PIVOT_Y = 0.92          # same pivot the head rig tilts around
FOOT_LENGTH_3D = 0.74        # true foot length; a front view only shows its short downward part (FOOT)
HEEL_BACK, HEEL_DROP = 0.16, 0.24    # heel behind and below the ankle, seen once the body turns
BEHIND_HEAD_GAP = 0.14       # head heights: gaps narrower than twice this between head, neck and hair hide a raised hand
BEHIND_HEAD_REACH = 0.90     # head heights round the wrist of a raised arm that the head may hide (hand and fingertips)
HAND_HIDDEN_SHARE = 0.5      # a hand hidden past this share gets no finger lines
TURNED_NECK_TOP = 0.18       # head heights the neck of a turned body reaches above the head pivot
HEEL_LIFT = 0.10             # a foot set by its swing: the heel stands this far off the line of the foot
SEATED_SWING = (35.0, 75.0)  # thigh swing (degrees forward) over which a figure counts as sitting
SEAT_DROP = 0.36             # below the pelvis centre, where a seated body rests on the seat (head heights)
GROUND_SOFTNESS = 0.03       # how softly the trunk flattens against what it rests on
VISIBILITY_FADE = 0.35       # radians over which a mark on the trunk fades out as it turns away
FAR_LIMB_ANGLE = 22.0        # degrees of turn past which the far arm hides behind the trunk
VISIBILITY_ROWS, VISIBILITY_COLUMNS = 260, 90    # samples over the front of the trunk for its visibility map

# ---- flesh: half-widths at even stations along each bone, (outer side, inner side), then the bow ----
# Stations run from the upper joint to the lower one. The bow bends the bone outward by that many heads.
THIGH_FLESH = ([0.385, 0.410, 0.392, 0.345, 0.288, 0.232, 0.200], [0.290, 0.305, 0.296, 0.268, 0.228, 0.192, 0.176], 0.030)
SHIN_FLESH = ([0.194, 0.222, 0.240, 0.214, 0.164, 0.124, 0.106], [0.172, 0.208, 0.244, 0.222, 0.156, 0.114, 0.100], 0.022)
FOOT_FLESH = ([0.105, 0.135, 0.158, 0.140], [0.100, 0.130, 0.158, 0.146], 0.0)
UPPER_ARM_FLESH = ([0.176, 0.204, 0.192, 0.170, 0.152, 0.140], [0.168, 0.172, 0.168, 0.154, 0.142, 0.132], 0.012)
FOREARM_FLESH = ([0.140, 0.166, 0.150, 0.122, 0.102, 0.090], [0.132, 0.150, 0.134, 0.110, 0.094, 0.084], 0.016)
NECK_HALF_WIDTH = 0.135
# Side view of each limb: (front, back) half-depths at the same stations, then a forward bow
# (the thigh bows forward, the calf swells back).
LIMB_DEPTH = {
    "thigh": ([0.33, 0.36, 0.35, 0.32, 0.28, 0.23, 0.19], [0.36, 0.34, 0.31, 0.27, 0.23, 0.19, 0.17], 0.03),
    "shin": ([0.14, 0.13, 0.12, 0.11, 0.10, 0.09, 0.09], [0.16, 0.24, 0.26, 0.22, 0.15, 0.11, 0.10], -0.02),
    "foot": ([0.17, 0.17, 0.12, 0.075], [0.11, 0.10, 0.08, 0.065], 0.0),   # the instep rises to the ankle; toes stay round
    "upper_arm": ([0.17, 0.18, 0.17, 0.15, 0.13, 0.12], [0.18, 0.19, 0.18, 0.15, 0.13, 0.12], -0.01),
    "forearm": ([0.14, 0.16, 0.14, 0.11, 0.09, 0.08], [0.13, 0.15, 0.13, 0.10, 0.085, 0.075], 0.01),
}
# A man's thighs run straighter: less flare at the top, the same knee.
MALE_THIGH_FLESH = ([0.330, 0.352, 0.342, 0.312, 0.272, 0.228, 0.202], [0.272, 0.288, 0.282, 0.262, 0.226, 0.192, 0.178], 0.022)

TURN_FAR_SQUEEZE, TURN_NEAR_STRETCH, TURN_CENTER_SHIFT = 0.16, 0.03, 0.07
HIP_SWELL = 0.07             # how far the near hip rounds out when the body is turned
LINE_WIDTH = 0.022           # outline width in head heights
FORM_BEVEL = 0.30            # how deep into a limb its roundness reaches; smaller reads flatter
BIG_FORM_BEVEL = 0.55        # same for the pass that models the whole figure as one mass
BIG_FORM_RAKE = 0.45         # the big-form pass lowers the light toward the picture plane by this factor
BIG_FORM_THRESHOLD = 0.12
BIG_FORM_TINT = (0.80, 0.62, 0.62)   # warm half-shadow laid over the side of the figure away from the light
SHEEN_COLOR = "#fff2e2"      # soft light running along the most lit ridge of each limb
CONTACT_TINT = (0.72, 0.52, 0.55)    # darkening where two limbs press together
CONTACT_FADE = 0.30          # head heights below the trunk over which that darkening fades in
BRIDGE_DEPTH = 0.55          # below the crotch, the shading treats the thighs as one mass over this depth
BRIDGE_HALF_WIDTH = 0.45     # how far either side of the crotch the gap between the thighs is bridged
MELT_RADIUS = 0.035          # fuses trunk and thighs so the hip line has no notch
ATTACH_RADIUS = 0.24         # around a joint where a limb merges into the trunk, its outline is dropped


@dataclass
class BodySpec:
    shoulder: float = 0.56       # half the distance between the shoulder joints
    chest: float = 0.47          # half-width of the ribcage
    waist: float = 0.385
    hip: float = 0.70            # hips about as wide as the shoulders: the hourglass
    bust: float = 1.45           # 0 flat .. 1 small .. 1.45 full .. 1.8 very full
    limb: float = 1.0            # limb thickness multiplier
    legs: float = 0.95           # leg length multiplier; 1.0 gives an 8-head fashion figure
    head: float = 1.08           # head size multiplier; a slightly larger head reads younger and more illustrative
    build: str = "female"        # "female" or "male": picks the surface anatomy and the thigh shape
    arms: float = 1.0            # extra arm thickness on top of `limb`
    neck: float = 1.0            # neck width multiplier


# A lean, athletic man: shoulders well past the hips, a straight waist, heavier arms and neck.
MALE_BODY = BodySpec(build="male", shoulder=0.68, chest=0.56, waist=0.43, hip=0.54, bust=0.0, limb=1.0,
                     arms=1.22, neck=1.32, legs=0.97, head=1.0)


@dataclass
class Pose:
    root: tuple = (0.50, 0.51)       # pelvis centre on the canvas (fractions of width, height)
    unit: float = 0.120              # head height / canvas height; 8 heads tall needs about 0.12 or less
    view: str = "front"              # "front" or "back"
    lean: float = 0.0                # rotation of the whole figure
    pelvis_tilt: float = 0.0         # positive lowers the hip on the screen right
    chest_tilt: float = 0.0          # positive lowers the shoulder on the screen right
    waist_shift: float = 0.0         # sideways slide of the ribcage over the pelvis (heads)
    turn: float = 0.0                # -1..1 body turned toward the screen left / right (narrows the far side)
    arm_l: tuple = (-10.0, 3.0)      # (upper arm, forearm)
    arm_r: tuple = (10.0, -3.0)
    leg_l: tuple = (-3.0, -1.0)      # (thigh, shin)
    leg_r: tuple = (3.0, 1.0)
    foot_l: float = -18.0
    foot_r: float = 18.0
    hand_l: float = None             # hand angle; None continues the forearm
    hand_r: float = None
    head_tilt: float = 0.0
    behind: tuple = ()               # limbs drawn behind the trunk, e.g. ("arm_r",)
    front_leg: str = None            # "leg_l" or "leg_r" when one leg crosses in front of the other
    shorten: dict = field(default_factory=dict)   # bone -> length multiplier, fakes limbs pointing at the viewer
    #   bone names: upper_arm_l, forearm_l, thigh_l, shin_l, foot_l (and _r)
    yaw: float = 0.0                 # degrees the body turns about its vertical axis: +90 shows the front facing screen right
    swing: dict = field(default_factory=dict)     # bone -> degrees swung forward (negative: back), seen from the side
    head_yaw: float = None           # degrees for the head; None follows the body
    pitch: float = 0.0               # degrees the camera looks down on the figure; shows the lap of a seated figure
    ground: float = None             # screen distance (head heights) below the pelvis centre of the seat or bed the
                                     # trunk rests on; flesh past it flattens. None: SEAT_DROP when sitting, else nothing


# Ready-made poses. Weight is on the leg at the screen left in all of them; mirror the signs for the other side.
# The pelvis slides over the standing foot, so the ribcage sits toward the free leg (positive waist_shift):
# the hip on the weight side juts out under a short, creased waist.
POSES = {
    "stand": {},
    "contrapposto": dict(pelvis_tilt=8, chest_tilt=-6, waist_shift=0.048, leg_l=(2, -1), leg_r=(11, -4), foot_r=26,
                         arm_l=(-12, 6), arm_r=(14, -8)),
    "hand_on_hip": dict(pelvis_tilt=9, chest_tilt=-6, waist_shift=0.054, leg_l=(2, -1), leg_r=(12, -4), foot_r=26,
                        arm_l=(-12, 6), arm_r=(40, -46), hand_r=-6),
    "arm_behind_head": dict(pelvis_tilt=9, chest_tilt=-7, waist_shift=0.054, leg_l=(2, -1), leg_r=(11, -3),
                            arm_l=(-152, 62), arm_r=(40, -46), hand_r=-6, behind=("arm_l",), head_tilt=5),
    "arms_up": dict(pelvis_tilt=7, chest_tilt=-4, waist_shift=0.042, leg_l=(2, -1), leg_r=(10, -3),
                    arm_l=(-150, 64), arm_r=(150, -64), behind=("arm_l", "arm_r")),
    "walk": dict(pelvis_tilt=5, chest_tilt=-4, waist_shift=0.024, leg_l=(3, 1), leg_r=(-3, 3), front_leg="leg_r",
                 foot_r=6, foot_l=-20, arm_l=(-18, -6), arm_r=(20, 2), shorten={"shin_l": 0.94}),
    "stance": dict(leg_l=(-7, 1), leg_r=(7, -1), foot_l=-24, foot_r=24, arm_l=(-15, 5), arm_r=(15, -5)),
    # Seen from the side: the near leg strides forward, the far one pushes off behind, the arms swing against them.
    "walk_side": dict(yaw=90, pelvis_tilt=3, chest_tilt=-2, leg_l=(0, 0), leg_r=(0, 0), foot_l=-8, foot_r=8,
                      arm_l=(-4, -2), arm_r=(4, 2),
                      swing={"thigh_l": 20, "shin_l": 4, "thigh_r": -13, "shin_r": -34,
                             "upper_arm_l": -20, "forearm_l": -8, "upper_arm_r": 22, "forearm_r": 46}),
    # Sitting on a chair: thighs level and forward, shins down, forearms resting along the thighs.
    "sit_side": dict(yaw=90, leg_l=(0, 0), leg_r=(0, 0), foot_l=-6, foot_r=6, arm_l=(-4, 0), arm_r=(4, 0),
                     swing={"thigh_l": 88, "thigh_r": 86, "shin_l": 2, "shin_r": -8,          # hands rest on the near knee
                            "upper_arm_l": 16, "upper_arm_r": 12, "forearm_l": 60, "forearm_r": 54}),
    "sit": dict(yaw=35, leg_l=(-2, 0), leg_r=(4, 2), foot_l=-10, foot_r=10, arm_l=(-8, 0), arm_r=(8, 0),
                swing={"thigh_l": 86, "thigh_r": 84, "shin_l": 4, "shin_r": -6,
                       "upper_arm_l": 16, "upper_arm_r": 12, "forearm_l": 70, "forearm_r": 64}),
    "sit_front": dict(pitch=20, leg_l=(-6, -3), leg_r=(6, 3), foot_l=-14, foot_r=14, arm_l=(-14, 8), arm_r=(14, -8),
                      swing={"thigh_l": 86, "thigh_r": 86, "shin_l": 4, "shin_r": 4,
                             "upper_arm_l": 22, "upper_arm_r": 22, "forearm_l": 62, "forearm_r": 62}),
    # Kneeling upright, shins along the floor; and sitting back on the heels (seiza).
    "kneel_side": dict(yaw=90, leg_l=(0, 0), leg_r=(0, 0), arm_l=(-4, 0), arm_r=(4, 0), foot_l=0, foot_r=0,
                       swing={"thigh_l": 10, "thigh_r": 4, "shin_l": -86, "shin_r": -90, "foot_l": -84, "foot_r": -86,
                              "upper_arm_l": 10, "upper_arm_r": 6, "forearm_l": 42, "forearm_r": 36}),
    # Turned toward the viewer the hands hang by the outer thighs: carried forward onto the thighs, the
    # near hand would land over the lower pelvis.
    "kneel": dict(yaw=35, leg_l=(-3, 0), leg_r=(4, 0), arm_l=(-8, 0), arm_r=(8, 0), foot_l=0, foot_r=0,
                  swing={"thigh_l": 10, "thigh_r": 4, "shin_l": -86, "shin_r": -90, "foot_l": -84, "foot_r": -86,
                         "upper_arm_l": 2, "upper_arm_r": 0, "forearm_l": 22, "forearm_r": 18}),
    "seiza": dict(yaw=90, ground=0.52, leg_l=(0, 0), leg_r=(0, 0), arm_l=(-4, 0), arm_r=(4, 0), foot_l=0, foot_r=0,
                  swing={"thigh_l": 80, "thigh_r": 78, "shin_l": -80, "shin_r": -82, "foot_l": -92, "foot_r": -94,
                         "upper_arm_l": 14, "upper_arm_r": 10, "forearm_l": 66, "forearm_r": 60}),
    # Lying: on the back seen from the side (head to the left, one knee raised), and on one side facing the viewer.
    "lie_back": dict(yaw=90, lean=-90, ground=0.36, head_yaw=60, leg_l=(0, 0), leg_r=(0, 0), foot_l=0, foot_r=0,
                     arm_l=(-2, 0), arm_r=(2, 0),
                     # the straight leg and the raised foot rest on the bed: both legs angle slightly toward it
                     swing={"thigh_l": 40, "shin_l": -62, "thigh_r": -4, "shin_r": -2, "foot_l": -6, "foot_r": 60,
                            "upper_arm_l": 4, "forearm_l": 24, "upper_arm_r": -4, "forearm_r": 10}),
    "lie_side": dict(lean=90, ground=0.66, pelvis_tilt=-6, chest_tilt=4, leg_l=(17, 6), leg_r=(4, 2), foot_l=-10,
                     foot_r=-10, arm_l=(-14, 16), arm_r=(176, 2), behind=("arm_r",), head_tilt=-8, front_leg="leg_l",
                     swing={"thigh_l": 22, "shin_l": -6}),
    "back": dict(view="back", pelvis_tilt=8, chest_tilt=-6, waist_shift=0.048, leg_l=(2, -1), leg_r=(11, -4), foot_r=24,
                 arm_l=(-12, 6), arm_r=(16, -10)),
}


def make_pose(name, **overrides):
    """A ready-made pose by name (see POSES), with any Pose field overridden."""
    return Pose(**{**POSES[name], **overrides})


def _direction(angle, swing=0.0):
    """Unit bone direction in 3D: `angle` opens the bone sideways in the picture plane of a front view,
    `swing` (degrees) carries it forward (+z, toward the viewer of a front view) or back."""
    radians, forward = np.radians(angle), np.radians(swing)
    return np.array([np.sin(radians) * np.cos(forward), np.cos(radians) * np.cos(forward), np.sin(forward)])


def _rotate(points, angle):
    """Rotate in the picture plane of a front view (about the z axis); 3D points keep their depth."""
    pts = np.atleast_2d(np.asarray(points, dtype=np.float64))
    flat = geo.transform(pts[:, :2], angle=np.radians(angle))
    return flat if pts.shape[1] == 2 else np.column_stack([flat, pts[:, 2]])


def _as3(points):
    pts = np.atleast_2d(np.asarray(points, dtype=np.float64))
    return pts if pts.shape[1] == 3 else np.column_stack([pts, np.zeros(len(pts))])


class Skeleton:
    """Joint positions in pixels, plus helpers to place points on the chest and pelvis.

    Joints live in 3D figure units (x right, y down, z toward the viewer of a front view). The body
    turns about the vertical axis by pose.yaw and is projected straight onto the picture. At yaw 0
    the projection drops z, so a front view is exactly the flat rig it always was.
    """

    def __init__(self, pose, body, canvas_shape):
        height, width = canvas_shape
        self.pose, self.body = pose, body
        self.unit = pose.unit * height
        self.origin = np.array([pose.root[0] * width, pose.root[1] * height])
        self.yaw = 0.0 if pose.view == "back" else np.radians(pose.yaw)
        self.cos_yaw, self.sin_yaw = np.cos(self.yaw), np.sin(self.yaw)
        self.pitch = np.radians(pose.pitch)
        pelvis = np.zeros(3)
        waist = np.array([pose.waist_shift * 0.5, -SPINE_LOWER, 0.0])
        chest = np.array([pose.waist_shift, -(SPINE_LOWER + SPINE_UPPER), 0.0])
        self._local = {"pelvis": pelvis, "waist": waist, "chest": chest}
        for side, sign in (("l", -1.0), ("r", 1.0)):
            # a thicker arm hangs its joint lower so the top of the arm still meets the shoulder line
            drop = SHOULDER_DROP + UPPER_ARM_FLESH[0][0] * (body.arms * body.limb - 1.0)
            shoulder = chest + _rotate(_as3(self._turned([(sign * body.shoulder, drop)], False)), pose.chest_tilt)[0]
            hip = pelvis + _rotate(_as3(self._turned([(sign * HIP_JOINT[0] * body.hip, HIP_JOINT[1])], False)), pose.pelvis_tilt)[0]
            upper, lower = getattr(pose, f"arm_{side}")
            thigh, shin = getattr(pose, f"leg_{side}")
            hand = getattr(pose, f"hand_{side}")
            elbow = shoulder + _direction(upper, self._swing(f"upper_arm_{side}")) * UPPER_ARM * self._scale(f"upper_arm_{side}")
            wrist = elbow + _direction(lower, self._swing(f"forearm_{side}")) * FOREARM * self._scale(f"forearm_{side}")
            knee = hip + _direction(thigh, self._swing(f"thigh_{side}")) * THIGH * body.legs * self._scale(f"thigh_{side}")
            ankle = knee + _direction(shin, self._swing(f"shin_{side}")) * SHIN * body.legs * self._scale(f"shin_{side}")
            if f"foot_{side}" in pose.swing:           # a foot set by its own swing: pointed, or lying back along the floor
                foot = _direction(getattr(pose, f"foot_{side}"), pose.swing[f"foot_{side}"]) * FOOT_LENGTH_3D
                along = foot / FOOT_LENGTH_3D
                # The heel stands off the sole side of the foot; for a foot pointed back that side faces up.
                sole_side = np.array([0.0, along[2], -along[1]])
                heel = ankle - along * HEEL_BACK + sole_side * HEEL_LIFT
            else:
                foot = _direction(getattr(pose, f"foot_{side}")) * FOOT
                # The foot points at the viewer of a front view, so it reads short there; its true length is in z.
                foot[2] = np.sqrt(max(FOOT_LENGTH_3D ** 2 - FOOT ** 2, 0.0))
                heel = ankle + np.array([0.0, HEEL_DROP * abs(self.sin_yaw), -HEEL_BACK])
            toe = ankle + foot * self._scale(f"foot_{side}")
            self._local.update({f"shoulder_{side}": shoulder, f"elbow_{side}": elbow, f"wrist_{side}": wrist,
                                f"hip_{side}": hip, f"knee_{side}": knee, f"ankle_{side}": ankle, f"toe_{side}": toe,
                                f"heel_{side}": heel})
            self._local[f"hand_{side}"] = wrist + _direction(lower if hand is None else hand,
                                                             self._swing(f"forearm_{side}")) * hand_rig.FIGURE_HAND_LENGTH
        self._local["head_pivot"] = chest + _rotate(_as3([(0.0, -NECK)]), pose.chest_tilt * 0.3)[0]
        self.joints = {name: self.to_pixels(self.project(point))[0] for name, point in self._local.items()}
        self.depth = {name: self.depth_of(point)[0] for name, point in self._local.items()}
        # Drawing order: past FAR_LIMB_ANGLE the far arm goes behind the trunk and the near leg in front.
        self.behind, self.front_leg, self.hidden_arm = tuple(pose.behind), pose.front_leg, None
        near = self.near_side()
        if near and abs(pose.yaw) > FAR_LIMB_ANGLE:
            far = "r" if near == "l" else "l"
            self.hidden_arm = f"arm_{far}"           # behind the trunk because of the turn: clothes leave it alone
            if self.hidden_arm not in self.behind:
                self.behind += (self.hidden_arm,)
            self.front_leg = self.front_leg or f"leg_{near}"
        thigh_swing = np.mean([pose.swing.get(f"thigh_{side}", 0.0) for side in ("l", "r")])
        self.seated = float(sh.smoothstep(SEATED_SWING[0], SEATED_SWING[1], thigh_swing))
        self.front_legs = (self.front_leg,) if self.front_leg else ()
        if self.seated > 0.5 and abs(pose.yaw) <= FAR_LIMB_ANGLE and pose.view != "back":
            # sitting seen from the front: both thighs come toward the viewer over the lap, the farther knee first
            self.front_legs = tuple(sorted(("leg_l", "leg_r"), key=lambda leg: self.depth[f"knee_{leg[-1]}"]))
            self.front_leg = self.front_legs[-1]
        self.ground = pose.ground if pose.ground is not None else (SEAT_DROP if self.seated > 0.5 else None)

    def _scale(self, bone):
        return self.pose.shorten.get(bone, 1.0)

    def _swing(self, bone):
        return self.pose.swing.get(bone, 0.0)

    def project(self, points):
        """3D figure units -> 2D figure units seen after the turn (orthographic).

        A camera pitched down (pose.pitch) sees points nearer to it lower on the picture.
        """
        pts = _as3(points)
        near = -pts[:, 0] * self.sin_yaw + pts[:, 2] * self.cos_yaw
        down = pts[:, 1] if self.pitch == 0.0 else pts[:, 1] * np.cos(self.pitch) + near * np.sin(self.pitch)
        return np.column_stack([pts[:, 0] * self.cos_yaw + pts[:, 2] * self.sin_yaw, down])

    def depth_of(self, points):
        """How far each 3D point sits toward the viewer after the turn."""
        pts = _as3(points)
        near = -pts[:, 0] * self.sin_yaw + pts[:, 2] * self.cos_yaw
        return near if self.pitch == 0.0 else near * np.cos(self.pitch) - pts[:, 1] * np.sin(self.pitch)

    def ground_mask(self, painting, softness=GROUND_SOFTNESS):
        """1 above the seat or bed the trunk rests on (see Pose.ground), fading to 0 past it; None without one."""
        if self.ground is None:
            return None
        rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
        below = rows - self.origin[1] - self.ground * self.unit     # the ground is level on the picture whatever the lean
        return np.broadcast_to(1.0 - sh.smoothstep(-self.px(softness), self.px(softness), below),
                               painting.shape).astype(np.float32)

    def near_side(self):
        """'l' or 'r': the side of the body turned toward the viewer, or None in a front view."""
        if abs(self.pose.yaw) < 1e-6 or self.pose.view == "back":
            return None
        return "l" if self.pose.yaw > 0 else "r"

    def to_pixels(self, points):
        """Figure units (pelvis centre at 0, 0) -> pixels, applying the lean of the whole figure."""
        return self.origin + _rotate(geo.as_points(np.atleast_2d(points)[:, :2]), self.pose.lean) * self.unit

    def _turned(self, points, shift_center):
        pts = geo.as_points(points).copy()
        turn = self.pose.turn
        far = pts[:, 0] * turn > 0                     # the side the body turns toward is seen narrower
        pts[:, 0] *= np.where(far, 1.0 - TURN_FAR_SQUEEZE * abs(turn), 1.0 + TURN_NEAR_STRETCH * abs(turn))
        if shift_center:
            pts[:, 0] += TURN_CENTER_SHIFT * turn * 2.0   # things on the front surface slide with the turn
        return pts

    # ---- placing points on the trunk ----------------------------------------------------
    def _frame(self, name):
        """(origin, tilt, height of y = 0 above the hip joints) of the chest, waist or pelvis frame."""
        pose = self.pose
        if name == "chest":
            return self._local["chest"], pose.chest_tilt, SPINE_LOWER + SPINE_UPPER
        if name == "waist":
            return self._local["waist"], (pose.chest_tilt + pose.pelvis_tilt) / 2, SPINE_LOWER
        if name == "pelvis":
            return self._local["pelvis"], pose.pelvis_tilt, 0.0
        raise ValueError(f"unknown trunk frame: {name}")

    def _on(self, frame, points, surface):
        origin, tilt, base = self._frame(frame)
        if self.yaw == 0.0:                            # front view: the flat rig, unchanged
            return self.to_pixels(origin[:2] + _rotate(self._turned(points, surface), tilt))
        placed, _ = self.wrap(frame, points)
        return self.to_pixels(placed)

    def on_chest(self, points, surface=False):
        """Chest coordinates (x from the breastbone, y down from the shoulder line) -> pixels."""
        return self._on("chest", points, surface)

    def on_pelvis(self, points, surface=False):
        """Pelvis coordinates (x from the centre, y down from the hip joints) -> pixels."""
        return self._on("pelvis", points, surface)

    def on_waist(self, points, surface=False):
        return self._on("waist", points, surface)

    def wrap(self, frame, points):
        """Points given in a front-view trunk frame, laid on the trunk surface of a turned body.

        x runs across the front of the body; |x| beyond the trunk half-width continues round the
        sides. Whatever has turned out of sight is held at the silhouette and pushed outward by the
        distance it still had to go, so regions drawn with far-away corners still cover the body.
        Returns (2D figure units after the turn, visibility 0..1 per point).
        """
        origin, tilt, base = self._frame(frame)
        pts = geo.as_points(points)
        heights = base - pts[:, 1]
        width, front, back = trunk_section(self.body, heights)
        centre = origin + _rotate(_as3(np.column_stack([np.zeros(len(pts)), pts[:, 1]])), tilt)
        across = _rotate(_as3([(1.0, 0.0)]), tilt)[0]
        right, left = section_extremes(width, front, back, np.radians(tilt), self.yaw)
        x = pts[:, 0]
        angle = np.where(np.abs(x) <= width, np.arccos(np.clip(x / np.maximum(width, 1e-9), -1.0, 1.0)),
                         np.where(x > 0, -(x - width) / np.maximum(width, 1e-9), np.pi + (-x - width) / np.maximum(width, 1e-9)))
        held = np.clip(angle, right, left)
        overshoot = np.abs(held - angle) * width                 # how far round the body a hidden point still had to go
        depth = np.where(np.sin(held) >= 0, front, back) * np.sin(held)
        surface = centre + across * (width * np.cos(held))[:, None] + np.column_stack([np.zeros((len(pts), 2)), depth])
        placed = self.project(surface)
        placed[:, 0] += np.where(angle < right, 1.0, np.where(angle > left, -1.0, 0.0)) * overshoot
        margin = np.minimum(angle - right, left - angle)
        return placed, sh.smoothstep(0.0, VISIBILITY_FADE, margin)

    def surface3(self, frame, points):
        """Points on the front of the trunk in 3D figure units (no hiding): for volumes such as breasts."""
        origin, tilt, base = self._frame(frame)
        pts = geo.as_points(points)
        width, front, _ = trunk_section(self.body, base - pts[:, 1])
        share = np.clip(pts[:, 0] / np.maximum(width, 1e-9), -1.0, 1.0)
        return origin + _rotate(_as3(pts), tilt) + np.column_stack([np.zeros((len(pts), 2)), front * np.sqrt(1.0 - share ** 2)])

    def front_visibility(self, shape):
        """Map (canvas shape) of how squarely the front of the trunk faces the viewer: 1 front-on, 0 turned away.

        Marks on the front of the body are clipped by it, so the side turned away loses them.
        """
        if self.pose.view == "back":            # seen from behind, the front faces away entirely
            return np.zeros(shape, dtype=np.float32)
        if self.yaw == 0.0:
            return np.ones(shape, dtype=np.float32)
        from scipy import ndimage
        heights = np.linspace(FLANK_STATIONS[0][0], SPINE_LOWER + SPINE_UPPER + NECK, VISIBILITY_ROWS)
        centre, tilt = trunk_frame(self, heights)
        width, front, back = trunk_section(self.body, heights)
        right, left = section_extremes(width, front, back, np.radians(tilt), self.yaw)
        angle = np.linspace(0.0, np.pi, VISIBILITY_COLUMNS)[None, :]
        across = np.stack([np.cos(np.radians(tilt)), np.sin(np.radians(tilt)), np.zeros_like(tilt)], axis=1)
        points = (centre[:, None, :] + across[:, None, :] * (width[:, None] * np.cos(angle))[..., None]
                  + np.stack([np.zeros_like(angle * width[:, None])] * 2 + [front[:, None] * np.sin(angle)], axis=-1))
        seen = sh.smoothstep(0.0, VISIBILITY_FADE, np.minimum(angle - right[:, None], left[:, None] - angle))
        pixels = np.rint(self.to_pixels(self.project(points.reshape(-1, 3)))).astype(int)
        inside = (pixels[:, 0] >= 0) & (pixels[:, 0] < shape[1]) & (pixels[:, 1] >= 0) & (pixels[:, 1] < shape[0])
        grid = np.zeros(shape, dtype=np.float32)
        np.maximum.at(grid, (pixels[inside, 1], pixels[inside, 0]), seen.reshape(-1)[inside].astype(np.float32))
        spacing = max(self.unit * (heights[-1] - heights[0]) / VISIBILITY_ROWS, 1.0)
        grid = ndimage.grey_dilation(grid, size=int(np.ceil(spacing * 2.5)) | 1)
        return sh.blur(grid, spacing)

    def visibility(self, frame, points):
        """0..1 per point: how squarely a point on the front of the trunk faces the viewer."""
        if self.pose.view == "back":            # pockets, lapels, ties and bows stay on the hidden front
            return np.zeros(len(geo.as_points(points)))
        if self.yaw == 0.0:
            return np.ones(len(geo.as_points(points)))
        return self.wrap(frame, points)[1]

    def px(self, units):
        return units * self.unit


# ---- flesh -------------------------------------------------------------------------
def _bone_tube(skeleton, start, end, flesh, side, depth=None, cap_end=True):
    """Tube along one bone. The outer profile and the bow go on the side of the limb away from the body.

    depth: (front, back, forward bow) profiles of the limb seen from the side. On a turned body each
    edge of the tube blends its side-to-side and front-to-back thickness, as the section turns.
    """
    outer, inner, bow = flesh
    scale = skeleton.body.limb * (skeleton.body.arms if "elbow" in start + end else 1.0)
    outer, inner = (np.array(profile) * scale * skeleton.unit for profile in (outer, inner))
    a, b = skeleton.joints[start], skeleton.joints[end]
    chord = b - a
    left_of_travel = np.array([chord[1], -chord[0]]) / max(np.linalg.norm(chord), 1e-9) * -1.0
    outward = left_of_travel if side == "l" else -left_of_travel
    left, right = (outer, inner) if side == "l" else (inner, outer)
    if skeleton.yaw == 0.0 or depth is None:
        path = geo.smooth([a, (a + b) / 2 + outward * bow * skeleton.unit, b])
        return geo.tube(path, left, right, caps=(True, cap_end))
    front, back, forward_bow = depth
    front, back = (np.array(profile) * scale * skeleton.unit for profile in (front, back))
    cos_yaw, sin_yaw = abs(skeleton.cos_yaw), skeleton.sin_yaw
    # Which screen side of the tube the front of the limb turns toward.
    front_on_right = sin_yaw >= 0
    left_is_screen_left = left_of_travel[0] <= 0
    left_depth, right_depth = (back, front) if front_on_right == left_is_screen_left else (front, back)
    left = np.hypot(left * cos_yaw, left_depth * sin_yaw)
    right = np.hypot(right * cos_yaw, right_depth * sin_yaw)
    bend = outward * bow * cos_yaw + np.array([forward_bow * sin_yaw, 0.0])
    path = geo.smooth([a, (a + b) / 2 + bend * skeleton.unit, b])
    return geo.tube(path, left, right, caps=(True, cap_end))


# Trunk flank: half-width by height above the hip joints (negative is below them), as
# (height, waist share, hip share, offset in head heights): width = waist * share + hip * share + offset.
# Below the widest point the flank keeps rounding down into the outer thigh, so hip and thigh read as one curve.
FLANK_STATIONS = (
    (-0.60, 0.00, 1.00, -0.10),
    (-0.35, 0.00, 1.00, -0.03),
    (-0.10, 0.00, 1.00, 0.00),      # widest point of the hips
    (0.25, 0.20, 0.80, 0.00),
    (0.55, 0.70, 0.30, 0.00),
    (0.82, 1.00, 0.00, 0.00),       # narrowest point of the waist
)
RIB_STATIONS = (               # (height, half-width above the waist as a share of chest + RIB_FLARE - waist)
    (1.10, 0.40),
    (1.40, 0.82),
    (1.75, 1.00),
)
RIB_FLARE = 0.045            # the ribcage is widest just below the armpit
TRUNK_BLEND = (0.35, 1.25)   # heights over which the pelvis frame hands over to the chest frame
FLANK_SAMPLES = 20
# Side view of the trunk: (height above the hip joints, front depth, back depth) in head heights.
# Breasts and buttocks are added as their own volumes; these are the ribcage, belly, back and neck.
TRUNK_DEPTH = {
    "female": [(-0.60, 0.29, 0.29), (-0.35, 0.30, 0.33), (-0.10, 0.31, 0.34), (0.20, 0.31, 0.30), (0.50, 0.28, 0.24),
               (0.82, 0.26, 0.22), (1.10, 0.29, 0.25), (1.40, 0.33, 0.29), (1.75, 0.34, 0.31), (2.03, 0.31, 0.31),
               (2.23, 0.24, 0.29), (2.32, 0.14, 0.29), (2.50, 0.17, 0.25), (2.69, 0.20, 0.22)],
    "male": [(-0.60, 0.28, 0.28), (-0.35, 0.28, 0.31), (-0.10, 0.28, 0.31), (0.20, 0.27, 0.27), (0.50, 0.26, 0.24),
             (0.82, 0.27, 0.23), (1.10, 0.31, 0.26), (1.40, 0.36, 0.30), (1.75, 0.38, 0.33), (2.03, 0.35, 0.34),
             (2.23, 0.27, 0.32), (2.32, 0.16, 0.31), (2.50, 0.19, 0.27), (2.69, 0.22, 0.24)],
}
HIP_SWELL_HEIGHT = (-0.12, 0.30)   # centre and spread of the extra hip roundness on a turned body


def _flank_width(body, heights):
    """Monotone interpolation: no overshoot between stations, zero slope at the waist and the hips."""
    stations = [(h, body.waist * w + body.hip * p + offset) for h, w, p, offset in FLANK_STATIONS]
    stations += [(h, body.waist + share * (body.chest + RIB_FLARE - body.waist)) for h, share in RIB_STATIONS]
    h, width = zip(*stations)
    return PchipInterpolator(h, width)(heights)


def upper_outline(body, capped=True, neck_top=0.06):
    """(half-width, chest y) from the neck down to the armpit: neck, trapezius slope, shoulder cap, ribcage.

    capped=False drops the round of the shoulder: that belongs to the arm, and once the far arm has
    gone behind the trunk the trunk alone must slope from the neck to the ribcage.
    neck_top: how far the neck reaches above the head pivot, hidden under the head.
    """
    neck = NECK_HALF_WIDTH * body.neck
    if capped:
        shoulder = [(body.shoulder - 0.02, -0.005), (body.shoulder + 0.10, 0.055), (body.shoulder + 0.13, 0.20)]
    else:
        rib = body.chest + RIB_FLARE
        shoulder = [(body.shoulder - 0.06, 0.0), (geo.lerp(body.shoulder - 0.06, rib, 0.5) + 0.02, 0.06), (rib + 0.02, 0.20)]
    return ([(neck, -(NECK + neck_top)), (neck + 0.010, -0.17), (0.25, -0.085), (body.shoulder - 0.16, -0.035)]
            + shoulder + [(body.chest + RIB_FLARE, 0.48)])


def trunk_section(body, heights):
    """Half-width, front depth and back depth of the trunk at each height above the hip joints.

    The widths are the ones the front outline is drawn with; the depths shape the side view.
    """
    heights = np.atleast_1d(np.asarray(heights, dtype=np.float64))
    top = SPINE_LOWER + SPINE_UPPER
    upper = sorted((top - y, w) for w, y in upper_outline(body))
    lower = [(h, body.waist * w + body.hip * p + offset) for h, w, p, offset in FLANK_STATIONS]
    lower += [(h, body.waist + share * (body.chest + RIB_FLARE - body.waist)) for h, share in RIB_STATIONS[:-1]]
    h, width = zip(*(lower + upper))
    depth = np.array(TRUNK_DEPTH[body.build])
    span = np.clip(heights, h[0], h[-1])
    front = PchipInterpolator(depth[:, 0], depth[:, 1])(np.clip(heights, depth[0, 0], depth[-1, 0]))
    back = PchipInterpolator(depth[:, 0], depth[:, 2])(np.clip(heights, depth[0, 0], depth[-1, 0]))
    return PchipInterpolator(h, width)(span), front, back


def section_extremes(width, front, back, tilt, yaw):
    """Angles round a trunk section (0 = right side, pi/2 = front) of its right and left silhouette points.

    The section is two half-ellipses: half-width `width` across, `front` and `back` deep. tilt and yaw are radians.
    """
    across = width * np.cos(tilt) * np.cos(yaw)
    turn = np.sin(yaw)
    right_depth, left_depth = (front, back) if turn >= 0 else (back, front)
    right = np.arctan2(right_depth * turn, across)
    left = np.arctan2(-left_depth * turn, -across)
    return right, np.where(left < 0, left + 2 * np.pi, left)


def _section_edge(skeleton, centre, tilt, width, height, sign, depths=None):
    """Silhouette point of the trunk section at `height` (centre in 3D figure units, tilt in degrees).

    depths: optional (front, back) arrays replacing the trunk's own, for things worn round it.
    """
    width = np.atleast_1d(np.asarray(width, dtype=np.float64))
    front, back = trunk_section(skeleton.body, height)[1:] if depths is None else depths
    right, left = section_extremes(width, front, back, np.radians(tilt), skeleton.yaw)
    angle = right if sign > 0 else left
    depth = np.where(np.sin(angle) >= 0, front, back) * np.sin(angle)
    across = _rotate(_as3([(1.0, 0.0)]), tilt)[0] if np.isscalar(tilt) else \
        np.column_stack([np.cos(np.radians(tilt)), np.sin(np.radians(tilt)), np.zeros(len(width))])
    points = _as3(centre) + across * (width * np.cos(angle))[:, None] + np.column_stack([np.zeros((len(width), 2)), depth])
    return skeleton.project(points)


def wrapped_outline(skeleton, heights, widths, standoff=0.0, back_extra=None):
    """Right and left silhouette (2D figure units after the turn) of a shell worn round the trunk.

    widths: its half-width at each height; standoff: how far it stands off the front and back
    (array or number); back_extra: more room behind, for the buttocks.
    """
    heights = np.asarray(heights, dtype=np.float64)
    _, front, back = trunk_section(skeleton.body, heights)
    front = front + standoff
    back = back + standoff + (0.0 if back_extra is None else back_extra)
    centre, tilt = trunk_frame(skeleton, heights)
    return (_section_edge(skeleton, centre, tilt, widths, heights, 1.0, (front, back)),
            _section_edge(skeleton, centre, tilt, widths, heights, -1.0, (front, back)))


def trunk_frame(skeleton, heights):
    """Centre (3D figure units) and tilt (degrees) of the trunk at each height above the hip joints.

    The pelvis frame holds below TRUNK_BLEND, the chest frame above it, and both are blended in between,
    so the outline meets the landmarks placed with on_pelvis and on_chest exactly.
    """
    pose = skeleton.pose
    heights = np.asarray(heights, dtype=np.float64)
    top = SPINE_LOWER + SPINE_UPPER
    column = np.zeros_like(heights)
    low = skeleton._local["pelvis"] + _rotate(np.column_stack([column, -heights, column]), pose.pelvis_tilt)
    high = skeleton._local["chest"] + _rotate(np.column_stack([column, top - heights, column]), pose.chest_tilt)
    weight = sh.smoothstep(TRUNK_BLEND[0], TRUNK_BLEND[1], heights)[:, None]
    centre = low * (1.0 - weight) + high * weight
    return centre, pose.pelvis_tilt + (pose.chest_tilt - pose.pelvis_tilt) * weight[:, 0]


def _flank(skeleton, sign, heights):
    """One side of the trunk between the ribcage and the hips, in 2D figure units after the turn."""
    body, turn = skeleton.body, skeleton.pose.turn
    width = _flank_width(body, heights)
    if sign * turn > 0:                                   # the side turned away is seen narrower
        width = width * (1.0 - TURN_FAR_SQUEEZE * abs(turn))
    else:                                                 # the near hip rounds out on a turned body
        width = width * (1.0 + TURN_NEAR_STRETCH * abs(turn))
        if body.build != "male":
            middle, spread = HIP_SWELL_HEIGHT
            width = width + HIP_SWELL * abs(turn) * np.exp(-((heights - middle) / spread) ** 2)
    centre, tilt = trunk_frame(skeleton, heights)
    if skeleton.yaw == 0.0:
        across = np.stack([np.cos(np.radians(tilt)), np.sin(np.radians(tilt))], axis=1)
        return centre[:, :2] + across * (sign * width)[:, None]
    return _section_edge(skeleton, centre, tilt, width, heights, sign)


def torso_curve(skeleton):
    """Trunk outline: neck, shoulders, ribcage narrowing to the waist, then the swell of the hips.

    A turned body shows each section at its silhouette points, so the front, back and flanks of
    the trunk take over the outline as the body turns.
    """
    rib_top = SPINE_LOWER + SPINE_UPPER - 0.48           # height of the last chest-frame point
    heights = np.linspace(rib_top - 0.12, FLANK_STATIONS[0][0], FLANK_SAMPLES)
    origin, tilt, top = skeleton._frame("chest")
    sides = []
    far_arm_hidden = skeleton.near_side() is not None and any(name.startswith("arm") and name[-1] != skeleton.near_side()
                                                              for name in skeleton.behind)
    for sign in (1.0, -1.0):
        far = skeleton.yaw != 0.0 and sign * skeleton.yaw > 0
        # A turned head shows the base of the skull behind the jaw; the neck must reach up under it there.
        outline = upper_outline(skeleton.body, capped=not (far and far_arm_hidden),
                                neck_top=0.06 if skeleton.yaw == 0.0 else TURNED_NECK_TOP)
        if skeleton.yaw == 0.0:
            chest = skeleton.on_chest([(sign * w, y) for w, y in outline])
            lower = skeleton.on_pelvis([(sign * 0.24, 0.52)])        # in toward the crotch, hidden inside the thighs
        else:
            chest = skeleton.to_pixels(np.vstack([
                _section_edge(skeleton, origin + _rotate(_as3([(0.0, y)]), tilt)[0], tilt, w, top - y, sign)
                for w, y in outline]))
            pelvis, pelvis_tilt, _ = skeleton._frame("pelvis")
            lower = skeleton.to_pixels(_section_edge(skeleton, pelvis + _rotate(_as3([(0.0, 0.52)]), pelvis_tilt)[0],
                                                     pelvis_tilt, 0.24, -0.52, sign))
        flank = skeleton.to_pixels(_flank(skeleton, sign, heights))
        sides.append(np.vstack([chest, flank, lower]))
    crotch = skeleton.to_pixels(skeleton.project(skeleton._local["pelvis"] + _rotate(_as3([(0.0, 0.45)]), skeleton.pose.pelvis_tilt)))
    points = np.vstack([sides[0], crotch, sides[1][::-1]])
    return geo.smooth(points, closed=True, corners=(0, len(points) - 1))


def limb_masks(painting, skeleton):
    """Masks of the four limbs (hands are added by the caller)."""
    masks = {}
    thigh = MALE_THIGH_FLESH if skeleton.body.build == "male" else THIGH_FLESH
    for side in ("l", "r"):
        heel = f"ankle_{side}" if skeleton.yaw == 0.0 else f"heel_{side}"      # the heel shows once the body turns
        arm = [_bone_tube(skeleton, f"shoulder_{side}", f"elbow_{side}", UPPER_ARM_FLESH, side, LIMB_DEPTH["upper_arm"]),
               _bone_tube(skeleton, f"elbow_{side}", f"wrist_{side}", FOREARM_FLESH, side, LIMB_DEPTH["forearm"])]
        leg = [_bone_tube(skeleton, f"hip_{side}", f"knee_{side}", thigh, side, LIMB_DEPTH["thigh"]),
               _bone_tube(skeleton, f"knee_{side}", f"ankle_{side}", SHIN_FLESH, side, LIMB_DEPTH["shin"]),
               _bone_tube(skeleton, heel, f"toe_{side}", FOOT_FLESH, side, LIMB_DEPTH["foot"])]
        masks[f"arm_{side}"] = sh.melt(np.maximum.reduce([painting.mask(curve) for curve in arm]), skeleton.px(MELT_RADIUS * 0.6))
        pieces = [painting.mask(curve) for curve in leg]
        masks[f"leg_{side}"] = sh.melt(np.maximum.reduce(pieces), skeleton.px(MELT_RADIUS * 0.6))
        if skeleton.seated > 0.5:          # a seated leg may be drawn in two layers: shin and foot, then the thigh over them
            masks[f"thigh_{side}"] = pieces[0]
            masks[f"shin_{side}"] = sh.melt(np.maximum(pieces[1], pieces[2]), skeleton.px(MELT_RADIUS * 0.6))
    return masks


def _joint_disc(painting, skeleton, joint, radius):
    center = skeleton.joints[joint]
    return painting.mask(geo.ellipse(center, skeleton.px(radius), skeleton.px(radius), count=32))


def bridged_height(painting, skeleton, mask, bevel):
    """Height field for shading a mask that holds both thighs.

    Inflating the mask as it is makes the notch between the thighs a deep edge, and the shadow
    along it ends in a rounded tongue at the top of the gap that reads as a dent. Here the gap is
    bridged from its top and the bridge fades out downward, so the inner-thigh shadow grows in gradually.
    """
    crotch = skeleton.on_pelvis([(0.0, 0.45)])[0]
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    cols = np.arange(painting.shape[1], dtype=np.float32)[None, :]
    reach = skeleton.px(BRIDGE_DEPTH + 0.6)
    window = ((rows >= crotch[1] - skeleton.px(0.10)) & (rows <= crotch[1] + reach)
              & (np.abs(cols - crotch[0]) <= skeleton.px(BRIDGE_HALF_WIDTH)))
    inside = (mask > 0.5) & window
    spanned = np.maximum.accumulate(inside, axis=1) & np.maximum.accumulate(inside[:, ::-1], axis=1)[:, ::-1]
    gap_rows = np.nonzero((spanned & ~(mask > 0.5)).any(axis=1))[0]
    if len(gap_rows) == 0:                    # the thighs touch all the way down: nothing to bridge
        return sh.inflate(mask, bevel)
    apex = float(gap_rows[0])                 # where the thighs part
    filled = np.maximum(mask, spanned.astype(np.float32))
    weight = 1.0 - sh.smoothstep(apex + skeleton.px(0.08), apex + skeleton.px(BRIDGE_DEPTH), rows)
    return sh.inflate(mask, bevel) * (1.0 - weight) + sh.inflate(filled, bevel) * weight


def draw_skin_group(painting, skeleton, mask, spec, style, light, attach=None, under=None, merge_into=None,
                    bridge=False):
    """Fill, shade and outline one group of body parts.

    attach: joint names where this group grows out of what is already drawn (no outline there).
    under: mask of the figure drawn so far; receives the group's cast shadow.
    merge_into: mask inside which the group shows no outline at all (a thigh inside the pelvis).
    bridge: the group holds both thighs; shade them as one mass near the crotch (see bridged_height).
    """
    skin = rgb(spec.skin)
    shadow = face.skin_shadow_color(spec, style)
    light2d = light_on_canvas(light)
    if under is not None:
        offset = -light2d * skeleton.px(0.07) + [0.0, skeleton.px(0.03)]
        # Multiply, so the shadow darkens whatever it lands on (skin or cloth) in that thing's own colour.
        cast = sh.cast_shadow(mask, under, offset, cast_softness_px(style, painting)) * (1.0 - mask)
        painting.fill(cast, rgb(style.shadow_tint), 0.75 * style.shadow_depth, "multiply")
    painting.part(mask, skin)
    height = bridged_height(painting, skeleton, mask, skeleton.px(FORM_BEVEL)) if bridge else None
    shade_form(painting, mask, skin, style, light, bevel=skeleton.px(FORM_BEVEL), shadow_color=shadow, height=height,
               threshold=style.shadow_threshold - 0.04,
               terminator=face.SKIN_TERMINATOR if style.terminator > 0 else None)
    if style.line_width > 0:
        keep = None
        if attach and under is not None:
            radius = ATTACH_RADIUS * skeleton.body.limb * (skeleton.body.arms if attach[0].startswith("shoulder") else 1.0)
            discs = np.maximum.reduce([_joint_disc(painting, skeleton, joint, radius) for joint in attach])
            keep = 1.0 - discs * sh.blur(under, skeleton.px(0.02))
        if merge_into is not None:
            inside = 1.0 - sh.blur(merge_into, skeleton.px(0.015))
            keep = inside if keep is None else keep * inside
        painting.outline_mask(mask, skeleton.px(LINE_WIDTH) * style.line_width,
                              line_color(style, skin, face.SKIN_INK), keep=keep)


def model_big_form(painting, skeleton, mask, style, light):
    """Shade the whole figure as one rounded mass.

    Per-limb shading alone leaves a body looking like separate tubes. This pass lets the
    side away from the light sink back as a whole, under a light lowered toward the
    picture plane so that more of the turn of the form shows.
    """
    raking = np.array([light[0], light[1], light[2] * BIG_FORM_RAKE])
    lit = sh.lighting(mask, raking, height=bridged_height(painting, skeleton, mask, skeleton.px(BIG_FORM_BEVEL)))
    far_side = sh.shadow_from_light(lit, BIG_FORM_THRESHOLD, 0.10 + 0.5 * style.edge_softness) * mask
    painting.fill(far_side, rgb(BIG_FORM_TINT), min(0.3 + 0.75 * style.gradient, 0.85), "multiply")


def polish_skin(painting, skeleton, skin, trunk, limbs, style, light, skin_color=None):
    """Contact shadows between the legs and a sheen along the lit ridges: what makes skin look alive."""
    from scipy import ndimage
    reach = skeleton.px(0.07)
    # Thigh tops overlap inside the pelvis; that is no contact. Below the crotch the shadow fades in
    # over CONTACT_FADE, so it never starts as a hard-topped blob.
    below_trunk = sh.smoothstep(0.0, skeleton.px(CONTACT_FADE), ndimage.distance_transform_edt(trunk < 0.5)).astype(np.float32)
    contact = np.clip(sh.blur(limbs["leg_l"], reach) * sh.blur(limbs["leg_r"], reach) * 3.0, 0.0, 1.0) * skin * below_trunk
    painting.fill(contact, rgb(CONTACT_TINT), 0.55 * style.shadow_depth, "multiply")
    if style.highlight > 0:
        lit = sh.lighting(skin, light, bevel=skeleton.px(0.20))
        ridge = sh.smoothstep(0.80, 0.98, lit) * skin
        softness = skeleton.px(0.006 + 0.03 * style.gradient)     # crisp for cel shading, diffuse for soft styles
        sheen = SHEEN_COLOR if skin_color is None else face.skin_light(skin_color, SHEEN_COLOR)
        painting.fill(sh.blur(ridge, softness) * skin, sheen, (0.22 + 0.25 * style.gradient) * style.highlight, "screen")


def head_spec(spec, skeleton, canvas_shape):
    """Place the head rig on top of the skeleton's neck."""
    height, width = canvas_shape
    lean = skeleton.pose.lean
    pivot = skeleton.joints["head_pivot"]
    head_unit = skeleton.unit * skeleton.body.head
    crown = pivot - np.array([0.0, HEAD_PIVOT_Y]) * head_unit
    pose = skeleton.pose
    if pose.view == "back":                                   # seen from behind, the head is drawn square-on
        return replace(spec, crown=(crown[0] / width, crown[1] / height), head_size=head_unit / height,
                       tilt=pose.head_tilt + lean, yaw=0.0, turn_deg=None)
    turn_deg = spec.turn_deg
    if pose.head_yaw is not None or pose.yaw != 0.0:          # a turned body takes the head round with it
        turn_deg = pose.head_yaw if pose.head_yaw is not None else pose.yaw
    return replace(spec, crown=(crown[0] / width, crown[1] / height), head_size=head_unit / height,
                   tilt=pose.head_tilt + lean, yaw=spec.yaw, turn_deg=turn_deg)


def _behind_head(painting, skeleton, side, head, back_hair):
    """Mask hiding the end of an arm raised behind the head; None when that hand is not raised.

    The head, the neck and the hair hanging behind them stand between the viewer and the hand; small gaps
    between them (under the jaw, beside the neck) are closed so fingers do not peek out at the throat.
    """
    wrist, shoulder = skeleton.joints[f"wrist_{side}"], skeleton.joints[f"shoulder_{side}"]
    if wrist[1] >= shoulder[1]:
        return None
    from scipy import ndimage
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    neck = painting.mask(torso_curve(skeleton)) * (rows < shoulder[1])
    cover = np.maximum.reduce([head, back_hair, neck]) > 0.5
    radius = skeleton.px(BEHIND_HEAD_GAP)
    grown = ndimage.distance_transform_edt(~cover) <= radius
    closed = ndimage.distance_transform_edt(grown) > radius
    near_hand = painting.mask(geo.ellipse(wrist, skeleton.px(BEHIND_HEAD_REACH), skeleton.px(BEHIND_HEAD_REACH)))
    return np.maximum(closed.astype(np.float32), cover.astype(np.float32)) * near_hand


def _draw_head_from_behind(painting, parts, spec, style, light):
    """Back of the head: skin and ears first, then the whole hair mass laid over them."""
    face.draw_ears(painting, parts.frame, spec, style)
    painting.part(parts.head, spec.skin)
    shade_form(painting, parts.head, spec.skin, style, light, shadow_color=face.skin_shadow_color(spec, style))
    hair = hair_rig.draw_back_hair(painting, parts.frame, spec, style, light, parts.plan, in_front=True)
    hat = accessories.draw_hat(painting, parts.frame, spec, style, light, parts.head, hair, from_behind=True)
    return np.maximum(hair, hat)            # headwear belongs to the silhouette of the hair


UNDER_KNEE_REACH = 0.55      # share of each shin, from the knee down, kept in shadow by the thighs and seat
UNDER_KNEE_DEPTH = 0.60      # strength of that shadow just under the knee


def shade_under_knees(painting, skeleton, limbs, style):
    """Seated, seen from the front: the raised thighs and the seat keep the top of each shin in shadow.

    The thighs point at the viewer and look short on the picture. This dark band under the knees is
    what tells a seated figure from a standing one, bare legs and trousers alike.
    """
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    for side in ("l", "r"):
        shin = limbs[f"shin_{side}"] * (1.0 - limbs[f"thigh_{side}"])
        showing = np.flatnonzero((shin > 0.5).any(axis=1))
        if len(showing) == 0:
            continue
        top = float(showing[0])                    # where the shin comes out from under the thigh
        ankle = skeleton.joints[f"ankle_{side}"][1]
        fade = 1.0 - sh.smoothstep(top, top + UNDER_KNEE_REACH * max(ankle - top, 1.0), rows)
        painting.fill(shin * fade, style.shadow_tint, UNDER_KNEE_DEPTH * style.shadow_depth, mode="multiply")


def draw_figure(painting, spec=None, body=None, pose=None, style=ANIME, light=sh.DEFAULT_LIGHT,
                dress=None, hands=None):
    """Draw a full figure. Returns masks (figure, skin, head, trunk, limbs, clothes, hair, eyes) and the skeleton.

    dress: optional function(painting, skeleton, masks, spec, style, light) -> mask, drawing clothes over
           the trunk and legs before the front arms go on. None leaves the figure study. A clothing.Outfit
           may add a `behind` layer (under the hair) and a `sleeve` layer (over each arm).
    hands: optional {"l": HandPose, "r": HandPose}; relaxed hands are used otherwise.
    """
    spec, body, pose = spec or PortraitSpec(), body or BodySpec(), pose or Pose()
    skeleton = Skeleton(pose, body, painting.shape)
    from_behind = pose.view == "back"
    head_spec_ = head_spec(spec, skeleton, painting.shape)
    parts = prepare_head(painting, head_spec_)
    limbs = limb_masks(painting, skeleton)
    hand_shapes, hand_masks = {}, {}
    for side in ("l", "r"):
        _, hand_shapes[side], hand_masks[side] = hand_rig.figure_hand(painting, skeleton, side,
                                                                       (hands or {}).get(side, hand_rig.RELAXED))
        limbs[f"arm_{side}"] = np.maximum(limbs[f"arm_{side}"], hand_masks[side])
    trunk = painting.mask(torso_curve(skeleton))
    legs_in_trunk = [name for name in ("leg_l", "leg_r") if name not in skeleton.front_legs and name not in skeleton.behind]
    resting = skeleton.ground_mask(painting)
    if resting is not None:                               # flesh resting on a seat or bed flattens against it
        trunk = trunk * resting
    trunk_group = np.maximum.reduce([trunk] + [limbs[name] for name in legs_in_trunk])
    if not from_behind and skeleton.yaw != 0.0:          # once the back shows, so do the buttocks
        buttocks = anatomy.buttock_mask(painting, skeleton)
        trunk_group = np.maximum(trunk_group, buttocks if resting is None else buttocks * resting)
    trunk_group = sh.melt(trunk_group, skeleton.px(MELT_RADIUS))
    if not from_behind:
        # Breasts belong to the silhouette: on a turned body the far one shows in profile past the ribcage.
        trunk_group = np.maximum(trunk_group, anatomy.breast_mask(painting, skeleton))

    masks = {"trunk": trunk, "limbs": limbs, "skeleton": skeleton}
    clothes = np.zeros(painting.shape, dtype=np.float32)
    behind_layer, sleeve_layer = getattr(dress, "behind", None), getattr(dress, "sleeve", None)
    if behind_layer is not None and not from_behind:      # what hangs behind the neck goes under the hair
        clothes = behind_layer(painting, skeleton, masks, spec, style, light)
    back_hair = np.zeros(painting.shape, dtype=np.float32) if from_behind else draw_head_back(painting, parts, head_spec_, style, light)
    drawn = clothes.copy()
    skin_ink = line_color(style, spec.skin, face.SKIN_INK)
    gap_width = skeleton.px(LINE_WIDTH) * style.line_width * 0.45

    def finish_arm(name, gaps=True):
        nonlocal clothes, drawn
        if gap_width > 0 and gaps:
            hand_rig.draw_finger_gaps(painting, hand_shapes[name[-1]], skin_ink, gap_width)
        if sleeve_layer is not None:
            sleeve = sleeve_layer(painting, skeleton, name[-1], masks, spec, style, light)
            clothes, drawn = np.maximum(clothes, sleeve), np.maximum(drawn, sleeve)

    for name in skeleton.behind:
        hidden = None
        if name.startswith("arm") and not from_behind:
            hidden = _behind_head(painting, skeleton, name[-1], parts.head, back_hair)
            if hidden is not None:      # a hand raised behind the head stays behind the head, the neck and the hair
                limbs[name] = limbs[name] * (1.0 - hidden)
        draw_skin_group(painting, skeleton, limbs[name], spec, style, light)
        if name.startswith("arm"):
            hand = hand_masks[name[-1]]
            if hidden is None or (hand * hidden).sum() < HAND_HIDDEN_SHARE * max(hand.sum(), 1e-6):
                finish_arm(name)
            elif sleeve_layer is not None:
                finish_arm(name, gaps=False)
        drawn = np.maximum(drawn, limbs[name])
    draw_skin_group(painting, skeleton, trunk_group, spec, style, light, bridge=len(legs_in_trunk) == 2)
    if not from_behind:
        # The jaw throws its shadow straight down; in profile it sits close over the neck (see outfit).
        turned = parts.frame.profile
        head_shadow = sh.cast_shadow(parts.caster, trunk_group,
                                     (-light_on_canvas(light)[0] * skeleton.px(0.05) * (1.0 - turned),
                                      skeleton.px(CHIN_SHADOW_DROP * (1.0 - PROFILE_CHIN_SHADOW * turned))),
                                     cast_softness_px(style, painting))
        painting.fill(head_shadow, face.skin_shadow_color(spec, style))
    anatomy.draw_landmarks(painting, skeleton, trunk_group, spec, style, light)
    drawn = np.maximum(drawn, trunk_group)
    lap = skeleton.seated > 0.5 and abs(pose.yaw) <= FAR_LIMB_ANGLE
    for front_leg in skeleton.front_legs:
        side = front_leg[-1]
        if lap:
            # Seen from the front a seated thigh points at the viewer: its knee end overlaps the top of the shin.
            draw_skin_group(painting, skeleton, limbs[f"shin_{side}"], spec, style, light, attach=[f"knee_{side}"], under=drawn)
            drawn = np.maximum(drawn, limbs[f"shin_{side}"])
            draw_skin_group(painting, skeleton, limbs[f"thigh_{side}"], spec, style, light,
                            attach=[f"hip_{side}"], under=drawn, merge_into=trunk)
        else:
            draw_skin_group(painting, skeleton, limbs[front_leg], spec, style, light,
                            attach=[f"hip_{side}"], under=drawn, merge_into=trunk)
        anatomy.draw_leg_marks(painting, skeleton, side, spec, style, limbs[front_leg])
        drawn = np.maximum(drawn, limbs[front_leg])
    if lap and not from_behind:
        anatomy.draw_lap(painting, skeleton, drawn, spec, style)
    masks.update({"trunk": trunk, "skin": drawn * (1.0 - clothes)})
    if skeleton.yaw != 0.0 and not from_behind:
        # On a turned body breasts and buttocks stand out of the trunk outline; clothes must cover them,
        # and must not cover the far arm showing past the back.
        buttocks = anatomy.buttock_mask(painting, skeleton)
        masks["trunk"] = np.maximum.reduce([trunk, anatomy.breast_mask(painting, skeleton),
                                            buttocks if resting is None else buttocks * resting])
        if skeleton.hidden_arm:
            masks["skin"] = masks["skin"] * (1.0 - limbs[skeleton.hidden_arm] * (1.0 - trunk_group))
    if dress is not None:
        clothes = np.maximum(clothes, dress(painting, skeleton, masks, spec, style, light))
        if behind_layer is not None and from_behind:      # seen from behind, a folded hood lies over the back
            clothes = np.maximum(clothes, behind_layer(painting, skeleton, masks, spec, style, light))
        drawn = np.maximum(drawn, clothes)
    masks["clothes"] = clothes
    if lap and not from_behind:
        shade_under_knees(painting, skeleton, limbs, style)
    for name in ("arm_l", "arm_r"):
        if name in skeleton.behind:
            continue
        draw_skin_group(painting, skeleton, limbs[name], spec, style, light,
                        attach=[f"shoulder_{name[-1]}"], under=drawn)
        finish_arm(name)
        drawn = np.maximum(drawn, limbs[name])
    model_big_form(painting, skeleton, drawn, style, light)
    polish_skin(painting, skeleton, drawn * (1.0 - clothes), trunk, limbs, style, light, spec.skin)

    if from_behind:
        hair = _draw_head_from_behind(painting, parts, head_spec_, style, light)
        eyes = np.zeros(painting.shape, dtype=np.float32)
    else:
        eyes, front_hair = draw_head_front(painting, parts, head_spec_, style, light)
        hair = np.maximum(front_hair, back_hair)
    figure = np.clip(hair + drawn + parts.head, 0.0, 1.0)
    draw_rim_light(painting, figure, style, light, skeleton.px(0.012))
    masks.update({"figure": figure, "skin": drawn, "head": parts.head, "eyes": eyes, "clothes": clothes, "hands": hand_masks,
                  "hair": hair, "frame": parts.frame})
    return masks
