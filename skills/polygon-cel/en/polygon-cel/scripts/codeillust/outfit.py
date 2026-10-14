"""Outfits: tops (knit sweater, shirt, off-shoulder dress, hoodie, tank top,
swimwear), bottoms (skirt, jeans, shorts, briefs) and shoes.

Garments are offsets of the body mannequin with openings cut by helper
masks (opacity 0 layers). Seams, folds and ribbing are thin ink strokes;
they carry the fabric identity more than the silhouette does.

build() returns layer groups because garments interleave with the body in
depth: sleeves of arms held behind the back sit behind the torso, skirts sit
over the legs but under an untucked top, a hoodie pocket covers the hands.
"""
import numpy as np

from . import color as col
from . import config as cfg
from . import backview, geom
from .body import RAISED_FOOT_SCALE, SHOULDER, front_z, mirror
from .scene import Blend, Layer, LineSpec, Material, ShadeSpec
from .wardrobe import BOW_COLOR, TIE_COLOR, WAIST, WardrobeMixin

DEFAULT_COLORS = {
    "knit_sweater": "#E9DFCF",
    "shirt": "#F5F5F1",
    "offshoulder_dress": "#7F9DC6",
    "hoodie": "#A9B1C1",
    "a_line_skirt": "#5A6480",
    "jeans": "#5F80AA",
    "sneakers": "#F2F2F0",
    "boots": "#5A4034",
    "crop_top": "#F4F1EC",
    "bikini": "#E57A6E",
    "one_piece": "#1E8C8A",
    "rash_guard": "#3E5F8A",
    "beach_shirt": "#F3EFE6",
    "tank_top": "#EDEBE5",
    "board_shorts": "#2F6F8F",
    "swim_briefs": "#24426A",
    "boxer_briefs": "#3F4552",
    "sports_bra": "#2E2F38", "camisole": "#E9D7DD", "slip_dress": "#8E2F3E", "halter_dress": "#1F1F26",
    "tee": "#F2F2EE", "oversized_tee": "#C9D3DE",
    "leggings": "#24252C", "joggers": "#5B6270", "slacks": "#3A3F4A", "pencil_skirt": "#2F3542",
    "dolphin_shorts": "#E8A0A8", "heels": "#2A2226", "dress_shoes": "#2E2420",
}
DEFAULT_BOTTOM = {"knit_sweater": "a_line_skirt", "shirt": "jeans", "hoodie": "jeans", "offshoulder_dress": None,
                  "crop_top": "jeans", "bikini": "bikini", "one_piece": None, "rash_guard": "bikini",
                  "beach_shirt": "bikini", "tank_top": "jeans", "sports_bra": "leggings", "camisole": "dolphin_shorts",
                  "slip_dress": None, "halter_dress": None, "tee": "jeans", "oversized_tee": None}
DEFAULT_BOTTOM_MALE = {"knit_sweater": "jeans", "shirt": "jeans", "hoodie": "jeans", "tank_top": "jeans",
                       "rash_guard": "board_shorts", "beach_shirt": "board_shorts", "shirtless": "board_shorts",
                       "tee": "jeans", "oversized_tee": "joggers"}
HOME_TOPS = ("camisole", "oversized_tee")          # worn barefoot at home
DRESSY = ("slip_dress", "halter_dress")            # heels by default
TUCK_BOTTOMS = ("slacks", "pencil_skirt")          # a shirt over these is tucked in
SWIM_TOPS = ("bikini", "one_piece", "rash_guard", "beach_shirt", "shirtless")
BAREFOOT_BOTTOMS = ("bikini", "board_shorts", "swim_briefs", "boxer_briefs")
NECK_REF = 0.176        # neck-base half-width the necklines are authored for (female body)
NECK_BASE_BLEND = (-0.05, 0.15)   # body-local y band where opening depth blends from the neck to the chest
PEC_FORM = 0.45         # cloth over pectorals shades far less than over a bust
RASH_GUARD_HEM = {"female": 1.78, "male": 2.15}   # body-local hem height: cropped over a bikini, hip length on males
RAISED_CAP = 0.55       # shoulder cap radius of a short sleeve on a horizontal or raised arm (share of hanging)
MALE_SLEEVE_EASE = 0.5  # muscular arms fill the sleeve; full ease would balloon it
BUST_REF_RY = 0.262     # medium bust radius; cloth shading strength scales from it
CUP_ARC = (172.0, 38.0) # triangle cup bottom: degrees along the breast outline; the outer side stays bare
CUP_MIN_X = 0.03        # cups stop short of the sternum
CUP_APEX = 1.35         # cup apex height above the bust center (bust radius units)
CUP_BULGE = (0.02, 0.07)   # sideways bulge of the inner and outer cup edges (H units), they wrap the breast
# swim brief outline, image-right half (body-local): low straight waist, smooth front, no emphasis
SWIM_BRIEF = [(0.0, 1.98), (0.30, 1.97), (0.50, 1.955), (0.60, 1.96), (0.60, 2.07), (0.45, 2.19),
              (0.29, 2.33), (0.14, 2.45), (0.0, 2.52)]
# shorts: (waist y, hem y, ease around the legs, shading bevel, inseam gap at the hem), body-local H units
SHORTS = {"board_shorts": (1.95, 3.02, 0.060, 0.12, 0.05), "boxer_briefs": (1.90, 2.74, 0.010, 0.08, 0.02)}
CROTCH_Y = 2.56         # inseam wedge apex, just below the torso's crotch point
BOXER_BAND = 0.10       # elastic waistband depth
BOXER_BAND_COLOR = "#E6E3DC"
# seen from behind: front-only details are dropped, necklines run higher, some garments open up
FRONT_ONLY = ("shirt_placket", "shirt_buttons", "shirt_collar_-1", "shirt_collar_1", "tie_", "bow_",
              "hoodie_cords", "hoodie_aglets", "hoodie_eyelets", "hoodie_pocket", "hood_lining", "rg_zip",
              "rg_pull", "bs_plackets", "bs_buttons", "bs_collar_", "board_cords", "joggers_cords", "buckle",
              "slip_cowl", "swim_cup_", "swim_strings", "swim_top_shadow", "swim_knot", "swim_gathers", "jeans_seams")
BACK_NECK = 0.40          # a back neckline is this share of the front depth
BACK_STRAP_Y = 0.82       # bikini back strap height
BACK_SCOOP = 1.30         # a one-piece swimsuit's low back reaches this height
# bikini bottoms seen from behind, image-right half from the top center around to the crotch
SWIM_BOTTOMS_BACK = {
    "classic":  [(0.0, 1.99), (0.30, 1.975), (0.52, 1.95), (0.62, 1.94), (0.62, 2.10), (0.52, 2.28),
                 (0.38, 2.44), (0.20, 2.54), (0.0, 2.56)],
    "high_leg": [(0.0, 1.99), (0.28, 1.965), (0.48, 1.91), (0.62, 1.88), (0.60, 1.95), (0.42, 2.12),
                 (0.26, 2.32), (0.12, 2.48), (0.0, 2.54)],
    "string":   [(0.0, 2.03), (0.20, 2.00), (0.215, 2.035), (0.07, 2.16), (0.03, 2.30), (0.0, 2.36)],
}
CROP_HEM = 1.12
LONG_HEM_START = 2.40   # hems below this drape from the hips instead of following the torso outline
JEANS_RISE = 1.86      # waistband height (body-local); low enough to show the navel under a crop top
# bikini bottom outlines, image-right half (body-local), from the center top around to the crotch
SWIM_BOTTOMS = {
    "classic":  [(0.0, 2.00), (0.28, 1.975), (0.50, 1.94), (0.62, 1.93), (0.62, 2.08), (0.44, 2.20),
                 (0.26, 2.35), (0.11, 2.47), (0.0, 2.52)],
    "high_leg": [(0.0, 2.00), (0.28, 1.96), (0.48, 1.90), (0.62, 1.87), (0.62, 1.93), (0.42, 2.10),
                 (0.24, 2.30), (0.10, 2.46), (0.0, 2.52)],
    "string":   [(0.0, 2.03), (0.20, 2.00), (0.215, 2.035), (0.15, 2.22), (0.075, 2.42), (0.0, 2.52)],
}
TOP_HEM = {"knit_sweater": 2.20, "shirt": 2.30, "hoodie": 2.22, "tank_top": 2.24}
SKIRT_HEM = 3.72


