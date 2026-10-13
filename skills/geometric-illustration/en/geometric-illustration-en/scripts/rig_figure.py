"""Clothed figure for upper-body and full-body framing.

Why: the body under the clothes is the same adult mannequin as the figure
study (rig_anatomy), so arms, hands and legs have real form, overlaps and
contours. Garments are fitted to that body in 3D (garment3d): the knit top
is the torso grown by the knit, the belt wraps the waist section, the skirt
hangs from the waist over the hips. Arms and hands are re-drawn above the
garments (and above the face or hair for gestures that touch them) as
selection overlays of the body.
"""
from dataclasses import replace

import numpy as np

import geom
import mannequin as M
import marks
import outfits
import rig_anatomy as A
from palette import darken, line_color
from scene import Drawable

Z = dict(collar_back=-0.05, body=0.0, shoe=0.4, cloth=2.0, skirt=2.2, belt=2.3, arms=2.5)   # collar_back: behind the neck
NECK_Y, HIP_Y = 0.98, 3.40
HAND_PIECES = ('palm', 'index', 'middle', 'ring', 'pinky', 'thumb')


def _limb(target, pole, hand='relaxed', hand_u=None, hand_n=(0, 0, 1), foot_dir=(0, 0, 1)):
    return A.Limb(tuple(target), tuple(pole), hand, hand_u, tuple(hand_n), tuple(foot_dir))


def _base(pelvis_roll=0.06, chest_roll=-0.04, shift=-0.06):
    """Standing pose with the weight on the figure's right leg (viewer's left)."""
    p = A.standing_pose()
    p.pelvis, p.chest = (0.0, 0.0, pelvis_roll), (0.0, 0.0, chest_roll)
    p.pelvis_pos = (A.PELVIS_ORIGIN[0] + shift, A.PELVIS_ORIGIN[1], 0.0)
    p.chest_pos = (A.CHEST_ORIGIN[0] + shift * 0.3, A.CHEST_ORIGIN[1], 0.0)
    # heels: the foot pitches down while the toes lie level ('point' bends them at the ball)
    p.legs[-1] = _limb((shift - 0.12, 7.95, 0.0), (0, 0, 1), 'point', foot_dir=(-0.35, 0.45, 1.0))
    p.legs[1] = _limb((0.34, 7.85, 0.18), (-0.15, 0.0, 1.0), 'point', foot_dir=(0.30, 0.50, 1.0))
    return p


def pose_relaxed():
    return _base()


def pose_hand_on_hip():
    p = _base(0.08, -0.05, -0.08)
    p.arms[1] = _limb((0.80, 2.80, -0.05), (1.0, -0.1, -0.6), 'hip', hand_u=(-0.15, 0.60, 0.80), hand_n=(0.95, 0.0, 0.3))
    return p


def pose_hair_touch():
    p = _base(0.07, -0.06, -0.06)
    p.arms[-1] = _limb((-0.70, 0.18, -0.05), (-1.0, -0.3, -0.3), 'hair', hand_u=(0.10, -1.0, -0.35),
                       hand_n=(-0.9, 0.0, 0.4))
    return p


def pose_chin_rest():
    p = _base(0.05, -0.03, -0.04)
    p.arms[-1] = _limb((0.18, 2.66, 0.66), (-0.2, 1.0, 1.0), 'relaxed', hand_u=(1.0, -0.15, -0.1),
                       hand_n=(0.0, -0.3, 1.0))
    p.arms[1] = _limb((0.10, 1.30, 0.62), (0.5, 1.0, 0.5), 'chin', hand_u=(-0.15, -1.0, 0.10), hand_n=(0.1, 0.1, 1.0))
    return p


def pose_arms_crossed():
    """Forearms folded across the waist: the right hand grips the left upper arm, the left hand tucks under."""
    p = _base(0.05, -0.03, -0.05)
    p.arms[-1] = _limb((0.52, 2.20, 0.66), (-1.0, 0.7, 0.6), 'clasp', hand_u=(1.0, 0.25, -0.35), hand_n=(0.0, -0.35, 1.0))
    p.arms[1] = _limb((-0.42, 2.42, 0.50), (1.0, 0.7, 0.5), 'clasp', hand_u=(-1.0, 0.1, -0.45), hand_n=(0.0, 0.25, 1.0))
    return p


def pose_hands_in_pockets():
    """Both hands in the front pockets: the wrists end inside the cloth, the elbows out and back."""
    p = _base(0.06, -0.04, -0.05)
    for s in (-1, 1):
        x, y, z = POCKET_WRIST
        p.arms[s] = _limb((s * x, y, z), (s * 1.0, 0.0, -0.6), 'pocket', hand_u=(s * 0.15, 1.0, -0.2),
                          hand_n=(s * 1.0, 0.0, 0.2))
    return p


