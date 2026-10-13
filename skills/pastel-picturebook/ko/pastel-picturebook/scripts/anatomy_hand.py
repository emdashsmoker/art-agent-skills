"""Hand anatomy: a jointed hand as relief parts.

Canonical hand: seen from the back, fingers pointing up, thumb on the left,
wrist centre at the origin. Lengths are shares of the hand length (wrist to
the tip of the middle finger = 1.0), so one scale factor sizes the whole hand.

A pose curls each finger by an angle per joint. Curl bends a finger away from
the viewer, so on the picture plane each bone simply shortens by the cosine of
its total curl: the standard foreshortening a figure artist estimates by eye.
"""
from dataclasses import dataclass, field

import numpy as np

import relief

# Finger: knuckle position, total length, bone shares (proximal, middle, distal), fan angle, width factor.
FINGERS = {
    "index":  {"knuckle": (-0.150, -0.485), "length": 0.420, "bones": (0.44, 0.29, 0.27), "fan": -7.0, "width": 1.00},
    "middle": {"knuckle": (-0.048, -0.515), "length": 0.470, "bones": (0.44, 0.30, 0.26), "fan": -1.0, "width": 1.04},
    "ring":   {"knuckle": (0.052, -0.495), "length": 0.435, "bones": (0.44, 0.30, 0.26), "fan": 5.0, "width": 0.98},
    "pinky":  {"knuckle": (0.140, -0.445), "length": 0.340, "bones": (0.42, 0.27, 0.31), "fan": 12.0, "width": 0.84},
}
# Half-widths along a finger: root, mid proximal, first joint, mid middle, second joint, mid distal, tip.
FINGER_PROFILE = np.array([0.047, 0.043, 0.0455, 0.040, 0.041, 0.037, 0.030])
# Thumb: base of the metacarpal, bone lengths, bone directions (degrees from straight up, negative = toward the thumb side).
THUMB = {"base": (-0.150, -0.085), "bones": (0.215, 0.165, 0.135), "angles": (-50.0, -34.0, -26.0),
         "profile": np.array([0.072, 0.060, 0.050, 0.046, 0.049, 0.042, 0.033])}
# Palm and wrist: centre line from the knuckle row down past the wrist, with widths on each side.
PALM_PATH = np.array([(-0.008, -0.335), (-0.004, -0.240), (0.0, -0.130), (0.0, 0.020), (0.0, 0.250), (0.0, 0.520)])
PALM_LEFT = np.array([0.200, 0.207, 0.203, 0.158, 0.160, 0.190])
PALM_RIGHT = np.array([0.205, 0.210, 0.196, 0.156, 0.165, 0.195])
# The back of the hand is a shallow dome; fingers are nearly round.
PALM_ROUNDNESS, FINGER_ROUNDNESS = 0.42, 0.85
# Index of the wrist in PALM_PATH; points after it are forearm.
WRIST_INDEX = 3
# How far finger roots are sunk into the palm so the two fuse without a gap.
ROOT_SINK = 0.035
# Half-width of the bar of flesh that runs along the knuckles.
KNUCKLE_BAR = 0.052
# The bar's ends are pulled in by this share so they do not bulge past the outer fingers.
BAR_END_INSET = 0.14
# How far (share of hand length) the thumb stands in front of the palm.
THUMB_LIFT = 0.03

# Poses: per finger (curl at knuckle, first joint, second joint) in degrees, plus fan spread and thumb swing.
# Palm side, in canonical coordinates (thumb on the left, fingers up, wrist at the origin).
# Pads: (centre, radius x, radius y, depth); a negative depth is the hollow of the palm.
PALM_PADS = [((-0.105, -0.13), 0.12, 0.17, 0.040), ((0.125, -0.15), 0.085, 0.20, 0.028),
             ((0.0, -0.27), 0.11, 0.10, -0.022)]
