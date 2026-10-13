# API summary

## Contents

- Coordinate systems
- Character fields
- Head
- Palette and Material
- HairStyle
- Painter
- Backgrounds
- Render entry points
- Shape tools
- Relief renderer
- 3D figures
- 3D scenes
- Outdoor scenes
- Colour grades
- Hands and full-body figures
- Terrain and landscapes
- Cities
- Still lifes

## Coordinate systems

| Space | Origin | Unit | Use |
|---|---|---|---|
| Canvas units | Top left | 1000 x 1333 (y grows downward) | Background, props, head centre position |
| Head units | Skull centre | Skull radius = 1 | Face, hair |
| Body units | The hollow between the collarbones | Skull radius = 1 | Neck, shoulders, outfits |
| Eye units | Eye centre | Eye half width = 1 (x toward the outer corner) | Lids, iris, lashes |

- Pixel size is set by `px_per_unit`
    + Preview 0.8 (800 x 1066), final 1.6 (1600 x 2133)
- Key heights in head units
    + Crown -1.00, top of the hair -1.17, brows near 0.00, eyes 0.30, nose tip 0.72, mouth 0.945, chin 1.20
- Key positions in body units
    + Shoulder tip (1.40, 0.58), armpit (0.99, 1.12), sundress neckline y 0.95-1.12

## Character fields

| Field | Default | Meaning |
|---|---|---|
| `palette` | `default_palette()` | All colours |
| `hair` | `long_windy_hair()` | Hairstyle data |
| `head_center` | (445, 505) | Head centre, canvas units |
| `head_radius` | 228 | Head size; larger fills more of the frame |
| `roll` | 0.06 | Head tilt (radians), positive clockwise |
| `yaw` | -0.22 | Head turn; negative faces image left, keep |yaw| within 0.3 |
| `eye_x`, `eye_y` | 0.41, 0.30 | Eye centre position |
| `eye_half_width` | 0.23 | Eye size; 0.20 a mature look, 0.25 a young look |
| `eye_open` | 1.0 | How open the eyes are; 0.6 sleepy, 1.15 wide open |
| `eye_slant` | 0.05 | Positive raises the outer corners |
| `gaze` | (-0.06, 0.0) | Gaze, direction on screen (eye units) |
| `smile` | 0.6 | 0 neutral, 1 a clear smile |
| `brow_tilt` | 0.0 | Positive raises the inner brows (gentle look), negative a determined look |
| `lower_face` | 1.0 | Length factor of the face below the eyes; 1.08-1.14 an adult face |
| `outfit` | `Outfit.STRAP_DRESS` | `STRAP_DRESS`, `LONG_SLEEVE_TOP` |
| `neck_offset` | (0.10, 1.64) | Reference point at the base of the neck, head units |
| `body_roll` | -0.04 | Shoulder tilt; opposite to the head reads naturally |
| `shoulder_half_width` | 1.42 | Half shoulder width |

- Change fields with `dataclasses.replace(default_character(), field=value)`
    + The dataclass is frozen, so fields cannot be assigned directly

## Head

- `Head(character)` converts points in head units to canvas units
    + `flat(points)` applies only the tilt, for props sitting over the whole head such as hats
    + `on_face(points)` applies the face curvature and yaw, for props on the face such as glasses or moles
    + `on_skull(points)` applies the scalp curvature and yaw, for props on the hair such as hairpins
    + `units(length)` converts a length in head units to canvas units

## Palette and Material

- `Material(base, shadow, line, accent=None, light=None)`
    + `base` flat colour, `shadow` shadow colour, `line` line colour, `accent` gradient end colour, `light` bright edge colour of soft shading
- `Palette` fields
    + Materials: `skin`, `hair`, `cloth`, `trim` (ribbon, collar)
    + Eyes: `iris_dark` (top), `iris_light` (bottom), `iris_glow` (lower reflection), `pupil`, `sclera`, `sclera_shadow`, `lash`
    + Other: `hair_highlight`, `brow`, `lip`, `blush`
- Write colours with `rgb("#RRGGBB")` and mix them with `mix(a, b, share)`

## HairStyle

| Field | Format | Meaning |
|---|---|---|
| `cap` | Points of a closed curve | Mass covering the skull; its bottom edge is the hairline |
| `back_mass` | Points of a closed curve | Dark mass behind the body |
| `back_locks` | List of `LockSpec` | Locks behind the body |
| `bangs` | List of `LockSpec` | Locks over the forehead, left to right |
| `side_locks` | List of `LockSpec` | Side hair falling in front of the shoulders |
| `flyaways` | List of `LockSpec` | Thin stray hairs that break the silhouette, width 0.02-0.03 |
| `highlight_radius` | 0.80 | Radius of the highlight band |
| `highlight_thickness` | 0.17 | Largest half width of the highlight band |

- `LockSpec(root, tip, width, bend=0, sway=0)` is in head units
    + By default the fringe ends near y 0.10 above the eyes and near y 0.30 between the eyes

## Painter

| Method | Function |
|---|---|
| `part(name, mask, material, roundness=0.4, casts=(), tone=None, outline=True, volume=1.0, detail=None)` | Draws flat colour, shading and lines at once |
| `cast(occluder, receiver, offset_units)` | Returns a cast shadow mask |
| `stroke(points, width, color, taper, opacity, clip)` | A stroke of varying width |
| `fill(polygon, color, opacity, clip)` | A flat shape without shading |
| `glaze(mask, color, opacity)` | A transparent colour glaze (blush, lips) |

