"""Body and outfits for a bust: neck, shoulders, and the clothes over them.

The chest follows the head turn only halfway, which makes a turned head
read as a living pose.
"""
import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..color import light_of, rgb, shadow_of
from ..styles import cast_softness_px, line_color, shade_form

NECK_HALF_WIDTH = 0.125
NECK_PROFILE_DEPTH = 0.8     # seen from the side the neck runs from under the jaw back to the nape, so it shows deeper
CHIN_SHADOW_DROP = 0.115     # how far below the jaw its shadow reaches on the neck, head units
PROFILE_CHIN_SHADOW = 0.5    # in profile the jaw sits close over the neck: the shadow shortens by this share
SHOULDER_HALF_WIDTH = 0.62
CANVAS_BOTTOM = 3.0          # far enough below the chin to run off any canvas
BODY_SHIFT = -0.05           # the chest trails behind the turning head
BODY_FAR_SQUEEZE, BODY_NEAR_STRETCH = 0.12, 0.04
LINE_WIDTH = 0.0060          # outline width in head units


def body_points(frame, points):
    """Body-plan units (symmetric, x > 0 is the far side) -> pixels, with a half turn of the chest."""
    pts = geo.as_points(points).copy()
    squeeze = np.where(pts[:, 0] > 0, 1.0 - BODY_FAR_SQUEEZE * frame.turn, 1.0 + BODY_NEAR_STRETCH * frame.turn)
    pts[:, 0] = pts[:, 0] * squeeze + BODY_SHIFT * frame.turn
    return frame.place(pts, tilted=False)


def neck_half_width(frame):
    """Half-width of the neck as drawn: its width from the front, its depth once the head is in profile."""
    return NECK_HALF_WIDTH * (1.0 + NECK_PROFILE_DEPTH * frame.profile)


def shoulder_side(side, grow=0.0, neck=NECK_HALF_WIDTH):
    """One side of the shoulder and arm silhouette, from the base of the neck downward."""
    s = SHOULDER_HALF_WIDTH + grow
    base = max(NECK_HALF_WIDTH * 1.38, neck * 1.06)      # a deep profile neck widens the base of the shoulders
    return [(side * (base + grow), 1.205 - grow), (side * 0.36, 1.285 - grow),
            (side * s * 0.88, 1.355 - grow), (side * s, 1.47), (side * (s + 0.045), 1.72),
            (side * (s + 0.06), CANVAS_BOTTOM)]


def draw_body_skin(painting, frame, spec, style, light, head, skin_shadow, skin_ink):
    """Neck and shoulders, with the shadow the head throws on the neck."""
    n = neck_half_width(frame)
    points = [(n, 0.80), (n * 0.96, 1.06)] + shoulder_side(1.0, neck=n) + shoulder_side(-1.0, neck=n)[::-1] + \
             [(-n * 0.96, 1.06), (-n, 0.80)]
    outline = geo.smooth(body_points(frame, points), closed=True, corners=(0, 7, 8, 15))
    body = painting.mask(outline)
    skin = rgb(spec.skin)
    painting.part(body, skin)
    shade_form(painting, body, skin, style, light, bevel=frame.px(0.10), shadow_color=skin_shadow)
    light_x = light[0] / max(np.hypot(light[0], light[1]), 1e-9)
    # In profile the jaw slopes up to the nape: a sideways slide would open a lit strip under it.
    near = 1.0 - PROFILE_CHIN_SHADOW * frame.profile
    chin_shadow = sh.cast_shadow(head, body, (-light_x * frame.px(0.05) * (1.0 - frame.profile), frame.px(CHIN_SHADOW_DROP * near)),
                                 cast_softness_px(style, painting))
    painting.fill(chin_shadow, skin_shadow)
    if style.line_width > 0:
        painting.outline(outline, frame.px(LINE_WIDTH) * style.line_width, skin_ink)
    return body


