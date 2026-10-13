"""Hands and feet built from their bones.

Each finger is three phalanges (the thumb two) laid out from anatomical length
ratios, and each foot carries five toes, so digit count and proportion are
correct by construction.

Hand local frame: origin at the wrist, +y toward the fingertips, thumb on -x,
1.0 = wrist to the tip of the middle finger. Foot local frame (front view):
origin at the ankle, +y toward the ground, big toe on -x, 1.0 = one head height.
"""
from dataclasses import dataclass

import numpy as np

from ..color import rgb, mix
from ..geometry import catmull_rom, ellipse, Ribbon
from ..scene import Part, Line, Stroke

# finger: knuckle position, total length, half width, rest angle and spread angle (deg from +y)
FINGERS = {
    "index":  dict(base=(-0.150, 0.500), length=0.430, width=0.046, rest=-5.0, spread=-13.0),
    "middle": dict(base=(-0.048, 0.532), length=0.470, width=0.047, rest=-1.0, spread=-3.0),
    "ring":   dict(base=(0.054, 0.512), length=0.440, width=0.044, rest=3.5, spread=7.0),
    "pinky":  dict(base=(0.146, 0.456), length=0.350, width=0.039, rest=9.0, spread=19.0),
}
PHALANX_RATIO = (0.45, 0.30, 0.25)               # proximal, middle, distal share of finger length
CURL_SHORTEN = (0.30, 0.60, 0.72)                # how much each phalanx foreshortens at full curl
# thumb: metacarpal (hidden in the ball of the thumb) + two phalanges; the ribbon is wide at
# the base so the ball of the thumb and the thumb read as one tapering form
THUMB = dict(base=(-0.120, 0.10), lengths=(0.180, 0.140, 0.115), rest=-28.0, spread=-48.0,
             widths=[(0, 0.088), (0.40, 0.064), (0.8, 0.050), (1, 0.043)])
FINGER_WIDTHS = [(0, 1.05), (0.55, 1.0), (0.9, 0.88), (1, 0.80)]      # relative to the finger's half width
PALM = [(-0.130, -0.02), (-0.172, 0.06), (-0.222, 0.20), (-0.214, 0.34), (-0.192, 0.44), (-0.204, 0.50),
        (-0.150, 0.545), (-0.048, 0.568), (0.054, 0.552), (0.146, 0.500), (0.204, 0.455), (0.214, 0.36),
        (0.204, 0.18), (0.166, 0.04), (0.128, -0.02)]
FOREARM = dict(axis=[(0.0, -0.55), (0.0, 0.04)], widths=[(0, 0.165), (0.75, 0.128), (1, 0.135)])

# a closed hand seen from its back: the back of the hand, the four fingers folded under the knuckles (their
# first segments show as a row of blocks), and the thumb folded across the side
FIST_BACK = [(-0.15, -0.02), (-0.19, 0.12), (-0.205, 0.30), (-0.20, 0.45), (-0.152, 0.478), (-0.10, 0.462),
             (-0.047, 0.482), (0.006, 0.464), (0.057, 0.478), (0.108, 0.458), (0.153, 0.468), (0.20, 0.44), (0.21, 0.30),
             (0.20, 0.14), (0.14, -0.02)]                     # the bottom edge rides over the four knuckles
FIST_FINGERS = {"index": (-0.205, -0.100, 0.665), "middle": (-0.100, 0.006, 0.685), "ring": (0.006, 0.108, 0.665),
                "pinky": (0.108, 0.198, 0.615)}            # x from, x to, lowest y
FIST_TOP, FIST_CREASE = 0.40, 0.555                        # where the folded fingers start; the crease across them
FIST_THUMB = dict(axis=[(-0.14, 0.08), (-0.225, 0.29), (-0.21, 0.48), (-0.13, 0.59)],
                  widths=[(0, 0.066), (0.5, 0.054), (1, 0.040)])
HAND_SHAPES = ("natural", "fist", "point", "grip")

