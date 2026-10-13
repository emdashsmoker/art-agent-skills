"""Layered clothes: sleeves, shoes, lace and the garments built from them.

A garment for draw_figure(dress=...) is a plain function (the body layer, drawn over the trunk
and legs) or an Outfit, which may add two more layers:

- behind: drawn right after the back hair, before the body (a hood lying on the back);
- sleeve: drawn over each arm right after that arm (sleeves, cuffs).

combine() stacks garments into one Outfit, drawn in the order given, so tops and bottoms mix freely:
    combine(jeans, sneakers, HOODIE)
"""
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import ndimage

from .. import geometry as geo
from .. import shading as sh
from ..color import light_of, mix, rgb, shadow_of
from ..styles import cast_softness_px, line_color, shade_form
from .wardrobe import FAR, LINE_WIDTH, _feet, _leg_openings, bottom_region, covered_thighs, fitted, jeans, leg_split

LACE_ALPHA = 0.55            # lace lets this much of its colour through over skin
SCALLOP_SPACING = 0.05       # head heights between scallops on a lace edge
LACE_DOTS = 3                # mesh dots per scallop
SLEEVE_EASE = {"fitted": 0.015, "loose": 0.032, "tailored": 0.026}
SLEEVE_SHADOW = 0.035        # how far down the arm the shadow under a sleeve hem reaches
SEAM_OPACITY = 0.45          # the armhole seam keeps this much of the sleeve outline where it crosses the garment
CUFF_ROOM = 0.012            # room left round the wrist inside a gathered cuff
SHOULDER_SNUG = 0.45         # share of the upper arm over which a sleeve grows from snug at the shoulder to its full ease
CLOTH_ROOM = 0.008           # the least room a sleeve keeps, so it still sits on top of the arm
SHIRT = "#f2f1ec"
TIE = "#7a1f2b"
DRESS_SHOE = "#2a1f1c"
SNEAKER = "#ebe8e1"
SEATED_TOP_LAP = 0.30        # seated, head heights past its hem that a top reaching the hips lies along the thighs
RIB_DEPTH = 0.12             # depth of a ribbed hem band, head heights
BACK_NECKLINE = -0.10        # chest y of a top's neckline at the back of the neck
TROUSER_GAP = 0.05           # head heights within which two trouser legs count as touching
SEATED_FRONT_YAW = 22.0      # degrees of turn up to which a seated figure is seen from the front (as in wardrobe.leg_split)
HOOD_SIZE = (0.40, 0.36)     # half-width and depth of the folded hood round the back of the neck
HOOD_RINGS = ((0.08, 1.0), (-0.10, 0.95), (-0.24, 0.62))   # (chest y, size): it lies on the shoulders, half way up the neck


def _zeros(painting):
    return np.zeros(painting.shape, dtype=np.float32)


def _turned(skeleton, vector):
    """A direction given for an upright figure (x right, y down), turned with the figure's lean."""
    angle = np.radians(skeleton.pose.lean)
    x, y = vector
    return np.array([x * np.cos(angle) - y * np.sin(angle), x * np.sin(angle) + y * np.cos(angle)])


@dataclass
class Outfit:
    body: Optional[Callable] = None      # f(painting, skeleton, masks, spec, style, light) -> mask
    sleeve: Optional[Callable] = None    # f(painting, skeleton, side, masks, spec, style, light) -> mask
    behind: Optional[Callable] = None    # f(painting, skeleton, masks, spec, style, light) -> mask

    def __call__(self, painting, skeleton, masks, spec, style, light):
        if self.body is None:
            return _zeros(painting)
        return self.body(painting, skeleton, masks, spec, style, light)


def combine(*garments):
    """One Outfit from several garments, drawn in the order given (trousers before a jacket)."""
    parts = [garment if isinstance(garment, Outfit) else Outfit(body=garment) for garment in garments]

    def body(painting, skeleton, masks, spec, style, light):
        return np.maximum.reduce([_zeros(painting)] + [part(painting, skeleton, masks, spec, style, light) for part in parts])

    def stacked(name):
        layers = [getattr(part, name) for part in parts if getattr(part, name) is not None]
        if not layers:
            return None

        def run(painting, *args):
            return np.maximum.reduce([_zeros(painting)] + [layer(painting, *args) for layer in layers])
        return run

    return Outfit(body=body, sleeve=stacked("sleeve"), behind=stacked("behind"))


# ---- building blocks -------------------------------------------------------------------
def _ink(style, color):
    return line_color(style, rgb(color))


def _line(skeleton, style, scale=1.0):
    return skeleton.px(LINE_WIDTH) * style.line_width * scale


def _cloth(painting, skeleton, mask, color, style, light, bevel=0.12, line=1.0):
    """Fill, shade and outline one piece of cloth. Returns the lambert map of its shading."""
    color = rgb(color)
    painting.part(mask, color)
    lit = shade_form(painting, mask, color, style, light, bevel=skeleton.px(bevel), threshold=style.shadow_threshold - 0.06)
    if style.line_width > 0 and line > 0:
        painting.outline_mask(mask, _line(skeleton, style, line), _ink(style, color))
    return lit


