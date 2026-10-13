"""Clothes for the full figure.

Fitted clothes are cut out of the body itself: a garment is the part of the body
mask that falls inside a region, grown by a hair so the cloth sits on top of the
skin. Only the necklines and hems have to be designed. Loose pieces such as a
skirt are their own shapes hung from the waist.

Each function has the signature expected by draw_figure(dress=...) and returns
the mask of what it drew.
"""
import numpy as np
from scipy import ndimage

from .. import geometry as geo
from .. import shading as sh
from ..color import rgb, shadow_of
from ..styles import cast_softness_px, line_color, shade_form

FAR = 3.0                    # region corners this far out are beyond any body
CLOTH_THICKNESS = 0.012      # how far cloth stands off the skin, in head heights
LINE_WIDTH = 0.022
FOOT_DISCS = 6               # discs laid along a turned foot to keep trousers off it


DRAPE_FROM = 0.50            # chest y of the armpits: cloth hangs only from what lies below them
DRAPE_PULL = 0.40            # hanging cloth draws back toward the body by this much per unit of fall
DRAPE_STEPS = 16


def hang(painting, skeleton, mask, reach):
    """`mask` with cloth falling from every wider part above, drawing back in as it falls.

    A loose top hangs from the bust and the ribcage over the hollow of the waist, and slopes
    back toward the body below. Rows above the armpits are left out, so the shoulders never make it boxy.
    """
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    armpits = skeleton.on_chest([(0.0, DRAPE_FROM)])[0][1]
    source = (mask * (rows >= armpits)).astype(np.float32)
    fallen = source.copy()
    for drop in np.linspace(0.0, skeleton.px(reach), DRAPE_STEPS + 1)[1:]:
        lowered = sh.shift(source, 0, drop)
        pull = int(drop * DRAPE_PULL)
        if pull > 0:
            lowered = ndimage.minimum_filter1d(lowered, size=2 * pull + 1, axis=1, mode="constant")
        fallen = np.maximum(fallen, lowered)
    return np.maximum(mask, sh.smoothstep(0.3, 0.6, sh.blur(fallen, skeleton.px(0.03))))


def fitted(painting, skeleton, body_mask, region, color, style, light, bevel=0.17, ease=0.0, drape=0.0, cut=None):
    """Cloth that follows the body inside `region` (closed pixel curve, or a list of curves joined). Returns its mask.

    ease: extra room in head heights; 0 is skin-tight, about 0.05 is a straight-leg jean.
    drape: head heights over which loose cloth falls straight from a wider part above (see hang).
    cut: optional mask taken out of the garment, such as the open front of a jacket.
    """
    if drape > 0:
        body_mask = hang(painting, skeleton, body_mask, drape)
    grown = sh.smoothstep(0.25, 0.45, sh.blur(body_mask, skeleton.px(CLOTH_THICKNESS)))
    if ease > 0:                 # loose cloth stands off the body by a fixed distance, so grow by distance
        distance = ndimage.distance_transform_edt(body_mask < 0.5)
        # over the shoulders the cloth hangs from the body, so it only stands off from the armpits down
        rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
        shoulders, armpits = skeleton.on_chest([(0.0, 0.0), (0.0, DRAPE_FROM)])[:, 1]
        reach = skeleton.px(ease) * sh.smoothstep(shoulders, armpits, rows) + skeleton.px(CLOTH_THICKNESS)
        grown = np.maximum(grown, np.clip(reach + 0.5 - distance, 0.0, 1.0).astype(np.float32))
    cloth = _region_mask(painting, region) * np.maximum(grown, body_mask)
    height = None
    if cut is not None:          # shade the garment whole: the edge of an opening is no edge of the form
        height = sh.inflate(cloth, skeleton.px(bevel))
        cloth = cloth * (1.0 - cut)
    painting.part(cloth, color)
    shade_form(painting, cloth, color, style, light, bevel=skeleton.px(bevel), threshold=style.shadow_threshold - 0.08,
               height=height)
    if style.line_width > 0:
        painting.outline_mask(cloth, skeleton.px(LINE_WIDTH) * style.line_width, line_color(style, color))
    return cloth


