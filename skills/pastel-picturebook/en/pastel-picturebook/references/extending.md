# How to extend

How to add elements that settings alone cannot express, ordered by difficulty

## Contents

- Adding props (hook modules)
- Basic functions
- The scene object
- New expression and look presets
- New hair styles
- New outfits
- New built-in accessories
- New interior items
- New styles
- New held objects
- New subjects
- New poses and body types
- New scene props and hand target points

## Adding props (hook modules)

- Two functions of the module passed with `--extras <file>.py` are called at fixed points
    + `after_background(scene)`: right after the background. For elements behind the figure (a window, the moon, plants)
    + `after_figure(scene)`: right after the figure. For elements in front of the figure (glasses, earrings, petals)
- The core files are not touched, so existing pictures are not affected
- Glasses, hats, scarves and bags are available directly as built-in accessories (`accessories` in the spec, `references/spec.md`). The glasses example below shows how to write a hook

```python
"""Round glasses example."""
import numpy as np
from raster import ellipse, fill, over, rgb, screen, smooth, stroke

FRAME_COLOR = "#2A2230"

def after_figure(scene):
    fig, unit = scene.fig, scene.px(1.0)
    centers = [fig.points["eye_far_center"], fig.points["eye_near_center"]]
    rings = [ellipse(center + [0, 0.03 * unit], 0.30 * unit, 0.27 * unit, 64) for center in centers]
    for ring in rings:
        screen(scene.image, rgb("#FFFFFF"), fill(scene.size, ring), 0.10)
        over(scene.image, rgb(FRAME_COLOR), stroke(scene.size, np.vstack([ring, ring[:1]]), 0.022 * unit))
    inner_far = rings[0][np.argmin(np.linalg.norm(rings[0] - centers[1], axis=1))]
    inner_near = rings[1][np.argmin(np.linalg.norm(rings[1] - centers[0], axis=1))]
    bridge = smooth([inner_far, 0.5 * (inner_far + inner_near) - [0, 0.04 * unit], inner_near])
    over(scene.image, rgb(FRAME_COLOR), stroke(scene.size, bridge, 0.020 * unit))
```

- Prop positions come from reference points already computed
    + `fig.points`: `eye_far_center`, `eye_near_center`, `nose_tip`, `pendant`, `hair_band`
    + `fig.shapes`: closed outlines such as `face`, `skin_body`, `cloth`, `hair_near`, `hair_far`, `hair_back`, `upper_lip`, `lower_lip`
    + `fig.paths`: open curves such as `jaw`, `mouth_line`, `cloth_neckline`, `collar_r`
- To place something in head coordinates, use `fig.head_frame.project([(x, y, z)])`
    + Ear position example: `(-1.0, 0.25, -0.1)`
- `pose.mirror` flips the finished picture, so props flip with it

## Basic functions

`scripts/raster.py`. Images are float32 RGB in 0-1. Coordinates are pixels (x, y)

| Function | Use |
|---|---|
| `smooth(points, closed=False)` | Smooth curve through control points |
| `ellipse(center, rx, ry, count, angle_deg)` | Ellipse outline |
| `join(a, b, ...)` | Joins curves. The joints stay as corners |
| `taper(count, start, end, peak_at)` | Width profile of a stroke |
| `fill(size, polygon)` | Mask of a closed outline |
| `stroke(size, path, widths)` | Mask of a stroke with varying width |
| `over(image, color, mask, opacity)` | Normal compositing |
| `multiply(...)`, `screen(...)` | Darkening and lightening composites |
| `blur(field, sigma)`, `shift(mask, dx, dy)` | Blur, translation |
| `noise(size, cell, seed)` | Smooth noise |
| `lambert(mask, light, sigma)` | Light amount from an inflated shape |

- The drawing order is always curve, mask, colour, line
    + Make the outline with a curve, get the mask with `fill`, paint with `over`, then add the line with `stroke`

## The scene object

