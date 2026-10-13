# codepaint API

Every public function of the engine. All length arguments are in logical units and give the same result at any scale.

## Contents

- Basic concepts
- Canvas
- Paints (Linear, Radial) and blending (Blend)
- geometry: paths
- color: colors
- motifs: procedural subjects
- figure: body rig and hands
- figure3d: 3D rig that turns the body
- head3d: head, face and hair by angle
- faces: face templates
- hairstyles: hairstyle templates and long hair drape
- character: painting 3D figures
- garment: clothing
- stage: two-shot stage
- Perspective: one-point perspective
- solids: 3D solids and cameras
- props: modern object parts
- styles: style tools
- post: post-processing
- io: saving and review
- noise: noise and ground textures

## Basic Concepts

- A path is an (N, 2) array in logical coordinates
    + Created and transformed with `geometry` functions
- A Shape is a mask piece made by putting a path on a canvas
    + Created with `canvas.shape(path)`
    + `a & b` intersection, `a - b` difference, `a | b` union, `a * 0.5` strength
- Colors accept `"#rrggbb"`, `"#rgb"`, 0-1 tuples and 0-255 tuples
- Images are 0-1 float RGB arrays (height, width, 3)
- The light direction `light` is an (x, y) that points toward where the light is
    + A top-left light is `(-0.6, -0.8)`, a top-right light `(0.6, -0.8)`
- Angles are in degrees, and clockwise on screen is positive

## Canvas

```python
Canvas(width, height, scale=1.0, background="#ffffff", seed=7)
Canvas.from_image(image, width, height, seed=7)   # to keep painting on top of a pass result
```

- `background=None` gives a transparent canvas
    + Used for layers drawn separately and placed over the background, such as figures
- Attributes: `width`, `height`, `scale`, `px_w`, `px_h`, `rgb`, `alpha`, `rng`, `flow`

### Making Shapes

| Call | Role |
|---|---|
| `shape(*paths, soft=0.0)` | Convert paths to a shape. Overlapping paths cut holes by the even-odd rule. soft is the edge blur width |
| `full()` | Shape of the whole canvas |
| `soften(shape, amount)` | Edge blur |
| `roughen(shape, amount=3.0, grain=12.0)` | Wobble the edges irregularly. amount is the wobble width, grain the pattern size |
| `mottle(shape, grain=60.0, coverage=0.5, soft=0.15, octaves=4)` | Keep a mottled pattern inside the shape. coverage is the remaining area ratio |
| `form_shadow(shape, light, amount=0.4, soft=0.0, roundness=1.0)` | Treats the shape as an inflated solid and cuts the amount fraction on the side away from the light |
| `contour(shape, width)` | A band of width thickness inside the outer contour. For outlining a whole silhouette. Returns empty shapes cut off by the frame unchanged |
| `form_light(shape, light, amount=0.15, soft=0.0, roundness=1.0)` | A highlight that settles inside the surface. The amount fraction that gets the most light |
| `edge_light(shape, light, width=6.0, soft=0.0)` | A band along the light-facing contour. Backlit rims and edge highlights |

- soft 0 in `form_shadow` gives the crisp border of cel painting, 0.2-0.5 the soft border of painting
- roundness below 1 computes a solid that is round only at the edges and flat in the middle

### Painting

```python
fill(shape, paint, opacity=1.0, blend=Blend.NORMAL, clip=None, grain=0.0)
stroke(path, color, width=2.0, taper=1.0, closed=False, opacity=1.0,
       blend=Blend.NORMAL, clip=None, light=None, contrast=0.6, jitter=0.0, soft=0.0)
paste(other_canvas, opacity=1.0)
direct(shape, angle=None, around=None)
```

- The paint of `fill` is a color, `Linear` or `Radial`
    + With clip, paint goes only inside that shape
    + grain 1.0 turns semi-transparent areas into stipple grains. Combined with a soft shape it makes stippled gradients
- The taper of `stroke` is a list of width factors along the length
    + `(0, 1, 0)` is a line pointed at both ends, `(1, 0.3)` a line that thins toward the end
    + closed=True together with light thickens the contour side away from the light
    + jitter is a 0-1 width wobble like a trembling hand