- `painter.canvas.mask(polygon, ...)` turns a polygon in canvas units into a 0-1 mask
- `painter.canvas.soft_ellipse(center, rx, ry, rotation)` is an ellipse with a soft edge
- `painter.canvas.part(name)` is the accumulated mask of a drawn part
    + Registered names: `hair_back`, `body`, `cloth`, `bow`, `face`, `eyes`, `mouth`, `hair_front`

## Backgrounds

| Function | Content |
|---|---|
| `vertical_gradient(canvas, top, bottom)` | Vertical gradient |
| `summer_sky(canvas, clouds, light)` | Blue sky with cumulus; `clouds` is a list of `(base centre, width, height, puff count)` |
| `sun_glow(canvas, center, radius)` | Glow of light |
| `flat_graphic(canvas)` | Flat composition of a circle and leaves |
| `studio_backdrop(canvas)` | Dark ground with a warm pool of light |
| `bokeh_dusk(canvas)` | Evening gradient with bokeh |
| `gradient_stops(canvas, stops)` | Vertical gradient through several colours; `stops` is a list of `(height share, colour)` |
| `cumulus_clouds(canvas, clouds, light, colors)` | Adds cumulus over an already painted sky; `colors` is `(light, shade, deep shade)` |
| `stars(canvas, count, bottom_y)` | Stars |
| `beach(canvas, light, horizon_y, shore_y, clouds)` | Sky, sea, surf line, sand |

## Render entry points

- `studio.render(compose, style, output_path, px_per_unit, seed, light, units_size, finishing, review, grade)`
    + `style` is `"anime"`, `"illust"` or `"painterly"`
    + `review=True` also saves `_overview.png` and `_face.png`
    + `finishing=False` saves the state before finishing, used to tell which stage a defect comes from
- `studio.run_cli(scene_name, compose, units_size, light, description, grade)` provides the command line `--style`, `--grade`, `--out`, `--preview`, `--seed`, `--no-review`
    + `grade` is the scene's default colour grade (a `grade.GRADES` name); `--grade none` turns it off
    + The order is `compose` → style finish → `canvas.overlays` (overlays such as falling snow) → colour grade
- `light` is an `(x, y, z)` direction (x right, y down, z toward the viewer); figure shading, shadows, rim light, floor shadows and cloud shading all follow it
    + Landscape-format pictures use `units_size=(1333.0, 1000.0)`
- `canvas.importance` is the area for fine brushes in painterly (a 0-1 map), and `canvas.shade_subject_as_one` sets whether the whole subject gets one light-to-dark gradient
- `canvas.overlays` is a list of `function(canvas)` run after the style finish (weather that brushwork and line art must not touch)
- Painterly brush detail on faces is automatic by face size (`finish.SMALL_FACE_UNITS`, `FACE_DETAIL`, `FACE_JOIN_UNITS`)
- The default light is `DEFAULT_LIGHT = (-0.52, -0.60, 0.61)` (upper left, in front)
    + Changing the light also needs the position constants of eye highlights and hair shine adjusted

## Shape tools

| Function | Purpose |
|---|---|
| `geometry.catmull_rom(points, closed)` | Smooth curve through every control point |
| `geometry.ellipse(center, rx, ry, rotation)` | Ellipse polygon |
| `geometry.lock(root, tip, width, bend, sway)` | Leaf-shaped lock, returns `(polygon, centre line)` |
| `geometry.ribbon(centerline, widths)` | Band polygon round a centre line |
| `geometry.Frame(origin, scale, rotation).apply(points)` | Converts local coordinates to canvas units |

## Relief renderer

Add parts to `relief.Relief(canvas)` from back to front, then call `render(painter)` once.

| Method | Purpose |
|---|---|
| `add(name, mask, material, thickness=1.0, depth=0.0, height=None, tone=None, gloss=0.0, drape=False, bridge=0.0, edge=True)` | Adds a part |
| `bump(mask, thickness, fade=None)` | A swell with a rim (keeps the material) |
| `swell(soft_mask, height_units)` | A swell without a rim, used with `canvas.soft_ellipse()` |
| `groove(mask, depth_px)` | A dent; negative depth is a raised ridge |
| `tint(mask, color, opacity, only=None)` | A colour glaze on the surface; `only` names the receiving parts |
| `visible(*names)` | Mask of the pixels where those parts show |
| `render(painter, cast_shadows=True, lines=True)` | Computes lighting, shadows and lines and composites them onto the canvas |

- `thickness` 1.0 gives a semicircular cross-section; smaller values are flatter
- Equal `depth` merges without seams like a joint, and `depth=FRONT` puts a part in front of every form below
- `height` is a hand-made height map (pixels); solids of revolution use `lathe_height(canvas, axis_x, top_y, bottom_y, profile(points))`
- `gloss` runs from 0 (matte) to 1 (glass)
- `bridge` is the size of the hollow a laid-on cloth spans (canvas units), and `edge=False` leaves out the border line of a part growing out of the form below (an arm at the shoulder)

## 3D figures

### Coordinates and units

