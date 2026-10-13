"""Accessories worn over the figure: glasses, a hat, a scarf and a crossbody bag, in every view.

Spec (top level, any subset; `true` takes the defaults):
  "accessories": {
    "glasses": {"shape": "round" | "square", "color": "#2A2230", "lens": 0.10},
    "hat":     {"kind": "beanie" | "cap" | "wide", "group": "hat", "pompom": false},
    "scarf":   {"side": "right", "group": "scarf", "length": 2.6},
    "bag":     {"side": "left", "group": "bag"}
  }
`side` is the side of the picture in the front view (the back view mirrors it). The palette groups
hat, scarf and bag come from assets/accessories.json; a "pattern" in a group dresses it like a garment.

Head pieces are drawn in the head's own frame (x right, y down, z toward the viewer; eye line y = 0),
so they turn with the head. A hat presses the hair down: hair above its lower edge and outside it is
painted out with the background saved before the figure (remember_background).
"""
import cv2
import numpy as np

import kit
import relief
from figure import EAR_DEPTH, Frame, face_z
from raster import ellipse, fill, mix, multiply, over, rgb, screen, shift, smooth, stroke, taper

GLASSES = {"shape": "round", "color": "#2A2230", "lens": 0.10}
HAT = {"kind": "beanie", "group": "hat", "pompom": False}
SCARF = {"side": "right", "group": "scarf", "length": 2.6}
BAG = {"side": "left", "group": "bag"}
DEFAULTS = {"glasses": GLASSES, "hat": HAT, "scarf": SCARF, "bag": BAG}

# ------------------------------------------------------------------ glasses (head units)
LENS = {"round": (0.30, 0.27, 2.0), "square": (0.32, 0.22, 4.0)}   # half-width, half-height, superellipse power
LENS_DROP = 0.03                 # lens centre below the eye centre
FRAME_LIFT = 0.10                # frame stands this far in front of the face
FRAME_WIDTH = 0.024
TEMPLE_END = (1.02, -0.04)       # where the temple meets the ear (x is mirrored per side)
GLINT_OPACITY = 0.45
# Profile: the near rim seen edge-on in front of the eye, the temple running back over the ear.
PROFILE_RIM = ((0.92, -0.02), 0.07, 0.25)
PROFILE_TEMPLE = [(0.88, -0.16), (0.30, -0.13), (-0.40, -0.10), (-0.56, 0.10)]

# ------------------------------------------------------------------ hats (head units, front frame)
BEANIE = [(-1.19, -0.55), (-1.25, -0.95), (-1.11, -1.38), (-0.76, -1.67), (0.0, -1.79), (0.76, -1.67), (1.11, -1.38),
          (1.25, -0.95), (1.19, -0.55), (0.0, -0.49)]
BEANIE_CUFF = -0.88              # top of the folded-up cuff
CAP = [(-1.16, -0.62), (-1.21, -0.98), (-1.04, -1.38), (-0.64, -1.64), (0.0, -1.73), (0.64, -1.64), (1.04, -1.38),
       (1.21, -0.98), (1.16, -0.62), (0.0, -0.70)]
CAP_TOP = -1.72                  # the button where the panels meet
# The visor: a crescent from the crown's sides reaching toward us, dipping at its front; its back edge tucks under the crown.
CAP_BRIM = {"half": 1.10, "side_y": -0.64, "base_z": 0.35, "reach": 0.95, "drop": 0.28, "tuck": 0.10}
WIDE_CROWN = [(-0.96, -0.92), (-1.00, -1.25), (-0.84, -1.66), (-0.45, -1.88), (0.0, -1.93), (0.45, -1.88), (0.84, -1.66),
              (1.00, -1.25), (0.96, -0.92), (0.0, -0.88)]
WIDE_BRIM = {"radius": 2.0, "y": -0.95, "drop": 0.34}
WIDE_BAND = (-0.92, -1.14)       # ribbon round the crown's base
# The hat's lower edge across the head (and well past it): hair above it, outside the hat, is pressed flat.
HAT_LINE = {"beanie": [(-2.6, -0.60), (0.0, -0.55), (2.6, -0.60)], "cap": [(-2.6, -0.67), (0.0, -0.74), (2.6, -0.67)],
            "wide": [(-3.0, -0.98), (0.0, -0.98), (3.0, -0.98)]}
