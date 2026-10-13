"""2D lighting: estimates form from a flat mask so shadows can be computed.

The core trick is inflation: a mask is puffed up like a pillow to get a height
field, the height field gives surface normals, and normals give light and shadow.
"""
import numpy as np
from scipy import ndimage as ndi

INSIDE_LEVEL = 0.5           # coverage above this counts as inside the shape
DEFAULT_SMOOTHING = 0.18     # blur of the height field as a fraction of the bevel radius
DEFAULT_LIGHT = (-0.55, -0.62, 0.56)   # from the upper left, slightly in front


def smoothstep(edge_low, edge_high, value):
    span = max(edge_high - edge_low, 1e-6)
    t = np.clip((value - edge_low) / span, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def blur(image, sigma):
    """Gaussian blur on the two spatial axes only.

    A 2D mask is blurred inside the box that holds it; most masks cover a small part of the canvas.
    """
    if sigma <= 0:
        return image
    if image.ndim == 2:
        box = mask_box(image, padding=int(np.ceil(sigma * 3)) + 1, level=0.0)
        if box is None:
            return image
        y0, y1, x0, x1 = box
        result = np.zeros_like(image)
        result[y0:y1, x0:x1] = ndi.gaussian_filter(image[y0:y1, x0:x1], sigma, mode="nearest")
        return result
    return ndi.gaussian_filter(image, (sigma, sigma) + (0,) * (image.ndim - 2), mode="nearest")


def shift(mask, dx, dy):
    """Move a mask; out[y, x] = mask[y - dy, x - dx].

    Edge values are repeated, so a shape cut off by the canvas keeps going beyond it.
    """
    return ndi.shift(mask, (dy, dx), order=1, mode="nearest")


def mask_box(mask, padding=0, level=1e-4):
    """Bounding box (y0, y1, x0, x1) of the non-empty part of a mask, or None if empty.

    Most parts cover a small share of the canvas; working inside the box saves most of the time.
    """
    rows = np.flatnonzero(np.any(mask > level, axis=1))
    cols = np.flatnonzero(np.any(mask > level, axis=0))
    if rows.size == 0:
        return None
    height, width = mask.shape
    return (max(rows[0] - padding, 0), min(rows[-1] + 1 + padding, height),
            max(cols[0] - padding, 0), min(cols[-1] + 1 + padding, width))


def inflate(mask, bevel=None, smoothing=DEFAULT_SMOOTHING):
    """Height field of a mask puffed up with a quarter-circle edge profile.

    bevel: how far from the edge the surface keeps rising (pixels).
           None gives a fully rounded form (face, fruit, cloud);
           a small value gives a flat top with rounded edges (torso, slab).
    smoothing: blur as a fraction of the bevel radius; raise it (0.4+) for pointed
           shapes whose inflated ridge would otherwise show as a crease.
    """
    result = np.zeros(mask.shape, dtype=np.float32)
    tight = mask_box(mask, padding=2, level=INSIDE_LEVEL)
    if tight is None:
        return result
    y0, y1, x0, x1 = tight
    distance = ndi.distance_transform_edt(mask[y0:y1, x0:x1] > INSIDE_LEVEL)
    peak = float(distance.max())
    if peak <= 0:
        return result
    radius = peak if bevel is None else min(float(bevel), peak)
    rise = np.clip(distance / radius, 0.0, 1.0)
    height = radius * np.sqrt(1.0 - (1.0 - rise) ** 2)
    sigma = max(radius * smoothing, 1.0)
    margin = int(np.ceil(sigma * 3))
    # Edge padding: a shape cut off by the canvas keeps going past the frame.
    wide = np.pad(height, margin, mode="edge")
    blurred = ndi.gaussian_filter(wide, sigma, mode="nearest")
    # paste the blurred block back, clipped to the canvas
    by0, bx0 = y0 - margin, x0 - margin
    cy0, cx0 = max(by0, 0), max(bx0, 0)
    cy1, cx1 = min(by0 + blurred.shape[0], mask.shape[0]), min(bx0 + blurred.shape[1], mask.shape[1])
    result[cy0:cy1, cx0:cx1] = blurred[cy0 - by0:cy1 - by0, cx0 - bx0:cx1 - bx0]
    return result


def surface_normals(height, depth=1.0):
    """Unit normals of a height field; depth exaggerates (>1) or flattens (<1) the relief."""
    grad_y, grad_x = np.gradient(height)
    normal = np.stack([-grad_x * depth, -grad_y * depth, np.ones_like(height)], axis=-1)
    return normal / np.linalg.norm(normal, axis=-1, keepdims=True)


def lighting(mask, light=DEFAULT_LIGHT, bevel=None, depth=1.0, height=None):
    """Lambert term (-1..1) for a mask lit from direction `light` (x, y, z toward the light)."""
    if height is None:
        height = inflate(mask, bevel)
    light = np.asarray(light, dtype=np.float64)
    light = (light / np.linalg.norm(light)).astype(np.float32)
    lit = np.full(mask.shape, light[2], dtype=np.float32)         # flat ground faces the viewer
    box = mask_box(height, padding=2, level=0.0)
    if box is None:
        return lit
    y0, y1, x0, x1 = box
    lit[y0:y1, x0:x1] = surface_normals(height[y0:y1, x0:x1], depth) @ light
    return lit


def shadow_from_light(lit, threshold=0.25, softness=0.02):
    """Shadow coverage where the lambert term falls below threshold.

    softness near 0 gives the hard cel edge; 0.3 or more gives airbrushed shading.
    """
    return 1.0 - smoothstep(threshold - softness, threshold + softness, lit)


def cast_shadow(occluder, receiver, offset, softness=0.0):
    """Shadow that `occluder` throws onto `receiver`: the occluder mask slid along the light."""
    shadow = shift(occluder, offset[0], offset[1])
    if softness > 0:
        shadow = blur(shadow, softness)
    return np.clip(shadow, 0.0, 1.0) * receiver


def rim(mask, direction, width, softness=0.0):
    """Thin band along the edge of `mask` that faces `direction` (rim light, edge highlight)."""
    direction = np.asarray(direction, dtype=np.float64)
    direction = direction / max(np.linalg.norm(direction), 1e-9)
    inner = shift(mask, -direction[0] * width, -direction[1] * width)
    band = np.clip(mask - inner, 0.0, 1.0)
    return blur(band, softness) * mask if softness > 0 else band


EDGE_SUPERSAMPLE = 2          # distance transforms work on whole pixels; a finer grid smooths the line


def edge_band(mask, width, shade_side=(0.6, 0.7), contrast=0.5):
    """Outline coverage along the edge of a mask, heavier on the side facing `shade_side`.

    Use when a shape is a union of several parts (a body made of limbs): tracing each
    part would leave lines at every joint, tracing the union leaves one clean contour.
    """
    result = np.zeros(mask.shape, dtype=np.float32)
    box = mask_box(mask, padding=int(np.ceil(width * 2)) + 3, level=INSIDE_LEVEL)
    if box is None or width <= 0:
        return result
    y0, y1, x0, x1 = box
    zoom = EDGE_SUPERSAMPLE
    fine = ndi.zoom(mask[y0:y1, x0:x1], zoom, order=1)
    # Edge padding keeps a shape that runs off the canvas from getting a line along the frame.
    padded = np.pad(fine > INSIDE_LEVEL, 1, mode="edge")
    signed = (ndi.distance_transform_edt(~padded) - ndi.distance_transform_edt(padded))[1:-1, 1:-1]
    grad_y, grad_x = np.gradient(blur(fine, max(width * zoom, 3.0)))
    length = np.maximum(np.hypot(grad_x, grad_y), 1e-6)
    side = np.asarray(shade_side, dtype=np.float64)
    side = side / max(np.linalg.norm(side), 1e-9)
    facing = -(grad_x * side[0] + grad_y * side[1]) / length          # outward normal . shade side
    local_width = width * zoom * (1.0 + contrast * np.clip(facing, -1.0, 1.0))
    band = np.clip(local_width / 2 - np.abs(signed) + 0.5, 0.0, 1.0).astype(np.float32)
    rows, cols = (y1 - y0), (x1 - x0)
    band = band[:rows * zoom, :cols * zoom].reshape(rows, zoom, cols, zoom).mean(axis=(1, 3))
    result[y0:y1, x0:x1] = band
    return result


def melt(mask, radius):
    """Round off the notches and corners of a mask, as if its parts had fused.

    Use on a union of overlapping parts (limbs and trunk, petals, rocks) for an organic outline.
    """
    return smoothstep(0.42, 0.58, blur(mask, radius)).astype(np.float32)


def ground_shadow(mask, drop=0.04, squash=0.22, lean=0.5, softness=4.0, level=INSIDE_LEVEL, center_y=None):
    """Shadow an object throws on the table or floor it stands on, as a flattened ellipse at its base.

    drop: how far below the base the shadow's centre sits (share of the object's height).
    squash: shadow height as a share of the object's width. lean: sideways slide, in object half-widths
    (positive toward the screen right, for a light on the left).
    center_y: pixel row of the shadow's centre, when the caller knows where the object meets the ground.
    """
    result = np.zeros(mask.shape, dtype=np.float32)
    box = mask_box(mask, level=level)
    if box is None:
        return result
    y0, y1, x0, x1 = box
    half_w = (x1 - x0) / 2
    center_x = (x0 + x1) / 2 + lean * half_w
    if center_y is None:
        center_y = y1 - (y1 - y0) * 0.03 + drop * (y1 - y0)
    grid_y, grid_x = np.mgrid[0:mask.shape[0], 0:mask.shape[1]].astype(np.float32)
    distance = ((grid_x - center_x) / (half_w * 1.15)) ** 2 + ((grid_y - center_y) / max(half_w * squash, 1.0)) ** 2
    result = np.clip(1.6 - 1.6 * distance, 0.0, 1.0)
    return blur(result, softness)


def occlusion(occluder, receiver, radius):
    """Soft darkening on `receiver` near `occluder` (contact shadow, ambient occlusion)."""
    return np.clip(blur(occluder, radius), 0.0, 1.0) * receiver


def linear_ramp(shape, start, end):
    """0 at point `start`, 1 at point `end`, clamped; used for gradients and light falloff."""
    height, width = shape
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    axis = np.asarray(end, dtype=np.float32) - np.asarray(start, dtype=np.float32)
    along = (grid_x - start[0]) * axis[0] + (grid_y - start[1]) * axis[1]
    return np.clip(along / max(float(axis @ axis), 1e-6), 0.0, 1.0)


def radial_ramp(shape, center, radius):
    """0 at `center`, 1 at distance `radius`, clamped."""
    height, width = shape
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    distance = np.hypot(grid_x - center[0], grid_y - center[1])
    return np.clip(distance / max(radius, 1e-6), 0.0, 1.0)
