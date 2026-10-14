# Bust figure rig (paintkit.figure)

Full bodies, hands and full-body garments are in `references/fullbody.md`. Face and hair settings (`FaceSpec`, `HairSpec`, `Look`) from this document are used as they are by the full-body rig too.

Draws a bust figure from parameters. One call paints back hair, body, clothes, face and front hair in order from back to front.

```python
from paintkit.figure import (ANIME, ILLUSTRATION, PAINTERLY, SKETCH, Look, BodySpec, Character,
                             FaceSpec, HairSpec, Head, Outfit, add_rim_light, draw_character)
masks = draw_character(cv, Character(head=Head((512, 480), 500), look=ANIME))
```

## Contents

1. Coordinates
2. Head
3. FaceSpec
4. HairSpec
5. BodySpec and Outfit
6. Look
7. Returned masks
8. Adjusting the impression
9. Composition
10. Adding props and patterns
11. Limits

## 1. Coordinates

- Head unit: half the length from crown to chin is 1. `head.unit` is that value in pixels
- `y`: crown -1, eyes about 0.13, nose tip 0.44, mouth 0.665, chin tip +1. Shoulders about 1.6, chest about 2.6
- `phi`: angle around the head. 0 is the front of the face, +90 the side toward screen right (at yaw 0)
- `head.at(phi, y, lift=0, forward=0)`: converts a point on the head surface to pixels
    + `lift`: share by which the point stands off the surface (around 0.10 on top of hair)
    + `forward`: distance pushed out toward the front of the face (nose, glasses temples)
- `head.path([(phi, y), ...])`: converts several points at once
- `head.facing(phi)`: how much the surface at that angle faces the viewer (1 head-on, 0 side, negative behind)

Every element on the face is defined in surface coordinates, so changing `yaw` moves and foreshortens them together.

## 2. Head

| Argument | Meaning | Recommended range |
|---|---|---|
| `center` | Midpoint between crown and chin, px | y 470-520 on a 1280-high canvas |
| `size` | Crown to chin, px | 35-42% of the canvas height |
| `yaw` | Head turn. Positive looks toward screen right. 90 is a profile, 180 the back of the head | -40..40 for the bust rig, -180..180 for the full-body rig |
| `tilt` | Head tilt. Positive is clockwise | -12..12 |
| `jaw` | Width scale of the lower face. Below 1 slims cheeks and chin for a more mature impression | 0.90..1.0 |

- With a negative `yaw`, the side of the face and the ear toward screen right (the positive `phi` side) show
- A turn of 15-25 degrees from the front (`yaw=0`) gives better volume
- Past 40 degrees the gaze stops following the viewer and looks ahead. From 42 degrees nose, lips and chin break out of the face outline and a profile line appears
- Eyes, brows and bang locks on the side turned away hide by themselves. When the face is fully turned away, hair covers the whole head
- Short hair (`length` under 1) covers the sides and back down to the nape

## 3. FaceSpec

| Argument | Default | Meaning |
|---|---|---|
| `skin` | `#ffe4d3` | Skin color |
| `eye_color` | `#4f78b8` | Iris color |
| `eye_phi` | 27 | Angle of the eye centers. Smaller brings the eyes closer together |
| `eye_y` | 0.13 | Eye height |
| `eye_half_width` | 13 | Half width of the eye (degrees) |
| `eye_half_height` | 0.105 | Half height of the eye. The strongest effect on the impression |
| `eye_slant` | 0.06 | Positive lifts the outer corners |
| `gaze` | (0, 0) | Gaze (-1..1 horizontal, -1..1 vertical) |
| `eye_contact` | True | Keeps eye contact with the viewer when the head turns |
| `lash_color`, `brow_color` | | Lash color, brow color (match them to the hair) |
| `lip_color`, `lip_fullness` | `#e0787c`, 0.5 | Lip color, 0 a line only and 1 full painted lips |
| `blush` | 0.35 | Strength of the blush |
| `smile` | 0.4 | -1 frown .. 1 smile |
| `mouth_open` | 0 | Mouth opening |
| `lashes` | 1.0 | Lash weight. Below 0.7 the outer lash flicks are left off (men 0.4) |
| `brow_weight` | 1.0 | Brow thickness. Larger also straightens the brows (men 1.6-1.8) |
| `brow_lift` | 0 | Brow height. Negative lowers them toward the eyes for a heavier look |
| `brow_tilt` | 0 | Positive raises the inner ends of the brows (worry, sadness). Negative lowers the inner ends (anger) |
| `lid` | 0 | Upper lid drop. 0 open .. 1 closed. Negative opens the eyes wide (surprise) |
| `squint` | 0 | Lower lid rise 0 .. 1. Eyes pushed up by the cheeks in a laugh |
| `mouth_corners` | 0 | Mouth corners for expressions. Positive raises (laugh), negative lowers (sadness). Moves about 3 times as far as `smile` |
| `mouth_width` | 1.0 | Mouth width scale. Narrow and open gives a round mouth (surprise) |
| `teeth` | 0 | Upper teeth showing at the top of an open mouth 0 .. 1 |

