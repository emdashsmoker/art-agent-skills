"""Cigarettes and their smoke, for figures, portraits and still lifes.

  in the mouth   `accessories.cigarette` true or {"side": "right" | "left", "lit": true, "smoke": 1.0} on a front
                 figure or portrait: from the corner of the mouth, angled down and out toward the viewer
  in the hand    `figure.holds` {"<side>": {"kind": "cigarette"}} with the hand "relaxed": across the index and
                 middle fingers, the lit end pointing away from the body (`point` -1 turns it round)
  on an ashtray  still life objects "ashtray" (with a resting cigarette) and the smoke rising from it

Smoke rises as a few thin strands from the ember: each wavers more and widens as it climbs, and fades.
"""
import numpy as np

from raster import blur, ellipse, fill, over, rgb, screen, stroke

# Cigarette (head units): length, half thickness, filter share of the length, ash share.
CIGARETTE = {"length": 1.15, "width": 0.085, "filter": 0.27, "ash": 0.07}
COLORS = {"paper": "#F2EFE8", "paper_shadow": "#B9B4AA", "filter": "#D89A5C", "filter_dots": "#A8693A", "ash": "#8A8A88",
          "ember": "#FF5A1E", "ember_core": "#FFD27A", "smoke": "#D8DCE2", "line": "#3A3632"}
# Smoke: strands, how high they rise (head units), how much they waver.
SMOKE = {"strands": 4, "rise": 4.5, "waver": 0.55, "width": 0.06, "opacity": 0.75}


def colors(scene):
    """The style's cigarette palette when it has one, else the defaults."""
    return {**COLORS, **scene.style["palette"].get("cigarette", {})}


def paint_cigarette(scene, mouth_end, lit_end, unit, lit=True):
    """A cigarette from its filter end to its lit end (pixels). Returns (mask, ember point)."""
    tones = colors(scene)
    mouth_end, lit_end = np.asarray(mouth_end, np.float64), np.asarray(lit_end, np.float64)
    along = lit_end - mouth_end
    width = CIGARETTE["width"] * unit * 2.0
    filter_end = mouth_end + along * CIGARETTE["filter"]
    ash_start = lit_end - along * CIGARETTE["ash"]
    body = stroke(scene.size, np.array([mouth_end, lit_end]), width)
    over(scene.image, rgb(tones["paper"]), body)
    if scene.shade_on:
        normal = np.array([-along[1], along[0]]) / max(np.linalg.norm(along), 1e-6)
        under = stroke(scene.size, np.array([mouth_end, lit_end]) + normal * width * 0.25, width * 0.5)
        over(scene.image, rgb(tones["paper_shadow"]), under * body, 0.6)
    tip = stroke(scene.size, np.array([mouth_end, filter_end]), width * 1.02)
    over(scene.image, rgb(tones["filter"]), tip)
    if lit:
        ash = stroke(scene.size, np.array([ash_start, lit_end]), width * 0.98)
        over(scene.image, rgb(tones["ash"]), ash)
        ember = fill(scene.size, ellipse(lit_end, width * 0.55, width * 0.55, 12))
        over(scene.image, rgb(tones["ember"]), ember)
        over(scene.image, rgb(tones["ember_core"]), fill(scene.size, ellipse(lit_end, width * 0.25, width * 0.25, 10)))
        if scene.shade_on:
            screen(scene.image, rgb(tones["ember"]), blur(ember, width * 1.2), 0.8)
    return np.maximum(body, tip), lit_end


def paint_smoke(scene, origin, unit, seed, amount=1.0, drift=0.25, clip=None):
    """Thin strands of smoke rising from `origin` (pixels): wavering, widening, fading as they climb."""
    if amount <= 0:
        return
    tones = colors(scene)
    rng = np.random.default_rng(seed)
    rise = SMOKE["rise"] * unit * amount
    strands = []
    for k in range(SMOKE["strands"]):
        t = np.linspace(0.0, 1.0, 60)
        phase, freq = rng.uniform(0, 2 * np.pi), rng.uniform(2.0, 3.4)
        waver = SMOKE["waver"] * unit * (0.25 + t ** 1.2) * np.sin(2 * np.pi * freq * t ** 0.8 + phase)
        lean = drift * unit * 3.0 * t ** 1.5 + rng.uniform(-0.1, 0.1) * unit * t
        path = np.column_stack([origin[0] + waver + lean, origin[1] - rise * t * rng.uniform(0.75, 1.05)])
        widths = SMOKE["width"] * unit * (0.7 + 2.0 * t) * rng.uniform(0.7, 1.2)
        strands.append((path, widths, k))
    layer = np.zeros(scene.size, np.float32)
    for path, widths, k in strands:
        line = stroke(scene.size, path, widths)
        fade = np.clip(1.0 - (origin[1] - np.arange(scene.size[0], dtype=np.float32)[:, None]) / max(rise, 1.0), 0.0, 1.0) ** 1.3
        layer = np.maximum(layer, line * fade * (1.0 if k == 0 else 0.7))
    layer = blur(layer, max(unit * 0.03, 0.8))
    if clip is not None:
        layer = layer * clip
    screen(scene.image, rgb(tones["smoke"]), layer, SMOKE["opacity"])


def paint_mouth_cigarette(scene):
    """A cigarette at the corner of the mouth of a front head (portrait or figure), and its smoke."""
    setup = (scene.fig.spec.get("accessories") or {}).get("cigarette")
    if not setup:
        return
    setup = setup if isinstance(setup, dict) else {}
    spec, head = scene.fig.spec, scene.fig.head_frame
    side = -1.0 if setup.get("side") == "left" else 1.0
    mouth = spec["mouth"]
    start = (side * mouth["half_width"] * 0.55, mouth["y"] + mouth["lip_height"] * 0.4, 1.0)
    direction = np.array([side * 0.62, 0.32, 0.72])
    direction = direction / np.linalg.norm(direction)
    end = np.array(start) + direction * CIGARETTE["length"] * 0.85
    points = head.project([start, tuple(end)])
    unit = head.unit_px
    lit = setup.get("lit", True)
    _, ember = paint_cigarette(scene, points[0], points[1], unit, lit)
    if lit:
        paint_smoke(scene, ember, unit, scene.fig.seed + 61, setup.get("smoke", 1.0), drift=side * 0.2)


def held_cigarette(scene, hand, unit, item):
    """A cigarette across the index and middle fingers of `hand`; the lit end points away (`point` +1 or -1)."""
    index, middle = hand.joints.get("index"), hand.joints.get("middle")
    if index is None or middle is None:
        return np.zeros(scene.size, np.float32)
    grip = (np.asarray(index[2]) + np.asarray(middle[2])) / 2.0
    finger = np.asarray(middle[-1], np.float64) - np.asarray(middle[1], np.float64)
    finger = finger / max(np.linalg.norm(finger), 1e-6)
    across = np.array([-finger[1], finger[0]])
    if across[0] < 0:
        across = -across
    across = across * item.get("point", 1)
    length = CIGARETTE["length"] * unit * item.get("size", 1.0)
    mouth_end, lit_end = grip - across * length * 0.35, grip + across * length * 0.65
    mask, ember = paint_cigarette(scene, mouth_end, lit_end, unit * item.get("size", 1.0), item.get("lit", True))
    if item.get("lit", True):
        paint_smoke(scene, ember, unit, scene.fig.seed + 63, item.get("smoke", 1.0), drift=float(across[0]) * 0.2)
    return mask
