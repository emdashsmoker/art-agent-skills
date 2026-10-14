"""Landscape terrain: a fractal height map seen through a pinhole camera.

The projection is the classic 'voxel space' method: walk away from the
camera in depth slices, and for every screen column draw the terrain of that
slice if it rises above everything drawn so far. Real geometry gives correct
overlap of ridges, distance haze and a horizon for free.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from . import shading
from .config import rgb

MAP_SIZE = 1024                 # world units and height-map cells per side
SLICE_GROWTH = 0.0035           # depth step grows with distance (far terrain needs fewer slices)
MIN_SLICE = 0.45
SHADOW_STEPS = 48
SHADOW_REACH = 260.0            # world units a peak can throw its shadow
SNOW_SLOPE_LIMIT = 1.9
ROCK_SLOPE = 1.45


@dataclass(frozen=True)
class Camera:
    position: tuple = (512.0, -60.0)   # world x, world y (depth axis)
    eye_height: float = 48.0           # world units above height zero
    horizon: float = 560.0             # canvas units from the top
    focal: float = 1100.0              # canvas units; larger = narrower view
    far: float = 1080.0


@dataclass(frozen=True)
class TerrainPalette:
    snow: tuple = (rgb("#FFFFFF"), rgb("#B4C8EC"))       # lit, shadow
    rock: tuple = (rgb("#C6C0BC"), rgb("#5A6A9C"))
    meadow: tuple = (rgb("#86C45C"), rgb("#3C7C52"))
    forest: tuple = (rgb("#3F8F4E"), rgb("#1C5142"))
    water: np.ndarray = None
    haze: np.ndarray = None

    def resolved(self):
        water = self.water if self.water is not None else rgb("#2F86BE")
        haze = self.haze if self.haze is not None else rgb("#CFEAF7")
        return water, haze


def value_noise(rng, size, cell, octaves):
    total = np.zeros((size, size), dtype=np.float32)
    weight_sum = 0.0
    for octave in range(octaves):
        cells = max(2, int(size / (cell / 2**octave)) + 2)
        coarse = rng.random((cells, cells)).astype(np.float32)
        weight = 0.5**octave
        total += cv2.resize(coarse, (size, size), interpolation=cv2.INTER_CUBIC) * weight
        weight_sum += weight
    return np.clip(total / weight_sum, 0.0, 1.0)


def alpine_lake_heightmap(rng, peak_height=330.0, sea_level=20.0):
    """Mountains far away and at the sides, a lake basin in the middle, a low bank at the camera."""
    ys, xs = np.mgrid[0:MAP_SIZE, 0:MAP_SIZE].astype(np.float32)
    ridged = 1.0 - np.abs(2.0 * value_noise(rng, MAP_SIZE, 300.0, 7) - 1.0)
    ridged = ridged**1.6
    broad = value_noise(rng, MAP_SIZE, 520.0, 3)
    far_range = shading.smoothstep(520.0, 860.0, ys)
    side = np.abs(xs - MAP_SIZE / 2) / (MAP_SIZE / 2)
    side_range = shading.smoothstep(0.50, 1.0, side) * shading.smoothstep(220.0, 520.0, ys) * 0.55
    envelope = np.maximum(far_range, side_range)
    height = envelope * (0.18 + 0.82 * ridged) * (0.55 + 0.9 * broad)
    height = height / height.max() * peak_height        # the tallest summit is exactly peak_height
    height += value_noise(rng, MAP_SIZE, 90.0, 4) * 22.0 * envelope
    near_bank = (1.0 - shading.smoothstep(40.0, 130.0, ys)) * (sea_level + 5.0 + 16.0 * value_noise(rng, MAP_SIZE, 120.0, 3))
    return np.maximum(height, near_bank).astype(np.float32), sea_level


def colorize(heightmap, sea_level, rng, light, palette=TerrainPalette(), peak_height=330.0):
    """Per-cell colour of the terrain: material by altitude and slope, then sunlight and shadow."""
    water_color, _ = palette.resolved()
    ground = np.maximum(heightmap, sea_level)
    smooth = shading.blur(ground, 1.2)
    slope_x = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    slope_y = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    steepness = np.sqrt(slope_x**2 + slope_y**2)
    normal_length = np.sqrt(steepness**2 + 1.0)
    lambert = np.clip((-slope_x * light[0] - slope_y * light[1] + light[2]) / normal_length, 0.0, 1.0)
    blocked = _terrain_shadow(ground, light)
    lit = shading.smoothstep(0.18, 0.62, lambert) * (1.0 - blocked)

    altitude = ground / peak_height
    patch = value_noise(rng, MAP_SIZE, 60.0, 4)
    snow = shading.smoothstep(0.52, 0.66, altitude + (patch - 0.5) * 0.24) * (steepness < SNOW_SLOPE_LIMIT)
    rock = np.maximum(shading.smoothstep(ROCK_SLOPE * 0.75, ROCK_SLOPE, steepness),
                      shading.smoothstep(0.44, 0.58, altitude))
    forest = shading.smoothstep(0.62, 0.40, patch) * shading.smoothstep(0.40, 0.26, altitude)

    def tone(pair):
        return pair[1] + (pair[0] - pair[1]) * lit[..., None]

    color = tone(palette.meadow)
    color = color * (1 - forest[..., None]) + tone(palette.forest) * forest[..., None]
    color = color * (1 - rock[..., None]) + tone(palette.rock) * rock[..., None]
    color = color * (1 - snow[..., None]) + tone(palette.snow) * snow[..., None]
    water = heightmap < sea_level
    color[water] = water_color
    return color.astype(np.float32), ground, water.astype(np.float32)


def _terrain_shadow(ground, light):
    planar = np.asarray(light[:2], dtype=np.float32)
    planar_length = float(np.linalg.norm(planar)) + 1e-9
    direction = planar / planar_length
    rise = float(light[2]) / planar_length
    blocked = np.zeros_like(ground)
    size = (ground.shape[1], ground.shape[0])
    for step in range(1, SHADOW_STEPS + 1):
        distance = SHADOW_REACH * step / SHADOW_STEPS
        shift = np.float32([[1, 0, -direction[0] * distance], [0, 1, -direction[1] * distance]])
        toward_light = cv2.warpAffine(ground, shift, size, borderMode=cv2.BORDER_REPLICATE)
        blocked = np.maximum(blocked, np.clip((toward_light - ground - distance * rise) / 3.0, 0.0, 1.0))
    return blocked


def render(canvas, ground, color, water, camera=Camera(), haze=None, haze_distance=1700.0):
    """Project the terrain onto the canvas (over whatever sky is already there).

    Returns (terrain_mask, water_mask, depth) as canvas-sized images.
    """
    haze = rgb("#CFEAF7") if haze is None else haze
    width, height = canvas.width, canvas.height
    scale = canvas.px_per_unit
    focal, horizon = camera.focal * scale, camera.horizon * scale
    columns = (np.arange(width, dtype=np.float32) + 0.5 - width / 2) / focal
    rows = np.arange(height, dtype=np.float32)[:, None]
    lowest = np.full(width, float(height), dtype=np.float32)   # first row not yet covered, per column
    terrain_mask = np.zeros((height, width), dtype=np.float32)
    water_mask = np.zeros((height, width), dtype=np.float32)
    depth_image = np.zeros((height, width), dtype=np.float32)
    image = canvas.rgb

    depth = 3.0
    while depth < camera.far:
        map_x = (camera.position[0] + columns * depth)[None, :].astype(np.float32)
        map_y = np.full_like(map_x, camera.position[1] + depth)
        surface = cv2.remap(ground, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)[0]
        slice_color = cv2.remap(color, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)[0]
        slice_water = cv2.remap(water, map_x, map_y, cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)[0]
        screen_y = horizon + (camera.eye_height - surface) * focal / depth
        fog = 1.0 - np.exp(-depth / haze_distance)
        slice_color = slice_color * (1 - fog) + haze * fog

        visible = screen_y < lowest
        if visible.any():
            top = int(max(0, np.floor(screen_y[visible].min())))
            bottom = int(min(height, np.ceil(lowest[visible].max())))
            band = rows[top:bottom]
            fill = (band >= screen_y[None, :]) & (band < lowest[None, :])
            image[top:bottom][fill] = np.broadcast_to(slice_color[None], fill.shape + (3,))[fill]
            terrain_mask[top:bottom][fill] = 1.0
            water_mask[top:bottom][fill] = np.broadcast_to(slice_water[None], fill.shape)[fill]
            depth_image[top:bottom][fill] = depth
            lowest = np.minimum(lowest, screen_y)
        depth += max(MIN_SLICE, depth * SLICE_GROWTH)
    return terrain_mask, water_mask, depth_image
