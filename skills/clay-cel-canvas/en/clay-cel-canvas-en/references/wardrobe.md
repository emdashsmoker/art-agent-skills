# Clothes, poses, places

How to dress the 3-D mannequin (the 3-D mannequin in `references/figure.md`), pose it and stand it in a place. Values were verified on the 15 single and 3 two-person combinations in `examples/outfits.py`.

## Contents

- Structure
- Pose presets
- Camera framing
- Principles of making clothes
- Clothes list
- Skirts and dresses
- Wind
- Two-shots
- Places
- Combination examples

## Structure

| Module | What it does |
|---|---|
| `atelier.staging` | 10 pose presets, a camera fitted to shot and direction (`pose_for`, `frame`) |
| `atelier.wardrobe` | Clothes that follow the body and tools that attach clothes to the body (`bikini`, `suit`, `hem`, `cut_leg`, `patch`, `strap` and others) |
| `atelier.drape` | Cloth that falls away from the body: skirts, dresses, scarves, wind (`Flare`, `flared_skirt`, `sundress` and others) |
| `atelier.turn` | Depth model that turns a front-drawn head up to three-quarter view (head turning in `references/figure.md`) |
| `examples/scenes.py` | 9 places: backdrop, floor, furniture colours, post-painting |
| `examples/outfits.py` | Combination example that draws one picture from a choice of sex, clothes, pose, place and shot. Includes two-person combinations |

## Pose presets

`pose_for(name, physique, bust)` stretches a pose written for the female mannequin to the build's leg length. Both sexes use the same names.

| Name | Pose | Support needed |
|---|---|---|
| `standing` | Weight on one leg, arms down | None |
| `hand_on_hip` | One hand on the hip, elbow out | None |
| `walking` | Front foot on the heel, back foot on the toes. Arms and chest turn against the legs | None |
| `arms_crossed` | Arms folded. Each hand tucked behind the opposite upper arm | None |
| `seated_chair` | Sitting upright on a chair, hands on the thighs | 2 `seat` (seat, backrest) |
| `leaning_wall` | Back against a wall, one foot flat on the wall | `wall` (a 1 m wide pillar) |
| `seated_ground` | Sitting on the ground, knees up, arms propped behind | `ground` |
| `reclining` | Lying on the side on a bed, one hand behind the head | `bed` |
| `seated_crossed` | Sitting on a chair, right leg crossed over the left knee. Left hand on the crossed knee, right hand on the lap | 2 `seat` (seat, backrest) |
| `waving` | Standing, right hand raised beside the head and waving. Palm toward the viewer | None |

- The returned `Staging` has `pose`, `supports`, `hand_at`, `hand_behind_head`
    + `supports` is a list of `(role, shape)`. The place sets the colours
- Write a new pose in metres for the female build
    + The floor is z = 0; the figure faces -y
    + Afterwards check that `strain` from `build()` is empty for both sexes
- When crossing legs, bring the upper leg's shin forward of the lower shin
    + With both shins at the same depth the calves bury into each other
- Folded arms need the elbows forward
    + With the elbows at the sides the forearms jut toward the viewer and look like they carry a box

## Camera framing

`frame(marks, physique, shot, azimuth, elevation, distance, aspect, margin)` places the camera for a shot.

| Shot | Lower edge |
|---|---|
| `full` | 10 cm below the ankles |
| `knee` | 6 cm below the knees |
| `waist` | 6 cm below the pelvis |
| `bust` | 6 cm below the chest |

- The upper edge is the crown of the anime head to be drawn (a head 1.1 times the skull)
- `azimuth` is the angle round the figure
    + Positive shows more of the figure's left side
    + 20-35 degrees is a three-quarter view. The head turns by the same angle automatically
- `elevation` defaults to near eye level (5 degrees)
    + A low camera makes the figure look large and strong
- Reclining poses use a landscape frame (`aspect` around 0.7) and a wide margin (`margin` 0.12)

## Principles of making clothes

One garment is made in 4 steps: shell, cut, add, paint.

### Shell

