"""3D figure rig: skeleton, builds, body surface data and poses for body3d.

Lengths are head heights (crown to chin = 1); the figure stands about 7.5
heads tall. Side names follow the picture at yaw 0: 'left' is image-left.

The body is described as data (trunk cross-sections and limb control points),
and the same data builds the clothes: a garment is the body surface over a
range of the trunk or a limb, pushed outward by the cloth thickness.
"""
from dataclasses import dataclass, field, replace
from enum import Enum

import numpy as np

from .body3d import Joint, ellipsoid, euler, rot_y, rot_z, section_sweep, sweep

SIDES = (("left", -1.0), ("right", 1.0))


class Sex(str, Enum):
    FEMALE = "female"
    MALE = "male"


@dataclass(frozen=True)
class Build:
    """Proportions relative to an average adult of the given sex (1.0 each)."""

    sex: Sex = Sex.FEMALE
    shoulders: float = 1.0
    bust: float = 1.0          # female breast size; ignored for male
    waist: float = 1.0
    hips: float = 1.0
    thighs: float = 1.0
    limbs: float = 1.0         # arm and leg thickness
    muscle: float = 0.0        # 0 smooth .. 1 defined (pecs, abs, deltoids, biceps)


FEMALE_AVERAGE = Build()
FEMALE_FULLER = Build(bust=1.32, waist=0.84, hips=1.12, thighs=1.06)
MALE_SLIM = Build(sex=Sex.MALE, shoulders=1.12, waist=1.02, hips=0.86, thighs=0.90, limbs=1.02, muscle=0.25)
MALE_ATHLETIC = Build(sex=Sex.MALE, shoulders=1.26, waist=1.06, hips=0.90, thighs=1.0, limbs=1.20, muscle=1.0)


def joints(build):
    """Skeleton for a build: shoulders and hips move apart with their widths."""
    shoulder_x = 0.60 * build.shoulders
    hip_x = 0.37 * (1.0 + (build.hips - 1.0) * 0.6)
    result = [
        Joint("pelvis", None, (0.0, 0.0, 0.0)),
        Joint("spine", "pelvis", (0.0, -0.80, 0.0)),
        Joint("chest", "spine", (0.0, -0.92, 0.0)),
        Joint("neck", "chest", (0.0, -0.60, 0.0)),
        Joint("head", "neck", (0.0, -0.80, 0.0)),
    ]
    for side, sign in SIDES:
        result += [
            Joint(f"shoulder_{side}", "chest", (sign * shoulder_x, -0.36, 0.0)),
            Joint(f"elbow_{side}", f"shoulder_{side}", (0.0, 1.30, 0.0)),
            Joint(f"wrist_{side}", f"elbow_{side}", (0.0, 1.08, 0.0)),
            Joint(f"hip_{side}", "pelvis", (sign * hip_x, 0.02, 0.0)),
            Joint(f"knee_{side}", f"hip_{side}", (0.0, 1.85, 0.0)),
            Joint(f"ankle_{side}", f"knee_{side}", (0.0, 1.63, 0.0)),
        ]
    return result


# ---- surface data ----------------------------------------------------------------------
# Trunk cross-sections, bottom to top: (landmark, joint, local point, half width, half depth, width channel).
TRUNK = (
    ("crotch", "pelvis", (0, 0.36, -0.02), 0.34, 0.28, "hips"),
    ("hip_low", "pelvis", (0, 0.18, -0.03), 0.60, 0.38, "hips"),
    ("hip", "pelvis", (0, 0.00, -0.04), 0.66, 0.40, "hips"),
    ("hip_high", "pelvis", (0, -0.30, -0.02), 0.58, 0.36, "hips"),
    ("waist", "spine", (0, 0.02, 0.0), 0.45, 0.31, "waist"),
    ("ribs", "chest", (0, 0.50, 0.01), 0.52, 0.34, "ribs"),
    ("chest", "chest", (0, 0.12, 0.03), 0.60, 0.38, "shoulders"),
    ("upper_chest", "chest", (0, -0.22, 0.0), 0.63, 0.35, "shoulders"),
    ("shoulder", "chest", (0, -0.46, -0.04), 0.46, 0.25, "shoulders"),
    ("neck", "chest", (0, -0.58, -0.04), 0.20, 0.17, "neck"),
)
TRUNK_LANDMARKS = {name: index / (len(TRUNK) - 1) for index, (name, *_rest) in enumerate(TRUNK)}
# Limb control points: (joint, local point, radius). Landmarks give their position along the limb.
ARM = (("shoulder", (0, 0.04, 0), 0.155), ("shoulder", (0, 0.65, 0), 0.15), ("elbow", (0, 0, 0), 0.105),
       ("elbow", (0, 0.40, 0), 0.12), ("wrist", (0, 0, 0), 0.078))
ARM_LANDMARKS = {"shoulder": 0.0, "upper_arm": 0.25, "elbow": 0.5, "forearm": 0.75, "wrist": 1.0}
LEG = (("hip", (0, -0.06, 0), 0.33), ("hip", (0, 0.80, 0), 0.28), ("knee", (0, 0, 0), 0.175),
       ("knee", (0, 0.45, -0.03), 0.195), ("ankle", (0, 0, 0), 0.092))
LEG_LANDMARKS = {"hip": 0.0, "thigh": 0.25, "knee": 0.5, "calf": 0.75, "ankle": 1.0}
FOOT = (((0, 0.05, -0.09), 0.088), ((0, 0.09, 0.10), 0.082), ((0, 0.12, 0.30), 0.075), ((0, 0.12, 0.40), 0.055))
FEMALE_NECK, MALE_NECK = 0.19, 0.235
TRAPEZIUS_SLOPE = 0.32       # radians the neck-to-shoulder line falls toward the shoulder


