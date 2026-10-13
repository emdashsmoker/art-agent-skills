"""City scenery: flat facades, far skylines, and perspective cameras (one- and two-point).

The trick for streets: paint each building face flat on its own small canvas
(facade()), then let Perspective tell you where its four corners land and
Canvas.paste() it there. The same works for the road, signs and shop fronts.

World units are meters: X to the right, Y up from the ground, Z away from the viewer.
"""
from dataclasses import dataclass

import numpy as np

from . import config, raster
from .canvas import Canvas
from .color import adjust, mix, shadow_of

_PX_PER_METER = 14            # facade texture resolution
_MIN_DEPTH = 0.5              # meters; nothing is projected closer than this
_NEAR_DEPTH, _NEAR_RESOLUTION = 30.0, 28   # buildings closer than this (m) get a finer texture (px/m)
_BLOCK_DEPTH = 14.0           # meters a building extends back from the street


def _rng(seed):
    return np.random.default_rng(config.DEFAULT_SEED if seed is None else seed)


def _rects(cv, boxes):
    """Mask of many axis-aligned rectangles (x0, y0, x1, y1)."""
    return cv.polygon(*[np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) for x0, y0, x1, y1 in boxes])


def facade(width_m, height_m, wall='#8a8f9a', glass='#27324a', lit=('#ffd98a', '#fff1c4', '#ffb86a'),
           lit_ratio=0.3, floor_m=3.4, bay_m=3.0, window=(0.62, 0.55), shop=None, resolution=None, seed=None):
    """One building face, painted flat. Returns a Canvas to paste().

    floor_m / bay_m: height of a storey and width of a window bay.
    window: (width, height) of a window as a fraction of its bay and storey.
    lit_ratio: share of windows with the lights on (0 for daytime).
    shop: color of a ground-floor shop front with a lit window band, or None.
    resolution: px per meter of the texture (default 14; raise it for faces close to the viewer).
    """
    rng = _rng(seed)
    scale = resolution or _PX_PER_METER
    width, height = max(int(width_m * scale), 8), max(int(height_m * scale), 8)
    cv = Canvas(width, height, wall)
    cv.tint(cv.full() * cv.linear((0, 0), (0, height)), shadow_of(wall, 0.7), 'normal', 0.35)   # grime toward the street
    cols, rows = max(int(width_m / bay_m), 1), max(int(height_m / floor_m), 1)
    cell_w, cell_h = width / cols, height / rows
    first_row = 1 if shop else 0
    dark, bright = [], [[] for _ in lit]
    for row in range(rows - first_row):
        for col in range(cols):
            x0 = (col + 0.5 - window[0] / 2) * cell_w
            y0 = (row + 0.5 - window[1] / 2) * cell_h
            box = (x0, y0, x0 + window[0] * cell_w, y0 + window[1] * cell_h)
            if rng.random() < lit_ratio:
                bright[rng.integers(len(lit))].append(box)
            else:
                dark.append(box)
    if dark:
        panes = _rects(cv, dark)
        cv.fill(panes, glass)
        cv.tint(panes * cv.linear((0, 0), (width, height)), adjust(glass, lightness=0.16), 'normal', 0.5)  # sky reflection
    for boxes, tone in zip(bright, lit):
        if boxes:
            cv.fill(_rects(cv, boxes), tone)
    sills = _rects(cv, [(x0 - 2, y1, x1 + 2, y1 + max(cell_h * 0.05, 1.5)) for x0, y0, x1, y1 in dark + sum(bright, [])])
    cv.tint(sills, adjust(wall, lightness=0.10), 'normal', 0.9)
    if shop:
        top = (rows - 1) * cell_h
        cv.fill(_rects(cv, [(0, top, width, height)]), shop)
        cv.fill(_rects(cv, [(width * 0.06, top + cell_h * 0.28, width * 0.94, height - cell_h * 0.12)]),
                mix(lit[0], '#ffffff', 0.25) if lit_ratio > 0 else glass)
        cv.fill(_rects(cv, [(0, top, width, top + cell_h * 0.16)]), shadow_of(shop, 0.8))
    cv.fill(_rects(cv, [(0, 0, width, max(cell_h * 0.10, 2))]), adjust(wall, lightness=0.08))      # roof ledge
    return cv


