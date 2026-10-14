"""Body construction: neck, torso, limbs from a pose skeleton.

All coordinates are body-local (origin at the neck base, H units). Limbs
are ribbons around bone segments with anatomical width profiles, which is
the capsule-and-bone mannequin figure drawing starts from.

A pose is an arm setup per side plus a leg stance. Arms carry a forearm
placement that decides depth order ("front" over the torso, "behind" hidden
by it, "raised" drawn over everything including hair) and an optional hand
gesture rendered by the 3D hand model.
"""
import numpy as np

from . import color as col
from . import config as cfg
from . import backview, geom, hand, handheld, musculature, shapes
from .scene import Blend, Layer, LineSpec, Material, ShadeSpec

# torso silhouette per gender and figure, image-right half (x >= 0), neck base to crotch.
# The shoulder line is shared within a gender; ribcage taper, waist and hip flare differ.
SHOULDER_LINE = [(0.172, -0.01), (0.25, 0.050), (0.40, 0.115), (0.54, 0.175), (0.63, 0.225),
                 (0.685, 0.275), (0.705, 0.34), (0.65, 0.46)]
FIGURES = {
    "slim":     {"torso": [(0.585, 0.56), (0.570, 0.74), (0.545, 0.98), (0.480, 1.26), (0.445, 1.45), (0.490, 1.78),
                           (0.580, 2.10), (0.565, 2.30), (0.40, 2.46), (0.0, 2.50)], "hip_x": 0.275},
    "balanced": {"torso": [(0.585, 0.56), (0.560, 0.74), (0.525, 0.92), (0.455, 1.14), (0.405, 1.33), (0.392, 1.45),
                           (0.450, 1.70), (0.570, 1.98), (0.632, 2.13), (0.600, 2.33), (0.42, 2.47), (0.0, 2.50)],
                 "hip_x": 0.295, "thigh": 1.04},
    "fuller":    {"torso": [(0.590, 0.56), (0.565, 0.74), (0.520, 0.92), (0.440, 1.14), (0.380, 1.32), (0.365, 1.43),
                           (0.440, 1.68), (0.590, 1.96), (0.675, 2.13), (0.635, 2.34), (0.43, 2.48), (0.0, 2.50)],
                 "hip_x": 0.315, "thigh": 1.10},
}
# breast (center x, center y, radius x, radius y) of the image-right side: nearly round so the lower
# hemisphere reads as a ball; a fuller bust sits a little lower and further out
# large and xlarge reach past the ribcage line, so the outer curve shows in front of the arm
BUSTS = {"small": (0.255, 0.690, 0.225, 0.210), "medium": (0.285, 0.715, 0.275, 0.262),
         "large": (0.310, 0.735, 0.312, 0.300), "xlarge": (0.330, 0.760, 0.345, 0.335)}
BUST_BASE_Z, BUST_PROJECTION = 0.25, 0.60   # depth of the bust center: chest surface plus a share of the radius
BUST_CONTOUR_ARC = (165.0, -45.0)           # inked border: inner side, around the bottom, up the outer side
BUST_CREASE_ARC = (165.0, 5.0)              # under-bust crease: inner side to the outer side
BUST_SHEEN = 0.16                           # skin specular on the bust (reads as a glossy, round surface)
SKIN_FORM = 0.45                            # smooth form shading on bust, hips and muscle masses
HIP_DOME = (0.10, 2.08, 0.30, 0.40, 1.45)   # outward offset from the hip joint, center y, radii, dome scale
HIP_THRESHOLD = -0.30                       # hips get form shading only; a cel step there reads as a dark patch
BUST_SPHERE = 1.08      # sphere radius over the outline radius: the rim turns away so a shadow crescent forms
BUST_TOP_REACH = 1.30   # the upper slope runs this far above the center (in radius units) and fades into the chest
# the bust stands in front of the arms as a round mass; its long upper slope blends into the chest, and cutting
# sleeves with the slope notched the far sleeve of a 3/4-turned figure near the shoulder (v10 showcase).
# A flat cut instead of the round top left a square step in every sleeve (rejected after a render comparison).

# male V-taper: trapezius slope to wide deltoids, lats under the armpit, narrow waist
MALE_SHOULDER_LINE = [(0.235, -0.06), (0.31, -0.010), (0.45, 0.050), (0.62, 0.115), (0.77, 0.180),
                      (0.88, 0.255), (0.93, 0.36), (0.90, 0.50)]
MALE_FIGURES = {
    "slim":     {"torso": [(0.800, 0.62), (0.760, 0.80), (0.690, 1.00), (0.610, 1.24), (0.560, 1.44), (0.550, 1.64),
                           (0.560, 1.90), (0.570, 2.12), (0.550, 2.32), (0.38, 2.46), (0.0, 2.50)],
                 "hip_x": 0.275, "pecs": (0.300, 0.500, 0.290, 0.180)},
    "balanced": {"torso": [(0.880, 0.62), (0.860, 0.80), (0.780, 1.00), (0.660, 1.24), (0.585, 1.44), (0.570, 1.64),
                           (0.580, 1.88), (0.590, 2.12), (0.565, 2.32), (0.40, 2.46), (0.0, 2.50)],
                 "hip_x": 0.285, "pecs": (0.320, 0.510, 0.330, 0.215)},
    "athletic": {"torso": [(0.920, 0.62), (0.900, 0.80), (0.820, 1.00), (0.690, 1.24), (0.600, 1.44), (0.580, 1.64),
                           (0.590, 1.88), (0.595, 2.12), (0.570, 2.32), (0.40, 2.46), (0.0, 2.50)],
                 "hip_x": 0.290, "pecs": (0.335, 0.515, 0.350, 0.235)},
}
# pectoral plate outline in (radius x, radius y) units around the pec center, image-right side:
# clavicle edge on top, armpit fold on the outer side, firm lower border
PEC_PLATE = [(-0.95, -1.80), (0.10, -1.95), (0.80, -1.55), (1.25, -0.70), (1.20, 0.20), (0.90, 0.85),
             (0.30, 1.10), (-0.40, 1.10), (-0.90, 0.95), (-0.97, 0.00)]
