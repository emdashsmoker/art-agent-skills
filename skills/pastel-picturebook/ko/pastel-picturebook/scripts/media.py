"""Finishing passes for the derived media styles (stage 5): the clean render re-made in another medium.

  watercolor  washes that flatten into pools, darker wet edges, granulation, blooms, cold-press paper
  pencil      graphite on paper: smudged tone, hatching that thickens with the shadow, the outlines kept
  manga       black and white: ink lines and solid blacks, mid tones as a screentone of dots
  pixel       a low-resolution grid of few colours with dark outlines, scaled back up without smoothing
  doomer      cold blue-grey night: colour drained to a slate ramp, only warm lights (sodium lamps, windows, a cigarette)
              keep their orange, crushed blacks, halation round the lights, heavy film grain, a dark vignette

Each finisher takes (image, fig, options, seed) and returns an RGB image in 0..1, so any subject can use it.
"""
import cv2
import numpy as np

from raster import blur, noise, rgb, smoothstep

LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def luminance(image):
    return (image @ LUMA).astype(np.float32)


def wobble(image, amount, cell, seed):
    """Shift every pixel by a slow random field (pixels): edges painted by hand never run straight."""
    height, width = image.shape[:2]
    dx = (noise((height, width), cell, seed, 2) - 0.5) * 2.0 * amount
    dy = (noise((height, width), cell, seed + 1, 2) - 0.5) * 2.0 * amount
    xs, ys = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    return cv2.remap(image, xs + dx.astype(np.float32), ys + dy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def paper_texture(size, cell, seed):
    """Cold-press paper tooth, -0.5..0.5: small bumps lit from the upper left."""
    tooth = noise(size, cell, seed, 3)
    lit = np.roll(tooth, 1, axis=0) - np.roll(tooth, -1, axis=1)
    return (tooth - 0.5) * 0.5 + lit * 2.0


# ------------------------------------------------------------------ watercolor
def finish_watercolor(image, fig, options, seed):
    """Transparent washes: flattened colour pools, pigment gathered at their edges, granulation and blooms."""
    height, width = image.shape[:2]
    scale = width / 1200.0
    flat = image.astype(np.float32)
    for _ in range(options.get("flatten", 2)):
        flat = cv2.bilateralFilter(flat, 9, 0.12, 6.0 * scale)
    flat = wobble(flat, options["wobble"] * scale, 40.0 * scale, seed + 11)
    # Water carries pigment to where a wash stops drying: the borders between colours darken.
    # Small bright specks (snowflakes, sparkles, flowers) are reserved paper, not washes: no wet edge may ring them.
    # A strong top-hat finds them; the edges are damped over them and a few pixels round them.
    speck = max(3, int(round(options.get("speck", 41) * scale)) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (speck, speck))
    gray = luminance(flat)
    specks = smoothstep(gray - cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel), 0.05, 0.12)
    reach = max(3, int(round(6 * scale)) | 1)
    specks = blur(cv2.dilate(specks, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (reach, reach))), 2.0 * scale)
    gray = blur(gray, 1.5 * scale)
    edges = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    edges = np.clip(blur(edges, 1.2 * scale) * options["edge_gain"], 0.0, 1.0) * (1.0 - np.clip(specks * 1.5, 0.0, 1.0))
    pigment = 1.0 - flat
    pigment = pigment * options["density"] * (1.0 + options["wet_edge"] * edges)[..., None]
    # Blooms: slow blotches where the wash dried unevenly; granulation: pigment settling in the paper's pits.
    bloom = noise((height, width), 70.0 * scale, seed + 13, 2) - 0.5
    grains = noise((height, width), 1.6 * scale, seed + 17, 1) - 0.5
    pigment = pigment * (1.0 + options["bloom"] * bloom + options["granulation"] * grains)[..., None]
    paper = rgb(options.get("paper_color", "#FBF8F1"))
    result = paper * (1.0 - np.clip(pigment, 0.0, 1.0))
    tooth = paper_texture((height, width), 2.2 * scale, seed + 19)
    return result * (1.0 + options["paper"] * tooth)[..., None]


# ------------------------------------------------------------------ pencil
def hatch_layer(size, angle_deg, spacing, width, seed):
    """Parallel hand-drawn strokes (0..1) at an angle: lines every `spacing` px that waver a little."""
    height, wide = size
    ys, xs = np.mgrid[0:height, 0:wide].astype(np.float32)
    turn = np.deg2rad(angle_deg)
    across = xs * np.cos(turn) + ys * np.sin(turn)
    waver = (noise(size, spacing * 8.0, seed, 2) - 0.5) * spacing * 0.8
    phase = np.mod((across + waver) / spacing, 1.0)
    line = np.exp(-((phase - 0.5) / (width / spacing)) ** 2)
    # Strokes break and fade along their length like a pencil lifted now and then.
    pressure = 0.6 + 0.4 * smoothstep(noise(size, spacing * 6.0, seed + 1, 2), 0.3, 0.7)
    return (line * pressure).astype(np.float32)


