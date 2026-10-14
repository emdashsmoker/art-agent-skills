"""Hair rig: big masses first, clumps second, strands and gloss last.

This mirrors how illustrators block hair: silhouette, then ribbons, then a
few strand lines. Drawing single hairs from the start never reads as hair.
"""
from dataclasses import replace

import numpy as np

from . import shading
from .config import ShadeMode, mix
from .geometry import Taper, catmull_rom, lock, offset_curve

BACK_DEPTH_DARKEN = 0.55        # hair behind the body sits in shade
BACK_LOCK_DARKEN = 0.22
STRAND_OFFSETS = (-0.24, 0.20)  # share of clump width
STRAND_WIDTH = 0.013            # head units
HIGHLIGHT_TEETH = 36            # gloss marks per half turn
ROOT_FADE = (0.18, 0.50)        # share of clump length over which its edge appears
HIGHLIGHT_LIGHT_ANGLE = -2.15   # radians; centre of the band, toward the light
HIGHLIGHT_SPREAD = 1.15
HIGHLIGHT_OPACITY_CEL = 0.80
HIGHLIGHT_OPACITY_SOFT = 0.45
SOFT_SHEEN_WIDTH = 0.45         # share of the band thickness used by soft styles
HIGHLIGHT_SOFT_BLUR = 5.0     # canvas units
TIP_TONE_START = -0.2           # head units below the skull centre where tips start to lighten
TIP_TONE_END = 3.2
FLYAWAY_OPACITY = 0.85
SKIN_TINT_OPACITY = 0.20        # fringe picks up skin colour near the face


def _place_lock(head, spec):
    root = head.on_skull([spec.root])[0]
    tip = head.on_skull([spec.tip])[0]
    # Locks mirror their bend when the head frame does not; keep the authored sign.
    return lock(root, tip, head.units(spec.width), spec.bend, spec.sway)


def front_polygons(character, head):
    """Geometry of all hair in front of the face, computed before painting so
    the face can receive its shadow."""
    cap = catmull_rom(head.on_skull(character.hair.cap), closed=True)
    bangs = [_place_lock(head, spec) for spec in character.hair.bangs]
    sides = [_place_lock(head, spec) for spec in character.hair.side_locks]
    return {"cap": cap, "bangs": bangs, "sides": sides}


def front_mask(canvas, polygons):
    shapes = [polygons["cap"]] + [poly for poly, _ in polygons["bangs"] + polygons["sides"]]
    return canvas.mask(*shapes)


def _tone(canvas, head):
    _, ys = canvas.grid()
    start = head.frame.origin[1] + head.units(TIP_TONE_START)
    end = head.frame.origin[1] + head.units(TIP_TONE_END)
    return shading.linear_ramp(ys, start, end)


def _root_fade(canvas, center):
    """0 at the clump root rising to 1 along its length."""
    xs, ys = canvas.grid()
    length = np.linalg.norm(center[-1] - center[0])
    distance = np.sqrt((xs - center[0][0]) ** 2 + (ys - center[0][1]) ** 2)
    return shading.smoothstep(ROOT_FADE[0] * length, ROOT_FADE[1] * length, distance)


def _paint_lock(painter, head, name, polygon, center, material, tone, casts=(), rooted=False):
    canvas = painter.canvas
    mask = canvas.mask(polygon)
    detail = _root_fade(canvas, center) if rooted else None
    painter.part(name, mask, material, roundness=0.75, tone=tone, casts=casts, detail=detail)
    count = len(center)
    taper_to_tip = np.sqrt(np.linspace(1.0, 0.0, count))
    width = np.linalg.norm(polygon[0] - polygon[-1])  # root width of the ribbon
    for share in STRAND_OFFSETS:
        strand = offset_curve(center, share * width * taper_to_tip)[3:-4]
        painter.stroke(strand, head.units(STRAND_WIDTH), material.line, Taper.BOTH,
                       painter.style.detail_line_opacity, clip=mask)


