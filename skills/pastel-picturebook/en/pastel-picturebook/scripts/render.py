"""Command line entry: subject + style + spec -> staged PNG renders.

Usage
  python render.py --subject portrait --style anime --out out/picture.png
                   [--spec my_spec.json] [--extras my_props.py] [--stages out/stages]

Subjects
  portrait    bust portrait (default)
  figure      full or three-quarter figure, clothed or figure study
  hand        hand studies
  still_life  objects on a table
  landscape   mountains, water, trees, sky
  city        street in one-point perspective, by day or night
  desk        modern objects on a desk (monitor, laptop, keyboard, phone, mug, plant, lamp)
  cafe        a café interior at eye height (window on the street, counter, tables, pendant lamps)
  room        a living room at eye height (curtained window, sofa, bookcase, rug, lamp)
  beach       sky, the sea to the horizon, foam, wet and dry sand, palms

Scenes
  "backdrop"    another subject painted first as the background (city, landscape, desk, ...);
                "place": "horizon" puts every figure's eyes on its horizon
  "companions"  more figures (or portraits), painted after the backdrop and before the main subject
  "grade"       a colour cast laid over the figures so they sit in the backdrop's light
  "weather"     rain or snow over the finished scene; indoors only through the windows

Stages written with --stages
  1_sketch   construction drawing
  2_flat     base colours only
  3_shaded   light and shadow, no ink
  4_inked    ink lines added (same as 3 for lineless styles)
  final      --out, after the style's finishing pass
"""
import argparse
import copy
import importlib
import importlib.util
import json
from pathlib import Path

import numpy as np

import cv2

from expressions import apply_expression
from looks import apply_look
from weather import apply_weather
from finish import finish, focus_map
from raster import blur, mix, rgb, save

ASSETS = Path(__file__).resolve().parent.parent / "assets"
STYLES = ["anime", "illust", "paint", "watercolor", "pencil", "manga", "pixel", "doomer"]
# Subject name -> module with build(spec), paint(fig, style, seed, shade, lines, extras), sketch(fig).
SUBJECT_MODULES = {"portrait": "subject_portrait", "figure": "subject_figure", "hand": "subject_hand",
                   "still_life": "subject_still_life", "landscape": "subject_landscape", "city": "subject_city",
                   "desk": "subject_desk", "cafe": "interior", "room": "interior", "bedroom": "interior",
                   "bathroom": "interior", "beach": "subject_beach", "park": "subject_park", "sakura": "subject_park",
                   "rooftop": "subject_skyline", "fireworks": "subject_skyline", "panelka": "subject_blocks",
                   "outskirts": "subject_blocks"}
# Subjects that start from the portrait's character spec (head, face, hair).
CHARACTER_SUBJECTS = {"portrait", "figure"}
# Where each background subject keeps its horizon (share of the picture height).
HORIZON_KEYS = {"city": ("camera", "horizon_y"), "landscape": ("horizon_y",), "cafe": ("camera", "horizon_y"),
                "room": ("camera", "horizon_y"), "bedroom": ("camera", "horizon_y"), "bathroom": ("camera", "horizon_y"),
                "beach": ("horizon_y",), "park": ("camera", "horizon_y"), "sakura": ("camera", "horizon_y"),
                "rooftop": ("camera", "horizon_y"), "fireworks": ("camera", "horizon_y"), "panelka": ("camera", "horizon_y"),
                "outskirts": ("camera", "horizon_y")}
# Indoors the weather shows only through the windows (the interior paints it there).
INTERIORS = {"cafe", "room", "bedroom", "bathroom"}
# A softened backdrop gets this share of its own detail budget in the painterly finish.
SOFT_BACKDROP_FOCUS = 0.6


