# Scene spec reference

## Structure
- A spec is one JSON object
- Every field has a default; write only the fields you need
    + A single line `{"style": "watercolor"}` already renders
- Print all defaults with: `python scripts/render.py --print-defaults`
- A value outside the allowed set prints an error with the allowed list before rendering

## Top-level fields

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| subject | character, still_life, landscape, city, interior | character | Subject |
| canvas.width, canvas.height | 256-4096 | 1024, 1280 | Output resolution (px) |
| canvas.seed | integer | 7 | Random seed for hair lock variation, brush strokes, and paper texture |
| quality | draft, final | final | final renders at 2x resolution and downsamples |
| framing | closeup, bust, waist, full, wide | bust | Framing (closeup fills the frame with face and neck, wide is an establishing shot with a small full-body figure in the scene) |
| style | anime_cel, soft_illust, painterly, watercolor | anime_cel | Style |
| characters | array of 2 or more character objects | none | Two-shots and groups (used in place of character, no head count limit) |
| pair.contact | none, hand_hold, shoulder_arm | none | Two-shot contact pose (2 characters only) |
| pair.lead | 0, 1 | 0 | characters index of the figure who puts the arm around in shoulder_arm |
| pair.rows | integer from 1 to the head count | 1 | Number of rows in a group (from 2, back rows stand smaller and higher and show between front-row heads) |
| mood | none, doomer | none | Mood preset (bundle of grade, background, and expression defaults, see the mood section below) |

- With framing full and no canvas size, the canvas becomes 960x1600
- With framing wide and no canvas size, the canvas becomes 1600x1000
- With body.pose lie and no canvas size, the canvas becomes 1600x1000 with a bed background
- With a subject other than character and no canvas size, the canvas becomes 1280x960
- framing, character, and background apply only when subject is character
- With characters, framing defaults to waist and the canvas to waist 1360x1024, full 1280x1600, wide 1600x1000
    + From 3 people in the front row, each person adds width (waist 480px, full 420px, wide 120px), up to 4096px

## character

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| gender | female, male | female | Gender (male applies the male preset and the male skeleton) |
| view | front, back, side | front | View (back is the back view, side is the profile) |
| facing | right, left | right | Screen direction a profile faces (view side only) |
| skin | hex | #F9E2D2 | Base skin color |
| face_shape | oval, round, sharp, square | oval | Jawline (square is an angular male jaw) |
| head_scale | 0.9-1.1 recommended | 1.0 | Head size scale |
| head.yaw | -40-40 | 15 | Left-right turn (degrees), positive faces screen right |
| head.pitch | -15-15 recommended | 0 | Nod (degrees), positive looks down |
| head.roll | -10-10 recommended | -3 | Head tilt (degrees) |
| body.yaw | -25-25 | 0 | Torso turn (degrees), 15-25 is a 3/4 view (the far side of the bust shows past the body outline) |
| body.roll | -5-5 | 0 | Upper body tilt (degrees) |
| body.pose | relaxed, close, behind, pocket, wave, hand_on_hip, hands_on_hips, arms_crossed, chin_rest, hair_tuck, hands_behind_head, walk, lean, sit, lie | relaxed | Arm pose or full-body posture |
| body.stance | straight, contrapposto, wide, walk, lean, sit, lie | straight, full-body postures use the same name | Leg stance (visible in full framing) |
| body.seat | chair, stool, bed | chair | Seat (pose sit only, bed is the bed edge) |
| body.figure | slim, balanced, curvy, athletic | balanced | Figure (curvy is female only, athletic is male only) |
| body.bust | small, medium, large, xlarge | medium | Bust size (female only, from large the side volume shows in front of the arms) |
| body.muscle | 0-1 | slim 0.10, balanced 0.30, athletic 0.50 | Male muscle definition (0 smooth, 1 sharpest abs and arm muscles) |
| body.hands.right, body.hands.left | open, relaxed, flat, fist, point, peace | pose default | Hand gesture (right is the hand on screen right) |
| body.hold.item | phone, can, cigarette | none | Object held in one hand (view front only) |
| body.hold.side | right, left | right | Hand that holds the object (screen side) |
| place.x | 0-1 | auto | Horizontal canvas position of a single figure (to put the figure on one side of the scene in wide framing) |