`scene`, which the `after_*` hooks and every function in `painter.py` receive

| Attribute | Description |
|---|---|
| `scene.image` | The current picture. Modified in place |
| `scene.size` | (height, width) |
| `scene.fig` | The whole sketch |
| `scene.px(units)` | Converts head units to pixels |
| `scene.mask(name)` | Mask of a `fig.shapes` entry (cached) |
| `scene.tone(group, key)` | Palette colour |
| `scene.edge(amount)` | Applies the style's edge treatment to a shadow amount |
| `scene.soften(mask, blur)` | Edge treatment matched to the style |
| `scene.ink(path, width, ...)` | A line following the style's line width |
| `scene.shade_on`, `scene.lines_on` | Switches for the stage images. Shading and lines are drawn only when these are true |
| `scene.rng` | Random generator with a fixed seed |

- To make a prop follow the style, use `scene.edge`, `scene.soften`, `scene.ink`
    + Using `over` alone draws the same shape in every style

## New expression and look presets

- Add presets to JSON without changing code
    + Expressions: `assets/expressions.json`. Looks: `face_shape`, `eye_shape`, `hair_style` in `assets/looks.json`
- A preset is a set of operations on setting paths (dotted keys)

| Operation | Meaning | Example |
|---|---|---|
| `add` | Adds to the current value | `{"mouth.smile": 0.05}` |
| `scale` | Multiplies the current value | `{"eyes.open_down": 0.75}` |
| `set` | Moves toward the value (strings are set as given) | `{"eyes.arch": 0.15}`, `{"hair.style": "bun"}` |
| `style_scale` | Multiplies a style value | `{"face_render.blush_opacity": 1.4}` |
| `flags` | Copied into the expression info (for drawing branches) | `{"tears": true}` |

```json
"sleepy": {"scale": {"eyes.open_up": 0.45, "eyes.open_down": 0.8}, "add": {"eyes.gaze_y": 0.03, "mouth.smile": 0.01}}
```

- Every operation is blended by `amount` (0-1). Values written by the user are not changed
- To change one eye only, use the paths `eyes.near.<key>`, `eyes.far.<key>`
- For new skin, hair or eye colours, add a name and colours to `skin_tone` (one target skin colour), `hair_color` (a 5-colour palette) or `eye_color` (3 iris colours) in `looks.json`
- After adding, render the same spec in 3 styles to check that the proportions hold

## New hair styles

- Edit the guide control points of each section in `hair_guides` in `figure.py`
    + A guide is a list of (x, y, z) points running from root to tip
    + Points over the forehead take the face surface depth from `fz(x, y)`
    + Hanging parts must set their height with `drop(share)` for `hair.length` to keep working
- Tied or updo styles add a section
    + Add (inner guide, outer guide) to `sections` and insert a `paint_hair_section` call into `paint_figure` at the right point in the order
- After editing, check in `1_sketch` that the guides do not cross

## New outfits

- For full-figure garments, `paint_dress`, `paint_shirt`, `paint_pants`, `paint_drape` in `subject_figure.py` and `paint_skirt`, `paint_jacket`, `paint_jeogori` in `wardrobe.py` are the models
    + Garments with sleeves make their sleeves with `wardrobe.long_sleeves` and add them to the sleeve list of `paint_garments`
    + For profile views, combine `top_piece` (tops), `skirt_piece` (skirts), `trousers` (trousers) in `wardrobe_profile.py`
    + Build the outline from body-part masks and spine coordinates (`spine_at`, `spine_side`) and compute the hang with `hang_fabric`
    + Add it to the garment painting order of the `paint` function and add its key to `figure.clothes`
- `wardrobe_casual.py` holds short examples
    + Parts laid on the body piece (hood, pocket, strings) are drawn inside the same mask after the body piece is painted
    + Tight garments (swimwear) use the blurred body height field directly, as `cling` does
    + Front and back views branch on `body.view` to draw different details
    + The key must go into the painting order lists (`subject_figure.GARMENTS`, `wardrobe_profile.GARMENT_KEYS`) so that the arms are laid over the garment again
