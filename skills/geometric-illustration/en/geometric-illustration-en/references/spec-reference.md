# Spec Field Reference

> Translated from the Korean original. Where the two editions disagree, follow the Korean edition.

A spec JSON is merged over `DEFAULT_SPEC` in `scripts/config.py`. Write only the fields to change.
The unit "head breadth" is a relative length with the head breadth as 1; the origin is the head center and the y axis points down.

## Contents
- Canvas, subject, style
- Light
- Palette
- Shading per material
- Character: sex, body type, head placement, face, face preset, eyes, brows, mouth, expression, hair, outfit, pose
- Groups
- Figure study
- Scene
- Background and lines

## Canvas, Subject, Style

| Field | Default | Range | Effect |
|---|---|---|---|
| `canvas.width` | 1024 | 256 or more | Output width (px) |
| `canvas.height` | 1280 | 256 or more | Output height (px). 1600 or more recommended for full body |
| `canvas.seed` | 7 | Integer | Random seed for illustration grain, oil strokes and watercolor bleeding |
| `subject` | `portrait` | `portrait`, `nude`, `still_life`, `cityscape`, `landscape` | What to draw |
| `style` | `anime` | `anime`, `illustration`, `oil`, `watercolor` | Style |
| `framing` | `bust` | `bust`, `upper_body`, `full_body`, `wide` | `portrait` only. Head size and position are computed automatically. `wide` is an establishing shot (full figure height 34% of the canvas, feet at 90% of the canvas height) |
| `look` | `none` | `none`, `doomer` | Whole-image color grade after the style render. `doomer`: lower saturation, bluer dark tones, saturation kept only in bright orange lights, black lifted to blue-gray, film grain, vignette (`looks.DOOMER`) |

## Light

| Field | Default | Effect |
|---|---|---|
| `light.direction` | [-0.55, -0.65, 0.55] | Vector toward the light. x right, y down, z toward the viewer. The sign of x also sets the background glow position. Scene subjects replace it with the light set by the time of day (`scene.time`) or the still life set (`scene.set`) |
| `light.cast_distance` | 0.032 | Cast shadow offset (head breadths). Length of the bangs shadow and hair shadows |
| `light.rim_color` | `#BFD4FF` | Backlight rim color (illustration, oil) |
| `light.rim_strength` | 0.55 | Rim light strength 0-1 |

## Palette

Every color is a `#RRGGBB` string or a 0-255 RGB array. Line colors are derived automatically from each flat color.

| Field | Target |
|---|---|
| `skin`, `blush`, `lips` | Skin, cheek blush, lips |
| `hair`, `hair_highlight` | Hair flat color, gloss color. Brow color derives from `hair` |
| `eye`, `sclera`, `lash` | Iris, eye white, lashes |
| `cloth`, `skirt` | Top (swimwear and underwear themselves), bottom (skirt, trousers, shorts) |
| `belt`, `shoe`, `sole` | Belt, shoe upper, sneaker sole and laces |
| `shirt`, `tie`, `accent` | Suit shirt, tie, secondary colors such as lace and straps |
| `metal` | Earrings, buckles, buttons |
| `drape` | Sofa drape of the reclining figure study |
| `chair` | Chair of the `seated` pose (wood material shading) |
| `hat` | Hat of `outfit.hat` (default dark gray) |
| `background` | [start color, end color] 2-color array. The end color is the `flat` background color |
| `background_glow` | Glow color on the light side of a `glow` background |

## Shading per Material

Keys are material group names: `skin` (face), `body` (mannequin body and hands), `hair`, `cloth`, `skirt`, `lips`, `eye_white`, `iris`, `metal`, `shoe`, `leather`, `glass`, `ceramic`, `fruit`, `lemon`, `wood`, `foliage`, `marble`, `device` (electronics), `paper`, `food`, `liquid`, `default`.
Groups `bg`, `sky`, `emissive`, `scenery`, `screen` (screen content) keep their designed colors and receive no shading.
Group `body` also gets cel shadow cleanup (filling small light gaps). Small designed shadows on the face (`skin`) stay as they are.

