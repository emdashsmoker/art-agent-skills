"""Still life: table, wall, drapery, vases, bottles, cups, fruit, flowers and modern props.

Objects are solids of revolution or spheroids with analytic normals, set on
a table plane seen slightly from above. Every object gets a projected ground
shadow and a contact shadow; the wall receives offset cast shadows. A warm
bounce light from the table lights the lower edges (reflected light), the
cue painters use to make objects sit on a surface.
"""
import numpy as np

from . import color as col
from . import geom, props, shapes
from .scene import Blend, Layer, Light, LineSpec, Material, ShadeSpec

TABLE_BACK = 0.56     # table back edge, fraction of canvas height
TABLE_FRONT = 0.86
OBJECT_SCALE = 0.42   # object size unit as fraction of canvas height

PROFILES = {
    "vase":   (1.00, [(0, 0.17), (0.06, 0.21), (0.35, 0.27), (0.62, 0.22), (0.80, 0.10), (0.92, 0.085), (1.0, 0.11)]),
    "bottle": (1.15, [(0, 0.13), (0.55, 0.13), (0.62, 0.12), (0.72, 0.05), (0.95, 0.04), (1.0, 0.046)]),
    "cup":    (0.30, [(0, 0.125), (1.0, 0.150)]),
    "mug":    (0.38, [(0, 0.135), (1.0, 0.135)]),
    "jar":    (0.55, [(0, 0.17), (0.08, 0.20), (0.75, 0.20), (0.85, 0.15), (1.0, 0.15)]),
}
FRUIT = {"apple": (0.135, 0.120), "orange": (0.122, 0.118), "lemon": (0.130, 0.085), "pear": (0.11, 0.15)}
DEFAULT_COLORS = {"vase": "#5E7FA8", "bottle": "#3F6B4F", "cup": "#F4F1EA", "mug": "#3E4E66", "jar": "#C9A36B",
                  "apple": "#C8423A", "orange": "#E8892E", "lemon": "#EBCB45", "pear": "#B8BE4A",
                  **props.PROP_COLORS}
DEFAULT_OBJECTS = [
    {"type": "bottle", "x": 0.24, "depth": 0.05},
    {"type": "vase", "x": 0.44, "depth": 0.15, "flowers": "#E8707A"},
    {"type": "cup", "x": 0.73, "depth": 0.45},
    {"type": "lemon", "x": 0.30, "depth": 0.70},
    {"type": "apple", "x": 0.50, "depth": 0.78},
    {"type": "orange", "x": 0.60, "depth": 0.62},
]


