"""End-to-end pipeline: spec -> layers -> render -> style finish -> post -> PNG.

Stages mirror an illustrator's process: plan (spec), construct (rig and
layers), line and color (renderer), style treatment, finishing (post).
Intermediate passes can be saved for inspection and debugging.
"""
import importlib
import os
import time

import cv2
import numpy as np

from . import duo, post, raster, spec as spec_mod, styles
from .background import make_background
from .character import build_layers, make_rig
from .color import hex_rgb
from .renderer import Renderer
from .scene import Layer, Light
from .interior import ROOMS

SUPERSAMPLE = {"draft": 1, "final": 2}
EMPTY_BACKGROUNDS = ("plain", "gradient")   # backdrops with no setting; watercolor may fade them to paper
# background type -> scene module rendered as the backdrop
SCENE_BACKGROUNDS = {"landscape": "landscape", "city": "city", **{room: "interior" for room in ROOMS}}
# how a scene's light reaches a figure standing in it: (tint, tint strength, rim color, rim strength)
SCENE_GRADE = {
    ("landscape", "day"): (None, 0.0, "#FFF0D0", 0.45),
    ("landscape", "sunset"): ("#FFC8A0", 0.25, "#FFB070", 0.75),
    ("landscape", "misty"): ("#DDE3EA", 0.15, "#E8ECF0", 0.35),
    ("landscape", "night"): ("#6A78A8", 0.45, "#A8BCEC", 0.70),
    ("city", "day"): (None, 0.0, "#FFF4E2", 0.40),
    ("city", "dusk"): ("#E8B4A4", 0.25, "#FFC08A", 0.65),
    ("city", "night"): ("#7C84B4", 0.45, "#FFD58A", 0.80),
    ("bedroom", "day"): ("#FFE6D2", 0.08, "#FFE2B8", 0.45),
    ("office", "day"): (None, 0.0, "#F4F6FA", 0.35),
    ("cafe", "day"): ("#FFD9B0", 0.12, "#FFD49A", 0.55),
    ("pool", "day"): (None, 0.0, "#FFF4E0", 0.50),
    ("gym", "day"): ("#E4E8EE", 0.06, "#F0F4FA", 0.40),
}


def make_light(lighting):
    key = lighting.get("key", "upper_left")
    vec = spec_mod.LIGHTS[key] if isinstance(key, str) else tuple(float(v) for v in key)
    rim_dir = lighting.get("rim_dir") or (-np.sign(vec[0]) or 1.0, -0.25)
    return Light(key=vec, key_color=lighting.get("key_color", "#FFF4E6"), rim_dir=tuple(rim_dir),
                 rim_color=lighting.get("rim_color", "#FFE2B8"), rim_strength=float(lighting.get("rim_strength", 0.55)))


def save_png(path, img):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ok = cv2.imwrite(path, (np.clip(img, 0, 1)[..., ::-1] * 255 + 0.5).astype(np.uint8))
    if not ok:
        raise IOError(f"could not write {path}")


def render_scene_background(spec, bg_type, W, H, light, style, style_name, seed):
    """Render a scene subject as the backdrop; return paint, its line pass, the figure's light and grade."""
    bg = spec["background"]
    module_name = SCENE_BACKGROUNDS[bg_type]
    scene_spec = dict(spec, subject=module_name, _backdrop=True)
    if module_name == "interior":
        scene_spec["interior"] = dict(bg.get("interior", {}), room=bg_type)
    else:
        # a figure stands center stage, so the landscape's framing tree is off unless asked for
        scene_spec[bg_type] = dict(bg.get(bg_type, {}), tree=bg.get(bg_type, {}).get("tree", False))
    module = importlib.import_module(f".{module_name}", __package__)
    s_layers, s_bg, s_light = module.build(scene_spec, W, H, light, seed)
    s_layers = styles.filter_layers(s_layers, style_name)
    paint, line_rgb, line_a, _ = Renderer(W, H, s_light, style, seed).render(s_layers, s_bg)
    time_of_day = scene_spec.get(bg_type, {}).get("time", "day")
    tint, strength, rim_color, rim_strength = SCENE_GRADE.get((bg_type, time_of_day), (None, 0.0, "#FFFFFF", 0.4))
    fig_light = Light(key=s_light.key, key_color=s_light.key_color, rim_dir=(-np.sign(s_light.key[0]) or 1.0, -0.25),
                      rim_color=rim_color, rim_strength=rim_strength)
    return paint, (line_rgb, line_a), fig_light, (tint, strength)


