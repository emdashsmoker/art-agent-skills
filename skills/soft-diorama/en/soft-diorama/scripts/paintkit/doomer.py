"""Doomer mood: the skill's signature look. Cold suburbs of panel housing at dusk and night, power
lines, sodium lamps and snow, painted in blue-grey with one small warm light in the frame.

PALETTE holds the colors. The motif painters draw on a Canvas:
    panel_facade() / panel_block()   panel apartment blocks (flat texture / box in perspective)
    utility_pole(), pylon(), wires() poles and towers that return points to hang wires on
    bare_tree(), snowfall(), smoke(), lamp_glow(), cigarette(), mouth_point()
finish() is the grade that ties a picture to the mood. See references/doomer.md.
"""
import cv2
import numpy as np

from . import config, finish as finishes, raster
from .canvas import Canvas
from .color import adjust, luminance, mix, rgb, shadow_of

PALETTE = {
    'night': '#1b2129', 'sky_top': '#28323e', 'sky_low': '#56636f', 'fog': '#8a95a1',
    'concrete': '#8b8f94', 'concrete_dark': '#5c6167', 'seam': '#6b7076', 'glass': '#2a323c',
    'snow': '#d3d9df', 'snow_shadow': '#97a3b1', 'asphalt': '#23272d',
    'sodium': '#f0a24e', 'sodium_core': '#ffd59a', 'window_warm': '#e3bf78', 'window_tv': '#8fb0d4',
    'ember': '#ff6a2a', 'rust': '#7e4a3c',
    'cloth_dark': '#2a2d33', 'cloth_wine': '#4e2a33', 'cloth_grey': '#5a5f66',
}

# --- panel housing (meters) ------------------------------------------------------------------
_FLOOR_M = 2.8                # storey height of a panel block
_BAY_M = 3.2                  # width of one window bay (one wall panel)
_WINDOW = (0.46, 0.48)        # window width and height as shares of a bay and a storey
_PANEL_RES = (6.0, 36.0)      # px per meter of a facade texture: lowest and highest
_JOINT_M = 0.06               # half-width of a joint between wall panels
_CANOPY = (0.12, 0.08)        # entrance canopy: overhang past the door (share of a bay), thickness (share of a storey)
_DOOR_LAMP = 0.2              # the lamp over an entrance, above its canopy (share of a storey)
_LEDGE = 0.04                 # window sills and balcony ledges (share of a storey)
_ROOF_EDGE = 0.06             # the band along the top of the wall (share of a storey)
_MULLIONS = 4                 # panes across a glazed balcony
_TV_SHARE = 0.2               # share of lit windows lit by a television (cold) instead of a lamp (warm)
_PARAPET = (0.08, 0.55)       # balcony parapet: side inset (share of bay), top (share down the window)
_DOOR = (0.42, 0.72)          # entrance door width (share of bay) and height (share of storey)
_ANTENNA_M = (2.2, 3.4)       # roof antenna height range
_STREAK_STRETCH = (1.0, 8.0)  # rain streaks run down the panels

# --- poles, towers, wires, trees (screen px, as shares of the object's height) ----------------
_POLE_WIDTH = 0.018           # of the pole height
_POLE_ARM = (0.06, 0.30)      # crossarm: drop below the top, length
_PYLON_LEVELS = (0.0, 0.32, 0.58, 0.82, 1.0)       # heights where the lattice changes width
_PYLON_HALF = (0.17, 0.09, 0.05, 0.035, 0.012)     # half-width of the body at each level
_PYLON_ARMS = ((0.60, 0.24), (0.80, 0.17))         # (height, half span) of the two crossarms
_PYLON_LINE = 0.006           # lattice line width share of the height
_WIRE_SAMPLES = 24
_TREE_DEPTH = 6               # branching levels of a bare tree
_TREE_SHRINK = (0.72, 0.62)   # length and width of a child branch relative to its parent
_BIRCH_MARKS = 9              # dark marks on a birch trunk

# --- snow, smoke, light ----------------------------------------------------------------------
_SUBPIXEL = 4                 # cv2 drawing shift: 1/16 px precision for snow flakes
_NEAR_FLAKES = 0.12           # share of flakes close to the camera: big and out of focus
_SMOKE_SAMPLES = 40
_SMOKE_GROWTH = 4.0           # a smoke wisp ends this many times wider than it starts

# --- finish ----------------------------------------------------------------------------------
_GRADE_SHADOWS, _GRADE_HIGHLIGHTS = '#1e3a48', '#ffc27a'
_POSTER_LEVELS = 18           # light banding, like an old print or a low-bitrate frame


