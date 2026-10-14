"""Finishing passes: turn the clean color + line layers into a final look.

Each `finish_*` takes a Canvas and returns an (H, W, 3) float image.
The small building blocks (bloom, grade, grain, ...) are public so a scene
can assemble its own finish.
"""
import cv2
import numpy as np

from . import config, raster
from .color import luminance, rgb


# --- building blocks ---------------------------------------------------------

def bloom(image, threshold=0.78, radius=18.0, strength=0.35):
    """Glow around bright areas, like light scattering in a lens."""
    bright = np.clip(image - threshold, 0.0, None) / max(1.0 - threshold, 1e-6)
    halo = cv2.GaussianBlur(bright, (0, 0), radius) + 0.5 * cv2.GaussianBlur(bright, (0, 0), radius * 3.0)
    return np.clip(1.0 - (1.0 - image) * (1.0 - np.clip(halo * strength, 0, 1)), 0.0, 1.0)


def grade(image, contrast=1.0, saturation=1.0, shadows=None, highlights=None, amount=0.12, gamma=1.0):
    """Color grading: contrast about mid-gray, saturation, split-toning.

    shadows/highlights: colors mixed into dark/bright areas (soft-light style)."""
    out = np.clip(image, 0.0, 1.0) ** gamma
    out = (out - 0.5) * contrast + 0.5
    gray = luminance(out)[..., None]
    out = gray + (out - gray) * saturation
    if shadows is not None:
        out = out + (rgb(shadows) - 0.5) * amount * 2.0 * (1.0 - gray) ** 2
    if highlights is not None:
        out = out + (rgb(highlights) - 0.5) * amount * 2.0 * gray ** 2
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def vignette(image, strength=0.25, color='#1a1420'):
    height, width = image.shape[:2]
    field = raster.radial_field((width, height), (width / 2, height / 2), width * 0.85, height * 0.85)
    dark = (1.0 - raster.smoothstep(field, 0.0, 0.55))[..., None] * strength
    return image * (1.0 - dark) + rgb(color) * dark


def grain(image, amount=0.03, seed=None, size=1.0):
    """Film/paper grain: monochrome noise, strongest in midtones."""
    height, width = image.shape[:2]
    rng = np.random.default_rng(config.DEFAULT_SEED if seed is None else seed)
    noise = rng.normal(0.0, 1.0, (int(height / size), int(width / size))).astype(np.float32)
    noise = cv2.resize(noise, (width, height), interpolation=cv2.INTER_LINEAR)
    gray = luminance(image)
    weight = (4.0 * gray * (1.0 - gray)) ** 0.5
    return np.clip(image + (noise * weight * amount)[..., None], 0.0, 1.0)