- `paste` composites a canvas of the same pixel size on top
- `direct` sets the oil stroke direction
    + angle is the direction (0 horizontal, 90 vertical), around is a direction circling that point

### Output

| Call | Role |
|---|---|
| `image(background="#ffffff")` | 0-1 RGB image. Transparent areas are filled with background |
| `guide_image(step=100)` | Image with the logical coordinate grid drawn over it. For checking positions |
| `next_seed()` | A new seed that reproduces identically between runs |

## Paints and Blending

```python
Linear(stops, start, end)      # linear gradient from start to end
Radial(stops, center, radius)  # radial gradient from center out to radius
```

- stops is a color list `["#112", "#eef"]` or a list of (position, color) `[(0.0, "#112"), (0.7, "#88a"), (1.0, "#eef")]`
- `Blend.NORMAL` paints over, `Blend.MULTIPLY` for shadows and watercolor glazing, `Blend.SCREEN` for light and haze, `Blend.ADD` for strong glow

## geometry

| Call | Role |
|---|---|
| `spline(points, closed=True, corners=())` | A curve through every control point. Breaks at corners indices |
| `polygon(points)` | Straight-edged polygon |
| `ellipse(cx, cy, rx, ry=None, angle=0.0)` | Ellipse. A circle without ry |
| `rect(x, y, width, height, radius=0.0)` | Rectangle. radius rounds the corners |
| `blob(cx, cy, radius, wobble=0.25, lobes=7, rng=None, stretch=(1, 1))` | Irregular organic shape. Clouds, bleeds, foliage masses |
| `transform(path, translate=(0, 0), rotate=0.0, scale=1.0, about=(0, 0))` | Scale and rotate around about, then translate |
| `ribbon(centerline, widths, closed=False)` | List of outlines that give a center line a width. Use as `canvas.shape(*ribbon(...))` |
| `densify(path, minimum_points)` | Resample a path with few points more densely |

- A few values in the widths of `ribbon` are interpolated along the length
    + Used for long forms with changing thickness, such as branches, hair strands and limbs

### Frame

A local coordinate frame. Design subjects whose proportions matter in unit coordinates, then place them on screen.

```python
head = g.Frame(origin=(1085, 372), unit=160, rotate=-5)   # head radius as 1
face = cv.shape(g.spline(head([(0, -1), (0.97, -0.3), (0.64, 1.0), (0, 1.37), ...])))
eye = head.child(0.49, 0.36, unit=0.31)     # eye frame inside the face
other_eye = head.mirrored().child(0.49, 0.36, unit=0.31)
```

| Call | Role |
|---|---|
| `frame(points)` | Convert a unit-coordinate point list to screen coordinates |
| `frame.point(x, y)` | Convert one point. Use as `g.ellipse(*frame.point(x, y), ...)` |
| `frame.length(value)` | Convert a unit length to a screen length |
| `frame.mirrored()` | A mirrored frame. For symmetric parts |
| `frame.child(x, y, unit=1.0, rotate=0.0)` | A child frame whose origin is a point in this frame |

- To change size, position or tilt, edit only the Frame arguments and the part coordinates stay as they are

## color

| Call | Role |
|---|---|
| `rgb(value)` | Convert a color notation to a 0-1 array |
| `mix(a, b, amount)` | Mix two colors |
| `shift(color, hue=0.0, saturation=1.0, value=1.0)` | HSV hue shift, saturation factor, value factor |
| `shade(color, depth=1.0)` | Shadow color. Pulls the hue toward cool, raises saturation and lowers value |
| `tint(color, amount=0.5)` | Highlight color. Mixes toward warm white |
| `luminance(image)` | Luminance |

## motifs

| Call | Role |
|---|---|
| `cumulus(canvas, center_x, base_y, width, height, light, palette, puffs=70, rng=None)` | Cumulus. palette is (light, middle, shade) |
| `ridge(x_start, x_end, base_y, peak_height, roughness=0.5, points=48, rng=None)` | Top-edge point list of a mountain ridge. Close it by joining two points below |
| `splatter(canvas, center, spread, count, palette, size_range, opacity, rng=None)` | Paint droplets |
| `canopy(canvas, center_x, center_y, width, height, light, palette, puffs=40, puff_size=(0.14, 0.26), rng=None)` | Foliage mass of a tree. Returns the painted shape |
| `grass(canvas, x_range, y_range, count, palette, blade=(14, 34), lean=0.35, rng=None)` | Grass blades. Larger y means nearer grass |