`dress(scene, marks, group, regions, thickness, smooth)` grows body regions by a thickness.

| Garment | Thickness (m) | Constant |
|---|---|---|
| Swimwear, innerwear | 0.004 | `FIT` |
| Tee, jeans, shorts | 0.008 | `SNUG` |
| Suit jacket | 0.012 | `JACKET` |
| Hoodie | 0.018 | |

- `smooth` is about 0.012. Larger values add volume at each melt and the garment puffs up
- Region names: `neck`, `chest`, `breast`, `abdomen`, `pelvis`, `shoulder` (deltoid), `upper_arm`, `forearm`, `hand`, `thigh`, `shin`, `foot`
- `side=1` (left) or `side=-1` (right) picks the limbs of one side
- Do not make a trouser leg as a separate group
    + A separate leg does not melt into the hips, and its hip end swells like a ball
    + Grow pelvis and both legs as one group and cut each leg with `cut_leg()`

### Cut

| Tool | Where it is used |
|---|---|
| `hem(scene, group, point, kept)` | A straight cut with a plane. Hems, waistlines |
| `cut_leg(scene, group, marks, name, at, keep_upper)` | Cuts one leg only and leaves the other. `at` is 0 at the hip, 1 at the knee, 2 at the ankle |
| `keep_polygon(scene, group, origin, frame, corners)` | Keeps only a convex polygon seen from the front. Triangle bikini cups |
| `cut_wedge(scene, group, origin, frame, apex, left, right)` | Carves a V opening from an apex, front only. Jacket fronts, V necklines |
| `scene.carve(Ellipsoid(...), group)` | Round necklines, armholes |

- Carve away everything above the neck root for a neckline
    + Carving only the front leaves a ring of cloth round the neck with a hole under it
- Cutting planes (`HalfSpace`) and overlaps (`Intersection`) are endless forms. Use them for carving only

### Add

| Tool | Where it is used |
|---|---|
| `onto(shapes, points, offset)` | Moves points onto the body surface at `offset` from it |
| `strap(shapes, points, lift)` | A strap path: fill points every 8 mm, attach them and smooth. Gaps that appear under a ridge are filled again. Shoulder straps, halter straps |
| `Skin(scene)` | The skin surface melted exactly as rendered. Put it in the forms list, as in `strap([Skin(scene)], ...)` |
| `Surface(marks, regions)` | A surface where only some regions are melted the same way as rendering. Used to wrap a torso band without the arms |
| `around(shapes, centre, axis, front, offset)` | Ring of points wrapping the body round an axis. Waistbands, cuffs, stocking tops |
| `rod(scene, group, points, radius)` | A rod joining points. Strings, straps, bands, collars |
| `patch(scene, group, marks, regions, thickness, smooth, origin, frame, corners)` | One layer of cloth laid over a garment. Lapels, ties, pockets |

- Place straps with `strap([Skin(scene)], ...)`
    + The body forms melt into each other, so the real skin is up to 1 cm outside the forms
    + A strap attached to the form surface sinks into the skin and looks broken near the collarbone
    + Attaching only the guide points lets the straight runs between them dive under the curve. `strap()` fills points densely before attaching
    + A straight run under a ridge, such as over the shoulder, splits onto the front and back faces and leaves a 9 cm gap
    + `strap()` adds a point in the middle of the gap. It lifts the point by a third of the gap length, then attaches it
    + Lift it higher and the point lands on the neck
- Wrap torso bands on `Surface(marks, regions)` (`_band(..., melted=True)`)
    + A band wrapped on the original forms sinks 1-16 mm into the melted skin
    + Wrapped on `Skin(scene)`, it walks in from outside and hits the arm beside the torso first
    + Underband: `CHEST_BAND` (chest, breast, abdomen). Hip string and panty waistband: `HIP_BAND` (pelvis, abdomen, thigh)
- Bra shoulder straps run down to underband height on the back and meet the band
- A bikini underband goes all the way round. It passes the lower corners of the cups and joins in the middle
- Grow torso garments to the pelvis region, then cut at the waist
    + The skin's waist is a surface melted from belly and pelvis, so a garment grown only to the belly sinks into the skin at the waist