def finish_pencil(image, fig, options, seed):
    """Graphite: a smudged tone, hatching layers switched on by darkness, dark outlines kept, paper grain."""
    height, width = image.shape[:2]
    scale = width / 1200.0
    lum = luminance(image)
    # Auto levels: the darkest part of any picture becomes the densest graphite, the lightest stays paper.
    low, high = np.percentile(lum, options.get("levels", [2, 98]))
    spread = np.clip((lum - low) / max(high - low, 1e-6), 0.0, 1.0)
    tone = np.clip((1.0 - spread) ** options.get("gamma", 1.0) * options["contrast"], 0.0, 1.0)
    shade = blur(tone, 2.0 * scale) * options["smudge"] * (0.5 + tone)
    spacing = options["spacing"] * scale
    # Each darker step lays another set of strokes over the last: cross-hatching builds up.
    clear = np.ones((height, width), np.float32)
    for k, (angle, start) in enumerate(zip(options["angles"], options["thresholds"])):
        layer = hatch_layer((height, width), angle, spacing, 0.9 * scale, seed + 23 + k)
        clear *= 1.0 - layer * smoothstep(tone, start, start + 0.18)
    hatch = 1.0 - clear
    # The render's own outlines are thin dark lines: a black-hat finds them and keeps them as pencil lines.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    lines = cv2.morphologyEx(lum, cv2.MORPH_BLACKHAT, kernel)
    lines = np.clip(lines * options["line_gain"], 0.0, 1.0)
    graphite = np.clip(shade + hatch * options["hatch"] + lines, 0.0, 1.0)
    tooth = paper_texture((height, width), 1.8 * scale, seed + 29)
    graphite = np.clip(graphite * (1.0 + options["paper"] * tooth * 2.0), 0.0, 1.0)
    paper, lead = rgb(options.get("paper_color", "#F6F3EC")), rgb(options.get("lead_color", "#33343B"))
    return paper * (1.0 - graphite[..., None]) + lead * graphite[..., None]


# ------------------------------------------------------------------ manga
def screentone(size, cell, angle_deg):
    """Distance (in cells) from each pixel to the nearest dot centre of a rotated dot grid."""
    height, width = size
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    turn = np.deg2rad(angle_deg)
    u = (xs * np.cos(turn) + ys * np.sin(turn)) / cell
    v = (-xs * np.sin(turn) + ys * np.cos(turn)) / cell
    return np.hypot(u - np.round(u), v - np.round(v))


def finish_manga(image, fig, options, seed):
    """Black ink on white: solid blacks below `black`, white above `white`, a dot screen in between."""
    height, width = image.shape[:2]
    scale = width / 1200.0
    lum = luminance(image)
    low, high = options["black"], options["white"]
    tone = np.clip((high - lum) / max(high - low, 1e-6), 0.0, 1.0)
    cell = options["cell"] * scale
    distance = screentone((height, width), cell, options.get("angle", 45.0))
    # A dot's radius grows with the tone so its covered share follows it (area ~ r^2).
    radius = np.sqrt(tone / np.pi) * 1.05
    soft = 0.7 / cell
    dots = np.clip((radius - distance) / soft + 0.5, 0.0, 1.0) * (tone > 0.04)
    ink = np.where(lum < low, 1.0, dots).astype(np.float32)
    ink = np.where(lum > high, 0.0, ink)
    # The render's outlines stay solid black lines.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    lines = np.clip(cv2.morphologyEx(lum, cv2.MORPH_BLACKHAT, kernel) * options["line_gain"], 0.0, 1.0)
    ink = np.maximum(ink, lines)
    paper, black = rgb(options.get("paper_color", "#FBFBF8")), rgb(options.get("ink_color", "#121214"))
    return paper * (1.0 - ink[..., None]) + black * ink[..., None]


# ------------------------------------------------------------------ pixel
def palette_kmeans(pixels, count, rounds=10):
    """`count` colours for a set of pixels (N, 3): k-means started from luminance quantiles (no randomness)."""
    order = np.argsort(pixels @ LUMA)
    centres = pixels[order[np.linspace(0, len(order) - 1, count).astype(int)]].copy()
    for _ in range(rounds):
        nearest = np.argmin(((pixels[:, None, :] - centres[None, :, :]) ** 2).sum(-1), axis=1)
        for k in range(count):
            members = pixels[nearest == k]
            if len(members):
                centres[k] = members.mean(axis=0)
    return centres


