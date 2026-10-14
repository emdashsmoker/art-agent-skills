"""Default scene specification.

Why: a user (or a language model) should be able to request a picture by
overriding a few fields. Every tunable lives here so no rig file hides magic
numbers that change the look.
"""
import copy

DEFAULT_SPEC = {
    "canvas": {"width": 1024, "height": 1280, "seed": 7},
    "subject": "portrait",            # portrait | figure study | still_life | cityscape | landscape
    "style": "anime",                 # anime | illustration | oil | watercolor
    "look": "none",                   # color grade over the finished image: none | doomer
    "framing": "bust",                # bust | upper_body | full_body | wide (a small full figure in its setting)
    "light": {
        "direction": [-0.55, -0.65, 0.55],   # screen x right, y down, z toward viewer; points to the light
        "cast_distance": 0.032,              # cast shadow offset in head widths
        "rim_color": "#BFD4FF",
        "rim_strength": 0.55,
    },
    "palette": {
        "skin": "#F4DED3",
        "blush": "#EC9C9C",
        "lips": "#C9727A",
        "hair": "#2A2E3B",
        "hair_highlight": "#6F7DA3",
        "eye": "#C98B3B",
        "sclera": "#F6F4F6",
        "lash": "#17161D",
        "cloth": "#2E3038",
        "skirt": "#A8825F",
        "belt": "#1F1E24",
        "shoe": "#1F1E24",
        "metal": "#D9B46A",
        "shirt": "#F1F0F4",
        "tie": "#5B2A3A",
        "accent": "#E8E4EC",
        "sole": "#F2F0F2",
        "drape": "#8E3B46",
        "chair": "#7A5C4A",
        "hat": "#3A3F48",
        "background": ["#8796AC", "#DCE1E8"],
        "background_glow": "#F3E7DA",
    },
    "cel_threshold": {                # raw lambert value below which a cel shadow starts, per material
        "skin": -0.30, "body": -0.05, "hair": 0.15, "cloth": 0.20, "skirt": 0.20, "default": 0.10,
    },
    "shadow_tint": {                  # multiply colors of the shadow layer per material group
        "skin": "#E3A9A6",
        "body": "#E3A9A6",
        "lips": "#C98C96",
        "hair": "#6E6F98",
        "cloth": "#77789A",
        "eye_white": "#B9BDD6",
        "iris": "#9A8FB4",
        "metal": "#A88A6A",
        "skirt": "#B79A9A",
        "shoe": "#7A7898",
        "leather": "#7A7898",
        "glass": "#7088A8",
        "ceramic": "#A9A3C6",
        "fruit": "#A0708E",
        "lemon": "#C9A07A",
        "wood": "#8E6C78",
        "foliage": "#6E6A9C",
        "default": "#B4B2CA",
    },
    "character": {
        "sex": "female",                 # female | male (build, face and hair presets: SEX_PRESETS)
        "build": "standard",             # body type: female standard|slender|fuller|athletic, male standard|slim|athletic
        "scale": None,                   # group pictures: drawn size relative to the others (None: men 1.06 beside women)
        "head": {"x": 0.50, "y": None, "size": None, "yaw": 0.22, "roll": -0.05},  # None = from framing
        "face": {"cheek": 0.485, "jaw_width": 0.385, "jaw_height": 0.44, "chin_length": 0.70,
                 "chin_width": 0.04, "jaw_sharpness": 0.85},
        "eyes": {"size": 1.1, "openness": 0.92, "tilt": 0.10, "spacing": 0.205, "height": 0.13,
                 "gaze": [-0.15, 0.0], "lash_weight": 1.0},
        "brows": {"angle": 0.4, "thickness": 0.9, "height": 0.0, "see_through": 0.35},
        "mouth": {"smile": 0.25, "width": 1.15, "lip_strength": 0.65},
        "blush": 0.30,
        "hair": {"style": "long", "length": 2.3, "volume": 0.06, "bangs": "swept", "bang_count": 8, "bang_length": 0.10,
                 "part": -0.14, "tuck": "near", "side_length": 1.75, "seed": 3},
        "outfit": {"type": "turtleneck_sleeveless", "shoulder_width": 0.93,
                   "skirt_length": 6.2, "skirt_flare": 1.15, "earrings": "drop",
                   "hat": "none",                # none | beanie (palette 'hat')
                   "shoes": None},               # None: the outfit's own | pumps | sneakers | oxfords | none
        "pose": {"preset": "relaxed", "turn": 0.0, "look": "auto", "custom": None},   # turn: name or radians
        "expression": "default",         # default (the face fields as given) | EXPRESSIONS
        "face_preset": "default",        # default | FACE_PRESETS (soft, sharp, mature, gentle, cool, bold)
    },
    "figure_study": {"pose": "venus", "hair": None},   # pose: back_three_quarter | venus | reclining | seated
    "characters": [],                 # group picture: 2-3 character dicts (each like "character", plus "palette")
    "layout": {"type": "side_by_side", "interaction": "none", "gap": None},   # side_by_side | facing | front_back;
                                                                           # none | hold_hands; gap in head widths
    "scene": {"time": "dusk",         # landscape / cityscape: dusk | day | golden | blue_night | rain_night | snow_night
              "site": None,           # cityscape: street | panel; landscape: lake | outskirts (None: the first)
              "set": "classic",       # still_life: classic | desk | cafe | gaming | kitchen
              "palette": {}},         # color overrides for still_life / cityscape / landscape (see scene modules)
    "background": {"type": "glow", "scene": "cityscape"},   # flat | gradient | glow | scene (scene: cityscape | landscape)
    "line": {"weight": 1.0},
}


