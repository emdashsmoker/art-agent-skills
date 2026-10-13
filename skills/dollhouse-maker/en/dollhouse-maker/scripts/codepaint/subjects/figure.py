"""Full figure drawn the way an illustrator constructs it, entirely in 2D.

  1. a stick skeleton of joints sets the pose (angles in the picture plane)
  2. the trunk is one contour through anatomical landmarks: neck, shoulder, armpit,
     bust, waist, hip, crotch. Chest and pelvis tilt against each other, so one
     side of the waist pinches and the other stretches
  3. limbs are tapered forms along the bones, with a different curve on each side
  4. all skin forms are inked as one surface: the outline is the silhouette of
     their union, plus an edge only where one form passes in front of another
  5. a three-quarter view is made with drawing rules, not rotation: the far half
     narrows, the near half widens slightly, the far breast breaks the contour,
     the near hip shows the buttock, far limbs tuck behind

A male figure (FigureSpec.sex = "male") goes through exactly the same steps; only the tables in BODY
change: broad shoulders, a straight waist, narrow hips, muscular limb widths, pectorals inked along their
lower border instead of breasts, and the abdominal landmarks drawn as lines.

Unit = one head height (hu). The neutral figure is 8 heads tall: chin 1.0,
pit of the neck 1.34, bust 2.05, waist 2.75, hip joints 3.83, crotch 4.15,
knees 5.8, ankles 7.6, ground 8.0. Angles are degrees from "straight down",
positive toward the screen-right; left/right always mean the viewer's.
"""
from dataclasses import dataclass, field, replace

import numpy as np

from ..color import rgb, mix
from ..geometry import catmull_rom, chaikin, ellipse, Ribbon
from ..scene import Part, Line, Stroke
from .extremities import Hand, HandSpec, Foot, FootSpec
from .head import Head, HeadSpec
from . import garments, held
from .side import SideView

# --- skeleton (hu) -------------------------------------------------------------
PELVIS_Y = 3.85                         # pelvis center below the top of the head
NECK_UP = 2.51                          # pelvis center up to the pit of the neck
WAIST_UP = 1.10
HIP_JOINT = (0.40, -0.02)               # in the pelvis frame
SHOULDER_JOINT = (0.665, 0.30)           # in the chest frame (origin = pit of the neck)
RAISED_SHOULDER = (0.16, 0.14)          # a raised arm carries its shoulder in and up
THIGH, SHIN = 1.97, 1.80
UPPER_ARM, FOREARM, HAND_LEN = 1.40, 1.12, 0.72
# the thigh is rounded as one mass with the trunk, so it takes the trunk's bulge; otherwise its edge
# shades darker than the hip above it and a band starts at the hip joint
LEG_BULGE = {True: 0.55, False: 0.9}    # keyed by "is the thigh"
THIGH_JOINT = 0.42                      # hu; around the hip joint the thigh grows out of the trunk with no line
LIMB_HALF = dict(leg=(0.34, 0.18), arm=(0.15, 0.115))   # typical half widths of (upper, lower) bone, for tone bands
LANDMARK = dict(female=0.22, male=0.36)  # strength of anatomy lines: knee, ankle bones, deltoid, elbow
VIEWS = ("front", "back", "side")
HAND_POSES = ("relaxed", "open", "hidden", "fist", "point", "grip")
# a raised arm whose hand is hidden behind the head: the forearm's end is drawn this share of the way toward
# the middle of the skull, so it lies behind the head instead of showing as a stub beside the ear
HIDDEN_REACH = 0.5
HIDDEN_SKULL_UP = 0.55      # middle of the skull above the neck joint, in head heights
FORESHORTENED_THIGH = 0.6   # leg_scale of a thigh below which it points at the viewer (drawn as a bent leg)
THIGH_GIRTH_T = 0.7         # where along the thigh its girth is taken for a thigh seen end on
GRIP_POINT = 0.56                       # where a held thing sits in a closed hand (hand lengths from the wrist)
SHARP_BEND = 65.0                       # deg; beyond this a limb is drawn as two overlapping forms

# --- trunk contour, right half; x is mirrored for the left ----------------------
CHEST = [(0.15, -0.13), (0.33, -0.04), (0.60, 0.06), (0.775, 0.17), (0.795, 0.34), (0.660, 0.52),
         (0.625, 0.74), (0.560, 1.00)]                      # chest frame: neck root .. underbust
# with the arm raised the shoulder tip lifts into the arm: the contour runs from the neck to the armpit
CHEST_RAISED = [(0.15, -0.13), (0.30, -0.06), (0.47, 0.02), (0.60, 0.22), (0.635, 0.50), (0.625, 0.74), (0.560, 1.00)]
WAIST = (0.450, 0.0)                                         # waist frame
PELVIS = [(0.585, -0.74), (0.790, -0.40), (0.880, -0.06), (0.76, 0.18), (0.32, 0.30)]   # pelvis frame: flank .. groin
HIP_WIDEST = 2                          # index of the widest point in PELVIS
# below the hip joint the thigh draws the contour, so the trunk tucks in under it
CROTCH_Y = 0.30
BUTTOCK = 0.085                         # extra width on the near upper thigh in a three-quarter view
LUMBAR, BELLY = 0.07, 0.05              # three-quarter: the near waist hollows (small of the back), the far waist fills

# --- three-quarter drawing rules (scaled by |turn|) -----------------------------
FAR_NARROW, NEAR_WIDEN = 0.30, 0.04     # half widths of the trunk
FAR_LIMB = 0.07                         # far limbs are drawn slightly thinner
FAR_BREAST_OUT, FAR_BREAST_NARROW = 0.07, 0.24
MAX_HEAD_YAW = 0.45                     # rad; limit of the head construction
HEAD_PIVOT_UP, HEAD_PIVOT_V = 0.48, 0.86  # skull pivot: above the pit of the neck, and its height in the head
SIDE_HEAD_FORWARD = 0.09                # hu; in profile the skull center sits forward of the neck
SEAT = ((-0.10, 0.22), 0.66, 0.24, 0.40)   # seated: buttock mass (center in pelvis frame, half width, half height),
                                        # and the seat surface below the pelvis center (hu)

# --- limb half widths along each bone: (t, outer, inner) -------------------------
THIGH_W = [(0.0, 0.46, 0.40), (0.15, 0.470, 0.405), (0.5, 0.365, 0.320), (0.85, 0.245, 0.235), (1.0, 0.215, 0.210)]
SHIN_W = [(0.0, 0.215, 0.210), (0.12, 0.210, 0.203), (0.30, 0.238, 0.250), (0.62, 0.155, 0.165),
          (0.90, 0.100, 0.097), (1.0, 0.104, 0.100)]
UPPER_ARM_W = [(0.0, 0.158, 0.158), (0.22, 0.178, 0.166), (0.60, 0.153, 0.145), (1.0, 0.126, 0.122)]
FOREARM_W = [(0.0, 0.126, 0.122), (0.22, 0.142, 0.134), (0.70, 0.100, 0.096), (1.0, 0.078, 0.076)]

# --- breast outline around its center (outer side = +x), chest frame -------------
BREAST_CENTER = (0.30, 0.70)
BREAST = [(-0.17, -0.30), (0.08, -0.33), (0.27, -0.14), (0.325, 0.08), (0.22, 0.28), (0.0, 0.335),
          (-0.21, 0.24), (-0.285, 0.02)]                    # teardrop: fuller low and to the outside
NIPPLE = (0.045, 0.075)

# --- bikini, drawn over the body and clipped to it -------------------------------
CUP = [(0.02, -0.40), (0.02, -0.40), (0.34, 0.06), (0.24, 0.31), (-0.06, 0.345), (-0.31, 0.16)]   # around the breast center
BRIEFS = [(0.0, -0.36), (0.98, -0.36), (0.98, -0.20), (0.50, 0.02), (0.15, 0.36), (0.0, 0.36)]     # pelvis frame, right half
BRIEFS_BACK = [(0.0, -0.34), (0.98, -0.36), (0.98, -0.20), (0.70, 0.14), (0.36, 0.38), (0.0, 0.42)]  # the seat is covered
BIKINI_BACK_BAND = 0.95             # chest frame y of the top's band across the back

# one-piece swimsuits, right half from the center of the neckline down to the crotch. Points outside the
# body are fine: the suit is clipped to the skin forms, so only neckline, armhole and leg cut matter.
SUIT_STRAP = [(0.21, -0.08), (0.32, -0.06)]                                     # chest frame
SUIT_ARMHOLE = [(0.42, 0.14), (0.56, 0.38), (0.70, 0.52), (1.00, 0.80)]          # chest frame
SUIT_SIDE = dict(waist=[(0.90, 0.0)], pelvis=[(1.20, -0.50)])
SUITS = {
    "onepiece": dict(neck=[(0.0, 0.60), (0.13, 0.50), (0.20, 0.22)],            # scoop neck, leg cut at the hip joint
                     cut=[(1.05, -0.34), (0.74, -0.16), (0.44, 0.08), (0.17, 0.28), (0.0, 0.33)]),
    "highleg": dict(neck=[(0.0, 1.02), (0.08, 0.70), (0.16, 0.30)],              # plunging neck, leg cut to the waist bone
                    cut=[(1.05, -0.72), (0.76, -0.54), (0.46, -0.14), (0.18, 0.24), (0.0, 0.33)]),
}
# from behind: a scoop down the back between the straps, and a leg cut that covers the seat
SUITS_BACK = {
    "onepiece": dict(neck=[(0.0, 0.95), (0.16, 0.78), (0.24, 0.30)],
                     cut=[(1.05, -0.34), (0.80, -0.08), (0.56, 0.24), (0.26, 0.42), (0.0, 0.44)]),
    "highleg": dict(neck=[(0.0, 1.25), (0.18, 0.95), (0.24, 0.30)],
                    cut=[(1.05, -0.66), (0.78, -0.34), (0.52, 0.10), (0.24, 0.36), (0.0, 0.40)]),
}
# slip dress: falls from the bust and skims the waist instead of following it
SLIP_NECK = [(0.0, 0.60), (0.15, 0.42), (0.30, 0.37), (0.50, 0.42), (0.66, 0.52)]   # chest frame
SLIP_SIDE = dict(chest=[(0.68, 0.80), (0.62, 1.06)], waist=[(0.50, 0.0)],
                 pelvis=[(0.64, -0.74), (0.84, -0.38), (0.92, -0.06)])       # skims the waist, covers the flank
SLIP_NECK_BACK = [(0.0, 0.50), (0.15, 0.42), (0.30, 0.37), (0.50, 0.42), (0.66, 0.52)]   # a lower, straight back
SLIP_HEM = 0.50                     # hem height along the thigh (0 = hip joint, 1 = knee)
OUTFITS_FEMALE = ("nude", "bikini", "onepiece", "highleg", "slip", "dressed")

# --- male body: broad shoulders, a straight waist, narrow hips, muscular limbs --------
CHEST_M = [(0.20, -0.15), (0.46, -0.06), (0.80, 0.05), (0.98, 0.20), (0.96, 0.34), (0.81, 0.52),
           (0.79, 0.80), (0.72, 1.02)]                     # neck root, trapezius, deltoid, armpit, lats
CHEST_RAISED_M = [(0.20, -0.15), (0.40, -0.08), (0.62, 0.02), (0.80, 0.22), (0.84, 0.50), (0.80, 0.78), (0.72, 1.02)]
PELVIS_M = [(0.640, -0.74), (0.675, -0.40), (0.695, -0.06), (0.63, 0.18), (0.30, 0.30)]
PEC_CENTER = (0.32, 0.46)                                   # chest frame
# around the pec center; the lower border is the drawn edge, a nearly straight line slanting up to the armpit
PEC = [(-0.29, -0.32), (-0.02, -0.34), (0.24, -0.24), (0.32, -0.08), (0.30, 0.04), (0.14, 0.16), (-0.06, 0.25),
       (-0.22, 0.28), (-0.30, 0.22), (-0.31, -0.06)]
MALE_NIPPLE = (0.04, 0.14)
ABS_ROWS = (-0.35, -0.10, 0.12)                             # tendinous intersections, waist frame y
# swim briefs and trunks, pelvis frame, right half
BRIEFS_M = [(0.0, -0.40), (0.98, -0.38), (0.98, -0.20), (0.56, 0.0), (0.22, 0.30), (0.0, 0.38)]
TRUNKS = dict(waist=[(0.0, -0.40), (0.0, -0.38)], hem=0.36, rise=0.40)   # waistband center and side height   # waistband, hem along the thigh, crotch y
# open shirt panel, right half: collar, shoulder, side, hem, then the open front edge back up to the collar
SHIRT = dict(shoulder=[(0.14, -0.17), (0.46, -0.08), (0.80, 0.03), (1.00, 0.20)],
             raised=[(0.14, -0.17), (0.40, -0.09), (0.60, 0.02), (0.76, 0.24)],
             side=dict(chest=[(0.86, 0.60), (0.84, 0.95)], waist=[(0.71, 0.0)], pelvis=[(0.76, -0.40), (0.78, -0.16)]),
             # a shirttail hem: high at the side seam, dropping toward the front corner
             front=dict(pelvis=[(0.64, 0.02), (0.47, 0.08), (0.39, 0.02), (0.38, -0.40)], waist=[(0.37, 0.0)],
                        chest=[(0.35, 0.90), (0.31, 0.56), (0.23, 0.26), (0.17, 0.02)]))