def draw_turtleneck(painting, frame, spec, style, light, head):
    cloth = rgb(spec.cloth)
    cloth_shadow = shadow_of(cloth, style.shadow_tint, style.shadow_depth)
    ink = line_color(style, cloth)
    n = neck_half_width(frame)
    collar_w = n * 1.32
    width = frame.px(LINE_WIDTH) * style.line_width
    soft = cast_softness_px(style, painting)

    torso_curve = geo.smooth(body_points(frame, shoulder_side(1.0, 0.022, n) + shoulder_side(-1.0, 0.022, n)[::-1]),
                             closed=True, corners=(0, 5, 6, 11))
    torso = painting.mask(torso_curve)
    painting.part(torso, cloth)
    shade_form(painting, torso, cloth, style, light, bevel=frame.px(0.26))

    top_edge = [(-collar_w, 1.01), (0.0, 1.07), (collar_w, 1.01)]
    fold_edge = [(-collar_w * 1.05, 1.13), (0.0, 1.19), (collar_w * 1.05, 1.13)]
    low_edge = [(-collar_w * 1.0, 1.235), (0.0, 1.30), (collar_w * 1.0, 1.235)]
    collar_pts = [top_edge[0], (-collar_w * 1.07, 1.13), low_edge[0], low_edge[1], low_edge[2],
                  (collar_w * 1.07, 1.13), top_edge[2], top_edge[1]]
    collar_curve = geo.smooth(body_points(frame, collar_pts), closed=True, corners=(0, 6))
    collar = painting.mask(collar_curve)
    # The rolled collar stands off the chest and shades it.
    painting.fill(sh.cast_shadow(collar, torso, (frame.px(0.012), frame.px(0.035)), soft), cloth_shadow, 0.9)
    if width > 0:
        painting.outline(torso_curve, width, ink)
    painting.part(collar, cloth)
    shade_form(painting, collar, cloth, style, light, bevel=frame.px(0.09))
    painting.fill(sh.cast_shadow(head, collar, (frame.px(0.03), frame.px(0.075)), soft), cloth_shadow, 0.9)

    # Knit ribs: short strokes between the collar edges say "wool" without drawing every stitch.
    edges = [geo.resample(geo.smooth(body_points(frame, edge)), 15) for edge in (top_edge, fold_edge, low_edge)]
    for upper, lower in zip(edges[:-1], edges[1:]):
        for a, b in zip(upper[1:-1], lower[1:-1]):
            painting.stroke(np.array([a, b]), frame.px(0.0034), cloth_shadow, taper=(0.3, 0.3),
                            opacity=0.55, layer="color", clip=collar)
    if width > 0:
        painting.outline(collar_curve, width, ink)
        painting.stroke(geo.smooth(body_points(frame, fold_edge)), width * 0.75, ink, taper=(0.15, 0.15))
    return np.maximum(torso, collar)


def draw_blazer(painting, frame, spec, style, light, head):
    inner, jacket = rgb(spec.cloth), rgb(spec.cloth_second)
    width = frame.px(LINE_WIDTH) * style.line_width
    soft = cast_softness_px(style, painting)
    n = neck_half_width(frame)

    top_pts = [(-n * 1.45, 1.19), (0.0, 1.37), (n * 1.45, 1.19), (0.42, CANVAS_BOTTOM), (-0.42, CANVAS_BOTTOM)]
    top_curve = geo.smooth(body_points(frame, top_pts), closed=True, corners=(0, 2, 3, 4))
    top = painting.mask(top_curve)
    painting.part(top, inner)
    shade_form(painting, top, inner, style, light, bevel=frame.px(0.2))
    inner_shadow = shadow_of(inner, style.shadow_tint)
    painting.fill(sh.cast_shadow(head, top, (frame.px(0.03), frame.px(0.10)), soft), inner_shadow, 0.85)
    if width > 0:
        painting.outline(top_curve, width, line_color(style, inner))

    total = top.copy()
    ink = line_color(style, jacket)
    jacket_shadow = shadow_of(jacket, style.shadow_tint)
    for side in (1.0, -1.0):
        panel_pts = [(side * n * 1.22, 1.12)] + shoulder_side(side, 0.03, n)[1:] + \
                    [(side * 0.10, CANVAS_BOTTOM), (side * 0.12, 1.84), (side * n * 1.05, 1.30)]
        panel_curve = geo.smooth(body_points(frame, panel_pts), closed=True, corners=(0, 5, 6, 7))
        panel = painting.mask(panel_curve)
        painting.fill(sh.cast_shadow(panel, top, (frame.px(0.015), frame.px(0.02)), soft), inner_shadow, 0.8)
        painting.part(panel, jacket)
        shade_form(painting, panel, jacket, style, light, bevel=frame.px(0.22))
        lapel_pts = [(side * n * 1.22, 1.12), (side * 0.345, 1.44), (side * 0.255, 1.50), (side * 0.12, 1.84),
                     (side * n * 1.05, 1.30)]
        lapel_curve = geo.smooth(body_points(frame, lapel_pts), closed=True, corners=(0, 1, 2, 3))
        lapel = painting.mask(lapel_curve)
        painting.fill(sh.cast_shadow(lapel, panel, (frame.px(0.012), frame.px(0.018)), soft), jacket_shadow, 0.8)
        lapel_color = light_of(jacket, amount=0.07)
        painting.part(lapel, lapel_color)
        shade_form(painting, lapel, lapel_color, style, light, bevel=frame.px(0.05))
        if width > 0:
            painting.outline(panel_curve, width, ink)
            painting.outline(lapel_curve, width * 0.85, ink)
        total = np.maximum(total, np.maximum(panel, lapel))
    return total


OUTFITS = {"turtleneck": draw_turtleneck, "blazer": draw_blazer}