def pose_walking():
    """A step toward the viewer: the right foot planted ahead, the left heel lifting behind, arms in counter-swing."""
    p = _base(0.03, -0.02, -0.02)
    p.pelvis = (0.10, 0.0, 0.03)                      # the hips turn with the forward leg, the chest against it
    p.chest = (-0.10, 0.0, -0.02)
    p.pelvis_pos = (p.pelvis_pos[0], p.pelvis_pos[1] + WALK_DROP, 0.0)
    p.chest_pos = (p.chest_pos[0], p.chest_pos[1] + WALK_DROP, 0.0)
    p.legs[-1] = _limb((-0.22, 7.92, 0.50), (0.0, 0.0, 1.0), 'point', foot_dir=(-0.15, 0.30, 1.0))
    p.legs[1] = _limb((0.30, 7.62, -0.52), (0.1, 0.0, 1.0), 'point', foot_dir=(0.10, 0.85, 0.55))
    p.arms[-1] = _limb((-1.00, 3.92, -0.40), (-0.3, 0.0, -1.0), 'relaxed', hand_n=(-1.0, 0.0, 0.25))
    p.arms[1] = _limb((0.92, 3.86, 0.52), (0.3, 0.0, -1.0), 'relaxed', hand_n=(1.0, 0.0, 0.35))
    p.keep_steps = True                                # flat shoes keep the lifted back heel
    return p


def pose_look_back():
    """Turned away, looking back over the shoulder (default view: POSE_VIEWS)."""
    p = _base(0.07, -0.05, -0.07)
    p.arms[1] = _limb((0.80, 2.80, -0.05), (1.0, -0.1, -0.6), 'hip', hand_u=(-0.15, 0.60, 0.80), hand_n=(0.95, 0.0, 0.3))
    return p


def pose_lean_wall():
    """Leaning a shoulder on a pillar at the left of the picture, ankles crossed (rig_figure draws the pillar)."""
    p = _base(0.03, -0.06, 0.02)
    p.legs[-1] = _limb((-0.05, 8.10, 0.0), (0.0, 0.0, 1.0), 'point', foot_dir=(-0.30, 0.0, 1.0))
    p.legs[1] = _limb((-0.22, 8.08, 0.30), (-0.2, 0.0, 1.0), 'point', foot_dir=(0.10, 0.0, 1.0))
    p.arms[1] = _limb((0.62, 3.25, 0.22), (1.0, 0.0, -0.6), 'pocket', hand_u=(0.15, 1.0, -0.2), hand_n=(1.0, 0.0, 0.2))
    p.lean = LEAN_ROLL
    p.prop = 'wall'
    return p


def pose_seated():
    """Sitting upright on a chair, thighs level, feet on the floor, hands resting on the thighs.

    The torso keeps its standing frame (the head anchors the picture); the legs fold under it and the
    floor rises to SEAT_FLOOR. Default view: three-quarter (POSE_VIEWS), so the thighs read.
    """
    p = _base(0.0, -0.02, 0.0)
    for s in (-1, 1):
        x, y, z = SEAT_ANKLE
        p.legs[s] = _limb((s * x, y, z), (0.0, -1.0, 0.6), 'point', foot_dir=(s * 0.2, 0.45, 1.0))
        p.arms[s] = _limb((s * 0.50, 3.22, 1.25), (s * 0.6, 0.0, -1.0), 'relaxed', hand_u=(-s * 0.15, 0.20, 1.0),
                          hand_n=(s * 0.25, -1.0, 0.1))
    p.flat_ankle = SEAT_ANKLE[1] + SEAT_HEEL
    p.prop = 'chair'
    return p


POSES = {'relaxed': pose_relaxed, 'hand_on_hip': pose_hand_on_hip, 'hair_touch': pose_hair_touch,
         'chin_rest': pose_chin_rest, 'arms_crossed': pose_arms_crossed, 'hands_in_pockets': pose_hands_in_pockets,
         'walking': pose_walking, 'look_back': pose_look_back, 'lean_wall': pose_lean_wall, 'seated': pose_seated}
SEATED = ('seated',)
SEAT_ANKLE = (0.42, 5.95, 2.30)            # seated: ankles below the knees (heels lifted for pumps)
SEAT_HEEL = 0.15                           # flat shoes bring the seated ankle down this much
SEAT_TOP_Y = 4.12                          # seat height: under the thighs and buttocks
CHAIR = dict(width=1.9, front=1.55, back=-0.85, thick=0.14, leg=0.12, inset=0.08, rest_top=1.75, rest_low=2.55,
             post=0.11)                    # chair in body coordinates (head widths)
