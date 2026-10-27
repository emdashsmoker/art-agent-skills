# How the stages are implemented

## Contents

- Modules
- Volume engine
- How each subject is built
- Stage 1 sketch
- Stage 2 flat colour
- Stage 3 shading
- Stage 4 inking
- Stage 5 finish
- Defects and the stage that causes them

## Modules

| File | Role |
|---|---|
| `scripts/raster.py` | Basics: curves, masks, strokes, compositing, noise |
| `scripts/relief.py` | Volume engine: height fields and lighting of tubes, solids of revolution, ellipsoids |
| `scripts/kit.py` | Tools shared by subjects: solid shading, outline extraction, shadows, ridgelines |
| `scripts/figure.py` | Portrait sketch: turns the spec into curves and shapes |
| `scripts/painter.py` | Portrait painting and `Scene` (style-dependent edges, inking) |
| `scripts/anatomy_body.py`, `scripts/anatomy_hand.py` | Full-figure skeleton (front, back) and the jointed hand model (back, palm). Sex body tables `FEMALE`, `MALE` |
| `scripts/anatomy_profile.py` | Figures in profile: profile face and body line, seated poses. Sex tables `FEMALE`, `MALE` |
| `scripts/subject_*.py` | Composition and painting of each subject |
| `scripts/wardrobe.py`, `scripts/wardrobe_profile.py` | Additional front and back garments (long sleeves, skirt, jacket, coat, hanbok), garments in profile |
| `scripts/wardrobe_casual.py` | Hoodie, swimsuit, bikini, swim trunks |
| `scripts/patterns.py` | Cloth patterns (stripes, check, dots) |
| `scripts/accessories.py` | Glasses, hat, scarf, bag (every view) |
| `scripts/expressions.py`, `scripts/looks.py` | Expression presets, looks (face shape, eye shape, hair style, colours, identity seed) |
| `scripts/interior.py` | Interior subjects (cafe, living room, bedroom, bathroom) |
| `scripts/weather.py` | Rain, snow, falling petals |
| `scripts/held.py` | Objects held in a hand (cup, book, umbrella, wine glass, phone) |
| `scripts/props.py` | Scene props shared by several figures (bench, cafe table) |
| `scripts/lying.py` | Lying poses: paints a figure in profile in a rotated frame and turns it back |
| `scripts/subject_beach.py` | Beach subject |
| `scripts/subject_park.py`, `scripts/subject_skyline.py` | Park and cherry-blossom avenue, sunset rooftop and riverside fireworks |
| `scripts/subject_blocks.py` | Panel apartment blocks and the outskirts (building walls, utility poles, street lamps, birches, pylons, crows) |
| `scripts/smoking.py` | Cigarettes (in the mouth, in the hand, on an ashtray) and smoke |
| `scripts/finish.py`, `scripts/brushwork.py` | Finish of each style, brush-stroke reconstruction |
| `scripts/media.py` | Finishes of the other media (watercolor, pencil, manga, pixel art, film night) |
| `scripts/render.py` | Entry point and scene composition (backdrop, companions, colour grade, hand targets between figures, re-laid parts, prop measurement) |
| `assets/spec_default.json`, `assets/style_*.json` | Default figure spec, style files. A style with a `base` key is laid over that style's file |
| `assets/subject_*.json` | Default composition and palette of each subject |
| `assets/sex_male.json` | Male preset: face, hair, neck, outfit, colours per style, full-figure outfit |
| `assets/expressions.json`, `assets/looks.json` | Expression and look presets (lists of setting operations) |
| `assets/accessories.json` | Accessory palettes |

## Volume engine

- A mass is represented as a height field over the picture
    + (Tube) a generalised cylinder defined by a path and a width profile. Limbs, torso, fingers, pears
    + (Solid of revolution) a vertical axis and a radius profile. Bottles, bowls
    + (Ellipsoid) fruit, rocks, tree crowns
    + (Bump) a soft swelling added onto another surface. Breasts, kneecaps, knuckles
- The slope of the height is the normal, so one light vector lights every subject the same way
    + Diffuse light is the dot product of normal and light. Gloss is Blinn-Phong
