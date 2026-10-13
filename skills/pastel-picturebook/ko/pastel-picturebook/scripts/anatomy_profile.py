"""Profile figure: a woman or a man seen from the side, facing the screen's right, standing or seated.

Everything is laid out in head units (1.0 = half the face width) with the
origin at the eye, x forward (toward the face), y down; `pose.mirror` flips
the finished picture to face left.

The profile is where a figure's appeal lives: the S of the back (shoulder
blades out, lumbar curve in, buttocks out), the line of the chest and breast,
the long diagonal of the thigh. These come from a torso tube whose front and
back depths vary along its length, plus two soft solids (breast, buttock)
whose outlines are drawn directly.

A man uses the same construction with his own tables (MALE): a firmer brow
and nose, a squarer jaw, the Adam's apple, a deeper chest with a flat chest
muscle in place of the breast, a flatter belly and smaller buttocks.
Seated (`profile_pose.seat`), the thighs run forward onto a stool and flatten
where they rest on it.
"""
import cv2
import numpy as np

import accessories
import kit
import relief
import subject_figure as sf
from anatomy_hand import build_hand
from figure import BUN_SPLIT, TIED_STYLES, TIP_SPLIT_START, Figure, add_wave, section_outline
from painter import Scene, form_shadow, paint_background, paint_hair_section, run_hook
from raster import blur, ellipse, fill, mix, over, resample, rgb, screen, shift, smooth, stroke, taper

# --------------------------------------------------------------------- head
# A small, slightly upturned nose, soft lips and a defined chin; the jaw runs straight to a clear angle.
FACE = [(0.66, -1.10), (0.80, -0.75), (0.86, -0.40), (0.79, -0.14), (0.89, 0.12), (1.00, 0.33), (1.09, 0.45),
        (1.07, 0.53), (0.90, 0.58), (0.92, 0.68), (0.94, 0.745), (0.88, 0.795), (0.905, 0.865), (0.87, 0.945),
        (0.81, 1.00), (0.85, 1.10), (0.78, 1.21), (0.57, 1.27), (0.06, 1.15), (-0.40, 0.92), (-0.55, 0.55),
        (-0.82, 0.40), (-1.28, 0.15), (-1.52, -0.35), (-1.46, -1.00), (-1.04, -1.46), (-0.35, -1.65), (0.25, -1.55)]
# The eye seen from the side: an open "<" set back from the bridge, as tall as the front view's eye.
EYE_UPPER = [(0.34, 0.03), (0.40, -0.07), (0.49, -0.135), (0.58, -0.135), (0.645, -0.075)]
EYE_LOWER = [(0.645, -0.075), (0.655, 0.0), (0.62, 0.06), (0.52, 0.075), (0.42, 0.06)]
IRIS = ((0.585, -0.025), 0.058, 0.10)
LASH_FLICK = [(0.63, -0.10), (0.71, -0.17), (0.78, -0.20)]
# Closed eye (a wink or a laugh): one arc across the opening.
CLOSED_ARC = [(0.36, 0.02), (0.50, -0.04), (0.64, 0.0)]
BROW = [(0.32, -0.42), (0.56, -0.49), (0.80, -0.43)]
UPPER_LIP = [(0.90, 0.655), (0.93, 0.715), (0.945, 0.75), (0.88, 0.795), (0.815, 0.79), (0.825, 0.71)]
LOWER_LIP = [(0.88, 0.795), (0.91, 0.86), (0.875, 0.935), (0.81, 0.93), (0.80, 0.84)]
NOSTRIL = [(0.95, 0.53), (1.00, 0.555), (1.04, 0.54)]
EAR = ((-0.50, 0.17), 0.15, 0.29)
CHEEK = ((0.28, 0.55), 0.30, 0.16)
# Hair runs root to tip between two guides: along the hairline and behind the ear, and over the skull.
HAIR_INNER = [(0.66, -1.10), (0.42, -0.94), (0.18, -0.66), (0.03, -0.34), (-0.12, -0.08), (-0.40, 0.0), (-0.74, 0.02), (-0.80, 0.56),
              (-0.92, 1.20), (-1.12, 2.20)]
HAIR_OUTER = [(0.66, -1.10), (0.62, -1.42), (0.20, -1.82), (-0.50, -1.95), (-1.25, -1.74), (-1.78, -1.10),
              (-1.92, -0.20), (-1.86, 0.80), (-1.90, 1.90)]
HAIR_GUIDE_SAMPLES = 72
# A bun behind the crown in profile: inner and outer guides from where it leaves the head to its top.
PROFILE_BUN = ([(-1.05, -1.25), (-1.55, -1.10), (-1.95, -1.45), (-1.85, -1.95), (-1.45, -2.10)],
               [(-1.05, -1.25), (-0.95, -1.70), (-1.10, -2.05), (-1.30, -2.15), (-1.45, -2.10)])


def profile_tail(length):
    """A ponytail in profile: tied high behind the crown, falling down the back (inner and outer guides)."""
    return ([(-1.10, -1.30), (-1.55, -1.05), (-1.80, 0.20), (-1.78, 0.6 * length), (-1.60, length)],
            [(-1.00, -1.60), (-1.80, -1.30), (-2.15, 0.10), (-2.12, 0.6 * length + 0.1), (-1.85, length + 0.1)])
# Fringe in profile (inner guide over the forehead, outer guide arching in front of it), root to tip:
# down to the brow for long hair, half way down the forehead for short cuts and tied-back hair.
PROFILE_BANGS_LONG = ([(0.15, -1.55), (0.45, -1.25), (0.60, -0.95), (0.68, -0.70), (0.74, -0.52)],
                      [(0.20, -1.70), (0.66, -1.46), (0.92, -1.14), (0.97, -0.82), (0.90, -0.52)])
PROFILE_BANGS_SHORT = ([(0.15, -1.60), (0.45, -1.32), (0.62, -1.06), (0.70, -0.88), (0.75, -0.74)],
                       [(0.20, -1.76), (0.64, -1.54), (0.86, -1.24), (0.88, -0.94), (0.82, -0.74)])
BANG_LOCKS, BANG_SPLIT = 3, 0.78
# Share of frontal light below which the profile face is in shadow.
PROFILE_FACE_LEVEL = 0.05
# Width (head units) of the rounded rim of the profile face.
PROFILE_FACE_RIM = 0.22

