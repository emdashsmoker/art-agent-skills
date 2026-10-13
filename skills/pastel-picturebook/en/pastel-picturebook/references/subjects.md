# Subject settings

Each subject chosen with `--subject` has a default settings file `assets/subject_<name>.json`. A user spec lists only the items to change. Inside the file, `spec` is the composition, `style` is the palette shared by all styles, and `style_<style>` holds overrides for that style only

## Contents

- figure (full-length figure)
- Scene composition (backdrop, companions, contact, props)
- hand
- still_life
- desk
- landscape
- beach
- city
- park, sakura (park and cherry-blossom path)
- rooftop, fireworks (sunset rooftop and fireworks riverside)
- panelka, outskirts (panel apartment blocks and outskirts field)
- cafe, room, bedroom, bathroom (interiors)
- weather

## figure (full-length figure)

The head uses the same structure as the portrait at a smaller size. Face, hair and palette items are the same as in `spec.md`

### Sex

| Key | Default | Description |
|---|---|---|
| `sex` | "female" | "male" uses the male body tables (`anatomy_body.MALE`, `anatomy_profile.MALE`) and the male preset |

- Male body: wide shoulders and chest, narrow waist and pelvis, thick neck and limbs, pectorals, abdominals, V line above the pelvis, trapezius and latissimus in the back view
- Male profile: brow ridge, straight nose, forward chin, Adam's apple, deep chest, flat belly, small buttocks, short hair
- `figure.shape` multipliers apply to both sexes

### Composition

| Key | Default | Description |
|---|---|---|
| `pose.head_center` | [0.50, 0.105] | Screen position of the midpoint between the eyes. A larger vertical value moves the figure down |
| `pose.head_unit` | 0.060 | Head unit size (fraction of the image width). 0.060 is full length, 0.085 is a knee-up framing |
| `figure.body_scale` | 1.0 | Body size relative to the head. 0.9 is 6.8 heads tall, 1.0 is 7.4, 1.05 is 7.7 |
| `figure.neck_shift` | 0.05 | How far the neck sits sideways off the head centre |
| `figure.floor` | {"y": 0.84} | Floor line height (fraction of the image height). null omits the floor. Side views use {"at_feet": true} to match the soles |
| `figure.view` | "front" | "front", "back" (back view), "side" (profile facing screen right, flipped with `pose.mirror`) |

### Body shape

| Key | Default | Range | Description |
|---|---|---|---|
| `figure.shape.shoulders` | 1.0 | 0.9-1.1 | Width multiplier for the shoulders and upper chest |
| `figure.shape.bust` | 1.0 | 0.8-1.2 | Bust size multiplier |
| `figure.shape.waist` | 1.0 | 0.9-1.15 | Waist width multiplier |
| `figure.shape.hips` | 1.0 | 0.9-1.12 | Pelvis and hip width multiplier (also buttock size in back and side views) |
| `figure.shape.thighs` | 1.0 | 0.9-1.12 | Thigh thickness multiplier |
| `figure.shape.legs` | 1.0 | 0.95-1.1 | Leg length multiplier |

### Pose

`figure.pose`. Angles are how far a limb swings outward from hanging straight down (degrees). Left and right are screen directions

| Key | Default | Description |
|---|---|---|
| `shoulder_tilt`, `pelvis_tilt` | 3, -6 | Tilt of the shoulder line and the pelvis line. Opposite signs give contrapposto |
| `arm_left`, `arm_right` | | Angles of `upper` (upper arm), `fore` (forearm), `hand`, and the optional items `foreshorten` [upper, fore], `toward` [upper, fore], `over` (lies over the other arm), `behind_clothes` (a hand behind the body hides behind the skirt and coat) |
| `leg_left`, `leg_right` | | Angles of `thigh`, `shin`, `foot`, and the optional items `foreshorten`, `toward` |
| `hand_left`, `hand_right` | "relaxed" | Hand pose name: `open`, `relaxed`, `victory`, `peace` (wide V for figure scale), `point`, `grip`, `fist`, `tucked` (hidden) |
| `hand_left_view`, `hand_right_view` | "back" | "palm" shows the palm (thumb on the other side). For waving and the V sign |
| `turn` | 0 | Body turn (degrees). Three-quarter full-length view (section below) |
| `stride` | none | Walking toward the viewer. {"lead": "left" or "right", "amount": 0-1, "arms": true} (section below) |
| `figure.holds` | | Objects held in the hands. {"right": {"kind": "cup"}, "left": {"kind": "book"}}. Optional `size`, `offset` [x, y] (head units), `group` (palette) |

- Hand on the hip: `upper` 28, `fore` -45, `hand` -32, `foreshorten` [1.0, 0.75]
    + The forearm tilts into the picture and looks shorter, so `foreshorten` shortens it by that much
- The weight-bearing leg has `thigh` around 0, and the resting leg has `thigh` 5-8 and `shin` around -8
- `toward` marks which way a shortened bone points (1 toward the viewer, 0 in the picture plane, -1 behind the body)
    + A bone toward the viewer rises forward and covers the body behind it, its top faces the light, and its near end looks larger
    + A bone behind the body is hidden by the torso and head, and only its visible part is drawn
    + Without `toward`, `foreshorten` only shortens the length
- Pose examples

| Pose | Values | Example |
|---|---|---|
| Arms crossed | Both arms `upper` 12-14, `fore` -92 to -96, `foreshorten` [0.72, 0.9], `toward` [1, 0]. Upper arm `"over": true`, lower hand `"tucked"` | `example_spec_figure_male_arms_crossed.json` |
| Hands behind the head | Both arms `upper` 150, `fore` -78, `foreshorten` [1.0, 0.55], `toward` [0, -1] | `example_spec_figure_hands_behind_head.json` |
| Hands behind the back | Both arms `upper` 8, `fore` -38, `foreshorten` [1.0, 0.55], `toward` [0, -1] | `example_spec_figure_male_hands_behind_back.json` |
| Holding a cup | `upper` 10, `fore` -128, `foreshorten` [1.0, 0.55], `toward` [0, 1], hand `"grip"`, `holds` cup | `example_spec_figure_holding.json` |
| Holding a book | Hanging arm, hand `"grip"`, `holds` book | `example_spec_figure_holding.json` |

- A held object sits behind the hand. The fingers wrap a cup in front of the torso with the handle on the side away from the wrist. The fingers grip the top edge of a book and lie over the cover

- When the upper arm passes 90 degrees, the shoulder joint rises upward and inward (a raised shoulder)
- A forearm coming toward the viewer gets its outline drawn over its own upper arm

### Hand targets and arms in front of the face

Giving an arm `reach` makes the code solve the upper arm and forearm angles so the middle of the palm lands on that point (two-joint inverse kinematics). Repeated renders to tune `upper` and `fore` are not needed

| Arm key | Description |
|---|---|
| `reach` | {"mark": name} a point on the figure's own body, {"at": [x, y]} a screen fraction (in picture coordinates after any mirroring), {"mark": name, "of": "main" or a companion index} a point on another figure (scenes only). Optional `offset` [dx, dy] (head units, in the figure's own direction) |
| `bend` | Elbow direction. "out" (default, away from the body), "in", "down", "up", "straight" (a straight arm shortened toward the viewer until it reaches) |
| `hand` | When given, fixes the hand direction at this angle (fingers hanging down, as for a hand on a shoulder). Without it, the hand follows the forearm direction plus `wrist` (degrees) |
| `foreshorten`, `toward` | Applied as usual. The solve uses the shortened bone lengths |
| `front` | true repaints the forearm and hand (sleeve included) after the head. The hand comes in front of the face and hair and casts a hand shadow on the face |

- An arm with `reach` does not inherit the preset arm's angles and foreshortening (the right arm default is a hand on the hip)
- Point names
    + Head: `chin`, `mouth`, `cheek_left`, `cheek_right`, `temple_left`, `temple_right`, `crown` (above the top of the head)
    + Body: `shoulder_*`, `elbow_*`, `wrist_*`, `hand_*`, `hip_*`, `knee_*`, `ankle_*` (* is left or right), `pit`, `bust`, `waist`, `navel`, `hips`
    + Aiming at the other arm's `elbow_*`, `wrist_*` or `hand_*` places that arm first and then solves (a hand supporting the elbow of the arm that props the chin)
