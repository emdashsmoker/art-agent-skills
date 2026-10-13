"""Outdoor world for 3D scenes: panel apartment blocks, open ground, sky, lamp light, wires and weather.

Interior rooms are stage sets of painted quads (interior.Surface); outdoors works the same way at a
larger scale. Buildings are boxes of painted facades, the ground is one big painted plane, and both
are drawn before the 3D items, so figures, lamps and benches stand in front of them in one picture.
Everything is placed in the same world as scene3d (head heights, floor y = 0, y down; metres() converts).

    world = World(light=NIGHT, sky=NIGHT_SKY, fog=FOG_NIGHT,
                  ground=ground_plane(snow_texture(rng, NIGHT, extent), extent),
                  blocks=[panel_block((0, metres(-80)), metres(90), 9, rng)],
                  lamps=[street3d.lamp_light(lamp)], items=[lamp, figure], snow=SNOW_LIGHT)
    draw_world(painter, camera, world, rng)

draw_world runs, in order: sky, ground, lamp pools (light_ground), wet reflections, blocks far to near,
the 3D items under night_lighting (lamps light them, screens and bulbs stay bright), wires, haze and snow.
"""
from dataclasses import dataclass, replace

import cv2
import numpy as np

from . import scene3d, shading
from .body3d import EMPTY, rot_y
from .config import rgb
from .interior import Surface, draw_surface, keep_detail
from .props3d import cm

FLOOR_HEIGHT = 2.8                 # metres, a typical panel block storey
BAY_WIDTH = 3.2                    # metres between window axes
FACADE_TEXELS_PER_METRE = 7.0      # facade texture density (a window is about ten texels wide)
GROUND_TEXELS_PER_HEAD = 3.0
GROUND_TEXTURE_MIN, GROUND_TEXTURE_MAX = 64, 4096   # texels along a side of the ground texture
DRIFT_SHADE = 0.25                 # how far drift hollows lean to the shade colour
PATH_SHADE = 0.55                  # how far a trodden path leans to the shade colour
CLOUD_CELL = 260.0                 # canvas units of the largest cloud blobs
WINDOW_SIZE = (0.46, 0.50)         # window width and height as a share of the bay and the storey
PARAPET = 0.6                      # metres of wall above the top storey


def metres(value):
    """Metres to head heights."""
    return cm(value * 100.0)


# ---- looks ------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Light:
    """How the outdoor parts are lit: night (lit windows, dark walls) or an overcast day."""
    wall: np.ndarray                 # concrete in this light
    seam: np.ndarray                 # panel joints
    glass: np.ndarray                # unlit window
    lit: tuple                       # colours of lit windows
    lit_share: float                 # share of windows lit
    balcony: np.ndarray
    snow: np.ndarray                 # open snow
    snow_shade: np.ndarray           # drift hollows and trodden paths
    ambient: np.ndarray              # what figures and objects keep of their colour away from any lamp


NIGHT = Light(wall=rgb("#3E4650"), seam=rgb("#2A3038"), glass=rgb("#161C26"),
              lit=(rgb("#F3C47E"), rgb("#E9A962"), rgb("#F7DDA6"), rgb("#8FB3CF"), rgb("#D9905A")), lit_share=0.22,
              balcony=rgb("#30373F"), snow=rgb("#6F7C8C"), snow_shade=rgb("#4A5462"),
              ambient=np.array([0.40, 0.45, 0.56], dtype=np.float32))
DUSK = Light(wall=rgb("#5E6670"), seam=rgb("#454C55"), glass=rgb("#2A3240"),
             lit=(rgb("#F3C47E"), rgb("#E9A962"), rgb("#F7DDA6"), rgb("#8FB3CF")), lit_share=0.14,
             balcony=rgb("#4C535C"), snow=rgb("#9AA3AE"), snow_shade=rgb("#6C7684"),
             ambient=np.array([0.62, 0.64, 0.72], dtype=np.float32))
OVERCAST = Light(wall=rgb("#9EA3A6"), seam=rgb("#7C8286"), glass=rgb("#4E5862"), lit=(rgb("#C8B88A"),),
                 lit_share=0.03, balcony=rgb("#858B90"), snow=rgb("#D3D8DA"), snow_shade=rgb("#A6AEB4"),
                 ambient=np.array([0.92, 0.94, 0.96], dtype=np.float32))


