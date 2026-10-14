"""City: a street in one-point perspective with facades, windows, lamps, skyline.

Geometry is built in meters in a simple pinhole camera (eye 1.6 m above the
road) and projected, so every window, curb and lamp converges on the same
vanishing point. Facades are planes with exact normals, so the sunlit side
of the street and the shaded side fall out of the lighting. Distance haze
mixes far facades toward the horizon color (aerial perspective).
"""
import numpy as np

from . import color as col
from . import geom, raster, shapes
from .scene import Blend, Layer, Light, LineSpec, Material, ShadeSpec

EYE = 1.6
ROAD_HALF, CURB = 5.0, 8.0
Z_NEAR, Z_FAR = 2.0, 260.0
HAZE_DIST = 180.0
FLOOR_H = 3.3
PALETTE = ["#D9C7A8", "#C98F6E", "#B8B4AA", "#E3D9C6", "#A86F5A", "#9FA8A3", "#D8B48C", "#C2A3A0"]
TIMES = {
    "day":   {"sky": ("#5D93CE", "#A9CBEA", "#E6EEF4"), "key": (-0.60, -0.60, 0.53), "key_color": "#FFF4E2",
              "facade": 1.00, "lit": 0.0, "haze": "#D6E2EC"},
    "dusk":  {"sky": ("#2E3966", "#B36F86", "#F2B47E"), "key": (0.75, -0.20, 0.62), "key_color": "#FFC08A",
              "facade": 0.72, "lit": 0.45, "haze": "#E2A68C"},
    "night": {"sky": ("#0C1430", "#1E2A55", "#3A4672"), "key": (-0.30, -0.70, 0.65), "key_color": "#8FA0D8",
              "facade": 0.38, "lit": 0.62, "haze": "#2E3866"},
}
WARM = "#FFD58A"
# power lines: wooden poles along the near sidewalk edge, wires sagging between pole tops, a few crossing the street
POLE = {"x": 0.45, "z0": 7.0, "step": 19.0, "height": 9.0, "arm": 1.3, "wires": (8.6, 8.1, 7.4), "sag": 0.035,
        "wire_w": 0.05}