def lace_edge(painting, skeleton, edge, color, style, clip, toward=(0.0, -1.0), depth=0.05):
    """Sheer lace strip running from a pixel polyline `edge` toward `toward`, scalloped along its far side.

    Returns the strip mask (clipped).
    """
    edge = geo.as_points(edge)
    count = max(int(geo.path_length(edge) / skeleton.px(SCALLOP_SPACING)), 3)
    path = geo.resample(edge, count + 1)
    normal = geo.normals(path)
    if (normal.mean(axis=0) @ np.asarray(toward, dtype=np.float64)) < 0:
        normal = -normal
    reach = skeleton.px(depth)
    outer = path + normal * reach
    strip = painting.mask(np.vstack([path, outer[::-1]])) * clip
    color = rgb(color)
    painting.fill(strip, color, LACE_ALPHA)
    dark = shadow_of(color, style.shadow_tint, 0.8)
    fine = max(skeleton.px(0.006), 0.8)
    rng = np.random.default_rng(count)
    for a, b, n in zip(outer[:-1], outer[1:], normal[:-1]):
        bump = geo.smooth([a, (a + b) / 2 + n * reach * 0.35, b])           # one scallop per gap
        painting.stroke(bump, fine, dark, taper=(0.2, 0.2), opacity=0.85, layer="color", clip=clip)
    for point, n in zip(path[:-1], normal[:-1]):                          # the mesh: fine dots over the strip
        for share in rng.uniform(0.15, 0.9, LACE_DOTS):
            dot = point + n * reach * share + rng.normal(0.0, reach * 0.25, 2)
            painting.stroke(np.array([dot, dot + [fine, 0.0]]), fine * 1.2, dark, taper=(0.0, 0.0), opacity=0.6,
                            layer="color", clip=clip)
    painting.stroke(path, fine * 1.3, dark, taper=(0.0, 0.0), opacity=0.7, layer="color", clip=clip)   # the seam
    return strip


def _arm_axis(skeleton, side, reach):
    """Point and direction along the arm: reach 0 shoulder, 1 elbow, 2 wrist."""
    shoulder, elbow, wrist = (skeleton.joints[f"{name}_{side}"] for name in ("shoulder", "elbow", "wrist"))
    if reach <= 1.0:
        return geo.lerp(shoulder, elbow, reach), elbow - shoulder
    return geo.lerp(elbow, wrist, min(reach - 1.0, 1.0)), wrist - elbow


def sleeve_mask(painting, skeleton, side, reach, ease, gather=0.0):
    """Mask of a sleeve from the shoulder to `reach` (0 shoulder, 1 elbow, 2 wrist).

    ease: room round the arm in head heights. gather: length (in the same reach units) over which
    the end closes in on the wrist, as a ribbed cuff does.
    """
    from .body import FOREARM_FLESH, LIMB_DEPTH, UPPER_ARM_FLESH, _bone_tube
    spans = [("shoulder", "elbow", UPPER_ARM_FLESH, "upper_arm", min(reach, 1.0))]
    if reach > 1.0:
        spans.append(("elbow", "wrist", FOREARM_FLESH, "forearm", min(reach - 1.0, 1.0)))
    per_unit = 1.0 / max(skeleton.body.limb * skeleton.body.arms, 1e-6)    # _bone_tube scales profiles up by this
    pieces = []
    for index, (start, end, flesh, depth_name, share) in enumerate(spans):
        last = index == len(spans) - 1
        stations = len(flesh[0])
        where = np.linspace(0.0, share, stations)
        room = np.full(stations, ease)
        if index == 0:                   # cloth lies snug over the shoulder and opens out down the arm
            room = CLOTH_ROOM + (room - CLOTH_ROOM) * sh.smoothstep(0.0, SHOULDER_SNUG, where)
        if gather > 0 and last:
            close = np.clip((where - (share - gather)) / gather, 0.0, 1.0)
            room = room * (1.0 - close) + CUFF_ROOM * close

        def cut(profile):
            return np.interp(where, np.linspace(0.0, 1.0, len(profile)), profile) + room * per_unit

        depth = LIMB_DEPTH[depth_name]
        joint = f"_sleeve_{side}_{end}"
        skeleton.joints[joint] = geo.lerp(skeleton.joints[f"{start}_{side}"], skeleton.joints[f"{end}_{side}"], share)
        try:
            tube = _bone_tube(skeleton, f"{start}_{side}", joint, (cut(flesh[0]), cut(flesh[1]), flesh[2] * share), side,
                              (cut(depth[0]), cut(depth[1]), depth[2] * share), cap_end=not last)
        finally:
            del skeleton.joints[joint]
        pieces.append(painting.mask(tube))
    return sh.melt(np.maximum.reduce(pieces), skeleton.px(0.02))