def channel(build, name):
    return {"fixed": 1.0, "hips": build.hips, "waist": build.waist, "shoulders": build.shoulders,
            "ribs": (build.waist + build.shoulders) / 2, "neck": 1.25 if build.sex is Sex.MALE else 1.0}[name]


def trunk_sections(skeleton, build, start=0.0, end=1.0, offset=0.0, flare=None):
    """Trunk cross-sections between two landmark positions (0 crotch .. 1 neck), pushed out by offset
    (a number, or a function of the landmark position). flare(t) may return extra half width (loose clothes)."""
    rows = []
    for name, joint, local, rx, rz, ch in TRUNK:
        point = skeleton.point(joint, local)
        rows.append((point, skeleton.rotation[joint], rx * channel(build, ch), rz))
    return _cut_sections(rows, start, end, offset, flare)


def _cut_sections(rows, start, end, offset, flare):
    count = len(rows) - 1
    result = []
    for u in _cut_positions(count, start, end):
        index = min(int(u), count - 1)
        t = u - index
        (p0, a0, x0, z0), (p1, a1, x1, z1) = rows[index], rows[index + 1]
        extra = flare(u / count) if flare else 0.0
        push = offset(u / count) if callable(offset) else offset
        frame = a0 if t < 0.5 else a1
        result.append((p0 * (1 - t) + p1 * t, frame, x0 * (1 - t) + x1 * t + push + extra,
                       z0 * (1 - t) + z1 * t + push + extra * 0.7))
    return result


def _cut_positions(count, start, end):
    """Control positions between start and end (0..1), keeping every original control point in between."""
    first, last = start * count, end * count
    inner = [float(i) for i in range(int(np.ceil(first)), int(np.floor(last)) + 1) if first < i < last]
    return [first] + inner + [last]


def limb_path(skeleton, side, spec, build, start=0.0, end=1.0, offset=0.0, scale=1.0):
    """Points and radii of an arm or leg between two positions along it (0 root .. 1 end)."""
    points = np.array([skeleton.point(f"{joint}_{side}", local) for joint, local, _ in spec])
    radii = np.array([radius for *_rest, radius in spec]) * scale
    count = len(spec) - 1
    positions = _cut_positions(count, start, end)
    cut_points, cut_radii = [], []
    for u in positions:
        index = min(int(u), count - 1)
        t = u - index
        cut_points.append(points[index] * (1 - t) + points[index + 1] * t)
        cut_radii.append(radii[index] * (1 - t) + radii[index + 1] * t + offset)
    return np.array(cut_points), np.array(cut_radii)


def limb_scale(build, limb):
    scale = build.limbs
    if limb == "leg" and build.sex is Sex.FEMALE:
        scale *= build.thighs
    return scale


# ---- body ------------------------------------------------------------------------------------
def breast_shape(build, sign):
    """Chest-frame centre and radii of one breast."""
    extra = build.bust - 1.0
    center = (sign * (0.27 + extra * 0.10), 0.14 + extra * 0.10, 0.24 + extra * 0.04)
    radii = (0.21 * build.bust, 0.21 * build.bust, 0.17 * (1 + extra * 1.2))
    return center, radii


def glute_shape(build, sign):
    """Pelvis-frame centre and radii of one buttock."""
    if build.sex is Sex.FEMALE:
        return (sign * 0.27, 0.12, -0.20), (0.30 * build.hips, 0.32, 0.27 * build.hips)
    return (sign * 0.24, 0.10, -0.16), (0.26, 0.28, 0.24)


def deltoid_shape(build, side):
    """Shoulder-joint-frame centre and radii of the shoulder muscle."""
    sign = -1.0 if side == "left" else 1.0
    size = 0.165 * build.shoulders * (1.0 + 0.12 * build.muscle)
    return (-sign * 0.02, 0.16, 0.0), (size, 0.30, size * 0.95)


def pec_shape(build, sign):
    """Chest-frame centre and radii of one male chest muscle."""
    return (sign * 0.25, -0.02, 0.22), (0.26 * build.shoulders, 0.19, 0.12 + 0.05 * build.muscle)


def trapezius_shape(build, sign):
    """Chest-frame centre, radii and slope of the muscle that runs from the neck to the shoulder.
    It fills the dip between neck and shoulder, so the shoulder line slopes instead of stepping."""
    bulk = 1.0 + 0.4 * build.muscle
    center = (sign * 0.36 * build.shoulders, -0.55, -0.07)
    radii = (0.27 * build.shoulders, 0.075 * bulk, 0.16 * bulk)
    return center, radii, sign * TRAPEZIUS_SLOPE


def trapezius_frame(skeleton, build, sign):
    return skeleton.rotation["chest"] @ rot_z(trapezius_shape(build, sign)[2])


NECK_BASE = (0.0, -0.52, -0.02)     # chest-local start of the neck
NECK_TOP = (0.0, -0.40, 0.0)        # neck-local end of the neck (inside the head)
NECK_BASE_SCALE = 1.05              # the neck is this much thicker at its base


def neck_path(skeleton, build):
    """(points, radii) of the neck from its base on the chest to inside the head."""
    radius = MALE_NECK if build.sex is Sex.MALE else FEMALE_NECK
    return ([skeleton.point("chest", NECK_BASE), skeleton.point("neck", NECK_TOP)],
            [radius * NECK_BASE_SCALE, radius])