def _region_mask(painting, region):
    """Coverage of one closed pixel curve, or of several joined."""
    if isinstance(region, (list, tuple)):
        return np.maximum.reduce([painting.mask(curve) for curve in region])
    return painting.mask(region)


NECKLINE_CORNERS = (3, 4, 9, 10)     # the four strap corners stay sharp
STRAP_TOP = -0.06            # chest y where a strap crosses the shoulder
BACK_EDGE = 0.56             # chest y of a strapped top's edge across the back
BACK_STRAP_ROWS = 12         # stations down each back strap
BACK_STRAP_SEEN = 0.5        # a back strap is drawn once some point on it faces the viewer this squarely


def _neckline(skeleton, strap=0.30, depth=0.56):
    """Scoop neckline with shoulder straps and rounded armholes, left to right, in pixels."""
    return skeleton.on_chest([(-FAR, BACK_EDGE), (-strap - 0.34, 0.50), (-strap - 0.17, 0.24), (-strap - 0.10, STRAP_TOP),
                              (-strap + 0.02, STRAP_TOP), (-strap + 0.07, 0.34), (-0.12, depth), (0.12, depth),
                              (strap - 0.07, 0.34), (strap - 0.02, STRAP_TOP), (strap + 0.10, STRAP_TOP),
                              (strap + 0.17, 0.24), (strap + 0.34, 0.50), (FAR, BACK_EDGE)])


def _back_straps(skeleton, strap=0.30):
    """Closed pixel curves of the straps running down the back from the shoulders, on a turned body.

    The neckline only cuts the front of each strap. Seen from the side, a strap has to carry on over
    the shoulder and down the back, or its top reads as a flag stuck on the shoulder.
    Each strap keeps its distance from the spine as it goes down: `lateral` is the across-the-body
    position (as seen from the front) of its two edges. Empty in a front or back view.
    """
    from .body import SPINE_LOWER, SPINE_UPPER, trunk_section
    if skeleton.yaw == 0.0 or skeleton.pose.view == "back":
        return []
    rows = np.linspace(STRAP_TOP, BACK_EDGE + 0.04, BACK_STRAP_ROWS)
    width, _, _ = trunk_section(skeleton.body, SPINE_LOWER + SPINE_UPPER - rows)
    curves = []
    for sign in (1.0, -1.0):
        edges = []
        for lateral in (strap - 0.02, strap + 0.08):
            turn = np.arccos(np.clip(lateral / width, -1.0, 1.0))     # round from the side; the back mirrors the front
            edges.append(np.column_stack([sign * width * (1.0 + turn), rows]))
        outline = np.vstack([edges[0], edges[1][::-1]])
        if skeleton.wrap("chest", outline)[1].max() >= BACK_STRAP_SEEN:
            curves.append(skeleton.on_chest(outline))
    return curves


def _leg_openings(skeleton, front, corner, low):
    """Leg openings as one boundary, screen right to left: `front` (x, y) points across the front.

    A front view only needs the corners at pelvis y `corner`. A turned body shows the back too, so
    there the boundary runs on round the side and under the buttocks at pelvis y `low`.
    x past the body's half-width counts on round the side: hip + hip * pi/2 is the middle of the back.
    """
    if skeleton.yaw == 0.0:
        right = [(FAR, corner)]
    else:
        side = skeleton.body.hip
        right = [(FAR, low), (side * (1.0 + np.pi / 2), low), (side * 1.4, (low + corner) / 2)]
    return right + list(front) + [(-x, y) for x, y in right[::-1]]


def _beyond(painting, skeleton, side, length, softness=0.02):
    """1 past the line across the thigh `length` head heights from the hip joint, along the thigh as seen."""
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    cols = np.arange(painting.shape[1], dtype=np.float32)[None, :]
    hip, knee = skeleton._local[f"hip_{side}"], skeleton._local[f"knee_{side}"]
    along = (knee - hip) / max(np.linalg.norm(knee - hip), 1e-9)
    cut = skeleton.to_pixels(skeleton.project(hip + along * length))[0]
    seen = skeleton.joints[f"knee_{side}"] - skeleton.joints[f"hip_{side}"]
    seen = seen / max(np.linalg.norm(seen), 1e-9)
    past = (cols - cut[0]) * seen[0] + (rows - cut[1]) * seen[1]
    return sh.smoothstep(-skeleton.px(softness), skeleton.px(softness), past)


