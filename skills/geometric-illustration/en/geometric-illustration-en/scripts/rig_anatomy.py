"""Adult figure (female or male build) built from mannequin solids, posed by a 3D joint skeleton.

Why: a believable figure needs ribcage and pelvis that turn independently,
limbs whose muscles bulge on the correct side, and feet and hands that
foreshorten. A small joint skeleton (two frames for ribcage and pelvis,
two-bone IK for arms and legs) places sphere-swept solids; the mannequin
module turns them into silhouette, depth, contours and shading.

Units are head widths (W). The proportions are fixed to an adult woman of
about 7.5 heads. They are deliberately not exposed as spec parameters.
Lengths, breadths and limb girths come from the ANSUR II female survey
(slim subset, BMI 19-22), rescaled so the anime-sized head (about 1.2x a
real head) sits on a body of real proportions, then slimmed slightly for
the illustration style (see references/anatomy.md).
The male build (BUILDS['male'], selected with use_build) keeps the same
vertical landmarks (neck, waist, crotch, knee, ankle levels) and changes the
breadths, girths, chest form and head size, so garments cut in rest
coordinates fit both builds.
Body coordinates: x toward the figure's left side when she faces the viewer
(viewer's right), y down, z out of her chest. Side s = +1 is that +x side.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field

import numpy as np

import rig_hand
from mannequin import Piece, cone, ellipse_cone, ellipsoid, ellipsoid_sweep, sphere, tube

# skeleton (standing, body coordinates)
CHEST_ORIGIN = (0.0, 1.70, 0.0)
PELVIS_ORIGIN = (0.0, 3.40, 0.0)
SHOULDER_LOCAL = (0.78, -0.50, -0.04)       # chest frame: joint 0.17 below the acromion (y 1.03)
HIP_LOCAL = (0.40, 0.32, 0.0)               # pelvis frame: at the greater trochanter (y 3.75)
NECK_BASE_LOCAL = (0.0, -0.64, -0.06)       # suprasternal notch (y 1.07)
UPPER_ARM, FOREARM = 1.60, 1.32             # elbow at the navel, wrist at the crotch
THIGH, SHIN = 2.25, 2.15                    # knee 5.96, ankle 8.10
HEAD_TO_NECK = np.array([0.0, 0.42, -0.10])  # head center -> top of the neck
NECK_RADII = (0.24, 0.20)                    # neck cone radius at the base and at the top
HAND_SCALE = 1.0                            # hand length 1.0 W
CROTCH_LOCAL = (0.0, 0.55, 0.04)            # pelvis frame; centre of the line-free modesty zone
MODESTY_RADIUS = 0.70
SOFT_CONTOUR_EPS = 0.08
CHEST_PIECES = ('breasts', 'pecs')          # the chest form of either build
CHEST_FORM = 'breasts'
GLUTE = ((0.24, 0.18, -0.26), (0.23, 0.44, -0.22), 0.34, 0.30)   # pelvis frame: cone ends and radii
PEC = ((0.27, -0.06, 0.38), (0.30, 0.16, 0.035))   # chest frame centre; half-width, half-height, half-depth
BREAST = ((0.24, -0.02, 0.28), (0.27, 0.18, 0.38), 0.20, 0.25)   # chest frame: cone ends and radii
PEC_ATTACH_K = 0.10
GIRDLE_REACH = 0.68                         # chest frame x where clavicle and trapezius meet the shoulder
THIGH_ROOT_R = 0.38                         # ball at the hip joint that roots the thigh in the hip curve
ARM_ATTACH_K = 0.14                         # blend of the arm into the shoulder girdle
GIRDLE_TOP = -0.52                          # chest frame y of the trapezius end: level with the deltoid top, no notch
HEAD_DRAW = 1.0                             # head size relative to the body unit (the male head is drawn smaller)


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-9)


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    """Rotation matrix: yaw about y, then pitch about x, then roll about z (applied roll first)."""
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return ry @ rx @ rz


@dataclass
class Frame3:
    origin: np.ndarray
    R: np.ndarray

    def p(self, local):
        return self.origin + self.R @ np.asarray(local, float)

    def d(self, local):
        return self.R @ np.asarray(local, float)


def two_bone_ik(root, target, l1, l2, pole):
    """Middle joint of a two-bone chain reaching toward target, bending toward the pole direction."""
    root, target = np.asarray(root, float), np.asarray(target, float)
    v = target - root
    dist = np.clip(np.linalg.norm(v), abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
    d = unit(v)
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = np.sqrt(max(l1 * l1 - a * a, 0.0))
    p = np.asarray(pole, float)
    p = unit(p - np.dot(p, d) * d)
    mid = root + d * a + p * h
    end = root + d * dist
    return mid, end


@dataclass
class Limb:
    target: tuple                   # wrist or ankle position (body coordinates)
    pole: tuple                     # elbow / knee bend direction
    hand: str = 'relaxed'           # hand gesture, or foot mode for legs ('flat' | 'point')
    hand_u: tuple = None            # direction from wrist to fingers (None = continue the forearm)
    hand_n: tuple = (0.0, 0.0, 1.0)  # back-of-hand direction
    foot_dir: tuple = (0.0, 0.0, 1.0)          # level: the sole of the foot model is flat


@dataclass
class BodyPose:
    chest: tuple = (0.0, 0.0, 0.0)          # yaw, pitch, roll of the ribcage
    pelvis: tuple = (0.0, 0.0, 0.0)         # yaw, pitch, roll of the pelvis
    chest_pos: tuple = CHEST_ORIGIN
    pelvis_pos: tuple = PELVIS_ORIGIN
    head_pos: tuple = (0.0, 0.0, 0.0)
    arms: dict = field(default_factory=dict)  # side -> Limb
    legs: dict = field(default_factory=dict)
    root_roll: float = 0.0                  # tilt the whole figure in the picture plane (reclining)
    view_yaw: float = 0.0                   # turn the figure away from the viewer
    view_pitch: float = 0.0
    turn: float = 0.0                       # clothed figure: the whole pose turned about the vertical axis (rig_figure.turned)
    lean: float = 0.0                       # clothed figure: tilt in the picture plane about the head (rig_figure.leaned)
    prop: str = None                        # clothed figure: a prop the pose needs ('wall', 'chair')
    keep_steps: bool = False                # flat shoes keep a lifted heel (a stride)
    flat_ankle: float = None                # ankle height of a flat foot when the floor is not the standing one (seated)
    face_yaw: float = 0.2                   # face turn as seen by the viewer (face rig)
    face_roll: float = 0.0
    hair: str = 'long'                      # long | updo
    hide_chest: bool = False                # back views: keep the chest silhouette plain
    chest_lock: list = None                 # optional hair lock path falling over the chest


def standing_pose():
    """Neutral standing pose; other poses copy and edit it."""
    hang = 1.05 + SHOULDER_LOCAL[0] - BUILDS['female']['SHOULDER_LOCAL'][0]    # arms hang below the build's shoulders
    arms = {s: Limb(target=(s * hang, 4.05, 0.10), pole=(s * 0.3, 0.0, -1.0), hand='relaxed',
                    hand_n=(s * 1.0, 0.0, 0.25)) for s in (-1, 1)}
    legs = {s: Limb(target=(s * 0.28, 8.10, -0.02), pole=(0.0, 0.0, 1.0), foot_dir=(s * 0.35, 0.0, 1.0))
            for s in (-1, 1)}
    return BodyPose(arms=arms, legs=legs)


# ---------------------------------------------------------------- solids

# Torso loft: one row per level of the standing body (y), giving the front-view width, the
# side-view depth and the depth centre (z). Reading the rows top to bottom gives the two contour
# drawings an artist starts from: the front hourglass (narrow waist, full hips) and the side
# S-curve (round upper back, hollow of the lower back, full buttocks, soft lower belly).
#            y     width  depth  z centre
TORSO_LOFT = [(1.12, 0.92, 0.62, -0.08),    # base of the neck, between the trapezius
              (1.40, 1.20, 0.82, -0.06),    # armpits
              (1.75, 1.26, 0.90, -0.07),    # chest (breasts are added on top)
              (2.12, 1.16, 0.86, -0.05),    # under the bust: lower ribs
              (2.45, 1.04, 0.76, -0.01),
              (2.70, 1.00, 0.72, 0.02),     # waist, the narrowest level
              (2.98, 1.16, 0.78, 0.03),     # iliac crest and navel
              (3.30, 1.46, 0.84, 0.01),
              (3.62, 1.64, 0.88, -0.03),    # hips: the torso carries the whole hip curve
              (3.94, 1.52, 0.76, -0.02)]    # crotch level
CHEST_WEIGHT_Y = (2.25, 2.95)              # levels between these blend the ribcage and pelvis frames


def _torso_point(chest, pelvis, rest):
    """Rest-pose body point -> posed point; the waist follows both frames."""
    rest = np.asarray(rest, float)
    pc = chest.p(rest - np.asarray(CHEST_ORIGIN))
    pp = pelvis.p(rest - np.asarray(PELVIS_ORIGIN))
    t = np.clip((rest[1] - CHEST_WEIGHT_Y[0]) / (CHEST_WEIGHT_Y[1] - CHEST_WEIGHT_Y[0]), 0, 1)
    t = t * t * (3 - 2 * t)
    return pc * (1 - t) + pp * t


LOFT_SUBDIV = 10            # sections per table interval: rows join without corners, bends without notches


def loft_rows():
    """TORSO_LOFT refined by a C1 curve through its rows (the hourglass and S-curve stay smooth)."""
    rows = np.array(TORSO_LOFT)
    n = (len(rows) - 1) * LOFT_SUBDIV + 1
    return np.stack([smooth_samples(rows[:, k], n) for k in range(rows.shape[1])], axis=1)


def loft_surface(chest, pelvis, y, x_frac=0.0, back=False):
    """Posed point on the torso surface at rest level y, x_frac of the half-width off centre."""
    rows = loft_rows()
    w, dpt, zc = (np.interp(y, rows[:, 0], rows[:, k]) for k in (1, 2, 3))
    z = np.sqrt(max(1 - x_frac * x_frac, 0.0)) * dpt / 2
    return _torso_point(chest, pelvis, (x_frac * w / 2, y, zc - z if back else zc + z))


# Artist's indication marks: the few short lines and grooves an illustrator adds to suggest
# anatomy without modelling it (collarbones, spine, shoulder blades, sacral dimples, buttock
# folds). Points sit on the body surface in the frame named by each mark; a mark is drawn
# only on the side of the body that faces the viewer and only where nothing covers it.
NAVEL_LEVEL = 2.96
SPINE_LEVELS = (1.30, 1.60, 1.90, 2.20, 2.48, 2.72, 2.96, 3.18)
DIMPLE_LEVEL, DIMPLE_X = 3.22, 0.17                               # fraction of the half-width
PEC_MARK = [(0.12, 0.11, 0.43), (0.27, 0.13, 0.40), (0.42, 0.08, 0.33)]                 # chest frame, male build
CLAVICLE_MARK = [(0.08, -0.58, 0.28), (0.30, -0.60, 0.25), (0.52, -0.56, 0.17)]           # chest frame
SCAPULA_MARK = [(0.20, -0.34, -0.48), (0.23, -0.12, -0.49), (0.21, 0.06, -0.48)]          # chest frame
GLUTE_FOLD_MARK = [(0.07, 0.70, -0.40), (0.20, 0.78, -0.42), (0.33, 0.76, -0.42), (0.42, 0.66, -0.38)]  # pelvis
CLEFT_MARK = [(0.0, 0.06, -0.47), (0.0, 0.24, -0.50)]                                      # pelvis frame


def anatomy_marks(chest, pelvis):
    """[(name, kind, frame, facing, points)]; kind ink | groove | dot, facing +1 front / -1 back."""
    def back(y, x=0.0):
        return loft_surface(chest, pelvis, y, x, back=True)
    out = [('navel', 'dot', pelvis, 1, [loft_surface(chest, pelvis, NAVEL_LEVEL)]),
           ('spine', 'groove', chest, -1, [back(y) for y in SPINE_LEVELS]),
           ('cleft', 'ink', pelvis, -1, [pelvis.p(q) for q in CLEFT_MARK])]
    for s in (-1, 1):
        def mirror(frame, pts):
            return [frame.p((s * x, y, z)) for x, y, z in pts]
        if CHEST_FORM == 'pecs':                     # the lower edge of the pectoral: a short, nearly level line
            out.append((f'pec_{s}', 'ink', chest, 1, mirror(chest, PEC_MARK)))
        out += [(f'clavicle_{s}', 'ink', chest, 1, mirror(chest, CLAVICLE_MARK)),
                (f'scapula_{s}', 'groove', chest, -1, mirror(chest, SCAPULA_MARK)),
                (f'dimple_{s}', 'dot', pelvis, -1, [back(DIMPLE_LEVEL, s * DIMPLE_X)]),
                (f'glute_fold_{s}', 'ink', pelvis, -1, mirror(pelvis, GLUTE_FOLD_MARK))]
    return out


KNEE_MARK = [(0.075, 0.07), (0.0, 0.115), (-0.075, 0.07)]       # (toward the outside, down the shin) under the kneecap


def leg_marks(joints):
    """Ink arc under each kneecap (knee toward the viewer): [(name, kind, normal, points)].
    The toes are modelled, so their own contours separate them (no painted toe split)."""
    out = []
    for s in (-1, 1):
        k, f, side, shin = (joints[f'{n}_{s}'] for n in ('knee', 'knee_fwd', 'knee_side', 'shin'))
        cap = k + f * 0.17
        out.append((f'knee_{s}', 'ink', f, [cap + side * a + shin * b for a, b in KNEE_MARK]))
    return out


def torso_loft(chest, pelvis):
    """One chain of elliptical capsules through the loft rows; each row turns with its frame blend."""
    pts, lats, rows = [], [], []
    for y, w, dpt, zc in loft_rows():
        c = _torso_point(chest, pelvis, (0.0, y, zc))
        pts.append(c)
        lats.append(unit(_torso_point(chest, pelvis, (1.0, y, zc)) - c))
        rows.append((w / 2, dpt / 2))
    n = len(pts) - 1
    axes = [pts[i + 1] - pts[i] for i in range(n)]
    return [ellipse_cone(pts[i], pts[i + 1], rows[i][0], rows[i][1], rows[i + 1][0], rows[i + 1][1],
                         lats[i], lats[i + 1], axes[i - 1] if i > 0 else None, axes[i + 1] if i < n - 1 else None)
            for i in range(n)]


def torso_pieces(chest, pelvis, head_pos):
    """Lofted trunk with shoulder girdle and neck as one smooth core, plus breasts and glutes."""
    soft = []
    for s in (-1, 1):
        reach = GIRDLE_REACH                       # the girdle runs out to the shoulder joint of the build
        soft += [cone(chest.p((s * 0.06, -0.60, 0.26)), chest.p((s * reach, -0.54, 0.08)), 0.035, 0.035),  # clavicle
                 cone(chest.p((s * 0.10, -0.76, -0.12)), chest.p((s * reach, GIRDLE_TOP, -0.08)), 0.14, 0.11),  # trapezius
                 cone(chest.p((s * 0.22, -0.42, -0.36)), chest.p((s * 0.24, 0.02, -0.34)), 0.11, 0.08),     # scapula, inner edge
                 cone(chest.p((s * 0.24, -0.40, -0.35)), chest.p((s * (reach - 0.06), -0.48, -0.24)), 0.10, 0.10)]  # scapula spine
    soft.append(sphere(pelvis.p((0.0, -0.14, 0.15)), 0.30))                                             # lower belly
    soft.append(sphere(pelvis.p(CROTCH_LOCAL), 0.30))          # smooth, featureless fill between the thighs
    neck_top = np.asarray(head_pos, float) + HEAD_TO_NECK
    soft.append(cone(chest.p(NECK_BASE_LOCAL), neck_top, *NECK_RADII))
    # the loft joins its rows with a tight blend (no bulge at the rows); the girdle, neck and soft
    # parts melt into it with a wide blend and draw no contours of their own
    torso = Piece('torso', torso_loft(chest, pelvis), k=LIMB_K)    # segments abut: a wide blend would ripple
    girdle = Piece('torso_soft', soft, k=0.10, parent='torso', attach_k=0.10, attach_n=len(soft), contours=False)
    # soft forms ink only where they overhang (the lower curve), never where they rise out of the chest
    if CHEST_FORM == 'pecs':
        # flat, broad muscle plates on the ribcage; only their lower edge is inked
        chest_form = Piece('pecs', [ellipsoid(chest.p((s * PEC[0][0], PEC[0][1], PEC[0][2])),
                                              [chest.d((PEC[1][0], 0, 0)), chest.d((0, PEC[1][1], 0)),
                                               chest.d((0, 0, PEC[1][2]))]) for s in (-1, 1)],
                           k=0.04, parent='torso', attach_k=PEC_ATTACH_K, attach_n=2, contours=False)
    else:
        (ba, bb, bra, brb) = BREAST
        chest_form = Piece('breasts', [cone(chest.p((s * ba[0], ba[1], ba[2])), chest.p((s * bb[0], bb[1], bb[2])), bra, brb)
                                       for s in (-1, 1)], k=0.04, parent='torso', attach_k=0.12, attach_n=2,
                           contour_eps=SOFT_CONTOUR_EPS)
    # round masses (a buttock is a rounded form from every side) with a wide blend into the hip
    (ga, gb, ra, rb) = GLUTE
    glutes = Piece('glutes', [cone(pelvis.p((s * ga[0], ga[1], ga[2])), pelvis.p((s * gb[0], gb[1], gb[2])), ra, rb)
                              for s in (-1, 1)], k=0.03, parent='torso', attach_k=0.12, attach_n=2,
                   contour_eps=SOFT_CONTOUR_EPS)
    return [torso, girdle, chest_form, glutes]


def _lerp(a, b, t):
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


# Limb profiles. A limb is swept along its bone with a smooth radius profile, the way an
# illustrator draws a leg as two long curves: a straight shin in front, the calf swelling
# behind. Muscles are folded into the profile (radius) and into small offsets of the section
# centre toward the bulging side, so the outline stays one continuous curve. Separate muscle
# spheres would each add a bump to the outline and a crease to the shading.
# Each list holds values at evenly spaced points from the proximal to the distal joint.
THIGH_PROFILE = {'r': [0.40, 0.395, 0.375, 0.345, 0.31, 0.275, 0.245, 0.225, 0.215],
                 'fwd': [0.0, 0.01, 0.025, 0.03, 0.025, 0.015, 0.0, -0.005, 0.0],      # quadriceps curve in front
                 'side': [0.0, 0.0, 0.0, 0.0, 0.0, -0.005, -0.015, -0.02, 0.0]}       # inner swell above the knee
SHIN_PROFILE = {'r': [0.215, 0.225, 0.235, 0.228, 0.20, 0.165, 0.135, 0.115, 0.105],
                'fwd': [0.0, -0.02, -0.045, -0.05, -0.04, -0.025, -0.01, 0.0, 0.0],      # calf behind, shin straight
                'side': [0.0, 0.0, 0.0, -0.01, -0.01, -0.005, 0.0, 0.0, 0.0]}         # inner calf sits lower
UPPER_ARM_PROFILE = {'r': [0.185, 0.19, 0.18, 0.168, 0.16, 0.152, 0.145, 0.139, 0.136],
                     'fwd': [0.0, 0.0, 0.01, 0.025, 0.03, 0.025, 0.015, 0.005, 0.0],    # biceps
                     'side': [0.02, 0.035, 0.03, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0]}       # deltoid cap, outward
FOREARM_PROFILE = {'r': [0.136, 0.141, 0.147, 0.146, 0.135, 0.122, 0.11, 0.10, 0.095],     # gentle swell: no ring at the elbow
                   'fwd': [0.0, 0.005, 0.01, 0.01, 0.005, 0.0, 0.0, 0.0, 0.0],
                   'side': [0.0, 0.015, 0.02, 0.015, 0.008, 0.0, 0.0, 0.0, 0.0]}       # brachioradialis, thumb side
def _scaled(profile, k):
    return dict(profile, r=[r * k for r in profile['r']])


# Build tables. 'female' holds the values defined above. 'male' comes from the ANSUR II male summary
# (whole sample, slimmed by the female slim/full ratios; see references/anatomy.md) converted to the same
# stature-relative units: shoulders +4%, pelvis -8 to -11%, arm and neck girth +7%, no breasts.
# Illustration factors on top: broad shoulders, an almost straight waist, a smaller head.
_BUILD_KEYS = ('TORSO_LOFT', 'SHOULDER_LOCAL', 'HIP_LOCAL', 'NECK_RADII', 'HAND_SCALE', 'THIGH_PROFILE',
               'SHIN_PROFILE', 'UPPER_ARM_PROFILE', 'FOREARM_PROFILE', 'CHEST_FORM', 'GLUTE', 'HEAD_DRAW',
               'GIRDLE_REACH', 'GIRDLE_TOP', 'ARM_ATTACH_K', 'THIGH_ROOT_R', 'BREAST', 'PEC')
BUILDS = {'female': {k: globals()[k] for k in _BUILD_KEYS}}
BUILDS['male'] = dict(
    TORSO_LOFT=[(1.12, 1.02, 0.68, -0.08),     # base of the neck: heavier trapezius
                (1.40, 1.48, 0.96, -0.03),     # armpits: broad back, deep ribcage
                (1.75, 1.46, 1.04, -0.01),     # chest (pectorals are added on top)
                (2.12, 1.34, 0.98, 0.0),
                (2.45, 1.21, 0.82, -0.01),
                (2.70, 1.15, 0.79, 0.01),      # waist: a gentle taper, no hourglass
                (2.98, 1.20, 0.84, 0.03),      # navel
                (3.30, 1.29, 0.82, 0.01),
                (3.62, 1.38, 0.84, -0.03),     # hips: narrower than the shoulders, an almost straight side
                (3.94, 1.30, 0.74, -0.02)],
    SHOULDER_LOCAL=(0.96, -0.52, -0.04),
    HIP_LOCAL=(0.35, 0.32, 0.0),
    NECK_RADII=(0.31, 0.28),
    HAND_SCALE=1.05,
    THIGH_PROFILE=dict(THIGH_PROFILE, r=[0.31, 0.325, 0.33, 0.325, 0.305, 0.28, 0.25, 0.23, 0.22]),   # no hip bump
    SHIN_PROFILE=_scaled(SHIN_PROFILE, 1.04),
    UPPER_ARM_PROFILE=dict(UPPER_ARM_PROFILE, r=[0.19, 0.20, 0.195, 0.185, 0.175, 0.165, 0.157, 0.150, 0.146]),
    FOREARM_PROFILE=_scaled(FOREARM_PROFILE, 1.08),
    CHEST_FORM='pecs',
    GLUTE=((0.22, 0.18, -0.22), (0.21, 0.42, -0.19), 0.29, 0.26),
    HEAD_DRAW=0.93,
    GIRDLE_REACH=0.86,
    GIRDLE_TOP=-0.57,
    THIGH_ROOT_R=0.30,                         # narrow male hips: the root must stay inside the hip line
    ARM_ATTACH_K=0.22,                         # the deltoid melts into the trapezius: one shoulder arc
    BREAST=BREAST,
    PEC=PEC,
)


# Body types. Each is the sex's base build changed by a few factors (the vertical landmarks stay, so
# every pose and garment cut line still fits): torso width and depth per loft row (neck, armpits,
# chest, under the bust, ribs, waist, navel, belly, hips, crotch), the shoulder joint and girdle,
# limb girth, neck, the chest form and the buttocks. The values keep each type within the range of
# real adult bodies; the proportion check measures them against targets derived from the same factors.
VARIANTS = {
    'female_slender': dict(width=[0.94, 0.93, 0.91, 0.90, 0.89, 0.89, 0.89, 0.90, 0.91, 0.92],
                           depth=[0.93, 0.92, 0.90, 0.89, 0.89, 0.89, 0.89, 0.90, 0.91, 0.92],
                           shoulder=0.94, hip=0.93, thigh=0.87, thigh_root=0.88, shin=0.89, upper_arm=0.87, forearm=0.90,
                           neck=0.93, chest=0.80, glute=0.88),
    'female_glamour': dict(width=[1.0, 1.02, 1.04, 1.0, 0.97, 0.96, 0.99, 1.05, 1.09, 1.08],
                           depth=[1.0, 1.04, 1.06, 1.0, 0.97, 0.96, 0.99, 1.04, 1.08, 1.06],
                           shoulder=1.0, hip=1.07, thigh=1.10, shin=1.05, upper_arm=1.05, forearm=1.03, neck=1.0,
                           chest=1.30, chest_drop=0.04, glute=1.15),
    'female_athletic': dict(width=[1.04, 1.07, 1.04, 1.04, 1.05, 1.06, 1.05, 1.04, 1.04, 1.05],
                            depth=[1.03, 1.04, 1.0, 1.02, 1.03, 1.04, 1.03, 1.02, 1.01, 1.0],
                            shoulder=1.07, hip=1.0, thigh=1.05, thigh_root=1.0, shin=1.10, upper_arm=1.14, forearm=1.08,
                            neck=1.05, chest=0.90, glute=1.05),
    'male_slim': dict(width=[0.93, 0.92, 0.92, 0.92, 0.92, 0.92, 0.92, 0.93, 0.94, 0.94],
                      depth=[0.93, 0.92, 0.91, 0.91, 0.92, 0.92, 0.92, 0.93, 0.94, 0.94],
                      shoulder=0.93, hip=0.96, thigh=0.87, shin=0.89, upper_arm=0.86, forearm=0.89, neck=0.90,
                      chest=0.80, glute=0.90),
    'male_athletic': dict(width=[1.05, 1.12, 1.12, 1.06, 1.00, 0.98, 0.99, 1.0, 1.01, 1.02],
                          depth=[1.05, 1.10, 1.12, 1.06, 1.0, 0.98, 0.99, 1.0, 1.01, 1.02],
                          shoulder=1.09, hip=1.0, thigh=1.10, thigh_root=1.04, shin=1.08, upper_arm=1.18, forearm=1.12,
                          neck=1.10, chest=1.35, glute=1.05),
}
BUILD_TYPES = {'female': ('standard', 'slender', 'glamour', 'athletic'), 'male': ('standard', 'slim', 'athletic')}


def _variant(base, f):
    """A build from a base build and a VARIANTS factor table."""
    b = dict(base)
    b['TORSO_LOFT'] = [(y, w * kw, d * kd, z) for (y, w, d, z), kw, kd in zip(base['TORSO_LOFT'], f['width'], f['depth'])]
    x, y, z = base['SHOULDER_LOCAL']
    b['SHOULDER_LOCAL'] = (x * f['shoulder'], y, z)
    b['GIRDLE_REACH'] = base['GIRDLE_REACH'] * f['shoulder']
    b['GIRDLE_TOP'] = base['GIRDLE_TOP'] - f.get('girdle_lift', 0.0)
    hx, hy, hz = base['HIP_LOCAL']
    b['HIP_LOCAL'] = (hx * f['hip'], hy, hz)
    b['THIGH_ROOT_R'] = base['THIGH_ROOT_R'] * f.get('thigh_root', f['thigh'])   # the root must stay inside the hip line
    for key, k in (('THIGH_PROFILE', 'thigh'), ('SHIN_PROFILE', 'shin'), ('UPPER_ARM_PROFILE', 'upper_arm'),
                   ('FOREARM_PROFILE', 'forearm')):
        b[key] = _scaled(base[key], f[k])
    b['NECK_RADII'] = tuple(r * f['neck'] for r in base['NECK_RADII'])
    (ba, bb, ra, rb) = base['BREAST']
    drop = f.get('chest_drop', 0.0)
    b['BREAST'] = ((ba[0], ba[1] + drop, ba[2]), (bb[0], bb[1] + drop, bb[2] + (rb * (f['chest'] - 1))),
                   ra * f['chest'], rb * f['chest'])
    (pc, ph) = base['PEC']
    b['PEC'] = (pc, (ph[0] * min(f['chest'], 1.08), ph[1] * min(f['chest'], 1.1), ph[2] * f['chest'] ** 2))
    (ga, gb, gra, grb) = base['GLUTE']
    b['GLUTE'] = (ga, gb, gra * f['glute'], grb * f['glute'])
    return b


for _key, _factors in VARIANTS.items():
    BUILDS[_key] = _variant(BUILDS[_key.split('_')[0]], _factors)


def build_key(sex, build='standard'):
    """BUILDS key of a sex and body type ('standard' is the sex's base build)."""
    if build not in BUILD_TYPES.get(sex, ()):
        raise ValueError(f"unknown body type '{build}' for sex '{sex}' (use {', '.join(BUILD_TYPES.get(sex, ()))})")
    return sex if build == 'standard' else f'{sex}_{build}'


@contextmanager
def use_build(name):
    """Select a build for everything built inside the block (rig, garments, checks), then restore.

    Why module values: the loft, profiles and joint offsets are read by the rig, the garments and
    the proportion check alike; switching them in one place keeps every consumer consistent.
    """
    if name not in BUILDS:
        raise ValueError(f"unknown sex/build '{name}' (use {', '.join(BUILDS)})")
    g = globals()
    saved = {k: g[k] for k in _BUILD_KEYS}
    g.update(BUILDS[name])
    try:
        yield BUILDS[name]
    finally:
        g.update(saved)


LIMB_SEGMENTS = 40          # cones per bone: fewer leave a tooth at every joint in grazing self-shadow
LIMB_K = 0.004              # blend inside a sweep: consecutive cones share end spheres, so almost none is needed
JOINT_SMOOTH = 2.5          # samples: Gaussian smoothing of a limb's centres and radii (rounds elbows and knees)


def smooth_samples(values, n):
    """n samples of the C1 Catmull-Rom curve through evenly spaced control values."""
    v = np.asarray(values, float)
    m = len(v) - 1
    t = np.linspace(0, m, n)
    i = np.clip(np.floor(t).astype(int), 0, m - 1)
    f = t - i
    p0, p1, p2, p3 = v[np.clip(i - 1, 0, m)], v[i], v[i + 1], v[np.clip(i + 2, 0, m)]
    return 0.5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f ** 2
                  + (3 * p1 - p0 - 3 * p2 + p3) * f ** 3)


