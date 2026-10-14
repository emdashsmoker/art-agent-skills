"""Full-body adult figure, posed by joint angles, seen from any side: front, three-quarter, profile, back.

Lengths are in head units (half a head height), like the rest of the rig.
The figure stands about 8 heads tall - adult proportions. Angles are in
degrees on the screen: 0 points straight down, positive swings toward screen
right, negative toward screen left. "left"/"right" always mean SCREEN sides
(as seen with the body facing the viewer).

Pose.turn rotates the body about its vertical axis (-180..180; 90 = profile facing
screen right, 180 = seen from behind). The torso is described by cross-sections
(half-width, front depth, back depth), so a turned body shows the chest and belly
profile on the side it faces and the back and buttocks on the other; legs blend
toward a side-view outline (calf at the back) as the body turns to profile. Limb lengths can be shortened to show limbs pointing toward or away from
the viewer (aim() computes angle and length from a 3D direction), which is how
seated poses are made.

The body is a set of skin parts (torso, neck, legs, feet, arms, hands) painted
by skin.paint_parts(), so limbs merge at the joints and only draw a line
where one part passes in front of another.
"""
from dataclasses import dataclass, field, replace

import cv2
import numpy as np

from .. import raster, shading
from ..color import adjust, mix
from . import hair as hair_module
from .bust import REFERENCE_UNIT, paint_head
from .face import FaceSpec
from .hair import HairSpec
from .hand import HandOrientation, HandSpec, build_hand, finish_hand
from .head import Head
from .look import ILLUSTRATION, Look, skin_line, skin_shadow
from .skin import Part, paint_parts

# --- proportions (head units) ---------------------------------------------------
HEIGHT_UNITS = 16.1           # crown to sole of a figure standing straight (about 8 heads)
_SPINE = 4.90                 # hip-joint line up to the pit of the neck
_NECK = 0.90                  # pit of the neck up to the head's pivot
_SHOULDER = (1.28, 0.30)      # shoulder joint in the chest frame
_HIP = (0.72, 0.0)            # hip joint in the pelvis frame
_UPPER_ARM, _FOREARM, _HAND = 2.70, 2.30, 1.50
_IN_FRONT = 1.6             # head units a far wrist must come forward of its shoulder to pass in front of the body
_REST_PALM_TILT = 20.0        # degrees a resting hand turns its palm from the thigh toward the back
_HAND_SLIVER = 0.025          # share of hand length; thinner bits of a far hand behind the body are dropped
_POCKET = 0.45                # head units; around a pocketed wrist the garment covers the arm
# Where a pocketed wrist goes, by HandSpec pose: pelvis frame (x as a share of the hip half-width, y, lift).
# 'pocket' is the mouth of a front trouser pocket; 'pouch' the side opening of a hoodie's kangaroo pocket.
_POCKETS = {'pocket': (0.80, -0.40, -0.06), 'pouch': (0.66, -0.88, 0.10)}   # a trouser pocket lies just under the cloth
_ELBOW_POLE = (0.8, 0.0, -0.6)  # body frame; a hand in a pocket bends its elbow out and back
_REACH_SLACK = 0.995          # a pocket out of reach is approached with the arm almost straight
_THIGH, _SHIN = 3.90, 3.80
_NECK_WIDTH = 0.64
_ARM_BULGE, _LEG_BULGE = 0.27, 0.50          # rounding radius of the limb's volume shading
_JOINT_BEND = 0.30            # how softly elbows and knees turn (rounding radius of the bone line)
# Limb contours: distance from the bone line to the skin on the outer (lateral) and inner
# (medial) side, at positions t along shoulder->wrist or hip->ankle. The two sides differ:
# that asymmetry is what turns a tube into an arm or a leg.
_ARM_OUTER = [(0.00, 0.33), (0.06, 0.38), (0.16, 0.39), (0.30, 0.33), (0.45, 0.30), (0.54, 0.29),   # deltoid, elbow
              (0.63, 0.34), (0.74, 0.31), (0.88, 0.22), (1.00, 0.17)]                                # forearm swell
_ARM_INNER = [(0.00, 0.30), (0.10, 0.31), (0.24, 0.34), (0.40, 0.31), (0.54, 0.28),
              (0.64, 0.31), (0.78, 0.25), (0.90, 0.19), (1.00, 0.17)]
_LEG_OUTER = [(0.00, 0.74), (0.07, 0.77), (0.18, 0.75), (0.32, 0.64), (0.44, 0.49), (0.51, 0.43),   # thigh, knee
              (0.56, 0.42), (0.62, 0.50), (0.70, 0.47), (0.82, 0.31), (0.93, 0.20), (1.00, 0.17)]    # high outer calf
_LEG_INNER = [(0.00, 0.66), (0.08, 0.71), (0.20, 0.64), (0.34, 0.50), (0.45, 0.39), (0.51, 0.41),   # inner knee bump
              (0.57, 0.37), (0.66, 0.50), (0.74, 0.46), (0.86, 0.27), (0.95, 0.19), (1.00, 0.18)]    # low inner calf
# Right half of the torso outline: chest frame (from the pit of the neck) ...
_CHEST_SIDE = [(0.34, -0.46), (0.62, -0.17), (1.10, 0.04), (1.40, 0.42), (1.23, 1.05), (1.14, 1.82)]
# ... and pelvis frame (from the hip-joint line). Waist, hip bone, widest hip, thigh root, lower pelvis.
_PELVIS_SIDE = [(0.84, -2.18), (0.96, -1.62), (1.21, -0.95), (1.41, -0.34), (1.49, 0.24), (1.40, 0.66),
                (0.60, 0.82)]
# Front and back depth of the body at each outline point above (head units from the body's
# center line): what a turned body shows on the side it faces (front) and the side it turns
# away from (back). Ribcage, waist, belly, then the buttocks swelling behind the hips.
_CHEST_DEPTH = [(0.45, 0.45), (0.55, 0.55), (0.62, 0.62), (0.72, 0.70), (0.78, 0.72), (0.72, 0.66)]
_PELVIS_DEPTH = [(0.62, 0.55), (0.66, 0.60), (0.72, 0.78), (0.74, 0.98), (0.70, 1.02), (0.62, 0.86), (0.50, 0.62)]
_BREAST_LIFT = 0.12           # breast center in front of the chest surface
_BREAST_SLOPE = 2.1           # how high above the breast center its upper slope starts (breast radii)
_SHOULDER_Z, _HIP_Z, _NECK_Z = -0.10, -0.05, -0.08   # joint depths (behind the center line)
_HEAD_FORWARD = 0.14          # the head sits a little in front of the neck base
_HIP_CAP_DEPTH = 0.6          # a turned hip cap narrows toward this share of its width
_BACK_VIEW = 0.25             # -cos(turn) beyond which the figure counts as seen from behind
_FAR_SIDE_TURN = 8.0          # degrees of turn beyond which one side counts as the far side
_ANKLE_CLEAR = 0.42           # radius around the ankle where the foot draws no overlap line
_FOOT_BLEND = 0.50            # the foot grows out of the ankle over this radius (head units)
_FOOT_FOLLOW = 1.25           # feet turn to a full side view as sin(turn) reaches 1 / this
_MARK_FADE = (-0.02, 0.32)    # surface facing over which body marks fade in (0 = on the silhouette)
_BACK_DETAIL_START = 0.15     # cos(turn) below which the back's landmarks start to show
_PINHOLE = 0.18               # enclosed gaps smaller than this square (head units) are sealed
_SEATED_SWING = 50.0          # degrees a thigh swings from hanging straight down before the pose counts as seated
_SEAT_THIGH = 0.84            # half-thickness of a thigh root in the seated mass (head units)
_HIP_CAP = (0.74, 0.20, 0.75, 0.82)   # x, y, rx, ry in the pelvis frame: the round of the hip over each joint
_BREAST_CENTER, _BREAST_RADIUS = (0.57, 1.40), 0.50
_BREAST_LOW = 1.02            # breast radii from its center down to the lowest point of its outline
_FOLD_GAP = 0.02              # head units from that lowest point down to the fold a bikini string sits in
_NAVEL_Y = -1.32              # pelvis frame
_WAIST_SMOOTHING = 0.16       # blur radius used to soften corners of the torso outline
_BASE_BULGE = 0.42            # rounding radius of the whole-body base shading
_BROAD_BULGE = 1.15           # second, wider rounding: lets the belly, ribcage and thighs swell gently
# Foot outlines around the ankle: seen from the front, and from the side (toes toward +x).
_FOOT_FRONT = [(-0.22, -0.20), (0.22, -0.20), (0.27, 0.16), (0.40, 0.50), (0.37, 0.70), (0.0, 0.80),
               (-0.37, 0.70), (-0.40, 0.50), (-0.27, 0.16)]
_FOOT_SIDE = [(-0.24, -0.20), (0.20, -0.20), (0.34, 0.12), (0.98, 0.42), (1.50, 0.60), (1.52, 0.74),
              (0.60, 0.80), (-0.28, 0.80), (-0.42, 0.56)]
# Toe centers, big toe first: across the front edge (front view) or bunched at the tip (side view).
_TOES_FRONT = [(0.27, 0.74), (0.11, 0.80), (-0.03, 0.79), (-0.16, 0.76), (-0.28, 0.70)]
_TOES_SIDE = [(1.50, 0.68), (1.46, 0.70), (1.40, 0.71), (1.33, 0.72), (1.26, 0.73)]
_TOE_RADII = [0.105, 0.078, 0.072, 0.066, 0.058]
# A foot seen from behind: the heel, with the toes hidden in front of it.
_FOOT_HEEL = [(-0.20, -0.20), (0.20, -0.20), (0.25, 0.18), (0.27, 0.48), (0.21, 0.72), (0.0, 0.80),
              (-0.21, 0.72), (-0.27, 0.48), (-0.25, 0.18)]
