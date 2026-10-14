"""Everyday and occasion wear: sportswear, office wear, party dresses, homewear.

Mixed into OutfitBuilder, so every garment reuses its helpers (cloth, torso,
neck_hole, tank_holes, pants_layers, bust_form). Fitted garments (pencil
skirt, slip and halter dresses) wrap torso, bust and thighs as one shape and
fill the gap between the legs; leggings and slacks are pants with a small or
regular ease. Dimensions are body-local H units.
"""
import cv2
import numpy as np

from . import color as col
from . import geom
from .body import mirror
from .scene import Blend, Layer, LineSpec, Material, ShadeSpec

WAIST = {"leggings": 1.62, "joggers": 1.86, "slacks": 1.80, "pencil_skirt": 1.56, "dolphin_shorts": 1.95}
EASE = {"leggings": 0.008, "joggers": 0.060, "slacks": 0.045, "pencil_skirt": 0.025, "dolphin_shorts": 0.022}
PENCIL_HEM = 3.55
DOLPHIN_HEM = 2.60
DRESS_HEM = {"slip_dress": 3.05, "halter_dress": 2.92}
CAMI_HEM = 2.05
TEE_HEM = {"tee": 2.25, "oversized_tee": 2.82}
BAND_DEPTH = 0.10          # waistbands, sports-bra underband, cuffs
SATIN_SHEEN = 0.55
TIE_COLOR = "#7A2E3A"
BOW_COLOR = "#2F3542"
TRIM_COLOR = "#F4F1EC"
HIP_HULL_TOP = 2.02
BACK_NECKLINE_Y = 0.55     # straight back neckline of camisoles and slip dresses
HALTER_BACK = 1.45         # an open-back halter dress starts covering here        # fitted skirts follow the body above this height, a smooth shell below