def chromatic_aberration(image, shift_px=1.2):
    """Tiny red/blue fringe toward the edges; a lens cue used in anime compositing."""
    height, width = image.shape[:2]
    out = image.copy()
    for channel, scale in ((0, 1.0 + shift_px / width), (2, 1.0 - shift_px / width)):
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), 0.0, scale)
        out[..., channel] = cv2.warpAffine(image[..., channel], matrix, (width, height),
                                           flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


def light_wash(image, field, color, mode='screen', opacity=0.3):
    """Blend a color through a scalar field over the whole picture (sun haze, dusk tint)."""
    top = rgb(color)
    if mode == 'screen':
        blended = 1.0 - (1.0 - image) * (1.0 - top)
    elif mode == 'multiply':
        blended = image * top
    elif mode == 'soft_light':
        blended = (1.0 - 2.0 * top) * image * image + 2.0 * top * image
    else:
        raise ValueError(f'unknown mode: {mode}')
    alpha = (field * opacity)[..., None]
    return np.clip(image + (blended - image) * alpha, 0.0, 1.0)


def paper_texture(size, seed=None, fiber=0.5):
    """Height map of rough paper in 0..1 (0.5 = flat): fine tooth plus soft mottling."""
    width, height = size
    rng = np.random.default_rng(config.DEFAULT_SEED if seed is None else seed)
    fine = cv2.GaussianBlur(rng.normal(0, 1, (height, width)).astype(np.float32), (0, 0), 0.9)
    coarse = cv2.GaussianBlur(rng.normal(0, 1, (height, width)).astype(np.float32), (0, 0), 3.5)
    strands = cv2.GaussianBlur(rng.normal(0, 1, (height, width)).astype(np.float32), (0, 0), sigmaX=6.0, sigmaY=0.7)
    tex = fine / fine.std() * 0.55 + coarse / coarse.std() * 0.35 + strands / strands.std() * 0.25 * fiber
    return np.clip(0.5 + tex * 0.16, 0.0, 1.0)


def _composite_lines(color_image, cv, opacity=1.0, line_alpha=None, line_color=None):
    alpha = (cv.line_alpha if line_alpha is None else line_alpha) * opacity
    safe = np.maximum(cv.line_alpha, 1e-4)[..., None]
    straight = cv.line_rgb / safe if line_color is None else np.broadcast_to(rgb(line_color), cv.line_rgb.shape)
    return color_image * (1.0 - alpha[..., None]) + straight * alpha[..., None]


def line_art(cv, paper='#ffffff'):
    """The line layer alone on blank paper: the inking stage, for review or process sheets."""
    blank = np.empty_like(cv.color)
    blank[:] = rgb(paper)
    return _composite_lines(blank, cv)


def contact_sheet(images, columns=None, gap=16, background='#ffffff'):
    """Tile same-sized images into one (for process sheets and side-by-side review)."""
    columns = columns or len(images)
    height, width = images[0].shape[:2]
    rows = int(np.ceil(len(images) / columns))
    sheet = np.empty((rows * height + (rows + 1) * gap, columns * width + (columns + 1) * gap, 3), np.float32)
    sheet[:] = rgb(background)
    for index, image in enumerate(images):
        row, column = divmod(index, columns)
        y, x = gap + row * (height + gap), gap + column * (width + gap)
        sheet[y:y + height, x:x + width] = image
    return sheet


# --- anime ---------------------------------------------------------------------

def finish_anime(cv, glow=0.22, diffusion=0.10, contrast=1.05, saturation=1.06, shadows='#5a62b0',
                 highlights='#ffe9c4', aberration=0.8, grain_amount=0.012, seed=None):
    """Crisp cel picture with the light compositing of modern anime:
    bloom on the brights, cool shadows / warm lights, a trace of lens fringe."""
    image = cv.flatten()
    # "Diffusion" filter: a blurred copy screened on softens skin and makes lights breathe.
    soft = cv2.GaussianBlur(image, (0, 0), 6.0)
    image = image + (1.0 - (1.0 - image) * (1.0 - soft) - image) * diffusion
    image = bloom(image, threshold=0.90, radius=14.0, strength=glow)
    image = grade(image, contrast=contrast, saturation=saturation, shadows=shadows, highlights=highlights,
                  amount=0.05)
    if aberration > 0:
        image = chromatic_aberration(image, aberration)
    return grain(image, grain_amount, seed)


# --- illustration ------------------------------------------------------------

def finish_illustration(cv, glow=0.24, line_soften=0.7, texture=0.035, contrast=1.04, saturation=1.04,
                        shadows='#46508f', highlights='#ffe2bd', seed=None):
    """Soft digital-painting look: softened colored lines, glazing, canvas texture."""
    color = cv.color
    alpha = cv2.GaussianBlur(cv.line_alpha, (0, 0), line_soften) if line_soften > 0 else cv.line_alpha
    image = _composite_lines(color, cv, 1.0, alpha)
    # Slight painterly merge of neighboring tones, edges kept.
    image = cv2.bilateralFilter(image.astype(np.float32), d=0, sigmaColor=0.06, sigmaSpace=4.0)
    image = bloom(image, threshold=0.86, radius=20.0, strength=glow)
    image = grade(image, contrast=contrast, saturation=saturation, shadows=shadows, highlights=highlights,
                  amount=0.10)
    tooth = paper_texture(cv.size, seed, fiber=0.2)
    image = np.clip(image + ((tooth - 0.5) * texture * 2.0)[..., None], 0.0, 1.0)
    return vignette(image, 0.14)


# --- watercolor ----------------------------------------------------------------

def finish_watercolor(cv, paper='#f6f0e3', wash=0.14, edge_darkening=1.3, bleed=3.5, turbulence=0.34,
                      granulation=0.24, wobble=2.5, line_color='#5b4a44', line_opacity=0.70,
                      border=0.06, seed=None):
    """Transparent watercolor on rough paper.

    Pigment model (after Bousseau et al. 2006): every effect changes a pigment
    density d around 1, and color responds as  C' = C - (C - C*C) * (d - 1),
    so dense pigment darkens and saturates instead of just graying.
    wash: how much the colors are thinned toward the paper.
    bleed: px of wet-in-wet softening.  border: unpainted paper margin (fraction).
    """
    seed = config.DEFAULT_SEED if seed is None else seed
    width, height = cv.size
    color = cv.color.copy()
    # Wet-in-wet: tones merge, then the brush wobbles along every boundary.
    color = cv2.bilateralFilter(color, d=0, sigmaColor=0.10, sigmaSpace=bleed)
    color = cv2.GaussianBlur(color, (0, 0), bleed * 0.35)
    wob_x = (raster.noise_field(cv.size, 46.0, 3, seed + 11) - 0.5) * 2.0 * wobble * 2.0
    wob_y = (raster.noise_field(cv.size, 46.0, 3, seed + 12) - 0.5) * 2.0 * wobble * 2.0
    grid_x, grid_y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    color = cv2.remap(color, grid_x + wob_x, grid_y + wob_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    color = color + (1.0 - color) * wash                     # thin the paint
    # Pigment collects at the edge of each wash as it dries.
    smooth = cv2.GaussianBlur(color, (0, 0), 1.6)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    edge = np.sqrt((gx ** 2 + gy ** 2).sum(axis=-1))
    edge = np.clip(cv2.GaussianBlur(edge, (0, 0), 1.2) * 4.0, 0.0, 1.0)
    flow = raster.noise_field(cv.size, 150.0, 4, seed + 13) - 0.5          # uneven drying
    tooth = paper_texture(cv.size, seed + 14) - 0.5                         # pigment settles in the grain
    density = 1.0 + edge_darkening * edge + turbulence * 2.0 * flow + granulation * 4.0 * tooth
    color = np.clip(color - (color - color * color) * (density[..., None] - 1.0), 0.0, 1.0)
    # Pencil underdrawing: textured by the paper tooth, a little soft.
    pencil = cv2.GaussianBlur(cv.line_alpha, (0, 0), 0.6) * np.clip(0.85 + tooth * 2.5, 0.0, 1.0)
    image = _composite_lines(color, cv, line_opacity, pencil, line_color)
    # Irregular unpainted margin.
    paper_rgb = rgb(paper) * (1.0 + (tooth * 0.10)[..., None])
    image = image * paper_rgb
    if border > 0:
        margin = border * min(width, height)
        inner = np.zeros((height, width), np.float32)
        cv2.rectangle(inner, (int(margin), int(margin)), (int(width - margin), int(height - margin)), 1.0, -1)
        ragged = cv2.GaussianBlur(inner, (0, 0), margin * 0.22) \
            + (raster.noise_field(cv.size, 60.0, 4, seed + 15) - 0.5) * 0.9
        painted = raster.smoothstep(ragged, 0.42, 0.58)[..., None]
        image = paper_rgb + (image - paper_rgb) * painted
    return np.clip(image, 0.0, 1.0).astype(np.float32)


# --- oil ---------------------------------------------------------------------

_BRISTLE_MIN_RADIUS = 5       # brushes thinner than this are drawn without bristle streaks


def paint_strokes(source, radii=(28, 14, 7, 3), threshold=0.055, max_steps=6, min_steps=2, curvature=0.55,
                  color_jitter=0.025, ground='#8a7560', flow_scale=260.0, seed=None):
    """Rebuild an image out of curved brush strokes, large brushes first.

    After Hertzmann 1998: for each brush size, compare the painting so far with
    a blurred reference; wherever it is still wrong, start a stroke in the
    reference color and let it run along the edges (perpendicular to the
    gradient). Flat areas have no gradient, so strokes there follow a smooth
    flow field instead, which gives the hand-laid look of a toned ground.
    Returns (painting (H,W,3) float, relief (H,W) float in 0..1).
    """
    seed = config.DEFAULT_SEED if seed is None else seed
    rng = np.random.default_rng(seed)
    height, width = source.shape[:2]
    canvas = np.empty((height, width, 3), np.uint8)
    canvas[:] = (rgb(ground) * 255).astype(np.uint8)
    relief = np.full((height, width), 128, np.uint8)
    flow_angle = raster.noise_field((width, height), flow_scale, 2, seed + 21) * 2.0 * np.pi
    flow = np.stack([np.cos(flow_angle), np.sin(flow_angle)], axis=-1)

    for layer, radius in enumerate(radii):
        reference = cv2.GaussianBlur(source, (0, 0), max(radius * 0.45, 0.6))
        lum = luminance(reference)
        gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=5)
        gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=5)
        step = max(int(radius), 2)
        error = np.sqrt(((canvas.astype(np.float32) / 255.0 - reference) ** 2).sum(axis=-1))
        area_error = cv2.blur(error, (step, step))
        ys, xs = np.mgrid[step // 2:height:step, step // 2:width:step]
        start = np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float32)
        start += rng.uniform(-0.4, 0.4, start.shape).astype(np.float32) * step
        start[:, 0] = np.clip(start[:, 0], 0, width - 1)
        start[:, 1] = np.clip(start[:, 1], 0, height - 1)
        ix, iy = start[:, 0].astype(int), start[:, 1].astype(int)
        if layer > 0:
            keep = area_error[iy, ix] > threshold
            start, ix, iy = start[keep], ix[keep], iy[keep]
        if len(start) == 0:
            continue
        start, ix, iy = _settle_on_side(start, source, gx, gy, radius)
        stroke_color = reference[iy, ix]
        paths = _trace_strokes(start, stroke_color, reference, canvas, gx, gy, flow, radius * 0.8,
                               max_steps, min_steps, curvature)
        jitter = 1.0 + rng.normal(0.0, color_jitter, (len(start), 1)).astype(np.float32)
        colors = np.clip(stroke_color * jitter * 255.0, 0, 255)
        heights = rng.integers(90, 200, len(start))
        thickness = max(int(radius * 2), 1)
        for index in rng.permutation(len(start)):
            path = paths[index]
            line = np.round(path * 8.0).astype(np.int32).reshape(-1, 1, 2)
            tone = colors[index]
            cv2.polylines(canvas, [line], False, tuple(int(c) for c in tone), thickness, cv2.LINE_AA, shift=3)
            cv2.polylines(relief, [line], False, int(heights[index]), thickness, cv2.LINE_AA, shift=3)
            if radius >= _BRISTLE_MIN_RADIUS:
                _bristles(canvas, relief, path, tone, int(heights[index]), radius, rng)
    return canvas.astype(np.float32) / 255.0, relief.astype(np.float32) / 255.0


