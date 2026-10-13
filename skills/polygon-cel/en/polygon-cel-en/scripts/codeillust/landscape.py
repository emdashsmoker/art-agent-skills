"""Landscape: sky, layered mountain ranges, lake with reflections, meadow, trees.

Depth is carried by atmospheric perspective: each range farther away is
mixed further toward the horizon sky color and loses line weight and
contrast, the classic aerial-perspective rule of landscape painting. The
lake mirrors the ranges about the waterline and darkens toward the viewer.
"""
import numpy as np

from . import color as col
from . import geom, raster, shapes
from .scene import Blend, Layer, Light, LineSpec, Material, ShadeSpec

HORIZON = 0.52          # waterline as a fraction of canvas height
SHORE = 0.74            # meadow begins below this line
TIMES = {
    "day":    {"sky": ("#5E95D0", "#BFD8EE", "#EAF2F8"), "key": (-0.62, -0.55, 0.55), "key_color": "#FFF6E8",
               "rim": "#FFF0D0", "range": "#5B6E8C", "grass": "#7FA64E", "water": "#4F7FB0"},
    "sunset": {"sky": ("#34406E", "#D9827A", "#F7C98A"), "key": (-0.85, -0.12, 0.50), "key_color": "#FFC890",
               "rim": "#FFB070", "range": "#5A4E70", "grass": "#6E8A48", "water": "#4A4E78"},
    "misty":  {"sky": ("#8C9BAE", "#C9D2DC", "#E6EAEE"), "key": (-0.45, -0.70, 0.55), "key_color": "#F4F4F0",
               "rim": "#E8ECF0", "range": "#6A7686", "grass": "#76905E", "water": "#7D8EA2"},
    # moonlight from the upper right: dark ranges, dim snow, a moon and stars in the sky
    "night":  {"sky": ("#0B1026", "#1C2648", "#34426A"), "key": (0.55, -0.60, 0.55), "key_color": "#AFC2EE",
               "rim": "#9DB2E6", "range": "#232C46", "grass": "#24382E", "water": "#18223E", "snow": "#7F8DAE",
               "flowers": "#8C96B0", "cloud": "#4A5678"},
}
SNOW = "#F6F8FB"
MOON = {"x": 0.27, "y": 0.15, "r": 0.028, "glow": 0.16, "color": "#F2F0E0", "halo": "#8EA4D8"}   # canvas fractions
STARS = 220