# A leg seen from the side, distance from the bone line to the front and to the back:
# thigh muscles and kneecap in front, buttock fold, back of the knee and the calf behind.
_LEG_SIDE_FRONT = [(0.00, 0.62), (0.10, 0.70), (0.25, 0.66), (0.40, 0.55), (0.48, 0.46), (0.52, 0.45),
                   (0.56, 0.40), (0.65, 0.33), (0.80, 0.26), (0.92, 0.20), (1.00, 0.18)]
_LEG_SIDE_BACK = [(0.00, 0.80), (0.08, 0.78), (0.25, 0.62), (0.42, 0.48), (0.50, 0.40), (0.57, 0.44),
                  (0.66, 0.58), (0.76, 0.50), (0.88, 0.30), (0.96, 0.22), (1.00, 0.20)]
_TABLE_SAMPLES = np.linspace(0.0, 1.0, 25)

# --- male build (same units and conventions as the tables above) -------------------
# Broader shoulders and ribcage, a straighter waist, narrower hips, heavier limbs and neck.
_MALE_SHOULDER = (1.46, 0.40)
_MALE_HIP = (0.66, 0.0)
_MALE_NECK_WIDTH = 0.80
_MALE_ARM_OUTER = [(0.00, 0.33), (0.06, 0.42), (0.16, 0.47), (0.30, 0.42), (0.45, 0.36), (0.54, 0.33),   # deltoid
                   (0.63, 0.40), (0.74, 0.36), (0.88, 0.25), (1.00, 0.20)]                                # forearm
_MALE_ARM_INNER = [(0.00, 0.36), (0.10, 0.38), (0.24, 0.43), (0.40, 0.39), (0.54, 0.32),                 # biceps
                   (0.64, 0.37), (0.78, 0.29), (0.90, 0.22), (1.00, 0.20)]
_MALE_LEG_OUTER = [(0.00, 0.58), (0.07, 0.63), (0.18, 0.66), (0.32, 0.62), (0.44, 0.50), (0.51, 0.45),
                   (0.56, 0.44), (0.62, 0.55), (0.70, 0.53), (0.82, 0.34), (0.93, 0.22), (1.00, 0.20)]
_MALE_LEG_INNER = [(0.00, 0.56), (0.08, 0.62), (0.20, 0.61), (0.34, 0.51), (0.45, 0.42), (0.51, 0.43),
                   (0.57, 0.40), (0.66, 0.53), (0.74, 0.49), (0.86, 0.29), (0.95, 0.21), (1.00, 0.20)]
_MALE_CHEST_SIDE = [(0.42, -0.50), (0.80, -0.18), (1.34, 0.04), (1.70, 0.45), (1.50, 1.10), (1.30, 1.85)]
_MALE_PELVIS_SIDE = [(1.10, -2.18), (1.10, -1.62), (1.17, -0.95), (1.26, -0.34), (1.31, 0.24), (1.26, 0.66),
                     (0.56, 0.86)]
_MALE_CHEST_DEPTH = [(0.55, 0.58), (0.70, 0.78), (0.84, 0.86), (0.98, 0.92), (0.96, 0.86), (0.84, 0.76)]
_MALE_PELVIS_DEPTH = [(0.72, 0.64), (0.72, 0.66), (0.74, 0.78), (0.74, 0.94), (0.70, 0.98), (0.62, 0.84),
                      (0.50, 0.60)]
_MALE_HIP_CAP = (0.66, 0.20, 0.62, 0.72)
# Pectoral outline in the chest frame (right side): sternum, collarbone, armpit, lower edge.
_PEC = [(0.07, 0.52), (0.55, 0.36), (1.06, 0.52), (1.22, 0.92), (1.02, 1.48), (0.50, 1.66), (0.08, 1.54)]
_PEC_CHEST_MARK = (0.66, 1.30)


@dataclass(frozen=True)
class _Build:
    shoulder: tuple
    hip: tuple
    neck_width: float
    arm: tuple                    # (outer, inner) contour tables
    leg: tuple
    chest: list
    pelvis: list
    chest_depth: list
    pelvis_depth: list
    hip_cap: tuple


_BUILDS = {
    'female': _Build(_SHOULDER, _HIP, _NECK_WIDTH, (_ARM_OUTER, _ARM_INNER), (_LEG_OUTER, _LEG_INNER),
                     _CHEST_SIDE, _PELVIS_SIDE, _CHEST_DEPTH, _PELVIS_DEPTH, _HIP_CAP),
    'male': _Build(_MALE_SHOULDER, _MALE_HIP, _MALE_NECK_WIDTH, (_MALE_ARM_OUTER, _MALE_ARM_INNER),
                   (_MALE_LEG_OUTER, _MALE_LEG_INNER), _MALE_CHEST_SIDE, _MALE_PELVIS_SIDE, _MALE_CHEST_DEPTH,
                   _MALE_PELVIS_DEPTH, _MALE_HIP_CAP),
}
FEMALE_FACE = FaceSpec(eye_half_height=0.098, lip_fullness=0.7)
MALE_FACE = FaceSpec(skin='#f2d2bd', eye_half_height=0.074, eye_half_width=12.5, eye_slant=0.0, lashes=0.40,
                     brow_weight=1.7, brow_lift=-0.30, brow_color='#3a2c28', lip_color='#c98d84', lip_fullness=0.15,
                     blush=0.0, smile=0.15)
MALE_HAIR = HairSpec(color='#2e2420', bangs='short', bangs_length=-0.52, part=-24.0, length=0.62, volume=0.09,
                     wave=0.1, shine=0.6)
_JAW = {'female': 0.93, 'male': 1.06}


@dataclass
class Pose:
    lean: float = 0.0             # spine lean; + toward screen right
    hip_tilt: float = 0.0         # + drops the screen-right hip
    shoulder_tilt: float = 0.0    # + drops the screen-right shoulder (oppose hip_tilt for contrapposto)
    left_arm: tuple = (-6.0, -1.0)    # (upper arm, forearm) angles of the arm on screen left
    right_arm: tuple = (6.0, 1.0)
    left_leg: tuple = (2.5, 1.0)      # (thigh, shin) angles; knees sit slightly inside the hips
    right_leg: tuple = (-2.5, -1.0)
    left_hand: HandSpec = field(default_factory=HandSpec)
    right_hand: HandSpec = field(default_factory=HandSpec)
    left_foot: float = -0.12      # 0 = toes toward the viewer, -1 = turned fully to screen left, +1 right
    right_foot: float = 0.12
    front_leg: str = None         # which leg overlaps the other ('left' | 'right'); None = the nearer one
    turn: float = 0.0             # body turn about its vertical axis, -60..60; + faces screen right
    head_yaw: float = 0.0
    head_tilt: float = 0.0
    neck: float = 0.0             # neck angle relative to the spine
    roll: float = 0.0             # turns the whole trunk (pelvis, spine, chest, head); 90 = lying, head to screen right


@dataclass
class Physique:
    bust: float = 1.0             # breast size scale
    waist: float = 1.0            # width scales
    hips: float = 1.0
    shoulders: float = 1.0
    limbs: float = 1.0            # arm and leg thickness
    gloss: float = 0.35           # soft sheen on the lit side of the skin


@dataclass
class Figure:
    pelvis: tuple                 # px; center of the hip-joint line
    height: float                 # px; crown to sole when standing straight
    pose: Pose = field(default_factory=Pose)
    physique: Physique = field(default_factory=Physique)
    face: FaceSpec = None         # None = FEMALE_FACE or MALE_FACE
    hair: HairSpec = None         # None = long hair (female) or MALE_HAIR
    look: Look = field(default_factory=lambda: ILLUSTRATION)
    jaw: float = None             # Head.jaw; None = 0.93 (slim, female) or 1.06 (broad, male)
    body_details: bool = True     # chest marks, navel, body creases (turn off under full clothing)
    sex: str = 'female'           # 'female' | 'male': body build, face and hair defaults

    def __post_init__(self):
        if self.sex not in _BUILDS:
            raise ValueError(f"sex must be 'female' or 'male', not {self.sex!r}")
        male = self.sex == 'male'
        if self.face is None:
            self.face = replace(MALE_FACE if male else FEMALE_FACE)
        if self.hair is None:
            self.hair = replace(MALE_HAIR) if male else HairSpec()
        if self.jaw is None:
            self.jaw = _JAW[self.sex]

    @property
    def build(self):
        return _BUILDS[self.sex]

    @property
    def unit(self):
        return self.height / HEIGHT_UNITS


