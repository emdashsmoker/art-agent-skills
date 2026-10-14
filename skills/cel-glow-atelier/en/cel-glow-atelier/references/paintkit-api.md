# paintkit API

Reference of the primitives in `scripts/paintkit`. Used for path B (mixed) and path C (free scene).

## Contents

- Basic concepts
- core : colors, paths, masks, layers
- light : mask-based lighting
- backdrop : backgrounds
- finish : finishing
- scenery : landscapes and cities
- urban : doomer city operations
- objects : objects (devices, furniture, cups)
- hand and figure : hands and full bodies
- profile : full body in profile
- back : full body back view
- furniture : furniture for characters
- duo : two-shots
- hat and props : hats and cigarettes
- features and hairstyle : face presets and hair textures
- scene and Portrait : connecting the rigs
- Free scene recipes
- Cautions

## Basic concepts

- Every drawing is a "mask (0-1 float array) + color" pair
- Coordinates are pixels with the y axis pointing down; colors are "#rrggbb" strings or 3 floats in 0-1
- Create layers from back to front and composite them at the end with `canvas.flatten()`
- Import form

```python
import sys
sys.path.insert(0, "<skill folder>/scripts")
from paintkit import core as pk, light as lt, backdrop as bd, finish as fn, scene
from paintkit import scenery as sn, hand as hd, figure as fg, body as bo, objects as ob
from paintkit import profile as pf, furniture as fu, duo
```

## core : colors, paths, masks, layers

| Function | Description |
|---|---|
| `pk.rgb(color)` | Converts a color to 0-1 float RGB |
| `pk.mix(a, b, t)` | Interpolates two colors |
| `pk.adjust(color, value, sat, hue_shift)` | Value and saturation scale with hue rotation (0.01 = 3.6 degrees) |
| `pk.spline(points, closed, n)` | Smooth curve through the control points |
| `pk.piecewise(points, corners, closed)` | Curve with corners only at the given control points |
| `pk.bezier(p0, p1, p2, p3)` | Cubic Bezier |
| `pk.ellipse(cx, cy, rx, ry, rot_deg)` | Ellipse polygon |
| `pk.rotate(pts, deg, origin)` | Rotation |
| `pk.resample(path, n)` | Even resampling by arc length |
| `pk.offset(path, distance)` | Shifts a path along its normals |
| `pk.taper(n, width, head, tail, peak)` | Width profile thinning at the ends |
| `pk.fill_mask(shape, polys)` | Anti-aliased mask of one or more polygons |
| `pk.stroke_mask(shape, (path, widths))` | Variable-width stroke mask, accepts a list |
| `pk.blur(mask, sigma)` | Gaussian blur |
| `pk.shift(mask, dx, dy)` | Translation |
| `pk.linear_ramp(shape, p0, p1)` | Linear ramp, 0 at p0 and 1 at p1 |
| `pk.radial_ramp(shape, center, radius, aspect)` | Radial ramp, 1 at the center and 0 at the radius |
| `pk.smoothstep(e0, e1, x)` | Smooth step |
| `pk.noise(shape, scale, seed, octaves)` | Smooth noise in 0-1 |
| `pk.save(image, path)`, `pk.load(path)` | Input and output |

### Canvas and Layer

```python
canvas = pk.Canvas(1200, 1500, background="#ffffff")
layer = canvas.layer("tree")                       # added on top
layer = canvas.layer("necklace", above="outfit")   # inserted right above the named layer
layer = canvas.layer("glow", mode="screen", opacity=0.8)
layer.paint(mask, "#ff8800", opacity=0.6)   # an H x W x 3 array also works as the color
layer.clip(mask)                             # keep only inside the mask (clipping)
layer.erase(mask)                            # erase the mask area
image = canvas.flatten()                     # 0-1 float RGB
```

- Blend modes : `normal`, `multiply`, `screen`, `overlay`, `add`, `softlight`
- `pk.Frame(origin, scale, rot_deg).to(points)` : converts local unit coordinates to pixels

## light : mask-based lighting

