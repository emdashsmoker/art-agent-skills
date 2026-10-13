"""Painting: a colour layer plus a separate line layer, filled and stroked through masks.

Keeping lines apart from colour lets each style decide what to do with them:
keep them crisp (anime), thin and tint them (illustration) or drop them (painterly).
"""
import numpy as np
from PIL import Image

from . import geometry as geo
from . import raster
from .color import rgb
from .shading import mask_box

STROKE_POINT_SPACING = 1.5   # pixels between resampled stroke points
MIN_STROKE_POINTS = 8


def blend(base, top, mode):
    if mode == "normal":
        return top
    if mode == "multiply":
        return base * top
    if mode == "screen":
        return 1.0 - (1.0 - base) * (1.0 - top)
    if mode == "add":
        return np.clip(base + top, 0.0, 1.0)
    if mode == "overlay":
        return np.where(base < 0.5, 2.0 * base * top, 1.0 - 2.0 * (1.0 - base) * (1.0 - top))
    if mode == "soft_light":
        return (1.0 - 2.0 * top) * base * base + 2.0 * top * base
    raise ValueError(f"unknown blend mode: {mode}")


def to_image(array):
    return Image.fromarray((np.clip(array, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))


class Painting:
    def __init__(self, width, height, background="#ffffff"):
        self.shape = (height, width)
        self.color = np.empty((height, width, 3), dtype=np.float32)
        self.color[:] = rgb(background)
        self.line_rgb = np.zeros((height, width, 3), dtype=np.float32)    # premultiplied
        self.line_alpha = np.zeros((height, width), dtype=np.float32)
        self.stages = {}     # name -> RGB snapshot, for the process sheet

    # ---- shapes ---------------------------------------------------------
    def mask(self, curve):
        """Coverage mask of a closed curve."""
        return raster.fill_mask(curve, self.shape)

    def fill(self, mask, color, opacity=1.0, mode="normal"):
        """Paint `color` (one colour or an HxWx3 image) through `mask` on the colour layer."""
        box = mask_box(mask)
        if box is None:
            return
        y0, y1, x0, x1 = box
        region = self.color[y0:y1, x0:x1]
        if isinstance(color, np.ndarray) and color.ndim == 3:
            top = color[y0:y1, x0:x1]
        else:
            top = np.broadcast_to(rgb(color), region.shape)
        alpha = (np.clip(mask[y0:y1, x0:x1], 0.0, 1.0) * opacity)[..., None]
        region += (blend(region, top, mode) - region) * alpha

    def part(self, mask, color):
        """Fill a new opaque part and hide any lines it covers, like stacking cut paper."""
        self.fill(mask, color)
        self.erase_lines(mask)

    def erase_lines(self, mask):
        keep = 1.0 - np.clip(mask, 0.0, 1.0)
        self.line_alpha *= keep
        self.line_rgb *= keep[..., None]

    # ---- strokes --------------------------------------------------------
    def stroke(self, path, width, color, taper=(0.25, 0.35), tip=0.08,
               opacity=1.0, layer="line", clip=None):
        """Draw a pen stroke. width: a number (tapered by `taper`) or one width per point.

        layer: "line" for outlines that styles may restyle or drop,
               "color" for marks that belong to the painting itself (lashes, lip line).
        clip: optional mask; the stroke only shows inside it (strands inside hair, folds inside cloth).
        """
        path = geo.as_points(path)
        if np.ndim(width) == 0:
            count = max(int(geo.path_length(path) / STROKE_POINT_SPACING), MIN_STROKE_POINTS)
            path = geo.resample(path, count)
            widths = raster.pressure(count, width, taper[0], taper[1], tip)
        else:
            widths = np.asarray(width, dtype=np.float64)
        patch, box = raster.stroke_patch(path, widths, self.shape)
        if patch is None:
            return
        x0, y0, x1, y1 = box
        alpha = patch * opacity
        if clip is not None:
            alpha = alpha * clip[y0:y1, x0:x1]
        ink = rgb(color)
        if layer == "color":
            region = self.color[y0:y1, x0:x1]
            region += (ink - region) * alpha[..., None]
            return
        keep = 1.0 - alpha
        self.line_rgb[y0:y1, x0:x1] = ink * alpha[..., None] + self.line_rgb[y0:y1, x0:x1] * keep[..., None]
        self.line_alpha[y0:y1, x0:x1] = alpha + self.line_alpha[y0:y1, x0:x1] * keep

    def outline(self, curve, width, color, shade_side=(0.6, 0.7), contrast=0.5,
                closed=True, opacity=1.0, layer="line"):
        """Contour line that grows heavier on the side facing `shade_side` (away from the light).

        Line weight variation is what separates inked drawings from vector outlines.
        """
        curve = geo.as_points(curve)
        path = np.vstack([curve, curve[:1]]) if closed else curve
        count = max(int(geo.path_length(path) / STROKE_POINT_SPACING), MIN_STROKE_POINTS)
        path = geo.resample(path, count)
        normal = geo.normals(path)
        # Pick the outward normal: signed area tells which way the contour winds.
        x, y = path[:, 0], path[:, 1]
        winding = np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
        outward = normal if winding < 0 else -normal
        side = np.asarray(shade_side, dtype=np.float64)
        side = side / max(np.linalg.norm(side), 1e-9)
        facing = np.clip(outward @ side, -1.0, 1.0)
        widths = width * (1.0 + contrast * facing)
        if not closed:
            widths = widths * raster.pressure(count, 1.0, 0.15, 0.2)
        self.stroke(path, widths, color, opacity=opacity, layer=layer)

    def outline_mask(self, mask, width, color, shade_side=(0.6, 0.7), contrast=0.5, opacity=1.0, keep=None):
        """Outline the edge of a mask (see shading.edge_band). keep: optional mask limiting where the line shows."""
        from .shading import edge_band
        band = edge_band(mask, width, shade_side, contrast) * opacity
        if keep is not None:
            band = band * keep
        box = mask_box(band)
        if box is None:
            return
        y0, y1, x0, x1 = box
        band, ink = band[y0:y1, x0:x1], rgb(color)
        rest = 1.0 - band
        self.line_rgb[y0:y1, x0:x1] = ink * band[..., None] + self.line_rgb[y0:y1, x0:x1] * rest[..., None]
        self.line_alpha[y0:y1, x0:x1] = band + self.line_alpha[y0:y1, x0:x1] * rest

    # ---- output ---------------------------------------------------------
    def flatten(self, line_opacity=1.0):
        alpha = (self.line_alpha * line_opacity)[..., None]
        return self.color * (1.0 - alpha) + self.line_rgb * line_opacity

    def line_art(self, paper="#ffffff"):
        """The line layer alone on plain paper, for checking the drawing before colour."""
        alpha = self.line_alpha[..., None]
        return rgb(paper) * (1.0 - alpha) + self.line_rgb

    def snapshot(self, name, line_opacity=1.0):
        """Record the current state as a named process stage."""
        self.stages[name] = self.flatten(line_opacity).copy()

    def save(self, path, image=None):
        to_image(self.flatten() if image is None else image).save(path)