def finish_pixel(image, fig, options, seed):
    """Few big pixels in few colours: area-averaged down to a grid, quantised, outlined, scaled back up."""
    height, width = image.shape[:2]
    across = options["cells"]
    down = max(int(round(height * across / width)), 1)
    small = cv2.resize(image.astype(np.float32), (across, down), interpolation=cv2.INTER_AREA)
    pixels = small.reshape(-1, 3)
    centres = palette_kmeans(pixels, options["colors"])
    # Ordered (Bayer) dithering: smooth gradients become checker steps between palette colours, not bands.
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16.0 - 0.47
    threshold = np.tile(bayer, (down // 4 + 1, across // 4 + 1))[:down, :across]
    pixels = (small + threshold[..., None] * options.get("dither", 0.0)).reshape(-1, 3)
    nearest = np.argmin(((pixels[:, None, :] - centres[None, :, :]) ** 2).sum(-1), axis=1)
    small = centres[nearest].reshape(down, across, 3).astype(np.float32)
    # A darker pixel where the brightness steps sharply: the hand-placed outline of sprite art.
    lum = luminance(small)
    step = np.maximum(np.abs(lum - np.roll(lum, 1, axis=0)), np.abs(lum - np.roll(lum, 1, axis=1)))
    edge = (step > options["edge"]) & (lum <= np.maximum(np.roll(lum, 1, axis=0), np.roll(lum, 1, axis=1)))
    small = np.where(edge[..., None], small * options["outline"], small)
    return cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)


# ------------------------------------------------------------------ doomer
def ramp(values, stops):
    """Colour for each value 0..1 along a ramp of (position, '#hex') stops."""
    positions = np.array([stop[0] for stop in stops], np.float32)
    colors = np.array([rgb(stop[1]) for stop in stops], np.float32)
    return np.stack([np.interp(values, positions, colors[:, k]) for k in range(3)], axis=-1).astype(np.float32)


def finish_doomer(image, fig, options, seed):
    """Late night in a cold city: a slate-blue ramp, warm lights left burning, grain and a heavy vignette."""
    height, width = image.shape[:2]
    scale = width / 1200.0
    image = image.astype(np.float32)
    lum = luminance(image)
    # Colour drains away; what is left is pushed onto a cold ramp from blue-black to grey.
    drained = lum[..., None] + (image - lum[..., None]) * options["saturation"]
    # Contrast round the middle grey: dark shapes stand against a pale sky like a photograph printed hard.
    tones = np.clip(0.5 + (lum - 0.5) * options.get("contrast", 1.0), 0.0, 1.0)
    cold = ramp(tones ** options.get("gamma", 1.0), options["ramp"])
    graded = drained + (cold - drained) * options["tint"]
    # Warm, bright things (sodium lamps, lit windows, an ember) keep their colour, pushed toward sodium orange.
    warmth = smoothstep(image[..., 0] - image[..., 2], options["warm_low"], options["warm_high"])
    burning = warmth * smoothstep(lum, options["warm_from"], options["warm_from"] + 0.2)
    sodium = image + (rgb(options["sodium"]) - image) * 0.35
    graded = graded + (sodium - graded) * burning[..., None]
    # Crushed blacks: the darkest quarter sinks into one deep tone.
    low = options["black_point"]
    graded = np.clip((graded - low) / (1.0 - low), 0.0, 1.0)
    # Halation: lights bleed a warm halo into the dark around them.
    bright = smoothstep(luminance(graded), 0.62, 0.95) * (0.4 + 0.6 * burning)
    halo = np.clip(blur(bright, options["halation_size"] * scale) * 2.2, 0.0, 1.0)
    glow = rgb(options["sodium"])
    graded = graded + (1.0 - graded) * glow * (halo * options["halation"])[..., None]
    # Vignette: the corners fall into the night.
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    distance = np.hypot((xs - width / 2) / (width / 2), (ys - height / 2) / (height / 2)) / np.sqrt(2.0)
    graded = graded * (1.0 - options["vignette"] * smoothstep(distance, 0.35, 1.0))[..., None]
    # Film grain, coarser than a pixel and stronger in the shadows.
    rng = np.random.default_rng(seed + 41)
    grain = blur(rng.standard_normal((height, width)).astype(np.float32), 0.6 * scale)
    grain = grain / max(float(grain.std()), 1e-6) * options["grain"] * (1.3 - 0.6 * luminance(graded))
    return np.clip(graded + grain[..., None], 0.0, 1.0)


FINISHERS = {"watercolor": finish_watercolor, "pencil": finish_pencil, "manga": finish_manga, "pixel": finish_pixel,
             "doomer": finish_doomer}
