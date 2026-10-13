# Process details

## Contents

- Design brief template
- Drawing steps and code
- Shading principles
- Line art principles
- Hair construction
- Relief renderer principles
- 3D figure renderer principles
- 3D scene renderer principles
- Outdoor scene renderer principles
- Extending the rigs

## Design brief template

Write one `.md` file in the template below before writing the scene script. Settling the composition and colours in words before placing coordinates cuts the number of revisions.

```
# Design brief
## Key message
- The one impression the picture conveys
## Design direction
- (Space and structure) Aspect ratio, how much of the frame the figure takes, where the empty space is
- (Colour and tone) Main colour, accent colour, direction of the shadow colours
- (Proportion and rhythm) Base unit, repeated forms
- (Composition and balance) Head position, gaze direction, centre of weight
- (Visual hierarchy) Order in which contrast and detail are spent
## Layout
- Head centre coordinates, head radius, light direction, yaw, roll
## Style
- One of anime, illust, painterly, and the background
```

## Drawing steps and code

| Drawing step | Code | Note |
|---|---|---|
| Planning | Design brief | Settled before writing code |
| Layout | `Character`, `HairStyle`, `geometry` | Shape data in unit space |
| Flat colour | `material.base` in `painter.part()` | Solid colour or gradient in a mask |
| Shading | Form shading in `painter.part()`, `painter.cast()` | Computed from the mask |
| Line art | Outline in `painter.part()`, `painter.stroke()` | Coloured lines, varying width |
| Background | `background` module | Drawn before the figure |
| Finishing | `finish.apply()` | Finish per style |
| Review | `selftest.py`, enlarged review images | Checked by eye |

## Shading principles

- (Form shading) Build a height map by rounding off the mask's edges, then light it
    + `shading.bevel_light()` makes height from the distance to the border and computes the dot product of the normal and the light
    + `roundness` is the share of the rounded band relative to the shape's half width: 0.15 for the face, 0.75 for hair locks
- (Cast shadows) Move the caster's mask away from the light and intersect it with the receiver
    + Shadows of the fringe on the forehead, the head on the neck and the side hair on the shoulders carry most of the sense of volume
- (Cel versus soft) A threshold on the same light value gives cel shading, mapping it over a range gives soft shading
    + `Style.shade_mode` decides the branch, so scene scripts need not know the style
- (Large form) The finishing pass adds a gradient over the whole figure that darkens away from the light
    + Per-part shading alone does not give the figure a sense of one mass

## Line art principles

- Outlines are a band just inside the mask border
    + They grow up to 1.7 times thicker on the side away from the light, standing in for the pressure of an ink line
- Line colours are set per material
    + Red-brown for skin, dark brown for hair and navy for white cloth are softer than black lines
- Lines inside a part (hair strands, cloth folds, double eyelids) are strokes tapering at both ends from `painter.stroke()`
    + Pass the part mask to `clip=` so they stay inside the shape

## Hair construction

- Stack large masses, locks, strands and highlights in that order
    + Hair drawn strand by strand from the start does not read as hair
- The back hair puts `back_locks` (locks) over `back_mass` (a dark mass)
- The front hair puts `bangs` (forehead locks) and `side_locks` (side hair) over `cap` (the mass covering the skull)
    + The fringe locks fade their lines and shading at the root, so they join `cap` without a seam
- The highlight band is an arc at a fixed distance from the head centre
    + Jagged in cel styles, a smooth band in soft-shaded styles
- One lock is `LockSpec(root, tip, width, bend, sway)`
    + `bend` is the curvature relative to length; on a lock running down, a positive value bulges toward image left
    + `sway` is an S-curve, 0.03-0.08 for long hair

## Relief renderer principles

- (Inflation) The height of a rounded cross-section is computed from the distance to the part mask's border
    + A circle becomes a hemisphere and a long strip a half cylinder
- (Merging) Heights are compared per part and the higher one shows
    + Two forms at the same depth join without a seam where their heights meet, which makes joints natural
    + A form given more depth rises over the one behind, and that border becomes an occlusion line
- (Lighting) Normals come from the slope of the height map, and brightness from their angle to the light
    + A threshold gives cel shading, mapping over a range gives soft shading
- (Shadows) From each pixel, step toward the light; if a higher surface is met, the pixel is in shadow
- (Crevice darkening) Places lower than their surroundings' average are darkened to show where forms meet
- (Lines) Lines are drawn only at silhouettes, borders of forms in front and deep valleys
    + Steep slopes inside a form get no line, so surfaces stay clean

## 3D figure renderer principles

