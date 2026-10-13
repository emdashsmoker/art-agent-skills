# Figures

How to set build, face, expression, pose, hands, hair, outfit and make-up

## Contents

- Build and face
- Expression
- Pose language
- Hand targets (reach)
- Held props (held_by)
- Two-person poses (pairs)
- Rows of people (groups)
- Hand shapes
- Hair
- Hat (hat)
- Outfits
- Make-up and eyes (look)
- Common problems

## Build and face

### Presets

| Name | Character |
| --- | --- |
| `woman` | Young adult woman, sharp jawline, large eyes, hourglass build (default) |
| `woman_fuller` | Glamorous build with strong curves |
| `woman_slender` | Tall, long-legged model build |
| `woman_soft` | Soft face shape, average build |
| `woman_athletic` | Muscular, sharp jawline |
| `woman_classical` | Classical-painting proportions, Greek nose, full figure |
| `woman_mature`, `woman_elder` | Middle-aged, elderly |
| `woman_anime` | Large eyes, small nose and mouth, short chin, slim build. For cel styles (`stylize: anime` by default) |
| `man` | Young adult man, square jaw and dark brows, broad shoulders and narrow waist |
| `man_athletic` | Muscular. Includes abdominal and chest contour shading (`muscle_definition`) |
| `man_slim` | Thin build, sharp jawline |
| `man_classical` | Classical-sculpture proportions, Greek nose, trained body. For classical male figure studies like David |
| `man_mature`, `man_elder` | Middle-aged, elderly |
| `man_anime` | Long legs, lean jaw, slightly large eyes. For cel styles (`stylize: semi` by default) |
| `androgynous` | Androgynous |

### Build axes (`phenotype`, 0-1)

| Axis | 0 | 1 |
| --- | --- | --- |
| `gender` | Male | Female |
| `age` | 0.77 is 18 years. Bodies under 18 are drawn clothed only (unclothed, underwear, bikini refused) | 0.776 young adult (about 23), 0.80 (41), 0.82 (56), 0.97 elderly |
| `muscle` | Little | Much |
| `weight` | Thin | Full |
| `height` | Short | Tall |
| `proportions` | Idealised proportions | Ordinary proportions |
| `cupsize`, `firmness` | Small, low | Large, high |
| `african`, `asian`, `caucasian` | The ratio of the three blends skeletal traits | |

### Face stylisation (`stylize`)

Applies cartoon proportions to the face that morphs cannot reach. Eyes, eyelids and brows move together, so the mesh does not tear

| Value | Effect |
| --- | --- |
| `none` | Realistic proportions |
| `semi` | Eyes a little larger, nose and mouth a little smaller, lower jaw a little shorter. Webtoon, semi-realistic |
| `anime` | Large eyes, small nose, narrow mouth, short and slender lower jaw. Anime |
| `chibi` | The strongest deformation |

- If the preset has a default it is used; the figure object's `stylize` overrides it

### Face and body morphs (`face`, -1 to 1)

254 axes. Full list with `python scripts/catalog.py shapes`. Frequently used axes

| Purpose | Axes |
| --- | --- |
| Sharpen the jawline | `chin-width-incr` negative, `chin-bones-incr` negative, `head-fat-incr` negative, `l/r-cheek-bones-incr` positive |
| Larger eyes | `l-eye-scale-incr`, `r-eye-scale-incr` positive |
| Wide-open eyes | `l-eye-height1-incr`, `r-eye-height1-incr` positive |
| Raised outer eye corners | `l-eye-corner2-up`, `r-eye-corner2-up` positive |
| Smaller nose | `nose-scale-horiz-incr`, `nose-scale-depth-incr` negative |
| Fuller lips | `mouth-lowerlip-volume-incr`, `mouth-upperlip-volume-incr` positive |
| Slimmer neck | `neck-scale-horiz-incr` negative |
| Waist and hips | `measure-waist-circ-incr` negative narrows, `measure-hips-circ-incr` positive widens |
| Masculine upper body | `torso-vshape-incr`, `measure-shoulder-dist-incr`, `torso-muscle-pectoral-incr`, `torso-muscle-dorsi-incr` positive |
| Limb muscles | `l/r-upperarm-muscle-incr`, `l/r-upperarm-shoulder-muscle-incr`, `l/r-upperleg-muscle-incr` positive |
| Brow ridge and jaw | `eyebrows-trans-forward` positive gives a heavy brow ridge, `chin-bones-incr` positive a square jaw |
| Bust | Build axes `cupsize`, `firmness`, plus `breast-trans-up`, `breast-volume-vert-up` |
| Buttocks, thighs | `buttocks-volume-incr`, `measure-thigh-circ-incr` |
| Leg length | `upperlegs-height-incr`, `lowerlegs-height-incr` |
| Abdominal tone | `stomach-tone-incr` |
| Shoulder width | `measure-shoulder-dist-incr` |

