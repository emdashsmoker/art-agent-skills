# Setting parameters

Face, hair and palette settings of the portrait (`portrait`) and the full figure (`figure`). A spec JSON holds only the items that differ from the defaults. The merge order is `assets/spec_default.json`, the style file's `figure`, the subject file, the sex preset (`assets/sex_<sex>.json`), then the user spec

## Contents

- Coordinate units
- canvas, seed, light
- sex
- pose
- face
- eyes
- nose, mouth
- body, outfit
- hair
- expression
- look
- accessories
- style (palette, patterns, rendering strength)

## Coordinate units

- The length unit is the head unit (1.0 = half the face width)
- The origin is midway between the eyes. X points to the picture's right, y points down
- Each style file already overrides the proportions, so a user spec only adjusts individuality

| Measure | anime | illust | paint |
|---|---|---|---|
| Chin height `chin_y` | 1.22 | 1.26 | 1.30 |
| Eye half-width `half_width` | 0.255 | 0.245 | 0.222 |
| Nose tip height `tip_y` | 0.55 | 0.58 | 0.63 |
| Mouth height `mouth.y` | 0.84 | 0.88 | 0.93 |

- Watercolor and pencil keep the `illust` proportions. Manga and pixel art keep the `anime` proportions

## canvas, seed, light

| Key | Default | Description |
|---|---|---|
| `canvas.width`, `canvas.height` | 1200, 1600 | Output size in pixels. A 3:4 ratio is recommended |
| `seed` | 7 | Random seed of hair strands, textures and brush strokes. The same value gives the same picture |
| `light` | [-0.55, -0.55, 0.63] | Vector pointing to the light (x, y, z). Negative x is left, negative y is up, z is toward the viewer |

## sex

| Key | Default | Description |
|---|---|---|
| `sex` | "female" | "male" merges the `assets/sex_male.json` preset before the user spec |

- What the male preset changes
    + (Face) a longer face (`chin_y` 1.34), a wide square jaw (`jaw_width` 0.90, `chin_width` 0.24), ears (`face.ears`)
    + (Eyes) smaller eyes, low thick straight brows, no lash wings
    + (Neck and shoulders) a thick neck, an Adam's apple (`body.adams_apple`), broad shoulders
    + (Hair) short hair (`hair.style` "short"), a short fringe swept to the side
    + (Outfit) a crew-neck T-shirt (`outfit.cut` "crew"), no necklace
    + Skin, hair and cloth colours per style, and beard shadow (`face_render.stubble`)
    + (Full figure, `subject_figure`) T-shirt, long trousers, shoes. The dress is turned off
- The user spec can override any preset value
    + For long hair on a man, set `hair.style` "long" and `hair.length`

## pose

| Key | Default | Range | Description |
|---|---|---|---|
| `head_center` | [0.515, 0.375] | 0-1 | Position of the point between the eyes on the picture (shares of width and height) |
| `head_unit` | 0.19 | 0.15-0.24 | Size of the head unit (share of the picture width). Larger values give a close-up |
| `yaw_deg` | 12 | 0-18 | Head turn. Above 18 the outline distorts. A small head on a 3/4 full figure allows up to 22 |
| `roll_deg` | -4 | -8-8 | Head tilt |
| `shoulder_roll_deg` | 2 | -5-5 | Shoulder tilt |
| `mirror` | false | | Flips the finished picture left to right. Use it to face the other way |
| `horizon_drop` | 0 | 0-0.1 | Lowers only this figure's eyes in a "horizon" scene placement (share of the picture height) |

## face

| Key | Default | Range | Description |
|---|---|---|---|
| `chin_y` | 1.22 | 1.10-1.40 | Eye to chin tip. Larger values look more mature |
| `cheek_width` | 0.95 | 0.90-1.00 | Cheekbone width |
| `jaw_width` | 0.73 | 0.68-0.85 | Width at the jaw corners. Smaller values give a V line |
| `jaw_height` | 0.62 | 0.55-0.70 | Height of the jaw corners (relative to `chin_y`) |
| `chin_width` | 0.11 | 0.09-0.18 | Chin tip width. Smaller is pointier |
| `jaw_sharpness` | 0.85 | 0-1 | How straight the line from the jaw corner to the chin is. 1 is straight, 0 is round cheeks |
| `ears` | false | | Draw the ears. Used with short hair |

## eyes

