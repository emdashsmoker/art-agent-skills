"""Rendering styles and surface materials.

A scene is authored once; the style decides how form, line and finish look.
"""
from dataclasses import dataclass, field, replace


@dataclass
class Style:
    name: str
    # --- form shading ---
    cel_mix: float = 1.0               # 1 = hard bands (anime), 0 = smooth gradient (painting)
    cel_threshold: float = 0.08        # lambert value where light turns to shadow
    cel_edge: float = 0.03             # softness of the band edge
    deep_threshold: float = -0.62      # second, darker band; None disables
    soft_range: tuple = (-0.35, 0.80)  # lambert range mapped to shadow..light when smooth
    ambient: tuple = (0.80, 0.76, 0.92)     # tint multiplied into every shadow
    light_color: tuple = (1.0, 0.97, 0.90)
    key_tint: tuple = (1.0, 1.0, 1.0)  # color of the key light multiplied into the lit side (neon: magenta)
    highlight: float = 1.0             # scales material highlights
    cast_strength: float = 1.0
    cast_blur: float = 1.0             # px; larger = softer cast shadows
    sss: float = 0.0                   # warm glow at the skin terminator
    rim: float = 0.0
    rim_color: tuple = (0.75, 0.85, 1.0)
    # --- line ---
    line_scale: float = 1.0            # 0 = no outlines
    line_tint: float = 0.0             # 0 = ink color, 1 = darkened local color
    ink: tuple = (0.13, 0.10, 0.14)
    # --- finish ---
    painterly: dict = None             # kwargs for painterly.paint, or None
    post: list = field(default_factory=list)


ANIME = Style(
    name="anime", cel_mix=1.0, cel_edge=0.025, ambient=(0.84, 0.78, 0.89),
    line_scale=1.0, line_tint=0.35, rim=0.0, sss=0.0,
    post=[("diffusion", dict(radius=14, strength=0.22)),
          ("bloom", dict(threshold=0.86, radius=14, strength=0.35)),
          ("grade", dict(contrast=1.05, saturation=1.06)),
          ("grain", dict(amount=0.012))],
)

ILLUST = Style(
    name="illust", cel_mix=0.45, cel_edge=0.10, deep_threshold=-0.5,
    soft_range=(-0.45, 0.85), ambient=(0.78, 0.72, 0.90), sss=0.55, rim=0.55,
    line_scale=0.7, line_tint=0.8, cast_blur=3.0,
    post=[("diffusion", dict(radius=18, strength=0.15)),
          ("bloom", dict(threshold=0.85, radius=20, strength=0.30)),
          ("grade", dict(contrast=1.06, saturation=1.04,
                         shadows=(0.97, 0.97, 1.04), highlights=(1.02, 1.0, 0.97))),
          ("paper", dict(amount=0.035)),
          ("grain", dict(amount=0.014))],
)

PAINTERLY = Style(
    name="painterly", cel_mix=0.0, deep_threshold=None, soft_range=(-0.20, 0.72),
    ambient=(0.56, 0.46, 0.48), sss=0.8, rim=0.22, rim_color=(0.95, 0.8, 0.6),
    line_scale=0.0, cast_blur=5.0, highlight=1.2,
    painterly=dict(),
    post=[("grade", dict(contrast=1.08, saturation=1.05,
                         shadows=(1.0, 0.97, 0.94), highlights=(1.02, 1.0, 0.95))),
          ("canvas_weave", dict(amount=0.018)),
          ("vignette", dict(strength=0.30, color=(0.08, 0.05, 0.04)))],
)

# transparent washes: soft light forms, thin colored lines, pigment effects and a ragged paper border
WATERCOLOR = Style(
    name="watercolor", cel_mix=0.30, cel_edge=0.14, deep_threshold=None, soft_range=(-0.45, 0.80),
    ambient=(0.80, 0.78, 0.94), sss=0.35, line_scale=0.45, line_tint=1.0, cast_blur=4.0, cast_strength=0.8,
    highlight=0.6,
    post=[("grade", dict(contrast=0.96, saturation=0.92, gamma=0.92)),
          ("watercolor", dict()),
          ("paper", dict(amount=0.08, scale=3.0))],
)

