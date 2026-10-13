"""Painter: fills, shades and inks a Figure layer by layer (stages 2-4).

One procedure serves every style. A style only changes three things:
  palette     colours per material (skin, hair, eye, cloth, line)
  shading     "cel"   = hard two-tone edges
              "soft"  = continuous gradients
              "grain" = gradients broken into speckle, as in textured print
  line_scale  ink width multiplier (0 switches line art off)

Layers are painted back to front, so occlusion needs no extra logic.
"""
import cv2
import numpy as np

import accessories
import smoking
from figure import face_light, on_face
from patterns import apply_pattern
from raster import (blur, ellipse, fill, fill_many, join, lambert, mix, multiply, noise, over, rgb,
                    screen, shift, smooth, smoothstep, stroke, stroke_many, taper)

# Half-width of the cel shadow edge in shadow-amount units; keeps the edge antialiased.
CEL_EDGE = 0.04
# Width of the transition between lit and shadowed, as a share of frontal light.
FORM_SHADOW_RANGE = 0.30
# Cast shadows fall mostly downward: sideways travel is damped so they stay near the caster.
CAST_SIDEWAYS = 0.45
# Hair highlight ring sinks by this many head units from the parting to the silhouette.
RING_DROP = 0.30
# Blur radius (px) of the noise used for grain shading: the size of one speckle.
GRAIN_SIZE = 0.7
# Head-unit size (px) from which ink lines are drawn at full width.
FULL_INK_UNIT = 200.0
EYES = ("eye_far", "eye_near")
SKETCH_PAPER, SKETCH_PENCIL, SKETCH_GUIDE = "#F3EEE4", "#4B4A52", "#8FB3D1"
# Geometry that would only clutter the construction drawing.
SKETCH_HIDDEN = {"hair_back", "nose_side", "nose_under", "cloth_ribs", "cloth_band", "skin_body", "tendon"}


class Scene:
    """Mutable painting state shared by all layer functions."""

    def __init__(self, fig, style, seed, shade=True, lines=True):
        self.fig, self.style = fig, style
        self.size = fig.size
        self.image = np.ones(fig.size + (3,), np.float32)
        self.rng = np.random.default_rng(seed)
        self.shade_on = shade
        self.lines_on = lines and style["line_scale"] > 0
        # Why: a small figure inked at portrait line width looks like a woodcut.
        self.ink_scale = min(1.0, (fig.unit / FULL_INK_UNIT) ** 0.5)
        self.mode = style["shading"]
        self.cel = self.mode == "cel"
        # Why a fixed grain field: every shadow must break up on the same speckle, like one sheet of paper.
        self.grain = blur(self.rng.random(fig.size, dtype=np.float32), GRAIN_SIZE)
        self.grain = (self.grain - self.grain.min()) / np.ptp(self.grain)
        self._masks = {}

    def mask(self, name):
        if name not in self._masks:
            self._masks[name] = fill(self.size, self.fig.shapes[name])
        return self._masks[name]

    def union(self, *names):
        return np.maximum.reduce([self.mask(name) for name in names])

    def tone(self, group, name):
        return rgb(self.style["palette"][group][name])

    def px(self, head_units):
        return head_units * self.fig.unit

    def edge(self, amount, window=None):
        """Turn a shadow amount field into the style's edge quality.

        `window` = (row slice, column slice) when `amount` is a crop of the canvas.
        """
        if not self.shade_on:
            return np.zeros_like(amount)
        if self.cel:
            return smoothstep(amount, 0.5 - CEL_EDGE, 0.5 + CEL_EDGE)
        soft = np.clip(blur(amount, self.px(self.style["soft_blur"])), 0.0, 1.0)
        return soft if self.mode == "soft" else self.speckle(soft, window)

    def soften(self, mask, blur_units):
        """Hard shape in cel mode, feathered in soft mode, speckled in grain mode."""
        if self.cel:
            return mask
        soft = blur(mask, self.px(blur_units))
        return soft if self.mode == "soft" else self.speckle(soft)

    def speckle(self, amount, window=None):
        """Dither a gradient against the grain field."""
        spread = self.style["grain_spread"]
        grain = self.grain if window is None else self.grain[window]
        return smoothstep(amount + (grain - 0.5) * spread, 0.5 - CEL_EDGE, 0.5 + CEL_EDGE)

    def ink(self, path, width, group="line", name="main", profile=None, opacity=1.0, clip=None):
        """Draw one tapered ink line."""
        if not self.lines_on:
            return
        shape = taper(len(path), 0.15, 0.15) if profile is None else profile
        line = stroke(self.size, path, width * self.style["line_scale"] * self.ink_scale * shape)
        over(self.image, self.tone(group, name), line if clip is None else line * clip, opacity)


def form_shadow(scene, mask, sigma_units, level, spread=FORM_SHADOW_RANGE):
    """Shadow amount 0..1 on the side of a shape turned away from the lamp.

    `sigma_units` = how far the rounding reaches inward; `level` = share of
    frontal light below which the surface is in shadow (higher = more shadow);
    `spread` = width of the lit-to-shadow transition in the same unit.
    """
    light = lambert(mask, scene.fig.light, scene.px(sigma_units)) / scene.fig.light[2]
    return np.clip((level - light) / spread + 0.5, 0.0, 1.0)


