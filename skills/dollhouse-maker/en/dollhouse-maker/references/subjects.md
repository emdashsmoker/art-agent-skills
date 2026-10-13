# Subject modules

## Contents

- Face (head.py)
- Head and shoulders (bust.py)
- Full figure (figure.py)
- Hands and feet (extremities.py)
- Landscape (landscape.py)
- City (city.py)
- Modern objects (objects.py)
- Two-shots (pair.py)
- Perspective stage (stage.py)
- Scene templates (scenes.py)

## Face (head.py)

A frontal template (half widths by height and the features in face coordinates) is drawn first, and a turned head is drawn with three-quarter face drawing rules. No depth values or rotation math are used.

- The center line bends toward the turn and shifts (most at the forehead, nose and mouth); protruding parts such as the nose tip and the hair shift a little more
- The far half is compressed toward its edge, the near half widens slightly
- The back of the skull appears on the near side and the jaw line runs diagonally from below the ear to the chin
- A cheekbone bump is added on the far contour
- Elements behind the face, such as the ears, the neck and a bun, shift against the turn

```python
head = Head(HeadSpec(cx=480, top=170, size=560, yaw=0.2))
scene.add(head.back_parts())     # back hair: before the body
scene.add(bust.parts())          # neck and body
scene.add(head.front_parts())    # face, features, front hair: after the body
```

| HeadSpec field | Default | Meaning |
|---|---|---|
| `cx`, `top`, `size` | required | x of the head axis, y of the crown, head height in px |
| `yaw` | 0 | how far the head turns, positive to screen-right, recommended range -0.45..0.45 |
| `roll` | 0 | tilt within the picture plane |
| `jaw` | 0.85 | 0 a round jaw, 1 a sharp jaw line with a narrow chin |
| `eye_size`, `eye_open` | 1.0 | eye size factor, how open the eyes are |
| `smile` | 0.3 | lift of the mouth corners 0..1 |
| `skin`, `hair`, `iris`, `lips` | colors | skin, hair, iris, lips |
| `lip_alpha`, `blush`, `eyeshadow` | 0.6, 0.22, 0.25 | density of lip color, blush, eyelid shading |
| `hair_style` | `"long"` | 12 styles, see the "Hair styles" table below |
| `bangs` | `"parted"` | `parted` (center part), `swept` (swept to the side), `full` (straight across), `short` (short choppy locks), `side` (side part, for short hair), `none` |
| `shading` | 0.6 | face plane shading 0..1: the side plane away from the light, the eye sockets, small lights on the cheek, nose bridge and chin |
| `light_side` | -1.0 | light direction, -1 from screen-left, +1 from the right (full figures follow `FigureSpec.light_side`) |
| `face` | `"female"` | `female`, `male` (wide jaw angle, dark straight brows, nose bridge and wings, a mouth line without lip color, short lashes) |
| `hair_length` | 2.1 | where the hair ends for `long` and `wavy`, in head heights from the crown |
| `line` | 1.0 | line weight factor |
| `seed` | 0 | randomness of the hair |
| `view` | `"front"` | `front` (face toward the viewer, turned with `yaw`), `back` (back of the head), `side` (profile) |
| `facing` | 1.0 | in `side`, the screen direction the face looks to, +1 right, -1 left |
| `expression` | `"neutral"` | `neutral`, `smile`, `laugh`, `angry`, `sad`, `surprised`, `sleepy` |
| `eye_shape` | `"default"` | `default`, `droopy` (downturned eyes), `upturned`, `narrow` (narrow eyes without a double lid) |
| `face_width` | 1.0 | width factor of the whole head, recommended 0.9 (narrow face)..1.1 (broad face) |
| `brow_weight` | 1.0 | brow thickness factor |
| `age` | 0 | 0 young adult, 0.5 middle-aged, 1 elderly: nasolabial folds, under-eye bags, crow's feet, forehead lines, a softer jaw |
| `gray` | 0 | share of gray in the hair and brows 0..1 |
| `beard` | `"none"` | `none`, `stubble`, `mustache`, `goatee`, `beard` (a full beard joined to the sideburns) |
| `beard_color` | None | beard color; None uses the hair color |
| `glasses` | `"none"` | `none`, `round`, `square`, `sunglasses` |
| `glasses_color` | `"#2a2630"` | frame color |
| `freckles` | 0 | density of freckles across the nose and cheeks 0..1 |
| `mole` | None | face coordinates `(u, v)` of a beauty mark, e.g. `(0.12, 0.79)` beside the mouth |

- The defaults of the newer fields (from `expression` to `mole`) render the same picture as earlier versions
- A string outside the allowed values stops at once with a `ValueError`

### Back view and profile

- `view="back"`: only the skin of the head, both ears and the back hair are drawn; the jaw is hidden by the neck and fades out
    + With hanging hair (`long`, `bob`, `medium`, `wavy`, `curly`) the hair falls over the body, so `back_parts()` is an empty list and all the hair is in `front_parts()`
    + Tied and short hair (`updo`, `ponytail`, `twintails`, `braid`, `short`, `buzz`) draws a nape hairline (`BACK_NAPE_V`), the bun of an updo, and tails hanging behind
- `view="side"`: drawn from one profile table in `profile.py` (forehead, brow ridge, nose, lips, chin, jaw angle, back of the skull)
    + The eye is a wedge open at the front, the iris a vertical ellipse at the front of the eye; women's lashes reach forward past the eye
    + The ear sits slightly behind the middle of the head, its top at brow height
    + The lower edge from the jaw angle to the nape lies over the neck and fades out without ink
    + Hair: a cap over the skull with the side hairline, bangs hanging in front of the forehead; long hair adds side hair over the ear and back hair falling behind the back (`back_parts()`)
    + Contour numbers are in `FACE_LINE` and `BACK_LINE`, the hairline in `SIDE_HAIRLINE`, the bangs in `BANGS` (by sex and style)
- Profile local coordinates: x forward (the way the face looks), v down (crown 0, chin 1); `profile.Q(head, pts)` converts them to screen coordinates

### Expressions and looks

The same head module combines expression, eye shape, face width, age, facial hair, glasses and skin marks to make different people. Front, three-quarter and profile views all work with the same fields. Samples are in `examples/faces.py`.

