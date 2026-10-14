# Character spec reference

All spec keys accepted by `scripts/render.py` and `paintkit.scene`. Full-body-only keys are in `figure-spec.md`, scene operations in `scenery.md`. Lengths are in "head units" (crown to chin = 1.0) and positions are written as canvas fractions (0-1).

## Contents

- Top-level keys
- character
- palette
- placement
- light
- background and foreground
- ambient
- style_overrides
- finish

## Top-level keys

| Key | Default | Description |
|---|---|---|
| `canvas` | [1200, 1500] | [width, height] pixels |
| `style` | "anime" | `anime`, `illust`, `painterly` |
| `seed` | 0 | Random seed of grain and brush strokes |
| `subject` | auto | `portrait` bust, `figure` full body, `none` scene only. Full body when a `figure` key exists |
| `figure` | none | Full body pose and outfit (`figure-spec.md`) |
| `character` | {} | Character gender, form, pose |
| `palette` | {} | 17 colors |
| `placement` | {} | Character size and position |
| `light` | {} | Light direction |
| `background` | pale gradient | List of background operations, layered in order |
| `extras` | none | List of other people in the background, drawn with the full body rig (`figure-spec.md`) |
| `duo` | none | The partner drawn with the main character and the relationship of the two, full body only (two-shot section of `figure-spec.md`) |
| `foreground` | none | List of operations drawn in front of the character (petals and the like) |
| `ambient` | none | Scene color laid over the lower part of the character |
| `style_overrides` | {} | Overrides of the style's render settings |
| `finish` | {} | Overrides of the finishing settings |

## character

| Key | Default | Recommended range | Effect |
|---|---|---|---|
| `gender` | "female" | 2 kinds | `female`, `male`. Face, hair, neck and shoulders, full body build and hands change |
| `jaw_sharpness` | 0.8 | 0-1 | 0 round egg shape, 1 sharp V line |
| `face_width` | 1.0 | 0.9-1.1 | Horizontal scale of the face |
| `chin_length` | 1.0 | 0.9-1.15 | Length scale below the mouth |
| `eye_width` | 0.190 | 0.16-0.21 | Eye width |
| `eye_height` | 0.098 | 0.07-0.11 | Eye height; smaller reads more mature |
| `eye_spacing` | 0.172 | 0.16-0.185 | Distance from the center line to an eye center |
| `eye_tilt` | 0.012 | -0.01-0.025 | Positive lifts the outer corners |
| `iris_scale` | 1.0 | 0.85-1.15 | Iris size scale |
| `gaze` | [0, 0] | each -1-1 | Pupil shift; positive x is screen right |
| `eyelid_open` | 1.0 | 0.55-1.0 | How open the eyes are |
| `brow_angle` | 0.006 | -0.012-0.015 | Positive lifts the brow tails |
| `mouth_width` | 0.115 | 0.09-0.14 | Mouth width |
| `smile` | 0.35 | -1-1 | Height of the mouth corners |
| `lip_fullness` | 1.0 | 0.7-1.4 | Lip thickness |
| `head_tilt` | -4.0 | -10-10 | Head tilt (degrees); positive is clockwise |
| `head_turn` | 0.0 | -2.5-2.5 | Face turn; positive turns to screen right. 1 is about 14 degrees, 2.5 about 35 degrees (three-quarter). Values out of range are clipped to 2.5 |
| `hair_style` | "long_straight" | 12 kinds | `long_straight`, `long_wavy`, `bob`, `short` short cut, `medium` medium length covering the ears, `slicked` short slicked back, `layered` male layered cut with crown volume and pointed texture, `long_curly` long curly (clumped silhouette and curl texture), `layered_bob` jaw-length layered bob, `two_block` two-block cut keeping the top long with the sides and back cut short, `perm` short perm with volume and small curls, `pixie` pixie cut with the ears showing |
| `bangs` | "side_swept" | 6 kinds | `side_swept` diagonal fringe, `see_through` thin see-through fringe, `parted` parted curtain bangs, `short_fringe` short fringe above the forehead, `swept_back` swept back with no fringe, `layered` sharp fringe swept one way (brushing the brows) |
| `parting` | -0.10 | -0.15-0.15 | x position of the parting |
| `hair_seed` | 7 | integer | Random seed of hair variation |
| `outfit` | "vneck" | 7 kinds | `vneck`, `turtleneck`, `blazer`, `offshoulder`, `crewneck` round knit, `shirt` collared shirt, `suit` suit and tie |
| `skin_tone` | "default" | 7 kinds | `default` gender default colors, `fair`, `light`, `medium`, `tan`, `brown`, `deep` (light to deep). `skin`, `skin_shadow`, `blush`, `lip` change together and colors written in `palette` win |
| `eye_shape` | "default" | 6 kinds | `default` gender default eyes, `round` round eyes, `almond` almond, `upturned` outer corners lifted, `droopy` outer corners dropped, `monolid` single lid without the crease line |
| `brow_shape` | "default" | 4 kinds | `default`, `straight` straight, `arched` arched, `thick` thick brows |
| `nose_shape` | "default" | 3 kinds | `default`, `dot` small nose drawn as one dot, `bridge` nose with a visible bridge line and nostrils |
| `mouth_shape` | "default" | 3 kinds | `default`, `small` small mouth, `heart` full lips with a clear cupid's bow |
| `hat` | "none" | 2 kinds | `none`, `beanie` knit beanie. Supported in busts and in full body front, three-quarter, profile and back views. Hair standing above the beanie is erased; fringe and side hair under the brim stay |