def draw_sleeve(painting, skeleton, side, masks, color, style, light, reach, ease, cuff=None, under=None):
    """Sleeve over an arm already drawn. Returns its mask.

    cuff: (length, colour) of a band closing the end of the sleeve (a ribbed hoodie cuff).
    under: (length, colour) of a shirt cuff showing past the end of the sleeve (a suit).
    """
    color = rgb(color)
    covered = _zeros(painting)
    if under is not None:
        length, under_color = under
        shirt = sleeve_mask(painting, skeleton, side, reach + length, SLEEVE_EASE["fitted"], gather=length)
        _cloth(painting, skeleton, shirt, under_color, style, light, bevel=0.05, line=0.8)
        covered = shirt
    gather = cuff[0] if cuff else 0.0
    mask = sleeve_mask(painting, skeleton, side, reach, ease, gather)
    _, along = _arm_axis(skeleton, side, reach)
    direction = along / max(np.linalg.norm(along), 1e-9)
    arm = masks["limbs"][f"arm_{side}"]
    cast = sh.cast_shadow(mask, np.maximum(arm, covered), direction * skeleton.px(SLEEVE_SHADOW), cast_softness_px(style, painting))
    painting.fill(cast * (1.0 - mask), rgb(style.shadow_tint), 0.55 * style.shadow_depth, "multiply")
    painting.part(mask, color)
    lit = shade_form(painting, mask, color, style, light, bevel=skeleton.px(0.12), threshold=style.shadow_threshold - 0.06)
    if cuff:
        length, cuff_color = cuff
        band = mask * (1.0 - sleeve_mask(painting, skeleton, side, reach - length, ease))
        painting.fill(band, cuff_color)
        shadow = sh.shadow_from_light(lit, style.shadow_threshold - 0.06, style.edge_softness) * band
        painting.fill(shadow, shadow_of(cuff_color, style.shadow_tint, style.shadow_depth))
        if style.line_width > 0:
            painting.outline_mask(band, _line(skeleton, style, 0.6), _ink(style, cuff_color), opacity=0.7)
    if style.line_width > 0:
        keep = None
        garment = masks.get("clothes")
        if garment is not None:          # where the sleeve meets the body of the garment, only a faint seam
            shoulder = skeleton.joints[f"shoulder_{side}"]
            disc = painting.mask(geo.ellipse(shoulder, skeleton.px(0.30), skeleton.px(0.30), count=32))
            keep = 1.0 - (1.0 - SEAM_OPACITY) * disc * sh.blur(garment, skeleton.px(0.02))
        painting.outline_mask(mask, _line(skeleton, style), _ink(style, color), keep=keep)
    return np.maximum(mask, covered)


def shoes(painting, skeleton, masks, color, style, light, kind="dress"):
    """Shoes over the feet. kind: "dress" (dark, glossy, thin sole) or "sneaker" (thick pale sole)."""
    color = rgb(color)
    feet = _feet(painting, skeleton)
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    shoe = _zeros(painting)
    for side in ("l", "r"):
        ankle = skeleton.joints[f"ankle_{side}"]
        below = sh.smoothstep(ankle[1] - skeleton.px(0.03), ankle[1] + skeleton.px(0.02), rows)
        shoe = np.maximum(shoe, below * feet * masks["limbs"][f"leg_{side}"])
    shoe = sh.smoothstep(0.2, 0.45, sh.blur(shoe, skeleton.px(0.015)))       # a little bigger than the foot
    lit = _cloth(painting, skeleton, shoe, color, style, light, bevel=0.06)
    sole_height = 0.05 if kind == "sneaker" else 0.022
    sole = shoe * (1.0 - sh.shift(shoe, 0, -skeleton.px(sole_height)))
    painting.fill(sole, "#f6f3ec" if kind == "sneaker" else shadow_of(color, style.shadow_tint, 0.7))
    if kind == "dress":
        painting.fill(sh.smoothstep(0.78, 0.95, lit) * shoe, light_of(color, amount=0.85), 0.75, "screen")
    else:                                     # laces across the instep
        lace = shadow_of(color, style.shadow_tint, 0.9)
        for side in ("l", "r"):
            ankle, toe = skeleton.joints[f"ankle_{side}"], skeleton.joints[f"toe_{side}"]
            along = (toe - ankle) / max(np.linalg.norm(toe - ankle), 1e-9)
            across = np.array([-along[1], along[0]]) * skeleton.px(0.055)
            for share in (0.30, 0.42, 0.54):
                centre = geo.lerp(ankle, toe, share)
                painting.stroke(np.array([centre - across, centre + across]), skeleton.px(0.012), lace, taper=(0.1, 0.1),
                                opacity=0.8, layer="color", clip=shoe)
    return shoe


def dress_shoes(painting, skeleton, masks, spec, style, light):
    return shoes(painting, skeleton, masks, DRESS_SHOE, style, light, kind="dress")


def sneakers(painting, skeleton, masks, spec, style, light):
    return shoes(painting, skeleton, masks, SNEAKER, style, light, kind="sneaker")


def _shoulder_line(skeleton, neck, dip, collar=0.17):
    """Top edge of a top with sleeves, over both shoulders and round the neck, left to right, pixels.

    neck: half-width of the neck opening; dip: chest y of its lowest point in front.
    Seen from behind, the neckline runs across the base of the neck whatever its depth in front.
    """
    if skeleton.pose.view == "back":
        dip = min(dip, BACK_NECKLINE)
    return geo.smooth(skeleton.on_chest([(-FAR, -0.32), (-0.30, -0.15), (-collar, -0.12), (-neck, dip - 0.07),
                                         (0.0, dip), (neck, dip - 0.07), (collar, -0.12), (0.30, -0.15), (FAR, -0.32)]))


def _on_surface(skeleton, frame, corners, closed=True, per_edge=8):
    """Polygon or polyline (pixels) laid on the trunk surface, straight between its corners in frame coordinates.

    Mapping only the corners would join them with straight screen lines that cut through the turn of
    the body; filling in the edges first keeps the shape on the surface (a lapel on a turned chest).
    """
    corners = geo.as_points(corners)
    ends = np.vstack([corners[1:], corners[:1]]) if closed else corners[1:]
    share = np.linspace(0.0, 1.0, per_edge, endpoint=False)[:, None]
    points = np.vstack([a + (b - a) * share for a, b in zip(corners, ends)] + ([] if closed else [corners[-1:]]))
    place = skeleton.on_chest if frame == "chest" else skeleton.on_pelvis
    return place(points, surface=True)