class _Frame:
    """A rotated local coordinate frame (chest or pelvis) in head units, with the body's turn.

    x: across the body (+ = screen right when the body faces the viewer), y: down,
    z: forward out of the body's front. pt(x, y, z) turns the point with the body and places it.
    """

    def __init__(self, origin, angle_deg, unit, turn_deg=0.0, profile=None):
        self.angle = angle_deg
        a = np.radians(angle_deg)
        self.origin, self.unit = np.asarray(origin, np.float64), unit
        self.x_axis = np.array([np.cos(a), np.sin(a)])
        self.y_axis = np.array([-np.sin(a), np.cos(a)])
        t = np.radians(turn_deg)
        self.turn, self.cos, self.sin = turn_deg, float(np.cos(t)), float(np.sin(t))
        self.profile = profile            # (ys, half widths, front depths, back depths) of the body in this frame

    def place(self, x, y):
        """A point whose x is already as seen on screen (turn applied)."""
        return self.origin + self.unit * (x * self.x_axis + y * self.y_axis)

    def pt(self, x, y, z=0.0):
        return self.place(x * self.cos + z * self.sin, y)

    def pts(self, points):
        return np.array([self.pt(*point) for point in points])

    def depth(self, x, z=0.0):
        """How far toward the viewer a body point sits after the turn (larger = nearer)."""
        return -x * self.sin + z * self.cos

    def _section(self, y):
        ys, widths, fronts, backs = self.profile
        return np.interp(y, ys, widths), np.interp(y, ys, fronts), np.interp(y, ys, backs)

    def front_z(self, x, y):
        """Depth of the body's front surface at (x, y): an elliptical section of the profile."""
        if self.profile is None:
            return 0.0
        width, front, _ = self._section(y)
        return float(front * np.sqrt(max(0.0, 1.0 - (x / max(width, 1e-6)) ** 2)))

    def back_z(self, x, y):
        """Depth of the body's back surface at (x, y) (negative: behind the center line)."""
        if self.profile is None:
            return 0.0
        width, _, back = self._section(y)
        return -float(back * np.sqrt(max(0.0, 1.0 - (x / max(width, 1e-6)) ** 2)))

    def surface(self, x, y, lift=0.0):
        """Point on the front of the body (for navel, collarbones, straps): follows the turn."""
        return self.pt(x, y, self.front_z(x, y) + lift)

    def surface_pts(self, points, lift=0.0):
        return np.array([self.surface(x, y, lift) for x, y in points])

    def back_surface(self, x, y, lift=0.0):
        """Point on the back of the body (spine, shoulder blades)."""
        return self.pt(x, y, self.back_z(x, y) - lift)

    def back_surface_pts(self, points, lift=0.0):
        return np.array([self.back_surface(x, y, lift) for x, y in points])

    def facing(self, x, y, back=False):
        """How squarely a surface point faces the viewer: 1 head-on, 0 on the silhouette, < 0 hidden."""
        if self.profile is None:
            return self.cos if not back else -self.cos
        width, front, rear = self._section(y)
        depth = rear if back else front
        z = (self.back_z(x, y) if back else self.front_z(x, y))
        normal = np.array([x / max(width, 1e-6) ** 2, z / max(depth, 1e-6) ** 2])
        normal = normal / max(np.linalg.norm(normal), 1e-9)
        return float(-normal[0] * self.sin + normal[1] * self.cos)

    def extent(self, half_width, front, back):
        """Screen-right and screen-left silhouette distances of a cross-section after the turn."""
        right_depth, left_depth = (front, back) if self.sin >= 0 else (back, front)
        c, s = abs(self.cos), abs(self.sin)
        return float(np.hypot(half_width * c, right_depth * s)), float(np.hypot(half_width * c, left_depth * s))

    def round_pts(self, points, front=0.8, back=None):
        """Outline points of a round form (a skirt, a hip) given by its half-widths: x > 0 is the
        screen-right edge, x < 0 the left. front/back: depth as a share of the half-width."""
        back = front if back is None else back
        placed = []
        for x, y in points:
            right, left = self.extent(abs(x), front * abs(x), back * abs(x))
            placed.append(self.place(right if x >= 0 else -left, y))
        return np.array(placed)


def _direction(angle_deg):
    a = np.radians(angle_deg)
    return np.array([np.sin(a), np.cos(a)])


def _upward(lean_deg):
    """Unit vector pointing up the screen, leaning toward screen right by lean_deg."""
    a = np.radians(lean_deg)
    return np.array([np.sin(a), -np.cos(a)])


def aim(turn, upper, lower):
    """Limb angles and lengths for a limb pointing in 3D, for Pose arms and legs.

    turn: the body's turn (Pose.turn). upper, lower: directions (x, y, z) of the two segments in the
    body's own frame: x across the body toward screen right (when facing the viewer), y down,
    z forward out of the chest. Returns (upper angle, lower angle, upper length, lower length), lengths as a
    share of full length: a thigh pointing at the viewer comes out short. The result also carries
    `.forward`, how far each segment comes toward the viewer per unit of its length (the rig uses it to
    tell whether a far arm reaching forward passes in front of the body).

    Example - seated, body turned 40 degrees, knees forward, shins down:
        Pose(turn=40, left_leg=aim(40, (-0.1, 0.15, 1), (0, 1, 0.1)), ...)
    """
    t = np.radians(turn)
    result_angles, result_lengths, result_depths = [], [], []
    for direction in (upper, lower):
        x, y, z = np.asarray(direction, np.float64) / max(np.linalg.norm(direction), 1e-9)
        screen_x = x * np.cos(t) + z * np.sin(t)
        result_angles.append(float(np.degrees(np.arctan2(screen_x, y))))
        result_lengths.append(float(max(np.hypot(screen_x, y), 0.18)))
        result_depths.append(float(z * np.cos(t) - x * np.sin(t)))
    return AimedLimb(result_angles + result_lengths, forward=tuple(result_depths))


class AimedLimb(tuple):
    """aim()'s 4-tuple (it unpacks and compares as one) with the segments' depth toward the viewer."""

    def __new__(cls, values, forward=None):
        limb = super().__new__(cls, values)
        limb.forward = forward
        return limb


def _segments(limb):
    """(upper angle, lower angle, upper length share, lower length share) from a 2- or 4-tuple."""
    limb = tuple(limb)
    return limb if len(limb) == 4 else limb[:2] + (1.0, 1.0)


def _wrist_forward(limb):
    """Head units the wrist sits toward the viewer from the shoulder (None: the pose gives no depth)."""
    forward = getattr(limb, 'forward', None)
    return None if forward is None else _UPPER_ARM * forward[0] + _FOREARM * forward[1]


def _point_3d(frame, x, y, z):
    """A frame point as screen px plus depth px toward the viewer."""
    return np.array([*frame.pt(x, y, z), frame.depth(x, z) * frame.unit])


def _direction_3d(frame, x, y, z):
    """A body-frame direction in the same axes as _point_3d."""
    screen = (x * frame.cos + z * frame.sin) * frame.x_axis + y * frame.y_axis
    return np.array([*screen, frame.depth(x, z)])


def _pocket_arm(figure, chest, pelvis, side, pocket):
    """Arm segments (upper angle, lower angle, upper share, lower share) that put the wrist into a pocket.

    Fixed arm angles miss the pocket once the build or the turn changes (a man's broad shoulders over
    narrow hips leave the wrist in the air). Two-bone inverse kinematics in 3D instead: from the shoulder
    to the pocket on the hip surface, the elbow bending out and back (law of cosines)."""
    unit, build, phys = chest.unit, figure.build, figure.physique
    share, y, lift = _POCKETS[pocket]
    x = side * share * float(np.interp(y, pelvis.profile[0], pelvis.profile[1]))
    # The frame's profile is the unscaled build; the painted hips are scaled by the physique.
    target = _point_3d(pelvis, x * phys.hips, y, (pelvis.front_z(x, y) + lift) * phys.hips)
    shoulder = _point_3d(chest, side * build.shoulder[0] * phys.shoulders, build.shoulder[1], _SHOULDER_Z)
    upper, lower = _UPPER_ARM * unit, _FOREARM * unit
    along = target - shoulder
    distance = float(np.linalg.norm(along))
    along = along / max(distance, 1e-9)
    distance = float(np.clip(distance, abs(upper - lower) + 1e-3 * unit, _REACH_SLACK * (upper + lower)))
    pole = _direction_3d(chest, side * _ELBOW_POLE[0], _ELBOW_POLE[1], _ELBOW_POLE[2])
    pole = pole - np.dot(pole, along) * along
    pole = pole / max(np.linalg.norm(pole), 1e-9)
    to_elbow = (upper ** 2 + distance ** 2 - lower ** 2) / (2.0 * distance)    # along the shoulder-wrist line
    elbow = shoulder + along * to_elbow + pole * np.sqrt(max(upper ** 2 - to_elbow ** 2, 0.0))
    wrist = shoulder + along * distance
    segments = []
    for start, end, length in ((shoulder, elbow, upper), (elbow, wrist, lower)):
        dx, dy = end[:2] - start[:2]
        segments.append((float(np.degrees(np.arctan2(dx, dy))), float(np.hypot(dx, dy) / length)))
    (upper_angle, upper_share), (lower_angle, lower_share) = segments
    return upper_angle, lower_angle, upper_share, lower_share


def _profile(points, depths):
    ys = np.array([y for _, y in points])
    order = np.argsort(ys)
    widths = np.array([x for x, _ in points])
    fronts = np.array([front for front, _ in depths])
    backs = np.array([back for _, back in depths])
    return ys[order], widths[order], fronts[order], backs[order]


def _hand_orientation(view, side, chest, direction_deg):
    """Where a hand's thumb and palm point once the body turns: (thumb side on screen, HandOrientation,
    face toward the viewer). view sets the palm in the body frame: 'back' faces it backward and 'palm'
    forward (both flat from the front), 'rest' toward the thigh as a hanging hand rests."""
    angle = np.radians(direction_deg)
    along = np.array([np.sin(angle), np.cos(angle), 0.0])          # screen x right, y down, z to the viewer
    across = np.array([np.cos(angle), -np.sin(angle), 0.0])
    toward_viewer = np.array([0.0, 0.0, 1.0])
    if view == 'rest':
        tilt = np.radians(_REST_PALM_TILT)
        palm = np.array([-side * np.cos(tilt), 0.0, -np.sin(tilt)])
    else:
        palm = np.array([0.0, 0.0, 1.0 if view == 'palm' else -1.0])
    palm = np.array([palm[0] * chest.cos + palm[2] * chest.sin, palm[1], -palm[0] * chest.sin + palm[2] * chest.cos])
    palm = palm - np.dot(palm, along) * along                       # the hand hangs in the picture plane
    norm = np.linalg.norm(palm)
    palm = palm / norm if norm > 1e-6 else -toward_viewer
    # Each hand keeps its handedness; 'palm' keeps the thumb inward at the front, as before.
    thumb = (side if view != 'palm' else -side) * np.cross(along, palm)
    thumb_across = float(np.dot(thumb, across))
    thumb_side = 1.0 if thumb_across >= 0.0 else -1.0
    orientation = HandOrientation(across=abs(thumb_across), palm=float(np.dot(palm, across)) * thumb_side,
                                  thumb_depth=float(np.dot(thumb, toward_viewer)),
                                  palm_depth=float(np.dot(palm, toward_viewer)))
    return thumb_side, orientation, 'palm' if orientation.palm_depth > 0.0 else 'back'