POCKET_WRIST = (0.52, 3.22, 0.22)        # a hand in a front pocket: the wrist just inside the cloth
WALK_DROP = 0.08                          # the pelvis drops a little in a stride (legs reach both feet)
LEAN_ROLL = -0.09                         # radians the figure tilts toward the pillar (about the head)
# default view of a preset when the spec leaves pose.turn at 0 and pose.look at 'auto': (turn, look, head yaw)
POSE_VIEWS = {'look_back': (2.55, 'face', 0.30), 'walking': (0.9, 'auto', None), 'seated': (0.6, 'auto', None)}
NO_POCKETS = ('bikini', 'innerwear')       # outfits with nothing to hide a hand in
KANGAROO_WRIST = (0.30, 3.04, 0.40)       # hoodie: the hands meet inside the front pocket
PILLAR_WIDTH, PILLAR_GAP = 1.6, 0.02      # head widths: the pillar's face and its gap to the shoulder
PILLAR_Z = -45.0                          # above a painted backdrop, below the figure's ground shadow layer and figure
PILLAR_SHADE = 0.86                       # the pillar: the backdrop's dark end, a little darker (multiplier)
POCKET_HANDS = ('pocket',)                # gestures whose hand stays under the clothes
# Male build: the same poses with wrist targets moved to the male body (narrower head, wider waist).
MALE_TARGETS = {('hand_on_hip', 1): (0.86, 2.82, -0.05), ('hair_touch', -1): (-0.64, 0.14, -0.08)}


def pose_for(name, sex):
    pose = POSES[name]()
    if sex == 'male':
        for (pname, s), target in MALE_TARGETS.items():
            if pname == name:
                pose.arms[s] = replace(pose.arms[s], target=target)
    return pose


# Named body turns (radians about the vertical axis; positive turns the chest toward the right of
# the picture). Any number is accepted too; a negative number turns the other way.
TURNS = {'front': 0.0, 'three_quarter': 0.6, 'side': np.pi / 2, 'three_quarter_back': 2.3, 'back': np.pi}
SIDES = {'left': 1, 'right': -1}                 # the figure's own left and right
LIMB_KEYS = ('target', 'pole', 'hand', 'hand_u', 'hand_n', 'foot_dir')


LOOKS = ('auto', 'face', 'away')
BACK_TURN = 1.9          # radians: from here a turned figure shows the back of the head ('auto')
TURN_YAW = 0.55          # head yaw per radian of body turn: the face follows the body ('auto')
MAX_HEAD_YAW = 0.35      # the face rig's limit


def head_view(spec):
    """(look, head yaw, body turn) of a clothed figure.

    look 'auto': the face turns with the body; a figure turned past BACK_TURN shows the back of
    the head. 'face': the face is drawn with the spec's head.yaw (a glance over the shoulder).
    'away': the back of the head.
    """
    ch = spec['character']
    yaw = ch['head']['yaw']
    if spec['subject'] != 'portrait':
        return 'face', yaw, 0.0
    turn = turn_angle(ch['pose'].get('turn', 0.0))
    look = ch['pose'].get('look', 'auto')
    if look not in LOOKS:
        raise ValueError(f"unknown pose look '{look}' (use {', '.join(LOOKS)})")
    preset = POSE_VIEWS.get(ch['pose'].get('preset'))
    if preset and abs(turn) < 1e-9 and look == 'auto':      # a preset that implies its own view (look_back)
        turn, look, preset_yaw = preset
        yaw = yaw if preset_yaw is None else preset_yaw
    if look == 'away' or (look == 'auto' and abs(turn) >= BACK_TURN):
        return 'away', 0.0, turn
    if look == 'face' or abs(turn) < 1e-9:
        return 'face', yaw, turn
    return 'face', float(np.sign(turn) * min(MAX_HEAD_YAW, abs(turn) * TURN_YAW)), turn


def turn_angle(value):
    """Spec turn (name or radians) -> radians."""
    if isinstance(value, str):
        sign = -1.0 if value.startswith('-') else 1.0
        name = value.lstrip('-')
        if name not in TURNS:
            raise ValueError(f"unknown pose turn '{value}' (use {', '.join(TURNS)}, a '-' prefix, or radians)")
        return sign * TURNS[name]
    return float(value or 0.0)