def _rng(seed):
    return np.random.default_rng(config.DEFAULT_SEED if seed is None else seed)


def _rects(cv, boxes):
    return cv.polygon(*[np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) for x0, y0, x1, y1 in boxes]) \
        if boxes else cv.empty()


def panel_facade(width_m, floors, wall=None, lit_ratio=0.2, balconies=0.45, glazed=0.5, entrances=0, windows=True,
                 resolution=None, seed=None):
    """One face of a panel apartment block, painted flat. Returns a Canvas to paste().

    floors: storeys. lit_ratio: share of lit windows. balconies: share of window columns with a stack
    of balconies (glazed: share of those balconies closed with glass). entrances: doors along the
    ground floor, each with a canopy and a lamp. windows=False gives a blank end wall (joints only).
    resolution: px per meter (default from _PANEL_RES)."""
    rng = _rng(seed)
    wall = PALETTE['concrete'] if wall is None else wall
    scale = resolution or _PANEL_RES[0] * 2
    width, height = max(int(width_m * scale), 8), max(int(floors * _FLOOR_M * scale), 8)
    cv = Canvas(width, height, wall)
    cols = max(int(round(width_m / _BAY_M)), 1)
    cell_w, cell_h = width / cols, height / floors
    streaks = cv.noise(scale=max(cell_w, 4.0), octaves=3, seed=int(rng.integers(1 << 30)), stretch=_STREAK_STRETCH)
    cv.tint(raster.smoothstep(streaks, 0.55, 0.85), shadow_of(wall, 0.7), 'normal', 0.35)
    cv.tint(cv.full() * cv.linear((0, height * 0.6), (0, height)), shadow_of(wall, 0.8), 'normal', 0.3)
    seam = max(_JOINT_M * scale, 0.6)
    joints = [(0, row * cell_h - seam, width, row * cell_h + seam) for row in range(1, floors)]
    joints += [(col * cell_w - seam, 0, col * cell_w + seam, height) for col in range(1, cols)]
    cv.fill(_rects(cv, joints), PALETTE['seam'], 0.8)
    cv.fill(_rects(cv, [(0, 0, width, max(cell_h * _ROOF_EDGE, 1.5))]), adjust(wall, lightness=0.08))
    if not windows:
        return cv
    doors = set(np.linspace(0, cols - 1, entrances + 2)[1:-1].round().astype(int)) if entrances else set()
    stacks = {col for col in range(cols) if col not in doors and rng.random() < balconies}
    dark, warm, tv, parapets, glass_fronts, canopies, door_boxes, lamps = [], [], [], [], [], [], [], []
    for row in range(floors):
        ground = row == floors - 1
        for col in range(cols):
            if ground and col in doors:
                x0 = (col + 0.5 - _DOOR[0] / 2) * cell_w
                door_boxes.append((x0, (row + 1 - _DOOR[1]) * cell_h, x0 + _DOOR[0] * cell_w, (row + 1) * cell_h))
                canopies.append((x0 - _CANOPY[0] * cell_w, (row + 1 - _DOOR[1] - _CANOPY[1]) * cell_h,
                                 x0 + (_DOOR[0] + _CANOPY[0]) * cell_w, (row + 1 - _DOOR[1]) * cell_h))
                lamps.append(((col + 0.5) * cell_w, (row + 1 - _DOOR[1] - _DOOR_LAMP) * cell_h))
                continue
            x0 = (col + 0.5 - _WINDOW[0] / 2) * cell_w
            y0 = (row + 0.45 - _WINDOW[1] / 2) * cell_h
            box = (x0, y0, x0 + _WINDOW[0] * cell_w, y0 + _WINDOW[1] * cell_h)
            if rng.random() < lit_ratio:
                (tv if rng.random() < _TV_SHARE else warm).append(box)
            else:
                dark.append(box)
            if col in stacks and not ground:
                front = (col * cell_w + _PARAPET[0] * cell_w, y0 + _PARAPET[1] * _WINDOW[1] * cell_h,
                         (col + 1) * cell_w - _PARAPET[0] * cell_w, (row + 1) * cell_h - 0.05 * cell_h)
                (glass_fronts if rng.random() < glazed else parapets).append(front)
    cv.fill(_rects(cv, dark), PALETTE['glass'])
    cv.fill(_rects(cv, warm), PALETTE['window_warm'])
    cv.fill(_rects(cv, tv), PALETTE['window_tv'])
    sills = [(x0 - 1, y1, x1 + 1, y1 + max(cell_h * _LEDGE, 1.0)) for x0, _, x1, y1 in dark + warm + tv]
    cv.fill(_rects(cv, sills), adjust(wall, lightness=0.07))
    if parapets:
        fronts = _rects(cv, parapets)
        cv.fill(fronts, adjust(wall, lightness=0.05))
        cv.fill(_rects(cv, [(x0, y1 - max(cell_h * 0.05, 1.0), x1, y1) for x0, _, x1, y1 in parapets]),
                shadow_of(wall, 0.9))
    if glass_fronts:
        fronts = _rects(cv, glass_fronts)
        cv.fill(fronts, mix(PALETTE['glass'], wall, 0.35))
        mullions = [(x0 + (x1 - x0) * k / _MULLIONS - 0.6, y0, x0 + (x1 - x0) * k / _MULLIONS + 0.6, y1)
                    for x0, y0, x1, y1 in glass_fronts for k in range(1, _MULLIONS)]
        cv.fill(_rects(cv, mullions), adjust(wall, lightness=0.1), 0.8)
        cv.fill(_rects(cv, [(x0, y0, x1, y0 + max(cell_h * _LEDGE, 1.0)) for x0, y0, x1, _ in glass_fronts]),
                adjust(wall, lightness=0.1))
    if door_boxes:
        cv.fill(_rects(cv, door_boxes), '#3a3430')
        cv.fill(_rects(cv, canopies), adjust(wall, lightness=0.1))
        for x, y in lamps:
            cv.tint(cv.radial((x, y), cell_w * 0.7) ** 2, PALETTE['sodium'], 'screen', 0.7)
            cv.fill(cv.ellipse(x, y, max(cell_w * 0.05, 1.0)), PALETTE['sodium_core'])
    return cv