def _turn_of(pose):
    """Body turn wrapped to -180..180."""
    return float((pose.turn + 180.0) % 360.0 - 180.0)


def seen_from_behind(pose):
    """True when the body turns its back to the viewer (front hidden)."""
    return -np.cos(np.radians(_turn_of(pose))) > _BACK_VIEW


def far_side(pose):
    """'right' or 'left': the side turned away from the viewer, or None when seen square on
    (from the front or from behind)."""
    turn = _turn_of(pose)
    if abs(turn) <= _FAR_SIDE_TURN or abs(turn) >= 180.0 - _FAR_SIDE_TURN:
        return None
    return 'right' if turn > 0 else 'left'


def under_bust(figure):
    """Chest-frame y of the fold under the breasts, where a bikini string or the hem of a cup sits."""
    return _BREAST_CENTER[1] + _BREAST_LOW * _BREAST_RADIUS * figure.physique.bust + _FOLD_GAP


def in_pocket(pose, name):
    """True when the hand on screen side name ('left' | 'right') is in a pocket (HandSpec 'pocket' or 'pouch')."""
    return getattr(pose, f'{name}_hand').pose in _POCKETS


def _front_leg(pose):
    if pose.front_leg is not None:
        return pose.front_leg
    far = far_side(pose)
    return 'right' if far is None else ('left' if far == 'right' else 'right')


@dataclass
class Skeleton:
    """Joint positions (px) and frames of a posed figure. Use it to place clothes and props."""
    unit: float
    pelvis: _Frame
    chest: _Frame
    joints: dict
    head: Head

    @property
    def chest_angle(self):
        return self.chest.angle

    @property
    def pelvis_angle(self):
        return self.pelvis.angle


def build_skeleton(figure):
    pose, unit = figure.pose, figure.unit
    turn = _turn_of(pose)
    build = figure.build
    pelvis = _Frame(figure.pelvis, pose.roll + pose.hip_tilt, unit, turn, _profile(build.pelvis, build.pelvis_depth))
    pit = pelvis.origin + unit * _SPINE * _upward(pose.roll + pose.lean)
    chest = _Frame(pit, pose.roll + pose.shoulder_tilt, unit, turn, _profile(build.chest, build.chest_depth))
    neck_base = chest.pt(0.0, 0.0, _NECK_Z)
    neck_top = neck_base + unit * _NECK * _upward(pose.roll + pose.lean * 0.5 + pose.neck)
    neck_top = neck_top + chest.x_axis * unit * _HEAD_FORWARD * chest.sin
    joints = dict(pit=pit, neck_base=neck_base, neck_top=neck_top)
    for side, name, arm, leg in ((-1, 'left', pose.left_arm, pose.left_leg), (1, 'right', pose.right_arm, pose.right_leg)):
        arm, leg = _segments(arm), _segments(leg)
        if in_pocket(pose, name):                  # the wrist goes into the pocket, whatever the arm angles say
            arm = _pocket_arm(figure, chest, pelvis, side, getattr(pose, f'{name}_hand').pose)
        shoulder = chest.pt(side * build.shoulder[0] * figure.physique.shoulders, build.shoulder[1], _SHOULDER_Z)
        elbow = shoulder + unit * _UPPER_ARM * arm[2] * _direction(arm[0])
        wrist = elbow + unit * _FOREARM * arm[3] * _direction(arm[1])
        hip = pelvis.pt(side * build.hip[0] * figure.physique.hips, build.hip[1], _HIP_Z)
        knee = hip + unit * _THIGH * leg[2] * _direction(leg[0])
        ankle = knee + unit * _SHIN * leg[3] * _direction(leg[1])
        joints.update({f'{name}_shoulder': shoulder, f'{name}_elbow': elbow, f'{name}_wrist': wrist,
                       f'{name}_hip': hip, f'{name}_knee': knee, f'{name}_ankle': ankle})
    head = Head(center=tuple(neck_top - (0.0, 0.80 * unit)), size=2.0 * unit, yaw=pose.head_yaw,
                tilt=pose.roll + pose.head_tilt + pose.lean * 0.5, jaw=figure.jaw)
    return Skeleton(unit, pelvis, chest, joints, head)


def _torso_outline(figure, skeleton):
    """Silhouette of the torso: each outline height is a cross-section seen at the body's turn."""
    phys, build = figure.physique, figure.build
    chest = [(x * (phys.shoulders if x > 1.0 else 1.0), y, front, back)
             for (x, y), (front, back) in zip(build.chest, build.chest_depth)]
    scale = [phys.waist, 0.7 * phys.waist + 0.3 * phys.hips, 0.3 * phys.waist + 0.7 * phys.hips, phys.hips,
             phys.hips, phys.hips, 1.0]
    pelvis = [(x * k, y, front * k, back * k) for (x, y), (front, back), k in zip(build.pelvis, build.pelvis_depth, scale)]
    right, left = [], []
    for frame, section in ((skeleton.chest, chest), (skeleton.pelvis, pelvis)):
        for x, y, front, back in section:
            to_right, to_left = frame.extent(x, front, back)
            right.append(frame.place(to_right, y))
            left.append(frame.place(-to_left, y))
    return np.vstack([np.array(right), np.array(left)[::-1]])


def _resample(table):
    t, d = np.array(table).T
    return np.interp(_TABLE_SAMPLES, t, d)


def _limb(cv, points, outer, inner, unit, scale, screen_side, side_view=None, turn_sin=0.0):
    """Arm or leg along its joints. screen_side: -1 for the limb on screen left, +1 for screen right.

    side_view: optional (front, back) tables of the limb seen from the side; blended in as the body
    turns toward profile (turn_sin = sin of the turn), so a profile leg gets its calf at the back.
    """
    # Walking from the root joint outward, the left-hand side is the outer side of a screen-right limb.
    left, right = (outer, inner) if screen_side > 0 else (inner, outer)
    left, right = _resample(left), _resample(right)
    if side_view is not None and abs(turn_sin) > 1e-3:
        front, back = _resample(side_view[0]), _resample(side_view[1])
        # Facing screen right, the front of a downward limb is on its left-hand side.
        side_left, side_right = (front, back) if turn_sin > 0 else (back, front)
        k = turn_sin * turn_sin
        left, right = (1.0 - k) * left + k * side_left, (1.0 - k) * right + k * side_right
    to_px = lambda widths: list(zip(_TABLE_SAMPLES, widths * scale * unit))     # noqa: E731
    return cv.contour(points, to_px(left), to_px(right), bend=_JOINT_BEND * unit)


def _foot(cv, ankle, shin_angle, turn, unit, inner_side, behind=0.0):
    """Foot at the end of the shin: a blend of its front view and its side view, with toes.

    inner_side: +1 if the big toe is toward screen right in the front view, -1 if left.
    behind: 0..1, how far the figure has its back to the viewer; the front view becomes a heel.
    """
    amount = min(abs(turn), 1.0)
    facing = -1.0 if turn < 0 else 1.0
    frame = _Frame(ankle, -shin_angle, unit)
    end_on = np.array(_FOOT_FRONT) * (1.0 - behind) + np.array(_FOOT_HEEL) * behind
    # Both outlines are mirrored together (the front one is symmetric) so their points keep
    # corresponding: blending a mirrored side view into an unmirrored front view would fold the sole.
    sole = (end_on * (1.0 - amount) + np.array(_FOOT_SIDE) * amount) * [facing, 1.0]
    front_toes = np.array(_TOES_FRONT) * [inner_side, 1.0]
    side_toes = np.array(_TOES_SIDE) * [facing, 1.0]
    toes = front_toes * (1.0 - amount) + side_toes * amount
    mask = cv.blob(frame.pts(sole))
    if amount < 0.5 and behind > 0.5:              # seen from behind the toes hide in front of the heel
        return mask
    for (x, y), radius in zip(toes, _TOE_RADII):
        cx, cy = frame.pt(x, y)
        mask = np.maximum(mask, cv.ellipse(cx, cy, radius * unit, radius * 1.15 * unit, -shin_angle))
    return mask


def _breast_center(chest, side, size):
    """Screen-space x (in the chest frame) and y of a breast's center, after the body's turn."""
    cx, cy = side * _BREAST_CENTER[0], _BREAST_CENTER[1]
    z = chest.front_z(cx, cy) + _BREAST_LIFT * size
    return cx * chest.cos + z * chest.sin, cy


def _breast(cv, chest, side, size, far=False):
    r = _BREAST_RADIUS * size
    sx, sy = _breast_center(chest, side, size)
    outline = [(-side * 0.15, -1.15), (side * 0.80, -0.55), (side * 1.02, 0.10), (side * 0.74, 0.80),
               (side * 0.05, 1.02), (-side * 0.66, 0.72), (-side * 0.92, 0.05), (-side * 0.70, -0.65)]
    points = np.array([chest.place(sx + dx * r, sy + dy * r) for dx, dy in outline])
    mask = cv.blob(points)
    if far:
        # Seen from the side the breast's upper slope runs straight down from the chest to the
        # chest mark: wrap the round shape and a point high on the chest wall in one convex outline.
        anchor = chest.surface(side * 0.55, sy - _BREAST_SLOPE * r)
        hull = cv2.convexHull(np.vstack([points, [anchor]]).astype(np.float32))[:, 0, :]
        upper = cv.polygon(hull) * cv.polygon(np.array([chest.place(-9.0, -9.0), chest.place(9.0, -9.0),
                                                        chest.place(9.0, sy), chest.place(-9.0, sy)]))
        mask = np.maximum(mask, upper)
    if far:                       # the upper slope melts into the chest wall
        root, reach = chest.place(sx - side * 0.10 * r, sy - 1.55 * r), 2.4 * r
    else:
        root, reach = chest.place(sx - side * 0.25 * r, sy - 0.95 * r), 1.75 * r
    return Part(mask, 0.62 * r * chest.unit, tuple(root), reach * chest.unit, shadow=0.8)