BRIM_SHADOW = 0.20               # head units the brim's shadow reaches down the face
# Profile (x forward, y down; the face's front is near x = 0.9).
PROFILE_HATS = {
    "beanie": [(0.82, -0.70), (0.88, -1.20), (0.52, -1.86), (-0.30, -2.18), (-1.16, -2.02), (-1.86, -1.34), (-2.02, -0.55),
               (-1.20, -0.62), (-0.20, -0.70)],
    "cap": [(0.76, -0.80), (0.82, -1.25), (0.46, -1.86), (-0.34, -2.10), (-1.16, -1.92), (-1.76, -1.26), (-1.88, -0.76),
            (-0.90, -0.80)],
    "wide": [(0.70, -0.96), (0.76, -1.40), (0.42, -2.02), (-0.40, -2.22), (-1.20, -2.05), (-1.62, -1.45), (-1.66, -0.98),
             (-0.50, -0.93)],
}
PROFILE_CUFF = [(0.84, -0.98), (-0.50, -0.90), (-2.02, -0.82)]
PROFILE_CAP_BRIM = [(0.66, -0.92), (1.30, -0.88), (1.76, -0.72), (1.80, -0.60), (1.32, -0.70), (0.70, -0.74)]
PROFILE_WIDE_BRIM = ((-0.45, -0.95), 2.55, 0.17)
PROFILE_HAT_LINE = {"beanie": [(2.5, -0.77), (0.8, -0.76), (-2.1, -0.61), (-3.0, -0.58)],
                    "cap": [(2.5, -0.87), (0.8, -0.86), (-1.9, -0.82), (-3.0, -0.80)],
                    "wide": [(3.0, -0.95), (-3.0, -0.95)]}

# ------------------------------------------------------------------ scarf and bag
# The scarf goes twice round the neck (two rolls, the lower one resting on the shoulders) and its two
# ends hang from under the rolls. (aside, spine level) in head units; widths are full widths.
SCARF_ROLLS = [([(-1.08, -0.86), (-0.58, -0.36), (0.0, -0.16), (0.58, -0.36), (1.08, -0.86)], 0.27),
               ([(-0.94, -1.12), (-0.50, -0.76), (0.0, -0.60), (0.50, -0.76), (0.94, -1.12)], 0.24)]
SCARF_ENDS = [((0.10, -0.30), (0.18, -0.9), 1.00), ((0.44, -0.36), (0.52, 0.0), 1.10)]   # start, end (relative), width
SCARF_DEPTH = 0.30
FRINGE = 0.16
PORTRAIT_SCARF = [(-1.00, 1.62), (-0.55, 1.47), (0.0, 1.43), (0.55, 1.47), (1.00, 1.62), (1.10, 1.95), (0.65, 2.18),
                  (0.0, 2.22), (-0.65, 2.18), (-1.10, 1.95)]           # torso frame, round the neck
PORTRAIT_ENDS = [((0.62, 2.02), (0.72, 4.0), 0.86), ((0.22, 2.00), (0.32, 4.6), 0.96)]   # start, end, width; the one behind first
BAG_SIZE = (0.62, 0.45)          # half-width, half-height (head units)
BAG_AT = (0.35, 1.32)            # below the hip level, aside of the spine
STRAP = 0.13


def wanted(spec, name):
    """The accessory's settings over its defaults, or None when it is not worn."""
    value = (spec.get("accessories") or {}).get(name)
    if not value:
        return None
    return {**DEFAULTS[name], **(value if isinstance(value, dict) else {})}


def any_worn(spec, *names):
    return any(wanted(spec, name) for name in names)


def remember_background(scene):
    """Keep the bare background: a hat paints out the hair it presses down with it."""
    if wanted(scene.fig.spec, "hat"):
        scene.fig.extra["bare_background"] = scene.image.copy()


def screen_side(cut, back):
    """+1 for a piece worn on the picture's right in the front view; the back view mirrors it."""
    sign = -1.0 if cut["side"] == "left" else 1.0
    return -sign if back else sign


# ------------------------------------------------------------------ head frame
def project(frame, points, z=0.0):
    points = np.asarray(points, np.float64)
    if points.shape[1] == 2:
        points = np.column_stack([points, np.full(len(points), z)])
    return frame.project(points)