SLEEVE_ROLL = 0.90                  # sleeves rolled up to just above the elbow (fraction of the upper arm)
OUTFITS_MALE = ("nude", "briefs", "trunks", "open_shirt", "dressed")

# every value that differs by sex; methods read these instead of the module constants
BODY = {
    "female": dict(chest=CHEST, chest_raised=CHEST_RAISED, waist=WAIST[0], pelvis=PELVIS, hip_joint=HIP_JOINT,
                   shoulder_joint=SHOULDER_JOINT, buttock=BUTTOCK, lumbar=LUMBAR, belly=BELLY,
                   thigh_w=THIGH_W, shin_w=SHIN_W, upper_arm_w=UPPER_ARM_W, forearm_w=FOREARM_W,
                   arm=(UPPER_ARM, FOREARM, HAND_LEN), seat=SEAT, neck=(0.135, 0.126, 0.142, 0.20),
                   clavicle=[(0.06, 0.03), (0.26, 0.055), (0.50, 0.02)], hand_breadth=1.0, foot=1.0,
                   outfits=OUTFITS_FEMALE,
                   head=dict()),
    "male": dict(chest=CHEST_M, chest_raised=CHEST_RAISED_M, waist=0.615, pelvis=PELVIS_M, hip_joint=(0.36, -0.02),
                 shoulder_joint=(0.86, 0.30), buttock=0.04, lumbar=0.03, belly=0.02,
                 thigh_w=[(0.0, 0.40, 0.36), (0.15, 0.41, 0.36), (0.45, 0.365, 0.31), (0.80, 0.27, 0.25), (1.0, 0.235, 0.22)],
                 shin_w=[(0.0, 0.24, 0.23), (0.12, 0.235, 0.23), (0.30, 0.27, 0.275), (0.62, 0.18, 0.185),
                         (0.90, 0.115, 0.11), (1.0, 0.12, 0.115)],
                 upper_arm_w=[(0.0, 0.20, 0.19), (0.18, 0.22, 0.20), (0.45, 0.19, 0.20), (0.70, 0.175, 0.18),
                              (1.0, 0.145, 0.14)],
                 forearm_w=[(0.0, 0.15, 0.145), (0.22, 0.175, 0.165), (0.70, 0.12, 0.115), (1.0, 0.095, 0.09)],
                 arm=(1.45, 1.15, 0.76), seat=((-0.06, 0.22), 0.58, 0.22, 0.40), neck=(0.165, 0.155, 0.17, 0.24),
                 clavicle=[(0.07, 0.02), (0.32, 0.05), (0.62, 0.0)], hand_breadth=1.12, foot=1.08,
                 outfits=OUTFITS_MALE,
                 head=dict(face="male", hair_style="short", bangs="short", jaw=0.88, eye_size=0.88, eyeshadow=0.0,
                           blush=0.0, lip_alpha=0.10)),
}
OUTFITS = OUTFITS_FEMALE + OUTFITS_MALE[1:]


@dataclass
class FigurePose:
    view: str = "front"            # front / back (seen from behind) / side (profile, see FigurePose.facing)
    facing: float = 1.0            # side view: +1 the figure looks to the screen-right, -1 to the left. In profile
                                   # limb angles read + = forward, and right_* is the near limb, left_* the far one
    turn: float = 0.0              # -1..1; three-quarter amount, + = body faces the viewer's right
    lean: float = 0.0              # deg; the whole trunk and head tip over around the pelvis, + = clockwise.
                                   # Limb angles stay absolute screen angles, so a lying figure is posed directly
    seated: bool = False           # buttocks rest on a seat: a flattened mass under the pelvis
    pelvis_tilt: float = 0.0       # deg; + lowers the right hip (weight on the left leg)
    chest_tilt: float = 0.0        # deg; + lowers the right shoulder
    spine_shift: float = 0.0       # hu; chest center moved right of the pelvis center
    head_tilt: float = 0.0         # deg
    head_yaw: float = 0.0          # deg; + turns the face to the right
    left_thigh: float = 2.0
    left_shin: float = 0.0
    right_thigh: float = -2.0
    right_shin: float = 0.0
    left_leg_scale: tuple = (1.0, 1.0)      # foreshortening of thigh and shin (1 = full length)
    right_leg_scale: tuple = (1.0, 1.0)
    left_upper_arm: float = -9.0
    left_forearm: float = -3.0
    right_upper_arm: float = 9.0
    right_forearm: float = 3.0
    left_arm_scale: tuple = (1.0, 1.0)
    right_arm_scale: tuple = (1.0, 1.0)
    left_arm_front: object = None           # True / False, or None = far arm goes behind the trunk
    right_arm_front: object = None
    left_hand: str = "relaxed"              # relaxed / open / hidden / fist / point / grip (holds FigureSpec.*_item)
    right_hand: str = "relaxed"
    left_wrist: float = 0.0                 # deg; the hand bends off the forearm line, + = toward the screen-right
    right_wrist: float = 0.0
    left_foot_turn: float = 12.0            # deg, toes turned out; 40 or more draws the foot from the side
    right_foot_turn: float = 12.0
    left_foot_pitch: float = 0.0            # side view: deg, + lifts the toes (heel strike), - points them (toe off)
    right_foot_pitch: float = 0.0


CONTRAPPOSTO = FigurePose(
    turn=0.55, pelvis_tilt=8.0, chest_tilt=-7.0, spine_shift=-0.10, head_tilt=-4.0, head_yaw=6.0,
    left_thigh=5.0, left_shin=2.0, right_thigh=-2.0, right_shin=10.0, right_leg_scale=(0.95, 0.96),
    left_upper_arm=-14.0, left_forearm=10.0, left_hand="relaxed", left_arm_front=True,
    right_upper_arm=148.0, right_forearm=-58.0, right_arm_scale=(0.95, 0.80), right_hand="hidden",
    right_arm_front=True, left_foot_turn=8.0, right_foot_turn=55.0)
ARMS_UP = FigurePose(
    turn=-0.45, pelvis_tilt=-7.0, chest_tilt=6.0, spine_shift=0.09, head_tilt=4.0, head_yaw=-6.0,
    left_thigh=2.0, left_shin=-10.0, left_leg_scale=(0.95, 0.96), right_thigh=-5.0, right_shin=-2.0,
    left_upper_arm=-146.0, left_forearm=56.0, left_arm_scale=(0.95, 0.80), left_hand="hidden", left_arm_front=True,
    right_upper_arm=150.0, right_forearm=-60.0, right_arm_scale=(0.95, 0.80), right_hand="hidden",
    right_arm_front=True, left_foot_turn=55.0, right_foot_turn=8.0)
PINUP = FigurePose(                 # weight on the left leg, hip pushed out, one hand in the hair, one on the hip
    turn=0.50, pelvis_tilt=12.0, chest_tilt=-9.0, spine_shift=-0.20, head_tilt=-6.0, head_yaw=4.0,
    left_thigh=3.0, left_shin=1.0, right_thigh=-9.0, right_shin=15.0, right_leg_scale=(0.93, 0.95),
    left_upper_arm=-30.0, left_forearm=38.0, left_arm_scale=(1.0, 0.82), left_hand="relaxed", left_arm_front=True,
    right_upper_arm=148.0, right_forearm=-58.0, right_arm_scale=(0.95, 0.80), right_hand="hidden",
    right_arm_front=True, left_foot_turn=6.0, right_foot_turn=58.0)
SEATED = FigurePose(                # on a box, body and knees turned to the right, near hand resting on the thigh
    turn=0.45, seated=True, lean=3.0, pelvis_tilt=-3.0, chest_tilt=-4.0, spine_shift=0.04, head_tilt=-5.0, head_yaw=-4.0,
    left_thigh=78.0, left_shin=-4.0, left_leg_scale=(0.80, 0.98), right_thigh=68.0, right_shin=8.0,
    right_leg_scale=(0.74, 0.98), left_upper_arm=12.0, left_forearm=66.0, left_arm_scale=(1.0, 0.95),
    left_hand="relaxed", left_arm_front=True, right_upper_arm=16.0, right_forearm=8.0, right_arm_scale=(0.98, 0.80),
    right_hand="relaxed", right_arm_front=False, left_foot_turn=58.0, right_foot_turn=58.0)
RECLINING = FigurePose(             # lying on her side, propped on the left elbow, head to the left
    turn=0.30, lean=-56.0, pelvis_tilt=-6.0, chest_tilt=4.0, head_tilt=44.0, head_yaw=0.0,
    left_thigh=84.0, left_shin=88.0, right_thigh=62.0, right_shin=100.0, right_leg_scale=(0.95, 0.95),
    # the elbow rests on the couch (lean chosen so it meets Figure.rest_y()), the forearm lies flat on it
    left_upper_arm=0.0, left_forearm=-86.0, left_arm_scale=(1.0, 0.90), left_hand="open", left_arm_front=True,
    right_upper_arm=62.0, right_forearm=60.0, right_hand="relaxed", right_arm_front=True,   # along the body to the hip
    left_foot_turn=60.0, right_foot_turn=60.0)
AKIMBO = FigurePose(                # standing square, hands on the hips, weight a little on the left leg
    turn=0.30, pelvis_tilt=4.0, chest_tilt=-2.0, spine_shift=-0.04, head_tilt=-3.0, head_yaw=-8.0,
    left_thigh=6.0, left_shin=-1.0, right_thigh=-7.0, right_shin=3.0, right_leg_scale=(0.97, 0.98),
    # the wrist lands on the iliac crest and the hand bends down over the hip
    left_upper_arm=-38.0, left_forearm=60.0, left_hand="relaxed", left_wrist=-50.0, left_arm_front=True,
    right_upper_arm=36.0, right_forearm=-60.0, right_hand="hidden", right_arm_front=False,
    left_foot_turn=14.0, right_foot_turn=50.0)
HEROIC = FigurePose(                # a classical standing nude: weight on the right leg, the free leg set out
    turn=0.40, pelvis_tilt=6.0, chest_tilt=-5.0, spine_shift=-0.06, head_tilt=-3.0, head_yaw=10.0,
    left_thigh=-10.0, left_shin=-3.0, left_leg_scale=(0.97, 0.97), right_thigh=3.0, right_shin=1.0,
    left_upper_arm=-7.0, left_forearm=-1.0, left_hand="relaxed", left_arm_front=True,
    right_upper_arm=10.0, right_forearm=26.0, right_arm_scale=(0.97, 0.90), right_hand="relaxed", right_arm_front=False,
    left_foot_turn=42.0, right_foot_turn=10.0)
PHONE = FigurePose(                 # looking down at a phone held in front of the chest
    turn=0.25, pelvis_tilt=4.0, chest_tilt=-2.0, spine_shift=-0.03, head_tilt=-9.0, head_yaw=-6.0,
    left_thigh=4.0, left_shin=0.0, right_thigh=-5.0, right_shin=4.0, right_leg_scale=(0.97, 0.98),
    left_upper_arm=-8.0, left_forearm=-3.0, left_hand="relaxed", left_arm_front=True,
    right_upper_arm=6.0, right_forearm=-152.0, right_arm_scale=(0.97, 0.80), right_hand="grip", right_arm_front=True,
    left_foot_turn=12.0, right_foot_turn=45.0)
COFFEE = FigurePose(                # a mug held at the chest, the other hand at the side
    turn=-0.25, pelvis_tilt=-4.0, chest_tilt=3.0, spine_shift=0.04, head_tilt=3.0, head_yaw=4.0,
    left_thigh=5.0, left_shin=-4.0, left_leg_scale=(0.97, 0.98), right_thigh=-4.0, right_shin=0.0,
    left_upper_arm=-4.0, left_forearm=128.0, left_arm_scale=(0.97, 0.78), left_hand="grip", left_arm_front=True,
    right_upper_arm=8.0, right_forearm=3.0, right_hand="relaxed", right_arm_front=True,
    left_foot_turn=45.0, right_foot_turn=12.0)
POINT = FigurePose(                 # pointing out to the side, the other hand on the hip
    turn=0.20, pelvis_tilt=5.0, chest_tilt=-3.0, spine_shift=-0.04, head_tilt=-2.0, head_yaw=14.0,
    left_thigh=6.0, left_shin=0.0, right_thigh=-6.0, right_shin=3.0,
    left_upper_arm=-34.0, left_forearm=50.0, left_arm_scale=(1.0, 0.86), left_hand="relaxed", left_wrist=-45.0,
    left_arm_front=True, right_upper_arm=80.0, right_forearm=86.0, right_hand="point", right_arm_front=True,
    left_foot_turn=14.0, right_foot_turn=40.0)
DESK = FigurePose(                  # seated square to the viewer at a desk, forearms forward on its top
    turn=0.08, seated=True, pelvis_tilt=0.0, chest_tilt=0.0, head_tilt=-4.0, head_yaw=0.0,
    left_thigh=10.0, left_shin=0.0, left_leg_scale=(0.30, 0.95), right_thigh=-10.0, right_shin=0.0,
    right_leg_scale=(0.30, 0.95), left_upper_arm=-12.0, left_forearm=38.0, left_arm_scale=(0.92, 0.66),
    left_hand="relaxed", left_arm_front=True, right_upper_arm=12.0, right_forearm=-38.0, right_arm_scale=(0.92, 0.66),
    right_hand="relaxed", right_arm_front=True, left_foot_turn=12.0, right_foot_turn=12.0)