# --------------------------------------------------------------------- body
# Neck: from under the skull to its base, half-widths.
# The neck leans forward: its base sits behind the jaw, its top under the skull.
# Its back widens toward the base: the trapezius runs from under the skull down to the shoulder.
NECK = ([(-0.30, 0.70), (-0.45, 1.50), (-0.62, 2.35)], [0.48, 0.66, 1.00], [0.48, 0.46, 0.55])
NECK_BASE = np.array([-0.50, 2.25])
# Torso centre line and its depth in front of and behind it, from the neck base to the crotch.
TORSO_Y = np.array([2.20, 2.70, 3.40, 4.30, 5.10, 5.70, 6.40, 7.10, 7.80, 8.40, 8.95])
TORSO_X = np.array([-0.58, -0.58, -0.56, -0.52, -0.46, -0.40, -0.38, -0.46, -0.54, -0.55, -0.50])
TORSO_FRONT = np.array([0.62, 1.02, 1.16, 1.20, 1.08, 0.96, 1.08, 1.06, 0.97, 0.85, 0.65])
TORSO_BACK = np.array([0.95, 1.08, 1.14, 1.02, 0.85, 0.70, 0.78, 1.06, 1.24, 1.20, 0.78])
# Which body-shape multiplier acts on each torso level: (front, back).
FRONT_SHAPE = ["", "", "", "", "waist", "waist", "waist", "hips", "hips", "hips", ""]
BACK_SHAPE = ["", "", "", "", "waist", "waist", "waist", "hips", "hips", "hips", "hips"]
TORSO_ROUNDNESS = 0.55
# How the torso's centre line moves forward (+) at each level when the back arches (pose "arch" = 1).
ARCH_SHIFT = np.array([0.0, 0.04, 0.10, 0.14, 0.18, 0.20, 0.14, 0.02, -0.08, -0.10, -0.08])
# Breast and buttock outlines as (distance out from the torso's surface, level); shape multipliers
# scale the distance out.
BREAST = [(-0.05, 3.30), (0.22, 3.74), (0.48, 4.12), (0.64, 4.42), (0.62, 4.63), (0.46, 4.82), (0.20, 4.92), (-0.08, 4.86)]
BUTTOCK = [(-0.05, 6.80), (0.14, 7.30), (0.22, 7.84), (0.20, 8.34), (0.08, 8.78), (-0.20, 9.00), (-0.55, 8.96)]
SOFT_DEPTH = 0.42
# Joints.
SHOULDER = np.array([-0.62, 3.05])
HIP = np.array([-0.52, 7.95])
UPPER_ARM, FOREARM, HAND = 3.35, 2.80, 1.80
THIGH, SHIN = 5.45, 4.70
UPPER_ARM_WIDTHS = np.array([0.56, 0.52, 0.46, 0.41, 0.37])
FOREARM_WIDTHS = np.array([0.38, 0.42, 0.37, 0.31, 0.28])
# Leg depths along the bone: (back, front). The thigh is fuller behind (hamstring), the shin behind (calf).
THIGH_BACK = np.array([1.10, 1.02, 0.88, 0.70, 0.54])
THIGH_FRONT = np.array([0.95, 0.94, 0.84, 0.67, 0.52])
SHIN_BACK = np.array([0.52, 0.68, 0.58, 0.40, 0.31])
SHIN_FRONT = np.array([0.48, 0.44, 0.40, 0.35, 0.30])
# Foot in profile: centre line from heel to toe (offsets from the ankle) and half-heights.
FOOT_PATH = [(-0.12, 0.28), (0.25, 0.36), (0.72, 0.43), (1.05, 0.48)]
FOOT_WIDTHS = np.array([0.26, 0.25, 0.15, 0.10])
FOCUS = {"background": 0.0, "body": 0.55, "cloth": 0.45, "hair": 0.4, "face": 0.9, "far": 0.4}
DEFAULT_POSE = {"lean": 0.0, "arch": 0.0, "arm": {"upper": -6.0, "fore": 8.0}, "leg_near": {"thigh": 2.0, "shin": -3.0},
                "leg_far": {"thigh": 14.0, "shin": -6.0}, "hand": "relaxed"}

FEMALE = {
    "FACE": FACE, "EYE_UPPER": EYE_UPPER, "EYE_LOWER": EYE_LOWER, "IRIS": IRIS, "LASH_FLICK": LASH_FLICK, "BROW": BROW,
    "BROW_WIDTH": 0.045, "LID_WIDTH": 0.04, "UPPER_LIP": UPPER_LIP, "LOWER_LIP": LOWER_LIP, "LIP_SHINE": (0.865, 0.865),
    "NOSTRIL": NOSTRIL, "EAR": EAR, "CHEEK": CHEEK, "HAIR_INNER": HAIR_INNER, "HAIR_OUTER": HAIR_OUTER, "SHORT_HAIR": False,
    "CLOSED_ARC": CLOSED_ARC,
    "NECK": NECK, "NECK_BASE": NECK_BASE, "ADAMS_APPLE": None,
    "TORSO_X": TORSO_X, "TORSO_FRONT": TORSO_FRONT, "TORSO_BACK": TORSO_BACK, "BREAST": BREAST, "BUTTOCK": BUTTOCK,
    "SOFT_DEPTH": SOFT_DEPTH, "SHOULDER": SHOULDER, "HIP": HIP,
    "UPPER_ARM": UPPER_ARM, "FOREARM": FOREARM, "HAND": HAND, "THIGH": THIGH, "SHIN": SHIN,
    "UPPER_ARM_WIDTHS": UPPER_ARM_WIDTHS, "FOREARM_WIDTHS": FOREARM_WIDTHS, "THIGH_BACK": THIGH_BACK, "THIGH_FRONT": THIGH_FRONT,
    "SHIN_BACK": SHIN_BACK, "SHIN_FRONT": SHIN_FRONT, "FOOT_SCALE": 1.0, "HAND_WIDTH": 1.0, "NIPPLE": (0.07, 0.12),
}
# A man in profile: a brow ridge over a deeper-set eye, a longer straight nose, thinner lips, a chin that
# stands forward and a jaw that runs level to a marked angle. The short cut ends above the ear and at the nape.
MALE = {
    **FEMALE,
    "FACE": [(0.66, -1.10), (0.80, -0.78), (0.86, -0.46), (0.89, -0.30), (0.80, -0.12), (0.92, 0.12), (1.04, 0.34), (1.12, 0.47),
             (1.09, 0.555), (0.93, 0.60), (0.935, 0.69), (0.945, 0.75), (0.89, 0.79), (0.905, 0.85), (0.875, 0.915), (0.83, 0.975),
             (0.89, 1.10), (0.88, 1.24), (0.74, 1.33), (0.20, 1.27), (-0.42, 1.06), (-0.55, 0.62),
             (-0.82, 0.40), (-1.28, 0.15), (-1.52, -0.35), (-1.46, -1.00), (-1.04, -1.46), (-0.35, -1.65), (0.25, -1.55)],
    "EYE_UPPER": [(0.38, 0.03), (0.44, -0.04), (0.52, -0.09), (0.60, -0.09), (0.66, -0.04)],
    "EYE_LOWER": [(0.66, -0.04), (0.665, 0.01), (0.63, 0.055), (0.53, 0.065), (0.44, 0.05)],
    "IRIS": ((0.60, -0.015), 0.05, 0.08), "LASH_FLICK": None, "CLOSED_ARC": [(0.40, 0.03), (0.52, -0.02), (0.65, 0.01)],
    "BROW": [(0.30, -0.33), (0.58, -0.37), (0.84, -0.32)], "BROW_WIDTH": 0.065, "LID_WIDTH": 0.026,
    "UPPER_LIP": [(0.92, 0.68), (0.94, 0.73), (0.945, 0.75), (0.89, 0.79), (0.84, 0.785), (0.85, 0.72)],
    "LOWER_LIP": [(0.885, 0.79), (0.905, 0.84), (0.88, 0.90), (0.825, 0.895), (0.815, 0.83)], "LIP_SHINE": (0.865, 0.85),
    "NOSTRIL": [(0.98, 0.565), (1.03, 0.585), (1.07, 0.57)],
    "EAR": ((-0.50, 0.17), 0.16, 0.31), "CHEEK": ((0.28, 0.55), 0.26, 0.14),
    "HAIR_INNER": [(0.62, -1.12), (0.40, -0.96), (0.18, -0.70), (0.05, -0.42), (-0.08, -0.10), (-0.36, -0.06), (-0.72, 0.02),
                   (-0.92, 0.40)],
    "HAIR_OUTER": [(0.62, -1.12), (0.68, -1.42), (0.30, -1.84), (-0.45, -1.98), (-1.20, -1.80), (-1.64, -1.22), (-1.68, -0.40),
                   (-1.46, 0.16), (-1.10, 0.48)],
    "SHORT_HAIR": True,
    # Thicker neck; its front carries the Adam's apple: (centre, radii) in body coordinates.
    "NECK": ([(-0.30, 0.70), (-0.45, 1.50), (-0.66, 2.35)], [0.56, 0.78, 1.14], [0.60, 0.56, 0.64]),
    "ADAMS_APPLE": ((0.12, 1.12), 0.12, 0.17),
    "TORSO_X": np.array([-0.62, -0.62, -0.60, -0.56, -0.50, -0.46, -0.44, -0.48, -0.52, -0.53, -0.50]),
    "TORSO_FRONT": np.array([0.70, 1.14, 1.32, 1.30, 1.12, 0.98, 0.98, 0.98, 0.92, 0.84, 0.66]),
    "TORSO_BACK": np.array([1.02, 1.18, 1.22, 1.10, 0.94, 0.82, 0.80, 0.92, 1.06, 1.06, 0.74]),
    # Chest muscle: a low shelf ending in a crisp lower edge; the buttock is small and high.
    "BREAST": [(-0.05, 2.80), (0.06, 3.20), (0.13, 3.62), (0.15, 3.92), (0.09, 4.14), (-0.06, 4.20)],
    "BUTTOCK": [(-0.05, 7.00), (0.08, 7.45), (0.12, 7.90), (0.10, 8.35), (0.02, 8.75), (-0.20, 8.95), (-0.50, 8.92)],
    "SOFT_DEPTH": 0.30, "SHOULDER": np.array([-0.66, 3.05]),
    "UPPER_ARM": 3.45, "FOREARM": 2.90, "HAND": 1.95, "THIGH": 5.55, "SHIN": 4.85,
    "UPPER_ARM_WIDTHS": np.array([0.68, 0.64, 0.55, 0.48, 0.42]),
    "FOREARM_WIDTHS": np.array([0.45, 0.51, 0.45, 0.37, 0.31]),
    "THIGH_BACK": np.array([1.08, 1.02, 0.90, 0.72, 0.56]), "THIGH_FRONT": np.array([1.00, 1.00, 0.90, 0.72, 0.56]),
    "SHIN_BACK": np.array([0.56, 0.74, 0.62, 0.42, 0.33]), "SHIN_FRONT": np.array([0.52, 0.48, 0.44, 0.38, 0.33]),
    "FOOT_SCALE": 1.12, "HAND_WIDTH": 1.15, "NIPPLE": (0.045, 0.045),
}
BUILDS = {"female": FEMALE, "male": MALE}
# Seated: the stool's top sits this share of the thigh's back depth under the hip joint; it reaches this
# share of the thigh forward; its board is this thick (head units).
SEAT_DROP, SEAT_REACH, SEAT_BOARD, SEAT_LEG = 0.92, 0.62, 0.40, 0.26
# Past STRIDE_FROM degrees of forward thigh swing the buttock flattens, by up to STRIDE_FLATTEN at STRIDE_FROM + STRIDE_SPAN.
STRIDE_FROM, STRIDE_SPAN, STRIDE_FLATTEN = 30.0, 60.0, 0.55
# Far shoulder offset from the near one (body coordinates, head units).
FAR_SHOULDER_SHIFT = (-0.10, -0.05)
# The far side of the body is in shadow: this much shadow tone over its skin and clothes.
FAR_SHADE = 0.30


