"""Brushwork: rebuild an image from layers of brush strokes (no neural network).

Method after Hertzmann, "Painterly Rendering with Curved Brush Strokes of
Multiple Sizes" (SIGGRAPH 1998):
  1. Start from a toned ground.
  2. For each brush size, large to small: blur the source to that size, find
     grid cells where the canvas still differs from it, and start a stroke at
     the worst pixel of each such cell.
  3. A stroke takes the source colour at its start and walks along the local
     edge direction until the canvas already matches better than the stroke would.
Two additions make it suit portraits:
  focus map  small brushes are only allowed where detail matters (eyes, lips)
  relief     each stroke also writes a height, lit afterwards like thick paint
  wet blend  a light edge-preserving smooth, as neighbouring wet strokes mix
"""
import cv2
import numpy as np

from raster import blur, noise, smoothstep

# A stroke's value and hue may wander by these shares, as paint is never mixed evenly.
VALUE_JITTER = 0.028
HUE_JITTER = 0.008
# Paint thickness range written to the height map (0..255); a narrow range keeps ridges low.
THICKNESS_RANGE = (170, 255)
# Brushes at least this wide leave full-height ridges.
FULL_RELIEF_RADIUS = 14.0
# Bristle streaks inside one stroke: brightness spread and count per brush radius.
BRISTLE_SPREAD = 0.05
BRISTLES_PER_RADIUS = 0.35
# Below this local contrast the image has no edge to follow; use the fallback sweep.
FLAT_ENERGY = 2e-4


