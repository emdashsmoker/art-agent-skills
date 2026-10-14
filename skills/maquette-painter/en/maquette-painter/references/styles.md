# Styles, lighting, media, finishing

> Translated from the Korean original. See the translation notice in `SKILL.md`.

## Contents
- Usage
- Style presets
- The doomer style
- Lighting presets
- Medium parameters
- Finishing passes
- Building a style the presets lack
- Colour planning tools

## Usage

```python
from atelier import paint, light, render, finish
image = paint(canvas, "watercolor", light("golden_hour"))                    # the preset as it is
image = paint(canvas, "oil", scene_light, params=dict(radii=(20, 10, 5), impasto=1.0),
              extra_finish=[("vignette", dict(strength=0.3))])               # override parameters, add a finish
image = render(canvas, "gouache", scene_light, groups={"figure": ("cel", dict(bands=3))})   # choose the medium directly
```

- `paint` renders with the preset's medium and then applies its finishing passes in order
- In a scene script, put `style_params` in the dictionary `build` returns to change medium parameters for that scene only
    + `return {"views": [view], "style_params": {"pastel": dict(paper="#8e99ae", grain=0.45)}}`
    + It applies per style name, so when other styles are compared with `--styles` it reaches only that style
    + Examples: light blue-grey pastel paper for a snow landscape (`scene_snow_forest.py`), smaller impressionist brushes and less colour jitter (`scene_beach_sunset.py`)
- `render` applies only the medium; `groups` assigns a different medium to each layer group
- In `studio.run` the options `--style`, `--light` and `--styles` give the same control

## Style presets

| Key | Medium | Face | Traits |
|---|---|---|---|
| anime_cel | cel | anime | Two-tone shading, colour-traced lines, soft diffusion |
| anime_film | gouache + cel | semi | Gouache backgrounds, three-tone figures, film compositing (diffusion, chromatic aberration, grain) |
| retro_anime | gouache + cel | anime | Black lines, hard shadows, high saturation, coarse grain |
| webtoon | cel | semi | Soft shading edges, bloom |
| manga | halftone (mono) | anime | Black-and-white screentone |
| flat_vector | flat | anime | Flat colour without shading or lines |
| flat_shadow | cel | anime | Flat colour without lines and one shadow tone |
| poster | gouache | semi | Poster colour in three values |
| storybook | watercolor | anime | Watercolour with pencil lines, a border of bare paper |
| pop_art | halftone | semi | Ben-Day dots and heavy black lines |
| art_nouveau | woodblock | semi | Flat colour and ornamental lines, faded paper |
| renaissance | oil | classic | Fine brushes, dark underpainting, umber glaze, craquelure |
| baroque | oil | classic | Strong value contrast, dark background |
| academic | oil | classic | Smooth brushwork, light underpainting |
| oil | oil | classic | Basic oil painting |
| impressionism | oil | classic | Short thick strokes, broken colour |
| post_impressionism | oil | classic | Long swirling strokes, high saturation |
| expressionism | oil | classic | Large brushes, exaggerated colour, outlines |
| fauvism | oil | classic | Saturation close to pure hues |
| pointillism | pointillism | classic | Divided colour dots |
| cubism | facets | classic | Faceted planes, muted colour |
| sumi_e | ink | semi | Ink wash, five ink tones, empty space |
| ink_color | ink | semi | Ink with light colour (sumuk damchae) |
| ukiyo_e | woodblock | semi | Flat colour, bokashi gradations, ink lines |
| minhwa | woodblock | semi | Flat colours of the five traditional hues on hanji paper |
| pencil | pencil | classic | Graphite hatching |
| colored_pencil | pencil | semi | Coloured pencil |
| charcoal | charcoal | classic | Smudged charcoal |
| pastel | pastel | classic | Pastel on tinted paper |
| watercolor | watercolor | semi | Transparent watercolour, pencil lines |
| watercolor_loose | watercolor | semi | Watercolour with heavy bleeding, no lines |
| urban_sketch | watercolor | semi | Ink lines with watercolour |
| doomer | gouache + cel | semi | Faded colour, teal-black shadows, sodium lamps and lit windows that bloom, film grain; figures in two-tone cel tinted by the light colour |
| doomer_mono | gouache + cel | semi | A black-and-white photocopy of the same world, crushed blacks, coarse toner grain |

## The doomer style

A style that paints a winter night in a post-Soviet suburb like a faded photograph. It copies no particular record sleeve or character and builds the mood from generic things.