| Field | Effect |
|---|---|
| `cel_threshold.<group>` | Shadow where the dot product of normal and light is below this value. Higher values give more shadow area. Skin uses -0.30 to keep the face bright |
| `shadow_tint.<group>` | Multiply color of the shadow. Reddish for skin, blue-violet for hair and clothes by default |

## Character

### Sex (`character.sex`)

| Value | Effect |
|---|---|
| `female` | Default. Adult female body, face, long hair, outfit `turtleneck_sleeveless` |
| `male` | Adult male body (broad shoulders, narrow pelvis, pectorals, thick neck, smaller drawn head), male face preset, hair `short`, outfit `tee_jeans`, no earrings |

- The sex preset changes only defaults. Face, eye, hair and outfit fields written in the spec take precedence over the preset
- Male outfits are the 10 in the outfit table below other than `bikini`, `lingerie`, `turtleneck_sleeveless`, `crop_hotpants`. Shoes of the suit, shirt and coat become lace-up shoes

### Body type (`character.build`)

| Sex | Value | Form |
|---|---|---|
| Female | `standard` | Default. ANSUR II lean subsample adjusted for anime illustration |
| Female | `slender` | Torso width and depth about 9% smaller, limbs about 12% thinner, chest form 0.8x |
| Female | `glamour` | Chest form 1.3x, hip width about 9% larger, waist 4% smaller, thighs and buttocks larger. Within adult body ranges, no exaggeration |
| Female | `athletic` | Shoulders 7% wider, waist 6% wider, upper arms 14% and calves 10% thicker |
| Male | `standard` | Default. Estimated from ANSUR II male summary statistics |
| Male | `slim` | Torso about 8% smaller, limbs about 13% thinner |
| Male | `athletic` | Shoulders 9%, chest breadth 12%, pectorals 1.35x, upper arms 18%, neck 10% larger, waist 2% smaller |

- Vertical reference heights (neck, waist, knee, ankle) are the same for all body types. Poses and garment cut lines still match
- Clothes are put on by inflating the body of the body type, so they follow it. Bikini and bra cups grow with the chest form
- Factor table: `VARIANTS` in `scripts/rig_anatomy.py`. Check: `python scripts/check_proportions.py --build female_glamour`
- `character.scale`: size relative to the other figures in a group. If null, a man beside a woman is 1.06

### Head placement (`character.head`)

| Field | Default | Range | Effect |
|---|---|---|---|
| `x` | 0.50 | 0-1 | Horizontal position of the head center (canvas fraction) |
| `y` | null | 0-1 | Vertical position of the head center. If null, computed from the framing |
| `size` | null | 0.05-0.5 | Head breadth (fraction of the canvas width). If null, computed from the framing |
| `yaw` | 0.22 | -0.35-0.35 | Left-right turn (radians). Positive faces screen right |
| `roll` | -0.05 | -0.15-0.15 | Tilt (radians) |

### Face preset (`character.face_preset`)

| Value | Effect |
|---|---|
| `default` | Face fields as given |
| `soft` | Round jawline, drooping eye corners, gentle brows |
| `sharp` | Angular jaw, raised eye corners, narrow eyes |
| `mature` | Long face, smaller eyes, thick brows, less blush |
| `gentle` | Drooping eye corners, gentle thin brows, soft jawline, faint smile |
| `cool` | Narrow raised eyes, low straight thick brows, narrow mouth, less blush |
| `bold` | Thick lashes and brows, strong lips, wide mouth |

Preset results are clamped into the adult face ranges (`eyes.size` 0.85-1.10, `eyes.openness` 0.70-0.95, `face.chin_length` 0.68-0.76, `face.jaw_width` 0.36-0.42, `blush` 0-0.35).