| Function | Description |
|---|---|
| `lt.light_vector(azimuth_deg, elevation_deg)` | Light direction vector. 135 = top left |
| `lt.paint_form(layer, mask, base, shadow, light, radius, threshold, softness)` | Paints base color and form shadow in one call |
| `lt.inflate(mask, radius)` | Height map of a flat mask puffed up like a cushion |
| `lt.normals_from_height(height)` | Normal map from a height map |
| `lt.sphere_normals(shape, center, rx, ry)` | Ellipsoid normal map (round forms such as heads and fruit) |
| `lt.lambert(normal_map, light)` | Diffuse light value (-1-1) |
| `lt.form_shadow(lit, threshold, softness)` | Shadow mask from the light values |
| `lt.cast_shadow(occluder, receiver, light, distance, softness, down_bias)` | Cast shadow |
| `lt.occlusion(occluder, receiver, spread, strength)` | Contact shadow |
| `lt.rim(mask, light, width, softness)` | Band on the edge toward the light |
| `lt.outline_mask(mask, width, light, variation)` | Outline band of varying width |

- `softness` 0.02 is cel shading, 0.15 illustration, 0.3 painting
- `radius` is about half the thickness of the form

## backdrop : backgrounds

- `bd.gradient(layer, top, bottom, angle_deg)`
- `bd.glow(layer, center, radius, color, opacity)`
- `bd.bokeh(layer, colors, count, size, opacity, seed)`
- `bd.wash(layer, colors, scale, seed)`
- `bd.light_shafts(layer, color, count, angle_deg, width_px, opacity)`
- `bd.petals(layer, color, count, size, seed)`

## finish : finishing

Input and output are both 0-1 float RGB images.

| Function | Description |
|---|---|
| `fn.diffusion(img, sigma, strength)` | Diffusion glow |
| `fn.bloom(img, threshold, sigma, strength)` | Bright-area bleed |
| `fn.grade(img, contrast, saturation, shadow_tint, highlight_tint, tint_strength)` | Color grading |
| `fn.vignette(img, strength, color)` | Darkening at the edges |
| `fn.grain(img, amount, seed)` | Film grain |
| `fn.paper(img, strength, scale, seed)` | Paper texture |
| `fn.canvas_weave(img, strength, period)` | Canvas weave pattern |
| `fn.chromatic(img, shift)` | Chromatic aberration at the edges |
| `fn.painterly(img, radii, threshold, detail, seed)` | Brush stroke reconstruction |
| `fn.tilt(img, degrees)` | Dutch angle. Rotation about the center (positive is counterclockwise) with an automatic zoom that removes empty corners |

- `detail` of `fn.painterly` is a mask of areas kept fine (the face and so on)
- Give `radii` from the large brush to the small one

## scenery : landscapes and cities

- A set of builders drawing straight onto one layer; positions and sizes are canvas fractions
- Functions : `sn.sky`, `sn.sun`, `sn.stars`, `sn.clouds`, `sn.ridge`, `sn.ground`, `sn.grass`, `sn.flowers`, `sn.water`, `sn.tree`, `sn.pine`, `sn.tree_line`, `sn.skyline`, `sn.street`, `sn.room`
- `sn.room(layer, floor, wall, floor_color, baseboard, window, ...)` : interior wall, window, wooden floor. Arguments are the same as the interior section of `scenery.md`
- Arguments are the same as the tables of `references/scenery.md`; pass the light vector as `light`
- `sn.ridge`, `sn.ground`, `sn.water`, `sn.tree` return the mask of the drawn area, so shading or elements can be added on top
- `sn.StreetView(layer, horizon, vanish_x, eye)` : perspective converter of the street
    + `project(x, y, z)` : converts meter coordinates (sideways, height, depth) to pixels
    + Used to add objects such as benches or sandwich boards at the exact position and size on the street
    + Cars and passers-by are drawn by the `cars`, `people` arguments of `sn.street`

```python
layer = canvas.layer("land")
sn.sky(layer, "#4f7fc0", "#f3d9b8", horizon=0.62)
sn.ridge(layer, base=0.60, height=0.30, color="#8f9cc4", shadow="#6a7aa8", light=LIGHT, seed=3)
lake = sn.water(layer, top=0.625)
```

## urban : doomer city operations

