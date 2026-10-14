"""Interior and poolside settings: bedroom, office, cafe, pool, gym.

The room is a stage seen in the props' orthographic view: a back wall facing
the viewer, a floor running toward the camera, furniture built from boxes,
rods and solids of revolution (props.PropKit). As a character backdrop the
stage is sized from the framing, so furniture keeps a believable scale next
to the figure (scaled down a little to fake the depth a lens would show).
Every setting stays low in contrast; the figure keeps the top of the hierarchy.

Stage coordinates (units of about 30 cm): x lateral from the canvas center,
y up from the floor, zf toward the viewer from the back wall.
"""
import numpy as np

from . import color as col
from . import config as cfg
from . import geom, props, shapes
from .scene import Blend, Layer, Light, LineSpec, Material, ShadeSpec

ROOMS = ("bedroom", "office", "cafe", "pool", "gym")
UNIT_PER_HEAD = 1.25      # stage units per head height (a 24 cm head, 30 cm units)
BACKDROP_SCALE = 0.62     # the backdrop is a little smaller than the figure: fake lens depth
FIGURE_HEIGHT = 6.95      # head top to sole, in head heights
FIGURE_DEPTH = 7.0        # distance from the back wall to the figure (units)
TILT = props.TILT
FLOOR_N = (0.0, -0.95, 0.30)
HEDGE_HEIGHT = 1.1        # pool hedge height above the far deck (units)
WALL_N = (0.0, 0.0, 1.0)
PALETTES = {
    "bedroom": {"wall": "#E9DDD3", "floor": "#B48A68", "accent": "#C8D4E3"},
    "office":  {"wall": "#E3E6E9", "floor": "#7E8894", "accent": "#5F7FA8"},
    "cafe":    {"wall": "#EADCC8", "floor": "#6B4A36", "accent": "#3E5A48"},
    "pool":    {"wall": "#9CC7EA", "floor": "#E6DDCF", "accent": "#3FA4C8"},
    "gym":     {"wall": "#C9CCCF", "floor": "#3A3D42", "accent": "#C8503E"},
}


class Stage:
    def __init__(self, W, H, framing, head_scale):
        fr = cfg.FRAMING[framing]
        head = fr["head_frac"] * H * head_scale
        self.W, self.H = W, H
        self.unit = head * UNIT_PER_HEAD * BACKDROP_SCALE
        feet_y = fr["top"] * H + FIGURE_HEIGHT * head
        self.floor_y = feet_y - FIGURE_DEPTH * TILT * self.unit
        self.cx = W * 0.5
        self.lw = H * 0.0026

    def origin(self, x, zf, y=0.0):
        return (self.cx + x * self.unit, self.floor_y + (zf * TILT - y) * self.unit)

    def view(self, x, zf, y=0.0, yaw=0.0):
        return props.View(self.origin(x, zf, y), self.unit, yaw)

    def wall(self, P):
        """Points on the back wall (x, y units) to canvas."""
        P = np.asarray(P, dtype=np.float64)
        return np.column_stack([self.cx + P[:, 0] * self.unit, self.floor_y - P[:, 1] * self.unit])

    def kit(self, name, x, zf, y=0.0, yaw=0.0):
        return props.PropKit(name, self.view(x, zf, y, yaw), self.lw)


