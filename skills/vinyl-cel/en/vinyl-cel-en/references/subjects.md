# Guide by subject

## Contents

- 3D figures
- Modern objects and interior scenes
- Outdoor scenes and the doomer set
- Light scenes
- Full-body figures
- Hands
- Landscapes
- Cityscapes
- Still lifes
- Matching styles to subjects

## 3D figures

- (Starting points) Turnaround `examples/turnaround3d.py`, poses `examples/pose_sheet3d.py`, outfits `examples/outfits3d.py`, finished scene `examples/beach_pair3d.py`
- (Structure) `Figure3D` bundles face data (`Character`), build (`Build`), pose (`Pose3D`), hairstyle (`Hair3D`), outfit (`Outfit3D`) and the camera
    + The length unit is the head height; the origin is the pelvis, y points down and z toward the viewer of the front view
    + Left and right are named by the screen of the front view, so `right` is image right (+x) from the front
    + `position` is the canvas position of the pelvis; given `ground`, the figure is lowered so the parts touching the floor reach that height
    + The parts touching the floor are decided by `figure3d.ground_points()`: the soles for standing and sitting poses, and the lowest hanging body and clothing parts (back of the head, back, heels, knees, insteps) for lying and kneeling
- (Camera) `yaw` 0 is the front; positive turns the figure's front toward image right, π/2 is the side and π the back
    + The default `pitch` 0.16 looks down slightly so the insteps show; 0 is a level view
- (Face) The face treatment is chosen by the angle the head turns away from the screen
    + `abs(yaw) <= 0.85` attaches the portrait rig's eyes, nose, mouth and brows to the front of the face
    + `abs(yaw) <= 2.05` gives a profile with one eye and a mouth line; beyond that is the back of the head, so no face is drawn
    + Women use `adult_face()`, men `male_face()` (narrow eyes, low brows, a longer lower face, dark irises, darker skin)
    + `male_face()` thins the lashes and removes the outer flick (`lash_weight` 0.55, `lash_flicks` False), thickens the brows (`brow_weight` 1.65), shrinks the irises (`iris_scale` 0.88), and weakens lip colour and blush (`lip_tint` 0.30, `blush_strength` 0.35)
- (Build) `Build(sex, shoulders, bust, waist, hips, thighs, limbs, muscle)`
    + `FEMALE_AVERAGE`, `FEMALE_FULLER` (bust 1.32, waist 0.84, hips 1.12, thighs 1.06)
    + `MALE_SLIM` (shoulders 1.12, muscle 0.25), `MALE_ATHLETIC` (shoulders 1.26, limb thickness 1.20, muscle 1.0, abs)
    + The torso is the `rig3d.TRUNK` section table (10 sections from crotch to neck), and the limbs are the `ARM` and `LEG` control points and radii
    + Breasts, pectorals, buttocks, deltoids and trapezius are separate ellipsoids, and the trapezius makes the slope from the neck down to the shoulder
- (Pose) `Pose3D` bundles local rotations `(rx, ry, rz)` per joint, hand poses and `Reach` to put a hand on a target
    + For bones pointing down, positive `rx` swings backward, so knees bend with positive `rx`, and lifting legs and arms forward is negative
    + For bones pointing up (spine, neck, head), positive `rx` bends forward, `ry` twists round the bone, and positive `rz` tilts toward image left
    + Elbows bend with negative `rx`; a positive value hyperextends them
    + `Reach(target=(joint, local coordinates), pole=direction the elbow points, fingers=finger direction, palm=palm direction)`
    + `fingers` and `palm` are directions in the chest frame, and the wrist bend stops at `rig3d.WRIST_LIMIT` (1.25 radians)
    + A target beyond arm's length makes the straight arm point toward it; a far target such as the knee when sitting is moved to mid-thigh
    + A new pose is made with `rig3d.pose(head=(...), reach={"right": Reach(...)}, hands={"right": FIST})` and registered in `POSES`
    + Floor poses lay the whole body down with a pelvis rotation: `pelvis=(-1.52, 0, 0)` lies on the back (head toward -z), `(π/2, 0, 0)` lies on the front (head toward +z)
    + Floor poses set no height of their own; when placed, the lowest parts touch the floor, and the pelvis and hip angles are fine-tuned so several parts touch together (the floor items of `selftest`)