- For symmetric axes, give `l-` and `r-` the same value
- These override the preset. Only the axes given change

## Expression

- Presets: `neutral`, `soft_smile`, `smile`, `serene`, `eyes_closed`, `serious`, `determined`, `sad`, `surprised`, `angry`, `melancholy`, `smirk`
- Set directly as an object of the 52 expression units (0-1)
    + Example: `{"mouthSmileLeft": 0.5, "mouthSmileRight": 0.5, "browInnerUp": 0.3, "jawOpen": 0.2}`
    + Eyes closed `eyeBlinkLeft/Right`, gaze `eyeLookUp/Down/In/OutLeft/Right`, mouth `mouthPucker`, `mouthFunnel`, brows `browDownLeft/Right`, `browOuterUpLeft/Right`

## Pose language

Poses are described by what the joints do, not by bone angles. A preset name or an object. Putting `preset` in the object overrides on top of it

```json
"pose": {
  "preset": "contrapposto",
  "head": {"turn": 20, "tilt": 6, "nod": 4},
  "arm.R": {"lift": 40, "forward": 60, "elbow": 80},
  "hand.R": "graceful"
}
```

### Presets

| Group | Names |
| --- | --- |
| Standing | `stand`, `contrapposto`, `s_curve`, `arms_behind_head`, `look_over_shoulder` (for back views, camera `yaw` 150-180), `hand_on_hip`, `hands_on_hips`, `arms_crossed`, `hand_on_chest`, `hair_touch`, `thinking`, `venus`, `pray` (palms together before the chest), `a_pose` |
| Holding things | `read_book` (an open book in both hands), `read_seated` (reading in a chair), `hold_cup` (a cup in the right hand), `look_at_phone` (looking down at a phone in the right hand). The prop is held with `held_by` (see Held props below) |
| Smoking | `smoke` (right hand with a cigarette lowered, head bowed), `smoke_inhale` (cigarette hand beside the chin), `sit_smoke` (seated, elbows on knees, cigarette between the knees). Hold a `cigarette` with `held_by` |
| Male standing | `david` (classical contrapposto with one hand at the shoulder), `heroic` (fists at the waist, legs apart), `hands_in_pockets` (both hands in trouser pockets; for clothed figures) |
| Action | `walk`, `run`, `jump` (in the air), `fight_stance`, `wave`, `arms_up`, `reach_up`, `point_forward` |
| Sitting | `sit_chair`, `sit_crossed_legs`, `sit_floor`, `kneel`, `kneel_sit` (sitting on the heels), `seated_side` (sitting sideways on the floor) |
| Lying | `recline` (lying propped on one side), `lie_back` |

- When a `reach` toward the body would bury the forearm in the torso, the engine turns the elbow outward as far as needed
- For seated poses, place the chair prop behind the figure (`at: [0, 0.12, 0]`)
- To lay or seat a figure on a bench or platform, set the z of the figure's `position` to its top surface
- Figures are placed so the lowest body point touches the ground
    + Adding `"airborne": 0.3` to the pose floats it that high (built into `jump`)