def heading(angle_deg):
    """Bone direction at `angle_deg` from straight down; positive swings forward (toward the face)."""
    turn = np.deg2rad(angle_deg)
    return np.array([np.sin(turn), np.cos(turn)])


def build(spec):
    """Lay out the profile figure in pixels."""
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    pose, setup = spec["pose"], spec["figure"]
    table = BUILDS[spec.get("sex", "female")]
    unit = pose["head_unit"] * width
    origin = np.array([pose["head_center"][0] * width, pose["head_center"][1] * height])
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=unit, light=light / np.linalg.norm(light), seed=spec["seed"], spec=spec)
    roll = np.deg2rad(pose.get("roll_deg", 0.0))
    turn = np.array([[np.cos(roll), -np.sin(roll)], [np.sin(roll), np.cos(roll)]])

    def head(points):
        return np.atleast_2d(np.asarray(points, np.float64)) @ turn.T * unit + origin

    scale = setup["body_scale"]
    base_px = head(table["NECK_BASE"])[0]
    lean = np.deg2rad(setup.get("profile_pose", {}).get("lean", 0.0))
    tilt = np.array([[np.cos(lean), -np.sin(lean)], [np.sin(lean), np.cos(lean)]])

    def body(points):
        return (np.atleast_2d(np.asarray(points, np.float64)) - table["NECK_BASE"]) @ tilt.T * unit * scale + base_px

    fig.extra["profile"] = {"head": head, "body": body, "scale": scale, "table": table}
    lay_out_head(fig, spec, table, head)

    def unbody(pixels):
        """Pixels -> body coordinates (head units, x forward, y down): the inverse of `body`."""
        return ((np.asarray(pixels, np.float64) - base_px) / (unit * scale)) @ tilt + table["NECK_BASE"]

    fig.extra["layout"] = lay_out_body(fig, aim_arm(spec, setup, head, unbody, table), body, table)
    return fig


def lay_out_head(fig, spec, table, head):
    """Profile face, eye, lips, brow and hair guides in pixels; `head` maps head units (x toward the face) to pixels."""
    unit = fig.unit
    fig.shapes["face"] = head(smooth(table["FACE"], samples=6, closed=True))
    length = spec["hair"]["length"]
    style = spec["hair"].get("style", "long")
    # Short and tied-back hair both hug the skull: they share the short cut's guides.
    close = table["SHORT_HAIR"] or style in ("short",) + TIED_STYLES
    inner, outer = list(MALE["HAIR_INNER"]), list(MALE["HAIR_OUTER"])
    if not close:
        inner, outer = list(table["HAIR_INNER"]) + [(-1.15, length * 0.8), (-1.22, length)], \
            list(table["HAIR_OUTER"]) + [(-1.96, length * 0.82), (-1.80, length + 0.10)]
    guides = []
    for guide in (inner, outer):
        curve = resample(smooth(guide, samples=10), HAIR_GUIDE_SAMPLES)
        guides.append(add_wave(head(curve), spec["hair"]["wave"] * unit, spec["hair"]["waves"], 0.6))
    fig.hair["side"] = tuple(guides)
    rng = np.random.default_rng(spec["seed"])
    fig.shapes["hair_side"] = section_outline(guides[0], guides[1], rng, spec["hair"]["tip_locks"] + 1,
                                              spec["hair"].get("tip_split", TIP_SPLIT_START))
    fig.points["hair_band"] = head([(0.0, -1.35)])[0]
    if style in TIED_STYLES:
        tail = profile_tail(length) if style == "ponytail" else PROFILE_BUN
        tail_guides = [resample(head(smooth(guide, samples=10)), HAIR_GUIDE_SAMPLES) for guide in tail]
        fig.hair["tail"] = tuple(tail_guides)
        fig.shapes["hair_tail"] = section_outline(tail_guides[0], tail_guides[1], rng, spec["hair"]["tip_locks"] + 1,
                                                  BUN_SPLIT if style == "bun" else spec["hair"].get("tip_split", TIP_SPLIT_START))
    if spec["hair"].get("bangs"):
        # The front view's fringe seen from the side: locks from the crown arching over the forehead.
        bangs = PROFILE_BANGS_SHORT if close else PROFILE_BANGS_LONG
        bang_guides = [resample(head(smooth(guide, samples=10)), HAIR_GUIDE_SAMPLES) for guide in bangs]
        fig.hair["bangs"] = tuple(bang_guides)
        fig.shapes["hair_bangs"] = section_outline(bang_guides[0], bang_guides[1], rng, BANG_LOCKS, BANG_SPLIT)
    for name, points in (("eye", table["EYE_UPPER"] + table["EYE_LOWER"]), ("upper_lip", table["UPPER_LIP"]),
                         ("lower_lip", table["LOWER_LIP"])):
        fig.shapes[name] = head(smooth(points, samples=6, closed=True))
    fig.paths["eye_upper"] = head(smooth(table["EYE_UPPER"], samples=8))
    fig.paths["brow"] = head(smooth(table["BROW"], samples=8))
    if table["LASH_FLICK"]:
        fig.paths["lash_flick"] = head(smooth(table["LASH_FLICK"], samples=6))
    fig.paths["nostril"] = head(smooth(table["NOSTRIL"], samples=6))