- (Pose list) 27 in `rig3d.POSES`
    + Standing: `stand`, `a_pose`, `contrapposto`, `hand_on_hip`, `arms_crossed`, `wave`, `point`, `think`, `hands_behind`, `cheer`, `peace`, `hands_in_pockets`
    + Moving: `walk`, `run` (upper body leaning forward, fists swinging, one supporting foot on the floor)
    + Sitting and on the floor: `sit`, `kneel` (kneeling upright, insteps on the floor), `kneel_sit` (kneeling and sitting on the feet, hands on the thighs), `lie_back` (lying on the back), `lie_front` (lying on the front on the elbows, chin in the hands, knees bent so the feet rise)
    + Using devices: `sit_type`, `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug`, `sit_game`
    + Smoking: `stand_smoke` (left hand in a pocket, cigarette in the right), `sit_smoke` (cigarette held in front of the chest), used with `props3d.held_cigarette()`
    + `hands_in_pockets` points the fingers into the hips, so use it with trousers-type garments (`jeans`, `trousers`, `hot_pants`, `swim_trunks`); the trousers cover the hand and make a pocket swell (`wardrobe3d.pocket_hands`)
    + Tops that cover the hips (T-shirt, shirt, hoodie, jacket) make a pocket swell over the hand, and long sleeves end above the wrist and go into it (`tuck_into_pocket`); a hoodie shows the hands in its front pocket
- (Mirroring) `rig3d.mirrored(pose)` returns the pose with left and right swapped
    + Used to move a hand gesture to the hand on the camera side in a side view (`mirrored(rig3d.HAND_ON_HIP)`)
    + Rotations keep their x component and flip the y and z components; hand targets and hand directions flip their x coordinate
- (Hands) `HandPose3D(curl, spread, thumb_out, thumb_curl)`, presets `RELAXED`, `OPEN`, `FIST`, `POINTING`, `HOLDING`, `PEACE`, `RUN_HAND`, `POCKET_GRIP`, `CUPPED`, `SMOKE_GRIP`
    + Fingers are sphere chains of 3 segments, so fists and peace signs show from every angle
- (Hair) `Hair3D` is made of a scalp layer, masses (`cap`, `lobes`), fringe ribbons, side locks, a back hair sheet, a ponytail and spiky tufts for short hair
    + The scalp layer is an ellipsoid 5% larger than the skull, cut away at the face opening and below `scalp_drop` (side hairline) and `nape` (back hairline)
    + Short male hair raises `scalp_drop` above the ears, so the ears and sideburns show
    + Strand lines and the highlight band are lines laid on the surface (decals), and strand lines run down long back hair too
    + The ends of long back hair split into 5 strands of different lengths (`Hair3D.tips`, `BACK_TIPS` in `LONG_HAIR`); the strands are the same part as the back sheet, so no swelling forms at the border
    + Side locks and the hair beside the face thin toward their ends into points (`LOCK_TIP_THICKNESS`)
