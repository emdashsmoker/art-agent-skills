# Drawing process and engine mapping

## Process map
- Each step of the skill maps to one step of an illustrator's workflow

| Step | Engine modules | Output |
|---|---|---|
| Planning | spec.py | Validated scene spec |
| Construction (proportions, skeleton) | config.py, rig.py | Head-unit proportions, projected 3D landmarks |
| Form (face, hair, body, outfit) | head.py, face.py, hair.py, body.py, musculature.py, hand.py, outfit.py, wardrobe.py, accessories.py | Layer stack (polygons, strokes) |
| Form (views) | backview.py, profile.py | Back anatomy, profile template |
| Form (scene subjects) | still_life.py, props.py, interior.py, landscape.py, city.py, shapes.py | Layer stack and background |
| Form (held props) | handheld.py | Objects placed between palm and fingers, screen light and smoke |
| Line art | renderer.py (line_mask) | Variable-width colored line art, thicker away from the light |
| Coloring | renderer.py (_shade) | Base color, form shading, cast shadows, rim light, highlights |
| Style | styles.py, painterly.py, watercolor.py | Cel, soft, oil, and watercolor processing |
| Finishing | post.py | Glaze, bloom, toning, doomer grade, vignette, grain |

## Construction principles
- Every measure is in head heights H
    + The head coordinate origin is the crown, the body coordinate origin is the neck base (top of the sternum)
- The head outline is the union of the Loomis sphere (cranium) and the jaw curve
    + 3D landmarks are rotated by yaw and pitch and projected orthographically, so a 3/4 view shrinks the far eye, pushes out the far cheekbone, and shifts the jaw on its own
- Eyes, nose, and mouth sit as points on the face cylinder and shorten horizontally with its curvature
- Hair locks are 3D spine curves on a shell over the scalp (cranium radius plus thickness)
    + The width direction is also computed in 3D, so lock widths foreshorten naturally when the head turns
- The body is a union of ribbons (capsules) with a joint skeleton and anatomical width profiles

### Proportion canon (adult woman, about 7 heads)

| Item | Value (H) |
|---|---|
| Eye width | 0.18 |
| Eye line height | 0.60 from the crown |
| Shoulder half width | about 0.72 |
| Neck base | 1.30 from the crown |
| Waist | 1.45 from the neck base |
| Widest hip | 2.10 from the neck base |
| Knee | 3.88 from the neck base |
| Ankle | 5.32 from the neck base |

### Male proportion differences (adult man)

| Item | Compared to female |
|---|---|
| Shoulder joint half width | 0.605 → 0.800, elbows move out by 60% of that shift, wrists by 50% |
| Neck base half width | 0.176 → 0.235 |
| Torso | Trapezius slope, lats below the armpits, inverted triangle with a narrow waist |
| Limb widths | Deltoid caps, biceps bulge, upper forearm bulge, outer thigh curve, calf bulge |
| Hands and feet | 1.22x |
| Leg spacing | Knee and ankle horizontal positions 1.22x |
| Face | 1.10x taller, angular jaw (square), thin lips, no lashes, thick low brows |

## Hand and pose principles
- Hands are a 3D skeleton: a palm block, 4 fingers × 3 segments, a 3-segment thumb
    + A gesture is a set of per-segment bend angles and finger spread angles
    + The finger direction and the palm normal rotate the whole hand before projection
    + Fingers are capsules, so they keep their thickness from any direction and only their length foreshortens
    + Per-finger layers are drawn in depth order, so front fingers hide back fingers
- 3 arm placements set the draw order
    + front: over the torso garment, under the sleeves (cuffs cover the wrists)
    + behind: behind the torso
    + raised: over the hair and face (waving)
- Contrapposto tilts the pelvis with a vertical shear below the waist
    + A rotation would swing the hem and legs sideways like a pendulum, so a shear is used
- Gesture arm poses set elbow and wrist targets in body coordinates
    + Arms crossed overlaps both forearms under the bust
    + Chin rest and hair tuck raise one hand beside the face in the raised placement
    + Hands behind head draws the arms before the back hair, so the hair flows over the elbows
- Full-body postures pair a leg stance template with an arm pose
    + Walking uses a front-back stride and the opposite arm swing
    + Leaning tilts the upper body, puts the hands behind the back, and hides one foot against the wall behind the other leg
    + Sitting draws a round knee cap at the end of the thighs foreshortened toward the viewer to show depth
    + A seated figure is shorter, so the framing scale is recomputed to fill the frame
    + Chair, stool, and bed are box seats at knee height drawn behind the figure