STANDING = FigurePose()
# profile poses (view="side"): angles + = forward; right_* is the near limb
SIDE_STAND = FigurePose(
    view="side", head_tilt=-2.0, left_thigh=-1.0, left_shin=0.0, right_thigh=2.0, right_shin=0.0,
    left_upper_arm=-4.0, left_forearm=8.0, right_upper_arm=3.0, right_forearm=12.0)
WALK = FigurePose(                  # mid stride: the near leg reaches forward, the far leg pushes off behind
    view="side", lean=3.0, head_tilt=-3.0, left_thigh=-15.0, left_shin=-36.0, right_thigh=24.0, right_shin=5.0,
    left_upper_arm=20.0, left_forearm=38.0, right_upper_arm=-22.0, right_forearm=-8.0,
    left_foot_pitch=8.0, right_foot_pitch=14.0)
SIDE_SEATED = FigurePose(           # upright on a chair, hands resting on the thighs
    view="side", seated=True, lean=-2.0, head_tilt=-2.0, left_thigh=86.0, left_shin=-2.0, right_thigh=82.0,
    right_shin=6.0, left_upper_arm=10.0, left_forearm=70.0, right_upper_arm=14.0, right_forearm=74.0,
    left_foot_pitch=0.0, right_foot_pitch=0.0)
SIDE_PHONE = FigurePose(            # standing in profile, looking down at a phone held up in the near hand
    view="side", lean=1.0, head_tilt=16.0, left_thigh=-2.0, right_thigh=3.0, right_shin=2.0,
    left_upper_arm=-3.0, left_forearm=6.0, right_upper_arm=8.0, right_forearm=128.0, right_arm_scale=(1.0, 0.92),
    right_hand="grip")
POSES = {"contrapposto": CONTRAPPOSTO, "arms_up": ARMS_UP, "pinup": PINUP, "seated": SEATED,
         "reclining": RECLINING, "akimbo": AKIMBO, "heroic": HEROIC, "phone": PHONE, "coffee": COFFEE, "point": POINT,
         "desk": DESK, "standing": STANDING, "side_stand": SIDE_STAND, "walk": WALK, "side_seated": SIDE_SEATED,
         "side_phone": SIDE_PHONE}

# a stride cycle in profile (walk()): leg swing about a slightly forward middle, the knee bending through the
# swing, the arms swinging against the legs
STRIDE_MID, STRIDE_SWING = 4.5, 19.5          # thigh: deg forward of vertical at mid stride, and the swing each way
KNEE_STANCE, KNEE_SWING = 8.0, 46.0           # knee bend on the ground, and the extra bend at mid swing
SWING_WINDOW = (0.42, 0.92)                   # share of the cycle the foot is off the ground (0 = heel strike)
ARM_SWING = 21.0                              # upper arm: deg each way
ELBOW_BEND, ELBOW_GAIN = 15.0, 0.2            # forearm: bend of the elbow, and more of it as the arm swings forward
TOE_PITCH = (11.0, 3.0)                       # foot pitch: mean and swing


def walk(phase=0.0, stride=1.0, facing=1.0, arms=1.0):
    """A walking pose in profile at one point of the stride cycle: phase 0 has the near leg reaching forward
    (heel strike), 0.25 the legs passing, 0.5 the far leg forward; stride scales the leg swing (0.6 a stroll,
    1.3 a brisk walk), arms the arm swing. Walkers in a crowd each take their own phase and stride."""
    out = {}
    for side, offset in (("right", 0.0), ("left", 0.5)):               # right is the near leg in profile
        f = (phase + offset) % 1.0
        thigh = STRIDE_MID + STRIDE_SWING * stride * np.cos(2 * np.pi * f)
        swing = 0.0
        if SWING_WINDOW[0] <= f <= SWING_WINDOW[1]:
            swing = np.sin(np.pi * (f - SWING_WINDOW[0]) / (SWING_WINDOW[1] - SWING_WINDOW[0]))
        bend = KNEE_STANCE + KNEE_SWING * swing * min(1.0, stride)
        upper = -ARM_SWING * arms * np.cos(2 * np.pi * f)                # each arm swings against its own leg
        out.update({f"{side}_thigh": float(thigh), f"{side}_shin": float(thigh - bend),
                    f"{side}_upper_arm": float(upper),
                    f"{side}_forearm": float(upper + ELBOW_BEND + ELBOW_GAIN * upper),
                    f"{side}_foot_pitch": float(TOE_PITCH[0] + TOE_PITCH[1] * np.cos(2 * np.pi * f))})
    return replace(WALK, facing=float(facing), **out)


@dataclass
class FigureSpec:
    cx: float                       # image x of the pelvis center
    top: float                      # image y of the top of the head in the neutral pose
    unit: float                     # px per head height
    skin: object = "#f0cfba"
    shoulder: float = 1.0           # width multipliers
    waist: float = 1.0
    hip: float = 1.0
    bust: float = 1.0               # breast volume; on a male figure the pectoral volume
    limb: float = 1.0               # limb thickness
    legs: float = 1.0               # leg length (1.05 = fashion-illustration proportion)
    gloss: float = 0.6              # soft highlights on shoulders, breasts, hips and legs (0 = matte skin)
    blush: float = 0.6              # warm tint at knees, elbows, shoulders
    modeling: float = 0.6           # soft form shadows: far side of the torso, inner thighs, abdomen, limb sides
    form: float = 1.0               # roundness of the skin forms (1.5-1.8 turns them harder: an oil study under side light)
    light_side: float = -1.0        # -1 = scene light comes from the left, +1 = from the right
    sex: str = "female"             # female / male: proportions, chest, head defaults and outfits (BODY)
    outfit: str = "nude"            # female: nude / bikini / onepiece / highleg / slip; male: nude / briefs / trunks / open_shirt
    cloth: object = "#1f3a5f"
    cloth2: object = None           # second garment: trunks under an open shirt, the bottom of "dressed"
    upper: str = None               # outfit "dressed", upper garment: tee / longsleeve / shirt / blouse (garments.TOPS)
    lower: str = None               # outfit "dressed", lower garment: jeans / slacks / skirt / long_skirt (garments.BOTTOMS)
    shoes: str = None               # any outfit: sneakers / heels / boots, None = barefoot
    cloth3: object = "#ecebe7"      # shoe color
    left_item: str = None           # held in a "grip" hand: phone / mug / book / umbrella / clear_umbrella (held.ITEMS)
    right_item: str = None
    head: dict = field(default_factory=dict)      # extra HeadSpec fields (hair, iris, ...)
    line: float = 1.0
    detail: bool = True             # navel, clavicles, creases
    ident: str = ""                 # several figures in one scene: a short unique id per figure ("a", "b"). Every
                                    # part name and key of this figure gets the prefix "ident/", so clips, ink
                                    # groups and shadows of two overlapping figures stay apart


def _dir(deg):
    a = np.radians(deg)
    return np.array([np.sin(a), np.cos(a)])


