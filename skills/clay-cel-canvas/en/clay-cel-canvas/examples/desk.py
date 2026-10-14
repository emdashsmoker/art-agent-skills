"""Worked example: a desk at night with a laptop, mug, phone, lamp and plant.

Usage: python desk.py <anime|illust|painterly> <output.png> [width_px]

Manufactured objects are boxes, slabs and cylinders, so they are modelled in
3-D (metres: x right, y away, z up, the desk top at z = 0) and projected with
one Camera. Every object is described in its own frame and set on the desk with
frame(origin, yaw), so it can be moved or turned without touching its shape.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atelier import STYLES, Art, Camera, mix, spline  # noqa: E402

# ---- plan -------------------------------------------------------------------
ASPECT = 0.75
LIGHT = (-0.50, -0.60, 0.62)
CAMERA = Camera(eye=(0.06, -0.80, 0.66), target=(0.0, 0.36, 0.12), focal=900, center=(500, 400))
DESK_DEPTH = 0.75
LAMP_HEAD = (-0.34, 0.47, 0.40)    # where the bulb is: shadows on the desk point away from it

PALETTE = {
    "wall": "#263545", "wall_light": "#3E5568", "desk": "#C39A6E", "desk_edge": "#8A6746",
    "shadow": "#6F5E7C", "metal": "#C9CED8", "metal_dark": "#9299A8", "key": "#2A2E38",
    "bezel": "#16181F", "screen": "#1C2133", "panel": "#151929", "glow": "#8FB6FF",
    "code": ("#C792EA", "#82AAFF", "#C3E88D", "#F78C6C", "#D7DCE8", "#89DDFF"),
    "mug": "#E0705A", "coffee": "#3B2318", "phone": "#1B1D24", "card": "#E8ECF5",
    "lamp": "#2F4858", "lamp_light": "#FFD79A", "pot": "#E9E3D8", "leaf": "#3F9460",
    "leaf_dark": "#2B6E4B", "note": ("#FFE27A", "#FF9FB0", "#9FD7FF"), "book": "#D9A441",
    "mouse": "#30343E", "pen": "#D8504A",
}


# ---- 3-D helpers --------------------------------------------------------------

def frame(origin, yaw=0.0):
    """Function taking an object's own (x, y, z) points to world points: turned, then moved."""
    turn = np.radians(yaw)
    cos, sin = np.cos(turn), np.sin(turn)

    def to_world(points):
        points = np.atleast_2d(np.asarray(points, float))
        x = points[:, 0] * cos - points[:, 1] * sin + origin[0]
        y = points[:, 0] * sin + points[:, 1] * cos + origin[1]
        return np.column_stack([x, y, points[:, 2]])

    return to_world


def slab(x0, x1, y0, y1, z, radius=0.0):
    """Horizontal rectangle at height z; radius rounds its corners."""
    if radius <= 0:
        return np.array([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], float)
    corners = ((x1 - radius, y1 - radius, 0), (x0 + radius, y1 - radius, 90),
               (x0 + radius, y0 + radius, 180), (x1 - radius, y0 + radius, 270))
    points = []
    for cx, cy, start in corners:
        for angle in np.radians(np.linspace(start, start + 90, 7)):
            points.append((cx + radius * np.cos(angle), cy + radius * np.sin(angle), z))
    return np.array(points, float)


def disc(cx, cy, radius, z, samples=40):
    """Horizontal circle; in the picture it becomes the right ellipse by itself."""
    angles = np.linspace(0, 2 * np.pi, samples, endpoint=False)
    return np.column_stack([cx + radius * np.cos(angles), cy + radius * np.sin(angles),
                            np.full(samples, float(z))])


def on_plane(origin, u, v, points):
    """2-D points (s, t) on a tilted plane to 3-D: origin + s * u + t * v."""
    points = np.asarray(points, float)
    return np.asarray(origin, float) + points[:, :1] * np.asarray(u, float) + points[:, 1:2] * np.asarray(v, float)


def seen(points):
    """World points as a canvas curve."""
    return CAMERA.project(points)


def hull(*point_sets):
    """Outline of a solid from the canvas points of its edges (convex solids only)."""
    points = np.vstack([seen(points) for points in point_sets]).astype(np.float32)
    return cv2.convexHull(points).reshape(-1, 2).astype(float)


def desk_shadow(art, desk, footprint, height):
    """Shadow of an object on the desk, thrown away from the lamp."""
    centre = footprint[:, :2].mean(axis=0)
    away = centre - LAMP_HEAD[:2]
    away = away / max(np.linalg.norm(away), 1e-6) * height * 0.9
    thrown = footprint + (away[0], away[1], 0)
    art.shadow(art.feather(art.shape(hull(footprint, thrown)), 4) * desk, PALETTE["shadow"], 0.75)