def apply_custom(pose, custom):
    """Joint-level overrides from the spec on top of a preset.

    custom: {"arm_left"|"arm_right"|"leg_left"|"leg_right": {target, pole, hand, hand_u, hand_n, foot_dir},
             "chest"|"pelvis": [yaw, pitch, roll], "shift": x offset of the hips (weight shift)}
    Coordinates are body coordinates of the front-facing figure (head widths, y down, z toward the viewer).
    """
    if not custom:
        return pose
    for key, value in custom.items():
        part, _, side = key.partition('_')
        if part in ('arm', 'leg') and side in SIDES:
            s, limbs = SIDES[side], (pose.arms if part == 'arm' else pose.legs)
            bad = set(value) - set(LIMB_KEYS)
            if bad:
                raise ValueError(f"unknown keys {sorted(bad)} in pose.custom.{key} (use {', '.join(LIMB_KEYS)})")
            limbs[s] = replace(limbs[s], **{k: (tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in value.items()})
        elif key in ('chest', 'pelvis'):
            setattr(pose, key, tuple(float(v) for v in value))
        elif key == 'shift':
            dx = float(value) - (pose.pelvis_pos[0] - A.PELVIS_ORIGIN[0])
            pose.pelvis_pos = (pose.pelvis_pos[0] + dx, pose.pelvis_pos[1], pose.pelvis_pos[2])
            pose.chest_pos = (pose.chest_pos[0] + dx * 0.3, pose.chest_pos[1], pose.chest_pos[2])
        else:
            raise ValueError(f"unknown pose.custom key '{key}' (use arm_left, arm_right, leg_left, leg_right, "
                             f"chest, pelvis, shift)")
    return pose


def leaned(pose, angle):
    """The pose tilted in the picture plane about the head (a lean on a wall); the feet stay level on the floor."""
    if abs(angle) < 1e-9:
        return pose
    R = A.rot(0.0, 0.0, angle)

    def r(v):
        return None if v is None else tuple(R @ np.asarray(v, float))
    pose.chest = (pose.chest[0], pose.chest[1], pose.chest[2] + angle)
    pose.pelvis = (pose.pelvis[0], pose.pelvis[1], pose.pelvis[2] + angle)
    pose.chest_pos, pose.pelvis_pos = r(pose.chest_pos), r(pose.pelvis_pos)
    for s, lb in pose.arms.items():
        pose.arms[s] = replace(lb, target=r(lb.target), pole=r(lb.pole), hand_u=r(lb.hand_u), hand_n=r(lb.hand_n))
    for s, lb in pose.legs.items():
        x, _, z = r(lb.target)
        pose.legs[s] = replace(lb, target=(x, lb.target[1], z), pole=r(lb.pole))
    return pose


def pocket_hands(pose, kind):
    """Hands meant for pockets: into the hoodie's front pocket, or let down where nothing can hide them."""
    relaxed = A.standing_pose().arms
    for s, lb in pose.arms.items():
        if lb.hand != 'pocket':
            continue
        if kind in NO_POCKETS:
            pose.arms[s] = relaxed[s]
        elif kind == 'hoodie_joggers':
            x, y, z = KANGAROO_WRIST
            pose.arms[s] = replace(lb, target=(s * x, y, z), pole=(s * 1.0, 0.2, -0.4), hand_u=(-s * 1.0, 0.2, -0.2))
    return pose


def turned(pose, angle):
    """The whole pose turned about the vertical axis through the head.

    Why the pose and not the view: the garments are fitted to the posed body frames, so turning
    the frames, joints and limb directions turns body and clothes together. The 2D head stays
    where it is (the axis runs through its centre) and turns on its own (head.yaw).
    """
    if abs(angle) < 1e-9:
        return pose
    R = A.rot(angle)

    def r(v):
        return None if v is None else tuple(R @ np.asarray(v, float))
    pose.chest = (pose.chest[0] + angle, pose.chest[1], pose.chest[2])
    pose.pelvis = (pose.pelvis[0] + angle, pose.pelvis[1], pose.pelvis[2])
    pose.chest_pos, pose.pelvis_pos, pose.head_pos = r(pose.chest_pos), r(pose.pelvis_pos), r(pose.head_pos)
    for limbs in (pose.arms, pose.legs):
        for s, lb in limbs.items():
            limbs[s] = replace(lb, target=r(lb.target), pole=r(lb.pole), hand_u=r(lb.hand_u), hand_n=r(lb.hand_n),
                               foot_dir=r(lb.foot_dir))
    pose.turn = angle
    return pose
# z of the hand overlay when a gesture brings the hand in front of the face or hair
HAND_OVER = {'chin': 5.5, 'hair': 9.6}


def _rot2(vec, rad):
    c, s = np.cos(rad), np.sin(rad)
    return np.array([vec[0] * c - vec[1] * s, vec[0] * s + vec[1] * c])


class GarmentFrame:
    """2D torso frame for garments, following the pose's ribcage and pelvis tilt and weight shift."""

    def __init__(self, pose, joints):
        self.pose = pose
        self.ankle = {s: joints[f'ankle_{s}'][:2] for s in (-1, 1)}
        self.hip = {s: joints[f'hip_{s}'][:2] for s in (-1, 1)}
        self.shoulder = {s: joints[f'shoulder_{s}'][:2] for s in (-1, 1)}
        self.elbow = {s: joints[f'elbow_{s}'][:2] for s in (-1, 1)}
        self.wrist = {s: joints[f'wrist_{s}'][:2] for s in (-1, 1)}
        self.knee = {s: joints[f'knee_{s}'][:2] for s in (-1, 1)}

    def torso(self, u, v):
        t = np.clip((v - 1.3) / (3.0 - 1.3), 0, 1)
        roll = (1 - t) * self.pose.chest[2] + t * self.pose.pelvis[2]
        cx = (1 - t) * self.pose.chest_pos[0] + t * self.pose.pelvis_pos[0]
        return np.array([cx, v]) + _rot2(np.array([u, 0.0]), roll)

    def torso_pts(self, pts):
        return np.array([self.torso(u, v) for u, v in pts])


SHOE_THICK = 0.018          # leather thickness over the foot (head widths)
# Shoe sections in the foot frame of rig_anatomy (forward, down, toward the big toe, half-width,
# half-height), before the leather thickness: the toe box runs past the toes to a point.
SHOE_TOE_BOX = [(0.42, 0.235, 0.020, 0.185, 0.095), (0.64, 0.262, 0.025, 0.195, 0.065),
                (0.80, 0.280, 0.045, 0.170, 0.050), (0.95, 0.292, 0.070, 0.110, 0.034),
                (1.06, 0.302, 0.085, 0.030, 0.020)]
SHOE_WALL = [(-0.13, 0.27, 0.0, 0.10, 0.06), (0.0, 0.29, 0.0, 0.125, 0.04),     # low sides along the sole
             (0.25, 0.30, 0.01, 0.155, 0.03), (0.50, 0.30, 0.02, 0.185, 0.03)]
SHOE_HEEL_CUP = ((-0.12, 0.25, 0.0), (0.105, 0.085, 0.11))   # centre; half-width, half-height, half-length
SHOE_HEEL_TIP = (-0.08, 0.33, 0.0)          # where the stiletto leaves the sole


def shoe_pieces(s, joints):
    """Pointed pump fitted to the foot model: a toe box past the toes, low side walls and a heel
    cup (the instep stays bare), and a stiletto down to the floor under the ball of the foot."""
    p = joints[f'foot_frame_{s}']
    t = SHOE_THICK

    def sweep(rows):
        return M.ellipsoid_sweep([p(f, d, m) for f, d, m, _, _ in rows], [w + t for *_, w, _ in rows],
                                 [h + t for *_, h in rows], A.unit(np.cross(joints[f'sole_{s}'], joints[f'foot_{s}'])))
    o = p(0.0, 0.0, 0.0)
    medial, down, fwd = (p(*e) - o for e in ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)))
    (w, h, length) = SHOE_HEEL_CUP[1]
    cup = M.ellipsoid(p(*SHOE_HEEL_CUP[0]), [medial * (w + t), down * (h + t), fwd * (length + t)])
    solids = sweep(SHOE_TOE_BOX) + sweep(SHOE_WALL) + [cup]
    base = p(*SHOE_HEEL_TIP)
    ground = max(p(0.64, A.SOLE + t, 0.025)[1], p(0.92, A.SOLE + t, 0.06)[1])    # floor under the ball and toes
    tip = np.array([base[0], max(ground, base[1] + 0.05), base[2]])
    heel = [M.cone(base, tip, 0.045, 0.020)]
    return [M.Piece(f'shoe_{s}', solids, k=0.01),
            M.Piece(f'heel_{s}', heel, k=0.0, parent=f'shoe_{s}', attach_k=0.0, attach_n=0)]