def lens_ring(center_x, cut, samples=64):
    """One lens outline in head units (x, y, z) round an eye centre."""
    half_w, half_h, power = LENS[cut["shape"]]
    turn = np.linspace(0.0, 2 * np.pi, samples, endpoint=False)
    cos, sin = np.cos(turn), np.sin(turn)
    x = center_x + half_w * np.sign(cos) * np.abs(cos) ** (2.0 / power)
    y = LENS_DROP + half_h * np.sign(sin) * np.abs(sin) ** (2.0 / power)
    return np.column_stack([x, y, face_z(x, y) + FRAME_LIFT])


def paint_glasses(scene, stage):
    """Front and three-quarter views. stage "temples": the arms (under the hair); "frames": lenses and rims."""
    cut = wanted(scene.fig.spec, "glasses")
    if not cut:
        return
    fig, unit = scene.fig, scene.px(1.0)
    head = fig.head_frame
    frame_color = rgb(cut["color"])
    center_x = fig.spec["eyes"]["center_x"]
    width = FRAME_WIDTH * unit
    if stage == "temples":
        for side in (1, -1):
            half_w = LENS[cut["shape"]][0]
            start = np.array([[side * (center_x + half_w * 0.98), 0.0, face_z(side * (center_x + half_w), 0.0) + FRAME_LIFT * 0.6]])
            end = np.array([[side * TEMPLE_END[0], TEMPLE_END[1], EAR_DEPTH]])
            path = project(head, np.vstack([start, (start * 0.5 + end * 0.5) + [0, -0.02, 0], end]))
            over(scene.image, frame_color, stroke(scene.size, smooth(path, samples=6), width * 0.9))
        return
    rings = {side: project(head, lens_ring(side * center_x, cut)) for side in (1, -1)}
    for side, ring in rings.items():
        glass = fill(scene.size, ring)
        screen(scene.image, rgb("#FFFFFF"), glass, cut["lens"])
        if scene.shade_on:
            # A glint across the lens: a short diagonal streak from the light's side.
            center = ring.mean(axis=0)
            reach = np.ptp(ring[:, 0]) * 0.28
            streak = np.array([center + [-reach, -reach * 0.6], center + [reach * 0.2, reach * 0.4]])
            screen(scene.image, rgb("#FFFFFF"), scene.soften(stroke(scene.size, streak, 0.05 * unit), 0.01) * glass, GLINT_OPACITY)
        over(scene.image, frame_color, stroke(scene.size, np.vstack([ring, ring[:1]]), width))
    inner_far = rings[1][np.argmin(rings[1][:, 0])]
    inner_near = rings[-1][np.argmax(rings[-1][:, 0])]
    bridge = smooth([inner_near, (inner_far + inner_near) / 2 - [0, 0.05 * unit], inner_far], samples=6)
    over(scene.image, frame_color, stroke(scene.size, bridge, width * 0.9))


def paint_glasses_profile(scene, head):
    """Profile: the near rim edge-on in front of the eye and the temple back to the ear (painted before the hair)."""
    cut = wanted(scene.fig.spec, "glasses")
    if not cut:
        return
    unit = scene.px(1.0)
    frame_color = rgb(cut["color"])
    (cx, cy), rx, ry = PROFILE_RIM
    rim = head(ellipse((cx, cy), rx, ry, 40))
    screen(scene.image, rgb("#FFFFFF"), fill(scene.size, rim), cut["lens"])
    over(scene.image, frame_color, stroke(scene.size, np.vstack([rim, rim[:1]]), FRAME_WIDTH * unit))
    temple = head(smooth(PROFILE_TEMPLE, samples=8))
    over(scene.image, frame_color, stroke(scene.size, temple, FRAME_WIDTH * unit * taper(len(temple), 0.0, 0.3, 0.0) + 1.0))


