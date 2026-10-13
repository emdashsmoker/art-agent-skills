"""paintkit.scene: spec-driven portrait pipeline.

A scene spec (plain dict / JSON) names the style, the character, the
background and the finish. `build` returns the layered canvas so custom
elements can still be painted before `finish` flattens and post-processes.
"""
from __future__ import annotations

import inspect
from dataclasses import fields, replace

import numpy as np

from . import anatomy as an
from . import back as bk
from . import backdrop as bd
from . import body as bo
from . import core as pk
from . import duo
from . import finish as fn
from . import light as lt
from . import scenery as sn
from . import urban as ur
from . import figure as fg
from . import furniture
from . import profile as pf
from . import props as pr
from .character import Portrait
from .spec import CharacterSpec, Palette, RenderStyle, with_gender_defaults

REFERENCE_HEIGHT = 1500.0     # pixel sizes in presets are tuned for this canvas height

# --------------------------------------------------------------------------
# Style presets: how to render (RenderStyle) + how to finish (post chain)
# --------------------------------------------------------------------------
RENDER_STYLES = {
    # Hard two-tone shadows, inked colored lines, band highlight on the hair.
    "anime": RenderStyle(name="anime"),
    # Soft gradients, thin faint lines, rim light, fuller lips.
    "illust": RenderStyle(
        name="illust", shadow_softness=0.16, cast_softness=0.012, shadow_strength=0.85,
        face_shadow_level=0.05, line_width=0.003, line_opacity=0.75, line_variation=0.7,
        airbrush=1.0, hair_strands=1.3, hair_highlight="soft", rim_light=0.8, lip_render="full"),
    # No lines, broad soft light; the brush-stroke pass supplies the texture.
    "painterly": RenderStyle(
        name="painterly", shadow_softness=0.30, cast_softness=0.02, shadow_strength=0.9,
        face_shadow_level=0.18, line_width=0.0, airbrush=1.0, hair_strands=0.6,
        hair_highlight="soft", rim_light=0.3, lip_render="full", eye_detail=0.8),
}

FINISH_DEFAULTS = {
    "anime": dict(diffusion=0.22, bloom=0.25, contrast=1.04, saturation=1.06,
                  shadow_tint="#2a2f6a", highlight_tint="#fff3e0", tint_strength=0.10,
                  vignette=0.0, grain=0.012, tilt=0.0),
    "illust": dict(diffusion=0.28, bloom=0.35, contrast=1.06, saturation=1.08,
                   shadow_tint="#3a2a5a", highlight_tint="#ffe6c0", tint_strength=0.14,
                   vignette=0.22, grain=0.015, tilt=0.0),
    "painterly": dict(diffusion=0.0, bloom=0.0, contrast=1.05, saturation=1.05,
                      shadow_tint="#2a2418", highlight_tint="#fff0d0", tint_strength=0.10,
                      vignette=0.0, grain=0.0, radii=(26, 13, 6, 3, 2), weave=0.04, tilt=0.0),
}

# Named looks layered over a style's own finish; keys given in the spec still win.
FINISH_PRESETS = {
    # Post-Soviet cold wave: drained color, blue-grey shadows, sodium-orange highlights, film grain.
    "doomer": dict(saturation=0.70, contrast=1.08, shadow_tint="#1a2436", highlight_tint="#ffb878",
                   tint_strength=0.22, vignette=0.32, grain=0.028, bloom=0.30, diffusion=0.12),
}

BACKDROPS = {
    "gradient": lambda layer, size, o: bd.gradient(layer, o["top"], o["bottom"], o.get("angle", 90.0)),
    "glow": lambda layer, size, o: bd.glow(
        layer, _abs_point(o.get("center", (0.5, 0.35)), size), o.get("radius", 0.45) * size[1],
        o["color"], o.get("opacity", 0.6)),
    "bokeh": lambda layer, size, o: bd.bokeh(
        layer, o["colors"], o.get("count", 26),
        tuple(v * size[1] / REFERENCE_HEIGHT for v in o.get("size", (30, 110))),
        o.get("opacity", 0.35), o.get("seed", 0)),
    "wash": lambda layer, size, o: bd.wash(
        layer, o["colors"], o.get("scale", 0.32) * size[1], o.get("seed", 0)),
    "light_shafts": lambda layer, size, o: bd.light_shafts(
        layer, o.get("color", "#ffffff"), o.get("count", 3), o.get("angle", 62.0),
        o.get("width", 0.10) * size[1], o.get("opacity", 0.3), seed=o.get("seed", 0)),
    "petals": lambda layer, size, o: bd.petals(
        layer, o["color"], o.get("count", 26),
        tuple(v * size[1] / REFERENCE_HEIGHT for v in o.get("size", (8, 26))), o.get("seed", 0)),
}


