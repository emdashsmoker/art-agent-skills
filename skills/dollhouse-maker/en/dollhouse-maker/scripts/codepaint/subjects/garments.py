"""Everyday clothes cut from the body itself, the way a costume illustrator dresses a figure drawing.

  1. a garment on the trunk is the trunk outline grown by the cloth's ease, cut between two lines
     across the body (neckline and hem), so it follows any pose and view the body is drawn in
  2. a sleeve or a trouser leg is a tube along the limb's bones from one point to another
     (0 = root joint, 1 = middle joint, 2 = end joint), its width the limb's width plus ease
  3. a skirt is the hips plus a tube down each thigh that flares toward the hem, joined across
     the gap between the legs, so it also drapes over seated thighs
  4. seams, folds, pockets and buttons are lines laid inside the garment

All functions take the Figure whose parts are being built (Figure.geo holds the body geometry).
"""
import cv2
import numpy as np

from ..color import rgb, mix
from ..geometry import catmull_rom, offset_polygon, Ribbon
from ..scene import Part, Line, Stroke

TOPS = ("tee", "longsleeve", "shirt", "blouse")
BOTTOMS = ("jeans", "slacks", "skirt", "long_skirt")

# neckline: the upper cut, a curve across the chest frame (x across, y down from the pit of the neck);
# the garment keeps what lies below it. Ends far out so the shoulders are covered.
NECKLINES = {
    "crew": [(-2.0, -0.60), (-0.42, -0.20), (-0.25, -0.09), (-0.13, 0.02), (0.0, 0.05), (0.13, 0.02), (0.25, -0.09),
             (0.42, -0.20), (2.0, -0.60)],
    "v": [(-2.0, -0.60), (-0.42, -0.20), (-0.22, -0.10), (-0.10, 0.18), (0.0, 0.42), (0.10, 0.18), (0.22, -0.10),
          (0.42, -0.20), (2.0, -0.60)],
    "collar": [(-2.0, -0.60), (-0.40, -0.22), (-0.22, -0.14), (-0.10, -0.02), (0.0, 0.12), (0.10, -0.02), (0.22, -0.14),
               (0.40, -0.22), (2.0, -0.60)],
    # from behind every top sits high on the nape: a shallow curve across the base of the neck
    "back": [(-2.0, -0.60), (-0.42, -0.22), (-0.26, -0.13), (-0.13, -0.085), (0.0, -0.075), (0.13, -0.085),
             (0.26, -0.13), (0.42, -0.22), (2.0, -0.60)],
}
# in profile the cut runs from the nape (x < 0) to the front of the neck (x > 0); chest frame
SIDE_NECKLINES = {
    "crew": [(-2.2, -0.70), (-0.30, -0.15), (-0.15, -0.10), (0.0, -0.04), (0.12, 0.03), (0.22, 0.07), (2.2, 0.12)],
    "v": [(-2.2, -0.70), (-0.30, -0.15), (-0.15, -0.10), (0.0, -0.04), (0.12, 0.05), (0.22, 0.13), (2.2, 0.19)],
    "collar": [(-2.2, -0.70), (-0.30, -0.16), (-0.15, -0.12), (0.0, -0.06), (0.12, 0.01), (0.22, 0.05), (2.2, 0.10)],
}
SIDE_RIB = [(-0.26, -0.09), (-0.12, -0.06), (0.02, 0.00), (0.15, 0.07)]
SIDE_COLLAR = [(-0.25, -0.15), (-0.10, -0.15), (0.05, -0.07), (0.17, 0.05), (0.11, 0.09), (0.02, 0.02), (-0.12, -0.05),
               (-0.25, -0.05)]