- (Forms) Body, hair and clothes are all ellipsoids, sphere chains and joined elliptical cross-sections
    + The torso is 10 cross-sections closely joined from crotch to neck, and the section axes blend the rotations of neighbouring joints so the torso joins without twisting
    + Section ellipsoids extend along the path up to 7 times the spacing (`SECTION_OVERLAP`) and overlap their neighbours far enough that no creases remain on the surface
    + Limbs and fingers are sphere chains of varying radius, and neighbouring spheres are joined with a narrow smooth maximum (`SWEEP_BLEND`)
    + Shallow creases between spheres tilt the normals a few degrees back and forth and show as a sawtooth on cel shadow edges, and this join removes the sawtooth
- (Depth) For each pixel, the depth of the surface nearest the viewer is computed analytically
    + Ellipsoids intersect the ray with a unit sphere, and spheres are heights over discs, so the curved surfaces are exact without a mesh
- (Melting together) Members of the same group (skin with skin, hair with hair, the same garment) merge with a smooth maximum so joints and armpits join without seams
    + The spheres of one form first merge among themselves, then blend once with the forms drawn before, so the swelling does not accumulate
    + Clothes lifted off the body by less than this swelling (at most `SMOOTH_BLEND`/4) let the skin poke through
- (Cutting) Surfaces where a `cut` function is true show their back face instead of the front, which makes jacket openings, the face opening and bikini openings
    + A form made of several pieces is cut once on the merged front face of its pieces, so the edge has no steps (`_cut_part`)
- (Lighting) The depth map is passed to `Relief` as its height map, and the same cel shading, cast shadows and lines as 2D subjects apply
    + The depth map is blurred only within one material, so shallow ridges between ellipsoids do not show as stripes
    + Lines are drawn only where depth jumps between different forms and where the material changes
    + Depth differences are averaged along the border before passing a soft threshold, so lines do not break into dots near the threshold
- (Surface lines) Seams, pockets and hair strands are 3D curves projected to the screen and drawn only where the surface depth and material at that point match
- (Face) Depending on the head's angle on screen, the 2D portrait rig (front to 3/4), a profile or no features (back view) is chosen
- (Pose) Forward kinematics from joint rotations, then arms with a `Reach` get their shoulder and elbow recomputed by two-bone inverse kinematics
    + The elbow direction is `pole`, the hand direction is `fingers` and `palm`, and the wrist bend stops at a limit
- (Narrow gaps) When an arm is a hair's width from the body, the background shows through as a lens shape and the lines trace round it into a white oval
    + Before the depth buffer is passed on, small empty areas enclosed by soft forms are found and filled with the farther form
    + The steep edge depth of the farther form is levelled toward its surroundings, and the occlusion and fold lines round it are left out
    + Holes enclosed by rigid objects (a mug handle and so on) are real holes and stay open
- (Floor contact) The lowest point of every ellipsoid and sphere is found analytically to decide which parts touch the floor
    + If no part lies `FLOOR_SLACK` or more below the soles, the soles touch; otherwise those parts rest on the floor, so lying and kneeling are handled by the same placement function
- (Strings that follow the surface) A string path is split every 1.5 cm, and only points whose approximate distance to the torso (`distance_to_solids`) is below the clearance are pushed out, with smoothing repeated
    + Points already clear stay where they are, so the string bridges hollows such as the cleavage

## 3D scene renderer principles

- (Perspective) Each pixel sends one ray, tilted from its point on the picture plane toward the eye
    + A point at depth z is `plane + z * direction`, and orthographic projection is the special case with direction (0, 0, 1)
    + Ellipsoids and spheres meet the ray through a quadratic equation, angular forms through ray marching
    + A camera without an eye distance uses the v4 code path as it was, so older pictures are byte-identical
- (Angular forms) A signed distance function gives the distance from a point to the surface (negative inside)
    + The ray starts where it enters the bounding sphere and advances by the distance; under 0.05 pixels counts as a hit
    + Subtraction (`Cut`) and union (`Union`) are the maximum and minimum of distances, so a hollow cup and its handle make one form
- (One scene) Each object is drawn into the same depth buffer with its own camera (`shift` and `yaw` holding its world placement)
    + `renderer.with_camera()` shares the buffer, so a figure's legs and the desk, the hands and the laptop hide each other per pixel
    + Rigid objects (group `rigid`) do not melt together, so a mug on the top gets a border line
    + Rooms are deeper than figures, so the base depth of the height map is lowered to the scene's farthest surface
- (Screens and lights) After lighting, screen contents are attached by perspective transform and a glow is added outside them only
    + Screens are found by a material of their own, so parts hidden by other objects are not drawn
- (Contact shadows) Objects on the floor get a soft shadow on the canvas, objects on a top get one on the surface colour of the furniture holding them
- (Interior walls) Floor, ceiling, 3 walls and decorations are textured quads
    + They are clipped at a plane 0.6 heads in front of the eye, projected, and textured with a homography
    + If the eye is behind the painted side's direction (`facing`), the quad is left out, so the room shows even when the camera stands outside a wall
