"""Desk still life: modern objects (laptop, monitor, keyboard, phone, mug, plant) on a desk.

Hard-surface objects are boxes and slabs in a small 3D scene measured in
centimetres (X right, Y up, Z away from the viewer), seen by a camera above
the desk looking down at it. Each box face is shaded by how far it turns
from the lamp, so flat objects get crisp light-and-shadow planes, which is
what makes them read as manufactured. Round things (mug, pot, leaves) reuse
the relief engine.

Screens are their own light sources: a screen shows a simple UI drawn in its
own perspective, and at night (or with the desk lamp off) it lights the
desk in front of it.
"""
import cv2
import numpy as np

import kit
import relief
from figure import Figure
from painter import Scene, run_hook
from raster import blur, ellipse, fill, fill_many, mask_box, mix, multiply, noise, over, rgb, screen, smooth, stroke, stroke_many, taper

UNIT_SHARE = 0.19
FOCUS = {"wall": 0.05, "desk": 0.3, "object": 0.65, "screen": 0.8}
NEAR_CLIP = 5.0
# Keyboard: rows of keys (count, starting offset in key widths), key pitch (cm), key cap inset (cm).
KEY_ROWS = ((13, 0.0), (13, 0.25), (12, 0.45), (11, 0.7), (1, 3.0))
KEY_PITCH, KEY_INSET = 1.95, 0.28
SPACE_KEYS = 6
# Screen UI: rows of "text" bars as (indent share, length share) and a block of colour.
UI_LINES = ((0.06, 0.55), (0.06, 0.38), (0.10, 0.62), (0.10, 0.48), (0.10, 0.70), (0.06, 0.30), (0.10, 0.52), (0.10, 0.44))


class Camera:
    """Pinhole camera above the desk, tilted down by `pitch_deg`."""

    def __init__(self, size, spec):
        height, width = size
        self.center = np.array([spec["center_x"] * width, spec["center_y"] * height])
        self.focal = spec["focal"] * width
        self.position = np.array(spec["position"], np.float64)
        pitch = np.deg2rad(spec["pitch_deg"])
        self.turn = np.array([[1, 0, 0], [0, np.cos(pitch), np.sin(pitch)], [0, -np.sin(pitch), np.cos(pitch)]])

    def view(self, points):
        pts = np.atleast_2d(np.asarray(points, np.float64)) - self.position
        return pts @ self.turn.T

    def project(self, points):
        pts = self.view(points)
        z = np.maximum(pts[:, 2], NEAR_CLIP)
        return np.column_stack([self.center[0] + self.focal * pts[:, 0] / z, self.center[1] - self.focal * pts[:, 1] / z])

    def depth(self, point):
        return float(self.view(point)[0, 2])

    def scale(self, point):
        """Pixels per centimetre at a point."""
        return self.focal / max(self.depth(point), NEAR_CLIP)


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light), seed=spec["seed"], spec=spec)
    fig.focus = np.full(fig.size, FOCUS["wall"], np.float32)
    return fig


def note_focus(scene, mask, level):
    scene.fig.focus = np.where(mask > 0.5, np.maximum(level, scene.fig.focus), scene.fig.focus).astype(np.float32)


# --------------------------------------------------------------- geometry
def rotate_y(points, center, angle_deg):
    """Turn points about a vertical axis through `center` (objects sit at an angle on the desk)."""
    turn = np.deg2rad(angle_deg)
    pts = np.asarray(points, np.float64) - center
    x = pts[..., 0] * np.cos(turn) + pts[..., 2] * np.sin(turn)
    z = -pts[..., 0] * np.sin(turn) + pts[..., 2] * np.cos(turn)
    return np.stack([x, pts[..., 1], z], axis=-1) + center


def box_faces(center, size, angle_deg=0.0):
    """The faces of an axis-aligned box as (corners, outward normal), before rotation about its centre."""
    cx, cy, cz = center
    sx, sy, sz = np.asarray(size) / 2.0
    corners = {
        "top": ([(-sx, sy, -sz), (sx, sy, -sz), (sx, sy, sz), (-sx, sy, sz)], (0, 1, 0)),
        "front": ([(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz)], (0, 0, -1)),
        "left": ([(-sx, -sy, sz), (-sx, -sy, -sz), (-sx, sy, -sz), (-sx, sy, sz)], (-1, 0, 0)),
        "right": ([(sx, -sy, -sz), (sx, -sy, sz), (sx, sy, sz), (sx, sy, -sz)], (1, 0, 0)),
        "back": ([(sx, -sy, sz), (-sx, -sy, sz), (-sx, sy, sz), (sx, sy, sz)], (0, 0, 1)),
    }
    origin = np.array([cx, cy, cz], np.float64)
    faces = {}
    for name, (points, normal) in corners.items():
        world = np.array(points, np.float64) + origin
        faces[name] = (rotate_y(world, origin, angle_deg), rotate_y(np.array(normal, np.float64), np.zeros(3), angle_deg))
    return faces