| Element | Tools |
|---|---|
| Place | `city.building(kind="panel")` panel blocks, `city.pylon` with `city.wires(painted=True)`, `city.chimney`, `scenery.bare_tree(birch=True)`, playground frames with `city.struts` |
| Light | Sodium lamp `#ffb468`, mercury lamp `#a4b4d4`, lit windows (panel facades light them at random at night), a sky lit by the town |
| Figures | `Hair("beanie")`, `wardrobe.hoodie`, `turtleneck`, a long `coat`, `expression="tired"`, a `props.cigarette` in the mouth with `props.smoke` |
| Weather | Two layers of `weather("snow")`, `wet_reflection` on slushy roads |

- doomer suits night; doomer_mono suits an overcast day or a snowy field
    + doomer lowers saturation to 0.72 and blooms the highlights, so lit windows and street lamps remain the only warm colours
    + doomer_mono is black and white with contrast 1.4, so keep sky and snowfield light and pylons and trees dark to read as silhouettes
- Light a figure with one street lamp as the key and leave the other side in teal-black shadow
    + The preset contains `key_color=0.6` so the key colour seeps into the face
    + For figures seen from behind or against the light, a light with `rim` draws a thin edge around the outline (`doomer_duo.py`)
- Check the three values in the rough so forms do not vanish in a dark picture (three layers: sky, buildings, lit windows)
- Examples: `doomer_male.py`, `doomer_female.py`, `doomer_duo.py`, `doomer_establishing.py`, `doomer_city.py`, `doomer_landscape.py`, `doomer_still_life.py`

## Lighting presets

```python
light("rembrandt", azimuth=-45, elevation=38)      # override arguments of a preset
```

| Key | Direction and character |
|---|---|
| studio | Upper left at 45 degrees, neutral |
| soft_front | Soft light from near the front, few shadows on the face |
| rembrandt | Warm light from the upper left side, deep shadows |
| side | Side light close to horizontal |
| top | Light from overhead |
| backlit | Back light, rim light |
| golden_hour | Low warm light, violet shadows, warm atmosphere |
| noon | High sun, blue shadows |
| overcast | Diffuse light, weak shadows |
| blue_hour | Cool low light |
| night | Moonlight |
| candle | Low red light close by |

- `Light` arguments

| Argument | Meaning |
|---|---|
| azimuth | -90 left, 0 front, 90 right, 150 and above is behind |
| elevation | 0 horizontal, 90 overhead |
| color, shadow_tint | Colour of the light, colour multiplied into the shadow side |
| wrap | How far light wraps around forms (higher is softer) |
| shadow_strength | Strength of cast shadows |
| haze, haze_strength | Atmosphere colour and how strongly the distance fades |
| rim | Rim light strength |
| bounce, bounce_color | Strength and colour of light reflected back into the shadow side (the terminator stays darkest) |
| flush | Warm glow just inside the terminator of soft materials such as skin |

- Tilt shadow colours toward the complement of the light (blue-violet shadows under warm light)
- Value steps of the reference render: light side, half tone, terminator (core shadow), reflected light, contact shadow (ambient occlusion)
    + Contact shadow is darkness independent of light direction, in creases, armpits and where objects touch
    + Set it directly: `canvas.occlude(shape, amount, blur, clip)`

## Medium parameters

### cel
| Argument | Meaning |
|---|---|
| bands | 1 flat, 2 base and shadow, 3 adds a deep shadow |
| soft | Width of shading edges (0.015 crisp, 0.13 airbrushed) |
| shadow_at, deep_at | Brightness where the shadow starts |
| simplify | How much shadow shapes are simplified |
| shadow_tint, shadow_saturation | Shadow colour |
| highlight | Strength of gloss highlights |
| lines | trace (colour trace), black, sepia, none |
| key_color | 0-1, how much the key light colour mixes into the lit tone (default 0 keeps the local colour; 0.5-0.7 when the light colour should show, as on a face under a sodium lamp) |
| rim | 0-1, uses the light's `rim` value to draw a bright edge on outlines turned toward the light (backlit silhouettes) |

### watercolor
| Argument | Meaning |
|---|---|
| wetness | Amount of bleeding (0 crisp, 1 very wet) |
| edge_darkening | How much paint pools at the edges |
| granulation | How much pigment settles into the paper grain |
| bloom | Water blooms |
| wobble_px | Hand-drawn wobble of outlines |
| glazes | Number of shadow glazes |
| reserve | Bare paper left in the lights |
| lines | pencil, ink, none |
| border | Width of the unpainted paper border |

### oil
| Argument | Meaning |
|---|---|
| radii | Brush radii, largest first; drop the small ones for a rough painting |
| threshold | Error threshold for repainting (higher gives sparser strokes) |
| length | Stroke length (minimum, maximum) |
| curvature | How strongly a stroke keeps its direction |
| jitter, hue_jitter | Per-stroke value and hue variation |
| swirl | Swirl of brush direction |
| impasto | Relief of thick paint |
| ground | Underpainting colour |
| vivid | Saturation multiplier |
| line_strength | How much of the underdrawing stays visible |
| focus_radii | Fine brushes used only in the focus area (the face) |

