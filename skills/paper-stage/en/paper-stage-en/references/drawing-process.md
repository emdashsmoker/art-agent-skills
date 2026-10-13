# Techniques step by step

How to make one picture in six steps: planning, form, line, colour, finishing and checking. Each step has one output and one pass condition.

## Planning

- Write the design direction note under these five headings
    + (Core impression) the one-sentence impression the picture should give
    + (Composition) aspect ratio, subject position, subject size, direction of gaze
    + (Colour) one dominant colour, one or two secondary colours, one accent
    + (Light) one key light direction, with or without a fill light
    + (Style) one of `anime`, `illust`, `painterly`
- Design the values in three bands: dark, middle and light
    + Put the subject and the background in different bands
    + Place the lightest value and the strongest contrast in one spot only, where the eye should go
- Limit the colours to 3-5
    + One complementary pair split into a large and a small area is stable, such as an orange outfit on a teal background
    + Making every shadow colour with `shadow_of` keeps the lighting consistent
- Set only one key light
    + The default is the upper left; light coming from the side the face looks toward keeps the face bright
- Recommended canvases are 1024x1280 for an upright figure and 1280x896 for a landscape
    + Past 1600 on the long side, rendering time rises sharply

## Form

- Break the subject into a list of parts, ordered from back to front
    + Example : background, back hair, neck, clothes, face, features, front hair
    + Example : sky, clouds, far mountains, near mountains, lake, foreground trees
- Write each part as a closed curve of 6-12 control points
    + `geo.smooth(points, closed=True)` joins the points smoothly
    + Mark angular spots such as the chin tip, a collar point or hair tips with their point numbers in `corners`
- Place the large parts first and the small parts in coordinates relative to them
    + Keeping an anchor point and a unit length in variables makes resizing the whole easy
    + Example : set `cx, cy, u = 512, 600, 300`, then use `(cx - 0.4 * u, cy + 0.2 * u)`
- The character of a form is decided by its silhouette
    + Mix straight lines, gentle curves and sharp curves to avoid a dull row of ellipses
    + Break the left-right symmetry a little for a natural look (a tilted head, hair swept to one side)
- The pass condition is a flat silhouette in which the subject already reads
    + Rendering with `flat_version(style)` shows the base colours without any light

### Overlap

- `painting.part(mask, color)` erases the lines under the new part
    + So the drawing order is the front-to-back order
- Multiply by the mask to paint only inside a part
    + Example : `painting.fill(pattern * shirt_mask, color)`
- Use `stroke(..., layer="color", clip=mask)` for fine marks on a part

## Line

- Line weight is 0.2-0.35% of the canvas height
    + At 1280 high, outlines are 2.5-4.5px and inner lines 1.5-2.5px
- `outline` makes the line on the side away from the light heavier on its own
    + `shade_side` is the screen direction that gets heavier, lower right by default
- Open lines get thin starts and ends through the `taper` of `stroke`
    + `taper=(0.1, 0.7)` swells quickly and fades out long
- Set the line colour with `line_color(style, fill_color)`
    + A darkened part colour is mixed in, so the line melts into the picture
- Decide where lines are left out
    + Borders between parts of the same colour, edges in strong light, the far background
- Marks that are content of the picture, such as eyes, mouth and lashes, go on `layer="color"`
    + Painterly drops the line layer, so anything kept only there is lost

## Colour

### Base colour and form shading

- `paint_part` handles base colour, form shading and outline in one call
    + For finer control call `part`, `shade_form` and `outline` separately
- Form shading is worked out by inflating the mask
    + Leave out `bevel` for round masses, set `bevel` to 20-30% of the width for flat ones
- Shadow area is set with `threshold`
    + For parts that should stay bright, such as the face, set it 0.2-0.3 below the style default
- When several parts must read as one mass, shade the joined mask once more
    + Example : shade each hair lock, then shade the whole hair mass

### Cast shadows

- Push the mask of the part in front away from the light and multiply it onto the part behind
    + `sh.cast_shadow(hair_mask, face_mask, offset=(dx, dy))`
    + With the light at the upper left, the offset points to the lower right
- The push distance stands for the height difference between the two parts
    + The shadow the fringe throws on the forehead is 5-8% of the head height