def facing_viewer(camera, corners, normal):
    """A face is drawn only if it turns toward the camera."""
    middle = np.mean(corners, axis=0)
    return float(np.dot(normal, camera.position - middle)) > 0


def plane_light(scene, normal):
    """Light on a flat face, 0..1, from the scene's lamp (y up in this scene, so flip the image-space y)."""
    lx, ly, lz = scene.fig.light
    lamp = np.array([lx, -ly, -lz])
    return float(np.clip(np.dot(normal, lamp / np.linalg.norm(lamp)), 0.0, 1.0))


def paint_face(scene, camera, corners, normal, group, extra_dark=0.0, ink=True):
    """Fill one flat face with the colour its angle to the lamp gives it. Returns its mask."""
    tones = scene.style["palette"][group]
    outline = camera.project(corners)
    mask = fill(scene.size, outline)
    lit = plane_light(scene, normal)
    shadow = np.clip(1.0 - lit * 1.25 + extra_dark, 0.0, 1.0)
    if scene.cel:
        shadow = float(shadow > 0.5) * 0.85
    elif scene.mode == "grain":
        shadow = np.clip(shadow, 0.0, 1.0)
    color = mix(rgb(tones["base"]), rgb(tones["shadow"]), shadow if scene.shade_on else 0.0)
    if scene.mode == "grain" and scene.shade_on:
        box = mask_box(mask)
        if box is not None:
            amount = scene.speckle(np.full(mask[box].shape, shadow, np.float32), box)
            tint = mix(rgb(tones["base"]), rgb(tones["shadow"]), amount[..., None])
            target = scene.image[box]
            target += (tint - target) * mask[box][..., None]
    else:
        over(scene.image, color, mask)
    if ink:
        scene.ink(np.vstack([outline, outline[:1]]), 1.6, group, "line", np.ones(len(outline) + 1), 0.9)
    return mask


def paint_box(scene, camera, center, size, group, angle_deg=0.0, skip=()):
    """A box: its visible faces, far to near. Returns {face name: mask}."""
    faces = box_faces(center, size, angle_deg)
    visible = [(name, corners, normal) for name, (corners, normal) in faces.items()
               if name not in skip and facing_viewer(camera, corners, normal)]
    visible.sort(key=lambda item: -camera.depth(np.mean(item[1], axis=0)))
    return {name: paint_face(scene, camera, corners, normal, group) for name, corners, normal in visible}


def cast_box_shadow(scene, camera, center, size, angle_deg, receiver, softness=0.02, opacity=0.5):
    """The shadow a box throws on the desk: its footprint slid away from the lamp, softened."""
    if not scene.shade_on:
        return
    lx, ly, lz = scene.fig.light
    reach = size[1] * 1.1 + 1.0
    shift_3d = np.array([-lx, 0.0, lz]) / max(np.hypot(lx, lz), 1e-6) * reach * 0.6
    cx, cy, cz = center
    sx, sz = size[0] / 2 + 0.6, size[2] / 2 + 0.6
    foot = np.array([(-sx, 0, -sz), (sx, 0, -sz), (sx, 0, sz), (-sx, 0, sz)], np.float64) + [cx, 0.01, cz]
    foot = rotate_y(foot, np.array([cx, 0, cz]), angle_deg)
    spread = np.vstack([foot, foot + shift_3d])
    hull = cv2.convexHull(camera.project(spread).astype(np.float32))[:, 0, :]
    shadow = scene.soften(fill(scene.size, hull), softness)
    multiply(scene.image, rgb(scene.style["palette"]["desk"]["cast"]), shadow * receiver, opacity)


