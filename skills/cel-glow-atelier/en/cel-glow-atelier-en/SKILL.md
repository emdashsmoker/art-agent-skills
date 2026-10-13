---
name: cel-glow-atelier-en
description: Illustration atelier painting with Python alone (numpy, OpenCV), no image model. Parametric rigs shape the forms and one light vector drives all shading through masks, in three flavors - crisp cel-shaded anime with angel-ring hair, soft illustration with airbrush, rim light and bloom, and oil painting rebuilt from brush strokes. Paints women and men as busts and full figures (any view, 20 outfits, 12 hair styles, face presets, 6 skin tones), two-shots, city nights, snow, landscapes, interiors, objects and still lifes under one light. References - process.md (process), portrait-spec.md (character keys), figure-spec.md (full body, poses, outfits, two-shots), scenery.md (scenes), style-guide.md (palettes, lighting), paintkit-api.md (drawing API). Use when the user asks to draw with code, draw an illustration, character, couple, landscape, city night view, background or still life, wants anime, illustration or oil painting style, or needs a picture without a diffusion model. Not for charts, diagrams or logos.
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and THIRD_PARTY_NOTICES.md
---

# Cel Glow Atelier

> **Translation notice** : This skill is an English translation of the Korean original (`cel-glow-atelier`). Translation can shift nuance, so instructions in this version may behave differently from the original intent and logic. The code, presets and examples are identical to the original; the written instructions are the translated part.

A skill that paints pictures with code alone. It uses no diffusion model API and no 3D modeling.

## Principle

- Typing coordinates directly fails
    + Language models have a weak sense of pixel coordinates
    + Language models are strong in proportion, process and color theory
- So a picture is split into 3 decisions
    + (Form) decided by parameters and control points; the engine handles curves and anti-aliasing
    + (Shading) derived automatically from one light vector through mask operations
    + (Style) the same forms with only render settings and post-processing swapped
- Looking at the render and fixing it, over and over, decides the quality

## Setup

- Two packages are needed, numpy and OpenCV
- Check them before working with the command below

```bash
python3 -c "import numpy, cv2; print(numpy.__version__, cv2.__version__)"
```

- If missing, install `numpy` and `opencv-python-headless` the way your environment does
- All scripts are relative to `scripts/` in this skill folder

## Choosing a path

| Request | Path | Method |
|---|---|---|
| Character bust (front up to about 35 degree three-quarter) | A1. Bust rig | Write a spec JSON, run `scripts/render.py` |
| Full body, upper body, hand gestures, figure study, sitting, leaning, profile, back view | A2. Full body rig | Add a `figure` key to the spec, run `scripts/render.py` |
| Two-person shot (couple, holding hands, arm in arm, arm around shoulders, face to face) | A2. Full body rig | Add a `duo` key to the spec |
| Other people in the background | A2. Full body rig | Add an `extras` list to the spec |
| City streets, mountains and lakes, fields, interiors (no person) | A3. Scene builder | Write `"subject": "none"` and a list of `background` operations |
| Doomer mood (panel apartment blocks, power lines, street lamps, snowy nights) | A2, A3 | City operations + `finish.preset` `"doomer"` (doomer section below) |
| Character + props, accessories, added elements | B. Mixed | `scene.build`, then add layers, then call `scene.finish` |
| Angular objects such as computers, appliances, furniture | C1. Object builder | Write a script with boxes and cylinders from `paintkit.objects` |
| Still life, organic forms, compositions no builder covers | C2. Free scene | Write a script with `paintkit` primitives |

