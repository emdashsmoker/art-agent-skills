"""Full-figure rig: a clothed adult female figure built on a jointed skeleton, front view.

Lengths are in head heights (crown to chin = 1); the standing figure is about
7.5 heads tall. Limb lengths are fixed constants, so a Pose can only rotate
joints, and a BodyShape can only scale widths within a plausible range. That
is what keeps any pose and any build anatomically plausible.

The body is assembled in a Relief: base forms (torso, limbs) are inflated and
merged, then soft swellings and grooves add the anatomy a silhouette lacks.
Outfits are layers on top of that body (see OUTFITS), so one body can be
dressed in any registered outfit.
"""
from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from . import props, rig_face, rig_hair, rig_hand, shading
from .character import Character, Head
from .geometry import Frame, catmull_rom, ellipse, ribbon
from .relief import FRONT, Relief, inflate

# ---- skeleton (head heights) ---------------------------------------------------
PELVIS_TO_CHEST = 1.72
SHOULDER_JOINT = (0.60, -0.36)      # in the chest frame
HIP_JOINT = (0.37, 0.02)            # in the pelvis frame
UPPER_ARM, FOREARM, HAND = 1.30, 1.08, 0.74
THIGH, SHIN = 1.85, 1.63
NECK_ROOT_Y = -0.60                 # chest frame
CHIN_ABOVE_NECK_ROOT = 0.30
HEAD_RADIUS_PER_HEAD_HEIGHT = 1 / 2.2    # the face rig's skull radius, in head heights
CHIN_BELOW_HEAD_CENTER = 1.20            # in skull radii (see rig_face)

# ---- surface (head heights) ------------------------------------------------------
# Half outline of the torso, top to bottom: (x, y, frame, width channel) with frame 'c' chest,
# 'w' waist, 'p' pelvis. The channel names the BodyShape value that scales the point's x.
TORSO_HALF = ((0.17, -0.62, "c", "fixed"), (0.40, -0.53, "c", "fixed"), (0.65, -0.41, "c", "fixed"),
              (0.71, -0.20, "c", "bust"), (0.56, 0.04, "c", "bust"), (0.51, 0.42, "c", "ribs"),
              (0.375, 0.00, "w", "waist"), (0.58, -0.36, "p", "hips"), (0.76, 0.08, "p", "hips"),
              (0.66, 0.26, "p", "hips"), (0.36, 0.36, "p", "thighs"))
BUST_SILHOUETTE = 0.30              # share of the bust scale that widens the chest outline
HIP_JOINT_SPREAD = 0.60             # share of the hip scale that moves the hip joints apart
CROTCH = (0.0, 0.27)
WAIST_SHARE = 0.56                  # waist position between chest centre and pelvis centre
TORSO_THICKNESS = 0.72              # a torso is flatter than it is wide
LIMB_THICKNESS = 0.92
NECK_WIDTH = 0.34
UPPER_ARM_WIDTHS = (0.33, 0.33, 0.29, 0.245)
FOREARM_WIDTHS = (0.245, 0.265, 0.225, 0.185)
THIGH_WIDTHS = (0.70, 0.68, 0.57, 0.43, 0.36)
SHIN_WIDTHS = (0.345, 0.405, 0.345, 0.225, 0.175)
# Foot seen from the front, ankle at the origin, x toward the big toe (mirrored per side).
FOOT_OUTLINE = ((-0.085, -0.06), (0.085, -0.06), (0.11, 0.10), (0.16, 0.25), (0.15, 0.36), (0.02, 0.40),
                (-0.12, 0.37), (-0.15, 0.24), (-0.11, 0.10))
FOOT_THICKNESS = 0.6
# Toes along the front edge: (x, y, radius x, radius y), big toe first.
TOES = ((0.095, 0.375, 0.050, 0.046), (0.030, 0.388, 0.034, 0.034), (-0.022, 0.382, 0.030, 0.031),
        (-0.068, 0.368, 0.027, 0.028), (-0.108, 0.348, 0.024, 0.025))
ANKLE_BONE = (0.075, 0.02, 0.040, 0.045, 0.012)