- (Outfits) Clothes are copies of the body's forms pushed outward, so they fit any build and pose
    + The thickness constants are `TIGHT` 0.030, `FITTED` 0.040, `LOOSE` 0.055 and `BULKY` 0.080 (head heights)
    + `TIGHT` must exceed the swelling where skin parts melt together (`body3d.SMOOTH_BLEND`/4 = 0.025), or skin shows through
    + Layered garments are lifted further by `LAYER_GAP` (0.02) per layer number in `GARMENT_LAYERS`
    + A top worn over bottoms is lifted by at least `FITTED` below the waist, and covers for the tops of the thighs and the hips are added automatically
    + The V opening of a jacket and the leg openings of a bikini are made with cut functions (`cut`); forms made of several pieces are cut once on the merged surface, so cut edges are smooth
    + Tubes that end midway, such as sleeves and trouser legs, end in a flat hem (`flat_hem`), so they do not balloon
    + Strings (bikini halter and back strings, the connector between cups) are densely resampled by `over_skin()` and pushed out of the torso surface (`ctx.skin()`, limbs excluded), so they do not sink into the chest, collarbone or neck and break
    + Strings start at the corner of the cup that actually shows (`_cup_corner`), and the halter wraps round the neck (`rig3d.neck_path`)
    + The shoulder straps of tank tops and sundresses are flat ribbons lying along the skin (`strap_over_skin`), so they sit on the shoulder for any build
    + A top over bottoms ends its torso and hip cover at one flat hem plane (`hem_cut`), so the hem stays even when sitting
    + A hoodie's hood is a separate layer lying flat on the back, so the hood's outline shows from behind
    + Shorts-type garments (leg length under 0.45) get a front centre seam that tells them apart from a skirt
    + A skirt lies along the thighs toward the knees when the thighs lift (`_skirt_fall`), and covers the tops of the thighs when sitting
    + Colours are a `Material` per slot (`top`, `bottom`, `outer`, `trim`, `accent`, `shoes`, `sole`, `outer_line`, `hat`, `gear`), and the slots an outfit uses are those in its colour dictionary in `OUTFITS`
- (Adding an outfit) Register a `(ctx) -> Piece(solids, decals)` function in `GARMENTS` and add a combination to `OUTFITS`
    + The torso uses `trunk(ctx, start, end, thickness, slot)`, arms `sleeve()`, legs `leg()`, the chest `chest_cover()` and the hips `seat_cover()`
    + Start and end are trunk positions (0 crotch, 0.44 waist, 0.89 shoulder, 1 neck, `TRUNK_LANDMARKS`)
    + Seams, pockets and buttons are `decal(points, width, slot, opacity, on=slot of the surface they show on)`
    + For a layered garment, add a layer number to `GARMENT_LAYERS` and check for skin showing through with `selftest.py`
- (New hairstyle) Change fringe angles, lengths and masses with `replace(head3d.PONYTAIL_HAIR, ...)`
- (Limits) Hair is a smooth mass, simpler than the wind-blown hair of the 2D portrait
    + Skirts are rigid forms lying along the thighs, so flutter and folds while walking are not shown
    + Painterly uses the finest brush (0.9 units) on small faces, but below a head height of 60 the eye shapes simplify
    + Animals, acrobatic poses (handstands, flips) and poses where two figures touch (hugging, piggyback) are not supported

## Modern objects and interior scenes

- (Starting points) Object list `examples/props_sheet3d.py`, modern still life `examples/desk_setup3d.py`, office `examples/desk_worker3d.py`, living room `examples/living_game3d.py`, cafe `examples/cafe3d.py`, bedroom `examples/bedroom3d.py`
- (Structure) One `SceneCamera` sees the whole world, and `Placed` items (figures, objects, furniture) are drawn into one depth buffer
    + The world is in head heights, the floor is y = 0, y points down, and object sizes are real measurements with `props3d.cm()` (desk 73 cm, laptop 32 x 22 cm)
    + An object's origin is the centre of its base, and its front is +z (laptops and monitors toward the user, sofas and chairs the way the sitter faces)
- (Camera) `SceneCamera(target, origin, scale, yaw, pitch, distance)`
    + `distance` is the eye distance (head heights): 12-20 for interiors, 26 for a wide object sheet, None for orthographic
    + Positive `yaw` turns the world's front toward image right; stand 0.2-0.6 off axis so figures and screens show together
    + When the eye leaves the room, that wall is left out and the floor runs on past it (`FLOOR_MARGIN`)
