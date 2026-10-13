"""Face rig: head shape, eyes, brows, nose, mouth, blush.

Proportions are encoded once here so a scene script cannot produce a
mis-proportioned face by accident. Eye coordinates are in eye units
(half eye width = 1, x grows toward the outer corner, y down).
"""
import cv2
import numpy as np

from . import shading
from .config import ShadeMode
from .geometry import Taper, catmull_rom, ellipse, lock, ribbon

# Right half of the face outline as (x, y, depth). Depth makes the chin swing
# further than the cheek when the head turns.
FACE_CONTOUR_RIGHT = (
    (0.00, -1.00, 0.00), (0.52, -0.86, 0.00), (0.80, -0.48, 0.00), (0.87, -0.02, 0.04),
    (0.83, 0.36, 0.12), (0.71, 0.66, 0.26), (0.48, 0.93, 0.50), (0.21, 1.13, 0.74),
    (0.00, 1.20, 0.86),
)

UPPER_LID = ((-1.00, 0.14), (-0.66, -0.34), (-0.15, -0.60), (0.42, -0.54), (0.84, -0.24), (1.04, 0.08))
LOWER_LID = ((1.04, 0.08), (0.74, 0.36), (0.18, 0.46), (-0.42, 0.40), (-0.84, 0.26), (-1.00, 0.14))
LASH_LINE = ((-1.02, 0.18), (-0.66, -0.36), (-0.15, -0.63), (0.42, -0.57), (0.86, -0.27),
             (1.08, 0.04), (1.15, 0.24))
LASH_WIDTHS = (0.04, 0.12, 0.18, 0.23, 0.27, 0.19, 0.0)
LASH_SPIKES = (((0.62, -0.44), (1.05, -0.66), 0.16), ((0.88, -0.24), (1.27, -0.36), 0.15))
CREASE = ((-0.58, -0.56), (-0.05, -0.85), (0.55, -0.80), (0.98, -0.46))
BROW = ((-1.08, -1.20), (-0.35, -1.42), (0.45, -1.47), (1.18, -1.22))
BROW_WIDTHS = (0.12, 0.15, 0.11, 0.02)

IRIS_CENTER_Y = -0.08
IRIS_RADIUS_X = 0.52
IRIS_RADIUS_Y = 0.65
PUPIL_RADIUS_X = 0.19
PUPIL_RADIUS_Y = 0.26
HIGHLIGHT_MAIN = (-0.25, -0.34, 0.17, 0.13)    # image-space dx, dy, rx, ry (eye units)
HIGHLIGHT_SMALL = (0.27, 0.30, 0.075, 0.065)
LID_SHADOW_DROP = 0.36                        # eye units the lid shadow falls on the eyeball

NOSE_TIP = (0.0, 0.72, 1.06)
MOUTH_Y = 0.945
MOUTH_HALF_WIDTH = 0.17
FRINGE_SHADOW_DROP = (0.025, 0.06)   # head units
FACE_ROUNDNESS = 0.15                # a face is nearly flat-lit in cel work
BLUSH_CENTER = (0.52, 0.62)


def face_outline(head):
    right = np.asarray(FACE_CONTOUR_RIGHT)
    left = right[-2:0:-1] * np.array([-1.0, 1.0, 1.0])
    return catmull_rom(head.project_face(np.vstack([right, left])), closed=True)


def draw_face(painter, character, head, hair_shadow_source):
    """Skin of the head with the shadow the fringe throws on the forehead."""
    canvas = painter.canvas
    face = canvas.mask(face_outline(head))
    drop = (head.units(FRINGE_SHADOW_DROP[0]), head.units(FRINGE_SHADOW_DROP[1]))
    casts = [painter.cast(hair_shadow_source, face, drop)]
    painter.part("face", face, character.palette.skin, roundness=FACE_ROUNDNESS, casts=casts)
    return face


def draw_features(painter, character, head, face_mask):
    palette = character.palette
    canvas = painter.canvas
    soft = painter.style.shade_mode is ShadeMode.SOFT

    for side in (-1, 1):
        center = head.on_face([(side * BLUSH_CENTER[0], BLUSH_CENTER[1])])[0]
        blush = canvas.soft_ellipse(center, head.units(0.24), head.units(0.12), character.roll)
        painter.glaze(blush * face_mask, palette.blush, 0.34 * character.blush_strength)

    _draw_nose(painter, character, head, face_mask, soft)
    _draw_mouth(painter, character, head, face_mask, soft)
    for side in (-1, 1):
        _draw_eye(painter, character, head, side, face_mask)


