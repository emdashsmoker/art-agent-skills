"""Surface anatomy: the few landmarks that make a simplified body read as a real one.

A figure built from tubes is only a mannequin. Collarbones, the weight of the
breasts, the navel, the creases at the hips, the furrow of the spine and the
knees are what the eye checks first, so these are drawn as light marks and
small shadows on top of the skin. Everything stays understated, in the manner
of a classical figure study.
"""
import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..color import mix, rgb, shadow_of
from ..styles import cast_softness_px
from . import face
from .frame import light_on_canvas

BREAST_CENTER = (0.240, 0.660)      # chest coordinates of one breast at bust = 1
BREAST_RADIUS = 0.215               # radius at bust = 1, in head heights
BREAST_SAG = 0.07                   # a fuller breast hangs lower by this much per unit of bust
BREAST_FORWARD = 0.10               # the ball's centre sits this share of its radius in front of the ribcage
BREAST_ROOT = 1.55                  # the upper slope starts this many radii above the centre
BUTTOCK_ROOT = 1.25                 # the lower back runs into the buttock from this many radii above its centre
CHEST_TONE_DIRECTION = (0.16, 0.20)     # chest tone offset from the breast centre (out, down) as a share of the radius
BUTTOCK_DEPTH = 0.90                # depth of a buttock volume as a share of its width
BUTTOCK_SINK = 0.35                 # how far its centre sits inside the back surface, as a share of its depth
BREAST_SPREAD = 0.06                # and sits further from the breastbone
NAVEL = (0.0, -0.50)                # pelvis coordinates
BUTTOCK_CENTER = (0.295, 0.095)     # pelvis coordinates
BUTTOCK_RADIUS = (0.325, 0.36)
BUTTOCK_HIP = 0.70                  # hip half-width the two values above were set for
MARK_WIDTH = 0.016                  # stroke width of a landmark line, in head heights
KNEE_FRONT = 0.12                   # how far the kneecap and shin sit in front of the leg's axis
HIGHLIGHT = "#fff3e6"


def _light(spec):
    """Highlight colour for this figure's skin (see face.skin_light)."""
    return face.skin_light(spec.skin, HIGHLIGHT)


def _marks(spec, style):
    shadow = face.skin_shadow_color(spec, style)
    ink = mix(shadow_of(shadow), face.SKIN_INK, 0.45)
    return shadow, ink


def _soft(painting, skeleton, curve, clip, color, opacity, softness, mode="normal"):
    painting.fill(sh.blur(painting.mask(curve), skeleton.px(softness)) * clip, color, opacity, mode)


def _line_opacity(style, strong, weak):
    """Marks are drawn firmly in line styles and only hinted at where the painting has no lines."""
    return strong if style.line_width > 0 else weak


# ---- front ----------------------------------------------------------------------------
GRAVITY_LEAN = 30.0          # degrees of lean past which breasts settle toward the ground instead of down the body
LYING_SAG = 0.10             # how far a lying figure's breasts slide toward the ground (head heights per unit of bust)
LYING_FLATTEN = 0.40         # how far into the chest a breast sinks, in radii, when the figure lies on its back


def _gravity(skeleton):
    """Down on the picture as a 3D direction in figure units, or None for an upright figure."""
    lean = skeleton.pose.lean
    if abs(lean) < GRAVITY_LEAN:
        return None
    across, down = np.sin(np.radians(lean)), np.cos(np.radians(lean))      # picture-down before the lean
    return across * np.array([skeleton.cos_yaw, 0.0, skeleton.sin_yaw]) + down * np.array([0.0, 1.0, 0.0])