# ------------------------------------------------------------------ hats
def hat_shapes(head, kind, back):
    """Pixel outlines (crown, brim or None, brim in front of the crown?) of a hat in the front frame."""
    if kind == "beanie":
        return project(head, smooth(BEANIE, samples=8, closed=True)), None
    if kind == "cap":
        crown = project(head, smooth(CAP, samples=8, closed=True))
        if back:
            return crown, None
        cut = CAP_BRIM
        turn = np.linspace(0.0, np.pi, 40)
        rise = np.sin(turn)
        outer = np.column_stack([cut["half"] * np.cos(turn), cut["side_y"] + cut["drop"] * rise, (cut["base_z"] + cut["reach"]) * rise])
        inner = np.column_stack([cut["half"] * np.cos(turn), cut["side_y"] - cut["tuck"] * rise, cut["base_z"] * rise])
        return crown, project(head, np.vstack([outer, inner[::-1]]))
    cut = WIDE_BRIM
    turn = np.linspace(0.0, 2 * np.pi, 80, endpoint=False)
    sign = -1.0 if back else 1.0
    disc = np.column_stack([cut["radius"] * np.cos(turn), cut["y"] + sign * cut["drop"] * np.sin(turn), cut["radius"] * np.sin(turn)])
    return project(head, smooth(WIDE_CROWN, samples=8, closed=True)), project(head, disc)


def press_hair(scene, line_px, hat_mask, hair_names):
    """Paint out the hair above the hat's lower edge that sticks out round the hat, with the saved background."""
    bare = scene.fig.extra.get("bare_background")
    if bare is None:
        return
    height = scene.size[0]
    above = fill(scene.size, np.vstack([line_px, [line_px[-1][0], -height], [line_px[0][0], -height]]))
    hair = np.maximum.reduce([scene.mask(name) for name in hair_names if name in scene.fig.shapes])
    out = np.clip(hair * above * (1.0 - hat_mask), 0.0, 1.0)
    out = cv2.dilate(out, np.ones((3, 3), np.uint8)) * above * (1.0 - hat_mask)
    over(scene.image, bare, out)


def brim_shadow(scene, brim_mask, hat_mask, receivers):
    """The brim's shadow on the face and hair under it."""
    if not scene.shade_on or brim_mask is None:
        return
    thrown = shift(brim_mask, 0.0, BRIM_SHADOW * scene.px(1.0))
    under = scene.soften(thrown, 0.02) * (1.0 - hat_mask) * receivers
    multiply(scene.image, scene.tone("skin", "shadow"), under, 0.55)


def shade_hat(scene, outline, group, depth_units, lift=0.0):
    """A rounded hat piece shaded in its group and outlined. Returns its mask."""
    unit = scene.px(1.0)
    part = relief.blob(scene.size, outline, depth_units * unit)
    part.height = part.height + lift * unit
    kit.shade_solid(scene, part, group, level=0.30, spread=0.5, seam_blur=0.05 * unit)
    kit.ink_edges(scene, part.mask, 2.0, group, "line")
    return part.mask