def cast_shadow(scene, caster_mask, distance_units):
    """Shadow a shape throws: the caster slid away from the lamp."""
    lx, ly, _ = scene.fig.light
    reach = scene.px(distance_units) / max(abs(ly), 1e-6)
    return shift(caster_mask, -lx * reach * CAST_SIDEWAYS, -ly * reach)


def lay_tones(scene, mask, group, shadow, deep=None):
    """Fill a region with its base colour, then shadow (and deep shadow) tones."""
    color = np.empty(scene.size + (3,), np.float32)
    color[:] = scene.tone(group, "base")
    color = mix(color, scene.tone(group, "shadow"), scene.edge(shadow)[..., None])
    if deep is not None:
        color = mix(color, scene.tone(group, "deep"), scene.edge(deep)[..., None])
    over(scene.image, color, mask)


# -------------------------------------------------------------- background
def paint_background(scene):
    """Backdrop: vertical gradient, optional tonal mottle, one large disc, optional bokeh."""
    backdrop = scene.fig.extra.get("backdrop")
    if backdrop is not None:
        # A scene: another subject already painted is the background.
        scene.image[:] = backdrop
        return
    back = scene.style["palette"]["background"]
    height, width = scene.size
    ramp = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    scene.image[:] = mix(rgb(back["top"]), rgb(back["bottom"]), ramp)
    if back["mottle"] > 0:
        cloud = noise(scene.size, scene.px(1.6), int(scene.rng.integers(1 << 30)), 3)
        scene.image *= (1.0 + back["mottle"] * (cloud - 0.5))[..., None]
    disc_center = (width * back["disc_x"], height * back["disc_y"])
    disc = fill(scene.size, ellipse(disc_center, width * back["disc_r"], width * back["disc_r"], 96))
    over(scene.image, rgb(back["disc"]), blur(disc, scene.px(back["disc_blur"])), back["disc_opacity"])
    for _ in range(back["bokeh"]):
        center = (scene.rng.uniform(0, width), scene.rng.uniform(0, height * 0.8))
        radius = scene.px(scene.rng.uniform(0.12, 0.45))
        spot = blur(fill(scene.size, ellipse(center, radius, radius, 40)), scene.px(0.02))
        screen(scene.image, rgb(back["bokeh_color"]), spot, scene.rng.uniform(0.10, 0.32))


# --------------------------------------------------------------------- hair
def flow_curve(guides, across):
    """The strand at fraction `across` (0 = inner guide, 1 = outer guide)."""
    inner, outer = guides
    return inner * (1.0 - across) + outer * across


def flow_wedge(guides, across, width, start, end):
    """Pointed strip following the flow: the unit shape of hair shading."""
    inner, outer = guides
    count = len(inner)
    index = np.arange(int(start * (count - 1)), int(end * (count - 1)) + 1)
    half = 0.5 * width * taper(len(index), 0.0, 0.0, 0.45, 0.8)
    left = np.clip(across - half, 0.0, 1.0)[:, None]
    right = np.clip(across + half, 0.0, 1.0)[:, None]
    left_edge = inner[index] * (1 - left) + outer[index] * left
    right_edge = inner[index] * (1 - right) + outer[index] * right
    return join(left_edge, right_edge[::-1])


def flow_wedges(scene, guides, count, width_range, start_range, length_range):
    """Union mask of random wedges scattered over a hair section."""
    rng = scene.rng
    wedges = []
    for _ in range(count):
        start = rng.uniform(*start_range)
        end = min(start + rng.uniform(*length_range), 1.0)
        wedges.append(flow_wedge(guides, rng.uniform(0.04, 0.96), rng.uniform(*width_range), start, end))
    return fill_many(scene.size, wedges)


def highlight_ring(scene, guides, thickness, teeth):
    """Jagged band across the flow at one height of the skull: the classic hair shine.

    How: for each strand find where it crosses the ring height, then push
    alternate points up and down along the strand to make teeth.
    """
    ring_y = scene.fig.points["hair_band"][1]
    upper, lower = [], []
    for i, across in enumerate(np.linspace(0.03, 0.97, teeth * 2 + 1)):
        curve = flow_curve(guides, across)
        target = ring_y + scene.px(RING_DROP) * across ** 2
        below = np.nonzero(curve[:, 1] >= target)[0]
        if len(below) == 0 or below[0] == 0:
            continue
        index = below[0]
        tangent = curve[min(index + 2, len(curve) - 1)] - curve[max(index - 2, 0)]
        tangent /= max(np.linalg.norm(tangent), 1e-6)
        reach = scene.px(thickness) * scene.rng.uniform(0.45, 1.0)
        upper.append(curve[index] - tangent * (reach if i % 2 else 0.2 * reach))
        lower.append(curve[index] + tangent * (0.2 * reach if i % 2 else reach))
    if len(upper) < 3:
        return np.zeros(scene.size, np.float32)
    return fill(scene.size, join(np.array(upper), np.array(lower)[::-1]))


def hair_form_shadow(scene):
    """One rounding for the whole hair mass, so sections do not shade as separate lumps."""
    hair = scene.style["hair_render"]
    whole = scene.union("hair_back", "hair_near", "hair_far")
    return form_shadow(scene, whole, 0.34, hair["form_level"], hair["form_spread"])