### Three-quarter (head_turn over 1)

- Turns over 14 degrees get a three-quarter correction step by step (results at 14 degrees or less stay the same)
    + Near side : the head silhouette is kept and the back of the head and nape hair show; the near ear is drawn over the face
    + Near cheek : the cheek outline turns inward about halfway with the face, so the cheek does not get wide and flat
    + Far side : a round cheek curve is redrawn from the cheekbone to the chin tip. Cheek space remains outside the far eye corner, nose tip and mouth corner, so the nose does not break the outline
    + Roundness of the cheek curve : rounder with lower `jaw_sharpness` and for men
    + Side hair : near side hair stays over the ear and moves only a little toward the face; far long fringe and side hair go behind the face
- Give `gaze` opposite to the head turn (about 0.4-0.55) to look at the viewer
- Three-quarter bust example : `illust_three_quarter.json`

### Male defaults

When `gender` is `male`, the values below fill the keys not written in the spec. Keys that are written stay as they are.

| Key | Male default |
|---|---|
| Face | `jaw_sharpness` 0.85, `face_width` 0.95, `chin_length` 1.05, `head_tilt` -2 |
| Eyes | `eye_width` 0.182, `eye_height` 0.062, `eye_tilt` 0.014, `iris_scale` 0.80, `eyelid_open` 0.92 |
| Brows and mouth | `brow_angle` 0, `mouth_width` 0.125, `smile` 0.10, `lip_fullness` 0.45 |
| Hair and outfit | `hair_style` "layered", `bangs` "layered", `parting` -0.06, `outfit` "shirt" |
| Colors | `skin` "#f6dccb", `skin_shadow` "#dca592", `blush` "#e9a497", `lip` "#c98d84" |

- A male face gets volume from an angular jawline, shade under the cheekbones, and highlights on the brow bone and nose bridge
- Male eyes are a long narrow almond with a thick upper lid line running past the outer corner; brows are low and thick
- The male neck shows the sternocleidomastoid line and a faint Adam's apple; blush and lip color are pale
- Ears show with `short`, `slicked`, `medium`, `layered`, `two_block`, `perm`, `pixie` hair
- Women can also use `short`, `slicked`, `layered` hair and `shirt`, `suit` outfits

## palette

| Key | Use | Design tip |
|---|---|---|
| `skin` | Skin base | High value, low saturation |
| `skin_shadow` | Skin shadow | Redder and more saturated than the base |
| `blush` | Blush on cheeks and around the eyes | Pink to coral |
| `lip` | Lips | Deeper than the blush |
| `hair` | Hair base | Main color candidate |
| `hair_shadow` | Hair shadow | 55-65% of the base value |
| `hair_light` | Hair highlight | Bright color shifted toward the light color |
| `iris` | Iris | Accent color candidate, high saturation |
| `eye_white` | Eye white | White with a slight grey |
| `line` | Base line color | Dark brown or dark navy |
| `cloth` | Main outfit | |
| `cloth_shadow` | Main outfit shadow | Blue-violet for light clothes |
| `cloth2` | Jacket (blazer, suit), full body bottoms | Shadow is derived automatically |
| `shoe` | Full body shoes, belt | |
| `accent` | Tie, male underwear band, training shorts stripe | Complementary to the outfit color draws the eye |
| `outer` | Full body jacket and coat (denim, leather, long coat) | Empty uses the material color |
| `hat` | Hat (`character.hat`) | Default #2b2c33; a value gap from the hair color makes the edge read |

- The `character.skin_tone` preset sets the 4 colors `skin`, `skin_shadow`, `blush`, `lip` at once, and colors written here win over the preset

## placement