# foot outlines, origin at the ankle, +y toward the ground, 1.0 = one head height
FOOT_FRONT = [(-0.085, -0.08), (-0.108, 0.02), (-0.098, 0.12), (-0.128, 0.26), (-0.160, 0.36), (-0.06, 0.395),
              (0.06, 0.39), (0.150, 0.355), (0.160, 0.28), (0.116, 0.13), (0.104, 0.02), (0.085, -0.08)]
TOES_FRONT = [(-0.108, 0.395, 0.050, 0.058), (-0.036, 0.418, 0.034, 0.050), (0.026, 0.414, 0.031, 0.046),
              (0.078, 0.400, 0.028, 0.041), (0.122, 0.380, 0.025, 0.035)]    # (x, y, rx, ry), big toe first (on -x)
# seen from the side, toes toward -x: heel, sole with its arch, toe tip, instep
FOOT_SIDE = [(0.085, -0.08), (0.100, 0.04), (0.130, 0.16), (0.135, 0.27), (0.090, 0.315), (-0.02, 0.315),
             (-0.14, 0.298), (-0.30, 0.312), (-0.47, 0.320), (-0.56, 0.305), (-0.585, 0.270), (-0.54, 0.235),
             (-0.40, 0.200), (-0.24, 0.120), (-0.12, 0.020), (-0.085, -0.08)]
TOES_SIDE = [(-0.535, 0.285, 0.060, 0.037), (-0.465, 0.300, 0.036, 0.026)]
# seen from behind: the heel, the tendon above it, a little of the forefoot showing at each side
FOOT_BACK = [(-0.085, -0.08), (-0.095, 0.06), (-0.10, 0.20), (-0.12, 0.29), (-0.10, 0.345), (0.0, 0.365),
             (0.10, 0.345), (0.12, 0.29), (0.10, 0.20), (0.095, 0.06), (0.085, -0.08)]
FOOT_SHAPES = {"front": (FOOT_FRONT, TOES_FRONT), "side": (FOOT_SIDE, TOES_SIDE), "back": (FOOT_BACK, [])}

