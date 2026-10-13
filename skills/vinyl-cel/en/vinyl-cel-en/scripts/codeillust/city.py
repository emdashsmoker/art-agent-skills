"""City street in one-point perspective.

World space is metric: x across the street, y up, z away from the camera.
Every flat thing (facade, road marking, puddle reflection) is drawn flat as
a texture or polygon and then projected, so perspective is exact by
construction instead of being eyeballed.
"""
from dataclasses import dataclass, replace

import cv2
import numpy as np

from . import shading
from .config import rgb

TEXELS_PER_METER = (10.0, 44.0)     # facade texture density: far buildings, near buildings
FLOOR_HEIGHT = 3.3                  # metres
BAY_WIDTH = 2.6
WINDOW_SHARE = (0.56, 0.58)         # window width and height as a share of bay and floor
SHOP_HEIGHT = 3.6
NEAR_CLIP = 2.5                     # metres; nothing nearer is drawn
FOG_DISTANCE = 190.0
WINDOW_LIGHTS = (rgb("#FFD98A"), rgb("#FFC06A"), rgb("#FFF0C8"), rgb("#FFB3A0"), rgb("#BFE4FF"))
WINDOW_DARK = rgb("#2A3350")
REFLECTION_STRENGTH = 0.55
REFLECTION_SMEAR_UNITS = 26.0
END_WALL_WIDTH = 16.0               # metres of camera-facing wall drawn beside each building
END_WALL_SHADE = 0.86
LAMP_GLOW_UNITS = 3.2               # glow radius in metres at the lamp's depth


@dataclass(frozen=True)
class StreetCamera:
    vanishing_point: tuple = (500.0, 690.0)   # canvas units
    focal: float = 780.0                      # canvas units
    eye_height: float = 1.6                   # metres

    def project(self, points_xyz):
        p = np.atleast_2d(np.asarray(points_xyz, dtype=np.float64))
        depth = np.maximum(p[:, 2], 1e-3)
        x = self.vanishing_point[0] + self.focal * p[:, 0] / depth
        y = self.vanishing_point[1] - self.focal * (p[:, 1] - self.eye_height) / depth
        return np.stack([x, y], axis=1)


@dataclass(frozen=True)
class Building:
    side: int               # -1 left of the street, +1 right
    near: float             # metres from the camera to the near corner
    depth: float            # length along the street
    height: float
    wall: np.ndarray
    lit_share: float = 0.45
    shop: np.ndarray = None  # colour of the lit shopfront, None for a plain ground floor