def breast_shapes(skeleton):
    """(sign, centre in pixels, radius in pixels, outline curve) for each breast, the far one first.

    On a turned body each breast is a ball resting on the front of the ribcage, so in a side
    view the near one stands out past the chest line and the far one hides behind it.
    """
    size = skeleton.body.bust
    if size <= 0.05:
        return []
    radius = BREAST_RADIUS * size ** 0.85
    gravity = _gravity(skeleton)
    shapes = []
    for sign in (1.0, -1.0):
        spot = (sign * (BREAST_CENTER[0] + BREAST_SPREAD * (size - 1.0)), BREAST_CENTER[1] + BREAST_SAG * (size - 1.0))
        forward = radius * BREAST_FORWARD
        if gravity is not None:            # lying: the weight settles toward the ground
            slide = BREAST_SAG * (size - 1.0) + LYING_SAG * size
            spot = (spot[0] + slide * gravity[0], spot[1] - BREAST_SAG * (size - 1.0) + slide * gravity[1])
            forward = forward + min(gravity[2], 0.0) * radius * LYING_FLATTEN
        if skeleton.yaw == 0.0:
            center, depth = skeleton.on_chest([spot], surface=True)[0], 0.0
        else:
            ball = skeleton.surface3("chest", [spot]) + [0.0, 0.0, forward]
            center, depth = skeleton.to_pixels(skeleton.project(ball))[0], skeleton.depth_of(ball)[0]
        # slightly taller than wide and leaning outward, as a soft weight hangs from the chest
        curve = geo.ellipse(center, skeleton.px(radius), skeleton.px(radius * 1.06), angle=sign * np.radians(-10), count=56)
        if skeleton.yaw != 0.0:
            # Seen turned, the upper slope runs straight down from the chest to the fullest point:
            # a ball alone reads as a balloon stuck on.
            root = skeleton.to_pixels(skeleton.project(skeleton.surface3("chest", [(spot[0], spot[1] - radius * BREAST_ROOT)])))
            curve = _hull(np.vstack([curve, root]))
        shapes.append((depth, sign, center, skeleton.px(radius), curve))
    shapes.sort(key=lambda shape: shape[0])
    return [shape[1:] for shape in shapes]


def buttock_shapes(skeleton):
    """(sign, centre in pixels, outline curve) of the buttock volumes seen on a turned body."""
    spread = skeleton.body.hip / BUTTOCK_HIP
    lift = 0.82 if skeleton.body.build == "male" else 1.0
    radius_x, radius_y = BUTTOCK_RADIUS[0] * spread, BUTTOCK_RADIUS[1] * spread ** 0.5 * lift
    depth = radius_x * BUTTOCK_DEPTH
    shapes = []
    for sign in (1.0, -1.0):
        spot = (sign * BUTTOCK_CENTER[0] * spread, BUTTOCK_CENTER[1])
        back = skeleton.surface3("pelvis", [spot])
        back[:, 2] = -back[:, 2] * _back_share(skeleton, spot) + depth * BUTTOCK_SINK
        center = skeleton.to_pixels(skeleton.project(back))[0]
        seen_x = np.hypot(radius_x * skeleton.cos_yaw, depth * skeleton.sin_yaw)
        ball = geo.ellipse(center, skeleton.px(seen_x), skeleton.px(radius_y), count=48)
        root = skeleton.surface3("pelvis", [(spot[0], spot[1] - radius_y * BUTTOCK_ROOT)])
        root[:, 2] = -root[:, 2] * _back_share(skeleton, (spot[0], spot[1] - radius_y * BUTTOCK_ROOT))
        shapes.append((sign, center, _hull(np.vstack([ball, skeleton.to_pixels(skeleton.project(root))]))))
    return shapes


def _hull(points):
    """Convex outline of a point set, as a closed curve."""
    from scipy.spatial import ConvexHull
    return points[ConvexHull(points).vertices]


def _back_share(skeleton, spot):
    """Back depth over front depth of the trunk at a pelvis point: turns a front surface point into a back one."""
    from .body import trunk_section
    _, front, back = trunk_section(skeleton.body, [-spot[1]])
    return float(back[0] / max(front[0], 1e-9))


def buttock_mask(painting, skeleton):
    return np.maximum.reduce([painting.mask(curve) for _, _, curve in buttock_shapes(skeleton)])


def breast_mask(painting, skeleton):
    shapes = breast_shapes(skeleton)
    if not shapes:
        return np.zeros(painting.shape, dtype=np.float32)
    return np.maximum.reduce([painting.mask(curve) for _, _, _, curve in shapes])


def draw_collarbones(painting, skeleton, clip, spec, style):
    shadow, ink = _marks(spec, style)
    width = skeleton.px(MARK_WIDTH)
    for sign in (1.0, -1.0):
        bone = geo.smooth(skeleton.on_chest([(sign * 0.05, 0.095), (sign * 0.20, 0.060), (sign * 0.34, 0.075), (sign * 0.44, 0.045)], surface=True))
        painting.stroke(bone, width, ink, taper=(0.25, 0.55), opacity=_line_opacity(style, 0.65, 0.35), layer="color", clip=clip)
        hollow = geo.needle(*skeleton.on_chest([(sign * 0.07, 0.14), (sign * 0.36, 0.115)], surface=True), skeleton.px(0.05))
        _soft(painting, skeleton, hollow, clip, shadow, 0.30, 0.02)
        ridge = geo.needle(*skeleton.on_chest([(sign * 0.10, 0.060), (sign * 0.36, 0.040)], surface=True), skeleton.px(0.028))
        _soft(painting, skeleton, ridge, clip, _light(spec), 0.30 * style.highlight, 0.012, "screen")
        tendon = geo.needle(*skeleton.on_chest([(sign * 0.105, -0.34), (sign * 0.035, 0.07)], surface=True), skeleton.px(0.035))
        _soft(painting, skeleton, tendon, clip, shadow, 0.30, 0.012)
    pit = geo.ellipse(skeleton.on_chest([(0.0, 0.105)], surface=True)[0], skeleton.px(0.035), skeleton.px(0.028))
    _soft(painting, skeleton, pit, clip, shadow, 0.55, 0.012)


