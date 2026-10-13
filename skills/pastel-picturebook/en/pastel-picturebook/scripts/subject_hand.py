"""Hand studies: one or more hands on toned paper, each with its own pose and placement."""
import numpy as np

import kit
import relief
from anatomy_hand import PALM_LINES, PALM_PADS, build_hand
from figure import Figure
from painter import Scene, run_hook
from raster import blur, ellipse, fill, mix, multiply, noise, over, rgb, screen, shift, smooth, stroke_many, taper

UNIT_SHARE = 0.19
FOCUS_HAND = 0.6
# The forearm fades into the paper over this stretch of the palm-to-forearm path.
FADE_START, FADE_END = 0.80, 0.98
# Knuckles: swelling on the back of the hand at the root of each finger (shares of hand length).
KNUCKLE_RADIUS, KNUCKLE_DEPTH = 0.050, 0.014
# A nail is drawn only if the last finger bone looks at least this many tip-widths long.
NAIL_MIN_LENGTH = 2.6
# A man's hand: broader (width multiplier), bonier knuckles, shorter and paler nails, veins on the back.
BUILD = {"female": {"width": 1.0, "knuckle": 1.0, "nail": (0.78, 0.42), "nail_tint": 1.0, "veins": 0},
         "male": {"width": 1.15, "knuckle": 1.6, "nail": (0.70, 0.36), "nail_tint": 0.35, "veins": 3}}
# Veins over the back of the hand, from the wrist toward the knuckles, in hand units (x across, y toward the fingers < 0).
VEINS = [[(-0.06, -0.02), (-0.09, -0.12), (-0.13, -0.24), (-0.15, -0.33)],
         [(0.02, -0.03), (0.01, -0.14), (0.04, -0.25), (0.03, -0.34)],
         [(0.10, -0.04), (0.13, -0.15), (0.15, -0.26)]]


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light),
                 seed=spec["seed"], spec=spec)
    fig.focus = np.zeros(fig.size, np.float32)
    return fig


def paint_paper(scene):
    """Toned paper with a faint mottle."""
    paper = scene.style["palette"]["paper"]
    scene.image[:] = kit.vertical_gradient(scene.size, [(0.0, paper["top"]), (1.0, paper["bottom"])])
    cloud = noise(scene.size, scene.size[1] * 0.18, scene.fig.seed + 3, 3)
    scene.image *= (1.0 + 0.10 * (cloud - 0.5) * (scene.shade_on and not scene.cel))[..., None]


def finger_axis(joints):
    """Unit direction of a finger's last bone and its normal."""
    along = joints[-1] - joints[-2]
    along = along / max(np.linalg.norm(along), 1e-6)
    return along, np.array([-along[1], along[0]])


def paint_nails(scene, hand, visible, build):
    """Fingernails on the back view: a pale plate with a highlight, set into the last bone."""
    tones = dict(scene.style["palette"]["nail"])
    plate_width, plate_length = build["nail"]
    tint = build["nail_tint"]
    tones["base"] = mix(rgb(scene.style["palette"]["skin"]["light"]), rgb(tones["base"]), tint)
    for name, joints in hand.joints.items():
        if name in hand.folded:
            continue
        along, _ = finger_axis(joints)
        last = np.linalg.norm(joints[-1] - joints[-2])
        tip_width = hand.widths[name][-1]
        if last < tip_width * NAIL_MIN_LENGTH:
            continue  # the fingertip points at the viewer; its nail is turned out of sight
        center = joints[-1] - along * last * 0.18
        angle = np.degrees(np.arctan2(along[1], along[0])) + 90
        plate = fill(scene.size, ellipse(center, tip_width * plate_width, last * plate_length, 28, angle))
        over(scene.image, tones["base"], plate * visible, 0.85)
        if scene.shade_on:
            glint = fill(scene.size, ellipse(center - np.sign(scene.fig.light[0]) * np.array([-tip_width * 0.25, 0]) - along * last * 0.05,
                                             tip_width * 0.22, last * 0.26, 16, angle))
            screen(scene.image, rgb(tones["light"]), scene.soften(glint, 0.004) * plate * visible, 0.6)
        if scene.lines_on:
            kit.ink_edges(scene, plate * visible, 1.2, "skin", "deep", opacity=0.7)


def paint_creases(scene, hand, visible):
    """Skin folds across each finger joint, and the hollow between tendons on the back of the hand."""
    marks = []
    for name, joints in hand.joints.items():
        if name in hand.folded:
            continue
        for index in range(2, len(joints) - 1):
            along = joints[index + 1] - joints[index - 1]
            along = along / max(np.linalg.norm(along), 1e-6)
            across = np.array([-along[1], along[0]])
            half = hand.widths[name][index] * 0.72
            for offset in ((-0.10, 0.10) if index == 2 else (0.0,)):
                middle = joints[index] + along * offset * hand.scale * 0.1
                arc = smooth([middle - across * half, middle - along * half * 0.18, middle + across * half])
                marks.append((arc, max(hand.scale * 0.004, 1.0) * taper(len(arc), 0.2, 0.2)))
    over(scene.image, rgb(scene.style["palette"]["skin"]["deep"]), stroke_many(scene.size, marks) * visible, 0.45)


def palm_pads(scene, hand):
    """Height of the palm's soft pads (thumb mound, outer edge, finger roots, fingertips) and its hollow."""
    scale = hand.scale
    total = np.zeros(scene.size, np.float32)
    for center, radius_x, radius_y, depth in PALM_PADS:
        point = hand.frame([center])[0]
        total += relief.bump(scene.size, point, radius_x * scale, radius_y * scale, depth * scale)
    for name, joints in hand.joints.items():
        if name == "thumb" or name in hand.folded:
            continue
        root = joints[1] + (joints[0] - joints[1]) * 1.2
        total += relief.bump(scene.size, root, 0.045 * scale, 0.04 * scale, 0.012 * scale)
        tip = joints[-1] + (joints[-2] - joints[-1]) * 0.30
        total += relief.bump(scene.size, tip, 0.035 * scale, 0.05 * scale, 0.010 * scale)
    return total