- The figure direction `facing` takes a target instead of an angle: a prop name (`"table"`), another figure's name, or scene coordinates `[x, y]`
    + A prop's `rotate_deg` takes targets the same way (a chair turned toward a table)

### Joints

| Key | Fields | Meaning |
| --- | --- | --- |
| `body` | `lean`, `tilt`, `turn` | The whole body from the pelvis. Lean forward, tilt to the figure's left, turn to the left |
| `torso` | `bend`, `side`, `twist` | Spread over the whole spine |
| `head` | `nod`, `tilt`, `turn` | Spread over neck and head. Positive `nod` bows |
| `arm.L`, `arm.R` | `lift` | 0 hanging, 90 horizontal, 180 up |
| | `forward` | 90 front, 0 side, -90 back |
| | `twist` | Positive turns inward. With the elbow bent, the forearm crosses in front of the body |
| | `elbow` | 0 straight, 150 fully bent |
| | `forearm_twist`, `wrist`, `wrist_side`, `shrug` | Palm direction, wrist bend, wrist side bend, shoulder shrug |
| `leg.L`, `leg.R` | `forward` | Hip flexion. 90 is the thigh horizontal |
| | `side`, `twist` | Spread, toes turned out |
| | `knee`, `ankle`, `foot_turn` | Knee bend, toes pointed down, foot turn |
| `gaze` | `yaw`, `pitch` | Eye direction |
| `bones` | `{bone name: [rx, ry, rz]}` | Rotates single bones directly. Last resort |

- `.L` is the figure's own left. On screen it appears on the right

## Hand targets (reach)

To put a hand somewhere, give a target instead of guessing angles. The engine works out the shoulder and elbow angles

```json
"pose": {"preset": "stand",
         "reach.R": {"to": "chin", "elbow": "down", "offset": 0.03},
         "reach.L": "hip.L"}
```

| Field | Description |
| --- | --- |
| `to` | A body landmark name, a point `[x, y, z]` in the figure's own space, or another figure's landmark `"name:landmark"` (e.g. `"b:shoulder.R"`) |
| `world` | Instead of `to`, scene coordinates `[x, y, z]` |
| `elbow` | Where the elbow points: `down`, `out`, `back`, `up`, `forward` |
| `elbow_world` | Instead of `elbow`, a direction `[x, y, z]` in scene axes |
| `offset` | Distance off the skin. Default 0.02 |
| `lay` | `true` lays the palm flat on the skin at that point. The fingers lie along the line the forearm runs (a chest, a waist, another person's shoulder) |

- Body landmarks: `head_top`, `forehead`, `temple.L/R`, `cheek.L/R`, `mouth`, `chin`, `ear.L/R`, `nape`, `throat`, `shoulder.L/R`, `shoulder_top.L/R` (top of the shoulder, where a resting hand lies), `chest`, `heart`, `breast.L/R`, `ribs.L/R`, `belly`, `waist.L/R`, `pocket.L/R`, `hip.L/R`, `pelvis`, `small_of_back`, `back_upper.L/R`, `back_lower.L/R`, `spine_upper`, `spine_lower`, `thigh.L/R`, `knee.L/R`
- To use another figure's landmark, that figure must be added first (put it earlier in the `figures` array)
- On an arm with `reach`, `lift`, `forward`, `twist` and `elbow` are ignored. `wrist` and `forearm_twist` still apply
- With `lay` the engine also sets the wrist bend and the forearm turn. The `rest` or `flat` hand shape looks natural
- Targets near the face tend to let the hand cover the face. Check in the underdrawing, then raise `offset` or move the target to `ear` or `temple`

## Held props (held_by)

Give a prop `held_by` and it sits in the hand without coordinate work. The figure must be added first (spec files handle this automatically)

```json
"props": [{"kind": "book", "held_by": "a:hands", "open": true},
          {"kind": "mug", "held_by": "b:hand.R"}]
```

| Value | Meaning |
| --- | --- |
| `name:hand.R`, `name:hand.L` | One hand. Cups, bottles and glasses stand upright wrapped in the hand. With the palm facing up, they stand on the palm |
| `name:hands` | Between both hands. A book rests across both palms |

- Props that lie on the palm: `book`, `phone`, `tablet`, `plate`, `game_controller`. A `cigarette` goes between index and middle finger. Everything else is held upright
- A book with `"open": true` is open
- Matching poses: `read_book`, `read_seated` + a book, `hold_cup` + `mug` or `takeaway_cup`, `look_at_phone` + `phone`, `smoke`, `smoke_inhale`, `sit_smoke` + `cigarette`
- `rotate_deg` turns the prop in the hand (e.g. the mug handle direction)

## Two-person poses (pairs)

A two-shot where the bodies touch goes in the top-level `pairs` array. The engine places both people and solves the touching hands against the other body

```json
"pairs": [{"kind": "hold_hands", "facing": 35,
           "a": {"name": "a", "preset": "woman", "pose": "walk", "outfit": "summer_dress"},
           "b": {"name": "b", "preset": "man", "pose": "walk", "outfit": "tshirt_jeans"}}]
```

| `kind` | Look | Default spacing |
| --- | --- | --- |
| `hold_hands` | Side by side holding hands. a's left hand and b's right hand | 0.56 m |
| `hand_on_shoulder` | a rests a hand on b's near shoulder | 0.52 m |
| `arm_around` | a puts an arm round b's shoulders and b holds a's waist | 0.44 m |
| `hug` | Face-to-face embrace. a holds b's shoulders, b holds a's waist, heads to opposite sides | 0.34 m |
| `dance` | Couple dance hold. a's (the lead's) right hand on b's back, b's left hand on a's shoulder, the other hands joined. Both look past the other's right shoulder | 0.44 m |

