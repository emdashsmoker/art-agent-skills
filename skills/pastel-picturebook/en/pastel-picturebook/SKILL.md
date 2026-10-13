---
name: pastel-picturebook
description: "A pastel picturebook skill that paints postcard-sized scenes in clear colours, thin lines and tidy cel shading. Big-eyed characters stand upright like paper dolls, smiling or waving, from a sunlit beach, cherry blossoms and a sunset rooftop to cafes, rainy neon streets and snowy nights. It draws with numpy and OpenCV only, without diffusion models, staged as sketch, flat colour, shading, inking and finish. It covers portraits, full figures, scenes of two to four people, outfits, still life, landscape, city, interiors and weather in 8 styles from anime and watercolor to manga and pixel art. Read references/spec.md for setting keys, references/subjects.md for subjects and scenes, references/pipeline.md for stages and defects, references/extending.md for adding subjects, styles and props. Use for '/pastel-picturebook', 'draw with code', 'picture without a diffusion model', 'picturebook-style picture', 'anime character', 'couple picture', 'still life', 'landscape', or any picture request without an image tool."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and OUTPUT_EXCEPTION.md
---

# Pastel Picturebook

> (Translation notice) This English edition was translated from the Korean original of the skill. The scripts and assets are the same files, but the instructions, tables and recommended values were translated, so the performance of the skill and the logic Claude follows with it may differ from the original.

A skill that draws pictures with code alone, without neural networks. It provides a set of tools that turn the stages of making a picture into code (`scripts/`) and the working procedure for using them

## Principles

- The order in which a person draws is implemented as code stages
    + (Sketch) Place forms with curves, skeletons and perspective
    + (Flat colour) Fill each part's mask with a single colour
    + (Shading) Give forms a height, take its normals and compute light and shadow from the light direction
    + (Inking) Turn outlines into strokes with varying width
    + (Finish) Apply the style's post-processing
- The 8 styles share the same sketch and swap only the palette, shading mode and finish
    + Watercolor, pencil, manga, pixel art and film night repaint an existing style (illustration or anime) in the finishing stage
- Picture quality is decided by the loop of looking at the render and fixing it
    + Code cannot see its own coordinate errors, so checking with the eyes is required

## Subjects

| Subject | `--subject` | Content | Default canvas | Styles that suit it |
|---|---|---|---|---|
| Portrait | `portrait` | Bust of a woman or a man | 1200x1600 | All 8 |
| Full figure | `figure` | Woman or man. Front, 3/4 view, back (looking back over the shoulder), side, lying. Standing, sitting, sitting with legs crossed, kneeling, leaning on a wall, walking (side, toward the viewer), running, jumping, crouching, arms crossed, waving, V sign, stretching, chin on hand, holding a cup, book, umbrella, wine glass or phone, hug and kiss (two figures in profile). Clothed or unclothed figure study | 1200x1600 | paint, illust |
| Hand | `hand` | Woman's or man's hand. Back and palm studies (open, relaxed, V, pointing) | 1600x1200 | anime, illust |
| Still life | `still_life` | Bottles, bowls and fruit on a table | 1600x1200 | paint, illust |
| Desk | `desk` | Monitor, laptop, keyboard, mouse, phone, mug, plant, lamp, notebook | 1600x1200 | anime, illust |
| Landscape | `landscape` | Sky, mountain ranges, lake reflection, conifers | 1600x1200 | illust, paint |
| Beach | `beach` | Sky, sea to the horizon, foam, wet and dry sand, palms | 1600x1200 | anime, illust |
| City | `city` | One-point perspective street, day or night | 1200x1600 | anime, paint |
| Park | `park` | Picnic lawn. Mown stripes, wildflowers, a far tree line, green trees, gingham blanket and basket | 1600x1200 | anime, watercolor |
| Cherry-blossom avenue | `sakura` | A tunnel of cherry trees meeting overhead, a path to the vanishing point, fallen and falling petals | 1600x1200 | anime, illust, watercolor |
| Rooftop | `rooftop` | Sunset sky and setting sun, backlit skyline, glass railing, string lights, potted plants | 1600x1200 | anime, illust |
| Fireworks | `fireworks` | Fireworks in the night sky (chrysanthemum, peony, willow), lit towers, a river reflecting the light, a riverside railing | 1600x1200 | anime, manga |
| Panel blocks | `panelka` | Courtyard of panel apartment blocks at night. Lit windows, balconies, entrance lamps, utility poles and wires, sodium street lamps, birches, a swing, snow. Can also be set up as a street between blocks | 1600x1200 | doomer, anime |
| Outskirts | `outskirts` | Edge of town at dusk. Dry grass, a dirt path, pylons and wires to the horizon, a far row of apartment blocks, crows | 1600x1200 | doomer, illust |
| Cafe | `cafe` | Interior at eye height. Window on the street, counter and espresso machine, round tables, pendant lamps. Day or night | 1600x1200 | anime, illust |
| Room | `room` | Living room at eye height. Curtained window, sofa, bookcase, rug, floor lamp. Day or night | 1600x1200 | anime, illust |
| Bedroom | `bedroom` | Bedroom at eye height. Bed with headboard, nightstands and table lamps, curtained window. Night by default | 1600x1200 | anime, illust |
| Bathroom | `bathroom` | Bathroom at eye height. Wall and floor tiles, bathtub, vanity and mirror, glass shower, towels | 1600x1200 | anime, illust |