_EDGE_GRADIENT = 1.5          # 5x5 Sobel response of a luminance step of about 0.03
_EDGE_STEP_BACK = 0.7         # how far (in brush radii) a start point moves off an edge


def _settle_on_side(start, source, gx, gy, radius):
    """Move stroke starts that sit on an edge to the side whose color they belong to.

    Strokes run along edges; one started exactly on the edge would take the mixed
    color of both sides and leave a gray dashed seam around every shape.
    """
    height, width = source.shape[:2]
    ix, iy = start[:, 0].astype(int), start[:, 1].astype(int)
    grad = np.stack([gx[iy, ix], gy[iy, ix]], axis=1)
    magnitude = np.linalg.norm(grad, axis=1)
    on_edge = magnitude > _EDGE_GRADIENT
    if not on_edge.any():
        return start, ix, iy
    normal = grad / np.maximum(magnitude, 1e-6)[:, None]
    reach = radius * _EDGE_STEP_BACK
    limit = np.array([width - 1, height - 1], np.float32)
    ahead = np.clip(start + normal * reach, 0, limit)
    behind = np.clip(start - normal * reach, 0, limit)
    own = source[iy, ix]

    def distance(points):
        return np.linalg.norm(source[points[:, 1].astype(int), points[:, 0].astype(int)] - own, axis=1)

    side = np.where((distance(ahead) < distance(behind))[:, None], ahead, behind)
    start = np.where(on_edge[:, None], side, start).astype(np.float32)
    return start, start[:, 0].astype(int), start[:, 1].astype(int)