def _upper_body(masks):
    """Trunk with both thighs: what a top that reaches the hips hangs over."""
    return np.maximum.reduce([masks["trunk"], masks["limbs"]["leg_l"], masks["limbs"]["leg_r"]])


def _top_over(painting, skeleton, masks, top, bottom, hem):
    """(region, body) of a top reaching the hips: top and bottom edges in pixels, hem the pelvis y of the bottom one.

    Seated, the thighs run forward at the height of the hem, so a hem line drawn across the body would
    leave the cloth lying along the whole thigh; the top covers the first stretch of each thigh and stops.
    """
    region = np.vstack([top, bottom])
    if skeleton.seated <= 0.5:
        return region, _upper_body(masks)
    return region, np.maximum(masks["trunk"], covered_thighs(painting, skeleton, masks, hem + SEATED_TOP_LAP))


def _seated_hem_band(painting, skeleton, masks, hem, depth):
    """Seated: the strip of a top's hem lying across the thighs, `depth` head heights deep."""
    length = hem + SEATED_TOP_LAP
    return np.clip(covered_thighs(painting, skeleton, masks, length) - covered_thighs(painting, skeleton, masks, length - depth), 0.0, 1.0)


def _hem(skeleton, frame, y, sag=0.03):
    """Hem line right to left at frame y, dipping a little in front."""
    place = skeleton.on_chest if frame == "chest" else skeleton.on_pelvis
    return geo.smooth(place([(FAR, y - sag), (0.0, y), (-FAR, y - sag)]))


# ---- crop tee and hot pants ---------------------------------------------------------------
def crop_tee(painting, skeleton, masks, spec, style, light, hem=1.12):
    """Close-fitting crew-neck tee (spec.cloth) ending above the navel (hem: chest y)."""
    region = np.vstack([_shoulder_line(skeleton, 0.10, 0.06), _hem(skeleton, "chest", hem)])
    tee = fitted(painting, skeleton, masks["trunk"], region, spec.cloth, style, light, ease=0.015, drape=0.35)
    if style.line_width > 0:          # a rib round the neck
        rib = skeleton.on_chest([(-0.13, -0.08), (-0.09, 0.02), (0.0, 0.08), (0.09, 0.02), (0.13, -0.08)], surface=True)
        painting.stroke(geo.smooth(rib), _line(skeleton, style, 0.6), _ink(style, spec.cloth), taper=(0.2, 0.2), clip=tee)
    return tee


def tee_sleeve(painting, skeleton, side, masks, spec, style, light):
    return draw_sleeve(painting, skeleton, side, masks, spec.cloth, style, light, reach=0.42, ease=SLEEVE_EASE["fitted"])


def hot_pants(painting, skeleton, masks, spec, style, light):
    """Low-rise denim shorts (spec.cloth_second) cut high on the thigh, with a frayed hem."""
    color = rgb(spec.cloth_second)
    top = geo.smooth(skeleton.on_pelvis([(-FAR, -0.24), (0.0, -0.17), (FAR, -0.24)]))
    right_leg = [(0.72, 0.44), (0.42, 0.56), (0.14, 0.60)]
    front = right_leg + [(0.0, 0.60)] + [(-x, y) for x, y in right_leg[::-1]]
    hem = geo.smooth(skeleton.on_pelvis(_leg_openings(skeleton, front, 0.44, 0.52)))
    region, body = bottom_region(painting, skeleton, masks, top, hem, 0.62)
    shorts = fitted(painting, skeleton, body, region, color, style, light, ease=0.01)
    leg_split(painting, skeleton, masks, shorts, color, style, start=0.40)
    if style.line_width > 0:
        ink, width = _ink(style, color), _line(skeleton, style, 0.7)
        painting.stroke(skeleton.on_pelvis([(0.0, -0.17), (0.02, 0.32)], surface=True), width, ink, taper=(0.1, 0.4), clip=shorts)
        band = geo.smooth(skeleton.on_pelvis([(-FAR, -0.16), (0.0, -0.09), (FAR, -0.16)]))
        painting.stroke(band, width, ink, taper=(0.0, 0.0), clip=shorts)
        for sign in (1.0, -1.0):
            pocket = skeleton.on_pelvis([(sign * 0.20, -0.14), (sign * 0.30, 0.02), (sign * (skeleton.body.hip - 0.10), 0.07)],
                                        surface=True)
            painting.stroke(geo.smooth(pocket), width, ink, taper=(0.1, 0.3), clip=shorts)
    # frayed threads hang from each leg opening onto the thigh
    rng = np.random.default_rng(spec.seed)
    threads = light_of(color, amount=0.6)
    for leg in () if skeleton.seated > 0.5 else (right_leg, [(-x, y) for x, y in right_leg]):
        for point in geo.resample(geo.smooth(skeleton.on_pelvis(leg, surface=True)), 18):
            length = skeleton.px(rng.uniform(0.012, 0.04))
            tip = point + [rng.uniform(-0.35, 0.35) * length, length]
            painting.stroke(np.array([point - [0.0, length * 0.3], tip]), skeleton.px(0.007), threads, taper=(0.0, 0.8),
                            opacity=0.85, layer="color", clip=masks["skin"])
    return shorts


