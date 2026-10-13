# Full body spec reference

When the spec has a `figure` key, the full body rig runs. Face and hair use the same `character` and `palette` keys as the bust. Gender is set with `character.gender`.

## Contents

- Structure
- figure keys
- Build
- Framing
- Pose presets
- Setting poses directly
- Furniture
- Profile
- Back view
- Hands
- Props (cigarette)
- Outfits
- Figure study
- Background people (extras)
- Two-shot (duo)
- Coordinates for the mixed mode

## Structure

- A full body is built on a 2D skeleton
    + A few angles set the joint positions
    + Limbs are shapes hung between 2 joints, and width curves make the shoulder, elbow, knee and calf contours
    + The torso is one curve joining the chest frame and the pelvis frame
    + Outfits are body parts widened outward
- Each gender has its own body plan
    + Female : hourglass silhouette, barefoot height about 7.2 heads, about 7.5 heads in high heels
    + Male : inverted triangle of wide shoulders and narrow hips, thick neck and limbs, large hands and feet, barefoot height about 7.4 heads
- The length unit is the head unit (crown to chin = 1.0)
- Left and right are always screen based (`left` = screen left)
- Face, hair and skin tone are set with the same `character` keys as the bust (character table of `portrait-spec.md`)
    + The 12 hair styles, `skin_tone`, `eye_shape`, `brow_shape`, `nose_shape`, `mouth_shape` all apply to the front, profile and back view rigs
    + In back views `two_block` is drawn as a short-cut band of back hair, and `pixie` and `layered` as pointed hair ends at the nape
    + In profile the nose and mouth presets change the face outline itself (`dot` nose lower, `bridge` nose higher, `heart` lips fuller)

## figure keys

| Key | Default | Description |
|---|---|---|
| `pose` | "standing" | Pose preset name |
| `pose_overrides` | {} | Pose items written over the preset |
| `outfit` | female "dress", male "shirt_pants" | 20 outfits (outfit table below), `bikini` is an alias of `swimsuit` |
| `build` | {} | Body scale factors (table below) |
| `heels` | false | High heels. The feet extend downward and the legs look longer |
| `ground_shadow` | none | Shadow under the feet (0.3-0.6), for scenes with a floor |
| `furniture` | pose default | `stool`, `chair`, `sofa`, `pillar`, `bed`, `none` |
| `furniture_color` | furniture default color | Furniture base color |
| `facing` | "right" | Profile poses only, `right` or `left` |
| `look` | pose default | Back view poses only, `away` (back of the head), `left`, `right` (looks back in profile), `left_3q`, `right_3q` (looks back in three-quarter) |
| `cigarette` | none | Where the cigarette is held, `left`, `right` (that hand), `mouth` (mouth corner). Props section below |

## Build

`build` values are scale factors on the gender's default body; 1.0 is the default.

| Key | Recommended range | Effect |
|---|---|---|
| `bust` | 0.8-1.25 | Breast volume for women, chest muscle size for men. 0 removes the chest shading |
| `waist` | 0.9-1.1 | Waist width. Lower makes the curves stronger |
| `hips` | 0.9-1.15 | Width of the hips and the top of the thighs |
| `shoulders` | 0.9-1.1 | Shoulder width |
| `legs` | 0.95-1.1 | Leg length |
| `muscle` | 0.8-1.4 | Limb thickness and muscle shading strength. Male abs and chest muscles deepen with it |

- Curvy female build example : `{"bust": 1.08, "waist": 0.96, "hips": 1.04}`
- Muscular male build example : `{"muscle": 1.3, "shoulders": 1.05}`
- Changing a factor by more than 0.1 at once easily misaligns outfit shapes, so check after rendering

## Framing

Framing is set in one of 2 ways.

- (Framing preset) `placement.shot` : name where the bottom edge of the picture crops the character. Size and position are computed automatically
- (Direct setting) `placement.head_height` and `pelvis` : set head size and pelvis position as canvas fractions

### Framing presets (shot)

