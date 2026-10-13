"""Scene spec: defaults, merge, validation.

The spec is the contract between whoever plans the picture (a person or an
LLM) and the engine. Every field has a default, so a spec may be as short as
{"style": "watercolor"}. Unknown enum values fail loudly with the allowed set.
"""
import copy
import json

LIGHTS = {
    "upper_left": (-0.55, -0.62, 0.56),
    "upper_right": (0.55, -0.62, 0.56),
    "front": (0.0, -0.35, 0.94),
    "side_left": (-0.90, -0.25, 0.35),
    "side_right": (0.90, -0.25, 0.35),
}

ENUMS = {
    "subject": ("character", "still_life", "landscape", "city", "interior"),
    "interior.room": ("bedroom", "office", "cafe", "pool", "gym"),
    "framing": ("closeup", "bust", "waist", "full", "wide"),
    "style": ("anime_cel", "soft_illust", "painterly", "watercolor"),
    "quality": ("draft", "final"),
    "character.gender": ("female", "male"),
    "character.view": ("front", "back", "side"),
    "character.facing": ("right", "left"),
    "character.face_shape": ("oval", "round", "sharp", "square"),
    "character.face.nose": ("small", "button", "defined"),
    "character.face.lips": ("thin", "natural", "full"),
    "character.eyes.lashes": ("none", "light", "normal", "heavy"),
    "character.body.bust": ("small", "medium", "large", "xlarge"),
    "character.eyes.shape": ("almond", "round", "droopy", "sharp"),
    "character.expression.mouth": ("smile", "neutral", "soft", "pout", "open_smile", "open"),
    "character.expression.brows": ("soft", "straight", "raised", "sharp"),
    "character.hair.style": ("long", "bob", "ponytail", "short"),
    "character.hair.bangs": ("full", "side_swept", "parted"),
    "character.hair.ears": ("hidden", "visible"),
    "character.outfit.type": ("knit_sweater", "shirt", "offshoulder_dress", "hoodie", "crop_top", "bikini",
                              "one_piece", "rash_guard", "beach_shirt", "tank_top", "shirtless", "sports_bra",
                              "camisole", "slip_dress", "halter_dress", "tee", "oversized_tee"),
    "character.outfit.variant": ("turtleneck", "crew", "tank", "tee", "triangle", "bandeau", "classic", "cutout",
                                 "plain", "print", "tie", "bow"),
    "character.outfit.bottom": ("a_line_skirt", "jeans", "bikini", "board_shorts", "swim_briefs", "boxer_briefs",
                                "leggings", "joggers", "slacks", "pencil_skirt", "dolphin_shorts"),
    "character.outfit.bottom_style": ("classic", "high_leg", "string"),
    "character.outfit.shoes": ("sneakers", "boots", "sandals", "barefoot", "heels", "dress_shoes"),
    "post.grade": ("neutral", "warm", "cool", "sunset", "doomer"),
    "mood": ("none", "doomer"),
    "character.body.hold.item": ("phone", "can", "cigarette"),
    "character.body.hold.side": ("right", "left"),
    "character.body.pose": ("relaxed", "close", "behind", "pocket", "wave", "hand_on_hip", "hands_on_hips",
                            "arms_crossed", "chin_rest", "hair_tuck", "hands_behind_head",
                            "walk", "lean", "sit", "lie"),
    "character.body.seat": ("chair", "stool", "bed"),
    "character.body.stance": ("straight", "contrapposto", "wide", "walk", "lean", "sit", "lie"),
    "character.body.figure": ("slim", "balanced", "curvy", "athletic"),
    "character.body.hands.right": ("open", "relaxed", "flat", "fist", "point", "peace"),
    "character.body.hands.left": ("open", "relaxed", "flat", "fist", "point", "peace"),
    "background.type": ("plain", "gradient", "sky", "bokeh", "window", "beach", "landscape", "city",
                        "bedroom", "office", "cafe", "pool", "gym", "bed"),
    "background.landscape.time": ("day", "sunset", "misty", "night"),
    "background.city.time": ("day", "dusk", "night"),
    "landscape.time": ("day", "sunset", "misty", "night"),
    "city.time": ("day", "dusk", "night"),
    "pair.contact": ("none", "hand_hold", "shoulder_arm"),
}

