"""paintkit.figure: paints the full-body figure (pure 2D).

Every body part is a smooth shape hung between two joints of the skeleton
(body.py); garments are the body parts grown outward. The head is the
existing Portrait rig, positioned by the skeleton, so faces and hair look
the same in bust and full-body pictures.
"""
from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np

from . import core as pk
from . import furniture
from . import light as lt
from . import props
from . import wardrobe
from .body import DEPTH, SIDES, Build, Pose, _across, _up, plan_for, solve_skeleton, turn_factors
from .character import Portrait
from .hand import Hand
from .spec import CharacterSpec, RenderStyle

SKIRT_GARMENTS = ("dress", "skirt", "bodycon") + wardrobe.SKIRT_GARMENTS
LAP_COVER = 0.90                  # share of the thigh a skirt covers on a seated figure
BUST_SIDE_LIGHT = 0.35            # share of the light's sideways component kept on the bust
OUTFITS = ("dress", "blouse_skirt", "sweater_pants", "bodycon", "swimsuit", "suit", "shirt_pants",
           "tshirt_jeans", "trunks", "innerwear", "crop_hotpants", "hoodie_jeans", "none") + wardrobe.OUTFITS
OUTFIT_ALIASES = {"bikini": "swimsuit"}
BAREFOOT_OUTFITS = ("swimsuit", "trunks", "innerwear", "none")
# Who each outfit is cut for. Any outfit is drawn on either gender when a spec asks for it;
# the table picks the default outfit and groups the names in error messages and documents.
OUTFIT_GENDER = {"dress": "female", "blouse_skirt": "female", "bodycon": "female", "swimsuit": "female",
                 "crop_hotpants": "female", "trunks": "male", **wardrobe.OUTFIT_GENDER}
DEFAULT_OUTFIT = {"female": "dress", "male": "shirt_pants"}


def resolve_outfit(name: str) -> str:
    """Outfit name with aliases resolved; an unknown name stops with the names grouped by gender."""
    name = OUTFIT_ALIASES.get(name, name)
    if name in OUTFITS:
        return name
    alias_of = {target: alias for alias, target in OUTFIT_ALIASES.items()}
    groups = {}
    for outfit in OUTFITS:
        label = f"{outfit} ({alias_of[outfit]})" if outfit in alias_of else outfit
        groups.setdefault(OUTFIT_GENDER.get(outfit, "unisex"), []).append(label)
    listing = "; ".join(f"{gender}: {', '.join(groups[gender])}" for gender in ("female", "male", "unisex"))
    raise ValueError(f"unknown figure outfit '{name}', expected one of {listing}")
# Straight trouser legs (diameters along thigh and shin): cloth hangs from
# the thigh and hides the calf instead of following it.
TROUSER_THIGH = ((0.0, 0.660), (0.50, 0.560), (1.0, 0.460))
TRUNKS_LENGTH = 0.33              # share of the thigh covered by swim trunks
TROUSER_SHIN = ((0.0, 0.460), (1.0, 0.420))
# Suit jacket opening and lapel, right half in the chest frame.
JACKET_V = ((0.150, -0.200), (0.0, 0.800))
JACKET_LAPEL = ((0.150, -0.120), (0.245, -0.060), (0.370, 0.150), (0.305, 0.235), (0.360, 0.300),
                (0.030, 0.800), (0.0, 0.800))
TIE_SHAPE = ((-0.040, -0.110), (0.040, -0.110), (0.030, -0.020), (0.070, 0.700), (0.0, 0.780), (-0.070, 0.700),
             (-0.030, -0.020))
SHIRT_COLLAR_WING = ((0.100, -0.210), (0.165, -0.170), (0.215, -0.040), (0.120, 0.060), (0.050, 0.110),
                     (0.085, -0.060))
# Innerwear (chest frame, relative to each bust center in bust radii): a balconette cup
# cut low across the top, and the brief (pelvis frame) cut higher on the hip than a bikini.
BRA_CUP = ((-0.95, 0.55), (-0.30, -0.50), (0.95, -0.38), (0.88, 0.72), (0.05, 1.02))
BRA_STRAP_TOP = (0.285, -0.120)   # over the collarbone, halfway out to the shoulder
INNERWEAR_BRIEF = ((-0.610, -0.140), (-0.540, -0.250), (0.0, -0.190), (0.540, -0.250), (0.610, -0.140),
                  (0.205, 0.365), (0.0, 0.440), (-0.205, 0.365))
BRA_BAND_TOP = 0.78              # underband top, in bust radii below the bust center
BRA_BAND_DEPTH = 0.07            # underband height (head units)
LACE_TRIM = 0.045                 # width of the lace border inside a innerwear edge (head units)
LACE_DOT = 0.016                  # spacing of the lace mesh
BOXER_LENGTH = 0.30               # share of the thigh covered by boxer briefs
# Casual wear (pelvis frame unless noted): crop tee hem above the navel, low-rise hot pants.
CROP_HEM_Y = -0.95
HOTPANTS_WAIST_Y = -0.30
HOTPANTS_LENGTH = 0.16            # share of the thigh the shorts cover (outer seam)
HOODIE_HEM_Y = 0.10
HOODIE_RIB = 0.10                 # hem band and cuff height
HOOD_LOBE = ((0.055, -0.170), (0.150, -0.300), (0.300, -0.250), (0.390, -0.070), (0.300, 0.020), (0.150, -0.040))
HOODIE_POCKET = ((-0.300, -0.560), (0.300, -0.560), (0.400, -0.090), (-0.400, -0.090))
# Garments a hand can go into, and how far up the forearm their cover may hide it.
POCKET_GARMENTS = ("pants_hips", "hotpants", "skirt", "dress", "jacket", "hoodie") + wardrobe.POCKET_GARMENTS
# (swim and underwear: none)
POCKET_REACH = 0.55
POCKETLESS_HAND_DEG = 28.0
SEAT_COLOR, SEAT_SHADOW = "#8a6a52", "#5a4034"
MUSCLE_WIDTH_GAIN = 0.15          # limb thickness gained per unit of Build.muscle


