# Pipeline Structure and Extension

> Translated from the Korean original. Where the two editions disagree, follow the Korean edition.

## Contents
- Modules
- Coordinate systems
- Drawable model
- Mannequin form engine
- Layer resolution order
- Turned bodies and view-aware clothes
- Straps and occlusion
- Groups and scene compositing
- Extension steps: figure poses, body types, figure study poses, anatomy marks, hand gestures, expressions and face presets, hair styles, hats, outfits, scenes, sites, times of day, still life sets, styles, color grade looks
- Debugging

## Modules

| Module | Responsibility |
|---|---|
| `render.py` | CLI. Spec loading, layer resolution, finished image (`paint`: style render, then color grade look), stage image output |
| `config.py` | Default spec, framing math, spec merging and typo warnings |
| `character.py` | Branching by subject, assembly of background and figure Drawables, scene backdrop compositing (tint, rim), group layout (`build_group`, name prefixes, z bands) |
| `frames.py` | Head frame (turn, tilt), body frame |
| `rig_face.py` | Face outline, ears, earrings, eyes, brows, nose, mouth, blush |
| `rig_hair.py` | Back hair, updo and bun, crown, bangs, side locks, gloss |
| `rig_hat.py` | Hats worn over the hair (`HATS`: beanie). The dome outline is a fixed silhouette; the folded cuff follows the face surface and wraps with the head turn |
| `rig_body.py` | Bust-only neck, shoulders, arms, turtleneck, collar |
| `mannequin.py` | Form engine that turns sphere-swept solids into silhouette, depth, normals, contour lines, self shadow and gloss |
| `rig_hand.py` | Palm, tapering 3-joint finger tubes, thumb, fingernail outlines, gesture table |
| `rig_anatomy.py` | Adult body (female and male body tables `BUILDS`, `use_build` swaps the table during a render): rib cage and pelvis frames, torso loft table, 2-joint IK, limb section profile sweeps, anatomy mark coordinates (`references/anatomy.md`) |
| `rig_figure.py` | Upper-body and full-body figures: 10 poses, direct joint targets (`apply_custom`), body turn (`turned`), leaning (`leaned`), head view (`head_view`), hands in pockets, props (pillar, chair), clothes on the mannequin body, shoes fitted to the feet, raised arms and hands |
| `garment_kit.py` | Garment blocks: copies of body pieces inflated by the cloth thickness, limb tube cutting, torso and limb rings, cut and keep polygons, rest coordinate masks (`rest_mask`), 3D straps (`strap`), lines, ribbons, printed bands, buttons |
| `outfits.py` | 14 outfit recipes (`RECIPES`), shoes per outfit, allowed lists per sex. Every cut line is written in rest pose coordinates or as a ratio position along a limb, so it follows pose and turn. The recipe context (`Ctx`) makes the visible lines, points, straps and small shapes of a turned body |
| `garment3d.py` | 3D clothes fitted to the body: knit top made by inflating the torso, with ribs that follow the body surface, turtleneck collar around the neck, belt around the waist section, skirt hanging from the hips (also used for coat skirts). View arc (`view_arc`), inverse transform to rest coordinates (`rest_coords`), body surface points and normals (`surface_rest`) |
| `rig_figure_study.py` | 4 figure study poses (male variant `male_variant`), adult face clamp, covering elements, anatomy mark rendering (clavicles, spine, scapulae, knees and others), automatic placement |
| `marks.py` | Small surface marks shared by the figure rigs: visible surface test, fingernails |
| `scene_common.py` | Time of day tables (sky colors, effect switches), sun, moon, stars, clouds, rain, snow, wet ground reflections, ridges, aerial perspective, conifers, broadleaf trees, bare trees and birches (`bare_tree`, `BIRCH`), grass |
| `scene_landscape.py`, `scene_city.py`, `scene_still.py` | The 3 scenes. Landscape and city have color tables per time of day and sites (`SITES`: lake and outskirts field, shopping avenue and panel estate); still life has the `classic` set |
| `scene_props.py` | Hard surface props: flat-faced polyhedra, cylinders, plates, tilted frustums, shapes inset on faces (screens, keys), table shadows |
| `scene_modern.py` | 4 modern still life sets (`desk`, `cafe`, `gaming`, `kitchen`) |
| `scene.py` | Drawable definition, occlusion and layer resolution |
| `geom.py` | Curves (Catmull-Rom, Bezier), variable-width strokes |
| `raster.py` | Antialiased rasterization, pseudo normals, patch operations, noise, color conversion |
| `palette.py` | Palette resolution, line color derivation |
| `styles.py` | Anime cel, soft illustration, shared shading functions |
| `painterly.py` | Oil, watercolor |
| `looks.py` | Whole-image color grade after the style render (`LOOKS`: `none`, `doomer`) |