def _pec(cv, chest, side, size, far=False):
    """Pectoral muscle: a flat plate from the sternum to the armpit with a clear lower edge.
    The top fades into the chest; only the lower edge turns and casts a soft shadow."""
    cx, cy = 0.6, 1.0
    outline = [(side * (cx + (x - cx) * size), cy + (y - cy) * size) for x, y in _PEC]
    mask = cv.blob(chest.surface_pts(outline, lift=0.05))
    root = chest.surface(side * 0.50, 0.30)
    lower_edge = cv.polygon(np.array([chest.place(-9.0, 1.15), chest.place(9.0, 1.15), chest.place(9.0, 9.0),
                                      chest.place(-9.0, 9.0)]))
    # Only the lower edge is a fold; the top and the sides grow out of the chest without a line.
    return Part(mask, 0.42 * chest.unit, tuple(root), (1.75 if far else 1.55) * chest.unit, shadow=0.6,
                line_mask=lower_edge)


def _chest_mark(chest, side, size):
    """Chest mark position on the breast's front, following the turn."""
    r = _BREAST_RADIUS * size
    sx, sy = _breast_center(chest, side, size)
    return chest.place(sx + side * 0.10 * r * chest.cos + 0.85 * r * chest.sin, sy + 0.22 * r)


def _seat_mass(cv, figure, skeleton, outline):
    """Seated: the buttocks and the tops of the thighs form one mass resting on the seat.

    When a thigh swings out toward the horizontal, the lower pelvis and the thigh roots are
    wrapped in one convex outline, so the underside runs smoothly from buttock to thigh.
    Returns that mask, or None for standing poses.
    """
    unit, joints, pelvis = skeleton.unit, skeleton.joints, skeleton.pelvis
    points = []
    for name in ('left', 'right'):
        hip, knee = joints[f'{name}_hip'], joints[f'{name}_knee']
        thigh = knee - hip
        swing = abs(np.degrees(np.arctan2(thigh[0], thigh[1])) - pelvis.angle)
        if swing < _SEATED_SWING:
            continue
        across = np.array([-thigh[1], thigh[0]]) / max(np.linalg.norm(thigh), 1e-6)
        for t in (0.0, 0.15, 0.3, 0.5):
            center = hip + thigh * t
            points += [center + across * _SEAT_THIGH * unit, center - across * _SEAT_THIGH * unit]
    if not points:
        return None
    hip_line = pelvis.origin
    lower = [p for p in outline if np.dot(p - hip_line, pelvis.y_axis) > -0.3 * unit]
    hull = cv2.convexHull(np.vstack([np.array(points), np.array(lower)]).astype(np.float32))[:, 0, :]
    return cv.polygon(hull)


def build_body(cv, figure, skeleton):
    """All skin parts back to front. Returns (parts, masks by name, hand detail data)."""
    unit, joints, phys = skeleton.unit, skeleton.joints, figure.physique
    pose = figure.pose
    masks, parts, hands = {}, [], []

    def add(name, mask, bulge, root=None, root_radius=0.0, shadow=1.0, overlay=True, line_mask=None, shape=None):
        masks[name] = mask
        parts.append(Part(mask, bulge * unit, None if root is None else tuple(root), root_radius * unit, shadow,
                          overlay, line_mask, shape))

    outline = _torso_outline(figure, skeleton)
    torso = cv.blob(outline)
    # Round off any kink where the tilted ribcage meets the pelvis: flesh folds, it does not crease.
    torso = raster.smoothstep(raster.blur(torso, _WAIST_SMOOTHING * unit), 0.42, 0.58)
    cap_x, cap_y, cap_rx, cap_ry = figure.build.hip_cap
    pelvis = skeleton.pelvis
    cap_width = cap_rx * phys.hips * unit * np.hypot(pelvis.cos, _HIP_CAP_DEPTH * pelvis.sin)
    caps = []
    for side in (-1, 1):                        # keeps the hip line continuous however the pelvis tilts
        center = pelvis.pt(side * cap_x * phys.hips, cap_y)
        torso = np.maximum(torso, cv.ellipse(center[0], center[1], cap_width, cap_ry * unit, skeleton.pelvis_angle))
        angles = np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False)
        caps += [center + cap_width * np.cos(a) * pelvis.x_axis + cap_ry * unit * np.sin(a) * pelvis.y_axis
                 for a in angles]
    seat = _seat_mass(cv, figure, skeleton, np.vstack([outline, caps]))
    if seat is not None:
        torso = np.maximum(torso, seat)
    add('torso', torso, 0.55, overlay=False)
    below_torso = 1.0 - masks['torso']          # leg-against-leg lines belong below the lower pelvis only
    neck = cv.ribbon([joints['neck_base'], joints['neck_top']], figure.build.neck_width * unit, [1.12, 0.98, 1.0], smooth=False)
    add('neck', neck, 0.26, joints['neck_base'], 1.05, shadow=0.0, overlay=False, line_mask=cv.empty())
    front_leg = _front_leg(pose)
    far = far_side(pose)
    turn_sin, turn_cos = skeleton.pelvis.sin, skeleton.pelvis.cos
    foot_follow = turn_sin * _FOOT_FOLLOW
    behind = float(np.clip(-turn_cos * 1.6, 0.0, 1.0))
    leg_ratio = np.mean([d for _, d in figure.build.leg[0]]) / np.mean([d for _, d in _LEG_OUTER])
    side_legs = ([(t, d * leg_ratio) for t, d in _LEG_SIDE_FRONT], [(t, d * leg_ratio) for t, d in _LEG_SIDE_BACK])
    order = ('left', 'right') if front_leg == 'right' else ('right', 'left')
    for name in order:
        side = -1 if name == 'left' else 1
        leg = _limb(cv, [joints[f'{name}_hip'], joints[f'{name}_knee'], joints[f'{name}_ankle']],
                    *figure.build.leg, unit, phys.limbs * phys.hips ** 0.7, side, side_legs, turn_sin)
        foot_turn = float(np.clip(getattr(pose, f'{name}_foot') + foot_follow, -1.0, 1.0))
        shin = joints[f'{name}_ankle'] - joints[f'{name}_knee']
        shin_angle = float(np.degrees(np.arctan2(shin[0], shin[1])))
        foot = _foot(cv, joints[f'{name}_ankle'], shin_angle, foot_turn,
                     unit, inner_side=1.0 if name == 'left' else -1.0, behind=behind)
        # The leg is shaded together with its foot, so the ankle reads as a joint, not a ball.
        add(f'{name}_leg', leg, _LEG_BULGE * phys.limbs, joints[f'{name}_hip'], 2.0, shadow=0.7,
            overlay=name == front_leg, line_mask=below_torso, shape=np.maximum(leg, foot))
        feet_so_far = [masks[key] for key in ('left_foot', 'right_foot') if key in masks]
        if feet_so_far:                 # a shin passing a foot leaves no round shadow on it
            parts[-1].shadow_clip = 1.0 - raster.grow(np.maximum.reduce(feet_so_far), 0.1 * unit)
        no_ledge = 1.0 - cv.radial(joints[f'{name}_ankle'], _ANKLE_CLEAR * unit) ** 0.3   # no line across the instep
        add(f'{name}_foot', foot, 0.20, joints[f'{name}_ankle'], _FOOT_BLEND, shadow=0.0, line_mask=no_ledge)
    sides = ((1, 'right'), (-1, 'left')) if far == 'right' else ((-1, 'left'), (1, 'right'))
    chest_form = _pec if figure.sex == 'male' else _breast
    for side, name in sides:                       # the far breast first, so the near one overlaps it
        breast = chest_form(cv, skeleton.chest, side, phys.bust, far=name == far)
        if turn_cos < 0.0:                         # turned away: only what shows past the back's outline
            breast.shape, breast.mask = breast.mask, breast.mask * (1.0 - masks['torso'])
        masks[f'{name}_breast'] = breast.mask
        parts.append(breast)
    body_front = np.maximum.reduce([masks['torso'], masks['left_breast'], masks['right_breast'], masks['neck']])
    # The far arm first: where the two hands meet at the side (a profile), the near one is in front.
    arms = ((1, 'right'), (-1, 'left')) if far == 'right' else ((-1, 'left'), (1, 'right'))
    behind_far_arm = body_front
    if skeleton.chest.cos < 0.0:                   # turned away, the far hand hangs behind the hips and legs too
        behind_far_arm = np.maximum.reduce([body_front, masks['left_leg'], masks['right_leg']])
    for side, name in arms:
        arm = _limb(cv, [joints[f'{name}_shoulder'], joints[f'{name}_elbow'], joints[f'{name}_wrist']],
                    *figure.build.arm, unit, phys.limbs, side)
        hidden = behind_far_arm if name == far else 0.0  # the far arm passes behind the body
        hand_hidden = hidden
        forward = _wrist_forward(getattr(pose, f'{name}_arm'))
        if name == far and forward is not None and forward > _IN_FRONT and not in_pocket(pose, name):
            # Reaching forward (hugging the knees, holding a cup), the far forearm and hand come round in
            # front of the body; only the upper arm along the far flank stays hidden.
            forearm_zone = cv.ribbon([joints[f'{name}_elbow'], joints[f'{name}_wrist']], 1.6 * unit, 'flat',
                                     smooth=False)
            hidden = hidden * (1.0 - forearm_zone)
            hand_hidden = 0.0
        add(f'{name}_arm', arm * (1.0 - hidden), _ARM_BULGE * phys.limbs, joints[f'{name}_shoulder'], 1.25,
            shape=arm if name == far else None)
        forearm = joints[f'{name}_wrist'] - joints[f'{name}_elbow']
        forearm_angle = float(np.degrees(np.arctan2(forearm[0], forearm[1])))
        spec = getattr(pose, f'{name}_hand')
        if in_pocket(pose, name):                  # in a pocket: the garment is drawn over the wrist
            pocket = cv.ellipse(*joints[f'{name}_wrist'], _POCKET * unit, _POCKET * unit)
            masks['pocket'] = np.maximum(masks.get('pocket', cv.empty()), pocket)
            masks[f'{name}_hand'] = cv.empty()
            continue
        thumb_side, orientation, face = _hand_orientation(spec.view, side, skeleton.chest, forearm_angle)
        hand_parts, details = build_hand(cv, joints[f'{name}_wrist'], forearm_angle, _HAND * unit,
                                         replace(spec, view=face), thumb_side=thumb_side, orientation=orientation)
        hand_mask = cv.empty()
        for part in hand_parts:
            if name == far:
                # What peeks past the body edge as a hairline strip reads as a glitch: keep only real pieces.
                visible = part.mask * (1.0 - hand_hidden)
                sliver = _HAND_SLIVER * _HAND * unit
                part.shape, part.mask = part.mask, raster.grow(raster.grow(visible, -sliver), sliver) * visible
            hand_mask = np.maximum(hand_mask, part.mask)
        masks[f'{name}_hand'] = hand_mask
        parts.extend(hand_parts)
        details['visible'] = 1.0 - hand_hidden if name == far else None   # nails and creases stay off the body
        details['name'] = name
        hands.append(details)
    far_hand = [details for details in hands if details['name'] == far]
    if far_hand:                                   # nor on the near arm and hand, painted over the far ones
        near = 'left' if far == 'right' else 'right'
        details = far_hand[0]
        details['visible'] = details['visible'] * (1.0 - np.maximum(masks[f'{near}_arm'], masks[f'{near}_hand']))
        details['palm_only'] = details['palm_only'] * details['visible']    # palm creases follow palm_only
    return parts, masks, hands