def body_solids(skeleton, build, skin, hands=None):
    """The bare body as solids (head and hair are added by head3d)."""
    s, b = skeleton, build
    solids = torso_solids(s, b, skin)
    for side, sign in SIDES:
        sh = f"shoulder_{side}"
        center, radii = deltoid_shape(b, side)
        solids.append(ellipsoid(s.point(sh, center), s.rotation[sh], radii, skin))
        points, radii = limb_path(s, side, ARM, b, scale=limb_scale(b, "arm"))
        if b.muscle > 0:
            radii = radii * (1 + 0.12 * b.muscle * np.array([0, 1, 0, 0.6, 0]))   # biceps and forearm
        solids.append(sweep(points, radii, skin))
        points, radii = limb_path(s, side, LEG, b, scale=limb_scale(b, "leg"))
        solids.append(sweep(points, radii, skin))
        solids.append(sweep([s.point(f"ankle_{side}", p) for p, _ in FOOT], [r for _, r in FOOT], skin, name="foot"))
        if hands is not None:
            solids += hands(s, side, skin)
    return solids


def torso_solids(skeleton, build, skin):
    """Trunk, neck, chest, glutes and trapezius without the limbs: the surface that strings and straps
    lie on (an arm hanging against the side must not push a bikini band away from the ribs)."""
    s, b = skeleton, build
    solids = section_sweep(trunk_sections(s, b), skin)
    solids.append(sweep(*neck_path(s, b), skin))
    if b.sex is Sex.FEMALE:
        for _, sign in SIDES:
            center, radii = breast_shape(b, sign)
            solids.append(ellipsoid(s.point("chest", center), s.rotation["chest"], radii, skin))
    else:
        muscle = b.muscle
        for _, sign in SIDES:
            center, radii = pec_shape(b, sign)
            solids.append(ellipsoid(s.point("chest", center), s.rotation["chest"], radii, skin))
        if muscle > 0.5:
            for row in range(3):
                for _, sign in SIDES:
                    solids.append(ellipsoid(s.point("spine", (sign * 0.10, -0.30 + row * 0.24, 0.27)),
                                            s.rotation["spine"], (0.10, 0.10, 0.05 * muscle), skin))
    for _, sign in SIDES:
        center, radii = glute_shape(b, sign)
        solids.append(ellipsoid(s.point("pelvis", center), s.rotation["pelvis"], radii, skin))
        center, radii, _ = trapezius_shape(b, sign)
        solids.append(ellipsoid(s.point("chest", center), trapezius_frame(s, b, sign), radii, skin))
    return solids


# ---- hands ------------------------------------------------------------------------------------
# Hand frame (applied on top of the wrist): y along the fingers, z out of the back of the hand,
# x toward the thumb on the left hand and away from it on the right hand.
FINGERS = (("index", 0.105, 0.300, 0.040), ("middle", 0.035, 0.330, 0.041), ("ring", -0.035, 0.310, 0.038),
           ("pinky", -0.100, 0.240, 0.033))
KNUCKLE_Y = 0.40
PHALANGES = (0.45, 0.30, 0.25)
THUMB = ((0.11, 0.10, -0.03), (0.135, 0.11, 0.090), 0.050)   # base, segment lengths, radius


@dataclass(frozen=True)
class HandPose3D:
    """curl: radians at each finger joint (0 straight, about 1.4 a fist). spread: radians between fingers."""

    curl: dict = field(default_factory=lambda: {"index": 0.25, "middle": 0.32, "ring": 0.38, "pinky": 0.45})
    spread: float = 0.08
    thumb_out: float = 0.55     # radians away from the palm
    thumb_curl: float = 0.25


RELAXED = HandPose3D()
OPEN = HandPose3D(curl={"index": 0.0, "middle": 0.0, "ring": 0.0, "pinky": 0.0}, spread=0.22, thumb_out=0.9,
                  thumb_curl=0.0)
FIST = HandPose3D(curl={"index": 1.45, "middle": 1.5, "ring": 1.5, "pinky": 1.5}, spread=0.0, thumb_out=0.2,
                  thumb_curl=0.9)
POINTING = replace(FIST, curl={"index": 0.0, "middle": 1.5, "ring": 1.5, "pinky": 1.5})
PEACE = HandPose3D(curl={"index": 0.0, "middle": 0.0, "ring": 1.5, "pinky": 1.5}, spread=0.30, thumb_out=0.2,
                   thumb_curl=0.9)
HOLDING = HandPose3D(curl={"index": 0.95, "middle": 1.0, "ring": 1.0, "pinky": 1.0}, spread=0.0, thumb_out=0.45,
                     thumb_curl=0.55)   # wraps round a handle about 0.07 head heights thick


def hand_frame(skeleton, side):
    sign = -1.0 if side == "left" else 1.0
    return skeleton.rotation[f"wrist_{side}"] @ rot_y(sign * np.pi / 2), (1.0 if side == "left" else -1.0)


def hand_solids(pose_by_side, scale=1.0):
    """Returns a hands(skeleton, side, skin) builder for body_solids."""

    def build(skeleton, side, skin):
        pose = pose_by_side[side]
        frame, thumb_side = hand_frame(skeleton, side)
        wrist = skeleton.position[f"wrist_{side}"]

        def at(local):
            return wrist + frame @ (np.asarray(local, dtype=np.float64) * scale)

        solids = [ellipsoid(at((0, 0.21, 0)), frame, (0.135 * scale, 0.22 * scale, 0.055 * scale), skin, name="hand"),
                  ellipsoid(at((thumb_side * 0.07, 0.15, -0.025)), frame,
                            (0.07 * scale, 0.11 * scale, 0.05 * scale), skin, name="hand")]
        for index, (finger, x, length, radius) in enumerate(FINGERS):
            angle = (1.5 - index) * pose.spread * thumb_side
            direction = rot_z_local(angle)
            point = np.array([thumb_side * x, KNUCKLE_Y, 0.0])
            path, bend = [point.copy()], np.eye(3)
            for share in PHALANGES:
                bend = bend @ rot_x_local(pose.curl[finger])
                point = point + direction @ bend @ np.array([0.0, length * share, 0.0])
                path.append(point.copy())
            radii = np.linspace(radius, radius * 0.78, len(path)) * scale
            solids.append(sweep([at(p) for p in path], radii, skin, name="hand"))
        base, lengths, radius = THUMB
        point = np.array([thumb_side * base[0], base[1], base[2]])
        direction = np.array([thumb_side * np.sin(pose.thumb_out), np.cos(pose.thumb_out) * 0.9, -0.35])
        direction /= np.linalg.norm(direction)
        path = [point.copy()]
        for segment, length in enumerate(lengths):
            # Thumb curl turns the thumb toward the palm centre (−x on the thumb side, −z palm side).
            turn = pose.thumb_curl * (segment + 1) * 0.5
            direction = direction + np.array([-thumb_side * turn * 0.6, 0.0, -turn * 0.5])
            direction /= np.linalg.norm(direction)
            point = point + direction * length
            path.append(point.copy())
        solids.append(sweep([at(p) for p in path], np.linspace(radius, radius * 0.75, len(path)) * scale, skin,
                            name="hand"))
        return solids

    return build