## figure

Usage and pose values are in `references/figure.md`.

```python
figure.Figure(frame, build=figure.FEMALE, hip_tilt=0, chest_tilt=0, spine=0, neck=None, head=None,
              arm_l=(8, 4), arm_r=(8, 4), leg_l=(3, 1), leg_r=(3, 1), stretch=None, shoulder_drop=0.0)
figure.Build(shoulder, ribcage, waist, hip, arm, leg, neck)   # provided: figure.FEMALE, figure.MALE
```

| Call | Role |
|---|---|
| `fig.joint(name)` | Screen coordinates of a joint. pelvis, shoulder_mid, neck_top, head, shoulder_l, elbow_l, wrist_l, hip_l, knee_l, ankle_l and their `_r` |
| `fig.torso()`, `fig.neck()`, `fig.head()` | Part outlines (path lists) |
| `fig.limb(bone, side, scale=1.0)` | Limb outline. bone is upper_arm, forearm, thigh or shin. scale is a thickness factor (clothing) |
| `fig.foot(side, view="front", turn=12.0)` | Foot outline. view is front, side, bare_front (with toes) or bare_back (heel) |
| `fig.toes(side, view="bare_front", turn=12.0)` | The 5 toes of a bare front foot [(toe outline, nail outline), ...], from the big toe to the little toe |
| `fig.parts()` | Dict of all part outlines |
| `fig.on_thorax(x, y)`, `fig.on_pelvis(x, y)` | Convert points in thorax and pelvis coordinates to screen coordinates |
| `fig.head_frame()` | Head frame (origin at the head center, unit the head height) |
| `fig.hand_frame(side, turn=0.0, flip=False)` | Hand frame (origin at the wrist, unit the hand length) |
| `fig.limb_frame(start, end)` | A frame that joins two joints. For placing cuffs and accessories |
| `figure.shape_of(canvas, paths)` | Merge overlapping outlines into one shape without holes |
| `figure.hand_open(frame, spread=1.0, curl=0.0, thumb=1.0, view="back")` | A hand seen from the back or the palm |
| `figure.hand_side(frame, curl=0.25)` | A hand seen from the thumb side |

- Hand functions return a `Hand`
    + `hand.parts[name]` is a list of part outlines, `hand.joints[name]` the joint coordinates, `hand.paths()` the list of all outlines

## figure3d

A rig for 3/4 views, profiles, back views and limbs swung forward and back. Usage and verified poses are in the 3D rig section of `references/figure.md`.

```python
from codepaint.figure3d import Figure3D, Depth, FEMALE_DEPTH, MALE_DEPTH
Figure3D(frame, build=figure.FEMALE, depth=FEMALE_DEPTH, turn=0.0, elevation=0.0, hip_tilt=0.0, chest_tilt=0.0,
         spine=0.0, neck=None, head=None, lean=0.0, arm_l=(8, 4), arm_r=(8, 4), leg_l=(3, 1), leg_r=(3, 1),
         swing=None, stretch=None, shoulder_drop=0.0, head_turn=0.0, foot_pitch=None)
Depth(chest, waist, hip, bust, glute)   # front and back half-depth of the torso (head heights)
```

- At turn 0 the joints and torso outline match `figure.Figure`
- Body coordinates: x is screen right seen from the front, y is down, z is toward the back of the body. The front of the body is -z