| Space | Origin | Unit | Axes |
|---|---|---|---|
| Figure space | Pelvis | Head height = 1 | x image right in the front view, y down, z toward the viewer of the front view |
| Joint local space | Joint | Head height | The bone runs along local +y; convert to figure space with `skeleton.point(joint, local_point)` |
| Head local space | Head joint | Head height | The front of the face is +z, skull centre (0, -0.05, -0.03) |
| Screen | Canvas units | `head_height` canvas units = head height 1 | `Camera3D` rotates figure space, then projects orthographically or in perspective |

### figure3d

| Item | Content |
|---|---|
| `Figure3D(character, build, pose, hair, outfit, position, ground, head_height, yaw, pitch, head_scale, ground_shadow, props, distance)` | 3D figure spec; `outfit=None` shows the bare form for checking |
| `draw_figure3d(painter, figure, relief=None)` | Draws and returns `(relief, depth_image, skeleton, renderer)` |
| `figure_parts(figure)` | Builds `FigureParts(skeleton, solids, decals, context, held)` without a camera (for scene composition) |
| `finish_figure(painter, renderer, image, figure, parts)` | After lighting: outfit lines, hair strands, the face, screens of held objects |
| `lowest_sole(skeleton)` | Figure-space y of the lower sole (floor height for sitting poses) |
| `ground_points(parts)`, `floor_level(parts)` | Figure-space points touching the floor (soles when standing, the lowest parts when lying or kneeling) and their height, used by `ground` and scene placement |
| `floor_shadow(canvas, view, parts, light)` | Floor shadow round the parts touching the floor, projected with the camera's perspective (shared by single figures and scenes); it leans away from the light and lengthens with a low light, constants `FLOOR_SHADOW*` |
| `FLOOR_SLACK` 0.06, `FLOOR_BAND` 0.12 | Parts lying this much lower than the soles touch instead; parts within this height of the floor count as resting on it |
| `stool(skeleton, character, material=None)` | Stool for sitting poses, passed as `props=(stool,)` |

| `Figure3D` field | Default | Meaning |
|---|---|---|
| `character` | Required | Palette and face settings; face presets `adult_face()`, `male_face()` |
| `build` | `FEMALE_AVERAGE` | Build |
| `pose` | `STAND` | Pose |
| `hair` | `LONG_HAIR` | Hairstyle |
| `outfit` | None | Outfit |
| `position` | (500, 640) | Canvas position of the pelvis |
| `ground` | None | Canvas y of the floor; when set, the parts touching the floor (`ground_points`) are put on it |
| `head_height` | 158 | Canvas length of head height 1 |
| `yaw` | 0.0 | 0 front; positive turns the front toward image right; π back |
| `pitch` | 0.16 | Positive looks down |
| `head_scale` | 1.0 | 1.0 realistic proportion, 1.08-1.15 the larger anime head |
| `ground_shadow` | True | Shadow under the feet |
| `props` | () | List of `f(skeleton, character) -> solids or Prop3D`; held objects are `props3d.held_*()` |
| `distance` | None | Eye distance for perspective (head heights); None is orthographic |

### rig3d

| Item | Content |
|---|---|
| `Build(sex, shoulders, bust, waist, hips, thighs, limbs, muscle)` | Build, presets `FEMALE_AVERAGE`, `FEMALE_FULLER`, `MALE_SLIM`, `MALE_ATHLETIC` |
| `Pose3D(rotations, hands, reach)`, `pose(hands=None, reach=None, **joint=(rx, ry, rz))` | Pose |
| `Reach(target, pole, wrist, fingers, palm)` | Inverse kinematics that puts a hand on `target=(joint, local_point)` |
| `HandPose3D(curl, spread, thumb_out, thumb_curl)` | Hand pose, presets `RELAXED`, `OPEN`, `FIST`, `POINTING`, `HOLDING`, `PEACE`, `FLAT_HAND`, `TYPING`, `PHONE_GRIP`, `CUP_GRIP`, `PAD_GRIP`, `RUN_HAND`, `POCKET_GRIP`, `CUPPED`, `SMOKE_GRIP` |
| `POSES` | `stand`, `a_pose`, `contrapposto`, `hand_on_hip`, `arms_crossed`, `walk`, `sit`, `wave`, `point`, `think`, `hands_behind`, `cheer`, `peace`, `sit_type`, `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug`, `sit_game`, `run`, `kneel`, `kneel_sit`, `lie_back`, `lie_front`, `hands_in_pockets`, `stand_smoke` (left hand in a pocket, cigarette in the right), `sit_smoke` (cigarette in front of the chest) |
| `hand_frame(skeleton, side)` | Hand frame (y along the fingers, z out of the back of the hand, x across the knuckles) and the sign of the thumb side |
| `pose_skeleton(Skeleton3D, joints(build), pose)` | Computes joint positions and rotations (forward then inverse kinematics) |
| `mirrored(pose)` | The pose with left and right swapped (rotations, hand poses, hand targets) |
| `joints(build)` | Skeleton; joint names are `pelvis`, `spine`, `chest`, `neck`, `head` and left and right `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle` |
| `body_solids(skeleton, build, skin, hands)` | Bare body forms |
| `torso_solids(skeleton, build, skin)` | Torso without limbs: neck, chest, buttocks, trapezius (the surface strings and pockets lie on) |
| `neck_path(skeleton, build)` | `(points, radii)` of the neck, constants `NECK_BASE`, `NECK_TOP`, `NECK_BASE_SCALE` |
| `TRUNK`, `TRUNK_LANDMARKS`, `ARM`, `LEG`, `FOOT` | Torso section table and limb control points |
| `breast_shape`, `pec_shape`, `glute_shape`, `deltoid_shape`, `trapezius_shape` | Centres and radii of muscle and fat masses |