def deep_merge(base, override):
    """Recursively overlay `override` on a copy of `base`."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_style(style_name):
    """A style file; one with "base" is laid over its base style (it lists only what it changes)."""
    style = read_json(ASSETS / f"style_{style_name}.json")
    if style.get("base"):
        style = deep_merge(read_json(ASSETS / f"style_{style['base']}.json"), style)
    return style


def load_setup(style_name, spec_path, subject="portrait"):
    """Merge, lowest priority first: defaults, style file, subject file, sex preset, user spec.

    The subject file and the sex preset may hold "spec", "style" (all styles) and
    "style_<name>" (one style). The user spec may hold "sex" ("female" default,
    "male" loads assets/sex_male.json) and a "style" key that patches the style.
    """
    style = read_style(style_name)
    # A derived style (watercolor on illust, manga on anime) also takes the per-style presets of its base.
    variants = [style_name] + ([style["base"]] if style.get("base") else [])

    def styled(preset):
        for name in variants:
            if f"style_{name}" in preset:
                return preset[f"style_{name}"]
        return {}

    spec = {}
    if subject in CHARACTER_SUBJECTS:
        spec = deep_merge(read_json(ASSETS / "spec_default.json"), style.get("figure", {}))
        # Colours of the accessories (hat, scarf, bag), under everything a style or subject sets.
        style = deep_merge(read_json(ASSETS / "accessories.json"), style)
    subject_file = ASSETS / f"subject_{subject}.json"
    if subject_file.exists():
        preset = read_json(subject_file)
        spec = deep_merge(spec, preset.get("spec", {}))
        style = deep_merge(style, preset.get("style", {}))
        style = deep_merge(style, styled(preset))
    # The user part is a file path, or a dict when a scene nests one subject's spec inside another's.
    user = copy.deepcopy(spec_path) if isinstance(spec_path, dict) else (read_json(spec_path) if spec_path else {})
    sex = user.get("sex", spec.get("sex", "female"))
    sex_file = ASSETS / f"sex_{sex}.json"
    if sex_file.exists():
        # A sex preset changes proportions, hair and rendering defaults; its "subject_<name>" part
        # adds what only makes sense for one subject (clothes for a full figure, say).
        preset = read_json(sex_file)
        for part in (preset, preset.get(f"subject_{subject}", {})):
            if subject in CHARACTER_SUBJECTS or part is not preset:
                spec = deep_merge(spec, part.get("spec", {}))
            style = deep_merge(style, part.get("style", {}))
            style = deep_merge(style, styled(part))
    style = deep_merge(style, user.pop("style", {}))
    spec = deep_merge(spec, user)
    for side in ("left", "right"):
        # An arm given a reach is described by its own keys only: the preset arm's angles and
        # foreshortening (the default hand on the hip) would bend it out of shape.
        arm = user.get("figure", {}).get("pose", {}).get(f"arm_{side}")
        if isinstance(arm, dict) and "reach" in arm:
            spec["figure"]["pose"][f"arm_{side}"] = copy.deepcopy(arm)
    if subject in CHARACTER_SUBJECTS:
        apply_look(spec, style, user)
        apply_expression(spec, style)
    return spec, style


def load_extras(path):
    """Import a user props module by file path."""
    if not path:
        return None
    module_spec = importlib.util.spec_from_file_location("extras", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def output(image, mirror):
    """Flip the finished picture when the pose is mirrored."""
    return np.ascontiguousarray(image[:, ::-1]) if mirror else image


# ------------------------------------------------------------------ scenes
def horizon_of(subject_name, spec):
    """The backdrop's horizon (share of the height), or None for subjects without one."""
    keys = HORIZON_KEYS.get(subject_name)
    if keys is None:
        return None
    value = spec
    for key in keys:
        value = value[key]
    return float(value)


def place_on_horizon(spec, horizon):
    """Standing adults share the camera's eye height: their eyes sit on the horizon.

    `pose.horizon_drop` (share of the picture height) lowers one figure's eyes: a shorter person,
    a head leaning on a shoulder, someone seated.
    """
    if horizon is not None and "pose" in spec:
        spec["pose"]["head_center"] = [spec["pose"]["head_center"][0], horizon + spec["pose"].get("horizon_drop", 0.0)]


