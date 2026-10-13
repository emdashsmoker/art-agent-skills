"""Relief renderer: parts are inflated into one shared height map and lit as a surface.

The flat part recipe (painter.part) shades each shape on its own, which is
right for graphic subjects such as hair clumps. Round subjects that touch and
overlap (limbs, fingers, fruit) need more: forms must merge at joints, cast
shadows on each other and show a line only where one form passes in front of
another. A height map gives all three from the same data.

Workflow: relief = Relief(canvas); relief.add(...) for every part, back to
front; relief.render(painter) once.
"""
import cv2
import numpy as np

from . import shading
from .config import ShadeMode
from .geometry import catmull_rom

NORMAL_SMOOTHING_PX = 1.5        # hides distance-transform facets
CEL_LIGHT_THRESHOLD = 0.34       # Lambert value where the cel shadow begins
CEL_EDGE = 0.035
SOFT_SHADOW_FLOOR = -0.05        # Lambert value mapped to full shadow in soft styles
SOFT_LIGHT_CEILING = 0.90        # Lambert value mapped to full base colour
HIGHLIGHT_START = 0.82           # Lambert value where the 'light' colour begins
SPECULAR_POWER = 48.0
CAST_STEPS = 36                  # samples along the ray toward the light
CAST_REACH_UNITS = 150.0         # how far a form can throw its shadow
CAST_SOFTNESS_PX = 2.5
CAST_SAMPLE_PX = 1.5             # target spacing of the shadow samples
CAST_STRENGTH_SOFT = 0.75
OCCLUSION_RADIUS_UNITS = 14.0    # crease darkening radius
OCCLUSION_STRENGTH = 0.9
OVERLAP_LINE_MARGIN_UNITS = (4.0, 9.0)   # how far one form must stand above another to earn a line
CREASE_RADIUS_UNITS = 2.2        # scale at which a valley between two forms is measured
CREASE_LINE_DEPTH = (1.2, 2.2)   # valley depth (pixels per unit radius) that earns a line
RIDGE_SMOOTHING = 0.20           # share of the form radius used to round the inflation ridge
ROI_PADDING_PX = 4
EDGE_EXTEND_PX = 6
FRONT = "front"                  # depth value: sit in front of whatever is underneath
FRONT_CLEARANCE_UNITS = 10.0


