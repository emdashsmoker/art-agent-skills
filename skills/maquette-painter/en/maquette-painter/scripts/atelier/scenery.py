"""Scenery: sky, terrain, water, vegetation and perspective construction for landscapes and settings.

Everything is laid in back to front with a scene depth (1 far .. 0 near). Depth drives aerial
perspective (Light haze) and wet-in-wet softness in watercolour, so far layers recede by themselves.
"""
import cv2
import numpy as np

from . import geom
from .core import Gradient, to_rgb, fractal_noise, smoothstep, normals_from_height


def _rng(canvas, seed):
    return canvas.rng if seed is None else np.random.default_rng(seed)


def sky(canvas, zenith="#4f86c6", horizon="#d6e6f2", horizon_y=None, glow=None, glow_color="#ffd9a0"):
    """Graded sky down to horizon_y. glow=(x, y, radius) adds a sun/moon haze."""
    horizon_y = canvas.height * 0.6 if horizon_y is None else horizon_y
    with canvas.layer(depth=1.0):
        canvas.add(geom.rect(0, 0, canvas.width, canvas.height),
                   Gradient.linear((0, 0), (0, horizon_y), [zenith, horizon]), "sky", unlit=True)
    if glow:
        x, y, radius = glow
        canvas.tint(geom.ellipse(x, y, radius), glow_color, alpha=0.75, blur=radius * 0.45)


def sun(canvas, x, y, radius, color="#fff4d6"):
    with canvas.layer(depth=1.0):
        canvas.add(geom.ellipse(x, y, radius), color, "sun", unlit=True)


def clouds(canvas, cover=0.4, y0=0.0, y1=None, color="#ffffff", shadow="#9fb2c8", scale=180.0, seed=None,
           depth=0.97, wispy=0.0, volume=0.4):
    """Cumulus-like cloud field between y0 and y1 (design units). cover 0..1; wispy stretches them flat.

    Each cloud is a lumpy dome lit by the scene light: billowed tops catch the sun, flat grey bases sit
    in their own shade. volume 0 gives flat graphic clouds.
    """
    rng = _rng(canvas, seed)
    y1 = canvas.height * 0.5 if y1 is None else y1
    s = canvas.scale
    stretch = 2.2 + 3.0 * wispy
    small = fractal_noise(canvas.H, int(canvas.W / stretch) + 2, scale * s / stretch, 5, rng)
    field = cv2.resize(small, (canvas.W, canvas.H), interpolation=cv2.INTER_CUBIC)
    billow = fractal_noise(canvas.H, canvas.W, scale * s * 0.22, 3, rng)
    xs, ys = canvas.grid()
    band = smoothstep(y1, y1 - (y1 - y0) * 0.45, ys) * smoothstep(y0 - 1, y0 + (y1 - y0) * 0.1, ys)
    mask = smoothstep(1 - cover - 0.03, 1 - cover + 0.12, field * (0.55 + 0.45 * band)) * band
    # Bases are flat: density is cut off sharply below each cloud's centre of mass.
    under = np.roll(field, int(-scale * s * 0.12), axis=0)
    lift = cv2.GaussianBlur(field - under, (0, 0), scale * s * 0.05)
    base = np.maximum(smoothstep(-0.06, 0.06, lift + 0.02), 1 - mask)                # thin edges stay light
    shade = (1 - base) * 0.65                                                        # undersides grey, never ink-dark
    tone = to_rgb(shadow)[None, None, :] * shade[..., None] + to_rgb(color)[None, None, :] * (1 - shade[..., None])
    height = cv2.GaussianBlur(mask * (0.75 + 0.5 * billow), (0, 0), scale * s * 0.06) * scale * s * 0.1
    normal = None
    if volume:          # the dome is modelled where the cloud is dense; wisps face the viewer and stay bright
        normal = normals_from_height(height, volume)
        normal = normal * mask[..., None] + np.array([0, 0, 1], np.float32) * (1 - mask[..., None])
    with canvas.layer(depth=depth):          # soft: light wraps deep into a cloud, as it scatters inside
        canvas.add(mask.astype(np.float32), tone.astype(np.float32), "cloud", normal=normal, unlit=not volume, soft=1.0)


def stars(canvas, count=260, y1=None, seed=None):
    rng = _rng(canvas, seed)
    y1 = canvas.height * 0.55 if y1 is None else y1
    for _ in range(count):
        x, y = rng.uniform(0, canvas.width), rng.uniform(0, y1) ** 1.0
        r = rng.choice([0.6, 0.8, 1.0, 1.6], p=[0.5, 0.3, 0.15, 0.05])
        canvas.accent(geom.ellipse(x, y, r), "#ffffff", alpha=rng.uniform(0.4, 1.0))


def _ridge(canvas, base_y, peak, roughness, rng, feature):
    xs = np.arange(canvas.W, dtype=np.float32) / canvas.scale
    line = np.zeros(canvas.W, np.float32)
    amplitude, frequency, total = 1.0, 1.0 / feature, 0.0
    for _ in range(6):
        line += amplitude * np.sin(xs * frequency * 2 * np.pi + rng.uniform(0, 2 * np.pi))
        total += amplitude
        amplitude *= 0.35 + 0.3 * roughness
        frequency *= 2.07
    line = line / total * 0.5 + 0.5
    return base_y - peak * line


def _noise1d(xs, period, rng):
    """Smooth value noise 0..1 along x with the given feature size."""
    count = int(xs.max() / period) + 4
    values = rng.random(count)
    i = np.floor(xs / period).astype(int)
    t = xs / period - i
    t = t * t * (3 - 2 * t)
    return values[i] * (1 - t) + values[i + 1] * t


def _peaks(canvas, base_y, peak, roughness, rng, feature):
    """Ridge line of a mountain range: ridged noise gives sharp summits and saddles, unlike rolling hills."""
    xs = np.arange(canvas.W, dtype=np.float32) / canvas.scale
    line = np.zeros(canvas.W, np.float32)
    amplitude, period, total = 1.0, feature * 0.55, 0.0
    for octave in range(6):
        ridged = 1 - np.abs(2 * _noise1d(xs, period, rng) - 1)
        line += amplitude * ridged ** (1.6 if octave == 0 else 1.0)
        total += amplitude
        amplitude *= 0.38 + 0.25 * roughness
        period /= 2.15
    line = (line - line.min()) / (line.max() - line.min() + 1e-6)
    return base_y - peak * (0.12 + 0.88 * line)