def covered_thighs(painting, skeleton, masks, length):
    """Seated: each thigh from the hip joint to `length` head heights along it."""
    return np.maximum.reduce([masks["limbs"][f"thigh_{side}"] * (1.0 - _beyond(painting, skeleton, side, length))
                              for side in ("l", "r")])


def leg_cut(painting, skeleton, masks, length):
    """Seated: the leg the garment leaves bare, everything past `length` head heights along each thigh.

    A seated thigh runs forward, so a leg opening drawn at a height below the hips would never cross
    it; garments cut seated legs across the thigh instead.
    """
    legs = np.maximum(masks["limbs"]["leg_l"], masks["limbs"]["leg_r"])
    legs = sh.smoothstep(0.1, 0.3, sh.blur(legs, skeleton.px(0.03)))        # takes in the fill where the legs fused
    return legs * (1.0 - covered_thighs(painting, skeleton, masks, length))


def bottom_region(painting, skeleton, masks, top, hem, length):
    """(region, body mask) for a garment over the hips.

    Standing, the leg openings follow `hem` (pixels, right to left). Seated, the region runs on down and
    the legs are cut across the thigh `length` head heights from the hip joints (see leg_cut).
    """
    if skeleton.seated <= 0.5:
        return np.vstack([top, hem]), masks["skin"]
    region = np.vstack([top, skeleton.to_pixels([(FAR * 3, 20.0), (-FAR * 3, 20.0)])])
    return region, masks["skin"] * (1.0 - leg_cut(painting, skeleton, masks, length))


SKIRT_FALL = 0.30            # seated, how far a skirt hangs down past the thighs
SKIRT_FALL_FROM = 0.35       # the stretch of thigh (head heights back from the hem) whose cloth falls
SKIRT_BRIDGE = 0.30          # seated, the skirt spans gaps narrower than this between the thighs and hips


def _closing(mask, radius):
    """Morphological closing (pixels): fills gaps and notches narrower than 2 * radius."""
    grown = ndimage.distance_transform_edt(mask < 0.5) <= radius
    return (ndimage.distance_transform_edt(grown) > radius).astype(np.float32)


def seated_skirt(painting, skeleton, masks, length, ease=0.03):
    """Mask of a skirt on a seated figure: over the hips and seat, along the thighs to `length`, hanging past it."""
    thighs = covered_thighs(painting, skeleton, masks, length)
    span = _closing(np.maximum(masks["trunk"], thighs), skeleton.px(SKIRT_BRIDGE))
    near_hem = np.maximum.reduce([_beyond(painting, skeleton, side, max(length - SKIRT_FALL_FROM, 0.0)) for side in ("l", "r")])
    edge = span * near_hem
    fallen = edge.copy()
    for drop in np.linspace(0.0, skeleton.px(SKIRT_FALL), 9)[1:]:
        fallen = np.maximum(fallen, sh.shift(edge, 0, drop))
    body = np.maximum(span, sh.smoothstep(0.3, 0.6, sh.blur(fallen, skeleton.px(0.03))))
    distance = ndimage.distance_transform_edt(body < 0.5)
    return np.maximum(body, np.clip(skeleton.px(ease) + 0.5 - distance, 0.0, 1.0)).astype(np.float32)


def swimsuit(painting, skeleton, masks, spec, style, light):
    """One-piece with a scoop neck and high-cut legs."""
    top = _neckline(skeleton)
    legs = skeleton.on_pelvis(_leg_openings(skeleton, [(0.62, -0.22), (0.40, 0.10), (0.16, 0.40), (0.0, 0.50),
                                                       (-0.16, 0.40), (-0.40, 0.10), (-0.62, -0.22)], -0.30, 0.34))
    region, body = bottom_region(painting, skeleton, masks, geo.smooth(top, corners=NECKLINE_CORNERS), geo.smooth(legs), 0.12)
    return fitted(painting, skeleton, body, [region] + _back_straps(skeleton), spec.cloth, style, light)