SNEAKER_THICK = 0.03
# Sneaker upper and sole sections in the foot frame (forward, down, toward the big toe, half-width,
# half-height): a round toe a little past the toes, a low collar under the ankle bones.
SNEAKER_UPPER = [(-0.12, 0.21, 0.0, 0.11, 0.11), (0.02, 0.20, 0.0, 0.14, 0.12), (0.25, 0.205, 0.01, 0.165, 0.115),
                 (0.50, 0.245, 0.02, 0.19, 0.085), (0.72, 0.27, 0.03, 0.19, 0.062), (0.90, 0.285, 0.05, 0.155, 0.048),
                 (1.00, 0.29, 0.055, 0.095, 0.038)]
SNEAKER_SOLE = [(-0.21, 0.325, 0.0, 0.125, 0.05), (0.0, 0.335, 0.0, 0.155, 0.055), (0.50, 0.34, 0.02, 0.22, 0.055),
                (0.88, 0.335, 0.045, 0.19, 0.055), (1.05, 0.325, 0.055, 0.10, 0.05)]
DRESS_SOLE = [(r[0], r[1] - 0.01, r[2], r[3] - 0.005, r[4] * 0.45) for r in SNEAKER_SOLE]   # thin leather sole
LACE_STEPS = (0.10, 0.19, 0.28, 0.37)
LACE_HALF = 0.07             # half the lace row width across the instep
TOE_CAP = (0.74, 0.16, 0.10)   # toe cap seam: forward position at the sides, half-width, bulge toward the toe