def _bone_samples(a, b, profile, fwd, side):
    """Section centres and radii along the bone a -> b (offsets move a centre toward its bulge)."""
    n = LIMB_SEGMENTS
    t = np.linspace(0, 1, n + 1)
    r, off_f, off_s = (smooth_samples(profile[k], n + 1) for k in ('r', 'fwd', 'side'))
    pts = np.array([_lerp(a, b, ti) + fwd * f + side * sd for ti, f, sd in zip(t, off_f, off_s)])
    return pts, r


def limb_sweep(bones):
    """One continuous sweep over consecutive bones [(a, b, profile, fwd, side), ...].

    Centres and radii are smoothed across the joints, so an elbow or knee bends as one rounded
    tube; separate sweeps would leave the joint sphere as a knob on the outer side of the bend.
    """
    pts, radii = [], []
    for k, bone in enumerate(bones):
        p, r = _bone_samples(*bone)
        pts.append(p if k == 0 else p[1:])
        radii.append(r if k == 0 else r[1:])
    pts, radii = np.vstack(pts), np.concatenate(radii)
    half = int(3 * JOINT_SMOOTH) + 1
    kern = np.exp(-0.5 * (np.arange(-half, half + 1) / JOINT_SMOOTH) ** 2)
    kern /= kern.sum()

    def smooth(v):
        return np.convolve(np.pad(v, half, mode='edge'), kern, mode='valid')
    pts = np.stack([smooth(pts[:, i]) for i in range(3)], axis=1)
    radii = smooth(radii)
    return [cone(pts[i], pts[i + 1], radii[i], radii[i + 1]) for i in range(len(pts) - 1)]