def jeans(painting, skeleton, masks, spec, style, light, rise=0.10, color=None, ease=0.0, legs=None):
    """Trousers (spec.cloth_second) from the waist to the ankles. rise: waistband below the waist; ease: looseness.

    legs: optional extra mask the trouser legs fill (straight-cut legs, see clothing.trouser_legs).
    """
    color = color or spec.cloth_second
    waistband = skeleton.on_waist([(-FAR, rise - 0.04), (0.0, rise), (FAR, rise - 0.04)])
    region = np.vstack([geo.smooth(waistband), skeleton.to_pixels([(FAR, 20.0), (-FAR, 20.0)])])
    body = masks["skin"] if legs is None else np.maximum(masks["skin"], legs)
    cloth = fitted(painting, skeleton, body * (1.0 - _feet(painting, skeleton)), region, color, style, light, ease=ease)
    if ease > 0:                 # loose cloth breaks into a few folds behind the knee and over the shoe
        cloth_shadow = shadow_of(color, style.shadow_tint, style.shadow_depth)
        for side in ("l", "r"):
            knee, ankle = skeleton.joints[f"knee_{side}"], skeleton.joints[f"ankle_{side}"]
            for share, size in ((0.0, 0.16), (0.82, 0.12), (0.92, 0.10)):
                center = geo.lerp(knee, ankle, share)
                fold = geo.bent_line(center - [skeleton.px(size), 0.0], center + [skeleton.px(size), skeleton.px(0.02)], 0.25)
                painting.stroke(fold, skeleton.px(0.024), cloth_shadow, taper=(0.5, 0.5), opacity=0.5, layer="color", clip=cloth)
    leg_split(painting, skeleton, masks, cloth, color, style)
    if style.line_width > 0:     # fly and pocket seams
        ink = line_color(style, color)
        width = skeleton.px(LINE_WIDTH) * style.line_width * 0.7
        painting.stroke(skeleton.on_pelvis([(0.0, -0.36), (0.01, 0.36)]), width, ink, taper=(0.1, 0.3), clip=cloth)
        hip = skeleton.body.hip
        for sign in (1.0, -1.0):
            pocket = geo.smooth(skeleton.on_pelvis([(sign * 0.20, -0.40), (sign * 0.30, -0.22), (sign * (hip - 0.20), -0.16)]))
            painting.stroke(pocket, width, ink, taper=(0.1, 0.3), clip=cloth)
    return cloth


def leg_split(painting, skeleton, masks, cloth, color, style, start=0.45):
    """On a turned body, the line where the near leg of a garment passes in front of the far one.

    Cloth painted over both legs hides the outline of the near leg; without this line shorts and
    trousers seen at an angle read as a skirt.
    """
    leg = skeleton.front_leg
    if style.line_width <= 0:
        return
    if skeleton.seated > 0.5 and abs(skeleton.pose.yaw) <= 22.0:
        # seated, seen from the front: the knee ends of both thighs over the shins
        inside = ndimage.distance_transform_edt(cloth > 0.5) > skeleton.px(0.03)
        for side in ("l", "r"):
            painting.outline_mask(masks["limbs"][f"thigh_{side}"], skeleton.px(LINE_WIDTH) * style.line_width * 0.8,
                                  line_color(style, color), keep=inside * (1.0 - masks["trunk"]))
        return
    if skeleton.yaw == 0.0 or not leg:
        return
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    top = skeleton.on_pelvis([(0.0, start - 0.15)])[0][1]           # start: pelvis y where the line is fully in
    inside = ndimage.distance_transform_edt(cloth > 0.5) > skeleton.px(0.03)
    keep = inside * sh.smoothstep(top, top + skeleton.px(0.15), rows)
    painting.outline_mask(masks["limbs"][leg], skeleton.px(LINE_WIDTH) * style.line_width * 0.8,
                          line_color(style, color), keep=keep)