The dependency direction is `render → character → rig_*, scene_* → mannequin, scene, geom, raster`, with no references in reverse. Style modules do not reference rigs or scenes.

## Coordinate Systems

- Head units: head breadth = 1, origin = head center, y down, z toward the viewer
- `HeadFrame.map(uv, z)`: converts head unit coordinates to screen pixels
    + `z='surface'`: a point on the face surface. Moves with its depth when the head turns
    + `z=None`: a silhouette point. Stays fixed when the head turns
- `BodyFrame.map(uv)`: converts body coordinates (head units) to pixels. Mannequin fields also build their grids with this frame.
- Body coordinates (`rig_anatomy`): x is the figure's left (screen right seen from the front), and side number `s = +1` is that side. Rib cage center y 1.70, pelvis center y 3.40, ankle 8.10, soles about 8.43
- Scene coordinates
    + Landscape: pixels and canvas fractions
    + City: street coordinates in meters (x right, y up, z forward) and a pinhole camera (`Camera`)
    + Still life: table plane y = 0, up is negative y, camera looking down at `PITCH`. Modern sets use a larger unit to frame closer (`scene_modern.UNIT_FRAC`)

## Drawable Model

One `scene.Drawable` is one shape on screen.

| Field | Meaning |
|---|---|
| `name`, `group`, `z` | Unique name, material group, depth order (larger is nearer) |
| `fill`, `fill_mode` | Polygon list. `evenodd` allows holes, `union` is for stroke ribbons, `each` for overlapping blobs (clouds, leaves) |
| `mask`, `line_mask`, `normal_map` | Coverage, line and normal patches precomputed by the mannequin |
| `color`, `gradient` | Solid color, 2 colors `(ca, cb, pa, pb)`, multi-stop `([(t, rgb)...], pa, pb)` |
| `strokes`, `line_color` | Line art strokes and their color. Lines hidden by nearer shapes are removed automatically |
| `clip` | Clipped by the filled area of other Drawables |
| `casts`, `receives` | Casting and receiving cast shadows |
| `receives_hair` | If False, receives no hair shadow (prevents shadows falling on clothes like stains) |
| `form_radius`, `form_poly` | Pseudo normal radius, proxy silhouette for the normal computation |
| `kind` | `fill`, `shadow`, `highlight`, `form` |
| `clip_vis`, `subtract` | Where a shadow or highlight applies, polygons to remove (cloud rim light) |

z conventions: background and sky -100, distant scene -90 to -50, back hair -10, inner face of a collar (upper and full body) -0.05, body 0 to 1, shoes 0.4, anatomy mark lines 1.01, fingernail lines at the hand's layer + 0.001, clothes 2-2.3, raised arm 2.5, face 5, still life props 5 + view depth, chin rest hand 5.5, eyes 6, bangs 10, hair touch hand 9.6, steam 40, rain 60

## Mannequin Form Engine

`mannequin.FormBuilder.build(name, group, z, pieces, ...)` makes the Drawables.