class RoomBuilder:
    def __init__(self, spec, W, H, light, seed, framing, head_scale):
        self.s = spec
        self.room = spec.get("room", "bedroom")
        pal = dict(PALETTES[self.room])
        pal.update({k: v for k, v in spec.items() if k in ("wall", "floor", "accent")})
        self.pal = pal
        self.st = Stage(W, H, framing, head_scale)
        self.W, self.H = W, H
        self.light = light
        self.rng = np.random.default_rng(seed + 307)
        self.layers = []

    # ------------------------------------------------------------ helpers
    def add(self, kit):
        self.layers += kit.layers
        return kit

    def plane(self, name, polys, color, normal, line=False, cast=(), gradient=(0.0, 0.0), tags=(), threshold=0.10):
        self.layers.append(Layer(name, Material.CLOTH, col.hex_rgb(color), polys=polys,
                                 line=LineSpec(self.st.lw) if line else None,
                                 shade=ShadeSpec(normal_map=shapes.plane_normals(normal), cast_tags=cast,
                                                 cast_dist=self.W * 0.025, gradient=gradient, rim=0.0,
                                                 threshold=threshold),
                                 tags=tags))

    def flat(self, name, polys, color, opacity=1.0, clip=(), blend=Blend.OVER, feather=0.0, line=None):
        self.layers.append(Layer(name, Material.FLAT, col.hex_rgb(color), polys=polys, clip=clip, opacity=opacity,
                                 blend=blend, feather=feather, line=LineSpec(line) if line else None))

    def ink(self, name, strokes, color, width, opacity=0.5, clip=()):
        out = [(np.asarray(sp, dtype=np.float64), np.full(len(sp), width)) for sp in strokes]
        self.layers.append(Layer(name, Material.INK, col.hex_rgb(color), strokes=out, opacity=opacity, clip=clip))

    def contact(self, name, x0, x1, z0, z1, opacity=0.45):
        """Soft shadow on the floor under a footprint."""
        st = self.st
        P = np.array([st.origin(x0, z0), st.origin(x1, z0), st.origin(x1, z1), st.origin(x0, z1)])
        self.flat(name, [P], col.rgb_hex(col.shadow_of(col.hex_rgb(self.pal["floor"]), 0.5, "#302040", 0.05, 0.2)),
                  opacity=opacity, clip=("floor",), blend=Blend.MULTIPLY, feather=st.unit * 0.25)

    def furniture_box(self, name, x0, x1, z0, z1, y0, y1, color, face_colors=None, spec=0.1):
        """Axis-aligned box in stage coordinates; returns its face quads."""
        kit = self.st.kit(name, 0.0, 0.0)
        faces = kit.box("box", (x0, y0, -z1), (x1 - x0, 0, 0), (0, y1 - y0, 0), (0, 0, z1 - z0), color,
                        face_colors=face_colors, spec=spec)
        self.add(kit)
        return faces

    # ------------------------------------------------------------ shell
    def shell(self, wall=True):
        st, W, H = self.st, self.W, self.H
        fy = st.floor_y
        if wall:
            self.plane("wall", [np.array([(-5, -5), (W + 5, -5), (W + 5, fy + 1), (-5, fy + 1)])], self.pal["wall"],
                       WALL_N, cast=("object",), gradient=(0.18, 0.0), tags=("wall",))
        self.plane("floor", [np.array([(-5, fy), (W + 5, fy), (W + 5, H + 5), (-5, H + 5)])], self.pal["floor"],
                   FLOOR_N, gradient=(0.22, 0.0), tags=("ground", "floor"))
        if wall:
            base = st.wall([(-20, 0), (20, 0), (20, 0.35), (-20, 0.35)])
            self.flat("baseboard", [base], col.rgb_hex(col.light_of(col.hex_rgb(self.pal["wall"]), 0.35)),
                      line=st.lw * 0.8)

    def planks(self, spacing=0.9, color=None, opacity=0.35):
        st = self.st
        c = color or col.rgb_hex(col.shadow_of(col.hex_rgb(self.pal["floor"]), 0.35))
        lines = []
        z = spacing
        while st.origin(0, z)[1] < self.H + 2:
            y = st.origin(0, z)[1]
            lines.append([(-5, y), (self.W + 5, y)])
            z += spacing
        for k in range(-20, 21):
            x = st.cx + (k * 2.6 + (0.9 if k % 2 else 0.0)) * st.unit
            lines.append([(x, st.floor_y), (x, self.H + 5)])
        self.ink("floor_lines", lines, c, st.lw * 0.7, opacity=opacity, clip=("floor",))

    def window(self, x0, x1, y0, y1, curtains=True, blinds=False):
        st = self.st
        frame = st.wall([(x0 - 0.18, y0 - 0.18), (x1 + 0.18, y0 - 0.18), (x1 + 0.18, y1 + 0.18), (x0 - 0.18, y1 + 0.18)])
        glass = st.wall([(x0, y1), (x1, y1), (x1, y0), (x0, y0)])
        self.flat("window_frame", [frame], "#F6F4F0", line=st.lw)
        self.layers.append(Layer("window_glass", Material.FLAT, col.hex_rgb("#BFD8EE"), polys=[glass],
                                 line=LineSpec(st.lw * 0.8),
                                 gradient_fill=(tuple(glass[0]), tuple(glass[3]), col.hex_rgb("#9EC3E6"),
                                                col.hex_rgb("#E8F1F8"))))
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        self.ink("window_bars", [st.wall([(xm, y0), (xm, y1)]), st.wall([(x0, ym), (x1, ym)])], "#F6F4F0",
                 st.lw * 2.2, opacity=1.0)
        if blinds:
            slats = [st.wall([(x0, y), (x1, y)]) for y in np.arange(y0 + 0.25, y1, 0.32)]
            self.ink("blinds", slats, "#F2F0EC", st.lw * 2.6, opacity=0.85, clip=("window_glass",))
        light = st.wall([(x0, y1), (x1, y1), (x1 + 1.8, 0), (x0 + 1.8, 0)])
        self.flat("window_light", [light], "#FFF4DC", opacity=0.22, clip=("wall", "floor"), blend=Blend.SCREEN,
                  feather=st.unit * 0.6)
        if curtains:
            for side, (a, b) in (("l", (x0 - 1.0, x0 + 0.3)), ("r", (x1 - 0.3, x1 + 1.0))):
                P = st.wall([(a, y1 + 0.5), (b, y1 + 0.5), (b + 0.1, y0 - 1.6), (a - 0.1, y0 - 1.6)])
                self.plane(f"curtain_{side}", [P], self.pal["accent"], (0.0, 0.0, 1.0), line=True, tags=("object",))
                folds = [st.wall([(a + t * (b - a), y1 + 0.5), (a + t * (b - a) + 0.05, y0 - 1.6)])
                         for t in np.linspace(0.2, 0.8, 4)]
                self.ink(f"curtain_{side}_folds", folds,
                         col.rgb_hex(col.shadow_of(col.hex_rgb(self.pal["accent"]), 0.35)), st.lw * 1.4, 0.6,
                         clip=(f"curtain_{side}",))

    def wall_art(self, x0, x1, y0, y1):
        st = self.st
        frame = st.wall([(x0, y1), (x1, y1), (x1, y0), (x0, y0)])
        inner = st.wall([(x0 + 0.2, y1 - 0.2), (x1 - 0.2, y1 - 0.2), (x1 - 0.2, y0 + 0.2), (x0 + 0.2, y0 + 0.2)])
        self.flat("art_frame", [frame], "#3A3430", line=st.lw)
        self.flat("art_canvas", [inner], "#F1ECE4")
        blobs = []
        for k in range(4):
            c = st.wall([(self.rng.uniform(x0 + 0.5, x1 - 0.5), self.rng.uniform(y0 + 0.5, y1 - 0.5))])[0]
            r = st.unit * self.rng.uniform(0.25, 0.55)
            blobs.append(geom.ellipse(c[0], c[1], r, r * self.rng.uniform(0.6, 1.0), 32, rot=self.rng.uniform(0, 3)))
        for k, b in enumerate(blobs):
            hue = ["#D9A38E", "#8FA9C4", "#C9B27A", "#9DB59A"][k]
            self.flat(f"art_blob{k}", [b], hue, clip=("art_canvas",), opacity=0.9)

    def mug(self, x, zf, y):
        kit = self.st.kit(f"mug{len(self.layers)}", x, zf, y)
        top, _, _ = kit.revolution("body", (0.0, 0.0, 0.0), 0.36, [(0, 0.12), (1.0, 0.12)], "#F2EFEA", spec=0.5)
        kit.flat("coffee", [top], "#5A3324", line=self.st.lw * 0.6)
        self.add(kit)

    def prop(self, kind, x, zf, y=0.0, scale=1.0, **obj):
        st = self.st
        layers, _ = props.build_prop(kind, f"{self.room}_{kind}_{len(self.layers)}", st.origin(x, zf, y),
                                     st.unit * scale, st.lw, self.rng, obj)
        self.layers += layers

    # ------------------------------------------------------------ rooms
    def bedroom(self):
        self.shell()
        self.planks()
        self.window(-3.8, -1.2, 3.4, 7.4)
        self.wall_art(2.0, 4.8, 4.8, 6.8)
        bed = "#EFEAE2"
        self.contact("bed_shadow", 0.6, 8.0, 0.0, 6.8)
        self.furniture_box("headboard", 0.6, 8.0, 0.0, 0.3, 0.0, 3.6, "#9C7A5E")
        self.furniture_box("bed_frame", 0.7, 7.9, 0.3, 6.8, 0.0, 0.8, "#9C7A5E")
        self.furniture_box("mattress", 0.8, 7.8, 0.3, 6.7, 0.8, 1.7, bed)
        self.furniture_box("duvet", 0.65, 7.95, 2.0, 6.9, 1.55, 1.95, self.pal["accent"])
        for k, x in enumerate((1.4, 3.6)):
            kit = self.st.kit(f"pillow{k}", x + 0.9, 0.5, 1.7)
            kit.dome("pillow", np.array([0.0, 0.0, -0.6]), 1.0, 0.55, 0.45, "#F7F4EE", spec=0.1)
            self.add(kit)
        self.contact("stand_shadow", -6.2, -4.6, 0.2, 1.6)
        self.furniture_box("nightstand", -6.2, -4.6, 0.2, 1.6, 0.0, 1.9, "#9C7A5E")
        self.prop("lamp", -5.4, 1.2, 1.9, scale=0.8)

    def office(self):
        self.shell()
        self.planks(spacing=1.6, opacity=0.18)
        self.window(1.4, 4.8, 3.2, 7.6, curtains=False, blinds=True)
        desk = "#E8E2D8"
        self.contact("desk_shadow", -5.0, -0.4, 0.0, 2.6)
        for k, x in enumerate((-4.8, -0.7)):
            self.furniture_box(f"desk_leg{k}", x, x + 0.15, 0.2, 2.4, 0.0, 2.4, "#4A4E55")
        self.furniture_box("desk_top", -5.0, -0.4, 0.0, 2.6, 2.4, 2.55, desk)
        self.prop("monitor", -2.9, 0.4, 2.55, scale=0.85)
        self.prop("keyboard", -2.9, 1.7, 2.55, scale=0.8)
        self.prop("lamp", -4.3, 0.5, 2.55, scale=0.8)
        self.prop("plant", -1.0, 0.6, 2.55, scale=0.7)
        self.mug(-1.6, 1.9, 2.55)
        self.contact("shelf_shadow", 5.2, 7.8, 0.0, 1.3)
        faces = self.furniture_box("shelf", 5.2, 7.8, 0.0, 1.3, 0.0, 6.6, "#D5CEC2")
        quad, vis = faces["z0"]
        if vis:
            rows = []
            for k in range(4):
                v0 = 0.08 + k * 0.23
                rows.append(props.sub_quad(quad, 0.05, 0.95, v0, v0 + 0.18))
            self.flat("shelf_backs", rows, "#8C8478", opacity=0.9)
            books = []
            colors = ["#7A3B3B", "#3E5F7A", "#5E7A4A", "#C9A36B", "#6A5A80"]
            for k, row in enumerate(rows):
                u = 0.02
                while u < 0.9:
                    w = self.rng.uniform(0.04, 0.09)
                    hgt = self.rng.uniform(0.55, 0.95)
                    books.append((colors[self.rng.integers(len(colors))], props.sub_quad(row, u, u + w, 1 - hgt, 1.0)))
                    u += w + 0.005
            for c in colors:
                polys = [q for cc, q in books if cc == c]
                self.flat(f"shelf_books_{c[1:]}", polys, c, line=self.st.lw * 0.5)

    def cafe(self):
        st = self.st
        self.shell()
        wood = "#8A6248"
        panel = st.wall([(-20, 0), (20, 0), (20, 3.4), (-20, 3.4)])
        self.plane("wainscot", [panel], wood, WALL_N, line=True, tags=("wall",))
        self.ink("wainscot_seams", [st.wall([(x, 0.3), (x, 3.3)]) for x in np.arange(-20, 20, 1.2)],
                 col.rgb_hex(col.shadow_of(col.hex_rgb(wood), 0.4)), st.lw, 0.6, clip=("wainscot",))
        self.planks(spacing=1.2)
        board = st.wall([(-4.2, 6.8), (-1.0, 6.8), (-1.0, 4.4), (-4.2, 4.4)])
        self.flat("menu_board", [board], "#2E3532", line=st.lw * 1.5)
        chalk = [st.wall([(-3.9, y), (-3.9 + self.rng.uniform(1.2, 2.6), y)]) for y in np.arange(6.4, 4.7, -0.35)]
        self.ink("menu_chalk", chalk, "#E8E4DA", st.lw * 1.3, 0.7, clip=("menu_board",))
        for k, x in enumerate((-2.6, 0.9, 4.4)):
            kit = st.kit(f"pendant{k}", x, 1.0)
            kit.rod("cord", [(0.0, 12.0, 0.0), (0.0, 7.2, 0.0)], 0.03, "#2A2A2A", spec=0.0)
            kit.revolution("shade", (0.0, 6.4, 0.0), 0.8, [(0, 0.55), (0.6, 0.30), (1.0, 0.10)], "#2F3A33", spec=0.5)
            self.add(kit)
            glow = st.origin(x, 1.0, 6.2)
            self.flat(f"pendant{k}_glow", [geom.ellipse(glow[0], glow[1], st.unit * 1.4, st.unit * 0.9, 40)],
                      "#FFE2A8", opacity=0.35, blend=Blend.SCREEN, feather=st.unit * 0.7)
        self.contact("counter_shadow", 1.0, 8.0, 0.0, 2.2)
        self.furniture_box("counter", 1.0, 8.0, 0.0, 2.2, 0.0, 3.2, wood,
                           face_colors={"y1": "#E6E0D6"})
        self.furniture_box("espresso", 1.6, 3.0, 0.3, 1.5, 3.2, 4.6, "#B8BCC2", spec=0.6)
        self.mug(3.6, 1.2, 3.2)
        self.contact("table_shadow", -4.2, -2.4, 3.0, 4.2)
        kit = st.kit("table", -3.3, 3.6)
        kit.revolution("stem", (0.0, 0.0, 0.0), 2.3, [(0, 0.10), (1.0, 0.10)], "#2C2C2C", spec=0.3)
        kit.revolution("top", (0.0, 2.3, 0.0), 0.12, [(0, 0.9), (1.0, 0.9)], "#E6E0D6", spec=0.2)
        self.add(kit)

    def pool(self):
        st, W, H = self.st, self.W, self.H
        fy = st.floor_y
        sky = np.array([(-5, -5), (W + 5, -5), (W + 5, fy + 1), (-5, fy + 1)])
        self.layers.append(Layer("sky", Material.FLAT, col.hex_rgb("#A9D0F0"), polys=[sky],
                                 gradient_fill=((0, 0), (0, fy), col.hex_rgb("#7DB6E8"), col.hex_rgb("#E4F1FA"))))
        # a trimmed hedge: low, with small round bumps along the top
        xs = np.linspace(-5, W + 5, 160)
        bumps = np.abs(np.sin(xs / (st.unit * 0.55))) ** 0.5
        hedge_top = fy - st.unit * (HEDGE_HEIGHT + 0.18 * bumps)
        hedge = np.vstack([np.column_stack([xs, hedge_top]), [(W + 5, fy + 1), (-5, fy + 1)]])
        self.layers.append(Layer("hedge", Material.CLOTH, col.hex_rgb("#5E8A58"), polys=[hedge],
                                 line=LineSpec(st.lw),
                                 shade=ShadeSpec(normal_map=shapes.height_normals(W, H, st.unit * 0.6, 1.6, 5),
                                                 threshold=0.25, rim=0.3), tags=("foliage",)))
        self.shell(wall=False)
        far = st.origin(0, 1.5)[1]
        near = st.origin(0, 5.8)[1]
        water = np.array([(-5, far), (W + 5, far), (W + 5, near), (-5, near)])
        self.layers.append(Layer("water", Material.FLAT, col.hex_rgb(self.pal["accent"]), polys=[water],
                                 line=LineSpec(st.lw),
                                 gradient_fill=((0, far), (0, near), col.hex_rgb("#2F8DBA"), col.hex_rgb("#6CC8E0"))))
        ripples = []
        for k in range(40):
            y = self.rng.uniform(far + 4, near - 4)
            x0 = self.rng.uniform(-0.1, 1.0) * W
            xs = np.linspace(x0, x0 + self.rng.uniform(0.05, 0.18) * W, 12)
            ripples.append(np.column_stack([xs, y + 2.0 * np.sin(xs / W * 40 + k)]))
        self.ink("ripples", ripples, "#E8F6FB", st.lw * 1.2, 0.7, clip=("water",))
        for name, (z0, z1) in (("coping_far", (1.2, 1.5)), ("coping_near", (5.8, 6.2))):
            a, b = st.origin(0, z0)[1], st.origin(0, z1)[1]
            self.flat(name, [np.array([(-5, a), (W + 5, a), (W + 5, b), (-5, b)])], "#F4F2EE", line=st.lw * 0.8)
        self.planks(spacing=1.4, color="#C9BEAE", opacity=0.5)
        for k, x in enumerate((-4.2, 2.6)):
            kit = st.kit(f"lounger{k}", x, 0.9, yaw=0.0)
            for lx in (-1.2, 1.2):
                kit.box(f"leg{int(lx > 0)}", (lx - 0.06, 0.0, -0.30), (0.12, 0, 0), (0, 0.45, 0), (0, 0, 0.6), "#B8B2A8")
            kit.box("seat", (-1.4, 0.45, -0.35), (2.8, 0, 0), (0, 0.22, 0), (0, 0, 0.7), self.pal["accent"])
            kit.box("back", (-1.4, 0.67, -0.35), (0.22, 0, 0), (-0.6, 1.0, 0), (0, 0, 0.7), self.pal["accent"])
            self.add(kit)
        kit = st.kit("umbrella", -6.0, 0.8)
        kit.rod("pole", [(0.0, 0.0, 0.0), (0.0, 4.2, 0.0)], 0.05, "#E8E2D6")
        kit.revolution("canopy", (0.0, 3.6, 0.0), 0.9, [(0, 1.9), (1.0, 0.05)], "#E8774E", spec=0.1)
        self.add(kit)

    def gym(self):
        st = self.st
        self.shell()
        mirror = st.wall([(-20, 7.2), (20, 7.2), (20, 1.4), (-20, 1.4)])
        self.layers.append(Layer("mirror", Material.FLAT, col.hex_rgb("#AEB8C2"), polys=[mirror],
                                 line=LineSpec(st.lw),
                                 gradient_fill=(tuple(mirror[0]), tuple(mirror[3]), col.hex_rgb("#C7D0D8"),
                                                col.hex_rgb("#8E99A5"))))
        glare = [st.wall([(x, 7.2), (x + 1.2, 7.2), (x - 1.0, 1.4), (x - 2.2, 1.4)]) for x in (-3.0, 2.5, 6.0)]
        self.flat("mirror_glare", glare, "#FFFFFF", opacity=0.12, clip=("mirror",))
        a, b = st.floor_y, self.H + 5
        tiles = [[(-5, st.origin(0, z)[1]), (self.W + 5, st.origin(0, z)[1])] for z in np.arange(2.0, 30, 2.0)]
        tiles += [[(st.cx + x * st.unit, a), (st.cx + x * st.unit, b)] for x in np.arange(-20, 21, 2.0)]
        self.ink("mats", tiles, "#26282C", st.lw, 0.7, clip=("floor",))
        self.contact("rack_shadow", -5.0, -1.2, 0.2, 1.6)
        self.furniture_box("rack", -5.0, -1.2, 0.2, 1.6, 0.0, 2.6, "#2E3136", spec=0.4)
        for k, (y, r) in enumerate(((1.1, 0.22), (2.0, 0.18))):
            for j, x in enumerate(np.linspace(-4.6, -1.6, 5)):
                kit = st.kit(f"db{k}_{j}", x, 0.6, y)
                kit.rod("bar", [(-0.18, r, 0.0), (0.18, r, 0.0)], 0.04, "#9AA0A8")
                for s in (-0.22, 0.22):
                    # a plate seen edge-on: short along the bar, as tall as its diameter
                    kit.rod(f"plate{int(s > 0)}", [(s - 0.04, r, 0.0), (s + 0.04, r, 0.0)], r, self.pal["accent"],
                            spec=0.2)
                self.add(kit)
        self.contact("bench_shadow", 1.2, 4.6, 2.0, 3.4)
        for k, x in enumerate((1.5, 4.1)):
            self.furniture_box(f"bench_leg{k}", x, x + 0.18, 2.2, 3.2, 0.0, 1.4, "#2E3136")
        self.furniture_box("bench_pad", 1.2, 4.6, 2.0, 3.4, 1.4, 1.75, "#26282C", spec=0.3)
        for k, x in enumerate((5.6, 6.6)):
            kit = st.kit(f"kettlebell{k}", x, 2.4)
            kit.dome("bell", np.array([0.0, 0.0, 0.0]), 0.34, 0.34, 0.60, "#2B2D31", spec=0.5)
            kit.rod("handle", [(-0.2, 0.55, 0.0), (-0.18, 0.85, 0.0), (0.18, 0.85, 0.0), (0.2, 0.55, 0.0)], 0.06,
                    "#2B2D31")
            self.add(kit)

    def build(self):
        getattr(self, self.room)()
        return self.layers


def build(spec, W, H, light, seed):
    """Scene entry point; a character backdrop passes framing and head scale through the spec."""
    it = dict(spec.get("interior", {}))
    room = it.get("room", "bedroom")
    if room not in ROOMS:
        raise ValueError(f"unknown interior room: {room!r} (allowed: {', '.join(ROOMS)})")
    framing = spec.get("framing", "full") if spec.get("_backdrop") else "full"
    head_scale = float(spec.get("character", {}).get("head_scale", 1.0)) if spec.get("_backdrop") else 1.0
    layers = RoomBuilder(it, W, H, light, seed, framing, head_scale).build()
    bg = np.broadcast_to(col.hex_rgb(PALETTES[room]["wall"]), (H, W, 3)).astype(np.float32).copy()
    lit = Light(key=light.key, key_color=light.key_color, rim_dir=light.rim_dir, rim_color=light.rim_color,
                rim_strength=light.rim_strength * 0.6)
    return layers, bg, lit