# Breast: an edged swelling (centre x, centre y, radius x, radius y, thickness) in the chest frame.
BREAST = (0.285, 0.175, 0.265, 0.275, 0.62)
BREAST_SOFT_TOP = 0.70              # share of the breast height over which its upper slope fades in
BREAST_SPREAD = 0.25                # centre moves outward per unit of extra bust (keeps a cleavage gap)
BREAST_DROP = 0.25                  # centre moves down per unit of extra bust (fuller breasts sit lower)
BREAST_PROJECTION = 0.80            # share of the extra bust added to the projection
UNDERBUST_FOLD = 0.020              # groove depth under the breast per unit of bust (head heights)
# Soft swellings without an edge: (centre x, centre y, radius x, radius y, height); x is mirrored.
DELTOID = (0.66, -0.20, 0.20, 0.30, 0.050)
HIP_BONE = (0.44, -0.30, 0.18, 0.15, 0.016)
OUTER_HIP = (0.62, 0.10, 0.22, 0.34, 0.060)
BELLY = (0.0, -0.30, 0.34, 0.30, 0.050)
# Inflating the torso treats the crotch point as an edge, so the lower abdomen falls away too
# steeply and reads as a dark band. This fills it back to the gentle slope of a real pelvis.
LOWER_ABDOMEN = (0.0, 0.14, 0.40, 0.26, 0.17)
KNEECAP = (0.0, 0.0, 0.17, 0.20, 0.035)
CALF = (0.0, 0.26, 0.20, 0.36, 0.030)        # relative to the knee, along the shin
# Grooves: polylines per frame with (half width, depth) in head heights.
COLLARBONE = ((0.07, -0.52), (0.30, -0.535), (0.56, -0.47))
STERNUM = ((0.0, -0.36), (0.0, 0.52))
MIDLINE = ((0.0, -1.00), (0.0, -0.48))          # pelvis frame: abdomen centre line down to the navel
NAVEL = (0.0, -0.46)
GROIN_FOLD = ((0.50, -0.20), (0.30, 0.08), (0.12, 0.24))
RIB_ARCH = ((0.04, 0.50), (0.22, 0.60), (0.42, 0.56))      # chest frame: lower edge of the ribcage
GROOVE_SOFTNESS = 0.045
SKIN_GLOSS = 0.06
SKIN_PARTS = ("body", "arm", "foot")
HAND_TURN = 0.66                    # hands of a standing figure are seen partly edge-on
IN_FRONT_CLEARANCE = 1.15           # how far a limb marked in_front rises above the tallest form

HEAD_SHADOW_DROP = (0.10, 0.27)     # skull radii the head's shadow falls on the neck
HAIR_SHADOW_DROP = (0.05, 0.07)
GROUND_SHADOW = (0.9, 0.16)         # half width and half height of the shadow under the feet


class FigureOutfit(str, Enum):
    SUNDRESS = "sundress"    # bodice, flared skirt, flat shoes
    BIKINI = "bikini"        # triangle top, high-cut briefs with side ties, barefoot


@dataclass(frozen=True)
class BodyShape:
    """Width scales relative to an average adult female build (1.0 each).
    Keep values within about 0.8-1.4; beyond that the body stops looking plausible."""

    bust: float = 1.0
    waist: float = 1.0
    hips: float = 1.0
    thighs: float = 1.0

    def channel(self, name):
        return {"fixed": 1.0, "bust": 1.0 + (self.bust - 1.0) * BUST_SILHOUETTE,
                "ribs": (1.0 + self.waist) / 2, "waist": self.waist, "hips": self.hips,
                "thighs": self.thighs}[name]


AVERAGE = BodyShape()
SLENDER = BodyShape(bust=0.9, waist=0.92, hips=0.95, thighs=0.92)
HOURGLASS = BodyShape(bust=1.32, waist=0.84, hips=1.12, thighs=1.06)


@dataclass(frozen=True)
class Pose:
    """Joint angles in radians. Limb angles are measured from straight down;
    positive swings toward image-right. Tilts are clockwise-positive, so a
    positive tilt lowers the image-right side."""

    hip_tilt: float = 0.0
    shoulder_tilt: float = 0.0
    spine_lean: float = 0.0          # sideways shift of the chest over the pelvis (head heights)
    head_roll: float = 0.0
    head_yaw: float = 0.0
    upper_arm_left: float = -0.14
    forearm_left: float = -0.05
    upper_arm_right: float = 0.14
    forearm_right: float = 0.05
    thigh_left: float = -0.04
    shin_left: float = 0.0
    thigh_right: float = 0.04
    shin_right: float = 0.0
    foot_left: float = -0.20
    foot_right: float = 0.20
    wrist_left: float = 0.0          # hand angle relative to the forearm
    wrist_right: float = 0.0
    hand_left: rig_hand.HandPose = rig_hand.RELAXED_HAND
    hand_right: rig_hand.HandPose = rig_hand.RELAXED_HAND
    # Limbs listed here are drawn in front of the torso (e.g. a hand resting on the hip).
    arm_left_in_front: bool = False
    arm_right_in_front: bool = False