# ---- hoodie ---------------------------------------------------------------------------
def hoodie_body(painting, skeleton, masks, spec, style, light, hem=0.10):
    """Loose hoodie (spec.cloth) to the hips, with a ribbed hem band, a front pocket and drawstrings."""
    color = rgb(spec.cloth)
    bottom = _hem(skeleton, "pelvis", hem, sag=0.02)
    region, over = _top_over(painting, skeleton, masks, _shoulder_line(skeleton, 0.11, 0.07, collar=0.18), bottom, hem)
    body = fitted(painting, skeleton, over, region, color, style, light, bevel=0.22, ease=0.06, drape=0.95)
    rib = shadow_of(color, style.shadow_tint, 0.22)
    seated = skeleton.seated > 0.5
    if seated:
        band = _seated_hem_band(painting, skeleton, masks, hem, RIB_DEPTH) * body
    else:
        band = painting.mask(np.vstack([_hem(skeleton, "pelvis", hem - RIB_DEPTH, sag=0.02)[::-1], bottom])) * body
    painting.fill(band, rib, 0.8)
    ink, width = _ink(style, color), _line(skeleton, style, 0.7)
    if style.line_width > 0 and not seated:
        painting.stroke(_hem(skeleton, "pelvis", hem - RIB_DEPTH, sag=0.02), width, ink, taper=(0.0, 0.0), clip=body)
    seen = skeleton.visibility("pelvis", [(0.0, -0.25)])[0]
    if seen > 0.2:
        pocket = _on_surface(skeleton, "pelvis", [(-0.36, -0.04), (-0.27, -0.44), (0.27, -0.44), (0.36, -0.04)], closed=False)
        if style.line_width > 0:
            painting.stroke(pocket, width, ink, taper=(0.0, 0.0), opacity=seen, clip=body)
        for sign in (1.0, -1.0):          # the slanted openings at either side
            opening = skeleton.on_pelvis([(sign * 0.27, -0.42), (sign * 0.35, -0.06)], surface=True)
            painting.stroke(opening, skeleton.px(0.035), shadow_of(color, style.shadow_tint, style.shadow_depth),
                            taper=(0.3, 0.3), opacity=0.55 * seen, layer="color", clip=body)
    cord = shadow_of(color, style.shadow_tint, 0.55) if rgb(color).mean() > 0.5 else light_of(color, amount=0.7)
    for sign in (1.0, -1.0):
        anchor = [(sign * 0.06, 0.06), (sign * 0.07, 0.32), (sign * 0.075, 0.56)]
        if skeleton.visibility("chest", anchor[:1])[0] < 0.3:
            continue
        string = geo.smooth(skeleton.on_chest(anchor, surface=True))
        painting.stroke(string, skeleton.px(0.016), cord, taper=(0.1, 0.1), layer="color")
        painting.stroke(geo.subpath(string, 0.86, 1.0), skeleton.px(0.026), cord, taper=(0.0, 0.0), layer="color")
    return body


def hood(painting, skeleton, masks, spec, style, light):
    """The hood folded on the back of the neck and shoulders. Drawn before the body, or over it seen from behind."""
    from .anatomy import _hull
    from .body import _as3, _rotate
    origin, tilt, _ = skeleton._frame("chest")
    width, depth = HOOD_SIZE

    def ring(y, size, count=13):
        return [(np.cos(a) * width * size, y, np.sin(a) * depth * size - 0.04) for a in np.linspace(0.0, -np.pi, count)]

    def outline(points):
        return skeleton.to_pixels(skeleton.project(origin + _rotate(_as3(points), tilt)))

    shell = [point for y, size in HOOD_RINGS for point in ring(y, size)]
    mask = painting.mask(geo.smooth(_hull(outline(shell)), closed=True))
    color = shadow_of(spec.cloth, style.shadow_tint, 0.15)
    _cloth(painting, skeleton, mask, color, style, light, bevel=0.10)
    if skeleton.pose.view != "back":     # the dark inside of the fold opens toward the front
        lining = painting.mask(geo.smooth(_hull(outline(ring(-0.20, 0.56, 9) + ring(-0.12, 0.64, 9))), closed=True)) * mask
        painting.fill(lining, shadow_of(color, style.shadow_tint, style.shadow_depth * 1.2))
    return mask


def hoodie_sleeve(painting, skeleton, side, masks, spec, style, light):
    return draw_sleeve(painting, skeleton, side, masks, spec.cloth, style, light, reach=1.96, ease=SLEEVE_EASE["loose"],
                       cuff=(0.14, shadow_of(spec.cloth, style.shadow_tint, 0.22)))


# ---- suit ------------------------------------------------------------------------------
def _trouser_leg(painting, skeleton, side, ease, straight):
    """(thigh, lower leg) masks of one straight-cut trouser leg."""
    from .body import LIMB_DEPTH, MALE_THIGH_FLESH, SHIN_FLESH, THIGH_FLESH, _bone_tube
    thigh = MALE_THIGH_FLESH if skeleton.body.build == "male" else THIGH_FLESH
    room = ease / max(skeleton.body.limb, 1e-6)
    knee_width = [thigh[0][-1], thigh[1][-1]]
    upper = (np.array(thigh[0]) + room, np.array(thigh[1]) + room, thigh[2])
    lower = tuple(np.maximum(np.array(profile), width * straight) + room for profile, width in zip(SHIN_FLESH[:2], knee_width))
    knee_depth = [LIMB_DEPTH["thigh"][0][-1], LIMB_DEPTH["thigh"][1][-1]]
    shin_depth = tuple(np.maximum(np.array(profile), width * straight) + room
                       for profile, width in zip(LIMB_DEPTH["shin"][:2], knee_depth))
    pieces = [_bone_tube(skeleton, f"hip_{side}", f"knee_{side}", upper, side,
                         (np.array(LIMB_DEPTH["thigh"][0]) + room, np.array(LIMB_DEPTH["thigh"][1]) + room, LIMB_DEPTH["thigh"][2])),
              _bone_tube(skeleton, f"knee_{side}", f"ankle_{side}", lower + (0.0,), side, shin_depth + (0.0,), cap_end=False)]
    return tuple(painting.mask(piece) for piece in pieces)


