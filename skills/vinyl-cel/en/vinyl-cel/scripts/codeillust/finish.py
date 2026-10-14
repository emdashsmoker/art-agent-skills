"""Finishing passes: the 'post' stage that gives each style its surface.

Input is the fully drawn canvas plus its part masks; output replaces canvas.rgb.
"""
import cv2
import numpy as np

from . import brushwork, shading
from .config import StyleName, rgb

# anime
RIM_SHIFT_UNITS = (5.0, 6.0)
RIM_STRENGTH = 0.55
BLOOM_THRESHOLD = 0.78
BLOOM_RADIUS_UNITS = 16.0
BLOOM_STRENGTH = 0.30
ANIME_SATURATION = 1.10
ANIME_GRAIN = 0.010
# illustration
PAPER_GRAIN = 0.055
PAPER_FIBER_UNITS = 2.2
EDGE_WOBBLE_UNITS = 1.4
ILLUST_SATURATION = 0.94
# painterly
UNDERPAINT = rgb("#5A4632")
PAINT_SATURATION = 1.06
PAINT_DETAIL = {"eyes": 1.0, "mouth": 1.0, "hand": 0.45}   # importance per part; figure default below
PAINT_FIGURE_DETAIL = 0.3
FACE_DETAIL = 0.5                     # importance of a large face
SMALL_FACE_UNITS = (100.0, 160.0)     # visible face span: at the first or less the whole face takes the finest brushes,
                                      # from the second up FACE_DETAIL holds (brush sizes are fixed in canvas units)
FACE_JOIN_UNITS = 6.0                 # hair strands narrower than twice this do not split one face into two
CHIAROSCURO_SHADE = rgb("#4A3A4E")    # multiply tone on the side away from the light
CHIAROSCURO_STRENGTH = 0.62
PAINT_GAMMA = 1.22                    # pulls chalky cel colours down into oil-paint mid-tones
PAINT_WARMTH = rgb("#FFF0DC")         # varnish tint
AIRBRUSH_SHADE = rgb("#C9C2E6")       # soft cool gradient layered over cel tones
AIRBRUSH_STRENGTH = 0.30


def figure_mask(canvas):
    total = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for mask in canvas.parts.values():
        total = np.maximum(total, mask)
    return total


def apply(canvas, style, light):
    if style.name is StyleName.ANIME:
        _finish_anime(canvas, light)
    elif style.name is StyleName.ILLUST:
        _finish_illust(canvas)
    elif style.name is StyleName.PAINTERLY:
        _finish_painterly(canvas, light)
    else:
        raise ValueError(f"no finishing pass for style: {style.name}")


def _saturate(image, amount):
    gray = image.mean(axis=2, keepdims=True)
    return np.clip(gray + (image - gray) * amount, 0.0, 1.0)


def _finish_anime(canvas, light):
    figure = figure_mask(canvas)
    # Rim light: the sliver of the figure that the shifted copy no longer covers.
    direction = np.asarray(light[:2]) / (np.linalg.norm(light[:2]) + 1e-9)
    shift = np.float32([[1, 0, -direction[0] * canvas.px(RIM_SHIFT_UNITS[0])],
                        [0, 1, -direction[1] * canvas.px(RIM_SHIFT_UNITS[1])]])
    moved = cv2.warpAffine(figure, shift, (canvas.width, canvas.height))
    rim = shading.blur(figure * (1 - moved), canvas.px(1.2))[..., None] * RIM_STRENGTH
    image = _shade_away_from_light(canvas, figure, light, AIRBRUSH_SHADE, AIRBRUSH_STRENGTH)
    image = image * (1 - rim) + rim

    bright = np.clip((image - BLOOM_THRESHOLD) / (1 - BLOOM_THRESHOLD), 0.0, 1.0)
    bloom = shading.blur(bright, canvas.px(BLOOM_RADIUS_UNITS)) * BLOOM_STRENGTH
    image = 1 - (1 - image) * (1 - bloom)
    image = _saturate(image, ANIME_SATURATION)
    image += canvas.rng.normal(0.0, ANIME_GRAIN, image.shape[:2])[..., None].astype(np.float32)
    canvas.rgb = np.clip(image, 0.0, 1.0)