def draw_back_hair(painter, character, head):
    hair = character.palette.hair
    tone = _tone(painter.canvas, head)
    deep = replace(hair, base=mix(hair.base, hair.shadow, BACK_DEPTH_DARKEN),
                   accent=mix(hair.accent, hair.shadow, BACK_DEPTH_DARKEN))
    mass = painter.canvas.mask(catmull_rom(head.flat(character.hair.back_mass), closed=True))
    painter.part("hair_back", mass, deep, roundness=0.25, tone=tone)
    mid = replace(hair, base=mix(hair.base, hair.shadow, BACK_LOCK_DARKEN),
                  accent=mix(hair.accent, hair.shadow, BACK_LOCK_DARKEN))
    for spec in character.hair.back_locks:
        polygon, center = _place_lock(head, spec)
        _paint_lock(painter, head, "hair_back", polygon, center, mid, tone)


def draw_front_hair(painter, character, head, polygons, face_mask):
    canvas = painter.canvas
    hair = character.palette.hair
    tone = _tone(canvas, head)

    for polygon, center in polygons["sides"]:
        _paint_lock(painter, head, "hair_front", polygon, center, hair, tone)
    cap = canvas.mask(polygons["cap"])
    painter.part("hair_front", cap, hair, roundness=0.30, tone=tone)
    # Paint the fringe from the temples inward so the centre clumps overlap the side ones.
    order = sorted(range(len(polygons["bangs"])),
                   key=lambda i: -abs(i - (len(polygons["bangs"]) - 1) / 2))
    for index in order:
        polygon, center = polygons["bangs"][index]
        _paint_lock(painter, head, "hair_front", polygon, center, hair, tone, rooted=True)

    for spec in character.hair.flyaways:
        polygon, _ = _place_lock(head, spec)
        painter.fill(polygon, mix(hair.base, hair.shadow, 0.5), FLYAWAY_OPACITY)

    fringe = canvas.mask(*[poly for poly, _ in polygons["bangs"]])
    forehead = canvas.soft_ellipse(head.on_face([(0.0, 0.15)])[0], head.units(0.95), head.units(0.40),
                                   character.roll)
    painter.glaze(fringe * forehead * face_mask, character.palette.skin.base, SKIN_TINT_OPACITY)
    _draw_highlight(painter, character, head, canvas.mask(polygons["cap"]) + fringe)


def _draw_highlight(painter, character, head, region):
    """Zigzag gloss band ('angel ring') that follows the curve of the skull."""
    canvas = painter.canvas
    style = character.hair
    xs, ys = canvas.grid()
    dx = (xs - head.frame.origin[0]) / head.radius
    dy = (ys - head.frame.origin[1]) / head.radius
    radius = np.sqrt(dx * dx + dy * dy)
    angle = np.arctan2(dy, dx) - character.roll

    # A continuous band with jagged edges: strands break the gloss into teeth.
    # The phase is warped so teeth are uneven, as if placed by hand.
    phase = angle * HIGHLIGHT_TEETH / np.pi + 0.9 * np.sin(angle * 7.3) + 0.5 * np.sin(angle * 17.1)
    tooth_index = np.floor(phase)
    spike = (1.0 - np.abs((phase - tooth_index) * 2.0 - 1.0)) ** 1.4
    tooth_gain = 0.25 + 0.75 * (np.sin(tooth_index * 12.9898) * 43758.5453 % 1.0)
    window = np.exp(-((angle - HIGHLIGHT_LIGHT_ANGLE) / HIGHLIGHT_SPREAD) ** 2)
    window = window * shading.smoothstep(0.15, 0.40, window)   # end the band cleanly, no hairline tail
    crisp = painter.style.shade_mode is ShadeMode.CEL
    # Cel work shows the teeth; soft styles keep only a smooth sheen.
    teeth = (0.22 + 0.78 * spike * tooth_gain) if crisp else SOFT_SHEEN_WIDTH
    half_width = style.highlight_thickness * window * teeth
    edge = (half_width - np.abs(radius - style.highlight_radius)) * canvas.px(head.radius)
    band = np.clip(edge + 0.5, 0.0, 1.0) * np.clip(region, 0.0, 1.0)
    opacity = HIGHLIGHT_OPACITY_CEL if crisp else HIGHLIGHT_OPACITY_SOFT
    edge_blur = 0.0 if crisp else canvas.px(HIGHLIGHT_SOFT_BLUR)
    canvas.blend(shading.blur(band, edge_blur), character.palette.hair_highlight, opacity)