class Relief:
    def __init__(self, canvas):
        self.canvas = canvas
        shape = (canvas.height, canvas.width)
        self.height = np.zeros(shape, dtype=np.float32)   # pixels toward the viewer
        self.cover = np.zeros(shape, dtype=np.float32)
        self.base = np.zeros(shape + (3,), dtype=np.float32)
        self.shadow = np.zeros(shape + (3,), dtype=np.float32)
        self.light = np.zeros(shape + (3,), dtype=np.float32)
        self.line = np.zeros(shape + (3,), dtype=np.float32)
        self.gloss = np.zeros(shape, dtype=np.float32)
        self.overlap_edge = np.zeros(shape, dtype=np.float32)   # where one form passes in front of another
        self.quiet = np.zeros_like(self.overlap_edge)   # where no interior lines are drawn (closed gaps)
        self.owner = np.zeros(shape, dtype=np.int32)             # which named part is visible at each pixel
        self._owner_ids = {}
        # Depth maps from body3d stop abruptly at the silhouette. Extending the edge values
        # outward before taking slopes keeps the rim from reading as an embossed border.
        self.extend_edges = False
        # Pixels a smooth curved surface hides from itself are already dark from shading; a
        # small tolerance stops them flickering into speckled 'shadow acne' on round forms.
        self.cast_bias_px = 0.0

    # ---- building ------------------------------------------------------------
    def add(self, name, mask, material, thickness=1.0, depth=0.0, height=None, tone=None, gloss=0.0,
            drape=False, bridge=0.0, edge=True):
        """Add one part.

        thickness: 1.0 inflates the shape to a round cross-section; lower is flatter.
        depth: canvas units the whole part sits in front of the picture plane.
               Equal depths merge smoothly (joints); a larger depth overlaps (arm over torso).
               FRONT places the part just in front of everything under it.
        height: optional explicit height image in pixels (e.g. a lathe profile).
        tone: optional 0..1 field blending material.base toward material.accent.
        drape: the part follows whatever is already there (cloth on a body) and
               only replaces the material.
        bridge: canvas units of hollow a draped part spans instead of sinking into
                (taut cloth over a groove); 0 follows the surface exactly.
        edge: False for a part that grows out of what is under it (an arm at the
              shoulder), so no overlap line is drawn where it starts.
        """
        region = _bounding_region(mask, ROI_PADDING_PX)
        if region is None:
            return
        local = mask[region]
        if depth is FRONT:
            depth = float((self.height[region] * (local > 0.5)).max()) / self.canvas.px_per_unit + FRONT_CLEARANCE_UNITS
        if drape:
            under = self.height
            if bridge > 0:
                under = np.maximum(under, shading.blur(under, self.canvas.px(bridge)))
            surface = under[region] + self.canvas.px(depth)
        elif height is not None:
            surface = height[region] * thickness + self.canvas.px(depth)
        else:
            surface = inflate(local) * thickness + self.canvas.px(depth)
        previous = self.height[region]
        wins = (surface >= previous).astype(np.float32)
        alpha = local * wins
        alpha3 = alpha[..., None]
        if edge:
            self._record_overlap_edge(region, alpha, surface - previous, drape)
        else:
            self.overlap_edge[region] = self.overlap_edge[region] * (1 - alpha)

        self.height[region] = self.height[region] * (1 - alpha) + surface * alpha
        base = np.broadcast_to(material.base, local.shape + (3,)).astype(np.float32)
        if tone is not None and material.accent is not None:
            amount = tone[region][..., None]
            base = base * (1 - amount) + material.accent * amount
        self.base[region] = self.base[region] * (1 - alpha3) + base * alpha3
        self.shadow[region] = self.shadow[region] * (1 - alpha3) + material.shadow * alpha3
        light = material.light if material.light is not None else material.base
        self.light[region] = self.light[region] * (1 - alpha3) + light * alpha3
        self.line[region] = self.line[region] * (1 - alpha3) + material.line * alpha3
        self.gloss[region] = self.gloss[region] * (1 - alpha) + gloss * alpha
        self.cover[region] = np.maximum(self.cover[region], local)
        owner_id = self._owner_ids.setdefault(name, len(self._owner_ids) + 1)
        self.owner[region] = np.where(alpha > 0.5, owner_id, self.owner[region])

        full_alpha = np.zeros_like(mask)
        full_alpha[region] = alpha
        self.canvas.remember(name, full_alpha)

    def _record_overlap_edge(self, region, alpha, margin, drape):
        """Remember the rim of the newly visible area where it stands clear of what
        is behind it. Forms that merge at equal height (joints) leave no rim."""
        won = (alpha > 0.5).astype(np.uint8)
        kernel = np.ones((3, 3), dtype=np.uint8)
        rim = (won - cv2.erode(won, kernel)).astype(np.float32)
        low, high = (self.canvas.px(value) for value in OVERLAP_LINE_MARGIN_UNITS)
        # Judge the margin a pixel inside the rim: right at the edge an inflated form has no height yet.
        inner_margin = cv2.dilate(np.where(won > 0, margin, -1e6).astype(np.float32), kernel, iterations=2)
        clear = np.ones_like(margin) if drape else shading.smoothstep(low, high, inner_margin)
        over_existing = (self.cover[region] > 0.5).astype(np.float32)
        self.overlap_edge[region] = self.overlap_edge[region] * (1 - alpha) + rim * clear * over_existing

    def visible(self, *names):
        """Mask of the pixels where one of the named parts is the visible surface."""
        ids = [self._owner_ids[name] for name in names if name in self._owner_ids]
        return np.isin(self.owner, ids).astype(np.float32)

    def tint(self, mask, color, opacity, only=None):
        """Transparent colour wash on the surface (blush, painted bands, shadows on cloth).
        only: names of the parts that may receive it."""
        if only is not None:
            mask = mask * self.visible(*only)
        alpha = (np.clip(mask, 0.0, 1.0) * opacity)[..., None]
        color = np.asarray(color, dtype=np.float32)
        self.base = (self.base * (1 - alpha) + color * alpha).astype(np.float32)
        self.shadow = (self.shadow * (1 - alpha * 0.6) + color * 0.75 * alpha * 0.6).astype(np.float32)

    def bump(self, mask, thickness=1.0, fade=None):
        """Raise a rounded swelling on the existing surface without changing its material
        (muscle, breast, knuckle, cheek). fade is an optional 0..1 field that softens
        one side so the swelling grows out of the surface instead of sitting on it."""
        swelling = inflate(mask) * thickness
        if fade is not None:
            swelling = swelling * fade
        self.height = (self.height + swelling * (self.cover > 0.5)).astype(np.float32)

    def swell(self, soft_mask, height_units):
        """Raise the surface by a soft-edged amount (use canvas.soft_ellipse). Unlike bump
        it leaves no rim, so it suits forms that have no visible boundary: a belly,
        a shoulder cap, a kneecap."""
        lift = soft_mask * self.canvas.px(height_units) * (self.cover > 0.5)
        self.height = (self.height + lift).astype(np.float32)

    def groove(self, mask, depth_px):
        """Press a soft dent into the surface (spine furrow, navel, apple dimple)."""
        self.height = (self.height - mask * depth_px * (self.cover > 0)).astype(np.float32)

    # ---- lighting --------------------------------------------------------------
    def render(self, painter, cast_shadows=True, lines=True):
        canvas, style, light = self.canvas, painter.style, painter.light
        region = _bounding_region(self.cover, ROI_PADDING_PX + int(canvas.px(4)))
        if region is None:
            return
        cover = self.cover[region]
        height = self.height[region]
        if self.extend_edges:
            height = _extend_outward(height, cover > 0.5, EDGE_EXTEND_PX)
        height = shading.blur(height, NORMAL_SMOOTHING_PX)
        slope_x = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0
        slope_y = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0
        length = np.sqrt(slope_x**2 + slope_y**2 + 1.0)
        lambert = (-slope_x * light[0] - slope_y * light[1] + light[2]) / length

        cast = self._cast_shadow(height, light) if cast_shadows else np.zeros_like(height)
        occlusion = self._occlusion(height) * cover

        base, shadow = self.base[region], self.shadow[region]
        if style.shade_mode is ShadeMode.CEL:
            lit = shading.smoothstep(CEL_LIGHT_THRESHOLD - CEL_EDGE, CEL_LIGHT_THRESHOLD + CEL_EDGE, lambert)
            lit = lit * (1 - shading.smoothstep(0.3, 0.7, cast))
            shade = (1 - lit) * style.shadow_opacity
            color = base * (1 - shade[..., None]) + shadow * shade[..., None]
        else:
            lit = shading.smoothstep(SOFT_SHADOW_FLOOR, SOFT_LIGHT_CEILING, lambert)
            lit = lit * (1 - cast * CAST_STRENGTH_SOFT) * (1 - occlusion * OCCLUSION_STRENGTH)
            shade = (1 - lit) * style.shadow_opacity
            color = base * (1 - shade[..., None]) + shadow * shade[..., None]
            glow = shading.smoothstep(HIGHLIGHT_START, 1.0, lambert) * (1 - cast)
            color = color * (1 - glow[..., None] * 0.7) + self.light[region] * glow[..., None] * 0.7

        half = np.array([light[0], light[1], light[2] + 1.0], dtype=np.float32)
        half /= np.linalg.norm(half)
        facing = np.clip((-slope_x * half[0] - slope_y * half[1] + half[2]) / length, 0.0, 1.0)
        specular = facing**SPECULAR_POWER * self.gloss[region] * (1 - cast)
        if style.shade_mode is ShadeMode.CEL:
            specular = shading.smoothstep(0.35, 0.45, specular) * (self.gloss[region] > 0)
        color = color + (1 - color) * specular[..., None]

        if lines and style.line_width > 0:
            line = self._lines(region, height, cover, canvas.px(style.line_width), light)
            line = line * style.line_opacity
            color = color * (1 - line[..., None]) + self.line[region] * line[..., None]

        alpha = cover[..., None]
        canvas.rgb[region] = (canvas.rgb[region] * (1 - alpha) + color * alpha).astype(np.float32)

    def _cast_shadow(self, height, light):
        """March from every pixel toward the light; a higher surface on the way blocks it."""
        planar = np.asarray(light[:2], dtype=np.float32)
        planar_length = float(np.linalg.norm(planar)) + 1e-9
        direction = planar / planar_length
        rise_per_px = float(light[2]) / planar_length
        reach = self.canvas.px(CAST_REACH_UNITS)
        blocked = np.zeros_like(height)
        size = (height.shape[1], height.shape[0])
        # Enough samples that neighbouring ones are about a pixel and a half apart even far out; sparse
        # samples copy a form's edge several times over and the shadow border turns into a staircase.
        steps = max(CAST_STEPS, int(np.ceil(reach / CAST_SAMPLE_PX)))
        for step in range(1, steps + 1):
            distance = reach * (step / steps) ** 1.2
            shift = np.float32([[1, 0, -direction[0] * distance], [0, 1, -direction[1] * distance]])
            toward_light = cv2.warpAffine(height, shift, size)
            excess = toward_light - (height + distance * rise_per_px) - self.cast_bias_px
            blocked = np.maximum(blocked, np.clip(excess / CAST_SOFTNESS_PX, 0.0, 1.0))
        return blocked

    def _occlusion(self, height):
        radius = self.canvas.px(OCCLUSION_RADIUS_UNITS)
        surrounding = shading.blur(height, radius)
        return np.clip((surrounding - height) / radius, 0.0, 1.0)

    def _lines(self, region, height, cover, width_px, light):
        silhouette = shading.outline_band(cover, width_px, light)
        radius = self.canvas.px(CREASE_RADIUS_UNITS)
        valley = (shading.blur(height, radius) - height) / radius
        crease = shading.smoothstep(CREASE_LINE_DEPTH[0], CREASE_LINE_DEPTH[1], valley)
        kernel = np.ones((3, 3), dtype=np.uint8)
        inside = cv2.erode((cover > 0.5).astype(np.uint8), kernel, iterations=max(1, int(width_px) + 1))
        interior = np.maximum(self.overlap_edge[region], crease) * inside * (1.0 - self.quiet[region])
        spread = max(1, int(round(width_px * 0.5)))
        brush = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * spread + 1, 2 * spread + 1))
        interior = shading.blur(cv2.dilate(interior, brush), 0.6)
        return np.clip(np.maximum(silhouette, interior), 0.0, 1.0)