def paint_hat(scene, back=False):
    """Front, three-quarter and back views: after the head and its hair."""
    cut = wanted(scene.fig.spec, "hat")
    if not cut:
        return
    fig, unit = scene.fig, scene.px(1.0)
    head = fig.head_frame
    kind, group = cut["kind"], cut["group"]
    tones = scene.style["palette"][group]
    crown, brim = hat_shapes(head, kind, back)
    crown_mask = fill(scene.size, crown)
    brim_mask = fill(scene.size, brim) if brim is not None else None
    hat_mask = crown_mask if brim_mask is None else np.maximum(crown_mask, brim_mask)
    hair_names = ("hair_back", "hair_near", "hair_far", "hair_tail")
    press_hair(scene, project(head, smooth(HAT_LINE[kind], samples=6)), hat_mask, hair_names)
    receivers = np.maximum.reduce([scene.mask(name) for name in ("face",) + hair_names if name in fig.shapes])
    if kind == "wide":
        shade_hat(scene, brim, group, 0.06)
        mask = shade_hat(scene, crown, group, 0.45, 0.1)
        band = fill(scene.size, project(head, [(-1.4, WIDE_BAND[0]), (1.4, WIDE_BAND[0]), (1.4, WIDE_BAND[1]), (-1.4, WIDE_BAND[1])])) * mask
        over(scene.image, rgb(tones.get("band", tones["shadow"])), band)
        kit.ink_edges(scene, band, 1.3, group, "line")
        if not back:
            brim_shadow(scene, brim_mask, hat_mask, receivers)
        return
    mask = shade_hat(scene, crown, group, 0.55 if kind == "beanie" else 0.50)
    if kind == "beanie":
        cuff = fill(scene.size, project(head, [(-1.5, BEANIE_CUFF), (1.5, BEANIE_CUFF), (1.5, -0.2), (-1.5, -0.2)])) * mask
        multiply(scene.image, rgb(tones["shadow"]), cuff, 0.30)
        scene.ink(project(head, smooth([(-1.24, BEANIE_CUFF + 0.02), (0.0, BEANIE_CUFF - 0.03), (1.24, BEANIE_CUFF + 0.02)], samples=8)),
                  1.4, group, "line", clip=mask)
        for x in np.linspace(-1.1, 1.1, 19):
            rib = project(head, [(x, BEANIE_CUFF + 0.06), (x, -0.56 + 0.04 * (x / 1.2) ** 2)])
            scene.ink(rib, 0.9, group, "line", np.ones(2), 0.45, clip=cuff)
        for x in np.linspace(-0.8, 0.8, 5):
            knit = project(head, smooth([(x * 1.2, BEANIE_CUFF - 0.05), (x * 1.1, -1.40), (x * 0.5, -1.85)], samples=6))
            scene.ink(knit, 0.9, group, "line", taper(len(knit), 0.0, 0.5, 0.3), 0.35, clip=mask)
        if cut.get("pompom"):
            ball = relief.ellipsoid(scene.size, project(head, [(0.0, -1.86)])[0], 0.28 * unit, 0.25 * unit)
            kit.shade_solid(scene, ball, group, level=0.3, spread=0.5)
            kit.ink_edges(scene, ball.mask, 1.4, group, "line")
        return
    # Cap: panels meeting at a button, the brim reaching toward us (from behind, the strap opening instead).
    for x in (-0.62, 0.0, 0.62):
        seam = project(head, smooth([(0.0, CAP_TOP), (x * 0.8, -1.25), (x, -0.70 if x == 0 else -0.66)], samples=6))
        scene.ink(seam, 1.0, group, "line", taper(len(seam), 0.2, 0.0), 0.5, clip=mask)
    button = fill(scene.size, ellipse(project(head, [(0.0, CAP_TOP)])[0], 0.08 * unit, 0.05 * unit, 16))
    over(scene.image, rgb(tones["shadow"]), button)
    if back:
        gap = fill(scene.size, project(head, smooth([(-0.36, -0.66), (-0.30, -0.92), (0.0, -1.00), (0.30, -0.92), (0.36, -0.66)],
                                                    samples=6)))
        over(scene.image, rgb(scene.style["palette"]["hair"]["shadow"]), gap * mask)
        scene.ink(project(head, [(-0.36, -0.80), (0.36, -0.80)]), 1.6, group, "line", np.ones(2), 0.8, clip=mask)
        return
    brim_part = relief.blob(scene.size, brim, 0.05 * unit)
    brim_part.height = brim_part.height + 0.6 * unit
    kit.shade_solid(scene, brim_part, group, level=0.25, spread=0.5)
    # The visor's front edge turns under: a dark rim along its lower edge.
    multiply(scene.image, rgb(tones["shadow"]), brim_mask * (1.0 - shift(brim_mask, 0, -0.07 * unit)), 0.7)
    kit.ink_edges(scene, brim_mask, 2.0, group, "line")
    brim_shadow(scene, brim_mask, hat_mask, receivers)