def soften(image, setup):
    """Push a backdrop back: optional blur (share of the width) and a fade toward a colour."""
    width = image.shape[1]
    if setup.get("blur", 0.0) > 0:
        image = blur(image, setup["blur"] * width)
    fade = setup.get("fade")
    if fade:
        image = mix(image, rgb(fade["color"]), fade["amount"])
    return np.clip(image, 0.0, 1.0).astype(np.float32)


def grade(image, focus, setup):
    """Tint the figure (where its detail map is above zero) with the scene's light colour."""
    if not setup or focus is None:
        return image
    figure = (focus > 0).astype(np.float32)
    figure = cv2.GaussianBlur(figure, (0, 0), 1.0)[..., None]
    tinted = image * mix(np.ones(3, np.float32), rgb(setup["color"]), setup["amount"])
    return (image + (tinted - image) * figure).astype(np.float32)


def detail_map(fig, subject_name):
    """The subject's detail map; a portrait builds its own from its shapes. It also marks where the figure is."""
    if fig.focus is not None:
        return fig.focus
    if subject_name in CHARACTER_SUBJECTS:
        return focus_map(fig)
    return np.zeros(fig.size, np.float32)


# A pixel counts as painted by a figure once it differs from the backdrop under it by this much (0-1 per channel).
DRAWN_STEP = 0.004


def paint_layer(subject_name, user_spec, style_name, backdrop=None, horizon=None, lifts=None):
    """Build and paint one subject over an optional backdrop layer, without the finishing pass.

    Returns (image, focus) in picture orientation (already flipped when mirrored). A figure whose
    spec names parts to `lift` adds (pixels, core, ring, focus, under_head) for them to `lifts`, to be laid on top of later
    figures: `core` is the parts themselves, `ring` the band just outside them where their outline lies.
    """
    module = importlib.import_module(SUBJECT_MODULES[subject_name])
    spec, style = load_setup(style_name, user_spec, subject_name)
    place_on_horizon(spec, horizon)
    fig = module.build(spec)
    mirror = spec.get("pose", {}).get("mirror", False)
    if backdrop is not None:
        fig.extra["backdrop"] = output(backdrop[0], mirror)
    image = module.paint(fig, style, spec["seed"])
    focus = detail_map(fig, subject_name)
    image = grade(image, focus, spec.get("grade"))
    if spec.get("lift") and lifts is not None:
        import anatomy_profile
        import subject_figure
        masker = anatomy_profile.lift_mask if "layout" in fig.extra else subject_figure.lift_mask
        core = masker(fig, spec["lift"], inked=False)
        mask = masker(fig, spec["lift"], inked=style["line_scale"] > 0)
        if backdrop is not None:
            # Only what the figure painted: a bone's tube can reach past its sleeve or hand into bare backdrop.
            drawn = (np.abs(image - fig.extra["backdrop"]).max(axis=2) > DRAWN_STEP).astype(np.float32)
            core, mask = core * drawn, mask * drawn
        ring = np.clip(mask - core, 0.0, 1.0)
        lifts.append((output(image, mirror), output(core, mirror), output(ring, mirror), output(focus, mirror),
                      bool(spec.get("lift_under_head"))))
    image, focus = output(image, mirror), output(focus, mirror)
    if backdrop is not None:
        focus = np.maximum(focus, backdrop[1])
    return image, focus


# ------------------------------------------------------------- contact
def scene_horizon(spec, style_name):
    """The backdrop's horizon when figures stand on it ("place": "horizon"), else None."""
    setup = spec.get("backdrop")
    if not setup or setup.get("place") != "horizon":
        return None
    back_user = copy.deepcopy(setup.get("spec", {}))
    back_user["canvas"] = dict(spec["canvas"])
    merged, _ = load_setup(style_name, back_user, setup["subject"])
    return horizon_of(setup["subject"], merged)


def arms_of(person):
    """The arm dicts of a figure spec (a merged spec or a companion's own part), keyed by side ("near" for a profile's arm)."""
    figure = person.get("figure", {})
    pose = figure.get("pose", {})
    arms = {side: pose[f"arm_{side}"] for side in ("left", "right") if isinstance(pose.get(f"arm_{side}"), dict)}
    near = (figure.get("profile_pose") or {}).get("arm")
    if isinstance(near, dict):
        arms["near"] = near
    return arms


