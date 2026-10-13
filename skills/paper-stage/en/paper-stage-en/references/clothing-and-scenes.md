# Outfits, poses, two-shots, scenes

Four layers laid on top of the full-body rig (`references/figure-body.md`): layered clothes and sleeves (`figure/clothing.py`), non-standing poses such as sitting and lying (`figure/body.py`), furniture (`figure/props.py`), several figures and framing (`figure/stage.py`), and scene backgrounds (`codepainter/sets.py`).

## Outfits

### List

Use them as `wardrobe.WARDROBE[name]` or `clothing.<CONSTANT>`.

| Name | Contents | Colours used |
|---|---|---|
| `lingerie` | half-cup bra (lace over the cups, centre gore, underband, shoulder straps), lace briefs with a bow | `cloth` |
| `lingerie_stockings` | the same set plus sheer thigh stockings with lace bands | `cloth` |
| `crop_top_shorts` | short-sleeved crop tee, low-rise denim hot pants (frayed hems), trainers | `cloth`, `cloth_second` |
| `hoodie` | oversized hoodie (hood folded back, front pocket, drawstrings, ribbed cuffs and hem), jeans, trainers | `cloth`, `cloth_second` |
| `hoodie_shorts` | hoodie with hot pants, trainers | `cloth`, `cloth_second` |
| `suit` | suit trousers (creases), shirt and collar, tie, single-breasted jacket (notch lapels, two buttons, pocket flaps), shirt cuffs, shoes | `cloth` |

- All can be worn by men and women; body differences come through the body mask on their own
- Checked at 0, 45 and 90 degrees and when sitting and lying

### Combining

```python
from codepainter.figure import clothing, wardrobe

outfit = clothing.combine(wardrobe.jeans, clothing.sneakers, clothing.HOODIE)      # list them in drawing order
dress_shirt = clothing.combine(clothing.suit_trousers, clothing.dress_shoes, clothing.shirt, clothing.tie)
draw_figure(painting, spec, body, pose, style, dress=outfit)
```

- `Outfit(body, sleeve, behind)` has three layers
    + `body` is clothing over the trunk and legs, drawn before the front arms
    + `sleeve` is drawn over each arm right after that arm, with the form `f(painting, skeleton, side, masks, spec, style, light)`
    + `behind` is drawn right after the back hair, before the trunk (the folded hood)
- Plain function outfits work as they are; `combine` wraps them in an Outfit
- The part functions are `crop_tee`, `hot_pants`, `hoodie_body`, `hood`, `shirt`, `tie`, `jacket`, `suit_trousers`, `bra`, `panties`, `stockings`, `sneakers`, `dress_shoes`

### Sleeves

```python
def blouse_sleeve(painting, skeleton, side, masks, spec, style, light):
    return clothing.draw_sleeve(painting, skeleton, side, masks, spec.cloth, style, light,
                                reach=1.6, ease=clothing.SLEEVE_EASE["loose"], cuff=(0.12, "#ffffff"))
```

| Argument | Meaning |
|---|---|
| `reach` | where the sleeve ends: 0 shoulder, 1 elbow, 2 wrist (short sleeve 0.42, long sleeve 1.9-1.97) |
| `ease` | room around the arm (head heights): `fitted` 0.015, `tailored` 0.035, `loose` 0.045 |
| `cuff` | (length, colour) of a ribbed band gathering the sleeve end at the wrist |
| `under` | (length, colour) of a shirt cuff showing past the sleeve |

- At the shoulder the sleeve fits with no room, and the room grows to mid upper arm (`SHOULDER_SNUG`)
    + Room from the shoulder makes it puff like a puff sleeve
- Where it meets the body piece, the line stays as a faint seam (`SEAM_OPACITY`)

### Designing body pieces

- Extended arguments of `wardrobe.fitted(..., ease, drape, cut)`
    + `drape` is how far cloth falls from the wide part below the armpits; it draws back toward the body as it falls (`DRAPE_PULL`)
    + Hoodie 0.95, jacket 0.6, shirt 0.3, crop tee 0.35
    + `ease` is 0 at the shoulders and largest from the armpits, so it never rises like shoulder pads
    + `cut` is an area taken out of the garment, such as the open front of a jacket; shading is worked out on the whole form before the opening
