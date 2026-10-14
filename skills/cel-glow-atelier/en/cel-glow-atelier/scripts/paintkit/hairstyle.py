"""paintkit.hairstyle: hair textures shared by the front, profile and back rigs.

Curls: small C-shaped arcs scattered over the hair, a dark arc with a short
light arc beside it toward the light, so the hair reads as a mass of ringlets.
Undercut: the shaved part of a two-block cut, a stubble tone between hair and
skin under the longer top; the zone is given per rig in that rig's head units.
"""
from __future__ import annotations

import numpy as np

from . import core as pk

CURL_RADIUS = 0.032               # head units
CURL_DENSITY = 0.55               # curls per curl-sized area of hair
CURL_MAX = 420
CURL_WIDTH = 0.0045
STUBBLE_MIX = 0.36                # stubble color: hair mixed toward the skin
STUBBLE_DOTS = 0.05               # share of stubble pixels that get a darker speck
# Undercut zones (polygons in each rig's head units): below the top hair, above and behind the ear.
UNDERCUT_FRONT = ((0.285, -0.20), (0.62, -0.22), (0.62, 0.25), (0.285, 0.25))
UNDERCUT_PROFILE = ((0.12, -0.20), (-0.62, -0.09), (-0.62, 0.45), (0.12, 0.45))
UNDERCUT_BACK = ((-0.70, -0.10), (0.70, -0.10), (0.70, 0.60), (-0.70, 0.60))


def curl_paths(mask: np.ndarray, radius_px: float, seed: int) -> list:
    """Arc paths (pixels) spread over `mask`; each opens toward a random side."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask > 0.5)
    if len(xs) == 0:
        return []
    count = min(int(len(xs) / (np.pi * radius_px ** 2) * CURL_DENSITY), CURL_MAX)
    picks = rng.choice(len(xs), size=count, replace=len(xs) < count)
    paths = []
    for i in picks:
        r = radius_px * rng.uniform(0.6, 1.1)
        start = rng.uniform(0.0, 2.0 * np.pi)
        ang = start + np.linspace(0.0, rng.uniform(3.2, 4.6), 10)
        paths.append(np.stack([xs[i] + np.cos(ang) * r, ys[i] + np.sin(ang) * r * 0.8], 1).astype(np.float32))
    return paths


def paint_curls(fig, layer, mask, seed: int) -> None:
    """Ringlet texture over the hair mask in the hair's own shadow and light colors."""
    pal = fig.pal
    paths = curl_paths(mask, fig.px(CURL_RADIUS), seed)
    if not paths:
        return
    width = max(fig.px(CURL_WIDTH), 0.8)
    dark = pk.stroke_mask(fig.shape, [(p, width) for p in paths])
    toward = np.asarray(fig.light[:2], np.float32)
    toward = toward / (np.linalg.norm(toward) or 1.0) * fig.px(CURL_RADIUS) * 0.35
    light = pk.stroke_mask(fig.shape, [(p[2:7] + toward, width * 0.8) for p in paths])
    layer.paint(dark * mask, pal.hair_shadow, 0.6)
    layer.paint(light * mask, pk.mix(pal.hair, pal.hair_light, 0.85), 0.5)


def paint_undercut(fig, layer, zone: np.ndarray, keep: np.ndarray) -> None:
    """Stubble over `zone` (a mask already cut to the hair), except where `keep` (longer hair) covers it."""
    pal = fig.pal
    shaved = np.clip(zone * (1.0 - keep), 0.0, 1.0)
    stubble = pk.mix(pal.hair, pal.skin, STUBBLE_MIX)
    layer.paint(shaved, stubble)
    rng = np.random.default_rng(fig.spec.hair_seed)
    specks = (rng.random(fig.shape) < STUBBLE_DOTS).astype(np.float32)
    layer.paint(specks * shaved, pal.hair, 0.35)
    # The longer top hair throws a soft shade onto the shaved band right under it.
    edge = np.clip(pk.blur(keep, fig.px(0.012)) - keep, 0.0, 1.0)
    layer.paint(edge * shaved * 2.0, pal.hair_shadow, 0.6)
