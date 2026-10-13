"""Canvas: the core of the drawing engine that turns paths into masks and lays down color.

Coordinates are logical coordinates as in SVG (top-left origin, y down), and changing scale alone changes the
resolution.
The intended workflow checks drafts quickly at a low scale and raises the scale only for the final render.
"""
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from . import color as colors
from . import config, geometry, noise


# Blur size ratio and slope factor of the mask in the solid approximation (form_shadow, form_light).
INFLATE_SIGMA_RATIOS = (0.12, 0.35, 0.8)
INFLATE_STEEPNESS = 1.1
# For the solid approximation, the shape is downscaled until its half-thickness is this many pixels.
INFLATE_WORK_RADIUS_PX = 20.0
# Screen-normal component of the light vector. Smaller values give straighter terminators, larger values bring
# the light from the front.
LIGHT_DEPTH_SHADOW = 0.3
LIGHT_DEPTH_HIGHLIGHT = 1.3
# Edge wobble factor. Above 0.84, dots appear in empty space outside the shape.
ROUGHEN_STRENGTH = 0.8


class Blend(Enum):
    """How a color combines with the base."""
    NORMAL = "normal"      # paint over
    MULTIPLY = "multiply"  # shadows, watercolor glazing
    SCREEN = "screen"      # light, haze
    ADD = "add"            # strong glow


def _blend_colors(backdrop, source, blend):
    if blend is Blend.NORMAL:
        return source
    if blend is Blend.MULTIPLY:
        return backdrop * source
    if blend is Blend.SCREEN:
        return 1.0 - (1.0 - backdrop) * (1.0 - source)
    if blend is Blend.ADD:
        return np.minimum(backdrop + source, 1.0)
    raise ValueError(f"unsupported blend mode: {blend!r}")


