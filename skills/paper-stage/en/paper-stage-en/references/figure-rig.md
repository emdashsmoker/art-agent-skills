# Portrait rig

`scripts/codepainter/figure/` is a 2D rig that draws one bust figure from parameters. It uses no 3D model; it slides a front-view layout sideways to follow the turn of the head.

## Call

```python
from codepainter.figure import PortraitSpec, draw_portrait
masks = draw_portrait(painting, PortraitSpec(...), style, light=(-0.55, -0.62, 0.56))
```

- Call it on a Painting whose background is already drawn
- Returns the `head`, `hair`, `body`, `eyes` and `figure` masks and the `frame` (HeadFrame)
    + `masks["head"]` is used as the `importance` of the painterly `finish`
    + `masks["figure"]` is the whole figure silhouette, used to keep background effects behind the figure

## PortraitSpec

| Field | Default | Meaning |
|---|---|---|
| `crown` | (0.53, 0.115) | top of the head, as shares of the canvas |
| `head_size` | 0.50 | head height / canvas height |
| `yaw` | -0.7 | head turn; -1 is a three-quarter view to the screen left, 0 front, 1 three-quarter to the right (1 = 25 degrees) |
| `turn_deg` | None | head turn in degrees, -90 - 90; when set it is used in place of `yaw`, 90 is a profile |
| `tilt` | 0.0 | head tilt in degrees, recommended range -8 - 8 |
| `jaw` | 0.85 | jaw line; 0 is a round egg shape, 1 a sharp V line |
| `eye_y` | 0.545 | eye height (crown 0, chin 1); lower reads more mature |
| `eye_spacing` | 0.142 | distance from the face centre line to the eye centre |
| `eye_size` | 1.18 | eye size factor |
| `eye_open` | 1.0 | eye height; below 1 gives narrow, cool eyes |
| `eye_tilt` | 7.0 | lift of the outer eye corners in degrees |
| `gaze` | None | gaze; None looks at the viewer, -1 - 1 looks left or right |
| `smile` | 0.15 | lift of the mouth corners |
| `lips` | 0.85 | lip colour strength; 0 shows only the line |
| `lashes` | 1.0 | lash weight; below 0.6 the outer corner lashes are left out |
| `brow` | 1.0 | brow weight; larger is lower and straighter |
| `face_width` | 1.0 | face width; 0.9 looks narrow and long, 1.1 wide and round |
| `cheek` | 0.0 | cheekbones; 1 raises the cheekbones and hollows below them |
| `nose` | 1.0 | nose size, 0.8 - 1.3 |
| `mouth` | 1.0 | mouth width, 0.85 - 1.2 |
| `lip_full` | 1.0 | lip fullness, 0.8 - 1.45 |
| `eye_shape` | "almond" | `almond`, `round` (round eyes), `droopy` (drooping eyes), `sharp` (narrow eyes with lifted outer corners) |
| `iris_size` | 1.0 | iris size; 0.8 small and sharp, 1.15 large and soft |
| `brow_tilt` | 0.0 | brow tilt in degrees; positive raises the inner ends (worried), negative lowers them (stern) |
| `brow_raise` | 0.0 | brow height shift (head units) |
| `mouth_open` | 0.0 | mouth opening, 0 - 1 |
| `eyes_closed` | None | `up` (closed in a smile), `down` (calmly closed) |
| `expression` | None | `smile`, `laugh`, `angry`, `sad`, `surprised` (laid over the face values) |
| `glasses` | None | `round`, `square`; frame colour is `glasses_color` |
| `earrings` | None | `stud`, `hoop`, `drop`; colour is `jewel` |
| `stubble` | 0.0 | stubble on the jaw and upper lip, 0 - 1 |
| `hat` | None | `beanie` (knitted beanie with a folded cuff); colour is `hat_color` |
| `hair_style` | "long" | `long`, `bob`, `short` (to the nape, ears showing), `wavy`, `ponytail`, `bun`, `two_block`, `slick` |
| `bangs` | "swept" | `swept` (side parting), `curtain` (centre parting), `textured` (short fringe swept aside), `none` (no fringe, combed back) |
| `outfit` | "turtleneck" | `turtleneck`, `blazer` |
| `skin`, `hair`, `eye`, `lip`, `cloth`, `cloth_second` | | colours; `cloth_second` is the blazer's outer fabric |
| `seed` | 7 | random placement of hair strands and highlights |