- Lying rotates the whole rig 90 degrees (orient) and lays the standing template down as is
    + The rotation is the last step of the head and body coordinate transforms, so face, hair, and outfit all rotate together
    + A shadow of the figure silhouette pushed off at an angle on the bed sheet grounds the figure

## Figure principles
- The figure is set by three sections of the torso silhouette
    + How fast it narrows below the ribs (slow narrowing widens the waist and makes the belly look forward)
    + Minimum waist width and height
    + Widest hip width (the thigh joint spacing widens with it)
- The bust is a skin layer with sphere normals for 3D shading, with no outline and a blurred edge that blends into the chest plate
- Over clothing, volume shows as a shadow under the bust, light on the upper slope, and folds pulled sideways
- Bikini cups, tube tops, and the crease under the bust follow the bust size of the figure
- The head has anime proportions, so the torso needs a waist to hip contrast for head and body to read as one character
- The bust is a nearly round lower hemisphere plus an upper slope that eases into the chest plate
    + The normals are spherical below the center and flatten gradually above it, like a droplet (a plain sphere leaves a dark ring on the upper slope)
    + The sphere radius is 1.08x the outline, so the lower edge turns away and makes a crescent shadow
    + The round lower outline and the shadow cast on the ribcage below it confirm the round mass
- Over clothing the same normals reshade the fabric, so the crescent shadow appears on the cloth
    + The lower outline is inked over the fabric
    + A cleavage shadow separates the two masses
    + Shading strength scales with the vertical bust radius
- The lower band of a triangle bikini cup follows the outer arc of the bust (the cup reads as rounded)
- The 4 bust sizes change the bust center and radius together (larger busts sit a little lower and further out)
- The bust is in front of the arms, so it joins the body silhouette and is removed from the arm mask
    + From large the outer curve passes the ribcage line and shows in front of the arm (side volume)
    + The top's bodice also takes the bust shape, and sleeves leave the bust area empty
    + The outer ink runs from under the bust along the outside up toward the armpit
- The bust center sits in front of the ribcage surface (depth 0.25 plus 0.6 of the radius), so turning the body brings the far side past the outline
- Necklines, armholes, and front openings project at neck silhouette depth above the neck base and at bust surface depth below it, so they stay aligned when the body turns
- The pelvis gets only soft dome-normal shading (a cel boundary would leave blotches on the hips)

## Male skeleton principles
- Each muscle mass is a skin layer with spheroid normals (crisp cel shadows plus soft shading express the muscles)
    + Pectorals are plates under the collarbones with the dome center raised, giving a shadow band at the lower edge
    + Torso: trapezius, 8-part rectus abdominis, 3-slip serratus, external obliques
    + Arms: deltoids, biceps, triceps, forearms (aligned with the arm bones, so they follow any pose)
    + Legs: outer quadriceps, inner teardrop, calves (flat domes and low thresholds avoid blotches)
- The arms hang slightly away from the body so the V of the lats shows under the armpits
- Ink lines go only where a painter would actually draw a boundary
    + Linea alba, rectus abdominis segments and outer edges, oblique edges, front deltoid groove, lower biceps edge, sternocleidomastoid, Adam's apple
    + Inner thigh teardrop muscle, outer thigh curve, inner calf edge
- Muscle definition (body.muscle) scales the opacity of the muscle skin layers, ab shadows, muscle lines, pectoral plates, back muscles, and pectoral shading over clothing together
    + Defaults per figure slim 0.10, balanced 0.30, athletic 0.50 (every man was 1.0 up to v9)
    + The silhouette (shoulder width, limb thickness) comes from the figure; muscle definition changes only surface detail
- Pectoral shading over clothing is weakened to 0.45x times the muscle definition, and sleeve ease is halved so sleeves do not balloon on thick arms
- Necklines, collars, hood linings, and armholes deform automatically with the neck thickness ratio and the shoulder shift
- Loose shorts subtract a wedge mask between the legs so they read as two legs (without it they look like a skirt)
- The front panel of swim and underwear bottoms is a smooth surface, and the crotch shape is not emphasized

