"""Scenery helpers: natural shapes that are tedious to place point by point."""
import numpy as np

from . import fx
from . import geometry as geo
from . import shading as sh


def noise_line(count, roughness=0.5, octaves=5, seed=0):
    """1D fractal noise in -1..1: the profile of a ridge, a treeline, a torn edge."""
    rng = np.random.default_rng(seed)
    position = np.linspace(0.0, 1.0, count)
    total, weight_sum = np.zeros(count), 0.0
    for octave in range(octaves):
        knots = 3 * 2 ** octave + 1
        weight = roughness ** octave
        total += np.interp(position, np.linspace(0.0, 1.0, knots), rng.uniform(-1.0, 1.0, knots)) * weight
        weight_sum += weight
    return total / weight_sum


def ridge(shape, base_y, relief, roughness=0.5, seed=0, tilt=0.0, count=240):
    """Closed silhouette of a mountain range or hill, filled down to the canvas bottom.

    base_y: mean height of the skyline in pixels. relief: how far peaks rise and dip around it.
    tilt: pixels the skyline climbs from left to right.
    """
    height, width = shape
    x = np.linspace(-2.0, width + 2.0, count)
    y = base_y - noise_line(count, roughness, seed=seed) * relief - np.linspace(0.0, tilt, count)
    return np.vstack([np.stack([x, y], axis=1), [[width + 2.0, height + 2.0], [-2.0, height + 2.0]]])


def clouds(shape, coverage=0.45, scale=1.0, seed=0, stretch=(1.0, 2.6), softness=0.06, band=None):
    """Cloud coverage mask from stretched noise.

    coverage: share of the sky that is cloud. softness: edge softness (0.01 crisp anime clouds, 0.2 haze).
    band: (top, bottom) pixel rows the clouds fade out beyond.
    """
    noise = fx.fbm(shape, scale=scale, octaves=5, seed=seed, stretch=stretch)
    level = np.quantile(noise, 1.0 - coverage)
    mask = sh.smoothstep(level - softness, level + softness, noise)
    if band is not None:
        rows = np.arange(shape[0], dtype=np.float32)[:, None]
        span = max(band[1] - band[0], 1)
        mask = mask * np.clip(np.sin(np.clip((rows - band[0]) / span, 0, 1) * np.pi) * 1.6, 0.0, 1.0)
    return mask.astype(np.float32)


def conifer(base, height, width, tiers=5, seed=0):
    """A fir tree as stacked drooping tiers, top first. Returns a list of closed polygons."""
    rng = np.random.default_rng(seed)
    base = np.asarray(base, dtype=np.float64)
    shapes = []
    for tier in range(tiers):
        top = base[1] - height * (1.0 - tier / (tiers + 0.6))
        bottom = base[1] - height * (1.0 - (tier + 1.35) / (tiers + 0.6))
        half = width / 2 * (tier + 1) / tiers * rng.uniform(0.85, 1.1)
        lean = rng.uniform(-0.06, 0.06) * width
        shapes.append(geo.smooth([(base[0] + lean, top), (base[0] + half, bottom), (base[0] + half * 0.35, bottom - height * 0.035),
                                  (base[0], bottom + height * 0.01), (base[0] - half * 0.35, bottom - height * 0.035),
                                  (base[0] - half, bottom)], closed=True, corners=(0, 1, 5)))
    trunk = [(base[0] - width * 0.04, base[1] - height * 0.12), (base[0] + width * 0.04, base[1] - height * 0.12),
             (base[0] + width * 0.05, base[1]), (base[0] - width * 0.05, base[1])]
    return [np.array(trunk)] + shapes


def blades(region_box, count, length, seed=0, lean=0.25):
    """Grass blades as (root, tip, bend) triples inside region_box = (x0, y0, x1, y1)."""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = region_box
    roots = np.stack([rng.uniform(x0, x1, count), rng.uniform(y0, y1, count)], axis=1)
    sizes = length * rng.uniform(0.5, 1.2, count)
    tips = roots + np.stack([rng.normal(lean, 0.25, count) * sizes, -sizes], axis=1)
    return [(root, tip, rng.uniform(-0.25, 0.25)) for root, tip in zip(roots, tips)]