| Field | Description |
| --- | --- |
| `a`, `b` | Same fields as a `figures` entry. In the default view a is on the left |
| `at` | Centre of the pair `[x, y]` |
| `facing` | Direction of the whole pair. 0 faces the camera |
| `distance` | Overrides the spacing |

- Giving `a` or `b` a `pose` such as `walk` changes only the touching arm and keeps the rest
- A palm touching the other body is laid flat on the skin. Where the other person's hair covers that spot, it lies on the hair and flattens the hair under it
- To swap roles, swap `a` and `b`. Example: for the man's arm round the woman's shoulders, make the man `a`
- With the camera omitted, the framing takes in both people
- Examples: `seaside_walk_watercolor.json` (walking hand in hand), `couple_dance_classical.json` (dance), `pen_wash_park_bench.json` (seated `arm_around` on a bench)

## Rows of people (groups)

A group of three or more standing in a row, each touching the next, goes in the top-level `groups` array

```json
"groups": [{"kind": "arm_around", "members": [
  {"name": "p1", "preset": "woman_anime", "outfit": "sweater_skirt"},
  {"name": "p2", "preset": "man_anime", "outfit": "hoodie_jeans"},
  {"name": "p3", "preset": "woman_anime", "outfit": "tshirt_jeans"}]}]
```

| Field | Description |
| --- | --- |
| `kind` | `arm_around` (arms round shoulders), `hold_hands` (a row holding hands), `hand_on_shoulder` |
| `members` | A `figures` entry for each person, from the left in the default view. Unnamed members become `p1`, `p2` and so on |
| `at`, `facing` | Centre and direction of the row |
| `spacing` | Distance between neighbours. Defaults to the `pairs` spacing of the same `kind` |

- Each pair of neighbours touches like a and b of `pairs`. Everyone uses the left arm for the right-hand neighbour and the right arm for the left-hand neighbour
- A person in the middle, touching both neighbours, looks straight ahead
- For a group without contact, put several people in `figures` with positions and `facing`
- Example: `anime_friends_trio.json` (three with arms round shoulders)

## Hand shapes