BACK_RIB = [(-0.28, -0.11), (-0.14, -0.05), (0.0, -0.04), (0.14, -0.05), (0.28, -0.11)]      # neckband seam, chest frame
SHIRT_YOKE = 0.34             # chest frame y of the seam across a shirt's shoulders, seen from behind
# per top: neckline, hem (pelvis frame y), body ease (hu), sleeve end (0 shoulder .. 2 wrist), sleeve width
# factor and ease, tucked into the bottom or worn over it
TOP_CUT = {
    "tee": dict(neck="crew", hem=-0.22, ease=0.035, sleeve=0.48, s_scale=1.16, s_add=0.035, tucked=False),
    "longsleeve": dict(neck="crew", hem=-0.25, ease=0.022, sleeve=1.93, s_scale=1.06, s_add=0.018, tucked=False),
    "shirt": dict(neck="collar", hem=-0.08, ease=0.05, sleeve=1.88, s_scale=1.16, s_add=0.035, tucked=False),
    "blouse": dict(neck="v", hem=-0.58, ease=0.04, sleeve=1.86, s_scale=1.22, s_add=0.04, tucked=True),
}
# per bottom: waist (pelvis frame y), leg end (0 hip .. 2 ankle), width factor, ease (hu), extra flare at the hem
# (hu), straight below the knee
BOTTOM_CUT = {
    "jeans": dict(waist=-0.46, end=1.93, scale=1.03, ease=0.025, flare=0.0, straight=False, skirt=False),
    "slacks": dict(waist=-0.58, end=1.95, scale=1.06, ease=0.045, flare=0.02, straight=True, skirt=False),
    "skirt": dict(waist=-0.66, end=0.86, scale=1.04, ease=0.04, flare=0.16, straight=False, skirt=True),
    "long_skirt": dict(waist=-0.66, end=1.80, scale=1.04, ease=0.05, flare=0.34, straight=False, skirt=True),
}
CLIP_SUB = 2                  # raster resolution of the cut, per px
KNEE_SPAN = 0.92              # a seated knee seen from the front: share of the leg's half width the edge spans,
KNEE_SAG = 0.13               # how far (hu) its rounded edge dips at the middle,
KNEE_SHADE_DROP = 0.07        # and the band of shade on the shin just below it: offset and width (hu)
KNEE_SHADE_W = 0.10
CONTOUR_STEP = 3              # px between kept outline points after a cut (smooths the raster steps)
SLEEVE_ROOT = 0.0             # a sleeve starts at the shoulder joint: its round top covers the arm's own round
                              # top and meets the shoulder line of the body piece instead of standing above it


