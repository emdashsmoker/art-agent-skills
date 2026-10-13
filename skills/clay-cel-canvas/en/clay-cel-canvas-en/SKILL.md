---
name: clay-cel-canvas-en
description: "Code-sculpted, cel-painted pictures, no image model. A 3-D clay mannequin sets proportion, pose and shadow; 2-D anime faces sit on it. Layers follow a painter's order and every render is checked by eye. Three flavours: anime (cel shading, bloom), illustration (paper tooth, print grain), painterly (brush strokes, impasto), plus an optional mood grade. Draws sharp-jawed characters, clothes and wind-blown skirts, two-shots, hair and face templates, props, still life, landscapes and perspective cities. References: api.md (engine), figure.md (faces, hair, anatomy, mannequin), wardrobe.md (clothes, poses, places), styles.md (styles, mood), scenery.md (nature), city.md (streets), still-life.md (objects). Use whenever the user asks for a picture: '/clay-cel-canvas-en', 'draw with code', 'anime-style picture', 'illustration', 'draw a character', 'full body', 'figure drawing', 'two people', 'still life', 'landscape', 'cityscape'. Also when no image API exists. Not for charts, diagrams, UI mockups, icons or logos."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and THIRD_PARTY_NOTICES.md
---

# clay-cel-canvas-en

> Translation notice: this English edition was translated from the Korean original (`clay-cel-canvas`). Its performance, logic and behaviour may differ from what the original intends.

A skill for drawing pictures with code. It uses no diffusion model and no image-generation API.

## Principles

- A picture is the sum of its procedures
    + A painter works in order: plan, form, flat colour, shading, line, detail, finish
    + Each procedure is written as coordinates, colours and compositing operations
- A style is a bundle of parameters for each procedure
    + The same scene script renders in three styles: `ANIME`, `ILLUST`, `PAINTERLY`
- Quality is set by the number of inspections
    + You cannot see the result while you write the coordinates
    + Opening the rendered image and fixing it is the real work of drawing

## Setup

- Dependencies: `numpy`, `opencv-python`
    + Install them first if they are missing
- Engine location: `scripts/atelier/` in this skill folder
- Top of a scene script

```python
import sys
sys.path.insert(0, "<this skill folder>/scripts")
from atelier import Art, STYLES, spline, ellipse, symmetric, rotate, mix
```

## Coordinates and layers

- The canvas is always 1000 units wide
    + Its height is `1000 * aspect` units
    + Units do not depend on pixel size, so a 512 px preview and a 2048 px final use the same script
    + The y axis grows downward
- There are 4 layers
    + `flat`: base colours and painted detail
    + `shade`: shadows (multiply)
    + `glow`: light (screen)
    + `line`: line art
- Adding a part with `art.part()` clears the shadow, light and line beneath its area
    + A part drawn later sits in front
    + Draw from back to front
- Inside a `with art.place(at, scale, angle, flip, pivot):` block you draw in local coordinates
    + Make reusable sub-pictures (a head, a hand, a tree, a still-life object) as functions and place them at any position and size
    + Coordinates, widths and radii inside the block are all transformed together
    + The light direction is not transformed, so shadows stay correct when a sub-picture is flipped or rotated

## Workflow

After each stage, render at 512 px and open the image yourself. If you see a defect, fix it before moving on.

### Stage 1: plan

Write constants at the top of the script.

- Subject and composition: picture ratio `ASPECT`, camera `VIEW = (centre x, centre y, zoom)`
- Light: `LIGHT = (x, y, z)` is the direction the light comes from
    + Front light from the upper left is `(-0.45, -0.60, 0.66)`
- Colour: name 8-16 colours in a `PALETTE` dictionary
    + Base it on 1 main colour, 1 complementary or contrasting colour, and 1 near-neutral colour
- Style: choose `anime`, `illust` or `painterly`
    + See `references/styles.md` for how to choose

### Stage 2: form

- List the parts from back to front
    + Example for a person: background, back hair, neck, clothes, ear, face, eyes, nose and mouth, front hair, accessories
- Place control points for each part and build its outline with `spline(points, closed=True)`
    + 6-20 control points per part is about right
    + Mark sharp corners as `(x, y, True)`
    + For a symmetric shape place half the points and use `symmetric(half, axis_x)`
- Build limbs, fingers and tree trunks with `art.tube([(x, y, width), ...])`
    + Give only the joint positions and the width at each joint; rounded flesh follows