- A1, A2 and A3 share one spec format and combine (e.g. full body character + city street background + nearby passers-by)
- For a man set `character.gender` to `"male"`; face, hair, body and hands change together
- Read `references/figure-spec.md` before working on path A2
- Read `references/scenery.md` before working on path A3
- Path B example : `assets/examples/custom_addition_example.py` (adds a necklace and a hairpin)
- Path C1 example : `assets/examples/desk_setup_example.py` (a desk with monitor, laptop and keyboard)
- Path C2 examples : `assets/examples/still_life_example.py` (vase still life), `assets/examples/landscape_example.py` (low-level landscape), `assets/examples/doomer_still_life_example.py` (kitchen window at night, reusing the scene operations for the view and the cigarette smoke)
- Read `references/paintkit-api.md` before working on path C

## Work order

Pictures fail less when made in process order. Details in `references/process.md`.

1. (Plan) Fix the characters, mood, style, light direction and each character's outfit from the request
    + Pick outfits from the list matching each character's gender (gender groups of the full body `outfit` below)
    + When the user lists outfit examples, give each example to a character of the matching gender and pick the same-situation outfit of the other gender for the others (e.g. male `trunks` for a female bikini, male `open_shirt_shorts` for a female crop top and hot pants)
    + Dress a character in the other gender's outfit only when the user states that combination
    + With 2 or more characters, give each a different hair style, eye shape and skin tone (so the people in one picture do not share one face)
2. (Design) Write the palette and composition first as a 5-10 line note
    + Colors improvised while coding break the harmony
    + Palette rules in `references/style-guide.md`
3. (Write) Copy one spec from `assets/examples/` and edit it
4. (Render) Run the command below; a bust takes about 10 seconds, a full body about 15-30 seconds

```bash
python3 scripts/render.py my_spec.json out.png --stages stages.png
```

5. (Review) Open the result PNG and check it with your own eyes
    + In an environment that cannot view images, ask the user to check the result
    + Find defects with the review checklist below, edit the spec and render again
    + Zoom in on the face and check it separately (eyes, jawline, hair edges)
6. (Deliver) Deliver the final PNG, and the process sheet (`--stages`) on request

## Spec essentials

All keys and ranges are in `references/portrait-spec.md`. The most used keys are below.

```json
{
  "canvas": [1200, 1500],
  "style": "anime",
  "character": {
    "gender": "female",
    "jaw_sharpness": 0.85,
    "head_turn": 0.65,
    "head_tilt": -5,
    "gaze": [-0.45, 0.0],
    "hair_style": "long_straight",
    "bangs": "side_swept",
    "outfit": "blazer"
  },
  "palette": {"hair": "#2b3050", "hair_shadow": "#16182a", "hair_light": "#9aa9dc", "iris": "#3f7fb5"},
  "light": {"azimuth": 135, "elevation": 42},
  "background": [{"type": "gradient", "top": "#b9c8e6", "bottom": "#e9eef7"}]
}
```

- `style` : one of `anime`, `illust`, `painterly`
- `gender` : `female`, `male`. For a man, the keys left out get male defaults
- `hair_style` 12 kinds
    + (original) `long_straight`, `long_wavy`, `bob`, `short`, `medium`, `slicked`, `layered`
    + (v13) `long_curly` (long curly), `layered_bob` (layered bob), `two_block` (two-block cut), `perm` (short perm), `pixie` (pixie cut)
- `bangs` : `side_swept`, `see_through`, `parted`, `short_fringe`, `swept_back`, `layered`
- The male default hair is `layered` (crown volume, pointed texture, fringe brushing the brows)
- `outfit` : `vneck`, `turtleneck`, `blazer`, `offshoulder` (female), `crewneck`, `shirt`, `suit`. Left out, female `vneck`, male `shirt`
- A misspelled key stops with an error that prints the allowed keys

### Face presets and skin tone

```json
"character": {"gender": "female", "hair_style": "long_curly", "skin_tone": "brown",
              "eye_shape": "almond", "brow_shape": "arched", "nose_shape": "default", "mouth_shape": "heart"}
```

- `skin_tone` : `fair`, `light`, `medium`, `tan`, `brown`, `deep` (light to deep)
    + Skin, skin shadow, blush and lip color change together. Colors written in `palette` win over the preset