def _eye(view):
    return np.asarray(view.position, np.float64)


def panel_block(cv, view, x0, x1, z0, z1, floors, wall=None, lit_ratio=0.2, balconies=0.45, glazed=0.5, entrances=2,
                antennas=2, shade=0.45, haze=None, haze_amount=0.0, seed=None):
    """A panel apartment block standing on the ground: footprint x0..x1, z0..z1 meters, `floors` storeys.

    Paints the faces turned toward the view's eye: the long faces get windows, balconies and entrances,
    the short ends are blank walls in shade. haze/haze_amount fade it toward the air (far blocks).
    Works with city.Perspective and city.Camera. Returns the covered mask."""
    rng = _rng(seed)
    wall = PALETTE['concrete'] if wall is None else wall
    height = floors * _FLOOR_M
    eye = _eye(view)
    long_x = (x1 - x0) >= (z1 - z0)
    faces = []
    if eye[2] < z0:
        faces.append(([(x0, height, z0), (x1, height, z0), (x1, 0.0, z0), (x0, 0.0, z0)], x1 - x0, long_x, 0.0))
    if eye[2] > z1:
        faces.append(([(x1, height, z1), (x0, height, z1), (x0, 0.0, z1), (x1, 0.0, z1)], x1 - x0, long_x, shade))
    if eye[0] < x0:
        faces.append(([(x0, height, z1), (x0, height, z0), (x0, 0.0, z0), (x0, 0.0, z1)], z1 - z0, not long_x, shade))
    if eye[0] > x1:
        faces.append(([(x1, height, z0), (x1, height, z1), (x1, 0.0, z1), (x1, 0.0, z0)], z1 - z0, not long_x, shade))
    covered = cv.empty()
    for corners, width_m, long_face, darkness in faces:
        nearest = min(view.depth(*corner) for corner in corners)
        resolution = float(np.clip(view.scale(max(nearest, 0.5)), *_PANEL_RES))
        texture = panel_facade(width_m, floors, wall, lit_ratio if long_face else 0.0, balconies, glazed,
                               entrances if long_face else 0, windows=long_face, resolution=resolution,
                               seed=int(rng.integers(1 << 30)))
        cover = cv.paste(texture, view.quad(corners))
        if darkness > 0:
            cv.tint(cover, '#4a5464', 'multiply', darkness)
        if haze is not None and haze_amount > 0:
            cv.tint(cover, haze, 'normal', haze_amount)
        covered = np.maximum(covered, cover)
    roof = []
    for _ in range(antennas):                                   # TV antennas along the roof
        x, z = rng.uniform(x0 + 1.0, x1 - 1.0), rng.uniform(z0 + 1.0, z1 - 1.0)
        tall = rng.uniform(*_ANTENNA_M)
        foot, top = view.project(x, height, z), view.project(x, height + tall, z)
        reach = view.scale_at(x, height, z)
        bar = [view.project(x - 0.6, height + tall * 0.8, z), view.project(x + 0.6, height + tall * 0.8, z)]
        roof += [(np.array([foot, top]), max(0.06 * reach, 0.8), 'flat'), (np.array(bar), max(0.05 * reach, 0.7), 'flat')]
    if roof:
        mast = cv.ribbons(roof)
        cv.fill(mast, haze if haze is not None and haze_amount > 0.5 else PALETTE['night'], 0.85)
    return covered