def paint_hat_profile(scene, head):
    """Profile hats, after the face and hair."""
    cut = wanted(scene.fig.spec, "hat")
    if not cut:
        return
    unit = scene.px(1.0)
    kind, group = cut["kind"], cut["group"]
    tones = scene.style["palette"][group]
    crown = head(smooth(PROFILE_HATS[kind], samples=8, closed=True))
    crown_mask = fill(scene.size, crown)
    brim = None
    if kind == "cap":
        brim = head(np.array(PROFILE_CAP_BRIM))
    elif kind == "wide":
        center, radius_x, radius_y = PROFILE_WIDE_BRIM
        brim = head(ellipse(center, radius_x, radius_y, 60, 4))
    brim_mask = fill(scene.size, brim) if brim is not None else None
    hat_mask = crown_mask if brim_mask is None else np.maximum(crown_mask, brim_mask)
    press_hair(scene, head(smooth(PROFILE_HAT_LINE[kind], samples=6)), hat_mask, ("hair_side", "hair_tail"))
    receivers = np.maximum.reduce([scene.mask(name) for name in ("face", "hair_side") if name in scene.fig.shapes])
    if kind == "wide":
        shade_hat(scene, brim, group, 0.05)
    mask = shade_hat(scene, crown, group, 0.50, 0.1)
    if kind == "beanie":
        cuff_line = head(smooth(PROFILE_CUFF, samples=6))
        below = fill(scene.size, np.vstack([cuff_line, cuff_line[::-1] + [0, 3.0 * unit]]))
        multiply(scene.image, rgb(tones["shadow"]), below * mask, 0.30)
        scene.ink(cuff_line, 1.4, group, "line", clip=mask)
        if cut.get("pompom"):
            ball = relief.ellipsoid(scene.size, head([(-0.35, -2.30)])[0], 0.30 * unit, 0.27 * unit)
            kit.shade_solid(scene, ball, group, level=0.3, spread=0.5)
            kit.ink_edges(scene, ball.mask, 1.4, group, "line")
    elif kind == "cap":
        brim_part = relief.blob(scene.size, brim, 0.04 * unit)
        brim_part.height = brim_part.height + 0.4 * unit
        kit.shade_solid(scene, brim_part, group, level=0.25, spread=0.5)
        kit.ink_edges(scene, brim_mask, 1.8, group, "line")
        brim_shadow(scene, brim_mask, hat_mask, receivers)
    else:
        band = fill(scene.size, head([(1.0, -0.95), (1.0, -1.18), (-1.8, -1.12), (-1.8, -0.92)])) * mask
        over(scene.image, rgb(tones.get("band", tones["shadow"])), band)
        kit.ink_edges(scene, band, 1.3, group, "line")
        brim_shadow(scene, brim_mask, hat_mask, receivers)


# ------------------------------------------------------------------ scarf
def ends_paths(length):
    """(path in (aside, level) pairs, width) of each hanging end of the scarf, the one behind first."""
    paths = []
    for (aside, level), (dx, dlevel), width in SCARF_ENDS:
        paths.append(([(aside, level), (aside + dx * 0.5, level + (length + dlevel) * 0.5), (aside + dx, level + length + dlevel)], width))
    return paths


def along_widths(count, widths):
    """Widths at `count` points spread evenly along a path, from a few given ones."""
    return np.interp(np.linspace(0.0, 1.0, count), np.linspace(0.0, 1.0, len(widths)), widths)


def shade_scarf(scene, part, group, unit):
    kit.shade_solid(scene, part, group, level=0.28, spread=0.5, seam_blur=0.08 * unit)
    kit.ink_edges(scene, part.mask, 1.8, group, "line")
    return part.mask


def fringe(scene, end, direction, width, group):
    """Short tassels across the end of a scarf."""
    if not scene.lines_on:
        return
    unit = scene.px(1.0)
    across = np.array([-direction[1], direction[0]])
    for k in np.linspace(-0.4, 0.4, 6):
        root = end + across * k * width
        scene.ink(np.array([root, root + direction * FRINGE * unit]), 1.0, group, "line", np.array([1.0, 0.4]), 0.8)


def paint_scarf_body(scene, body, trunk):
    """Front and back views: the wrap round the neck and, in front, two ends hanging down the chest."""
    from anatomy_body import spine_at
    cut = wanted(scene.fig.spec, "scarf")
    if not cut:
        return np.zeros(scene.size, np.float32)
    unit, group = body.unit, cut["group"]
    back = body.view == "back"
    sign = screen_side(cut, back)
    masks = []
    if not back:
        for path, width in ends_paths(cut["length"]):
            points = np.array([spine_at(body, level, sign * aside) for aside, level in path])
            points = smooth(points, samples=6)
            end = relief.tube(scene.size, points, along_widths(len(points), [width * 0.8, width, width]) * unit * 0.5, roundness=0.35,
                              cap_start=False, cap_end=False)
            end.height = end.height + 0.5 * unit
            masks.append(shade_scarf(scene, end, group, unit))
            direction = (points[-1] - points[-2]) / max(np.linalg.norm(points[-1] - points[-2]), 1e-6)
            fringe(scene, points[-1], direction, width * unit, group)
    for path, half_width in SCARF_ROLLS:
        points = smooth(np.array([spine_at(body, level, aside) for aside, level in path]), samples=6)
        # Each roll thins where it turns round the side of the neck.
        roll = relief.tube(scene.size, points, along_widths(len(points), [0.6, 1.0, 1.0, 1.0, 0.6]) * half_width * unit, roundness=0.6)
        roll.height = roll.height + 0.6 * unit
        masks.append(shade_scarf(scene, roll, group, unit))
    return np.maximum.reduce(masks)