def _seen(frame, x, y, back=False):
    """Opacity for a surface mark at (x, y): full where the surface faces the viewer, fading out
    as it turns toward the silhouette, zero beyond it."""
    return float(raster.smoothstep(np.float32(frame.facing(x, y, back)), _MARK_FADE[0], _MARK_FADE[1]))


def _anatomy_details(cv, figure, skeleton, masks, look):
    """Quiet surface cues that make a figure study read as a body: collarbones, the
    center line, navel, hip creases, knees, chest marks; from behind the spine,
    shoulder blades and buttock folds. No pelvic detail."""
    unit, chest, pelvis, joints = skeleton.unit, skeleton.chest, skeleton.pelvis, skeleton.joints
    skin = figure.face.skin
    shade = skin_shadow(skin, look.shade_depth)
    line = skin_line(skin, look)
    torso = masks['torso']
    arms = np.maximum(masks['left_arm'], masks['right_arm'])
    open_torso = torso * (1.0 - arms) * (1.0 - np.maximum(masks['left_hand'], masks['right_hand']))
    soft = max(look.soft_px * 0.5, 0.06 * unit)
    light_side = -1.0 if look.light[0] < 0 else 1.0

    strokes = cv.empty()
    for side in (-1, 1):                               # collarbones and the hollow under them
        bone = chest.surface_pts([(side * 0.10, 0.06), (side * 0.50, -0.01), (side * 1.00, 0.05)])
        seen = _seen(chest, side * 0.50, 0.0)
        strokes = np.maximum(strokes, cv.ribbon(bone, 0.035 * unit, [0.5, 1.0, 0.3]) * seen)
        hollow = cv.ribbon(bone + (0.0, 0.07 * unit), 0.14 * unit, [0.7, 1.0, 0.2])
        cv.tint(raster.blur(hollow, soft) * open_torso, shade, 'normal', 0.35 * seen)
        crease = pelvis.surface_pts([(side * 0.78, -0.42), (side * 0.50, 0.02), (side * 0.22, 0.42)])   # hip to lower pelvis
        cv.tint(raster.blur(cv.ribbon(crease, 0.06 * unit, [0.2, 1.0, 0.7]), soft * 0.8) * open_torso,
                shade, 'normal', 0.28 * _seen(pelvis, side * 0.50, 0.02))
    cv.tint(raster.blur(strokes, 0.4 * look.scale) * open_torso, line, 'normal', 0.5)

    for side in (-1, 1):                               # lower edge of the ribcage, and the waist turning under it
        arch = np.vstack([chest.surface_pts([(side * 0.10, 2.05), (side * 0.52, 2.30)]),
                          pelvis.surface_pts([(side * 0.86, -2.25)])])
        cv.tint(raster.blur(cv.ribbon(arch, 0.16 * unit, [0.3, 1.0, 0.6]), soft * 1.6) * open_torso,
                shade, 'normal', 0.22 * _seen(chest, side * 0.52, 2.30))
    navel = pelvis.surface(0.0, _NAVEL_Y)
    navel_seen = _seen(pelvis, 0.0, _NAVEL_Y)
    center = [chest.surface(0.0, 0.75), chest.surface(0.0, 1.9), pelvis.surface(0.0, _NAVEL_Y - 0.5), navel]
    cv.tint(raster.blur(cv.ribbon(center, 0.10 * unit, [0.3, 0.8, 1.0, 0.5]), soft) * open_torso,
            shade, 'normal', 0.30 * _seen(chest, 0.0, 1.9))
    for side in (-1, 1) if figure.sex != 'male' else ():   # soft belly planes beside the center line
        belly = cv.radial(pelvis.surface(side * 0.36, _NAVEL_Y - 0.55), 0.32 * unit * max(abs(pelvis.cos), 0.5),
                          0.75 * unit)
        cv.tint(belly * open_torso, '#ffffff', 'soft_light', 0.22 * look.highlight * _seen(pelvis, side * 0.36, -1.9))
    if navel_seen > 0:
        hole = cv.ellipse(navel[0], navel[1], 0.045 * unit * max(abs(pelvis.cos), 0.35), 0.10 * unit,
                          figure.pose.roll + figure.pose.hip_tilt)
        cv.tint(raster.blur(hole, 0.012 * unit) * open_torso, adjust(shade, lightness=-0.14, chroma=0.9), 'normal',
                0.85 * navel_seen)
        cv.tint(raster.blur(cv.ellipse(navel[0] - light_side * 0.03 * unit, navel[1] + 0.16 * unit, 0.10 * unit,
                                       0.05 * unit), 0.03 * unit) * open_torso, '#ffffff', 'soft_light', 0.5 * navel_seen)

    lower_pelvis = cv.radial(pelvis.surface(0.0, 0.62), 0.42 * unit, 0.36 * unit)      # shadow where the thighs meet
    legs = np.maximum(masks['left_leg'], masks['right_leg'])
    cv.tint(lower_pelvis * np.maximum(torso, legs) * (1.0 - arms), shade, 'normal', 0.45 * _seen(pelvis, 0.0, 0.62))

    chest_tone = adjust(mix(skin, figure.face.lip_color, 0.50), lightness=-0.03)
    male = figure.sex == 'male'
    if male:
        _male_torso(cv, figure, skeleton, masks, look, open_torso, soft)
    for side, name in ((-1, 'left'), (1, 'right')):
        if male:
            chest_mark, size = chest.surface(side * _PEC_CHEST_MARK[0], _PEC_CHEST_MARK[1], 0.06), 0.62
            visible = open_torso * _seen(chest, side * _PEC_CHEST_MARK[0], _PEC_CHEST_MARK[1])
        else:
            chest_mark, size = _chest_mark(chest, side, figure.physique.bust), 1.0
            visible = masks[f'{name}_breast'] * (1.0 - arms) * _seen(chest, side * 0.62, 1.45)
        cv.tint(raster.blur(cv.ellipse(chest_mark[0], chest_mark[1], 0.115 * size * unit * max(abs(chest.cos), 0.4),
                                       0.105 * size * unit), 0.02 * unit) * visible,
                chest_tone, 'normal', 0.80 if not male else 0.65)
        cv.tint(raster.blur(cv.ellipse(chest_mark[0], chest_mark[1], 0.042 * size * unit), 0.012 * unit) * visible,
                adjust(chest_tone, lightness=-0.08), 'normal', 0.85)
    if pelvis.cos < _BACK_DETAIL_START:
        _back_details(cv, figure, skeleton, masks, look, soft)
    front_knee = float(raster.smoothstep(np.float32(pelvis.cos), -0.1, 0.5))
    back_knee = float(raster.smoothstep(np.float32(-pelvis.cos), 0.1, 0.6))
    for side, name in ((-1, 'left'), (1, 'right')):
        knee = joints[f'{name}_knee']                  # kneecap: light on top, a curved shadow beneath
        leg = masks[f'{name}_leg']
        along = joints[f'{name}_ankle'] - knee
        along = along / max(np.hypot(*along), 1e-6)
        across = np.array([along[1], -along[0]])
        cv.tint(cv.radial(knee - along * 0.12 * unit, 0.32 * unit) * leg, '#ffffff', 'soft_light',
                0.35 * look.highlight * front_knee)
        under = cv.ribbon([knee + along * 0.20 * unit - across * 0.26 * unit, knee + along * 0.34 * unit,
                           knee + along * 0.20 * unit + across * 0.26 * unit], 0.10 * unit, 'taper')
        cv.tint(raster.blur(under, soft * 0.7) * leg, shade, 'normal', 0.50 * front_knee)
        # Back of the knee: a short crease where the calf meets the thigh.
        crease = cv.ribbon([knee + along * 0.06 * unit - across * 0.24 * unit, knee + along * 0.10 * unit,
                            knee + along * 0.06 * unit + across * 0.24 * unit], 0.06 * unit, 'taper')
        cv.tint(raster.blur(crease, soft * 0.6) * leg, shade, 'normal', 0.45 * back_knee)


