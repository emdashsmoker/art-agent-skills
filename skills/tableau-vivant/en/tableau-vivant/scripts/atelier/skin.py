"""Face and body paint evaluated per pixel: lips, brows, lashes, lid creases, irises, blush, contour, nails.

All shapes are defined in the template space (see figure._template_vertices), so they stick to
the skin through every body shape, expression and pose. The aim is a face that reads as plausible
at a glance: depth around the eyes, a mouth with two lips, eyes that catch light.
"""
import functools
import os
import numpy as np
import cv2

from .shade import material_mask
from . import beard

# Template-space landmarks of the default adult (metres, pelvis origin; front is -Y, up is +Z).
EYE_X, EYE_Z = 0.031, 0.894
FACE_FRONT_Y = -0.085            # template y nearer than this counts as the front of the face
BROW_INNER = (0.0105, 0.9070)    # (x, z)
BROW_PEAK = (0.0360, 0.9150)
BROW_TAIL = (0.0530, 0.9085)
CHEEK_CENTER = (0.046, 0.862)
LIP_PART_Z, LIP_PART_DROP, LIP_HALF_WIDTH = 0.8250, 0.0016, 0.024   # where the lips meet; corners sit lower
# (|x|, y, z, radius) of areas where skin runs redder: knees, elbows, ears, nose tip, shoulders, knuckles, heels
FLESH_ROSY_ZONES = ((0.147, -0.075, -0.28, 0.05), (0.369, -0.010, 0.427, 0.045), (0.082, -0.045, 0.870, 0.022),
                    (0.0, -0.168, 0.860, 0.014), (0.180, -0.02, 0.660, 0.05), (0.505, -0.22, 0.270, 0.03),
                    (0.178, 0.03, -0.790, 0.04))