# shoes, in the same foot frames. skin: the foot outline the leg is drawn with (a pump shows the instep);
# body: the shoe; sole: its bottom band; extra: a heel or a shaft; sole_y: depth of the sole below the ankle
SHOES = {
    "sneakers": dict(
        front=dict(skin=[(-0.105, -0.05), (-0.125, 0.06), (-0.14, 0.20), (-0.175, 0.33), (-0.18, 0.41), (-0.10, 0.455),
                         (0.06, 0.45), (0.17, 0.41), (0.175, 0.32), (0.135, 0.18), (0.12, 0.06), (0.10, -0.05)],
                   sole=0.37, laces=[(0.08, 0.025), (0.14, 0.03), (0.20, 0.035)], lace_w=0.06),
        side=dict(skin=[(0.10, -0.06), (0.13, 0.10), (0.155, 0.25), (0.14, 0.345), (0.07, 0.37), (-0.30, 0.37),
                        (-0.56, 0.365), (-0.63, 0.33), (-0.63, 0.27), (-0.55, 0.22), (-0.38, 0.16), (-0.20, 0.06),
                        (-0.08, -0.04)],
                  sole=0.31, laces=[(-0.12, 0.05), (-0.22, 0.10), (-0.32, 0.15)], lace_w=0.07),
        back=dict(skin=[(-0.11, -0.05), (-0.12, 0.10), (-0.135, 0.28), (-0.125, 0.40), (0.0, 0.42), (0.125, 0.40),
                        (0.135, 0.28), (0.12, 0.10), (0.11, -0.05)], sole=0.35, laces=[], lace_w=0.0),
        sole_y=0.41, material="matte"),
    "boots": dict(
        front=dict(skin=[(-0.12, -0.46), (-0.125, -0.10), (-0.13, 0.12), (-0.16, 0.30), (-0.17, 0.40), (-0.09, 0.445),
                         (0.06, 0.44), (0.16, 0.40), (0.165, 0.30), (0.13, 0.12), (0.125, -0.10), (0.12, -0.46)],
                   sole=0.39, laces=[], lace_w=0.0),
        side=dict(skin=[(0.11, -0.46), (0.12, -0.10), (0.15, 0.20), (0.15, 0.36), (0.02, 0.37), (-0.30, 0.37),
                        (-0.55, 0.36), (-0.61, 0.32), (-0.59, 0.25), (-0.40, 0.17), (-0.20, 0.06), (-0.11, -0.10),
                        (-0.11, -0.46)],
                  sole=0.33, laces=[], lace_w=0.0, heel=[(0.15, 0.30), (0.02, 0.30), (0.02, 0.37), (0.15, 0.37)]),
        back=dict(skin=[(-0.12, -0.46), (-0.125, -0.10), (-0.13, 0.20), (-0.13, 0.40), (0.0, 0.41), (0.13, 0.40),
                        (0.13, 0.20), (0.125, -0.10), (0.12, -0.46)], sole=0.34, laces=[], lace_w=0.0),
        sole_y=0.41, material="gloss"),
    "heels": dict(
        # on a heel the foot points down the instep to the toe: the outline is longer and a pump covers the toes
        front=dict(skin=[(-0.08, -0.08), (-0.10, 0.04), (-0.095, 0.16), (-0.11, 0.30), (-0.115, 0.42), (-0.05, 0.52),
                         (0.0, 0.56), (0.06, 0.52), (0.125, 0.42), (0.12, 0.28), (0.10, 0.14), (0.10, 0.02), (0.08, -0.08)],
                   pump=[(-0.118, 0.27), (-0.125, 0.42), (-0.05, 0.53), (0.0, 0.575), (0.06, 0.53), (0.135, 0.42),
                         (0.13, 0.27), (0.06, 0.31), (0.0, 0.32), (-0.06, 0.31)],
                   sole=None, laces=[], lace_w=0.0),
        side=dict(skin=[(0.08, -0.08), (0.11, 0.08), (0.12, 0.22), (0.06, 0.30), (-0.10, 0.40), (-0.30, 0.50),
                        (-0.48, 0.555), (-0.53, 0.54), (-0.45, 0.48), (-0.28, 0.38), (-0.16, 0.22), (-0.08, 0.04),
                        (-0.07, -0.08)],
                  pump=[(0.12, 0.12), (0.135, 0.25), (0.08, 0.32), (-0.10, 0.425), (-0.30, 0.52), (-0.50, 0.57),
                        (-0.55, 0.55), (-0.46, 0.47), (-0.30, 0.40), (-0.20, 0.36), (-0.05, 0.31), (0.08, 0.21)],
                  sole=None, laces=[], lace_w=0.0, heel=[(0.06, 0.30), (0.12, 0.29), (0.10, 0.565), (0.08, 0.565)]),
        back=dict(skin=[(-0.08, -0.08), (-0.09, 0.06), (-0.095, 0.20), (-0.085, 0.28), (0.0, 0.30), (0.085, 0.28),
                        (0.095, 0.20), (0.09, 0.06), (0.08, -0.08)],
                  pump=[(-0.10, 0.12), (-0.105, 0.27), (0.0, 0.31), (0.105, 0.27), (0.10, 0.12), (0.0, 0.17)],
                  sole=None, laces=[], lace_w=0.0, heel=[(-0.03, 0.29), (0.03, 0.29), (0.016, 0.57), (-0.016, 0.57)]),
        sole_y=0.57, material="gloss"),
}
BARE_SOLE_Y = 0.36
SNEAKER_COUNTER = [(-0.14, 0.17), (-0.14, 0.36), (0.0, 0.37), (0.14, 0.36), (0.14, 0.17), (0.0, 0.23)]  # back view
SNEAKER_TAB = [(-0.025, -0.09), (0.025, -0.09), (0.028, 0.06), (-0.028, 0.06)]


def _rounded_box(x0, y0, x1, y1, r, n=5):
    """Rectangle with quarter-circle corners, as points."""
    a = np.linspace(0, np.pi / 2, n)
    corners = [(x1 - r, y0 + r, -np.pi / 2), (x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, np.pi / 2), (x0 + r, y0 + r, np.pi)]
    return np.vstack([np.stack([cx + r * np.cos(a0 + a), cy + r * np.sin(a0 + a)], 1) for cx, cy, a0 in corners])