- `Solid`: a sphere or a cone with different end radii (sphere-swept). 3D coordinates
    + Elliptical section cone (`ellipse_cone`): the radius along direction `lat` differs from the radius at right angles to it. It builds forms with different width and depth, like the torso, as a single chain. The half-width, depth amplitude and twist seen from the view are computed in closed form (`_section`)
    + End caps of elliptical section cones are short (`CAP_LENGTH`). Seams inside a chain are cut on the bisector and joined when `prev_dir`, `next_dir` are given (`_miter`, `MITER_REACH`, `MITER_MIN_COS`)
    + Ellipsoid (`ellipsoid(c, axes)`): three semi-axis vectors in any direction. Depth is exact as the solution of the ray's quadratic, and the silhouette is the first-order distance to the ellipse where the depth discriminant becomes 0 (with shear correction). It is exact from any view
    + Ellipsoid sweep (`ellipsoid_sweep(centres, widths, heights, lats)`): interpolates the sections and joins ellipsoids densely at 20% of the section thickness (`SWEEP_SPACING`). Used for flat forms whose end easily faces the viewer, like the foot. Keep the piece blend `k` small (a large `k` on dense solids inflates the form)
    + Tube (`tube(points, radii)`): a cone chain that subdivides between joint points and smooths centers and radii. Fingers, toes
- `Piece`: a group of solids. Joined smoothly inside (`k`). Tree structure
    + `parent` and `attach_n`: only the first `attach_n` solids join the parent smoothly (shoulder, finger roots). The rest have a hard boundary, so a hand resting on the hip does not melt into it
    + A tree has 1 root. `build` draws only the tree that starts at the first piece, so separate pieces (headset ear cups and the like) are tied in with `parent` too (`attach_n=0` gives a hard boundary)
    + `contour_eps`: minimum depth difference for drawing occlusion lines. Set it large for softly rising forms like the chest and buttocks, so only the lower curve is drawn
- Field computation
    + Silhouette: exact 2D distance (uneven capsule, Inigo Quilez)
    + Depth: for cones, the height of the sphere on the axis that rises highest above that pixel (`_sweep_section`, closed form + one Newton step for the axis tilt); for spheres, the round section height. The depth gradient is the normal
    + Contour lines: silhouette lines (thicker on the side away from the light) + occlusion lines where piece i passes in front of piece j. An occlusion line remains only where i is the frontmost surface
    + Normals: computed from the gradient after smoothing the depth field in proportion to the head breadth (`NORMAL_SMOOTH`, coverage normalized). Creases at solid seams do not smear into shading stripes
    + Self shadow: ray tracing through the depth field (`SHADOW_REACH`), then a blur proportional to the head breadth (`SHADOW_SOFT`)
    + Long chains (limb sweeps, torso loft) keep the in-piece blend `k` near 0 (`rig_anatomy.LIMB_K`), because `smin` makes a small bump at every joined seam
    + Gloss: Blinn reflection (`gloss=(color, exponent, opacity)`)
- `select`: an overlay that keeps only some pieces. Used to keep the whole body under the clothes and redraw only the arms and hands over the clothes or the face
    + Whether a piece outside the selection hides a selected piece is decided by comparing depth only on the pixels that piece actually covers (`SELECT_EDGE_PX`). The depth field is extrapolated over the whole solid window; used as is, a torso that does not even cover the area hides the inside of the sleeve and leaves a band of skin between the sleeve and the body panel
- `quiet_zones`: round zones where no interior lines are drawn. Outlines of pieces with the `QUIET_KEEP` prefix (`hand_`) are kept, so the outline of a covering hand does not vanish
- Performance: each solid computes only inside its own window; large boxes use a 2x coarser grid and interpolate

## Layer Resolution Order

`Resolver.resolve()` makes one front-to-back pass.

1. Visible area of each shape = fill x (1 - accumulated coverage in front)
2. Line art = (strokes + line mask) x (1 - accumulated coverage in front)
3. Cast shadow = coverage of the `casts` shapes in front, shifted away from the light x visible area of the current shape
4. Normals = `normal_map` or the gradient of a round height field of radius `form_radius`
5. `form` shapes composite local normal bumps
6. `shadow`, `highlight` shapes composite into the `clip_vis` area (with `subtract` applied)

Output layers: `flat`, `line_rgb`, `line_a`, `normal`, `cast`, `shadow_shape`, `hl_rgb`, `hl_a`, `groups`, `detail`, `unit`, `kind`

## Turned Bodies and View-Aware Clothes

The body turn of a clothed figure turns the pose itself (`rig_figure.turned`). It turns the yaw of the rib cage and pelvis frames, the joint positions, and the limb targets and directions around a vertical axis through the head center. Body and clothes share the same 3D coordinates, so clothes made from inflated body pieces turn along unchanged. The front view (`turn` 0) goes through the same code path as before and matches to the pixel.