def _bone_axes(a, b, toward, s):
    """Unit forward (toward the bending pole) and outward vectors across the bone a -> b."""
    d = unit(np.asarray(b, float) - a)
    f = np.asarray(toward, float) - np.dot(toward, d) * d
    f = unit(f) if np.linalg.norm(f) > 1e-6 else unit(np.cross(d, (1.0, 0.0, 0.0)))
    return f, unit(np.cross(d, f)) * -s


def arm_pieces(s, chest, limb):
    """Upper arm, forearm and hand. Returns pieces and the joint positions."""
    shoulder = chest.p((s * SHOULDER_LOCAL[0], SHOULDER_LOCAL[1], SHOULDER_LOCAL[2]))
    elbow, wrist = two_bone_ik(shoulder, limb.target, UPPER_ARM, FOREARM, limb.pole)
    body_fwd = chest.d((0, 0, 1))
    fwd_u, _ = _bone_axes(shoulder, elbow, body_fwd, s)
    out_u = unit(chest.d((s, 0, 0)) - np.dot(chest.d((s, 0, 0)), unit(elbow - shoulder)) * unit(elbow - shoulder))
    fwd_f, _ = _bone_axes(elbow, wrist, body_fwd, s)
    lateral = unit(np.cross(unit(wrist - elbow), body_fwd)) * s
    solids = limb_sweep([(shoulder, elbow, UPPER_ARM_PROFILE, fwd_u, out_u), (elbow, wrist, FOREARM_PROFILE, fwd_f, lateral)])
    arm = Piece(f'arm_{s}', solids, k=LIMB_K, parent='torso', attach_k=ARM_ATTACH_K, attach_n=2,
                skip_contour_with=[f'hand_{s}_palm'])
    u_dir = limb.hand_u if limb.hand_u is not None else unit(wrist - elbow)
    hand, hs = rig_hand.hand_pieces(f'hand_{s}', wrist, u_dir, limb.hand_n, -s, limb.hand, f'arm_{s}',
                                    forearm_r=0.10, scale=HAND_SCALE)
    return [arm] + hand, dict(shoulder=shoulder, elbow=elbow, wrist=wrist, nails=hs.nails)