# head width and head-center height as fractions of the canvas, per framing
FRAMINGS = ("bust", "upper_body", "full_body", "wide")
FRAMING_TOP = -0.62          # top of the hair in head widths (head center = 0)
FRAMING_EXTENT = {"upper_body": 5.0, "full_body": 8.9}   # visible body length in head widths
SEATED_EXTENT = 6.95         # a seated full figure: head top to the raised floor
FRAMING_MARGIN = 0.05        # top margin as a fraction of canvas height
BUST_HEAD_SIZE, BUST_HEAD_Y = 0.32, 0.30   # bust crops the body, so head size and headroom are fixed
WIDE_FIGURE, WIDE_GROUND = 0.34, 0.90       # wide shot: figure height and feet line as fractions of the canvas


def framing_head(framing, width, height, seated=False):
    """Head size and vertical position so the requested body range fits the canvas."""
    if framing not in FRAMINGS:
        raise ValueError(f"unknown framing '{framing}' (use {', '.join(FRAMINGS)})")
    if framing == "bust":
        return BUST_HEAD_SIZE, BUST_HEAD_Y
    if framing == "wide":                   # an establishing shot: the setting dominates, the figure stands small
        extent = SEATED_EXTENT if seated else FRAMING_EXTENT["full_body"]
        unit = WIDE_FIGURE * height / (extent - FRAMING_TOP)
        return unit / width, WIDE_GROUND - extent * unit / height
    margin = FRAMING_MARGIN * height
    extent = SEATED_EXTENT if seated and framing == "full_body" else FRAMING_EXTENT[framing]
    unit = (height - 2 * margin) / (extent - FRAMING_TOP)
    y = margin + (-FRAMING_TOP) * unit
    return unit / width, y / height


FREE_FORM = ("scene.palette.", "shadow_tint.", "cel_threshold.")   # maps whose keys the consumers define