| shot | Bottom edge of the picture | Use |
|---|---|---|
| `full` | Floor under the feet (5% margin top and bottom) | Full body, seated full body, two-shot full body |
| `thigh` | Middle of the thighs | Pictures where figure and outfit are the subject |
| `knee` | Just below the knees | Standard upper body close-up of a standing character |
| `waist` | Below the hips | Upper body and face, two-shot conversation scenes |
| `bust` | Below the chest | A bust drawn with the full body rig (with hand gestures) |

- The margin above the crown is fixed at 5% of the canvas height; with hands raised over the head (`stretch`, `wave`) it is measured from the fingertips
- `placement.x` : horizontal position of the character center (center of both characters in a two-shot), canvas fraction, default 0.5
- With `shot`, `head_height` and `pelvis` cannot be used too (stops with an error)
- Example : `"placement": {"shot": "thigh", "x": 0.45}`
- A Dutch angle that tilts the picture is set with `finish.tilt` (degrees, positive is counterclockwise, 3-8 recommended) and zooms in automatically so no empty corners appear

### Direct setting

`pelvis` is the canvas fraction coordinate of the pelvis center.

| Framing | canvas | head_height | pelvis |
|---|---|---|---|
| Full body (female) | [1100, 1800] | 0.115 | [0.5, 0.47] |
| Full body (male) | [1100, 1800] | 0.110 | [0.5, 0.48] |
| Full body + high heels | [1100, 1800] | 0.112 | [0.5, 0.46] |
| Seated full body | [1100, 1700] | 0.150 | [0.5, 0.53] |
| Seated full body on a sofa | [1600, 1500] | 0.135 | [0.5, 0.56] |
| Profile walking | [1600, 1300] | 0.112 | [0.47, 0.50] |
| Profile sitting | [1300, 1500] | 0.130 | [0.5, 0.55] |
| Profile sofa | [1600, 1400] | 0.125 | [0.48, 0.57] |
| Profile leaning on a pillar | [1300, 1800] | 0.110 | [0.52, 0.48] |
| Back view full body | [1100, 1800] | 0.112 | [0.5, 0.50] |
| Back view sitting | [1300, 1700] | 0.130 | [0.5, 0.56] |
| Knee up | [1200, 1600] | 0.19-0.20 | [0.5, 0.80] |
| Upper body | [1200, 1500] | 0.30 | [0.5, 1.19] |

- Reference distances (head units, from the pelvis center)

| Position | Female | Male |
|---|---|---|
| Crown | 3.29 up | 3.30 up |
| Eyes | 2.77 up | 2.78 up |
| Soles | 3.89 down (high heels 4.15) | 4.12 down |

- Eye y coordinate = pelvis y - 2.77 x head_height
- Face detail survives when the head is 250 pixels tall or more

## Pose presets

| Name | Content | Default furniture |
|---|---|---|
| `standing` | Basic stance close to attention | |
| `contrapposto` | Weight on one leg, right hand on the waist | |
| `akimbo` | Both hands on the waist | |
| `wave` | Right hand raised in greeting | |
| `clasped` | Both hands joined in front | |
| `peace` | Right hand V sign beside the face, the arm drawn in front of the hair | |
| `pinup` | One hand behind the head, the other on the raised hip. S curve | |
| `walk` | Walking seen from the front | |
| `sitting` | Seated with knees together and both hands on the knees | `stool` |
| `sitting_crossed` | Seated with the screen-right leg crossed over the other knee, both hands on the upper knee | `stool` |
| `three_quarter` | Three-quarter with the body turned about 30 degrees | |
| `lean` | Diagonal stance with the screen-left shoulder leaning on a pillar and ankles crossed | `pillar` |
| `side_stand` | Standing in profile (profile rig) | |
| `side_walk` | Walking in profile, front heel landing and back leg pushing (profile rig) | |
| `side_sit` | Sitting upright in profile, both hands on the thighs (profile rig) | `stool` |
| `side_wave` | Standing in profile, raising the near hand with the palm turned outward to greet (profile rig) | |
| `side_lounge` | Sitting in profile with the back against the sofa back cushion, knees forward and both hands on the thighs (profile rig) | `sofa` |
| `side_lean` | Standing in profile with the back against a pillar, the far sole pressed to the pillar (profile rig) | `pillar` |
| `back_stand` | Standing with the back turned, the back of the head showing (back view rig) | |
| `back_lookback` | Weight on one leg with the hip out, looking back over the shoulder (back view rig) | |
| `back_walk` | Walking away, the raised foot shows its sole (back view rig) | |
| `back_sit` | Seated seen from behind, shins showing below the seat, hands on the knees hidden (back view rig) | `stool` |
| `arms_crossed` | Arms crossed. The screen-left hand hides under the other arm and the screen-right hand grips the other upper arm | |
| `pockets` | Standing with both hands in pockets. The wrists are covered by the outfit | |
| `stretch` | Stretching with both arms over the head and wrists crossed | |

