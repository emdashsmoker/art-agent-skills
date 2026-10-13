"""Things a figure holds in a hand: a phone, a mug, a book, an umbrella.

Each is drawn upright in the picture around the grip point of a closed hand (Hand shape "grip"); the
fingers are drawn after it, so they wrap over its near side. Sizes are in head heights (hu) of the figure.
"""
import numpy as np

from ..color import mix
from ..geometry import catmull_rom, ellipse, Ribbon
from ..scene import Part, Line, Stroke

PHONE = dict(w=0.30, h=0.64, r=0.05)               # hu
MUG = dict(r=0.19, h=0.44)
BOOK = dict(w=0.74, h=1.00, t=0.10, grip=0.12)     # grip: how far below its top edge the hand holds it
# shaft: grip to the top of the canopy; radius: half the open canopy; dome: canopy height above its rim;
# rim_bow: the near edge of the rim sags below the far edge (we look a little up at it); 8 ribs, 4 on the near half
UMBRELLA = dict(shaft=2.75, radius=2.3, dome=0.85, rim_bow=0.16, scallop=0.07, ribs=8, hook=0.36)


def _box(cx, cy, w, h, r, n=5):
    a = np.linspace(0, np.pi / 2, n)
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    corners = [(x1 - r, y0 + r, -np.pi / 2), (x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, np.pi / 2), (x0 + r, y0 + r, np.pi)]
    return np.vstack([np.stack([x + r * np.cos(a0 + a), y + r * np.sin(a0 + a)], 1) for x, y, a0 in corners])


def _line(u, color, width=1.7):
    return Line(width * u / 150.0, color=mix(color, "#0c0a14", 0.6))


def phone(c, u, name, color="#23262d", screen=False):
    """A phone seen from its back (the holder looks at the screen), or from the screen side."""
    w, h, r = PHONE["w"] * u, PHONE["h"] * u, PHONE["r"] * u
    body = Part(name, color, polys=[_box(c[0], c[1], w, h, r)], material="gloss", bulge=0.35, line=_line(u, color),
                group="held")
    parts = [body]
    if screen:
        parts.append(Part(name + "_screen", "#4a7fd0", polys=[_box(c[0], c[1], w * 0.88, h * 0.92, r * 0.8)],
                          shade=False, material="flat", receive=False,
                          gradient=((c[0], c[1] - h / 2), "#3b6fb6", (c[0], c[1] + h / 2), "#d9a6c8")))
    else:                                           # camera block in the upper corner
        cam = np.array([c[0] - w * 0.22, c[1] - h * 0.34])
        parts.append(Part(name + "_cam", mix(color, "#000000", 0.35), polys=[_box(cam[0], cam[1], w * 0.36, w * 0.36, w * 0.08)],
                          material="gloss", bulge=0.3, line=_line(u, color, 1.0), group="held"))
        for dy in (-0.07, 0.07):
            p = cam + np.array([0, dy * w])
            parts.append(Part(name + "_lens", "#0c0e14", polys=[ellipse(p[0], p[1], 0.05 * w, 0.05 * w)], shade=False,
                              material="flat", receive=False))
    parts.append(Part(name + "_glint", "#ffffff", polys=[np.array([(c[0] - w * 0.40, c[1] - h * 0.46),
                                                                   (c[0] - w * 0.30, c[1] - h * 0.46),
                                                                   (c[0] - w * 0.30, c[1] + h * 0.30),
                                                                   (c[0] - w * 0.40, c[1] + h * 0.30)])],
                      shade=False, material="flat", alpha=0.18, blur=0.01 * u, blend="screen", clip=name, receive=False))
    return parts


def mug(c, u, name, color="#e8e2d6", drink="#5a3726"):
    """An upright mug, the hand around its body; the handle shows on the far side."""
    r, h = MUG["r"] * u, MUG["h"] * u
    k = 0.30                                        # the rim ellipse: we look a little down on it
    top, bot = c + [0, -h / 2], c + [0, h / 2]
    a = np.linspace(0, np.pi, 20)
    wall = np.vstack([np.stack([bot[0] + r * np.cos(a), bot[1] + r * k * np.sin(a)], 1),
                      np.stack([top[0] - r * np.cos(a), top[1] - r * k * np.sin(a)], 1)])
    hc = c + [-r, -0.02 * u]
    loop = catmull_rom(np.array([hc + [0.02 * u, -0.13 * u], hc + [-0.12 * u, -0.11 * u], hc + [-0.14 * u, 0.01 * u],
                                 hc + [-0.09 * u, 0.11 * u], hc + [0.02 * u, 0.12 * u]]), samples=8)
    parts = [Part(name + "_handle", color, ribbon=Ribbon(loop, [(0, 0.025 * u), (1, 0.025 * u)], step=2.0),
                  material="gloss", line=_line(u, color), group="held"),
             Part(name, color, polys=[wall], material="gloss", bulge=0.5, line=_line(u, color), group="held"),
             Part(name + "_rim", mix(color, "#000000", 0.08), polys=[ellipse(top[0], top[1], r, r * k)], shade=False,
                  material="flat", line=_line(u, color, 1.2), receive=False),
             Part(name + "_drink", drink, polys=[ellipse(top[0], top[1] + 0.012 * u, r * 0.84, r * k * 0.78)], shade=False,
                  material="flat", receive=False)]
    for ox in (-0.04, 0.05):                        # steam
        ys = np.linspace(0, 1, 10)
        path = np.stack([top[0] + (ox + 0.03 * np.sin(ys * 6 + ox * 40)) * u, top[1] - (0.05 + 0.35 * ys) * u], 1)
        parts.append(Part(name + "_steam", "#ffffff", polys=[path[:1]], alpha=0.0, shade=False, material="flat",
                          strokes=[Stroke(path, width=0.02 * u, color="#ffffff", alpha=0.45, taper=(True, True))]))
    return parts


