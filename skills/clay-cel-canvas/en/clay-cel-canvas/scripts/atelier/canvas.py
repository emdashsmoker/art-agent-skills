"""The drawing surface: a digital painter's layer stack, driven by code.

Layers, bottom to top:
    flat   base colours and painted detail       (normal blend)
    shade  shadows                               (multiply)
    glow   highlights and light                  (screen)
    line   line art                              (alpha over)

Adding a part clears shade, glow and line underneath it, so parts occlude each
other in drawing order while every stage stays separately viewable.

All coordinates and sizes are in canvas units: the canvas is 1000 units wide at
any pixel size, so a 512 px preview and a 2048 px final share one script.
"""
from contextlib import contextmanager
from typing import NamedTuple

import cv2
import numpy as np

from .color import line_color_for, rgb
from .finish import apply_finish, value_noise
from .geometry import resample, tube
from .style import ShadeMode

UNITS_WIDE = 1000.0
SUPERSAMPLE = 2            # masks are rasterised larger, then averaged down
FIXED_POINT_BITS = 4       # sub-pixel precision passed to OpenCV drawing calls

DEFAULT_LIGHT = (-0.45, -0.60, 0.66)  # direction toward the light: x right, y down, z to viewer
DEFAULT_SHADOW_TINT = "#A79AD2"
CEL_THRESHOLD = 0.30       # lambert value where a cel shadow begins
CEL_EDGE = 0.035
SOFT_LIGHT_END = 0.90      # soft shading runs between these lambert values
SOFT_DARK_END = -0.20
SOFT_FORM_LIGHT = 0.16     # SOFT mode also brightens the side facing the light
FORM_LIGHT_COLOR = "#FFF1DC"
FORM_GAIN = 1.5            # how strongly shapes bulge toward the viewer
OUTLINE_WIDTH = 2.6
OUTLINE_VARIATION = 0.45   # lines get this much thicker on the side facing away from light
LINE_WIDTH = 2.2
MIN_PEN_WIDTH = 1.3        # lines of a shrunken sub-drawing never get thinner than this
SKETCH_GAIN = 1.2          # how readily a colour border becomes a pencil line
SKETCH_OPACITY = 0.75
WIDE_BLUR_SIGMA = 6.0     # px; wider blurs run on a downscaled copy
INFLATE_GRID = 160         # px; longest side of the grid the balloon shape is solved on
INFLATE_LEVELS = (8, 4, 2, 1)
INFLATE_SWEEPS = 120
INFLATE_GAIN = 1.8         # 2.0 turns a disc into a true hemisphere; a little flatter reads better
NEIGHBOUR_KERNEL = np.array([[0, 0.25, 0], [0.25, 0, 0.25], [0, 0.25, 0]], np.float32)

TAPERS = {
    "both": lambda t: np.sin(np.pi * t) ** 0.55,
    "start": lambda t: t ** 0.6,          # thin at the first point
    "end": lambda t: (1 - t) ** 0.6,      # thin at the last point
    "none": lambda t: np.ones_like(t),
}
STAGES = ("line", "flat", "shade", "light", "final")


def _smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


def _blur_wide(image, sigma):
    """Gaussian blur that stays fast for wide radii by working on a smaller copy."""
    if sigma <= WIDE_BLUR_SIGMA:
        return cv2.GaussianBlur(image, (0, 0), max(sigma, 0.3))
    factor = sigma / WIDE_BLUR_SIGMA
    height, width = image.shape[:2]
    small_size = (max(int(width / factor), 2), max(int(height / factor), 2))
    small = cv2.resize(image, small_size, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), WIDE_BLUR_SIGMA)
    wide = cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(wide, (0, 0), factor)  # hides the grid of the small copy