- (Scenes) Put `backdrop` (another subject as the background) and `companions` (other figures) into a portrait or figure spec to compose a scene
- (Contact) A hand target (`reach`) puts a hand on another figure's hand, shoulder, elbow or back, or on a point of the picture. `lift` lays an earlier figure's hand again over a later one. With `lift_under_head` the lifted part passes under the other figure's hair
- (Scene props) `props` holds a bench (figures seated facing us) and a cafe table (figures seated in profile). A held umbrella keeps the rain off. A figure in profile can lean on a pillar (`profile_pose.wall`)
- (Several people) Three or more people work the same way (the `companions` list). Values for group photos, toasts, dances and selfies are in the several-people section of `references/subjects.md`
- (Weather) Rain, snow or petals with the top-level `weather`. Outdoors it covers the whole picture. Indoors it shows only through the windows
- Setting keys per subject are in `references/subjects.md`. Portrait and face keys are in `references/spec.md`
- For a subject not on the list, write a new module following `references/extending.md`

## Scope

- (Supported) The 18 subjects above, 8 styles, 8 expressions, looks (face shape, eye shape, hair style and colour, skin tone, freckles, identity seed), 5 built-in accessories (cigarette included), 6 held objects, 3 cloth patterns, 3 kinds of weather, composition changes through the spec, composed scenes (any number of figures), hand and arm contact (holding hands, arm over the shoulder, leaning, joined hands), hug and kiss in profile, shared props (bench, table, umbrella), props added through hook modules
- (Unsupported) 3/4 rotation of back views and seated poses, a lying pose seen from the front, skirt folds that drape over the thighs of seated or kneeling figures in profile (trousers recommended), photographic detail
    + For an unsupported request, tell the user the limit first and propose what is possible
- The built-in body tables use adult proportions (adult body and face proportions)
- Rule on minors
    + No nude or sexual depiction of anyone under 18
    + Judge only by explicit signals: an age under 18 set in the request, a minor student status set in the request, a depiction of a pre-pubescent child's body
    + A youthful face, small stature or an anime drawing style are common in adults as well, so they alone are not treated as signs of a minor

## Dependencies

- Python 3.9 or later, numpy, opencv-python
- Check with `python -c "import numpy, cv2"` before starting. If missing, install following the user's environment rules
- No other packages and no external API calls

## Procedure