- Ring angles are relative to the body (theta 0 = body front). `G.view_arc` picks the visible half as the arc on the viewer's side between the left and right screen ends (contour points) of the ring. The neck ring (`NeckAxis`) also uses a body-relative basis and gets its visible arc from `arc`. The neckline drop (`drop`) happens at the body front
- Outlines written in rest coordinates (cups, tank top, briefs, jacket front opening) become `K.rest_mask` on a turned body. Each pixel of the cloth depth field is turned back into a 3D point, its rest coordinates come from `G.rest_coords` (the inverse of the rib cage and pelvis frame blend), and it is tested against the front or back outline. That is why every outfit has a back outline (`back_rest`, `back_outline`)
- Lines and points on clothes (seams, pockets, lapels, buttons, ties) are made with `ctx.paths`, `ctx.points`, `ctx.patch`. The curve is smoothed in rest coordinates, then torso surface points and normals (`G.surface_rest`) are found and only the parts facing the viewer remain. `back=True` is for lines on the back (back pockets of jeans, back seam of a jacket)
- Limb rings (sleeves, trouser hems) are viewer-relative by nature. Stripes and folds that need body-relative angles use `limb_view_thetas`
- On a turned body the legs overlap on screen. The trouser hem cut polygon cuts only inside that leg's area (`LIMB_FOOT_REACH`), and bare legs (`bare_legs`, starting slightly below the hem) become blocker pieces that hide the other leg's clothes
- The vertically hanging part of a skirt (`HangFrame`) turns with the body as well. The visible half is painted centered on the viewer's side
- Head: the 2D face rig draws only yaw -0.35 to 0.35. `head_view` sets the face yaw from the body turn (`TURN_YAW`) and draws the back of the head (`rig_face.build_back_head`, `rig_hair.back_view_hair`) beyond 1.9 radians. On a body seen from the back, long hair falls over the back (z 3) (`long_fall`) and shifts backward when turned sideways (`HAIR_BACK_SHIFT`)
- The hood comes up over the clothes when the back is visible

## Straps and Occlusion

`K.strap` takes a strap as a 3D path. It resamples the path at 1.5 px on screen, then hides each point that lies behind the body depth field (occluded) or whose outward normal faces away from the viewer (wrapping behind). Each visible span draws one ribbon.

- Spans on the body surface read their depth from the depth field (`K.surface_points`)
- A halter strap around the neck is a ring with the radius that touches the drawn neck outline (`outfits.neck_fit_radius`, wider than the cone because the neck and trapezius blend). The strap turns exactly at the neck outline
- A strap over the shoulder (bra) joins a front point, a point at the top of the trapezius (`'free'`) and a point on the back (`ctx.strap_rest`)
- A strap that is part of the body panel (crop top) draws its edge lines out to the cloth outline (`edges_to_form`). The cloth outline becomes the top edge of the strap over the shoulder
- Clothes are a layer above the body regardless of depth. Close-fitting tops on a turned body add the bare neck as a blocker piece (`neck_blocker`). Without it, the far strap passing behind the neck shows in front of the neck
- Shorts on a turned body draw a dividing line from the crotch to the inner end of the near leg hem (`turned_inseam`). The two loose legs do not read as one skirt
- Arms are redrawn over the clothes (`arms`). On a turned body the torso cloth pieces registered by the top recipe (`ctx.cover`) are added as blockers, so the arm is hidden where torso cloth is in front. That is why `build_figure` builds the outfit first and the arms after
- The armholes of a turtleneck on a turned body widely blur the rest coordinate mask and sharpen it again to remove stair steps (`TOP_MASK_SMOOTH`). The armhole line is drawn on that mask's boundary (`cut_edge_line`). A line drawn along the rest coordinate path lies on another surface and runs over the armpit skin

## Groups and Scene Compositing