- Presets fit both genders. Hand positions adjust to the gender's body automatically
- `three_quarter` turns only the body, so set the face direction separately with `character.head_turn`
- `pockets` puts the hands into pockets on outfits with pockets (`dress`, `blouse_skirt`, `sweater_pants`, `suit`, `shirt_pants`, `tshirt_jeans`, `crop_hotpants`, `hoodie_jeans`, the 6 v9 outfits with pants or shorts)
    + Outfits without pockets (`bodycon`, `knit_dress`, `swimsuit`, `trunks`, `lingerie`, `none`) lower relaxed hands diagonally away from the body
- `arms_crossed` reads best in upper body framing (`thigh`, `knee`, `waist`) because the arms pass in front of the torso
- `stretch` raises the hands over the head, so with `shot` the framing adjusts automatically to keep the fingertips in the picture

## Setting poses directly

Put the items below in `pose_overrides` to modify a preset (front rig). Profile pose items are in the profile section.

| Item | Description |
|---|---|
| `spine`, `chest`, `neck` | Tilt of waist, upper body, neck (degrees). 0 is vertical, positive leans to screen right |
| `hip_tilt`, `shoulder_tilt` | Tilt of the hip line and shoulder line. Positive lowers the screen-right side |
| `turn` | Torso turn (degrees). Positive faces screen right, up to 40 |
| `arm_left`, `arm_right` | [upper arm, forearm] angles. 0 is straight down, positive toward screen right |
| `leg_left`, `leg_right` | [thigh, shin] angles |
| `reach_left`, `reach_right` | Wrist target. When set, the arm angles are computed automatically (3 formats below) |
| `elbow_left`, `elbow_right` | 1 is the natural elbow (low and away from the body), -1 the opposite solution |
| `arm_left_scale`, `arm_right_scale` | [upper arm, forearm] length scale. Below 1 shows the arm coming toward the viewer |
| `leg_left_scale`, `leg_right_scale` | [thigh, shin] length scale. A seated thigh is 0.42 |
| `hand_left`, `hand_right` | Hand gesture name |
| `hand_left_view`, `hand_right_view` | `back` back of the hand, `palm` palm |
| `hand_left_angle`, `hand_right_angle` | Direction the fingers point (degrees). Left out, the forearm direction |
| `hand_left_roll`, `hand_right_roll` | Rotation around the hand's long axis (degrees, -90-90). Positive shows the thumb side to the viewer, negative the little finger side |
| `hand_left_pitch`, `hand_right_pitch` | How far the fingertips tip toward the viewer (degrees, 0-75). Foreshortens the fingers |
| `foot_left`, `foot_right` | Toe direction (degrees) |
| `behind` | List of arms drawn behind the torso, e.g. ["left"] |
| `front` | List of arms drawn in front of the face and hair |
| `first_leg` | The leg drawn first, placed behind |
| `legs_front` | true draws the legs in front of the torso (seated poses with the thighs coming toward the viewer) |
| `seat` | Seat height (head units below the pelvis center). Needed for seated poses |
| `support` | Default furniture of the pose (`stool`, `pillar`) |

- Back view poses use the same items. Left and right stay screen based

### Wrist targets

- 3 formats
    + Name : `"hip"`. Mirrored automatically to the arm's side, positioned for the gender's body
    + Coordinates : `[x, y]`. Head units from the pelvis center, x positive to screen right, y negative upward
    + Joint based : `["knee_right", dx, dy]`. Offset from a leg joint (`hip_*`, `knee_*`, `ankle_*`) position