# Head landmarks a profile hand can reach for, in head units (x toward the face, y down from the eye).
PROFILE_HEAD_MARKS = {"chin": (0.82, 1.16), "mouth": (0.95, 0.78), "cheek": (0.40, 0.62), "brow": (0.62, -0.45), "crown": (-0.40, -1.95)}
# Elbow choices in profile: forward and back are the front-view "out" and "in" for a figure facing +x.
PROFILE_BENDS = {"forward": "out", "back": "in", "down": "down", "up": "up"}


def aim_arm(spec, setup, head, unbody, table):
    """The setup with the near arm's `reach` solved into angles (see anatomy_body.solve_arm).

    A reach is {"mark": a PROFILE_HEAD_MARKS name} or {"at": [x, y]} (shares of the picture after any
    mirror), plus "offset" [dx, dy] in head units; "bend" is forward, back, down or up.
    """
    arm = (setup.get("profile_pose") or {}).get("arm") or {}
    aim = arm.get("reach")
    if not isinstance(aim, dict):
        return setup
    from anatomy_body import elbow_for, heading as down_heading, angle_of, GRASP_SHARE, REACH_ROUNDS
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    if "at" in aim:
        x, y = aim["at"]
        mirror = spec.get("pose", {}).get("mirror", False)
        target = unbody([[(1.0 - x if mirror else x) * width, y * height]])[0]
    elif aim["mark"] in ("knee", "ankle"):
        # The near leg's joints, laid out as lay_out_body does (body coordinates).
        leg = {**DEFAULT_POSE, **(setup.get("profile_pose") or {})}["leg_near"]
        legs = (setup.get("shape") or {}).get("legs", 1.0)
        knee = table["HIP"] + table["THIGH"] * legs * heading(leg["thigh"])
        target = knee if aim["mark"] == "knee" else knee + table["SHIN"] * legs * heading(leg["shin"])
    else:
        target = unbody(head([PROFILE_HEAD_MARKS[aim["mark"]]]))[0]
    target = target + np.asarray(aim.get("offset", (0.0, 0.0)), np.float64)
    solved = {key: value for key, value in arm.items() if key != "reach"}
    solved.setdefault("upper", DEFAULT_POSE["arm"]["upper"])
    solved.setdefault("fore", DEFAULT_POSE["arm"]["fore"])
    shoulder = table["SHOULDER"]
    for _ in range(REACH_ROUNDS):
        wrist = target - GRASP_SHARE * table["HAND"] * down_heading(solved["fore"])
        elbow, wrist = elbow_for(shoulder, wrist, table["UPPER_ARM"], table["FOREARM"], 1, PROFILE_BENDS[solved.get("bend", "down")])
        solved["upper"] = angle_of(elbow - shoulder, 1)
        solved["fore"] = angle_of(wrist - elbow, 1)
    pose = {**(setup.get("profile_pose") or {}), "arm": solved}
    return {**setup, "profile_pose": pose}


def lay_out_body(fig, setup, body, table):
    """Joints and outlines of the body in pixels."""
    pose = {**DEFAULT_POSE, **setup.get("profile_pose", {})}
    # An arm whose partner reach was set aside (measuring the scene) keeps the default angles.
    pose["arm"] = {**DEFAULT_POSE["arm"], **pose["arm"]}
    shape = setup.get("shape") or {}
    legs = shape.get("legs", 1.0)
    unit = fig.unit * fig.extra["profile"]["scale"]
    front = table["TORSO_FRONT"] * np.array([shape.get(name, 1.0) if name else 1.0 for name in FRONT_SHAPE])
    back = table["TORSO_BACK"] * np.array([shape.get(name, 1.0) if name else 1.0 for name in BACK_SHAPE])
    center = table["TORSO_X"] + pose["arch"] * ARCH_SHIFT
    hip = table["HIP"]
    seated = bool(pose.get("seat"))
    seat_y = hip[1] + table["THIGH_BACK"][0] * SEAT_DROP
    neck_path, neck_back, neck_front = table["NECK"]
    layout = {"pose": pose, "unit": unit, "table": table, "body": body, "center_u": center, "front_u": front, "back_u": back,
              "spine": body(np.column_stack([center, TORSO_Y])), "front": front * unit, "back": back * unit,
              "neck": (body(neck_path), np.array(neck_back) * unit, np.array(neck_front) * unit)}
    for name, outline, key, surface, sign in (("breast", table["BREAST"], "bust", front, 1.0),
                                              ("buttock", table["BUTTOCK"], "hips", back, -1.0)):
        points = np.array(outline)
        edge = center + sign * surface
        reach = shape.get(key, 1.0) * (1.0 + 0.4 * pose["arch"] * (sign < 0))
        if sign < 0 and not seated and pose["leg_near"]["thigh"] > STRIDE_FROM:
            # A thigh swung far forward (running, kicking, crouching) stretches the buttock flat over the hip.
            reach *= 1.0 - STRIDE_FLATTEN * min((pose["leg_near"]["thigh"] - STRIDE_FROM) / STRIDE_SPAN, 1.0)
        out = np.interp(points[:, 1], TORSO_Y, edge) + sign * points[:, 0] * reach
        levels = points[:, 1]
        if seated and sign < 0:
            # Sitting spreads the buttock back along the seat instead of letting it hang below.
            out = out - np.clip(levels - (seat_y - 0.6), 0, None) * 0.35
            levels = np.minimum(levels, seat_y)
        layout[name] = body(np.column_stack([out, levels]))
    shoulder = table["SHOULDER"]
    elbow = shoulder + table["UPPER_ARM"] * heading(pose["arm"]["upper"])
    wrist = elbow + table["FOREARM"] * heading(pose["arm"]["fore"])
    layout["arm"] = [body(point)[0] for point in (shoulder, elbow, wrist)]
    if pose.get("arm_far"):
        # The far arm hangs from the far shoulder, a little behind the near one; walking swings it opposite the near arm.
        far_shoulder = shoulder + np.array(FAR_SHOULDER_SHIFT)
        far_elbow = far_shoulder + table["UPPER_ARM"] * heading(pose["arm_far"]["upper"])
        far_wrist = far_elbow + table["FOREARM"] * heading(pose["arm_far"]["fore"])
        layout["arm_far"] = [body(point)[0] for point in (far_shoulder, far_elbow, far_wrist)]
    for name in ("leg_near", "leg_far"):
        knee = hip + table["THIGH"] * legs * heading(pose[name]["thigh"])
        ankle = knee + table["SHIN"] * legs * heading(pose[name]["shin"])
        layout[name] = [body(point)[0] for point in (hip, knee, ankle)]
        foot = np.array(FOOT_PATH) * table["FOOT_SCALE"]
        point = pose[name].get("foot", 0.0)
        if point:
            # A pointed foot (running, kicking back, crouching on the toes) turns about the ankle; positive points the toes down.
            turn = np.deg2rad(point)
            foot = foot @ np.array([[np.cos(turn), np.sin(turn)], [-np.sin(turn), np.cos(turn)]])
        layout[f"{name}_foot"] = body(ankle + foot)
    breast = layout["breast"]
    layout["marks"] = {"nipple": breast[min(3, len(breast) - 1)], "navel": body((center[6] + front[6] - 0.02, 6.35))[0],
                       "pit": body((center[0] + front[0], 2.35))[0], "fold": body((center[-1] - 0.55, 8.97))[0],
                       "blade": body((center[2] - back[2] + 0.25, 3.60))[0], "lumbar": body((center[5] - back[5] + 0.2, 5.70))[0]}
    if seated:
        layout["seat"] = seat_layout(body, table, layout, center, back, seat_y, legs)
    return layout