STANDING = Pose()
CONTRAPPOSTO = Pose(hip_tilt=0.13, shoulder_tilt=-0.09, spine_lean=0.12, head_roll=0.06, head_yaw=-0.18,
                    upper_arm_left=-0.27, forearm_left=-0.10, upper_arm_right=0.22, forearm_right=0.08,
                    thigh_left=0.00, shin_left=0.02, thigh_right=0.13, shin_right=-0.08,
                    foot_left=-0.12, foot_right=0.32)
# The wrist turns the fingers down so the hand rests on the side of the hip, not on the belly.
HAND_ON_HIP = replace(CONTRAPPOSTO, upper_arm_right=0.66, forearm_right=-0.98, wrist_right=1.15,
                      arm_right_in_front=True)
# A-pose: arms held clear of the body, legs slightly apart. The neutral base for dressing up.
A_POSE = Pose(upper_arm_left=-0.42, forearm_left=-0.18, upper_arm_right=0.42, forearm_right=0.18,
              thigh_left=-0.07, thigh_right=0.07, shin_left=0.02, shin_right=-0.02, foot_left=-0.25, foot_right=0.25)
ARM_RAISED = replace(CONTRAPPOSTO, upper_arm_left=-2.70, forearm_left=1.93, head_roll=-0.07, head_yaw=0.16)


@dataclass(frozen=True)
class Figure:
    character: Character             # palette, hair and face; its head placement is set by the pose
    pose: Pose = CONTRAPPOSTO
    pelvis: tuple = (500.0, 640.0)   # canvas units
    head_height: float = 158.0       # canvas units per head height
    outfit: FigureOutfit = FigureOutfit.SUNDRESS
    body: BodyShape = AVERAGE
    outfit_material: object = None   # Material for swimwear and similar; None uses palette.trim
    head_scale: float = 1.0          # 1.0 = realistic 7.5 heads; 1.15-1.25 gives the larger head of anime figures
    ground_y: float = None           # canvas y of the floor for the cast shadow; None = no shadow


class Skeleton:
    """Forward kinematics: Pose -> joint positions on the canvas."""

    def __init__(self, figure):
        pose, scale = figure.pose, figure.head_height
        self.scale = scale
        self.pelvis = Frame(figure.pelvis, scale, pose.hip_tilt)
        chest_center = (figure.pelvis[0] + pose.spine_lean * scale, figure.pelvis[1] - PELVIS_TO_CHEST * scale)
        self.chest = Frame(chest_center, scale, pose.shoulder_tilt)
        waist_center = (np.asarray(chest_center) * (1 - WAIST_SHARE) + np.asarray(figure.pelvis) * WAIST_SHARE)
        self.waist = Frame(tuple(waist_center), scale, (pose.hip_tilt + pose.shoulder_tilt) / 2)
        self.body = figure.body
        self.joints = {}
        for side, sign in (("left", -1.0), ("right", 1.0)):
            shoulder = self.chest.apply([(sign * SHOULDER_JOINT[0], SHOULDER_JOINT[1])])[0]
            elbow = shoulder + _direction(getattr(pose, f"upper_arm_{side}")) * UPPER_ARM * scale
            wrist = elbow + _direction(getattr(pose, f"forearm_{side}")) * FOREARM * scale
            hip_x = HIP_JOINT[0] * (1.0 + (figure.body.hips - 1.0) * HIP_JOINT_SPREAD)
            hip = self.pelvis.apply([(sign * hip_x, HIP_JOINT[1])])[0]
            knee = hip + _direction(getattr(pose, f"thigh_{side}")) * THIGH * scale
            ankle = knee + _direction(getattr(pose, f"shin_{side}")) * SHIN * scale
            self.joints[side] = dict(shoulder=shoulder, elbow=elbow, wrist=wrist, hip=hip, knee=knee, ankle=ankle)
        self.neck_root = self.chest.apply([(0.0, NECK_ROOT_Y)])[0]
        self.chin = self.neck_root + np.array([0.0, -CHIN_ABOVE_NECK_ROOT * scale])

    def frame(self, key):
        return {"c": self.chest, "w": self.waist, "p": self.pelvis}[key]


def _direction(angle):
    return np.array([np.sin(angle), np.cos(angle)])


def _limb(start, end, widths, scale, samples=24):
    """Tapered limb with round joints. widths are sampled evenly from start to end."""
    t = np.linspace(0.0, 1.0, samples)
    center = np.asarray(start)[None, :] * (1 - t[:, None]) + np.asarray(end)[None, :] * t[:, None]
    profile = np.interp(t, np.linspace(0.0, 1.0, len(widths)), widths) * scale
    return [ribbon(center, profile), ellipse(start, profile[0] / 2, profile[0] / 2, samples=32),
            ellipse(end, profile[-1] / 2, profile[-1] / 2, samples=32)]