- (pose choice) relaxed and close lower the arms with the hands beside the thighs
- (pose choice) wave raises the screen-right hand beside the face and shows the palm (hand and sleeve are drawn over the hair)
- (pose choice) hand_on_hip and hands_on_hips rest the hands on the waist with the backs of the hands showing
- (pose choice) behind hides the hands behind the back
- (pose choice) pocket puts the hands in the hoodie's kangaroo pocket, other outfits switch to behind automatically
- (gestures) arms_crossed crosses the arms under the bust, chin_rest rests the chin on one hand, hair_tuck tucks hair behind the ear with one hand, hands_behind_head laces both hands behind the head
- (full-body postures) walk has a stride and arm swing, lean leans the back on a wall with one foot against it, sit sits facing front, lie lies on a bed with one arm behind the head
- (full-body postures) pose walk, lean, sit, or lie sets the stance of the same name automatically (a stance given directly wins)
- (sit) a seated figure is shorter than a standing one, so full framing scales it up to fill the frame again
- (lie) the whole figure is drawn turned 90 degrees
- (lie) a shadow of the figure is added on the bed sheet automatically
- (stance choice) contrapposto puts the weight on the screen-left leg with a hip tilt and the other leg apart
- Hands are projections of a 3D palm and a 3-segment finger skeleton; changing only the gesture changes the finger shapes
- wave with peace: `"body": {"pose": "wave", "hands": {"right": "peace"}}`
- (figure fallback) athletic on a woman becomes balanced, curvy on a man becomes athletic
- (3/4 view) body.yaw and head.yaw in the same direction look natural (for example body.yaw 24, head.yaw 20)
- (female figures) curvy has the narrowest waist and the widest hips and thighs
- (hold) the holding arm takes a fixed pose per object and the other arm follows pose
    + phone is a hand cradling the phone's back in the palm in front of the chest (the viewer sees the back of the hand and the back of the phone), the screen's cold light brightens the area around the hand
    + can is a hand at belly height gripping the can with the back of the hand toward the viewer
    + cigarette is a cigarette between the fingers of a hand hanging beside the hip, the smoke rises and drifts away from the body
    + with phone and can the fingers wrap around the far edge of the object and end in rounded knuckles
    + to look at the object, combine head.pitch 14-18 with eyes.gaze [x, 1.2] and eyes.openness 0.45-0.5
- (wide) a distant full figure about 40% of the canvas height, feet fixed on the ground in the lower part of the frame
    + the scene leads, so put the figure to one side with place.x 0.3-0.4 or 0.6-0.7 and leave room in the gaze direction

### view
- front: default view, head.yaw and body.yaw turn it up to a 3/4 view
- back: the body seen from behind, the face looks back over the shoulder in the head.yaw direction
    + head.yaw 25-35 recommended (at 0 the frontal face sits on top of the back silhouette)
    + Back anatomy: spine groove, shoulder blades, female lower back dimples, male trapezius and lats, glute volume
    + Front-only details (buttons, ties, pockets, zippers) are left out, the neckline rises to the back of the neck
    + The halter dress turns into an open back, the one-piece swimsuit into a back scoop
    + The behind pose gathers the hands behind the waist
- side: dedicated profile template (nose, lips, and chin sit on the face outline)
    + Bust and glutes are drawn as part of the body silhouette, tops fall straight down from the bust point
    + Supported postures: relaxed, walk, sit (other poses draw as relaxed)
    + Outfits simplify to neckline, hem, sleeves, straps, and flare (front details such as buttons and prints are left out)
    + facing picks the direction

### gender (male preset)
- `"gender": "male"` inserts the male preset between the defaults and the user's values (user values always win)

| Area | Male preset values |
|---|---|
| Face | face_shape square, face.length 1.10, nose defined, lips thin, skin #F3D6C2 |
| Eyes | shape sharp, size 0.96, openness 0.82, iris 0.92, lashes none, color #4A5A6E |
| Expression | mouth neutral, blush 0, brows straight, brow_weight 2.3, brow_lift -0.12 |
| Hair | style short, bangs side_swept, color #3A3234, ears visible |
| Skeleton | inverted triangle torso, round deltoids, plate-like pectorals, 6-pack abs, thicker limbs, Adam's apple, hands and feet 1.22x, wider leg spacing |
| Outfit | type shirt, bottoms default to jeans or board_shorts |

