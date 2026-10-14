#!/usr/bin/env python3
"""Cityscape: a street after rain at dusk, in one-point perspective.

    python city_dusk.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
import cv2
import numpy as np

from codeillust import background, city, studio
from codeillust.config import rgb

SCENE_NAME = "city_dusk"
CAMERA = city.StreetCamera(vanishing_point=(500.0, 800.0), focal=780.0, eye_height=1.6)
STREET_HALF_WIDTH = 9.0            # metres from the centre line to the building line
SIDEWALK = 3.0
HAZE = rgb("#E79A86")              # dusk haze that swallows the far end of the street
SKY_STOPS = [(0.0, rgb("#16224F")), (0.30, rgb("#4B3F86")), (0.50, rgb("#C4688C")), (0.60, rgb("#FFA66E")),
             (1.0, rgb("#FFA66E"))]
CLOUDS = [((330.0, 300.0), 420.0, 130.0, 34), ((760.0, 170.0), 360.0, 100.0, 26)]
CLOUD_COLORS = (rgb("#FFC9A8"), rgb("#B978A8"), rgb("#6A4E92"))
SUN_GLOW = (CAMERA.vanishing_point, 430.0, (1.0, 0.82, 0.55), 0.75)
WALLS = (rgb("#5B4A6B"), rgb("#6E5560"), rgb("#465478"), rgb("#75656E"), rgb("#3E4A66"), rgb("#62506E"))
SHOPS = (rgb("#FFD9A0"), rgb("#8FEADC"), rgb("#FF9FBA"), None, rgb("#FFE8C0"))
# (depth along the street, height) for each side, near to far, in metres.
LEFT_ROW = [(13.0, 22.0), (10.0, 14.0), (16.0, 31.0), (12.0, 18.0), (18.0, 26.0), (14.0, 15.0), (24.0, 34.0),
            (30.0, 22.0), (40.0, 28.0), (60.0, 20.0)]
RIGHT_ROW = [(11.0, 16.0), (15.0, 27.0), (9.0, 12.0), (17.0, 22.0), (13.0, 33.0), (20.0, 17.0), (22.0, 25.0),
             (34.0, 30.0), (44.0, 19.0), (60.0, 24.0)]
FIRST_BUILDING = 3.0
LAMPS = [(side * 6.4, z) for z in (12.0, 26.0, 42.0, 62.0, 90.0) for side in (-1, 1)]
SIGNS = [(-8.8, 9.0, 4.2, 8.6, 1.1, rgb("#FF5C8A")), (7.6, 14.0, 4.6, 9.4, 1.2, rgb("#5CE1E6")),
         (-8.7, 21.0, 5.0, 8.0, 1.0, rgb("#FFD45C")), (7.8, 30.0, 4.4, 9.0, 1.0, rgb("#FF8A5C")),
         (-8.7, 37.0, 4.5, 9.5, 1.0, rgb("#9B8CFF"))]
WINDOW_GLOW = rgb("#FFC98A")


def _row(side, plan):
    buildings, near = [], FIRST_BUILDING
    for index, (depth, height) in enumerate(plan):
        buildings.append(city.Building(side=side, near=near, depth=depth, height=height,
                                       wall=WALLS[(index * 2 + (side > 0)) % len(WALLS)],
                                       lit_share=0.5, shop=SHOPS[(index + (side > 0)) % len(SHOPS)]))
        near += depth
    return buildings


def compose(painter):
    canvas = painter.canvas
    background.gradient_stops(canvas, SKY_STOPS)
    background.stars(canvas, 90, 420.0)
    background.cumulus_clouds(canvas, CLOUDS, painter.light, CLOUD_COLORS)
    background.sun_glow(canvas, *SUN_GLOW)
    city.skyline(canvas, CAMERA, canvas.rng, 520.0, 16, HAZE)

    # What the wet road will show: the sky and the walls hinged down about the ground.
    horizon_px = int(canvas.px(CAMERA.vanishing_point[1]))
    mirror = np.zeros_like(canvas.rgb)
    below = canvas.height - horizon_px
    mirror[horizon_px:] = cv2.flip(canvas.rgb[max(0, horizon_px - below):horizon_px], 0)[:below]

    buildings = _row(-1, LEFT_ROW) + _row(1, RIGHT_ROW)
    ground, road = city.draw_road(canvas, CAMERA, STREET_HALF_WIDTH, SIDEWALK)
    glow = city.draw_buildings(canvas, CAMERA, buildings, STREET_HALF_WIDTH, HAZE)
    glow = np.maximum(glow, city.draw_signs(canvas, CAMERA, SIGNS))
    city.draw_buildings(canvas, CAMERA, buildings, STREET_HALF_WIDTH, HAZE, layer=mirror, mirrored=True)
    city.draw_signs(canvas, CAMERA, SIGNS, layer=mirror, mirrored=True)
    city.wet_reflection(canvas, mirror, ground)
    city.draw_lamps(canvas, CAMERA, LAMPS)
    city.bloom(canvas, glow, WINDOW_GLOW)
    canvas.importance = np.full((canvas.height, canvas.width), 0.5, dtype=np.float32)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, description=__doc__)