def _limb_chain(joints, widths_per_segment, scale, samples=24):
    """One continuous limb through several joints (hip-knee-ankle). Inflating it as a
    single shape keeps the knee or elbow smooth; separate segments leave a crease."""
    centers, profiles = [], []
    for index, widths in enumerate(widths_per_segment):
        start, end = np.asarray(joints[index]), np.asarray(joints[index + 1])
        t = np.linspace(0.0, 1.0, samples)[1 if index else 0:]
        centers.append(start[None, :] * (1 - t[:, None]) + end[None, :] * t[:, None])
        profiles.append(np.interp(t, np.linspace(0.0, 1.0, len(widths)), widths) * scale)
    center, profile = np.vstack(centers), np.concatenate(profiles)
    # A disc at every joint fills the outside of a bend; joint k takes the width where segment k starts.
    joint_widths = [segment[0] for segment in widths_per_segment] + [widths_per_segment[-1][-1]]
    shapes = [ribbon(center, profile)]
    for joint, width in zip(joints, joint_widths):
        shapes.append(ellipse(joint, width * scale / 2, width * scale / 2, samples=32))
    return shapes


def _along(canvas, start, end):
    """0 at start rising to 1 at end, measured along the line between them."""
    xs, ys = canvas.grid()
    axis = np.asarray(end) - np.asarray(start)
    return np.clip(((xs - start[0]) * axis[0] + (ys - start[1]) * axis[1]) / (axis @ axis + 1e-9), 0.0, 1.0)


def _torso_outline(skeleton):
    body = skeleton.body
    right = np.array([skeleton.frame(key).apply([(x * body.channel(ch), y)])[0] for x, y, key, ch in TORSO_HALF])
    left = np.array([skeleton.frame(key).apply([(-x * body.channel(ch), y)])[0] for x, y, key, ch in TORSO_HALF])
    crotch = skeleton.pelvis.apply([CROTCH])
    return catmull_rom(np.vstack([right, crotch, left[::-1]]), closed=True)


def head_character(figure, skeleton):
    """The Character placed on this skeleton (head size, position and turn come from the pose)."""
    radius = figure.head_height * HEAD_RADIUS_PER_HEAD_HEIGHT * figure.head_scale
    lower_face = figure.character.lower_face
    center = (skeleton.chin[0], skeleton.chin[1] - CHIN_BELOW_HEAD_CENTER * lower_face * radius)
    return replace(figure.character, head_center=center, head_radius=radius, roll=figure.pose.head_roll,
                   yaw=figure.pose.head_yaw)


def draw_figure(painter, figure):
    """Draw the whole figure back to front. Returns (relief, skeleton)."""
    canvas = painter.canvas
    skeleton = Skeleton(figure)
    character = head_character(figure, skeleton)
    head = Head(character)
    hair_polygons = rig_hair.front_polygons(character, head)
    front_hair = rig_hair.front_mask(canvas, hair_polygons)
    face_shape = canvas.mask(rig_face.face_outline(head))

    if figure.ground_y is not None:
        _ground_shadow(canvas, figure, skeleton)
    rig_hair.draw_back_hair(painter, character, head)

    relief = Relief(canvas)
    _build_trunk_and_legs(relief, figure, skeleton)
    # Arms that hang behind the clothes go on before them, arms in front after.
    finish_hands = [_add_arm(relief, painter, figure, skeleton, side) for side in ("left", "right")
                    if not getattr(figure.pose, f"arm_{side}_in_front")]
    _anatomy(relief, figure, skeleton)
    finish_outfit = dress(relief, painter, figure, skeleton)
    finish_hands += [_add_arm(relief, painter, figure, skeleton, side) for side in ("left", "right")
                     if getattr(figure.pose, f"arm_{side}_in_front")]
    skin = character.palette.skin
    for occluder, drop in ((face_shape, HEAD_SHADOW_DROP), (front_hair, HAIR_SHADOW_DROP)):
        cast = painter.cast(occluder, relief.cover, (head.units(drop[0]), head.units(drop[1])))
        relief.tint(cast, skin.shadow, 0.8, only=SKIN_PARTS)
    relief.render(painter)
    for finish in finish_hands + [finish_outfit]:
        finish()

    face = rig_face.draw_face(painter, character, head, front_hair)
    rig_face.draw_features(painter, character, head, face)
    rig_hair.draw_front_hair(painter, character, head, hair_polygons, face)
    rig_face.draw_brows_and_lashes_over_hair(painter, character, head, 0.35)
    return relief, skeleton