- Set a person's coordinates from the proportions in `references/figure.md`
- Follow the assembly methods in `references/scenery.md` for landscapes, `references/city.md` for cities and `references/still-life.md` for still life
- Objects made of boxes and cylinders (laptops, furniture, buildings) get 3-D coordinates and are projected with `Camera`
    + Eyeballed coordinates do not make parallel edges meet at one vanishing point
- Full-body figures, especially seated or reclining poses and nudes, are built on the 3-D mannequin (`atelier.mannequin`, `atelier.sculpt`)
    + Limbs placed in 2-D drift in length and overlap as the pose gets complex, and the body twists
    + The mannequin takes only the directions of pelvis, chest and head plus target positions for hands and feet; it solves elbows and knees itself
    + The face is the bust example's head, placed at the mannequin's chin
    + There are 2 builds, `FEMALE` and `MALE`. The male has his own bust, nude and clothed examples
- Start a clothed figure from a combination in `examples/outfits.py` (`references/wardrobe.md`)
    + Choose a pose preset (`atelier.staging`), clothes (`atelier.wardrobe`), a place (`examples/scenes.py`) and a shot
    + `frame()` sets the camera for the shot; the head follows the body's head direction and turns up to three-quarter view
    + Skirts, dresses, scarves and wind come from `atelier.drape`; two people come from `DUOS` and `nude.draw_cast()`
- Build the masks needed for shadow work ahead of time with `art.shape(curve)`

### Stage 3: flat colour

- Add parts from back to front with `art.part(curve_or_mask, color)`
- At this point check silhouette and colour layout with `art.save(path, stage="flat")`
    + The subject must read from its silhouette alone

### Stage 4: shading

- `part()` adds the form shadow itself; `bulge` picks the kind of volume
    + No `bulge`: a balloon-like volume. A circle becomes a sphere, a band becomes a cylinder. Use it for fruit, limbs, clouds, torsos
    + `bulge=radius`: a flat volume rounded only at its edges. The smaller the radius, the thinner the shadow along the edge. Use it for clothes, faces, walls, paper
    + Parts that must stay flat take `shade=False`
- Cast shadow: `art.shadow(art.move(caster_mask, dx, dy) * receiver_mask, tint)`
    + Shadows of hair on the forehead, the chin on the neck and a collar on the clothes create depth
- A shadow colour is a multiply colour
    + Use a light pink on skin (for example `#EDCBC4`)
    + Elsewhere use the default pale violet

> (Order rule) Apply a shadow cast onto a lower part before drawing the upper part. Applied after, the shadow stains the upper part too.

### Stage 5: line

- `part()` draws the outline itself
    + It thickens on the side away from the light
    + The line colour is a darkened version of the part's colour
    + Parts that must look continuous take `outline=False`
- Inner lines come in two kinds
    + `art.line()`: contour-like lines such as folds and hair strands. Styles without line art skip them
    + `art.mark()`: painted strokes such as lashes, brows and lip lines. Every style draws them
- Vary stroke width with `taper`: `both`, `start`, `end`, `none`

### Stage 6: detail and light

- Spend effort where the eye goes first
    + For a person that is the eyes. Stack white, iris, iris rim, pupil, lower reflected light, upper-lid shadow, highlights in that order
- Add light with `art.light(mask, color, opacity)`
    + Use it for highlights, hair sheen and back-light rims
- Make soft colour changes with `art.blob()` and `art.ramp()` masks
    + Cheek blush, sky gradients, the darker colour toward the hair ends
- Mark focus areas with `art.focus_on(mask)`
    + The finish keeps detail sharper inside them

### Stage 7: finish

- `art.save(path)` applies the style's post-processing
- A mood layer goes over the post-processing: `art.grade = doomer` (see the mood layer in `references/styles.md`)
    + It fits any style. Choose the scene's colours and props in the same mood
- Render finals at `width_px=1024` or more
    + For cleaner lines draw at 2048 and use `save(path, downscale=2)`
- `art.save_stages(path)` saves 5 stages side by side in one image: line, flat, shade, light, final
    + Use it when asked to show the process

## Minimal example

