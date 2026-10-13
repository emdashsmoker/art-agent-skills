# Engine API

Public functions of the `scripts/codepainter/` package. Coordinates are pixels, with x positive to the right and y positive downward. Colours are `"#rrggbb"` strings or RGB in the 0-1 range. Masks are float32 arrays (0-1) the size of the canvas.

## Contents

- Painting (canvas)
- geometry (curves)
- shading (light and shade)
- color (colour)
- styles (styles)
- fx (finishing)
- objects (boxes and cylinders)
- backdrop (backgrounds)
- scenery (natural things)
- sets (backgrounds for figure scenes)
- painterly (brushwork)

## Painting

`from codepainter import Painting`

| Call | Role |
|---|---|
| `Painting(width, height, background="#ffffff")` | creates one colour layer and one line layer |
| `.mask(curve)` | turns a closed curve into an anti-aliased mask |
| `.fill(mask, color, opacity=1.0, mode="normal")` | paints a colour through a mask; mode is normal, multiply, screen, add, overlay or soft_light |
| `.part(mask, color)` | fills an opaque part and erases the lines it covers |
| `.stroke(path, width, color, taper=(0.25, 0.35), tip=0.08, opacity=1.0, layer="line", clip=None)` | one pen stroke with pressure |
| `.outline(curve, width, color, shade_side=(0.6, 0.7), contrast=0.5, closed=True)` | outline that grows heavier on the side away from the light |
| `.outline_mask(mask, width, color, shade_side, contrast=0.5, keep=None)` | outline along a mask's edge, for forms joined from several parts |
| `.erase_lines(mask)` | erases lines inside a mask |
| `.flatten(line_opacity=1.0)` | HxWx3 image of colour and lines combined |
| `.line_art(paper="#ffffff")` | image of the line layer alone |
| `.snapshot(name)` | records the current state as a process step (kept in `.stages`) |
| `.save(path, image=None)` | saves a PNG; without image it saves the flatten result |

- `.color` is an HxWx3 array and can be edited directly
- A number as the `width` of `stroke` thins both ends through `taper`
    + An array as long as the point count sets the width directly
- `layer="line"` is for outlines that a style may restyle or drop
    + `layer="color"` is for marks that belong to the picture itself, such as lashes, lip lines and hair strands
- The `mask` of `fill` is cut by multiplication
    + Example : `painting.fill(shadow * part_mask, color)` paints only inside the part
- Hundreds of small polygons (windows, snowflakes, tiles) are rasterised into one mask at once with `raster.fill_many(polygons, painting.shape)`

## geometry

`from codepainter import geometry as geo`. Every function returns an (N, 2) array.

| Function | Role |
|---|---|
| `smooth(points, closed=False, corners=())` | smooth curve through the control points; corners are point numbers kept angular |
| `ellipse(center, rx, ry, angle=0.0)` | ellipse |
| `arc(center, rx, ry, start, end)` | open arc, angles in radians |
| `bent_line(start, end, bend=0.0)` | line bowed to one side; bend is the bow as a share of the length |
| `lock(root_a, root_b, tip, bend=0.0, belly=0.0)` | closed form with a pointed tip (hair lock, leaf, flame, cloth fold) |
| `needle(start, end, width)` | lens shape pointed at both ends (highlight streak, grass blade, glint on water) |
| `tube(path, left, right=None, caps=(True, True))` | tube of changing width (limbs, tails, branches, roads) |
| `symmetric(profile, axis_x)` | turned form made by mirroring one contour about a vertical axis (bottle, bowl, fruit) |
| `quad_map(quad)` | perspective mapping that carries 0-1 coordinates onto a wall or floor quad |
| `grid_cells(columns, rows, margin, inset)` | 0-1 coordinate grid for windows and tiles |
| `rounded_rect(x0, y0, x1, y1, radius)` | rectangle with rounded corners (screen, key, button) |
| `Oblique(origin, across, back, up, scale)` | oblique projection frame with `.place(points3)` and `.box(x, y, z, width, depth, height)` |
| `transform(points, scale, angle, translate, pivot)` | scale, rotate, move |
| `offset(path, distance)` | parallel shift along the normal |
| `wobble(path, amplitude, seed)` | slight shake imitating an unsteady hand |
| `subpath(path, start, end)` | part of a path over a 0-1 span |
| `resample(path, count)` | resample at even spacing |
| `lerp(a, b, t)` | blend of two points or two paths |

- With a positive `bend`, a line going down bows toward the left of the screen and a line going right bows downward
    + A negative value bows to the other side
    + When the sign is confusing, check in a render and flip it
- `left` and `right` of `tube` are lists of half widths spaced evenly along the path
    + `left` is the screen left of a path going downward
