# Low-level API

> Translated from the Korean original. See the translation notice in `SKILL.md`.

## Contents
- Module map
- Canvas
- geom (paths)
- Gradient and colour
- Lighting and rendering
- studio and qa
- Drawing directly

## Module map

| Module | Role |
|---|---|
| `core` | Canvas (structure buffers), Light, Gradient, colour utilities |
| `geom` | Path construction (curves, tapered strokes, shapes, booleans) |
| `figure`, `character`, `head`, `hair`, `wardrobe` | Figures |
| `ensemble` | Shared space for several figures, contact between figures, overlap, shadows |
| `scenery`, `city`, `objects`, `props`, `sculpt` | Landscape, city, still life, modern objects, custom masses |
| `media`, `styles`, `finish` | Medium renderers, style presets, finishing passes |
| `brief`, `compose`, `palette` | Planning, composition, colour planning |
| `studio`, `qa` | Run loop, review tools |

- Typical import: `from atelier import Brief, Canvas, Gradient, Light, Figure, Hair, Ensemble, Sculpture, city, compose, geom, palette, qa, scenery, objects, props, wardrobe, studio, paint, light`

## Canvas

```python
canvas = Canvas(width, height, scale=1.0, seed=0, paper="#ffffff")     # usually created by brief.canvas()
```

- width and height are design units; real pixels are scale times larger
- Structure buffers: albedo (local colour), normal (form), region, depth, shadow (cast shadow), occlusion (contact shadow), soft (soft material), unlit (excluded from lighting), gloss, line (line art), over (final accents), group (medium group), focus

### Drawing methods