- Painting colours with `kit.shade_solid` (or `wardrobe.shade_cloth`) applies the palette group's `pattern` automatically
- For the portrait outfit, replace the outline (`cloth`), neckline (`neckline`) and folds (`folds`) returned by `outfit_curves` in `figure.py`
- `paint_outfit` in `painter.py` runs in the order outline fill, form shadow, fold shadows, lines
    + Collars, buttons and patterns are added at the end of the same function with `fill` and `stroke`
- A simple extra layer (jacket, scarf) is safer drawn in a hook module's `after_figure`, based on `fig.shapes["cloth"]`

## New built-in accessories

- In `scripts/accessories.py`, register a defaults dict in `DEFAULTS` and add a drawing function
- Head accessories defined in head coordinates (x right, y down, z toward the viewer, origin between the eyes) and projected with `fig.head_frame.project` follow the head turn
    + In profile, `fig.extra["profile"]["head"]` plays the same role
- Where they are called
    + (Portrait) `painter.paint_figure` (in the right order relative to the hair)
    + (Front and back full figures) `subject_figure.paint_head_front`, `paint_head_back`. Body accessories in `paint_garments`
    + (Profile) `anatomy_profile.paint_head`. Body accessories in `wardrobe_profile.paint_garments`
- An accessory that presses the hair paints out the hair poking out with the background saved beforehand (`remember_background`), as `press_hair` does
- Add colour groups to `assets/accessories.json`

## New interior items

- Write a function `paint_<name>(scene, camera, item, floor_mask)` in `scripts/interior.py` and register it in `WALL_ITEMS` (walls) or `FLOOR_ITEMS` (floor)
    + Coordinates are centimetres (X right, Y up, Z into the room). `camera.project` gives picture coordinates, `camera.scale(point)` gives pixels per cm
    + Boxes use `subject_desk.paint_box`, round things `relief.lathe` or `disc_with_rim`, floor shadows `floor_shadow`
    + Lights that switch on are registered with `keep_lit` (so they do not darken at night) and `scene.glows` (glow)
- Add colour groups to `style.palette` in `assets/subject_cafe.json`, `subject_room.json`
- A new interior subject (an office, for example) is made by changing only `items` in `assets/subject_<name>.json` and registering `"<name>": "interior"` in `SUBJECT_MODULES` of `render.py` and the name in `HORIZON_KEYS` and `INTERIORS` (the bedroom `subject_bedroom.json` and the bathroom `subject_bathroom.json` are the models)
    + Colour groups of new items go in that subject file's `style.palette`. A pattern over whole walls is taken as a `room` setting key and drawn right after `paint_shell` (`room.wall_tiles` and `paint_wall_tiles`)

## New styles

- Copy an `assets/style_<name>.json` to write one and add its name to `STYLES` in `render.py`
- Decide in this order: `shading` mode, `line_scale`, palette, proportions (`figure`), finish (`finish.kind`)
- If a new finish is needed, add a function to `finish.py` and register it in `FINISHERS`
- A style imitating another material (printmaking, palette-knife oil, coloured pencil and the like) is shortest with `base`
    + Inherit a base style and write only the values that change, as in `{"name": "<name>", "base": "illust", "finish": {"kind": "<name>", ...}}`
    + Write the finish function in `media.py` as `finish_<name>(image, fig, options, seed)` and register it in `FINISHERS`. The input is the base style's picture just before its finish (0-1 RGB). The output has the same format
    + Per-subject `style_<base>` palette overrides are followed automatically when there is no `style_<name>`

## New held objects

