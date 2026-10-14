"""Building blocks shared by the media: outlines, tone bands, colour helpers, surface textures."""
import numpy as np
import cv2

from .line import edge_map, draw_lines, GROUND_PARTS
from .noise import fractal_noise, white_noise
from .shade import material_mask, downsample

LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def luminance(image):
    return image @ LUMA


def saturate(image, amount):
    """amount 1 = unchanged, 0 = grey, > 1 = more chroma."""
    grey = luminance(image)[..., None]
    return np.clip(grey + (image - grey) * amount, 0, 1)


def mix(a, b, t):
    return a * (1 - t) + b * t


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


RELIEF_STROKE_BLUR = 0.8        # px; smooths the relief before finding its valleys
RELIEF_STROKE_THRESHOLD = 6e-5  # height curvature (m per output px squared) that counts as a groove
RELIEF_STROKE_LIGHT_FADE = 0.75
RELIEF_STROKE_GAIN = 1.4
HAIR_SMOOTH_FACTOR = 2.5        # hair shading is calmed this much more than other surfaces
FACE_SMOOTH_FACTOR = 2.6      # faces get broader, calmer shadow shapes than bodies and cloth


def hair_mask(F):
    """Supersampled mask of head hair and beards."""
    mask = np.zeros(F.g["mask"].shape, bool)
    for name in F.g["materials"]:
        if name.endswith((".hair", ".beard")):
            mask |= material_mask(F.g, name)
    return mask


