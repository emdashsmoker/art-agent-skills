"""Face: skin shading and the features (eyes, brows, nose, mouth, ears).

Feature marks are stroked on the colour layer because they belong to the face
in every style, including the painterly one that drops outlines.
"""
import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..color import adjust, light_of, mix, rgb, shadow_of
from ..styles import cast_softness_px, line_color, shade_form

SKIN_SHADOW_TINT = (0.93, 0.77, 0.79)   # skin shadows stay warm and rosy, never grey
SKIN_TERMINATOR = "#f0714f"             # light scattering through skin reddens the shadow edge
SKIN_INK = "#4a2a2e"
FACE_SMOOTHING = 0.45        # heavy blur removes the ridge an inflated V-shaped chin would have
FACE_BEVEL = 0.09            # head units: the face is broad and flat, only its edge turns away from the light
FACE_THRESHOLD_SHIFT = -0.27  # a face takes less form shadow than a ball would
CAP_SHADOW_SHARE = 0.35      # the hair cap lies on the scalp, so its shadow reaches a third as far as a lock's

# Eye shape in eye-local units (x: -1 inner corner .. +1 outer corner, y down).
UPPER_LID = [(-1.0, 0.20), (-0.62, -0.50), (-0.12, -0.80), (0.42, -0.72), (0.84, -0.34), (1.06, -0.10)]
LOWER_LID = [(1.06, -0.10), (0.72, 0.40), (0.12, 0.60), (-0.48, 0.52), (-1.0, 0.20)]
LID_CREASE = [(-0.72, -0.78), (-0.12, -1.24), (0.50, -1.14), (0.98, -0.66)]
LASH_WING = (1.26, -0.34)
# Eye shapes: (upper lid, lower lid, lash wing) in the same eye-local units. "almond" is the default above.
EYE_SHAPES = {
    "almond": (UPPER_LID, LOWER_LID, LASH_WING),
    "round": ([(-1.0, 0.15), (-0.70, -0.62), (-0.18, -0.95), (0.40, -0.90), (0.82, -0.52), (1.0, -0.05)],
              [(1.0, -0.05), (0.74, 0.55), (0.10, 0.78), (-0.52, 0.66), (-1.0, 0.15)], (1.18, -0.22)),
    "droopy": ([(-1.0, 0.05), (-0.60, -0.62), (-0.10, -0.84), (0.40, -0.66), (0.80, -0.22), (1.04, 0.26)],
               [(1.04, 0.26), (0.70, 0.56), (0.10, 0.62), (-0.48, 0.48), (-1.0, 0.05)], (1.16, 0.20)),
    "sharp": ([(-1.0, 0.22), (-0.62, -0.36), (-0.10, -0.62), (0.44, -0.64), (0.86, -0.48), (1.12, -0.34)],
              [(1.12, -0.34), (0.74, 0.16), (0.12, 0.42), (-0.48, 0.44), (-1.0, 0.22)], (1.40, -0.62)),
}
CLOSED_EYE = {"up": 0.55, "down": -0.40}    # bulge of a closed eye's lash line: up for a happy arc, down for calm
BROW_OUTER_X = 0.258                         # face-plane x of the outer end of a brow
BROW_TILT_ARM = 0.10                         # head units over which brow_tilt lifts the inner end
RESTING_SMILE = 0.15                         # smile values up to this keep the plain resting mouth
SMILE_LIFT = 0.014                           # extra corner lift (or drop for a frown) per unit of smile past rest
SMILE_WIDEN = 0.18                           # extra mouth width per unit of smile past rest
MOUTH_OPEN_DEPTH = 0.040                     # head units a fully open mouth drops its lower lip
TEETH_SHARE = 0.32                           # top share of an open mouth showing the upper teeth
# The near eye seen from the side: a wedge closing at the outer corner, its front edge the bulge of the cornea.
UPPER_LID_PROFILE = [(-0.86, 0.42), (-1.0, -0.12), (-0.84, -0.66), (-0.28, -0.70), (0.46, -0.46), (1.06, -0.10)]
LOWER_LID_PROFILE = [(1.06, -0.10), (0.62, 0.22), (0.04, 0.44), (-0.50, 0.50), (-0.86, 0.42)]
PROFILE_CORNEA_SHARE = 0.30  # part of the profile upper lid that runs down the cornea: no lash line there
EYE_HALF_WIDTH = 0.078
EYE_HALF_HEIGHT = 0.040
IRIS_RADIUS = 0.89           # in units of eye half height
PROFILE_EYE_NARROW = 0.42    # seen from the side an eye shows about 0.6 of its front width
PROFILE_IRIS_NARROW = 0.50   # and its iris turns into a tall, narrow oval
EYEBALL_SHIFT = 0.55         # in profile the iris sits at the front of the eye, on the bulge of the eyeball
PROFILE_BROW_NARROW = 0.45   # the near brow shortens with the eye below it
PROFILE_BROW_CENTER = 0.14   # face-plane x the near brow shortens toward