def draw_brows_and_lashes_over_hair(painter, character, head, opacity, clip=None):
    """Anime convention: brows and lash lines stay readable through the fringe. clip (a mask of the
    head and its hair) keeps them off the background where a turned head hides the far eye."""
    keep = 1.0 if clip is None else clip
    for side in (-1, 1):
        place = _eye_placer(character, head, side)
        painter.canvas.blend(_brow_mask(painter.canvas, place, character.brow_tilt, character.brow_weight) * keep,
                             character.palette.brow, opacity)
        painter.canvas.blend(_lash_mask(painter.canvas, place, character.lash_weight, character.lash_flicks) * keep,
                             character.palette.lash, opacity * 0.8)


# ---- eye -------------------------------------------------------------------
def _eye_placer(character, head, side):
    """Map eye-unit points to the canvas. side = -1 image-left eye, +1 image-right."""
    half = character.eye_half_width
    angle = -character.eye_slant

    def place(points, open_scale=True):
        p = np.atleast_2d(np.asarray(points, dtype=np.float64)).copy()
        if open_scale:
            p[:, 1] = np.where(p[:, 1] < 0, p[:, 1] * character.eye_open, p[:, 1])
        x = p[:, 0] * np.cos(angle) - p[:, 1] * np.sin(angle)
        y = p[:, 0] * np.sin(angle) + p[:, 1] * np.cos(angle)
        face_xy = np.stack([side * (character.eye_x + half * x), character.eye_y + half * y], axis=1)
        return head.on_face(face_xy)

    return place


def _lash_mask(canvas, place, weight=1.0, flicks=True):
    center = catmull_rom(place(LASH_LINE))
    control_t = np.linspace(0.0, 1.0, len(LASH_WIDTHS))
    widths = np.interp(np.linspace(0.0, 1.0, len(center)), control_t, LASH_WIDTHS)
    unit = np.linalg.norm(place([(1.0, 0.0)])[0] - place([(0.0, 0.0)])[0])
    polygons = [ribbon(center, widths * unit * weight)]
    for root, tip, width in (LASH_SPIKES if flicks else ()):
        polygons.append(lock(place([root])[0], place([tip])[0], width * unit, bend=0.12)[0])
    return canvas.mask(*polygons)


def _brow_mask(canvas, place, tilt, weight=1.0):
    # Tilt pivots the brow about its middle: inner end up, outer end down.
    brow = np.asarray(BROW) + np.array([[0.0, x * tilt] for x, _ in BROW])
    center = catmull_rom(place(brow, open_scale=False))
    control_t = np.linspace(0.0, 1.0, len(BROW_WIDTHS))
    widths = np.interp(np.linspace(0.0, 1.0, len(center)), control_t, BROW_WIDTHS)
    unit = np.linalg.norm(place([(1.0, 0.0)])[0] - place([(0.0, 0.0)])[0])
    return canvas.mask(ribbon(center, widths * unit * weight))


