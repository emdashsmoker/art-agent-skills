"""Small accessories: necklace (body stage), hairpin, earrings and beanie (head stage)."""
import numpy as np

from . import color as col
from . import config as cfg
from . import geom
from .body import front_z
from .scene import Layer, LineSpec, Material, ShadeSpec

GOLD = "#E3C27A"
# knit beanie over the cranium sphere (head-local units): the cuff's lower edge runs lower at the back of the head
BEANIE = {"radius": 0.435, "front_y": 0.31, "back_y": 0.40, "cuff": 0.11, "color": "#2E3038", "ribs": 26}
SKULL_CENTER = (0.0, 0.40, 0.0)


def _ring(rig, R, y_front, y_back, n=96):
    """Canvas points and view depth of a ring on the cranium sphere, theta 0 facing the viewer."""
    th = np.linspace(-np.pi, np.pi, n)
    y = y_front + (y_back - y_front) * (1 - np.cos(th)) / 2
    rho = np.sqrt(np.clip(R * R - (y - SKULL_CENTER[1]) ** 2, 0, None))
    P3 = np.column_stack([rho * np.sin(th), y, rho * np.cos(th)])
    return rig.head(P3), rig.depth(P3)


def _front_run(pts, depth):
    """The contiguous visible run of a ring around theta 0 (the middle sample)."""
    vis = depth > 0
    mid = len(pts) // 2
    lo = hi = mid
    while lo > 0 and vis[lo - 1]:
        lo -= 1
    while hi < len(pts) - 1 and vis[hi + 1]:
        hi += 1
    return pts[lo:hi + 1], (lo, hi)


def beanie_layers(rig, ch):
    """Knit beanie seen with the front rig (front and back views): dome, folded cuff, rib lines."""
    H = rig.H
    b = BEANIE
    R = b["radius"] + 0.03 * (float(ch["hair"].get("volume", 1.0)) - 1.0)
    color = col.hex_rgb(ch.get("beanie_color", b["color"]))
    low, d_low = _ring(rig, R, b["front_y"], b["back_y"])
    up, d_up = _ring(rig, R, b["front_y"] - b["cuff"], b["back_y"] - b["cuff"])
    edge, (lo, hi) = _front_run(low, d_low)
    c = rig.head([SKULL_CENTER])[0]
    a0 = np.arctan2(edge[-1][1] - c[1], edge[-1][0] - c[0])
    a1 = np.arctan2(edge[0][1] - c[1], edge[0][0] - c[0])
    # from the right end of the cuff over the top of the head (canvas y down, so the top is at -90 degrees)
    if a1 > a0:
        a1 -= 2 * np.pi
    arc = np.linspace(a0, a1, 64)
    dome = np.vstack([edge, np.column_stack([c[0] + R * H * np.cos(arc), c[1] + R * H * np.sin(arc)])])
    cuff = np.vstack([low[lo:hi + 1], up[lo:hi + 1][::-1]])
    ribs = [(np.array([low[k], up[k]]), np.full(2, 0.0030 * H))
            for k in range(lo, hi + 1, max((hi - lo) // b["ribs"], 1))]
    line = LineSpec(cfg.LINE_HAIR * H)
    return [Layer("beanie", Material.CLOTH, color, polys=[dome], line=line,
                  shade=ShadeSpec(inflate=0.10 * H, threshold=0.15, rim=0.6), tags=("accessory", "hat")),
            Layer("beanie_cuff", Material.CLOTH, col.shadow_of(color, 0.08), polys=[cuff], line=line, clip=("beanie",),
                  shade=ShadeSpec(inflate=0.03 * H, threshold=0.15), tags=("accessory", "hat")),
            Layer("beanie_ribs", Material.INK, col.shadow_of(color, 0.35), strokes=ribs, clip=("beanie_cuff",),
                  opacity=0.6)]


def body_accessories(rig, ch):
    items = ch.get("accessories", [])
    H = rig.H
    layers = []
    if "necklace" in items:
        chain = geom.catmull_rom(np.array([(-0.175, 0.00), (-0.12, 0.20), (0.0, 0.36), (0.12, 0.20), (0.175, 0.00)]), 12)
        pts3 = np.column_stack([chain, front_z(chain[:, 0]) + 0.02])
        spine = rig.body(pts3)
        gold = col.hex_rgb(GOLD)
        layers.append(Layer("necklace_chain", Material.INK, gold, strokes=[(spine, np.full(len(spine), 0.0040 * H))],
                            tags=("accessory",)))
        pend = rig.body(np.array([(0.0, 0.405, 0.28)]))[0]
        drop = geom.catmull_rom(np.array([(0, -0.030), (0.020, 0.005), (0.0, 0.035), (-0.020, 0.005)]) * H + pend, 6,
                                closed=True)
        layers.append(Layer("necklace_pendant", Material.CLOTH, gold, polys=[drop], line=LineSpec(0.0032 * H),
                            shade=ShadeSpec(inflate=0.015 * H, spec=1.0), tags=("accessory",)))
    return layers


def head_accessories(rig, ch, hair_b):
    items = ch.get("accessories", [])
    H = rig.H
    layers = []
    if "hairpin" in items:
        ps = hair_b.part_side
        color = col.hex_rgb(ch.get("hairpin_color", GOLD))
        polys = []
        for k, off in enumerate((0.0, 0.045)):
            c3 = hair_b.S(ps * (0.235 + off * 0.3), 0.30 + off, 0.035)
            c = rig.head([c3])[0]
            a = np.linspace(-np.pi / 2, np.pi / 2, 12)
            cap = np.column_stack([0.010 * np.cos(a), 0.010 * np.sin(a)])
            bar = np.vstack([cap + [0.055, 0.0], (-cap) + [-0.055, 0.0]])
            polys.append(geom.rotate(bar, np.radians(-32 * ps) + rig.roll) * H + c)
        layers.append(Layer("hairpin", Material.CLOTH, color, polys=polys, line=LineSpec(0.0032 * H),
                            shade=ShadeSpec(inflate=0.01 * H, spec=1.0), tags=("accessory",)))
    if "beanie" in items:
        layers += beanie_layers(rig, ch)
    if "earrings" in items and ch["hair"].get("ears", "hidden") == "visible":
        for side in (-1, 1):
            lobe = rig.head([(side * 0.385, 0.735, -0.01)])[0]
            drop = geom.ellipse(lobe[0], lobe[1] + 0.035 * H, 0.013 * H, 0.022 * H, 24)
            layers.append(Layer(f"earring_{side}", Material.CLOTH, col.hex_rgb(GOLD), polys=[drop],
                                line=LineSpec(0.003 * H), shade=ShadeSpec(inflate=0.01 * H, spec=1.0)))
    return layers
