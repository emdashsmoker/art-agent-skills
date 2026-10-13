# Engine functions

All coordinates and sizes are in canvas units (canvas width = 1000). Colours are `"#RRGGBB"` strings.

## Contents

- Creating a canvas
- Placing sub-pictures
- Camera projection
- 3-D sculpting
- Poses and framing
- Clothes
- Skirts and dresses
- Several people
- Turning the head
- Hair and face templates
- Mood layer
- Place helpers
- Making curves
- Making masks
- Processing masks
- Painting
- Drawing lines
- Output
- Colour tools

## Creating a canvas

```python
Art(style, width_px=1024, aspect=1.25, light=(-0.45, -0.60, 0.66), seed=7,
    paper="#FFFFFF", view=None)
```

| Argument | Meaning |
|---|---|
| `style` | `STYLES["anime"]`, `STYLES["illust"]`, `STYLES["painterly"]` |
| `width_px` | Output width in pixels. 512 for previews, 1024 or more for finals |
| `aspect` | Height / width. 1.25 for a portrait, 1.0 square, 0.62 for a landscape |
| `light` | Direction the light comes from, `(x, y, z)`. Positive x is right, positive y is down, positive z is toward the viewer |
| `seed` | Random seed. The same value gives the same picture |
| `view` | `(centre x, centre y, zoom)`. Changes the composition without touching coordinates |

Attributes: `art.width`, `art.height` (pixels), `art.units_high` (units), `art.rng` (random generator), `art.style`,
`art.grade` (mood layer, default `None`; see the mood layer in `references/styles.md`).

## Placing sub-pictures

```python
with art.place(at=(x, y), scale=1.0, angle=0.0, flip=False, pivot=(0, 0)):
    draw_something(art)        # every coordinate and size in here is local
```

| Argument | Meaning |
|---|---|
| `pivot` | Reference point in local coordinates |
| `at` | Canvas position where the reference point lands |
| `scale` | Scale factor. Also converts something drawn in metres to canvas units |
| `angle` | Rotation in degrees. Positive is clockwise on screen |
| `flip` | Mirror left-right. Turns a right hand into a left hand |

- Blocks can be nested (a head inside a body, a hand at the end of an arm)
- Masks made inside a block can be used outside it as they are
- Line width rules
    + A line with an explicit width is transformed like any other size
    + Lines without a width and outlines get thinner when scaled down and do not thicken when scaled up
    + Lines inside a block never get thinner than 1.3 units

## Camera projection

```python
from atelier import Camera
camera = Camera(eye=(0.06, -0.80, 0.66), target=(0.0, 0.36, 0.12), focal=900, center=(500, 400))
curve = camera.project(points_3d)          # (N, 3) -> (N, 2) canvas coordinates
```

- World coordinates: x to the right, y away from the viewer, z up. Metres are recommended
- The camera at `eye` looks at `target`; `target` lands at the canvas point `center`

| Argument or function | Meaning |
|---|---|
| `focal` | Canvas length of 1 unit seen at distance 1. Large is telephoto, small is wide angle |
| `camera.project(points)` | 3-D points to canvas coordinates |
| `camera.depth(points)` | Distance along the line of sight |
| `camera.scale_at(point)` | Canvas length of 1 unit at that point. Pass it to `art.place(scale=...)` |
| `camera.rays(canvas_points)` | Directions of the rays through canvas points |
| `camera.to_world(vector)`, `camera.to_screen(vector)` | Convert between screen directions (x right, y down, z toward the viewer) and world directions |

- To show a table top below eye level, put the z of `eye` higher than the z of `target`
- Helpers that make 3-D points (`frame`, `slab`, `disc`, `on_plane`, `hull`) are in `examples/desk.py`

## 3-D sculpting

`atelier.sculpt` finds 3-D forms with one ray per pixel and makes masks and light for painting. For a whole human body use `atelier.mannequin` (the 3-D mannequin in `references/figure.md`). `mannequin.build(scene, pose, physique=FEMALE or MALE)`, `mannequin.dress(scene, marks, group, regions, thickness, smooth)`.

| Form | How to make it |
|---|---|
| `Sphere(center, radius)` | Sphere |
| `Ellipsoid(center, radii, rotation)` | Ellipsoid |
| `Capsule(a, ra, b, rb)` | Rod with round ends. Each end can have its own radius |
| `RoundBox(center, half, rounding, rotation)` | Box with rounded edges |
| `Offset(shape, amount)` | Another form grown by a fixed thickness. Clothes, shells |
| `HalfSpace(point, normal)` | Everything on one side of a plane. For carving only. `carve(HalfSpace(p, n))` keeps the side `n` points to |
| `Intersection(*shapes)` | Where forms overlap. For carving only. Two half-spaces make a V wedge |
| `hanging_cloth(scene, group, top_from, top_to, drop, rng)` | Cloth hanging from its top edge in vertical folds |