NOSE_TIP_Y, MOUTH_Y, MOUTH_HALF_WIDTH = 0.700, 0.826, 0.064
EAR_FRONT_PROFILE = 0.30     # past this much profile the near ear is drawn over the side of the head
EAR_PROFILE = (0.045, 0.10)  # (front edge, width) of the near ear in a full profile, head units
# Ear outline points as (shift, share of the width, y): x = edge + shift + share * width.
EAR_SHAPE = [(-0.01, 0.0, 0.505), (0.0, 0.75, 0.50), (0.0, 1.0, 0.575), (0.0, 0.72, 0.665), (0.0, 0.25, 0.725),
             (-0.02, 0.0, 0.66)]
EAR_SHAPE_PROFILE = [(-0.005, 0.0, 0.515), (0.0, 0.52, 0.488), (0.0, 1.0, 0.548), (0.0, 0.86, 0.648),
                     (0.0, 0.38, 0.712), (-0.012, 0.0, 0.672)]
EAR_INNER = [(0.25, 0.535), (0.70, 0.55), (0.60, 0.64), (0.22, 0.66)]          # (share of the width, y)
EAR_INNER_PROFILE = [(0.22, 0.545), (0.66, 0.548), (0.62, 0.628), (0.26, 0.648)]
EAR_TILT = 0.22              # in profile the ear leans back: x shift per head unit above its middle
EAR_MIDDLE_Y = 0.60
EAR_RIM_SHADE = 0.024        # head units of soft shade round an ear drawn without outlines
FAR_FEATURE_HIDE = np.radians(56.0)   # past this turn the far eye and brow are hidden behind the nose bridge


BLUSH = ("#f08a8a", "#a8443f")              # cheek colour on fair skin, on deep skin
TERMINATOR_DEEP = "#9a3a22"                  # shadow-edge glow on deep skin
DEEP_LIGHT_TINT, DEEP_LIGHT_AMOUNT = (1.0, 0.86, 0.72), 0.45   # highlights on deep skin: the skin pushed toward warm light
SKIN_DEPTH_RANGE = (0.80, 0.40)              # mean skin brightness over which the warm colours move to their deep version


def skin_depth(skin):
    """0 for fair skin .. 1 for deep skin, from the mean brightness of the skin colour."""
    light, dark = SKIN_DEPTH_RANGE
    return float(np.clip((light - rgb(skin).mean()) / (light - dark), 0.0, 1.0))


def blush_color(skin):
    """Cheek and nose-tip colour for this skin: pink on fair skin, a deeper brick red on deep skin."""
    return mix(BLUSH[0], BLUSH[1], skin_depth(skin))


def skin_light(skin, base):
    """Highlight colour for skin: the near-white base on fair skin, a lit version of the skin itself on deep skin.

    A near-white screened over deep skin greys it out into a chalky patch.
    """
    return mix(base, light_of(skin, DEEP_LIGHT_TINT, DEEP_LIGHT_AMOUNT), skin_depth(skin))


def terminator_color(skin):
    return mix(SKIN_TERMINATOR, TERMINATOR_DEEP, skin_depth(skin))


def skin_shadow_color(spec, style):
    return shadow_of(spec.skin, SKIN_SHADOW_TINT, style.shadow_depth)


