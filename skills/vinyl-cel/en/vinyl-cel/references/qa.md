# Review criteria

## Procedure

1. Render with `--preview`
2. Open `_overview.png` and check the overall impression and composition
3. Open `_face.png` and check the eyes, nose, mouth and fringe
4. Go through the items below and apply the fix for any defect
5. When there is no defect, render at final size and repeat steps 2-3 once
    + Thin lines and grain that the preview hides show at final size

## Checklist

| Area | What to check |
|---|---|
| Composition | Is the space above the head 10-20% of the frame height, and does the figure fill at least half of the frame |
| Face | Do both eyes match in height and size, is the jawline smooth, are the nose and mouth on the face's centre line |
| Eyes | Are the irises inside the lids, are the highlights on the same side in both eyes |
| Hair | Is no scalp showing, are there no seam lines at lock roots, does the highlight band stay off the face |
| Body | Do neck length and shoulder width suit the head size, does no clothing stick out past the body |
| Light | Do all shadows fall away from the light (lower right by default) |
| Lines | Are there no breaks and no stair-stepping |
| Style | Does the chosen style's signature (cel edges, paper grain, brushwork) show at first glance |
| Full body | Are there no ring-shaped lines at the joints, does an arm in front show over the clothes, do the feet stand on the ground shadow |
| Impression | Do the face and head ratio match the intended impression (mature, youthful), does the outfit cover the intended areas |
| 3D figures | From the front, 3/4, side and back: does no skin poke through clothes, is no scalp showing at the temples and the back of the head, do knees and elbows not bend backwards, do hands neither sink into the body nor float, do the feet touch the floor, do straps not look broken, are cel shadow edges smooth |
| Floor poses | Do a lying figure's head, back, hips and heels touch the floor or mattress together, do a kneeling figure's knees and insteps touch the floor |
| Hands | Are the fingers even in thickness, is there no step between wrist and palm |
| Modern objects | Is `scene3d.overlaps()` an empty list, do objects not float above the top (contact shadow), do screens face the user, does what lies behind show through glass |
| Interior scenes | Do the walls, floor and furniture share vanishing directions, do furniture legs and feet touch the floor, are seated figures' hips on the seat, do hands read as holding the keyboard or device |
| Landscape | Is there no empty area below the horizon, does the reflection start at the lake shore, are far mountains paler than near ones |
| City | Do the rows of windows converge on the vanishing point, do tall buildings not look paper-thin, are reflections right under the buildings |
| Still life | Do objects not float above the table (shadow at the base), are the outlines symmetric |
| Colour | Is there enough contrast between the main colour and the background, are shadow colours not muddy |

## Fixes by symptom