# ---- body ----------------------------------------------------------------------
def _build_trunk_and_legs(relief, figure, skeleton):
    canvas = relief.canvas
    skin = figure.character.palette.skin
    scale = skeleton.scale
    for side in ("left", "right"):                       # legs first: the torso sits on them
        joints = skeleton.joints[side]
        thigh_widths = np.asarray(THIGH_WIDTHS) * figure.body.thighs
        leg = _limb_chain([joints["hip"], joints["knee"], joints["ankle"]], [thigh_widths, SHIN_WIDTHS], scale)
        relief.add("body", canvas.mask(*leg), skin, thickness=LIMB_THICKNESS, gloss=SKIN_GLOSS)
        _add_foot(relief, skeleton, figure, side, skin)
    relief.add("body", canvas.mask(_torso_outline(skeleton)), skin, thickness=TORSO_THICKNESS, gloss=SKIN_GLOSS)
    neck = ribbon(np.linspace(skeleton.neck_root + np.array([0.0, 0.12 * scale]),
                              skeleton.chin - np.array([0.0, 0.25 * scale]), 8), np.full(8, NECK_WIDTH * scale))
    relief.add("body", canvas.mask(neck), skin, thickness=LIMB_THICKNESS, gloss=SKIN_GLOSS)


def foot_frame(skeleton, figure, side):
    """Foot frame: origin at the ankle; x points to the big toe, which lies toward the body's midline."""
    inward = 1.0 if side == "left" else -1.0
    frame = Frame(tuple(skeleton.joints[side]["ankle"]), skeleton.scale, -getattr(figure.pose, f"foot_{side}"))
    return frame, np.array([inward, 1.0])


def _add_foot(relief, skeleton, figure, side, skin):
    canvas = relief.canvas
    frame, mirror = foot_frame(skeleton, figure, side)
    relief.add("foot", canvas.mask(catmull_rom(frame.apply(np.asarray(FOOT_OUTLINE) * mirror), closed=True)), skin,
               thickness=FOOT_THICKNESS, gloss=SKIN_GLOSS)
    for x, y, radius_x, radius_y in TOES:
        toe = frame.apply(ellipse((x * mirror[0], y), radius_x, radius_y, samples=24))
        relief.bump(canvas.mask(toe), 0.35)
    x, y, radius_x, radius_y, height = ANKLE_BONE
    _soft_swelling(relief, frame, (x * mirror[0], y, radius_x, radius_y, height))


def _add_arm(relief, painter, figure, skeleton, side):
    """Upper arm, forearm and hand of one side. Returns the hand's finishing callable."""
    canvas = relief.canvas
    skin = figure.character.palette.skin
    scale, pose = skeleton.scale, figure.pose
    joints = skeleton.joints[side]
    # Arms are a separate part so clothes clipped to the body never spill onto a hanging arm.
    # They grow out of the shoulder, so they leave no overlap line there (edge=False).
    depth = 0.0
    if not getattr(pose, f"arm_{side}_in_front"):
        arm = _limb_chain([joints["shoulder"], joints["elbow"], joints["wrist"]], [UPPER_ARM_WIDTHS, FOREARM_WIDTHS],
                          scale)
        relief.add("arm", canvas.mask(*arm), skin, thickness=LIMB_THICKNESS, gloss=SKIN_GLOSS, edge=False)
    else:
        relief.add("arm", canvas.mask(*_limb(joints["shoulder"], joints["elbow"], UPPER_ARM_WIDTHS, scale)), skin,
                   thickness=LIMB_THICKNESS, gloss=SKIN_GLOSS, edge=False)
        forearm = canvas.mask(*_limb(joints["elbow"], joints["wrist"], FOREARM_WIDTHS, scale))
        # The forearm rises steadily from the elbow to clear the torso at the wrist;
        # a constant offset would show a step at the elbow like a doll joint.
        depth = float(relief.height.max()) / canvas.px_per_unit * IN_FRONT_CLEARANCE
        lift = _along(canvas, joints["elbow"], joints["wrist"]) * canvas.px(depth)
        relief.add("arm", forearm, skin, height=inflate(forearm) * LIMB_THICKNESS + lift, gloss=SKIN_GLOSS)
    hand_angle = getattr(pose, f"forearm_{side}") + getattr(pose, f"wrist_{side}")
    hand_frame = Frame(tuple(joints["wrist"]), HAND * scale, -hand_angle)
    return rig_hand.draw_hand(relief, painter, hand_frame, skin, getattr(pose, f"hand_{side}"),
                              rig_hand.HandView.BACK, side == "right", name="hand", depth=depth, turn=HAND_TURN)


def breast_geometry(body, sign):
    """Breast centre (chest frame), radii and projection for a BodyShape. sign: -1 left, +1 right."""
    x, y, radius_x, radius_y, thickness = BREAST
    extra = body.bust - 1.0
    center = (sign * (x + extra * BREAST_SPREAD), y + extra * BREAST_DROP)
    return center, radius_x * body.bust, radius_y * body.bust, thickness * (1.0 + extra * BREAST_PROJECTION)