def figure_marks(spec, subject_name):
    """Landmarks of a figure (front, back or side) as shares of the picture, its own partner reaches ignored."""
    spec = copy.deepcopy(spec)
    for arm in arms_of(spec).values():
        if isinstance(arm.get("reach"), dict) and "of" in arm["reach"]:
            arm.pop("reach")
    marks, _ = measure(spec, subject_name)
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    return {name: [float(point[0] / width), float(point[1] / height)] for name, point in marks.items()}


def link_reaches(spec, subject_name, style_name, horizon):
    """Turn every reach aimed at another figure ({"mark": ..., "of": "main" or a companion's index}) into a
    point on the picture ({"at": ...}), so each figure can be built alone.

    Why here: only the scene knows where the other figures stand. Each figure is built once more just
    to read its landmarks; nothing is painted.
    """
    people = [("main", spec)] + list(enumerate(spec.get("companions", [])))
    if not any(isinstance(arm.get("reach"), dict) and "of" in arm["reach"] for _, person in people for arm in arms_of(person).values()):
        return
    cache = {}

    def marks_of(key):
        if key not in cache:
            cache[key] = figure_marks(*person_spec(spec, key, subject_name, style_name, horizon))
        return cache[key]

    for _, person in people:
        for arm in arms_of(person).values():
            aim = arm.get("reach")
            if isinstance(aim, dict) and "of" in aim:
                arm["reach"] = {"at": marks_of(aim["of"])[aim["mark"]], "offset": aim.get("offset", [0.0, 0.0])}


# ---------------------------------------------------------------- props
# Seated at a café table, its top stands this far (head units) above the seat; a bench's backrest is on by default.
TABLE_ABOVE_SEAT = 3.4
# An elbow resting on a table: the joint's centre sits this far (head units) above the top.
ELBOW_ON_TABLE = 0.30


def person_spec(spec, key, subject_name, style_name, horizon):
    """Merged, placed spec and subject of the main figure ("main") or a companion (its index), for measuring."""
    if key == "main":
        merged = copy.deepcopy(spec)
    else:
        user = copy.deepcopy(spec["companions"][key])
        subject_name = user.pop("subject", "figure")
        user["canvas"] = dict(spec["canvas"])
        user.setdefault("light", spec.get("light"))
        merged, _ = load_setup(style_name, user, subject_name)
    place_on_horizon(merged, horizon)
    return merged, subject_name


def measure(merged, subject_name):
    """Landmarks (pixels, picture orientation) and body unit (pixels) of a built figure."""
    import anatomy_profile
    import subject_figure
    fig = importlib.import_module(SUBJECT_MODULES[subject_name]).build(merged)
    side = merged.get("figure", {}).get("view") == "side"
    marks = anatomy_profile.landmarks(fig) if side else subject_figure.landmarks(fig)
    unit = fig.extra["layout"]["unit"] if side else fig.extra["body"].unit
    if merged.get("pose", {}).get("mirror", False):
        marks = {name: np.array([fig.size[1] - point[0], point[1]]) for name, point in marks.items()}
    return marks, unit


def bench_geometry(prop, people):
    """A bench under every listed figure seated facing us: from its hips (back edge) to its knees (front edge)."""
    import props
    units = [unit for _, unit in people]
    unit = float(np.mean(units))
    hips = [marks[f"hip_{side}"] for marks, _ in people for side in ("left", "right")]
    knees = [marks[f"knee_{side}"] for marks, _ in people for side in ("left", "right")]
    ankles = [marks[f"ankle_{side}"] for marks, _ in people for side in ("left", "right")]
    overhang = prop.get("overhang", props.BENCH["overhang"]) * unit
    return {"kind": "bench", "unit": unit, "backrest": prop.get("backrest", True),
            "x0": min(point[0] for point in hips) - overhang, "x1": max(point[0] for point in hips) + overhang,
            "back_y": float(np.mean([point[1] for point in hips])) + props.BENCH["back"] * unit,
            "front_y": float(np.mean([point[1] for point in knees])) + props.BENCH["front"] * unit,
            "floor_front": max(point[1] for point in ankles) + props.BENCH["foot"] * unit}