def skyline(cv, base_y, height=(120, 380), width=(46, 130), color='#2a3050', lit='#ffd98a', lit_ratio=0.25,
            window_px=5, seed=None):
    """A row of distant towers as flat silhouettes with speckled windows, filled down to base_y.

    Layer two or three rows (farther = lower, paler) for depth. Returns the row's mask.
    """
    rng = _rng(seed)
    towers, lights, x = [], [], -rng.uniform(0, width[1])
    while x < cv.width:
        w, h = rng.uniform(*width), rng.uniform(*height)
        top = base_y - h
        towers.append(np.array([(x, base_y), (x, top), (x + w, top), (x + w, base_y)]))
        if rng.random() < 0.35:                                # stepped crown
            towers.append(np.array([(x + w * 0.25, top), (x + w * 0.25, top - h * 0.10), (x + w * 0.75, top - h * 0.10),
                                    (x + w * 0.75, top)]))
        if rng.random() < 0.25:                                # antenna
            towers.append(np.array([(x + w * 0.5 - 1.5, top), (x + w * 0.5 - 1.5, top - h * 0.22),
                                    (x + w * 0.5 + 1.5, top - h * 0.22), (x + w * 0.5 + 1.5, top)]))
        pitch = window_px * 2.2
        for wx in np.arange(x + pitch * 0.6, x + w - pitch * 0.6, pitch):
            for wy in np.arange(top + pitch, base_y - pitch * 0.5, pitch * 1.25):
                if rng.random() < lit_ratio:
                    lights.append((wx, wy, wx + window_px, wy + window_px * 1.2))
        x += w + rng.uniform(-6, 14)
    mask = cv.polygon(*towers)
    cv.fill(mask, color)
    if lights:
        cv.tint(_rects(cv, lights) * mask, lit, 'normal', 0.9)
    return mask


@dataclass
class Perspective:
    """One-point perspective camera looking down the Z axis.

    vanishing: px where the street disappears. focal: px (about the canvas width
    for a normal lens; smaller = wider). eye: camera height in meters.
    """
    vanishing: tuple
    focal: float
    eye: float = 1.6

    def project(self, x, y, z):
        """World point (meters) -> canvas px."""
        z = max(z, _MIN_DEPTH)
        return (self.vanishing[0] + self.focal * x / z, self.vanishing[1] - self.focal * (y - self.eye) / z)

    def scale(self, z):
        """Pixels per meter at depth z - the size of anything standing there."""
        return self.focal / max(z, _MIN_DEPTH)

    @property
    def position(self):
        """Camera position in meters (it sits on the Z axis at eye height)."""
        return (0.0, self.eye, 0.0)

    def depth(self, x, y, z):
        """Distance of a world point along the viewing direction."""
        return z

    def scale_at(self, x, y, z):
        """Pixels per meter at a world point."""
        return self.scale(z)

    def depth_at_row(self, row_y):
        """Depth of the ground point that appears on canvas row row_y (below the horizon)."""
        return self.focal * self.eye / max(row_y - self.vanishing[1], 1e-6)

    def quad(self, corners):
        """Project four world points (x, y, z) given as top-left, top-right, bottom-right, bottom-left:
        any flat face - a tilted laptop screen, a ramp, a sloping roof."""
        return [self.project(*corner) for corner in corners]

    def wall_quad(self, x, z_near, z_far, height):
        """Corners (TL, TR, BR, BL as seen on screen) of a wall parallel to the street at lateral position x."""
        near_top, far_top = self.project(x, height, z_near), self.project(x, height, z_far)
        near_bottom, far_bottom = self.project(x, 0.0, z_near), self.project(x, 0.0, z_far)
        if x < 0:
            return [near_top, far_top, far_bottom, near_bottom]
        return [far_top, near_top, near_bottom, far_bottom]

    def front_quad(self, x_left, x_right, z, height, base=0.0):
        """Corners of a wall facing the viewer at depth z."""
        return [self.project(x_left, height, z), self.project(x_right, height, z),
                self.project(x_right, base, z), self.project(x_left, base, z)]

    def ground_quad(self, x_left, x_right, z_near, z_far):
        """Corners of a ground strip (road, pavement) running away from the viewer."""
        return [self.project(x_left, 0.0, z_far), self.project(x_right, 0.0, z_far),
                self.project(x_right, 0.0, z_near), self.project(x_left, 0.0, z_near)]