- `from paintkit import urban as ur`. Draws straight onto one layer; positions and sizes are canvas fractions (same rules as scenery)
- Functions : `ur.panel_blocks`, `ur.power_lines`, `ur.streetlamp`, `ur.snow`, `ur.fog`, `ur.bare_tree`
    + Arguments are the same as the city operations table of `references/scenery.md`
    + All return the mask of the drawn area (`snow` the flakes, `panel_blocks` all blocks)
- To put them in only part of a scene, like the view out of a window, draw on a separate canvas of the same size and paint its `flatten()` result through the glass mask

```python
view = pk.Canvas(WIDTH, HEIGHT)
ur.panel_blocks(view.layer("blocks"), time="night", blocks=[{"x": [0.3, 0.8], "base": 0.95, "top": 0.2}])
ur.snow(view.layer("snow"), count=400)
canvas.layer("outside").paint(glass_mask, view.flatten())     # paints an H x W x 3 color field through the mask
```

## objects : objects (devices, furniture, cups)

- Principle : man-made things are combinations of boxes and cylinders, with details placed on each face
- `ob.Stage(shape, origin, scale, yaw, pitch, distance, light)` : a fixed camera
    + Real dimensions (e.g. cm) are used as is and converted to picture positions
    + Axes : x right, y up, z away from the viewer
    + `origin` is the pixel where the origin lands, `scale` pixels per unit
    + `yaw` is the camera's sideways turn, `pitch` the downward viewing angle
    + Without `distance` it is a parallel projection (clean like a product drawing); a number gives a perspective projection
- Drawing functions

| Function | Description |
|---|---|
| `ob.box(stage, layer, center, size, color, shadow, radius, edge)` | Box. Paints the visible faces with a tone per face and returns `{face name: Face}` |
| `ob.cylinder(stage, layer, center, radius, height, color, shadow, top_color, taper)` | Upright cylinder (cups, cans, pots, posts) |
| `ob.pebble(stage, layer, center, size, color, shadow)` | Low round object without flat faces (mouse, soap, stone) |
| `ob.polygon(stage, layer, points, color, opacity, softness)` | Flat polygon in space coordinates (floor, wall, paper) |
| `stage.ground_shadow(points, softness)` | Shadow mask the points cast on the plane y = 0 |
| `stage.project(points)` | Converts space coordinates to pixels |

- `center` is the center of the object's bottom face, `size` is (width x, height y, depth z)
- `radius` rounds corners (space units) and applies to the 2 large faces perpendicular to the thinnest axis
- Face names : `front`, `back`, `left`, `right`, `top`, `bottom`. Only faces visible from the camera are returned
- `Face` : place details in face coordinates (u right, v down, 0-1)
    + `face.rect(u0, v0, u1, v1, radius)` : pixel polygon of a rectangle on the face
    + `face.at(uv)` : converts face coordinates to pixels
    + `face.mask()` : mask of the whole face
- `ob.grid(face, area, columns, rows, gap, radius)` : list of grid polygons of equal cells (keyboard keys, windows, app icons)
- `ob.text_lines(face, layer, area, rows, colors, seed)` : rows of short bars that read as text or code (screens, documents)
- Drawing order : walls and floor, shadows, far objects, near objects
- Collecting shadows on a `multiply` layer makes objects look attached to the floor

```python
stage = ob.Stage(canvas.shape, origin=(760, 640), scale=7.3, yaw=22, pitch=20)   # 1 unit = 1 cm
faces = ob.box(stage, layer, center=(0, 12, 17), size=(64, 38, 2.4), color="#22252d", radius=1.2)
layer.paint(pk.fill_mask(canvas.shape, faces["front"].rect(0.03, 0.04, 0.97, 0.96)), "#1b2233")   # screen
ob.text_lines(faces["front"], layer, (0.08, 0.15, 0.94, 0.92), rows=17, colors=("#7fd1c7", "#f2c14e"))
```

- Full example : `assets/examples/desk_setup_example.py` (monitor, laptop, keyboard, mouse, phone, mug, potted plant, framed picture)
- Limit : objects with many curved surfaces (car bodies, chair backs, streamlined devices) are simplified into box combinations

## hand and figure : hands and full bodies