### 1. Plan

- Pull the subject, style, elements and mood out of the request into a short design memo
    + (Figure) hair, eyes, facial impression, outfit, pose, background
    + (Scene) composition, light direction, key colours, main objects
- How to choose a style

| Style | `--style` | Character | Suits |
|---|---|---|---|
| Anime | `anime` | Ink lines, two-step cel shading, bright colours | Characters, background art, bright moods |
| Illustration | `illust` | No ink lines, grain shading, limited palette, paper texture | Posters, profile images, stylish moods |
| Painting | `paint` | Continuous shading rebuilt with brush strokes, canvas texture | Portraits, still life, classical moods |
| Watercolor | `watercolor` | Illustration base. Bleeding colour pools, darker wet edges, blooms, paper grain | Landscapes, cherry blossoms, lyrical moods |
| Pencil sketch | `pencil` | Illustration base. Graphite tone, cross-hatching that builds up in the dark, pencil outlines | Studies, croquis, calm moods |
| Black-and-white manga | `manga` | Anime base. Ink, screentone dots, bold ink lines | Comic panels, night scenes, dramatic scenes |
| Pixel art | `pixel` | Anime base. Low-resolution grid, few colours, dithering, outline cells | Game-like, retro moods |
| Film night | `doomer` | Anime base. Drained colour on a cold blue-grey ramp, only sodium-orange lights kept, crushed blacks, halation, film grain, vignette | Panel blocks, winter nights, lonely figures |

- If the user names no style, pick one of the subject table's recommended styles and state the reason in one line

### 2. Write the spec

- Write a JSON file holding only the items that differ from the defaults
    + Merge order: `assets/spec_default.json` (figures only), `assets/style_<style>.json`, `assets/subject_<subject>.json`, `assets/sex_<sex>.json` (when `sex` is set), the user spec
- For a man, the single line `"sex": "male"` changes the face, short hair, body, outfit and colours together
- An expression is one word, `"expression": "laugh"`. Appearance is `look` (face shape, eye shape, hair style, hair colour, eye colour, skin tone, freckles, identity seed)
    + To make several figures in the same style look different, give each a different integer in `look.identity`
- Accessories go in `accessories` (glasses, hat, scarf, bag, cigarette). Cloth patterns go in a palette group's `pattern`
- Colours are overridden in the spec's `style.palette`

```json
{
  "pose": {"yaw_deg": 14, "mirror": true},
  "face": {"jaw_sharpness": 1.0, "jaw_width": 0.72},
  "hair": {"length": 1.55, "wave": 0.0},
  "style": {"palette": {"hair": {"base": "#8C3B2E", "shadow": "#5C211B", "light": "#E08A5B", "line": "#3A1410", "deep": "#3A1410"}}}
}
```

- To change the hair colour, set all 5 of `base`, `shadow`, `light`, `line`, `deep`, or use `look.hair_color`
    + Brows and lashes follow the hair colour automatically

```json
{
  "expression": "smile",
  "look": {"face_shape": "round", "eye_shape": "big", "hair_style": "ponytail", "skin_tone": "tan", "freckles": 0.5, "identity": 12},
  "accessories": {"glasses": true, "hat": {"kind": "beanie", "pompom": true}, "scarf": true},
  "style": {"palette": {"scarf": {"pattern": {"kind": "check", "color": "#2F3A5A", "scale": 0.3}}}}
}
```

- Example specs (`assets/`)