def top_and_jeans(painting, skeleton, masks, spec, style, light):
    """Sleeveless top (spec.cloth) tucked into close-fitting trousers (spec.cloth_second)."""
    waistband = skeleton.on_waist([(-FAR, 0.06), (0.0, 0.10), (FAR, 0.06)])
    top_region = np.vstack([geo.smooth(_neckline(skeleton, strap=0.33, depth=0.40), corners=NECKLINE_CORNERS),
                            geo.smooth(waistband)[::-1] + [0.0, skeleton.px(0.04)]])
    top = fitted(painting, skeleton, masks["trunk"], [top_region] + _back_straps(skeleton, strap=0.33), spec.cloth, style, light)
    return np.maximum(top, jeans(painting, skeleton, masks, spec, style, light))


def trunks(painting, skeleton, masks, spec, style, light, hem=0.55):
    """Close-fitting short trunks (spec.cloth) with a contrasting waistband (spec.cloth_second).

    hem: leg opening below the hip joints, in head heights. Also the cover for a man's figure study.
    """
    top = skeleton.on_pelvis([(-FAR, -0.12), (0.0, -0.06), (FAR, -0.12)])
    # each leg opening rises toward the inner thigh, so the hem never reads as one straight box edge
    low = skeleton.on_pelvis([(FAR, hem + 0.04), (0.30, hem), (0.10, hem - 0.04), (0.0, hem - 0.05),
                              (-0.10, hem - 0.04), (-0.30, hem), (-FAR, hem + 0.04)])
    region, body = bottom_region(painting, skeleton, masks, geo.smooth(top), geo.smooth(low), hem)
    cloth = fitted(painting, skeleton, body, region, spec.cloth, style, light, bevel=0.20)
    band_low = skeleton.on_pelvis([(-FAR, -0.02), (0.0, 0.04), (FAR, -0.02)])
    band = painting.mask(np.vstack([geo.smooth(top), geo.smooth(band_low)[::-1]])) * cloth
    painting.fill(band, spec.cloth_second)
    shade_form(painting, band, spec.cloth_second, style, light, bevel=skeleton.px(0.08))
    cloth_shadow = shadow_of(spec.cloth, style.shadow_tint, style.shadow_depth)
    for sign in (1.0, -1.0):     # soft folds where the cloth pulls toward the lower pelvis
        fold = geo.smooth(skeleton.on_pelvis([(sign * 0.30, 0.05), (sign * 0.16, 0.24), (sign * 0.05, 0.36)]))
        painting.stroke(fold, skeleton.px(0.026), cloth_shadow, taper=(0.5, 0.4), opacity=0.5, layer="color", clip=cloth)
    if style.line_width > 0:
        ink = line_color(style, spec.cloth_second)
        painting.stroke(geo.smooth(band_low), skeleton.px(LINE_WIDTH) * style.line_width * 0.6, ink, taper=(0.0, 0.0), clip=cloth)
    return cloth


def shirtless_jeans(painting, skeleton, masks, spec, style, light):
    """Bare chest, jeans worn low on the hips."""
    return jeans(painting, skeleton, masks, spec, style, light, rise=0.50, ease=0.06)


def _feet(painting, skeleton):
    feet = np.zeros(painting.shape, dtype=np.float32)
    for side in ("l", "r"):
        ankle, toe, knee = (skeleton.joints[f"{name}_{side}"] for name in ("ankle", "toe", "knee"))
        center = ankle + (toe - ankle) * 0.5 + (ankle - knee) * 0.02
        feet = np.maximum(feet, painting.mask(geo.ellipse(center, skeleton.px(0.36), skeleton.px(0.36))))
        if skeleton.yaw != 0.0:        # seen turned, the foot is long: discs all along it, heel to toe
            heel = skeleton.joints[f"heel_{side}"]
            for share in np.linspace(0.0, 1.0, FOOT_DISCS):
                center = geo.lerp(heel, toe, share)
                feet = np.maximum(feet, painting.mask(geo.ellipse(center, skeleton.px(0.24), skeleton.px(0.24))))
    return feet