def draw_breasts(painting, skeleton, clip, spec, style, light):
    shapes = breast_shapes(skeleton)
    if not shapes:
        return
    shadow, ink = _marks(spec, style)
    skin = rgb(spec.skin)
    light2d = light_on_canvas(light)
    soft = cast_softness_px(style, painting)
    masks = [painting.mask(curve) for _, _, _, curve in shapes]
    for index, (sign, center, radius, curve) in enumerate(shapes):
        # far to near: what a nearer breast covers is no longer this one's to mark
        nearer = np.maximum.reduce(masks[index + 1:]) if index + 1 < len(masks) and skeleton.yaw != 0.0 else 0.0
        own_clip = clip * (1.0 - nearer)
        breast = masks[index] * own_clip
        # weight: the underside turns from the light and throws a soft shadow on the ribs below
        under = sh.cast_shadow(breast, own_clip, (-light2d[0] * radius * 0.14, radius * 0.26), soft + radius * 0.05)
        painting.fill(under * (1.0 - breast), shadow, 0.70)
        lit = sh.lighting(breast, light)
        painting.fill(sh.shadow_from_light(lit, style.shadow_threshold + 0.02, style.edge_softness + 0.06) * breast, shadow, 0.85)
        low = sh.linear_ramp(painting.shape, center, center + [0.0, radius * 1.05]) ** 2 * breast      # fuller, darker toward the base
        painting.fill(low, shadow, 0.35 + 0.25 * style.gradient)
        glow = geo.ellipse(center + light2d * radius * 0.36 - [0.0, radius * 0.10], radius * 0.46, radius * 0.38)
        painting.fill(sh.blur(painting.mask(glow), radius * (0.10 + 0.25 * style.gradient)) * breast, _light(spec),
                      (0.28 + 0.2 * style.gradient) * style.highlight, "screen")
        # the lower curve is the only line needed; the upper slope melts into the chest
        base = geo.arc(center, radius, radius * 1.06, np.radians(2), np.radians(178), 30)
        painting.stroke(base, skeleton.px(MARK_WIDTH), ink, taper=(0.32, 0.32), opacity=_line_opacity(style, 0.85, 0.30),
                        layer="color", clip=own_clip)
        # The chest tone sits on the front of the ball: it slides round and narrows as the body turns.
        out, down = CHEST_TONE_DIRECTION
        forward = np.sqrt(1.0 - out ** 2 - down ** 2)
        facing = -sign * out * skeleton.sin_yaw + forward * skeleton.cos_yaw
        if facing <= 0.05:
            continue
        chest_tone_center = center + np.array([(sign * out * skeleton.cos_yaw + forward * skeleton.sin_yaw) * radius, down * radius])
        squeeze = min(facing / forward, 1.0)
        tone = mix(skin, spec.lip, 0.42)
        chest_tone = geo.ellipse(chest_tone_center, radius * 0.20 * squeeze, radius * 0.18)
        painting.fill(sh.blur(painting.mask(chest_tone), radius * 0.03) * own_clip, tone, 0.75)
        painting.fill(painting.mask(geo.ellipse(chest_tone_center, radius * 0.07 * max(squeeze, 0.5), radius * 0.065)) * own_clip,
                      mix(tone, shadow_of(tone), 0.55), 0.85)
    if skeleton.body.bust >= 0.8:      # the hollow between
        ends = [(0.0, BREAST_CENTER[1] - 0.22), (0.0, BREAST_CENTER[1] + 0.25)]
        seen = float(np.min(skeleton.visibility("chest", ends)))
        if seen > 0.05:
            cleft = geo.needle(*skeleton.on_chest(ends, surface=True), skeleton.px(0.07))
            _soft(painting, skeleton, cleft, clip, shadow, 0.45 * seen, 0.024)