- Write `paint_<name>(scene, grip, unit, group, ...)` in `held.py` returning a mask, and register it in `GRIP` (anchor point in the hand), `GROUPS` (palette group) and the branches of `paint_held`
    + The object is painted behind the hand. The palm, knuckles, four fingers and forearm are laid over it again. Only the thumb hides behind the object
    + The wine glass (`paint_glass`) and the phone (`paint_phone`) are short models
- Add the colour group to `style.palette` in `assets/subject_figure.json`

## New subjects

- Write `scripts/subject_<name>.py` and register it in `SUBJECT_MODULES` of `render.py`
    + Save the default composition and palette as `spec` and `style` in `assets/subject_<name>.json`
- The 3 functions a module must provide

```python
def build(spec):            # returns a Figure holding size, light, seed and spec
def paint(fig, style, seed, shade=True, lines=True, extras=None):   # returns the image
sketch = kit.sketch         # sketch stage; draws the outlines registered with kit.register
```

- The shortest model is `scripts/subject_hand.py`. The object-list approach is `scripts/subject_still_life.py`
- An outdoor backdrop where people stand matches `backdrop.place` "horizon" directly when it uses the level camera in centimetres from `interior.make_camera` (`scripts/subject_park.py`, `scripts/subject_skyline.py`)
    + Register ("camera", "horizon_y") in `HORIZON_KEYS` of `render.py`
    + To make several subjects from one module, list each name with the same module in `SUBJECT_MODULES` and vary only `assets/subject_<name>.json`
    + Repeating wall surfaces (window grids, tiles) are drawn at once, thousands of windows included, with modulo arithmetic on the surface coordinates projected back from each pixel (`subject_blocks.paint_block`)
- Order of work
    + Write a design memo (composition, light, palette)
    + Paint from the background toward the front
    + Make masses with `relief.tube`, `relief.lathe`, `relief.ellipsoid` and colour them with `kit.shade_solid`
    + Flat shapes use `fill` and `over`. Lines use `kit.ink_edges`
    + Ground shadows use `kit.ground_shadow`
    + Record the painting detail level in `fig.focus` (a 0-1 map)

| Function | Use |
|---|---|
| `relief.tube(size, path, left, right, roundness)` | A tube along a path. Width set at each path point |
| `relief.lathe(size, axis_x, top_y, bottom_y, profile, tilt)` | Solid of revolution about a vertical axis |
| `relief.ellipsoid(size, center, rx, ry)` | Ball, egg shape |
| `relief.bump(...)` | Height of a swelling added to another surface |
| `relief.union(parts, blend)`, `relief.place_over(base, part, lift)` | Merge into one mass (rounded joint of `blend` px), lay one in front |
| `relief.blob(size, outline, depth)` | A solid from any outline, rounded only at the edges |
| `kit.shade_solid(scene, part, group, level, spread, gloss)` | Solid shading. Applies the style's edge treatment automatically |
| `kit.ink_edges(scene, mask, width)`, `kit.ink_tube(...)` | Outline, tube outline without the root |
| `kit.vertical_gradient`, `kit.ridge_line`, `kit.below_line` | Sky, ridgeline, mask under a ridgeline |

- The loop of rendering each stage, looking at it and fixing it applies to every subject

## New poses and body types

- Full-figure poses are adjusted with the angles in `figure.pose` (`references/subjects.md`)
    + Poses with limbs coming toward the viewer, like sitting, set `foreshorten` and `toward` together
    + A limb going behind the body uses `toward` -1. When arms overlap, the arm on top gets `over`
- Most profile poses come from angles alone (kneeling, crossing the legs, a foot against a wall). An object touching the body takes its position from that pose's skeleton coordinates and is painted before the figure (`anatomy_profile.paint_wall` is the model)
- A pose whose body and head views differ is composed by changing the painting order (`figure.look_back` paints the profile head of `anatomy_profile.paint_turned_head` over a back-view body)
- New held objects get a drawing function in `held.py` and are registered in the grip position `GRIP`, the palette `GROUPS` and the branches of `paint_held`
- A new backdrop scene is usable through `backdrop.subject` as soon as its subject module exists. If it has a horizon, register its position in `HORIZON_KEYS` of `render.py`
- Bone lengths and part widths are constants at the top of `scripts/anatomy_body.py`
    + Width arrays are half-widths (head units) from root to tip