def book(c, u, name, color="#7a2f3a"):
    """A closed hardcover held near its top edge: cover, a band across it, the page block along the side."""
    w, h, t = BOOK["w"] * u, BOOK["h"] * u, BOOK["t"] * u
    cy = c[1] - BOOK["grip"] * u + h / 2
    pages = Part(name + "_pages", "#f1ead8", polys=[_box(c[0] + t * 0.6, cy - t * 0.3, w, h, 0.01 * u)], material="matte",
                 bulge=0.2, line=_line(u, "#c9bfa6"), group="held")
    cover = Part(name, color, polys=[_box(c[0], cy, w, h, 0.012 * u)], material="matte", bulge=0.25, line=_line(u, color),
                 group="held")
    band = Part(name + "_band", mix(color, "#f3e3b0", 0.7), polys=[_box(c[0], cy - h * 0.22, w * 0.7, h * 0.08, 0.005 * u)],
                shade=False, material="flat", clip=name, receive=False)
    spine = Part(name + "_spine", mix(color, "#000000", 0.25), polys=[_box(c[0] - w / 2 + 0.03 * u, cy, 0.06 * u, h, 0.005 * u)],
                 shade=False, material="flat", clip=name, receive=False)
    return [pages, cover, band, spine]


def umbrella(c, u, name, color="#2b3a5c", clear=False):
    """An open umbrella held upright: hook handle below the fist, the shaft up to a dome canopy over the head.

    The canopy is drafted as a dome seen from the side: its outline is the silhouette profile, the rim is the
    lower half of a flat ellipse with the fabric rising between the rib tips, and each visible rib is the
    silhouette profile narrowed by the cosine of its angle around the shaft (the meridians of the dome).
    clear=True: a transparent vinyl canopy that lets the scene show through."""
    U = UMBRELLA
    R, H, bow = U["radius"] * u, U["dome"] * u, U["rim_bow"] * u
    apex = c + [0.0, -U["shaft"] * u]
    rim_y = apex[1] + H
    half = U["ribs"] // 2
    step = np.pi / half

    def meridian(phi, t):                              # t = 0 at the apex, pi/2 at the rim
        return np.stack([apex[0] + R * np.sin(t) * np.cos(phi), rim_y - H * np.cos(t) + bow * np.sin(phi) * np.sin(t)], 1)

    phis = np.linspace(0.0, np.pi, 24 * half + 1)
    frac = (phis % step) / step
    rim = np.stack([apex[0] + R * np.cos(phis), rim_y + bow * np.sin(phis) - U["scallop"] * u * np.sin(np.pi * frac)], 1)
    t = np.linspace(0.0, np.pi / 2, 24)
    outline = np.vstack([rim, meridian(np.pi, t[::-1])[1:], meridian(0.0, t)[1:-1]])
    fabric = "#dfe9f4" if clear else color
    ink = Line(1.4 * u / 150.0, color="#f4f8ff" if clear else mix(color, "#0c0a14", 0.6), alpha=0.9 if clear else 1.0)
    shaft = np.array([c + [0.0, 0.36 * u], apex])
    hook = catmull_rom(np.array([c + [0.0, 0.30 * u], c + [0.01 * u, 0.30 * u + U["hook"] * u * 0.55],
                                 c + [0.13 * u, 0.30 * u + U["hook"] * u * 0.80], c + [0.24 * u, 0.30 * u + U["hook"] * u * 0.55],
                                 c + [0.25 * u, 0.30 * u + U["hook"] * u * 0.25]]), samples=8)
    ribs = [Stroke(meridian(k * step, t), width=1.1 * u / 150.0, color="#f4f8ff" if clear else mix(color, "#0c0a14", 0.55),
                   alpha=0.8, taper=(False, True), clip=True) for k in range(1, half)]
    tip = np.array([apex, apex + [0.0, -0.20 * u]])
    return [Part(name + "_shaft", "#2a2a30", ribbon=Ribbon(shaft, [(0, 0.028 * u), (1, 0.022 * u)], step=2.0),
                 material="gloss", line=_line(u, "#2a2a30", 1.0), group="held"),
            Part(name + "_hook", "#4a2e22", ribbon=Ribbon(hook, [(0, 0.05 * u), (1, 0.045 * u)], step=2.0),
                 material="gloss", line=_line(u, "#4a2e22"), group="held"),
            Part(name + "_tip", "#2a2a30", ribbon=Ribbon(tip, [(0, 0.03 * u), (1, 0.015 * u)], step=2.0), material="gloss",
                 group="held"),
            Part(name, fabric, polys=[outline], material="gloss" if clear else "cloth", bulge=0.6, alpha=0.38 if clear else 1.0,
                 line=ink, strokes=ribs, group="held")]


ITEMS = {"phone": phone, "mug": mug, "book": book, "umbrella": umbrella,
         "clear_umbrella": lambda c, u, name: umbrella(c, u, name, clear=True)}