def paint_scarf_portrait(scene):
    """Portrait: the wrap round the base of the neck and one end falling over the chest."""
    cut = wanted(scene.fig.spec, "scarf")
    if not cut:
        return
    fig, unit, group = scene.fig, scene.px(1.0), cut["group"]
    torso = Frame(fig.head_frame.origin_px, fig.head_frame.unit_px, 0.0, fig.spec["pose"]["shoulder_roll_deg"])
    sign = screen_side(cut, False)
    for (x0, y0), (x1, y1), width in PORTRAIT_ENDS:
        end_path = smooth(torso.project([(sign * x0, y0), (sign * (x0 + x1) / 2, (y0 + y1) / 2), (sign * x1, y1)]), samples=6)
        end = relief.tube(scene.size, end_path, along_widths(len(end_path), [width * 0.4, width * 0.5, width * 0.5]) * unit, roundness=0.35,
                          cap_start=False, cap_end=False)
        end.height = end.height + 0.5 * unit
        shade_scarf(scene, end, group, unit)
        crease = end_path[2:] + [sign * width * 0.12 * unit, 0]
        scene.ink(crease, 1.1, group, "line", taper(len(crease), 0.0, 0.4, 0.5), 0.45, clip=end.mask)
    part = relief.blob(scene.size, torso.project(smooth(PORTRAIT_SCARF, samples=8, closed=True)), SCARF_DEPTH * unit)
    part.height = part.height + 0.6 * unit
    shade_scarf(scene, part, group, unit)
    # Two turns of the wrap: a fold line between them, and a short crease where they twist.
    fold = torso.project(smooth([(-1.04, 1.80), (-0.3, 1.86), (0.4, 1.80), (1.04, 1.74)], samples=8))
    scene.ink(fold, 1.4, group, "line", taper(len(fold), 0.2, 0.2), 0.6, clip=part.mask)


def paint_scarf_profile(scene, layout, torso_x):
    """Profile: the wrap round the neck and an end hanging in front of the chest."""
    cut = wanted(scene.fig.spec, "scarf")
    if not cut:
        return np.zeros(scene.size, np.float32)
    unit, body, group = layout["unit"], layout["body"], cut["group"]
    levels = np.linspace(2.25, 2.25 + cut["length"] * 0.95, 5)
    end_path = smooth(body(np.array([(torso_x(layout, y, 1) + 0.16, y) for y in levels])), samples=4)
    end = relief.tube(scene.size, end_path, np.full(len(end_path), 0.20 * unit), roundness=0.4)
    end.height = end.height + 1.6 * unit
    mask = shade_scarf(scene, end, group, unit)
    direction = (end_path[-1] - end_path[-2]) / max(np.linalg.norm(end_path[-1] - end_path[-2]), 1e-6)
    fringe(scene, end_path[-1], direction, 0.40 * unit, group)
    wrap = relief.blob(scene.size, body(ellipse((-0.52, 1.98), 0.98, 0.40, 40, 8)), SCARF_DEPTH * unit)
    wrap.height = wrap.height + 1.8 * unit
    return np.maximum(mask, shade_scarf(scene, wrap, group, unit))


# ------------------------------------------------------------------ bag
def bag_outline(center, unit):
    """A soft rectangle (pixels) centred on `center`."""
    half_w, half_h = BAG_SIZE[0] * unit, BAG_SIZE[1] * unit
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    points = []
    for cx, cy in corners:
        corner = center + np.array([cx * half_w, cy * half_h])
        points.extend([corner + [-cx * 0.15 * unit, 0], corner, corner + [0, -cy * 0.15 * unit]])
    return smooth(points, samples=4, closed=True)