| Key | Default | Range | Description |
|---|---|---|---|
| `center_x` | 0.47 | 0.42-0.50 | Horizontal position of the eye centre |
| `half_width` | 0.255 | 0.20-0.28 | Eye half-width |
| `open_up`, `open_down` | 0.15, 0.10 | 0.09-0.20, 0.06-0.13 | From the eye centre to the upper and lower lids |
| `tilt` | 0.10 | 0-0.15 | Upturn of the outer corners |
| `lash_thickness` | 0.06 | 0.03-0.07 | Thickness of the upper lash line |
| `wing_length`, `wing_lift` | 0.16, 0.30 | | Length and lift of the line at the outer corner |
| `crease_gap` | 0.07 | | Gap between the double-lid crease and the lid |
| `brow_gap` | 0.37 | 0.27-0.42 | Gap between eye and brow |
| `brow_slant` | 0.75 | 0.3-1.0 | How much the brow follows the eye's tilt. High looks resolute, low looks gentle |
| `gaze_x`, `gaze_y` | -0.03, -0.035 | -0.06-0.06 | Gaze direction |
| `iris_rx`, `iris_ry` | 0.145, 0.152 | | Iris radii. About 0.6 times `open_up + open_down` looks natural |
| `pupil_ratio` | 0.48 | 0.4-0.55 | Pupil size (relative to the iris) |

## nose, mouth

| Key | Default | Description |
|---|---|---|
| `nose.tip_y` | 0.55 | Nose tip height |
| `nose.width` | 0.11 | Half-width of the nostrils |
| `nose.protrusion` | 0.26 | How far the nose stands out. How far it shifts sideways when the head turns |
| `mouth.y` | 0.84 | Mouth height |
| `mouth.half_width` | 0.215 | Mouth half-width |
| `mouth.lip_height` | 0.045 | Lip thickness |
| `mouth.smile` | 0.012 | Lift of the mouth corners. 0.03 or more is a smile. Negative values turn them down |
| `mouth.open` | 0 | Mouth opening (0-0.2). An open mouth shows its inside, the tongue and the upper teeth |

## body, outfit

| Key | Default | Description |
|---|---|---|
| `body.neck_half_width` | 0.42 | Neck half-width |
| `body.neck_pit_y` | 2.02 | Height of the hollow between the collarbones. Its difference from `chin_y` is the neck length |
| `body.shoulder_half_width` | 1.75 | Shoulder half-width |
| `body.shoulder_y` | 2.24 | Height of the shoulder points |
| `body.adams_apple` | false | Adam's apple and the neck muscle lines |
| `outfit.cut` | "boat" | "boat" (a knit with a wide neckline that bares the shoulders), "crew" (a round neck that circles the neck and covers the shoulders) |
| `outfit.necklace` | true | false leaves out the necklace |
| `outfit.neckline_half_width` | 1.36 | Width at which the neckline sits on the shoulders |
| `outfit.neckline_dip_y` | 2.62 | Lowest point of the neckline |
| `outfit.ease` | 0.06 | Ease of the garment |
| `outfit.band_width` | 0.13 | Thickness of the ribbed neckband |
| `outfit.rib_spacing` | 0.085 | Spacing of the knit's vertical ribs |

## hair

| Key | Default | Range | Description |
|---|---|---|---|
| `style` | "long" | | "long" (long hair), "short" (short hair ending above the ears and at the nape), "ponytail" (tied back and hanging down. `length` is the tail length), "bun" (a bun behind the crown). Tied hair shows the ears and is drawn in every view (front, back, side) |
| `part_x` | 0.32 | 0.1-0.45 | Position of the parting |
| `length` | 3.4 | 1.3-4.0 | Height of the hair tips. 1.5 is a bob, 2.3 the shoulder line, 3.4 the chest line |
| `volume` | 0.14 | 0.10-0.22 | Volume above the skull |
| `tip_locks` | 3 | 2-5 | Number of locks at the tips |
| `tip_split` | 0.93 | 0.85-0.95 | Where the locks start to split (share of the hair length). Smaller values give deeper splits |
| `band_y` | -0.80 | | Height of the gloss band |
| `wave`, `waves` | 0.025, 1.4 | 0-0.08, 1-3 | Width and count of the waves |
| `bangs.near`, `bangs.far` | 4, 2 | 0-6, 0-3 | Number of fringe locks on each side of the parting. 0 bares the forehead |
| `bangs.length` | 0.72 | 0.5-0.85 | Fringe length. 0.85 reaches the eyes |
| `bangs.width` | 0.14 | 0.08-0.18 | Lock thickness |
| `bangs.seed` | 3 | | Variation of lock lengths and widths |

## expression

| Name | Expression | What changes |
|---|---|---|
| `smile` | Smile | Mouth corners up, lower lids rise so the eyes curve a little, blush |
| `laugh` | Broad laugh | Open mouth with upper teeth, curved closed eyes, raised brows, deep blush |
| `sad` | Sad | Mouth corners down, brows raised at the inner ends, gaze down |
| `cry` | Crying | Sad with a slightly open mouth, red cheeks, tear tracks |
| `surprise` | Surprise | Wide-open eyes, smaller pupils, raised brows, a round open mouth |
| `angry` | Angry | Brows lowered at the inner ends, narrowed eyes, mouth corners down |
| `wink` | Wink | The near eye closed into an arc, a smile |
| `kiss` | Kiss | Both eyes closed into arcs, a faint smile, strong blush on the cheeks |