- (Placement) Placing things by the furniture anchors gets heights and directions right
    + `scene3d.on_top(object, desk, offset=(x, 0, z), yaw=turn)` puts it on the top, with offset in the furniture's frame
    + `scene3d.seated(figure, chair)` puts a figure on the seat; for a sofa, `seated(figure, sofa, "seat_1")`
    + The seat height `furniture3d.SEAT_TOP` is derived from the sitting pose, so every sitting pose fits the same chair
    + A figure's `Placed.at` is the floor point under the pelvis, and the lowest body part touches that height, so a lying figure goes straight on the bed anchor `anchor(bed, "lie_back")` or `"lie_front"`
    + `lie_back_0` and `lie_back_1` are per pillow (head on the pillow); `lie_front` is the middle of the bed, and the figure faces the foot end
    + To put an object on the duvet, use `on_top(object, bed, offset, key="duvet")`
- (Layout check) `scene3d.overlaps(items)` finds volume shared between objects and furniture
    + It returns a list of `Overlap(first, second, depth, volume)`, largest volume first; an empty list means nothing passes through
    + Contacts up to 1 cm³ (a leg pressing the rug, an object on a top) are allowed, and the test is by volume rather than depth so thin objects are caught too
    + Figures are not checked (sitting, typing and holding are intended contacts)
- (Objects) Angular forms are the boxes, slabs, cylinders, truncated cones and rings of `sdf3d` and their combinations
    + A new object is a function returning `Prop3D(name, solids, screens, ...)`, with `props3d.laptop()` as the model
    + Rigid parts are in the default group (`rigid`), so they do not melt together where they touch and get a border line
    + Repeats such as keyboards use `Grid`, the inside of a cup `Cut` and handles `Torus(arc=...)`
- (Glass) Clear parts go in `Prop3D.glass` and are composited in a second pass after the opaque pass (`props3d.finish_glass`)
    + What lies behind shows through, the colour deepens toward the outline, and the side facing the light gets a hard highlight and a thin outline
    + Glass is not written to the depth buffer, so it does not hide the objects behind; contents such as drinks are drawn as ordinary `solids`
    + The model is `props3d.drinking_glass(fill=0.6)`
    + Refraction (distortion of what lies behind) is not computed
- (Cables) `props3d.cable(points, sag=0.0)` is a smooth line through points, placed in world coordinates as they are with `Placed(cable)`
    + The points are where the cable touches, and the axis lifts by the radius, so points on a top or the floor (y = 0) lie on that surface
    + A path running over the edge of a top down to the floor is modelled by `charger_cable()` in `desk_setup3d.py`
- (Screens) Give the screen panel a material of its own and register `Screen(corners, content, material)`
    + After lighting, the screen content is attached to the four corners by perspective transform, and a glow is added outside
    + The presets (`screens.PRESETS`) are fictional generic screens; other screens are passed as `function(width, height, rng) -> RGB image`
- (Held objects) `held_phone`, `held_mug` and `held_controller` attach objects to the hand frame
    + The pose sets the hand direction, so pair them with `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug` and `sit_game`
    + Typing (`sit_type`) assumes the default desk and seat heights and a keyboard about one head in front of the pelvis (`LAPTOP_DEPTH` in `desk_worker3d.py`)
    + A figure looking at a phone lowers the gaze with `replace(character, gaze=(0.0, 0.10))`
- (Interiors) `interior.living_room()`, `office()`, `cafe()` and `bedroom()` return a `Room` with walls, furniture and props
    + Seat figures and place objects by the furniture names in `room.places`
    + Custom rooms are built directly with `Shell`, `shell_surfaces`, `trims`, `on_back_wall` and so on (`desk_setup3d.py`)
    + Wall windows make the view outside (sky, city, street) together with sunlight patches on the floor
- (Limits) Doors, stairs and mirrors are not provided
    + Glass shows transmission and highlights only, with no refraction or reflected image
    + The duvet is a rigid slab, so a duvet covering a body and crumpled folds are not shown, and lying figures rest on top of the duvet

