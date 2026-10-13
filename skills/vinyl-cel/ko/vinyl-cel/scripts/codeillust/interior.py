"""Indoor rooms for 3D scenes: a living room, an office and a cafe.

A room is a stage set: a floor, a ceiling, a back wall and two side walls, open toward the camera.
The shell is drawn as flat painted surfaces (planks, paint, windows with a view, sunlight on the
floor) projected by the same SceneCamera as the furniture and figures, so the perspective of the
walls, the furniture and the people agrees. Furniture and objects come from furniture3d and
props3d and are drawn into one depth buffer with any figures added to the scene.

    room = interior.living_room()
    gamer = scene3d.seated(Figure3D(..., pose=rig3d.SIT_GAME, props=(props3d.held_controller(),)),
                           room.places["sofa"], "seat_1")
    interior.draw_room(painter, camera, room, [gamer])

World units are head heights (props3d.cm converts), the floor is y = 0 and y points down.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from . import furniture3d, props3d
from .config import rgb
from .props3d import cm
from .scene3d import Placed, draw_scene3d, on_top

TEXELS_PER_HEAD = 48            # texture density of walls and floors
NEAR_CLIP = 0.6                 # head heights in front of the eye where surfaces are cut off
INSET = 0.02                    # head heights a wall decoration stands off its wall (drawn after it anyway)
CORNER_SHADOW = 1.2             # head heights over which the floor darkens toward a wall
CORNER_SHADOW_OPACITY = 0.28
SUNLIGHT = (0.30, 0.92, 0.85)   # direction sunlight travels through a back-wall window (x, y down, z into the room)
SUN_PATCH_OPACITY = 0.30
ROOM_FRONT = 40.0              # z where the side walls end: past any camera inside the room, so they reach the frame edge


@dataclass
class Surface:
    """A flat painted quad. corners: four world points in texture order (top-left, top-right,
    bottom-right, bottom-left of the texture). texture: HxWx3 RGB, or HxWx4 with alpha, floats 0..1."""

    corners: tuple
    texture: np.ndarray
    facing: tuple = None        # world direction its painted side faces; it is skipped when the eye is behind it


@dataclass
class Room:
    surfaces: list                                   # drawn in order, back to front
    items: list                                      # scene3d.Placed furniture and objects
    places: dict = field(default_factory=dict)       # name -> Placed, for seating figures and adding objects
    size: tuple = (0.0, 0.0, 0.0, 0.0, 0.0)          # x left, x right, z back, z front, height


def draw_room(painter, camera, room, items=()):
    """Paint the shell, then draw the furniture, objects and figures in one depth buffer.
    Returns what draw_scene3d returns."""
    for surface in room.surfaces:
        draw_surface(painter.canvas, camera, surface)
    result = draw_scene3d(painter, camera, list(room.items) + list(items))
    painter.canvas.shade_subject_as_one = False
    return result


# ---- projecting a flat surface ----------------------------------------------------------------------------
def draw_surface(canvas, camera, surface):
    """Warp the surface texture onto its projected quad, cut at the near plane. A wall the eye stands
    behind is left out, as a stage set opens the side the camera looks in from. Returns the canvas mask
    the surface covers (None when nothing was drawn)."""
    eye = camera.eye()
    if surface.facing is not None and eye is not None:
        if float((eye - np.asarray(surface.corners[0])) @ np.asarray(surface.facing)) <= 0:
            return
    texture = np.asarray(surface.texture, dtype=np.float32)
    height, width = texture.shape[:2]
    uv = np.array([[0.0, 0.0], [width, 0.0], [width, height], [0.0, height]])
    view = camera.for_object().to_view(np.asarray(surface.corners, dtype=np.float64))
    limit = np.inf if camera.distance is None else camera.distance - NEAR_CLIP
    view, uv = _clip_near(view, uv, limit)
    if len(view) < 3:
        return
    grow = np.ones(len(view)) if camera.distance is None else camera.distance / (camera.distance - view[:, 2])
    points = (np.asarray(camera.origin) + view[:, :2] * grow[:, None] * camera.scale) * canvas.px_per_unit
    if len(points) == 3:                       # a homography needs four points: add the centroid
        points = np.vstack([points, points.mean(axis=0)])
        uv = np.vstack([uv, uv.mean(axis=0)])
    matrix, _ = cv2.findHomography(uv.astype(np.float32), points.astype(np.float32), 0)
    if matrix is None:
        return
    mask = canvas.mask(points[: len(view)] / canvas.px_per_unit)
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    if rows.size == 0:
        return
    top, bottom, left, right = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    shift = np.array([[1, 0, -left], [0, 1, -top], [0, 0, 1]], dtype=np.float64)
    warped = cv2.warpPerspective(texture, shift @ matrix, (int(right - left), int(bottom - top)),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    alpha = mask[top:bottom, left:right]
    if warped.ndim == 3 and warped.shape[2] == 4:
        alpha = alpha * warped[..., 3]
        warped = warped[..., :3]
    region = canvas.rgb[top:bottom, left:right]
    canvas.rgb[top:bottom, left:right] = region * (1 - alpha[..., None]) + warped * alpha[..., None]
    return mask


def keep_detail(canvas, mask, detail):
    """Ask painterly finishing for finer brushes where mask covers (rows of windows, a view through a
    window): detail 0..1 as Prop3D.detail."""
    if mask is None:
        return
    wanted = (mask * detail).astype(np.float32)
    canvas.importance = wanted if canvas.importance is None else np.maximum(canvas.importance, wanted)


def _clip_near(view, uv, limit):
    """Sutherland-Hodgman clip of a polygon to view z <= limit, carrying texture coordinates along."""
    if not np.isfinite(limit):
        return view, uv
    out_view, out_uv = [], []
    count = len(view)
    for index in range(count):
        a, b = view[index], view[(index + 1) % count]
        ua, ub = uv[index], uv[(index + 1) % count]
        a_in, b_in = a[2] <= limit, b[2] <= limit
        if a_in:
            out_view.append(a)
            out_uv.append(ua)
        if a_in != b_in:
            t = (limit - a[2]) / (b[2] - a[2])
            out_view.append(a + (b - a) * t)
            out_uv.append(ua + (ub - ua) * t)
    return np.array(out_view), np.array(out_uv)


# ---- textures -----------------------------------------------------------------------------------------------
def _size(length):
    return max(4, int(round(length * TEXELS_PER_HEAD)))


def paint(width, height, color, rng, top_light=1.05, bottom_shade=0.90, mottle=0.025):
    """Painted plaster: lighter near the ceiling, a little darker near the floor, faint unevenness."""
    w, h = _size(width), _size(height)
    ramp = np.linspace(top_light, bottom_shade, h, dtype=np.float32)[:, None, None]
    noise = cv2.resize(rng.random((max(2, h // 40), max(2, w // 40))).astype(np.float32), (w, h),
                       interpolation=cv2.INTER_CUBIC)[..., None]
    return np.clip(np.asarray(color, dtype=np.float32) * ramp * (1 + (noise - 0.5) * mottle), 0, 1)


def planks(width, depth, colors, rng, plank=cm(16.0), seam=rgb("#3A2618")):
    """Wooden floorboards running along the texture's width, with staggered joints and grain."""
    w, h = _size(width), _size(depth)
    image = np.zeros((h, w, 3), dtype=np.float32)
    row_px = max(3, int(plank * TEXELS_PER_HEAD))
    for top in range(0, h, row_px):
        x = -int(rng.uniform(0, 1) * row_px * 6)
        while x < w:
            length = int(rng.uniform(5.0, 11.0) * row_px)
            tone = colors[int(rng.integers(len(colors)))] * rng.uniform(0.94, 1.06)
            image[top:top + row_px, max(x, 0):max(x + length, 0)] = tone
            if x > 0:
                image[top:top + row_px, x:x + 1] = seam
            x += length
        image[top:top + 1] = seam
    grain = cv2.resize(rng.random((h, max(2, w // 24))).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(image * (0.94 + 0.12 * grain[..., None]), 0, 1)


def carpet_tiles(width, depth, color, rng, tile=cm(50.0)):
    w, h = _size(width), _size(depth)
    tile_px = max(2, int(tile * TEXELS_PER_HEAD))
    ys, xs = np.mgrid[0:h, 0:w]
    checker = ((ys // tile_px + xs // tile_px) % 2).astype(np.float32)
    speckle = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    shade = 1.0 + checker[..., None] * 0.035 + cv2.GaussianBlur(speckle, (0, 0), 0.8)[..., None] * 0.03
    image = np.asarray(color, dtype=np.float32) * shade
    image[(ys % tile_px == 0) | (xs % tile_px == 0)] *= 0.93
    return np.clip(image, 0, 1)


def bricks(width, height, color, rng, mortar=rgb("#D8CFC2"), brick=(cm(24.0), cm(7.0))):
    w, h = _size(width), _size(height)
    bw, bh = max(4, int(brick[0] * TEXELS_PER_HEAD)), max(3, int(brick[1] * TEXELS_PER_HEAD))
    image = np.empty((h, w, 3), dtype=np.float32)
    image[:] = mortar
    for row, top in enumerate(range(0, h, bh)):
        offset = (bw // 2) * (row % 2)
        for left in range(-offset, w, bw):
            tone = np.asarray(color) * rng.uniform(0.86, 1.10)
            image[top + 1:top + bh - 1, max(left + 1, 0):max(left + bw - 1, 0)] = tone
    return np.clip(image, 0, 1)


def _rect(image, x0, y0, x1, y1, color):
    h, w = image.shape[:2]
    image[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w), :3] = color


NIGHT_BLOCK = rgb("#2A313B")
NIGHT_WINDOWS = (rgb("#F3C47E"), rgb("#E9A962"), rgb("#8FB3CF"))
NIGHT_LIT_SHARE = 0.25


def panel_night_view(width, height, rng):
    """Night out of a flat's window: the panel block across the courtyard, a few windows lit, a lamp below."""
    w, h = _size(width), _size(height)
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    image = np.broadcast_to(rgb("#121A26") * (1 - t) + rgb("#2C3644") * t, (h, w, 3)).astype(np.float32).copy()
    top, bottom = int(0.18 * h), int(0.92 * h)
    image[top:bottom] = NIGHT_BLOCK
    rows, cols = 9, max(4, int(w / (0.11 * h)))
    cell_w, cell_h = w / cols, (bottom - top) / rows
    for row in range(rows):
        for col in range(cols):
            x0, y0 = int((col + 0.28) * cell_w), int(top + (row + 0.25) * cell_h)
            x1, y1 = int((col + 0.72) * cell_w), int(top + (row + 0.75) * cell_h)
            lit = rng.random() < NIGHT_LIT_SHARE
            color = NIGHT_WINDOWS[rng.integers(len(NIGHT_WINDOWS))] * rng.uniform(0.75, 1.0) if lit else \
                NIGHT_BLOCK * rng.uniform(0.55, 0.75)
            image[y0:y1, x0:x1] = color
    image[bottom:] = rgb("#3A4250")
    lamp = (int(rng.uniform(0.2, 0.8) * w), int(0.86 * h))
    glow = np.zeros((h, w), dtype=np.float32)
    cv2.circle(glow, lamp, max(2, int(0.02 * h)), 1.0, -1, cv2.LINE_AA)
    glow = np.maximum(glow, cv2.GaussianBlur(glow, (0, 0), 0.08 * h) * 4.0)
    image = 1 - (1 - image) * (1 - np.clip(glow, 0, 1)[..., None] * rgb("#F2A65A"))
    return np.clip(image, 0, 1).astype(np.float32)


def wallpaper(width, height, rng, ground=rgb("#B9A98A"), motif=rgb("#8E7E62"), stripe=cm(18.0)):
    """Old patterned wallpaper: faded vertical bands with a small repeated motif, a little uneven."""
    image = paint(width, height, ground, rng, mottle=0.04)
    h, w = image.shape[:2]
    period = max(4, int(stripe * TEXELS_PER_HEAD))
    for x in range(0, w, period):
        image[:, x:x + max(1, period // 10)] = image[:, x:x + max(1, period // 10)] * 0.9 + motif * 0.1
        for y in range((x // period % 2) * period // 2, h, period):
            cv2.ellipse(image, (x + period // 2, y), (max(1, period // 7), max(1, period // 5)), 0, 0, 360,
                        tuple(float(c) for c in motif), -1, cv2.LINE_AA)
    return np.clip(image, 0, 1).astype(np.float32)


@dataclass(frozen=True)
class SkyView:
    """A window view of a sky gradient, a sun or moon disc with its glow and rows of tower silhouettes."""
    stops: tuple                 # (share of the height from the top, colour) pairs
    skyline: tuple               # (colour, lowest, highest share of the height) per row of towers, back to front
    lit_share: float             # share of tower windows lit (0 for a daytime skyline)
    disc_color: np.ndarray
    disc_at: tuple               # disc centre as shares of the width and height
    disc_size: float             # disc radius as a share of the height (the glow reaches five times as far)
    stars: float = 0.0           # stars per texel of width in the upper sky


SKY_VIEW_WINDOWS = (rgb("#F6C980"), rgb("#F2B56A"), rgb("#9FC0F0"))
SKY_VIEW_GLOW = 0.45
SKY_VIEW_STAR = rgb("#C8D0F0")
SKY_VIEWS = {
    # A city at night seen from a desk: indigo sky, a moon, towers with a quarter of their windows lit.
    "city_night": SkyView(stops=((0.0, rgb("#121A36")), (0.6, rgb("#2C3462")), (1.0, rgb("#6E5878"))),
                          skyline=((rgb("#2E3558"), 0.30, 0.62), (rgb("#1A2040"), 0.45, 0.80)), lit_share=0.28,
                          disc_color=rgb("#F6EED8"), disc_at=(0.70, 0.26), disc_size=0.045, stars=0.15),
    # Late afternoon: blue overhead fading to gold, a low sun, low warm roofs on the horizon.
    "golden": SkyView(stops=((0.0, rgb("#8DB2D6")), (0.55, rgb("#F2D4A6")), (1.0, rgb("#F6B07A"))),
                      skyline=((rgb("#C9A58E"), 0.12, 0.26), (rgb("#A88274"), 0.08, 0.18)), lit_share=0.0,
                      disc_color=rgb("#FFF4D6"), disc_at=(0.30, 0.66), disc_size=0.06),
}


def sky_view(width, height, rng, view):
    """Paint a SkyView at window size (head heights)."""
    w, h = _size(width), _size(height)
    t = np.linspace(0.0, 1.0, h)
    column = np.zeros((h, 3), np.float32)
    for (t0, c0), (t1, c1) in zip(view.stops, view.stops[1:]):
        inside = (t >= t0) & (t <= t1)
        k = ((t[inside] - t0) / (t1 - t0))[:, None]
        column[inside] = c0 * (1 - k) + c1 * k
    image = np.repeat(column[:, None, :], w, axis=1)
    yy, xx = np.mgrid[0:h, 0:w]
    distance = np.hypot(xx - view.disc_at[0] * w, yy - view.disc_at[1] * h)
    glow = np.clip(1.0 - distance / (h * view.disc_size * 5), 0.0, 1.0) ** 2 * SKY_VIEW_GLOW
    image = image + glow[..., None] * (view.disc_color - image)
    image[distance < h * view.disc_size] = view.disc_color
    for _ in range(int(w * view.stars)):
        image[rng.integers(0, int(h * 0.45)), rng.integers(0, w)] = SKY_VIEW_STAR
    window_px = max(2, w // 70)
    for color, low, high in view.skyline:
        x = 0
        while x < w:
            span = int(rng.uniform(0.06, 0.16) * w)
            top = int(h * (1.0 - rng.uniform(low, high)))
            image[top:, x:x + span] = color
            for wy in range(top + window_px * 2, h - window_px, window_px * 3):
                for wx in range(x + window_px, x + span - window_px * 2, window_px * 3):
                    if rng.random() < view.lit_share:
                        image[wy:wy + window_px, wx:wx + window_px] = SKY_VIEW_WINDOWS[rng.integers(len(SKY_VIEW_WINDOWS))]
            x += span + int(rng.uniform(0.0, 0.03) * w)
    return np.clip(image, 0, 1).astype(np.float32)


def outdoor_view(width, height, kind, rng):
    """What a window shows: 'sky' (clouds), 'city' (towers), 'street' (trees and shops across a road),
    'panel_night' (the block across the courtyard at night), 'city_night' (towers under a moon) or
    'golden' (a low sun over the roofs late in the afternoon)."""
    if kind == "panel_night":
        return panel_night_view(width, height, rng)
    if kind in SKY_VIEWS:
        return sky_view(width, height, rng, SKY_VIEWS[kind])
    w, h = _size(width), _size(height)
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    image = np.broadcast_to(rgb("#5AA8E6") * (1 - t) + rgb("#D4EEFA") * t, (h, w, 3)).astype(np.float32).copy()
    for _ in range(5):
        cx, cy = rng.uniform(0, w), rng.uniform(0.1, 0.5) * h
        for dx in (-0.6, 0.0, 0.6):
            r = rng.uniform(0.06, 0.11) * w
            cv2.circle(image, (int(cx + dx * r), int(cy)), int(r), (1.0, 1.0, 1.0), -1, cv2.LINE_AA)
    if kind in ("city", "street"):
        base = 0.62 if kind == "city" else 0.48
        x = 0
        while x < w:
            bw = int(rng.uniform(0.08, 0.2) * w)
            top = int((base - rng.uniform(0.0, 0.35 if kind == "city" else 0.2)) * h)
            tone = rgb("#9AA6BE") * rng.uniform(0.85, 1.1) if kind == "city" else rgb("#E2C8A8") * rng.uniform(0.8, 1.1)
            image[top:, x:x + bw] = tone
            for wy in range(top + 6, int(h * (0.95 if kind == "city" else 0.70)), 10):
                for wx in range(x + 4, x + bw - 6, 9):
                    image[wy:wy + 5, wx:wx + 5] = rgb("#C8D8EE") if kind == "city" else rgb("#8AA0B8")
            x += bw + int(rng.uniform(0.0, 0.03) * w)
    if kind == "street":
        image[int(0.70 * h):] = rgb("#8C8C94")
        image[int(0.82 * h):] = rgb("#5E5E68")
        for _ in range(4):
            cx = rng.uniform(0, w)
            cv2.circle(image, (int(cx), int(0.55 * h)), int(0.09 * w), tuple(float(c) for c in rgb("#5E9A4C")), -1,
                       cv2.LINE_AA)
            cv2.rectangle(image, (int(cx - 2), int(0.6 * h)), (int(cx + 2), int(0.72 * h)), (0.3, 0.22, 0.16), -1)
    return np.clip(image, 0, 1)


def window(width, height, kind, rng, frame=rgb("#F4F2EE"), panes=(2, 1), blinds=False):
    """Window with a frame, mullions and the view outside (optionally half-open blinds)."""
    image = outdoor_view(width, height, kind, rng)
    h, w = image.shape[:2]
    if blinds:
        slat = max(3, h // 40)
        for top in range(0, int(h * 0.45), slat):
            image[top:top + slat - 1] = rgb("#E8E6E0") * (0.92 + 0.08 * (top % (2 * slat) == 0))
    border = max(2, int(cm(5.0) * TEXELS_PER_HEAD))
    image[:border], image[-border:], image[:, :border], image[:, -border:] = frame, frame, frame, frame
    for k in range(1, panes[0]):
        x = int(k * w / panes[0])
        image[:, x - border // 2:x + border // 2] = frame
    for k in range(1, panes[1]):
        y = int(k * h / panes[1])
        image[y - border // 2:y + border // 2] = frame
    return image


def curtain(width, height, color, folds=6):
    w, h = _size(width), _size(height)
    xs = np.linspace(0, folds * 2 * np.pi, w, dtype=np.float32)
    shade = 0.86 + 0.14 * np.sin(xs)[None, :, None]
    return np.clip(np.broadcast_to(np.asarray(color) * shade, (h, w, 3)).astype(np.float32), 0, 1)


def artwork(width, height, rng, frame=rgb("#3A3030")):
    """Framed abstract print: a few flat colour fields and a circle."""
    w, h = _size(width), _size(height)
    image = np.empty((h, w, 3), dtype=np.float32)
    image[:] = rgb("#F4EEE2")
    colors = (rgb("#E8A87C"), rgb("#85B6B0"), rgb("#E8C46A"), rgb("#C3727C"), rgb("#6E8CC0"))
    for _ in range(3):
        x0, y0 = rng.uniform(0.1, 0.5), rng.uniform(0.1, 0.5)
        _rect(image, x0, y0, x0 + rng.uniform(0.25, 0.45), y0 + rng.uniform(0.25, 0.45),
              colors[int(rng.integers(len(colors)))])
    cv2.circle(image, (int(w * 0.62), int(h * 0.38)), int(min(w, h) * 0.18),
               tuple(float(c) for c in colors[int(rng.integers(len(colors)))]), -1, cv2.LINE_AA)
    border = max(2, int(cm(3.0) * TEXELS_PER_HEAD))
    image[:border], image[-border:], image[:, :border], image[:, -border:] = frame, frame, frame, frame
    return image


def menu_board(width, height, rng):
    w, h = _size(width), _size(height)
    image = np.empty((h, w, 3), dtype=np.float32)
    image[:] = rgb("#2C3330")
    for column in (0.08, 0.55):
        y = 0.14
        _rect(image, column, 0.06, column + 0.22, 0.10, rgb("#F2D49A"))
        while y < 0.88:
            _rect(image, column, y, column + rng.uniform(0.18, 0.30), y + 0.025, rgb("#E8E6DE"))
            _rect(image, column + 0.33, y, column + 0.38, y + 0.025, rgb("#E8E6DE"))
            y += 0.075
    border = max(2, int(cm(3.0) * TEXELS_PER_HEAD))
    image[:border], image[-border:], image[:, :border], image[:, -border:] = (rgb("#7A5236"),) * 4
    return image


def fade(width, height, color, opacity, toward="bottom"):
    """RGBA strip that fades from opacity at one edge to clear (soft shadows where surfaces meet)."""
    w, h = _size(width), _size(height)
    ramp = np.linspace(0.0, 1.0, h if toward in ("top", "bottom") else w, dtype=np.float32) ** 1.6
    if toward == "top":
        ramp = ramp[::-1]
    alpha = (ramp[:, None] * np.ones((1, w)) if toward in ("top", "bottom")
             else np.ones((h, 1)) * (ramp[None, :] if toward == "right" else ramp[::-1][None, :]))
    image = np.empty((h, w, 4), dtype=np.float32)
    image[..., :3] = color
    image[..., 3] = alpha * opacity
    return image


def sun_patch(width, height, panes, opacity=SUN_PATCH_OPACITY, color=rgb("#FFF4D8")):
    """RGBA patch of window light on the floor, with the shadows of the mullions."""
    w, h = _size(width), _size(height)
    alpha = np.ones((h, w), dtype=np.float32)
    bar = max(2, int(cm(5.0) * TEXELS_PER_HEAD))
    for k in range(1, panes[0]):
        x = int(k * w / panes[0])
        alpha[:, x - bar // 2:x + bar // 2] = 0.0
    alpha = cv2.GaussianBlur(alpha, (0, 0), max(1.0, bar * 0.6))
    edge = cv2.GaussianBlur(np.pad(np.ones((h - 2 * bar, w - 2 * bar), np.float32), bar), (0, 0), bar)
    image = np.empty((h, w, 4), dtype=np.float32)
    image[..., :3] = color
    image[..., 3] = alpha * edge * opacity
    return image


def rgb_material(hex_base):
    """A plain painted material from one colour (shadow and line derived)."""
    base = rgb(hex_base)
    return props3d.Material(base=base, shadow=base * 0.62, line=base * 0.3, light=np.minimum(base * 1.15, 1.0))


# ---- the shell -------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Shell:
    x0: float
    x1: float
    z0: float           # back wall
    z1: float           # open front (walls end here)
    height: float


BACK, LEFT, RIGHT, UP, DOWN = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 1.0, 0.0)
FLOOR_MARGIN = 30.0     # head heights the floor runs on past the side walls (seen when a wall is left out)


def shell_surfaces(shell, floor, back, left, right, ceiling):
    """The five surfaces of a room, textures already sized to them (the floor texture spans the walls;
    the floor margin past them repeats its edge)."""
    s = shell
    margin = FLOOR_MARGIN
    return [Surface(((s.x0, -s.height, s.z1), (s.x1, -s.height, s.z1), (s.x1, -s.height, s.z0),
                     (s.x0, -s.height, s.z0)), ceiling, DOWN),
            Surface(((s.x0 - margin, 0.0, s.z0), (s.x1 + margin, 0.0, s.z0), (s.x1 + margin, 0.0, s.z1),
                     (s.x0 - margin, 0.0, s.z1)), _widen(floor, s, margin), UP),
            Surface(((s.x0, -s.height, s.z0), (s.x1, -s.height, s.z0), (s.x1, 0.0, s.z0), (s.x0, 0.0, s.z0)), back,
                    BACK),
            Surface(((s.x0, -s.height, s.z1), (s.x0, -s.height, s.z0), (s.x0, 0.0, s.z0), (s.x0, 0.0, s.z1)), left,
                    LEFT),
            Surface(((s.x1, -s.height, s.z0), (s.x1, -s.height, s.z1), (s.x1, 0.0, s.z1), (s.x1, 0.0, s.z0)), right,
                    RIGHT)]


def _widen(texture, shell, margin):
    """The floor texture continued sideways by tiling it, for the floor past the side walls."""
    share = margin / (shell.x1 - shell.x0)
    extra = int(round(texture.shape[1] * share))
    reps = int(np.ceil(extra / texture.shape[1])) + 1
    tiled = np.concatenate([texture] * reps, axis=1)
    return np.concatenate([tiled[:, tiled.shape[1] - extra:], texture, tiled[:, :extra]], axis=1)


def on_back_wall(shell, x0, x1, top, bottom, texture):
    """A decoration on the back wall: x from x0 to x1, heights above the floor from bottom to top."""
    z = shell.z0 + INSET
    return Surface(((x0, -top, z), (x1, -top, z), (x1, -bottom, z), (x0, -bottom, z)), texture, BACK)


def on_left_wall(shell, z_back, z_front, top, bottom, texture):
    x = shell.x0 + INSET
    return Surface(((x, -top, z_front), (x, -top, z_back), (x, -bottom, z_back), (x, -bottom, z_front)), texture,
                   LEFT)


def on_right_wall(shell, z_back, z_front, top, bottom, texture):
    x = shell.x1 - INSET
    return Surface(((x, -top, z_back), (x, -top, z_front), (x, -bottom, z_front), (x, -bottom, z_back)), texture,
                   RIGHT)


def trims(shell, color, height=cm(8.0)):
    """Skirting boards along the three walls and the soft darkening of the floor next to them."""
    s = shell
    shade = rgb("#2A2026")
    return [on_back_wall(s, s.x0, s.x1, height, 0.0, np.full((4, 4, 3), color, np.float32)),
            on_left_wall(s, s.z0, s.z1, height, 0.0, np.full((4, 4, 3), color, np.float32)),
            on_right_wall(s, s.z0, s.z1, height, 0.0, np.full((4, 4, 3), color, np.float32)),
            Surface(((s.x0, -0.001, s.z0 + CORNER_SHADOW), (s.x1, -0.001, s.z0 + CORNER_SHADOW), (s.x1, -0.001, s.z0),
                     (s.x0, -0.001, s.z0)), fade(s.x1 - s.x0, CORNER_SHADOW, shade, CORNER_SHADOW_OPACITY, "bottom")),
            Surface(((s.x0 + CORNER_SHADOW, -0.001, s.z0), (s.x0 + CORNER_SHADOW, -0.001, s.z1), (s.x0, -0.001, s.z1),
                     (s.x0, -0.001, s.z0)), fade(s.z1 - s.z0, CORNER_SHADOW, shade, CORNER_SHADOW_OPACITY, "bottom")),
            Surface(((s.x1 - CORNER_SHADOW, -0.001, s.z1), (s.x1 - CORNER_SHADOW, -0.001, s.z0), (s.x1, -0.001, s.z0),
                     (s.x1, -0.001, s.z1)), fade(s.z1 - s.z0, CORNER_SHADOW, shade, CORNER_SHADOW_OPACITY, "bottom"))]


def sunlight(shell, x0, x1, top, bottom, panes):
    """Floor patch lit through a back-wall window (x0..x1, top and bottom heights above the floor)."""
    direction = np.asarray(SUNLIGHT, dtype=np.float64)

    def land(x, height):
        t = height / direction[1]
        return (x + direction[0] * t, -0.002, shell.z0 + direction[2] * t)

    corners = (land(x0, top), land(x1, top), land(x1, bottom), land(x0, bottom))
    width = abs(x1 - x0)
    depth = abs(corners[0][2] - corners[3][2])
    return Surface(corners, sun_patch(width, depth, panes))


# ---- rooms -------------------------------------------------------------------------------------------------------
def living_room(seed=3):
    """Living room: plank floor, cream walls, a window with curtains, a sofa along the left side facing a
    television on a low cabinet along the right side, a coffee table on a rug between them, a bookcase,
    plants and a floor lamp.
    places: 'sofa' (facing +x; seats 'seat_0' nearest the open front .. 'seat_2'), 'cabinet', 'coffee_table'."""
    rng = np.random.default_rng(seed)
    shell = Shell(-8.0, 8.0, -9.0, ROOM_FRONT, cm(250.0))
    wall = rgb("#EFE4D2")
    width, depth = shell.x1 - shell.x0, shell.z1 - shell.z0
    surfaces = shell_surfaces(shell, planks(width, depth, (rgb("#B98654"), rgb("#A97446"), rgb("#C6935E")), rng),
                              paint(width, shell.height, wall, rng), paint(depth, shell.height, wall * 0.97, rng),
                              paint(depth, shell.height, wall * 0.97, rng), paint(width, depth, wall * 0.92, rng))
    surfaces += trims(shell, rgb("#F7F3EC"))
    window_box = (-3.0, 3.0, cm(215.0), cm(85.0))
    surfaces.append(on_back_wall(shell, *window_box, window(6.0, window_box[2] - window_box[3], "sky", rng, panes=(2, 1))))
    surfaces.append(sunlight(shell, *window_box, (2, 1)))
    curtain_color = rgb("#C8D8C0")
    for x in (window_box[0] - 1.1, window_box[1] - 0.2):
        surfaces.append(on_back_wall(shell, x, x + 1.3, cm(225.0), cm(40.0), curtain(1.3, cm(185.0), curtain_color)))
    surfaces.append(on_left_wall(shell, -5.3, 0.1, cm(205.0), cm(150.0), artwork(5.4, cm(55.0), rng)))

    sofa = Placed(furniture3d.sofa(), at=(shell.x0 + 2.4, 0.0, -2.6), yaw=np.pi / 2)
    cabinet = Placed(furniture3d.low_cabinet(), at=(shell.x1 - 0.95, 0.0, -2.6), yaw=-np.pi / 2)
    tv = on_top(props3d.television("game"), cabinet, offset=(0.0, 0.0, -0.2))
    table = Placed(furniture3d.coffee_table(), at=(-0.8, 0.0, -2.6), yaw=np.pi / 2)
    items = [Placed(furniture3d.rug(cm(240.0), cm(170.0)), at=(-1.2, 0.0, -2.6), yaw=np.pi / 2), sofa, cabinet, tv,
             table,
             on_top(props3d.mug(body=props3d.surface("#E07A5F", "#9A3E36", "#4E1A18", "#F8A890")), table,
                    offset=(-0.9, 0.0, 0.2)),
             on_top(props3d.book_stack(2, seed=8), table, offset=(1.1, 0.0, -0.1), yaw=0.3),
             Placed(furniture3d.bookshelf(), at=(-5.6, 0.0, shell.z0 + 0.7)),
             Placed(props3d.potted_plant(height=cm(60.0)), at=(6.8, 0.0, -7.8)),
             Placed(furniture3d.floor_lamp(), at=(shell.x0 + 0.8, 0.0, -7.0)),
             on_top(props3d.potted_plant(seed=6), cabinet, offset=(-3.2, 0.0, 0.0))]
    return Room(surfaces, items, {"sofa": sofa, "cabinet": cabinet, "coffee_table": table},
                (shell.x0, shell.x1, shell.z0, shell.z1, shell.height))


def office(seed=5):
    """Open office: carpet tiles, a wall of windows with blinds over the city, two desks (a laptop desk and a
    monitor desk), task chairs, a filing shelf and plants.
    places: 'desk' and 'chair' (the laptop desk, its user faces +z), 'desk_2' and 'chair_2'."""
    rng = np.random.default_rng(seed)
    shell = Shell(-13.0, 13.0, -9.0, ROOM_FRONT, cm(270.0))
    wall = rgb("#E9ECEF")
    width, depth = shell.x1 - shell.x0, shell.z1 - shell.z0
    surfaces = shell_surfaces(shell, carpet_tiles(width, depth, rgb("#7E8794"), rng),
                              paint(width, shell.height, wall, rng), paint(depth, shell.height, wall * 0.96, rng),
                              paint(depth, shell.height, wall * 0.96, rng), paint(width, depth, wall * 0.95, rng))
    surfaces += trims(shell, rgb("#B9BEC6"))
    for x in (-12.0, -6.0, 0.0, 6.0):
        box = (x, x + 5.6, cm(240.0), cm(80.0))
        surfaces.append(on_back_wall(shell, *box, window(5.6, box[2] - box[3], "city", rng, frame=rgb("#C9CDD4"),
                                                         panes=(2, 1), blinds=True)))
        surfaces.append(sunlight(shell, *box, (2, 1)))
    surfaces.append(on_left_wall(shell, -6.0, -2.0, cm(190.0), cm(110.0), artwork(4.0, cm(80.0), rng)))

    desk = Placed(furniture3d.desk(cm(140.0), cm(70.0)), at=(-1.0, 0.0, -2.0), yaw=np.pi)
    chair = Placed(furniture3d.office_chair(), at=(-1.0, 0.0, -4.4))
    desk_2 = Placed(furniture3d.desk(cm(140.0), cm(70.0)), at=(6.5, 0.0, -1.4), yaw=np.pi - 0.35)
    chair_2 = Placed(furniture3d.office_chair(), at=(5.5, 0.0, -4.2), yaw=0.05)
    items = [desk, chair, desk_2, chair_2,
             on_top(props3d.mug(body=props3d.surface("#5E8FC8", "#2E5A8E", "#14304E", "#9AC0EC")), desk,
                    offset=(2.0, 0.0, 0.5)),
             on_top(props3d.phone("home"), desk, offset=(-1.8, 0.0, 0.8), yaw=0.4),
             on_top(props3d.potted_plant(seed=9), desk, offset=(-2.4, 0.0, -0.7)),
             on_top(props3d.monitor("code"), desk_2, offset=(0.0, 0.0, 0.5), yaw=np.pi),
             on_top(props3d.keyboard(), desk_2, offset=(0.0, 0.0, -0.6), yaw=np.pi),
             on_top(props3d.mouse(), desk_2, offset=(-1.3, 0.0, -0.6), yaw=np.pi),
             on_top(props3d.desk_lamp(), desk_2, offset=(2.2, 0.0, 0.6), yaw=np.pi + 0.6),
             on_top(props3d.book_stack(3, seed=2), desk_2, offset=(-2.2, 0.0, 0.5), yaw=0.2),
             Placed(furniture3d.bookshelf(cm(90.0), cm(120.0), shelves=3, body=rgb_material("#C9CDD4")),
                    at=(shell.x0 + 0.7, 0.0, 3.0), yaw=np.pi / 2),
             Placed(props3d.potted_plant(height=cm(80.0), seed=4), at=(-12.0, 0.0, -7.8)),
             Placed(props3d.potted_plant(height=cm(70.0), seed=7), at=(12.0, 0.0, -7.6))]
    places = {"desk": desk, "chair": chair, "desk_2": desk_2, "chair_2": chair_2}
    return Room(surfaces, items, places, (shell.x0, shell.x1, shell.z0, shell.z1, shell.height))


def cafe(seed=11):
    """Cafe: plank floor, a brick back wall with a street window, a counter under a menu board, pendant lamps
    over two round tables with chairs, plants.
    places: 'table', 'chair' (at its left side, facing +x), 'chair_2' (behind it, facing the open front +z),
    'table_2', 'counter'."""
    rng = np.random.default_rng(seed)
    shell = Shell(-12.0, 12.0, -8.0, ROOM_FRONT, cm(280.0))
    width, depth = shell.x1 - shell.x0, shell.z1 - shell.z0
    surfaces = shell_surfaces(shell, planks(width, depth, (rgb("#8A5E3E"), rgb("#7A5236"), rgb("#966A46")), rng,
                                            plank=cm(12.0)),
                              bricks(width, shell.height, rgb("#B8664A"), rng),
                              paint(depth, shell.height, rgb("#E8DCC8"), rng),
                              paint(depth, shell.height, rgb("#E8DCC8"), rng),
                              paint(width, depth, rgb("#3A3434"), rng, 1.0, 1.0))
    surfaces += trims(shell, rgb("#5A3C28"))
    window_box = (-10.5, -1.5, cm(230.0), cm(70.0))
    surfaces.append(on_back_wall(shell, *window_box, window(9.0, window_box[2] - window_box[3], "street", rng,
                                                            frame=rgb("#2E2A28"), panes=(3, 1))))
    surfaces.append(sunlight(shell, *window_box, (3, 1)))
    surfaces.append(on_back_wall(shell, 3.0, 10.0, cm(250.0), cm(175.0), menu_board(7.0, cm(75.0), rng)))
    surfaces.append(on_left_wall(shell, -4.0, 0.0, cm(200.0), cm(130.0), artwork(4.0, cm(70.0), rng)))

    table = Placed(furniture3d.cafe_table(), at=(-3.0, 0.0, -1.0))
    chair = Placed(furniture3d.cafe_chair(), at=(-5.0, 0.0, -0.7), yaw=np.pi / 2)
    chair_2 = Placed(furniture3d.cafe_chair(), at=(-3.0, 0.0, -3.0))
    table_2 = Placed(furniture3d.cafe_table(), at=(4.0, 0.0, 2.8))
    counter = Placed(furniture3d.counter(cm(280.0)), at=(6.5, 0.0, shell.z0 + 1.5))
    items = [table, chair, chair_2, table_2,
             Placed(furniture3d.cafe_chair(), at=(5.9, 0.0, 3.6), yaw=-1.9),
             Placed(furniture3d.cafe_chair(), at=(2.2, 0.0, 2.2), yaw=1.2),
             counter,
             on_top(props3d.paper_cup(), counter, offset=(-3.0, 0.0, 0.0)),
             on_top(props3d.paper_cup(), counter, offset=(-2.4, 0.0, 0.3)),
             on_top(props3d.mug(), counter, offset=(2.5, 0.0, -0.2)),
             on_top(props3d.potted_plant(seed=12), counter, offset=(4.6, 0.0, -0.3)),
             on_top(props3d.mug(body=props3d.surface("#F2EFE8", "#A9A6B4", "#5A5866", "#FFFFFF")), table_2,
                    offset=(0.3, 0.0, 0.2)),
             Placed(furniture3d.pendant_lamp(ceiling=shell.height), at=(-3.0, 0.0, -1.0)),
             Placed(furniture3d.pendant_lamp(ceiling=shell.height), at=(4.0, 0.0, 2.8)),
             Placed(props3d.potted_plant(height=cm(90.0), seed=3), at=(-11.0, 0.0, -6.8)),
             Placed(props3d.potted_plant(height=cm(60.0), seed=13), at=(11.0, 0.0, 0.5))]
    places = {"table": table, "chair": chair, "chair_2": chair_2, "table_2": table_2, "counter": counter}
    return Room(surfaces, items, places, (shell.x0, shell.x1, shell.z0, shell.z1, shell.height))


def bedroom(seed=13):
    """Bedroom: plank floor, warm walls, a double bed against the back wall under a picture, nightstands with a
    lamp and a plant, a window with curtains on the left wall, a rug at the foot of the bed.
    places: 'bed' (figures: anchors 'lie_back_0', 'lie_back_1', 'lie_front'; objects: 'top', 'duvet'),
    'nightstand' (right of the bed)."""
    rng = np.random.default_rng(seed)
    shell = Shell(-8.0, 8.0, -6.0, ROOM_FRONT, cm(250.0))
    wall = rgb("#EDE2D6")
    width, depth = shell.x1 - shell.x0, shell.z1 - shell.z0
    surfaces = shell_surfaces(shell, planks(width, depth, (rgb("#B98E66"), rgb("#AC8058"), rgb("#C49A72")), rng),
                              paint(width, shell.height, wall, rng), paint(depth, shell.height, wall * 0.97, rng),
                              paint(depth, shell.height, wall * 0.97, rng), paint(width, depth, wall * 0.93, rng))
    surfaces += trims(shell, rgb("#F7F3EC"))
    surfaces.append(on_back_wall(shell, -2.4, 2.4, cm(215.0), cm(150.0), artwork(4.8, cm(65.0), rng)))
    window_box = (-3.5, 1.5, cm(215.0), cm(90.0))
    surfaces.append(on_left_wall(shell, *window_box, window(5.0, window_box[2] - window_box[3], "sky", rng)))
    for z in (window_box[0] - 1.0, window_box[1] - 0.3):
        surfaces.append(on_left_wall(shell, z, z + 1.3, cm(225.0), cm(40.0), curtain(1.3, cm(185.0), rgb("#D8C8E0"))))

    bed = Placed(furniture3d.bed(), at=(0.0, 0.0, shell.z0 + cm(103.0)))
    nightstand = Placed(furniture3d.low_cabinet(cm(45.0), cm(52.0), cm(38.0)), at=(4.6, 0.0, shell.z0 + 0.95))
    nightstand_2 = Placed(furniture3d.low_cabinet(cm(45.0), cm(52.0), cm(38.0)), at=(-4.6, 0.0, shell.z0 + 0.95))
    items = [bed, nightstand, nightstand_2,
             on_top(props3d.desk_lamp(), nightstand, offset=(0.1, 0.0, -0.1), yaw=-0.6),
             on_top(props3d.book_stack(2, seed=12), nightstand_2, offset=(-0.4, 0.0, 0.15), yaw=0.2),
             on_top(props3d.potted_plant(seed=14), nightstand_2, offset=(0.45, 0.0, -0.2)),
             Placed(furniture3d.rug(cm(200.0), cm(120.0)), at=(0.0, 0.0, bed.at[2] + cm(140.0))),
             Placed(props3d.potted_plant(height=cm(70.0), seed=15), at=(6.9, 0.0, shell.z0 + 0.8))]
    return Room(surfaces, items, {"bed": bed, "nightstand": nightstand},
                (shell.x0, shell.x1, shell.z0, shell.z1, shell.height))
