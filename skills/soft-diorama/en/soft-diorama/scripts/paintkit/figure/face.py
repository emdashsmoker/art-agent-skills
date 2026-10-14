"""Face: skin base, ears, eyes, brows, nose, mouth, blush.

Feature shapes are written in small local coordinates and mapped onto the
head surface, so one definition serves every head angle.
"""
from dataclasses import dataclass

import numpy as np

from .. import geometry, raster, shading
from ..color import adjust, mix, rgb
from .look import skin_line, skin_shadow

# Eye shape in local (u, v): u = -1 inner corner .. +1 outer corner,
# v = -1 top of the opening .. +1 bottom. Almond with a lifted outer third.
_EYE_OPENING = [(-1.00, 0.30), (-0.62, -0.50), (-0.12, -0.96), (0.42, -0.90), (0.84, -0.42),
                (1.02, 0.02), (0.66, 0.70), (0.05, 0.93), (-0.55, 0.78)]
_UPPER_LASH = [(-1.04, 0.30), (-0.64, -0.56), (-0.12, -1.04), (0.44, -0.98), (0.88, -0.50), (1.10, 0.04)]
_UPPER_LASH_WIDTH = [0.22, 0.62, 0.95, 1.0, 0.92, 0.35]
_LASH_FLICKS = [[(0.80, -0.62), (1.10, -0.70), (1.34, -0.92)],
                [(0.98, -0.30), (1.22, -0.30), (1.44, -0.44)]]
_LOWER_LID = [(1.04, 0.06), (0.80, 0.56), (0.42, 0.86), (0.05, 0.97)]
_CREASE = [(-0.62, -1.18), (-0.10, -1.52), (0.48, -1.46), (0.92, -1.02)]
_BROW = [(-1.10, -2.48), (-0.35, -2.72), (0.48, -2.70), (1.22, -2.22)]
_BROW_WIDTH = [0.70, 1.0, 0.85, 0.25]

_FLICK_MIN_LASHES = 0.7     # below this lash weight the outer flicks are left off
_EYE_MIN_FACING = 0.10      # an eye turned further away than this is hidden behind the head
_FACE_MIN_FACING = -0.15    # nose, mouth and face planes vanish once the face turns this far away
_CONTACT_YAW = 40.0
_PROFILE_FROM_YAW = 42.0    # nose and lips break the outline only once the head is turned this far         # beyond this head yaw the eyes stop seeking the viewer (profile, back views)
# Profile line of the face at its center (phi 0): (height y, how far it stands in front of the
# skull's section). Nose bridge and tip, the lips, the chin pad. Seen from the side these break
# the plain head outline; seen from the front they lie inside it and add nothing.
_PROFILE = [(0.08, 0.0), (0.18, 0.006), (0.28, 0.055), (0.38, 0.115), (0.44, 0.150), (0.475, 0.125),
            (0.51, 0.050), (0.54, 0.022), (0.60, 0.046), (0.648, 0.040), (0.668, 0.014), (0.69, 0.036),
            (0.72, 0.040), (0.77, 0.016), (0.84, 0.052), (0.92, 0.032), (0.98, 0.0)]
_EYE_CONTACT = 0.22         # iris shift (degrees of phi) per degree of head yaw
_SOFT_LOOK_PX = 4.0         # shade_soft above this gets extra soft facial modeling
_NOSE_Y = 0.44
_MOUTH_Y = 0.665
_BROW_TILT = 1.4            # eye half-heights the inner end of a brow moves at brow_tilt 1
_CORNER_LIFT = 0.07         # head units the mouth corners move at mouth_corners 1
_TEETH_SHARE = 0.55         # share of the mouth opening the upper teeth fill


def _band_above(y, size):
    """Polygon of everything above screen height y."""
    width, height = size
    return [(-1.0, -1.0), (width + 1.0, -1.0), (width + 1.0, y), (-1.0, y)]