### head3d

| Item | Content |
|---|---|
| `Hair3D(cap_center, cap_radii, bangs, bang_length, bang_width, frame_locks, sweep, spikes, lobes, back_length, back_width, tips, side_locks, ponytail, ears, scalp_drop, nape)` | Hairstyle; `tips` is a list of `(across share, length share)` of the strands at the end of the back hair |
| `BACK_TIPS`, `back_sheet(skeleton, hair)`, `back_tips(skeleton, hair)` | Default end strands for long hair, sections of the back sheet and the end strands |
| `LONG_HAIR`, `BOB_HAIR`, `PONYTAIL_HAIR`, `MALE_SHORT_HAIR`, `MALE_MEDIUM_HAIR` | Provided hairstyles |
| `head_solids(skeleton, sex, skin, ears)`, `hair_solids(skeleton, hair, material)` | Skull and hair forms |
| `draw_face(painter, renderer, image, skeleton, character)` | Face treatment to match the angle |
| `FRONT_LIMIT` 0.85, `PROFILE_LIMIT` 2.05 | Border angles of the front face and the profile |

### wardrobe3d

| Item | Content |
|---|---|
| `OUTFITS` | `crop_top_hot_pants`, `hoodie_jeans`, `hoodie_shorts`, `tank_top_jeans`, `sundress`, `bikini`, `t_shirt_jeans`, `shirt_trousers`, `swim_trunks`, `suit`, `winter_beanie`, `winter_headphones`, `hoodie_beanie` |
| `puffer(ctx)`, `beanie(ctx)`, `headphones(ctx)` | Down jacket (layer 3, quilting lines `outer_line`, stand-up collar, zip), beanie (a head-local ellipsoid cut at the brim plane, folded cuff, rib lines, slot `hat`), headphones worn on the head (slot `gear`) |
| `PUFFY`, `PUFFER_QUILT`, `PUFFER_COLLAR`, `BEANIE_CROWN`, `BEANIE_BRIM`, `BEANIE_CUFF`, `HEADPHONE_BAND`, `HEADPHONE_CUP` | Winter wear measurements |
| `GARMENTS` | Registry of garments, `(ctx) -> Piece(solids, decals)` |
| `Outfit3D(garments, colors)` | List of garment names and a `Material` per slot |
| `GARMENT_LAYERS`, `LAYER_GAP` | Layer numbers of layered garments and the gap between layers |
| `TIGHT`, `FITTED`, `LOOSE`, `BULKY` | Thickness off the skin |
| `trunk`, `sleeve`, `leg`, `chest_cover`, `seat_cover`, `hip_cover` | Cloth lifted off each part of the body |
| `ring_curve`, `limb_ring`, `decal`, `chest_point` | Curves for seams and hem lines |
| `flat_hem(points)` | A hem ending flat at the tube's last point (prevents balloon ends) |
| `over_skin(ctx, path, clearance, hug=False)` | Resamples a string path densely and pushes it out of the torso surface; `hug=True` also pulls floating points onto the surface; `ctx.skin()` is `torso_solids` |
| `strap_over_skin(ctx, path, slot, half_width, half_thickness)` | Flat shoulder strap lying along the skin (tank top, sundress) |
| `hem_cut(ctx, hem)` | Cut test below the section plane at trunk position `hem`, shared by the torso and hip cover of a top over bottoms |
| `hood(ctx)` | The roll behind the neck and the hood layer lying on the back |
| `front_seam(ctx, thickness, slot)` | Front centre seam decal of shorts (automatic for leg lengths under `SHORTS_LENGTH`) |
| `pocket_sides(ctx)`, `pocket_hands(ctx, thickness, slot, sleeve_room)` | Sides with a hand in the front pocket, cloth covering the hand (tops covering the hips stretch it up the forearm by `POCKET_SLEEVE_ROOM` and widen it) |
| `tuck_into_pocket(ctx, side)` | Cut that ends the long sleeve of a hand in a pocket above the wrist (`POCKET_TUCK`, no inner wall) |
| `bikini_cup`, `bikini_strings`, `side_tie`, `_cup_corner` | Triangle cups, halter, back string and connector, ties at the hips, the visible cup corner |
| `_skirt_fall(ctx, hip_frame)` | Direction a skirt falls (down when standing, along the thighs when sitting), `SKIRT_LAP_BEND` |
| `pocket_hands(ctx, thickness, slot)` | Cloth covering a hand in the front pocket (called automatically by trousers-type garments) |
| `fabric(base, shadow, line, light)` | Makes a cloth `Material` |

### body3d

