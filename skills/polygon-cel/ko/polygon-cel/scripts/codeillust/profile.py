"""Profile (side) view: head, body and garments drawn as side silhouettes.

The front rig places features on a 3D head and body seen from the front; a
true side view needs different silhouettes (nose, lips and chin on the face
outline, bust and glutes on the torso outline, feet in profile), so this
module draws the figure from side-view templates in the same coordinate
spaces (head-local and body-local, H units, x toward the facing direction).
Garments are generic: a band of the body silhouette between a neckline and
a hem, plus sleeves, skirt flares or fitted shells, which covers every
outfit type at the cost of front details (buttons, cords, prints).
"""
import cv2
import numpy as np

from . import color as col
from . import config as cfg
from . import geom, hand, shapes
from .accessories import BEANIE
from .body import BUSTS, FIGURES, LIMB_WIDTHS, MALE_FIGURES, limb
from .outfit import DEFAULT_BOTTOM, DEFAULT_BOTTOM_MALE, DEFAULT_COLORS
from .scene import Layer, LineSpec, Material, ShadeSpec

# ---------------------------------------------------------------- head (head-local, facing +x)
SKULL = (-0.04, 0.40, 0.39)            # center x, center y, radius
FACE = {   # forehead to chin bottom, then under the jaw toward the neck
    "female": [(0.27, 0.12), (0.335, 0.26), (0.355, 0.40), (0.362, 0.50), (0.352, 0.565), (0.392, 0.665),
               (0.424, 0.735), (0.386, 0.765), (0.392, 0.800), (0.370, 0.825), (0.381, 0.850), (0.350, 0.885),
               (0.356, 0.930), (0.310, 0.975), (0.180, 0.985), (0.070, 0.950)],
    "male":   [(0.27, 0.12), (0.345, 0.26), (0.365, 0.40), (0.380, 0.50), (0.360, 0.570), (0.410, 0.675),
               (0.445, 0.745), (0.398, 0.780), (0.398, 0.815), (0.378, 0.840), (0.386, 0.865), (0.362, 0.900),
               (0.372, 0.960), (0.330, 1.010), (0.180, 1.020), (0.060, 0.985)],
}
NAPE = [(-0.06, 0.88), (-0.20, 0.84), (-0.30, 0.74)]
EAR = (-0.02, 0.635, 0.055, 0.095)
EYE = {"female": [(0.268, 0.582), (0.300, 0.566), (0.330, 0.572), (0.350, 0.604), (0.330, 0.632), (0.292, 0.640)],
       "male":   [(0.272, 0.592), (0.305, 0.580), (0.335, 0.584), (0.352, 0.606), (0.333, 0.626), (0.296, 0.632)]}
IRIS = (0.322, 0.606, 0.022, 0.040)
BROW = [(0.250, 0.498), (0.300, 0.480), (0.358, 0.482)]
HAIR_ARC_START = 150.0         # degrees (y down): the hair mass starts low on the back of the skull
FRINGE_ARC_END = -12.0         # degrees: the fringe leaves the skull arc here, in front of the forehead
FRINGE_EDGE = {   # lower edge of the fringe, front to back: tip, notch, tip, notch, tip, back into the cap
    "long":  [(0.405, 0.475), (0.345, 0.390), (0.338, 0.505), (0.280, 0.405), (0.248, 0.470), (0.175, 0.360)],
    "short": [(0.400, 0.370), (0.335, 0.300), (0.318, 0.390), (0.250, 0.310), (0.205, 0.360), (0.120, 0.270)],
}
HAIRLINE_PATHS = {   # from the back of the fringe around the side of the face to the back of the skull
    # down past the hidden ear, ending in pointed locks over the neck that fall in front of the back hair
    "covered": [(0.15, 0.46), (0.10, 0.60), (0.07, 0.82), (0.05, 1.02), (0.03, 1.20), (-0.03, 1.04), (-0.09, 1.24),
                (-0.15, 1.06), (-0.23, 1.18), (-0.31, 0.98), (-0.40, 0.76)],
    # sideburn, up the front of the ear, over it, down behind it, a short pointed nape
    "ear":     [(0.13, 0.48), (0.08, 0.56), (0.075, 0.67), (0.045, 0.69), (0.04, 0.56), (-0.02, 0.515),
                (-0.09, 0.56), (-0.12, 0.70), (-0.20, 0.86), (-0.27, 0.80), (-0.33, 0.87), (-0.40, 0.72)],
}
SIDE_LOCK = [(0.13, 0.38), (0.12, 0.66), (0.10, 0.90), (0.12, 1.10)]     # frames the cheek, root under the fringe
STRAND_SIDE_ENDS = {False: [(0.02, 0.80), (-0.22, 0.80)], True: [(-0.06, 0.50), (-0.25, 0.74)]}
STRAND_BOW = np.array([0.03, -0.03])
LOCK_BOW = 0.18                # sideways bow of each lock edge (share of its length): curved, pointed tips
STRAND_OPACITY = 0.45
PROFILE_BEANIE = {"front": 0.80, "back": 0.92}   # cuff ends as shares of the dome radius in front of and behind it