- `smile` is the faint mouth corner of the resting face, `mouth_corners` the mouth corner of an expression
- Face style presets and expression presets are in `references/fullbody.md` section 17

## 4. HairSpec

| Argument | Default | Meaning |
|---|---|---|
| `color` | `#6b4a3a` | Hair color. Shadow, highlight and line colors are derived from it |
| `bangs` | `wispy` | `full` straight-cut, `wispy` light bangs, `side` swept to one side, `curtain` parted in the middle to both sides, `short` short bangs combed sideways (men), `parted` split at the parting and falling to the temples (short at the parting, so the forehead shows as an inverted V), `back` combed from the hairline back over the crown (slicked back), `spiky` locks standing up from the crown with pointed bangs, `none` open forehead |
| `bangs_length` | -0.10 | y of the bang tips. -0.15 brows, 0.1 eyes |
| `part` | -20 | Position of the parting (phi). `side` sweeps away from the parting |
| `length` | 2.9 | y of the back hair tips. 0.6 short hair (under 1), 1.1-1.3 bob, 1.7 shoulders, 3.0 chest |
| `side_length` | 1.25 | End y of the locks framing the face |
| `wave` | 0 | 0 straight .. 1 wavy |
| `fullness` | 1.0 | Width of the back hair |
| `volume` | 0.10 | How far the hair stands off the scalp |
| `shine` | 1.0 | Highlight band across the crown. 0.4-0.6 recommended for watercolor and oil |
| `seed` | 7 | Random seed of the lock placement |
| `tie` | `none` | Tied hair. `ponytail` high ponytail, `low_ponytail` low ponytail, `braid` a single braid, `bun` high bun, `low_bun` low bun (chignon), `half_up` half-up |
| `tail_length` | 2.4 | y where a ponytail or braid ends |
| `tie_color` | `#2b2629` | Color of the hair tie |
| `flow` | 0 | How far a ponytail or braid streams back. 0 hangs .. 1 level (running, wind) |
| `fade` | 0 | Density of the clipper-cut area. 0 none .. 1 bare skin. That area turns a cool grey with the scalp showing through |
| `fade_line` | -0.35 | y where the clipper cut starts on the sides and back. -1 or less clips the whole head (buzz cut) |

- `length < 1.7` is treated as a bob, with the ends curling in
- `length < 1.0` is short hair: the back hair follows the scalp only down to the nape, the side hair ends above the ears and sideburns appear. The hairline passes over the ears, runs down behind them and is lowest at the middle of the nape. `short` bangs suit it
- Male face and hair presets `MALE_FACE`, `MALE_HAIR` are in `references/fullbody.md` section 9
- Use `curtain` together with `part=0`
- With any `tie` other than `half_up` all the hair is tied. There is no mass of back hair, and comb lines in the direction of the tie are drawn over the hair covering the scalp
    + Locks framing the face stay only with `side_length` 0.5 or more. 0 gives neat hair with everything tied
    + Tails and buns are painted over the body and head when the back of the head faces the viewer (from profile to back views), and behind the body otherwise
- The edge of `fade` drops below the face in front of the temples, so the hairline over the forehead stays. Above 0.3 the sideburns disappear too
- The 24 named hairstyles are ready to use through `hairstyle()` in `references/fullbody.md` section 16

## 5. BodySpec and Outfit

| BodySpec | Meaning |
|---|---|
| `turn` | Torso turn (degrees). About half of the head turn, in the same direction, looks natural |
| `lean` | Shoulder tilt (degrees). Positive drops the shoulder on screen right |
| `shoulder_scale` | Shoulder width scale |

| Outfit.kind | Shape |
|---|---|
| `knit` | Round-neck knit |
| `turtleneck` | Turtleneck |
| `vneck` | V-neck top. Collarbones show |
| `camisole` | Top with straps. Shoulders and collarbones bare |
| `offshoulder` | Off-shoulder |

`Outfit(kind, color, trim='', detail=1.0)`. `trim` is the color of collars and straps, `detail` the strength of volume shading and seams.

## 6. Look

| Preset | Lines | Shadow edge | Matching finish |
|---|---|---|---|
| `ANIME` | Thick and dark | Hard | `finish_anime` |
| `ILLUSTRATION` | Thin and light | Soft + facial modeling | `finish_illustration` |
| `SKETCH` | Pencil feel | Medium | `finish_watercolor` |
| `PAINTERLY` | None (only lashes, brows and the mouth line stay) | Soft | `finish_oil` |

To change the light direction or strength, use a copy.

```python
from dataclasses import replace
look = replace(ILLUSTRATION, light=(0.7, -0.8), shade_depth=1.2)
```

Fields: `line_scale` (line weight scale), `line_depth` (how dark lines are), `line_opacity`, `shade_soft` (blur of the shadow edge in px), `shade_depth` (shadow strength), `highlight` (highlight strength), `light` (light direction), `light_height` (height of the light in the full-body volume shading; lower gives deeper relief).
`shade_depth=0, highlight=0` leaves only the flat base colors.

## 7. Returned masks