def draw_abdomen(painting, skeleton, clip, spec, style):
    shadow, ink = _marks(spec, style)
    top = skeleton.on_chest([(0.0, 0.95)], surface=True)[0]
    navel = skeleton.on_pelvis([NAVEL], surface=True)[0]
    furrow = geo.needle(top, navel, skeleton.px(0.07))           # the shallow groove down the middle of the belly
    _soft(painting, skeleton, furrow, clip, shadow, 0.30, 0.028)
    for sign in (1.0, -1.0):
        arch = geo.needle(*skeleton.on_chest([(sign * 0.08, 0.95), (sign * 0.32, 1.17)], surface=True), skeleton.px(0.06))
        _soft(painting, skeleton, arch, clip, shadow, 0.22, 0.03)          # lower edge of the ribcage
        # a toned belly: a long soft groove each side of the middle, and a lit plane between groove and flank
        side_top, side_low = skeleton.on_chest([(sign * 0.150, 1.08)], surface=True)[0], skeleton.on_pelvis([(sign * 0.135, -0.36)], surface=True)[0]
        _soft(painting, skeleton, geo.needle(side_top, side_low, skeleton.px(0.045)), clip, shadow, 0.20, 0.026)
        flank_top, flank_low = skeleton.on_chest([(sign * 0.25, 1.15)], surface=True)[0], skeleton.on_pelvis([(sign * 0.25, -0.40)], surface=True)[0]
        _soft(painting, skeleton, geo.needle(flank_top, flank_low, skeleton.px(0.09)), clip, _light(spec), 0.16 * style.highlight, 0.04, "screen")
        # the hip bone shows as a small ridge with a soft hollow inside it
        ridge = geo.needle(*skeleton.on_pelvis([(sign * 0.39, -0.33), (sign * 0.28, -0.10)], surface=True), skeleton.px(0.05))
        _soft(painting, skeleton, ridge, clip, shadow, 0.36, 0.02)
    pit = geo.needle(navel - [0.0, skeleton.px(0.038)], navel + [0.0, skeleton.px(0.038)], skeleton.px(0.030))
    painting.fill(painting.mask(pit) * clip, ink, 0.75)
    hood = geo.ellipse(navel - [0.0, skeleton.px(0.03)], skeleton.px(0.04), skeleton.px(0.03))
    _soft(painting, skeleton, hood, clip, shadow, 0.4, 0.012)
    belly = geo.ellipse(skeleton.on_pelvis([(0.0, -0.20)], surface=True)[0], skeleton.px(0.20), skeleton.px(0.15))
    _soft(painting, skeleton, belly, clip, _light(spec), 0.16 * style.highlight, 0.07, "screen")     # soft swell below the navel


def draw_hip_creases(painting, skeleton, clip, spec, style):
    """Creases where the thighs meet the trunk, and an understated shadow between them."""
    shadow, ink = _marks(spec, style)
    width = skeleton.px(MARK_WIDTH)
    for sign in (1.0, -1.0):
        if f"leg_{'r' if sign > 0 else 'l'}" in skeleton.front_legs:
            continue
        crease = geo.smooth(skeleton.on_pelvis([(sign * 0.45, -0.02), (sign * 0.28, 0.20), (sign * 0.075, 0.37)], surface=True))
        painting.stroke(crease, width, ink, taper=(0.65, 0.15), opacity=_line_opacity(style, 0.65, 0.35), layer="color", clip=clip)
    if skeleton.seated > 0.5:          # sitting: the thighs cover the lower pelvis, so neither shadow nor gap shows
        return
    delta = geo.smooth(skeleton.on_pelvis([(-0.06, 0.33), (0.06, 0.33), (0.0, 0.45)], surface=True), closed=True)
    _soft(painting, skeleton, delta, clip, shadow, 0.32, 0.02)
    gap = skeleton.on_pelvis([(0.0, 0.40), (0.0, 0.64)])
    painting.stroke(gap, width, ink, taper=(0.3, 0.6), opacity=_line_opacity(style, 0.6, 0.35), layer="color", clip=clip)


def draw_lap(painting, skeleton, clip, spec, style):
    """Seated, seen from the front: the folds where the belly meets the raised thighs, and the shadow between them."""
    shadow, ink = _marks(spec, style)
    width = skeleton.px(MARK_WIDTH)
    for sign in (1.0, -1.0):
        fold = geo.smooth(skeleton.on_pelvis([(sign * 0.50, -0.06), (sign * 0.30, 0.06), (sign * 0.08, 0.16)], surface=True))
        painting.stroke(fold, width, ink, taper=(0.6, 0.2), opacity=_line_opacity(style, 0.7, 0.4), layer="color", clip=clip)
    knees = [skeleton.joints[f"knee_{side}"] for side in ("l", "r")]
    hips = skeleton.on_pelvis([(0.0, 0.14)], surface=True)[0]
    between = geo.smooth([hips, geo.lerp(knees[0], knees[1], 0.5) + [0.0, -skeleton.px(0.15)]])
    painting.stroke(between, width, ink, taper=(0.3, 0.5), opacity=_line_opacity(style, 0.55, 0.3), layer="color", clip=clip)
    _soft(painting, skeleton, geo.ellipse(hips + [0.0, skeleton.px(0.10)], skeleton.px(0.10), skeleton.px(0.16)), clip, shadow, 0.35, 0.04)