### gouache
| Argument | Meaning |
|---|---|
| steps | Number of value steps |
| soft | Blending between steps |
| brush | Strength of brush marks |
| wobble_px | Outline wobble (0.5 or less for architecture) |

### ink
| Argument | Meaning |
|---|---|
| tones | Ink tone steps |
| bleed | Bleeding |
| dry_brush | Dry brush |
| color | Colour wash strength (0 pure ink, 0.5 light colour) |
| mist | How far the distance dissolves into empty paper |

### pencil, charcoal, pastel
| Argument | Meaning |
|---|---|
| spacing, layers | Hatching spacing and number of layers (pencil) |
| softness | Amount of smudging |
| color | 0 graphite, 1 coloured pencil |
| paper | Paper colour (tinted paper for pastel) |
| grain | Paper grain showing through (pastel) |

### woodblock, halftone, pointillism, facets
| Medium | Main arguments |
|---|---|
| woodblock | bands, bokashi (gradation at the top), misregister (blocks out of register), mute (saturation), paper |
| halftone | dot (dot spacing), mono (black-and-white screentone), vivid |
| pointillism | dot (dot size), divide (amount of colour division), passes |
| facets | cell (facet size), mute, tilt (facet shading) |

## Finishing passes

| Function | Use |
|---|---|
| `grade(image, contrast, saturation, temperature, exposure, gamma)` | Colour grading |
| `bloom(image, threshold, radius, strength)` | Glow around bright areas |
| `diffusion(image, radius, strength)` | Diffusion glow of anime photography |
| `light_wash(image, direction, color, strength)` | Directional light gradient across the picture |
| `vignette(image, strength, softness)` | Darker edges |
| `glaze(image, color, strength)` | A transparent colour layer over everything (the warm tone of old paintings) |
| `grain(image, amount, size)` | Film grain |
| `craquelure(image, scale, strength)` | Cracks of an old oil painting |
| `chromatic(image, pixels)` | Lens chromatic aberration |
| `seal(image, x, y, size)` | Artist's seal |
| `mat(image, margin, color)` | Mat border |

- Apply finishes lightly (if the effect shows before the picture, it is too much)
- Add one with `paint(..., extra_finish=[("function name", dict(arguments))])`

## Building a style the presets lack

- Pick the closest preset, then adjust three things: medium parameters, lighting, finish
- Recipes

| Goal | Recipe |
|---|---|
| Ghibli-like background | gouache (steps 5, soft 0.25), noon lighting, saturation 1.1 |
| Shinkai-like sky | cel figures with gouache backgrounds, golden_hour, stronger bloom and light_wash |
| Rococo | academic with a pastel palette, soft_front lighting |
| Romantic landscape | oil (radii 20, 10, 5, 2.5), golden_hour, vignette 0.3 |
| Van Gogh-like | post_impressionism with swirl 0.5, complementary palette |
| Monet-like | impressionism with hue_jitter 0.05, overcast lighting |
| Mucha-like | art_nouveau with heavy outlines (raise line_width), a round halo shape |
| Pop art portrait | pop_art with a primary-colour background, vivid 1.8 |
| Noir | charcoal or cel (bands 2) with side lighting, the noir palette |
| Cyberpunk | anime_cel with night lighting, neon `unlit` shapes, stronger bloom |
| Rainy night anime | retro_anime with night lighting (lighter shadow_tint), two layers of `weather("rain")`, `wet_reflection`, finish glow |
| Candlelit chiaroscuro (tenebrism) | baroque with candle-like lighting (elevation 5-10), dark background with a halo on the wall around the candle, `objects.candle` |
| East Asian painting with colour | ink_color with color 0.7 |
| Fantasy concept art | oil (keep focus_radii), backlit lighting, bloom |

- The essence of a style also belongs in the structure stage
    + Ukiyo-e wants flat composition and wide empty space, art nouveau curving ornament and round halos, cubism front and side views at once
- Render a new recipe next to the existing presets with `--styles` and compare

## Colour planning tools

```python
from atelier import palette
palette.harmony("#2f8f8a", "analogous")        # three analogous colours
palette.harmony("#c8553d", "complementary")    # complementary pair
palette.ramp("#6b8ec2", steps=5)               # value steps that turn cooler in the darks and warmer in the lights
palette.mute("#c8553d", 0.4)                   # lower saturation
palette.NAMED["earth"]                         # a named palette
```

- Schemes: monochrome, analogous, complementary, split, triad, tetrad
- Named palettes: earth, impressionist, ukiyo, pastel, noir, sunset, forest, ocean, minhwa, doomer
- Keep colour shares near 60 dominant, 30 secondary, 10 accent
- Use the accent colour only at the focal point