## Outdoor scenes and the doomer set

- (Starting points) Man `examples/doomer_man.py`, woman `doomer_woman.py`, two-shot `doomer_pair.py`, establishing shot `doomer_establishing.py`, cityscape `doomer_city.py`, landscape `doomer_landscape.py`, still life `doomer_still.py`
- (Mood) A sleeping city at night, a few lit windows and one person
    + One or two small figures in front of huge repetition (identical windows, rows of power poles and street lamps)
    + Murky teal shadows, sodium orange light, washed-out blacks and low saturation come from the colour grade `doomer`
    + Only the mood is borrowed; specific album covers, meme characters and real buildings are not reproduced
- (Structure) One `outdoor.World` holds the light, sky, fog, ground, buildings, lamps, 3D items, wires and snow, drawn with `draw_world`
    + The order is sky, ground, light pools on the ground, wet reflections, buildings (farthest first), 3D items (night lighting), wires, haze and falling snow
    + Distances are entered in metres with `outdoor.metres()` (street lamp 5.6-8 m, a 9-storey panel block 26 m, 40 m between power poles)
- (Light) `NIGHT`, `DUSK` and `OVERCAST` set the walls and windows, the snow colour and the ambient light on figures (`ambient`) together
    + Street lamp light falls off with the square of distance, and a shaded lamp lights only inside its cone (`cone`); the ground and the figures use the same formula
    + A figure inside a lamp's cone has a lit face, and outside it becomes a silhouette (the back view of the two-shot is the model)
    + Point the cel shading toward the lamp with `run_cli(..., light=...)` (raise y for light from above)
    + Bulbs, phone screens, embers and smoke are drawn after the night lighting, so they stay bright in dark scenes
- (Camera) Before rendering, compute the canvas positions of the lamp head, the figure's head and feet and the building roofs with `camera.project(point)` to check they fit in the frame
    + To get a street lamp's head into the frame, put the lamp behind the figure or use a lower courtyard lamp (`street_lamp(cm(560), cm(110))`)
    + If buildings cover the whole frame, move them further away to leave sky (establishing shot 150-430 m, two-shot 195 m)
    + One-point perspective uses `yaw=0`, `pitch=0` and a road along z (cityscape)
    + The world direction at the frame edges can be worked back with `world_points` or `plane_points`
- (Ground) `paths` in the snowfield `snow_texture(rng, light, extent, paths)` are trodden paths in plane coordinates (0..extent)
    + Roads are `road_texture(..., along="x"|"z")`, and a wet road is `World(wet=True)`, which draws streaks of reflected lamp light
- (Buildings) `panel_block(at, length, floors, rng, light, yaw)` is a roof and 4 sides of facade texture
    + One window per storey and bay; the share and colours of lit windows come from the light preset, adjusted with `replace_light(NIGHT, lit_share=0.3)`
    + To line a road with buildings, use `yaw=π/2` on the left and `yaw=-π/2` on the right
- (Street furniture) `street3d` has street lamps, power poles and wires, benches, a bus stop (glass walls, fluorescent tube) and birches
    + Seating works as indoors: `scene3d.seated(figure, bench, "seat_1")`
    + Wires are `wires_between(list_of_poles)`, and arbitrary wires such as trolleybus wires are lists of `outdoor.catenary(a, b, sag)`
- (Figures) Winter outfits `winter_beanie`, `winter_headphones` and `hoodie_beanie`
    + Cigarettes are `props3d.held_cigarette()` with the poses `stand_smoke` and `sit_smoke`; the smoke is automatic
    + A back view looking up uses `replace(rig3d.SIT, rotations={**rig3d.SIT.rotations, "neck": (-0.10, 0, 0), "head": (-0.16, 0, 0)})`
- (Indoor still life) The wall gets the same night lighting as the objects with `outdoor.light_plane(..., ambient=..., mask=draw_surface(...))`
    + The view out of the window (`window(..., "panel_night", ...)`) is drawn after the lighting, so the windows outside stay bright