### Face presets

```python
from codepainter.figure.frame import FACES
from codepainter.figure.palette import look

spec = PortraitSpec(**{**FACES["cool"], **look("tan", "black", "gray"), "hair_style": "ponytail", "expression": "smile"})
```

| Name | Impression |
|---|---|
| `cool` | sharp jaw, narrow eyes with lifted outer corners, small iris, small mouth |
| `bright` | round face, large round eyes, wide smile |
| `gentle` | drooping eyes, inner brow ends raised in worry, faint smile |
| `elegant` | narrow face, cheekbones, full lips, thin brows |
| `sporty` | thick straight brows, wide mouth, big grin |
| `sharp_man` | V-line jaw, narrow eyes, lowered inner brow ends |
| `soft_man` | round eyes, soft jaw, faint smile |
| `rugged_man` | wide jaw, large nose, very thick brows, stubble |

- Presets, colours and hair are joined by dict merging (`{**a, **b}`)
    + For the same key the later value wins; passing them as separate keyword arguments makes the keys clash with an error
- The male presets include `short` hair and a `textured` fringe; another hairstyle overrides them in the merge
- An expression (`expression`) is added onto or multiplied with the preset values (`frame.EXPRESSIONS`)
    + `laugh` has eyes closed in a smile and an open mouth, `surprised` raised brows and a slightly open mouth
    + With hair that covers the brows, `angry` and `sad` read weakly; they read well with a `textured` or `none` fringe

### Hairstyles

| Name | Front | Profile and back |
|---|---|---|
| `wavy` | long wavy hair and side locks | the same waves |
| `ponytail` | hair combed back and tied, wisps at the temples | a tail hanging from the back of the head down the back, with a hair tie (colour from `cloth`) |
| `bun` | a bun shows behind the crown | a round bun high on the back of the head |
| `two_block` | long top hair falling in points over short clipped sides | the same structure, skin showing through the short parts |
| `slick` | short hair combed back with no fringe (use with `bangs="none"`) | a smooth back of the head |

- The hair mass adds each style's own parts on top of four base cuts (`long`, `bob`, `short`, `tied`) (`hair.STYLE_BASE`)
- Tails and buns are drawn in the back hair layer, so from the front they hide behind the head

### Colour palette

- `palette.look(skin, hair, eye, outfit)` returns a dict of colour fields
    + `"#rrggbb"` is accepted in place of a name; the lip colour is picked to suit the skin
    + `lipstick="#c0304a"` mixes in a lip colour
- Seven skin steps : `porcelain`, `fair`, `light`, `olive`, `tan`, `brown`, `deep`
    + Cheek flush, the red of the shadow edge and skin highlights move together with the skin value
- Hair colours : 8 natural (`black`, `dark_brown`, `brown`, `chestnut`, `auburn`, `blonde`, `platinum`, `gray`), 6 anime (`pink`, `sky`, `silver`, `lavender`, `mint`, `crimson`)
- Eye colours : 6 natural (`brown`, `amber`, `hazel`, `green`, `blue`, `gray`), 4 anime (`red`, `violet`, `gold`, `teal`)
- 8 outfit schemes : `classic`, `warm`, `earth`, `pastel`, `sea`, `mono`, `denim`, `doomer` (in `cloth`, `cloth_second` order)

### Tuning the impression