## Face detail principles
- Face length stretches the jaw outline vertically from where the jaw starts; nose and mouth move proportionally from the eye line
- 3 noses: small is 1 stroke of bridge shadow, button adds a round tip reflection, defined adds nostril wings and bridge lines
- 3 lip types: thin draws only the mouth line, natural adds a lower lip color shape, full adds a Cupid's bow upper lip and gloss
- Lashes are the thickness of the upper lid line and the number of flicks at the outer corner; none draws only the lid line
- Short hair sweeps crown locks from roots on the scalp shell toward the part to break the silhouette (so it does not look like a helmet)

## View principles
- (Back view) the same silhouette with only the surface information swapped
    + Front-only layers (buttons, ties, pockets, bust volume shading) are filtered out by name
    + Spine groove, shoulder blades, lower back dimples, male trapezius and lats, and glutes are dome-normal skin layers
    + Bottom fabric takes sphere-normal shading over the glutes, so the round form shows
    + Forearm front and back placements are swapped compared to the front view
    + Hands in the behind pose gather behind the waist
    + Back hair is drawn over the outfit, on the back
    + A bright reflected light on the back hair prevents a dark mass
    + The face is the front head, turned to look back in the head.yaw direction
- (Profile) a dedicated silhouette template, separate from the front rig
    + 1 face outline holds forehead, nose, lips, and chin
    + Eyes are drawn as side-view eyes
    + Hair is a mass whose cranium arc, pointed bang tips, and hairline beside the face run as 1 outline, plus strand lines
    + Torso depth is about 0.55-0.7x of the front width, so it does not look thin as a stick
    + The bust is a droplet volume merged into the body outline
    + Tops are a convex hull that falls straight down from the bust point
    + The neckline is a slanted line joining back neck height and front neck height across the neck depth
    + Outfits generalize to a body band between neckline and hem, sleeves, straps, and flare

## Outfit form principles
- Fitted dresses and pencil skirts wrap the convex hull of hips and thighs, removing the dip between the legs
- A shirt over slacks or a pencil skirt is cut at the waistline and drawn tucked in
- Long tops past the hips are drape polygons that fall straight from the pelvis
- Skirts and long top hems in a seated pose are cut above the knee and drawn resting on the thighs
- Satin (slip dress) has a narrow strong highlight, knit and cotton a wide weak highlight
- Arms with the elbow above the shoulder (hands behind head, hair tuck, arm over the shoulder) are drawn with the sleeve ridden up
    + The upper arm sleeve goes under the bodice, so only the part outside the bodice along the arm shows
    + The bodice is not cut by that arm, so the area under the armpit stays covered by the bodice
    + A long sleeve that reaches the wrist stays over the forearm skin
- The rash guard is cropped over a bikini for women and reaches the hips for men
- Where the bust shows in front of the arm only its round lower mass is used (the gentle upper slope merges into the chest plate)

## Scene compositing principles
- The background scene renders first and the character renders over it
- Scene line art is erased where the character covers it (background lines do not show through the character)
- The character takes the scene's light direction as is, plus a multiply tint and rim light in the scene colors at sunset and night
- Full framing grounds the figure with a shadow under the feet pushed away from the light
- (wide) the scene stays as it is and only the figure becomes small
    + The ground line is fixed at about 83% of the canvas height, so seated and rescaled figures stand on the same ground
    + A single figure can also stand to one side of the scene with place.x for an establishing shot where the scene leads

## Held prop principles
- (Cigarette) drawn behind the finger layers and in front of the palm layer
    + The cigarette passes under the curled fingers and sticks out of the hand, so it reads as held between the fingers
- (Can, phone) the back of the hand faces the viewer, so the whole hand is drawn in front of the object
    + The object's center sits under the knuckles, so the first finger segments cross the object's front
    + The second and third segments bend away from the viewer at the far edge of the object and show as rounded knuckles
    + Straight fingers running past the edge look like they pierce the object; fingers cut straight at the edge look severed
    + The can uses real proportions (height 0.50H, diameter 0.28H) and the hand sits above the hoodie pocket
    + The palm supports the phone's back from below and the top of the phone shows above the hand; the thumb is on the screen side (away from the viewer) and is drawn behind the phone
    + Hoodie drawstrings and collars are erased where the holding hand and the object are, so these stay in front (the cuff stays over the wrist)
- The holding arm has fixed elbow, wrist, and palm directions per object and moves out by the width of the broader male shoulders
- Effects the object gives off, such as light and smoke, are drawn last over the whole figure
    + Phone screen light is a small screen-blend ellipse around the hand (a large one looks like a white blot on the chest)
    + Cigarette smoke is a wavy band that starts at the ember, widens, fades, and drifts away from the body without riding up the sleeve