- Make sleeves as straight rods and grow the deltoid region with them
    + A sleeve grown from the arm shows the muscles and looks like a bodybuilder's
    + Leave out the deltoid and skin shows at the shoulder seam
- Lay ties, lapels and pockets with `patch()`
    + The garment surface is swollen a little by melting. A rod placed at a distance measured from the original body sinks into the garment
    + `patch()` grows a few more mm the same way as the garment beneath, so it lies on top over any curve
- Make loose garments fall straight by melting a rounded box (`RoundBox`) into the torso
    + An ellipsoid narrows toward the hem and becomes a shield shape
    + Carve the forearm and hand shapes out of the garment so the arms do not sink into it (folded arms, hands near a pocket)

### Paint

A clothes function returns a list of things to paint. A `(group, colour, shadow colour)` tuple is painted with `sculpt.paint`. The functions below make painting functions that run after rendering.

| Function | Effect |
|---|---|
| `lace(groups, colour, tint, skin)` | Paints the cloth, then lets skin show through a fine hole pattern. Edges get a solid border |
| `sheer(groups, colour, skin, skin_shadow)` | Thin stockings. The leg shows through in the middle; edges and shade are dark |
| `seam(points, colour, width)` | Stitch line on a surface. Sections hidden behind something are skipped |

## Clothes list

| Function | Parts | Build |
|---|---|---|
| `bikini(scene, marks)` | Triangle cups, halter strings, under strings, low-rise bottom | Female |
| `innerwear(scene, marks, skin)` | Moulded-cup bra, shoulder straps, underband, high-cut briefs, thigh-high stockings | Female |
| `crop_top(scene, marks)` | Sleeveless, hem under the chest, round neckline | Both |
| `hot_pants(scene, marks)` | Hem at 22% down the thigh, rolled cuff, button, stitching | Both |
| `tee(scene, marks, physique)` | Short sleeves, crew neck, hem tucked into the trousers | Both |
| `jeans(scene, marks)` | Slim fit, ankle hem, front pockets and side-seam stitching, button | Both |
| `shirt(scene, marks, colour, tie, sleeves, physique)` | Shirt body tucked into the trousers, collar, tie or open collar. With `sleeves`, sleeves (0.45 short, 1.9 long) | Both |
| `suit(scene, marks, physique, ...)` | Shirt, one-button jacket, peak lapels, straight sleeves, suit trousers, belt | Both |
| `hoodie(scene, marks, physique, long)` | Body box, hood down, strings, kangaroo pocket, ribbed hem and cuffs. `long=True` is an oversized fit reaching the thighs | Both |
| `swim_trunks(scene, marks)` | Mid-thigh length, drawstring, side stripe | Both |
| `shoes(scene, marks, pose, physique, kind)` | `oxford`, `sneaker`, `flat`, `dark_sneaker` | Both |

- When one garment goes over another close-fitting one, give them different thicknesses
    + Two garments of the same thickness swap front and back per pixel and blotch
    + A tee tucked into trousers is 2 mm thinner than the trousers

## Skirts and dresses

`atelier.drape`. A shell grown from the body cannot make cloth that stands off and spreads from it. A skirt is an open shell (`Flare`) that widens from the waist to the hem.

- The skirt shape has 3 sections
    + Waist: 4 mm off the skin (`WAIST_EASE`). Wider, the waist opening looks like a basket rim
    + From the waist to the widest hip line (2 cm below the hip joints): it follows the hips down
    + Below that: it flares straight by `flare` (metres wider per metre) (A-line). It never comes closer than 1.4 cm to the body
- Radii are kept in a table of 49 heights by 72 directions (`body_profile`, `flare_profile`)
    + At each height measure the melted skin's girth and join the two legs with a convex hull. The cloth does not dive between the legs
    + The skirt never narrows going down. Cloth caught on the hips does not curl in below them
    + In a walking pose the skirt widens by itself with the stride
