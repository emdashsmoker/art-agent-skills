"""Head frame: where the head sits on the canvas and how its turn moves each point.

Every facial feature is laid out once on a frontal "face plane" (x from the face
centre line, y from crown 0.0 to chin 1.0, unit = head height). A head turn slides
those points sideways according to how far they stick out (nose most, cheeks least).
The head outline itself is blended between hand-drawn key shapes, front, three-quarter
and profile, the way a 2D animator keys a head turn. No 3D model is involved. Past the
three-quarter key the line down the middle of the face (brow, nose, lips, chin) is laid on
the same face plane and joins the outline, which is what makes a profile read.

Convention: the face turns toward +x. A negative yaw mirrors the finished drawing.
"""
from dataclasses import dataclass, replace

import numpy as np

from .. import geometry as geo
from .. import shading as sh

MAX_YAW = np.radians(25.0)   # yaw = 1.0 is this many degrees, the classic three-quarter view
FACE_DEPTH = 0.40            # how far the face plane sits in front of the neck axis
FACE_CURVE = 1.5             # how fast the face falls back toward the sides
DOME_FADE_Y = 0.36           # above this height the skull dome stops following the face
NECK_PIVOT_Y = 0.92          # head tilt rotates around this height on the axis

# Head outline key shapes: 22 matching points, clockwise from the crown.
# Index 11 is the chin, 1-10 the far side (top to bottom), 12-21 the near side (bottom to top).
FRONT_CONTOUR = [
    (0.0, 0.0), (0.20, 0.03), (0.32, 0.14), (0.355, 0.30), (0.36, 0.43), (0.355, 0.50),
    (0.345, 0.60), (0.31, 0.72), (0.25, 0.83), (0.155, 0.925), (0.06, 0.988),
    (0.0, 1.0),
    (-0.06, 0.988), (-0.155, 0.925), (-0.25, 0.83), (-0.31, 0.72), (-0.345, 0.60),
    (-0.355, 0.50), (-0.36, 0.43), (-0.355, 0.30), (-0.32, 0.14), (-0.20, 0.03),
]
TURNED_CONTOUR = [
    (-0.015, 0.0), (0.19, 0.03), (0.325, 0.15), (0.375, 0.30), (0.378, 0.43), (0.362, 0.505),
    (0.372, 0.60), (0.335, 0.72), (0.285, 0.83), (0.235, 0.925), (0.205, 0.985),
    (0.16, 1.0),
    (0.095, 0.99), (-0.04, 0.932), (-0.19, 0.845), (-0.235, 0.73), (-0.30, 0.63),
    (-0.345, 0.54), (-0.375, 0.44), (-0.388, 0.30), (-0.345, 0.14), (-0.22, 0.04),
]
# Profile key: the face side (+x) is forehead to chin; the near side runs up the jaw to its angle under
# the ear, along the base of the skull to the nape, then round the back of the skull to the crown.
PROFILE_CONTOUR = [
    (-0.02, 0.0), (0.17, 0.025), (0.29, 0.095), (0.355, 0.20), (0.385, 0.33), (0.375, 0.48),
    (0.365, 0.62), (0.365, 0.76), (0.36, 0.88), (0.415, 0.968), (0.38, 0.99),     # 9, 10 lie on the chin
    (0.29, 1.0),
    (0.16, 0.968), (0.05, 0.915), (-0.06, 0.848), (-0.18, 0.826), (-0.30, 0.80), (-0.42, 0.68),
    (-0.475, 0.53), (-0.485, 0.38), (-0.44, 0.20), (-0.28, 0.05),
]
NAPE_IDS = (14, 16)          # profile outline points from the jaw angle to the nape: the neck carries on there, no line
# Middle line of the face, crown side first: (y, how far it stands out of the face plane).
# Forehead leaning back, brow ridge, dip at the root of the nose, nose, lips, chin, then under the chin.
MIDLINE = [(0.24, 0.0), (0.33, -0.012), (0.40, 0.006), (0.445, 0.020), (0.50, 0.008), (0.58, 0.042), (0.65, 0.082),
           (0.695, 0.108), (0.715, 0.092), (0.735, 0.042), (0.765, 0.034), (0.795, 0.048), (0.822, 0.026),
           (0.845, 0.044), (0.88, 0.010), (0.935, 0.034), (0.968, 0.016), (0.99, -0.02)]