### Face (`character.face`)

| Field | Default | Effect |
|---|---|---|
| `cheek` | 0.485 | Face half-width at cheekbone height |
| `jaw_width` | 0.385 | Half-width at the jaw angle. Smaller gives a V line |
| `jaw_height` | 0.44 | Height of the jaw angle |
| `chin_length` | 0.70 | Chin tip height. Larger gives a longer face |
| `chin_width` | 0.04 | Chin tip half-width. Closer to 0 is pointier |
| `jaw_sharpness` | 0.85 | 0-1. Straightness of the outline from the jaw angle to the chin tip |

### Eyes (`character.eyes`)

| Field | Default | Effect |
|---|---|---|
| `size` | 1.1 | Eye size factor 0.8-1.4 |
| `openness` | 0.92 | Vertical opening 0.6-1.1 |
| `tilt` | 0.10 | Rise angle of the outer eye corner (radians). Positive gives cat eyes |
| `spacing` | 0.205 | Horizontal distance of the eye centers (head breadths) |
| `height` | 0.13 | Height of the eye center line (below the head center) |
| `gaze` | [-0.15, 0.0] | Gaze x, y. -1-1 |
| `lash_weight` | 1.0 | Lash thickness factor |

### Brows (`character.brows`)

| Field | Default | Effect |
|---|---|---|
| `angle` | 0.4 | Rise of the brow peak. Larger gives a sharper impression |
| `thickness` | 0.9 | Thickness factor |
| `height` | 0.0 | Vertical offset (head breadths) |
| `see_through` | 0.35 | Opacity of the brows showing through the bangs 0-1 |

### Mouth and blush

| Field | Default | Effect |
|---|---|---|
| `mouth.smile` | 0.25 | Rise of the mouth corners 0-1 |
| `mouth.width` | 1.15 | Mouth width factor |
| `mouth.lip_strength` | 0.65 | Lip color opacity 0-1 |
| `blush` | 0.30 | Cheek blush opacity 0-1. 0 omits it |
| `mouth.open` | 0 | Open mouth 0-1. With smile 0.3 or more, a laughing mouth (upper teeth, tongue); below that, a round mouth |
| `eyes.shape` | `open` | `closed` gives smiling closed eyes (an upward curved lash line) |

### Expression (`character.expression`)

| Value | Effect |
|---|---|
| `default` | Face fields as given |
| `smile` | Raised mouth corners, slightly narrowed eyes |
| `laugh` | Closed eyes, open mouth with upper teeth, more blush |
| `neutral` | Flat mouth, gentle brows |
| `surprised` | Round open mouth, larger eyes, raised brows |
| `serious` | Lowered mouth corners, narrow eyes, angular brows |
| `sad` | Drooping mouth corners, brows raised at the inner ends, downward gaze |

Expressions apply after the face preset and change the eye and brow values of the sex preset (`config.EXPRESSIONS`).

### Hair (`character.hair`)

| Field | Default | Effect |
|---|---|---|
| `style` | `long` | `long` straight long hair, `updo`, `short` short hair (male default), named hair styles below |
| `length` | 2.3 | Height of the back hair tips (head breadths). 1.4 shoulder, 2.3 chest, 3.5 or more waist. When reducing it, reduce `side_length` too |
| `volume` | 0.06 | Volume above the scalp 0-0.15 |
| `bangs` | `swept` | `swept` to one side, `parted` curtain, `blunt` straight across, `slicked` combed back (forehead exposed) |
| `bang_count` | 8 | Number of bang clumps, 3 or more |
| `bang_length` | 0.10 | Height of the bang tips. The eye center line is 0.13 |
| `part` | -0.14 | Part position -0.3-0.3 |
| `tuck` | `near` | Side tucked behind the ear: `near` the near side, `far` the far side, `none` both down |
| `side_length` | 1.75 | Height of the side lock tips |
| `seed` | 3 | Random seed for clump width and tip variation |