def mountains(canvas, base_y, peak, color="#6f7fa6", depth=0.85, roughness=0.6, feature=None, seed=None,
              snow=None, snow_color="#f4f6fa", facets=1.0, region="mountain", forest=None, forest_color="#4a5e48",
              shape="alpine"):
    """A mountain range whose ridge rises up to `peak` above base_y.

    The faces are a height field carved by ridged noise stretched down the fall line, so spurs and
    gullies run from the summits; the scene light then models lit faces and shadowed flanks.
    facets  strength of the carved planes (0 = flat silhouette, for far ranges or prints)
    snow    design-unit y above which upward-facing slopes hold snow; steep rock stays bare
    forest  design-unit y below which the lower slopes are wooded (forest_color)
    shape   'alpine' (sharp summits and saddles) or 'rounded' (dome-like peaks of East Asian ink landscapes)
    """
    rng = _rng(canvas, seed)
    feature = feature or canvas.width * 0.9
    s = canvas.scale
    outline = _peaks if shape == "alpine" else _ridge
    ridge = outline(canvas, base_y, peak, roughness, rng, feature) * s
    ys = np.arange(canvas.H, dtype=np.float32)[:, None] * np.ones((1, canvas.W), np.float32)
    mask = np.clip(ys - ridge[None, :] + 0.5, 0, 1)
    span = peak * s
    below = np.clip(ys - ridge[None, :], 0, None)
    stretched = fractal_noise(max(int(canvas.H / 2.2), 4), canvas.W, span * 0.5, 6, rng, persistence=0.55)
    carve = 1 - np.abs(2 * cv2.resize(stretched, (canvas.W, canvas.H), interpolation=cv2.INTER_CUBIC) - 1)
    near_crest = 0.35 + 0.65 * np.exp(-below / (0.7 * span))
    surface = below * 0.55 + carve * span * 0.32 * near_crest          # z toward the viewer: faces tilt up
    surface = cv2.GaussianBlur(surface, (0, 0), 0.8 * s)
    normal = normals_from_height(surface, facets) if facets else None
    variation = fractal_noise(canvas.H, canvas.W, span * 0.15, 3, rng) - 0.5
    rgb = np.clip(to_rgb(color)[None, None, :] * (1 + 0.18 * variation[..., None]), 0, 1).astype(np.float32)
    if forest is not None:
        ragged = (fractal_noise(canvas.H, canvas.W, span * 0.12, 3, rng) - 0.5) * span * 0.5
        wood = smoothstep(forest * s - 4 * s + ragged, forest * s + 4 * s + ragged, ys)
        rgb = rgb * (1 - wood[..., None]) + to_rgb(forest_color) * wood[..., None]
    if snow is not None and normal is not None:
        ragged = (fractal_noise(canvas.H, canvas.W, span * 0.18, 4, rng) - 0.5) * span * 0.5
        high = smoothstep(snow * s + ragged + 3 * s, snow * s + ragged - 3 * s, ys)
        settles = smoothstep(0.05, 0.35, -normal[..., 1]) * smoothstep(0.85, 0.55, np.abs(normal[..., 0]))
        cap = high * settles
        rgb = rgb * (1 - cap[..., None]) + to_rgb(snow_color) * cap[..., None]
    elif snow is not None:
        ragged = fractal_noise(canvas.H, canvas.W, span * 0.2, 4, rng) - 0.5
        line = snow * s + ragged * span * 0.6
        cap = smoothstep(line + 3, line - 3, ys)
        rgb = rgb * (1 - cap[..., None]) + to_rgb(snow_color) * cap[..., None]
    with canvas.layer(depth=depth):
        canvas.add(mask.astype(np.float32), rgb, region, normal=normal)
        if facets:          # gullies hold shadow whatever the light
            valley = np.clip((cv2.GaussianBlur(surface, (0, 0), span * 0.04) - surface) / (span * 0.03), 0, 1)
            canvas.occlude(valley * mask * 0.6 * facets)
    return ridge / s


def hills(canvas, base_y, rise, color="#6f9a5a", depth=0.6, seed=None, feature=None, region="hill", texture=0.4):
    """Soft rolling ground rising up to `rise` above base_y; lit as a gently curved surface."""
    rng = _rng(canvas, seed)
    ridge = _ridge(canvas, base_y, rise, 0.25, rng, feature or canvas.width * 1.3) * canvas.scale
    ys = np.arange(canvas.H, dtype=np.float32)[:, None]
    mask = np.clip(ys - ridge[None, :] + 0.5, 0, 1)
    s = canvas.scale
    bumps = fractal_noise(canvas.H, canvas.W, rise * 1.2 * s, 4, rng) * rise * s * 0.35
    height = bumps - (ys - ridge[None, :]) * 0.55
    normal = normals_from_height(cv2.GaussianBlur(height, (0, 0), 6.0 * s), 0.6)
    variation = (fractal_noise(canvas.H, canvas.W, 40 * s, 3, rng) - 0.5) * texture * 0.3
    rgb = np.clip(to_rgb(color)[None, None, :] * (1 + variation[..., None]), 0, 1).astype(np.float32)
    with canvas.layer(depth=depth):
        canvas.add(mask.astype(np.float32), rgb, region, normal=normal)
    return ridge / canvas.scale


def ground(canvas, y, color="#8fae6a", far_color=None, depth=0.4, region="ground"):
    """Flat ground plane from y to the bottom edge, optionally graded toward a far colour."""
    fill = Gradient.linear((0, y), (0, canvas.height), [far_color, color]) if far_color else color
    with canvas.layer(depth=depth):
        canvas.add(geom.rect(0, y, canvas.width, canvas.height), fill, region, normal=(0, -0.75, 0.66))