```python
scene = sculpt.Scene()
scene.add(shape, group="clay", blend=0.0, anchor=None, reach=None)
result = sculpt.render(art, camera, scene, step=2)
sculpt.paint(art, result, "clay", color, tint=shadow, deep=crease, sheen=0.3)
```

- Forms in the same `group` melt together over the `blend` width. With an `anchor`, nothing farther than `reach` from that point melts
- `scene.carve(shape, group, blend)` carves a shape out of the forms added to that group so far. Necklines, holes, grooves
- `sculpt.paint()` paints base colour, form shadow, cast shadow, crease darkness, sheen and outline in one call and returns the mask
- Orientation matrices: `rotation(turn, lean, tilt)` or `facing(up, front)`
- Results for painting over afterwards: `result.lit`, `result.shadow`, `result.ao`, `result.at(point)`, `result.visible(point)`, `result.disc(center, normal, radius)`
- One scene takes 10-40 seconds at 1280 px
- Forms large enough to surround the camera (a wide floor) are drawn too
- Landmarks from `mannequin.build()`: `chin`, `head_up`, `head_frame`, `skull`, `neck`, `chest_marks`, `navel`, `pelvis`, `pelvis_frame`, `chest`, `chest_frame`, left and right `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle`, plus `forms`, `form_sides`, `leg_radii`, `arm_radius`
- `mannequin.dress(..., side=1 or -1)` grows the limb forms of one side only

## Poses and framing

`atelier.staging` (pose presets and camera framing in `references/wardrobe.md`).

```python
from atelier.staging import POSES, frame, pose_for
staging = pose_for("walking", physique, bust=0.95)      # pose, supports, hand_at, hand_behind_head
camera = frame(marks, physique, shot="knee", azimuth=30, elevation=5, aspect=1.5)
```

## Clothes

`atelier.wardrobe` (clothes principles and the clothes list in `references/wardrobe.md`). A clothes function adds forms to the scene and returns a list of things to paint.

```python
from atelier import wardrobe as w
items = w.tee(scene, marks, physique) + w.jeans(scene, marks) + w.shoes(scene, marks, pose, physique, "sneaker")
# items: (group, colour, shadow) or a function(art, result) called after rendering
```

## Skirts and dresses

`atelier.drape` (skirts and dresses, and wind, in `references/wardrobe.md`).

```python
from atelier import drape as d
items = d.sundress(scene, marks, wind=(0.35, -0.06, 0.05)) + d.scarf(scene, marks, wind=(0.35, -0.06, 0.05))
body = d.body_profile(marks, top, front, length, wind)  # table of radii to the melted skin [row, direction] over height t
profile = d.flare_profile(body, length, flare=0.30, hip_drop=0.145, ease=d.WAIST_EASE, press=None)
skirt = d.Flare(top, up, front, profile, length, folds=9, fold_depth=0.014, pleats=False, wind=(0, 0, 0),
                obstacles=[(point, radius), ...], fold_from=0.10)   # an open shell you build yourself
d.ribbon(scene, group, points, across, half_width, thickness)    # a flat band (scarf tails)
```

| Name | What it does |
|---|---|
| `body_profile(...)` | Body girth measured from the wind-swayed centre. A convex hull joins the two legs |
| `flare_profile(...)` | Radius table with waist ease, hip following and A-line flare applied, plus a table of how far hands may push in |
| `Flare` | Open shell that follows the table. Folds, wind, pull-in at the hands |
| `Ribbon`, `ribbon()` | Band of thin boxes chained along a path and a width direction. Added in pieces of 6 segments |

`Surface(marks, regions)` in `atelier.wardrobe` is a surface where only the chosen regions are melted, the same way rendering melts them. Put it in the forms list of `around()` and `strap()`.

## Several people

```python
from atelier.staging import pair_for, placed
a, b = pair_for("holding_hands", physique_a, physique_b)        # Staging for both
art = figure_study.draw_cast(style, width, setting, [figure_study.Actor(sitter_a, pose_a, extras_a), figure_study.Actor(sitter_b, pose_b, extras_b)])
```

- Forms added inside a `Scene.named(prefix)` context get the prefix on their group names
- `Render.within(prefix)` is a render result that shows only that person's groups under their original names
- `Scene.distance(points, group)` is the distance to a group's surface, melted exactly as rendered

## Turning the head

`atelier.turn` (head turning in `references/figure.md`).