def _draw_eye(painter, character, head, side, face_mask):
    palette = character.palette
    canvas = painter.canvas
    place = _eye_placer(character, head, side)
    unit = np.linalg.norm(place([(0.0, 1.0)])[0] - place([(0.0, 0.0)])[0])  # one eye unit on canvas
    unit_px = canvas.px(unit)

    opening_polygon = np.vstack([catmull_rom(place(UPPER_LID)), catmull_rom(place(LOWER_LID))[1:]])
    opening = canvas.mask(opening_polygon) * face_mask
    lid_shadow = opening * (1 - _shift_down(opening, LID_SHADOW_DROP * unit_px))
    lid_shadow = shading.blur(lid_shadow, max(0.6, unit_px * 0.03))

    canvas.blend(opening, palette.sclera)
    canvas.blend(lid_shadow, palette.sclera_shadow, 0.9)

    gaze_x, gaze_y = character.gaze
    # Gaze is an image-space direction, so both eyes must move the same way.
    iris_center = (gaze_x * side, IRIS_CENTER_Y + gaze_y)
    size = character.iris_scale
    iris_polygon = place(_local_ellipse(iris_center, IRIS_RADIUS_X * size, IRIS_RADIUS_Y * size), open_scale=False)
    iris_full = canvas.mask(iris_polygon)
    iris = iris_full * opening
    _paint_iris(painter, palette, iris, iris_full, unit_px)

    pupil_polygon = place(_local_ellipse(iris_center, PUPIL_RADIUS_X * size, PUPIL_RADIUS_Y * size), open_scale=False)
    canvas.blend(shading.blur(canvas.mask(pupil_polygon), unit_px * 0.025) * iris, palette.pupil, 0.95)
    canvas.blend(shading.blur(lid_shadow, unit_px * 0.05) * iris, palette.pupil, 0.55)

    glow_center = place([(iris_center[0], iris_center[1] + 0.42)], open_scale=False)[0]
    glow = canvas.soft_ellipse(glow_center, unit * 0.42, unit * 0.24, character.roll)
    canvas.blend(glow * iris, palette.iris_glow, 0.75)

    for dx, dy, radius_x, radius_y in (HIGHLIGHT_MAIN, HIGHLIGHT_SMALL):
        # Highlights follow the light, so they sit on the same image side in both eyes.
        local = (iris_center[0] + dx * side * size, iris_center[1] + dy * size)
        spot = place(_local_ellipse(local, radius_x * size, radius_y * size), open_scale=False)
        canvas.blend(canvas.mask(spot) * opening, (1.0, 1.0, 1.0), 0.96)

    lashes = _lash_mask(canvas, place, character.lash_weight, character.lash_flicks)
    canvas.blend(lashes * np.maximum(face_mask, opening), palette.lash)
    outer_lower_lid = catmull_rom(place(LOWER_LID[:3]))
    painter.stroke(outer_lower_lid, unit * 0.07 * character.lash_weight, palette.lash, Taper.END, 0.85,
                   clip=np.maximum(face_mask, opening))
    painter.stroke(catmull_rom(place(CREASE)), unit * 0.045,
                   palette.skin.line, Taper.BOTH, 0.75, clip=face_mask)
    canvas.blend(_brow_mask(canvas, place, character.brow_tilt, character.brow_weight) * face_mask, palette.brow, 0.95)
    canvas.remember("eyes", np.maximum(opening, lashes))


def _paint_iris(painter, palette, iris, iris_full, unit_px):
    canvas = painter.canvas
    rows = np.flatnonzero(iris_full.max(axis=1) > 0)
    if rows.size == 0:
        return
    cols = np.flatnonzero(iris_full.max(axis=0) > 0)
    # Work in the iris's own box (padded so the distance transform sees the outside).
    pad = 3
    box = (slice(max(rows[0] - pad, 0), rows[-1] + pad + 1), slice(max(cols[0] - pad, 0), cols[-1] + pad + 1))
    pixel_rows = np.arange(box[0].start, box[0].start + iris_full[box].shape[0], dtype=np.float32)[:, None] + 0.5
    ramp = shading.linear_ramp(pixel_rows, rows[0], rows[-1])[..., None] ** 1.25
    color = np.zeros(canvas.rgb.shape, dtype=np.float32)
    color[box] = palette.iris_dark * (1 - ramp) + palette.iris_light * ramp
    canvas.blend(iris, color)
    rim = np.zeros(iris_full.shape, dtype=np.float32)
    rim[box] = np.clip(1 - shading.inside_distance(iris_full[box]) / (unit_px * 0.10), 0.0, 1.0)
    canvas.blend(rim * iris, palette.iris_dark, 0.85)


def _local_ellipse(center, radius_x, radius_y):
    return ellipse(center, radius_x, radius_y, samples=48)


def _shift_down(mask, pixels):
    shift = np.float32([[1, 0, 0], [0, 1, pixels]])
    return cv2.warpAffine(mask, shift, (mask.shape[1], mask.shape[0]))