def table_geometry(prop, people, width, leaning=None):
    """A café table between figures seated in profile: centred between their knees, its top above their seats.

    `leaning` (one figure's measure) puts the top under that figure's elbow instead: an elbow resting on it.
    """
    unit = float(np.mean([unit for _, unit in people]))
    seats = [marks.get("seat", marks["hip"])[1] for marks, _ in people]
    x = prop["x"] * width if "x" in prop else float(np.mean([marks["knee"][0] for marks, _ in people]))
    top = float(np.mean(seats)) - prop.get("above_seat", TABLE_ABOVE_SEAT) * unit
    if leaning is not None:
        top = float(leaning[0]["elbow"][1]) + ELBOW_ON_TABLE * leaning[1]
    cups = [x + offset * unit for offset in prop.get("cups", [])]
    return {"kind": "table", "unit": unit, "x": x, "top_y": top, "floor": max(marks["soles"][1] for marks, _ in people),
            "radius": prop.get("radius", 2.7), "cups": cups}


def resolve_props(spec, subject_name, style_name, horizon):
    """Measure the figures each scene prop serves and hand the props' geometry to the figure painted first.

    A prop is {"kind": "bench" | "table", "on": ["main", 0, ...]} ("on" defaults to every figure).
    """
    if not spec.get("props"):
        return
    keys = ["main"] + list(range(len(spec.get("companions", []))))
    width = spec["canvas"]["width"]
    measured = {}
    resolved = []
    for prop in spec["props"]:
        people = []
        for key in prop.get("on", keys):
            if key not in measured:
                measured[key] = measure(*person_spec(spec, key, subject_name, style_name, horizon))
            people.append(measured[key])
        if prop["kind"] == "bench":
            resolved.append(bench_geometry(prop, people))
            continue
        leaning = prop.get("elbow_of")
        if leaning is not None and leaning not in measured:
            measured[leaning] = measure(*person_spec(spec, leaning, subject_name, style_name, horizon))
        resolved.append(table_geometry(prop, people, width, None if leaning is None else measured[leaning]))
    first = spec["companions"][0] if spec.get("companions") else spec
    first["scene_props"] = resolved


# How far (px) the later figure's face and front hair reach past their fill when a lifted part passes under them,
# so their own outline stays whole.
HEAD_COVER_GROW = 2


def luminance(image):
    return image @ np.array([0.299, 0.587, 0.114], np.float32)


