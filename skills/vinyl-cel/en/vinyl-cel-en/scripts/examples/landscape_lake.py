#!/usr/bin/env python3
"""Landscape: an alpine lake under summer clouds.

    python landscape_lake.py --style all --preview --out out/
"""
import _toolkit  # noqa: F401  (sets the import path)
import numpy as np

from codeillust import background, scenery, studio, terrain

SCENE_NAME = "landscape_lake"
CANVAS_UNITS = (1333.0, 1000.0)            # landscape format
CAMERA = terrain.Camera(position=(512.0, -60.0), eye_height=85.0, horizon=540.0, focal=1150.0)
TERRAIN_LIGHT = (-0.55, -0.30, 0.78)       # map space: from the left, slightly from the camera side
CLOUDS = [((1020.0, 420.0), 620.0, 330.0, 70), ((260.0, 330.0), 420.0, 190.0, 40),
          ((620.0, 120.0), 260.0, 60.0, 14)]
BANK_TOP = 830.0                           # canvas y where the foreground grass begins
PINES = [((95.0, 1010.0), 620.0, 250.0), ((230.0, 1020.0), 430.0, 180.0), ((1240.0, 1015.0), 700.0, 280.0),
         ((1120.0, 1020.0), 380.0, 160.0)]
SKY_DETAIL = 0.0                           # painterly: broad strokes in the sky
LAND_DETAIL = 0.45                         # painterly: finer strokes on land and water


def compose(painter):
    canvas = painter.canvas
    background.summer_sky(canvas, CLOUDS, painter.light)
    heightmap, sea_level = terrain.alpine_lake_heightmap(canvas.rng)
    light = np.asarray(TERRAIN_LIGHT) / np.linalg.norm(TERRAIN_LIGHT)
    color, ground, water = terrain.colorize(heightmap, sea_level, canvas.rng, light)
    land, lake, _ = terrain.render(canvas, ground, color, water, CAMERA)
    scenery.reflect_water(canvas, lake)
    scenery.grass(canvas, BANK_TOP)
    for base, height, width in PINES:
        scenery.pine(painter, base, height, width)
    canvas.importance = SKY_DETAIL + land * (LAND_DETAIL - SKY_DETAIL)


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, units_size=CANVAS_UNITS, description=__doc__)