class StillLifeBuilder:
    def __init__(self, spec, W, H, light, seed):
        self.s = spec
        self.W, self.H = W, H
        self.light = light
        self.rng = np.random.default_rng(seed + 211)
        self.yt, self.yf = TABLE_BACK * H, TABLE_FRONT * H
        self.table = col.hex_rgb(spec.get("table", "#8A5A3C"))
        self.wall = col.hex_rgb(spec.get("wall", "#E6DCCB"))
        self.lw = H * 0.0032

    # ------------------------------------------------------------ helpers
    def base_y(self, depth):
        return self.yt + (0.10 + 0.78 * depth) * (self.yf - self.yt)

    def unit(self, obj):
        return self.H * OBJECT_SCALE * float(obj.get("scale", 1.0)) * (0.86 + 0.14 * obj.get("depth", 0.5))

    def obj_layer(self, name, polys, color, normals, spec=0.0, spec_edge=0.93, shadow=None, tags=("object",),
                  line=True, rim=1.0):
        return Layer(name, Material.CLOTH, color, polys=polys, line=LineSpec(self.lw) if line else None,
                     shade=ShadeSpec(normal_map=normals, threshold=0.10, spec=spec, spec_edge=spec_edge,
                                     shadow=shadow, rim=rim),
                     tags=tags + ("focus",))

    def shadows(self, name, outline, y_base, width):
        shade = col.shadow_of(self.table, 0.55, "#302040", 0.05, 0.2)
        ground = shapes.ground_shadow(outline, y_base, self.light)
        contact = geom.ellipse(np.mean(outline[:, 0]), y_base, width * 0.55, width * 0.11, 40)
        return [Layer(f"{name}_shadow", Material.FLAT, shade, polys=[ground], clip=("tabletop", "cloth"),
                      blend=Blend.MULTIPLY, opacity=0.55, feather=self.H * 0.006),
                Layer(f"{name}_contact", Material.FLAT, shade, polys=[contact], clip=("tabletop", "cloth"),
                      blend=Blend.MULTIPLY, opacity=0.65, feather=self.H * 0.004)]

    # ------------------------------------------------------------ setting
    def setting(self):
        W, H = self.W, self.H
        wall = Layer("wall", Material.CLOTH, self.wall, polys=[np.array([(0, 0), (W, 0), (W, self.yt + 2), (0, self.yt + 2)])],
                     shade=ShadeSpec(cast_tags=("object",), cast_dist=W * 0.05, gradient=(0.30, 0.0), rim=0.0),
                     tags=("wall",))
        k = self.light.key_screen()
        x0 = W * (0.10 if k[0] < 0 else 0.55)
        win = np.array([(x0, 0.0), (x0 + 0.30 * W, 0.0), (x0 + 0.22 * W, self.yt), (x0 - 0.08 * W, self.yt)])
        glow = Layer("window_light", Material.GLOW, col.hex_rgb(self.light.key_color), polys=[win],
                     clip=("wall",), feather=W * 0.03, blend=Blend.SCREEN, opacity=0.35)
        top = Layer("tabletop", Material.CLOTH, self.table,
                    polys=[np.array([(-5, self.yt), (W + 5, self.yt), (W + 5, self.yf), (-5, self.yf)])],
                    shade=ShadeSpec(normal_map=shapes.plane_normals((0.0, -0.75, 0.66)), gradient=(0.25, 0.0),
                                    rim=0.0), line=LineSpec(self.lw), tags=("tabletop",))
        front = Layer("table_front", Material.FLAT, col.shadow_of(self.table, 0.22, "#402030", 0.04, 0.10),
                      polys=[np.array([(-5, self.yf), (W + 5, self.yf), (W + 5, H + 5), (-5, H + 5)])],
                      line=LineSpec(self.lw))
        grain = []
        for _ in range(26):
            y = self.rng.uniform(self.yt + 4, self.yf - 4)
            xa = self.rng.uniform(-0.1, 0.8) * W
            xs = np.linspace(xa, xa + self.rng.uniform(0.2, 0.5) * W, 24)
            sp = np.column_stack([xs, y + 2.5 * np.sin(xs / W * 9 + self.rng.uniform(0, 6))])
            grain.append((sp, geom.tapered_widths(24, self.H * 0.0018, 0.3, 0.3)))
        wood = Layer("wood_grain", Material.INK, col.shadow_of(self.table, 0.25), strokes=grain, opacity=0.35,
                     clip=("tabletop",))
        return [wall, glow, top, wood, front]

    def cloth(self):
        c = self.s.get("cloth", "#F2EEE6")
        if not c:
            return []
        W, H = self.W, self.H
        color = col.hex_rgb(c)
        x0, x1 = 0.52 * W, 1.02 * W
        back_y = self.yt + 0.22 * (self.yf - self.yt)
        xs = np.linspace(x0, x1, 40)
        hem_x = np.linspace(x1, x0 + 0.06 * W, 60)
        hem_y = H * 0.985 - 0.02 * H * np.sin(np.linspace(0, 5 * np.pi, 60)) ** 2
        on_table = np.vstack([np.column_stack([xs, back_y + 0.015 * H * np.sin(xs / W * 14)]),
                              [(x1, self.yf), (x0 - 0.01 * W, self.yf), (x0 - 0.01 * W, self.yf - 0.06 * H)]])
        hang = np.vstack([[(x0 - 0.01 * W, self.yf - 1), (x1, self.yf - 1)], np.column_stack([hem_x, hem_y]),
                          [(x0 + 0.03 * W, self.yf + 0.02 * H)]])
        # vertical folds: alternating light and dark bands across the hanging part
        n_f = 9
        band_x = np.linspace(x0, x1, n_f + 1)
        darks = [np.array([(a, self.yf), (b, self.yf), (b + 0.01 * W, H), (a + 0.01 * W, H)])
                 for a, b in zip(band_x[:-1:2], band_x[1::2])]
        folds = []
        for xa in band_x[1:-1]:
            sp = np.array([(xa, self.yf + 0.01 * H), (xa + 0.006 * W, self.yf + 0.06 * H), (xa + 0.012 * W, H * 0.97)])
            folds.append((geom.catmull_rom(sp, 10), geom.tapered_widths(21, H * 0.0028, 0.5, 0.3)))
        edge = np.array([(x0 - 0.01 * W, self.yf), (x1, self.yf)])
        plane_up = shapes.plane_normals((0.0, -0.75, 0.66))
        return [Layer("cloth", Material.CLOTH, color, polys=[on_table], line=LineSpec(self.lw),
                      shade=ShadeSpec(normal_map=plane_up, gradient=(0.0, 0.10), rim=0.0), tags=("cloth",)),
                Layer("cloth_hang", Material.CLOTH, color, polys=[hang], line=LineSpec(self.lw),
                      shade=ShadeSpec(normal_map=shapes.plane_normals((0.15, 0.1, 1.0)), threshold=0.62,
                                      gradient=(0.0, 0.25), rim=0.0), tags=("cloth",)),
                Layer("cloth_fold_shadow", Material.FLAT, col.shadow_of(color, 0.18, "#4050A0", 0.04, 0.12),
                      polys=darks, clip=("cloth_hang",), blend=Blend.MULTIPLY, feather=W * 0.008, opacity=0.8),
                Layer("cloth_folds", Material.INK, col.shadow_of(color, 0.45, "#4050A0", 0.04, 0.2),
                      strokes=folds + [(edge, np.full(2, H * 0.003))], clip=("cloth",), opacity=0.5)]

    # ------------------------------------------------------------ objects
    def vessel(self, i, obj):
        kind = obj["type"]
        h_unit, prof = PROFILES[kind]
        s = self.unit(obj)
        cx, yb = obj["x"] * self.W, self.base_y(obj.get("depth", 0.3))
        color = col.hex_rgb(obj.get("color", DEFAULT_COLORS[kind]))
        outline, top, ys, rs = shapes.revolution_outline(cx, yb, h_unit * s, [(t, r * s) for t, r in prof])
        name = f"obj{i}_{kind}"
        glossy = {"vase": (0.9, 0.95), "bottle": (1.0, 0.975), "cup": (0.7, 0.94), "mug": (0.6, 0.94),
                  "jar": (0.5, 0.93)}[kind]
        layers = self.shadows(name, outline, yb, rs[0] * 2)
        if kind in ("cup", "mug"):
            ring_c = (cx + rs[len(rs) // 2] * 0.98, yb - h_unit * s * 0.52)
            outer = geom.ellipse(*ring_c, 0.085 * s, 0.10 * s, 48)
            inner = geom.ellipse(*ring_c, 0.050 * s, 0.065 * s, 48)
            layers.append(Layer(f"{name}_handle", Material.CLOTH, color, polys=[outer, inner], even_odd=True,
                                line=LineSpec(self.lw), shade=ShadeSpec(inflate=0.02 * s, threshold=0.1),
                                tags=("object", "focus")))
        layers.append(self.obj_layer(name, [outline], color, shapes.revolution_normals(cx, ys, rs),
                                     spec=glossy[0], spec_edge=glossy[1]))
        mouth_r = rs[-1]
        inner_c = col.shadow_of(color, 0.55, "#201830", 0.05, 0.2)
        layers.append(Layer(f"{name}_mouth", Material.FLAT, inner_c, polys=[top], line=LineSpec(self.lw * 0.8)))
        if kind in ("cup", "mug"):
            liquid = geom.ellipse(cx, ys[-1] + mouth_r * 0.06, mouth_r * 0.86, mouth_r * shapes.VIEW_TILT * 0.80, 48)
            layers.append(Layer(f"{name}_coffee", Material.FLAT, col.hex_rgb(obj.get("liquid", "#5A3324")),
                                polys=[liquid], clip=(f"{name}_mouth",)))
        else:
            lip = geom.ellipse(cx, ys[-1] + mouth_r * 0.05, mouth_r * 0.80, mouth_r * shapes.VIEW_TILT * 0.70, 40)
            layers.append(Layer(f"{name}_inner", Material.FLAT, col.shadow_of(inner_c, 0.4), polys=[lip],
                                clip=(f"{name}_mouth",), feather=mouth_r * 0.08))
        if kind == "bottle":
            streak = np.array([(cx - rs[5] * 0.55, ys[5]), (cx - rs[5] * 0.35, ys[5]), (cx - rs[22] * 0.35, ys[22]),
                               (cx - rs[22] * 0.55, ys[22])])
            layers.append(Layer(f"{name}_glint", Material.FLAT, col.hex_rgb("#FFFFFF"), polys=[streak],
                                clip=(name,), blend=Blend.SCREEN, opacity=0.45, feather=s * 0.006))
        if obj.get("flowers"):
            layers += self.flowers(name, cx, ys[-1], mouth_r, s, col.hex_rgb(obj["flowers"]))
        return layers

    def fruit(self, i, obj):
        kind = obj["type"]
        s = self.unit(obj)
        rx, ry = (v * s for v in FRUIT[kind])
        cx, yb = obj["x"] * self.W, self.base_y(obj.get("depth", 0.7))
        cy = yb - ry * 0.92
        color = col.hex_rgb(obj.get("color", DEFAULT_COLORS[kind]))
        name = f"obj{i}_{kind}"
        tilt = self.rng.uniform(-0.25, 0.25)
        if kind == "pear":
            prof = geom.catmull_rom(np.array([(0, -1.0), (0.45, -0.85), (0.55, -0.2), (1.0, 0.45), (0.0, 1.0),
                                              (-1.0, 0.45), (-0.55, -0.2), (-0.45, -0.85)]), 8, closed=True)
            outline = prof * [rx, ry] + [cx, cy]
        elif kind == "lemon":
            a = np.linspace(0, 2 * np.pi, 96, endpoint=False)
            nub = 1 + 0.10 * np.exp(-((np.cos(a) ** 2 - 1) ** 2) / 0.004)
            outline = np.column_stack([cx + rx * np.cos(a) * nub, cy + ry * np.sin(a)])
        elif kind == "apple":
            a = np.linspace(0, 2 * np.pi, 96, endpoint=False)
            dent = 1 - 0.10 * np.exp(-((a - 1.5 * np.pi) ** 2) / 0.05) - 0.04 * np.exp(-((a - 0.5 * np.pi) ** 2) / 0.08)
            outline = np.column_stack([cx + rx * np.cos(a) * dent, cy + ry * np.sin(a) * dent])
        else:
            outline = geom.ellipse(cx, cy, rx, ry, 96)
        outline = geom.rotate(outline, tilt, (cx, cy))
        warm = col.shadow_of(color, 0.30 if kind == "lemon" else 0.40, "#6A2040", 0.03 if kind == "lemon" else 0.06, 0.25)
        gloss = {"apple": (0.8, 0.94), "orange": (0.35, 0.90), "lemon": (0.45, 0.91), "pear": (0.4, 0.92)}[kind]
        layers = self.shadows(name, outline, yb, rx * 2)
        layers.append(self.obj_layer(name, [outline], color, shapes.sphere_normals(cx, cy, rx, ry), spec=gloss[0],
                                     spec_edge=gloss[1], shadow=col.rgb_hex(warm)))
        if kind == "apple":
            blush = geom.ellipse(cx + rx * 0.15, cy + ry * 0.1, rx * 0.65, ry * 0.75, 48)
            layers.append(Layer(f"{name}_blush", Material.FLAT, col.hex_rgb("#E8C04A"), polys=[blush], clip=(name,),
                                feather=rx * 0.35, blend=Blend.SCREEN, opacity=0.30))
        if kind in ("apple", "pear"):
            top = geom.rotate([(cx, cy - ry * 0.88)], tilt, (cx, cy))[0]
            stem = geom.bezier(top, top + [0.01 * s, -0.04 * s], top + [0.03 * s, -0.06 * s], top + [0.035 * s, -0.08 * s], 12)
            layers.append(Layer(f"{name}_stem", Material.INK, col.hex_rgb("#4A3020"),
                                strokes=[(stem, geom.tapered_widths(12, 0.012 * s, 0.0, 0.3))]))
        if kind == "orange":
            dimples = [geom.ellipse(cx + u * rx, cy + v * ry, rx * 0.012, ry * 0.012, 8)
                       for u, v in self.rng.uniform(-0.7, 0.7, (60, 2)) if u * u + v * v < 0.5]
            layers.append(Layer(f"{name}_pores", Material.FLAT, warm, polys=dimples, clip=(name,), opacity=0.35))
        return layers

    def flowers(self, name, cx, top_y, mouth_r, s, color):
        rng = self.rng
        n = 7
        layers, stems, leaves = [], [], []
        heads = []
        for k in range(n):
            ang = np.radians(-60 + 120 * k / (n - 1) + rng.uniform(-8, 8))
            L = s * rng.uniform(0.32, 0.48)
            head = np.array([cx + np.sin(ang) * L * 1.05, top_y - np.cos(ang) * L])
            base = np.array([cx + rng.uniform(-0.5, 0.5) * mouth_r, top_y + mouth_r * 0.1])
            ctrl = base + (head - base) * 0.5 + [rng.uniform(-0.02, 0.02) * s, 0]
            stems.append((geom.bezier(base, ctrl, ctrl, head, 16), geom.tapered_widths(16, 0.010 * s, 0.0, 0.0) + 1))
            heads.append((head, s * rng.uniform(0.055, 0.075), rng.uniform(0, np.pi), rng.uniform(-0.12, 0.12)))
            if k % 2 == 0:
                p = base + (head - base) * rng.uniform(0.35, 0.6)
                d = np.array([np.sign(ang + 1e-3) * 0.9, -0.4])
                blade = np.array([p, p + d * 0.04 * s + [0, -0.02 * s], p + d * 0.11 * s, p + d * 0.05 * s + [0, 0.015 * s]])
                leaves.append(geom.catmull_rom(blade, 6, closed=True))
        green = col.hex_rgb(self.s.get("leaves", "#5E8A4A"))
        layers.append(Layer(f"{name}_stems", Material.INK, col.shadow_of(green, 0.15), strokes=stems,
                            tags=("object",)))
        layers.append(Layer(f"{name}_leaves", Material.CLOTH, green, polys=leaves, line=LineSpec(self.lw * 0.8),
                            shade=ShadeSpec(inflate=0.012 * s, threshold=0.1), tags=("object", "focus")))
        heads.sort(key=lambda h: h[0][1])
        for j, (c, r, rot, hue) in enumerate(heads):
            petals = []
            for p in range(6):
                a = rot + p * np.pi / 3
                pc = c + np.array([np.cos(a), np.sin(a) * 0.8]) * r * 0.62
                petals.append(geom.ellipse(pc[0], pc[1], r * 0.58, r * 0.40, 24, rot=a))
            pcol = col.shift(color, dh=hue * 0.15, dv=rng.uniform(-0.05, 0.08))
            layers.append(Layer(f"{name}_flower{j}", Material.CLOTH, pcol, polys=petals, line=LineSpec(self.lw * 0.8),
                                shade=ShadeSpec(normal_map=shapes.sphere_normals(c[0], c[1], r * 1.25, r * 1.05),
                                                threshold=0.05, rim=0.6),
                                tags=("object", "focus")))
            layers.append(Layer(f"{name}_flower{j}_eye", Material.FLAT, col.hex_rgb("#E8B640"),
                                polys=[geom.ellipse(c[0], c[1], r * 0.26, r * 0.22, 24)], line=LineSpec(self.lw * 0.6)))
        return layers

    def prop(self, i, obj):
        kind = obj["type"]
        name = f"obj{i}_{kind}"
        yb = self.base_y(obj.get("depth", 0.4))
        layers, outline = props.build_prop(kind, name, (obj["x"] * self.W, yb), self.unit(obj), self.lw, self.rng, obj)
        width = outline[:, 0].max() - outline[:, 0].min()
        return self.shadows(name, outline, outline[:, 1].max(), width * 0.8) + layers

    # ------------------------------------------------------------ assembly
    def build(self):
        objects = [dict(o) for o in self.s.get("objects") or DEFAULT_OBJECTS]
        for o in objects:
            if o.get("type") not in DEFAULT_COLORS:
                raise ValueError(f"unknown still-life object: {o.get('type')!r} (allowed: {', '.join(DEFAULT_COLORS)})")
        layers = self.setting() + self.cloth()
        for i, o in sorted(enumerate(objects), key=lambda io: io[1].get("depth", 0.5)):
            if o["type"] in PROFILES:
                layers += self.vessel(i, o)
            elif o["type"] in props.PROPS:
                layers += self.prop(i, o)
            else:
                layers += self.fruit(i, o)
        return layers


def build(spec, W, H, light, seed):
    sl = spec.get("still_life", {})
    bounce = col.light_of(col.hex_rgb(sl.get("table", "#8A5A3C")), 0.45)
    lit = Light(key=light.key, key_color=light.key_color, rim_dir=(0.35, 1.0), rim_color=col.rgb_hex(bounce),
                rim_strength=0.45)
    bg = np.broadcast_to(col.hex_rgb(sl.get("wall", "#E6DCCB")), (H, W, 3)).astype(np.float32).copy()
    return StillLifeBuilder(sl, W, H, lit, seed).build(), bg, lit