class Figure(Portrait):
    """Full-body figure. Layers (bottom to top): hair_back, seat, figure, face,
    features, hair_front, see_through, figure_front, rim."""

    cigarette = None              # "left" | "right" | "mouth" (props.CIGARETTE_HOLDS), set by scene.make_figure

    def __init__(self, canvas: pk.Canvas, spec: CharacterSpec, style: RenderStyle, head_height: float,
                 pelvis_px, pose: Pose | None = None, outfit: str = "dress", build: Build | None = None,
                 heels: bool = False, light=None, furniture: str | None = None, furniture_color=None):
        outfit = resolve_outfit(outfit)
        self.pose = pose or Pose()
        self.build = build or Build()
        self.fig_outfit = outfit
        self.heels = heels
        self.furniture = furniture if furniture is not None else (self.pose.support or "none")
        self.furniture_color = furniture_color
        self.plan = plan_for(spec.gender)
        self.turn_cos, self.turn_sin = turn_factors(self.pose)
        self.joints = solve_skeleton(self.pose, self.build, self.plan)
        self.muscle_gain = 1.0 + MUSCLE_WIDTH_GAIN * (self.build.muscle - 1.0)
        self.pelvis_px = np.asarray(pelvis_px, np.float32)
        eyes = self.pelvis_px + self.joints["eyes"] * head_height
        # The head leans with the neck; the character's own tilt is added on top.
        spec = replace(spec, head_tilt=spec.head_tilt + self.pose.neck)
        super().__init__(canvas, spec, style, head_height, eyes, light)

    # -- coordinate helpers -------------------------------------------------
    def at(self, pts_hu) -> np.ndarray:
        """Skeleton space (head units from the pelvis) to pixels."""
        return self.pelvis_px + np.asarray(pts_hu, np.float32) * self.hh

    def _turned(self, x: float, depth: float) -> float:
        """A body turn narrows widths and slides forward-lying points sideways."""
        return x * self.turn_cos + depth * self.turn_sin

    def chest_pt(self, x: float, y: float, depth: float = 0.0) -> np.ndarray:
        axis = _across(self.pose.chest + self.pose.shoulder_tilt)
        return self.joints["chest"] + axis * self._turned(x, depth) - _up(self.pose.chest) * y

    def pelvis_pt(self, x: float, y: float, depth: float = 0.0) -> np.ndarray:
        axis = _across(self.pose.hip_tilt)
        return (self.joints["pelvis"] + axis * self._turned(x, depth)
                + np.array([-axis[1], axis[0]], np.float32) * y)

    def grow(self, mask, amount: float) -> np.ndarray:
        size = int(round(self.px(amount))) * 2 + 1
        return cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))

    def limb(self, start, end, profile, extra: float = 0.0, t_range=(0.0, 1.0), bow=None, side: float = 1.0,
             root_scale: float = 1.0):
        """(path, widths) of one limb segment.

        extra: added thickness (cloth). bow: sideways offset profile of the
        centerline. root_scale: width multiplier at the root that fades to 1
        at the far end (wide hips widen the top of the thigh, not the knee).
        """
        t = np.linspace(t_range[0], t_range[1], 24)[:, None]
        start, end = np.asarray(start, np.float32), np.asarray(end, np.float32)
        line = start * (1.0 - t) + end * t
        if bow is not None:
            axis = (end - start) / (np.linalg.norm(end - start) or 1.0)
            outward = np.array([axis[1], -axis[0]], np.float32) * side      # perpendicular, toward the outside
            positions, offsets = zip(*bow)
            line = line + outward * np.interp(t[:, 0], positions, offsets)[:, None]
        positions, diameters = zip(*profile)
        # Cloth sits close at the root of a limb and loosens further down;
        # full thickness at the root would puff up into a shoulder pad.
        ease = 0.30 + 0.70 * pk.smoothstep(0.0, 0.30, t[:, 0]) if t_range[0] == 0.0 else 1.0
        taper = 1.0 + (root_scale - 1.0) * (1.0 - t[:, 0])
        widths = (np.interp(t[:, 0], positions, diameters) * self.muscle_gain * taper + extra * ease) * self.hh
        return self.at(line), widths

    # -- part masks ---------------------------------------------------------
    def bust_centers(self) -> list:
        return [self.chest_pt(self.plan.bust_center[0] * sign, self.plan.bust_center[1], DEPTH["bust"]) for sign in (1.0, -1.0)]

    def bust_mask(self) -> np.ndarray:
        radius = self.plan.bust_radius * self.build.bust
        shapes = [pk.ellipse(cx, cy, radius * 0.94 * self.plan.bust_aspect, radius) for cx, cy in self.bust_centers()]
        return pk.fill_mask(self.shape, [self.at(shape) for shape in shapes])

    def torso_mask(self) -> np.ndarray:
        scale = self.build.scale
        right = ([self.chest_pt(x * scale(key), y) for x, y, key in self.plan.chest_side]
                 + [self.pelvis_pt(x * scale(key), y) for x, y, key in self.plan.pelvis_side])
        left = ([self.chest_pt(-x * scale(key), y) for x, y, key in self.plan.chest_side]
                + [self.pelvis_pt(-x * scale(key), y) for x, y, key in self.plan.pelvis_side])
        crotch = self.pelvis_pt(0.0, self.plan.crotch_y, DEPTH["crotch"])
        outline = pk.spline(np.array(right + [crotch] + left[::-1]), closed=True, n=8)
        torso = pk.fill_mask(self.shape, self.at(outline))
        neck = pk.resample(self.at(np.array([self.chest_pt(0.0, -0.10), self.joints["skull"]])), 12)
        widths = np.interp(np.linspace(0.0, 1.0, 12), (0.0, 0.45, 1.0), self.plan.neck_width) * self.hh
        torso = np.maximum(torso, pk.stroke_mask(self.shape, (neck, widths)))
        # In a turned body the far breast passes the edge of the ribcage and
        # becomes part of the silhouette; from the front it stays inside. A man's chest
        # muscle is a flat plate on the ribcage: added here it bulged out like a breast.
        return np.maximum(torso, self.bust_mask()) if self.build.bust > 0 and not self.male else torso

    def arm_strokes(self, side: str, extra: float = 0.0, upto: float = 1.0) -> list:
        """`upto` in 0-2: 1.0 = to the elbow, 2.0 = to the wrist (sleeve length)."""
        j, sign = self.joints, SIDES[side]
        strokes = [self.limb(j[f"shoulder_{side}"], j[f"elbow_{side}"], self.plan.upper_arm_width, extra,
                             (0.0, min(upto, 1.0)))]
        if upto > 1.0:
            strokes.append(self.limb(j[f"elbow_{side}"], j[f"wrist_{side}"], self.plan.forearm_width, extra,
                                     (0.0, upto - 1.0), self.plan.forearm_bow, sign))
        return strokes

    def leg_strokes(self, side: str, extra: float = 0.0, upto: float = 2.0) -> list:
        j, sign = self.joints, SIDES[side]
        strokes = [self.limb(j[f"hip_{side}"], j[f"knee_{side}"], self.plan.thigh_width, extra, (0.0, min(upto, 1.0)),
                             self.plan.thigh_bow, sign, root_scale=self.build.hips)]
        if upto > 1.0:
            strokes.append(self.limb(j[f"knee_{side}"], j[f"ankle_{side}"], self.plan.shin_width, extra, (0.0, upto - 1.0),
                                     self.plan.shin_bow, sign))
        return strokes

    def foot_mask(self, side: str) -> np.ndarray:
        angle = getattr(self.pose, f"foot_{side}")
        outline = self.plan.foot_heeled if self.heels else self.plan.foot_shape
        shape = pk.rotate(outline * [SIDES[side], 1.0], -angle) + self.joints[f"ankle_{side}"]
        return pk.fill_mask(self.shape, self.at(pk.spline(shape, closed=True, n=8)))

    def make_hand(self, side: str) -> Hand:
        fore = getattr(self.pose, f"hand_{side}_angle")
        if fore is None:
            fore = self.joints[f"arm_angles_{side}"][1]
        # Keep the thumb on the inner (body) side whichever way the hand points.
        mirror = SIDES[side] * (1.0 if np.cos(np.deg2rad(fore)) >= 0 else -1.0) < 0
        frame = pk.Frame(self.at(self.joints[f"wrist_{side}"]), self.px(self.plan.hand_length), -fore)
        return Hand(self.shape, frame, getattr(self.pose, f"hand_{side}"), mirror,
                    getattr(self.pose, f"hand_{side}_view"), self.plan.hand_widen,
                    getattr(self.pose, f"hand_{side}_roll"), getattr(self.pose, f"hand_{side}_pitch"))

    def build_masks(self):
        super().build_masks()
        m = self.masks
        m["torso"] = self.torso_mask()
        self.hands = {side: self.make_hand(side) for side in SIDES}
        for side in SIDES:
            m[f"arm_{side}"] = pk.stroke_mask(self.shape, self.arm_strokes(side, upto=2.0))
            m[f"leg_{side}"] = np.maximum(pk.stroke_mask(self.shape, self.leg_strokes(side)), self.foot_mask(side))
        m["legs"] = np.maximum(m["leg_left"], m["leg_right"])
        parts = [m["torso"], m["legs"]] + [m[f"arm_{side}"] for side in SIDES]
        m["body"] = np.maximum.reduce(parts + [hand.mask for hand in self.hands.values()])
        self.garments = self.lap_garments(self.garment_masks())
        zero = np.zeros(self.shape, np.float32)
        m["cloth"] = np.maximum.reduce([g["mask"] for g in self.garments] or [zero])
        self.pocket_hands()

    def pocket_hands(self):
        """A hand in a pocket: the forearm ends where the cloth covers it. Without a garment
        over the wrist there is no pocket, and the hand shows, relaxed."""
        for side in SIDES:
            if getattr(self.pose, f"hand_{side}") != "pocket":
                continue
            covers = [g["mask"] for g in self.garments if g["name"] in POCKET_GARMENTS]
            wrist = self.at(self.joints[f"wrist_{side}"])
            col, row = (int(np.clip(v, 0, n - 1)) for v, n in zip(wrist, self.shape[::-1]))
            cover = np.maximum.reduce(covers) if covers else None
            if cover is None or cover[row, col] < 0.5:
                # Fingers turned out along the hip rather than in across the front.
                self.pose = replace(self.pose, **{f"hand_{side}": "relaxed",
                                                  f"hand_{side}_angle": POCKETLESS_HAND_DEG * SIDES[side]})
                self.hands[side] = self.make_hand(side)
                continue
            near = (pk.radial_ramp(self.shape, wrist, self.px(POCKET_REACH)) > 0).astype(np.float32)
            hide = 1.0 - cover * near
            self.masks[f"arm_{side}"] = self.masks[f"arm_{side}"] * hide
            for garment in self.garments:          # the sleeve end goes into the pocket too
                if garment["zone"] == f"arm_{side}":
                    garment["mask"] = garment["mask"] * hide

    # -- garments -----------------------------------------------------------
    def chest_cover(self, neckline, lower: float = 2.4) -> np.ndarray:
        """Mask of everything below a neckline given as right-half chest points."""
        depth = DEPTH["chest"]
        right = [self.chest_pt(x, y, depth) for x, y in neckline]
        left = [self.chest_pt(-x, y, depth) for x, y in neckline]
        outer_y = neckline[-1][1]
        poly = [self.chest_pt(-1.2, lower), self.chest_pt(-1.2, outer_y)] + left[::-1] + right + \
               [self.chest_pt(1.2, outer_y), self.chest_pt(1.2, lower)]
        return pk.fill_mask(self.shape, self.at(np.array(poly)))

    def chest_band(self, top: float, bottom: float) -> np.ndarray:
        """Horizontal band of the chest frame between two heights. A difference of covers:
        the product cover * (1 - cover) leaves a faint line along their shared lower edge."""
        line = lambda y: ((0.0, y), (0.80, y))
        return np.clip(self.chest_cover(line(top)) - self.chest_cover(line(bottom)), 0.0, 1.0)

    @staticmethod
    def bridge_rows(mask) -> np.ndarray:
        """Fill every row between its leftmost and rightmost covered pixel.

        A skirt stretches straight across from thigh to thigh; without this
        a dress built from the leg shapes would split into shorts."""
        covered = mask > 0.5
        any_row = covered.any(axis=1)
        first = covered.argmax(axis=1)
        last = mask.shape[1] - 1 - covered[:, ::-1].argmax(axis=1)
        columns = np.arange(mask.shape[1])[None, :]
        span = (columns >= first[:, None]) & (columns <= last[:, None]) & any_row[:, None]
        return np.maximum(mask, span.astype(np.float32))

    def above_line(self, y: float) -> np.ndarray:
        """Mask of everything above a level line `y` below the pelvis (gravity, not pelvis tilt)."""
        base = self.joints["pelvis"]
        return pk.fill_mask(self.shape, self.at(np.array([base + [-4, -5], base + [4, -5], base + [4, y],
                                                          base + [-4, y]])))

    def skirt_mask(self, hem_y: float, hem_half: float, hip_half: float) -> np.ndarray:
        """Skirt from the waist to a hem. The waistband follows the tilted
        pelvis; from the hips down the cloth hangs straight (gravity)."""
        def hang_pt(x, y):
            return self.joints["pelvis"] + np.array([x * self.turn_cos, y], np.float32)

        waist = 0.305 * self.build.waist
        hip_half = hip_half * self.build.hips
        side = [(waist, -0.760), (hip_half * 0.87, -0.400), (hip_half, 0.080),
                ((hip_half + hem_half) / 2 + 0.012, hem_y * 0.55), (hem_half, hem_y)]
        placers = [self.pelvis_pt, self.pelvis_pt, self.pelvis_pt, hang_pt, hang_pt]
        right = pk.spline(np.array([place(x, y) for place, (x, y) in zip(placers, side)]), n=8)
        left = pk.spline(np.array([place(-x, y) for place, (x, y) in zip(placers, side)]), n=8)
        # The hem dips slightly at the center, the way a hanging cloth edge does.
        hem = pk.spline(np.array([hang_pt(hem_half, hem_y), hang_pt(0.0, hem_y + 0.05),
                                  hang_pt(-hem_half, hem_y)]), n=8)
        cloth = pk.fill_mask(self.shape, self.at(np.vstack([right, hem, left[::-1]])))
        # A leg that swings outside the cut still wears the skirt down to the hem.
        return np.maximum(cloth, self.grow(self.masks["legs"], 0.03) * self.above_line(hem_y))

    def sleeve_mask(self, side: str, extra: float, upto: float) -> np.ndarray:
        return pk.stroke_mask(self.shape, self.arm_strokes(side, extra, upto))

    def swimsuit_masks(self):
        """Bikini: two cups with ties, and a brief."""
        m, depth = self.masks, DEPTH["bust"]
        radius = self.plan.bust_radius * self.build.bust
        skin = self.grow(np.maximum(m["torso"], m["legs"]), 0.008)
        cups, ties = [], []
        for sign in (1.0, -1.0):
            cx, cy = self.plan.bust_center[0] * sign, self.plan.bust_center[1]
            corners = [(cx - radius * 0.85 * sign, cy + radius * 0.45), (cx, cy - radius * 1.20),
                       (cx + radius * 1.02 * sign, cy + radius * 0.30), (cx + radius * 0.10 * sign, cy + radius * 1.08)]
            cups.append(self.at(pk.spline(np.array([self.chest_pt(x, y, depth) for x, y in corners]), closed=True)))
            neck_tie = np.array([self.chest_pt(cx, cy - radius * 1.15, depth), self.chest_pt(0.110 * sign, -0.165)])
            ties.append((pk.resample(self.at(neck_tie), 12), self.px(0.020)))
        band = np.array([self.chest_pt(-0.46, 0.745), self.chest_pt(0.0, 0.760, DEPTH["chest"]),
                         self.chest_pt(0.46, 0.745)])
        ties.append((pk.resample(self.at(pk.spline(band)), 24), self.px(0.022)))
        top = np.maximum(pk.fill_mask(self.shape, cups), pk.stroke_mask(self.shape, ties)) * skin
        hips = self.build.hips
        brief = [(-0.615 * hips, -0.060), (-0.550 * hips, -0.170), (0.0, -0.105), (0.550 * hips, -0.170),
                 (0.615 * hips, -0.060), (0.215, 0.365), (0.0, 0.440), (-0.215, 0.365)]
        depths = [0.0, 0.0, DEPTH["belly"], 0.0, 0.0, DEPTH["crotch"], DEPTH["crotch"], DEPTH["crotch"]]
        bottom = pk.fill_mask(self.shape, self.at(pk.spline(
            np.array([self.pelvis_pt(x, y, d) for (x, y), d in zip(brief, depths)]), closed=True))) * skin
        return top, bottom

    def garment_masks(self) -> list:
        """[{name, mask, color, shadow, zone}], painted in list order within a zone.
        zone: torso | arm_left | arm_right | leg_left | leg_right | lap."""
        pal, m, kind = self.pal, self.masks, self.fig_outfit

        def dark(color):
            return pk.adjust(color, value=0.66, sat=1.15)

        shoes = []
        if self.heels or kind not in BAREFOOT_OUTFITS:
            shoes = [dict(name=f"shoe_{side}", mask=self.grow(self.foot_mask(side), 0.016), color=pal.shoe,
                          shadow=dark(pal.shoe), zone=f"leg_{side}") for side in SIDES]
        if kind == "none":
            return shoes
        cloth = dict(color=pal.cloth, shadow=pal.cloth_shadow)
        if kind in ("suit", "shirt_pants", "tshirt_jeans", "trunks"):
            return self.menswear_masks(kind, shoes, cloth, dark)
        if kind == "innerwear":
            return shoes + self.innerwear_masks(cloth, dark)
        if kind in ("crop_hotpants", "hoodie_jeans"):
            return self.casual_masks(kind, shoes, cloth, dark)
        if kind in wardrobe.OUTFITS:
            return wardrobe.front_garments(self, kind, shoes)
        if kind == "swimsuit":
            top, bottom = self.swimsuit_masks()
            return shoes + [dict(name="bikini_bottom", mask=bottom, zone="torso", fitted=True, **cloth),
                            dict(name="bikini_top", mask=top, zone="torso", fitted=True, **cloth)]
        if kind == "bodycon":
            neckline = ((0.0, 0.420), (0.110, 0.345), (0.235, 0.300), (0.390, 0.350), (0.500, 0.300), (0.80, 0.300))
            cover = self.chest_cover(neckline) * self.above_line(1.02)
            skirt = self.bridge_rows(self.grow(m["legs"], 0.012) * cover * (1.0 - self.above_line(0.10)))
            mask = np.maximum(self.grow(m["torso"], 0.012) * cover, skirt)
            straps = [(pk.resample(self.at(np.array([self.chest_pt(0.240 * sign, 0.310, DEPTH["chest"]),
                                                     self.chest_pt(0.205 * sign, -0.125)])), 12), self.px(0.026))
                      for sign in (1.0, -1.0)]
            mask = np.maximum(mask, pk.stroke_mask(self.shape, straps) * self.grow(m["torso"], 0.012))
            return shoes + [dict(name="bodycon", mask=mask, zone="torso", fitted=True, **cloth)]
        if kind == "dress":
            neckline = ((0.0, 0.300), (0.140, 0.230), (0.180, -0.105), (0.320, -0.075), (0.390, 0.170),
                        (0.80, 0.230))
            bodice = self.grow(m["torso"], 0.012) * self.chest_cover(neckline)
            mask = np.maximum(bodice, self.skirt_mask(1.60, 0.82, 0.630))
            return shoes + [dict(name="dress", mask=mask, zone="torso", folds=(1.60, 0.82, 6), **cloth)]

        def sleeves(extra, upto):
            return [dict(name=f"sleeve_{side}", mask=self.sleeve_mask(side, extra, upto), zone=f"arm_{side}",
                         **cloth) for side in SIDES]

        if kind == "blouse_skirt":
            neckline = ((0.0, 0.330), (0.140, -0.050), (0.235, -0.135), (0.80, -0.02))
            blouse = self.grow(m["torso"], 0.020) * self.chest_cover(neckline)
            skirt = self.skirt_mask(1.52, 0.520, 0.630)
            # Blouse first: it is tucked into the skirt.
            return shoes + sleeves(0.032, 2.0) + [
                dict(name="blouse", mask=blouse, zone="torso", **cloth),
                dict(name="skirt", mask=skirt, color=pal.cloth2, shadow=dark(pal.cloth2), zone="torso",
                     folds=(1.52, 0.520, 2))]
        # sweater_pants
        neckline = ((0.0, -0.020), (0.125, -0.085), (0.170, -0.160), (0.80, -0.10))
        hem_line = self.above_line(-0.02)
        sweater = self.grow(m["torso"], 0.038) * self.chest_cover(neckline) * hem_line
        hips = self.grow(m["torso"], 0.014) * (1.0 - hem_line)
        pants = [dict(name=f"pants_{side}", mask=pk.stroke_mask(self.shape, self.leg_strokes(side, 0.035, 1.97)),
                      color=pal.cloth2, shadow=dark(pal.cloth2), zone=f"leg_{side}") for side in SIDES]
        # Pants first: the sweater hangs over the waistband.
        return pants + shoes + sleeves(0.060, 1.94) + [
            dict(name="pants_hips", mask=hips, color=pal.cloth2, shadow=dark(pal.cloth2), zone="torso",
                 fitted=True, no_line=m["legs"]),
            dict(name="sweater", mask=sweater, zone="torso", **cloth)]

    def chest_poly(self, points, mirror_x: bool = False) -> np.ndarray:
        """Mask of a polygon given in chest-frame points (x mirrored when asked)."""
        sign = -1.0 if mirror_x else 1.0
        pts = [self.chest_pt(x * sign, y, DEPTH["chest"]) for x, y in points]
        return pk.fill_mask(self.shape, self.at(np.array(pts)))

    def beyond(self, start: str, end: str, t: float) -> np.ndarray:
        """Half-plane past the point at fraction t from joint `start` to `end`,
        cut square to the bone: a straight hem or sleeve end."""
        a, b = self.joints[start], self.joints[end]
        axis = (b - a) / (np.linalg.norm(b - a) or 1.0)
        across = np.array([-axis[1], axis[0]], np.float32) * 3.0
        point = a + (b - a) * t
        return pk.fill_mask(self.shape, self.at(np.array([point - across, point + across,
                                                          point + across + axis * 6.0, point - across + axis * 6.0])))

    def trouser_strokes(self, side: str, extra: float) -> list:
        j = self.joints
        return [self.limb(j[f"hip_{side}"], j[f"knee_{side}"], TROUSER_THIGH, extra, root_scale=self.build.hips),
                self.limb(j[f"knee_{side}"], j[f"ankle_{side}"], TROUSER_SHIN, extra, (0.0, 0.97))]

    def menswear_masks(self, kind: str, shoes: list, cloth: dict, dark) -> list:
        """Suit, shirt and trousers, t-shirt and jeans, swim trunks."""
        pal, m = self.pal, self.masks
        lower = dict(color=pal.cloth2, shadow=dark(pal.cloth2))

        def sleeves(extra, upto, colors):
            if upto < 1.0:             # short sleeve: cut square across the upper arm
                masks = {side: self.sleeve_mask(side, extra, 1.0)
                         * (1.0 - self.beyond(f"shoulder_{side}", f"elbow_{side}", upto)) for side in SIDES}
            else:
                masks = {side: self.sleeve_mask(side, extra, upto) for side in SIDES}
            return [dict(name=f"sleeve_{side}", mask=masks[side], zone=f"arm_{side}", **colors) for side in SIDES]

        def legs(strokes_of, waist_y):
            hips = self.grow(m["torso"], 0.03) * (1.0 - self.above_line(waist_y))
            pants = [dict(name=f"pants_{side}", mask=pk.stroke_mask(self.shape, strokes_of(side)), zone=f"leg_{side}",
                          **lower) for side in SIDES]
            return pants, dict(name="pants_hips", mask=hips, zone="torso", fitted=True, no_line=m["legs"], **lower)

        if kind == "trunks":
            legs_cut = [pk.stroke_mask(self.shape, self.leg_strokes(side, 0.040, 1.0))
                        * (1.0 - self.beyond(f"hip_{side}", f"knee_{side}", TRUNKS_LENGTH)) for side in SIDES]
            band = 1.0 - self.above_line(-0.36)
            mask = np.maximum.reduce(legs_cut + [self.grow(m["torso"], 0.025)]) * band
            return shoes + [dict(name="trunks", mask=mask, zone="torso", **cloth)]
        if kind == "tshirt_jeans":
            pants, hips = legs(lambda side: self.leg_strokes(side, 0.035, 1.97), -0.40)
            neckline = ((0.0, -0.050), (0.120, -0.100), (0.170, -0.160), (0.80, -0.120))
            tee = self.grow(m["torso"], 0.035) * self.chest_cover(neckline) * self.above_line(0.04)
            return pants + shoes + sleeves(0.055, 0.48, cloth) + [hips, dict(name="tee", mask=tee, zone="torso",
                                                                             **cloth)]
        pants, hips = legs(lambda side: self.trouser_strokes(side, 0.02), -0.34)
        if kind == "shirt_pants":
            neckline = ((0.0, 0.300), (0.120, 0.050), (0.170, -0.120), (0.80, -0.100))
            shirt = self.grow(m["torso"], 0.030) * self.chest_cover(neckline) * self.above_line(-0.30)
            belt = self.grow(m["torso"], 0.036) * self.above_line(-0.24) * (1.0 - self.above_line(-0.33))
            collar = np.maximum(self.chest_poly(SHIRT_COLLAR_WING), self.chest_poly(SHIRT_COLLAR_WING, True))
            return pants + shoes + sleeves(0.045, 1.96, cloth) + [
                hips, dict(name="shirt", mask=shirt, zone="torso", buttons=(0.30, 1.00), **cloth),
                dict(name="belt", mask=belt, color=pal.shoe, shadow=dark(pal.shoe), zone="torso", fitted=True),
                dict(name="collar", mask=collar * self.grow(m["torso"], 0.06), zone="torso", fitted=True, **cloth)]
        # suit: shirt and tie show in the V of the jacket
        opening = self.chest_poly([(-JACKET_V[0][0], JACKET_V[0][1]), JACKET_V[0], JACKET_V[1]])
        chest = self.grow(m["torso"], 0.03)
        shirt = chest * self.chest_cover(((0.0, -0.150), (0.120, -0.180), (0.80, -0.180))) * opening
        tie = self.chest_poly(TIE_SHAPE) * opening
        jacket = np.maximum(self.grow(m["torso"], 0.048),
                            self.bridge_rows(self.grow(m["legs"], 0.05) * self.above_line(0.36)))
        collar_line = ((0.0, -0.120), (0.180, -0.150), (0.80, -0.120))
        jacket = jacket * self.above_line(0.36) * (1.0 - opening) * self.chest_cover(collar_line)
        lapels = np.maximum(self.chest_poly(JACKET_LAPEL), self.chest_poly(JACKET_LAPEL, True)) * jacket
        suit = dict(color=pal.cloth2, shadow=dark(pal.cloth2))
        return pants + shoes + sleeves(0.035, 1.96, suit) + [
            hips, dict(name="shirt", mask=shirt, zone="torso", fitted=True, **cloth),
            dict(name="tie", mask=tie, color=pal.accent, shadow=dark(pal.accent), zone="torso", fitted=True),
            dict(name="jacket", mask=jacket, zone="torso", seam=True, **suit),
            dict(name="lapels", mask=lapels, color=pk.adjust(pal.cloth2, value=1.25), shadow=suit["color"],
                 zone="torso", fitted=True)]

    def innerwear_masks(self, cloth: dict, dark) -> list:
        """Lace bra and brief; a man's set is boxer briefs with a contrast waistband."""
        m, pal = self.masks, self.pal
        skin = self.grow(np.maximum(m["torso"], m["legs"]), 0.008)
        if self.male:
            legs_cut = [pk.stroke_mask(self.shape, self.leg_strokes(side, 0.018, 1.0))
                        * (1.0 - self.beyond(f"hip_{side}", f"knee_{side}", BOXER_LENGTH)) for side in SIDES]
            boxers = np.maximum.reduce(legs_cut + [self.grow(m["torso"], 0.012)]) * (1.0 - self.above_line(-0.34))
            band = boxers * self.above_line(-0.23)
            return [dict(name="boxers", mask=boxers, zone="torso", fitted=True, **cloth),
                    dict(name="waistband", mask=band, color=pal.accent, shadow=dark(pal.accent), zone="torso",
                         fitted=True)]
        depth = DEPTH["bust"]
        radius = self.plan.bust_radius * self.build.bust
        cups, straps = [], []
        for sign in (1.0, -1.0):
            cx, cy = self.plan.bust_center[0] * sign, self.plan.bust_center[1]
            corners = [self.chest_pt(cx + u * radius * sign, cy + v * radius, depth) for u, v in BRA_CUP]
            cups.append(self.at(pk.spline(np.array(corners), closed=True)))
            top = self.chest_pt(cx + BRA_CUP[2][0] * radius * 0.8 * sign, cy + BRA_CUP[2][1] * radius, depth)
            strap = np.array([top, self.chest_pt(BRA_STRAP_TOP[0] * sign, BRA_STRAP_TOP[1])])
            straps.append((pk.resample(self.at(strap), 12), self.px(0.016)))
        gore = self.chest_poly([(-0.04, self.plan.bust_center[1] + radius * 0.25),
                                (0.04, self.plan.bust_center[1] + radius * 0.25),
                                (0.03, self.plan.bust_center[1] + radius * 1.0),
                                (-0.03, self.plan.bust_center[1] + radius * 1.0)])
        under = self.plan.bust_center[1] + radius * BRA_BAND_TOP     # the band tucks under the cups
        band = self.chest_band(under, under + BRA_BAND_DEPTH)
        bra = np.maximum.reduce([pk.fill_mask(self.shape, cups), gore, band]) * skin
        bra = np.maximum(bra, pk.stroke_mask(self.shape, straps) * self.grow(m["torso"], 0.008))
        hips = self.build.hips
        depths = [0.0, 0.0, DEPTH["belly"], 0.0, 0.0, DEPTH["crotch"], DEPTH["crotch"], DEPTH["crotch"]]
        brief = pk.fill_mask(self.shape, self.at(pk.spline(np.array(
            [self.pelvis_pt(x * (hips if abs(x) > 0.5 else 1.0), y, d) for (x, y), d in zip(INNERWEAR_BRIEF, depths)]),
            closed=True))) * skin
        return [dict(name="brief", mask=brief, zone="torso", fitted=True, lace=True, **cloth),
                dict(name="bra", mask=bra, zone="torso", fitted=True, lace=True, **cloth)]

    def casual_masks(self, kind: str, shoes: list, cloth: dict, dark) -> list:
        """Crop tee with denim hot pants; hoodie with jeans."""
        pal, m = self.pal, self.masks
        lower = dict(color=pal.cloth2, shadow=dark(pal.cloth2))
        torso = m["torso"]
        if kind == "crop_hotpants":
            neckline = ((0.0, -0.030), (0.120, -0.090), (0.170, -0.160), (0.80, -0.120))
            tee = self.grow(torso, 0.016) * self.chest_cover(neckline) * self.above_line(CROP_HEM_Y)
            sleeves = [dict(name=f"sleeve_{side}", mask=self.sleeve_mask(side, 0.035, 1.0)
                            * (1.0 - self.beyond(f"shoulder_{side}", f"elbow_{side}", 0.42)), zone=f"arm_{side}",
                            **cloth) for side in SIDES]
            legs_cut = [pk.stroke_mask(self.shape, self.leg_strokes(side, 0.022, 1.0))
                        * (1.0 - self.beyond(f"hip_{side}", f"knee_{side}", HOTPANTS_LENGTH)) for side in SIDES]
            shorts = np.maximum.reduce(legs_cut + [self.grow(torso, 0.016)]) * (1.0 - self.above_line(HOTPANTS_WAIST_Y))
            return shoes + sleeves + [dict(name="hotpants", mask=shorts, zone="torso", fitted=True, denim=True, **lower),
                                      dict(name="tee", mask=tee, zone="torso", fitted=True, **cloth)]
        # hoodie_jeans
        hem = self.above_line(HOODIE_HEM_Y)
        body = self.grow(torso, 0.050) * self.chest_cover(((0.0, -0.040), (0.120, -0.110), (0.80, -0.120))) * hem
        hood = np.maximum(self.chest_poly(HOOD_LOBE), self.chest_poly(HOOD_LOBE, True)) * (1.0 - self.chest_cover(
            ((0.0, 0.080), (0.80, 0.080))))
        pants = [dict(name=f"pants_{side}", mask=pk.stroke_mask(self.shape, self.leg_strokes(side, 0.035, 1.97)),
                      zone=f"leg_{side}", **lower) for side in SIDES]
        hips = self.grow(torso, 0.03) * (1.0 - self.above_line(-0.40))
        rib = dict(color=pk.adjust(pal.cloth, value=0.90), shadow=pal.cloth_shadow)
        sleeves = []
        for side in SIDES:
            sleeve = self.sleeve_mask(side, 0.070, 1.94)
            cuff = sleeve * self.beyond(f"elbow_{side}", f"wrist_{side}", 1.0 - HOODIE_RIB * 2.0)
            sleeves += [dict(name=f"sleeve_{side}", mask=sleeve, zone=f"arm_{side}", **cloth),
                        dict(name=f"cuff_{side}", mask=cuff, zone=f"arm_{side}", fitted=True, **rib)]
        band = body * (1.0 - self.above_line(HOODIE_HEM_Y - HOODIE_RIB))
        return pants + shoes + sleeves + [
            dict(name="pants_hips", mask=hips, zone="torso", fitted=True, no_line=m["legs"], **lower),
            dict(name="hoodie", mask=body, zone="torso", pocket=HOODIE_POCKET, strings=True, **cloth),
            dict(name="hem_band", mask=band, zone="torso", fitted=True, no_line=body, **rib),
            dict(name="hood", mask=hood * self.grow(torso, 0.10), zone="torso", **cloth)]

    def lap_garments(self, garments: list) -> list:
        """Seated figure: a skirt lies over the thighs.

        The legs are drawn over the torso when seated, so the cloth on the
        lap is a garment of its own, painted after the legs."""
        skirts = [g for g in garments if g["name"] in SKIRT_GARMENTS]
        if self.pose.seat is None or not skirts:
            return garments
        skirt = skirts[0]
        thighs = [stroke for side in SIDES for stroke in self.leg_strokes(side, 0.03, LAP_COVER)]
        lap = self.bridge_rows(pk.stroke_mask(self.shape, thighs))
        if skirt["name"] != "dress":           # a narrow skirt has no spare cloth to hang below the seat
            skirt["mask"] = skirt["mask"] * self.above_line(self.pose.seat + 0.12)
            skirt.pop("folds", None)
        # No outline where the lap meets the rest of the skirt: it is one piece of cloth.
        return garments + [dict(name="lap", mask=lap, color=skirt["color"], shadow=skirt["shadow"], zone="lap",
                                no_line=skirt["mask"])]

    # -- light --------------------------------------------------------------
    def body_light(self, mask, radius: float, bumps: float = 0.0) -> np.ndarray:
        """Diffuse term of a body part; `bumps` (0-1) adds the bust to the torso.

        Each breast is a dome whose upper side eases into the chest: a bare
        hemisphere would read as a ball stuck on the ribcage."""
        height = lt.inflate(mask, self.px(radius))
        if bumps > 0 and self.build.bust > 0:
            yy, xx = np.mgrid[0:self.shape[0], 0:self.shape[1]].astype(np.float32)
            radius_px = self.px(self.plan.bust_radius * self.build.bust)
            bust = np.zeros(self.shape, np.float32)
            for center in self.bust_centers():
                cx, cy = self.at(center)
                dome = np.sqrt(np.clip(radius_px ** 2 - ((xx - cx) / self.plan.bust_aspect) ** 2 - (yy - cy) ** 2,
                                       0.0, None))
                slope_y = cy - radius_px * 0.70
                slope = radius_px * self.plan.bust_slope * np.exp(-(((xx - cx) / (radius_px * 0.85)) ** 2
                                                    + ((yy - slope_y) / (radius_px * 0.75)) ** 2))
                # Overlapping domes (turned torso) merge into one surface; adding them would raise a ridge.
                bust = np.maximum(bust, dome * self.plan.bust_dome + slope)
            height = height + bust * bumps
            normals = lt.normals_from_height(pk.blur(height, self.px(0.012)))
            # Side light draws a claw of shadow up the chest gap. A steeper light on the bust
            # keeps the shadow underneath, where it describes the volume.
            steep = self.light * np.array([BUST_SIDE_LIGHT, 1.0, 1.0], np.float32)
            zone = pk.blur((bust > 0).astype(np.float32), self.px(0.03))
            return lt.lambert(normals, self.light) * (1.0 - zone) + lt.lambert(normals, steep / np.linalg.norm(steep)) * zone
        return lt.lambert(lt.normals_from_height(pk.blur(height, self.px(0.012))), self.light)

    def joint_zone(self, joint: str, radius: float) -> np.ndarray:
        """Soft disc around a joint, used to hide the seam between two parts."""
        return pk.smoothstep(0.0, 0.35, pk.radial_ramp(self.shape, self.at(self.joints[joint]), self.px(radius)))

    def trunk_light(self) -> np.ndarray:
        """Diffuse term of torso and limbs fused into one form, computed once.

        Each part lit from its own outline shows a shaded rim where it meets
        the torso (a doll joint). Near the joints the fused light is used."""
        if not hasattr(self, "_trunk_light"):
            m = self.masks
            fused = np.maximum.reduce([m["torso"], m["legs"]]
                                      + [m[f"arm_{side}"] for side in SIDES if side not in self.pose.front])
            self._trunk_light = self.body_light(fused, 0.20, bumps=1.0)
        return self._trunk_light

    def blend_to_trunk(self, lit, joint: str, radius: float) -> np.ndarray:
        zone = self.joint_zone(joint, radius)
        return lit * (1.0 - zone) + self.trunk_light() * zone

    # -- painting -----------------------------------------------------------
    def paint_surface(self, layer, mask, color, shadow, lit, casters=(), threshold: float = 0.24,
                      no_line=None, sheen: bool = False):
        """Fill, shade and outline one surface. `no_line` (mask) suppresses the
        outline where this part grows out of another one (shoulder, hip).
        `sheen` adds a soft highlight where the surface faces the light."""
        st = self.style
        layer.paint(mask, color)
        shade = self.shadow_of(lit, threshold) * mask
        for caster, distance in casters:
            shade = np.maximum(shade, self.cast(caster, mask, distance, down_bias=0.3))
        layer.paint(shade, shadow, st.shadow_strength)
        # A soft second tone rounds the form between light and shadow.
        turn = (1.0 - pk.smoothstep(-0.15, 0.65, lit)) * mask
        layer.paint(turn, shadow, 0.28 * st.airbrush)
        if sheen:
            glow = pk.smoothstep(0.80, 0.99, lit) * mask * (1.0 - shade)
            layer.paint(glow, pk.mix(color, "#ffffff", 0.55), 0.38 * st.airbrush)
        if st.line_width > 0:
            band = lt.outline_mask(mask, max(self.px(st.line_width), 1.0), self.light, st.line_variation)
            if no_line is not None:
                band = band * (1.0 - no_line)
            layer.paint(band, self.line_color(color), st.line_opacity)

    def paint_garments(self, layer, zone: str, casters=()):
        for garment in self.garments:
            if garment["zone"] != zone:
                continue
            wide = zone == "torso"
            # Cloth softens what is under it, so the bust shows at reduced strength.
            # A hanging coat stands off the body: no bust or buttocks show through it.
            bumps = 0.0 if garment.get("drape") else (0.5 if wide else 0.0)
            lit = self.body_light(garment["mask"], 0.22 if wide else 0.10, bumps=bumps)
            if garment.get("fitted"):          # skin-tight: it has no form of its own, only the body's
                lit = self.trunk_light()
            self.paint_surface(layer, garment["mask"], garment["color"], garment["shadow"], lit, casters,
                               no_line=garment.get("no_line"), sheen=bool(garment.get("fitted") or garment.get("gloss")))
            if "folds" in garment:
                self.paint_skirt_folds(layer, garment)
            if garment.get("seam"):
                self.paint_front_seam(layer, garment)
            if "buttons" in garment:
                self.paint_buttons(layer, garment)
            if garment.get("lace"):
                self.paint_lace(layer, garment)
            if garment.get("denim"):
                self.paint_denim(layer, garment)
            if "pocket" in garment:
                self.paint_pocket(layer, garment)
            if garment.get("strings"):
                self.paint_strings(layer, garment)
            for detail in garment.get("details", ()):
                detail(self, layer, garment)

    def paint_skirt_folds(self, layer, garment):
        """Fold shadows that widen toward the hem, where hanging cloth gathers."""
        hem_y, hem_half, count = garment["folds"]
        strokes = []
        for x in np.linspace(-0.82, 0.82, count):
            x = x + self.rng.uniform(-0.06, 0.06)
            path = np.array([[x * 0.42, 0.10], [x * hem_half * 0.80, hem_y * 0.55], [x * hem_half, hem_y + 0.02]])
            path = pk.resample(pk.spline(self.at(path + self.joints["pelvis"])), 24)
            strokes.append((path, pk.taper(len(path), self.px(0.055), head=0.0, tail=1.0, peak=1.0)))
        folds = pk.blur(pk.stroke_mask(self.shape, strokes), self.px(0.004 + self.style.shadow_softness * 0.04))
        layer.paint(folds * garment["mask"], garment["shadow"], 0.55 * self.style.shadow_strength)

    def paint_front_seam(self, layer, garment):
        """Closing edge of a jacket from the V down to the hem, with one button."""
        line = [self.chest_pt(0.0, 0.80, DEPTH["chest"]), self.pelvis_pt(0.010, -0.20, DEPTH["belly"]),
                self.pelvis_pt(0.025, 0.36, DEPTH["crotch"])]
        self.cloth_ink(layer, garment, line)
        button = self.at(self.chest_pt(0.035, 0.90, DEPTH["chest"]))
        dot = pk.fill_mask(self.shape, pk.ellipse(button[0], button[1], self.px(0.022), self.px(0.022)))
        layer.paint(dot * garment["mask"], pk.adjust(garment["color"], value=0.6), 0.9)

    def paint_buttons(self, layer, garment):
        top, bottom = garment["buttons"]
        self.cloth_ink(layer, garment, [self.chest_pt(0.0, top, DEPTH["chest"]),
                                        self.pelvis_pt(0.0, -0.32, DEPTH["belly"])])
        for y in np.linspace(top + 0.12, top + 0.12 + bottom, 4):
            center = self.at(self.chest_pt(0.022, y, DEPTH["chest"]))
            dot = pk.fill_mask(self.shape, pk.ellipse(center[0], center[1], self.px(0.014), self.px(0.014)))
            layer.paint(dot * garment["mask"], pk.adjust(garment["color"], value=0.82), 0.9)

    def paint_lace(self, layer, garment):
        """Lace border: a dotted mesh along the inside of the edge, lighter than the cloth,
        and a fainter mesh over the whole piece."""
        mask = garment["mask"]
        inside = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 3)
        trim = (inside > 0) & (inside < self.px(LACE_TRIM))
        yy, xx = np.mgrid[0:self.shape[0], 0:self.shape[1]].astype(np.float32)
        step = max(self.px(LACE_DOT), 3.0)
        cell_x, cell_y = (xx % step) / step - 0.5, ((yy + (xx // step % 2) * step / 2) % step) / step - 0.5
        dots = (cell_x ** 2 + cell_y ** 2 < 0.09).astype(np.float32)
        light = pk.mix(garment["color"], "#ffffff", 0.45)
        layer.paint(dots * trim * mask, light, 0.75)
        layer.paint(dots * mask * (1.0 - trim), garment["shadow"], 0.22)

    def paint_denim(self, layer, garment):
        """Denim: fly seam, pocket curves and a frayed hem."""
        for sign in (1.0, -1.0):
            pocket = [self.pelvis_pt(0.20 * sign, HOTPANTS_WAIST_Y + 0.01, DEPTH["belly"]),
                      self.pelvis_pt(0.32 * sign, -0.12), self.pelvis_pt(0.50 * sign, -0.14)]
            self.cloth_ink(layer, garment, pocket)
        self.cloth_ink(layer, garment, [self.pelvis_pt(0.02, HOTPANTS_WAIST_Y + 0.02, DEPTH["belly"]),
                                        self.pelvis_pt(0.03, 0.10, DEPTH["crotch"]),
                                        self.pelvis_pt(0.0, 0.20, DEPTH["crotch"])])
        ticks = []
        for side in SIDES:
            hip, knee = self.joints[f"hip_{side}"], self.joints[f"knee_{side}"]
            hem = hip + (knee - hip) * HOTPANTS_LENGTH
            axis = (knee - hip) / (np.linalg.norm(knee - hip) or 1.0)
            across = np.array([-axis[1], axis[0]], np.float32)
            for t in np.linspace(-0.30, 0.30, 9):
                start = hem + across * t - axis * 0.02
                ticks.append((pk.resample(self.at(np.array([start, start + axis * 0.05])), 4), self.px(0.008)))
        layer.paint(pk.stroke_mask(self.shape, ticks) * self.grow(garment["mask"], 0.02),
                    pk.mix(garment["color"], "#ffffff", 0.5), 0.8)

    def paint_pocket(self, layer, garment):
        pts = [self.pelvis_pt(x, y, DEPTH["belly"]) for x, y in garment["pocket"]]
        self.cloth_ink(layer, garment, [pts[3], pts[0], pts[1], pts[2]])
        self.cloth_ink(layer, garment, [pts[2], pts[3]])

    def paint_strings(self, layer, garment):
        """Hoodie drawstrings hanging from the neckline, with tipped ends."""
        strokes, tips = [], []
        for sign in (1.0, -1.0):
            line = np.array([self.chest_pt(0.065 * sign, -0.050, DEPTH["chest"]),
                             self.chest_pt(0.075 * sign, 0.200, DEPTH["chest"]),
                             self.chest_pt(0.085 * sign, 0.420, DEPTH["chest"])])
            path = pk.resample(self.at(pk.spline(line)), 16)
            strokes.append((path, self.px(0.012)))
            tips.append((pk.resample(self.at(np.array([line[-1], line[-1] + [0.0, 0.06]])), 4), self.px(0.018)))
        lace = pk.stroke_mask(self.shape, strokes + tips)
        layer.paint(lace, pk.mix(garment["color"], "#ffffff", 0.7), 0.95)
        layer.paint(lt.outline_mask(lace, 1.0, self.light, 0.0), self.line_color(garment["color"]), 0.5)

    def cloth_ink(self, layer, garment, points):
        path = pk.resample(self.at(pk.spline(np.array(points))), 24)
        widths = pk.taper(len(path), self.px(max(self.style.line_width, 0.0022)), head=0.0, tail=0.0)
        layer.paint(pk.stroke_mask(self.shape, (path, widths)) * garment["mask"], self.line_color(garment["color"]),
                    self.style.line_opacity if self.style.line_width > 0 else 0.5)

    def skin_ink(self, layer, clip, points, opacity: float, **taper_kw):
        """Tapered skin-tone line through head-unit points (creases, bony landmarks)."""
        tone = pk.adjust(self.pal.skin_shadow, value=0.82, sat=1.2)
        path = pk.resample(self.at(pk.spline(np.array(points))), 24)
        widths = pk.taper(len(path), self.px(max(self.style.line_width, 0.0022)), **taper_kw)
        layer.paint(pk.stroke_mask(self.shape, (path, widths)) * clip, tone, opacity)

    def paint_arm(self, layer, side: str):
        pal, st = self.pal, self.style
        mask = self.masks[f"arm_{side}"]
        lit = self.body_light(mask, 0.10)
        if side not in self.pose.front:
            lit = self.blend_to_trunk(lit, f"shoulder_{side}", 0.45)
        # No line where the shoulder merges into the torso: a full ring there reads as a doll joint.
        seam = self.masks["torso"] * self.joint_zone(f"shoulder_{side}", 0.42)
        self.paint_surface(layer, mask, pal.skin, pal.skin_shadow, lit, no_line=seam, sheen=True)
        self.hands[side].paint(layer, pal.skin, pal.skin_shadow, self.line_color(pal.skin), self.light,
                               softness=st.shadow_softness, line_width=st.line_width / self.plan.hand_length,
                               line_opacity=st.line_opacity, strength=st.shadow_strength)
        self.paint_garments(layer, f"arm_{side}")

    def paint_leg(self, layer, side: str):
        pal, j, sign = self.pal, self.joints, SIDES[side]
        mask = self.masks[f"leg_{side}"]
        lit = self.blend_to_trunk(self.body_light(mask, 0.15), f"hip_{side}", 0.75)
        # A skirt or long top throws its hem shadow onto the legs.
        hems = [] if self.pose.legs_front else [(g["mask"], 0.07) for g in self.garments if g["zone"] == "torso"]
        self.paint_surface(layer, mask, pal.skin, pal.skin_shadow, lit, hems, sheen=True)
        knee = j[f"knee_{side}"]
        self.skin_ink(layer, mask, [knee + [-0.075, 0.015], knee + [0.0, 0.060], knee + [0.075, 0.015]], 0.7,
                      head=0.0, tail=0.0)
        self.skin_ink(layer, mask, [knee + [0.085 * sign, -0.13], knee + [0.100 * sign, -0.02]], 0.45,
                      head=0.0, tail=0.0)
        # The shin bone runs just under the skin and catches a long highlight.
        shin_mid = knee + (j[f"ankle_{side}"] - knee) * 0.45 + [0.03 * self.light_side, 0.0]
        shin_light = pk.radial_ramp(self.shape, self.at(shin_mid), self.px(0.30), aspect=4.0) * mask
        layer.paint(shin_light, pk.mix(pal.skin, "#ffffff", 0.5), 0.22 * self.style.airbrush)
        self.paint_garments(layer, f"leg_{side}")

    def paint_torso(self, layer):
        pal, st, m = self.pal, self.style, self.masks
        torso = m["torso"]
        lit = self.trunk_light()
        middle_arms = [m[f"arm_{side}"] for side in SIDES if side not in self.pose.behind]
        casters = [(m["face"], 0.115), (m["hair_sides"], 0.035)] + [(arm, 0.045) for arm in middle_arms]
        # The pelvis flows into the thighs: no outline across the legs.
        self.paint_surface(layer, torso, pal.skin, pal.skin_shadow, lit, casters, no_line=m["legs"], sheen=True)
        deep = lt.occlusion(m["face"], torso, self.px(0.03)) * self.cast(m["face"], torso, 0.115, 0.6)
        layer.paint(deep, pk.adjust(pal.skin_shadow, value=0.86, sat=1.15), 0.55 * st.airbrush)
        self.paint_torso_details(layer, torso)
        self.paint_garments(layer, "torso", casters)

    def paint_torso_details(self, layer, torso):
        """Collarbones, bust, navel and lower pelvis lines: what a bare torso needs to read as a body."""
        if self.male:
            self.paint_male_torso(layer, torso)
            return
        chest, belly, crotch = DEPTH["chest"], DEPTH["belly"], DEPTH["crotch"]
        hips = self.build.hips
        for sign in (1.0, -1.0):
            self.skin_ink(layer, torso, [self.chest_pt(0.050 * sign, -0.130, chest), self.chest_pt(0.19 * sign, -0.120, chest),
                                         self.chest_pt(0.36 * sign, -0.085)], 0.75, head=0.1, tail=0.0, peak=0.25)
            self.skin_ink(layer, torso, [self.pelvis_pt(0.430 * hips * sign, 0.060), self.pelvis_pt(0.225 * sign, 0.290, crotch),
                                         self.pelvis_pt(0.038 * sign, self.plan.crotch_y - 0.005, crotch)], 0.6,
                          head=0.0, tail=0.6, peak=0.8)
        if self.build.bust > 0:
            radius = self.plan.bust_radius * self.build.bust
            for (cx, cy), sign in zip(self.bust_centers(), (1.0, -1.0)):
                under = [[cx - radius * 0.80 * sign, cy + radius * 0.58], [cx, cy + radius * 0.99],
                         [cx + radius * 0.84 * sign, cy + radius * 0.50]]
                self.skin_ink(layer, torso, under, 0.6, head=0.0, tail=0.0)
        navel = [self.pelvis_pt(0.0, -0.560, belly), self.pelvis_pt(0.004, -0.500, belly)]
        self.skin_ink(layer, torso, navel, 0.85, head=0.3, tail=0.0, peak=0.3)
        self.paint_torso_modeling(layer, torso)

    def paint_torso_modeling(self, layer, torso):
        """Soft tones for the planes of the trunk (airbrush strength of the style)."""
        pal, air = self.pal, self.style.airbrush
        chest, belly = DEPTH["chest"], DEPTH["belly"]
        light = pk.mix(pal.skin, "#ffffff", 0.55)

        def soft(center, radius, aspect, color, opacity):
            spot = pk.radial_ramp(self.shape, self.at(center), self.px(radius), aspect) * torso
            layer.paint(spot, color, opacity * air)

        soft(self.chest_pt(0.0, 0.930, belly), 0.085, 4.6, pal.skin_shadow, 0.30)     # furrow down the abdomen
        soft(self.chest_pt(0.0, 0.520, chest), 0.060, 2.6, pal.skin_shadow, 0.34)     # chest gap
        soft(self.chest_pt(0.0, 0.100, chest), 0.150, 0.8, light, 0.22)               # upper chest catches light
        for sign in (1.0, -1.0):
            soft(self.pelvis_pt(0.365 * self.build.hips * sign, -0.330), 0.090, 1.3, light, 0.26)   # hip bone
            soft(self.chest_pt(0.300 * sign, 0.830), 0.100, 2.0, pal.skin_shadow, 0.22)             # under the ribs
        for cx, cy in self.bust_centers():
            radius = self.plan.bust_radius * self.build.bust
            soft([cx + radius * 0.30 * self.light_side, cy - radius * 0.35], radius * 0.75, 1.0, light, 0.30)
        soft(self.pelvis_pt(0.0, -0.160, belly), 0.210, 0.75, light, 0.18)            # lower belly

    def paint_male_torso(self, layer, torso):
        """Collarbones, chest muscles, abdominal plates, iliac lines and navel.

        Muscle groups are soft tone patches; their strength follows Build.muscle."""
        pal, air = self.pal, self.style.airbrush
        chest, belly = DEPTH["chest"], DEPTH["belly"]
        strength = float(np.clip(self.build.muscle, 0.0, 1.6))
        light = pk.mix(pal.skin, "#ffffff", 0.55)
        tone = pk.adjust(pal.skin_shadow, value=0.92, sat=1.1)

        def soft(center, radius, aspect, color, opacity):
            spot = pk.radial_ramp(self.shape, self.at(center), self.px(radius), aspect) * torso
            layer.paint(spot, color, opacity * air * strength)

        cx, cy = self.plan.bust_center
        radius = self.plan.bust_radius * self.build.bust
        for sign in (1.0, -1.0):
            self.skin_ink(layer, torso, [self.chest_pt(0.050 * sign, -0.130, chest), self.chest_pt(0.24 * sign, -0.115, chest),
                                         self.chest_pt(0.50 * sign, -0.060)], 0.75, head=0.1, tail=0.0, peak=0.25)
            # Lower edge of the chest muscle, from the sternum out toward the armpit.
            self.skin_ink(layer, torso, [self.chest_pt(0.030 * sign, cy + radius * 0.90, chest),
                                         self.chest_pt((cx + radius * 0.3) * sign, cy + radius * 1.00, chest),
                                         self.chest_pt((cx + radius * 1.10) * sign, cy + radius * 0.55)], 0.50 * strength,
                          head=0.2, tail=0.6, peak=0.4)
            soft(self.chest_pt((cx + 0.04) * sign, cy + radius * 1.05, chest), radius * 1.2, 0.16, tone, 0.40)
            chest_mark = self.at(self.chest_pt((cx + 0.02) * sign, cy + radius * 0.55, chest))
            dot = pk.fill_mask(self.shape, pk.ellipse(chest_mark[0], chest_mark[1], self.px(0.020), self.px(0.017)))
            layer.paint(pk.blur(dot, self.px(0.004)) * torso, pk.mix(pal.skin_shadow, pal.lip, 0.35), 0.55)
            for row, y in enumerate((0.86, 1.04)):
                # Abdominal plates: shade between the plates, light on them.
                soft(self.chest_pt(0.105 * sign, y, belly), 0.085, 0.45, tone, 0.30)
                soft(self.chest_pt(0.115 * sign, y - 0.09, belly), 0.075, 0.9, light, 0.22)
            soft(self.pelvis_pt(0.115 * sign, -0.52, belly), 0.075, 0.9, light, 0.18)
            # Iliac furrow (the V from the hip bone toward the lower pelvis).
            self.skin_ink(layer, torso, [self.pelvis_pt(0.385 * sign, -0.330), self.pelvis_pt(0.260 * sign, -0.080, belly),
                                         self.pelvis_pt(0.150 * sign, 0.120, DEPTH["crotch"])], 0.45,
                          head=0.3, tail=0.9, peak=0.4)
            soft(self.pelvis_pt(0.40 * sign, -0.30), 0.10, 1.3, light, 0.24)
            soft(self.chest_pt(0.44 * sign, 0.80), 0.10, 3.0, tone, 0.30)        # side of the ribcage
        soft(self.chest_pt(0.0, 0.92, belly), 0.050, 6.0, tone, 0.35)               # line down the abdomen
        soft(self.chest_pt(0.10 * self.light_side, cy - radius * 0.2, chest), 0.42, 0.45, light, 0.22)   # chest plate
        navel = [self.pelvis_pt(0.0, -0.560, belly), self.pelvis_pt(0.004, -0.505, belly)]
        self.skin_ink(layer, torso, navel, 0.85, head=0.3, tail=0.0, peak=0.3)

    def paint_seat(self):
        """Furniture behind the figure: the stool here, other pieces in furniture.py."""
        if self.furniture != "stool":
            furniture.paint(self, self.furniture, self.furniture_color)
            return
        if self.pose.seat is None:
            raise ValueError("furniture 'stool' needs a seated pose (a pose with 'seat')")
        layer = self.cv.layer("seat")
        base, top = self.joints["pelvis"], self.pose.seat
        floor = max(self.joints["ankle_left"][1], self.joints["ankle_right"][1]) + 0.36
        legs = [(pk.resample(self.at(np.array([base + [x, top + 0.10], base + [x * 1.12, floor]])), 8), self.px(0.085))
                for x in (-0.62, 0.62)]
        bar = (pk.resample(self.at(np.array([base + [-0.66, top + 0.95], base + [0.66, top + 0.95]])), 8), self.px(0.06))
        frame = pk.stroke_mask(self.shape, legs + [bar])
        lt.paint_form(layer, frame, SEAT_SHADOW, pk.adjust(SEAT_SHADOW, value=0.7), self.light, self.px(0.03), softness=0.1)
        slab = pk.fill_mask(self.shape, self.at(pk.spline(np.array(
            [base + [-0.80, top], base + [0.80, top], base + [0.84, top + 0.08], base + [0.80, top + 0.16],
             base + [-0.80, top + 0.16], base + [-0.84, top + 0.08]]), closed=True)))
        lt.paint_form(layer, slab, SEAT_COLOR, SEAT_SHADOW, self.light, self.px(0.06), softness=0.1)
        self.outline(layer, np.maximum(slab, frame), SEAT_COLOR)

    def paint_body(self):
        layer = self.cv.layer("figure")
        pose = self.pose
        other = "right" if pose.first_leg == "left" else "left"
        for side in pose.behind:
            self.paint_arm(layer, side)
        if not pose.legs_front:
            for side in (pose.first_leg, other):
                self.paint_leg(layer, side)
        self.paint_torso(layer)
        if pose.legs_front:
            for side in (pose.first_leg, other):
                self.paint_leg(layer, side)
            self.paint_garments(layer, "lap")
        for side in SIDES:
            if side not in pose.behind and side not in pose.front:
                self.paint_arm(layer, side)

    def paint_outfit(self):
        """Garments are painted with the body parts they sit on (see paint_body)."""

    def paint_front_arms(self):
        if not self.pose.front:
            return
        layer = self.cv.layer("figure_front")
        for side in self.pose.front:
            self.paint_arm(layer, side)

    def paint_fx(self):
        super().paint_fx()
        props.paint(self)         # held props go over the rim light: a lit tip is its own light

    def paint_ground_shadow(self, layer, opacity: float = 0.35):
        """Soft contact shadow under the feet; without it a figure floats."""
        j = self.joints
        feet = np.array([j["ankle_left"], j["ankle_right"]])
        center = self.at(feet.mean(axis=0) + [0.12 * -self.light_side, 0.38])
        span = self.px(abs(feet[1, 0] - feet[0, 0]) / 2 + 0.60)
        layer.paint(pk.radial_ramp(self.shape, center, span, aspect=0.16), "#3a3550", float(opacity))

    def skeleton_lines(self) -> list:
        """Pixel paths of the bones, for the construction guide."""
        j = self.joints
        chains = [("pelvis", "waist", "chest", "neck", "skull", "eyes")]
        for side in SIDES:
            chains.append((f"shoulder_{side}", f"elbow_{side}", f"wrist_{side}"))
            chains.append((f"hip_{side}", f"knee_{side}", f"ankle_{side}"))
        chains += [("shoulder_left", "shoulder_right"), ("hip_left", "hip_right")]
        return [self.at(np.array([j[name] for name in chain])) for chain in chains]

    def render(self) -> "Figure":
        self.build_masks()
        self.paint_hair_back()
        self.paint_seat()
        self.paint_body()
        self.paint_face()
        self.paint_hair_front()
        self.paint_front_arms()
        self.paint_fx()
        return self
