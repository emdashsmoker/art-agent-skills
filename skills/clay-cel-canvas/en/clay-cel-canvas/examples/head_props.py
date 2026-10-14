"""Props a painted head can wear or hold: a knit beanie, a lit cigarette, wired earphones.

Both heads (portrait.py, portrait_male.py) call these with their own PropPlaces and
`tilt`, the function that takes points in the head's drawing units to the canvas.
Every prop is drawn over the finished head, so a head without props is unchanged.
Choose them with HeadLook(hat=..., cigarette=..., earrings="earphones").
"""
from dataclasses import dataclass

import numpy as np

from atelier import ellipse, spline

HATS = ("none", "beanie")
CIGARETTES = ("none", "lit")

PROP_PALETTE = {
    "knit": "#2F3039", "knit_deep": "#1A1B21", "knit_light": "#767B8E",
    "paper": "#F3F0EA", "filter": "#D29458", "ash": "#9A9590", "ember": "#FF5A1F", "ember_glow": "#FFB26B",
    "smoke": "#D5DAE0", "bud": "#F2F3F5", "cable": "#E3E5EA",
}

# beanie: an ellipse over the skull, cut at the brim, with a folded cuff
CUFF_SPILL = 12          # the knit stands this far outside the skull at the sides
DOME_RISE = 36           # and this far above it at the top
CUFF_HEIGHT = 0.17       # cuff height as a share of the skull's width
CUFF_SAG = 16            # the cuff's edges dip this much at the forehead: a ring seen a little from above
RIB_COUNT = 24           # ribs across the front of the cuff
RIB_SPREAD = 1.45        # radians either side of the front that the ribs cover
RIB_WIDTH = 1.6
FOLD_WIDTH = 2.4         # the line where the cuff folds up
OUTLINE_SAMPLES = 64
HAT_SHADOW = (4, 12)     # the hat's shadow on the face and front hair

# cigarette: held at the mouth corner, pointing down to the viewer's right
CIGARETTE_LENGTH = 100
CIGARETTE_WIDTH = 12
CIGARETTE_DROOP = 24     # degrees below horizontal
FILTER_SHARE = 0.32      # the filter's share of the length
ASH_SHARE = 0.08
EMBER_RADIUS = 7
EMBER_GLOW_RADIUS = 22

# smoke: thin strands that sway as they rise, over a faint haze
SMOKE_RISE = 300
SMOKE_SWAY = 20
SMOKE_WAVES = 2.2        # sway periods over the rise
SMOKE_POINTS = 48
# Widths are life size: a head is about 460 units, so a 12-unit strand is a wisp about 6 mm wide.
SMOKE_STRANDS = ((0.0, 12.0, 0.55), (0.35, 7.0, 0.42))    # (phase, width, opacity)
SMOKE_HAZE = (60, 26, 0.45)                               # (stroke width, feather, opacity)

# earphones
BUD_RADIUS = 9
CABLE_WIDTH = 2.4
CABLE_SAG = 18           # a hanging cable bows out a little


@dataclass(frozen=True)
class PropPlaces:
    """Where a head's props sit, in that head's drawing units."""
    skull: tuple          # (centre x, centre y, half width, half height): ellipse of the hair over the skull
    brim: float           # y of the beanie's lower edge at the forehead
    mouth: tuple          # mouth corner that holds the cigarette
    ears: tuple           # ((x, y, side, bud), ...): where each cable starts; bud False = under the hair
    cable_join: tuple     # where the two cables meet below the chin
    cable_end: tuple      # where the single cable runs into the clothes
    back_smoke: tuple     # seen from behind: (x, y) where the smoke first shows beside the head, drift


# ---- beanie -------------------------------------------------------------------

def _brim_curve(places, lift, xs):
    """y along a ring around the head at height `lift` above the brim, for the given xs."""
    centre_x, _, half_width, _ = places.skull
    across = np.clip((xs - centre_x) / (half_width + CUFF_SPILL), -1, 1)
    return places.brim - lift - CUFF_SAG * (across ** 2)


def _dome(places):
    """Outline of the whole hat: the ellipse above the brim ring, closed by the ring."""
    centre_x, centre_y, half_width, half_height = places.skull
    width, height = half_width + CUFF_SPILL, half_height + DOME_RISE
    side_y = places.brim - CUFF_SAG
    start = np.arcsin(np.clip((centre_y - side_y) / height, -1, 1))
    angles = np.linspace(np.pi - start, start, OUTLINE_SAMPLES)        # left brim, over the top, right brim
    top = np.stack([centre_x + width * np.cos(angles), centre_y - height * np.sin(angles)], 1)
    xs = np.linspace(top[-1, 0], top[0, 0], OUTLINE_SAMPLES)
    return np.vstack([top, np.stack([xs, _brim_curve(places, 0, xs)], 1)])


def _ring_band(places, low, high, xs):
    """Closed band between two rings, for the cuff."""
    upper, lower = _brim_curve(places, high, xs), _brim_curve(places, low, xs)
    return np.vstack([np.stack([xs, upper], 1), np.stack([xs[::-1], lower[::-1]], 1)])


def beanie_mask(art, tilt, places):
    return art.shape(tilt(_dome(places)))