@dataclass
class Camera:
    """Camera that can turn and tilt: two-point (yaw) and three-point (pitch) perspective.

    center: px where the line of sight meets the canvas (usually the canvas center).
    focal: px (about the canvas width for a normal lens; smaller = wider).
    position: (x, y, z) meters; y is the eye height.
    yaw: degrees; + turns the camera to look toward +X (screen right).
    pitch: degrees; + tilts it down to look at the floor or a table, so verticals converge downward.

    Same projection interface as Perspective (project, scale_at, depth, quad, position), so
    solids, paste() and figures work with either.
    """
    center: tuple
    focal: float
    position: tuple = (0.0, 1.6, 0.0)
    yaw: float = 0.0
    pitch: float = 0.0

    def _basis(self):
        yaw, pitch = np.radians(self.yaw), np.radians(self.pitch)
        forward = np.array([np.sin(yaw) * np.cos(pitch), -np.sin(pitch), np.cos(yaw) * np.cos(pitch)])
        right = np.array([np.cos(yaw), 0.0, -np.sin(yaw)])
        up = np.cross(forward, right)
        return right, up, forward

    @property
    def eye(self):
        return self.position[1]

    def depth(self, x, y, z):
        """Distance of a world point along the line of sight."""
        _, _, forward = self._basis()
        return float(np.dot(np.array([x, y, z], np.float64) - self.position, forward))

    def project(self, x, y, z):
        """World point (meters) -> canvas px."""
        right, up, forward = self._basis()
        d = np.array([x, y, z], np.float64) - self.position
        depth = max(float(np.dot(d, forward)), _MIN_DEPTH * 0.2)
        return (self.center[0] + self.focal * float(np.dot(d, right)) / depth,
                self.center[1] - self.focal * float(np.dot(d, up)) / depth)

    def scale(self, depth):
        """Pixels per meter at a given viewing distance."""
        return self.focal / max(depth, _MIN_DEPTH * 0.2)

    def scale_at(self, x, y, z):
        """Pixels per meter at a world point."""
        return self.scale(self.depth(x, y, z))

    def quad(self, corners):
        """Project four world points given as top-left, top-right, bottom-right, bottom-left."""
        return [self.project(*corner) for corner in corners]

    def vanishing_point(self, heading_deg):
        """Where horizontal lines with this heading meet on the canvas (0 = along +Z, 90 = along +X)."""
        heading = np.radians(heading_deg)
        far = np.array(self.position) + 1e6 * np.array([np.sin(heading), 0.0, np.cos(heading)])
        return self.project(*far)

    def horizon_y(self):
        """Canvas row of the horizon at the center column."""
        return self.vanishing_point(self.yaw)[1]


def project_polygon(view, points, near=0.3):
    """Project a flat world polygon [(x, y, z), ...] that may reach past the camera.

    The part closer than `near` meters (or behind the viewer) is cut off first, so a road
    or pavement that runs under the camera still fills the bottom of the picture.
    Returns canvas points for cv.polygon(), or an empty list when nothing is in front.
    """
    points = [np.asarray(p, np.float64) for p in points]
    depths = [view.depth(*p) - near for p in points]
    kept = []
    for index, (point, depth) in enumerate(zip(points, depths)):
        following, following_depth = points[(index + 1) % len(points)], depths[(index + 1) % len(points)]
        if depth >= 0:
            kept.append(point)
        if (depth >= 0) != (following_depth >= 0):              # the edge crosses the near plane
            t = depth / (depth - following_depth)
            kept.append(point + (following - point) * t)
    return np.array([view.project(*p) for p in kept]) if len(kept) >= 3 else []


def ground_rects(cv, view, rects, y=0.0):
    """Mask of axis-aligned rectangles lying on the ground: [(x0, z0, x1, z1), ...] meters.
    Road markings, crosswalk stripes, paving slabs, rugs."""
    polygons = [project_polygon(view, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]) for x0, z0, x1, z1 in rects]
    polygons = [np.asarray(p) for p in polygons if len(p)]
    return cv.polygon(*polygons) if polygons else cv.empty()


def road_texture(width_m, length_m, asphalt='#3a3d46', line='#e9e2c8', lanes=2, crosswalk_at=None):
    """Flat road seen from above, far end at the top. Paste it onto Perspective.ground_quad()."""
    scale = _PX_PER_METER
    width, height = int(width_m * scale), int(length_m * scale)
    cv = Canvas(width, height, asphalt)
    cv.tint(raster.smoothstep(cv.noise(scale=90, octaves=3, seed=3, stretch=(1.0, 4.0)), 0.45, 0.7),
            adjust(asphalt, lightness=0.05), 'normal', 0.5)
    dashes = []
    for lane in range(1, lanes):
        x = width * lane / lanes
        for y in np.arange(0, height, 6.0 * scale):
            dashes.append((x - 0.08 * scale, y, x + 0.08 * scale, y + 3.0 * scale))
    edge = 0.35 * scale
    dashes += [(edge, 0, edge + 0.12 * scale, height), (width - edge - 0.12 * scale, 0, width - edge, height)]
    if crosswalk_at is not None:
        y = height - crosswalk_at * scale
        dashes += [(x, y - 3.0 * scale, x + 0.5 * scale, y) for x in np.arange(0.6 * scale, width - 0.6 * scale, 1.0 * scale)]
    cv.fill(_rects(cv, dashes), line, 0.9)
    return cv