- `eye_shape` : `round` (round eyes), `almond` (almond), `upturned` (upturned outer corners), `droopy` (drooping outer corners), `monolid` (single lid)
- `brow_shape` : `straight` (straight), `arched` (arched), `thick` (thick brows)
- `nose_shape` : `dot` (dot nose), `bridge` (nose with a visible bridge)
- `mouth_shape` : `small` (small mouth), `heart` (full heart-shaped lips)
- All left out or `default` gives the gender's default face; the same keys apply to busts and to the front, profile and back views of full bodies
- The same keys work in the `character` of the two-shot partner (`duo.partner`) and of background people (`extras`)
- Examples : `face_curly_brown`, `male_two_block` (busts), `figure_pixie_city`, `male_perm_park` (profile), `figure_bob_lake` (back view), `duo_tones_night` (two-shot)

### Full body and scenes

```json
{
  "canvas": [1100, 1800],
  "style": "anime",
  "character": {"head_turn": -0.55, "gaze": [0.4, 0], "hair_style": "long_straight"},
  "figure": {"pose": "contrapposto", "outfit": "sweater_pants", "build": {"waist": 0.96}, "ground_shadow": 0.5},
  "placement": {"head_height": 0.115, "pelvis": [0.5, 0.47]},
  "background": [
    {"type": "sky", "top": "#3b3f7a", "bottom": "#f4a57a", "horizon": 0.47},
    {"type": "street", "horizon": 0.47, "time": "dusk", "eye": 0.9, "seed": 7, "cars": 4, "people": 5}
  ]
}
```

- `pose` : `standing`, `contrapposto`, `akimbo`, `wave`, `clasped`, `peace`, `showcase`, `walk`, `sitting`, `sitting_crossed`, `three_quarter`, `lean`, `arms_crossed` (arms crossed), `pockets` (hands in pockets), `stretch` (stretching)
- Profile `pose` : `side_stand`, `side_walk`, `side_sit`, `side_wave`, `side_lounge` (sofa), `side_lean` (pillar). Set `right` or `left` with `facing`
- Back view `pose` : `back_stand`, `back_walk`, `back_lookback`, `back_sit`. Set `look` to `away` (back of the head), `left`, `right` (looks back in profile), `left_3q`, `right_3q` (looks back in three-quarter)
- Hand angles : `hand_left_roll` (-90-90), `hand_left_pitch` (0-75) in `pose_overrides`, with `right` pairs
    + If a hanging hand looks flat, `roll` 60-75 shows its thumb side
    + A waving hand tips toward the viewer with `pitch` 30-40
- Full body `outfit` 20 kinds (left out, female `dress`, male `shirt_pants`)
    + (Female) `dress`, `blouse_skirt`, `bodycon`, `swimsuit` (alias `bikini`), `crop_hotpants`, `knit_dress` (knit dress), `tank_jeans` (tank top and jeans)
    + (Male) `trunks` (swim trunks), `open_shirt_shorts` (open short-sleeve shirt and shorts)
    + (Unisex) `suit` (suit), `shirt_pants`, `tshirt_jeans`, `sweater_pants`, `hoodie_jeans`, `tank_shorts` (tank top and training shorts), `denim_jacket_chinos`, `leather_jacket_jeans`, `coat_turtleneck` (long coat), `innerwear` (drawers for men), `none`
    + The engine draws the outfit written in the spec regardless of gender. Matching outfits to gender is the job of whoever writes the spec
    + Jacket and coat color is `palette.outer`; empty uses the material color (denim blue, leather black, coat camel)