DEFAULT_SPEC = {
    "subject": "character",
    "canvas": {"width": 1024, "height": 1280, "seed": 7},
    "quality": "final",
    "framing": "bust",
    "style": "anime_cel",
    "character": {
        "gender": "female",
        "skin": "#F9E2D2",
        "face_shape": "oval",
        "face": {"length": 1.0, "nose": "small", "lips": "natural"},
        "head_scale": 1.0,
        "head": {"yaw": 15, "pitch": 0, "roll": -3},
        "body": {"yaw": 0, "roll": 0, "pose": "relaxed", "stance": "straight", "figure": "balanced", "bust": "medium",
                 "hands": {}},
        "eyes": {"color": "#4F7DB8", "shape": "almond", "size": 1.0, "openness": 1.0, "tilt": 3,
                 "gaze": "viewer", "iris": 1.0, "lashes": "normal", "crease": True},
        "expression": {"mouth": "smile", "blush": 0.35, "brows": "soft", "eye_smile": 0.0, "brow_weight": 1.0},
        "hair": {"color": "#5A3C38", "style": "long", "bangs": "side_swept", "wave": 0.0, "volume": 1.0,
                 "ears": "hidden"},
        "outfit": {"type": "knit_sweater"},
        "accessories": [],
    },
    "lighting": {"key": "upper_left", "rim_color": "#FFE2B8", "rim_strength": 0.55},
    "background": {"type": "gradient"},
    "post": {},
}


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _get(d, dotted):
    for part in dotted.split("."):
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    return d


def _character_errors(ch, label):
    """Enum, outfit and angle checks of one character; label names it in messages."""
    errors = []
    for key, allowed in ENUMS.items():
        if not key.startswith("character."):
            continue
        v = _get({"character": ch}, key)
        if v is not None and v not in allowed:
            errors.append(f"{label}{key[len('character'):]}={v!r} (allowed: {', '.join(allowed)})")
    kind = ch["outfit"].get("type")
    if ch.get("gender") == "male" and kind in FEMALE_ONLY_OUTFITS:
        errors.append(f"{label}.outfit.type={kind!r} is not available for male characters")
    if ch.get("gender") != "male" and kind in MALE_ONLY_OUTFITS:
        errors.append(f"{label}.outfit.type={kind!r} is only available for male characters")
    if ch.get("gender") == "male" and ch["outfit"].get("bottom") in FEMALE_ONLY_BOTTOMS:
        errors.append(f"{label}.outfit.bottom={ch['outfit']['bottom']!r} is not available for male characters")
    if abs(float(ch["head"]["yaw"])) > 40:
        errors.append(f"{label}.head.yaw must be within [-40, 40] degrees")
    muscle = ch["body"].get("muscle")
    if muscle is not None and not (isinstance(muscle, (int, float)) and 0 <= muscle <= 1):
        errors.append(f"{label}.body.muscle must be a number within [0, 1] (got {muscle!r})")
    return errors


def _pair_errors(spec):
    """Group limits: count, framing, poses and contact preconditions (contacts are two-figure only)."""
    chars = spec["characters"]
    if len(chars) < 2:
        return [f"characters must hold 2 or more entries (got {len(chars)}); use character for one figure"]
    errors = []
    if spec["framing"] not in PAIR_FRAMINGS:
        errors.append(f"framing={spec['framing']!r} with characters (allowed: {', '.join(PAIR_FRAMINGS)})")
    for i, ch in enumerate(chars):
        if ch["body"].get("pose") == "lie":
            errors.append(f"characters[{i}].body.pose='lie' is single-figure only")
    rows = spec.get("pair", {}).get("rows", 1)
    if not isinstance(rows, int) or not 1 <= rows <= len(chars):
        errors.append(f"pair.rows must be an integer within [1, {len(chars)}] (got {rows!r})")
        rows = 1
    contact = spec.get("pair", {}).get("contact", "none")
    if contact in CONTACT_VIEWS and rows > 1:
        errors.append(f"pair.contact={contact!r} needs one row (pair.rows=1)")
    elif contact in CONTACT_VIEWS and len(chars) != 2:
        errors.append(f"pair.contact={contact!r} needs exactly 2 characters (got {len(chars)}); "
                      "use contact 'none' for groups")
    elif contact in CONTACT_VIEWS:        # an unknown contact is already reported by the enum check
        for i, ch in enumerate(chars):
            if ch.get("view", "front") not in CONTACT_VIEWS[contact]:
                errors.append(f"pair.contact={contact!r} needs view in {CONTACT_VIEWS[contact]} "
                              f"(characters[{i}].view={ch.get('view', 'front')!r})")
            if ch["body"].get("pose") in CONTACT_BLOCKED_POSES:
                errors.append(f"pair.contact={contact!r} cannot use characters[{i}].body.pose="
                              f"{ch['body']['pose']!r} (both arms are posed)")
        lead = spec.get("pair", {}).get("lead", 0)
        if lead not in (0, 1):
            errors.append(f"pair.lead must be 0 or 1 (got {lead!r})")
    return errors