- `character.build_group` makes a complete spec per figure (`group_character`: defaults, sex preset, outfit colors, figure fields)
- `group_layout` sets head centers, units, z bands and default turns. The largest figure fits the framing and the floor is shared (seated figures use a floor at chair height)
- Each figure is drawn inside `use_build`, then `namespaced` prefixes names with `p{i}_`. `clip` refers to names within the same figure, so it changes along. From the second figure on, z moves back by 25 per figure (one figure spans about -10 to 12 in z)
- When the `clip_vis` of a shading, gloss or form overlay is a material group, it becomes the list of that figure's names in the same group. Without `clip_vis`, the overlay's own group is used. Material groups span the whole picture; left unchanged, the shading of a figure behind bleeds onto the skin of the figure in front
- Holding hands sets the inner wrist targets of both figures to one point between them on screen and puts it into `pose.custom`. For a turned figure the point is converted back to pre-turn coordinates
- Scene compositing (`background.type: scene`) has the scene module draw the whole canvas and puts the figure on top. It uses the scene's light and multiplies the figure palette by the time of day tint (`tinted`)
- Scene Drawables lower z by `BACKDROP_DROP` (100). Scene z reaches up to about -19, which would put it in front of the second and third figure bands (-35, -60), pillars and ground shadows
- Ground shadows over a scene lay a dark color semi-transparently. The background palette colors are lighter than a night scene and would become glowing blotches
- The group of ground shadows over a scene is `scenery`. The `bg` group is left empty as paper margin in watercolor

## Extension Steps

### Add a figure pose (`rig_figure.POSES`)

- Build a weight-shifted stance with `_base()`, then register a function that replaces the arm `Limb`s
- `Limb(target, pole, hand, hand_u, hand_n)`
    + `target`: wrist position, `pole`: direction the elbow points to
    + `hand_u`: direction from the wrist to the fingers, `hand_n`: direction of the back of the hand
- If a hand must come in front of the face or hair, set a z per gesture in `HAND_OVER`
- A hand to hide under the clothes uses gesture `pocket`. It drops out of the raised arm overlay and out of the sleeve and cloth blocker pieces
- If a pose has a default view, put (turn, look, face yaw) in `POSE_VIEWS`. Used for poses that do not read from the front, like walking
- If a prop is needed, set `pose.prop` (`'wall'`, `'chair'`) and draw it in `build_figure`. Seated poses register `flat_ankle` (floor height) and `SEATED` (framing)
- A foot that keeps its heel raised even in flat shoes, like a stride, uses `keep_steps`
- Male wrist target adjustments go in `MALE_TARGETS`

### Add a body type (`rig_anatomy.BUILDS`)

- Put the values of `_BUILD_KEYS` (torso loft, shoulder and hip joint positions, limb profiles, neck, hands, chest form, buttocks, head size, shoulder girdle) into a new dict
- Vertical reference heights (neck 1.07, waist 2.70, navel 2.96, crotch 4.08, knee 5.96, ankle 8.10) do not change. Garment cut lines use these heights
- The render is built by `character.build_scene` inside `use_build(spec['character']['sex'])`. Do not bind body values to function default arguments (the value freezes at definition time and the switch is ignored)
- Put face, hair and outfit defaults in `config.SEX_PRESETS` and measurement targets in `check_proportions.TARGETS`, then check with `python scripts/check_proportions.py --build <name> --sheet turn.png`
- If the wrist targets of the clothed poses do not touch the body, add targets per body type as in `rig_figure.MALE_TARGETS`
- A body type variant of the same sex is added as one factor row in `VARIANTS` with its name in `BUILD_TYPES` (body type variants in `references/anatomy.md`). Check targets are generated automatically

### Add expressions and face presets (`config.EXPRESSIONS`, `FACE_PRESETS`)

- 1 row = changes per face part. `key*` multiplies, `key+` adds, a plain key sets
- An open mouth is `mouth.open`, closed eyes are `eyes.shape: closed` (`rig_face.open_mouth`, `closed_eye`)
- Face preset results are clamped into `FACE_LIMITS` (adult face ranges)

### Add a hair style (`rig_hair.HAIR_PRESETS`)

- Name one of the three base builders (`long`, `updo`, `short`) and the fields to override. If a new form is needed, add a flag to the builder (`undercut`, `tail`)
- The back of the head is drawn by `back_view_hair`, which reads the same preset
- Side locks use only the fixed shape points above the tail (`lock_points`, `LOCK_GAP`). With a short `side_length` the lock does not bend up and fold