# ---- nose and mouth ----------------------------------------------------------
def _draw_nose(painter, character, head, face_mask, soft):
    palette = character.palette
    canvas = painter.canvas
    tip = head.project_face([NOSE_TIP])[0]
    shadow_side = 1.0  # image-right, away from the light
    wedge = head.project_face([
        (0.02 * shadow_side, 0.655, 1.01), (0.07 * shadow_side, 0.745, 0.98), (0.0, 0.752, 1.05),
    ])
    if soft:
        bridge = head.project_face([(0.07, 0.42, 0.98)])[0]
        canvas.blend(canvas.soft_ellipse(bridge, head.units(0.06), head.units(0.26), character.roll) * face_mask,
                     palette.skin.shadow, 0.45)
        canvas.blend(canvas.soft_ellipse(wedge.mean(axis=0), head.units(0.08), head.units(0.08)) * face_mask,
                     palette.skin.shadow, 0.75)
        canvas.blend(canvas.soft_ellipse(tip - (head.units(0.03), head.units(0.06)),
                                         head.units(0.04), head.units(0.04)) * face_mask,
                     palette.skin.light, 0.7)
    else:
        painter.fill(wedge, palette.skin.shadow, 1.0, clip=face_mask)
    under = head.project_face([(-0.035, 0.765, 1.05), (0.01, 0.775, 1.06), (0.05, 0.765, 1.03)])
    painter.stroke(catmull_rom(under), head.units(0.013), palette.skin.line, Taper.BOTH, 0.8, clip=face_mask)


def _draw_mouth(painter, character, head, face_mask, soft):
    palette = character.palette
    canvas = painter.canvas
    lift = 0.035 * character.smile
    half = MOUTH_HALF_WIDTH * (0.85 + 0.2 * character.smile)
    line = head.on_face([
        (-half, MOUTH_Y - lift), (-half * 0.5, MOUTH_Y + 0.004), (0.0, MOUTH_Y + 0.012),
        (half * 0.5, MOUTH_Y + 0.004), (half, MOUTH_Y - lift),
    ])
    center = head.on_face([(0.0, MOUTH_Y + 0.025)])[0]
    if soft:
        upper = head.on_face([
            (-half, MOUTH_Y - lift), (-half * 0.45, MOUTH_Y - 0.035), (-0.03, MOUTH_Y - 0.045),
            (0.0, MOUTH_Y - 0.032), (0.03, MOUTH_Y - 0.045), (half * 0.45, MOUTH_Y - 0.035),
            (half, MOUTH_Y - lift), (half * 0.5, MOUTH_Y + 0.004), (0.0, MOUTH_Y + 0.012),
            (-half * 0.5, MOUTH_Y + 0.004),
        ])
        lower = head.on_face([
            (-half * 0.92, MOUTH_Y - lift * 0.8), (-half * 0.5, MOUTH_Y + 0.004), (0.0, MOUTH_Y + 0.012),
            (half * 0.5, MOUTH_Y + 0.004), (half * 0.92, MOUTH_Y - lift * 0.8),
            (half * 0.55, MOUTH_Y + 0.060), (0.0, MOUTH_Y + 0.082), (-half * 0.55, MOUTH_Y + 0.060),
        ])
        lips = shading.blur(canvas.mask(catmull_rom(upper, closed=True), catmull_rom(lower, closed=True)),
                            canvas.px(head.units(0.006)))
        canvas.blend(lips * face_mask, palette.lip, 0.85 * character.lip_tint)
        shine = head.on_face([(-0.03, MOUTH_Y + 0.045)])[0]
        canvas.blend(canvas.soft_ellipse(shine, head.units(0.05), head.units(0.014), character.roll) * lips,
                     (1.0, 1.0, 1.0), 0.55)
    else:
        tint = canvas.soft_ellipse(center, head.units(0.15), head.units(0.05), character.roll)
        painter.glaze(tint * face_mask, palette.lip, 0.38 * character.lip_tint)
        under = head.on_face([(-0.06, MOUTH_Y + 0.085), (0.0, MOUTH_Y + 0.095), (0.06, MOUTH_Y + 0.085)])
        painter.stroke(catmull_rom(under), head.units(0.012), palette.skin.shadow, Taper.BOTH, 0.9, clip=face_mask)
    painter.stroke(catmull_rom(line), head.units(0.022), palette.skin.line * 0.85, Taper.BOTH, 0.95, clip=face_mask)
    canvas.remember("mouth", (canvas.soft_ellipse(center, head.units(0.26), head.units(0.12), character.roll) > 0.35)
                    .astype(np.float32) * face_mask)