@dataclass
class FaceSpec:
    skin: str = '#ffe4d3'
    eye_color: str = '#4f78b8'
    eye_phi: float = 27.0          # degrees from the face center to each eye center
    eye_y: float = 0.13
    eye_half_width: float = 13.0   # degrees around the head
    eye_half_height: float = 0.105  # head units; larger = more stylized/younger
    eye_slant: float = 0.06        # + lifts the outer corners
    gaze: tuple = (0.0, 0.0)       # -1..1 each: (toward screen right, downward)
    eye_contact: bool = True       # irises compensate for head yaw so she looks at the viewer
    lash_color: str = '#2b1f2a'
    brow_color: str = '#5a4038'
    lip_color: str = '#e0787c'
    lip_fullness: float = 0.5      # 0 = line only, 1 = full painted lips
    blush: float = 0.35
    smile: float = 0.4             # -1 frown .. 1 smile
    mouth_open: float = 0.0        # 0 closed .. 1 open
    lashes: float = 1.0            # lash weight; 0.4 with no flicks reads as a man's eyes
    brow_weight: float = 1.0       # brow thickness; 1.6-1.8 for a man
    brow_lift: float = 0.0         # + raises the brows, - lowers them toward the eyes (heavier look)
    brow_tilt: float = 0.0         # + raises the inner ends (worried, sad), - pulls them down (angry)
    lid: float = 0.0               # upper lid drop: 0 open .. 1 closed; below 0 opens the eye wide (surprise)
    squint: float = 0.0            # lower lid rise: 0 .. 1 (cheeks pushed up by a laugh)
    mouth_corners: float = 0.0     # expression: corners pulled up (+, a smile) or down (-, sorrow), -1 .. 1
    mouth_width: float = 1.0       # mouth width scale; narrow and open reads as surprise
    teeth: float = 0.0             # upper teeth showing in an open mouth, 0 .. 1


class _EyeFrame:
    """Maps local eye coordinates onto the head for one eye."""

    def __init__(self, head, spec, side):
        self.head, self.spec, self.side = head, spec, side   # side: +1 screen-right eye, -1 left

    def points(self, local, v_scale=1.0, lidded=True):
        """lidded: the upper lid (lid) and the lower lid (squint) move the points above and below the
        eye's midline; off for the brows, which stay put."""
        local = np.asarray(local, np.float64)
        u, v = local[:, 0], local[:, 1]
        spec = self.spec
        if lidded and (spec.lid or spec.squint):
            v = np.where(v < 0, v * (1.0 - spec.lid), v * (1.0 - spec.squint))
        phi = self.side * (spec.eye_phi + u * spec.eye_half_width)
        y = spec.eye_y + (v * v_scale - spec.eye_slant * u) * spec.eye_half_height
        return self.head.at(phi, y)

    @property
    def height_px(self):
        return self.head.px(self.spec.eye_half_height)


def draw_head_base(cv, head, spec, look):
    """Skin-colored head shape. Returns its mask."""
    mask = cv.polygon(head.silhouette())
    cv.fill(mask, spec.skin)
    return mask


def draw_ear(cv, head, spec, look, side):
    """One ear; returns mask (empty if hidden behind the head)."""
    if head.facing(side * 92.0) < -0.30:
        return cv.empty()
    surface = [(80, 0.04, 0.00), (92, -0.08, 0.035), (104, 0.00, 0.06), (106, 0.20, 0.05),
               (97, 0.40, 0.02), (82, 0.38, 0.00)]
    pts = np.array([head.at(side * phi, y, lift) for phi, y, lift in surface])
    mask = cv.blob(pts)
    cv.fill(mask, spec.skin)
    shade = skin_shadow(spec.skin, look.shade_depth)
    inner = cv.blob(np.array([head.at(side * phi, y, lift) for phi, y, lift in
                              [(90, 0.02, 0.02), (99, 0.04, 0.045), (100, 0.20, 0.04), (92, 0.30, 0.015)]]))
    cv.tint(raster.blur(inner, look.soft_px * 0.5) * mask, shade, 'normal', 0.85)
    cv.outline(mask, 2.2 * look.line_px, skin_line(spec.skin, look), opacity=look.line_opacity)
    return mask


