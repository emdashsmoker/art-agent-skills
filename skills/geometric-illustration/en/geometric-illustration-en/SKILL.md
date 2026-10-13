---
name: geometric-illustration-en
description: "Draws illustrations with numpy and OpenCV alone: sphere-and-cone mannequins, a one-point pinhole camera and flat-faced props, staged like hand drawing (construction, line art, flats, shading, finish) with no diffusion model. The flavor is quiet geometry: crisp ink silhouettes, calm navy and blue-gray grounds, a few amber window lights, one key light, figures holding a pose. Renders men and women (bust to wide shot, groups of 2-3), streets drawn into a vanishing point, layered landscapes and tabletop still lifes in anime cel, soft illustration, oil or watercolor with color-grade looks, reproducibly from one JSON spec. Spec fields: references/spec-reference.md. Modules and extension: references/pipeline.md. Body proportions and form checks: references/anatomy.md. Styles and color grading: references/styles.md. Use for 'draw with code', 'procedural anime character', 'night city in code', 'still life in code', and any portrait or background request with no image generation tool."
license: GPL-3.0-or-later. Rendered images are not covered by the GPL (additional permission in THIRD_PARTY_NOTICES.md). Complete terms in LICENSE
---

# Code Illustration

> Translation notice: this English edition was translated from the Korean original skill (`geometric-illustration`). Its performance, behavior and logic may differ from what the original intends. Where the two editions disagree, follow the Korean edition.

A skill that draws pictures by porting the real drawing process to code. It uses no diffusion model, no image generation API and no 3D software.

## How It Works

Every picture passes through the 7 steps below. Each step maps 1:1 to the order in which a person draws.

| Drawing step | Code step | Modules |
|---|---|---|
| Planning | Write the JSON spec | `config.py` |
| Construction lines | Head frame, joint skeleton, perspective camera | `frames.py`, `rig_anatomy.py`, `scene_city.py` |
| Form | Mannequin stacked from spheres and cones (Loomis, Bridgman method), 3D clothes fitted to the body, flat and cylindrical props | `mannequin.py`, `rig_hand.py`, `rig_anatomy.py`, `garment3d.py`, `garment_kit.py`, `outfits.py`, `scene_props.py` |
| Line art | Variable-width strokes, silhouette lines, occlusion contours | `geom.py`, `mannequin.py`, `scene.py` |
| Flat colors | Solid colors and gradients per material group | `scene.py` |
| Shading | Normals from depth fields, self shadow, cast shadow, designed shadows | `mannequin.py`, `scene.py` |
| Finishing | Layer compositing per style, whole-image color grade (look) | `styles.py`, `painterly.py`, `looks.py` |

The core design is "layer separation". Rig and scene modules output only line art, flat color, normal, shadow and highlight layers. Style renderers composite the same layers in different ways. The style can therefore change while the subject stays the same.

Soft forms such as the body, hands and fruit are mannequins built from spheres and cones (sphere-swept solids). A sphere-swept solid keeps its sphere-swept shape after orthographic projection, so its silhouette, depth and contour lines come from closed-form expressions. The torso is a single chain of elliptical sections with different width and thickness. The foot is a sweep of closely spaced ellipsoids, so its form holds up even seen from the front. Fingers and toes are tubes that taper toward the tip. Clothes are put on the same body in 3D. Close-fitting clothes are the matching body parts inflated by the cloth thickness, trousers and sleeves are tubes wrapped around the limbs, and a skirt is a cloth surface hanging from the hips, so they follow the body when the pose changes. Hard objects such as laptops, cups and plates are flat-faced polyhedra and cylinder props, and each face takes one tone. There are no meshes and no 3D packages.

## Subjects