def head_cover(fig):
    """The face and front hair a painted front figure shows (its own orientation), zeros for other figures."""
    cover = fig.extra.get("head_cover") if hasattr(fig, "extra") else None
    if cover is None:
        return np.zeros(fig.size, np.float32)
    grown = cv2.dilate((cover > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=HEAD_COVER_GROW)
    return np.maximum(cover, grown).astype(np.float32)


def lay_lifts(image, focus, lifts, mirror, head=None):
    """Paint lifted parts of earlier figures back on top (they come in picture orientation).

    A part lifted "under the head" (an arm around the shoulders) stays behind the later figure's face and front hair (`head`).
    In the ring round a part only its outline comes along: a ring pixel is laid where it is darker than what lies
    there, so the earlier figure's own backdrop never shows as a pale halo.
    """
    for pixels, core, ring, part_focus, under_head in lifts:
        pixels, core, ring, part_focus = (output(layer, mirror) for layer in (pixels, core, ring, part_focus))
        if under_head and head is not None:
            core, ring = core * (1.0 - head), ring * (1.0 - head)
        image = (image + (pixels - image) * core[..., None]).astype(np.float32)
        darker = (luminance(pixels) < luminance(image)).astype(np.float32)
        image = (image + (pixels - image) * (ring * darker)[..., None]).astype(np.float32)
        if focus is not None:
            focus = np.where(core > 0.5, part_focus, focus).astype(np.float32)
    return image, focus


def scene_behind(spec, style_name, lifts=None):
    """Paint the backdrop and companions of a scene. Returns ((image, focus) or None, horizon)."""
    layer, horizon = None, None
    canvas = spec.get("canvas")
    setup = spec.get("backdrop")
    if setup:
        back_user = copy.deepcopy(setup.get("spec", {}))
        back_user["canvas"] = dict(canvas)
        back_user.setdefault("light", spec.get("light"))
        if setup["subject"] in INTERIORS and spec.get("weather"):
            back_user.setdefault("weather", spec["weather"])
        merged, _ = load_setup(style_name, back_user, setup["subject"])
        if setup.get("place") == "horizon":
            horizon = horizon_of(setup["subject"], merged)
        image, focus = paint_layer(setup["subject"], back_user, style_name)
        softened = setup.get("blur", 0.0) > 0 or setup.get("fade")
        layer = (soften(image, setup), focus * (SOFT_BACKDROP_FOCUS if softened else 1.0))
    for companion in spec.get("companions", []):
        user = copy.deepcopy(companion)
        subject_name = user.pop("subject", "figure")
        user["canvas"] = dict(canvas)
        user.setdefault("light", spec.get("light"))
        layer = paint_layer(subject_name, user, style_name, layer, horizon, lifts)
    return layer, horizon


def main():
    parser = argparse.ArgumentParser(description="Render a code-drawn picture.")
    parser.add_argument("--subject", default="portrait", choices=sorted(SUBJECT_MODULES))
    parser.add_argument("--style", default="anime", choices=STYLES)
    parser.add_argument("--spec", default=None, help="JSON with overrides of the subject's default spec")
    parser.add_argument("--extras", default=None, help="Python file with after_background/after_figure hooks")
    parser.add_argument("--out", required=True)
    parser.add_argument("--stages", default=None, help="folder for per-stage images")
    args = parser.parse_args()

    subject = importlib.import_module(SUBJECT_MODULES[args.subject])
    spec, style = load_setup(args.style, args.spec, args.subject)
    extras = load_extras(args.extras)
    if args.subject in CHARACTER_SUBJECTS:
        link_reaches(spec, args.subject, args.style, scene_horizon(spec, args.style))
        resolve_props(spec, args.subject, args.style, scene_horizon(spec, args.style))
    lifts = []
    behind, horizon = scene_behind(spec, args.style, lifts)
    place_on_horizon(spec, horizon)
    fig = subject.build(spec)
    seed = spec["seed"]
    mirror = spec.get("pose", {}).get("mirror", False)
    if behind is not None:
        fig.extra["backdrop"] = output(behind[0], mirror)
    image = subject.paint(fig, style, seed, extras=extras)
    if behind is not None or spec.get("grade"):
        focus = detail_map(fig, args.subject)
        image = grade(image, focus, spec.get("grade"))
        if behind is not None:
            fig.focus = np.maximum(focus, output(behind[1], mirror))
    if lifts:
        # Parts of earlier figures that lie in front of later ones (a hand on the partner's far shoulder).
        image, fig.focus = lay_lifts(image, detail_map(fig, args.subject), lifts, mirror, head_cover(fig))
    backdrop_subject = (spec.get("backdrop") or {}).get("subject")
    if spec.get("weather") and args.subject not in INTERIORS and backdrop_subject not in INTERIORS:
        # Outdoors the rain or snow falls in front of everything, figures included.
        image = apply_weather(image, spec["weather"], seed, shelter=fig.extra.get("shelter"))
    if args.stages:
        stage_dir = Path(args.stages)
        stage_dir.mkdir(parents=True, exist_ok=True)
        stages = {"1_sketch": subject.sketch(fig),
                  "2_flat": subject.paint(fig, style, seed, shade=False, lines=False, extras=extras),
                  "3_shaded": subject.paint(fig, style, seed, shade=True, lines=False, extras=extras),
                  "4_inked": image}
        prefix = f"{args.subject}_{args.style}"
        for name, stage in stages.items():
            save(stage_dir / f"{prefix}_{name}.png", output(stage, mirror))
    image = finish(image, fig, style, seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    save(args.out, output(image, mirror))
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