# ---- a man's front ----------------------------------------------------------------------
PEC_LOW = 0.60                      # chest y of the lower edge of the chest muscle at the breastbone
PEC_OUTER = 0.50                    # chest y where that edge turns up into the armpit
ABS_ROWS = (0.93, 1.17, 1.42)       # chest y of the creases across the stomach muscle
ABS_HALF_WIDTH = 0.155              # stomach muscle half-width at the creases


def draw_pecs(painting, skeleton, clip, spec, style, light):
    """Two broad plates from the breastbone to the armpits, each with a firm lower edge."""
    shadow, ink = _marks(spec, style)
    light2d = light_on_canvas(light)
    width = skeleton.px(MARK_WIDTH)
    reach = skeleton.body.chest + 0.02
    for sign in (1.0, -1.0):
        plate = skeleton.on_chest([(sign * 0.025, 0.14), (sign * 0.30, 0.10), (sign * reach, 0.22),
                                   (sign * (reach + 0.02), PEC_OUTER - 0.04), (sign * (reach - 0.10), PEC_OUTER + 0.08),
                                   (sign * 0.20, PEC_LOW + 0.03), (sign * 0.025, PEC_LOW - 0.02)], surface=True)
        pec = painting.mask(geo.smooth(plate, closed=True)) * clip
        lit = sh.lighting(pec, light, bevel=skeleton.px(0.10))
        painting.fill(sh.shadow_from_light(lit, style.shadow_threshold + 0.04, style.edge_softness + 0.08) * pec, shadow, 0.55)
        under = sh.cast_shadow(pec, clip, (-light2d[0] * skeleton.px(0.01), skeleton.px(0.045)),
                               cast_softness_px(style, painting) + skeleton.px(0.012))
        painting.fill(under * (1.0 - pec), shadow, 0.65)
        edge = geo.smooth(skeleton.on_chest([(sign * 0.03, PEC_LOW - 0.02), (sign * 0.20, PEC_LOW + 0.03),
                                             (sign * (reach - 0.10), PEC_OUTER + 0.08), (sign * (reach + 0.01), PEC_OUTER - 0.06)], surface=True))
        painting.stroke(edge, width, ink, taper=(0.5, 0.2), opacity=_line_opacity(style, 0.75, 0.30), layer="color", clip=clip)
        glow = geo.ellipse(skeleton.on_chest([(sign * 0.24, 0.30)], surface=True)[0], skeleton.px(0.15), skeleton.px(0.10))
        _soft(painting, skeleton, glow, pec, _light(spec), (0.20 + 0.15 * style.gradient) * style.highlight, 0.05, "screen")
        chest_mark = skeleton.on_chest([(sign * 0.25, PEC_OUTER - 0.02)], surface=True)[0]
        tone = mix(rgb(spec.skin), spec.lip, 0.40)
        painting.fill(sh.blur(painting.mask(geo.ellipse(chest_mark, skeleton.px(0.030), skeleton.px(0.026))), skeleton.px(0.006)) * clip, tone, 0.8)
    groove = geo.needle(*skeleton.on_chest([(0.0, 0.16), (0.0, PEC_LOW)], surface=True), skeleton.px(0.05))
    _soft(painting, skeleton, groove, clip, shadow, 0.40, 0.02)