def water(canvas, y0, y1=None, color="#5d8fb4", reflect=0.6, ripples=0.5, depth=0.5, seed=None, region="water",
          light=None, glitter=None):
    """Still water from y0 down to y1. Mirrors whatever is already painted above y0.

    light    the scene Light: reflections then show the shaded scene, not flat local colour
    glitter  (x, width) of a sun path broken into sparkling ripples
    Ripples grow toward the viewer, and the reflection fades into the water body there (Fresnel).
    """
    rng = _rng(canvas, seed)
    y1 = canvas.height if y1 is None else y1
    s = canvas.scale
    r0, r1 = int(y0 * s), int(min(y1 * s, canvas.H))
    span = r1 - r0
    if span <= 0:
        return
    if light is not None:
        from .core import reference
        scene = reference(canvas, light)
    else:
        scene = canvas.albedo
    source = scene[max(r0 - span, 0):r0][::-1]
    mirror = cv2.resize(source, (canvas.W, span), interpolation=cv2.INTER_AREA) if source.shape[0] != span else source.copy()
    near = np.linspace(0.0, 1.0, span, dtype=np.float32)                    # 0 at the far shore, 1 at the bottom
    gx, gy = np.meshgrid(np.arange(canvas.W, dtype=np.float32), np.arange(span, dtype=np.float32))
    # Ripple bands: thin and dense far away, wider and stronger near the viewer.
    wave_rows = fractal_noise(span, max(canvas.W // 40, 4), 6 * s, 3, rng)
    wave_rows = cv2.resize(wave_rows, (canvas.W, span), interpolation=cv2.INTER_CUBIC) - 0.5
    strength = (0.2 + 2.5 * near ** 1.5)[:, None] * ripples
    mirror = cv2.remap(mirror.astype(np.float32), (gx + wave_rows * 18 * s * strength).astype(np.float32),
                       (gy + wave_rows * 3 * s * strength).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    mirror = cv2.GaussianBlur(mirror, (0, 0), sigmaX=0.6 * s, sigmaY=1.2 * s)
    fresnel = (reflect * (1 - 0.55 * near))[:, None, None]
    body = to_rgb(color)[None, None, :] * (0.8 + 0.2 * (1 - near))[:, None, None]
    rgb = mirror * fresnel + body * (1 - fresnel)
    if ripples:             # light and dark ripple edges
        crest = np.clip(wave_rows * 6, -1, 1) * (0.04 + 0.12 * near[:, None]) * ripples
        rgb = rgb * (1 + crest[..., None])
    if glitter is not None:
        gx0, width = glitter
        across = np.exp(-((gx / s - gx0) / (width * (0.4 + 0.8 * near[:, None]))) ** 2)
        sparkle = (rng.random((span, canvas.W)) > 0.93).astype(np.float32)
        sparkle = cv2.GaussianBlur(sparkle, (0, 0), sigmaX=3 * s, sigmaY=0.5 * s) * 5
        rgb = rgb + np.clip(sparkle * across, 0, 1)[..., None] * (1 - rgb) * 0.9
    shore = np.exp(-(np.arange(span, dtype=np.float32) / (1.5 * s)) ** 2)[:, None, None]
    rgb = rgb * (1 - 0.25 * shore) + 0.25 * shore * np.clip(body * 1.4, 0, 1)
    full_rgb = np.zeros((canvas.H, canvas.W, 3), np.float32)
    full_rgb[r0:r1] = np.clip(rgb, 0, 1)
    mask = np.zeros((canvas.H, canvas.W), np.float32)
    mask[r0:r1] = 1.0
    with canvas.layer(depth=depth):
        canvas.add(mask, full_rgb, region, unlit=True)


def treeline(canvas, base_y, height, color="#3f6650", depth=0.7, density=1.0, seed=None, region="trees", conifer=True):
    """Distant forest edge: a mass of spires (conifer) or rounded crowns of varied height and tone."""
    rng = _rng(canvas, seed)
    s = canvas.scale
    mask = np.zeros((canvas.H, canvas.W), np.uint8)
    count = int(canvas.width / (height * 0.28) * density)
    for _ in range(count):
        x = rng.uniform(-height, canvas.width + height)
        h = height * rng.lognormal(-0.25, 0.3)
        spire = conifer and rng.random() < 0.85
        if spire:
            w = h * rng.uniform(0.14, 0.24)
            left = [(x - w * f, base_y - h * (1 - f) + rng.uniform(-0.04, 0.04) * h) for f in (0.2, 0.45, 0.7, 1.0)]
            right = [(x + w * f, base_y - h * (1 - f) + rng.uniform(-0.04, 0.04) * h) for f in (1.0, 0.7, 0.45, 0.2)]
            pts = np.array([(x, base_y - h)] + right[::-1][::-1] + [(x + w, base_y + 2), (x - w, base_y + 2)] + left[::-1]) * s
            cv2.fillPoly(mask, [pts.astype(np.int32)], 255, lineType=cv2.LINE_AA)
        else:
            w = h * rng.uniform(0.4, 0.7)
            for _ in range(3):
                cx, cy = x + rng.uniform(-0.3, 0.3) * w, base_y - h * rng.uniform(0.45, 0.7)
                cv2.ellipse(mask, (int(cx * s), int(cy * s)), (int(w * 0.6 * s), int(h * 0.38 * s)), 0, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.rectangle(mask, (0, int((base_y - height * 0.15) * s)), (canvas.W, int((base_y + height * 0.1) * s)), 255, -1)
    tone = 1 + 0.18 * (fractal_noise(canvas.H, canvas.W, height * 0.6 * s, 2, rng)[..., None] - 0.5)
    rgb = np.clip(to_rgb(color)[None, None, :] * tone, 0, 1).astype(np.float32)
    with canvas.layer(depth=depth):
        canvas.add(mask.astype(np.float32) / 255.0, rgb, region, form="round", bulge=height * 0.15, relief=0.6)


BIRCH_BARK = "#e4e2dc"       # chalk-white birch bark; its twigs stay dark
BIRCH_MARK = "#2a2624"       # the black lenticel dashes and the dark base of an old birch


def bare_tree(canvas, x, base_y, height, bark="#3a3430", depth=0.4, seed=None, spread=0.5, lean=0.0, birch=False,
              twig=None, region="tree"):
    """A leafless winter tree: a tapering trunk forking into boughs, the boughs into ever finer twigs.

    birch  white bark with black dashes; the trunk keeps its white high up and the twigs are dark
    spread crown width as a share of the height; lean tilts the trunk (fraction of height, + to the right)
    Twigs are drawn as one mask, so a tree costs one layer however fine it gets.
    """
    rng = _rng(canvas, seed)
    s = canvas.scale
    trunk_rgb = to_rgb(BIRCH_BARK if birch else bark)
    twig_rgb = to_rgb(twig if twig is not None else ("#3a2c28" if birch else bark))
    top = (x + lean * height, base_y - height * 0.97)
    mid = (x + lean * height * 0.45 + rng.uniform(-1, 1) * height * 0.02, base_y - height * 0.5)
    trunk_w = height * 0.032
    boughs = np.zeros((canvas.H, canvas.W), np.uint8)       # the first forks keep the bark colour of the trunk
    twigs = np.zeros((canvas.H, canvas.W), np.uint8)

    def limb(start, angle, length, width, level):
        """One bough: a slightly bent line, then two or three thinner, shorter forks from its far half."""
        bend = rng.uniform(-0.2, 0.2)
        a1 = angle + bend
        end = (start[0] + np.cos(a1) * length, start[1] - np.sin(a1) * length)
        knee = (start[0] + np.cos(angle) * length * 0.5, start[1] - np.sin(angle) * length * 0.5)
        mask = boughs if level == 1 else twigs
        for a, b in ((start, knee), (knee, end)):
            cv2.line(mask, (int(a[0] * s), int(a[1] * s)), (int(b[0] * s), int(b[1] * s)), 255,
                     max(int(round(width * s)), 1), cv2.LINE_AA)
        if level >= 5 or length < height * 0.015:
            return
        for _ in range(int(rng.integers(2, 4))):
            t = rng.uniform(0.4, 1.0)
            fork = (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)
            turn = rng.uniform(0.2, 0.6) * rng.choice([-1, 1])
            up = 0.15 * (np.pi / 2 - a1)                        # forks bend back toward the light
            limb(fork, a1 + turn + up, length * rng.uniform(0.5, 0.72), width * 0.6, level + 1)

    for k in range(int(5 + 5 * spread)):                        # boughs leave the trunk from a third of the way up
        t = rng.uniform(0.32, 0.92)
        start = (x + lean * height * t, base_y - height * t)
        side = 1 if k % 2 else -1
        angle = np.pi / 2 - side * rng.uniform(0.35, 0.9) * (0.6 + spread)
        limb(start, angle, height * spread * rng.uniform(0.4, 0.65) * (1.1 - t * 0.5), trunk_w * 0.34 * (1.15 - t), 1)
    bough_rgb = trunk_rgb * 0.65 + twig_rgb * 0.35 if birch else trunk_rgb
    with canvas.layer(depth=depth):
        canvas.add(twigs.astype(np.float32) / 255.0, twig_rgb, region)
        canvas.add(boughs.astype(np.float32) / 255.0, bough_rgb, region)
        trunk = geom.taper([(x, base_y + 2), mid, top], trunk_w, start=1.0, end=0.15, peak=0.0)
        canvas.add(trunk, trunk_rgb, region, form="round", outline=(max(trunk_w * 0.06, 0.6), twig_rgb * 0.7))
        if birch:                                               # lenticels: short dark dashes across the trunk
            for _ in range(int(14 + height / 12)):
                t = rng.uniform(0.02, 0.85)
                cx = x + lean * height * t * 0.9
                cy = base_y - height * t
                half = trunk_w * (1 - 0.8 * t) * 0.5
                dash = geom.ellipse(cx + rng.uniform(-0.3, 0.3) * half, cy, half * rng.uniform(0.3, 0.8),
                                    max(height * 0.004, 0.6))
                canvas.add(dash, BIRCH_MARK, region, clip=trunk)
            canvas.add(geom.rect(x - trunk_w, base_y - height * 0.06, x + trunk_w, base_y + 2), BIRCH_MARK, region,
                       clip=trunk)


def conifer(canvas, x, base_y, height, color="#2f5a45", trunk="#4a3526", depth=0.35, seed=None, lean=0.0,
            snow=0.0, snow_color="#f4f6fa"):
    """A fir/spruce: many drooping, ragged branches within a narrow cone, the trunk showing in the gaps.

    snow 0..1 lays snow on the upper face of every branch tier (0 none, 1 heavy).
    """
    rng = _rng(canvas, seed)
    s = canvas.scale
    mask = np.zeros((canvas.H, canvas.W), np.uint8)
    half = height * rng.uniform(0.15, 0.2)
    branches = max(14, int(height / 9))
    ledges = []                                                          # upper edge of every branch: where snow lies
    for k in range(branches):
        t = (k + rng.uniform(0.0, 0.8)) / branches                     # 0 at the top, 1 at the base
        if t > 0.94:
            continue
        cx = x + lean * height * (1 - t)
        y = base_y - height * (1 - t * 0.92)
        reach = half * (0.08 + 0.92 * t ** 0.9) * rng.uniform(0.7, 1.15)
        droop = reach * rng.uniform(0.25, 0.55)
        thick = height * (0.015 + 0.05 * t) * rng.uniform(0.8, 1.2)
        for side in (-1, 1):
            if rng.random() < 0.08 and t > 0.3:
                continue                                                 # a gap lets the trunk show
            tip = (cx + side * reach, y + droop)
            pts = [(cx, y - thick * 0.6), (cx + side * reach * 0.5, y + droop * 0.1 - thick * 0.5), tip]
            ledges.append((list(pts), thick))
            for j in range(3):                                           # ragged lower edge: hanging twigs
                f = 0.8 - j * 0.25
                pts.append((cx + side * reach * f, y + droop * f + thick * rng.uniform(0.6, 1.3)))
                pts.append((cx + side * reach * (f - 0.12), y + droop * (f - 0.12) + thick * 0.3))
            pts.append((cx, y + thick * 0.8))
            cv2.fillPoly(mask, [(np.array(pts) * s).astype(np.int32)], 255, lineType=cv2.LINE_AA)
    top = np.array([x + lean * height, base_y - height])
    cv2.fillPoly(mask, [(np.array([top, (top[0] - half * 0.08, top[1] + height * 0.08),
                                   (top[0] + half * 0.08, top[1] + height * 0.08)]) * s).astype(np.int32)], 255, cv2.LINE_AA)
    shade = 1 + 0.25 * (fractal_noise(canvas.H, canvas.W, height * 0.08 * s, 2, rng)[..., None] - 0.5)
    rgb = np.clip(to_rgb(color)[None, None, :] * shade, 0, 1).astype(np.float32)
    with canvas.layer(depth=depth):
        canvas.add(geom.taper([(x, base_y + 2), tuple(top)], height * 0.035, start=1.0, end=0.2), trunk, "trunk")
        canvas.add(mask.astype(np.float32) / 255.0, rgb, "foliage", form="round", bulge=half * 0.5, relief=0.8,
                   cast=(height * 0.03, height * 0.02, 2, 0.4))
        if snow:
            _snow_ledges(canvas, ledges, mask, height, snow, snow_color, rng)


def _snow_ledges(canvas, ledges, mask, height, amount, color, rng):
    """Snow lying along the upper edge of each branch: a soft white band that thins toward the branch tip,
    broken into clumps, with a little of it hanging over the branch below."""
    s = canvas.scale
    snow = np.zeros((canvas.H, canvas.W), np.uint8)
    for pts, thick in ledges:
        width = max(int(thick * (0.35 + 0.45 * amount) * s), 1)
        line = (np.array(pts) * s).astype(np.int32)
        cv2.polylines(snow, [line[:2]], False, 255, width, cv2.LINE_AA)
        cv2.polylines(snow, [line[1:]], False, 255, max(width // 2, 1), cv2.LINE_AA)
    clumps = fractal_noise(canvas.H, canvas.W, height * 0.04 * s, 2, rng)
    cover = cv2.GaussianBlur(snow.astype(np.float32) / 255.0, (0, 0), 0.5 * s) * smoothstep(0.42 - 0.2 * amount, 0.6, clumps)
    reach = int(height * 0.012 * s) * 2 + 3                       # snow may sit a little above the branch outline
    cover = np.clip(cover * 1.5, 0, 1) * cv2.dilate((mask > 127).astype(np.uint8), np.ones((reach, reach), np.uint8))
    canvas.add(cover.astype(np.float32), color, "snow", form="round", bulge=height * 0.008, relief=0.5, soft=0.4)


def broadleaf(canvas, x, base_y, height, color="#5f8f4a", trunk="#5a4030", depth=0.35, seed=None, spread=0.55,
              outline=None, density=1.0):
    """A deciduous tree: trunk and boughs, a crown of separate leaf clumps with sky showing between them.

    density  > 1 breaks the crown into more, smaller clumps (a big tree seen close, a tree in blossom).
    """
    rng = _rng(canvas, seed)
    crown_y = base_y - height * 0.64
    radius = height * spread * 0.5
    base = to_rgb(color)
    with canvas.layer(depth=depth):
        trunk_w = height * 0.06
        canvas.add(geom.taper([(x, base_y + 2), (x + height * 0.01, base_y - height * 0.3), (x, crown_y + radius * 0.3)], trunk_w,
                              start=1.0, end=0.5, peak=0.05), trunk, "trunk", form="round", outline=outline)
        boughs = []
        for _ in range(5):
            angle = rng.uniform(-2.6, -0.5)
            end = (x + np.cos(angle) * radius * rng.uniform(0.5, 0.85), crown_y + np.sin(angle) * radius * 0.7)
            boughs.append(end)
            canvas.add(geom.taper([(x, base_y - height * rng.uniform(0.28, 0.4)), end], trunk_w * 0.4, start=1.0, end=0.15),
                       trunk, "trunk", form="round")
        # Clumps sit in an irregular envelope; far clumps first and darker, so the crown has depth.
        clumps = []
        for _ in range(int((70 + radius * 0.1) * density ** 2)):
            angle, dist = rng.uniform(0, 2 * np.pi), rng.uniform(0.0, 1.0) ** 0.5
            cx = x + np.cos(angle) * dist * radius * 1.1
            cy = crown_y + np.sin(angle) * dist * radius * 0.8
            size = radius * rng.uniform(0.11, 0.2) * (1.1 - 0.3 * dist) / density
            clumps.append((rng.random(), cx, cy, size))
        for anchor in boughs:
            clumps.append((rng.uniform(0.3, 1.0), anchor[0], anchor[1], radius * rng.uniform(0.14, 0.2) / density))
        clumps.sort()
        shapes = []
        for front, cx, cy, size in clumps:
            tone = np.clip(base * (0.7 + 0.42 * front) * rng.uniform(0.92, 1.08), 0, 1)
            # Leafy outline: many small scallops around each clump.
            angles = np.linspace(0, 2 * np.pi, 15, endpoint=False)
            pts = [(cx + np.cos(a) * size * rng.uniform(0.7, 1.15), cy + np.sin(a) * size * 0.85 * rng.uniform(0.7, 1.15))
                   for a in angles]
            shapes.append(geom.blob(pts))
            canvas.add(shapes[-1], tone, "foliage", form="round", bulge=size * 0.6, relief=0.7,
                       cast=(size * 0.1, size * 0.15, size * 0.1, 0.3))
        if outline:             # line art follows the crown's silhouette, not every clump
            width, color = outline if isinstance(outline, (tuple, list)) else (outline, None)
            canvas.ink(geom.union(*shapes), color if color is not None else np.clip(base * 0.45, 0, 1), stroke=width)

def grass(canvas, y0, y1, color="#4f7f3f", density=1.0, blade=18.0, depth=0.15, seed=None, region="grass"):
    """Foreground grass blades between y0 and y1."""
    rng = _rng(canvas, seed)
    s = canvas.scale
    dark = np.zeros((canvas.H, canvas.W), np.uint8)
    light = np.zeros((canvas.H, canvas.W), np.uint8)
    count = int(canvas.width * (y1 - y0) / (blade * 3.2) * density)
    for _ in range(count):
        x, y = rng.uniform(0, canvas.width), rng.uniform(y0, y1)
        grow = blade * (0.6 + (y - y0) / max(y1 - y0, 1) * 0.9) * rng.uniform(0.7, 1.3)
        lean = rng.normal(0, 0.3) * grow
        pts = np.array([[x, y], [x + lean * 0.4, y - grow * 0.6], [x + lean, y - grow]]) * s
        target = light if rng.random() < 0.4 else dark
        cv2.polylines(target, [pts.astype(np.int32)], False, 255, max(int(grow * 0.07 * s), 1), cv2.LINE_AA)
    base = to_rgb(color)
    with canvas.layer(depth=depth):
        canvas.add(dark.astype(np.float32) / 255.0, base * 0.8, region)
        canvas.add(light.astype(np.float32) / 255.0, np.clip(base * 1.25 + 0.04, 0, 1), region)


def flowers(canvas, y0, y1, colors=("#f2d14a", "#e86a6a", "#ffffff"), count=120, size=3.0, depth=0.15, seed=None):
    rng = _rng(canvas, seed)
    with canvas.layer(depth=depth):
        for _ in range(count):
            x, y = rng.uniform(0, canvas.width), rng.uniform(y0, y1)
            r = size * (0.5 + (y - y0) / max(y1 - y0, 1))
            canvas.add(geom.ellipse(x, y, r, r * 0.8), colors[rng.integers(len(colors))], "flower", unlit=False)


def rock(canvas, x, y, width, height, color="#8a8580", depth=0.3, seed=None, outline=None):
    """A boulder sitting on (x, y): irregular outline with faceted shading."""
    rng = _rng(canvas, seed)
    count = 9
    pts = []
    for i in range(count):
        angle = np.pi + np.pi * i / (count - 1)
        r = rng.uniform(0.8, 1.05)
        pts.append((x + np.cos(angle) * width / 2 * r, y + np.sin(angle) * height * r))
    path = geom.polygon(pts + [(x + width / 2, y), (x - width / 2, y)])
    with canvas.layer(depth=depth):
        canvas.add(path, color, "rock", form="round", bulge=min(width, height) * 0.35, relief=1.3,
                   cast=(width * 0.08, height * 0.04, 2, 0.5), outline=outline)


def contact_shadow(canvas, x, y, width, height=None, strength=0.6, blur=None):
    """Soft shadow on the ground under something standing at (x, y): anchors a figure or object to the floor."""
    height = width * 0.22 if height is None else height
    canvas.shade(geom.ellipse(x, y, width / 2, height / 2), strength, blur=blur if blur is not None else height * 0.45)


# ---------- weather ----------
# Particle look per kind, as (far, near) pairs in design units: a band of falling particles gets bigger, softer,
# sparser and more transparent the nearer it is to the lens. count is particles per 100 x 100 design units.
WEATHER = {
    "rain": dict(size=(9.0, 60.0), width=(0.45, 1.8), alpha=(0.4, 0.3), blur=(0.0, 1.4), count=(9.0, 0.5),
                 colors=("#dfe8f2",), crisp=True),
    "snow": dict(size=(0.7, 4.5), width=(1.0, 1.0), alpha=(0.85, 0.75), blur=(0.0, 2.2), count=(7.0, 0.35),
                 colors=("#ffffff",), crisp=False),
    "petals": dict(size=(2.2, 9.0), width=(0.5, 0.5), alpha=(0.95, 0.9), blur=(0.0, 1.6), count=(1.6, 0.12),
                   colors=("#f7cfd8", "#fbe6ea", "#eeaabd"), crisp=False),
}


def weather(canvas, kind="rain", amount=1.0, near=0.3, wind=0.18, colors=None, y0=0.0, y1=None, seed=None,
            crisp=None, depth=None, clip=None):
    """One band of falling rain, snow or petals.

    near   0 = a far band (fine, dense, sharp) .. 1 = a band just before the lens (large, sparse, defocused).
           Call once before the figures with a low value and once after them with a higher one: the far band
           is hidden behind the figures, the near band crosses them, and the picture gains depth.
    wind   horizontal drift per unit of fall (rain slant; the tumble direction of flakes and petals).
    crisp  True keeps the particles sharp over any medium (rain streaks survive a painterly medium);
           False paints them into the picture so the medium and the haze treat them like everything else.
    """
    spec = WEATHER[kind]
    rng = _rng(canvas, seed)
    s = canvas.scale
    y1 = canvas.height if y1 is None else y1
    def at_band(key):
        far_value, near_value = spec[key]
        return far_value + (near_value - far_value) * near

    size, width, alpha, blur = at_band("size"), at_band("width"), at_band("alpha"), at_band("blur")
    count = int(at_band("count") * amount * canvas.width * (y1 - y0) / 1e4)
    colors = colors or spec["colors"]
    crisp = spec["crisp"] if crisp is None else crisp
    depth = (0.9 - 0.85 * near) if depth is None else depth
    masks = [np.zeros((canvas.H, canvas.W), np.uint8) for _ in colors]
    for _ in range(count):
        x, y = rng.uniform(-size, canvas.width + size), rng.uniform(y0 - size, y1)
        k = rng.integers(len(colors))
        grow = rng.uniform(0.6, 1.3)
        if kind == "rain":
            length = size * grow
            pts = np.array([[x, y], [x + wind * length, y + length]]) * s
            cv2.line(masks[k], tuple(pts[0].astype(int)), tuple(pts[1].astype(int)), 255,
                     max(int(round(width * s * grow)), 1), cv2.LINE_AA)
        elif kind == "snow":
            r = max(size * grow * s, 0.6)
            cv2.ellipse(masks[k], (int(x * s), int(y * s)), (int(round(r)), int(round(r * rng.uniform(0.8, 1.0)))),
                        0, 0, 360, 255, -1, cv2.LINE_AA)
        else:                       # a petal: a small teardrop tumbling at a random angle
            length = size * grow * s
            angle = rng.uniform(0, 2 * np.pi) + wind
            u = np.array([np.cos(angle), np.sin(angle)])
            v = np.array([-u[1], u[0]]) * rng.uniform(0.35, 0.9)          # foreshortened as it turns
            t = np.linspace(0, np.pi, 9)
            outline = [np.array([x * s, y * s]) + u * length * (np.cos(a) * 0.5) + v * length * 0.32 * np.sin(a) *
                       (1.15 - 0.3 * np.cos(a)) * side for side in (1, -1) for a in (t if side > 0 else t[::-1])]
            cv2.fillPoly(masks[k], [np.array(outline).astype(np.int32)], 255, cv2.LINE_AA)
    with canvas.layer(depth=depth):
        for color, mask in zip(colors, masks):
            field = mask.astype(np.float32) / 255.0
            if blur:
                field = cv2.GaussianBlur(field, (0, 0), blur * s)
            field = np.clip(field * alpha, 0, 1)
            if clip is not None:
                field = field * canvas.mask(clip)
            if crisp:
                canvas.accent(field, color)
            else:                       # painted in, but leaves depth and groups alone so no outline is traced
                saved_depth, saved_group = canvas.depth.copy(), canvas.group.copy()
                canvas.add(field, color, None, unlit=True)
                canvas.depth, canvas.group = saved_depth, saved_group


def wet_reflection(canvas, ground, light, strength=0.55, ripple=0.5, streak=1.0, glow=0.8, threshold=0.62, seed=None):
    """Wet ground: everything standing on it is mirrored below its own foot, smeared into vertical streaks,
    and bright lamps, signs and windows run down the ground as long light pillars.

    ground  mask or path of the wet surface (road, pavement, floor). Call after everything that stands on it,
            figures included: each object reflects about the line where it meets the ground, which is exact
            for upright things in a level perspective.
    """
    rng = _rng(canvas, seed)
    s = canvas.scale
    wet = np.clip(canvas.mask(ground).astype(np.float32), 0, 1)
    if wet.max() <= 0:
        return
    from .core import reference, luminance
    scene = reference(canvas, light)
    H, W = canvas.H, canvas.W
    # Foot line of each column: the last row above that is not wet ground.
    base = np.full((H, W), -1, np.int32)
    last = np.full(W, -1, np.int32)
    standing = wet < 0.5
    for y in range(H):
        last = np.where(standing[y], y, last)
        base[y] = last
    ys = np.arange(H, dtype=np.float32)[:, None]
    source_y = 2 * base - ys
    valid = (base >= 0) & (source_y >= 0)
    # Ripples: sideways wobble that grows with the distance below the foot line.
    wobble = fractal_noise(H, max(W // 24, 4), 5 * s, 3, rng)
    wobble = cv2.resize(wobble, (W, H), interpolation=cv2.INTER_CUBIC) - 0.5
    reach = np.clip((ys - base) / (40 * s), 0, 1)
    map_x = np.arange(W, dtype=np.float32)[None, :] + wobble * ripple * 10 * s * (0.3 + reach)
    map_y = np.where(valid, source_y, ys).astype(np.float32)
    mirror = cv2.remap(scene.astype(np.float32), map_x.astype(np.float32), map_y, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT)
    mirror = cv2.GaussianBlur(mirror, (0, 0), sigmaX=0.7 * s, sigmaY=(1.0 + 4.0 * streak) * s)
    # Light pillars: bright sources smear straight down and fade.
    bright = smoothstep(threshold, 1.0, luminance(scene))[..., None] * scene
    pillar = np.zeros_like(bright)
    decay = np.exp(-1.0 / (max(streak, 0.05) * 90 * s))
    run = np.zeros((W, 3), np.float32)
    for y in range(H):
        run = np.maximum(bright[y], run * decay)
        pillar[y] = run
    pillar = cv2.GaussianBlur(pillar, (0, 0), sigmaX=1.6 * s, sigmaY=3 * s) * (wet > 0.5)[..., None]
    # Fade out where the mirrored point nears the top of the picture: nothing above the frame to reflect.
    seen = valid * smoothstep(0.0, 60 * s, source_y)
    rgb = np.clip(mirror * seen[..., None] + pillar * glow, 0, 1)
    # Grazing angles reflect more (Fresnel): the far ground near the foot lines is the most mirror-like.
    fresnel = strength * (1.0 - 0.45 * reach)
    patches = 0.75 + 0.5 * fractal_noise(H, W, 60 * s, 2, rng)                   # not every patch is equally wet
    alpha = np.clip(fresnel * patches * seen + luminance(pillar) * glow, 0, 1) * wet
    saved_depth, saved_group = canvas.depth.copy(), canvas.group.copy()
    canvas.add(alpha.astype(np.float32), rgb.astype(np.float32), None, unlit=True, keep_normal=1.0)
    canvas.depth, canvas.group = saved_depth, saved_group


# ---------- perspective construction ----------
NEAR_PLANE = 0.1      # world units in front of the camera; geometry closer than this is clipped away


class Perspective:
    """Camera for ground-plane construction: streets, rooms, tables, buildings.

    World: X right, Y up, Z ahead (same length unit, e.g. metres). The camera stands at (0, eye, 0).
    horizon_y  design-unit y of the eye level; eye = camera height above the ground
    focal      in canvas widths: 0.8 wide angle .. 1.5 normal .. 3 telephoto
    yaw        degrees the camera turns to the right. 0 gives one-point perspective down the Z axis;
               20 to 45 gives two-point perspective on a street corner.
    pitch      degrees the camera tilts up (+) or down (-). Verticals then converge: three-point perspective
               (looking up at towers, down into a street). horizon_y stays the picture's centre line, so with
               pitch the true horizon moves: down when looking up, up when looking down.
    """

    def __init__(self, canvas, horizon_y, eye=1.6, focal=1.2, centre_x=None, yaw=0.0, pitch=0.0):
        self.canvas, self.horizon_y, self.eye = canvas, horizon_y, eye
        self.f = focal * canvas.width
        self.cx = canvas.width / 2 if centre_x is None else centre_x
        self.yaw, self.pitch = yaw, pitch
        cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        cp, sp = np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
        turn = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
        tilt = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
        self._rotation = tilt @ turn                     # world direction -> camera direction

    # ----- camera space -----
    def to_camera(self, x, y, z):
        """World point -> camera space relative to the eye (x right, y up, z ahead of the lens)."""
        return tuple(self._rotation @ np.array([x, y - self.eye, z], float))

    def to_world_direction(self, cx, cy, cz):
        return self._rotation.T @ np.array([cx, cy, cz], float)

    def sun(self, light):
        """World direction toward the light of a scene Light (its azimuth and elevation are camera-relative)."""
        dx, dy, dz = (float(v) for v in light.direction)
        return self.to_world_direction(dx, -dy, -dz)

    def depth(self, x, z):
        """Distance ahead of the camera of a world point (for draw order and sizing)."""
        return self.to_camera(x, 0, z)[2]

    def point(self, x, y, z):
        cx, cy, cz = self.to_camera(x, y, z)
        cz = max(cz, 1e-3)
        return (self.cx + self.f * cx / cz, self.horizon_y - self.f * cy / cz)

    def scale(self, z, x=0.0):
        """Design units per world unit at a point (use for sizing figures and props in the scene)."""
        return self.f / max(self.depth(x, z), 1e-3)

    def screen_normal(self, normal):
        """World normal -> canvas normal (x right, y down, z toward the viewer)."""
        nx, ny, nz = self._rotation @ np.asarray(normal, float)
        return (nx, -ny, -nz)

    def _clip(self, corners):
        """Clip a world polygon against the near plane (Sutherland-Hodgman in camera space)."""
        cam = [self.to_camera(*c) for c in corners]
        out = []
        for i, a in enumerate(cam):
            b = cam[(i + 1) % len(cam)]
            a_in, b_in = a[2] >= NEAR_PLANE, b[2] >= NEAR_PLANE
            if a_in:
                out.append(a)
            if a_in != b_in:
                t = (NEAR_PLANE - a[2]) / (b[2] - a[2])
                out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
        return out

    def quad(self, corners):
        """Any planar world polygon (3 or more corners), clipped at the camera and projected."""
        cam = self._clip(corners)
        if len(cam) < 3:
            return geom.polygon([(0, 0), (0, 0), (0, 0)])
        return geom.polygon([(self.cx + self.f * x / z, self.horizon_y - self.f * y / z) for x, y, z in cam])

    def ground_quad(self, x0, x1, z0, z1, y=0.0):
        return self.quad([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)])

    def face(self, origin, u_axis, v_axis):
        """Mapper for a planar face: f(u, v, out=0) -> canvas point. u, v run 0..1 along the two axes;
        out is a distance along the face normal (awnings, sills and signs stand off the wall)."""
        origin, u_axis, v_axis = (np.asarray(v, float) for v in (origin, u_axis, v_axis))
        normal = np.cross(v_axis, u_axis)
        normal = normal / (np.linalg.norm(normal) + 1e-9)

        def mapper(u, v, out=0.0):
            return self.point(*(origin + u * u_axis + v * v_axis + out * normal))
        mapper.size = (float(np.linalg.norm(u_axis)), float(np.linalg.norm(v_axis)))
        mapper.normal = normal
        mapper.corners = [origin, origin + u_axis, origin + u_axis + v_axis, origin + v_axis]
        return mapper

    def box_faces(self, x, z, width, depth, height, y=0.0):
        """All five outer faces of an axis-aligned box as {name: (mapper, visible)}.

        u runs left to right as seen from outside the face; v runs bottom to top (top face: front to back).
        """
        x0, x1, z0, z1, y0, y1 = x, x + width, z, z + depth, y, y + height
        up = (0, height, 0)
        faces = {
            "front": self.face((x0, y0, z0), (width, 0, 0), up),
            "back": self.face((x1, y0, z1), (-width, 0, 0), up),
            "left": self.face((x0, y0, z1), (0, 0, -depth), up),
            "right": self.face((x1, y0, z0), (0, 0, depth), up),
            "top": self.face((x0, y1, z0), (width, 0, 0), (0, 0, depth)),
        }
        out = {}
        for name, mapper in faces.items():
            centre = np.mean(mapper.corners, axis=0)
            to_eye = np.array([0.0, self.eye, 0.0]) - centre
            out[name] = (mapper, float(mapper.normal @ to_eye) > 1e-6)
        return out

    def box(self, x, z, width, depth, height, color, y=0.0, side_color=None, top_color=None, region="box",
            outline=None, scene_depth=None, clip=None):
        """Axis-aligned box with its near-left-bottom corner at (x, y, z). Draws the visible faces.

        Returns face mappers {'front', 'back', 'left', 'right', 'top', 'side'}: f(u, v, out=0) -> canvas
        point with u and v in 0..1, for placing windows, doors and signs. 'side' is the visible side face
        (the one that looks onto the street in a one-point view). Each mapper has .visible.
        clip limits the drawing to a mask: redrawing a table top over only the legs of a sitter drawn after
        it keeps her hands on the table in front of it.
        """
        c = self.canvas
        base = to_rgb(color)
        side_color = base * 0.9 if side_color is None else to_rgb(side_color)
        top_color = np.clip(base * 1.06, 0, 1) if top_color is None else to_rgb(top_color)
        faces = self.box_faces(x, z, width, depth, height, y)
        fills = {"front": base, "back": base, "left": side_color, "right": side_color, "top": top_color}
        with c.layer(depth=scene_depth):
            for name, (mapper, visible) in faces.items():
                if visible:
                    c.add(self.quad(mapper.corners), fills[name], region, normal=self.screen_normal(mapper.normal),
                          outline=outline, clip=clip)
        out = {}
        for name, (mapper, visible) in faces.items():
            mapper.visible = visible
            out[name] = mapper
        visible_sides = [n for n in ("left", "right") if faces[n][1]]
        out["side"] = out[visible_sides[0]] if visible_sides else out["left" if x > 0 else "right"]
        return out

    def room(self, x0, x1, z0, z1, height, wall="#d9cdb8", floor="#8a6a50", ceiling=None, back=None,
             side=None, outline=None, scene_depth=None, openings=None):
        """Inside of a box room seen by a camera standing in it: floor, ceiling, back wall and two side walls.

        Returns face mappers {'back', 'left', 'right', 'floor', 'ceiling'} with u running left to right and
        v bottom to top as seen from inside the room (floor and ceiling: v runs away from the camera), for
        windows, doors, pictures and rugs. Each mapper has .visible.
        openings  {face: [(u0, v0, u1, v1), ...]} cuts holes (windows, doorways) through the walls, so whatever
                  was painted before the room (sky, the street outside) shows through them.
        """
        c = self.canvas
        width, depth = x1 - x0, z1 - z0
        up = (0, height, 0)
        faces = {
            "back": (self.face((x0, 0, z1), (width, 0, 0), up), back or wall),
            "left": (self.face((x0, 0, z0), (0, 0, depth), up), side or wall),
            "right": (self.face((x1, 0, z1), (0, 0, -depth), up), side or wall),
            "floor": (self.face((x0, 0, z0), (width, 0, 0), (0, 0, depth)), floor),
            "ceiling": (self.face((x0, height, z1), (width, 0, 0), (0, 0, -depth)),
                        ceiling or np.clip(to_rgb(wall) * 1.04, 0, 1)),
        }
        out = {}
        with c.layer(depth=scene_depth):
            for name, (mapper, color) in faces.items():
                centre = np.mean(mapper.corners, axis=0)
                mapper.visible = float(mapper.normal @ (np.array([0.0, self.eye, 0.0]) - centre)) > 1e-6
                if mapper.visible:
                    shape = self.quad(mapper.corners)
                    for u0, v0, u1, v1 in (openings or {}).get(name, ()):
                        shape = geom.subtract(shape, geom.polygon([mapper(u0, v0), mapper(u1, v0), mapper(u1, v1),
                                                                   mapper(u0, v1)]))
                    c.add(shape, color, name if name in ("floor", "ceiling") else "wall",
                          normal=self.screen_normal(mapper.normal), outline=outline)
                out[name] = mapper
        return out

    def chair(self, x, z, seat=0.45, width=0.42, depth=0.42, back=0.45, color="#6a4a34", back_side="far",
              outline=None, scene_depth=None):
        """A plain wooden chair centred on (x, z): four legs, a seat at height `seat` and a back rest.

        back_side  where the back rest stands: 'far' (the sitter faces the camera), 'near' (seen from behind),
                   'left' or 'right' (the sitter faces across the picture, away from that side).
        Draw it before the figure who sits on it; her body then covers the parts of the chair it hides.
        """
        leg, slab = 0.035, 0.035
        x0, z0 = x - width / 2, z - depth / 2
        dark = np.clip(to_rgb(color) * 0.8, 0, 1)
        corners = [(lx, lz) for lz in (z0 + depth - leg, z0) for lx in (x0, x0 + width - leg)]     # far legs first

        def on_back(lx, lz):
            return {"far": lz > z0, "near": lz == z0, "left": lx == x0, "right": lx > x0}[back_side]
        if back_side in ("far", "near"):
            rest = (x0, z0 + depth - leg if back_side == "far" else z0, width, leg)
        else:
            rest = (x0 if back_side == "left" else x0 + width - leg, z0, leg, depth)
        with self.canvas.layer(depth=scene_depth):
            for lx, lz in corners:
                self.box(lx, lz, leg, leg, seat + back if on_back(lx, lz) else seat, dark, region="chair", outline=outline)
            if back_side == "near":
                self.box(x0, z0, width, depth, slab, color, y=seat - slab, region="chair", outline=outline)
                self.box(*rest[:2], rest[2], rest[3], back * 0.35, color, y=seat + back * 0.6, region="chair", outline=outline)
            else:
                self.box(*rest[:2], rest[2], rest[3], back * 0.35, color, y=seat + back * 0.6, region="chair", outline=outline)
                self.box(x0, z0, width, depth, slab, color, y=seat - slab, region="chair", outline=outline)

    def windows(self, mapper, rows, cols, color="#2c3a4a", margin=0.12, gap=0.35, region="window", lit=None, seed=0):
        """Grid of windows on a face mapper. lit = colour for randomly lit windows (night scenes)."""
        rng = np.random.default_rng(seed)
        cell_w, cell_h = (1 - 2 * margin) / cols, (1 - 2 * margin) / rows
        for r in range(rows):
            for col in range(cols):
                u0 = margin + col * cell_w + cell_w * gap / 2
                v0 = margin + r * cell_h + cell_h * gap / 2
                u1, v1 = u0 + cell_w * (1 - gap), v0 + cell_h * (1 - gap)
                glow = lit is not None and rng.random() < 0.45
                self.canvas.add(geom.polygon([mapper(u0, v0), mapper(u1, v0), mapper(u1, v1), mapper(u0, v1)]),
                                lit if glow else color, region, unlit=glow, gloss=0.0 if glow else 0.4)


def skyline(canvas, base_y, height, color="#3a4660", depth=0.8, seed=None, lit=None, density=1.0):
    """Far city silhouette: a row of flat towers, optionally with lit windows."""
    rng = _rng(canvas, seed)
    x = -20.0
    with canvas.layer(depth=depth):
        while x < canvas.width + 20:
            w = rng.uniform(0.04, 0.10) * canvas.width / density
            h = height * rng.uniform(0.35, 1.0)
            shade = to_rgb(color) * rng.uniform(0.85, 1.1)
            canvas.add(geom.rect(x, base_y - h, x + w, base_y + 2), np.clip(shade, 0, 1), "building", normal=(0.2, 0, 1))
            if lit is not None:
                for _ in range(int(w * h / 320)):
                    wx, wy = rng.uniform(x + 3, x + w - 5), rng.uniform(base_y - h + 4, base_y - 6)
                    canvas.add(geom.rect(wx, wy, wx + 2.2, wy + 3.2), lit, "window", unlit=True)
            x += w * rng.uniform(0.75, 1.1)