def trouser_legs(painting, skeleton, ease, straight=0.9):
    """Straight-cut trouser legs: tubes down each leg that keep `straight` of the knee width to the ankle.

    Fitted cloth follows the calf and closes in at the ankle; pressed trousers fall straight from the knee.
    """
    legs = _zeros(painting)
    for side in ("l", "r"):
        legs = np.maximum(legs, sh.melt(np.maximum.reduce(_trouser_leg(painting, skeleton, side, ease, straight)), skeleton.px(0.03)))
    return legs


def _divide_trouser_legs(painting, skeleton, cloth, color, style, ease, straight=0.9):
    """Seated and seen from the front, straight legs touch below the knees; a line keeps them two legs."""
    if style.line_width <= 0 or skeleton.seated <= 0.5 or abs(skeleton.pose.yaw) > SEATED_FRONT_YAW:
        return
    left, right = (_trouser_leg(painting, skeleton, side, ease, straight)[1] for side in ("l", "r"))
    # The inner edge of the left lower leg where it runs close to the right one; the ease of the cloth
    # has filled the gap between them, so one line along that edge stands for both.
    near_right = (sh.blur(right, skeleton.px(TROUSER_GAP)) > 0.02).astype(np.float32)
    painting.outline_mask(left, _line(skeleton, style, 0.8), _ink(style, color), keep=near_right * (1.0 - right) * cloth)


def suit_trousers(painting, skeleton, masks, spec, style, light):
    """Straight trousers (spec.cloth) with a pressed crease down the front of each leg."""
    cloth = jeans(painting, skeleton, masks, spec, style, light, rise=0.08, color=spec.cloth, ease=0.02,
                  legs=trouser_legs(painting, skeleton, 0.03))
    _divide_trouser_legs(painting, skeleton, cloth, spec.cloth, style, 0.03)
    crease = light_of(spec.cloth, amount=0.25)
    for side in ("l", "r"):
        hip, ankle = skeleton.joints[f"hip_{side}"], skeleton.joints[f"ankle_{side}"]
        line = np.array([geo.lerp(hip, ankle, 0.20), geo.lerp(hip, ankle, 0.95)]) + [skeleton.sin_yaw * skeleton.px(0.12), 0.0]
        painting.stroke(line, skeleton.px(0.010), crease, taper=(0.3, 0.1), opacity=0.25 + 0.45 * abs(skeleton.cos_yaw),
                        layer="color", clip=cloth)
    return cloth


def shirt(painting, skeleton, masks, spec, style, light, tucked=True, color=SHIRT):
    """Dress shirt with a turned-down collar, tucked in by default."""
    hem = -0.16 if tucked else 0.12
    region = np.vstack([_shoulder_line(skeleton, 0.09, -0.04), _hem(skeleton, "pelvis", hem, sag=0.02)])
    body = fitted(painting, skeleton, _upper_body(masks), region, color, style, light, ease=0.02, drape=0.3)
    for sign in (1.0, -1.0):
        points = [(sign * 0.015, 0.03), (sign * 0.155, -0.14), (sign * 0.17, 0.0), (sign * 0.11, 0.17)]
        if skeleton.visibility("chest", points[:1])[0] < 0.2:
            continue
        flap = painting.mask(_on_surface(skeleton, "chest", points))
        _cloth(painting, skeleton, flap, color, style, light, bevel=0.03, line=0.8)
    return body


def tie(painting, skeleton, masks, spec, style, light, color=TIE):
    if skeleton.visibility("chest", [(0.0, 0.5)])[0] < 0.15:
        return _zeros(painting)
    knot = _on_surface(skeleton, "chest", [(-0.045, 0.0), (0.045, 0.0), (0.03, 0.10), (-0.03, 0.10)])
    blade = _on_surface(skeleton, "chest", [(-0.03, 0.10), (0.03, 0.10), (0.075, 1.05), (0.0, 1.15), (-0.075, 1.05)])
    mask = np.maximum(painting.mask(knot), painting.mask(blade))
    _cloth(painting, skeleton, mask, color, style, light, bevel=0.03, line=0.8)
    return mask