- `build` : body scale factors (`bust`, `waist`, `hips`, `shoulders`, `legs`, `muscle`), 1.0 is the default
- `heels` : true for high heels
- `furniture` : `stool`, `chair`, `sofa`, `pillar`, `bed`, `none`. Seated poses default to `stool`, `lean` to `pillar`. `bed` is for front seated poses only, profile takes the 5 kinds without `bed`, back view takes `stool`, `chair`, `none`
- Arms are easiest to set by wrist targets (`reach_left`, `reach_right`)
- Framing is easiest with `placement.shot` : one of `full`, `thigh`, `knee`, `waist`, `bust` and a horizontal position `x`
    + Direct setting is `placement.head_height` and `pelvis` : 0.115 full body, 0.20 knee up, 0.30 upper body
    + A Dutch angle is `finish.tilt` 3-8 degrees
- In a street scene with a standing character, match `street.horizon` to the pelvis height and use `eye` 0.9 (perspective match)
- Add distant cars and passers-by with `cars`, `people` of `street`
- Put nearby people in top-level `extras` and place them on the street with `"at": [x, z]` in meters
- `outfit` `none` is a body without clothes. The engine has no pelvic or female chest mark shapes, so none are drawn (same for `innerwear`, `swimsuit`, bare-chested `trunks`)
- An interior background is one `room` operation, like `{"type": "room", "window": "night", "lamp": [0.88, 0.48]}`
- A hat is `character.hat` `"beanie"` (beanie), color `palette.hat`. Front, three-quarter, profile and back views all supported
- A cigarette is `figure.cigarette` : `left`, `right` (between index and middle finger), `mouth` (mouth corner). Smoke rises automatically
    + A cigarette in a pocketed hand (`pocket`, `tucked`) stops with an error
    + `mouth` is not drawn in a back view showing only the back of the head (`look` `away`)

### Two-shot

```json
{
  "canvas": [1400, 1600],
  "character": {"gender": "female", "hair_style": "long_wavy"},
  "figure": {"pose": "standing", "outfit": "dress", "heels": true, "ground_shadow": 0.45},
  "duo": {
    "pose": "arm_in_arm",
    "partner": {
      "character": {"gender": "male"},
      "figure": {"pose": "standing", "outfit": "suit"}
    }
  },
  "placement": {"shot": "full"}
}
```

- `duo.pose` : `side_by_side`, `hold_hands`, `arm_in_arm`, `arm_around`, `face_to_face`
- The partner stands on the `side` (default `right`), is sized by real height ratio, and both feet rest on the same floor
- Hand positions at contact points and gaze are set automatically; details in the two-shot section of `references/figure-spec.md`

### Doomer mood

```json
{
  "style": "anime",
  "character": {"gender": "male", "hat": "beanie"},
  "palette": {"cloth": "#24242a", "cloth2": "#2e323c"},
  "figure": {"pose": "pockets", "outfit": "hoodie_jeans", "cigarette": "mouth"},
  "background": [
    {"type": "sky", "top": "#141a28", "bottom": "#3a3446"},
    {"type": "ground", "top": 0.8, "color": "#b9bec8"},
    {"type": "panel_blocks", "time": "night", "blocks": [{"x": [0.1, 0.9], "base": 0.82, "top": 0.2}]},
    {"type": "power_lines", "kind": "wood"},
    {"type": "streetlamp", "base": [0.75, 0.86], "height": 0.5},
    {"type": "snow", "count": 500}
  ],
  "finish": {"preset": "doomer"}
}
```

- 6 city operations : `panel_blocks` (panel apartment blocks), `power_lines` (wooden poles, pylons), `streetlamp`, `snow`, `fog`, `bare_tree` (leafless tree, birch)
- `finish.preset` `"doomer"` : lower saturation, blue-grey shadows, sodium orange highlights, vignette, film grain. The spec's `finish` keys win over the preset
- Keep warm colors only in window light, street lamps and the cigarette ember; paint the rest in blue-grey and ink black
- Put `ground` before `panel_blocks`; a block reads as standing on the ground when its `base` sinks below the ground line
- 7 examples : `doomer_male`, `doomer_female`, `doomer_duo`, `doomer_establishing` (establishing shot), `doomer_city`, `doomer_landscape` (json), `doomer_still_life_example.py` (still life)
- Detailed operation keys in the city operations section of `references/scenery.md`, color recipe in the doomer section of `references/style-guide.md`