| File | Content |
|---|---|
| `example_spec_bob.json` | Bob-haired portrait (with the glasses hook `example_props_glasses.py`) |
| `example_spec_figure_nude.json` | Female front figure study, contrapposto with a hand on the hip |
| `example_spec_figure_back.json` | Female figure study from behind |
| `example_spec_figure_side.json` | Female figure study in profile, arched back |
| `example_spec_figure_seated_side.json`, `example_spec_figure_seated_front.json` | Female seated poses (side, front) |
| `example_spec_portrait_male.json` | Male portrait |
| `example_spec_figure_male.json` | Male full figure (T-shirt, long trousers) |
| `example_spec_figure_male_nude.json` | Male front figure study with a hip cloth |
| `example_spec_figure_male_back.json`, `example_spec_figure_male_side.json` | Male figure studies from behind and in profile |
| `example_spec_figure_male_seated_side.json`, `example_spec_figure_male_seated_front.json`, `example_spec_figure_male_seated_front_nude.json` | Male seated poses (side study, front clothed, front study) |
| `example_spec_hand_male.json` | Male hands (back, palm, pointing) |
| `example_spec_figure_shirt_skirt.json`, `example_spec_figure_coat.json` | Long-sleeved shirt and skirt, a coat over them |
| `example_spec_figure_male_jacket.json`, `example_spec_figure_male_shorts.json` | Male jacket, shorts |
| `example_spec_figure_hanbok.json`, `example_spec_figure_male_hanbok.json`, `example_spec_figure_side_hanbok.json` | Hanbok (female, male, side) |
| `example_spec_figure_male_walk.json`, `example_spec_figure_front_walk.json` | Walking in profile (with the far arm), walking toward the viewer |
| `example_spec_figure_male_arms_crossed.json` | Arms crossed |
| `example_spec_figure_hands_behind_head.json`, `example_spec_figure_male_hands_behind_back.json` | Hands behind the head, hands behind the back |
| `example_spec_figure_holding.json`, `example_spec_figure_side_holding.json` | Holding a cup and a book (front), holding a cup (side) |
| `example_spec_scene_city_night.json` | Figure in a city at night (eyes on the horizon, colour grade) |
| `example_spec_scene_pair.json` | Two figures in a landscape |
| `example_spec_portrait_city_bokeh.json` | Portrait against a blurred city at night |
| `example_spec_city_night.json` | City at night |
| `example_spec_desk_night.json` | Desk in a dark room (screen and lamp light) |
| `example_spec_portrait_laugh.json`, `example_spec_portrait_cry_rain.json` | Laughing ponytail with freckles, a crying portrait on a rainy night street |
| `example_spec_portrait_glasses_beanie.json`, `example_spec_portrait_male_cap.json` | Glasses, pompom beanie, check scarf. A man in a baseball cap, winking |
| `example_spec_figure_hoodie.json`, `example_spec_figure_side_hoodie.json` | Hoodie (front and side), hat, bag, glasses |
| `example_spec_figure_swimsuit.json`, `example_spec_figure_bikini.json`, `example_spec_figure_male_trunks.json` | Striped swimsuit, polka-dot bikini, male swim trunks |
| `example_spec_figure_patterns.json` | Striped shirt, check skirt, scarf |
| `example_spec_cafe_night_rain.json`, `example_spec_room_snow.json` | Cafe on a rainy night, room on a snowy day (`--subject cafe`, `room`) |
| `example_spec_city_rain.json`, `example_spec_landscape_snow.json` | Rainy street, lake in the snow (`--subject city`, `landscape`) |
| `example_spec_scene_cafe.json`, `example_spec_scene_room_night.json` | Figure in a cafe on a rainy day, figure in a room at night |
| `example_spec_figure_wave.json`, `example_spec_figure_peace.json` | Waving, a wink with a V sign by the eye (hand target, palm, hand in front of the face) |
| `example_spec_figure_male_stretch.json`, `example_spec_figure_thinking.json` | Stretching, chin on hand in a coat |
| `example_spec_figure_three_quarter.json`, `example_spec_figure_male_three_quarter.json` | 3/4 full figures (dress, male jacket) |
| `example_spec_figure_side_run.json`, `example_spec_figure_male_side_jump.json`, `example_spec_figure_side_crouch.json` | Running, jumping, crouching in profile |
| `example_spec_figure_lying_back.json`, `example_spec_figure_lying_front.json` | Lying on the back with a knee up, lying on the front propped on the elbows |
| `example_spec_scene_umbrella_rain.json` | Rainy street, two people walking toward us under the man's umbrella, her hand on his arm |
| `example_spec_scene_cafe_date.json` | Two people facing each other at a cafe table (chin on hand, holding a cup) |
| `example_spec_scene_beach.json`, `example_spec_scene_beach_lying.json` | Holding hands and waving on the beach, a figure lying on the sand |
| `example_spec_scene_snow_night.json`, `example_spec_scene_bench.json` | Walking toward us on a snowy night street, arm over the shoulder and leaning in. Holding hands on a lakeside bench |
| `example_spec_scene_embrace.json`, `example_spec_scene_embrace_bath.json`, `example_spec_figure_underwear.json` | Two people in underwear hugging and kissing in a bedroom and a bathroom at night (profile), female underwear (front) |
| `example_spec_bedroom_day.json`, `example_spec_bathroom_night.json` | Bedroom by day, bathroom at night with the sconce on (`--subject bedroom`, `bathroom`) |
| `example_spec_scene_friends_photo.json`, `example_spec_scene_toast_party.json` | Three friends on a cherry-blossom avenue, arms over shoulders and V signs. Four people raising wine glasses in a living room at night |
| `example_spec_scene_dance_rooftop.json`, `example_spec_scene_selfie_fireworks.json` | A couple twirling hand in hand on a rooftop at sunset, a selfie by the river under fireworks |
| `example_spec_scene_look_back.json`, `example_spec_scene_lean_wall.json` | Looking back over the shoulder on a cherry-blossom avenue, leaning on a pillar on a night street |
| `example_spec_scene_cross_legs.json`, `example_spec_scene_picnic_kneel.json` | Sitting with legs crossed in a cafe, kneeling on a picnic blanket in the park |
| `example_spec_scene_doomer_man.json`, `example_spec_scene_doomer_woman.json` | Man in the film-night style (beanie, hoodie, cigarette in the mouth), woman in the film-night style (bob, black hoodie, cigarette in hand). Snowy courtyard of the blocks |
| `example_spec_scene_doomer_pair.json`, `example_spec_scene_doomer_world.json` | Two people seen from behind looking at the lit blocks, a lone figure in a wide courtyard (world establishing shot) |
| `example_spec_panelka_street.json`, `example_spec_still_life_kitchen_night.json` | Snowy night street between panel blocks (`--subject panelka`), kitchen table at night (ashtray, tea glass, can, the blocks outside the window, `--subject still_life`) |