class OutfitBuilder(WardrobeMixin):
    def __init__(self, rig, spec, body):
        o = spec.get("outfit", {})
        self.kind = o.get("type", "knit_sweater")
        self.variant = o.get("variant")
        self.color = col.hex_rgb(o.get("color", DEFAULT_COLORS.get(self.kind, "#DDDDDD")))
        self.male = body.gender == "male"
        self.bottom_kind = o.get("bottom", (DEFAULT_BOTTOM_MALE if self.male else DEFAULT_BOTTOM).get(self.kind))
        if self.bottom_kind == "bikini":
            bottom_default = o.get("bikini_color", o.get("color", DEFAULT_COLORS["bikini"])) \
                if self.kind == "bikini" else o.get("bikini_color", "#2F4F7A")
        else:
            bottom_default = DEFAULT_COLORS.get(self.bottom_kind or "", "#555566")
        self.bottom_color = col.hex_rgb(o.get("bottom_color", bottom_default))
        self.bottom_style = o.get("bottom_style", "classic")
        self.s_bikini_color = o.get("bikini_color", "#2F4F7A")
        self.s_print_color = o.get("print_color", "#E38A5C")
        swim = self.kind in SWIM_TOPS or self.bottom_kind in BAREFOOT_BOTTOMS or self.kind in HOME_TOPS
        if swim:
            shoe_default = "barefoot"
        elif self.kind in DRESSY or self.bottom_kind == "pencil_skirt":
            shoe_default = "heels"
        elif self.bottom_kind == "slacks":
            shoe_default = "dress_shoes"
        else:
            shoe_default = "sneakers"
        self.shoe_kind = o.get("shoes", shoe_default)
        self.s_tie_color = o.get("tie_color", TIE_COLOR)
        self.s_bow_color = o.get("bow_color", BOW_COLOR)
        # a shirt tucked into slacks or a pencil skirt ends at their waistband
        self.tuck_y = WAIST[self.bottom_kind] + 0.02 if self.bottom_kind in TUCK_BOTTOMS else None
        self.shoe_color = col.hex_rgb(o.get("shoe_color", DEFAULT_COLORS.get(self.shoe_kind, "#EEEEEE")))
        self.rig = rig
        self.body = body
        self.H = rig.H
        self.line = LineSpec(cfg.LINE_BODY * self.H)
        # a seated figure's skirts and dresses end on the thighs, just past the knees
        knees = [body.leg_joints(s)[1][1] for s in (-1, 1)]
        self.hem_cap = max(knees) + 0.10 if body.stance.get("knee_caps") else None
        # necklines and armholes are authored for the female frame; a thicker neck
        # and wider shoulders scale and shift them (identity for the female body)
        self.neck_scale = body.neck_w[1] / NECK_REF
        self.shoulder_dx = body.shoulder[0] - SHOULDER[0]
        # the bust sits in front of the arms: sleeves give way to it, the garment body wraps it
        self.bust_cut = ("bust_front_mask",) if body.bust_in_front else ()
        self.back = body.back

    # ------------------------------------------------------------ helpers
    def nx(self, P):
        """Neckline points scaled to this body's neck width."""
        P = np.array(P, dtype=np.float64)
        P[:, 0] *= self.neck_scale
        return P

    def C(self, P, z=None):
        P = geom.pts(P)
        zz = front_z(P[:, 0]) if z is None else z
        return self.rig.body(np.column_stack([P, np.broadcast_to(zz, (len(P),))]))

    def S(self, P):
        """Canvas points on the garment surface: neck silhouette depth above the neck base,
        chest surface depth below it (openings stay aligned with the body when it turns)."""
        P = geom.pts(P)
        return self.C(P, front_z(P[:, 0]) * geom.smoothstep(NECK_BASE_BLEND[0], NECK_BASE_BLEND[1], P[:, 1]))

    def ink_of(self, color):
        return col.shadow_of(color, 0.42, "#303A70", 0.04, 0.25)

    def cloth(self, name, polys, cut=(), clip=(), inflate=0.10, cast=("head", "hair_front"), color=None,
              tags=("garment",), line=True, spec=0.0, spec_edge=0.93):
        return Layer(name, Material.CLOTH, self.color if color is None else color, polys=polys,
                     line=self.line if line else None, cut=cut, clip=clip,
                     shade=ShadeSpec(inflate=inflate * self.H, cast_tags=cast, cast_dist=0.06 * self.H,
                                     threshold=0.12, rim=0.8, spec=spec, spec_edge=spec_edge),
                     tags=tags)

    def ink(self, name, strokes, opacity=0.6, color=None, width=0.0045, clip=()):
        if isinstance(color, str):
            color = col.hex_rgb(color)
        out = []
        for spine, w in strokes:
            sp = geom.catmull_rom(np.asarray(spine, dtype=np.float64), 10)
            ww = geom.tapered_widths(len(sp), width * self.H * w, 0.3, 0.4)
            out.append((self.C(sp), ww))
        return Layer(name, Material.INK, self.ink_of(self.color if color is None else color), strokes=out,
                     opacity=opacity, clip=clip, tags=("garment_detail",))

    def helper(self, name, polys):
        return Layer(name, Material.FLAT, self.color, polys=polys, opacity=0.0)

    def torso(self, expand, bottom=None, hem_curve=0.03):
        if bottom is not None and bottom > LONG_HEM_START:
            # a hem below the crotch hangs straight from the hips (tunic, oversized tee)
            hip = max(x for x, y in self.body.torso_r if 1.8 < y < 2.4) + expand
            xs = np.linspace(hip * 1.04, -hip * 1.04, 24)
            hem = np.column_stack([xs, bottom + hem_curve * (1 - (xs / (hip * 1.04)) ** 2)])
            drape = self.body.pelvis(np.vstack([[(-hip, 1.95), (hip, 1.95)], hem]))
            polys = [self.body.to_canvas(self.body.torso_local(expand)), self.body.to_canvas(drape)]
        else:
            polys = [self.body.to_canvas(self.body.torso_local(expand, bottom=bottom, hem_curve=hem_curve))]
        if self.body.has_bust:
            polys += self.body.bust_polys(expand)
        return polys

    def arm_polys(self, side, parts, expand, extend=0.0):
        polys = []
        for part in parts:
            ps = self.body.arm_local(side, part, expand)
            if part == "lower" and extend:
                _, e, w = self.body.joints(side)
                d = (w - e) / np.linalg.norm(w - e)
                tip = w + d * extend
                ps.append(geom.ellipse(*tip, 0.075 + expand, 0.075 + expand, 24))
                ps.append(geom.stroke_outline(np.array([w, tip]), 0.14 + 2 * expand))
            polys += [self.body.to_canvas(p) for p in ps]
        return polys

    def sleeve_layers(self, g, prefix, expand, inflate=0.09, extend=0.0, color=None, clip=(), tags=("garment",)):
        """Add sleeves to the groups their forearm placement belongs to."""
        tags = tags + ("sleeve",)
        expand *= MALE_SLEEVE_EASE if self.male else 1.0
        for side in (-1, 1):
            place = self.body.arms[side]["forearm"]
            if place == "front":
                # one piece down to the wrist: it must stay above the forearm skin (tag read by build_layers)
                g["top"].append(self.cloth(f"{prefix}_{side}", self.arm_polys(side, ("upper", "lower"), expand, extend),
                                           inflate=inflate, color=color, clip=clip, cut=self.bust_cut,
                                           tags=tags + ("full_sleeve",)))
                continue
            g["top"].append(self.cloth(f"{prefix}_{side}", self.arm_polys(side, ("upper",), expand),
                                       inflate=inflate, color=color, clip=clip, cut=self.bust_cut, tags=tags))
            group = {"behind": "back", "raised": "raised", "behind_head": "behind_head"}[place]
            g[group].append(self.cloth(f"{prefix}_low_{side}", self.arm_polys(side, ("lower",), expand, extend),
                                       inflate=inflate * 0.8, color=color, clip=clip, tags=tags + (place,)))

    def neck_hole(self, name, depth, half=0.19, top=-2.0):
        half *= self.neck_scale
        if self.back:
            depth *= BACK_NECK
        R = [(half, -0.02), (half * 0.80, depth * 0.55), (half * 0.35, depth * 0.95), (0.0, depth)]
        P = np.vstack([[(-half * 1.3, top), (half * 1.3, top)], R, mirror(R[::-1])[1:]])
        return self.helper(name, [self.S(geom.catmull_rom(P, 8, closed=True))])

    def arm_folds(self):
        strokes = []
        for side in (-1, 1):
            sx = side * 1.0
            strokes += [([(sx * 0.58, 0.55), (sx * 0.50, 0.66), (sx * 0.40, 0.72)], 0.9),
                        ([(sx * 0.57, 0.80), (sx * 0.49, 0.86)], 0.7),
                        ([(sx * 0.70, 0.95), (sx * 0.73, 1.10)], 0.7)]
        return strokes

    def hem_band(self, name, y0, y1, expand, ribs=True):
        band = self.body.torso_local(expand + 0.005, bottom=y1)
        band = band[band[:, 1] >= y0 - 0.02]
        top = np.array([[band[:, 0].min(), y0], [band[:, 0].max(), y0]])
        P = np.vstack([band, top])
        layers = [self.cloth(name, [self.C(geom.pts(P), 0.2)], cut=("arms_mask",), inflate=0.03)]
        if ribs:
            xs = np.linspace(band[:, 0].min() * 0.95, band[:, 0].max() * 0.95, 30)
            layers.append(self.ink(f"{name}_ribs", [([(x, y0 + 0.01), (x, y1 + 0.02)], 0.7) for x in xs],
                                   opacity=0.25, width=0.0035))
        return layers

    # ------------------------------------------------------------ dispatch
    def build(self):
        fn = getattr(self, f"_{self.kind}", None)
        if fn is None:
            raise ValueError(f"unknown outfit type: {self.kind}")
        groups = {"back": [], "bottom": [], "shoes": [], "top": [], "over_hands": [], "raised": [], "behind_head": []}
        info = fn(groups)
        if self.bottom_kind == "bikini":
            groups["bottom"] += self._bikini_bottom_layers()
        elif self.bottom_kind:
            getattr(self, f"_{self.bottom_kind}")(groups)
        self._shoes(groups)
        if self.back:
            self.back_view(groups)
        return groups, info

    def back_view(self, g):
        """Drop front-only details and add what a back adds: glute form on bottoms and dresses."""
        for k in g:
            g[k] = [L for L in g[k] if "front_only" not in L.tags and not L.name.startswith(FRONT_ONLY)]
        if self.bottom_kind:
            g["bottom"] += backview.glute_form(self, ("pants", "skirt"), self.bottom_color)
        if self.kind in ("slip_dress", "halter_dress", "one_piece"):
            g["top"] += backview.glute_form(self, (self.kind,), self.color)

    # ------------------------------------------------------------ tops
    def _knit_sweater(self, g):
        turtle = (self.variant or "turtleneck") == "turtleneck"
        hem = TOP_HEM["knit_sweater"]
        g["top"] += [self.neck_hole("knit_hole", 0.10 if turtle else 0.14, 0.19),
                     self.cloth("knit_body", self.torso(0.045, hem, 0.0), cut=("knit_hole", "arms_mask"), inflate=0.14)]
        g["top"] += self.hem_band("knit_hem", hem - 0.13, hem, 0.045)
        ribs = [([(x, 0.12 + 0.02 * (x / 0.5) ** 2), (x * 1.01, 0.70), (x * 0.98, hem - 0.15)], 0.55)
                for x in np.linspace(-0.52, 0.52, 23)]
        g["top"].append(self.ink("knit_ribs", ribs, opacity=0.18, width=0.0035))
        g["top"] += self.bust_form("knit", self.color, ("knit_body",), folds=False)
        self.sleeve_layers(g, "knit_sleeve", 0.055, extend=0.05)
        g["top"].append(self.ink("knit_folds", self.arm_folds(), opacity=0.45))
        if turtle:
            tube = [(0.232, 0.08), (0.238, -0.04), (0.228, -0.14), (0.214, -0.215), (0.12, -0.235), (0.0, -0.24)]
            P = np.vstack([tube, mirror(tube[::-1])[1:], [(-0.232, 0.08), (-0.10, 0.12), (0.10, 0.12)]])
            P = geom.catmull_rom(self.nx(P), 8, closed=True)
            g["top"].append(self.cloth("knit_collar", [self.C(P, 0.28)], inflate=0.07,
                                       tags=("garment", "garment_top")))
            fold = self.nx([(-0.225, -0.10), (-0.10, -0.075), (0.10, -0.075), (0.225, -0.10)])
            cribs = [([(x * self.neck_scale, -0.215 + 0.03 * (x / 0.22) ** 2), (x * 1.04 * self.neck_scale, 0.09)], 0.8)
                     for x in np.linspace(-0.19, 0.19, 12)]
            g["top"] += [self.ink("collar_ribs", cribs, opacity=0.30, width=0.0035),
                         self.ink("collar_fold", [(fold, 1.2)], opacity=0.6)]
        else:
            band = [(0.19, -0.02), (0.16, 0.06), (0.08, 0.13), (0.0, 0.14)]
            outer = [(0.25, -0.01), (0.21, 0.11), (0.10, 0.19), (0.0, 0.20)]
            P = np.vstack([band, mirror(band[::-1])[1:], mirror(outer), outer[::-1]])
            g["top"].append(self.cloth("knit_band", [self.C(geom.catmull_rom(self.nx(P), 6, closed=True), 0.26)],
                                       inflate=0.04))
        return {"clavicles": False}

    def _shirt(self, g):
        hem = self.tuck_y or TOP_HEM["shirt"]
        accessory = self.variant if self.variant in ("tie", "bow") else None
        depth = 0.30 if accessory else 0.34          # a tie or bow closes the collar to the top button
        if self.back:
            depth = 0.06
        g["top"] += [self.helper("shirt_hole", [self.S(self.nx([(-0.26, -2), (0.26, -2), (0.17, -0.03), (0.02, depth),
                                                                (-0.02, depth), (-0.17, -0.03)]))]),
                     self.cloth("shirt_body", self.torso(0.030, hem, 0.08), cut=("shirt_hole", "arms_mask"),
                                inflate=0.14)]
        g["top"] += self.bust_form("shirt", self.color, ("shirt_body",), strength=0.8)
        self.sleeve_layers(g, "shirt_sleeve", 0.045)
        back = [(0.235, 0.06), (0.225, -0.10), (0.12, -0.15), (0.0, -0.16)]
        P = self.nx(np.vstack([back, mirror(back[::-1])[1:], [(-0.17, 0.05), (0.17, 0.05)]]))
        inner = col.shadow_of(self.color, 0.18, "#4050A0", 0.04, 0.12)
        g["top"].append(self.cloth("shirt_collar_back", [self.C(geom.catmull_rom(P, 6, closed=True), -0.05)],
                                   cut=() if self.back else ("neck_mask",), inflate=0.03,
                                   color=self.color if self.back else inner))
        if accessory == "tie":
            g["top"] += self.necktie()
        flap = self.nx([(0.018, 0.345), (0.160, -0.045), (0.215, -0.025), (0.345, 0.125), (0.305, 0.245), (0.150, 0.205)])
        for side in (-1, 1):
            F = flap.copy()
            F[:, 0] *= side
            F = geom.catmull_rom(F, 3, closed=True, alpha=0.9)
            g["top"].append(self.cloth(f"shirt_collar_{side}", [self.C(F, 0.28)], inflate=0.04,
                                       tags=("garment", "garment_top")))
        g["top"].append(self.ink("shirt_placket", [([(0.0, 0.35), (0.0, 1.2), (0.0, hem)], 1.0),
                                                   ([(0.06, 0.36), (0.06, hem + 0.05)], 0.7)], opacity=0.5))
        buttons = [self.C(geom.ellipse(0.03, y, 0.018, 0.018, 24)) for y in (0.52, 0.86, 1.20, 1.54, 1.88)
                   if y < hem - 0.05]
        g["top"].append(Layer("shirt_buttons", Material.FLAT, col.hex_rgb("#FFFFFF"), polys=buttons,
                              line=LineSpec(0.0035 * self.H)))
        g["top"].append(self.ink("shirt_folds", self.arm_folds() + [([(-0.30, 0.95), (-0.24, 1.15)], 0.7),
                                                                     ([(0.26, 1.00), (0.20, 1.22)], 0.7)], opacity=0.5))
        if accessory == "bow":
            g["top"] += self.neck_bow()
        return {"clavicles": accessory is None}

    def _offshoulder_dress(self, g):
        neck = [(0.0, 0.585), (0.30, 0.50), (0.58, 0.47), (0.86, 0.56), (1.20, 0.66)]
        Nfull = np.vstack([mirror(neck[::-1]), neck[1:]])
        below = geom.catmull_rom(np.vstack([Nfull, [(1.4, 6.0), (-1.4, 6.0)]]), 8, closed=True)
        g["top"] += [self.helper("dress_below", [self.C(below, 0.2)]),
                     self.cloth("dress_body", self.torso(0.030, 1.55, 0.0), clip=("dress_below",),
                                cut=("arms_mask",), inflate=0.14, tags=("garment", "dress_part"))]
        skirt = [(0.455, 1.40), (0.56, 1.78), (0.72, 2.25), (0.90, 2.95), (1.02, SKIRT_HEM)]
        g["top"] += self.bust_form("dress", self.color, ("dress_body",), strength=0.8)
        g["top"].append(self._skirt_layer("dress_skirt", skirt, self.color, gathers=True))
        for side in (-1, 1):
            polys = [self.body.to_canvas(p) for p in self.body.arm_local(side, "upper", 0.095)]
            g["top"].append(self.cloth(f"dress_sleeve_{side}", polys, clip=("dress_below",), cut=self.bust_cut,
                                       inflate=0.10, tags=("garment", "dress_part", "sleeve")))
        top = geom.catmull_rom(Nfull, 10)
        top = top[np.abs(top[:, 0]) < 1.02]
        wave = 0.075 + 0.018 * np.cos(np.linspace(0, 26 * np.pi, len(top)))
        band = np.vstack([top - [0, 0.012], (top + np.column_stack([np.zeros(len(top)), wave]))[::-1]])
        g["top"].append(self.cloth("dress_ruffle", [self.C(band, 0.30)], inflate=0.03, clip=("dress_part",),
                                   color=col.light_of(self.color, 0.12), tags=("garment", "garment_top")))
        gathers = [([(p[0], p[1] + 0.02), (p[0] * 1.005, p[1] + 0.07)], 0.6) for p in top[::6]]
        g["top"].append(self.ink("dress_gathers", gathers, opacity=0.40, width=0.0035))
        g["top"].append(self.ink("dress_folds", [([(-0.25, 0.75), (-0.22, 1.10), (-0.24, 1.45)], 0.8),
                                                 ([(0.20, 0.78), (0.18, 1.15)], 0.7)], opacity=0.40))
        return {"clavicles": True}

    def _hoodie(self, g):
        hem = TOP_HEM["hoodie"]
        g["top"] += [self.neck_hole("hood_hole", 0.12, 0.20),
                     self.cloth("hoodie_body", self.torso(0.070, hem, 0.0), cut=("hood_hole", "arms_mask"),
                                inflate=0.15)]
        g["top"] += self.hem_band("hoodie_hem", hem - 0.12, hem, 0.07)
        g["top"] += self.bust_form("hoodie", self.color, ("hoodie_body",), folds=False, strength=0.5)
        self.sleeve_layers(g, "hoodie_sleeve", 0.075)
        if self.back:
            drape = self.nx([(0.0, -0.10), (0.30, -0.08), (0.44, 0.10), (0.40, 0.45), (0.22, 0.72), (0.0, 0.80),
                             (-0.22, 0.72), (-0.40, 0.45), (-0.44, 0.10), (-0.30, -0.08)])
            g["top"] += [self.cloth("hood_back", [self.C(geom.catmull_rom(drape, 6, closed=True), 0.3)], inflate=0.08,
                                    tags=("garment", "garment_top")),
                         self.ink("hood_back_fold", [([(-0.22, 0.10), (0.0, 0.42), (0.22, 0.10)], 1.0)], opacity=0.5,
                                  clip=("hood_back",))]
            return {"clavicles": False}
        outer = [(0.0, -0.215), (0.24, -0.175), (0.40, -0.05), (0.50, 0.12), (0.54, 0.27)]
        fr = [(0.46, 0.31), (0.30, 0.235), (0.14, 0.19), (0.0, 0.175)]
        R = np.vstack([outer, fr])
        hood = geom.catmull_rom(self.nx(np.vstack([R, mirror(R[::-1])[1:-1]])), 8, closed=True)
        dark = col.shadow_of(self.color, 0.22, "#3040A0", 0.04, 0.15)
        g["top"].append(self.cloth("hood", [self.C(hood, 0.15)], cut=("neck_mask",), inflate=0.08,
                                   tags=("garment", "garment_top")))
        lining = [(0.0, 0.14), (0.10, 0.105), (0.18, 0.03), (0.215, -0.05)]
        L2 = np.vstack([mirror(lining[::-1]), lining[1:], [(0.25, -0.02), (0.20, 0.08), (0.10, 0.155), (0.0, 0.19),
                                                           (-0.10, 0.155), (-0.20, 0.08), (-0.25, -0.02)]])
        g["top"].append(self.cloth("hood_lining", [self.C(geom.catmull_rom(self.nx(L2), 6, closed=True), 0.3)],
                                   cut=("neck_mask",), inflate=0.02, color=dark, line=False))
        strokes, tips = [], []
        for side in (-1, 1):
            spine = np.array([(side * 0.075, 0.16), (side * 0.085, 0.40), (side * 0.070, 0.62), (side * 0.090, 0.86)])
            sp = geom.catmull_rom(spine, 10)
            strokes.append((self.C(sp), np.full(len(sp), 0.020 * self.H)))
            tips.append(self.C(geom.stroke_outline(np.array([sp[-1], sp[-1] + [0.0, 0.07]]), 0.036)))
        g["top"].append(Layer("hoodie_cords", Material.INK, col.light_of(self.color, 0.35), strokes=strokes,
                              tags=("garment_detail",)))
        g["top"].append(Layer("hoodie_aglets", Material.FLAT, col.hex_rgb("#D8D8DC"), polys=tips,
                              line=LineSpec(0.0035 * self.H)))
        eyelets = [self.C(geom.ellipse(s * 0.075, 0.165, 0.016, 0.014, 20)) for s in (-1, 1)]
        g["top"].append(Layer("hoodie_eyelets", Material.FLAT, col.hex_rgb("#C8C8CC"), polys=eyelets,
                              line=LineSpec(0.003 * self.H)))
        g["top"].append(self.ink("hoodie_folds", self.arm_folds() + [([(-0.34, 0.9), (-0.30, 1.2)], 0.8),
                                                                      ([(0.33, 0.95), (0.28, 1.25)], 0.8)], opacity=0.5))
        pocket = np.array([(-0.32, 1.72), (0.32, 1.72), (0.47, 1.99), (0.47, 2.10), (-0.47, 2.10), (-0.47, 1.99)])
        g["over_hands"].append(self.cloth("hoodie_pocket", [self.C(geom.resample(pocket, 0.01, closed=True))],
                                          inflate=0.05))
        return {"clavicles": False}

    # ------------------------------------------------------------ bottoms
    def hem(self, y):
        return min(y, self.hem_cap) if self.hem_cap else y

    def _skirt_layer(self, name, right_side, color, gathers=False):
        R = np.array(right_side, dtype=np.float64)
        R[:, 1] = np.minimum(R[:, 1], self.hem(R[-1, 1]))
        hem_x = np.linspace(R[-1, 0], -R[-1, 0], 60)
        hem = np.column_stack([hem_x, R[-1, 1] + 0.035 * np.sin(np.linspace(0, 7 * np.pi, 60)) ** 2])
        top = np.array([(-R[0, 0], R[0, 1]), (0.0, R[0, 1] + 0.02)])
        P = np.vstack([top, geom.catmull_rom(R, 10)[:-1], hem, geom.catmull_rom(mirror(R[::-1]), 10)[1:]])
        P = self.body.pelvis(P)
        return Layer(name, Material.CLOTH, color, polys=[self.C(P, 0.2)], line=self.line, cut=("arms_mask",),
                     shade=ShadeSpec(inflate=0.14 * self.H, cast_tags=("garment_top", "hand"), cast_dist=0.05 * self.H,
                                     threshold=0.12, rim=0.8),
                     tags=("garment", "skirt"))

    def _a_line_skirt(self, g):
        right = [(0.445, 1.45), (0.54, 1.80), (0.66, 2.20), (0.80, 2.90), (0.90, SKIRT_HEM)]
        g["bottom"].append(self._skirt_layer("skirt", right, self.bottom_color))
        g["bottom"].append(self.ink("skirt_folds", [([(x * 0.55, 2.0), (x * 0.9, 2.9), (x, SKIRT_HEM)], 0.9)
                                                    for x in (-0.70, -0.30, 0.10, 0.45, 0.80)],
                                    color=self.bottom_color, opacity=0.45))

    def waist_edge(self, waist_y):
        """Waistline (body-local) dipping gently toward the center front."""
        xs = np.linspace(-1.5, 1.5, 31)
        return np.column_stack([xs, waist_y + 0.035 * (1 - np.clip(np.abs(xs) / 0.6, 0, 1) ** 2)])

    def pants_layers(self, name, waist_y, hem_y, ease, inflate, gap=0.0, extra_cut=()):
        """Torso and leg ribbons clipped between the waistline and a hem: one garment silhouette.

        gap opens an inseam wedge between the legs; loose shorts would otherwise
        fuse into one block that reads as a skirt.
        """
        edge = self.waist_edge(waist_y)
        band = self.body.pelvis(np.vstack([edge, [(1.5, hem_y), (-1.5, hem_y)]]))
        polys = [self.C(self.body.torso_local(ease * 0.7), 0.2)]
        for side in (-1, 1):
            for part in ("thigh", "calf"):
                polys += [self.body.to_canvas(p) for p in self.body.leg_local(side, part, ease)]
        layers = [self.helper(f"{name}_waist", [self.C(band, 0.2)])]
        cut = ("arms_mask",) + tuple(extra_cut)
        if gap:
            wedge = np.array([(0.0, CROTCH_Y), (gap, hem_y + 0.2), (-gap, hem_y + 0.2)])
            layers.append(self.helper(f"{name}_gap", [self.C(self.body.pelvis(wedge), 0.2)]))
            cut += (f"{name}_gap",)
        return layers + [
                Layer(name, Material.CLOTH, self.bottom_color, polys=polys, line=self.line,
                      clip=(f"{name}_waist",), cut=cut,
                      shade=ShadeSpec(inflate=inflate * self.H, cast_tags=("garment_top", "hand"),
                                      cast_dist=0.05 * self.H, threshold=0.12, rim=0.8),
                      tags=("garment", "pants"))]

    def _jeans(self, g):
        # low-rise waist: low enough to show the navel under a crop top
        g["bottom"] += self.pants_layers("jeans", JEANS_RISE, 7.0, 0.035, 0.10)
        xs, top = self.waist_edge(JEANS_RISE).T
        band = self.body.pelvis(np.column_stack([xs, top + 0.075]))
        seams = [(band[np.abs(band[:, 0]) < 0.62], 0.9), ([(0.0, JEANS_RISE + 0.11), (0.02, 2.25), (0.0, 2.45)], 1.0),
                 ([(-0.48, JEANS_RISE + 0.10), (-0.32, 2.12), (-0.24, JEANS_RISE + 0.10)], 0.9),
                 ([(0.48, JEANS_RISE + 0.10), (0.32, 2.12), (0.24, JEANS_RISE + 0.10)], 0.9)]
        for side in (-1, 1):
            hip, knee, ankle = self.body.leg_joints(side)
            out = np.array([side * 0.20, 0.0])
            seams.append(([hip + out * 1.2, knee + out * 0.75, ankle + out * 0.5], 0.8))
        g["bottom"].append(self.ink("jeans_seams", seams, color=self.bottom_color, opacity=0.5))
        if self.back:
            pockets = []
            for side in (-1, 1):
                P = np.array([(0.12, 2.06), (0.38, 2.04), (0.37, 2.26), (0.25, 2.32), (0.13, 2.27)])
                P[:, 0] *= side
                pockets.append(self.C(self.body.pelvis(P), 0.2))
            g["bottom"] += [self.cloth("jeans_pockets", pockets, clip=("jeans",), inflate=0.02,
                                       color=self.bottom_color, tags=("garment", "pants")),
                            self.ink("jeans_yoke", [([(-0.56, 1.98), (0.0, 2.08), (0.56, 1.98)], 0.9)],
                                     color=self.bottom_color, opacity=0.5, clip=("jeans",))]

    def thigh_span(self, side, y):
        """(center, half width) of the thigh ribbon at height y (body-local)."""
        hip, knee, _ = self.body.leg_joints(side)
        t = (y - hip[1]) / (knee[1] - hip[1])
        w = np.interp(t, np.linspace(0, 1, len(self.body.widths["thigh"])), self.body.widths["thigh"])
        return hip + (knee - hip) * t, w / 2

    def thigh_outer(self, side, y, inset):
        c, half = self.thigh_span(side, y)
        return c + [side * (half - inset), 0.0]

    def thigh_hem(self, side, y, ease):
        """Hem line across one thigh, sagging slightly at the front."""
        c, half = self.thigh_span(side, y)
        half += ease + 0.02
        return [c + [side * half, 0.0], c + [0.0, 0.025], c - [side * half, 0.0]]

    def _board_shorts(self, g):
        waist, hem, ease, inflate, gap = SHORTS["board_shorts"]
        g["bottom"] += self.pants_layers("board_shorts", waist, hem, ease, inflate, gap)
        edge = self.body.pelvis(self.waist_edge(waist))
        band = self.body.pelvis(self.waist_edge(waist + 0.10))
        stripes, cords = [], []
        for side in (-1, 1):
            sp = geom.resample(np.array([self.body.pelvis([(side * 0.50, waist + 0.03)])[0],
                                         self.thigh_outer(side, hem + 0.05, 0.06)]), 0.02)
            stripes.append((self.C(sp), np.full(len(sp), 0.032 * self.H)))
            cp = geom.catmull_rom(np.array([(side * 0.03, waist + 0.08), (side * 0.055, waist + 0.21),
                                            (side * 0.035, waist + 0.34)]), 8)
            cords.append((self.C(cp), geom.tapered_widths(len(cp), 0.014 * self.H, 0.1, 0.2)))
        g["bottom"] += [
            self.ink("board_band", [(band[np.abs(band[:, 0]) < 0.62], 0.9)], color=self.bottom_color, opacity=0.5),
            Layer("board_stripes", Material.INK, col.light_of(self.bottom_color, 0.55), strokes=stripes,
                  clip=("board_shorts",), opacity=0.85),
            Layer("board_cords", Material.INK, col.hex_rgb("#F2EFE8"), strokes=cords, tags=("garment_detail",)),
            self.ink("board_folds", [([(-0.30, hem - 0.30), (-0.26, hem - 0.05)], 0.8),
                                     ([(0.34, hem - 0.28), (0.30, hem - 0.04)], 0.8),
                                     ([(0.0, edge[15, 1] + 0.12), (0.01, 2.40)], 0.9)],
                     color=self.bottom_color, opacity=0.45, clip=("board_shorts",)),
        ]

    def _boxer_briefs(self, g):
        waist, hem, ease, inflate, gap = SHORTS["boxer_briefs"]
        g["bottom"] += self.pants_layers("boxer_briefs", waist, hem, ease, inflate, gap)
        top = self.body.pelvis(self.waist_edge(waist - 0.01))
        low = self.body.pelvis(self.waist_edge(waist + BOXER_BAND))
        band = np.vstack([top, low[::-1]])
        seams = [(self.thigh_hem(side, hem - 0.06, ease), 0.8) for side in (-1, 1)]
        seams += [([self.body.pelvis([(side * 0.52, waist + 0.16)])[0], self.thigh_outer(side, hem - 0.08, 0.05)], 0.7)
                  for side in (-1, 1)]
        g["bottom"] += [
            Layer("boxer_band", Material.CLOTH, col.hex_rgb(BOXER_BAND_COLOR), polys=[self.C(band, 0.2)],
                  clip=("boxer_briefs",), line=LineSpec(cfg.LINE_DETAIL * self.H),
                  shade=ShadeSpec(inflate=0.04 * self.H, threshold=0.12, rim=0.6)),
            self.ink("boxer_seams", seams, color=self.bottom_color, opacity=0.45, clip=("boxer_briefs",)),
        ]

    def _swim_briefs(self, g):
        g["bottom"].append(self.brief_layer("swim_briefs", SWIM_BOTTOMS_BACK["classic"] if self.back else SWIM_BRIEF,
                                            self.bottom_color))
        edge = self.body.pelvis(np.array([(-0.58, 2.00), (0.0, 2.025), (0.58, 2.00)]))
        g["bottom"].append(self.ink("swim_briefs_band", [(edge, 0.8)], color=self.bottom_color, opacity=0.5))

    # ------------------------------------------------------------ revealing tops
    def short_sleeve(self, side, expand, length=0.42):
        """Upper-arm sleeve with a rounded shoulder and a straight hem (no puff)."""
        s0, e, _ = self.body.joints(side)
        end = s0 + (e - s0) * length
        spine = geom.resample(np.array([s0, end]), 0.01)
        t = np.linspace(0, 1, len(spine))
        uw = self.body.widths["upper"]
        w = np.interp(t, [0, 1], [uw[0], uw[2]]) + 2 * expand
        # the round shoulder cap belongs to a hanging arm; on a raised arm it hung below the armpit like an
        # empty sleeve (v10 showcase), so it shrinks as the upper arm rises toward horizontal and above
        hang = float(np.clip((e - s0)[1] / max(np.linalg.norm(e - s0), 1e-6), 0.0, 1.0))
        cap = w[0] / 2 * (RAISED_CAP + (1 - RAISED_CAP) * hang)
        shoulder = geom.ellipse(*s0, cap, cap, 32)
        return [self.body.to_canvas(p) for p in (geom.stroke_outline(spine, w), shoulder)]

    def bust_form(self, name, color, clip, folds=True, strength=1.0):
        """Fabric over the bust (or pectorals): the cloth takes the round form underneath.

        Layers, back to front: cloth with the sphere (dome) normals of each breast,
        so cel shading cuts a shadow crescent at the lower outer rim; the shade cast
        below the lower border; a soft sheen on the upper slope; the lower border
        inked through the cloth; stretch folds.
        """
        H = self.H
        cx, cy, rx, ry = self.body.bust
        if self.male:
            strength, folds = strength * PEC_FORM * self.body.muscle, False
        else:
            strength *= ry / BUST_REF_RY      # a fuller bust pushes more light and shadow into the cloth
        layers, shade, light, fold, contour = [], [], [], [], []
        for side in (-1, 1):
            layers.append(Layer(f"{name}_round_{side}", Material.CLOTH, color,
                                polys=[self.C(self.body.bust_shape(side, 0.01), self.body.bust_z())], clip=clip,
                                feather=0.012 * H, opacity=min(strength, 1.0),
                                shade=ShadeSpec(normal_map=self.body.bust_normals(side), threshold=0.12, rim=0.8)))
            crease = np.array(self.body.crease(side))
            sp = geom.catmull_rom(crease, 10)
            shade.append((self.C(sp + [0.0, 0.03]), geom.tapered_widths(len(sp), 0.045 * H, 0.35, 0.35)))
            contour.append((np.array(self.body.bust_contour(side)), 1.0))
            light.append(self.C(geom.ellipse(side * (cx - rx * 0.15), cy - ry * 0.40, rx * 0.60, ry * 0.50, 32)))
            fold.append(([(side * (cx + rx * 0.3), cy + ry * 1.25), (side * (cx + rx * 0.9), cy + ry * 1.45),
                          (side * (cx + rx * 1.35), cy + ry * 1.40)], 0.8))
            fold.append(([(side * (cx - rx * 0.6), cy + ry * 1.35), (side * (cx - rx * 0.2), cy + ry * 1.75)], 0.6))
        # the valley between the breasts: a soft vertical shade separates the two volumes
        if not self.male:
            valley = geom.catmull_rom(np.array([(0.0, cy - ry * 0.25), (0.0, cy + ry * 0.45), (0.0, cy + ry * 0.95)]), 8)
            shade.append((self.C(valley), geom.tapered_widths(len(valley), 0.045 * H * (ry / BUST_REF_RY), 0.5, 0.4)))
        layers += [Layer(f"{name}_bust", Material.FLAT, col.shadow_of(color, 0.16, "#4050A0", 0.04, 0.12), strokes=shade,
                         clip=clip, blend=Blend.MULTIPLY, feather=0.010 * H, opacity=0.50 * strength),
                   Layer(f"{name}_bust_light", Material.GLOW, col.light_of(color, 0.4), polys=light, clip=clip,
                         blend=Blend.SCREEN, feather=0.035 * H, opacity=0.18 * strength),
                   self.ink(f"{name}_contour", contour, color=color, opacity=min(0.70 * strength, 0.85), clip=clip,
                            width=0.0050)]
        if folds:
            layers.append(self.ink(f"{name}_folds", fold, color=color, opacity=0.40 * strength, clip=clip))
        for L in layers:
            L.tags = tuple(L.tags) + ("front_only",)
        return layers

    def _crop_top(self, g):
        tee = (self.variant or "tank") == "tee"
        if tee:
            g["top"].append(self.neck_hole("crop_neck", 0.13, 0.20))
            cut = ("crop_neck", "arms_mask")
        else:
            k = BACK_NECK if self.back else 1.0
            R = [(0.20, -0.02), (0.19, 0.12 * k), (0.13, 0.25 * k), (0.0, 0.29 * k)]
            P = np.vstack([[(-0.26, -2.0), (0.26, -2.0)], R, mirror(R[::-1])[1:]])
            g["top"].append(self.helper("crop_neck", [self.S(geom.catmull_rom(P, 8, closed=True))]))
            holes = []
            for side in (-1, 1):
                A = np.array([(0.34, -2.0), (2.0, -2.0), (2.0, 0.62), (0.64, 0.56), (0.52, 0.44), (0.40, 0.24), (0.35, 0.05)])
                A[:, 0] *= side
                holes.append(self.S(geom.catmull_rom(A, 6, closed=True)))
            g["top"].append(self.helper("crop_arm", holes))
            cut = ("crop_neck", "crop_arm", "arms_mask")
        body = self.torso(0.022, CROP_HEM, 0.02)
        g["top"].append(self.cloth("crop_body", body, cut=cut, inflate=0.15, tags=("garment", "crop")))
        g["top"] += self.bust_form("crop", self.color, ("crop_body",))
        g["top"].append(self.ink("crop_hem", [([(-0.56, CROP_HEM - 0.05), (0.0, CROP_HEM - 0.03), (0.56, CROP_HEM - 0.05)], 0.9)],
                                 opacity=0.35))
        if tee:
            for side in (-1, 1):
                g["top"].append(self.cloth(f"crop_sleeve_{side}", self.short_sleeve(side, 0.05), inflate=0.08,
                                           cut=self.bust_cut, tags=("garment", "sleeve")))
        return {"clavicles": True, "exposed": True}

    def _bikini(self, g):
        H = self.H
        if self.back:
            return self.bikini_back(g)
        bandeau = (self.variant or "triangle") == "bandeau"
        layers = []
        if bandeau:
            bx, by, brx, bry = self.body.bust
            t, b = by - bry * 0.95, by + bry * 1.05
            top_edge = [(-0.70, t + 0.04), (-bx, t), (0.0, t + 0.07), (bx, t), (0.70, t + 0.04)]
            bot_edge = [(0.70, b - 0.01), (bx, b + 0.01), (0.0, b - 0.03), (-bx, b + 0.01), (-0.70, b - 0.01)]
            band = geom.catmull_rom(np.vstack([top_edge, bot_edge]), 8, closed=True)
            layers.append(self.cloth("swim_top", [self.C(band)], clip=("torso_mask", "bust_mask"), cut=("upper_arm_mask",),
                                     inflate=0.14, tags=("garment", "swim_top")))
            knot = geom.ellipse(0.0, by + 0.02, 0.045, 0.07, 24)
            layers.append(self.cloth("swim_knot", [self.C(knot)], inflate=0.03, tags=("garment", "swim_top")))
            gathers = [([(0.0, by - 0.05), (s * 0.12, by - 0.09)], 0.7) for s in (-1, 1)] + \
                      [([(0.0, by + 0.09), (s * 0.14, by + 0.14)], 0.7) for s in (-1, 1)]
            layers.append(self.ink("swim_gathers", gathers, opacity=0.5))
            shadow_polys = [self.C(np.vstack([bot_edge, np.array(bot_edge)[::-1] + [0.0, 0.05]]))]
        else:
            cups, strings, shadow_polys = [], [], []
            bx, by, brx, bry = self.body.bust
            bz = self.body.bust_z()
            for side in (-1, 1):
                # the cup bottom follows the breast's lower border, so the cup reads as a ball;
                # its sides rise to an apex on the upper slope
                a = np.radians(np.linspace(CUP_ARC[0], CUP_ARC[1], 17))
                arc = np.column_stack([bx + brx * np.cos(a), by + bry * np.sin(a)])
                arc[:, 0] = np.maximum(arc[:, 0], CUP_MIN_X)
                apex = np.array([bx - brx * 0.10, by - bry * CUP_APEX])
                inner_mid = apex + (arc[0] - apex) * 0.5 + [-CUP_BULGE[0], 0.0]
                outer_mid = apex + (arc[-1] - apex) * 0.5 + [CUP_BULGE[1], 0.0]
                P = np.vstack([[apex, inner_mid], arc, [outer_mid]]) * [side, 1]
                cups.append((self.C(geom.catmull_rom(P, 6, closed=True), bz), None))
                below = arc * [side, 1]
                shadow_polys.append(self.C(np.vstack([below, below[::-1] + [0.0, 0.045]]), bz))
                # strings leave the cups at the bust depth and reach the neck and the back at the
                # body silhouette, so they stay attached when the body turns
                neck = geom.catmull_rom(np.array([apex + [-0.01, 0.01], (0.15, 0.17), (0.125, -0.03)]) * [side, 1], 8)
                strings.append((self.C(neck, np.linspace(bz, 0.0, len(neck))), 0.016))
                back = geom.resample(np.array([arc[-1] * [side, 1], (side * 0.75, 0.80)]), 0.02)
                strings.append((self.C(back, np.linspace(bz, 0.0, len(back))), 0.018))
            xi, yi = arc[1]
            strings.append((self.C(np.array([(-xi, yi), (xi, yi)]), bz), 0.018))
            string_layer_strokes = [(sp, np.full(len(sp), w * H)) for sp, w in strings]
            layers.append(Layer("swim_strings", Material.INK, col.shadow_of(self.color, 0.10), strokes=string_layer_strokes,
                                clip=("torso_mask", "neck_mask"), cut=("upper_arm_mask",), tags=("garment",)))
            for side, (poly, _) in zip((-1, 1), cups):
                layers.append(Layer(f"swim_cup_{side}", Material.CLOTH, self.color, polys=[poly], line=self.line,
                                    shade=ShadeSpec(normal_map=self.body.bust_normals(side),
                                                    threshold=0.10, rim=0.8, spec=0.25, spec_edge=0.90),
                                    tags=("garment", "swim_top")))
        g["top"].append(Layer("swim_top_shadow", Material.FLAT, col.shadow_of(self.body.skin, 0.25, "#B03040", 0.04, 0.2),
                              polys=shadow_polys, clip=("torso_mask",), cut=("upper_arm_mask",),
                              blend=Blend.MULTIPLY, feather=0.008 * H,
                              opacity=0.45))
        g["top"] += layers
        return {"clavicles": True, "exposed": True}

    def bikini_back(self, g):
        """Bikini top from behind: a strap across the back and the halter tied at the nape."""
        H = self.H
        bandeau = (self.variant or "triangle") == "bandeau"
        width = 0.10 if bandeau else 0.022
        y = BACK_STRAP_Y
        strap = self.C(np.array([(-0.75, y - width / 2), (0.75, y - width / 2), (0.75, y + width / 2),
                                 (-0.75, y + width / 2)]))
        layers = [Layer("swim_back_strap", Material.CLOTH, self.color, polys=[strap], line=self.line,
                        clip=("torso_mask", "bust_mask"), cut=("upper_arm_mask",),
                        shade=ShadeSpec(inflate=0.02 * H, threshold=0.12, rim=0.8), tags=("garment",))]
        if not bandeau:
            ties = [self.C(np.array([(s * 0.06, -0.05), (s * 0.16, 0.10), (s * 0.26, 0.24)])) for s in (-1, 1)]
            bow = [self.C(geom.ellipse(s * 0.04, -0.04, 0.04, 0.022, 16, rot=s * 0.4), 0.0) for s in (-1, 1)]
            layers += [Layer("swim_neck_ties", Material.INK, col.shadow_of(self.color, 0.10),
                             strokes=[(t, np.full(len(t), 0.016 * H)) for t in ties], clip=("torso_mask", "neck_mask")),
                       Layer("swim_neck_bow", Material.CLOTH, self.color, polys=bow, line=LineSpec(cfg.LINE_DETAIL * H),
                             shade=ShadeSpec(inflate=0.01 * H))]
        g["top"] += layers
        return {"clavicles": False, "exposed": True}

    def tank_holes(self, prefix, depth=0.29, half=0.20):
        """Scoop neck and armhole helpers shared by tank-style garments."""
        half *= self.neck_scale
        if self.back:
            depth *= BACK_NECK
        R = [(half, -0.02), (half * 0.95, depth * 0.41), (half * 0.65, depth * 0.86), (0.0, depth)]
        P = np.vstack([[(-half * 1.3, -2.0), (half * 1.3, -2.0)], R, mirror(R[::-1])[1:]])
        holes = []
        for side in (-1, 1):
            A = np.array([(0.34, -2.0), (2.0, -2.0), (2.0, 0.62), (0.64, 0.56), (0.52, 0.44), (0.40, 0.24), (0.35, 0.05)])
            A[:, 0] = np.where(A[:, 0] < 2.0, A[:, 0] + self.shoulder_dx, A[:, 0]) * side
            holes.append(self.S(geom.catmull_rom(A, 6, closed=True)))
        return [self.helper(f"{prefix}_neck", [self.S(geom.catmull_rom(P, 8, closed=True))]),
                self.helper(f"{prefix}_arm", holes)]

    def _one_piece(self, g):
        cutout = (self.variant or "classic") == "cutout"
        g["top"] += self.tank_holes("op", depth=0.42, half=0.21)
        legs = []
        for side in (-1, 1):
            L = np.array([(0.09, 2.47), (0.24, 2.30), (0.42, 2.10), (0.62, 1.90), (2.0, 1.90), (2.0, 7.0), (0.09, 7.0)])
            L[:, 0] *= side
            legs.append(self.C(self.body.pelvis(geom.catmull_rom(L, 6, closed=True, alpha=0.9)), 0.2))
        g["top"].append(self.helper("op_legs", legs))
        cuts = ("op_neck", "op_arm", "op_legs", "arms_mask")
        if self.back:
            scoop = np.array([(-0.40, -2.0), (0.40, -2.0), (0.40, BACK_SCOOP - 0.25), (0.0, BACK_SCOOP),
                              (-0.40, BACK_SCOOP - 0.25)])
            g["top"].append(self.helper("op_back", [self.S(geom.catmull_rom(scoop, 6, closed=True, alpha=0.9))]))
            cuts += ("op_back",)
        if cutout and not self.back:
            holes = [self.C(self.body.pelvis(geom.ellipse(side * 0.40, 1.42, 0.13, 0.16, 32, rot=side * 0.35)))
                     for side in (-1, 1)]
            g["top"].append(self.helper("op_cutout", holes))
            cuts = cuts + ("op_cutout",)
        g["top"].append(self.cloth("one_piece", self.torso(0.012), clip=("body_skin",), cut=cuts,
                                   inflate=0.15, tags=("garment", "swim_top")))
        g["top"] += self.bust_form("op", self.color, ("one_piece",), folds=False, strength=0.9)
        return {"clavicles": True, "exposed": True}

    def _rash_guard(self, g):
        # a cropped rash guard suits a bikini; on a male it left a skin band above the board shorts (v10 showcase)
        hem = RASH_GUARD_HEM["male" if self.male else "female"]
        g["top"] += [self.helper("rg_neck", [self.S(self.nx([(-0.30, -2.0), (0.30, -2.0), (0.17, -0.12), (-0.17, -0.12)]))]),
                     self.cloth("rash_guard", self.torso(0.020, hem, 0.0), cut=("rg_neck", "arms_mask"), inflate=0.15)]
        collar = self.nx([(-0.19, -0.13), (0.19, -0.13), (0.205, 0.07), (0.0, 0.10), (-0.205, 0.07)])
        g["top"].append(self.cloth("rg_collar", [self.C(geom.catmull_rom(collar, 6, closed=True, alpha=0.9), 0.27)],
                                   inflate=0.04, tags=("garment", "garment_top")))
        g["top"] += self.bust_form("rg", self.color, ("rash_guard",), strength=0.9)
        accent = col.hex_rgb("#E8E4DA")
        zip_line = [([(0.0, -0.12), (0.0, 0.8), (0.0, hem)], 1.0)]
        g["top"].append(self.ink("rg_zip", zip_line, color=col.light_of(self.color, 0.6), opacity=0.9))
        pull = self.C(np.array([(-0.022, 0.02), (0.022, 0.02), (0.018, 0.12), (-0.018, 0.12)]), 0.28)
        g["top"].append(Layer("rg_pull", Material.CLOTH, accent, polys=[pull], line=LineSpec(cfg.LINE_DETAIL * self.H),
                              shade=ShadeSpec(inflate=0.01 * self.H, spec=0.8)))
        self.sleeve_layers(g, "rg_sleeve", 0.035, inflate=0.08, extend=0.02)
        stripes = []
        for side in (-1, 1):
            s0, e, w = self.body.joints(side)
            stripes.append(([s0 + [side * 0.10, -0.02], e + [side * 0.10, 0.0]], 1.2))
        g["top"].append(Layer("rg_stripes", Material.INK, accent,
                              strokes=[(self.body.to_canvas(np.array(sp)), np.full(2, 0.016 * self.H)) for sp, _ in stripes],
                              clip=("sleeve",), opacity=0.9))
        return {"clavicles": False, "exposed": True}

    def _tank_top(self, g):
        hem = TOP_HEM["tank_top"]
        g["top"] += self.tank_holes("tank", depth=0.30, half=0.21)
        g["top"].append(self.cloth("tank_body", self.torso(0.020, hem, 0.02), cut=("tank_neck", "tank_arm", "arms_mask"),
                                   inflate=0.15))
        g["top"] += self.bust_form("tank", self.color, ("tank_body",))
        g["top"].append(self.ink("tank_hem", [([(-0.56, hem - 0.05), (0.0, hem - 0.03), (0.56, hem - 0.05)], 0.9)],
                                 opacity=0.35))
        return {"clavicles": True}

    def _shirtless(self, g):
        """Bare chest: the body layers already carry pectorals, abs and clavicles."""
        return {"clavicles": True, "exposed": True}

    def _beach_shirt(self, g):
        """Open short-sleeve shirt, over a triangle bikini top (female) or the bare chest (male)."""
        if not self.male and not self.back:
            shirt_color = self.color
            self.color = col.hex_rgb(self.s_bikini_color)
            self._bikini(g)
            self.color = shirt_color
        hem = 1.98
        opening = self.nx([(-0.17, -2.0), (0.17, -2.0), (0.13, 0.45), (0.21, 1.20), (0.28, 2.6), (-0.30, 2.6),
                            (-0.23, 1.20), (-0.15, 0.45)])
        g["top"].append(self.helper("bs_open", [self.S(geom.catmull_rom(opening, 6, closed=True, alpha=0.9))]))
        g["top"].append(self.cloth("beach_shirt", self.torso(0.045, hem, 0.05),
                                   cut=("arms_mask",) if self.back else ("bs_open", "arms_mask"), inflate=0.12))
        if (self.variant or "plain") == "print":
            rng = np.random.default_rng(17)
            flowers = []
            for _ in range(70):
                reach = 0.75 + self.shoulder_dx
                c = np.array([rng.uniform(-reach, reach), rng.uniform(0.0, hem)])
                r = rng.uniform(0.035, 0.06)
                for k in range(5):
                    a = k * 2 * np.pi / 5 + rng.uniform(0, 1)
                    flowers.append(self.C(geom.ellipse(c[0] + np.cos(a) * r * 0.6, c[1] + np.sin(a) * r * 0.6,
                                                       r * 0.5, r * 0.32, 12, rot=a)))
            g["top"].append(Layer("bs_print", Material.FLAT, col.hex_rgb(self.s_print_color), polys=flowers,
                                  clip=("beach_shirt",), opacity=0.85))
        flap = self.nx([(0.13, 0.42), (0.17, -0.06), (0.24, -0.03), (0.36, 0.13), (0.30, 0.30), (0.17, 0.32)])
        for side in (-1, 1):
            F = flap.copy()
            F[:, 0] *= side
            g["top"].append(self.cloth(f"bs_collar_{side}", [self.C(geom.catmull_rom(F, 3, closed=True, alpha=0.9), 0.28)],
                                       inflate=0.04, tags=("garment", "garment_top")))
        edges = [([(0.13, 0.45), (0.21, 1.2), (0.25, hem)], 0.8), ([(-0.15, 0.45), (-0.23, 1.2), (-0.27, hem)], 0.8)]
        g["top"].append(self.ink("bs_plackets", [(self.nx([(x + 0.04 * np.sign(x), y) for x, y in e]), w)
                                                 for e, w in edges],
                                 opacity=0.45))
        # buttons ride the left panel just outside the opening edge
        bys = 0.75 + 0.36 * np.arange(4)
        bxs = np.interp(bys, [0.45, 1.20, 2.60], [-0.15, -0.23, -0.30]) * self.neck_scale - 0.03
        buttons = [self.C(geom.ellipse(x, y, 0.016, 0.016, 16)) for x, y in zip(bxs, bys)]
        g["top"].append(Layer("bs_buttons", Material.FLAT, col.hex_rgb("#FFFFFF"), polys=buttons,
                              line=LineSpec(0.0035 * self.H)))
        for side in (-1, 1):
            g["top"].append(self.cloth(f"bs_sleeve_{side}", self.short_sleeve(side, 0.05, length=0.58), inflate=0.08,
                                       cut=self.bust_cut, tags=("garment", "sleeve")))
        return {"clavicles": True, "exposed": True}

    # ------------------------------------------------------------ swim bottom
    def brief_layer(self, name, right_half, color):
        """Swim bottom from an image-right outline, mirrored and clipped to the skin."""
        R = np.array(right_half)
        P = np.vstack([R, mirror(R[::-1])[1:-1]])
        P = self.body.pelvis(geom.catmull_rom(P, 8, closed=True, alpha=0.9))
        return Layer(name, Material.CLOTH, color, polys=[self.C(P, 0.2)], line=self.line, clip=("body_skin",),
                     shade=ShadeSpec(inflate=0.07 * self.H, cast_tags=("hand",), cast_dist=0.02 * self.H, threshold=0.12,
                                     rim=0.8, spec=0.2, spec_edge=0.9),
                     tags=("garment", "pants", "swim_bottom"))

    def _bikini_bottom_layers(self):
        H = self.H
        color = self.bottom_color
        shapes_ = SWIM_BOTTOMS_BACK if self.back else SWIM_BOTTOMS
        layers = [self.brief_layer("swim_bottom", shapes_.get(self.bottom_style, shapes_["classic"]), color)]
        if self.bottom_style == "string":
            strokes, bows = [], []
            for side in (-1, 1):
                sp = self.body.pelvis(np.array([(side * 0.205, 2.005), (side * 0.40, 1.96), (side * 0.62, 1.91)]))
                strokes.append((self.C(geom.catmull_rom(sp, 8)), np.full(17, 0.017 * H)))
                knot = self.body.pelvis([(side * 0.54, 1.93)])[0]
                for a in (-0.6, 0.6):
                    loop = geom.ellipse(knot[0] + side * 0.035 * np.cos(a), knot[1] - 0.02, 0.035, 0.018, 16,
                                        rot=a * side)
                    bows.append(self.C(loop))
                for dx in (0.0, 0.03):
                    tail = np.array([knot, knot + [side * dx, 0.10]])
                    strokes.append((self.C(tail), np.full(2, 0.012 * H)))
            layers.append(Layer("swim_ties", Material.INK, col.shadow_of(color, 0.10), strokes=strokes,
                                clip=("body_skin",), tags=("garment",)))
            layers.append(Layer("swim_bows", Material.CLOTH, color, polys=bows, line=LineSpec(cfg.LINE_DETAIL * H),
                                shade=ShadeSpec(inflate=0.01 * H)))
        return layers

    def _shoes(self, g):
        if self.shoe_kind in ("barefoot", "sandals", "heels"):
            g["shoes"] += self.body.feet_layers(self.shoe_kind, self.shoe_color)
            return
        shoe = np.array([(-0.080, -0.06), (0.080, -0.06), (0.100, 0.10), (0.118, 0.25), (0.090, 0.34),
                         (-0.070, 0.34), (-0.105, 0.25), (-0.098, 0.10)])
        sole = np.array([(-0.105, 0.27), (0.118, 0.27), (0.110, 0.35), (-0.100, 0.35)])
        polys, soles, laces = [], [], []
        for side in (-1, 1):
            a = self.body.leg_joints(side)[2] - [0.0, 0.02]
            S, So = shoe.copy(), sole.copy()
            if side in self.body.stance.get("raised_foot", ()):
                S, So = S * RAISED_FOOT_SCALE, So * RAISED_FOOT_SCALE
            S[:, 0] *= side
            So[:, 0] *= side
            polys.append(self.body.to_canvas(geom.catmull_rom(S + a, 6, closed=True)))
            soles.append(self.body.to_canvas(geom.catmull_rom(So + a, 3, closed=True, alpha=0.9)))
            for k in range(3):
                y = a[1] + 0.02 + k * 0.055
                laces.append(([(a[0] - 0.04, y), (a[0] + 0.04, y + 0.01)], 0.8))
        sole_col = col.hex_rgb("#FFFFFF") if self.shoe_kind == "sneakers" else col.shadow_of(self.shoe_color, 0.4)
        if self.shoe_kind == "dress_shoes":
            sole_col = col.shadow_of(self.shoe_color, 0.5)
        g["shoes"] += [
            Layer("shoes", Material.CLOTH, self.shoe_color, polys=polys, line=self.line,
                  shade=ShadeSpec(inflate=0.04 * self.H, cast_tags=("pants",), cast_dist=0.03 * self.H, spec=0.6),
                  tags=("shoes",)),
            Layer("soles", Material.CLOTH, sole_col, polys=soles, line=LineSpec(cfg.LINE_BODY * self.H * 0.7),
                  shade=ShadeSpec(inflate=0.01 * self.H)),
        ]
        if self.shoe_kind == "sneakers":
            g["shoes"].append(self.ink("laces", laces, color=self.shoe_color, opacity=0.6))
