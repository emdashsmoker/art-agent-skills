"""Canvas: the structure buffers every medium paints from.

Why buffers: a painting separates WHAT is there
(local colour, form, edges, depth) from HOW it is painted (cel, watercolour, oil).
Scene code fills these buffers once; any medium can then render them.

Buffers (device pixels, float32 unless noted):
  albedo   local colour, before light
  normal   surface direction (x right, y down, z toward viewer)
  region   int16 id per pixel, names in Canvas.regions
  depth    0 near .. 1 far, drives atmosphere and shadow reach
  shadow   cast-shadow amount 0..1
  unlit    1 where colour is used as painted (sky, glow), 0 where light applies
  gloss    specular strength 0..1
  line_a / line_rgb   ink layer (coverage and colour)
  over     RGBA accents drawn after the medium (eye glints, sparks)
  group    uint8 id used to give layers different media (background vs figure)
  focus    0..1 where the picture needs its finest handling (a face): media add detail there
  occlusion  0..1 ambient occlusion: creases and contacts that stay dark whatever the light direction
  soft     0..1 soft translucent material (skin): wider terminator with a warm flush in it
"""
import contextlib

import cv2
import numpy as np
import skia

from . import geom

LINE_DARKEN = 0.34            # colour-traced line = local colour pushed toward dark
LINE_SATURATE = 1.25
SHADOW_DEPTH_REACH = 0.12     # a cast shadow only lands on layers this close in depth
INFLATE_PAD_LIMIT = 96