def _soft_swelling(relief, frame, spec, sign=1.0):
    x, y, radius_x, radius_y, height = spec
    center = frame.apply([(sign * x, y)])[0]
    blob = relief.canvas.soft_ellipse(center, radius_x * frame.scale, radius_y * frame.scale, frame.rotation)
    relief.swell(blob, height * frame.scale)


def _groove_line(relief, frame, points, sign, half_width, depth):
    canvas = relief.canvas
    curve = catmull_rom(frame.apply(np.asarray(points) * np.array([sign, 1.0])))
    line = canvas.mask(ribbon(curve, np.full(len(curve), half_width * 2 * frame.scale)))
    relief.groove(shading.blur(line, canvas.px(GROOVE_SOFTNESS * frame.scale)), canvas.px(depth * frame.scale))


def _anatomy(relief, figure, skeleton):
    """Swellings and grooves that turn merged tubes into a body."""
    canvas = relief.canvas
    skin = figure.character.palette.skin
    chest, pelvis, scale = skeleton.chest, skeleton.pelvis, skeleton.scale
    _, ys = canvas.grid()

    for side, sign in (("left", -1.0), ("right", 1.0)):
        _soft_swelling(relief, chest, DELTOID, sign)
        _soft_swelling(relief, pelvis, HIP_BONE, sign)
        x, y, radius_x, radius_y, height = OUTER_HIP
        _soft_swelling(relief, pelvis, (x * figure.body.hips, y, radius_x, radius_y, height * figure.body.hips), sign)
        # Breast: a full lower curve that grows gently out of the chest above it. Each side is
        # clipped at the midline so the two never add up; the gap between them is the cleavage.
        center, radius_x, radius_y, thickness = breast_geometry(figure.body, sign)
        shape = chest.apply(ellipse(center, radius_x, radius_y, samples=64))
        side_only = canvas.mask(chest.apply([(0.0, -3.0), (sign * 3.0, -3.0), (sign * 3.0, 3.0), (0.0, 3.0)]))
        top = float(shape[:, 1].min())
        fade = shading.smoothstep(top, top + 2 * radius_y * scale * BREAST_SOFT_TOP, ys)
        relief.bump(canvas.mask(shape) * side_only, thickness, fade)
        fold = [(center[0] + sign * radius_x * np.cos(a), center[1] + radius_y * np.sin(a) * 0.96)
                for a in np.linspace(0.35, 2.6, 6)]
        _groove_line(relief, chest, [(abs(px), py) for px, py in fold], sign, 0.016,
                     UNDERBUST_FOLD * max(figure.body.bust - 0.8, 0.0) * 2)
        _groove_line(relief, chest, COLLARBONE, sign, 0.012, -0.020)       # negative depth = raised ridge
        _groove_line(relief, chest, RIB_ARCH, sign, 0.020, 0.012)
        _groove_line(relief, pelvis, GROIN_FOLD, sign, 0.016, 0.016)
        joints = skeleton.joints[side]
        shin_angle = getattr(figure.pose, f"shin_{side}")
        knee = Frame(tuple(joints["knee"]), scale, -shin_angle)
        _soft_swelling(relief, knee, KNEECAP)
        _soft_swelling(relief, knee, CALF)
    _soft_swelling(relief, pelvis, BELLY)
    _soft_swelling(relief, pelvis, LOWER_ABDOMEN)
    _groove_line(relief, chest, STERNUM, 1.0, 0.022, 0.026)
    _groove_line(relief, pelvis, MIDLINE, 1.0, 0.018, 0.016)
    navel = pelvis.apply([NAVEL])[0]
    relief.groove(canvas.soft_ellipse(navel, 0.030 * scale, 0.050 * scale), canvas.px(0.06 * scale))
    relief.tint(canvas.soft_ellipse(navel, 0.030 * scale, 0.045 * scale), skin.shadow, 0.55, only=SKIN_PARTS)

    blush = figure.character.palette.blush
    for side in ("left", "right"):
        joints = skeleton.joints[side]
        for key, radius in (("knee", 0.20), ("elbow", 0.14), ("shoulder", 0.20)):
            relief.tint(canvas.soft_ellipse(joints[key], radius * scale, radius * scale), blush, 0.16,
                        only=SKIN_PARTS)