- (Painterly) Facades, ground, wires and street furniture ask for fine brushes (`keep_detail`), so windows and poles do not smear, and falling snow is drawn after the brushwork
- (Limits) Buildings are box facades, so balconies and entrances are painted, not solid
    + Shadows are floor shadows and contact shadows only; street lamps cast no long shadows
    + Rain, reflections in puddles and vehicles are not provided

## Light scenes

- (Starting points) Night desk `examples/night_desk.py`, afternoon window `sunny_reading.py`, sunset bench `dusk_bench.py`, beach sunset `beach_sunset.py`
- (Mood) Warm everyday moments where one named light source wraps the figures
    + Use one key light and one complementary fill (a warm key with a cool fill, or the reverse)
    + Pick the grade from the scene's time of day: `cozy_night`, `late_sun` or `golden_hour`
- (Room lighting) Draw with `outdoor.draw_lit_room(painter, camera, surfaces, views, items, lamps, ambient)`
    + A night scene uses an ambient of 0.3-0.4 with a screen (pale blue, reach 50 cm) and a desk lamp (warm, cone 1.05)
    + A daytime scene uses an ambient of 0.8-0.9 with a broad warm lamp (reach 5 head heights) in front of the window standing in for the sun
    + Window views (`window(..., "city_night"|"golden")`) and sun patches (`interior.sunlight`) go in `views` and are drawn after the lighting
    + Only surfaces with a `facing` are lit; surfaces without one, such as corner shadows, stay as painted
- (Outdoor sunset) Give `outdoor.World` sunset sky stops and warm walls from `replace_light(DUSK, wall=..., ambient=...)`
    + The ground is a warm grey `asphalt_texture(rng, extent, color=...)`; leaving out the snowfield weakens the doomer feel
    + Set the blocks 300 m or more away so the sky stays open in the upper frame
- (Beach) Paint the sunset sky, the sun and its path over `background.beach` and draw only the figures in 3D
    + Match the horizon with `outdoor.horizon_y(camera)` and warm the figures with `night_lighting` using one distant warm lamp
- (Framing) A medium shot where the face is 1/10 to 1/14 of the frame height, upper body or more in view
    + Place trees and poles by solving the world x for a chosen canvas x so nothing stands behind a head (`dusk_bench.world_x`, bisection with `camera.project`)
    + Do not confuse canvas units with preview pixels (the preview is x0.8)
- (Style) A three-quarter face looking down stays clean in `illust`; anime line art joins the nose and mouth lines into a hook
- (Outfits) For a skirt in a walking pose, scale the leg joint rotations by 0.55 so the forward thigh stays inside the skirt (`beach_sunset.STROLL`)
- (Limits) Lamps are point lights without direction, so match the light direction on faces with the cel shading direction `run_cli(..., light=...)`
    + Light shafts through a window, screen reflections and figures reflected in water are not provided

## Full-body figures

- (Starting points) Clothed figures `scripts/examples/full_body.py`, swimwear `scripts/examples/swimwear_beach.py`
- (Structure) `Figure` bundles the figure data (`Character`), pose (`Pose`), body shape (`BodyShape`), outfit, pelvis position and the size of one head height
    + The length unit is the head height (crown to chin = 1), and a standing figure is about 7.5
    + Limb lengths are constants, so poses change only joint angles
- (Facial impression) `adult_face(character)` is a mature look with the lower face lengthened 1.12 times and smaller eyes
    + The default face is a big-eyed anime look
    + `head_scale` 1.0 is realistic proportion, 1.15 or more the larger anime head
- (Body shape) `BodyShape(bust, waist, hips, thighs)` are width factors relative to an average adult woman
    + Presets are `AVERAGE`, `SLENDER` and `HOURGLASS` (bust 1.32, waist 0.84, hips 1.12, thighs 1.06)
    + Use each value in the 0.8-1.4 range; beyond it the forms break down
    + Left and right breasts are cut at the centre line and inflated separately, so a chest gap remains as they grow