def _smoothstep(edge_low, edge_high, value):
    t = np.clip((value - edge_low) / max(edge_high - edge_low, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


@dataclass
class Shape:
    """A mask piece. Stores only its bounding box area to save memory and time."""
    mask: np.ndarray
    x0: int
    y0: int

    @property
    def x1(self):
        return self.x0 + self.mask.shape[1]

    @property
    def y1(self):
        return self.y0 + self.mask.shape[0]

    def placed(self, x0, y0, x1, y1):
        """Place this mask in an array of the given box size. Zero outside the box."""
        out = np.zeros((max(y1 - y0, 0), max(x1 - x0, 0)), np.float32)
        ix0, iy0 = max(x0, self.x0), max(y0, self.y0)
        ix1, iy1 = min(x1, self.x1), min(y1, self.y1)
        if ix1 > ix0 and iy1 > iy0:
            out[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = \
                self.mask[iy0 - self.y0:iy1 - self.y0, ix0 - self.x0:ix1 - self.x0]
        return out

    def _like_self(self, other):
        return other.placed(self.x0, self.y0, self.x1, self.y1)

    def __and__(self, other):
        """Intersection. Used to keep shadows or patterns inside a parent shape."""
        return Shape(self.mask * self._like_self(other), self.x0, self.y0)

    def __sub__(self, other):
        """Difference."""
        return Shape(self.mask * (1.0 - self._like_self(other)), self.x0, self.y0)

    def __or__(self, other):
        """Union."""
        x0, y0 = min(self.x0, other.x0), min(self.y0, other.y0)
        x1, y1 = max(self.x1, other.x1), max(self.y1, other.y1)
        return Shape(np.maximum(self.placed(x0, y0, x1, y1), other.placed(x0, y0, x1, y1)), x0, y0)

    def __mul__(self, factor):
        """Adjust mask strength."""
        return Shape(self.mask * float(factor), self.x0, self.y0)

    @property
    def is_empty(self):
        return self.mask.size == 0 or float(self.mask.max()) <= 0.0


class Linear:
    """Linear gradient paint. stops is a list of colors or a list of (position 0-1, color)."""

    def __init__(self, stops, start, end):
        self.positions, self.colors = _normalize_stops(stops)
        self.start = np.asarray(start, np.float64)
        self.end = np.asarray(end, np.float64)

    def sample(self, xs, ys):
        axis = self.end - self.start
        t = ((xs - self.start[0]) * axis[0] + (ys - self.start[1]) * axis[1]) / max(axis @ axis, 1e-9)
        return _lookup_stops(t, self.positions, self.colors)


class Radial:
    """Radial gradient paint. The center is position 0 and the radius distance is position 1."""

    def __init__(self, stops, center, radius):
        self.positions, self.colors = _normalize_stops(stops)
        self.center = np.asarray(center, np.float64)
        self.radius = float(radius)

    def sample(self, xs, ys):
        t = np.hypot(xs - self.center[0], ys - self.center[1]) / max(self.radius, 1e-9)
        return _lookup_stops(t, self.positions, self.colors)


def _normalize_stops(stops):
    stops = list(stops)
    # A color tuple has length 3, so a tuple of length 2 is recognized as a (position, color) pair.
    has_positions = all(isinstance(stop, (tuple, list)) and len(stop) == 2 for stop in stops)
    if has_positions:
        positions = np.array([position for position, _ in stops], np.float64)
        palette = np.stack([colors.rgb(value) for _, value in stops])
    else:
        positions = np.linspace(0.0, 1.0, len(stops))
        palette = np.stack([colors.rgb(value) for value in stops])
    return positions, palette


def _lookup_stops(t, positions, palette):
    t = np.clip(t, 0.0, 1.0)
    return np.stack([np.interp(t, positions, palette[:, channel]) for channel in range(3)], axis=-1).astype(np.float32)


class Canvas:
    """RGBA working surface. With background None it starts transparent and can be placed on another canvas."""

    def __init__(self, width, height, scale=1.0, background="#ffffff", seed=config.DEFAULT_SEED):
        self.width, self.height, self.scale = float(width), float(height), float(scale)
        self.px_w = int(round(width * scale))
        self.px_h = int(round(height * scale))
        self.rgb = np.zeros((self.px_h, self.px_w, 3), np.float32)
        self.alpha = np.zeros((self.px_h, self.px_w), np.float32)
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self._seed_counter = 0
        # Brushstroke direction (radians). Where it is NaN, the style pass picks the direction itself.
        self.flow = np.full((self.px_h, self.px_w), np.nan, np.float32)
        if background is not None:
            self.rgb[:] = colors.rgb(background)
            self.alpha[:] = 1.0

    @classmethod
    def from_image(cls, image, width, height, seed=config.DEFAULT_SEED):
        """Constructor for painting further on top of an image that went through a style pass."""
        canvas = cls(width, height, scale=image.shape[1] / width, background=None, seed=seed)
        canvas.rgb[:] = image[: canvas.px_h, : canvas.px_w, :3]
        canvas.alpha[:] = 1.0
        return canvas

    def next_seed(self):
        """A seed that differs per call yet stays the same between runs. Guarantees reproducible results."""
        self._seed_counter += 1
        return self.seed * 1000 + self._seed_counter

    # ---------- shapes ----------

    def shape(self, *paths, soft=0.0):
        """Convert paths to a mask. Where paths overlap, the even-odd rule cuts holes.

        soft is the edge blur (logical units), used for smoke, light and bleeds.
        """
        pixel_paths = [np.asarray(path, np.float64) * self.scale for path in paths]
        sigma = soft * self.scale
        padding = config.RASTER_PADDING_PX + int(np.ceil(sigma * config.BLUR_PADDING_SIGMAS))
        stacked = np.vstack(pixel_paths)
        x0 = max(int(np.floor(stacked[:, 0].min())) - padding, 0)
        y0 = max(int(np.floor(stacked[:, 1].min())) - padding, 0)
        x1 = min(int(np.ceil(stacked[:, 0].max())) + padding + 1, self.px_w)
        y1 = min(int(np.ceil(stacked[:, 1].max())) + padding + 1, self.px_h)
        if x1 <= x0 or y1 <= y0:
            return Shape(np.zeros((0, 0), np.float32), 0, 0)

        # The built-in antialiasing of cv2.fillPoly inflates outlines by about 0.6px, which doubles the width
        # of thin lines.
        # Filling at a larger size and reducing by area averaging gives a mask with exact pixel coverage.
        oversample = config.RASTER_OVERSAMPLE
        factor = 1 << config.RASTER_SHIFT_BITS
        fixed = [np.round(((path - (x0, y0) + 0.5) * oversample - 0.5) * factor).astype(np.int32)
                 for path in pixel_paths]
        raster = np.zeros(((y1 - y0) * oversample, (x1 - x0) * oversample), np.uint8)
        cv2.fillPoly(raster, fixed, 255, lineType=cv2.LINE_8, shift=config.RASTER_SHIFT_BITS)
        mask = cv2.resize(raster, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        if sigma > 0.0:
            mask = cv2.GaussianBlur(mask, (0, 0), sigma)
        return Shape(mask, x0, y0)

    def full(self):
        """A shape that covers the whole canvas."""
        return Shape(np.ones((self.px_h, self.px_w), np.float32), 0, 0)

    def soften(self, shape, amount):
        """Blur the shape edges. Keeps room for the spread unless the box touches the frame edge."""
        sigma = amount * self.scale
        pad = int(np.ceil(sigma * config.BLUR_PADDING_SIGMAS))
        x0, y0 = max(shape.x0 - pad, 0), max(shape.y0 - pad, 0)
        x1, y1 = min(shape.x1 + pad, self.px_w), min(shape.y1 + pad, self.px_h)
        return Shape(cv2.GaussianBlur(shape.placed(x0, y0, x1, y1), (0, 0), sigma), x0, y0)

    def roughen(self, shape, amount=3.0, grain=12.0):
        """Wobble the edges irregularly. Expresses dry brush, torn paper and water-bleed borders.

        amount is the wobble width and grain is the wobble pattern size (both in logical units).
        """
        soft = self.soften(shape, amount)
        wobble = noise.fbm(soft.mask.shape, max(grain * self.scale, 2.0), self.next_seed(), octaves=3)
        return Shape(_smoothstep(0.42, 0.58, soft.mask + (wobble - 0.5) * ROUGHEN_STRENGTH), soft.x0, soft.y0)

    def contour(self, shape, width):
        """A band of width thickness inside the outer contour of the shape. Used to outline a whole silhouette.

        edge_light picks the contour on one side, and contour picks it on all sides.
        """
        # Parts cut off by the frame (feet in a knee-up composition and so on) are empty shapes, and OpenCV
        # erosion rejects empty arrays.
        if shape.mask.size == 0:
            return shape
        radius = max(int(round(width * self.scale)), 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
        return Shape(np.clip(shape.mask - cv2.erode(shape.mask, kernel), 0.0, 1.0), shape.x0, shape.y0)

    def mottle(self, shape, grain=60.0, coverage=0.5, soft=0.15, octaves=4):
        """Keep a mottled pattern inside the shape. Used for cloud texture, foliage masses and color variation.

        coverage is the remaining area ratio, soft is the softness of the blotch edges.
        """
        pattern = noise.fbm(shape.mask.shape, max(grain * self.scale, 2.0), self.next_seed(), octaves=octaves)
        threshold = 1.0 - coverage
        return Shape(shape.mask * _smoothstep(threshold - soft, threshold + soft, pattern), shape.x0, shape.y0)

    # ---------- solids ----------

    def _lambert(self, shape, light, roundness, light_depth):
        """Inflate a 2D shape into a virtual solid and find its angle to the light (Johnston 2002, Lumo).

        An approximation that gives the terminator of round forms without building a 3D model.
        """
        solid = (shape.mask > 0.5).astype(np.float32)
        binary = np.pad(solid.astype(np.uint8), 1)
        thickness = float(cv2.distanceTransform(binary, cv2.DIST_L2, 5).max())
        radius = max(thickness * roundness, 1.0)
        # Shading changes slowly, so computing it on a downscaled mask gives the same result.
        # Blurring a large shape at full resolution costs work that grows with the square of the radius.
        shrink = max(radius / INFLATE_WORK_RADIUS_PX, 1.0)
        small_size = (max(int(solid.shape[1] / shrink), 2), max(int(solid.shape[0] / shrink), 2))
        small = cv2.resize(solid, small_size, interpolation=cv2.INTER_AREA)
        small_radius = radius / shrink
        # Blurring the mask at several sizes and adding them gives a pillow-shaped height that is steep at the
        # edges and gentle in the middle.
        # Using the distance transform directly as height shows ridges as creases in the shading, so this
        # method was chosen.
        pad = int(np.ceil(small_radius * INFLATE_SIGMA_RATIOS[-1] * config.BLUR_PADDING_SIGMAS))
        padded = np.pad(small, pad)
        height = sum(cv2.GaussianBlur(padded, (0, 0), max(small_radius * ratio, 0.5))
                     for ratio in INFLATE_SIGMA_RATIOS)
        height = height[pad:pad + small.shape[0], pad:pad + small.shape[1]] * small_radius * INFLATE_STEEPNESS
        grad_y, grad_x = np.gradient(height)
        normal = np.stack([-grad_x, -grad_y, np.ones_like(height)], axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        direction = np.array([light[0], light[1], light_depth], np.float64)
        direction /= np.linalg.norm(direction)
        lambert = (normal @ direction).astype(np.float32)
        return cv2.resize(lambert, (solid.shape[1], solid.shape[0]), interpolation=cv2.INTER_CUBIC)

    def form_shadow(self, shape, light=(-0.6, -0.8), amount=0.4, soft=0.0, roundness=1.0):
        """A shadow shape cut from the side of the shape away from the light, covering the amount fraction.

        light is the direction of the light ((-1, -1) for a top-left light source).
        soft 0 gives a crisp cel-animation border, and higher values give a soft painterly border.
        """
        return self._form_band(shape, light, amount, soft, roundness, lit_side=False)

    def form_light(self, shape, light=(-0.6, -0.8), amount=0.15, soft=0.0, roundness=1.0):
        """A highlight shape cut from the side of the shape that gets the most light, covering the amount fraction."""
        return self._form_band(shape, light, amount, soft, roundness, lit_side=True)

    def edge_light(self, shape, light=(-0.6, -0.8), width=6.0, soft=0.0):
        """A band along the light-facing contour of the shape. Used for backlit rims, edge highlights and a sense of
        thickness.

        Shift the shape away from the light by width, and the part left uncovered is the edge that catches the
        light.
        form_light places a highlight inside the surface, and edge_light places light on the contour.
        """
        direction = np.asarray(light, np.float64)
        direction = direction / max(np.linalg.norm(direction), 1e-9)
        offset = -direction * width * self.scale
        matrix = np.array([[1.0, 0.0, offset[0]], [0.0, 1.0, offset[1]]], np.float32)
        moved = cv2.warpAffine(shape.mask, matrix, (shape.mask.shape[1], shape.mask.shape[0]))
        band = np.clip(shape.mask - moved, 0.0, 1.0)
        if soft > 0.0:
            band = cv2.GaussianBlur(band, (0, 0), soft * self.scale) * shape.mask
        return Shape(band, shape.x0, shape.y0)

    def _form_band(self, shape, light, amount, soft, roundness, lit_side):
        inside = shape.mask > 0.5
        if not inside.any():
            return Shape(np.zeros_like(shape.mask), shape.x0, shape.y0)
        # The highlight uses light tilted toward the viewer so it settles inside the surface and stays off the
        # contour.
        depth = LIGHT_DEPTH_HIGHLIGHT if lit_side else LIGHT_DEPTH_SHADOW
        lambert = self._lambert(shape, light, roundness, depth)
        if lit_side:
            lambert = -lambert
        threshold = float(np.quantile(lambert[inside], amount))
        spread = max(soft * float(np.ptp(lambert[inside])), 1e-4)
        band = 1.0 - _smoothstep(threshold - spread, threshold + spread, lambert)
        return Shape(band * shape.mask, shape.x0, shape.y0)

    def direct(self, shape, angle=None, around=None):
        """Set the brushstroke direction for a shape area. Brush texture explains the direction of a form.

        angle: direction in degrees (0 is horizontal, 90 is vertical). For example, horizontal for water and
        vertical for grass.
        around: a direction circling this point. Used for suns, moons and swirling clouds.
        """
        if (angle is None) == (around is None):
            raise ValueError("give exactly one of angle and around")
        region = (slice(shape.y0, shape.y1), slice(shape.x0, shape.x1))
        inside = shape.mask > 0.5
        if angle is not None:
            values = np.full(shape.mask.shape, np.deg2rad(angle), np.float32)
        else:
            ys, xs = np.mgrid[shape.y0:shape.y1, shape.x0:shape.x1].astype(np.float32)
            values = np.arctan2(ys - around[1] * self.scale, xs - around[0] * self.scale) + np.pi / 2.0
        self.flow[region] = np.where(inside, values, self.flow[region])

    # ---------- paint ----------

    def fill(self, shape, paint, opacity=1.0, blend=Blend.NORMAL, clip=None, grain=0.0):
        """Paint a color or a gradient into a shape.

        With clip, paint goes only inside that shape (shadows, patterns, highlights).
        Raising grain turns semi-transparent areas into stipple grains (the rough gradients of illustration).
        """
        if shape.is_empty:
            return
        coverage = shape.mask if clip is None else (shape & clip).mask
        coverage = np.clip(coverage, 0.0, 1.0)
        if grain > 0.0:
            speckle = noise.white(coverage.shape, self.next_seed())
            stippled = (coverage > speckle).astype(np.float32)
            coverage = coverage * (1.0 - grain) + stippled * grain
        source_alpha = (coverage * opacity)[..., None]

        region = (slice(shape.y0, shape.y1), slice(shape.x0, shape.x1))
        if hasattr(paint, "sample"):
            ys, xs = np.mgrid[shape.y0:shape.y1, shape.x0:shape.x1].astype(np.float32) / self.scale
            source = paint.sample(xs, ys)
        else:
            source = np.broadcast_to(colors.rgb(paint), coverage.shape + (3,))

        backdrop = self.rgb[region]
        backdrop_alpha = self.alpha[region][..., None]
        # Where the base is transparent, there is nothing to blend with, so the plain color is used.
        blended = backdrop_alpha * _blend_colors(backdrop, source, blend) + (1.0 - backdrop_alpha) * source
        out_alpha = source_alpha + backdrop_alpha * (1.0 - source_alpha)
        out_rgb = (blended * source_alpha + backdrop * backdrop_alpha * (1.0 - source_alpha)) \
            / np.maximum(out_alpha, 1e-6)
        self.rgb[region] = out_rgb
        self.alpha[region] = out_alpha[..., 0]

    def stroke(self, path, color, width=2.0, taper=1.0, closed=False, opacity=1.0,
               blend=Blend.NORMAL, clip=None, light=None, contrast=0.6, jitter=0.0, soft=0.0):
        """Draw a line. Pressure can vary in three ways.

        taper: list of width factors along the length. (0, 1, 0) gives a line pointed at both ends.
        light: with a light direction, the contour side away from the light gets thicker (weight variation of closed
        outlines).
        jitter: 0-1 amount of gentle width wobble, like a trembling hand.
        """
        path = np.asarray(path, np.float64)
        if not closed:
            path = geometry.densify(path, config.MIN_STROKE_POINTS)
        widths = geometry.taper_profile(path, taper) * width
        if light is not None:
            outward = geometry.normals(path, closed)
            if closed and geometry.signed_area(path) < 0.0:
                outward = -outward
            direction = np.asarray(light, np.float64)
            direction = direction / max(np.linalg.norm(direction), 1e-9)
            widths = widths * np.clip(1.0 - contrast * (outward @ direction), 0.25, None)
        if jitter > 0.0:
            knots = self.rng.uniform(1.0 - jitter, 1.0 + jitter, max(len(path) // 12, 4))
            widths = widths * np.interp(geometry.arc_lengths(path), np.linspace(0.0, 1.0, len(knots)), knots)
        outline = self.shape(*geometry.ribbon(path, widths, closed), soft=soft)
        self.fill(outline, color, opacity=opacity, blend=blend, clip=clip)

    def paste(self, other, opacity=1.0):
        """Place another canvas of the same size on top of this one (compositing a figure layer over a background
        and so on)."""
        if other.rgb.shape != self.rgb.shape:
            raise ValueError("pixel size of the canvas to paste differs")
        source_alpha = (other.alpha * opacity)[..., None]
        backdrop_alpha = self.alpha[..., None]
        out_alpha = source_alpha + backdrop_alpha * (1.0 - source_alpha)
        self.rgb = (other.rgb * source_alpha + self.rgb * backdrop_alpha * (1.0 - source_alpha)) \
            / np.maximum(out_alpha, 1e-6)
        self.alpha = out_alpha[..., 0]

    # ---------- output ----------

    def image(self, background="#ffffff"):
        """0-1 float RGB image. Transparent areas are filled with the background color."""
        alpha = self.alpha[..., None]
        return np.clip(self.rgb * alpha + colors.rgb(background) * (1.0 - alpha), 0.0, 1.0)

    def guide_image(self, step=config.GUIDE_STEP):
        """An image with the logical coordinate grid drawn over it. Used to check and fix shape positions by eye."""
        frame = (self.image() * 255.0).astype(np.uint8)[..., ::-1].copy()
        for x in np.arange(0.0, self.width + 1.0, step):
            px = int(round(x * self.scale))
            cv2.line(frame, (px, 0), (px, self.px_h - 1), config.GUIDE_COLOR, 1)
            cv2.putText(frame, str(int(x)), (px + 3, 14), cv2.FONT_HERSHEY_SIMPLEX,
                        config.GUIDE_FONT_SCALE, config.GUIDE_COLOR, 1, cv2.LINE_AA)
        for y in np.arange(0.0, self.height + 1.0, step):
            py = int(round(y * self.scale))
            cv2.line(frame, (0, py), (self.px_w - 1, py), config.GUIDE_COLOR, 1)
            cv2.putText(frame, str(int(y)), (3, py - 4), cv2.FONT_HERSHEY_SIMPLEX,
                        config.GUIDE_FONT_SCALE, config.GUIDE_COLOR, 1, cv2.LINE_AA)
        return frame[..., ::-1].astype(np.float32) / 255.0