```python
art = Art(STYLES["anime"], width_px=512, aspect=1.0, light=(-0.45, -0.60, 0.66))
art.paint(art.everywhere(), "#F2C79A")                      # background
art.paint(art.ramp((0, 0), (0, 1000)), "#3F7C85", 0.9)      # gradient over it
art.blur(6)                                                 # push background out of focus
body = art.part(ellipse(500, 560, 260, 300), "#E8765C")     # shape, flat, form shadow, outline
leaf_mask = art.shape(spline([(500, 300), (640, 160, True), (560, 330)], closed=True))
art.shadow(art.move(leaf_mask, 20, 40) * body)              # cast shadow before the leaf is drawn
art.part(leaf_mask, "#4FA36B")
art.light(art.blob((400, 440), 90) * body, "#FFFFFF", 0.7)  # highlight
art.save("out.png")
```

## Inspection checklist

Open the render and check each item.

- Form: does the subject read from its silhouette alone?
- Proportion: are the person's eyes, nose, mouth and jaw within the ranges in `references/figure.md`?
- Overlap: are there no gaps or stray slivers between parts?
- Shading: is every shadow on the side away from the light?
- Bleeding: has no shadow spread onto another part?
- Focus: does the most worked area match where the eye goes?
- Style: do lines, shadow edges and texture follow the chosen style's rules?

Crop and zoom into small areas. Defects in eyes and mouths do not show at full-picture scale.

## Common defects