def shade_face(cv, head, face_mask, spec, look, shadow_casters=None):
    """Form shadow, cast shadows from hair, blush. Call before drawing features."""
    shade = skin_shadow(spec.skin, look.shade_depth)
    unit = head.unit
    # Far-side form shadow: thin crescent opposite the light.
    form = shading.crescent(face_mask, look.light, 0.11 * unit, look.soft_px)
    cv.tint(form, shade, 'normal', 0.9)
    if shadow_casters is not None:
        lx, ly = look.light
        drop = shading.cast(shadow_casters, face_mask, (-lx * 0.05 * unit, 0.085 * unit), look.soft_px)
        cv.tint(drop, shade, 'normal', 0.95)
    # Soft warm glow low on the cheeks keeps flat skin from looking like paper.
    warm = adjust(spec.skin, lightness=-0.03, chroma=1.5, toward_hue=30.0, toward=0.4)
    cv.tint(cv.linear(head.at(0, -0.2), head.at(0, 1.0)) * face_mask, warm, 'normal', 0.35)
    if look.shade_soft >= _SOFT_LOOK_PX:
        _soft_modeling(cv, head, face_mask, spec, look, shade)
    if spec.blush > 0:
        blush_color = adjust(spec.lip_color, lightness=0.06, chroma=1.1)
        for side in (-1, 1):
            if head.facing(side * 34.0) < 0.15:
                continue
            center = head.at(side * 34.0, 0.37)
            squeeze = max(head.facing(side * 34.0), 0.35)
            field = cv.radial(center, 0.27 * unit * squeeze, 0.15 * unit)
            cv.tint(field ** 1.5 * face_mask, blush_color, 'normal', spec.blush)


def _soft_modeling(cv, head, face_mask, spec, look, shade):
    """Painted looks need planes, not only edges: side plane, eye sockets, nose, under-lip."""
    unit = head.unit
    light_side = -1.0 if look.light[0] < 0 else 1.0
    side_plane = shading.crescent(face_mask, look.light, 0.24 * unit, 0.07 * unit)
    cv.tint(side_plane, shade, 'normal', 0.55)
    for side in (-1, 1):
        if head.facing(side * spec.eye_phi) < 0.2:
            continue
        socket = cv.radial(head.at(side * spec.eye_phi, spec.eye_y - 1.5 * spec.eye_half_height),
                           0.26 * unit * head.facing(side * spec.eye_phi), 0.13 * unit)
        cv.tint(socket * face_mask, shade, 'normal', 0.30)
    if not face_visible(head):
        return
    ridge = [head.at(0, 0.02, forward=0.02), head.at(0, 0.26, forward=0.06), head.at(0, _NOSE_Y, forward=0.09)]
    nose_side = cv.ribbon([pt - (light_side * 0.035 * unit, 0) for pt in ridge], 0.07 * unit, [0.5, 1.0, 0.8])
    cv.tint(raster.blur(nose_side, 0.022 * unit) * face_mask, shade, 'normal', 0.40)
    under_lip = cv.radial(head.at(0, _MOUTH_Y + 0.13), 0.10 * unit, 0.035 * unit)
    cv.tint(under_lip * face_mask, shade, 'normal', 0.45)
    cheek = cv.radial(head.at(light_side * 30.0, 0.30), 0.30 * unit, 0.22 * unit)
    cv.tint(cheek * face_mask, '#ffffff', 'soft_light', 0.35 * look.highlight)


def face_visible(head):
    """True while the front of the face is turned toward the viewer at all."""
    return head.facing(0.0) > _FACE_MIN_FACING


def draw_profile(cv, head, spec, look, face_mask):
    """Nose, lips and chin standing out of the head outline when the face is seen from the side.
    Returns the added mask (empty for a front view), already painted in skin."""
    if not face_visible(head) or abs(head.yaw) < _PROFILE_FROM_YAW:
        return cv.empty()
    ys = np.array([y for y, _ in _PROFILE])
    forward = np.array([f for _, f in _PROFILE])
    outer = geometry.spline(np.column_stack([ys, forward]), samples=12)
    edge = np.array([head.at(0.0, y, forward=f) for y, f in outer])
    base = np.array([head.at(0.0, y) for y, _ in outer[::-1]])
    profile = cv.polygon(np.vstack([edge, base])) * (1.0 - face_mask)
    cv.fill(profile, spec.skin)
    return profile