- Several parts merge into one surface by the maximum of their heights before lighting
    + On the body, a smooth maximum where parts overlap joins the limbs to the torso with a round fillet. It makes the largest difference between a mannequin and a body
    + Breasts and buttocks are asymmetric bumps: long and gentle above, short and round where they turn below
    + An arm melts into the body at the shoulder root and rises in front of the body further down. The two rules blend with a continuous weight
    + Seams are melted by blurring the height field before lighting
- A part placed in front (an arm before the torso, a thumb before the palm) gets extra height to show the overlap, plus a contact shadow
- Skin gets two extra lights
    + (Rim light) a thin bright edge along the silhouette on the shadow side
    + (Bounce light) warm light from below, so the area under the chest or the chin does not read as a black hole
    + A reddish tint on the shadow boundary suggests light spreading under the skin
- Cloth starts from the body's height field and is computed to hang from high points (a downward sweep with a slope limit. Narrow side valleys are filled by a closing operation)
    + (T-shirt) torso and shoulder caps as one body piece. The sleeves are painted as its continuation and only the sleeves' own edges are inked
    + (Trousers) the pelvis part and two leg tubes are merged before the hanging is computed
    + (Hip cloth) wraps along the body's outline with a slanted hem that hangs lower on the knot side
    + (Lap cloth, seated front) covers thighs and knees and sags between the knees. Its height is blurred only inside the cloth, so the empty space between the legs does not drag its edges dark
- Bones that come toward the viewer (a seated thigh, a forearm reaching to the knee) gain height along their length
    + The front part hides the body behind it and its top surface faces up and brightens
    + The near end (the knee) is widened for perspective. The shin hanging at knee depth gets half of that enlargement, the foot a quarter
    + An overhead light (straight above, slightly in front) brightens the upward-facing tops of the thighs. Under cel and grain shading the knee tops and the belly would otherwise fall into the same bright step and the change of plane would not show
    + (Check) the median brightness of the thigh tops is measured per style to be higher than the belly's
- Inking extracts the outlines of the masks and draws them
    + The root of a tube growing out of another mass is left without a line

## How each subject is built

- (Full figure) The spine curve bends from the shoulder tilt to the pelvis tilt and becomes the centre line of the torso tube. Limbs are placed by forward kinematics of the joint angles
- (Hand target) When an arm has a target, two-joint inverse kinematics solves the angles
    + To put the middle of the palm (0.3 of the hand length from the wrist) on the target, the wrist position is found by stepping back along the hand's direction. The law of cosines with the shoulder-to-wrist distance and the two bone lengths gives the elbow
    + The elbow has two solutions, chosen by `bend` (out from the body, in, down, up). `straight` shortens both bones by the same ratio into a straight arm reaching toward the viewer
    + Raising an arm past 90 degrees lifts the shoulder, so the shoulder position and the solution are corrected alternately 4 times until they converge
- (Hand in front of the face) The picture is saved just before the head is painted. After the head, only the area of the forearm and hand (with the near sleeve) is pasted back. The hand's shadow is the hand mask pushed down and away from the light, multiplied onto the face only
- (3/4 view) A projection of the body turned about a vertical axis is laid over the front skeleton
    + Points on the body's mid-plane (spine, joints) have their horizontal coordinate multiplied by cos
    + The visible half-width of the torso's elliptical section (half-width w, depth w x roundness) is sqrt((w cos)^2 + (depth sin)^2)
    + A point on the front surface at horizontal position a goes to a cos + depth x sqrt(1 - (a/w)^2) x sin. Breasts, navel, collarbones, neckline, buttons and zips slide toward the turned side
    + Garments follow automatically through the spine coordinate functions (`spine_at` on the front surface, `spine_side` on the outline)
    + The far arm is treated as a bone passing behind the torso. The near leg gets extra height to lie in front of the far leg
- (Actions in profile) Running, jumping and crouching come from the leg angles and body lean of the profile skeleton alone. Feet can turn at the ankle. Being in the air only lowers the floor and the shadow
    + Raising a thigh far forward straightens the buttock outline (stretched glutes)
- (Lying) A person lying down seen from the side looks like a standing profile figure turned by 90 degrees
    + The canvas size, eye position, light vector and backdrop are all moved into the rotated frame, the profile figure is painted there, and the result is turned back
    + The columns where the body touches the ground (back or front) are measured and the figure is moved so they meet the given ground height before turning it upright again
