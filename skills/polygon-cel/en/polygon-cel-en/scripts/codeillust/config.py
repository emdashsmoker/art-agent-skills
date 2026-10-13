"""Proportion canon and render defaults.

All anatomy values are in head-height units (H). Head-local space: origin at
the top of the skull, y down, z toward the viewer. Body-local space: origin at
the neck base (suprasternal notch), same axes. Values follow the common
anime adult-female canon (about 7 heads tall, eyes near mid-face) and were
tuned by rendering and inspecting, so change them in small steps.
"""

# ---------------------------------------------------------------- head canon
CRANIUM_Y = 0.40          # sphere center of the skull
CRANIUM_R = 0.39
FACE_RF = 0.37            # radius of the face cylinder carrying features
NECK_PIVOT = (0.0, 0.92, -0.05)   # head rotation pivot
NECK_BASE_Y = 1.30        # head-local y of the body origin

EYE_Y = 0.600
EYE_X = 0.168
EYE_W = 0.180
BROW_RISE = 0.118         # brow height above eye center (H)
NOSE_Y = 0.748
MOUTH_Y = 0.860
MOUTH_W = 0.085

# jaw control points per face shape: (x, y, z) for the image-right half
JAW = {
    "oval":  [(0.370, 0.44, 0.04), (0.364, 0.560, 0.08), (0.352, 0.640, 0.12), (0.288, 0.800, 0.13),
              (0.158, 0.935, 0.22), (0.045, 0.995, 0.27)],
    "round": [(0.372, 0.44, 0.04), (0.370, 0.560, 0.08), (0.362, 0.650, 0.12), (0.315, 0.800, 0.13),
              (0.190, 0.935, 0.22), (0.060, 0.985, 0.27)],
    "sharp": [(0.368, 0.44, 0.04), (0.360, 0.555, 0.08), (0.345, 0.630, 0.12), (0.270, 0.795, 0.14),
              (0.135, 0.940, 0.23), (0.030, 1.000, 0.28)],
    "square": [(0.374, 0.44, 0.04), (0.374, 0.560, 0.08), (0.370, 0.665, 0.12), (0.325, 0.815, 0.14),
               (0.200, 0.945, 0.22), (0.075, 0.990, 0.27)],
}
JAW_TOP = 0.44            # face length scales the jaw below this line

# ---------------------------------------------------------------- body canon
SHOULDER_HALF = 0.80      # acromion half width
NECK_HALF = 0.165
CHEST_Y = 0.70            # body-local y of bust line
WAIST_Y = 1.45
HIP_Y = 2.10
CROTCH_Y = 2.42
KNEE_Y = 3.90
ANKLE_Y = 5.35
FOOT_Y = 5.70

# ---------------------------------------------------------------- framing
# head height as a fraction of canvas height, head-top y and figure center x
FRAMING = {
    "closeup": {"head_frac": 0.520, "top": 0.110, "cx": 0.500},
    "bust":  {"head_frac": 0.335, "top": 0.090, "cx": 0.500},
    "waist": {"head_frac": 0.235, "top": 0.055, "cx": 0.500},
    "full":  {"head_frac": 0.130, "top": 0.035, "cx": 0.500},
    # establishing shot: a small whole figure standing on the lower part of a wide scene
    "wide":  {"head_frac": 0.058, "top": 0.430, "cx": 0.500},
}
WHOLE_FIGURE = ("full", "wide")   # framings that show the feet and stand the figure on the ground
LEAD_ROOM = 0.035         # figure shifts away from the facing direction
FIGURE_HEIGHT = 6.95      # standing figure, head top to sole, in head heights
SIT_HEIGHT = 5.85         # seated figure, head top to sole
LIE_LENGTH = 0.86         # a lying figure spans this share of the canvas width
LIE_ORIENT = -90.0        # lying figures are turned so the head points to screen left

# ---------------------------------------------------------------- rendering
LINE_FACE = 0.0062        # silhouette line width as fraction of H
LINE_HAIR = 0.0058
LINE_BODY = 0.0060
LINE_DETAIL = 0.0040

DEFAULT_SKIN = "#F9E2D2"
DEFAULT_CANVAS = (1024, 1280)

# ---------------------------------------------------------------- group pictures (two or more figures)
# distance between neighbouring body centers in head heights of the tallest figure, per contact
PAIR_SPACING = {"none": 1.95, "hand_hold": 2.05, "shoulder_arm": 1.15}
PAIR_SIDE_SPACING = 1.85  # two profiles facing each other
PAIR_MALE_EXTRA = 0.25    # a male frame is wider at the shoulders; each one adds this much
PAIR_YAW = 15.0           # default head turn toward the partner (toward the group center)
GROUP_MARGIN = 1.35       # head heights kept beside the outer figures' centers (shoulders, arms, air)
ROW_SCALE = 0.93          # each row further back is drawn this much smaller
ROW_RISE = 0.55           # and stands this many head heights higher on the canvas (farther ground)