# ---------------------------------------------------------------- body (body-local, facing +x)
BACK_LINE = {
    "female": [(-0.17, -0.02), (-0.26, 0.15), (-0.32, 0.40), (-0.32, 0.70), (-0.27, 1.05), (-0.21, 1.40),
               (-0.26, 1.70), (-0.40, 2.00), (-0.45, 2.20), (-0.38, 2.42), (-0.22, 2.56)],
    "male":   [(-0.19, -0.04), (-0.32, 0.15), (-0.39, 0.45), (-0.37, 0.80), (-0.29, 1.20), (-0.24, 1.45),
               (-0.27, 1.75), (-0.35, 2.05), (-0.37, 2.25), (-0.29, 2.45), (-0.17, 2.56)],
}
FRONT_LINE = {
    "female": [(0.15, -0.02), (0.21, 0.15), (0.26, 0.40), (0.27, 0.70), (0.24, 0.98), (0.20, 1.30), (0.23, 1.60),
               (0.26, 1.85), (0.23, 2.10), (0.16, 2.40), (0.05, 2.52)],
    # pec shelf, rib cage, flat abdomen
    "male":   [(0.18, -0.02), (0.27, 0.18), (0.36, 0.40), (0.38, 0.60), (0.33, 0.80), (0.28, 1.00), (0.26, 1.30),
               (0.26, 1.60), (0.25, 1.90), (0.21, 2.20), (0.13, 2.42), (0.05, 2.52)],
}
NECK = {"female": ((-0.20, 0.80), (0.12, 0.92), (-0.17, 0.03), (0.15, 0.08)),   # head top back/front, body base
        "male":   ((-0.23, 0.80), (0.14, 0.95), (-0.20, 0.03), (0.18, 0.08))}
GLUTE_PROFILE = (-0.28, 2.20, 0.19, 0.30)   # center x, y, radii
PEC_PROFILE = (0.24, 0.56, 0.15, 0.22)
SHOULDER_JOINT = (0.0, 0.40)
DELTOID = {"female": (0.0, 0.03, 0.15, 0.19), "male": (0.01, 0.05, 0.23, 0.27)}   # offset from the joint, radii
ARM_EXPAND = {"female": 0.0, "male": 0.025}   # side-on, the male arm shows biceps and triceps depth
HIP_JOINT = (-0.02, 2.14)
# poses in profile: arm (elbow, wrist) and leg (knee, ankle) per near/far side
PROFILE_POSES = {
    "relaxed": {"near_arm": ((-0.03, 1.40), (0.04, 2.25)), "far_arm": ((0.00, 1.40), (0.08, 2.24)),
                "near_leg": ((0.04, 3.88), (-0.02, 5.32)), "far_leg": ((0.07, 3.88), (0.02, 5.32))},
    "walk":    {"near_arm": ((-0.14, 1.38), (-0.26, 2.18)), "far_arm": ((0.10, 1.38), (0.30, 2.14)),
                "near_leg": ((0.26, 3.84), (0.46, 5.26)), "far_leg": ((-0.10, 3.88), (-0.42, 5.18))},
    "sit":     {"near_arm": ((0.04, 1.38), (0.52, 2.02)), "far_arm": ((0.07, 1.38), (0.56, 2.04)),
                "near_leg": ((0.95, 2.18), (0.95, 3.62)), "far_leg": ((0.99, 2.18), (0.99, 3.62))},
}
FOOT = [(-0.07, -0.04), (0.06, -0.03), (0.17, 0.12), (0.30, 0.22), (0.31, 0.28), (-0.10, 0.28), (-0.12, 0.15)]
FAR_DARKEN = 0.10
BUST_APEX = 0.75          # the bust apex projects this many bust radii past the chest wall
BUST_DEPTH_R = 0.85       # horizontal radius of the bust in profile (bust radii); its back half sits in the chest
CHEST_X = 0.27            # chest wall at the bust line (female front line)

# garment bands: (neck front y, neck back y, hem y, sleeve, ease); sleeve: None, "cap", "short", "elbow", "long"
TOPS = {
    "knit_sweater": (0.06, 0.02, 2.20, "long", 0.045), "shirt": (0.30, -0.05, 2.30, "long", 0.03),
    "hoodie": (0.12, 0.02, 2.22, "long", 0.07), "offshoulder_dress": (0.50, 0.50, 1.55, "puff", 0.03),
    "crop_top": (0.30, 0.05, 1.12, None, 0.022), "rash_guard": (-0.10, -0.10, 1.78, "long", 0.02),
    "beach_shirt": (0.40, -0.05, 1.98, "short", 0.045), "tank_top": (0.30, 0.05, 2.24, None, 0.02),
    "sports_bra": (0.34, 0.10, None, None, 0.015), "camisole": (None, 0.55, 2.05, None, 0.012),
    "slip_dress": (None, 0.55, 3.05, None, 0.018), "halter_dress": (-0.10, 1.45, 2.92, None, 0.018),
    "tee": (0.12, 0.0, 2.25, "short", 0.035), "oversized_tee": (0.14, 0.02, 2.82, "elbow", 0.10),
    "one_piece": (0.42, 1.30, None, None, 0.012),
}
FITTED_DRESSES = ("slip_dress", "halter_dress")
BOTTOMS = {   # waist y, hem y (None = ankle), ease, kind
    "jeans": (1.86, None, 0.035, "pants"), "leggings": (1.62, None, 0.008, "pants"),
    "joggers": (1.86, None, 0.06, "pants"), "slacks": (1.80, None, 0.045, "pants"),
    "board_shorts": (1.95, 3.02, 0.06, "pants"), "boxer_briefs": (1.90, 2.74, 0.01, "pants"),
    "dolphin_shorts": (1.95, 2.60, 0.022, "pants"), "a_line_skirt": (1.45, 3.72, 0.03, "flare"),
    "pencil_skirt": (1.56, 3.55, 0.025, "fitted"), "bikini": (2.00, None, 0.0, "brief"),
    "swim_briefs": (1.98, None, 0.0, "brief"),
}
DRAPE_BACK, DRAPE_FRONT = 0.46, 0.27   # long tops below the hips hang straight from the glutes and belly
DRAPE_UPPER_REACH = 2.2   # the cloth slope starts this many bust radii above the bust center
LOOSE_EASE = 0.03         # tops with at least this ease hang straight from the bust apex
FITTED_BRIDGE = 1.6       # fitted tops cling again this many bust radii below the bust center
NECKLINE_TURN_X = 0.20      # half depth of the neck, where a neckline changes from back to front height
STRAPPED = ("camisole", "slip_dress")
STRAP_FRONT = [(0.14, 0.24), (0.04, 0.03)]          # from the neckline up to the top of the shoulder
STRAP_BACK = [(0.04, 0.03), (-0.14, 0.20), (-0.27, 0.55)]
STRAP_W = 0.022
STRAP_NECKLINE_RISE = 1.0   # strapped necklines start this many bust radii above the bust center
SLEEVE_END = {"cap": 0.20, "short": 0.45, "puff": 0.35, "elbow": 1.0, "long": 2.0}