class CityBuilder:
    def __init__(self, spec, W, H, light, seed):
        self.s = spec
        self.W, self.H = W, H
        self.t = TIMES[spec.get("time", "day")]
        self.light = light
        self.seed = seed
        self.rng = np.random.default_rng(seed + 401)
        self.vp = np.array([0.5 * W, 0.55 * H])
        self.f = 0.80 * W
        self.cam_x = float(spec.get("camera_x", -1.8))   # off-center camera avoids a mirror-symmetric street
        # the road must reach the bottom edge even on tall (portrait) canvases
        self.z_near = min(Z_NEAR, self.f * EYE / (H - self.vp[1] + 0.05 * H))
        self.haze = col.hex_rgb(self.t["haze"])
        self.lw = H * 0.0026

    # ------------------------------------------------------------ camera
    def P(self, pts3):
        p = np.asarray(pts3, dtype=np.float64).reshape(-1, 3)
        z = np.maximum(p[:, 2], 0.3)
        return np.column_stack([self.vp[0] + self.f * (p[:, 0] - self.cam_x) / z,
                                self.vp[1] + self.f * (EYE - p[:, 1]) / z])

    def quad(self, a, b, c, d):
        return self.P([a, b, c, d])

    def fog(self, color, z):
        k = 1 - np.exp(-z / HAZE_DIST)
        return col.mix(color, self.haze, k * 0.85)

    def night(self, color):
        m = self.t["facade"]
        if m >= 1:
            return color
        return col.mix(color * m, col.hex_rgb("#2A3360") * 0.9, (1 - m) * 0.55)

    # ------------------------------------------------------------ sky
    def sky(self):
        W, H = self.W, self.H
        top, mid, hor = (col.hex_rgb(c) for c in self.t["sky"])
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None] / (self.vp[1] / H)
        t1 = np.clip(y * 1.4, 0, 1)
        t2 = np.clip((y - 0.6) / 0.4, 0, 1)
        img = (top * (1 - t1) + mid * t1) * (1 - t2) + hor * t2
        img = np.broadcast_to(img, (H, W, 3)).astype(np.float32).copy()
        if self.s.get("time", "day") == "night":
            pts = self.rng.uniform(0, 1, (260, 2)) * [W, self.vp[1] * 0.9]
            stars = raster.Rasterizer(W, H).circles(pts, self.rng.uniform(0.4, 1.4, len(pts)) * H / 960)
            img = raster.screen(img, col.hex_rgb("#FFFFFF"), stars * 0.8)
        return img

    # ------------------------------------------------------------ street
    def street(self):
        road_c = self.night(col.hex_rgb("#6E6F76"))
        walk_c = self.night(col.hex_rgb("#B9B2A6"))
        zn, zf = self.z_near, Z_FAR + 200
        layers = []
        for name, x0, x1, c in (("road", -ROAD_HALF, ROAD_HALF, road_c), ("walk_l", -CURB, -ROAD_HALF, walk_c),
                                ("walk_r", ROAD_HALF, CURB, walk_c)):
            q = self.quad((x0, 0, zn), (x1, 0, zn), (x1, 0, zf), (x0, 0, zf))
            fill = (tuple(self.P([(0, 0, zf)])[0]), tuple(self.P([(0, 0, zn)])[0]), self.fog(c, 150), c)
            layers.append(Layer(name, Material.FLAT, c, polys=[q], line=LineSpec(self.lw), gradient_fill=fill,
                                tags=("ground",)))
        dashes = []
        for z in np.arange(4.0, Z_FAR, 9.0):
            dashes.append(self.quad((-0.12, 0, z), (0.12, 0, z), (0.12, 0, z + 3.5), (-0.12, 0, z + 3.5)))
        layers.append(Layer("lane", Material.FLAT, self.night(col.hex_rgb("#F2EEE0")), polys=dashes, opacity=0.9))
        curbs = []
        for x in (-ROAD_HALF, ROAD_HALF):
            curbs.append(self.quad((x - 0.15, 0.0, zn), (x + 0.15, 0.0, zn), (x + 0.15, 0.0, zf), (x - 0.15, 0.0, zf)))
        layers.append(Layer("curbs", Material.FLAT, self.night(col.hex_rgb("#D8D2C6")), polys=curbs))
        return layers

    # ------------------------------------------------------------ buildings
    def windows(self, side, z0, z1, h, front_x=None):
        """Window quads (glass, lit) on the street facade, or on the front face if front_x is given."""
        X = side * CURB
        glass, lit = [], []
        floors = np.arange(4.2, h - 1.6, FLOOR_H)
        if front_x is None:
            for y in floors:
                for z in np.arange(z0 + 1.2, z1 - 1.6, 2.6):
                    q = self.quad((X, y, z), (X, y, z + 1.3), (X, y + 1.8, z + 1.3), (X, y + 1.8, z))
                    (lit if self.rng.random() < self.t["lit"] else glass).append(q)
        else:
            for y in floors:
                for x in np.arange(1.0, front_x - 1.5, 2.6):
                    xa = side * (CURB + x)
                    q = self.quad((xa, y, z0), (xa + side * 1.3, y, z0), (xa + side * 1.3, y + 1.8, z0), (xa, y + 1.8, z0))
                    (lit if self.rng.random() < self.t["lit"] else glass).append(q)
        return glass, lit

    def window_layers(self, name, glass, lit, z):
        layers = []
        if glass:
            c = self.fog(self.night(col.hex_rgb("#8FA8C2")), z)
            layers.append(Layer(name, Material.FLAT, c, polys=glass,
                                gradient_fill=((0, self.vp[1] - self.H * 0.5), (0, self.vp[1] + self.H * 0.1),
                                               col.light_of(c, 0.25), col.shadow_of(c, 0.18))))
        if lit:
            warm = col.hex_rgb(WARM)
            layers.append(Layer(name + "_lit", Material.FLAT, warm, polys=lit))
            layers.append(Layer(name + "_glow", Material.GLOW, warm, polys=lit, blend=Blend.SCREEN,
                                feather=self.H * 0.006, opacity=0.6))
        return layers

    def building(self, i, side, z0, z1, h, color, show_front, extras):
        """Facade (+ front face) layers; small parts are pooled into `extras` by depth band."""
        X = side * CURB
        name = f"bld{side}_{i}"
        zc = (z0 + z1) / 2
        band = 0 if zc < 40 else (1 if zc < 110 else 2)
        base = self.fog(self.night(color), zc)
        layers = []
        depth_x = 30.0
        if show_front:
            front = self.quad((X, 0, z0), (X + side * depth_x, 0, z0), (X + side * depth_x, h, z0), (X, h, z0))
            layers.append(Layer(f"{name}_front", Material.CLOTH, base, polys=[front], line=LineSpec(self.lw),
                                shade=ShadeSpec(normal_map=shapes.plane_normals((0.0, 0.0, 1.0)), threshold=0.15,
                                                gradient=(0.0, 0.18), rim=0.0),
                                tags=("building", "focus")))
            # front-face windows overlap nearer buildings on screen, so they stay with their building
            layers += self.window_layers(f"{name}_fwin", *self.windows(side, z0, z1, h, depth_x), zc)
        facade = self.quad((X, 0, z0), (X, 0, z1), (X, h, z1), (X, h, z0))
        layers.append(Layer(name, Material.CLOTH, base, polys=[facade], line=LineSpec(self.lw),
                            shade=ShadeSpec(normal_map=shapes.plane_normals((-side, 0.0, 0.0)), threshold=0.0,
                                            gradient=(0.0, 0.22), rim=0.0),
                            tags=("building", "focus")))
        lit_side = np.sign(self.light.key_screen()[0]) != side
        cornice_c = col.shadow_of(base, 0.12 if lit_side else 0.25)
        layers.append(Layer(f"{name}_cornice", Material.FLAT, cornice_c,
                            polys=[self.quad((X, h - 0.9, z0), (X, h - 0.9, z1), (X, h, z1), (X, h, z0))],
                            line=LineSpec(self.lw * 0.7)))

        def add(kind, polys):
            extras.setdefault((kind, band), []).extend(polys)
        add("shop", [self.quad((X, 0.3, z), (X, 0.3, z + 2.2), (X, 2.8, z + 2.2), (X, 2.8, z))
                     for z in np.arange(z0 + 0.8, z1 - 2.6, 3.0)])
        add("awning", [self.quad((X, 3.2, z0 + 0.4), (X, 3.2, z1 - 0.4), (X - side * 1.6, 2.7, z1 - 0.4),
                                 (X - side * 1.6, 2.7, z0 + 0.4))])
        glass, lit = self.windows(side, z0, z1, h)
        add("glass", glass)
        add("lit", lit)
        return layers

    def pooled(self, side, extras):
        """One layer per (part, depth band): windows, shop fronts, awnings."""
        layers = []
        zmid = {0: 25.0, 1: 75.0, 2: 170.0}
        awning_c = col.hex_rgb(self.s.get("awning", "#5E7F6E"))
        for (kind, band), polys in sorted(extras.items(), key=lambda kv: -kv[0][1]):
            if not polys:
                continue
            z = zmid[band]
            name = f"{kind}{side}_{band}"
            if kind in ("glass", "lit"):
                layers += self.window_layers(name, polys if kind == "glass" else [], polys if kind == "lit" else [], z)
            elif kind == "shop":
                c = self.fog(self.night(col.hex_rgb("#6F8296")), z)
                if self.t["lit"]:
                    c = col.mix(c, col.hex_rgb(WARM), 0.55)
                layers.append(Layer(name, Material.FLAT, c, polys=polys, line=LineSpec(self.lw * 0.6)))
            else:
                c = self.fog(self.night(awning_c), z)
                layers.append(Layer(name, Material.CLOTH, c, polys=polys, line=LineSpec(self.lw * 0.7),
                                    shade=ShadeSpec(normal_map=shapes.plane_normals((-side * 0.3, -0.9, 0.3)),
                                                    threshold=0.0, rim=0.0)))
        return layers

    def side(self, side):
        rng = self.rng
        z = Z_NEAR
        blocks = []
        while z < Z_FAR:
            w = rng.uniform(9, 20)
            h = rng.uniform(12, 34) if z < 120 else rng.uniform(12, 26)
            blocks.append((z, z + w, h, col.hex_rgb(rng.choice(PALETTE))))
            z += w
        layers, shadows, extras = [], [], {}
        # far to near so nearer blocks cover farther ones; facades of one side never overlap
        for i in range(len(blocks) - 1, -1, -1):
            z0, z1, h, c = blocks[i]
            prev_h = blocks[i - 1][2] if i > 0 else 0.0
            layers += self.building(i, side, z0, z1, h, c, h > prev_h, extras)
            if np.sign(self.light.key_screen()[0]) == side or self.t["facade"] < 1:
                continue
            reach = min(h * 0.55, 2 * ROAD_HALF + 2)
            X = side * CURB
            shadows.append(self.quad((X, 0, z0), (X, 0, z1), (X - side * reach, 0, z1 + h * 0.15),
                                     (X - side * reach, 0, z0 + h * 0.15)))
        return layers + self.pooled(side, extras), shadows

    def skyline(self):
        rng = self.rng
        polys, lit = [], []
        for x in np.arange(-90, 90, 7.0):
            if abs(x) < 9:
                continue
            h = rng.uniform(25, 85) * (1.2 - abs(x) / 150)
            w = rng.uniform(4, 8)
            z = Z_FAR + 120 + rng.uniform(0, 80)
            polys.append(self.quad((x, 0, z), (x + w, 0, z), (x + w, h, z), (x, h, z)))
            if self.t["lit"] > 0:
                for y in np.arange(6, h - 3, 6):
                    if rng.random() < self.t["lit"] * 0.6:
                        lit.append(self.quad((x + 1, y, z), (x + 2.2, y, z), (x + 2.2, y + 2, z), (x + 1, y + 2, z)))
        c = col.mix(self.night(col.hex_rgb("#8D97A8")), self.haze, 0.6)
        layers = [Layer("skyline", Material.FLAT, c, polys=polys, tags=("building",))]
        if lit:
            layers.append(Layer("skyline_lit", Material.FLAT, col.hex_rgb(WARM), polys=lit, opacity=0.8))
        return layers

    def lamps(self):
        H = self.H
        poles, heads, glows, pools = [], [], [], []
        for z in np.arange(13.0, Z_FAR * 0.6, 22.0):
            for sx in (-1, 1):
                x = sx * (CURB - 1.0)
                base, top = self.P([(x, 0, z), (x, 6.0, z)])
                arm_end = self.P([(x - sx * 1.4, 6.1, z)])[0]
                width = max(self.f * 0.16 / z, 0.6)
                poles.append((np.array([base, top]), np.full(2, width)))
                poles.append((np.array([top, arm_end]), np.full(2, width * 0.7)))
                r = max(self.f * 0.35 / z, 1.0)
                heads.append(geom.ellipse(arm_end[0], arm_end[1] + r * 0.4, r, r * 0.55, 16))
                glows.append(geom.ellipse(arm_end[0], arm_end[1] + r * 0.6, r * 4, r * 4, 24))
                c = self.P([(x - sx * 1.4, 0, z)])[0]
                pools.append(geom.ellipse(c[0], c[1], self.f * 2.6 / z, self.f * 0.7 / z, 32))
        metal = self.night(col.hex_rgb("#3E4450"))
        layers = [Layer("lamp_poles", Material.INK, metal, strokes=poles),
                  Layer("lamp_heads", Material.FLAT, col.hex_rgb(WARM) if self.t["lit"] else metal, polys=heads)]
        if self.t["lit"]:
            warm = col.hex_rgb(WARM)
            layers.insert(0, Layer("lamp_pools", Material.GLOW, warm, polys=pools, clip=("ground",), blend=Blend.SCREEN,
                                   feather=H * 0.012, opacity=0.35 * self.t["lit"] / 0.62))
            layers.append(Layer("lamp_glow", Material.GLOW, warm, polys=glows, blend=Blend.SCREEN, feather=H * 0.01,
                                opacity=0.45))
        return layers

    def wires(self):
        """Utility poles with cross-arms and sagging wires; drawn as dark ink in front of the facades."""
        H = self.H
        poles, wires = [], []
        zs = np.arange(POLE["z0"], Z_FAR * 0.7, POLE["step"])
        tops = {}
        for sx in (-1, 1):
            x = sx * (CURB - POLE["x"])
            for z in zs:
                base, top = self.P([(x, 0, z), (x, POLE["height"], z)])
                width = max(self.f * 0.22 / z, 0.7)
                poles.append((np.array([base, top]), np.full(2, width)))
                arm = self.P([(x - POLE["arm"], POLE["wires"][0] + 0.1, z), (x + POLE["arm"], POLE["wires"][0] + 0.1, z)])
                poles.append((arm, np.full(2, width * 0.6)))
            tops[sx] = (x, zs)
        rng = np.random.default_rng(self.seed + 403)
        spans = [((tops[sx][0], z0), (tops[sx][0], z1)) for sx in (-1, 1) for z0, z1 in zip(zs[:-1], zs[1:])]
        # a few lines cross the street from one side to a pole further down the other side
        spans += [((tops[-1][0], zs[k]), (tops[1][0], zs[k + 1])) for k in range(0, len(zs) - 1, 2)]
        for (xa, za), (xb, zb) in spans:
            for h in POLE["wires"]:
                t = np.linspace(0, 1, 24)
                span = np.hypot(xb - xa, zb - za)
                sag = POLE["sag"] * span * rng.uniform(0.8, 1.2)
                pts = np.column_stack([xa + (xb - xa) * t, h - sag * 4 * t * (1 - t), za + (zb - za) * t])
                widths = np.maximum(self.f * POLE["wire_w"] / pts[:, 2], 0.6)
                wires.append((self.P(pts), widths))
        ink = self.night(col.hex_rgb("#2A2E38"))
        return [Layer("utility_poles", Material.INK, ink, strokes=poles),
                Layer("power_lines", Material.INK, ink, strokes=wires, opacity=0.85)]

    def build(self):
        left, sh_l = self.side(-1)
        right, sh_r = self.side(1)
        layers = self.skyline() + self.street()
        shadows = sh_l + sh_r
        if shadows:
            layers.append(Layer("building_shadows", Material.FLAT, col.hex_rgb("#4A4E6A"), polys=shadows,
                                clip=("ground",), blend=Blend.MULTIPLY, opacity=0.45, feather=self.H * 0.002))
        lamps = self.lamps()
        pools = [L for L in lamps if L.name == "lamp_pools"]
        rest = [L for L in lamps if L.name != "lamp_pools"]
        wires = self.wires() if self.s.get("wires", False) else []
        return layers + pools + left + right + rest + wires


def build(spec, W, H, light, seed):
    cs = spec.get("city", {})
    t = TIMES[cs.get("time", "day")]
    user_key = spec.get("lighting", {}).get("key")
    key = t["key"] if user_key in (None, "upper_left") else light.key
    lit = Light(key=key, key_color=t["key_color"], rim_dir=(1.0, -0.2), rim_color="#FFFFFF", rim_strength=0.0)
    b = CityBuilder(cs, W, H, lit, seed)
    return b.build(), b.sky(), lit