def draw_eye(cv, head, spec, look, side):
    """One full eye: white, iris, lid shadow, lashes, crease. Returns opening mask."""
    if head.facing(side * spec.eye_phi) < _EYE_MIN_FACING:
        return cv.empty()
    frame = _EyeFrame(head, spec, side)
    hh = frame.height_px
    opening = cv.blob(frame.points(_EYE_OPENING))
    white = mix('#ffffff', spec.skin, 0.12)
    cv.fill(opening, white)

    iris = _draw_iris(cv, head, spec, look, frame, opening)

    # Upper lid and lashes shade the top of the eyeball.
    lid_shadow = opening * (1.0 - raster.shift(opening, 0, 0.34 * hh))
    cv.tint(raster.blur(lid_shadow, max(look.soft_px * 0.4, 0.8)) * opening,
            rgb('#b9b3cf'), 'multiply', 0.85)

    _draw_eye_highlights(cv, head, look, frame, opening, iris)
    _draw_lashes(cv, spec, look, frame)
    return opening


def _iris_outline(head, spec, frame, radius_scale=1.0, squash=0.80):
    """Ellipse on the head surface; taller than wide like most stylized eyes."""
    radius = 0.93 * spec.eye_half_height * radius_scale
    # A turned head keeps eye contact only if the irises rotate back toward the viewer.
    # Eye contact fades out past _CONTACT_YAW: a face in profile looks ahead, not at the viewer.
    contact_yaw = float(np.clip(head.yaw, -_CONTACT_YAW, _CONTACT_YAW))
    contact_yaw *= float(np.clip(1.0 - (abs(head.yaw) - _CONTACT_YAW) / 30.0, 0.0, 1.0))
    toward_viewer = -contact_yaw * _EYE_CONTACT if spec.eye_contact else 0.0
    center_phi = frame.side * spec.eye_phi + spec.gaze[0] * 0.30 * spec.eye_half_width + toward_viewer
    center_y = spec.eye_y + (-0.06 + spec.gaze[1] * 0.25) * spec.eye_half_height
    angle = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    width_at_eye = 0.725 * np.cos(np.radians(spec.eye_phi))   # d(x)/d(phi) on the surface
    phi = center_phi + np.degrees(squash * radius * np.cos(angle) / width_at_eye)
    y = center_y + radius * np.sin(angle)
    return head.at(phi, y), head.at(center_phi, center_y)


def _draw_iris(cv, head, spec, look, frame, opening):
    outline, center = _iris_outline(head, spec, frame)
    iris = cv.polygon(outline) * opening
    hh = frame.height_px
    base = rgb(spec.eye_color)
    dark = adjust(base, lightness=-0.24, chroma=1.05, hue=-12.0)
    light = adjust(base, lightness=0.12, chroma=1.10, hue=14.0)
    top, bottom = center + (0, -hh), center + (0, hh)
    cv.fill(iris, cv.ramp(cv.linear(top, bottom), (0.0, dark), (0.45, base), (1.0, light)))
    # Dark limbal ring defines the iris against the white.
    ring = iris * (1.0 - raster.grow(iris, -max(0.10 * hh, 1.5)))
    cv.tint(raster.blur(ring, 0.8), adjust(base, lightness=-0.34), 'normal', 0.9)
    _iris_fibers(cv, iris, center, outline, base, look)
    pupil_outline, _ = _iris_outline(head, spec, frame, radius_scale=0.42)
    pupil = cv.polygon(pupil_outline) * opening
    cv.tint(pupil, adjust(base, lightness=-0.45, chroma=0.7), 'normal', 0.95)
    # Light pooling in the lower iris: the signature "glassy" anime eye.
    glow = cv.radial(center + (0, 0.62 * hh), 0.70 * hh * head.facing(frame.side * spec.eye_phi), 0.46 * hh)
    cv.tint(glow * iris, adjust(base, lightness=0.30, chroma=0.9, hue=20.0), 'screen', 0.85 * look.highlight)
    return iris


def _iris_fibers(cv, iris, center, outline, base, look):
    """Fine radial streaks: the iris is a fibrous muscle, and a flat disc looks like a sticker."""
    rng = np.random.default_rng(len(outline))
    strokes = []
    for index in range(0, len(outline), 2):
        edge = outline[index]
        inner = center + (edge - center) * rng.uniform(0.40, 0.55)
        outer = center + (edge - center) * rng.uniform(0.80, 0.95)
        strokes.append(([inner, outer], max(np.linalg.norm(edge - center) * 0.07, 0.8), 'taper'))
    cv.tint(cv.ribbons(strokes) * iris, adjust(base, lightness=0.22, chroma=0.8), 'screen', 0.35 * look.highlight)