| `expression` | Eyes | Brows | Mouth |
|---|---|---|---|
| `neutral` | default | default | uses the `smile` field |
| `smile` | slightly narrowed | slightly raised | corners raised |
| `laugh` | closed (an arc bulging upward) | raised | wide open mouth with upper teeth and tongue |
| `angry` | slightly narrowed | inner ends lowered and tilted, a knit between the brows | corners lowered |
| `sad` | slightly narrowed | inner ends raised and tilted | corners lowered |
| `surprised` | wide open | raised high | a round open mouth |
| `sleepy` | half closed | slightly raised | default |

- Expression numbers are in `head.EXPRESSIONS`, eye shape numbers in `head.EYE_SHAPES` (tilt, openness, double lid)
- Age: `age` handles the wrinkles and the jaw, `gray` the hair color, so old age combines `age=1.0, gray=0.9`
- Facial hair, glasses, wrinkles, freckles and moles are drawn by `face_extras.py`
    + Front and three-quarter: `marks()`, `beard()`, `glasses()`; profile: `marks_side()`, `beard_side()`, `glasses_side()`
    + Not drawn from behind
- For varied skin tones set `skin` and `FigureSpec.skin` to the same value, e.g. `"#8a5a3c"`, `"#a8724e"`, `"#d8a882"`

### Hair styles

| `hair_style` | Front and three-quarter | Back view | Profile |
|---|---|---|---|
| `long` | hair falling below the shoulders, side hair covering the ears | hair falling over the back | side hair over the ear and back hair behind the back |
| `bob` | cut straight below the chin | down to the nape | short side hair |
| `updo` | a bun on top of the head, ears showing | nape hairline and bun | bun on the back of the head |
| `ponytail` | tied back, the tail falling to one side | tail falling behind | tail falling behind |
| `short` | short hair, ears showing, sideburns | short back hair | a short cap |
| `none` | bald | bald | bald |
| `medium` | medium length touching the shoulders (`MEDIUM_LEN`) | down to the shoulders | medium side hair |
| `wavy` | long hair with wavy edges and strands (`WAVE`) | wavy long hair | wavy side hair |
| `curly` | a round cloud of curls around the head with ring patterns (`CURL_R`) | a round mass of curls | curls swelling toward the back of the head |
| `buzz` | very short hair with the scalp showing (`BUZZ_VOL`, `BUZZ_SHOW`) | a short hairline | a thin cap |
| `twintails` | two tails tied above the ears on both sides, with hair ties | tails on both sides | a tail hanging behind the ear |
| `braid` | a braid laid forward over one shoulder (V-shaped links) | a braid down the middle of the back | a braid from the back of the head down the back |

- Short styles (`short`, `buzz`) look natural with `bangs="short"`, medium length on men with `bangs="side"`
- The hair ties of twintails and braids are the fixed color `#c84a5a`

### Face coordinates (u, v)

`head.P(u, v, lift)` converts a point of the frontal template to screen coordinates on the turned face. u is horizontal from the center line, v vertical from the crown (0) to the chin (1), in head heights. Place extra details such as jewelry, marks and glasses with this function so they follow the head turn.

| Landmark | u | v |
|---|---|---|
| hairline center | 0 | 0.185 |
| brows | ±0.05..±0.30 | 0.43 |
| eye center | ±0.156 | 0.548 |
| eye width | 0.200 | - |
| top of the ear | ±0.35 | 0.49 |
| nose tip | 0 | 0.722 |
| mouth | 0 | 0.818 |
| jaw angle | ±0.26 | 0.80 |
| chin | 0 | 1.0 |

- `lift` is how far something stands out from the face (in head heights): nose tip 0.05, hair 0.045; it shifts further toward the turn
- `head.behind("ear" | "neck" | "bun", v)` gives points of elements behind the face, shifted against the turn
- The drawing rule numbers are constants at the top of `head.py` (CENTER_SHIFT, FAR_SQUEEZE, NEAR_SPREAD, SKULL_BACK, CHEEK_BUMP, BEHIND)
- `head.chin()` and `head.neck_top()` are the screen coordinates of the chin and of the start of the neck

### Face details

- Eyes: 18 iris fibers, a pink fold at the inner corner, lash clusters at the outer upper lid (5 for women)
- Face planes: a crisp shadow on the side plane away from the light (entering below the cheekbone from the temple and following the jaw line to the chin)
    + Edge coordinates in `FACE_PLANE`; density is `FACE[sex]["plane"]` times `shading`
- Hair: strand lines flowing from the crown to the hairline (`HAIR_FLOW`), flyaways at the crown, a shine band broken into locks

### Male face

- `face="male"` switches the jaw width table (`WIDTH_KEYS_MALE`) and the feature table (`FACE["male"]`) together
- Short hair (`hair_style="short"`) is drawn with a hair thickness that is thick at the crown and thin at the sides (`SHORT_VOL`)
    + Pointed tufts on the outline (`SHORT_TUFT`) and sideburns in front of the ears (`SIDEBURN_V`) are added
    + The ears are drawn over the hair and cover the edge of the short back hair
- A mature male look combines `jaw` 0.88-0.95, `eye_size` 0.85-0.9, `lip_alpha` 0.1, `blush` 0, `eyeshadow` 0

## Head and shoulders (bust.py)

```python
bust = Bust(head, BustSpec(outfit="camisole", cloth="#27354f", shoulder=1.0, turn=0.35, bust=1.0))
man = Bust(head_m, BustSpec(sex="male", outfit="tshirt", cloth="#33404c", turn=-0.35))
```