MIDLINE_CORNERS = (7, 9)     # nose tip and the turn under the nose stay sharp; the rest of the line is smoothed
MIDLINE_DEPTH = 0.15         # thickness of the band laid behind the middle line of the face
PROFILE_CURVE_GAIN = 1.2     # in profile the face wraps back faster toward the sides than a three-quarter key shows
JAW_FAR_IDS, JAW_NEAR_IDS = (8, 9, 10), (14, 13, 12)
JAW_SOFTEN = (0.022, 0.034, 0.026)   # outward push of the jaw points when jaw = 0
PROFILE_JAW_DROP = 1.4       # in profile a soft, broad jaw shows as a lower line under the face
FACE_WIDTH_FROM = (0.30, 0.50)   # head y over which face_width takes effect, from none (forehead) to full
CHEEK_IDS = ((6, 16), (7, 15))   # (far, near) outline points at the cheekbone and just under it
CHEEK_PUSH = (0.016, -0.012)     # outward push of those points at cheek = 1: the bone stands out, the hollow sinks
MIDLINE_NOSE = (5, 6, 7, 8, 9)   # middle line points that belong to the nose (scaled by spec.nose)


@dataclass
class PortraitSpec:
    # placement (fractions of the canvas)
    crown: tuple = (0.53, 0.115)     # top of the skull
    head_size: float = 0.50         # head height / canvas height
    yaw: float = -0.7               # -1..1; negative faces the viewer's left
    tilt: float = 0.0               # head roll in degrees
    # face
    jaw: float = 0.85               # 0 soft oval .. 1 sharp V-line
    eye_y: float = 0.545            # lower = younger, higher = more mature
    eye_spacing: float = 0.142      # eye centre distance from the face centre line
    eye_size: float = 1.18
    eye_open: float = 1.0           # <1 narrower, cooler eyes; >1 rounder, younger eyes
    eye_tilt: float = 7.0           # degrees, outer corner raised
    gaze: float = None              # iris shift -1..1; None looks at the viewer
    smile: float = 0.15
    lips: float = 0.85              # lip colour strength (0 = line only)
    turn_deg: float = None          # head turn in degrees (-90..90); overrides yaw (yaw 1.0 = 25 degrees)
    lashes: float = 1.0             # lash weight; about 0.35 for a man
    brow: float = 1.0               # brow thickness; 1.4 or more reads masculine
    # face shape (1.0 / 0.0 / "almond" keep the default face)
    face_width: float = 1.0         # 0.9 narrow, long-looking .. 1.1 broad, round-looking
    cheek: float = 0.0              # 0 smooth .. 1 defined cheekbones with a hollow under them
    nose: float = 1.0               # nose size: 0.8 small .. 1.3 large
    mouth: float = 1.0              # mouth width: 0.85 small .. 1.2 wide
    lip_full: float = 1.0           # lip thickness: 0.8 thin .. 1.4 full
    eye_shape: str = "almond"       # almond | round | droopy | sharp
    iris_size: float = 1.0          # 0.8 small irises, a sharper look .. 1.15 large irises, a softer look
    brow_tilt: float = 0.0          # degrees: + raises the inner ends (worried), - lowers them (stern)
    brow_raise: float = 0.0         # head units the brows sit higher
    mouth_open: float = 0.0         # 0 closed .. 1 open
    eyes_closed: str = None         # None | "up" (happy arcs) | "down" (calm, sleeping)
    expression: str = None          # None | smile | laugh | angry | sad | surprised (see EXPRESSIONS)
    # accessories
    glasses: str = None             # None | round | square
    glasses_color: str = "#2a2224"
    earrings: str = None            # None | stud | hoop | drop
    jewel: str = "#e8c46a"
    stubble: float = 0.0            # 0 clean shaven .. 1 heavy stubble on jaw and upper lip
    hat: str = None                 # None | beanie
    hat_color: str = "#2a2a30"
    # hair
    hair_style: str = "long"        # long | bob | short | wavy | ponytail | bun | two_block | slick
    bangs: str = "swept"            # swept | curtain | textured | none
    # outfit
    outfit: str = "turtleneck"      # turtleneck | blazer
    # palette
    skin: str = "#f9e2d2"
    hair: str = "#4a353b"
    eye: str = "#8a6a3c"
    lip: str = "#c4636a"
    cloth: str = "#d2a24c"
    cloth_second: str = "#2f3440"   # jacket colour when outfit = blazer
    seed: int = 7


# Overrides that turn the default face into a man's: a broader jaw, smaller and narrower eyes,
# straight heavy brows, light lashes, uncoloured lips and short hair.
MASCULINE = dict(jaw=0.40, eye_size=0.98, eye_open=0.80, eye_tilt=2.0, eye_y=0.55, lips=0.12, lashes=0.35,
                 brow=1.55, smile=0.05, hair_style="short", bangs="textured", lip="#b07a72")


