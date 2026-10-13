"""Neck, shoulders and a simple top for bust portraits.

Coordinates continue the head's vertical scale: v in head heights from the top
of the skull (chin = 1.0, pit of the neck ~ 1.34, shoulder tips ~ 1.47).
"""
from dataclasses import dataclass

import numpy as np

from ..color import rgb
from ..geometry import catmull_rom, ellipse, Ribbon
from ..scene import Part, Line, Stroke

# right half of the torso outline (x, v); mirrored for the left
TORSO_HALF = [(0.13, 1.19), (0.27, 1.29), (0.47, 1.355), (0.62, 1.41), (0.665, 1.52), (0.60, 1.78),
              (0.555, 2.0), (0.535, 2.35), (0.50, 2.75), (0.53, 3.2), (0.60, 3.7)]
ARM_AXIS = [(0.655, 1.55), (0.70, 2.1), (0.725, 2.8), (0.74, 3.7)]          # right upper arm
ARM_WIDTH = [(0, 0.125), (0.25, 0.128), (0.7, 0.108), (1, 0.100)]          # half width along it
# right half of each garment: a smooth upper edge from the center line outward, then the side
# seam down to below the picture. Edge and seam meet in a corner.
OUTFITS = {
    "camisole": dict(edge=[(0.0, 1.86), (0.15, 1.74), (0.25, 1.54), (0.29, 1.352), (0.33, 1.348), (0.37, 1.54),
                           (0.47, 1.78), (0.565, 1.95)],
                     seam=[(0.545, 2.35), (0.51, 2.75), (0.54, 3.2), (0.61, 3.7)]),
    "tshirt": dict(edge=[(0.0, 1.475), (0.07, 1.468), (0.15, 1.41), (0.20, 1.27), (0.45, 1.335), (0.63, 1.395), (0.68, 1.52)],
                   seam=[(0.62, 1.80), (0.57, 2.0), (0.55, 2.35), (0.52, 2.75), (0.55, 3.2), (0.62, 3.7)]),
    "offshoulder": dict(edge=[(0.0, 1.80), (0.20, 1.79), (0.42, 1.755), (0.62, 1.70), (0.78, 1.66), (0.855, 1.70)],
                        seam=[(0.875, 1.95), (0.86, 2.6), (0.86, 3.7)]),
}
SLEEVE_T = 0.30        # t-shirt sleeves cover this fraction of the upper arm
# a male torso: steeper trapezius from the neck, squarer shoulders, a straighter side
TORSO_HALF_MALE = [(0.14, 1.17), (0.25, 1.25), (0.43, 1.32), (0.60, 1.385), (0.665, 1.50), (0.62, 1.78),
                   (0.585, 2.0), (0.565, 2.35), (0.55, 2.75), (0.55, 3.2), (0.58, 3.7)]
# per sex: torso outline, x scale of the whole bust, arm half widths, neck half widths (top, middle, low, base)
BODY = {
    "female": dict(torso=TORSO_HALF, width=1.0, arm=ARM_WIDTH, axis=ARM_AXIS, neck=(0.125, 0.116, 0.130, 0.18)),
    # the thicker male arm starts lower and further in, so its rounded top stays under the shoulder line
    "male": dict(torso=TORSO_HALF_MALE, width=1.16, arm=[(0, 0.140), (0.25, 0.146), (0.7, 0.122), (1, 0.112)],
                 axis=[(0.635, 1.60), (0.685, 2.1), (0.71, 2.8), (0.725, 3.7)], neck=(0.150, 0.146, 0.158, 0.22)),
}
# garments cut for the male torso; the others fall back to the shared table
OUTFITS_MALE = {
    "tshirt": dict(edge=[(0.0, 1.462), (0.07, 1.455), (0.14, 1.40), (0.18, 1.245), (0.25, 1.238), (0.43, 1.308),
                         (0.60, 1.372), (0.675, 1.50)],
                   seam=[(0.635, 1.80), (0.60, 2.0), (0.58, 2.35), (0.565, 2.75), (0.565, 3.2), (0.595, 3.7)]),
}

# the upper edge seen from behind: a t-shirt sits high on the nape, a camisole dips in a low scoop
BACK_EDGES = {
    "camisole": [(0.0, 1.98), (0.18, 1.95), (0.27, 1.70), (0.29, 1.352), (0.33, 1.348), (0.37, 1.54), (0.47, 1.78),
                 (0.565, 1.95)],
    "tshirt": [(0.0, 1.30), (0.08, 1.295), (0.15, 1.27), (0.20, 1.24), (0.45, 1.335), (0.63, 1.395), (0.68, 1.52)],
}
BACK_EDGES_MALE = {
    "tshirt": [(0.0, 1.28), (0.09, 1.27), (0.16, 1.24), (0.20, 1.225), (0.25, 1.238), (0.43, 1.308), (0.60, 1.372),
               (0.675, 1.50)],
}