def rot_x_local(angle):
    """Curl toward the palm (−z) for a finger pointing along +y."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[1, 0, 0], [0, c, s], [0, -s, c]], dtype=np.float64)


def rot_z_local(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]], dtype=np.float64)


# ---- poses ------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Reach:
    """Put a hand on a point: target is (joint, local point); pole is a figure-space direction the
    elbow should point to; wrist is an extra (rx, ry, rz) for the hand relative to the forearm."""

    target: tuple
    pole: tuple = (1.0, 0.3, -0.5)
    wrist: tuple = (0.0, 0.0, 0.0)
    fingers: tuple = None      # if set: chest-frame direction the fingers point (replaces wrist) ...
    palm: tuple = None         # ... and the chest-frame direction the palm faces


@dataclass(frozen=True)
class Pose3D:
    """Local joint rotations as (rx, ry, rz) in radians (see body3d.rot_x/rot_y/rot_z), hand poses,
    and optional reaches that place a hand by inverse kinematics.

    rx > 0 swings a bone that points down backward, away from the viewer of a front view (a knee
    bends with rx > 0, a leg or arm lifts forward with rx < 0); a bone that points up (spine, neck,
    head) leans forward with rx > 0,
    rz > 0 swings it toward image-left, ry twists about the bone.
    """

    rotations: dict = field(default_factory=dict)
    hands: dict = field(default_factory=lambda: {"left": RELAXED, "right": RELAXED})
    reach: dict = field(default_factory=dict)       # side -> Reach

    def matrices(self):
        return {name: euler(*angles) for name, angles in self.rotations.items()}


def pose(hands=None, reach=None, **rotations):
    return Pose3D(rotations, hands or {"left": RELAXED, "right": RELAXED}, reach or {})


def mirrored(pose_value):
    """The same pose with left and right exchanged: a wave with the other hand, or a hand-on-hip pose that
    shows its raised arm on the near side of a profile. Mirroring across the body's middle plane keeps a
    rotation about x and reverses the ones about y and z."""
    def swap(name):
        for side, other in (("_left", "_right"), ("_right", "_left")):
            if name.endswith(side):
                return name[:-len(side)] + other
        return name

    def other_side(side):
        return "right" if side == "left" else "left"

    def flip_angles(angles):
        rx, ry, rz = angles
        return (rx, -ry, -rz)

    def flip_point(point):
        return None if point is None else (-point[0], point[1], point[2])

    rotations = {swap(name): flip_angles(angles) for name, angles in pose_value.rotations.items()}
    hands = {other_side(side): hand for side, hand in pose_value.hands.items()}
    reach = {other_side(side): Reach((swap(item.target[0]), flip_point(item.target[1])), pole=flip_point(item.pole),
                                     wrist=flip_angles(item.wrist), fingers=flip_point(item.fingers),
                                     palm=flip_point(item.palm))
             for side, item in pose_value.reach.items()}
    return Pose3D(rotations, hands, reach)


def pose_skeleton(skeleton_class, joint_list, pose_value):
    """Forward kinematics, then two-bone inverse kinematics for every reach in the pose."""
    rotations = pose_value.matrices()
    skeleton = skeleton_class(joint_list, rotations)
    if not pose_value.reach:
        return skeleton
    lengths = {j.name: float(np.linalg.norm(j.offset)) for j in joint_list}
    for side, reach in pose_value.reach.items():
        joint, local = reach.target
        target = skeleton.point(joint, local)
        rotations.update(_solve_arm(skeleton, side, target, np.asarray(reach.pole, dtype=np.float64),
                                    lengths[f"elbow_{side}"], lengths[f"wrist_{side}"]))
        rotations[f"wrist_{side}"] = euler(*reach.wrist)
        skeleton = skeleton_class(joint_list, rotations)
        if reach.fingers is not None:
            rotations[f"wrist_{side}"] = _orient_hand(skeleton, side, reach)
            skeleton = skeleton_class(joint_list, rotations)
    return skeleton


WRIST_LIMIT = 1.25   # radians the hand may bend away from the forearm line


def _orient_hand(skeleton, side, reach):
    """Wrist rotation that points the fingers and turns the palm as the reach asks, with the bend
    away from the forearm limited so the wrist never looks broken."""
    chest = skeleton.rotation["chest"]
    forearm = skeleton.rotation[f"elbow_{side}"]
    along = forearm[:, 1] / np.linalg.norm(forearm[:, 1])
    fingers = chest @ np.asarray(reach.fingers, dtype=np.float64)
    fingers /= np.linalg.norm(fingers)
    bend = float(np.arccos(np.clip(fingers @ along, -1.0, 1.0)))
    if bend > WRIST_LIMIT:
        # Turn the fingers back toward the forearm line until the bend is at the limit.
        side_dir = fingers - along * (fingers @ along)
        side_dir /= np.linalg.norm(side_dir) + 1e-9
        fingers = along * np.cos(WRIST_LIMIT) + side_dir * np.sin(WRIST_LIMIT)
    palm = chest @ np.asarray(reach.palm if reach.palm is not None else (0.0, 0.0, 1.0), dtype=np.float64)
    back = -(palm - fingers * (palm @ fingers))          # hand-frame z points out of the back of the hand
    back /= np.linalg.norm(back) + 1e-9
    hand = np.stack([np.cross(fingers, back), fingers, back], axis=1)
    sign = -1.0 if side == "left" else 1.0
    wrist_world = hand @ rot_y(sign * np.pi / 2).T
    return (forearm / np.linalg.norm(forearm[:, 0])).T @ wrist_world


def _solve_arm(skeleton, side, target, pole, upper, lower):
    """Shoulder and elbow rotations that bring the wrist to target with the elbow toward pole."""
    shoulder = skeleton.position[f"shoulder_{side}"]
    to_target = target - shoulder
    distance = float(np.clip(np.linalg.norm(to_target), 1e-6, (upper + lower) * 0.999))
    axis = to_target / (np.linalg.norm(to_target) + 1e-9)
    # Elbow position: law of cosines along the target axis, offset toward the pole.
    along = (upper**2 - lower**2 + distance**2) / (2 * distance)
    height = np.sqrt(max(upper**2 - along**2, 0.0))
    side_dir = pole - axis * (pole @ axis)
    side_dir /= np.linalg.norm(side_dir) + 1e-9
    elbow = shoulder + axis * along + side_dir * height
    wrist = shoulder + axis * distance
    up_dir = (elbow - shoulder) / upper
    fore_dir = (wrist - elbow) / (np.linalg.norm(wrist - elbow) + 1e-9)
    bend_axis = np.cross(up_dir, fore_dir)
    if np.linalg.norm(bend_axis) < 1e-6:
        bend_axis = np.cross(up_dir, np.array([0.0, 0.0, 1.0]))
    bend_axis /= np.linalg.norm(bend_axis)
    # Shoulder frame: y along the upper arm, x the elbow hinge, z completing the right-handed frame.
    z_axis = np.cross(bend_axis, up_dir)
    world = np.stack([bend_axis, up_dir, z_axis], axis=1)
    parent = skeleton.rotation["chest"]
    shoulder_local = parent.T @ world
    fore_local = world.T @ fore_dir                    # (0, cos a, -sin a) for a hinge about x
    angle = float(np.arctan2(-fore_local[2], fore_local[1]))
    from .body3d import rot_x
    return {f"shoulder_{side}": shoulder_local, f"elbow_{side}": rot_x(angle)}


TURN_OUT = 0.32      # radians the feet point outward when standing
STAND = pose(shoulder_left=(0, 0, 0.12), shoulder_right=(0, 0, -0.12), elbow_left=(-0.12, 0, 0),
             elbow_right=(-0.12, 0, 0), ankle_left=(0, -TURN_OUT, 0), ankle_right=(0, TURN_OUT, 0))
A_POSE_3D = pose(shoulder_left=(0, 0, 0.45), shoulder_right=(0, 0, -0.45), hip_left=(0, 0, 0.06),
                 hip_right=(0, 0, -0.06), knee_left=(0, 0, -0.04), knee_right=(0, 0, 0.04),
                 ankle_left=(0, -TURN_OUT, -0.02), ankle_right=(0, TURN_OUT, 0.02))
CONTRAPPOSTO = pose(pelvis=(0, 0, -0.10), spine=(0, 0, 0.05), chest=(0, 0, 0.10), head=(0, 0, -0.06),
                    shoulder_left=(0.05, 0, 0.20), elbow_left=(-0.25, 0, 0), shoulder_right=(0, 0, -0.18),
                    elbow_right=(-0.15, 0, 0), hip_left=(0, 0, 0.10), hip_right=(-0.12, 0, -0.05),
                    knee_right=(0.32, 0, 0), ankle_left=(0, -TURN_OUT, -0.10), ankle_right=(-0.05, TURN_OUT + 0.15, 0.05))
# Palm flat on the side of the hip, fingers pointing forward and down; the target sits one hand
# thickness outside the clothed hip, so the hand rests on trousers instead of sinking into them.
FLAT_HAND = HandPose3D(curl={"index": 0.10, "middle": 0.12, "ring": 0.16, "pinky": 0.20}, spread=0.04, thumb_out=0.75,
                       thumb_curl=0.10)
HAND_ON_HIP = Pose3D(dict(CONTRAPPOSTO.rotations), {"left": RELAXED, "right": FLAT_HAND},
                     {"right": Reach(("hip_right", (0.39, -0.44, -0.16)), pole=(1.0, -0.2, -0.6),
                                     fingers=(0.0, 0.55, 0.85), palm=(-1.0, 0.0, 0.0))})
ARMS_CROSSED = pose(hip_left=(0, 0, 0.04), hip_right=(0, 0, -0.04), head=(0, 0.15, 0),
                    ankle_left=(0, -TURN_OUT, -0.04), ankle_right=(0, TURN_OUT, 0.04),
                    hands={"left": HOLDING, "right": HOLDING},
                    reach={"left": Reach(("chest", (0.42, 0.62, 0.46)), pole=(-1.0, 0.4, 0.5)),
                           "right": Reach(("chest", (-0.46, 0.52, 0.58)), pole=(1.0, 0.4, 0.5))})
WALK = pose(pelvis=(0, 0.10, 0), chest=(0, -0.14, 0), shoulder_left=(0.35, 0, 0.06), elbow_left=(-0.30, 0, 0),
            shoulder_right=(-0.30, 0, -0.06), elbow_right=(-0.35, 0, 0), hip_left=(-0.38, 0, 0.02),
            knee_left=(0.15, 0, 0), ankle_left=(0.10, 0, 0), hip_right=(0.30, 0, -0.02), knee_right=(0.55, 0, 0),
            ankle_right=(-0.25, 0, 0))
SIT = pose(spine=(0.08, 0, 0), hip_left=(-1.45, 0, 0.10), knee_left=(1.45, 0, 0), hip_right=(-1.45, 0, -0.10),
           knee_right=(1.45, 0, 0), ankle_left=(0, -0.2, 0), ankle_right=(0, 0.2, 0),
           reach={"left": Reach(("hip_left", (0.02, 1.25, 0.30)), pole=(-1.0, 0.6, -0.3),
                                fingers=(0.1, 0.3, 1.0), palm=(0.0, 1.0, 0.0)),
                  "right": Reach(("hip_right", (-0.02, 1.25, 0.30)), pole=(1.0, 0.6, -0.3),
                                 fingers=(-0.1, 0.3, 1.0), palm=(0.0, 1.0, 0.0))})
WAVE = Pose3D({**CONTRAPPOSTO.rotations, "head": (0, -0.12, -0.08)}, {"left": RELAXED, "right": OPEN},
              {"right": Reach(("chest", (0.95, -1.35, 0.30)), pole=(0.7, 1.0, -0.2), wrist=(0.75, 0.0, -0.25))})
_FEET = dict(ankle_left=(0, -TURN_OUT, 0), ankle_right=(0, TURN_OUT, 0))
POINT = pose(head=(0.05, 0.25, 0), spine=(0, 0.15, 0), hip_left=(0, 0, 0.06), hip_right=(0, 0, -0.04), **_FEET,
             hands={"left": RELAXED, "right": POINTING},
             reach={"right": Reach(("chest", (0.95, -0.15, 2.05)), pole=(1.0, 0.6, -0.3),
                                   fingers=(0.25, -0.05, 1.0), palm=(-1.0, 0.0, 0.0))})
THINK = pose(head=(0.12, -0.10, -0.12), hip_left=(0, 0, 0.05), hip_right=(0, 0, -0.03), **_FEET,
             hands={"left": RELAXED, "right": HOLDING},
             reach={"right": Reach(("head", (0.14, 0.86, 0.26)), pole=(0.3, 1.0, 0.3),
                                   fingers=(-0.3, -1.0, 0.35), palm=(-0.5, 0.0, -1.0)),
                    "left": Reach(("chest", (0.30, 0.86, 0.45)), pole=(-1.0, 0.5, 0.4),
                                  fingers=(1.0, 0.1, 0.1), palm=(0.0, -1.0, 0.0))})
HANDS_BEHIND = pose(head=(-0.05, 0.0, 0.0), spine=(-0.06, 0, 0), **_FEET,
                    reach={"left": Reach(("pelvis", (-0.12, -0.05, -0.62)), pole=(-1.0, 0.3, -0.4),
                                         fingers=(0.4, 1.0, 0.0), palm=(0.0, 0.0, -1.0)),
                           "right": Reach(("pelvis", (0.12, -0.05, -0.62)), pole=(1.0, 0.3, -0.4),
                                          fingers=(-0.4, 1.0, 0.0), palm=(0.0, 0.0, -1.0))})
CHEER = pose(head=(-0.15, 0.0, -0.05), hip_left=(0, 0, 0.06), hip_right=(0, 0, -0.06), **_FEET,
             hands={"left": FIST, "right": FIST},
             reach={"right": Reach(("chest", (0.75, -2.35, 0.40)), pole=(1.0, 0.3, -0.3),
                                   fingers=(0.0, -1.0, 0.0), palm=(-1.0, 0.0, 0.2)),
                    "left": Reach(("pelvis", (-0.80, -0.55, 0.30)), pole=(-1.0, 0.0, -0.6),
                                  fingers=(0.3, -0.4, 1.0), palm=(1.0, 0.0, 0.0))})
PEACE_SIGN = pose(head=(0.0, 0.10, 0.14), spine=(0, 0, -0.04), hip_left=(0, 0, 0.05), hip_right=(0, 0, -0.03), **_FEET,
                  hands={"left": RELAXED, "right": PEACE},
                  reach={"right": Reach(("head", (0.58, 0.42, 0.30)), pole=(0.5, 1.0, 0.2),
                                        fingers=(0.10, -1.0, 0.1), palm=(0.0, 0.0, 1.0))})
# ---- poses with objects -----------------------------------------------------------------------------------
# Hands that hold something. The held object itself is built by props3d.held_* from the same hand frame.
TYPING = HandPose3D(curl={"index": 0.45, "middle": 0.50, "ring": 0.55, "pinky": 0.60}, spread=0.12, thumb_out=0.45,
                    thumb_curl=0.30)
PHONE_GRIP = HandPose3D(curl={"index": 0.80, "middle": 0.90, "ring": 0.95, "pinky": 1.00}, spread=0.04,
                        thumb_out=0.80, thumb_curl=0.45)
CUP_GRIP = HandPose3D(curl={"index": 0.55, "middle": 0.60, "ring": 0.65, "pinky": 0.70}, spread=0.05, thumb_out=0.95,
                      thumb_curl=0.25)
PAD_GRIP = HandPose3D(curl={"index": 0.70, "middle": 1.10, "ring": 1.15, "pinky": 1.20}, spread=0.02, thumb_out=0.95,
                      thumb_curl=0.20)
_SIT_LEGS = dict(hip_left=(-1.45, 0, 0.10), knee_left=(1.45, 0, 0), hip_right=(-1.45, 0, -0.10), knee_right=(1.45, 0, 0),
                 ankle_left=(0, -0.2, 0), ankle_right=(0, 0.2, 0))
_LAP = {"left": SIT.reach["left"], "right": SIT.reach["right"]}
LOOK_DOWN = dict(neck=(0.12, 0, 0), head=(0.30, 0, 0))
# Hands on a laptop keyboard: the targets assume furniture3d.desk at its default height and a seat at SEAT_TOP,
# with the laptop's front edge about one head height in front of the pelvis.
SIT_TYPE = pose(spine=(0.14, 0, 0), neck=(0.05, 0, 0), head=(0.16, 0, 0), **_SIT_LEGS,
                hands={"left": TYPING, "right": TYPING},
                reach={"left": Reach(("pelvis", (-0.30, -1.52, 1.18)), pole=(-1.0, 0.7, -0.3),
                                     fingers=(0.15, 0.35, 1.0), palm=(0.0, 1.0, 0.15)),
                       "right": Reach(("pelvis", (0.30, -1.52, 1.18)), pole=(1.0, 0.7, -0.3),
                                      fingers=(-0.15, 0.35, 1.0), palm=(0.0, 1.0, 0.15))})
# A phone in the right hand in front of the chest, screen toward the eyes (props3d.held_phone).
_PHONE_REACH = Reach(("chest", (0.55, 0.42, 1.0)), pole=(1.0, 0.7, -0.3), fingers=(-1.0, 0.0, 0.0),
                     palm=(0.0, -0.5, -0.85))
STAND_PHONE = pose(**LOOK_DOWN, hip_left=(0, 0, 0.05), hip_right=(0, 0, -0.03), **_FEET,
                   hands={"left": RELAXED, "right": PHONE_GRIP}, reach={"right": _PHONE_REACH})
SIT_PHONE = pose(spine=(0.10, 0, 0), **LOOK_DOWN, **_SIT_LEGS, hands={"left": RELAXED, "right": PHONE_GRIP},
                 reach={"left": _LAP["left"], "right": _PHONE_REACH})
# A cup in the right hand at the chest, fingers round its body (props3d.held_mug).
_CUP_REACH = Reach(("chest", (0.46, 0.45, 0.66)), pole=(1.0, 0.8, -0.4), fingers=(0.0, 0.0, 1.0), palm=(-1.0, 0.0, 0.0))
STAND_MUG = pose(head=(0.10, 0.12, -0.05), hip_left=(0, 0, 0.05), hip_right=(0, 0, -0.03), **_FEET,
                 hands={"left": RELAXED, "right": CUP_GRIP}, reach={"right": _CUP_REACH})
SIT_MUG = pose(spine=(0.06, 0, 0), head=(0.08, 0.10, -0.04), **_SIT_LEGS, hands={"left": RELAXED, "right": CUP_GRIP},
               reach={"left": _LAP["left"], "right": _CUP_REACH})
# Both hands on a game controller above the lap (props3d.held_controller).
SIT_GAME = pose(spine=(0.16, 0, 0), neck=(-0.06, 0, 0), head=(-0.04, 0, 0), **_SIT_LEGS,
                hands={"left": PAD_GRIP, "right": PAD_GRIP},
                reach={"left": Reach(("pelvis", (-0.36, -0.98, 0.95)), pole=(-1.0, 0.8, -0.3),
                                     fingers=(0.55, -0.45, 0.70), palm=(0.75, 0.35, 0.0)),
                       "right": Reach(("pelvis", (0.36, -0.98, 0.95)), pole=(1.0, 0.8, -0.3),
                                      fingers=(-0.55, -0.45, 0.70), palm=(-0.75, 0.35, 0.0))})
# ---- poses in motion and on the floor ----------------------------------------------------------------------
# A figure is set down by figure3d.ground_points, so these poses need no height of their own: the parts that
# hang lowest (the support foot; knees and insteps; back, hips and heels; elbows and thighs) meet the floor.
RUN_HAND = HandPose3D(curl={"index": 1.0, "middle": 1.1, "ring": 1.15, "pinky": 1.2}, spread=0.02, thumb_out=0.4,
                      thumb_curl=0.5)
# The back arm swings out past the hip: bent further forward, its fist lands on the hip and reads as a grab.
RUN = pose(pelvis=(0, -0.12, 0), spine=(0.22, 0, 0), chest=(0, 0.20, 0), neck=(-0.10, 0, 0), head=(-0.12, -0.06, 0),
           shoulder_right=(-0.85, 0, -0.10), elbow_right=(-1.45, 0, 0), shoulder_left=(0.95, 0, 0.18),
           elbow_left=(-1.05, 0, 0), hip_right=(0.20, 0, -0.02), knee_right=(0.30, 0, 0), ankle_right=(-0.15, 0, 0),
           hip_left=(-1.05, 0, 0.03), knee_left=(1.40, 0, 0), ankle_left=(0.35, 0, 0),
           hands={"left": RUN_HAND, "right": RUN_HAND})
KNEEL = pose(spine=(0.02, 0, 0), shoulder_left=(0, 0, 0.12), shoulder_right=(0, 0, -0.12), elbow_left=(-0.20, 0, 0),
             elbow_right=(-0.20, 0, 0), hip_left=(0, 0, 0.05), hip_right=(0, 0, -0.05), knee_left=(1.57, 0, 0),
             knee_right=(1.57, 0, 0), ankle_left=(1.35, 0, 0), ankle_right=(1.35, 0, 0))
KNEEL_SIT = pose(spine=(0.04, 0, 0), hip_left=(-1.30, 0, 0.07), hip_right=(-1.30, 0, -0.07), knee_left=(2.75, 0, 0),
                 knee_right=(2.75, 0, 0), ankle_left=(1.30, 0, 0), ankle_right=(1.30, 0, 0),
                 reach={side: replace(SIT.reach[side], target=(f"hip_{side}", (sign * 0.02, 1.02, 0.30)))
                        for side, sign in (("left", 1.0), ("right", -1.0))})
LIE_BACK = pose(pelvis=(-1.52, 0, 0), head=(0.0, 0.25, 0), shoulder_left=(0, 0, 0.32),
                shoulder_right=(0, 0, -0.32), elbow_left=(-0.25, 0, 0), elbow_right=(-0.25, 0, 0),
                hip_left=(0.04, 0, 0.07), hip_right=(0.04, 0, -0.07), ankle_left=(0.45, -0.15, 0), ankle_right=(0.45, 0.15, 0))
CUPPED = HandPose3D(curl={"index": 0.30, "middle": 0.34, "ring": 0.40, "pinky": 0.46}, spread=0.06, thumb_out=0.55,
                    thumb_curl=0.20)      # chin resting in the hands
LIE_FRONT = pose(pelvis=(np.pi / 2, 0, 0), spine=(-0.40, 0, 0), chest=(-0.35, 0, 0), neck=(-0.25, 0, 0),
                 head=(-0.30, 0, 0), hip_left=(0, 0, 0.05), hip_right=(0, 0, -0.05), knee_left=(1.70, 0, 0.10),
                 knee_right=(1.20, 0, -0.10), ankle_left=(0.50, 0, 0), ankle_right=(0.50, 0, 0),
                 hands={"left": CUPPED, "right": CUPPED},
                 reach={"left": Reach(("head", (-0.22, 0.74, 0.28)), pole=(-1.0, 1.0, 0.3),
                                      fingers=(0.2, -1.0, 0.3), palm=(0.0, 0.0, -1.0)),
                        "right": Reach(("head", (0.22, 0.74, 0.28)), pole=(1.0, 1.0, 0.3),
                                       fingers=(-0.2, -1.0, 0.3), palm=(0.0, 0.0, -1.0))})
# Hands flat in the front pockets, thumbs tucked in: the fingers point down and into the hips, so the hand
# sinks under the trousers and only the wrist shows at the pocket opening (wardrobe3d.pocket_hands).
POCKET_GRIP = HandPose3D(curl={"index": 0.20, "middle": 0.22, "ring": 0.25, "pinky": 0.28}, spread=0.02, thumb_out=0.30,
                         thumb_curl=0.15)
HANDS_IN_POCKETS = pose(head=(0.0, 0.08, 0.04), hip_left=(0, 0, 0.06), hip_right=(0, 0, -0.04), **_FEET,
                        hands={"left": POCKET_GRIP, "right": POCKET_GRIP},
                        reach={"left": Reach(("pelvis", (-0.48, -0.02, 0.30)), pole=(-1.0, 0.0, -0.5),
                                             fingers=(0.20, 1.0, -0.45), palm=(0.6, 0.0, -0.8)),
                               "right": Reach(("pelvis", (0.48, -0.02, 0.30)), pole=(1.0, 0.0, -0.5),
                                              fingers=(-0.20, 1.0, -0.45), palm=(-0.6, 0.0, -0.8))})
# A cigarette between the index and middle fingers (props3d.held_cigarette): those two fingers straight, the others
# curled into the palm.
SMOKE_GRIP = HandPose3D(curl={"index": 0.18, "middle": 0.22, "ring": 1.05, "pinky": 1.15}, spread=0.0, thumb_out=0.35,
                        thumb_curl=0.55)
# Standing, the left hand in a pocket, the right hanging forward at the hip with the cigarette pointing out.
STAND_SMOKE = pose(head=(0.06, 0.10, 0.02), hip_left=(0, 0, 0.06), hip_right=(0, 0, -0.04), **_FEET,
                   hands={"left": POCKET_GRIP, "right": SMOKE_GRIP},
                   reach={"left": HANDS_IN_POCKETS.reach["left"],
                          "right": Reach(("pelvis", (0.50, -0.30, 0.42)), pole=(1.0, 0.2, -0.6),
                                         fingers=(0.10, 0.45, 1.0), palm=(-1.0, 0.0, 0.0))})
# Sitting, the left hand on the lap, the right raised in front of the chest, the cigarette pointing forward.
SIT_SMOKE = pose(spine=(0.10, 0, 0), head=(0.04, -0.10, 0.0), **_SIT_LEGS, hands={"left": RELAXED, "right": SMOKE_GRIP},
                 reach={"left": _LAP["left"],
                        "right": Reach(("chest", (0.48, 0.30, 0.72)), pole=(1.0, 0.8, -0.3), fingers=(0.0, -1.0, 0.25),
                                       palm=(0.0, 0.0, -1.0))})

POSES = {"stand": STAND, "a_pose": A_POSE_3D, "contrapposto": CONTRAPPOSTO, "hand_on_hip": HAND_ON_HIP,
         "arms_crossed": ARMS_CROSSED, "walk": WALK, "sit": SIT, "wave": WAVE, "point": POINT, "think": THINK,
         "hands_behind": HANDS_BEHIND, "cheer": CHEER, "peace": PEACE_SIGN,
         "sit_type": SIT_TYPE, "stand_phone": STAND_PHONE, "sit_phone": SIT_PHONE, "stand_mug": STAND_MUG,
         "sit_mug": SIT_MUG, "sit_game": SIT_GAME, "run": RUN, "kneel": KNEEL, "kneel_sit": KNEEL_SIT,
         "lie_back": LIE_BACK, "lie_front": LIE_FRONT, "hands_in_pockets": HANDS_IN_POCKETS,
         "stand_smoke": STAND_SMOKE, "sit_smoke": SIT_SMOKE}
SEAT_HEIGHT = 1.62    # head heights from the pelvis origin down to the seat top in the SIT pose