## Mood principles
- A mood lays 3 bundles (scene spec, character background, character defaults) under the user's spec, so user values always win
- (doomer grade) desaturates, multiplies the shadows with navy, screens the highlights with a pale grey-blue, then fades the darks toward a navy grey
    + Only lit windows and street lights stay warm, so the solitude of an empty night street reads
- (Power lines) utility poles with cross-arms on both sides of the street, sagging catenary wires, and wires across the street build a residential night street hung with wires
- (Night landscape) moon and stars, moonlight, dark sky and mountains, blue-grey clouds and snow
- (Beanie) the folded cuff and ribs follow the head sphere, and the crown locks are left out so no hair pokes through the hat

## Two-shot and group principles
- (Placement) neighbor gaps and height differences are computed in head heights H
    + The tallest figure's head top is aligned to the framing guide, and all feet share one ground
    + By default heads and profiles face the group center, so the relationship reads first
    + From 3 people the canvas widens, and groups past 4096px shrink the figures to fit
- (Multiple rows) rows further back are smaller (0.93x per row) and stand on higher ground (0.55 head heights per row) to read as further away
    + A back row with as many people as the front row is staggered by half a gap, so faces show between front-row heads
    + After staggering the whole group is re-centered so the outer figures are not cut off
    + Rows are drawn from back to front
- (Draw order) each figure gets its own render pass, drawn from the back figure to the front figure
    + Layer names are mask keys within a pass, so separate passes avoid name clashes
    + Chairs, beds, and ground shadows are drawn before the figure passes so they do not cover another figure
    + A front figure's coverage erases the back figure's line art
- (Front-view sitting) a shadow starts at the knee and fades downward on the shins just below the knees
    + It is the cue that the foreshortened thighs come toward the viewer, which tells the pose apart from standing
- (Hand holding) both arms are solved with 2-joint inverse kinematics so the wrists meet between the figures
    + The hand height is the lower of the heights the nearly straight arms can reach
    + The front hand is a fist wrapping the fingers of the back hand, so it reads as holding hands
- (Arm over the shoulder) the elbow is fixed behind the partner's neck on the far side and the wrist at the far shoulder tip
    + The figure with the arm is drawn behind, so the upper arm passes behind the partner's head and neck
    + A reveal pass redraws only the forearm and hand area after the partner's pass to show the arm over the shoulder
    + The partner's neck column and face are subtracted from the reveal area, giving the edge where the forearm comes out from behind the neck

## Bare skin principles
- Legs and torso merge into one silhouette, so no outline crosses the thighs
- Revealing outfits enlarge the skin bevel radius, so the torso and limbs shade like cylinders
- The forearm outline is left out where it overlaps the upper arm (no elbow seam)
- 4 skin form cues are drawn on a layer under the outfit: navel, abdominal midline, groin lines, crease and shadow under the bust
    + Whatever the outfit covers is hidden automatically, so they always apply regardless of outfit
- Bikini cups shade with sphere normals around the bust center, with a small shadow on the skin under the cup
- Straps and tube tops are clipped by the torso mask and cut by the upper arm mask, so they pass behind the arms

## Scene principles
- (Still life) vases, bottles, and cups are solids of revolution, fruits are spheroids
    + Exact normals come from the silhouette slope, so the terminator, core shadow, and highlight follow the form
    + Each object casts a floor shadow and a contact shadow, plus an offset shadow on the wall
    + Table bounce light as a rim light from below seats the objects on the surface
- (Landscape) aerial perspective: further ranges blend into the horizon sky color with weaker lines and contrast
    + Ridgelines are 1D fractals (midpoint displacement), shading is the sum of mask bevel normals and noise gradients
    + Snow settles only above an absolute altitude, the lake is the mountain polygons flipped at the water line
    + Cumulus clouds are clusters of round masses with flat bottoms, shaded like solids
- (City) 3D coordinates in meters are projected with a pinhole camera (eye height 1.6m)
    + Every window, curb, and street light converges on the same vanishing point
    + Building faces have exact plane normals, so the lit side and the shaded side come from the lighting
    + Distant buildings blend into the haze color; at night windows and street lights glow with halation