# Palm lines: heart, head, life, and two wrist creases.
PALM_LINES = [[(0.205, -0.395), (0.11, -0.405), (0.0, -0.425), (-0.085, -0.455)],
              [(-0.185, -0.33), (-0.08, -0.32), (0.04, -0.295), (0.14, -0.255)],
              [(-0.17, -0.33), (-0.12, -0.24), (-0.085, -0.12), (-0.065, 0.0)],
              [(-0.14, 0.035), (0.0, 0.045), (0.14, 0.035)],
              [(-0.12, 0.075), (0.0, 0.085), (0.12, 0.075)]]

POSES = {
    "open":    {"index": (4, 6, 4), "middle": (3, 5, 4), "ring": (5, 7, 5), "pinky": (8, 10, 6), "spread": 1.25, "thumb": 0.0},
    "relaxed": {"index": (8, 16, 12), "middle": (12, 22, 15), "ring": (15, 25, 16), "pinky": (17, 26, 16), "spread": 0.45, "thumb": 16.0},
    "victory": {"index": (2, 4, 3), "middle": (2, 4, 3), "ring": (72, 95, 60), "pinky": (72, 95, 60), "spread": 1.9, "thumb": 44.0},
    # A V sign held up by the face: the two fingers spread wide enough to read at figure scale.
    "peace":   {"index": (2, 3, 2), "middle": (2, 3, 2), "ring": (78, 100, 65), "pinky": (78, 100, 65), "spread": 3.6, "thumb": 48.0},
    "point":   {"index": (2, 4, 3), "middle": (72, 95, 60), "ring": (72, 95, 60), "pinky": (72, 95, 60), "spread": 0.6, "thumb": 40.0},
    # Fingers wrapped round something held (a cup, a book's edge): curled at every joint but not folded away.
    "grip":    {"index": (48, 55, 35), "middle": (50, 58, 35), "ring": (53, 60, 35), "pinky": (56, 62, 35), "spread": 0.3, "thumb": 30.0},
    "fist":    {"index": (85, 100, 70), "middle": (85, 100, 70), "ring": (85, 100, 70), "pinky": (85, 100, 70), "spread": 0.3, "thumb": 45.0},
}
# A hand tucked out of sight (under the other arm when the arms are folded) is built as a fist and hidden.
HIDDEN_POSES = {"tucked": "fist"}
# A finger curled past this at the knuckle is folded into the palm: only its first bone shows.
FOLDED_CURL = 60.0


@dataclass
class Hand:
    """Everything a painter needs to draw one hand, in pixels."""
    whole: relief.Part                              # all parts fused
    fingers: dict = field(default_factory=dict)     # name -> Part (includes "thumb")
    palm: relief.Part = None
    knuckles: relief.Part = None
    joints: dict = field(default_factory=dict)      # name -> list of joint points (root .. tip)
    widths: dict = field(default_factory=dict)      # name -> half-width (px) at each joint
    folded: set = field(default_factory=set)        # fingers folded into the palm
    hidden: bool = False                            # tucked out of sight: built, but with empty masks
    scale: float = 1.0
    view: str = "back"                              # "back" or "palm"
    frame: object = None                            # canonical hand coordinates -> pixels


def place(points, wrist, scale, angle_deg, mirror):
    """Canonical hand coordinates -> pixels."""
    pts = np.atleast_2d(np.asarray(points, np.float64)).copy()
    if mirror:
        pts[:, 0] *= -1
    turn = np.deg2rad(angle_deg)
    rotated = np.column_stack([pts[:, 0] * np.cos(turn) - pts[:, 1] * np.sin(turn),
                               pts[:, 0] * np.sin(turn) + pts[:, 1] * np.cos(turn)])
    return rotated * scale + np.asarray(wrist, np.float64)


def finger_joints(spec, curls, spread):
    """Joint positions of one finger in canonical coordinates: sunk root, knuckle, joint, joint, tip."""
    direction = np.deg2rad(spec["fan"] * spread)
    heading = np.array([np.sin(direction), -np.cos(direction)])
    knuckle = np.array(spec["knuckle"])
    points = [knuckle - heading * ROOT_SINK, knuckle]
    total = 0.0
    for share, curl in zip(spec["bones"], curls):
        total += curl
        points.append(points[-1] + heading * spec["length"] * share * np.cos(np.deg2rad(min(total, 89.0))))
        if curls[0] > FOLDED_CURL:
            break
    return np.array(points)


