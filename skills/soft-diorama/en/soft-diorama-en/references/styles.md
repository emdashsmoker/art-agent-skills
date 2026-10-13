# Recipes per style

## Contents

1. Common principles
2. Anime
3. Illustration
4. Watercolor
5. Oil
6. Doomer mood
7. Lighting
8. Palette
9. Troubleshooting table

## 1. Common principles

- A style is decided by the combination of three layers
    + The look at the drawing stage (line weight, shadow edge)
    + Density and focus of the background
    + The finish function
- All three layers must point to the same style. A cel-shaded figure under an oil finish blurs the style
- When bright areas are large, bloom covers the picture in white. Keep either the subject's skin or the clothes at a middle value
- Blur the background with `cv.color = blur(cv.color, 1.5-3.0)` right before painting the subject, to separate the focus

## 2. Anime

| Element | Setting |
|---|---|
| look | `ANIME` |
| Background | `sky` + `cloud_bank`, or a simple flat indoor color. Cloud edges `edge=1.0` |
| Color | Saturated base colors. Shadows are the cool colors `shadow_of` makes |
| Finish | `finish_anime(cv, glow=0.15-0.25, diffusion=0.06-0.12)` |
| Eyes | `eye_half_height` 0.11-0.125 |

- A backlit rim with `add_rim_light` lifts the figure off the background
- With a bright sky, lower `glow` to 0.15 or less

## 3. Illustration

| Element | Setting |
|---|---|
| look | `ILLUSTRATION` (`shade_depth` 1.0-1.2) |
| Background | Dark gradient + `bokeh` + `sun_glow`, blur 3.0 |
| Color | Skin around `#f7d6c2`, clothes at middle to dark values |
| Finish | `finish_illustration(cv, glow=0.2-0.3, texture=0.03-0.05)` |

- Light from the side or behind with a strong `add_rim_light(width=8-10)` brings out the mood
- The look adds the soft modeling of the face (side planes, eye sockets, nose bridge, under the lip) by itself

## 4. Watercolor

| Element | Setting |
|---|---|
| look | `SKETCH` |
| Background | Light paper-colored canvas + `wash_backdrop` + `leaves`/`petals` at the corners |
| Color | Light, clear colors. Dark colors turn muddy in the finish |
| Finish | `finish_watercolor(cv, wash=0.10-0.20, bleed=3-5, edge_darkening=1.0-1.6)` |
| Hair | `HairSpec(shine=0.4-0.6)` |

- Raising `wash` makes it paler, raising `edge_darkening` deepens the marks where paint pooled
- Without a paper margin, `border=0`
- Props that must not pass over the figure (petals and the like) are painted before the figure

## 5. Oil

| Element | Setting |
|---|---|
| look | `PAINTERLY` |
| Background | Dark, simple masses of color (`wash_backdrop`), or a landscape |
| Color | Strong value contrast. Deep colors suit the clothes |
| Finish | `finish_oil(cv, radii=(28,14,7,3), impasto=0.3-0.5, detail=mask)` |
| Hair | `HairSpec(shine=0.4-0.6)` |

- For figures pass `detail = np.maximum(grow(masks['eyes'], 14), masks['face'] * 0.6)` to repaint the face with small brushes
- Landscapes keep a strong brush feel with big brushes such as `radii=(24,12,6,3)`
- The ground color (`ground`) shows through where the brush barely reached. A brown or grey complementary to the scene suits it
- Small letters and fine patterns get buried in the strokes. Design the forms large

## 6. Doomer mood

A mood preset. Details in `references/doomer.md`

- Color: only `doomer.PALETTE`. Cold blue-grey over most of the picture, 1-2 warm points
- Figures: `ILLUSTRATION` with `light_height` 0.45-0.55, `add_rim_light(color=PALETTE['sodium'])` from the side of the street lamp
- Background: repeated windows of `panel_block`, diagonals of `wires`, snow from `snowfall`. In night scenes darken the walls with `wall='#5a6069'`
- Finish: `doomer.finish(cv, warmth=0.3-0.75)`. Raise `warmth` when there is an evening glow, lower it on an overcast day