def sneaker_pieces(s, joints, rows, thick, name):
    p = joints[f'foot_frame_{s}']
    lat = A.unit(np.cross(joints[f'sole_{s}'], joints[f'foot_{s}']))
    solids = M.ellipsoid_sweep([p(f, d, m) for f, d, m, _, _ in rows], [w + thick for *_, w, _ in rows],
                               [h + thick for *_, h in rows], lat)
    return [M.Piece(name, solids, k=0.01)]


def build_sneakers(fb, joints, pal, lw, dress=False):
    """Sneakers, or with dress=True lace-up dress shoes: the same last with a thin dark sole and dark laces."""
    out = []
    sole_rows = DRESS_SOLE if dress else SNEAKER_SOLE
    sole_color = darken(pal['shoe'], 0.5) if dress else pal['sole']
    lace_color = darken(pal['shoe'], 0.6) if dress else pal['sole']
    for s in (-1, 1):
        for name, rows, color, z in ((f'sole_{s}', sole_rows, sole_color, Z['shoe']),
                                     (f'sneaker_{s}', SNEAKER_UPPER, pal['shoe'], Z['shoe'] + 0.01)):
            res = fb.build(name, 'shoe', z, sneaker_pieces(s, joints, rows, SNEAKER_THICK, name), color=color,
                           line_color=line_color(color), self_shadow=False)
            if res is not None:
                out += res.drawables
        p = joints[f'foot_frame_{s}']
        tops = [(f, upper_top(f)) for f in LACE_STEPS]
        laces = [body_px(fb, np.array([p(f, d, LACE_HALF), p(f + 0.08, d + 0.012, -LACE_HALF)])) for f, d in tops]
        laces += [body_px(fb, np.array([p(f, d, -LACE_HALF), p(f + 0.08, d + 0.012, LACE_HALF)])) for f, d in tops]
        out.append(Drawable(f'laces_{s}', 'shoe', Z['shoe'] + 0.02, fill=None, clip=[f'sneaker_{s}'],
                            strokes=[geom.stroke_polygon(l, lw * 0.8) for l in laces], line_color=lace_color))
        ms = np.linspace(-TOE_CAP[1], TOE_CAP[1], 12)               # toe cap seam: an arc across the front of the toe
        cap = [p(TOE_CAP[0] + TOE_CAP[2] * (1 - (m / TOE_CAP[1]) ** 2), upper_top(TOE_CAP[0]) - 0.005, m + 0.04) for m in ms]
        out.append(Drawable(f'toecap_{s}', 'shoe', Z['shoe'] + 0.02, fill=None, clip=[f'sneaker_{s}'],
                            strokes=[geom.stroke_polygon(body_px(fb, np.array(cap)), lw * 0.6)],
                            line_color=line_color(pal['shoe'])))
    return out


def upper_top(f):
    """Foot-frame depth of the top of the sneaker upper at forward position f."""
    return np.interp(f, [r[0] for r in SNEAKER_UPPER], [r[1] - r[4] for r in SNEAKER_UPPER]) - SNEAKER_THICK


def body_px(fb, pts3):
    return fb.frame.map(np.asarray(pts3)[:, :2])


def build_shoes(fb, joints, color):
    out = []
    for s in (-1, 1):
        res = fb.build(f'shoe_{s}', 'shoe', Z['shoe'], shoe_pieces(s, joints), color=color,
                       line_color=line_color(color), self_shadow=False)
        if res is not None:
            out += res.drawables
    return out


def build_ground_shadow(body, sk, pal, on_scene=False):
    """Soft contact shadow so a full figure stands on something.
    on_scene: the ground is a painted scene, its color unknown here: the shadow darkens what is under it
    (the backdrop palette color is lighter than a night street or dark grass and would glow)."""
    c = (sk.ankle[-1] + sk.ankle[1]) / 2 + [0.0, 0.55]
    shape = body.map(geom.ellipse(c[0], c[1], 0.95, 0.16, 48))
    color, opacity = (SCENE_SHADOW, SCENE_SHADOW_OPACITY) if on_scene else (pal['background'][0] * 0.8, 0.45)
    group = 'scenery' if on_scene else 'bg'    # 'bg' is backdrop: watercolor leaves paper there (a white hole)
    return [Drawable('ground_shadow', group, -50, fill=[shape], color=color,
                     opacity=opacity, feather=body.px(0.08), casts=False, receives=False)]