- (Hands) Finger curl shows on the picture as cosine shortening of the phalanx lengths
- (Still life) A view looking slightly down on the table. Round sections become ellipses. Cast shadows are ellipses away from the light
- (Landscape) Painted in bands from far to near. Ridgelines are octave noise. Mountain shading samples the ridge slope obliquely with depth. The lake is the scene above flipped and rippled
- (City) The street is laid out as 3D boxes in metres with a pinhole projection. With real dimensions, perspective shrinking comes out right by itself
    + At night every light source is recorded in a separate light layer, two levels of glow are added, and the light layer is flipped about the line where buildings meet the ground and smeared vertically into wet road reflections
- (Desk) The desk sits in a 3D space in centimetres seen by a camera looking down. Each box face takes its brightness from its angle to the light, giving manufactured goods hard planes. Round objects reuse the volume engine. A lit screen is a light source
- (Figures in profile) The torso tube gets separate front and back depths at each height to form the S curve of the back. Breasts and buttocks are added as soft solids (blobs) drawn from their outlines
    + Seated poses cut away everything below the seat top, flattening the underside of the buttocks and thighs and spreading the buttock outline backwards
- (Outfits) Outlines are cut with body-part masks and spine coordinates. The hanging cloth surface is computed from the body's height field and painted
    + Inner garments first, then the arms laid again over the clothes, then the sleeves last
    + Sleeve length limits come from the projection along the bone direction, because a tube's own coordinates are valid only inside its bounding box
    + In profile, the front view's spine heights are mapped to profile heights at the chest, waist, pelvis and crotch, so the same settings can be reused
- (Arms in front and behind) A bone going behind the body gets less height and the in-front rule is switched off there. The torso and head hide that part
    + When arms overlap, the arm placed later lies on top. The lower arm's line is erased under the upper arm
- (Held objects) The object is painted behind the hand, then the forearm, the back of the hand and the four fingers are laid back on top. Only the thumb hides behind the object
    + Re-laying only the fingers leaves the back of the hand and the cut-off fingers floating in the middle of the object, as if the hand went through it
    + Grip positions: a cup's body centre lies under the curled fingers with the handle away from the wrist. A book's top edge lies at the finger roots