class WardrobeMixin:
    # ------------------------------------------------------------ shared shapes
    def hem_clip(self, name, hem_y, top=-3.0):
        P = self.body.pelvis(np.array([(-2.0, top), (2.0, top), (2.0, hem_y), (0.0, hem_y + 0.02), (-2.0, hem_y)]))
        return self.helper(name, [self.C(P, 0.2)])

    def fitted_polys(self, ease, hem_y, with_torso=True):
        """Torso (with bust) above the hips, and one smooth shell from the hips over both thighs to the hem.

        How: below the widest hip point the outline is the convex hull of the hips and thighs, so a
        fitted skirt tapers in one curve instead of showing the hip-thigh notch or the gap between legs.
        """
        polys = self.torso(ease) if with_torso else []
        hips = self.body.torso_local(ease)
        pts = [hips[hips[:, 1] > HIP_HULL_TOP]]
        for side in (-1, 1):
            for part in ("thigh", "calf") if hem_y > 3.4 else ("thigh",):
                for p in self.body.leg_local(side, part, ease):
                    pts.append(p[p[:, 1] < hem_y + 0.1])
        P = np.vstack([q for q in pts if len(q)]).astype(np.float32)
        hull = cv2.convexHull(P)[:, 0, :].astype(np.float64)
        polys.append(self.C(hull, 0.2))
        return polys

    def satin(self, name, clip):
        """Glossy streaks that make satin read as satin."""
        streaks = []
        for x, y0, y1 in ((-0.30, 1.40, 2.60), (0.22, 1.30, 2.80), (0.05, 2.10, 2.95)):
            sp = geom.catmull_rom(np.array([(x, y0), (x * 1.08, (y0 + y1) / 2), (x * 0.95, y1)]), 8)
            streaks.append((self.C(sp), geom.tapered_widths(len(sp), 0.05 * self.H, 0.5, 0.5)))
        return Layer(f"{name}_sheen", Material.FLAT, col.light_of(self.color, 0.6), strokes=streaks, clip=clip,
                     blend=Blend.SCREEN, feather=0.02 * self.H, opacity=0.35)

    def strap_strokes(self, name, pts_pairs, width=0.016, color=None):
        strokes = []
        for a, b in pts_pairs:
            sp = geom.catmull_rom(np.array([a, (a + b) / 2 + [0.0, -0.02], b]), 8)
            strokes.append((self.C(sp), np.full(len(sp), width * self.H)))
        return Layer(name, Material.INK, self.color if color is None else color, strokes=strokes,
                     tags=("garment", "garment_top"))

    def neckline_cut(self, name, right_half):
        """Helper covering everything above a neckline given as its image-right half (center first)."""
        R = np.array(right_half, dtype=np.float64)
        if self.back:
            R[:, 1] = BACK_NECKLINE_Y        # camisoles and slips run straight across the back
        P = np.vstack([mirror(R[::-1]), R[1:], [(R[-1][0], -3.0), (-R[-1][0], -3.0)]])
        return self.helper(name, [self.S(geom.catmull_rom(P, 6, closed=True, alpha=0.9))])

    def lace(self, name, right_half):
        """Scalloped trim along a neckline."""
        R = np.array(right_half, dtype=np.float64)
        line = geom.resample(geom.catmull_rom(np.vstack([mirror(R[::-1]), R[1:]]), 8), 0.028)
        dots = [self.C(geom.ellipse(x, y + 0.004, 0.017, 0.015, 14)) for x, y in line]
        clip = ("torso_mask", "bust_mask") if self.body.has_bust else ("torso_mask",)
        return Layer(name, Material.FLAT, col.light_of(self.color, 0.45), polys=dots, clip=clip,
                     line=LineSpec(0.002 * self.H), tags=("garment", "garment_top"))

    # ------------------------------------------------------------ bottoms
    def _leggings(self, g):
        w = WAIST["leggings"]
        g["bottom"] += self.pants_layers("leggings", w, 7.0, EASE["leggings"], 0.08)
        band = self.body.pelvis(self.waist_edge(w + BAND_DEPTH))
        seams = [([self.body.pelvis([(side * 0.50, w + 0.12)])[0], self.thigh_outer(side, 3.2, 0.03),
                   self.body.leg_joints(side)[2] + [side * 0.06, -0.1]], 0.8) for side in (-1, 1)]
        g["bottom"] += [self.ink("leggings_band", [(band[np.abs(band[:, 0]) < 0.62], 0.9)], color=self.bottom_color,
                                 opacity=0.55, clip=("leggings",)),
                        self.ink("leggings_seams", seams, color=self.bottom_color, opacity=0.35, clip=("leggings",))]

    def _joggers(self, g):
        w = WAIST["joggers"]
        g["bottom"] += self.pants_layers("joggers", w, 7.0, EASE["joggers"], 0.12)
        cuffs, folds = [], []
        for side in (-1, 1):
            _, knee, ankle = self.body.leg_joints(side)
            half = self.body.widths["calf"][-1] / 2 + EASE["joggers"] * 0.6
            a = ankle + [0.0, -0.02]
            cuffs.append(self.C(np.array([a + [-half, -BAND_DEPTH * 1.3], a + [half, -BAND_DEPTH * 1.3],
                                          a + [half, 0.0], a + [-half, 0.0]])))
            for k in range(3):
                y = a[1] - BAND_DEPTH * 1.3 - 0.05 - k * 0.07
                folds.append(([(a[0] - half * 0.8, y), (a[0], y + 0.02), (a[0] + half * 0.8, y)], 0.7))
        cords = [([(s * 0.03, w + 0.08), (s * 0.05, w + 0.22), (s * 0.035, w + 0.33)], 1.0) for s in (-1, 1)]
        g["bottom"] += [self.cloth("joggers_cuffs", cuffs, inflate=0.03, color=col.shadow_of(self.bottom_color, 0.08),
                                   tags=("garment", "pants")),
                        self.ink("joggers_folds", folds, color=self.bottom_color, opacity=0.45, clip=("joggers",)),
                        self.ink("joggers_cords", cords, color="#F2EFE8", opacity=0.9, width=0.006)]

    def _slacks(self, g):
        w = WAIST["slacks"]
        g["bottom"] += self.pants_layers("slacks", w, 7.0, EASE["slacks"], 0.10)
        creases = []
        for side in (-1, 1):
            hip, knee, ankle = self.body.leg_joints(side)
            creases.append(([hip + [0.0, 0.25], knee, ankle + [0.0, -0.05]], 0.8))
        belt = self.body.pelvis(np.vstack([self.waist_edge(w - 0.005), self.waist_edge(w + 0.085)[::-1]]))
        buckle = self.C(self.body.pelvis(np.array([(-0.045, w + 0.01), (0.045, w + 0.01), (0.045, w + 0.085),
                                                   (-0.045, w + 0.085)])))
        g["bottom"] += [self.ink("slacks_creases", creases, color=self.bottom_color, opacity=0.4, clip=("slacks",)),
                        self.cloth("belt", [self.C(belt, 0.2)], clip=("slacks",), inflate=0.02,
                                   color=col.hex_rgb("#2A2420"), tags=("garment", "pants")),
                        Layer("buckle", Material.CLOTH, col.hex_rgb("#C9C3B6"), polys=[buckle],
                              line=LineSpec(0.003 * self.H), shade=ShadeSpec(inflate=0.01 * self.H, spec=0.8))]

    def _pencil_skirt(self, g):
        w, ease = WAIST["pencil_skirt"], EASE["pencil_skirt"]
        hem = self.hem(PENCIL_HEM)
        zone = self.body.pelvis(np.vstack([self.waist_edge(w), [(1.5, hem), (0.0, hem + 0.02), (-1.5, hem)]]))
        polys = [self.C(self.body.torso_local(ease), 0.2)] + self.fitted_polys(ease, hem, with_torso=False)
        g["bottom"] += [self.helper("pencil_zone", [self.C(zone, 0.2)]),
                        Layer("pencil_skirt", Material.CLOTH, self.bottom_color, polys=polys, line=self.line,
                              clip=("pencil_zone",), cut=("arms_mask",),
                              shade=ShadeSpec(inflate=0.12 * self.H, cast_tags=("garment_top", "hand"),
                                              cast_dist=0.05 * self.H, threshold=0.12, rim=0.8),
                              tags=("garment", "skirt"))]
        band = self.body.pelvis(self.waist_edge(w + BAND_DEPTH))
        g["bottom"] += [self.ink("pencil_vent", [([(0.0, hem - 0.30), (0.0, hem)], 0.9)],
                                 color=self.bottom_color, opacity=0.5),
                        self.ink("pencil_band", [(band[np.abs(band[:, 0]) < 0.62], 0.9)], color=self.bottom_color,
                                 opacity=0.5, clip=("pencil_skirt",))]

    def _dolphin_shorts(self, g):
        w = WAIST["dolphin_shorts"]
        g["bottom"] += self.pants_layers("dolphin_shorts", w, DOLPHIN_HEM, EASE["dolphin_shorts"], 0.08, gap=0.05,
                                         extra_cut=("dolphin_splits",))
        splits, piping = [], []
        for side in (-1, 1):
            out = self.thigh_outer(side, DOLPHIN_HEM, -0.03)
            arch = np.array([out + [side * 0.04, 0.05], out + [-side * 0.03, 0.0], out + [-side * 0.10, -0.16],
                             out + [-side * 0.17, 0.0], out + [-side * 0.20, 0.05]])
            splits.append(self.C(geom.catmull_rom(arch, 6, closed=True)))
            piping.append((arch[1:-1], 1.0))
            piping.append((self.thigh_hem(side, DOLPHIN_HEM - 0.01, EASE["dolphin_shorts"]), 1.0))
        g["bottom"].insert(0, self.helper("dolphin_splits", splits))
        g["bottom"].append(self.ink("dolphin_piping", piping, color=TRIM_COLOR, opacity=0.95, width=0.006,
                                    clip=("dolphin_shorts",)))

    # ------------------------------------------------------------ tops
    def _sports_bra(self, g):
        cx, cy, rx, ry = self.body.bust
        hem = cy + ry + 0.16
        g["top"] += self.tank_holes("sb", depth=0.34, half=0.22)
        above = self.C(np.array([(-2, -3), (2, -3), (2, hem - BAND_DEPTH), (-2, hem - BAND_DEPTH)]))
        g["top"] += [self.cloth("sports_bra", self.torso(0.015, hem, 0.0), cut=("sb_neck", "sb_arm", "arms_mask"),
                                inflate=0.15, tags=("garment", "swim_top")),
                     self.helper("sb_above_band", [above]),
                     self.cloth("sb_band", self.torso(0.02, hem, 0.0), clip=("sports_bra",), cut=("sb_above_band",),
                                inflate=0.03, color=col.shadow_of(self.color, 0.25), tags=("garment", "swim_top"))]
        g["top"] += self.bust_form("sb", self.color, ("sports_bra",), folds=False)
        return {"clavicles": True, "exposed": True}

    def _camisole(self, g):
        cx, cy, rx, ry = self.body.bust
        top_y = cy - ry * 0.55
        neck = [(0.0, cy - ry * 0.20), (cx * 0.55, top_y - 0.01), (cx + rx * 0.55, top_y), (0.75, top_y + 0.08)]
        g["top"].append(self.neckline_cut("cami_top", neck))
        neck = neck[:-1]          # the trim stops at the bust's outer side
        g["top"].append(self.cloth("camisole", self.torso(0.012, CAMI_HEM, 0.02), cut=("cami_top", "arms_mask"),
                                   inflate=0.14))
        g["top"] += self.bust_form("cami", self.color, ("camisole",), strength=0.9)
        g["top"].append(self.lace("cami_lace", neck))
        g["top"].append(self.strap_strokes("cami_straps", [(np.array((s * (cx + rx * 0.15), top_y + 0.01)),
                                                            np.array((s * 0.33, 0.05))) for s in (-1, 1)]))
        g["top"].append(self.ink("cami_hem", [([(-0.58, CAMI_HEM - 0.04), (0.0, CAMI_HEM - 0.02),
                                               (0.58, CAMI_HEM - 0.04)], 0.8)], opacity=0.35))
        return {"clavicles": True, "exposed": True}

    def _dress_body(self, g, name, neck_cuts, hem):
        hem = self.hem(hem)
        g["top"].append(self.hem_clip(f"{name}_hem", hem))
        g["top"].append(self.cloth(name, self.fitted_polys(0.018, hem), clip=(f"{name}_hem",),
                                   cut=neck_cuts + ("arms_mask",), inflate=0.15, tags=("garment", "dress_part"),
                                   spec=SATIN_SHEEN if name == "slip_dress" else 0.2, spec_edge=0.92))
        g["top"] += self.bust_form(name, self.color, (name,), folds=False)

    def _slip_dress(self, g):
        cx, cy, rx, ry = self.body.bust
        top_y = cy - ry * 0.60
        neck = [(0.0, cy - ry * 0.05), (cx * 0.5, top_y), (cx + rx * 0.6, top_y - 0.01), (0.75, top_y + 0.08)]
        g["top"].append(self.neckline_cut("slip_top", neck))
        self._dress_body(g, "slip_dress", ("slip_top",), DRESS_HEM["slip_dress"])
        g["top"].append(self.satin("slip", ("slip_dress",)))
        cowl = [([(-cx * 0.8, top_y + 0.10), (0.0, cy + ry * 0.10), (cx * 0.8, top_y + 0.10)], 0.7),
                ([(-cx * 0.5, top_y + 0.22), (0.0, cy + ry * 0.30), (cx * 0.5, top_y + 0.22)], 0.6)]
        g["top"].append(self.ink("slip_cowl", cowl, opacity=0.35, clip=("slip_dress",)))
        g["top"].append(self.strap_strokes("slip_straps", [(np.array((s * (cx + rx * 0.10), top_y + 0.01)),
                                                            np.array((s * 0.33, 0.05))) for s in (-1, 1)], 0.012))
        return {"clavicles": True, "exposed": True}

    def _halter_dress(self, g):
        cuts = []
        for side in (-1, 1):
            P = np.array([(0.14, -3.0), (3.0, -3.0), (3.0, 0.72), (0.60, 0.72), (0.36, 0.38), (0.14, -0.02)])
            P[:, 0] *= side
            cuts.append(self.S(geom.catmull_rom(P, 4, closed=True, alpha=0.9)))
        if self.back:
            # a halter dress is open behind down to the small of the back
            open_back = np.array([(-0.70, -3.0), (0.70, -3.0), (0.70, HALTER_BACK - 0.20), (0.0, HALTER_BACK),
                                  (-0.70, HALTER_BACK - 0.20)])
            cuts.append(self.S(geom.catmull_rom(open_back, 6, closed=True, alpha=0.9)))
        g["top"].append(self.helper("halter_cut", cuts))
        self._dress_body(g, "halter_dress", ("halter_cut",), DRESS_HEM["halter_dress"])
        collar = self.C(np.array([(-0.22, -0.13), (0.22, -0.13), (0.23, -0.03), (-0.23, -0.03)]), 0.0)
        g["top"].append(self.cloth("halter_collar", [collar], clip=("neck_mask",), inflate=0.03,
                                   tags=("garment", "garment_top")))
        g["top"].append(self.ink("halter_folds", [([(-0.10, 0.20), (-0.18, 0.55)], 0.7), ([(0.10, 0.20), (0.18, 0.55)], 0.7)],
                                 opacity=0.35, clip=("halter_dress",)))
        return {"clavicles": False, "exposed": True}

    def _tee(self, g, oversized=False):
        kind = "oversized_tee" if oversized else "tee"
        hem = TEE_HEM[kind]
        ease = 0.10 if oversized else 0.035
        g["top"].append(self.neck_hole(f"{kind}_neck", 0.14 if oversized else 0.12, 0.21 if oversized else 0.19))
        g["top"].append(self.cloth(kind, self.torso(ease, hem, 0.02), cut=(f"{kind}_neck", "arms_mask"),
                                   inflate=0.15))
        g["top"] += self.bust_form(kind, self.color, (kind,), folds=not oversized, strength=0.5 if oversized else 0.8)
        band = [(0.21, -0.02), (0.17, 0.08), (0.08, 0.15), (0.0, 0.16)] if oversized else \
               [(0.19, -0.02), (0.16, 0.07), (0.08, 0.13), (0.0, 0.14)]
        outer = [(x * 1.18, y + 0.035) for x, y in band]
        P = self.nx(np.vstack([band, mirror(band[::-1])[1:], mirror(outer), outer[::-1]]))
        g["top"].append(self.cloth(f"{kind}_band", [self.C(geom.catmull_rom(P, 6, closed=True), 0.26)], inflate=0.03))
        for side in (-1, 1):
            g["top"].append(self.cloth(f"{kind}_sleeve_{side}",
                                       self.short_sleeve(side, 0.10 if oversized else 0.05, 0.66 if oversized else 0.45),
                                       inflate=0.09, cut=self.bust_cut, tags=("garment", "sleeve")))
        folds = [([(-0.45, hem - 0.55), (-0.40, hem - 0.05)], 0.8), ([(0.40, hem - 0.60), (0.36, hem - 0.05)], 0.8)]
        if oversized:
            folds += [([(-0.15, 1.30), (-0.22, 2.10)], 0.7), ([(0.18, 1.35), (0.25, 2.20)], 0.7)]
        g["top"].append(self.ink(f"{kind}_folds", folds, opacity=0.4, clip=(kind,)))
        return {"clavicles": False}

    def _oversized_tee(self, g):
        return self._tee(g, oversized=True)

    # ------------------------------------------------------------ shirt accessories
    def necktie(self):
        color = col.hex_rgb(self.s_tie_color)
        knot = self.C(self.nx([(-0.045, 0.30), (0.045, 0.30), (0.035, 0.40), (-0.035, 0.40)]), 0.28)
        blade = self.C(np.array([(-0.032, 0.40), (0.032, 0.40), (0.075, 1.30), (0.0, 1.43), (-0.075, 1.30)]))
        stripe = [(self.C(np.array([(-0.06, y), (0.06, y + 0.05)])), np.full(2, 0.008 * self.H))
                  for y in np.arange(0.55, 1.30, 0.16)]
        return [Layer("tie_blade", Material.CLOTH, color, polys=[blade], line=self.line,
                      shade=ShadeSpec(inflate=0.03 * self.H, threshold=0.12, spec=0.3), tags=("garment",)),
                Layer("tie_stripes", Material.INK, col.light_of(color, 0.35), strokes=stripe, clip=("tie_blade",),
                      opacity=0.7),
                Layer("tie_knot", Material.CLOTH, color, polys=[knot], line=self.line,
                      shade=ShadeSpec(inflate=0.02 * self.H, threshold=0.12, spec=0.3), tags=("garment",))]

    def neck_bow(self):
        color = col.hex_rgb(self.s_bow_color)
        loops = [self.C(geom.ellipse(s * 0.075, 0.33, 0.075, 0.042, 24, rot=s * 0.25), 0.28) for s in (-1, 1)]
        tails = [self.C(np.array([(s * 0.02, 0.35), (s * 0.06, 0.36), (s * 0.10, 0.62), (s * 0.06, 0.64)]), 0.28)
                 for s in (-1, 1)]
        knot = self.C(geom.ellipse(0.0, 0.335, 0.028, 0.03, 16), 0.29)
        shade = ShadeSpec(inflate=0.02 * self.H, threshold=0.12, spec=0.4)
        return [Layer("bow_tails", Material.CLOTH, color, polys=tails, line=self.line, shade=shade, tags=("garment",)),
                Layer("bow_loops", Material.CLOTH, color, polys=loops, line=self.line, shade=shade, tags=("garment",)),
                Layer("bow_knot", Material.CLOTH, color, polys=[knot], line=self.line, shade=shade, tags=("garment",))]
