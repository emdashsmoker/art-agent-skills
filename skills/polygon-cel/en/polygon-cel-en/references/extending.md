# Engine extension guide

## When to extend
- Extend the code only when the allowed spec values cannot express the request
    + Examples: a new outfit (cardigan, trench coat), new hair (twin tails), a new background (flower field)
- Add extension code to the `scripts/codeillust/` modules and register it in the allowed spec values (spec.py ENUMS)

## Core data structures

### Layer (scene.py)
- A picture is a list of Layers, and the list order is the occlusion order
- Main fields

| Field | Meaning |
|---|---|
| name | Unique name (key for clip, cut, and cast shadow references) |
| material | SKIN, HAIR, CLOTH compute shading, FLAT is a solid color, INK is a stroke, GLOW is soft light |
| polys | List of closed curves in canvas coordinates (filled as a union) |
| strokes | [(spine points, width array)] variable-width strokes |
| clip, cut | Intersection and difference with the masks of other layer names or tags (a layer processed earlier contributes its final mask with its own clip and cut applied) |
| line | LineSpec(width px, root, root_fade, hide) outline, segments inside the hide mask are left out |
| shade | ShadeSpec(inflate, normal_map, cast_tags, cast_dist, threshold, gradient, rim, spec, spec_edge, form) |
| opacity | 0 makes a helper mask layer (material for clip and cut) |
| blend, feather | Blend mode, mask blur |
| tags | Role tags, referenced by cast shadows, clip, and cut |

### Normal maps (shapes.py)
- `ShadeSpec.normal_map` is a function `(y0, y1, x0, x1) -> (h, w, 3)` that returns unit normals
    + When given it replaces inflate, and the renderer requests only the layer's bbox
- Provided functions

| Function | Use |
|---|---|
| sphere_normals(cx, cy, rx, ry) | Fruits, flower heads |
| revolution_normals(cx, ys, rs) | Vases, bottles, cups (revolution_outline also returns ys, rs) |
| plane_normals(n) | Walls, tables, building faces |
| height_normals(w, h, scale, strength, seed, base) | Meadows, rough ground |
| mask_normals(polys, w, h, radius, noise, scale, seed) | Mountain ranges, foliage masses, clouds |
| teardrop_normals(cx, cy, rx, ry, top_reach, top_flat) | Bust (spherical below, flattening above) |
| ellipsoid_normals(cx, cy, rx, ry, rot) | Rotated muscle masses |

- Normal coordinates: x right, y down, z toward the viewer

### Tags the system reads

| Tag | Meaning |
|---|---|
| head | Casts shadows on the face and neck |
| hair_front, bangs, cap, sidelock | Front hair, shadows on the face and clothes |
| hair_back | Back hair |
| garment, garment_top | Outfit, outfit around the neck (collars and so on) |
| body, hand, legs, forearm | Skin parts |
| skirt, pants, shoes | Bottoms and shoes |
| blush_hatch | Cheek hatching for cel only (removed in other styles) |
| sleeve | Sleeves; front forearms and hands are inserted right before the first sleeve layer |
| front, behind, raised, behind_head | Placement groups of forearms and hands (behind_head is drawn before the back hair) |
| front_only | Front-only layers left out in the back view |
| seat | Chair, stool, or bed behind a seated figure (moves to the stage pass drawn before the figure passes in two-shots) |
| focus | Treated as the subject in style processing (watercolor fades outside focus to paper on plain and gradient backgrounds) |
| object, wall, tabletop, cloth, ground, building, foliage | Shadow references of scene subjects |

### Coordinate transforms
- `rig.head(P3)`: head coordinates in 3D (x, y, z) → canvas px, with yaw, pitch, and roll
- `rig.head2(P2)`: already projected 2D head points → canvas px, with roll only
- `rig.body(P3)`, `body.to_canvas(P2, z)`: body coordinates → canvas px
- `OutfitBuilder.C(P)`: 2D body coordinates with the torso front depth (front_z) attached, then transformed
- `rig.orient`: rotation of the whole rig (degrees), applied as the last step of the head and body transforms (lying uses -90)
- `props.View(origin, unit, yaw)`: object coordinates (x right, y up, z inward) → canvas px, oblique orthographic projection `Y = yb - (y + z * 0.30) * unit`
- Profile `ProfileBuilder.Hc`, `Bc`: 2D head and body coordinates multiplied by the facing sign, then transformed (x is the facing direction)
- `rig.body_local(C)`: canvas px → 2D body coordinates (z = 0 plane, the inverse of body2), used to move a two-shot contact arm from the partner's coordinates into its own
- Write every measure in H (head height) and use no px constants