@dataclass(frozen=True)
class Lamp:
    """A light source that lights the figures and objects round it (a street lamp, a lit doorway)."""
    at: tuple                        # world point of the bulb
    color: np.ndarray
    reach: float                     # head heights at which its light has fallen to half
    strength: float = 1.0
    cone: float = None               # half angle (radians from straight down) of a shaded lamp's light; None all round


SODIUM = rgb("#F2A65A")


@dataclass(frozen=True)
class Fog:
    color: np.ndarray
    distance: float                  # head heights at which fog covers a little over half
    horizon_band: float              # canvas units of haze above and below the horizon
    horizon_strength: float


FOG_NIGHT = Fog(color=rgb("#2C3846"), distance=metres(220.0), horizon_band=70.0, horizon_strength=0.55)
FOG_DUSK = Fog(color=rgb("#56606C"), distance=metres(180.0), horizon_band=90.0, horizon_strength=0.60)
FOG_OVERCAST = Fog(color=rgb("#B4BABC"), distance=metres(140.0), horizon_band=110.0, horizon_strength=0.75)

NIGHT_SKY = ((0.0, rgb("#0E141E")), (0.55, rgb("#1C2634")), (1.0, rgb("#34404E")))
DUSK_SKY = ((0.0, rgb("#1E2A3C")), (0.45, rgb("#3C4A5C")), (0.75, rgb("#7A7270")), (1.0, rgb("#B08A6A")))
OVERCAST_SKY = ((0.0, rgb("#848C92")), (0.6, rgb("#A4AAAE")), (1.0, rgb("#C2C6C6")))


@dataclass(frozen=True)
class Snow:
    count: int                       # flakes per million square canvas units
    size: tuple                      # canvas units: smallest and largest flake
    opacity: float
    streak: float                    # vertical stretch of the near flakes (falling)


SNOW_LIGHT = Snow(count=900, size=(0.8, 3.6), opacity=0.7, streak=1.6)
SNOW_HEAVY = Snow(count=1400, size=(0.9, 4.2), opacity=0.75, streak=2.0)


# ---- facades ----------------------------------------------------------------------------------------------------
STAIN = (0.92, 0.12)               # concrete weathering: base brightness and its uneven spread
STAIN_CELL = 24                    # texels per weathering blotch
WINDOW_SILL = 0.30                 # share of a storey below a window
LIT_SPREAD, DARK_SPREAD = (0.80, 1.05), (0.85, 1.25)   # brightness variation of lit and of dark windows
BALCONY_TOP = 0.72                 # share of a storey above which a balcony parapet covers the wall
BALCONY_REACH = 0.15               # share of a bay a balcony stands out past its window either side
BALCONY_SHARE = 4                  # one bay in this many has a column of balconies
CURTAIN_CHANCE, CURTAIN_DIM = 0.5, 0.72   # half-drawn curtains in lit windows
MULLION_DIM = 0.6
ENTRANCE = (0.32, 0.68, 0.25, 0.18)        # door from and to (share of the bay), door top and canopy (share of storey)