- (Pose) Limb angles are measured from straight down, positive toward image right
    + Tilt values are positive clockwise, so a positive value lowers image right
    + The provided poses are `STANDING`, `CONTRAPPOSTO`, `HAND_ON_HIP`, `ARM_RAISED` and `A_POSE`
    + `wrist_left` and `wrist_right` are hand angles relative to the forearm, used to turn the fingers of a hand on the hip downward
    + New poses are made with `dataclasses.replace(CONTRAPPOSTO, upper_arm_right=0.6, ...)`
- (Contrapposto) Tilt the pelvis and shoulders opposite ways and move the chest toward the weight-bearing side
    + `hip_tilt` 0.10-0.15, `shoulder_tilt` about -0.07 and `spine_lean` about 0.10 are a natural range
- (Arms in front or behind) Arms lying over the body or clothes set `arm_left_in_front` or `arm_right_in_front` to True
    + Arms left unset are drawn before the clothes and go behind the skirt
- (Outfit layers) Outfits are layers put on after the body is complete, drawn by functions registered in `OUTFITS`
    + The provided outfits are `SUNDRESS` (bodice, straps, flared skirt, shoes) and `BIKINI` (triangle top, high-cut bottoms, side ties, bare feet)
    + Swimwear colour is `Figure.outfit_material`, or the palette's `trim` when unset
    + Changing only `outfit` on the same `Figure` changes the clothes (`examples/dressup_base.py`)
- (Adding an outfit) Add a value to `FigureOutfit` and register a function taking `(relief, painter, figure, skeleton)` in `OUTFITS`
    + Cloth that follows the body uses `relief.add(..., drape=True)`; cloth that spans a hollow and pulls taut sets `bridge`
    + Multiplying the cloth mask by `relief.visible("body")` keeps it from spreading over arms and hands
    + Cloth standing as its own form (a skirt) gets its own height map and `depth=FRONT`
    + Decorations drawn after lighting (ties, buttons) are returned as a function, which `draw_figure()` calls last
    + `selftest.py` checks for missing registrations and the coverage of swimwear
- (Limits) Only front-facing standing figures are supported, and the face is small on screen, so expressions read weakly

## Hands

- (Starting point) `scripts/examples/hand_study.py`
- (Structure) One palm, 4 fingers (3 segments each) and a thumb
    + The length unit is the hand length (wrist to middle fingertip = 1)
    + The hand frame's origin is the wrist, +y the finger direction and +x the thumb direction
- (Pose) `spread`, `curl` (0-1), `bend` (in-plane bend) and `thumb_angle` of `HandPose`
    + The provided poses are `OPEN_HAND`, `RELAXED_HAND` and `VICTORY_HAND`
    + Curled fingers are shown by shortening their visible length
- (Direction) `HandView.PALM` draws palm lines, `HandView.BACK` draws nails and knuckles
    + `mirror=True` is the other hand, and `turn` is how far the hand turns sideways (1.0 front, 0.66 near side-on)
    + To point the fingers up, rotate the frame by π
- (Finishing) Call the function returned by `draw_hand()` after `relief.render()`, or nails and palm lines are not drawn
- (Limits) Fists, hands holding things and interlaced fingers are not supported

## Landscapes

- (Starting point) `scripts/examples/landscape_lake.py`
- (Structure) Sky, terrain, water reflection and foreground (meadow, conifers) in that order
    + `terrain.alpine_lake_heightmap()` makes a height map with a far mountain range, a lake basin and a mound in front of the camera
    + `terrain.colorize()` splits snow, rock, meadow and forest by altitude and slope, and computes sunlight and mountain shadows
    + `terrain.render()` sweeps depth slices away from the camera and projects them onto the screen
- (Camera) `Camera(position, eye_height, horizon, focal)`
    + Raising `eye_height` shows more of the lake, `horizon` is the horizon's canvas y, and a larger `focal` makes the mountains bigger