- Polygons on a turned body (lapels, ties, front openings) are placed with `clothing._on_surface`, which fills in points along each edge
    + Wrapping only the corners lets straight edges cut across the body's turn, so the near lapel goes flat
- Lace is `clothing.lace_edge(painting, skeleton, edge_line, color, style, clip, toward, depth)`
    + In order : a sheer band, scallops along the outer edge, mesh dots, a stitch line
    + `toward` is the direction the band reaches; on a lying body turn it by the body's lean with `clothing._turned`
- Suit trouser legs keep the knee width down to the ankle with `clothing.trouser_legs`
    + Close-fitting trousers follow the calf and narrow at the ankle
- For trousers and shorts on a turned body, `wardrobe.leg_split` draws the near leg's contour inside the cloth
    + Without this line, shorts look like a skirt at 45 degrees
- On suit trousers seated front-on, the two calves touch and merge into one mass, so the inner line of the left leg is drawn inside the cloth (`clothing._divide_trouser_legs`)
- Bra shoulder straps end where the front arm first hides them
    + This prevents a scrap of strap end floating above the arm in profile
- The folded hood rests on the shoulders and rises only to half the neck height (`HOOD_RINGS`)
    + In back views it is drawn over the back
- Tops that reach the hips (hoodie, jacket) cover only part of the front of the thighs when seated (`clothing.SEATED_TOP_LAP`)
- In back views, things attached to the front of the body (pockets, drawstrings, ties, lapels, buttons) are not drawn
    + The neckline of tops rises to the height of the back of the neck (`BACK_NECKLINE`)

## Sitting, kneeling, lying

### Presets

| Name | Pose |
|---|---|
| `sit_side` | seated on a chair in profile, thighs level, shins vertical, hands on the knees |
| `sit` | the same pose in three-quarter (`yaw=35`) |
| `sit_front` | seated front-on, the camera looking down 20 degrees (`pitch=20`), hands on the knees |
| `kneel_side`, `kneel` | kneeling with the upper body upright, shins and insteps on the floor; the hands of `kneel` hang beside the outer thighs |
| `seiza` | profile, sitting back on the heels |
| `lie_back` | lying on the back in profile (`yaw=90, lean=-90`), one knee raised, both feet on the bed |
| `lie_side` | lying on the side facing the viewer (`lean=90`), upper leg resting on the lower |

### How it works

- When `swing["thigh_x"]` passes 35-75 degrees the pose counts as seated (`skeleton.seated`)
    + A seated pose cuts the bottom of the trunk flat at the seat (`SEAT_DROP` 0.36)
    + If the bottom of the trunk sags between the legs, the buttocks seem to droop below the chair
- `Pose.ground` is the downward screen distance (head heights) to the surface the body rests on
    + Trunk and buttocks flatten along that line on a chair, bed or floor
    + For a body lying on its side, a value close to the pelvis half width (0.66) has the pelvis and shoulder touching while the waist lifts
- `Pose.pitch` is the angle the camera looks down at, in degrees
    + Thighs reaching toward the viewer show on the picture, if short
    + A front sitting pose draws the shins first and the thighs over them, so the knee ends cover the tops of the shins
- The foot direction can be set directly with `swing["foot_x"]`
    + 0 down, 90 forward, -90 back; kneeling is around -84 (instep on the floor)
- The breasts of a lying body sag toward the bottom of the screen (gravity) (`anatomy.LYING_SAG`)
    + Lying on the back, the breast volume sinks toward the ribcage (`LYING_FLATTEN`)
    + Below 30 degrees of `lean` the existing calculation is kept

### Clothes on seated figures

- Leg openings set at hip height would cover the whole thigh reaching forward
    + When seated, `wardrobe.bottom_region` cuts across the thigh at a set length along it
    + Hot pants 0.62, briefs 0.16, bikini and swimsuit 0.12, male trunks 0.55 (head heights from the hip joint along the thigh)
- Skirts use `wardrobe.seated_skirt`
    + It covers the hips and thighs, fills the gap between the thighs, then drapes down in front of the knees