def slip_dress(painting, skeleton, masks, spec, style, light, hem=1.25, flare=0.26):
    """Thin-strapped dress: fitted bodice, skirt flaring from the hips. hem: length below the hip joints."""
    body = skeleton.body
    cloth = rgb(spec.cloth)
    cloth_shadow = shadow_of(cloth, style.shadow_tint, style.shadow_depth)
    hip_line = skeleton.on_pelvis([(-FAR, 0.30), (FAR, 0.30)])       # the bodice runs well under the skirt top
    bodice_region = np.vstack([geo.smooth(_neckline(skeleton, strap=0.30, depth=0.58), corners=NECKLINE_CORNERS), hip_line[::-1]])
    # skirt: hangs from the hips, wider at the hem, with a gently waving edge
    rng = np.random.default_rng(spec.seed)
    hem_x = np.linspace(-(body.hip + flare), body.hip + flare, 9)
    hem_y = hem + 0.035 * np.sin(np.linspace(0, 4 * np.pi, 9) + rng.uniform(0, 6.28)) + 0.03 * (hem_x / (body.hip + flare)) ** 2
    skirt_pts = [(-(body.hip - 0.10), -0.34), (-(body.hip + 0.05), -0.02), (-(body.hip + flare * 0.6), hem * 0.55)] + \
                list(zip(hem_x, hem_y)) + \
                [((body.hip + flare * 0.6), hem * 0.55), ((body.hip + 0.05), -0.02), ((body.hip - 0.10), -0.34)]
    seated = skeleton.seated > 0.5
    if seated:                     # the skirt lies along the thighs and hangs past the knees
        waist_down = painting.mask(np.vstack([skeleton.on_pelvis([(-FAR, -0.34), (FAR, -0.34)]),
                                              skeleton.to_pixels([(FAR * 3, 20.0), (-FAR * 3, 20.0)])]))
        skirt = seated_skirt(painting, skeleton, masks, hem * 1.2, ease=0.05) * waist_down
    elif skeleton.yaw == 0.0:
        skirt_curve = geo.smooth(skeleton.on_pelvis(skirt_pts), closed=True, corners=(0, 3, 11, len(skirt_pts) - 1))
        hem_points = skeleton.on_pelvis(list(zip(hem_x, hem_y)))
        skirt = painting.mask(skirt_curve)
    else:
        skirt_curve, hem_points = _turned_skirt(skeleton, [y for _, y in skirt_pts[:3]] + [hem],
                                                [abs(x) for x, _ in skirt_pts[:3]] + [body.hip + flare], hem_y - hem)
        skirt = painting.mask(skirt_curve)
    soft = cast_softness_px(style, painting)
    painting.fill(sh.cast_shadow(skirt, masks["skin"], (skeleton.px(0.02), skeleton.px(0.07)), soft) * (1.0 - skirt),
                  shadow_of(spec.skin, (0.93, 0.77, 0.79), style.shadow_depth), 0.85)
    grown = sh.smoothstep(0.25, 0.45, sh.blur(masks["trunk"], skeleton.px(CLOTH_THICKNESS)))
    bodice = _region_mask(painting, [bodice_region] + _back_straps(skeleton, strap=0.30)) * np.maximum(grown, masks["trunk"])
    dress = np.maximum(skirt, bodice)
    painting.part(dress, cloth)
    shade_form(painting, dress, cloth, style, light, bevel=skeleton.px(0.20), threshold=style.shadow_threshold - 0.05)
    # folds fan out from the hips toward the hem
    hips = skeleton.on_pelvis([(0.0, -0.05)])[0]
    for index in () if seated else (1, 2, 4, 6, 7):
        if skeleton.yaw == 0.0:
            start = skeleton.on_pelvis([(hem_x[index] * 0.45, -0.05 + 0.1 * abs(hem_x[index]))])[0]
        else:                      # on a turned skirt the folds rise from the hips straight above their hem point
            start = np.array([geo.lerp(hips[0], hem_points[index][0], 0.55), hips[1] + skeleton.px(0.10)])
        fold = geo.lock(start + [-skeleton.px(0.015), 0], start + [skeleton.px(0.015), 0],
                        hem_points[index] + [skeleton.px(0.03), 0], bend=0.03 * np.sign(hem_x[index]), belly=1.2)
        painting.fill(painting.mask(fold) * dress, cloth_shadow, 0.55)
    if style.line_width > 0:
        painting.outline_mask(dress, skeleton.px(LINE_WIDTH) * style.line_width, line_color(style, cloth))
    return dress