| Symptom | Cause | Fix |
|---|---|---|
| Beard-like dark area under the face | Shadow cast on the neck applied after the face | Move the shadow before the face's `part()` |
| Slivers of base colour stick out beside a part | Lower part is wider than the upper part | Narrow the lower part |
| Shadow covers the whole part | `bulge` is large for the part's size | Reduce `bulge` to 1/5 of the part's width or less |
| A line looks broken midway | A part drawn later covers it | Reorder the parts or reinforce with `art.line()` |
| A line floats in the air | A thin stroke starts outside the shape | Move its start inside the shape |
| A person drawn as an adult looks young | Eyes are large and set low | Apply the adult proportions in `references/figure.md` |
| Face smears in the painterly style | No focus area | Apply `art.focus_on()` to the face and eyes |
| Body looks like a jointed doll | Limbs drawn as separate parts get ball-shaped shading at joints | Merge torso and limb masks and draw them as one part |
| Bands or gaps at joints | Roots of overlapping limbs cover the body's shading | Apply the seam handling in `references/figure.md` |
| Too many lines make the body look like doll seams | Every muscle and bone curve drawn in ink | Line only the collarbones and folds; use light shadows elsewhere |
| Glove- or sock-like bands at wrists and ankles | Hands and feet painted apart from the limbs break the shading | Merge hand and foot masks into the limb mask, paint once, then add detail |
| Fingers and toes merge in the painterly style | No line art, so touching fingers lose their border | Add gap shadows with `hands.separate()`; leave gaps between toe tips |
| Person looks stiff | Shoulder line and hip line are parallel | Put the weight on one leg and tilt the two lines opposite ways |
| Building perspective is off | Windows and road placed by eye | Compute coordinates with the projection in `references/city.md` |
| Full body looks twisted | Limbs placed in 2-D drift in length and overlap | Pose with the 3-D mannequin |
| Mannequin joints swell like balls | Several forms melted into one joint add volume | Join end to end at the joint with similar radii and narrow the melt |
| Ring-shaped crease at a mannequin joint | The melt's edge falls near the joint | Increase the melt distance (`reach`) |
| Mannequin shoulders look square | The round end of the upper arm pokes above the shoulder line | Lower the shoulder joint to the shoulder line |
| Man looks like a boy | Narrow jaw, thin neck, sloping shoulders | Apply the male face and body comparison in `references/figure.md` |
| Muscles or toes show through clothes | Clothes grown straight from the body follow every groove | `dress(..., smooth=0.012)`; build shoes as separate rounded boxes |
| Clothes puff up like balloons | Large `smooth` adds volume at each melt | Reduce `smooth` to about 0.012 |
| Neck disappears when clothed | The grown shirt covers the neck root and shoulders | Carve the neckline with `scene.carve()` (`references/figure.md`) |
| Male face looks bland | Wide face, small eyes, helmet-like hair | Narrow the face, enlarge the eyes, split the hair into locks (male comparison in `references/figure.md`) |
| Clothed body looks muscular | Shoulders wide and square for the head, sleeves grown along muscles, camera looking up | Bring outer shoulder width to about 1.6 (female) or 1.8 (male) head heights and slope the shoulders. Straight cylinder sleeves, camera at eye level (`references/figure.md`) |
| Toes look cut off | Forefoot narrower than the toe row, so outer toes stick out of the foot | A flat ellipsoid that widens the forefoot (`FOREFOOT`) |
| Skin shows through shoes | Shoe box smaller than the foot | Add a thinly grown film of the foot to the shoe group |
| In a nude, fingers drop near the groin and read as an unintended gesture | With the back of the hand up, the thumb drops below the palm | Lay the hand flat, raise `curl` to fold the thumb, lift the wrist a little |
| Trouser legs or stockings balloon at the hips | Legs grown as separate groups do not melt into the hips | Grow pelvis and legs as one group and cut each leg with `cut_leg()` |
| Round hole under the neckline | Carving only the front leaves a ring of cloth round the neck | Carve away everything above the neck root |
| Ties, straps, lapels or pockets do not show | Buried inside the melted, puffed clothes | Lay a cloth grown the same way as the garment beneath with `patch()` |
| Skin shows at the short-sleeve shoulder seam | The deltoid stays outside the sleeve | Grow the `shoulder` region with the sleeve |
| Loose clothes swallow the arms | The body-panel box covers the front of the arms | Carve the forearm and hand shapes out of the clothes |
| Blotches on two-layer clothes | Equal thickness swaps front and back per pixel | Make the inner garment 2 mm thinner |
| A strap looks broken near the collarbone | The strap sinks into the melted skin; straight runs between points dive under the curve | Fill densely with `strap([Skin(scene)], points)` so it sits on the real skin |
| A strap breaks over the shoulder | A straight run under the ridge splits onto front and back faces, leaving a gap | `strap()` adds a point mid-gap to lift it onto the ridge |
| Underband, hip string or waistband does not show | A band wrapped on the original forms sinks into the melted skin | Wrap it on `Surface(marks, torso regions)` (`_band(..., melted=True)`). `Skin` hits the nearby arm first |
| Bra straps end on the upper back | The strap path does not reach the underband | Run the path's end down to underband height on the back |
| Skin shows at the waist under a dress or shirt | A body panel grown only to the belly sinks into the skin at the waist | Grow to the pelvis region, then cut at the waist |
| Skirt swallows the hands | Skirt radius lies outside the lowered hands | Pull the skirt in at the hands and forearms (`Flare`'s `obstacles`) |
| Hole-like dent in the skirt under a hand | The pull-in digs into the skin | Stop just above the skin (`flare_profile`'s contact table) |
| Skirt waist looks like a basket rim | Wind room and 1.4 cm room added to the waist radius | Waist 4 mm off the skin; room only from below the hips |
| Skirt stiff like a lampshade or cone | Flares right at the waist; folds are an even sine | Follow the body to the hip line, then flare; vary fold spacing and depth |
| Skirt balloons like a sack on the downwind side | Wind room added all round | Measure round the wind-swayed centre; no flare on the downwind side |
| Top pokes out below the skirt waist | Tucked top is thicker than the skirt's waist room | Give `ease` the top's thickness (1.4 cm over a tee) |
| Scarf floats like a choker; tails are lumpy | One thin loop round the neck; tails of chained ellipsoids | Two thick loops and a knot, two `Ribbon` tails |
| Skirt balloons at the knees when legs cross or knees rise | Legs joined by a round bar and cut in one plane | Cover only to the knees and cut per leg; a flat web between the legs (`_web`) |
| Face drawn on the back of the head in a back view | The drawn head is a front view | Past 110 degrees of turn, lay only the hair (`nude.BACK_VIEW`) |
| A chair or bed shows as a white box or grey slab | The place has no colour for that support role | Set `seat`, `bed`, `wall` colours per place |
| Floor-slab outline shows across same-coloured grass | Backdrop ground and 3-D floor meet off line | Put the hill's foot on `ground_edge()` |
| Thick dark band at the far edge of the floor | Ground within 5 degrees of the horizon jumps in depth per row and outlines pile up | Shorten the floor so its far edge stays 5 degrees below the horizon |
| Every person has the same face | One hair style, hair colour and feature set | Choose with `HeadLook` (hair and face templates in `references/figure.md`) |
| The beanie looks like a small cap perched on top | Its brim sits high on the forehead | Lower the brim to just above the brows (`PropPlaces.brim`) |
| Beanie ribs stick out of the hat | Rib lines drawn without a mask | Make ribs and fold line as brush masks multiplied by the hat mask |
| Orange rim light on the beanie in a bust | The rim follows the hair outline under the hat | Merge the hat mask into the rim-light mask |
| Cigarette smoke vanishes in full-body pictures | Head drawing units shrink in a full body, so strokes are 1-2 px | Thicken smoke strands and haze (`SMOKE_STRANDS`, `SMOKE_HAZE`) |
| Shot from behind, the floor lies only on the camera's side | The floor slab runs only toward +y | Flip it with `ground_prop(place, looking_back(camera))` |
| The side edge of the floor slab shows in a wide frame | The slab reaches 8 m to each side | Increase the place's `ground_width` |
| Backdrop buildings change size from shot to shot | Backdrop drawn in canvas units | Lay it out in metres and project with `camera.project()` (rooftop district) |
| White sneakers and snowy ground glare at night | Bright colours stay brightest even after the mood layer | Dark sneakers (`dark_sneaker`), blue-grey snow |
| In a knee shot the wall hides the whole place | Even a 1 m wall fills the frame when zoomed in | A full shot or a pose without a wall |
| Wires, pylons, twigs and snowflakes vanish in the painterly style | The brush finish paints over thin lines and small dots | `keep_fine_lines(art)` puts thin lines darker than their surroundings in focus. `snowfall()` puts the flakes in focus |
| A man with a bare forehead looks like he is balding | The hairline sinks at the part | Keep the hairline even from the part to the far temple |
| Short hair looks like a helmet | Side hair runs outside the face outline down to the jaw | Tuck the sides and nape inside the face outline |
| A seated skirt balloons like a bell | A skirt round a vertical axis wraps the forward-reaching thighs | Switch to a tube skirt that follows the thighs (`flared_skirt` switches itself) |
| A wind-blown hem hides behind the body | The wind points away from the viewer (+y) | Give the wind a small component toward the viewer (-y) |
| In a two-shot the far person's head is drawn over the near person's body | The drawn head knows nothing of 3-D occlusion | Paint the farthest person first (`draw_cast`) |
| Bra cups look as small as plasters | Only the breast ellipsoid grown thinly, exposing the melted slope | A moulded cup: the breast grown by 1.2 cm |
| A wall hides the place | The support wall is wider than the frame | Keep it narrow like a pillar |
| Feet sink into or float above the floor | Ankle height does not match foot size | Put the lowest point of the sole on the floor (`references/figure.md`) |

## Reference files

Read a document only when drawing its subject.

| Document | Contents | When to read |
|---|---|---|
| `references/api.md` | Full list of engine functions | Always, before writing a script |
| `references/figure.md` | Faces, hair style, hair colour and feature templates, head props, head turning, full-body proportion, poses, hands, feet, the 3-D mannequin, nude anatomy, clothes | When drawing people |
| `references/wardrobe.md` | Clothes, skirts and dresses, wind, 10 pose presets, two-shots, camera framing, 9 places, combination examples, 4 doomer figures | When drawing clothed people or two people |
| `references/scenery.md` | Sky, clouds, mountains, water, trees, grass | When drawing nature |
| `references/city.md` | Perspective projection, buildings, windows, reflections on a wet road | When drawing streets and buildings |
| `references/still-life.md` | Still-life arrangement, textures of vessels and fruit, cloth, modern objects drawn with camera projection | When drawing objects |
| `references/styles.md` | Rules per style, making a new style, the mood layer | When choosing or changing a style or mood |

The examples are finished scene scripts. Copying the closest one and editing it is faster than starting from an empty file.

| Example | Scene | Reusable parts |
|---|---|---|
| `examples/portrait.py` | Adult woman, bust | The whole head (`head_masks`, `draw_back_hair`, `draw_ear`, `draw_head_front`), 6 hair styles and features (`styled`, `HAIR_STYLES`) |
| `examples/head_style.py` | Hair and face templates | `HeadLook`, hair and eye colour palettes, shading tones from one colour |
| `examples/hands.py` | 5 hand studies | Hands (`draw_hand`, `draw_hand_side`, `hand_parts`, `finish_hand`, `Pose`) |
| `examples/feet.py` | 3 foot studies | Feet with toes (`draw_foot`, `foot_parts`, `finish_foot`) |
| `examples/figure.py` | Clothed standing full body | Clothed body (`body_masks`, `add_limb`), pose coordinates |
| `examples/nude.py` | Female nude standing, seated, reclining | 3 mannequin poses, shared figure machinery for both sexes (`draw_figure`, `draw_cast`, `Actor`, `Sitter`, `Setting`, `head_placement`) |
| `examples/portrait_male.py` | Adult man, bust | The whole male head (`head_masks`, `draw_back_hair`, `draw_ear`, `draw_head_front`), 4 hair styles and brows (`styled`, `HAIR_STYLES`) |
| `examples/nude_male.py` | Male nude standing, seated, reclining | 3 male poses, a held cloth (`held_cloth`) |
| `examples/outfits.py` | 15 single and 3 two-person combinations | Combination machinery (`Look`, `Duo`, `LOOKS`, `DUOS`, `dress_outfit`, `cast_for`) |
| `examples/scenes.py` | 9 places | Places (`Place`, `PLACES`, `horizon`, `ground_edge`, `looking_back`), prefab apartment blocks (`panel_block`), a leafless tree (`bare_tree`), falling snow (`snowfall`) |
| `examples/head_props.py` | Head props | Beanie, cigarette and smoke, wired earphones (`PropPlaces`, `draw_beanie`, `draw_cigarette`, `draw_smoke`, `draw_earphones`) |
| `examples/doomer.py` | 7 doomer pictures | Applying the mood layer (`art.grade = doomer`), sliding the frame (`shifted`), 4 figures (`FIGURES`) |
| `examples/doomer_city.py` | Apartment street on a snowy night | Window grid on a long facade, sodium street lamps, trolleybus wires |
| `examples/doomer_landscape.py` | Winter field, pylons, birches | Pylons (`pylon`), birches (`birch`), dry grass |
| `examples/doomer_still_life.py` | Kitchen windowsill at night | Painting the view outside first, tea-glass holder, ashtray, cassette |
| `examples/figure_male.py` | Man in shirt and trousers, full body | 3-D dressing (`dress`, `sleeves`, `open_collar`, `shoe`, `clothes`), lean build `LEAN`, carving the neckline with `scene.carve()` |
| `examples/still_life.py` | Bottle, pitcher, fruit, cloth | One function per object, table shadows |
| `examples/desk.py` | Laptop, mug, smartphone, lamp, potted plant | 3-D helpers (`frame`, `slab`, `disc`, `on_plane`, `hull`) |
| `examples/landscape.py` | Lake and mountains at sunset | Ridges (`ridge`) |
| `examples/meadow.py` | Summer meadow, cumulus clouds, a big tree | Clouds and tree crowns (`puffs`) |
| `examples/city.py` | Rainy evening street | Projection (`project`), reflections (`reflect`) |

## Prohibited

- Do not draw nudity or sexual depictions of minors
    + Minor: a character set as under 18, or a character drawn with a child's body (a body before secondary sexual characteristics)
    + Art-style traits such as large eyes alone do not make a character a minor
    + If part of a request falls here, decline only that part and continue with the rest

## Limits

- Hard subjects: profiles and back views, photoreal texture
    + The face is a front drawing that is turned, so it turns only up to 35 degrees
    + A head seen from behind is drawn as hair only. Side views between 35 and 110 degrees look awkward
    + Complex body poses are solved by the mannequin
- Skirts and dresses cover folds falling from the waist and wind
    + No physics of cloth catching and folding on the body. A seated skirt is replaced by a shape that follows the thighs
    + Folds are a wave round the hem. No deep folds where cloth overlaps itself
    + A scarf tail is a single-surface ribbon. No fringe and no sagging layers of cloth
    + Hair does not blow in the wind
- Props are 2-D drawings attached to the head
    + The cigarette is held only in the mouth. There is no cigarette in the hand
    + Snow only falls. It does not settle on people or clothes
    + People in night scenes are painted with the same key light. The dark mood comes from backdrop colour, rim light and the mood layer
- Two-person presets go up to 2 people. For more people add them to `draw_cast()`
- A mannequin render takes 10-40 seconds per scene at 1280 px
- The body aims at plausibility
    + Proportion, centre of gravity and large curves are right; individual muscles are not modelled in detail
- The mannequin has no genital forms
    + The 3 nude examples use classical figure-study compositions
- Finishing one picture takes 5-15 rounds of rendering and inspection
    + Cutting the rounds lowers quality first