### Add a figure study pose (`rig_figure_study.POSES`)

- Copy `A.standing_pose()` and set the rib cage and pelvis rotation, positions, limb targets, view (`view_yaw`, `root_roll`) and face direction
- Write rib cage and pelvis positions relative to reference origins, as in `_at(A.CHEST_ORIGIN, dx, dy, dz)`. The pose holds when the proportions change
- A standing foot sets the y component of `foot_dir` to 0 (level sole)
- A raised foot (`hand='point'`) bends the toes at the ball to lie on the floor. Put the ankle target about 0.55 above the standing ankle and point `foot_dir` down (example: `(-0.12, 0.85, 0.5)`)
- A reclining pose rolls the pelvis and rib cage frames themselves by 90 degrees (see `pose_reclining`)
- Design new poses so that posture, hands, hair or a drape cover the chest and pelvis. If the front of the upper body is exposed, cover it with `chest_lock` or the arms.
- For a view from the back, `hide_chest=True`

### Add an anatomy mark (`rig_anatomy.anatomy_marks`, `leg_marks`)

- 1 mark = (name, kind, reference frame, facing side, list of 3D points). Kinds are `ink` (faint line), `groove` (narrow shadow groove), `dot` (small shadow dot)
- Points sit on the body surface. For the torso, `loft_surface(chest, pelvis, y, x ratio, back)` gives surface points
- At render time a mark is drawn only when the normal of its reference frame faces the viewer (`FACING_MIN`) and the point lies within `MARK_SURFACE_TOL` of the visible surface. A line needs 2 or more consecutive visible points

### Add a hand gesture (`rig_hand.GESTURES`)

- Per finger `(spread, MCP, PIP, DIP)` bend angles (radians); the thumb takes a tip target `(u, v, n)` in hand coordinates
- The thumb is placed automatically on an arc of constant curvature to its tip.
- A fist bends PIP more than MCP (knuckles show from the back of the hand)
- A thumb tip placed far outside the palm width sticks out like a stick. A back-of-hand component `n` between -0.3 and 0 looks natural
- Checking with `python scripts/check_proportions.py --hands hands.png` (back of the hand, thumb side, palm) is faster than `--stages`.
- Fingernails are drawn by `marks.nails` from the outlines the rig makes. Below `NAIL_MIN_PX` on screen they are skipped

### Add a hat (`rig_hat.HATS`)

- Add a name to `HATS` and one function to the branch of `build_hat`. It returns a list of Drawables on the head frame
- Set z to `HAT_Z` (above the top hair layer) so the hat hides the hair under it. Hair meant to show below the brim stays outside the hat outline
- Map the silhouette with `frame.map(..., z=None)` and face-side lines with surface depth so they follow the head turn. A back view (`away=True`) maps every point as silhouette
- Color uses one palette key (`hat`)

### Add an outfit

- Bust 2D outfit: the `rig_body.build_bust_outfit` branch (only `turtleneck_sleeveless`). Other outfits use the 3D clothes path in the bust as well
- 3D outfit: register one function in `outfits.RECIPES` and put the shoes in `SHOES` (`pumps`, `sneakers`, `none`), male shoe exceptions in `MALE_SHOES` (`oxfords`), male availability in `MALE_OUTFITS`, and default colors in `config.OUTFIT_PALETTES`
- For turned bodies, recipes use `ctx.paths`, `ctx.points`, `ctx.patch`, `ctx.strap_rest` and avoid 2D points (`ctx.surf`) directly. Give close-fitting clothes and briefs a back outline. Front openings use `sleeved_top(front_cuts=...)`
- Printed color bands (track suit stripes, zippers) use `K.band_stripe` (paints the flat color as is; `K.lines` uses the darkened line color)
- Long coat skirts are drawn with `G.build_skirt(..., name, color, top_y)` and fold depth (`skirt_folds`); seated poses use `lap_skirt`
- Recipes are built from 4 constructions
    + Close-fitting clothes (`fitted_top`, `briefs`): inflate the matching body pieces slightly, then keep only the inside of an outline in rest pose coordinates (`keep`). Cups, briefs, crop tops
    + Tubular clothes (`trousers`, `sleeved_top`): inflate the torso and limbs, then cut with waist, neck and hem rings (`waist_cut`, `neck_cut`, `hem_cut`). Limb ends are cut by `tubes` at ratio positions (hip 0, knee 1, ankle 2 / shoulder 0, elbow 1, wrist 2)
    + Band (`band`): a band filling the space between 2 torso section rings. Belts, waistbands
    + Lines and small shapes (`K.lines`, `K.ribbon`, `K.patch_shape`, `K.dots`): seams, pockets, lapels, straps, ties, buttons