def seat_layout(body, table, layout, center, back, seat_y, legs):
    """Stool under a seated figure, in pixels: its board (a quad) and two legs reaching the floor."""
    floor = max(layout["leg_near_foot"][:, 1].max(), layout["leg_far_foot"][:, 1].max())
    rear = center[-2] - back[-2] - 0.35
    front = table["HIP"][0] + table["THIGH"] * legs * SEAT_REACH
    board = body([(rear, seat_y), (front, seat_y), (front, seat_y + SEAT_BOARD), (rear, seat_y + SEAT_BOARD)])
    stand = []
    for x in (rear + 0.25, front - 0.25 - SEAT_LEG):
        corner = body([(x, seat_y + SEAT_BOARD), (x + SEAT_LEG, seat_y + SEAT_BOARD)])
        stand.append(np.vstack([corner, [[corner[1][0], floor], [corner[0][0], floor]]]))
    return {"board": board, "legs": stand, "y": body([(0.0, seat_y)])[0][1], "floor": floor}


def landmarks(fig):
    """Named points of a built profile figure in pixels (its own orientation, before a mirror)."""
    layout = fig.extra["layout"]
    head = fig.extra["profile"]["head"]
    marks = {name: np.asarray(point, np.float64) for name, point in zip(("shoulder", "elbow", "wrist"), layout["arm"])}
    marks.update({name: np.asarray(point, np.float64) for name, point in zip(("hip", "knee", "ankle"), layout["leg_near"])})
    marks["eye"] = head([(0.0, 0.0)])[0]
    marks["chin"] = head([(0.86, 1.18)])[0]
    marks["soles"] = np.array([marks["ankle"][0], max(layout["leg_near_foot"][:, 1].max(), layout["leg_far_foot"][:, 1].max())])
    marks["mouth"] = head([PROFILE_HEAD_MARKS["mouth"]])[0]
    # Partner marks for an embrace: the back of the neck and the small of the back.
    path, back, _ = layout["neck"]
    forward = layout["body"]([(1.0, 0.0)])[0] - layout["body"]([(0.0, 0.0)])[0]
    forward = forward / max(np.linalg.norm(forward), 1e-6)
    marks["nape"] = path[1] - forward * back[1]
    marks["lower_back"] = np.asarray(layout["marks"]["lumbar"], np.float64)
    marks["upper_back"] = np.asarray(layout["marks"]["blade"], np.float64)
    if "seat" in layout:
        marks["seat"] = np.array([marks["hip"][0], layout["seat"]["y"]])
    return marks


def lift_mask(fig, names, inked=True):
    """Mask of the near arm's parts of a painted profile figure, to lay them again over a later figure.

    A name is "hand_near", "forearm_near" (forearm and hand) or "arm_near"; a dict {"part": name, "from": share}
    keeps the forearm only from that share of its length on (as subject_figure.lift_mask does).
    """
    parts = fig.extra["arm_masks"]
    total = np.zeros(fig.size, np.float32)
    for item in names:
        name, start = (item["part"], item.get("from", 0.0)) if isinstance(item, dict) else (item, 0.0)
        part = name.rsplit("_", 1)[0]
        core = parts["hand"]
        if part in ("forearm", "arm"):
            core = np.maximum(core, parts["forearm"] * (parts["forearm_along"] >= start))
        if part == "arm":
            core = np.maximum(core, parts["upper"])
        total = np.maximum(total, core)
    if not inked:
        return total.astype(np.float32)
    return np.maximum(total, cv2.dilate((total > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8))).astype(np.float32)


# ------------------------------------------------------------------- relief
def sit_on(part, layout):
    """Flatten a part where it rests on the seat: nothing of it may hang below the seat's top."""
    if "seat" not in layout:
        return part
    rows = np.arange(part.mask.shape[0], dtype=np.float32)[:, None]
    keep = np.clip(layout["seat"]["y"] - rows + 0.5, 0.0, 1.0)
    board = layout["seat"]["board"]
    within = (np.arange(part.mask.shape[1])[None, :] >= board[:, 0].min()) & (np.arange(part.mask.shape[1])[None, :] <= board[:, 0].max())
    keep = np.where(within, keep, 1.0).astype(np.float32)
    return relief.Part((part.mask * keep).astype(np.float32), part.height, part.along, part.across)


def leg_relief(size, layout, name):
    hip, knee, ankle = layout[name]
    unit, table = layout["unit"], layout["table"]
    thigh = relief.tube(size, np.linspace(hip, knee, 5), table["THIGH_BACK"] * unit, table["THIGH_FRONT"] * unit, 0.88)
    shin = relief.tube(size, np.linspace(knee, ankle, 5), table["SHIN_BACK"] * unit, table["SHIN_FRONT"] * unit, 0.88)
    foot = relief.tube(size, layout[f"{name}_foot"], FOOT_WIDTHS * unit * table["FOOT_SCALE"], roundness=0.8)
    return sit_on(relief.union([thigh, shin, foot], blend=0.15 * unit), layout)


def body_relief(size, layout):
    """Torso, neck, breast (or chest muscle), buttock and the near leg, fused into one surface."""
    unit = layout["unit"]
    return relief.union([trunk_relief(size, layout), leg_relief(size, layout, "leg_near")], blend=0.30 * unit)


def trunk_relief(size, layout):
    """Torso, neck and the soft forms on them, flattened where they sit."""
    unit, table = layout["unit"], layout["table"]
    torso = relief.tube(size, layout["spine"], layout["back"], layout["front"], TORSO_ROUNDNESS, cap_start=False)
    neck = relief.tube(size, *layout["neck"], roundness=0.80)
    soft = [relief.blob(size, smooth(layout[name], samples=8, closed=True), table["SOFT_DEPTH"] * unit) for name in ("breast", "buttock")]
    if table["ADAMS_APPLE"]:
        center, radius_x, radius_y = table["ADAMS_APPLE"]
        body = layout["body"]
        soft.append(relief.blob(size, body(ellipse(center, radius_x, radius_y, 24)), radius_x * 0.8 * unit))
    return sit_on(relief.union([torso, neck] + soft, blend=0.30 * unit), layout)


def arm_relief(size, layout, hand_pose, name="arm"):
    """One arm with its hand. Returns (arm, upper arm, hand); the forearm tube rides along as `arm.fore`."""
    shoulder, elbow, wrist = layout[name]
    unit, table = layout["unit"], layout["table"]
    upper = relief.tube(size, np.linspace(shoulder, elbow, 5), table["UPPER_ARM_WIDTHS"] * unit, roundness=0.88)
    fore = relief.tube(size, np.linspace(elbow, wrist, 5), table["FOREARM_WIDTHS"] * unit, roundness=0.88)
    direction = wrist - elbow
    angle = np.degrees(np.arctan2(direction[0], -direction[1]))
    hand = build_hand(size, wrist, table["HAND"] * unit, angle, hand_pose, mirror=True, forearm=False, width=table["HAND_WIDTH"])
    arm = relief.union([upper, fore], blend=0.12 * unit)
    arm = relief.union([arm, hand.whole], blend=0.08 * unit)
    arm.fore = fore
    return arm, upper, hand


