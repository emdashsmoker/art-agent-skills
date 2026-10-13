"""paintkit.spec: the three knobs of a portrait.

Palette = which colors, CharacterSpec = who is drawn, RenderStyle = how it
is rendered. Everything else in the rig is derived from these.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Palette:
    skin: str = "#fbe5d8"
    skin_shadow: str = "#eab7aa"
    blush: str = "#f39a96"
    lip: str = "#d8706f"
    hair: str = "#2c3048"
    hair_shadow: str = "#181a2b"
    hair_light: str = "#93a2d6"
    iris: str = "#3f7fb5"
    eye_white: str = "#f8f4f2"
    line: str = "#3a2326"
    cloth: str = "#f3efe9"
    cloth_shadow: str = "#c7c3d1"
    cloth2: str = "#30323f"
    shoe: str = "#2a2630"
    accent: str = "#8a2f3c"       # tie and other small accents
    outer: str = ""               # jacket or coat over the top; empty = the material's own color
    hat: str = "#2b2c33"          # knit hat (character.hat)


GENDERS = ("female", "male")


@dataclass
class CharacterSpec:
    gender: str = "female"        # female | male (see GENDER_DEFAULTS)
    # --- face shape ---
    jaw_sharpness: float = 0.8    # 0 = soft oval, 1 = sharp V line
    face_width: float = 1.0       # horizontal scale of the face
    chin_length: float = 1.0      # vertical scale below the mouth
    # --- eyes ---
    eye_width: float = 0.190
    eye_height: float = 0.098
    eye_spacing: float = 0.172    # eye center distance from the midline
    eye_tilt: float = 0.012       # outer corner lift (positive = upturned)
    iris_scale: float = 1.0
    gaze: tuple = (0.0, 0.0)      # iris offset, in iris radii
    eyelid_open: float = 1.0      # 0.6 = half-lidded
    brow_angle: float = 0.006     # positive lifts the tail
    # --- mouth ---
    mouth_width: float = 0.115
    smile: float = 0.35           # -1 frown ... 1 smile
    lip_fullness: float = 1.0
    # --- pose ---
    head_tilt: float = -4.0       # degrees, positive = clockwise on screen
    head_turn: float = 0.0        # -1 ... 1, positive turns the face to the viewer's right
    # --- hair ---
    hair_style: str = "long_straight"   # long_straight | long_wavy | bob | short | medium | slicked
    bangs: str = "side_swept"            # side_swept | see_through | parted | short_fringe | swept_back
    parting: float = -0.10               # x of the parting, head units
    hair_seed: int = 7
    # --- outfit ---
    outfit: str = "vneck"                # vneck | turtleneck | blazer | offshoulder | crewneck | shirt | suit
    hat: str = "none"                    # none | beanie (hat.HATS)
    # --- presets (see features.py and SKIN_TONES; "default" keeps the gender's own look) ---
    skin_tone: str = "default"           # default | fair | light | medium | tan | brown | deep
    eye_shape: str = "default"           # default | round | almond | upturned | droopy | monolid
    brow_shape: str = "default"          # default | straight | arched | thick
    nose_shape: str = "default"          # default | dot | bridge
    mouth_shape: str = "default"         # default | small | heart
    palette: Palette = field(default_factory=Palette)


@dataclass
class RenderStyle:
    """How the same geometry gets rendered. See styles.py for presets."""
    name: str = "anime"
    shadow_softness: float = 0.02     # lambert-space softness of form shadows
    cast_softness: float = 0.0        # blur (head units) of cast shadows
    shadow_strength: float = 1.0
    face_shadow_level: float = -0.10  # lambert threshold; higher = larger face shadow
    line_width: float = 0.0045        # outline width, head units (0 = no line)
    line_opacity: float = 1.0
    line_variation: float = 0.6
    airbrush: float = 0.5             # strength of soft gradients
    hair_strands: float = 1.0         # density multiplier of strand lines
    hair_highlight: str = "band"      # band | soft | none
    eye_detail: float = 1.0
    rim_light: float = 0.0
    lip_render: str = "tint"          # tint | full


# Starting values per gender, used for every key a spec leaves out. The
# dataclass defaults above are the female values, so "female" adds nothing.
GENDER_DEFAULTS = {
    "female": {},
    "male": dict(jaw_sharpness=0.85, face_width=0.95, chin_length=1.05, eye_width=0.182, eye_height=0.062,
                 eye_tilt=0.014, iris_scale=0.80, eyelid_open=0.92, brow_angle=0.0, mouth_width=0.125, smile=0.10,
                 lip_fullness=0.45, head_tilt=-2.0, hair_style="layered", bangs="layered", parting=-0.06,
                 outfit="shirt"),
}
GENDER_PALETTES = {
    "female": {},
    "male": dict(skin="#f6dccb", skin_shadow="#dca592", blush="#e9a497", lip="#c98d84"),
}


# Skin tone presets, light to deep: (skin, skin_shadow, blush, lip) per gender. Shadows stay warm
# and a step more saturated than the skin; male blush and lips sit closer to the skin.
SKIN_TONES = {
    "fair": {"female": ("#fdeee6", "#efc2b8", "#f4a3a0", "#dc7a7c"),
             "male": ("#f9e6da", "#e2b3a3", "#eab0a5", "#cf9a92")},
    "light": {"female": ("#f8dcc8", "#e4ab97", "#ef9a8f", "#d26e68"),
              "male": ("#f3d3bf", "#d69d88", "#e3a090", "#c4877b")},
    "medium": {"female": ("#ecc39f", "#cf9474", "#e08a74", "#c06258"),
               "male": ("#e6ba98", "#c48a6a", "#d4917a", "#b27e6a")},
    "tan": {"female": ("#d6a47c", "#b37b58", "#c9765d", "#a9544a"),
            "male": ("#cf9b74", "#a8724f", "#bb7a60", "#9c6a58")},
    "brown": {"female": ("#a8724c", "#80502f", "#a35a43", "#7e3f36"),
              "male": ("#9f6b47", "#774a2c", "#94573f", "#75463a")},
    "deep": {"female": ("#6e4630", "#4c2c1c", "#7a3c2c", "#5a2a24"),
             "male": ("#684330", "#452819", "#6c3a2a", "#553026")},
}
SKIN_TONE_KEYS = ("skin", "skin_shadow", "blush", "lip")


def skin_tone_palette(tone: str, gender: str) -> dict:
    """Palette values of a skin tone preset; empty for "default" (the gender's own colors)."""
    if tone == "default":
        return {}
    if tone not in SKIN_TONES:
        raise ValueError(f"unknown skin_tone '{tone}', expected one of {['default', *SKIN_TONES]}")
    return dict(zip(SKIN_TONE_KEYS, SKIN_TONES[tone][gender]))


def with_gender_defaults(character: dict, palette: dict) -> tuple:
    """(character values, palette values) with the gender's starting values filled in.
    A skin tone preset sits between the gender palette and the spec's own palette keys."""
    gender = character.get("gender", "female")
    if gender not in GENDERS:
        raise ValueError(f"unknown gender '{gender}', expected one of {GENDERS}")
    tone = skin_tone_palette(character.get("skin_tone", "default"), gender)
    return {**GENDER_DEFAULTS[gender], **character}, {**GENDER_PALETTES[gender], **tone, **palette}
