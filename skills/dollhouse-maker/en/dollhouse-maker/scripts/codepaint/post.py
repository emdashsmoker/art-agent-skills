"""Finishing effects. Every function takes and returns float RGB (h, w, 3) in 0..1."""
import cv2
import numpy as np

from .color import fbm, luminance, rgb, smoothstep


def bloom(img, threshold=0.75, radius=18.0, strength=0.5, **_):
    """Glow around the brightest areas (lamps, highlights, sky)."""
    bright = img * smoothstep(threshold, 1.0, luminance(img))[..., None]
    glow = cv2.GaussianBlur(bright, (0, 0), radius) + 0.5 * cv2.GaussianBlur(bright, (0, 0), radius * 3)
    return np.clip(1 - (1 - img) * (1 - np.clip(glow * strength, 0, 1)), 0, 1)


def diffusion(img, radius=10.0, strength=0.25, **_):
    """Soft screen of a blurred copy: the dreamy finish common in anime stills."""
    soft = cv2.GaussianBlur(img, (0, 0), radius)
    return np.clip(img * (1 - strength) + (1 - (1 - img) * (1 - soft)) * strength, 0, 1)


def grade(img, contrast=1.0, saturation=1.0, shadows=(1, 1, 1), highlights=(1, 1, 1),
          gamma=1.0, **_):
    """Contrast around mid-gray, saturation, and split toning."""
    out = np.clip((img - 0.5) * contrast + 0.5, 0, 1) ** gamma
    lum = luminance(out)[..., None]
    out = lum + (out - lum) * saturation
    tone = np.asarray(shadows, np.float32) * (1 - lum) + np.asarray(highlights, np.float32) * lum
    return np.clip(out * tone, 0, 1)


def grain(img, amount=0.03, seed=0, **_):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, amount, img.shape[:2]).astype(np.float32)
    return np.clip(img + noise[..., None], 0, 1)


def paper(img, amount=0.06, scale=3.0, seed=0, **_):
    """Paper tooth: fine fibrous noise multiplied in."""
    h, w = img.shape[:2]
    tooth = fbm(h, w, scale=scale, octaves=3, seed=seed) - 0.5
    blotch = fbm(h, w, scale=180, octaves=2, seed=seed + 1) - 0.5
    return np.clip(img * (1 + amount * (2 * tooth + 0.6 * blotch))[..., None], 0, 1)


def canvas_weave(img, amount=0.05, period=3.2, seed=0, **_):
    """Linen weave visible through thin paint."""
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    jitter = (fbm(h, w, scale=40, octaves=2, seed=seed) - 0.5) * 2.0
    weave = np.sin(2 * np.pi * (xs + jitter) / period) * np.sin(2 * np.pi * (ys + jitter) / period)
    return np.clip(img * (1 + amount * weave)[..., None], 0, 1)


def vignette(img, strength=0.35, color=(0, 0, 0), **_):
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((xs - w / 2) / (w / 2), (ys - h / 2) / (h / 2)) / np.sqrt(2)
    a = (smoothstep(0.45, 1.0, d) * strength)[..., None]
    return img * (1 - a) + rgb(color) * a


def edge_darken(img, amount=0.25, radius=2.0, **_):
    """Pigment pooling at shape edges, as in watercolor and gouache washes."""
    gray = luminance(img)
    blur = cv2.GaussianBlur(gray, (0, 0), radius)
    edges = np.abs(cv2.Laplacian(blur, cv2.CV_32F, ksize=3))
    edges = np.clip(edges * 12, 0, 1)
    return np.clip(img * (1 - amount * edges)[..., None], 0, 1)


def _grid(h, w):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return xs, ys


