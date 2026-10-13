"""Light and shadow derived from masks.

A flat mask has no form, so form is faked the way a cel painter does it:
(1) round the shape off near its edge and light that bevel,
(2) drop shadows from one shape onto another by shifting the occluder.
"""
import cv2
import numpy as np

BEVEL_STEEPNESS = 1.6      # how strongly the rounded edge turns away from the viewer
MIN_BEVEL_PX = 2.0


def smoothstep(edge_low, edge_high, value):
    t = np.clip((value - edge_low) / (edge_high - edge_low + 1e-9), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def blur(image, sigma_px):
    if sigma_px <= 0.3:
        return image
    return cv2.GaussianBlur(image, (0, 0), sigmaX=float(sigma_px), sigmaY=float(sigma_px))


def inside_distance(mask):
    """Distance in pixels from each inside pixel to the shape boundary."""
    return cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5)


def bevel_light(mask, light, roundness):
    """Relative light on a shape treated as a pillow. 1.0 = flat interior.

    roundness is the bevel width as a share of the shape's half-thickness, so
    the same value gives a similar look on a thin lock and on a wide torso.
    """
    distance = inside_distance(mask)
    thickest = float(distance.max())
    if thickest <= 0.0:
        return np.ones_like(mask)
    bevel_px = max(MIN_BEVEL_PX, roundness * thickest)
    profile = np.clip(distance / bevel_px, 0.0, 1.0)
    height = np.sin(profile * np.pi / 2)            # quarter-circle cross-section
    height = blur(height.astype(np.float32), bevel_px * 0.22)
    slope_x = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0 * bevel_px * BEVEL_STEEPNESS
    slope_y = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0 * bevel_px * BEVEL_STEEPNESS
    normal_length = np.sqrt(slope_x**2 + slope_y**2 + 1.0)
    lambert = (-slope_x * light[0] - slope_y * light[1] + light[2]) / normal_length
    return lambert / light[2]


def cast_shadow(occluder, receiver, offset_px, edge_px):
    """Shadow of `occluder` on `receiver`, offset away from the light."""
    dx, dy = offset_px
    shift = np.float32([[1, 0, dx], [0, 1, dy]])
    moved = cv2.warpAffine(occluder, shift, (occluder.shape[1], occluder.shape[0]))
    return blur(moved, edge_px) * receiver


def outline_band(mask, width_px, light, shadow_side_gain=0.7):
    """Line-art alpha hugging the inside of a shape edge.

    The line is heavier on the side facing away from the light, which is how
    inkers suggest weight without any shading.
    """
    distance = inside_distance(mask)
    soft = blur(mask, max(1.5, width_px * 1.5))
    grad_x = cv2.Sobel(soft, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(soft, cv2.CV_32F, 0, 1, ksize=3)
    length = np.sqrt(grad_x**2 + grad_y**2) + 1e-6
    # The mask gradient points inward; the outward normal is its negative.
    facing_away = np.clip((grad_x * light[0] + grad_y * light[1]) / length, 0.0, 1.0)
    local_width = width_px * (1.0 + shadow_side_gain * facing_away)
    return np.clip(local_width - distance + 0.5, 0.0, 1.0) * mask


def linear_ramp(coordinate, start, end):
    """0 at `start`, 1 at `end`, clamped. Used for top-to-bottom colour drift."""
    return np.clip((coordinate - start) / (end - start + 1e-9), 0.0, 1.0)