### 3 keys that bring life

- `head_turn` : turns the face left or right; 0 looks like a front ID photo. 1.0 is 14 degrees, 1.5-2.5 is three-quarter (21-35 degrees)
- `head_tilt` : head tilt; 3-6 degrees looks natural
- `gaze` : pupil direction; set opposite to the head turn to look at the viewer

## Styles

| Style | Render traits | Post-processing |
|---|---|---|
| `anime` | Two-step shading with crisp edges, colored lines, hair highlight band | Diffusion glow, bloom, light grain |
| `illust` | Soft gradient shading, thin lines, rim light, full lips | Glow, bloom, vignette, color grading |
| `painterly` | No lines, broad soft light and shade | Brush stroke reconstruction (large brush to small), canvas texture |

- Fine-tune each style with the `style_overrides` and `finish` keys
- The painterly style gets more convincing with smaller eyes and fuller lips (`eye_height` 0.078, `lip_fullness` 1.3)

## Review checklist

- (Face) Do both eyes match the intended size and height
- (Face) Is the jawline smooth, with no kinks or bumps
- (Face) Are the hair, eye shape and skin tone of the people in one picture distinct from each other
- (Hair) Are there no skin-colored gaps at the forehead and temples
- (Hair) Does the fringe avoid covering the eyes too much
- (Shading) Are all shadows on the side away from the light
- (Color) Is the background lower in contrast than the character, without the character sinking into it
- (Full body) Do the hands reach their intended positions, without elbows piercing the body
- (Full body) Do the feet rest on the floor line and shadow, and does the character's size match the background horizon
- (Full body) Do the curves of waist, hips and chest read as the intended body type
- (Full body) Does a man read as an inverted triangle with shoulders wider than hips, and a broad flat chest
- (Full body) Does a seated character's bottom sit on the seat surface, and does a leaning shoulder touch the pillar
- (Profile) Do the nose and chin point in the direction of travel, and are the far limbs behind the body
- (Back view) Do the back of the head and the nape join naturally, and does a looking-back face sit over the shoulder
- (Three-quarter) Is the far eye inside the cheek outline, and does the back hair continue behind the near ear
- (Two-shot) Do held hands and linked arms actually touch, are both people's feet on the same floor line, does the height difference look natural
- (Outfit) Does each character's outfit come from that gender's list, with no other-gender outfit the user did not ask for
- (Outfit) Do sleeves and wrists of pocketed hands end at the pocket, and do lace and denim textures stay inside the outfit
- (Hands) Are the fingers free of tangles, and do palm and back of the hand face the intended way
- (Objects) Is every object lit from the same direction, and do floor shadows touch the objects
- (Doomer) Are warm colors only in window light, street lamps and the cigarette ember, and does no hair stick out above the beanie
- (Doomer) Does the cigarette sit between the fingers or at the mouth corner, does smoke start at the ember, do the wires end at the far pole
- (Composition) Is the space above the head and the left-right balance appropriate
- (Finish) Are there no defects such as lines, dots or empty areas at the edges

## Common problems and fixes