# The masculine face values without its colour, so a palette (palette.look) decides the lips.
_MALE = {key: value for key, value in MASCULINE.items() if key != "lip"}
# Face presets: overrides for PortraitSpec. Merge with a palette and a hairstyle, later keys winning:
#     PortraitSpec(**{**FACES["cool"], **palette.look("tan", "black"), "hair_style": "ponytail"})
FACES = {
    "cool": dict(jaw=1.0, eye_shape="sharp", eye_size=1.08, eye_open=0.72, eye_tilt=13.0, iris_size=0.82, face_width=0.93,
                 mouth=0.85, smile=-0.1, lips=0.7, brow=0.85, brow_tilt=-7.0, brow_raise=-0.004, nose=0.95),
    "bright": dict(jaw=0.2, eye_shape="round", eye_size=1.32, eye_open=1.12, eye_tilt=2.0, iris_size=1.12, face_width=1.08,
                   mouth=1.2, smile=0.9, brow=0.95, brow_tilt=4.0, brow_raise=0.012, nose=0.85),
    "gentle": dict(jaw=0.55, eye_shape="droopy", eye_size=1.2, eye_open=0.92, eye_tilt=-5.0, iris_size=1.05, face_width=1.02,
                   smile=0.55, lip_full=1.15, brow=0.9, brow_tilt=9.0),
    "elegant": dict(jaw=0.95, eye_shape="almond", eye_size=1.06, eye_open=0.82, eye_tilt=8.0, eye_y=0.53, lashes=1.3,
                    face_width=0.92, cheek=1.0, nose=1.08, mouth=1.0, lip_full=1.45, lips=1.0, smile=0.05,
                    brow=0.75, brow_raise=0.006),
    "sporty": dict(jaw=0.5, eye_shape="almond", eye_size=1.12, eye_open=0.95, eye_tilt=3.0, face_width=1.05,
                   mouth=1.25, smile=0.75, lips=0.55, brow=1.5, brow_tilt=-5.0),
    "sharp_man": dict(_MALE, jaw=0.95, eye_shape="sharp", eye_open=0.62, eye_tilt=9.0, iris_size=0.85, face_width=0.94,
                      cheek=0.8, brow=1.6, brow_tilt=-8.0),
    "soft_man": dict(_MALE, jaw=0.3, eye_shape="round", eye_size=1.1, eye_open=0.95, eye_tilt=-1.0, iris_size=1.1,
                     face_width=1.03, smile=0.45, brow=1.25, brow_tilt=6.0),
    "rugged_man": dict(_MALE, jaw=0.05, eye_size=0.92, eye_open=0.7, eye_y=0.56, face_width=1.1, cheek=0.6, nose=1.3,
                       mouth=1.15, brow=2.0, brow_tilt=-4.0, brow_raise=-0.008, stubble=0.8),
}

# Expressions laid over any face: (field, operation, value); "add" adds, "mul" multiplies, "set" replaces.
EXPRESSIONS = {
    "smile": [("smile", "add", 0.45), ("eye_open", "mul", 0.88), ("brow_raise", "add", 0.004)],
    "laugh": [("smile", "add", 0.7), ("eyes_closed", "set", "up"), ("mouth_open", "set", 0.75), ("brow_raise", "add", 0.012),
              ("brow_tilt", "add", 4.0)],
    "angry": [("smile", "add", -0.6), ("eye_open", "mul", 0.72), ("brow_tilt", "add", -24.0), ("brow_raise", "add", -0.014),
              ("brow", "mul", 1.15), ("mouth", "mul", 0.9)],
    "sad": [("smile", "add", -0.5), ("eye_open", "mul", 0.82), ("brow_tilt", "add", 14.0), ("brow_raise", "add", 0.004),
            ("mouth", "mul", 0.85)],
    "surprised": [("smile", "set", 0.0), ("eye_open", "mul", 1.22), ("brow_raise", "add", 0.03), ("brow_tilt", "add", 5.0),
                  ("mouth_open", "set", 0.6), ("mouth", "mul", 0.6)],
}


def expressed(spec):
    """The spec with its expression laid over the face values (unchanged when expression is None)."""
    if not spec.expression:
        return spec
    if spec.expression not in EXPRESSIONS:
        raise ValueError(f"unknown expression: {spec.expression}")
    changes = {}
    for name, operation, value in EXPRESSIONS[spec.expression]:
        current = changes.get(name, getattr(spec, name))
        changes[name] = current + value if operation == "add" else current * value if operation == "mul" else value
    return replace(spec, expression=None, **changes)