Named hair styles (`rig_hair.HAIR_PRESETS`) override fields over the three base hair builders. Color and seed come from the spec.

| `style` | Base | Shape |
|---|---|---|
| `side_part` | `short` | Deep side part, short swept bangs |
| `slicked` | `short` | Hair combed back, forehead exposed |
| `two_block` | `short` | Short sides, longer top falling as parted bangs |
| `medium` | `long` | Medium length reaching the jawline and nape |
| `bob` | `long` | Jaw-length bob, blunt bangs |
| `ponytail` | `updo` | Tail tied at the back and hanging down |
| `hime` | `long` | Blunt bangs, jaw-length side locks, long back hair |
| `center_part` | `long` | Center part curtain bangs, long straight hair |
| `shoulder` | `long` | Shoulder length, parted bangs, one side tucked behind the ear (for women and men) |
| `crop` | `short` | Short hair with blunt bangs above the brows |

### Outfit (`character.outfit`)

| Field | Default | Effect |
|---|---|---|
| `type` | `turtleneck_sleeveless` | Outfit type (table below) |
| `shoulder_width` | 0.93 | Shoulder half-width. Bust turtleneck only |
| `skirt_length` | 6.2 | Skirt hem height (head breadths, standing pose). Upper and full body of `turtleneck_sleeveless` only |
| `skirt_flare` | 1.15 | Target hem half-width. The skirt flares at a constant slope from the hips to this width. If the legs reach farther out, it widens by that much |
| `earrings` | `drop` | `drop`, `stud`, `none` |
| `hat` | `none` | `none`, `beanie` (knit beanie with a folded cuff). Drawn over the hair, so only bangs and side locks below the cuff show. Also drawn in back views |
| `shoes` | null | If null, the outfit's default shoes. Change to `pumps`, `sneakers`, `oxfords`, `none` |

| `type` | Pieces | Shoes | Default colors (`cloth` / `skirt`) |
|---|---|---|---|
| `turtleneck_sleeveless` | Sleeveless turtleneck, midi skirt, belt | Pumps | Charcoal / camel |
| `bikini` | Triangle bikini, tie-side bottom | Barefoot | Navy |
| `lingerie` | Lace-trimmed bra, briefs | Barefoot | Black, lace `accent` |
| `crop_hotpants` | Crop tank top, denim hot pants | Sneakers | White / light blue |
| `tee_jeans` | Short-sleeve T-shirt, jeans | Sneakers | White / dark blue |
| `suit` | Jacket, shirt, tie, slacks, belt | Pumps | Charcoal, `shirt`, `tie` |
| `hoodie_joggers` | Hoodie (hood, pocket, cords), jogger pants | Sneakers | Gray / black |
| `swim_trunks` | Swim trunks (drawstring, side stripe). Male only | Barefoot | `skirt` teal |
| `shirt_slacks` | Dress shirt (collar, buttons, cuffs), slacks, belt | Pumps / men's shoes | `shirt` light blue / charcoal |
| `knit_coat` | Crewneck knit, belted knee-length coat (lapels), trousers | Pumps / men's shoes | `shirt` ivory, `cloth` camel / charcoal |
| `polo_shorts` | Polo shirt (collar, 2 buttons), chino shorts above the knee | Sneakers | Navy / beige |
| `tank_shorts` | Sports singlet, running shorts (side stripe `accent`) | Sneakers | White / black |
| `denim_jacket` | Open denim jacket (chest pockets, buttons), T-shirt, jeans | Sneakers | `cloth` blue, `shirt` white / dark blue |
| `track_suit` | Zip track jacket (stand collar), track pants, stripes on sleeves and legs | Sneakers | Navy, stripe `accent` |

- Every outfit has default colors. Colors written in the spec's `palette` take precedence over them
- In the bust, `turtleneck_sleeveless` uses the bust-only outfit; other outfits use 3D clothes put on the mannequin body
- The current body model has no nipple or genital geometry