IRIS_ANGLE = 0.40                # radians from the pupil axis on the eyeball
PUPIL_ANGLE = 0.15
# line thicknesses on the skin, metres
LASH_UPPER_M, LASH_LOWER_M = 0.0021, 0.0007
CREASE_INNER_M, CREASE_OUTER_M = 0.0044, 0.0053
LASH_COLOR_DEFAULT = (0.10, 0.07, 0.07)
# stubble
STUBBLE_EDGE = 0.026             # width of the band over which shaved hair thins out at the edge (m); narrower drew a hard cheek line
STUBBLE_CELL = 0.0011            # spacing of the speckle (one hair)
STUBBLE_COOL = (0.74, 0.77, 0.85)  # shaved hair under skin: the skin's own lightness, greyed and cooled
STUBBLE_HAIR_SHARE = 0.25        # how much of the hair colour itself shows in that shadow
LUMA = (0.299, 0.587, 0.114)
# body relief, modelled as a height field that tilts the surface normals (see shade.apply_bump).
# Entries: (kind, shape, size, height in m, side, group). kind "line": shape = polyline in (|x|, z), size = half-width.
# kind "blob": shape = centre (|x|, z), size = (rx, rz). side: front | back | any. group: muscle (scaled by
# look.muscle_definition) or relief (scaled by look.body_relief, present on every body).
RELIEF = (
    # chest and abdomen
    ("blob", (0.075, 0.505), (0.066, 0.046), 0.0075, "front", "muscle"),                                   # pectorals
    ("line", ((0.012, 0.485), (0.05, 0.462), (0.10, 0.462), (0.15, 0.49), (0.17, 0.53)), 0.008, -0.0045, "front", "muscle"),
    ("line", ((0.0, 0.455), (0.0, 0.20)), 0.005, -0.0028, "front", "muscle"),                              # linea alba
    ("line", ((0.0, 0.405), (0.05, 0.41)), 0.004, -0.0022, "front", "muscle"),                             # tendinous lines
    ("line", ((0.0, 0.345), (0.055, 0.352)), 0.004, -0.0022, "front", "muscle"),
    ("line", ((0.0, 0.285), (0.058, 0.29)), 0.004, -0.0016, "front", "muscle"),
    ("line", ((0.06, 0.44), (0.068, 0.36), (0.064, 0.26), (0.05, 0.20)), 0.006, -0.0032, "front", "muscle"),
    ("blob", (0.030, 0.432), (0.026, 0.024), 0.0026, "front", "muscle"),                                   # abdominal blocks
    ("blob", (0.031, 0.376), (0.027, 0.024), 0.0026, "front", "muscle"),
    ("blob", (0.032, 0.317), (0.028, 0.025), 0.0022, "front", "muscle"),
    ("blob", (0.032, 0.250), (0.027, 0.035), 0.0016, "front", "muscle"),
    ("line", ((0.12, 0.25), (0.085, 0.18), (0.035, 0.10)), 0.008, -0.0045, "front", "muscle"),           # iliac furrow (the V)
    ("blob", (0.105, 0.245), (0.03, 0.05), 0.0028, "front", "muscle"),                                     # obliques
    # back
    ("blob", (0.085, 0.575), (0.05, 0.065), 0.0016, "back", "muscle"),                                      # shoulder blades
    ("blob", (0.032, 0.30), (0.022, 0.12), 0.0016, "back", "muscle"),                                       # spinal erectors
    ("line", ((0.0, 0.66), (0.0, 0.12)), 0.007, -0.0018, "back", "relief"),                                # spine
    ("blob", (0.036, 0.13), (0.012, 0.012), -0.0022, "back", "relief"),                                    # dimples of Venus
    # collarbones and the hollows around them
    ("line", ((0.015, 0.695), (0.08, 0.705), (0.15, 0.715)), 0.006, 0.0026, "front", "relief"),
    ("line", ((0.03, 0.718), (0.08, 0.722), (0.13, 0.73)), 0.008, -0.0018, "front", "relief"),
    ("blob", (0.0, 0.702), (0.012, 0.010), -0.0022, "front", "relief"),                                    # notch at the throat
)
RELIEF_FRONT_Y, RELIEF_BACK_Y, RELIEF_SIDE_FADE = -0.05, 0.03, 0.03
MUSCLE_SCALE = 0.75              # muscle_definition 1.0 = a fit athlete, not a competition bodybuilder
MIN_LINE_PX = 2.5              # below this on-screen width a face line is drawn fainter instead of thicker

DEFAULT_LOOK = dict(
    lip_color=(0.80, 0.40, 0.40), lip_strength=0.78, lip_gloss=0.45,
    brow_color=(0.22, 0.15, 0.12), brow_thickness=1.15, brow_arch=1.0, brow_strength=0.85,
    blush_color=(0.95, 0.55, 0.50), blush_strength=0.20, flesh_variation=0.3, contour=0.5,
    eyeshadow_color=(0.45, 0.30, 0.30), eyeshadow_strength=0.30,
    lash_strength=0.9, lash_width=1.0, lash_color=LASH_COLOR_DEFAULT, crease=0.45,
    nail_color=(0.93, 0.70, 0.68), nail_strength=0.6,
    chest_tone_color=(0.80, 0.52, 0.48), chest_tone_strength=0.40,
    iris_color=(0.36, 0.24, 0.16), iris_size=1.08, pupil_size=1.0,
    sclera_color=(0.95, 0.94, 0.93), iris_shade=0.45, catchlight=0.95, catchlight_size=1.15,
    skin_gloss=0.16,
    stubble=0.0, beard_region="full", beard_color=(0.16, 0.12, 0.10), muscle_definition=0.0, body_relief=0.6,
)


@functools.lru_cache(maxsize=None)
def _uv_mask(name):
    import anny
    from PIL import Image
    path = os.path.join(anny.__path__[0], "data", "mpfb2", "textures", f"mpfb_{name}.jpg")
    return np.asarray(Image.open(path).convert("L"), np.float32) / 255.0