# Scenery builders take fractions of the canvas already, so they plug in as-is.
SCENERY_OPS = ("sky", "sun", "stars", "clouds", "ridge", "ground", "grass", "flowers", "water", "tree",
               "pine", "tree_line", "skyline", "street", "room") + ur.OPS


def _scenery_op(name: str, layer: pk.Layer, options: dict, light) -> None:
    function = getattr(ur if name in ur.OPS else sn, name)
    allowed = set(inspect.signature(function).parameters) - {"layer"}
    _check_keys({k: v for k, v in options.items() if k != "type"}, allowed, f"background '{name}'")
    kwargs = {k: v for k, v in options.items() if k != "type"}
    if "light" in allowed:
        kwargs["light"] = light              # one light for figure and scenery alike
    function(layer, **kwargs)


def _abs_point(fraction, size):
    return (fraction[0] * size[0], fraction[1] * size[1])


TOP_LEVEL_KEYS = ("canvas", "style", "seed", "subject", "character", "figure", "palette", "placement", "light",
                  "background", "extras", "foreground", "ambient", "style_overrides", "finish", "duo")
EXTRA_KEYS = ("character", "palette", "figure", "at", "placement")
SECTION_KEYS = {
    "placement": ("head_height", "eye_center", "pelvis", "shot", "x"),
    "figure": ("pose", "pose_overrides", "outfit", "build", "heels", "ground_shadow", "furniture",
               "furniture_color", "facing", "look", "cigarette"),
    "light": ("azimuth", "elevation"),
    "ambient": ("color", "opacity", "from"),
}


def _check_keys(values: dict, allowed, label: str) -> None:
    """A misspelled key would otherwise be ignored silently and the picture
    would just not change, which is far harder to notice than an error."""
    unknown = set(values) - set(allowed)
    if unknown:
        raise ValueError(f"unknown {label} keys {sorted(unknown)}; allowed: {sorted(allowed)}")


def _dataclass_from(cls, values: dict, label: str):
    _check_keys(values, {f.name for f in fields(cls)}, label)
    return cls(**values)


def validate(spec: dict) -> str:
    """Check every key of a spec. Returns the style name."""
    _check_keys(spec, TOP_LEVEL_KEYS, "spec")
    name = spec.get("style", "anime")
    if name not in RENDER_STYLES:
        raise ValueError(f"unknown style '{name}', expected one of {list(RENDER_STYLES)}")
    for section, allowed in SECTION_KEYS.items():
        _check_keys(spec.get(section) or {}, allowed, section)
    _check_keys(spec.get("style_overrides", {}), {f.name for f in fields(RenderStyle)}, "style_overrides")
    finish_opts = spec.get("finish", {})
    _check_keys(finish_opts, set(FINISH_DEFAULTS[name]) | {"preset"}, "finish")
    if "preset" in finish_opts and finish_opts["preset"] not in FINISH_PRESETS:
        raise ValueError(f"unknown finish preset '{finish_opts['preset']}', expected one of {list(FINISH_PRESETS)}")
    return name


def _style(spec: dict) -> RenderStyle:
    return replace(RENDER_STYLES[validate(spec)], **spec.get("style_overrides", {}))


def paint_backdrop(layer: pk.Layer, size, operations: list, light=None) -> None:
    for op in operations:
        kind = op.get("type")
        if kind in SCENERY_OPS:
            _scenery_op(kind, layer, op, light)
        elif kind in BACKDROPS:
            BACKDROPS[kind](layer, size, op)
        else:
            raise ValueError(f"unknown background type '{kind}', expected one of "
                             f"{list(BACKDROPS) + list(SCENERY_OPS)}")