def paint_hair_section(scene, name, form, in_back=False, behind_body=False):
    """One hair section: base, flow shadows, highlight ring, outlines, strands.

    `behind_body` hides the part that falls behind the shoulder, for a section
    that must still be painted after the face it overlaps.
    """
    guides = scene.fig.hair[name]
    mask = scene.mask(f"hair_{name}")
    if behind_body:
        mask = mask * (1.0 - scene.union("skin_body", "cloth"))
    hair = scene.style["hair_render"]
    shadow = form
    if in_back:
        shadow = np.maximum(shadow, 0.9)
    elif scene.shade_on:
        dark = flow_wedges(scene, guides, hair["shadow_wedges"], (0.03, 0.10), (0.12, 0.70), (0.20, 0.50))
        broad = flow_wedges(scene, guides, hair["broad_wedges"], (0.14, 0.26), (0.25, 0.50), (0.30, 0.50))
        shadow = np.maximum.reduce([shadow, dark, broad])
    lay_tones(scene, mask, "hair", shadow)
    if scene.shade_on and not in_back:
        ring = highlight_ring(scene, guides, hair["ring_thickness"], hair["ring_teeth"])
        lit = flow_wedges(scene, guides, hair["light_wedges"], (0.008, 0.025), (0.10, 0.65), (0.10, 0.28))
        glow = scene.soften(np.maximum(ring, lit * 0.55) * mask, 0.012)
        over(scene.image, scene.tone("hair", "light"), glow, hair["light_opacity"])
    if scene.shade_on and hair["texture_strands"] > 0:
        paint_strand_texture(scene, guides, mask, hair["texture_strands"], in_back)
    if scene.lines_on:
        strands = []
        for _ in range(hair["strand_lines"]):
            curve = flow_curve(guides, scene.rng.uniform(0.06, 0.94))
            start = int(scene.rng.uniform(0.05, 0.70) * len(curve))
            stop = min(start + int(scene.rng.uniform(0.15, 0.40) * len(curve)), len(curve))
            if stop - start > 3:
                strands.append((curve[start:stop], 1.1 * scene.style["line_scale"] * taper(stop - start)))
        over(scene.image, scene.tone("hair", "line"), stroke_many(scene.size, strands) * mask, 0.5)
        outline = scene.fig.shapes[f"hair_{name}"]
        visible = blur(mask, 1.5) > 0.02 if behind_body else None
        scene.ink(np.vstack([outline, outline[:1]]), 2.4, "hair", "line", np.ones(len(outline) + 1), clip=visible)
    if not in_back and hair["flyaways"] > 0:
        paint_flyaways(scene, guides, hair["flyaways"])


def paint_flyaways(scene, guides, count):
    """A few single hairs that leave the silhouette; without them hair reads as a helmet."""
    rng = scene.rng
    strands = []
    for _ in range(count):
        curve = flow_curve(guides, rng.uniform(1.01, 1.05))
        start = int(rng.uniform(0.05, 0.40) * len(curve))
        stop = min(start + int(rng.uniform(0.10, 0.25) * len(curve)), len(curve))
        if stop - start > 3:
            strands.append((curve[start:stop], 1.5 * taper(stop - start)))
    over(scene.image, scene.tone("hair", "base"), stroke_many(scene.size, strands), 0.9)


def paint_strand_texture(scene, guides, mask, count, in_back):
    """Gradient styles: many faint light and dark strands that read as hair texture."""
    rng = scene.rng
    batches = {"light": [], "shadow": []}
    for i in range(count):
        curve = flow_curve(guides, rng.uniform(0.02, 0.98))
        start = int(rng.uniform(0.0, 0.75) * len(curve))
        stop = min(start + int(rng.uniform(0.12, 0.45) * len(curve)), len(curve))
        if stop - start > 3:
            widths = rng.uniform(1.0, 2.6) * taper(stop - start)
            batches["light" if i % 2 else "shadow"].append((curve[start:stop], widths))
    light_opacity = 0.10 if in_back else 0.30
    over(scene.image, scene.tone("hair", "light"), stroke_many(scene.size, batches["light"]) * mask, light_opacity)
    over(scene.image, scene.tone("hair", "deep"), stroke_many(scene.size, batches["shadow"]) * mask, 0.45)


def wisp_strokes(scene):
    """(path, widths) of each loose lock: wide near the root, pointed at the tip."""
    return [(lock["path"], lock["width"] * taper(len(lock["path"]), 0.45, 0.0, 0.30)) for lock in scene.fig.locks]


def paint_hair_wisps(scene):
    """Loose locks over the forehead and cheek."""
    for path, widths in wisp_strokes(scene):
        if scene.lines_on:
            over(scene.image, scene.tone("hair", "line"), stroke(scene.size, path, widths + 3.0 * scene.style["line_scale"]))
        over(scene.image, scene.tone("hair", "base"), stroke(scene.size, path, widths))
        if scene.shade_on:
            core = stroke(scene.size, path - [widths.max() * 0.18, 0], widths * 0.22)
            over(scene.image, scene.tone("hair", "light"), scene.soften(core, 0.008), 0.40)