| Item | Content |
|---|---|
| `ellipsoid(center, axes, radii, material, group, name, gloss)` | Rotated ellipsoid; `axes` is a 3x3 whose columns are the local axes |
| `sweep(points, radii, material, group, name, caps, gloss)` | Sphere chain through control points (limbs, fingers) |
| `section_sweep(sections, material, step, overlap, group, name, gloss, cut)` | Form joining elliptical sections (torso, hair locks) |
| `solid.cut = f(figure-space points) -> bool array` | Cuts the front face where true to show the back face (jacket opening, face opening, bikini openings) |
| `Camera3D(origin, scale, yaw, pitch, distance=None, shift=(0, 0, 0))` | Camera; `distance` is the eye distance for perspective (None is orthographic), `shift` is an object's position in a scene |
| `DepthRenderer(canvas, camera).draw(solids)`, `.result()` | Depth, material and part buffers |
| `renderer.with_camera(camera)` | A renderer for another object sharing the buffers (objects in one scene hide each other) |
| `renderer.project(points)` | Screen pixel positions and depths of figure-space points |
| `RIGID_PREFIX` | Groups starting with `"rigid"` do not melt into each other (rigid objects) |
| `to_relief(relief, image, px_per_head)` | Passes the depth map to `Relief` to compute lighting and lines |
| `visible_runs(renderer, image, points, tolerance, material)` | Stretches of a curve that are not hidden |
| `SMOOTH_BLEND` 0.10, `CLOTH_BLEND` 0.06 | Width over which forms of the same group melt together (skin and hair, clothes) |
| `SECTION_BLEND` 0.02 | Width that fills the creases between neighbouring section ellipsoids |
| `SECTION_OVERLAP` 7.0, `SECTION_END_REACH` 3.0 | How far section ellipsoids extend along the path (multiples of the spacing), and at both ends |
| `SWEEP_BLEND` 0.02 | Width that fills between neighbouring spheres of a chain (prevents cel shadow sawtooth), 25% of the radius for thin chains |
| `SWEEP_SPACING` 0.22, `SWEEP_SUBPIXEL_RADIUS_PX` 1.0, `SWEEP_SUBPIXEL_SPACING` 1.0 | Sphere spacing in a chain (share of the radius); thin chains with a screen radius under one pixel use spheres just touching, painting the same pixels with fewer spheres |
| `SURFACE_SMOOTH` 0.022 | Height map blur width that removes leftover ridges |
| `LINE_JUMP_SMOOTH`, `LINE_MIN_LENGTH` | Width over which occlusion-line depth differences are averaged along the border, and the threshold for dropping short line pieces |
| `distance_to_solids(points, solids)` | Approximate signed distance to the union of forms (negative inside), used by string placement and the overlap check |
| `cut.lining = False` | Attached to a cut test, no inner wall is drawn at the cut (the hem of a thin cover) |
| `SLIVER_AREA` 0.004 | Enclosed gaps between soft forms up to this area (square head heights) are filled with the farther form and the lines round them left out; holes enclosed by rigid objects stay open |

### Faces

- `character.male_face(character)` is the adult male face preset (narrow eyes, low brows, a longer lower face, dark irises, darker skin)
    + The male face changes `lash_weight` (0.55), `lash_flicks` (False), `brow_weight` (1.65), `iris_scale` (0.88), `lip_tint` (0.30) and `blush_strength` (0.35) of `Character`; the defaults are all 1.0 and True
- Gaze is set like `replace(character, gaze=(0.0, 0.10))`, with positive y looking down (eyes on a phone)
- `character.adult_face(character)` is the adult female face preset

## 3D scenes

### Coordinates and units

| Space | Origin | Unit | Axes |
|---|---|---|---|
| World | Any point on the floor | Head height = 1 = 23 cm | x image right (scene yaw 0), y down (floor y = 0), z toward the camera |
| Object space | Centre of the object's base | Head heights, converted with `props3d.cm(centimetres)` | The front is +z, up is -y |

### scene3d

| Item | Content |
|---|---|
| `SceneCamera(target, origin, scale, yaw, pitch, distance)` | Scene camera; the world point `target` lands on canvas `origin`, and `scale` is the canvas length of head height 1 at that depth |
| `camera.for_object(at, yaw)` | `Camera3D` for an object placed in the world |
| `camera.project(points)`, `camera.eye()` | Canvas positions and depths of world points, the eye's world position |
| `Placed(item, at, yaw)` | Scene item; `item` is a `Figure3D` or a `Prop3D`, and a figure's `at` is the floor point under the pelvis (the lowest part touches this height) |
| `draw_scene3d(painter, camera, items, relief=None, lighting=None)` | Draws into one depth buffer and returns `(relief, depth_image, renderer)`; `lighting(canvas, image)` runs after lines and faces and before screens, bulbs and smoke (night lighting) |
| `anchor(placed, key)` | World position of an anchor (`Prop3D.anchors`) of a placed object |
| `seated(figure, placed, key="seat", turn=0.0)` | A figure seated on a chair or sofa seat |
| `on_top(item, placed, offset, yaw, key="top")` | An object on the top of a desk, table or counter; `offset` is (x, 0, z) in the furniture's frame |
| `overlaps(items, tolerance)` | Pairs of objects and furniture sharing more volume than `tolerance` (1 cm³), a list of `Overlap(first, second, depth, volume)` |

### sdf3d

| Item | Content |
|---|---|
| `Box(half, radius)` | Rounded box |
| `Slab(half, corner, edge)` | Slab with rounded corners in plan (phone, panel, table top, cushion), thickness along local y |
| `Cylinder(radius, half_height, edge)`, `Cone(top, bottom, half_height, edge)` | Upright cylinder, truncated cone |
| `Torus(major, minor, arc)` | Ring in the local xz plane; `arc` keeps part of it (a handle) |
| `Moved(shape, offset, rotation)`, `Union(*shapes)`, `Cut(keep, carve)`, `Grid(shape, spacing, counts)` | Move, union, subtraction (a hollow cup), grid repeat (keyboard) |
| `sdf_solid(shape, center, axes, material, group, name, gloss)` | Form passed to the depth renderer |
| `turn_x`, `turn_y`, `turn_z` | Rotation matrices |
| `MAX_STEPS`, `HIT_PX`, `GRAZE_PX` | Ray marching steps and hit distances |