def figure_coverage(rnd, layers):
    cov = np.zeros((rnd.h, rnd.w), np.float32)
    for L in layers:
        if L.opacity > 0 and L.blend.value == "over":
            cov = np.maximum(cov, rnd.masks[L.name] * L.opacity)
    return cov


def apply_grade(paint, cov, grade):
    """Tint the figure toward the scene's light (dusk, night) so it does not look pasted on."""
    tint, strength = grade
    if tint is None or strength <= 0:
        return paint
    return raster.multiply(paint, hex_rgb(tint), cov * strength)


def merge_lines(fig_rgb, fig_a, scene_rgb, scene_a, cov):
    """Scene lines survive only where the figure does not cover them."""
    s_a = scene_a * (1 - cov) * (1 - fig_a)
    total = fig_a + s_a
    rgb = (fig_rgb * fig_a[..., None] + scene_rgb * s_a[..., None]) / np.maximum(total[..., None], 1e-4)
    return rgb.astype(np.float32), np.clip(total, 0, 1).astype(np.float32)


STAGE_SHADOWS = ("ground_shadow", "drop_shadow")


def keep_masks(rnd, layers, ss, H, W):
    """Output-resolution masks the style finish reads: tagged focus layers, else every visible layer."""
    keep = {L.name for L in layers if "focus" in L.tags} or {L.name for L in layers if L.opacity > 0}
    masks = raster.MaskStore(H, W)
    for k in rnd.masks:
        if k in keep:
            masks[k] = styles.downsample(rnd.masks[k], ss)
    return masks


def merge_masks(acc, new, cov):
    """Masks of a pass drawn over earlier ones: the new coverage hides what it covers."""
    if acc is None:
        return new
    hide = 1 - cov
    for k in acc:
        if acc.box(k) is not None:
            acc[k] = acc[k] * hide
    for k in new:
        acc[k] = np.maximum(acc[k], new[k]) if k in acc else new[k]
    return acc


def _renamed(layer, prefix):
    return Layer(**{**layer.__dict__, "name": prefix + layer.name})


def figure_passes(stacks):
    """Layer stacks (draw order) -> [(figure position or None, layers)]. One figure is one pass (v8).

    Two figures: seats and floor shadows of both go first, so a bed or chair never covers the
    other figure; then each figure back to front.
    """
    if len(stacks) == 1:
        return [(0, stacks[0])]
    stage, bodies = [], []
    for i, layers in enumerate(stacks):
        body = []
        for L in layers:
            if "seat" in L.tags or L.name in STAGE_SHADOWS:
                stage.append(_renamed(L, f"p{i}_"))     # names are mask keys: keep them unique in one pass
            else:
                body.append(L)
        bodies.append((i, body))
    return ([(None, stage)] if stage else []) + bodies


def tagged_coverage(rnd, layers, tag):
    cov = np.zeros((rnd.h, rnd.w), np.float32)
    for L in layers:
        if tag in L.tags and L.opacity > 0:
            cov = np.maximum(cov, rnd.masks[L.name])
    return cov


