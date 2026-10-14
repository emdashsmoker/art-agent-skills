"""paintkit.objects: hard-surface objects (devices, furniture, boxes, cups).

Man-made things are boxes and cylinders with details on their faces. A
Stage is a fixed camera that turns real-world sizes (any unit, e.g. cm)
into picture positions; `box` and `cylinder` paint the visible faces with a
tone per face, and every face can place details on itself in 0-1 face
coordinates (a screen on the front of a monitor, keys on a keyboard).

Draw back to front: floor and wall first, then far objects, then near ones.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import core as pk

WORLD_LIGHT = (-0.45, 0.80, -0.40)      # toward the light: from the upper left, in front


class Stage:
    """Camera for object scenes.

    World axes: x right, y up, z away from the viewer. `yaw` orbits the
    camera sideways (positive shows the left sides of things), `pitch`
    raises it (positive looks down on the tops). `distance` adds
    perspective: None is a parallel projection (clean, product-drawing
    look), a number is the camera distance in world units.
    """

    def __init__(self, shape, origin, scale: float, yaw: float = 28.0, pitch: float = 22.0,
                 distance: float | None = None, light=WORLD_LIGHT):
        self.shape = shape
        self.origin = np.asarray(origin, np.float32)
        self.scale = float(scale)                      # pixels per world unit at the origin
        self.distance = distance
        yaw_r, pitch_r = np.deg2rad(yaw), np.deg2rad(pitch)
        cy, sy, cp, sp = np.cos(yaw_r), np.sin(yaw_r), np.cos(pitch_r), np.sin(pitch_r)
        # Rows: screen right, screen up, depth (larger = farther).
        self.basis = np.array([[cy, 0.0, -sy],
                               [sy * sp, cp, cy * sp],
                               [sy * cp, -sp, cy * cp]], np.float32)
        light = np.asarray(light, np.float32)
        self.light = light / np.linalg.norm(light)

    def camera(self, points) -> np.ndarray:
        return np.asarray(points, np.float32).reshape(-1, 3) @ self.basis.T

    def project(self, points) -> np.ndarray:
        """World points (N x 3) to pixels (N x 2)."""
        cam = self.camera(points)
        zoom = 1.0 if self.distance is None else self.distance / np.maximum(self.distance + cam[:, 2], 1e-3)
        return self.origin + np.stack([cam[:, 0], -cam[:, 1]], axis=1) * (self.scale * np.reshape(zoom, (-1, 1)))

    def faces_camera(self, normal) -> bool:
        return float(self.basis[2] @ np.asarray(normal, np.float32)) < -1e-6

    def tone(self, normal, color, shadow=None) -> np.ndarray:
        """Face color from how squarely the face meets the light."""
        base = pk.rgb(color)
        dark = pk.adjust(base, value=0.55, sat=1.15) if shadow is None else pk.rgb(shadow)
        lit = float(np.clip(0.30 + 0.75 * max(float(self.light @ np.asarray(normal, np.float32)), 0.0), 0.0, 1.0))
        return dark * (1.0 - lit) + base * lit

    def ground_shadow(self, points, softness: float = 6.0) -> np.ndarray:
        """Mask of the shadow that world points cast on the plane y = 0."""
        pts = np.asarray(points, np.float32).reshape(-1, 3)
        dropped = pts - self.light[None, :] * (pts[:, 1:2] / self.light[1])
        hull = cv2.convexHull(self.project(np.vstack([dropped, pts * [1, 0, 1]])).astype(np.float32))[:, 0, :]
        return pk.blur(pk.fill_mask(self.shape, hull), softness)


class Face:
    """One flat face: place details on it in face coordinates (u right, v down, both 0-1)."""

    def __init__(self, stage: Stage, corner, u_vec, v_vec, normal):
        self.stage = stage
        self.corner = np.asarray(corner, np.float32)       # world position of (u=0, v=0)
        self.u_vec = np.asarray(u_vec, np.float32)
        self.v_vec = np.asarray(v_vec, np.float32)
        self.normal = np.asarray(normal, np.float32)
        self.width = float(np.linalg.norm(self.u_vec))
        self.height = float(np.linalg.norm(self.v_vec))

    def world(self, uv) -> np.ndarray:
        uv = np.asarray(uv, np.float32).reshape(-1, 2)
        return self.corner + uv[:, :1] * self.u_vec + uv[:, 1:] * self.v_vec

    def at(self, uv) -> np.ndarray:
        """Face coordinates to pixels."""
        return self.stage.project(self.world(uv))

    def rect(self, u0: float, v0: float, u1: float, v1: float, radius: float = 0.0) -> np.ndarray:
        """Pixel polygon of a rectangle on the face; `radius` rounds corners (world units)."""
        if radius <= 0:
            return self.at([[u0, v0], [u1, v0], [u1, v1], [u0, v1]])
        ru, rv = radius / self.width, radius / self.height
        ru, rv = min(ru, (u1 - u0) / 2), min(rv, (v1 - v0) / 2)
        arc = np.linspace(0.0, np.pi / 2, 7)
        corners = [(u1 - ru, v0 + rv, -np.pi / 2), (u1 - ru, v1 - rv, 0.0), (u0 + ru, v1 - rv, np.pi / 2),
                   (u0 + ru, v0 + rv, np.pi)]
        points = [[cu + np.cos(start + a) * ru, cv + np.sin(start + a) * rv] for cu, cv, start in corners for a in arc]
        return self.at(points)

    def mask(self, radius: float = 0.0) -> np.ndarray:
        return pk.fill_mask(self.stage.shape, self.rect(0.0, 0.0, 1.0, 1.0, radius))


def box(stage: Stage, layer: pk.Layer, center, size, color, shadow=None, radius: float = 0.0,
        edge: float = 0.0) -> dict:
    """Paint a box and return its visible faces {"front" | "back" | "left" | "right" | "top" | "bottom": Face}.

    center: world position of the middle of the box's bottom face.
    size: (width x, height y, depth z). radius: corner rounding of each face.
    edge: opacity of a light line along face borders (catches the bevel of a manufactured edge).
    """
    cx, cy, cz = center
    w, h, d = size
    x0, x1, y0, y1, z0, z1 = cx - w / 2, cx + w / 2, cy, cy + h, cz - d / 2, cz + d / 2
    candidates = {
        "front": ((x0, y1, z0), (w, 0, 0), (0, -h, 0), (0, 0, -1)),
        "back": ((x1, y1, z1), (-w, 0, 0), (0, -h, 0), (0, 0, 1)),
        "left": ((x0, y1, z1), (0, 0, -d), (0, -h, 0), (-1, 0, 0)),
        "right": ((x1, y1, z0), (0, 0, d), (0, -h, 0), (1, 0, 0)),
        "top": ((x0, y1, z1), (w, 0, 0), (0, 0, -d), (0, 1, 0)),
        "bottom": ((x0, y0, z0), (w, 0, 0), (0, 0, d), (0, -1, 0)),
    }
    faces = {name: Face(stage, *parts) for name, parts in candidates.items() if stage.faces_camera(parts[3])}
    # Rounded corners belong to the two largest faces (the caps); the thin sides wrap around them.
    cap_names = _CAP_FACES[int(np.argmin(size))] if radius > 0 else ()
    if cap_names:
        outlines = [Face(stage, *candidates[name]).rect(0.0, 0.0, 1.0, 1.0, radius) for name in cap_names]
        hull = cv2.convexHull(np.vstack(outlines).astype(np.float32))[:, 0, :]
        sides = [stage.tone(face.normal, color, shadow) for name, face in faces.items() if name not in cap_names]
        if sides:
            layer.paint(pk.fill_mask(stage.shape, hull), np.mean(sides, axis=0))
    for name, face in faces.items():
        if cap_names and name not in cap_names:
            continue
        mask = face.mask(radius if name in cap_names else 0.0)
        layer.paint(mask, stage.tone(face.normal, color, shadow))
        if edge > 0:
            rim = np.clip(mask - cv2.erode(mask, np.ones((3, 3), np.uint8)), 0.0, 1.0)
            layer.paint(rim, pk.mix(color, "#ffffff", 0.6), edge)
    return faces


_CAP_FACES = {0: ("left", "right"), 1: ("top", "bottom"), 2: ("front", "back")}   # by thinnest axis
PEBBLE_LEVELS = 7


def pebble(stage: Stage, layer: pk.Layer, center, size, color, shadow=None) -> np.ndarray:
    """Low rounded object without flat faces (mouse, soap, stone, cushion). Returns its mask.

    center: middle of the footprint. size: (width x, height y, depth z).
    """
    cx, cy, cz = center
    w, h, d = size
    ang = np.linspace(0.0, 2 * np.pi, 48, endpoint=False)
    rings = []
    for level in np.linspace(0.0, 1.0, PEBBLE_LEVELS):
        shrink = np.sqrt(max(1.0 - level ** 2, 0.0))          # half-ellipsoid profile
        rings.append(np.stack([cx + np.cos(ang) * w / 2 * shrink, np.full_like(ang, cy + h * level),
                               cz + np.sin(ang) * d / 2 * shrink], axis=1))
    hull = cv2.convexHull(stage.project(np.vstack(rings)).astype(np.float32))[:, 0, :]
    mask = pk.fill_mask(stage.shape, hull)
    base = pk.rgb(color)
    dark = pk.adjust(base, value=0.62, sat=1.1) if shadow is None else pk.rgb(shadow)
    # The lit point sits toward the light; tone falls off with distance from it.
    middle, reach = hull.mean(axis=0), np.ptp(hull, axis=0).max()
    lit_at = middle + np.array([np.sign(stage.light[0]) * 0.18, -0.20]) * reach
    falloff = 1.0 - pk.radial_ramp(stage.shape, lit_at, reach * 0.95)     # 0 at the lit point
    layer.paint(mask, base)
    layer.paint(mask * pk.smoothstep(0.35, 1.0, falloff), dark, 0.8)
    layer.paint(mask * (1.0 - pk.smoothstep(0.0, 0.28, falloff)), pk.mix(base, "#ffffff", 0.7), 0.5)
    return mask


def cylinder(stage: Stage, layer: pk.Layer, center, radius: float, height: float, color, shadow=None,
             top_color=None, taper: float = 1.0) -> dict:
    """Upright cylinder (cup, can, lamp post, pot). `taper` scales the bottom radius.

    Returns {"top": pixel polygon of the top rim, "mask": whole mask}.
    """
    cx, cy, cz = center
    ang = np.linspace(0.0, 2 * np.pi, 64, endpoint=False)
    ring = np.stack([np.cos(ang), np.zeros_like(ang), np.sin(ang)], axis=1)
    top = stage.project(ring * radius + [cx, cy + height, cz])
    bottom = stage.project(ring * radius * taper + [cx, cy, cz])
    hull = cv2.convexHull(np.vstack([top, bottom]).astype(np.float32))[:, 0, :]
    mask = pk.fill_mask(stage.shape, hull)
    base = pk.rgb(color)
    dark = pk.adjust(base, value=0.55, sat=1.15) if shadow is None else pk.rgb(shadow)
    # Round side: light falls off across the width, like a column.
    left, right = hull[:, 0].min(), hull[:, 0].max()
    side = 1.0 if stage.light[0] < 0 else -1.0
    start, end = (left, right) if side > 0 else (right, left)
    across = pk.linear_ramp(stage.shape, (start, 0), (end, 0))
    shade = pk.smoothstep(0.35, 1.0, across)
    layer.paint(mask, base)
    layer.paint(mask * shade, dark, 0.85)
    gloss = np.exp(-((across - 0.22) / 0.07) ** 2) * mask
    layer.paint(gloss, pk.mix(base, "#ffffff", 0.7), 0.35)
    top_mask = pk.fill_mask(stage.shape, top)
    layer.paint(top_mask, stage.tone((0, 1, 0), base if top_color is None else top_color, shadow))
    return {"top": top, "mask": mask}


def polygon(stage: Stage, layer: pk.Layer, points, color, opacity: float = 1.0, softness: float = 0.0) -> np.ndarray:
    """Fill a flat polygon given by world points (floor, wall, rug, sheet of paper)."""
    mask = pk.blur(pk.fill_mask(stage.shape, stage.project(points)), softness)
    layer.paint(mask, color, opacity)
    return mask


def text_lines(face: Face, layer: pk.Layer, area, rows: int, colors, seed: int = 0, indent: bool = True,
               thickness: float = 0.35) -> None:
    """Rows of short bars that read as text or code on a screen or page.

    area: (u0, v0, u1, v1) on the face. thickness: bar height as a share of the row pitch.
    """
    rng = np.random.default_rng(seed)
    u0, v0, u1, v1 = area
    pitch = (v1 - v0) / rows
    groups = {index: [] for index in range(len(colors))}
    for row in range(rows):
        u = u0 + (rng.integers(0, 4) * 0.04 * (u1 - u0) if indent else 0.0)
        v = v0 + row * pitch
        if rng.random() < 0.12:
            continue                                  # blank line
        while u < u1 - 0.04 * (u1 - u0):
            length = rng.uniform(0.05, 0.22) * (u1 - u0)
            end = min(u + length, u1)
            groups[int(rng.integers(len(colors)))].append(face.rect(u, v, end, v + pitch * thickness))
            u = end + 0.025 * (u1 - u0)
            if rng.random() < 0.3:
                break
    for index, quads in groups.items():
        if quads:
            layer.paint(pk.fill_mask(face.stage.shape, quads, ss=2), colors[index])


def grid(face: Face, area, columns: int, rows: int, gap: float = 0.18, radius: float = 0.0) -> list:
    """Pixel polygons of a grid of equal cells on a face (keys, windows, tiles, app icons)."""
    u0, v0, u1, v1 = area
    cell_u, cell_v = (u1 - u0) / columns, (v1 - v0) / rows
    cells = []
    for row in range(rows):
        for col in range(columns):
            cu, cv = u0 + col * cell_u, v0 + row * cell_v
            cells.append(face.rect(cu + cell_u * gap / 2, cv + cell_v * gap / 2,
                                   cu + cell_u * (1 - gap / 2), cv + cell_v * (1 - gap / 2), radius))
    return cells