def validate(spec):
    errors = []
    for key, allowed in ENUMS.items():
        if key.startswith("character."):
            continue
        v = _get(spec, key)
        if v is not None and v not in allowed:
            errors.append(f"{key}={v!r} (allowed: {', '.join(allowed)})")
    if "characters" in spec:
        for i, ch in enumerate(spec["characters"]):
            errors += _character_errors(ch, f"characters[{i}]")
        errors += _pair_errors(spec)
    else:
        errors += _character_errors(spec["character"], "character")
    key = spec["lighting"].get("key")
    if isinstance(key, str) and key not in LIGHTS:
        errors.append(f"lighting.key={key!r} (allowed: {', '.join(LIGHTS)} or [x, y, z])")
    w, h = spec["canvas"]["width"], spec["canvas"]["height"]
    if not (256 <= w <= MAX_SIDE and 256 <= h <= MAX_SIDE):
        errors.append(f"canvas width/height must be within [256, {MAX_SIDE}]")
    if errors:
        raise ValueError("invalid spec:\n  " + "\n  ".join(errors))
    return spec


# male defaults layered between DEFAULT_SPEC and the user's spec (user values still win)
MALE_PRESET = {"character": {
    "skin": "#F3D6C2", "face_shape": "square", "face": {"length": 1.10, "nose": "defined", "lips": "thin"},
    "eyes": {"shape": "sharp", "size": 0.96, "openness": 0.82, "tilt": 1, "iris": 0.92, "lashes": "none",
             "color": "#4A5A6E"},
    "expression": {"mouth": "neutral", "blush": 0.0, "brows": "straight", "brow_weight": 2.3, "brow_lift": -0.12},
    "hair": {"style": "short", "bangs": "side_swept", "color": "#3A3234", "ears": "visible", "volume": 0.9},
    "body": {"figure": "balanced"}, "outfit": {"type": "shirt"}}}
FEMALE_ONLY_OUTFITS = ("offshoulder_dress", "crop_top", "bikini", "one_piece", "sports_bra", "camisole",
                       "slip_dress", "halter_dress")
MALE_ONLY_OUTFITS = ("shirtless",)
FEMALE_ONLY_BOTTOMS = ("bikini", "pencil_skirt", "dolphin_shorts")
FULL_CANVAS = {"width": 960, "height": 1600}   # a standing figure needs a taller frame
LIE_CANVAS = {"width": 1600, "height": 1000}   # a lying figure is laid along the width
WIDE_CANVAS = {"width": 1600, "height": 1000}  # an establishing shot reads wide
SCENE_CANVAS = {"width": 1280, "height": 960}  # still lifes, landscapes and streets read wider


PAIR_FRAMINGS = ("waist", "full", "wide")
PAIR_CANVAS = {"waist": {"width": 1360, "height": 1024}, "full": {"width": 1280, "height": 1600},
               "wide": {"width": 1600, "height": 1000}}
GROUP_STEP = {"waist": 480, "full": 420, "wide": 120}   # default canvas widening per figure beyond two (px)
MAX_SIDE = 4096
CONTACT_VIEWS = {"hand_hold": ("front", "back"), "shoulder_arm": ("front",)}
CONTACT_BLOCKED_POSES = ("arms_crossed", "sit", "lie")