def _extend_outward(height, inside, steps):
    """Copy the outermost inside values a few pixels outward (nearest-value extrapolation)."""
    filled, known = height.copy(), inside.astype(np.uint8)
    kernel = np.ones((3, 3), dtype=np.uint8)
    for _ in range(steps):
        sums = cv2.boxFilter(filled * known, -1, (3, 3), normalize=False)
        counts = cv2.boxFilter(known.astype(np.float32), -1, (3, 3), normalize=False)
        grown = cv2.dilate(known, kernel)
        new = (grown > 0) & (known == 0)
        filled = np.where(new, sums / np.maximum(counts, 1.0), filled).astype(np.float32)
        known = grown
    return filled


def inflate(mask):
    """Height (pixels) of a shape blown up like a balloon: a disc becomes a hemisphere.

    The distance to the edge is smoothed before the round profile is applied so
    the medial ridge of non-circular shapes does not show as a crease.
    """
    distance = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    radius = float(distance.max())
    if radius <= 0.0:
        return np.zeros_like(mask)
    distance = shading.blur(distance, max(0.8, radius * RIDGE_SMOOTHING)) * (mask > 0.5)
    distance = np.minimum(distance, radius)
    return np.sqrt(np.clip(2 * radius * distance - distance * distance, 0.0, None)).astype(np.float32)


