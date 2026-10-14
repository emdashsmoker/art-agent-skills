"""Figure: a construction mannequin posed on a skeleton and rendered as a relief.

Units are head heights (HU). World axes: x toward the viewer's right, y up, z toward the viewer.
The figure faces +z at rest, so the figure's LEFT side is at +x.

Anatomy is fixed by tables (proportions, masses, five fingers, five toes); a scene only chooses
build, pose and view. That is what makes the result anatomically consistent by construction.
"""
import cv2
import numpy as np

from .relief import EMPTY, Relief, thicken
from .core import to_rgb, trace_color

CANON_HEADS = 8.0             # the tables below describe an 8-head figure

# ---------- skeleton (rest pose, absolute HU coordinates, left side) ----------
REST = {
    "pelvis": (0.00, 4.20, 0.00),
    "waist": (0.00, 4.95, 0.00),
    "chest": (0.00, 5.55, 0.00),
    "neck": (0.00, 6.62, -0.03),
    "head": (0.00, 7.08, 0.00),
    "l_clav": (0.10, 6.50, 0.02),
    "l_shoulder": (0.70, 6.38, -0.02),
    "l_elbow": (0.76, 5.06, -0.03),
    "l_wrist": (0.80, 3.94, 0.03),
    "l_hip": (0.36, 4.18, 0.00),
    "l_knee": (0.33, 2.12, 0.02),
    "l_ankle": (0.30, 0.36, -0.03),
}
PARENT = {
    "pelvis": None, "waist": "pelvis", "chest": "waist", "neck": "chest", "head": "neck",
    "l_clav": "chest", "l_shoulder": "l_clav", "l_elbow": "l_shoulder", "l_wrist": "l_elbow",
    "l_hip": "pelvis", "l_knee": "l_hip", "l_ankle": "l_knee",
}
ORDER = ["pelvis", "waist", "chest", "neck", "head", "clav", "shoulder", "elbow", "wrist", "hip", "knee", "ankle"]

# Pose values are (forward, twist, side) in degrees. These signs turn them into rotations so that
# positive always means: bend forward / turn to the viewer's right / move outward (limbs) or lean right (spine).
SPINE_SIGNS = (1, 1, -1)
LIMB_SIGNS = {"shoulder": (-1, 1, 1), "elbow": (-1, 1, 1), "wrist": (-1, 1, 1),
              "hip": (-1, 1, 1), "knee": (1, 1, 1), "ankle": (-1, 1, 1)}