def _finish_illust(canvas):
    # Wobble edges slightly so shapes look cut or brushed by hand, not plotted.
    offset_x = (canvas.noise(28.0, octaves=2) - 0.5) * 2 * canvas.px(EDGE_WOBBLE_UNITS)
    offset_y = (canvas.noise(28.0, octaves=2) - 0.5) * 2 * canvas.px(EDGE_WOBBLE_UNITS)
    ys, xs = np.mgrid[0:canvas.height, 0:canvas.width].astype(np.float32)
    image = cv2.remap(canvas.rgb, xs + offset_x, ys + offset_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    image = _saturate(image, ILLUST_SATURATION)
    fiber = canvas.rng.normal(0.0, 1.0, image.shape[:2]).astype(np.float32)
    fiber = shading.blur(fiber, canvas.px(PAPER_FIBER_UNITS) * 0.35)
    fiber /= (np.abs(fiber).max() + 1e-9)
    speckle = canvas.rng.normal(0.0, 0.5, image.shape[:2]).astype(np.float32)
    grain = (fiber * 0.7 + speckle * 0.3) * PAPER_GRAIN
    canvas.rgb = np.clip(image * (1.0 + grain[..., None]), 0.0, 1.0)


def _finish_painterly(canvas, light):
    figure = figure_mask(canvas)
    canvas.rgb = _shade_away_from_light(canvas, figure, light, CHIAROSCURO_SHADE, CHIAROSCURO_STRENGTH)
    canvas.rgb = (np.clip(canvas.rgb, 0.0, 1.0) ** PAINT_GAMMA * PAINT_WARMTH).astype(np.float32)
    detail = figure * PAINT_FIGURE_DETAIL
    for name, importance in PAINT_DETAIL.items():
        detail = np.maximum(detail, shading.blur(canvas.part(name), canvas.px(4.0)) * importance)
    detail = np.maximum(detail, shading.blur(_face_detail(canvas), canvas.px(4.0)))
    if canvas.importance is not None:
        detail = np.maximum(detail, canvas.importance)
    painted = brushwork.paint(canvas.rgb, detail, canvas.px_per_unit, canvas.rng, UNDERPAINT)
    canvas.rgb = _saturate(painted, PAINT_SATURATION)


def _face_detail(canvas):
    """Face mask weighted per face: small faces get finer brushes so eyes and mouth survive."""
    face = canvas.part("face")
    solid = (face > 0.5).astype(np.uint8)
    join = max(1, int(round(canvas.px(FACE_JOIN_UNITS))))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * join + 1, 2 * join + 1))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(solid, cv2.MORPH_CLOSE, kernel))
    small, large = SMALL_FACE_UNITS
    importance = np.zeros(count, dtype=np.float32)
    for index in range(1, count):
        span = max(stats[index, cv2.CC_STAT_WIDTH], stats[index, cv2.CC_STAT_HEIGHT]) / canvas.px_per_unit
        share = float(np.clip((large - span) / (large - small), 0.0, 1.0))
        importance[index] = FACE_DETAIL + share * (1.0 - FACE_DETAIL)
    return face * importance[labels]


def _shade_away_from_light(canvas, figure, light, shade_color, strength):
    """Large soft gradient across the figure: the side away from the light sinks
    into a coloured shadow. Adds the big form that per-part shading cannot."""
    if not canvas.shade_subject_as_one:
        return canvas.rgb
    direction = np.asarray(light[:2]) / (np.linalg.norm(light[:2]) + 1e-9)
    xs, ys = canvas.grid()
    along = -(xs * direction[0] + ys * direction[1])
    inside = along[figure > 0.5]
    if inside.size == 0:
        return canvas.rgb
    low, high = np.percentile(inside, [8, 97])
    amount = shading.smoothstep(low, high, along) ** 1.4 * strength * figure
    tint = 1.0 - amount[..., None] * (1.0 - np.asarray(shade_color, dtype=np.float32))
    return (canvas.rgb * tint).astype(np.float32)
