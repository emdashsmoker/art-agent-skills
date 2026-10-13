# Engine API

## Contents

- Coordinates and units
- Scene
- Part
- Line and Stroke
- Ribbon and curve tools
- Connected shapes
- Color tools
- Styles and materials
- Brush pass
- Post effects
- Backdrops
- Review tools
- Tuning constants

## Coordinates and units

- Coordinates are pixels; x grows to the right, y grows downward
- Colors are `"#rrggbb"` strings or RGB in the range 0..1
- Angles are radians, clockwise on screen is positive
    + Only `FigurePose` uses degrees
- The light vector `light=(x, y, z)` points from the surface toward the light; z points toward the viewer
    + A light at the upper left, in front: `(-0.48, -0.58, 0.66)`
    + A side light that stresses volume: `(-0.74, -0.42, 0.52)`

## Scene

```python
scene = Scene(width=1024, height=1280, light=(-0.48, -0.58, 0.66), seed=0)
scene.set_background(color_or_image)      # a color or an (h, w, 3) image
scene.add(part, [part, ...], ...)         # the order of adding is the back-to-front order
img = scene.render("anime")               # returns 0..1 float RGB
img, buffers = scene.render(style, return_buffers=True)   # also returns the flat, normals and focus buffers
save(img, "out.png")
```

- Rendering runs masks, shading and shadows per part, lines, then the style finish
- `flat` from `return_buffers` is the picture before the finish, useful to locate defects

## Part

One shape. Give either `polys` or `ribbon`.

| Field | Default | Meaning |
|---|---|---|
| `name` | required | name, used to target `clip` |
| `color` | required | local color |
| `polys` | None | list of closed polygons, filled as their union |
| `ribbon` | None | a `Ribbon` object |
| `material` | `"matte"` | material name, see the material table below |
| `shade` | True | False fills flat without volume shading |
| `bulge` | 1.0 | how strongly a polygon shape rounds; lower is flatter |
| `flatness` | 1.0 | flatness of a ribbon's cross section; 1 is a cylinder |
| `gradient` | None | `((x, y), color, (x, y), color)` linear gradient fill |
| `line` | None | outline `Line` |
| `strokes` | [] | list of detail `Stroke`s |
| `clip` | None | a name or group name (or a list), keeps the shape inside those parts |
| `fade_t` | None | ribbons only: `(t0, t1)` fades in at the start, `(t0, t1, t2, t3)` also fades out at the end |
| `erase` | [] | `[(polygon, blur px)]` soft holes |
| `blur` | 0 | edge blur in px, for blush and auxiliary shading |
| `alpha` | 1.0 | opacity |
| `blend` | `"normal"` | `normal`, `multiply`, `screen`, `add` |
| `cast` | 0 | distance in px of the shadow cast on parts below |
| `receive` | True | whether cast shadows fall on it |
| `group` | `""` | parts of one group do not cast shadows on each other |
| `focus` | 0 | how finely the brush pass paints here, 0..1 |
| `light_bias` | 0 | positive shifts the shading toward light, negative toward shadow |
| `accent` | False | marks a painted highlight; left out by a style without highlights (`highlight` 0, `poster`) |
| `depth` | None | stage depth (m) of a piece of furniture, used by `Set.arrange` to sort people among it; None stays behind everything, like walls and floors |

- `clip` can refer only to parts added earlier
- `clip`, `under`, `shape_with` and `merge` find parts by name, group and tag, so parts with the same name in one scene get mixed up
    + When placing several people or objects made by the same module, give the names a unique prefix (for people, `FigureSpec.ident`)
- Flat details (pupils, patterns, highlights) use `shade=False, material="flat"`

## Line and Stroke

```python
Line(width=2.2, color=None, taper=True, shade_gain=0.7, paths=None, caps=(False, False), alpha=1.0)
Stroke(path, width=1.6, color=None, taper=(True, True), alpha=1.0, clip=False, feature=True)
```

- `Line` is the outline of a part
    + `color=None` mixes the style's ink color with the local color automatically
    + `shade_gain` is how much heavier the line gets on the side away from the light
    + `paths` draws only the given stretches instead of the whole outline
    + `caps` says whether to ink the start and end caps of a ribbon
    + `taper` is True, False or a `(start, end)` tuple
- `Stroke` is a free line belonging to a part
    + `width` is a single value or an array along the stroke
    + `feature=True` draws in every style (lashes, the mouth line); False is left out in line-less styles (strand lines)
    + `clip=True` keeps it inside its own part

## Ribbon and curve tools

```python
Ribbon(axis, width_a, width_b=None, step=4.0, round_start=True, round_end=True)
```

- `axis` is the axis polyline; `width_a` and `width_b` are the half widths on each side
    + A width is a single value, an array, or a key list `[(t, width), ...]`
    + When the axis runs down the screen, side A is on screen-left