def _sample_uv(name, uv, where):
    """Sample a UV-space mask at covered pixels only."""
    tex = _uv_mask(name)
    size = tex.shape[0]
    # remap over the full frame (its row/column limits rule out one long strip of samples)
    map_u = (uv[..., 0] * size - 0.5).astype(np.float32)
    map_v = ((1.0 - uv[..., 1]) * size - 0.5).astype(np.float32)
    return cv2.remap(tex, map_u, map_v, cv2.INTER_LINEAR) * where


def _mix(albedo, color, alpha):
    albedo += (np.asarray(color, np.float32) - albedo) * alpha[..., None]


def _blob(x, z, centre, radius):
    """Soft elliptical patch in the face plane. radius = (rx, rz)."""
    return np.exp(-(((x - centre[0]) / radius[0]) ** 2 + ((z - centre[1]) / radius[1]) ** 2))


def _brow_mask(x, z, thickness, arch):
    """Soft brow shape from a curve through inner, peak and tail points (template x is mirrored)."""
    (x0, z0), (x1, z1), (x2, z2) = BROW_INNER, BROW_PEAK, BROW_TAIL
    z1 = z0 + (z1 - z0) * arch
    t = np.clip((x - x0) / (x2 - x0), 0, 1)
    tp = (x1 - x0) / (x2 - x0)
    # piecewise smooth centre line: rises to the peak, then falls to the tail
    rise = z0 + (z1 - z0) * np.sin(np.clip(t / tp, 0, 1) * np.pi / 2)
    fall = z2 + (z1 - z2) * np.cos(np.clip((t - tp) / (1 - tp), 0, 1) * np.pi / 2)
    centre = np.where(t < tp, rise, fall)
    half = 0.0030 * thickness * (1.0 - 0.72 * t ** 1.5)          # thick at the nose, thin at the temple
    inside = (x > x0 - 0.002) & (x < x2 + 0.001)
    soft = 0.0016                                                # hairs thin out at the edge instead of ending in a line
    ends = np.clip((x - (x0 - 0.002)) / 0.006, 0, 1) * np.clip(((x2 + 0.001) - x) / 0.003, 0, 1)
    return np.clip((half - np.abs(z - centre)) / soft + 0.5, 0, 1) * inside * ends


def _ring(mask, skin, inner_px, outer_px):
    """Skin pixels whose distance to `mask` lies between two radii (screen pixels)."""
    def grow(radius):
        r = max(int(round(radius)), 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        return cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)
    outer = grow(outer_px)
    return (outer & ~grow(inner_px) if inner_px >= 1 else outer) & skin


def _paint_eye_surround(g, albedo, look, skin, eye, x, z):
    """Lash lines, the upper-lid crease and the lower lid: what makes an eye read as an eye."""
    depth = np.nanmedian(g["depth"][eye])
    px = g["camera"].focal_px / depth                    # pixels per metre at the eyes
    upper = z > EYE_Z + 0.0005
    outer_half = x > EYE_X + 0.003
    lash_rgb = look["lash_color"]
    width = LASH_UPPER_M * look["lash_width"]
    line = _ring(eye, skin, 0, width * px) & upper
    wing = _ring(eye, skin, 0, width * 1.9 * px) & upper & outer_half      # lashes gather toward the outer corner
    sigma = max(width * px * 0.3, 0.6)
    band = cv2.GaussianBlur((line | wing).astype(np.float32), (0, 0), sigma)
    # a small, distant face cannot hold full-strength lines: they would swallow the eye
    fade = float(np.clip(width * px / MIN_LINE_PX, 0.25, 1.0))
    _mix(albedo, lash_rgb, np.clip(band * 1.7, 0, 1) * skin * look["lash_strength"] * fade)
    lower = cv2.GaussianBlur((_ring(eye, skin, 0, LASH_LOWER_M * px) & ~upper).astype(np.float32), (0, 0), 0.7)
    lower_fade = float(np.clip(LASH_LOWER_M * px / MIN_LINE_PX, 0.0, 1.0))
    _mix(albedo, lash_rgb, np.clip(lower * 1.4, 0, 1) * skin * 0.35 * look["lash_strength"] * lower_fade)
    if look["crease"] > 0 and CREASE_INNER_M * px > 3.0:
        fold = _ring(eye, skin, CREASE_INNER_M * px, CREASE_OUTER_M * px) & upper & (x > EYE_X - 0.011) & (x < EYE_X + 0.016)
        fold = cv2.GaussianBlur(fold.astype(np.float32), (0, 0), max(0.0004 * px, 0.7))
        _mix(albedo, albedo * 0.55, np.clip(fold * 1.5, 0, 1) * skin * look["crease"])