def reflect(painting, waterline, depth, ripple=6.0, darken=0.25, tint="#1c2a44", seed=0):
    """Mirror what is above `waterline` into the `depth` rows below it, broken by ripples."""
    height, width = painting.shape
    depth = int(min(depth, waterline, height - waterline))
    waterline = int(waterline)
    mirrored = painting.color[waterline - depth:waterline][::-1].copy()
    rows = np.arange(depth)[:, None]
    columns = np.arange(width)[None, :]
    # Ripples shift each row sideways; the shift grows toward the viewer.
    wave = fx.fbm((depth, width), scale=3.0, octaves=3, seed=seed, stretch=(1.0, 6.0)) - 0.5
    shift = (wave * ripple * (0.4 + rows / max(depth, 1) * 2.0)).astype(int)
    mirrored = mirrored[rows, np.clip(columns + shift, 0, width - 1)]
    mirrored = sh.blur(mirrored, 1.2)
    from .color import rgb
    fade = (darken + 0.35 * rows / max(depth, 1))[..., None]
    painting.color[waterline:waterline + depth] = mirrored * (1.0 - fade) + rgb(tint) * fade


# ---- streets and buildings -----------------------------------------------------------
def skyline(shape, base_y, heights=(40, 160), widths=(30, 90), seed=0):
    """Closed silhouette of distant buildings: a row of blocks of random width and height."""
    rng = np.random.default_rng(seed)
    height, width = shape
    points, x = [(-2.0, base_y)], -2.0
    while x < width + 2:
        top = base_y - rng.uniform(*heights)
        step = rng.uniform(*widths)
        points += [(x, top), (x + step, top)]
        x += step
    points += [(x, base_y), (x, height + 2.0), (-2.0, height + 2.0)]
    return np.array(points)


def street_wall(base_near, vanishing, near, far, height):
    """One building face along a street in one-point perspective.

    base_near: where the foot of the building line meets the picture edge (pixels).
    near, far: position along the street, 0 at base_near .. 1 at the vanishing point.
    height: wall height in pixels as it would be at base_near; it shrinks with distance.
    Returns the corners in screen order top-left, top-right, bottom-right, bottom-left (for geo.quad_map).
    """
    base_near, vanishing = np.asarray(base_near, dtype=np.float64), np.asarray(vanishing, dtype=np.float64)

    def edge(position):
        foot = base_near + (vanishing - base_near) * position
        return foot - [0.0, height * (1.0 - position)], foot

    top_a, foot_a = edge(near)
    top_b, foot_b = edge(far)
    if foot_a[0] <= foot_b[0]:
        return np.array([top_a, top_b, foot_b, foot_a])
    return np.array([top_b, top_a, foot_a, foot_b])


def windows(painting, quad, columns, rows, lit_colors, dark="#1d2538", lit=0.5, margin=0.2,
            inset=(0.06, 0.05, 0.94, 0.86), seed=0, clip=None):
    """Grid of windows on a wall quad, some lit. Returns the mask of the lit ones (for glow or reflections)."""
    rng = np.random.default_rng(seed)
    mapping = geo.quad_map(quad)
    glow = np.zeros(painting.shape, dtype=np.float32)
    for cell in geo.grid_cells(columns, rows, margin, inset):
        mask = painting.mask(mapping(cell))
        if clip is not None:
            mask = mask * clip
        if rng.random() < lit:
            painting.fill(mask, lit_colors[rng.integers(len(lit_colors))], rng.uniform(0.75, 1.0))
            glow = np.maximum(glow, mask)
        else:
            painting.fill(mask, dark, 0.9)
    return glow


# ---- soft natural masses ----------------------------------------------------------------
def puffs(painting, center, width, height, count=10, seed=0, flat_base=True):
    """Mask of a heap of overlapping discs: a cumulus cloud, a bush, a tree crown, a puff of smoke.

    flat_base: cut the heap off level at the bottom, as fair-weather clouds are.
    Returns (mask, list of disc masks); the single discs are useful for shading each lump by itself.
    """
    rng = np.random.default_rng(seed)
    center = np.asarray(center, dtype=np.float64)
    discs = []
    for index in range(count):
        along = (index + 0.5) / count * 2.0 - 1.0 + rng.uniform(-0.12, 0.12)
        crown = 1.0 - along ** 2                                   # lumps are tallest in the middle of the heap
        radius = height * (0.28 + 0.34 * crown) * rng.uniform(0.8, 1.15)
        spot = center + [along * width / 2 * 0.86, -height * 0.42 * crown * rng.uniform(0.5, 1.0)]
        discs.append(painting.mask(geo.ellipse(spot, radius * rng.uniform(1.0, 1.35), radius, count=40)))
    mask = np.maximum.reduce(discs)
    if flat_base:
        rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
        cut = 1.0 - sh.smoothstep(center[1] + height * 0.04, center[1] + height * 0.10, rows)   # keep what is above the base
        mask, discs = mask * cut, [disc * cut for disc in discs]
    return mask, discs