| Function | What it does |
|---|---|
| `FaceDepth(axis, centre_y, half_width, half_height, depth, nose, nose_height, nose_spread)` | Depth model of one head drawing |
| `surface(points, turn, face)` | Points on the face moved to their turned positions |
| `outline(points, turn, face, keep_until, chin_y)` | The face outline moved to its turned position |
| `squeeze(point, turn, face)` | How much the face narrows sideways at that point |
| `clamp(turn)` | Limits the angle to ±35 degrees |

## Hair and face templates

`examples/head_style.py` (hair and face templates in `references/figure.md`).

| Name | What it does |
|---|---|
| `HeadLook(hair, hair_colour, eyes, brows, lips, eye_colour, earrings, hat, cigarette)` | Hair style, hair colour, eye shape, brows, lips, eye colour, earrings or earphones, hat, cigarette. Unset fields take the head's default |
| `head.styled(look)` | Context that draws a head module (`portrait`, `portrait_male`) in that style and colour |
| `head.HAIR_STYLES` | Hair style names of that head module |
| `hair_tones(colour)`, `eye_tones(colour)` | Shading tones from a name or `"#RRGGBB"` |
| `portrait.draw(style, width, look)` | A bust with that face |
| `figure_study.Sitter(..., look=look)` | The face of a full-body figure |
| `outfits.Look(..., face=look)`, `outfits.Duo(..., faces=(a, b))` | Faces in the combination examples |
| `head.draw_head_back(art)` | A head seen from behind: back hair, hat, smoke |

Props in `examples/head_props.py` (props in `references/figure.md`).