# ---------- colour ----------
def to_rgb(color):
    """'#rrggbb', (r, g, b) ints 0..255, or floats 0..1  ->  float32 array 0..1."""
    if isinstance(color, str):
        text = color.lstrip("#")
        return np.array([int(text[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    arr = np.asarray(color, np.float32)[:3]
    if all(isinstance(c, (int, np.integer)) for c in color[:3]) and arr.max() > 1:
        return arr / 255.0
    return arr


def luminance(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def saturate(rgb, amount):
    grey = luminance(rgb)[..., None]
    return np.clip(grey + (rgb - grey) * amount, 0, 1)


def mix(a, b, t):
    return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t


def trace_color(rgb):
    """Line colour derived from the local colour (anime 'colour trace')."""
    return saturate(np.asarray(rgb, np.float32) * LINE_DARKEN, LINE_SATURATE)


def shift_hue(rgb, degrees, sat=1.0, val=1.0):
    """Rotate hue of an RGB array/colour; used for shadow colours and palette variation."""
    arr = np.clip(np.asarray(rgb, np.float32), 0, 1)
    shaped = arr.reshape(-1, 1, 3)
    hsv = cv2.cvtColor(shaped, cv2.COLOR_RGB2HSV)
    hsv[..., 0] = (hsv[..., 0] + degrees) % 360
    hsv[..., 1] = np.clip(hsv[..., 1] * sat, 0, 1)
    hsv[..., 2] = np.clip(hsv[..., 2] * val, 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).reshape(arr.shape)


# ---------- noise ----------
def fractal_noise(height, width, scale, octaves=4, rng=None, persistence=0.5):
    """Smooth multi-octave noise in 0..1. `scale` is the largest feature size in pixels.

    Each octave is white noise generated at reduced size and upsampled: fast for big features.
    """
    rng = rng or np.random.default_rng(0)
    total = np.zeros((height, width), np.float32)
    amplitude, norm, feature = 1.0, 0.0, float(scale)
    for _ in range(octaves):
        step = max(feature / 2.0, 1.0)
        small_h, small_w = max(int(height / step) + 2, 2), max(int(width / step) + 2, 2)
        layer = rng.standard_normal((small_h, small_w)).astype(np.float32)
        layer = cv2.resize(layer, (width, height), interpolation=cv2.INTER_CUBIC)
        layer /= layer.std() + 1e-6
        total += amplitude * layer
        norm += amplitude
        amplitude *= persistence
        feature = max(feature * 0.5, 1.0)
    return np.clip(0.5 + 0.22 * total / norm * np.sqrt(octaves), 0.0, 1.0)


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


# ---------- fills ----------
class Gradient:
    """Linear or radial gradient fill in design units. stops: [(position 0..1, colour), ...] or colours."""

    def __init__(self, kind, a, b, stops):
        self.kind, self.a, self.b = kind, a, b
        if not isinstance(stops[0], (tuple, list)) or isinstance(stops[0][0], str) or len(stops[0]) == 3:
            stops = [(i / (len(stops) - 1), c) for i, c in enumerate(stops)]
        self.stops = stops

    @classmethod
    def linear(cls, p0, p1, stops):
        return cls("linear", p0, p1, stops)

    @classmethod
    def radial(cls, centre, radius, stops):
        return cls("radial", centre, radius, stops)

    def shader(self):
        colors = [_skia_color(to_rgb(c)) for _, c in self.stops]
        positions = [float(p) for p, _ in self.stops]
        if self.kind == "linear":
            return skia.GradientShader.MakeLinear(points=[tuple(self.a), tuple(self.b)], colors=colors,
                                                  positions=positions)
        return skia.GradientShader.MakeRadial(center=tuple(self.a), radius=float(self.b), colors=colors,
                                              positions=positions)


def _skia_color(rgb, alpha=1.0):
    r, g, b = (np.clip(rgb, 0, 1) * 255).astype(int)
    return skia.Color(int(r), int(g), int(b), int(round(alpha * 255)))


# ---------- canvas ----------
class Canvas:
    def __init__(self, width, height, scale=1.0, seed=0, paper="#ffffff"):
        self.width, self.height, self.scale = width, height, float(scale)
        self.W, self.H = int(round(width * scale)), int(round(height * scale))
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        shape = (self.H, self.W)
        self.albedo = np.ones(shape + (3,), np.float32) * to_rgb(paper)
        self.normal = np.zeros(shape + (3,), np.float32)
        self.normal[..., 2] = 1.0
        self.region = np.zeros(shape, np.int16)
        self.depth = np.ones(shape, np.float32)
        self.shadow = np.zeros(shape, np.float32)
        self.unlit = np.ones(shape, np.float32)
        self.gloss = np.zeros(shape, np.float32)
        self.line_a = np.zeros(shape, np.float32)
        self.line_rgb = np.zeros(shape + (3,), np.float32)
        self.over = np.zeros(shape + (4,), np.float32)
        self.group = np.zeros(shape, np.uint8)
        self.focus = np.zeros(shape, np.float32)
        self.occlusion = np.zeros(shape, np.float32)
        self.soft = np.zeros(shape, np.float32)
        self.regions = {"": 0}
        self.groups = {"background": 0}
        self.pen_depth, self.pen_group = 0.5, "background"
        self._scratch = np.zeros(shape + (4,), np.uint8)
        self._surface = skia.Surface(self._scratch)
        self._sk = self._surface.getCanvas()
        self._sk.scale(self.scale, self.scale)

    # ----- bookkeeping -----
    def region_id(self, name):
        if name not in self.regions:
            self.regions[name] = len(self.regions)
        return self.regions[name]

    def region_mask(self, *names):
        ids = [self.regions[n] for n in names if n in self.regions]
        return np.isin(self.region, ids)

    def group_id(self, name):
        if name not in self.groups:
            self.groups[name] = len(self.groups)
        return self.groups[name]

    @contextlib.contextmanager
    def layer(self, depth=None, group=None):
        """Everything added inside shares a scene depth (0 near .. 1 far) and a media group."""
        saved = (self.pen_depth, self.pen_group)
        self.pen_depth = saved[0] if depth is None else depth
        self.pen_group = saved[1] if group is None else group
        try:
            yield self
        finally:
            self.pen_depth, self.pen_group = saved

    def grid(self):
        """(xs, ys) design-unit coordinates of every device pixel, for numpy-built masks."""
        ys, xs = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        return xs / self.scale, ys / self.scale

    def noise(self, scale, octaves=4):
        return fractal_noise(self.H, self.W, scale * self.scale, octaves, self.rng)

    # ----- rasterising -----
    def _box(self, path, pad):
        bounds = path.computeTightBounds()
        x0 = int(np.floor(bounds.left() * self.scale - pad))
        y0 = int(np.floor(bounds.top() * self.scale - pad))
        x1 = int(np.ceil(bounds.right() * self.scale + pad))
        y1 = int(np.ceil(bounds.bottom() * self.scale + pad))
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, self.W), min(y1, self.H)
        if x1 <= x0 or y1 <= y0:
            return None
        return (slice(y0, y1), slice(x0, x1))

    def _raster(self, shape, fill, clip=None, stroke=None):
        """-> (alpha crop, rgb crop or constant, box). shape is a skia.Path or a full-frame mask."""
        if isinstance(shape, np.ndarray):
            ys, xs = np.nonzero(shape > 1e-3)
            if len(ys) == 0:
                return None, None, None
            box = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
            alpha = shape[box].astype(np.float32)
            if isinstance(clip, np.ndarray):
                alpha = alpha * clip[box]
            elif clip is not None:
                alpha = alpha * self.mask(clip)[box]
            if isinstance(fill, np.ndarray) and fill.ndim == 3:
                return alpha, fill[box].astype(np.float32), box
            return alpha, to_rgb(fill), box

        pad = 2 + (stroke or 0) * self.scale
        box = self._box(shape, pad)
        if box is None:
            return None, None, None
        self._scratch[box] = 0
        paint = skia.Paint(AntiAlias=True)
        is_gradient = isinstance(fill, Gradient)
        if is_gradient:
            paint.setShader(fill.shader())
        else:
            paint.setColor(skia.ColorWHITE)
        if stroke:
            paint.setStyle(skia.Paint.kStroke_Style)
            paint.setStrokeWidth(float(stroke))
            paint.setStrokeJoin(skia.Paint.kRound_Join)
            paint.setStrokeCap(skia.Paint.kRound_Cap)
        self._sk.save()
        if clip is not None and not isinstance(clip, np.ndarray):
            self._sk.clipPath(clip, skia.ClipOp.kIntersect, True)
        self._sk.drawPath(shape, paint)
        self._sk.restore()
        pixels = self._scratch[box].astype(np.float32) / 255.0
        alpha = pixels[..., 3].copy()
        if isinstance(clip, np.ndarray):
            alpha *= clip[box]
        if is_gradient:
            rgb = pixels[..., :3] / np.maximum(pixels[..., 3:4], 1e-3)   # un-premultiply
        elif isinstance(fill, np.ndarray) and fill.ndim == 3:
            rgb = fill[box].astype(np.float32)
        else:
            rgb = to_rgb(fill)
        return alpha, rgb, box

    def mask(self, shape, clip=None):
        """Full-frame coverage mask (0..1) of a path."""
        if isinstance(shape, np.ndarray):
            return shape
        full = np.zeros((self.H, self.W), np.float32)
        alpha, _, box = self._raster(shape, "#ffffff", clip)
        if alpha is not None:
            full[box] = alpha
        return full

    # ----- form -----
    def _inflate(self, solid, bulge, relief):
        """Normals of a pillow-like relief raised from a silhouette (Lumo-style inflation)."""
        if min(solid.shape) < 3:            # a sliver clipped by the frame edge: too thin to have a form
            flat = np.zeros(solid.shape + (3,), np.float32)
            flat[..., 2] = 1.0
            return flat
        guess = int(min(max(solid.shape) // 2, INFLATE_PAD_LIMIT))
        pad = int(min((bulge * self.scale) if bulge else guess, INFLATE_PAD_LIMIT)) + 2
        padded = cv2.copyMakeBorder(solid.astype(np.uint8), pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        dist = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[pad:-pad, pad:-pad]
        radius = (bulge * self.scale) if bulge else max(float(dist.max()), 1.0)
        t = np.clip(dist / radius, 0, 1)
        height = radius * np.sqrt(np.clip(1 - (1 - t) ** 2, 0, 1)) * relief
        height = cv2.GaussianBlur(height, (0, 0), max(1.0, radius * 0.14))
        return normals_from_height(height)

    # ----- drawing -----
    def add(self, shape, fill="#808080", region=None, *, form="flat", bulge=None, relief=1.0,
            normal=None, unlit=False, gloss=0.0, cast=None, outline=None, clip=None, alpha=1.0,
            depth=None, group=None, keep_normal=0.0, soft=0.0):
        """Lay down one opaque shape: local colour + form + optional cast shadow and outline.

        form    'flat' | 'round' (inflated relief). bulge = bevel radius in design units
                (None = fully domed). relief scales the steepness.
        normal  explicit (nx, ny, nz) for planes such as box faces, or a full-frame HxWx3 normal map.
        cast    (dx, dy, blur, strength): drop a shadow onto nearby layers below.
        outline width, or (width, colour). Colour None = traced from the fill.
        keep_normal  0..1: how much of the form already underneath shows through this shape's own form
                     (a lock of hair lying on the skull keeps the skull's roundness).
        """
        a, rgb, box = self._raster(shape, fill, clip)
        if a is None:
            return None
        depth = self.pen_depth if depth is None else depth
        if cast:
            self._cast(a, box, depth, *cast)
        a = a * alpha
        a3 = a[..., None]
        self.albedo[box] = self.albedo[box] * (1 - a3) + rgb * a3
        solid = a > 0.5
        if region is not None:
            self.region[box][solid] = self.region_id(region)
        if isinstance(normal, np.ndarray) and normal.ndim == 3:        # per-pixel normals (terrain, cloth)
            n = normal[box]
        elif normal is not None:
            n = np.broadcast_to(np.asarray(normal, np.float32) / np.linalg.norm(normal), a.shape + (3,))
        elif form == "round":
            n = self._inflate(solid, bulge, relief)
        else:
            n = np.broadcast_to(np.array([0, 0, 1], np.float32), a.shape + (3,))
        if keep_normal:
            n = n * (1 - keep_normal) + self.normal[box] * keep_normal
        self.normal[box] = self.normal[box] * (1 - a3) + n * a3
        self.depth[box][solid] = depth
        self.group[box][solid] = self.group_id(self.pen_group if group is None else group)
        self.unlit[box] = self.unlit[box] * (1 - a) + (1.0 if unlit else 0.0) * a
        self.gloss[box] = self.gloss[box] * (1 - a) + gloss * a
        if not keep_normal:                        # a decal on a form keeps that form's material and creases
            self.soft[box] = self.soft[box] * (1 - a) + soft * a
            self.occlusion[box] *= 1 - a
        self.shadow[box] *= 1 - a
        self.line_a[box] *= 1 - a
        self.over[box] *= (1 - a)[..., None]
        if outline:
            width, color = outline if isinstance(outline, (tuple, list)) else (outline, None)
            if color is None:
                mean = rgb if np.ndim(rgb) == 1 else (rgb * a3).sum((0, 1)) / max(a.sum(), 1e-6)
                color = trace_color(mean)
            self.ink(shape, color, stroke=width, clip=clip)
        return box

    def _cast(self, alpha, box, depth, dx, dy, blur=0.0, strength=1.0):
        full = np.zeros((self.H, self.W), np.float32)
        full[box] = alpha
        shift = np.float32([[1, 0, dx * self.scale], [0, 1, dy * self.scale]])
        moved = cv2.warpAffine(full, shift, (self.W, self.H))
        if blur:
            moved = cv2.GaussianBlur(moved, (0, 0), blur * self.scale)
        reachable = np.abs(self.depth - depth) < SHADOW_DEPTH_REACH
        self.shadow = np.maximum(self.shadow, moved * strength * reachable)

    def shade(self, shape, amount=1.0, blur=0.0, clip=None):
        """Paint a designed shadow shape straight into the shadow buffer."""
        m = self.mask(shape, clip) if not isinstance(shape, np.ndarray) else shape
        if blur:
            m = cv2.GaussianBlur(m, (0, 0), blur * self.scale)
            if isinstance(clip, np.ndarray):
                m = m * clip
        self.shadow = np.maximum(self.shadow, m * amount)

    def occlude(self, shape, amount=1.0, blur=0.0, clip=None):
        """Darken a crease or contact regardless of light direction (under a lip, where a vase meets the table)."""
        m = self.mask(shape, clip) if not isinstance(shape, np.ndarray) else shape
        if blur:
            m = cv2.GaussianBlur(m, (0, 0), blur * self.scale)
            if isinstance(clip, np.ndarray):
                m = m * clip
        self.occlusion = np.maximum(self.occlusion, m * amount)

    def tint(self, shape, color, alpha=1.0, blur=0.0, clip=None):
        """Change local colour only (blush, lip colour, soft gradients). Form and region stay."""
        a, rgb, box = self._raster(shape, color, clip)
        if a is None:
            return
        if blur:
            full = np.zeros((self.H, self.W), np.float32)
            full[box] = a
            full = cv2.GaussianBlur(full, (0, 0), blur * self.scale)
            if isinstance(clip, np.ndarray):
                full *= clip
            elif clip is not None:
                full *= self.mask(clip)
            a3 = (full * alpha)[..., None]
            self.albedo = self.albedo * (1 - a3) + to_rgb(color) * a3
            return
        a3 = (a * alpha)[..., None]
        self.albedo[box] = self.albedo[box] * (1 - a3) + rgb * a3

    def focus_on(self, shape, amount=1.0, blur=0.0):
        """Mark where the viewer should look. Media spend their finest strokes and crispest edges here."""
        m = self.mask(shape)
        if blur:
            m = cv2.GaussianBlur(m, (0, 0), blur * self.scale)
        self.focus = np.maximum(self.focus, m * amount)

    def ink(self, shape, color="#201418", stroke=None, alpha=1.0, clip=None):
        """Add to the line layer: a filled shape (tapered stroke path) or a stroked outline."""
        a, _, box = self._raster(shape, "#ffffff", clip, stroke=stroke)
        if a is None:
            return
        a = a * alpha
        a3 = a[..., None]
        self.line_rgb[box] = self.line_rgb[box] * (1 - a3) + to_rgb(color) * a3
        self.line_a[box] = 1 - (1 - self.line_a[box]) * (1 - a)

    def stroke(self, points, width, color="#201418", start=0.0, end=0.0, peak=0.5, alpha=1.0, clip=None):
        """Tapered pen line through points."""
        self.ink(geom.taper(points, width, start, end, peak), color, alpha=alpha, clip=clip)

    def accent(self, shape, color="#ffffff", alpha=1.0, clip=None, blur=0.0):
        """Final-pass accent kept crisp over any medium (eye glints, sparkles, rim flecks)."""
        a, rgb, box = self._raster(shape, color, clip)
        if a is None:
            return
        if blur:
            full = np.zeros((self.H, self.W), np.float32)
            full[box] = a
            a = cv2.GaussianBlur(full, (0, 0), blur * self.scale)
            box = (slice(0, self.H), slice(0, self.W))
        a = a * alpha
        rgb = np.broadcast_to(rgb, a.shape + (3,))
        self.over[box][..., :3] = self.over[box][..., :3] * (1 - a[..., None]) + rgb * a[..., None]
        self.over[box][..., 3] = 1 - (1 - self.over[box][..., 3]) * (1 - a)

    def add_buffers(self, alpha, rgb, normal=None, region=None, gloss=None, unlit=0.0,
                    depth=None, group=None, line_a=None, line_rgb=None, cast=None, soft=None, occlusion=None):
        """Composite a pre-rendered layer (a figure, a relief object). All arrays full-frame."""
        depth = self.pen_depth if depth is None else depth
        box = (slice(0, self.H), slice(0, self.W))
        if cast:
            self._cast(alpha, box, depth, *cast)
        a3 = alpha[..., None]
        solid = alpha > 0.5
        self.albedo = self.albedo * (1 - a3) + rgb * a3
        if normal is not None:
            self.normal = self.normal * (1 - a3) + normal * a3
        if region is not None:
            self.region[solid] = region[solid]
        self.depth[solid] = depth
        self.group[solid] = self.group_id(self.pen_group if group is None else group)
        self.unlit = self.unlit * (1 - alpha) + unlit * alpha
        self.gloss = self.gloss * (1 - alpha) + (0.0 if gloss is None else gloss) * alpha
        self.soft = self.soft * (1 - alpha) + (0.0 if soft is None else soft) * alpha
        self.occlusion = self.occlusion * (1 - alpha) + (0.0 if occlusion is None else occlusion) * alpha
        self.shadow *= 1 - alpha
        self.line_a *= 1 - alpha
        self.over *= (1 - alpha)[..., None]
        if line_a is not None:
            l3 = line_a[..., None]
            self.line_rgb = self.line_rgb * (1 - l3) + line_rgb * l3
            self.line_a = 1 - (1 - self.line_a) * (1 - line_a)


def normals_from_height(height, strength=1.0):
    gy, gx = np.gradient(height.astype(np.float32))
    n = np.dstack([-gx * strength, -gy * strength, np.ones_like(height, dtype=np.float32)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


# ---------- light ----------
class Light:
    """One key light plus ambient. azimuth: -90 left .. 0 front .. 90 right; elevation: 90 = overhead."""

    def __init__(self, azimuth=-40, elevation=40, color="#fff6ea", shadow_tint="#8c8fb4",
                 wrap=0.15, shadow_strength=1.0, haze="#c9d6e4", haze_strength=0.0, rim=0.0,
                 bounce=0.3, bounce_color="#ffd9b8", flush=0.5):
        az, el = np.radians(azimuth), np.radians(elevation)
        self.direction = np.array([np.sin(az) * np.cos(el), -np.sin(el), np.cos(az) * np.cos(el)], np.float32)
        self.color, self.shadow_tint = to_rgb(color), to_rgb(shadow_tint)
        self.wrap, self.shadow_strength = wrap, shadow_strength
        self.haze, self.haze_strength, self.rim = to_rgb(haze), haze_strength, rim
        # bounce: light reflected back into the shadow side (keeps the core shadow darkest at the terminator)
        # flush:  warm glow inside the terminator of soft materials such as skin
        self.bounce, self.bounce_color, self.flush = bounce, to_rgb(bounce_color), flush


def _unit_normals(canvas):
    return canvas.normal / (np.linalg.norm(canvas.normal, axis=2, keepdims=True) + 1e-6)


def lightness(canvas, light):
    """Scalar illumination 0..1 per pixel: form shading times cast shadow and occlusion; 1 where unlit."""
    n = _unit_normals(canvas)
    wrap = light.wrap + 0.3 * canvas.soft                       # soft materials let light creep round the form
    lambert = (n @ light.direction + wrap) / (1 + wrap)
    lit = np.clip(lambert, 0, 1) * (1 - canvas.shadow * light.shadow_strength) * (1 - 0.55 * canvas.occlusion)
    return lit * (1 - canvas.unlit) + canvas.unlit


def reference(canvas, light, lit=None):
    """Smooth 'what a realist would aim for' render: the target every medium interprets.

    Light side, halftone, core shadow, reflected light and occlusion are all present, because
    that sequence of tones is what makes a form read as round.
    """
    n = _unit_normals(canvas)
    lit = lightness(canvas, light) if lit is None else lit
    tone = smoothstep(0.0, 1.0, lit)[..., None]
    away = np.clip(-(n @ light.direction), 0, 1)                 # how squarely a surface faces away from the key
    down = np.clip(n[..., 1], 0, 1)                              # surfaces facing the ground pick up its warmth
    reflected = light.bounce * (0.75 * away + 0.5 * down) * (1 - canvas.occlusion)
    shadow_side = canvas.albedo * (light.shadow_tint + reflected[..., None] * light.bounce_color * 0.6)
    shadow_side = shadow_side * (1 - 0.45 * canvas.occlusion)[..., None]
    lit_side = canvas.albedo * light.color
    color = shadow_side * (1 - tone) + lit_side * tone
    if light.flush and canvas.soft.max() > 0:                     # blood under the skin shows where light grazes it
        band = np.exp(-((lit - 0.34) / 0.2) ** 2) * canvas.soft * light.flush * (1 - canvas.shadow)
        color = color * (1 + band[..., None] * np.array([0.22, -0.02, -0.08], np.float32))
    unlit = canvas.unlit[..., None]
    color = color * (1 - unlit) + canvas.albedo * unlit
    if canvas.gloss.max() > 0:
        half = light.direction + np.array([0, 0, 1], np.float32)
        half /= np.linalg.norm(half)
        facing = np.clip(n @ half, 0, 1)
        spec = (facing ** 60 + 0.35 * facing ** 12) * canvas.gloss * (1 - canvas.shadow) * (1 - canvas.unlit)
        color = color + spec[..., None] * light.color
    if light.rim:
        rim = np.clip(1 - n[..., 2], 0, 1) ** 3 * light.rim * (1 - canvas.unlit)
        color = color + rim[..., None] * light.color
    if light.haze_strength:
        fog = (np.clip(canvas.depth, 0, 1) ** 1.5 * light.haze_strength)[..., None]
        color = color * (1 - fog) + light.haze * fog
    return np.clip(color, 0, 1)


def composite_lines(image, canvas, mode="trace", strength=1.0):
    """Lay the ink layer over a rendered image. mode: trace | black | sepia | none."""
    if mode == "none":
        return image
    rgb = canvas.line_rgb
    if mode == "black":
        rgb = np.zeros_like(rgb) + 0.06
    elif mode == "sepia":
        rgb = np.zeros_like(rgb) + to_rgb("#3a2a20")
    a = np.clip(canvas.line_a * strength, 0, 1)[..., None]
    return image * (1 - a) + rgb * a


def composite_over(image, canvas):
    # The accent buffer holds premultiplied colour (accent() and the erases scale colour and alpha together),
    # so its colour is added as is; multiplying by alpha again would square every soft edge and glow.
    a = canvas.over[..., 3:4]
    return image * (1 - a) + canvas.over[..., :3]


def save(image, path):
    rgb = (np.clip(image, 0, 1) * 255 + 0.5).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return path