# graphite on paper: value structure from soft shading, hatching from the post pass
PENCIL = Style(
    name="pencil", cel_mix=0.2, cel_edge=0.12, deep_threshold=None, soft_range=(-0.55, 0.95),
    ambient=(0.72, 0.72, 0.74), line_scale=0.75, line_tint=0.0, ink=(0.12, 0.12, 0.14), cast_blur=3.0,
    highlight=0.3,
    post=[("pencil", dict()),
          ("paper", dict(amount=0.05, scale=2.0)),
          ("grain", dict(amount=0.008))],
)

# retro screen print: two flat tones per color, heavy navy outline, a few inks, dot screen in the shadows
POSTER = Style(
    name="poster", cel_mix=1.0, cel_edge=0.01, deep_threshold=None, ambient=(0.70, 0.66, 0.82),
    highlight=0.0, line_scale=1.7, line_tint=0.12, ink=(0.11, 0.13, 0.24), cast_blur=0.5,
    post=[("grade", dict(contrast=1.06, saturation=0.82, shadows=(0.94, 0.98, 1.06), highlights=(1.05, 1.0, 0.88))),
          ("posterize", dict(levels=6, chroma_step=14.0)),
          ("halftone", dict(cell=6.0, strength=0.28, start=0.40)),
          ("paper", dict(amount=0.04, scale=3.0)),
          ("grade", dict(highlights=(1.0, 0.98, 0.92)))],
)

# night under colored signs: blue-violet shadows, a magenta key, a cyan rim and strong glow
NEON = Style(
    name="neon", cel_mix=0.7, cel_edge=0.06, deep_threshold=-0.55, ambient=(0.30, 0.30, 0.60),
    key_tint=(0.84, 0.62, 0.88), sss=0.3, rim=1.0, rim_color=(0.35, 0.95, 1.0), line_scale=0.75, line_tint=0.5,
    ink=(0.05, 0.04, 0.10), cast_blur=2.0, highlight=1.2, light_color=(1.0, 0.75, 0.95),
    post=[("grade", dict(contrast=1.12, saturation=1.25, gamma=1.18, shadows=(0.80, 0.82, 1.18),
                         highlights=(1.06, 0.96, 1.06))),
          ("bloom", dict(threshold=0.62, radius=16, strength=0.85)),
          ("chromatic", dict(shift=1.6)),
          ("vignette", dict(strength=0.45, color=(0.02, 0.01, 0.06))),
          ("grain", dict(amount=0.014))],
)

STYLES = {s.name: s for s in (ANIME, ILLUST, PAINTERLY, WATERCOLOR, PENCIL, POSTER, NEON)}


def get_style(style, **overrides):
    """Look up a preset by name (or pass a Style) and override fields."""
    base = STYLES[style] if isinstance(style, str) else style
    return replace(base, **overrides) if overrides else base


# Per-material look. shadow_tint multiplies with Style.ambient.
MATERIALS = {
    "matte": dict(shadow_tint=(0.72, 0.72, 0.78), highlight=0.0, hl_range=(0.75, 0.98), sss=0.0),
    "skin":  dict(shadow_tint=(0.90, 0.72, 0.69), highlight=0.10, hl_range=(0.80, 0.99), sss=1.0),
    "hair":  dict(shadow_tint=(0.62, 0.58, 0.72), highlight=0.0, hl_range=(0.70, 0.95), sss=0.0),
    "cloth": dict(shadow_tint=(0.70, 0.68, 0.80), highlight=0.0, hl_range=(0.80, 1.0), sss=0.0),
    "gloss": dict(shadow_tint=(0.60, 0.60, 0.72), highlight=0.55, hl_range=(0.86, 0.97), sss=0.0),
    "flat":  dict(shadow_tint=(1.0, 1.0, 1.0), highlight=0.0, hl_range=(0.9, 1.0), sss=0.0),
}
