# Styles

## How the three styles differ

| Item | `anime` | `illust` | `painterly` |
|---|---|---|---|
| Outline | Thin coloured line | None | None |
| Shadow edge | Crisp two-tone | Crisp two-tone, weaker | Continuous gradation |
| Shadows and light added by hand | Shape kept | Shape kept | Edges loosen |
| Width of form shadows | `bulge` as given | `bulge` as given | 2.2 times `bulge` |
| Edges | Smooth | Wobbly, as if cut by hand | Clean silhouette, brush marks inside the areas |
| Texture | Light grain | Paper colour, mottling, print grain | Flat-brush marks, bristle streaks, paint relief, canvas weave |
| Light handling | Bloom, diffused glow | None | Warm light added on lit areas |
| Render time at 1024 px | 6 s | 4 s | 14 s |

## How to choose

| Words in the request | Style |
|---|---|
| anime, manga, cel, clean lines, character sheet | `anime` |
| illustration, picture book, poster, cover, flat, gouache, risograph | `illust` |
| painting, oil, impressionist, brushwork, impasto | `painterly` |

With no such words, try `anime` first for people and `painterly` first for landscapes.

## Tips per style

### anime

- Lines decide the quality
    + Draw finals at 2048 px and save with `downscale=2`
- Design the shadow shapes yourself
    + The basic three are cast shadows under the hair, under the chin and under the collar
- Keep highlights small and crisp
    + Eyes, hair sheen, lips, metal

### illust

- There are no lines, so colour areas must separate the forms by contrast
    + Give two touching parts clearly different values
- Reduce detail and enlarge the areas
- Thin strokes get lost in the grain; use widths of 3 units or more

### painterly

- Spread the values wide
    + Brushwork blurs detail, so large masses of light and shade carry the form
- Always set focus areas
    + 0.6 on the whole face, 1.0 on the eyes and mouth
    + 0.6-0.7 on still-life objects and on people's bodies
    + Areas without focus stay as large brush marks
- Brush strokes paint only inside areas of similar colour
    + Silhouettes stay clean; brush marks appear only inside the areas
    + If two touching areas differ little in colour, the border is lost in the brushwork
- Strokes 1 unit wide disappear

## Making a new style

`Style` is a frozen dataclass. Derive a new one by changing values of an existing style.

```python
from dataclasses import replace
from atelier import ANIME

BOLD_INK = replace(ANIME, name="bold-ink", line_width=1.8, line_local_color=0.0, ink="#111111")
art = Art(BOLD_INK, ...)
```

| Field | Meaning |
|---|---|
| `shade_mode` | `ShadeMode.CEL` or `ShadeMode.SOFT` |
| `shade_strength` | How strongly the shadow colour applies |
| `form_scale` | Multiplier on `bulge` |
| `softness` | Radius that loosens the edges of shadows and light added by hand |
| `line_opacity` | At 0, outlines and `art.line()` are skipped |
| `line_width` | Multiplier on every line width |
| `line_local_color` | 0 uses only the ink colour; 1 uses only a darkened part colour |
| `ink` | Ink colour |
| `finish` | Post-processing: one of `Finish.ANIME`, `Finish.ILLUST`, `Finish.PAINTERLY` |

Tune the strength of post-processing with the constants at the top of `scripts/atelier/finish.py`.

| Constant | Effect |
|---|---|
| `BLOOM_STRENGTH` | Light bloom in the anime style |
| `WOBBLE_AMPLITUDE` | Edge wobble in the illustration style |
| `SPECKLE_AMOUNT`, `ILLUST_GRAIN` | Grain in the illustration style |
| `BRUSH_RADII` | Brush sizes in the painterly style (large brushes to small) |
| `BRUSH_ERROR_THRESHOLD` | Lower it for more small strokes and finer detail |
| `BRUSH_EDGE_TOLERANCE` | Raise it and strokes bleed across colour borders |
| `IMPASTO_AMOUNT` | Strength of paint relief |

## Mood layer

A colour grade laid once more over the style's finish. It fits all three styles (`scripts/atelier/mood.py`).

```python
from atelier.mood import doomer
art.grade = doomer          # compose("final") and save() apply it after the finish
```

- `art.grade` defaults to `None`. Left empty, the picture does not change
- A mood is one function `grade(image, ppu, rng) -> image`. It takes and returns a 0-1 RGB array
- `GRADES` collects them by name
- `doomer`: a cold, faded photo late at night

| Constant | Effect |
|---|---|
| `DOOMER_SATURATION` | Share of the colour kept |
| `DOOMER_SHADOW`, `DOOMER_HIGHLIGHT`, `DOOMER_SPLIT` | Lean darks toward blue-grey and lights toward faded paper |
| `DOOMER_FADE`, `DOOMER_CONTRAST` | Lift black for a faded-film look |
| `DOOMER_VIGNETTE`, `DOOMER_VIGNETTE_START` | Darken the corners |
| `DOOMER_GRAIN`, `DOOMER_GRAIN_SIZE` | Clumped film grain |

- In the painterly style the brushwork covers thin lines and small dots
    + Put wires, pylons and twigs in focus with `scenes.keep_fine_lines(art)`
    + `scenes.snowfall()` puts snowflakes in focus itself
- Choose the scene in the same mood
    + Night, snow, the orange of sodium street lamps, few lit windows, dark clothes, cigarette smoke
    + Examples: 7 pictures in `examples/doomer.py` (man, woman, two-shot, world-building shot, city, landscape, still life)
