"""Textures and finishing passes applied to whole images (HxWx3 float, 0..1)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

from .color import luminance, rgb
from .painting import to_image
from .shading import blur, radial_ramp, smoothstep

NOISE_BASE_CELLS = 4      # coarsest octave of fbm has this many cells across the short side
SHEET_LABEL_HEIGHT = 34
SHEET_GAP = 10


def fbm(shape, scale=1.0, octaves=4, seed=0, stretch=(1.0, 1.0)):
    """Smooth cloudy noise in 0..1 (summed octaves of upsampled random grids).

    scale: feature size multiplier (bigger = finer detail).
    stretch: (y, x) elongation of the features, e.g. (1, 6) gives horizontal streaks.
    """
    rng = np.random.default_rng(seed)
    height, width = shape
    total = np.zeros(shape, dtype=np.float32)
    weight_sum = 0.0
    for octave in range(octaves):
        cells = NOISE_BASE_CELLS * scale * (2 ** octave)
        grid_h = max(int(round(cells / stretch[0] * height / min(height, width))), 2)
        grid_w = max(int(round(cells / stretch[1] * width / min(height, width))), 2)
        grid = rng.random((grid_h + 3, grid_w + 3)).astype(np.float32)
        layer = ndi.zoom(grid, (height / grid_h, width / grid_w), order=3)[:height, :width]
        weight = 0.5 ** octave
        total += layer * weight
        weight_sum += weight
    total /= weight_sum
    low, high = float(total.min()), float(total.max())
    return (total - low) / max(high - low, 1e-6)


def grain(image, amount=0.03, seed=0):
    """Fine film grain; breaks up the too-clean look of computed gradients."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, amount, image.shape[:2]).astype(np.float32)
    return np.clip(image + blur(noise, 0.6)[..., None], 0.0, 1.0)


def paper(image, amount=0.06, seed=0):
    """Paper tooth: a multiply texture mixing fine grain with soft mottling."""
    shape = image.shape[:2]
    rng = np.random.default_rng(seed)
    tooth = blur(rng.random(shape).astype(np.float32), 0.8)
    tooth = (tooth - tooth.mean()) / max(float(tooth.std()), 1e-6)
    mottle = fbm(shape, scale=6, octaves=3, seed=seed + 1) - 0.5
    texture = 1.0 + amount * (0.35 * tooth + 1.2 * mottle)
    return np.clip(image * texture[..., None], 0.0, 1.0)


def bloom(image, threshold=0.75, radius=18.0, strength=0.35):
    """Light bleeding out of the brightest areas (screen blend of a blurred bright pass)."""
    bright = np.clip((luminance(image) - threshold) / max(1.0 - threshold, 1e-6), 0.0, 1.0)
    halo = blur(image * bright[..., None], radius) * strength
    return 1.0 - (1.0 - image) * (1.0 - np.clip(halo, 0.0, 1.0))


def glow(image, radius=10.0, strength=0.25):
    """Diffusion filter: the soft overall haze common in modern anime illustration."""
    soft = blur(image, radius)
    screened = 1.0 - (1.0 - image) * (1.0 - soft)
    return image + (screened - image) * strength


def vignette(image, strength=0.25, center=None, radius=None):
    height, width = image.shape[:2]
    center = center or (width / 2, height / 2)
    radius = radius or np.hypot(width, height) / 2
    falloff = radial_ramp((height, width), center, radius) ** 2
    return image * (1.0 - strength * falloff)[..., None]


def grade(image, contrast=1.0, saturation=1.0, shadows=None, highlights=None, gamma=1.0):
    """Colour grade: contrast around mid grey, saturation, split-toning of darks and lights.

    shadows / highlights: (colour, amount) pairs pulling darks / lights toward a hue,
    which ties separately coloured parts into one light.
    """
    result = np.clip(image, 0.0, 1.0) ** gamma
    result = (result - 0.5) * contrast + 0.5
    luma = luminance(result)[..., None]
    result = luma + (result - luma) * saturation
    if shadows is not None:
        color, amount = shadows
        result += (rgb(color) - result) * amount * (1.0 - np.clip(luma, 0, 1)) ** 2
    if highlights is not None:
        color, amount = highlights
        result += (rgb(color) - result) * amount * np.clip(luma, 0, 1) ** 2
    return np.clip(result, 0.0, 1.0)


# The skill's signature mood: a cold, washed-out concrete world where only the warm lights keep their colour.
DOOMER = dict(saturation=0.40, warm_saturation=0.95, contrast=0.94, shadows=("#1d3a40", 0.32),
              highlights=("#e4e0d0", 0.06), fade=0.05, grain=0.032, vignette=0.34)
# Lamps and lit windows are strongly orange and bright; skin is warm too, but less so, and keeps only part of its colour.
WARM_EDGES = (0.30, 0.45)    # red minus blue over which a pixel turns from cold to warm light
LIT_EDGES = (0.55, 0.80)     # luminance over which a warm pixel counts as a light


def warm_lights(image):
    """0..1 per pixel: how much a pixel is a warm light (lamp, lit window) in an otherwise cold picture."""
    warmth = smoothstep(*WARM_EDGES, image[..., 0] - image[..., 2])
    return warmth * smoothstep(*LIT_EDGES, luminance(image))


def doomer(image, seed=0, strength=1.0):
    """Doomer mood over a finished image: drained colour, teal shadows, lifted blacks, heavy grain, dark corners.

    Lamps and lit windows keep their colour, so a single warm light carries the picture.
    strength: 0 leaves the image as it is, 1 is the full mood.
    """
    mood = DOOMER
    source = np.clip(image, 0.0, 1.0)
    saturation = mood["saturation"] + (mood["warm_saturation"] - mood["saturation"]) * warm_lights(source)
    luma = luminance(source)[..., None]
    result = luma + (source - luma) * saturation[..., None]
    result = grade(result, contrast=mood["contrast"], shadows=mood["shadows"], highlights=mood["highlights"])
    result = mood["fade"] + result * (1.0 - mood["fade"])          # the blacks of old film never reach black
    result = vignette(result, mood["vignette"])
    result = grain(result, mood["grain"], seed)
    return source + (result - source) * strength


def stage_sheet(stages, path, columns=3, tile_width=420):
    """Tile named stage snapshots into one contact sheet so the whole process can be reviewed."""
    names = list(stages)
    first = stages[names[0]]
    tile_height = int(round(tile_width * first.shape[0] / first.shape[1]))
    rows = (len(names) + columns - 1) // columns
    sheet_width = columns * tile_width + (columns + 1) * SHEET_GAP
    sheet_height = rows * (tile_height + SHEET_LABEL_HEIGHT) + (rows + 1) * SHEET_GAP
    sheet = Image.new("RGB", (sheet_width, sheet_height), (245, 243, 238))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    for index, name in enumerate(names):
        column, row = index % columns, index // columns
        left = SHEET_GAP + column * (tile_width + SHEET_GAP)
        top = SHEET_GAP + row * (tile_height + SHEET_LABEL_HEIGHT + SHEET_GAP)
        tile = to_image(stages[name]).resize((tile_width, tile_height), Image.LANCZOS)
        sheet.paste(tile, (left, top + SHEET_LABEL_HEIGHT))
        draw.text((left, top + 4), name, fill=(40, 40, 40), font=font)
    sheet.save(path)