# Default colors per outfit (cloth = top, skirt = bottom); a spec's own palette entries win.
OUTFIT_PALETTES = {
    "bikini": {"cloth": "#2F4A6E"},
    "innerwear": {"cloth": "#2A2230", "accent": "#B98FA5"},
    "crop_hotpants": {"cloth": "#F1EEF0", "skirt": "#7E9CC2", "shoe": "#F2F0F2", "sole": "#D9D6DC"},
    "tee_jeans": {"cloth": "#F1EEF0", "skirt": "#4C6A93", "shoe": "#2B2D35", "sole": "#F2F0F2"},
    "suit": {"cloth": "#2F3138", "shirt": "#F1F0F4", "tie": "#5B2A3A", "belt": "#1F1E24", "shoe": "#1F1E24"},
    "swim_trunks": {"skirt": "#2E5A7A", "accent": "#F1EEF0"},
    "hoodie_joggers": {"cloth": "#9AA0AE", "skirt": "#2B2D35", "accent": "#F1EEF0", "shoe": "#F2F0F2",
                       "sole": "#D9D6DC"},
    "shirt_slacks": {"shirt": "#D3DEEC", "skirt": "#3A3E48", "belt": "#2A2420", "shoe": "#2A2420"},
    "knit_coat": {"shirt": "#E7DFD2", "cloth": "#8A6F58", "skirt": "#34363E", "shoe": "#2A2420", "metal": "#C9A86A"},
    "polo_shorts": {"cloth": "#2F4E6F", "skirt": "#C9B796", "shoe": "#F2F0F2", "sole": "#D9D6DC"},
    "tank_shorts": {"cloth": "#E9ECEF", "skirt": "#2B2F3A", "accent": "#E46A4E", "shoe": "#F2F0F2", "sole": "#D9D6DC"},
    "denim_jacket": {"shirt": "#F1EEF0", "cloth": "#5E7FA8", "skirt": "#2F3D55", "metal": "#C9A86A", "shoe": "#2B2D35",
                     "sole": "#F2F0F2"},
    "track_suit": {"cloth": "#2F3E5C", "accent": "#F1EEF0", "shoe": "#F2F0F2", "sole": "#D9D6DC"},
}


# Presets applied when a spec picks a sex; the spec's own fields still win. A chic adult man:
# smaller narrower eyes, light lashes, heavier straight brows, a longer squarer jaw, short hair.
SEX_PRESETS = {
    "female": {},
    "male": {
        "character": {
            "face": {"cheek": 0.475, "jaw_width": 0.41, "jaw_height": 0.47, "chin_length": 0.73,
                     "chin_width": 0.10, "jaw_sharpness": 0.9},
            "eyes": {"size": 0.88, "openness": 0.78, "tilt": 0.05, "spacing": 0.21, "height": 0.12,
                     "lash_weight": 0.35},
            "brows": {"angle": 0.18, "thickness": 1.45, "height": -0.035, "see_through": 0.2},
            "mouth": {"smile": 0.12, "width": 1.0, "lip_strength": 0.18},
            "blush": 0.0,
            "hair": {"style": "short", "length": 0.6, "volume": 0.08, "bangs": "swept", "bang_count": 7,
                     "bang_length": 0.02, "part": -0.16, "tuck": "none", "side_length": 0.35},
            "outfit": {"type": "tee_jeans", "earrings": "none"},
        },
        "palette": {"lips": "#D19A94"},
        "figure_study": {"hair": "short"},
    },
}


# Expression presets: changes on top of the face fields (a sex preset's own eyes and brows stay its
# own). 'key*' multiplies, 'key+' adds, a plain key sets. Mouth 'open' draws an open mouth; eyes
# 'shape' closed draws the arched happy eye.
EXPRESSIONS = {
    "smile": {"mouth": {"smile": 1.1}, "eyes": {"openness*": 0.88}, "brows": {"height+": -0.01}},
    "laugh": {"mouth": {"smile": 0.9, "open": 0.8}, "eyes": {"shape": "closed"}, "brows": {"height+": -0.025, "angle": 0.1},
              "blush+": 0.12},
    "neutral": {"mouth": {"smile": 0.04}, "brows": {"angle": 0.25}},
    "surprised": {"mouth": {"smile": 0.0, "open": 0.55}, "eyes": {"openness*": 1.12}, "brows": {"height+": -0.05,
                                                                                                    "angle": -0.2}},
    "serious": {"mouth": {"smile": -0.30}, "eyes": {"openness*": 0.86}, "brows": {"height+": 0.015, "angle": 0.75}},
    "sad": {"mouth": {"smile": -0.75}, "eyes": {"openness*": 0.82, "gaze": [-0.10, 0.35]}, "brows": {"angle": -0.55,
                                                                                                    "height+": -0.012}},
}