# Foot sections along the foot, from the ankle joint: (forward, down, toward the big toe,
# half-width, half-height). The sole stays flat while the top drops from the ankle over the
# instep to the toes; the toe end leans toward the big toe so the front reads as a slant.
FOOT_SECTIONS = [(-0.10, 0.19, 0.000, 0.100, 0.120),     # heel
                 (0.00, 0.17, 0.000, 0.125, 0.150),      # under the ankle
                 (0.22, 0.19, 0.010, 0.155, 0.130),      # instep (high, then a smooth drop)
                 (0.45, 0.235, 0.020, 0.185, 0.090),
                 (0.64, 0.265, 0.025, 0.195, 0.062),     # ball of the foot
                 (0.76, 0.274, 0.030, 0.170, 0.050)]     # toe roots: the toes are separate tubes
HEEL_BALL = ((-0.12, 0.21, 0.0), 0.10)                  # rounds the heel seen from behind
BIG_TOE = [((0.62, 0.265, 0.13), 0.056), ((0.80, 0.275, 0.125), 0.052), ((0.94, 0.283, 0.118), 0.044)]
# Small toes, second to fifth: (root, knuckle, tip) as ((forward, down, medial), radius). Their
# tips step back laterally, so the front of the foot reads as a slanted toe line; they lie on
# the floor (down + radius = the sole at 0.325).
SMALL_TOES = [[((0.72, 0.285, 0.045), 0.036), ((0.84, 0.290, 0.045), 0.034), ((0.925, 0.296, 0.043), 0.028)],
              [((0.71, 0.287, -0.025), 0.034), ((0.81, 0.292, -0.028), 0.032), ((0.885, 0.298, -0.030), 0.027)],
              [((0.69, 0.290, -0.088), 0.032), ((0.78, 0.295, -0.093), 0.030), ((0.845, 0.300, -0.097), 0.025)],
              [((0.66, 0.293, -0.140), 0.030), ((0.74, 0.297, -0.148), 0.027), ((0.795, 0.302, -0.153), 0.023)]]