def _back_details(cv, figure, skeleton, masks, look, soft):
    """Seen from behind: the groove of the spine between its two muscle ridges, the shoulder
    blades, the dimples above the pelvis, the cleft and the folds under the buttocks."""
    unit, chest, pelvis = skeleton.unit, skeleton.chest, skeleton.pelvis
    shade = skin_shadow(figure.face.skin, look.shade_depth)
    male = figure.sex == 'male'
    depth = 1.25 if male else 1.0                  # a man's back carries deeper muscle relief
    arms = np.maximum.reduce([masks[k] for k in ('left_arm', 'right_arm', 'left_hand', 'right_hand')])
    back = masks['torso'] * (1.0 - arms)

    def mark(points, width, opacity, blur_scale=1.0, profile=(0.3, 1.0, 0.5), color=shade, mode='normal'):
        stroke = cv.ribbon(points, width * unit, list(profile))
        cv.tint(raster.blur(stroke, soft * blur_scale) * back, color, mode, opacity)

    spine = np.vstack([chest.back_surface_pts([(0.0, 0.25), (0.0, 1.2), (0.0, 2.2)]),
                       pelvis.back_surface_pts([(0.0, -1.6), (0.0, -0.55)])])
    mark(spine, 0.10, 0.40 * depth * _seen(chest, 0.0, 1.2, back=True), 1.4, (0.2, 0.8, 1.0, 0.8, 0.3))
    for side in (-1, 1):
        ridge = np.vstack([chest.back_surface_pts([(side * 0.22, 1.4), (side * 0.22, 2.3)]),
                           pelvis.back_surface_pts([(side * 0.24, -1.3)])])
        mark(ridge, 0.16, 0.20 * look.highlight * _seen(chest, side * 0.22, 1.8, back=True), 2.0,
             (0.2, 1.0, 0.4), '#ffffff', 'soft_light')
        seen = _seen(chest, side * 0.55, 1.0, back=True)
        blade = chest.back_surface_pts([(side * 0.32, 0.55), (side * 0.40, 1.20), (side * 0.78, 1.62)])
        mark(blade, 0.12, 0.46 * depth * seen, 1.5, (0.3, 1.0, 0.6))
        top = cv.radial(chest.back_surface(side * 0.68, 0.95), 0.36 * unit * max(abs(chest.cos), 0.4), 0.42 * unit)
        cv.tint(top * back, '#ffffff', 'soft_light', 0.30 * look.highlight * seen)
        dimple = pelvis.back_surface(side * 0.30, -0.62)
        dimple_seen = _seen(pelvis, side * 0.30, -0.62, back=True)
        cv.tint(raster.blur(cv.ellipse(dimple[0], dimple[1], 0.07 * unit, 0.05 * unit), soft) * back, shade,
                'normal', (0.25 if male else 0.40) * dimple_seen)
        fold = pelvis.back_surface_pts([(side * 0.12, 0.84), (side * 0.48, 0.92), (side * 0.90, 0.70)])
        legs_and_seat = np.maximum(masks['torso'], np.maximum(masks['left_leg'], masks['right_leg'])) * (1.0 - arms)
        stroke = cv.ribbon(fold, 0.09 * unit, [0.3, 1.0, 0.4])
        cv.tint(raster.blur(stroke, soft) * legs_and_seat, shade, 'normal',
                0.40 * _seen(pelvis, side * 0.48, 0.80, back=True))
        round_ = cv.radial(pelvis.back_surface(side * 0.55, 0.20), 0.45 * unit * max(abs(pelvis.cos), 0.4),
                           0.55 * unit)
        cv.tint(round_ * back, '#ffffff', 'soft_light', 0.25 * look.highlight * _seen(pelvis, side * 0.55, 0.2, True))
    cleft = pelvis.back_surface_pts([(0.0, -0.30), (0.0, 0.30), (0.0, 0.80)])
    mark(cleft, 0.05, 0.55 * _seen(pelvis, 0.0, 0.3, back=True), 0.6, (0.2, 1.0, 0.8))


def _male_torso(cv, figure, skeleton, masks, look, open_torso, soft):
    """Muscle landmarks of a lean male torso, all as soft shadows: the lower edge of the
    pectorals, the rows and edges of the abdominal wall, the iliac furrows running down
    toward the lower pelvis (they stop above it), and the serratus over the ribs."""
    unit, chest, pelvis = skeleton.unit, skeleton.chest, skeleton.pelvis
    shade = skin_shadow(figure.face.skin, look.shade_depth)

    def furrow(points, width, opacity, blur_scale=1.0, profile=(0.3, 1.0, 0.5), facing=1.0):
        stroke = cv.ribbon(points, width * unit, list(profile))
        cv.tint(raster.blur(stroke, soft * blur_scale) * open_torso, shade, 'normal', opacity * facing)

    for side in (-1, 1):
        # Landmarks on the side turning away fade out before they reach the silhouette.
        facing = float(np.clip(1.0 - 1.8 * max(0.0, side * chest.sin), 0.0, 1.0)) * _seen(chest, side * 0.5, 1.5)
        if facing <= 0.0:
            continue
        under_pecs = chest.surface_pts([(side * 1.12, 1.12), (side * 0.96, 1.50), (side * 0.50, 1.66),
                                        (side * 0.10, 1.56)], 0.03)
        furrow(under_pecs, 0.16, 0.45, 1.4, (0.4, 1.0, 1.0, 0.6), facing)
        rectus_edge = np.vstack([chest.surface_pts([(side * 0.56, 2.0)]),
                                 pelvis.surface_pts([(side * 0.50, -2.2), (side * 0.44, -1.1), (side * 0.28, -0.05)])])
        furrow(rectus_edge, 0.10, 0.34, 1.2, facing=facing)
        for row_y in (-2.75, -2.25, -1.78):                                      # rows of the abdominal wall
            row = pelvis.surface_pts([(side * 0.06, row_y + 0.04), (side * 0.24, row_y), (side * 0.42, row_y + 0.05)])
            furrow(row, 0.09, 0.42, 1.0, (0.2, 1.0, 0.4), facing)
            block = cv.radial(pelvis.surface(side * 0.25, row_y + 0.25), 0.20 * unit * max(pelvis.cos, 0.5), 0.24 * unit)
            cv.tint(raster.blur(block, soft) * open_torso, '#ffffff', 'soft_light', 0.12 * look.highlight * facing)
        iliac = pelvis.surface_pts([(side * 0.98, -1.10), (side * 0.62, -0.42), (side * 0.30, 0.22)])
        furrow(iliac, 0.09, 0.38, 1.2, (0.2, 1.0, 0.3), facing)
        for k in range(3):                                                       # serratus over the ribs
            y = 1.62 + 0.20 * k
            furrow(chest.surface_pts([(side * 1.24, y), (side * 1.06, y + 0.14)]), 0.06, 0.16, 0.8, (0.3, 1.0), facing)


def _adams_apple(cv, figure, skeleton, masks, look):
    """A small bump on the front of a man's neck: light on top, shadow under it."""
    unit, joints, chest = skeleton.unit, skeleton.joints, skeleton.chest
    point = joints['neck_base'] + 0.42 * (joints['neck_top'] - joints['neck_base'])
    point = point + chest.x_axis * unit * 0.30 * chest.sin
    neck = masks['neck']
    seen = float(raster.smoothstep(np.float32(chest.cos), -0.1, 0.45))       # it is on the front of the neck
    if seen <= 0.0:
        return
    shade = skin_shadow(figure.face.skin, look.shade_depth)
    cv.tint(raster.blur(cv.ellipse(point[0], point[1] + 0.10 * unit, 0.08 * unit, 0.05 * unit), 0.03 * unit) * neck,
            shade, 'normal', 0.40 * seen)
    cv.tint(cv.radial(point, 0.06 * unit, 0.09 * unit) * neck, '#ffffff', 'soft_light', 0.40 * look.highlight * seen)


def _skin_finish(cv, figure, skeleton, masks, union, look, head_shadow):
    """Head shadow on the neck, warm joints, and a sheen along the lit side."""
    unit, joints = skeleton.unit, skeleton.joints
    skin = figure.face.skin
    shade = skin_shadow(skin, look.shade_depth)
    lx = look.light[0]
    under_chin = shading.cast(head_shadow, np.maximum(masks['neck'], masks['torso']),
                              (-lx * 0.10 * unit, 0.32 * unit), max(look.soft_px, 0.05 * unit))
    cv.tint(under_chin, shade, 'normal', 0.80)
    warm = adjust(mix(skin, figure.face.lip_color, 0.55), lightness=0.02)
    for name in ('left_knee', 'right_knee', 'left_elbow', 'right_elbow', 'left_shoulder', 'right_shoulder'):
        cv.tint(cv.radial(joints[name], 0.42 * unit) ** 1.5 * union, warm, 'normal', 0.16)
    if figure.sex == 'male':
        _adams_apple(cv, figure, skeleton, masks, look)
    if figure.physique.gloss > 0:
        sheen = shading.rim(union, look.light, 0.20 * unit, soft=0.09 * unit)
        cv.tint(sheen, '#ffffff', 'soft_light', figure.physique.gloss * look.highlight)


# Shots for framing(): head units from the crown down to the bottom of the frame.
_SHOTS = {'full': HEIGHT_UNITS + 0.35, 'knee': 12.4, 'thigh': 10.2, 'waist': 8.2, 'bust': 4.9, 'face': 2.7}
_CROWN_TO_PELVIS = 7.6        # crown to the hip-joint line, head units, standing straight


def framing(size, shot='full', center=0.5, headroom=0.55):
    """Zoom on a full figure: where to put it and how tall to make it so that `shot` fills the canvas.

    size: (width, height) of the canvas. shot: 'full' | 'knee' | 'thigh' | 'waist' | 'bust' | 'face'.
    center: horizontal position of the body (0..1). headroom: head units above the crown (hair, margin).
    Returns dict(pelvis=, height=) to unpack into Figure(**framing(...), pose=..., ...).
    The whole body is still built; everything below the frame simply falls off the canvas,
    so one pose serves every shot from full length to a close-up.
    """
    if shot not in _SHOTS:
        raise ValueError(f'unknown shot {shot!r}; choose from {sorted(_SHOTS)}')
    width, height = size
    unit = height / (_SHOTS[shot] + headroom)
    return dict(pelvis=(width * center, (headroom + _CROWN_TO_PELVIS) * unit), height=unit * HEIGHT_UNITS)