| Symptom | Cause | Fix |
|---|---|---|
| A wide patch of skin shows on the forehead | Fringe locks too narrow or the bottom edge of `cap` too high | Set `width` in `bangs` to 0.45 or more, lower the y of the bottom edge of `cap` |
| Many radial lines on the crown | Lock root lines show | Raise `rig_hair.ROOT_FADE` |
| A wide shadow band on the face | Face `roundness` too high | Lower `rig_face.FACE_ROUNDNESS` |
| Thorn-like shadows above the eyes | The fringe shadow falls too long | Reduce `rig_face.FRINGE_SHADOW_DROP` |
| Small head, large body | `head_radius` too small | Raise `head_radius` and adjust `head_center` |
| The neck looks long | y of `neck_offset` too large | Lower it into the 1.55-1.65 range |
| Shoulders look broad and masculine | `shoulder_half_width` too large | Set it in the 1.35-1.45 range |
| A clothing corner sticks out over the arm | The cloth shape does not follow the torso's side line | Put the cloth shape's end points on the armpit coordinates and multiply by the body mask |
| The highlight band looks like a headband | The band is thin and uniform | Set `highlight_thickness` to 0.15 or more |
| The far eye is awkwardly narrow | `yaw` too large | Keep the absolute value within 0.3 |
| Clouds look like blue lumps | Too much shade | Raise the start value of `background.PUFF_SHADE_BAND` |
| Painterly faces look blotchy | Colour jitter in the fine brush layers | Lower `brushwork.COLOR_JITTER` or the later values of `RELIEF_GAIN` |
| Painterly faces look washed out | The underpainting is too bright | Raise `finish.PAINT_GAMMA` |
| The output file differs between runs | Random numbers drawn outside `canvas.rng` | Draw all random numbers from `canvas.rng` |
| Doll-like ring lines at the joints | Height difference between the forms in front and behind | Merge them at the same `depth`, or raise the depth gradually along the arm |
| Round objects cut into each other | The front object's `depth` is too small | Use `depth=FRONT` |
| A ring round an inflated form | The rim of `bump()` | Switch to the rimless `swell()` |
| Radial streaks on a relief surface | Ridges in the height map | Raise `relief.RIDGE_SMOOTHING` or `NORMAL_SMOOTHING_PX` |
| Nails of a hidden hand show over the clothes | Finishing details ignore occlusion | Clip them with `relief.visible(name)` |
| In painterly, only one subject is dark | Separate subjects shaded as one mass | `canvas.shade_subject_as_one = False` |
| Mountains fill the frame | Peaks too high or focal length too long | Lower `peak_height` or `Camera.focal` |
| Mountains look like grey lumps | Haze too thick or too much rock | Raise `haze_distance` and `terrain.ROCK_SLOPE` |
| The lake looks like a thin strip | The camera is low | Raise `Camera.eye_height` |
| Buildings look like thin blades | The wall facing the camera is missing | Use the front walls of `draw_buildings()` (the default) |
| Cloth looks like corrugated iron | Even fold spacing | Raise `fold_units` of `stilllife.cloth()` |
| Horizontal lines at knees and elbows | The forms before and after the joint are inflated separately | Inflate one mass through the joint (`rig_figure._limb_chain`) |
| A dotted line on the shoulder | The edge where the arm rises over the torso | Add the arm with `edge=False` |
| A dark band across the lower belly or the middle of the bottoms | The torso swell drops steeply at the crotch apex | Raise the height of `rig_figure.LOWER_ABDOMEN` |
| Hip skin shows beside a skirt | The skirt outline lies inside the build's hip curve | Move `rig_figure.SKIRT_UPPER_HIP` outward |
| A hand on the hip lies on the belly | The hand continues the forearm's direction | Turn the fingers down with `Pose.wrist_*` |
| The figure looks younger than intended | Big eyes, short lower face, big head | Apply `adult_face()`, `head_scale` 1.0 |
| (3D) Patches of skin show through clothes | Cloth thickness smaller than the swell where skin parts blend | Use thickness `TIGHT` (0.030) or more, and set the layer in `GARMENT_LAYERS` |
| (3D) Trousers show as a sawtooth under a top's hem | The tops of the thighs and the hip swell of the trousers | Make the top a layered garment and `hip_cover` is added automatically |
| (3D) Horizontal striped shading on clothes or body, sawtooth shadow edges | Creases between section ellipsoids or chained spheres | Raise `body3d.SECTION_OVERLAP` (section length), `SWEEP_BLEND` (narrow smooth union of sphere chains) and `SURFACE_SMOOTH` |
| (3D) Occlusion lines break up like dotted lines | The depth difference hovers round the threshold | Raise `body3d.LINE_JUMP_SMOOTH` or drop short pieces with `LINE_MIN_LENGTH` |
| (3D) Strings sink into the skin and break in places | Straight runs of the string path go into the chest, collarbone or neck | Pass the string path through `wardrobe3d.over_skin()`, distance outside the torso `STRING_CLEARANCE` |
| (3D) A string end floats away from the cup | The string starts inside the breast | Start strings at the visible cup corner found by `_cup_corner()` |
| (3D) Sleeves or trouser legs end in round balloons | The end hemisphere of a sphere chain | Apply `flat_hem()` to tubes that end midway (`leg` and `sleeve` do it automatically) |
| (3D) The cut edge of an opening is stepped | Each section piece is cut separately | Pieces of the same `part` are cut once on the merged surface (`DepthRenderer._cut_part`, automatic) |
| (3D) The ends of long hair clump round like a cape | The back hair sheet ends in one mass | Split the ends into strands with `Hair3D.tips` (applied by default in `LONG_HAIR`) |
| (3D) A male face looks feminine | Long lashes, large irises, lip colour | Use `male_face()` (sets `lash_weight`, `brow_weight`, `iris_scale` and `lip_tint`) |
| (3D) A lying figure floats or touches on one side only | The body tilts so only the lowest single point touches | Adjust the pelvis `rx` and the hip `rx` by 0.02-0.05, check the contact parts with `ground_points()` |
| (3D) Fingers in a pocket show over the trousers | The hand lies outside the body surface | Point the fingers into the body (negative z in `fingers`) and use a trousers-type outfit |
| (3D) In a hands-in-pockets pose the sleeve end sticks out past a top's hem | The sleeve end is thicker than the top's pocket swell | Raise `POCKET_SLEEVE_ROOM` and `POCKET_SLEEVE_WIDEN` (long sleeves are cut by `tuck_into_pocket` automatically) |
| (3D) Small white ovals or dark specks between arm and body | Gaps a hair's width wide between arm and body | The renderer closes enclosed gaps up to `SLIVER_AREA` (0.004 square head heights); raise it if larger gaps remain |
| (3D) In a backlit scene the figure glows from the front | The default light is in use | Give `light` a negative z |
| (3D) A shoulder strap floats above the shoulder like a handle | A round tube on fixed coordinates | Make straps with `strap_over_skin()` |
| (3D) A seated figure's top hem sticks out like a flap at the hips | The torso end and the hip cover are cut at different places | Cut both with the `hem_cut()` plane (automatic for a top over bottoms) |
| (3D) In a 3/4 face the far eye pokes out past the cheek outline | Features drawn on the outline band or outside the face | Features are limited to inside the outline, and brows and lashes over the hair to the head and hair area (automatic) |
| (3D) In a side view the hand gesture is hidden by the face or body | The gesturing hand is on the far side from the camera | Mirror the pose with `rig3d.mirrored(pose)` |
| (3D) The figure looks like floating with a level camera | The floor shadow is an ellipse unrelated to the viewpoint | `figure3d.floor_shadow()` projects it in perspective (automatic) |
| (3D) Shorts look like a skirt | Legs end at crotch height and the legs no longer separate | Extend the legs below the crotch (`HOT_PANTS_LEG` 0.19); the front centre seam is automatic |
| (3D) Shadow edges are stepped | Shadow samples too far apart | Lower `relief.CAST_SAMPLE_PX` |
| (3D) Skin shows at the temples or the sides of the head | The scalp layer is cut over too wide a range | Lower `Hair3D.scalp_drop` or narrow `FACE_OPENING` |
| (3D) Sleeves puff up like balls | Sleeve ease is large even over the shoulder | Raise `wardrobe3d.SLEEVE_EASE_LENGTH` or lower the sleeve thickness |
| (3D) Shoulders rise in a hard angle | The arm root sphere rises above the torso | Adjust the trapezius shape (`TRAPEZIUS_SLOPE`) and the height of the first `ARM` control point |
| (3D) Knees or elbows bend backwards | Wrong sign of `rx` | Bend knees with positive `rx` and elbows with negative `rx` |
| (3D) A hand sinks into the hip | The target lies inside the build | Give the `Reach` target relative to a `hip_*` joint (it follows the pelvis width) |
| (3D) The wrist bends as if broken | Hand direction too far from the forearm | Turn `fingers` toward the forearm direction, or move the elbow with `pole` |
| (3D) Dot-like specks on clothes | Short pieces of hidden seam lines | Raise `figure3d.MIN_RUN_WIDTHS` |
| (3D) Hair covers the face | The hair mass comes forward of the face | Reduce the z of `Hair3D.cap_radii` or raise `HAIRLINE_Y` |
| (3D) Rendering is slow | Proportional to the number of figures and canvas size | Review sheets with `--preview` and render the final once |
| (Scene) An object's corner sticks out over another object | The two objects really overlap (a book behind a laptop lid) | Find overlapping pairs with `scene3d.overlaps(items)` and move the `on_top` offset |
| (Scene) Glass looks like an opaque panel | The glass part is in `solids` | Put clear parts in `Prop3D.glass` (`drinking_glass()` is the model) |
| (Scene) A cable sinks into the top or floats | Path points differ from the surface height | Put path points at the height of the top or floor (the axis lifts by the radius automatically) |
| (Scene) Screen content looks washed out | The glow overlaps the screen | The glow is applied outside the screen only (strength with `props3d.GLOW_STRENGTH`) |
| (Scene) Screen content is drawn over another object | Several objects share the screen material | Give each screen panel a new material with `own_material()` |
| (Scene) A keyboard looks like a black ripple | Material border lines between the keys and the base | Bring the key material's line colour close to its base colour (`KEYCAP`) |
| (Scene) The bottom or side of the frame stays white canvas | The eye is outside the room | Lower the camera `distance` or widen the room's `Shell`; the floor runs on by `FLOOR_MARGIN` |
| (Scene) Exaggerated perspective makes near objects large | The eye is too close | Raise `distance` and match the size with `scale` |
| (Scene) A seated figure floats above or sinks into the seat | The seat height does not match the pose | Use `seated()` and `furniture3d.SEAT_TOP`, and give new seat furniture the same height |
| (Scene) A seated figure's skirt hangs as a cone below the knees | A custom skirt does not use `_skirt_fall()` | Take the skirt path direction from `_skirt_fall()` (`skirt_flared` is the model) |
| (Scene) Typing hands do not reach the keyboard | The laptop is too far from or too close to the pelvis | Put the keyboard's front edge about one head in front of the pelvis (`desk_worker3d.LAPTOP_DEPTH`) |
| (Scene) A phone or cup looks detached from the hand | A pose not made for the object is used | Use the pose paired with `held_*` (`stand_phone`, `sit_mug` and so on) |
| (Scene) In painterly, small objects smear into blotches | Only coarse brushes applied | Set `Prop3D.detail` to 0.8 or more |
| (Scene) In painterly, small faces smear | The face is very narrow (under 60 units) | Raise the camera `scale` or `finish.SMALL_FACE_UNITS` |
| (Outdoor) The street lamp head leaves the frame | The lamp is close to the camera or too tall | Put the lamp behind the figure or use a lower lamp (`street_lamp(cm(560), cm(110))`), and check coordinates with `camera.project` before rendering |
| (Outdoor) The figure under a lamp is a black silhouette | The figure is outside the lamp's cone (`cone`) | Move the figure right under the lamp or widen `lamp_light(..., cone=...)` |
| (Outdoor) Buildings cover the whole frame and leave no sky | The buildings are close | Move them further away (10 times the camera distance or more) or reduce the floors |
| (Outdoor) The ground looks flat and bright like a stage | The snow colour is brighter than the light preset or the lamp pool is wide | Darken `Light.snow`, lower `LAMP_REACH` or `cone` |
| (Outdoor) The horizon colours of the sky do not show | The sky stops follow the canvas height | `sky(..., horizon=horizon_y(camera))` (`draw_world` does it automatically) |
| (Outdoor) Far buildings vanish in the fog | `Fog.distance` is shorter than the building distance | For wide views give a separate `Fog(distance=metres(400-2200))` |
| (Outdoor) In painterly, windows and poles smear into blotches | Only coarse brushes applied | Facades, ground and wires use `keep_detail` automatically; for a new plane use `interior.keep_detail(canvas, mask, 0.7)` |
| (Outdoor) In painterly, snowflakes smear into blobs of paint | The snow is drawn before the finish | Put the snow in `canvas.overlays` so it is drawn after the finish (`draw_world` does it automatically) |
| (Outdoor) Scenes with many birches are slow | Hundreds of spheres per thin twig | Twigs with a screen radius under one pixel use touching spheres (automatic, `SWEEP_SUBPIXEL_SPACING`); if still slow, lower `BIRCH_TWIGS` |
| (Light) The laptop lid blows out to white | The screen lamp lights the bright aluminium lid right in front of it | Give the lid a dark colour (`laptop(shell=...)`) and make the screen light paler |
| (Light) Faces turn murky purple or grey | A saturated blue screen light multiplied with a low ambient | Use a pale screen colour such as `#D2DEF8` and add some red to the ambient |
| (Light) A face looking down joins the nose and mouth lines into a hook | Anime line art with a camera looking down | Use `illust`, a camera `pitch` of 0.06 or less and a smaller downward gaze (`gaze` y) |
| (Light) A walking figure's thigh pokes through the front of the skirt | The stride is wider than the skirt | Scale the leg joint rotations by 0.55 (`beach_sunset.STROLL`) |
| (Light) A tree or lamp pole stands behind a head | Placed only by world coordinates | Choose the canvas x first and solve the world x (`dusk_bench.world_x`) |
| (Outdoor) Smoke does not show | The smoke colour is close to the bright snow behind it | Compose so a dark building or sky lies behind the smoke, or raise the opacity in `smoke_wisps` |
| (Outdoor) A wall splits into a brighter top and a darker bottom | Plane lighting also lights pixels of another plane | Light only the pixels that plane painted with `light_plane(..., mask=draw_surface(...))` |

## Isolating the stage

- When it is unclear whether a defect comes from the drawing stage or the finishing stage, save the state before finishing with `studio.render(..., finishing=False)` and compare
- When a specific part is suspect, leave out the calls after that part in `compose()` for a moment and render