def paint_palm(scene, hand, visible):
    """Palm colour and its lines: pinker than the back of the hand, with the three main creases."""
    scale = hand.scale
    tones = scene.style["palette"]["skin"]
    palm_area = hand.palm.mask * visible
    over(scene.image, rgb(tones["blush"]), scene.soften(palm_area, 0.0) * 0.6, 0.18 * scene.shade_on)
    lines = []
    for index, points in enumerate(PALM_LINES):
        path = smooth(hand.frame(points))
        width = scale * (0.006 if index < 3 else 0.004)
        lines.append((path, width * taper(len(path), 0.1, 0.1)))
    over(scene.image, rgb(tones["deep"]), stroke_many(scene.size, lines) * visible, 0.55)


def paint_veins(scene, hand, visible, count):
    """A few soft raised veins on the back of a man's hand: light on the lamp side, a hair of shadow on the other."""
    if count <= 0 or not scene.shade_on:
        return
    toward = -np.sign(scene.fig.light[0])
    tones = scene.style["palette"]["skin"]
    for points in VEINS[:count]:
        path = smooth(hand.frame(points))
        width = hand.scale * 0.010 * taper(len(path), 0.3, 0.0, 0.4)
        ridge = scene.soften(stroke_many(scene.size, [(path, width)]), 0.004) * hand.palm.mask * visible
        over(scene.image, rgb(tones["shadow"]), shift(ridge, toward * hand.scale * 0.006, 0) * (1 - ridge), 0.30)
        screen(scene.image, rgb(tones["light"]), ridge, 0.22)


def paint_hand(scene, placement):
    """One hand: paper shadow, skin with form shading, knuckles, creases, nails, ink."""
    width, height = scene.size[1], scene.size[0]
    wrist = (placement["x"] * width, placement["y"] * height)
    scale = placement["size"] * height
    build = BUILD[placement.get("sex", scene.fig.spec.get("sex", "female"))]
    hand = build_hand(scene.size, wrist, scale, placement.get("angle", 0.0), placement["pose"], placement.get("mirror", False),
                      view=placement.get("view", "back"), width=placement.get("width", build["width"]))
    fade = np.clip((FADE_END - hand.palm.along) / (FADE_END - FADE_START), 0.0, 1.0)
    in_fingers = np.maximum.reduce([part.mask for part in hand.fingers.values()])
    visible = np.maximum.reduce([hand.palm.mask * fade, in_fingers, hand.knuckles.mask])
    if scene.shade_on:
        toward = -np.sign(scene.fig.light[0])
        thrown = blur(shift(hand.whole.mask * visible, toward * scale * 0.035, scale * 0.03), scale * 0.02)
        multiply(scene.image, rgb(scene.style["palette"]["paper"]["cast"]), thrown, 0.45)
    surface = hand.whole.height.copy()
    if hand.view == "back":
        for name, joints in hand.joints.items():
            if name != "thumb":
                surface += relief.bump(scene.size, joints[1], scale * KNUCKLE_RADIUS, scale * KNUCKLE_RADIUS,
                                       scale * KNUCKLE_DEPTH * build["knuckle"])
    else:
        surface += palm_pads(scene, hand) * (hand.whole.mask > 0)
    body = relief.Part(hand.whole.mask, surface)
    kit.shade_solid(scene, body, "skin", level=0.34, spread=0.55, clip=visible)
    if scene.shade_on:
        flush = np.maximum.reduce([fill(scene.size, ellipse(joints[1], scale * 0.045, scale * 0.04)) for name, joints in hand.joints.items()
                                   if name != "thumb"] + [fill(scene.size, ellipse(joints[-1], scale * 0.04, scale * 0.04)) for joints in hand.joints.values()])
        over(scene.image, rgb(scene.style["palette"]["skin"]["blush"]), blur(flush, scale * 0.02) * visible, 0.30)
    if scene.shade_on:
        thumb = hand.fingers["thumb"].mask
        under = blur(shift(thumb, -np.sign(scene.fig.light[0]) * scale * 0.012, scale * 0.012), scale * 0.012)
        over(scene.image, rgb(scene.style["palette"]["skin"]["shadow"]), scene.soften(under * (1 - thumb), 0.0) * visible, 0.75)
    paint_creases(scene, hand, visible)
    if hand.view == "back":
        paint_veins(scene, hand, visible, build["veins"])
        paint_nails(scene, hand, visible, build)
    else:
        paint_palm(scene, hand, visible)
    for name, part in hand.fingers.items():
        kit.ink_tube(scene, part, 2.4, start=0.22 if name != "thumb" else 0.30, clip=visible)
    back = relief.Part(np.maximum(hand.palm.mask, hand.knuckles.mask), None, np.maximum(hand.palm.along, 0.05 * hand.knuckles.mask))
    kit.ink_tube(scene, back, 2.6, start=0.0, end=FADE_START + 0.08, clip=(1.0 - in_fingers) * visible)
    scene.fig.focus = np.maximum(scene.fig.focus, np.where(visible > 0.5, FOCUS_HAND, 0.0).astype(np.float32))
    kit.register(scene, f"hand_{placement['pose']}_{int(wrist[0])}", hand.whole.mask)


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    paint_paper(scene)
    run_hook(extras, "after_background", scene)
    for placement in fig.spec["hands"]:
        paint_hand(scene, placement)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