- Presets: `relaxed` (default), `open`, `flat`, `fist`, `point`, `peace`, `grip`, `pinch`, `graceful`, `thumbs_up`, `cigarette` (index and middle finger loosely together), `rest` (a hand laid on a body: fingers together, barely bent)
- Set directly: `{"curl": [thumb, index, middle, ring, little], "spread": -1 to 1}`. `curl` 0 is straight, 1 fully bent

## Hair

```json
"hair": {"style": "long_wavy", "bangs": "side", "part": "left", "color": "auburn",
         "density": 1.0, "length_scale": 1.0, "wind": [0.5, 0, 0]}
```

| Field | Options |
| --- | --- |
| `style` | Long: `long_straight`, `long_wavy`, `very_long`, `shoulder`, `long_male` (shoulder-length men's long hair) |
| | Bob and curls: `bob`, `pixie`, `curly`, `afro` |
| | Short: `buzz` (close to shaved), `short_crop`, `textured_crop` (short with the front raised), `side_part`, `undercut` (short sides, top swept back), `slick_back` |
| | Tied: `ponytail`, `low_ponytail`, `bun`, `chignon`, `man_bun`, and `bald` |
| `bangs` | `none`, `wispy`, `full`, `side`, `curtain`, `long` |
| `part` | `center`, `left`, `right`, `none` (swept back) |
| `color` | A name or RGB |
| `wind` | Direction and strength pushing the hanging hair. `[0.5, 0, 0]` blows it to screen right |
| `face_framing` | 0 tucks the front hair behind the ears, 1 lets it fall beside the face. Default 0.2 |

- Hair grows along gravity after the pose is set, so it hangs naturally with the head bowed or the figure lying down
- Apart from the fringe, the engine pushes hair aside so it does not pass in front of the face
- Tied hair (`ponytail`, `bun`, `chignon`) never covers the face, so it is safe
- In short hair, a shell over the scalp carries the volume and the locks on top give the grain. Styled hair keeps its combed direction and hugs the head

## Hat (hat)

```json
"hat": "beanie"     or     "hat": {"style": "beanie", "color": [0.30, 0.10, 0.10]}
```

- `beanie`: a knitted beanie. Covers from above the forehead down to a line below the back of the skull, with the edge turned up. Vertical rib knit
- It sits over the hair. Long hair falls from under the beanie
- Default colour is a dark grey-black

## Beard (beard)

```json
"beard": "short_beard"
"beard": {"style": "full_beard", "color": "auburn"}
```

| Value | Shape |
| --- | --- |
| `none` | None (default) |
| `stubble` | Shadow of a shave. Darkest at the chin and round the mouth, fading toward the cheeks |
| `short_beard` | A short trimmed beard. From the sideburns to the chin |
| `full_beard` | A full beard falling below the chin |
| `goatee` | Round the mouth and chin |
| `mustache` | Moustache |

- The colour defaults to the hair colour. Stubble paint goes under the beard too, so its edge looks natural

## Outfits

### Presets

| Group | Names (ids in brackets are used for colour changes) |
| --- | --- |
| None | `figure_study` |
| Underwear, swimwear | `underwear` (bra, briefs), `briefs`, `trunks`, `swimsuit`, `bikini` (bikini_top, bikini_bottom) |
| Classical male figure study | `perizoma` (perizoma). A slanted loincloth worn low on the hips |
| Street | `hoodie_jeans` (hoodie, hood, pocket, cords, jeans, shoes; a loose hoodie with the hood down), `long_coat` (coat, lapels, sweater, trousers, boots; a knee-length wool coat with a turtleneck) |
| Everyday | `tshirt_jeans` (tshirt, jeans, shoes), `tank_shorts` (tank, shorts), `sportswear` (sports_top, leggings, shoes), `sweater_skirt` (sweater, skirt, boots), `blouse_trousers` (blouse, trousers, shoes), `office` (blouse, pencil_skirt, shoes), `shirt_trousers` (shirt, collar, trousers, belt, shoes; an open-collar shirt tucked into belted trousers), `suit` (jacket, lapels, shirt, tie, trousers, shoes) |
| Dresses | `sundress`, `summer_dress`, `little_black_dress` (dress), `evening_gown` (gown) |
| Traditional, classical | `chiton` (chiton, belt), `hanbok` (jeogori, chima), `kimono` (kimono_top, kimono_skirt, obi), `robe` (robe_top, robe_skirt) |
| Genre | `bodysuit`, `tactical` (bodysuit, vest, belt, boots) |

- Colour change: `"colors": {"dress": [0.8, 0.1, 0.2]}`
- A preset cut for a woman, given to a male build (`gender` under 0.5), switches to the men's version automatically
    + `sportswear` becomes a T-shirt and shorts, `swimsuit` swim trunks, `bikini` board shorts, `underwear` men's underwear
    + `blouse_trousers` and `office` become `shirt_trousers` (shirt and trousers)
    + Colours also apply through the original ids (`sports_top`, `leggings`, `swimsuit`, `bikini_bottom`, `blouse`)
    + To keep the original cut, build the outfit as an array of garment objects
- When sitting or kneeling, a skirt falls from the knees and spreads where it meets the floor
- Hands resting on thighs, hips or waist press the cloth and sit on top of the clothing (other people's hands too)
    + A hand tucked under the other arm, as in crossed arms, does not press the clothing

### Building an outfit

Give `outfit` an array of garment objects, from the innermost to the outermost

```json
"outfit": [
  {"type": "bottom", "id": "pants", "length": "full", "ease": 0.012, "color": [0.2, 0.2, 0.25]},
  {"type": "top", "id": "shirt", "sleeve": "elbow", "neckline": "v", "bottom": 0.28, "ease": 0.01, "folds": 0.005, "color": [0.9, 0.9, 0.88]},
  {"type": "footwear", "id": "shoes", "style": "ankle_boots", "color": [0.15, 0.1, 0.1]}
]
```

| type | Main fields |
| --- | --- |
| `top` | `sleeve` (none, cap, short, elbow, three_quarter, long), `neckline`, `top`, `bottom`, `ease`, `folds`, `drape` (how far the cloth bridges over muscle contours; jackets 40), `drape_floor` (how much ease stays above the shoulders, 0-1) |
| `bottom` | `length` (brief, short, bermuda, capri, full, footed), `top`, `ease`, `folds` |
| `skirt` | `length` (micro, mini, above_knee, knee, midi, ankle, floor), `flare`, `folds`, `fold_count`, `waist` (under 0.30 it sits on the hips), `wind`, `hem_slant` (a hem raised on one side) |
| `dress` | Uses the `sleeve` and `neckline` of `top` together with the fields of `skirt`. `bodice_folds` |
| `band` | `top`, `bottom`, `ease`. Belts, obi |
| `footwear` | `style` (shoes, ankle_boots, boots, socks, stockings) |
| `tie` | Necktie. `tip` (tip height), `ease` |
| `lapel` | A jacket's V lapel. `neckline`, `width`, `over_ease` and `drape` (same values as the jacket below), `gap` (height above the jacket) |

- `neckline`: `turtle`, `crew`, `boat`, `v`, `deep_v`, `scoop`, `square`, `straps`, `halter`, `strapless`, `one_shoulder`
- `top` and `bottom` are body height coordinates (metres)
    + 0.72 base of the neck, 0.66 shoulder, 0.58 armpit, 0.52 chest, 0.46 under the bust, 0.36 waist, 0.14 hips, 0.06 crotch, -0.28 knee, -0.74 ankle
- `ease` is the distance off the skin. For layered clothing, give the outer garment an `ease` at least 0.004 larger
- `folds` is fold depth (metres). 0.004 gives fine creases, 0.02 or more deep drapery
- Bending elbows and knees gathers folds in sleeves and trouser hems automatically. Looser clothing (larger `ease`) folds deeper
- Tops fit at the shoulder and loosen toward the bottom. The ease goes mostly below the bust and under the sleeves
    + So a loose shirt on a muscular build does not puff up at the shoulders like padding
- `drape` makes the cloth bridge hollows instead of following muscle contours
    + 40 is applied to the jacket and lapels of the suit preset
    + Sleeved tops with `ease` of 0.008 or more (blouses, T-shirts, sweaters) get 10 automatically, so the cloth settles over the shoulders
    + For a close-fitting top, set `"drape": 0`

## Make-up and eyes (look)

| Field | Default | Description |
| --- | --- | --- |
| `iris_color` | Brown | A name or RGB |
| `iris_size`, `pupil_size` | 1.08, 1.0 | Scale of iris and pupil |
| `catchlight`, `catchlight_size` | 0.95, 1.15 | Reflected light in the eye |
| `lip_color`, `lip_strength`, `lip_gloss` | Rose, 0.78, 0.45 | Lip colour, strength, gloss |
| `brow_color`, `brow_thickness`, `brow_arch` | From the hair colour, 1.15, 1.0 | Eyebrows |
| `lash_strength`, `lash_width`, `crease` | 0.9, 1.0, 0.45 | Lash line, its width, eyelid crease line |
| `eyeshadow_color`, `eyeshadow_strength` | Brown, 0.30 | Eyelids |
| `blush_color`, `blush_strength` | Pink, 0.20 | Cheeks |
| `contour` | 0.5 | Shading on the eyelids and under the cheekbones, highlights on the nose bridge and cheekbones. Facial modelling |
| `skin_gloss` | 0.16 | Skin sheen. At 0.4 or more cel styles draw glossy highlights |
| `flesh_variation` | 0.3 | Redness at joints, ears, nose tip and fingertips. 0.6 recommended for classical oil, 0.1 for cel |
| `nail_color`, `nail_strength` | Pale pink, 0.6 | Finger and toenails |
| `chest_tone_color`, `chest_tone_strength` | Rose, 0.40 | Chest tone tint in figure studies |
| `muscle_definition` | 0 | Relief of chest, abs, the pelvic V and shoulder blades. Shading depends on the light. Men 0.5 by default, muscular 1.0 |
| `body_relief` | 0.6 | Subtle relief of collarbones, spine and lower-back dimples. All figures |
| `stubble`, `beard_color` | 0, beard colour | Stubble strength and colour. Usually set by `beard` |

- Male presets default to natural lips, no eye make-up, dark brows and matte skin

## Common problems

| Symptom | Fix |
| --- | --- |
| Fringe covers the eyes | `bangs` to `wispy` or `none`, or tied hair |
| Hand buried in the body | `reach` `offset` to 0.04-0.06 (hands resting on clothing press the cloth automatically) |
| Two people seated opposite each other look away from each other | Give `facing` the table name instead of an angle |
| In a two-shot one person hides the other | `pairs` `facing` to 30-45, or adjust the camera `yaw` |
| Hand floats in the air | Replace the angles with `reach` |
| Arm twisted unnaturally | Change the `reach` `elbow` direction (from `down` to `out`, etc.) |
| A hand laid on the body looks like a claw | `"lay": true` on the `reach`, hand shape `rest` |
| Skin shows through clothing | Raise that garment's `ease` by 0.003 |
| Long hair sticks out from the shoulders | Lower `length_scale`, or set `style` to `shoulder` |
| Face seems to look upward | Add 5-10 to `head.nod`, camera `pitch` to 5 |
| Eyes clump black in full-figure shots | Line-drawing styles keep only the upper lash line on small eyes. If still too dark, `look.lash_strength` to 0.5, or `canvas.detail` to `fine` |
| A figure study looks flat | Pose `s_curve` or `arms_behind_head`, build `woman_fuller`, `look.skin_gloss` 0.3-0.45, lighting `three_quarter` + `warm` |
| A male upper body looks flat | Build `man_athletic`, `look.muscle_definition` 0.8-1.0, lighting `side` or `rembrandt` (relief shows best in side light) |
| Lower body of a male figure study | Classical: `perizoma`; modern: `briefs` or `trunks`. With `figure_study` the area is smooth, since the body model has no pelvic detail |