| Symptom | Fix |
|---|---|
| Startled doll-like eyes | `eyelid_open` 0.85-0.92, `iris_scale` 0.95 |
| Face looks wide and flat | Raise `jaw_sharpness`, `face_width` 0.95 |
| Front view looks bland | `head_turn` 0.5-0.8, `head_tilt` 3-6, `gaze` the opposite way |
| Hair is one solid lump | Widen the value gap of `hair` and `hair_shadow`, set `hair_light` |
| Character sinks into the background | Lower background saturation and contrast, `style_overrides.rim_light` 0.6 or more |
| Painterly face is smeared | Last `finish.radii` value to 2, raise the canvas resolution |
| Colors look muddy | Move shadow hues toward red or purple and raise their saturation |
| Arm bends awkwardly | Adjust the `reach_*` target; for the opposite solution `elbow_*` -1 |
| Elbow of a hand near the face juts sideways | Shrink `arm_*_scale` to [0.45, 0.65] so the arm reads as coming forward |
| Face is smeared in a full body | Raise `head_height` (knee-up framing), canvas height 1800 or more |
| Character floats on the street | `ground_shadow` 0.4 or more, match `street.horizon` to the `pelvis` y |
| Body looks flat | `build` `waist` 0.95, `hips` 1.05, `bust` 1.08, pose `contrapposto` or `showcase` |
| Arm is stiff and straight | Pull the `reach_*` target toward the body so the elbow bends |
| Street looks empty | `street` `cars` 3-6, `people` 5-10 |
| Object seems to float | Add a floor shadow with `stage.ground_shadow` |
| Man looks like a boy | `jaw_sharpness` 0.85-0.9, `eye_height` 0.060-0.065, `hair_style` and `bangs` to `layered` |
| Male face looks bland | `head_turn` 0.4 or more with opposite `gaze`, `smile` 0.1-0.35, `layered` instead of `slicked` for a wide forehead |
| Hanging hand looks flat | `hand_*_roll` 60-75 |
| Back view looks monotonous | Look over the shoulder with `back_lookback`, `look` `right_3q` to meet the viewer's eyes, close-fitting outfit, side light (`azimuth` 120-140) |
| Far eye of a three-quarter face is hidden | Lower `head_turn` to 2.0 or less, pick `bangs` short on the far side |
| Three-quarter chin juts out sharply | Lower `jaw_sharpness` to 0.6-0.75 (the far cheek curve rounds), `chin_length` 0.95 |
| Male body looks thin | `build` `muscle` 1.2-1.3, `shoulders` 1.05 |
| Background person leaves the frame | Reduce x of `at` or increase z (background people section of `figure-spec.md`) |
| Sofa is cut off | Canvas width 1600 or more; a sofa is about 6 heads wide |
| Two-shot hands do not touch or overlap | Adjust `duo.gap` by 0.1-0.2 (arm in arm 1.3-1.5, holding hands 1.85-2.1) |
| Hand on the waist covers the front of the pelvis (thigh-up framing) | In `pose_overrides`, `reach_left` [-0.68, -0.34], `reach_right` [0.68, -0.34], `hand_*_pitch` 55 |
| Half the face is dark in backlight | `style_overrides.face_shadow_level` -0.3 |
| Eyes float in a painterly face | `eye_height` 0.078, `lip_fullness` 1.3 |
| One person of a two-shot leaves the frame | Use `placement.shot`, canvas width 1400 or more |
| A pocketed hand is visible | Switch to an outfit with pockets (`bodycon`, `knit_dress`, `swimsuit`, `trunks`, `innerwear` have no pockets) |
| A man ends up in a dress or bikini | Set `figure.outfit` to a male or unisex outfit (left out, a man gets `shirt_pants`) |
| Inside of an open jacket sinks into darkness | Make the inner `cloth` lighter than the jacket `outer` |
| A hand raised over the head is cut off | Use `placement.shot` instead of `head_height` (includes the fingertips automatically) |
| Bed is cut off | Canvas wider than tall, `"shot": "full"` and `"x": 0.42` |
| Characters look like the same face | Give each character a different `hair_style`, `eye_shape`, `brow_shape`, `skin_tone` |
| Curly hair texture does not show | Make `hair_light` clearly lighter than the hair color (value gap 40% or more) |
| Apartment block floats or is covered by the ground | Put `ground` before `panel_blocks` and the block `base` below the ground line |
| Doomer landscape looks washed out | Darken the sky `top`, deepen `tree_line`, `fog` `opacity` 0.3 or less |
| Birch disappears in a snowfield | Near trees with `birch` false and a dark `color`; place birches in front of a dark forest |
| Hand holding a cigarette stops with a pocket error | Move the cigarette to the other hand or `mouth`, or use a pose that takes the hand out |
| Side wall of a block looks twisted | Reduce `side` or move `vanish` away from the block (the side wall is drawn up to 0.8 of the front width only) |