PEC_LOWER = [(-0.90, 0.95), (-0.40, 1.10), (0.30, 1.10), (0.90, 0.85), (1.20, 0.20)]
PEC_DOME = (0.10, -0.30, 1.60, 1.80)   # dome center offset and radii (pec radius units): shadow band at the border
GENDER = {
    "female": {"shoulder": (0.605, 0.37), "neck": (0.150, 0.176), "hand": 1.00, "abs": False, "stance_x": 1.00},
    "male":   {"shoulder": (0.800, 0.40), "neck": (0.205, 0.235), "hand": 1.22, "abs": True, "stance_x": 1.22},
}
# arm joints are authored for the female shoulder; a wider frame moves elbows and wrists out by these shares
# (above 1, the arms hang slightly away from the body so the lats show below the armpits)
ELBOW_SHIFT, WRIST_SHIFT = 1.30, 1.10
BACK_CLASP = (0.17, 1.80)    # wrist of a hand held behind the back, seen from behind
BUST_CONTOUR_W = 0.0050   # lower-border line weight (H units)
FIGURE_FALLBACK = {"female": {"athletic": "balanced"}, "male": {"fuller": "athletic"}}
TORSO_R = SHOULDER_LINE + FIGURES["balanced"]["torso"]
SHOULDER = (0.605, 0.37)

# arm setups in image-right coordinates (x > 0); the image-left arm mirrors them
HANG_NORMAL = (-0.92, 0.0, -0.38)     # palm toward the thigh, thumb forward
ARMS = {
    "hang":       {"elbow": (0.735, 1.40), "wrist": (0.775, 2.28), "forearm": "front", "hand": "relaxed",
                   "palm": HANG_NORMAL},
    "hang_close": {"elbow": (0.690, 1.40), "wrist": (0.640, 2.25), "forearm": "front", "hand": "relaxed",
                   "palm": HANG_NORMAL},
    "behind":     {"elbow": (0.700, 1.36), "wrist": (0.420, 2.02), "forearm": "behind", "hand": None},
    "pocket":     {"elbow": (0.720, 1.40), "wrist": (0.300, 1.92), "forearm": "front", "hand": None},
    "wave":       {"elbow": (0.880, 1.22), "wrist": (1.000, 0.40), "forearm": "raised", "hand": "open",
                   "fingers": (0.06, -1.0, 0.05), "palm": (0.0, 0.0, 1.0)},
    "hip":        {"elbow": (1.080, 1.10), "wrist": (0.700, 1.52), "forearm": "front", "hand": "flat",
                   "fingers": (-0.10, 0.75, -0.65), "palm": (-0.95, 0.0, 0.20)},
    # gestures: wrist_shift 0 keeps a wrist where it touches the body or face on any frame width
    "cross":      {"elbow": (0.660, 1.30), "wrist": (-0.460, 1.17), "forearm": "front", "hand": "relaxed",
                   "fingers": (-0.60, -0.75, -0.25), "palm": (0.15, 0.10, -0.98), "wrist_shift": 0.0},
    "cross_under": {"elbow": (0.690, 1.38), "wrist": (-0.360, 1.27), "forearm": "front", "hand": None,
                    "wrist_shift": 0.0},
    "chin":       {"elbow": (0.540, 1.22), "wrist": (0.100, -0.06), "forearm": "raised", "hand": "fist",
                   "fingers": (-0.30, -0.90, -0.30), "palm": (-0.60, -0.20, -0.75), "wrist_shift": 0.0},
    "support":    {"elbow": (0.680, 1.36), "wrist": (-0.500, 1.28), "forearm": "front", "hand": None,
                   "wrist_shift": 0.0},
    "tuck":       {"elbow": (0.980, 0.25), "wrist": (0.400, -0.52), "forearm": "raised", "hand": "flat",
                   "fingers": (0.05, -1.0, -0.20), "palm": (-0.90, 0.0, -0.40), "wrist_shift": 0.0},
    "behind_head": {"elbow": (1.020, -0.42), "wrist": (0.180, -0.85), "forearm": "behind_head", "hand": None,
                    "wrist_shift": 0.0},
    # walking: the back arm swings out behind the hip, the front arm forward toward the midline
    "swing_back": {"elbow": (0.770, 1.40), "wrist": (0.900, 2.20), "forearm": "front", "hand": "relaxed",
                   "palm": HANG_NORMAL},
    "swing_fwd":  {"elbow": (0.690, 1.36), "wrist": (0.520, 2.12), "forearm": "front", "hand": "relaxed",
                   "palm": HANG_NORMAL},
    "rest_knee":  {"elbow": (0.720, 1.40), "wrist": (0.400, 2.42), "forearm": "front", "hand": "relaxed",
                   "fingers": (-0.20, 0.55, 0.80), "palm": (0.05, 0.85, -0.50)},
    "rest":       {"elbow": (0.700, 1.36), "wrist": (0.180, 1.55), "forearm": "front", "hand": "relaxed",
                   "fingers": (-0.95, 0.20, 0.15), "palm": (0.0, 0.25, -0.97), "wrist_shift": 0.0},
}
POSES = {
    "relaxed": ("hang", "hang"),           # (image-right arm, image-left arm)
    "close": ("hang_close", "hang_close"),
    "behind": ("behind", "behind"),
    "pocket": ("pocket", "pocket"),
    "wave": ("wave", "hang"),
    "hand_on_hip": ("hip", "hang"),
    "hands_on_hips": ("hip", "hip"),
    "arms_crossed": ("cross", "cross_under"),
    "chin_rest": ("chin", "support"),
    "hair_tuck": ("tuck", "hang"),
    "hands_behind_head": ("behind_head", "behind_head"),
    "walk": ("swing_back", "swing_fwd"),
    "lean": ("behind", "behind"),
    "sit": ("rest_knee", "rest_knee"),
    "lie": ("behind_head", "rest"),
}
# leg stances: per side (image-right, image-left) knee and ankle; pelvis tilt in degrees
HIP = (0.275, 2.14)
STANCES = {
    "straight":     {"tilt": 0.0, "R": {"knee": (0.215, 3.88), "ankle": (0.195, 5.32)},
                     "L": {"knee": (0.215, 3.88), "ankle": (0.195, 5.32)}},
    "contrapposto": {"tilt": 7.0, "R": {"knee": (0.215, 3.80), "ankle": (0.360, 5.22)},
                     "L": {"knee": (0.180, 3.90), "ankle": (0.085, 5.34)}},
    "wide":         {"tilt": 0.0, "R": {"knee": (0.290, 3.88), "ankle": (0.380, 5.30)},
                     "L": {"knee": (0.290, 3.88), "ankle": (0.380, 5.30)}},
    # the forward foot lands lower (nearer the viewer), the back foot is up on its toes
    "walk":         {"tilt": 3.0, "R": {"knee": (0.215, 3.90), "ankle": (0.250, 5.42)},
                     "L": {"knee": (0.190, 3.78), "ankle": (0.120, 5.08)}},
    # one knee bent with its foot against the wall behind: a short calf and a foreshortened raised foot
    "lean":         {"tilt": 5.0, "R": {"knee": (0.300, 3.72), "ankle": (0.250, 4.70)},
                     "L": {"knee": (0.190, 3.90), "ankle": (0.120, 5.34)}, "raised_foot": (1,)},
    # thighs point at the viewer: short in projection, knees face front, calves hang to the floor
    "sit":          {"tilt": 0.0, "R": {"knee": (0.300, 2.66), "ankle": (0.280, 4.12)},
                     "L": {"knee": (0.300, 2.66), "ankle": (0.280, 4.12)}, "knee_caps": True},
    "lie":          {"tilt": 0.0, "R": {"knee": (0.235, 3.88), "ankle": (0.280, 5.32)},
                     "L": {"knee": (0.200, 3.88), "ankle": (0.170, 5.32)}},
}
# shin shade of a front-view sitter: a band wider than the leg (the leg mask trims it) fading downward
LAP_SHADOW = {"start": 0.0, "core": 0.10, "long": 0.38, "feather": 0.06, "half": 1.2, "color": "#7A6A86",
              "core_opacity": 0.30, "long_opacity": 0.22}