@dataclass
class HandSpec:
    x: float                       # wrist position in the image
    y: float
    length: float                  # wrist to middle fingertip, px
    angle: float = 0.0             # radians; 0 = fingers point down the screen, + = clockwise
    mirror: bool = False           # False: thumb on screen-left for a hand pointing down; True flips it
    spread: float = 0.35           # 0 = fingers together, 1 = fully splayed
    curl: tuple = (0.1, 0.15, 0.2, 0.25, 0.3)   # thumb, index, middle, ring, pinky; 0 straight, 1 closed
    skin: object = "#f8e0d2"
    nails: bool = True
    forearm: bool = False          # add a forearm stub (for standalone hand studies)
    open_wrist: bool = False       # no outline across the wrist (the hand continues an arm)
    breadth: float = 1.0           # palm and finger width multiplier (1.12 = a broad male hand)
    shape: str = "natural"         # natural (spread / curl apply) / fist / point (index out) / grip (around a held thing)
    line: float = 1.0
    group: str = "hand"


class Hand:
    def __init__(self, spec):
        self.s = spec
        self.px = spec.length / 260.0

    def to_image(self, p):
        s = self.s
        p = np.asarray(p, float).reshape(-1, 2) * [(-1 if s.mirror else 1) * s.breadth, 1] * s.length
        c, sn = np.cos(s.angle), np.sin(s.angle)
        return np.stack([s.x + p[:, 0] * c - p[:, 1] * sn, s.y + p[:, 0] * sn + p[:, 1] * c], 1)

    def _shadow(self, depth=1.5):
        return np.clip(rgb(self.s.skin) * (1 - depth + depth * np.array([0.80, 0.58, 0.58])), 0, 1)

    def _chain(self, base, lengths, angle_deg, curl, bend_toward=0.0):
        """Joint positions of one digit. Curl foreshortens each phalanx and leans it inward."""
        pts, p = [np.array(base, float)], np.array(base, float)
        for k, seg in enumerate(lengths):
            a = np.radians(angle_deg + (bend_toward - angle_deg) * curl * 0.5 * (k + 1) / len(lengths))
            shorten = 1 - CURL_SHORTEN[min(k, 2)] * curl
            p = p + np.array([np.sin(a), np.cos(a)]) * seg * shorten
            pts.append(p.copy())
        return np.array(pts)

    def _digit(self, name, joints, width, curl, width_keys=None, skip_creases=0):
        s, px = self.s, self.px
        # start inside the palm so the root is covered, then run through the joints
        root = joints[0] - (joints[1] - joints[0]) * (0.35 if width_keys is None else 0.0)
        axis = catmull_rom(self.to_image(np.vstack([root, joints]) if width_keys is None else joints), samples=8)
        w = width * s.length * s.breadth
        keys = [(t, w * k) for t, k in FINGER_WIDTHS] if width_keys is None else \
               [(t, k * s.length * s.breadth) for t, k in width_keys]
        ribbon = Ribbon(axis, keys, step=2.0)
        shadow = self._shadow()
        strokes = []
        joint_img = self.to_image(joints)
        for k in range(1 + skip_creases, len(joints) - 1):  # creases over the knuckles
            d = joint_img[k + 1] - joint_img[k - 1]
            nrm = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-6)
            strokes.append(Stroke(np.array([joint_img[k] - nrm * w * 0.62, joint_img[k] + nrm * w * 0.62]),
                                  width=1.3 * px, color=shadow, alpha=0.5))
        parts = [Part(f"{name}", s.skin, ribbon=ribbon, material="skin",
                      line=Line(2.0 * px * s.line, caps=(False, True), shade_gain=0.5),
                      strokes=strokes, fade_t=(0.0, 0.16), group=s.group, focus=0.6)]
        if s.nails and curl < 0.6:
            tip, prev = joints[-1], joints[-2]
            c = self.to_image(prev + (tip - prev) * 0.62)[0]
            ang = np.arctan2(*(self.to_image(tip)[0] - self.to_image(prev)[0])[::-1])
            nail = ellipse(c[0], c[1], np.linalg.norm(tip - prev) * s.length * 0.36, w * 0.62, ang, n=24)
            parts.append(Part(f"{name}_nail", mix(s.skin, "#f6b8b4", 0.45), polys=[nail], shade=False,
                              material="flat", receive=False, group=s.group,
                              line=Line(1.0 * px * s.line, color=mix(shadow, "#ffffff", 0.2), alpha=0.7)))
        return parts

    def _closed(self, extended=()):
        """A fist seen from the back of the hand; fingers named in extended are drawn straight instead."""
        s, px = self.s, self.px
        line = Line(2.0 * px * s.line, shade_gain=0.5)
        back = Part("palm", s.skin, polys=[catmull_rom(self.to_image(FIST_BACK), closed=True, samples=6)],
                    material="skin", bulge=0.5, line=line, group=s.group, focus=0.6)
        if s.open_wrist:
            back.erase = [(self.to_image([(-0.3, -0.10), (0.3, -0.10), (0.3, 0.015), (-0.3, 0.015)]), 0.02 * s.length)]
            back.line = Line(2.0 * px * s.line, shade_gain=0.5, paths=[catmull_rom(self.to_image(FIST_BACK[1:-1]), samples=6)])
        parts = []                                             # folded fingers first: the knuckles lie over them
        shadow = self._shadow()
        for name in ("pinky", "ring", "middle", "index"):
            if name in extended:
                continue
            x0, x1, y1 = FIST_FINGERS[name]
            box = _rounded_box(x0, FIST_TOP, x1, y1, 0.045)
            crease = self.to_image([(x0 + 0.015, FIST_CREASE), ((x0 + x1) / 2, FIST_CREASE + 0.012), (x1 - 0.015, FIST_CREASE)])
            parts.append(Part(f"fist_{name}", s.skin, polys=[self.to_image(box)],
                              material="skin", bulge=0.7, line=Line(1.8 * px * s.line, shade_gain=0.5), group=s.group,
                              focus=0.6, strokes=[Stroke(catmull_rom(crease, samples=6), width=1.2 * px, color=shadow,
                                                         alpha=0.55)]))
        parts.append(back)
        for name in extended:                                  # a pointing finger: straight from its knuckle
            f = FINGERS[name]
            joints = self._chain(f["base"], [f["length"] * r for r in PHALANX_RATIO], f["rest"], 0.0)
            parts += self._digit(name, joints, f["width"], 0.0)
        thumb = Ribbon(catmull_rom(self.to_image(FIST_THUMB["axis"]), samples=8),
                       [(t, w * s.length * s.breadth) for t, w in FIST_THUMB["widths"]], step=2.0)
        parts.append(Part("thumb", s.skin, ribbon=thumb, material="skin", line=Line(2.0 * px * s.line, shade_gain=0.5),
                          group=s.group, focus=0.6))
        return parts

    def parts(self):
        s, px = self.s, self.px
        if s.shape in ("fist", "grip"):
            return self._closed()
        if s.shape == "point":
            return self._closed(extended=("index",))
        curls = s.curl
        palm = Part("palm", s.skin, polys=[catmull_rom(self.to_image(PALM), closed=True, samples=6)],
                    material="skin", bulge=0.5, line=Line(2.0 * px * s.line, shade_gain=0.5), group=s.group,
                    focus=0.6)
        parts = [palm]
        if s.forearm:
            arm = Ribbon(self.to_image(FOREARM["axis"]), [(t, w * s.length) for t, w in FOREARM["widths"]],
                         step=4.0, round_start=False)
            parts = [Part("forearm", s.skin, ribbon=arm, material="skin", group=s.group,
                          line=Line(2.0 * px * s.line, shade_gain=0.5)), palm]
        if s.forearm or s.open_wrist:
            palm.erase = [(self.to_image([(-0.3, -0.10), (0.3, -0.10), (0.3, 0.015), (-0.3, 0.015)]), 0.02 * s.length)]
            palm.line = Line(2.0 * px * s.line, shade_gain=0.5,
                             paths=[catmull_rom(self.to_image(PALM[1:-1]), samples=6)])
        for i, name in reversed(list(enumerate(("index", "middle", "ring", "pinky")))):
            f = FINGERS[name]
            angle = f["rest"] + (f["spread"] - f["rest"]) * s.spread
            lengths = [f["length"] * r for r in PHALANX_RATIO]
            joints = self._chain(f["base"], lengths, angle, curls[i + 1])
            parts += self._digit(name, joints, f["width"], curls[i + 1])
        angle = THUMB["rest"] + (THUMB["spread"] - THUMB["rest"]) * s.spread
        joints = self._chain(THUMB["base"], THUMB["lengths"], angle, curls[0], bend_toward=10.0)
        parts += self._digit("thumb", joints, THUMB["widths"][-1][1], curls[0],
                             width_keys=THUMB["widths"], skip_creases=1)
        return parts