# ---- skin ---------------------------------------------------------------------
def visible_ears(frame):
    """[(side, outline points, inner points)] in head units for the ears in view; side -1 near, +1 far.

    Outline points run front top, top, back, back low, lobe, front low (index 4 is the lobe).
    """
    near_width = geo.lerp(geo.lerp(0.030, 0.085, frame.turn), EAR_PROFILE[1], frame.profile)
    visible = [(-1.0, near_width)]                                   # near ear widens as the head turns
    if frame.turn < 0.5:
        visible.append((1.0, geo.lerp(0.030, 0.0, frame.turn * 2)))
    ears = []
    for side, width in visible:
        edge = geo.lerp(geo.lerp(0.335, 0.30, frame.turn), EAR_PROFILE[0], frame.profile) if side < 0 else 0.335
        amount = frame.profile if side < 0 else 0.0
        shape = geo.lerp(np.array(EAR_SHAPE), np.array(EAR_SHAPE_PROFILE), amount)
        lean = EAR_TILT * amount * (EAR_MIDDLE_Y - shape[:, 2])
        points = np.stack([side * (edge + shape[:, 0] + shape[:, 1] * width + lean), shape[:, 2]], axis=1)
        inner_shape = geo.lerp(np.array(EAR_INNER), np.array(EAR_INNER_PROFILE), amount)
        inner_lean = EAR_TILT * amount * (EAR_MIDDLE_Y - inner_shape[:, 1])
        inner_points = np.stack([side * (edge + inner_shape[:, 0] * width + inner_lean), inner_shape[:, 1]], axis=1)
        ears.append((side, points, inner_points))
    return ears


def draw_ears(painting, frame, spec, style):
    """Ears sit behind the head outline; hair usually covers them, short styles reveal them."""
    skin = rgb(spec.skin)
    shadow = skin_shadow_color(spec, style)
    for side, points, inner_points in visible_ears(frame):
        curve = geo.smooth(frame.place(points), closed=True)
        ear = painting.mask(curve)
        painting.part(ear, skin)
        inner = painting.mask(geo.smooth(frame.place(inner_points), closed=True))
        painting.fill(sh.blur(inner, cast_softness_px(style, painting)) * ear, shadow, 0.9)
        if style.line_width > 0:
            painting.outline(curve, frame.px(0.0055) * style.line_width, line_color(style, skin, SKIN_INK))
        else:                # without a line the rim of the ear needs a soft shade to part it from the cheek
            painting.fill(sh.edge_band(ear, frame.px(EAR_RIM_SHADE)) * ear, shadow_of(shadow), 0.85)


def draw_head_skin(painting, frame, spec, style, light, head, contour, front_hair, keep=None, locks=None, joined=None):
    """Flat skin, form shadow, the shadow of the hair, and the warm zones.

    keep: optional outline weight mask; a turned head drops its line where it meets the neck.
    locks: optional mask of the front locks; given, only they throw a long shadow and the cap a short one.
    joined: optional mask of the neck just past the head outline; the form carries on into it without an edge.
    """
    skin = rgb(spec.skin)
    shadow = skin_shadow_color(spec, style)
    light2d = np.asarray(light[:2]) / max(np.linalg.norm(light[:2]), 1e-9)
    soft = cast_softness_px(style, painting)
    painting.part(head, skin)
    shade_form(painting, head, skin, style, light, shadow_color=shadow,
               height=sh.inflate(head if joined is None else np.maximum(head, joined),
                                 bevel=frame.px(FACE_BEVEL), smoothing=FACE_SMOOTHING),
               threshold=style.shadow_threshold + FACE_THRESHOLD_SHIFT,
               terminator=terminator_color(spec.skin) if style.terminator > 0 else None)
    cast_offset = -light2d * frame.px(0.05) + [0.0, frame.px(0.03)]
    if locks is None:
        hair_shadow = sh.cast_shadow(front_hair, head, cast_offset, soft)
    else:
        hair_shadow = np.maximum(sh.cast_shadow(front_hair, head, cast_offset * CAP_SHADOW_SHARE, soft),
                                 sh.cast_shadow(locks, head, cast_offset, soft))
    painting.fill(hair_shadow, shadow)
    if style.gradient > 0.2:     # soft styles also darken the skin where hair closes in on it
        painting.fill(sh.occlusion(front_hair, head, frame.px(0.035)), shadow, 0.5 * style.gradient)
    if style.blush > 0:
        for side in (1.0, -1.0):
            cheek = frame.face([(side * 0.185, 0.655)])[0]
            blush = sh.blur(painting.mask(geo.ellipse(cheek, frame.px(0.062), frame.px(0.030))), frame.px(0.022))
            painting.fill(blush * head, blush_color(spec.skin), 0.42 * style.blush)
        nose = frame.face([(0.0, NOSE_TIP_Y - 0.01)], lift=0.09)[0]
        tip = sh.blur(painting.mask(geo.ellipse(nose, frame.px(0.022), frame.px(0.018))), frame.px(0.012))
        painting.fill(tip * head, blush_color(spec.skin), 0.22 * style.blush)
    if style.line_width > 0:
        ink = line_color(style, skin, SKIN_INK)
        if frame.profile > 0:            # the outline now includes brow, nose, lips and chin
            painting.outline_mask(head, frame.px(0.0060) * style.line_width, ink, keep=keep)
        else:
            painting.outline(contour, frame.px(0.0060) * style.line_width, ink)