## Layer stack order (character.build_layers)
- (sit) seat, (lie) shadow on the bed, (full, wide) ground shadow
- (behind_head placement) forearm skin, hands, sleeves
- Back hair (moves over the outfit in the back view)
- (behind placement) forearm skin, back sleeves
- (waist, full) leg skin
- Body skin (union of neck, torso, arms), arms_mask helper layer
- Collarbones (revealing outfits)
- (waist, full) bottoms, shoes, (front-view sit) shadow under the knees
- Top bodice, (front placement) forearm skin and hands, sleeves, collar, details
    + Hands are drawn palm, held object (hold), fingers (for a can or a phone: thumb, object, then the rest of the hand)
- Layers that cover the hands (hoodie pocket)
- Body accessories (necklace)
- Face, cheek blush, nose, mouth, eyes
- Hair cap, crown locks (left out under a beanie), bangs, side locks
- Brows (showing through the bangs, an anime convention)
- Hair shine ring, head accessories
- (raised placement) forearm skin, hands, lower sleeves
- Effects of the held object (phone screen light, cigarette smoke and ember glow)
- view side uses the separate stack of `profile.build_layers`: seat, back hair, far limbs, body skin (bust, glutes), bottoms, shoes, top bodice, near arm and hand, sleeves and front straps, face, ear, eye, side locks, hair mass and strand lines

## Two-shot and group render structure (duo.py, pipeline.render_figures)
- `duo.plan(spec, W, H)` returns the list of `Figure` in draw order (back to front, no head count limit)
    + `_rows`: row number per figure, `_ranks`: left-to-right order within a row, `_offsets`: accumulated neighbor gaps per row and back row stagger, `_place`: head height, head top, center x, per-row shrink and rise, fit-to-canvas shrink
    + The draw order starts from the figure with the largest place.depth (default is the row number)
    + Figure: per-figure spec (character replaced), Rig, characters index, reveal area, partner position, reveal exclusion area (reveal_cut)