# --------------------------------------------------------------------- body
def paint_body(scene):
    """Neck and shoulders with the shadow the head throws on the neck."""
    fig, mask = scene.fig, scene.mask("skin_body")
    render = scene.style["body_render"]
    face = scene.mask("face")
    thrown = cast_shadow(scene, face, render["chin_shadow_reach"]) * (1.0 - face)
    hair_thrown = cast_shadow(scene, scene.mask("hair_near"), 0.08)
    shadow = np.maximum.reduce([form_shadow(scene, mask, 0.16, render["form_level"]), thrown, hair_thrown])
    lay_tones(scene, mask, "skin", shadow, deep=cast_shadow(scene, face, render["chin_shadow_reach"] * 0.35) * thrown)
    if scene.shade_on:
        pit = blur(scene.mask("neck_pit"), scene.px(0.03))
        multiply(scene.image, scene.tone("skin", "shadow"), pit * mask, 0.5)
        for key in ("collar_r", "collar_l"):
            path = fig.paths[key]
            under = stroke(scene.size, path + [0, scene.px(0.030)], scene.px(0.045) * taper(len(path), 0.0, 0.0, 0.4))
            multiply(scene.image, scene.tone("skin", "shadow"), blur(under, scene.px(0.02)) * mask, render["collar_opacity"])
    for key in ("neck_r", "neck_l"):
        scene.ink(fig.paths[key], 2.6)
    for key in ("collar_r", "collar_l"):
        scene.ink(fig.paths[key], 1.5, profile=taper(len(fig.paths[key]), 0.0, 0.0, 0.35), opacity=0.6, clip=mask)
    if fig.spec and fig.spec["body"].get("adams_apple") and scene.shade_on:
        paint_neck_details(scene, mask)


def paint_neck_details(scene, mask):
    """A man's neck: the Adam's apple and the two neck muscles running down to the collarbones."""
    fig, unit = scene.fig, scene.px(1.0)
    body = fig.spec["body"]
    chin, pit = fig.spec["face"]["chin_y"], body["neck_pit_y"]
    neck_frame = lambda points: _body_frame(fig).project(points)
    apple = neck_frame([(0.02, chin + (pit - chin) * 0.38)])[0]
    bump = fill(scene.size, ellipse(apple, 0.09 * unit, 0.13 * unit))
    under = blur(shift(bump, 0.0, scene.px(0.07)) * (1 - bump), 0.03 * unit)
    over(scene.image, scene.tone("skin", "shadow"), under * mask, 0.30)
    screen(scene.image, scene.tone("skin", "light"), blur(bump, 0.04 * unit) * mask, 0.18)
    for sign in (-1, 1):
        muscle = neck_frame(smooth([(sign * body["neck_half_width"] * 0.75, chin + 0.05), (sign * 0.30, (chin + pit) / 2),
                                    (sign * 0.10, pit - 0.02)]))
        line = stroke(scene.size, muscle, 0.06 * unit * taper(len(muscle), 0.0, 0.6, 0.5))
        over(scene.image, scene.tone("skin", "shadow"), blur(line, 0.04 * unit) * mask, 0.18)


def _body_frame(fig):
    """The frame the neck and shoulders were built in (roll only)."""
    from figure import Frame
    spec = fig.spec
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    pose = spec["pose"]
    origin = (pose["head_center"][0] * width, pose["head_center"][1] * height)
    return Frame(origin, pose["head_unit"] * width, 0.0, pose["shoulder_roll_deg"])


def paint_ears(scene):
    """Ears (short hair only): skin shapes behind the cheeks, with a shadowed inner fold."""
    fig = scene.fig
    for name in ("ear_far", "ear_near"):
        if name not in fig.shapes:
            continue
        mask = scene.mask(name)
        shadow = form_shadow(scene, mask, 0.06, 0.45)
        lay_tones(scene, mask, "skin", shadow)
        fold = fig.paths[f"{name}_fold"]
        over(scene.image, scene.tone("skin", "deep"), stroke(scene.size, fold, scene.px(0.030) * taper(len(fold), 0.3, 0.3)) * mask, 0.6)
        over(scene.image, scene.tone("skin", "blush"), blur(mask, scene.px(0.03)) * mask, 0.25 * scene.shade_on)
        scene.ink(np.vstack([fig.shapes[name], fig.shapes[name][:1]]), 2.0, profile=np.ones(len(fig.shapes[name]) + 1))