- `ribbon.side_a` and `ribbon.side_b` are the side outlines, `ribbon.axis` is the resampled axis
- `ribbon.cap(0)` and `ribbon.cap(1)` are the round caps at the start and end
- `ribbon.outline_paths(cap_start, cap_end)` is the list of paths to ink

| Function | Use |
|---|---|
| `catmull_rom(points, closed=False, samples=14)` | a smooth curve through the control points |
| `bezier(p0, p1, p2, p3, n=24)` | cubic Bezier curve |
| `ellipse(cx, cy, rx, ry, rot=0, n=48)` | ellipse polygon |
| `transform(p, scale, rotate, translate, origin, mirror)` | scale, rotate, move, mirror |
| `chaikin(p, iterations=2)` | rounds the corners of a joint chain |
| `offset_polygon(poly, distance)` | grows or shrinks a smooth closed polygon |
| `resample(p, step=None, n=None)` | even resampling by arc length |
| `profile(keys, t)` | monotone interpolation between `[(t, value)]` keys |
| `lerp(a, b, t)` | linear interpolation |

## Connected shapes

When limbs grow out of a trunk, inking every shape separately leaves a line at every joint. The fields below treat several shapes as one surface.

| Field | Meaning |
|---|---|
| `merge` | parts sharing the key are inked as one surface; line weight and color come from the first part's `line` |
| `joints` | `[(x, y, radius)]` where this part grows out of another; no overlap line inside the radius |
| `grow_from` | `(part name, blur px)` inside the joint radius the fill fades into the base part so it shows through |
| `shape_with` | list of part names: the form is inflated as one mass with the adjoining parts, so no rim of shading appears where they meet; give the parts of one mass the same `bulge` too |
| `tags` | extra keys that other parts can use in `clip`, `under` and `shape_with` |
| `under` | list of keys: the part lies beneath those parts and is hidden where they are (cloth under a hand on the hip); no ink is drawn in the hidden area either |
| `fitted` | inflates and inks the shape as clipped by `clip`; for clothes that hug the body |

```python
body = Part("body", FUR, polys=[body_outline], material="hair", merge="cat", line=Line(3.0),
            shape_with=["leg"])
leg = Part("leg", FUR, ribbon=leg_ribbon, material="hair", merge="cat",
           joints=[(hip_x, hip_y, 40)], grow_from=("body", 6))
```

- Ink appears only on the silhouette of the union and where a front part passes over a back part
- The ink is drawn right after the last part of a merge group, so add the parts of a group one after another
    + An opaque part of another group added in between (with a line, `normal` blend, `alpha` 0.9 or more) hides the ink of the group parts before it
    + By this rule a sleeve stacked right after an arm lies over the arm's ink
    + Parts of the same `group` as the merge group (a hand at the end of an arm) do not hide it, so the union outline is drawn over them
    + The ink of a back group part that passes over the inserted part again is kept
- Shapes laid on the body, such as clothes, are added after the group with `clip` naming the body parts
    + A part with `clip` has its outline clipped to the same area
- An independent silhouette made of several polygons (the hip band and leg tubes of shorts) takes a `merge` so only the outline of the union is inked

## Color tools

| Function | Use |
|---|---|
| `rgb(value)` | converts a color string to a 0..1 array |
| `mix(a, b, t)` | mixes two colors |
| `adjust(color, hue=0, sat=1, val=1)` | hue shift, saturation and value factors |
| `vertical_gradient(h, w, [(y share, color), ...])` | vertical gradient image |
| `fbm(h, w, scale, octaves, seed, stretch)` | 0..1 fractal noise; `stretch` widens it horizontally |
| `smoothstep(e0, e1, x)` | smooth step function, reversed edges supported |

## Styles and materials

```python
from codepaint import get_style, ANIME, ILLUST, PAINTERLY, WATERCOLOR, PENCIL, POSTER, NEON
style = get_style("illust", rim=0.8, line_scale=0.5)     # override only some fields of a preset
```

| Preset | Shading | Line | Post effects |
|---|---|---|---|
| `anime` | stepped shading | dark line | diffusion glow, bloom, grain |
| `illust` | soft shading with a weak edge | local-color line | diffusion glow, bloom, paper grain |
| `painterly` | continuous shading | no line | brush repainting, canvas grain, vignette |
| `watercolor` | light continuous shading | thin local-color line | `watercolor`, paper grain |
| `pencil` | grayscale continuous shading | graphite line | `pencil`, paper grain |
| `poster` | two-step flat shading, no highlights | heavy navy line | `posterize`, `halftone`, paper grain |
| `neon` | blue-violet shade, magenta key | thin dark line | night grading, strong bloom, `chromatic`, dark vignette |