@dataclass
class BustSpec:
    outfit: str = "camisole"        # camisole / tshirt / offshoulder / bare
    cloth: object = "#2f3e5c"
    shoulder: float = 1.0           # shoulder width multiplier
    turn: float = 0.0               # -1..1, body turned left / right (foreshortens the far shoulder)
    bust: float = 1.0               # chest volume multiplier (female only)
    sex: str = "female"             # female / male: torso outline, widths, neck and chest under the cloth
    view: str = "front"             # front / back: seen from behind, no clavicles or throat; the spine at the nape


class Bust:
    def __init__(self, head, spec=None):
        self.h, self.b = head, spec or BustSpec()
        self.size = head.s.size
        self.body = BODY[self.b.sex]

    def B(self, x, v):
        """Body-frame point (no head roll) to image coordinates."""
        hs, t = self.h.s, self.b.turn
        x = np.asarray(x, float) * self.b.shoulder * self.body["width"]
        x = np.where(x * t > 0, x * (1 - 0.20 * abs(t)), x * (1 + 0.04 * abs(t))) + 0.05 * t
        return np.stack([hs.cx + x * hs.size, hs.top + np.asarray(v, float) * hs.size], -1)

    def _mirror_poly(self, half):
        half = np.asarray(half, float)
        left = half[::-1] * [-1, 1]
        keep = left[:, 0] < -1e-6                       # do not duplicate center-line points
        pts = np.vstack([half, left[keep]])
        return catmull_rom(self.B(pts[:, 0], pts[:, 1]), closed=True, samples=8)

    def _skin_shadow(self, depth=1.4):
        return self.h._skin_shadow(depth)

    def _arm(self, sd):
        hs, px, size = self.h.s, self.h.px, self.size
        ax = np.array(self.body["axis"])
        ribbon = Ribbon(catmull_rom(self.B(sd * ax[:, 0], ax[:, 1]), samples=10),
                        [(t, w * size) for t, w in self.body["arm"]], step=4.0)
        # axis runs down the screen: side A is screen-left. Ink the outer side from the
        # shoulder cap, the inner side only below the armpit where it leaves the chest.
        n = ribbon.n
        cap = ribbon.cap(0)
        if sd > 0:
            outer = np.vstack([cap[len(cap) // 2:], ribbon.side_b]) if cap is not None else ribbon.side_b
            inner = ribbon.side_a[int(n * 0.17):]
        else:
            outer = np.vstack([cap[:len(cap) // 2 + 1][::-1], ribbon.side_a]) if cap is not None else ribbon.side_a
            inner = ribbon.side_b[int(n * 0.17):]
        arm = Part(f"arm_{sd}", hs.skin, ribbon=ribbon, material="skin",
                   line=Line(2.4 * px * hs.line, paths=[outer, inner], shade_gain=0.6, taper=(False, True)),
                   group="body")
        return arm, ribbon

    def _sleeve(self, sd, ribbon):
        n = max(3, int(ribbon.n * SLEEVE_T))
        sleeve = Ribbon(ribbon.axis[:n], ribbon.wa[:n] * 1.14, ribbon.wb[:n] * 1.14, step=4.0, round_end=False)
        return Part(f"sleeve_{sd}", self.b.cloth, ribbon=sleeve, material="cloth",
                    line=Line(2.2 * self.h.px * self.h.s.line, caps=(True, False)), group="garment")

    def parts(self):
        hs, px, size = self.h.s, self.h.px, self.size
        torso_poly = self._mirror_poly([(0.0, 1.24)] + self.body["torso"])
        strokes = []
        back = self.b.view == "back"
        for sd in (-1, 1):
            if back:                                     # the trapezius edge from the nape out to the shoulder
                bone = self.B(sd * np.array([0.10, 0.25, 0.42]), [1.25, 1.36, 1.40])
            else:
                bone = self.B(sd * np.array([0.05, 0.18, 0.34, 0.47]), [1.335, 1.352, 1.335, 1.345])
            strokes.append(Stroke(catmull_rom(bone, samples=8), width=1.6 * px, color=self._skin_shadow(),
                                  alpha=0.35 if back else 0.6))
        if back:                                         # the spine running down from the nape
            strokes.append(Stroke(self.B([0.0, 0.0], [1.30, 1.9]), width=1.4 * px, color=self._skin_shadow(), alpha=0.35))
        torso = Part("torso", hs.skin, polys=[torso_poly], material="skin", bulge=0.45,
                     line=Line(2.4 * px * hs.line, shade_gain=0.6), strokes=strokes, group="body")

        top = self.h.neck_top()
        base = self.B(0.0, 1.37)
        axis = np.array([top, (top * 0.45 + base * 0.55), base])
        neck_w = self.body["neck"]
        neck_ribbon = Ribbon(catmull_rom(axis, samples=10),
                             [(t, w * size) for t, w in zip((0, 0.45, 0.8, 1), neck_w)], step=4.0)
        n = neck_ribbon.n
        cut = int(n * 0.80)
        tendon = [Stroke(np.array([neck_ribbon.axis[int(n * 0.35)] + [sd * 0.085 * size, 0],
                                   neck_ribbon.axis[int(n * 0.86)] + [sd * 0.030 * size, 0]]),
                         width=1.4 * px, color=self._skin_shadow(), alpha=0.35) for sd in (-1, 1)]
        if self.b.view == "back":
            tendon = []
        elif self.b.sex == "male":
            tendon.append(self._adams_apple(neck_ribbon))
        neck = Part("neck", hs.skin, ribbon=neck_ribbon, material="skin", flatness=1.2,
                    line=Line(2.2 * px * hs.line, paths=[neck_ribbon.side_a[:cut], neck_ribbon.side_b[:cut]]),
                    fade_t=(0.0, 0.01, 0.72, 0.98), strokes=tendon, group="body")
        arms = [self._arm(sd) for sd in (-1, 1)]
        arm_parts = [a for a, _ in arms]
        outfit = self.b.outfit
        if outfit == "bare":
            return [torso, neck] + arm_parts
        if outfit == "camisole":                      # arms pass in front of the garment's sides
            return [torso, neck] + self._outfit() + arm_parts
        if outfit == "tshirt":
            sleeves = [self._sleeve(sd, r) for sd, (_, r) in zip((-1, 1), arms)]
            return [torso, neck] + arm_parts + self._outfit() + sleeves
        return [torso, neck] + arm_parts + self._outfit()

    def _adams_apple(self, neck_ribbon):
        """A short shaded curve below the jaw shadow: the thyroid cartilage."""
        px, size = self.h.px, self.size
        c = neck_ribbon.axis[int(neck_ribbon.n * 0.45)]
        arc = c + np.array([[-0.030, 0.012], [0.0, 0.026], [0.030, 0.012]]) * size
        return Stroke(catmull_rom(arc, samples=6), width=1.5 * px, color=self._skin_shadow(), alpha=0.45)

    def _garment_poly(self):
        spec = (OUTFITS_MALE if self.b.sex == "male" else {}).get(self.b.outfit, OUTFITS[self.b.outfit])
        edge, seam = np.array(spec["edge"]), np.array(spec["seam"])
        if self.b.view == "back":
            edges = (BACK_EDGES_MALE if self.b.sex == "male" else {}).get(self.b.outfit, BACK_EDGES.get(self.b.outfit))
            edge = np.array(edges) if edges is not None else edge
        right = np.vstack([catmull_rom(self.B(edge[:, 0], edge[:, 1]), samples=8),
                           catmull_rom(self.B(seam[:, 0], seam[:, 1]), samples=6)])
        left = np.vstack([catmull_rom(self.B(-edge[:, 0], edge[:, 1]), samples=8),
                          catmull_rom(self.B(-seam[:, 0], seam[:, 1]), samples=6)])
        return np.vstack([right, left[::-1]])

    def _outfit(self):
        px, size, cloth = self.h.px, self.size, rgb(self.b.cloth)
        poly = self._garment_poly()
        garment = Part("garment", cloth, polys=[poly], material="cloth", bulge=0.35,
                       line=Line(2.2 * px * self.h.s.line), group="garment")
        parts = [garment]
        if self.b.sex == "male" or self.b.view == "back":
            return parts                          # a flat chest, or the back: no swell under the cloth
        for sd in (-1, 1):
            c = self.B(sd * 0.25, 1.98)
            rx, ry = 0.25 * size * self.b.bust, 0.235 * size * self.b.bust
            form = ellipse(c[0], c[1], rx, ry)
            # a gentle swell under the cloth: mostly lit, fading out upward, no outline
            parts.append(Part(f"bust_{sd}", cloth, polys=[form], material="cloth", bulge=0.42, light_bias=0.22,
                              clip="garment", erase=[(ellipse(c[0], c[1] - ry * 0.75, rx * 1.4, ry * 1.0), 0.12 * size)],
                              alpha=0.85, group="garment"))
        return parts