# moods: defaults layered under the user's spec (user values still win)
# doomer: the lonely late night; night streets with power lines, muted cold color, grain, tired eyes
MOODS = {
    "doomer": {
        "spec": {"post": {"grade": "doomer", "grade_amount": 1.0, "grain": 0.018, "vignette": 0.30, "light_wash": 0.0,
                          "vibrance": 0.0},
                 "city": {"time": "night", "wires": True}, "landscape": {"time": "night"}},
        "background": {"type": "city", "city": {"time": "night", "wires": True}},
        "character": {"eyes": {"openness": 0.80}, "expression": {"mouth": "neutral", "blush": 0.06, "eye_smile": 0.0,
                                                                  "brows": "soft"}},
    },
}


def _character(entry, mood=None):
    """One character: defaults, the male preset when asked, the mood's look, then the user's values."""
    base = DEFAULT_SPEC["character"]
    if (entry or {}).get("gender") == "male":
        base = deep_merge(base, MALE_PRESET["character"])
    if mood in MOODS:
        base = deep_merge(base, MOODS[mood]["character"])
    return deep_merge(base, entry or {})


def _normalize_pair(user_spec):
    """Two or more characters side by side: each entry is a full character with an optional place."""
    size_given = any(k in (user_spec.get("canvas") or {}) for k in ("width", "height"))
    framing = user_spec.get("framing", "waist")
    base = deep_merge(DEFAULT_SPEC, {"framing": framing, "pair": {"contact": "none", "lead": 0}})
    if not size_given and framing in PAIR_CANVAS:
        count = len(user_spec["characters"]) if isinstance(user_spec["characters"], list) else 0
        rows = (user_spec.get("pair") or {}).get("rows", 1)
        per_row = -(-count // rows) if isinstance(rows, int) and rows >= 1 else count   # widest (front) row
        extra = max(per_row - 2, 0)
        width = min(PAIR_CANVAS[framing]["width"] + extra * GROUP_STEP[framing], MAX_SIDE)
        base = deep_merge(base, {"canvas": dict(PAIR_CANVAS[framing], width=width)})
    mood = user_spec.get("mood")
    if mood in MOODS:
        base = deep_merge(base, MOODS[mood]["spec"])
        if "background" not in user_spec:
            base["background"] = MOODS[mood]["background"]
    rest = {k: v for k, v in user_spec.items() if k != "characters"}
    spec = deep_merge(base, rest)
    entries = user_spec["characters"]
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise ValueError("invalid spec:\n  characters must be a list of character objects")
    spec["characters"] = [_character(e, mood) for e in entries]
    # untouched head turns and profile directions are filled per side by the pair planner
    spec["_user_characters"] = copy.deepcopy(entries)
    if spec["characters"]:
        spec["character"] = spec["characters"][0]
    return validate(spec)


def normalize(user_spec):
    user_spec = user_spec or {}
    if "characters" in user_spec:
        return _normalize_pair(user_spec)
    base = DEFAULT_SPEC
    size_given = any(k in (user_spec.get("canvas") or {}) for k in ("width", "height"))
    if user_spec.get("framing") == "full" and not size_given:
        base = deep_merge(DEFAULT_SPEC, {"canvas": FULL_CANVAS})
    if user_spec.get("framing") == "wide" and not size_given:
        base = deep_merge(DEFAULT_SPEC, {"canvas": WIDE_CANVAS})
    if ((user_spec.get("character") or {}).get("body") or {}).get("pose") == "lie" and not size_given:
        base = deep_merge(DEFAULT_SPEC, {"canvas": LIE_CANVAS, "background": {"type": "bed"}})
    if user_spec.get("subject", "character") != "character" and not size_given:
        base = deep_merge(DEFAULT_SPEC, {"canvas": SCENE_CANVAS})
    if (user_spec.get("character") or {}).get("gender") == "male":
        base = deep_merge(base, MALE_PRESET)
    mood = user_spec.get("mood")
    if mood in MOODS:
        base = deep_merge(base, dict(MOODS[mood]["spec"], character=MOODS[mood]["character"]))
        lying = ((user_spec.get("character") or {}).get("body") or {}).get("pose") == "lie"
        if "background" not in user_spec and not lying:
            base["background"] = MOODS[mood]["background"]
    spec = deep_merge(base, user_spec)
    return validate(spec)


def load(path):
    with open(path, encoding="utf-8") as f:
        return normalize(json.load(f))