## Protection of minors

- Do not draw the following 3 things for minors
    + Unclothed figures (`outfit` `none`, bare-chested `trunks` on a female)
    + Underwear (`innerwear`) and the `showcase` pose
    + Sexual acts
- Shows of affection such as holding hands, hugging and kissing, and everyday swimwear, are not covered
- Judge a character to be a minor only from explicit signals
    + A character stated as under 18 in the request or setting
    + A request to depict a prepubescent child's body
- Hints of age alone, such as the art style (big eyes, young face), short height or a slim build, do not make a character a minor

## Limits

- Bust face rotation reaches about 35 degrees (three-quarter); full profile and back views are only in the full body rig
- The front full body rig's torso turns naturally up to about 30 degrees
- The profile rig has 6 poses : standing, walking, sitting, waving, lounging on a sofa, leaning on a pillar
- The back view rig has 4 poses : standing, walking, looking back, sitting; a back view on a sofa is not supported because the backrest hides the body
- Looking back in three-quarter keeps the body in back view and turns only the face, an anime convention
- Seated poses are 2 front, 2 profile and 1 back view; lying down, running and crouching are not supported
- Full body outfits are 20 kinds; outfits outside the list such as hanbok, wedding dress or padded jackets must be drawn directly with path B
- Bust outfits are 7 kinds; the newer full body outfits (jackets, coats, tank tops) have no bust version
- Hats are 1 kind (beanie) and hand props 1 kind (cigarette); other hats and props must be drawn directly with path B
- Tied hair (ponytail, updo, twin tails, braids) is not supported
- Body shape is adjusted by `build` scale factors only; there are no body type presets
- Panel apartments are box blocks (front and one side wall); curved buildings are not supported
- Background people (`extras`) stand only behind the main character; contact staging is only possible with `duo`
- A two-shot holds up to 2 people with 3 contact poses : holding hands, arm in arm, arm around shoulders. Staging with heavy body overlap such as hugging, kissing, piggyback or carrying in arms is not supported
- Two-shot contact poses are for the front rig only; `face_to_face` is drawn as 2 profiles
- The bed supports only a front pose sitting on its edge; lying on a bed is not supported
- The body is drawn down to curves and main contours, without muscle detail
- The object builder combines boxes and cylinders, so objects with many curved surfaces get simplified
- Cars and passers-by on the street are simple shapes for distance
- Hands are 7 gestures turned by rotation (`roll`) and tilt (`pitch`); views looking up at a hand from below are not supported
- Elements outside the rigs and builders must be drawn directly with path B or C2, which is harder
- The quality level is clean 2D illustration, a different field from the realism of diffusion models
- For requests it cannot draw, tell the user the possible range first

## Reference files

| File | When to read |
|---|---|
| `references/process.md` | When you need judgment criteria and fixing tips per process stage |
| `references/portrait-spec.md` | When checking all spec keys, ranges, hair and face presets, skin tones, background kinds |
| `references/figure-spec.md` | When setting full body, male body, poses, furniture, profile, back view, background people, two-shots, hand angles, full body outfits, framing |
| `references/scenery.md` | When building city, landscape and interior scenes, doomer city operations, matching perspective of character and background |
| `references/style-guide.md` | When designing palettes, scene lighting recipes, the doomer color recipe, fine-tuning styles |
| `references/paintkit-api.md` | When drawing directly with path B or C (including the object builder `objects`) |
| `assets/examples/*.json` | Starting specs (5 female busts, 4 male busts, 35 full bodies, 6 two-shots, 7 scenes) |
| `assets/examples/*.py` | Example code for the mixed mode and free scenes |