| `subject` | Content | Recommended canvas |
|---|---|---|
| `portrait` | A clothed figure. `character.sex` picks female or male, `character.build` the body type. `framing` picks bust, upper body, full body or establishing shot (`wide`). A `characters` list makes a 2-3 person group. With `background.type: scene` the figure stands over a city or landscape | 1024 x 1280, full body 1024 x 1600, group 1280 x 1600 |
| `nude` | Adult figure study. 4 poses each for women and men | Standing 1024 x 1600, reclining 1600 x 1024 |
| `still_life` | Still life. `scene.set`: `classic` (bottle, jug, fruit, drape), `desk` (laptop, mug, lamp, potted plant), `cafe` (latte, cake, iced drink), `gaming` (monitor, RGB keyboard, headset), `kitchen` (tea glass in a holder, radio cassette player, snowy housing blocks outside the window) | 1400 x 1050 |
| `cityscape` | One-point perspective street. `scene.site`: `street` (shopping avenue, default), `panel` (prefabricated panel housing estate with bare street trees). `scene.time` picks the time of day | 1600 x 1000 |
| `landscape` | `scene.site`: `lake` (mountains and lake, default), `outskirts` (field at the edge of town, a line of power pylons, birches, housing blocks and chimneys on the horizon). `scene.time` picks the time of day | 1600 x 1000 |

Time of day (`scene.time`): `dusk` (default), `day` clear daylight, `golden` golden hour, `blue_night` blue-hour night view, `rain_night` rainy night, `snow_night` snowy night (sodium street lamps, snow-covered road with wheel ruts). Each time changes the sky, the light source, the object colors and the effects (sun path, moon and stars, windows and street lamps, rain, snow, reflections on a wet road) together.

Color grade (`look`): `none` (default), `doomer` (lower saturation and cooler shadows, saturation kept only in orange lights, faded blacks, film grain, vignette). It is applied once to the whole image after the style renderer finishes.

## Figure Study

The `nude` subject draws 4 academic nude poses of classical painting, for women and for men.

- Body proportions are fixed to adult values: US Army anthropometric data (ANSUR II female, male) adjusted to an anime illustration body (`references/anatomy.md`).
- The current body model has no nipple or genital geometry. No interior lines are drawn around the pelvis. Women and men are the same in this.
- The 4 poses are classical compositions in which posture, hands, hair or a drape cover the chest and pelvis.

### (Content limit) Nudity and sexual acts involving minors

- The skill does not draw nudity or sexual acts involving minors. This is the only content limit of this skill.
- The test is how the body is depicted.
    + A request to draw a body before puberty (a child's head-to-body ratio, undeveloped chest and pelvis, a child's build)
    + A figure stated to be under age or stated to be a child
- Art style, large eyes or a youthful face alone are not the test.
- Code implementation: body proportions are fixed to adult values. Face parameters of the `nude` subject are clamped to the `rig_nude.ADULT_FACE` ranges. The clamp applies only to the rendered result.

## Dependencies

- Python 3.9 or later
- 2 packages: `numpy`, `opencv-python-headless`
    + Tested versions: Python 3.11, numpy 2.4, OpenCV 4.13 / Python 3.13, numpy 2.5, OpenCV 5.0
    + Install example: `pip install numpy opencv-python-headless`
    + In a conda environment: `conda install numpy`, then `pip install opencv-python-headless`

Install the dependencies before every other step. The renderer uses no GPU, no network and no fonts.

## Quick Start

```bash
cd scripts
python render.py --out portrait.png                                         # default figure, anime cel, bust
python render.py --out portrait.png --style oil                             # change only the style
python render.py --spec ../assets/examples/landscape_dusk_oil.json --out land.png
python render.py --spec ../assets/examples/city_rain_night_watercolor.json --out rain.png   # time of day example
python render.py --spec ../assets/examples/still_desk_anime.json --out desk.png            # modern still life example
python render.py --spec ../assets/examples/male_suit_illustration.json --out male.png      # male figure example
python render.py --spec ../assets/examples/turn_back_turtleneck_watercolor.json --out back.png   # back view
python render.py --spec ../assets/examples/seated_turtleneck_anime.json --out seated.png         # seated on a chair
python render.py --spec ../assets/examples/group_hold_hands_anime.json --out pair.png            # two-person group
python render.py --spec ../assets/examples/scene_city_track_illustration.json --out city.png     # figure in a night city
python render.py --spec ../assets/examples/doomer_establishing_anime.json --out doomer.png      # doomer establishing shot
python render.py --spec my.json --out out.png --stages stages/              # stage images + process sheet
```