def lathe_height(canvas, axis_x, top_y, bottom_y, radius_at, base_roundness=0.22, top_roundness=0.0):
    """Height image of a surface of revolution with a vertical axis (bottles, vases, pears).

    radius_at(t) returns the radius in canvas units for t in 0..1 from top to bottom.
    base_roundness / top_roundness close the ends with an elliptical arc: 0.2 is a
    flat foot or rim seen from slightly above, 1.0 is a fully round end.
    Returns (height_px, mask).
    """
    xs, ys = canvas.grid()
    t = (ys - top_y) / (bottom_y - top_y)
    foot = float(radius_at(np.array([1.0]))[0])
    lip = float(radius_at(np.array([0.0]))[0])
    below = np.clip((ys - bottom_y) / (foot * base_roundness + 1e-9), 0.0, 1.0)
    above = np.clip((top_y - ys) / (lip * top_roundness + 1e-9), 0.0, 1.0)
    body = radius_at(np.clip(t, 0.0, 1.0))
    radius = np.where(t < 0, lip * np.sqrt(1 - above**2), np.where(t <= 1, body, foot * np.sqrt(1 - below**2)))
    radius = radius.astype(np.float32)
    offset = xs - axis_x
    height = np.sqrt(np.clip(radius**2 - offset**2, 0.0, None)) * canvas.px_per_unit
    edge = np.clip((radius - np.abs(offset)) * canvas.px_per_unit + 0.5, 0.0, 1.0)
    return height.astype(np.float32), (edge * (radius > 0)).astype(np.float32)


def profile(points):
    """Radius function for lathe_height from (t, radius) control points on a smooth curve."""
    curve = catmull_rom(points, samples=24)
    order = np.argsort(curve[:, 0])
    ts, radii = curve[order, 0], np.clip(curve[order, 1], 0.0, None)

    def radius_at(t):
        return np.interp(np.asarray(t, dtype=np.float64), ts, radii)

    return radius_at


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
