"""Still-life objects for the relief renderer: fruit, bottles, jugs, cloth, table.

Every builder adds parts to a Relief and returns the object's base point so
the scene can place its table shadow.
"""
import cv2
import numpy as np

from . import shading
from .config import Material, rgb
from .geometry import Frame, Taper, catmull_rom, ellipse, lock
from .relief import FRONT, lathe_height, profile

STEM = rgb("#4A3020")
LEAF = Material(base=rgb("#5E9A44"), shadow=rgb("#24503A"), line=rgb("#16302A"), light=rgb("#A8D878"))
TABLE_SHADOW = rgb("#1A1418")
SHADOW_STRETCH = 1.7         # table shadow length as a multiple of the object's half-width
SHADOW_FLATNESS = 0.20       # the table is seen at a low angle, so shadows are thin ellipses
RED_APPLE = Material(base=rgb("#C8362C"), shadow=rgb("#5A1028"), line=rgb("#3A0A1C"), accent=rgb("#E2B242"),
                     light=rgb("#FF9C84"))
GREEN_APPLE = Material(base=rgb("#9CC544"), shadow=rgb("#3E6A30"), line=rgb("#20401E"), accent=rgb("#DCDC68"),
                       light=rgb("#E6F6A8"))
ORANGE = Material(base=rgb("#F08A1C"), shadow=rgb("#A4481C"), line=rgb("#5E2A14"), light=rgb("#FFD488"))
LEMON = Material(base=rgb("#F2D43A"), shadow=rgb("#AE8A22"), line=rgb("#5E4A14"), light=rgb("#FFF6B0"))
PEAR = Material(base=rgb("#D2C24C"), shadow=rgb("#7A6A28"), line=rgb("#4A3E18"), accent=rgb("#C07A3C"),
                light=rgb("#F4EEA0"))
GRAPE = Material(base=rgb("#5E3074"), shadow=rgb("#22103A"), line=rgb("#140A24"), light=rgb("#B8A0DC"))
GLASS = Material(base=rgb("#2F5E40"), shadow=rgb("#0C2420"), line=rgb("#06140F"), light=rgb("#8ED0A0"))
CERAMIC = Material(base=rgb("#E9E3D6"), shadow=rgb("#8C8698"), line=rgb("#4A4658"), light=rgb("#FFFFFF"))
PAPER = Material(base=rgb("#EADFC4"), shadow=rgb("#9A8E7C"), line=rgb("#5A5044"), light=rgb("#FFF8E6"))
CLOTH = Material(base=rgb("#F1EDE4"), shadow=rgb("#9892A6"), line=rgb("#5A5668"), light=rgb("#FFFFFF"))


def room(canvas, table_back_y, table_front_y, wall=(rgb("#55483E"), rgb("#2A2320")),
         wood=(rgb("#8A5E3E"), rgb("#5E3C28")), light_center=(300.0, 250.0)):
    """Backdrop wall with a pool of light, and a table top with its front face."""
    xs, ys = canvas.grid()
    pool = canvas.soft_ellipse(light_center, canvas.units_width * 0.75, canvas.units_height * 0.8)[..., None]
    canvas.rgb = (wall[1] * (1 - pool) + wall[0] * pool).astype(np.float32)
    top = shading.smoothstep(table_back_y - 1.0, table_back_y + 1.0, ys)
    depth = shading.linear_ramp(ys, table_back_y, table_front_y)[..., None]
    grain = (canvas.noise(14.0, octaves=2) - 0.5)[..., None] * 0.05
    canvas.blend(top, wood[1] * (1 - depth) + wood[0] * depth + grain)
    front = shading.smoothstep(table_front_y - 1.0, table_front_y + 1.0, ys)
    canvas.blend(front, wood[1] * 0.62)
    canvas.blend(front * (1 - shading.smoothstep(table_front_y + 4.0, table_front_y + 7.0, ys)), wood[0] * 1.25)