- The quad of `quad_map` runs top-left, top-right, bottom-right, bottom-left
    + It cannot be used on a quad that closes to a point; the far edge needs a length
- Use `symmetric` for left-right symmetric forms, or mirror one side's control points as `(2 * centre_x - x, y)`

## shading

`from codepainter import shading as sh`. The default light is `DEFAULT_LIGHT = (-0.55, -0.62, 0.56)` (upper left, toward the front).

| Function | Role |
|---|---|
| `inflate(mask, bevel=None, smoothing=0.18)` | height map of the inflated mask; without bevel the form is fully rounded |
| `lighting(mask, light, bevel=None, depth=1.0, height=None)` | Lambert lighting value (-1 - 1) |
| `shadow_from_light(lit, threshold=0.25, softness=0.02)` | shadow mask where the lighting value falls below the threshold |
| `cast_shadow(occluder, receiver, offset, softness=0.0)` | shadow a part in front throws onto the part behind |
| `rim(mask, direction, width, softness=0.0)` | edge band facing a given direction (rim light, edge highlight) |
| `occlusion(occluder, receiver, radius)` | soft darkness where parts touch |
| `ground_shadow(mask, drop, squash, lean, softness)` | flat shadow an object throws on a table or floor |
| `edge_band(mask, width, shade_side, contrast)` | band along a mask's edge, the inner calculation of `outline_mask` |
| `melt(mask, radius)` | melts grooves and corners of a joined mask into one mass |
| `linear_ramp(shape, start, end)` | straight gradient that is 0 at start and 1 at end |
| `radial_ramp(shape, center, radius)` | round gradient that is 0 at the centre and 1 at the radius |
| `blur(image, sigma)` | Gaussian blur |
| `shift(mask, dx, dy)` | moves a mask |
| `smoothstep(low, high, value)` | smooth step function |

- `bevel` is the distance (pixels) over which the surface keeps rising from the edge
    + Leave it out for balls, faces and fruit; for flat-topped forms like a trunk or a slab use 20-30% of the width
- Raise `smoothing` to 0.4 or more when ridge marks show on a pointed form
- The x and y of `light` point toward where the light comes from on the screen
    + An upper-left light has negative x and y; z is how frontal it is

## color

`from codepainter import color`

| Function | Role |
|---|---|
| `rgb(value)` | turns a string or tuple into an RGB array |
| `mix(a, b, amount)` | mixes two colours |
| `adjust(color, hue=0.0, saturation=1.0, value=1.0)` | hue rotation, saturation and value factors |
| `shadow_of(color, tint, depth=1.0)` | shadow colour (violet-leaning multiply, saturation raised) |
| `light_of(color, tint, amount=0.5)` | highlight colour (moved toward warm white) |

## styles

`from codepainter.styles import get_style, shade_form, paint_part, line_color, finish, flat_version`

| Function | Role |
|---|---|
| `get_style(name, **overrides)` | returns the `anime`, `illust` or `painterly` preset, values can be overridden |
| `paint_part(painting, curve, color, style, light, line_width=2.5, bevel=None, shade=True, **shading)` | finishes one part (mask, base colour, shading, outline) in one call, returns the mask |
| `shade_form(painting, mask, base, style, light, bevel=None, depth=1.0, threshold=None, shadow_color=None, height=None, terminator=None)` | applies the style's form shading to a part already painted |
| `line_color(style, fill_color, ink)` | outline colour matched to the part colour |
| `finish(painting, style, seed=0, importance=None, **brush_options)` | finishing pass per style, returns the finished image |
| `flat_version(style)` | the style with light switched off, for checking base colours |
| `gloss(painting, mask, light, size=0.16, reach=0.45, color, opacity, softness)` | glossy spot on the lit side of a round part |

- Raising `threshold` enlarges the shadow area
    + The default is the style's `shadow_threshold`
- `depth` is a factor that exaggerates volume

## fx

`from codepainter import fx`. Input and output are HxWx3 images.

| Function | Role |
|---|---|
| `fbm(shape, scale=1.0, octaves=4, seed=0, stretch=(1.0, 1.0))` | cloud-like noise (0-1); stretch is (vertical, horizontal) elongation |
| `glow(image, radius, strength)` | overall diffusion glow |
| `bloom(image, threshold, radius, strength)` | light bleeding out of the bright parts only |
| `grade(image, contrast, saturation, shadows, highlights, gamma)` | contrast, saturation, tint of lights and darks |
| `paper(image, amount, seed)` | paper texture |
| `grain(image, amount, seed)` | film grain |
| `vignette(image, strength)` | darkens the edges |
| `doomer(image, seed=0, strength=1.0)` | doomer mood : drained colour, teal shadows, faded blacks, vignette, grain, colour kept only in warm lights |
| `warm_lights(image)` | how much each pixel is a warm light (street lamp, lit window), 0-1 |
| `stage_sheet(stages, path, columns=3)` | gathers the process steps on one sheet |