- Where parts touch, add a soft darkness with `sh.occlusion`

### Highlights

- Edge light is `sh.rim(mask, direction, width)`
    + A warm light colour on the key-light edge, a cool light colour for the rim light on the far edge
- Spot highlights are small ellipses through `fill`
    + Eyes, lips, nose tip, metal, glass
- Band highlights are several `geo.needle` shapes laid along the flow
    + Hair sheen, glints on water

### Material by material

| Material | How |
|---|---|
| Skin | reddish shadow colour, a faint flush on the cheeks and nose tip, an orange band along the shadow edge |
| Hair | forms by lock, shading per lock, strand lines along the flow, band highlights |
| Cloth | keep large planes flat, shadow only where it folds, show thickness at collars and cuffs |
| Metal | crisp border between light and dark, add a band reflecting the surroundings |
| Glass and water | let the colour behind show through, light only the edges and reflections |
| Foliage | silhouette of the mass first, single leaves only at the edges |
| Sky | deep at the top and bright at the horizon, stress the lit edge of clouds |

## Finishing

- `finish(painting, style)` runs the default finishing for each style
    + For more tuning apply `fx` functions to the returned image
- Finishing cannot fix flaws in the picture
    + Apply it only after form and value structure have passed
- For painterly, pass a mask of the areas to paint finely as `importance`
    + The face mask for figures; it can be left out for landscapes

## Checking

- Open the rendered image and check it against the table below
    + Once whole, once as a zoomed crop of the key area

```python
from PIL import Image
Image.open("out.png").crop((300, 340, 740, 780)).resize((880, 880)).save("crop.png")
```