def paint_bag_piece(scene, center, strap_path, group, unit, show_flap=True):
    """Strap then the bag on it: body, flap, buckle. Returns their mask."""
    tones = scene.style["palette"][group]
    strap = relief.tube(scene.size, strap_path, np.full(len(strap_path), STRAP * unit * 0.5), roundness=0.3)
    strap.height = strap.height + 1.0 * unit
    kit.shade_solid(scene, strap, group, level=0.3, spread=0.5)
    kit.ink_edges(scene, strap.mask, 1.4, group, "line")
    outline = bag_outline(center, unit)
    body = relief.blob(scene.size, outline, 0.22 * unit)
    body.height = body.height + 1.0 * unit
    kit.shade_solid(scene, body, group, level=0.3, spread=0.5, gloss=0.25, shininess=30)
    kit.ink_edges(scene, body.mask, 2.0, group, "line")
    if show_flap:
        half_w, half_h = BAG_SIZE[0] * unit, BAG_SIZE[1] * unit
        flap = smooth([center + [-half_w, -half_h], center + [-half_w, 0.05 * unit], center + [0, 0.25 * unit], center + [half_w, 0.05 * unit],
                       center + [half_w, -half_h]], samples=6, closed=True)
        flap_mask = fill(scene.size, flap) * body.mask
        over(scene.image, mix(rgb(tones["base"]), rgb(tones.get("light", tones["base"])), 0.15), flap_mask, 0.6)
        multiply(scene.image, rgb(tones["shadow"]), shift(flap_mask, 0, 0.05 * unit) * (1 - flap_mask) * body.mask, 0.5)
        kit.ink_edges(scene, flap_mask, 1.4, group, "line")
        clasp = fill(scene.size, ellipse(center + [0, 0.16 * unit], 0.09 * unit, 0.07 * unit, 16))
        over(scene.image, rgb(scene.style["palette"]["accent"]["metal"]), clasp)
    return np.maximum(strap.mask, body.mask)


def paint_bag_body(scene, body):
    """Front and back views: the strap from the far shoulder across the trunk to the bag at the hip."""
    from anatomy_body import HIP_LEVEL, spine_at, spine_side
    cut = wanted(scene.fig.spec, "bag")
    if not cut:
        return np.zeros(scene.size, np.float32)
    unit, group = body.unit, cut["group"]
    sign = screen_side(cut, body.view == "back")
    center = spine_side(body, HIP_LEVEL + BAG_AT[1] - 1.0, sign, BAG_AT[0] - BAG_SIZE[0])
    top = center + [0.0, -BAG_SIZE[1] * unit]
    shoulder = spine_at(body, -0.66, -sign * 0.80)
    strap_path = smooth([shoulder, spine_at(body, 1.6, -sign * 0.15), top + [-sign * 0.25 * unit, 0.0]], samples=8)
    return paint_bag_piece(scene, center, strap_path, group, unit, show_flap=body.view != "back")


def paint_bag_profile(scene, layout, torso_x):
    """Profile: the strap comes over the far shoulder, across the chest, to the bag on the near hip."""
    cut = wanted(scene.fig.spec, "bag")
    if not cut:
        return np.zeros(scene.size, np.float32)
    unit, body, group = layout["unit"], layout["body"], cut["group"]
    center = body([(torso_x(layout, 7.75, 0) + 0.15, 7.75)])[0]
    strap_path = body(smooth([(torso_x(layout, 2.55, 1) - 0.05, 2.55), (torso_x(layout, 4.8, 1) - 0.25, 4.8),
                              (torso_x(layout, 7.2, 0) + 0.30, 7.25)], samples=8))
    return paint_bag_piece(scene, center, strap_path, group, unit)


def paint_strap_portrait(scene):
    """Portrait: only the bag's strap shows, crossing the chest from one shoulder."""
    cut = wanted(scene.fig.spec, "bag")
    if not cut:
        return
    fig, unit, group = scene.fig, scene.px(1.0), cut["group"]
    torso = Frame(fig.head_frame.origin_px, fig.head_frame.unit_px, 0.0, fig.spec["pose"]["shoulder_roll_deg"])
    sign = screen_side(cut, False)
    shoulders = fig.spec["body"]["shoulder_half_width"]
    path = smooth(torso.project([(-sign * shoulders * 0.55, fig.spec["body"]["shoulder_y"] - 0.12), (0.0, 3.4), (sign * shoulders, 5.0)]),
                  samples=8)
    strap = relief.tube(scene.size, path, np.full(len(path), STRAP * unit * 0.5), roundness=0.3)
    strap.height = strap.height + 0.5 * unit
    kit.shade_solid(scene, strap, group, level=0.3, spread=0.5)
    kit.ink_edges(scene, strap.mask, 1.6, group, "line")