### Pose (`character.pose`)

| Field | Default | Effect |
|---|---|---|
| `preset` | `relaxed` | Pose table below. Upper and full body only |
| `turn` | 0.0 | Body turn: `front`, `three_quarter` (0.6), `side` (pi/2), `three_quarter_back` (2.3), `back` (pi); a leading `-` turns to the other side; a number is radians. Positive turns the chest toward screen right |
| `look` | `auto` | `auto` the face turns with the body (back of the head at 1.9 radians or more), `face` draws the face with `head.yaw` (glance over the shoulder), `away` back of the head |
| `custom` | null | Direct joint targets (below) |

| Pose | Action | Default view |
|---|---|---|
| `relaxed` | Both arms down, weight shift | Front |
| `hand_on_hip` | One hand on the hip | Front |
| `hair_touch` | One hand brushing the hair back | Front |
| `chin_rest` | Chin resting over crossed arms | Front |
| `arms_crossed` | Arms crossed | Front |
| `hands_in_pockets` | Both hands in the front pockets (the front pocket for a hoodie). Bikini and underwear lower the arms | Front |
| `walking` | A step with the front foot planted and the back heel raised, arms swinging in counter | `turn` 0.9 |
| `look_back` | Back to the viewer, glancing over the shoulder, one hand on the hip | `turn` 2.55, `look` `face` |
| `lean_wall` | Shoulder leaning on a pillar at screen left, ankles crossed | Front |
| `seated` | Seated on a chair, hands on the thighs. Full-body framing fits the seated height | `turn` 0.6 |

- The default view is used only when the spec has `turn` 0 and `look` `auto`. A written `turn` takes precedence
- In the seated pose the skirt becomes cloth lying on the thighs (ending at the knees), and coat skirts change the same way

Direct joint targets (`custom`): written in body coordinates facing front (head breadths, origin at the head center, y down, z toward the viewer); the turn (`turn`) applies after them.

| Key | Value |
|---|---|
| `arm_left`, `arm_right`, `leg_left`, `leg_right` | `{target: [x, y, z], pole: [x, y, z], hand: gesture or foot mode, hand_u, hand_n, foot_dir}` (left and right of the figure) |
| `chest`, `pelvis` | `[yaw, pitch, roll]` radians |
| `shift` | Sideways pelvis shift (weight shift) |

Reference values: shoulder joint (±0.74, 1.17), elbow height 2.75, wrist height 4.05, hip joint (±0.32, 3.74), knee 5.96, ankle 8.10. Hand gestures: `relaxed`, `hip`, `hair`, `chin`, `cover`, `clasp`, `prop`, `pocket` (hidden under the clothes). Foot modes: `flat`, `point` (tiptoe, pumps).

## Groups (`characters`, `layout`)

With `subject` `portrait`, listing 2-3 figures in `characters` makes a group picture. Each entry takes the same fields as `character` plus `palette` (overridden in the order sex preset, outfit default colors, figure colors).

| Field | Default | Values | Effect |
|---|---|---|---|
| `layout.type` | `side_by_side` | `side_by_side`, `facing`, `front_back` | Side by side (2-3 figures), facing (turned 0.75 radians toward each other), front and back (the figure behind is slightly smaller and higher) |
| `layout.interaction` | `none` | `none`, `hold_hands` | Two neighboring figures hold their inner hands between them |
| `layout.gap` | null | Head breadths | Gap between neighbors. If null, the default of the layout |

- Framing follows `framing`, and the largest figure fits the canvas. If the width is not enough, everything shrinks
- When seated and standing figures mix, they share the same floor
- The front-to-back order is the list order (the first figure is frontmost)
- The figure study (`nude`) does not support groups

## Figure Study (`nude`)

Used only when `subject` is `nude`. The figure is fixed to adult proportions and placed automatically to fit the canvas.

