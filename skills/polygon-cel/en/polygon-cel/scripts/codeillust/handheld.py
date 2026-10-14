"""Objects held in one hand: phone, canned drink, cigarette.

A held object sits between the palm and the fingers: body.hand_layers draws the palm,
then the object (mid layers), then the fingers wrapped over it, so the hand reads as
gripping. Light the object gives off or puts out (screen glow, smoke) goes on top of
the whole figure (late layers). Positions are body-local (H units) relative to the wrist
of the image-right arm and mirror for the image-left arm.
"""
import numpy as np

from . import color as col
from . import config as cfg
from . import geom, shapes
from .scene import Blend, Layer, LineSpec, Material, ShadeSpec

# arm setups per item (image-right arm; wrist_shift 0 keeps a hand that touches the body in place)
HOLD_ARMS = {
    # the palm cradles the phone's back from below (screen up toward the face, back toward the viewer):
    # the back of the hand faces the viewer and the fingers curl around the phone's far long edge
    # the thumb rests on the screen, the side facing away from the viewer, so it goes behind the phone
    "phone": {"elbow": (0.70, 1.42), "wrist": (0.30, 1.10), "forearm": "front", "hand": "grip",
              "fingers": (-1.0, -0.10, 0.0), "palm": (0.0, -0.55, -0.83), "wrist_shift": 0.0,
              "thumb_behind": True},
    # back of the hand toward the viewer, palm on the can's front, fingers curling around its far edge;
    # the wrist sits above the hoodie pocket, which is drawn over anything lower
    "can": {"elbow": (0.74, 1.40), "wrist": (0.56, 1.40), "forearm": "front", "hand": "grip",
            "fingers": (-1.0, 0.05, 0.0), "palm": (0.0, 0.0, -1.0), "wrist_shift": 0.0},
    # elbow a little bent so the hand (and the smoke) stays at hip height, inside a waist-up frame
    "cigarette": {"elbow": (0.80, 1.32), "wrist": (0.74, 2.02), "forearm": "front", "hand": "relaxed",
                  "palm": (-0.92, 0.0, -0.38)},
}
ITEMS = tuple(HOLD_ARMS)
# offsets of the can and the phone are measured from the knuckles (see _knuckle_anchor)
PHONE = {"offset": (0.0, -0.18), "size": (0.30, 0.46), "tilt": -8.0, "color": "#24262C", "glow": "#CFE0FF",
         "glow_radius": (0.34, 0.38), "glow_drop": 0.18, "glow_opacity": 0.25}
# a 355 ml can is about 12 x 6.6 cm against a 23 cm head (0.50 x 0.28 H)
CAN = {"offset": (-0.04, 0.04), "width": 0.28, "height": 0.50, "color": "#B04A3A", "lid": "#C8CCD2"}
KNUCKLE_REACH = 0.33     # wrist to knuckles of the unscaled hand (hand.MCP), along the fingers
BEHIND_HAND_TAG = "behind_hand"   # a held object wrapped by the whole hand: drawn before the palm and fingers
HELD_HAND_TAG = "held_hand"       # parts of the hand that holds an object
HELD_TAGS = ("held", HELD_HAND_TAG)   # garment details drawn later (drawstrings) are cut by these masks
# the cigarette passes under the curled fingers (clamped between them) and points out past the hand
CIGARETTE = {"offset": (-0.14, 0.36), "dir": (0.18, 0.12), "width": 0.032, "paper": "#F2EEE6", "ember": "#FF7A3A",
             "smoke": "#C8CCD6", "smoke_rise": 1.25, "smoke_drift": 0.50}
Z_FRONT = 0.30           # depth of a held object in front of the body


def _rounded_rect(c, w, h, r, n=6):
    """Closed outline of a w x h rectangle centered at c with corner radius r."""
    pts = []
    for (sx, sy), a0 in (((1, 1), 0.0), ((-1, 1), 90.0), ((-1, -1), 180.0), ((1, -1), 270.0)):
        cc = np.array([c[0] + sx * (w / 2 - r), c[1] + sy * (h / 2 - r)])
        a = np.radians(np.linspace(a0, a0 + 90.0, n))
        pts.append(cc + r * np.column_stack([np.cos(a), np.sin(a)]))
    return np.vstack(pts)


def _anchor(body, side, offset):
    _, _, w = body.joints(side)
    return w + np.array([offset[0] * side, offset[1]])


def _knuckle_anchor(body, side, offset):
    """Point offset from the knuckles of a grip hand: a wrapped object stands under them, so the first
    phalanges cross its front and the bent ones end at its far edge (a larger hand reaches further)."""
    return _anchor(body, side, (offset[0] - KNUCKLE_REACH * body.hand_scale, offset[1]))