| Name | Female [x, y] | Male [x, y] |
|---|---|---|
| `hip` waist | [0.61, -0.25] | [0.54, -0.25] |
| `front` in front of the body | [0.075, 0.05] | [0.08, 0.06] |
| `lap` on the knees (seated) | [0.10, 0.16] | [0.10, 0.16] |
| `chest` chest | [0.12, -1.38] | [0.14, -1.45] |
| `by_face` beside the face | [0.70, -2.20] | [0.76, -2.30] |
| `wave` above beside the head | [1.38, -2.62] | [1.50, -2.75] |
| `behind_head` behind the head | [0.40, -3.05] | [0.42, -3.18] |
| `crown` beside the crown | [0.23, -2.93] | [0.25, -3.05] |
| `pocket` front pants pocket | [0.42, -0.08] | [0.40, -0.06] |

- The table's x is for the screen-right arm; with a name, the left arm is mirrored automatically
- Reference coordinates (female) : shoulder joint [±0.49, -1.80], hip joint [±0.30, 0.05], knee [±0.38, 1.89], ankle [±0.41, 3.59]
- Reference coordinates (male) : shoulder joint [±0.66, -1.83], hip joint [±0.24, 0.05], knee [±0.33, 2.00], ankle [±0.36, 3.82]
- For poses with a hand near the face or chest, shrink `arm_*_scale` to about [0.45, 0.65]
- If a hand must cover hair or face, put that arm in `front`
- A target farther than the arm length straightens the arm, so pull the target toward the body

## Furniture

| furniture | Shape | Condition |
|---|---|---|
| `stool` | Round stool | Seated poses |
| `chair` | Wooden chair with a backrest | Seated poses |
| `sofa` | Two-seat sofa, back cushion and armrests | Seated poses |
| `pillar` | Square pillar on screen left, touching the leaning shoulder | Standing pose (`lean`) |
| `bed` | Double bed, wooden base, mattress, duvet, 2 pillows, headboard on screen left | Seated poses (`sitting`, `sitting_crossed`) |
| `none` | No furniture | |