## objects

`from codepainter import objects`

| Function | Role |
|---|---|
| `paint_box(painting, faces, color, style, tones, line_width=2.2, top_color=None)` | paints an `Oblique.box` result with a value per face, returns a dict of face masks |
| `paint_cylinder(painting, center, radius, height, color, style, light, squash=0.36, hollow=None)` | cylinder seen from above; `hollow` is the colour inside an open top |

## backdrop

`from codepainter import backdrop`. Draws straight onto the Painting's colour layer.

| Function | Role |
|---|---|
| `gradient(painting, start_color, end_color, start=None, end=None)` | straight gradient background |
| `mottle(painting, color, amount, scale, seed)` | blotchy variation that takes the machine-made look off flat backgrounds |
| `glow(painting, center, radius, color, opacity)` | soft pool of light |
| `window_light(painting, corner, size, slant, panes, bar, color, opacity, softness)` | window light cast on a wall |
| `bokeh(painting, colors, count, radius, opacity, seed)` | out-of-focus light discs |

## scenery

`from codepainter import scenery`

| Function | Role |
|---|---|
| `ridge(shape, base_y, relief, roughness, seed, tilt)` | silhouette of a mountain range or hill (closed polygon) |
| `clouds(shape, coverage, scale, seed, stretch, softness, band)` | cloud mask |
| `conifer(base, height, width, tiers, seed)` | list of polygons for one conifer |
| `blades(region_box, count, length, seed, lean)` | list of (root, tip, bend) for grass blades |
| `reflect(painting, waterline, depth, ripple, darken, tint, seed)` | reflection on water |
| `noise_line(count, roughness, octaves, seed)` | 1D fractal noise |
| `puffs(painting, center, width, height, count, seed, flat_base)` | (mask, list of lump masks) of a cumulus cloud or bush |
| `foliage(painting, center, width, height, count, seed)` | (mask, list of leaf clump masks) of a tree crown |
| `scatter(region_box, count, seed, near_scale, far_scale)` | list of (x, y, size) that grows larger nearer the viewer |
| `skyline(shape, base_y, heights, widths, seed)` | silhouette of a distant city |
| `street_wall(base_near, vanishing, near, far, height)` | quad of a building wall along a one-point perspective street |
| `windows(painting, quad, columns, rows, lit_colors, dark, lit, margin, inset, seed)` | grid of windows on a wall, returns the mask of the lit ones |
| `panel_facade(painting, quad, floors, bays, seed, lit, wall, shade, balcony_every, stairs_every, line_width)` | one face of a panel apartment block : seams, windows, balconies, stairwells; returns the lit window mask |
| `bare_tree(painting, base, height, seed, color, birch, lean, depth, width)` | leafless winter tree; `birch=True` gives a white-trunked birch |
| `snowfall(painting, count, seed, size, color, opacity, keep_clear)` | falling snow, cleared over the `keep_clear` mask (faces) |
| `wire(start, end, sag, count)` | path of a cable sagging between two points |
| `sodium_lamp(painting, foot, height, side, ground, color)` | sodium street lamp with a bent arm and a pool of light on the ground, returns the lamp head position |

## sets

`from codepainter import sets`. Full backgrounds for figure scenes; usage is in `references/clothing-and-scenes.md`.

| Function | Role |
|---|---|
| `beach(painting, style, horizon, seed)` | midday sea and sandy beach |
| `bedroom(painting, style, floor, seed)` | evening bedroom wall, window light, curtain, wooden floor |
| `office(painting, style, floor, seed)` | towers beyond a glass wall, potted plant, carpet |
| `night_street(painting, style, horizon, seed)` | street at night, lit windows, street lamps, wet road |
| `cafe(painting, style, floor, seed)` | cafe wall, city through the window, pendant lamps, tiled floor |
| `park(painting, style, horizon, seed)` | midday park, two rows of trees, lawn, path |
| `panel_block(painting, style, horizon, seed, lamp, lit)` | doomer block yard, panel apartment blocks, bare trees, sodium lamp, snow |
| `light_figures(painting, figures, info, style)` | gives figures the scene's ambient light and rim light |

- Background functions return `SetInfo(horizon, ground, grade, ambient, rim)`
- `SETS` is a dict from name to function

## painterly

`from codepainter import painterly`

- `repaint(source, seed=0, importance=None, ground=None, detail=1.0, bristle=1.0, impasto=1.0, canvas=1.0, layers=BRUSH_LAYERS)`
    + Returns the source repainted stroke by stroke
    + `finish` calls it automatically for painterly, so direct calls are needed only for fine tuning