@dataclass
class FootSpec:
    x: float                       # ankle position in the image
    y: float
    unit: float                    # px per head height of the figure this foot belongs to
    angle: float = 0.0             # radians, + = clockwise on screen
    mirror: bool = False           # False = big toe / toe tips on screen-left
    view: str = "front"            # front (toes toward the viewer) / side (toes to one side) / back (heel)
    skin: object = "#f8e0d2"
    line: float = 1.0
    group: str = "foot"
    merge: str = "foot"            # ink key; give a figure's key to ink the foot together with its leg
    scale: float = 1.0             # foot size multiplier (1.08 = a male foot)
    shoe: str = None               # sneakers / boots / heels, None = barefoot (SHOES)
    shoe_color: object = "#ecebe7"


class Foot:
    """A standing foot: one outline plus its toes. The toes are inked as part of the same
    surface, so each shows as a short contour where it overlaps the foot."""

    def __init__(self, spec):
        self.s = spec
        self.px = spec.unit / 150.0

    def to_image(self, p):
        s = self.s
        p = np.asarray(p, float).reshape(-1, 2) * [(-1 if s.mirror else 1), 1] * s.unit * s.scale
        c, sn = np.cos(s.angle), np.sin(s.angle)
        return np.stack([s.x + p[:, 0] * c - p[:, 1] * sn, s.y + p[:, 0] * sn + p[:, 1] * c], 1)

    def outline(self):
        """Closed outline of the foot without toes (to union into a leg, or to draw alone); in a shoe the
        outline the leg ends in: the shoe's silhouette, or for a pump the arched foot."""
        if self.s.shoe:
            return catmull_rom(self.to_image(SHOES[self.s.shoe][self.s.view]["skin"]), closed=True, samples=6)
        return catmull_rom(self.to_image(FOOT_SHAPES[self.s.view][0]), closed=True, samples=6)

    def sole_y(self):
        """Depth of the sole below the ankle, in units: where the ground is."""
        return SHOES[self.s.shoe]["sole_y"] if self.s.shoe else BARE_SOLE_Y

    def _shoe_parts(self):
        s, px = self.s, self.px
        spec, view = SHOES[s.shoe], SHOES[s.shoe][s.view]
        col = rgb(s.shoe_color)
        line = Line(1.8 * px * s.line, color=mix(col, "#0c0a14", 0.65))
        key = f"shoe_{id(self)}"
        body_pts = view.get("pump", view["skin"])
        body = Part(key, col, polys=[catmull_rom(self.to_image(body_pts), closed=True, samples=6)],
                    material=spec["material"], bulge=0.55, line=line, group=s.group)
        parts = [body]
        if "heel" in view:                                 # the heel under the arch
            parts.insert(0, Part(key + "_heel", mix(col, "#0c0a14", 0.25), polys=[self.to_image(view["heel"])],
                                 material=spec["material"], line=line, group=s.group))
        if view["sole"] is not None:                       # a light rubber band along the bottom
            band = self.to_image([(-0.8, view["sole"]), (0.8, view["sole"]), (0.8, 0.8), (-0.8, 0.8)])
            sole_col = "#f4f2ee" if s.shoe == "sneakers" else mix(col, "#0c0a14", 0.5)
            parts.append(Part(key + "_sole", sole_col, polys=[band], shade=False, material="flat", clip=key,
                              receive=False))
        dark = mix(col, "#0c0a14", 0.5)
        for (x, y, w) in [(x, y, view["lace_w"]) for x, y, _ in [(p[0], p[1], 0) for p in view["laces"]]]:
            if s.view == "front":
                pts = [(-w, y), (0.0, y + 0.012), (w, y)]
            else:
                pts = [(x + w * 0.4, y - w * 0.5), (x - w * 0.4, y + w * 0.5)]
            body.strokes.append(Stroke(self.to_image(pts) if s.view == "side" else self.to_image([(p[0], p[1]) for p in pts]),
                                       width=1.4 * px, color=dark, alpha=0.8, clip=True))
        if s.shoe == "sneakers" and view["sole"] is not None:   # the edge of the rubber sole
            body.strokes.append(Stroke(self.to_image([(-0.8, view["sole"]), (0.8, view["sole"])]), width=1.3 * px,
                                       color=dark, alpha=0.55, taper=(False, False), clip=True))
        if s.shoe == "sneakers" and s.view == "back":      # heel counter, pull tab and the collar around the ankle
            parts.insert(1, Part(key + "_counter", mix(col, "#7d8796", 0.45), polys=[catmull_rom(self.to_image(SNEAKER_COUNTER),
                                                                                                 closed=True, samples=5)],
                                 material=spec["material"], bulge=0.4, clip=key, line=Line(1.2 * px * s.line, color=dark, alpha=0.6),
                                 group=s.group))
            parts.insert(2, Part(key + "_tab", mix(col, "#7d8796", 0.45), polys=[self.to_image(SNEAKER_TAB)], material="matte",
                                 line=Line(1.0 * px * s.line, color=dark, alpha=0.6), group=s.group))
            body.strokes.append(Stroke(catmull_rom(self.to_image([(-0.11, 0.0), (0.0, 0.03), (0.11, 0.0)]), samples=6),
                                       width=1.3 * px, color=dark, alpha=0.6, clip=True))
        if s.shoe == "boots" and s.view == "front":        # the seam where the shaft meets the foot
            body.strokes.append(Stroke(catmull_rom(self.to_image([(-0.13, 0.10), (0.0, 0.14), (0.13, 0.10)]), samples=6),
                                       width=1.2 * px, color=dark, alpha=0.6, clip=True))
        return parts

    def toe_parts(self):
        s, px = self.s, self.px
        if s.shoe:
            return self._shoe_parts()
        parts = []
        for i, (x, y, rx, ry) in reversed(list(enumerate(FOOT_SHAPES[s.view][1]))):
            c = self.to_image([(x, y)])[0]
            toe = ellipse(c[0], c[1], rx * s.unit * s.scale, ry * s.unit * s.scale, s.angle, n=28)
            parts.append(Part(f"toe_{i}", s.skin, polys=[toe], material="skin", bulge=0.8,
                              line=Line(1.7 * px * s.line, shade_gain=0.5), group=s.group, merge=s.merge))
            if s.view == "front":
                nail_c = self.to_image([(x, y - ry * 0.12)])[0]
                nail = ellipse(nail_c[0], nail_c[1], rx * s.unit * s.scale * 0.55, ry * s.unit * s.scale * 0.42, s.angle, n=18)
                parts.append(Part(f"toe_{i}_nail", mix(s.skin, "#f6b8b4", 0.5), polys=[nail], shade=False,
                                  material="flat", receive=False, alpha=0.8, group=s.group))
        return parts

    def parts(self):
        """Standalone foot (for studies). In a figure the outline is unioned into the leg instead."""
        s, px = self.s, self.px
        foot = Part("foot", s.skin, polys=[self.outline()], material="skin", bulge=0.6,
                    line=Line(2.0 * px * s.line, shade_gain=0.5), group=s.group, merge=s.merge)
        return [foot] + self.toe_parts()