| Call | Role |
|---|---|
| `body.groups()` | Masses to paint [(name, outline list), ...], far first. Names are body, arm_l, arm_r, leg_l, leg_r |
| `body.joint(name)`, `body.joints3[name]` | Screen coordinates and body coordinates of a joint |
| `body.torso()`, `body.neck()`, `body.limb(bone, side, scale=1.0)` | Part outlines. The torso comes from projecting sections by height |
| `body.foot(side)`, `body.toes(side)` | Bare foot silhouette usable at any angle, and the 5 toes that appear only when the toes are visible |
| `body.foot_axes(side)` | Forward and outward directions of the foot |
| `body.surface(part, x, y, side="front")` | Body-coordinate point on the torso surface and its outward normal. part is thorax or pelvis, side is front or back |
| `body.on_thorax(x, y, side)`, `body.on_pelvis(x, y, side)` | Screen coordinates of a surface point. x and y are the same thorax and pelvis coordinates as in `figure.Figure` |
| `body.facing(normal)`, `body.facing_at(part, x, y, side)` | How much a normal faces the viewer (-1 to 1). At 0 or below the surface is hidden |
| `body.bulge(part, x, y, z, radii)` | Outline of an ellipsoid in part coordinates. Round masses of breasts, buttocks and lower pelvis |
| `body.local_point(part, x, y, z)` | Convert a point in part coordinates to body coordinates |
| `body.project(point)`, `body.project_path(points)`, `body.depth_of(point)` | Body coordinates to screen coordinates and view depth |
| `body.head_center()`, `body.head_yaw()` | Body coordinates of the skull center, head angle relative to the viewer |
| `body.hand_frame(side, turn=0.0, flip=False)` | Hand frame along the projected forearm direction |
| `body.inside_torso(point)` | Whether a body-coordinate point is inside the torso sections. Used for penetration checks (`stage.collisions`) |
| `body.torso_section(y)` | Torso section at body-coordinate height y (center x, center z, half-width, front depth, back depth). Used for hair drape |
| `Figure3D(..., in_front=("arm_l",))` | Paints limbs that cross in front of the body after the body |

## character

```python
from codepaint import character as ch
model = ch.place(look, origin, unit, turn, elevation=0.0, head_pitch=0.0, ink=ch.ANIME, outfit=None, grips=(), **pose)
ch.paint_figure(canvas, model, defer=())
ch.paint_deferred(canvas, model, ("arm_l",))
look = ch.restyle(ch.FEMALE, face=faces.FEMALE_SOFT, hair=hairstyles.LONG_STRAIGHT,
                  hair_color=hairstyles.HAIR_COLORS["pink"])   # pick face, hair and hair color templates
ch.Ink(light, light3d, line_width, line_scale, line_opacity, body_shadow, face_shadow, hair_shadow, shadow_soft,
       light_opacity)
```

| Call | Role |
|---|---|
| `ch.FEMALE`, `ch.MALE` | Looks of an adult woman and man (Look: sex, build, torso depth, head shape, hair, colors, shoulder drop, face template) |
| `ch.restyle(look, face=None, hair=None, hair_color=None)` | A look with only the face template (including face shape), hairstyle and hair color changed. The hair color changes only hair, hair_shade, hair_light and line_hair of the palette |
| `ch.face_spec(look)` | Face template of a look. If `look.face` is None, the default face for the sex |
| `ch.lowest_foot(look, unit, turn, elevation, **pose)` | Screen height from the pelvis center to the lowest foot tip. Used to put the feet on the floor |
| `ch.paint_figure(canvas, model, defer=())` | One person. Limb masses in defer are skipped |
| `ch.paint_deferred(canvas, model, names)` | Paints the held-back masses (skin, markers, clothing) |
| `ch.paint_garment(canvas, model, piece)` | One clothing piece |
| `ch.choose_hand(model, side)` | The Hand of that side and its finger paint order. Used to pull a hand out from behind a rod |
| `ch.paint_fingers(canvas, model, side)` | Paints fingers one at a time. The thumb line is drawn faintly only inside the palm (`THUMB_LINE_ON_PALM` 0.35) so the thumb joins the palm |
| `Ink.lit_from(light, light3d)` | An Ink with only the light direction changed |

## garment

```python
from codepaint import garment
outfit = garment.formal_dress(dress="#a8202c", length=3.75, flare=1.0, wave=0.09, swirl=55)
Garment(name, group, paths, palette, lines=(), dots=(), order=0, shine=0.0, facing=0.0, merge="")
Hem(length, flare=0.2, wave=0.0, waves=7, swirl=0.0, drift=0.0)
```