| Field | Default | Values | Effect |
|---|---|---|---|
| `nude.pose` | `venus` | `back_three_quarter`, `venus`, `reclining`, `seated` | Pose. See the table below |
| `nude.hair` | null | null, `long`, `updo`, `short` | Hair style. If null, the pose default (`short` for men) |

| Pose | Composition | How it covers |
|---|---|---|
| `back_three_quarter` | Standing 3/4 from behind, glancing over the shoulder, one hand at the updo | View from the back |
| `venus` | Frontal contrapposto standing pose | Arms, hands, hair |
| `reclining` | Reclining on a sofa seen from behind (odalisque) | View from the back, drape |
| `seated` | Seated on the floor hugging the knees, side view | Thighs and arms |

With `character.sex` `male`, the same 4 poses are drawn with the male body. There is no hair lock covering the chest. In `venus` the arm that covered the chest lowers to the side and the hand covering the pelvis stays. The body without genital geometry and the line-free zone around the pelvis are the same for women and men.

Face, eye and hair color fields of `character` apply as given and are clamped to these ranges: `eyes.size` 0.85-1.10, `eyes.openness` 0.70-0.95, `face.chin_length` 0.68-0.76, `face.jaw_width` 0.36-0.42, `blush` 0-0.35.

## Scene (`scene`)

The `still_life`, `cityscape` and `landscape` subjects draw the composition and light set by the scene. Fine variations of the layout change with `character.hair.seed` (the scene random seed).

| Field | Default | Values | Effect |
|---|---|---|---|
| `scene.time` | `dusk` | `dusk`, `day`, `golden`, `blue_night`, `rain_night`, `snow_night` | Time of day of landscapes and cityscapes. See the table below |
| `scene.site` | null | City `street`, `panel` / landscape `lake`, `outskirts` | Site. If null, the first value (`street`, `lake`). See the table below |
| `scene.set` | `classic` | `classic`, `desk`, `cafe`, `gaming`, `kitchen` | Still life set. See the table below |
| `scene.palette` | {} | Color dict | Scene color overrides. Keys in the table below. Applied over the colors of the chosen time of day or set |

### Time of day (`scene.time`)

| Value | Meaning | Elements turned on |
|---|---|---|
| `dusk` | Dusk (default) | Sun on the horizon, sun path, rim light on clouds and ridges, some windows and street lamps |
| `day` | Clear day | High sun, white clouds, glints on the lake. In the city, a building shadow band on the sun side, light and dark contrast on the facades, windows reflecting the sky |
| `golden` | Golden hour | Low sun above the horizon, golden sun path and rim light, a few lit windows |
| `blue_night` | Blue-hour night view | Moon, stars, moonlight path, village lights on the lakeshore, most windows, street lamps, signs |
| `rain_night` | Rainy night | Rain streaks, dense clouds, misty ridges, rain rings on the lake, light streaks reflected on the wet road |
| `snow_night` | Snowy night | Overcast sky, falling snow (far snow and large near flakes), sodium street lamps, wheel ruts on the snow-covered road, some lit windows, bare trees and birches |

### Site (`scene.site`)

| Scene | Value | Composition |
|---|---|---|
| `cityscape` | `street` | Avenue lined with shops and signs, lane markings, cars (default) |
| `cityscape` | `panel` | 5-12 story panel apartment blocks beyond front yards (panel seams, balconies, stairwell windows), blocks in a back row, bare street trees, wires and street lamps |
| `landscape` | `lake` | Mountain ridges, lake, conifers on the shore (default). On a snowy night the front trees are birches |
| `landscape` | `outskirts` | Field at the edge of town, footpath in the snow, housing blocks and chimneys on the horizon, aircraft warning lights on the chimney tops, a receding line of power pylons, birches in front |

Every site draws at every time of day. Colors of `outskirts` at times other than `snow_night` derive from the lake palette of that time.