### props3d

| Item | Content |
|---|---|
| `Prop3D(name, solids, screens, decals, glows, footprint, rests_on, detail, anchors, glass, wisps)` | Object; `rests_on` names the furniture receiving its contact shadow, `detail` is painterly brush detail, `glass` holds clear parts, `wisps` holds smoke and steam |
| `Wisp(points, width, color, opacity)`, `smoke_path(source, rise, seed, sway)`, `smoke_wisps(source, seed)`, `draw_wisp` | Threads of smoke that widen and fade as they rise |
| `Screen(corners, content, material, brightness)`, `Glow(point, radius, color, strength)` | Glowing screens and bulbs |
| `laptop(lid_angle, screen)`, `monitor(screen, tilt)`, `keyboard()`, `mouse()`, `phone(screen)`, `tablet(screen)` | Devices |
| `headphones()`, `game_controller()`, `television(screen)` | Devices |
| `mug(body, drink)`, `paper_cup()`, `book()`, `book_stack(count, seed)`, `desk_lamp(lit)`, `potted_plant(height, seed)` | Household items |
| `drinking_glass(fill, drink, glass)` | Clear drinking glass with a drink |
| `cigarette(lit, smoke, seed)`, `ashtray(butts, lit, seed)`, `tea_glass(fill, drink, holder, steam, seed)` | Cigarette (ember `Glow`, smoke), ashtray (butts, a cigarette resting on the rim), tea glass in a metal holder (steam) |
| `cassette()`, `cassette_player()` | Audio cassette, portable cassette player with two speakers, a deck and an aerial |
| `cable(points, sag, radius, material)` | Cable through points (the points are where it touches, the axis lies one radius above), placed in world coordinates as they are with `Placed(cable)` |
| `finish_glass(painter, view, image, solids)` | Second-pass composite of clear parts (show-through, colour toward the outline, highlight, outline), called automatically by `finish_prop` |
| `GLASS_BODY`, `GLASS_EDGE`, `GLASS_RIM`, `GLASS_SHINE`, `GLASS_HIGHLIGHT`, `GLASS_LINE` | Glass constants |
| `held_phone(side, screen)`, `held_mug(side)`, `held_controller()`, `held_cigarette(side, lit, seed)` | Objects attached to the hand frame, passed in `Figure3D.props`; the cigarette sits between the index and middle fingers, pointing out of the back of the hand (`CIGARETTE_IN_FINGERS`) |
| `transformed(prop, origin, rotation)`, `frame(x_axis, y_axis)` | Moving an object, an orthonormal frame |
| `cm(value)`, `surface(base, shadow, line, light)`, `own_material(material)` | Unit conversion, making a material, copying a material for one object |
| `contact_shadow`, `finish_prop(..., lights=True)`, `light_prop` | Contact shadow; lines and glass after lighting; screens, lights and smoke (with `lights=False`, `light_prop` draws them separately) |

### furniture3d

| Item | Content |
|---|---|
| `desk`, `office_chair`, `sofa(seats)`, `low_cabinet`, `coffee_table`, `cafe_table`, `cafe_chair`, `counter`, `bookshelf`, `pendant_lamp(ceiling)`, `floor_lamp`, `rug` | Furniture, anchors `seat`, `seat_0..`, `top` |
| `bed(width, length, frame_material, sheet, duvet, pillows)` | Bed, anchors `top` (mattress), `duvet` (on the duvet), `lie_back_0..` (lying per pillow), `lie_back`, `lie_front` |
| `BED_TOP`, `LIE_HEAD`, `DUVET_SHARE`, `DUVET_LIFT` | Mattress height, z from pelvis to head when lying, share of the length the duvet covers, duvet height |
| `SEAT_TOP`, `SEAT_DROP` | Seat height that fits the sitting poses, pelvis to seat |
| `DESK_HEIGHT`, `TABLE_HEIGHT`, `COUNTER_HEIGHT` | Top heights |
| `radiator(sections, height_above_floor)`, `windowsill(width, depth, height)` | Cast-iron radiator (back toward -z), a sill standing out of the wall (anchor `top`, name `sill`) |

### interior

| Item | Content |
|---|---|
| `living_room()`, `office()`, `cafe()`, `bedroom()` | `Room(surfaces, items, places, size)`; `places` holds a `Placed` per furniture name |
| `draw_room(painter, camera, room, items)` | Paints the walls, then draws furniture and figures into one depth buffer |
| `Shell(x0, x1, z0, z1, height)`, `shell_surfaces(...)`, `trims(...)` | Floor, ceiling, 3 walls, skirting and corner shadows of a custom room |
| `on_back_wall`, `on_left_wall`, `on_right_wall`, `sunlight` | Wall decorations and sunlight patches from windows |
| `paint`, `planks`, `carpet_tiles`, `bricks`, `window`, `curtain`, `artwork`, `menu_board`, `outdoor_view`, `wallpaper(width, height, rng, ground, motif, stripe)` | Wall textures; window views `sky`, `city`, `street`, `panel_night` (the panel block across the yard at night), `city_night` (lit towers under the moon), `golden` (a low sun in a golden sky) |
| `SkyView(stops, skyline, lit_share, disc_color, disc_at, disc_size, stars)`, `SKY_VIEWS`, `sky_view(width, height, rng, view)` | A window view made of sky stops, a sun or moon and tower silhouettes; register a name in `SKY_VIEWS` to use it as `window(..., name)` |
| `Surface(corners, texture, facing)`, `draw_surface(canvas, camera, surface)` | Projected flat quad, left out when the eye is behind it; returns the mask of the painted area |
| `keep_detail(canvas, mask, detail)` | Asks painterly for fine brushes in the mask area (walls lined with windows, the view out of a window) |