def street(cv, view, road_half=5.0, pavement=3.0, depth=(4.0, 160.0), height=(12.0, 38.0), length=(10.0, 22.0),
           walls=('#8a8f9a', '#9a8f86', '#7f8794', '#a39a8c'), glass='#27324a', lit_ratio=0.3, shops=('#7a3b3b', '#2f5a5a', '#5a4a7a'),
           asphalt='#3a3d46', paving='#77736f', shade_side='left', haze=None, seed=None):
    """A street running straight away from the viewer: road, pavements and a wall of buildings on each side.

    depth: (nearest, farthest) meters built. height/length: building size ranges in meters.
    shade_side: the row that sits in shadow ('left' | 'right' | None for night scenes).
    haze: color the far buildings fade toward (default: the sky color just above the vanishing point).
    Returns dict(road=mask, left=mask, right=mask).
    """
    rng = _rng(seed)
    near, far = depth
    if haze is None:
        column = int(np.clip(view.vanishing[0], 0, cv.width - 1))
        haze = cv.color[max(int(view.vanishing[1]) - 40, 0), column].copy()
    row_start = min(near, view.depth_at_row(cv.height) * 0.9)
    outer = road_half + pavement
    masks = dict(left=cv.empty(), right=cv.empty())
    for side, name in ((-1, 'left'), (1, 'right')):
        plan, z = [], near
        while z < far:
            size = rng.uniform(*length)
            plan.append((z, min(z + size, far), rng.uniform(*height)))
            z += size
        for z0, z1, tall in reversed(plan):                                # far to near
            wall = walls[rng.integers(len(walls))]
            detail = _NEAR_RESOLUTION if z0 < _NEAR_DEPTH else _PX_PER_METER
            distance = np.clip((z0 - near) / (far - near), 0.0, 1.0) ** 0.7  # far walls fade into the air
            # End wall facing the viewer: seen wherever this building rises above its nearer neighbor.
            end = facade(_BLOCK_DEPTH, tall, wall, glass, lit_ratio=lit_ratio * 0.6, resolution=detail,
                         seed=int(rng.integers(1 << 30)))
            x_inner, x_outer = side * outer, side * (outer + _BLOCK_DEPTH)
            end_cover = cv.paste(end, view.front_quad(min(x_inner, x_outer), max(x_inner, x_outer), z0, tall))
            cv.tint(end_cover, '#6a7096', 'multiply', 0.35)
            face = facade(z1 - z0, tall, wall, glass, lit_ratio=lit_ratio, resolution=detail,
                          shop=shops[rng.integers(len(shops))] if shops else None,
                          seed=int(rng.integers(1 << 30)))
            cover = cv.paste(face, view.wall_quad(side * outer, z0, z1, tall))
            if shade_side == name:
                cv.tint(cover, '#5a6288', 'multiply', 0.55)
            for covered in (end_cover, cover):
                cv.tint(covered, haze, 'normal', 0.75 * distance)
            masks[name] = np.maximum(masks[name], np.maximum(cover, end_cover))
    for x0, x1, tone in ((-outer, -road_half, paving), (road_half, outer, paving)):
        slab = Canvas(int((x1 - x0) * _PX_PER_METER), int((far - row_start) * _PX_PER_METER), tone)
        kerb = _rects(slab, [(0 if x0 > 0 else slab.width - 3, 0, 3 if x0 > 0 else slab.width, slab.height)])
        slab.fill(kerb, adjust(tone, lightness=0.12))
        cv.paste(slab, view.ground_quad(x0, x1, row_start, far))
    masks['road'] = cv.paste(road_texture(2 * road_half, far - row_start, asphalt),
                             view.ground_quad(-road_half, road_half, row_start, far))
    return masks


def street_lamp(cv, view, x, z, height=7.0, glow='#ffd9a0', on=True, pole='#2a2c33'):
    """A lamp post standing at world position (x, z); its arm reaches toward the road."""
    scale = view.scale_at(x, 0.0, z)
    foot, top = view.project(x, 0.0, z), view.project(x, height, z)
    arm = view.project(x - np.sign(x) * 1.6, height + 0.2, z)
    cv.fill(cv.ribbon([foot, top, arm], max(0.16 * scale, 1.2), 'flat', smooth=False), pole)
    if on:
        cv.tint(cv.radial(arm, 5.0 * scale) ** 2.0, glow, 'screen', 0.85)
        cv.tint(cv.radial(arm, 0.5 * scale), '#ffffff', 'screen', 0.95)
        pool = view.project(x - np.sign(x) * 1.6, 0.0, z)
        cv.tint(cv.radial(pool, 6.0 * scale, 1.6 * scale), glow, 'screen', 0.35)