def table_shadow(relief, base, half_width, away=(1.0, 0.0), opacity=0.62, receivers=("cloth",)):
    """Shadow an object throws along the table, plus the dark contact line under it.

    Call after every object is added: the shadow goes on the bare table (canvas)
    and on the receiver parts of the relief, never on the objects themselves.
    """
    canvas = relief.canvas
    length = half_width * SHADOW_STRETCH
    center = (base[0] + away[0] * length * 0.62, base[1] + away[1] * length * 0.62 - half_width * 0.05)
    cast = canvas.soft_ellipse(center, length, half_width * SHADOW_FLATNESS * 1.6)
    contact = canvas.soft_ellipse((base[0] + half_width * 0.1, base[1] - half_width * 0.04),
                                  half_width * 0.95, half_width * SHADOW_FLATNESS * 0.7)
    shadow = np.clip(cast * 0.9 + contact, 0.0, 1.0)
    canvas.blend(shadow, TABLE_SHADOW, opacity)
    relief.tint(shadow, TABLE_SHADOW * 2.2, opacity * 0.8, only=receivers)


def round_fruit(relief, name, center, radius, material, squash=0.94, gloss=0.5, mottle=0.5, dimple=True,
                pores=0.0, depth=FRONT):
    """Apple, orange, plum: a slightly squashed sphere. Returns its base point."""
    canvas = relief.canvas
    mask = canvas.mask(ellipse(center, radius, radius * squash, samples=96))
    tone = canvas.noise(radius * 0.9, octaves=3) * mottle if material.accent is not None else None
    relief.add(name, mask, material, depth=depth, tone=tone, gloss=gloss)
    if dimple:
        hollow = canvas.soft_ellipse((center[0] + radius * 0.05, center[1] - radius * squash * 0.80),
                                     radius * 0.42, radius * 0.20)
        relief.groove(hollow * mask, canvas.px(radius * 0.22))
    if pores > 0:
        relief.height += (canvas.noise(radius * 0.045, octaves=1) - 0.5) * canvas.px(pores) * (mask > 0.5)
    return (center[0], center[1] + radius * squash)


def stem(painter, top_center, length, lean=0.25, leaf=None):
    """Stem (and optional leaf) drawn after relief.render, since both are thin graphic shapes."""
    root = np.asarray(top_center, dtype=np.float64)
    tip = root + np.array([lean * length, -length])
    curve = catmull_rom([root, (root + tip) / 2 + np.array([-lean * length * 0.3, 0.0]), tip])
    painter.stroke(curve, length * 0.16, STEM, Taper.START)
    if leaf is not None:
        polygon, center = lock(tip, tip + np.asarray(leaf), np.linalg.norm(leaf) * 0.5, 0.2)
        painter.part("leaf", painter.canvas.mask(polygon), LEAF, roundness=0.6)
        painter.stroke(center[2:-2], np.linalg.norm(leaf) * 0.03, LEAF.shadow, Taper.END, 0.7)


def lathe_object(relief, name, axis_x, top_y, bottom_y, radius_points, material, gloss, depth=0.0,
                 base_roundness=0.22, top_roundness=0.0, mottle=0.0):
    """Bottle, jug or pear from a radius profile [(t, radius), ...]. Returns (base point, mask)."""
    canvas = relief.canvas
    height, mask = lathe_height(canvas, axis_x, top_y, bottom_y, profile(radius_points),
                                base_roundness, top_roundness)
    tone = canvas.noise(60.0, octaves=3) * mottle if mottle > 0 else None
    relief.add(name, mask, material, depth=depth, height=height, gloss=gloss, tone=tone)
    return (axis_x, bottom_y + radius_points[-1][1] * base_roundness), mask