- (Painterly) Hand-sized objects get fine brushes with importance 0.85, while furniture and walls are left to coarse brushes
    + Faces are measured on screen and the smaller they are, the higher their importance up to 1.0, so even small faces in a scene get the finest brush (0.9 units)
- (Glass) After the opaque pass, only the clear parts are drawn into a separate depth buffer and composited on pixels where they lie in front of the scene
    + The composite has 4 layers: a light tint, a colour deepening toward the outline (more glass in the line of sight), a highlight and a thin outline
    + The scene's depth buffer is not changed, so objects behind the glass show as they are
- (Overlap check) A 1 cm grid is laid over the space where two objects' bounding boxes overlap, and the volume of points inside both objects is counted

## Outdoor scene renderer principles

- (Stage) Buildings and the ground are flat pictures projected like interior walls and are painted before the 3D items
    + A building is the 4 sides of a box and a roof, and the facade texture has one window per storey and bay, joints, balconies and entrances
    + Buildings are painted from the farthest, mixed with fog colour by their distance from the eye
- (From pixels to the world) World coordinates come back from where a pixel's line of sight meets a plane, or from a pixel and its depth
    + Lamp light on the ground and walls and lamp light on figures and objects use the same world-coordinate formula, so light pools and figures match in brightness
- (Night lighting) After 3D items are drawn down to their lines and faces, each pixel is multiplied by `ambient + Σ lamp colour × strength × nearness`
    + Nearness is `1 / (1 + distance² / reach²)`, and a shaded lamp falls to 0 outside its downward cone
    + Screens, bulbs, embers and smoke are drawn after the multiplication, so they stay bright in dark scenes
- (Sky and haze) The sky's colour stops follow the horizon height; empty pixels get a band at the horizon and 3D items get fog by distance
- (Wires) Hanging wires (a parabola approximation) are projected and drawn as lines of constant width, leaving out stretches behind the depth buffer
- (Wet road) A vertical streak from under each lamp down to its mirror image below the ground imitates the reflection
- (Thin forms) Sphere chains with a screen radius under one pixel are drawn with spheres just touching
    + Such chains mark only the pixels their spheres cover, so the same pixels take at least 4 times fewer spheres, and landscapes with many birches render about 4 times faster
- (Overlays and grades) Falling snow comes after the style's finish (`canvas.overlays`), and the colour grade after that

## Extending the rigs

1. A new hairstyle is a function in `character.py` that returns a `HairStyle`
    + Start from the coordinates of `long_windy_hair()` and `short_bob_hair()` and edit them
2. A new outfit adds a value to `character.Outfit` and a drawing function and branch to `rig_body.py`
    + Multiply cloth shapes by the body mask so they do not leave the body
3. A new background is a function in `background.py` that fills `canvas.rgb`
4. A new style follows the steps in `references/styles.md`
5. Full-body outfits register a layer function in `rig_figure.OUTFITS` (steps in `references/subjects.md`)
6. A new pose adds a value of `rig_figure.Pose` with only the angles changed
    + Limb lengths are constants, so it must pass the length preservation check in `selftest.py`
7. A new subject starts from a copy of the nearest scene in `scripts/examples/`
8. A 3D outfit registers garment functions in `wardrobe3d.GARMENTS` and adds the combination and colours to `OUTFITS`
    + Layered garments add a layer number to `GARMENT_LAYERS`
9. A 3D pose is made with `rig3d.pose()` and registered in `rig3d.POSES`
    + For poses where a hand touches the body, `Reach` holds up to build changes better than joint angles
10. A 3D hairstyle starts from `replace(head3d.LONG_HAIR, ...)`
11. After extending, run `selftest.py` and check previews from the front, 3/4, side and back
12. A new object is a function in `props3d` that returns a `Prop3D`
    + Sizes are real measurements with `cm()`, the origin is the centre of the base, the front is +z, and a screen uses `_panel_screen()`
    + Adding the name to `PROP_BUILDERS` in `selftest.py` includes it in the render check
13. New furniture goes in `furniture3d`: seats use the seat height `SEAT_TOP` and the anchor `seat`, furniture to put things on uses `top`, furniture to lie on uses `lie_back` and `lie_front`
    + After placing it, check for interpenetration with `scene3d.overlaps()`
14. A new interior copies a room function in `interior` and changes the `Shell` size, wall textures, furniture layout and `places`
15. New screen contents register a `(width, height, rng) -> RGB` function in `screens.PRESETS`
16. A new held object attaches at a position and axes in the hand frame like `held_phone()`, and comes with a pose that sets the hand direction
17. Parts that run over the body, such as strings and straps, pass their path through `wardrobe3d.over_skin()`
18. Floor poses lay the body down with a pelvis rotation, then check with the floor items of `selftest.py` that several parts touch together