def draw_male_abdomen(painting, skeleton, clip, spec, style):
    """Stomach muscle in blocks, the long groove down the middle, the obliques and the V over the hips."""
    shadow, ink = _marks(spec, style)
    top = skeleton.on_chest([(0.0, PEC_LOW + 0.04)], surface=True)[0]
    navel = skeleton.on_pelvis([NAVEL], surface=True)[0]
    _soft(painting, skeleton, geo.needle(top, navel, skeleton.px(0.05)), clip, shadow, 0.42, 0.016)
    for row, y in enumerate(ABS_ROWS):
        for sign in (1.0, -1.0):
            crease = geo.needle(*skeleton.on_chest([(sign * 0.035, y + 0.015), (sign * ABS_HALF_WIDTH, y - 0.01)], surface=True),
                                skeleton.px(0.034 - 0.004 * row))
            _soft(painting, skeleton, crease, clip, shadow, 0.40 - 0.06 * row, 0.014)
            block = geo.ellipse(skeleton.on_chest([(sign * 0.095, y - 0.10)], surface=True)[0], skeleton.px(0.065), skeleton.px(0.07))
            _soft(painting, skeleton, block, clip, _light(spec), 0.16 * style.highlight, 0.03, "screen")
    for sign in (1.0, -1.0):
        # the outer edge of the muscle: a long soft groove each side
        edge = geo.smooth(np.vstack([skeleton.on_chest([(sign * 0.20, PEC_LOW + 0.10), (sign * 0.21, 1.20)], surface=True),
                                     skeleton.on_pelvis([(sign * 0.17, -0.30)], surface=True)]))
        groove = geo.tube(edge, [skeleton.px(w) for w in (0.010, 0.022, 0.018, 0.008)], count=24)
        _soft(painting, skeleton, groove, clip, shadow, 0.36, 0.02)
        # serratus: three short slants along the ribs under the arm
        for k in range(3):
            y = 0.68 + 0.13 * k
            tooth = geo.needle(*skeleton.on_chest([(sign * (skeleton.body.chest - 0.02), y), (sign * (skeleton.body.chest - 0.12), y + 0.08)], surface=True),
                               skeleton.px(0.03))
            _soft(painting, skeleton, tooth, clip, shadow, 0.24, 0.012)
        # the V over the hip bones runs from the flank down toward the lower pelvis
        v_line = geo.smooth(skeleton.on_pelvis([(sign * 0.42, -0.42), (sign * 0.30, -0.12), (sign * 0.12, 0.22)], surface=True))
        painting.stroke(v_line, skeleton.px(MARK_WIDTH), ink, taper=(0.55, 0.3), opacity=_line_opacity(style, 0.6, 0.3), layer="color", clip=clip)
        _soft(painting, skeleton, geo.tube(v_line + [sign * skeleton.px(0.02), 0.0], [skeleton.px(0.02), skeleton.px(0.035), skeleton.px(0.02)], count=24),
              clip, shadow, 0.30, 0.02)
    pit = geo.needle(navel - [0.0, skeleton.px(0.034)], navel + [0.0, skeleton.px(0.034)], skeleton.px(0.026))
    painting.fill(painting.mask(pit) * clip, ink, 0.7)


# ---- back -----------------------------------------------------------------------------
def draw_back(painting, skeleton, clip, spec, style):
    """Spine furrow, shoulder blades and the two dimples above the hips."""
    shadow, ink = _marks(spec, style)
    width = skeleton.px(MARK_WIDTH)
    nape, lumbar = skeleton.on_chest([(0.0, 0.10)])[0], skeleton.on_pelvis([(0.0, -0.30)])[0]
    _soft(painting, skeleton, geo.needle(nape, lumbar, skeleton.px(0.085)), clip, shadow, 0.42, 0.03)
    spine = geo.smooth([skeleton.on_chest([(0.0, 0.55)])[0], skeleton.on_waist([(0.0, 0.0)])[0], lumbar])
    painting.stroke(spine, width, ink, taper=(0.5, 0.4), opacity=_line_opacity(style, 0.55, 0.25), layer="color", clip=clip)
    for sign in (1.0, -1.0):
        blade = geo.smooth(skeleton.on_chest([(sign * 0.13, 0.30), (sign * 0.17, 0.58), (sign * 0.27, 0.80)]))
        painting.stroke(blade, width, ink, taper=(0.4, 0.5), opacity=_line_opacity(style, 0.45, 0.2), layer="color", clip=clip)
        hollow = geo.needle(*skeleton.on_chest([(sign * 0.10, 0.36), (sign * 0.20, 0.82)]), skeleton.px(0.07))
        _soft(painting, skeleton, hollow, clip, shadow, 0.28, 0.03)
        plane = geo.ellipse(skeleton.on_chest([(sign * 0.30, 0.50)])[0], skeleton.px(0.13), skeleton.px(0.20))
        _soft(painting, skeleton, plane, clip, _light(spec), 0.20 * style.highlight, 0.05, "screen")
        dimple = geo.ellipse(skeleton.on_pelvis([(sign * 0.165, -0.345)])[0], skeleton.px(0.034), skeleton.px(0.028))
        _soft(painting, skeleton, dimple, clip, shadow, 0.55, 0.012)
        flank = geo.needle(*skeleton.on_waist([(sign * 0.24, -0.30), (sign * 0.20, 0.28)]), skeleton.px(0.07))
        _soft(painting, skeleton, flank, clip, shadow, 0.22, 0.03)             # the long muscles either side of the spine


