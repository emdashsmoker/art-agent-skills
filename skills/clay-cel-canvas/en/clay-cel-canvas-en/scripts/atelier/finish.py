"""Finishing passes. Each takes and returns a float32 RGB image in 0..1.

Sizes are given in canvas units and converted with `ppu` (pixels per unit), so a
small preview and a large final render look alike.
"""
import cv2
import numpy as np

from .style import Finish

LUMA = np.array([0.299, 0.587, 0.114], np.float32)

# --- anime ---
BLOOM_THRESHOLD = 0.80
BLOOM_RADIUS = 16.0
BLOOM_STRENGTH = 0.30
DIFFUSION_RADIUS = 9.0
DIFFUSION_AMOUNT = 0.22
ANIME_SATURATION = 1.06
ANIME_GRAIN = 0.012

# --- illustration ---
WOBBLE_AMPLITUDE = 1.5
WOBBLE_CELL = 38.0
PAPER_COLOR = np.array([0.965, 0.935, 0.885], np.float32)
PAPER_AMOUNT = 0.55
MOTTLE_CELL = 120.0
MOTTLE_AMOUNT = 0.035
SPECKLE_AMOUNT = 0.16
ILLUST_GRAIN = 0.028

# --- painterly ---
BRUSH_RADII = (30.0, 15.0, 7.0, 3.2)  # large to small, like blocking-in then refining
BROAD_FORM_SIGMA = 28.0               # units; scale at which strokes follow big shapes
BRUSH_LENGTH_RANGE = (3.0, 9.0)       # stroke length as a multiple of its radius
BRUSH_EDGE_TOLERANCE = 0.16           # a stroke stops where colour differs by this much
BRUSH_ERROR_THRESHOLD = 0.085         # repaint only where the canvas is this far off
BRUSH_VALUE_JITTER = 0.022            # per-stroke lightness variation
BRUSH_HUE_JITTER = 0.010              # per-stroke colour variation
BRUSH_TIP_WIDTH = 0.7                 # the stroke narrows to this fraction at its far end
BRISTLE_COUNT = 4
FLOW_CELL = 160.0
IMPASTO_AMOUNT = 0.045
WEAVE_PERIOD = 3.4
WEAVE_AMOUNT = 0.030
FOCUS_RESTORE = 0.55


def value_noise(shape, cell_px, rng, octaves=3):
    """Smooth random field in roughly 0..1; cell_px is the size of the largest blobs."""
    height, width = shape
    total = np.zeros(shape, np.float32)
    weight_sum = 0.0
    for octave in range(octaves):
        cell = max(cell_px / 2 ** octave, 1.0)
        coarse = rng.random((int(height / cell) + 3, int(width / cell) + 3)).astype(np.float32)
        weight = 0.5 ** octave
        total += weight * cv2.resize(coarse, (width, height), interpolation=cv2.INTER_CUBIC)
        weight_sum += weight
    return total / weight_sum


def _blur(image, sigma):
    return cv2.GaussianBlur(image, (0, 0), max(sigma, 0.3))


def _luma(image):
    return image @ LUMA


def _saturate(image, amount):
    grey = _luma(image)[..., None]
    return grey + (image - grey) * amount


def _screen(base, top):
    return 1 - (1 - base) * (1 - top)


def _grain(image, amount, rng):
    noise = rng.normal(0, amount, image.shape[:2]).astype(np.float32)
    return image + noise[..., None]


def finish_anime(image, ppu, rng, focus):
    """Bloom on the highlights plus a soft diffusion glow, as in anime compositing."""
    bright = np.clip((image - BLOOM_THRESHOLD) / (1 - BLOOM_THRESHOLD), 0, 1)
    image = _screen(image, _blur(bright, BLOOM_RADIUS * ppu) * BLOOM_STRENGTH)
    diffused = _screen(image, _blur(image, DIFFUSION_RADIUS * ppu))
    image = image + (diffused - image) * DIFFUSION_AMOUNT * (1 - 0.5 * focus[..., None])
    image = _saturate(image, ANIME_SATURATION)
    return _grain(image, ANIME_GRAIN, rng)