# ---- geometry ------------------------------------------------------------------------
def clip_polys(subjects, region):
    """Intersection of the union of subject polygons with a region polygon, as smooth polygons."""
    allp = np.vstack(list(subjects) + [region])
    x0, y0 = np.floor(allp.min(0)) - 4
    x1, y1 = np.ceil(allp.max(0)) + 4
    w, h = int((x1 - x0) * CLIP_SUB) + 1, int((y1 - y0) * CLIP_SUB) + 1
    a, b = np.zeros((h, w), np.uint8), np.zeros((h, w), np.uint8)
    for p in subjects:
        cv2.fillPoly(a, [np.round((p - [x0, y0]) * CLIP_SUB).astype(np.int32)], 255)
    cv2.fillPoly(b, [np.round((region - [x0, y0]) * CLIP_SUB).astype(np.int32)], 255)
    contours, _ = cv2.findContours(cv2.bitwise_and(a, b), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in contours:
        pts = c[:, 0, :].astype(float) / CLIP_SUB + [x0, y0]
        keep = pts[::max(1, CONTOUR_STEP * CLIP_SUB)]
        if len(keep) >= 6:
            out.append(catmull_rom(keep, closed=True, samples=3))
    return out


def band(fig, top_curve, bottom_y, frame_top="chest", frame_bottom="pelvis"):
    """Region between a curve across one frame and a straight line across another (image polygon)."""
    top = fig.I(fig.F(frame_top, top_curve))
    bottom = fig.I(fig.F(frame_bottom, [(2.2, bottom_y), (-2.2, bottom_y)]))
    return np.vstack([top, bottom])


def below(fig, frame, y):
    """Everything below a line across a frame (for waistbands)."""
    line = fig.I(fig.F(frame, [(-2.2, y), (2.2, y)]))
    down = (fig.I(np.array([0.0, 6.0])) - fig.I(np.zeros(2))) * 1.0
    return np.vstack([line, line[::-1] + down])


def limb_point(g, L):
    """Point on a limb's bones at L (0 root joint, 1 middle joint, 2 end joint); L < 0 runs back past the root."""
    a, b, c = g["a"], g["b"], g["c"]
    if L <= 1:
        return a + (b - a) * L
    return b + (c - b) * (L - 1)


def limb_width(fig, g, L, col):
    """Half width of the limb at L on one side (col 0 outer, 1 inner), px."""
    table, t = (g["upper"], max(L, 0.0)) if L <= 1 else (g["lower"], L - 1)
    arr = np.array(table, float)
    return float(np.interp(t, arr[:, 0], arr[:, 1 + col])) * fig.u * g["thick"]


def tube(fig, kind, side, L0, L1, scale=1.0, ease=0.0, flare=0.0, straight=False, round_start=True,
         round_end=False, steps=18):
    """Ribbon(s) around a limb from L0 to L1: the limb's own widths times scale plus ease (hu), growing by
    flare (hu) toward L1. A sharply bent limb gives one ribbon per bone, as the body does."""
    g = fig.geo["limbs"][(kind, side)]
    spans = [(L0, L1)]
    if g["bent"] and L0 < 1 < L1:
        spans = [(L0, 1.0), (1.0, L1)]
    knee_w = None
    out = []
    for k, (l0, l1) in enumerate(spans):
        Ls = np.linspace(l0, l1, steps)
        axis = np.array([limb_point(g, L) for L in Ls])
        if not g["bent"] and l0 < 1 < l1:
            keep = np.vstack([axis[:-1:3], axis[-1:]])       # every third point, always ending on the last
            axis = catmull_rom(keep, samples=4)
            Ls = np.linspace(l0, l1, len(axis))
        f = (Ls - L0) / max(L1 - L0, 1e-6)
        w = []
        for col in (0, 1):
            ws = np.array([limb_width(fig, g, L, col) for L in Ls]) * scale + (ease + flare * f ** 1.5) * fig.u
            if straight:                                   # trousers that fall straight from the knee
                knee_w = limb_width(fig, g, 1.0, col) * scale + ease * fig.u
                ws = np.where(Ls > 1.0, np.maximum(ws, knee_w), ws)
            w.append(ws)
        t = np.linspace(0, 1, len(Ls))
        ka, kb = (w[0], w[1]) if g["outer_is_a"] else (w[1], w[0])
        rib = Ribbon(axis, list(zip(t, ka)), list(zip(t, kb)), step=3.0,
                     round_start=round_start if k == 0 else True, round_end=round_end if k == len(spans) - 1 else True)
        out.append(rib)
    return out


def _dark(color, t=0.5):
    return mix(color, "#0c0a14", t)


def _ink(fig, color):
    return Line(1.7 * fig.px * fig.s.line, color=_dark(color, 0.6))


def _detail(fig, path, color, alpha=0.45, width=1.2, clip=True):
    return Stroke(catmull_rom(np.asarray(path), samples=6), width=width * fig.px, color=color, alpha=alpha,
                  feature=False, clip=clip)


# ---- tops ----------------------------------------------------------------------------------
def top_body(fig, kind, color, under):
    """The trunk piece of a top: eased trunk (and bust) cut between the neckline and the hem."""
    cut = TOP_CUT[kind]
    e = cut["ease"] * fig.u
    subjects = [offset_polygon(fig.geo["trunk"], e)] + [offset_polygon(b, e * 0.6) for b in fig.geo["breasts"]]
    if fig.side:
        neck = SIDE_NECKLINES[cut["neck"]]
    else:
        neck = NECKLINES["back" if fig.back else cut["neck"]]
    region = band(fig, neck, cut["hem"])
    polys = clip_polys(subjects, region)
    name = f"top_{kind}"
    dark = _dark(color, 0.45)
    strokes = []
    if fig.side:
        if kind in ("tee", "longsleeve"):                  # the neckband from the nape round to the front
            strokes.append(_detail(fig, fig.I(fig.F("chest", SIDE_RIB)), dark, 0.55, 1.3))
        seam = np.vstack([fig.F("chest", [(-0.05, 0.62), (-0.04, 1.0)]), fig.F("waist", [(-0.03, 0.0)]),
                          fig.F("pelvis", [(-0.04, cut["hem"] + 0.05)])])
        strokes.append(_detail(fig, fig.I(seam), dark, 0.30))    # the side seam
    elif fig.back:
        if kind in ("tee", "longsleeve"):                  # the neckband seam, high on the nape
            strokes.append(_detail(fig, fig.I(fig.F("chest", BACK_RIB)), dark, 0.55, 1.3))
        if kind == "shirt":                                # the yoke across the shoulders, a box pleat below it
            strokes.append(_detail(fig, fig.I(fig.F("chest", [(-1.2, SHIRT_YOKE + 0.04), (0.0, SHIRT_YOKE),
                                                               (1.2, SHIRT_YOKE + 0.04)])), dark, 0.5))
            for x in (-0.05, 0.05):
                strokes.append(_detail(fig, fig.I(fig.F("chest", [(x, SHIRT_YOKE), (x * 1.6, SHIRT_YOKE + 0.40)])), dark, 0.35))
        if kind == "blouse":                               # a seam down the middle of the back
            seam = np.vstack([fig.F("chest", [(0.0, -0.04), (0.0, 0.9)]), fig.F("waist", [(0.0, 0.10)])])
            strokes.append(_detail(fig, fig.I(seam), dark, 0.3))
    elif kind in ("tee", "longsleeve"):                    # a ribbed neckband just inside the neckline
        rib = fig.I(fig.F("chest", [(-0.27, -0.06), (-0.14, 0.07), (0.0, 0.10), (0.14, 0.07), (0.27, -0.06)]))
        strokes.append(_detail(fig, rib, dark, 0.55, 1.3))
    if kind == "shirt" and not fig.back and not fig.side:  # placket, buttons
        placket = np.vstack([fig.F("chest", [(0.02, 0.14), (0.03, 0.9)]), fig.F("waist", [(0.03, 0.0)]),
                             fig.F("pelvis", [(0.035, -0.12)])])
        strokes.append(_detail(fig, fig.I(placket), dark, 0.55, 1.2))
        for k in range(5):
            p = fig.I(placket[0] + (placket[-1] - placket[0]) * (0.08 + k * 0.22))
            strokes.append(Stroke(np.array([p - [0.012 * fig.u, 0], p + [0.012 * fig.u, 0]]), width=3.2 * fig.px,
                                  color=mix(color, "#ffffff", 0.6), alpha=0.95, taper=(False, False), clip=True))
    if kind == "blouse" and not fig.back and not fig.side:  # soft drape from the shoulders into the waist
        for sd in (-1, 1):
            fold = np.vstack([fig.F("chest", [(sd * 0.40, 0.25), (sd * 0.34, 1.05)]), fig.F("waist", [(sd * 0.22, 0.10)])])
            strokes.append(_detail(fig, fig.I(fold), dark, 0.30))
    for sd in (() if fig.side else (-1, 1)):               # side folds where the cloth gathers at the waist
        fold = np.vstack([fig.F("chest", [(sd * 0.55, 1.0)]), fig.F("waist", [(sd * 0.48, 0.12)])])
        strokes.append(_detail(fig, fig.I(fold), dark, 0.25))
    parts = [Part(name, color, polys=polys, material="cloth", bulge=0.55, line=_ink(fig, color), merge=name,
                  under=under, group="outfit", strokes=strokes, cast=0.02 * fig.u)]
    if fig.geo["breasts"]:                                 # the bust keeps its volume under the cloth
        for p in fig._breast_cloth(rgb(color), name, name + "_bust", 0.012, line_alpha=0.15, bulge=0.6):
            p.under = under
            parts.append(p)
    if kind == "shirt":
        if fig.side:
            parts.append(Part("collar_side", mix(color, "#ffffff", 0.06),
                              polys=[catmull_rom(fig.I(fig.F("chest", SIDE_COLLAR)), closed=True, samples=4)],
                              material="cloth", bulge=0.4, line=_ink(fig, color), under=under, group="outfit",
                              cast=0.015 * fig.u))
        else:
            parts += _collar_back(fig, color, under) if fig.back else _collar(fig, color, under)
    return parts


def _collar(fig, color, under):
    """Two collar points turned down over the neckline."""
    parts = []
    for sd in (-1, 1):
        pts = fig.F("chest", [(sd * 0.03, 0.12), (sd * 0.22, -0.15), (sd * 0.31, -0.08), (sd * 0.27, 0.26)])
        poly = fig.I(pts)                                   # pointed: a shirt collar has corners
        parts.append(Part(f"collar_{sd}", mix(color, "#ffffff", 0.06), polys=[poly], material="cloth", bulge=0.4,
                          line=_ink(fig, color), under=under, group="outfit", cast=0.015 * fig.u))
    return parts


def _collar_back(fig, color, under):
    """The collar seen from behind: a band standing around the nape, turned down over the neckline."""
    top = [(x, y - 0.11) for x, y in BACK_RIB[::-1]]
    pts = fig.F("chest", [(-0.33, -0.15)] + BACK_RIB + [(0.33, -0.15)] + top)
    return [Part("collar_back", mix(color, "#ffffff", 0.06), polys=[catmull_rom(fig.I(pts), closed=True, samples=4)],
                 material="cloth", bulge=0.4, line=_ink(fig, color), under=under, group="outfit", cast=0.015 * fig.u)]


def sleeve(fig, kind, side):
    """A sleeve over one arm, built with the arm so it stacks with it; a shirt adds a cuff."""
    cut = TOP_CUT[kind]
    color = fig.s.cloth
    ribs = tube(fig, "arm", side, SLEEVE_ROOT, cut["sleeve"], scale=cut["s_scale"], ease=cut["s_add"],
                flare=0.02 if kind == "blouse" else 0.0)
    polys = [p for r in ribs for p in r.polys()]
    key = f"sleeve_{side}"
    strokes = []
    g = fig.geo["limbs"][("arm", side)]
    if cut["sleeve"] > 1.2:                                # folds at the inside of the elbow
        b = limb_point(g, 1.0)
        d = limb_point(g, 1.1) - limb_point(g, 0.9)
        n = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-6)
        for k in (-1, 1):
            strokes.append(_detail(fig, [b + n * 0.05 * fig.u + d * 0.3 * k, b + d * 0.1 * k, b - n * 0.05 * fig.u + d * 0.25 * k],
                                   _dark(color, 0.45), 0.35))
    parts = [Part(key, color, polys=polys, material="cloth", bulge=0.5, line=_ink(fig, color), merge=key,
                  group="outfit", tags=(f"arm_{side}",), strokes=strokes,
                  joints=[(*limb_point(g, 0.0), 0.22 * fig.u)])]
    if kind in ("shirt", "blouse"):
        cuff = tube(fig, "arm", side, cut["sleeve"] - 0.10, cut["sleeve"], scale=cut["s_scale"] * 1.02,
                    ease=cut["s_add"], round_start=False)
        parts.append(Part(key + "_cuff", mix(color, "#ffffff", 0.05), polys=[p for r in cuff for p in r.polys()],
                          material="cloth", bulge=0.4, line=_ink(fig, color), group="outfit", tags=(f"arm_{side}",)))
    return parts