- A new bottom function that builds its leg openings with `bottom_region(painting, skeleton, masks, top_line, hem_line, length)` supports seated poses on its own

## Furniture

```python
from codepainter.figure import props
from codepainter.figure.body import Skeleton

skeleton = Skeleton(pose, body, painting.shape)
chair = props.chair(skeleton, color="#6b4a33", cushion="#a8786a")
back = props.draw(painting, skeleton, chair, style)                     # behind the figure
masks = draw_figure(painting, spec, body, pose, style, dress=dress)
props.contact_shadows(painting, skeleton, masks["figure"], back, style)  # shadows where they touch
props.draw(painting, skeleton, chair, style, layer="front")             # legs that come in front of the figure
props.floor_shadow(painting, skeleton, [masks["limbs"]["leg_l"], masks["limbs"]["leg_r"], back], style)
```

- Furniture is built from boxes (`props.Box`) in the same 3D space as the figure
    + It follows the figure's body turn and camera angle and ignores the body's lean; a bed stays level on the picture
    + Only the visible faces are painted, shaded by their direction; cushions and mattresses with `soft=True` get inflated shading
- `props.chair(skeleton)` is built to fit the seat height and foot position of the seated body
- `props.bed(skeleton)` is built from the length between the head and feet of the lying body, with the pillow at the head
    + The height down to the floor under the bed is `props.BED_HEIGHT`
- `props.table(skeleton, reach=None, half=None)` is a small cafe table in front of a seated body (square top, one stem, foot plate)
    + The top sits `props.TABLE["height"]` above the seat, at navel height
    + `reach` is the distance from the pelvis centre to the middle of the table in the direction the figure faces; by default just past the knees
    + For two people facing each other, give the table to one of them only and set `reach` to half the distance between them

```python
sa, sb = Skeleton(a.pose, a.body, shape), Skeleton(b.pose, b.body, shape)     # a faces right, b faces left
a.props = [props.chair(sa), props.table(sa, reach=(sb.origin[0] - sa.origin[0]) / 2 / sa.unit, half=1.0)]
b.props = [props.chair(sb)]
```

## Framing and two-shots

### Framing presets

```python
from codepainter.figure.stage import frame

(pose,) = frame([(pose, body)], painting.shape, "waist")                       # full | knee | waist | bust
her_pose, his_pose = frame([(her_pose, BodySpec()), (his_pose, MALE_BODY)], painting.shape, "knee", centers=(0.38, 0.64))
```

- Works out `root` and `unit` so the chosen cut fits the canvas
    + `full` cuts below the feet, `knee` below the knees, `waist` above the thighs, `bust` below the chest
    + Several figures stand on one floor and share one size unit, so height differences show as they are
- `full` keeps hands and feet inside each figure's slot; closer cuts fit only the shoulder width and let figures overlap (`overlap`)
- Given `floor` (a pixel row), the figures stand on the background's floor line
    + A figure lying on a lawn or floor needs `floor` set on the near ground (0.85-0.9 of the canvas height), or it floats above the horizon

### Reaching

```python
from codepainter.figure.stage import reach

his_pose = reach(his_pose, MALE_BODY, "l", target_pixel, painting.shape, depth=0.9)
```

- Works out the upper arm and forearm angles and their forward swing with two-joint inverse kinematics
    + `target` is a canvas pixel; `depth` is how far that point comes toward the viewer, measured for that figure
    + By default the palm centre goes to the target (`palm=True`); out of reach, the arm stretches all the way
    + The elbow direction is `pole` (by default outward, down and back)
- `rest_hands(pose, body, shape, on="knees")` rests both hands on the knees (`"thighs"` for mid thigh)
    + The seated hands reach the knees even on builds with a different shoulder width
    + For near-front seating (22 degrees or less) the hands move outside the knees by `stage.REST_OUTWARD`, so they do not overlap over the groin
- A front-facing seated figure easily reads as standing, because the thighs look short
    + A shadow of the thighs and seat is painted on the shins below the knees on its own (`body.shade_under_knees`)
    + To read clearly as seated, turn it `yaw=15` to `20`; for men spread the knees (`leg_l=(-14, -6), leg_r=(14, 6)`)