def build(spec: dict):
    """Paint background and figure. Returns (canvas, portrait); nothing is flattened yet."""
    subject = validate_subject(spec)
    width, height = spec.get("canvas", (1200, 1500))
    canvas = pk.Canvas(width, height)
    light_cfg = spec.get("light", {})
    light = lt.light_vector(light_cfg.get("azimuth", 135.0), light_cfg.get("elevation", 42.0))
    paint_backdrop(canvas.layer("background"), (width, height),
                   spec.get("background", [{"type": "gradient", "top": "#cfd8e6", "bottom": "#eef1f6"}]), light)
    if spec.get("extras"):
        paint_extras(canvas, spec, light)
    if subject == "none":                 # scenery only: no figure, nothing more to build
        validate(spec)
        if spec.get("foreground"):
            paint_backdrop(canvas.layer("foreground"), (width, height), spec["foreground"], light)
        return canvas, None
    character_values, palette_values = with_gender_defaults(spec.get("character", {}), spec.get("palette", {}))
    palette = _dataclass_from(Palette, palette_values, "palette")
    character = _dataclass_from(CharacterSpec, {**character_values, "palette": palette}, "character")
    place = spec.get("placement", {})
    _check_framing(subject, spec, place)
    if subject == "figure":
        if spec.get("duo"):
            portrait = _build_duo(canvas, spec, character, light)
        else:
            portrait = _build_figure(canvas, spec, character, light)
    else:
        head_height = place.get("head_height", 0.413) * height
        eye_center = _abs_point(place.get("eye_center", (0.5, 0.36)), (width, height))
        portrait = Portrait(canvas, character, _style(spec), head_height, eye_center, light).render()
    ambient = spec.get("ambient")
    if ambient:
        # Tinting the lower figure with the scene color seats it in the scene.
        ramp = pk.linear_ramp(canvas.shape, (0, height * ambient.get("from", 0.55)), (0, height))
        canvas.layer("ambient").paint(ramp * _people_mask(portrait), ambient["color"],
                                      ambient.get("opacity", 0.25))
    front = spec.get("foreground")
    if front:
        layer = canvas.layer("foreground")
        paint_backdrop(layer, (width, height), front, light)
        # Scattered foreground pieces must never land on the face.
        layer.erase(np.clip(pk.blur(portrait.masks["face"], portrait.px(0.03)) * 2.0, 0.0, 1.0))
    return canvas, portrait


def _people_mask(portrait) -> np.ndarray:
    """Silhouette of the main figure and, in a two-shot, its partner."""
    mask = portrait.figure_mask()
    partner = getattr(portrait, "partner", None)
    return mask if partner is None else np.maximum(mask, partner.figure_mask())


def _build_duo(canvas: pk.Canvas, spec: dict, character: CharacterSpec, light) -> fg.Figure:
    """Two-shot branch of `build`: the main figure plus a partner (see duo.py)."""
    pair_spec = spec["duo"]
    _check_keys(pair_spec, duo.DUO_KEYS, "duo")
    partner = pair_spec.get("partner") or {}
    _check_keys(partner, duo.PARTNER_KEYS, "duo partner")
    partner_cfg = partner.get("figure", {})
    _check_keys(partner_cfg, SECTION_KEYS["figure"], "duo partner figure")
    character_values, palette_values = with_gender_defaults(partner.get("character", {}), partner.get("palette", {}))
    palette = _dataclass_from(Palette, palette_values, "duo partner palette")
    partner_character = _dataclass_from(CharacterSpec, {**character_values, "palette": palette},
                                        "duo partner character")
    cfg, place = spec["figure"], spec.get("placement", {})
    width, height = canvas.width, canvas.height
    head_px = place.get("head_height", 0.115) * height
    gap = pair_spec.get("gap", duo.DEFAULT_GAP.get(pair_spec.get("pose", "side_by_side"), 1.8))
    side = duo.SIDES_OF.get(pair_spec.get("side", "right"), 1.0)
    if "shot" in place:                    # frame both: the taller crown, the shared floor, the pair's width
        style = _style(spec)
        ext = _extents(canvas, cfg, character, style, light)
        other = _extents(canvas, partner_cfg, partner_character, style, light)
        ratio = duo.stature_ratio(character.gender, partner_character.gender, stature_units, STATURE_M)
        ext["crown"] = min(ext["crown"], ext["full"] - (other["full"] - other["crown"]) * ratio)
        head_px, pelvis = _shot_placement(canvas, place, ext, gap, side)
    elif "pelvis" in place:
        pelvis = _abs_point(place["pelvis"], (width, height))
    else:                                  # center the pair
        pelvis = (width * 0.5 - side * gap * head_px / 2, height * 0.47)
    pair = duo.Duo(canvas, pair_spec, cfg, character, partner_character, partner_cfg, _style(spec), light,
                   head_px, pelvis, make_figure, stature_units, STATURE_M)
    return pair.render(cfg.get("ground_shadow"), partner_cfg.get("ground_shadow", cfg.get("ground_shadow")))