# ---- bottoms --------------------------------------------------------------------------------
def bottom(fig, kind, color, under):
    """Trousers or a skirt: the hips below the waistband plus a tube down each leg, filled as one piece."""
    cut = BOTTOM_CUT[kind]
    e = cut["ease"] * fig.u
    seat = [offset_polygon(fig.geo["seat"], e)] if fig.geo.get("seat") is not None else []
    hips = clip_polys([offset_polygon(fig.geo["trunk"], e)] + seat, below(fig, "pelvis", cut["waist"]))
    legs, tubes, far_tube = {}, [], []
    for side in ("left", "right"):
        ribs = tube(fig, "leg", side, 0.0, cut["end"], scale=cut["scale"], ease=cut["ease"], flare=cut["flare"],
                    straight=cut["straight"], round_start=False)
        legs[side] = ribs
        polys_ = [p for r in ribs for p in r.polys()]
        if fig.side and side == "left" and not cut["skirt"]:   # in profile the far trouser leg is its own form
            far_tube = polys_
        else:
            tubes += polys_
    polys = hips + tubes
    if cut["skirt"]:
        polys.append(_web(fig, legs))
    name = f"bottom_{kind}"
    dark = _dark(color, 0.45)
    strokes = _bottom_details(fig, kind, cut, legs, color, dark) + _knees_toward(fig, cut, dark)
    main = Part(name, color, polys=polys, material="cloth", bulge=0.5, line=_ink(fig, color), merge=name,
                under=under, group="outfit", strokes=strokes, cast=0.015 * fig.u)
    if not far_tube:
        return [main]
    far = Part(name + "_far", color, polys=far_tube, material="cloth", bulge=0.5, line=_ink(fig, color),
               merge=name + "_far", under=under, group="outfit", light_bias=-0.22, cast=0.015 * fig.u,
               strokes=_knee_creases(fig, ["left"], dark))
    return [far, main]