- `--style`: `anime` | `illustration` | `oil` | `watercolor`
- `--stages`: saves `1_construction`, `2_lineart`, `3_flats`, `4_shading`, `5_final`, `process_sheet.png`
- Misspelled spec keys are reported as warnings on stderr. Invalid enum values exit with an error that lists the valid values.
- Render time (at 1024 x 1280): anime, illustration and watercolor 2-5 s, oil 6-15 s. Scenes and modern still lifes 3-8 s
- One render peaks at about 0.4-0.9 GB of memory. When rendering several pictures in parallel, keep the number of concurrent runs at or below the available memory in GB

## Workflow

### Step 1 (Planning) Translate the request into a spec

- Extract subject, style, framing or pose, impression and colors from the request
- Write only the fields that differ from the defaults into the JSON
    + All fields and ranges are in `references/spec-reference.md`
- Use the table below as the starting point for impression keywords of a figure

| Impression | Fields to adjust |
|---|---|
| Chic, cool | `face.jaw_sharpness` 0.8-0.9, `eyes.tilt` 0.08-0.14, `mouth.smile` 0.1-0.25, `blush` 0.2 |
| Soft, cute | `eyes.size` 1.2-1.3, `eyes.tilt` 0.0, `face.jaw_sharpness` 0.5, `blush` 0.45 |
| Elegant, mature | `eyes.openness` 0.85, `eyes.lash_weight` 1.2, `brows.angle` 0.2, `mouth.lip_strength` 0.8 |
| Bright, friendly | `mouth.smile` 0.5-0.7, `brows.angle` 0.1, `eyes.gaze` straight ahead [0, 0] |

- Sex: setting `character.sex` to `male` applies the male body, face, short hair and male outfit defaults together. Impression tuning uses the fields of the table above unchanged
- Body type (`character.build`): female `standard`, `slender`, `glamour`, `athletic`, male `standard`, `slim`, `athletic` (muscular). All are variations within real adult body ranges, and clothes follow the body type
- Face preset (`character.face_preset`): `soft`, `sharp`, `mature`, `gentle` (drooping eyes), `cool` (narrow eyes), `bold` (strong features). They change the face only within the adult face ranges
- Expression (`character.expression`): `smile`, `laugh` (closed eyes, open mouth), `neutral`, `surprised`, `serious`, `sad`
- Hair (`character.hair.style`): `long`, `updo`, `short`, `bob`, `ponytail`, `medium`, `side_part`, `slicked` (combed back), `two_block`, `hime` (hime cut), `center_part`, `shoulder` (shoulder length), `crop` (short blunt bangs)
- Framing (`framing`): `bust`, `upper_body`, `full_body`, `wide` (establishing shot: the full figure is about 1/3 of the canvas height, the feet 10% above the bottom edge). For an establishing shot, place the figure on a third with `character.head.x`
- Figure pose (`character.pose.preset`): `relaxed`, `hand_on_hip`, `hair_touch` (brushing the hair back), `chin_rest`, `arms_crossed`, `hands_in_pockets`, `walking`, `look_back`, `lean_wall` (leaning on a pillar), `seated` (on a chair)
    + `pose.turn`: body turn. `front`, `three_quarter`, `side`, `three_quarter_back`, `back`; a leading `-` turns to the other side; a number is radians
    + `pose.look`: `auto` (the face turns with the body and becomes the back of the head on large turns), `face` (face over the shoulder), `away` (back of the head)
    + `pose.custom`: set wrist and ankle targets of the limbs and rib cage and pelvis rotation directly