- For poses with the hand near the face, shorten the upper arm toward the viewer so the elbow comes down: `foreshorten` [0.45-0.55, 1.0], `toward` [1, 0]
- When the hand is very close to its own shoulder, the target is closer than the difference of the two bone lengths and the arm cannot fold. Shorten the forearm too (`foreshorten` [0.6, 0.7], `toward` [1, 1]) or move the target away from the shoulder
- Pose examples

| Pose | Values | Example |
|---|---|---|
| Waving | `reach` {"mark": "temple_right", "offset": [1.6, -0.3]}, `bend` "down", hand `open`, `hand_right_view` "palm" | `example_spec_figure_wave.json` |
| V sign | `reach` {"mark": "cheek_right", "offset": [1.15, 0]}, `bend` "down", `foreshorten` [0.45, 1], `toward` [1, 0], `wrist` -25, `front` true, hand `peace`, palm | `example_spec_figure_peace.json` |
| Stretching | Both arms `reach` {"mark": "crown", "offset": [±0.15, -0.6]}, `bend` "out", one arm `over` | `example_spec_figure_male_stretch.json` |
| Chin in hand (standing) | Right arm `reach` {"mark": "chin", "offset": [0, 0.45]}, `foreshorten` [0.55, 1], `toward` [1, 0], `front` true, hand `fist`. Left arm `reach` {"mark": "elbow_right", "offset": [-0.2, 0.35]} | `example_spec_figure_thinking.json` |

### Body turn (three-quarter view)

`figure.pose.turn` (degrees) rotates the torso about its vertical axis for an oblique full-length view. Positive values turn the front of the body toward screen right

- The visible width of the torso section (an ellipse) becomes sqrt((width cos)^2 + (depth sin)^2)
- The joints (shoulders, pelvis, limbs) sit on the body's middle plane, so their horizontal positions narrow by cos
- Front features (breasts, navel, collarbones, neckline, buttons, zip) shift toward the turning side by front depth x sin. The far breast meets the outline
- The far arm passes behind the torso and shows only where it leaves the outline (an arm placed with `reach` is drawn in front as an exception). The near leg comes in front of the far leg
- Turn the head with `pose.yaw_deg` as well (about 0.7 times the body `turn`, 22 or less)
- Clothing uses the same keys. Only the front view (`figure.view` "front") is supported
- Recommended range -35 to 35
- Examples: `example_spec_figure_three_quarter.json` (woman, 30 degrees), `example_spec_figure_male_three_quarter.json` (man, -30 degrees, jacket)

### Seated pose (front)

| Key | Description |
|---|---|
| `figure.seat` | Draws a bench. `half_width` (half width in head units, default 2.2), `board` (top thickness, 0.45), `leg` (leg thickness, 0.28). null omits it |
| Legs | Positive `thigh` spreads the knees, negative brings them together. `foreshorten` [0.30-0.40, 1.0], `toward` [1, 0] |
| Arms | Hands on the thighs: `upper` 8-14, `fore` -18 to 0, `foreshorten` [1.0, 0.70], `toward` [0, 1] |

- The thighs come toward the viewer, so the knee outline is drawn over the shin and the thigh outline over the belly
- Depth cues are added automatically
    + (Perspective) The thigh widens toward the knee, and the shin and foot grow by the knee's depth
    + (Top surface) The upward-facing top of the thigh gets top light. It brightens toward the knee and near the thigh ridge
    + (Creases) A crease where the thigh meets the torso, and shade under the knee
- A seated thigh is pressed by the seat and its section becomes wide and flat
- Trousers bulge at the knee by the thigh width, and the top above the knee brightens
- `figure.clothes.drape` turns into a lap cloth in the seated front view
    + It wraps the pelvis, covers the thighs and knees, then sags between the knees. The knot ends rest on the thigh
    + The hands are drawn over the cloth
- Examples: `example_spec_figure_seated_front.json` (female nude), `example_spec_figure_male_seated_front.json` (male, clothed), `example_spec_figure_male_seated_front_nude.json` (male nude, lap cloth)
- Seated test: only a leg whose thigh comes more than half its length toward the viewer gets the knee outline, top light, creases and bulging trousers

### Front walk

`figure.pose.stride` sets a walk toward the viewer in one go. A front walk is mostly a change in depth (one leg toward the viewer, one behind), so angles alone do not show it

| Key | Default | Description |
|---|---|---|
| `lead` | "left" | The leg stepping forward (screen side) |
| `amount` | 1.0 | Stride. Multiplies how much the bones are shortened |
| `arms` | true | Arm swing. The arm on the lead-leg side swings back and the other swings forward (elbow slightly bent, shortened toward the viewer). A hand that swings back hides behind the skirt and coat |

- Lead leg: the thigh comes a little toward the viewer and the foot plants
- Back leg: the heel lifts so the ankle rises about 0.5 head units and the foot looks short. Its outline stays behind the lead leg
- With `stride`, the values of both legs come from `stride`. An arm placed with `reach` does not swing and stays where it is
- Trousers, skirts and coats use the same keys as standing
- Use a full-length framing so the walking legs show: with the eyes at 0.40, `head_unit` 0.034-0.036 fits down to the feet
- Examples: `example_spec_figure_front_walk.json` (woman), `example_spec_scene_snow_night.json`, `example_spec_scene_umbrella_rain.json` (a couple walking toward the viewer)

### Side poses

When `figure.view` is "side", use `figure.profile_pose`