def _inflate(mask):
    """Height (px) of the mask blown up like a balloon: discs become domes, strips
    become half-cylinders.

    Solves the Poisson equation laplace(u) = -1 inside the mask on a small grid,
    coarse to fine, then takes the square root: for a disc that is exactly a sphere.
    """
    rows, cols = np.nonzero(mask > 0.5)
    height = np.zeros(mask.shape, np.float32)
    if len(rows) == 0:
        return height
    top, bottom = max(rows.min() - 2, 0), min(rows.max() + 3, mask.shape[0])
    left, right = max(cols.min() - 2, 0), min(cols.max() + 3, mask.shape[1])
    crop = mask[top:bottom, left:right]
    factor = max(max(crop.shape) / INFLATE_GRID, 1.0)
    grid = (max(int(crop.shape[1] / factor), 4), max(int(crop.shape[0] / factor), 4))
    potential = None
    for level in INFLATE_LEVELS:                      # grid spacing, coarse to fine
        size = (max(grid[0] // level, 2), max(grid[1] // level, 2))
        inside = (cv2.resize(crop, size, interpolation=cv2.INTER_AREA) > 0.5).astype(np.float32)
        potential = (np.zeros(size[::-1], np.float32) if potential is None
                     else cv2.resize(potential, size, interpolation=cv2.INTER_LINEAR))
        for _ in range(INFLATE_SWEEPS):
            neighbours = cv2.filter2D(potential, -1, NEIGHBOUR_KERNEL, borderType=cv2.BORDER_CONSTANT)
            potential = (neighbours + level * level / 4) * inside
    dome = np.sqrt(np.maximum(potential, 0)) * INFLATE_GAIN * factor
    dome = cv2.resize(dome, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_CUBIC)
    height[top:bottom, left:right] = cv2.GaussianBlur(dome, (0, 0), max(factor, 0.6))
    return height


class Placement(NamedTuple):
    """Where local coordinates land on the canvas: world = matrix @ local + offset."""
    matrix: np.ndarray
    offset: np.ndarray
    scale: float


IDENTITY = Placement(np.eye(2), np.zeros(2), 1.0)


class Art:
    def __init__(self, style, width_px=1024, aspect=1.25, light=DEFAULT_LIGHT,
                 seed=7, paper="#FFFFFF", view=None):
        """view=(center_x, center_y, zoom) frames the picture like a camera, so the
        composition can be changed without touching any coordinates."""
        self.style = style
        self.width = int(width_px)
        self.height = int(round(width_px * aspect))
        self.units_high = UNITS_WIDE * aspect
        center_x, center_y, zoom = view or (UNITS_WIDE / 2, self.units_high / 2, 1.0)
        self.ppu = self.width / UNITS_WIDE * zoom
        # pixel = unit * ppu - origin
        self.origin = np.array([center_x * self.ppu - self.width / 2,
                                center_y * self.ppu - self.height / 2], np.float32)
        self.light_dir = np.asarray(light, np.float32) / np.linalg.norm(light)
        self.rng = np.random.default_rng(seed)
        self.paper = rgb(paper)
        size = (self.height, self.width)
        self.flat = np.ones(size + (3,), np.float32) * self.paper
        self.shade = np.ones(size + (3,), np.float32)
        self.glow = np.zeros(size + (3,), np.float32)
        self.line_rgb = np.zeros(size + (3,), np.float32)   # premultiplied by alpha
        self.line_alpha = np.zeros(size, np.float32)
        self.focus = np.zeros(size, np.float32)
        self.grade = None    # mood grade (image, ppu, rng) -> image, run after the finish
        self._placement = IDENTITY

    # -------------------------------------------------------------- placement

    @contextmanager
    def place(self, at=(0.0, 0.0), scale=1.0, angle=0.0, flip=False, pivot=(0.0, 0.0)):
        """Draw a sub-picture in its own coordinates, then set it down anywhere.

        Inside the block every coordinate and size is local: `pivot` (local)
        lands on `at`, after mirroring (flip), scaling and rotating (degrees,
        clockwise on screen). Blocks can be nested. Masks made inside the block
        are ordinary canvas masks and stay valid outside it.
        """
        previous = self._placement
        turn = np.radians(angle)
        local = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]]) * scale
        if flip:
            local = local @ np.diag([-1.0, 1.0])
        matrix = previous.matrix @ local
        offset = (previous.matrix @ np.asarray(at, float) + previous.offset
                  - matrix @ np.asarray(pivot, float))
        self._placement = Placement(matrix, offset, previous.scale * scale)
        try:
            yield
        finally:
            self._placement = previous

    def _world(self, points):
        return np.asarray(points, float) @ self._placement.matrix.T + self._placement.offset

    def _size(self, value):
        return value * self._placement.scale

    def _pen(self, width, default):
        """Line width in canvas units under the current placement.

        A width given by the caller is local, so it scales like everything else.
        The default pen belongs to the picture: it shrinks with a shrunken
        sub-drawing but never grows. Inside a placement no line goes hair-thin.
        """
        scale = self._placement.scale
        if scale == 1.0:
            return default if width is None else width
        scaled = default * min(scale, 1.0) if width is None else width * scale
        return max(scaled, MIN_PEN_WIDTH)

    # ------------------------------------------------------------------ masks

    def _raster(self, draw, bounds):
        """Run draw() on a supersampled crop; return (small mask, region) or None."""
        x0 = max(int(np.floor(bounds[0] * self.ppu - self.origin[0])) - 2, 0)
        y0 = max(int(np.floor(bounds[1] * self.ppu - self.origin[1])) - 2, 0)
        x1 = min(int(np.ceil(bounds[2] * self.ppu - self.origin[0])) + 2, self.width)
        y1 = min(int(np.ceil(bounds[3] * self.ppu - self.origin[1])) + 2, self.height)
        if x1 <= x0 or y1 <= y0:
            return None
        big = np.zeros(((y1 - y0) * SUPERSAMPLE, (x1 - x0) * SUPERSAMPLE), np.uint8)
        scale = self.ppu * SUPERSAMPLE * (1 << FIXED_POINT_BITS)
        origin = (self.origin + (x0, y0)) * SUPERSAMPLE * (1 << FIXED_POINT_BITS)

        def to_fixed(points):
            return np.round(np.asarray(points, float) * scale - origin).astype(np.int32)

        draw(big, to_fixed, scale)
        small = cv2.resize(big, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
        return small.astype(np.float32) / 255, (slice(y0, y1), slice(x0, x1))

    def _to_pixels(self, point):
        return np.asarray(point, np.float32) * self.ppu - self.origin

    def _full(self, patch):
        mask = np.zeros((self.height, self.width), np.float32)
        if patch is not None:
            small, region = patch
            mask[region] = small
        return mask

    def _shapes_patch(self, curves):
        """Fill one or more closed curves, given in local coordinates."""
        curves = [self._world(curve) for curve in curves]

        def draw(big, to_fixed, _scale):
            for curve in curves:
                cv2.fillPoly(big, [to_fixed(curve)], 255, cv2.LINE_AA, FIXED_POINT_BITS)

        every = np.vstack(curves)
        return self._raster(draw, (*every.min(axis=0), *every.max(axis=0)))

    def _stroke_patch(self, points, width, taper):
        """Stroke of one width with tapered ends; points local, width already final."""
        points = resample(self._world(points), max(width * 0.3, 0.8))
        if len(points) < 2:
            return None
        half = width / 2 * TAPERS[taper](np.linspace(0, 1, len(points)))
        return self._ribbon_patch(points, half)

    def _ribbon_patch(self, points, half):
        """Band along world-space points with a half-width at each point."""
        direction = np.gradient(points, axis=0)
        direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-9)
        side = np.stack([-direction[:, 1], direction[:, 0]], axis=1) * half[:, None]
        left, right = points + side, points - side

        def draw(big, to_fixed, scale):
            # Why per-segment quads: a single polygon self-intersects on tight bends.
            for i in range(len(points) - 1):
                quad = to_fixed([left[i], left[i + 1], right[i + 1], right[i]])
                cv2.fillConvexPoly(big, quad, 255, cv2.LINE_AA, FIXED_POINT_BITS)
                center = tuple(int(v) for v in to_fixed(points[i]))
                cv2.circle(big, center, int(half[i] * scale), 255, -1,
                           cv2.LINE_AA, FIXED_POINT_BITS)

        reach = 2 * float(half.max())
        low, high = points.min(axis=0) - reach, points.max(axis=0) + reach
        return self._raster(draw, (*low, *high))

    def shape(self, points):
        """Filled mask (float 0..1) from a dense closed curve."""
        return self._full(self._shapes_patch([points]))

    def shapes(self, curves):
        """One mask from many closed curves at once: windows, tiles, leaves."""
        return self._full(self._shapes_patch(curves))

    def brush(self, points, width, taper="both"):
        """Mask of a stroke along a dense curve. taper: both, start, end, none."""
        return self._full(self._stroke_patch(points, self._size(width), taper))

    def tube(self, points):
        """Mask of a rounded limb through (x, y, width) control points."""
        dense = tube(points)
        centre = self._world(dense[:, :2])
        width = self._size(dense[:, 2])
        dense = resample(np.column_stack([centre, width]), max(float(width.min()) * 0.3, 0.8))
        if len(dense) < 2:
            return self._full(None)
        return self._full(self._ribbon_patch(dense[:, :2], dense[:, 2] / 2))

    def everywhere(self):
        """Mask covering the whole picture."""
        return np.ones((self.height, self.width), np.float32)

    def ramp(self, start, end):
        """Linear gradient mask: 0 at start, 1 at end."""
        start, end = self._to_pixels(self._world(start)), self._to_pixels(self._world(end))
        grid_y, grid_x = np.mgrid[0:self.height, 0:self.width].astype(np.float32)
        axis = end - start
        along = (grid_x - start[0]) * axis[0] + (grid_y - start[1]) * axis[1]
        return np.clip(along / float(axis @ axis), 0, 1)

    def blob(self, center, radius):
        """Soft round mask: 1 at the centre, fading to 0 at radius."""
        grid_y, grid_x = np.mgrid[0:self.height, 0:self.width].astype(np.float32)
        center = self._to_pixels(self._world(center))
        distance = np.hypot(grid_x - center[0], grid_y - center[1])
        return 1 - _smoothstep(0, self._size(radius) * self.ppu, distance)

    def noise(self, cell, octaves=3):
        """Smooth random field in 0..1; cell is the blob size in units."""
        return value_noise((self.height, self.width), self._size(cell) * self.ppu, self.rng,
                           octaves)

    def threshold(self, field, level, softness=0.05):
        """Turn a smooth field (noise, ramp) into a mask: 1 where field > level."""
        return _smoothstep(level - softness, level + softness, field).astype(np.float32)

    def feather(self, mask, radius):
        """Soften a mask edge by radius units."""
        return _blur_wide(mask, self._size(radius) * self.ppu)

    def _signed_distance(self, mask):
        """Pixels from the mask edge: negative inside, positive outside."""
        binary = (mask > 0.5).astype(np.uint8)
        outside = cv2.distanceTransform(1 - binary, cv2.DIST_L2, 5)
        inside = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        signed = np.where(binary > 0, 0.5 - inside, outside - 0.5)
        return cv2.GaussianBlur(signed, (0, 0), 1.0)  # removes pixel staircase

    def grow(self, mask, amount):
        """Expand the mask edge by amount units; negative shrinks."""
        return np.clip(self._size(amount) * self.ppu - self._signed_distance(mask) + 0.5, 0, 1)

    def move(self, mask, dx, dy):
        """Shift a mask by (dx, dy) units."""
        dx, dy = self._placement.matrix @ (dx, dy)
        matrix = np.float32([[1, 0, dx * self.ppu], [0, 1, dy * self.ppu]])
        return cv2.warpAffine(mask, matrix, (self.width, self.height))

    def _as_mask(self, shape):
        shape = np.asarray(shape, np.float32)
        if shape.shape == (self.height, self.width):
            return shape
        return self.shape(shape)

    # ------------------------------------------------------------------ paint

    def _occlude(self, mask):
        keep = (1 - mask)[..., None]
        self.shade = self.shade * keep + mask[..., None]
        self.glow *= keep
        self.line_rgb *= keep
        self.line_alpha *= keep[..., 0]

    def erase_line(self, mask):
        """Remove line art under a mask, to join parts that should read as one."""
        self.line_rgb *= (1 - mask)[..., None]
        self.line_alpha *= 1 - mask

    def paint(self, mask, color, opacity=1.0):
        """Paint colour onto the flat layer through a mask."""
        alpha = (mask * opacity)[..., None]
        self.flat += (rgb(color) - self.flat) * alpha

    def _soften(self, mask):
        """Feather hand-placed shadow and light shapes in styles that ask for it."""
        if self.style.softness <= 0:
            return mask
        return self.feather(mask, self.style.softness)

    def shadow(self, mask, tint=None, opacity=1.0):
        """Darken through a mask by multiplying with a tint colour."""
        mask = self._soften(mask)
        tint = rgb(DEFAULT_SHADOW_TINT if tint is None else tint)
        amount = (mask * opacity * self.style.shade_strength)[..., None]
        self.shade *= 1 - amount * (1 - tint)

    def light(self, mask, color="#FFFFFF", opacity=1.0):
        """Add light through a mask (screen blend): highlights, rim light, glow."""
        mask = self._soften(mask)
        lit = 1 - (1 - self.glow) * (1 - rgb(color) * (mask * opacity)[..., None])
        self.glow = lit.astype(np.float32)  # numpy scalars can silently widen to float64

    def lambert(self, mask, bulge=None):
        """Lighting of the mask as a solid form: 1 lit, below 0 unlit.

        Without bulge the mask is inflated like a balloon: round things become
        spheres, limbs become cylinders. With bulge (a radius in units) the
        shape stays flat and only its rim is rounded, like a cushion or a coat.
        """
        if bulge:
            inside = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
            radius = min(self._size(bulge) * self.style.form_scale * self.ppu,
                         max(float(inside.max()), 1.0))
            # Why a blurred mask, not the distance itself: distance has creases along
            # the middle of a shape, and creases show up as kinks in the shadow edge.
            # A blurred step is already dome-like: steep at the rim, flat in the middle.
            height = _blur_wide(mask, radius * 0.5) * radius * FORM_GAIN
        else:
            height = _inflate(mask)
        slope_y, slope_x = np.gradient(height)
        normal = np.stack([-slope_x, -slope_y, np.ones_like(height)], axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        return normal @ self.light_dir

    def form_shadow(self, mask, bulge=None, tint=None, clip=None):
        """Shadow the side of a shape that faces away from the light.

        clip limits where the shadow lands: use it to shade one finger or limb
        of a larger part without darkening the place where it joins.
        """
        lit = self.lambert(mask, bulge)
        if clip is not None:
            mask = mask * clip
        self.shade_by(mask, lit, tint)

    def shade_by(self, mask, lit, tint=None):
        """Shadow where a lighting field (1 lit, below 0 unlit) turns away from the light,
        the way the style shades: hard-edged for cel, graded for soft."""
        amount_by_mode = {
            ShadeMode.CEL: lambda: _smoothstep(CEL_THRESHOLD + CEL_EDGE,
                                               CEL_THRESHOLD - CEL_EDGE, lit),
            ShadeMode.SOFT: lambda: _smoothstep(SOFT_LIGHT_END, SOFT_DARK_END, lit),
        }
        amount = amount_by_mode[self.style.shade_mode]()
        tint = rgb(DEFAULT_SHADOW_TINT if tint is None else tint)
        strength = (mask * amount * self.style.shade_strength)[..., None]
        self.shade *= np.clip(1 - strength * (1 - tint), 0, 1)   # a strong style never goes past black
        if self.style.shade_mode is ShadeMode.SOFT:
            facing = _smoothstep(0.75, 1.0, lit) * mask * SOFT_FORM_LIGHT
            self.light(facing, FORM_LIGHT_COLOR)

    def _ink(self, alpha, color, region=(slice(None), slice(None))):
        alpha = alpha[..., None]
        self.line_rgb[region] = self.line_rgb[region] * (1 - alpha) + rgb(color) * alpha
        self.line_alpha[region] = self.line_alpha[region] * (1 - alpha[..., 0]) + alpha[..., 0]

    def ink(self, alpha, color=None, opacity=1.0):
        """Put a ready-made line mask on the line layer (hidden in styles without line art)."""
        if self.style.line_opacity <= 0:
            return
        self._ink(alpha * self.style.line_opacity * opacity, self.style.ink if color is None else color)

    def outline(self, mask, color=None, width=None, clip=None):
        """Contour line around a mask, thicker on the side away from the light."""
        if self.style.line_opacity <= 0 or mask.max() <= 0.5:
            return
        distance = self._signed_distance(mask)
        slope_y, slope_x = np.gradient(distance)
        length = np.maximum(np.hypot(slope_x, slope_y), 1e-6)
        light_2d = self.light_dir[:2] / max(np.linalg.norm(self.light_dir[:2]), 1e-6)
        away = -(slope_x * light_2d[0] + slope_y * light_2d[1]) / length
        base = self._pen(width, OUTLINE_WIDTH) * self.style.line_width * self.ppu
        thickness = base * (1 + OUTLINE_VARIATION * away)
        alpha = np.clip(thickness / 2 - np.abs(distance) + 0.5, 0, 1) * self.style.line_opacity
        if clip is not None:
            alpha = alpha * clip
        self._ink(alpha, self.style.ink if color is None else color)

    def line(self, points, color=None, width=None, taper="both", opacity=1.0):
        """Ink stroke on the line layer. Hidden in styles that have no line art."""
        if self.style.line_opacity <= 0:
            return
        width = self._pen(width, LINE_WIDTH) * self.style.line_width
        patch = self._stroke_patch(points, width, taper)
        if patch is None:
            return
        small, region = patch
        self._ink(small * self.style.line_opacity * opacity,
                  self.style.ink if color is None else color, region)

    def mark(self, points, color, width, taper="both", opacity=1.0):
        """Painted stroke on the flat layer. Drawn in every style."""
        patch = self._stroke_patch(points, self._size(width), taper)
        if patch is None:
            return
        small, region = patch
        self.flat[region] += (rgb(color) - self.flat[region]) * (small * opacity)[..., None]

    def line_color(self, fill):
        """The style's outline colour for a part filled with the given colour."""
        return line_color_for(fill, self.style.ink, self.style.line_local_color)

    def part(self, shape, color, *, shade=True, outline=True, bulge=None,
             shadow_tint=None, line_color=None, line_width=None):
        """Add a solid part: base colour, form shadow, outline. Returns its mask.

        shape is a dense closed curve or an existing mask.
        """
        mask = self._as_mask(shape)
        self._occlude(mask)
        self.paint(mask, color)
        if shade:
            self.form_shadow(mask, bulge, shadow_tint)
        if outline:
            self.outline(mask, self.line_color(color) if line_color is None else line_color,
                         line_width)
        return mask

    def blur(self, radius):
        """Blur everything drawn so far: pushes the background out of focus."""
        sigma = max(self._size(radius) * self.ppu, 0.3)
        for name in ("flat", "shade", "glow", "line_rgb", "line_alpha"):
            setattr(self, name, _blur_wide(getattr(self, name), sigma))

    def focus_on(self, mask):
        """Mark the focal area: finishing passes keep it crisper than the rest."""
        self.focus = np.maximum(self.focus, mask)

    # ----------------------------------------------------------------- output

    def _with_line(self, image):
        return image * (1 - self.line_alpha[..., None]) + self.line_rgb

    def _sketch(self):
        """Pencil drawing on paper, traced from the borders between painted colours.

        Why: eyes and mouths are paint, not ink, so the line layer alone would
        show a face without features.
        """
        steps = [cv2.Sobel(self.flat, cv2.CV_32F, dx, dy) for dx, dy in ((1, 0), (0, 1))]
        border = np.sqrt(steps[0] ** 2 + steps[1] ** 2).max(axis=2)
        pencil = np.clip(border * SKETCH_GAIN, 0, 1)[..., None] * SKETCH_OPACITY
        return self.paper * (1 - pencil) + rgb(self.style.ink) * pencil

    def compose(self, stage="final"):
        """Float RGB image of one stage: line, flat, shade, light or final."""
        if stage not in STAGES:
            raise ValueError(f"stage must be one of {STAGES}, got {stage!r}")
        if stage == "line":
            return self._with_line(self._sketch())
        if stage == "flat":
            return self._with_line(self.flat)
        if stage == "shade":
            return self._with_line(self.flat * self.shade)
        lit = self._with_line(1 - (1 - self.flat * self.shade) * (1 - self.glow)).astype(np.float32)
        if stage == "light":
            return lit
        finish_rng = np.random.default_rng(self.rng.integers(1 << 31))
        # Why not self.ppu: texture size belongs to the picture, not to the camera zoom.
        picture_ppu = self.width / UNITS_WIDE
        picture = apply_finish(self.style.finish, lit, picture_ppu, finish_rng, self.focus)
        if self.grade is None:
            return picture
        grade_rng = np.random.default_rng(self.rng.integers(1 << 31))
        return np.clip(self.grade(picture, picture_ppu, grade_rng), 0, 1)

    @staticmethod
    def _to_bgr8(image):
        return cv2.cvtColor((np.clip(image, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)

    def save(self, path, stage="final", downscale=1):
        """Write one stage as an image. downscale=2 halves the size for cleaner edges."""
        image = self._to_bgr8(self.compose(stage))
        if downscale > 1:
            size = (self.width // downscale, self.height // downscale)
            image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(path), image)

    def save_stages(self, path):
        """Write all stages side by side: line, flat, shade, light, final."""
        cv2.imwrite(str(path), np.hstack([self._to_bgr8(self.compose(s)) for s in STAGES]))