- (Modern objects) objects such as laptop, monitor, and keyboard are assemblies of box, rod, dome, and revolved parts
    + All parts use the same oblique orthographic projection (depth times 0.30 added to the height axis), so top slants stay consistent
    + Box faces are drawn only when their normal has a positive component toward the screen, removing hidden faces
    + Screens are abstract interfaces made of a theme gradient, windows, and text lines
    + Still life shadows are computed from the whole object silhouette
- (Interior) floor, walls, windows, and furniture sit in depth order on a stage with the same oblique projection
    + The stage scale for a character background comes from the character's head size
    + The stage is 0.62x smaller than the character to fake lens depth
    + The room palette (wall, floor, accent) and the time-of-day tint also apply to the character

## Coloring principles
- Form shading: soft shading added on top of the cel steps
    + Faces turned to the front keep the base color, faces turned away from the light darken gradually, faces turned toward it brighten slightly
    + Applied to the bust, pelvis, and muscle masses, together with skin specular, so they read as round surfaces
- Form shadows: a mask distance field builds a round bevel height and its gradient gives pseudo normals (Johnston 2002, Lumo)
    + Only the edges slope and the inside stays flat, which gives the edge shading typical of anime
- Cast shadows: the occluding layer's mask shifted away from the light
    + Bangs on the forehead, the chin on the neck, hair on clothing
    + Only layers higher in the stack cast shadows
- Shadow colors lower value, raise saturation, and shift hue at the same time
    + Skin shifts toward red, hair and outfits toward blue-violet
    + Nearly unsaturated colors such as white and grey get cool grey-blue shadows
- Line color is a darker color of the same family as the adjacent fill (colored line art)
- Lines are thicker on the side away from the light, and hair lock lines vanish toward the roots

## Style principles
- (anime_cel) crisp 2-step shading, bold colored line art, diagonal hatching on the cheeks
- (soft_illust) soft-edged shading, thin light line art, warm glaze, bloom, saturation boost
- (painterly) Hertzmann (1998) multi-size curved brush strokes
    + From large to small brushes, strokes go only where the grid error between canvas and reference is large
    + Strokes curve along the direction perpendicular to the value gradient (isophotes)
    + The face area gets a higher error weight and is repainted with small brushes
    + A distant figure whose face is under 6% of the canvas height is repainted entirely with the finishing brush (large brushes smear hands and face into the street)
    + Eyes and mouth partly restore the rendered original (so small brushes do not smear the mouth and erase the expression), line art is restated at underdrawing strength
    + Bristle texture is line integral convolution (LIC) over a direction field, impasto is relief lighting of a stroke height buffer
- (watercolor) Bousseau (2006) pigment density model C' = C - (C - C²)(d - 1)
    + The density d is the sum of edge pooling, low-frequency blotches, high-frequency granulation, and paper grain
    + Noise displacement wobbles the edges, and blooms apply in random areas
    + plain and gradient backgrounds fade into bare paper away from the character; scene backgrounds stay without fading
    + Dark passages get more pigment (glazing, so a night sky does not float at mid grey)
    + A night picture with mean value 0.20 or lower is painted edge to edge without paper fade (gradual transition up to 0.30)
    + Eyes, brows, nose, mouth, and lips are kept out of blooms (a bloom smears the iris into a black blot)
    + Edge pooling is computed on a median-filtered image without specks such as stars and glints (no black rings around the specks)
    + Line art takes a pencil tone

## Defect table