| Call | Role |
|---|---|
| `casual_knit`, `casual_shirt`, `formal_dress`, `formal_suit`, `long_coat`, `mage_robe`, `light_armor` | Outfits. Each takes colors and returns "a function that takes a body and returns a list of pieces" |
| `loft(body, top, bottom, ease, hem=None, half=None, loose=0.0)` | Torso garment (Loft). `.outline()` screen outline, `.line_at(angle)` vertical line, `.ring_line(index)` horizontal line |
| `limb_span(body, bone, side, t0, t1, scale, widths=None, caps=(True, True), root=None)` | A band wrapped thickly around a bone span (sleeves, trouser legs, boots, bracers) |
| `limb_marks(body, side, [(bone, t, angle), ...])`, `limb_surface(...)` | Fold lines and points on the surface of clothed limbs |
| `shoe(body, side, growth, lift)`, `neck_band(body, height, ease)`, `bulge(body, part, center, radii)` | Shoes, scarves and high collars, round pieces (pauldrons) |
| `surface_curve(body, part, points)`, `surface_dots(body, part, points)` | Collars, front openings and buttons on the torso surface |
| `cloth(base)` | (base, shadow, light side, line) colors from one base color |

## stage

```python
from codepaint.stage import Stage, Collision, arm_toward, ELBOW_POLE
stage = Stage(origin, unit, elevation=0.0)        # origin is the screen coordinate of the world origin (floor center)
model = stage.place(look, x, z, turn, floor=0.0, head_pitch=0.0, ink=..., outfit=..., reach=None, pelvis_y=None,
                    grips=(), palm_out=(), poles=None, fists=None, **pose)
hits = stage.collisions([model_a, model_b])       # [Collision(model, limb, other, part), ...]. An empty list means no penetration
```

- `reach={"arm_r": world coordinates}` aligns the wrist, and `fists={"arm_r": world coordinates}` aligns the center of the closed fist (`fist_world`) to the target
- `poles={"arm_r": (outward, down, back)}` is the elbow direction of that arm (body coordinates). Omitted, it is `ELBOW_POLE` (0.45, 1.0, 0.35)
    + For two people standing shoulder to shoulder, the outward side of the inner arm faces the partner, so the default bends the elbow into the partner's body. Reduce the outward component to 0 or below
- With `palm_out=("r",)` the palm of that closed hand faces away from the body (toward the person beside). The fingers of two held hands wrap around each other
- The limb of a `Collision` is a bone name with side such as `forearm_r`, and part is `torso` or the name of the other person's arm bone

| Call | Role |
|---|---|
| `stage.project(points)`, `stage.point(x, y, z)`, `stage.depth(point)` | World coordinates to screen coordinates and view depth |
| `stage.joint_world(model, name)`, `stage.fist_world(model, side)`, `stage.to_world(model, point)` | World coordinates of a person's joint, fist center and body-coordinate point |
| `stage.far_first(models)` | Sort people far first |
| `stage.collisions(models)` | List of places where an arm bone center line enters another person's torso or two people's arm bones come closer than the sum of their thicknesses |
| `stage.box(x, y, z ranges)` | Visible faces [(name, outline, normal)] |
| `stage.cylinder(center, radius, top, bottom)` | {'side', 'top'} outlines. Paint the top after the side |
| `stage.ellipse(center, radius, y, radius_z=None)` | A circle parallel to the floor (table top, plate, floor shadow) |
| `arm_toward(shoulder, target, side, pole=ELBOW_POLE)` | Arm angles (two spreads, two swings) that bring the wrist to a body-coordinate target |

## head3d

```python
from codepaint.head3d import Head3D, HeadSpec, HairStyle, Lock, FEMALE_HEAD, MALE_HEAD
head = Head3D.on_body(body, FEMALE_HEAD, pitch=0.0)       # matched to the head position and angle of a Figure3D
head = Head3D(frame, spec=FEMALE_HEAD, yaw=0.0, elevation=0.0, pitch=0.0)   # the frame unit is the skull radius
HairStyle(thickness, hairline, locks, hang_from=0.3)
Lock(root, tip, width, lift=0.1, bulge=0.0, taper=(1.0, 0.95, 0.75, 0.35, 0.0), drape="", spread=0.0)   # root and tip are (phi, v)
```