def _ground_shadow(canvas, figure, skeleton):
    center_x = (skeleton.joints["left"]["ankle"][0] + skeleton.joints["right"]["ankle"][0]) / 2
    shadow = canvas.soft_ellipse((center_x + 0.25 * skeleton.scale, figure.ground_y),
                                 GROUND_SHADOW[0] * skeleton.scale, GROUND_SHADOW[1] * skeleton.scale)
    canvas.rgb = (canvas.rgb * (1 - shadow[..., None] * 0.45)).astype(np.float32)


# ---- clothes -------------------------------------------------------------------
DRESS_NECKLINE = ((-0.60, -0.06), (-0.36, -0.02), (0.0, 0.06), (0.36, -0.02), (0.60, -0.06))   # chest frame
DRESS_STRAP = ((0.40, -0.03), (0.37, -0.30), (0.30, -0.56))
DRESS_STRAP_WIDTH = 0.085
SKIRT_WAIST_HALF = 0.44
SKIRT_HEM = (1.02, 1.42)            # half width and drop below the pelvis centre (head heights)
SKIRT_HEM_WAVES = 7
SKIRT_UPPER_HIP = (0.64, -0.36)     # pelvis frame; just outside the torso outline at that height
SKIRT_FOLD_HEIGHT = 0.045
SHOE_TOP = -0.06                     # foot frame y where the shoe begins


def dress(relief, painter, figure, skeleton):
    """Put the figure's outfit on the body. Returns a callable for details drawn after lighting."""
    layer = OUTFITS.get(figure.outfit)
    if layer is None:
        raise ValueError(f"no drawing routine for outfit: {figure.outfit}")
    finish = layer(relief, painter, figure, skeleton)
    return finish if finish is not None else (lambda: None)


def _sundress(relief, painter, figure, skeleton):
    canvas = relief.canvas
    palette = figure.character.palette
    chest, waist, pelvis, scale = skeleton.chest, skeleton.waist, skeleton.pelvis, skeleton.scale

    # Bodice: everything on the torso between the neckline and the waist follows the body.
    neckline = catmull_rom(chest.apply(DRESS_NECKLINE))
    waist_line = waist.apply([(0.9, 0.12), (-0.9, 0.12)])
    torso_only = canvas.mask(_torso_outline(skeleton))
    bodice = canvas.mask(np.vstack([neckline, waist_line])) * torso_only
    relief.add("cloth", bodice, palette.cloth, drape=True, depth=1.0)
    for sign in (-1.0, 1.0):
        strap_center = catmull_rom(chest.apply(np.asarray(DRESS_STRAP) * np.array([sign, 1.0])))
        strap = ribbon(strap_center, np.full(len(strap_center), DRESS_STRAP_WIDTH * scale))
        relief.add("cloth", canvas.mask(strap) * torso_only, palette.cloth, drape=True, depth=1.0)

    # Skirt: its own flared form in front of the thighs, with a wavy hem and soft folds.
    hem_x = np.linspace(-SKIRT_HEM[0], SKIRT_HEM[0], SKIRT_HEM_WAVES * 4 + 1) * figure.body.hips
    hem_y = SKIRT_HEM[1] + 0.035 * np.sin(np.linspace(0, SKIRT_HEM_WAVES * 2 * np.pi, len(hem_x)))
    hem = pelvis.apply(np.stack([hem_x, hem_y], axis=1))
    waist_half = SKIRT_WAIST_HALF * figure.body.waist
    top = waist.apply([(-waist_half, 0.06), (waist_half, 0.06)])
    hip_half = 0.76 * figure.body.hips
    hip = pelvis.apply([(hip_half, 0.02), (-hip_half, 0.02)])
    # The skirt passes over the upper hip slightly outside the body so no skin shows beside it.
    upper_hip = pelvis.apply([(SKIRT_UPPER_HIP[0] * figure.body.hips, SKIRT_UPPER_HIP[1]),
                              (-SKIRT_UPPER_HIP[0] * figure.body.hips, SKIRT_UPPER_HIP[1])])
    outline = np.vstack([top[0:1], top[1:2], upper_hip[0:1], hip[0:1], hem[::-1], hip[1:2], upper_hip[1:2]])
    skirt = canvas.mask(outline)
    xs, _ = canvas.grid()
    pleats = 0.5 + 0.5 * np.sin((xs - figure.pelvis[0]) / (SKIRT_HEM[0] * scale) * np.pi * SKIRT_HEM_WAVES)
    height = inflate(skirt) * 0.30 + pleats * canvas.px(SKIRT_FOLD_HEIGHT * scale) * shading.blur(skirt, canvas.px(6))
    relief.add("cloth", skirt, palette.cloth, height=height.astype(np.float32), depth=FRONT)
    belt = waist.apply([(-waist_half, 0.0), (waist_half, 0.0), (waist_half, 0.12), (-waist_half, 0.12)])
    relief.add("cloth_trim", canvas.mask(belt) * relief.cover, palette.trim, drape=True, depth=1.5)

    for side in ("left", "right"):
        frame, mirror = foot_frame(skeleton, figure, side)
        shoe = catmull_rom(frame.apply([(x * mirror[0], max(y, SHOE_TOP)) for x, y in FOOT_OUTLINE]), closed=True)
        relief.add("shoe", canvas.mask(shoe) * relief.visible("foot"), palette.trim, drape=True, depth=1.0)