### screens

- `render(content, width, height, rng)`, presets `desktop`, `code`, `video`, `chat`, `home`, `game`
- A new screen passes `function(width, height, rng) -> RGB image` as `Screen.content`

## Outdoor scenes

### outdoor

| Item | Content |
|---|---|
| `metres(value)` | Metres to head heights (1 m = 4.35) |
| `Light(wall, seam, glass, lit, lit_share, balcony, snow, snow_shade, ambient)`, `NIGHT`, `DUSK`, `OVERCAST`, `replace_light(light, **changed_fields)` | Outdoor light: building walls and windows, snow colours, ambient light on figures and objects |
| `Fog(color, distance, horizon_band, horizon_strength)`, `FOG_NIGHT`, `FOG_DUSK`, `FOG_OVERCAST` | Distance fog and horizon haze |
| `NIGHT_SKY`, `DUSK_SKY`, `OVERCAST_SKY`, `sky(canvas, stops, clouds, horizon)` | Sky colour stops (1.0 at the horizon), cloud layer |
| `Snow(count, size, opacity, streak)`, `SNOW_LIGHT`, `SNOW_HEAVY`, `snowfall(canvas, rng, snow)` | Falling snow |
| `facade(length_m, floors, rng, light, entrances, balconies)`, `panel_block(at, length, floors, rng, light, depth, yaw, entrances)`, `Block(surfaces, center)` | Panel block facade texture and box; `yaw` turns the long side away from facing +z (π/2 faces +x) |
| `draw_blocks(canvas, camera, blocks, fog)` | Paints from the farthest, mixing in fog by distance |
| `ground_plane(texture, extent, center)`, `snow_texture(rng, light, extent, paths)`, `road_texture(rng, light, extent, road_width, ..., along)`, `asphalt_texture` | Ground plane at y = 0, snowfield (trodden `paths` in plane coordinates 0..extent), a road through the middle (`along="x"` runs it along x) |
| `Lamp(at, color, reach, strength, cone)`, `SODIUM` | Light source; halves at `reach`, `cone` is the downward half angle (radians) |
| `light_ground(canvas, camera, lamps)`, `light_plane(canvas, camera, lamps, point, normal, ambient, mask)` | Light pools on the ground, lighting of any plane (a room wall); with `ambient` the lighting multiplies |
| `night_lighting(camera, ambient, lamps)` | Lighting for `draw_scene3d(lighting=...)`: ambient and lamp light on figures and objects |
| `draw_lit_room(painter, camera, surfaces, views, items, lamps, ambient, view_detail)` | A room lit by its own lamps: each surface is painted then lit, window views and sun patches (`views`) go on after the lighting, objects and figures share the same lamps |
| `wet_reflections(canvas, camera, lamps, width, strength)` | Streaks of lamp light reflected in a wet road |
| `catenary(a, b, sag)`, `draw_wires(canvas, camera, image, wires, width, color, tolerance)` | Points of a hanging wire, drawing wires hidden by depth comparison |
| `atmosphere(canvas, camera, image, fog)`, `horizon_y(camera)` | Haze, canvas y of the horizon |
| `world_points(canvas, camera, depth, where)`, `plane_points(canvas, camera, point, normal)`, `ground_points(canvas, camera)` | Working back from pixels to world coordinates |
| `World(light, sky, fog, ground, blocks, lamps, items, wires, snow, clouds, wet)`, `draw_world(painter, camera, world, rng)` | Contents of one outdoor picture and drawing it in the set order |
| `FACADE_DETAIL`, `GROUND_DETAIL`, `WIRE_DETAIL` | Painterly brush detail (facades, ground, wires) |

### street3d

| Item | Content |
|---|---|
| `street_lamp(height, arm, pole, housing, lit)`, `lamp_light(placed, color, reach, strength, cone)` | Street lamp with a concrete pole and an arm reaching toward +x (anchor `bulb`), the `Lamp` of that lamp |
| `power_pole(height, crossarm, wood, insulators, lean)`, `wires_between(poles, sag)` | Wooden power pole (anchors `wire_0..`), wires joining the same insulators of neighbouring poles |
| `bench(seats, slats, legs)` | Courtyard bench (facing +z, anchors `seat_0..`) |
| `bus_stop(width, depth, height, frame_material, seats, lit)`, `shelter_light(placed, reach, strength)` | Bus stop with glass walls (anchors `seat_0..`, `light`), the `Lamp` of its fluorescent tube |
| `birch(height, seed)` | Winter birch (white trunk, dark bark marks, thin branches) |
| `LAMP_HEIGHT`, `LAMP_ARM`, `LAMP_REACH`, `LAMP_CONE`, `POLE_HEIGHT`, `CROSSARM`, `WIRE_SAG`, `STREET_DETAIL` | Measurement and light constants |