- Folds start a little above the hip line and deepen toward the hem
    + Soft folds vary a little in spacing and depth round the girth (`FOLD_JITTER`, `FOLD_SWELL`)
    + Pleats are an even, angular wave
- Where hands and forearms touch, the skirt pulls in (`obstacles`)
    + Without it a hand lowered at the side sinks into the skirt
    + It never pulls in past just above the skin (`DENT_MARGIN`). Further in, a hole-like dent appears under the hand
- A skirt worn over a tucked-in top gets waist room equal to the top's thickness (`ease`, 1.4 cm over a tee)
    + Without the room the top pokes out below the skirt waist
- In seated or reclining poses (thighs tilted more than 50 degrees from vertical) `flared_skirt()` becomes a tube skirt
    + The tube skirt grows hips and thighs and joins the two legs with a rod to cover the tops of the knees
    + With crossed legs or raised knees the skirt rides up to the knees and is cut per leg
    + Then a flat ellipsoid of cloth joins the two legs (`_web`). A round rod balloons when the legs part, and cutting both legs with one plane bunches the cloth at the knees

| Function | Shape |
|---|---|
| `flared_skirt(scene, marks, length, flare, folds, depth, pleats, wind, ease)` | A-line skirt that follows the hips down from the waist, then flares. Default length 48 cm |
| `pleated_skirt(scene, marks, length, wind, ease)` | 22 knife pleats, 40 cm |
| `mini_skirt(scene, marks, wind)` | 30 cm |
| `tube_skirt(scene, marks, at, ease)` | Skirt that follows the body. `at` is the hem position (0 hip, 1 knee, 2 ankle) |
| `pencil_skirt(scene, marks)` | Tube skirt to just above the knees |
| `sundress(scene, marks, length, wind)` | Strap dress: bodice cut straight above the chest, thin shoulder straps, a skirt flaring from the waist |
| `sheath_dress(scene, marks)` | Close-fitting knee-length dress. No straps |
| `scarf(scene, marks, wind, length, width)` | Cloth wound twice round the neck, a knot in front, 2 tails. Without wind the tails hang straight in front of the chest |

- Dress bodice and skirt meet at waist height (0.165 m from the pelvis)

### Scarf

- The cloth wound round the neck is 2 thick loops
    + They follow the neck column and sit lower in front
    + Their sides are lifted where they meet the shoulder slope. Up to half their thickness is left pressed into the shoulder (`SCARF_SQUASH`)
    + Lifted all the way, the loop sides rise above the chin
- The tails are flat bands (`Ribbon`)
    + Sweep thin boxes along a smooth path. Chained ellipsoids make a lumpy band
    + Make each box a little long so the outside of a bend has no notch
    + Add them in pieces of 6 segments (`ribbon()`). Each piece has small bounds, so rendering is fast
- Without wind the tails hang straight down with gravity, clear of the chest
    + Past the chest they keep that distance. They do not curl in below the chest
- With wind the tails stream toward the wind like flags
    + The width direction stands upright; the tail ripples sideways and twists slowly
    + The 2nd tail sags a little lower so the two tails do not overlap

## Wind

`wind` in the clothes functions is a world vector. Its length is the distance (m) the hem is pushed. 0.35 is a breeze, 0.55 a strong wind.

| Effect | Size |
|---|---|
| The hem is pushed toward the wind | 30% of the wind length |
| The wind side billows | 45% of the radius per metre of wind |
| The downwind side clings to the legs | Flare reduced by 200% per metre of wind. No flare at 0.5 m or more (`WIND_PRESS`) |
| The windward hem lifts | 55% of the length per metre of wind, at most 45% |
| Folds deepen | 5 cm per metre of wind |
| Scarf tails flutter toward the wind | Ripple and twist grow together |

- Measure the skirt girth at each height from the wind-swayed centre
    + The downwind side clings to the legs and the wind side gains room
    + Adding wind room to the whole girth widens the waist and the downwind side balloons like a sack
- Point the wind a little toward the viewer (-y) and lifted cloth does not hide behind the body
- Hair is a front drawing and does not blow in the wind