def draw_buttocks(painting, skeleton, clip, spec, style, light):
    """Two soft masses with a short crease under each and the cleft between them.

    The cheeks melt into the back and the hips, so their own edges never show: each one is a
    blurred mask, shaded with a wide soft terminator. Hard cel edges inside the silhouette read as dents.
    """
    shadow, ink = _marks(spec, style)
    light2d = light_on_canvas(light)
    width = skeleton.px(MARK_WIDTH)
    spread = skeleton.body.hip / BUTTOCK_HIP           # narrower hips, smaller and closer-set cheeks
    male = skeleton.body.build == "male"
    lift = 0.82 if male else 1.0                      # a man's buttocks are shorter, flatter and sit higher
    radius_x, radius_y = skeleton.px(BUTTOCK_RADIUS[0] * spread), skeleton.px(BUTTOCK_RADIUS[1] * spread ** 0.5 * lift)
    for sign in (1.0, -1.0):
        center = skeleton.on_pelvis([(sign * BUTTOCK_CENTER[0] * spread, BUTTOCK_CENTER[1])])[0]
        shape = painting.mask(geo.ellipse(center, radius_x, radius_y, count=56)) * clip
        cheek = sh.blur(shape, radius_x * 0.18) * clip
        lit = sh.lighting(shape, (light[0] * 0.45, light[1], light[2]))     # nearly from above, so both cheeks shade alike
        turned = sh.shadow_from_light(lit, style.shadow_threshold - 0.05, style.edge_softness + 0.30)
        painting.fill(turned * cheek, shadow, 0.45 + 0.15 * (1.0 - style.gradient))
        low = sh.linear_ramp(painting.shape, center, center + [0.0, radius_y]) ** 2 * cheek
        painting.fill(low, shadow, 0.22 + 0.2 * style.gradient)
        glow = geo.ellipse(center + light2d * [0.3, 1.0] * radius_x * 0.32 - [0.0, radius_y * 0.12], radius_x * 0.46, radius_y * 0.36)
        painting.fill(sh.blur(painting.mask(glow), radius_x * (0.18 + 0.25 * style.gradient)) * cheek, _light(spec),
                      (0.24 + 0.2 * style.gradient) * style.highlight * (0.5 if male else 1.0), "screen")
        if male:                                       # the hollow at the side of each hip
            hollow = geo.ellipse(center + [sign * radius_x * 0.80, radius_y * 0.05], radius_x * 0.26, radius_y * 0.50)
            painting.fill(sh.blur(painting.mask(hollow), radius_x * 0.30) * clip, shadow, 0.25)
        # the crease under each cheek: only its inner half, firm at the cleft and fading toward the hip
        # arc angles: 90 degrees is straight down; the inner side faces the cleft
        inner_bottom, outer_bottom = (np.radians(150), np.radians(70)) if sign > 0 else (np.radians(30), np.radians(110))
        fold = geo.arc(center, radius_x * 0.96, radius_y * 0.98, inner_bottom, outer_bottom, 20)
        painting.stroke(fold, width, ink, taper=(0.15, 0.85), opacity=_line_opacity(style, 0.7, 0.3), layer="color", clip=clip)
        under = sh.cast_shadow(shape, clip, (0.0, radius_y * 0.12), cast_softness_px(style, painting) + radius_y * 0.10)
        painting.fill(under * (1.0 - cheek), shadow, 0.40)
    top, bottom = skeleton.on_pelvis([(0.0, -0.20), (0.0, 0.45)])
    _soft(painting, skeleton, geo.needle(top, bottom, skeleton.px(0.07)), clip, shadow, 0.45, 0.025)
    painting.stroke(np.array([top, bottom]), width * 1.1, ink, taper=(0.6, 0.1), opacity=_line_opacity(style, 0.75, 0.4),
                    layer="color", clip=clip)


# ---- legs ------------------------------------------------------------------------------
def _leg_axes(skeleton, side):
    knee, ankle = skeleton.joints[f"knee_{side}"], skeleton.joints[f"ankle_{side}"]
    down = (ankle - knee) / max(np.linalg.norm(ankle - knee), 1e-9)
    return knee, down, np.array([-down[1], down[0]])