# ---- room -----------------------------------------------------------------------

def draw_room(art):
    art.paint(art.everywhere(), PALETTE["wall"])
    art.paint(art.blob(seen((-0.34, DESK_DEPTH, 0.45)), 420), PALETTE["wall_light"], 0.9)
    desk = art.shape(seen(slab(-1.6, 1.6, 0.0, DESK_DEPTH, 0.0)))
    art.part(desk, PALETTE["desk"], shade=False, outline=False)
    front = art.shape(seen(np.array([(-1.6, 0, 0), (1.6, 0, 0), (1.6, 0, -0.04), (-1.6, 0, -0.04)])))
    art.part(front, PALETTE["desk_edge"], shade=False)
    art.shadow(desk * art.ramp(seen((0, DESK_DEPTH - 0.1, 0)), seen((0, DESK_DEPTH, 0))),
               PALETTE["shadow"], 0.5)                       # the wall shades the back of the desk
    for index, (x, z, tilt) in enumerate(((0.16, 0.40, 4), (0.27, 0.38, -5), (0.21, 0.50, 2))):
        note = on_plane((x, DESK_DEPTH, z), (1, 0, 0), (0, 0, 1),
                        [(-0.04, -0.04), (0.04, -0.04), (0.04, 0.04), (-0.04, 0.04)])
        note = frame((0, 0))(note)
        centre = seen((x, DESK_DEPTH, z))
        with art.place(at=centre, angle=tilt, pivot=centre):
            art.part(seen(note), mix(PALETTE["note"][index], PALETTE["wall"], 0.3), bulge=4)
    return desk


# ---- objects (each in its own frame, origin on the desk) ---------------------------

def draw_laptop(art, desk, origin=(0.0, 0.33), yaw=-5.0):
    world = frame(origin, yaw)
    half, depth, thick = 0.16, 0.11, 0.014
    desk_shadow(art, desk, world(slab(-half, half, -depth, depth, 0)), 0.05)
    base_top = world(slab(-half, half, -depth, depth, thick, 0.012))
    art.part(hull(base_top, world(slab(-half, half, -depth, depth, 0, 0.012))), PALETTE["metal_dark"],
             shade=False)
    top = art.part(seen(base_top), PALETTE["metal"], shade=False)

    keys = []
    for row in range(4):
        for column in range(12):
            x, y = -0.135 + column * 0.0225, 0.085 - row * 0.021
            keys.append(seen(world(slab(x, x + 0.019, y - 0.017, y, thick, 0.003))))
    for x0, x1 in ((-0.135, -0.094), (-0.090, 0.044), (0.048, 0.1335)):       # bottom row, space bar
        keys.append(seen(world(slab(x0, x1, -0.016, 0.001, thick, 0.003))))
    art.paint(art.shapes(keys), PALETTE["key"])
    pad = art.shape(seen(world(slab(-0.05, 0.05, -0.098, -0.03, thick, 0.006))))
    art.paint(pad, mix(PALETTE["metal"], "#FFFFFF", 0.25))
    art.outline(pad, PALETTE["metal_dark"], 1.2)

    # The lid leans back from the hinge; everything on the display lives on that plane.
    lean = np.radians(18)
    hinge = world([(0, depth, thick)])[0]
    across = world([(1, 0, 0)])[0] - world([(0, 0, 0)])[0]
    back = world([(0, 1, 0)])[0] - world([(0, 0, 0)])[0]
    upward = back * np.sin(lean) + np.array([0, 0, 1]) * np.cos(lean)

    def on_lid(points):
        return seen(on_plane(hinge, across, upward, points))

    def lid_rect(s0, s1, t0, t1):
        return on_lid([(s0, t0), (s1, t0), (s1, t1), (s0, t1)])

    art.part(lid_rect(-half, half, 0, 0.215), PALETTE["bezel"], shade=False)
    display = art.shape(lid_rect(-half + 0.008, half - 0.008, 0.012, 0.207))
    art.paint(display, PALETTE["screen"])
    art.paint(art.shape(lid_rect(-0.152, -0.098, 0.012, 0.207)), PALETTE["panel"])
    art.paint(art.shape(lid_rect(-0.152, 0.152, 0.193, 0.207)), PALETTE["panel"])
    dots = [on_lid([(-0.145 + i * 0.009 + 0.003 * np.cos(a), 0.200 + 0.003 * np.sin(a))
                    for a in np.linspace(0, 6.28, 12)]) for i in range(3)]
    for dot, color in zip(dots, ("#FF5F57", "#FEBC2E", "#28C840")):
        art.paint(art.shape(dot), color)
    bars = {color: [] for color in PALETTE["code"]}
    for row in range(13):                                    # lines of code: indented coloured bars
        t = 0.182 - row * 0.0125
        s = -0.088 + 0.012 * int(art.rng.integers(0, 4))
        for _ in range(int(art.rng.integers(1, 5))):
            length = art.rng.uniform(0.012, 0.05)
            if s + length > 0.146:
                break
            color = PALETTE["code"][int(art.rng.integers(len(PALETTE["code"])))]
            bars[color].append(lid_rect(s, s + length, t, t + 0.006))
            s += length + 0.008
    for row in range(9):                                     # file list in the side panel
        t = 0.178 - row * 0.014
        bars[PALETTE["code"][4]].append(lid_rect(-0.146, -0.146 + art.rng.uniform(0.02, 0.042), t,
                                                 t + 0.005))
    for color, rects in bars.items():
        if rects:
            art.paint(art.shapes(rects), color, 0.95)
    art.light(art.feather(display, 10), PALETTE["glow"], 0.30)                # the screen glows
    art.light(top * art.ramp(seen(world([(0, -0.02, thick)])[0]), seen(world([(0, depth, thick)])[0])),
              PALETTE["glow"], 0.35)                                          # and lights the keys
    art.focus_on(art.feather(np.maximum(display, top), 4))