## Two-shots

- `staging.pair_for(name, physique_a, physique_b)` gives two people's poses turned and placed
    + The first person stands on the viewer's left

| Name | Pose |
|---|---|
| `side_by_side` | Standing side by side, each turned 12 degrees toward the other. One has a hand on the hip |
| `holding_hands` | Standing side by side, holding inner hands. Heads turned toward each other |
| `facing` | Each turned 32 degrees to face the other. One has folded arms |

- `staging.placed(staging, offset, turn)` turns and moves any pose
- Give `frame()` lists of landmarks and builds and it places the camera to fit everyone
- `figure_study.draw_cast(style, width, setting, [Actor(sitter, pose, extras), ...])` draws them
    + Each person's group names get a prefix (`p0.`, `p1.`) and everyone renders at once. They hide each other and cast shadows on each other
    + Painting goes from the farthest person. A nearer body covers the drawn head of a farther person
    + The place's post-painting (`Setting.painters`) runs once after everyone is painted
- When a head turns more than 35 degrees from the camera, the drawn head stops at 35 degrees. Keep facing angles in two-shots within 35 degrees

## Places

`PLACES` in `examples/scenes.py` holds 9.

| Name | Backdrop | Floor | Furniture and post-painting |
|---|---|---|---|
| `beach` | Sky, clouds, sea, glitter on the water, foam of the waves | Sand, 4 m | None |
| `bedroom` | Violet wall, lamp light, a window with the moon, curtains | Wooden floor | Headboard, 2 pillows, a blanket |
| `office` | Light wall, buildings beyond a big window | Grey floor | Chair colour, desk with a laptop |
| `night_street` | Night sky, lit buildings, 3 neon signs, street lamps | Wet asphalt | Neon reflections on the ground, teal neon rim on the figure's right edge |
| `dusk` | Sunset sky and sun | Red paving | None |
| `cafe` | Warm wall, a big window on the street with an awning, shelves with jars, pendant lights | Wooden floor | Chair colour, a round table with a mug (beside and behind the figure) |
| `park` | Clear sky, a hill, round trees | Lawn, 6 m | Bench colour |
| `panel_yard` | Snowy night, 2 prefab apartment blocks, a leafless tree, a sodium street lamp | Snow, 3 m | Concrete wall and green bench colours, orange rim light on the figure's right, falling snow |
| `rooftop` | Night sky, murky glow on the horizon, power-plant chimneys, an apartment district below, parapet and TV aerials | Roof, 1.6 m; 30 m to each side | Falling snow |

- The backdrop is a 2-D picture
    + Draw the sea's horizon on the camera's horizon (`horizon()`)
    + Get the far edge of the floor from `ground_edge()`
- Put the line where backdrop ground meets the 3-D floor slab on a border in the backdrop
    + On the beach it is the foam of the waves; in the park the foot of the hill
    + Without a border, the floor slab's outline shows across same-coloured grass
- Keep the floor's far edge 5 degrees below the horizon even from a low camera (within about 9 m of the camera)
    + Floor closer to the horizon jumps in depth from row to row; the outlines pile into a dark band
    + That is why the park lawn is 3.5 m. The hill in the backdrop covers what lies beyond
- The floor is a 3-D slab, so it receives the figures' shadows
- `furnish(supports)` looks at the pose's supports and adds furniture around them
    + If there is a bed, pillows go at its end
- `painters` run once after every figure is painted
- Keep pillar-like supports narrower than the frame. A wall that covers the frame hides the place
    + In a knee shot even a 1 m wall covers the frame. For a shot that shows the place, choose a full shot or a pose without a wall
- Shot from behind (`azimuth` around 180), the floor slab and its far edge flip to the side away from the camera (`looking_back(camera)`)
- A wide frame shows the side edge of the floor slab. Increase that place's `ground_width`
- The district below the roof is laid out in metres and projected with the camera
    + A backdrop drawn in canvas units changes size between shots with different angles of view
    + The rows of the district are 70-900 m from the camera; their roofs are lower than this roof. Near rows hide behind the parapet