def draw_beanie(art, tilt, places, under):
    """A dark knit beanie with a ribbed cuff. under: mask of what its shadow falls on."""
    hat = beanie_mask(art, tilt, places)
    art.shadow(art.move(hat, *HAT_SHADOW) * under * (1 - hat), opacity=0.8)
    art.part(hat, PROP_PALETTE["knit"], bulge=60, shadow_tint=PROP_PALETTE["knit_deep"])
    centre_x, _, half_width, _ = places.skull
    width = half_width + CUFF_SPILL
    cuff_height = 2 * half_width * CUFF_HEIGHT
    xs = np.linspace(centre_x - width, centre_x + width, OUTLINE_SAMPLES)
    cuff = art.shape(tilt(_ring_band(places, 0, cuff_height, xs))) * hat
    art.part(cuff, PROP_PALETTE["knit"], bulge=20, shadow_tint=PROP_PALETTE["knit_deep"])
    # Ribs crowd toward the sides, where the cuff turns away: even steps of angle, not of x.
    ribs = []
    for angle in np.linspace(-RIB_SPREAD, RIB_SPREAD, RIB_COUNT):
        x = np.full(2, centre_x + width * np.sin(angle))
        rib = np.stack([x, [_brim_curve(places, 3, x[:1])[0], _brim_curve(places, cuff_height - 3, x[:1])[0]]], 1)
        ribs.append(art.brush(tilt(rib), RIB_WIDTH, "none"))
    art.paint(np.maximum.reduce(ribs) * cuff, PROP_PALETTE["knit_deep"], 0.7)
    fold = art.brush(tilt(np.stack([xs, _brim_curve(places, cuff_height, xs)], 1)), FOLD_WIDTH, "none")
    art.paint(fold * hat, PROP_PALETTE["knit_deep"], 0.9)
    sheen = tilt(spline([(centre_x - width * 0.6, places.brim - cuff_height - 40),
                         (centre_x - width * 0.2, places.brim - cuff_height - 92),
                         (centre_x + width * 0.3, places.brim - cuff_height - 100)]))
    art.light(art.feather(art.brush(sheen, 18), 10) * hat, PROP_PALETTE["knit_light"], 0.35)
    return hat


# ---- cigarette and smoke ------------------------------------------------------

def draw_cigarette(art, tilt, root, droop=CIGARETTE_DROOP):
    """A lit cigarette from the held end `root` (drawing units; at a mouth corner, turn
    applied), pointing to the viewer's right, `droop` degrees below horizontal.
    Returns the burning tip in drawing units, where the smoke starts."""
    angle = np.radians(droop)
    along = np.array([np.cos(angle), np.sin(angle)]) * CIGARETTE_LENGTH
    across = np.array([-along[1], along[0]]) / CIGARETTE_LENGTH * CIGARETTE_WIDTH / 2
    root = np.asarray(root, float)

    def piece(start, end):
        a, b = root + along * start, root + along * end
        return art.shape(tilt(np.array([a - across, b - across, b + across, a + across])))

    art.part(piece(0, 1), PROP_PALETTE["paper"], bulge=5)
    art.part(piece(0, FILTER_SHARE), PROP_PALETTE["filter"], bulge=5)
    art.part(piece(1 - ASH_SHARE, 1), PROP_PALETTE["ash"], bulge=4)
    tip = root + along
    # tilt only turns the drawing, so a radius in drawing units holds on the canvas
    ember = tilt(tip[None])[0]
    art.paint(art.blob(ember, EMBER_RADIUS), PROP_PALETTE["ember"], 0.95)
    art.light(art.blob(ember, EMBER_GLOW_RADIUS), PROP_PALETTE["ember_glow"], 0.7)
    return tip


def draw_smoke(art, tilt, start, drift=40.0):
    """Smoke rising from `start` (drawing units), swaying, drifting sideways by `drift`."""
    rise = np.linspace(0, 1, SMOKE_POINTS)
    haze_width, haze_feather, haze_opacity = SMOKE_HAZE
    for phase, width, opacity in SMOKE_STRANDS:
        sway = SMOKE_SWAY * rise * np.sin(2 * np.pi * (SMOKE_WAVES * rise + phase))
        path = tilt(np.stack([start[0] + drift * rise + sway, start[1] - SMOKE_RISE * rise], 1))
        art.mark(path, PROP_PALETTE["smoke"], width, "both", opacity)
        if phase == 0:
            art.light(art.feather(art.brush(path, haze_width), haze_feather), PROP_PALETTE["smoke"], haze_opacity)


# ---- earphones ----------------------------------------------------------------

def draw_earphones(art, tilt, places, in_sight):
    """White wired earbuds; in_sight(side) says whether that ear shows. Each cable hangs
    from its ear (or from under the hair) to the join below the chin, then one runs on."""
    join = np.asarray(places.cable_join, float)
    for x, y, side, bud in places.ears:
        start = np.array([x, y + (BUD_RADIUS if bud else 0)])
        middle = (start + join) / 2 + (side * CABLE_SAG, 0)
        art.mark(tilt(spline([tuple(start), tuple(middle), tuple(join)])), PROP_PALETTE["cable"], CABLE_WIDTH,
                 "none")
        if bud and in_sight(side):
            art.part(tilt(ellipse(x, y, BUD_RADIUS, BUD_RADIUS * 1.15)), PROP_PALETTE["bud"], bulge=6)
    art.mark(tilt(spline([tuple(join), tuple((join + places.cable_end) / 2 + (4, 0)), tuple(places.cable_end)])),
             PROP_PALETTE["cable"], CABLE_WIDTH, "end")