def _knees_toward(fig, cut, dark):
    """Seated and seen from the front, a thigh points at the viewer: the cloth over each knee ends in a rounded
    edge across the shin below it, with a band of shade where the shin turns down out of the light."""
    strokes = []
    for side in ("left", "right"):
        g = fig.geo["limbs"][("leg", side)]
        if not g.get("toward") or cut["end"] <= 1.0:
            continue
        kp = limb_point(g, 1.0)
        d = kp - limb_point(g, 0.0)
        d = d / max(np.linalg.norm(d), 1e-6)
        n_ = np.array([-d[1], d[0]])
        half = [limb_width(fig, g, 1.0, col) * cut["scale"] + cut["ease"] * fig.u for col in (0, 1)]
        right, left = (half[0], half[1]) if (side == "right") == g["outer_is_a"] else (half[1], half[0])
        s_ = np.linspace(-1, 1, 9)
        width = np.where(s_ < 0, left, right) * KNEE_SPAN
        edge = kp + n_[None] * (s_ * width)[:, None] + d[None] * (np.sqrt(1 - s_ ** 2) * KNEE_SAG * fig.u)[:, None]
        strokes.append(_detail(fig, edge, dark, 0.65, width=1.6))
        strokes.append(_detail(fig, edge + d * KNEE_SHADE_DROP * fig.u, dark, 0.22, width=KNEE_SHADE_W * fig.u / fig.px))
    return strokes