_BOUNDS_HEIGHT = 1000.0        # px; figure height at which a pose is measured before scaling it to fit
_HAIR_MARGIN = 1.25           # head radii; the hair stands out this far from the head center
_FOOT_REACH = 1.2             # head units around the ankle covered by the foot


def pose_bounds(figure):
    """Screen box (x0, y0, x1, y1) in px of a posed figure: joints, head with hair, hands and feet."""
    skeleton = build_skeleton(figure)
    unit, joints, head = skeleton.unit, skeleton.joints, skeleton.head
    points = [np.asarray(point, np.float64) for point in joints.values()]
    radius = _HAIR_MARGIN * head.unit
    points += [np.asarray(head.center) + offset for offset in ((-radius, -radius), (radius, radius))]
    for name in ('left', 'right'):
        forearm = joints[f'{name}_wrist'] - joints[f'{name}_elbow']
        reach = forearm / max(np.linalg.norm(forearm), 1e-6) * _HAND * unit
        points.append(joints[f'{name}_wrist'] + reach)
        points += [joints[f'{name}_ankle'] + np.array(offset) * unit
                   for offset in ((-_FOOT_REACH, 0.0), (_FOOT_REACH, 0.0), (0.0, 0.9))]
    points = np.array(points)
    return (*points.min(axis=0), *points.max(axis=0))


def _measure(pose, sex):
    x0, y0, x1, y1 = pose_bounds(Figure(pelvis=(0.0, 0.0), height=_BOUNDS_HEIGHT, pose=pose, sex=sex))
    return np.array([x0, y0, x1, y1]) / _BOUNDS_HEIGHT


def fit(box, pose, sex='female', align='bottom', scale=1.0):
    """pelvis and height that fit a posed figure into box (x0, y0, x1, y1) px: centered across,
    standing on the box's bottom edge (align='bottom') or centered (align='center').
    scale shrinks it below the largest size that fits (a taller man next to a woman: 1.0 vs 0.94).
    Use: Figure(**fit((0, 0, 800, 1000), pose), pose=pose)"""
    bx0, by0, bx1, by1 = box
    x0, y0, x1, y1 = _measure(pose, sex)
    height = min((bx1 - bx0) / (x1 - x0), (by1 - by0) / (y1 - y0)) * scale
    cx = 0.5 * (bx0 + bx1) - 0.5 * (x0 + x1) * height
    cy = by1 - y1 * height if align == 'bottom' else 0.5 * (by0 + by1) - 0.5 * (y0 + y1) * height
    return dict(pelvis=(float(cx), float(cy)), height=float(height))


def thirds(size, column='left', margin=0.06):
    """Box for placing a figure on a rule-of-thirds line: column 'left', 'right' or 'center'.
    The box is centered on the line, so the figure's middle sits on it."""
    width, height = size
    line = {'left': 1 / 3, 'center': 1 / 2, 'right': 2 / 3}[column] * width
    half = width * (1 / 3 - margin)
    return (line - half, height * margin, line + half, height * (1 - margin))


def group(box, poses, sexes=None, scales=None, gap=0.04, shot=None, headroom=0.55):
    """Lay out several figures side by side in box, all standing on one floor at one scale.
    scales: relative heights (e.g. 1.0 for a man, 0.94 for a woman). gap: space between them as a
    share of the box width (negative overlaps them, for a tight group portrait).
    shot: None stands everyone on the box's bottom edge, as large as fits. 'waist', 'thigh', 'bust' ...
    (see framing) sizes them so that the tallest is framed that way in the box height: the floor then
    lies below the box and what is under the frame falls off the canvas.
    Returns a list of dict(pelvis, height), one per pose."""
    count = len(poses)
    sexes = sexes or ['female'] * count
    scales = scales or [1.0] * count
    bx0, by0, bx1, by1 = box
    sizes = [_measure(pose, sex) * relative for pose, sex, relative in zip(poses, sexes, scales)]
    widths = [x1 - x0 for x0, _, x1, _ in sizes]
    spare = (bx1 - bx0) * (1.0 - gap * (count - 1))
    if shot is None:
        height = min(spare / sum(widths), (by1 - by0) / max(y1 - y0 for _, y0, _, y1 in sizes))
        floor = by1
    else:
        if shot not in _SHOTS:
            raise ValueError(f'unknown shot {shot!r}; choose from {sorted(_SHOTS)}')
        # As large as the shot asks, unless the row would then be wider than the box (a looser shot).
        height = min((by1 - by0) / (_SHOTS[shot] + headroom) * HEIGHT_UNITS, spare / sum(widths))
        unit = height / HEIGHT_UNITS
        tallest = int(np.argmax(scales))
        floor = by0 + (headroom + _CROWN_TO_PELVIS * scales[tallest]) * unit + sizes[tallest][3] * height
    used = sum(widths) * height + (bx1 - bx0) * gap * (count - 1)
    left = 0.5 * (bx0 + bx1) - 0.5 * used
    placements = []
    for (x0, y0, x1, y1), relative in zip(sizes, scales):
        figure_height = height * relative
        pelvis = (left - x0 * height, floor - y1 * height)
        placements.append(dict(pelvis=(float(pelvis[0]), float(pelvis[1])), height=float(figure_height)))
        left += (x1 - x0) * height + (bx1 - bx0) * gap
    return placements


def draw_figure(cv, figure, garments=()):
    """Paint a full-body figure. garments: callables (cv, figure, skeleton, masks, look) -> mask,
    painted over the skin in the given order (see figure.wardrobe).

    Returns dict(all=, skin=, skeleton=, plus one mask per body part, garment and head part).
    """
    skeleton = build_skeleton(figure)
    head, unit = skeleton.head, skeleton.unit
    look = replace(figure.look, scale=head.unit / REFERENCE_UNIT)
    skin = figure.face.skin
    cv.track('figure')

    # Seen from behind, the long hair hangs in front of the back: paint it last.
    hair_over = head.facing(0.0) < -_BACK_VIEW
    tie_over = hair_module.tie_in_front(head, figure.hair)
    back_hair = None if hair_over else hair_module.paint_back_hair(cv, head, figure.hair, look)
    tie = None if tie_over else hair_module.paint_tie(cv, head, figure.hair, look)
    parts, masks, hands = build_body(cv, figure, skeleton)
    union = paint_parts(cv, parts, skin, look, base_bulge=_BASE_BULGE * unit, broad_bulge=_BROAD_BULGE * unit)
    sealed = _close_pinholes(cv, union, unit)            # before the skin finish, so no rim light rings them
    union = np.maximum(union, sealed)
    for details in hands:
        finish_hand(cv, details, skin, look, union if details['visible'] is None else union * details['visible'])
    hair_parts, casters = hair_module.front_hair_masks(cv, head, figure.hair)
    head_shadow = np.maximum(cv.polygon(head.silhouette()), casters)
    if figure.body_details:
        _anatomy_details(cv, figure, skeleton, masks, look)
    _skin_finish(cv, figure, skeleton, masks, union, look, head_shadow)
    masks['skin'] = union
    # Headwear (garments marked over_head) goes on after the head and the hair; the rest before.
    worn = [index for index, garment in enumerate(garments) if not getattr(garment, 'over_head', False)]
    for index in worn:
        masks[f'garment_{index}'] = garments[index](cv, figure, skeleton, masks, look)
    body = np.maximum.reduce([union] + [masks[f'garment_{index}'] for index in worn])
    sealed = np.maximum(sealed, _close_pinholes(cv, body, unit))
    masks.update(paint_head(cv, head, figure.face, figure.hair, look, hair_parts, casters, back_hair))
    if hair_over:
        back_hair = hair_module.paint_back_hair(cv, head, figure.hair, look, over=True)
    if tie_over:
        tie = hair_module.paint_tie(cv, head, figure.hair, look, over=True)
    for index in sorted(set(range(len(garments))) - set(worn)):
        masks[f'garment_{index}'] = garments[index](cv, figure, skeleton, masks, look)
    masks.update(all=np.maximum(cv.tracked('figure'), sealed), skin=union, back_hair=back_hair, tie=tie,
                 skeleton=skeleton)
    return masks


def _close_pinholes(cv, body, unit):
    """Seal the tiny background islands a turned body encloses (an arm grazing the waist):
    fill them with the surrounding paint and drop their outline rings. Real gaps stay open."""
    solid = (body > 0.5).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(1 - solid, connectivity=4)
    height, width = solid.shape
    limit = (_PINHOLE * unit) ** 2
    small = [index for index in range(1, count)
             if stats[index, cv2.CC_STAT_AREA] < limit
             and stats[index, cv2.CC_STAT_LEFT] > 0 and stats[index, cv2.CC_STAT_TOP] > 0
             and stats[index, cv2.CC_STAT_LEFT] + stats[index, cv2.CC_STAT_WIDTH] < width
             and stats[index, cv2.CC_STAT_TOP] + stats[index, cv2.CC_STAT_HEIGHT] < height]
    if not small:
        return cv.empty()
    holes = np.isin(labels, small).astype(np.float32)
    region = raster.grow(holes, max(2.0, 0.03 * unit))
    paint = (np.clip(cv.color, 0.0, 1.0) * 255).astype(np.uint8)
    filled = cv2.inpaint(paint, (region > 0.5).astype(np.uint8), 3, cv2.INPAINT_TELEA).astype(np.float32) / 255
    cv.color = np.where(region[..., None] > 0.5, filled, cv.color).astype(np.float32)
    keep = 1.0 - raster.blur(region, 1.0)                # the line layer is premultiplied: scale both
    cv.line_alpha *= keep
    cv.line_rgb *= keep[..., None]
    return region
