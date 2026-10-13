"""Oil pass: repaints the underpainting image as a set of real brushstrokes.

Follows the layered curved-stroke algorithm of Hertzmann (1998). A large brush covers everything first.
Small brushes repaint only where the difference from the underpainting is large, so strokes gather where detail is
needed.
On top of that it adds relief lighting from paint thickness (impasto) and the canvas weave.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import noise

# Brush radii (logical units). Painting goes from the large brush to the small one.
BRUSH_RADII = (22.0, 10.0, 4.5)
# Spacing of stroke start points as a multiple of the brush radius. Smaller is denser.
GRID_FACTOR = 0.9
# Small brushes are added only where the color difference between the underpainting and the current frame
# exceeds this value.
ERROR_THRESHOLD = 0.05
MIN_STROKE_STEPS = 2
MAX_STROKE_STEPS = 9
# Fraction of the previous direction mixed in so the brush does not turn sharply.
CURVATURE_FILTER = 0.6
# Jitter the color of each stroke a little to create the mixed-color feel of oil paint.
COLOR_JITTER = 0.05
HUE_JITTER_RATIO = 0.25
# Per-stroke width variation and the width change along the length (start, body, end).
STROKE_WIDTH_RANGE = (0.75, 1.15)
STROKE_PROFILE_POSITIONS = (0.0, 0.25, 0.7, 1.0)
STROKE_PROFILE = (0.85, 1.0, 0.95, 0.55)
# When the stroke color and the underpainting color differ by this much, the stroke has crossed an edge and
# the brush lifts.
EDGE_TOLERANCE = 0.12
# Default brush direction (degrees) for flat areas without clear contours.
DEFAULT_ANGLE_DEG = -25.0
# Areas with a color change weaker than this value count as flat.
FLAT_ENERGY = 0.004
BRISTLE_LENGTH = 9.0
RELIEF_STRENGTH = 0.55
# Weights of the two relief components. A large thickness difference between strokes makes the rims of large
# strokes stand out like stains.
THICKNESS_WEIGHT = 0.9
BRISTLE_WEIGHT = 0.26
# The first layer (largest brush) has less color jitter. Brightness differences of wide strokes look like
# stains on flat surfaces.
FIRST_LAYER_JITTER_RATIO = 0.5
WEAVE_STRENGTH = 0.05
LIGHT_DIRECTION = (-0.7, -0.7)
POLYLINE_SHIFT_BITS = 3


def _orientation_field(reference, radius_px, flow_hint):
    """Direction for the brush to follow (radians). A structure tensor finds the direction parallel to color edges."""
    luma = cv2.GaussianBlur(colors.luminance(reference), (0, 0), max(radius_px * 0.5, 1.0))
    grad_x = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    sigma = max(radius_px, 2.0)
    j_xx = cv2.GaussianBlur(grad_x * grad_x, (0, 0), sigma)
    j_xy = cv2.GaussianBlur(grad_x * grad_y, (0, 0), sigma)
    j_yy = cv2.GaussianBlur(grad_y * grad_y, (0, 0), sigma)
    angle = 0.5 * np.arctan2(2.0 * j_xy, j_xx - j_yy) + np.pi / 2.0
    energy = j_xx + j_yy

    fallback = np.full_like(angle, np.deg2rad(DEFAULT_ANGLE_DEG))
    if flow_hint is not None:
        hinted = ~np.isnan(flow_hint)
        fallback[hinted] = flow_hint[hinted]
        # Where the artist set a direction, it yields to the automatic direction only at very clear edges.
        flat = np.where(hinted, energy < FLAT_ENERGY * 6.0, energy < FLAT_ENERGY)
    else:
        flat = energy < FLAT_ENERGY
    angle = np.where(flat, fallback, angle)
    # Angles repeat every 180 degrees, so they are doubled to get a correct average.
    cos2 = cv2.GaussianBlur(np.cos(2.0 * angle), (0, 0), sigma * 0.5)
    sin2 = cv2.GaussianBlur(np.sin(2.0 * angle), (0, 0), sigma * 0.5)
    return 0.5 * np.arctan2(sin2, cos2)


def _seed_points(shape_hw, spacing, rng):
    height, width = shape_hw
    ys, xs = np.mgrid[spacing / 2.0:height:spacing, spacing / 2.0:width:spacing]
    points = np.stack([xs.ravel(), ys.ravel()], axis=1)
    points += rng.uniform(-spacing / 2.0, spacing / 2.0, points.shape)
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    return points


def _sample(image, points):
    xi = np.clip(np.round(points[:, 0]).astype(int), 0, image.shape[1] - 1)
    yi = np.clip(np.round(points[:, 1]).astype(int), 0, image.shape[0] - 1)
    return image[yi, xi]


def _trace_strokes(seeds, reference, painted, angle, radius_px):
    """Advance every stroke one step at a time. Returns the path array and the point count of each path.

    If painted is None, this is the first layer on an empty frame and the brush lifts only at color edges.
    """
    height, width = angle.shape
    position = seeds.copy()
    stroke_color = _sample(reference, position)
    alive = np.ones(len(seeds), bool)
    previous = np.zeros_like(position)
    counts = np.ones(len(seeds), int)
    trail = [position.copy()]
    for step in range(1, MAX_STROKE_STEPS + 1):
        theta = _sample(angle, position)
        direction = np.stack([np.cos(theta), np.sin(theta)], axis=1)
        direction[(direction * previous).sum(axis=1) < 0.0] *= -1.0
        if step > 1:
            direction = CURVATURE_FILTER * direction + (1.0 - CURVATURE_FILTER) * previous
            direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-6)
        candidate = position + direction * radius_px
        inside = (candidate[:, 0] >= 0) & (candidate[:, 0] < width) & \
                 (candidate[:, 1] >= 0) & (candidate[:, 1] < height)
        target = _sample(reference, candidate)
        distance = np.linalg.norm(target - stroke_color, axis=1)
        # The brush lifts where the stroke color drifts farther from the underpainting than the current frame.
        worse = np.zeros(len(seeds), bool) if painted is None else \
            np.linalg.norm(target - _sample(painted, candidate), axis=1) < distance
        crossed = distance > EDGE_TOLERANCE
        alive &= inside & ~crossed & ~((step > MIN_STROKE_STEPS) & worse)
        position = np.where(alive[:, None], candidate, position)
        counts += alive
        previous = direction
        trail.append(position.copy())
    return np.stack(trail, axis=1), counts, stroke_color


def _paint_layer(painted, relief, reference, angle, radius_px, first_layer, color_jitter, rng):
    blurred = cv2.GaussianBlur(reference, (0, 0), max(radius_px * 0.5, 0.8))
    seeds = _seed_points(angle.shape, max(radius_px * GRID_FACTOR, 2.0), rng)
    if not first_layer:
        error = np.abs(painted.astype(np.float32) / 255.0 - blurred).mean(axis=-1)
        error = cv2.GaussianBlur(error, (0, 0), radius_px)
        seeds = seeds[_sample(error, seeds) > ERROR_THRESHOLD]
    if len(seeds) == 0:
        return
    snapshot = None if first_layer else painted.astype(np.float32) / 255.0
    paths, counts, stroke_colors = _trace_strokes(seeds, blurred, snapshot, angle, radius_px)
    # Jitter brightness strongly and hue weakly. Strong per-channel jitter leaves pure-hue stains on dark
    # surfaces.
    brightness = 1.0 + rng.normal(0.0, color_jitter, (len(seeds), 1))
    hue_drift = rng.normal(0.0, color_jitter * HUE_JITTER_RATIO, stroke_colors.shape)
    stroke_colors = np.clip(stroke_colors * brightness + hue_drift, 0.0, 1.0)
    for index in rng.permutation(len(seeds)):
        _draw_stroke(painted, relief, paths[index, :counts[index]], stroke_colors[index], radius_px, rng)


def _draw_stroke(painted, relief, points, stroke_color, radius_px, rng):
    """Stamp one stroke on the frame and the relief record. A flat-brush mark with a blunt start and a tapering end."""
    if len(points) == 1:
        points = np.vstack([points, points + (radius_px * 0.6, 0.0)])
    heading = points[-1] - points[0]
    width = 2.0 * radius_px * rng.uniform(*STROKE_WIDTH_RANGE)
    profile = np.interp(np.linspace(0.0, 1.0, len(points)), STROKE_PROFILE_POSITIONS, STROKE_PROFILE) * width
    tangent = np.gradient(points, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-6)
    offset = np.stack([tangent[:, 1], -tangent[:, 0]], axis=1) * profile[:, None] / 2.0
    # Extend both ends of the center line by half a width to mark where the brush lands and lifts.
    lead = points[:1] - tangent[:1] * radius_px * 0.5
    tail = points[-1:] + tangent[-1:] * radius_px * 0.5
    outline = np.vstack([lead, points + offset, tail, (points - offset)[::-1]])
    fixed = np.round(outline * (1 << POLYLINE_SHIFT_BITS)).astype(np.int32)
    paint = tuple(int(channel * 255.0) for channel in stroke_color)
    cv2.fillPoly(painted, [fixed], paint, cv2.LINE_AA, POLYLINE_SHIFT_BITS)
    # Record a different thickness and direction for each stroke for the relief lighting and brush texture.
    theta2 = 2.0 * np.arctan2(heading[1], heading[0])
    record = (int(rng.integers(60, 255)), int(127.5 + 127.5 * np.cos(theta2)), int(127.5 + 127.5 * np.sin(theta2)))
    cv2.fillPoly(relief, [fixed], record, cv2.LINE_8, POLYLINE_SHIFT_BITS)


def _bristle_streaks(relief, length_px, seed):
    """Noise stretched along the stroke direction. Creates the grain that bristles leave in the paint."""
    height, width = relief.shape[:2]
    theta = 0.5 * np.arctan2(relief[..., 2].astype(np.float32) - 127.5, relief[..., 1].astype(np.float32) - 127.5)
    step_x, step_y = np.cos(theta), np.sin(theta)
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    speckle = noise.white((height, width), seed)
    steps = max(int(round(length_px)), 1)
    total = np.zeros((height, width), np.float32)
    for offset in range(-steps, steps + 1):
        total += cv2.remap(speckle, xs + offset * step_x, ys + offset * step_y,
                           cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    streaks = total / (2 * steps + 1)
    return (streaks - streaks.mean()) / max(float(streaks.std()), 1e-6)


def render(canvas, brush_radii=BRUSH_RADII, relief=RELIEF_STRENGTH, weave=WEAVE_STRENGTH,
           color_jitter=COLOR_JITTER, detail=None):
    """Return a 0-1 RGB image of the current canvas repainted as an oil painting.

    brush_radii: list of brush radii (logical units). A smaller last value keeps more detail.
    relief: strength of the paint-thickness relief. 0 gives a flat gouache feel.
    detail: the smallest brush is used only inside this shape. Set it to give detail to the focal area only.
    Areas with a direction set in canvas.flow are stroked in that direction (see Canvas.direct).
    """
    reference = canvas.image().astype(np.float32)
    rng = np.random.default_rng(canvas.next_seed())
    # Start from a blurred underpainting so the base color shows through gaps the first layer did not cover.
    painted = (cv2.GaussianBlur(reference, (0, 0), brush_radii[0] * canvas.scale) * 255.0).astype(np.uint8)
    relief_map = np.zeros(reference.shape, np.uint8)
    relief_map[..., 1] = 255
    relief_map[..., 2] = 127
    for layer_index, radius in enumerate(brush_radii):
        radius_px = max(radius * canvas.scale, 1.0)
        angle = _orientation_field(reference, radius_px, canvas.flow)
        layer_reference = reference
        is_finest = layer_index == len(brush_radii) - 1 and layer_index > 0
        if is_finest and detail is not None:
            # Outside the focal area, the target is the current frame so no small brushes are added.
            weight = detail.placed(0, 0, canvas.px_w, canvas.px_h)[..., None]
            layer_reference = reference * weight + (painted.astype(np.float32) / 255.0) * (1.0 - weight)
        layer_jitter = color_jitter * (FIRST_LAYER_JITTER_RATIO if layer_index == 0 else 1.0)
        _paint_layer(painted, relief_map, layer_reference, angle, radius_px, layer_index == 0, layer_jitter, rng)

    result = painted.astype(np.float32) / 255.0
    if relief > 0.0:
        streaks = _bristle_streaks(relief_map, BRISTLE_LENGTH * canvas.scale, canvas.next_seed())
        thickness = cv2.GaussianBlur(relief_map[..., 0].astype(np.float32) / 255.0, (0, 0), 0.8)
        surface = cv2.GaussianBlur(thickness * THICKNESS_WEIGHT + streaks * BRISTLE_WEIGHT, (0, 0), 0.7)
        grad_x = cv2.Sobel(surface, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(surface, cv2.CV_32F, 0, 1, ksize=3)
        light = np.asarray(LIGHT_DIRECTION, np.float32)
        shading = -(grad_x * light[0] + grad_y * light[1]) * relief * 0.35
        result = result * (1.0 + np.clip(shading, -0.3, 0.3)[..., None])
        result = result * (1.0 + 0.03 * relief * np.clip(streaks, -2.0, 2.0)[..., None])
    if weave > 0.0:
        texture = noise.canvas_weave(result.shape[:2], canvas.next_seed(), canvas.scale)
        result = result * (1.0 - weave * (1.0 - texture)[..., None])
    return np.clip(result, 0.0, 1.0)