class HeadFrame:
    """Maps head units to pixels and applies the turn and tilt of the head.

    turn: 0..1 from the front to the three-quarter key (25 degrees).
    profile: 0..1 from the three-quarter key to a full profile (90 degrees).
    """

    def __init__(self, spec, canvas_shape):
        height, width = canvas_shape
        self.scale = spec.head_size * height
        self.crown = np.array([spec.crown[0] * width, spec.crown[1] * height])
        if spec.turn_deg is None:            # yaw: -1..1 spans the three-quarter keys
            self.side = 1.0 if spec.yaw >= 0 else -1.0
            self.theta = min(abs(spec.yaw), 1.0) * MAX_YAW
        else:
            self.side = 1.0 if spec.turn_deg >= 0 else -1.0
            self.theta = np.radians(min(abs(spec.turn_deg), 90.0))
        self.turn = min(self.theta / MAX_YAW, 1.0)
        self.profile = float(np.clip((self.theta - MAX_YAW) / (np.pi / 2 - MAX_YAW), 0.0, 1.0))
        self.tilt = np.radians(spec.tilt)
        self.pivot = self.crown + np.array([0.0, NECK_PIVOT_Y]) * self.scale
        # face shape values the outline and the middle line of the face need
        self.face_width, self.cheek, self.nose = spec.face_width, spec.cheek, spec.nose

    def place(self, points, tilted=True):
        """Head-local units -> pixels (mirrors for a left-facing head, then tilts)."""
        pts = geo.as_points(points) * [self.side, 1.0]
        pixels = self.crown + pts * self.scale
        return geo.transform(pixels, angle=self.tilt, pivot=self.pivot) if tilted else pixels

    def face(self, points, lift=0.0):
        """Frontal face-plane units -> pixels. lift: how far the point sticks out (nose tip about 0.1)."""
        pts = geo.as_points(points)
        # The face juts forward but the crown does not, so the slide fades out toward the top.
        dome = sh.smoothstep(0.0, DOME_FADE_Y, pts[:, 1])
        curve = FACE_CURVE * (1.0 + PROFILE_CURVE_GAIN * self.profile)
        depth = (FACE_DEPTH - curve * pts[:, 0] ** 2) * dome + lift
        turned_x = pts[:, 0] * np.cos(self.theta) + depth * np.sin(self.theta)
        return self.place(np.stack([turned_x, pts[:, 1]], axis=1))

    def px(self, units):
        return units * self.scale


def head_contour(frame, jaw):
    """Head outline control points in head units for the current turn and jaw sharpness."""
    contour = geo.lerp(np.array(FRONT_CONTOUR), np.array(TURNED_CONTOUR), frame.turn)
    if frame.profile > 0:
        contour = geo.lerp(contour, np.array(PROFILE_CONTOUR), frame.profile)
    seen_wide = 1.0 - frame.profile                  # seen from the side the face width is no longer in view
    if frame.face_width != 1.0:
        # wider or narrower below the forehead; the dome of the skull keeps its size
        below_brow = sh.smoothstep(FACE_WIDTH_FROM[0], FACE_WIDTH_FROM[1], contour[:, 1])
        contour[:, 0] *= 1.0 + (frame.face_width - 1.0) * below_brow * seen_wide
    if frame.cheek != 0.0:
        for ids, push in zip(CHEEK_IDS, CHEEK_PUSH):
            contour[ids[0], 0] += push * frame.cheek * seen_wide
            contour[ids[1], 0] -= push * frame.cheek * seen_wide
    soften = 1.0 - jaw
    side_push = soften * seen_wide
    for index, push in zip(JAW_FAR_IDS, JAW_SOFTEN):
        contour[index, 0] += push * side_push
    for index, push in zip(JAW_NEAR_IDS, JAW_SOFTEN):
        contour[index, 0] -= push * side_push
        contour[index, 1] += push * soften * frame.profile * PROFILE_JAW_DROP
    return contour


def midline_shape(frame, smooth=True):
    """Closed curve from the middle line of the face back to the head's axis, in pixels.

    Joined to the head outline, it lets the brow, nose, lips and chin stand out once the head turns far.
    smooth=False keeps the straight segments: a large nose turns sharply under its tip, where the smoothed
    line can fold over itself and leave a pocket unfilled; filling both closes it.
    """
    line = [(y, lift * frame.nose if index in MIDLINE_NOSE else lift) for index, (y, lift) in enumerate(MIDLINE)]
    front = np.vstack([frame.face([(0.0, y)], lift=lift) for y, lift in line])
    if smooth:
        front = geo.smooth(front, corners=MIDLINE_CORNERS)   # soft lips and chin, a crisp nose tip
    # a band of fixed depth behind the line, so it always stays inside the head
    # the back edge keeps the default nose: a larger nose only moves the front, so the band never thins to a gap
    back = np.vstack([frame.face([(0.0, y)], lift=lift - MIDLINE_DEPTH) for y, lift in MIDLINE[::-1]])
    return np.vstack([front, back])


def light_on_canvas(light):
    """The 2D direction toward the light, as seen on the canvas."""
    flat = np.array(light[:2], dtype=np.float64)
    return flat / max(np.linalg.norm(flat), 1e-9)