def _knee_creases(fig, sides, dark):
    strokes = []
    for side in sides:
        g = fig.geo["limbs"][("leg", side)]
        kp = limb_point(g, 1.0)
        d = limb_point(g, 1.05) - limb_point(g, 0.95)
        n_ = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-6)
        for k in (-0.5, 0.5):
            strokes.append(_detail(fig, [kp + n_ * 0.12 * fig.u + d * k, kp + d * (k + 0.3), kp - n_ * 0.10 * fig.u + d * k],
                                   dark, 0.3))
    return strokes


def _web(fig, legs):
    """Cloth spanning the gap between the legs from the crotch to the hem (a skirt is one piece)."""
    crotch = fig.I(fig.F("pelvis", [(0.0, -0.10)]))[0]
    ends = []
    for side in ("left", "right"):
        r = legs[side][-1]
        ends.append((r.side_a[-1], r.side_b[-1]))
    (la, lb), (ra, rb) = ends
    if fig.side:                                            # in profile the hems lie front and back: span them all
        pts = np.array([crotch, la, lb, ra, rb], np.float32)
        return cv2.convexHull(pts)[:, 0, :].astype(float)
    return np.array([crotch, la, lb, ra, rb])


def _bottom_details(fig, kind, cut, legs, color, dark):
    strokes = []
    band_y = cut["waist"] + 0.07
    strokes.append(_detail(fig, fig.I(fig.F("pelvis", [(-0.9, band_y), (0.0, band_y + 0.01), (0.9, band_y)])), dark, 0.5))
    if not cut["skirt"] and fig.side:
        strokes += _side_details(fig, kind, band_y, dark, cut)
    elif not cut["skirt"] and fig.back:
        strokes += _seat_details(fig, kind, band_y, dark)
    elif not cut["skirt"]:
        fly = fig.F("pelvis", [(0.06, band_y + 0.02), (0.07, 0.10), (0.0, 0.24)])
        strokes.append(_detail(fig, fig.I(fly), dark, 0.5))
        for sd in (-1, 1):                                  # front pockets
            pocket = fig.F("pelvis", [(sd * 0.40, band_y + 0.01), (sd * 0.50, -0.20), (sd * 0.70, -0.10)])
            strokes.append(_detail(fig, fig.I(pocket), dark, 0.45))
    if not cut["skirt"] and fig.side:
        strokes += _knee_creases(fig, ["right"], dark)
        if kind == "jeans":
            strokes.append(_detail(fig, fig.I(fig.F("pelvis", [(-0.9, band_y + 0.02), (0.9, band_y + 0.02)])), "#d9a04a",
                                   0.6, 0.9))
    elif not cut["skirt"]:
        near = "left" if fig.far > 0 else "right"           # the leg in front shows its inside seam
        g = fig.geo["limbs"][("leg", near)]
        for r in legs[near]:
            inner = r.side_b if g["outer_is_a"] else r.side_a
            n = len(inner)
            strokes.append(Stroke(inner[int(n * 0.12):int(n * 0.97)], width=1.6 * fig.px, color=_dark(color, 0.6),
                                  alpha=0.8, feature=False, clip=True))
        for side in ("left", "right"):                      # creases behind the knee and at the hem
            g = fig.geo["limbs"][("leg", side)]
            kp = limb_point(g, 1.0)
            d = limb_point(g, 1.05) - limb_point(g, 0.95)
            n_ = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-6)
            for k in (-0.5, 0.5):
                strokes.append(_detail(fig, [kp + n_ * 0.12 * fig.u + d * k, kp + d * (k + 0.3), kp - n_ * 0.10 * fig.u + d * k],
                                       dark, 0.3))
        if kind == "jeans":                                 # top stitching in thread color
            thread = "#d9a04a"
            strokes.append(_detail(fig, fig.I(fig.F("pelvis", [(-0.9, band_y + 0.02), (0.9, band_y + 0.02)])), thread, 0.6, 0.9))
    else:                                                   # skirts: folds falling from the waist to the hem
        if fig.back:                                        # a zip down the middle of the back, a vent at the hem
            strokes.append(_detail(fig, fig.I(fig.F("pelvis", [(0.0, band_y), (0.0, band_y + 0.42)])), dark, 0.55))
            pull = fig.I(fig.F("pelvis", [(0.0, band_y + 0.02)]))[0]
            strokes.append(Stroke(np.array([pull, pull + [0, 0.05 * fig.u]]), width=3.0 * fig.px, color=_dark(color, 0.25),
                                  alpha=0.9, taper=(False, False), clip=True))
            ends = [limb_point(fig.geo["limbs"][("leg", side)], cut["end"]) for side in ("left", "right")]
            hem = (ends[0] + ends[1]) / 2
            strokes.append(_detail(fig, [hem, hem - np.array([0, 0.28 * fig.u])], dark, 0.45))
        for sd in (-1, 1):
            for k, x in enumerate((0.18, 0.52)):
                top_p = fig.F("pelvis", [(sd * x, cut["waist"] + 0.15)])[0]
                side = "left" if sd < 0 else "right"
                g = fig.geo["limbs"][("leg", side)]
                end = (limb_point(g, cut["end"] * 0.96) - fig.j["pelvis"]) * (1.0 + 0.12 * k) + fig.j["pelvis"]
                strokes.append(_detail(fig, fig.I(np.array([top_p, (top_p + end) / 2, end])), dark, 0.32))
    return strokes