| Style field | Meaning |
|---|---|
| `cel_mix` | 1 is stepped shading, 0 continuous shading |
| `cel_threshold`, `cel_edge` | where the shading edge falls and how soft it is |
| `deep_threshold` | position of a second dark step; None turns it off |
| `soft_range` | range mapped to shadow and light in continuous shading |
| `ambient` | ambient color multiplied into every shadow |
| `light_color`, `highlight` | highlight color and strength factor |
| `key_tint` | key light color multiplied into lit faces, default (1, 1, 1), magenta for neon |
| `cast_strength`, `cast_blur` | density and blur px of cast shadows |
| `sss` | reddish bleed at the shading edge of skin |
| `rim`, `rim_color` | rim light strength and color |
| `line_scale` | outline weight factor; 0 is no line |
| `line_tint`, `ink` | share of local color in the line color, and the ink color |
| `painterly` | dict of brush pass arguments; None is no brush pass |
| `post` | list of post effect steps `[(name, argument dict), ...]` |

| Material | Use | Character |
|---|---|---|
| `matte` | ordinary things | neutral shadow |
| `skin` | skin | reddish shadow, bleed at the edge, faint highlight |
| `hair` | hair, fur | dark cool shadow |
| `cloth` | cloth | cool shadow |
| `gloss` | metal, glass, wet surfaces | strong highlight |
| `flat` | flat details | no shadow |

## Brush pass

```python
finish(img, style="painterly", normals=None, focus=None, seed=0)   # applies the brush pass and post effects at once
paint(ref, normals=None, focus=None, seed=0, radii=None, scale=1.0, threshold=14, ground=None,
      relief=0.15, jitter=5, stroke_length=1.0, fidelity=0.75, detail_blend=0.40)
```

- `paint` repaints the reference picture from large brushes to small ones (after Hertzmann 1998)
- `scale` multiplies all brush radii; smaller is finer
- With `normals` the strokes run around the forms
- `focus` is a map of the areas to paint finely; `Part.focus` passes it automatically
- `fidelity` is how strongly strokes that stray far from the reference are pulled back
- `relief` is the strength of paint thickness shading; 0 is flat paint
- `ground` is the color of the underpainting; unset, a warm color based on the picture's mean

## Post effects

Applied in order as `post.apply(img, [(name, arguments), ...], seed)`.

| Effect | Main arguments | Use |
|---|---|---|
| `bloom` | threshold, radius, strength | light glowing around bright areas |
| `diffusion` | radius, strength | soft diffuse glow over the whole picture |
| `grade` | contrast, saturation, shadows, highlights, gamma | contrast, saturation, tint of lights and darks |
| `grain` | amount | film grain |
| `paper` | amount, scale | paper grain |
| `canvas_weave` | amount, period | canvas weave |
| `vignette` | strength, color | darker edges |
| `edge_darken` | amount, radius | watercolor pooling at edges |
| `watercolor` | wobble, flatten, bleed, pigment, hue_drift, granulation, wet_edge, lighten, border | transparent watercolor: details simplified into paint areas, wobbling edges, blooms, uneven density, pigment granulation, pooling at edges, a white paper border |
| `pencil` | spacing, length, strength, smudge, contour, paper_color, graphite | pencil drawing: hatching in 3 directions by value step, smudged graphite, drawn lines found by local contrast and kept as one pencil line |
| `posterize` | levels, chroma_step, keep_dark | screen-print color fields: value and color axes cut into coarse steps and turned into flat inks; areas of different hue do not mix; thin lines become one dark ink |
| `halftone` | cell, angle, strength, start | printed halftone dots in dark areas, larger dots where darker |
| `chromatic` | shift | lens chromatic aberration, red outward and blue inward |

## Backdrops

| Function | Result |
|---|---|
| `backdrop.studio(h, w, center_color, edge_color, center, radius)` | a studio wall lighter in the middle |
| `backdrop.wash(h, w, colors, seed, scale, contrast)` | a ground of 3-4 colors bleeding into each other |
| `backdrop.bokeh(img, count, radius, colors, alpha, seed, region)` | out-of-focus light discs |
| `backdrop.light_beam(img, angle, width, strength, color)` | diagonal beams of light |

## Review tools

| Function | Use |
|---|---|
| `review.preview(img, path, max_side=1200)` | saves a reduced copy |
| `review.zoom(img, path, box, scale=2.0)` | saves an enlarged area |
| `review.sheet(images, path, columns, height)` | a comparison sheet of several pictures |
| `review.stats(img)` | mean brightness, contrast, share of clipped white and black, saturation, amount of detail |

- Example `stats` thresholds: contrast 0.25 or more, clipped white 0.25 or less, clipped black 0.35 or less

## Tuning constants

The engine constants are collected in `codepaint/config.py`. Tune mask samples, inflation grid size, minimum line weight, default brush radii and the like in that file.