- A mature impression is `eye_y` 0.52-0.55, `eye_open` 0.85-1.0, `jaw` 0.8-1.0
- A younger-looking impression is `eye_y` 0.57-0.60, `eye_open` 1.2-1.4, `eye_size` 1.3, `jaw` 0-0.4
- A male face is `PortraitSpec(**frame.MASCULINE, ...)`
    + Wide jaw, small narrow eyes, thick brows, light lashes, neutral lips, `short` hair and a `textured` fringe
- A three-quarter view (`yaw` of 0.6-0.8 either way) shows the jaw line best
- Turns past 25 degrees are set with `turn_deg`
    + Between 25 and 90 degrees the three-quarter key and the profile key are blended
    + The centre line of forehead, brow ridge, dip at the root of the nose, nose, lips and chin joins the head outline to form the profile silhouette
    + The underside of the jaw slopes up from the chin to the jaw angle under the ear, and behind the jaw angle it runs into the neck with no outline
    + Past 56 degrees the far eye and brow and the far fringe are hidden
    + The near eye switches to a wedge shape made for profiles, and the iris narrows and moves forward (toward the cornea)
    + The ear gets smaller and leans back, and the hair turns just behind the ear and runs down to the nape
    + For long hair and bobs the near side hair flows from behind the ear down in front of the nape, covering the back of the head and the nape
    + The far side hair is drawn behind the face with the back hair, so the face hides it
    + The bust's neck grows deeper front to back toward the profile and starts under the jaw

### Profile proportions (90 degrees, head units, face side +x)

| Part | Position (x, y) |
|---|---|
| Forehead | (0.39, 0.36) |
| Brow ridge | (0.42, 0.44) |
| Dip at the root of the nose | (0.41, 0.49) |
| Nose tip | (0.51, 0.695) |
| Chin tip | (0.43, 0.93) |
| Jaw angle | (-0.06, 0.85) |
| Nape | (-0.30, 0.80) |
| Ear | x -0.02 - -0.16 (top leaning back), height 0.49-0.71 |

- To change the values, edit `PROFILE_CONTOUR` (22 outline points, points 9-10 on the chin) and `MIDLINE` (height, how far it stands out) in `frame.py`
- Profile eye and ear shapes are `UPPER_LID_PROFILE`, `LOWER_LID_PROFILE` and `EAR_SHAPE_PROFILE` in `face.py`

## Coordinates

- In head units the crown is y=0 and the chin tip y=1; a length of 1 is the head height
- `frame.face(points, lift)` turns front face-plane coordinates into pixels
    + x is measured from the face centre line; turning the head shifts and narrows it on its own
    + `lift` is how far a point stands out: nose tip 0.1, lips 0.03, glasses 0.05
- `frame.place(points)` turns head coordinates into pixels
    + Used for things attached to the side and back of the head (earrings, side hair, hats)
- `frame.px(units)` turns a length in head units into pixels
- In both systems positive x is the far side, away from where the face looks
    + With a negative `yaw` the whole result is mirrored left to right

| Part | Face-plane coordinates (x, y) |
|---|---|
| Eye centre | (±eye_spacing, eye_y) |
| Brow | (±0.06 - ±0.26, eye_y - 0.10) |
| Nose tip | (0, 0.70), lift 0.105 |
| Mouth | (0, 0.826), lift 0.03 |
| Chin tip | (0, 1.0) |
| Earlobe | `frame.place([(-0.32, 0.73)])` (near side) |

## Adding accessories

Draw them on the same Painting after calling `draw_portrait`.