class ProfileBuilder:
    def __init__(self, rig, ch, light, seed):
        self.rig, self.ch, self.light = rig, ch, light
        self.H = rig.H
        self.f = -1.0 if ch.get("facing", "right") == "left" else 1.0
        self.gender = ch.get("gender", "female")
        self.male = self.gender == "male"
        self.skin = col.hex_rgb(ch["skin"])
        self.hair = col.hex_rgb(ch["hair"]["color"])
        self.line = LineSpec(cfg.LINE_BODY * self.H)
        self.face_line = LineSpec(cfg.LINE_FACE * self.H)
        pose = ch.get("pose", "relaxed")
        self.pose_name = pose if pose in PROFILE_POSES else "relaxed"
        self.pose = PROFILE_POSES[self.pose_name]
        self.widths = LIMB_WIDTHS[self.gender]
        figure = ch.get("figure", "balanced")
        if self.male:
            self.bust = None
            self.hip = MALE_FIGURES.get(figure, MALE_FIGURES["balanced"])["hip_x"]
        else:
            self.bust = BUSTS.get(ch.get("bust", "medium"), BUSTS["medium"])
            self.hip = FIGURES.get(figure, FIGURES["balanced"])["hip_x"]
        o = ch["outfit"]
        self.kind = o.get("type", "knit_sweater")
        self.color = col.hex_rgb(o.get("color", DEFAULT_COLORS.get(self.kind, "#DDDDDD")))
        defaults = DEFAULT_BOTTOM_MALE if self.male else DEFAULT_BOTTOM
        self.bottom = o.get("bottom", defaults.get(self.kind))
        if self.bottom == "bikini":
            bottom_hex = o.get("bikini_color", o.get("color", DEFAULT_COLORS["bikini"]))
        else:
            bottom_hex = DEFAULT_COLORS.get(self.bottom or "", "#555566")
        self.bottom_color = col.hex_rgb(o.get("bottom_color", bottom_hex))
        self.seed = seed

    # ------------------------------------------------------------ coordinates
    def Hc(self, P):
        return self.rig.head2(geom.pts(P) * [self.f, 1.0])

    def Bc(self, P):
        return self.rig.body2(geom.pts(P) * [self.f, 1.0])

    def B3(self, P3):
        P = np.asarray(P3, dtype=np.float64).reshape(-1, 3)
        return self.rig.body(np.column_stack([P[:, 0] * self.f, P[:, 1], P[:, 2]]))

    def skin_layer(self, name, polys, inflate=0.07, color=None, tags=("body",), line=True):
        return Layer(name, Material.SKIN, self.skin if color is None else color, polys=polys,
                     line=self.line if line else None,
                     shade=ShadeSpec(inflate=inflate * self.H, cast_tags=("hair_front", "garment_top"),
                                     cast_dist=0.06 * self.H, threshold=0.12, rim=0.5, form=0.3), tags=tags)

    # ------------------------------------------------------------ head
    def face_outline(self):
        cx, cy, r = SKULL
        face = np.array(FACE[self.gender])
        a0 = np.arctan2(NAPE[-1][1] - cy, NAPE[-1][0] - cx)
        a1 = np.arctan2(face[0][1] - cy, face[0][0] - cx)
        if a1 < a0:
            a1 += 2 * np.pi
        arc = np.column_stack([cx + r * np.cos(np.linspace(a0, a1, 40)), cy + r * np.sin(np.linspace(a0, a1, 40))])
        return geom.catmull_rom(np.vstack([arc, face[1:], NAPE]), 6, closed=True, alpha=0.9)

    def head_layers(self):
        H = self.H
        ch = self.ch
        ex, ey, erx, ery = EAR
        layers = []
        layers.append(Layer("face", Material.SKIN, self.skin, polys=[self.Hc(self.face_outline())],
                            line=self.face_line,
                            shade=ShadeSpec(inflate=0.05 * H, threshold=0.10, rim=0.35, cast_tags=("hair_front",),
                                            cast_dist=0.035 * H, form=0.25),
                            tags=("head",)))
        if ch["hair"].get("ears", "hidden") == "visible" or self.male:
            # the ear sits on the side of the skull, so it is drawn over the face shape
            ear = geom.ellipse(ex, ey, erx, ery, 32)
            layers.append(Layer("ear", Material.SKIN, self.skin, polys=[self.Hc(ear)], line=self.face_line,
                                shade=ShadeSpec(inflate=0.03 * H, threshold=0.12)))
        blush = float(ch["expression"].get("blush", 0.35))
        if blush > 0:
            layers.append(Layer("blush", Material.FLAT, col.hex_rgb(ch["expression"].get("blush_color", "#F28C8C")),
                                polys=[self.Hc(geom.ellipse(0.25, 0.715, 0.075, 0.035, 24))], clip=("face",),
                                feather=0.02 * H, opacity=blush * 0.8))
        ink = col.shadow_of(self.skin, 0.5, "#B03040", 0.05, 0.35)
        mouth = [(0.372, 0.826), (0.350, 0.832)] if not self.male else [(0.380, 0.842), (0.355, 0.848)]
        nose = [(0.392, 0.762), (0.372, 0.768)] if not self.male else [(0.400, 0.780), (0.378, 0.786)]
        layers.append(Layer("face_lines", Material.INK, ink,
                            strokes=[(self.Hc(geom.catmull_rom(np.array(p), 4)), np.full(5, 0.006 * H))
                                     for p in (mouth, nose)], opacity=0.8))
        layers += self.eye_layers()
        return layers

    def eye_layers(self):
        H = self.H
        e = self.ch["eyes"]
        shape = geom.catmull_rom(np.array(EYE[self.gender]), 8, closed=True)
        ix, iy, irx, iry = IRIS
        iris_c = col.hex_rgb(e.get("color", "#4F7DB8"))
        lid = np.array(EYE[self.gender][:4])
        lash = geom.catmull_rom(np.vstack([lid[:1] + [-0.015, -0.006], lid]), 6)
        lash_w = 0.016 if not self.male else 0.010
        brow = geom.catmull_rom(np.array(BROW) + ([0.0, 0.012] if self.male else [0.0, 0.0]), 6)
        brow_c = col.shadow_of(self.hair, 0.15)
        return [
            Layer("eye_white", Material.FLAT, col.hex_rgb("#FBFBFD"), polys=[self.Hc(shape)]),
            Layer("iris", Material.FLAT, iris_c, polys=[self.Hc(geom.ellipse(ix, iy, irx, iry, 32))],
                  clip=("eye_white",), gradient_fill=None),
            Layer("pupil", Material.FLAT, col.shadow_of(iris_c, 0.6), clip=("eye_white",),
                  polys=[self.Hc(geom.ellipse(ix + 0.004, iy + 0.004, irx * 0.45, iry * 0.5, 24))]),
            Layer("eye_glint", Material.FLAT, col.hex_rgb("#FFFFFF"), clip=("eye_white",),
                  polys=[self.Hc(geom.ellipse(ix - 0.006, iy - 0.016, 0.008, 0.010, 16))]),
            Layer("lash", Material.INK, col.hex_rgb("#2A2026"),
                  strokes=[(self.Hc(lash), geom.tapered_widths(len(lash), lash_w * H, 0.15, 0.4))]),
            Layer("brow", Material.INK, brow_c,
                  strokes=[(self.Hc(brow), geom.tapered_widths(len(brow), (0.016 if self.male else 0.010) * H,
                                                               0.2, 0.5))]),
        ]

    # ------------------------------------------------------------ hair
    def clump(self, name, pts, w_root, color=None, tags=("hair", "hair_front")):
        sp = geom.catmull_rom(np.array(pts, dtype=np.float64), 10)
        t = np.linspace(0, 1, len(sp))
        w = w_root * (1 - t) ** 0.9 * (1 + 0.3 * np.sin(np.pi * t))
        poly = geom.stroke_outline(sp, w)
        return Layer(name, Material.HAIR, self.hair if color is None else color, polys=[self.Hc(poly)],
                     line=LineSpec(cfg.LINE_FACE * self.H * 0.9),
                     shade=ShadeSpec(inflate=0.02 * self.H, threshold=0.06, rim=0.8), tags=tags)

    def hair_back_layers(self):
        style = self.ch["hair"].get("style", "long")
        length = {"long": 2.55, "bob": 1.08, "ponytail": 1.05, "short": 0.80}[style]
        length = float(self.ch["hair"].get("length", length))
        dark = col.shadow_of(self.hair, 0.16, "#302870", 0.04, 0.12)
        if style == "ponytail":
            pts = [(-0.38, 0.30), (-0.55, 0.55), (-0.62, 1.00), (-0.58, 1.55)]
            return [self.clump("ponytail", pts, 0.26, color=dark, tags=("hair", "hair_back"))]
        if style == "short":
            return []
        back = [(-0.40, 0.40), (-0.44, 0.70), (-0.40, 1.10), (-0.34, min(length, 1.6)), (-0.30, length)]
        front = [(-0.08, length - 0.05), (-0.12, min(length, 1.5)), (-0.10, 1.00), (-0.05, 0.75)]
        P = np.vstack([back, front])
        return [Layer("hair_back", Material.HAIR, dark, polys=[self.Hc(geom.catmull_rom(P, 8, closed=True))],
                      line=LineSpec(cfg.LINE_FACE * self.H),
                      shade=ShadeSpec(inflate=0.06 * self.H, gradient=(0.2, 0.5), threshold=0.06),
                      tags=("hair", "hair_back"))]

    def hair_front_layers(self):
        """One hair mass: skull arc, pointed fringe edge, then the hairline around the side of the face."""
        cx, cy, r = SKULL
        vol = 0.035 * float(self.ch["hair"].get("volume", 1.0))
        hair = self.ch["hair"]
        short = hair.get("style", "long") == "short"
        ear_visible = hair.get("ears", "hidden") == "visible" or self.male
        a = np.radians(np.linspace(HAIR_ARC_START, 360.0 + FRINGE_ARC_END, 48))
        arc = np.column_stack([cx + (r + vol) * np.cos(a), cy + (r + vol) * np.sin(a)])
        edge = self.fringe_edge(arc[-1], FRINGE_EDGE["short" if short else "long"])
        if ear_visible:     # the sideburn and ear contour stay smooth
            side = geom.catmull_rom(np.vstack([edge[-1:], HAIRLINE_PATHS["ear"], arc[:1]]), 8, alpha=0.9)[1:-1]
        else:               # side hair falls in locks with the same bowed, pointed edges as the fringe
            side = self.fringe_edge(edge[-1], HAIRLINE_PATHS["covered"] + [tuple(arc[0])])[1:-1]
        cap = np.vstack([arc, edge[1:], side])
        locks = not ear_visible and not short
        # the side lock hangs from under the cap, so only its part in front of the hairline shows
        layers = [self.clump("side_lock", SIDE_LOCK, 0.085)] if locks else []
        layers.append(Layer("hair_cap", Material.HAIR, self.hair, polys=[self.Hc(cap)],
                            line=LineSpec(cfg.LINE_FACE * self.H),
                            shade=ShadeSpec(inflate=0.08 * self.H, threshold=0.25, rim=1.0),
                            tags=("hair", "hair_front", "cap")))
        layers.append(self.strand_layer(arc, edge, ear_visible))
        return layers

    def fringe_edge(self, start, tips):
        """Pointed lower edge of the fringe: each lock edge bows forward between a tip and a notch."""
        pts = [np.asarray(start)] + [np.array(q) for q in tips]
        out = [pts[0][None, :]]
        t = np.linspace(0, 1, 10)[1:, None]
        for p, q in zip(pts[:-1], pts[1:]):
            d = q - p
            ctrl = (p + q) / 2 + np.array([d[1], -d[0]]) * LOCK_BOW
            out.append((1 - t) ** 2 * p + 2 * (1 - t) * t * ctrl + t ** 2 * q)
        return np.vstack(out)

    def strand_layer(self, arc, edge, ear_visible):
        """Thin strand lines from the crown toward the fringe tips and down the side of the head."""
        crown = arc[len(arc) * 2 // 3]
        ends = [edge[9 * k] for k in (1, 3, 5)] + [np.array(p) for p in STRAND_SIDE_ENDS[ear_visible]]
        strokes = []
        for tip in ends:
            mid = crown * 0.4 + tip * 0.6 + STRAND_BOW
            sp = geom.catmull_rom(np.array([crown, mid, tip]), 8)
            strokes.append((self.Hc(sp), geom.tapered_widths(len(sp), 0.006 * self.H, 0.4, 0.5)))
        return Layer("hair_strands", Material.INK, col.shadow_of(self.hair, 0.35), strokes=strokes,
                     clip=("hair_cap",), opacity=STRAND_OPACITY)

    # ------------------------------------------------------------ body geometry
    def torso_poly(self, ease=0.0, top=None):
        back = np.array(BACK_LINE[self.gender]) + [-ease, 0.0]
        front = np.array(FRONT_LINE[self.gender]) + [ease, 0.0]
        if top is not None:
            back, front = back[back[:, 1] >= top - 0.2], front[front[:, 1] >= top - 0.2]
        P = np.vstack([front, back[::-1]])
        return geom.catmull_rom(P, 6, closed=True, alpha=0.9)

    def bust_shape(self, grow=0.0):
        """Side outline of the breast: round below, a long gentle upper slope, back half inside the chest."""
        _, cy, _, ry = self.bust
        r = BUST_DEPTH_R * ry + grow
        c = np.array([CHEST_X + BUST_APEX * ry - BUST_DEPTH_R * ry, cy + 0.03])
        a = np.linspace(0, 2 * np.pi, 72, endpoint=False)
        ky = np.where(np.sin(a) < 0, 1.30, 1.0)
        return np.column_stack([c[0] + r * np.cos(a), c[1] + (ry + grow) * np.sin(a) * ky]), c, r

    def bust_contour(self):
        """Under-bust curve from the chest wall around the bottom to the apex."""
        shape, c, r = self.bust_shape()
        a = np.radians(np.linspace(150, -10, 14))
        ry = self.bust[3]
        return np.column_stack([c[0] + r * np.cos(a), c[1] + ry * np.sin(a)])

    def arm(self, which, expand=0.0, part=None):
        e, w = self.pose[which]
        s = np.array(SHOULDER_JOINT)
        expand += ARM_EXPAND[self.gender]
        polys = []
        if part in (None, "upper"):
            dx, dy, rx, ry = DELTOID[self.gender]
            polys += limb(s, e, self.widths["upper"], expand) + [geom.ellipse(s[0] + dx, s[1] + dy, rx + expand,
                                                                               ry + expand, 40)]
        if part in (None, "lower"):
            polys += limb(e, w, self.widths["lower"], expand)
        return polys

    def leg(self, which, expand=0.0):
        k, a = self.pose[which]
        h = np.array(HIP_JOINT)
        return limb(h, k, self.widths["thigh"], expand) + limb(k, a, self.widths["calf"], expand, bend=-0.02)

    def foot(self, which):
        _, a = self.pose[which]
        return geom.catmull_rom(np.array(FOOT) + a, 6, closed=True)

    # ------------------------------------------------------------ body layers
    def far_side_layers(self):
        far = col.shadow_of(self.skin, FAR_DARKEN)
        layers = [self.skin_layer("far_leg", [self.Bc(p) for p in self.leg("far_leg")] + [self.Bc(self.foot("far_leg"))],
                                  color=far, tags=("body", "legs")),
                  self.skin_layer("far_arm", [self.Bc(p) for p in self.arm("far_arm")], color=far, tags=("body",))]
        return layers

    def neck_poly(self):
        tb, tf, bb, bf = NECK[self.gender]
        top = self.Hc([tb, tf])
        bot = self.Bc([bb, bf])
        return np.array([top[0], top[1], bot[1], bot[0]])

    def body_layers(self):
        H = self.H
        polys = [self.neck_poly(), self.Bc(self.torso_poly())] + [self.Bc(p) for p in self.leg("near_leg")]
        polys.append(self.Bc(self.foot("near_leg")))
        if self.bust is not None:
            polys.append(self.Bc(self.bust_shape()[0]))     # the bust belongs to the body outline
        layers = [self.skin_layer("body_skin", polys, inflate=0.12),
                  Layer("torso_mask", Material.FLAT, self.skin, polys=[self.Bc(self.torso_poly())], opacity=0.0)]
        if self.bust is not None:
            shape, c, r = self.bust_shape()
            cc = self.Bc([c])[0]
            layers.append(Layer("bust", Material.SKIN, self.skin, polys=[self.Bc(shape)], clip=("body_skin",),
                                feather=0.008 * H,
                                shade=ShadeSpec(normal_map=shapes.teardrop_normals(cc[0], cc[1], r * 1.08 * H,
                                                                                   self.bust[3] * 1.08 * H, 1.3),
                                                threshold=0.10, rim=0.3, spec=0.16, spec_edge=0.9, form=0.45),
                                tags=("body", "bust")))
            sp = self.Bc(self.bust_contour())
            ink = col.shadow_of(self.skin, 0.45, "#B03040", 0.05, 0.35)
            layers.append(Layer("bust_contour", Material.INK, ink, clip=("body_skin",), opacity=0.8,
                                strokes=[(sp, geom.tapered_widths(len(sp), 0.005 * H, 0.3, 0.4))]))
        gx, gy, grx, gry = GLUTE_PROFILE
        gc = self.Bc([(gx, gy)])[0]
        layers.append(Layer("glute", Material.SKIN, self.skin,
                            polys=[self.Bc(geom.ellipse(gx, gy, grx, gry, 40))], clip=("body_skin",),
                            feather=0.012 * H,
                            shade=ShadeSpec(normal_map=shapes.sphere_normals(gc[0], gc[1], grx * 1.12 * H, gry * 1.1 * H),
                                            threshold=0.08, rim=0.3, form=0.45), tags=("body",)))
        if self.male:
            px, py, prx, pry = PEC_PROFILE
            pc = self.Bc([(px - 0.01, py - 0.01)])[0]
            layers.append(Layer("pec", Material.SKIN, self.skin, polys=[self.Bc(geom.ellipse(px, py, prx, pry, 32))],
                                clip=("torso_mask",), feather=0.01 * H,
                                shade=ShadeSpec(normal_map=shapes.sphere_normals(pc[0], pc[1], prx * 1.3 * H, pry * 1.36 * H),
                                                threshold=0.10, rim=0.3, form=0.45), tags=("body",)))
        return layers

    def near_arm_layers(self):
        H = self.H
        layers = [self.skin_layer("near_arm", [self.Bc(p) for p in self.arm("near_arm")], inflate=0.06,
                                  tags=("body", "forearm"))]
        e, w = self.pose["near_arm"]
        d = np.array(w) - np.array(e)
        d = d / np.linalg.norm(d)
        parts = hand.posed_parts("relaxed", np.r_[w, 0.10], (d[0], d[1], 0.0), (0.0, 0.0, -1.0), 1, self.B3, H,
                                 scale=1.22 if self.male else 1.0)
        for name, polys, _ in parts:
            layers.append(Layer(f"hand_{name}", Material.SKIN, self.skin, polys=polys,
                                line=LineSpec(cfg.LINE_DETAIL * H * 1.1),
                                shade=ShadeSpec(inflate=0.018 * H, threshold=0.12, rim=0.4), tags=("body", "hand")))
        return layers

    # ------------------------------------------------------------ garments
    def band_helper(self, name, top_front, top_back, hem_front, hem_back):
        # the neckline turns from its back height to its front height across the neck, so a scoop back or a
        # high front reads clearly from the side
        P = np.array([(-2.0, top_back), (-NECKLINE_TURN_X, top_back), (NECKLINE_TURN_X, top_front), (2.0, top_front),
                      (2.0, hem_front), (-2.0, hem_back)])
        return Layer(name, Material.FLAT, self.color, polys=[self.Bc(P)], opacity=0.0)

    def cloth_layer(self, name, polys, color, clip=(), inflate=0.12, tags=("garment",)):
        return Layer(name, Material.CLOTH, color, polys=polys, line=self.line, clip=clip,
                     shade=ShadeSpec(inflate=inflate * self.H, cast_tags=("hair_front", "head"), cast_dist=0.05 * self.H,
                                     threshold=0.12, rim=0.8), tags=tags)

    def fitted_shell(self, ease, hem):
        hips = self.torso_poly(ease)
        pts = [hips[hips[:, 1] > 2.0]]
        for which in ("near_leg", "far_leg"):
            for p in self.leg(which, ease):
                pts.append(p[p[:, 1] < hem + 0.1])
        P = np.vstack([q for q in pts if len(q)]).astype(np.float32)
        return cv2.convexHull(P)[:, 0, :].astype(np.float64)

    def top_layers(self):
        if self.kind == "shirtless":
            return [], []
        layers, sleeves = [], []
        if self.kind == "bikini":
            if self.bust is not None:
                shape, c, r = self.bust_shape(0.01)
                wall = CHEST_X - 0.04
                cups = shape[shape[:, 0] > wall]
                cup = np.vstack([cups, [(wall, cups[:, 1].max()), (wall, cups[:, 1].min())]])
                layers.append(self.cloth_layer("bikini_cup", [self.Bc(geom.catmull_rom(cup, 4, closed=True))],
                                               self.color, inflate=0.05))
            strap = np.array([(-0.40, 0.80), (CHEST_X, 0.84), (CHEST_X, 0.87), (-0.40, 0.83)])
            layers.append(self.cloth_layer("bikini_strap", [self.Bc(strap)], self.color, clip=("torso_mask",), inflate=0.01))
            return layers, sleeves
        neck_f, neck_b, hem, sleeve, ease = TOPS[self.kind]
        if self.bust is not None:
            cx, cy, rx, ry = self.bust
            if neck_f is None:      # strap-held necklines cover the upper slope of the bust
                neck_f = cy - ry * STRAP_NECKLINE_RISE
            if hem is None:
                hem = cy + ry + 0.16
        else:
            neck_f = 0.30 if neck_f is None else neck_f
            hem = 1.10 if hem is None else hem
        name = f"top_{self.kind}"
        hem_back = hem + (0.02 if self.kind != "one_piece" else 0.0)
        if self.kind == "one_piece":
            hem, hem_back = 2.30, 2.45
        polys = [self.Bc(self.torso_poly(ease))]
        if self.bust is not None:
            polys.append(self.Bc(self.bust_drape(ease, hem)))
        if self.kind in FITTED_DRESSES or hem > 2.40:
            polys.append(self.Bc(self.fitted_shell(ease, hem) if self.kind in FITTED_DRESSES else self.drape(ease, hem)))
        if self.kind == "offshoulder_dress":
            polys.append(self.Bc(self.flare(1.40, 3.72, ease)))
            hem = hem_back = 3.72
        layers.append(self.band_helper(f"{name}_band", neck_f, neck_b, hem, hem_back))
        layers.append(self.cloth_layer(name, polys, self.color, clip=(f"{name}_band",), inflate=0.14,
                                       tags=("garment", "garment_top" if neck_f < 0.1 else "garment")))
        if self.bust is not None and neck_f < self.bust[1]:
            shape, c, r = self.bust_shape(ease)
            cc = self.Bc([c])[0]
            layers.append(Layer(f"{name}_round", Material.CLOTH, self.color, polys=[self.Bc(shape)],
                                clip=(name,), feather=0.012 * self.H,
                                shade=ShadeSpec(normal_map=shapes.teardrop_normals(cc[0], cc[1], r * 1.08 * self.H,
                                                                                   self.bust[3] * 1.08 * self.H, 1.3),
                                                threshold=0.12, rim=0.8)))
        if self.kind in STRAPPED and self.bust is not None:
            # the back half runs behind the arm; the front half crosses the shoulder in front of it
            for part, pts, out in (("back", STRAP_BACK, layers), ("front", [(CHEST_X + 0.02, neck_f)] + STRAP_FRONT, sleeves)):
                sp = self.Bc(geom.catmull_rom(np.array(pts), 8))
                out.append(Layer(f"{name}_strap_{part}", Material.CLOTH, self.color, line=LineSpec(cfg.LINE_DETAIL * self.H),
                                 strokes=[(sp, np.full(len(sp), STRAP_W * self.H))], tags=("garment",)))
        if sleeve:
            end = SLEEVE_END[sleeve]
            arm = self.arm("near_arm", 0.045, None if end > 1.0 else "upper")
            s = np.array(SHOULDER_JOINT)
            e, w = (np.array(v) for v in self.pose["near_arm"])
            stop = s + (e - s) * end if end <= 1.0 else w
            cut = np.array([(-2, -3), (2, -3), (2, stop[1] + 0.02), (-2, stop[1] + 0.02)])
            sleeves.append(Layer(f"{name}_sleeve_zone", Material.FLAT, self.color, polys=[self.Bc(cut)], opacity=0.0))
            sleeves.append(self.cloth_layer(f"{name}_sleeve", [self.Bc(p) for p in arm], self.color,
                                            clip=(f"{name}_sleeve_zone",), inflate=0.09, tags=("garment", "sleeve")))
        return layers, sleeves

    def bust_drape(self, ease, hem):
        """Cloth bridges the bust: a straight slope from the upper chest to the apex and no under-bust crease.

        Loose tops hang from the apex to the hem; fitted ones cling again just below the bust.
        """
        shape, c, r = self.bust_shape(ease)
        ry = self.bust[3]
        top = c[1] - ry * DRAPE_UPPER_REACH
        bottom = hem if ease >= LOOSE_EASE else c[1] + ry * FITTED_BRIDGE
        front = np.array(FRONT_LINE[self.gender]) + [ease, 0.0]
        front = front[(front[:, 1] >= top) & (front[:, 1] <= bottom)]
        anchors = np.array([(0.0, top), (0.0, bottom)])
        P = np.vstack([shape, front, anchors]).astype(np.float32)
        return cv2.convexHull(P)[:, 0, :].astype(np.float64)

    def drape(self, ease, hem):
        back, front = DRAPE_BACK + ease, DRAPE_FRONT + ease
        return np.array([(-back, 1.95), (front, 1.95), (front + 0.04, hem), (-back - 0.04, hem)])

    def flare(self, waist, hem, ease):
        return geom.catmull_rom(np.array([(-0.24 - ease, waist), (0.22 + ease, waist), (0.36, (waist + hem) / 2),
                                          (0.48, hem), (-0.58, hem), (-0.46, (waist + hem) / 2)]), 6, closed=True,
                                alpha=0.9)

    def bottom_layers(self):
        if not self.bottom:
            return []
        waist, hem, ease, kind = BOTTOMS[self.bottom]
        name = f"bottom_{self.bottom}"
        ankle = max(self.pose["near_leg"][1][1], self.pose["far_leg"][1][1])
        hem = ankle + 0.05 if hem is None else hem
        polys = [self.Bc(self.torso_poly(ease * 0.7))]
        seated_skirt = self.pose_name == "sit" and kind in ("flare", "fitted")
        if kind == "pants" or seated_skirt:
            polys += [self.Bc(p) for which in ("near_leg", "far_leg") for p in self.leg(which, ease + 0.03 * seated_skirt)]
        elif kind == "flare":
            polys.append(self.Bc(self.flare(waist, hem, ease)))
        elif kind == "fitted":
            polys.append(self.Bc(self.fitted_shell(ease, hem)))
        if seated_skirt:
            # a seated skirt lies along the thighs and stops at the knees
            knee_x = self.pose["near_leg"][0][0]
            band = np.array([(-2.0, waist), (knee_x + 0.06, waist), (knee_x + 0.06, 2.60), (-2.0, 2.60)])
        elif kind == "brief":
            # swim bottoms: a band over the hips cut high at the leg in front and over the glute behind
            front_cut, back_cut = (2.20, 2.42) if self.bottom == "bikini" else (2.25, 2.48)
            band = np.array([(-2.0, waist), (2.0, waist), (2.0, front_cut), (0.0, 2.55), (-2.0, back_cut)])
        else:
            band = np.array([(-2.0, waist), (2.0, waist), (2.0, hem), (-2.0, hem)])
        return [Layer(f"{name}_band", Material.FLAT, self.bottom_color, polys=[self.Bc(band)], opacity=0.0),
                self.cloth_layer(name, polys, self.bottom_color, clip=(f"{name}_band",), inflate=0.10,
                                 tags=("garment", "pants"))]

    def shoe_layers(self):
        shoes = self.ch["outfit"].get("shoes")
        if shoes is None:
            barefoot = self.kind in ("bikini", "one_piece", "rash_guard", "beach_shirt", "shirtless", "camisole",
                                     "oversized_tee") or self.bottom in ("bikini", "board_shorts", "swim_briefs",
                                                                         "boxer_briefs")
            shoes = "barefoot" if barefoot else "sneakers"
        if shoes in ("barefoot", "sandals"):
            return []
        color = col.hex_rgb(self.ch["outfit"].get("shoe_color", DEFAULT_COLORS.get(shoes, "#EEEEEE")))
        layers = []
        for which in ("far_leg", "near_leg"):
            F = geom.offset_closed(self.foot(which), 0.015)
            layers.append(self.cloth_layer(f"shoe_{which}", [self.Bc(F)], color, inflate=0.03, tags=("shoes",)))
        return layers

    # ------------------------------------------------------------ seat
    def seat_layers(self):
        if self.pose_name != "sit":
            return []
        color = col.hex_rgb("#8A6248")
        knee_y = self.pose["near_leg"][0][1]
        floor = self.pose["near_leg"][1][1] + 0.30
        parts = [np.array([(-0.50, knee_y + 0.12), (0.80, knee_y + 0.12), (0.80, knee_y + 0.26), (-0.50, knee_y + 0.26)]),
                 np.array([(0.70, knee_y + 0.26), (0.78, knee_y + 0.26), (0.78, floor), (0.70, floor)]),
                 np.array([(-0.48, knee_y + 0.26), (-0.40, knee_y + 0.26), (-0.40, floor), (-0.48, floor)]),
                 np.array([(-0.56, 0.90), (-0.48, 0.90), (-0.48, knee_y + 0.14), (-0.56, knee_y + 0.14)])]
        return [Layer("seat", Material.CLOTH, color, polys=[self.Bc(p) for p in parts], line=self.line,
                      shade=ShadeSpec(inflate=0.02 * self.H, threshold=0.12), tags=("seat",))]

    # ------------------------------------------------------------ assembly
    def beanie_layers(self):
        """Knit beanie in profile: dome over the skull arc, cuff band lower at the back of the head."""
        if "beanie" not in self.ch.get("accessories", []):
            return []
        b = BEANIE
        cx, cy, r = SKULL
        R = r + b["radius"] - 0.39 + 0.03 * (float(self.ch["hair"].get("volume", 1.0)) - 1.0)

        def on_circle(x):     # upper intersection of a vertical line with the dome circle
            return cy - np.sqrt(max(R * R - (x - cx) ** 2, 0.0))
        front_x, back_x = cx + R * PROFILE_BEANIE["front"], cx - R * PROFILE_BEANIE["back"]
        fy, by = b["front_y"], b["back_y"]
        a0, a1 = np.arctan2(fy - cy, front_x - cx), np.arctan2(by - cy, back_x - cx)
        if a1 > a0:
            a1 -= 2 * np.pi
        arc = np.linspace(a0, a1, 48)
        dome = np.vstack([np.column_stack([cx + R * np.cos(arc), cy + R * np.sin(arc)]), [(front_x, fy)]])
        t = np.linspace(0, 1, 16)
        low = np.column_stack([front_x + (back_x - front_x) * t, fy + (by - fy) * t])
        up = low - [0.0, b["cuff"]]
        cuff = np.vstack([low, up[::-1]])
        ribs = [(self.Hc(np.array([low[k], up[k]])), np.full(2, 0.0030 * self.H)) for k in range(0, 16, 2)]
        color = col.hex_rgb(self.ch.get("beanie_color", b["color"]))
        line = LineSpec(cfg.LINE_HAIR * self.H)
        return [Layer("beanie", Material.CLOTH, color, polys=[self.Hc(dome)], line=line,
                      shade=ShadeSpec(inflate=0.10 * self.H, threshold=0.15, rim=0.6), tags=("accessory", "hat")),
                Layer("beanie_cuff", Material.CLOTH, col.shadow_of(color, 0.08), polys=[self.Hc(cuff)], line=line,
                      clip=("beanie",), shade=ShadeSpec(inflate=0.03 * self.H, threshold=0.15), tags=("accessory",)),
                Layer("beanie_ribs", Material.INK, col.shadow_of(color, 0.35), strokes=ribs, clip=("beanie_cuff",),
                      opacity=0.6)]

    def build(self):
        tops, sleeves = self.top_layers()
        return (self.seat_layers() + self.hair_back_layers() + self.far_side_layers() + self.body_layers()
                + self.bottom_layers() + self.shoe_layers() + tops + self.near_arm_layers() + sleeves
                + self.head_layers() + self.hair_front_layers() + self.beanie_layers())


def build_layers(rig, ch, light, seed):
    return ProfileBuilder(rig, ch, light, seed).build()