def foliage(painting, center, width, height, count=16, seed=0):
    """Mask of a tree crown or shrub: leaf clumps scattered inside an ellipse, small ones toward the rim.

    Returns (mask, list of clump masks ordered back to front).
    """
    rng = np.random.default_rng(seed)
    center = np.asarray(center, dtype=np.float64)
    clumps = []
    for index in range(count):
        angle, reach = rng.uniform(0, 2 * np.pi), np.sqrt(rng.uniform(0.0, 1.0)) * 0.72
        spot = center + [np.cos(angle) * reach * width / 2, np.sin(angle) * reach * height / 2]
        radius = min(width, height) * (0.30 - 0.12 * reach) * rng.uniform(0.85, 1.2)
        clumps.append((spot[1], painting.mask(geo.ellipse(spot, radius * rng.uniform(1.0, 1.3), radius, count=36))))
    clumps = [mask for _, mask in sorted(clumps, key=lambda item: item[0])]     # upper clumps sit behind lower ones
    return np.maximum.reduce(clumps), clumps


def scatter(region_box, count, seed=0, near_scale=1.0, far_scale=0.3):
    """Random (x, y, scale) spots in region_box = (x0, y0, x1, y1); scale grows toward the bottom (the viewer)."""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = region_box
    xs, ys = rng.uniform(x0, x1, count), rng.uniform(y0, y1, count)
    scales = far_scale + (near_scale - far_scale) * (ys - y0) / max(y1 - y0, 1e-6)
    order = np.argsort(ys)                                        # far ones first so near ones overlap them
    return [(xs[i], ys[i], scales[i]) for i in order]


# ---- concrete suburbs (the doomer mood) ---------------------------------------------------
CONCRETE = "#9a9d97"
DARK_WINDOW = "#2a3236"
WARM_WINDOWS = ("#f2c27a", "#e9a65a", "#f6d89a", "#d9905a")
WINDOW_INSET = (0.24, 0.22, 0.76, 0.72)     # one window inside its panel: (u0, v0, u1, v1) shares of the panel
BALCONY_INSET = (0.08, 0.50, 0.92, 0.97)    # balcony parapet inside its panel, covering the lower window
SEAM_WIDTH = 0.035           # panel seam width as a share of a panel's height on the picture
SEAM_OPACITY = 0.45
ROOF_BAND = 0.018            # dark parapet band along the top, share of the face height
PLINTH_BAND = 0.035          # darker concrete plinth along the foot, share of the face height
STAIR_INSET = (0.40, 0.50, 0.60, 0.92)      # stairwell window: narrow, half a floor lower than the flats
STAIR_LIGHT = "#d6dccb"      # stairwell lamps are pale fluorescent, never warm
STAIR_LIT = 0.6
STAIN_OPACITY = 0.22         # rain streaks running down the concrete
SNOW_COLOR = "#eef1ee"
SNOW_CLEAR = 0.9             # share of flakes taken out over a keep_clear mask


def _cells(mapping, floors, bays, inset, keep):
    """Polygons of one rectangle per panel, mapped onto the wall; keep(floor, bay) picks which panels get one."""
    u0, v0, u1, v1 = inset
    polygons = []
    for floor in range(floors):
        for bay in range(bays):
            if keep(floor, bay):
                corners = [(bay + u0, floor + v0), (bay + u1, floor + v0), (bay + u1, floor + v1), (bay + u0, floor + v1)]
                polygons.append(mapping(np.array(corners) / [bays, floors]))
    return polygons


