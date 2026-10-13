"""Rasterisation: turns curves into anti-aliased coverage masks (float32, 0..1)."""
import numpy as np
from PIL import Image, ImageDraw

from . import geometry as geo

SUPERSAMPLE = 4          # PIL draws aliased shapes, so draw large and shrink
BOX_PADDING = 2          # pixels of slack around a shape's bounding box
MIN_STROKE_WIDTH = 0.35  # thinner ribbons vanish between supersamples


def _bounding_box(points, shape, extra=0.0):
    height, width = shape
    x0 = int(max(np.floor(points[:, 0].min() - extra) - BOX_PADDING, 0))
    y0 = int(max(np.floor(points[:, 1].min() - extra) - BOX_PADDING, 0))
    x1 = int(min(np.ceil(points[:, 0].max() + extra) + BOX_PADDING, width))
    y1 = int(min(np.ceil(points[:, 1].max() + extra) + BOX_PADDING, height))
    return x0, y0, x1, y1


def _shrink(image, size):
    small = image.resize(size, Image.BOX)
    return np.asarray(small, dtype=np.float32) / 255.0


def fill_patch(polygon, shape):
    """Coverage of a closed polygon. Returns (patch, (x0, y0, x1, y1)) or (None, None)."""
    polygon = geo.as_points(polygon)
    x0, y0, x1, y1 = _bounding_box(polygon, shape)
    if x1 <= x0 or y1 <= y0:
        return None, None
    image = Image.new("L", ((x1 - x0) * SUPERSAMPLE, (y1 - y0) * SUPERSAMPLE), 0)
    local = (polygon - [x0, y0]) * SUPERSAMPLE
    ImageDraw.Draw(image).polygon([tuple(p) for p in local], fill=255)
    return _shrink(image, (x1 - x0, y1 - y0)), (x0, y0, x1, y1)


def stroke_patch(path, widths, shape):
    """Coverage of a variable-width stroke.

    Built from one quad per segment plus a disc per point, because a single
    ribbon polygon self-intersects on tight curves and leaves holes.
    """
    path = geo.as_points(path)
    widths = np.maximum(np.broadcast_to(np.asarray(widths, dtype=np.float64), (len(path),)), 0.0)
    x0, y0, x1, y1 = _bounding_box(path, shape, extra=float(widths.max()) / 2)
    if x1 <= x0 or y1 <= y0 or len(path) < 2:
        return None, None
    image = Image.new("L", ((x1 - x0) * SUPERSAMPLE, (y1 - y0) * SUPERSAMPLE), 0)
    draw = ImageDraw.Draw(image)
    local = (path - [x0, y0]) * SUPERSAMPLE
    half = widths * SUPERSAMPLE / 2
    normal = geo.normals(local)
    left, right = local + normal * half[:, None], local - normal * half[:, None]
    for i in range(len(local) - 1):
        if max(widths[i], widths[i + 1]) < MIN_STROKE_WIDTH:
            continue
        quad = [tuple(left[i]), tuple(left[i + 1]), tuple(right[i + 1]), tuple(right[i])]
        draw.polygon(quad, fill=255)
    for (cx, cy), radius, width in zip(local, half, widths):
        if width >= MIN_STROKE_WIDTH:
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=255)
    return _shrink(image, (x1 - x0, y1 - y0)), (x0, y0, x1, y1)


def to_full(patch, box, shape):
    full = np.zeros(shape, dtype=np.float32)
    if patch is not None:
        x0, y0, x1, y1 = box
        full[y0:y1, x0:x1] = patch
    return full


def fill_mask(polygon, shape):
    return to_full(*fill_patch(polygon, shape), shape)


def fill_many(polygons, shape):
    """Coverage of many small polygons at once (windows, flakes, tiles): one image instead of one mask each."""
    polygons = [geo.as_points(polygon) for polygon in polygons if len(polygon) >= 3]
    if not polygons:
        return np.zeros(shape, dtype=np.float32)
    x0, y0, x1, y1 = _bounding_box(np.vstack(polygons), shape)
    if x1 <= x0 or y1 <= y0:
        return np.zeros(shape, dtype=np.float32)
    image = Image.new("L", ((x1 - x0) * SUPERSAMPLE, (y1 - y0) * SUPERSAMPLE), 0)
    draw = ImageDraw.Draw(image)
    for polygon in polygons:
        draw.polygon([tuple(p) for p in (polygon - [x0, y0]) * SUPERSAMPLE], fill=255)
    return to_full(_shrink(image, (x1 - x0, y1 - y0)), (x0, y0, x1, y1), shape)


def stroke_mask(path, widths, shape):
    return to_full(*stroke_patch(path, widths, shape), shape)


def pressure(count, width, taper_in=0.25, taper_out=0.35, tip=0.08, power=0.8):
    """Width along a stroke: thin entry, full body, thin exit, like pen pressure.

    taper_in, taper_out: fraction of the stroke spent swelling and thinning.
    tip: width at the very ends as a fraction of the full width.
    """
    position = np.linspace(0.0, 1.0, count)
    swell = np.ones(count)
    if taper_in > 0:
        swell = np.minimum(swell, np.clip(position / taper_in, 0, 1) ** power)
    if taper_out > 0:
        swell = np.minimum(swell, np.clip((1 - position) / taper_out, 0, 1) ** power)
    return width * (tip + (1 - tip) * swell)
