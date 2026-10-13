"""City street in one-point perspective.

Construction follows perspective drawing: a horizon line, one vanishing point,
and every plane drawn flat first and then mapped onto its receding quad.
  - facades: wall, window grid, shopfront drawn flat, then warped
  - ground: asphalt, markings, paving joints and sun shadows drawn as a street plan, then warped
  - props: signs, trees, lamps, cars and people placed by distance and drawn far to near
Light is one sun direction plus sky ambient, so the lit side of the street, the
shaded side and the shadows on the road agree with each other.
Distances are meters; the camera stands on the street axis looking along +z.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from ..color import rgb, mix, fbm, vertical_gradient
from .landscape import clouds

SUPERSAMPLE = 2             # everything is drawn on a finer canvas, then averaged down
PIXELS_PER_METER = 14       # resolution of the flat facade drawings
NEAR_PPM = 36               # facades closer than NEAR_Z are drawn finer: they fill the frame
NEAR_Z = 32.0
GROUND_PPM = 22             # resolution of the near street plan
GROUND_NEAR = (2.0, 70.0)   # z range drawn at full plan resolution
GROUND_FILL = 0.9           # share of the depth where the ground meets the frame's bottom edge (low cameras)
FLOOR_HEIGHT = 3.3
WALLS = ["#c2b3a2", "#9aa3ad", "#a9705a", "#7d9391", "#d2c9b8", "#8a8482", "#b0a48c", "#6f7f98", "#c9a98a"]
LIT = ["#ffd98a", "#ffc46b", "#ffe9b8", "#fff4dc", "#ffb45e"]
NEON = ["#ff4f7a", "#39d6ff", "#ffd23f", "#7dff8a", "#ff8a3d", "#c77dff"]
SIGN = ["#c8412f", "#2f6fb0", "#e0b02a", "#2e8f6a", "#e8e2d2", "#30303a", "#d86a2a"]
CAR = ["#b3261e", "#e8e6e1", "#22262e", "#3a5f8a", "#8a8f96", "#d8b23a", "#2f5e4a"]
CLOTHES = ["#39465c", "#8a3b3b", "#d9d2c4", "#2f5a4a", "#b08a4a", "#5a4a6a", "#20232b", "#a85a2a"]


@dataclass
class CitySpec:
    width: int = 1280
    height: int = 896
    horizon: float = 0.60                 # fraction of the height
    vanish_x: float = 0.46                # fraction of the width (off-center reads less staged)
    focal: float = 0.80                   # focal length as a fraction of the width
    eye_height: float = 1.6
    road_half: float = 5.0
    sidewalk: float = 3.2
    time: str = "day"                     # day / golden / dusk / night
    sky: list = None                      # override sky stops [(y, color), ...]
    lit: float = None                     # share of lit windows; None = from time
    wet_road: float = 0.0                 # reflection strength on the road (rain)
    wires: bool = True
    signs: float = 1.0                    # density multipliers; 0 removes the element
    trees: float = 1.0
    cars: float = 1.0
    people: float = 1.0
    depth: float = 240.0                  # how far the street runs, m
    seed: int = 0


# sun = direction toward the sun (x right, y up, z away). strength 0 = no direct light.
TIMES = {
    "day": dict(sky=[(0, "#2f6cc0"), (0.65, "#8fbfea"), (1, "#dcebf5")], ambient=(0.60, 0.66, 0.80),
                sun_color=(1.00, 0.95, 0.84), strength=0.80, sun=(0.38, 0.70, 0.60), lit=0.03, haze="#cfe0ee",
                road="#5f6269", cloud=("#ffffff", "#a9b9d0"), lamp=0.0, stars=0.0),
    "golden": dict(sky=[(0, "#35579c"), (0.50, "#c9a28c"), (0.85, "#ffc98a"), (1, "#ffe6b0")],
                   ambient=(0.56, 0.54, 0.66), sun_color=(1.00, 0.72, 0.42), strength=1.0,
                   sun=(0.50, 0.42, 0.76), lit=0.14, haze="#f3c896", road="#56555e",
                   cloud=("#ffd9a8", "#8f86a8"), lamp=0.0, stars=0.0),
    "dusk": dict(sky=[(0, "#1d2a5c"), (0.45, "#6a4f96"), (0.8, "#f08a5d"), (1, "#ffd38a")],
                 ambient=(0.46, 0.43, 0.60), sun_color=(1.0, 0.6, 0.4), strength=0.0, sun=(0.1, 0.2, 1.0),
                 lit=0.55, haze="#e9a27c", road="#2f2f3c", cloud=("#ffb08a", "#5a4a7a"), lamp=1.0, stars=0.4),
    "night": dict(sky=[(0, "#060a1c"), (0.7, "#15224a"), (1, "#2c3a6a")], ambient=(0.20, 0.22, 0.34),
                  sun_color=(1, 1, 1), strength=0.0, sun=(0.1, 0.2, 1.0), lit=0.45, haze="#1e2a52",
                  road="#15161f", cloud=("#33406e", "#0c1230"), lamp=1.0, stars=1.0),
}


def _clip_rect(img, x0, y0, x1, y1):
    h, w = img.shape[:2]
    return max(int(x0), 0), max(int(y0), 0), min(int(x1), w), min(int(y1), h)


def _fill(img, x0, y0, x1, y1, value):
    x0, y0, x1, y1 = _clip_rect(img, x0, y0, x1, y1)
    if x1 > x0 and y1 > y0:
        img[y0:y1, x0:x1] = value


def _scale(img, x0, y0, x1, y1, factor):
    x0, y0, x1, y1 = _clip_rect(img, x0, y0, x1, y1)
    if x1 > x0 and y1 > y0:
        img[y0:y1, x0:x1] *= factor


class City:
    def __init__(self, spec=None):
        self.s = spec or CitySpec()
        s = self.s
        self.k = SUPERSAMPLE
        self.W, self.H = s.width * self.k, s.height * self.k
        self.cx, self.hy, self.f = s.vanish_x * self.W, s.horizon * self.H, s.focal * self.W
        self.t = dict(TIMES[s.time])
        if s.sky:
            self.t["sky"] = s.sky
        if s.lit is not None:
            self.t["lit"] = s.lit
        self.rng = np.random.default_rng(s.seed)
        self.edge = s.road_half + s.sidewalk
        self.sun = np.asarray(self.t["sun"], float) / np.linalg.norm(self.t["sun"])
        self.sunny = self.t["strength"] > 0.4
        self.glow = np.zeros((self.H, self.W, 3), np.float32)        # emissive light, bloomed at the end
        self.rows = self._plan_buildings()

    # ---- projection and light ----------------------------------------------
    def P(self, x, y, z):
        """Street space (x right, y up, z away; meters) to canvas pixels."""
        z = np.maximum(np.asarray(z, float), 0.5)
        return np.stack([self.cx + self.f * np.asarray(x, float) / z,
                         self.hy - self.f * (np.asarray(y, float) - self.s.eye_height) / z], -1)

    def px_per_m(self, z):
        return self.f / max(z, 0.5)

    def light(self, normal):
        """Light color falling on a surface with this normal (ambient sky + sun)."""
        t = self.t
        direct = max(0.0, float(np.dot(normal, self.sun))) * t["strength"]
        return np.asarray(t["ambient"], np.float32) + np.asarray(t["sun_color"], np.float32) * direct

    def haze_amount(self, z):
        return float(1 - np.exp(-z / (self.s.depth * 0.6)))

    def hazed(self, color, z):
        a = self.haze_amount(z)
        return np.asarray(color, np.float32) * (1 - a) + rgb(self.t["haze"]) * a

    def shadow_reach(self, height):
        """How far (m, toward -x) a wall of this height on the right side throws its shadow."""
        return height * self.sun[0] / self.sun[1]

    def in_shadow(self, x, y, z):
        """Is a point on the street shaded by the right-hand building row?"""
        if not self.sunny:
            return False
        travel = (self.edge - x) / self.sun[0]                    # along the ray toward the sun
        hit_y, hit_z = y + travel * self.sun[1], z + travel * self.sun[2]
        return any(side > 0 and z0 <= hit_z <= z0 + length and height >= hit_y
                   for z0, length, height, side, _, _ in self.rows)

    # ---- planning ---------------------------------------------------------
    def _plan_buildings(self):
        s, rng = self.s, self.rng
        kinds = ["masonry", "masonry", "office", "balcony", "strip"]
        rows = []
        for side in (-1, 1):
            z = 3.0
            while z < s.depth:
                length = rng.uniform(11, 26)
                height = rng.uniform(10, 24) * (1 + 2.4 * rng.random() ** 3)
                kind = kinds[rng.integers(len(kinds))]
                if height > 45:
                    kind = "office"
                if z < NEAR_Z and kind in ("office", "strip"):       # close to the camera, plain glass reads as an
                    kind, height = "masonry", min(height, 30.0)      # empty slab: use walls with windows and shops
                rows.append((z, length, height, side, rng.uniform(9, 18), kind))
                z += length + (rng.uniform(4, 8) if rng.random() < 0.14 else 0.0)     # occasional side street
        return rows

    # ---- facade drawings (flat, unlit) --------------------------------------
    def _window(self, tex, emit, x0, y0, x1, y1, panes, lit, frame, glass, bar):
        """One window: glass, frame, mullions, sill shadow. Lit windows also go to emit."""
        rng = self.rng
        if x1 - x0 < 3 or y1 - y0 < 3:
            return
        if lit:
            col = rgb(LIT[rng.integers(len(LIT))]) * rng.uniform(0.75, 1.05)
            grad = np.linspace(0.80, 1.06, max(int(y1) - int(y0), 1), dtype=np.float32)[:, None, None]
            xa, ya, xb, yb = _clip_rect(tex, x0, y0, x1, y1)
            if xb > xa and yb > ya:
                tex[ya:yb, xa:xb] = np.clip(col * grad[:yb - ya], 0, 1)
                if rng.random() < 0.35:                               # curtain half drawn
                    tex[ya:ya + (yb - ya) // 3, xa:xb] *= 0.72
                emit[ya:yb, xa:xb] = tex[ya:yb, xa:xb] * 0.55
        else:
            xa, ya, xb, yb = _clip_rect(tex, x0, y0, x1, y1)
            if xb > xa and yb > ya:                                   # sky reflection fades down the pane
                grad = np.linspace(1.45, 0.75, yb - ya, dtype=np.float32)[:, None, None]
                tex[ya:yb, xa:xb] = np.clip(glass * rng.uniform(0.8, 1.2) * grad, 0, 1)
            if rng.random() < 0.3:                                    # blind or curtain behind the glass
                _fill(tex, x0, y0, x1, y0 + (y1 - y0) * rng.uniform(0.3, 0.8), np.clip(glass * 0.5 + 0.38, 0, 1))
        for k in range(1, panes):
            xm = x0 + (x1 - x0) * k // panes
            _fill(tex, xm, y0, xm + bar, y1, frame); _fill(emit, xm, y0, xm + bar, y1, 0)
        for box in ((x0, y0, x1, y0 + bar), (x0, y1 - bar, x1, y1), (x0, y0, x0 + bar, y1), (x1 - bar, y0, x1, y1)):
            _fill(tex, *box, frame); _fill(emit, *box, 0)
        _scale(tex, x0 - bar, y1, x1 + bar, y1 + 2 * bar, 0.62)       # sill shadow

    def _shopfront(self, tex, emit, x0, x1, h, ppm, frame, glass):
        rng, t = self.rng, self.t
        top, bottom = h - int(2.9 * ppm), h - int(0.3 * ppm)
        lit = rng.random() < min(1.0, t["lit"] * 1.6 + 0.08)
        self._window(tex, emit, x0, top, x1, bottom, 3, lit, frame, glass, max(1, ppm // 8))
        if rng.random() < 0.6:                                        # awning or sign band
            col = rgb(SIGN[rng.integers(len(SIGN))])
            y0, y1 = h - int(3.5 * ppm), h - int(2.95 * ppm)
            _fill(tex, x0 - ppm // 4, y0, x1 + ppm // 4, y1, col)
            if rng.random() < 0.7:                                    # lettering suggested by blocks
                n = rng.integers(3, 8)
                for k in range(n):
                    bx = x0 + (x1 - x0) * (0.12 + 0.76 * k / n)
                    _fill(tex, bx, y0 + (y1 - y0) * 0.28, bx + (x1 - x0) * 0.5 / n, y1 - (y1 - y0) * 0.28,
                          np.clip(1.25 - col, 0, 1) if col.mean() < 0.55 else col * 0.25)
            if t["lamp"] > 0.5 and rng.random() < 0.7:
                xa, ya, xb, yb = _clip_rect(tex, x0, y0, x1, y1)
                emit[ya:yb, xa:xb] = tex[ya:yb, xa:xb] * 0.6
            _scale(tex, x0, y1, x1, y1 + ppm // 3, 0.7)               # shade under the awning

    def _facade(self, length, height, kind, ppm=PIXELS_PER_METER):
        """Draw one facade flat and unlit. Returns (albedo, emission)."""
        rng, t = self.rng, self.t
        w, h = max(8, int(length * ppm)), max(8, int(height * ppm))
        wall = np.clip(rgb(WALLS[rng.integers(len(WALLS))]) * rng.uniform(0.82, 1.08), 0, 1)
        tex = np.empty((h, w, 3), np.float32)
        tex[:] = wall
        # weathering: large stains plus streaks running down from the top
        stain = fbm(h, w, scale=90, octaves=4, seed=int(rng.integers(1 << 30)))
        streak = fbm(h, w, scale=26, octaves=3, seed=int(rng.integers(1 << 30)), stretch=0.12)
        tex *= (0.90 + 0.14 * stain + 0.06 * streak)[..., None]
        emit = np.zeros_like(tex)
        sky_top, sky_low = rgb(t["sky"][0][1]), rgb(t["sky"][-1][1])
        glass = np.clip(mix(sky_top, "#2a2c30", 0.76), 0, 1)          # daylight glass reads dark, faintly sky-tinted
        frame = np.clip(wall * 0.5, 0, 1) if rng.random() < 0.5 else np.clip(wall * 0.3 + 0.62, 0, 1)
        bar = max(1, ppm // 9)
        floor = FLOOR_HEIGHT if kind != "office" else 3.7
        floors = max(1, int(height / floor))
        ground = 1 if kind != "office" else 0                          # floors given to shops

        if kind == "office":                                          # curtain wall: glass panels in a grid
            bay = rng.uniform(1.4, 2.0)
            cols = max(2, int(length / bay))
            panel = fbm(floors * 2 + 2, cols + 2, scale=3.0, octaves=2, seed=int(rng.integers(1 << 30)))
            tint = rgb(["#6f8fb0", "#5f8a86", "#8794a8", "#4f6f9a"][rng.integers(4)])
            for fl in range(floors):
                y1 = h - int(fl * floor * ppm)
                y0 = h - int((fl + 1) * floor * ppm)
                # glass mirrors the sky: brighter and warmer high up, darker toward the street
                up = fl / max(floors - 1, 1)
                for c in range(cols):
                    x0, x1 = int(c * w / cols), int((c + 1) * w / cols)
                    refl = (sky_top * (1 - up) * 0.7 + sky_low * up) * 0.38 + tint * 0.20 + 0.16
                    refl = refl * (0.62 + 0.55 * panel[fl, c])
                    lit = rng.random() < t["lit"] * 0.8
                    if lit:
                        refl = rgb(LIT[rng.integers(len(LIT))]) * rng.uniform(0.7, 1.0)
                        _fill(emit, x0 + bar, y0 + int(0.9 * ppm), x1, y1, refl * 0.5)
                    _fill(tex, x0 + bar, y0 + int(0.9 * ppm), x1, y1, np.clip(refl, 0, 1))
                    _fill(tex, x0 + bar, y0, x1, y0 + int(0.9 * ppm), np.clip(tint * 0.45, 0, 1))   # spandrel
                    _fill(tex, x0, y0, x0 + bar, y1, frame * 0.8)
            # lobby: tall dark glazing between columns, with a canopy line above it
            lobby = h - int(4.6 * ppm)
            _fill(tex, 0, lobby, w, h, np.clip(glass * 0.9, 0, 1))
            for c in range(0, cols + 1, 3):
                xc = int(c * w / cols)
                _fill(tex, xc - int(0.3 * ppm), lobby, xc + int(0.3 * ppm), h, np.clip(wall * 1.05, 0, 1))
            _fill(tex, 0, lobby - int(0.35 * ppm), w, lobby, np.clip(wall * 0.9, 0, 1))
            if t["lit"] > 0.1:
                _fill(emit, 0, lobby + int(0.3 * ppm), w, h - int(0.3 * ppm), rgb(LIT[2]) * 0.25 * min(1.0, t["lit"] * 2))
                tex[lobby + int(0.3 * ppm):h - int(0.3 * ppm)] = np.clip(tex[lobby + int(0.3 * ppm):h - int(0.3 * ppm)] + rgb(LIT[2]) * 0.35 * min(1.0, t["lit"] * 2), 0, 1)
        else:
            bay = rng.uniform(2.6, 4.0)
            bays = max(1, int(length / bay))
            bw = w / bays
            win_w, win_h = rng.uniform(0.45, 0.72), rng.uniform(0.42, 0.62)
            for fl in range(ground, floors):
                base = h - int(fl * floor * ppm)
                y1 = base - int(0.22 * floor * ppm)
                y0 = y1 - int(floor * win_h * ppm)
                if kind == "balcony":
                    # recessed loggia band, door-height windows, slab edge and railing in front
                    _scale(tex, 0, base - int(floor * ppm * 0.92), w, base - int(0.12 * floor * ppm), 0.72)
                    y0, y1 = base - int(floor * ppm * 0.86), base - int(0.14 * floor * ppm)
                if kind == "strip":
                    self._window(tex, emit, int(0.4 * ppm), y0, w - int(0.4 * ppm), y1, max(2, bays * 2),
                                 rng.random() < t["lit"] * 0.5, frame, glass, bar)
                else:
                    for b in range(bays):
                        x0 = int(b * bw + bw * (1 - win_w) / 2)
                        self._window(tex, emit, x0, y0, int(x0 + bw * win_w), y1, 2,
                                     rng.random() < t["lit"], frame, glass, bar)
                if kind == "balcony":
                    slab = np.clip(wall * 1.12, 0, 1)
                    _fill(tex, 0, base - int(0.16 * floor * ppm), w, base - int(0.08 * floor * ppm), slab)
                    rail = base - int(0.42 * floor * ppm)
                    _fill(tex, 0, rail, w, rail + bar, frame)
                    for xk in range(0, w, max(2, ppm // 3)):
                        _fill(tex, xk, rail, xk + 1, base - int(0.16 * floor * ppm), frame)
                    _scale(tex, 0, base - int(0.08 * floor * ppm), w, base + bar, 0.6)
                    for b in range(bays):                              # air conditioner boxes
                        if rng.random() < 0.3:
                            ax = int(b * bw + bw * 0.08)
                            _fill(tex, ax, rail + 2 * bar, ax + int(0.8 * ppm), rail + int(0.6 * ppm), np.clip(wall * 0.2 + 0.7, 0, 1))
                else:
                    _scale(tex, 0, base - bar, w, base, 0.82)           # floor line
            for b in range(bays):                                      # ground floor shops
                self._shopfront(tex, emit, int(b * bw + bw * 0.07), int(b * bw + bw * 0.93), h, ppm, frame, glass)
            for xk in (0, w - int(0.35 * ppm)):                        # corner pilasters
                _scale(tex, xk, 0, xk + int(0.35 * ppm), h - int(3.6 * ppm), 1.08)
        # cornice: a light band with its shadow under it
        _scale(tex, 0, 0, w, int(0.55 * ppm), 1.12)
        _scale(tex, 0, int(0.55 * ppm), w, int(0.85 * ppm), 0.62)
        return np.clip(tex, 0, 1), emit

    def _shade_left_facade(self, tex, z0, length, height):
        """Shadow that the right-hand row throws across the street onto a left facade."""
        if not self.sunny:
            return
        h, w = tex.shape[:2]
        ppm = w / length
        travel = 2 * self.edge / self.sun[0]
        drop, shift = travel * self.sun[1], travel * self.sun[2]
        zs = z0 + (np.arange(w) + 0.5) / ppm + shift                  # where the ray came from on the right row
        top = np.zeros(w)
        for bz, blen, bh, side, _, _ in self.rows:
            if side > 0:
                top = np.where((zs >= bz) & (zs <= bz + blen), np.maximum(top, bh - drop), top)
        rows = (h - np.clip(top, 0, height) * ppm).astype(int)        # texture row where the shadow tops out
        ys = np.arange(h)[:, None]
        shaded = ys >= rows[None, :]
        lit, shade = self.light(np.array([1.0, 0, 0])), self.light(np.array([0, 0, -1.0]))
        tex[shaded] *= (shade / lit) * 0.92

    def _warp(self, canvas, tex, emit, quad):
        """Map a flat drawing onto a quad given as TL, TR, BR, BL canvas points."""
        h, w = tex.shape[:2]
        # pre-shrink to roughly the on-screen size: warping a far, tiny facade from the full
        # drawing would alias the window grid
        span = max(np.linalg.norm(quad[0] - quad[1]), np.linalg.norm(quad[1] - quad[2]),
                   np.linalg.norm(quad[3] - quad[2]), np.linalg.norm(quad[0] - quad[3]))
        scale = min(1.0, span * 1.5 / max(w, h))
        if scale < 1.0:
            size = (max(2, int(w * scale)), max(2, int(h * scale)))
            tex = cv2.resize(tex, size, interpolation=cv2.INTER_AREA)
            emit = cv2.resize(emit, size, interpolation=cv2.INTER_AREA) if emit is not None else None
            h, w = tex.shape[:2]
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        m = cv2.getPerspectiveTransform(src, np.float32(quad))
        x0, y0 = np.floor(np.clip(quad.min(0), 0, [self.W, self.H])).astype(int)
        x1, y1 = np.ceil(np.clip(quad.max(0), 0, [self.W, self.H])).astype(int)
        if x1 - x0 < 1 or y1 - y0 < 1:
            return
        shift = np.float64([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]]) @ m
        size = (int(x1 - x0), int(y1 - y0))
        warped = cv2.warpPerspective(tex, shift, size, flags=cv2.INTER_LINEAR)
        mask = cv2.warpPerspective(np.ones((h, w), np.float32), shift, size, flags=cv2.INTER_LINEAR)[..., None]
        region = canvas[y0:y1, x0:x1]
        region[...] = region * (1 - mask) + warped * mask
        g = self.glow[y0:y1, x0:x1]
        g *= (1 - mask)
        if emit is not None:
            g += cv2.warpPerspective(emit, shift, size, flags=cv2.INTER_LINEAR) * mask

    # ---- sky and far distance -----------------------------------------------
    def _sky(self):
        s, t = self.s, self.t
        img = vertical_gradient(int(self.hy) + 2, self.W, t["sky"])
        img = np.vstack([img, np.repeat(img[-1:], self.H - img.shape[0], 0)])
        if t["strength"] > 0:                                          # glow around the sun's bearing
            sx = self.cx + self.f * self.sun[0] / max(self.sun[2], 0.2)
            sy = self.hy - self.f * self.sun[1] / max(self.sun[2], 0.2)
            ys, xs = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
            d = np.hypot(xs - sx, ys - sy) / self.W
            img = img + (np.asarray(t["sun_color"], np.float32) - img) * (np.exp(-(d / 0.5) ** 1.3) * 0.45)[..., None]
        img = clouds(img, coverage=0.42, y_range=(0.0, s.horizon * 0.9), color=t["cloud"][0], shadow=t["cloud"][1],
                     seed=s.seed + 3, light=(0.4, 0.8), scale=0.26)
        if t["stars"] > 0:
            stars = (self.rng.random((self.H, self.W)) > 1 - 0.0008 * t["stars"]).astype(np.float32)
            fade = np.clip(1 - np.arange(self.H) / (self.hy * 0.6), 0, 1)[:, None]
            img = np.clip(img + (cv2.GaussianBlur(stars, (0, 0), 1.1) * 5 * fade)[..., None], 0, 1)
        return img.astype(np.float32)

    def _skyline(self, canvas):
        """Hazy towers beyond the end of the street: they close the vista and set the scale."""
        s, rng, t = self.s, self.rng, self.t
        haze = rgb(t["haze"])
        towers = sorted(((rng.uniform(s.depth * 1.3, s.depth * 3.2), rng.uniform(-110, 110), rng.uniform(12, 30),
                          rng.uniform(55, 180)) for _ in range(18)), key=lambda r: -r[0])
        for z, x, w, hgt in towers:
            a, b = self.P(x, hgt, z), self.P(x + w, 0, z)
            x0, y0, x1, y1 = _clip_rect(canvas, a[0], a[1], b[0], b[1])
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            near = 1 - (z - s.depth * 1.3) / (s.depth * 1.9)             # nearer towers are a little darker
            body = np.clip(haze * (0.80 - 0.16 * near) * (0.75 + 0.35 * np.asarray(t["ambient"])), 0, 1)
            fade = np.linspace(0.0, 0.55, y1 - y0, dtype=np.float32)[:, None, None]     # haze pools low
            block = body * (1 - fade) + haze * fade
            block = np.repeat(block, x1 - x0, 1)
            split = int((x1 - x0) * rng.uniform(0.55, 0.75))
            warm = np.asarray(t["sun_color"], np.float32) * t["strength"]
            block[:, :split] = np.clip(block[:, :split] * (1 + 0.10 * warm), 0, 1)       # sunlit face
            block[:, split:] *= 0.90
            step = max(3, int(self.f * 3.6 / z))
            block[::step] *= 0.93                                         # floor lines
            if t["lit"] > 0.3:
                on = rng.random(block.shape[:2]) > 0.985
                block[on] = rgb(LIT[rng.integers(len(LIT))]) * 0.85
            canvas[y0:y1, x0:x1] = block

    # ---- ground ---------------------------------------------------------------
    def _ground_plan(self, z_range, ppm):
        """Top-down drawing of the street between two distances: (plan, light pools)."""
        s, t, rng = self.s, self.t, self.rng
        edge = self.edge
        w, h = int(2 * edge * ppm), int((z_range[1] - z_range[0]) * ppm)
        X = lambda x: int((x + edge) * ppm)                           # plan column of a street x
        Z = lambda z: int(h - (z - z_range[0]) * ppm)                 # plan row (far = top)
        plan = np.empty((h, w, 3), np.float32)
        plan[:] = rgb("#9c9892")                                      # paving
        tile = max(2, int(1.2 * ppm))
        joint = max(1, int(ppm * 0.04))
        for r in range(0, h, tile):                                   # paving joints across and along
            plan[r:r + joint] *= 0.86
        for c in list(range(0, X(-s.road_half), tile)) + list(range(X(s.road_half), w, tile)):
            plan[:, c:c + joint] *= 0.90
        road = rgb(t["road"]) if self.t["strength"] == 0 else rgb("#6a6b70")
        plan[:, X(-s.road_half):X(s.road_half)] = road
        # asphalt: mottling, darker wheel tracks, a few repair patches
        rw = X(s.road_half) - X(-s.road_half)
        mott = fbm(h, rw, scale=4.0 * ppm, octaves=4, seed=s.seed + 21)
        grit = rng.normal(0, 0.035, (h, rw)).astype(np.float32)
        plan[:, X(-s.road_half):X(s.road_half)] *= (0.86 + 0.22 * mott + grit)[..., None]
        for lane in (-0.75, -0.25, 0.25, 0.75):
            c = X(lane * s.road_half * 0.92)
            plan[:, c - int(0.3 * ppm):c + int(0.3 * ppm)] *= 0.93
        for _ in range(int((z_range[1] - z_range[0]) / 14)):
            px, pz = rng.uniform(-s.road_half * 0.8, s.road_half * 0.5), rng.uniform(*z_range)
            _scale(plan, X(px), Z(pz + rng.uniform(1.5, 5)), X(px + rng.uniform(1, 2.6)), Z(pz), rng.uniform(0.78, 0.9))
        mark = rgb("#e8e3d4")
        for side in (-1, 1):                                          # curb and gutter
            c = X(side * s.road_half)
            _fill(plan, c - int(0.14 * ppm), 0, c + int(0.14 * ppm), h, rgb("#b8b3a8"))
            g = X(side * (s.road_half - 0.35))
            _scale(plan, min(c, g), 0, max(c, g), h, 0.86)
            e = X(side * (s.road_half - 0.75))
            _fill(plan, e - int(0.06 * ppm), 0, e + int(0.06 * ppm), h, mark * 0.9)
        for z in np.arange(10.0, z_range[1], 9.0):                    # center dashes
            _fill(plan, X(-0.08), Z(z + 4.0), X(0.08), Z(z), mark)
        if z_range[0] < 9:                                            # crosswalk and stop line
            for x in np.arange(-s.road_half + 0.9, s.road_half - 0.9, 1.1):
                _fill(plan, X(x), Z(9.0), X(x + 0.6), Z(5.6), mark)
            _fill(plan, X(0.3), Z(10.6), X(s.road_half - 0.8), Z(10.2), mark)
        plan *= self.light(np.array([0, 1.0, 0]))
        if self.sunny:                                                # shadows of the right-hand row
            shade = self.light(np.array([0, 0, -1.0])) / self.light(np.array([0, 1.0, 0])) * 0.9
            mask = np.zeros((h, w), np.float32)
            for bz, blen, bh, side, _, _ in self.rows:
                if side < 0:
                    continue
                reach = self.shadow_reach(bh)
                dz = reach * self.sun[2] / self.sun[0]
                poly = np.array([(X(edge), Z(bz)), (X(edge), Z(bz + blen)), (X(edge - reach), Z(bz + blen - dz)),
                                 (X(edge - reach), Z(bz - dz))], np.int32)
                cv2.fillPoly(mask, [poly], 1.0)
            mask = cv2.GaussianBlur(mask, (0, 0), 0.12 * ppm)[..., None]
            plan = plan * (1 - mask) + plan * shade * mask
        pools = np.zeros_like(plan)
        if t["lamp"] > 0:                                             # pools of lamp light
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            for z, side in self._lamp_positions():
                if z_range[0] - 8 < z < z_range[1] + 8:
                    d = np.hypot(xx - X(side * (s.road_half - 0.9)), yy - Z(z)) / (6.0 * ppm)
                    pools += (np.exp(-d * d * 2.2) * 0.42 * t["lamp"])[..., None] * np.array([1.0, 0.82, 0.55], np.float32)
        return np.clip(plan + pools * plan * 2.2 + pools * 0.25, 0, 1.5)

    def _ground(self, canvas):
        s = self.s
        # a low camera sees the ground closer than GROUND_NEAR at the bottom of the frame: start the plan there
        near = min(GROUND_NEAR[0], GROUND_FILL * self.f * s.eye_height / max(self.H - self.hy, 1.0))
        for z_range, ppm in (((near, GROUND_NEAR[1]), GROUND_PPM), ((GROUND_NEAR[1], s.depth * 2.2), 2.5)):
            plan = self._ground_plan(z_range, ppm)
            a = self.haze_amount((z_range[0] + z_range[1]) / 2) if z_range[0] > 50 else 0.0
            plan = plan * (1 - a) + rgb(self.t["haze"]) * a
            quad = np.array([self.P(-self.edge, 0, z_range[1]), self.P(self.edge, 0, z_range[1]),
                             self.P(self.edge, 0, z_range[0]), self.P(-self.edge, 0, z_range[0])])
            self._warp(canvas, plan.astype(np.float32), None, quad)
        ys = np.arange(self.H, dtype=np.float32)[:, None]             # haze thickens toward the horizon
        t_haze = np.clip(1 - (ys - self.hy) / (self.H * 0.07), 0, 1) ** 2 * (ys > self.hy)
        canvas[...] = canvas * (1 - t_haze[..., None] * 0.75) + rgb(self.t["haze"]) * t_haze[..., None] * 0.75

    # ---- buildings ------------------------------------------------------------
    def _buildings(self, canvas):
        edge = self.edge
        haze = rgb(self.t["haze"])
        for z0, length, height, side, depth, kind in sorted(self.rows, key=lambda r: -r[0]):     # far to near
            z1 = z0 + length
            a = self.haze_amount((z0 + z1) / 2)
            # wall facing the camera (seen above lower neighbors and at side streets): always unlit by the sun
            ppm = NEAR_PPM if z0 < NEAR_Z else PIXELS_PER_METER
            front, front_emit = self._facade(depth, height, "masonry" if kind == "office" else kind, ppm)
            front = front * self.light(np.array([0, 0, -1.0])) * 0.92
            front = front * (1 - a) + haze * a
            xs = sorted([edge * side, (edge + depth) * side])
            quad = np.array([self.P(xs[0], height, z0), self.P(xs[1], height, z0), self.P(xs[1], 0, z0), self.P(xs[0], 0, z0)])
            self._warp(canvas, np.clip(front, 0, 1).astype(np.float32), front_emit * (1 - a * 0.7), quad)
            # facade along the street
            tex, emit = self._facade(length, height, kind, ppm)
            tex = tex * self.light(np.array([-float(side), 0, 0]))
            if side < 0:
                self._shade_left_facade(tex, z0, length, height)
            tex = np.clip(tex, 0, 1) * (1 - a) + haze * a
            emit = emit * (1 - a * 0.7)
            near_top, far_top = self.P(edge * side, height, z0), self.P(edge * side, height, z1)
            near_bot, far_bot = self.P(edge * side, 0, z0), self.P(edge * side, 0, z1)
            if side < 0:                                              # texture u runs near -> far
                quad = np.array([near_top, far_top, far_bot, near_bot])
            else:
                quad = np.array([far_top, near_top, near_bot, far_bot])
                tex, emit = tex[:, ::-1], emit[:, ::-1]
            self._warp(canvas, np.ascontiguousarray(tex, np.float32), np.ascontiguousarray(emit), quad)

    # ---- props ----------------------------------------------------------------
    def _poly(self, canvas, pts, color, emit=None):
        p = np.round(np.asarray(pts) * 4).astype(np.int32)
        cv2.fillPoly(canvas, [p], tuple(float(c) for c in np.clip(color, 0, 1)), cv2.LINE_AA, shift=2)
        if emit is not None:
            cv2.fillPoly(self.glow, [p], tuple(float(c) for c in np.clip(emit, 0, 1)), cv2.LINE_AA, shift=2)

    def _line(self, canvas, a, b, color, width):
        cv2.line(canvas, tuple(np.round(np.asarray(a) * 4).astype(int)), tuple(np.round(np.asarray(b) * 4).astype(int)),
                 tuple(float(c) for c in np.clip(color, 0, 1)), max(1, int(round(width))), cv2.LINE_AA, shift=2)

    def _prop_light(self, x, z, normal=(0, 0.45, -0.9)):
        """Light on an upright prop, darker when the right-hand row shades it."""
        n = np.asarray(normal, float)
        if self.in_shadow(x, 1.0, z):
            return self.light(np.array([0, 0, -1.0]))
        return self.light(n / np.linalg.norm(n)) * 0.92 + 0.06

    def _lamp_positions(self):
        return [(z, side) for z in np.arange(self.s.depth, 15.0, -19.0) for side in (-1, 1)]

    def _draw_lamp(self, canvas, z, side):
        s, t = self.s, self.t
        x = side * (s.road_half + 0.45)
        pole = self.hazed(np.clip(rgb("#3f4048") * self._prop_light(x, z), 0, 1), z)
        base, top, arm = self.P(x, 0, z), self.P(x, 6.4, z), self.P(x - side * 1.6, 6.7, z)
        w = self.px_per_m(z) * 0.11
        self._line(canvas, base, top, pole, w)
        self._line(canvas, top, arm, pole, w * 0.8)
        r = max(1.0, self.px_per_m(z) * 0.17)
        head = self.P(x - side * 1.6, 6.62, z)
        on = t["lamp"] > 0.2
        cv2.circle(canvas, tuple(np.round(head * 4).astype(int)), int(r * 4),
                   (1.0, 0.95, 0.85) if on else tuple(float(c) for c in pole * 1.5), -1, cv2.LINE_AA, shift=2)
        if on:
            cv2.circle(self.glow, tuple(np.round(head * 4).astype(int)), int(r * 4),
                       tuple(float(c) for c in np.array([1.0, 0.86, 0.62]) * t["lamp"]), -1, cv2.LINE_AA, shift=2)

    def _draw_sign(self, canvas, z, side, rng):
        """Blade sign: a board standing out from the wall, facing along the street."""
        t = self.t
        x0 = side * self.edge
        reach, y0 = rng.uniform(0.7, 1.3), rng.uniform(3.2, 7.5)
        tall = rng.random() < 0.6
        hgt, wid = (rng.uniform(2.0, 5.0), reach) if tall else (rng.uniform(0.7, 1.2), reach * 1.5)
        x1 = x0 - side * wid
        col = rgb(SIGN[rng.integers(len(SIGN))])
        a, b = self.P(min(x0, x1), y0 + hgt, z), self.P(max(x0, x1), y0, z)
        quad = [a, (b[0], a[1]), b, (a[0], b[1])]
        lit = t["lamp"] > 0.5 and rng.random() < 0.75
        if lit:
            col = rgb(NEON[rng.integers(len(NEON))])
        shown = col if lit else col * self._prop_light(x1, z, (0, 0.2, -1))
        shown = self.hazed(np.clip(shown, 0, 1), z)
        self._poly(canvas, quad, shown, emit=col * 0.75 * (1 - self.haze_amount(z)) if lit else None)
        ink = np.clip(1.3 - col, 0, 1) if col.mean() < 0.5 else col * 0.25      # blocks standing in for lettering
        n = rng.integers(3, 6) if tall else 1
        for k in range(n):
            f0, f1 = (k + 0.2) / n, (k + 0.8) / n
            pa = (a[0] + (b[0] - a[0]) * 0.22, a[1] + (b[1] - a[1]) * f0)
            pb = (a[0] + (b[0] - a[0]) * 0.78, a[1] + (b[1] - a[1]) * f1)
            mark = ink if lit else self.hazed(np.clip(ink * self._prop_light(x1, z, (0, 0.2, -1)), 0, 1), z)
            self._poly(canvas, [pa, (pb[0], pa[1]), pb, (pa[0], pb[1])], mark)

    def _draw_tree(self, canvas, z, side, rng):
        """Street tree: many small leaf masses, each toned by how much it faces the sun."""
        s = self.s
        x = side * (s.road_half + 0.75)
        m = self.px_per_m(z)
        light = self._prop_light(x, z, (0.3, 0.8, -0.5))
        shade = self.light(np.array([0, 0, -1.0])) * 0.58
        trunk_h, crown = rng.uniform(2.7, 3.5), rng.uniform(1.25, 1.75)
        bark = self.hazed(np.clip(rgb("#4a3a30") * light * 0.85, 0, 1), z)
        fork = self.P(x + rng.uniform(-0.15, 0.15), trunk_h, z)
        self._line(canvas, self.P(x, 0, z), fork, bark, m * 0.20)
        center = np.array([0.0, trunk_h + crown * 0.8])
        for _ in range(3):                                            # limbs into the crown
            tip = self.P(x + rng.uniform(-crown, crown) * 0.6, center[1] + rng.uniform(-0.2, 0.5) * crown, z)
            self._line(canvas, fork, tip, bark, m * 0.10)
        leaf = rgb(["#4f7a3a", "#5e8a40", "#44703a", "#6a8f3c"][rng.integers(4)])
        ang, rad = rng.uniform(0, 2 * np.pi, 46), np.sqrt(rng.uniform(0, 1, 46))
        dx, dy = np.cos(ang) * rad * crown * 1.05, np.sin(ang) * rad * crown * 0.82
        # masses on the sun side and on top catch light; the underside stays dark
        facing = np.clip(0.45 + 0.55 * (dy / crown) + 0.45 * (dx / crown) * np.sign(self.sun[0]), 0, 1)
        for k in np.argsort(facing):                                  # dark masses first
            tone = shade + (light * 1.05 - shade) * facing[k] * rng.uniform(0.8, 1.1)
            c = self.P(x + dx[k], center[1] + dy[k], z)
            r = rng.uniform(0.28, 0.46) * crown * m
            cv2.circle(canvas, tuple(np.round(c * 4).astype(int)), max(int(r * 4), 4),
                       tuple(float(v) for v in self.hazed(np.clip(leaf * tone, 0, 1), z)), -1, cv2.LINE_AA, shift=2)

    def _draw_person(self, canvas, x, z, rng):
        m = self.px_per_m(z)
        hgt = rng.uniform(1.58, 1.84)
        light = self._prop_light(x, z)
        top, pants = rgb(CLOTHES[rng.integers(len(CLOTHES))]), rgb(CLOTHES[rng.integers(len(CLOTHES))]) * 0.7
        skin = rgb(["#e8c4a6", "#d9ac8a", "#b98a68"][rng.integers(3)])
        tone = lambda c: self.hazed(np.clip(c * light, 0, 1), z)
        stride = rng.uniform(-0.16, 0.16)
        hip, sh = hgt * 0.50, hgt * 0.82
        for sgn in (-1, 1):                                           # legs, then arms
            self._line(canvas, self.P(x + sgn * 0.07, hip, z), self.P(x + sgn * (0.07 + stride), 0.02, z), tone(pants), m * 0.15)
        self._poly(canvas, [self.P(x - 0.19, sh, z), self.P(x + 0.19, sh, z), self.P(x + 0.15, hip - 0.04, z),
                            self.P(x - 0.15, hip - 0.04, z)], tone(top))
        for sgn in (-1, 1):
            self._line(canvas, self.P(x + sgn * 0.20, sh - 0.03, z), self.P(x + sgn * (0.23 - stride * 0.5), hip + 0.05, z),
                       tone(top * 0.9), m * 0.10)
        head = self.P(x, sh + 0.17, z)
        cv2.ellipse(canvas, tuple(np.round(head * 4).astype(int)), (int(m * 0.105 * 4), int(m * 0.125 * 4)), 0, 0, 360,
                    tuple(float(c) for c in tone(skin)), -1, cv2.LINE_AA, shift=2)
        hair = self.P(x, sh + 0.215, z)
        cv2.ellipse(canvas, tuple(np.round(hair * 4).astype(int)), (int(m * 0.112 * 4), int(m * 0.10 * 4)), 0, 180, 360,
                    tuple(float(c) for c in tone(rgb("#2a2420"))), -1, cv2.LINE_AA, shift=2)
        if self.sunny and not self.in_shadow(x, 0.1, z):               # cast shadow on the pavement
            tip = self.P(x - hgt * self.sun[0] / self.sun[1], 0, z - hgt * self.sun[2] / self.sun[1])
            base_l, base_r = self.P(x - 0.16, 0, z), self.P(x + 0.16, 0, z)
            layer = canvas.copy()
            self._poly(layer, [base_l, base_r, tip + [m * 0.12, 0], tip - [m * 0.12, 0]], layer[int(np.clip(base_l[1], 0, self.H - 1)), int(np.clip(base_l[0], 0, self.W - 1))] * 0.55)
            canvas[...] = layer

    def _draw_car(self, canvas, x, z, rng, away=True, moving=False):
        """A sedan as two boxes (body, cabin). The side toward the street axis and the near end show."""
        t = self.t
        w, length, sill, belt, roof = 1.78, 4.3, 0.28, 0.95, 1.42
        paint = rgb(CAR[rng.integers(len(CAR))]) * 0.88
        lit, shade = self._prop_light(x, z, (0, 0.5, -0.85)), self.light(np.array([0, 0, -1.0]))
        side_light = self.light(np.array([-np.sign(x), 0.25, 0.0]) / 1.03) if not self.in_shadow(x, 1, z) else shade
        tone = lambda c, l: self.hazed(np.clip(np.asarray(c) * l, 0, 1), z)
        xi, xo = x - np.sign(x) * w / 2, x + np.sign(x) * w / 2        # side toward the axis / toward the curb
        z0, z1 = z, z + length
        c0, c1 = z0 + (1.05 if away else 1.45), z1 - (1.45 if away else 1.05)   # cabin span
        glass = np.clip(rgb(t["sky"][0][1]) * 0.55 + 0.08, 0, 1)
        # contact shadow, then far-to-near: side, cabin side, roof, near end
        self._poly(canvas, [self.P(xi - 0.15 * np.sign(xi - xo), 0, z0 - 0.1), self.P(xo, 0, z0 - 0.1), self.P(xo, 0, z1 + 0.1),
                            self.P(xi - 0.15 * np.sign(xi - xo), 0, z1 + 0.1)], tone(rgb(t["road"]), 0.35))
        self._poly(canvas, [self.P(xi, belt, z0), self.P(xi, belt, z1), self.P(xi, sill, z1), self.P(xi, sill, z0)], tone(paint, side_light))
        self._poly(canvas, [self.P(xi, roof, c0 + 0.35), self.P(xi, roof, c1 - 0.45), self.P(xi, belt, c1), self.P(xi, belt, c0)],
                   tone(glass, 1.0))
        self._poly(canvas, [self.P(xi, roof, c0 + 0.35), self.P(xo, roof, c0 + 0.35), self.P(xo, roof, c1 - 0.45), self.P(xi, roof, c1 - 0.45)],
                   tone(paint, lit * 1.08))
        self._poly(canvas, [self.P(xi, belt, z0), self.P(xo, belt, z0), self.P(xo, belt, c0), self.P(xi, belt, c0)], tone(paint, lit * 1.02))
        for wz in (z0 + 0.85, z1 - 0.85):                             # wheels on the visible side
            ang = np.linspace(0, 2 * np.pi, 20)
            self._poly(canvas, self.P(np.full(20, xi), 0.33 + 0.33 * np.sin(ang), wz + 0.33 * np.cos(ang)), tone(rgb("#16161a"), 1.0))
        self._poly(canvas, [self.P(xi, belt, z0), self.P(xo, belt, z0), self.P(xo, sill, z0), self.P(xi, sill, z0)], tone(paint, shade * 0.95))
        self._poly(canvas, [self.P(xi, sill + 0.20, z0), self.P(xo, sill + 0.20, z0), self.P(xo, sill, z0), self.P(xi, sill, z0)],
                   tone(rgb("#1c1c20"), 1.0))                                # bumper
        inset = 0.14
        self._poly(canvas, [self.P(xi + inset * np.sign(xo - xi), roof, c0 + 0.35), self.P(xo - inset * np.sign(xo - xi), roof, c0 + 0.35),
                            self.P(xo, belt, z0 + 0.25), self.P(xi, belt, z0 + 0.25)], tone(glass, 0.9))
        lamp = (1.0, 0.16, 0.12) if away else (1.0, 0.95, 0.8)
        on = t["lamp"] > 0.2 and (moving or away is False)
        for lx in (xi + 0.12 * np.sign(xo - xi), xo - 0.42 * np.sign(xo - xi)):
            q = [self.P(lx, belt - 0.12, z0), self.P(lx + 0.30 * np.sign(xo - xi), belt - 0.12, z0),
                 self.P(lx + 0.30 * np.sign(xo - xi), belt - 0.30, z0), self.P(lx, belt - 0.30, z0)]
            self._poly(canvas, q, np.array(lamp) * (1.0 if on else 0.55), emit=np.array(lamp) * 0.9 if on else None)

    def _draw_signal(self, canvas, z):
        s, t = self.s, self.t
        x = s.road_half + 0.5
        dark = self.hazed(np.clip(rgb("#33343c") * self._prop_light(x, z), 0, 1), z)
        m = self.px_per_m(z)
        self._line(canvas, self.P(x, 0, z), self.P(x, 5.6, z), dark, m * 0.16)
        self._line(canvas, self.P(x, 5.5, z), self.P(x - 4.2, 5.7, z), dark, m * 0.11)
        box_a, box_b = self.P(x - 4.6, 6.15, z), self.P(x - 3.4, 5.75, z)
        self._poly(canvas, [box_a, (box_b[0], box_a[1]), box_b, (box_a[0], box_b[1])], dark * 0.7)
        for k, col in enumerate(((1.0, 0.2, 0.15), (0.35, 0.3, 0.1), (0.1, 0.3, 0.2))):
            c = self.P(x - 4.4 + 0.4 * k, 5.95, z)
            cv2.circle(canvas, tuple(np.round(c * 4).astype(int)), int(m * 0.13 * 4), col, -1, cv2.LINE_AA, shift=2)
            if k == 0:
                cv2.circle(self.glow, tuple(np.round(c * 4).astype(int)), int(m * 0.13 * 4), (0.9, 0.15, 0.1), -1, cv2.LINE_AA, shift=2)

    def _draw_wires(self, canvas, z0, z1):
        x = -(self.edge - 0.7)
        color = tuple(float(c) for c in self.hazed(np.array([0.10, 0.10, 0.13]), z0))
        u = np.linspace(0, 1, 24)
        for dx, y in ((-0.85, 8.6), (0.0, 8.6), (0.85, 8.6), (-0.8, 7.9), (0.8, 7.9)):
            zz = z0 + (z1 - z0) * u
            yy = y - 1.1 * 4 * u * (1 - u)                             # sag between poles
            p = np.round(self.P(np.full_like(u, x + dx), yy, zz) * 4).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(canvas, [p], False, color, max(1, int(self.px_per_m(z0) * 0.035)), cv2.LINE_AA, shift=2)

    def _draw_pole(self, canvas, z):
        x = -(self.edge - 0.7)
        color = self.hazed(np.clip(rgb("#5a5048") * self._prop_light(x, z), 0, 1), z)
        m = self.px_per_m(z)
        self._line(canvas, self.P(x, 0, z), self.P(x, 9.0, z), color, m * 0.2)
        for y in (8.6, 7.9):
            self._line(canvas, self.P(x - 0.9, y, z), self.P(x + 0.9, y, z), color, m * 0.09)

    def _props(self, canvas):
        s, rng = self.s, self.rng
        items = []                                                    # (distance, draw function)
        for z, side in self._lamp_positions():
            items.append((z, lambda c, z=z, side=side: self._draw_lamp(c, z, side)))
        for z0, length, height, side, _, kind in self.rows:
            for _ in range(int(rng.poisson(length / 5.0 * s.signs)) if kind != "office" else 0):
                z = z0 + rng.uniform(0.5, length - 0.5)
                if z > 9:
                    sub = np.random.default_rng(int(rng.integers(1 << 30)))
                    items.append((z, lambda c, z=z, side=side, sub=sub: self._draw_sign(c, z, side, sub)))
        if s.trees > 0:
            for side in (-1, 1):
                for z in np.arange(21.0 + (5 if side > 0 else 0), s.depth * 0.8, 12.0 / s.trees):
                    sub = np.random.default_rng(int(rng.integers(1 << 30)))
                    items.append((z + 0.01, lambda c, z=z, side=side, sub=sub: self._draw_tree(c, z, side, sub)))
        if s.cars > 0:
            for side in (-1, 1):                                      # parked along both curbs
                z = 17.0
                while z < s.depth * 0.6:
                    if rng.random() < 0.6 * s.cars:
                        sub = np.random.default_rng(int(rng.integers(1 << 30)))
                        items.append((z, lambda c, z=z, side=side, sub=sub: self._draw_car(c, side * (s.road_half - 1.9), z, sub, away=side > 0)))
                    z += rng.uniform(5.2, 7.5)
            for lane, away in ((s.road_half * 0.28, True), (-s.road_half * 0.28, False)):
                for z in 26 + np.cumsum(rng.uniform(9, 30, int(3 * s.cars))):      # spaced so they never overlap
                    sub = np.random.default_rng(int(rng.integers(1 << 30)))
                    items.append((z, lambda c, z=z, lane=lane, away=away, sub=sub: self._draw_car(c, lane, z, sub, away=away, moving=True)))
        for _ in range(int(26 * s.people)):
            z = rng.uniform(22, s.depth * 0.55)
            x = rng.choice((-1, 1)) * rng.uniform(s.road_half + 1.2, self.edge - 0.6)
            sub = np.random.default_rng(int(rng.integers(1 << 30)))
            items.append((z, lambda c, z=z, x=x, sub=sub: self._draw_person(c, x, z, sub)))
        items.append((13.5, lambda c: self._draw_signal(c, 13.5)))
        if s.wires:
            poles = np.arange(11.0, s.depth, 29.0)
            for z in poles:
                items.append((z, lambda c, z=z: self._draw_pole(c, z)))
            for z0, z1 in zip(poles[:-1], poles[1:]):
                items.append((z0 - 0.01, lambda c, z0=z0, z1=z1: self._draw_wires(c, z0, z1)))
        for _, draw in sorted(items, key=lambda it: -it[0]):          # far to near
            draw(canvas)

    def _wet_road(self, canvas):
        s = self.s
        if s.wet_road <= 0:
            return
        hy = int(self.hy)
        depth = self.H - hy
        above = (canvas + self.glow * 1.2)[max(0, hy - depth):hy][::-1]
        if above.shape[0] < depth:
            above = np.vstack([above, np.repeat(above[-1:], depth - above.shape[0], 0)])
        refl = cv2.GaussianBlur(above, (0, 0), sigmaX=2.0 * self.k, sigmaY=14.0 * self.k)
        rows = np.arange(depth, dtype=np.float32)[:, None]
        xs = np.arange(self.W, dtype=np.float32)[None, :]
        half = self.f * s.road_half / np.maximum(self.f * s.eye_height / np.maximum(rows, 1.0), 0.5)   # road half width per row
        on_road = np.clip((half - np.abs(xs - self.cx)) / (2.0 * self.k), 0, 1)
        streak = 0.75 + 0.25 * fbm(depth, self.W, scale=90 * self.k, octaves=3, seed=s.seed + 9, stretch=0.25)
        a = (on_road * streak * s.wet_road)[..., None]
        canvas[hy:] = np.clip(canvas[hy:] * (1 - a * 0.55) + refl * a, 0, 1)

    # ---- assembly ---------------------------------------------------------
    def build(self):
        """Returns (image, glow): float RGB at the requested size. glow holds emissive light
        (windows, signs, lamps) for a bloom pass."""
        canvas = self._sky()
        self._skyline(canvas)
        self._ground(canvas)
        self._buildings(canvas)
        self._wet_road(canvas)
        self._props(canvas)
        size = (self.s.width, self.s.height)
        img = cv2.resize(np.clip(canvas, 0, 1), size, interpolation=cv2.INTER_AREA)
        glow = cv2.resize(np.clip(self.glow, 0, 1), size, interpolation=cv2.INTER_AREA)
        return img.astype(np.float32), glow.astype(np.float32)


def build_city(spec=None):
    """Street scene as a finished reference picture with its own light bloom applied."""
    img, glow = City(spec).build()
    halo = cv2.GaussianBlur(glow, (0, 0), 5) * 0.75 + cv2.GaussianBlur(glow, (0, 0), 24) * 0.6
    return np.clip(1 - (1 - img) * (1 - np.clip(halo, 0, 1)), 0, 1).astype(np.float32)
