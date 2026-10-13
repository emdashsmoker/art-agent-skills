# Style and palette guide

## Contents

- Definition of the 3 styles
- Palette design rules
- Palette examples by mood
- Telling characters apart and skin tone
- Male characters
- Colors per outfit
- Two-shot colors
- Background design
- Lighting recipes by scene
- Doomer mood
- Fine-tuning per style

## Definition of the 3 styles

| Aspect | anime | illust | painterly |
|---|---|---|---|
| Form | Lines and flat areas | Areas and thin lines | Color fields and brush strokes |
| Shading steps | 2 steps (base, shadow) | Continuous gradient | Continuous, broken per stroke |
| Shadow edges | Crisp | Soft | Loose |
| Eyes | Large and decorative | Medium | Small and realistic |
| Lips | Line and pale tint | Painted shape | Painted shape |
| Background | Gradient, light shafts | Bokeh, backlight | Color field wash |
| Finish | Glow, grain | Bloom, vignette | Brush strokes, canvas texture |

- Choose the style from the user's words
    + "anime", "cel", "manga" : anime
    + "illustration", "webtoon cover", "game illustration", "semi-realistic" : illust
    + "painting", "oil painting", "painterly", "old master" : painterly

## Palette design rules

- Assign colors by role
    + Main color : the color with the largest area in the picture (hair or outfit)
    + Supporting color : the background color supporting the main color
    + Accent color : the smallest area, the highest saturation (iris, lips, props)
- A shadow color moves 3 values together from its base
    + Value down 10-40%
    + Saturation up 10-40%
    + Hue shifted to the neighboring warm or cool side
- A warm light gets cool shadows, a cool light warm shadows
- Keep value gaps between the 3 hair colors
    + `hair_shadow` at 55-65% of the `hair` value
    + `hair_light` at 2 times or more of the `hair` value, with lower saturation
- Keep the background lower in value contrast and saturation than the character
    + Dark hair against a light background, light hair against a medium or darker background brings out the silhouette
- When code needs a derived color, use `pk.adjust(color, value, sat, hue_shift)`

## Telling characters apart and skin tone

- With several characters in one picture, make them differ in 3 layers : silhouette, face, color
    + (Silhouette) a `hair_style` combination with different hair length and mass (e.g. `long_curly` and `two_block`)
    + (Face) different `eye_shape` and `brow_shape` (e.g. `droopy` and `upturned`)
    + (Color) `skin_tone` 2 or more steps apart, with different hair color values too