- Render pass order
    + Background (renders the scene for a scene background)
    + Stage pass: seat-tagged layers and ground shadows of both figures (names prefixed with p0_, p1_ to avoid clashes)
    + Figure passes: one figure at a time from back to front (the front figure's coverage erases earlier line art)
    + Reveal pass: re-renders a figure that has a reveal and composites only the coverage inside the reveal area
- Style processing masks are saved per pass at output resolution, occluded by the coverage of later passes, then merged by name with a maximum
- A single-figure spec takes 1 pass and gives the same result as v8 (0 pixel difference)

### Adding a contact pose
- Write `_<contact>(chars, rigs, sides, ...)` in duo.py
    + Move a target point in the partner's body coordinates to the canvas with `rig.body2`, then into its own body coordinates with `rig.body_local`
    + Build the arm setup (elbow, wrist, forearm, hand, fingers, palm) with `_local_arm` and store it in `chars[i]["_arms"] = {side: arm}`
    + If the elbow position is free use `_elbow` (2-joint inverse kinematics)
    + Return parts that must show over the partner as reveal polygons, parts that must stay in front of the partner as reveal_cut polygons
- `_keep_posed_arm_outside` moves an arm with an action to the outer arm (`FREE_ARMS` are arm setups that may be overwritten)
- Register in spec.py `ENUMS["pair.contact"]`, `CONTACT_VIEWS`, `CONTACT_BLOCKED_POSES`, and config.py `PAIR_SPACING`

## Extension recipes

### Adding a top
- Add a `_<type>(self, g)` method to `OutfitBuilder`
    + Bodice: `self.cloth(name, self.torso(expand, hem), cut=("<neck hole helper>", "arms_mask"))`
    + Neck hole: `self.neck_hole(name, depth, half)` helper layer
    + Openings such as slits and armholes are helper layers projected with `self.S(points)` (they stay aligned with the torso when the body turns)
    + Sleeves: `front, behind = self.sleeve_layers(prefix, expand)`, then `g["back"] += behind`, `g["top"] += front`
    + Details: `self.ink(name, [(points, width_scale)], opacity)` (seams, folds, button plackets)
    + Return value: `{"clavicles": whether the collarbones show}`
- Put new outfit methods in wardrobe.py `WardrobeMixin` to keep outfit.py from growing (OutfitBuilder inherits it)
    + Fitted dresses: `self.fitted_polys(ease, hem_y, with_torso)` (convex hull of hips and thighs)
    + Seated hems: `self.hem(y)` cuts above the knee
- Register defaults in `DEFAULT_COLORS`, `DEFAULT_BOTTOM`, `DEFAULT_BOTTOM_MALE`, `TOP_HEM`
- Back view: add front-only layer names to outfit.py `FRONT_ONLY` or give them the `front_only` tag
- Profile: register (front neckline y, back neckline y, hem y, sleeve, ease) in profile.py `TOPS`
- Add the name to spec.py `ENUMS["character.outfit.type"]`
    + For a single-gender outfit also register it in `FEMALE_ONLY_OUTFITS` or `MALE_ONLY_OUTFITS`
- Write neckline and collar coordinates for the female neck and wrap them in `self.nx(points)` to follow the thicker male neck automatically
    + Armhole coordinates move out by `self.shoulder_dx`
    + Reuse `self.bust_form()` for bust shading over clothing (weakened automatically by pectoral strength for men)

### Adding a bottom
- Add layers to `g["bottom"]` in a `_<bottom>(self, g)` method
    + Skirts reuse `self._skirt_layer(name, right_outline_points, color)`
    + Pants reuse `self.pants_layers(name, waist_height, hem_height, ease, bevel, gap)` (gap is the wedge width between the legs)
    + Swim bottoms reuse `self.brief_layer(name, right_outline_points, color)`
- Profile: register (waist y, hem y, ease, kind pants|flare|fitted|brief) in profile.py `BOTTOMS`

### Adjusting a gender skeleton
- Register shoulder joint, neck width, hand scale, abs on or off, and leg spacing scale in body.py `GENDER`
- Register torso silhouettes as right-half point lists in `FIGURES` (female) and `MALE_FIGURES` (male)
- Limb width profiles are in `LIMB_WIDTHS[gender]` (any number of samples, add samples to express muscle bulges)
- Male muscles are in musculature.py: 1 muscle is 1 dome-normal skin layer (`_mass`), boundary lines go in `border_lines`
- Bust and pectoral forms branch by gender in 3 body.py functions: `bust_shape`, `crease`, `bust_normals`
- Adjust face, eye, and hair defaults in spec.py `MALE_PRESET` (user values always win)

### Adding a hairstyle
- Add a style branch to `back_layers` and `side_layers` of `HairBuilder`
    + 1 lock: `self.clump_layer(name, 3D control points, root width, width profile, tags)`
    + A point on the scalp: `self.S(x, y, lift)` (shell surface z computed automatically)
    + Width profiles: `blade` (bang type, pointed tip), `lock` (long lock type)
- Register in `DEFAULT_LENGTH` and spec.py ENUMS
- Vary lock widths irregularly in a large, medium, small rhythm (repeating one width looks like comb teeth)

### Adding arm poses and hand gestures
- Add an arm setup to body.py `ARMS`: elbow, wrist (coordinates of the screen-right arm), forearm placement, hand gesture, fingers direction, palm normal
- Register the (screen-right arm, screen-left arm) pair in `POSES`
- Register curl (3 bends per finger × 4 fingers), spread, and thumb (abd, opp, curl) in hand.py `GESTURES`
- Register in spec.py ENUMS

### Adding a full-body posture
- Register a leg template in body.py `STANCES`: tilt, knee and ankle of the screen-right leg (R) and the screen-left leg (L)
    + `raised_foot` is a foot tipped back against a wall (foreshortened from the front, hidden from behind), `knee_caps` are knee caps on thighs foreshortened toward the viewer
- Register the arm pair in `POSES` and link the pose name to a stance in `POSE_STANCE`
- If the rig must rotate, set orient in character.py `make_rig` (see lying)
- For profile support add arm and leg joint coordinates to profile.py `PROFILE_POSES`

### Adding a modern object
- Write a `def <kind>(kit, color, rng, **options)` function in props.py, then register it in `PROPS`, `PROP_COLORS`, `PROP_YAW`
    + Parts: `kit.box(part, origin, ex, ey, ez, color)`, `kit.rod`, `kit.dome`, `kit.revolution`, `kit.flat`
    + With a screen use `kit.screen(part, quad, theme, rng)` and register in `SCREEN_PROPS`
    + Add parts from back to front (no depth sorting)
- still_life.py recognizes any type in `props.PROPS` automatically; add it to the spec.md table

### Adding an interior room
- Write a method named after the room in interior.py `RoomBuilder`: `self.shell()` (walls, floor), `self.window`, `self.furniture_box`, `self.prop`
- Register in `ROOMS`, `PALETTES`, and the (room, "day") tint in pipeline.py `SCENE_GRADE`
- Register `interior.room` and `background.type` in spec.py ENUMS, and character.py `GROUNDED_BACKGROUNDS`

### Adding a scene subject
- Implement `build(spec, W, H, light, seed) -> (layers, background, light)` in `scripts/codeillust/<subject>.py`
- The pipeline loads the module by subject name; register it in spec.py `ENUMS["subject"]`
- Tag subject layers with focus to mark them for style processing

### Adding a background
- Add a branch to background.py `make_background`, register `DEFAULTS` and ENUMS
- Keep backgrounds lower in contrast and detail than the character

### Adding a held prop
- Register the holding arm setup in handheld.py `HOLD_ARMS`: elbow, wrist (screen-right arm), forearm, hand, fingers, palm, wrist_shift
- Write `<item>_layers(body, side)` and register it in `BUILDERS`
    + The return value is (mid, late): mid goes between palm and fingers, late is drawn over the whole figure
    + An object held with the back of the hand toward the viewer gets `BEHIND_HAND_TAG` on its layers and is drawn before the palm and fingers
    + In that case set hand "grip" in the arm setup, fingers across the object's front, palm facing the object
    + Place the object with `_knuckle_anchor(body, side, offset)` from the knuckles (the hand size scale applies automatically)
    + If the thumb touches the object's far face, add `"thumb_behind": True` to the arm setup to draw the thumb behind the object
    + Place other objects with `_anchor(body, side, offset)` in body coordinates from the wrist (the x sign flips for the screen-left hand)
    + Project body-coordinate polygons to the canvas with `body.to_canvas(poly, Z_FRONT)`
- Register in spec.py `ENUMS["character.body.hold.item"]`

### Adding a mood
- Register per name in spec.py `MOODS`: spec (finishing, scene defaults), background (character background), character (character defaults)
- If it needs its own grade, add a branch to post.py `grade` and register `ENUMS["post.grade"]`
- Register `ENUMS["mood"]`; mood values sit under the user's spec, so user values always win

### Adding a style
- Register `StyleName`, `PRESETS` (Style), `POST_DEFAULTS`, `DROP_TAGS` in styles.py
- Add a branch to `finish()`: inputs are the color pass, the line pass (rgb, alpha), and the layer masks
- Register in spec.py ENUMS["style"]

## Cautions
- Helper masks: neck_mask, torso_mask, upper_arm_mask, arms_mask (used to cut straps, tube tops, and sleeves)
- Women add a bust_mask, and the bust area is removed from upper_arm_mask and arms_mask (sleeves empty the bust with `self.bust_cut`)
- No duplicate layer names (mask store key clash); two-shots and groups allow duplicates across figures because each figure has its own pass
- When adding a male muscle layer, multiply its opacity by `musculature.strength(body)` so it follows body.muscle
- Masks are stored in raster.MaskStore as uint8 per bbox, and each read builds a full-canvas float array (saves memory in scenes with hundreds of layers)
- Helper layers have opacity 0 and are left out of the character mask in style processing automatically
- A clip that names a tag the layer itself carries intersects with its own mask and has no effect
- A clip with several names intersects with the union of those masks
    + If you need the intersection of several masks, build it first on a helper layer (opacity 0) with clip, then reference that name
- Cast shadows come only from layers higher in the stack; check the order first
- With 2 or more polys or with clip or cut, line art is extracted from the final mask outline
- After extending, check with `python scripts/selftest.py` and a draft render