| Call | Role |
|---|---|
| `head.silhouette()` | Head outlines [skull, face]. Paint them merged with `figure.shape_of` |
| `head.face(origin=(0, 0), unit=1.0, flip=False)` | Face table frame (FaceFrame). Frontal coordinates from craft.md go in and come out as screen coordinates at this angle |
| `face(points)`, `face.point(x, y, lift=0)` | A point list and a single point. The third value is the height above the face surface (nose bridge) |
| `face.child(x, y, unit)`, `face.mirrored()`, `face.length(value)` | Child frame (eye), mirroring, screen length |
| `face.facing(x, y)`, `face.ellipse(x, y, rx, ry)` | How much the face surface there faces the viewer, an ellipse attached to the face surface (iris, cheek blush) |
| `head.ear(side)` | (outer outline, inner helix line, facing value). Above 0.5 paint it over the head, below it paint it before the head |
| `head.nose_tip()` | Screen coordinates of the nose tip |
| `head.cap(style)` | List of outlines of the hair covering the scalp. Paint them merged |
| `head.face_window(style)` | Face area to cut out of the cap. None at angles where the face is hidden |
| `head.locks(style)` | Lock outlines by layer {"back": [...], "front": [...]}. back is painted before the body, front after the cap. Drape locks need the body, so use `hairstyles.lock_layers` |
| `head.lock_samples(style, lock, count)` | Head-coordinate points and normals of a lock center line |
| `head.shell(phi, v, offset)`, `head.hairline(style, phi)` | Point and normal on the scalp, height where hair starts. Used for light bands and strand lines |
| `head.facing(normal)`, `head.view_vector(vector)` | How much a head-coordinate normal faces the viewer, a direction converted to view coordinates (lighting) |

- The head angle phi is 0 at the face front, 90 at the side hair on screen right seen from the front, and 180 at the back of the head
- hairline takes (phi, v) over 0-180 degrees and is mirrored for both sides
- `Lock.drape` is the side (front or back) where a lock falling below the shoulders flows along the torso, and `Lock.spread` is how much it flares sideways as it goes down

## faces

Face templates. Usage and the list are in the face and hair templates section of `references/figure.md`.

```python
from codepaint import faces
FaceSpec(head, eye, eye_center, eye_unit, brow, nose_bridge, nose_tip_y, mouth, blush=(), blush_at=(0.55, 0.74),
         blush_radii=(0.2, 0.08), chin_shade=(), stubble=0.0)
EyeShape(white, white_corners, iris, pupil, gleam, lid, lid_corners, lower, lower_style, iris_span, sclera, pupil_color,
         crease=(), crease_style=(1.3, (0.2, 1, 0.2), 0.6))
BrowShape(points, fill=False, corners=(), width=2.8, taper=(0.7, 1, 0.1))
MouthShape(lips, line, line_width, line_taper, lower=(), upper=(), shade=(), philtrum=())
```

| Name | Content |
|---|---|
| `faces.FEMALE_MATURE`, `FEMALE_SOFT`, `FEMALE_SHARP` | Three female faces. Dict `faces.FEMALE_FACES` |
| `faces.MALE_CLEAN`, `MALE_GENTLE`, `MALE_RUGGED` | Three male faces. Dict `faces.MALE_FACES` |
| `faces.ALMOND_EYE`, `NARROW_EYE`, `DROOPY_EYE`, `CAT_EYE`, `GENTLE_EYE`, `DEEP_EYE` | Eye shapes |
| `faces.SOFT_FEMALE_HEAD`, `SHARP_FEMALE_HEAD`, `GENTLE_MALE_HEAD`, `RUGGED_MALE_HEAD` | Face shapes (jaw sections) |

- Coordinates use the same frontal basis as the craft.md face tables. Eyes use a child frame with the eye center as origin and an eye half-width of 1

## hairstyles

Hairstyle templates and long hair drape. Usage and the list are in the face and hair templates section of `references/figure.md`.