def watercolor(img, wobble=2.5, flatten=5.0, bleed=0.45, pigment=0.35, hue_drift=0.10, granulation=0.06,
               wet_edge=2.2, lighten=0.16, border=0.035, seed=0, **_):
    """Transparent washes on paper (after Bousseau et al. 2006, "Interactive watercolor rendering").

    The picture is treated as pigment density (1 - color): small detail is flattened into washes, wash
    boundaries wander, density varies in large turbulent patches and fine grains, pigment pools along the
    rim of each wash, and the washes thin out toward a ragged white paper border.
    """
    h, w = img.shape[:2]
    out = cv2.bilateralFilter(img.astype(np.float32), 9, 0.10, flatten)          # washes, not detail
    xs, ys = _grid(h, w)
    dx = (fbm(h, w, scale=70, octaves=2, seed=seed + 11) - 0.5) * 2 * wobble
    dy = (fbm(h, w, scale=70, octaves=2, seed=seed + 12) - 0.5) * 2 * wobble
    out = cv2.remap(out, xs + dx, ys + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    wet = smoothstep(0.55, 0.85, fbm(h, w, scale=220, octaves=2, seed=seed + 13))[..., None] * bleed
    out = out * (1 - wet) + cv2.GaussianBlur(out, (0, 0), 5.0) * wet           # wet-in-wet: soft where paper was wet
    dens = 1 - out
    turb = fbm(h, w, scale=110, octaves=4, seed=seed + 14) - 0.5                # uneven wash: pigment settles in patches
    drift = np.stack([fbm(h, w, scale=260, octaves=2, seed=seed + 20 + c) - 0.5 for c in range(3)], -1)
    grains = fbm(h, w, scale=5, octaves=2, seed=seed + 15) - 0.5                # pigment caught in the paper tooth
    dens = dens * (1 + 2 * pigment * turb)[..., None] * (1 + 2 * hue_drift * drift)
    dens = dens * (1 + 2 * granulation * grains * smoothstep(0.1, 0.6, dens.mean(-1)))[..., None]
    rim = np.clip(dens - cv2.GaussianBlur(dens, (0, 0), 4.0), 0, None)          # denser side of each wash edge
    dens = (dens + wet_edge * rim) * (1 - lighten)
    if border > 0:                                                             # ragged edge where the wash stops
        reach = np.minimum(np.minimum(xs, w - 1 - xs), np.minimum(ys, h - 1 - ys)) / max(h, w)
        ragged = border * (0.6 + 0.8 * fbm(h, w, scale=60, octaves=3, seed=seed + 16))
        fade = np.clip((reach - ragged * 0.6) / (ragged * 0.4), 0, 1)           # per-pixel edges: no smoothstep
        dens = dens * (fade * fade * (3 - 2 * fade))[..., None]
    return np.clip(1 - dens, 0, 1)


PENCIL_ANGLES = (-50.0, 40.0, -10.0)       # hatch directions, degrees: diagonal, cross, near horizontal
PENCIL_LEVELS = (0.18, 0.42, 0.66)         # darkness where each hatch layer starts


def _hatch_layer(h, w, angle_deg, spacing, length, rng):
    """Short parallel pencil strokes over the whole picture, on a jittered grid along one direction."""
    a = np.radians(angle_deg)
    e, n = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
    reach = np.hypot(h, w) / 2 + length
    offsets = np.arange(-reach, reach, spacing)
    steps = np.arange(-reach, reach, length * 0.8)
    o, t = np.meshgrid(offsets, steps)
    o = o + rng.uniform(-0.3, 0.3, o.shape) * spacing
    t = t + rng.uniform(-0.3, 0.3, t.shape) * length
    centers = np.array([w / 2, h / 2]) + o[..., None] * n + t[..., None] * e
    keep = (centers[..., 0] > -length) & (centers[..., 0] < w + length) & (centers[..., 1] > -length) & (centers[..., 1] < h + length)
    centers = centers[keep]
    half = length * rng.uniform(0.35, 0.55, len(centers))[:, None]
    turn = np.radians(rng.uniform(-6, 6, len(centers)))
    d = np.stack([np.cos(a + turn), np.sin(a + turn)], 1)
    seg = np.stack([centers - d * half, centers + d * half], 1)
    layer = np.zeros((h, w), np.float32)
    pressure = rng.integers(0, 3, len(seg))                 # three pencil pressures
    for k, value in enumerate((0.55, 0.8, 1.0)):
        lines = [(s * 4).astype(np.int32) for s in seg[pressure == k]]
        cv2.polylines(layer, lines, False, value, 1, cv2.LINE_AA, shift=2)
    return layer


def pencil(img, spacing=4.5, length=28.0, strength=0.8, smudge=0.35, contour=0.35,
           paper_color=(0.965, 0.955, 0.93), graphite=(0.17, 0.17, 0.20), seed=0, **_):
    """Graphite drawing: the picture's darkness becomes a light smudge plus up to three layers of hatching
    (each layer starts at a darker value), drawn ink stays as pencil line, and edges of unlined areas get a
    soft contour."""
    h, w = img.shape[:2]
    rng = np.random.default_rng(seed)
    lum = luminance(img)
    dark = smoothstep(0.04, 0.92, 1 - lum)
    hatch = np.zeros((h, w), np.float32)
    for angle, level in zip(PENCIL_ANGLES, PENCIL_LEVELS):
        cover = smoothstep(level, level + 0.22, dark)
        hatch = 1 - (1 - hatch) * (1 - _hatch_layer(h, w, angle, spacing, length, rng) * cover)
    soft = cv2.GaussianBlur(lum, (0, 0), 1.2)
    grad = np.hypot(cv2.Sobel(soft, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(soft, cv2.CV_32F, 0, 1, ksize=3))
    # drawn lines are thin and only partly dark after antialiasing: find them by contrast with their surroundings
    line = smoothstep(0.03, 0.16, cv2.GaussianBlur(lum, (0, 0), 2.5) - lum)
    ink = np.maximum(line, smoothstep(0.30, 0.10, lum))
    near_ink = cv2.dilate((line > 0.2).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32)
    edges = np.clip(grad * 4.0 - 0.25, 0, 1) * contour * (1 - near_ink)   # a drawn line is not traced twice
    total = 1 - (1 - dark * smudge) * (1 - hatch * strength) * (1 - edges) * (1 - ink * 0.85)
    total = total[..., None]
    return np.clip(np.asarray(paper_color, np.float32) * (1 - total) + np.asarray(graphite, np.float32) * total, 0, 1)


def posterize(img, levels=6, chroma_step=14.0, keep_dark=0.22, **_):
    """Screen-print color: lightness is cut into a few flat steps and the color axes (Lab a, b) into coarse
    steps, so every region becomes one flat ink while different hues stay apart (skin next to a white shirt
    keeps its warmth). A 3x3 median per axis removes stray pixels (a 2 px line survives it). Thin lines darker
    than keep_dark (the eyes of small figures are 1-2 px) are printed in one dark ink; large dark areas (black
    clothes, hair) keep their own quantized color."""
    lab = cv2.cvtColor(img.astype(np.float32), cv2.COLOR_RGB2LAB)
    step_l = 100.0 / levels
    quant = [np.round(lab[..., 0] / step_l), np.round(lab[..., 1] / chroma_step), np.round(lab[..., 2] / chroma_step)]
    offset = [0, 128 // chroma_step, 128 // chroma_step]                 # a, b are signed: shift into uint8
    clean = [cv2.medianBlur((q + o).astype(np.uint8), 3).astype(np.float32) - o for q, o in zip(quant, offset)]
    flat = np.stack([clean[0] * step_l, clean[1] * chroma_step, clean[2] * chroma_step], -1).astype(np.float32)
    lum = luminance(img)
    thin = (cv2.GaussianBlur(lum, (0, 0), 2.5) - lum) > 0.05            # lines only: a large dark area keeps its own ink
    ink = (lum < keep_dark) & thin
    if ink.any():
        flat[ink] = lab[ink].mean(0)                                   # one flat ink for every drawn line
    return np.clip(cv2.cvtColor(flat, cv2.COLOR_LAB2RGB), 0, 1)


def halftone(img, cell=7.0, angle=15.0, strength=0.30, start=0.35, **_):
    """Printed dot screen in the darker areas: dot size grows with darkness past `start`."""
    h, w = img.shape[:2]
    xs, ys = _grid(h, w)
    a = np.radians(angle)
    u = (xs * np.cos(a) + ys * np.sin(a)) / cell
    v = (-xs * np.sin(a) + ys * np.cos(a)) / cell
    r = np.hypot(u - np.floor(u) - 0.5, v - np.floor(v) - 0.5)
    radius = 0.55 * np.sqrt(np.clip((1 - luminance(img) - start) / (1 - start), 0, 1))
    dot = smoothstep(0.06, -0.06, r - radius) * (radius > 0)
    return np.clip(img * (1 - strength * dot)[..., None], 0, 1)


def chromatic(img, shift=1.5, **_):
    """Lens color fringing: red pushed outward, blue pulled inward, growing toward the corners."""
    h, w = img.shape[:2]
    xs, ys = _grid(h, w)
    k = shift / (max(h, w) / 2)
    out = img.copy()
    for ch, sign in ((0, -1), (2, 1)):
        mx = (xs - w / 2) * (1 + sign * k) + w / 2
        my = (ys - h / 2) * (1 + sign * k) + h / 2
        out[..., ch] = cv2.remap(img[..., ch], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


EFFECTS = {f.__name__: f for f in (bloom, diffusion, grade, grain, paper, canvas_weave,
                                   vignette, edge_darken, watercolor, pencil, posterize, halftone, chromatic)}


def apply(img, steps, seed=0):
    """steps = [("bloom", {...}), ("grain", {...}), ...] applied in order."""
    for name, kwargs in steps:
        img = EFFECTS[name](img, seed=seed, **kwargs).astype(np.float32)
    return img