def panel_facade(painting, quad, floors, bays, seed=0, lit=0.2, wall=CONCRETE, shade=0.0, balcony_every=0,
                 stairs_every=0, line_width=0.0, ink="#202428", lit_colors=WARM_WINDOWS):
    """One face of a prefabricated panel apartment block: seams between panels, one window per panel, some lit.

    quad: corners top-left, top-right, bottom-right, bottom-left (pixels), as for geo.quad_map, so the panels
    shrink toward the far edge. floors, bays: panels up and across. lit: share of windows with the light on.
    shade: 0..1 how far this face is turned from the light (the end wall of a block is darker).
    balcony_every: every n-th column of panels carries balconies (0 for none).
    stairs_every: every n-th column is a stairwell, narrow windows half a floor down with pale lamps (0 for none).
    Returns the mask of the lit windows, for glows and reflections.
    """
    from . import raster
    from .color import mix, shadow_of
    rng = np.random.default_rng(seed)
    mapping = geo.quad_map(quad)
    face = painting.mask(quad)
    base = mix(wall, shadow_of(wall, (0.62, 0.70, 0.74)), shade)
    painting.part(face, base)
    stains = fx.fbm(painting.shape, scale=3.0, octaves=3, seed=seed, stretch=(9.0, 1.0))
    painting.fill(face * sh.smoothstep(0.5, 0.9, stains), shadow_of(base, (0.80, 0.84, 0.86)), STAIN_OPACITY, "multiply")
    panel_height = np.linalg.norm(np.asarray(quad[3], float) - np.asarray(quad[0], float)) / floors
    seam = max(panel_height * SEAM_WIDTH, 0.6)
    seam_color = shadow_of(base, (0.55, 0.60, 0.64))
    for floor in range(1, floors):
        painting.stroke(mapping([(0.0, floor / floors), (1.0, floor / floors)]), seam, seam_color, taper=(0, 0),
                        opacity=SEAM_OPACITY, layer="color", clip=face)
    for bay in range(1, bays):
        painting.stroke(mapping([(bay / bays, 0.0), (bay / bays, 1.0)]), seam, seam_color, taper=(0, 0),
                        opacity=SEAM_OPACITY * 0.7, layer="color", clip=face)
    is_lit = rng.random((floors, bays)) < lit
    color_of = rng.integers(len(lit_colors), size=(floors, bays))
    stair = (lambda b: b % stairs_every == stairs_every // 2) if stairs_every > 0 else (lambda b: False)
    stair_lit = rng.random((floors, bays)) < STAIR_LIT
    is_lit &= ~np.array([[stair(b) for b in range(bays)]] * floors, dtype=bool)
    dark = raster.fill_many(_cells(mapping, floors, bays, WINDOW_INSET, lambda f, b: not stair(b) and not is_lit[f, b]),
                            painting.shape)
    painting.fill(dark * face, DARK_WINDOW)
    for on, tone in ((False, DARK_WINDOW), (True, STAIR_LIGHT)):
        stairs = raster.fill_many(_cells(mapping, floors, bays, STAIR_INSET, lambda f, b: stair(b) and stair_lit[f, b] == on),
                                  painting.shape)
        painting.fill(stairs * face, tone)
    glow = np.zeros(painting.shape, dtype=np.float32)
    for index, color in enumerate(lit_colors):
        windows = raster.fill_many(_cells(mapping, floors, bays, WINDOW_INSET,
                                          lambda f, b: is_lit[f, b] and color_of[f, b] == index), painting.shape) * face
        painting.fill(windows, color)
        glow = np.maximum(glow, windows)
    if balcony_every > 0:
        parapets = raster.fill_many(_cells(mapping, floors - 1, bays, BALCONY_INSET, lambda f, b: b % balcony_every == 0),
                                    painting.shape) * face
        painting.fill(parapets, mix(base, "#ffffff", 0.10))
        under = np.clip(sh.shift(parapets, 0, -max(seam * 1.5, 1.0)) - parapets, 0.0, 1.0)   # slab shadow on the wall above
        painting.fill(under * face, seam_color, 0.6)
        glow = glow * (1.0 - parapets)
    painting.fill(painting.mask(mapping([(0, 0), (1, 0), (1, ROOF_BAND), (0, ROOF_BAND)])) * face, seam_color, 0.8)
    painting.fill(painting.mask(mapping([(0, 1 - PLINTH_BAND), (1, 1 - PLINTH_BAND), (1, 1), (0, 1)])) * face, seam_color, 0.7)
    if line_width > 0:
        painting.outline(quad, line_width, ink)
    return glow


def bare_tree(painting, base, height, seed=0, color="#2b2a2e", birch=False, lean=0.0, depth=5, width=None):
    """Leafless winter tree: a trunk forking into ever thinner branches. Strokes on the colour layer.

    base: foot of the trunk (pixels). height: trunk-and-crown height in pixels. lean: degrees off upright.
    birch: pale trunk with dark marks, dark thin branches.
    """
    rng = np.random.default_rng(seed)
    trunk_width = width or height * 0.035
    trunk_color = "#d8d6cc" if birch else color

    def grow(start, angle, length, stroke_width, level):
        end = start + length * np.array([np.sin(np.radians(angle)), -np.cos(np.radians(angle))])
        path = geo.resample(geo.bent_line(start, end, rng.uniform(-0.12, 0.12)), 12)
        tone = trunk_color if level == 0 else color
        painting.stroke(path, np.linspace(stroke_width, stroke_width * 0.62, len(path)), tone, layer="color")
        if birch and level == 0:                       # dark marks across the pale bark
            for share in rng.uniform(0.05, 0.95, 9):
                spot = geo.lerp(start, end, share)
                mark = np.array([spot - [stroke_width * 0.45, 0], spot + [stroke_width * rng.uniform(0.0, 0.45), 1.0]])
                painting.stroke(mark, stroke_width * rng.uniform(0.10, 0.22), color, taper=(0.3, 0.3), layer="color")
        if level >= depth or stroke_width < 0.5:
            return
        forks = 2 if level == 0 else rng.integers(2, 4)
        for fork in range(forks):
            spread = rng.uniform(18.0, 40.0) * (1.0 if fork % 2 == 0 else -1.0)
            origin = path[int(rng.uniform(0.55, 1.0) * (len(path) - 1))] if level > 0 else end
            grow(origin, angle + spread + rng.uniform(-6, 6), length * rng.uniform(0.55, 0.75), stroke_width * 0.62, level + 1)
        if level == 0:                                 # side branches along the upper trunk
            for share in (0.45, 0.62, 0.78):
                origin = path[int(share * (len(path) - 1))]
                side = rng.choice([-1.0, 1.0])
                grow(origin, angle + side * rng.uniform(35, 60), length * 0.45, stroke_width * 0.45, level + 2)

    grow(np.asarray(base, dtype=np.float64), lean, height * 0.45, trunk_width, 0)


def snowfall(painting, count, seed=0, size=(0.8, 3.4), color=SNOW_COLOR, opacity=0.85, keep_clear=None):
    """Falling snow over the whole picture: many small sharp flakes and a few large soft ones near the eye.

    size: flake radius range in pixels for a 1000 px tall picture.
    keep_clear: optional mask (faces) where flakes thin out; specks on a face read as blemishes.
    """
    from . import raster
    rng = np.random.default_rng(seed)
    height, width = painting.shape
    scale = height / 1000.0
    radii = (size[0] + (size[1] - size[0]) * rng.random(count) ** 3) * scale     # most flakes are small
    xs, ys = rng.uniform(0, width, count), rng.uniform(0, height, count)
    near = radii > (size[0] + (size[1] - size[0]) * 0.45) * scale
    for chosen, softness in ((~near, 0.4), (near, 1.6)):
        flakes = [geo.ellipse((x, y), r, r * 0.9, count=8) for x, y, r in zip(xs[chosen], ys[chosen], radii[chosen])]
        mask = sh.blur(raster.fill_many(flakes, painting.shape), softness * scale)
        if keep_clear is not None:
            mask = mask * (1.0 - SNOW_CLEAR * np.clip(keep_clear, 0.0, 1.0))
        painting.fill(mask, color, opacity)


def wire(start, end, sag, count=24):
    """A cable hanging between two points, sagging `sag` pixels at the middle (power lines, tram wires)."""
    start, end = np.asarray(start, dtype=np.float64), np.asarray(end, dtype=np.float64)
    share = np.linspace(0.0, 1.0, count)
    points = start + (end - start) * share[:, None]
    points[:, 1] += sag * 4.0 * share * (1.0 - share)
    return points


SODIUM = "#f0a050"           # the orange of a sodium street lamp
LAMP_HALO, LAMP_POOL = 0.45, 0.55   # opacity of the lamp's halo in the air and of its pool on the ground


def sodium_lamp(painting, foot, height, side=1.0, ground=None, color=SODIUM, pole="#1d2124"):
    """Street lamp with a bent arm and a sodium glow; lights a pool on the ground mask if one is given.

    foot: bottom of the pole (pixels). height: pole height in pixels. side: -1 or 1, the way the arm reaches.
    Returns the lamp head position, for rims and highlights that should face it.
    """
    from . import backdrop
    foot = np.asarray(foot, dtype=np.float64)
    top = foot - [0.0, height]
    head = top + [side * height * 0.16, height * 0.03]
    painting.stroke(np.array([foot, top]), max(height * 0.016, 1.2), pole, taper=(0.0, 0.0), layer="color")
    painting.stroke(geo.bent_line(top, head, -0.35 * side), max(height * 0.011, 1.0), pole, taper=(0.0, 0.1), layer="color")
    # Normal blending keeps the orange: screened over pale snow it would wash out to white.
    if ground is not None:
        pool = painting.mask(geo.ellipse(foot + [side * height * 0.16, height * 0.02], height * 0.60, height * 0.13))
        painting.fill(sh.blur(pool, height * 0.07) * ground, color, LAMP_POOL)
    backdrop.glow(painting, head, height * 0.75, color, opacity=LAMP_HALO, mode="normal")
    backdrop.glow(painting, head, height * 0.12, "#ffe2b0", opacity=0.9)
    painting.fill(painting.mask(geo.ellipse(head + [0.0, height * 0.012], height * 0.035, height * 0.016)), "#fff2d6")
    return head