- Outfit (`character.outfit.type`): `turtleneck_sleeveless` (turtleneck and skirt, female default), `bikini`, `lingerie`, `crop_hotpants` (crop top and hot pants), `tee_jeans` (T-shirt and jeans, male default), `suit`, `hoodie_joggers` (hoodie and joggers), `swim_trunks` (male only), `shirt_slacks` (shirt and slacks), `knit_coat` (knit and belted long coat), `polo_shorts` (polo and chino shorts), `tank_shorts` (singlet and running shorts), `denim_jacket` (denim jacket and T-shirt), `track_suit`. Men support the 10 outfits other than bikini, lingerie, turtleneck with skirt and crop top. Every outfit has default colors and shoes; `palette` changes only the colors
    + `outfit.hat`: `none` (default), `beanie` (knit beanie with a folded cuff, color `palette.hat`). The hat is drawn over the hair, so bangs and side locks show only below the cuff
    + `outfit.shoes`: replaces the outfit's default shoes with `pumps`, `sneakers`, `oxfords` or `none` (flat shoes for a woman in a coat on a snowy road, for example)
- Group: list 2-3 figures in `characters` and pick `layout.type` (`side_by_side`, `facing`, `front_back`) and `layout.interaction` (`none`, `hold_hands`). Each figure has its own sex, build, outfit, pose, expression and `palette`
- Figure over a scene: with `background.type` set to `scene` and `background.scene` set to `cityscape` or `landscape`, the figure stands over the scene of `scene.time` and takes the scene's light direction, color tint and rim color
- Figure study poses: `back_three_quarter`, `venus`, `reclining`, `seated`
- Scenes: pick `scene.time`, `scene.site` (landscape, city) and `scene.set` (still life) first, then override only colors with `scene.palette`
- Doomer mood (the lonely mood of an Eastern European winter night): `scene.time` `snow_night`, `scene.site` `panel` or `outskirts`, for a still life `scene.set` `kitchen`, `look` `doomer`, black and gray clothes with `outfit.hat` `beanie`, expression `neutral` or `sad`. Use only the mood and reproduce no specific album cover or logo

### Step 2 (Design direction) Write a short direction note

- Before rendering, fix a direction of about 5 lines: one key impression, a color scheme (base color + at most 2 accents), gaze direction, light direction, background contrast
    + The light comes first because the shadows, reflected light and background glow positions all derive from it
- Scene subjects have their light designed into the time of day and the set. Pick the character of the light with `scene.time` and `scene.set`, and change only the colors with `scene.palette`.
- When hair and clothes share the same dark color, the silhouettes merge. Separate the value of one of them.

### Step 3 (Rendering) Output with the process sheet

- Render the first pass with `--stages` and check each stage
    + Figure poses draw the joint skeleton in `1_construction`
- To compare styles, render the same spec 4 times changing only `--style`

### Step 4 (Review) Open the rendered images and check them

- Check the full image and zoomed crops of the face, hands and feet separately. Line defects do not show in small thumbnails.
- To look at hands and feet alone, `python scripts/check_proportions.py --hands hands.png` renders gestures and foot poses from several directions.
- When a defect is found, start from the adjustment point in the table below.