def paint_outfit(scene):
    """Knit top: base, fold shadows, ribbed neckline band, chain."""
    fig, mask = scene.fig, scene.mask("cloth")
    unit = scene.px(1.0)
    render = scene.style["body_render"]
    hair_thrown = cast_shadow(scene, scene.mask("hair_near"), 0.10)
    folds = np.zeros(scene.size, np.float32)
    for path in fig.paths["cloth_folds"]:
        inside = path + [np.sign(fig.points["pendant"][0] - path[0, 0]) * 0.035 * unit, 0]
        folds = np.maximum(folds, stroke(scene.size, inside, 0.075 * unit * taper(len(path), 0.0, 0.5, 0.35)))
    shadow = np.maximum.reduce([form_shadow(scene, mask, 0.14, render["cloth_form_level"]), hair_thrown, folds])
    lay_tones(scene, mask, "cloth", shadow)
    band = scene.mask("cloth_band")
    apply_pattern(scene, mask * (1.0 - band), "cloth")
    if scene.shade_on:
        multiply(scene.image, scene.tone("cloth", "shadow"), band, 0.30)
        neckline, inner = fig.paths["cloth_neckline"], fig.paths["cloth_band_inner"]
        ribs = [(np.vstack([neckline[i], inner[i]]), 1.3) for i in range(1, len(neckline) - 1, 2)]
        multiply(scene.image, scene.tone("cloth", "shadow"), stroke_many(scene.size, ribs), 0.6)
        knit = [(path, 1.2 * taper(len(path), 0.3, 0.6)) for path in fig.paths["cloth_ribs"]]
        multiply(scene.image, scene.tone("cloth", "shadow"), stroke_many(scene.size, knit) * mask * (1 - band),
                 render["knit_opacity"])
    scene.ink(fig.paths["cloth_neckline"], 2.4, "cloth", "line")
    scene.ink(fig.paths["cloth_band_inner"], 1.3, "cloth", "line", opacity=0.6)
    for key in ("cloth_outline_r", "cloth_outline_l"):
        scene.ink(fig.paths[key], 2.8, "cloth", "line", taper(len(fig.paths[key]), 0.4, 0.6))
    for path in fig.paths["cloth_folds"]:
        scene.ink(path, 1.6, "cloth", "line", taper(len(path), 0.0, 0.5, 0.3), 0.75)
    if fig.spec is None or fig.spec["outfit"].get("necklace", True):
        chain = stroke(scene.size, fig.paths["cloth_chain"], 1.7) * scene.mask("skin_body")
        over(scene.image, scene.tone("accent", "metal"), chain)
        pendant = fill(scene.size, ellipse(fig.points["pendant"], 0.030 * unit, 0.030 * unit, 24))
        over(scene.image, scene.tone("accent", "metal"), pendant)
        over(scene.image, scene.tone("accent", "shine"), shift(pendant, -0.010 * unit, -0.010 * unit) * pendant, 0.9)


# --------------------------------------------------------------------- face
def paint_face(scene):
    """Face skin: form shadow, hair cast shadow, blush, jaw line."""
    fig, mask = scene.fig, scene.mask("face")
    unit = scene.px(1.0)
    render = scene.style["face_render"]
    casters = np.maximum(scene.union("hair_near", "hair_far"), stroke_many(scene.size, wisp_strokes(scene)))
    thrown = cast_shadow(scene, casters, render["hair_shadow_reach"])
    # Why a sideways slice: the far cheek is the only plane of a young face that
    # turns from the lamp; rounding the whole outline would also darken the chin.
    toward_lamp = np.sign(fig.light[0])
    far_cheek = mask * (1.0 - shift(mask, toward_lamp * scene.px(render["cheek_shadow_width"]), 0))
    if scene.cel:
        shadow = np.maximum(far_cheek, thrown)
    else:
        lit = face_light(fig.head_frame, scene.size, fig.light)
        form = np.clip((render["form_level"] - lit) / render["form_range"] + 0.5, 0.0, 1.0)
        shadow = np.maximum(form, thrown)
    lay_tones(scene, mask, "skin", shadow)
    if scene.shade_on and not scene.cel:
        glow = np.clip((lit - render["light_level"]) / max(1.0 - render["light_level"], 1e-6), 0.0, 1.0)
        screen(scene.image, scene.tone("skin", "light"), glow * mask, render["light_opacity"])
    if scene.shade_on:
        for eye in EYES:
            cx, cy = fig.points[f"{eye}_center"]
            cheek = fill(scene.size, ellipse((cx, cy + 0.38 * unit), 0.24 * unit, 0.11 * unit))
            over(scene.image, scene.tone("skin", "blush"), blur(cheek, 0.08 * unit) * mask, render["blush_opacity"])
    if scene.shade_on and scene.mode == "soft":
        model_face_planes(scene)
    if scene.shade_on and render.get("stubble", 0.0) > 0:
        paint_stubble(scene, mask, render["stubble"])
    paint_face_marks(scene, mask)
    jaw = fig.paths["jaw"]
    scene.ink(jaw, 2.8, profile=taper(len(jaw), 0.35, 0.35, 0.55))


# Freckles scatter over the nose bridge and the upper cheeks (head units: x, y ranges).
FRECKLE_AREA = ((-0.75, 0.75), (0.12, 0.52))
FRECKLE_COUNT = 70          # at full strength
MOLE_RADIUS = 0.022         # head units


def paint_face_marks(scene, face):
    """Freckles and moles from spec["look"]: small darker dots laid on the face surface."""
    look = scene.fig.spec.get("look") or {}
    head, unit = scene.fig.head_frame, scene.px(1.0)
    dots = []
    amount = look.get("freckles", 0.0)
    if amount > 0:
        rng = np.random.default_rng(scene.fig.seed + 91)
        count = int(FRECKLE_COUNT * amount)
        xs = rng.uniform(*FRECKLE_AREA[0], count)
        ys = rng.uniform(*FRECKLE_AREA[1], count)
        # Denser over the nose and the cheekbones than at the edges.
        keep = rng.uniform(0, 1, count) < np.exp(-((np.abs(xs) - 0.35) / 0.35) ** 2) + 0.35
        for x, y in zip(xs[keep], ys[keep]):
            dots.append(((x, y), rng.uniform(0.010, 0.020), 0.45))
    for x, y in look.get("moles", []):
        dots.append(((x, y), MOLE_RADIUS, 0.85))
    for (x, y), radius, opacity in dots:
        center = head.project(on_face(np.array([[x, y]])))[0]
        spot = fill(scene.size, ellipse(center, radius * unit, radius * unit * 0.9, 12))
        over(scene.image, scene.tone("skin", "deep"), scene.soften(spot, 0.004) * face, opacity)