def jacket(painting, skeleton, masks, spec, style, light, hem=0.32):
    """Single-breasted jacket (spec.cloth): open V over shirt and tie, notched lapels, two buttons, pocket flaps."""
    color = rgb(spec.cloth)
    region, over = _top_over(painting, skeleton, masks, _shoulder_line(skeleton, 0.12, -0.02, collar=0.19),
                             _hem(skeleton, "pelvis", hem, sag=0.02), hem)
    opening = np.maximum(
        painting.mask(_on_surface(skeleton, "chest", [(-0.12, -0.10), (-0.04, 1.24), (0.04, 1.24), (0.12, -0.10)])),
        painting.mask(_on_surface(skeleton, "pelvis", [(0.0, -0.56), (0.04, -0.26), (0.09, -0.02), (0.16, hem + 0.06),
                                                       (-0.16, hem + 0.06), (-0.09, -0.02), (-0.04, -0.26)])))
    front_open = None if skeleton.pose.view == "back" else opening        # the open front is not seen from behind
    body = fitted(painting, skeleton, over, region, color, style, light, bevel=0.2, ease=0.04, drape=0.6, cut=front_open)
    lapel_color = light_of(color, amount=0.10)
    ink = _ink(style, color)
    for sign in (1.0, -1.0):
        points = [(sign * 0.12, -0.10), (sign * 0.27, 0.22), (sign * 0.21, 0.30), (sign * 0.29, 0.37), (sign * 0.05, 1.22),
                  (sign * 0.035, 1.24)]
        if skeleton.visibility("chest", points[:2]).min() < 0.1:
            continue
        lapel = painting.mask(_on_surface(skeleton, "chest", points)) * body
        _cloth(painting, skeleton, lapel, lapel_color, style, light, bevel=0.05, line=0.8)
    for y in (1.36, 1.62):
        spot = [(0.05, y)]
        if skeleton.visibility("chest", spot)[0] > 0.3:
            centre = skeleton.on_chest(spot, surface=True)[0]
            button = painting.mask(geo.ellipse(centre, skeleton.px(0.024), skeleton.px(0.024), count=16)) * body
            painting.fill(button, shadow_of(color, style.shadow_tint, 0.7))
    if style.line_width > 0:
        for sign in (1.0, -1.0):          # pocket flaps
            flap = [(sign * 0.22, -0.30), (sign * 0.50, -0.29)]
            if skeleton.visibility("pelvis", flap).min() > 0.3:
                painting.stroke(skeleton.on_pelvis(flap, surface=True), _line(skeleton, style, 0.7), ink, taper=(0.1, 0.1), clip=body)
    return body


def jacket_sleeve(painting, skeleton, side, masks, spec, style, light):
    return draw_sleeve(painting, skeleton, side, masks, spec.cloth, style, light, reach=1.90, ease=SLEEVE_EASE["tailored"],
                       under=(0.07, SHIRT))


# ---- lingerie ----------------------------------------------------------------------------
STRAP_SEEN = 0.5             # coverage below which a strap counts as hidden at that point


def _until_hidden(path, seen):
    """The part of a path from its start up to where `seen` first hides it; None if hidden from the start.

    A strap that disappears behind an arm and comes out again would show as a loose scrap above the arm.
    """
    rows = np.clip(np.round(path[:, 1]).astype(int), 0, seen.shape[0] - 1)
    cols = np.clip(np.round(path[:, 0]).astype(int), 0, seen.shape[1] - 1)
    hidden = np.flatnonzero(seen[rows, cols] < STRAP_SEEN)
    if len(hidden) == 0:
        return path
    return path[:hidden[0] + 1] if hidden[0] >= 2 else None