ANKLE_BONES = [((0.0, -0.01, 0.075), 0.050), ((-0.02, 0.04, -0.070), 0.050)]   # inner higher, outer lower
FOOT_ATTACH_K = 0.10        # wide blend at the ankle front: no crease band between shin and foot
FOOT_K = 0.01               # blend inside the foot (small: a dense sweep inflates with a large k)
BALL = (0.64, 0.265)        # ball of the foot (forward, down): the toes bend here
SOLE = 0.325                # depth of the sole below the ankle in the foot frame (sections and toes rest on it)


def foot_frame(ankle, foot, sole, side, toe_dir=None):
    """Map (forward, down, toward the big toe) foot coordinates to world points.

    toe_dir: direction of the toes when they bend at the ball (standing on tiptoe the foot is
    steep while the toes lie on the floor); None keeps them in line with the foot.
    """
    medial = -side                                      # side points to the outside of the leg
    toe_sole = None if toe_dir is None else unit(sole - toe_dir * np.dot(sole, toe_dir))

    def p(f, d, m):
        if toe_dir is None or f <= BALL[0]:
            return ankle + foot * f + sole * d + medial * m
        ball = ankle + foot * BALL[0] + sole * BALL[1]
        return ball + toe_dir * (f - BALL[0]) + toe_sole * (d - BALL[1]) + medial * m
    return p