- 3 male figures: slim (lean build), balanced (standard build), athletic (widest shoulders and chest)
- Muscle definition follows the default per figure; set it directly with body.muscle (for example `"body": {"figure": "athletic", "muscle": 0.8}`)
- Not allowed for men: offshoulder_dress, crop_top, bikini, one_piece, sports_bra, camisole, slip_dress, halter_dress, bottom bikini, pencil_skirt, dolphin_shorts
- Not allowed for women: shirtless

### face

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| length | 0.9-1.15 | 1.0 | Face length (nose and mouth positions scale with it) |
| nose | small, button, defined | small | small is a nose bridge shadow, button a round tip, defined adds nostril wings and a bridge |
| lips | thin, natural, full | natural | thin draws the upper line only, natural adds lower lip color, full adds a Cupid's bow and lip gloss |

### eyes

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| color | hex | #4F7DB8 | Iris color |
| shape | almond, round, droopy, sharp | almond | Eye shape (droopy slopes down, sharp slopes up) |
| size | 0.85-1.15 recommended | 1.0 | Eye size |
| openness | 0.6-1.1 | 1.0 | How open the eyes are |
| tilt | -5-8 | 3 | Outer corner tilt (degrees) |
| gaze | viewer, forward, left, right, up, down, [x, y] | viewer | Gaze, viewer looks at the viewer whatever the head direction |
| spacing | 0.9-1.1 | 1.0 | Distance between the eyes |
| iris | 0.85-1.15 | 1.0 | Iris size scale |
| lashes | none, light, normal, heavy | normal | Lash thickness and number of tip flicks |
| crease | true, false | true | Double eyelid line |

### expression

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| mouth | smile, neutral, soft, pout, open_smile, open | smile | Mouth shape |
| blush | 0-1 | 0.35 | Cheek blush strength |
| blush_color | hex | #F28C8C | Blush color |
| brows | soft, straight, raised, sharp | soft | Brow shape (raised is a troubled look) |
| eye_smile | 0-1 | 0 | Raises the lower lids for smiling eyes |
| brow_weight | 0.8-2.5 | 1.0 | Brow thickness scale |
| brow_lift | -0.2-0.2 | 0 | Brow height (negative lowers them toward the eyes) |

### hair

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| color | hex | #5A3C38 | Base hair color |
| style | long, bob, ponytail, short | long | Hairstyle (short is nape length with crown locks and sideburns in front of the ears) |
| bangs | full, side_swept, parted | side_swept | Bangs (full is straight-cut locks, parted is a center part) |
| length | head units | long 2.55, bob 1.08, short 0.72 | Back hair length |
| wave | 0-1 | 0 | Wave strength |
| volume | 0.8-1.3 | 1.0 | Hair thickness over the scalp |
| part_side | 1, -1 | opposite the head turn | Part direction (1 is screen right) |
| ears | hidden, visible | hidden | Whether the ears show |

### outfit

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| type | knit_sweater, shirt, offshoulder_dress, hoodie, crop_top, bikini, one_piece, rash_guard, beach_shirt, tank_top, shirtless, sports_bra, camisole, slip_dress, halter_dress, tee, oversized_tee | knit_sweater | Top |
| variant | turtleneck, crew (knit), tank, tee (crop top), triangle, bandeau (bikini), classic, cutout (one-piece swimsuit), plain, print (beach shirt), tie, bow (shirt) | first value per outfit | Top variant |
| bikini_color | hex | #2F4F7A | Color of the bikini worn with a rash guard or a beach shirt |
| print_color | hex | #E38A5C | Pattern color of the beach shirt print |
| color | hex | per outfit | Top color |
| bottom | a_line_skirt, jeans, bikini, board_shorts, swim_briefs, boxer_briefs, leggings, joggers, slacks, pencil_skirt, dolphin_shorts, null | per top | Bottom (null for one-pieces and dresses) |
| bottom_style | classic, high_leg, string | classic | Bikini bottom cut |
| bottom_color | hex | per bottom, bikini uses the top color | Bottom color |
| shoes | sneakers, boots, sandals, barefoot, heels, dress_shoes | per outfit | Shoes |
| tie_color, bow_color | hex | #7A2E3A, #2F3542 | Shirt tie and bow colors |
| shoe_color | hex | per shoe | Shoe color |