| Defect | Cause | Fix |
|---|---|---|
| Subject sinks into the background | value bands overlap | move the background or the subject one band |
| Form looks lumpy and awkward | wrong control points, wrong proportions | render the silhouette alone and fix the control points |
| A part pokes out of the body | too much bend or belly in `lock` | halve them and narrow the root |
| Shadow covers more than half a part | threshold too high | lower it by 0.1-0.2 |
| Ridge marks on a pointed part | inflation ridge | pass `inflate(mask, smoothing=0.45)` as `height` |
| Odd shadow at the canvas edge | a part ends at the picture edge | carry the part past the edge |
| Lines look mechanically even | no weight variation | use `outline`, set `taper`, apply `geo.wobble` |
| Joint lines show between joined parts | outlined part by part | join the masks and apply `outline_mask` once |
| A groove shows at the seam of a joined form | part contours do not meet | melt with `sh.melt(mask, radius)` before filling |
| Shadow colour floats on clothes | skin shadow colour painted on another material | apply `style.shadow_tint` in multiply mode |
| The whole picture looks hazy | too much bloom or diffusion glow | call `fx` functions one by one at lower strength in place of `finish` |
| Face smears in painterly | no fine area given | pass the face mask as `importance`, `detail=1.3` |
| Painterly is covered in tiny dots | too much small pattern in the source | simplify the source, `detail=0.8` |
| Bumps and dents on the body's side contour | points from frames with different tilt joined in one curve | build the side contour from one width-by-height function |
| Breasts on a turned body look stuck on like balloons | only a ball-shaped volume | use a teardrop that runs straight up to the chest plate |
| Far shoulder of a turned body juts out bluntly | the round trunk shoulder is left where the arm is hidden | remove the round trunk shoulder once the far arm hides |
| Hair strands cross the face in profile | side hair placed for the front slides across the face | draw the far side hair behind the face with the back hair |
| Profile face looks boxy | flat underside of the jaw, no jaw angle | slope the jaw underside up to the jaw angle and join the neck behind it |
| Back of the head looks bald in profile | hairline far from the ear, no hair in front of the nape | set the hairline just behind the ear and hang the near side hair in front of the nape |
| Profile eye looks like a front eye | the front eye shape is only turned | use a wedge shape, narrow the iris and move it forward |
| Hard pink blotch across the middle of the cheek | the whole face inflated like a ball for shading | limit the inflation depth (`bevel`) to the width of the face edge |
| Salmon band around the forehead and ears | the whole scalp cap throws a long shadow | long shadows only for fringe locks, a short one for the cap |
| A line appears between head and neck | shading breaks at the lower edge of the head mask | shade with a height that reaches into the neck join behind the jaw angle, throw shadow only from the jaw |
| Sleeves puff like puff sleeves | ease added from the shoulder | zero ease at the shoulder, rising gently to mid upper arm |
| A man's sleeves balloon | ease added on top of a thick arm scale | arm scale around 1.2 and sleeve ease around 0.03 for clothed figures |
| Black square scrap on top of the shoulder in profile | only the end of a strap hidden by the arm is left | end the strap where the arm first hides it |
| Feet are long and flat like flippers | feet too long and thinning to the toes | shorten the foot, thicken the instep and toes |
| A loose top bulges like a pregnant belly | cloth falls straight down from the bust all the way | pull it back toward the body as it falls, into a slope |
| Near lapel goes flat on a turned body | only polygon corners are wrapped round the body | fill in points along each edge, then wrap |
| Shorts look like a skirt at 45 degrees | the cloth covers both legs as one mass | draw the near leg's contour inside the cloth |
| Seated shorts cover down to the knees | leg openings set at hip height | cut across the thigh at a set length along it |
| A seated skirt drapes behind the chair | the standing skirt shape is used | cover hips and thighs, drape it in front of the knees |
| Seated buttocks sag below the chair | the bottom of the trunk drops between the legs | cut trunk and buttocks flat at the seat |
| Lingerie lace on a lying body points the wrong way | lace direction set by the screen | turn it with the body's lean |
| In a two-shot the back figure's hand is hidden by the front figure | the far figure is drawn first and its hand gets covered | lay just the hand back over with `Actor.over` |
| An outstretched hand is as small as a baby's | a hand pointing at the viewer shrunk in length and width | shorten only along the hand axis and keep the width |
| Fingers raised behind the head show beside the neck or jaw | the arm behind the body drawn in front of head and neck | hide the hand behind head, neck, back hair and the gaps between them |
| Pockets, ties and lapels show in a back view | front-element visibility does not know the back view | set front visibility to 0 in back views |
| A seated hoodie or jacket covers the knees like a dress | hem cut at the standing height | cover only a set length along the thighs |
| In a two-shot a hand floats with no arm | a hand whose arm is hidden behind the front figure laid over with `over` | hold with the hand whose arm shows, bring the elbow forward with the `pole` of `reach` |
| Flag-shaped scrap on the shoulder of a strapped top in profile | the neckline cuts only the front strap, no strap down the back | on a turned body carry the strap over the shoulder and down the back (`wardrobe._back_straps`) |
| A front-facing seated figure reads as standing | thighs foreshortened toward the viewer, hands covering the knees | hands outside the knees, shadow on the shins below the knees, turn 15-20 degrees |
| Hands land over the groin in a three-quarter kneel | the forward forearm sends the near hand to the middle of the body | lower the hands beside the outer thighs |
| Feet seem to float above their shadow in a downward view | the floor shadow sits under the toe tips | centre it between heels and toes, widen it with the downward angle |
| A figure lying on a lawn floats above the horizon | the lying body is placed at the vertical middle of the canvas | lay it on the near ground with `frame(..., floor=row)` |
| Two people sit facing each other across empty air | chairs with no table | give `props.table` to one of them with `reach` at half their distance |
| A beanie reads as a bowl haircut | black hat on black hair | set `hat_color` one step lighter than the hair |
| Hair strands poke out above a beanie | hair volume under the hat unchanged | plan the hair pressed flat under a hat, cover all hair above the cuff with the hat's convex hull |
| Lamp light dies to white after the doomer grade | orange painted with `screen` over bright snow loses its saturation | paint warm light with `mode="normal"` |
| After the doomer grade only skin in shade stays pink | the warm-light test includes skin in shade | narrow the test to red minus blue of 0.30 or more and brightness of 0.55 or more |
| Snowflakes on the face look like blemishes | snow scattered evenly over the whole picture | `snowfall(..., keep_clear=face_mask)` |

- A process sheet is made by recording `painting.snapshot("step name")` and calling `fx.stage_sheet(painting.stages, "sheet.png")`
    + Sheet labels are in English because of the default font
- If the same defect remains after two fixes, change how that part is built
    + Example : split a complex form drawn as one curve into 2-3 parts