def thumb_joints(swing):
    """Thumb joints; `swing` (degrees) folds the thumb in toward the palm."""
    points = [np.array(THUMB["base"])]
    for length, angle in zip(THUMB["bones"], THUMB["angles"]):
        direction = np.deg2rad(angle + swing)
        points.append(points[-1] + length * np.array([np.sin(direction), -np.cos(direction)]))
    return np.array(points)


def profile_at_joints(profile, joint_count):
    """Half-widths at each joint from the 7-point finger profile."""
    full = [profile[0], profile[0], profile[2], profile[4], profile[6]]
    return np.array(full[:joint_count])


def build_hand(size, wrist, scale, angle_deg=0.0, pose="open", mirror=False, forearm=True, view="back", width=1.0):
    """Construct one hand. `scale` = hand length in pixels; `angle_deg` rotates it (0 = fingers up).

    `forearm=False` stops the hand at the wrist, for attaching it to an arm built elsewhere.
    `view="palm"` shows the palm: the same skeleton seen from the other side, so the thumb
    changes side, and the palm's own soft pads replace the knuckles.
    `width` scales every half-width (a man's hand: thicker fingers, broader palm, about 1.15).
    """
    hidden = pose in HIDDEN_POSES
    setup = POSES[HIDDEN_POSES.get(pose, pose)]
    flip = mirror != (view == "palm")
    keep = len(PALM_PATH) if forearm else WRIST_INDEX + 1
    palm_path = place(PALM_PATH[:keep], wrist, scale, angle_deg, flip)
    left, right = (PALM_RIGHT, PALM_LEFT) if flip else (PALM_LEFT, PALM_RIGHT)
    palm = relief.tube(size, palm_path, left[:keep] * scale * width, right[:keep] * scale * width, PALM_ROUNDNESS, cap_end=not forearm)
    hand = Hand(whole=palm, palm=palm, scale=scale, view=view)
    hand.frame = lambda points: place(points, wrist, scale, angle_deg, flip)
    for name, spec in FINGERS.items():
        joints = finger_joints(spec, setup[name], setup["spread"])
        widths = profile_at_joints(FINGER_PROFILE * spec["width"], len(joints)) * scale * width
        if setup[name][0] > FOLDED_CURL:
            hand.folded.add(name)
        path = place(joints, wrist, scale, angle_deg, flip)
        hand.fingers[name] = relief.tube(size, path, widths, roundness=FINGER_ROUNDNESS)
        hand.joints[name], hand.widths[name] = path, widths
    thumb = place(thumb_joints(setup["thumb"]), wrist, scale, angle_deg, flip)
    thumb_widths = np.array([THUMB["profile"][0], THUMB["profile"][2], THUMB["profile"][4], THUMB["profile"][6]]) * scale * width
    hand.fingers["thumb"] = relief.tube(size, thumb, thumb_widths, roundness=FINGER_ROUNDNESS)
    hand.joints["thumb"], hand.widths["thumb"] = thumb, thumb_widths
    # Why a bar along the knuckles: it closes the gaps between finger roots with
    # the rounded webs a real hand has, instead of the palm's straight top edge.
    order = ["pinky", "ring", "middle", "index"] if not flip else ["index", "middle", "ring", "pinky"]
    ridge = np.array([hand.joints[name][1] for name in order])
    middle = ridge.mean(axis=0)
    ridge[[0, -1]] += (middle - ridge[[0, -1]]) * BAR_END_INSET
    hand.knuckles = relief.tube(size, ridge, KNUCKLE_BAR * scale * width, roundness=PALM_ROUNDNESS)
    behind = relief.union([palm, hand.knuckles] + [part for name, part in hand.fingers.items() if name != "thumb"])
    # The thumb crosses in front of the palm, so it is laid over the rest and raised a little.
    hand.whole = relief.place_over(behind, hand.fingers["thumb"], THUMB_LIFT * scale)
    hand.hidden = hidden
    if hidden:
        for part in [hand.whole, hand.palm, hand.knuckles] + list(hand.fingers.values()):
            part.mask = np.zeros_like(part.mask)
    return hand