SUBJECTS = ("portrait", "figure", "none")


def _check_framing(subject: str, spec: dict, place: dict) -> None:
    """Keys that only mean something for full figures fail loudly instead of being ignored."""
    if subject != "figure" and ({"shot", "x"} & set(place)):
        raise ValueError("'placement.shot' and 'placement.x' frame full figures only; a bust uses "
                         "'head_height' and 'eye_center'")
    if "shot" in place and ({"head_height", "pelvis"} & set(place)):
        raise ValueError("'placement.shot' sets the size and position itself; drop 'head_height' and 'pelvis' "
                         "(use 'x' to move the figure sideways)")
    if "x" in place and "shot" not in place:
        raise ValueError("'placement.x' centers a 'placement.shot' framing; add 'shot' or use 'pelvis'")
    if spec.get("duo") and subject != "figure":
        raise ValueError("'duo' needs a full figure: add a 'figure' section")


def validate_subject(spec: dict) -> str:
    """portrait = bust rig, figure = full-body rig, none = scenery only."""
    subject = spec.get("subject", "figure" if "figure" in spec else "portrait")
    if subject not in SUBJECTS:
        raise ValueError(f"unknown subject '{subject}', expected one of {SUBJECTS}")
    return subject


# Framing presets (placement.shot): where the bottom edge of the picture cuts the figure.
SHOTS = ("full", "thigh", "knee", "waist", "bust")
SHOT_MARGIN_TOP, SHOT_MARGIN_BOTTOM = 0.05, 0.05     # of the canvas height; the bottom margin only in "full"
HAIR_ABOVE_CROWN = 0.08         # head units of hair above the skull top
PAIR_WIDTH_MARGIN = 2.4         # head units added to the pelvis gap for the pair's outer arms
SHOT_MAX_WIDTH = 0.94           # share of the canvas width a pair may span


def _extents(canvas: pk.Canvas, cfg: dict, character: CharacterSpec, style: RenderStyle, light) -> dict:
    """Head-unit heights (y down from the pelvis) of the crown and of each shot's cut line."""
    figure = make_figure(canvas, cfg, character, style, 100.0, (0.0, 0.0), light)
    j = figure.joints
    hip = max(float(j["hip_left"][1]), float(j["hip_right"][1]))
    knee = max(float(j["knee_left"][1]), float(j["knee_right"][1]))
    crown = float(j["eyes"][1]) + an.CROWN_Y - HAIR_ABOVE_CROWN
    # Hands raised over the head (a stretch, a wave) set the top of the frame instead.
    hands_top = min(float(j["wrist_left"][1]), float(j["wrist_right"][1])) - figure.plan.hand_length
    return {"crown": min(crown, hands_top - HAIR_ABOVE_CROWN), "full": furniture.floor_level(figure),
            "thigh": hip + 0.55 * (knee - hip), "knee": knee + 0.25, "waist": 0.35,
            "bust": float(j["chest"][1]) + 0.90}


def _shot_placement(canvas: pk.Canvas, place: dict, ext: dict, pair_gap: float = 0.0, pair_side: float = 1.0):
    """(head height px, pelvis px) that frame the figure (or pair) for placement.shot."""
    shot = place["shot"]
    if shot not in SHOTS:
        raise ValueError(f"unknown shot '{shot}', expected one of {SHOTS}")
    width, height = canvas.width, canvas.height
    top_px = height * SHOT_MARGIN_TOP
    bottom_px = height * (1.0 - SHOT_MARGIN_BOTTOM) if shot == "full" else float(height)
    span = ext[shot] - ext["crown"]
    head_px = (bottom_px - top_px) / span
    if pair_gap:                           # a pair must also fit across
        head_px = min(head_px, width * SHOT_MAX_WIDTH / (pair_gap + PAIR_WIDTH_MARGIN))
    spare = (bottom_px - top_px - span * head_px) / 2.0 if shot == "full" else 0.0
    center = place.get("x", 0.5) * width
    pelvis_x = center - pair_side * pair_gap * head_px / 2.0
    return head_px, (pelvis_x, top_px + spare - ext["crown"] * head_px)