### 3. Render

```bash
cd <skill folder>/scripts
python render.py --subject portrait --style anime --spec <spec>.json --out <output>.png --stages <stage folder>
```

- Without `--subject` the subject is `portrait`
- `--stages` also saves 4 stage images
    + `1_sketch` (sketch), `2_flat` (flat colour), `3_shaded` (shading), `4_inked` (inking)
- `--extras <file>.py` is a hook module for adding props
- Time (measured on 2 CPU cores): anime and illustration 3-10 s, painting 12-20 s, the 4 new media styles about the same as their base style (1-2 s for the finish). A two-figure scene takes about twice as long, a four-figure scene about 4 times, and `--stages` about twice

### 4. Review

- Open the result PNG as an image and look at it. Zoom into the key parts and look again
    + At least one full view and one crop of a focal part such as the face or hands
- What to check
    + (Proportion) spacing of the features, head-to-body ratio, limb lengths
    + (Overlap) fringe and eyes, arms and torso, front-to-back order of objects
    + (Volume) light direction matching shadow direction, sense of mass
    + (Colour) whether the main elements stand apart from each other
    + (Defects) broken lines, floating pieces, seam lines, unintended stains
- When a defect shows, narrow down the stage that causes it with the `--stages` images, then change only the setting involved
    + Form problems in `1_sketch`, colour problems in `2_flat`, shading problems in `3_shaded`