def foot_pieces(s, ankle, foot, sole, side, toe_dir=None):
    """Foot as one ellipsoid sweep (exact from any view, bends at the ball on tiptoe) with a
    heel ball, ankle bones and a separate big toe."""
    p = foot_frame(ankle, foot, sole, side, toe_dir)
    lat = unit(np.cross(sole, foot))
    solids = ellipsoid_sweep([p(f, d, m) for f, d, m, _, _ in FOOT_SECTIONS],
                             [w for *_, w, _ in FOOT_SECTIONS], [h for *_, h in FOOT_SECTIONS], lat)
    solids += [sphere(p(*HEEL_BALL[0]), HEEL_BALL[1])] + [sphere(p(*c), r) for c, r in ANKLE_BONES]
    toe = tube([p(*c) for c, _ in BIG_TOE], [r for _, r in BIG_TOE], 3, 0.8)
    small = [cone for t in SMALL_TOES for cone in tube([p(*c) for c, _ in t], [r for _, r in t], 3, 0.8)]
    return [Piece(f'leg_{s}_foot', solids, k=FOOT_K, parent=f'leg_{s}', attach_k=FOOT_ATTACH_K, attach_n=len(solids),
                  skip_contour_with=[f'leg_{s}']),
            Piece(f'leg_{s}_toes', small, k=0.004, parent=f'leg_{s}_foot', attach_k=0.02, attach_n=len(small),
                  contour_eps=0.03),
            Piece(f'leg_{s}_toe', toe, k=0.004, parent=f'leg_{s}_foot', attach_k=0.03, attach_n=len(toe),
                  contour_eps=0.03)], p