SKIRT_ROWS = 24
SKIRT_SEAT = (0.17, -0.12, 0.30)     # extra room behind for the buttocks: amount, height, spread (head heights)
HEM_SAG = 0.04                       # seen from a little above, the front of a hem hangs lower than its sides


def _turned_skirt(skeleton, ys, widths, wave):
    """Outline and hem points (pixels) of a skirt on a turned body: a flared shell round the hips and thighs.

    ys, widths: pelvis y and half-width of the skirt's front-view outline, top to hem.
    wave: the hem's up-and-down ripple at its sample points.
    """
    from .body import section_extremes, trunk_frame, trunk_section, wrapped_outline
    rows = np.linspace(ys[0], ys[-1], SKIRT_ROWS)
    half = np.interp(rows, ys, widths)
    heights = -rows
    trunk_width, _, _ = trunk_section(skeleton.body, heights)
    standoff = np.maximum(half - trunk_width, 0.02)
    amount, middle, spread = SKIRT_SEAT
    seat = amount * np.exp(-((heights - middle) / spread) ** 2)
    right, left = wrapped_outline(skeleton, heights, half, standoff, seat)
    # the hem: the visible arc of its section, from the right silhouette round the front to the left
    hem_height = heights[-1:]
    _, front, back = trunk_section(skeleton.body, hem_height)
    front, back = front + standoff[-1], back + standoff[-1] + seat[-1]
    centre, tilt = trunk_frame(skeleton, hem_height)
    first, last = section_extremes(half[-1:], front, back, np.radians(tilt), skeleton.yaw)
    angles = np.linspace(first[0], last[0], len(wave))
    depth = np.where(np.sin(angles) >= 0, front[0], back[0]) * np.sin(angles)
    across = np.array([np.cos(np.radians(tilt[0])), np.sin(np.radians(tilt[0])), 0.0])
    ring = centre[0] + across * (half[-1] * np.cos(angles))[:, None] + np.column_stack([np.zeros((len(angles), 2)), depth])
    hem = skeleton.project(ring) + np.column_stack([np.zeros(len(angles)), wave + HEM_SAG * np.clip(np.sin(angles), 0.0, 1.0)])
    outline = np.vstack([right, hem, left[::-1]])
    curve = geo.smooth(skeleton.to_pixels(outline), closed=True, corners=(len(right) - 1, len(right) + len(hem)))
    return curve, skeleton.to_pixels(hem)


def bikini(painting, skeleton, masks, spec, style, light):
    """Two-piece: triangle cups on thin strings, low-rise brief."""
    from . import anatomy
    cloth = rgb(spec.cloth)
    ink = line_color(style, cloth)
    string = skeleton.px(0.016)
    total = np.zeros(painting.shape, dtype=np.float32)
    neck = skeleton.on_chest([(0.0, -0.16)])[0]
    for sign, center, radius, _ in anatomy.breast_shapes(skeleton):
        cup = geo.smooth([center + [-sign * radius * 0.10, -radius * 1.25], center + [sign * radius * 1.08, radius * 0.30],
                          center + [sign * radius * 0.85, radius * 1.02], center + [-sign * radius * 0.95, radius * 1.02],
                          center + [-sign * radius * 0.90, radius * 0.25]], closed=True, corners=(0, 2, 3))
        total = np.maximum(total, fitted(painting, skeleton, masks["skin"], cup, cloth, style, light, bevel=0.10))
        tie = geo.bent_line(center + [-sign * radius * 0.10, -radius * 1.2], neck + [sign * skeleton.px(0.11), 0], 0.06 * sign)
        painting.stroke(tie, string, cloth, taper=(0.0, 0.0), layer="color", clip=masks["skin"])
    band = skeleton.on_chest([(-0.6, 0.98), (0.0, 1.02), (0.6, 0.98)], surface=True)
    painting.stroke(geo.smooth(band), string, cloth, taper=(0.0, 0.0), layer="color", clip=masks["trunk"])
    top = skeleton.on_pelvis([(-FAR, -0.02), (-0.50, -0.06), (0.0, 0.08), (0.50, -0.06), (FAR, -0.02)])
    legs = skeleton.on_pelvis(_leg_openings(skeleton, [(0.60, 0.00), (0.36, 0.20), (0.14, 0.42), (0.0, 0.50),
                                                       (-0.14, 0.42), (-0.36, 0.20), (-0.60, 0.00)], 0.0, 0.26))
    region, body = bottom_region(painting, skeleton, masks, geo.smooth(top), geo.smooth(legs), 0.12)
    brief = fitted(painting, skeleton, body, region, cloth, style, light)
    if style.line_width > 0:
        for sign in (1.0, -1.0):       # side ties, where that hip is in view
            spot = [(sign * (skeleton.body.hip - 0.02), -0.03)]
            if skeleton.visibility("pelvis", spot)[0] < 0.3:
                continue
            knot = skeleton.on_pelvis(spot)[0]
            for angle in (0.5, 1.1):
                end = knot + skeleton.px(0.16) * np.array([sign * np.sin(angle), np.cos(angle)])
                painting.stroke(geo.bent_line(knot, end, 0.2 * sign), string * 0.9, ink, taper=(0.0, 0.6))
    return np.maximum(total, brief)