- (Water) `scenery.reflect_water()` flips the scene about the far shore to mirror it in the water
- (Foreground) `scenery.grass()` is ground, grass blades and flowers; `scenery.pine()` is a conifer of stacked tiers
    + Trees at both edges of the frame draw the eye to the mountains in the middle
- (Other terrain) New terrain is a function that builds a height map
    + The height map is 1024 x 1024, with the y axis running away from the camera
- (Limits) Broadleaf trees, buildings and sea waves are not provided

## Cityscapes

- (Starting point) `scripts/examples/city_dusk.py`
- (Structure) Sky, far skyline, road, buildings, signs, wet road reflections, street lamps and glow in that order
    + The world unit is the metre; x runs across the road, y up and z away from the camera
    + `StreetCamera(vanishing_point, focal, eye_height)` does the projection
- (Buildings) `Building(side, near, depth, height, wall, lit_share, shop)`
    + The facade is made as a flat texture and perspective-warped onto a quad, so window spacing narrows with perspective
    + Uneven building heights keep the line where they meet the sky alive
- (Wet road) A layer of sky and buildings flipped below the ground line is laid over the road
    + Each building is flipped about its own ground line, so reflections sit in the geometrically right place
- (Light) Windows and signs return emission masks, and `city.bloom()` adds the glow
- (Time of day) Change `SKY_STOPS`, `HAZE` and `lit_share` to switch between day, evening and night
- (Limits) Only one-point perspective, no people or vehicles, flat roofs only

## Still lifes

- (Starting point) `scripts/examples/still_life.py`
- (Structure) Room (wall and table), cloth, objects at the back, fruit in front, table shadows, lighting, stems and leaves in that order
- (Solids of revolution) Bottles, jugs and pears pass a radius profile `[(t, radius), ...]` to `lathe_object()`
    + t runs 0-1 from top to bottom, and `base_roundness` and `top_roundness` set how round the ends are
- (Fruit) `round_fruit()` is apples and oranges, `tilted_ellipse_fruit()` lemons and `grapes()` a bunch of grapes
    + `gloss` is shine, `mottle` colour blotches and `pores` the bumpiness of the peel
- (Shadows) Call `table_shadow(relief, base_point, half_width)` after adding all objects
    + Shadows fall only on the bare table and the cloth, not on objects
    + Shadows the objects cast on each other are computed by `relief.render()`
- (Placement) Give objects at the back a small base y and objects in front a large base y, so they read as standing on the table
- (Limits) Refraction in clear glass, reflections on metal and flowers are not provided

## Matching styles to subjects

| Subject | Best style | Reason |
|---|---|---|
| Portraits, full-body figures | Anime, illust | Lines and flat colour suit the simple forms of the face |
| 3D figure sheets | Anime | Cel shading and occlusion lines show the forms at each angle most clearly |
| Hands | Illust | Soft shading brings out the round forms of the knuckles |
| Landscapes | Painterly, anime | Brushwork covers the fine noise of the terrain and keeps the large forms |
| Cities | Anime | Glow and crisp windows make the evening mood |
| Still lifes | Painterly | Chiaroscuro and brushwork give the look of a classical still life |
| Modern still lifes | Anime, illust | Angular forms and glowing screens are crisp with lines and flat colour |
| Interior scenes | Illust, anime | Wall textures and sunlight patches suit soft shading; painterly gives small faces fine brushes automatically |

- Scenes without figures differ little between anime and illust
    + The two styles differ mainly in the lines and shading of figures
- In painterly, areas that need fine brushes are given by `canvas.importance` (a 0-1 map)
    + Hand-sized objects in a scene get fine brushes automatically through `Prop3D.detail` (0.85 by default), furniture 0.3
- Scenes of several separate subjects set `canvas.shade_subject_as_one = False`
    + By default the whole subject is treated as one mass and darkened away from the light
