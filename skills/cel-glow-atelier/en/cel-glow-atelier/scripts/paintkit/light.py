"""paintkit.light: lighting derived from 2D masks (no 3D model).

A flat shape is "inflated" into a height field, which yields surface
normals, which yield form shadows for any light direction. Cast shadows,
occlusion and rim light come from shifting and blurring masks. Because all
of it derives from one light vector, every part of a picture stays lit
consistently without hand-placing each shadow.
"""
from __future__ import annotations

import cv2
import numpy as np

from .core import blur, shift, smoothstep


def light_vector(azimuth_deg: float, elevation_deg: float = 45.0) -> np.ndarray:
    """Unit vector pointing *toward* the light.

    azimuth: 0 = from the right, 90 = from the top, 135 = from the top-left
    (screen space, y axis pointing down). elevation: 90 = from the viewer.
    """
    az, el = np.deg2rad(azimuth_deg), np.deg2rad(elevation_deg)
    return np.array([np.cos(az) * np.cos(el), -np.sin(az) * np.cos(el), np.sin(el)], np.float32)


def inflate(mask, radius: float) -> np.ndarray:
    """Height field that bulges a flat mask like a pillow.

    `radius` is the distance from the edge over which the surface rises;
    use about half the shape's thickness for round forms and a small value
    for flat forms with a rounded rim.
    """
    binary = (mask > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    t = np.clip(dist / max(radius, 1e-6), 0.0, 1.0)
    height = np.sqrt(1.0 - (1.0 - t) ** 2) * radius
    return blur(height.astype(np.float32), max(radius * 0.12, 1.0))


def normals_from_height(height) -> np.ndarray:
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    nrm = np.stack([-gx, -gy, np.ones_like(gx)], axis=-1)
    return nrm / np.linalg.norm(nrm, axis=-1, keepdims=True)


def sphere_normals(shape, center, radius_x: float, radius_y: float) -> np.ndarray:
    """Analytic normals of an ellipsoid; steadier than `inflate` for a head."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    nx = (xx - center[0]) / radius_x
    ny = (yy - center[1]) / radius_y
    nz = np.sqrt(np.clip(1.0 - nx ** 2 - ny ** 2, 0.04, 1.0))
    nrm = np.stack([nx, ny, nz], axis=-1)
    return nrm / np.linalg.norm(nrm, axis=-1, keepdims=True)


def lambert(normal_map, light) -> np.ndarray:
    """Diffuse term in [-1, 1] (1 = facing the light)."""
    return (normal_map @ np.asarray(light, np.float32)).astype(np.float32)


def form_shadow(lit, threshold: float = 0.25, softness: float = 0.02) -> np.ndarray:
    """Shadow mask (1 = shadow) from a diffuse term.

    softness near 0 gives the hard cel edge of anime; 0.3+ gives the
    gradual turn of painterly shading.
    """
    return 1.0 - smoothstep(threshold - softness, threshold + softness, lit)


def cast_shadow(occluder, receiver, light, distance: float, softness: float = 0.0,
                down_bias: float = 0.0) -> np.ndarray:
    """Shadow that `occluder` throws onto `receiver`, displaced away from the light.

    down_bias (0-1) bends the throw toward straight down; a chin shadow on a
    neck reads better when it drops than when it slides sideways.
    """
    direction = -np.asarray(light[:2], np.float32)
    direction = direction / (float(np.linalg.norm(direction)) or 1.0)
    direction = direction * (1.0 - down_bias) + np.array([0.0, 1.0], np.float32) * down_bias
    norm = float(np.linalg.norm(direction)) or 1.0
    dx, dy = direction / norm * distance
    moved = blur(shift(occluder, float(dx), float(dy)), softness)
    return np.clip(moved * receiver, 0.0, 1.0)


def rim(mask, light, width: float, softness: float = 1.0) -> np.ndarray:
    """Thin band along the edge of `mask` that faces the light."""
    direction = -np.asarray(light[:2], np.float32)
    norm = float(np.linalg.norm(direction)) or 1.0
    dx, dy = direction / norm * width
    band = mask * (1.0 - shift(mask, float(dx), float(dy)))
    return np.clip(blur(band, softness) * mask, 0.0, 1.0)


def occlusion(occluder, receiver, spread: float, strength: float = 1.0) -> np.ndarray:
    """Soft contact darkening on `receiver` around `occluder`."""
    return np.clip(blur(occluder, spread) * receiver * strength, 0.0, 1.0)


def outline_mask(mask, width: float, light=None, variation: float = 0.0) -> np.ndarray:
    """Outline band hugging the outside-inside edge of a mask.

    With `light` and `variation` > 0 the line thins on the lit side and
    thickens on the shadow side, the way an inked line carries weight.
    """
    inner = cv2.erode(mask, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (int(width * 2) | 1, int(width * 2) | 1)))
    band = np.clip(mask - inner, 0.0, 1.0)
    if light is None or variation <= 0:
        return band
    soft = blur(mask, max(width * 2.0, 1.5))
    gx = cv2.Sobel(soft, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(soft, cv2.CV_32F, 0, 1, ksize=3)
    length = np.sqrt(gx ** 2 + gy ** 2) + 1e-6
    # Outward normal of the silhouette is -gradient of the mask.
    facing = (-gx / length) * light[0] + (-gy / length) * light[1]
    weight = np.clip(1.0 - variation * (facing * 0.5 + 0.5), 0.0, 1.0)
    return band * weight


def paint_form(layer, mask, base, shadow, light, radius: float, threshold: float = 0.25,
               softness: float = 0.05, strength: float = 1.0) -> np.ndarray:
    """Fill a part with `base` and add its inflated form shadow in one call.

    Returns the shadow mask so callers can stack further tones on it.
    """
    layer.paint(mask, base)
    lit = lambert(normals_from_height(inflate(mask, radius)), light)
    shade = form_shadow(lit, threshold, softness) * mask
    layer.paint(shade, shadow, strength)
    return shade