def _paint_iris(g, albedo, glow_rgb, glow_alpha, look, eye):
    angle, side, up = (g["attrs"]["eye"][..., i] for i in range(3))
    iris_r = IRIS_ANGLE * look["iris_size"]
    pupil_r = PUPIL_ANGLE * look["pupil_size"]
    soft = 0.02
    in_iris = np.clip((iris_r - angle) / soft + 0.5, 0, 1) * eye
    in_pupil = np.clip((pupil_r - angle) / soft + 0.5, 0, 1) * eye
    # sclera: never pure white; the upper lid throws a shadow across the top of the eyeball
    lid_shadow = np.clip(up * 2.2 + 0.25, 0, 1)
    sclera = np.asarray(look["sclera_color"], np.float32) * (1 - 0.34 * lid_shadow)[..., None] * np.array([0.98, 0.99, 1.0], np.float32)
    albedo[eye] = sclera[eye]
    iris_rgb = np.asarray(look["iris_color"], np.float32)
    radius = np.clip(angle / iris_r, 0, 1)
    azimuth = np.arctan2(up, side)
    fibres = 0.5 + 0.5 * np.sin(azimuth * 26 + np.sin(azimuth * 7) * 2.0)                # radial streaks
    shade = 1.0 - look["iris_shade"] * np.clip(up / np.sin(iris_r) * 0.5 + 0.5, 0, 1)     # darker under the upper lid
    # lighter ring around the pupil, darker toward the rim, a brighter crescent opposite the catchlight
    profile = 1.25 - 0.55 * radius ** 2 + 0.12 * (fibres - 0.5)
    crescent = np.clip(-up / np.sin(iris_r), 0, 1) ** 1.5 * 0.45
    iris = np.clip(iris_rgb[None, None] * (shade * profile + crescent)[..., None], 0, 1)
    _mix(albedo, iris, in_iris)
    limbus = np.exp(-((angle - iris_r) / 0.04) ** 2) * eye * (angle < iris_r + 0.05)
    _mix(albedo, iris_rgb * 0.25, limbus * 0.75)
    _mix(albedo, (0.02, 0.015, 0.02), in_pupil)
    if look["catchlight"] > 0:
        # catchlights sit on the eyeball, toward the key light; a small second one echoes it
        to_light = -g["light_dir"] / np.linalg.norm(g["light_dir"])
        cx = 0.17 * np.sign(to_light @ g["camera"].right or 1.0)
        size = 0.085 * look["catchlight_size"]
        main = np.clip((1 - np.hypot(side - cx, up - 0.17) / size) / 0.25, 0, 1)
        echo = np.clip((1 - np.hypot(side + cx * 0.9, up + 0.13) / (size * 0.45)) / 0.3, 0, 1) * 0.6
        spot = np.maximum(main, echo) * eye * (angle < iris_r * 1.25)
        glow_alpha[:] = np.maximum(glow_alpha, spot * look["catchlight"])


def _line_distance(x, z, points):
    """Distance (m) in the (|x|, z) plane to a polyline given as [(x, z), ...]."""
    best = np.full(x.shape, np.inf, np.float32)
    for (x0, z0), (x1, z1) in zip(points[:-1], points[1:]):
        dx, dz = x1 - x0, z1 - z0
        t = np.clip(((x - x0) * dx + (z - z0) * dz) / (dx * dx + dz * dz), 0, 1)
        best = np.minimum(best, np.hypot(x - (x0 + t * dx), z - (z0 + t * dz)))
    return best