- A new body type (muscular, slender and so on) gets one more table
    + `anatomy_body.py`: register a dict that overrides only the changed keys, like `MALE = {**FEMALE, ...}`, in `BUILDS`
    + `anatomy_profile.py`: register a profile table the same way in `BUILDS`
    + `assets/sex_<name>.json`: face, hair, outfit and colour preset. Merged when the spec's `sex` names it
    + Check the form first with a clay render (grey solids without colour), then colour it
- Hand poses are added to `POSES` in `scripts/anatomy_hand.py`
    + A hand that must read at figure scale (the V sign `peace`) gets a large finger spread (`spread`)
- For an arm whose angles are tedious to tune, use `reach` (hand target) and choose only `bend`. The solver is `anatomy_body.solve_arm`. In profile, `anatomy_profile.aim_arm`
- A new profile action is a combination of `lean` and leg angles. Angles are relative to the body, so write the picture angle plus `lean`
- A front action driven by depth (like walking toward the viewer, with legs going toward and away from the viewer) is made as a preset where one key fills the limb angles, `foreshorten` and `toward` at once, like `anatomy_body.stride_pose`
    + A foot with the heel raised uses `tiptoe` true in the leg settings (foot length `TIPTOE_LENGTH`). That leg's outline stays behind the other leg
    + An arm swung back uses `behind_clothes` true in the arm settings. The part of the arm going behind the body (`arm_behind`) also hides behind clothing outside the bare body outline (`subject_figure.tucked_arms`)
    + Seated rendering (knee outline, knee light, creases, puffed trousers) applies only to legs in `body.seated`. A leg counts as seated when its thigh comes toward the viewer by more than `SEATED_SHARE` (0.5) of its length
- To add lying directions, change `lying.turns` (rotation codes), `frame_spec` (eye position and light rotation) and `resting_side` (the side touching the ground) together

## New scene props and hand target points

- A prop shared by several figures gets `paint_<name>(scene, geo, mirror)` in `scripts/props.py`, registered in `PAINTERS`
    + `geo` is in pixel coordinates of the finished picture. If the figure painting it is mirrored, flip it with `flip_x`
    + Size and position are measured and passed by `render.resolve_props`. Add a function that computes them from the figures' `measure` (points and body unit), like `render.bench_geometry` and `table_geometry`
    + Add the colour group to `style.palette` in `assets/subject_figure.json` (`seat` for the bench, `table` for the table)
- New points a hand can aim at
    + (Head) add head coordinates to `subject_figure.HEAD_MARKS` (front) or `anatomy_profile.PROFILE_HEAD_MARKS` (profile)
    + (Body) add to both `anatomy_body.joint_marks` (joints before the pose, used when aiming) and `subject_figure.landmarks` (points other figures read in a scene)
- To re-lay a new part that crosses in front, add the part name and mask to `subject_figure.lift_mask` (front) and `anatomy_profile.lift_mask` (profile, from `fig.extra["arm_masks"]` saved while painting)
    + New points a profile figure can aim at go in `anatomy_profile.landmarks`. `render.arms_of` also reads the `reach` of a profile arm and turns the other figure's point into a picture position
    + `render.paint_layer` limits the part to the pixels that figure painted and splits it into the part (`core`) and the outer outline band (`ring`). `lay_lifts` lifts only pixels in the band darker than what lies below (the outline)
    + To pass under the face and fringe of a figure painted later, use `lift_under_head`. The covering area is that figure's `fig.extra["head_cover"]` (face, near hair, far hair outside the body)
- An object that keeps the rain off adds its mask to `fig.extra["shelter"]`. The weather stage then removes the rain streaks there