SCENE_SHADOW, SCENE_SHADOW_OPACITY = np.array([0.06, 0.06, 0.09], np.float32), 0.38


def build_figure(head, body, spec, pal, lw, rng):
    """Mannequin body (under clothes), garments, then arms and hands lifted above the clothes."""
    ch = spec['character']
    name = ch['pose']['preset']
    if name not in POSES:
        raise ValueError(f"unknown pose '{name}' (use {', '.join(POSES)})")
    kind, sex = ch['outfit']['type'], ch['sex']
    if kind not in outfits.outfit_types(sex):
        raise ValueError(f"outfit type '{kind}' is not available for sex '{sex}' "
                         f"(use {', '.join(outfits.outfit_types(sex))})")
    shoes = outfits.shoes_for(kind, sex, ch['outfit'].get('shoes'))
    pose = apply_custom(pocket_hands(pose_for(name, sex), kind), ch['pose'].get('custom'))
    if shoes != 'pumps':
        pose = flat_feet(pose)
    pose = turned(leaned(pose, pose.lean), head_view(spec)[2])
    pieces, joints = A.body_pieces(pose)
    if pose.prop == 'chair':                   # seated: the soft fill between the thighs would hang below the lap
        pieces = [without_crotch_fill(pc, joints['crotch']) for pc in pieces]
    sk = GarmentFrame(pose, joints)
    canvas = (spec['canvas']['height'], spec['canvas']['width'])
    fb = M.FormBuilder(body, canvas, spec['light']['direction'], lw)
    skin, sl = pal['skin'], line_color(pal['skin'])
    quiet = [(joints['crotch'][:2], A.MODESTY_RADIUS)]
    body_res = fb.build('body', 'body', Z['body'], pieces, color=skin, line_color=sl, quiet_zones=quiet)
    out = list(body_res.drawables)
    ctx = outfits.Ctx(fb, body, pieces, joints, pose, pal, lw, rng, res=body_res)
    clothes = outfits.build_outfit(kind, ctx, ch['outfit'], Z)
    hidden = [s for s in (-1, 1) if pose.arms[s].hand in POCKET_HANDS]     # hands in pockets stay under the cloth
    arms = [p.name for p in pieces if p.name.startswith(('arm_', 'hand_'))
            and not any(p.name.startswith(f'hand_{s}') for s in hidden)]
    # the arms are drawn above the clothes; on a turned figure the torso cloth in front of an arm hides it
    covers = ctx.cloth_covers if ctx.turned else []
    lifted = fb.build('arms', 'body', Z['arms'], pieces + covers, color=skin, line_color=sl, select=arms)
    if lifted is not None:
        out += lifted.drawables
    away = head_view(spec)[0] == 'away'
    for s in (-1, 1):
        top = ('arms', Z['arms'], lifted) if lifted is not None else ('body', Z['body'], body_res)
        z = None if away else HAND_OVER.get(pose.arms[s].hand)     # seen from behind the head hides the gesture
        if z is not None:
            hand = [f'hand_{s}_{h}' for h in HAND_PIECES]
            over = fb.build(f'hand_over_{s}', 'body', z, pieces, color=skin, line_color=sl, select=hand, self_shadow=False)
            if over is not None:
                out += over.drawables
                top = (f'hand_over_{s}', z, over)
        name, zt, res = top
        out += marks.nails(joints[f'nails_{s}'], lambda q: np.asarray(q, float), body, res, name, zt, skin, lw)
    if shoes == 'pumps':
        out += build_shoes(fb, joints, pal['shoe'])
    elif shoes in ('sneakers', 'oxfords'):
        out += build_sneakers(fb, joints, pal, lw, dress=shoes == 'oxfords')
    out += build_ground_shadow(body, sk, pal, spec['background']['type'] == 'scene')
    if pose.prop == 'wall':
        out += build_pillar(body, body_res, sk, pal, lw, canvas)
    elif pose.prop == 'chair':
        out += build_chair(body, pose, pal, lw, max(sk.ankle[-1][1], sk.ankle[1][1]) + A.SOLE)
    out += clothes
    return out, sk


def build_pillar(body, res, sk, pal, lw, canvas):
    """A square pillar at the left whose side the figure's shoulder rests on (lean_wall)."""
    ys, xs = np.nonzero(res.sdf_px < 0)
    shoulder_y = body.map([sk.shoulder[-1]])[0][1]
    band = np.abs(ys + res.box[0] - shoulder_y) < body.px(0.3)
    right = (xs[band].min() + res.box[1]) if band.any() else body.map([sk.shoulder[-1]])[0][0]
    right -= body.px(PILLAR_GAP)
    floor = body.map([(0.0, max(sk.ankle[-1][1], sk.ankle[1][1]) + 0.35)])[0][1]
    left = right - body.px(PILLAR_WIDTH)
    face = np.array([[left, 0.0], [right, 0.0], [right, floor], [left, floor]])
    wall = darken(pal['background'][0], PILLAR_SHADE)
    edge = np.array([[right, 0.0], [right, floor]])
    return [Drawable('pillar', 'bg', PILLAR_Z, fill=[face], color=wall, casts=False, receives=True,
                     strokes=[geom.stroke_polygon(edge, lw * 1.2), geom.stroke_polygon(face[2:], lw)],
                     line_color=line_color(wall))]