- When using `skin_tone`, leave `skin`, `skin_shadow`, `blush`, `lip` empty (the preset's 4 colors are matched to each other)
- For deep skin tones (`brown`, `deep`), warm `hair_light` and rim light separate the face outline from the background
- Curly hair (`long_curly`, `perm`) needs `hair_light` clearly lighter than the hair color for the curl texture to show

## Palette examples by mood

| Mood | hair / shadow / light | iris | cloth | background |
|---|---|---|---|---|
| Cool and clear | #2b3050 / #16182a / #9aa9dc | #3f7fb5 | #f4f1ec | #b9c8e6 to #e9eef7 |
| Sunset | #6b4034 / #3a1f1e / #f2b98a | #8a5a2c | #2e3440 | #f6c9a0 to #7c6fa6 |
| Classic oil painting | #7a3b24 / #3b1a14 / #e8a05c | #4d6b4a | #3f5247 | #5c6146, #7d7a52, #3f4a3c wash |
| Night, neon | #1c1b2e / #0d0c18 / #ff7ad9 | #36e0d0 | #15161f | #141432 to #3a1f5c, bokeh #ff7ad9 |
| Spring, pastel | #e8c9a0 / #b08a60 / #fff4d6 | #7fae6a | #fdf6ee | #fbe3e8 to #e4f2e0, petals #ffc2d1 |

## Male characters

- Let gender read through contrasts of form
    + Jaw : `jaw_sharpness` 0.8-0.9 makes an angular jaw corner
    + Eyes : `eye_height` 0.060-0.070, smaller for a more mature impression
    + Hair : `layered` reads most refined (default). `short`, `slicked` read neat, `medium` androgynous
- Elements of a handsome impression
    + Eyes : long narrow eyes with a thick upper lid line (in the defaults). Bigger eyes look boyish
    + Angle : `head_turn` 0.4-0.5 with opposite `gaze` for a sidelong look; avoid front ID photo framing. To stress the jawline, three-quarter (`head_turn` 2.0-2.5)
    + Light : side light (`azimuth` 120-140) brings out the shade under the cheekbones and the jawline, `rim_light` 0.5-0.7
    + Fringe : a `layered` fringe brushing one brow adds mood
    + Body : `muscle` 1.1-1.3, `shoulders` 1.03-1.05. Higher makes the arms thick and heavy looking
- Keep blush and lip saturation lower than for women (in the defaults)
- Moving the skin shadow a bit toward reddish brown gives a sun-tanned impression
- Suits use dark navy or grey `cloth2`, with a wine or dark green `accent` tie

| Mood | hair / shadow / light | cloth / cloth2 / accent | background |
|---|---|---|---|
| Suit, evening | #2b2420 / #140f0c / #b08a6a | #f4f2ee / #26304a / #7a2434 | #5b5f6e to #c9c2b8, bokeh #ffe2b0 |
| Casual, day | #26252e / #121216 / #8f9ab8 | #f2f3f5 / #3a4258 | #b9c9de to #eef1f6 |
| Beach | #2a1d18 / #140c08 / #d09060 | #2f6fa8 | sky #3f8fd8, water #1f7f9c, sand #ead3a4 |

## Colors per outfit

| Outfit | cloth / cloth_shadow / cloth2 | Tip |
|---|---|---|
| `lingerie` (bedroom at night) | #2a2230 / #140f18 | A near-black violet contrasts with the skin and the lace trim stands out bright. For white, #f4f0ea / #c8c0b8 |
| `crop_hotpants` | #f6f2ea / #c0b4a4 / #5a7aa8 | White T-shirt and mid-value denim. Denim too dark hides the pocket stitching |
| `hoodie_jeans` | #3a3f4c / #1e212a / #34405e | Grey or charcoal hoodie with navy jeans. Similar values for hoodie and pants make the silhouette look long |
| `suit` (suit) | #f4f2ee / #b8b4ae / #2a3040 | White shirt, dark navy suit, `accent` wine #5a2a3a tie |
| `swimsuit`, `bikini` | #f2f0ea / #b8c0cc | Move the shadow of a white bikini toward sky blue to match beach light |
| `open_shirt_shorts` | #e9e4d8 / #b0a898 / #3c4a5e | Ivory or pale sky blue shirt with dark navy or beige #c8b48e shorts |
| `tank_shorts` | #f2f2f0 / #b8bcc4 / #2c3140 | White tank top and charcoal shorts, `accent` stripes red #c8394f or neon yellow #d8e04a |
| `denim_jacket_chinos` | #f4f1ea / #c4bcae / #c8b48e | White T-shirt, beige chinos, jacket `outer` left empty (denim blue) |
| `leather_jacket_jeans` | #ece6dc / #b4a99a / #3c4a66 | A light T-shirt secures value contrast against the black jacket, jacket `outer` left empty (leather black) |
| `coat_turtleneck` | #ece6dc / #b4a99a / #2c3140 | Ivory turtleneck and dark slacks, coat `outer` camel by default, grey coat #6a6c72 |
| `knit_dress` | #e8dccb / #b8a690 | Oatmeal shades show the rib texture best; dark colors hide the rib lines |
| `tank_jeans` | #f2ede6 / #c0b4a8 / #44567a | White tank top and mid-value jeans |

- Shoe color of the newer outfits is `shoe`; white sneakers are #f0ece4
- For open jackets and coats, inner clothes (`cloth`) lighter than the outerwear (`outer`) make the front panel outline read
- Hot pants (`crop_hotpants`) automatically get a fly line, pocket curves and frayed hems over `cloth2`

## Two-shot colors

- Give high saturation to only 1 of the 2 characters
    + E.g. a red dress #b8344a and a dark navy suit #262c3c, with a #7a2a3a tie linking the two by color
- Different hair color values keep the edge readable where the two heads overlap
- Skin colors slightly different per person through `palette.skin`, `skin_shadow` look natural (e.g. female #f8dccb, male #eec5a6)
- Keep the background value lower or higher than both characters. Avoid colors where only one person sinks into the background

## Background design

- Build the background from 2-3 stacked operations
    + Layer 1 : the overall color with `gradient` or `wash`
    + Layer 2 : `glow` behind the head to lead the eye to the face
    + Layer 3 : one of `bokeh`, `light_shafts`, `petals` for a sense of space
- Place the `glow` `center` on the same side as the light direction
- One `wash` is enough for a painterly background; the brush strokes add variation
- Interior (`room`) walls are higher in value and lower in saturation than the outfits (#d9cbbd, #cfd4da); curtains are a dark shade of the wall color

## Lighting recipes by scene

Character and background must receive the same light to read as one scene. Below are verified combinations.

| Scene | `light` (azimuth / elevation) | Character settings | `finish` |
|---|---|---|---|
| Night street after rain | 50 / 32 (lamp side) | `rim_light` 0.85, `ambient` navy 0.25 | `bloom` 0.45, `diffusion` 0.2, navy violet shadows, orange highlights |
| Sunset backlit beach | 30 with the sun on the right, 150 on the left / 22 | `rim_light` 0.9, `face_shadow_level` -0.3 (keeps half the face from going dark) | `bloom` 0.45, violet shadows, `tilt` 3-5 |
| Morning interior by a window | 140 with the window on the left, 40 on the right / 30 | `rim_light` 0.5, light outfit | `diffusion` 0.25, sky blue shadows, `tint_strength` 0.1 |
| Lamp-lit interior at night | 140 with the lamp on the left, 40 on the right / 30 | `lamp` and `window` "night" of `room`, `ambient` violet 0.12-0.2 | `bloom` 0.3, violet shadows, amber highlights |
| City by day | 120-130 / 45 | `rim_light` 0.4 | `bloom` 0.2, `vignette` 0.12 |
| Character in a sunset lake landscape | 150 with the sun on the left, 30 on the right / 20 | Small character with `head_height` 0.075-0.085, `rim_light` 0.85 | `bloom` 0.35, violet shadows |

- Put the sun, street lamps and lamps on the same side as `light.azimuth` (light comes from the right at 0, the top at 90, the left at 180. Below 90 is screen right, above 90 screen left)
- For painterly characters set `eye_height` 0.078 and `lip_fullness` 1.3 together. Large anime-proportion eyes float awkwardly inside brush strokes

## Doomer mood

A recipe for a little warmth left inside a cold, wide city. Panel apartments, power lines, street lamps and snow are the stage, and characters stand as dark single-color masses.

- Color hierarchy : warm light sources > character silhouette > window grid > sky
    + Use warm colors only for window light (#f2c66b), sodium street lamps (#ffb35a) and the cigarette ember
    + The rest is blue-grey (#7a7c88, #9aa0aa) and ink black (#121826, #24242a)
- Outfits : `cloth` #24242a-#3a3a44, `outer` #26262c, `hat` #1e1e24, hair #16161c-#1c1c24
    + Skin desaturated to #efd9cc-#f2ddd2, shadow #c4a09a
    + `hair_light` orange grey (#c8a078) on the lamp side, blue grey (#8a93b8) on the sky side
- `ambient` : navy (#26284a) 0.2-0.3, `from` 0.45-0.6 to blend the lower body into the night
- `rim_light` 0.7-1.0 : separates dark clothes from a dark background
- Values of `finish.preset` `"doomer"` : `saturation` 0.70, `contrast` 1.08, shadows #1a2436, highlights #ffb878, `tint_strength` 0.22, `vignette` 0.32, `grain` 0.028, `bloom` 0.30, `diffusion` 0.12
    + The spec's `finish` keys override the preset (e.g. painterly only adds `radii`)

| Scene | Style | `light` | Composition points |
|---|---|---|---|
| Male knee-up (`doomer_male`) | anime | 70 / 55 (lamp overhead) | Beanie, hoodie, cigarette in the mouth, night blocks and wooden poles behind, snow front and back |
| Female walking in profile (`doomer_female`) | illust | 155 / 18 (dusk from the left) | Long coat, birch path, dusk blocks |
| Two-shot back view (`doomer_duo`) | anime | 90 / 12 (backlit by windows ahead) | Two people side by side and a large lit block, `rim_light` 1.0 |
| Establishing shot (`doomer_establishing`) | illust | 150 / 20 | Several blocks in side perspective, wires converging on the vanishing point, 2 small passers-by (`extras`) |
| City painting (`doomer_city`) | painterly | 60 / 40 | Blocks around a courtyard, 2 street lamps, leafless trees |
| Landscape painting (`doomer_landscape`) | painterly | 120 / 25 | Row of pylons, distant blocks, dark clouds and a warm horizon |
| Still life (`doomer_still_life_example.py`) | illust | Behind and above the window | Ashtray and smoke, tea in a glass, cassette radio, lit blocks outside the window |

- Composition : a low horizon for large sky and building areas, characters on the thirds
- In establishing shots keep the characters small with `head_height` 0.02-0.03 so the place is the subject
- A bright upper sky makes the picture look washed out; keep the top darkest and a faint warmth near the horizon

## Fine-tuning per style

- anime
    + If lines look thick, `line_width` 0.0035
    + To widen the face shadow, `face_shadow_level` 0.0-0.1
    + To remove the hair band highlight, `hair_highlight` "none"
- illust
    + For a backlit feel, `rim_light` 1.0 and a stronger background `glow`
    + To remove lines completely, `line_width` 0
    + Eyes around `eye_height` 0.085 suit semi-realism
- painterly
    + If the brush looks rough, shrink `finish.radii` to [20, 10, 5, 3, 2]
    + For bold strokes, [36, 18, 9, 4]
    + A small canvas loses face detail, so a height of 1500 or more is recommended