# Bikini top: one cup per breast in breast-local units (u toward the outer side, v down,
# both scaled by the breast radii). The cup covers the whole front of the breast.
BIKINI_CUP = ((-0.10, -0.92), (0.55, -0.32), (0.95, 0.42), (0.32, 0.98), (-0.55, 0.88), (-0.82, 0.22))
BIKINI_CUP_APEX = 0
BIKINI_CUP_OUTER = 2
BIKINI_CUP_INNER = 4
BIKINI_NECK_TIE = (0.20, -0.66)     # chest frame; halter strings meet behind the neck
BIKINI_BAND_SIDE = (0.80, 0.42)     # chest frame; band runs round to the back
BIKINI_STRING = 0.030               # string width (head heights)
# Bikini bottom: right half in the pelvis frame, x scaled by the hips.
BIKINI_BRIEF_HALF = ((0.0, -0.16), (0.48, -0.14), (0.84, -0.10), (0.84, -0.01), (0.54, 0.05), (0.27, 0.20),
                     (0.07, 0.36))
BIKINI_TIE = (0.80, -0.05)          # pelvis frame; side tie position
BIKINI_TIE_SIZE = 0.085             # head heights
BIKINI_BRIDGE = 45.0                # canvas units of hollow the taut fabric spans (no dents at the groin)


def _bikini(relief, painter, figure, skeleton):
    canvas = relief.canvas
    material = figure.outfit_material or figure.character.palette.trim
    chest, pelvis, scale = skeleton.chest, skeleton.pelvis, skeleton.scale
    skin = relief.visible("body")            # never paint onto arms or hands
    string_width = BIKINI_STRING * scale

    def strap(points_chest):
        center = catmull_rom(chest.apply(points_chest))
        return canvas.mask(ribbon(center, np.full(len(center), string_width)))

    inner_corners = []
    for sign in (-1.0, 1.0):
        center, radius_x, radius_y, _ = breast_geometry(figure.body, sign)
        cup_local = [(center[0] + sign * u * radius_x, center[1] + v * radius_y) for u, v in BIKINI_CUP]
        cup = canvas.mask(catmull_rom(chest.apply(cup_local), closed=True))
        relief.add("swim", cup * skin, material, drape=True, depth=1.5, gloss=0.25)
        apex, outer, inner = (cup_local[i] for i in (BIKINI_CUP_APEX, BIKINI_CUP_OUTER, BIKINI_CUP_INNER))
        neck = (sign * BIKINI_NECK_TIE[0], BIKINI_NECK_TIE[1])
        relief.add("swim", strap([apex, ((apex[0] + neck[0]) / 2, (apex[1] + neck[1]) / 2 - 0.02), neck]) * skin,
                   material, drape=True, depth=1.0)
        side = (sign * BIKINI_BAND_SIDE[0] * figure.body.channel("bust"), BIKINI_BAND_SIDE[1])
        relief.add("swim", strap([outer, ((outer[0] + side[0]) / 2, (outer[1] + side[1]) / 2 + 0.02), side]) * skin,
                   material, drape=True, depth=1.0)
        inner_corners.append(inner)
    middle = (0.0, (inner_corners[0][1] + inner_corners[1][1]) / 2 - 0.02)
    relief.add("swim", strap([inner_corners[0], middle, inner_corners[1]]) * skin, material, drape=True, depth=1.0)

    hips = figure.body.hips
    right = [(x * hips, y) for x, y in BIKINI_BRIEF_HALF]
    left = [(-x, y) for x, y in right[::-1]]
    brief = canvas.mask(catmull_rom(pelvis.apply(right + left[1:-1]), closed=True))
    relief.add("swim", brief * skin, material, drape=True, depth=1.5, gloss=0.25, bridge=BIKINI_BRIDGE)

    def ties():
        for sign in (-1.0, 1.0):
            where = pelvis.apply([(sign * BIKINI_TIE[0] * hips, BIKINI_TIE[1])])[0]
            props.bow(painter, Frame(tuple(where), BIKINI_TIE_SIZE * scale, pelvis.rotation), material, name="swim")

    return ties


OUTFITS = {FigureOutfit.SUNDRESS: _sundress, FigureOutfit.BIKINI: _bikini}