def _build_figure(canvas: pk.Canvas, spec: dict, character: CharacterSpec, light) -> fg.Figure:
    """Full-body branch of `build`: placement by the pelvis position, or by a shot preset."""
    cfg, place = spec["figure"], spec.get("placement", {})
    width, height = canvas.width, canvas.height
    head_height = place.get("head_height", 0.115) * height
    pelvis = _abs_point(place.get("pelvis", (0.5, 0.47)), (width, height))
    if "shot" in place:
        head_height, pelvis = _shot_placement(canvas, place, _extents(canvas, cfg, character, _style(spec), light))
    figure = make_figure(canvas, cfg, character, _style(spec), head_height, pelvis, light)
    shadow = cfg.get("ground_shadow")
    if shadow:
        # Painted before the figure so it lies under the feet.
        figure.paint_ground_shadow(canvas.layer("ground_shadow", mode="multiply"), shadow)
    return figure.render()


def make_figure(canvas: pk.Canvas, cfg: dict, character: CharacterSpec, style: RenderStyle, head_height: float,
                pelvis, light) -> fg.Figure:
    """Front rig, or the side-view rig when the pose is a side pose."""
    figure = _make_rig(canvas, cfg, character, style, head_height, pelvis, light)
    figure.cigarette = pr.check(cfg.get("cigarette"))
    return figure


def _make_rig(canvas: pk.Canvas, cfg: dict, character: CharacterSpec, style: RenderStyle, head_height: float,
              pelvis, light) -> fg.Figure:
    name = cfg.get("pose", "standing")
    build = bo.make_build(cfg.get("build"))
    outfit = cfg.get("outfit", fg.DEFAULT_OUTFIT[character.gender])
    heels = bool(cfg.get("heels", False))
    if name in pf.SIDE_POSES:
        pose = pf.make_side_pose(name, cfg.get("pose_overrides"))
        return pf.SideFigure(canvas, character, style, head_height, pelvis, pose, outfit, build, heels, light,
                             cfg.get("facing", "right"), cfg.get("furniture"), cfg.get("furniture_color"))
    if "facing" in cfg:
        raise ValueError("'facing' applies to side poses only: " + ", ".join(pf.SIDE_POSES))
    if name in bk.BACK_POSES:
        pose, look = bk.make_back_pose(name, cfg.get("pose_overrides"))
        return bk.BackFigure(canvas, character, style, head_height, pelvis, pose, outfit, build, heels, light,
                             cfg.get("furniture"), cfg.get("furniture_color"), look=cfg.get("look", look))
    if "look" in cfg:
        raise ValueError("'look' applies to back poses only: " + ", ".join(bk.BACK_POSES))
    if name not in bo.POSES:
        raise ValueError(f"unknown pose '{name}'; front view: {', '.join(bo.POSES)}; "
                         f"side view: {', '.join(pf.SIDE_POSES)}; back view: {', '.join(bk.BACK_POSES)}")
    pose = bo.make_pose(name, cfg.get("pose_overrides"))
    return fg.Figure(canvas, character, style, head_height, pelvis, pose, outfit, build, heels, light,
                     cfg.get("furniture"), cfg.get("furniture_color"))


# Extras: other people placed in the scene with the full-body rig.
STATURE_M = {"female": 1.63, "male": 1.76}
EXTRA_SHADOW = 0.35
CROP_HALF_WIDTH, CROP_ABOVE, CROP_BELOW = 2.6, 3.7, 4.6      # head units around the pelvis


def stature_units(gender: str) -> tuple:
    """(height in head units, pelvis height above the soles in head units) of a standing figure."""
    plan = bo.plan_for(gender)
    above = plan.spine_low + plan.spine_high + plan.neck_rise + plan.neck_length + plan.skull_to_eyes - an.CROWN_Y
    below = plan.hip_drop + plan.thigh + plan.shin + furniture.FOOT_BOTTOM
    return above + below, below