# ---- eyes ---------------------------------------------------------------------
class Eye:
    """Geometry of one eye. side: +1 far eye, -1 near eye.

    The near eye takes on its profile shape as the head turns past the three-quarter key: the face plane
    has no eyeball, so the narrowing, the wedge shape and the forward iris stand in for its curve.
    """

    def __init__(self, frame, spec, side):
        self.frame, self.spec, self.side = frame, spec, side
        self.profile = frame.profile if side < 0 else 0.0
        self.center = np.array([side * spec.eye_spacing, spec.eye_y])
        self.half_w = EYE_HALF_WIDTH * spec.eye_size * (1.0 - PROFILE_EYE_NARROW * self.profile)
        self.half_h = EYE_HALF_HEIGHT * spec.eye_size * spec.eye_open
        self.angle = -np.radians(spec.eye_tilt)
        self.iris = IRIS_RADIUS * spec.iris_size
        if spec.eye_shape not in EYE_SHAPES:
            raise ValueError(f"unknown eye_shape: {spec.eye_shape}")
        upper, lower, self.wing = EYE_SHAPES[spec.eye_shape]
        self.upper = self._keyed(upper, UPPER_LID_PROFILE)
        self.lower = self._keyed(lower, LOWER_LID_PROFILE)

    def _keyed(self, front, profile):
        return front if self.profile <= 0 else geo.lerp(np.array(front), np.array(profile), self.profile)

    def curve(self, local_points):
        """Eye-local points -> pixels. Local +x always points to the outer corner."""
        pts = geo.transform(geo.as_points(local_points), angle=self.angle)
        frontal = self.center + pts * [self.side * self.half_w, self.half_h]
        return self.frame.face(frontal)

    def iris_center(self):
        """Iris centre in eye-local units."""
        if self.spec.gaze is None:
            # A turned head looking at the viewer: both irises slide toward the near side.
            shift = -0.30 * self.frame.turn * self.side * (1.0 - self.profile)
        else:
            shift = self.spec.gaze * 0.35 * self.side
        return np.array([shift - EYEBALL_SHIFT * self.profile, -0.10])

    def iris_ring(self, radius_scale=1.0, offset=(0.0, 0.0), squash=1.0):
        radius_y = self.iris * radius_scale
        radius_x = radius_y * self.half_h / self.half_w * 0.94 * (1.0 - PROFILE_IRIS_NARROW * self.profile)
        center = self.iris_center() + np.asarray(offset) * self.iris
        return self.curve(geo.ellipse(center, radius_x, radius_y * squash, count=40))