def phone_layers(body, side):
    H = body.H
    c = _knuckle_anchor(body, side, PHONE["offset"])
    w, h = PHONE["size"]
    rect = geom.rotate(_rounded_rect(c, w, h, min(w, h) * 0.18), np.radians(PHONE["tilt"] * side), center=c)
    poly = body.to_canvas(rect, Z_FRONT)
    color = col.hex_rgb(PHONE["color"])
    mid = [Layer(f"phone_{side}", Material.CLOTH, color, polys=[poly], line=LineSpec(cfg.LINE_DETAIL * H),
                 shade=ShadeSpec(normal_map=shapes.plane_normals((0.0, -0.2, 1.0)), threshold=0.1, spec=0.9,
                                 spec_edge=0.95), tags=("held", BEHIND_HAND_TAG))]
    # the screen faces the holder: its light spills on the hands around it as a soft cold glow; a larger glow
    # raised over the chest read as a white blot there (v13 doomer pair)
    top = body.to_canvas(np.array([c + [0.0, -h * 0.5]]), Z_FRONT)[0]
    rx, ry = PHONE["glow_radius"]
    glow = geom.ellipse(top[0], top[1] + PHONE["glow_drop"] * H, rx * H, ry * H, 48)
    late = [Layer(f"phone_glow_{side}", Material.GLOW, col.hex_rgb(PHONE["glow"]), polys=[glow], blend=Blend.SCREEN,
                  feather=0.20 * H, opacity=PHONE["glow_opacity"])]
    return mid, late


def can_layers(body, side):
    H = body.H
    c = _knuckle_anchor(body, side, CAN["offset"])
    w, h = CAN["width"], CAN["height"]
    body_poly = np.array([(c[0] - w / 2, c[1] - h / 2), (c[0] + w / 2, c[1] - h / 2), (c[0] + w / 2, c[1] + h / 2),
                          (c[0] - w / 2, c[1] + h / 2)])
    bottom = geom.ellipse(c[0], c[1] + h / 2, w / 2, w * 0.14, 32)
    lid = geom.ellipse(c[0], c[1] - h / 2, w / 2, w * 0.14, 32)
    cc = body.to_canvas(np.array([c]), Z_FRONT)[0]
    normals = shapes.revolution_normals(cc[0], np.array([cc[1] - h / 2 * H, cc[1] + h / 2 * H]),
                                        np.array([w / 2 * H, w / 2 * H]))
    line = LineSpec(cfg.LINE_DETAIL * H)
    tags = ("held", BEHIND_HAND_TAG)
    mid = [Layer(f"can_{side}", Material.CLOTH, col.hex_rgb(CAN["color"]),
                 polys=[body.to_canvas(body_poly, Z_FRONT), body.to_canvas(bottom, Z_FRONT)], line=line,
                 shade=ShadeSpec(normal_map=normals, threshold=0.1, spec=1.0, spec_edge=0.9), tags=tags),
           Layer(f"can_lid_{side}", Material.CLOTH, col.hex_rgb(CAN["lid"]), polys=[body.to_canvas(lid, Z_FRONT)],
                 line=line, shade=ShadeSpec(normal_map=shapes.plane_normals((0.0, -0.9, 0.4)), spec=1.0),
                 tags=tags)]
    return mid, []


def cigarette_layers(body, side):
    H = body.H
    p0 = _anchor(body, side, CIGARETTE["offset"])
    d = np.array([CIGARETTE["dir"][0] * side, CIGARETTE["dir"][1]])
    p1 = p0 + d
    stick = body.to_canvas(np.array([p0 - d * 0.35, p1]), Z_FRONT)
    tip = body.to_canvas(np.array([p1]), Z_FRONT)[0]
    mid = [Layer(f"cigarette_{side}", Material.CLOTH, col.hex_rgb(CIGARETTE["paper"]),
                 strokes=[(stick, np.full(2, CIGARETTE["width"] * H))], line=LineSpec(cfg.LINE_DETAIL * H * 0.8),
                 tags=("held",)),
           Layer(f"ember_{side}", Material.GLOW, col.hex_rgb(CIGARETTE["ember"]),
                 polys=[geom.ellipse(tip[0], tip[1], 0.022 * H, 0.020 * H, 16)], tags=("held",))]
    # smoke: a thin wavy ribbon rising from the ember, widening and fading as it climbs
    rng = np.random.default_rng(int(abs(tip[0]) + abs(tip[1])))
    n = 40
    t = np.linspace(0, 1, n)
    sway = np.sin(t * np.pi * 3 + rng.uniform(0, np.pi)) * 0.10 * t + np.sin(t * np.pi * 7) * 0.025
    # the smoke drifts away from the body: rising straight up it ran along the sleeve like a highlight (v13)
    drift = side * CIGARETTE["smoke_drift"] * t ** 0.8
    pts = np.column_stack([tip[0] + (sway + drift) * H, tip[1] - t * CIGARETTE["smoke_rise"] * H])
    widths = (0.010 + 0.05 * t) * H
    late = [Layer(f"smoke_{side}", Material.GLOW, col.hex_rgb(CIGARETTE["smoke"]), strokes=[(pts, widths)],
                  blend=Blend.SCREEN, feather=0.02 * H, opacity=0.45),
            Layer(f"ember_glow_{side}", Material.GLOW, col.hex_rgb(CIGARETTE["ember"]),
                  polys=[geom.ellipse(tip[0], tip[1], 0.07 * H, 0.07 * H, 24)], blend=Blend.SCREEN, feather=0.03 * H,
                  opacity=0.5)]
    return mid, late


BUILDERS = {"phone": phone_layers, "can": can_layers, "cigarette": cigarette_layers}


def layers(body, side, item):
    """(mid layers between palm and fingers, late layers over the figure) of a held item."""
    return BUILDERS[item](body, side)