| Method | Use |
|---|---|
| `add(shape, fill, region, ...)` | One opaque shape (local colour, form, shadow, outline) |
| `tint(shape, color, alpha, blur, clip)` | Paint over the local colour only (blush, patterns, colour shifts) |
| `shade(shape, amount, blur, clip)` | Set a shadow shape directly (where light is blocked) |
| `occlude(shape, amount, blur, clip)` | Contact shadow (dark gaps and touching places, independent of light direction) |
| `ink(shape, color, stroke, alpha, clip)` | Add a shape or outline to the line layer (it follows the style's line_strength, so it fades in styles with faint lines) |
| `stroke(points, width, color, start, end, peak, alpha, clip)` | Pen line of varying width |
| `accent(shape, color, alpha, clip, blur)` | Accent that stays crisp over the medium (eye glints, sparkles, lamp halos, smoke). Alpha and blurred edges blend in at exactly their stated strength |
| `focus_on(shape, amount, blur)` | Mark the area to render with the finest handling |
| `mask(shape, clip)` | Coverage mask of a path (reusable as a clip) |
| `layer(depth, group)` | Set depth and medium group for everything inside the with block |
| `region_mask(*names)` | Look up a region mask by name |
| `grid()`, `noise(scale, octaves)` | Coordinate grid, smooth noise (for building numpy masks) |

### Arguments of add

```python
canvas.add(shape, fill="#808080", region=None, form="flat", bulge=None, relief=1.0, normal=None,
           unlit=False, gloss=0.0, cast=None, outline=None, clip=None, alpha=1.0, depth=None, group=None,
           keep_normal=0.0, soft=0.0)
```

| Argument | Meaning |
|---|---|
| shape | A `geom` path or a canvas-sized numpy mask (0-1) |
| fill | Colour code, RGB tuple, `Gradient`, or a canvas-sized RGB array |
| region | Region name (the same name means the same region) |
| form | flat for a plane, round for an inflated form |
| bulge | Edge rounding radius for round; None makes the whole shape a dome |
| relief | Strength of the relief |
| normal | Facing of a plane `(nx, ny, nz)` or a normal-map array. Floor `(0, -0.8, 0.6)`, front wall `(0, 0, 1)` |
| unlit | True keeps the painted colour and ignores lighting (sky, light sources, flat design) |
| gloss | Gloss 0-1 |
| cast | `(dx, dy, blur, strength)` casts a shadow onto the layers below |
| outline | Line width or `(width, colour)`; without a colour it is derived from the fill |
| clip | Draw only inside this path or mask |
| keep_normal | Share of the underlying form to keep (patterns on skin, locks on a head) |
| soft | Soft material 0-1 (light wraps deeper and a warm glow appears at the terminator; skin and clouds) |

- A shape drawn later covers those drawn earlier (line art and shadows included)
- Coordinates: x to the right, y downward

## geom (paths)

| Function | Use |
|---|---|
| `runs([[p0, p1, ...], [...]])` | Joins smooth runs; run boundaries become sharp corners |
| `blob(points)` | Smooth closed curve through every point |
| `polygon(points)` | Straight-sided polygon |
| `ellipse(cx, cy, rx, ry, angle)`, `rect(x0, y0, x1, y1, radius)` | Basic shapes |
| `taper(points, width, start, end, peak)` | Outline of a brush stroke, thick in the middle and thin at the ends |
| `ribbon(points, widths)` | Band with a width at each point (hair locks, cloth) |
| `symmetric(half_points, axis_x)`, `mirror(points, axis_x)` | Left-right symmetry |
| `offset`, `rotate`, `scale` | Path transforms |
| `union`, `intersect`, `subtract` | Path booleans |
| `sample(points)` | List of points along the curve |

- `runs` example: a leaf as two runs `[[base, side1, tip], [tip, side2, base]]` gets a pointed tip
- `taper` start and end are the width shares kept at each end (0 needle point, 1 blunt)

## Gradient and colour

```python
Gradient.linear((x0, y0), (x1, y1), ["#colour1", "#colour2"])              # evenly spaced
Gradient.linear(p0, p1, [(0.0, "#colour1"), (0.7, "#colour2"), (1.0, "#colour3")])
Gradient.radial((cx, cy), radius, ["#inside", "#outside"])
```

- Colour notation: `"#rrggbb"`, a tuple of 0-255 integers, a tuple of 0-1 floats
- Utilities: `to_rgb`, `mix(a, b, t)`, `shift_hue(color, degrees)`, `trace_color(color)` (a darker colour for line art)

## Lighting and rendering

| Function | Use |
|---|---|
| `Light(azimuth, elevation, color, shadow_tint, wrap, haze, haze_strength, rim, bounce, bounce_color, flush)` | A light |
| `light(name, **overrides)` | Lighting preset |
| `paint(canvas, style, light, params, extra_finish)` | Render with a style preset and its finish |
| `render(canvas, medium, light, groups, **params)` | Render with a medium directly |
| `reference(canvas, light)` | Smooth reference render without a medium |
| `lightness(canvas, light)` | Per-pixel brightness 0-1 |
| `save(image, path)` | Save as PNG |

- Rendering does not change the canvas, so one canvas can be rendered in several media
- Oil and pointillism place random strokes, so the same `seed` is needed to reproduce a result

## studio and qa

| Tool | Use |
|---|---|
| `studio.run(build, brief, output)` | Handles the command-line modes (`--rough`, `--buffers`, `--styles`, `--style`, `--light`, `--scale`, `--seed`, `--out`) |
| `qa.sheet(images, labels, columns)` | Several images on one sheet |
| `qa.buffers(canvas, light)` | Structure-buffer sheet |
| `qa.zoom(image, x0, y0, x1, y1)` | Enlarge an area (fractional coordinates 0-1) |
| `qa.check_figure(view)` | Count fingers and toes |
| `qa.check_image(image)` | Value, contrast and saturation statistics |
| `compose.value_check(image)` | Three-value conversion |
| `compose.guides(image)` | Overlay a rule-of-thirds guide (for review) |

- When `build` returns a dictionary `{"views": [...], "light": Light, "style_params": {style: {medium parameters}}}`, it is used for the hand and foot check, the light swap and per-scene medium tuning

## Drawing directly

- Break the subject down in this order: one large silhouette, the colour areas inside it, the forms that make light and shade, then lines and accents last
- Choose the form

| Nature of the subject | Tool |
|---|---|
| Flat shapes, patterns, signs | `canvas.add(path, colour, form="flat")` |
| A single rounded form (fruit, stone, cloud) | `canvas.add(path, colour, form="round")` |
| A solid made of several overlapping masses (animal, furniture, vehicle) | `Sculpture` |
| Box shapes in perspective (building, room) | `scenery.Perspective`; for streets, `city` |
| Irregular natural forms (terrain, forest) | numpy masks and `canvas.noise` |

- Define only half of a symmetric shape and complete it with `geom.symmetric`
- When an element repeats, vary its size and position a little with seeded random numbers to break the repetition
- Check the silhouette with `--rough` before drawing details
- To lay a flat element over a solid, use `clip` together with `keep_normal=1.0`
- Show a light source as a bright `unlit=True` shape combined with the `bloom` finish
- Show glass and water with a blurred `tint` of what lies behind and an `accent` highlight on the edge