def _body_height(x, y, z, muscle, relief):
    """Height field (m) of muscle and bone relief at template positions; x is |x|."""
    front = np.clip((RELIEF_FRONT_Y - y) / RELIEF_SIDE_FADE, 0, 1)
    back = np.clip((y - RELIEF_BACK_Y) / RELIEF_SIDE_FADE, 0, 1)
    height = np.zeros(x.shape, np.float32)
    for kind, shape, size, amount, side, group in RELIEF:
        scale = muscle if group == "muscle" else relief
        if scale <= 0:
            continue
        if kind == "line":
            d = _line_distance(x, z, shape)
            profile = np.exp(-(d / size) ** 2)
        else:
            r2 = ((x - shape[0]) / size[0]) ** 2 + ((z - shape[1]) / size[1]) ** 2
            profile = np.clip(1 - r2, 0, 1) ** 2
        where = front if side == "front" else back if side == "back" else 1.0
        height += profile * amount * scale * where * (MUSCLE_SCALE if group == "muscle" else 1.0)
    return height


def make_painter(figure_name, look=None):
    """Painter closure for one figure; plugs into shade.albedo_map(painters=...)."""
    look = {**DEFAULT_LOOK, **(look or {})}

    def paint(g, albedo, glow_rgb, glow_alpha):
        skin = material_mask(g, f"{figure_name}.skin")
        eye = material_mask(g, f"{figure_name}.eye")
        if skin.any():
            tpl = g["attrs"]["tpl"]
            x, y, z = np.abs(tpl[..., 0]), tpl[..., 1], tpl[..., 2]
            front = skin & (y < FACE_FRONT_Y) & (z > 0.78)
            uv = g["uv"]
            g["gloss"][skin] = look["skin_gloss"]
            if look["contour"] > 0:
                # light and shade a make-up artist would place: depth at the sockets and under the cheekbones,
                # light on the bridge of the nose, the cheekbones and the chin
                c = look["contour"]
                shade = _blob(x, z, (EYE_X, 0.9035), (0.020, 0.0075)) * 0.30 + _blob(x, z, (0.014, 0.892), (0.006, 0.012)) * 0.28 + \
                    _blob(x, z, (0.058, 0.842), (0.016, 0.020)) * 0.20 + _blob(x, z, (0.0, 0.8065), (0.016, 0.004)) * 0.22
                light = _blob(x, z, (0.0, 0.885), (0.0045, 0.022)) * 0.22 + _blob(x, z, (0.048, 0.875), (0.014, 0.008)) * 0.16 + \
                    _blob(x, z, (0.0, 0.792), (0.010, 0.007)) * 0.12 + _blob(x, z, (0.0, 0.8385), (0.006, 0.0025)) * 0.18
                warm_shadow = albedo * np.array([0.80, 0.66, 0.62], np.float32)
                _mix(albedo, warm_shadow, np.clip(shade * c, 0, 1) * front)
                _mix(albedo, np.clip(albedo * 1.12 + 0.04, 0, 1), np.clip(light * c, 0, 1) * front)
            lips = _sample_uv("lips", uv, skin)
            lower_lip = z < LIP_PART_Z - LIP_PART_DROP * np.clip(x / LIP_HALF_WIDTH, 0, 1) ** 2
            lip_rgb = np.asarray(look["lip_color"], np.float32)
            _mix(albedo, np.where(lower_lip[..., None], lip_rgb, lip_rgb * 0.84), lips * look["lip_strength"])
            # where the lips meet: a dark line, strongest at the centre and fading before the corners
            part = LIP_PART_Z - LIP_PART_DROP * np.clip(x / LIP_HALF_WIDTH, 0, 1) ** 2
            seam = np.exp(-((z - part) / 0.0009) ** 2) * (x < LIP_HALF_WIDTH + 0.003) * front
            _mix(albedo, lip_rgb * 0.38, seam * 0.75 * np.clip(look["lip_strength"] + 0.3, 0, 1))
            lip_shine = lips * lower_lip * _blob(x, z, (0.0, 0.8195), (0.012, 0.0035))
            g["gloss"][skin] = np.maximum(g["gloss"], look["lip_gloss"] * lips)[skin]
            g["shine"][lips > 0.5] = 45.0
            glow_alpha[:] = np.maximum(glow_alpha, lip_shine * look["lip_gloss"] * 0.5)
            nails = _sample_uv("fingernails", uv, skin) + _sample_uv("toenails", uv, skin)
            _mix(albedo, look["nail_color"], nails * look["nail_strength"])
            g["gloss"][nails > 0.5] = 0.5
            g["shine"][nails > 0.5] = 50.0
            _mix(albedo, look["chest_tone_color"], _sample_uv("aureolae", uv, skin) * look["chest_tone_strength"])
            lids = _sample_uv("eyelids", uv, skin)
            _mix(albedo, look["eyeshadow_color"], lids * look["eyeshadow_strength"])
            cheek = _blob(x, z, CHEEK_CENTER, (0.022, 0.016))
            _mix(albedo, look["blush_color"], cheek * front * look["blush_strength"])
            if look["flesh_variation"] > 0:
                # living skin is not one colour: blood shows at joints, extremities, ears and the nose
                rosy = np.zeros(skin.shape, np.float32)
                for cx, cy, cz, radius in FLESH_ROSY_ZONES:
                    rosy += np.exp(-(((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2) / radius ** 2))
                rosy += np.clip((x - 0.515) / 0.03, 0, 1) + np.clip((-0.775 - z) / 0.03, 0, 1) * (y < -0.09)   # fingers, toes
                _mix(albedo, look["blush_color"], np.clip(rosy, 0, 1) * skin * look["flesh_variation"] * 0.5)
            if look["stubble"] > 0:
                # shaved hair shows through the skin as a grey-blue shadow, speckled where each hair sits
                # densest along the jaw, chin and lip; thinning out over a wide band toward the cheek line
                region = np.clip(beard.margin(x, y, z, look["beard_region"]) / STUBBLE_EDGE, 0, 1) ** 0.8 * skin
                cell = np.floor(tpl / STUBBLE_CELL)
                speck = (np.sin(cell[..., 0] * 12.9898 + cell[..., 1] * 78.233 + cell[..., 2] * 37.719) * 43758.5453) % 1.0
                # a grey-blue veil over the skin, not a darker skin tone: darkened skin colour reads as dirt or a bruise
                lightness = (albedo @ np.asarray(LUMA, np.float32))[..., None]
                shadow = lightness * np.asarray(STUBBLE_COOL, np.float32) * (1 - STUBBLE_HAIR_SHARE) + \
                    np.asarray(look["beard_color"], np.float32) * STUBBLE_HAIR_SHARE
                _mix(albedo, shadow, region * look["stubble"] * (0.55 + 0.45 * speck))
            if look["muscle_definition"] > 0 or look["body_relief"] > 0:
                # relief is form, not paint: it goes into the surface normals so light and shadow model it
                muscle = _body_height(x, y, z, look["muscle_definition"], 0.0) * skin
                bone = _body_height(x, y, z, 0.0, look["body_relief"]) * skin
                g["bump"] = g.get("bump", 0.0) + muscle + bone
                g["relief"] = g.get("relief", 0.0) + muscle          # muscle grooves, for media that ink them
            brow = _brow_mask(x, z, look["brow_thickness"], look["brow_arch"]) * front
            # individual hairs: fine streaks that lean outward along the brow
            hairs = 0.5 + 0.5 * np.sin((x * 0.55 + z) * 5200.0 + np.sin(x * 900.0) * 1.5)
            _mix(albedo, look["brow_color"], brow * look["brow_strength"] * (0.72 + 0.28 * hairs))
            if look["lash_strength"] > 0 and eye.any():
                _paint_eye_surround(g, albedo, look, skin, eye, x, z)
        if eye.any():
            _paint_iris(g, albedo, glow_rgb, glow_alpha, look, eye)

    return paint
