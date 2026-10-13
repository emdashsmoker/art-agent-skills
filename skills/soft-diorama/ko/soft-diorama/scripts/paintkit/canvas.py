"""Canvas: one color layer + one line layer.

fill() lays down an opaque surface (a new object) and erases older lines
under it, so drawing back-to-front just works. tint() modifies what is already
there (shadows, glows, gradients). ink()/outline() draw on the line layer,
which stays separate so each style can finish colors and lines differently.
"""
import cv2
import numpy as np

from . import config, geometry, raster, shading
from .color import adjust, light_of, rgb, shadow_of


def _blend(base, top, mode):
    if mode == 'normal':
        return top
    if mode == 'multiply':
        return base * top
    if mode == 'screen':
        return 1.0 - (1.0 - base) * (1.0 - top)
    if mode == 'add':
        return base + top
    if mode == 'overlay':
        return np.where(base < 0.5, 2.0 * base * top, 1.0 - 2.0 * (1.0 - base) * (1.0 - top))
    if mode == 'soft_light':
        return (1.0 - 2.0 * top) * base * base + 2.0 * top * base
    raise ValueError(f'unknown blend mode: {mode}')


def _bbox(mask):
    rows = np.flatnonzero(mask.max(axis=1) > 1e-4)
    cols = np.flatnonzero(mask.max(axis=0) > 1e-4)
    if rows.size == 0 or cols.size == 0:
        return None
    return slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1)