| Call | Role |
|---|---|
| `hairstyles.BOB`, `LONG_STRAIGHT`, `SHOULDER`, `PONYTAIL` | Four female styles (jawline bob, long straight, shoulder-length, ponytail). Dict `FEMALE_HAIRS` |
| `hairstyles.SHORT`, `SIDE_PART`, `CROPPED`, `MALE_LONG` | Four male styles (short, side part, cropped, long hair covering the neck). Dict `MALE_HAIRS` |
| `hairstyles.lock_layers(model)` | Lock outlines by layer {"back": [...], "tucked": [...], "front": [...]}. Drape locks are computed to flow along the torso, and locks passing behind the face go to tucked |
| `hairstyles.HairColor(base, shade, light, line)` | One hair color |
| `hairstyles.HAIR_COLORS` | Dict of 12 hair colors: black, dark_brown, chestnut, blonde, silver, pink, sky_blue, navy, red, purple, mint, orange |
| `hairstyles.head_to_body(model)` | (origin, matrix) that moves head-coordinate points to body coordinates. Moved points project to the same screen position |
| `hairstyles.drape(body, points, side)` | A body-coordinate center line with the span inside the torso pushed out past the side surface |

## Perspective

Usage is in `references/subjects.md`.

```python
Perspective(vanish, eye_height=1.6, focal=900.0)
```

| Call | Role |
|---|---|
| `project(x, y, z)` | Project a scene point (x left-right, y height, z depth) to screen coordinates |
| `path(points)` | Project a scene point list to a screen path |
| `scale_at(z)` | Screen length of a scene length of 1 at depth z |
| `side_wall(x, z_near, z_far, y_bottom, y_top)` | A wall receding in depth |
| `front_wall(x_left, x_right, z, y_bottom, y_top)` | A wall facing the camera |
| `ground(x_left, x_right, z_near, z_far, y=0.0)` | A rectangle on the ground |
| `side_wall_grid(x, z_near, z_far, y_bottom, y_top, columns, rows, margin=0.25)` | Cell list of a side wall (windows) |
| `front_wall_grid(x_left, x_right, z, y_bottom, y_top, columns, rows, margin=0.25)` | Cell list of a facing wall |

## styles

### anime

| Call | Role |
|---|---|
| `cel(canvas, outline, base, shade=None, amount=0.0, line=None, width=3.0, light=(-0.6, -0.8))` | One cel part: base color, automatic shadow, outline. Returns the filled shape |
| `rim_light(canvas, light, width=4.0, tint="#fff4dc", opacity=0.7)` | Rim light on the light-side contour of a transparent canvas |
| `finish(canvas, diffusion, bloom, shadows, highlights, grade_amount, aberration, grain)` | Returns the image with compositing effects |

### oil

```python
oil.render(canvas, brush_radii=(22.0, 10.0, 4.5), relief=0.55, weave=0.05, color_jitter=0.05, detail=None)
```

- Returns the underpainting repainted with layered brushstrokes
- With a shape in detail, the smallest brush is used only inside it

### watercolor

```python
watercolor.wash(canvas, outline, paint, opacity=0.85, soft=6.0, rough=7.0, blend=Blend.MULTIPLY, cover=False)
watercolor.render(canvas, wobble=2.2, bleed=0.55, turbulence=0.30, granulation=0.22, edge=0.55, paper_tint="#fbf7ee")
```

- `wash` paints one brushstroke and returns its shape
- `render` returns the image with pigment and paper effects

### illustration

```python
illustration.render(canvas, roughness=0.8, ink_mottle=0.10, paper_tint="#f7f1e3", paper_fiber=0.05, misregister=0.0)
```

- Returns the image with print texture

## solids

Usage is in the modern objects section of `references/subjects.md`. Scene coordinates are x right, y up, z depth.

| Call | Role |
|---|---|
| `box(center, size)` | Box. Face names front, back, left, right, top, bottom |
| `slab(center, size, radius=0.0, segments=10)` | Slab with rounded corners. Face names front, back, side |
| `prism(outline, depth, smooth_sides=False)` | Prism extruding an xy-plane outline along z |
| `cylinder(base_center, radius, height, top_radius=None, segments=64)` | Cylinder and frustum. Face names top, bottom, side |
| `circle(center, radius, segments=64)` | 3D point list on a horizontal circle |
| `solid.moved(offset)`, `solid.rotated(yaw=0, pitch=0, about=(0, 0, 0))` | Transforms that return a new Solid |
| `solid.face(name)`, `solid.center` | Find a face by name, center |
| `face.point(u, v)`, `face.region(u0, v0, u1, v1)` | 3D point and rectangle at 0-1 coordinates on a face |
| `Camera(eye, target, focal=1200, center=(800, 450))` | Perspective camera |
| `camera.project(point)`, `camera.path(points)` | Project to screen coordinates |
| `camera.depth(point)`, `camera.scale_at(point)` | Depth, and the screen length of a length of 1 at that depth |
| `camera.visible_faces(solid)`, `camera.order(solids)` | Visible faces and solids sorted far first. order sorts by center depth, so leave out supporting faces such as desks |
| `camera.region(face, u0, v0, u1, v1)` | Screen path of a rectangle on a face |
| `camera.face_ellipse(face, u, v, radius_u, radius_v=None)` | Screen path of an ellipse on a face |
| `face_color(base, normal, light, ambient=0.35, highlight=0.25)` | Face color by the light angle |
| `draw(canvas, camera, solid, paint, light, line=None, width=2.0, opacity=1.0)` | Paints a solid and returns a dict of shapes by face name |