def facade_texture(rng, building, haze):
    """Flat elevation of a building side: u runs along the street (near to far), v from roof to ground."""
    far_weight = np.clip((building.near - 8.0) / 60.0, 0.0, 1.0)
    density = TEXELS_PER_METER[1] * (1 - far_weight) + TEXELS_PER_METER[0] * far_weight
    width = max(8, int(building.depth * density))
    height = max(8, int(building.height * density))
    texture = np.empty((height, width, 3), dtype=np.float32)
    grime = np.linspace(1.08, 0.90, height, dtype=np.float32)[:, None, None]
    texture[:] = building.wall * grime
    glow = np.zeros((height, width), dtype=np.float32)

    floors = max(1, int((building.height - SHOP_HEIGHT) / FLOOR_HEIGHT))
    bays = max(1, int(building.depth / BAY_WIDTH))
    bay_px = width / bays
    floor_px = (height - SHOP_HEIGHT * density) / floors
    for floor in range(floors):
        top = int(floor * floor_px + floor_px * (1 - WINDOW_SHARE[1]) / 2)
        bottom = int(top + floor_px * WINDOW_SHARE[1])
        ledge = int((floor + 1) * floor_px)
        texture[max(0, ledge - max(1, int(density * 0.12))):ledge] *= 0.82
        for bay in range(bays):
            left = int(bay * bay_px + bay_px * (1 - WINDOW_SHARE[0]) / 2)
            right = int(left + bay_px * WINDOW_SHARE[0])
            if rng.random() < building.lit_share:
                color = WINDOW_LIGHTS[rng.integers(len(WINDOW_LIGHTS))] * rng.uniform(0.75, 1.0)
                texture[top:bottom, left:right] = color
                glow[top:bottom, left:right] = 1.0
                blind = int((bottom - top) * rng.uniform(0.0, 0.5))
                texture[top:top + blind, left:right] *= 0.82
            else:
                texture[top:bottom, left:right] = WINDOW_DARK * rng.uniform(0.8, 1.25)
            mullion = max(1, int(density * 0.07))
            middle = (left + right) // 2
            texture[top:bottom, middle - mullion // 2:middle + mullion // 2 + 1] *= 0.55
    shop_top = int(height - SHOP_HEIGHT * density)
    if building.shop is not None:
        band = slice(shop_top + int(density * 0.7), height - int(density * 0.35))
        texture[band] = building.shop
        glow[band] = 1.0
        texture[shop_top:shop_top + int(density * 0.7)] = building.wall * 0.6
        for bay in range(bays + 1):                        # pillars between shop windows
            x = int(bay * bay_px)
            texture[shop_top:, max(0, x - int(density * 0.18)):x + int(density * 0.18)] = building.wall * 0.7
            glow[shop_top:, max(0, x - int(density * 0.18)):x + int(density * 0.18)] = 0.0

    along = np.linspace(building.near, building.near + building.depth, width, dtype=np.float32)
    fog = (1.0 - np.exp(-along / FOG_DISTANCE))[None, :, None]
    texture = texture * (1 - fog) + haze * fog
    return np.clip(texture, 0.0, 1.0), glow


def _warp(canvas, texture, corners_units):
    """Project a flat texture onto a quad (corner order: top-left, top-right, bottom-right, bottom-left).
    Returns (warped image, coverage)."""
    height, width = texture.shape[:2]
    source = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    target = (np.asarray(corners_units) * canvas.px_per_unit).astype(np.float32)
    matrix = cv2.getPerspectiveTransform(source, target)
    size = (canvas.width, canvas.height)
    warped = cv2.warpPerspective(texture, matrix, size, flags=cv2.INTER_LINEAR)
    cover = cv2.warpPerspective(np.ones((height, width), dtype=np.float32), matrix, size, flags=cv2.INTER_LINEAR)
    return warped, cover


def draw_buildings(canvas, camera, buildings, street_half_width, haze, layer=None, mirrored=False):
    """Draw facades far to near into `layer` (default: the canvas).

    mirrored=True draws each wall hinged downward about its ground line, which
    is exactly what a wet road reflects. Returns the glow image (lit windows).
    """
    layer = canvas.rgb if layer is None else layer
    glow_total = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for building in sorted(buildings, key=lambda b: -b.near):
        # Each building has its own random stream so the mirrored pass repeats the same windows.
        rng = np.random.default_rng([int(building.near * 100), int(building.height * 100), building.side + 1])
        texture, glow = facade_texture(rng, building, haze)
        x = building.side * street_half_width
        near = max(building.near, NEAR_CLIP)
        far = building.near + building.depth
        if not mirrored and building.near > NEAR_CLIP:
            _draw_end_wall(canvas, camera, layer, rng, building, x, haze)
        roof = camera.project([(x, building.height, near), (x, building.height, far)])
        ground = camera.project([(x, 0.0, near), (x, 0.0, far)])
        if mirrored:
            roof = 2 * ground - roof
        corners = np.array([roof[0], roof[1], ground[1], ground[0]])
        warped, cover = _warp(canvas, texture, corners)
        layer[:] = layer * (1 - cover[..., None]) + warped * cover[..., None]
        warped_glow, _ = _warp(canvas, glow, corners)
        glow_total = glow_total * (1 - cover) + warped_glow
    return glow_total


def _draw_end_wall(canvas, camera, layer, rng, building, x, haze):
    """Wall that faces the camera. Without it a tall building behind a low one
    would look like a paper-thin blade; the nearer building later covers its lower part."""
    end = replace(building, depth=END_WALL_WIDTH, shop=None, lit_share=building.lit_share * 0.5,
                  wall=building.wall * END_WALL_SHADE)
    texture, _ = facade_texture(rng, end, haze)
    outer = x + building.side * END_WALL_WIDTH
    corners = camera.project([(x, building.height, building.near), (outer, building.height, building.near),
                              (outer, 0.0, building.near), (x, 0.0, building.near)])
    warped, cover = _warp(canvas, texture, corners)
    layer[:] = layer * (1 - cover[..., None]) + warped * cover[..., None]


def draw_signs(canvas, camera, signs, layer=None, mirrored=False):
    """Hanging signs that face the viewer. signs: [(x, z, y_bottom, y_top, width, colour), ...] in metres.
    Returns their glow image."""
    layer = canvas.rgb if layer is None else layer
    glow = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for x, z, y_bottom, y_top, width, color in sorted(signs, key=lambda item: -item[1]):
        corners = camera.project([(x, y_top, z), (x + width, y_top, z), (x + width, y_bottom, z), (x, y_bottom, z)])
        if mirrored:
            ground_y = camera.project([(x, 0.0, z)])[0][1]
            corners[:, 1] = 2 * ground_y - corners[:, 1]
        mask = canvas.mask(corners)
        layer[:] = layer * (1 - mask[..., None]) + np.asarray(color, dtype=np.float32) * mask[..., None]
        glow = np.maximum(glow, mask)
    return glow


def ground_polygon(camera, x_left, x_right, z_near, z_far):
    return camera.project([(x_left, 0.0, z_near), (x_right, 0.0, z_near), (x_right, 0.0, z_far),
                           (x_left, 0.0, z_far)])


def draw_road(canvas, camera, street_half_width, sidewalk, asphalt=rgb("#2B2C3F"), paving=rgb("#4A465C"),
              marking=rgb("#D9D2C0"), far=400.0):
    """Asphalt, sidewalks, centre dashes and a zebra crossing. Returns the road mask."""
    road_half = street_half_width - sidewalk
    whole = canvas.mask(ground_polygon(camera, -street_half_width, street_half_width, NEAR_CLIP * 0.4, far))
    canvas.blend(whole, paving)
    road = canvas.mask(ground_polygon(camera, -road_half, road_half, NEAR_CLIP * 0.4, far))
    canvas.blend(road, asphalt)
    for side in (-1, 1):
        curb = ground_polygon(camera, side * road_half, side * (road_half + 0.25), NEAR_CLIP * 0.4, far)
        canvas.blend(canvas.mask(curb), paving * 1.35)
    dashes = [ground_polygon(camera, -0.09, 0.09, z, z + 3.0) for z in np.arange(14.0, 160.0, 7.0)]
    canvas.blend(canvas.mask(*dashes), marking, 0.85)
    stripes = [ground_polygon(camera, x, x + 0.55, 6.0, 10.0) for x in np.arange(-road_half + 0.3, road_half - 0.5, 1.1)]
    canvas.blend(canvas.mask(*stripes), marking, 0.9)
    return whole, road


def draw_lamps(canvas, camera, positions, pole_height=6.5, color=rgb("#FFE2A8"), pole=rgb("#1C1D2B")):
    """Street lamps. positions: [(x, z), ...] in metres. Returns a glow image for the bloom pass."""
    glow = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for x, z in sorted(positions, key=lambda item: -item[1]):
        inward = -np.sign(x) * 1.2
        base, top, head = camera.project([(x, 0.0, z), (x, pole_height, z), (x + inward, pole_height, z)])
        width = camera.focal * 0.14 / z
        canvas.blend(canvas.mask([(base[0] - width / 2, base[1]), (base[0] + width / 2, base[1]),
                                  (top[0] + width / 3, top[1]), (top[0] - width / 3, top[1])]), pole)
        arm = [(top[0], top[1] - width / 3), (head[0], head[1] - width / 3), (head[0], head[1] + width / 3),
               (top[0], top[1] + width / 3)]
        canvas.blend(canvas.mask(arm), pole)
        radius = camera.focal * LAMP_GLOW_UNITS / z
        halo = canvas.soft_ellipse(head, radius, radius)
        core = canvas.soft_ellipse(head, radius * 0.16, radius * 0.16)
        glow = np.maximum(glow, np.maximum(halo * 0.55, core))
        pool_center = camera.project([(x + inward, 0.0, z)])[0]
        pool = canvas.soft_ellipse(pool_center, camera.focal * 5.0 / z, camera.focal * 5.0 / z * 0.22)
        canvas.rgb = (1 - (1 - canvas.rgb) * (1 - pool[..., None] * 0.30 * color)).astype(np.float32)
    canvas.rgb = (1 - (1 - canvas.rgb) * (1 - glow[..., None] * color)).astype(np.float32)
    return glow


def wet_reflection(canvas, mirror_layer, road_mask, strength=REFLECTION_STRENGTH):
    """Lay the mirrored scene onto the road, smeared downward like light on wet asphalt."""
    smear = max(3, int(canvas.px(REFLECTION_SMEAR_UNITS))) | 1
    smeared = cv2.blur(mirror_layer, (max(1, smear // 8) | 1, smear))
    ripple = 0.75 + 0.5 * canvas.noise(70.0, octaves=3)
    canvas.rgb = (1 - (1 - canvas.rgb) * (1 - smeared * (road_mask * ripple * strength)[..., None])).astype(np.float32)


def bloom(canvas, glow, color, radius_units=9.0, strength=0.6):
    """Halo around emitters (windows, signs)."""
    halo = shading.blur(glow, canvas.px(radius_units))[..., None] * strength
    canvas.rgb = (1 - (1 - canvas.rgb) * (1 - halo * np.asarray(color, dtype=np.float32))).astype(np.float32)


def skyline(canvas, camera, rng, depth, count, haze, base_height=(40.0, 130.0), color=rgb("#3A3558"),
            spread=120.0):
    """Distant towers facing the camera, seen over the end of the street."""
    fog = 1.0 - np.exp(-depth / (FOG_DISTANCE * 2.2))
    tone = color * (1 - fog) + haze * fog
    for _ in range(count):
        x = rng.uniform(-spread, spread)
        width = rng.uniform(14.0, 34.0)
        height = rng.uniform(*base_height)
        corners = camera.project([(x, height, depth), (x + width, height, depth), (x + width, 0.0, depth),
                                  (x, 0.0, depth)])
        canvas.blend(canvas.mask(corners), tone * rng.uniform(0.85, 1.1))
        rows, cols = int(height / 4.0), int(width / 3.5)
        lights = []
        for row in range(rows):
            for col in range(cols):
                if rng.random() < 0.22:
                    wx, wy = x + (col + 0.3) * width / cols, height - (row + 0.3) * height / rows
                    lights.append(camera.project([(wx, wy, depth), (wx + 1.6, wy, depth), (wx + 1.6, wy - 1.8, depth),
                                                  (wx, wy - 1.8, depth)]))
        if lights:
            canvas.blend(canvas.mask(*lights), WINDOW_LIGHTS[rng.integers(len(WINDOW_LIGHTS))], 0.8)