def draw_mug(art, desk, origin=(0.29, 0.19)):
    cx, cy = origin
    radius, height = 0.040, 0.092
    desk_shadow(art, desk, disc(cx, cy, radius, 0), height)
    scale = CAMERA.scale_at((cx, cy, 0))
    handle = [(cx + radius * 0.9, cy, height * 0.78), (cx + radius * 1.75, cy, height * 0.66),
              (cx + radius * 1.7, cy, height * 0.32), (cx + radius * 0.9, cy, height * 0.22)]
    art.part(art.tube([(*seen(point), 0.013 * scale) for point in handle]), PALETTE["mug"], bulge=4)
    body = art.part(hull(disc(cx, cy, radius, 0), disc(cx, cy, radius, height)), PALETTE["mug"])
    rim = art.part(seen(disc(cx, cy, radius, height)), mix(PALETTE["mug"], "#FFFFFF", 0.25),
                   shade=False)
    art.paint(art.shape(seen(disc(cx, cy, radius * 0.86, height))), PALETTE["coffee"])
    top = seen((cx, cy, height))
    art.light(art.blob(top + (-0.5 * radius * scale, 0.45 * height * scale), 9) * body, "#FFFFFF", 0.5)
    for shift in (-10, 9):                                   # steam
        wisp = spline([top + (shift, -8), top + (shift + 9, -40), top + (shift - 6, -74),
                       top + (shift + 5, -104)])
        art.light(art.feather(art.brush(wisp, 7), 4), "#FFFFFF", 0.28)
    art.focus_on(art.feather(np.maximum(body, rim), 4) * 0.8)


def draw_phone(art, desk, origin=(-0.30, 0.17), yaw=18.0):
    world = frame(origin, yaw)
    half_w, half_l, thick = 0.036, 0.075, 0.008
    desk_shadow(art, desk, world(slab(-half_w, half_w, -half_l, half_l, 0)), 0.02)
    top = world(slab(-half_w, half_w, -half_l, half_l, thick, 0.009))
    art.part(hull(top, world(slab(-half_w, half_w, -half_l, half_l, 0, 0.009))), "#3A3E4A", shade=False)
    art.part(seen(top), PALETTE["phone"], shade=False)
    glass = art.shape(seen(world(slab(-0.032, 0.032, -0.070, 0.070, thick, 0.006))))
    art.paint(glass, "#232838")
    card = art.shape(seen(world(slab(-0.027, 0.027, 0.012, 0.040, thick, 0.005))))
    art.paint(card, PALETTE["card"], 0.92)
    art.light(art.feather(card, 6), PALETTE["glow"], 0.35)
    lines = [seen(world(slab(-0.021, x1, y, y + 0.004, thick))) for x1, y in ((0.012, 0.030),
                                                                              (0.002, 0.021))]
    art.paint(art.shapes(lines), "#7A8499")
    art.paint(art.shape(seen(world(slab(-0.014, 0.014, -0.046, -0.038, thick, 0.003)))), "#59627A")
    art.focus_on(art.feather(glass, 3) * 0.8)


def draw_mouse(art, desk, origin=(0.245, 0.37), yaw=-12.0):
    world = frame(origin, yaw)
    outline = [(0.03 * np.cos(a), 0.052 * np.sin(a) + 0.006 * np.sin(a) ** 2, 0.0)
               for a in np.linspace(0, 2 * np.pi, 40, endpoint=False)]
    desk_shadow(art, desk, world(outline), 0.035)
    body = art.part(seen(world(outline)), PALETTE["mouse"])
    art.line(seen(world([(0, 0.05, 0), (0, 0.012, 0)])), "#6B7385", 1.2, "none")
    art.light(art.blob(seen(world([(-0.01, 0.02, 0)])[0]), 12) * body, "#FFFFFF", 0.3)