def _bristles(canvas, relief, path, tone, height_value, radius, rng):
    """Streaks inside a stroke: a loaded brush leaves ridges, not a flat band."""
    direction = path[-1] - path[0]
    length = float(np.hypot(*direction))
    if length < 1.0:
        return
    normal = np.array([-direction[1], direction[0]]) / length
    for _ in range(3):
        offset = normal * rng.uniform(-0.7, 0.7) * radius
        shade = rng.uniform(0.90, 1.10)
        streak = np.round((path + offset) * 8.0).astype(np.int32).reshape(-1, 1, 2)
        width = max(int(radius * rng.uniform(0.25, 0.5)), 1)
        cv2.polylines(canvas, [streak], False, tuple(int(min(c * shade, 255)) for c in tone), width,
                      cv2.LINE_AA, shift=3)
        cv2.polylines(relief, [streak], False, int(np.clip(height_value + (shade - 1.0) * 600, 0, 255)),
                      width, cv2.LINE_AA, shift=3)


def _trace_strokes(start, stroke_color, reference, canvas, gx, gy, flow, radius, max_steps, min_steps, curvature):
    """Advance all strokes of one layer together. Returns a list of (K,2) arrays."""
    height, width = reference.shape[:2]
    count = len(start)
    position = start.copy()
    previous = np.zeros((count, 2), np.float32)
    alive = np.ones(count, bool)
    history = [position.copy()]
    painted = canvas.astype(np.float32) / 255.0
    for step_index in range(max_steps):
        ix = np.clip(position[:, 0].astype(int), 0, width - 1)
        iy = np.clip(position[:, 1].astype(int), 0, height - 1)
        grad = np.stack([gx[iy, ix], gy[iy, ix]], axis=1)
        strength = np.linalg.norm(grad, axis=1, keepdims=True)
        along_edge = np.stack([-grad[:, 1], grad[:, 0]], axis=1) / np.maximum(strength, 1e-6)
        direction = np.where(strength > 0.02, along_edge, flow[iy, ix])
        flip = (direction * previous).sum(axis=1, keepdims=True) < 0
        direction = np.where(flip, -direction, direction)
        if step_index > 0:
            direction = curvature * direction + (1.0 - curvature) * previous
            direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-6)
        if step_index >= min_steps:
            # Stop once the painting already matches the reference better than this stroke would.
            ref_here = reference[iy, ix]
            worse = np.abs(ref_here - painted[iy, ix]).sum(axis=1) < np.abs(ref_here - stroke_color).sum(axis=1)
            alive &= ~worse
        moved = position + direction * radius
        inside = (moved[:, 0] >= 0) & (moved[:, 0] < width) & (moved[:, 1] >= 0) & (moved[:, 1] < height)
        alive &= inside
        position = np.where(alive[:, None], moved, position)
        previous = np.where(alive[:, None], direction, previous).astype(np.float32)
        history.append(position.copy())
    stacked = np.stack(history, axis=1)                      # (count, steps+1, 2)
    return [stacked[i] for i in range(count)]