def _draw_eye_highlights(cv, head, look, frame, opening, iris):
    hh = frame.height_px
    box = np.argwhere(iris > 0.5)
    if len(box) == 0:
        return
    cy, cx = box.mean(axis=0)
    light_side = -1.0 if look.light[0] < 0 else 1.0
    near = raster.grow(opening, 2)
    main = cv.ellipse(cx + light_side * 0.34 * hh, cy - 0.40 * hh, 0.27 * hh, 0.19 * hh, -25 * light_side)
    small = cv.ellipse(cx - light_side * 0.30 * hh, cy + 0.36 * hh, 0.11 * hh, 0.09 * hh)
    cv.tint(main * near, '#ffffff', 'normal', look.highlight)
    cv.tint(small * near, '#ffffff', 'normal', 0.85 * look.highlight)


def _draw_lashes(cv, spec, look, frame):
    hh = frame.height_px
    scale = max(look.line_scale, 0.55)       # lashes stay visible even in lineless looks
    lash_width = 0.30 * hh * scale * spec.lashes
    lash = cv.ribbon(frame.points(_UPPER_LASH), lash_width, _UPPER_LASH_WIDTH)
    if spec.lashes >= _FLICK_MIN_LASHES:      # light lashes carry no flicks at the outer corner
        for flick in _LASH_FLICKS:
            lash = np.maximum(lash, cv.ribbon(frame.points(flick), 0.17 * hh * scale * spec.lashes, 'in'))
    cv.ink_mask(lash, spec.lash_color)
    skin_ink = skin_line(spec.skin, look)
    cv.ink(frame.points(_LOWER_LID), 0.085 * hh * scale, mix(spec.lash_color, skin_ink, 0.35), 'in')
    cv.ink(frame.points(_CREASE), 0.060 * hh * scale, skin_ink, 'taper', opacity=0.8)


def draw_brow(cv, head, spec, look, side, opacity=1.0):
    if head.facing(side * spec.eye_phi) < _EYE_MIN_FACING - 0.05:
        return
    frame = _EyeFrame(head, spec, side)
    width = 0.20 * frame.height_px * max(look.line_scale, 0.6) * spec.brow_weight
    # Heavier brows sit lower and run straighter.
    brow = [(u, v - spec.brow_lift - (spec.brow_weight - 1.0) * 0.25 * (v + 2.6)) for u, v in _BROW]
    if spec.brow_tilt:                          # the inner end (u = -1) moves, the outer end stays nearly put
        brow = [(u, v - spec.brow_tilt * _BROW_TILT * 0.5 * (1.0 - u)) for u, v in brow]
    cv.ink(frame.points(brow, lidded=False), width, spec.brow_color, _BROW_WIDTH, opacity=opacity)


def draw_nose(cv, head, spec, look, face_mask):
    if not face_visible(head):
        return
    unit = head.unit
    skin_ink = skin_line(spec.skin, look)
    shade = skin_shadow(spec.skin, look.shade_depth)
    turn = np.sin(np.radians(head.yaw))
    light_side = -1.0 if look.light[0] < 0 else 1.0
    tip = head.at(0, _NOSE_Y, forward=0.10)
    # Small shadow under and beside the tip, on the side away from the light.
    under = cv.ellipse(tip[0] - light_side * 0.035 * unit, tip[1] + 0.035 * unit,
                       0.050 * unit, 0.026 * unit, 20 * light_side)
    cv.tint(raster.blur(under, look.soft_px * 0.35) * face_mask, shade, 'normal', 0.9)
    if look.line_scale > 0:
        hook = [head.at(0, _NOSE_Y - 0.035, forward=0.085), tip, head.at(0, _NOSE_Y + 0.030, forward=0.06)]
        cv.ink(hook, 1.7 * look.line_px, skin_ink, 'taper', opacity=0.9)
    # When the head turns, the bridge shows as a soft plane on the far side.
    if abs(turn) > 0.12:
        bridge = [head.at(0, 0.24, forward=0.05), head.at(0, 0.34, forward=0.08), tip]
        strength = min((abs(turn) - 0.12) * 3.0, 1.0)
        far = np.sign(turn)
        plane = cv.ribbon([p + (far * 0.022 * unit, 0) for p in bridge], 0.045 * unit, [0.2, 1.0, 0.7])
        cv.tint(raster.blur(plane, max(look.soft_px, 2.5)) * face_mask, shade, 'normal', 0.35 * strength)
    cv.tint(cv.ellipse(tip[0] + light_side * 0.012 * unit, tip[1] - 0.022 * unit, 0.014 * unit, 0.011 * unit),
            '#ffffff', 'normal', 0.75 * look.highlight)