def finish_illust(image, ppu, rng, focus):
    """Hand-cut edges, paper tone and print grain, as in gouache or risograph work."""
    height, width = image.shape[:2]
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    shift_x = (value_noise((height, width), WOBBLE_CELL * ppu, rng) - 0.5) * 2
    shift_y = (value_noise((height, width), WOBBLE_CELL * ppu, rng) - 0.5) * 2
    amplitude = WOBBLE_AMPLITUDE * ppu * 2 * (1 - 0.7 * focus)
    image = cv2.remap(image, grid_x + shift_x * amplitude, grid_y + shift_y * amplitude,
                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    image = image * (1 - PAPER_AMOUNT + PAPER_AMOUNT * PAPER_COLOR)
    mottle = value_noise((height, width), MOTTLE_CELL * ppu, rng) - 0.5
    image = image * (1 + MOTTLE_AMOUNT * 2 * mottle[..., None])
    # Why: ink never covers paper fully, so dark areas show light flecks.
    speckle = np.clip(rng.random((height, width)).astype(np.float32) - 0.72, 0, 1) / 0.28
    speckle = _blur(speckle, 0.6 * ppu)
    image = image + (1 - _luma(image))[..., None] * speckle[..., None] * SPECKLE_AMOUNT
    return _grain(image, ILLUST_GRAIN, rng)


def _edge_direction(luma, sigma):
    """Angle running along edges at one scale, and how strong the edge is."""
    smooth = _blur(luma, sigma)
    grad_x = cv2.Sobel(smooth, cv2.CV_32F, 1, 0)
    grad_y = cv2.Sobel(smooth, cv2.CV_32F, 0, 1)
    return np.arctan2(grad_y, grad_x) + np.pi / 2, np.hypot(grad_x, grad_y)


def _stroke_angles(luma, radius, broad_sigma, flow):
    """Stroke direction per pixel.

    Strokes follow nearby edges; failing that the big shapes they sit in (so
    hair is painted along its length); failing that a loose flow field.
    """
    local_angle, local_strength = _edge_direction(luma, radius * 0.8)
    broad_angle, broad_strength = _edge_direction(luma, broad_sigma)
    angles = np.where(broad_strength > 0.0004, broad_angle, flow)
    return np.where(local_strength > 0.004, local_angle, angles)


def _reach(reference, color, start, step_vector, max_steps):
    """How far a stroke may run from start before the picture changes colour.

    Why: a stroke that crosses an edge smears two areas into each other.
    """
    height, width = reference.shape[:2]
    position = np.array(start, float)
    for step in range(1, max_steps + 1):
        position += step_vector
        col, row = int(position[0]), int(position[1])
        if not (0 <= col < width and 0 <= row < height):
            return step - 1
        if np.abs(reference[row, col] - color).sum() > BRUSH_EDGE_TOLERANCE:
            return step - 1
    return max_steps


def _lay_stroke(canvas, relief, image, color, tail, tip, radius, rng):
    """Paint one flat-brush stroke from tail to tip (pixel coordinates).

    The stroke only lands on pixels whose own colour is close to its colour.
    Why: a brush this wide would otherwise spill across outlines and leave
    ragged silhouettes.
    """
    height, width = canvas.shape[:2]
    along = (tip - tail) / max(np.linalg.norm(tip - tail), 1e-6)
    across = np.array([-along[1], along[0]]) * radius
    corners = np.array([tail + across, tip + across * BRUSH_TIP_WIDTH,
                        tip - across * BRUSH_TIP_WIDTH, tail - across])
    x0, y0 = np.maximum(np.floor(corners.min(axis=0)).astype(int) - 1, 0)
    x1, y1 = np.minimum(np.ceil(corners.max(axis=0)).astype(int) + 2, (width, height))
    if x1 <= x0 or y1 <= y0:
        return
    origin = np.array([x0, y0])
    footprint = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillConvexPoly(footprint, np.round(corners - origin).astype(np.int32), 255, cv2.LINE_AA)
    # Bristles: each hair of the brush leaves paint of a slightly different thickness.
    ridges = np.zeros(footprint.shape, np.float32)
    hair = max(int(round(radius * 2 / BRISTLE_COUNT)), 1)
    for index in range(BRISTLE_COUNT):
        offset = across * ((index + 0.5) / BRISTLE_COUNT * 2 - 1)
        cv2.line(ridges, tuple(int(v) for v in np.round(tail + offset - origin)),
                 tuple(int(v) for v in np.round(tip + offset * BRUSH_TIP_WIDTH - origin)),
                 float(rng.uniform(0.25, 0.75)), hair)
    region = (slice(y0, y1), slice(x0, x1))
    distance = np.abs(image[region] - color).sum(axis=2)
    alike = np.clip((BRUSH_EDGE_TOLERANCE * 1.5 - distance) / (BRUSH_EDGE_TOLERANCE * 0.5), 0, 1)
    alpha = footprint.astype(np.float32) / 255 * alike
    canvas[region] += (color - canvas[region]) * alpha[..., None]
    relief[region] += (ridges - relief[region]) * alpha * (ridges > 0)


def _paint_layer(canvas, relief, image, reference, angles, error, radius, focus, cover_all, rng):
    """Lay one pass of brush strokes of a single size onto canvas and relief."""
    height, width = reference.shape[:2]
    step = radius * 1.1
    xs = np.arange(step / 2, width, step)
    ys = np.arange(step / 2, height, step)
    grid = np.stack(np.meshgrid(xs, ys), axis=-1).reshape(-1, 2)
    grid += rng.uniform(-step / 2, step / 2, grid.shape)
    rng.shuffle(grid)
    for x, y in grid:
        col = min(max(int(x), 0), width - 1)
        row = min(max(int(y), 0), height - 1)
        calm = 1 - 0.75 * focus[row, col]   # focal areas get tighter, quieter strokes
        if not cover_all and error[row, col] < BRUSH_ERROR_THRESHOLD * calm:
            continue
        angle = angles[row, col] + rng.normal(0, 0.15)
        along = np.array([np.cos(angle), np.sin(angle)])
        pure = reference[row, col]
        max_steps = int(round(rng.uniform(*BRUSH_LENGTH_RANGE) / 2))
        ahead = _reach(reference, pure, (x, y), along * radius, max_steps) * radius
        behind = _reach(reference, pure, (x, y), -along * radius, max_steps) * radius
        jitter = rng.normal(0, BRUSH_VALUE_JITTER) + rng.normal(0, BRUSH_HUE_JITTER, 3)
        color = np.clip(pure + jitter * calm, 0, 1).astype(np.float32)
        tail = np.array([x, y]) - along * (behind + radius / 2)
        tip = np.array([x, y]) + along * (ahead + radius / 2)
        _lay_stroke(canvas, relief, image, color, tail, tip, radius, rng)


def finish_painterly(image, ppu, rng, focus):
    """Rebuild the picture from brush strokes, large to small, then add paint relief."""
    height, width = image.shape[:2]
    image = np.clip(image, 0, 1).astype(np.float32)
    luma = _luma(image)
    flow = value_noise((height, width), FLOW_CELL * ppu, rng, octaves=2) * 2 * np.pi
    canvas = _blur(image, BRUSH_RADII[0] * ppu)        # underpainting
    relief = np.full((height, width), 0.5, np.float32)
    for index, radius_units in enumerate(BRUSH_RADII):
        radius = max(radius_units * ppu, 1.0)
        reference = _blur(image, radius * 0.45)
        angles = _stroke_angles(luma, radius, BROAD_FORM_SIGMA * ppu, flow)
        error = _blur(np.abs(canvas - reference).sum(axis=2), radius * 0.5)
        _paint_layer(canvas, relief, image, reference, angles, error, radius, focus,
                     cover_all=(index == 0), rng=rng)
    painted = canvas + (image - canvas) * (focus * FOCUS_RESTORE)[..., None]

    bumps = _blur(relief, 1.6 * max(ppu, 0.5))
    lit = -(cv2.Sobel(bumps, cv2.CV_32F, 1, 0) + cv2.Sobel(bumps, cv2.CV_32F, 0, 1))
    painted = painted + np.clip(lit, -1, 1)[..., None] * IMPASTO_AMOUNT

    period = WEAVE_PERIOD * ppu
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    weave = np.sin(grid_x * 2 * np.pi / period) * np.sin(grid_y * 2 * np.pi / period)
    return painted * (1 + WEAVE_AMOUNT * weave[..., None])


FINISHERS = {
    Finish.ANIME: finish_anime,
    Finish.ILLUST: finish_illust,
    Finish.PAINTERLY: finish_painterly,
}


def apply_finish(finish, image, ppu, rng, focus):
    return np.clip(FINISHERS[finish](image, ppu, rng, focus), 0, 1)