def _rot(v, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    v = np.asarray(v, float)
    return np.stack([v[..., 0] * c - v[..., 1] * s, v[..., 0] * s + v[..., 1] * c], -1)


class Figure(SideView):
    MERGE = "body"                  # all skin forms share this ink key

    def __init__(self, spec, pose="contrapposto"):
        self.s = spec
        self.b = BODY[spec.sex]
        if spec.outfit not in self.b["outfits"]:
            raise ValueError(f"outfit for a {spec.sex} figure must be one of {self.b['outfits']}")
        if spec.upper not in (None,) + garments.TOPS or spec.lower not in (None,) + garments.BOTTOMS:
            raise ValueError(f"upper must be one of {garments.TOPS}, lower one of {garments.BOTTOMS}")
        self.p = POSES[pose] if isinstance(pose, str) else pose
        if self.p.view not in VIEWS:
            raise ValueError(f"view must be one of {VIEWS}")
        self.back = self.p.view == "back"
        self.side = self.p.view == "side"
        self.fc = 1.0 if self.p.facing >= 0 else -1.0                # side view: the screen direction of the front
        self.u = spec.unit
        self.px = spec.unit / 150.0
        self.a = min(abs(self.p.turn), 1.0)                 # three-quarter amount
        self.thigh_outer = {}                               # side -> (outer contour points, fraction of thigh length)
        self.thigh_inner = {}                               # side -> (inner contour points, fraction of thigh length)
        # body geometry kept while the forms are built, so clothes can be cut from the body itself
        self.geo = dict(trunk=None, breasts=[], limbs={})
        self.sole = {"left": 0.36, "right": 0.36}           # depth of each sole below its ankle (hu), set by _leg
        self.far = float(np.sign(self.p.turn))              # +1: the far side is screen-right; 0: frontal
        if self.side:                                       # a profile has no three-quarter rules
            self.a, self.far = 0.0, 0.0
        self._solve()

    # ---- frames and skeleton ------------------------------------------------
    def I(self, p):
        """Figure space (hu, origin = pelvis center) to image px."""
        s = self.s
        return np.asarray(p, float) * self.u + [s.cx, s.top + PELVIS_Y * self.u]

    def _wide(self, x):
        """Three-quarter rule for widths: the far half narrows, the near half widens a little."""
        x = np.asarray(x, float)
        if self.side:                                       # profile: + is the front of the body
            return x * self.fc
        is_far = x * self.far > 0
        return x * np.where(is_far, 1 - FAR_NARROW * self.a, 1 + NEAR_WIDEN * self.a)

    def _frames(self):
        p = self.p
        neck = _rot(np.array([p.spine_shift, -NECK_UP]), p.lean)
        waist = _rot(np.array([p.spine_shift * 0.45, -WAIST_UP]), p.lean)
        return dict(chest=(neck, p.chest_tilt + p.lean), waist=(waist, (p.chest_tilt + p.pelvis_tilt) / 2 + p.lean),
                    pelvis=(np.zeros(2), p.pelvis_tilt + p.lean))

    def tilt(self, frame):
        """Screen rotation of a frame in radians (for shapes laid on it)."""
        return float(np.radians(self.frames[frame][1]))

    def F(self, frame, pts, scale=1.0):
        """Point(s) of a frame (chest / waist / pelvis) in figure space, with the three-quarter rule."""
        origin, tilt = self.frames[frame]
        q = np.asarray(pts, float).reshape(-1, 2) * [scale, 1.0]
        q = np.stack([self._wide(q[:, 0]), q[:, 1]], 1)
        return origin + _rot(q, tilt)

    def _solve(self):
        p, s, b = self.p, self.s, self.b
        if self.side:
            return self._side_solve(THIGH, SHIN)
        upper_arm, forearm, _ = b["arm"]
        self.frames = self._frames()
        j = {"pelvis": np.zeros(2), "neck": self.frames["chest"][0]}
        for side, sd in (("left", -1), ("right", 1)):
            j[f"hip_{side}"] = self.F("pelvis", (sd * b["hip_joint"][0], b["hip_joint"][1]), s.hip)[0]
            scale = getattr(p, f"{side}_leg_scale")
            j[f"knee_{side}"] = j[f"hip_{side}"] + _dir(getattr(p, f"{side}_thigh")) * THIGH * s.legs * scale[0]
            j[f"ankle_{side}"] = j[f"knee_{side}"] + _dir(getattr(p, f"{side}_shin")) * SHIN * s.legs * scale[1]
            local = np.array([sd * b["shoulder_joint"][0], b["shoulder_joint"][1]])
            if self._raised(side):
                local += [-sd * RAISED_SHOULDER[0], -RAISED_SHOULDER[1]]
            j[f"shoulder_{side}"] = self.F("chest", local, s.shoulder)[0]
            scale = getattr(p, f"{side}_arm_scale")
            j[f"elbow_{side}"] = j[f"shoulder_{side}"] + _dir(getattr(p, f"{side}_upper_arm")) * upper_arm * scale[0]
            j[f"wrist_{side}"] = j[f"elbow_{side}"] + _dir(getattr(p, f"{side}_forearm")) * forearm * scale[1]
        self.j = j

    def _raised(self, side):
        return abs(getattr(self.p, f"{side}_upper_arm")) > 90

    def _is_far(self, sd):
        return sd * self.far > 0 and self.a > 0.15

    def joint(self, name):
        """Image position of a joint: hip_/knee_/ankle_/shoulder_/elbow_/wrist_ + left/right, neck, pelvis."""
        return self.I(self.j[name])

    def ground_y(self):
        if self.s.shoes:                                     # a shoe sole (a heel) stands lower than a bare foot
            from .extremities import SHOES
            depth = SHOES[self.s.shoes]["sole_y"]
        else:
            depth = 0.36
        return max(self.joint("ankle_left")[1], self.joint("ankle_right")[1]) + depth * self.u

    def _shadow(self, depth=1.4):
        return np.clip(rgb(self.s.skin) * (1 - depth + depth * np.array([0.80, 0.58, 0.58])), 0, 1)

    def _skin(self, name, **kw):
        """A skin form: same color and material, inked together with the rest of the body."""
        s = self.s
        kw.setdefault("line", Line(1.9 * self.px * s.line, shade_gain=0.45))
        if "bulge" in kw:
            kw["bulge"] = kw["bulge"] * s.form
        return Part(name, s.skin, material="skin", group="body", merge=self.MERGE, **kw)

    # ---- trunk ------------------------------------------------------------
    def _trunk_contour(self):
        if self.side:
            return self._side_contour()
        s, b = self.s, self.b
        sides = {}
        for sd in (-1, 1):
            shape = b["chest_raised"] if self._raised("left" if sd < 0 else "right") else b["chest"]
            chest = self.F("chest", [(sd * x, y) for x, y in shape], s.shoulder)
            hollow = (1 + b["belly"] * self.a) if self._is_far(sd) else (1 - b["lumbar"] * self.a)
            waist = self.F("waist", (sd * b["waist"] * hollow, WAIST[1]), s.waist)
            pelvis = [(sd * x, y) for x, y in b["pelvis"]]
            sides[sd] = np.vstack([chest, waist, self.F("pelvis", pelvis, s.hip)])
        crotch = self.F("pelvis", (0.0, CROTCH_Y))
        return np.vstack([sides[1], crotch, sides[-1][::-1]])

    def _trunk(self):
        s, px = self.s, self.px
        contour = catmull_rom(self.I(self._trunk_contour()), closed=True, samples=10)
        self.geo["trunk"] = contour
        strokes = []
        if s.detail and self.back:
            strokes = self._back_marks()
        elif s.detail:
            shadow = self._shadow()
            C = lambda pts: catmull_rom(self.I(self.F("chest", pts)), samples=8)
            Pv = lambda pts: catmull_rom(self.I(self.F("pelvis", pts)), samples=8)
            for sd in (-1, 1):                                # clavicles, groin creases
                strokes.append(Stroke(C([(sd * x, y) for x, y in self.b["clavicle"]]),
                                      width=1.6 * px, color=shadow, alpha=0.55))
                if s.sex == "female":                         # a male figure draws the iliac furrow instead
                    strokes.append(Stroke(Pv([(sd * 0.60, -0.16), (sd * 0.44, 0.0), (sd * 0.24, 0.16), (sd * 0.09, 0.26)]),
                                          width=1.2 * px, color=shadow, alpha=0.20))
            navel = self.I(self.F("pelvis", [(0, -0.82), (0, -0.76)]))
            strokes.append(Stroke(navel, width=2.6 * px, color=mix(self._shadow(1.6), "#5a3a30", 0.4), alpha=0.75))
            notch = C([(-0.055, -0.04), (0.0, 0.03), (0.055, -0.04)])      # the pit between the clavicles
            strokes.append(Stroke(notch, width=1.3 * px, color=shadow, alpha=0.35))
            if s.sex == "male":
                strokes += self._abs()
                for sd in (-1, 1):                            # serratus: the saw-tooth along the ribs below the armpit
                    for x, y in ((0.70, 0.74), (0.68, 0.86), (0.655, 0.98)):
                        strokes.append(Stroke(C([(sd * (x + 0.05), y - 0.04), (sd * x, y), (sd * (x - 0.04), y + 0.02)]),
                                              width=1.2 * px, color=shadow, alpha=0.30))
            else:
                mid = self.I(np.vstack([self.F("chest", [(0, 1.12)]), self.F("waist", [(0, -0.05)])]))
                strokes.append(Stroke(mid, width=1.3 * px, color=shadow, alpha=0.22))
        # rounded together with the thighs: otherwise the lower edge of the trunk would shade like a rim
        return self._skin("trunk", polys=[contour], bulge=0.55, strokes=strokes, focus=0.45,
                          shape_with=["leg_left_0", "leg_right_0"])

    def _back_marks(self):
        """The back seen from behind: the spine, the shoulder blades, the long muscles beside the spine, the two
        dimples above the pelvis and the cleft between the buttocks."""
        px, shadow = self.px, self._shadow(1.2)
        C = lambda frame, pts: catmull_rom(self.I(self.F(frame, pts)), samples=8)
        male = self.s.sex == "male"
        strokes = [Stroke(catmull_rom(np.vstack([self.I(self.F("chest", [(0, 0.08), (0, 0.85)])), self.I(self.F("waist", [(0, 0.0)])),
                                                 self.I(self.F("pelvis", [(0, -0.60)]))]), samples=8),
                          width=1.5 * px, color=shadow, alpha=0.45)]
        for sd in (-1, 1):
            blade = [(sd * 0.20, 0.24), (sd * 0.17, 0.52), (sd * 0.28, 0.84), (sd * 0.46, 0.68)]   # inner edge, lower tip
            strokes.append(Stroke(C("chest", blade), width=1.4 * px, color=shadow, alpha=0.42 if male else 0.32))
            strokes.append(Stroke(C("chest", [(sd * 0.24, 0.30), (sd * 0.44, 0.22), (sd * 0.60, 0.17)]), width=1.2 * px,
                                  color=shadow, alpha=0.25))
            column = np.vstack([self.I(self.F("chest", [(sd * 0.12, 0.95)])), self.I(self.F("waist", [(sd * 0.13, 0.0)])),
                                self.I(self.F("pelvis", [(sd * 0.12, -0.55)]))])
            strokes.append(Stroke(catmull_rom(column, samples=8), width=1.2 * px, color=shadow, alpha=0.30 if male else 0.18))
            dimple = self.I(self.F("pelvis", [(sd * 0.15, -0.58), (sd * 0.17, -0.53)]))
            strokes.append(Stroke(dimple, width=2.2 * px, color=shadow, alpha=0.45))
            if male:                                          # the edge of the broad back muscle under the arm
                strokes.append(Stroke(C("chest", [(sd * 0.72, 0.62), (sd * 0.62, 0.90), (sd * 0.55, 1.05)]), width=1.2 * px,
                                      color=shadow, alpha=0.28))
        strokes.append(Stroke(C("pelvis", [(0.0, -0.40), (0.0, -0.10), (0.0, 0.26)]), width=1.6 * px, color=shadow,
                              alpha=0.6))
        return strokes

    def _abs(self):
        """Male abdomen: the center line, the tendinous intersections across the rectus, the outer edge
        of the rectus, and the iliac furrows running down to the groin (the V)."""
        px, shadow = self.px, self._shadow(1.2)
        C = lambda frame, pts: self.I(self.F(frame, pts))
        strokes = [Stroke(catmull_rom(np.vstack([C("chest", [(0, 0.80)]), C("waist", [(0, 0.0)]),
                                                 C("pelvis", [(0, -0.86)])]), samples=8),
                          width=1.5 * px, color=shadow, alpha=0.40)]
        for row, y in enumerate(ABS_ROWS):
            for sd in (-1, 1):
                dip = 0.03 * (row - 1)                       # the rows bow down toward the navel
                pts = C("waist", [(sd * 0.035, y), (sd * 0.13, y - 0.02 + dip), (sd * 0.23, y + 0.03 + dip)])
                strokes.append(Stroke(catmull_rom(pts, samples=6), width=1.5 * px, color=shadow, alpha=0.34))
        for sd in (-1, 1):
            edge = np.vstack([C("chest", [(sd * 0.27, 0.86)]), C("waist", [(sd * 0.27, -0.10)]),
                              C("pelvis", [(sd * 0.24, -0.52)])])
            strokes.append(Stroke(catmull_rom(edge, samples=8), width=1.3 * px, color=shadow, alpha=0.20))
            furrow = C("pelvis", [(sd * 0.58, -0.56), (sd * 0.42, -0.26), (sd * 0.17, 0.10)])
            strokes.append(Stroke(catmull_rom(furrow, samples=8), width=1.6 * px, color=shadow, alpha=0.42))
        return strokes

    def _pecs(self):
        """Pectoral masses: a broad flat form on each side whose lower border is the drawn edge; the top
        fades into the chest. Named like the breasts so clothes and accents clip the same way."""
        s, u = self.s, self.u
        parts = []
        for sd in sorted((-1, 1), key=lambda sd: not self._is_far(sd)):
            outline = catmull_rom(self._breast_shape(sd, PEC, PEC_CENTER), closed=True, samples=8)
            top, side = self._breast_shape(sd, [(0.0, -0.34), (0.34, -0.06)], PEC_CENTER)
            # inked only along the lower border: a line running up the outer side into the armpit would
            # round the pec into a breast
            parts.append(self._skin(f"breast_{sd}", polys=[outline], bulge=0.25, cast=0.02 * u, focus=0.5,
                                    erase=[(ellipse(top[0], top[1], 0.50 * s.bust * u, 0.30 * s.bust * u), 0.10 * u)],
                                    joints=[(top[0], top[1], 0.44 * s.bust * u), (side[0], side[1], 0.17 * u)],
                                    line=Line(1.9 * self.px * s.line, alpha=0.5)))
            c = self._breast_shape(sd, [MALE_NIPPLE], PEC_CENTER)[0]       # every male outfit leaves the chest bare
            squash = 1 - 0.35 * self.a if self._is_far(sd) else 1.0
            parts.append(Part("areola", mix(s.skin, "#b97a70", 0.45), polys=[ellipse(c[0], c[1], 0.030 * u * squash, 0.027 * u)],
                              shade=False, material="flat", blur=0.008 * u, alpha=0.75, receive=False, clip=f"breast_{sd}"))
        return parts

    def _breast_shape(self, sd, shape, center=BREAST_CENTER):
        """Outline points around one breast center, with the three-quarter rules applied."""
        s = self.s
        far = self._is_far(sd)
        out = FAR_BREAST_OUT * (0.4 if s.sex == "male" else 1.0)     # a flat chest barely breaks the contour
        cx = float(self._wide(sd * center[0] * s.shoulder)) + (self.far * out * self.a if far else 0.0)
        narrow = 1 - (FAR_BREAST_NARROW if far else 0.04) * self.a
        pts = np.asarray(shape, float) * s.bust
        local = np.stack([cx + sd * pts[:, 0] * narrow, center[1] + pts[:, 1]], 1)
        origin, tilt = self.frames["chest"]
        return self.I(origin + _rot(local, tilt))

    def _breasts(self):
        s, u = self.s, self.u
        parts = []
        order = sorted((-1, 1), key=lambda sd: not self._is_far(sd))          # far breast first
        for sd in order:
            outline = catmull_rom(self._breast_shape(sd, BREAST), closed=True, samples=8)
            self.geo["breasts"].append(outline)
            top = self._breast_shape(sd, [(0.0, -0.30)])[0]
            parts.append(self._skin(f"breast_{sd}", polys=[outline], bulge=0.85, cast=0.05 * u, focus=0.5,
                                    erase=[(ellipse(top[0], top[1], 0.46 * s.bust * u, 0.27 * s.bust * u), 0.10 * u)],
                                    joints=[(top[0], top[1], 0.40 * s.bust * u)],
                                    line=Line(2.0 * self.px * s.line, alpha=0.85)))
            if s.outfit != "nude":
                continue
            shift = self.far * 0.06 * self.a                # both point toward where the chest faces
            c = self._breast_shape(sd, [(NIPPLE[0] + sd * shift, NIPPLE[1])])[0]
            squash = 1 - 0.35 * self.a if self._is_far(sd) else 1.0
            parts.append(Part("areola", mix(s.skin, "#c9837c", 0.55), polys=[ellipse(c[0], c[1], 0.050 * u * squash, 0.046 * u)],
                              shade=False, material="flat", blur=0.010 * u, alpha=0.85, receive=False, clip=f"breast_{sd}"))
            parts.append(Part("nipple", mix(s.skin, "#b86f6c", 0.75), polys=[ellipse(c[0], c[1], 0.017 * u * squash, 0.016 * u)],
                              shade=False, material="flat", blur=0.004 * u, alpha=0.9, receive=False, clip=f"breast_{sd}"))
        return parts

    # ---- skin rendering ---------------------------------------------------
    def _soft(self, name, center, rx, ry, color, alpha, clip, rot=0.0, blend="normal", blur=0.06):
        """A soft-edged patch of tone on the skin: no form of its own, clipped to the forms it lies on."""
        u = self.u
        return Part(name, color, polys=[ellipse(center[0], center[1], rx * u, ry * u, rot)], shade=False,
                    material="flat", blur=blur * u, alpha=alpha, blend=blend, clip=clip, receive=False)

    def _across(self, a, b, t, amount):
        """Point at fraction t of the bone a-b moved across it by amount hu (+ toward the light, also for a
        lying limb); and the bone's rotation for ellipse()."""
        d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        perp = np.array([-d[1], d[0]])
        if perp @ np.array([self.s.light_side * 0.8, -0.6]) < 0:
            perp = -perp
        return a + (b - a) * t + perp * amount * self.u, float(np.arctan2(-d[0], d[1]))

    def _inward(self, a, b, sd):
        """Unit vector across the bone a-b toward the body's center line (sd = -1 left limb, +1 right)."""
        d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        return np.array([-d[1], d[0]]) * sd, d

    def _landmark(self, pts, alpha=1.0):
        """A short anatomy line in skin shadow tone, clipped to the form it is drawn on."""
        strength = LANDMARK[self.s.sex] * alpha
        return Stroke(catmull_rom(np.asarray(pts), samples=6), width=1.3 * self.px, color=self._shadow(1.2),
                      alpha=strength, clip=True)

    def _along(self, a, b, t, side_shift):
        """Point at fraction t of the bone a-b, shifted sideways in hu; and the bone's rotation for ellipse()."""
        d = b - a
        return a + d * t + [side_shift * self.u, 0.0], float(np.arctan2(-d[0], d[1]))

    def _trunk_accents(self):
        """Modeling on the torso: shadow down the side away from the light, the hollows beside the
        abdomen, light on the near hip. These are painted tone, as an illustrator lays them in."""
        s, ls = self.s, self.s.light_side
        clip = ["trunk", "breast_-1", "breast_1"]
        shade, light = self._shadow(0.9), "#fff6ec"
        parts = []
        if s.modeling > 0:
            rw, rc = self.tilt("waist"), self.tilt("chest")
            # down the side away from the light; on a male the band sits on the flank, off the pecs and abs
            side_x, side_w = (0.50, 0.11) if s.sex == "male" else (0.36, 0.15)
            side = self.I(self.F("waist", (-ls * side_x, -0.25)))[0]
            parts.append(self._soft("torso_shade", side, side_w, 0.80, shade, 0.75 * s.modeling, clip, rot=rw,
                                    blend="multiply", blur=0.08))
            for sd in (-1, 1):                        # beside the abdomen; from behind, the groove beside the spine
                c = self.I(self.F("waist", (sd * (0.10 if self.back else 0.17), 0.12)))[0]
                parts.append(self._soft("abdomen", c, 0.045, 0.36, shade, 0.34 * s.modeling, clip, rot=rw,
                                        blend="multiply", blur=0.045))
            if self.back:
                pass
            elif s.sex == "male":                     # shade tucked under each pec border
                for sd in (-1, 1):
                    c = self._breast_shape(sd, [(0.02, 0.33)], PEC_CENTER)[0]
                    parts.append(self._soft("under_pec", c, 0.30, 0.05, shade, 0.30 * s.modeling, ["trunk"],
                                            rot=rc - sd * 0.18, blend="multiply", blur=0.04))
            else:
                under = self.I(self.F("chest", (0.0, 1.12)))[0]
                parts.append(self._soft("under_bust", under, 0.45, 0.07, shade, 0.45 * s.modeling, clip, rot=rc,
                                        blend="multiply", blur=0.05))
        if s.gloss > 0:
            hip = self.I(self.F("pelvis", (ls * 0.52, -0.30)))[0]
            parts.append(self._soft("hip_light", hip, 0.10, 0.24, light, 0.50 * s.gloss, clip, rot=self.tilt("pelvis"),
                                    blend="screen", blur=0.05))
            for sd in (-1, 1):
                if self.back:                         # light across each shoulder blade
                    c = self.I(self.F("chest", (sd * 0.36 + ls * 0.04, 0.45)))[0]
                    parts.append(self._soft("blade_light", c, 0.14, 0.18, light, 0.35 * s.gloss, clip,
                                            rot=self.tilt("chest"), blend="screen", blur=0.05))
                    continue
                if s.sex == "male":                   # a broad sheen on the upper pec, toward the light
                    c = self._breast_shape(sd, [(ls * sd * 0.10, -0.02)], PEC_CENTER)[0]
                    parts.append(self._soft("pec_light", c, 0.17, 0.10, light, 0.45 * s.gloss, [f"breast_{sd}"],
                                            rot=self.tilt("chest"), blend="screen", blur=0.04))
                    continue
                c = self._breast_shape(sd, [(ls * sd * 0.09, -0.07)])[0]
                parts.append(self._soft("breast_light", c, 0.10 * s.bust, 0.09 * s.bust, light, 0.60 * s.gloss,
                                        [f"breast_{sd}"], blend="screen", blur=0.035))
            collar = self.I(self.F("chest", (ls * 0.40, 0.14)))[0]
            parts.append(self._soft("shoulder_light", collar, 0.16, 0.07, light, 0.40 * s.gloss, clip, rot=self.tilt("chest"),
                                    blend="screen", blur=0.04))
        return parts

    def _limb_accents(self, kind, side, names):
        """Light along the limb on the light side, warm blush at the joint, shadow high on the inner thigh."""
        s = self.s
        a, b, c = (self.joint(f"{k}_{side}") for k in (("hip", "knee", "ankle") if kind == "leg" else ("shoulder", "elbow", "wrist")))
        wide = 1.0 if kind == "leg" else 0.5
        # bones under a sleeve take no skin tone: 0 none, 1 the upper arm, 2 the whole arm
        sleeved = 0
        if kind == "arm" and s.outfit == "open_shirt":
            sleeved = 1
        elif kind == "arm" and s.outfit == "dressed" and s.upper:
            sleeved = 2 if garments.TOP_CUT[s.upper]["sleeve"] > 1.2 else 1
        parts = []
        bones = ((a, b, 0.42, 0.20), (b, c, 0.36, 0.16))
        for k, (p0, p1, t, ratio) in enumerate(bones):
            if k < sleeved:
                continue
            # streaks scale with the drawn bone, so they stay on a foreshortened thigh
            length = ratio * np.linalg.norm(p1 - p0) / self.u
            if s.gloss > 0:
                center, rot = self._across(p0, p1, t, 0.11 * wide)
                parts.append(self._soft(f"{kind}_light", center, 0.040 * wide, length, "#fff6ec",
                                        0.55 * s.gloss, names, rot=rot, blend="screen", blur=0.03))
            if s.modeling > 0:                               # form shadow down the side away from the light
                hw = LIMB_HALF[kind][k] * s.limb
                center, rot = self._across(p0, p1, 0.5, -0.58 * hw)
                parts.append(self._soft(f"{kind}_shade", center, 0.30 * hw, length * 1.9, self._shadow(0.9),
                                        0.30 * s.modeling, names, rot=rot, blend="multiply", blur=0.04))
        if s.blush > 0 and sleeved < 2:
            parts.append(self._soft(f"{kind}_blush", b + [0, 0.02 * self.u], 0.13 * wide + 0.03, 0.12 * wide + 0.03, "#f08f86",
                                    0.30 * s.blush, names, blur=0.05))
            if kind == "arm" and not sleeved:              # (shoulder blush)
                parts.append(self._soft("shoulder_blush", a + [0, -0.03 * self.u], 0.13, 0.11, "#f08f86", 0.16 * s.blush,
                                        names + ["trunk"], blur=0.05))
        if kind == "leg" and self.back and s.gloss > 0:        # the round of each buttock catches the light
            inner, down = self._inward(a, b, -1 if side == "left" else 1)
            c = a - inner * 0.12 * self.u + down * 0.05 * self.u
            parts.append(self._soft("buttock_light", c, 0.15, 0.17, "#fff6ec", 0.35 * s.gloss, names + ["trunk"],
                                    blend="screen", blur=0.06))
        if s.modeling > 0 and kind == "leg" and not self.side:
            # a narrow soft band along the inner thigh, starting below the crotch so the two legs'
            # bands do not pile up into a dark wedge there
            inner, rot = self._along(a, b, 0.34, -(-1 if side == "left" else 1) * 0.25)
            parts.append(self._soft("thigh_shade", inner, 0.06, 0.34, self._shadow(0.9), 0.26 * s.modeling, names,
                                    rot=rot, blend="multiply", blur=0.08))
        return parts

    def rest_y(self):
        """Image y of the lowest point of the trunk: where a lying figure meets its couch."""
        return float(self.I(self._trunk_contour())[:, 1].max())

    def seat_y(self):
        """Image y of the seat surface for a seated pose."""
        return self.I(np.array([0.0, self.b["seat"][3]]))[1]

    def _seat(self):
        """Buttocks pressed on a seat: a wide flattened mass under the pelvis, cut flat at the seat."""
        s, u = self.s, self.u
        (cx, cy), half_w, half_h, _ = self.b["seat"]
        c = self.I(self.F("pelvis", (cx, cy)))[0]
        mass = ellipse(c[0], c[1], half_w * s.hip * u, half_h * u, self.tilt("pelvis"), n=48)
        mass[:, 1] = np.minimum(mass[:, 1], self.seat_y())
        self.geo["seat"] = mass
        return self._skin("seat", polys=[mass], bulge=0.6, joints=[(c[0], c[1] - 0.10 * u, 0.62 * u)],
                          shape_with=["trunk"], grow_from=("trunk", 0.06 * u))

    # ---- limbs ------------------------------------------------------------
    def _limb_ribbons(self, a, b, c, w1, w2, outer_is_a, thickness, split=False):
        """Forms for a two-bone limb a-b-c with (t, outer, inner) width keys per bone; split=True draws the two
        bones apart even when they line up on screen."""
        u = self.u
        l1, l2 = np.linalg.norm(b - a), np.linalg.norm(c - b)
        v1, v2 = (b - a) / max(l1, 1e-6), (c - b) / max(l2, 1e-6)
        bend = np.degrees(np.arccos(np.clip(v1 @ v2, -1, 1)))

        def keys(w, t0, t1, col):
            return [(t0 + (t1 - t0) * k[0], k[1 + col] * u * thickness) for k in w]
        oa, ia = (0, 1) if outer_is_a else (1, 0)
        if bend <= SHARP_BEND and not split:
            share = l1 / (l1 + l2)
            axis = chaikin(np.array([a, a + (b - a) * 0.7, b, b + (c - b) * 0.3, c]), 2)
            ka = keys(w1, 0, share, oa)[:-1] + keys(w2, share, 1, oa)
            kb = keys(w1, 0, share, ia)[:-1] + keys(w2, share, 1, ia)
            return [Ribbon(axis, ka, kb, step=4.0)]
        return [Ribbon(np.array([a, b]), keys(w1, 0, 1, oa), keys(w1, 0, 1, ia), step=4.0),
                Ribbon(np.array([b, c]), keys(w2, 0, 1, oa), keys(w2, 0, 1, ia), step=4.0)]

    def _leg(self, side):
        s, u, p, body = self.s, self.u, self.p, self.b
        sd = -1 if side == "left" else 1
        a, b, c = (self.joint(f"{k}_{side}") for k in ("hip", "knee", "ankle"))
        # the outer thigh starts where the hip contour of the trunk is, so the silhouette runs through
        hip_x = abs(float(self._wide(sd * body["pelvis"][HIP_WIDEST][0] * s.hip)))
        joint_x = abs(float(self._wide(sd * body["hip_joint"][0] * s.hip)))
        thin = 1 - FAR_LIMB * self.a if self._is_far(sd) else 1.0
        top = max(0.30, hip_x - joint_x) / (s.limb * thin)
        thigh_w = body["thigh_w"]
        thigh = [(t, o * (1 + (top / thigh_w[0][1] - 1) * max(0.0, 1 - t / 0.6)), i) for t, o, i in thigh_w]
        if self.a > 0 and not self._is_far(sd):              # near side: the buttock rounds the upper thigh
            thigh[1] = (thigh[1][0], thigh[1][1] + body["buttock"] * self.a, thigh[1][2])
        # an axis that runs down the screen has side A on screen-left: the outer side of the left leg
        # a thigh drawn much shorter than it is points at the viewer (seated, seen from the front): it is drawn
        # as a bent leg, the thigh in front with its rounded end as the knee, even though it lines up with the shin
        toward = not self.side and getattr(p, f"{side}_leg_scale")[0] < FORESHORTENED_THIGH
        if toward:                     # seen end on, the thigh keeps its mid girth down to the knee
            keys = np.array(thigh, float)
            mid_o, mid_i = (float(np.interp(THIGH_GIRTH_T, keys[:, 0], keys[:, k])) for k in (1, 2))
            thigh = [(t, max(o, mid_o), max(i, mid_i)) for t, o, i in thigh]
        ribbons = self._limb_ribbons(a, b, c, thigh, body["shin_w"], outer_is_a=(sd < 0), thickness=s.limb * thin,
                                     split=toward)
        self.geo["limbs"][("leg", side)] = dict(a=a, b=b, c=c, upper=thigh, lower=body["shin_w"], thick=s.limb * thin,
                                                outer_is_a=(sd < 0), bent=len(ribbons) == 2, toward=toward)
        ribbons[0].round_start = False                       # cut flat at the hip joint: above it the trunk draws the hip
        # remember the outer contour of the thigh (figure space): a dress over the hips follows it
        r0 = ribbons[0]
        span = np.linalg.norm(b - a) / (np.linalg.norm(b - a) + (np.linalg.norm(c - b) if len(ribbons) == 1 else 0.0))
        outer, inner = (r0.side_a, r0.side_b) if sd < 0 else (r0.side_b, r0.side_a)
        self.thigh_outer[side] = ((outer - self.I(np.zeros(2))) / u, r0.t / span)
        self.thigh_inner[side] = ((inner - self.I(np.zeros(2))) / u, r0.t / span)
        turn = getattr(p, f"{side}_foot_turn")
        view = "side" if turn >= 40 else ("back" if self.back else "front")
        shin = c - b                                         # the foot turns with the shin (a lying leg)
        phi = float(np.arctan2(-shin[0], shin[1]))
        if view == "front":                                  # big toe on the inner side, toes turned out
            foot = FootSpec(x=c[0], y=c[1], unit=u, angle=phi + np.radians(-sd * turn), mirror=(sd < 0), view=view)
        elif view == "back":                                 # the heel straight under the ankle
            foot = FootSpec(x=c[0], y=c[1], unit=u, angle=phi, mirror=(sd < 0), view=view)
        else:                                                # toes point outward and a little down
            foot = FootSpec(x=c[0], y=c[1], unit=u, angle=phi + sd * np.radians(90 - turn) * 0.5, mirror=(sd > 0),
                            view=view)
        foot.skin, foot.line, foot.group, foot.merge, foot.scale = s.skin, s.line, "body", self.MERGE, body["foot"]
        foot.shoe, foot.shoe_color = s.shoes, s.cloth3
        foot = Foot(foot)
        self.sole[side] = foot.sole_y()
        parts = []
        for k, r in enumerate(ribbons):
            polys = r.polys() + ([foot.outline()] if k == len(ribbons) - 1 else [])
            extra = {}
            if k == 0:                                       # the thigh grows out of the pelvis
                # rounded with the trunk only: each thigh keeps its own inner rim of shade, so two touching
                # legs still read as two. The joint zone stops short of the crotch, so the line between the
                # thighs starts right below it
                extra = dict(joints=[(a[0], a[1], THIGH_JOINT * u)], grow_from=("trunk", 0.07 * u),
                             shape_with=["trunk"])
            else:
                extra = dict(joints=[(b[0], b[1], 0.20 * u)])
            parts.append(self._skin(f"leg_{side}_{k}", polys=polys, bulge=LEG_BULGE[k == 0], focus=0.35, **extra))
        if len(parts) == 2:
            # a sharply bent leg (seated, kneeling): the thigh comes toward the viewer, so it is drawn in
            # front and its rounded end is the knee
            parts = parts[::-1]
        elif s.detail and self.back:
            inner, down = self._inward(a, b, sd)              # the crease behind the knee, the calf's inner head
            parts[-1].strokes.append(self._landmark([b + inner * 0.08 * u + down * 0.02 * u, b + down * 0.04 * u,
                                                     b - inner * 0.08 * u + down * 0.02 * u], 1.2))
            inner2, down2 = self._inward(b, c, sd)
            parts[-1].strokes.append(self._landmark([b + down2 * 0.18 * u + inner2 * 0.12 * u,
                                                     b + down2 * 0.45 * u + inner2 * 0.13 * u,
                                                     b + down2 * 0.80 * u + inner2 * 0.06 * u]))
        elif s.detail:
            arc = np.array([b + [-0.075 * u, 0.035 * u], b + [0.0, 0.085 * u], b + [0.075 * u, 0.035 * u]])
            parts[-1].strokes.append(Stroke(catmull_rom(arc, samples=8), width=1.3 * self.px, color=self._shadow(), alpha=0.38))
            inner, down = self._inward(a, b, sd)              # the teardrop of the inner thigh muscle above the knee
            parts[-1].strokes.append(self._landmark([b - down * 0.34 * u + inner * 0.10 * u,
                                                     b - down * 0.15 * u + inner * 0.165 * u,
                                                     b - down * 0.02 * u + inner * 0.14 * u]))
        if s.detail and self.back:
            inner, down = self._inward(a, b, sd)              # the fold under the buttock, across the top of the thigh
            thigh = parts[-1] if len(parts) == 2 else parts[0]
            top = a + down * 0.30 * u
            thigh.strokes.append(self._landmark([top + inner * 0.30 * u - down * 0.02 * u, top + down * 0.05 * u,
                                                 top - inner * 0.25 * u - down * 0.06 * u], 1.6))
        if s.detail:                                          # ankle bones: the inner one sits higher
            inner, down = self._inward(b, c, sd)
            shin_part = parts[0] if len(parts) == 2 else parts[-1]
            for side_k, lift, r in ((1, 0.05, 0.032), (-1, 0.0, 0.028)):
                o = c + inner * side_k * 0.075 * u - down * lift * u
                shin_part.strokes.append(self._landmark([o - down * r * u, o + (inner * side_k - down) * 0.7 * r * u,
                                                         o + inner * side_k * r * u], 0.9))
        return parts + foot.toe_parts()

    def _arm(self, side):
        s, u, p = self.s, self.u, self.p
        sd = -1 if side == "left" else 1
        a, b, c = (self.joint(f"{k}_{side}") for k in ("shoulder", "elbow", "wrist"))
        raised = self._raised(side)
        if raised and not self.back and getattr(p, f"{side}_hand") == "hidden":
            skull = self.joint("neck") - np.array([0.0, HIDDEN_SKULL_UP * u])
            c = c + (skull - c) * HIDDEN_REACH
        thin = 1 - FAR_LIMB * self.a if self._is_far(sd) else 1.0
        # for a raised arm the axis points up, which flips which side is the outer one
        start = a - (b - a) / np.linalg.norm(b - a) * 0.10 * u if raised else a       # a raised arm starts inside the trunk
        if not raised and not self._arm_in_front(side):
            # an arm behind the trunk shows only below the shoulder: its rounded top would bulge past
            # the trunk's shoulder line, so it starts lower
            start = a + (b - a) / np.linalg.norm(b - a) * 0.14 * u
        ribbons = self._limb_ribbons(start, b, c, self.b["upper_arm_w"], self.b["forearm_w"], (sd < 0) != raised,
                                     s.limb * thin)
        self.geo["limbs"][("arm", side)] = dict(a=a, b=b, c=c, upper=self.b["upper_arm_w"], lower=self.b["forearm_w"],
                                                thick=s.limb * thin, outer_is_a=(sd < 0) != raised, bent=len(ribbons) == 2)
        ribbons[0].round_start = not raised                  # ... with no ball below the armpit
        parts = []
        for k, r in enumerate(ribbons):
            if k == 0:                                       # the upper arm grows out of the shoulder
                extra = dict(joints=[(a[0], a[1], 0.30 * u)], grow_from=("trunk", 0.04 * u))
            else:
                extra = dict(joints=[(b[0], b[1], 0.15 * u)])
            parts.append(self._skin(f"arm_{side}_{k}", polys=r.polys(), bulge=0.9, focus=0.35, tags=(f"arm_{side}",), **extra))
        if s.detail and not raised:
            inner, d = self._inward(a, b, sd)
            arm_part = parts[0]
            # where the deltoid tucks into the arm, on the outer side; and the crease inside the elbow
            arm_part.strokes.append(self._landmark([a + d * 0.24 * u - inner * 0.15 * u, a + d * 0.38 * u - inner * 0.13 * u,
                                                    a + d * 0.50 * u - inner * 0.08 * u]))
            if self.back:                                    # the point of the elbow
                arm_part.strokes.append(self._landmark([b - inner * 0.05 * u - d * 0.03 * u, b + d * 0.02 * u,
                                                        b + inner * 0.05 * u - d * 0.03 * u], 0.9))
            else:
                arm_part.strokes.append(self._landmark([b + inner * 0.07 * u - d * 0.02 * u, b + inner * 0.03 * u + d * 0.015 * u,
                                                        b - inner * 0.01 * u + d * 0.025 * u], 0.8))
        if len(ribbons) == 2 and raised:                     # the forearm passes behind the upper arm and head
            parts = parts[::-1]
        if s.outfit == "open_shirt":                         # the sleeve lies right over the upper arm
            k = [q.name for q in parts].index(f"arm_{side}_0") + 1
            parts[k:k] = self._sleeve(side, a, b, thin)
        if s.outfit == "dressed" and s.upper:                # a top's sleeve stacks with its arm
            k = max(i for i, q in enumerate(parts) if q.name.startswith(f"arm_{side}_")) + 1
            parts[k:k] = garments.sleeve(self, s.upper, side)
        pose = getattr(p, f"{side}_hand")
        if pose not in HAND_POSES:
            raise ValueError(f"{side}_hand must be one of {HAND_POSES}")
        if pose != "hidden":
            direction = c - b
            curl = (0.1, 0.0, 0.0, 0.0, 0.0) if pose == "open" else (0.25, 0.30, 0.38, 0.46, 0.55)
            hand = Hand(HandSpec(x=c[0] - direction[0] * 0.02, y=c[1] - direction[1] * 0.02, length=self.b["arm"][2] * u,
                                 angle=np.arctan2(-direction[0], direction[1]) - np.radians(getattr(p, f"{side}_wrist")),
                                 mirror=(sd < 0) != self.back,              # from behind: the back of the hand
                                 spread=0.9 if pose == "open" else 0.04, open_wrist=True,
                                 curl=curl, skin=s.skin, nails=False, line=s.line, group="body",
                                 breadth=self.b["hand_breadth"],
                                 shape=pose if pose in ("fist", "point", "grip") else "natural"))
            hand_parts = hand.parts()
            item = getattr(s, f"{side}_item")
            if item and pose == "grip":                  # the held thing sits in the fist, the fingers wrap over it
                grip = hand.to_image([(0.0, GRIP_POINT)])[0]
                hand_parts = held.ITEMS[item](grip, u, f"held_{side}") + hand_parts
            for q in hand_parts:
                q.tags = (f"arm_{side}", f"hand_{side}")      # hand_*: a pair scene can move the hand
            parts += hand_parts
        return parts

    def _arm_in_front(self, side):
        choice = getattr(self.p, f"{side}_arm_front")
        if self.back:                                        # from behind, an arm across the front passes behind
            return True if choice is None else not choice
        if choice is not None:
            return choice
        return not self._is_far(-1 if side == "left" else 1)

    # ---- head and neck ----------------------------------------------------
    def _head(self):
        s, p = self.s, self.p
        neck = self.joint("neck")
        yaw = np.clip(np.radians(p.head_yaw) + p.turn * 0.42, -MAX_HEAD_YAW, MAX_HEAD_YAW)
        kw = dict(skin=s.skin, line=s.line, light_side=s.light_side)
        kw.update(self.b["head"])                           # sex defaults first, the caller's choices win
        kw.update(s.head)
        kw["view"] = "back" if self.back else ("side" if self.side else "front")
        if self.side:                                       # the skull sits forward of the neck, the face looks ahead
            kw["facing"] = self.fc
            neck = neck + [self.fc * SIDE_HEAD_FORWARD * self.u, 0.0]
            yaw = 0.0
        # the skull pivots on top of the neck; the neck follows the trunk and part of the head tilt
        sign = self.fc if self.side else 1.0
        pivot = neck + _rot(np.array([self.far * 0.05 * self.a, -HEAD_PIVOT_UP]) * self.u, (p.lean + p.head_tilt * 0.4) * sign)
        roll = np.radians((p.head_tilt + p.lean) * (self.fc if self.side else 1.0))
        return Head(HeadSpec(cx=pivot[0], top=pivot[1] - HEAD_PIVOT_V * self.u, size=self.u, yaw=yaw, roll=roll, **kw))

    def _neck(self, head):
        u = self.u
        top, base = head.neck_top(), self.joint("neck") + [0, 0.06 * u]
        ribbon = Ribbon(catmull_rom(np.array([top, (top + base) / 2, base]), samples=10),
                        [(t, w * u) for t, w in zip((0, 0.5, 0.85, 1), self.b["neck"])], step=4.0)
        strokes = []
        if self.s.sex == "male" and self.s.detail and not self.back and not self.side:   # the Adam's apple, high on the throat
            c = ribbon.axis[int(ribbon.n * 0.42)]
            arc = c + _rot(np.array([[-0.032, 0.010], [0.0, 0.024], [0.032, 0.010]]), self.p.lean) * u
            strokes.append(Stroke(catmull_rom(arc, samples=6), width=1.4 * self.px, color=self._shadow(), alpha=0.42))
        return self._skin("neck", ribbon=ribbon, flatness=1.2, fade_t=(0.0, 0.01, 0.70, 0.98),
                          joints=[(base[0], base[1], 0.26 * u)], strokes=strokes)

    # ---- outfit -----------------------------------------------------------
    def _bikini(self):
        s, u, px = self.s, self.u, self.px
        cloth = rgb(s.cloth)
        line = Line(1.7 * px * s.line, color=mix(cloth, "#0c0a14", 0.6))
        parts = []
        half = np.array(BRIEFS_BACK if self.back else BRIEFS)
        outline = np.vstack([half, (half * [-1, 1])[::-1]])
        briefs = catmull_rom(self.I(self.F("pelvis", outline, s.hip)), closed=True, samples=6)
        lower = ["trunk", "leg_left_0", "leg_right_0"]        # not the arms: cloth must not show on a hand at the hip
        parts.append(Part("briefs", cloth, polys=[briefs], material="cloth", bulge=0.5, clip=lower, line=line,
                          group="outfit"))
        if self.back:
            return parts + self._bikini_back(cloth, line)
        band = self.I(self.F("chest", [(-0.75, 1.02), (0.0, 1.05), (0.75, 1.02)], s.shoulder))
        straps = [Stroke(catmull_rom(band, samples=8), width=3.2 * px, color=cloth, taper=(False, False), clip=True)]
        for sd in sorted((-1, 1), key=lambda sd: not self._is_far(sd)):
            cup = catmull_rom(self._breast_shape(sd, CUP), closed=True, samples=6)
            apex = self._breast_shape(sd, [CUP[0]])[0]
            tie = self.I(self.F("chest", (sd * 0.17, -0.10), s.shoulder))[0]
            parts.append(Part(f"cup_{sd}", cloth, polys=[cup], material="cloth", bulge=0.85, line=line, cast=0.035 * u,
                              clip=["trunk", "breast_-1", "breast_1"],
                              group="outfit", strokes=[Stroke(np.array([apex, tie]), width=2.6 * px, color=cloth,
                                                              taper=(False, False))]))
        # the band under the bust is drawn on a carrier part so it can be clipped to the body
        carrier = Part("band", cloth, polys=[ellipse(*self.I(self.F("chest", (0, 1.03)))[0], 0.95 * u, 0.2 * u)],
                       shade=False, material="flat", alpha=0.0, clip="trunk", strokes=straps)
        return [carrier] + parts

    def _bikini_back(self, cloth, line):
        """The top from behind: a band across the back fastened in the middle, and the halter ties meeting
        in a bow at the nape."""
        s, u, px = self.s, self.u, self.px
        band = self.I(self.F("chest", [(-1.1, BIKINI_BACK_BAND + 0.02), (0.0, BIKINI_BACK_BAND), (1.1, BIKINI_BACK_BAND + 0.02)],
                             s.shoulder))
        strokes = [Stroke(catmull_rom(band, samples=8), width=4.0 * px, color=cloth, taper=(False, False), clip=True)]
        nape = self.I(self.F("chest", (0.0, -0.13), s.shoulder))[0]
        for sd in (-1, 1):
            tie = self.I(self.F("chest", [(sd * 0.20, -0.06), (sd * 0.09, -0.12)], s.shoulder))
            strokes.append(Stroke(np.vstack([tie, [nape]]), width=2.4 * px, color=cloth, taper=(False, False)))
            loop = nape + np.array([[0, 0], [sd * 0.05, -0.025], [sd * 0.06, 0.01], [0, 0]]) * u
            strokes.append(Stroke(catmull_rom(loop, samples=5), width=2.0 * px, color=cloth, taper=(False, False)))
            end = nape + np.array([[0, 0], [sd * 0.02, 0.05], [sd * 0.03, 0.09]]) * u
            strokes.append(Stroke(end, width=1.8 * px, color=cloth, taper=(False, True)))
        clasp = self.I(self.F("chest", (0.0, BIKINI_BACK_BAND), s.shoulder))[0]
        strokes.append(Stroke(np.array([clasp - [0.03 * u, 0], clasp + [0.03 * u, 0]]), width=5.0 * px,
                              color=mix(cloth, "#0c0a14", 0.3), taper=(False, False), clip=True))
        carrier = Part("band", cloth, polys=[ellipse(*self.I(self.F("chest", (0, BIKINI_BACK_BAND)))[0], 1.2 * u, 0.6 * u)],
                       shade=False, material="flat", alpha=0.0, clip="trunk", strokes=strokes[:1] + strokes[-1:])
        ties = Part("ties", cloth, polys=[ellipse(nape[0], nape[1], 0.3 * u, 0.2 * u)], shade=False, material="flat",
                    alpha=0.0, strokes=strokes[1:-1])
        return [carrier, ties]

    def _outfit_line(self, second=False):
        cloth = rgb(self.s.cloth)
        if second:
            cloth = rgb(self.s.cloth2) if self.s.cloth2 is not None else mix(cloth, "#141a26", 0.75)
        return cloth, Line(1.7 * self.px * self.s.line, color=mix(cloth, "#0c0a14", 0.6))

    def _skin_names(self):
        names = ["trunk", "breast_-1", "breast_1", "leg_left_0", "leg_right_0"]
        return names + (["seat"] if self.p.seated else [])

    def _half_chain(self, segments):
        """Right-half outline given as [(frame, points), ...] -> figure space points, plus the mirrored left half."""
        s = self.s
        scale = dict(chest=s.shoulder, waist=s.waist, pelvis=s.hip)
        right = np.vstack([self.F(frame, pts, scale[frame]) for frame, pts in segments])
        left_local = [(frame, [(-x, y) for x, y in pts]) for frame, pts in segments]
        left = np.vstack([self.F(frame, pts, scale[frame]) for frame, pts in left_local])
        return right, left

    def _breast_cloth(self, cloth, owner, merge, cast, line_alpha=0.7, bulge=0.85):
        """The bust under a garment: the breast outline in cloth, clipped to the garment, rounded on its own."""
        if self.side:
            return self._side_bust_cloth(cloth, owner, merge, cast, line_alpha, bulge)
        s, u = self.s, self.u
        line = self._outfit_line()[1]
        line.alpha = line_alpha
        parts = []
        for sd in sorted((-1, 1), key=lambda sd: not self._is_far(sd)):
            outline = catmull_rom(self._breast_shape(sd, BREAST), closed=True, samples=8)
            top = self._breast_shape(sd, [(0.0, -0.30)])[0]
            parts.append(Part(f"{owner}_bust_{sd}", cloth, polys=[outline], material="cloth", bulge=bulge, fitted=True,
                              clip=owner, merge=merge, cast=cast * u, group="outfit",
                              erase=[(ellipse(top[0], top[1], 0.46 * s.bust * u, 0.27 * s.bust * u), 0.10 * u)],
                              joints=[(top[0], top[1], 0.40 * s.bust * u)], line=line))
        return parts

    def _suit(self, under):
        """One-piece swimsuit fitted to the body: neckline, straps, armholes and leg cut are drawn,
        everything else follows the skin outline."""
        kind = (SUITS_BACK if self.back else SUITS)[self.s.outfit]
        cloth, line = self._outfit_line()
        segments = [("chest", kind["neck"] + SUIT_STRAP + SUIT_ARMHOLE), ("waist", SUIT_SIDE["waist"]),
                    ("pelvis", SUIT_SIDE["pelvis"] + kind["cut"])]
        right, left = self._half_chain(segments)
        loop = np.vstack([right, left[::-1][1:-1]])             # the center points are shared by both halves
        poly = catmull_rom(self.I(loop), closed=True, samples=5)
        suit = Part("suit", cloth, polys=[poly], material="cloth", bulge=0.6, fitted=True, merge="suit", line=line,
                    clip=self._skin_names(), under=under, group="outfit")
        parts = [suit] + ([] if self.back else self._breast_cloth(cloth, "suit", "suit", 0.025))
        for p in parts[1:]:
            p.under = under
        parts += self._cloth_sheen(cloth, ["suit"] + [p.name for p in parts[1:]])
        return parts

    def _slip(self, under):
        """Slip dress: thin straps, a neckline across the bust, a body that drops straight from the bust
        past the waist, and a hem across both thighs. It is its own silhouette, not clipped to the body."""
        s, u, px, j = self.s, self.u, self.px, self.j
        cloth, line = self._outfit_line()
        neck = SLIP_NECK_BACK if self.back else SLIP_NECK
        right, left = self._half_chain([("chest", neck + SLIP_SIDE["chest"]), ("waist", SLIP_SIDE["waist"]),
                                        ("pelvis", SLIP_SIDE["pelvis"])])
        # below the widest point of the hip the dress follows the outer thigh, eased out a little, so the
        # legs never poke through its sides; it ends at the hem, a straight cut across both thighs
        sides, hem_c = {}, {}
        for sd, n in ((-1, "left"), (1, "right")):
            pts_out, frac = self.thigh_outer[n]
            keep = (frac > 0.10) & (frac <= SLIP_HEM)
            hem_c[sd] = j[f"hip_{n}"] + (j[f"knee_{n}"] - j[f"hip_{n}"]) * SLIP_HEM
            ease = pts_out[keep] + (pts_out[keep] - hem_c[sd]) * 0.03
            sides[sd] = ease[::max(1, len(ease) // 6)]
        mid = (hem_c[1] + hem_c[-1]) / 2 + np.array([0.0, 0.04])
        right_chain = catmull_rom(self.I(np.vstack([right, sides[1]])), samples=6)
        left_chain = catmull_rom(self.I(np.vstack([left, sides[-1]])), samples=6)
        hem_line = catmull_rom(np.vstack([right_chain[-1], self.I(mid), left_chain[-1]]), samples=10)
        poly = np.vstack([right_chain, hem_line[1:-1], left_chain[::-1][:-1]])

        # straps over the shoulders, folds falling from the bust and from the hips
        strokes = []
        for sd in (-1, 1):
            strap = self.I(self.F("chest", [(sd * 0.30, 0.37), (sd * 0.31, 0.10), (sd * 0.30, -0.07)], s.shoulder))
            strokes.append(Stroke(catmull_rom(strap, samples=6), width=2.4 * px, color=cloth, taper=(False, False)))
        fold = mix(cloth, "#0c0a14", 0.45)
        for sd in (-1, 1):                                   # satin pulls from the bust point and from the hip
            top = self.F("chest", (sd * 0.22, 1.08), s.shoulder)[0]
            low = self.F("waist", (sd * 0.16, 0.30))[0]
            strokes.append(Stroke(catmull_rom(self.I(np.vstack([top, (top + low) / 2 + [sd * 0.03, 0], low])), samples=8),
                                  width=1.2 * px, color=fold, alpha=0.25, feature=False, clip=True))
            hip = self.F("pelvis", (sd * 0.62, 0.10), s.hip)[0]
            low = hem_c[sd] + (hem_c[-sd] - hem_c[sd]) * 0.30 + np.array([0.0, -0.03])
            strokes.append(Stroke(catmull_rom(self.I(np.vstack([hip, (hip + low) / 2 + [sd * 0.02, 0], low])), samples=8),
                                  width=1.2 * px, color=fold, alpha=0.25, feature=False, clip=True))
        dress = Part("slip", cloth, polys=[poly], material="cloth", bulge=0.55, line=line, under=under, group="outfit",
                     strokes=strokes, cast=0.02 * u)
        parts = [dress] + ([] if self.back else self._breast_cloth(cloth, "slip", "slip_bust", 0.015, line_alpha=0.30, bulge=0.6))
        for p in parts[1:]:
            p.under = under
        parts += self._cloth_sheen(cloth, ["slip"] + [p.name for p in parts[1:]], satin=True)
        return parts

    def _cloth_sheen(self, cloth, names, satin=False):
        """Highlights on the cloth: a long sheen on the light side, and a glint on each breast."""
        s, ls = self.s, self.s.light_side
        light = mix(cloth, "#ffffff", 0.75)
        amount = (0.55 if satin else 0.35) * max(s.gloss, 0.3)
        parts = []
        side = self.I(self.F("waist", (ls * 0.30, 0.10)))[0]
        parts.append(self._soft("cloth_sheen", side, 0.07, 0.95 if satin else 0.55, light, amount, names,
                                rot=self.tilt("waist"), blend="screen", blur=0.05))
        for sd in (() if self.back or self.side else (-1, 1)):
            c = self._breast_shape(sd, [(ls * sd * 0.09, -0.06)])[0]
            parts.append(self._soft("cloth_glint", c, 0.08 * s.bust, 0.06 * s.bust, light, amount * 1.2, names,
                                    blend="screen", blur=0.03))
        return parts

    def _ease(self, pts, a, b, amount):
        """Push contour points (figure space) away from the bone a-b: loose cloth stands off the limb."""
        d = b - a
        d = d / max(np.linalg.norm(d), 1e-9)
        rel = pts - a
        off = rel - np.outer(rel @ d, d)
        return pts + off / np.maximum(np.linalg.norm(off, axis=1, keepdims=True), 1e-9) * np.asarray(amount)[:, None]

    def _swim_briefs(self):
        s, px = self.s, self.px
        cloth, line = self._outfit_line()
        half = np.array(BRIEFS_M)
        outline = np.vstack([half, (half * [-1, 1])[::-1]])
        poly = catmull_rom(self.I(self.F("pelvis", outline, s.hip)), closed=True, samples=6)
        band = self.I(self.F("pelvis", [(-1.0, -0.33), (0.0, -0.335), (1.0, -0.31)], s.hip))
        strokes = [Stroke(catmull_rom(band, samples=8), width=1.3 * px, color=mix(cloth, "#0c0a14", 0.5), alpha=0.6,
                          feature=False, clip=True)]
        return [Part("briefs", cloth, polys=[poly], material="cloth", bulge=0.5, clip=["trunk", "leg_left_0", "leg_right_0"],
                     line=line, group="outfit", strokes=strokes)]

    def _trunks_shape(self):
        """Swim shorts: a band over the pelvis down to the crotch, and a loose tube down each thigh to the hem.
        Drawn as separate polygons filled as one, so overlapping legs in a three-quarter view stay solid."""
        s, j = self.s, self.j
        hem, rise = TRUNKS["hem"], TRUNKS["rise"]
        pelvis = self.b["pelvis"]
        right = [TRUNKS["waist"][0], (pelvis[1][0] + 0.015, TRUNKS["waist"][1][1]), (pelvis[2][0] + 0.03, pelvis[2][1]),
                 (pelvis[3][0] + 0.03, pelvis[3][1]), (0.0, rise)]
        band = np.vstack([self.F("pelvis", right, s.hip), self.F("pelvis", [(-x, y) for x, y in right[::-1][1:-1]], s.hip)])
        polys, hem_pts = [self.I(catmull_rom(band, closed=True, samples=6))], {}
        for n in ("left", "right"):
            a, b = j[f"hip_{n}"], j[f"knee_{n}"]
            sides = []
            for contour in (self.thigh_outer[n], self.thigh_inner[n]):
                pts, frac = contour
                keep = frac <= hem
                ease = 0.03 + 0.02 * frac[keep] / hem                       # the leg opening stands off a little
                sides.append(self._ease(pts[keep], a, b, ease)[::max(1, keep.sum() // 8)])
            outer, inner = sides
            down = (b - a) / max(np.linalg.norm(b - a), 1e-9)
            inner[-1] = inner[-1] - down * 0.05                          # the leg opening rises toward the inseam
            mid = (outer[-1] + inner[-1]) / 2 + down * 0.02
            hem_line = np.vstack([outer[-1], mid, inner[-1]])
            tube = np.vstack([catmull_rom(outer, samples=6), catmull_rom(hem_line, samples=6)[1:-1],
                              catmull_rom(inner, samples=6)[::-1]])
            polys.append(self.I(tube))
            hem_pts[n] = (outer[-1], inner[-1])
        if self.p.seated:                                   # cloth under the buttocks ends at the seat
            seat = self.seat_y()
            polys = [np.stack([q[:, 0], np.minimum(q[:, 1], seat)], 1) for q in polys]
        return polys, hem_pts

    def _swim_trunks(self):
        s, u, px = self.s, self.u, self.px
        cloth, line = self._outfit_line(second=s.outfit == "open_shirt")
        polys, hem_pts = self._trunks_shape()
        dark = mix(cloth, "#0c0a14", 0.5)
        strokes = []
        band = self.I(self.F("pelvis", [(-0.80, -0.31), (0.0, -0.325), (0.80, -0.31)], s.hip))
        strokes.append(Stroke(catmull_rom(band, samples=8), width=1.4 * px, color=dark, alpha=0.6, feature=False, clip=True))
        knot = self.F("pelvis", [(0.0, -0.35)], s.hip)[0]
        for sd in (() if self.back else (-1, 1)):             # drawstring ends hanging from the waistband
            cord = self.I(np.array([knot, knot + [sd * 0.03, 0.10], knot + [sd * 0.05, 0.20]]))
            strokes.append(Stroke(catmull_rom(cord, samples=6), width=1.6 * px, color=mix(cloth, "#ffffff", 0.7),
                                  alpha=0.9, taper=(False, True)))
        # the inseam seen from the front: one crease from the crotch down between the legs to the hem
        crotch = self.F("pelvis", [(0.0, TRUNKS["rise"] - 0.06)], s.hip)[0]
        hem_mid = (hem_pts["left"][1] + hem_pts["right"][1]) / 2
        if self.back:                                         # from behind: the seam down the seat
            crotch, hem_mid = self.F("pelvis", [(0.0, -0.30)], s.hip)[0], crotch
        strokes.append(Stroke(self.I(np.array([crotch, hem_mid])), width=1.5 * px, color=line.color, alpha=0.7,
                              taper=(True, False), clip=True))
        # inked as one surface: the band and the two leg tubes overlap, only their joint silhouette is drawn
        return [Part("trunks", cloth, polys=polys, material="cloth", bulge=0.5, line=line, group="outfit",
                     merge="trunks", strokes=strokes, cast=0.02 * u)]

    def _open_shirt(self):
        """An unbuttoned shirt: two panels hanging from the shoulders, open down the front. The sleeves are
        built with the arms (see _sleeve) so they stack with them."""
        s, u, px = self.s, self.u, self.px
        cloth, line = self._outfit_line()
        if self.back:
            return self._shirt_back(cloth, line)
        polys, strokes = [], []
        dark = mix(cloth, "#0c0a14", 0.45)
        for sd, n in ((-1, "left"), (1, "right")):
            shoulder = SHIRT["raised"] if self._raised(n) else SHIRT["shoulder"]
            chain = [("chest", shoulder + SHIRT["side"]["chest"]), ("waist", SHIRT["side"]["waist"]),
                     ("pelvis", SHIRT["side"]["pelvis"] + SHIRT["front"]["pelvis"]), ("waist", SHIRT["front"]["waist"]),
                     ("chest", SHIRT["front"]["chest"])]
            scale = dict(chest=s.shoulder, waist=s.waist, pelvis=s.hip)
            pts = np.vstack([self.F(frame, [(sd * x, y) for x, y in seg], scale[frame]) for frame, seg in chain])
            polys.append(catmull_rom(self.I(pts), closed=True, samples=5))
            # collar roll and the placket beside the open edge
            collar = self.F("chest", [(sd * 0.17, -0.13), (sd * 0.25, 0.08), (sd * 0.32, 0.32)], s.shoulder)
            strokes.append(Stroke(catmull_rom(self.I(collar), samples=6), width=1.5 * px, color=dark, alpha=0.55,
                                  feature=False, clip=True))
            placket = np.vstack([self.F("chest", [(sd * 0.42, 0.62), (sd * 0.43, 0.95)], s.shoulder),
                                 self.F("waist", [(sd * 0.44, 0.0)], s.waist), self.F("pelvis", [(sd * 0.46, -0.40)], s.hip)])
            strokes.append(Stroke(catmull_rom(self.I(placket), samples=6), width=1.1 * px, color=dark, alpha=0.35,
                                  feature=False, clip=True))
            for x0, x1 in ((0.62, 0.58), (0.78, 0.66)):     # drape folds falling from the chest to the hem
                fold = np.vstack([self.F("chest", [(sd * x0, 0.55)], s.shoulder), self.F("waist", [(sd * (x0 + x1) / 2, 0.0)], s.waist),
                                  self.F("pelvis", [(sd * x1, -0.12)], s.hip)])
                strokes.append(Stroke(catmull_rom(self.I(fold), samples=6), width=1.2 * px, color=dark, alpha=0.28,
                                      feature=False, clip=True))
        light = mix(cloth, "#ffffff", 0.55)
        for y in (0.70, 1.00):                               # buttons on the screen-left panel
            c = self.I(self.F("chest", [(-0.40, y)], s.shoulder))[0]
            strokes.append(Stroke(np.array([c - [0.012 * u, 0], c + [0.012 * u, 0]]), width=3.0 * px, color=light,
                                  alpha=0.9, taper=(False, False)))
        return [Part("shirt", cloth, polys=polys, material="cloth", bulge=0.45, line=line, merge="shirt",
                     group="outfit", strokes=strokes)]

    def _shirt_back(self, cloth, line):
        """The open shirt from behind is one closed panel: collar band at the nape, a yoke, a box pleat, and
        the shirttail hem dropping toward the middle."""
        s, px = self.s, self.px
        scale = dict(chest=s.shoulder, waist=s.waist, pelvis=s.hip)
        halves = []
        for sd, n in ((-1, "left"), (1, "right")):
            shoulder = SHIRT["raised"] if self._raised(n) else SHIRT["shoulder"]
            chain = [("chest", shoulder + SHIRT["side"]["chest"]), ("waist", SHIRT["side"]["waist"]),
                     ("pelvis", SHIRT["side"]["pelvis"] + [(0.64, 0.02), (0.32, 0.12), (0.0, 0.16)])]
            halves.append(np.vstack([self.F(frame, [(sd * x, y) for x, y in seg], scale[frame]) for frame, seg in chain]))
        loop = np.vstack([halves[1], halves[0][::-1][1:]])
        dark = mix(cloth, "#0c0a14", 0.45)
        strokes = []
        def stroke(frame_pts, alpha, width=1.2):
            pts = np.vstack([self.F(frame, p, scale[frame]) for frame, p in frame_pts])
            strokes.append(Stroke(catmull_rom(self.I(pts), samples=6), width=width * px, color=dark, alpha=alpha,
                                  feature=False, clip=True))
        stroke([("chest", [(-0.15, -0.08), (0.0, -0.06), (0.15, -0.08)])], 0.6, 1.5)        # collar band
        stroke([("chest", [(-1.0, 0.36), (0.0, 0.32), (1.0, 0.36)])], 0.45)                 # yoke
        for x in (-0.05, 0.05):
            stroke([("chest", [(x, 0.32), (x * 1.5, 0.75)])], 0.32)                        # box pleat
        for sd in (-1, 1):                                    # drape from the shoulder blades to the hem
            stroke([("chest", [(sd * 0.45, 0.45)]), ("waist", [(sd * 0.40, 0.0)]), ("pelvis", [(sd * 0.42, -0.05)])], 0.28)
        return [Part("shirt", cloth, polys=[catmull_rom(self.I(loop), closed=True, samples=5)], material="cloth",
                     bulge=0.45, line=line, merge="shirt", group="outfit", strokes=strokes)]

    def _sleeve(self, side, a, b, thin):
        """A rolled shirt sleeve over the upper arm: it starts above the shoulder joint to cover the deltoid
        and ends in a cuff."""
        s, u = self.s, self.u
        cloth, line = self._outfit_line()
        d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        start, end = a + d * 0.02 * u, a + (b - a) * SLEEVE_ROLL       # the round start caps the shoulder
        widths = self.b["upper_arm_w"]
        keys_a = [(t, w * 1.20 * u * s.limb * thin) for t, w, _ in widths]
        keys_b = [(t, w * 1.20 * u * s.limb * thin) for t, _, w in widths]
        sleeve = Ribbon(np.array([start, end]), keys_a, keys_b, step=4.0, round_start=True, round_end=False)
        cuff_end = end + d * 0.10 * u
        cuff = Ribbon(np.array([end - d * 0.02 * u, cuff_end]), [(0, keys_a[-1][1] * 1.08), (1, keys_a[-1][1] * 1.05)],
                      [(0, keys_b[-1][1] * 1.08), (1, keys_b[-1][1] * 1.05)], step=3.0, round_start=False, round_end=False)
        # filled as outlines and rounded like the panels beside it: a cylinder-shaded sleeve would show a dark
        # stripe down its shadow side that the broad, nearly flat panels do not have
        return [Part(f"sleeve_{side}", cloth, polys=sleeve.polys(), material="cloth", bulge=0.45, line=line,
                     merge="shirt", group="outfit", tags=(f"arm_{side}",)),
                Part(f"cuff_{side}", mix(cloth, "#ffffff", 0.08), polys=cuff.polys(), material="cloth", bulge=0.45,
                     line=line, merge="shirt", group="outfit", tags=(f"arm_{side}",))]

    def _outfit(self, under):
        if self.side:
            return self._side_outfit(under)
        outfit = self.s.outfit
        if outfit == "dressed":
            return garments.dress(self, under)
        if outfit in ("briefs", "trunks", "open_shirt"):
            parts = {"briefs": self._swim_briefs, "trunks": self._swim_trunks}.get(outfit, self._swim_trunks)()
            if outfit == "open_shirt":
                parts += self._open_shirt()
            for p in parts:
                p.under = under
            return parts
        if self.s.outfit == "bikini":
            parts = self._bikini()
            for p in parts:
                p.under = under
            return parts
        if self.s.outfit in SUITS:
            return self._suit(under)
        if self.s.outfit == "slip":
            return self._slip(under)
        return []

    # ---- assembly ---------------------------------------------------------
    def parts(self, inserts=None, overlays=None):
        """All parts, back to front.

        inserts: parts to place between the body and the arms in front of it (a desk the figure sits at:
        it hides the lap, the forearms rest on it). The arms in front are then inked on their own.
        overlays: parts in front of the arms but behind the face (a laptop lid in front of typing hands).
        Inserts and overlays keep their own names; the figure's parts take the FigureSpec.ident prefix."""
        external = {id(q) for q in list(inserts or []) + list(overlays or [])}
        if self.side:
            out = self._side_parts(inserts, overlays)
        else:
            out = self._front_parts(inserts, overlays)
        return self._namespace(out, external)

    def _namespace(self, parts, external):
        """Prefix every name and key of this figure's parts with its ident (nothing changes without one)."""
        tag = self.s.ident
        if not tag:
            return parts
        ns = lambda key: f"{tag}/{key}" if key else key
        for q in parts:
            if id(q) in external:
                continue
            q.name, q.group, q.merge = ns(q.name), ns(q.group), ns(q.merge)
            q.tags = tuple(ns(t) for t in q.tags)
            if isinstance(q.clip, str):
                q.clip = ns(q.clip)
            elif q.clip:
                q.clip = [ns(c) for c in q.clip]
            if q.under:
                q.under = [ns(k) for k in q.under]
            if q.shape_with:
                q.shape_with = [ns(k) for k in q.shape_with]
            if q.grow_from:
                q.grow_from = (ns(q.grow_from[0]), q.grow_from[1])
        return parts

    def _front_parts(self, inserts, overlays):
        p = self.p
        head = self._head()
        legs = {side: self._leg(side) for side in ("left", "right")}
        arms = {side: self._arm(side) for side in ("left", "right")}
        if self.a > 0.15:                                    # three-quarter: the near leg overlaps the far one
            near = "left" if self.far > 0 else "right"
        else:                                                # frontal: the weight-bearing leg sits in front
            near = "left" if p.pelvis_tilt >= 0 else "right"
        far = "right" if near == "left" else "left"
        out = list(head.back_parts())
        out += [a for side in ("left", "right") if not self._arm_in_front(side) for a in arms[side]]
        names = lambda parts: [q.name for q in parts if q.merge]
        out.append(self._trunk())
        if not self.back:                                    # from behind the chest is hidden
            out += self._pecs() if self.s.sex == "male" else self._breasts()
        out += self._trunk_accents()
        if p.seated:
            out.append(self._seat())
        out.append(self._neck(head))
        for side in (far, near):
            out += legs[side] + self._limb_accents("leg", side, names(legs[side]))
        front_arms = []
        for side in ("left", "right"):
            if self._arm_in_front(side):
                front_arms += arms[side] + self._limb_accents("arm", side, names(arms[side]))
        if inserts is None:
            front = [f"arm_{side}" for side in ("left", "right") if self._arm_in_front(side)]
            out += front_arms + self._outfit(front)          # clothes lie beneath the arms in front
        else:
            for q in front_arms:                             # inked apart from the body, which is inked before the inserts
                if q.merge == self.MERGE:
                    q.merge = self.MERGE + "_front_arms"
            out += self._outfit([]) + list(inserts) + front_arms
        out += list(overlays or [])
        out += head.front_parts()
        return out
