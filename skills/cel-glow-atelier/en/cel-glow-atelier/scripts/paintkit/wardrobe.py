"""paintkit.wardrobe: the outfits added in v9 (outerwear, sportswear, summer wear, knitwear).

Every outfit is built from the rig's own mask helpers (chest_cover, beyond, leg and
arm strokes), so the same few shapes serve both genders: a jacket cut from the torso
outline fits a broad male chest and a female bust alike. One builder per outfit and
view keeps the whole outfit in one place.

Garment dicts follow figure.Figure.garment_masks(); the extra key `details` holds
painters called as detail(figure, layer, garment) after the garment is shaded.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import core as pk
from .body import DEPTH, SIDES

OUTFITS = ("open_shirt_shorts", "tank_shorts", "denim_jacket_chinos", "leather_jacket_jeans", "coat_turtleneck",
           "knit_dress", "tank_jeans")
OUTFIT_GENDER = {"open_shirt_shorts": "male", "knit_dress": "female", "tank_jeans": "female"}
# Garments a hand can go into (see figure.POCKET_GARMENTS), and skirts that lie over a seated lap.
POCKET_GARMENTS = ("shorts", "coat")
SKIRT_GARMENTS = ("knit_dress",)
# Outer layer colors when the palette leaves `outer` empty: the material's own color.
OUTER_COLORS = {"denim_jacket_chinos": "#5f7fa8", "leather_jacket_jeans": "#34303a", "coat_turtleneck": "#b08860"}

# -- shapes (chest frame: x across, y down from the chest joint; pelvis frame for hems) --
CREW_NECK = ((0.0, -0.050), (0.120, -0.100), (0.170, -0.160), (0.80, -0.120))
COLLAR_LINE = ((0.0, -0.160), (0.170, -0.180), (0.80, -0.120))   # top edge of a jacket around the neck
# Camp collar: lies flat and open along the V of the shirt.
CAMP_NECK = ((0.0, 0.300), (0.110, 0.040), (0.165, -0.130), (0.80, -0.100))
CAMP_COLLAR = ((0.095, -0.175), (0.180, -0.150), (0.310, -0.050), (0.215, 0.090), (0.070, 0.290), (0.110, 0.040))
SHIRT_HEM_Y = 0.12                # untucked shirt hem below the pelvis center
SHORTS_LENGTH = 0.62              # share of the thigh casual shorts cover
TRAINING_LENGTH = 0.45
SHORTS_WAIST_Y = -0.34
WAISTBAND = 0.09                  # elastic band height of training shorts
STRIPE_OFFSET = 0.25              # side stripe distance from the thigh axis (head units)
# Sleeveless top: scoop neck and armhole cut, x in shoulder half-widths (fits any shoulder width;
# a neck cut in head units read as a narrow keyhole on broad male shoulders).
TANK_NECK = ((0.0, 0.250), (0.153, 0.225), (0.255, 0.130), (0.306, -0.020), (0.337, -0.110), (1.63, -0.100))
TANK_ARMHOLE = ((0.42, -0.40), (3.0, -0.40), (3.0, 0.80), (0.82, 0.74), (0.60, 0.46), (0.46, 0.12))
SLIM_ARMHOLE = ((0.38, -0.40), (3.0, -0.40), (3.0, 0.62), (0.84, 0.56), (0.58, 0.34), (0.42, 0.08))
TANK_HEM_Y = 0.06
FITTED_TANK_HEM_Y = -0.04
# Open jackets: the gap between the two fronts, from the collar down past the hem.
DENIM_OPENING = ((-0.100, -0.200), (0.100, -0.200), (0.170, 0.600), (0.190, 3.0), (-0.190, 3.0), (-0.170, 0.600))
DENIM_HEM_Y = -0.18
DENIM_BAND = 0.10                 # waistband height of the denim jacket
DENIM_COLLAR = ((0.090, -0.190), (0.200, -0.170), (0.360, -0.040), (0.300, 0.060), (0.130, 0.200), (0.110, 0.020))
DENIM_FLAP = ((0.160, 0.420), (0.360, 0.420), (0.350, 0.540), (0.260, 0.580), (0.170, 0.540))
LEATHER_OPENING = ((-0.100, -0.200), (0.100, -0.200), (0.240, 0.700), (0.220, 3.0), (-0.220, 3.0), (-0.240, 0.700))
LEATHER_HEM_Y = -0.26
LEATHER_LAPEL = ((0.100, -0.200), (0.240, -0.120), (0.460, 0.120), (0.360, 0.230), (0.400, 0.320), (0.240, 0.700),
                 (0.150, 0.300))
ZIP_COLOR = "#c9c6c0"
LEATHER_LAPEL_LIFT = 1.55         # lapels catch more light than the jacket body: dark leather needs a big lift
# Long coat: lapels to the waist, then the fronts hang open to the hem below the knee.
COAT_OPENING = ((-0.100, -0.180), (0.100, -0.180), (0.180, 0.900), (0.140, 1.300), (0.130, 6.0), (-0.130, 6.0),
                (-0.140, 1.300), (-0.180, 0.900))
COAT_LAPEL = ((0.100, -0.180), (0.270, -0.100), (0.440, 0.180), (0.360, 0.270), (0.420, 0.380), (0.180, 0.900),
              (0.120, 0.400))
COAT_BELOW_KNEE = 0.18            # coat hem below the knees (head units)
COAT_SKIRT_TOP = -0.30            # the coat skirt hangs from this level (pelvis frame)
COAT_COVER_DEPTH = 8.0            # chest_cover reach below the chest: past any coat hem
COAT_LAP_COVER = 0.90             # share of the thigh the coat fronts cover on a seated figure
LAP_SEAT_MARGIN = 0.12            # the coat body ends this far below the seat line
COAT_POCKET = ((0.30, 0.10), (0.56, 0.10))    # pelvis frame, right pocket flap ends
TURTLE_NECK = ((0.0, -0.360), (0.110, -0.360), (0.150, -0.200), (0.80, -0.100))
TURTLE_FOLDS = (-0.300, -0.205)   # rolled collar fold lines (chest y)
TUCKED_HEM_Y = -0.30
# Knit dress: crew neck, long sleeves, hem above the knee.
KNIT_NECK = ((0.0, -0.090), (0.120, -0.130), (0.170, -0.170), (0.80, -0.120))
KNIT_HEM_Y = 1.30
KNIT_RIB_COUNT = 9
KNIT_CUFF = 0.12


def dark(color):
    return pk.adjust(color, value=0.66, sat=1.15)


def colors(color) -> dict:
    return dict(color=color, shadow=dark(color))


def outer_color(fig) -> str:
    return fig.pal.outer or OUTER_COLORS[fig.fig_outfit]


def shoulder_half(fig) -> float:
    """Half the shoulder width in the chest frame: armholes scale with it."""
    return float(abs(fig.joints["shoulder_right"][0] - fig.joints["chest"][0])) / max(fig.turn_cos, 0.5)


def mirrored(fig, points) -> np.ndarray:
    return np.maximum(fig.chest_poly(points), fig.chest_poly(points, True))


# -- front view: shared pieces --------------------------------------------------
def sleeves(fig, extra: float, upto: float, paint: dict, cuff: float = 0.0) -> list:
    """Sleeves to `upto` (1 = elbow, 2 = wrist; below 1 a short sleeve cut square), with an
    optional cuff band of `cuff` forearm shares at the end."""
    out = []
    for side in SIDES:
        if upto < 1.0:
            mask = fig.sleeve_mask(side, extra, 1.0) * (1.0 - fig.beyond(f"shoulder_{side}", f"elbow_{side}", upto))
        else:
            mask = fig.sleeve_mask(side, extra, upto)
        out.append(dict(name=f"sleeve_{side}", mask=mask, zone=f"arm_{side}", **paint))
        if cuff > 0:
            band = mask * fig.beyond(f"elbow_{side}", f"wrist_{side}", upto - 1.0 - cuff)
            out.append(dict(name=f"cuff_{side}", mask=band, zone=f"arm_{side}", fitted=True,
                            color=pk.adjust(paint["color"], value=0.92), shadow=paint["shadow"]))
    return out


def trousers(fig, straight: bool, paint: dict, waist_y: float = -0.34) -> tuple:
    """([left leg, right leg], hips): straight legs (slacks, chinos) or legs that follow the body (jeans).
    The legs go first in a garment list, the hips with the torso garments."""
    m = fig.masks
    if straight:
        legs = [pk.stroke_mask(fig.shape, fig.trouser_strokes(side, 0.02)) for side in SIDES]
    else:
        legs = [pk.stroke_mask(fig.shape, fig.leg_strokes(side, 0.035, 1.97)) for side in SIDES]
    hips = fig.grow(m["torso"], 0.03) * (1.0 - fig.above_line(waist_y))
    return ([dict(name=f"pants_{side}", mask=leg, zone=f"leg_{side}", **paint) for side, leg in zip(SIDES, legs)],
            dict(name="pants_hips", mask=hips, zone="torso", fitted=True, no_line=m["legs"], **paint))


def shorts(fig, length: float, extra: float, paint: dict, details=(), leg_details=()) -> tuple:
    """([left leg, right leg], seat): leg pieces in the leg zones, the seat in the torso zone.
    A seated figure's legs are painted over the torso, so legs cut in the torso zone would
    vanish under bare thighs."""
    m = fig.masks
    legs = [dict(name=f"shorts_{side}", mask=pk.stroke_mask(fig.shape, fig.leg_strokes(side, extra, 1.0))
                 * (1.0 - fig.beyond(f"hip_{side}", f"knee_{side}", length)), zone=f"leg_{side}",
                 details=leg_details, **paint)
            for side in SIDES]
    seat = np.maximum.reduce([g["mask"] for g in legs] + [fig.grow(m["torso"], 0.03)])
    seat = seat * (1.0 - fig.above_line(SHORTS_WAIST_Y))
    return legs, dict(name="shorts", mask=seat, zone="torso", no_line=m["legs"], details=details, **paint)


def tank_mask(fig, armhole, hem_y: float, neck=TANK_NECK) -> np.ndarray:
    scale = shoulder_half(fig)
    cut = mirrored(fig, [(x * scale, y) for x, y in armhole])
    neckline = [(x * scale, y) for x, y in neck]
    return fig.grow(fig.masks["torso"], 0.016) * fig.chest_cover(neckline) * (1.0 - cut) * fig.above_line(hem_y)


def coat_skirt(fig, hem_y: float) -> np.ndarray:
    """Coat below the waist: cloth hangs over the widest points of hips and legs, so the
    outline is their convex hull (no step where the hips meet the thighs)."""
    below_waist = 1.0 - fig.above_line(COAT_SKIRT_TOP)
    region = np.maximum(fig.grow(fig.masks["legs"], 0.08) * fig.above_line(hem_y),
                        fig.grow(fig.masks["torso"], 0.065)) * below_waist
    ys, xs = np.nonzero(region > 0.5)
    if len(xs) < 3:
        return region
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))[:, 0].astype(np.float32)
    return pk.fill_mask(fig.shape, hull) * fig.above_line(hem_y) * below_waist


def open_jacket(fig, opening, hem_y: float, grow: float) -> tuple:
    """(jacket, opening) masks: the torso grown by `grow` down to the hem, minus the gap
    between the open fronts."""
    gap = fig.chest_poly(opening)
    body = fig.grow(fig.masks["torso"], grow) * fig.above_line(hem_y) * fig.chest_cover(COLLAR_LINE)
    return body * (1.0 - gap), gap


# -- front view: details --------------------------------------------------------
def placket(fig, layer, garment):
    """Button placket from the bottom of the V to the hem."""
    top = fig.chest_pt(0.0, CAMP_NECK[0][1], DEPTH["chest"])
    fig.cloth_ink(layer, garment, [top, fig.pelvis_pt(0.0, -0.40, DEPTH["belly"]),
                                   fig.pelvis_pt(0.0, SHIRT_HEM_Y + 0.05, DEPTH["crotch"])])
    for y in np.linspace(-1.45, -0.05, 4):
        center = fig.at(fig.pelvis_pt(0.022, y, DEPTH["belly"]))
        dot = pk.fill_mask(fig.shape, pk.ellipse(center[0], center[1], fig.px(0.014), fig.px(0.014)))
        layer.paint(dot * garment["mask"], pk.adjust(garment["color"], value=0.82), 0.9)


def side_stripes(fig, layer, garment):
    """Training shorts: a contrast stripe down each outer seam."""
    strokes = []
    for side, sign in SIDES.items():
        hip, knee = fig.joints[f"hip_{side}"], fig.joints[f"knee_{side}"]
        axis = (knee - hip) / (np.linalg.norm(knee - hip) or 1.0)
        outward = np.array([axis[1], -axis[0]], np.float32)
        if outward[0] * sign < 0:          # point away from the body's midline
            outward = -outward
        top = fig.pelvis_pt(0.50 * sign * fig.build.hips, SHORTS_WAIST_Y + WAISTBAND)
        hem = hip + (knee - hip) * TRAINING_LENGTH + outward * STRIPE_OFFSET
        strokes.append((pk.resample(fig.at(np.array([top, hem])), 12), fig.px(0.018)))
    stripe = pk.stroke_mask(fig.shape, strokes) * garment["mask"]
    layer.paint(stripe, pk.mix(fig.pal.accent, "#ffffff", 0.15), 0.95)


def waistband(fig, layer, garment):
    band = garment["mask"] * fig.above_line(SHORTS_WAIST_Y + WAISTBAND)
    layer.paint(band, pk.adjust(garment["color"], value=1.12), 0.9)
    fig.cloth_ink(layer, garment, [fig.pelvis_pt(-0.6, SHORTS_WAIST_Y + WAISTBAND),
                                   fig.pelvis_pt(0.0, SHORTS_WAIST_Y + WAISTBAND + 0.01, DEPTH["belly"]),
                                   fig.pelvis_pt(0.6, SHORTS_WAIST_Y + WAISTBAND)])


def denim_front(fig, layer, garment):
    """Trucker jacket: flap pockets, the waistband seam and light topstitching."""
    for mirror in (False, True):
        sign = -1.0 if mirror else 1.0
        flap = [fig.chest_pt(x * sign, y, DEPTH["chest"]) for x, y in DENIM_FLAP]
        fig.cloth_ink(layer, garment, flap + [flap[0]])
        button = fig.at(fig.chest_pt(0.26 * sign, 0.53, DEPTH["chest"]))
        dot = pk.fill_mask(fig.shape, pk.ellipse(button[0], button[1], fig.px(0.016), fig.px(0.016)))
        layer.paint(dot * garment["mask"], ZIP_COLOR, 0.95)
    fig.cloth_ink(layer, garment, [fig.pelvis_pt(-0.9, DENIM_HEM_Y - DENIM_BAND),
                                   fig.pelvis_pt(0.0, DENIM_HEM_Y - DENIM_BAND + 0.01, DEPTH["belly"]),
                                   fig.pelvis_pt(0.9, DENIM_HEM_Y - DENIM_BAND)])


def zipper(fig, layer, garment):
    """Rider jacket: an open zip along the right front and a slanted chest zip."""
    lines = [[fig.chest_pt(0.265, 0.72, DEPTH["chest"]), fig.pelvis_pt(0.245, LEATHER_HEM_Y - 0.02, DEPTH["belly"])],
             [fig.chest_pt(-0.46, 0.52, DEPTH["chest"]), fig.chest_pt(-0.34, 0.84, DEPTH["chest"])]]
    strokes = [(pk.resample(fig.at(np.array(line)), 16), fig.px(0.012)) for line in lines]
    layer.paint(pk.stroke_mask(fig.shape, strokes) * garment["mask"], ZIP_COLOR, 0.9)


def coat_pockets(fig, layer, garment):
    for sign in (1.0, -1.0):
        (x0, y0), (x1, y1) = COAT_POCKET
        fig.cloth_ink(layer, garment, [fig.pelvis_pt(x0 * sign, y0), fig.pelvis_pt(x1 * sign, y1)])


def turtle_folds(fig, layer, garment):
    for y in TURTLE_FOLDS:
        fig.cloth_ink(layer, garment, [fig.chest_pt(-0.16, y), fig.chest_pt(0.0, y + 0.02, DEPTH["chest"]),
                                       fig.chest_pt(0.16, y)])


def knit_ribs(fig, layer, garment):
    """Rib knit: soft vertical lines that follow the body down to the hem."""
    strokes = []
    for x in np.linspace(-0.36, 0.36, KNIT_RIB_COUNT):
        path = np.array([fig.chest_pt(x * 0.9, 0.05, DEPTH["chest"]), fig.chest_pt(x * 0.75, 1.05, DEPTH["chest"]),
                         fig.pelvis_pt(x * 1.05, 0.10, DEPTH["belly"]), fig.pelvis_pt(x * 1.10, KNIT_HEM_Y)])
        line = pk.resample(fig.at(pk.spline(path)), 32)
        strokes.append((line, fig.px(0.010)))
    ribs = pk.blur(pk.stroke_mask(fig.shape, strokes), fig.px(0.004)) * garment["mask"]
    layer.paint(ribs, garment["shadow"], 0.35)


# -- front view: outfits --------------------------------------------------------
def open_shirt_shorts(fig, shoes, cloth, lower) -> list:
    """Short-sleeved camp-collar shirt worn open at the neck and untucked, over shorts."""
    torso = fig.masks["torso"]
    shirt = fig.grow(torso, 0.040) * fig.chest_cover(CAMP_NECK) * fig.above_line(SHIRT_HEM_Y)
    collar = mirrored(fig, CAMP_COLLAR) * fig.grow(torso, 0.06)
    legs, seat = shorts(fig, SHORTS_LENGTH, 0.060, lower)
    return legs + shoes + sleeves(fig, 0.075, 0.50, cloth) + [seat,
        dict(name="camp_shirt", mask=shirt, zone="torso", details=(placket,), **cloth),
        dict(name="collar", mask=collar, zone="torso", fitted=True, color=pk.adjust(cloth["color"], value=1.04),
             shadow=cloth["shadow"])]


def tank_shorts(fig, shoes, cloth, lower) -> list:
    """Sleeveless training top with loose training shorts: waistband and side stripes."""
    cut = (TANK_ARMHOLE if fig.male else SLIM_ARMHOLE, TANK_HEM_Y)
    legs, seat = shorts(fig, TRAINING_LENGTH, 0.070, lower, (waistband, side_stripes), (side_stripes,))
    return legs + shoes + [seat, dict(name="tank", mask=tank_mask(fig, *cut), zone="torso", fitted=not fig.male,
                                      cut=cut, **cloth)]


def denim_jacket_chinos(fig, shoes, cloth, lower) -> list:
    """Open trucker jacket over a crew-neck tee, straight chinos."""
    torso, outer = fig.masks["torso"], colors(outer_color(fig))
    tee = fig.grow(torso, 0.03) * fig.chest_cover(CREW_NECK) * fig.above_line(0.04)
    jacket, _ = open_jacket(fig, DENIM_OPENING, DENIM_HEM_Y, 0.055)
    collar = mirrored(fig, DENIM_COLLAR) * fig.grow(torso, 0.08)
    legs, hips = trousers(fig, True, lower)
    return legs + shoes + sleeves(fig, 0.065, 1.94, outer, cuff=0.10) + [hips,
        dict(name="tee", mask=tee, zone="torso", **cloth),
        dict(name="denim_jacket", mask=jacket, zone="torso", details=(denim_front,), cut=(DENIM_HEM_Y, 0.055), **outer),
        dict(name="collar", mask=collar, zone="torso", fitted=True, color=pk.adjust(outer["color"], value=1.08),
             shadow=outer["color"])]


def leather_jacket_jeans(fig, shoes, cloth, lower) -> list:
    """Open rider jacket with wide lapels over a tee, slim jeans."""
    torso, outer = fig.masks["torso"], colors(outer_color(fig))
    tee = fig.grow(torso, 0.03) * fig.chest_cover(CREW_NECK) * fig.above_line(0.04)
    jacket, _ = open_jacket(fig, LEATHER_OPENING, LEATHER_HEM_Y, 0.050)
    lapels = mirrored(fig, LEATHER_LAPEL) * fig.grow(torso, 0.06) * fig.chest_cover(COLLAR_LINE)
    legs, hips = trousers(fig, False, lower)
    return legs + shoes + sleeves(fig, 0.050, 1.95, {**outer, "gloss": True}) + [hips,
        dict(name="tee", mask=tee, zone="torso", **cloth),
        dict(name="leather_jacket", mask=jacket, zone="torso", gloss=True, details=(zipper,), cut=(LEATHER_HEM_Y, 0.050),
             **outer),
        dict(name="lapels", mask=lapels, zone="torso", fitted=True, gloss=True,
             color=pk.adjust(outer["color"], value=LEATHER_LAPEL_LIFT), shadow=outer["color"])]


def coat_turtleneck(fig, shoes, cloth, lower) -> list:
    """Long open coat over a tucked turtleneck and slacks; the coat hangs straight to below the knee."""
    m, outer = fig.masks, colors(outer_color(fig))
    knee_y = max(fig.joints["knee_left"][1], fig.joints["knee_right"][1]) - fig.joints["pelvis"][1]
    hem_y = float(knee_y + COAT_BELOW_KNEE)
    turtle = fig.grow(m["torso"], 0.03) * fig.chest_cover(TURTLE_NECK) * fig.above_line(TUCKED_HEM_Y)
    skirt = coat_skirt(fig, hem_y)
    gap = fig.chest_poly(COAT_OPENING)
    coat = (np.maximum(fig.grow(m["torso"], 0.065), skirt) * fig.above_line(hem_y)
            * fig.chest_cover(COLLAR_LINE, lower=COAT_COVER_DEPTH))
    coat = coat * (1.0 - gap)
    lap = []
    if fig.pose.seat is not None:
        # Seated: the coat stops at the seat and its two fronts lie open over the thighs.
        coat = coat * fig.above_line(fig.pose.seat + LAP_SEAT_MARGIN)
        thighs = [stroke for side in SIDES for stroke in fig.leg_strokes(side, 0.06, COAT_LAP_COVER)]
        lap_mask = fig.bridge_rows(pk.stroke_mask(fig.shape, thighs)) * (1.0 - gap)
        lap = [dict(name="coat_lap", mask=lap_mask, zone="lap", no_line=coat, **outer)]
    lapels = mirrored(fig, COAT_LAPEL) * coat
    legs, hips = trousers(fig, True, lower)
    return legs + shoes + sleeves(fig, 0.075, 1.96, outer) + [hips,
        dict(name="turtleneck", mask=turtle, zone="torso", details=(turtle_folds,), **cloth),
        dict(name="coat", mask=coat, zone="torso", details=(coat_pockets,), cut=(hem_y, 0.065), **outer),
        dict(name="lapels", mask=lapels, zone="torso", fitted=True, color=pk.adjust(outer["color"], value=1.12),
             shadow=outer["color"])] + lap


def knit_dress(fig, shoes, cloth, lower) -> list:
    """Rib-knit sweater dress: crew neck, long sleeves, hem above the knee, close to the body."""
    m = fig.masks
    cover = fig.chest_cover(KNIT_NECK) * fig.above_line(KNIT_HEM_Y)
    skirt = fig.bridge_rows(fig.grow(m["legs"], 0.015) * cover * (1.0 - fig.above_line(0.10)))
    dress = np.maximum(fig.grow(m["torso"], 0.015) * cover, skirt)
    return shoes + sleeves(fig, 0.040, 1.96, cloth, cuff=KNIT_CUFF) + [
        dict(name="knit_dress", mask=dress, zone="torso", fitted=True, details=(knit_ribs,), **cloth)]


def tank_jeans(fig, shoes, cloth, lower) -> list:
    """Fitted tank top over slim low-rise jeans."""
    cut = (SLIM_ARMHOLE, FITTED_TANK_HEM_Y)
    legs, hips = trousers(fig, False, lower, waist_y=-0.30)
    return legs + shoes + [hips, dict(name="tank", mask=tank_mask(fig, *cut), zone="torso", fitted=True, cut=cut,
                                      **cloth)]


FRONT = {"open_shirt_shorts": open_shirt_shorts, "tank_shorts": tank_shorts, "denim_jacket_chinos": denim_jacket_chinos,
         "leather_jacket_jeans": leather_jacket_jeans, "coat_turtleneck": coat_turtleneck, "knit_dress": knit_dress,
         "tank_jeans": tank_jeans}


def front_garments(fig, kind: str, shoes: list) -> list:
    pal = fig.pal
    cloth = dict(color=pal.cloth, shadow=pal.cloth_shadow)
    return FRONT[kind](fig, shoes, cloth, colors(pal.cloth2))


# -- side view (profile.SideFigure; chest frame x points forward) ----------------------------
SIDE_CAMP_COLLAR = ((-0.150, -0.170), (0.080, -0.130), (0.200, 0.040), (0.130, 0.120), (-0.060, 0.000))
SIDE_DENIM_COLLAR = ((-0.200, -0.180), (0.060, -0.150), (0.150, 0.020), (0.060, 0.080), (-0.160, 0.000))
SIDE_LAPEL = ((0.060, -0.120), (0.200, 0.000), (0.300, 0.200), (0.240, 0.420), (0.140, 0.300))
SIDE_ARMHOLE = (0.17, 0.30)       # half axes of the armhole opening below the shoulder joint
SIDE_ARMHOLE_DROP = 0.20
SIDE_SLIM_ARMHOLE = (0.14, 0.27)
# An open jacket or coat hangs straight down from the collar: in profile the front edge
# is a near-vertical line a little behind the chest front, and the top shows in front of it.
SIDE_FRONT_EDGE = ((0.220, -0.30), (3.0, -0.30), (3.0, 7.0), (0.320, 7.0), (0.340, 0.50), (0.300, 0.10))


def side_shorts(fig, length: float, extra: float, waist_y: float = SHORTS_WAIST_Y) -> np.ndarray:
    legs = [pk.stroke_mask(fig.shape, fig.leg_strokes(side, extra, 1.0))
            * (1.0 - fig.beyond(f"hip_{side}", f"knee_{side}", length)) for side in ("left", "right")]
    return np.maximum.reduce(legs + [fig.grow(fig.masks["torso"], 0.03)]) * (1.0 - fig.above_line(waist_y))


def side_sleeves(fig, extra: float, upto: float, paint: dict, cuff: float = 0.0) -> list:
    out = []
    for side in ("left", "right"):
        mask = pk.stroke_mask(fig.shape, fig.arm_strokes(side, extra, max(upto, 1.0)))
        if upto < 1.0:
            mask = mask * (1.0 - fig.beyond(f"shoulder_{side}", f"elbow_{side}", upto))
        out.append(dict(name=f"sleeve_{side}", mask=mask, zone=f"arm_{side}", **paint))
        if cuff > 0:
            out.append(dict(name=f"cuff_{side}", mask=mask * fig.beyond(f"elbow_{side}", f"wrist_{side}",
                                                                        upto - 1.0 - cuff),
                            zone=f"arm_{side}", fitted=True, color=pk.adjust(paint["color"], value=0.92),
                            shadow=paint["shadow"]))
    return out


def side_trousers(fig, extra: float, paint: dict, waist_y: float = -0.40) -> list:
    legs = [dict(name=f"pants_{side}", mask=pk.stroke_mask(fig.shape, fig.leg_strokes(side, extra, 1.97)),
                 zone=f"leg_{side}", **paint) for side in ("left", "right")]
    hips = fig.grow(fig.masks["torso"], 0.03) * (1.0 - fig.above_line(waist_y))
    return legs + [dict(name="pants_hips", mask=hips, zone="torso", fitted=True, **paint)]


def side_tank(fig, armhole, top_front: float, hem_y: float) -> np.ndarray:
    shoulder = fig.at(fig.joints["shoulder_right"] + np.array([0.0, SIDE_ARMHOLE_DROP], np.float32))
    hole = pk.fill_mask(fig.shape, pk.ellipse(shoulder[0], shoulder[1], fig.px(armhole[0]), fig.px(armhole[1])))
    return fig.grow(fig.masks["torso"], 0.016) * fig.band(-0.10, top_front, hem_y) * (1.0 - hole)


def side_open_front(fig) -> np.ndarray:
    return fig.chest_poly(SIDE_FRONT_EDGE)


def side_flap(fig, points, grow: float = 0.06) -> np.ndarray:
    return fig.chest_poly(points) * fig.grow(fig.masks["torso"], grow)


def side_stripe(fig, layer, garment):
    """Training shorts in profile: the stripe runs down the middle of the near thigh."""
    hip, knee = fig.joints["hip_right"], fig.joints["knee_right"]
    line = np.array([fig.pelvis_pt(0.0, SHORTS_WAIST_Y + WAISTBAND), hip + (knee - hip) * TRAINING_LENGTH])
    stripe = pk.stroke_mask(fig.shape, (pk.resample(fig.at(line), 12), fig.px(0.018))) * garment["mask"]
    layer.paint(stripe, pk.mix(fig.pal.accent, "#ffffff", 0.15), 0.95)


def side_waistband(fig, layer, garment):
    layer.paint(garment["mask"] * fig.above_line(SHORTS_WAIST_Y + WAISTBAND), pk.adjust(garment["color"], value=1.12),
                0.9)


def side_coat_body(fig, hem_y: float, front_gap) -> np.ndarray:
    """Coat in profile: the torso part open at the front, and below it cloth that hangs straight
    from the hips. Seated, the skirt of the coat lies over the lap instead, closed over the thigh."""
    torso = fig.grow(fig.masks["torso"], 0.065) * fig.band(-0.18, -0.10, None)
    if fig.pose.seat is not None:
        return np.maximum(torso * (1.0 - front_gap), fig.seated_skirt(COAT_LAP_COVER, 0.40))
    return np.maximum(torso, fig.side_skirt(hem_y, 0.06)) * fig.above_line(hem_y) * (1.0 - front_gap)


def side_garments(fig, kind: str, shoes: list) -> list:
    pal, torso = fig.pal, fig.masks["torso"]
    cloth = dict(color=pal.cloth, shadow=pal.cloth_shadow)
    lower = colors(pal.cloth2)
    if kind == "open_shirt_shorts":
        shirt = fig.grow(torso, 0.04) * fig.band(-0.16, 0.12, SHIRT_HEM_Y)
        collar = side_flap(fig, SIDE_CAMP_COLLAR)
        return shoes + side_sleeves(fig, 0.075, 0.50, cloth) + [
            dict(name="shorts", mask=side_shorts(fig, SHORTS_LENGTH, 0.06), zone="torso", **lower),
            dict(name="camp_shirt", mask=shirt, zone="torso", **cloth),
            dict(name="collar", mask=collar, zone="torso", fitted=True, color=pk.adjust(pal.cloth, value=1.04),
                 shadow=pal.cloth_shadow)]
    if kind == "tank_shorts":
        tank = side_tank(fig, SIDE_ARMHOLE if fig.male else SIDE_SLIM_ARMHOLE, 0.18, TANK_HEM_Y)
        return shoes + [dict(name="shorts", mask=side_shorts(fig, TRAINING_LENGTH, 0.07), zone="torso",
                             details=(side_waistband, side_stripe), **lower),
                        dict(name="tank", mask=tank, zone="torso", fitted=not fig.male, **cloth)]
    if kind == "tank_jeans":
        tank = side_tank(fig, SIDE_SLIM_ARMHOLE, 0.18, FITTED_TANK_HEM_Y)
        return side_trousers(fig, 0.035, lower, -0.36) + shoes + [
            dict(name="tank", mask=tank, zone="torso", fitted=True, **cloth)]
    if kind == "knit_dress":
        if fig.pose.seat is not None:
            skirt = fig.seated_skirt(0.80, 0.18)
        else:
            skirt = fig.bridge_rows(fig.grow(fig.masks["legs"], 0.015) * fig.above_line(KNIT_HEM_Y)
                                    * (1.0 - fig.above_line(0.10)))
        dress = np.maximum(fig.grow(torso, 0.015) * fig.band(-0.12, -0.08, KNIT_HEM_Y), skirt)
        return shoes + side_sleeves(fig, 0.040, 1.96, cloth, cuff=KNIT_CUFF) + [
            dict(name="knit_dress", mask=dress, zone="torso", fitted=True, **cloth)]
    # Outer layers over a top: jackets and the coat.
    outer = colors(outer_color(fig))
    front_gap = side_open_front(fig)
    if kind == "coat_turtleneck":
        knee_y = fig.joints["knee_right"][1] - fig.joints["pelvis"][1]
        coat = side_coat_body(fig, float(knee_y + COAT_BELOW_KNEE), front_gap)
        turtle = fig.grow(torso, 0.03) * fig.band(-0.36, -0.36, TUCKED_HEM_Y)
        return side_trousers(fig, 0.06, lower) + shoes + side_sleeves(fig, 0.075, 1.96, outer) + [
            dict(name="turtleneck", mask=turtle, zone="torso", **cloth),
            dict(name="coat", mask=coat, zone="torso", **outer),
            dict(name="lapels", mask=side_flap(fig, SIDE_LAPEL) * coat, zone="torso", fitted=True,
                 color=pk.adjust(outer["color"], value=1.12), shadow=outer["color"])]
    tee = fig.grow(torso, 0.035) * fig.band(-0.14, -0.08, 0.04)
    if kind == "denim_jacket_chinos":
        jacket = fig.grow(torso, 0.055) * fig.band(-0.18, -0.10, DENIM_HEM_Y) * (1.0 - front_gap)
        return side_trousers(fig, 0.06, lower) + shoes + side_sleeves(fig, 0.065, 1.94, outer, cuff=0.10) + [
            dict(name="tee", mask=tee, zone="torso", **cloth),
            dict(name="denim_jacket", mask=jacket, zone="torso", **outer),
            dict(name="collar", mask=side_flap(fig, SIDE_DENIM_COLLAR, 0.08), zone="torso", fitted=True,
                 color=pk.adjust(outer["color"], value=1.08), shadow=outer["color"])]
    # leather_jacket_jeans
    jacket = fig.grow(torso, 0.05) * fig.band(-0.18, -0.10, LEATHER_HEM_Y) * (1.0 - front_gap)
    return side_trousers(fig, 0.035, lower) + shoes + side_sleeves(fig, 0.050, 1.95, {**outer, "gloss": True}) + [
        dict(name="tee", mask=tee, zone="torso", **cloth),
        dict(name="leather_jacket", mask=jacket, zone="torso", gloss=True, **outer),
        dict(name="lapels", mask=side_flap(fig, SIDE_LAPEL) * jacket, zone="torso", fitted=True, gloss=True,
             color=pk.adjust(outer["color"], value=LEATHER_LAPEL_LIFT), shadow=outer["color"])]


# -- back view (back.BackFigure: the front garments turned around by name) ---------------------
BACK_NAMES = ("camp_shirt", "tank", "denim_jacket", "leather_jacket", "coat")
BACK_NECK = ((0.0, -0.150), (0.80, -0.150))
TANK_BACK_NECK = ((0.0, 0.020), (0.224, 0.000), (0.306, -0.090), (1.63, -0.100))      # shoulder half-widths
BACK_COLLAR = (-0.200, -0.060)    # band of a shirt collar seen from behind (chest y top, bottom)
DENIM_BACK_COLLAR = (-0.200, 0.020)
DENIM_YOKE = ((-0.80, 0.300), (-0.30, 0.330), (0.0, 0.450), (0.30, 0.330), (0.80, 0.300))


def collar_band(fig, top: float, bottom: float) -> np.ndarray:
    return fig.chest_band(top, bottom) * fig.grow(fig.masks["torso"], 0.06)


def denim_back(fig, layer, garment):
    """Trucker jacket from behind: the pointed yoke across the shoulder blades and the waistband seam."""
    fig.cloth_ink(layer, garment, [fig.chest_pt(x, y) for x, y in DENIM_YOKE])
    hem = garment["cut"][0]
    fig.cloth_ink(layer, garment, [fig.pelvis_pt(-0.9, hem - DENIM_BAND), fig.pelvis_pt(0.9, hem - DENIM_BAND)])


def coat_vent(fig, layer, garment):
    """Center back seam from the collar to the waist, then the vent opening down to the hem."""
    hem = garment["cut"][0]
    fig.cloth_ink(layer, garment, [fig.chest_pt(0.0, -0.10), fig.pelvis_pt(0.0, -0.30), fig.pelvis_pt(0.0, hem - 0.02)])


def back_view(fig, garment) -> list:
    """One front garment of a v9 outfit as seen from behind (zero or more garments)."""
    name, torso = garment["name"], fig.masks["torso"]
    if name == "tank":
        armhole, hem = garment["cut"]
        return [{**garment, "mask": tank_mask(fig, armhole, hem, TANK_BACK_NECK)}]
    if name == "camp_shirt":
        back = fig.grow(torso, 0.040) * fig.above_line(SHIRT_HEM_Y) * fig.chest_cover(BACK_NECK)
        collar = dict(name="collar_back", mask=collar_band(fig, *BACK_COLLAR), zone="torso", fitted=True,
                      color=pk.adjust(garment["color"], value=1.04), shadow=garment["shadow"])
        return [{**garment, "mask": np.maximum(garment["mask"], back), "details": ()}, collar]
    hem, grow = garment["cut"]
    if name == "coat":
        skirt = coat_skirt(fig, hem)
        if fig.pose.seat is not None:
            skirt = skirt * fig.above_line(fig.pose.seat + LAP_SEAT_MARGIN)
        back = (np.maximum(fig.grow(torso, grow), skirt) * fig.above_line(hem)
                * fig.chest_cover(BACK_NECK, lower=COAT_COVER_DEPTH))
        return [{**garment, "mask": back, "details": (coat_vent,), "drape": True}]
    back = fig.grow(torso, grow) * fig.above_line(hem) * fig.chest_cover(BACK_NECK)
    if name == "denim_jacket":
        collar = dict(name="collar_back", mask=collar_band(fig, *DENIM_BACK_COLLAR), zone="torso", fitted=True,
                      color=pk.adjust(garment["color"], value=1.08), shadow=garment["color"])
        return [{**garment, "mask": back, "details": (denim_back,)}, collar]
    return [{**garment, "mask": back, "details": ()}]        # leather_jacket