- `hd.Hand(shape, frame, pose, mirror, view, widen, roll, pitch)` : one hand; `widen` scales finger thickness (male 1.15)
    + `frame` is `pk.Frame(wrist pixel, hand length pixels, rotation)`; rotation 0 points the fingers down the screen
    + `pose` is a gesture name or `hd.HandPose(curl, spread, thumb_out, thumb_curl)`
    + `roll` : rotation around the hand's long axis (degrees, -90-90); positive shows the thumb side to the viewer
    + `pitch` : how far the fingers tip toward the viewer (degrees, 0-75)
    + Hand points are 3D (x, y, z), with z the thickness toward the back of the hand and the finger bend depth. A rotated hand draws its fingers in depth order
    + Paint with `hand.paint(layer, skin, shadow, line_color, light)` and check the area with `hand.mask`
    + `hd.HIDDEN_POSES` (`pocket`, `tucked`) : hands that are not drawn. `hand.hidden` is true and the mask is empty
- `fg.Figure` : the full body rig. Usually used through the spec's `figure` key; details in `references/figure-spec.md`
- `bo.make_pose(name, overrides)` : creates a pose object
- `bo.make_build(values)` : creates a build object
- `bo.plan_for(gender)` : the gender's body plan (`BodyPlan`, all proportions and width curves)
- `bo.solve_skeleton(pose, build, plan)` : computes only the joint coordinates (to check a pose before drawing)
- `bo.POSES`, `bo.REACH` : dictionaries of pose presets and female wrist targets (male in `plan.reach`)
- `fg.OUTFITS`, `fg.OUTFIT_ALIASES` : full body outfit names and aliases (`bikini` is `swimsuit`)
- `fg.OUTFIT_GENDER`, `fg.DEFAULT_OUTFIT` : the gender each outfit is cut for (unisex when absent from the table) and the default outfit per gender
- `fg.resolve_outfit(name)` : resolves aliases and returns the outfit name; an unknown name raises `ValueError` with the list grouped by gender
- `paintkit.wardrobe` : front, profile and back forms of the 7 v9 outfits. New outfits are added to this module as 3 functions, one per view
- `scene.make_figure(canvas, cfg, character, style, head_height_px, pelvis_px, light)` : creates the matching front, profile or back rig from the spec's `figure` dictionary
- `spec.with_gender_defaults(character, palette)` : (character, palette) dictionaries filled with the gender defaults

## profile : full body in profile

- `pf.SideFigure(canvas, spec, style, head_height, pelvis_px, pose, outfit, build, heels, light, facing, furniture)` : the profile rig
- `pf.make_side_pose(name, overrides)` : `side_stand`, `side_walk`, `side_sit`, `side_wave`, `side_lounge`, `side_lean` presets with overrides
- `profile_head.ProfileHead(figure, frame)` : profile head (face, ear, eye, hair). Shared by the profile rig and looking back from a back view
    + `profile_head.ProfileFrame(origin, scale, pitch_deg, sign)` : profile coordinate conversion; `sign` -1 looks left
    + `head.masks()`, `head.paint_face(layer, features, face, neck)`, `head.paint_hair(layer, hair)`
- Profile coordinates : the origin is the head's center line at eye level, the face toward +x. Eye about (0.34, 0), nose tip about (0.50, 0.16), ear about (-0.04, 0.06)
- `figure.face_frame.to(points)` : converts profile coordinates to pixels (when looking left, the layers are flipped after rendering, so use `figure.head.to`)

## back : full body back view

- `bk.BackFigure(canvas, spec, style, head_height, pelvis_px, pose, outfit, build, heels, light, look=...)` : the back view rig, inheriting `fg.Figure` and sharing its skeleton
- `bk.make_back_pose(name, overrides)` : `back_stand`, `back_lookback`, `back_walk`, `back_sit` presets with overrides; returns (pose, default look)
- `bk.LOOKS` : `away`, `left`, `right`, `left_3q`, `right_3q` (`_3q` uses the front face rig turned 35 degrees)
- In the mixed mode `torso` of `figure.masks` includes the nape (skin below the back hair)

## furniture : furniture for characters