def mouth(relief, name, center, radius, material, flatness=0.22):
    """Dark opening of a jug or bowl seen from slightly above."""
    canvas = relief.canvas
    rim = canvas.mask(ellipse(center, radius, radius * flatness))
    inner = canvas.mask(ellipse((center[0], center[1] + radius * 0.02), radius * 0.86, radius * flatness * 0.80))
    relief.tint(rim, material.light, 0.6, only=(name,))
    relief.tint(inner, material.shadow * 0.45, 0.95, only=(name,))


def band(relief, mask, top_y, bottom_y, color, opacity=0.9):
    """Painted stripe around a lathe object."""
    _, ys = relief.canvas.grid()
    stripe = shading.smoothstep(top_y - 1.5, top_y + 1.5, ys) * (1 - shading.smoothstep(bottom_y - 1.5, bottom_y + 1.5, ys))
    relief.tint(stripe * mask, color, opacity)


def label(relief, name, bottle_mask, top_y, bottom_y, material=PAPER):
    _, ys = relief.canvas.grid()
    area = ((ys > top_y) & (ys < bottom_y)).astype(np.float32) * (bottle_mask > 0.5)
    relief.add(name, cv2.GaussianBlur(area, (0, 0), 0.8), material, drape=True, gloss=0.0)


def grapes(relief, name, top_center, count, grape_radius, material=GRAPE, spread=2.6, length=4.2):
    """Bunch of grapes hanging/lying as a tapering heap of small spheres. Returns its base point."""
    canvas = relief.canvas
    rng = canvas.rng
    centers = []
    for _ in range(count):
        down = rng.random() ** 0.8
        across = rng.uniform(-1.0, 1.0) * (1.0 - down * 0.75)
        centers.append((top_center[0] + across * spread * grape_radius,
                        top_center[1] + down * length * grape_radius))
    centers.sort(key=lambda c: c[1])                     # lower grapes lie in front
    for index, center in enumerate(centers):
        radius = grape_radius * rng.uniform(0.85, 1.1)
        relief.add(name, canvas.mask(ellipse(center, radius, radius * 0.96, samples=40)), material,
                   depth=FRONT, gloss=0.75)
    lowest = max(center[1] for center in centers)
    return (top_center[0], lowest + grape_radius)


def cloth(relief, name, outline, material=CLOTH, fold_units=120.0, fold_height=26.0, direction=0.5):
    """Draped cloth: a flat shape whose surface carries long soft folds."""
    canvas = relief.canvas
    mask = canvas.mask(catmull_rom(outline, closed=True))
    xs, ys = canvas.grid()
    along = xs * np.cos(direction) + ys * np.sin(direction)
    # Folds wander and swell unevenly; evenly spaced ridges read as corrugated iron.
    wander = canvas.noise(fold_units * 3.0, octaves=2) * fold_units * 3.2
    swell = canvas.noise(fold_units * 2.0, octaves=2)
    folds = (0.5 + 0.5 * np.sin((along + wander) * 2 * np.pi / fold_units)) ** 2.0 * swell
    edge = np.clip(shading.inside_distance(mask) / canvas.px(18.0), 0.0, 1.0)
    height = (folds * fold_height + 3.0) * canvas.px_per_unit * edge
    relief.add(name, mask, material, height=height.astype(np.float32), gloss=0.0)


def tilted_ellipse_fruit(relief, name, center, radius_x, radius_y, rotation, material, gloss=0.35, pores=0.0):
    """Lemon, plum on its side, egg: an ellipsoid at an angle. Returns its base point."""
    canvas = relief.canvas
    shape = Frame(center, 1.0, rotation).apply(ellipse((0.0, 0.0), radius_x, radius_y, samples=96))
    mask = canvas.mask(shape)
    relief.add(name, mask, material, depth=FRONT, gloss=gloss)
    if pores > 0:
        relief.height += (canvas.noise(radius_y * 0.06, octaves=1) - 0.5) * canvas.px(pores) * (mask > 0.5)
    return (center[0], float(shape[:, 1].max()))