## Colour grades

| Item | Content |
|---|---|
| `grade.Grade(saturation, shadow_tint, highlight_tint, split_strength, fade, contrast, halation_threshold, halation_radius, halation_color, halation_strength, grain, grain_size, vignette)` | Colour grade over the finished picture |
| `grade.DOOMER`, `grade.DOOMER_DAY`, `grade.GRADES` | Night (teal shadows, sodium orange halation, washed-out blacks, grain), overcast day |
| `grade.COZY_NIGHT`, `grade.LATE_SUN`, `grade.GOLDEN_HOUR` | Warm everyday grades (a room at night, late afternoon, outdoors at sunset) that keep saturation with light grain |
| `grade.apply(canvas, grade)` | Halation → saturation → split toning → fade and contrast → vignette → grain |

## Hands and full-body figures

| Item | Content |
|---|---|
| `rig_hand.draw_hand(relief, painter, frame, material, pose, view, mirror, name, depth, turn)` | Adds a hand and returns a function that draws nails and palm lines |
| `rig_hand.HandPose(spread, curl, bend, thumb_angle, thumb_curl)` | Hand pose |
| `rig_hand.OPEN_HAND`, `RELAXED_HAND`, `VICTORY_HAND` | Provided poses |
| `rig_figure.Figure(character, pose, pelvis, head_height, outfit, body, outfit_material, head_scale, ground_y)` | Full-body figure spec |
| `rig_figure.Pose(...)` | Joint angles and wrist angles; fields in `references/subjects.md` |
| `rig_figure.BodyShape(bust, waist, hips, thighs)` | Body width factors, presets `AVERAGE`, `SLENDER`, `HOURGLASS` |
| `rig_figure.FigureOutfit`, `rig_figure.OUTFITS` | Outfit names and the registry of outfit layer functions |
| `rig_figure.STANDING`, `CONTRAPPOSTO`, `HAND_ON_HIP`, `ARM_RAISED`, `A_POSE` | Provided poses |
| `character.adult_face(character)` | Adult face preset (lower face x1.12, smaller eyes) |
| `rig_figure.draw_figure(painter, figure)` | Draws the full body and returns `(relief, skeleton)` |
| `rig_figure.Skeleton(figure).joints` | Coordinates of `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle` for `left` and `right` |
| `character.long_straight_hair()`, `character.figure_palette()` | Long straight hair for full-body figures, a palette with deeper skin |

## Terrain and landscapes

| Function | Purpose |
|---|---|
| `terrain.alpine_lake_heightmap(rng, peak_height, sea_level)` | Returns `(height map, water level)` |
| `terrain.colorize(heightmap, sea_level, rng, light, palette)` | Returns `(colour map, ground height, water mask)` |
| `terrain.render(canvas, ground, color, water, camera, haze, haze_distance)` | Projection, returns `(terrain mask, water mask, depth)` |
| `terrain.Camera(position, eye_height, horizon, focal, far)` | Camera |
| `scenery.reflect_water(canvas, water_mask)` | Water reflection and ripples |
| `scenery.pine(painter, base, height, width)` | Conifer |
| `scenery.grass(canvas, top_y, blade_count, blade_height, flowers)` | Foreground meadow |

- The terrain light is a map-space vector `(x, y, z)`, with y running away from the camera

## Cities

| Function | Purpose |
|---|---|
| `city.StreetCamera(vanishing_point, focal, eye_height).project(points_xyz)` | Projects metre coordinates to canvas units |
| `city.Building(side, near, depth, height, wall, lit_share, shop)` | Building spec |
| `city.draw_buildings(canvas, camera, buildings, street_half_width, haze, layer, mirrored)` | Draws facades, returns an emission mask |
| `city.draw_road(canvas, camera, street_half_width, sidewalk)` | Road, pavements, lanes, crossing |
| `city.draw_signs(canvas, camera, signs, layer, mirrored)` | Projecting signs |
| `city.draw_lamps(canvas, camera, positions)` | Street lamps |
| `city.wet_reflection(canvas, mirror_layer, road_mask)` | Wet road reflection |
| `city.bloom(canvas, glow, color)` | Glow |
| `city.skyline(canvas, camera, rng, depth, count, haze)` | Distant high-rises |

## Still lifes

| Function | Purpose |
|---|---|
| `stilllife.room(canvas, table_back_y, table_front_y)` | Wall and table |
| `stilllife.lathe_object(relief, name, axis_x, top_y, bottom_y, radius_points, material, gloss, ...)` | Bottle, jug, pear |
| `stilllife.round_fruit(relief, name, center, radius, material, ...)` | Apple, orange |
| `stilllife.tilted_ellipse_fruit(relief, name, center, rx, ry, rotation, material)` | Lemon |
| `stilllife.grapes(relief, name, top_center, count, grape_radius)` | Bunch of grapes |
| `stilllife.cloth(relief, name, outline)` | Folded cloth |
| `stilllife.mouth()`, `band()`, `label()` | Spout, band pattern, label |
| `stilllife.table_shadow(relief, base, half_width, away)` | Shadow on the table |
| `stilllife.stem(painter, top_center, length, lean, leaf)` | Stem and leaf |

- Material constants are `RED_APPLE`, `GREEN_APPLE`, `ORANGE`, `LEMON`, `PEAR`, `GRAPE`, `GLASS`, `CERAMIC`, `PAPER`, `CLOTH`