## 7. Lighting

All of these go in with `cv.tint` before the finish, or with `finish.light_wash` after it.

```python
# sunlight leaking in: warm light spreading from the corner on the light's side
cv.tint(cv.radial((120, 90), 900) ** 1.5, '#fff0c8', 'screen', 0.30)

# sink the lower part to draw the eye to the face
cv.tint(masks['all'] * cv.linear((0, 760), (0, 1280)), '#2a2f55', 'multiply', 0.25)

# light bounced from the background on the shadow side
bounce = shading.rim(masks['all'], (-look.light[0], 0.3), 10, soft=4)
cv.tint(bounce, '#9fc4ff', 'screen', 0.35)

# unify the overall color after the finish
image = finish.light_wash(image, cv.full(), '#ffd9b0', 'soft_light', 0.25)
```

## 8. Palette

- Let one main color cover more than half of the picture (usually the background)
- Give the subject colors with a large value difference from the main color
- Use the accent only on small areas (eyes, lips, props)
- Do not pick shadow colors by hand. Make them with `shadow_of`, and with `skin_shadow` for skin
- Starting points by time of day

| Mood | Sky/background | Light | Shadow side |
|---|---|---|---|
| Midday | `#2f74d0` → `#cfe9fb` | `#fff6d8` | Bluish grey |
| Sunset | `#6f7fc0` → `#f6b79a` | `#ffe0b0` | Violet |
| Night street | `#2b2440` → `#a8645a` | `#ffc78a` | Navy |
| Indoors by a window | `#f4e6d2` → `#d9c6bd` | `#fff6da` | Brownish grey |

## 9. Troubleshooting table