def _draw_iris(painting, eye, white, iris_color, dark):
    """Dark rim, shaded top, lit lower crescent, pupil: the layers that make an eye look wet."""
    iris = painting.mask(eye.iris_ring()) * white
    painting.fill(iris, adjust(iris_color, value=0.55, saturation=1.1))
    painting.fill(painting.mask(eye.iris_ring(0.86)) * white, iris_color)
    top = eye.curve([eye.iris_center() + [0, -eye.iris]])[0]
    low = eye.curve([eye.iris_center() + [0, eye.iris * 0.5]])[0]
    painting.fill((1.0 - sh.linear_ramp(painting.shape, top, low)) * iris,
                  adjust(iris_color, value=0.30, saturation=1.15), 0.92)
    crescent = painting.mask(eye.iris_ring(0.60, offset=(0.0, 0.42), squash=0.78)) * iris
    painting.fill(sh.blur(crescent, eye.frame.px(0.002)),
                  light_of(adjust(iris_color, saturation=1.25), amount=0.45), 0.85)
    painting.fill(painting.mask(eye.iris_ring(0.42)) * white, dark)


def _draw_catch_lights(painting, eye, white, light2d, strength):
    """Placed in pixel space toward the light so both eyes reflect the same source."""
    center = eye.curve([eye.iris_center()])[0]
    radius = eye.frame.px(eye.half_h * eye.iris)
    main = geo.ellipse(center + light2d * radius * 0.52, radius * 0.26, radius * 0.30)
    painting.fill(painting.mask(main) * white, "#ffffff", 0.96 * max(strength, 0.7))
    small = geo.ellipse(center - light2d * radius * 0.50, radius * 0.11, radius * 0.11)
    painting.fill(painting.mask(small) * white, "#ffffff", 0.75 * strength)


def _draw_lashes(painting, eye, lash_color, skin):
    frame, spec = eye.frame, eye.spec
    # Upper lash line: thin at the inner corner, heaviest past the middle, flicked at the wing.
    lid = geo.resample(geo.smooth(np.vstack([eye.curve(eye.upper), eye.curve([eye.wing])])), 60)
    if eye.profile > 0:                  # in profile the lid starts at the top of the cornea
        lid = geo.resample(geo.subpath(lid, PROFILE_CORNEA_SHARE * eye.profile, 1.0), 60)
    position = np.linspace(0.0, 1.0, len(lid))
    weight = np.interp(position, [0.0, 0.18, 0.62, 0.86, 1.0], [0.30, 0.62, 1.0, 0.72, 0.04])
    weight = np.maximum(weight, np.interp(position, [0.0, 0.25], [0.85, 0.0]) * eye.profile)   # lid edge over the cornea
    painting.stroke(lid, weight * frame.px(0.0135) * spec.eye_size * (0.45 + 0.55 * spec.lashes), lash_color, layer="color")
    outward = frame.side * eye.side
    flicks = ((0.74, (0.9, -0.55), 0.55), (0.86, (1.0, -0.28), 0.50)) if spec.lashes >= 0.6 else ()
    for start, direction, length in flicks:
        root = lid[int(start * (len(lid) - 1))]
        end = root + frame.px(eye.half_w * length) * np.array(direction) * [outward, 1.0]
        painting.stroke(geo.bent_line(root, end, 0.18 * outward), frame.px(0.0075), lash_color,
                        taper=(0.0, 0.9), layer="color")
    if spec.lashes >= 0.6 and eye.profile > 0.5:
        # Seen from the side the upper lashes stand out in front of the eye.
        for start, length in ((0.02, 0.62), (0.10, 0.48)):
            root = lid[int(start * (len(lid) - 1))]
            end = root + frame.px(EYE_HALF_WIDTH * spec.eye_size * length) * np.array([-outward * 0.85, -0.55])
            painting.stroke(geo.bent_line(root, end, -0.2 * outward), frame.px(0.0065), lash_color,
                            taper=(0.0, 0.9), opacity=min(1.0, (eye.profile - 0.5) * 2.0), layer="color")
    # Lower lid: only the outer half is stated, the rest is left to the viewer.
    lower = geo.smooth(eye.curve(eye.lower))
    painting.stroke(geo.subpath(lower, 0.04, 0.52), frame.px(0.0042), mix(lash_color, skin, 0.25),
                    taper=(0.1, 0.7), layer="color")
    painting.stroke(geo.smooth(eye.curve(LID_CREASE)), frame.px(0.0034), mix(lash_color, shadow_of(skin), 0.45),
                    taper=(0.35, 0.35), opacity=0.85, layer="color")