- (female bottom defaults) knit gets an A-line skirt; shirt, hoodie, crop top, tank top, and tee get jeans; bikini, rash guard, and beach shirt get a bikini bottom; sports bra gets leggings; camisole gets dolphin shorts; one-pieces, dresses, the one-piece swimsuit, and the oversized tee get none
- (male bottom defaults) knit, shirt, hoodie, tank top, and tee get jeans; the oversized tee gets joggers; rash guard, beach shirt, and shirtless get board_shorts
- (shoe defaults) swim tops, swimsuits, underwear bottoms, and homewear (camisole, oversized_tee) are barefoot; dresses (slip_dress, halter_dress) get heels; slacks get dress_shoes; everything else gets sneakers
- (sportswear) sports_bra is a sports bra with a wide underband, leggings are ankle-length fitted leggings, joggers are joggers with elastic cuffs
- (office look) shirt variant tie adds a necktie, bow makes a bow blouse; a shirt over slacks or a pencil_skirt is tucked in automatically (slacks include a belt)
- (party dresses) slip_dress is an above-knee dress with thin straps and satin sheen, halter_dress has a neck strap and an open back
- (homewear) camisole has lace trim, oversized_tee is a long tee covering the hips, dolphin_shorts are short shorts with side slits
- tee is a unisex short-sleeve T-shirt
- beach_shirt is an unbuttoned short-sleeve shirt, worn over a triangle bikini by women and over a bare chest by men
- tank_top is a unisex sleeveless top, shirtless is a male-only bare torso
- (male bottoms) board_shorts are mid-thigh board shorts with side stripes and a waist cord
- (male bottoms) swim_briefs are low-rise swim briefs, boxer_briefs are boxer briefs with a waistband
- The front panel of swimwear and underwear is a smooth surface; the crotch shape is not emphasized
- Bottoms and shoes render only in waist and full framing
- The crop top ends above the navel and jeans are low-rise, so the belly shows (skirts have a high waistline and cover it)
- (bottom_style) classic is a basic brief cut, high_leg raises the side line above the hip bones, string has a small front panel with strings and side bows
- In view back the bikini bottom draws as its back panel (classic and high_leg cover most of the glutes, string is a small triangle)
- Revealing outfits add torso cylinder shading, the navel, the abdominal midline, the groin lines, and the crease under the bust automatically
- Revealing male outfits also add the line under the pectorals, ab divisions, flank lines, and the Adam's apple
- Necklines, collars, and armholes widen automatically for the thicker male neck and broader shoulders