def draw_knee(painting, skeleton, side, spec, style, clip):
    shadow, ink = _marks(spec, style)
    knee, down, across = _leg_axes(skeleton, side)
    unit = skeleton.unit
    if skeleton.pose.view == "back":
        # the hollow behind the knee: a short crease between two tendons
        crease = geo.bent_line(knee - across * unit * 0.10, knee + across * unit * 0.10, 0.08)
        painting.stroke(crease, unit * MARK_WIDTH * 0.9, ink, taper=(0.3, 0.3), opacity=_line_opacity(style, 0.5, 0.25), layer="color", clip=clip)
        hollow = geo.ellipse(knee - down * unit * 0.03, unit * 0.09, unit * 0.11, angle=np.arctan2(down[1], down[0]) - np.pi / 2)
        painting.fill(sh.blur(painting.mask(hollow), unit * 0.03) * clip, shadow, 0.35)
        return
    knee = knee + np.array([skeleton.sin_yaw * KNEE_FRONT * unit, 0.0])      # the kneecap is on the front of the leg
    facing = abs(skeleton.cos_yaw)
    cap = geo.ellipse(knee - down * unit * 0.02, unit * 0.085, unit * 0.10, angle=np.arctan2(down[1], down[0]) - np.pi / 2)
    under = geo.needle(knee + down * unit * 0.10 - across * unit * 0.07, knee + down * unit * 0.10 + across * unit * 0.07, unit * 0.05)
    painting.fill(sh.blur(painting.mask(under), unit * 0.02) * clip, shadow, 0.40)
    painting.fill(sh.blur(painting.mask(cap), unit * 0.03) * clip, _light(spec), 0.16 + 0.2 * style.gradient)
    for sign in (1.0, -1.0):
        dimple = geo.bent_line(knee + across * sign * unit * 0.085 - down * unit * 0.06,
                               knee + across * sign * unit * 0.070 + down * unit * 0.07, 0.25 * sign)
        painting.stroke(dimple, unit * MARK_WIDTH * 0.9, ink, taper=(0.4, 0.4), opacity=_line_opacity(style, 0.42, 0.2) * facing,
                        layer="color", clip=clip)


def draw_shin(painting, skeleton, side, spec, style, clip):
    """A long soft light down the front of the thigh and the shin: the leg's roundness in one stroke."""
    shift = np.array([skeleton.sin_yaw * KNEE_FRONT * skeleton.unit, 0.0])
    hip, knee, ankle = (skeleton.joints[f"{name}_{side}"] + shift for name in ("hip", "knee", "ankle"))
    unit = skeleton.unit
    for start, end, size in ((geo.lerp(hip, knee, 0.22), geo.lerp(hip, knee, 0.85), 0.10), (geo.lerp(knee, ankle, 0.12), geo.lerp(knee, ankle, 0.80), 0.055)):
        painting.fill(sh.blur(painting.mask(geo.needle(start, end, unit * size)), unit * 0.035) * clip, _light(spec),
                      (0.12 + 0.14 * style.gradient) * style.highlight, "screen")


def draw_toes(painting, skeleton, side, spec, style, clip):
    """Short strokes at the front of the foot; four gaps are enough to say five toes."""
    if skeleton.pose.view == "back":
        return
    _, ink = _marks(spec, style)
    ankle, toe = skeleton.joints[f"ankle_{side}"], skeleton.joints[f"toe_{side}"]
    forward = (toe - ankle) / max(np.linalg.norm(toe - ankle), 1e-9)
    across = np.array([-forward[1], forward[0]])
    unit = skeleton.unit
    for offset in (-0.075, -0.025, 0.025, 0.075):
        start = toe + across * unit * offset + forward * unit * 0.02
        painting.stroke(np.array([start, start + forward * unit * 0.09]), unit * MARK_WIDTH * 0.8, ink,
                        taper=(0.3, 0.2), opacity=0.55 * abs(skeleton.cos_yaw), layer="color", clip=clip)


def draw_leg_marks(painting, skeleton, side, spec, style, clip):
    draw_shin(painting, skeleton, side, spec, style, clip)
    draw_knee(painting, skeleton, side, spec, style, clip)
    draw_toes(painting, skeleton, side, spec, style, clip)


def draw_landmarks(painting, skeleton, clip, spec, style, light):
    """All landmarks of the trunk and of the legs merged into it. clip: the mask they must stay inside."""
    if skeleton.pose.view == "back":
        draw_back(painting, skeleton, clip, spec, style)
        draw_buttocks(painting, skeleton, clip, spec, style, light)
    elif skeleton.body.build == "male":
        front = clip * skeleton.front_visibility(painting.shape)
        draw_collarbones(painting, skeleton, front, spec, style)
        draw_pecs(painting, skeleton, front, spec, style, light)
        draw_male_abdomen(painting, skeleton, front, spec, style)
    else:
        front = clip * skeleton.front_visibility(painting.shape)     # marks on the side turned away disappear
        draw_collarbones(painting, skeleton, front, spec, style)
        draw_breasts(painting, skeleton, clip, spec, style, light)
        draw_abdomen(painting, skeleton, front, spec, style)
        draw_hip_creases(painting, skeleton, front, spec, style)
    for side in ("l", "r"):
        if f"leg_{side}" not in skeleton.front_legs and f"leg_{side}" not in skeleton.behind:
            draw_leg_marks(painting, skeleton, side, spec, style, clip)