RAISED_FOOT_SCALE = np.array([0.92, 0.78])   # a foot tipped back toward a wall is shorter from the front
POSE_STANCE = {"walk": "walk", "lean": "lean", "sit": "sit", "lie": "lie"}   # used unless a stance is given
UPPER_ARM_W = [0.300, 0.275, 0.245, 0.215, 0.195]
FOREARM_W = [0.210, 0.215, 0.180, 0.148, 0.128]
THIGH_W = [0.580, 0.530, 0.430, 0.340, 0.285]
CALF_W = [0.275, 0.315, 0.285, 0.210, 0.155, 0.140]
LIMB_WIDTHS = {
    "female": {"upper": UPPER_ARM_W, "lower": FOREARM_W, "thigh": THIGH_W, "calf": CALF_W},
    # deltoid cap, deltoid insertion dip, biceps bulge; brachioradialis near the elbow; quad sweep; calf belly
    "male":   {"upper": [0.420, 0.400, 0.360, 0.355, 0.360, 0.330, 0.285],
               "lower": [0.300, 0.330, 0.310, 0.260, 0.205, 0.185],
               "thigh": [0.660, 0.640, 0.600, 0.530, 0.450, 0.360],
               "calf": [0.360, 0.410, 0.430, 0.370, 0.280, 0.210, 0.190]},
}


def mirror(P):
    Q = geom.pts(P).copy()
    Q[:, 0] *= -1
    return Q


def front_z(x, half_width=0.62, depth=0.26):
    """Depth of the torso front surface at body-local x (elliptic section)."""
    return depth * np.sqrt(np.clip(1 - (np.asarray(x) / half_width) ** 2, 0, 1))