# --- poles, towers and wires (screen space) ---------------------------------------------------

def utility_pole(cv, base, height, color=None, arm=True):
    """A concrete pole standing at base (px) with a crossarm and insulators. Returns the points
    to hang wires on (left to right)."""
    color = PALETTE['night'] if color is None else color
    x, y = base
    width = max(height * _POLE_WIDTH, 1.5)
    top = (x, y - height)
    cv.fill(cv.ribbon([base, top], width, [1.0, 0.7], smooth=False), color)
    if not arm:
        return [top]
    arm_y = y - height * (1.0 - _POLE_ARM[0])
    half = height * _POLE_ARM[1] / 2.0
    cv.fill(cv.ribbon([(x - half, arm_y), (x + half, arm_y)], width * 0.6, 'flat', smooth=False), color)
    anchors = [(x + half * k, arm_y - width * 0.9) for k in (-0.95, -0.4, 0.4, 0.95)]
    for ax, ay in anchors:
        cv.fill(cv.ellipse(ax, ay + width * 0.3, width * 0.35, width * 0.6), color)
    return anchors


def pylon(cv, base, height, color=None):
    """A lattice power tower standing at base (px). Returns the tips of its crossarms (left to right,
    lower arm first) to hang wires on."""
    color = PALETTE['night'] if color is None else color
    x, y = base
    line = max(height * _PYLON_LINE, 0.8)
    levels = [(y - height * level, height * half) for level, half in zip(_PYLON_LEVELS, _PYLON_HALF)]
    strokes = []
    for side in (-1, 1):                                    # the two legs
        strokes.append((np.array([(x + side * half, level_y) for level_y, half in levels]), line * 1.4, 'flat'))
    for (y_low, half_low), (y_high, half_high) in zip(levels[:-1], levels[1:]):
        strokes.append((np.array([(x - half_low, y_low), (x + half_high, y_high)]), line, 'flat'))   # cross bracing
        strokes.append((np.array([(x + half_low, y_low), (x - half_high, y_high)]), line, 'flat'))
        strokes.append((np.array([(x - half_high, y_high), (x + half_high, y_high)]), line, 'flat'))
    tips = []
    for level, span in _PYLON_ARMS:
        arm_y = y - height * level
        reach = height * span
        for side in (-1, 1):
            tip = (x + side * reach, arm_y)
            strokes.append((np.array([(x, arm_y - height * 0.03), tip]), line, 'flat'))
            strokes.append((np.array([(x, arm_y), tip]), line, 'flat'))
            tips.append(tip)
    cv.fill(cv.ribbons(strokes), color)
    tips.sort(key=lambda tip: (-tip[1], tip[0]))
    return tips


def wires(cv, spans, sag=0.05, width=1.2, color=None, opacity=0.9):
    """Sagging wires between pairs of points: spans = [(start, end), ...] in px. sag: drop at
    mid-span as a share of the span length. Returns the mask."""
    color = PALETTE['night'] if color is None else color
    t = np.linspace(0.0, 1.0, _WIRE_SAMPLES)
    strokes = []
    for start, end in spans:
        start, end = np.asarray(start, np.float64), np.asarray(end, np.float64)
        drop = sag * float(np.linalg.norm(end - start)) * 4.0 * t * (1.0 - t)
        points = start[None] + (end - start)[None] * t[:, None] + np.stack([np.zeros_like(t), drop], axis=1)
        strokes.append((points, width, 'flat'))
    mask = cv.ribbons(strokes) if strokes else cv.empty()
    cv.fill(mask, color, opacity)
    return mask