- Furniture supported per view
    + Front : all 6 kinds
    + Profile : 5 kinds. `sofa` is seen from its end and the near armrest covers the hips, `pillar` stands right behind the back
    + Back view : `stool`, `chair`, `none`. The `chair` backrest is drawn in front of the body (on the viewer's side)

- Furniture is built in the same head units as the character, so the size matches automatically
- The seat height follows the pose's `seat`
- A sofa is about 6 heads wide, so make the canvas wide (e.g. [1600, 1500])
- The bed shows the character sitting on its long edge, drawn turned about 18 degrees so the headboard shows
    + It is about 6 heads long, so a wide canvas (e.g. [1500, 1300]) with `"shot": "full"` and `"x": 0.42` is stable
    + `furniture_color` is the duvet color
    + Together with the interior background `room` it becomes a bedroom scene (`figure_lingerie_room.json`)

## Profile

When `pose` is `side_stand`, `side_walk`, `side_sit`, `side_wave`, `side_lounge` or `side_lean`, the profile rig runs.

- The face is drawn as a profile outline (forehead, nose, lips, chin). Men get a larger brow bone, nose and chin
- Hair style, fringe, outfit, gender and build keys take the same values as the front view
- With `facing` `left` the character looks left (the light flips with it)
- Far limbs are drawn dark behind the body, the near arm in front of the body

`pose_overrides` items (angles in degrees, positive toward the face)

| Item | Description |
|---|---|
| `lean`, `chest`, `neck` | Forward tilt of waist, upper body, neck |
| `head_pitch` | Positive bows the head |
| `near_arm`, `far_arm` | [upper arm, forearm] angles of the near and far arm |
| `near_leg`, `far_leg` | [thigh, shin] angles of the near and far leg |
| `near_foot`, `far_foot` | Foot tilt. Positive lifts the heel |
| `near_hand`, `far_hand` | Hand gesture name (table in the hands section) |
| `near_hand_roll`, `far_hand_roll` | Hand rotation (degrees). The default 55 shows the back of the hand and the thumb side together, negative turns toward the palm |
| `near_hand_angle`, `far_hand_angle` | Finger direction (degrees, 0 is down). Left out, the forearm direction |
| `seat` | Seat height (head units below the pelvis center) |
| `support` | Default furniture of the pose |

- Walking on the other foot example : `{"near_leg": [-14, -30], "far_leg": [20, 5], "near_foot": 40, "far_foot": -12, "near_arm": [16, 32], "far_arm": [-18, -6]}`
- Profile furniture is 5 kinds, `stool`, `chair`, `sofa`, `pillar`, `none`. `side_sit` defaults to `stool`, `side_lounge` to `sofa`, `side_lean` to `pillar`
- The seat goes under the hips, and the sofa back cushion and the pillar face go to the point where the back sticks out farthest, automatically
- A skirt drapes like a tent over a raised knee (thigh at 30 degrees or more)

## Back view

When `pose` is `back_stand`, `back_lookback`, `back_walk` or `back_sit`, the back view rig runs.

- The skeleton is the same as the front rig; the forms laid on it change
    + Head : back of the head and backs of the ears. Short hair shows the nape, and `layered` splits into pointed ends at the back
    + Body : spine groove, shoulder blades, lower back dimples, buttock curve. Men get extra shading of broad back muscles
    + Legs : creases behind the knees, calves, Achilles tendons, heels
    + Outfit : back panels, jacket back vents, back pants pockets, bikini back strings. Ties and lapels are not drawn
- `look` decides the head direction
    + `away` : back of the head (`back_stand`, `back_walk` default)
    + `right`, `left` : a profile face looking back over that shoulder (`back_lookback` default is `right`)
    + `right_3q`, `left_3q` : a three-quarter face from the front face rig turned 35 degrees. The eyes meet the viewer and long hair hangs down the back
- Looking back in three-quarter follows `character.gaze` when it is set
- `back_sit` draws the legs and the hands on the knees behind the seat and the body. A chair backrest is drawn in front of the body
- Hanging hands default to an angle showing the little finger side (-60 degrees); change it with `hand_*_roll`
- Close-fitting outfits (`bodycon`, `swimsuit`) show the buttock curve, pants and skirts show it faintly
- Back view render examples : `figure_back_beach.json` (female, looking back), `male_back_city.json` (male, suit), `figure_back_chair.json` (female, sitting on a chair looking back in three-quarter)

## Hands

| Gesture | Shape |
|---|---|
| `relaxed` | Relaxed hand, fingers slightly bent |
| `open` | Hand with fingers spread |
| `together` | Flat hand with fingers together |
| `point` | Only the index finger extended |
| `peace` | V sign |
| `fist` | Fist |
| `grip` | Hand holding something |
| `pocket` | Hand in a pocket. Hand and wrist are covered by the outfit and not drawn |
| `tucked` | Hand hidden under the other arm (`arms_crossed`). Not drawn |

- Male hands are drawn with thicker fingers and palms
- Hands are built from 3D points with depth at every finger joint, so `roll` and `pitch` can rotate them
    + `roll` 60-75 : a hanging hand seen from the thumb side. Most effective when the back of the hand looks flat from the front
    + `roll` -45 : the little finger side
    + `pitch` 30-40 : a waving hand tips toward the viewer and the fingers look shorter
    + A rotated hand gets its palm thickness and finger front-to-back order computed automatically, and a hidden thumb is hidden
- Hand angle render example : `figure_hand_angles.json` (waving hand `pitch` 35, hanging hand `roll` 70)
- `peace` looks most natural in the `palm` view
- The thumb points toward the body automatically
- Hands hold up in upper body framing; pictures zoomed in on the hands alone are not recommended

## Props (cigarette)

- `figure.cigarette` draws one cigarette and its smoke. Usable on the front, three-quarter, profile and back view rigs, `extras` and `duo.partner`
- `left`, `right` : the filter sits between that hand's index and middle fingers and the lit end points outward past the index finger
    + It is attached in hand coordinates, so it turns with the hand's `roll`, `pitch` and wrist angle
    + If that hand is `pocket` or `tucked` it stops with an error (a hidden hand cannot hold a cigarette)
    + A hanging hand looks most natural. For a hand raised near the face, shrink `arm_*_scale` to [0.45, 0.65] so the elbow does not jut sideways
- `mouth` : held at the mouth corner, tilting down and outward
    + The front rig uses the mouth corner opposite the head turn (the viewer's side), the profile the front of the lip line
    + A back view with `look` `away` does not show the mouth, so it is not drawn
- Smoke rises from the lit end in 4 strands, widening and fading upward, drifting a little toward the light
- The cigarette and smoke are drawn over the rim light (the ember is its own light)
- To draw a cigarette alone, as in a still life, use `paintkit.props.paint_cigarette`, `paintkit.props.smoke` (`paintkit-api.md`)

## Outfits

| outfit | Gender | Parts | Color keys |
|---|---|---|---|
| `dress` | female | Sleeveless dress, knee length, folds | `cloth`, `cloth_shadow` |
| `blouse_skirt` | female | Long-sleeve blouse + pencil skirt | blouse `cloth`, skirt `cloth2` |
| `sweater_pants` | unisex | Sweater + long pants | sweater `cloth`, pants `cloth2` |
| `bodycon` | female | Close-fitting strappy mini dress, gloss | `cloth`, `cloth_shadow` |
| `swimsuit` | female | Bikini (triangle top + bottom) | `cloth`, `cloth_shadow` |
| `suit` | unisex | Suit jacket, shirt, tie, straight pants | jacket and pants `cloth2`, shirt `cloth`, tie `accent` |
| `shirt_pants` | unisex | Collared shirt (tucked in), belt, straight pants | shirt `cloth`, pants `cloth2`, belt `shoe` |
| `tshirt_jeans` | unisex | Short-sleeve T-shirt + jeans | T-shirt `cloth`, pants `cloth2` |
| `trunks` | male | Swim trunks (on a woman, a topless figure study) | `cloth`, `cloth_shadow` |
| `lingerie` | unisex | Female : lace-trimmed bra + briefs. Male : drawers + contrasting waistband | `cloth`, `cloth_shadow`, male waistband `accent` |
| `crop_hotpants` | female | Cropped T-shirt showing the navel + denim hot pants (fly, curved pockets, frayed hems) | T-shirt `cloth`, hot pants `cloth2` |
| `hoodie_jeans` | unisex | Hoodie (hood, strings, kangaroo pocket, ribbed hem and cuffs) + jeans | hoodie `cloth`, pants `cloth2` |
| `open_shirt_shorts` | male | Short-sleeve open-collar shirt (untucked, buttoned) + shorts above the knee | shirt `cloth`, shorts `cloth2` |
| `tank_shorts` | unisex | Sleeveless sports top + training shorts (waistband, side stripes) | top `cloth`, shorts `cloth2`, stripes `accent` |
| `denim_jacket_chinos` | unisex | Open denim jacket (collar, flap chest pockets, waistband, cuffs) + crew-neck T-shirt + straight chinos | jacket `outer`, T-shirt `cloth`, pants `cloth2` |
| `leather_jacket_jeans` | unisex | Open rider leather jacket (wide lapels, zipper, gloss) + T-shirt + slim jeans | jacket `outer`, T-shirt `cloth`, pants `cloth2` |
| `coat_turtleneck` | unisex | Long coat below the knee (lapels, side pockets, back vent) + tucked turtleneck + straight slacks | coat `outer`, turtleneck `cloth`, pants `cloth2` |
| `knit_dress` | female | Ribbed knit dress, crew neck, long sleeves with cuffs, above the knee, close-fitting | `cloth`, `cloth_shadow` |
| `tank_jeans` | female | Close-fitting tank top + low-rise slim jeans | top `cloth`, pants `cloth2` |
| `none` | unisex | No outfit | |

- `bikini` is the same outfit as `swimsuit`
- Use `suit` for suit requests; the tie color is `accent`

- The gender column is who the outfit is cut for; it is used for defaults, error messages and the grouping in the docs
    + The engine draws the spec's outfit as written regardless of gender
    + When picking outfits, first pick one whose gender column matches the character, and use other-gender outfits only when the user states that combination
    + Pairs by situation : bikini `swimsuit` and `trunks`, crop top and hot pants `crop_hotpants` and `open_shirt_shorts`, dress `dress` and `suit`, blouse and skirt `blouse_skirt` and `shirt_pants`, knit dress `knit_dress` and `coat_turtleneck` or `sweater_pants`
- Jacket and coat color is `palette.outer`; empty uses the material color (denim `#5f7fa8`, leather `#34303a`, coat `#b08860`)
- Shoe color is `palette.shoe`
- `swimsuit`, `trunks`, `lingerie`, `none` default to bare feet; with `heels` on, shoes are drawn
- Every outfit is also drawn in profile and back views
    + v9 outfits from the back : shirt collar band, denim jacket yoke and waistband, coat center line and back vent, tank top back neckline
    + v9 outfits in profile : the inner clothes show between the front panels of open jackets and coats, and coat skirts fall straight from the hips
- View forms of the 3 v8 outfits
    + Back view : bra back band and straps, back pockets of the hot pants, hood lying on the back of the hoodie
    + Profile : side of the bra cup, the crop hem, the hood hanging behind the neck
- Close-fitting outfits (`bodycon`, `swimsuit`) follow the body's shading as is, so `build` changes show best on them
- In seated poses, skirts (including `knit_dress`) automatically get cloth covering the top of the thighs
- In seated poses, a long coat breaks at the seat and the two front panels spread over the thighs
- Shorts are split into leg pieces and a seat piece, so they show over the thighs in seated poses too
- Bust `character.outfit` values are not used for full bodies

## Figure study

- `outfit` `none` is a body without clothes (figure study, outfit design underdrawing and the like)
- What the engine draws
    + The engine has no genital shapes
    + Female : the torso is shown with collarbones, breast shading, navel and groin lines. The engine has no nipple shapes
    + Male : the torso is shown with chest muscles, abs, the iliac V line and navel. Nipples are faint color dots
- `trunks` on a woman is topless, with the same torso treatment as above
- `lingerie` also uses the same torso treatment; see-through or removed underwear is not in the engine
- Minor standards follow the protection of minors section of SKILL.md
- The painterly style (`painterly`) and knee-up framing look most like a painting
    + Smaller eyes (`eye_height` 0.062-0.074), fuller lips (female `lip_fullness` 1.3)
    + A dark `wash` background, `rim_light` 0.4

## Background people (extras)

People in the top-level `extras` list are drawn into the background with the full body rig. They are drawn before the main character and always stand behind.

| Key | Description |
|---|---|
| `character` | Gender, face, hair (same keys as the bust) |
| `palette` | Colors |
| `figure` | Pose, outfit, build and so on (the figure keys of this document) |
| `at` | [x, z] meters. Position on the street (`street`). x is the sideways distance from the road center, z the distance forward from the camera |
| `placement` | `head_height`, `pelvis`. Direct placement as canvas fractions in scenes without a street |

- With `at`, size is computed from height (female 1.63 m, male 1.76 m) and perspective
- The sidewalk is at x 3.6-6.2 m from the road center
- Condition to stay inside the canvas : |x| < z x canvas width / (1.8 x canvas height). For a [1500, 1000] canvas, |x| < 0.83 z
- Nearby background person example : `{"character": {"gender": "male"}, "figure": {"pose": "side_walk", "outfit": "tshirt_jeans", "facing": "left"}, "at": [-4.3, 7.0]}`
- Rendering is faster with distant crowds as `people` of `street` and nearby people as `extras`
- For a person holding hands or linking arms with the main character, use `duo` instead of `extras` (next section)

## Two-shot (duo)

When the top-level `duo` key exists, a partner (`partner`) is drawn next to the main character (`figure`).

```json
"duo": {
  "pose": "arm_in_arm",
  "side": "right",
  "partner": {
    "character": {"gender": "male", "hair_style": "layered"},
    "palette": {"cloth": "#f2f2f4", "cloth2": "#1c2233", "accent": "#7a1a2a"},
    "figure": {"pose": "standing", "outfit": "suit"}
  }
}
```

| Key | Default | Description |
|---|---|---|
| `pose` | "side_by_side" | Relationship of the two (table below) |
| `side` | "right" | Side the partner stands on (screen based) |
| `gap` | pose default | Distance between the two pelvis centers (main character head units) |
| `front` | "main" | Character drawn in front, `main` or `partner` |
| `eyes` | pose default | `each_other` (look at each other), `viewer` (look at the viewer) |
| `partner` | {} | The partner's `character`, `palette`, `figure` (same keys as the main character) |

| pose | Staging | Default gap | Default eyes |
|---|---|---|---|
| `side_by_side` | Standing side by side, no contact | 1.9 | `viewer` |
| `hold_hands` | Inner hands held below hip height | 2.0 | `each_other` |
| `arm_in_arm` | The main character rests a hand on the partner's bent forearm; the partner's hand on that arm is in a pocket | 1.4 | `each_other` |
| `arm_around` | The partner wraps the inner arm behind the main character's back at shoulder height and rests the hand on the far shoulder. The arm shows over the shoulder line on both sides of the neck and the hand drapes over the front of the shoulder | 1.5 | `each_other` |
| `face_to_face` | Both in profile facing each other, leaning in slightly | 1.4 | facing each other |

- The partner's size comes from real height (female 1.63 m, male 1.76 m) and both characters' feet stand on the same floor line
- `each_other` turns toward the partner only those of `head_turn` and `gaze` not set in the spec
- Contact poses (`hold_hands`, `arm_in_arm`, `arm_around`) need front poses for both characters
    + Targets and gestures of the contact hands are set automatically; the same items in `pose_overrides` win
    + The other hands follow each character's pose preset (e.g. partner `pose` `pockets`)
- `face_to_face` switches both characters to the profile rig and sets `facing` automatically. A given profile pose is used as is
- If the `arm_in_arm` partner wears an outfit without pockets, the hand comes down diagonally beside the body
- The `arm_around` arm actually bends back behind the back, so on screen it is drawn shortened to the distance between the shoulders
    + The wrist rests on the main character's far shoulder outline (including jacket collar and shoulder)
    + When a shorter partner wraps a taller main character, the elbow bends more so the arm shows over the shoulder line behind the neck
- `placement.shot` frames both characters together, considering the taller one's crown, the common floor and the width of both
    + Without `shot`, `pelvis` sets the main character's pelvis position; with neither, both are centered in the picture
- `ground_shadow` follows the main character's value unless the partner `figure` sets its own
- Two-shot render examples : `duo_city.json` (arm in arm, full body), `duo_beach.json` (face to face, upper body), `duo_rain_night.json` (holding hands, night street), `duo_living_room.json` (arm around shoulders, interior)

## Coordinates for the mixed mode

Tools of the full body object (`portrait`) returned by `scene.build`.

- `portrait.joints` : dictionary of joint coordinates (head units, from the pelvis). Keys are `pelvis`, `waist`, `chest`, `neck`, `eyes`, `shoulder_left`, `elbow_left`, `wrist_left`, `hip_left`, `knee_left`, `ankle_left` with `_right` pairs. In profile `left` is the far side, `right` the near side
- `portrait.at(points)` : converts skeleton coordinates to pixels
- `portrait.chest_pt(x, y)`, `portrait.pelvis_pt(x, y)` : points relative to the tilted chest and pelvis
- `portrait.masks` : besides the bust masks, `torso`, `arm_left`, `arm_right`, `leg_left`, `leg_right`, `legs`
- `portrait.hands["right"].mask` : hand mask
- `portrait.plan` : the gender's body plan (all proportion values)
- `portrait.partner` : the partner object of a two-shot (with the same tools), absent otherwise
- Layer order (front) : background, ground_shadow, hair_back, seat, figure, face, features, hair_front, see_through, figure_front, rim
- Layer order (profile) : background, ground_shadow, seat, figure_far, far_shade, figure, face, features, hair_front, figure_front, rim
- Layer order (back view) : same as front. `hair_back` is empty and the whole head of hair is drawn in `hair_front`, no `see_through`
    + Looking back in three-quarter : `hair_back` is drawn over `figure` (hair hanging down the back)
    + Seated back view : figure_far (legs, arms on the knees), seat, figure, (chair) seat_front in that order
- Layer order (profile sofa) : the near armrest is drawn in `seat_front` over `figure_front`
- Layer order (two-shot) : ground_shadow, all layers of the character behind, all layers of the character in front; with `arm_around`, the partner's hand is drawn again on top in `duo_hand`