| Key | Default | Description |
|---|---|---|
| `head_height` | 0.413 | Head height / canvas height |
| `eye_center` | [0.5, 0.36] | Position of the midpoint between the eyes (canvas fraction), bust only |
| `pelvis` | [0.5, 0.47] | Position of the pelvis center, full body only (the full body `head_height` default is 0.115) |
| `shot` | none | Full body framing preset `full`, `thigh`, `knee`, `waist`, `bust`. Size and position are computed automatically |
| `x` | 0.5 | Horizontal position of the character center (of both characters in a two-shot) used with `shot` |

- `shot` cannot be used with `head_height` or `pelvis`, and not for busts (`portrait`)
- Crop positions per preset are in the framing section of `figure-spec.md`

## light

| Key | Default | Description |
|---|---|---|
| `azimuth` | 135 | Light direction (degrees). 0 right, 90 top, 135 top left, 45 top right |
| `elevation` | 42 | Tilt toward the viewer. Higher is front light, lower is side light |

## background and foreground

Lists of operation objects, layered from top to bottom.

| type | Keys | Description |
|---|---|---|
| `gradient` | `top`, `bottom`, `angle`(90) | Two-color linear gradient |
| `glow` | `color`, `center`([0.5, 0.35]), `radius`(0.45, height fraction), `opacity`(0.6) | Soft round light |
| `bokeh` | `colors`, `count`(26), `size`([30, 110]), `opacity`(0.35), `seed` | Out-of-focus light circles |
| `wash` | `colors`, `scale`(0.32, height fraction), `seed` | Bleeding color fields, for painterly backgrounds |
| `light_shafts` | `color`, `count`(3), `angle`(62), `width`(0.10), `opacity`(0.3), `seed` | Diagonal light shafts |
| `petals` | `color`, `count`(26), `size`([8, 26]), `seed` | Scattered leaf-shaped pieces |

- Sky, mountain, water, tree, city street, interior and doomer city operations (`sky`, `ridge`, `water`, `tree`, `street`, `room`, `panel_blocks`, `snow` and others, 21 kinds) are in `scenery.md`

## ambient

| Key | Default | Description |
|---|---|---|
| `color` | required | A color from the lower background is recommended |
| `opacity` | 0.25 | Strength of the overlay |
| `from` | 0.55 | Start height (canvas height fraction) |

## style_overrides

| Key | anime | illust | painterly | Description |
|---|---|---|---|---|
| `shadow_softness` | 0.02 | 0.16 | 0.30 | Softness of form shadow edges |
| `cast_softness` | 0.0 | 0.012 | 0.02 | Blur of cast shadows |
| `shadow_strength` | 1.0 | 0.85 | 0.9 | Shadow opacity |
| `face_shadow_level` | -0.10 | 0.05 | 0.18 | Larger widens the face shadow area |
| `line_width` | 0.0045 | 0.003 | 0.0 | Outline width, 0 means no lines |
| `line_opacity` | 1.0 | 0.75 | 1.0 | Line opacity |
| `line_variation` | 0.6 | 0.7 | 0.6 | How much lines thin on the light side |
| `airbrush` | 0.5 | 1.0 | 1.0 | Strength of blush and gradients |
| `hair_strands` | 1.0 | 1.3 | 0.6 | Density of hair strand lines |
| `hair_highlight` | "band" | "soft" | "soft" | `band` jagged band, `soft` blurred band, `none` |
| `eye_detail` | 1.0 | 1.0 | 0.8 | Iris texture and secondary highlight |
| `rim_light` | 0.0 | 0.8 | 0.3 | Light on the edge toward the light |
| `lip_render` | "tint" | "full" | "full" | `tint` pale tint, `full` painted lip shape |

## finish

| Key | Description |
|---|---|
| `diffusion` | Diffusion glow strength (0-0.4) |
| `bloom` | Strength of bright-area bleed (0-0.5) |
| `contrast`, `saturation` | Scale factors around 1.0 |
| `shadow_tint`, `highlight_tint` | Colors laid on dark and bright areas |
| `tint_strength` | Tint strength (0-0.25) |
| `vignette` | Darkening at the edges (0-0.4) |
| `grain` | Film grain (0-0.03) |
| `radii` | painterly only, list of brush radii (large to small), default [26, 13, 6, 3, 2] |
| `weave` | painterly only, canvas texture strength |
| `tilt` | Picture tilt (degrees), positive is counterclockwise. 0 is the default, 3-8 is a natural Dutch angle. Zooms in automatically so no empty corners appear |
| `preset` | A named finishing bundle. It sits on top of the style defaults and the spec's other `finish` keys win over it. Currently 1 kind, `doomer` (doomer section of `style-guide.md`) |