def bra(painting, skeleton, masks, spec, style, light):
    """Balconette bra (spec.cloth): cups over the lower breasts with lace along their top, a centre gore,
    an underband and straps over the shoulders."""
    from . import anatomy
    color = rgb(spec.cloth)
    skin = masks["skin"]
    shapes = anatomy.breast_shapes(skeleton)
    if not shapes:
        return _zeros(painting)
    size = skeleton.body.bust
    spot_y = anatomy.BREAST_CENTER[1] + anatomy.BREAST_SAG * (size - 1.0)
    band_y = spot_y + anatomy.BREAST_RADIUS * size ** 0.85 * 0.92
    under = np.vstack([_hem(skeleton, "chest", band_y + 0.07)[::-1], _hem(skeleton, "chest", band_y - 0.01)])
    gore = skeleton.on_chest([(-0.07, band_y), (-0.025, spot_y + 0.02), (0.025, spot_y + 0.02), (0.07, band_y)], surface=True)
    on_body = sh.smoothstep(0.25, 0.45, sh.blur(masks["trunk"], skeleton.px(0.012)))
    total = np.maximum(painting.mask(under), painting.mask(gore)) * on_body
    _cloth(painting, skeleton, total, color, style, light, bevel=0.04, line=0.8)
    reach = skeleton.px(4.0)
    across, down = _turned(skeleton, (1.0, 0.0)), _turned(skeleton, (0.0, 1.0))
    front_arms = np.maximum.reduce([_zeros(painting)] + [masks["limbs"][name] for name in ("arm_l", "arm_r")
                                                         if name not in skeleton.behind])
    for index, (sign, centre, radius, curve) in enumerate(shapes):
        def at(x, y):              # breast-local offsets (radii), turned with the figure
            return centre + (across * x + down * y) * radius
        inner, outer = at(-sign * 1.05, -0.02), at(sign * 1.0, -0.55)
        top = geo.smooth([inner, at(sign * 0.05, -0.24), outer])                                  # inner end to outer end
        far = reach / radius
        below = painting.mask(np.vstack([top, at(sign * 1.6, -0.55), at(sign * 1.6, far), at(-sign * 1.25, far),
                                         at(-sign * 1.25, -0.02)]))
        ball = sh.smoothstep(0.2, 0.45, sh.blur(painting.mask(curve), skeleton.px(0.012)))
        nearer = _zeros(painting)
        if skeleton.yaw != 0.0:
            for *_, near_curve in shapes[index + 1:]:
                nearer = np.maximum(nearer, painting.mask(near_curve))
        cup = ball * below * skin * (1.0 - nearer)
        _cloth(painting, skeleton, cup, color, style, light, bevel=0.10, line=0.8)
        lace_edge(painting, skeleton, top, color, style, skin * (1.0 - nearer) * ball, toward=-down, depth=0.045)
        strap_end = [(sign * 0.33, -0.03)]
        if skeleton.visibility("chest", strap_end)[0] > 0.2:
            start = geo.lerp(top[len(top) // 2], outer, 0.5)
            strap = geo.bent_line(start, skeleton.on_chest(strap_end, surface=True)[0], 0.03 * sign)
            clip = skin * (1.0 - nearer) * (1.0 - cup)
            strap = _until_hidden(strap, 1.0 - front_arms)
            if strap is None:
                continue
            if style.line_width > 0:
                painting.stroke(strap, skeleton.px(0.03) + _line(skeleton, style, 0.8), _ink(style, color), taper=(0.0, 0.0),
                                layer="color", clip=clip)
            painting.stroke(strap, skeleton.px(0.03), color, taper=(0.0, 0.0), layer="color", clip=clip)
        total = np.maximum(total, cup)
    return total


def panties(painting, skeleton, masks, spec, style, light):
    """Brief (spec.cloth) with lace along the waist and the leg openings."""
    color = rgb(spec.cloth)
    skin = masks["skin"]
    waist = [(-FAR, -0.10), (-0.42, -0.12), (0.0, -0.03), (0.42, -0.12), (FAR, -0.10)]
    right_leg = [(0.58, 0.02), (0.34, 0.22), (0.13, 0.43)]
    front = right_leg + [(0.0, 0.50)] + [(-x, y) for x, y in right_leg[::-1]]
    legs = geo.smooth(skeleton.on_pelvis(_leg_openings(skeleton, front, 0.02, 0.28)))
    region, body = bottom_region(painting, skeleton, masks, geo.smooth(skeleton.on_pelvis(waist)), legs, 0.16)
    brief = fitted(painting, skeleton, body, region, color, style, light)
    outside = skin * (1.0 - brief)
    lace_edge(painting, skeleton, geo.smooth(skeleton.on_pelvis(waist[1:-1], surface=True)), color, style, outside,
              toward=_turned(skeleton, (0.0, -1.0)), depth=0.045)
    for sign in () if skeleton.seated > 0.5 else (1.0, -1.0):
        edge = geo.smooth(skeleton.on_pelvis([(sign * x, y) for x, y in right_leg], surface=True))
        lace_edge(painting, skeleton, edge, color, style, outside, toward=_turned(skeleton, (sign * skeleton.cos_yaw, 0.6)),
                  depth=0.04)
    if skeleton.visibility("pelvis", [(0.0, -0.04)])[0] > 0.4:      # a small bow at the front
        knot = skeleton.on_pelvis([(0.0, 0.0)], surface=True)[0]
        for sign in (1.0, -1.0):
            loop = geo.ellipse(knot + [sign * skeleton.px(0.028), 0.0], skeleton.px(0.026), skeleton.px(0.016), angle=sign * 0.4)
            painting.fill(painting.mask(loop), mix(color, "#ffffff", 0.25))
    return brief


def stockings(painting, skeleton, masks, spec, style, light, top=0.45):
    """Sheer thigh-high stockings (spec.cloth) with a lace top. top: share of the thigh where they end."""
    color = rgb(spec.cloth)
    rows, cols = np.mgrid[0:painting.shape[0], 0:painting.shape[1]].astype(np.float32)
    covered = _zeros(painting)
    for side in ("l", "r"):
        leg = masks["limbs"][f"leg_{side}"]
        hip, knee = skeleton.joints[f"hip_{side}"], skeleton.joints[f"knee_{side}"]
        down = (knee - hip) / max(np.linalg.norm(knee - hip), 1e-9)
        start = geo.lerp(hip, knee, top)
        beyond = (cols - start[0]) * down[0] + (rows - start[1]) * down[1]
        sheer = sh.smoothstep(-1.0, 1.0, beyond) * leg
        painting.fill(sheer, color, 0.40)
        inside = ndimage.distance_transform_edt(leg > 0.5)
        painting.fill(sheer * (1.0 - sh.smoothstep(0.0, skeleton.px(0.08), inside)), color, 0.40)   # denser where it wraps away
        across = np.array([-down[1], down[0]]) * skeleton.px(0.6)
        welt = start + down * skeleton.px(0.08)
        lace_edge(painting, skeleton, np.array([welt - across, welt + across]), color, style, leg, toward=-down, depth=0.08)
        covered = np.maximum(covered, sheer)
    return covered


# ---- outfits ------------------------------------------------------------------------------
def _layers(*garments):
    def body(painting, skeleton, masks, spec, style, light):
        return np.maximum.reduce([garment(painting, skeleton, masks, spec, style, light) for garment in garments])
    return body


LINGERIE = Outfit(body=_layers(panties, bra))
LINGERIE_STOCKINGS = Outfit(body=_layers(stockings, panties, bra))
CROP_TOP_SHORTS = Outfit(body=_layers(hot_pants, sneakers, crop_tee), sleeve=tee_sleeve)
HOODIE = Outfit(body=hoodie_body, sleeve=hoodie_sleeve, behind=hood)
HOODIE_JEANS = combine(_layers(jeans, sneakers), HOODIE)
HOODIE_SHORTS = combine(_layers(hot_pants, sneakers), HOODIE)
SUIT = Outfit(body=_layers(suit_trousers, dress_shoes, shirt, tie, jacket), sleeve=jacket_sleeve)

OUTFITS = {"lingerie": LINGERIE, "lingerie_stockings": LINGERIE_STOCKINGS, "crop_top_shorts": CROP_TOP_SHORTS,
           "hoodie": HOODIE_JEANS, "hoodie_shorts": HOODIE_SHORTS, "suit": SUIT}
