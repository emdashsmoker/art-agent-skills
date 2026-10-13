# Style recipes

A style is a bundle of `Style` values in `scripts/codepainter/styles.py`. Scene code asks the style for line weight and shading method as it draws, so changing the values alone turns the same scene into a different style.

## Style fields

| Field | anime | illust | painterly | Meaning |
|---|---|---|---|---|
| `line_width` | 1.0 | 0.62 | 0.0 | outline weight factor; 0 means no lines |
| `line_tint` | 0.35 | 0.75 | 1.0 | how much the line colour takes after the part colour |
| `line_opacity` | 1.0 | 0.9 | 0.0 | line opacity in the final composite |
| `edge_softness` | 0.015 | 0.10 | 0.22 | softness of the shadow edge |
| `shadow_threshold` | 0.30 | 0.30 | 0.34 | where shadow starts; higher means wider shadows |
| `shadow_depth` | 0.85 | 0.80 | 0.95 | shadow strength |
| `second_tone` | 0.0 | 0.45 | 0.55 | a darker second shade |
| `gradient` | 0.10 | 0.45 | 0.70 | soft volume gradient |
| `cast_softness` | 0.0 | 3.0 | 6.0 | blur of cast shadows |
| `rim` | 0.35 | 0.75 | 0.55 | rim light |
| `highlight` | 1.0 | 0.85 | 0.6 | highlights |
| `blush` | 0.45 | 0.75 | 0.8 | skin flush |
| `strands` | 0.35 | 1.0 | 0.8 | density of hair strands |
| `terminator` | 0.0 | 0.6 | 0.8 | red band along the skin's shadow edge |
| `shadow_tint` | light violet | violet | deep violet | multiply colour of shadows |

## Tuning

```python
style = get_style("anime", line_width=1.3, rim=0.0)       # change some values of a preset
```

- The preset name drives the finishing branch of `finish`, so a variant style follows its base preset's finishing
- See the table below for tested variants

| Goal | Setting |
|---|---|
| Comic look with heavy lines | `get_style("anime", line_width=1.4, highlight=0.8)` |
| Flat poster look with no lines | `get_style("anime", line_width=0.0, line_opacity=0.0, strands=0.0)` |
| Dramatic look with deep shading | `get_style("anime", shadow_threshold=0.42, shadow_depth=1.0, second_tone=0.5)` |
| Clear, light watercolour illustration | `get_style("illust", shadow_depth=0.55, line_opacity=0.6, gradient=0.6)` |
| Painterly with lines left in | `get_style("painterly", line_width=0.5, line_opacity=0.5)` |

## Finishing passes

| Style | Order inside `finish` |
|---|---|
| anime | diffusion glow, colour grade, light grain |
| illust | bloom, diffusion glow, tint of lights and darks, paper texture, vignette, grain |
| painterly | brush repaint, colour grade, vignette |

- To set the strengths yourself, apply `fx` functions one by one to the result of `painting.flatten(style.line_opacity)`

```python
image = painting.flatten(style.line_opacity)
image = fx.glow(image, radius=12, strength=0.10)
image = fx.grade(image, contrast=1.08, saturation=1.1, shadows=("#2a2a50", 0.12))
painting.save("out.png", fx.grain(image, 0.01))
```

## Painterly brushwork

- The principle is layered painting from large brushes to small
    + Each layer adds strokes only in cells where the current canvas differs strongly from the source
    + Strokes flow along the direction of form edges
- Flat areas keep large brush marks; only areas with detail get tidied with small brushes
    + So the clearer the value and colour masses of the source, the better the result

| Option | Default | Effect |
|---|---|---|
| `importance` | None | areas with value 1 are painted finely with thin brushes |
| `detail` | 1.0 | above 1 makes everything finer, below 1 rougher |
| `bristle` | 1.0 | strength of the bristle texture |
| `impasto` | 1.0 | strength of the paint-thickness relief |
| `canvas` | 1.0 | strength of the canvas weave texture |
| `ground` | auto | ground colour showing between strokes |
| `seed` | 0 | random stroke placement |