The dict returned by `draw_character`.

| Key | Area |
|---|---|
| `all` | The whole figure |
| `face` | Head (skin) |
| `eyes` | Open area of both eyes |
| `front_hair`, `back_hair` | Front hair side, back hair |
| `tie` | Ponytail, braid, bun (an empty mask without tied hair) |
| `cloth` | Clothes |
| `neck`, `torso` | Neck, shoulders and chest (silhouette of the skin) |

Example uses

```python
add_rim_light(cv, masks['all'], look, color='#ffe2b0', width=6, opacity=0.8)   # backlit rim
cv.tint(masks['all'] * cv.linear((0, 700), (0, 1280)), '#2a2f55', 'multiply', 0.25)  # sink the lower part
detail = np.maximum(grow(masks['eyes'], 14), masks['face'] * 0.6)              # detail area for oil
```

## 8. Adjusting the impression

| Desired impression | Adjustment |
|---|---|
| Mature adult | `eye_half_height` 0.095-0.11, `eye_y` 0.10-0.13, `lip_fullness` 0.6 or more, `blush` 0.2-0.3, bangs `side`/`curtain`/`none` |
| Crisp and striking | `eye_half_height` 0.115-0.125, `eye_half_width` 14, `eye_slant` 0.10 |
| Soft and gentle | `eye_slant` 0.0-0.03, `smile` 0.5 or more, `blush` 0.4 |
| Calm and urban | `smile` 0.1-0.2, `eye_slant` 0.10, dark hair, `turtleneck` |

- The larger the eyes and the lower they sit on the face, the younger the face looks. For adult characters, keep within the ranges of the table above
- Slightly deeper skin (`#f7d6c2` and the like) keeps the face from blowing out against bright backgrounds and bloom

## 9. Composition

- At 1024x1280, `Head(center=(520, 500), size=500)` gives a chest-up composition
- A smaller head shows more of the body. The y of the bottom canvas edge is `(canvas height - center.y) / head.unit`
    + An edge that falls on the chest line (y 2.4-2.9) looks awkward. Cut below the shoulders (2.2 or less) or below the chest (3.0 or more)
- Leave more room on the side the head faces (with a negative yaw, move the figure a little to the right)

## 10. Adding props and patterns

Draw them over with basic shapes after `draw_character`. The code below is a checked, working example.

```python
unit = head.unit
light = character.look.light

# cloth pattern: multiply stripes inside the cloth mask only. The shading already painted stays
ys = np.arange(cv.height, dtype=np.float32)[:, None] * np.ones((1, cv.width), np.float32)
stripes = ((ys // (0.11 * unit)) % 2 == 0).astype(np.float32)
cv.tint(stripes * masks['cloth'], '#3f5f8a', 'multiply', 0.85)

# earring: below the visible earlobe (with a negative yaw, the positive phi side)
lobe = head.at(96, 0.42, lift=0.02)
drop = cv.ellipse(lobe[0], lobe[1] + 0.10 * unit, 0.035 * unit, 0.06 * unit)
cv.paint_form(drop, '#e8c25a', light, shadow=0.3, line_width=1.5, rim=0.8)

# hair pin: sits on the hair, so give it lift
clip = cv.ribbon([head.at(40, -0.42, lift=0.11), head.at(58, -0.30, lift=0.11)], 0.07 * unit, 'flat')
cv.paint_form(clip, '#e2556b', light, shadow=0.3, line_width=1.6, rim=0.7)

# glasses: two lens rims and a bridge
eye_y = character.face.eye_y
rings = cv.empty()
for side in (-1, 1):
    ring = [head.at(side * (27 + 15 * np.cos(a)), eye_y + 0.02 + 0.15 * np.sin(a))
            for a in np.linspace(0, 2 * np.pi, 40)]
    cv.tint(cv.polygon(np.array(ring)), '#ffffff', 'screen', 0.12)          # lens reflection
    rings = np.maximum(rings, cv.ribbon(ring + ring[:1], 3.2, 'flat', smooth=False))
bridge = [head.at(-12, eye_y - 0.02), head.at(0, eye_y - 0.05, forward=0.04), head.at(12, eye_y - 0.02)]
cv.ink_mask(np.maximum(rings, cv.ribbon(bridge, 3.0, 'flat')), '#3a2a2a')
```

Props that go under the hair (necklaces and the like) sit on clothes or skin, so they can simply be drawn over. When the hair must hide them, cut them with `* (1 - masks['front_hair'])`.

## 11. Limits

- This rig is for chest-up compositions only. For full bodies and hands use `draw_figure`, `draw_hand` (`references/fullbody.md`)
- The body of the bust rig is built for the front, so it turns only up to 40 degrees. Draw profiles and back views by zooming the full-body rig with `framing()` (`references/fullbody.md` sections 6, 8)
- Expressions change within brow tilt, eyelids, gaze, mouth corners, mouth opening and upper teeth. Manga symbols such as eyes closed in a laugh (^^), tears and sweat drops must be drawn by hand
- Requests beyond this range are designed directly with the methods of `references/primitives.md`