def render_figures(spec, W, H, ss, light, style, style_name, seed, log, t0):
    """Backdrop plus one or two figures.

    Returns paint, lines (rgb, alpha), output-res masks, the figures' light (a scene backdrop
    supplies its own) and the layer count.
    """
    bg_type = spec["background"].get("type")
    if "characters" in spec:
        figures = duo.plan(spec, W * ss, H * ss)
    else:
        figures = [duo.Figure(spec, make_rig(spec, W * ss, H * ss), 0)]
    scene_lines, grade = None, None
    if bg_type in SCENE_BACKGROUNDS:
        # the figures stand in a rendered scene and take its light
        bg, scene_lines, light, grade = render_scene_background(spec, bg_type, W * ss, H * ss, light, style,
                                                                style_name, seed)
        log(f"[scene] {bg_type} background, {time.time() - t0:.1f}s")
    else:
        focus = np.mean([f.rig.head([(0.0, 0.55, 0.0)])[0] for f in figures], axis=0)
        bg = make_background(spec["background"], W * ss, H * ss, focus, seed)
    stacks = [styles.filter_layers(build_layers(f.spec, f.rig, light, seed), style_name) for f in figures]
    passes = figure_passes(stacks)
    log(f"[construct] character x{len(figures)}: {sum(len(p) for _, p in passes)} layers, {time.time() - t0:.1f}s")
    paint, lines, masks = bg, scene_lines, None
    cov_all = np.zeros((H * ss, W * ss), np.float32)
    heads, bodies = {}, {}
    for i, layers in passes:
        rnd = Renderer(W * ss, H * ss, light, style, seed)
        paint, line_rgb, line_a, _ = rnd.render(layers, paint)
        cov = figure_coverage(rnd, layers)
        lines = (line_rgb, line_a) if lines is None else merge_lines(line_rgb, line_a, *lines, cov)
        cov_all = np.maximum(cov_all, cov)
        masks = merge_masks(masks, keep_masks(rnd, layers, ss, H, W), styles.downsample(cov, ss))
        if i is not None and len(figures) > 1:
            heads[i], bodies[i] = tagged_coverage(rnd, layers, "head"), layers
    for i, f in enumerate(figures):
        if not f.reveal:
            continue
        # the figure again, kept only inside its reveal region: an arm resting over the partner's shoulder
        rz = raster.Rasterizer(W * ss, H * ss)
        region = rz.fill(f.reveal).copy()
        if f.reveal_cut:
            region *= 1 - rz.fill(f.reveal_cut)
        region *= 1 - heads[f.partner]
        rnd = Renderer(W * ss, H * ss, light, style, seed)
        again, line_rgb, line_a, _ = rnd.render(bodies[i], paint)
        cov = figure_coverage(rnd, bodies[i]) * region
        paint = paint * (1 - cov[..., None]) + again * cov[..., None]
        lines = merge_lines(line_rgb, line_a * region, *lines, cov)
        cov_all = np.maximum(cov_all, cov)
    if grade is not None:
        paint = apply_grade(paint, cov_all, grade)
    return paint, lines, masks, light, sum(len(p) for _, p in passes)


def render(user_spec, out_path, passes_dir=None, log=print):
    t0 = time.time()
    spec = spec_mod.normalize(user_spec)
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    seed = int(spec["canvas"].get("seed", 0))
    ss = SUPERSAMPLE[spec["quality"]]
    style_name = styles.StyleName(spec["style"])
    style = styles.PRESETS[style_name]

    light = make_light(spec["lighting"])
    subject = spec["subject"]
    if subject == "character":
        paint, (line_rgb, line_a), masks, light, n_layers = render_figures(spec, W, H, ss, light, style, style_name,
                                                                          seed, log, t0)
        log(f"[render] paint + line passes, {time.time() - t0:.1f}s")
    else:
        module = importlib.import_module(f".{subject}", __package__)
        layers, bg, light = module.build(spec, W * ss, H * ss, light, seed)
        layers = styles.filter_layers(layers, style_name)
        log(f"[construct] {subject}: {len(layers)} layers, {time.time() - t0:.1f}s")
        rnd = Renderer(W * ss, H * ss, light, style, seed)
        paint, line_rgb, line_a, _ = rnd.render(layers, bg)
        log(f"[render] paint + line passes, {time.time() - t0:.1f}s")
        masks = keep_masks(rnd, layers, ss, H, W)
        n_layers = len(layers)

    paint = styles.downsample(paint, ss)
    premul = styles.downsample(line_rgb * line_a[..., None], ss)
    line_a = styles.downsample(line_a, ss)
    line_rgb = premul / np.maximum(line_a[..., None], 1e-4)
    backdrop = subject == "character" and spec["background"].get("type") not in EMPTY_BACKGROUNDS
    img = styles.finish(style_name, paint, line_rgb, line_a, masks, seed, backdrop=backdrop)
    log(f"[style] {style_name.value}, {time.time() - t0:.1f}s")
    post_spec = spec_mod.deep_merge(styles.POST_DEFAULTS[style_name], spec.get("post", {}))
    img = post.apply(img, post_spec, light, seed)
    save_png(out_path, img)
    if passes_dir:
        save_png(os.path.join(passes_dir, "01_paint.png"), paint)
        save_png(os.path.join(passes_dir, "02_lines.png"), 1 - line_a[..., None] * (1 - line_rgb))
        save_png(os.path.join(passes_dir, "03_figure_mask.png"),
                 np.repeat(styles.union_mask(masks)[..., None], 3, axis=2))
    log(f"[done] {out_path} ({W}x{H}), {time.time() - t0:.1f}s")
    return {"path": out_path, "seconds": round(time.time() - t0, 1), "layers": n_layers}