def draw_mouth(cv, head, spec, look, face_mask):
    if not face_visible(head):
        return
    unit = head.unit
    half = 9.5 * spec.mouth_width                # mouth half-width in degrees
    lift = 0.022 * spec.smile + _CORNER_LIFT * spec.mouth_corners    # corners rise with a smile
    gap = 0.045 * spec.mouth_open
    lip = rgb(spec.lip_color)
    line_color = adjust(lip, lightness=-0.26, chroma=1.1)
    upper = [(-half, _MOUTH_Y - lift), (-half * 0.45, _MOUTH_Y + 0.004), (0, _MOUTH_Y + 0.010),
             (half * 0.45, _MOUTH_Y + 0.004), (half, _MOUTH_Y - lift)]
    if spec.mouth_open > 0:
        # The opening: an arched top under the upper lip, a rounder bottom; narrow, it closes to an O.
        corner = _MOUTH_Y - lift * 0.8
        upper = [(-half * 0.8, corner), (-half * 0.4, _MOUTH_Y - gap * 0.35), (0, _MOUTH_Y - gap * 0.45),
                 (half * 0.4, _MOUTH_Y - gap * 0.35), (half * 0.8, corner)]
        bottom = [(half * 0.45, _MOUTH_Y + gap * 1.5), (0, _MOUTH_Y + gap * 1.75), (-half * 0.45, _MOUTH_Y + gap * 1.5)]
        inside = cv.blob(head.path(upper + bottom))
        cv.tint(inside * face_mask, adjust(lip, lightness=-0.22, chroma=1.2), 'normal', 1.0)
        if spec.teeth > 0:                       # the upper teeth fill the top of the opening
            edge = head.at(0, _MOUTH_Y + gap * _TEETH_SHARE * 1.6)
            band = cv.polygon(np.array(_band_above(edge[1], cv.size)))
            cv.tint(inside * band * face_mask, '#f7f3ee', 'normal', 0.95 * spec.teeth)
    if spec.lip_fullness > 0:
        lower_y = _MOUTH_Y + gap * 1.6
        lower_lip = cv.blob(head.path([(-half * 0.62, lower_y + 0.006), (0, lower_y + 0.012),
                                       (half * 0.62, lower_y + 0.006), (half * 0.30, lower_y + 0.058),
                                       (-half * 0.30, lower_y + 0.058)]))
        upper_lip = cv.blob(head.path([(-half * 0.80, _MOUTH_Y - lift * 0.6), (-half * 0.28, _MOUTH_Y - 0.030),
                                       (0, _MOUTH_Y - 0.020), (half * 0.28, _MOUTH_Y - 0.030),
                                       (half * 0.80, _MOUTH_Y - lift * 0.6), (0, _MOUTH_Y + 0.012)]))
        soft = max(look.soft_px * 0.5, 1.2)
        cv.tint(raster.blur(lower_lip, soft) * face_mask, lip, 'normal', 0.75 * spec.lip_fullness)
        cv.tint(raster.blur(upper_lip, soft) * face_mask, adjust(lip, lightness=-0.05), 'normal',
                0.65 * spec.lip_fullness)
        shine = cv.ellipse(*head.at(-2.0, lower_y + 0.026), 0.030 * unit, 0.010 * unit)
        cv.tint(raster.blur(shine, 1.0), '#ffffff', 'normal', 0.55 * spec.lip_fullness * look.highlight)
    width = 2.4 * max(look.line_scale, 0.5) * look.scale
    cv.ink(head.path(upper), width, line_color, [0.35, 0.9, 1.0, 0.9, 0.35])