- A prefab apartment block is one `panel_block()` call. Far blocks that look small skip dark windows and draw only lit ones

## Combination examples

```bash
python examples/outfits.py anime out.png 1280 beach_bikini
python examples/outfits.py painterly out.png 1280 custom f suit seated_chair office full 30
```

- One line `Look(sex, outfit, pose, place, shot, azimuth, elevation, aspect, margin, wind, face)` is one picture
- One line `Duo((sex, outfit), (sex, outfit), pair, place, ..., faces)` is one picture of two people
- `face` and `faces` are `HeadLook`s. They choose hair style, hair colour and features (hair and face templates in `references/figure.md`)
- Outfit names: `bikini`, `swim_trunks`, `innerwear`, `crop_top`, `tee_jeans`, `suit`, `hoodie`, `flared_skirt`, `pleated_skirt`, `pencil_skirt`, `sundress`, `sundress_scarf`, `sheath_dress`, `dark_hoodie`
    + `dark_hoodie`: black hoodie, dark jeans, dark sneakers (`SHOES["dark_sneaker"]`). Both sexes
- 15 preset single looks (`LOOKS`)

| Name | Sex | Outfit | Pose | Place |
|---|---|---|---|---|
| `beach_bikini` | F | Bikini | Hand on hip | Beach |
| `beach_trunks` | M | Swim trunks | Standing | Beach |
| `bedroom_innerwear` | F | Innerwear | Reclining | Bedroom |
| `bedroom_hoodie` | F | Oversized hoodie | Standing (knee shot) | Bedroom |
| `office_suit_f` | F | Beige suit | Seated on a chair | Office |
| `office_suit_m` | M | Navy suit and tie | Arms folded (knee shot) | Office |
| `night_crop_top` | F | Crop top and hot pants | Leaning on a wall | Night street |
| `night_hoodie` | M | Hoodie and jeans | Walking | Night street |
| `dusk_jeans` | F | Tee and jeans | Walking | Dusk |
| `beach_sundress` | F | Strap dress, breeze | Standing | Beach |
| `night_pleated` | F | Tee and pleated skirt | Walking | Night street |
| `office_sheath` | F | Close-fitting dress | Seated on a chair | Office |
| `dusk_scarf` | F | Strap dress and scarf, strong wind | Hand on hip (knee shot) | Dusk |
| `cafe_crossed` | F | Strap dress | Seated, legs crossed | Cafe |
| `park_wave` | F | Crop top and hot pants | Waving (low eye level) | Park |

- 3 preset two-person combinations (`DUOS`)

| Name | Left | Right | Pose | Place |
|---|---|---|---|---|
| `beach_couple` | F, bikini | M, swim trunks | Side by side | Beach |
| `night_date` | F, crop top and flared skirt | M, hoodie and jeans | Holding hands | Night street |
| `office_talk` | F, blouse and pencil skirt | M, suit | Facing (knee shot) | Office |

- 4 doomer-mood figures are in `FIGURES` of `examples/doomer.py`

| Name | People | Pose | Place | Props |
|---|---|---|---|---|
| `man` | M, black hoodie | Walking | Panel-block yard | Beanie, cigarette, earphones |
| `woman` | F, black hoodie, black hair, drooping eyes | Seated, legs crossed | Panel-block yard | Beanie, cigarette, earphones |
| `pair` | F (bob) and M, black hoodies | Side by side (knee shot) | Rooftop | Both smoking, beanie on the man |
| `establishing` | M, black hoodie | Standing, seen from behind | Rooftop | Beanie, cigarette smoke |

- A world-building shot puts the figure in small (`margin=0.36`, a wide frame `aspect=0.66`, `elevation=20`)
    + `FRAME_SHIFT` slides the picture so the figure sits on the right third and the empty roof floor leaves the frame
    + Sliding is a crop from the same camera's wider view, so the perspective holds (`shifted(camera, dx, dy)`)
- The clothed man uses the `figure_male.LEAN` build
- Innerwear, the strap dress and the close-fitting dress are made only on the female mannequin