### 5. Iterate and deliver

- Change the spec and render again until the review passes
- Deliver the final PNG with the spec JSON used
    + The same spec and `seed` reproduce the same picture
- If the user is curious about the process, deliver the stage images too

## Common adjustments

| Wanted change | Setting |
|---|---|
| Sharper jaw | `face.jaw_sharpness` 1.0, `face.jaw_width` 0.70, `face.chin_width` 0.10 |
| Upturned eyes | `eyes.tilt` 0.13, `eyes.brow_slant` 0.9 |
| Gentle expression | `mouth.smile` 0.035, `eyes.brow_slant` 0.4 |
| Short hair, waves | `hair.length` 1.5, `hair.wave` 0.06 |
| Facing the other way | `pose.mirror` true |
| Body shape | `figure.shape` factors `shoulders`, `bust`, `waist`, `hips`, `thighs`, `legs` (1.0 as the reference) |
| Back view, side view | `figure.view` "back" or "side" |
| Man | `sex` "male" |
| Seated (side) | `figure.profile_pose.seat` true, `thigh` about 84 |
| Seated (front) | `figure.seat`, legs `foreshorten` [0.34, 1.0] with `toward` [1, 0] |
| Change the outfit | Combine `shirt`, `pants`, `skirt`, `dress`, `jacket`, `coat`, `jeogori`, `chima`, `baji` in `figure.clothes`. null turns one off |
| Long sleeves, shorts | `shirt.sleeve` 1.9, `pants.length` 0.42 |
| Arms crossed | Arm `fore` about -92, the upper arm `"over": true`, the hand underneath `"tucked"` |
| Hand behind the body | That forearm's `toward` [0, -1] |
| Holding something | `figure.holds` {"right": {"kind": "cup"}}, hand pose `"grip"` |
| Backdrop and several figures | `backdrop` {"subject": "city", "place": "horizon"}, `companions` [figure specs] |
| Head-to-body ratio | `figure.body_scale` (0.9 is 6.8 heads, 1.0 is 7.4 heads, 1.05 is 7.7 heads) |
| Pose | Limb angles in `figure.pose`, `shoulder_tilt`, `pelvis_tilt` |
| Still life, desk arrangement | Add, remove or move items in the `objects` list |
| City at night | `night.on` true |
| Show the palm | `view` "palm" in the `hands` item |
| Another street, other mountains | Change `seed` |
| Dramatic light | `light` [-0.8, -0.3, 0.5] |
| Expression | `expression` "smile", "laugh", "sad", "cry", "surprise", "angry", "wink", "kiss". Weaker: {"name": "smile", "amount": 0.5} |
| Face shape, eye shape | `look.face_shape` "round", "long", "square", "heart". `look.eye_shape` "big", "narrow", "droopy", "cat" |
| Hair style | `look.hair_style` "ponytail", "bun", "curly", "bob", "short" |
| Skin, hair, eye colour | `look.skin_tone` in 6 steps from "fair" to "dark", `look.hair_color`, `look.eye_color` |
| Freckles, moles | `look.freckles` 0.6, `look.moles` [[0.35, 0.55]] |
| Look like another person | Change the integer in `look.identity` |
| Hoodie, swimwear, underwear | `hoodie`, `swimsuit`, `bikini`, `trunks`, `underwear` in `figure.clothes` (true gives the defaults. Underwear is a bra and briefs for women, boxer briefs for men) |
| Cloth pattern | `style.palette.<group>.pattern` {"kind": "stripes", "check", "dots", "color", "scale"} |
| Glasses, hat, scarf, bag | `accessories` {"glasses": true, "hat": {"kind": "cap"}, "scarf": true, "bag": true} |
| Interior backdrop | `backdrop` {"subject": "cafe", "room", "bedroom", "bathroom", "place": "horizon"}. For night, `time` "night" in the backdrop spec |
| Rain, snow | `weather` {"kind": "rain"} or {"kind": "snow"} |
| A hand where you want it | `reach` {"mark": "chin"} or {"at": [x, y]} on the arm, `bend` "down", `front` true in front of the face |
| Show the palm (full figure) | `hand_right_view` "palm", hand `open` or `peace` |
| 3/4 full figure | `figure.pose.turn` 30, `pose.yaw_deg` 22 |
| Walking toward the viewer | `figure.pose.stride` {"lead": "left"}. For a full-figure frame, `head_unit` 0.034-0.036 |
| Running, jumping | Leg angles and `lift` (height in the air) in a side `profile_pose`, leg `foot` (toe angle) |
| Lying | `figure.lying` {"face": "up" or "down", "ground": 0.8} on a side figure |
| Holding hands, arm over the shoulder | Both hands `reach` the same `at` point. For the other's shoulder, {"mark": "shoulder_right", "of": "main"} with the companion's `lift` and `lift_under_head` true |
| Hand on the other's arm | Companion arm `reach` {"mark": "elbow_right", "of": "main"}, `lift` the forearm |
| Leaning on someone | `roll_deg` toward the other, `figure.neck_shift` 0.5-0.8, `pose.horizon_drop` |
| Hug and kiss | Two side figures facing each other. Arm `reach` {"mark": "upper_back" or "lower_back", "of": the other}. An arm that lies over the other uses the companion's `lift` ["arm_near"]. `expression` "kiss" |
| Bench, cafe table | Top-level `props` [{"kind": "bench"}] or [{"kind": "table", "elbow_of": "main"}] |
| Umbrella | Main figure `figure.holds` {"right": {"kind": "umbrella"}}, hand `grip`, arm `reach` {"at": between the two faces}, `foreshorten` [1.0, 0.65], `front` true. The rain stays off the area under it |
| Wine glass, phone | `figure.holds` {"left": {"kind": "glass"}} or {"kind": "phone"}, hand `grip` |
| Kneeling | Side legs `thigh` 70 `shin` -90 `foot` 172. On a picnic blanket, backdrop camera `eye_height` 100 and `horizon_drop` |
| Legs crossed | Side `seat` true, near leg `thigh` 94 `shin` 12, far leg `thigh` 84 `shin` -4 |
| Leaning on a wall | Side `profile_pose.wall` true, `lean` -6, near leg `thigh` 36 `shin` -88 `foot` 88 |
| Looking back over the shoulder | Back view with `figure.look_back` true (to the left, {"side": "left"}). The face shows in profile over the shoulder |
| Arm sides of front figures | `arm_left` is the arm on the picture's left. An arm reaching to the middle is `arm_right` for the left person and `arm_left` for the right person |
| Cherry petals | `weather` {"kind": "petals"} |
| New backdrops | `backdrop` {"subject": "park", "sakura", "rooftop", "fireworks", "panelka", "place": "horizon"} |
| Film night | `--style doomer`. Backdrop `panelka` (night) or `outskirts` (dusk), weather `snow` |
| Cigarette | In the mouth `accessories.cigarette` true, in the hand `figure.holds` {"left": {"kind": "cigarette"}}, still life `ashtray` |

## References

- `references/spec.md`: every setting of the portrait and the figure's face, hair, expressions, looks, accessories, palette and patterns
- `references/subjects.md`: setting keys of full figures (with outfits), scene composition (with several people), hands, still life, desk, landscape, city, park and cherry-blossom avenue, rooftop and fireworks, panel blocks and outskirts, cafe and rooms, weather
- `references/pipeline.md`: how each stage is implemented and how the styles differ (other media finishes included). Read it to trace a defect or to build a new style
- `references/extending.md`: how to add hook props, new expression and look presets, new hair styles, new outfits, new built-in accessories, new interior items, new styles, new held objects, new poses and new subjects