def leg_pieces(s, pelvis, limb):
    """Thigh and shin as one smooth sweep, the foot as a child that melts into the ankle."""
    hip = pelvis.p((s * HIP_LOCAL[0], HIP_LOCAL[1], HIP_LOCAL[2]))
    knee, ankle = two_bone_ik(hip, limb.target, THIGH, SHIN, limb.pole)
    shin_dir = unit(ankle - knee)
    fwd_knee, side = _bone_axes(knee, ankle, limb.pole, s)          # side points to the outside of the leg
    fwd_thigh, side_thigh = _bone_axes(hip, knee, limb.pole, s)
    foot = unit(limb.foot_dir)
    sole = shin_dir - foot * np.dot(shin_dir, foot)              # toward the ground, across the foot
    sole = unit(sole) if np.linalg.norm(sole) > 1e-3 else -fwd_knee
    side = unit(side - np.dot(side, foot) * foot - np.dot(side, sole) * sole) if np.linalg.norm(
        side - np.dot(side, foot) * foot) > 1e-3 else unit(np.cross(sole, foot)) * s
    leg = [sphere(hip, THIGH_ROOT_R)]                           # thigh root, inside the hip curve of the torso
    leg += limb_sweep([(hip, knee, THIGH_PROFILE, fwd_thigh, side_thigh), (knee, ankle, SHIN_PROFILE, fwd_knee, side)])
    toe_dir = None
    if limb.hand == 'point':                                     # on tiptoe: the toes lie level on the floor
        level = foot - np.array([0.0, 1.0, 0.0]) * foot[1]
        toe_dir = unit(level) if np.linalg.norm(level) > 0.2 else None
    feet, p = foot_pieces(s, ankle, foot, sole, side, toe_dir)
    joints = dict(hip=hip, knee=knee, ankle=ankle, toe=p(0.94, 0.29, 0.06), ball=p(0.64, 0.27, 0.025),
                  heel=p(-0.12, 0.21, 0.0), instep=p(0.22, 0.20, 0.01), sole=sole, foot=foot,
                  knee_fwd=fwd_knee, knee_side=side, shin=shin_dir, foot_frame=p)
    return [Piece(f'leg_{s}', leg, k=LIMB_K, parent='torso', attach_k=0.08, attach_n=2,
                  skip_contour_with=['torso', 'torso_soft', 'glutes', f'leg_{s}_foot'])] + feet, joints