# ------------------------------------------------------------------- paint
def paint_seat(scene, layout):
    """A plain wooden stool: board and two legs, lit from the lamp's side, outlined."""
    seat = layout.get("seat")
    if not seat:
        return
    tones = sf.seat_tones(scene)
    for leg in seat["legs"]:
        mask = fill(scene.size, leg)
        over(scene.image, rgb(tones["shadow"]), mask)
        kit.ink_edges(scene, mask, 1.8, "seat", "line")
    board = fill(scene.size, seat["board"])
    over(scene.image, rgb(tones["base"]), board)
    if scene.shade_on:
        rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
        top, bottom = seat["board"][:, 1].min(), seat["board"][:, 1].max()
        under = np.clip((rows - top) / max(bottom - top, 1.0), 0, 1) * np.ones((1, scene.size[1]), np.float32)
        over(scene.image, rgb(tones["shadow"]), board * under, 0.6)
        edge = stroke(scene.size, seat["board"][:2], scene.px(0.05))
        screen(scene.image, rgb(tones["light"]), edge * board, 0.5)
    kit.ink_edges(scene, board, 2.0, "seat", "line")


# A wall (pillar) a figure leans back against: its width (head units) and the share of light on its face.
WALL = {"width": 4.5, "gap": 0.0, "lit": 0.35}


def wall_edge(layout):
    """The x (px) where the figure's back is furthest back: shoulder blades, buttock, a foot set against the wall."""
    rear = min(layout["buttock"][:, 0].min(), layout["marks"]["blade"][0])
    for name in ("leg_near_foot", "leg_far_foot"):
        rear = min(rear, layout[name][:, 0].min())
    return rear


def paint_wall(scene, layout):
    """A pillar behind a figure leaning back on it (`profile_pose.wall`): its edge meets her back."""
    setup = layout["pose"].get("wall")
    if not setup:
        return
    setup = {**WALL, **(setup if isinstance(setup, dict) else {})}
    unit = layout["unit"]
    rear = wall_edge(layout)
    right = rear - setup["gap"] * unit
    left = right - setup["width"] * unit
    floor = max(layout["leg_near_foot"][:, 1].max(), layout["leg_far_foot"][:, 1].max()) + 0.1 * unit
    outline = np.array([(left, -10.0), (right, -10.0), (right, floor), (left, floor)])
    mask = fill(scene.size, outline)
    tones = scene.style["palette"]["wall"]
    over(scene.image, rgb(tones["base"]), mask)
    if scene.shade_on:
        cols = np.arange(scene.size[1], dtype=np.float32)[None, :]
        # The pillar's face darkens away from its lit corner; the corner itself catches a line of light.
        fall = np.clip((right - cols) / max(right - left, 1.0), 0.0, 1.0) * np.ones((scene.size[0], 1), np.float32)
        over(scene.image, rgb(tones["shadow"]), scene.edge(fall * (1.0 - setup["lit"]) + 0.15) * mask, 0.8)
        corner = stroke(scene.size, np.array([(right - 0.06 * unit, -10.0), (right - 0.06 * unit, floor)]), 0.08 * unit)
        screen(scene.image, rgb(tones["light"]), corner * mask, 0.6)
        base = np.clip((np.arange(scene.size[0], dtype=np.float32)[:, None] - (floor - 0.5 * unit)) / (0.5 * unit), 0.0, 1.0)
        over(scene.image, rgb(tones["shadow"]), base * mask, 0.5)
    kit.ink_edges(scene, mask, 2.0, "wall", "line")


def paint_head(scene, layout):
    """Profile face: skin, ear, eye, brow, lips, then the hair."""
    fig = scene.fig
    head = fig.extra["profile"]["head"]
    table = layout["table"]
    unit = scene.px(1.0)
    # A narrow rounded rim: a profile face is lit almost flat, its form shows only at the edges.
    face = relief.blob(scene.size, fig.shapes["face"], PROFILE_FACE_RIM * unit)
    # Why a low level: only the turn under the jaw goes dark; broken into grain, a wider shadow reads as stubble.
    kit.shade_solid(scene, face, "skin", level=PROFILE_FACE_LEVEL, spread=0.5, flush=scene.style["body_render"]["skin_flush"],
                    seam_blur=0.10 * unit)
    tones = scene.style["palette"]
    center, radius_x, radius_y = table["EAR"]
    ear = fill(scene.size, head(ellipse(center, radius_x, radius_y, 32, -12)))
    over(scene.image, rgb(tones["skin"]["shadow"]), scene.soften(ear, 0.01), 0.35)
    inner_ear = head(smooth([(-0.52, -0.02), (-0.66, 0.10), (-0.64, 0.30), (-0.54, 0.38)]))
    over(scene.image, rgb(tones["skin"]["deep"]), stroke(scene.size, inner_ear, 0.025 * unit * taper(len(inner_ear), 0.2, 0.2)), 0.6)
    center, radius_x, radius_y = table["CHEEK"]
    over(scene.image, rgb(tones["skin"]["blush"]), blur(fill(scene.size, head(ellipse(center, radius_x, radius_y))), 0.10 * unit) * face.mask,
         scene.style["face_render"]["blush_opacity"])
    stubble = scene.style["face_render"].get("stubble", 0.0)
    if scene.shade_on and stubble > 0:
        # Beard shadow along the jaw, the chin and the upper lip; the lips stay clear.
        beard = fill(scene.size, head(smooth([(0.95, 0.64), (0.97, 1.00), (0.93, 1.27), (0.40, 1.30), (-0.40, 1.08), (-0.48, 0.80),
                                              (-0.25, 0.95), (0.35, 1.08), (0.80, 0.98), (0.84, 0.68)], samples=6, closed=True)))
        lips = blur(np.maximum(scene.mask("upper_lip"), scene.mask("lower_lip")), 0.02 * unit)
        over(scene.image, rgb(tones["hair"]["base"]), blur(beard, 0.05 * unit) * face.mask * (1.0 - lips), stubble * 0.8)
    eyes = fig.spec.get("eyes", {})
    # In profile the near eye is the one we see; a wink or a laugh closes it into an arc.
    closed = {**eyes, **eyes.get("near", {})}.get("closed", 0.0) >= 0.5
    upper = fig.paths["eye_upper"]
    if closed:
        arc = head(smooth(table["CLOSED_ARC"], samples=8))
        over(scene.image, rgb(tones["hair"]["line"]), stroke(scene.size, arc, table["LID_WIDTH"] * unit * taper(len(arc), 0.3, 0.6, 0.5)))
    else:
        eye = scene.mask("eye")
        over(scene.image, rgb(tones["eye"]["white"]), eye)
        center, radius_x, radius_y = table["IRIS"]
        iris = fill(scene.size, head(ellipse(center, radius_x, radius_y, 24))) * eye
        over(scene.image, rgb(tones["eye"]["iris"]), iris)
        over(scene.image, rgb(tones["eye"]["iris_dark"]), shift(iris, 0, -0.03 * unit) * iris, 0.6)
        # A catch light in the upper front of the iris keeps the eye alive at figure scale.
        glint = fill(scene.size, head(ellipse((center[0] + 0.012, center[1] - 0.045), radius_x * 0.38, radius_y * 0.26, 16))) * iris
        over(scene.image, rgb(tones["eye"]["white"]), glint, 0.9)
        over(scene.image, rgb(tones["hair"]["line"]), stroke(scene.size, upper, table["LID_WIDTH"] * unit * taper(len(upper), 0.3, 1.0, 0.8)))
    if "lash_flick" in fig.paths and not closed:
        flick = fig.paths["lash_flick"]
        over(scene.image, rgb(tones["hair"]["line"]), stroke(scene.size, flick, 0.022 * unit * taper(len(flick), 1.0, 0.0, 0.0)))
    brow = fig.paths["brow"]
    over(scene.image, rgb(tones["hair"]["shadow"]), stroke(scene.size, brow, table["BROW_WIDTH"] * unit * taper(len(brow), 0.5, 0.0, 0.3)), 0.9)
    over(scene.image, rgb(tones["lip"]["upper"]), scene.soften(scene.mask("upper_lip"), 0.004), 0.70)
    over(scene.image, rgb(tones["lip"]["lower"]), scene.soften(scene.mask("lower_lip"), 0.004), 0.70)
    if scene.shade_on:
        shine = fill(scene.size, head(ellipse(table["LIP_SHINE"], 0.03, 0.018)))
        screen(scene.image, rgb(tones["lip"]["shine"]), blur(shine, 0.008 * unit) * scene.mask("lower_lip"), 0.5)
    over(scene.image, rgb(tones["skin"]["deep"]), stroke(scene.size, fig.paths["nostril"], 0.018 * unit), 0.7)
    paint_profile_expression(scene, table, head, unit)
    scene.ink(np.vstack([fig.shapes["face"], fig.shapes["face"][:1]]), 2.4, profile=np.ones(len(fig.shapes["face"]) + 1))
    accessories.paint_glasses_profile(scene, head)
    if fig.spec["hair"].get("style") == "bun":
        bun = scene.mask("hair_tail")
        paint_hair_section(scene, "tail", form_shadow(scene, bun, 0.30, scene.style["hair_render"]["form_level"]))
    hair = scene.mask("hair_side")
    form = form_shadow(scene, hair, 0.30, scene.style["hair_render"]["form_level"], scene.style["hair_render"].get("form_spread", 0.3))
    paint_hair_section(scene, "side", form)
    if "bangs" in fig.hair:
        bangs = scene.mask("hair_bangs")
        paint_hair_section(scene, "bangs", form_shadow(scene, bangs, 0.20, scene.style["hair_render"]["form_level"]))
    accessories.paint_hat_profile(scene, head)
    return face.mask