def _street_view(spec: dict, canvas: pk.Canvas) -> sn.StreetView:
    streets = [op for op in spec.get("background", []) if op.get("type") == "street"]
    if not streets:
        raise ValueError("an extra placed with 'at' needs a 'street' in the background; use 'placement' instead")
    street = streets[0]
    return sn.StreetView(canvas.get("background"), street.get("horizon", 0.5), street.get("vanish_x", 0.5),
                         street.get("eye", 1.6))


def _extra_placement(extra: dict, gender: str, spec: dict, canvas: pk.Canvas) -> tuple:
    """(head height px, pelvis px) from street meters ('at': [x, z]) or canvas fractions ('placement')."""
    if "at" in extra:
        x, z = extra["at"]
        if z <= 0:
            raise ValueError("extra 'at' needs a positive distance z (meters in front of the camera)")
        view = _street_view(spec, canvas)
        total, below = stature_units(gender)
        unit_m = STATURE_M[gender] / total
        return unit_m * view.focal / z, view.project(x, below * unit_m, z)
    place = extra.get("placement")
    if not place:
        raise ValueError("every extra needs 'at' (street meters) or 'placement' (head_height, pelvis)")
    _check_keys(place, ("head_height", "pelvis"), "extra placement")
    return place["head_height"] * canvas.height, np.array(_abs_point(place["pelvis"], (canvas.width, canvas.height)))


def paint_extras(canvas: pk.Canvas, spec: dict, light) -> None:
    """Other people in the scene, drawn with the full-body rig into the background, far ones first.

    Each one is rendered on a small canvas cut from the current picture, so
    every blend mode composites exactly and small figures stay cheap."""
    background = canvas.get("background")
    style = _style(spec)
    jobs = []
    for index, extra in enumerate(spec["extras"]):
        _check_keys(extra, EXTRA_KEYS, f"extras[{index}]")
        _check_keys(extra.get("figure", {}), SECTION_KEYS["figure"], f"extras[{index}] figure")
        character_values, palette_values = with_gender_defaults(extra.get("character", {}),
                                                                 extra.get("palette", {}))
        palette = _dataclass_from(Palette, palette_values, "palette")
        character = _dataclass_from(CharacterSpec, {**character_values, "palette": palette}, "character")
        head_px, pelvis = _extra_placement(extra, character.gender, spec, canvas)
        jobs.append((head_px, pelvis, character, extra.get("figure", {})))
    for head_px, pelvis, character, cfg in sorted(jobs, key=lambda job: job[0]):
        x0 = int(max(pelvis[0] - CROP_HALF_WIDTH * head_px, 0))
        x1 = int(min(pelvis[0] + CROP_HALF_WIDTH * head_px, canvas.width))
        y0 = int(max(pelvis[1] - CROP_ABOVE * head_px, 0))
        y1 = int(min(pelvis[1] + CROP_BELOW * head_px, canvas.height))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue                       # outside the picture
        scene_now = canvas.flatten()
        crop = pk.Canvas(x1 - x0, y1 - y0)
        crop.layer("background").paint(np.ones(crop.shape, np.float32), scene_now[y0:y1, x0:x1])
        offset = np.array([x0, y0], np.float32)
        figure = make_figure(crop, cfg, character, style, head_px, np.asarray(pelvis, np.float32) - offset, light)
        figure.paint_ground_shadow(crop.layer("ground_shadow", mode="multiply"), cfg.get("ground_shadow", EXTRA_SHADOW))
        figure.render()
        region = np.zeros(canvas.shape, np.float32)
        region[y0:y1, x0:x1] = 1.0
        pasted = scene_now.copy()
        pasted[y0:y1, x0:x1] = crop.flatten()
        background.paint(region, pasted)


BODY_DETAIL = 0.5                 # extra stroke density on the body of a painterly figure