def _draw_closed_eye(painting, eye):
    """A closed eye: one lash line, arched up for a happy face or sagging for a calm one. Returns an empty mask."""
    frame, spec = eye.frame, eye.spec
    lash_color = mix(spec.hair, "#120c10", 0.6)
    bulge = CLOSED_EYE[spec.eyes_closed]
    across = np.linspace(-1.0, 1.08, 24)
    line = eye.curve(np.stack([across, -bulge * (1.0 - across ** 2) + 0.12], axis=1))
    weight = np.interp(np.linspace(0.0, 1.0, len(line)), [0.0, 0.2, 0.7, 1.0], [0.3, 0.8, 1.0, 0.25])
    painting.stroke(line, weight * frame.px(0.011) * spec.eye_size * (0.45 + 0.55 * spec.lashes), lash_color, layer="color")
    if spec.lashes >= 0.6:               # a few lashes at the outer end, pointing away from the arc
        outward = frame.side * eye.side
        for start in (0.80, 0.92):
            root = line[int(start * (len(line) - 1))]
            end = root + frame.px(eye.half_w * 0.35) * np.array([outward * 0.8, 0.6 if bulge < 0 else -0.6])
            painting.stroke(np.array([root, end]), frame.px(0.005), lash_color, taper=(0.0, 0.9), layer="color")
    return np.zeros(painting.shape, dtype=np.float32)


def draw_eye(painting, eye, style, light2d, clip=None):
    spec = eye.spec
    if spec.eyes_closed:
        return _draw_closed_eye(painting, eye)
    opening = np.vstack([geo.smooth(eye.curve(eye.upper)), geo.smooth(eye.curve(eye.lower))[1:-1]])
    white = painting.mask(opening)
    if clip is not None and eye.frame.profile > 0:
        white = white * clip
    lash_color = mix(spec.hair, "#120c10", 0.6)
    # Sclera, shaded from the top because the upper lid and lashes overhang it.
    painting.fill(white, mix("#f6f0ee", spec.skin, 0.12))
    top, bottom = eye.curve([(0.0, -0.80), (0.0, 0.20)])
    lid_shadow = (1.0 - sh.linear_ramp(painting.shape, top, bottom)) * white
    painting.fill(lid_shadow, shadow_of(mix("#e9dfe2", spec.skin, 0.3), style.shadow_tint), 0.85)
    _draw_iris(painting, eye, white, rgb(spec.eye), mix(lash_color, "#000000", 0.5))
    _draw_catch_lights(painting, eye, white, light2d, style.highlight)
    _draw_lashes(painting, eye, lash_color, spec.skin)
    return white


def draw_brow(painting, frame, spec, side):
    brow_y = spec.eye_y - 0.088 * spec.eye_size
    arch = 1.0 / spec.brow                       # heavy brows sit lower and run straighter
    drop = 0.012 * (spec.brow - 1.0)
    points = [(side * 0.058, brow_y + 0.006 + drop), (side * 0.140, brow_y - 0.006 * arch + drop),
              (side * 0.205, brow_y - 0.008 * arch + drop), (side * BROW_OUTER_X, brow_y + 0.012 + drop)]
    if spec.brow_tilt or spec.brow_raise:
        # brow_tilt lifts or lowers the inner end about the outer one; brow_raise moves the whole brow
        lift = np.tan(np.radians(spec.brow_tilt)) * BROW_TILT_ARM
        points = [(x, y - spec.brow_raise - lift * (BROW_OUTER_X - abs(x)) / (BROW_OUTER_X - 0.058)) for x, y in points]
    if side < 0 and frame.profile > 0:
        squeeze = 1.0 - PROFILE_BROW_NARROW * frame.profile
        points = [(-PROFILE_BROW_CENTER + (x + PROFILE_BROW_CENTER) * squeeze, y) for x, y in points]
    path = geo.resample(geo.smooth(frame.face(points)), 40)
    position = np.linspace(0.0, 1.0, len(path))
    widths = np.interp(position, [0.0, 0.10, 0.55, 1.0], [0.50, 1.0, 0.80, 0.06]) * frame.px(0.0145) * spec.brow
    painting.stroke(path, widths, mix(spec.hair, shadow_of(spec.skin), 0.22), opacity=0.92, layer="color")