```python
frame = masks["frame"]
ink = "#2a1c24"
for side in (1.0, -1.0):                                   # glasses
    center = (side * spec.eye_spacing, spec.eye_y + 0.01)
    rim = frame.face(geo.ellipse(center, 0.10, 0.075), lift=0.05)
    painting.fill(painting.mask(rim), "#ffffff", 0.12)     # lens glare
    painting.outline(rim, frame.px(0.009), ink, contrast=0.2)
bridge = frame.face([(-0.045, spec.eye_y - 0.01), (0.045, spec.eye_y - 0.01)], lift=0.06)
painting.stroke(bridge, frame.px(0.008), ink, taper=(0.0, 0.0))

lobe = frame.place([(-0.315, 0.76)])[0]                    # earring
drop = geo.ellipse(lobe + [0, frame.px(0.05)], frame.px(0.018), frame.px(0.03))
painting.part(painting.mask(drop), "#e8c46a")
```

- Glasses, earrings, stubble and a beanie are set straight from `PortraitSpec` values (`figure/accessories.py`)
    + The example above shows how to draw any other accessory by hand
- A beanie (`hat="beanie"`) takes a ring round the head as the lower edge of its cuff, so it turns with the head from the front, three-quarter, profile and back
    + The cuff edge sits at 0.30 head units on the forehead and 0.50 at the back of the head (`accessories.HAT_BAND`)
    + All hair above the cuff is covered; fringe, side hair and tails below the cuff stay in view
    + Under a hat the hair volume is pressed to `hair.HAT_PRESSED` times, so no strands poke out above the crown
    + A black beanie on black hair reads as a haircut, so set `hat_color` one step lighter than the hair
- Accessories that must sit behind the hair are inserted by hand following the assembly order in `figure/portrait.py`
    + The assembly order is back hair (tails and buns included), body, clothes, ears, face, stubble, features, earrings, front hair, beanie, glasses

## Hair variations

```python
from codepainter.figure import HeadFrame, hair
frame = HeadFrame(spec, painting.shape)
plan = hair.plan_hair(frame, spec)
a, b, t = frame.place([(0.30, 0.20), (0.40, 0.34), (0.52, 1.35)])      # add a long side lock falling on the far side
plan.locks.insert(0, geo.lock(a, b, t, bend=-0.08 * frame.side, belly=0.2))
masks = draw_portrait(painting, spec, style, hair_plan=plan)
```

- `plan.locks` is the list of locks from back to front, each a `geo.lock` result
    + Inserted near the start it goes behind the other locks, near the end it is drawn in front
- `plan.back` is the closed curve of the back hair silhouette and can be replaced whole
- Multiply `bend` by `frame.side` so the direction holds when the head is mirrored
- A whole new hairstyle registers a base cut in `STYLE_BASE` of `figure/hair.py` and adds branches to `_back_sides`, `_bang_defs` and `_plan_knots`

## Adding outfits

```python
from codepainter.figure import outfit

def draw_tee(painting, frame, spec, style, light, head):
    points = outfit.shoulder_side(1.0, 0.02) + outfit.shoulder_side(-1.0, 0.02)[::-1]
    curve = geo.smooth(outfit.body_points(frame, points), closed=True, corners=(0, 5, 6, 11))
    return paint_part(painting, curve, spec.cloth, style, light, line_width=frame.px(0.006), bevel=frame.px(0.26))

outfit.OUTFITS["tee"] = draw_tee          # PortraitSpec(outfit="tee") works from here on
```

- An outfit function returns the mask of the area it drew
- `outfit.body_points` turns trunk coordinates (left-right symmetric, head units) into pixels and follows the upper-body turn

## Limits

- The head is supported from the front to a profile (90 degrees)
    + The trunk of the bust outfits (turtleneck, blazer) turns only to three-quarter; in a profile bust the trunk stays close to the front
    + The blazer collar keeps its front shape, so in a profile bust the neck and collar can come apart; a turtleneck is recommended for profile busts
    + The back of the head is supported in the full-body rig's `view="back"`
- Tied-up hair that shows the ears is not included
    + If needed, build it by hand from basic shapes and allow more rounds of checking
- For full figures and hands use the full-body rig in `references/figure-body.md`
- Tilting the head up and down (nodding) is not supported