def body_pieces(pose):
    chest = Frame3(np.asarray(pose.chest_pos, float), rot(*pose.chest))
    pelvis = Frame3(np.asarray(pose.pelvis_pos, float), rot(*pose.pelvis))
    pieces = torso_pieces(chest, pelvis, pose.head_pos)
    if pose.hide_chest:
        pieces = [pc for pc in pieces if pc.name not in CHEST_PIECES]
    joints = {'head': np.asarray(pose.head_pos, float), 'neck': chest.p(NECK_BASE_LOCAL),
              'crotch': pelvis.p(CROTCH_LOCAL)}
    for s in (-1, 1):
        arm, j = arm_pieces(s, chest, pose.arms[s])
        pieces += arm
        joints.update({f'{k}_{s}': v for k, v in j.items()})
        leg, j = leg_pieces(s, pelvis, pose.legs[s])
        pieces += leg
        joints.update({f'{k}_{s}': v for k, v in j.items()})
    return pieces, joints


# ---------------------------------------------------------------- view

def world_transform(pose):
    """Body coordinates -> view coordinates (root roll around the pelvis, then view turn)."""
    pivot = np.asarray(pose.pelvis_pos, float)
    R = rot(pose.view_yaw, pose.view_pitch, 0.0) @ rot(0.0, 0.0, pose.root_roll)

    def tf(p):
        return R @ (np.asarray(p, float) - pivot) + pivot
    return tf


def transform_pieces(pieces, tf):
    out = []
    for pc in pieces:
        solids = []
        for s in pc.solids:
            solids.append(s.mapped(tf))
        out.append(Piece(pc.name, solids, pc.k, pc.parent, pc.attach_k, pc.attach_n, pc.contours,
                         list(pc.skip_contour_with), pc.contour_eps))
    return out


def extent(pieces, extra_points=(), extra_r=0.0):
    lo, hi = np.full(2, np.inf), np.full(2, -np.inf)
    for pc in pieces:
        for s in pc.solids:
            for c, r in s.ends():
                lo, hi = np.minimum(lo, c[:2] - r), np.maximum(hi, c[:2] + r)
    for p in extra_points:
        lo, hi = np.minimum(lo, np.asarray(p)[:2] - extra_r), np.maximum(hi, np.asarray(p)[:2] + extra_r)
    return lo, hi