### accessories
- Given as an array: `["hairpin", "necklace", "earrings"]`
- hairpin puts 2 pins in the bangs on the parting side, color from `character.hairpin_color`
- necklace is a chain and a pendant, works best with outfits that show the collarbones (shirt, off-shoulder)
- earrings render only with `hair.ears: "visible"`
- beanie is a knit hat covering down to the forehead (folded cuff and ribs), it hides the crown locks and keeps the bangs and side locks
    + Hat color is `character.beanie_color` (default #2E3038), also applies to the profile

## characters (two-shots and groups)
- An array that places 2 or more characters, each entry has the character fields plus place
- No limit on head count or gender mix
- Supports waist, full, and wide framing
- pose lie is not supported for group members
- Contact poses (pair.contact) apply only to 2 people in one row; 3 or more stand or sit side by side
- A group wider than the canvas shrinks to fit (full keeps the ground line, waist keeps the tallest figure's head top)

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| place.x | 0-1 | auto | Horizontal canvas position of the figure's center |
| place.scale | 0.9-1.1 recommended | 1.0 | Height scale (1.04-1.08 recommended for men), the feet of both figures share one ground |
| place.depth | real number | row number | Larger values are drawn behind; on a tie, list order runs back to front |
| place.row | integer 0 or more | auto | Row the figure stands in (0 is the front row) |

- (placement) without place.x the gap between neighbors is computed in head heights
    + no contact 1.95, hand_hold 2.05, shoulder_arm 1.15, plus 0.25 per man among the neighbors, 1.85 when all are profiles
- (placement) without place.x figures are placed from screen left in list order
- (multiple rows) with pair.rows the front row fills first from the start of the list (people per row by ceiling division, 7 people in 2 rows gives 4 in front and 3 behind)
    + Each row further back is 0.93x the size and stands 0.55 head heights higher to show depth
    + A back row with as many people as the front row shifts sideways by half a gap, so faces show between front-row heads
    + place.row sets the row of a specific figure
- (head) without head.yaw each figure turns 15 degrees toward the group center; the middle figure of an odd group faces front
- (profiles) with view side and no facing, figures face the group center (2 people face each other, the middle figure of an odd group faces right)
- (hand_hold) the inner hands of the two figures meet between them, the front figure's hand wraps the back figure's fingers
    + Supports view front and back (a back-view walk holding hands works)
- (shoulder_arm) the pair.lead figure puts the inner arm around the partner's shoulders
    + The forearm comes out from behind the partner's neck, rests on the far shoulder, and the hand hangs in front of the shoulder
    + The draw order puts the figure with the arm behind automatically
    + Supports view front only
- (contact in general) arms_crossed, sit, and lie cannot take contact (poses that use both arms)
- (contact in general) an action such as wave or chin_rest on the inner arm moves to the outer arm automatically
- Example: couple holding hands, full body

```json
{"framing": "full", "pair": {"contact": "hand_hold"},
 "characters": [
   {"outfit": {"type": "offshoulder_dress", "shoes": "heels"}},
   {"gender": "male", "place": {"scale": 1.06}, "outfit": {"type": "shirt", "bottom": "slacks"}}],
 "background": {"type": "city", "city": {"time": "dusk"}}}
```

## still_life

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| wall | hex | #E6DCCB | Wall color |
| table | hex | #8A5A3C | Table color (also sets the reflected light color) |
| cloth | hex, null | #F2EEE6 | Tablecloth color, null leaves it out |
| leaves | hex | #5E8A4A | Flower stem and leaf color |
| objects | array | default 6-object layout | Object list |

- Fields of an objects entry

| Field | Allowed | Meaning |
|---|---|---|
| type | vase, bottle, cup, mug, jar, apple, orange, lemon, pear, laptop, monitor, keyboard, mouse, phone, headphones, lamp, books, plant | Object kind |
| x | 0-1 | Horizontal position (share of canvas width) |
| depth | 0-1 | 0 is the back of the table, 1 the front (also sets draw order and size) |
| scale | 0.6-1.4 | Size scale |
| color | hex | Object color |
| flowers | hex | Puts flowers in a vase, jar, or bottle |
| liquid | hex | Drink color in a cup or mug |
| yaw | degrees | Horizontal turn of modern objects (each object has a default) |
| screen | code, desktop, off | Screen theme of laptop, monitor, phone (laptop defaults to code, the others to desktop) |
| leaves | hex | Leaf color of plant |

- Where objects overlap, the one with the larger depth is drawn in front
- 3-6 objects work best, horizontal positions within 0.15-0.85 recommended
- Modern objects are assemblies of solids (boxes, rods, domes) projected with the same oblique view, so their tops read consistently
- For a desk still life put large objects such as monitor and laptop at depth 0.05-0.3, and keyboard, mouse, phone, mug at depth 0.5-0.7

## interior

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| room | bedroom, office, cafe, pool, gym | bedroom | Room type |
| wall, floor, accent | hex | palette per room | Wall, floor, and accent colors |

- bedroom: wooden floor, curtained window, bed, nightstand with a lamp, wall frame
- office: window with blinds, desk with a monitor and keyboard, potted plant, mug, bookshelf
- cafe: menu board, pendant lights, counter with a coffee machine, round table
- pool: sky, low hedge, pool water with ripples, parasol, sun loungers
- gym: rubber mat floor, mirror wall, dumbbell rack, bench, kettlebells
- As a character background the furniture scale follows the head size of the character framing automatically

## landscape

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| time | day, sunset, misty, night | day | Time of day (sky, light, mountain and water color set; night adds moon, stars, and moonlight) |
| clouds | 0-5 | 3 | Number of cumulus clouds |
| tree | true, false | true | Foreground tree (placed opposite the light) |
| flowers | hex | #F4F0E0 | Wildflower color |

- The composition is fixed: sky, 3 mountain layers (distant snowy range, middle snowy range, near conifer hill), lake with reflections, meadow
- Vary the composition with canvas.seed (ridges, clouds, and tree shapes change)

## city

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| time | day, dusk, night | day | Time of day (sky, light, share of lit windows) |
| camera_x | -4-4 | -1.8 | Camera left-right position (m), 0 is a symmetric street |
| awning | hex | #5E7F6E | Shop awning color |
| wires | true, false | false | Utility poles and sagging wires (poles on both sides, wires across the street) |

- One-point perspective street: building facades, windows, shops, awnings, street lights, distant skyline
- Building heights and colors change with canvas.seed

## lighting

| Field | Allowed | Default | Meaning |
|---|---|---|---|
| key | upper_left, upper_right, front, side_left, side_right, [x, y, z] | upper_left | Key light direction (screen space x right, y down, z toward the viewer) |
| key_color | hex | #FFF4E6 | Key light color |
| rim_color | hex | #FFE2B8 | Rim light color |
| rim_strength | 0-1 | 0.55 | Rim light strength |
| rim_dir | [x, y] | opposite the key | Rim light direction |

- The key direction sets shadow positions, line weight variation, and iris highlight positions together
- landscape and city use the light of their time set by default; a lighting.key other than upper_left uses that direction

## background

| type | Default colors | Features |
|---|---|---|
| plain | [#E9EEF3] | Solid color |
| gradient | [top, bottom] | Vertical gradient with a soft light behind the head |
| sky | [upper sky, lower sky, clouds] | Noise-based clouds |
| bokeh | [top, bottom, lights] | Round light bokeh with a night-view feel |
| window | [upper wall, lower wall, sunlight] | Diagonal window light beams and a window frame |
| beach | [upper sky, horizon sky, sea, sand] | Sea horizon, glints on the water, wave lines, sand, cumulus clouds |
| bed | [sheet, pillow, blanket] | Bed sheet, pillow, and blanket seen from above (default background for pose lie) |
| bedroom, office, cafe, pool, gym | none | Renders an interior scene as the character background, `"interior": {...}` takes wall, floor, accent |
| landscape | none | Renders a landscape scene as the character background, `"landscape": {...}` takes the landscape fields (tree defaults to false) |
| city | none | Renders a city street scene as the character background, `"city": {...}` takes the city fields |

- landscape and city backgrounds apply the scene's light to the character as is
    + At sunset, dusk, and night the character takes the scene tint and a rim light, so the composite blends in
- In full framing with a beach, landscape, city, or interior background a ground shadow is added under the feet automatically
- In the watercolor style plain and gradient backgrounds fade into bare paper away from the character; other backgrounds keep the scene
- Example: `"background": {"type": "city", "city": {"time": "night"}}`

## post (finishing)
- Without it the style defaults apply; given keys override only themselves

| Field | Range | Meaning |
|---|---|---|
| light_wash | 0-1 | Warm glaze on the light side, cool glaze on the other side |
| bloom | 0-1 | Glow around bright areas |
| grade | neutral, warm, cool, sunset, doomer | Split toning (doomer desaturates, adds navy shadows, and fades the darks) |
| grade_amount | 0-1 | Toning strength |
| vignette | 0-0.4 | Darker edges |
| grain | 0-0.02 | Film grain |
| vibrance | 0-0.3 | Saturation boost for muted colors |

## mood (mood presets)
- A preset that bundles defaults of several fields and applies them at once; values the user gives always win
- doomer: a cold, muted picture of late-night solitude (empty night street, power lines, blank tired eyes)

| Target | doomer defaults |
|---|---|
| post | grade doomer, grade_amount 1.0, grain 0.018, vignette 0.30, light_wash 0, vibrance 0 |
| background (character) | night city street with power lines (`{"type": "city", "city": {"time": "night", "wires": true}}`) |
| city, landscape | time night, city also wires true |
| character | eyes.openness 0.80, expression mouth neutral, blush 0.06, eye_smile 0, brows soft |

- A background given directly or pose lie (bed background) skips the background default
- In two-shots and groups every character in characters takes the character defaults
- Good companions: beanie (accessories beanie), a dark hoodie, a held prop, a wide shot, a night interior by a window (window background in dark colors)
- Example: a man in a beanie holding a cigarette on a night street

```json
{"style": "anime_cel", "framing": "waist", "mood": "doomer",
 "character": {"gender": "male", "head": {"yaw": -12, "pitch": 4}, "eyes": {"openness": 0.72},
   "accessories": ["beanie"], "body": {"hold": {"item": "cigarette", "side": "left"}},
   "outfit": {"type": "hoodie", "color": "#2A2C34", "bottom": "jeans"}}}
```

## Palette guidelines
- Keep only 1 of hair, outfit, and background highly saturated and the rest muted
- A muted background in the complement or a neighbor of the outfit color separates the figure well
- With black hair raise the background value; with blond or silver hair lower it
- An iris color from a different part of the color wheel than the hair draws the eye to the eyes
- Adjust skin only in value near the default (#F9E2D2, #F3D2BE, #E8BFA3, and so on)