```python
image = finish(painting, style, importance=masks["head"], detail=1.2, impasto=1.4)   # thick, detailed oil
image = finish(painting, style, detail=0.7, bristle=0.5, canvas=0.3)                 # rough, smooth gouache
```

- The brush sizes are the list of `BrushLayer(radius, threshold, steps, jitter, focus_only)` in `painterly.BRUSH_LAYERS`
    + Pass another list to `layers=` to replace it
    + Keep `jitter` below `threshold / 3`, or strokes are painted over without end

## New styles

```python
from codepainter.styles import Style
NOIR = Style(name="anime", line_width=1.2, line_tint=0.0, line_opacity=1.0, edge_softness=0.01,
             shadow_threshold=0.45, shadow_depth=1.0, second_tone=0.0, gradient=0.0, cast_softness=0.0,
             rim=0.6, highlight=0.7, blush=0.0, strands=0.2, terminator=0.0, shadow_tint=(0.35, 0.35, 0.45))
```

- `name` sets the finishing branch, so give one of `anime`, `illust`, `painterly`

## Doomer mood

The skill's signature look. A mood laid over any of the three styles at the end.

- Core message : one warm light in a cold, endlessly repeating concrete world
- Test : does the cold repeating structure dominate the picture while the single warm light holds the eye

```python
from codepainter import fx, scenery, sets
painting = Painting(1536, 1024)
info = sets.SETS["panel_block"](painting, style, lamp=0.53)       # overcast sky, panel blocks, snowy yard, sodium lamp
scenery.snowfall(painting, 1400, seed=3)                          # with figures, call it after drawing them
image = fx.doomer(finish(painting, style), seed=3)
```

| Element | Rule |
|---|---|
| Colour | one low-saturation blue-grey family; the accent is one warm orange family (lit windows, street lamps, a low sun, a glass of tea) |
| Light | paint warm light with `mode="normal"`; painted with `screen` over bright snow it washes out to white and the mood grade drains it |
| Buildings | draw panel seams, window grids, balconies and stairwells with `scenery.panel_facade`; 15-30% of windows lit |
| Figures | black clothes (`look(..., outfit="doomer")`), a beanie (`hat="beanie"`), drooping eyes and a lowered gaze (`head_tilt`), placed on a third of the frame |
| Weather | overcast sky, snowy ground and grey slush, `scenery.snowfall`, bare trees with `scenery.bare_tree` |

- The order inside `fx.doomer(image, seed, strength)` : lower saturation, teal shadows and faded lights, lifted blacks, vignette, heavy grain
    + Where `fx.warm_lights(image)` is 0 the saturation is `fx.DOOMER["saturation"]`, where it is 1 it is `warm_saturation`
    + The warm-light test uses red minus blue against `fx.WARM_EDGES` and brightness against `fx.LIT_EDGES`; skin keeps only part of its colour
- Choosing the style
    + When a face is the subject, anime or illust; when space and air are the subject, painterly
- The 7 cuts of the finished example `scripts/examples/doomer.py`

| Cut | Style | Composition |
|---|---|---|
| `man` | illust | waist shot by the yard lamp, beanie and hoodie |
| `woman` | anime | bust in front of the blocks at night, black turtleneck, fringe |
| `pair` | anime | two people with a street lamp between them, each looking the other way |
| `establishing` | painterly | yard between two blocks, climbing frame, a small figure from behind under the lamp with its footprints |
| `city` | illust | rows of blocks seen from high up, striped chimney with smoke, power lines |
| `landscape` | painterly | snowfield, birches, pylons running to the horizon, a low sun |
| `still_life` | painterly | kitchen windowsill at night, tea glass in a metal holder, cassette, wired earphones |

- The layout and forms of particular album covers, photos or meme characters are not copied; only genre elements are combined