- Another figure's joint positions come from `Skeleton(that_figure_pose, body, shape).joints[...]`
    + Above the shoulder is `joints["shoulder_r"] - [0, 0.14 * skeleton.unit]`

### Drawing several figures

```python
from codepainter.figure.stage import Actor, draw_actors, floor_shadows

her = Actor(spec_a, BodySpec(), her_pose, WARDROBE["suit"], depth=0.0, props=[chair])
him = Actor(spec_b, MALE_BODY, his_pose, WARDROBE["suit"], depth=-0.9, over=("hand_l",))
figures = draw_actors(painting, [her, him], style)
floor_shadows(painting, [her, him], style, color="#30353c")
```

- Figures are drawn from the smallest `depth` (farthest) on
    + Right after a nearer figure is drawn, its shadow falls on the farther ones
- Parts listed in `over` are drawn again on top after all figures
    + For scenes where the hand of the person behind rests on the shoulder or arm of the person in front
    + The names are `hand_l`, `hand_r`, `arm_l`, `arm_r`
    + Use the hand whose arm shows; a hand whose arm hides behind the front person floats alone
    + For such a hand `draw_actors` gives a warning; hold with the other hand, or send the elbow forward with `reach(..., pole=...)`
- Returns the union of all figure masks, used for scene lighting (`sets.light_figures`)
- `hands` (left and right hand masks) is added to the `draw_figure` masks

## Scene backgrounds

```python
from codepainter import sets

info = sets.SETS["night_street"](painting, style)        # beach | bedroom | office | night_street | cafe | park | panel_block
figures = draw_actors(painting, actors, style)
sets.light_figures(painting, figures, info, style)       # the scene's ambient light and rim light
image = fx.grade(finish(painting, style), **info.grade)
```

| Name | Contents | Lighting |
|---|---|---|
| `beach` | sky and clouds, headland, glittering sea, wave line, wet sand | midday, no grade |
| `bedroom` | plaster wall, window light pattern, curtain, wooden floor, skirting board | warm ambient light and a rim light from the right |
| `office` | towers beyond a glass wall, window frames, potted plant, grey carpet | cool midday |
| `night_street` | night sky, lit windows, street lamps, shop lights, reflections on the wet road, bokeh | violet ambient light and an orange rim light |
| `cafe` | cream wall, window onto the city, wooden wainscot, pendant lamps, tiled floor | warm ambient light and a yellow rim light |
| `park` | sky and clouds, two rows of trees, lawn, path, grass blades | midday, no grade |
| `panel_block` | overcast sky, three panel apartment blocks, bare trees, power line, sodium street lamp, snow and slush | cool ambient light and an orange rim light from the lamp side; finish with `fx.doomer` |

- The `lamp` of `panel_block(painting, style, lamp=0.82, lit=0.22)` is the street lamp's horizontal position (share of the width); the figures' rim light comes from that side too
    + Add falling snow after the figures with `scenery.snowfall(painting, count, keep_clear=face_mask)`
- `SetInfo` holds the floor line (`horizon`), floor shadow colour (`ground`), colour grade (`grade`), ambient light (`ambient`) and rim light (`rim`)
    + The rim light width is `sets.RIM_WIDTH` of the canvas height; even in anime it bleeds a little so it does not look like an outline
- A finished example is `examples/scene.py --scene beach|bedroom|office|night_street|cafe|park`

## Limits

- Orthographic with no photographic perspective; depth between figures shows only through drawing order and shadows
    + To draw a figure standing far away smaller, lower its `unit` directly
- Contact where two bodies wrap round each other, such as an embrace or interlaced fingers, is not supported
    + `over` supports only laying hands and arms back on top
- A front-facing seated figure has its knees foreshortened toward the viewer, so it needs the chair and the hand positions to read as seated
- Long hair on a lying figure only approximates sagging toward the floor and gathering shorter (`hair.GRAVITY_SHARE`, `LYING_LENGTH`)
    + Hair fanning out over the bed is not supported
- Lying face down, squatting and crossed legs have no presets
    + They can be built by hand with `swing` and `ground`, with more rounds of checking
- Clothing folds are a few lines in fixed places; pull folds that follow the pose are not supported
