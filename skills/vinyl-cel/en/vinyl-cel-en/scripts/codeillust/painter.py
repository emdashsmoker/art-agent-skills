"""The repeatable per-part recipe: flat colour -> shadow -> line.

One part = one closed shape with one material. Parts are painted back to
front, so a later part hides the lines of an earlier one exactly like stacked
layers in a paint program.
"""
import numpy as np

from . import shading
from .config import ShadeMode
from .geometry import Taper, ribbon, width_profile

ROI_PADDING_PX = 6
SOFT_SHADOW_RANGE = 0.55   # light span mapped to the full shadow in soft mode
SOFT_LIGHT_RANGE = 0.45
CEL_EDGE = 0.03            # smoothstep half-width of the cel border, in light units


class Painter:
    def __init__(self, canvas, style, light):
        self.canvas = canvas
        self.style = style
        light = np.asarray(light, dtype=np.float32)
        self.light = light / np.linalg.norm(light)

    # ---- parts -------------------------------------------------------------
    def part(self, name, mask, material, roundness=0.4, casts=(), tone=None, outline=True, volume=1.0,
             detail=None):
        """Paint one shape.

        casts: full-size masks of shadows falling on this part.
        tone: optional 0..1 field blending material.base toward material.accent.
        volume: 0 disables the bevel shadow (flat graphic parts such as irises).
        detail: optional 0..1 field that fades the form shadow and the line,
                used where a clump grows out of a larger mass and must not
                show a seam.
        """
        region = _bounding_region(mask, ROI_PADDING_PX)
        if region is None:
            return
        local_mask = mask[region]
        local_detail = 1.0 if detail is None else detail[region]
        shade = self._form_shadow(local_mask, roundness) * volume * local_detail
        light_amount = self._lit_edge(local_mask, roundness) * volume * local_detail
        for cast in casts:
            shade = np.maximum(shade, np.clip(cast[region], 0.0, 1.0))
        shade = shade * self.style.shadow_opacity

        color = np.broadcast_to(material.base, local_mask.shape + (3,)).astype(np.float32)
        if tone is not None and material.accent is not None:
            amount = tone[region][..., None]
            color = color * (1 - amount) + material.accent * amount
        color = color * (1 - shade[..., None]) + material.shadow * shade[..., None]
        if material.light is not None:
            color = color * (1 - light_amount[..., None]) + material.light * light_amount[..., None]

        if outline and self.style.line_width > 0:
            width_px = self.canvas.px(self.style.line_width)
            line = shading.outline_band(local_mask, width_px, self.light) * self.style.line_opacity * local_detail
            color = color * (1 - line[..., None]) + material.line * line[..., None]

        alpha = local_mask[..., None]
        self.canvas.rgb[region] = self.canvas.rgb[region] * (1 - alpha) + color * alpha
        self.canvas.remember(name, mask)

    def _form_shadow(self, local_mask, roundness):
        lambert = shading.bevel_light(local_mask, self.light, roundness)
        if self.style.shade_mode is ShadeMode.CEL:
            threshold = self.style.cel_threshold
            return 1.0 - shading.smoothstep(threshold - CEL_EDGE, threshold + CEL_EDGE, lambert)
        return shading.smoothstep(0.0, 1.0, (1.0 - lambert) / SOFT_SHADOW_RANGE)

    def _lit_edge(self, local_mask, roundness):
        if self.style.shade_mode is ShadeMode.CEL:
            return np.zeros_like(local_mask)
        lambert = shading.bevel_light(local_mask, self.light, roundness)
        return shading.smoothstep(0.0, 1.0, (lambert - 1.0) / SOFT_LIGHT_RANGE) * 0.8

    # ---- helpers the rig uses ----------------------------------------------
    def cast(self, occluder, receiver, offset_units):
        """Shadow mask of one part on another; sharp in cel styles, soft otherwise."""
        offset_px = (self.canvas.px(offset_units[0]), self.canvas.px(offset_units[1]))
        return shading.cast_shadow(occluder, receiver, offset_px, self.canvas.px(self.style.shadow_edge))

    def stroke(self, points, width, color, taper=Taper.BOTH, opacity=1.0, clip=None):
        """Tapered pen stroke along a polyline (design units)."""
        polygon = ribbon(points, width_profile(len(points), width, taper))
        mask = self.canvas.mask(polygon)
        if clip is not None:
            mask = mask * clip
        self.canvas.blend(mask, color, opacity)

    def fill(self, polygon, color, opacity=1.0, clip=None):
        """Flat shape without shading, for small graphic accents."""
        mask = self.canvas.mask(polygon)
        if clip is not None:
            mask = mask * clip
        self.canvas.blend(mask, color, opacity)
        return mask

    def glaze(self, mask, color, opacity):
        """Transparent colour wash (blush, lip tint, ambient shadow)."""
        self.canvas.blend(mask, color, opacity)


def _bounding_region(mask, padding):
    rows = np.flatnonzero(mask.max(axis=1) > 0)
    if rows.size == 0:
        return None
    cols = np.flatnonzero(mask.max(axis=0) > 0)
    top = max(0, rows[0] - padding)
    bottom = min(mask.shape[0], rows[-1] + 1 + padding)
    left = max(0, cols[0] - padding)
    right = min(mask.shape[1], cols[-1] + 1 + padding)
    return (slice(top, bottom), slice(left, right))