def without_crotch_fill(piece, crotch):
    if piece.name != 'torso_soft':
        return piece
    keep = [sd for sd in piece.solids if not (sd.b is None and np.linalg.norm(sd.a - crotch) < 1e-6)]
    return replace(piece, solids=keep, attach_n=min(piece.attach_n, len(keep)))


def build_chair(body, pose, pal, lw, floor):
    """A plain wooden chair under a seated figure: seat, four legs, two back posts and a back rail.

    Built in the front-facing body frame and turned with the figure. The chair lies behind the body
    (it supports it from below and behind); seen from behind, the back rest comes in front of it.
    """
    import scene_props as P
    c = CHAIR
    R = A.rot(pose.turn)
    view = P.View(body, 0.0)
    w, f, b, t, lg, i = c['width'], c['front'], c['back'], c['thick'], c['leg'], c['inset']
    color = np.asarray(pal['chair'], np.float32)
    boxes = [('seat', (-w / 2, SEAT_TOP_Y, b), (w, 0, 0), (0, t, 0), (0, 0, f - b))]
    for k, (x, z) in enumerate(((-w / 2 + i, f - i - lg), (w / 2 - i - lg, f - i - lg), (-w / 2 + i, b + i),
                                (w / 2 - i - lg, b + i))):
        boxes.append((f'leg_{k}', (x, SEAT_TOP_Y + t, z), (lg, 0, 0), (0, floor - SEAT_TOP_Y - t, 0), (0, 0, lg)))
    for k, x in enumerate((-w / 2 + i, w / 2 - i - c['post'])):
        boxes.append((f'post_{k}', (x, c['rest_top'], b + i), (c['post'], 0, 0), (0, SEAT_TOP_Y - c['rest_top'], 0),
                      (0, 0, c['post'])))
    boxes.append(('rail', (-w / 2 + i, c['rest_top'], b + i - 0.02), (w - 2 * i, 0, 0),
                  (0, c['rest_low'] - c['rest_top'], 0), (0, 0, c['post'] * 0.8)))
    away = abs(pose.turn) > np.pi / 2
    faces = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [3, 2, 6, 7], [0, 3, 7, 4], [1, 2, 6, 5]]
    out = []
    for name, corner, ex, ey, ez in boxes:
        verts = P.box_verts(corner, ex, ey, ez) @ R.T
        z = CHAIR_FRONT_Z if away and name in ('rail', 'post_0', 'post_1') else CHAIR_Z
        out += P.solid(f'chair_{name}', 'wood', z, view, verts, faces, color, lw)
    return out


CHAIR_Z, CHAIR_FRONT_Z = -1.0, 2.7         # behind the body; the back rest seen from behind is in front of it
FLAT_ANKLE_Y = 8.10          # flat shoes or bare feet: the heels come down to the standing ankle height


def flat_feet(pose):
    """The same stance with the heels on the floor (flat shoes, sneakers, bare feet).
    A stride keeps its lifted back heel (pose.keep_steps): only the planted foot comes down."""
    legs = {}
    for s, limb in pose.legs.items():
        if getattr(pose, 'keep_steps', False) and limb.target[1] < FLAT_ANKLE_Y - 0.25:
            legs[s] = limb
            continue
        x, _, zz = limb.target
        fx, _, fz = limb.foot_dir
        ankle = pose.flat_ankle if pose.flat_ankle is not None else FLAT_ANKLE_Y
        legs[s] = replace(limb, target=(x, ankle, zz), hand='flat', foot_dir=(fx, 0.0, fz))
    pose.legs = legs
    return pose


def figure_guides(body, sk):
    lines = [body.map(np.array([sk.shoulder[-1], sk.shoulder[1]])), body.map(np.array([sk.hip[-1], sk.hip[1]]))]
    for s in (-1, 1):
        lines.append(body.map(np.array([sk.shoulder[s], sk.elbow[s], sk.wrist[s]])))
        lines.append(body.map(np.array([sk.hip[s], sk.knee[s], sk.ankle[s]])))
    lines.append(body.map(np.array([sk.torso(0, NECK_Y), sk.torso(0, HIP_Y)])))
    return lines