# ------------------------------------------------------------ the setting
def paint_room(scene, camera):
    """Wall, window light falling on it, desk top and its front edge."""
    spec, tones = scene.fig.spec, scene.style["palette"]
    height, width = scene.size
    wall = tones["wall"]
    scene.image[:] = kit.vertical_gradient(scene.size, [(0.0, wall["top"]), (1.0, wall["bottom"])])
    if scene.shade_on:
        toward = np.sign(scene.fig.light[0])
        cols = np.arange(width, dtype=np.float32)[None, :]
        glow = np.clip(0.5 - toward * (cols / width - 0.5) * 1.6, 0, 1) * np.ones((height, 1), np.float32)
        screen(scene.image, rgb(wall["glow"]), glow ** 1.5, spec["room"]["window_glow"])
    desk = spec["desk"]
    corners = [(-desk["width"] / 2, 0, desk["front_z"]), (desk["width"] / 2, 0, desk["front_z"]),
               (desk["width"] / 2, 0, desk["back_z"]), (-desk["width"] / 2, 0, desk["back_z"])]
    top = fill(scene.size, camera.project(corners))
    rows = np.arange(height, dtype=np.float32)[:, None]
    near = np.clip((rows - top.any(axis=1).argmax()) / max(height - top.any(axis=1).argmax(), 1), 0, 1)
    color = mix(rgb(tones["desk"]["shadow"]), rgb(tones["desk"]["base"]), (near * 0.7 + 0.3)[..., None])
    over(scene.image, np.broadcast_to(color, scene.image.shape), top)
    if scene.shade_on:
        grain = noise(scene.size, width * 0.004, scene.fig.seed + 3, 2)
        stretched = cv2.resize(cv2.resize(grain, (width // 40, height)), (width, height), interpolation=cv2.INTER_CUBIC)
        multiply(scene.image, rgb(tones["desk"]["shadow"]), np.clip(stretched * 2.2 - 1.2, 0, 1) * top, spec["desk"]["grain"])
    front = fill(scene.size, camera.project([(-desk["width"] / 2, 0, desk["front_z"]), (desk["width"] / 2, 0, desk["front_z"]),
                                             (desk["width"] / 2, -desk["thickness"], desk["front_z"]),
                                             (-desk["width"] / 2, -desk["thickness"], desk["front_z"])]))
    over(scene.image, rgb(tones["desk"]["deep"]), front)
    note_focus(scene, top, FOCUS["desk"])
    return top


# ---------------------------------------------------------------- objects
def screen_ui(scene, camera, corners, tones, on):
    """Draw a simple app on a screen given by its 4 corners (bottom-left, bottom-right, top-right, top-left)."""
    outline = camera.project(corners)
    mask = fill(scene.size, outline)
    if not on:
        over(scene.image, rgb(tones["off"]), mask)
        return mask
    over(scene.image, rgb(tones["background"]), mask)
    bl, br, tr, tl = (np.asarray(point, np.float64) for point in corners)

    def at(u, v):
        """A point on the screen: u from left to right, v from bottom to top (0..1)."""
        bottom = bl + (br - bl) * u
        top = tl + (tr - tl) * u
        return bottom + (top - bottom) * v

    def quad(u0, v0, u1, v1):
        return camera.project([at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1)])

    over(scene.image, rgb(tones["bar"]), fill(scene.size, quad(0.0, 0.92, 1.0, 1.0)))
    over(scene.image, rgb(tones["side"]), fill(scene.size, quad(0.0, 0.0, 0.22, 0.92)))
    bars = [quad(0.03, 0.80 - k * 0.09, 0.19, 0.84 - k * 0.09) for k in range(6)]
    over(scene.image, rgb(tones["side_text"]), fill_many(scene.size, bars), 0.8)
    over(scene.image, rgb(tones["accent"]), fill(scene.size, quad(0.27, 0.52, 0.62, 0.86)))
    over(scene.image, rgb(tones["accent2"]), fill(scene.size, quad(0.66, 0.52, 0.96, 0.86)))
    lines = []
    for k, (indent, length) in enumerate(UI_LINES[:5]):
        v = 0.44 - k * 0.075
        lines.append(quad(0.27 + indent * 0.6, v, 0.27 + (indent + length) * 0.69, v + 0.03))
    over(scene.image, rgb(tones["text"]), fill_many(scene.size, lines), 0.75)
    if scene.shade_on:
        # A soft reflection of the room across the glass.
        glare = fill(scene.size, quad(0.55, 0.0, 1.0, 1.0)) * mask
        screen(scene.image, rgb("#FFFFFF"), blur(glare, scene.size[1] * 0.03) * mask, 0.08)
    return mask


def paint_monitor(scene, camera, item, receiver):
    """External monitor: thin panel on a stand with a flat foot."""
    tones = scene.style["palette"]
    x, z, angle = item["x"], item["z"], item.get("angle", 0.0)
    width, height = item["width"], item["height"]
    lift, foot = item.get("lift", 10.0), item.get("foot", 22.0)
    cast_box_shadow(scene, camera, (x, 1.0, z + 2), (foot, 1.5, foot * 0.6), angle, receiver, opacity=0.45)
    panel_center = (x, lift + height / 2, z)
    shadow_box = (width, height + lift, 4.0)
    cast_box_shadow(scene, camera, (x, (lift + height) / 2, z), shadow_box, angle, receiver, 0.05, 0.25)
    paint_box(scene, camera, (x, 0.6, z + 3), (foot, 1.2, foot * 0.55), "device", angle)
    paint_box(scene, camera, (x, lift / 2 + 1, z + 3.5), (5.0, lift + 2, 2.0), "device", angle)
    faces = paint_box(scene, camera, panel_center, (width, height, 1.6), "device", angle)
    bezel = 0.9
    corners = rotate_y(np.array([(x - width / 2 + bezel, lift + bezel + 1.4, z - 0.81), (x + width / 2 - bezel, lift + bezel + 1.4, z - 0.81),
                                 (x + width / 2 - bezel, lift + height - bezel, z - 0.81), (x - width / 2 + bezel, lift + height - bezel, z - 0.81)]),
                       np.array(panel_center), angle)
    on = item.get("on", True)
    glass = screen_ui(scene, camera, corners, tones["screen"], on)
    if on:
        scene.lights.append((glass, rgb(tones["screen"]["glow"])))
    mask = np.maximum.reduce(list(faces.values()) + [glass])
    note_focus(scene, mask, FOCUS["screen"])
    kit.register(scene, f"monitor_{int(x)}", mask)


def paint_laptop(scene, camera, item, receiver):
    """Laptop: a thin base with a keyboard and trackpad, and a lid opened back to `open_deg`."""
    tones = scene.style["palette"]
    x, z, angle = item["x"], item["z"], item.get("angle", 0.0)
    width, depth = item["width"], item["depth"]
    hinge_z = z + depth / 2
    cast_box_shadow(scene, camera, (x, 1.0, z), (width, 2.0, depth), angle, receiver, opacity=0.5)
    base = paint_box(scene, camera, (x, 0.75, z), (width, 1.5, depth), "device", angle)
    deck = rotate_y(np.array([(x - width / 2 + 1.0, 1.51, z - depth / 2 + 7.5), (x + width / 2 - 1.0, 1.51, z - depth / 2 + 7.5),
                              (x + width / 2 - 1.0, 1.51, hinge_z - 1.2), (x - width / 2 + 1.0, 1.51, hinge_z - 1.2)]), np.array([x, 0, z]), angle)
    paint_keys(scene, camera, deck, item.get("keys", True))
    pad = rotate_y(np.array([(x - 5.5, 1.52, z - depth / 2 + 1.2), (x + 5.5, 1.52, z - depth / 2 + 1.2), (x + 5.5, 1.52, z - depth / 2 + 6.8),
                             (x - 5.5, 1.52, z - depth / 2 + 6.8)]), np.array([x, 0, z]), angle)
    over(scene.image, rgb(tones["device"]["shadow"]), fill(scene.size, camera.project(pad)), 0.35)
    tilt = np.deg2rad(item.get("open_deg", 108.0))
    up = np.array([0.0, np.sin(tilt), -np.cos(tilt)])
    lid_height = depth * 0.95
    hinge_l, hinge_r = np.array([x - width / 2, 1.5, hinge_z]), np.array([x + width / 2, 1.5, hinge_z])
    lid = rotate_y(np.array([hinge_l, hinge_r, hinge_r + up * lid_height, hinge_l + up * lid_height]), np.array([x, 0, z]), angle)
    normal_front = rotate_y(np.array([0.0, np.cos(tilt - np.pi / 2), -np.sin(tilt - np.pi / 2)]), np.zeros(3), angle)
    shell = paint_face(scene, camera, lid, -normal_front if not facing_viewer(camera, lid, normal_front) else normal_front, "device")
    inset = 0.9
    span = lid[1] - lid[0]
    rise = lid[3] - lid[0]
    glass_corners = [lid[0] + span * (inset / width) + rise * 0.06, lid[1] - span * (inset / width) + rise * 0.06,
                     lid[2] - span * (inset / width) - rise * 0.04, lid[3] + span * (inset / width) - rise * 0.04]
    glass_corners = [point - normal_front * 0.05 for point in glass_corners]
    on = item.get("on", True)
    glass = screen_ui(scene, camera, glass_corners, tones["screen"], on)
    if on:
        scene.lights.append((glass, rgb(tones["screen"]["glow"])))
    mask = np.maximum.reduce(list(base.values()) + [shell, glass])
    note_focus(scene, mask, FOCUS["screen"])
    kit.register(scene, f"laptop_{int(x)}", mask)


def paint_keys(scene, camera, deck, show):
    """Rows of key caps inside a rectangle given by 4 corners (front-left, front-right, back-right, back-left)."""
    if not show:
        return
    fl, fr, br, bl = (np.asarray(point, np.float64) for point in deck)
    across = (fr - fl) / np.linalg.norm(fr - fl)
    along = (bl - fl) / np.linalg.norm(bl - fl)
    pitch = min(np.linalg.norm(fr - fl) / 13.5, np.linalg.norm(bl - fl) / 5.4)
    keys, rows_total = [], len(KEY_ROWS)
    for row, (count, offset) in enumerate(KEY_ROWS):
        depth = (rows_total - 1 - row) * pitch + pitch * 0.2
        if count == 1:
            start = fl + across * pitch * (offset + 0.2) + along * depth
            keys.append(np.array([start, start + across * pitch * SPACE_KEYS, start + across * pitch * SPACE_KEYS + along * pitch * 0.82,
                                  start + along * pitch * 0.82]))
            continue
        for k in range(count):
            start = fl + across * pitch * (k + offset + 0.2) + along * depth
            inset = KEY_INSET / KEY_PITCH * pitch
            keys.append(np.array([start + across * inset * 0.3, start + across * (pitch - inset), start + across * (pitch - inset) + along * (pitch - inset),
                                  start + across * inset * 0.3 + along * (pitch - inset)]))
    tones = scene.style["palette"]["keys"]
    caps = fill_many(scene.size, [camera.project(key + [0, 0.15, 0]) for key in keys])
    over(scene.image, rgb(tones["base"]), caps)
    if scene.shade_on:
        lips = fill_many(scene.size, [camera.project(key[:2].tolist() + (key[:2][::-1] + [0, 0.15, 0]).tolist()) for key in keys])
        over(scene.image, rgb(tones["shadow"]), lips * (1 - caps), 0.8)


def paint_keyboard(scene, camera, item, receiver):
    """Stand-alone keyboard: a low slab with key caps."""
    x, z, angle = item["x"], item["z"], item.get("angle", 0.0)
    width, depth = item["width"], item["depth"]
    cast_box_shadow(scene, camera, (x, 1.0, z), (width, 2.0, depth), angle, receiver, opacity=0.4)
    faces = paint_box(scene, camera, (x, 0.9, z), (width, 1.8, depth), "device", angle)
    deck = rotate_y(np.array([(x - width / 2 + 0.8, 1.81, z - depth / 2 + 0.8), (x + width / 2 - 0.8, 1.81, z - depth / 2 + 0.8),
                              (x + width / 2 - 0.8, 1.81, z + depth / 2 - 0.8), (x - width / 2 + 0.8, 1.81, z + depth / 2 - 0.8)]),
                    np.array([x, 0, z]), angle)
    paint_keys(scene, camera, deck, True)
    note_focus(scene, np.maximum.reduce(list(faces.values())), FOCUS["object"])


def paint_phone(scene, camera, item, receiver):
    """Phone lying face up: a thin slab with a dark glass face and a camera bump."""
    tones = scene.style["palette"]
    x, z, angle = item["x"], item["z"], item.get("angle", 0.0)
    width, depth = item["width"], item["depth"]
    cast_box_shadow(scene, camera, (x, 0.5, z), (width, 0.9, depth), angle, receiver, 0.01, 0.45)
    faces = paint_box(scene, camera, (x, 0.45, z), (width, 0.9, depth), "phone", angle)
    glass = rotate_y(np.array([(x - width / 2 + 0.3, 0.91, z - depth / 2 + 0.3), (x + width / 2 - 0.3, 0.91, z - depth / 2 + 0.3),
                               (x + width / 2 - 0.3, 0.91, z + depth / 2 - 0.3), (x - width / 2 + 0.3, 0.91, z + depth / 2 - 0.3)]),
                     np.array([x, 0, z]), angle)
    on = item.get("on", False)
    face_mask = fill(scene.size, camera.project(glass))
    over(scene.image, rgb(tones["screen"]["background"] if on else tones["screen"]["off"]), face_mask)
    if scene.shade_on:
        streak = blur(fill(scene.size, camera.project([glass[0] * 0.5 + glass[1] * 0.5, glass[1], glass[2] * 0.6 + glass[1] * 0.4,
                                                       glass[3] * 0.3 + glass[2] * 0.7])), 2.0) * face_mask
        screen(scene.image, rgb("#FFFFFF"), streak, 0.22)
    if on:
        scene.lights.append((face_mask, rgb(tones["screen"]["glow"])))
    note_focus(scene, np.maximum.reduce(list(faces.values())), FOCUS["object"])


def paint_mouse(scene, camera, item, receiver):
    """Mouse: a low egg seen from above."""
    x, z = item["x"], item["z"]
    center = camera.project([(x, 1.8, z)])[0]
    scale = camera.scale((x, 1.8, z))
    foot = camera.project([(x, 0, z - 5.0), (x, 0, z + 5.0)])
    radius_y = abs(foot[1][1] - foot[0][1]) / 2
    toward = -np.sign(scene.fig.light[0])
    kit.ground_shadow(scene, center + [toward * 1.6 * scale, radius_y * 0.45], 3.6 * scale, radius_y * 1.15,
                      scene.style["palette"]["desk"]["cast"], 0.45, 0.012, receiver)
    body = relief.ellipsoid(scene.size, center + [0, radius_y * 0.2], 3.1 * scale, radius_y * 1.1, depth=3.0 * scale)
    kit.shade_solid(scene, body, "device", level=0.35, spread=0.5, gloss=0.4, shininess=30)
    kit.ink_edges(scene, body.mask, 1.6, "device", "line")
    seam = smooth([center + [0, -radius_y * 0.9], center + [0, -radius_y * 0.2]])
    over(scene.image, rgb(scene.style["palette"]["device"]["line"]), stroke(scene.size, seam, 1.2) * body.mask, 0.6)
    note_focus(scene, body.mask, FOCUS["object"])


def paint_mug(scene, camera, item, receiver):
    """Mug: a cylinder with a handle, coffee inside, and a curl of steam."""
    tones = scene.style["palette"]
    x, z = item["x"], item["z"]
    radius, tall = item["radius"], item["height"]
    scale = camera.scale((x, tall / 2, z))
    base_px = camera.project([(x, 0, z)])[0]
    top_px = camera.project([(x, tall, z)])[0]
    rim_px = camera.project([(x, tall, z - radius)])[0]
    tilt = max((rim_px[1] - top_px[1]) / (radius * scale), 0.05)
    cast_box_shadow(scene, camera, (x, tall / 2, z), (radius * 2, tall, radius * 2), 0.0, receiver, 0.03, 0.5)
    side = np.sign(-scene.fig.light[0]) or 1.0
    handle_path = smooth([top_px + [side * radius * scale * 0.85, (base_px[1] - top_px[1]) * 0.18],
                          top_px + [side * radius * scale * 1.55, (base_px[1] - top_px[1]) * 0.42],
                          top_px + [side * radius * scale * 0.90, (base_px[1] - top_px[1]) * 0.72]])
    handle = relief.tube(scene.size, handle_path, radius * scale * 0.16, roundness=0.9)
    kit.shade_solid(scene, handle, "mug", level=0.35, spread=0.5, gloss=0.35, shininess=30)
    kit.ink_edges(scene, handle.mask, 1.8, "mug", "line")
    body = relief.lathe(scene.size, top_px[0], top_px[1], base_px[1], np.full(6, radius * scale), tilt=tilt)
    mask = kit.shade_solid(scene, body, "mug", level=0.35, spread=0.6, gloss=0.4, shininess=36)
    opening = fill(scene.size, ellipse(top_px, radius * scale, radius * scale * tilt, 48))
    over(scene.image, rgb(tones["mug"]["shadow"]), opening)
    coffee = fill(scene.size, ellipse(top_px + [0, radius * scale * tilt * 0.25], radius * scale * 0.86, radius * scale * tilt * 0.80, 48))
    over(scene.image, rgb(tones["coffee"]["base"]), coffee * opening)
    if scene.shade_on:
        shine = fill(scene.size, ellipse(top_px + [-radius * scale * 0.35, 0], radius * scale * 0.18, radius * scale * tilt * 0.12))
        screen(scene.image, rgb("#FFFFFF"), blur(shine, 1.2) * coffee, 0.5)
    kit.ink_edges(scene, np.maximum(mask, opening), 2.0, "mug", "line")
    kit.ink_edges(scene, opening, 1.4, "mug", "line")
    if item.get("steam", True) and scene.shade_on:
        wisps = []
        for k in range(3):
            start = top_px + [(k - 1) * radius * scale * 0.35, -radius * scale * tilt * 0.4]
            points = [start + [np.sin(t * 2.2 + k) * radius * scale * 0.35, -t * radius * scale * 2.2] for t in np.linspace(0, 1, 6)]
            path = smooth(points)
            wisps.append((path, radius * scale * 0.10 * taper(len(path), 0.2, 0.0, 0.3)))
        screen(scene.image, rgb("#FFFFFF"), blur(stroke_many(scene.size, wisps), radius * scale * 0.08), 0.35)
    note_focus(scene, np.maximum(mask, handle.mask), FOCUS["object"])
    kit.register(scene, f"mug_{int(x)}", np.maximum(mask, handle.mask))


def paint_plant(scene, camera, item, receiver):
    """Potted plant: a tapered pot and a fan of long leaves."""
    tones = scene.style["palette"]
    x, z = item["x"], item["z"]
    radius, tall = item["radius"], item["height"]
    scale = camera.scale((x, tall / 2, z))
    base_px = camera.project([(x, 0, z)])[0]
    top_px = camera.project([(x, tall, z)])[0]
    rim_px = camera.project([(x, tall, z - radius)])[0]
    tilt = max((rim_px[1] - top_px[1]) / (radius * scale), 0.05)
    cast_box_shadow(scene, camera, (x, tall / 2, z), (radius * 2, tall * 2.5, radius * 2), 0.0, receiver, 0.05, 0.40)
    rng = np.random.default_rng(scene.fig.seed + 43)
    leaves = []
    for k in range(item.get("leaves", 9)):
        lean = rng.uniform(-75, 75)
        reach = rng.uniform(1.6, 3.0) * radius * scale
        turn = np.deg2rad(lean)
        root = top_px + [rng.uniform(-0.3, 0.3) * radius * scale, 0]
        tip = root + reach * np.array([np.sin(turn), -np.cos(turn)])
        middle = (root + tip) / 2 + np.array([np.cos(turn), np.sin(turn)]) * reach * rng.uniform(-0.15, 0.15) + [0, reach * 0.12]
        path = smooth([root, middle, tip])
        leaves.append((path, radius * scale * rng.uniform(0.22, 0.32) * taper(len(path), 0.25, 0.0, 0.35), lean))
    for path, widths, lean in sorted(leaves, key=lambda leaf: abs(leaf[2])):
        part = relief.tube(scene.size, path, widths, roundness=0.35)
        kit.shade_solid(scene, part, "leaf", level=0.45, spread=0.5, gloss=0.25, shininess=20)
        over(scene.image, rgb(tones["leaf"]["shadow"]), stroke(scene.size, path, np.maximum(widths * 0.08, 0.8)) * part.mask, 0.6)
        kit.ink_edges(scene, part.mask, 1.4, "leaf", "line")
    profile = radius * scale * np.linspace(1.0, 0.78, 6)
    pot = relief.lathe(scene.size, top_px[0], top_px[1], base_px[1], profile, tilt=tilt)
    mask = kit.shade_solid(scene, pot, "pot", level=0.40, spread=0.55)
    rim = relief.lathe(scene.size, top_px[0], top_px[1] - radius * scale * 0.05, top_px[1] + radius * scale * 0.18,
                       np.full(4, radius * scale * 1.04))
    kit.shade_solid(scene, rim, "pot", level=0.40, spread=0.55)
    kit.ink_edges(scene, np.maximum(mask, rim.mask), 1.8, "pot", "line")
    note_focus(scene, mask, FOCUS["object"])


def paint_lamp(scene, camera, item, receiver):
    """Desk lamp: weighted base, two-part arm, shade; lights a pool on the desk when on."""
    tones = scene.style["palette"]
    x, z = item["x"], item["z"]
    base_px = camera.project([(x, 1.0, z)])[0]
    scale = camera.scale((x, 0, z))
    elbow = camera.project([(x + item["reach"] * 0.35, item["height"] * 0.65, z + 4)])[0]
    head = camera.project([(x + item["reach"], item["height"], z - 2)])[0]
    cast_box_shadow(scene, camera, (x, 1.0, z), (12, 2, 12), 0.0, receiver, 0.03, 0.4)
    foot = relief.lathe(scene.size, base_px[0], base_px[1] - 1.8 * scale, base_px[1] + 0.5 * scale, np.full(4, 6.0 * scale), tilt=0.35)
    kit.shade_solid(scene, foot, "lamp", level=0.35, spread=0.5, gloss=0.5, shininess=40)
    for start, end in ((base_px - [0, 1.5 * scale], elbow), (elbow, head)):
        arm = relief.tube(scene.size, np.linspace(start, end, 4), 0.55 * scale, roundness=0.9)
        kit.shade_solid(scene, arm, "lamp", level=0.35, spread=0.5, gloss=0.5, shininess=40)
        kit.ink_edges(scene, arm.mask, 1.4, "lamp", "line")
    shade_path = np.array([head + [-0.5 * scale, -2.0 * scale], head + [4.5 * scale, 3.5 * scale]])
    shade = relief.tube(scene.size, shade_path, np.array([2.2, 5.0]) * scale, roundness=0.8)
    kit.shade_solid(scene, shade, "lamp", level=0.38, spread=0.5, gloss=0.5, shininess=40)
    kit.ink_edges(scene, np.maximum(shade.mask, foot.mask), 1.6, "lamp", "line")
    if item.get("on", True):
        mouth = fill(scene.size, ellipse(head + [4.5 * scale, 4.6 * scale], 4.2 * scale, 1.6 * scale, 32, -32))
        over(scene.image, rgb(tones["lamp"]["bulb"]), mouth * shade.mask, 0.95)
        target = (x + item["reach"] + 6, 0, z - 10)
        pool = fill(scene.size, camera.project([(target[0] + 22 * np.cos(t), 0, target[2] + 18 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 40)]))
        scene.pools.append((blur(pool, scene.size[1] * 0.03) * receiver, rgb(tones["lamp"]["bulb"])))
        scene.lights.append((mouth * shade.mask, rgb(tones["lamp"]["bulb"])))


def paint_notebook(scene, camera, item, receiver):
    """Paper notebook with a pen lying across it."""
    tones = scene.style["palette"]
    x, z, angle = item["x"], item["z"], item.get("angle", 0.0)
    cast_box_shadow(scene, camera, (x, 0.5, z), (item["width"], 1.0, item["depth"]), angle, receiver, 0.01, 0.35)
    paint_box(scene, camera, (x, 0.5, z), (item["width"], 1.0, item["depth"]), "paper", angle)
    lines = []
    for k in range(1, 10):
        v = z - item["depth"] / 2 + k * item["depth"] / 10
        ends = rotate_y(np.array([(x - item["width"] / 2 + 1.5, 1.01, v), (x + item["width"] / 2 - 1.0, 1.01, v)]), np.array([x, 0, z]), angle)
        lines.append((camera.project(ends), 0.8))
    over(scene.image, rgb(tones["paper"]["rule"]), stroke_many(scene.size, lines), 0.55)
    pen = rotate_y(np.array([(x - item["width"] * 0.35, 1.6, z + 2), (x + item["width"] * 0.45, 1.6, z - 4)]), np.array([x, 0, z]), angle)
    path = camera.project(pen)
    body = relief.tube(scene.size, np.linspace(path[0], path[1], 4), 0.45 * camera.scale(pen[0]), roundness=0.9)
    kit.shade_solid(scene, body, "pen", level=0.35, spread=0.5, gloss=0.6, shininess=50)


PAINTERS = {"monitor": paint_monitor, "laptop": paint_laptop, "keyboard": paint_keyboard, "phone": paint_phone,
            "mouse": paint_mouse, "mug": paint_mug, "plant": paint_plant, "lamp": paint_lamp, "notebook": paint_notebook}


def light_up(scene, top):
    """Screens and the lamp light the desk; then every light source gets a soft bloom."""
    if not scene.shade_on:
        return
    width = scene.size[1]
    for mask, color in scene.pools:
        screen(scene.image, color, mask, 0.35)
    for mask, color in scene.lights:
        spill = blur(mask, width * 0.05) * top * (1 - mask)
        screen(scene.image, color, spill, scene.fig.spec["room"]["screen_spill"])
        screen(scene.image, color, blur(mask, width * 0.008), 0.25)


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    scene.lights, scene.pools = [], []
    camera = Camera(fig.size, fig.spec["camera"])
    top = paint_room(scene, camera)
    run_hook(extras, "after_background", scene)
    items = sorted(fig.spec["objects"], key=lambda item: -camera.depth((item["x"], 0, item["z"])))
    for item in items:
        PAINTERS[item["kind"]](scene, camera, item, top)
    light_up(scene, top)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
