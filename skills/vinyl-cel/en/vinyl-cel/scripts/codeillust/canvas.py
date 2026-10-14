"""Raster canvas: turns design-unit shapes into anti-aliased masks and keeps the image.

Masks are float32 images in 0..1. Working with masks (instead of drawing
pixels directly) is what lets later stages derive shadows, outlines and
highlights from the same shape, the way an artist reuses a selection.
"""
import cv2
import numpy as np

SUBPIXEL_SHIFT = 4  # OpenCV fixed-point bits; keeps curve edges smooth
SUBPIXEL_FACTOR = 1 << SUBPIXEL_SHIFT


SOFT_REACH = 2.7    # radii beyond which a soft ellipse is below 1e-5 and is left at zero

class Canvas:
    def __init__(self, units_width, units_height, px_per_unit, seed):
        self.px_per_unit = float(px_per_unit)
        self.units_width = units_width
        self.units_height = units_height
        self.width = int(round(units_width * px_per_unit))
        self.height = int(round(units_height * px_per_unit))
        self.rgb = np.ones((self.height, self.width, 3), dtype=np.float32)
        self.parts = {}  # name -> mask, kept for shadows and finishing passes
        self.rng = np.random.default_rng(seed)
        self._grid = None
        # Optional 0..1 map of where fine brushwork is wanted in painterly renders
        # (scenes without a figure set this; figures are detected from their parts).
        self.importance = None
        # Finishing passes shade the whole subject from light side to dark side.
        # Scenes with several separate subjects (a study sheet) switch this off.
        self.shade_subject_as_one = True
        # Drawn over the finished style (before a colour grade): weather and other effects in front of
        # the lens that brushwork and line passes must not touch. Each is a function(canvas).
        self.overlays = []

    def px(self, units):
        return units * self.px_per_unit

    def mask(self, *polygons):
        """Union of closed polygons as an anti-aliased coverage mask."""
        buffer = np.zeros((self.height, self.width), dtype=np.uint8)
        for polygon in polygons:
            points = np.round(np.asarray(polygon) * self.px_per_unit * SUBPIXEL_FACTOR).astype(np.int32)
            cv2.fillPoly(buffer, [points], 255, lineType=cv2.LINE_AA, shift=SUBPIXEL_SHIFT)
        return buffer.astype(np.float32) / 255.0

    def blend(self, mask, color, opacity=1.0):
        """Normal-mode layer composite. color is an RGB triple or an HxWx3 image.
        Only the bounding box of the mask is touched: strokes and face details cover a few
        hundred pixels, and compositing the whole canvas for each made figures slow."""
        mask = np.asarray(mask, dtype=np.float32)
        rows = np.flatnonzero(mask.any(axis=1))
        if rows.size == 0 or opacity == 0:
            return
        cols = np.flatnonzero(mask.any(axis=0))
        box = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
        color = np.asarray(color, dtype=np.float32)
        if color.ndim == 3:
            color = color[box]
        alpha = (mask[box] * opacity)[..., None]
        if not self.rgb.flags.writeable or self.rgb.dtype != np.float32:
            self.rgb = self.rgb.astype(np.float32)              # keep one dtype for OpenCV
        self.rgb[box] = self.rgb[box] * (1 - alpha) + color * alpha

    def remember(self, name, mask):
        """Accumulate a named part mask (several shapes may share a name)."""
        previous = self.parts.get(name)
        self.parts[name] = mask.copy() if previous is None else np.maximum(previous, mask)

    def part(self, name):
        return self.parts.get(name, np.zeros((self.height, self.width), dtype=np.float32))

    def grid(self):
        """Pixel-centre coordinates in design units, for gradients and soft shapes."""
        if self._grid is None:
            ys, xs = np.mgrid[0:self.height, 0:self.width].astype(np.float32)
            self._grid = ((xs + 0.5) / self.px_per_unit, (ys + 0.5) / self.px_per_unit)
        return self._grid

    def soft_ellipse(self, center, radius_x, radius_y, rotation=0.0):
        """Gaussian blob, for blush and glow where a hard edge would look pasted on.
        Evaluated only where it is above about 1e-5 (SOFT_REACH radii); zero beyond."""
        xs, ys = self.grid()
        reach = SOFT_REACH * max(radius_x, radius_y)
        box = self.box_around(center, reach)
        result = np.zeros((self.height, self.width), dtype=np.float32)
        if box is None:
            return result
        dx, dy = xs[box] - center[0], ys[box] - center[1]
        cos_r, sin_r = np.cos(rotation), np.sin(rotation)
        u = (dx * cos_r + dy * sin_r) / radius_x
        v = (-dx * sin_r + dy * cos_r) / radius_y
        result[box] = np.exp(-(u * u + v * v) * 1.6)
        return result

    def box_around(self, center, reach_units):
        """Pixel slices of the square of half size reach_units round a point, clipped to the canvas."""
        x0 = int(np.floor(self.px(center[0] - reach_units)))
        x1 = int(np.ceil(self.px(center[0] + reach_units))) + 1
        y0 = int(np.floor(self.px(center[1] - reach_units)))
        y1 = int(np.ceil(self.px(center[1] + reach_units))) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, self.width), min(y1, self.height)
        if x0 >= x1 or y0 >= y1:
            return None
        return slice(y0, y1), slice(x0, x1)

    def noise(self, cell_units, octaves=3):
        """Smooth value noise in 0..1. cell_units is the size of the largest blobs."""
        total = np.zeros((self.height, self.width), dtype=np.float32)
        weight_sum = 0.0
        for octave in range(octaves):
            cell_px = max(2.0, self.px(cell_units) / (2**octave))
            grid_h = max(2, int(self.height / cell_px) + 2)
            grid_w = max(2, int(self.width / cell_px) + 2)
            coarse = self.rng.random((grid_h, grid_w)).astype(np.float32)
            weight = 0.5**octave
            total += cv2.resize(coarse, (self.width, self.height), interpolation=cv2.INTER_CUBIC) * weight
            weight_sum += weight
        return np.clip(total / weight_sum, 0.0, 1.0)

    def to_uint8(self):
        return (np.clip(self.rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)

    def save(self, path, output_scale=1.0):
        image = cv2.cvtColor(self.to_uint8(), cv2.COLOR_RGB2BGR)
        if output_scale != 1.0:
            size = (int(round(self.width * output_scale)), int(round(self.height * output_scale)))
            image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        if not cv2.imwrite(str(path), image):
            raise IOError(f"could not write image: {path}")