def _side_details(fig, kind, band_y, dark, cut):
    """Trousers in profile: the slant of the front pocket, the outseam down the near leg, the edge of a back pocket."""
    strokes = [_detail(fig, fig.I(fig.F("pelvis", [(0.30, band_y + 0.01), (0.22, band_y + 0.16), (0.12, band_y + 0.26)])),
                       dark, 0.5)]
    g = fig.geo["limbs"][("leg", "right")]
    seam = np.array([limb_point(g, L) for L in np.linspace(0.06, cut["end"] - 0.04, 12)])
    strokes.append(_detail(fig, seam, dark, 0.35))
    if kind == "jeans":
        strokes.append(_detail(fig, fig.I(fig.F("pelvis", [(-0.38, band_y + 0.22), (-0.50, band_y + 0.30), (-0.52, band_y + 0.50)])),
                               dark, 0.45))
    return strokes


def _seat_details(fig, kind, band_y, dark):
    """Trousers from behind: the seam down the seat; jeans add a yoke and two patch pockets, slacks two welts."""
    strokes = [_detail(fig, fig.I(fig.F("pelvis", [(0.0, band_y), (0.0, -0.05), (0.0, 0.30)])), dark, 0.45)]
    if kind == "jeans":
        yoke = fig.F("pelvis", [(-0.95, band_y + 0.10), (0.0, band_y + 0.22), (0.95, band_y + 0.10)])
        strokes.append(_detail(fig, fig.I(yoke), dark, 0.45))
        for sd in (-1, 1):
            y0 = band_y + 0.26
            pocket = fig.F("pelvis", [(sd * 0.16, y0), (sd * 0.62, y0 - 0.03), (sd * 0.60, y0 + 0.30), (sd * 0.40, y0 + 0.38),
                                      (sd * 0.19, y0 + 0.31), (sd * 0.16, y0)])
            strokes.append(_detail(fig, fig.I(pocket), dark, 0.55))
            stitch = fig.F("pelvis", [(sd * 0.21, y0 + 0.05), (sd * 0.57, y0 + 0.02)])
            strokes.append(_detail(fig, fig.I(stitch), "#d9a04a", 0.6, 0.9))
    else:
        for sd in (-1, 1):
            welt = fig.F("pelvis", [(sd * 0.22, band_y + 0.20), (sd * 0.56, band_y + 0.18)])
            strokes.append(_detail(fig, fig.I(welt), dark, 0.5))
    return strokes


def dress(fig, under):
    """All the garments of FigureSpec.upper / .lower, in wearing order. Sleeves are added by Figure._arm."""
    s = fig.s
    top = top_body(fig, s.upper, s.cloth, under) if s.upper else []
    bottom_parts = bottom(fig, s.lower, s.cloth2 or "#2f3d5c", under) if s.lower else []
    if s.upper and TOP_CUT[s.upper]["tucked"]:
        return top + bottom_parts
    return bottom_parts + top