# ---- nose and mouth -----------------------------------------------------------
def draw_nose(painting, frame, spec, style, light2d, clip=1.0):
    shadow_color = skin_shadow_color(spec, style)
    n = spec.nose                        # size: the tip stands out further and the wings spread wider
    tip = frame.face([(0.0, NOSE_TIP_Y)], lift=0.105 * n)[0]
    bridge = frame.face([(0.0, NOSE_TIP_Y - 0.125), (0.0, NOSE_TIP_Y - 0.055)], lift=[0.05 * n, 0.085 * n])
    base = frame.face([(0.0, NOSE_TIP_Y + 0.036 * n)], lift=0.04 * n)[0]
    # The nose only casts a visible shadow on the side away from the light.
    shadow_side = 1.0 if light2d[0] * frame.side < 0 else -1.0
    wing = frame.face([(shadow_side * 0.034 * n, NOSE_TIP_Y + 0.028 * n)], lift=0.030 * n)[0]
    shadow = painting.mask(geo.smooth([tip, base, wing], closed=True, corners=(0, 1, 2)))
    painting.fill(sh.blur(shadow, cast_softness_px(style, painting) + frame.px(0.0015)) * clip, shadow_color, 0.9)

    ink = mix(shadow_of(shadow_color), SKIN_INK, 0.5)
    # The profile edge of the nose appears as the head turns; a frontal nose is only a hook under the tip.
    under = frame.face([(0.0, NOSE_TIP_Y + 0.030 * n)], lift=0.060 * n)[0]
    profile = geo.smooth([bridge[0], bridge[1], tip, under])
    if frame.profile < 1.0:              # in profile the head outline already draws the nose
        painting.stroke(geo.subpath(profile, 0.78 - 0.45 * frame.turn, 1.0), frame.px(0.0040), ink,
                        taper=(0.6, 0.25), opacity=0.85 * (1.0 - frame.profile), layer="color")
    nostril = frame.face([(-shadow_side * 0.018 * n, NOSE_TIP_Y + 0.033 * n), (-shadow_side * 0.030 * n, NOSE_TIP_Y + 0.028 * n)],
                         lift=0.03 * n)
    painting.stroke(nostril, frame.px(0.0040), ink, taper=(0.3, 0.5), opacity=0.6, layer="color")
    if style.highlight > 0 and style.gradient > 0.2:
        glint = geo.ellipse(tip + light2d * frame.px(0.006), frame.px(0.009), frame.px(0.007))
        painting.fill(sh.blur(painting.mask(glint), frame.px(0.004)) * clip, "#ffffff", 0.5 * style.highlight)