| Symptom | Cause | Adjustment |
|---|---|---|
| Half the face in shadow | Light and face turn conflict | Set the sign of `light.direction` x opposite to `head.yaw` |
| Bangs cover the eyes | Bangs too long | Lower `hair.bang_length`, set `hair.bangs` to `swept` |
| Far eye sticks to the outline | Turn too large | Keep the absolute value of `head.yaw` at or below 0.35 |
| Hand floats off the body | Wrist target error | Move `Limb.target` of the pose function while watching the `--stages` skeleton |
| Fingers look clumped | Gesture bends too much | Reduce the finger bend angles in `rig_hand.GESTURES` |
| Fist looks like a mitten | First knuckle bends too much | Reduce the MCP bend and increase the PIP bend of the gesture |
| Thumb sticks out like a stick | Thumb tip target far from the palm | Pull the gesture's `thumb` target toward the palm (`n` from -0.3 to 0) |
| Round bump beside the wrist | Thumb root outside the wrist | Move v of `rig_hand.THUMB_BASE` inside the wrist half-width |
| Sole looks tilted | y component of `foot_dir` | Standing feet y 0, tiptoe and high heels `hand='point'` |
| Blotchy shadow on the chest of a top | Knit normals not smoothed enough | Raise `garment3d.TOP_NORMAL_BLUR` |
| Knit ribs wobble | Ripples in the height field that spaces the ribs | Raise `garment3d.RIB_HEIGHT_BLUR`, `RIB_SMOOTH` |
| Skirt looks like a cylinder or legs show through | Hem width or ease too small | Adjust spec `skirt_flare`, raise `garment3d.SKIRT_EASE` |
| Skirt folds too weak or too strong | Fold depth and count | Adjust `garment3d.FOLD_DEPTH`, `FOLD_COUNT` |
| Sleeve or trouser hem cuts into the body | Limb hem cut reaches too far | Lower `garment_kit.LIMB_CUT_REACH`, `LIMB_SIDE_REACH` |
| Cloth stays like a pillar above the neckline | Inflated up to the neck cone | In the recipe use `sleeved_top(..., neck=False)` (default), check the neckline height `NECK_BASE_Y` |
| A scrap of cloth hangs below short bottoms | The lower end of the torso drops between the legs | Check `outfits.SHORTS_MAX` (short bottoms are cut below the line joining both hems) |
| Male shoulder rises like a bump | Trapezius end lower than the deltoid | `GIRDLE_TOP`, `ARM_ATTACH_K` in `rig_anatomy.BUILDS['male']` |
| Bump beside the male pelvis | Thigh root ball outside the pelvis line | Reduce `THIGH_ROOT_R`, `HIP_LOCAL` in `BUILDS['male']` |
| Bump on the pelvis line of a new body type | Thigh thickness factor larger than the pelvis width factor | Set `thigh_root` in `rig_anatomy.VARIANTS` near 1.0, raise the pelvis row `width`, then run `check_proportions.py` |
| Strap breaks off on the skin in front of the neck or shoulder | Strap path ends inside the drawn outline | Draw straps with `garment_kit.strap` (3D path, hidden by depth and facing). Neck loops fit the drawn neck outline through `outfits.neck_fit_radius` |
| Front lines (pocket, lapel) show on the back of a turned body | Lines drawn as 2D points | In the recipe use `ctx.paths`, `ctx.points`, `ctx.patch` (back lines with `back=True`) |
| Cups or briefs print on the back of a turned body | Only a front outline exists | Give `fitted_top`, `briefs` a back outline (`back_rest`, `back_outline`) |
| On a turned body one trouser hem cut slices the other leg | 2D cut polygons overlap | Check `outfits.LIMB_FOOT_REACH`, `LIMB_FOOT_MARGIN` (limit the cut to that leg's area) |
| Skin scraps around a hand in a pocket | Hand or forearm comes out in front of the clothes | Move z of `rig_figure.POCKET_WRIST`, `KANGAROO_WRIST` inside the cloth surface |
| A group figure leaves the canvas | Canvas too narrow | Widen the canvas or reduce `layout.gap`. The layout shrinks to fit the width |
| Top shoulder puffs like a puff sleeve | Sleeve ease too small, shoulder bridge too short | Raise the recipe's sleeve ease, check `outfits.BRIDGE_TOP` |
| Shirt pokes out beside the jacket neckline | Each layer has a different neckline radius | Raise `outfits.NECK_CUT_EASE` |
| Collar floats in front of the neck | Inner face of the collar ahead of the neck | Bust: `z_back` of `rig_body.build_collar`; upper and full body: move `rig_figure.Z['collar_back']` behind the neck |
| Collar wraps the neck too little | Collar height and thickness | Adjust `garment3d.COLLAR_TOP_Y` (raise toward the chin), `COLLAR_EASE` |
| Foot and shoe do not match | Shoe sections differ from foot sections | Make `rig_figure.SHOE_TOE_BOX`, `SHOE_WALL` slightly larger than `rig_anatomy.FOOT_SECTIONS` |
| Body shadow looks messy | Self shadow too long, small light gaps | Lower `mannequin.SHADOW_REACH`, raise `styles.SHADOW_SIMPLIFY` |
| Body looks like a log | Torso section proportions | Adjust waist width and z center in `rig_anatomy.TORSO_LOFT`, then check the turn sheet with `check_proportions.py --sheet` |
| Limb outline is lumpy | Sudden changes in the radius profile | Smooth the `*_PROFILE` values in `rig_anatomy`, check the inflection count of `check_proportions.py` |
| Limb shadow edge is jagged | Too few sweep segments | Raise `rig_anatomy.LIMB_SEGMENTS` |
| Anatomy marks missing or in the wrong place | Mark points off the surface | Move the mark coordinates in `rig_anatomy` toward the surface, check `rig_nude.MARK_SURFACE_TOL` |
| Covering hand has no outline | Quiet-zone handling | Check that the hand piece names start with `hand_` (`mannequin.QUIET_KEEP`) |
| Oil brushwork smears roughly | Brushes too large | Reduce `OIL_FIG_BRUSHES` in `painterly.py` |
| Watercolor blotches too strong | Too much pigment modulation | Lower `WC_TURBULENCE`, `WC_EDGE_DARKEN` in `painterly.py` |
| Hair rises beside the hat | Hair volume larger than the hat dome | Lower `rig_hat.HAIR_PRESS`, raise `HAT_THICK` |
| Hat cuff covers the brows | Cuff sits too low | Move `rig_hat.CUFF_FRONT_V` up (toward negative) |
| Beanie merges with the hair | Hat and hair share the same value | Make `palette.hat` two steps lighter than the hair |
| Skin looks ashen with the doomer look | Base saturation too low | Raise `saturation` in `looks.DOOMER` |

### Step 5 (Delivery) Deliver the result

- Deliver the final PNG with the spec JSON used, so the result can be reproduced
- The same spec with the same `canvas.seed` and `hair.seed` always produces the same image.

## Extension

- Steps to add poses, anatomy marks, hand gestures, outfits, scenes, times of day, still life sets and styles are in `references/pipeline.md`
- Sources of the body proportions, conversion formulas, form design (hands and feet included) and the review procedure are in `references/anatomy.md`. After changing the body form, `python scripts/check_proportions.py` (proportion error, outline bumps, hand and foot ratios) must pass
- Internal parameters of the style renderers and how to tune them are in `references/styles.md`
- The principle when extending is to keep the split in which "rigs and scenes own only shapes, styles own only compositing"

## Limits

- Faces support only front to 3/4 view (`face_yaw` -0.35 to 0.35); there is no full profile face. Even with the body turned to the side, the face is drawn as a 3/4 view toward the viewer. A back view is either the back of the head or a face over the shoulder
- Outfits are fixed designs; only length and color change. Cloth flutter and wind exist only in skirt and coat hems
- The camera is a single eye-level view close to orthographic. There is no high or low angle
- Poses are 10 predefined presets plus direct joint targets. Holding objects in the fingers (props) is not supported
- Groups are 2-3 clothed figures. The only interaction is holding hands; there is no arm over the shoulder or hug. Figure studies do not support groups
- Scene compositing lays the scene behind the figure. The figure's feet are not placed by computing the scene's perspective floor
- Male proportion targets are estimates from public male summary statistics. Hand and foot size and buttock depth are design values
- Each site (`scene.site`) has one scene composition, and element placement varies only with the seed. The 6 times of day, the 2 city and 2 landscape sites and the 5 still life sets are fixed presets.
- Watercolor leaves paper margins at the edges of the background. In night scenes and with the `doomer` look a white margin appears around the dark sky and looks out of place, so use another style there.
- Oil smears small snowflakes into brush marks. Close snowflakes over a figure can look like round blotches.
- The only hat is the beanie. Brimmed hats, a raised hood and scarves are not available.
- Fingers are expressed per joint. Fingernails are drawn only in close framing (6 px or more on screen); there are no palm lines, knuckle creases or toenails.
- Toes are modeled as the big toe plus the other 4. No gesture moves the toes separately. The heeled shoe is a single pointed pump design.
- In the back-view poses of the figure study, the face is still drawn with the front face rig, so the head looks turned.
- Proportion targets of the body type variants are a construction check: base targets multiplied by the body type factors. They do not come from new survey data.
- Diffusion-level realism is out of scope. The goal is to keep the human drawing process as reproducible code.