def draw_notebook(art, desk, origin=(0.42, 0.50), yaw=14.0):
    world = frame(origin, yaw)
    desk_shadow(art, desk, world(slab(-0.075, 0.075, -0.105, 0.105, 0)), 0.02)
    art.part(hull(world(slab(-0.075, 0.075, -0.105, 0.105, 0.014, 0.006)),
                  world(slab(-0.075, 0.075, -0.105, 0.105, 0, 0.006))), "#F3EEE2", shade=False)
    cover = art.part(seen(world(slab(-0.075, 0.075, -0.105, 0.105, 0.014, 0.006))), PALETTE["book"],
                     bulge=10)
    art.paint(art.shape(seen(world(slab(0.048, 0.056, -0.105, 0.105, 0.014)))) * cover, "#3A3140")
    pen = [seen(world([(x, -0.135 + x * 0.3, 0.004)])[0]) for x in (-0.09, 0.07)]
    scale = CAMERA.scale_at((*origin, 0))
    art.part(art.tube([(*pen[0], 0.008 * scale), (*pen[1], 0.008 * scale)]), PALETTE["pen"], bulge=3)


def draw_lamp(art, desk, origin=(-0.56, 0.58)):
    cx, cy = origin
    desk_shadow(art, desk, disc(cx, cy, 0.07, 0), 0.03)
    art.part(hull(disc(cx, cy, 0.07, 0), disc(cx, cy, 0.066, 0.014)), PALETTE["lamp"], bulge=6)
    joints = [(cx, cy, 0.014), (cx - 0.02, cy, 0.30), (LAMP_HEAD[0] - 0.02, LAMP_HEAD[1], LAMP_HEAD[2] + 0.07)]
    for a, b in zip(joints[:-1], joints[1:]):
        width = 0.014 * CAMERA.scale_at(a)
        art.part(art.tube([(*seen(a), width), (*seen(b), width)]), PALETTE["lamp"], bulge=3)
    hx, hy, hz = LAMP_HEAD
    opening = disc(hx, hy, 0.075, hz)
    shade = art.part(hull(opening, disc(hx - 0.01, hy, 0.03, hz + 0.08)), PALETTE["lamp"])
    art.paint(art.shape(seen(opening)), PALETTE["lamp_light"])
    art.light(art.feather(art.shape(seen(opening)), 14), PALETTE["lamp_light"], 0.9)
    pool = art.shape(seen(disc(hx + 0.06, hy - 0.10, 0.34, 0)))               # light on the desk
    art.light(art.feather(pool, 30) * desk, PALETTE["lamp_light"], 0.42)
    return shade


def draw_plant(art, desk, origin=(0.62, 0.62)):
    cx, cy = origin
    desk_shadow(art, desk, disc(cx, cy, 0.05, 0), 0.12)
    rim = seen((cx, cy, 0.11))
    scale = CAMERA.scale_at((cx, cy, 0.11))
    with art.place(at=rim, scale=scale):                     # leaves drawn in metres, upright
        back_leaves = ([(0, 0, True), (-0.11, -0.12), (-0.16, -0.27, True), (-0.05, -0.15)],
                       [(0, 0, True), (0.09, -0.10), (0.17, -0.22, True), (0.05, -0.13)])
        front_leaves = ([(0, 0, True), (-0.05, -0.16), (-0.02, -0.34, True), (0.03, -0.17)],
                        [(0, 0, True), (0.05, -0.13), (0.10, -0.29, True), (0.09, -0.13)],
                        [(0, 0, True), (-0.09, -0.07), (-0.19, -0.13, True), (-0.09, -0.03)])
        for points in back_leaves:
            art.part(spline(points, closed=True), PALETTE["leaf_dark"], bulge=0.02)
    art.part(hull(disc(cx, cy, 0.045, 0), disc(cx, cy, 0.062, 0.11)), PALETTE["pot"])
    art.paint(art.shape(seen(disc(cx, cy, 0.055, 0.11))), "#4A382B")
    with art.place(at=rim, scale=scale):
        for points in front_leaves:
            leaf = art.part(spline(points, closed=True), PALETTE["leaf"], bulge=0.02)
            art.line(spline([points[0][:2], points[1][:2], points[2][:2]]), PALETTE["leaf_dark"],
                     0.004, opacity=0.8)
            art.focus_on(leaf * 0.5)


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=12)
    desk = draw_room(art)
    draw_lamp(art, desk)                                     # back to front
    draw_plant(art, desk)
    draw_notebook(art, desk)
    draw_laptop(art, desk)
    draw_mouse(art, desk)
    draw_phone(art, desk)
    draw_mug(art, desk)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