class Canvas:
    def __init__(self, width=config.DEFAULT_WIDTH, height=config.DEFAULT_HEIGHT, background='#ffffff'):
        self.width, self.height = width, height
        self.size = (width, height)
        self.color = np.empty((height, width, 3), np.float32)
        self.color[:] = rgb(background)
        # Line layer is stored premultiplied so that compositing is a single lerp.
        self.line_rgb = np.zeros((height, width, 3), np.float32)
        self.line_alpha = np.zeros((height, width), np.float32)
        self._tracking = {}

    # --- shape constructors (return masks) ---------------------------------
    def blob(self, points, smooth=True):
        return raster.blob_mask(self.size, points, smooth)

    def polygon(self, *polygons):
        return raster.polygon_mask(self.size, list(polygons))

    def rect(self, x0, y0, x1, y1, radius=0.0):
        """Axis-aligned rectangle, optionally with rounded corners (screens, keys, buttons, phones)."""
        radius = min(radius, abs(x1 - x0) / 2.0, abs(y1 - y0) / 2.0)
        if radius <= 0:
            return self.polygon(np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
        core = self.polygon(np.array([(x0 + radius, y0), (x1 - radius, y0), (x1 - radius, y1), (x0 + radius, y1)]),
                            np.array([(x0, y0 + radius), (x1, y0 + radius), (x1, y1 - radius), (x0, y1 - radius)]))
        corners = [raster.ellipse_mask(self.size, cx, cy, radius, radius)
                   for cx in (x0 + radius, x1 - radius) for cy in (y0 + radius, y1 - radius)]
        return np.maximum.reduce([core] + corners)

    def ellipse(self, cx, cy, rx, ry=None, rotation_deg=0.0):
        return raster.ellipse_mask(self.size, cx, cy, rx, ry or rx, rotation_deg)

    def ribbon(self, points, width, profile='taper', smooth=True):
        return raster.ribbon_mask(self.size, [raster.ribbon_pieces(points, width, profile, smooth)])

    def contour(self, points, left, right, bend=0.0):
        """Band with a different width on each side of its centerline - for forms
        whose two edges are not mirror images (limbs, a bottle seen off-axis).

        left, right: [(t, px), ...] distances from the centerline at positions t (0..1)
        along it; "left" is the left-hand side when walking from the first point to the last.
        bend: px radius that rounds the corners of the centerline (a soft elbow instead of a hinge).
        """
        return raster.ribbon_mask(self.size, [raster.contour_pieces(points, left, right, bend)])

    def ribbons(self, strokes):
        """Many ribbons in one mask. strokes: iterable of (points, width, profile)."""
        return raster.ribbon_mask(self.size, [raster.ribbon_pieces(p, w, pr) for p, w, pr in strokes])

    def empty(self):
        return np.zeros((self.height, self.width), np.float32)

    def full(self):
        return np.ones((self.height, self.width), np.float32)

    # --- scalar fields -------------------------------------------------------
    def linear(self, p0, p1):
        return raster.linear_field(self.size, p0, p1)

    def radial(self, center, rx, ry=None, rotation_deg=0.0):
        return raster.radial_field(self.size, center, rx, ry, rotation_deg)

    def noise(self, scale=64.0, octaves=4, seed=None, stretch=(1.0, 1.0)):
        return raster.noise_field(self.size, scale, octaves, seed, stretch)

    def ramp(self, field, *stops):
        """Map a scalar field (0..1) to colors. stops: colors, evenly spaced,
        or (position, color) pairs. Returns an (H, W, 3) image usable as a fill color."""
        if not isinstance(stops[0], tuple) or len(stops[0]) != 2 or isinstance(stops[0][0], str):
            stops = [(i / (len(stops) - 1), c) for i, c in enumerate(stops)]
        positions = np.array([p for p, _ in stops], np.float32)
        colors = np.stack([rgb(c) for _, c in stops])
        return np.stack([np.interp(field, positions, colors[:, k]) for k in range(3)], axis=-1).astype(np.float32)

    # --- painting -----------------------------------------------------------
    def fill(self, mask, color, opacity=1.0):
        """Paint an opaque surface. Hides older lines beneath it."""
        self._paint(mask, color, 'normal', opacity)
        self.line_rgb *= (1.0 - mask * opacity)[..., None]
        self.line_alpha *= 1.0 - mask * opacity
        for tracked in self._tracking.values():
            np.maximum(tracked, mask, out=tracked)

    def tint(self, mask, color, mode='multiply', opacity=1.0):
        """Modify existing color inside a mask (shadow, light, glow, gradient)."""
        self._paint(mask, color, mode, opacity)

    def _paint(self, mask, color, mode, opacity):
        box = _bbox(mask)
        if box is None:
            return
        alpha = (mask[box] * opacity)[..., None]
        color = np.asarray(color) if not isinstance(color, str) else rgb(color)
        top = color[box] if color.ndim == 3 else rgb(color)
        base = self.color[box]
        blended = np.clip(_blend(base, top, mode), 0.0, 1.0)
        self.color[box] = base + (blended - base) * alpha

    def ink(self, points, width, color='#2a2030', profile='taper', opacity=1.0, clip=None, smooth=True):
        """One pen stroke on the line layer."""
        self.ink_mask(self.ribbon(points, width, profile, smooth), color, opacity, clip)

    def ink_mask(self, mask, color='#2a2030', opacity=1.0, clip=None):
        """Put any mask on the line layer (e.g. many ribbons rasterized at once)."""
        alpha = mask * opacity if clip is None else mask * clip * opacity
        box = _bbox(alpha)
        if box is None:
            return
        a = alpha[box][..., None]
        color = np.asarray(color) if not isinstance(color, str) else rgb(color)
        top = color[box] if color.ndim == 3 else rgb(color)
        self.line_rgb[box] = top * a + self.line_rgb[box] * (1.0 - a)
        self.line_alpha[box] = a[..., 0] + self.line_alpha[box] * (1.0 - a[..., 0])

    def outline(self, mask, width, color='#2a2030', weight_dir=(0.4, 1.0), weight_gain=0.45,
                wobble=0.12, opacity=1.0, clip=None, seed=None):
        """Trace a mask edge with a pen whose width varies.

        weight_dir: lines get heavier where the outward normal points this way
        (default: down-right, the side away from an upper-left light).
        wobble: fraction of random width variation, for a hand-drawn feel.
        """
        direction = np.asarray(weight_dir, np.float64)
        direction /= max(np.linalg.norm(direction), 1e-6)
        rng = np.random.default_rng(config.DEFAULT_SEED if seed is None else seed)
        strokes = []
        for line in raster.contours(mask):
            closed = np.vstack([line, line[:1]])
            closed = geometry.resample(closed, step=config.RIBBON_STEP_PX)
            normal = geometry.normals(closed)
            # findContours walks so that the left normal can face in or out;
            # orient it outward using the signed area.
            if cv2.contourArea(line.astype(np.float32), oriented=True) < 0:
                normal = -normal
            facing = normal @ direction
            noise = np.interp(np.linspace(0, 1, len(closed)),
                              np.linspace(0, 1, max(len(closed) // 40, 2) + 1),
                              rng.normal(0, wobble, max(len(closed) // 40, 2) + 1))
            half = 0.5 * width * np.clip(1.0 + weight_gain * facing + noise, 0.25, 2.0)
            strokes.append((closed, half))
        self.ink_mask(raster.ribbon_mask(self.size, strokes), color, opacity, clip)

    def paint_form(self, mask, color, light=(-0.55, -1.0), shadow=0.12, soft=1.2, line_width=2.5,
                   shadow_color=None, line_color=None, rim=0.0):
        """Fill + form shadow + outline in one call: the quickest way to add a solid object.

        shadow: crescent size as a fraction of the shape's smaller extent (0 = flat).
        rim: opacity of a thin light edge on the lit side (0 = none).
        """
        base = rgb(color)
        self.fill(mask, base)
        rows = np.flatnonzero(mask.max(axis=1) > 0.5)
        cols = np.flatnonzero(mask.max(axis=0) > 0.5)
        extent = min(rows.size, cols.size) if rows.size and cols.size else 0
        if shadow > 0 and extent:
            tone = shadow_of(base) if shadow_color is None else rgb(shadow_color)
            self.tint(shading.crescent(mask, light, shadow * extent, soft), tone, 'normal', 0.9)
        if rim > 0 and extent:
            self.tint(shading.rim(mask, light, max(0.03 * extent, 2.0), soft), light_of(base, 1.6), 'normal', rim)
        if line_width > 0:
            tone = adjust(base, lightness=-0.38, chroma=1.15) if line_color is None else rgb(line_color)
            self.outline(mask, line_width, tone, weight_dir=(-light[0], -light[1]))

    def paint_volume(self, mask, color, light=(-0.55, -1.0), bulge=None, depth=1.0, gloss=0.0,
                     shadow_color=None, light_color=None, line_width=0.0, line_color=None):
        """Fill a shape with soft rounded shading (shadow - base - light), as if modeled in paint.

        bulge: roundness radius in px (default: a third of the shape's smaller extent).
        depth: shadow strength. gloss: 0 matte .. 1 wet-looking specular spot.
        """
        base = rgb(color)
        rows = np.flatnonzero(mask.max(axis=1) > 0.5)
        cols = np.flatnonzero(mask.max(axis=0) > 0.5)
        if not (rows.size and cols.size):
            return
        if bulge is None:
            bulge = max(min(rows.size, cols.size) / 3.0, 2.0)
        lit = shading.volume(mask, light, bulge)
        dark = shadow_of(base, 1.2 * depth) if shadow_color is None else rgb(shadow_color)
        bright = light_of(base, 1.1) if light_color is None else rgb(light_color)
        deep = adjust(dark, lightness=-0.09 * depth)
        self.fill(mask, self.ramp(lit, (0.0, deep), (0.38, dark), (0.70, base), (1.0, bright)))
        if gloss > 0:
            self.tint(raster.smoothstep(lit, 0.90, 0.99) * mask, '#ffffff', 'screen', gloss)
        if line_width > 0:
            tone = adjust(base, lightness=-0.38, chroma=1.15) if line_color is None else rgb(line_color)
            self.outline(mask, line_width, tone, weight_dir=(-light[0], -light[1]))

    def paste(self, source, quad, opacity=1.0):
        """Place a flat picture into the scene in perspective.

        source: another Canvas, or an (H, W, 3) image. quad: its four corners on
        this canvas as (top-left, top-right, bottom-right, bottom-left).
        Draw anything flat (a facade, a sign, floor tiles) on its own canvas,
        then paste it onto a wall, a road or a table top. Returns the covered mask.
        """
        image = source.flatten() if isinstance(source, Canvas) else np.asarray(source, np.float32)
        height, width = image.shape[:2]
        corners = np.float32([(0, 0), (width, 0), (width, height), (0, height)])
        matrix = cv2.getPerspectiveTransform(corners, np.float32(quad))
        warped = cv2.warpPerspective(image, matrix, self.size, flags=cv2.INTER_AREA)
        cover = cv2.warpPerspective(np.ones((height, width), np.float32), matrix, self.size,
                                    flags=cv2.INTER_LINEAR)
        self.fill(cover, warped, opacity)
        return cover

    # --- coverage tracking ---------------------------------------------------
    def track(self, name):
        """Start recording the union of every fill() under `name`
        (e.g. the whole character, for rim light or background separation)."""
        self._tracking[name] = self.empty()

    def tracked(self, name, stop=True):
        mask = self._tracking.pop(name) if stop else self._tracking[name]
        return mask

    # --- output -------------------------------------------------------------
    def flatten(self, line_opacity=1.0):
        """Color layer with the line layer composited on top."""
        a = (self.line_alpha * line_opacity)[..., None]
        return np.clip(self.color * (1.0 - a) + self.line_rgb * line_opacity, 0.0, 1.0)

    def save(self, path, image=None):
        save_image(path, self.flatten() if image is None else image)


def save_image(path, image):
    data = (np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(data, cv2.COLOR_RGB2BGR)):
        raise IOError(f'could not write image: {path}')