def _span_rows(mask):
    """Fill every row between its leftmost and rightmost covered pixel: cloth stretched from leg to leg."""
    inside = mask > 0.5
    from_left = np.maximum.accumulate(inside, axis=1)
    from_right = np.maximum.accumulate(inside[:, ::-1], axis=1)[:, ::-1]
    return (from_left & from_right).astype(np.float32)


def bodycon(painting, skeleton, masks, spec, style, light, hem=0.95):
    """Close-fitting strap dress ending on the thighs. hem: length below the hip joints, in head heights."""
    top = _neckline(skeleton, strap=0.31, depth=0.66)
    low = skeleton.on_pelvis([(FAR, hem - 0.03), (0.0, hem), (-FAR, hem - 0.03)])
    region = np.vstack([geo.smooth(top, corners=NECKLINE_CORNERS), geo.smooth(low)])
    if skeleton.seated > 0.5:
        region = np.vstack([geo.smooth(top, corners=NECKLINE_CORNERS), skeleton.to_pixels([(FAR * 3, 20.0), (-FAR * 3, 20.0)])])
        body = np.maximum(masks["trunk"], seated_skirt(painting, skeleton, masks, hem, ease=0.0))
    else:
        # A skirt does not follow each leg: below the hips the cloth spans straight across from thigh to thigh.
        below_hips = painting.mask(np.vstack([skeleton.on_pelvis([(-FAR, 0.25), (FAR, 0.25)]), geo.smooth(low)]))
        body = np.maximum(masks["skin"], _span_rows(masks["skin"] * below_hips) * below_hips)
    dress = fitted(painting, skeleton, body, [region] + _back_straps(skeleton, strap=0.31), spec.cloth, style, light)
    cloth_shadow = shadow_of(spec.cloth, style.shadow_tint, style.shadow_depth)
    for y in (-0.62, -0.50, 0.10, 0.22, 0.60):      # stretch creases at the waist, across the hips and thighs
        crease = geo.smooth(skeleton.on_pelvis([(-0.34, y + 0.03), (0.0, y), (0.34, y + 0.03)]))
        painting.stroke(crease, skeleton.px(0.030), cloth_shadow, taper=(0.45, 0.45), opacity=0.45, layer="color", clip=dress)
    return dress


WARDROBE = {"swimsuit": swimsuit, "bikini": bikini, "top_and_jeans": top_and_jeans, "slip_dress": slip_dress,
            "bodycon": bodycon, "trunks": trunks, "shirtless_jeans": shirtless_jeans}

# Layered garments (sleeves, shoes, lace) live in clothing.py and register here.
from . import clothing as _clothing  # noqa: E402  (needs the helpers above)

WARDROBE.update(_clothing.OUTFITS)