- (Scenes) The backdrop subject is painted first and used as the figures' background layer. A standing adult's eyes are at camera height, so they sit on the horizon. The figures are multiplied by the colour of the backdrop's light
    + A hand target aimed at another figure is resolved by the scene, which builds that figure once more, reads the point and turns it into a picture position. So hands meet even though each figure is built separately
    + Figures overlap as whole layers, so a part that crosses in front of a later figure (a hand on the other's shoulder) is cut out of the earlier figure's picture by its mask and pasted again over the later figure. This extends the re-laying used for held objects to pairs of figures
    + Shared props (bench, table) take their size from the hips, knees, elbows and soles of the figures using them and are painted in the background stage of the figure painted first, so every figure stands in front of the prop
- (Umbrella) Painted after the head, so the canopy lies over the hair and over earlier figures. The canopy and the column under it are removed from the rain layer of the weather stage
- (Beach) Painted from far to near: sky, sea (from deep at the horizon to pale turquoise at the shore), foam along the winding shoreline, wet sand taking the sky's light, dry sand. Palm fronds are strokes whose width varies like teeth along the midrib, so they leave no holes when they overlap
- (Expressions and looks) A preset is a list of operations on setting values (`add`, `scale`, `set`, `style_scale` for rendering strength)
    + The same change sits on each style's own base proportions, so an expression does not break the style's face
    + Values written by the user are excluded from the operations
    + Smiling eyes curve both lid curves upward. Closed eyes merge the two curves into one line and drop the catchlight
    + Skin tone moves the style's whole skin palette by per-channel ratios to the reference skin colour, because rotating the hue turns it orange
    + The identity seed adds a random amount within a set range to each face setting, giving different faces within the same style
- (Patterns) After the garment is painted with its shading, the pattern is drawn inside its area and the pattern colour is multiplied by the brightness ratio of the base, keeping the shadows of the folds
    + Patterns are fixed to picture coordinates, so body and sleeves of the same garment continue into each other
- (Accessories) Head accessories are defined in the head's 3D coordinates and follow the head turn
    + Glasses temples go under the hair. Frames and lenses go over it
    + For a hat, the hair is painted first, the hair poking out above the hat line is painted out with the background saved earlier, and the hat is painted on top. The hair does not need to be rebuilt to the hat's shape
    + The brim's shadow is the brim mask pushed down, multiplied onto the face and hair only
    + The bag and the scarf are a layer over the clothes and under the arms. The step that lays the arms again over the clothes puts them in the right order by itself
- (Swimwear) Uses a widely blurred copy of the body's height field directly. It does not hang from high points like loose clothing, so it reads as tight to the body
- (Interiors) The room is a box in centimetres projected by a level camera into one-point perspective. Walls, floor and ceiling each have a fixed brightness. The corners get a blurred shadow band (ambient occlusion)
    + Floor items are painted in depth order, reusing the desk subject's box painting and potted plant
    + The view outside is a picture of sky, buildings or trees and weather painted inside the window glass mask
    + At night the whole picture is darkened toward blue, except pixels painted as the view outside or as lit lamps and not covered afterwards. Each lamp adds a warm glow
- (Weather) A grey cast, a thin haze and a layer of rain streaks or snowflakes are added in turn. Snowflakes are split into 4 layers by size and only the large ones are blurred, giving depth
    + Petals use the same 4 layers with ellipses turned at many angles, painted with normal blending (`over`) so the pink shows even on a bright sky
- (Park and skylines) Ground and buildings are projected by the same level camera in centimetres as the interiors
    + Each ground pixel is projected back to ground coordinates (X, Z), which give the mown stripes and the gingham checks in correct perspective
    + Tree crowns are ellipsoid clumps sized by depth and arranged in a dome. Noise roughens the edges and holes inside show branches and sky
    + Far things are covered by sky colour in proportion to distance (aerial perspective)
    + Building fronts are parallel to the picture, so the window grid is computed at once with modulo arithmetic on pixel coordinates, and each window is lit by a fixed random number
    + The river flips the picture above about the bank line, ripples it, and blurs only the bright pixels vertically into light columns
    + Fireworks are three layers: rays drooping under gravity (brightest at the tips), a near glow, and a large halo lighting the smoke
- (Looking back) After the back view's body is painted, the head layout of a profile figure (`anatomy_profile.lay_out_head`) is built in a separate set of shapes and painted over the same picture
    + Turning a front face far pushes it out of the skull outline and the far side looks cut off. A profile face keeps its features on the outline and avoids this
- (Women and men) The same stages and functions with the body tables swapped
    + The male front has the chest muscles as wide tilted bumps, the abdominals as 3 pairs of small bumps, smaller buttocks
    + Short hair from behind is a hair cap over the skull, an irregular hairline at the nape, the ears and the skin of the nape

## Stage 1 sketch

- The face is written as a centripetal Catmull-Rom curve through control points
    + Hand-placed control points are unevenly spaced, so the centripetal form that does not overshoot is used
- The jawline has 2 segments that bend at the jaw corner
    + `jaw_sharpness` pulls the middle point onto the straight line to control sharpness
- A head turn gives each point a depth value and uses a rotating projection
    + Face surface depth is an ellipsoid approximation (`face_z`)
    + The nose moves further by its protrusion and the far eye narrows by itself
- Each hair section is defined by 2 guide curves, inner and outer
    + Every strand, shadow and highlight interpolates the two guides, so the whole mass shares one flow
    + The sections are `back`, `far` (far side hair), `near` (near side hair) and the fringe locks
- The far side hair lies in front of the face and behind the shoulders, so it is painted masked by the body

## Stage 2 flat colour

- Closed curves are filled at 3 times supersampling and scaled down to remove stair-stepping
- Painting order: background, back hair, body, outfit, face, nose, mouth, eyes, far side hair, near side hair, fringe
    + Painting back to front needs no occlusion computation
- The eyes stack layers in the order of a hand drawing
    + White, lid shade, iris gradient, lower reflected light, iris rim, pupil, lashes, double-lid line, brow, catchlight dots

## Stage 3 shading

- Shadow is computed as a shadow amount field in 0-1, then the style's edge treatment is applied
    + `cel`: a hard edge cut at 0.5
    + `soft`: a blurred continuous edge
    + `grain`: the blurred edge compared with fixed noise and broken into grain
- Two kinds of form shadow
    + (General shapes) the slope of the height made by blurring and inflating the mask is used as the normal (the idea of Johnston, Lumo 2002)
    + (Face) the analytic normals of an ellipsoid. Inflation would darken the jaw and the cheeks equally, which does not suit a face
- Cast shadows: the casting shape's mask is pushed away from the light
    + The chin onto the neck, the fringe onto the forehead, the side hair onto the clothes
- The `soft` style adds per-plane corrections on the face
    + Forehead, cheekbones, nose bridge and chin lighter. Eye sockets, under the cheeks and under the lower lip darker
- Hair shadows are a sum of pointed bands (wedges) following the flow
    + The gloss is a toothed band that finds a fixed height on each strand and alternately pushes it up and down

## Stage 4 inking

- Lines are rendered as strokes whose width changes along their length
    + A width profile that thins at both ends gives the hand-drawn impression
- Line colour depends on the material
    + Skin lines are reddish brown. Hair lines are the darkest step of the hair colour
- A style with `line_scale` 0 leaves out the inking and shows outlines by shading contrast

## Stage 5 finish

- (Anime) warm cast on the light side and cool cast on the other side, glow in bright areas, a light vignette
- (Illustration) paper texture and fine grain
- (Painting) brush-stroke reconstruction (Hertzmann, Painterly Rendering with Curved Brush Strokes of Multiple Sizes, 1998)
    + Layers stack from the largest brush to the smallest
    + In each layer, strokes start only in cells where the canvas differs strongly from a reference blurred to the brush size
    + A stroke carries the colour of its starting point and follows the outline direction (structure tensor)
    + Flat areas use a slanted default sweep direction
    + A focus map (background 0, outfit 0.3, hair 0.4, body 0.5, face 0.75, features 1.0) limits where the small brushes may go
    + Each stroke records its thickness, and raking light shows the relief of the paint

### Other-media styles (`scripts/media.py`)

- An existing style's render (illustration for watercolor and pencil, anime for manga and pixel art) is the base picture, repainted in another medium in the finishing stage
    + A style file inherits its base style's settings through the `base` key and overrides only `finish` and a few values
    + The same finish works on any subject
- (Watercolor, `watercolor`) A bilateral filter forms colour pools and a hand-tremor displacement is added
    + Wet edges where pigment gathers at colour borders. Small bright specks (snowflakes and the like) are found first so no edge rings them
    + Blooms where the wash dried unevenly, grain settling in the paper's pits, cold-press paper texture
- (Pencil, `pencil`) Auto levels turn the darkest area into the densest graphite
    + Over a smudged base tone, hatching layers in different directions are added one by one as the tone darkens (cross-hatching)
    + The render's outlines are found with a black-hat operation and kept as pencil lines
- (Manga, `manga`) Dark areas become ink, light areas paper, mid tones a 45-degree dot screen (the dot radius grows with darkness). Outlines are ink lines
- (Pixel art, `pixel`) Area averaging reduces the picture to a grid (`cells` across). K-means started from brightness quantiles keeps a few colours (`colors`)
    + 4x4 Bayer dithering turns gradients into checkered steps where bands would show. Cells where brightness turns sharply become dark outline cells
    + Nearest-neighbour scaling brings it back to the original size

### Film night (`doomer`)

- Over an anime render, colour is drained (saturation 0.4), contrast is raised to 1.35, and the result is laid on a cold ramp from blue-black to grey
- Only bright, strongly reddish pixels (sodium lamps, lit windows, a cigarette ember, a sunset at the horizon) keep their colour, pushed toward sodium orange
- The darkest few percent are pressed into one tone, crushing the blacks
- An orange glow around the lights, a vignette darkening the corners, and film grain coarser than a pixel and stronger in the shadows
- Building walls (`subject_blocks`) project each pixel back to coordinates on the wall (cm across, cm up) and compute panel joints and the window grid at once with modulo arithmetic. A fixed random number per window picks its light (warm, amber, television blue)

## Defects and the stage that causes them

| Symptom | Stage to check | Fix |
|---|---|---|
| Features look misplaced | `1_sketch` | Height values in `face`, `eyes`, `nose`, `mouth` |
| Fringe covers the eyes | `1_sketch` | Shorten `hair.bangs.length` |
| Neck too long or too short | `1_sketch` | The difference between `body.neck_pit_y` and `face.chin_y` |
| Colours blend into each other | `2_flat` | Widen the value differences in the palette |
| Too much shadow on the face | `3_shaded` | Lower `face_render.form_level` |
| Hair looks flat | `3_shaded` | Raise `hair_render.shadow_wedges`, `light_opacity` |
| Painted face turns mushy | final | Lower the small brush `threshold` in `finish.layers` |
| Painted skin looks rough | final | Raise `finish.glaze` (0-1, how much of the smooth underpainting is laid back over the strokes) |
| Seam lines show on the body | `3_shaded` | Check the form alone with a clay render, then adjust `BLEND` in `anatomy_body.py` or the part's widths |
| Background band between hat and hair | `4_inked` | Move `HAT_LINE` (the line that paints out hair) in `accessories.py` above the hat's lower edge |
| Pattern too fine or too large | `2_flat` | Adjust `pattern.scale`. Portraits have a large head unit, so the same value looks larger |
| Watercolor edges too dark | final | Lower `finish.edge_gain`, `finish.wet_edge` |
| Pencil too grey | final | Raise `finish.gamma` (brightens the mid tones), lower `finish.smudge` |
| Bands show in pixel art | final | Raise `finish.dither`, raise `finish.colors` |
| Spotty shadows on swimwear | `3_shaded` | Raise `CLING_BLUR` in `wardrobe_casual.py` |
| Elbow shoots up at a hand target | `1_sketch` | The target is too close to the shoulder (within the difference of the two bone lengths). Move the target away, also shorten the forearm with `foreshorten`, or change `bend` |
| A hand raised before the face is hidden by hair | final | `front` true on the arm |
| Sleeve of a folded arm covers the hand or breaks on the upper arm | `2_flat` | Arms with a hand target or `front` keep the upper and lower sleeves separately and leave the hand bare. For other arms check the sleeve end by the angles |
| Far shoulder pokes over the clothes in a 3/4 view | `2_flat` | The far arm is treated as behind the torso. If it must come forward, place it with `reach` |
| A hand on the other's shoulder does not show | final | Make the hand's owner a companion and name the hand or forearm in `lift` |
| The sleeve of an arm over the shoulder shows as an angular block by the other's neck | final | `lift` `{"part": "forearm_<side>", "from": 0.7}` lifts only the cuff. `lift_under_head` true |
| In a front group photo, the cuff of an arm around the shoulders stays as a block on the other's shoulder | final | Set `lift` to the hand only (`"hand_<side>"`) and shorten that figure's sleeve to about 1.6 |
| The elbow of a V sign beside the face juts far out from the body | `1_sketch` | Upper arm `foreshorten` 0.45 and `toward` -1 send the upper arm behind the body and keep the elbow near the shoulder |
| A hand on the other's arm is covered by its own sleeve | `1_sketch` | Space the two figures apart to straighten the arm and turn the `hand` angle toward the other |
| The umbrella shaft crosses another face | final | Give the hand target as `at` between the two faces |
| The arm holding the umbrella reads as a block beside the torso | `1_sketch` | Upper arm `foreshorten` 1.0, forearm 0.65, `toward` [0, 1], `bend` "down". Check that the elbow comes to the waist |
| A forearm folded up over its upper arm merges with it into one sleeve block | `4_inked` | When an arm with a hand target or `front` folds more than 120 degrees, the edge of the forearm sleeve is drawn inside the sleeve automatically (a shadow seam in lineless styles). If the line is weak, adjust `FOLD_COS`, `FOLD_LINE_FROM`, `FOLD_SHADE` in `wardrobe.py` |
| A hand swung back shows over a skirt or coat | final | `behind_clothes` true on that arm (automatic for the back arm of `stride`) |
| The back foot floats or the stride is too long when walking toward the viewer | `1_sketch` | Lower `stride.amount` |
| Mouths miss in a kiss or one person's feet float | `1_sketch` | Measure the `mouth` and `soles` points of both figures and match `head_center` x and `horizon_drop` |
| The arm round the other's neck covers one's own face | `1_sketch` | Lower the hand target down the other's back to bring the elbow down (`upper_back` `offset` y 1.0 or more) |
| The arm round the other's neck hides behind one's own neck | final | `front` "arm" on that arm |
| A lying figure floats above the ground | final | Match `lying.ground` to the backdrop's ground height |