def paint_stubble(scene, face, strength):
    """A shaved man's beard shadow: a faint cool-dark tint over the jaw, chin and upper lip."""
    fig, unit = scene.fig, scene.px(1.0)
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    nose_y = fig.points["nose_tip"][1]
    mouth_y = fig.paths["mouth_line"][:, 1].mean()
    below = smoothstep(rows, nose_y + 0.04 * unit, mouth_y - 0.05 * unit) * np.ones((1, scene.size[1]), np.float32)
    lips = blur(np.maximum(scene.mask("upper_lip"), scene.mask("lower_lip")), 0.02 * unit)
    area = below * face * (1.0 - lips)
    # The beard follows the jaw, not the cheeks: keep it inside a band along the face's lower edge.
    inner = cv2.erode((face > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=int(0.30 * unit))
    band = np.clip(1.0 - blur(inner.astype(np.float32), 0.10 * unit) * 0.7, 0, 1)
    upper_lip = smoothstep(rows, nose_y + 0.04 * unit, nose_y + 0.10 * unit) * (1 - smoothstep(rows, mouth_y - 0.06 * unit, mouth_y))
    near_mouth = fill(scene.size, ellipse(fig.points["nose_tip"] + [0, (mouth_y - nose_y) * 0.6], 0.32 * unit, 0.22 * unit))
    area = area * np.maximum(band, blur(near_mouth, 0.05 * unit) * upper_lip + blur(near_mouth, 0.08 * unit) * (rows > mouth_y))
    grain = noise(scene.size, max(unit * 0.012, 1.5), int(scene.fig.seed) + 51, 1)
    over(scene.image, scene.tone("hair", "base"), blur(area, 0.03 * unit) * (0.75 + 0.5 * grain) * face, strength)


def model_face_planes(scene):
    """Gradient styles only: light and shadow patches that give the face its planes."""
    face = scene.mask("face")
    strength = scene.style["face_render"]["plane_strength"]
    for plane in scene.fig.planes:
        patch = blur(fill(scene.size, plane["outline"]), scene.px(plane["blur"])) * face
        if plane["kind"] == "light":
            screen(scene.image, scene.tone("skin", "light"), patch, plane["opacity"] * strength)
        else:
            over(scene.image, scene.tone("skin", "shadow"), patch, plane["opacity"] * strength)


def paint_nose(scene):
    """Nose: planes as tone in soft styles, a short mark in line styles."""
    fig, face = scene.fig, scene.mask("face")
    render = scene.style["face_render"]
    if scene.shade_on:
        over(scene.image, scene.tone("skin", "shadow"), scene.soften(scene.mask("nose_side"), 0.035) * face,
             render["nose_side_opacity"])
        over(scene.image, scene.tone("skin", "shadow"), scene.soften(scene.mask("nose_under"), 0.02) * face,
             render["nose_under_opacity"])
        over(scene.image, scene.tone("skin", "shadow"), scene.mask("nose_wedge") * face, render["nose_wedge_opacity"])
        tip_center = fig.points["nose_tip"] - [scene.px(0.03), scene.px(0.03)]
        tip = fill(scene.size, ellipse(tip_center, scene.px(0.035), scene.px(0.028)))
        screen(scene.image, scene.tone("skin", "light"), blur(tip, scene.px(0.012)), render["nose_light_opacity"])
    bridge = fig.paths["nose_bridge"]
    scene.ink(bridge, 1.8, profile=taper(len(bridge), 0.0, 0.2, 0.7))
    scene.ink(fig.paths["nose_nostril_far"], 1.4, opacity=0.7)


def paint_mouth(scene):
    """Lips as two tinted shapes, a shine on the lower lip, the parting line."""
    fig, face = scene.fig, scene.mask("face")
    render = scene.style["face_render"]
    upper, lower = scene.mask("upper_lip"), scene.mask("lower_lip")
    if "mouth_inner" in fig.shapes:
        paint_open_mouth(scene)
    over(scene.image, scene.tone("lip", "upper"), upper, render["lip_opacity"])
    over(scene.image, scene.tone("lip", "lower"), lower, render["lip_opacity"])
    if scene.shade_on:
        offset = shift(lower, -scene.px(0.03), -scene.px(0.02))
        shine = shift(lower, 0, -scene.px(0.012)) * lower * blur(offset, scene.px(0.02))
        screen(scene.image, scene.tone("lip", "shine"), shine, render["lip_shine_opacity"])
        below = cast_shadow(scene, lower, 0.03) * (1 - lower) * face
        over(scene.image, scene.tone("skin", "shadow"), scene.soften(below, 0.015), 0.6)
    line = fig.paths["mouth_line"]
    parting = stroke(scene.size, line, render["mouth_line"] * taper(len(line), 0.2, 0.2))
    over(scene.image, scene.tone("lip", "line"), parting, 0.9)
    if "mouth_lower_line" in fig.paths:
        lower_line = fig.paths["mouth_lower_line"]
        over(scene.image, scene.tone("lip", "line"), stroke(scene.size, lower_line, render["mouth_line"] * 0.6 * taper(len(lower_line), 0.2, 0.2)), 0.7)


def paint_open_mouth(scene):
    """Inside an open mouth: dark depth, the upper teeth under the top lip, the tongue low down."""
    inner = scene.mask("mouth_inner")
    over(scene.image, mix(scene.tone("lip", "line"), np.zeros(3, np.float32), 0.35), inner)
    tongue = shift(inner, 0, scene.px(0.03)) * inner
    over(scene.image, scene.tone("lip", "upper"), blur(tongue, scene.px(0.01)) * inner, 0.55)
    teeth = scene.mask("mouth_teeth") * inner
    over(scene.image, scene.tone("eye", "white"), teeth)
    if scene.shade_on:
        # The teeth's lower edge turns away into the mouth: a band of shadow along it.
        edge = teeth * (1.0 - shift(teeth, 0, -scene.px(0.012)))
        over(scene.image, scene.tone("eye", "white_shadow"), edge, 0.6)


def paint_tears(scene):
    """Tears welling on the lower lids and a wet track down each cheek."""
    fig, unit = scene.fig, scene.px(1.0)
    tones = scene.style["palette"]["eye"]
    for eye in EYES:
        lower = fig.paths[f"{eye}_lower"]
        welling = stroke(scene.size, lower + [0, 0.012 * unit], 0.028 * unit * taper(len(lower), 0.3, 0.3))
        screen(scene.image, scene.tone("eye", "catchlight"), welling * scene.mask("face"), 0.7)
        start = lower[len(lower) // 3]
        track = smooth([start, start + [0.02 * unit, 0.25 * unit], start + [0.0, 0.55 * unit]], samples=8)
        wet = stroke(scene.size, track, 0.035 * unit * taper(len(track), 0.6, 0.9, 0.7)) * scene.mask("face")
        over(scene.image, mix(scene.tone("skin", "light"), rgb(tones["white"]), 0.5), wet, 0.45)
        screen(scene.image, scene.tone("eye", "catchlight"), stroke(scene.size, track + [-0.008 * unit, 0], 0.010 * unit) * wet, 0.8)
        drop = fill(scene.size, ellipse(track[-1] + [0, 0.02 * unit], 0.03 * unit, 0.045 * unit, 20))
        over(scene.image, mix(scene.tone("skin", "light"), rgb(tones["white"]), 0.6), drop * scene.mask("face"), 0.7)
        scene.ink(np.vstack([ellipse(track[-1] + [0, 0.02 * unit], 0.03 * unit, 0.045 * unit, 20)]), 0.8, "eye", "iris_dark", opacity=0.4)


def paint_eye(scene, eye):
    """One eye, built the way it is drawn by hand: white, iris, pupil, lid, lashes, catchlights."""
    fig, unit = scene.fig, scene.px(1.0)
    render = scene.style["eye_render"]
    opening = scene.mask(f"{eye}_opening")
    iris_shape = fig.shapes[f"{eye}_iris"]
    iris = scene.mask(f"{eye}_iris") * opening
    center = fig.points[f"{eye}_center"]
    radius_x = 0.5 * np.ptp(iris_shape[:, 0])
    radius_y = 0.5 * np.ptp(iris_shape[:, 1])
    lid_shade = opening * (1.0 - shift(opening, 0, render["lid_shadow"] * unit))

    over(scene.image, scene.tone("eye", "white"), opening)
    if scene.shade_on:
        over(scene.image, scene.tone("eye", "white_shadow"), blur(lid_shade, 0.012 * unit) * opening, 0.85)

    iris_color = scene.tone("eye", "iris")
    if scene.shade_on:
        rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
        depth = np.clip((rows - (center[1] - radius_y)) / (2 * radius_y), 0.0, 1.0)
        ramp = smoothstep(depth, 0.18, 0.62)[..., None]
        iris_color = np.broadcast_to(mix(scene.tone("eye", "iris_dark"), iris_color, ramp), scene.size + (3,))
    over(scene.image, iris_color, iris)
    if scene.shade_on:
        glow = fill(scene.size, ellipse(center + [0, 0.52 * radius_y], 0.66 * radius_x, 0.40 * radius_y))
        over(scene.image, scene.tone("eye", "iris_light"), blur(glow, 0.010 * unit) * iris, 0.85)
    ring = stroke(scene.size, np.vstack([iris_shape, iris_shape[:1]]), render["iris_ring"] * unit)
    over(scene.image, scene.tone("eye", "iris_dark"), ring * opening, 0.9)
    over(scene.image, scene.tone("eye", "pupil"), scene.mask(f"{eye}_pupil") * opening)
    if scene.shade_on:
        multiply(scene.image, scene.tone("eye", "iris_dark"), blur(lid_shade, 0.010 * unit) * iris, 0.75)

    lash = scene.mask(f"{eye}_lash")
    spikes = fill_many(scene.size, [np.vstack([spike, spike[1] + [0, 0.012 * unit]])
                                    for spike in fig.paths[f"{eye}_lash_spikes"]])
    # Why hair tones: lashes and brows are hair, so they follow the hair colour automatically.
    over(scene.image, scene.tone("hair", "line"), np.maximum(lash, spikes * render["lash_spikes"]))
    lower = fig.paths[f"{eye}_lower"]
    outer_part = lower[:int(len(lower) * 0.55)]
    lower_widths = render["lower_lash"] * unit * taper(len(outer_part), 0.9, 0.0, 0.1)
    over(scene.image, scene.tone("hair", "line"), stroke(scene.size, outer_part, lower_widths), 0.9)
    crease = fig.paths[f"{eye}_crease"]
    crease_widths = render["crease"] * unit * taper(len(crease), 0.0, 0.3, 0.6)
    over(scene.image, scene.tone("skin", "deep"), stroke(scene.size, crease, crease_widths), 0.9)
    brow = fig.paths[f"{eye}_brow"]
    brow_widths = render["brow"] * unit * taper(len(brow), 0.55, 0.0, 0.3)
    over(scene.image, scene.tone("hair", "shadow"), stroke(scene.size, brow, brow_widths), render["brow_opacity"])
    if scene.shade_on and not scene.cel:
        lid = fill(scene.size, join(fig.paths[f"{eye}_upper"][6:-4], crease[::-1]))
        over(scene.image, scene.tone("skin", "shadow"), blur(lid, 0.012 * unit), render["lid_tone"])
        rim = stroke(scene.size, lower + [0, 0.016 * unit], 0.014 * unit * taper(len(lower), 0.2, 0.2))
        screen(scene.image, scene.tone("skin", "light"), blur(rim, 0.006 * unit), render["lower_rim"])
    if scene.shade_on and fig.extra.get("eye_closed", {}).get(eye, 0.0) < 0.5:
        toward_lamp = np.sign(fig.light[0])
        main = ellipse(center + [toward_lamp * 0.40 * radius_x, -0.42 * radius_y], 0.30 * radius_x, 0.24 * radius_y, 24, -20)
        small = ellipse(center - [toward_lamp * 0.38 * radius_x, -0.42 * radius_y], 0.13 * radius_x, 0.11 * radius_y, 16)
        over(scene.image, scene.tone("eye", "catchlight"), fill(scene.size, main))
        over(scene.image, scene.tone("eye", "catchlight"), fill(scene.size, small) * opening, 0.85)


# ------------------------------------------------------------------- sketch
def paint_sketch(fig):
    """Stage 1 image: the construction drawing, before any colour."""
    image = np.empty(fig.size + (3,), np.float32)
    image[:] = rgb(SKETCH_PAPER)
    chin_y = fig.head_frame.unproject(fig.paths["jaw"])[1].max()
    helpers = [on_face(np.column_stack([np.zeros(24), np.linspace(-1.35, chin_y, 24)])),
               on_face(np.column_stack([np.linspace(-0.95, 0.95, 24), np.zeros(24)]))]
    guides = [(fig.head_frame.project(helper), 1.6) for helper in helpers]
    over(image, rgb(SKETCH_GUIDE), stroke_many(fig.size, guides))
    lines = [(np.vstack([shape, shape[:1]]), 1.5) for name, shape in fig.shapes.items() if name not in SKETCH_HIDDEN]
    for name, path in fig.paths.items():
        if name in SKETCH_HIDDEN:
            continue
        lines += [(p, 1.5) for p in path] if isinstance(path, list) else [(path, 1.5)]
    lines += [(lock["path"], 1.5) for lock in fig.locks]
    over(image, rgb(SKETCH_PENCIL), stroke_many(fig.size, lines), 0.8)
    return image


# ------------------------------------------------------------------ driver
def run_hook(extras, name, scene):
    """Call an optional user function (see references/extending.md)."""
    hook = getattr(extras, name, None)
    if hook is not None:
        hook(scene)


def paint_figure(fig, style, seed, shade=True, lines=True, extras=None):
    """Paint every layer back to front and return the image.

    `extras` is an optional module with `after_background(scene)` and/or
    `after_figure(scene)`: the place to add props without editing this file.
    """
    scene = Scene(fig, style, seed, shade, lines)
    hair_form = hair_form_shadow(scene)
    paint_background(scene)
    run_hook(extras, "after_background", scene)
    accessories.remember_background(scene)
    paint_hair_section(scene, "back", hair_form, in_back=True)
    if "tail" in fig.hair:
        paint_hair_section(scene, "tail", hair_form)
    paint_body(scene)
    paint_outfit(scene)
    accessories.paint_strap_portrait(scene)
    accessories.paint_scarf_portrait(scene)
    paint_ears(scene)
    paint_face(scene)
    paint_nose(scene)
    paint_mouth(scene)
    for eye in EYES:
        paint_eye(scene, eye)
    if (fig.spec.get("expression") or {}).get("tears"):
        paint_tears(scene)
    accessories.paint_glasses(scene, "temples")
    paint_hair_section(scene, "far", hair_form, behind_body=True)
    paint_hair_section(scene, "near", hair_form)
    paint_hair_wisps(scene)
    accessories.paint_glasses(scene, "frames")
    accessories.paint_hat(scene)
    smoking.paint_mouth_cigarette(scene)
    run_hook(extras, "after_figure", scene)
    return scene.image