def finish(canvas: pk.Canvas, portrait: Portrait, spec: dict) -> np.ndarray:
    """Flatten and apply the style's post chain. Returns float RGB."""
    name = spec.get("style", "anime")
    given = dict(spec.get("finish", {}))
    preset = FINISH_PRESETS.get(given.pop("preset", None), {})
    opts = {**FINISH_DEFAULTS[name], **preset, **given}
    unit = canvas.height / REFERENCE_HEIGHT
    seed = spec.get("seed", 0)
    img = canvas.flatten()
    if name == "painterly":
        detail = None
        if portrait is not None:
            # The face keeps finer strokes than the rest, the eyes the finest.
            detail = pk.blur(portrait.masks["face"], 20 * unit) * 0.6 + portrait.masks["eyes"] * 1.4
            if isinstance(portrait, fg.Figure):      # hands are the second place the eye checks
                hands = np.maximum.reduce([hand.mask for hand in portrait.hands.values()])
                detail = detail + pk.blur(hands, 6 * unit) * 0.8
                # Skin covered only in patches by the fine brush reads as blotches; covering it evenly keeps it smooth.
                m = portrait.masks
                body = np.maximum.reduce([m["torso"], m["legs"], m["arm_left"], m["arm_right"]])
                detail = detail + pk.blur(body, 8 * unit) * BODY_DETAIL
            partner = getattr(portrait, "partner", None)
            if partner is not None:           # a two-shot: the partner's face gets the same fine strokes
                detail = detail + pk.blur(partner.masks["face"], 20 * unit) * 0.6 + partner.masks["eyes"] * 1.4
        radii = tuple(max(r * unit, 1.5) for r in opts["radii"])
        img = fn.painterly(img, radii=radii, detail=detail, seed=seed)
    if opts["tilt"]:                      # before the glow and grain, which belong to the frame
        img = fn.tilt(img, opts["tilt"])
    if opts["diffusion"] > 0:
        img = fn.diffusion(img, 14 * unit, opts["diffusion"])
    if opts["bloom"] > 0:
        img = fn.bloom(img, 0.80, 18 * unit, opts["bloom"])
    img = fn.grade(img, opts["contrast"], opts["saturation"], opts["shadow_tint"],
                   opts["highlight_tint"], opts["tint_strength"])
    if opts["vignette"] > 0:
        img = fn.vignette(img, opts["vignette"])
    if opts.get("weave", 0) > 0:
        img = fn.canvas_weave(img, opts["weave"])
    if opts["grain"] > 0:
        img = fn.grain(img, opts["grain"], seed)
    return img


def render(spec: dict) -> np.ndarray:
    canvas, portrait = build(spec)
    return finish(canvas, portrait, spec)


def process_sheet(spec: dict) -> np.ndarray:
    """Four panels showing the production stages: guide, flats, shading+line, final."""
    canvas, portrait = build(spec)
    final = finish(canvas, portrait, spec)
    if portrait is None:
        raise ValueError("a process sheet needs a figure; this spec is scenery only")
    flat_spec = {**spec, "style_overrides": {**spec.get("style_overrides", {}),
                                             "shadow_strength": 0.0, "airbrush": 0.0,
                                             "hair_highlight": "none", "rim_light": 0.0}}
    flat_canvas, _ = build(flat_spec)
    panels = [construction_guide(portrait), flat_canvas.flatten(), canvas.flatten(), final]
    return np.hstack([p[::2, ::2] for p in panels])


def construction_guide(portrait: Portrait) -> np.ndarray:
    """Sketch stage: part silhouettes and proportion lines on white."""
    canvas = pk.Canvas(portrait.cv.width, portrait.cv.height, "#ffffff")
    layer = canvas.layer("guide")
    tones = {"hair_back": "#d9dde6", "body": "#f1e4dc", "cloth": "#e3e6ea", "face": "#f7ebe4",
             "hair_front": "#c5cad6"}
    for key, tone in tones.items():
        mask = portrait.masks[key]
        layer.paint(mask, tone)
        layer.paint(lt.outline_mask(mask, 2.0), "#6a7080")
    for y in (an.CROWN_Y, an.BROW_Y, 0.0, an.NOSE_Y, an.MOUTH_Y, an.CHIN_Y):
        line = portrait.head.to([[-0.40, y], [0.40, y]])
        layer.paint(pk.stroke_mask(canvas.shape, (line, 1.6)), "#d0584a")
    axis = portrait.head.to([[0.0, an.CROWN_Y - 0.05], [0.0, an.CHIN_Y + 0.05]])
    layer.paint(pk.stroke_mask(canvas.shape, (axis, 1.6)), "#d0584a")
    if isinstance(portrait, fg.Figure):
        for bone in portrait.skeleton_lines():
            layer.paint(pk.stroke_mask(canvas.shape, (bone, 2.4)), "#2f6fb0")
    return canvas.flatten()