# Looking back over a shoulder: the profile face sits this far (head units) toward the side it turns to, so the back
# view's neck rises under the jaw and the ear (the profile neck's top is 0.30 behind the eye), and this far lower:
# a head turned over the shoulder sinks a little toward it.
TURNED_HEAD_SHIFT, TURNED_HEAD_DROP = 0.30, 0.20


def paint_turned_head(scene, setup):
    """`figure.look_back` on a figure seen from behind: the head turned to show its profile over the shoulder.

    Why the profile head: a front face turned past 30 degrees slides off its own skull and reads as cut in half;
    the profile outline already has the nose, lips and chin on the silhouette. The face turns to the picture's
    right, or its left with {"side": "left"}. The head is laid out as the profile figure's and painted into the
    same picture over the back view's neck. Returns the head's mask (face and hair).
    """
    fig = scene.fig
    spec = fig.spec
    side = -1.0 if isinstance(setup, dict) and setup.get("side") == "left" else 1.0
    table = BUILDS[spec.get("sex", "female")]
    unit = fig.unit
    origin = np.asarray(fig.head_frame.origin_px, np.float64) + np.array([side * TURNED_HEAD_SHIFT, TURNED_HEAD_DROP]) * unit
    roll = np.deg2rad(side * spec["pose"].get("roll_deg", 0.0))
    turn = np.array([[np.cos(roll), -np.sin(roll)], [np.sin(roll), np.cos(roll)]])

    def head(points):
        return (np.atleast_2d(np.asarray(points, np.float64)) * np.array([side, 1.0])) @ turn.T * unit + origin

    turned = Figure(size=fig.size, unit=unit, light=fig.light, seed=fig.seed, spec=spec)
    turned.extra["profile"] = {"head": head, "body": None, "scale": 1.0, "table": table}
    lay_out_head(turned, spec, table, head)
    view = Scene(turned, scene.style, fig.seed, scene.shade_on, scene.lines_on)
    view.image = scene.image
    if spec["hair"].get("style") == "ponytail":
        tail = view.mask("hair_tail")
        paint_hair_section(view, "tail", form_shadow(view, tail, 0.30, view.style["hair_render"]["form_level"]))
    face = paint_head(view, {"table": table})
    hair = [view.mask("hair_side")] + ([view.mask("hair_bangs")] if "bangs" in turned.hair else [])
    return np.maximum.reduce([face] + hair).astype(np.float32)


def paint_profile_expression(scene, table, head, unit):
    """Expression in profile: the mouth corner turned up or down, an opened mouth, tears."""
    spec, tones = scene.fig.spec, scene.style["palette"]
    mouth = spec.get("mouth", {})
    corner = np.array(table["LOWER_LIP"][-1])
    # Only an expression's change from the resting mouth shows: a neutral profile keeps its plain lips.
    rest = (spec.get("expression") or {}).get("rest_smile", mouth.get("smile", 0.0))
    turn = (mouth.get("smile", rest) - rest) * 4.0
    if abs(turn) > 0.02:
        tick = head(smooth([corner + [0.02, 0.0], corner - [0.06, turn * 0.6], corner - [0.12, turn]], samples=6))
        over(scene.image, rgb(tones["lip"]["line"]), stroke(scene.size, tick, 0.016 * unit * taper(len(tick), 0.8, 0.0, 0.2)), 0.8)
    opening = mouth.get("open", 0.0)
    if opening > 0:
        upper, lower = np.array(table["UPPER_LIP"]), np.array(table["LOWER_LIP"])
        gap = [upper[3], upper[4], lower[-1] + [0.0, opening * 0.5], lower[0] + [0.0, opening * 0.8]]
        over(scene.image, mix(rgb(tones["lip"]["line"]), np.zeros(3, np.float32), 0.3), fill(scene.size, head(np.array(gap))), 0.9)
    if (spec.get("expression") or {}).get("tears"):
        track = head(smooth([(0.55, 0.07), (0.50, 0.30), (0.45, 0.58)], samples=8))
        over(scene.image, mix(rgb(tones["skin"]["light"]), rgb(tones["eye"]["white"]), 0.5), stroke(scene.size, track, 0.03 * unit), 0.5)