| BustSpec field | Meaning |
|---|---|
| `outfit` | `camisole`, `tshirt`, `offshoulder`, `bare` |
| `cloth` | clothing color |
| `shoulder` | shoulder width factor |
| `turn` | body direction -1..1, foreshortens the far shoulder |
| `bust` | chest volume factor (women only) |
| `sex` | `female`, `male` (steep trapezius, broad shoulders, thicker neck and arms, Adam's apple, flat chest) |
| `view` | `front`, `back` (the spine and trapezius edges at the nape instead of collarbones and Adam's apple; clothes with a back neckline) |

- The vertical coordinate continues the head's v scale (chin 1.0, pit of the neck 1.34, shoulder tip 1.41)
- `bust.B(x, v)` converts body coordinates to screen coordinates, for necklaces or clothing patterns
- A back-view portrait combines `HeadSpec(view="back")` and `BustSpec(view="back", turn=0)`; the example is `build_back()` in `examples/portrait.py`
    + Back neckline cuts are in `BACK_EDGES` and `BACK_EDGES_MALE`
- A new garment adds the right-half coordinates of its top edge (`edge`) and side seam (`seam`) to `OUTFITS`
    + Cuts fitted to the male trunk go into `OUTFITS_MALE`; without one, the shared table is stretched to the male width

## Full figure (figure.py)

The drawing order of an illustrator, implemented in 2D. Women and men go through the same procedure; only the proportion table (`BODY`) differs. A joint skeleton sets the pose, the trunk is drawn as one outline joining anatomical landmarks (neck, shoulders, armpits, side of the chest, waist, pelvis, crotch), and the limbs are drawn along the bones with different curves on each side. All skin shapes are inked as one surface, so no lines appear at the joints. The unit is the head height (hu) and the base proportion is 8 heads.

```python
figure = Figure(FigureSpec(cx=448, top=70, unit=180, skin="#eec6ab", outfit="nude",
                           bust=1.08, waist=0.95, hip=1.02,
                           head=dict(hair_style="long", bangs="swept")), pose="contrapposto")
scene.add(figure.parts())        # all shapes, sorted back to front
man = Figure(FigureSpec(cx=448, top=70, unit=180, sex="male", skin="#dcae8c", outfit="nude"), pose="heroic")
```

| Guide line | hu from the crown |
|---|---|
| chin | 1.0 |
| pit of the neck | 1.34 |
| shoulder joint | 1.64 |
| chest apex | 2.05 |
| waist | 2.75 |
| navel | 3.05 |
| hip joint | 3.83 |
| crotch | 4.15 |
| knee | 5.80 |
| ankle | 7.60 |
| ground | 8.0 |

| FigureSpec field | Meaning |
|---|---|
| `cx`, `top`, `unit` | x of the pelvis center, y of the crown in the neutral pose, px per head height |
| `sex` | `female`, `male`; switches the proportion table, the face defaults and the outfit list together |
| `skin` | skin color |
| `shoulder`, `waist`, `hip`, `bust`, `limb` | factors for shoulder, waist and hip width, chest size (pectorals for men), limb thickness |
| `legs` | leg length factor; about 1.05 gives fashion illustration proportions |
| `gloss` | soft sheen on the shoulders, chest, pelvis and limbs 0..1 |
| `blush` | redness at the knees, elbows and shoulders 0..1 |
| `modeling` | form shading on the sides of the trunk, beside the abdomen, under the chest and on the inner thighs 0..1 |
| `light_side` | light direction of the scene, -1 left, +1 right (match the sign of x in `Scene.light`) |
| `outfit`, `cloth` | one outfit and its color; women `nude`, `bikini`, `onepiece`, `highleg`, `slip`, `dressed`; men `nude`, `briefs`, `trunks`, `open_shirt`, `dressed` |
| `cloth2` | color of the shorts under an open shirt, or of the bottoms with `dressed`; None is a darker `cloth` |
| `upper`, `lower` | for `dressed`, the top `tee`, `longsleeve`, `shirt`, `blouse` and the bottoms `jeans`, `slacks`, `skirt`, `long_skirt` |
| `shoes`, `cloth3` | shoes for every outfit, `sneakers`, `boots`, `heels` (None is barefoot), and their color |
| `left_item`, `right_item` | an object held in a `grip` hand: `phone`, `mug`, `book`, `umbrella`, `clear_umbrella` |
| `ident` | a short identifier telling several people in one scene apart; prefixes every shape name and key with `ident/` |
| `head` | dict of extra fields passed to `HeadSpec` |
| `line`, `detail` | line weight factor, whether to show details such as the navel and collarbones |
| `form` | roundness factor of the skin forms; 1.5-1.8 turns the forms strongly, like a side-lit oil study |

- To stress curves combine `waist` 0.92-0.97, `bust` 1.05-1.15, `legs` 1.03-1.07
    + In three-quarter view the waist line is drawn automatically, hollow on the near side and filling out on the far side
- Sheen and shading are laid as separate shapes, so they apply in every style; 0 turns them off
- A mature face combines `head=dict(eye_size=0.92, jaw=0.95, lip_alpha=0.75, eyeshadow=0.35)`
- A slim build combines `hip` 0.95, `bust` 0.9, `limb` 0.95
- With `detail=True`, anatomical landmarks are drawn with lines in the skin's shadow color
    + Shared: the pit between the collarbones, the end of the deltoid, the crease inside the elbow, the inner muscle above the knee, the inner and outer ankle bones
    + Men also: serratus teeth, abdominal segments, the iliac V line
    + Adjust the strength in `LANDMARK[sex]`
- Each limb bone gets a sheen band on the light side and a form shadow band on the other side (`gloss`, `modeling`)

### Male build

| Item | Female | Male |
|---|---|---|
| shoulder joint x (rib cage coordinates) | 0.665 | 0.86 |
| waist half width | 0.45 | 0.615 |
| widest pelvis half width | 0.88 | 0.695 |
| upper arm, forearm, hand length (hu) | 1.40, 1.12, 0.72 | 1.45, 1.15, 0.76 |
| chest | breasts (teardrop) | pectorals (only the lower line inked, a straight line rising to the armpit) |
| abdomen | one center line | linea alba, 3 rows of tendinous intersections, outer line of the rectus, iliac V line |
| hand width, foot size | 1.0, 1.0 | 1.12, 1.08 |

- Adjust the numbers in the `BODY["male"]` dict of `figure.py`
- The groin is drawn as the same smooth form as for women (the module has no genital forms)

### Outfits

| outfit | Form | Construction |
|---|---|---|
| `bikini` | triangle cups, halter strap, under-bust strap, briefs | laid on the body and cut to the trunk and chest areas |
| `onepiece` | scoop neck, shoulder straps, leg cut at hip height | a body-hugging outfit: cut inside the skin shapes so it follows the body outline exactly |
| `highleg` | deep V neck, leg cut up to the hip bones | same as `onepiece` |
| `slip` | thin straps, sweetheart neck, straight hem at mid thigh | an independent silhouette: skims the waist and falls along the outer lines of the pelvis and thighs |

- Outfits are drawn under the arms and hands in front, so a hand on the hip rests over the clothes
- The chest is inflated separately inside the fabric and gets its own sheen and shadow
- Fabric sheen (long side sheen, a reflected light on the chest) follows `gloss`; `slip` gets it stronger, like satin
- A new outfit adds neckline and leg cut coordinates to `SUITS` (body-hugging outfits), or draws an independent silhouette modeled on `_slip`

| Male outfit | Form | Construction |
|---|---|---|
| `briefs` | low-rise swim briefs, a waistband line | cut to the trunk and thigh areas |
| `trunks` | drawstring swim shorts, hem at mid thigh | an independent silhouette joining one hip band and two leg tubes; only the outline of the union is inked |
| `open_shirt` | a shirt open in front, sleeves rolled to the elbow, with `trunks` underneath | two panels over the trunk; the sleeves are stacked right over the upper arms and follow the arms' front-back order |

- Shorts in a sitting pose are cut at the top of the seat

### Everyday clothes (garments.py, outfit="dressed")

Clothes are cut from the actual body form. The trunk outline is grown by the ease and cut into a band between the neckline and the hem, and sleeves and trouser legs are tubes laid along the bones (joint position L: 0 root, 1 elbow or knee, 2 wrist or ankle). The same code applies as it is to front, three-quarter, back and profile views and to sitting and lying poses.

| Top | Neckline | Sleeve end L | Hem | Details |
|---|---|---|---|---|
| `tee` | crew | 0.48 (short sleeve) | above the hips, worn over the bottoms | neckband, no elbow |
| `longsleeve` | crew | 1.93 (wrist) | above the hips | neckband, crease inside the elbow |
| `shirt` | collar | 1.88 | over the bottoms | two pointed collar pieces, button placket, cuffs |
| `blouse` | V neck | 1.86 | tucked into the bottoms | folds running from the shoulders to the waist, cuffs |

| Bottoms | Waist | End L | Form | Details |
|---|---|---|---|---|
| `jeans` | hips | 1.93 | tubes fitted to the legs | waistband, front fly line, front pockets, inseams, yellow stitching, folds behind the knees |
| `slacks` | waist | 1.95 | straight below the knee | waistband, fly line, pockets, knee folds |
| `skirt` | waist | 0.86 (above the knee) | flaring toward the hem | cloth spanning between the legs, folds running from the waist to the hem |
| `long_skirt` | waist | 1.80 (above the ankle) | flaring widely | same |

- The chest swells as a separate volume under the clothes and gets sheen and shadow
- Sleeves are stacked with the arms and follow their front-back order; the trunk piece is drawn under the arms in front
- Back view: a high back neckline, a shirt yoke with a box pleat and back collar, blouse back seams, a jeans yoke and back pockets, slacks welt pockets, a skirt zipper and hem slit
- Profile: side seams, a neckline running from the front of the neck to the back (`SIDE_NECKLINES`), slanted front pockets, outer seams; the far trouser leg is a separate, darker shape
- Adjust the cut numbers in `TOP_CUT`, `BOTTOM_CUT` and `NECKLINES` of `garments.py`; a new garment adds one row to the table

| Shoes | Form | Front, side, back |
|---|---|---|
| `sneakers` | white rubber sole, laces, heel counter and pull tab | all 3 |
| `boots` | a shaft above the ankle, a heel | all 3 |
| `heels` | pumps that show the instep, a thin heel, the foot tilted onto the toes and lengthened | all 3 |

- The sole depth of the shoes (`SHOES[...]["sole_y"]`) is reflected in `figure.ground_y()`

### Poses

`pose` is a preset name or a `FigurePose` object. Front and three-quarter presets are `pinup`, `contrapposto`, `arms_up`, `seated`, `reclining`, `akimbo`, `heroic`, `standing`, `phone`, `coffee`, `point`, `desk`; profile presets are `side_stand`, `walk`, `side_seated`, `side_phone`. For a back view, change only the view of any preset, as in `dataclasses.replace(POSES["akimbo"], view="back")`. All presets apply to women and men alike. Angles are in degrees: 0 is straight down, positive is toward screen-right. Left and right are always from the viewer's side.

| FigurePose field | Meaning |
|---|---|
| `view` | `front`, `back` (back view), `side` (profile) |
| `facing` | in `side`, the screen direction the body faces, +1 right, -1 left |
| `turn` | amount of three-quarter view -1..1, positive faces screen-right, recommended range -0.7..0.7 |
| `lean` | angle tilting the trunk and head about the pelvis center; limb angles are screen angles and set separately |
| `seated` | True adds a buttock mass pressed on a seat below the pelvis |
| `pelvis_tilt` | pelvis tilt, positive lowers the right hip (weight on the left leg) |
| `chest_tilt` | shoulder line tilt, natural with the opposite sign to the pelvis |
| `spine_shift` | sideways shift of the rib cage center (hu) |
| `head_tilt`, `head_yaw` | head tilt and turn |
| `left_thigh`, `left_shin`, `right_thigh`, `right_shin` | directions of thighs and shins |
| `left_leg_scale`, `right_leg_scale` | (thigh, shin) foreshortening ratios, 1 is the full length |
| `left_upper_arm`, `left_forearm`, `right_upper_arm`, `right_forearm` | directions of upper arms and forearms; an absolute value over 90 is a raised arm |
| `left_arm_scale`, `right_arm_scale` | (upper arm, forearm) foreshortening ratios |
| `left_arm_front`, `right_arm_front` | True in front of the trunk, False behind it, None puts the far arm behind automatically |
| `left_hand`, `right_hand` | `relaxed`, `open`, `hidden`, `fist`, `point` (pointing with the index finger), `grip` (holding something, shows `*_item`) |
| `left_wrist`, `right_wrist` | wrist bend angle, turns the hand further from the forearm direction, positive toward screen-right |
| `left_foot_turn`, `right_foot_turn` | toe-out angle; 40 or more draws the foot seen from the side |
| `left_foot_pitch`, `right_foot_pitch` | foot tilt in profile, positive lifts the toes (heel strike), negative points them down |

- `pinup` pushes the pelvis out over the supporting leg, one hand in the hair and one on the hip
- `akimbo` has both hands on the hips with the elbows out; the wrists bend so the hands come down onto the pelvis
- `heroic` is a classical standing pose on the right leg with the left leg set out
- `seated` sits on a box with the knees drawn together to the right; the prop height is `figure.seat_y()`
    + Thighs are foreshortened with `*_leg_scale`, and a bent leg draws the thigh in front so its rounded end is the knee
    + A front-facing seated pose (`desk`) with a thigh foreshortening ratio below `FORESHORTENED_THIGH` (0.6) is also split into two shapes to draw the knee, even when the thigh lines up with the shin
    + A thigh pointing at the viewer keeps its mid girth (`THIGH_GIRTH_T`) down to the knee; trousers and skirts get a knee edge line and shade below it (`garments.KNEE_*`)
- `reclining` lies on the side propped on the left elbow; the floor height is `figure.rest_y()`
    + Changing `lean` lifts the elbow off the floor, so adjust it together with `left_upper_arm`
    + The screen placement of a lying pose is computed as `top = pelvis height - 3.85 * unit`
- `phone` looks down at a phone held in the near hand, `coffee` holds a mug in front of the chest, `point` has one hand on the hip and points to the side
- `desk` sits facing the viewer at a desk with the forearms on the desk; the desk goes between the body and the arms in front with `figure.parts(inserts=[...], overlays=[...])`
    + `inserts` are shapes drawn behind the arms in front and over the body (a desk), `overlays` are shapes drawn over the arms in front and behind the face (a laptop lid)
    + The example is `study()` in `examples/desk.py`
- Three-quarter views are drawn by drawing rules without rotation math
    + The far half of the body narrows, the near half widens slightly, the far breast projects past the outline, a buttock curve is added over the near thigh, and the far arm goes behind the trunk
- Contrapposto gives `pelvis_tilt` and `chest_tilt` opposite signs and `spine_shift` toward the supporting leg
- Limbs coming toward or going away from the camera are foreshortened by shortening them with `*_scale`
- A limb bent more than 65 degrees is split into two shapes drawn overlapping
- A hand raised behind the head set to `hidden` is treated as hidden by the head
    + The forearm of a raised arm is drawn on toward the middle of the skull by `HIDDEN_REACH` (0.5) so its end goes behind the head (not in back views)
- `figure.joint("wrist_left")` and the like give the screen coordinates of joints, for placing props
- `figure.ground_y()` is the height of the soles, for placing floor shadows
- `figure.seat_y()` is the top of the seat in a sitting pose, `figure.rest_y()` the lowest point of the trunk (the floor of a lying pose)
- Contour numbers are constants at the top of `figure.py` (CHEST, WAIST, PELVIS, THIGH_W, BREAST and others) and the `BODY` dict

### Back views and profiles

Back views and profiles are also drawn by drawing rules without rotation math.

- Back view (`view="back"`): dorsal anatomy landmarks are drawn over the same outline as the front
    + The spine line, the inner edges and lower tips of the shoulder blades, the erectors beside the spine, two dimples above the pelvis, the cleft of the buttocks, the folds below the buttocks
    + The creases behind the knees, the inner head of the calf, the point of the elbow; hands are mirrored to show their backs
    + Chest, collarbones and Adam's apple are left out; sheen on the shoulder blades and buttocks
    + An arm wrapped in front (`*_arm_front=True`) goes behind the trunk in a back view
    + A bikini gets a back band and a bow at the nape, a one-piece a low back, shorts a seat seam, an open shirt a closed back panel (yoke, box pleat)
- Profile (`view="side"`, `side.py`): the frame's x turns into the body's front-back direction, + is the front of the body
    + The trunk is one side contour joining the neck, chest, the hollow of the lower back, the belly and the buttocks (`SIDE_TRUNK`, depth factor `SIDE_DEPTH`)
    + A woman's breast is one teardrop growing from the front of the chest; a man's pectorals are part of the contour
    + Both legs start from one hip joint in the middle of the pelvis depth and both arms from one shoulder; the far limbs are drawn first and slightly darker
    + The leg width table differs in front (kneecap) and behind (calf) (`SIDE_LEG`); feet are in profile, hands are side-on with the thumb forward
    + `right_*` are the near limbs, `left_*` the far limbs; a positive angle reaches forward
    + The head is a profile, with the skull center over the neck set forward of the neck (`SIDE_HEAD_FORWARD`)
    + Every outfit (swimwear, slip, shorts, open shirt, everyday clothes) has a profile cut
- `walk` is mid stride, the near leg stepping forward and the far leg pushing off behind; the arms swing against the legs
    + `figure.walk(phase, stride, facing, arms)` makes a pose for any point of the stride
    + `phase` 0 is the near foot landing, 0.25 the legs passing each other, 0.5 the far foot landing
    + `stride` 0.6 is a stroll, 1.0 a normal walk, 1.3 a brisk walk; `arms` scales the arm swing
    + In a crowd give each person a different `phase` and `stride`; the example is `crosswalk()` in `examples/variety.py`
- `side_seated` sits upright on a chair with the hands on the thighs; the chair is `objects.side_chair(front edge x, figure.seat_y(), figure.ground_y(), unit, facing, depth)`
- A character sheet with front, three-quarter, profile and back on one page is `turnaround()` in `examples/figure.py`

## Hands and feet (extremities.py)

Fingers have three segments (the thumb two) placed in anatomical length ratios. The number and proportions of fingers and toes are fixed by the structure.

```python
Hand(HandSpec(x, y, length=400, angle=0.0, mirror=False, spread=0.35,
              curl=(0.1, 0.15, 0.2, 0.25, 0.3), forearm=True)).parts()
Foot(FootSpec(x, y, unit=520, angle=0.0, mirror=False, view="front")).parts()
```

| HandSpec field | Meaning |
|---|---|
| `x`, `y` | wrist position |
| `length` | px from the wrist to the tip of the middle finger |
| `angle` | 0 has the fingertips pointing down the screen, `np.pi` up |
| `mirror` | False puts the thumb of a downward hand on screen-left |
| `spread` | finger spread 0..1 |
| `curl` | bend of (thumb, index, middle, ring, little) 0..1 |
| `nails`, `forearm`, `open_wrist` | show nails, add a forearm, leave out the wrist line |
| `breadth` | width factor of palm and fingers; men's hands 1.12 |
| `shape` | `natural` (bent segments), `fist`, `point` (a fist with the index finger out), `grip` (wrapped around an object) |

- Bending in `natural` is shown by foreshortening the segment lengths
- `fist`, `point` and `grip` are built as form constructions
    + The mass of the back of the hand, the row of the last segments of four folded fingers, and the thumb wrapping over the fingers are stacked in turn
    + `point` straightens only the index finger and draws it over the back of the hand
    + `grip` draws the object first at the point `(0, 0.56)` on the palm side (in hand lengths), then the fingers wrap over it
- Held objects are `phone`, `mug`, `book`, `umbrella`, `clear_umbrella` in `held.py`, sized in the person's head height units (`held.ITEMS[name](grip_point, unit, name)`)
    + An umbrella is a handle hook below the fist, a straight shaft up from the fist and a dome canopy over the head (numbers in `held.UMBRELLA`)
    + The canopy outline is the dome's side contour, its lower rim the lower half of a flat ellipse, and the visible ribs are the side contour narrowed by the cosine of each rib angle
    + `clear_umbrella` is a translucent vinyl canopy that shows the background through it
    + Raising the forearm (`*_forearm` 170-180) to bring the fist beside the face lets the shaft pass clear of the head
- The gesture example is `gestures()` in `examples/hands.py`
- Feet come in 3 views, `view="front"`, `view="side"` (profile) and `view="back"` (heel); `unit` is the head height px of the owner
    + Put shoes on with `FootSpec.shoe` and `shoe_color`
    + `FootSpec.scale` is the foot size factor; men's feet 1.08
    + `mirror=False` puts the big toe and the toes on screen-left

## Landscape (landscape.py)

A landscape is depth layers stacked back to front. Farther layers are lighter and bluer with smoother ridges, with mist below each layer.

```python
img = build_landscape(LandscapeSpec(width=1280, height=896, seed=3))
save(finish(img, "painterly", seed=1), "lake.png")
```

| LandscapeSpec field | Meaning |
|---|---|
| `horizon` | horizon height as a share |
| `sky` | sky gradient `[(y share, color), ...]` |
| `sun`, `sun_color` | sun position (x, y) as shares; None is no sun |
| `haze`, `far`, `near` | haze color, color of the farthest ridge, color of the nearest ridge |
| `ridges`, `peaks` | number of ridges, sharpness of peaks 0..1 |
| `cloud_cover` | amount of cloud 0..1 |
| `lake`, `trees`, `grass_color` | show a lake and trees, grass color |

For another layout, combine the part functions below directly.

| Function | Use |
|---|---|
| `sky(h, w, stops, sun, sun_color, sun_size, glow)` | sky and sun |
| `clouds(img, coverage, y_range, color, shadow, scale, seed)` | clouds |
| `ridge_line(width, base, amplitude, roughness, seed, scale, peaks)` | array of ridge heights |
| `ridge_layer(img, ridge, color, mist_color, mist, texture, slope_light)` | fills below a ridge |
| `water(img, y0, reflect_strength, tint, ripple, sparkle, sun_x)` | water reflections and glitter |
| `conifer(img, x, base_y, height, color)`, `tree_line(img, ridge, color, density, size)` | conifers |
| `grass(img, y0, color, blade, count)` | foreground grass |

## City (city.py)

A one-point-perspective street. Building fronts and the road surface are drawn first as flat plans, then projected onto quads receding to the vanishing point. One sun direction and the sky's ambient light keep the sunny-side buildings, the shady-side buildings and the shadows on the road consistent. Signs, street trees, street lamps, cars, pedestrians and utility poles are sorted by distance and drawn from the farthest. Distances are in meters.

```python
img = build_city(CitySpec(width=1280, height=896, time="day", seed=2))
save(finish(img, "anime"), "street.png")
```

| CitySpec field | Meaning |
|---|---|
| `horizon`, `vanish_x` | horizon height and horizontal vanishing point position as shares |
| `focal` | focal length relative to the width; smaller is wider |
| `eye_height` | eye height in m |
| `road_half`, `sidewalk` | half width of the roadway and width of the sidewalk in m |
| `time` | `day`, `golden`, `dusk`, `night` |
| `sky`, `lit` | set the sky colors and the share of lit windows directly |
| `wet_road` | reflection strength of a wet road; 0 is a dry road |
| `signs`, `trees`, `cars`, `people` | density factor per element; 0 removes it |
| `wires` | show utility poles and wires |
| `depth` | length of the street in m |

- There are 4 building types, masonry walls, glass curtain walls, balconies and ribbon windows, placed by `seed`
- A rainy evening combines `time="dusk", wet_road=0.55`, a clear day `time="day"`
- `City(spec).build()` returns (picture, glow map), for applying bloom to the glow map directly
- `City.P(x, y, z)` converts a point in street space to screen coordinates, for placing people or props in perspective
- `City.px_per_m(z)` is pixels per meter at distance z, for computing the `unit` of a foreground person

## Modern objects (objects.py)

Drawn as oblique-projection boxes. The front keeps its true shape, depth is a parallel shift in a fixed oblique direction. No vanishing point, rotation or depth values are used. The unit is 10 cm; x is right, y up, z into the screen; the desk top is y = 0.

```python
from codepaint.subjects import objects as ob
desk = ob.Desk(x=800, y=800, unit=62, depth=(0.30, -0.42))
parts = ob.plant(desk, 7.6, 5.4) + ob.monitor(desk, -1.6, 3.4, glow=0.3) + ob.mug(desk, -5.6, 0.0)
scene.add(parts)                 # add from the back (objects with larger z) to the front
```

| Desk argument | Meaning |
|---|---|
| `x`, `y` | screen position of the desk top origin (0, 0, 0) |
| `unit` | px per 10 cm |
| `depth` | screen shift per unit of depth; positive x shows the right side faces, negative the left side faces |
| `light` | direction toward the light in object space, default upper left front |

| Group | Functions | Main arguments |
|---|---|---|
| Computers | `laptop`, `monitor`, `keyboard`, `mouse` | `screen_kind` (`desktop`, `code`, `video`, `off`), `open_deg`, `glow`, `width`, `color` |
| Handheld devices | `smartphone`, `tablet`, `headphones`, `camera` | `upright` (a phone stood up), `screen_kind` (including `home`), `cushion`, `trim` |
| Desk items | `mug`, `desk_lamp`, `plant`, `books` | `drink`, `steam`, `light` (a pool of lamp light), `pot`, `leaf`, `colors` |
| Home appliances | `tv`, `speaker`, `gamepad` | `screen_kind`, `glow`, `grille`, `accent` |
| Furniture | `chair`, `side_chair` | `seat_h`, `frame` (office chair), `depth`, `facing` (a chair seen from the side) |

- `laptop(..., facing="away")` draws the back of the lid and the logo instead of the screen, for placing in front of a person sitting across the desk
- `side_chair` is drawn as an exact side view without oblique projection, its back rest standing behind the sitter

- Every object function takes the position `(desk, x, z)`, x being the object's center and z its front edge
- Face colors follow the light and the face direction: the top is lightest, the front middle, the side away from the light darkest
- Cylinders (mugs, pots, lamp bases) are drawn with ellipses whose minor axis lies on the cylinder axis, the side swept from light to shadow
- Keys, buttons and screen content are placed in the coordinates of the face they lie on and follow its oblique
- Each object automatically gets a soft contact shadow on the desk pushed away from the light
- Assemble new objects with `screen()` for screen content, `box()` for boxes and `cylinder()` for cylinders
- The scene example is `build()` in `examples/desk.py`; the list of 15 is `catalog()`

## Two-shots (pair.py)

Four composition functions for putting two people in one scene. a stands on the left and b on the right; each gets an `ident` so their shapes do not mix. Arms that touch are solved with two-joint inverse kinematics (`reach`) so the hand lands on its target point.

```python
from codepaint.subjects import pair
two = pair.holding_hands(her_spec, his_spec, cx=700, gap=2.1, front="b")
scene.add(two.parts)             # back to front; two.a and two.b are Figures
```

| Function | Composition | Construction |
|---|---|---|
| `side_by_side(a, b, cx, gap=1.6, front="b")` | two people shoulder to shoulder, turned slightly toward each other | the front person (`front`) is drawn later |
| `holding_hands(a, b, cx, gap=2.1, front="b")` | holding hands | the hands meet at a midpoint below the pelvis; the front person's hand wraps the other's with `grip` |
| `arm_over_shoulder(a, b, cx, gap=1.35)` | an arm over the shoulder | a's forearm lies along b's shoulder line behind the neck and the hand rests on b's far shoulder; only the hand moves to b's `overlays` |
| `conversation(a, b, cx, gap=3.6)` | talking face to face in three-quarter view | a listens holding a mug, b talks with an open hand |

- `cx` is the screen x of the center between the two, `gap` the distance between the two pelvis centers (hu)
- Match the `unit` and `top` of both specs before calling
    + Show a height difference with `top`; for a man 0.3-0.5 of a head height higher looks natural
    + In a perspective scene match them to the same depth with `Camera.fit()`
- `reach(figure, side, target, elbow)` returns the (upper arm, forearm) angles that put the wrist on a target screen point
    + `elbow="out"` bends away from the body; `"up"` and `"down"` pick the higher or lower elbow
- `mirrored(pose)` is the pose with left and right swapped, for flipping one pose when two people face each other
- For three or more people give each a different `FigureSpec.ident` and `scene.add` them from the person standing farthest back
- Hand parts carry the tags `hand_left` and `hand_right`, so they can be moved into another person's drawing order

## Perspective stage (stage.py)

A one-point-perspective construction frame. The front faces of boxes are true shape parallel to the picture plane and depth edges converge on one vanishing point on the horizon. Units are meters; x is right of the line of sight, y up from the floor, z depth into the screen.

```python
from codepaint.subjects import stage as st
cam = st.Camera(1500, 1000, eye=1.3)                  # eye height 1.3 m, horizon at 0.42 of the picture height
room = st.Room(cam, width=6.4, depth=7.5, floor_kind="planks")
scene.add(room.parts(), room.window(-2.6, -0.4, 0.9, 2.3), st.sofa(cam, "sofa", 0.0, 6.0))
spec = cam.fit(spec, "standing", x=-0.6, z=4.0)        # size and position of a person standing at 4 m depth
```

| Camera field or method | Meaning |
|---|---|
| `horizon`, `vp_x` | screen y of the horizon (eye level), screen x of the vanishing point |
| `focal` | px covered by 1 m at 1 m distance; the default is a 58 degree horizontal angle of view, larger is telephoto |
| `eye` | eye height (m): 1.5 for a standing viewpoint, 1.2 for a seated one |
| `P(x, y, z)` | screen coordinates of a stage point |
| `scale(z)`, `unit_at(z)` | px per m at depth z, a person's head height in px (head 0.215 m) |
| `floor_y(z)`, `near_z()` | screen y of the floor at depth z, the depth where the floor leaves the bottom of the picture |
| `fit(spec, pose, x, z, seat=None, lie=None)` | fits a person's size and position to depth z; with `seat` (m) they sit on a seat of that height, with `lie` (m) a lying pose (`reclining`) rests on a surface of that height |

| Part | Functions |
|---|---|
| Room | `Room(cam, width, depth, height, wall, back, floor, ceiling, floor_kind)`, `.parts()`, `.window(...)`, `.picture(...)` |
| Box | `box(cam, name, x0, y0, z0, w, h, d, color)`: only the visible faces, back to front, top lighter, sides darker |
| Furniture | `table` (rectangular, `round_top` round), `chair` (`facing="away"` a chair seen from the front, `"toward"` seen from behind), `sofa`, `shelf`, `rug`, `plant`, `floor_lamp`, `pendant`, `blackboard` |
| Outdoors | `Ground(cam)` (sky, lawn, a path running to the vanishing point), `.treeline()`, `tree`, `bench`, `lamp_post` |
| Weather | `rain(width, height, count, length, angle, color, alpha, seed)`: rain streaks over the whole picture, nearer drops longer, thicker and brighter; `splashes(cam, x_range, z_range, count)`: rings of raindrops on a wet floor |
| Shadows and reflections | `contact(cam, name, x, z, w, d)`, `figure_shadow(cam, figure, z)`, `reflection(parts, ground_y, color, alpha, blur, squash)`: a soft silhouette of shapes mirrored in a wet floor, added before the shapes it reflects |
| Depth and light marks | `placed(parts, depth)`: records the sorting depth on the shapes of one piece of furniture; `lit(parts)`: tags shapes that give light (lamp shades, bulbs, glows) with `light` |

- A box shows its left side when it is right of the line of sight and its top when it is below eye level, chosen automatically
- The position arguments of furniture functions are (center x, front edge z)
- Furniture functions record a sorting depth (`Part.depth`) on all their shapes
    + Furniture people stand behind (tables, boxes, shelves) takes the depth of its front edge
    + Furniture people sit on (chairs, sofas, benches) takes a depth `SIT_SHARE` (0.6) of its depth behind its front edge
    + Things flat on the floor (rugs, floor shadows) take `FLOOR` and stay under every person
    + An object standing on another piece (a monitor on a desk) takes the same depth as its support with `placed`
- Floor planks and tile joints are drawn with lines converging on the vanishing point and horizontal lines by depth
- Furniture in front of a person (a table in front of them) is added after the person; a desk the person leans on goes between the body and the arms with `Figure.parts(inserts=...)`

## Scene templates (scenes.py)

| Function | Place | Spots for people (`spots`) | Contents |
|---|---|---|---|
| `cafe(w, h)` | cafe | `left_seat`, `right_seat` (sitting face to face in profile) | brick back wall, a window onto the street, a counter and menu board, pendant lights, a round table in front (`front`) |
| `classroom(w, h)` | classroom | `seat_a`, `seat_b` (sitting facing the viewer) | lockers, a notice board, a clock, windows in the left wall, rows of empty desks, desks for the two spots (`inserts`) |
| `living_room(w, h)` | living room | `sofa_left`, `sofa_right` | sofa, rug, coffee table in front (`front`), window, picture, bookcase, floor lamp, plant |
| `park(w, h)` | park | `path` | sky, a distant line of trees, lawn, path, trees, bench, lamp post, a near tree (`front`) |
| `office(w, h)` | high-rise office | `desk_seat` (sitting facing the viewer), `stand` | a long window onto city towers, ceiling light panels, rows of desks with monitors and partitions, a plant, a cabinet, a near desk (`inserts`) and a laptop lid (`overlays`) |
| `bedroom(w, h)` | morning bedroom | `bed_edge` (sitting on the front edge of the bed) | a back wall window with curtains, a patch of sunlight on the floor, a double bed with headboard, duvet and pillows, two nightstands with a lamp, a picture, a rug |
| `rooftop(w, h)` | sunset rooftop | `rail` (standing at the rail) | sunset sky and low sun (`image`), three layers of backlit distant city silhouettes, concrete floor, parapet with a rail, string lights, a water tank, air-conditioning units |
| `street(spec, rain)` | city street (`CitySpec` time of day) | `road` (middle of the near road) | the `city.py` street picture (`image`) with the same camera; `rain=True` adds rain streaks and raindrop rings (`front`) |
| `rainy_street(w, h)` | rainy street at night | `road` | night, wet road reflections, more signs, rain |
| `beach(w, h)` | beach | `shore` | sky and clouds, a band of sea with a surf line, sand (`image`), a parasol, a towel |

- The return value `Set`: `cam`, `back` (behind people), `front` (in front of people), `spots` (by name, (x, z, seat height or None)), `inserts` (shapes between body and arms, by spot), `overlays` (shapes between arms and face, by spot), `image` (the background picture of an open-air place, or None)
- Drawing order: `image` (with `Scene.set_background`, if present), `back`, people (the farthest first), `front`
- `street()` copies the camera numbers of the street picture (`horizon`, `vanish_x`, `focal`, `eye_height`) to the stage camera, so people placed with `cam.fit` stand on its road
    + A low angle is set as in `CitySpec(eye_height=0.5, horizon=0.62)`, and the road fills the picture down to its bottom edge (`GROUND_FILL`)
- Every template except `street()` and `rainy_street()` takes camera keywords (`horizon` px, `eye` m, `focal` px, `vp_x` px)
    + Example: `scenes.cafe(1500, 1000, eye=1.55, horizon=300)` is a close shot at a standing person's eye height
    + Furniture and walls are laid out again through the changed camera, and the stage coordinates of `spots` stay valid
- `Set.arrange((z, parts), ...)` returns a drawing list with the people slotted in among the furniture in depth order
    + Shapes without a depth, such as walls, floors, windows and things on the walls, and floor shapes are drawn first
    + Furniture and people follow from the farthest to the nearest; at the same depth people come after the furniture
    + Usage: `scene.add(s.arrange((z1, fig1.parts()), (z2, [shadow, *fig2.parts()])), s.front)`
    + A person standing between rows of desks has their legs hidden by the desks and chairs in front
- `Set.night(room, people, lamps, tint)` returns the same place at night as a new `Set`
    + Every color moves toward the night color (`NIGHT_TINT`) by the `room` share; window glass becomes night sky and the view outside goes darker still
    + Patches of sunlight (tag `daylight`) are removed; lamps, bulbs and ceiling light panels (tag `light`) keep their brightness, and their glows grow `lamps` times
    + A light night veil over everything including people (`people`) and the glows over it are added at the start of `front`
    + For streets use `CitySpec(time="night")`; use `night()` for interiors, the park, the rooftop and the beach
- Finished examples are `cafe()`, `classroom()`, `living_room()` and `park()` in `examples/scenes.py`, and the 6 newer places in `examples/gallery.py`
- 21 test pictures of situations, poses, framing and group shots are in `examples/variety.py` (`BUILDERS`)
    + Including groups of 3-8, close and long shots, a low angle, a lying person, sitting facing the viewer on a bench and a sofa, and a meeting table
    + `office_late()` is an example of an office at night (`night()`) with a person walking between rows of desks (`arrange()`, `walk()`)