### Still life set (`scene.set`)

| Value | Composition | Light |
|---|---|---|
| `classic` | Bottle, jug, apple, lemon, grapes, drape (default) | Window light from the upper left |
| `desk` | Laptop (code on screen), mug with steam, smartphone, desk lamp, potted plant, notebook and pen | Desk lamp on the right |
| `cafe` | Latte and saucer, slice of cake with strawberry, fork, iced latte glass, smartphone, earbud case, large window and bokeh | Afternoon window light from behind on the left |
| `gaming` | Monitor (game screen), RGB keyboard, mouse, RGB desk pad, headset stand, drink can, RGB wall lighting | Soft light from the front above, screen and RGB glow |
| `kitchen` | Checked vinyl tablecloth, tea glass in a metal holder with a spoon, radio cassette player (tape window, speaker, orange tuning dial, antenna), cassette tape, snowy night housing blocks beyond a white window frame | One incandescent bulb off screen at the upper right |

### Palette keys

| Scene | Main palette keys |
|---|---|
| Shared sky | `zenith`, `upper`, `middle`, `lower`, `horizon`, `sun`, `sun_glow`, `cloud_top`, `cloud_lit`, `cloud_rim`, `haze`, `moon`, `star`, `rain`, `snow` |
| `landscape` | `ridge_far`, `ridge_mid`, `ridge_rim`, `hill`, `shore`, `water_top`, `water_deep`, `pine`, `tree`, `grass`, `glitter`, `ripple`, `village` |
| `landscape` `outskirts` | `field_far`, `field_near`, `drift`, `path`, `pylon`, `birch`, `birch_mark`, `town`, `town_lit`, `chimney`, `beacon` |
| `cityscape` | `wall_a`, `wall_b`, `wall_c`, `wall_front`, `roof_rim`, `window_lit`, `window_dark`, `sign_a`, `sign_b`, `sign_c`, `road`, `road_far`, `walk`, `line`, `pole`, `lamp`, `lamp_pool`, `skyline` |
| `cityscape` `panel` | The keys above plus `window_cool` (blue windows), `seam` (panel seams), `yard` (front yards), `tree` (street trees), `rut` (wheel ruts in the snow) |
| `still_life` `classic` | `wall_top`, `wall_low`, `window_light`, `table`, `table_edge`, `grain`, `drape`, `drape_light`, `bottle`, `jug`, `jug_band`, `apple`, `apple_blush`, `lemon`, `grape`, `stem`, `gloss` |
| `still_life` `desk` | `wall_top`, `wall_low`, `table`, `table_edge`, `grain`, `lamp_light`, `laptop`, `laptop_key`, `editor`, `mug`, `coffee`, `phone`, `wallpaper_a`, `wallpaper_b`, `lamp`, `pot`, `soil`, `leaf`, `leaf_edge`, `cover`, `pages`, `pen`, `gloss`, `steam` |
| `still_life` `cafe` | `wall_top`, `wall_low`, `window`, `frame`, `table`, `table_edge`, `vein`, `cup`, `latte`, `foam`, `plate`, `sponge`, `frosting`, `cream`, `berry`, `fork`, `glass`, `coffee_milk`, `milk`, `ice`, `straw`, `phone`, `wallpaper_a`, `wallpaper_b`, `case`, `gloss`, `bokeh` |
| `still_life` `gaming` | `wall_top`, `wall_low`, `table`, `table_edge`, `grain`, `monitor`, `game_sky_a`, `game_sky_b`, `game_hill`, `game_near`, `hud`, `hp`, `keyboard`, `pad`, `mouse`, `headset`, `can`, `can_label`, `can_top`, `gloss`, `screen_spill` |
| `still_life` `kitchen` | `wall_top`, `wall_low`, `table`, `table_edge`, `check`, `window_night`, `window_haze`, `block`, `block_far`, `block_lit`, `block_cool`, `lamp_pool`, `frame`, `sill`, `glass`, `tea`, `holder`, `spoon`, `player`, `player_face`, `grille`, `dial`, `cassette`, `label`, `reel`, `gloss`, `steam`, `snow`, `lamp_light` |