def paint_profile_accents(scene, layout, skin):
    """Nipple, navel, the fold under the buttock, the lumbar hollow, the shoulder blade; a man's chest edge."""
    unit, table = layout["unit"], layout["table"]
    tones = scene.style["palette"]["skin"]
    strength = scene.style["body_render"]["accent"]
    marks = layout["marks"]
    shadow, deep, flush = rgb(tones["shadow"]), rgb(tones["deep"]), rgb(tones["blush"])
    tip = marks["nipple"]
    radius_x, radius_y = table["NIPPLE"]
    areola = fill(scene.size, ellipse(tip + [-0.06 * unit, 0.0], radius_x * unit, radius_y * unit, 20)) * skin
    over(scene.image, mix(shadow, flush, 0.6), blur(areola, 0.01 * unit), 0.6)
    navel = marks["navel"]
    over(scene.image, deep, scene.soften(stroke(scene.size, smooth([navel + [0, -0.06 * unit], navel + [-0.05 * unit, 0], navel + [0, 0.05 * unit]]),
                                                0.025 * unit), 0.006) * skin, 0.7)
    if "seat" not in layout:
        fold = marks["fold"]
        sf.crease(scene, [fold + [-0.25 * unit, -0.05 * unit], fold, fold + [0.40 * unit, 0.06 * unit]], 0.07, shadow, 0.55 * strength, 0.03, skin)
    sf.soft_mark(scene, fill(scene.size, ellipse(marks["lumbar"], 0.30 * unit, 0.55 * unit)), shadow, 0.25 * strength, 0.15, skin)
    sf.soft_mark(scene, fill(scene.size, ellipse(marks["blade"], 0.25 * unit, 0.45 * unit)), shadow, 0.18 * strength, 0.12, skin)
    pit = marks["pit"]
    bone = smooth([pit, pit + [-0.35 * unit, 0.10 * unit], pit + [-0.75 * unit, 0.12 * unit]])
    sf.soft_mark(scene, stroke(scene.size, bone + [0, 0.06 * unit], 0.06 * unit * taper(len(bone), 0.2, 0.0, 0.4)), shadow, 0.35 * strength, 0.03, skin)
    if table["ADAMS_APPLE"]:
        chest = layout["breast"]
        edge = smooth([chest[-3], chest[-2] + [0.0, 0.04 * unit], chest[-1] + [-0.30 * unit, 0.02 * unit]])
        sf.crease(scene, edge, 0.06, shadow, 0.45 * strength, 0.03, skin)
        if scene.lines_on:
            scene.ink(edge, 1.3, profile=taper(len(edge), 0.0, 0.0, 0.4), opacity=0.5, clip=skin)


def paint_far_part(scene, part, render, unit):
    """A limb on the far side: shaded a little darker than the body, then outlined."""
    kit.shade_solid(scene, part, "skin", level=render["figure_level"] + 0.12, spread=render["figure_spread"], seam_blur=0.10 * unit)
    over(scene.image, rgb(scene.style["palette"]["skin"]["shadow"]), part.mask, FAR_SHADE * scene.shade_on)
    kit.ink_edges(scene, part.mask, 2.0)


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    layout = fig.extra["layout"]
    unit = layout["unit"]
    render = scene.style["body_render"]
    paint_background(scene)
    near_ankle, far_ankle = layout["leg_near"][2], layout["leg_far"][2]
    soles = max(layout["leg_near_foot"][:, 1].max(), layout["leg_far_foot"][:, 1].max())
    # Off the ground (a jump, a running stride): the floor and the shadow stay `lift` head units below the soles.
    lift = layout["pose"].get("lift", 0.0) * unit
    if lift:
        far_ankle, near_ankle = far_ankle + [0.0, lift], near_ankle + [0.0, lift]
    sf.paint_floor(scene, [far_ankle, near_ankle], soles + 0.08 * unit + lift)
    run_hook(extras, "after_background", scene)
    if fig.spec.get("scene_props"):
        import props
        props.paint_scene_props(scene)
    paint_seat(scene, layout)
    paint_wall(scene, layout)
    accessories.remember_background(scene)
    import wardrobe_profile
    clothes = fig.spec["figure"].get("clothes") or {}

    far = leg_relief(fig.size, layout, "leg_far")
    far_parts = [far]
    if "arm_far" in layout:
        far_arm, far_upper, far_hand = arm_relief(fig.size, layout, layout["pose"].get("hand_far", "relaxed"), "arm_far")
        paint_far_part(scene, far_arm, render, unit)
        for part in far_hand.fingers.values():
            kit.ink_tube(scene, part, 1.4, start=0.25)
        far_parts.append(far_arm)
        wardrobe_profile.paint_far_sleeves(scene, layout, far_arm, far_upper, clothes)
    paint_far_part(scene, far, render, unit)
    wardrobe_profile.paint_far_leg_clothes(scene, layout, clothes)
    if fig.spec["hair"].get("style") == "ponytail":
        tail = scene.mask("hair_tail")
        paint_hair_section(scene, "tail", form_shadow(scene, tail, 0.30, scene.style["hair_render"]["form_level"]))

    trunk = body_relief(fig.size, layout)
    arm, upper, hand = arm_relief(fig.size, layout, layout["pose"]["hand"])
    whole = sf.lay_arm(trunk, arm, upper, unit)
    toward = -np.sign(fig.light[0])
    thrown = blur(shift(arm.mask, toward * unit * 0.12, unit * 0.06), unit * 0.06) * (1.0 - arm.mask)
    kit.shade_solid(scene, whole, "skin", level=render["figure_level"], spread=render["figure_spread"], gloss=render["skin_sheen"],
                    shininess=sf.SHEEN_SHININESS, flush=render["skin_flush"], extra_shadow=thrown * scene.shade_on,
                    seam_blur=sf.SEAM_BLUR * unit)
    sf.rim_light(scene, whole, render["rim"])
    sf.bounce_light(scene, whole, render["bounce"])
    paint_profile_accents(scene, layout, trunk.mask * (1.0 - arm.mask))
    skin_layer = scene.image.copy()
    kit.ink_edges(scene, whole.mask, 2.6)
    kit.ink_tube(scene, relief.Part(arm.mask, arm.height, np.where(upper.mask > 0.5, upper.along, 1.0).astype(np.float32)), 2.2,
                 start=0.30, clip=trunk.mask)
    for part in hand.fingers.values():
        kit.ink_tube(scene, part, 1.6, start=0.25)
    cloth = wardrobe_profile.paint_garments(scene, layout, trunk, whole, arm, upper, hand, skin_layer, clothes)
    if fig.spec["figure"].get("holds"):
        import held
        cloth = np.maximum(cloth, held.paint_held(scene, {"near": hand}, fig.spec["figure"]["holds"], unit, {"near": arm.fore.mask}))

    painted_arm = scene.image.copy() if layout["pose"]["arm"].get("front") else None
    fig.extra["arm_masks"] = {"hand": hand.whole.mask, "forearm": arm.fore.mask, "forearm_along": arm.fore.along, "upper": upper.mask}
    face = paint_head(scene, layout)
    # What of the head lies in front of a partner's arm passing behind the neck: face and hair.
    fig.extra["head_cover"] = np.maximum.reduce([face, scene.mask("hair_side")] + ([scene.mask("hair_bangs")] if "bangs" in fig.hair else []))
    if painted_arm is not None:
        # A hand at the chin or the cheek lies in front of the face: lay the forearm and hand back on top.
        # "arm" brings the upper arm too: an arm raised round a partner's neck passes in front of one's own neck.
        front = np.maximum(arm.fore.mask, hand.whole.mask)
        if layout["pose"]["arm"].get("front") == "arm":
            front = np.maximum(front, upper.mask)
        front = np.maximum(front, cv2.dilate((front > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)) * scene.lines_on)
        over(scene.image, painted_arm, front.astype(np.float32))
    run_hook(extras, "after_figure", scene)
    focus = np.full(scene.size, FOCUS["background"], np.float32)
    hair = scene.union("hair_side", "hair_bangs") if "bangs" in fig.hair else scene.mask("hair_side")
    for level, mask in ((FOCUS["far"], np.maximum.reduce([part.mask for part in far_parts])), (FOCUS["body"], whole.mask),
                        (FOCUS["cloth"], cloth), (FOCUS["hair"], hair),
                        (FOCUS["face"], (blur(face, 0.06 * scene.px(1.0)) > 0.02) * (1.0 - hair))):
        focus = np.where(mask > 0.5, level, focus)
    fig.focus = focus.astype(np.float32)
    for name, part in (("body", whole), ("far_leg", far)):
        kit.register(scene, f"profile_{name}", part.mask)
    return scene.image