| Key | Default | Description |
|---|---|---|
| `lean` | 0 | Tilt of the whole body (degrees) |
| `arch` | 0 | Back arch (0-1). The chest comes forward and the buttocks back |
| `arm` | | `upper` and `fore` angles of the near arm. Positive is forward |
| `leg_near`, `leg_far` | | `thigh` and `shin` angles of the near and far legs. The far leg is drawn darker and behind |
| `hand` | "relaxed" | Hand pose name |
| `arm_far`, `hand_far` | none | `upper` and `fore` angles and hand pose of the far arm. Drawn darker behind the body. Used for walking |
| `seat` | false | true gives a pose seated on a chair. The buttocks and the underside of the thighs flatten on the seat |
| `wall` | none | true or {"width", "gap"}. Raises a pillar behind the body and aligns its edge with the rearmost point among the back, the buttocks and a foot set against the wall (`width` 4.5 head units). Colour `style.palette.wall` |
| `lift` | 0 | Distance from the soles to the floor and shadow (head units). Airtime for jumps and runs |
| Leg `foot` | 0 | Foot rotation at the ankle. Positive points the toes down (a foot kicked back, tiptoe) |
| Arm `reach`, `bend`, `front` | | Hand target of the near arm. Points `chin`, `mouth`, `cheek`, `brow`, `crown`, `knee`, `ankle` or {"at": [x, y]}. In scenes, {"mark": name, "of": partner} aims at the partner side figure's `nape`, `upper_back`, `lower_back`, `shoulder`, `hip`, `mouth` and so on. `bend` is "forward", "back", "down", "up". `front` true brings the forearm and hand in front of the face (chin in hand), and "arm" also brings the upper arm in front of the figure's own face and neck (an arm around the partner's neck) |

- The side head uses its own profile outline, and `hair.length`, `hair.wave` and `hair.tip_split` apply
    + Profile proportions: the eye is an almond set inward from the nose bridge (thick upper lid line, lash tips sweeping back), the lips and chin sit behind the nose tip, sideburns in front of the ear
    + When the front view has `hair.bangs`, fringe locks come over the forehead from the crown
    + The male uses a short-hair outline, so `hair.length` does not apply
- Side seated values
    + Legs: near leg `thigh` 84-86, `shin` 4-8, far leg `thigh` 78-80, `shin` -6 to -10
    + Arm: `upper` 10-16, `fore` 72-76 (the hand rests on the thigh)
    + `lean` positive leans forward, negative leans back
    + Floor: `figure.floor` {"at_feet": true}
- Examples: `example_spec_figure_seated_side.json` (woman), `example_spec_figure_male_seated_side.json` (man)
- Side walk values: near leg `thigh` 22, `shin` 4, far leg `thigh` -16, `shin` -30, near arm `upper` -22, far arm `upper` 24, `fore` 38, `lean` 2 (example `example_spec_figure_male_walk.json`)
- Side angles are relative to the body. When the body leans by `lean`, the bone angle seen on screen is (set angle - `lean`)
- Side action values

| Action | Values | Example |
|---|---|---|
| Run | `lean` 12, `lift` 0.6, near leg `thigh` 67 `shin` -13 `foot` 20, far leg `thigh` -20 `shin` -125 `foot` 60, near arm `upper` -40 `fore` 40, far arm `upper` 55 `fore` 130, hand `fist` | `example_spec_figure_side_run.json` |
| Jump | `lean` -6, `lift` 2.4, both arms `upper` 145-160 `fore` 165-172, legs `thigh` 4-24 `shin` -86 to -100 `foot` 34-40 | `example_spec_figure_male_side_jump.json` |
| Crouch | `lean` 30, legs `thigh` 128-135 `shin` 15-18 `foot` -8 to -10, arm `reach` {"mark": "knee", "offset": [0.7, 1.3]} `bend` "forward" | `example_spec_figure_side_crouch.json` |
| Kneeling sit | `lean` 2, legs `thigh` 68-70 `shin` -90 `foot` 172 (instep on the floor), arm `upper` 6 `fore` 48 (hand on the thigh), bare feet with `shoes` false | `example_spec_scene_picnic_kneel.json` |
| Cross-legged sit | `seat` true, `lean` -4, near leg crossed on top `thigh` 94 `shin` 12 `foot` 25, lower leg `thigh` 84 `shin` -4, arm `upper` 8 `fore` 60 (hand on the knee) | `example_spec_scene_cross_legs.json` |
| Leaning on a wall | `wall` true, `lean` -6, `arch` 0.6, near leg set against the wall `thigh` 36 `shin` -88 `foot` 88, standing leg `thigh` 6 `shin` -4, arm `upper` -8 `fore` -10 (hand toward the wall) | `example_spec_scene_lean_wall.json` |

- Raising the thigh forward more than 30 degrees (except when seated) straightens the buttock outline
- Folding the knee more than 140 degrees (kneeling) splits the trouser leg into two tubes, thigh and shin, which cover the inside of the fold
- Side skirt and dress hems fall vertically relative to the standing body. Trousers or shorts suit side poses that sit or kneel
- A long sleeve on a side arm raised more than 18 degrees covers up over the shoulder
- Side figures use the same clothing keys as the front. To put an object in a side figure's hand, use the key "near" in `holds` (example `example_spec_figure_side_holding.json`)

### Looking back over the shoulder

A back-view (`figure.view` "back") figure with `figure.look_back` true or {"side": "left"}

- The body is drawn in back view and the head in profile. The nose, lips and chin sit on the outline, so the face turned over the shoulder is not cut off
    + By default the figure looks back toward screen right (its right shoulder). "left" turns the other way
    + The profile head sits 0.30 head units toward the turning side and 0.20 down from the eyes, so the back-view neck joins under the chin and ear
    + Long hair flows from the back of the head down over the back, and ponytails and fringes follow the profile rules
- Values: `pose.yaw_deg` 0, `roll_deg` 4-8 (the head tips toward the shoulder it turns over)
- Turning a front face more than 30 degrees pushes the face outside the head outline and it looks cut off, so do not use it for looking back
- Example: `example_spec_scene_look_back.json` (looking back on the cherry-blossom path)

### Lying poses

The side figure is drawn in a frame rotated 90 degrees and then rotated back so it lies down. The light source and background are rotated into the same frame, so they match the scene light

| Key | Description |
|---|---|
| `figure.lying.face` | "up" (lying on the back, head to the left) or "down" (lying face down, head to the right). Use `pose.mirror` for the other direction |
| `figure.lying.ground` | Height of the ground the body touches (fraction of the image height, default 0.80). The lowest point of the body (the back, or the elbows and thighs) is aligned here |

- Use with `figure.view` "side". `profile_pose` angles are read as for a standing pose
    + The upper side of the lying body (screen top) is the front of the body for "up" and the back of the body for "down"
- `pose.head_center` and `pose.head_unit` refer to the finished picture
- Lying on the back reduces the breast projection to 0.8 times. A contact shadow falls on the ground under the body
- Without a background, the ground colour is painted from `ground` down over the style's background colour. With a background subject (beach, room and so on), the figure lies on top of it
- Pose values
    + Lying with knees up: near leg `thigh` 55 `shin` -40 `foot` -20, far leg straight, arm `upper` 20 `fore` 45 (hand on the thigh)
    + Lying face down on the elbows: `lean` -25, legs `thigh` -25 and `shin` -70 to -100 (feet raised), arm `upper` 65 `fore` 155, head `roll_deg` -55
- The hair flows toward the body and spreads on the ground. For long hair lying face down, a ponytail or a bob looks natural
- Examples: `example_spec_figure_lying_back.json`, `example_spec_figure_lying_front.json`, `example_spec_scene_beach_lying.json`

### Clothing

| Key | Description |
|---|---|
| `figure.clothes.dress` | Sleeveless dress. `strap_outer`, `strap_inner` (strap positions), `neck_level` (neckline depth), `hem_level` (skirt hem height, 9.3 is above the knee), `hem_half` (half width of the hem), `folds` (number of folds), `fold_depth` |
| `figure.clothes.shirt` | T-shirt, shirt. `ease` (looseness), `neck_half` (half width of the neck opening), `neck_level` (neckline height), `hem_level` (hem height), `sleeve` (sleeve length: 0-1 is a fraction of the upper arm, 1-2 runs down the forearm, 1.9 is above the wrist), `group` (palette, default `cloth`) |
| `figure.clothes.pants` | Trousers and belt. `waist_level`, `hem_drop` (length below the ankle), `leg_widths` [hip, knee, hem], `length` (1 is full-length trousers, 0.42 is shorts) |
| `figure.clothes.skirt` | Skirt. `waist_level` (default 3.55), `hem_level`, `hem_half`, `folds`, `fold_depth`, `group` (default `skirt`) |
| `figure.clothes.jacket`, `coat` | Outer layer over the shirt. `ease`, `hem_level` (6.7 is a jacket, above 7.0 gives flaring coat tails), `hem_half`, `button_level` (bottom of the front V opening), `buttons`, `sleeve`, `group` (default `jacket`) |
| `figure.clothes.jeogori` | Hanbok jacket. `ease`, `hem_level` (women 1.95, men 5.4), `sleeve`, `sleeve_hang` (the sleeve's lower curve hanging down, head units), `goreum_length` (length of the ribbon ties), `trim_group` (palette for the collar and ties, default `goreum`) |
| `figure.clothes.chima` | Hanbok skirt. `top_level` (above the bust, default 0.95), `hem_half`, `hem_drop` (length below the ankle), `folds` |
| `figure.clothes.baji` | Hanbok trousers. `waist_level`, `leg_widths` [hip, knee, above the ankle band, ankle band] |
| `figure.clothes.drape` | Cloth wrapped around the pelvis (a classical figure-study convention). `top_level`, `bottom_level`, `knot` (knot side, -1 left, 1 right), `slant` (how much longer the knot side hangs) |
| `figure.clothes.hoodie` | Hoodie. Hood folded around the neck (on the upper back in the back view), kangaroo pocket, drawstrings, ribbed hem and cuffs. `ease` (default 0.16), `hem_level` (default 5.0), `sleeve` (default 1.96), `group` (default `hoodie`). true uses the defaults |
| `figure.clothes.swimsuit` | One-piece swimsuit. Low neckline and straps, high-cut leg line, deep back opening in the back view. `neck_level` (1.05), `strap_aside` (0.70), `leg_cut` (how far the leg line rises from below the pelvis, 0.55), `back_level` (back opening, 2.6), `group` (default `swim`) |
| `figure.clothes.underwear` | Underwear. Women get a strap bra (cups covering the breasts, an underband, a light trim above the cups) and briefs (a light waistband, a front bow). Men get fitted trunks (short legs, a wide elastic waistband). `bottom_level` (waist line of the women's briefs, default 4.7). Men take the trouser keys (`waist_level` 4.95, `length` 0.24, `leg_widths`). `group` (default `underwear`). true uses the defaults. Shared by front, back and side views |
| `figure.clothes.bikini` | Bikini. Halter-neck triangle cups with an underband, low-rise bottoms. `bottom_level` (waist line of the bottoms, default 4.9), `group` (default `swim`) |
| `figure.clothes.trunks` | Men's swim trunks. Mid-thigh length, a drawstring knot at the waistband. Takes the trouser keys as they are (`waist_level` 4.85, `length` 0.32, `leg_widths`), `group` (default `swim`) |
| `figure.clothes.shoes` | true paints the feet in the shoe colour |
| `figure.clothes` | null gives a nude study |

- Heights (`*_level`) are head units measured along the torso spine. 4.85 is the belt, 5.45 the pelvis, 6.5 the crotch
- The male preset turns on `shirt`, `pants` and `shoes` and sets `dress` to null
    + A male nude is `{"shirt": null, "pants": null, "shoes": false}`. To wrap the pelvis in cloth, add `drape`
- Painting order (inside to outside): underwear, swimsuit, bikini, drape, trousers, swim trunks, hanbok trousers, skirt, hanbok skirt, shirt, dress, hoodie, jeogori, jacket, coat, bags and scarves. Then the arms are placed back over the clothes and the sleeves are painted
- To dress a man in a hoodie, turn off the default T-shirt: `{"shirt": null, "hoodie": true}`. Swim trunks are `{"shirt": null, "pants": null, "shoes": false, "trunks": true}`
- Swimsuits cling to the body. They follow its curves and do not hang from the chest like loose clothes
- Colours: dress and T-shirt `style.palette.cloth`, trousers `pants` (with `belt`, the women's default is denim), skirt `skirt`, jacket and coat `jacket` (with `button`), jeogori `jeogori`, hanbok skirt `chima`, hanbok trousers `baji`, collar and ties `goreum`, white collar strip `dongjeong`, drape `drape`, hoodie `hoodie` (with `string` for the drawstrings), swimsuit `swim` (with `string`), underwear `underwear` (with `trim` for the trim and `band` for the men's waistband, dark grey in the male preset), shoes `shoe`, chair `seat`, cup `cup` (with `drink`), book `book` (with `pages`)
- Patterns (stripes, check, dots) are applied by putting `pattern` in any of the palette groups above (Patterns in `references/spec.md`)
- Accessories (glasses, hats, scarves, bags) use the top-level `accessories` key (accessories in `references/spec.md`)
- Clothing examples: `example_spec_figure_shirt_skirt.json`, `example_spec_figure_coat.json`, `example_spec_figure_male_jacket.json`, `example_spec_figure_male_shorts.json`, `example_spec_figure_hanbok.json`, `example_spec_figure_male_hanbok.json`, `example_spec_figure_side_hanbok.json`, `example_spec_figure_hoodie.json` (hoodie, hat, bag), `example_spec_figure_side_hoodie.json` (side hoodie, beanie, glasses), `example_spec_figure_swimsuit.json` (striped swimsuit, wide-brimmed hat), `example_spec_figure_bikini.json` (polka-dot bikini), `example_spec_figure_male_trunks.json` (striped swim trunks, cap), `example_spec_figure_patterns.json` (striped shirt, check skirt, scarf)
- Nude study examples

| File | Content |
|---|---|
| `example_spec_figure_nude.json` | Woman, front, knee-up framing, contrapposto with a hand on the hip |
| `example_spec_figure_back.json` | Woman, back view |
| `example_spec_figure_side.json` | Woman, side, arched back |
| `example_spec_figure_male_nude.json` | Man, front, pelvis drape |
| `example_spec_figure_male_back.json` | Man, back view |
| `example_spec_figure_male_side.json` | Man, side, near leg stepping forward |
| `example_spec_figure_male_seated_front_nude.json` | Man, seated front, lap cloth |

### Rendering strength

`style.body_render`

| Key | Description |
|---|---|
| `figure_level`, `figure_spread` | Amount of body shadow and width of its edge. Raising `figure_level` widens the shadow |
| `cloth_level` | Amount of clothing shadow |
| `skin_sheen` | Skin sheen. 0 is matte |
| `accent` | Strength of anatomical accents such as the collarbones, navel and knees. 0 omits them. In line-art styles, men also get strokes for the line under the pectorals, the abdominals and the V line |
| `top_light` | Strength of the top light on the thigh tops in the seated front view. Default 0.55, painterly 0.8 |

## Scene composition (backdrop, companions)

Keys placed in portrait and full-length figure specs. The background is drawn first, then the companions, and the main figure last in front

| Key | Description |
|---|---|
| `backdrop.subject` | Subject used as the background (`city`, `landscape`, `beach`, `park`, `sakura`, `rooftop`, `fireworks`, `cafe`, `room`, `bedroom`, `bathroom`, `desk`, `still_life`, `figure` and so on). The image size follows the main figure |
| `backdrop.spec` | Settings for the background subject. Leave `light` empty to use the main figure's light |
| `backdrop.place` | "horizon" puts every figure's eyes on the background horizon (city, landscape, cafe, room), because a standing adult's eyes are at the camera's eye height |
| `backdrop.blur` | Background blur (fraction of the image width). About 0.006 gives a blurred background behind a portrait |
| `backdrop.fade` | {"color", "amount"}. Pulls the background toward one colour so the figure stands out |
| `companions` | A list of other figure specs. Each item takes `subject` (default `figure`), `sex`, `pose.head_center`, `pose.head_unit` and so on. Farther figures are drawn first |
| `grade` | {"color", "amount"}. Tints the figures with the background light (about 0.3 blue-violet for a night street, about 0.18 warm orange for a room at night) |
| `weather` | {"kind": "rain", "snow", "petals"}. With an outdoor background, rain, snow or petals fall in front of the figures too. With an indoor background (cafe, room), they fall only outside the window |
| `pose.horizon_drop` | In "horizon" placement, lowers only this figure's eyes by this fraction of the image height (a shorter person, a leaning head) |
| `props` | List of props shared by several figures (section below) |
| Companion `lift` | Lifts parts of this figure back over figures drawn after it (section below) |

- On a background, the floor is not repainted. Only the shadows under the feet are added (when `figure.floor` is set)
- Figure size is set with `head_unit`. With the eyes on the horizon, size stands for distance
- Full-length fit: with the eyes at 0.40, `head_unit` 0.044, and at 0.42, about 0.040
- Drawing order follows the `companions` list, with the main figure last (frontmost)
- For a mirrored figure (`pose.mirror`), the `head_center` x is given before mirroring. To stand it at screen x 0.67, use 0.33
- Examples: `example_spec_scene_city_night.json`, `example_spec_scene_pair.json`, `example_spec_portrait_city_bokeh.json`, `example_spec_scene_cafe.json` (a figure in a cafe on a rainy day), `example_spec_scene_room_night.json` (a room at night), `example_spec_portrait_cry_rain.json` (crying portrait on a rainy night street)

### Contact between figures

- Holding hands: both figures' hands aim at the same screen point. `reach` {"at": [x, y]}, `bend` "straight", hands `grip` (the hand on top) and `relaxed`
    + The hand of the figure drawn later lies on top
- Hand on the partner's body: `reach` {"mark": "shoulder_right", "of": "main", "offset": [-0.1, 0.0]}
    + The scene stands the partner figure first, reads the point, and converts it to a screen position
    + Two arms aiming at each other form a cycle, so holding hands uses the same `at` point
- Front-back overlap: list the parts to lift again in the companion's `lift`
    + "hand_<side>", "forearm_<side>" (forearm and hand, with sleeve), "arm_<side>" (the whole arm)
    + {"part": "forearm_right", "from": 0.7} lifts only from 70% along the forearm to the hand
    + The lifted area is limited to pixels the figure actually painted. In the band outside the part, only the outline follows (only pixels darker than what lies below)
    + With the companion's `lift_under_head` true, the lifted part passes under the face and fringe of the figure drawn later
- Arm over the shoulder: draw the hugging person first as a companion and extend the arm `straight` to the partner's far shoulder. `hand` around 10 lets the fingers hang in front of the shoulder, with `lift` {"part": "forearm_right", "from": 0.7} and `lift_under_head` true
    + The arm passes behind the partner's neck and back, and only the sleeve end and hand come out again under the far-side hair
    + `from` around 0.7 lifts only the sleeve end and hand, so the arm emerges from under the hair
- Hand on the arm (arm in arm): make the hand's owner a companion with `reach` {"mark": "elbow_right", "of": "main", "offset": [0.3, -0.3]}, `bend` "down", `foreshorten` [1.0, 0.6], `toward` [0, 1], `hand` 80, `lift` {"part": "forearm_left", "from": 0.5}
    + About 0.17 of the image width between the two heads straightens the arm so the hand comes out of the sleeve
- Leaning: turn the leaning person's `roll_deg` toward the partner (negative for a partner on the left), move the body the other way with `figure.neck_shift` 0.5-0.8, and set `figure.pose.neck_lean` around -0.3 and `horizon_drop` around 0.02
- Turning the bodies toward each other (`turn` ±10-15) makes a two-shot look natural
- Examples: `example_spec_scene_beach.json` (holding hands, waving), `example_spec_scene_snow_night.json` (walking with an arm over the shoulder, leaning), `example_spec_scene_umbrella_rain.json` (walking under an umbrella with a hand on the arm), `example_spec_scene_bench.json` (holding hands and leaning on a bench)

### Scenes with several people (group photo, toast, dance, selfie)

- A front figure's `arm_left` is the arm on screen left and `arm_right` the arm on screen right. To reach toward the middle, the left figure uses `arm_right` and the right figure uses `arm_left`
- Elbow direction (`bend`) "out" points outward on that arm's side, and "in" toward the body's middle. For the right figure's `arm_left`, "out" points toward the middle of the group
- Drawing order: the person putting an arm around someone's shoulder goes first (earlier among the companions), the person the arm passes behind is drawn later, and `lift` brings only the hand back up
- For four people standing in front view on a landscape image (1600x1200), use `head_unit` 0.030 and about 0.16 of the image width between people. When a hand target is beyond arm length (about 6 head units), the arm stops at full extension

| Scene | Setup | Example |
|---|---|---|
| Three friends' group photo | The middle figure (companion 0) has both arms `reach` {"mark": "shoulder_left", "of": 1} and {"mark": "shoulder_right", "of": "main"}, `bend` "straight", `lift` both hands (`"hand_left"`, `"hand_right"`), `lift_under_head` true, sleeve 1.6. The two side figures make a V sign with the outer hand (`reach` {"mark": "cheek_left", "offset": [-1.15, 0]}, `foreshorten` [0.45, 1], `toward` [-1, 0], hand `peace`) | `example_spec_scene_friends_photo.json` |
| Toast for four | Each of the four has `holds` {"kind": "glass"} in the inner hand, hand `grip`, arm `reach` {"at": a point above the heads}. The inner two raise their glasses just above their own shoulders so the glasses touch, and the outer two raise theirs above the gap between their own head and the neighbour's | `example_spec_scene_toast_party.json` |
| Couple dance | The side man's near arm and the front woman's arm aim at the same point above the heads (`at`) and hold hands. The woman's other arm spreads to the side (`upper` 62 `fore` 40), with a wide dress hem (`hem_half` 3.2, `folds` 7) | `example_spec_scene_dance_rooftop.json` |
| Selfie | Two faces close together (0.18 of the image width apart), `roll_deg` toward each other. One person reaches toward a bottom corner off screen (`reach` {"at": [0.06, 0.93]}, `foreshorten` [1.0, 0.7]) with `holds` {"kind": "phone"}, and the other makes a V sign | `example_spec_scene_selfie_fireworks.json` |

### Hug and kiss (side)

Two side figures facing each other. The near arm wrapped around the partner shows in front of the partner (toward the viewer)

- Placement: one faces right, and the other faces left with `pose.mirror` true. The arm of the main figure, drawn later, lies over the partner as it is
- Kiss
    + Both have `expression` "kiss"
    + Heads: the taller one bows toward the partner (the mirrored figure takes a positive `roll_deg` around 18), and the shorter one lifts the head (around -14)
    + Match `head_center` x so the two mouth points (`mouth`) overlap, and match `horizon_drop` so the soles (`soles`) rest on the same floor
- Arm around the waist (main figure): arm `reach` {"mark": "lower_back", "of": 0, "offset": [-0.25, 0]}, `bend` "down", hand `relaxed`
- Arm around the neck (companion): arm `reach` {"mark": "upper_back", "of": "main", "offset": [-0.35, 1.3]}, `bend` "up", `front` "arm"
    + Companion `lift` ["arm_near"] with `lift_under_head` true lifts the whole arm back over the partner while it passes under the partner's face and hair
    + The lower the hand target moves down the partner's upper back, the lower the elbow, which then rests in front of the neck under the partner's chin
- Tiptoe: leg `foot` 25-30
- Additional side points: `mouth`, `nape` (back of the neck), `upper_back` (shoulder blades), `lower_back` (small of the back)
- Examples: `example_spec_scene_embrace.json` (bedroom at night, in underwear), `example_spec_scene_embrace_bath.json` (bathroom)

### Scene props (props)

Props shared by several figures. The scene measures the figures to set size and position, and draws the props in the background stage of the first figure drawn

| `kind` | Keys | Description |
|---|---|---|
| `bench` | `on` (default all figures), `backrest` (default true), `overhang` (length past the hips, 2.0 head units) | A long bench with a backrest spanning from the hips to the knees of figures seated in front view. The figures' `figure.seat` is null |
| `table` | `on`, `elbow_of` (top at this figure's elbow height), `above_seat` (top height, 3.4 head units above the seat), `x` (screen fraction), `radius` (2.7 head units), `cups` (list of cup positions, head units from the centre) | A round cafe table between figures seated in side view. It stands in the middle between the knees |

- A seated eye height is lower than the camera eye height, so cafe scenes set the background camera `horizon_y` to the seated eye height and use a small head unit (about 0.028 at 1600x1200)
- Examples: `example_spec_scene_bench.json`, `example_spec_scene_cafe_date.json`

### Umbrella

{"kind": "umbrella"} in `figure.holds`. It stands from the handle in the hand up to the canopy above the head

| Key | Default | Description |
|---|---|---|
| `radius` | 4.4 | Canopy radius (head units). About 4.4 covers two people |
| `rise` | 4.9 | Height from the hand to the canopy rim (head units) |

- A dome seen from below, the inner surface visible between the scalloped edges, ribs, a hook handle and a tip
- It is drawn after the head, so the canopy lies over the hair and the companions. Make the figure holding the umbrella the main figure
- In rain, no streaks fall on the canopy or on the shaft area under it (the edge fades softly). The grey light and mist stay
- To place the handle between two faces, give the hand target with `at`. Keep at least 0.15 of the image width between the two heads so the shaft does not cross a face
- Hand held at chest height: `bend` "down", `foreshorten` [1.0, 0.65], `toward` [0, 1], `front` true. The upper arm hangs at the side with the elbow at the flank, and the forearm rises to the handle
    + The hand target is about 0.05 of the image width from the figure's own shoulder toward the partner, slightly below the shoulder
- Colours: `style.palette.umbrella` (`base`, `shadow`, `light`, `line`, `inner` for the inner surface, `shaft` for the shaft)
- Example: `example_spec_scene_umbrella_rain.json`

### Wine glass, phone, cigarette

{"kind": "glass"} or {"kind": "phone"} in `figure.holds`. Hand pose `grip`

| `kind` | Keys | Description |
|---|---|---|
| `glass` | `drink` (drink colour, default "#A3263A" red wine), `size` | A wine glass held by the stem. A clear bowl and wine above the fist, the foot below |
| `phone` | `turn` (tilt in degrees), `size` | A phone seen from the back (two camera lenses). The hand taking a selfie |
| `cigarette` | `point` (1 or -1, direction of the lit end), `lit`, `smoke`, `size` | A cigarette held between the index and middle fingers, with smoke. Hand pose `relaxed`. The four fingers are laid back over it, so it comes out from between them |

- Colours: `style.palette.glass` (`base` glass tint, `light` reflection, `line`, `drink`), `style.palette.phone` (`base`, `shadow`, `line`, `lens`)

## hand

| Key | Description |
|---|---|
| `hands` | List of hands. Each item has `pose`, `x`, `y` (wrist position, screen fraction), `size` (hand length, fraction of the image height), `angle` (rotation, 0 is fingertips up), `mirror` (the other hand), `view` ("back" for the back of the hand, "palm" for the palm), `sex`, `width` (hand width multiplier) |
| `sex` | Default sex for all hands. "male" gives a broad hand (`width` 1.15), thick knuckles, short pale nails and veins on the back of the hand |

- Pose names: `open`, `relaxed`, `victory` (V), `point`
- To add a pose, add three joint bend angles per finger, `spread` and `thumb` (thumb fold) to `POSES` in `scripts/anatomy_hand.py`
- The palm view swaps the thumb side and draws palm lines, wrist creases and fleshy pads (nails omitted)
- Male hand example: `example_spec_hand_male.json`

## still_life

Positions and sizes are fractions of the image width. Objects are drawn from back to front in order of their base height

| Key | Description |
|---|---|
| `table.back_y`, `table.front_y` | Back and front edges of the table top |
| `cloth` | Cloth `left`, `right`, `drop` (hanging length), `folds`. Remove the item to omit the cloth |
| `objects` | List of objects |

| `kind` | Required | Optional |
|---|---|---|
| `bottle`, `vase`, `jar`, `cup` | `x`, `base_y`, `height`, `radius`, `group` | `gloss`, `shininess`, `label` {`top`, `bottom`} |
| `bowl` | `x`, `rim_y`, `radius`, `depth`, `group` | `fruit`: a list of `ball` items with `dx`, `dy` from the bowl centre |
| `ball` | `x`, `base_y`, `rx`, `ry`, `group` | `angle`, `stem`, `tips` (lemon tips), `gloss` |
| `pear` | `x`, `base_y`, `height`, `radius`, `group` | `tilt_deg` |
| `ashtray` | `x`, `base_y`, `radius` | `butts` (number of butts), `lit` (a lit cigarette resting on the rim), `smoke`, `group` (default `ashtray`, with the `ash` colour) |
| `tea_glass` | `x`, `base_y`, `radius`, `height` | `handle` ("right", "left"). Black tea (`tea`) in a glass set in a metal holder (`holder`), with a spoon |
| `can` | `x`, `base_y`, `radius`, `height` | `group` (default `can`, with the `band` stripe colour) |

- `group` is the name of a colour group in `style.palette`. Add a new colour as a group with `base`, `shadow`, `deep`, `light`, `line`
- Shiny materials like glass take `gloss` 0.8 or more and `shininess` 80 or more
- `wall_items` [{"kind": "window", "x0", "x1", "y0", "y1", "block_top", "columns", "lit"}]: a night window in the back wall. Outside it are the wall of the apartment block opposite and a few lit windows, plus the window frame and sill (colour `window`)
- Example: `example_spec_still_life_kitchen_night.json` (a kitchen table at night, `--style doomer`)

## desk

The desk is placed in a 3D space in centimetres (X right, Y up, Z into the picture) and projected by a camera looking down from above

| Key | Description |
|---|---|
| `camera` | `position` [x, y, z] (cm), `pitch_deg` (downward angle), `focal` (field of view), `center_x`, `center_y` (image centre) |
| `room` | `window_glow` (brightness of the window-side wall), `screen_spill` (how far screen light spreads onto the desk) |
| `desk` | `width`, `front_z`, `back_z`, `thickness`, `grain` (wood grain strength) |
| `objects` | List of objects. Common keys `kind`, `x`, `z` (cm) |

| `kind` | Items |
|---|---|
| `monitor` | `width`, `height`, `lift` (stand height), `foot`, `angle`, `on` |
| `laptop` | `width`, `depth`, `open_deg` (screen opening angle), `angle`, `on`, `keys` |
| `keyboard` | `width`, `depth`, `angle` |
| `mouse` | none |
| `phone` | `width`, `depth`, `angle`, `on` |
| `mug` | `radius`, `height`, `steam` |
| `plant` | `radius`, `height`, `leaves` |
| `lamp` | `reach` (horizontal distance to the lamp head, negative is left), `height`, `on` |
| `notebook` | `width`, `depth`, `angle` (pen included) |

- Screen content is drawn as a simple app screen (top bar, sidebar, two cards, lines of text). Colour `style.palette.screen`
- A lit screen and a desk lamp are treated as light sources and light the desk around them
- For a dark room, darken the wall, desk and device colours and raise `screen_spill`, as in `example_spec_desk_night.json`

## landscape

Vertical positions are fractions of the image height, and horizontal positions fractions of the image width

| Key | Description |
|---|---|
| `horizon_y` | Waterline height |
| `sky` | `sun_x`, `sun_y`, `sun_r`, `clouds` (0-1, cloud amount), `birds` (number of birds) |
| `ranges` | List of mountain ranges from far to near. `group` (colour group), `amplitude` (height), `roughness` (0.4 gentle, 0.6 rugged), `snow` (snow line), `forest` (forest sawtooth spacing), `haze` (haze strength) |
| `water` | `ripple` (reflection wobble), `glitter` (number of sun glints), `streaks` (number of ripple streaks) |
| `bank` | Near shore `top_y`, `amplitude`, `dip`, `grass`, `rocks` [[x, size], ...] |
| `pines` | List of conifers [[x, height], ...] |

- The time of day is set by the three colours `top`, `middle`, `horizon` of `style.palette.sky`
- The mountain shapes change with `seed`

## beach

Painted from far to near: sky, sea up to the horizon, breaking wave foam, wet and dry sand, palm trees. Vertical positions are fractions of the image height, and horizontal positions fractions of the image width

| Key | Description |
|---|---|
| `horizon_y` | Horizon height. With `backdrop.place` "horizon", standing figures' eyes come here |
| `sky` | `sun_x`, `sun_y`, `sun_r`, `clouds` (same as the landscape) |
| `sea` | `shore_y` (waterline height), `waves` (number of ripples), `glitter` (number of sun glints) |
| `sand` | `ripples` (number of wind ripple marks) |
| `palms` | List of palms [[x, base y, height, lean], ...]. Height is a fraction of the image height, and lean is the horizontal shift relative to the height |

- The sea is deep toward the horizon and turns pale turquoise toward the shore. The waterline curves gently
- The wet sand band catches the sky light and is bright, and the faint line of the next wave shows above the foam line
- Colours: `style.palette.sky`, `sea` (`deep`, `shallow`, `light`, `glitter`, `foam`), `sand` (`far`, `near`, `wet`, `shadow`), `palm` (`trunk`, `trunk_shadow`, `leaf`, `leaf_shadow`, `line`)
- Examples: `example_spec_scene_beach.json`, `example_spec_scene_beach_lying.json` (`backdrop.subject` "beach")

## city

The street is laid out in 3D in metres and then projected in perspective

| Key | Description |
|---|---|
| `camera` | `vanish_x`, `horizon_y` (vanishing point position), `focal` (field of view, larger is more telephoto), `eye_height` (eye height, m) |
| `street` | `road_half_width`, `building_line` (distance to the building line), `length` (street length), `haze`, `building_depth` [min, max], `building_height` [min, max], `crosswalk_z`, `pole_spacing`, `tree_spacing` |
| `sky.clouds` | Cloud amount (0-1) |

- The building layout changes with `seed`

### Night view

| Key | Default | Description |
|---|---|---|
| `night.on` | false | Turns on the night view |
| `night.lit` | 0.45 | Fraction of lit windows |
| `night.shops` | 0.85 | Fraction of lit shops |
| `night.stars` | 260 | Number of stars |
| `night.cars` | 3 | Cars per lane (receding cars show tail lights, approaching cars headlights) |
| `night.wet` | 0.75 | Strength of wet road reflections. 0 is a dry road |

- The night colours `style.palette.city_night`, `foliage_night` and `trunk_night` override the day colours
- Signs, windows, street lamps and car lights bloom and leave vertically smeared reflections on the road
- Colours in `style.palette.city`: `walls` (list of wall colours), `awnings`, `signs`, `shade_tint` (shade tint), `haze`
- The sunlit side is set by the sign of the `light` x

## park, sakura (park and cherry-blossom path)

Outdoor ground seen from a standing person's eye height. It uses the same centimetre units as the interiors (X right, Y up, Z into the picture) and a level camera, so paths converge to one vanishing point on the horizon and trees shrink with distance. Both subjects use the same module (`scripts/subject_park.py`) and differ only in their default setup

| Subject | Default setup |
|---|---|
| `park` | Picnic lawn. Mown striped grass, wild flowers, grass blades in front, a far forest band, scattered green trees, a checked picnic blanket and a basket |
| `sakura` | Cherry-blossom path. A paved walk running to the horizon, cherry trees planted in pairs on both sides forming a blossom tunnel that meets overhead, fallen petals on the ground, a pinkish far forest band. A standalone render includes drifting petals (`weather` "petals") |

| Key | Default | Description |
|---|---|---|
| `camera` | `eye_height` 155, `horizon_y` 0.42 (park), 0.47 (cherry path), `focal` 0.70-0.75 | The same camera as the interiors |
| `sky` | | The same sky as the landscape (`sun_x`, `sun_y`, `sun_r`, `clouds`) |
| `haze` | {"distance": 9000, "amount": 0.6} | How much far trees are covered with sky colour (distance in cm) |
| `treeline` | | Far forest band above the horizon {"lift", "amplitude", "crown", "group" ("treeline" green, "blossom_far" pink), "haze"} |
| `lawn` | | {"stripes" (mown stripe width in cm, 0 for none), "blades" (number of grass blades in front), "flowers" (number of wild flowers)} |
| `path` | none (cherry path {"half_width": 180}) | A paved path running from the front of the picture to the vanishing point. Paving joints and kerbstones |
| `avenue` | none (cherry path) | Trees planted in pairs on both sides of the path {"kind" ("sakura", "green"), "offset" (cm from the path edge to the trunk), "first_z", "last_z", "spacing"} |
| `trees` | 4 trees in the park | List of single trees [{"x", "z", "kind", "size"}] |
| `blanket` | park | Picnic blanket {"x", "z", "width", "depth", "turn_deg", "check" (check size in cm)} |
| `basket` | park | Basket with lid and handle {"x", "z", "turn_deg"} |
| `petals` | none (cherry path) | Fallen petals on the ground {"ground" (count), "far" (scatter distance in cm)} |
| `time` | "day" | In daytime, trees cast dappled shade on the ground |

- Trees: a trunk leaning toward the path and forked branches carry a rounded canopy made of several clumps. Branches and sky show through gaps inside the canopy. Cherry trees add bright clusters of blossom and dark shaded gaps
- To place a kneeling or seated figure on the blanket, lower the camera (`eye_height` about 100) and set the figure's `horizon_drop` (by how much the eyes sit below the camera)
- Colours: `sky`, `treeline`, `blossom_far`, `lawn` (`far`, `near`, `stripe`, `shadow`, `blade`, `blade_light`), `path` (`base`, `far`, `seam`, `kerb`), `blossom`, `foliage` (`base`, `shadow`, `light`, `line`), `trunk`, `blanket` (`white`, `check`, `deep`), `basket`, `basket_lid`, `petal`, `flower`
- Examples: `example_spec_scene_friends_photo.json` (group photo on the cherry path), `example_spec_scene_look_back.json` (looking back on the cherry path), `example_spec_scene_picnic_kneel.json` (kneeling on the picnic blanket)

## rooftop, fireworks (sunset rooftop and fireworks riverside)

`scripts/subject_skyline.py`. A city skyline seen from a standing person's eye height. Building fronts are rectangles parallel to the picture, and depth comes from rows of buildings layered one behind another

| Subject | Default setup |
|---|---|
| `rooftop` | Sunset. A sky shifting from violet to gold, the sun setting between buildings, long clouds turned gold near the sun, dark backlit buildings with rim light on their tops, a concrete tile floor, a glass railing, a string of bulbs overhead, planters |
| `fireworks` | Riverside at night. Stars, four fireworks, lit high-rises, a river reflecting the buildings and fireworks and stretching their light downward, a stone-paved promenade and railing |

| Key | Description |
|---|---|
| `time` | "sunset" or "night" |
| `sky` | `sun_x`, `sun_y`, `sun_r` (screen fractions), `clouds` (0-1), `stars` (number of night stars) |
| `fireworks` | List of fireworks [{"x", "y", "r" (screen fractions), "color", "kind", "rays", "tail"}]. `kind` "trail" (chrysanthemum of light streaks), "dots" (peony of star grains), "willow" (drooping willow). `tail` true adds a rising tail |
| `skyline` | List of building rows from the farthest [{"z" (cm), "height" (range of top heights above the floor in cm), "width", "gap", "haze", "base"}]. Some buildings have stepped upper floors or antennas (red aviation lights at night) |
| `lit` | Fraction of lit windows (default 0.12 at sunset, 0.5 at night) |
| `river` | River {"z0", "z1" (far bank in cm), "level" (water level in cm), "ripple", "waves"} |
| `floor` | {"kind": "roof" or "promenade", "tile" (cm)} |
| `railing` | {"z", "wall" (height of the low wall in cm), "height" (handrail height), "posts" (post spacing), "glass" (glass between posts)} |
| `lights` | Strings of bulbs [{"from": [x, y, z], "to": [x, y, z], "sag", "bulbs"}] |
| `plants` | Floor planters [{"x", "z", "radius", "height"}] |

- At sunset the floor gets a warm path of light from the sun toward the viewer, and at night the floor is faintly tinted with firework colours
- With figures standing in the scene, `grade` {"color": "#FFB98A", "amount": 0.22} suits the sunset light and about {"color": "#B9A8E8", "amount": 0.2} suits the fireworks
- When the horizon moves, move the `y` of the sun and fireworks too so buildings do not hide them
- Colours: `sky` (`top`, `middle`, `low`, `horizon`, `glow`, `sun`, `cloud`, `cloud_warm`, `cloud_lit`, `night_top`, `night_middle`, `night_low`), `city` and `city_night` (`face`, `shade`, `haze`, `base`, `glass`, `window_lit`, `rim`, `beacon`), `water`, `floor`, `railing` (`wall`, `cap`, `metal`, `shine`, `glass`), `lights`
- Examples: `example_spec_scene_dance_rooftop.json` (dance on the sunset rooftop), `example_spec_scene_selfie_fireworks.json` (fireworks selfie)

## panelka, outskirts (panel apartment blocks and outskirts field)

`scripts/subject_blocks.py`. The stage for the film-night style. It uses the same centimetre level camera as the park and the rooftop, so figures can stand on the horizon

| Subject | Default setup |
|---|---|
| `panelka` | A block courtyard at night. Panel apartment blocks of 9-12 floors on three sides (panel joints, rain stains, a window grid with only some windows lit, TV-lit windows, balconies, entrance lamps), snowy ground and a trodden path, utility poles and sagging wires, sodium street lamps and pools of light, bare birches, a swing. A standalone render includes snow (`weather` "snow") |
| `outskirts` | Edge of town at dusk. A dry grass field and a dirt path, a line of pylons to the horizon with three sagging wires, a far row of apartment blocks, warm light on the horizon, crows |

| Key | Description |
|---|---|
| `time` | "night" or "dusk" |
| `camera` | The same camera as the interiors (`horizon_y`, `focal`, `eye_height`, `x`) |
| `sky` | `clouds` (0-1, low stratus), `stars` |
| `haze` | {"distance", "amount"}. How much far buildings are covered with sky colour |
| `ground` | `snow` (true for snow, false for dry grass), `path` ([[x, z], ...] path centreline), `width` (path width in cm), `ruts` (list of wheel rut x positions), `stalks` (number of grass stalks) |
| `blocks` | List of buildings. {"face": "front", "z", "x0", "x1"} is a wall facing the viewer, and {"face": "side", "x", "z0", "z1"} a side wall running into the picture. Common keys `floors` (number of floors), `lit` (fraction of lit windows, 0.18 at night), `balconies` (fraction of window columns with balconies), `doors` (number of entrances, with entrance lamps at night), `salt` (random seed for the window layout) |
| `poles`, `wires` | Utility poles [{"x", "z", "height"}]. Wires sag between neighbouring poles and off screen (`wires.sag`, `wires.count`) |
| `lamps` | Street lamps [{"x", "z", "height", "arm" (1 for an arm to the right, -1 to the left)}]. At night the lamp head glows and a pool of light falls on the ground |
| `birches` | Birches [{"x", "z", "height"}]. Black marks on white trunks and recursive branches |
| `swing` | Swing {"x", "z"}. null turns it off |
| `pylons` | A line of pylons {"x", "z0", "spacing", "count", "height", "drift", "sag"} |
| `crows` | {"perched": crows on the wires, "flying": crows in flight} |

- Street between blocks: place side-wall buildings in turn on both sides of the path, make `ground.path` a straight wide road, and add wheel ruts with `ruts` (example `example_spec_panelka_street.json`)
- Placing figures: a full-length fit is eyes at 0.38-0.40 with `head_unit` 0.036 at 1200x1600, and eyes at 0.40 with 0.019 at 1600x1200. To stand a figure small and far away, as in a world establishing shot, use camera `focal` 0.45 and `head_unit` 0.0065
- Colours: `sky` (`night_*`, `dusk_*`, `haze_*`), `ground` (`snow_*`, `grass_*`, `path`, `path_dirt`, `rut`, `stalk`, `stalk_light`), `block` (`wall`, `shade`, `day`, `glass`, `lit`, `lit_amber`, `tv`, `balcony`, `door`), `lamp` (`head`, `pool`, `glow`), `pole` (`base`, `wire`, `metal`, `crow`), `birch` (`bark`, `mark`, `twig`)
- Examples: `example_spec_scene_doomer_man.json`, `example_spec_scene_doomer_woman.json`, `example_spec_scene_doomer_pair.json`, `example_spec_scene_doomer_world.json`, `example_spec_panelka_street.json`

## cafe, room, bedroom, bathroom (interiors)

An interior seen from a standing person's eye height. The room is a box in centimetres (X right, Y up, Z into the picture) and the camera looks level, so all lines running into the picture converge to one vanishing point on the horizon. The four subjects use the same module (`scripts/interior.py`) and differ only in their default setup

| Subject | Default setup |
|---|---|
| `cafe` | A window onto the street, a counter and espresso machine, round tables, chairs, pendant lights, a menu board, shelves |
| `room` | Living room. Curtained window, sofa, bookshelf, rug, low table, floor lamp, potted plant |
| `bedroom` | Bedroom (night by default). A bed with a headboard (pillows, a turned-down duvet), two nightstands with table lamps, a curtained window on the left wall, a framed picture over the bed, a rug, a potted plant |
| `bathroom` | Bathroom (day by default). Wall tiles up to waist height, floor tiles, a bathtub, a washbasin and mirror, wall lamps, a glass shower stall, a towel rail |

| Key | Default | Description |
|---|---|---|
| `camera.eye_height` | 150 | Camera height (cm). A standing adult's eye height |
| `camera.horizon_y` | 0.46 | Horizon (vanishing point) height, fraction of the image height. Adjust it together with `backdrop.place` "horizon" when standing figures in the room |
| `camera.focal` | 0.62 | Focal length (fraction of the image width). Smaller is wider |
| `camera.center_x`, `camera.x` | 0.5, 0 | Horizontal position of the vanishing point, and the camera's sideways position (cm) |
| `room.width`, `room.height`, `room.depth` | 640, 300, 600 (cafe), 620, 270, 600 (room) | Room size (cm). The camera is at the front centre |
| `room.floor` | "tiles" (cafe, bathroom), "planks" (room, bedroom) | Floor: checked tiles (`tile` size) or floorboards (`plank` width) |
| `room.wall_tiles` | none (bathroom {"height": 130, "size": 30}) | Covers the three walls from the floor up to `height` (cm) with tiles of `size` |
| `time` | "day" | "night" darkens the room and puts a night view outside the window, and lit lamps warm the room |
| `weather` | none | {"kind": "rain" or "snow"}. Visible only outside the window |
| `items` | per subject | List of furniture and wall decorations (table below) |

| `kind` | Position keys | Other keys |
|---|---|---|
| `window` | `wall` ("back", "left", "right"), `a0`, `a1` (X range on the back wall, Z range on side walls), `y0`, `y1` | `panes` [columns, rows], `view` ("street" for buildings, "trees" for trees), `curtains`, `frame` (frame thickness in cm) |
| `frame` | Same as window | Framed abstract picture |
| `menu` | Same as window | Chalk menu board |
| `shelf` | `a0`, `a1` | `levels` (list of shelf heights in cm). A wall shelf holding bottles and cups |
| `counter` | `a0`, `a1`, `z` (front face) | `depth`, `height`, `machine` (espresso machine), `cups` |
| `table` | `x`, `z` | `radius`, `height` (74 for a cafe table, 45 for a living-room table), `cups` |
| `chair` | `x`, `z` | `angle` (0 puts the backrest on the far side, 180 on the near side) |
| `stool` | `x`, `z` | `height`, `radius` |
| `sofa` | `x`, `z` (front face) | `width`, `depth`, `angle` |
| `bookshelf` | `x`, `z` (front face) | `width`, `height`, `depth`, `shelves` |
| `rug` | `x`, `z` (front edge) | `width`, `depth` |
| `plant` | `x`, `z` | `radius`, `height`, `leaves` |
| `floor_lamp` | `x`, `z` | `height`, `on` (by default lit only at night) |
| `pendant` | `x`, `z` | `drop` (length hanging from the ceiling), `radius`, `on` |
| `bed` | `x`, `z` (foot end) | `width` (160), `length` (205), `headboard` (headboard height 115), `duvet_share` (fraction of the length the duvet covers, 0.70). The headboard is set against the back wall |
| `nightstand` | `x`, `z` (front face) | `width`, `depth`, `height` (55). One drawer |
| `table_lamp` | `x`, `z`, `y` (height it stands at) | `on` (by default lit only at night) |
| `bathtub` | `x`, `z` (front face) | `width` (170), `depth` (75), `height` (55). A tub inside a surround, with a faucet |
| `vanity` | `x`, `z` (front face) | `width`, `depth`, `height` (82). Two-door cabinet, counter top, basin and faucet |
| `shower` | `a0`, `a1` (X range), `z` (glass face) | `height` (200). A shower head on the back wall and a glass partition in front |
| `mirror` | Same as window | Thin metal frame and streaks of reflected light |
| `sconce` | `wall`, `a`, `y` | `on` (on by default). Wall lamp |
| `towel` | Same as window | A towel on a rail (striped) |

- Floor objects are drawn from far to near, so overlaps come out right on their own. Rugs always lie at the bottom
- Keep the spot where a figure will stand (within 2 m of the camera) clear. Default setups place objects at Z 220 and beyond
- Colours: `room_wall` (`base` back wall, `shadow`, `ceiling`, `line`), `room_floor` (`base`, `shadow`, `alt` tiles, `line`, `cast` shadows), `room_trim` (window frames, skirting boards), `outside` (day and night colours outside the window, `sun` for sunlight on the floor), `desk` (wooden top), `counter`, `chair`, `sofa`, `shelf_wood`, `books`, `rug` (`border`, `motif`), `curtain`, `board` (`chalk`), `art`, `jars`, `lamp` (`bulb` for bulb light), `shade`, `mug`, `device`, `leaf`, `pot`
    + Bedroom: `bed_wood` (bed frame, nightstands), `headboard`, `sheet`, `duvet`, `pillow`
    + Bathroom: `room_tile`, `porcelain` (bathtub, washbasin), `vanity`, `metal` (faucets, frames), `mirror` (`top`, `bottom`, `gleam`), `glass` (`opacity`), `towel` (`stripe`)
- Moving the camera sideways (`camera.x`) reveals the bed behind a figure standing in the middle (-110 in the hug example)
- Examples: `example_spec_cafe_night_rain.json`, `example_spec_room_snow.json`, `example_spec_bedroom_day.json`, `example_spec_bathroom_night.json`, `example_spec_scene_cafe.json`, `example_spec_scene_room_night.json`, `example_spec_scene_embrace.json` (bedroom), `example_spec_scene_embrace_bath.json` (bathroom)

## weather

Top-level `weather` in the spec. It can be added to any subject

| Key | Default | Description |
|---|---|---|
| `kind` | | "rain" (grey light, light mist, slanting streaks), "snow" (bright mist, flakes small and sharp in the distance and large and blurred up close), "petals" (drifting cherry petals, pink ellipses turned at various angles, small and sharp in the distance and large and blurred up close) |
| `amount` | 1.0 | Amount of streaks and flakes, and strength of the colour shift |
| `wind` | 12 | Streak slant (degrees) |

- Outdoor subjects (city, landscape and so on) and figures standing on them get weather across the whole picture. Rain or snow also falls in front of the figures
- Interiors (cafe, room) and figures with an interior background get weather only inside the window glass
- When a figure holds an umbrella, no streaks or flakes fall on the umbrella or under it
- Examples: `example_spec_city_rain.json`, `example_spec_landscape_snow.json`, `example_spec_cafe_night_rain.json`, `example_spec_room_snow.json`, `example_spec_scene_friends_photo.json` (petals)