def draw_mouth(painting, frame, spec, style, clip=1.0):
    # Past a faint resting smile the corners lift further and the mouth widens, so a real smile reads at small sizes.
    beyond = max(spec.smile - RESTING_SMILE, 0.0) + min(spec.smile, 0.0)
    y, half, lift = MOUTH_Y, MOUTH_HALF_WIDTH * spec.mouth * (1.0 + SMILE_WIDEN * max(beyond, 0.0)), 0.03
    full = spec.lip_full
    corner_y = y + 0.004 - spec.smile * 0.014 - beyond * SMILE_LIFT
    shadow_color = skin_shadow_color(spec, style)
    across = [-half, -0.48 * half, -0.14 * half, 0.0, 0.14 * half, 0.48 * half, half]
    line_y = [corner_y, y + 0.004, y - 0.002, y + 0.002, y - 0.002, y + 0.004, corner_y]
    # An open mouth drops the lower lip, most at the middle, none at the corners.
    gap = [spec.mouth_open * MOUTH_OPEN_DEPTH * (1.0 - (x / half) ** 2) for x in across]

    def lips(points):
        return geo.smooth(frame.face(points, lift=lift))

    line = lips(list(zip(across, line_y)))
    top = lips([(-half, corner_y), (-0.52 * half, y - 0.013 * full), (-0.17 * half, y - 0.022 * full), (0.0, y - 0.016 * full),
                (0.17 * half, y - 0.022 * full), (0.52 * half, y - 0.013 * full), (half, corner_y)])
    drop = float(np.interp(0.56, [0.0, 1.0], [gap[3], 0.0]))          # the lower lip follows the opening down
    bottom = lips([(half, corner_y), (0.56 * half, y + 0.024 * full + drop), (0.0, y + 0.033 * full + gap[3]),
                   (-0.56 * half, y + 0.024 * full + drop), (-half, corner_y)])
    lip_color = rgb(spec.lip)
    if spec.mouth_open > 0:
        lower_edge = lips(list(zip(across, [ly + g for ly, g in zip(line_y, gap)])))
        opening = painting.mask(np.vstack([line, lower_edge[::-1]]))
        painting.fill(opening * clip, mix(shadow_of(lip_color, style.shadow_tint, 1.0), "#2a0e14", 0.55))
        teeth_edge = lips(list(zip(across, [ly + g * TEETH_SHARE for ly, g in zip(line_y, gap)])))
        teeth = painting.mask(np.vstack([line, teeth_edge[::-1]])) * opening
        painting.fill(teeth * clip, mix("#f4efea", spec.skin, 0.15))
        line_lower = lower_edge
    if spec.lips > 0:
        upper = painting.mask(np.vstack([top, line[::-1]]))
        lower = painting.mask(np.vstack([line if spec.mouth_open <= 0 else line_lower, bottom]))
        soft = frame.px(0.0025)
        # The upper lip faces down, so it is always the darker of the two.
        painting.fill(sh.blur(upper, soft) * clip, shadow_of(lip_color, style.shadow_tint, 0.7), spec.lips)
        painting.fill(sh.blur(lower, soft) * clip, lip_color, spec.lips * 0.92)
        if style.highlight > 0:
            shine = frame.face([(-0.012, y + 0.015 * full + gap[3])], lift=lift)[0]
            glint = painting.mask(geo.ellipse(shine, frame.px(0.016), frame.px(0.0055))) * lower
            painting.fill(sh.blur(glint, frame.px(0.002)) * clip, light_of(lip_color, amount=0.75), 0.75 * style.highlight)
    under = painting.mask(geo.ellipse(frame.face([(0.0, y + 0.050 + gap[3])], lift=0.015)[0], frame.px(0.034), frame.px(0.009)))
    painting.fill(sh.blur(under, frame.px(0.006)) * clip, shadow_color, 0.55)
    ink = mix(shadow_of(lip_color), "#3a1c22", 0.65)
    painting.stroke(line, frame.px(0.0052), ink, taper=(0.3, 0.3), layer="color")
    if spec.mouth_open > 0:
        painting.stroke(line_lower, frame.px(0.0040), ink, taper=(0.4, 0.4), opacity=0.8, layer="color")


def draw_features(painting, frame, spec, style, light2d, clip=None):
    """Nose, mouth, brows and eyes. Returns the union of the two eye-opening masks.

    clip: optional head mask; a far eye on a turned head must not show past the cheek.
    """
    # Turned far, soft marks round the nose and lips would spill past the outline of the face.
    soft_clip = clip if clip is not None and frame.profile > 0 else 1.0
    draw_nose(painting, frame, spec, style, light2d, soft_clip)
    draw_mouth(painting, frame, spec, style, soft_clip)
    eyes = np.zeros(painting.shape, dtype=np.float32)
    sides = (1.0, -1.0) if frame.theta <= FAR_FEATURE_HIDE else (-1.0,)
    for side in sides:
        draw_brow(painting, frame, spec, side)
        eyes = np.maximum(eyes, draw_eye(painting, Eye(frame, spec, side), style, light2d, clip))
    return eyes