def limb(a, b, widths, expand=0.0, bend=0.0):
    """Closed ribbon between joints a and b with round caps."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    n = np.array([-(b - a)[1], (b - a)[0]])
    mid = (a + b) / 2 + n * bend
    spine = geom.resample(geom.bezier(a, (a + mid) / 2, (mid + b) / 2, b, 32), 0.01)
    t = np.linspace(0, 1, len(spine))
    w = np.interp(t, np.linspace(0, 1, len(widths)), widths) + 2 * expand
    return [geom.stroke_outline(spine, w), geom.ellipse(*a, w[0] / 2, w[0] / 2, 32),
            geom.ellipse(*b, w[-1] / 2, w[-1] / 2, 32)]


class BodyBuilder:
    def __init__(self, rig, spec):
        self.rig = rig
        self.s = spec
        self.H = rig.H
        self.skin = col.hex_rgb(spec["skin"])
        self.line = LineSpec(cfg.LINE_BODY * self.H)
        right, left = POSES.get(spec.get("pose", "relaxed"), POSES["relaxed"])
        if spec.get("_mirror_pose"):
            right, left = left, right   # a two-figure contact keeps the posed arm on the outer side
        self.arms = {1: dict(ARMS[right]), -1: dict(ARMS[left])}
        for key, side in (("right", 1), ("left", -1)):
            g = (spec.get("hands") or {}).get(key)
            if g and self.arms[side]["hand"]:
                self.arms[side]["hand"] = g
        stance = spec.get("stance", "straight")
        if stance == "straight":
            stance = POSE_STANCE.get(spec.get("pose"), stance)
        self.stance_name = stance
        self.stance = STANCES.get(stance, STANCES["straight"])
        # seen from behind, forearms in front of the torso go behind it and the reverse;
        # hands that were hidden behind the back become visible
        self.back = spec.get("view", "front") == "back"
        if self.back:
            for a in self.arms.values():
                if a["forearm"] == "behind":
                    a["forearm"] = "front"
                    a["hand"] = a["hand"] or "relaxed"
                    a["wrist"] = BACK_CLASP     # hands meet at the small of the back
                    a["wrist_shift"] = 0.0
                elif a["forearm"] == "front":
                    a["forearm"] = "behind"
        self.gender = spec.get("gender", "female")
        g = GENDER[self.gender]
        name = spec.get("figure", "balanced")
        name = FIGURE_FALLBACK[self.gender].get(name, name)
        if self.gender == "male":
            fig = MALE_FIGURES[name]
            muscle = spec.get("muscle")
            self.muscle = float(muscle) if muscle is not None else musculature.MUSCLE_BY_FIGURE[name]
            self.torso_r = MALE_SHOULDER_LINE + fig["torso"]
            self.bust = fig["pecs"]       # pectorals reuse the bust geometry (center, radii)
        else:
            fig = FIGURES[name]
            self.muscle = 0.0
            self.torso_r = SHOULDER_LINE + fig["torso"]
            self.bust = BUSTS.get(spec.get("bust", "medium"), BUSTS["medium"])
        self.hip = (fig["hip_x"], HIP[1])
        self.shoulder = np.array(g["shoulder"])
        self.neck_w = g["neck"]
        self.hand_scale = g["hand"]
        self.abs = g["abs"]
        # stances are authored for the female figure; a male stance sets the knees apart
        self.leg_spread = np.array([g["stance_x"], 1.0])
        self.widths = dict(LIMB_WIDTHS[self.gender])
        if "thigh" in fig:
            self.widths["thigh"] = [w * fig["thigh"] for w in self.widths["thigh"]]
        dx = self.shoulder[0] - SHOULDER[0]
        for a in self.arms.values():
            a["elbow"] = (a["elbow"][0] + dx * ELBOW_SHIFT, a["elbow"][1])
            a["wrist"] = (a["wrist"][0] + dx * WRIST_SHIFT * a.get("wrist_shift", 1.0), a["wrist"][1])
        # a held object takes one arm (front views; the back and side views keep their pose)
        hold = spec.get("hold") or {}
        self.hold = None
        if hold.get("item") in handheld.ITEMS and spec.get("view", "front") == "front":
            side = 1 if hold.get("side", "right") == "right" else -1
            arm = dict(ARMS["hang"], **handheld.HOLD_ARMS[hold["item"]])
            dx = self.shoulder[0] - SHOULDER[0]      # a wider male frame moves the elbow (and a free wrist) out
            arm["elbow"] = (arm["elbow"][0] + dx * ELBOW_SHIFT, arm["elbow"][1])
            arm["wrist"] = (arm["wrist"][0] + dx * WRIST_SHIFT * arm.get("wrist_shift", 1.0), arm["wrist"][1])
            self.arms[side] = arm
            self.hold = (side, hold["item"])
        # contact arms of a two-figure picture: joints already solved in this body's local space
        for side, arm in (spec.get("_arms") or {}).items():
            self.arms[side] = dict(arm)
        self.tilt = np.radians(self.stance["tilt"])
        # the pose of the image-right arm stays the reference for outfits
        self.pose = self.arms[1]

    # ------------------------------------------------------------ geometry (body-local)
    def pelvis(self, P):
        """Contrapposto hip tilt as a vertical shear below the waist.

        How: a rotation would swing hems and legs sideways like a pendulum;
        a shear only raises one hip and lowers the other, which is what the
        eye reads as weight shift. Identity for a straight stance.
        """
        P = geom.pts(P).copy()
        if self.tilt == 0:
            return P
        s = geom.smoothstep(1.25, 1.95, P[:, 1])
        P[:, 1] -= P[:, 0] * np.tan(self.tilt) * s
        return P

    def torso_local(self, expand=0.0, top=None, bottom=None, hem_curve=0.03):
        R = np.array(self.torso_r)
        if top is not None:
            R[0, 1] = top
        P = np.vstack([R, mirror(R[::-1])[1:]])
        P = geom.catmull_rom(P, 8, closed=True)
        if expand:
            P = geom.offset_closed(P, expand)
        if bottom is not None:
            keep = P[:, 1] <= bottom
            split = np.argmax(~keep)
            right, left = P[:split], P[keep][split:]
            xr = right[-1, 0]
            hx = np.linspace(xr, left[0, 0], 24)
            hem = np.column_stack([hx, bottom + hem_curve * (1 - (hx / max(abs(xr), 1e-6)) ** 2)])
            P = np.vstack([right, hem, left])
        return self.pelvis(P)

    def joints(self, side):
        a = self.arms[side]
        m = np.array([side, 1.0])
        return self.shoulder * m, np.array(a["elbow"]) * m, np.array(a["wrist"]) * m

    def arm_local(self, side, part, expand=0.0):
        s, e, w = self.joints(side)
        a, b = (s, e) if part == "upper" else (e, w)
        return limb(a, b, self.widths[part], expand)

    def leg_joints(self, side):
        key = "R" if side > 0 else "L"
        m = np.array([side, 1.0])
        hip = self.pelvis([np.array(self.hip) * m])[0]
        m = m * self.leg_spread
        return hip, np.array(self.stance[key]["knee"]) * m, np.array(self.stance[key]["ankle"]) * m

    def leg_local(self, side, part, expand=0.0):
        hip, knee, ankle = self.leg_joints(side)
        a, b = (hip, knee) if part == "thigh" else (knee, ankle)
        return limb(a, b, self.widths[part], expand, bend=0.02 if part == "calf" else 0.0)

    def neck_canvas(self):
        nt, nb = self.neck_w
        top = self.rig.head([(-nt, 0.78, -0.02), (nt, 0.78, -0.02)])
        bot = self.rig.body2([(-nb, 0.06), (nb, 0.06)])
        mid = (top + bot) / 2
        mid[:, 0] = (mid[:, 0] - mid.mean(axis=0)[0]) * 0.97 + mid.mean(axis=0)[0]
        P = np.array([top[0], mid[0], bot[0], bot[1], mid[1], top[1]])
        return geom.catmull_rom(P, 10, closed=True)

    def to_canvas(self, P, z=0.0):
        return self.rig.body2(P, z)

    def _skin(self, name, polys, inflate=0.07, cast=("head", "hair_front", "garment_top"), tags=("body",)):
        return Layer(name, Material.SKIN, self.skin, polys=polys, line=self.line,
                     shade=ShadeSpec(inflate=inflate * self.H, cast_tags=cast, cast_dist=0.085 * self.H,
                                     threshold=0.12, rim=0.5), tags=tags)

    # ------------------------------------------------------------ layers
    def skin_layers(self, include_legs=False, exposed=False):
        """Neck, torso, upper arms (and legs) as one silhouette.

        Legs join the torso so a bare body has one outline: drawn separately,
        the torso's lower edge would run across the thighs. An exposed torso
        gets a wide bevel so it shades round like a cylinder.
        """
        polys = [self.neck_canvas(), self.to_canvas(self.torso_local())]
        for side in (-1, 1):
            polys += [self.to_canvas(p) for p in self.arm_local(side, "upper")]
            if include_legs:
                polys += [self.to_canvas(p) for part in ("thigh", "calf") for p in self.leg_local(side, part)]
        cast = ("head", "hair_front", "garment_top", "skirt", "swim_top")
        uppers = [self.to_canvas(p) for side in (-1, 1) for p in self.arm_local(side, "upper")]
        layers = []
        arm_cut = ()
        if self.has_bust:
            busts = self.bust_polys()
            polys += busts          # the bust's outer curve belongs to the silhouette from either side
            layers.append(Layer("bust_mask", Material.FLAT, self.skin, polys=busts, opacity=0.0))
            if self.bust_in_front:
                # the bust projects in front of the arms: arm masks exclude it so garments and
                # straps over the bust are not cut where it overlaps an arm
                layers.append(Layer("bust_front_mask", Material.FLAT, self.skin, polys=self.bust_front_polys(),
                                    opacity=0.0))
                arm_cut = ("bust_front_mask",)
        return layers + [self._skin("body_skin", polys, inflate=0.15 if exposed else 0.07, cast=cast),
                         Layer("neck_mask", Material.FLAT, self.skin, polys=[self.neck_canvas()], opacity=0.0),
                         Layer("torso_mask", Material.FLAT, self.skin, polys=[polys[1]], opacity=0.0),
                         Layer("upper_arm_mask", Material.FLAT, self.skin, polys=uppers, cut=arm_cut, opacity=0.0)]

    @property
    def has_bust(self):
        return self.gender == "female"

    @property
    def bust_in_front(self):
        """The bust is nearer the viewer than the arms (front views only)."""
        return self.has_bust and not self.back

    def bust_z(self):
        return BUST_BASE_Z + BUST_PROJECTION * self.bust[3]

    def bust_polys(self, grow=0.0):
        return [self.to_canvas(self.bust_shape(side, grow), self.bust_z()) for side in (-1, 1)]

    def bust_front_polys(self):
        """The forward-projecting part of each breast: its round outline without the long upper slope."""
        cx, cy, rx, ry = self.bust
        return [self.to_canvas(geom.ellipse(side * cx, cy, rx, ry, 72), self.bust_z()) for side in (-1, 1)]

    def lap_shadow_layers(self):
        """Seated, seen from the front: the lap shades the shins right below the knees.

        Why: with the thighs foreshortened toward the viewer, a front-view sitter read as a standing figure;
        the shade under the knees is the cue that the thighs come forward (v13 limitation work).
        """
        if self.back or self.stance_name != "sit":
            return []
        shade = col.hex_rgb(LAP_SHADOW["color"])
        layers = []
        for name, length, opacity in (("lap_shadow", LAP_SHADOW["long"], LAP_SHADOW["long_opacity"]),
                                      ("lap_shadow_core", LAP_SHADOW["core"], LAP_SHADOW["core_opacity"])):
            polys = []
            for side in (-1, 1):
                _, knee, ankle = self.leg_joints(side)
                half = self.widths["calf"][0] * LAP_SHADOW["half"]
                a, b = knee + [0.0, LAP_SHADOW["start"]], knee + (ankle - knee) * length
                polys.append(self.to_canvas(np.array([a - [half, 0], a + [half, 0], b + [half * 0.8, 0],
                                                      b - [half * 0.8, 0]]), 0.3))
            layers.append(Layer(name, Material.FLAT, shade, polys=polys, clip=("body_skin", "pants"),
                                blend=Blend.MULTIPLY, feather=LAP_SHADOW["feather"] * self.H, opacity=opacity))
        return layers

    def hip_layers(self):
        """Round hips (female) from the front, glutes (everyone) from behind."""
        if self.back:
            return backview.glute_layers(self)
        if not self.has_bust:
            return []
        ox, cy, rx, ry, k = HIP_DOME
        layers = []
        for side in (-1, 1):
            hip, _, _ = self.leg_joints(side)
            c = np.array([hip[0] + side * ox, cy])
            poly = self.to_canvas(geom.ellipse(c[0], c[1], rx, ry, 48), 0.2)
            cc = self.to_canvas([c], 0.2)[0]
            normals = shapes.sphere_normals(cc[0], cc[1], rx * k * self.H, ry * k * self.H)
            layers.append(Layer(f"hip_{side}", Material.SKIN, self.skin, polys=[poly], clip=("body_skin",),
                                feather=0.03 * self.H,
                                shade=ShadeSpec(normal_map=normals, threshold=HIP_THRESHOLD, rim=0.3, form=SKIN_FORM),
                                tags=("body", "hip")))
        return layers

    def anatomy_layers(self):
        """Surface landmarks of bare skin: navel, midline, lower pelvis lines, under-bust crease.

        They sit under every garment, so clothing hides whatever it covers.
        """
        if self.back:
            return backview.back_anatomy(self) + (musculature.limb_layers(self) if self.abs else [])
        H = self.H
        ink = col.shadow_of(self.skin, 0.45, "#B03040", 0.05, 0.35)
        shade = col.shadow_of(self.skin, 0.18, "#C04050", 0.04, 0.2)
        strokes, soft = [], []

        def stroke(pts, w, taper=(0.4, 0.4)):
            sp = geom.catmull_rom(np.array(pts, dtype=np.float64), 10)
            return (self.to_canvas(sp, 0.25), geom.tapered_widths(len(sp), w * H, *taper))
        if not self.abs:
            strokes.append(stroke([(0.0, 1.00), (0.004, 1.25), (0.0, 1.48)], 0.0030, (0.5, 0.5)))
        for side in (-1, 1):
            strokes.append(stroke([(side * 0.42, 1.86), (side * 0.30, 2.02), (side * 0.17, 2.20)], 0.0038))
        navel = self.to_canvas(geom.ellipse(0.0, 1.575, 0.016, 0.030, 24), 0.25)
        navel_shadow = self.to_canvas(geom.ellipse(0.004, 1.565, 0.030, 0.040, 24), 0.25)
        return [Layer("skin_soft_shadow", Material.FLAT, shade, strokes=soft, polys=[navel_shadow], clip=("body_skin",),
                      blend=Blend.MULTIPLY, feather=0.012 * H, opacity=0.55),
                Layer("skin_lines", Material.INK, ink, strokes=strokes, clip=("body_skin",), opacity=0.40),
                Layer("navel", Material.FLAT, ink, polys=[navel], clip=("body_skin",), opacity=0.75, feather=0.002 * H)] + \
            (musculature.male_layers(self) if self.abs else [])

    # ------------------------------------------------------------ bust
    def bust_shape(self, side, grow=0.0):
        """Breast (female) or pectoral plate (male) outline, body-local."""
        cx, cy, rx, ry = self.bust
        if self.gender == "male":
            P = np.array(PEC_PLATE) * [rx + grow, ry + grow] + [cx, cy]
            P = geom.catmull_rom(P, 8, closed=True)
        else:
            # round lower hemisphere; the upper slope is a longer, gentler arc that fades into the chest
            a = np.linspace(0, 2 * np.pi, 72, endpoint=False)
            ky = np.where(np.sin(a) < 0, BUST_TOP_REACH, 1.0)
            P = np.column_stack([cx + (rx + grow) * np.cos(a), cy + (ry + grow) * np.sin(a) * ky])
        P[:, 0] *= side
        return P

    def bust_arc(self, side, a0, a1, n=13):
        """Points on the breast outline between two angles (degrees, 90 = bottom), inner side at 180."""
        cx, cy, rx, ry = self.bust
        a = np.radians(np.linspace(a0, a1, n))
        ky = np.where(np.sin(a) < 0, BUST_TOP_REACH, 1.0)
        return [(side * x, y) for x, y in np.column_stack([cx + rx * np.cos(a), cy + ry * np.sin(a) * ky])]

    def crease(self, side):
        """Lower border of the breast or pectoral, inner end first (body-local)."""
        if self.gender == "male":
            cx, cy, rx, ry = self.bust
            return [(side * x, y) for x, y in np.array(PEC_LOWER) * [rx, ry] + [cx, cy]]
        return self.bust_arc(side, *BUST_CREASE_ARC, n=9)

    def bust_contour(self, side):
        """Inked border of the breast: under the bust and up the outer side toward the armpit."""
        if self.gender == "male":
            return self.crease(side)
        return self.bust_arc(side, *BUST_CONTOUR_ARC)

    def bust_normals(self, side, scale=BUST_SPHERE):
        cx, cy, rx, ry = self.bust
        H = self.H
        if self.gender == "male":
            ox, oy, kx, ky = PEC_DOME
            c = self.to_canvas([(side * (cx + ox * rx), cy + oy * ry)], self.bust_z())[0]
            return shapes.sphere_normals(c[0], c[1], rx * kx * H, ry * ky * H)
        c = self.to_canvas([(side * cx, cy)], self.bust_z())[0]
        return shapes.teardrop_normals(c[0], c[1], rx * scale * H, ry * scale * H, BUST_TOP_REACH)

    def bust_layers(self):
        """Breast or pectoral volume on bare skin.

        Sphere (or dome) shading gives the lit top and the shadow crescent; a
        tapered contour along the lower border and a soft cast shadow below it
        make the mass read as round. The top stays open and blends into the chest.
        """
        if self.back:
            return []
        H = self.H
        z = self.bust_z()
        sheen = BUST_SHEEN if self.has_bust else BUST_SHEEN * 0.6
        form = musculature.strength(self)     # pectoral plate definition follows the male muscle setting
        layers, contour, cast = [], [], []
        for side in (-1, 1):
            poly = self.to_canvas(self.bust_shape(side), z)
            # the bust stays inside the body silhouette, which already includes it (female)
            layers.append(Layer(f"bust_{side}", Material.SKIN, self.skin, polys=[poly], clip=("body_skin",),
                                feather=0.008 * H,
                                shade=ShadeSpec(normal_map=self.bust_normals(side), threshold=0.10, rim=0.3,
                                                spec=sheen, spec_edge=0.90, form=SKIN_FORM),
                                opacity=form, tags=("body", "bust")))
            sp = geom.catmull_rom(np.array(self.bust_contour(side)), 6)
            contour.append((self.to_canvas(sp, z), geom.tapered_widths(len(sp), BUST_CONTOUR_W * H, 0.30, 0.45)))
            cr = geom.catmull_rom(np.array(self.crease(side)), 8)
            cast.append((self.to_canvas(cr + [0.0, 0.03], z), geom.tapered_widths(len(cr), 0.055 * H, 0.3, 0.4)))
        ink = col.shadow_of(self.skin, 0.45, "#B03040", 0.05, 0.35)
        shade = col.shadow_of(self.skin, 0.20, "#C04050", 0.04, 0.2)
        layers += [Layer("bust_cast", Material.FLAT, shade, strokes=cast, clip=("torso_mask",), cut=("bust",),
                         blend=Blend.MULTIPLY, feather=0.010 * H, opacity=0.55 * form),
                   Layer("bust_contour", Material.INK, ink, strokes=contour, clip=("body_skin",), opacity=0.80 * form)]
        return layers

    def feet_layers(self, kind, shoe_color=None):
        """Bare feet seen from the front (toes toward the viewer), with sandal straps or pump vamps."""
        if self.back:
            return backview.heel_layers(self)
        H = self.H
        k = self.hand_scale
        foot = np.array([(-0.062, -0.03), (0.062, -0.03), (0.088, 0.10), (0.104, 0.22), (0.090, 0.30), (0.050, 0.335),
                         (-0.030, 0.330), (-0.075, 0.30), (-0.092, 0.20), (-0.080, 0.08)]) * k
        polys, toes, straps, soles, vamps = [], [], [], [], []
        for side in (-1, 1):
            a = self.leg_joints(side)[2]
            F = foot.copy()
            F[:, 0] *= -side          # big toe on the inner side
            raised = RAISED_FOOT_SCALE if side in self.stance.get("raised_foot", ()) else np.ones(2)
            # v9: a calf ending in a round cap read as a stump; a foot pointing down and back reads as
            # a foot set against the wall
            F *= raised
            polys.append(self.to_canvas(geom.catmull_rom(F + a, 6, closed=True), 0.3))
            for j, x in enumerate((-0.045, -0.010, 0.022, 0.050)):
                t = np.array([(x * -side, 0.27), (x * -side + side * -0.004, 0.315)]) * k * raised + a
                toes.append((self.to_canvas(t, 0.3), np.full(2, (0.0032 - 0.0004 * j) * H)))
            if kind == "heels":
                # a pump covers the toes; the arch lifts the heel so the foot reads shorter from the front
                vamps.append(self.to_canvas(geom.ellipse(a[0] - side * 0.004, a[1] + 0.24 * k * raised[1],
                                                         0.10 * k * raised[0], 0.11 * k * raised[1], 32), 0.3))
            if kind == "sandals":
                for y in (0.08, 0.20):
                    w = np.interp(y, [0.0, 0.3], [0.072, 0.10])
                    strap = np.array([(-w, y), (w, y), (w, y + 0.035), (-w, y + 0.035)]) * raised
                    straps.append(self.to_canvas(strap + a, 0.3))
                sole = np.array([(-0.105, 0.31), (0.115, 0.31), (0.105, 0.36), (-0.095, 0.36)]) * raised
                soles.append(self.to_canvas(sole + a, 0.3))
        ink = col.shadow_of(self.skin, 0.45, "#B03040", 0.05, 0.35)
        layers = []
        if soles:
            layers.append(Layer("sandal_soles", Material.CLOTH, col.hex_rgb("#B08A62"), polys=soles, line=self.line,
                                shade=ShadeSpec(inflate=0.01 * H)))
        layers += [self._skin("feet", polys, inflate=0.04, cast=(), tags=("body", "feet")),
                   Layer("toe_lines", Material.INK, ink, strokes=toes, opacity=0.55)]
        if vamps:
            layers.append(Layer("pumps", Material.CLOTH, shoe_color if shoe_color is not None else col.hex_rgb("#2A2226"),
                                polys=vamps, clip=("feet",), line=self.line,
                                shade=ShadeSpec(inflate=0.02 * H, spec=0.8, spec_edge=0.9)))
        if straps:
            layers.append(Layer("sandal_straps", Material.CLOTH, col.hex_rgb("#8A5A3C"), polys=straps,
                                line=LineSpec(cfg.LINE_DETAIL * H), shade=ShadeSpec(inflate=0.01 * H)))
        return layers

    def arm_layers(self, placement):
        """Forearm skin and hand layers of every arm with the given placement."""
        layers = []
        for side in (-1, 1):
            a = self.arms[side]
            if a["forearm"] != placement:
                continue
            tags = ("body", "forearm", placement)
            polys = [self.to_canvas(p) for p in self.arm_local(side, "lower")]
            fore = self._skin(f"forearm_skin_{side}", polys, inflate=0.05, tags=tags)
            # no outline where the forearm overlaps the upper arm: one continuous arm at the elbow
            fore.line = LineSpec(self.line.width, hide=("upper_arm_mask",))
            layers.append(fore)
            if self.abs:
                layers += musculature.forearm_layers(self, side, clip=(fore.name,))
            layers += self.hand_layers(side, tags)
        return layers

    def hand_layers(self, side, tags):
        a = self.arms[side]
        if not a["hand"]:
            return []
        _, e, w = self.joints(side)
        d = (w - e) / np.linalg.norm(w - e)
        fingers = np.array(a.get("fingers", (d[0] * side, d[1], 0.15)), dtype=np.float64)
        palm = np.array(a.get("palm", HANG_NORMAL), dtype=np.float64)
        if self.back:
            fingers[2], palm[2] = -fingers[2], -palm[2]     # the hand is seen from its other side
        parts = hand.posed_parts(a["hand"], np.r_[w, 0.10], fingers, palm, side,
                                 self.rig.body, self.H, scale=self.hand_scale)
        held = handheld.layers(self, side, self.hold[1])[0] if self.hold and self.hold[0] == side else []

        hand_tags = tags + ("hand",) + ((handheld.HELD_HAND_TAG,) if held else ())

        def part_layer(name, polys):
            return Layer(f"hand_{side}_{name}", Material.SKIN, self.skin, polys=polys,
                         line=LineSpec(cfg.LINE_DETAIL * self.H * 1.1),
                         shade=ShadeSpec(inflate=0.018 * self.H, cast_tags=("hand",),
                                         cast_dist=0.012 * self.H, threshold=0.12, rim=0.4),
                         tags=hand_tags)

        if any(handheld.BEHIND_HAND_TAG in L.tags for L in held):
            # a can or a phone is held with the back of the hand toward the viewer: the hand is in front of it,
            # except a thumb resting on the object's far face (a phone screen)
            behind = {"thumb"} if a.get("thumb_behind") else set()
            return ([part_layer(n, p) for n, p, _ in parts if n in behind] + held
                    + [part_layer(n, p) for n, p, _ in parts if n not in behind])
        layers = []
        for name, polys, _ in parts:
            if held and name != "palm":
                layers += held        # the object sits in the palm; the fingers close over it
                held = []
            layers.append(part_layer(name, polys))
        return layers + held

    def held_late_layers(self):
        """Glow or smoke of a held object, drawn over the whole figure."""
        return handheld.layers(self, *self.hold)[1] if self.hold else []

    def knee_layers(self):
        if self.back:
            return []
        knees = []
        for side in (-1, 1):
            _, k, _ = self.leg_joints(side)
            arc = geom.bezier(k + [-0.07, 0.02], k + [-0.03, 0.06], k + [0.03, 0.06], k + [0.07, 0.02], 12)
            knees.append((self.to_canvas(arc), geom.tapered_widths(12, 0.004 * self.H, 0.4, 0.4)))
        ink = col.shadow_of(self.skin, 0.45, "#B03040", 0.05, 0.35)
        layers = [Layer("knee_lines", Material.INK, ink, strokes=knees, opacity=0.45)]
        if self.stance.get("knee_caps"):
            # knees facing the viewer: round caps at the end of the foreshortened thighs
            for side in (-1, 1):
                _, k, _ = self.leg_joints(side)
                r = self.widths["thigh"][-1] / 2
                c = self.to_canvas([k + [0.0, -0.02]], 0.3)[0]
                layers.append(Layer(f"knee_cap_{side}", Material.SKIN, self.skin,
                                    polys=[self.to_canvas(geom.ellipse(k[0], k[1] - 0.02, r, r * 1.05, 32), 0.3)],
                                    clip=("body_skin",), feather=0.01 * self.H,
                                    shade=ShadeSpec(normal_map=shapes.sphere_normals(c[0], c[1], r * 1.2 * self.H,
                                                                                      r * 1.25 * self.H),
                                                    threshold=0.08, rim=0.3, form=SKIN_FORM),
                                    tags=("body",)))
        return layers

    def silhouette_polys(self):
        """Torso, limbs and neck of the whole figure (for drop shadows)."""
        polys = [self.neck_canvas(), self.to_canvas(self.torso_local())]
        for side in (-1, 1):
            polys += [self.to_canvas(p) for part in ("upper", "lower") for p in self.arm_local(side, part)]
            polys += [self.to_canvas(p) for part in ("thigh", "calf") for p in self.leg_local(side, part)]
        return polys

    def clavicle_layers(self):
        if self.back:
            return []
        H = self.H
        strokes = []
        for side in (-1, 1):
            c = np.array([(0.05, 0.035), (0.16, 0.075), (0.30, 0.070), (0.44, 0.100)])
            c[:, 0] *= side * self.shoulder[0] / SHOULDER[0]     # collarbones span the shoulder width
            spine = geom.catmull_rom(c, 10)
            strokes.append((self.to_canvas(spine, 0.2), geom.tapered_widths(len(spine), 0.0045 * H, 0.4, 0.5)))
        notch = geom.bezier((-0.045, 0.05), (-0.01, 0.10), (0.01, 0.10), (0.045, 0.05), 12)
        strokes.append((self.to_canvas(notch, 0.25), geom.tapered_widths(12, 0.004 * H, 0.4, 0.4)))
        line = col.shadow_of(self.skin, 0.45, "#B03040", 0.05, 0.35)
        return [Layer("clavicles", Material.INK, line, strokes=strokes, opacity=0.55, tags=("body_detail",))]