def facade(length, floors, rng, light, entrances=0, balconies=True):
    """Elevation texture of a panel block wall: storeys of identical windows, panel joints, balcony
    columns and, at the foot, entrance doors under small canopies. length in metres."""
    density = FACADE_TEXELS_PER_METRE
    height = floors * FLOOR_HEIGHT + PARAPET
    w, h = max(8, int(length * density)), max(8, int(height * density))
    image = np.empty((h, w, 3), dtype=np.float32)
    image[:] = light.wall
    stain = cv2.resize(rng.random((max(2, h // STAIN_CELL), max(2, w // STAIN_CELL))).astype(np.float32), (w, h),
                       interpolation=cv2.INTER_CUBIC)
    image *= (STAIN[0] + STAIN[1] * stain)[..., None]
    bays = max(1, int(length / BAY_WIDTH))
    bay_px, floor_px = w / bays, FLOOR_HEIGHT * density
    top = PARAPET * density
    # Panel joints: one horizontal line per storey, one vertical line per bay.
    for k in range(floors + 1):
        y = int(top + k * floor_px)
        image[max(0, y - 1):y + 1] = light.seam
    for k in range(bays + 1):
        x = int(k * bay_px)
        image[:, max(0, x - 1):x + 1] = light.seam
    balcony_bays = set(rng.choice(bays, size=max(1, bays // BALCONY_SHARE), replace=False)) \
        if balconies and bays > 2 else set()
    entrance_bays = set(np.linspace(1, bays - 2, entrances).astype(int)) if entrances and bays > 2 else set()
    for floor in range(floors):
        for bay in range(bays):
            x0 = (bay + 0.5 - WINDOW_SIZE[0] / 2) * bay_px
            y0 = top + (floor + WINDOW_SILL) * floor_px
            x1, y1 = x0 + WINDOW_SIZE[0] * bay_px, y0 + WINDOW_SIZE[1] * floor_px
            ground = floor == floors - 1
            if ground and bay in entrance_bays:
                _entrance(image, bay, bay_px, top + floor * floor_px, floor_px, light)
                continue
            lit = rng.random() < light.lit_share
            color = light.lit[rng.integers(len(light.lit))] * rng.uniform(*LIT_SPREAD) if lit else \
                light.glass * rng.uniform(*DARK_SPREAD)
            _window(image, x0, y0, x1, y1, color, lit, rng)
            if bay in balcony_bays and not ground:
                yb = int(top + (floor + BALCONY_TOP) * floor_px)
                reach = BALCONY_REACH * bay_px
                image[yb:int(top + (floor + 1) * floor_px) - 1, int(x0 - reach):int(x1 + reach)] = \
                    light.balcony * rng.uniform(0.9, 1.1)
    return np.clip(image, 0.0, 1.0)


def _window(image, x0, y0, x1, y1, color, lit, rng):
    xa, ya, xb, yb = int(x0), int(y0), max(int(x1), int(x0) + 2), max(int(y1), int(y0) + 2)
    image[ya:yb, xa:xb] = color
    if lit and rng.random() < CURTAIN_CHANCE:
        mid = (xa + xb) // 2
        side = slice(xa, mid) if rng.random() < 0.5 else slice(mid, xb)
        image[ya:yb, side] = color * CURTAIN_DIM
    middle = (xb - xa) // 2
    image[ya:yb, xa + middle:xa + middle + 1] *= MULLION_DIM


def _entrance(image, bay, bay_px, floor_top, floor_px, light):
    door_from, door_to, door_top, canopy_at = ENTRANCE
    x0, x1 = int((bay + door_from) * bay_px), int((bay + door_to) * bay_px)
    image[int(floor_top + door_top * floor_px):int(floor_top + floor_px), x0:x1] = light.glass * 0.7
    canopy = int(floor_top + canopy_at * floor_px)
    image[canopy:canopy + 2, int(x0 - 0.12 * bay_px):int(x1 + 0.12 * bay_px)] = light.seam * 0.8
    cv2.circle(image, (int((x0 + x1) / 2), canopy + 4), 2, tuple(float(c) for c in light.lit[0]), -1)


@dataclass
class Block:
    surfaces: list                   # facades and roof, each an interior.Surface
    center: np.ndarray               # world point at the middle of the block's base


def panel_block(at, length, floors, rng, light=NIGHT, depth=metres(12.0), yaw=0.0, entrances=3):
    """A panel apartment block: a box whose long faces are window walls and whose ends are blank
    (or have a column of small windows). at: (x, z) of the base centre; length and depth in head
    heights; yaw turns the long side away from facing +z."""
    length_m, depth_m = length / metres(1.0), depth / metres(1.0)
    height = metres(floors * FLOOR_HEIGHT + PARAPET)
    turn = rot_y(yaw)
    center = np.array([at[0], 0.0, at[1]], dtype=np.float64)

    def corner(x, y, z):
        return tuple(center + turn @ np.array([x, y, z]))

    hx, hz = length / 2, depth / 2
    front = facade(length_m, floors, rng, light, entrances)
    back = facade(length_m, floors, rng, light, 0)
    end = facade(depth_m, floors, rng, replace_light(light, lit_share=light.lit_share * 0.5), 0, balconies=False)
    roof = np.empty((8, 8, 3), dtype=np.float32)
    roof[:] = light.seam
    surfaces = [Surface((corner(-hx, -height, -hz), corner(hx, -height, -hz), corner(hx, -height, hz),
                         corner(-hx, -height, hz)), roof, tuple(turn @ np.array([0.0, -1.0, 0.0]))),
                Surface((corner(-hx, -height, hz), corner(hx, -height, hz), corner(hx, 0, hz), corner(-hx, 0, hz)), front,
                        tuple(turn @ np.array([0.0, 0.0, 1.0]))),
                Surface((corner(hx, -height, -hz), corner(-hx, -height, -hz), corner(-hx, 0, -hz), corner(hx, 0, -hz)), back,
                        tuple(turn @ np.array([0.0, 0.0, -1.0]))),
                Surface((corner(hx, -height, hz), corner(hx, -height, -hz), corner(hx, 0, -hz), corner(hx, 0, hz)), end,
                        tuple(turn @ np.array([1.0, 0.0, 0.0]))),
                Surface((corner(-hx, -height, -hz), corner(-hx, -height, hz), corner(-hx, 0, hz), corner(-hx, 0, -hz)),
                        end, tuple(turn @ np.array([-1.0, 0.0, 0.0])))]
    return Block(surfaces, center)


def replace_light(light, **changes):
    return replace(light, **changes)


FACADE_DETAIL = 0.7                # painterly brush detail on facades: rows of windows stay windows


def draw_blocks(canvas, camera, blocks, fog=None):
    """Paint the blocks far to near, each faded into the fog by its distance from the eye."""
    eye = camera.eye()
    eye = np.asarray(camera.target, dtype=np.float64) if eye is None else eye
    for block in sorted(blocks, key=lambda b: -float(np.linalg.norm(b.center - eye))):
        distance = float(np.linalg.norm(block.center - eye))
        for surface in block.surfaces:
            keep_detail(canvas, draw_surface(canvas, camera, fogged(surface, distance, fog)), FACADE_DETAIL)


def fogged(surface, distance, fog):
    if fog is None:
        return surface
    amount = 1.0 - np.exp(-distance / fog.distance)
    texture = surface.texture * (1.0 - amount) + fog.color * amount
    return Surface(surface.corners, texture.astype(np.float32), surface.facing)


# ---- ground and sky ---------------------------------------------------------------------------------------------
def ground_plane(texture, extent=metres(600.0), center=(0.0, 0.0)):
    """A square of ground at y = 0 round center (x, z), painted with texture."""
    cx, cz = center
    half = extent / 2
    return Surface(((cx - half, 0.0, cz - half), (cx + half, 0.0, cz - half), (cx + half, 0.0, cz + half),
                    (cx - half, 0.0, cz + half)), texture, (0.0, -1.0, 0.0))


def snow_texture(rng, light, extent=metres(600.0), paths=()):
    """Snow-covered ground in this light: soft drifts, and trodden paths ((polyline of (x, z) in the
    plane's own coordinates 0..extent, width) pairs) where the snow is packed and darker."""
    size = min(GROUND_TEXTURE_MAX, max(GROUND_TEXTURE_MIN, int(extent * GROUND_TEXELS_PER_HEAD)))
    drift = cv2.resize(rng.random((24, 24)).astype(np.float32), (size, size), interpolation=cv2.INTER_CUBIC)
    image = light.snow * (1 - drift[..., None] * DRIFT_SHADE) + light.snow_shade * (drift[..., None] * DRIFT_SHADE)
    scale = size / extent
    for path, width in paths:
        points = (np.asarray(path, dtype=np.float64) * scale).astype(np.int32).reshape(-1, 1, 2)
        mask = np.zeros((size, size), dtype=np.float32)
        cv2.polylines(mask, [points], False, 1.0, max(1, int(width * scale)), cv2.LINE_AA)
        mask = cv2.GaussianBlur(mask, (0, 0), max(1.0, width * scale * 0.3))[..., None] * PATH_SHADE
        image = image * (1 - mask) + light.snow_shade * mask
    return np.clip(image, 0.0, 1.0).astype(np.float32)


def asphalt_texture(rng, extent=metres(600.0), color=rgb("#2A2F36")):
    size = min(GROUND_TEXTURE_MAX, max(GROUND_TEXTURE_MIN, int(extent * GROUND_TEXELS_PER_HEAD)))
    grain = cv2.resize(rng.random((48, 48)).astype(np.float32), (size, size), interpolation=cv2.INTER_CUBIC)
    return np.clip(color * (0.85 + 0.3 * grain[..., None]), 0, 1).astype(np.float32)


ROAD_DASH = (metres(3.0), metres(6.0))      # length of a centre-line dash and of the gap after it
ROAD_LINE = metres(0.15)
ROAD_KERB = metres(0.25)


def road_texture(rng, light, extent=metres(600.0), road_width=metres(14.0), asphalt=rgb("#23282F"),
                 marking=rgb("#8C8E88"), kerb=rgb("#5A6068"), along="z"):
    """Snow-covered ground with a road through the middle of the plane, running along z or x: dark
    asphalt, a dashed centre line and kerbs."""
    if along == "x":
        return np.ascontiguousarray(np.rot90(road_texture(rng, light, extent, road_width, asphalt, marking, kerb)))
    image = snow_texture(rng, light, extent)
    size = image.shape[0]
    scale = size / extent
    half = int(road_width / 2 * scale)
    middle = size // 2
    grain = cv2.resize(rng.random((64, 8)).astype(np.float32), (2 * half, size), interpolation=cv2.INTER_CUBIC)
    image[:, middle - half:middle + half] = asphalt * (0.85 + 0.3 * grain[..., None])
    kerb_px = max(1, int(ROAD_KERB * scale))
    image[:, middle - half - kerb_px:middle - half] = kerb
    image[:, middle + half:middle + half + kerb_px] = kerb
    line = max(1, int(ROAD_LINE * scale))
    dash, gap = (int(length * scale) for length in ROAD_DASH)
    for y in range(0, size, max(1, dash + gap)):
        image[y:y + dash, middle - line // 2:middle + line // 2 + 1] = marking
    return np.clip(image, 0.0, 1.0).astype(np.float32)


REFLECTION_STRENGTH = 0.55


def wet_reflections(canvas, camera, lamps, width=metres(0.6), strength=REFLECTION_STRENGTH):
    """Lights mirrored in a wet road: a soft vertical streak from under each lamp down toward its
    mirror image below the ground, brightest near the ground."""
    layer = np.zeros((canvas.height, canvas.width, 3), dtype=np.float32)
    for lamp in lamps:
        bulb = np.asarray(lamp.at, dtype=np.float64)
        foot = bulb * np.array([1.0, 0.0, 1.0])
        mirror = bulb * np.array([1.0, -1.0, 1.0])
        (fx, fy), (mx, my) = camera.project(np.stack([foot, mirror]))[0]
        if my <= fy:
            continue
        _, depth = camera.project(foot[None])
        grow = 1.0 if camera.distance is None else camera.distance / max(camera.distance - float(depth[0]), 1e-3)
        half = max(1, int(canvas.px(width * camera.scale * grow) / 2))
        streak = np.zeros((canvas.height, canvas.width), dtype=np.float32)
        top, bottom = int(canvas.px(fy)), int(canvas.px(my))
        for row in range(max(0, top), min(canvas.height, bottom)):
            fade = 1.0 - (row - top) / max(1, bottom - top)
            center = int(canvas.px(fx + (mx - fx) * (row - top) / max(1, bottom - top)))
            streak[row, max(0, center - half):max(0, center + half)] = fade ** 1.5
        streak = shading.blur(streak, half * 0.8)
        layer += streak[..., None] * np.asarray(lamp.color) * lamp.strength
    canvas.rgb = (1 - (1 - canvas.rgb) * (1 - np.clip(layer * strength, 0, 1))).astype(np.float32)


GROUND_DETAIL = 0.45               # painterly brush detail on the ground: paths, kerbs and reflections keep their shape


def draw_ground(canvas, camera, plane):
    keep_detail(canvas, draw_surface(canvas, camera, plane), GROUND_DETAIL)


def sky(canvas, stops, clouds=0.0, horizon=None):
    """Sky gradient (stops: (share, colour) from the top, 1.0 at the horizon) and, with clouds > 0, a soft
    overcast layer of that strength. horizon: canvas y of the horizon (horizon_y); None is the bottom edge."""
    _, ys = canvas.grid()
    reach = canvas.units_height if horizon is None else max(float(horizon), 1.0)
    share = np.clip(ys / reach, 0.0, 1.0)
    positions = [position for position, _ in stops]
    canvas.rgb = np.stack([np.interp(share, positions, [color[channel] for _, color in stops]) for channel in range(3)],
                          axis=2).astype(np.float32)
    if clouds > 0:
        layer = canvas.noise(CLOUD_CELL, octaves=3)
        canvas.rgb = (canvas.rgb * (1 - clouds * (layer[..., None] - 0.5))).astype(np.float32)


# ---- light ------------------------------------------------------------------------------------------------------
GROUND_GLOW = 0.8                  # share of a lamp's light the ground sends back (snow and wet asphalt are bright)


def light_ground(canvas, camera, lamps):
    """Lit patches on the ground round the lamps, with the same falloff as night_lighting, so a lamp
    lights the snow under it and the figure beside it alike. Call it right after draw_ground."""
    light_plane(canvas, camera, lamps, GROUND_POINT, GROUND_NORMAL)


def light_plane(canvas, camera, lamps, point, normal, ambient=None, mask=None):
    """Lamp light on whatever was painted on a plane (through point, facing normal): the ground, or a
    wall of a room at night. ambient None adds the light over the painted colours (ground already
    painted in night colours); an ambient multiplies the painted colours by ambient plus the lamps, as
    night_lighting does for figures and objects. Pixels whose line of sight misses the plane are left, and
    with mask (what interior.draw_surface returns) so are the pixels the surface does not cover."""
    points, on_plane = plane_points(canvas, camera, point, normal)
    if mask is not None:
        covered = mask[on_plane] > 0.5
        points, on_plane = points[covered], on_plane & (mask > 0.5)
    if not on_plane.any():
        return
    light = np.zeros((int(on_plane.sum()), 3))
    for lamp in lamps:
        light += _nearness(points, lamp)[:, None] * lamp.strength * np.asarray(lamp.color)
    if ambient is None:
        glow = np.clip(light * GROUND_GLOW, 0.0, 1.0)
        canvas.rgb[on_plane] = 1 - (1 - canvas.rgb[on_plane]) * (1 - glow)
    else:
        canvas.rgb[on_plane] = np.clip(canvas.rgb[on_plane] * (np.asarray(ambient) + light), 0.0, 1.0)


def night_lighting(camera, ambient, lamps=()):
    """Lighting for scene3d.draw_scene3d(lighting=...): figures and objects keep ambient of their
    colour, and each lamp adds its colour by distance (falling to half at its reach)."""
    def light(canvas, image):
        drawn = image.depth > EMPTY / 2
        if not drawn.any():
            return
        points = world_points(canvas, camera, image.depth, drawn)
        gain = np.tile(np.asarray(ambient, dtype=np.float64), (len(points), 1))
        for lamp in lamps:
            gain += _nearness(points, lamp)[:, None] * lamp.strength * np.asarray(lamp.color)
        cover = image.coverage[drawn][:, None]
        canvas.rgb[drawn] = np.clip(canvas.rgb[drawn] * (1 - cover + cover * gain), 0.0, 1.0)
    return light


VIEW_DETAIL = 0.7                  # painterly brush detail on window views: lit windows and the moon keep their shape


def draw_lit_room(painter, camera, surfaces, views, items, lamps, ambient, view_detail=VIEW_DETAIL):
    """A room lit by its own lamps (a desk lamp, a screen, the sun through a window), the way a night street
    is lit: each surface is painted then lit like the items (its colour times ambient plus the lamps;
    surfaces without a facing, such as a sun patch, are left as painted), the window views go on after
    that so what is outside keeps its own light, then the items share one depth buffer under the same lamps.
    surfaces: interior.Surface list back to front (interior.shell_surfaces, on_back_wall, ...).
    views: the window surfaces (interior.window textures) and sun patches drawn over the lit walls.
    Returns what scene3d.draw_scene3d returns."""
    canvas = painter.canvas
    for surface in surfaces:
        covered = draw_surface(canvas, camera, surface)
        if covered is not None and surface.facing is not None:
            light_plane(canvas, camera, lamps, surface.corners[0], surface.facing, ambient=ambient, mask=covered)
    for surface in views:
        keep_detail(canvas, draw_surface(canvas, camera, surface), view_detail)
    return scene3d.draw_scene3d(painter, camera, items, lighting=night_lighting(camera, ambient, lamps))


CONE_SOFTNESS = 0.12               # radians over which a shaded lamp's light fades out at the cone edge


def _nearness(points, lamp):
    """1 at the bulb, one half at its reach, falling with the square of the distance beyond; a shaded
    lamp lights only the cone below it, which makes the round pool under a street lamp."""
    offset = points - np.asarray(lamp.at)
    squared = np.sum(offset ** 2, axis=1)
    nearness = 1.0 / (1.0 + squared / lamp.reach ** 2)
    if lamp.cone is None:
        return nearness
    angle = np.arccos(np.clip(offset[:, 1] / np.sqrt(squared + 1e-9), -1.0, 1.0))      # 0 straight down (y is down)
    return nearness * (1.0 - shading.smoothstep(lamp.cone - CONE_SOFTNESS, lamp.cone + CONE_SOFTNESS, angle))


def world_points(canvas, camera, depth, where):
    """World positions of the drawn pixels where is True (the inverse of camera.project)."""
    rows, cols = np.nonzero(where)
    z = depth[rows, cols].astype(np.float64)
    grow = np.ones_like(z) if camera.distance is None else camera.distance / np.maximum(camera.distance - z, 1e-3)
    view = np.column_stack([_picture_plane(canvas, camera, rows, cols) / grow[:, None], z])
    return np.asarray(camera.target, dtype=np.float64) + view @ camera.matrix()


GROUND_POINT, GROUND_NORMAL = (0.0, 0.0, 0.0), (0.0, -1.0, 0.0)


def ground_points(canvas, camera):
    """World points where each pixel's line of sight meets the ground (y = 0), and the mask of the
    pixels that meet it in front of the eye (below the horizon)."""
    return plane_points(canvas, camera, GROUND_POINT, GROUND_NORMAL)


def plane_points(canvas, camera, point, normal):
    """World points where each pixel's line of sight meets the plane through point with normal, and the
    mask of the pixels whose line of sight meets it in front of the eye."""
    rows, cols = np.mgrid[0:canvas.height, 0:canvas.width]
    rows, cols = rows.ravel(), cols.ravel()
    plane = np.column_stack([_picture_plane(canvas, camera, rows, cols), np.zeros(len(rows))])
    through = np.asarray(camera.target, dtype=np.float64) + plane @ camera.matrix()
    eye = camera.eye()
    if eye is None:                        # orthographic: every line of sight is parallel to the view axis
        eye_offset = camera.matrix().T @ np.array([0.0, 0.0, 1.0])
        starts, ways = through, -np.broadcast_to(eye_offset, through.shape)
    else:
        starts, ways = np.broadcast_to(eye, through.shape), through - eye
    normal = np.asarray(normal, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        reach = ((np.asarray(point, dtype=np.float64) - starts) @ normal) / (ways @ normal)
    hits = np.isfinite(reach) & (reach > 0)
    mask = hits.reshape(canvas.height, canvas.width)
    return (starts + ways * np.where(hits, reach, 0.0)[:, None])[hits], mask


def _picture_plane(canvas, camera, rows, cols):
    """View x, y (head heights) of pixel centres on the picture plane through the camera target."""
    xy = (np.stack([cols, rows], axis=1) + 0.5) / canvas.px_per_unit
    return (xy - np.asarray(camera.origin)) / camera.scale


# ---- wires ------------------------------------------------------------------------------------------------------
WIRE_SAMPLES = 40
WIRE_DETAIL = 0.85                 # painterly brush detail along wires: they stay thin lines


def catenary(a, b, sag):
    """Points of a wire hung from world point a to b, sagging by sag head heights at its middle."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    t = np.linspace(0.0, 1.0, WIRE_SAMPLES)[:, None]
    return a * (1 - t) + b * t + np.array([0.0, 1.0, 0.0]) * (4.0 * sag * t * (1 - t))


def draw_wires(canvas, camera, image, wires, width=1.4, color=rgb("#14181E"), tolerance=0.05):
    """Thin wires as lines of constant width (a solid this thin would break up into dots). Each wire is
    a list of world points; a stretch hidden behind a drawn object is left out."""
    mask = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for points in wires:
        xy, depth = camera.project(np.asarray(points, dtype=np.float64))
        px = xy * canvas.px_per_unit
        rows = np.clip(px[:, 1].astype(int), 0, canvas.height - 1)
        cols = np.clip(px[:, 0].astype(int), 0, canvas.width - 1)
        behind = depth[...] < image.depth[rows, cols] - tolerance
        visible = ~behind
        start = None
        for index in range(len(px) + 1):
            if index < len(px) and visible[index]:
                start = index if start is None else start
                continue
            if start is not None and index - start > 1:
                run = np.round(px[start:index] * 16).astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(mask, [run], False, 1.0, max(1, int(round(canvas.px(width)))), cv2.LINE_AA, shift=4)
            start = None
    canvas.blend(mask, color, 0.9)
    keep_detail(canvas, np.clip(shading.blur(mask, canvas.px(2.0)) * 4.0, 0.0, 1.0), WIRE_DETAIL)


# ---- weather ----------------------------------------------------------------------------------------------------
HORIZON_REACH = 1e4                  # head heights: far enough that a point there sits on the horizon line


def horizon_y(camera):
    """Canvas y of the horizon: a point far ahead along the level ground, in the direction the camera looks."""
    ahead = -(camera.matrix().T @ np.array([0.0, 0.0, 1.0]))
    ahead[1] = 0.0
    ahead /= np.linalg.norm(ahead) + 1e-9
    far = np.asarray(camera.target, dtype=np.float64) + ahead * HORIZON_REACH
    return float(camera.project(far[None])[0][0, 1])


def atmosphere(canvas, camera, image, fog):
    """Haze: the sky and painted surfaces fade toward the fog colour near the horizon, 3D items by their
    distance from the eye."""
    hy = horizon_y(camera)
    _, ys = canvas.grid()
    band = np.exp(-((ys - hy) / fog.horizon_band) ** 2) * fog.horizon_strength
    empty = image.depth <= EMPTY / 2
    distance = (camera.distance if camera.distance is not None else 0.0) - image.depth
    item_fog = 1.0 - np.exp(-np.clip(distance, 0.0, None) / fog.distance)
    amount = np.where(empty, band, item_fog * 0.85)
    canvas.rgb = (canvas.rgb * (1 - amount[..., None]) + fog.color * amount[..., None]).astype(np.float32)


def snowfall(canvas, rng, snow, color=rgb("#E8EEF4")):
    """Falling flakes over the whole picture: many small far flakes, a few large soft near ones."""
    area = (canvas.width / canvas.px_per_unit) * (canvas.height / canvas.px_per_unit)
    count = int(snow.count * area / 1e6)
    xs = rng.uniform(0, canvas.width, count)
    ys = rng.uniform(0, canvas.height, count)
    nearness = rng.random(count) ** 3                      # most flakes are far and small
    radii = canvas.px(snow.size[0]) + nearness * canvas.px(snow.size[1] - snow.size[0])
    sharp = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    soft = np.zeros_like(sharp)
    for x, y, r, near in zip(xs, ys, radii, nearness):
        target = soft if near > 0.5 else sharp
        axes = (max(1, int(r)), max(1, int(r * (1 + snow.streak * near))))
        cv2.ellipse(target, (int(x), int(y)), axes, 0, 0, 360, float(0.6 + 0.4 * (1 - near)), -1, cv2.LINE_AA)
    flakes = np.maximum(shading.blur(sharp, 0.6), shading.blur(soft, canvas.px(snow.size[1]) * 0.35))
    canvas.blend(np.clip(flakes, 0, 1), color, snow.opacity)


# ---- the whole outdoor picture ----------------------------------------------------------------------------------
@dataclass
class World:
    """Everything an outdoor picture holds, drawn by draw_world in the right order."""
    light: Light
    sky: tuple                       # sky stops, e.g. NIGHT_SKY
    fog: Fog
    ground: Surface                  # ground_plane(snow_texture(...)) or ground_plane(road_texture(...))
    blocks: list = ()
    lamps: list = ()                 # Lamp: light the ground and the items
    items: list = ()                 # scene3d.Placed figures, street furniture and objects
    wires: list = ()                 # world point lists (street3d.wires_between, catenary)
    snow: Snow = None
    clouds: float = 0.0              # strength of the overcast cloud layer on the sky
    wet: bool = False                # lamps mirrored in a wet road


def draw_world(painter, camera, world, rng):
    """Sky, ground and its lamp light, buildings, then the 3D items lit by the lamps, wires over them,
    haze and falling snow. Returns what scene3d.draw_scene3d returns."""
    canvas = painter.canvas
    sky(canvas, world.sky, world.clouds, horizon_y(camera))
    draw_ground(canvas, camera, world.ground)
    light_ground(canvas, camera, world.lamps)
    if world.wet:
        wet_reflections(canvas, camera, world.lamps)
    draw_blocks(canvas, camera, world.blocks, world.fog)
    lighting = night_lighting(camera, world.light.ambient, world.lamps)
    result = scene3d.draw_scene3d(painter, camera, list(world.items), lighting=lighting)
    image = result[1]
    draw_wires(canvas, camera, image, world.wires)
    atmosphere(canvas, camera, image, world.fog)
    if world.snow is not None:
        # Falling snow is in front of everything: drawn over the finished style, so brushwork keeps the
        # flakes small and sharp.
        flakes = np.random.default_rng(rng.integers(1 << 31))
        canvas.overlays.append(lambda finished: snowfall(finished, flakes, world.snow))
    return result