| Name | What it does |
|---|---|
| `PropPlaces(skull, brim, mouth, ears, cable_join, cable_end, back_smoke)` | Prop positions for one head (in that head's drawing units) |
| `draw_beanie(art, tilt, places, under)` | Beanie. `under` is the mask that receives the hat's shadow |
| `draw_cigarette(art, tilt, root, droop=24)` | A lit cigarette. Returns the ember tip's coordinates |
| `draw_smoke(art, tilt, start, drift=40)` | Smoke that rises and sways |
| `draw_earphones(art, tilt, places, in_sight)` | Wired earphones. `in_sight(side)` says whether that ear shows |

`tilt` is a function that moves points in drawing units to the canvas. Pass the head module's `tilt`, or `np.asarray` in a still life.

## Mood layer

`atelier.mood` (the mood layer in `references/styles.md`).

| Name | What it does |
|---|---|
| `art.grade = doomer` | After the finish: cold, faded colour, vignette, film grain |
| `vignette(shape, start, amount)` | Multiplier that falls off toward the corners |
| `film_grain(shape, amount, size_px, rng)` | Clumped grain |
| `GRADES` | Moods by name |

## Place helpers

`examples/scenes.py` (places in `references/wardrobe.md`).

| Name | What it does |
|---|---|
| `panel_block(art, box, floors, columns, balconies, lit, haze, haze_colour)` | A prefab apartment block seen face on: panel joints, window grid, lit windows and their glow, balconies, roof |
| `bare_tree(art, base, height, colour, depth, spread, angle, width)` | A leafless tree. Branches split in two or three |
| `snowfall(art, result=None)` | Falling snow. Uses its own seed, so the flakes stay put when the scene changes. Puts the flakes in focus so they survive the painterly style |
| `keep_fine_lines(art)` | Finds thin lines darker than their surroundings and puts them in focus, so painterly brushwork does not erase wires and twigs |
| `looking_back(camera)` | -1 when the camera looks from behind the figure, +1 from the front |
| `ground_edge(art, camera, reach, height=0)` | Canvas y of the floor's far edge. With `height`, the height of a wall standing on that edge |

## Making curves

A curve is an `(N, 2)` array. A control point is `(x, y)` or `(x, y, True)`; a true third value makes it a corner.

| Function | Result |
|---|---|
| `spline(points, closed=False, samples=16)` | Smooth curve through the control points. Bends sharply only at marked corners |
| `ellipse(cx, cy, rx, ry, angle=0)` | Closed ellipse |
| `symmetric(half_points, axis_x)` | Control points with the half mirrored and joined left-right |
| `mirror(points, axis_x)` | Control points mirrored left-right |
| `rotate(curve, degrees, center)` | Rotates a curve. Positive is clockwise on screen |
| `resample(curve, step)` | Redistributes points along a curve at an even spacing |
| `tube(points)` | `(N, 3)` array smoothly joining `(x, y, width)` control points. Usually use `art.tube()` instead |

For a straight polygon use `np.array([(x, y), ...], float)` as it is.

## Making masks

A mask is a 0-1 float array of size `(height, width)`. Multiplying gives the intersection, `np.maximum` the union, `1 - mask` the inverse.

| Function | Result |
|---|---|
| `art.shape(curve)` | Inside of a closed curve |
| `art.shapes(curves)` | Many closed curves at once. Use it when there are many: windows, flowers, tiles |
| `art.tube(points)` | Round band through `(x, y, width)` control points. Limbs, fingers, stems, handles |
| `art.brush(curve, width, taper="both")` | A stroke along a curve |
| `art.everywhere()` | The whole picture |
| `art.ramp(start, end)` | Linear gradient. 0 at start, 1 at end |
| `art.blob(center, radius)` | Round glow, 1 at the centre and 0 at the radius |
| `art.noise(cell, octaves=3)` | Smooth random pattern in 0-1. `cell` is the blob size |

## Processing masks

| Function | Result |
|---|---|
| `art.feather(mask, radius)` | Softens the edges |
| `art.grow(mask, amount)` | Expands the edges outward. Negative shrinks |
| `art.move(mask, dx, dy)` | Shifts. Used for cast shadows and back-light rims |
| `art.threshold(field, level, softness=0.05)` | Turns a pattern into a mask. Used for clouds |

Common combinations:

```python
cast = art.move(caster, 6, 14) * receiver            # cast shadow
rim = figure * (1 - art.move(figure, -5, 2))         # band along the right edge (back light)
band = mask * (1 - art.move(mask, 0, 9))             # band along the top edge (eyelid shadow)
fade = mask * art.ramp((0, 400), (0, 900))           # darker toward the bottom
```

## Painting

| Function | Action |
|---|---|
| `art.part(shape, color, shade=True, outline=True, bulge=None, shadow_tint=None, line_color=None, line_width=None)` | Adds a part. Base colour, form shadow and outline in one call; returns the mask |
| `art.paint(mask, color, opacity=1.0)` | Paints on the base-colour layer |
| `art.shadow(mask, tint=None, opacity=1.0)` | Applies a multiply colour on the shadow layer |
| `art.light(mask, color="#FFFFFF", opacity=1.0)` | Applies a screen colour on the light layer |
| `art.form_shadow(mask, bulge=None, tint=None, clip=None)` | Applies the form shadow alone. `clip` limits where it falls |
| `art.erase_line(mask)` | Erases lines under the mask. Makes two parts look joined |
| `art.shade_by(mask, lit, tint)` | Shades in the style's manner from a light value (1 bright, 0 or below dark) |
| `art.ink(alpha, color)` | Lays a prepared line mask on the line-art layer |
| `art.line_color(fill)` | The style's line colour for a part of that colour |
| `art.mark(curve, color, width, taper="both", opacity=1.0)` | A stroke on the base-colour layer. Visible in every style |
| `art.blur(radius)` | Blurs everything drawn so far. Pushes a background back |
| `art.focus_on(mask)` | Marks a focus area |

The `shape` of `part()` takes either a curve or a mask.

Two ways of `bulge`:

| Value | Volume | Use |
|---|---|---|
| Omitted | Balloon-like volume. A circle becomes a sphere, a band a cylinder | Fruit, limbs, bodies, clouds, tree crowns, bottles |
| A radius | Flat volume rounded only at its edges | Clothes, faces, walls, cloth, ground |

## Drawing lines

| Function | Action |
|---|---|
| `art.line(curve, color=None, width=None, taper="both", opacity=1.0)` | A stroke on the line-art layer. Skipped in styles without line art |
| `art.outline(mask, color=None, width=None, clip=None)` | Outline of a mask. `clip` keeps only part of it |

`taper` values:

| Value | Width change |
|---|---|
| `both` | Thin at both ends |
| `start` | Thin at the start |
| `end` | Thin at the end |
| `none` | Even |

## Output

| Function | Action |
|---|---|
| `art.save(path, stage="final", downscale=1)` | Saves one stage as an image |
| `art.save_stages(path)` | Saves the 5 stages side by side |
| `art.compose(stage)` | Returns one stage as a float RGB array |

| `stage` | Contents |
|---|---|
| `line` | Underdrawing on paper. Line art plus colour borders shown as pencil lines |
| `flat` | Base colours and lines |
| `shade` | Shadows added |
| `light` | Light added |
| `final` | The style's post-processing, then `art.grade` |

## Colour tools

| Function | Result |
|---|---|
| `mix(color_a, color_b, amount)` | Mix of two colours |
| `adjust(color, hue=0.0, saturation=1.0, value=1.0)` | Hue shift, saturation and value multipliers |
| `rgb(color)` | RGB array in 0-1 |