def bare_tree(cv, base, height, color=None, birch=False, spread=26.0, lean=0.0, seed=None):
    """A leafless winter tree standing at base (px). birch=True: a pale trunk with dark marks.
    lean: degrees the trunk leans toward screen right. Returns the mask."""
    rng = _rng(seed)
    color = PALETTE['night'] if color is None else color
    strokes, trunk = [], []

    def grow(start, angle, length, width, depth):
        direction = np.array([np.sin(np.radians(angle)), -np.cos(np.radians(angle))])
        bend = np.array([direction[1], -direction[0]]) * rng.uniform(-0.12, 0.12) * length
        end = start + direction * length
        points = np.array([start, (start + end) / 2.0 + bend, end])
        strokes.append((points, width, [1.0, _TREE_SHRINK[1] ** 0.5]))
        if depth >= _TREE_DEPTH - 1:                       # the trunk and the main limbs
            trunk.append((points, width))
        if depth <= 1:
            return
        for _ in range(int(rng.integers(2, 4))):
            grow(end - direction * length * rng.uniform(0.0, 0.3), angle + rng.uniform(-spread, spread) * 1.4,
                 length * rng.uniform(_TREE_SHRINK[0] * 0.85, _TREE_SHRINK[0] * 1.1), width * _TREE_SHRINK[1], depth - 1)

    grow(np.asarray(base, np.float64), lean, height * 0.36, max(height * 0.045, 1.5), _TREE_DEPTH)
    mask = cv.ribbons(strokes)
    cv.fill(mask, color)
    if birch and trunk:                                    # white bark on the trunk and main limbs, dark marks
        stem = cv.ribbons([(points, width * 0.86, [1.0, _TREE_SHRINK[1] ** 0.5]) for points, width in trunk])
        cv.fill(stem, '#d4d1c9')
        marks = []
        for points, width in trunk:
            for _ in range(max(_BIRCH_MARKS * len(points) // (3 * len(trunk)), 2)):
                t = rng.uniform(0.05, 0.95)
                center = points[0] + (points[-1] - points[0]) * t
                half = width * rng.uniform(0.2, 0.45)
                marks.append((np.array([center - (half, 0), center + (half, 0)]), max(width * 0.14, 0.8), 'taper'))
        cv.fill(cv.ribbons(marks) * stem, '#2a2c30')
    return mask


# --- snow, smoke and light ---------------------------------------------------------------------

def snowfall(cv, count, size=2.2, color=None, region=None, opacity=0.85, seed=None):
    """Falling snow: `count` flakes of radius around `size` px; a few near the camera come big and
    blurred. region: (x0, y0, x1, y1) px (default the whole canvas). Returns the mask."""
    rng = _rng(seed)
    color = PALETTE['snow'] if color is None else color
    x0, y0, x1, y1 = region or (0, 0, cv.width, cv.height)
    layers = []
    for share, scale, soft in ((1.0 - _NEAR_FLAKES, 1.0, 0.0), (_NEAR_FLAKES, 3.2, 2.5)):
        canvas = np.zeros((cv.height, cv.width), np.uint8)
        for _ in range(int(count * share)):
            radius = size * scale * rng.uniform(0.5, 1.4)
            center = (int(rng.uniform(x0, x1) * (1 << _SUBPIXEL)), int(rng.uniform(y0, y1) * (1 << _SUBPIXEL)))
            cv2.circle(canvas, center, max(int(radius * (1 << _SUBPIXEL)), 1), 255, -1, cv2.LINE_AA, _SUBPIXEL)
        layer = canvas.astype(np.float32) / 255.0
        layers.append(raster.blur(layer, soft * size) if soft > 0 else layer)
    mask = np.maximum(layers[0], layers[1] * 0.7)
    cv.tint(mask, color, 'normal', opacity)
    return mask


def smoke(cv, start, rise, drift=0.0, width=3.0, color='#c3c9cf', opacity=0.45, strands=4, seed=None):
    """Smoke drifting up from start (px): thin wisps that sway more as they climb and part from each
    other, over a faint haze. rise: px it climbs; drift: px it leans sideways by the top.
    width: px of a wisp at its start. For cigarettes, breath and chimneys. Returns the mask."""
    rng = _rng(seed)
    t = np.linspace(0.0, 1.0, _SMOKE_SAMPLES)
    strokes = []
    for _ in range(strands):
        phase, cycles = rng.uniform(0, 2 * np.pi), rng.uniform(1.4, 2.6)
        sway = rise * rng.uniform(0.05, 0.11)
        part = drift * rng.uniform(0.6, 1.4) + rise * rng.uniform(-0.12, 0.12)    # wisps fan out as they rise
        xs = start[0] + part * t ** 1.4 + sway * t ** 1.2 * np.sin(2 * np.pi * cycles * t + phase)
        ys = start[1] - rise * t * rng.uniform(0.75, 1.0)
        strokes.append((np.stack([xs, ys], axis=1), width * rng.uniform(0.6, 1.1),
                        list(1.0 + _SMOKE_GROWTH * np.linspace(0.0, 1.0, 8) ** 1.5)))
    wisps = cv.ribbons(strokes)
    mask = np.maximum(raster.blur(wisps, width * 0.6), 0.35 * raster.blur(wisps, width * 4.0))
    fade = 1.0 - cv.linear(start, (start[0] + drift, start[1] - rise))
    mask = np.clip(mask, 0.0, 1.0) * fade ** 1.3
    cv.tint(mask, color, 'normal', opacity)
    return mask


def lamp_glow(cv, point, radius, color=None, strength=0.8):
    """Halo of a sodium lamp (or a lit window) at point (px)."""
    color = PALETTE['sodium'] if color is None else color
    cv.tint(cv.radial(point, radius) ** 2.0, color, 'screen', strength)
    cv.tint(cv.radial(point, radius * 0.12), PALETTE['sodium_core'], 'screen', min(strength + 0.15, 1.0))


def cigarette(cv, base, tip, width, lit=True):
    """A cigarette from base (the filter end, at the lips or fingers) to tip (px). Returns the tip,
    where smoke starts."""
    base, tip = np.asarray(base, np.float64), np.asarray(tip, np.float64)
    filter_end = base + (tip - base) * 0.3
    paper = cv.ribbon([filter_end, tip], width, 'flat', smooth=False)
    cork = cv.ribbon([base, filter_end], width, 'flat', smooth=False)
    body = np.maximum(paper, cork)
    cv.fill(paper, '#e9e4da')
    cv.fill(cork, '#c58a55')
    cv.outline(body, max(width * 0.18, 0.8), '#2e2a2c', opacity=0.7)
    if lit:
        cv.fill(cv.ellipse(tip[0], tip[1], width * 0.55), PALETTE['ember'])
        lamp_glow(cv, tuple(tip), width * 3.5, PALETTE['ember'], 0.6)
    return tuple(tip)


def mouth_point(head, side=1.0):
    """Corner of the mouth (px) on `side` (+1 screen right) and the unit screen direction the face
    points to. Place a cigarette from here along that direction, drooping a little."""
    corner = np.asarray(head.at(side * 8.0, 0.68), np.float64)
    ahead = np.asarray(head.at(side * 8.0, 0.68, forward=1.0), np.float64) - corner
    norm = np.linalg.norm(ahead)
    return tuple(corner), (tuple(ahead / norm) if norm > 1e-6 else (side, 0.0))


# --- finish --------------------------------------------------------------------------------------

def finish(cv, glow=0.3, warmth=0.5, fade=0.35, saturation=0.68, grain_amount=0.045, vignette_strength=0.32,
           posterize=0.18, seed=None):
    """The doomer grade: softened colored lines, a glow around lamps and windows, low saturation,
    teal shadows and sodium-orange lights (warmth 0..1), blacks lifted toward navy (fade), light
    banding, coarse grain and a dark vignette. Returns an (H, W, 3) image."""
    alpha = cv2.GaussianBlur(cv.line_alpha, (0, 0), 0.7)
    image = finishes._composite_lines(cv.color, cv, 0.85, alpha)
    image = cv2.bilateralFilter(image.astype(np.float32), d=0, sigmaColor=0.05, sigmaSpace=3.0)
    image = finishes.bloom(image, threshold=0.70, radius=16.0, strength=glow)
    image = finishes.grade(image, contrast=1.06, saturation=saturation, shadows=_GRADE_SHADOWS, amount=0.16)
    image = finishes.grade(image, highlights=_GRADE_HIGHLIGHTS, amount=0.18 * warmth)
    darkness = (1.0 - luminance(image))[..., None] ** 2
    image = image + (rgb(PALETTE['night']) - image) * fade * darkness
    stepped = np.round(image * _POSTER_LEVELS) / _POSTER_LEVELS
    image = image + (stepped - image) * posterize
    image = finishes.grain(image, grain_amount, seed, size=1.4)
    return finishes.vignette(np.clip(image, 0.0, 1.0).astype(np.float32), vignette_strength, PALETTE['night'])