- `paint` is one color or a `{face name: color}` dict. Faces missing from the dict use the color of `"*"`

## props

Every function returns a `Prop`. position is the bottom center of the object (cm), and yaw is clockwise seen from above.

| Call | Parts (solids) | Faces (faces) |
|---|---|---|
| `laptop(position, yaw=0, size=(31, 21.5), open_angle=108)` | base, lid | screen, deck |
| `monitor(position, yaw=0, size=(60, 34), stand_height=11, tilt=6)` | foot, neck, panel | screen |
| `keyboard(position, yaw=0, size=(44, 13.5), height=2.0)` | body | keys |
| `phone(position, yaw=0, size=(7.2, 15.0), thickness=0.8)` | body | screen |
| `mug(position, radius=4.2, height=9.5, handle=True)` | body, line handle | surface |
| `book(position, yaw=0, size=(15, 2.6, 22))` | body | cover |
| `desk_lamp(position, yaw=0, reach=26, height=38, shade_radius=7)` | base, shade, line arm | point bulb |

| Call | Role |
|---|---|
| `prop.draw(canvas, camera, paints, light, line=None, width=2.0)` | paints is `{part name: color or dict of colors by face name}`. Line parts are drawn only when they have a color |
| `keycaps(canvas, camera, face, color, rows=5, columns=15, gap=0.18, light_edge=None, area=(0, 0, 1, 1))` | Key grid on a face |
| `LAPTOP_KEY_AREA`, `LAPTOP_TOUCHPAD` | Key area and touchpad area on the laptop deck face |

## post

Every function takes an image and returns an image.

| Call | Role |
|---|---|
| `bloom(image, threshold=0.75, radius=24.0, strength=0.5)` | Glow from bright areas |
| `diffusion(image, radius=12.0, strength=0.3)` | Soft atmosphere over the whole frame |
| `grade(image, shadows=None, highlights=None, amount=0.15, contrast=1.0, saturation=1.0)` | Color grading that tints shadows and highlights |
| `vignette(image, strength=0.25, softness=0.75)` | Darkens the edges to pull the eye to the center |
| `grain(image, amount=0.03, seed=0, size=1.0)` | Film grain |
| `chromatic_aberration(image, shift_px=1.0)` | Lens chromatic aberration |
| `light_gradient(image, color, start, end, strength=0.3, screen=True)` | Light or shade from one side of the frame. start and end are 0-1 frame ratios |

- radius and shift_px are in pixels, so pass `value * canvas.scale`

## io

| Call | Role |
|---|---|
| `save(image, path)` | Save as PNG. Creates the folder if missing |
| `crop(image, box, scale, zoom=2.0)` | Crop and enlarge the logical box |
| `sheet(images, columns=2)` | Lay several images on one sheet. For comparing stages |

## noise

| Call | Role |
|---|---|
| `fbm(shape_hw, scale_px, seed, octaves=4)` | Fractal noise 0-1 |
| `value_noise(shape_hw, scale_px, seed)` | Smooth noise 0-1 |
| `white(shape_hw, seed)` | White noise 0-1 |
| `paper_texture(shape_hw, seed, scale=1.0)` | Watercolor paper tooth |
| `canvas_weave(shape_hw, seed, scale=1.0)` | Canvas weave pattern |

- Scene code rarely uses these directly. They serve when building a new style pass