- Sleeved tops include the body up to the shoulder top (`SHOULDER_CAP`) in the body panel and add cones of cloth draped from beside the neck to the shoulder end (`shoulder_bridges`). The shoulder line runs straight and the sleeve does not puff
- Sleeved tops draw the body panel and the sleeves separately. Sleeve pieces use their own name prefix (if they share names with the panel's shoulder pieces, they overwrite each other). Hem and neckline cut only the panel, cuffs only the sleeves. A sleeve is hidden where the panel or a bare hand is in front (`blockers`)
- Necklines that do not reach the neck are inflated without the body's neck cone (`without_neck`). With it, the cloth stays like a pillar around the neck
- Neckline cuts use the same ring radius (`NECK_CUT_EASE`) for every layer. If an inner layer is cut narrower, it pokes out beside the outer layer
- The neckline ring lies level with the chest (`NeckAxis.ring(level=True)`). A ring at right angles to the neck drops one end when the head tilts and misaligns with the shoulders
- Beyond both ends of the neckline ring, the cut follows a curve that rises gently toward the shoulders (`NECK_RAMP_RUN`, height = cloth ease + `NECK_RAMP_RISE`). Cloth inflated over the trapezius sits higher than the ring, and a vertical cut leaves a stair step beside the neck
- The top edge of the opening of an open outer layer (`OPEN_TOP_Y`) sits above the neck ring. Below it, a collar scrap crossing the front of the neck remains as a solid line
- Short bottoms cut away everything below the line joining both hems. The lower end of the torso does not hang between the legs
- z: swimwear, underwear and sleeveless tops sit below the redrawn arms (2.5), sleeved clothes above them (2.55-2.6). The hoodie hood sits behind the neck (-0.5)
- Upper and full body turtleneck and skirt use `build_top`, `build_belt`, `build_skirt` of `garment3d`. All use the same pose frame as the body mannequin (`rig_anatomy._torso_point`)
    + Close-fitting clothes: inflate the matching body pieces by the cloth thickness (`grown`), draw them with `FormBuilder`, then cut with 2D boundary polygons (armhole, waist). Outline, shading and occlusion lines follow the body exactly
    + Bands around the body: project the front half of a 3D ring made by inflating a torso section (`torso_ring`). The band ends at the body's side line
    + Hanging clothes: compute the body section at each height, build an envelope that falls at a constant slope (`drape`), and paint those sections as a 3D grid (`paint_mesh`). Below the hips it hangs vertically, regardless of the pelvis tilt (`HangFrame`)
    + Rings below eye level (`EYE_Y`) bend down at the front (`perspective`). It is the cue that bands and hems wrap the body
    + Clothes use `receives_hair=False`
- Collars around the neck
    + The bust uses the 2D collar of `rig_body.build_collar`
    + Upper and full body put a tube inflated along the neck cone (`garment3d.collar_piece`) into the top's solid, so it rises straight out of the body panel. The top edge, the lower line of the folded band and the vertical ribs are drawn with rings around the neck (`NeckAxis.ring`)
    + The collar side line joins the armhole line with a round curve (`COLLAR_FILLET`). If the two lines break at one point, a corner remains at the joint
    + The inner face of the collar sits behind the neck (z -0.05). If the inner face is in front of the neck, the collar seems to float in front of it
- If the shoes are not pumps, the pose's heels come down to the floor (`rig_figure.flat_feet`)
- New material groups are added under the same name to `shadow_tint`, `cel_threshold` of `config.DEFAULT_SPEC`
- Check: render a spec that changes only `type` in 4 poses (`relaxed`, `hand_on_hip`, `hair_touch`, `chin_rest`). In the bent-arm poses, check that sleeve and hem cuts do not slice the body

### Add a scene

- Function signature: `build_x(spec, w, h, rng) -> (drawables, light_direction, unit_px)`
- To support times of day, keep `PALETTES[time]`, `LIGHTS[time]` in the scene module and turn on sun, moon, stars, rain, window lights and wet ground with `scene_common.scene_time` and the `FX[time]` switches
- Register in `character.SCENES`
- Sky goes in group `sky`, self-lit elements in `emissive`, elements in designed colors in `scenery`
- Depth is expressed with `scene_common.haze(color, depth)`: the farther, the closer to the horizon color

### Add a site (`scene.site`)

- Add a name to the scene module's `SITES` and one function to the site branch of the scene builder. The first value is the default site
- Camera, sky and time of day effects are shared with the existing sites. Color keys used only by the new site go directly into a time row such as `snow_night`, and the other times derive them from existing keys (`scene_landscape._outskirts_palette`)
- Scene compositing behind a figure (`background.type: scene`) reads the same `scene.site`

### Add a time of day (`scene_common.SKIES`, `FX`)

- Add one row of sky colors to `SKIES` and one row of effect switches to `FX` (`sun`, `rim`, `windows`, `lamps`, `moon`, `stars`, `rain`, `wet`, `snow`)
- Add a row with the same name to `PALETTES`, `LIGHTS` of each scene module
- To use it behind figures, add rows to `character.SCENE_TINTS`, `SCENE_RIMS` too
- Wet ground reflections flip a light at height H in the pinhole camera to the point -H below the ground and draw it as a vertical streak of light (`scene_city._reflection`)

### Add a still life set (`scene_modern`)

- Register the set in `SETS`, `PALETTES`, `LIGHTS` and add one function to the branch of `build_modern`
- Hard objects are built with `scene_props` (flat-faced polyhedron `solid`, `table_box`, cylinder `cylinder`, plate `disc`, tilted frustum `frustum_hull`), soft objects with mannequin pieces
- Screen content finds a rectangle on the display face with `inset` and is drawn in group `screen` (no shading)
- Shadows: `cast_shadow` pushes each point away from the light by its height and makes a convex hull on the table

### Add a style

- Function signature: `render_x(layers, spec, pal) -> float32 RGB (h, w, 3), values 0-1`
- Register in `render.STYLE_RENDERERS`
- Shared parts: `styles.soft_shaded`, `styles.apply_lines`, `styles.multiply_shadow`, `styles.screen`, `styles.bloom`, `styles.grade`, `styles.backdrop`

### Add a color grade look (`looks.LOOKS`)

- Function signature: `look_x(img, rng) -> float32 RGB`, input and output both values 0-1
- Add a name to `LOOKS` and connect it in the branch of `apply_look`. Keep the constants in one named dict, like `DOOMER`
- A look works only on the finished image and reads no layers. It is independent of the style, so the same look applies to all 4 styles
- The finished image is always made with `render.paint` (CLI and tool scripts alike). Calling a style renderer directly leaves the look out

## Debugging

- Use `--stages` to see the image of each stage and find the stage where a defect first appears.
- After changing the body form, run `python scripts/check_proportions.py --sheet turn.png` first. It fails when proportion error or the count of outline inflections (bumps) exceeds the limits, and the turn sheet (front, 3/4, side, back) shows silhouette and shading (review procedure in `references/anatomy.md`)
    + Construction stage: frames, skeleton targets
    + Line art stage: curve control points, z order, occlusion lines
    + Flat color stage: polygon orientation, `fill_mode`
    + Shading stage: normals, `cel_threshold`, self shadow
- To find the lines of a specific Drawable, check `line_mask` by region in the result of `character.build_scene(spec)`.
- If a twisted ribbon polygon makes holes, use `fill_mode='union'`; if overlapping blobs make holes, use `'each'`
- `clip` is the intersection of a list of names. To draw on either the road or the sidewalk, split the Drawable and clip each part with 1 name
- One render peaks at 0.4-0.9 GB of memory (full-body oil is the largest). Keep parallel renders at or below the available memory divided by 1 GB