| Symptom | Cause | Fix |
|---|---|---|
| Pointed hook on the face outline | Bang tip overlaps the far cheek outline | Reduce yaw or change bangs |
| Dark rectangle outside the shoulder | Back hair exposed in a 3/4 view | Reduce yaw, reduce hair.length, consider style bob |
| Fingers spread awkwardly | Gesture and hand direction combination | Change hands to relaxed or flat |
| Waving hand covers the hair | raised placement draws over the hair | Turn head.yaw away from the hand |
| Still life objects sink into each other | Same x and depth | x gap 0.1 or more, depth difference 0.15 or more |
| Landscape composition does not work | Ridges and clouds come from the seed | Change only canvas.seed |
| City street is flat and symmetric | camera_x 0 | Set camera_x near -2 or 2 |
| Belly does not show under a crop top | Bottom is a_line_skirt (high waistline) | Change bottom to jeans |
| Bikini bottom looks small | bust framing does not draw bottoms | Change framing to waist or full |
| Torso looks flat | figure slim | Change figure to balanced or curvy |
| Figure floats over a scene background | bust and waist framing have no ground shadow | Use full framing or match the background time to the character lighting |
| Smudged face in oil | Color mixing at the large brush stage | Change the seed, use quality final |
| Watercolor looks like cel | Solid background, small painted area | Use background gradient or sky |
| Murky shadows on shirts and white clothes | Achromatic shadows | Add a slight tint to outfit.color (#F4F2EE and so on) |
| Full-body figure is small | 4:5 canvas | Omit canvas (automatic 960x1600) or give a portrait canvas |
| Hair highlight looks like a headband | Ring too wide | Change the seed (moves the ring breaks) |
| Back view face sticks frontally to the back of the body | view back with head.yaw 0 | head.yaw 25-35 to look back over the shoulder |
| Profile pose does not change | pose not supported in view side | Choose relaxed, walk, or sit |
| Seated figure on an empty background | plain or gradient background | Use an office, cafe, or bedroom background |
| Lying figure is cut off | Portrait canvas given | Omit canvas (automatic 1600x1000) |
| Desk objects look piled up | Large objects at a front depth | monitor and laptop at depth 0.3 or less, small objects at 0.5 or more |
| Two-shot figure touches the canvas edge | Broad shoulders of 2 men | Omit canvas (automatic size) or narrow the gap with place.x |
| Group figures look small | Many people pass the 4096px maximum width and shrink | Fewer people, use framing waist |
| Contact pose error (3 or more people) | Contact is for 2 people only | Use pair.contact none |
| Male abs and arm muscles too strong | body.muscle too high | Set body.muscle to 0.3 or less |
| Front-view sitting looks like standing | From the front the thighs foreshorten toward the viewer and almost vanish | Sit in view side (for 2 people keep knee room with place.x) |
| Far sleeve dents round on a 3/4 turned top | The far side of the bust shows in front of the arm | body.yaw 12 or less, or a sleeveless top (camisole, tank top) |
| Only bare skin shows in a closeup | Neckline of an off-shoulder or tube top is below the frame | Use a top with a high neckline in closeups, such as a shirt, knit, or hoodie |
| Two-shot figures overlap too much | place.x gap too small | Omit place.x (automatic spacing) |
| Held hands cut off at the bottom | Hand height in waist framing is below the hips | Use framing full |
| Arm over the shoulder does not show | The lead figure's view is not front | view front for both figures |
| Two-shot contact pose error | arms_crossed, sit, or lie pose | Change that figure's pose to relaxed or similar |
| Back-row faces hidden by the front row | More people in the back row than in the front | Adjust pair.rows or use place.row to keep the back row no larger than the front |
| Held object does not show | view back or side | hold draws only in view front |
| Fingers pierce the held object | Finger length and object position do not match | Put the object's center under the knuckles and wrap it with the grip gesture (extending.md, adding held props) |
| Looking at the phone but the gaze goes to the viewer | gaze down moves the iris only a little | head.pitch 14-18, eyes.gaze [x, 1.2], eyes.openness 0.45-0.5 |
| Distant figure sinks into the scene | Dark outfit over a dark background | Move place.x in front of a street light pool or a lit window |
| Doomer picture looks murky grey | Light background colors take the desaturating grade | Use navy and dark grey families for background and outfit colors |

## Limits
- 2 character templates (adult woman, adult man) and 3 views: front (up to about 35 degrees to the side), back, profile
- Only combinations of 6 hand gestures, 11 arm poses, and 7 leg stances
- Profiles support only the relaxed, walk, and sit postures
- Profile outfits leave out front details (buttons, prints)
- Sitting is 1 front-facing posture (depth shown by a shadow under the knees), lying is 1 posture seen from above
- Character background scenes: landscape, city street, beach, 5 interiors, bed
- A single figure is placed from the screen center, place.x sets its horizontal position
- Two-shots and groups use waist, full, and wide framing; multiple rows stand in perspective on one ground (stepped risers and a seated front row with a standing back row are not supported)
- Held props: a phone, a canned drink, or a cigarette, 1 in one hand, front view only
- 1 mood preset, doomer
- Contact for 2 people: hand holding (front, back view) and arm over the shoulder (front), 2 kinds
- Shadows cast between figures and depth tests for hands hidden by another figure are not supported
- Scene elements come from fixed lists (18 still life objects, 1 landscape composition, 1 city street composition, 5 interior compositions)
- Realistic depiction (photorealism) is out of scope