def edge_directions(image, sigma, fallback_angle):
    """Unit vectors along local edges; in flat areas, along `fallback_angle` (radians field).

    How: structure tensor. Angles are blended as doubled angles because an
    edge direction has no front or back.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    jxx, jxy, jyy = blur(gx * gx, sigma), blur(gx * gy, sigma), blur(gy * gy, sigma)
    along_edge = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + 0.5 * np.pi
    energy = jxx + jyy
    coherence = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (energy + 1e-9)
    trust = coherence * smoothstep(energy, FLAT_ENERGY, FLAT_ENERGY * 8)
    vx = trust * np.cos(2 * along_edge) + (1 - trust) * np.cos(2 * fallback_angle)
    vy = trust * np.sin(2 * along_edge) + (1 - trust) * np.sin(2 * fallback_angle)
    angle = 0.5 * np.arctan2(vy, vx)
    return np.cos(angle), np.sin(angle)


def stroke_starts(error, allowed, threshold, grid):
    """Worst pixel of every grid cell whose mean error exceeds the threshold."""
    height, width = error.shape
    rows, cols = height // grid, width // grid
    cells = error[:rows * grid, :cols * grid].reshape(rows, grid, cols, grid).transpose(0, 2, 1, 3)
    cells = cells.reshape(rows, cols, grid * grid)
    worst = cells.argmax(axis=2)
    ys = np.arange(rows)[:, None] * grid + worst // grid
    xs = np.arange(cols)[None, :] * grid + worst % grid
    keep = (cells.mean(axis=2) > threshold) & (allowed[ys, xs] > 0.5)
    return np.stack([xs[keep], ys[keep]], axis=1).astype(np.float32)


def trace_strokes(starts, reference, canvas, direction, radius, options, rng):
    """Walk every stroke at once. Returns (points[N, L, 2], lengths[N], colors[N, 3])."""
    dir_x, dir_y = direction
    height, width = reference.shape[:2]
    count = len(starts)
    position = starts.copy()
    xi, yi = position[:, 0].astype(int), position[:, 1].astype(int)
    colors = reference[yi, xi]
    heading = np.stack([dir_x[yi, xi], dir_y[yi, xi]], axis=1)
    heading *= rng.choice([-1.0, 1.0], size=(count, 1)).astype(np.float32)
    alive = np.ones(count, bool)
    lengths = np.ones(count, int)
    points = [position.copy()]
    curvature = options["curvature"]
    for step in range(options["max_length"]):
        xi = np.clip(position[:, 0].astype(int), 0, width - 1)
        yi = np.clip(position[:, 1].astype(int), 0, height - 1)
        local = np.stack([dir_x[yi, xi], dir_y[yi, xi]], axis=1)
        local[(local * heading).sum(axis=1) < 0] *= -1
        heading = curvature * local + (1 - curvature) * heading
        heading /= np.maximum(np.linalg.norm(heading, axis=1, keepdims=True), 1e-6)
        target = position + heading * radius
        tx, ty = target[:, 0].astype(int), target[:, 1].astype(int)
        inside = (tx >= 0) & (tx < width) & (ty >= 0) & (ty < height)
        tx, ty = np.clip(tx, 0, width - 1), np.clip(ty, 0, height - 1)
        if step >= options["min_length"]:
            wanted = reference[ty, tx]
            canvas_better = np.abs(wanted - canvas[ty, tx]).sum(axis=1) < np.abs(wanted - colors).sum(axis=1)
            alive &= ~canvas_better
        alive &= inside
        position = np.where(alive[:, None], target, position)
        lengths += alive
        points.append(position.copy())
    return np.stack(points, axis=1), lengths, colors


def draw_strokes(canvas, relief, points, lengths, colors, radius, rng):
    """Render strokes in random order into the colour canvas and the height map (uint8)."""
    bristles = max(int(radius * BRISTLES_PER_RADIUS), 1)
    for index in rng.permutation(len(points)):
        path = points[index, :lengths[index]]
        wander = (1 + rng.normal(0, VALUE_JITTER)) * (1 + rng.normal(0, HUE_JITTER, 3))
        tint = np.clip(colors[index] * wander, 0, 1) * 255.0
        # Why scale by radius: a small brush carries little paint, so it leaves a low ridge.
        low, high = THICKNESS_RANGE
        thick = high - rng.random() * (high - low) * min(radius / FULL_RELIEF_RADIUS, 1.0)
        line = np.round(path * 8).astype(np.int32).reshape(-1, 1, 2)
        width = max(int(round(radius * 2)), 1)
        if len(path) == 1:
            center = tuple(line[0, 0])
            cv2.circle(canvas, center, int(radius * 8), tint.tolist(), -1, cv2.LINE_AA, shift=3)
            cv2.circle(relief, center, int(radius * 8), int(thick), -1, cv2.LINE_AA, shift=3)
            continue
        cv2.polylines(canvas, [line], False, tint.tolist(), width, cv2.LINE_AA, shift=3)
        cv2.polylines(relief, [line], False, int(thick), width, cv2.LINE_AA, shift=3)
        if bristles < 2:
            continue
        tangent = path[-1] - path[0]
        normal = np.array([-tangent[1], tangent[0]]) / max(np.linalg.norm(tangent), 1e-6)
        for offset in rng.uniform(-0.75, 0.75, bristles):
            streak = np.round((path + normal * offset * radius) * 8).astype(np.int32).reshape(-1, 1, 2)
            shade = 1 + rng.normal(0, BRISTLE_SPREAD)
            streak_width = max(int(radius * 0.45), 1)
            cv2.polylines(canvas, [streak], False, np.clip(tint * shade, 0, 255).tolist(), streak_width, cv2.LINE_AA, shift=3)
            cv2.polylines(relief, [streak], False, int(np.clip(thick * shade, 0, 255)), streak_width, cv2.LINE_AA, shift=3)


def light_relief(canvas, relief, light, strength):
    """Shade the paint surface from its height map, as raking light on impasto."""
    height = blur(relief.astype(np.float32) / 255.0, 0.9)
    slope_x = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
    slope_y = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
    shade = 1.0 - strength * (slope_x * light[0] + slope_y * light[1])
    return canvas * np.clip(shade, 0.6, 1.4)[..., None]


def canvas_weave(shape, period, seed):
    """Woven cloth texture in 0..1 (0.5 = neutral)."""
    height, width = shape
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    weave = np.sin(2 * np.pi * xs / period) * np.sin(2 * np.pi * ys / period)
    return 0.5 + 0.35 * weave + 0.3 * (noise(shape, period * 0.6, seed, 2) - 0.5)


def paint(source, focus, light, options, seed):
    """Re-paint `source` (float RGB) with brush strokes. `focus` 0..1 = where detail is allowed."""
    rng = np.random.default_rng(seed)
    height, width = source.shape[:2]
    canvas = np.empty((height, width, 3), np.uint8)
    canvas[:] = np.round(np.asarray(options["ground"]) * 255)
    relief = np.zeros((height, width), np.uint8)
    sweep = np.deg2rad(options["sweep_deg"]) + (noise((height, width), options["sweep_cell"], seed + 1, 2) - 0.5) * np.pi * options["sweep_wander"]
    for layer in options["layers"]:
        radius = layer["radius"]
        reference = blur(source, radius * options["blur_factor"])
        direction = edge_directions(reference, radius * 1.5, sweep)
        current = canvas.astype(np.float32) / 255.0
        error = np.abs(current - reference).sum(axis=2)
        allowed = (focus >= layer["min_focus"]).astype(np.float32)
        grid = max(int(radius * options["grid_factor"]), 1)
        starts = stroke_starts(error, allowed, layer["threshold"], grid)
        if len(starts) == 0:
            continue
        points, lengths, colors = trace_strokes(starts, reference, current, direction, radius, layer, rng)
        draw_strokes(canvas, relief, points, lengths, colors, radius, rng)
    blended = cv2.bilateralFilter(canvas, 0, options["wet_blend"] * 255.0, 2.0) if options["wet_blend"] > 0 else canvas
    painted = light_relief(blended.astype(np.float32) / 255.0, relief, light, options["relief"])
    weave = canvas_weave((height, width), options["weave_period"], seed + 2)
    return np.clip(painted * (1.0 + options["weave"] * (weave - 0.5))[..., None], 0.0, 1.0)