In the `classic` set, changing only `drape` derives `drape_light` automatically in the same hue. The hue cycle of the RGB lighting starts at `scene_modern.RGB_PHASE`.

## Background and Lines

| Field | Default | Effect |
|---|---|---|
| `background.type` | `glow` | `flat`, `gradient`, `glow`, `scene` |
| `background.scene` | `cityscape` | Scene drawn behind the figure when `type` is `scene`: `cityscape`, `landscape`. The time of day is `scene.time` |
| `line.weight` | 1.0 | Overall line weight factor |

With a `scene` background the figure takes the scene's light direction, the time of day tint on skin and clothes (`character.SCENE_TINTS`), and the time of day color on the rim light (`SCENE_RIMS`).

## Examples

### Figure

```json
{
  "style": "illustration",
  "framing": "upper_body",
  "character": {
    "head": {"yaw": -0.2},
    "eyes": {"gaze": [0.15, 0.0]},
    "hair": {"bangs": "parted", "part": 0.0, "tuck": "none"},
    "pose": {"preset": "hand_on_hip"}
  },
  "palette": {"hair": "#6B4A3A", "hair_highlight": "#C9A48A", "eye": "#4F7FB8"},
  "light": {"direction": [0.55, -0.65, 0.55]}
}
```

When the face turns left (negative `yaw`), switch the light x to positive to light the broad side of the face.

### Body turn, pose, body type

```json
{"style": "anime", "framing": "full_body", "canvas": {"width": 1024, "height": 1600},
 "character": {"sex": "male", "build": "athletic", "outfit": {"type": "denim_jacket"},
               "hair": {"style": "two_block"}, "pose": {"preset": "walking", "turn": "side"},
               "expression": "smile"}}
```

### Group and scene compositing

```json
{"style": "illustration", "framing": "full_body", "canvas": {"width": 1280, "height": 1600},
 "background": {"type": "scene", "scene": "cityscape"}, "scene": {"time": "dusk"},
 "characters": [
   {"sex": "female", "build": "glamour", "outfit": {"type": "knit_coat"}, "hair": {"style": "bob"}, "expression": "laugh"},
   {"sex": "male", "outfit": {"type": "shirt_slacks"}, "hair": {"style": "slicked"}, "palette": {"shirt": "#E8E4DA"}}],
 "layout": {"type": "side_by_side", "interaction": "hold_hands"}}
```

### Figure study and scenes

```json
{"subject": "nude", "style": "oil", "canvas": {"width": 1600, "height": 1024},
 "nude": {"pose": "reclining"}, "palette": {"drape": "#3E4A6E"}}
```

```json
{"subject": "cityscape", "style": "illustration", "canvas": {"width": 1600, "height": 1000},
 "scene": {"time": "blue_night", "palette": {"window_lit": "#FFE2A0", "sign_a": "#FF9A5C"}}}
```

```json
{"subject": "still_life", "style": "watercolor", "canvas": {"width": 1400, "height": 1050},
 "scene": {"set": "cafe", "palette": {"berry": "#C8325A"}}}
```

### Doomer establishing shot

```json
{"style": "anime", "look": "doomer", "framing": "wide", "canvas": {"width": 1600, "height": 1000},
 "background": {"type": "scene", "scene": "cityscape"}, "scene": {"time": "snow_night", "site": "panel"},
 "character": {"head": {"x": 0.34}, "hair": {"style": "medium"}, "pose": {"preset": "walking"},
               "outfit": {"type": "knit_coat", "hat": "beanie", "shoes": "oxfords", "earrings": "none"}},
 "palette": {"cloth": "#423E3C", "skirt": "#202227", "hat": "#6A7078"}}
```