def face_region(F):
    """Face area (0..1) at supersampled resolution, from the focus map."""
    h, w = F.lit.shape
    return cv2.resize((F.focus >= 0.99).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def soft_lit(F, smooth_px, face_smooth=FACE_SMOOTH_FACTOR, face_lift=0.0):
    """Lit fraction with polygon-scale noise smoothed away (supersampled resolution).

    Faces are smoothed more: small shadow islands around the nose and mouth read as blemishes in flat styles.
    face_lift 0..1 brightens the face's half-tones so only the side turned well away from the light stays in shadow."""
    s = F.g["supersample"]
    sigma = smooth_px * s
    lit = cv2.GaussianBlur(F.lit, (0, 0), sigma) if sigma > 0 else F.lit
    if sigma > 0:
        # hair is built from many small locks; flat styles shade it as a few large masses, not lock by lock
        hair = hair_mask(F)
        if hair.any():
            calm = cv2.GaussianBlur(F.lit, (0, 0), sigma * HAIR_SMOOTH_FACTOR)
            lit = np.where(hair, calm, lit)
    if face_smooth and sigma > 0:
        face = face_region(F)
        if face.any():
            face = cv2.GaussianBlur(face, (0, 0), sigma)
            calm = cv2.GaussianBlur(F.lit, (0, 0), sigma * face_smooth)
            if face_lift:
                calm = np.clip(calm, 0, 1) ** (1 - face_lift)
            lit = lit * (1 - face) + calm * face
    return lit


def soft_tone(F, smooth_px):
    sigma = smooth_px * F.g["supersample"]
    return cv2.GaussianBlur(F.tone, (0, 0), sigma) if sigma > 0 else F.tone


def step(value, threshold, softness=0.012):
    return np.clip((value - threshold) / softness + 0.5, 0, 1)


def skin_mask(F):
    """Supersampled mask of all skin pixels (skin takes warmer shadows than cloth)."""
    mask = np.zeros(F.g["mask"].shape, bool)
    for name in F.g["materials"]:
        if name.endswith(".skin"):
            mask |= material_mask(F.g, name)
    return mask


def fresnel_rim(F):
    """Grazing-angle factor 0..1 on objects (supersampled). Ground planes are excluded: seen edge-on,
    a floor or a sea would otherwise light up as one big rim."""
    g = F.g
    facing = np.clip(-np.sum(g["normal"] * g["view"], -1), 0, 1)
    ground = np.zeros(g["mask"].shape, bool)
    for index, name in enumerate(g["parts"]):
        if name in GROUND_PARTS:
            ground |= g["part"] == index
    return (1 - facing) * g["mask"] * ~ground


def outline(F, width=1.6, crease_deg=38.0, depth_step=0.035, thin_in_light=0.6, lit=None, wobble=0.0, taper=0.0,
            quiet_face=False):
    """Ink coverage 0..1 at output resolution.

    thin_in_light: 0 = even line, 1 = lines almost vanish on the lit side.
    wobble: hand tremor in pixels.  taper: 0..1 random thick-thin variation along the line.
    quiet_face: ink only the face's outline and features (the anime way); no lines along the nose or cheeks.
    """
    quiet = face_region(F) > 0.5 if quiet_face else None
    edges = edge_map(F.g, depth_step=depth_step, crease_deg=crease_deg, quiet=quiet)
    weight = None
    if thin_in_light and lit is not None:
        weight = 1.0 - thin_in_light * lit
    if taper:
        h, w = edges.shape
        pressure = fractal_noise((h, w), 60 * F.g["supersample"], F.seed, 601, octaves=2)
        weight = (1.0 if weight is None else weight) * (1 - taper + taper * 2 * pressure)
    ink = draw_lines(F.g, edges, width, weight)
    if wobble:
        ink = warp(ink, F.seed, wobble, 24, salt=611)
    return np.clip(ink, 0, 1)


def relief_strokes(F):
    """Thin line coverage (output resolution) along valleys of the body relief height field."""
    height = F.g["relief"]
    if np.ndim(height) == 0:
        return np.zeros((F.height, F.width), np.float32)
    s = F.g["supersample"]
    smooth = cv2.GaussianBlur(np.asarray(height, np.float32), (0, 0), RELIEF_STROKE_BLUR * s)
    valley = cv2.Laplacian(smooth, cv2.CV_32F)
    threshold = RELIEF_STROKE_THRESHOLD / (s * s)
    strokes = np.clip((valley - threshold) / threshold, 0, 1) * (smooth < 0)
    # an inker marks anatomy firmly on the shadow side and barely at all where the light falls
    strokes = strokes * (1 - RELIEF_STROKE_LIGHT_FADE * np.clip(cv2.GaussianBlur(F.lit, (0, 0), 2.0 * s), 0, 1))
    return np.clip(downsample(strokes, F.g) * RELIEF_STROKE_GAIN, 0, 1)


def warp(image, seed, amount_px, cell, salt=21):
    """Displace an image by smooth noise (hand wobble, wet paper, print misregistration)."""
    h, w = image.shape[:2]
    dx = (fractal_noise((h, w), cell, seed, salt, octaves=2) - 0.5) * 2 * amount_px
    dy = (fractal_noise((h, w), cell, seed, salt + 1, octaves=2) - 0.5) * 2 * amount_px
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return cv2.remap(image, xs + dx, ys + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def paper_height(shape, seed, coarse=9.0):
    """Paper tooth as a height field in [0, 1]."""
    rough = fractal_noise(shape, coarse, seed, 11, octaves=3)
    fine = cv2.GaussianBlur(white_noise(shape, seed, 12), (0, 0), 0.8)
    fine = (fine - fine.min()) / (np.ptp(fine) + 1e-9)
    return 0.55 * rough + 0.45 * fine


def canvas_weave(shape, pitch=3.0):
    """Woven canvas pattern in [-1, 1]."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    k = 2 * np.pi / pitch
    return np.sin(xx * k) * np.sin(yy * k)


def halftone(shape, value, pitch=6.0, angle_deg=45.0):
    """Dot screen: returns ink coverage 0..1 for a darkness map `value` (1 = solid)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.radians(angle_deg)
    u = (xx * np.cos(a) + yy * np.sin(a)) / pitch
    v = (-xx * np.sin(a) + yy * np.cos(a)) / pitch
    cell = np.hypot(u - np.round(u), v - np.round(v)) / 0.7071
    return np.clip((np.sqrt(np.clip(value, 0, 1)) - cell) * pitch * 0.6 + 0.5, 0, 1)


def quantize_to_palette(image, palette, softness=0.0):
    """Snap every pixel to its nearest palette colour (limited-palette looks: woodblock, poster)."""
    palette = np.asarray(palette, np.float32)
    flat = image.reshape(-1, 3)
    distance = ((flat[:, None, :] - palette[None]) ** 2).sum(-1)
    snapped = palette[distance.argmin(1)].reshape(image.shape)
    return mix(snapped, image, softness)


def vignette(shape, strength=0.3, radius=0.75):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    return 1 - strength * np.clip((d - radius) / (1.42 - radius), 0, 1) ** 2