def finish_oil(cv, radii=(28, 14, 7, 3), impasto=0.35, canvas_weave=0.025, keep_lines=1.0,
               ground='#8a7560', contrast=1.05, saturation=1.10, seed=None, detail=None):
    """Oil painting: the picture is repainted with brush strokes, then lit from
    the side so the paint relief shows.

    detail: optional mask (H,W); inside it a second, careful pass with small
    brushes keeps features such as eyes and lips legible.
    """
    seed = config.DEFAULT_SEED if seed is None else seed
    source = cv.flatten(line_opacity=keep_lines)
    source = grade(source, contrast=contrast, saturation=saturation)
    painting, relief = paint_strokes(source, radii=radii, ground=ground, seed=seed)
    if detail is not None:
        small = max(radii[-1], 2)
        fine, fine_relief = paint_strokes(source, radii=(small * 2, small, max(small // 2, 1)), threshold=0.02,
                                          color_jitter=0.008, max_steps=4, ground=ground, seed=seed + 1)
        weight = cv2.GaussianBlur(np.clip(detail, 0.0, 1.0).astype(np.float32), (0, 0), 4.0)
        painting = painting * (1.0 - weight[..., None]) + fine * weight[..., None]
        relief = relief * (1.0 - weight) + (0.5 + (fine_relief - 0.5) * 0.4) * weight
    # Raking light across the paint ridges.
    bump = cv2.GaussianBlur(relief, (0, 0), 1.0)
    emboss = bump - raster.shift(bump, 1.5, 1.5)
    painting = np.clip(painting * (1.0 + impasto * emboss[..., None] * 2.2), 0.0, 1.0)
    # Linen weave showing through thin paint.
    width, height = cv.size
    xs, ys = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    weave = np.sin(xs * 1.9) * np.sin(ys * 1.9) + 0.6 * (paper_texture(cv.size, seed + 2) - 0.5) * 6.0
    painting = np.clip(painting * (1.0 + canvas_weave * weave[..., None]), 0.0, 1.0)
    return vignette(painting, 0.18).astype(np.float32)