def _rot_x(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _rot_y(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rot_z(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# ---------- body masses: (joint, (x, y, z), half-width, depth-front, depth-back) ----------
FEMALE = {
    # The spine is an S-curve: ribcage carried forward, hollow at the small of the back, pelvis tipped back.
    "torso": [
        # Depths follow measured adult proportions (waist about 0.7 HU front to back, hips about 0.9).
        ("pelvis", (0, 3.70, -0.02), 0.20, 0.20, 0.22),
        ("pelvis", (0, 3.90, -0.03), 0.52, 0.34, 0.42),
        ("pelvis", (0, 4.10, -0.04), 0.77, 0.40, 0.52),
        ("pelvis", (0, 4.35, -0.03), 0.75, 0.40, 0.48),
        ("pelvis", (0, 4.62, -0.01), 0.64, 0.38, 0.38),
        ("waist", (0, 4.98, 0.02), 0.475, 0.36, 0.34),
        ("chest", (0, 5.35, 0.03), 0.52, 0.37, 0.35),
        ("chest", (0, 5.72, 0.02), 0.585, 0.41, 0.39),
        ("chest", (0, 6.08, 0.00), 0.61, 0.39, 0.42),
        ("chest", (0, 6.33, -0.02), 0.62, 0.32, 0.38),
        ("chest", (0, 6.49, -0.04), 0.52, 0.24, 0.31),
        ("chest", (0, 6.60, -0.05), 0.40, 0.19, 0.26),
        ("chest", (0, 6.70, -0.07), 0.27, 0.14, 0.22),
    ],
    "neck": [
        ("chest", (0, 6.46, -0.08), 0.26, 0.24, 0.26),
        ("neck", (0, 6.80, -0.03), 0.21, 0.23, 0.24),
        ("head", (0, 7.14, 0.02), 0.20, 0.22, 0.23),
    ],
    "upper_arm": [
        ("l_shoulder", (0.70, 6.38, -0.02), 0.15, 0.17, 0.17),
        ("l_shoulder", (0.73, 6.16, -0.02), 0.18, 0.19, 0.19),
        ("l_shoulder", (0.745, 5.75, -0.02), 0.15, 0.16, 0.16),
        ("l_shoulder", (0.755, 5.35, -0.03), 0.128, 0.135, 0.135),
        ("l_elbow", (0.76, 5.06, -0.03), 0.122, 0.125, 0.125),
    ],
    "forearm": [
        ("l_elbow", (0.76, 5.06, -0.03), 0.122, 0.125, 0.125),
        ("l_elbow", (0.775, 4.80, -0.01), 0.14, 0.13, 0.13),
        ("l_elbow", (0.79, 4.40, 0.01), 0.11, 0.10, 0.10),
        ("l_wrist", (0.80, 3.98, 0.03), 0.085, 0.064, 0.064),
    ],
    # The thigh starts inside the pelvis mass so hip and leg read as one continuous form.
    "thigh": [
        ("l_hip", (0.40, 4.25, -0.03), 0.34, 0.30, 0.38),
        ("l_hip", (0.385, 3.85, -0.01), 0.385, 0.36, 0.40),
        ("l_hip", (0.365, 3.35, 0.00), 0.34, 0.36, 0.35),
        ("l_hip", (0.345, 2.75, 0.01), 0.26, 0.29, 0.27),
        ("l_hip", (0.33, 2.32, 0.02), 0.205, 0.235, 0.22),
        ("l_knee", (0.33, 2.14, 0.02), 0.19, 0.22, 0.21),
    ],
    "shin": [
        ("l_knee", (0.33, 2.12, 0.02), 0.185, 0.21, 0.21),
        ("l_knee", (0.335, 1.90, 0.00), 0.20, 0.19, 0.24),
        ("l_knee", (0.335, 1.62, -0.02), 0.23, 0.18, 0.29),
        ("l_knee", (0.32, 1.15, -0.02), 0.155, 0.15, 0.19),
        ("l_knee", (0.305, 0.70, -0.03), 0.115, 0.12, 0.135),
        ("l_ankle", (0.30, 0.40, -0.03), 0.112, 0.11, 0.12),
    ],
}
MALE = {
    # Broad chest and shoulders over narrow hips (the V of the torso), a deep ribcage, a short straight waist,
    # less sway at the small of the back than the female build. Same joints; measured adult proportions.
    "torso": [
        ("pelvis", (0, 3.72, -0.02), 0.24, 0.22, 0.24),
        ("pelvis", (0, 3.92, -0.03), 0.55, 0.36, 0.40),
        ("pelvis", (0, 4.15, -0.03), 0.66, 0.42, 0.46),
        ("pelvis", (0, 4.40, -0.02), 0.655, 0.42, 0.43),
        ("pelvis", (0, 4.65, 0.00), 0.63, 0.42, 0.38),
        ("waist", (0, 4.98, 0.02), 0.62, 0.40, 0.37),
        ("chest", (0, 5.35, 0.03), 0.68, 0.43, 0.42),
        ("chest", (0, 5.75, 0.03), 0.79, 0.50, 0.48),
        ("chest", (0, 6.10, 0.01), 0.85, 0.48, 0.50),
        ("chest", (0, 6.36, -0.02), 0.86, 0.39, 0.46),
        ("chest", (0, 6.52, -0.04), 0.70, 0.29, 0.38),
        ("chest", (0, 6.64, -0.06), 0.50, 0.22, 0.31),
        ("chest", (0, 6.74, -0.08), 0.33, 0.17, 0.26),
    ],
    "neck": [
        ("chest", (0, 6.50, -0.08), 0.33, 0.28, 0.31),
        ("neck", (0, 6.85, -0.05), 0.265, 0.23, 0.29),
        ("head", (0, 7.16, -0.01), 0.25, 0.19, 0.27),
    ],
    "upper_arm": [
        ("l_shoulder", (0.71, 6.32, -0.02), 0.19, 0.20, 0.21),
        ("l_shoulder", (0.735, 6.12, -0.02), 0.23, 0.235, 0.235),
        ("l_shoulder", (0.75, 5.75, -0.02), 0.20, 0.22, 0.205),
        ("l_shoulder", (0.755, 5.35, -0.03), 0.17, 0.18, 0.175),
        ("l_elbow", (0.76, 5.06, -0.03), 0.145, 0.14, 0.15),
    ],
    "forearm": [
        ("l_elbow", (0.76, 5.06, -0.03), 0.145, 0.14, 0.15),
        ("l_elbow", (0.775, 4.80, -0.01), 0.18, 0.16, 0.16),
        ("l_elbow", (0.79, 4.40, 0.01), 0.135, 0.12, 0.12),
        ("l_wrist", (0.80, 3.98, 0.03), 0.105, 0.078, 0.078),
    ],
    # Straighter outer thigh than the female build: the hip does not flare past the thigh.
    "thigh": [
        ("l_hip", (0.37, 4.25, -0.03), 0.32, 0.32, 0.38),
        ("l_hip", (0.36, 3.85, -0.01), 0.37, 0.38, 0.40),
        ("l_hip", (0.35, 3.35, 0.00), 0.345, 0.38, 0.36),
        ("l_hip", (0.34, 2.75, 0.01), 0.275, 0.31, 0.29),
        ("l_hip", (0.33, 2.32, 0.02), 0.215, 0.25, 0.23),
        ("l_knee", (0.33, 2.14, 0.02), 0.20, 0.23, 0.22),
    ],
    "shin": [
        ("l_knee", (0.33, 2.12, 0.02), 0.19, 0.22, 0.22),
        ("l_knee", (0.335, 1.90, 0.00), 0.21, 0.20, 0.25),
        ("l_knee", (0.335, 1.62, -0.02), 0.245, 0.19, 0.31),
        ("l_knee", (0.32, 1.15, -0.02), 0.165, 0.16, 0.20),
        ("l_knee", (0.305, 0.70, -0.03), 0.125, 0.13, 0.145),
        ("l_ankle", (0.30, 0.40, -0.03), 0.12, 0.12, 0.13),
    ],
}
DEFAULT_TONE = {"female": 0.55, "male": 0.75}

SEX = {
    "female": dict(masses=FEMALE, shoulder_x=0.66, hip_x=0.36, limb=1.0, neck=1.0),
    "male": dict(masses=MALE, shoulder_x=0.86, hip_x=0.33, limb=1.0, neck=1.0, hand=1.12, foot=1.08),
}

# Hand geometry in the hand frame: D along the fingers, T toward the thumb side, N out of the palm.
FINGERS = {   # name: (D, T of knuckle, total length, base radius, spread sign)
    "index": (0.42, 0.115, 0.33, 0.041, 1.0),
    "middle": (0.44, 0.038, 0.365, 0.042, 0.25),
    "ring": (0.42, -0.04, 0.335, 0.039, -0.45),
    "pinky": (0.375, -0.115, 0.26, 0.034, -1.0),
}
PHALANX = (0.46, 0.30, 0.24)
HAND_POSES = {
    #            curls (knuckle, middle joint) for index..pinky,   spread, thumb (splay, oppose, curl)
    "relaxed": dict(curl=[(12, 22), (16, 28), (22, 34), (28, 40)], spread=5, thumb=(32, 15, 15)),
    "open": dict(curl=[(0, 4), (0, 4), (0, 4), (0, 4)], spread=12, thumb=(48, 5, 5)),
    "fist": dict(curl=[(85, 100), (85, 100), (85, 100), (85, 100)], spread=0, thumb=(25, 60, 55)),
    "point": dict(curl=[(0, 5), (85, 100), (85, 100), (85, 100)], spread=0, thumb=(25, 60, 50)),
    "hold": dict(curl=[(40, 50), (45, 55), (50, 58), (55, 60)], spread=3, thumb=(38, 45, 30)),
    "grace": dict(curl=[(5, 12), (22, 34), (28, 40), (14, 26)], spread=8, thumb=(30, 20, 15)),
}
HEAD_PROFILE = [   # (y above the head joint, half-width, z front, z back): a natural adult head
    (-0.06, 0.07, 0.36, 0.24), (-0.01, 0.15, 0.40, 0.12), (0.07, 0.225, 0.425, 0.00),
    (0.17, 0.28, 0.435, -0.14), (0.30, 0.32, 0.44, -0.31), (0.42, 0.34, 0.44, -0.40),
    (0.57, 0.35, 0.44, -0.44), (0.72, 0.335, 0.40, -0.43), (0.84, 0.27, 0.30, -0.36),
    (0.89, 0.13, 0.13, -0.17),
]
TOES = [   # (x offset from foot axis, toward the body centre negative), length, radius, start setback
    (-0.115, 0.21, 0.058, 0.00), (-0.040, 0.19, 0.043, 0.00), (0.020, 0.165, 0.040, 0.02),
    (0.075, 0.14, 0.037, 0.05), (0.125, 0.11, 0.034, 0.09),
]

REACH_TARGETS = {   # name: (anchor joint, wrist target in rest coordinates; +x = the reaching arm's own side)
    "hip": ("pelvis", (0.78, 4.72, 0.12)), "waist_front": ("waist", (0.1, 4.95, 0.42)),
    "chest": ("chest", (0.0, 5.75, 0.50)), "heart": ("chest", (-0.2, 5.95, 0.52)), "opposite_shoulder": ("chest", (-0.5, 6.25, 0.38)),
    "collar": ("chest", (0.05, 6.35, 0.36)), "lap": ("pelvis", (0.12, 4.05, 0.45)), "pelvis_front": ("pelvis", (0.02, 4.02, 0.46)),
    "chin": ("head", (0.1, 6.98, 0.42)), "cheek": ("head", (0.34, 7.3, 0.3)), "hair": ("head", (0.4, 7.7, 0.12)),
    "behind_head": ("head", (0.25, 7.5, -0.5)), "pocket": ("pelvis", (0.62, 4.3, 0.2)),
    "forward": ("chest", (0.3, 5.9, 1.3)), "up": ("chest", (0.5, 8.3, 0.1)), "side": ("chest", (2.2, 6.2, 0.0)),
    "own_shoulder": ("chest", (0.62, 6.42, 0.32)), "fold": ("chest", (-0.46, 5.62, 0.68)),
    "fold_under": ("chest", (-0.52, 5.46, 0.62)),
}
# Where the elbow should end up for some targets (rest coordinates on the chest, x toward the reaching arm):
# crossed arms bring the elbows forward so the forearms lie level across the body.
ELBOW_HINTS = {"fold": (0.84, 5.30, 0.32), "fold_under": (0.86, 5.22, 0.30)}
# Hand shapes a pose implies when the caller does not choose: crossed arms grip the upper arms, fists rest on the hips.
POSE_HANDS = {"arms_crossed": {"l": "hold", "r": "hold"}, "heroic": {"l": "fist", "r": "fist"}}

POSES = {
    "stand": {},
    "relaxed": {
        "l_shoulder": (4, 0, 8), "r_shoulder": (4, 0, 8), "l_elbow": (12, 0, 0), "r_elbow": (12, 0, 0),
        "l_hip": (0, -6, 3), "r_hip": (0, -6, 3),
    },
    "contrapposto": {   # weight on the figure's right leg; hips and shoulders counter-tilt
        "pelvis": (0, 0, 7), "waist": (2, 0, -11), "chest": (0, 0, -2), "neck": (0, 0, 3), "head": (2, -8, 4),
        "r_hip": (-2, 0, -7), "r_knee": (0, 0, 0),
        "l_hip": (16, -12, 11), "l_knee": (30, 0, 0), "l_ankle": (-10, 0, 0),
        "l_shoulder": (6, 0, 9), "l_elbow": (18, 0, 0), "r_shoulder": (-4, 0, 12), "r_elbow": (10, 0, 0),
    },
    "hand_on_hip": {
        "pelvis": (0, 0, 6), "waist": (0, 0, -9), "chest": (0, 0, -2), "head": (0, 10, -3),
        "r_hip": (0, 0, -6), "l_hip": (10, -10, 9), "l_knee": (20, 0, 0),
        "r_wrist": (10, 0, 0), "l_shoulder": (4, 0, 8), "l_elbow": (10, 0, 0),
        "_reach": {"r": "hip"},
    },
    "heroic": {   # both hands on the hips, chest open, weight on one leg
        "pelvis": (0, 0, 5), "waist": (-2, 0, -7), "chest": (-5, 0, -2), "head": (-3, 12, -2),
        "r_hip": (0, 0, -5), "l_hip": (8, -12, 10), "l_knee": (14, 0, 0), "l_ankle": (-6, 0, 0),
        "l_wrist": (10, 0, 0), "r_wrist": (10, 0, 0),
        "_reach": {"l": "hip", "r": "hip"},
    },
    "david": {   # contrapposto, one hand raised to the shoulder, the head turned over it
        "pelvis": (0, 0, 7), "waist": (2, 0, -10), "chest": (0, -6, -3), "neck": (0, -10, 2), "head": (-2, -26, 3),
        "r_hip": (-2, 0, -7), "l_hip": (16, -14, 12), "l_knee": (30, 0, 0), "l_ankle": (-10, 0, 0),
        "r_shoulder": (4, 0, 10), "r_elbow": (16, 0, 0), "r_wrist": (6, 0, 0),
        "_reach": {"l": "own_shoulder"},
    },
    "arms_crossed": {   # forearms folded across the chest
        "pelvis": (0, 0, 4), "waist": (0, 0, -5), "head": (2, 8, -2), "r_hip": (0, 0, -4), "l_hip": (6, -8, 7), "l_knee": (10, 0, 0),
        "_reach": {"l": "fold", "r": "fold_under"},
    },
    "walk": {
        "pelvis": (0, 6, 0), "chest": (2, -8, 0),
        "l_hip": (26, 0, 2), "l_knee": (14, 0, 0), "l_ankle": (8, 0, 0),
        "r_hip": (-16, 0, 2), "r_knee": (24, 0, 0), "r_ankle": (-18, 0, 0),
        "l_shoulder": (-22, 0, 6), "l_elbow": (18, 0, 0), "r_shoulder": (24, 0, 6), "r_elbow": (30, 0, 0),
    },
    "venus": {   # classical modest pose: one arm across the chest, one lowered in front
        "pelvis": (0, 0, 7), "waist": (3, 0, -11), "chest": (0, 0, -2), "neck": (0, 0, 3), "head": (6, -14, 6),
        "l_hip": (15, -12, 11), "l_knee": (30, 0, 0), "l_ankle": (-10, 0, 0), "r_hip": (-2, 0, -7),
        "r_shoulder": (31, -81, 0), "r_elbow": (124, 0, 0), "r_wrist": (8, 0, 0),
        "l_shoulder": (14, -12, -19), "l_elbow": (14, 0, 0), "l_wrist": (6, 0, 0),
    },
    "allure": {   # weight on one leg, one hand in the hair behind the head, the other resting on the thigh
        "pelvis": (0, 4, 8), "waist": (2, -3, -12), "chest": (-3, -4, -3), "neck": (0, 0, 4), "head": (4, 14, 8),
        "r_hip": (-2, 0, -8), "l_hip": (18, -14, 12), "l_knee": (34, 0, 0), "l_ankle": (-12, 0, 0),
        "l_shoulder": (8, 0, 12), "l_elbow": (22, 0, 0), "l_wrist": (10, 0, 0),
        "_reach": {"r": "behind_head"},
    },
    "arms_behind_head": {   # both hands in the hair; opens the chest and lifts the ribcage
        "pelvis": (0, 0, 6), "waist": (0, 0, -8), "chest": (-6, 0, -2), "head": (2, -8, 4),
        "r_hip": (-2, 0, -6), "l_hip": (12, -10, 9), "l_knee": (22, 0, 0),
        "_reach": {"l": "behind_head", "r": "behind_head"},
    },
    "arms_up": {
        "l_shoulder": (10, 0, 150), "r_shoulder": (10, 0, 150), "l_elbow": (30, 0, 0), "r_elbow": (30, 0, 0),
        "chest": (-4, 0, 0),
    },
    "sit": {
        "l_hip": (88, 0, 6), "r_hip": (88, 0, 6), "l_knee": (88, 0, 0), "r_knee": (88, 0, 0),
        "l_shoulder": (22, 0, 6), "r_shoulder": (22, 0, 6), "l_elbow": (50, 0, 0), "r_elbow": (50, 0, 0),
        "waist": (4, 0, 0),
    },
}


class Figure:
    """A posed mannequin.

    sex      'female' | 'male'
    heads    total height in head units: 7.5 natural, 8 idealised, 6.5-7 anime, 8.5 fashion
    slim     scales limb and torso thickness (1.0 = table values)
    bust     breast size factor for the female build (0 removes the masses)
    curves   female waist-to-hip contrast: 0.6 straight, 1.0 hourglass, 1.3 pronounced
    pose     preset name or {joint: (forward, twist, side)} in degrees; merged over 'stand'
    hands    {'l': preset or dict, 'r': ...} from HAND_POSES
    turn     whole-figure yaw: 0 faces the viewer, + turns toward the viewer's right
    """

    def __init__(self, sex="female", heads=7.75, slim=1.0, bust=1.0, pose="relaxed", hands=None,
                 turn=0.0, lean=0.0, tilt=0.0, head_scale=1.0, curves=1.0, tone=None):
        self.sex, self.heads, self.slim, self.bust, self.curves = sex, heads, slim, bust, curves
        self.tone = DEFAULT_TONE[sex] if tone is None else tone      # muscle definition 0 smooth .. 1 athletic
        self.spec = SEX[sex]
        self.k = (heads - 1.0) / (CANON_HEADS - 1.0)        # body scale relative to the head
        self.head_scale = head_scale
        self.pose = dict(POSES[pose]) if isinstance(pose, str) else dict(pose)
        self.hands = dict(POSE_HANDS.get(pose, {"l": "relaxed", "r": "relaxed"})) if isinstance(pose, str) else {"l": "relaxed", "r": "relaxed"}
        self.hands.update(hands or {})
        self.turn, self.lean, self.tilt = turn, lean, tilt
        self.extra_masses = []          # garments and props add (name, group, node list / ellipsoids)
        self.late = {}                  # {name: callable(view) -> masses} stamped after the body (hair locks resting on it)
        self.extra_carves = []          # hollows pressed into the surface: dict(point=world, radius=HU, depth=HU)
        self.head_profile = HEAD_PROFILE
        self.face_relief = None         # callable (u, v) -> forward displacement in HU; set by head.prepare
        self.ears = True
        self.neck_scale = 1.0           # drawing styles slim the neck (anime about 0.75)
        self._solve()
        for side, target in self.pose.get("_reach", {}).items():     # pose presets may place a hand by target
            self.reach(side, target)

    # ----- kinematics -----
    def set_pose(self, **joints):
        self.pose.update(joints)
        self._solve()
        return self

    def _rest(self, name):
        side, base = (name[0], name[2:]) if name[:2] in ("l_", "r_") else ("", name)
        x, y, z = REST["l_" + base] if side else REST[base]
        if base == "shoulder":
            x = self.spec["shoulder_x"]
        elif base in ("elbow", "wrist"):
            x += self.spec["shoulder_x"] - REST["l_shoulder"][0]
        elif base in ("hip", "knee", "ankle"):
            x += self.spec["hip_x"] - REST["l_hip"][0]
        if side == "r":
            x = -x
        return np.array([x, y, z]) * self.k

    def _local_rotation(self, name):
        fwd, twist, side_angle = self.pose.get(name, (0, 0, 0))
        side, base = (name[0], name[2:]) if name[:2] in ("l_", "r_") else ("", name)
        mirror = -1 if side == "r" else 1
        if base == "clav":          # (forward, -, raise)
            return _rot_z(side_angle * mirror) @ _rot_y(-fwd * mirror)
        if side:
            sx, sy, sz = LIMB_SIGNS[base]
            return _rot_z(side_angle * sz * mirror) @ _rot_x(fwd * sx) @ _rot_y(twist * sy * mirror)
        sx, sy, sz = SPINE_SIGNS
        return _rot_z(side_angle * sz) @ _rot_x(fwd * sx) @ _rot_y(twist * sy)

    def _solve(self):
        names = []
        for base in ORDER:
            names += [base] if base in REST else ["l_" + base, "r_" + base]
        self.R, self.P = {}, {}
        root = _rot_y(self.turn) @ _rot_x(self.lean) @ _rot_z(-self.tilt)
        for name in names:
            side, base = (name[0], name[2:]) if name[:2] in ("l_", "r_") else ("", name)
            parent = PARENT["l_" + base] if side else PARENT[base]
            if parent and parent.startswith("l_") and side == "r":
                parent = "r_" + parent[2:]
            local = self._local_rotation(name)
            if parent is None:
                self.R[name] = root @ local
                self.P[name] = self._rest(name)
            else:
                self.R[name] = self.R[parent] @ local
                self.P[name] = self.P[parent] + self.R[parent] @ (self._rest(name) - self._rest(parent))
        # Stand on the ground: lowest sole point at y = 0, pelvis recentred over x = z = 0.
        lowest = min(self._foot_points(side)[:, 1].min() for side in ("l", "r"))
        shift = np.array([-self.P["pelvis"][0], -lowest, -self.P["pelvis"][2]])
        for name in self.P:
            self.P[name] = self.P[name] + shift

    def reach(self, side, target=None, anchor="chest", bend_hint=60.0, world=None, elbow=None):
        """Pose one arm so the wrist reaches a point on or near the body (inverse kinematics).

        side    'l' or 'r'
        target  a key of REACH_TARGETS, or (x, y, z) in rest-pose coordinates (x is mirrored for the right arm,
                so positive x always means 'toward this arm's own side')
        anchor  joint the target moves with ('chest', 'pelvis', 'head', ...); ignored for named targets
        world   a fixed point in this figure's world space in place of target (another figure's shoulder, say)
        elbow   optional world point the elbow should stay near (steers the arm behind or in front of things)
        Returns the remaining distance in head units (below 0.1 means the hand got there).
        """
        from scipy.optimize import minimize
        if target == "hip":                  # the hand rests on this body's own hip, whatever its width
            _, rest = self.table_point("torso", 4.62, 84)
            anchor, target = "pelvis", (rest[0] + 0.07, 4.66, rest[2] + 0.04)
        hint = ELBOW_HINTS.get(target) if isinstance(target, str) else None
        if isinstance(target, str) and target != "hip":
            anchor, target = REACH_TARGETS[target]
        mirror = -1 if side == "r" else 1
        fixed = None if world is None else np.asarray(world, float)
        rest = fixed if fixed is not None else np.array([target[0] * mirror, target[1], target[2]], float)
        elbow_goal = None if elbow is None else np.asarray(elbow, float)
        shoulder, elbow, wrist = side + "_shoulder", side + "_elbow", side + "_wrist"

        overhead = fixed is None and rest[1] > 6.6     # a hand at the head: the forearm must not pass in front of the face

        def cost(values):
            fwd, twist, out, bend = values
            self.pose[shoulder], self.pose[elbow] = (fwd, twist, out), (bend, 0, 0)
            self._solve()
            goal = fixed if fixed is not None else self.world(anchor, rest)
            miss = np.linalg.norm(self.P[wrist] - goal) / self.k
            if overhead:
                ahead = (self.R["chest"].T @ (self.P[elbow] - self.P["chest"]))[2] / self.k
                miss += 0.5 * max(0.0, ahead - 0.15)
            if hint is not None:
                miss += 0.3 * np.linalg.norm(self.P[elbow] - self.world("chest", (hint[0] * mirror, hint[1], hint[2]))) / self.k
            if elbow_goal is not None:
                miss += 0.3 * np.linalg.norm(self.P[elbow] - elbow_goal) / self.k
            comfort = 0.0004 * abs(twist) + 0.0002 * abs(out) + 0.004 * max(0.0, -out - 25) + 0.004 * max(0.0, bend - 150) \
                + 0.004 * max(0.0, -bend)
            return miss + comfort
        best = None
        starts = [(20, 0, 10, bend_hint), (40, -40, 10, 90), (10, 40, 30, 100), (70, -20, 0, 40)]
        if overhead:
            starts += [(30, 0, 130, 140), (10, 30, 150, 150)]
        for start in starts:
            result = minimize(cost, start, method="Nelder-Mead", options=dict(xatol=0.5, fatol=1e-4, maxiter=400))
            if best is None or result.fun < best.fun:
                best = result
        fwd, twist, out, bend = (float(round(v, 1)) for v in best.x)
        self.pose[shoulder], self.pose[elbow] = (fwd, twist, out), (bend, 0, 0)
        self._solve()
        goal = fixed if fixed is not None else self.world(anchor, rest)
        return float(np.linalg.norm(self.P[wrist] - goal) / self.k)

    def world(self, joint, rest_point):
        """World position of a point given in rest-pose coordinates and bound to a joint."""
        return self.P[joint] + self.R[joint] @ (np.asarray(rest_point, float) * self.k - self._rest(joint))

    def head_point(self, local):
        """World position of a point in head-local HU (origin = head joint; x right, y up, z front)."""
        return self.P["head"] + self.R["head"] @ (np.asarray(local, float) * self.head_scale)

    def _foot_points(self, side):
        mirror = -1 if side == "r" else 1
        joint = side + "_ankle"
        x = (0.30 + self._dx("ankle")) * mirror
        return np.array([self.world(joint, (x, 0.0, z)) for z in (-0.30, 0.70)])

    def _dx(self, base):
        if base in ("hip", "knee", "ankle"):
            return self.spec["hip_x"] - REST["l_hip"][0]
        if base in ("shoulder", "elbow", "wrist"):
            return self.spec["shoulder_x"] - REST["l_shoulder"][0]
        return 0.0

    # ----- surface points -----
    def table_point(self, name, y, angle, side="l"):
        """Rest-pose point on the surface of a body table at height y, `angle` degrees around its axis.

        name   'torso', 'neck', 'upper_arm', 'forearm', 'thigh', 'shin'
        angle  0 front, 90 outward (the figure's left on the torso and neck), 180 back, 270 inward
        Returns (joint, rest point) for world(joint, point).
        """
        if name == "torso":
            rows, scale = self._torso_table(), self.slim
        elif name == "neck":
            rows, scale = self.spec["masses"]["neck"], self.spec["neck"] * self.neck_scale
        else:
            rows, scale = self.spec["masses"][name], self.spec["limb"] * self.slim
        rows = sorted(rows, key=lambda row: row[1][1])
        ys = np.array([row[1][1] for row in rows])
        pick = lambda k: float(np.interp(y, ys, [row[k] for row in rows]))           # noqa: E731
        cx, cz = (float(np.interp(y, ys, [row[1][i] for row in rows])) for i in (0, 2))
        width, front, back = pick(2) * scale, pick(3) * scale, pick(4) * scale
        joint = rows[int(np.argmin(np.abs(ys - y)))][0]
        a = np.radians(angle)
        depth = front if np.cos(a) >= 0 else back
        mirror = -1 if side == "r" else 1
        if joint.startswith("l_"):
            base = joint[2:]
            x = (cx + self._dx(base) + np.sin(a) * width) * mirror
            joint = side + "_" + base
        else:
            x = cx + np.sin(a) * width
        return joint, (x, y, cz + np.cos(a) * depth)

    def _mark(self, name, y, angle, radius, amount, side="l"):
        joint, rest = self.table_point(name, y, angle, side)
        return dict(point=self.world(joint, rest), radius=radius * self.k, depth=amount * self.k)

    def _line(self, name, start, end, radius, amount, side="l", count=None):
        """Closely spaced marks from (y, angle) to (y, angle): they merge into one groove or ridge.

        Marks are spaced at most half a radius apart along the height, so the line never breaks into beads.
        """
        if count is None:
            count = max(int(abs(end[0] - start[0]) / (radius * 0.5)) + 1, 4)
        return [self._mark(name, start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t, radius, amount, side)
                for t in np.linspace(0, 1, count)]

    def anatomy(self):
        """Muscle and bone landmarks as (hollows, swells), scaled by `tone`. Plausible, not an atlas.

        Hollows: notch at the base of the throat, dimples of Venus, the groove of the hip, the deltoid's
        V, the line between biceps and triceps, the hollows beside the knee tendon and the Achilles.
        Swells: the neck cords, shoulder blades, hip bones, forearm, the teardrop above the inner knee,
        the calf. A male build adds the abdominal grid and the lower border of the chest.
        """
        t = self.tone
        if t <= 0:
            return [], []
        dents, swells = [], []
        dents.append(self._mark("torso", 6.56, 0, 0.045, 0.03 * t))                                  # jugular notch
        for s, sign in (("l", 1), ("r", -1)):
            swells += self._line("neck", (7.0, 75 * sign), (6.62, 12 * sign), 0.035, 0.014 * t)              # neck cord
            swells.append(self._mark("torso", 5.98, 180 - 34 * sign, 0.15, 0.022 * t))              # shoulder blade
            dents += self._line("torso", (6.25, 180 - 15 * sign), (5.72, 180 - 21 * sign), 0.035, 0.012 * t)
            dents.append(self._mark("torso", 4.55, 180 - 21 * sign, 0.042, 0.03 * t))              # dimple of Venus
            swells.append(self._mark("torso", 4.42, 60 * sign, 0.06, 0.012 * t))                     # hip bone
            dents += self._line("torso", (4.36, 56 * sign), (3.98, 22 * sign), 0.04, 0.011 * t)     # groove of the hip
            dents += self._line("torso", (5.56, 10 * sign), (5.30, 48 * sign), 0.04, 0.008 * t * (2.0 if self.sex == "male" else 1.0))
            dents += self._line("upper_arm", (6.15, 35), (5.78, 90), 0.03, 0.01 * t, s)             # deltoid V
            dents += self._line("upper_arm", (6.15, 145), (5.78, 90), 0.03, 0.01 * t, s)
            dents += self._line("upper_arm", (5.72, 90), (5.22, 96), 0.028, 0.008 * t, s)          # biceps | triceps
            swells.append(self._mark("forearm", 4.8, 50, 0.07, 0.014 * t, s))                         # forearm muscle
            swells.append(self._mark("thigh", 2.48, 300, 0.09, 0.02 * t, s))                          # inner knee teardrop
            dents += self._line("thigh", (3.35, 96), (2.5, 96), 0.035, 0.008 * t, s)               # outer thigh band
            for side_angle in (35, 325):
                dents.append(self._mark("shin", 1.96, side_angle, 0.035, 0.012 * t, s))             # beside the knee tendon
            swells.append(self._mark("shin", 1.68, 212, 0.09, 0.02 * t, s))                           # calf, inner head
            swells.append(self._mark("shin", 1.76, 150, 0.075, 0.014 * t, s))                         # calf, outer head
            for side_angle in (135, 225):
                dents.append(self._mark("shin", 0.62, side_angle, 0.035, 0.012 * t, s))             # beside the Achilles
            if self.sex == "male":
                swells.append(self._mark("upper_arm", 5.62, 12, 0.11, 0.03 * t, s))                     # biceps
                swells.append(self._mark("upper_arm", 5.85, 192, 0.11, 0.022 * t, s))                   # triceps
                swells.append(self._mark("thigh", 2.95, 78, 0.13, 0.026 * t, s))                        # outer quadriceps
                swells += self._line("thigh", (3.55, 4), (2.6, 2), 0.07, 0.016 * t, s)                  # rectus femoris
                swells.append(self._mark("torso", 4.56, 64 * sign, 0.08, 0.02 * t))                     # obliques over the hip
                dents.append(self._mark("torso", 4.08, 96 * sign, 0.07, 0.03 * t))                      # hollow at the side of the seat
                dents += self._line("torso", (5.74, 4 * sign), (5.86, 58 * sign), 0.055, 0.015 * t)  # lower chest border
                for y in (5.36, 5.08, 4.82):                                                          # abdominal grid
                    dents += self._line("torso", (y, 4 * sign), (y + 0.03, 26 * sign), 0.04, 0.011 * t, count=8)
                for k in range(4):                                                                    # serratus
                    dents.append(self._mark("torso", 5.72 - k * 0.12, 72 * sign, 0.03, 0.01 * t))
        if self.sex == "male":
            swells.append(self._mark("neck", 6.84, 0, 0.045, 0.028))                               # Adam's apple
        return dents, swells

    # ----- masses -----
    def _nodes(self, table, side, radius_scale):
        """Table rows -> world points, axes and radii for one sweep."""
        mirror = -1 if side == "r" else 1
        pts, lat, sag, w, f, b = [], [], [], [], [], []
        for joint, (x, y, z), width, front, back in table:
            base = joint[2:] if joint.startswith("l_") else joint
            name = (side + "_" + base) if joint.startswith("l_") else joint
            x = (x + (self._dx(base) if joint.startswith("l_") else 0.0)) * mirror
            pts.append(self.world(name, (x, y, z)))
            lat.append(self.R[name] @ [1, 0, 0])
            sag.append(self.R[name] @ [0, 0, 1])
            w.append(width * self.k * radius_scale)
            f.append(front * self.k * radius_scale)
            b.append(back * self.k * radius_scale)
        return dict(points=np.array(pts), lateral=np.array(lat), sagittal=np.array(sag),
                    width=np.array(w), front=np.array(f), back=np.array(b))

    def masses(self):
        """Body, head and added masses (garments, hair) as dicts: sweeps (points...) or ellipsoids (centre...)."""
        return self._body_masses() + self._head() + self.extra_masses

    def _torso_table(self):
        """Torso rows with the figure's curves applied: fuller hips and a narrower waist as `curves` rises."""
        rows = []
        for joint, (x, y, z), width, front, back in self.spec["masses"]["torso"]:
            if self.sex == "female":
                c = self.curves - 1.0
                hip = np.exp(-((y - 4.18) / 0.33) ** 2)
                waist = np.exp(-((y - 5.0) / 0.3) ** 2)
                width *= 1 + 0.10 * c * hip - 0.14 * c * waist
                back *= 1 + 0.10 * c * hip
            rows.append((joint, (x, y, z), width, front, back))
        return rows

    def surface_z(self, y, side="front"):
        """Rest-pose z of the torso surface on the midline at height y (front or back), from the torso table."""
        rows = sorted(self._torso_table(), key=lambda row: row[1][1])
        ys = [row[1][1] for row in rows]
        edge = [row[1][2] + (row[3] if side == "front" else -row[4]) for row in rows]
        return float(np.interp(y, ys, edge))

    def _body_masses(self):
        tables = self.spec["masses"]
        limb = self.spec["limb"] * self.slim
        soft = self.k * self.slim
        out = [dict(part="torso", group="trunk", **self._nodes(self._torso_table(), "l", self.slim)),
               dict(part="neck", group="trunk", **self._nodes(tables["neck"], "l", self.spec["neck"] * self.neck_scale))]

        def bump(part, group, joint, rest, radii, scale, tilt=None):
            axes = self.R[joint] if tilt is None else self.R[joint] @ tilt
            return dict(part=part, group=group, rest_y=rest[1], centre=self.world(joint, rest), axes=axes,
                        radii=np.asarray(radii, float) * scale)
        if self.sex == "female" and self.bust > 0:
            size = self.k * (0.72 + 0.28 * self.bust)
            push = 0.06 * (self.bust - 1)
            rot = self.R["chest"]
            for side, mirror in (("l", 1), ("r", -1)):
                # A breast is a teardrop: it leaves the chest wall high under the collarbone, swells downward and
                # slightly outward, and is fullest low. One swept form gives that without seams.
                # The upper part is a wide, thin sheet lying on the chest, so the form rises out of it gradually.
                wall = self.surface_z(5.9) - 0.33              # how far the chest wall sits forward of the reference build
                path = [(0.25 * mirror, 6.27, 0.14 + wall), (0.28 * mirror, 6.12, 0.20 + wall + push * 0.4),
                        (0.31 * mirror, 5.96, 0.30 + wall + push), (0.32 * mirror, 5.86, 0.335 + wall + push),
                        (0.315 * mirror, 5.79, 0.31 + wall + push)]
                out.append(dict(part="breast_" + side, group="trunk", rest_y=5.98, roundness=1.0, blend=0.08,
                                points=np.array([self.world("chest", p) for p in path]),
                                lateral=rot @ _rot_y(14 * mirror) @ [1, 0, 0], sagittal=rot @ _rot_y(14 * mirror) @ [0, 0.45, 0.89],
                                width=np.array([0.23, 0.225, 0.215, 0.20, 0.14]) * size,
                                front=np.array([0.05, 0.11, 0.165, 0.16, 0.10]) * size))
        # Surface anatomy: low masses that catch the light (belly, hip bones, kneecaps, collarbones).
        # A deep, wide ellipsoid that only just breaks the surface: the lower belly swells without an edge.
        belly = bump("torso", "trunk", "pelvis", (0, 4.56, self.surface_z(4.56) - 0.15), (0.30, 0.28, 0.18), soft)
        belly["blend"] = 0.04
        out.append(belly)
        for side, mirror in (("l", 1), ("r", -1)):
            knee_x = (0.33 + self._dx("knee")) * mirror
            out.append(bump("thigh_" + side, "leg_" + side, side + "_knee", (knee_x, 2.15, 0.17), (0.095, 0.12, 0.065), limb * self.k))
            out.append(dict(part="torso", group="trunk", rest_y=6.47,                                   # collarbone
                            points=np.array([self.world("chest", (0.05 * mirror, 6.455, self.surface_z(6.455) - 0.03)),
                                             self.world("chest", (0.30 * mirror, 6.49, self.surface_z(6.49) - 0.07)),
                                             self.world(side + "_clav", ((self.spec["shoulder_x"] - 0.12) * mirror, 6.50, 0.03))]),
                            lateral=self.R["chest"] @ [0, 1, 0], sagittal=self.R["chest"] @ [0, 0, 1],
                            width=np.array([0.03, 0.026, 0.03]) * soft, front=np.array([0.03, 0.026, 0.03]) * soft, roundness=1.0))
            girdle = (self.spec["shoulder_x"] - 0.20) * mirror
            girdle_mass = bump("torso", "trunk", side + "_clav", (girdle, 6.40, -0.03), (0.30, 0.13, 0.19), soft, _rot_z(-16 * mirror))
            girdle_mass["blend"] = 0.05                  # the shoulder girdle rounds into the deltoid cap
            out.append(girdle_mass)
            if self.sex == "male":
                out += self._male_masses(side, mirror, soft, limb)
            fullness = 1 + 0.10 * (self.curves - 1.0) if self.sex == "female" else 0.74      # male seat: smaller, squarer
            back = self.surface_z(4.1, "back") + 0.45          # follows the depth of the hips in the torso table
            seat = [(0.29 * mirror, 4.46, -0.12 + back), (0.28 * mirror, 4.24, -0.17 + back),
                    (0.26 * mirror, 4.03, -0.21 + back), (0.25 * mirror, 3.93, -0.20 + back)]
            out.append(dict(part="buttock_" + side, group="trunk", rest_y=4.05, roundness=1.0, blend=0.10,     # gluteal mass
                            points=np.array([self.world("pelvis", p) for p in seat]),
                            lateral=self.R["pelvis"] @ [1, 0, 0], sagittal=self.R["pelvis"] @ [0, 0, -1],
                            width=np.array([0.28, 0.33, 0.34, 0.29]) * soft * fullness,
                            front=np.array([0.16, 0.24, 0.29, 0.26]) * soft * fullness))
            out.append(bump("shin_" + side, "leg_" + side, side + "_ankle", ((0.30 + self._dx("ankle") + 0.085) * mirror, 0.40, -0.04),
                            (0.04, 0.05, 0.045), limb * self.k))                                           # outer ankle bone
            # Upper arm and thigh join the trunk with a fillet: shoulder and hip have no seam.
            for name, group, blend in (("upper_arm", "arm_", 0.05), ("forearm", "arm_", 0), ("thigh", "leg_", 0.06), ("shin", "leg_", 0)):
                out.append(dict(part=f"{name}_{side}", group=group + side, blend=blend, **self._nodes(tables[name], side, limb)))
            out += self._hand(side)
            out += self._foot(side)
        return out

    def _male_masses(self, side, mirror, soft, limb):
        """Muscle masses that shape a male silhouette: chest plates, deltoid caps, the wings of the back."""
        out = []
        rot = self.R["chest"]
        plate = []
        for y, angle in ((5.98, 6), (6.0, 24), (6.1, 46)):
            joint, rest = self.table_point("torso", y, angle * mirror)
            plate.append(self.world(joint, (rest[0], rest[1], rest[2] - 0.05)))
        out.append(dict(part="chest_" + side, group="trunk", rest_y=6.0, blend=0.06, roundness=1.0, points=np.array(plate),
                        lateral=rot @ [0, 1, 0], sagittal=rot @ [0, 0, 1],
                        width=np.array([0.17, 0.2, 0.15]) * soft, front=np.array([0.09, 0.11, 0.07]) * soft))
        cap = self.world(side + "_shoulder", ((self.spec["shoulder_x"] - 0.02) * mirror, 6.16, 0.0))
        out.append(dict(part="upper_arm_" + side, group="arm_" + side, rest_y=6.16, blend=0.12, centre=cap,
                        axes=self.R[side + "_shoulder"] @ _rot_z(-8 * mirror), radii=np.array([0.16, 0.24, 0.19]) * limb * self.k))
        trap = [self.world("chest", (x * mirror, y, z)) for x, y, z in ((0.17, 6.86, -0.10), (0.42, 6.66, -0.10), (0.68, 6.47, -0.07))]
        out.append(dict(part="torso", group="trunk", rest_y=6.66, blend=0.10, roundness=1.0, points=np.array(trap),
                        lateral=rot @ [0, 0, 1], sagittal=rot @ [0, 1, 0],
                        width=np.array([0.14, 0.17, 0.13]) * soft, front=np.array([0.06, 0.075, 0.05]) * soft))   # trapezius
        wing = []
        for y, angle in ((6.02, 112), (5.65, 106), (5.3, 98)):
            joint, rest = self.table_point("torso", y, angle * mirror)
            wing.append(self.world(joint, (rest[0] - 0.04 * mirror, rest[1], rest[2])))
        out.append(dict(part="torso", group="trunk", rest_y=5.65, blend=0.07, roundness=1.0, points=np.array(wing),
                        lateral=rot @ [0, 0, 1], sagittal=rot @ [mirror, 0, 0],
                        width=np.array([0.16, 0.14, 0.07]) * soft, front=np.array([0.08, 0.07, 0.03]) * soft))
        return out

    def carves(self):
        """Hollows pressed into the surface after the masses are joined: spine furrow, breastbone, midline, navel.

        Each entry is dict(point=world position on the surface, radius=HU, depth=HU). Closely spaced entries
        merge into one continuous furrow.
        """
        k = self.k
        out = []
        for y in np.linspace(4.7, 6.4, 40):                                # furrow of the spine, deepest at the waist
            hollow = 0.25 + 0.05 * np.exp(-((y - 5.0) / 0.4) ** 2)
            depth = 0.022 + 0.02 * np.exp(-((y - 5.1) / 0.5) ** 2)
            out.append(dict(point=self.world("chest" if y > 5.2 else "waist", (0, y, self.surface_z(y, "back") + hollow - 0.25)),
                            radius=0.06 * k, depth=depth * k))
        if self.sex == "female" and self.bust > 0:
            for y in np.linspace(5.7, 6.25, 12):                            # breastbone, between the breasts
                out.append(dict(point=self.world("chest", (0, y, self.surface_z(y))), radius=0.07 * k, depth=0.022 * k))
        for y in np.linspace(4.7, 5.45, 16):                                # midline of the abdomen
            out.append(dict(point=self.world("waist" if y < 5.2 else "chest", (0, y, self.surface_z(y))), radius=0.05 * k, depth=0.012 * k))
        out.append(dict(point=self.world("waist", (0, 4.92, self.surface_z(4.92))), radius=0.022 * k, depth=0.03 * k))   # navel
        if self.sex == "male":
            for y in np.linspace(4.7, 5.6, 14):                              # the midline runs deeper between the abdominals
                out.append(dict(point=self.world("waist" if y < 5.2 else "chest", (0, y, self.surface_z(y))), radius=0.04 * k,
                                depth=0.016 * self.tone * k))
        return out + self.extra_carves

    def _head(self):
        from .head import head_grid
        rot, hs = self.R["head"], self.head_scale
        local = head_grid(self.head_profile, self.face_relief)
        out = [dict(part="head", group="head", surface=self.P["head"] + (local * hs) @ rot.T)]
        if self.ears:
            for side, mirror in (("l", 1), ("r", -1)):
                out.append(dict(part="ear_" + side, group="head", centre=self.head_point((0.335 * mirror, 0.36, -0.13)),
                                axes=rot @ _rot_y(-22 * mirror), radii=np.array([0.035, 0.105, 0.06]) * hs))
        return out

    def hand_frame(self, side):
        """(wrist position, D, T, N): finger direction, thumb-side direction, palm normal (world)."""
        mirror = -1 if side == "r" else 1
        rot = self.R[side + "_wrist"]
        return (self.P[side + "_wrist"], rot @ [0, -1, 0], rot @ [0, 0, 1], rot @ [-mirror, 0, 0])

    def _hand(self, side):
        pose = self.hands[side]
        pose = HAND_POSES[pose] if isinstance(pose, str) else pose
        wrist, D, T, N = self.hand_frame(side)
        k = self.k * self.spec.get("hand", 1.0)
        group = "hand_" + side
        out = [dict(part=f"palm_{side}", group=group,
                    points=np.array([wrist + D * 0.02 * k, wrist + D * 0.22 * k, wrist + D * 0.42 * k]),
                    lateral=T, sagittal=N, width=np.array([0.105, 0.165, 0.17]) * k,
                    front=np.array([0.06, 0.07, 0.055]) * k, back=np.array([0.055, 0.06, 0.05]) * k)]
        for index, (name, (d, t, length, radius, spread_sign)) in enumerate(FINGERS.items()):
            mcp, pip = pose["curl"][index]
            angles = np.cumsum([mcp, pip, pip * 0.65])
            spread = np.radians(pose["spread"] * spread_sign)
            dir0 = D * np.cos(spread) + T * np.sin(spread)
            across = np.cross(N, dir0)
            point = wrist + (D * d + T * t) * k
            pts, normals = [point], []
            for seg, angle in zip(PHALANX, np.radians(angles)):
                direction = dir0 * np.cos(angle) + N * np.sin(angle)
                normals.append(N * np.cos(angle) - dir0 * np.sin(angle))
                point = point + direction * length * seg * k
                pts.append(point)
            for j in range(3):
                r0, r1 = radius * (1 - 0.07 * j) * k, radius * (1 - 0.07 * (j + 1)) * k
                out.append(dict(part=f"{name}_{side}", group=group, points=np.array([pts[j], pts[j + 1]]),
                                lateral=across, sagittal=normals[j], width=np.array([r0, r1]),
                                front=np.array([r0, r1]) * 0.92, roundness=1.0))
        splay, oppose, curl = np.radians(pose["thumb"])
        dir0 = D * np.cos(splay) + T * np.sin(splay)
        dir0 = dir0 * np.cos(oppose) + N * np.sin(oppose)
        flex = N * 0.55 - T * 0.85
        flex = flex - (flex @ dir0) * dir0
        flex /= np.linalg.norm(flex)
        point = wrist + (D * 0.09 + T * 0.125 + N * 0.03) * k
        across = np.cross(flex, dir0)
        for j, (seg_len, radius, angle) in enumerate(((0.20, 0.058, 0.0), (0.155, 0.047, curl * 0.5), (0.13, 0.042, curl))):
            direction = dir0 * np.cos(angle) + flex * np.sin(angle)
            nxt = point + direction * seg_len * k
            out.append(dict(part=f"thumb_{side}", group=group, points=np.array([point, nxt]), lateral=across,
                            sagittal=flex * np.cos(angle) - dir0 * np.sin(angle),
                            width=np.array([radius, radius * 0.9]) * k, front=np.array([radius, radius * 0.9]) * 0.92 * k,
                            roundness=1.0))
            point = nxt
        return out

    def _foot(self, side):
        mirror = -1 if side == "r" else 1
        joint = side + "_ankle"
        dx = self._dx("ankle")
        rot = self.R[joint]

        size = self.spec.get("foot", 1.0)               # a larger foot grows forward and sideways from the ankle

        def at(x, y, z):
            return self.world(joint, ((0.30 + (x - 0.30) * size + dx) * mirror, y, z * size))
        k = self.k * size
        group = "leg_" + side
        out = [dict(part=f"foot_{side}", group=group,
                    points=np.array([at(0.30, 0.12, -0.15), at(0.30, 0.17, 0.00), at(0.305, 0.12, 0.22),
                                     at(0.31, 0.085, 0.42), at(0.31, 0.07, 0.52)]),
                    lateral=rot @ [1, 0, 0], sagittal=rot @ [0, 1, 0],
                    width=np.array([0.095, 0.11, 0.145, 0.18, 0.165]) * k,
                    front=np.array([0.10, 0.17, 0.115, 0.072, 0.05]) * k,
                    back=np.array([0.10, 0.14, 0.095, 0.068, 0.052]) * k)]
        for i, (offset, length, radius, setback) in enumerate(TOES):
            start = at(0.31 + offset, 0.055, 0.50 - setback)
            end = at(0.31 + offset, 0.045, 0.50 - setback + length)
            out.append(dict(part=f"toe{i + 1}_{side}", group="toes_" + side, points=np.array([start, end]),
                            lateral=rot @ [1, 0, 0], sagittal=rot @ [0, 1, 0],
                            width=np.array([radius, radius * 0.92]) * k, front=np.array([radius, radius * 0.85]) * 0.9 * k,
                            roundness=1.0))
        return out


class FigureView:
    """A figure placed on a canvas: owns the projection and the rendered relief."""

    depth = 0.0                     # class defaults, so views built by subclasses (Sculpture) have them too
    hidden = None

    def __init__(self, figure, canvas, x, ground_y, height, supersample=2):
        self.figure, self.canvas = figure, canvas
        self.unit = height / figure.heads                 # design units per head unit
        self.x, self.ground_y = x, ground_y
        self.ss = supersample
        self.px = canvas.scale * supersample              # device px per design unit (relief buffer)
        self.relief = Relief(canvas.W * supersample, canvas.H * supersample)
        self.groups = {}
        self.skin_gloss = 0.0           # sheen on bare skin (0.1 to 0.25 gives lit shoulders and hips a soft highlight)
        self.depth = 0.0                # design units toward the viewer: places this figure in front of or behind others
        self.hidden = None              # relief pixels covered by another figure (set by hide_behind)

    @classmethod
    def closeup(cls, figure, canvas, x, head_top_y, unit, supersample=2):
        """Place the figure by head size: `unit` design units per head, crown at head_top_y.

        Use for busts and half-length portraits where the feet are off-canvas.
        """
        crown = figure.P["head"][1] + 0.92 * figure.head_scale
        view = cls(figure, canvas, x - figure.P["head"][0] * unit, head_top_y + crown * unit,
                   unit * figure.heads, supersample)
        return view

    # ----- projection -----
    def to_device(self, world):
        """World HU -> relief-buffer pixel coordinates (x, y, z)."""
        w = np.atleast_2d(np.asarray(world, float))
        out = np.stack([(self.x + w[:, 0] * self.unit) * self.px,
                        (self.ground_y - w[:, 1] * self.unit) * self.px,
                        (w[:, 2] * self.unit + self.depth) * self.px], axis=1)
        return out if np.ndim(world) > 1 else out[0]

    def to_scene(self, world):
        """World HU -> scene point (x, y, z) in design units, shared by every figure on the canvas."""
        w = np.asarray(world, float)
        return np.array([self.x + w[0] * self.unit, self.ground_y - w[1] * self.unit, w[2] * self.unit + self.depth])

    def from_scene(self, point):
        """Scene point in design units -> this figure's world HU (inverse of to_scene)."""
        x, y, z = (float(v) for v in point)
        return np.array([(x - self.x) / self.unit, (self.ground_y - y) / self.unit, (z - self.depth) / self.unit])

    def hide_behind(self, others):
        """Remove the relief wherever another built figure is in front (same canvas and supersample)."""
        mine = self.relief.mask()
        hidden = np.zeros_like(mine)
        for other in others:
            if other.relief.z.shape != self.relief.z.shape:
                raise ValueError("figures hidden behind each other must share the canvas and supersample")
            hidden |= mine & other.relief.mask() & (other.relief.z > self.relief.z)
        if hidden.any():
            self.relief.z[hidden] = EMPTY
            self.relief.part[hidden] = 0
            self._raw_z[hidden] = EMPTY
        self.hidden = hidden
        return self

    def group_mask(self, group):
        """Coverage (canvas resolution) of every part of one group ('hair', 'trunk', a garment name)."""
        ids = [pid for pid, name in self.groups.items() if name == group]
        return self._down(np.isin(self.relief.part, ids).astype(np.float32))

    def coverage(self):
        """Coverage (canvas resolution) of everything this figure shows."""
        return self._down(self.relief.mask().astype(np.float32))

    def to_canvas(self, world):
        """World HU -> design-unit (x, y) on the canvas, for drawing 2D features on the figure."""
        w = np.atleast_2d(np.asarray(world, float))
        out = np.stack([self.x + w[:, 0] * self.unit, self.ground_y - w[:, 1] * self.unit], axis=1)
        return out if np.ndim(world) > 1 else out[0]

    def _axis(self, v):
        v = np.asarray(v, float)
        flip = np.array([1.0, -1.0, 1.0])
        return v * flip

    def stamp(self, mass):
        if mass.get("blend"):                   # soft tissue: stamp alone, then join with a fillet
            target, self.relief = self.relief, Relief(self.relief.W, self.relief.H)
            self._stamp(mass)
            layer, self.relief = self.relief, target
            layer_groups = {layer.parts[mass["part"]]: mass.get("group", mass["part"])}
            target.smooth_union(layer, mass["blend"] * self.unit * self.px)
            self.groups[target.parts[mass["part"]]] = layer_groups[layer.parts[mass["part"]]]
            return
        self._stamp(mass)

    def _stamp(self, mass):
        scale = self.unit * self.px
        part = self.relief.part_id(mass["part"])
        self.groups[part] = mass.get("group", mass["part"])
        if "surface" in mass:
            grid = np.asarray(mass["surface"], float)
            self.relief.surface(self.to_device(grid.reshape(-1, 3)).reshape(grid.shape), part)
            return
        if "centre" in mass:
            axes = np.asarray(mass["axes"], float) * np.array([[1.0], [-1.0], [1.0]])
            self.relief.ellipsoid(self.to_device(mass["centre"]), axes, np.asarray(mass["radii"]) * scale, part)
            return
        back = mass.get("back")
        self.relief.sweep(self.to_device(mass["points"]), self._axis(mass["lateral"]), self._axis(mass["sagittal"]),
                          mass["width"] * scale, mass["front"] * scale,
                          None if back is None else back * scale, part,
                          roundness=mass.get("roundness", 0.8), flow=mass.get("group") == "hair")

    def build(self, extra=()):
        for mass in list(self.figure.masses()) + list(extra):
            self.stamp(mass)
        for maker in self.figure.late.values():
            for mass in maker(self):
                self.stamp(mass)
        scale = self.unit * self.px
        self._raw_z = self.relief.z.copy()
        self._membrane(scale)
        self._carve(scale)
        modelled = self.relief.z.copy()
        self.relief.smooth(0.035 * scale, 0.05 * scale)
        fine = np.isin(self.relief.part, [pid for pid, group in self.groups.items() if group in ("head", "hair")])
        self.relief.z[fine] = modelled[fine]            # the face and hair keep their fine modelling (lips, lids, locks)
        return self

    def _carve(self, scale):
        """Press hollows into the relief and raise swells, wherever that part of the surface faces the viewer."""
        relief = self.relief
        if self.figure is None:
            return
        inside = relief.mask()
        hollows, swells = self.figure.anatomy() if hasattr(self.figure, "anatomy") else ([], [])
        dent = self._stamp_marks(list(self.figure.carves()) + hollows, scale, inside)
        rise = self._stamp_marks(swells, scale, inside)
        cloth = {m.get("group") for m in self.figure.extra_masses if m.get("tag") == "garment"}
        covered = np.isin(relief.part, [pid for pid, group in self.groups.items() if group in cloth])
        weight = np.where(covered, 0.2, 1.0).astype(np.float32)        # cloth bridges grooves; only a trace shows through
        relief.z += (rise - dent) * inside * weight

    def _stamp_marks(self, marks, scale, inside):
        """Gaussian marks combined by maximum, so a row of them forms one continuous groove or ridge."""
        relief = self.relief
        field = np.zeros((relief.H, relief.W), np.float32)
        for mark in marks:
            x, y, z = self.to_device(mark["point"])
            sigma, depth = mark["radius"] * scale, mark["depth"] * scale
            ix, iy = int(round(x)), int(round(y))
            if not (0 <= ix < relief.W and 0 <= iy < relief.H) or not inside[iy, ix]:
                continue
            if abs(relief.z[iy, ix] - z) > 0.12 * scale:                 # on a side we cannot see
                continue
            reach = int(sigma * 3) + 1
            x0, x1, y0, y1 = max(ix - reach, 0), min(ix + reach + 1, relief.W), max(iy - reach, 0), min(iy + reach + 1, relief.H)
            gx, gy = np.meshgrid(np.arange(x0, x1) - x, np.arange(y0, y1) - y)
            stamp = (depth * np.exp(-(gx ** 2 + gy ** 2) / (2 * sigma ** 2))).astype(np.float32)
            field[y0:y1, x0:x1] = np.maximum(field[y0:y1, x0:x1], stamp)
        return field

    def _membrane(self, scale, reach=0.07, limit=0.10, groups=None):
        """Stretch a skin over the body masses: shallow gaps between neighbouring masses are bridged.

        Separate ellipsoids meet in creases, which is what makes a figure look assembled from parts.
        Closing the height field with a disc fills every crease narrower than the disc, the way skin
        and fat span the muscles underneath. Real overlaps (an arm in front of the torso) are deeper
        than `limit` and stay untouched; hands, toes and the head keep their detail.
        """
        from .relief import EMPTY
        relief = self.relief
        if groups is None:
            skip = [pid for pid, group in self.groups.items() if group.startswith(("hand_", "toes_", "head", "hair"))]
            body = relief.mask() & ~np.isin(relief.part, skip)
        else:           # only these groups (the trunk: breasts and buttocks merging into the torso)
            body = np.isin(relief.part, [pid for pid, group in self.groups.items() if group in groups])
        if not body.any():
            return
        size = max(int(reach * scale) * 2 + 1, 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        z = np.where(body, relief.z, EMPTY).astype(np.float32)
        closed = cv2.erode(cv2.dilate(z, kernel), kernel)
        fill = np.where(body, closed - relief.z, 0.0)
        # The bridge fades out as the gap deepens, so the edge of a filled area never becomes a step.
        weight = np.clip((limit * scale - fill) / (0.5 * limit * scale), 0, 1) * (fill > 0)
        relief.z += (fill * weight).astype(np.float32)

    # ----- output -----
    def part_mask(self, *names):
        """Coverage (0..1, canvas device resolution) of the named parts as visible in the relief."""
        ids = [self.relief.parts[n] for n in names if n in self.relief.parts]
        mask = np.isin(self.relief.part, ids).astype(np.float32)
        return self._down(mask)

    def _down(self, array):
        if self.ss == 1:
            return array
        return cv2.resize(array, (self.canvas.W, self.canvas.H), interpolation=cv2.INTER_AREA)

    def composite(self, colors, region_of=None, default="#e8c4a8", line_width=1.6, line_color=None,
                  crease=0.45, gloss=None, cast=None, lines=True, flatten=None, folds=None, light=None,
                  self_shadow=0.9, occlusion=1.0):
        """Lay the relief onto the canvas.

        colors     {part name or group name: colour}; default colours anything unnamed (skin)
        region_of  {part or group name: canvas region name}; default region is 'skin'
        flatten    {part or group name: 0..1}: turn that form's shading toward the viewer.
                   Cel-style faces use about 0.7 so the face is not cut in half by a shadow.
        folds      {part name: strength}: cloth folds as a normal perturbation running down the garment.
        light      the scene Light: enables shadows the figure casts on itself (chin on neck, arm on torso)
        """
        relief, canvas = self.relief, self.canvas
        scale = self.unit * self.px
        inside = relief.mask()
        rgb_hi = np.zeros(relief.z.shape + (3,), np.float32)
        region_hi = np.zeros(relief.z.shape, np.int16)
        gloss_hi = np.zeros(relief.z.shape, np.float32)
        soft_hi = np.zeros(relief.z.shape, np.float32)
        region_of = region_of or {}
        gloss = gloss or {}
        for name, pid in relief.parts.items():
            if not name:
                continue
            group = self.groups.get(pid, name)
            color = colors.get(name, colors.get(group, default))
            mask = relief.part == pid
            rgb_hi[mask] = to_rgb(color)
            region_name = region_of.get(name, region_of.get(group, "skin"))
            region_hi[mask] = canvas.region_id(region_name)
            gloss_hi[mask] = gloss.get(name, gloss.get(group, self.skin_gloss if region_name == "skin" else 0.0))
            soft_hi[mask] = 1.0 if region_name == "skin" else 0.0
        alpha = self._down(inside.astype(np.float32))
        normal_hi = relief.normals(blur=1.0 * self.ss)
        for name, amount in (flatten or {}).items():
            ids = [pid for part, pid in relief.parts.items() if part == name or self.groups.get(pid) == name]
            mask = np.isin(relief.part, ids)
            normal_hi[mask] = normal_hi[mask] * (1 - amount) + np.array([0, 0, 1], np.float32) * amount
        for name, amount in (folds or {}).items():
            if name in relief.parts and amount > 0:
                mask = relief.part == relief.parts[name]
                normal_hi[mask] += self._fold_field(amount)[mask]
        normal = self._down(normal_hi)
        rgb = self._down(rgb_hi) / np.maximum(alpha, 1e-3)[..., None]
        region = cv2.resize(region_hi, (canvas.W, canvas.H), interpolation=cv2.INTER_NEAREST)
        line_a = line_rgb = None
        if lines:
            group_ids = {}
            pairs = set()
            for pid, group in self.groups.items():
                group_ids.setdefault(group, []).append(pid)
            for group, ids in group_ids.items():
                if group.startswith(("hand_", "toes_")):        # fingers and toes always read as separate
                    pairs |= {(a, b) for a in ids for b in ids if a < b}
            smoothed, relief.z = relief.z, self._raw_z
            skin_groups = ("trunk", "arm_", "leg_", "hand_", "toes_")       # no crease lines on faces, hair, cloth
            no_crease = [pid for pid, group in self.groups.items() if not group.startswith(skin_groups)]
            family = np.arange(len(relief.parts) + 1)
            hair_ids = [pid for pid, group in self.groups.items() if group == "hair"]
            if hair_ids:
                family[hair_ids] = hair_ids[0]                # locks of hair are one mass: no ink between them
            soft_tissue = [relief.parts[n] for n in ("breast_l", "breast_r", "buttock_l", "buttock_r") if n in relief.parts]
            if soft_tissue and "torso" in relief.parts:
                family[soft_tissue] = relief.parts["torso"]   # breasts and buttocks grow out of the torso without a seam
            line_hi = relief.lines(scale, width=line_width * self.px, crease=crease, part_pairs=pairs,
                                   crease_mask=~np.isin(relief.part, no_crease), family=family[relief.part])
            relief.z = smoothed
            # A hem or neckline has no depth jump, so region changes inside the figure get their own line.
            change = np.zeros_like(inside)
            for axis in (0, 1):
                change |= (region_hi != np.roll(region_hi, 1, axis=axis)) & inside & np.roll(inside, 1, axis=axis)
            line_hi = np.maximum(line_hi, thicken(change.astype(np.float32), line_width * self.px) * 0.85)
            if self.hidden is not None and self.hidden.any():       # the figure in front draws that outline itself
                size = max(int(line_width * self.px), 1) * 2 + 1
                cover = cv2.dilate(self.hidden.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
                line_hi = line_hi * (1 - cover)
            line_a = self._down(line_hi)
            traced = trace_color(np.clip(rgb, 0, 1)) if line_color is None else np.broadcast_to(to_rgb(line_color), rgb.shape)
            line_rgb = np.ascontiguousarray(traced, dtype=np.float32)
        canvas.add_buffers(alpha, np.clip(rgb, 0, 1), normal=normal, region=region,
                           gloss=self._down(gloss_hi), cast=cast, line_a=line_a, line_rgb=line_rgb,
                           soft=self._down(soft_hi), occlusion=self._down(relief.occlusion(scale)) * occlusion)
        self.flow = None if relief.flow is None else self._down(relief.flow)
        if light is not None and self_shadow:
            shade = relief.cast_shadow(light.direction, reach=0.45 * scale, bias=0.03 * scale,
                                       softness=0.016 * scale)
            canvas.shadow = np.maximum(canvas.shadow, self._down(shade) * alpha * self_shadow)
        return self

    def _fold_field(self, amount):
        """Normal offsets for hanging cloth: long vertical ridges with slight drift."""
        scale = self.unit * self.px
        h, w = self.relief.z.shape
        rng = self.canvas.rng
        small = rng.standard_normal((max(int(h / (scale * 1.4)), 2), max(int(w / (scale * 0.13)), 2))).astype(np.float32)
        ridges = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
        ridges = cv2.GaussianBlur(ridges, (0, 0), scale * 0.035)
        gx = np.gradient(ridges, axis=1) * scale * 0.06 * amount
        out = np.zeros((h, w, 3), np.float32)
        out[..., 0] = np.clip(gx, -0.9, 0.9)
        return out

    def joint(self, name):
        """Design-unit (x, y) of a joint: anchor for 2D additions and for checking a pose."""
        return self.to_canvas(self.figure.P[name])