class LandscapeBuilder:
    def __init__(self, spec, W, H, light, seed):
        self.s = spec
        self.W, self.H = W, H
        self.t = TIMES[spec.get("time", "day")]
        self.light = light
        self.seed = seed
        self.rng = np.random.default_rng(seed + 307)
        self.yh = HORIZON * H
        self.ys = SHORE * H
        self.sky_h = col.hex_rgb(self.t["sky"][2])
        self.lw = H * 0.0026

    # ------------------------------------------------------------ sky
    def sky(self):
        W, H = self.W, self.H
        top, mid, hor = (col.hex_rgb(c) for c in self.t["sky"])
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None] / HORIZON
        t1 = np.clip(y * 1.6, 0, 1) ** 0.9
        t2 = np.clip((y - 0.62) / 0.38, 0, 1)
        img = top * (1 - t1) + mid * t1
        img = img * (1 - t2) + hor * t2
        img = np.broadcast_to(img, (H, W, 3)).astype(np.float32).copy()
        if self.s.get("time", "day") == "night":
            img = self.night_sky(img)
        if self.s.get("time", "day") == "sunset":
            k = self.light.key_screen()
            sx, sy = W * (0.5 + 0.30 * np.sign(k[0])), self.yh - 0.06 * H
            yy2, xx2 = np.mgrid[0:H, 0:W].astype(np.float32)
            r = np.sqrt((xx2 - sx) ** 2 + (yy2 - sy) ** 2)
            img = raster.screen(img, col.hex_rgb("#FFE6B0"), np.exp(-(r / (0.18 * W)) ** 2) * 0.8)
            img = raster.over(img, col.hex_rgb("#FFF4DA"), np.clip((0.032 * W - r) / 2.0, 0, 1))
        return img

    def night_sky(self, img):
        """Stars fading toward the horizon, a moon on the key-light side with a cold halo."""
        W, H = self.W, self.H
        rng = np.random.default_rng(self.seed + 311)
        pts = np.column_stack([rng.uniform(0, W, STARS), H * HORIZON * rng.uniform(0, 1, STARS) ** 1.6])
        fade = 1 - pts[:, 1] / (H * HORIZON)
        stars = raster.Rasterizer(W, H).circles(pts, rng.uniform(0.4, 1.3, STARS) * H / 960 * (0.4 + 0.6 * fade))
        img = raster.screen(img, col.hex_rgb("#FFFFFF"), stars * 0.8)
        k = self.light.key_screen()
        mx, my = W * (0.5 + MOON["x"] * np.sign(k[0] or 1.0)), H * MOON["y"]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
        img = raster.screen(img, col.hex_rgb(MOON["halo"]), np.exp(-(r / (MOON["glow"] * W)) ** 2) * 0.55)
        return raster.over(img, col.hex_rgb(MOON["color"]), np.clip((MOON["r"] * W - r) / 1.5, 0, 1))

    def clouds(self):
        """Cumulus as clusters of round puffs on a flat base, shaded like solids."""
        W, H = self.W, self.H
        rng = self.rng
        n = int(self.s.get("clouds", 3))
        layers = []
        top, mid, hor = (col.hex_rgb(c) for c in self.t["sky"])
        # night clouds are moonlit grey, not the bright tops of day cumulus
        white = col.hex_rgb(self.t["cloud"]) if "cloud" in self.t else col.light_of(hor, 0.7, self.t["key_color"])
        shade = col.mix(col.mix(mid, top, 0.35), hor, 0.35)
        xs = np.linspace(0.12, 0.88, n) + rng.uniform(-0.06, 0.06, n)
        for i, x in enumerate(xs):
            base = H * rng.uniform(0.17, 0.30)
            width = W * rng.uniform(0.14, 0.24) * (1.0 - 0.25 * (base / H - 0.17) / 0.13)
            puffs = []
            for _ in range(16):
                u = rng.uniform(-1, 1)
                r = width * (0.10 + 0.16 * (1 - u * u)) * rng.uniform(0.8, 1.2)
                cx = x * W + u * width * 0.5
                cy = base - r * rng.uniform(0.2, 0.9) - width * 0.12 * (1 - u * u)
                puffs.append(geom.ellipse(cx, cy, r * 1.1, r, 32))
            puffs.append(np.array([(x * W - width * 0.55, base), (x * W + width * 0.55, base),
                                   (x * W + width * 0.45, base - width * 0.08), (x * W - width * 0.45, base - width * 0.08)]))
            normals = shapes.mask_normals(puffs, W, H, radius=width * 0.10, noise=0.0)
            layers.append(Layer(f"cloud{i}", Material.CLOTH, white, polys=puffs, line=LineSpec(self.lw * 0.5, alpha=0.35),
                                shade=ShadeSpec(normal_map=normals, threshold=0.05, gradient=(0.0, 0.35),
                                                shadow=col.rgb_hex(shade), rim=0.6),
                                tags=("cloud",)))
        return layers

    # ------------------------------------------------------------ mountains
    def range_poly(self, base_y, height, rough, seed, peaks):
        n = 256
        r = shapes.ridge(n, rough, seed, peaks)
        xs = np.linspace(-0.02 * self.W, 1.02 * self.W, n)
        ridge_y = base_y - r * height
        return np.vstack([np.column_stack([xs, ridge_y]), [(xs[-1], base_y + 4), (xs[0], base_y + 4)]]), ridge_y, xs

    def ranges(self):
        W, H = self.W, self.H
        base = col.hex_rgb(self.t["range"])
        haze = self.sky_h
        specs = [  # (height, haze, roughness, line, snow, peaks)
            (0.24, 0.62, 0.55, False, True, [(0.28, 1.0), (0.62, 0.8), (0.88, 0.6)]),
            (0.17, 0.34, 0.58, True, True, [(0.15, 0.7), (0.47, 1.0), (0.80, 0.55)]),
            (0.075, 0.12, 0.62, True, False, [(0.30, 0.6), (0.75, 1.0)]),
        ]
        layers, mirrors = [], []
        for i, (hgt, hz, rough, line, snow, peaks) in enumerate(specs):
            poly, ridge_y, xs = self.range_poly(self.yh, hgt * H, rough, self.seed + 31 * i, peaks)
            if i == 2:
                color = col.mix(col.hex_rgb(self.t["grass"]), base, 0.45)
                color = col.shadow_of(color, 0.25)
            else:
                color = col.mix(base, haze, hz)
            normals = shapes.mask_normals([poly], W, H, radius=0.06 * H, noise=6.0 + 4 * i, scale=0.05 * W,
                                          seed=self.seed + i)
            name = f"range{i}"
            layers.append(Layer(name, Material.CLOTH, color, polys=[poly],
                                line=LineSpec(self.lw * (0.6 + 0.4 * i)) if line else None,
                                shade=ShadeSpec(normal_map=normals, threshold=0.20 + 0.05 * i, rim=0.6,
                                                shadow=col.rgb_hex(col.mix(col.shadow_of(color, 0.22, "#303870", 0.05, 0.1),
                                                                           haze, hz * 0.5))),
                                tags=("range", "focus") if i else ("range",)))
            if snow:
                # snow lies above an absolute altitude, deeper in gullies (noise)
                n2 = raster.noise(1, len(xs), 5, self.seed + 77 + i, octaves=4)[0]
                snow_line = self.yh - hgt * H * (0.62 + 0.10 * i) + (n2 - 0.5) * hgt * H * 0.30
                snow_line = np.maximum(snow_line, ridge_y)
                cap = np.vstack([np.column_stack([xs, ridge_y - 2]), np.column_stack([xs[::-1], snow_line[::-1]])])
                white = col.mix(col.hex_rgb(self.t.get("snow", SNOW)), haze, hz * 0.6)
                layers.append(Layer(f"{name}_snow", Material.CLOTH, white, polys=[cap], clip=(name,),
                                    shade=ShadeSpec(normal_map=normals, threshold=0.25, rim=0.8),
                                    tags=("range",)))
            if i == 2:
                layers += self.conifers(xs, ridge_y, color)
            mirrors.append((poly, color))
        return layers, mirrors

    def conifers(self, xs, ridge_y, hill_color):
        H = self.H
        rng = self.rng
        trees = []
        for x in rng.uniform(0, self.W, 140):
            y = np.interp(x, xs, ridge_y) + rng.uniform(0.003, 0.05) * H
            if y > self.yh - 2:
                continue
            h = rng.uniform(0.022, 0.040) * H
            w = h * 0.38
            pts = []
            for tier in range(3):
                ty = y - h * tier * 0.28
                tw = w * (1 - tier * 0.25)
                pts.append(np.array([(x - tw, ty), (x + tw, ty), (x, ty - h * 0.55)]))
            trees += pts
        green = col.shadow_of(col.hex_rgb(self.t["grass"]), 0.42, "#203850", 0.05, 0.2)
        return [Layer("conifers", Material.CLOTH, green, polys=trees, clip=(), line=LineSpec(self.lw * 0.6),
                      shade=ShadeSpec(inflate=0.006 * H, threshold=0.15, rim=0.6), tags=("focus",))]

    # ------------------------------------------------------------ water
    def lake(self, mirrors):
        W, H = self.W, self.H
        xs = np.linspace(-5, W + 5, 64)
        shore = self.ys + 0.025 * H * np.sin(xs / W * 7 + 1.3) + 0.012 * H * np.sin(xs / W * 19)
        water = np.vstack([[(-5, self.yh), (W + 5, self.yh)], np.column_stack([xs[::-1], shore[::-1]])])
        far = col.mix(col.hex_rgb(self.t["water"]), self.sky_h, 0.55)
        near = col.shadow_of(col.hex_rgb(self.t["water"]), 0.15)
        layers = [Layer("lake", Material.FLAT, far, polys=[water], gradient_fill=((0, self.yh), (0, self.ys), far, near),
                        tags=("lake", "focus"))]
        for i, (poly, color) in enumerate(mirrors):
            P = poly.copy()
            P[:, 1] = 2 * self.yh - P[:, 1]
            refl = col.mix(col.shadow_of(color, 0.18, "#203060", 0.04, 0.1), col.hex_rgb(self.t["water"]), 0.25)
            layers.append(Layer(f"reflection{i}", Material.FLAT, refl, polys=[P], clip=("lake",),
                                feather=H * 0.003, opacity=0.75 - 0.1 * (2 - i)))
        ripples = []
        for _ in range(170):
            y = self.rng.uniform(self.yh + 2, self.ys)
            depth = (y - self.yh) / (self.ys - self.yh)
            x = self.rng.uniform(0, W)
            L = (0.01 + 0.05 * depth) * W
            ripples.append((np.array([(x, y), (x + L, y)]), geom.tapered_widths(2, H * (0.0010 + 0.0025 * depth), 0, 0)
                            + 0.5))
        layers.append(Layer("ripples", Material.INK, col.light_of(self.sky_h, 0.4), strokes=ripples, clip=("lake",),
                            opacity=0.55))
        line = np.array([(-5, self.yh), (W + 5, self.yh)])
        layers.append(Layer("waterline", Material.INK, col.light_of(self.sky_h, 0.5),
                            strokes=[(line, np.full(2, H * 0.0018))], opacity=0.7))
        return layers, shore, xs

    # ------------------------------------------------------------ foreground
    def meadow(self, shore, xs):
        W, H = self.W, self.H
        grass = col.hex_rgb(self.t["grass"])
        ground = np.vstack([np.column_stack([xs, shore]), [(W + 5, H + 5), (-5, H + 5)]])
        layers = [Layer("meadow", Material.CLOTH, grass, polys=[ground], line=LineSpec(self.lw),
                        shade=ShadeSpec(normal_map=shapes.height_normals(W, H, 0.06 * W, 5.0, self.seed + 9,
                                                                          base=(0.0, -0.8, 0.6)),
                                        threshold=0.22, gradient=(0.0, 0.25), rim=0.0),
                        tags=("ground", "focus"))]
        rng = self.rng
        blades, flowers = [], []
        for _ in range(900):
            y = rng.uniform(self.ys + 0.01 * H, H)
            depth = (y - self.ys) / (H - self.ys)
            x = rng.uniform(0, W)
            L = (0.008 + 0.035 * depth ** 1.5) * H
            lean = rng.uniform(-0.4, 0.4)
            tip = np.array([x + lean * L, y - L])
            blades.append((geom.bezier((x, y), (x, y - L * 0.5), (x + lean * L * 0.5, y - L * 0.8), tip, 6),
                           geom.tapered_widths(6, (0.0015 + 0.004 * depth) * H, 0.0, 0.9)))
            if rng.random() < 0.06:
                r = (0.002 + 0.006 * depth) * H
                flowers.append(geom.ellipse(tip[0], tip[1], r, r * 0.8, 12))
        dark = col.shadow_of(grass, 0.30, "#204060", 0.05, 0.2)
        light = col.light_of(grass, 0.25)
        half = len(blades) // 2
        flower_color = self.s.get("flowers", self.t.get("flowers", "#F4F0E0"))
        layers += [Layer("grass_dark", Material.INK, dark, strokes=blades[:half], clip=("meadow",), opacity=0.8),
                   Layer("grass_light", Material.INK, light, strokes=blades[half:], clip=("meadow",), opacity=0.7),
                   Layer("wildflowers", Material.FLAT, col.hex_rgb(flower_color), polys=flowers,
                         clip=("meadow",), opacity=0.9)]
        return layers

    def tree(self):
        if not self.s.get("tree", True):
            return []
        W, H = self.W, self.H
        k = self.light.key_screen()
        side = 1 if k[0] < 0 else -1          # tree on the shadow side frames the light
        tx = W * (0.5 + side * 0.32)
        ty = H * 0.93
        th = H * 0.50
        trunk = np.array([(tx - 0.018 * W, ty), (tx - 0.010 * W, ty - th * 0.55), (tx - 0.006 * W, ty - th * 0.8),
                          (tx + 0.006 * W, ty - th * 0.8), (tx + 0.010 * W, ty - th * 0.55), (tx + 0.022 * W, ty)])
        branches = []
        for a, L, y in ((-0.9, 0.11, 0.55), (0.8, 0.13, 0.62), (-0.5, 0.09, 0.72)):
            p = np.array([tx, ty - th * y])
            q = p + np.array([np.sin(a), -np.cos(a)]) * L * H
            branches.append((geom.bezier(p, p + (q - p) * 0.4 + [0, -0.01 * H], q, q, 10),
                             geom.tapered_widths(10, 0.011 * W, 0.0, 0.8)))
        rng = self.rng
        # foliage clumps sit on the branch ends and the crown; each clump is its own
        # layer so lines and shadows separate the masses (back clumps first)
        centers = [b[0][-1] for b in branches] + [(tx - side * 0.05 * W, ty - th * 0.95),
                                                  (tx + side * 0.06 * W, ty - th * 0.80), (tx, ty - th * 0.87)]
        leaf = col.shadow_of(col.hex_rgb(self.t["grass"]), 0.15, "#305030", 0.04, 0.15)
        bark = col.hex_rgb("#5E4434")
        shadow = geom.ellipse(tx + side * 0.06 * W, ty + 0.01 * H, 0.14 * W, 0.022 * H, 40)
        layers = [Layer("tree_shadow", Material.FLAT, col.shadow_of(col.hex_rgb(self.t["grass"]), 0.45), polys=[shadow],
                        clip=("meadow",), blend=Blend.MULTIPLY, feather=H * 0.01, opacity=0.6),
                  Layer("trunk", Material.CLOTH, bark, polys=[trunk], strokes=branches, line=LineSpec(self.lw),
                        shade=ShadeSpec(inflate=0.01 * W, threshold=0.2, rim=0.5), tags=("tree", "focus"))]
        for j, (cx, cy) in enumerate(centers):
            R = rng.uniform(0.075, 0.10) * H
            blobs = [geom.ellipse(cx, cy + R * 0.1, R * 0.9, R * 0.62, 32)]
            for _ in range(12):
                a = rng.uniform(np.pi * 0.9, np.pi * 2.1)
                rr = rng.uniform(0.35, 1.0)
                c = (cx + np.cos(a) * rr * R, cy + np.sin(a) * rr * R * 0.75 + R * 0.12)
                r = rng.uniform(0.28, 0.42) * R
                blobs.append(geom.ellipse(c[0], c[1], r * 1.15, r, 24))
            normals = shapes.mask_normals(blobs, W, H, radius=0.55 * R, noise=7.0, scale=0.009 * W,
                                          seed=self.seed + 41 + j)
            tone = col.shift(leaf, dv=rng.uniform(-0.04, 0.05))
            layers.append(Layer(f"foliage{j}", Material.CLOTH, tone, polys=blobs, line=LineSpec(self.lw),
                                shade=ShadeSpec(normal_map=normals, threshold=0.15, rim=0.8,
                                                cast_tags=("foliage",), cast_dist=0.02 * H),
                                tags=("tree", "foliage", "focus")))
        return layers

    def build(self):
        ranges, mirrors = self.ranges()
        lake, shore, xs = self.lake(mirrors)
        return self.clouds() + ranges + lake + self.meadow(shore, xs) + self.tree()


def build(spec, W, H, light, seed):
    ls = spec.get("landscape", {})
    t = TIMES[ls.get("time", "day")]
    user_key = spec.get("lighting", {}).get("key")
    key = t["key"] if user_key in (None, "upper_left") else light.key
    lit = Light(key=key, key_color=t["key_color"], rim_dir=(-np.sign(key[0]) or 1.0, -0.3), rim_color=t["rim"],
                rim_strength=0.35)
    b = LandscapeBuilder(ls, W, H, lit, seed)
    return b.build(), b.sky(), lit