| Symptom | Cause | Fix |
|---|---|---|
| Face or clothes blown out to white | Too much bloom, large bright areas | Lower `glow` and `diffusion`. Darken the skin or the clothes one step |
| Bangs cover the eyes | Bang tips too low | Move `bangs_length` toward -0.15. Or `side`/`curtain` |
| Far eye hidden by side hair | Large head turn | Keep the absolute `yaw` at 25 or less |
| Hair looks like a helmet | Locks too uniform | `wave` 0.2 or more, `bangs='wispy'`, change `seed` |
| Figure sinks into the background | Too little value contrast | `add_rim_light`, blur the background, adjust the background value |
| Shadows point every which way | Light vectors disagree | Give `look.light` and the `light` argument of background functions the same value |
| Lines too thick or too thin | Line weight does not match the style | `replace(look, line_scale=...)` |
| Cel shadow edge is hazy | `shade_soft` is large | Set it to 1.0-1.5 |
| Watercolor is blurry and muddy | Too much bleed, dark colors | `bleed` 3 or less, `wash` 0.10, switch to light colors |
| Face smeared in oil | No detail area given | Pass a `detail` mask, last `radii` value 2-3 |
| Oil strokes look like worms | Too much impasto | `impasto` 0.3 or less |
| Clouds look flat | Shade and light colors too close | Make `shade` deeper and bluer |
| Object floats like a sticker | No contact shadow | Lay a `blur(ellipse)` with `multiply` on the ground, then paint the object on it |
| Curves come out dented | Uneven spacing of control points | Space the points evenly or use fewer |
| Rendering is slow | Large canvas or oil | Check at half size. Oil only at the end |
| Skin flushes red | Shadows too deep | `shade_depth` to 1.0-1.25 |
| Body looks like a flat doll | Light hits from the front | `light_height` 0.5-0.6, light from the side, darker background |
| Limbs look attached separately | Joint edges show in a cel-shaded look | Use a look of the `ILLUSTRATION` family |
| Faces attached in perspective are blurry | Flat picture too low in resolution | Make the flat Canvas larger, `facade(resolution=28)` |
| Round objects look flat | Only the crescent shadow of `paint_form` | Switch to `paint_volume`, `bulge` at 1/3-1/2 of the width |
| Night scene blown out to white | Lamp light raised strongly with `screen` | Press down only outside the pool of light and keep its own color inside (`references/objects.md` section 6) |
| Modern objects small, floor empty | Camera far away or horizon low | Raise `focal`, lower the y of `vanishing`. Move the objects to a near z |
| Flat object splits into two layers | Only the top and bottom outlines drawn | Fill the thickness with `solids.slab` |
| Small parts vanish in oil | Big brushes cover the parts | Pass the object area as a `detail` mask |
| Body turned, face still looks front | The head turns separately | Three-quarter `head_yaw = turn * 0.6-0.8`, profile and back `head_yaw = turn` |
| Lower line of a seated figure's buttocks is bumpy | Thighs not far enough forward | z of the thigh direction in `aim()` 1.0 or more, turn the body 20-40 degrees |
| Male body flat like a mannequin | Front light buries the muscle grooves | `light_height` 0.5-0.55, light from the side, turn the body 25-35 degrees |
| Ground or road drawn upside down in two-point perspective | Points behind the camera projected as they are | Draw only what is in front of the camera with `city.project_polygon`, `city.ground_rects` |
| Picture pasted on a turned box is upside down | Face corners in a different order | Pass the face quad returned by `box()` to `paste` unchanged |
| Both hands gather over the buttocks in a back view | Arm angles are screen angles and stay put when the body turns | Give the arms in the body's own directions with `aim(turn, ...)` |
| Arm seems cut off near the elbow in a back view | Forearm reaching forward (z+) hides behind the body | z of the forearm direction 0.3 or less, x toward the outside of the body |
| Lying figure floats above the bed | `fit()` keeps room for standing feet | Put the bottom of the `fit` box 0.4-0.5 head units below the surface |
| Hand in a pocket shows over the clothes | Ordinary hand shape | `HandSpec('pocket')` with trousers or a suit. For hoodies `HandSpec('pouch')` |
| Hoodie sleeve cut off beside the hem, hand gone | The long top covers the trouser pocket | Put the hand in the kangaroo pocket with `poses.hands_in_pockets(turn, pouch=True)` |
| Doomer picture reads as just a dark picture | No repeated elements and no warm point | Add the window grid of panel blocks, wires and one street lamp, and limit warm points to 1-2 |
| Night apartment walls bright as day | Default concrete color | `panel_block(wall='#5a6069')`, far blocks `haze_amount` 0.4-0.7 |
| Cigarette smoke invisible | Grey smoke in front of a bright wall | Let it rise in front of a dark sky or a window, `opacity` 0.6-0.7 |
| Background shows between a loose sleeve and the body | Default of fitted clothes | `top(close=True)` (default for hoodies and suit jackets) |
| Face in profile hidden by hair | Side locks hang in front of the cheek | `side_length` 0.8 or less, or `bangs='side'` |
| Hair from behind looks too flat | Light falls evenly on one mass of hair | Light from the side (`light=(-0.75, -0.55)`), `add_rim_light`, `wave` 0.3 or more |
| Several figures have the same hairstyle | The same default `HairSpec` | Pick a different `hairstyle()` name per figure. Mixing tied and short hair splits the silhouettes |
| Ponytail invisible from the front | The tail is behind the head and neck | Turn the body or head 30 degrees or more. In profile and back views the tail is painted over the body |
| High bun cut off at the top of the picture | `fit()` leaves out the height of the bun | Raise the room above with `framing(headroom=0.9)` or in the `fit` box |
| Expression hard to read | Full bangs hide the brows, small face | A hairstyle showing the forehead such as `center_long`, `side_part`, `framing(..., 'face')` |
| Hem of a winter coat flares like a bell | Coat skirt made with `skirt()` | Use `long_coat()`. It falls almost straight from the hips |
| Ponytail of a running figure hangs down | Tails follow gravity by default | `hairstyle('ponytail', flow=0.6-0.8)` |
| Figures small in a group portrait, lower part empty | `group()` stands the whole bodies on the floor line | `group(..., shot='waist', gap=-0.1)`, paint the middle figure last |
| Hand of a far arm reaching forward (hugging knees, folded arms) disappears | Arm angles given as screen angles | Give the arms with `aim(turn, ...)`. Depth in the body's frame is needed to paint them in front of the body |