- Format: `"expression": "smile"` or `{"name": "laugh", "amount": 0.6}` (`amount` 0-1 gives an intermediate strength)
- An expression pushes the current face settings, so each style's proportions stay intact
- Values written directly in the user spec (such as `mouth.smile`) are not overwritten by the expression
- A figure in profile shows the direction of the mouth corners, an open mouth, closed eyes and tears
- Individual settings that make up an expression
    + `eyes.closed` (0-1, 1 is closed), `eyes.arch` (how much the lids curve up, smiling eyes), `eyes.brow_inner` (lift of the inner brow. Negative frowns), `eyes.brow_raise` (lift of the whole brow), `mouth.open`
    + To change one eye only, write the same keys under `eyes.near` or `eyes.far` (a wink is `eyes.near.closed` 1.0)
- Add a new expression as operations in `assets/expressions.json` (`references/extending.md`)

## look

The single key `look` changes a character's appearance. Every item is optional

| Key | Values | Description |
|---|---|---|
| `face_shape` | `oval` (default), `round`, `long`, `square`, `heart` | Face shape. Round cheeks, a long face, a square jaw, a heart shape with a slim jaw |
| `eye_shape` | `almond` (default), `big`, `narrow`, `droopy`, `cat` | Eye shape. Big eyes, narrow eyes, droopy eyes, upturned cat eyes |
| `hair_style` | `long`, `short`, `bob`, `ponytail`, `bun`, `curly` | Hair style. `bob` is a short bob, `curly` is voluminous curls |
| `hair_color` | `black`, `dark_brown`, `brown`, `blonde`, `red`, `silver` | Replaces all 5 colours of the hair palette at once |
| `eye_color` | `dark_brown`, `brown`, `hazel`, `green`, `blue`, `gray` | Replaces the 3 iris colours |
| `skin_tone` | `fair`, `light` (reference), `medium`, `tan`, `deep`, `dark` | Skin colour. The style's skin palette is moved by ratio to the reference colour, so each style keeps its colouring |
| `freckles` | 0-1 | Amount of freckles over the nose and cheeks |
| `moles` | [[x, y], ...] | Mole positions (head units, origin between the eyes). [[0.35, 0.55]] is on the picture-right cheek at nose-tip height |
| `identity` | integer or {"seed", "amount"} | Identity seed. It shifts the jaw, eyes, nose, mouth and parting slightly within set limits, so the same style yields different people |

- Presets are operations that push the current values. Values written directly in the user spec win
- The same `identity` reproduces the same face. In a scene with several figures, giving each companion a different value keeps faces from repeating
- The preset list and limits are in `assets/looks.json`

```json
{"look": {"face_shape": "round", "eye_shape": "big", "hair_style": "ponytail", "hair_color": "brown",
          "skin_tone": "tan", "freckles": 0.6, "identity": 12}, "expression": "smile"}
```

## accessories

The top-level `accessories`. Drawn on portraits and full figures (front, back, side). `true` uses the defaults

| Key | Sub-keys | Description |
|---|---|---|
| `glasses` | `shape` ("round", "square"), `color` (frame colour), `lens` (strength of the lens reflection, 0.10) | Glasses. They turn with the head. The temples go under the hair. Left out in back views |
| `hat` | `kind` ("beanie", "cap", "wide"), `pompom` (beanie pompom), `group` (palette, default `hat`) | Hat. Beanie, baseball cap (with the strap gap in back views), wide-brimmed hat (with a ribbon band). The brim throws a shadow on the face. Hair poking out above the hat line is treated as pressed down and painted out |
| `scarf` | `side` ("left", "right"), `length` (length of the hanging ends, default 2.6), `group` (default `scarf`) | Scarf. Two wraps round the neck and two hanging ends with fringes. Only the wraps in back views |
| `bag` | `side` ("left", "right"), `group` (default `bag`) | Crossbody bag. A diagonal strap from the opposite shoulder and a bag by the hip (flap and clasp). Only the strap on portraits. On the near hip in profile |
| `cigarette` | `side` ("right", "left"), `lit` (default true), `smoke` (smoke height factor, 1.0) | A cigarette at the corner of the mouth. It tilts down toward the viewer and smoke rises from the lit end. Front portraits and front full figures only |

- `side` is the picture side in the front view. A back view uses the same person's side, so it appears on the opposite side of the picture
- Colours: `hat` (with the `band` ribbon), `scarf`, `bag` in `style.palette` (defaults in `assets/accessories.json`). Glasses use `color`
- The bag and the scarf are drawn over the clothes and under the arms
- Cigarette colours are overridden with `style.palette.cigarette` (`paper`, `filter`, `ash`, `ember`, `smoke`). The defaults are `COLORS` in `scripts/smoking.py`