- `fu.paint(figure, kind, color)` : draws `chair`, `sofa`, `pillar`, `bed` behind a front character (usually through the spec's `figure.furniture`)
- `fu.floor_level(figure)` : skeleton y coordinate of the floor under the feet (head units below the pelvis). Used to stand other people or objects on the same floor
- `fu.paint_side(figure, kind, color, near)` : profile furniture `stool`, `chair`, `sofa`, `pillar`. `near=False` behind the character, `near=True` in front (the near armrest of the sofa)
- `fu.back_contact(figure)` : the point where the back sticks out farthest in profile (head units), reference for the back cushion and pillar position
- `fu.paint_back_chair(figure, color, near)` : a chair seen from behind. `near=False` the seat and legs, `near=True` the backrest
- `fu.stage_for(figure, yaw)` : an `objects.Stage` with the floor under the character's feet as origin and 1 unit = 1 head
    + Used to place objects such as tables, boxes or potted plants beside a character at the same scale

## duo : two-shots

- Usually used through the spec's top-level `duo` key; details in the two-shot section of `references/figure-spec.md`
- `duo.DUO_POSES` : `side_by_side`, `hold_hands`, `arm_in_arm`, `arm_around`, `face_to_face`
- `duo.stature_ratio(main_gender, partner_gender, scene.stature_units, scene.STATURE_M)` : the partner's head size scale from real height ratio
- `duo.Duo(canvas, duo_spec, main_cfg, main_character, partner_character, partner_cfg, style, light, head_px, main_pelvis, scene.make_figure, scene.stature_units, scene.STATURE_M)` : placement and contact plan of the two characters
    + `render(shadow_main, shadow_partner)` : draws both characters and returns the main character object; the partner is `portrait.partner`
- In the mixed mode, the joints of the two characters are `portrait.joints` and `portrait.partner.joints`, each with its own `at` for pixel conversion

## hat and props : hats and cigarettes

- `paintkit.hat` : called automatically right after the rig draws the hair, when `character.hat` is not `none`
    + Shapes are defined in head units of each head frame (front `head.to`, profile `ProfileFrame.to`), so they follow head turn and tilt
    + Hair standing above the beanie is erased from the hair layers (`hair_front`, `hair_back`, `see_through`)
- `paintkit.props`
    + `pr.paint_cigarette(layer, base, tip, width, line_color=None, line_opacity=0.6)` : draws filter, paper, ash, ember and glow between two pixel points (the filter at `base`)
    + `pr.smoke(layer, start, rise_px, width_px, seed=0, color, opacity=0.5, drift=0.25)` : smoke rising `rise_px` from `start`. `drift` is the sideways drift as a share of the rise (negative is left)
    + A character's cigarette is handled automatically by the `figure.cigarette` key; the 2 functions above are for still lifes and the mixed mode
- Still life example : `assets/examples/doomer_still_life_example.py` (a cigarette resting on an ashtray placed with `stage.project`, 2 smoke columns)

```python
base, tip = stage.project([(4.0, 2.5, -14.0), (-2.0, 2.0, -11.6)])     # filter, ember (cm)
pr.paint_cigarette(layer, base, tip, width=0.8 * PIXELS_PER_CM, line_color="#12141a")
pr.smoke(canvas.layer("smoke"), tip, rise_px=500, width_px=3.0, color="#cdd5e0", opacity=0.6, drift=-0.12)
```

## features and hairstyle : face presets and hair textures

- Usually used through the spec's `character` keys (`eye_shape`, `brow_shape`, `nose_shape`, `mouth_shape`, `skin_tone`, `hair_style`)
- `paintkit.features`
    + `EYE_SHAPES`, `BROW_SHAPES`, `NOSE_SHAPES`, `MOUTH_SHAPES` : preset names and shape data (head units, shared by both genders)
    + `features.check(spec)` : `ValueError` on a name that is not allowed
    + `features.eye_lids(shape, w, h, tilt)` : upper and lower lid control points of a preset eye
- `paintkit.spec.SKIN_TONES` : `skin`, `skin_shadow`, `blush`, `lip` per gender for the 6 skin tones
    + `spec.skin_tone_palette(tone, gender)` : dictionary of palette values; `with_gender_defaults` inserts it between the gender palette and the spec palette
- `paintkit.hairstyle`
    + `hairstyle.paint_curls(fig, layer, mask, seed)` : C-shaped curl texture over the mask (a dark arc + a light arc toward the light)
    + `hairstyle.paint_undercut(fig, layer, zone, keep)` : paints `zone` in the short-cut hair color and puts shade under `keep` (the long hair)
- Hair shape data is `paintkit.anatomy.HAIR_STYLES`, with the new keys `ears`, `wave_freq`, `ragged`, `volume`, `curls`, `undercut`, `nape_locks`, `profile`

## scene and Portrait : connecting the rigs

```python
canvas, portrait = scene.build(spec)      # draws background and character as layers
# ... draw additional layers here ...
image = scene.finish(canvas, portrait, spec)
pk.save(image, "out.png")
```

- Layer order (bust) : background, hair_back, body, outfit, face, features, hair_front, see_through, rim, ambient, foreground
- `portrait.head.to(points)` : converts head unit coordinates to pixels, with tilt and turn
- `portrait.head.to_rigid(points, depth)` : converts points off the face surface (ears, earrings) to pixels, turned at a fixed depth. Makes a difference in three-quarter
- `portrait.head.wide` : strength of the correction for turns over 14 degrees (0-1)
- `portrait.head.turned_outline(outline, anchors)` : turns the face outline. `anchors` is `anatomy.face_anchors(spec)`; in three-quarter it redraws the cheek curve relative to the features
- `portrait.body.to(points)` : converts body unit coordinates to pixels, without tilt
- `portrait.px(value)` : converts a head unit length to pixels
- `portrait.masks` : `face`, `body`, `cloth`, `hair_back`, `hair_cap`, `hair_bangs`, `hair_sides`, `hair_front`, `eyes`, and `ears` when the ears show
- `portrait.figure_mask()` : silhouette of the whole character
- `scene.SHOTS` : framing preset names (`full`, `thigh`, `knee`, `waist`, `bust`)
- `portrait.light` : the light vector, reusable for shading added elements

### Head unit reference points

| Position | Coordinates (x, y) |
|---|---|
| Crown | (0, -0.52) |
| Brows | (±0.17, -0.108) |
| Eye centers | (±0.172, 0) |
| Nose tip | (0, 0.183) |
| Mouth | (0, 0.283) |
| Chin tip | (0, 0.455) |
| Half face width (at eye height) | 0.335 |
| Bottom center of the neck (body units) | (0, 0.78) |
| Shoulder tips (body units) | (±0.505, 0.935) |

## Free scene recipes

- Standard order for drawing one element
    + Write a `pk.spline` path with 4-8 control points
    + Make a mask with `pk.fill_mask`
    + Apply base color and form shadow with `lt.paint_form`
    + Add `lt.cast_shadow`, `lt.rim` if needed
    + For styles with lines, paint `lt.outline_mask` in a dark color
- Order for the whole scene
    + Create layers from the farthest surfaces such as sky or wall
    + Lower value contrast and saturation for farther elements (atmospheric perspective)
    + Deeper and crisper for nearer elements
    + Use the same `light` vector for every element
    + Chain 2-4 `finish` functions at the end
- Write natural things as clusters of many small masses
    + Tree crowns : stack several clusters of about 7 ellipses
    + Mountain ridges : join control points of random heights with a spline
- Reflections and water : flip the `canvas.flatten()` result, paint it darker and add ripple strokes
- Full examples : `assets/examples/landscape_example.py`, `assets/examples/still_life_example.py`, `assets/examples/desk_setup_example.py`, `assets/examples/doomer_still_life_example.py`
- To give a free scene the same finish as a spec, `scene.finish(canvas, None, {"style": "illust", "finish": {"preset": "doomer"}, "seed": 7})`

## Cautions

- Push polygon control points well outside the picture to avoid gaps at the edges
- Define line widths and radii as constants proportional to the canvas size at the top of the file
- Hundreds of strokes are fast only when passed to `pk.stroke_mask` at once as a list
- Fix random numbers with `np.random.default_rng(seed)` for reproducibility
- Render and check after adding every 1-2 elements