# Face presets: adult face types as changes on top of the sex preset (same syntax as EXPRESSIONS).
# Results stay inside FACE_LIMITS, the adult face ranges of the figure study (rig_figure_study.ADULT_FACE).
FACE_PRESETS = {
    "soft": {"face": {"jaw_sharpness+": -0.15, "cheek+": 0.012, "jaw_width+": 0.008}, "eyes": {"tilt+": -0.04,
                                                                                               "openness*": 1.03},
             "brows": {"angle+": -0.10, "thickness*": 0.9}},
    "sharp": {"face": {"jaw_sharpness+": 0.10, "jaw_width+": -0.012, "chin_length+": 0.02},
              "eyes": {"tilt+": 0.07, "openness*": 0.86}, "brows": {"angle+": 0.15}},
    "mature": {"face": {"chin_length+": 0.04, "jaw_height+": 0.02, "jaw_sharpness+": 0.05},
               "eyes": {"size*": 0.92, "openness*": 0.90}, "brows": {"height+": 0.01, "thickness*": 1.12},
               "blush*": 0.5},
    "gentle": {"face": {"jaw_sharpness+": -0.08}, "eyes": {"tilt+": -0.10},
               "brows": {"angle+": -0.20, "thickness*": 0.95}, "mouth": {"smile+": 0.05}},
    "cool": {"eyes": {"tilt+": 0.06, "openness*": 0.82}, "brows": {"angle+": -0.12, "height+": 0.02, "thickness*": 1.15},
             "mouth": {"width*": 0.9, "smile+": -0.08}, "blush*": 0.4},
    "bold": {"face": {"jaw_sharpness+": 0.05, "cheek+": -0.008}, "eyes": {"lash_weight*": 1.5},
             "brows": {"thickness*": 1.3}, "mouth": {"lip_strength*": 1.25, "width*": 1.06}},
}
FACE_LIMITS = {("eyes", "size"): (0.85, 1.10), ("eyes", "openness"): (0.70, 0.95),
               ("face", "chin_length"): (0.68, 0.76), ("face", "jaw_width"): (0.36, 0.42), ("blush",): (0.0, 0.35)}


def _apply_changes(out, table):
    for part, changes in table.items():
        if not isinstance(changes, dict):                 # top-level number (blush+ / blush*)
            key = part.rstrip("+*")
            out[key] = out[key] + changes if part.endswith("+") else (out[key] * changes if part.endswith("*")
                                                                         else changes)
            continue
        for key, value in changes.items():
            field = key.rstrip("+*")
            if key.endswith("*"):
                out[part][field] = out[part][field] * value
            elif key.endswith("+"):
                out[part][field] = out[part][field] + value
            else:
                out[part][field] = copy.deepcopy(value)
    return out


def apply_face_preset(character):
    """character fields with the face preset applied (a copy), kept inside the adult ranges."""
    name = character.get("face_preset", "default")
    if name == "default":
        return character
    if name not in FACE_PRESETS:
        raise ValueError(f"unknown face_preset '{name}' (use default, {', '.join(FACE_PRESETS)})")
    out = _apply_changes(copy.deepcopy(character), FACE_PRESETS[name])
    for path, (lo, hi) in FACE_LIMITS.items():
        node = out
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = min(max(node[path[-1]], lo), hi)
    return out


def apply_expression(character):
    """character fields with the expression preset applied (a copy); 'default' leaves them as given."""
    name = character.get("expression", "default")
    if name == "default":
        return character
    if name not in EXPRESSIONS:
        raise ValueError(f"unknown expression '{name}' (use default, {', '.join(EXPRESSIONS)})")
    return _apply_changes(copy.deepcopy(character), EXPRESSIONS[name])


def preset_defaults(user):
    """Defaults for the sex and outfit a user spec asks for (applied under the spec's own fields)."""
    ch = (user or {}).get("character", {}) or {}
    sex = ch.get("sex", DEFAULT_SPEC["character"]["sex"])
    if sex not in SEX_PRESETS:
        raise ValueError(f"unknown character.sex '{sex}' (use {', '.join(SEX_PRESETS)})")
    preset = SEX_PRESETS[sex]
    base_type = preset.get("character", {}).get("outfit", {}).get("type", DEFAULT_SPEC["character"]["outfit"]["type"])
    kind = (ch.get("outfit", {}) or {}).get("type", base_type)
    return deep_merge(preset, {"palette": OUTFIT_PALETTES.get(kind, {})})


def deep_merge(base, override, path="", warn=None):
    """Override defaults; unknown keys are reported because a typo would otherwise do nothing."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if key not in out and warn is not None and not path.startswith(FREE_FORM):
            warn(f"unknown spec key '{path}{key}' (ignored by the renderer)")
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value, f"{path}{key}.", warn)
        else:
            out[key] = copy.deepcopy(value)
    return out