## style

The `style` key of a user spec overrides the style file

### Palette

| Group | Keys | Description |
|---|---|---|
| `skin` | `base`, `shadow`, `deep`, `light`, `blush` | Skin base, shadow, deep shadow, highlight, blush |
| `hair` | `base`, `shadow`, `light`, `line`, `deep` | Hair base, shadow, gloss, line, darkest strands. Brows and lashes use these colours too |
| `eye` | `white`, `white_shadow`, `iris`, `iris_dark`, `iris_light`, `pupil`, `catchlight` | White, white shade, three iris tones, pupil, catchlight |
| `lip` | `upper`, `lower`, `shine`, `line` | Upper lip, lower lip, shine, line between the lips |
| `cloth` | `base`, `shadow`, `line` | Outfit |
| `line` | `main` | Skin outline |
| `accent` | `metal`, `shine` | Necklace |
| `background` | `top`, `bottom`, `disc`, `disc_x`, `disc_y`, `disc_r`, `disc_blur`, `disc_opacity`, `mottle`, `bokeh`, `bokeh_color` | Vertical gradient, round disc, mottling, bokeh |

### Patterns (pattern)

Put `pattern` in any cloth colour group to print a pattern on that garment. The pattern follows the shading already painted and darkens in the folds

| Key | Default | Description |
|---|---|---|
| `kind` | | "stripes", "check", "dots" |
| `color` | | Pattern colour |
| `scale` | 0.35 | Repeat spacing (head units) |
| `angle` | 0 | Angle (degrees). For stripes 0 is vertical, 90 is horizontal |
| `width` | 0.35 | Share of the repeat taken by the pattern (for dots, the diameter share) |
| `opacity` | 0.9 | Pattern strength |

- Groups it applies to: the portrait knit and the full-figure dress, the shirt `cloth`, `skirt`, `pants`, `jacket`, `jeogori`, `chima`, `baji`, `drape`, `hoodie`, `swim`, and the accessories `hat`, `scarf`, `bag`
- Example: `"style": {"palette": {"skirt": {"pattern": {"kind": "check", "color": "#7A2430", "scale": 0.55, "width": 0.3}}}}`

- Move shadow colours in value and hue together
    + Skin shadows toward red and white-cloth shadows toward blue stay clean
- Keep a large value difference between the hair colour and the background colour
    + The silhouette decides the first impression of the picture

### Rendering strength

| Key | Description |
|---|---|
| `shading` | One of `cel`, `soft`, `grain` |
| `line_scale` | Line width factor. 0 leaves out the inking |
| `soft_blur` | Blur width of the shading for `soft` and `grain` |
| `grain_spread` | Transition width of the grain in `grain` |
| `hair_render` | Number of hair shadow wedges, gloss band, strand texture, number of loose hairs |
| `face_render` | Face shading threshold, blush, nose rendering, lip strength, `stubble` (beard shadow strength, 0 leaves it out) |
| `body_render` | Length of the shadow under the chin, strength of the knit ribs. For full figures see the rendering-strength table in `references/subjects.md` |
| `eye_render` | Lid shade, iris rim, brow thickness |
| `finish` | Settings of the finishing stage. For painting, `layers` (brush radii and thresholds) controls roughness and `glaze` sets the strength of the last transparent glaze |
| `base` | Name of the base style. This file is laid over that style's settings (watercolor and pencil use `illust`, manga and pixel art use `anime`) |

- Main `finish` values of the other-media styles
    + (Watercolor) `flatten` (colour pooling passes), `wobble` (edge jitter, px), `edge_gain`, `wet_edge` (edge darkening), `density`, `bloom` (blotches), `granulation` (grain), `speck` (size of bright specks to protect, px), `paper`, `paper_color`
    + (Pencil) `levels` (auto-levels percentiles), `gamma` (higher brightens the mid tones), `contrast`, `smudge` (smudged base tone), `spacing` (hatching spacing, px), `angles`, `thresholds` (darkness where each layer starts), `hatch`, `line_gain`, `paper_color`, `lead_color`
    + (Manga) `black`, `white` (brightness limits for ink and paper), `cell` (screentone spacing, px), `angle`, `line_gain`, `paper_color`, `ink_color`
    + (Pixel art) `cells` (cells across), `colors` (number of colours), `dither` (Bayer dithering strength), `edge` (brightness step that makes an outline cell), `outline` (brightness factor of outline cells)

- Rougher brushwork in painting: delete the radius-3 and radius-1.6 layers in `finish.layers`
- Finer brushwork in painting: lower each layer's `threshold`
