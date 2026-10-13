# Drawing figures

> Translated from the Korean original. See the translation notice in `SKILL.md`.

## Contents
- Components
- Figure (proportions and pose)
- Body build and surface anatomy
- Male figures
- Pose conventions
- Hands
- Character (face, skin, expression)
- Hair
- wardrobe (clothing)
- Folk dress (kimono, hanbok, fundoshi, sarashi)
- Hand-held props
- Seated figures and tables
- Several figures (two-shots)
- Placement in the frame
- Figure checks
- Common adjustments

## Components

- `Figure`: a drawing mannequin made of a skeleton and masses; it has proportions, a pose and hand shapes
- `Character`: the unit that dresses a Figure in face, hair, clothing and skin colour and draws it on the canvas
- `Hair`: the hair mass (scalp cap) with fringe, side locks and back hair
- `wardrobe`: clothing that wraps the body masses
- `Character.draw` handles the drawing order (back hair, body and clothing, face, fringe, brows)
- Coordinates: head-height units (HU); x to the right of the picture, y up, z toward the viewer. In the rest pose the figure faces the viewer

## Figure (proportions and pose)

```python
Figure(sex="female", heads=7.75, slim=1.0, bust=1.0, pose="relaxed", hands=None,
       turn=0.0, lean=0.0, tilt=0.0, head_scale=1.0, curves=1.0, tone=None)
```

| Argument | Meaning | Suggested values |
|---|---|---|
| sex | female, male | |
| heads | Height in heads | Anime 6.8-7.4, natural 7.5-7.75, idealised 8, fashion 8.5 |
| slim | Thickness of torso and limbs | 0.9 lean, 1.0 default, 1.1 sturdy |
| bust | Female bust size | 0-1.3, classical figure studies 0.9-1.15 |
| curves | Contrast between female waist and hips | 0.6 straight, 1.0 default, 1.3 pronounced |
| tone | Strength of muscle tone | 0 smooth, female default 0.55, male default 0.75, 1 athletic |
| pose | Preset name or a dictionary of joints | Table below |
| hands | `{"l": preset, "r": preset}` | Hands section below |
| turn | Whole-body rotation; positive faces picture right | Three-quarter 25-35, profile 80-90, back view 180 |
| lean, tilt | Whole-body lean forward, tilt sideways | 0-10 |

- Pose presets (`POSES`)

| Key | Pose |
|---|---|
| stand | Standing at attention |
| relaxed | Relaxed upright stance with arms slightly apart |
| contrapposto | Classical stance with the weight on one leg |
| hand_on_hip | One hand on the hip |
| walk | Walking |
| sit | Sitting on a chair (draw the chair separately) |
| arms_up | Both arms raised |
| venus | Classical figure study pose, one arm across the chest and one lowered |
| allure | Contrapposto with one hand behind the head |
| arms_behind_head | Both hands behind the head, ribcage open |
| heroic | Both hands on the hips, chest out |
| david | Classical statue pose, weight on one leg and one hand on the opposite shoulder |
| arms_crossed | Folded arms |

- Override some joints on top of a preset: `figure.set_pose(head=(4, -26, -5), l_elbow=(25, 0, 0))`
- Adding `"_reach": {"r": "behind_head"}` to a pose dictionary sends that hand to the target when the figure is created (see `reach` below)

## Body build and surface anatomy

- The torso cross-section table follows measured proportions (waist about 0.7 HU front to back, pelvis about 0.9 HU)
    + In profile the S-curve of the spine shows: ribcage forward, small of the back hollow, pelvis tilted back
- Bust, buttocks, upper arms, thighs, shoulder girdle and lower belly join the torso smoothly
    + Giving a mass a `blend` value (HU) stamps it separately and merges it with a smooth union, so no crease forms at the seam
    + Deep steps that really overlap, such as the fold under the bust, are kept
- A skin pass fills shallow gaps between masses (hands, toes and face excepted)
- The spinal furrow, sternum, linea alba and navel are grooves pressed into the surface
    + Add a groove: `figure.extra_carves.append(dict(point=world point, radius=HU, depth=HU))`
- Muscle tone (scaled by `tone`)
    + Hollows: the notch below the neck, dimples of Venus, the lower pelvis furrow, the deltoid V, the line between biceps and triceps, the band down the outer thigh, either side of the knee tendon, either side of the Achilles tendon, the lower edge of the ribs
    + Swellings: sternocleidomastoid, shoulder blades, hip bones, brachioradialis, the teardrop muscle inside the knee, the two heads of the calf
    + Male figures add the abdominal grid, the lower edge of the chest and serratus anterior
    + For more swellings, extend `figure.anatomy()` or add grooves to `extra_carves`
- `figure.table_point(name, y, angle, side)`: rest-pose point on the surface of torso, neck or limbs (angle 0 front, 90 outward, 180 back)
- `figure.surface_z(y, "front" or "back")`: z of the torso centre-line surface at height y (for placing props and markings)
- Skin gloss follows the face style automatically (classic 0.06, semi 0.03, anime 0)
- Muscle tone shows fully on bare skin and only 20% through clothing (cloth covers the grooves)

## Male figures

- `Figure(sex="male")` uses the same joints and pipeline as the female figure with the male cross-section table (`MALE`)
    + Shoulder joints at 0.86 HU, pelvis 0.66 HU wide, a short straight waist, a deep ribcage (a V-shaped torso, broad shoulders, narrow hips)
    + Hands 1.12 times, feet 1.08 times larger, a thicker neck, straighter outer thighs
- Male muscle masses (merged into the torso with `blend`)
    + Chest plates, heads of the deltoids, the slope of the trapezius, the wings of the latissimus
    + Smaller buttock masses than the female figure
- Male muscle tone (tone default 0.75): biceps, triceps, outer thigh, rectus femoris, obliques above the pelvis, the hollow beside the buttock, the lower edge of the chest, the abdominal grid, serratus anterior, Adam's apple
- Face and head follow `figure.sex` automatically
    + Head section: wider below the jaw, a broad chin that juts forward
    + Facial relief: brow ridge 1.9 times, eye sockets 1.25 times, cheekbones 1.25 times, jaw 1.5 times, an added jaw angle, lips 0.6 times
    + Features: eye height 0.8 times, lashes 0.45 times, eye-corner slant 0.3 times, almost no blush, brows low, straight and thick
    + Semi male faces leave the lips unpainted and draw only the mouth line and the shadow under the lower lip, plus one line down one side of the nose
    + Male figures take only half of the style's neck slimming (anime 0.74, semi 0.82)
- Classical male figure study
    + A knotted cloth round the pelvis (`wardrobe.loincloth()`) follows the convention of classical painting and leaves the legs bare
    + Suggested: `pose="david"` or `heroic`, turn 10-25, rembrandt lighting, classic face, heads 7.9 (`figure_classical_male.py`)
- Webtoon male portrait: semi face, `Hair("crop", "textured")`; a light top and studio lighting show the build well (`portrait_male.py`)

## Pose conventions

- Joint values are angles `(forward, twist, side)`
    + forward positive: bend forward (raise a limb forward, bow the spine)
    + twist positive: turn toward picture right
    + side positive: spread a limb outward; tilt spine and head toward picture right
- Joint names

| Part | Joints |
|---|---|
| Torso | pelvis, waist, chest, neck, head |
| Arms | l_clav, l_shoulder, l_elbow, l_wrist (r_ for the right) |
| Legs | l_hip, l_knee, l_ankle (r_ for the right) |

- l_ is the figure's own left (it appears on picture right in a front view)
- Elbows and knees use only the forward value (positive bends both)
- The clavicle (clav) is `(push forward, -, raise shoulder)`
- Common values
    + Raise an arm 90 degrees forward: `l_shoulder=(90, 0, 0)`
    + Arm out level to the side: `l_shoulder=(0, 0, 90)`
    + Turn the head toward picture left and bow it slightly: `head=(8, -25, 0)`
    + Weight on the right leg: `pelvis=(0, 0, 7), r_hip=(0, 0, -7), l_hip=(15, -10, 11), l_knee=(28, 0, 0)`
- Pose an arm by hand position: `figure.reach(side, target)` computes shoulder and elbow angles so the wrist reaches the target
    + Named targets (`REACH_TARGETS`): hip, waist_front, chest, heart, opposite_shoulder, own_shoulder, fold, collar, lap, pelvis_front, chin, cheek, hair, behind_head, pocket, forward, up, side
    + hip computes the surface beside the waist for the body build, so the hand meets the waist on both sexes
    + Coordinate targets: `figure.reach("l", (x, y, z), anchor="chest")` in rest-pose coordinates; positive x is the reaching arm's side
    + Returns the remaining distance (HU); under 0.1 means reached
    + Set the torso pose first, then call it (the target moves with the torso)
- Tilting the pelvis tilts both legs, so counter it with the opposite side value on the standing leg's hip
- When building a new pose, adjust one or two joints at a time and check with `--rough`

## Hands

- Five fingers are fixed by the skeleton; only the hand shape is chosen
- Presets (`HAND_POSES`): relaxed, open, fist, point, hold, grace
- Direct shape: `{"curl": [(knuckle, middle joint) x 4], "spread": spread angle, "thumb": (spread, opposition, bend)}`
- Turn the palm with the wrist twist: `l_wrist=(0, 90, 0)`
- When hands are small on screen (full figures), relaxed or grace is the safest

## Character (face, skin, expression)

```python
Character(figure, style="anime", jaw=0.7, cheek=1.0, hair=Hair(...), palette=None, outfit=(),
          expression="neutral", gaze=(0.0, 0.0), skin="fair", beard=0.0, glasses=None)
character.draw(canvas, x, ground_y=None, height=None, head_top_y=None, unit=None, light=None)
```

| Argument | Meaning |
|---|---|
| style | anime (large eyes, line-led), semi (webtoon, semi-realistic), classic (natural proportions, for painting) |
| jaw | 0 round jaw, 1 sharp V line; default 0.7 |
| cheek | Cheek width multiplier |
| palette | Overrides for skin, iris, brow, lash, lip, eye_white, blush colours |
| expression | neutral, gentle, smile, serious, sad, tired (heavy half-closed lids, lowered brows) |
| gaze | Eye direction (x, y), range -1 to 1 |
| skin | porcelain, fair, light, warm, olive, tan, brown, deep, or a colour code |
| beard | Stubble 0-1 (fine stippling and a light shadow on jaw, chin and upper lip); 0.3 light, 0.6 heavy |
| glasses | None, round (thin metal frame), oval, square (heavy horn rim), or `dict(kind, color, lens)` |

- `brief.character()` builds a Character from the brief's settings; figure, hair, outfit and the rest can be overridden as arguments
- Passing `light` to `draw` computes the shadows the body casts on itself, under the jaw, under the arms and so on
- Face styles
    + anime: flattens facial shading so the face is never split by shadow
    + semi: 55% facial relief, double-eyelid line, lower lid, nostril wings, the Cupid's bow of the upper lip
    + classic: 100% facial relief; the iris takes the light and the eye white darkens toward both corners like a sphere
- Facial relief is a displacement pushing the head surface forward (`head.FaceRelief`)
    + Eye sockets, bridge and tip of the nose, nostril wings, cheekbones, the area round the mouth, upper and lower lips, philtrum and chin are one continuous skin
    + Profile outline and shading stay consistent at any angle
- Ears get their rim and the shadow of their hollow automatically
- Glasses are a rigid frame floating in front of the eyes; they foreshorten with head turns and only the visible temple runs back to the ear
- `draw` runs three stages in turn: `place` (projection), `build` (relief), `paint` (colour and face). For several figures `Ensemble` calls the stages separately
    + Other elements can be drawn between stages: after `build` the canvas positions of hands and joints are known and nothing is painted yet
    + When drawing in between, call `build(view)` without back_hair (`paint` draws long back hair so it lies in front of the prop)

## Hair

```python
Hair(style="long", fringe="swept", color="#3e2f45", side=None, volume=None, wave=0.0, sway=0.0,
     length=None, seed=1, gloss=0.55, strand=0.3, ring=0.0)
```

| Argument | Choices |
|---|---|
| style | long, medium, bob, short, ponytail, bun, updo, crop (short male hair), beanie (knit beanie) |
| fringe | swept (side-swept), straight (blunt bangs), parted (centre parting), curtain (curtain bangs), wispy (thin strands), none, side_part (male side parting), quiff (swept up), textured (short and tousled) |
| volume | Hair volume; None takes the style default (crop 0.45, others 1.0) |
| side | Side-lock length (HU); 0 for none |
| wave | 0 straight, 1 heavy waves |
| sway | Drift with the wind; negative is left |
| length | Back hair length (HU) set directly |
| strand | Strength of the strand streaks (0.3-0.5 in painting styles) |
| ring | Strength of the highlight band on the crown (applied automatically in anime styles) |

- Fringe and side locks are solid strands lying on the skull (part of the same height map as the body)
    + They cover the face correctly, cast shadows on the forehead, and the face never shows through at any angle
    + Wide locks split into three thinner strands for texture; long side locks fall with gravity at the tips
- Hair texture is streaks smeared along the flow of the strands (the strand value)
- The classic style drops the lines between locks for one mass; anime and semi draw a flow line on every lock
- crop is a shell of even thickness over the skull (`CROP_HAIRLINE` defines the hairline)
    + Rounded over the forehead, rising slightly at the temples, sideburns in front of the ears, then behind the ears down to the nape
    + It pairs with the three male fringes and leaves the ears showing
- A third value on a fringe path point lifts the hair off the scalp there (the raised front of a quiff)
- beanie is a knit cap built the same way as crop
    + It covers the forehead low and ends at a line over the tops of the ears down to the back of the skull (`BEANIE_LINE`); the crown swells a little
    + The turned-up cuff (`BEANIE_CUFF`) has vertical ribbing and a fold line; gloss and strand texture switch off automatically
    + It pairs with fringe none (choosing a beanie in the brief sets the fringe to none automatically)
- For black hair in night scenes, lower to about `gloss=0.2` so the crown highlight does not break into fragments

## wardrobe (clothing)

- List garments in `outfit` from the innermost out

| Function | Main arguments |
|---|---|
| `top(color, sleeves, hem, neck)` | sleeves: none, cap, short, elbow, three_quarter, long |
| `pants(color, length)` | length: full, cropped, knee, shorts |
| `skirt(color, hem, flare)` | hem: 3.2 mini, 2.5 knee, 1.2 midi, 0.5 maxi |
| `dress(color, sleeves, hem, flare, neck)` | |
| `coat(color, hem, sleeves)` | Outer layer worn over other garments |
| `drape(color, top_y, hem, flare)` | Classical cloth wrapped round the hips (down to the feet like a skirt); on a man it follows his own hip width |
| `loincloth(color, top_y, length, width, knot)` | Hip band, cloth hanging front and back, a knot on one hip (classical male figure study); length is the front cloth length (HU), knot "l" or "r" |
| `shoes(color)` | |
| `hoodie(color, sleeves, hem, strings, pocket)` | Hoodie with the hood down: a thick hood collar round the neck, the empty hood lying on the back, two drawstrings at the throat, a pouch pocket |
| `turtleneck(color, sleeves, hem)` | Fitted knit with a collar rolled up round the neck |

- hem, neck and top_y are rest-pose heights (HU): waist 4.95, hips 4.2, knees 2.1
- Add details with the `detail` argument
    + `top(..., detail=wardrobe.neckline("v", depth, width))`: V-neck or scoop neck
    + `coat(..., detail=wardrobe.open_front(inner_color, lapel=True, buttons=0))`: a coat worn open with lapels
    + `top(..., neck=6.62, detail=wardrobe.collar(open_neck=True, buttons=5))`: shirt collar and button placket
- The `folds` argument sets the strength of fold shading (0 is smooth)
- Clothing wraps the bust, buttocks, male chest plates and deltoid heads, so muscle masses never pierce it
- Draw patterns, logos, ribbons and the like inside the garment after `draw` with `canvas.add(..., clip=view.part_mask("top") > 0.5)`

- Doomer outfits
    + Man: `Hair("beanie", "none")`, `hoodie`, `expression="tired"`, a cigarette in the mouth (`doomer_male.py`)
    + Woman: `Hair("bob", "straight", gloss=0.2)`, `turtleneck`, a long open `coat`, folded arms (`doomer_female.py`)
    + Wired earphones are two thin lines from points beside the face meeting at one point on the chest, plus one line running down (`earphones` in `doomer_female.py`)

## Folk dress (kimono, hanbok, fundoshi, sarashi)

| Function | Main arguments | Shape |
|---|---|---|
| `kimono(color, sleeves, hem, collar, under, pattern)` | sleeves: short, tomesode, furisode / pattern: None, blossom, dots | Crossed collar with the left panel on top, a collar band, a white han-eri inside the neck, sleeve pouches hanging below the arms, a wrapped skirt to the ankles |
| `obi(color, width, cord, bow)` | width: wide (women), narrow (men) | wide is a sash from the waist to below the bust with a box knot on the back (otaiko) and a cord across the middle (obijime); narrow is a sash tied low on the hips with a small knot |
| `jeogori(color, length, git, dongjeong, goreum)` | length: short (women), long (men) | Collar closing to the right (git colour), white dongjeong at the neck, two goreum ribbons hanging from the right breast, sleeves rounded underneath |
| `chima(color, top, hem, flare)` | top: height above the bust (default 6.05) | Skirt tied above the bust, falling straight from below the bust to the hips and flaring wide below |
| `baji(color, ease)` | | Wide trousers gathered at the ankles with daenim ties |
| `fundoshi(color, apron, twist)` | apron: 0 (rokushaku), about 1.0 (etchu) | Twisted waist band, front pouch, a strand between the buttocks; apron is the length of the front flap (HU) |
| `sarashi(color, lo, hi)` | belly: lo 4.62, hi 5.6 / chest: lo 5.5, hi 6.35 | White cloth wound flat round the body several times, with the lines of the turns |

- Dressing order (innermost first)
    + Kimono: `[kimono(...), obi(...), shoes("#f4f2ec")]` (white shoes stand in for tabi)
    + Women's hanbok: `[chima(...), jeogori(...)]`; the jeogori covers the top of the chima
    + Men's hanbok: `[baji(...), jeogori(..., length="long")]`
    + Festival dress: `[fundoshi(), sarashi()]`; add `coat(hem=4.2, sleeves="elbow", detail=open_front(...))` on top for a happi
- The `Brief` outfit options kimono, hanbok and festival build these sets for each sex
- Kimono skirts and the hanbok chima widen so a walking leg never shows through a corner of the cross-section; with a long stride the skirt opens wide
- Collars, ribbons and the lines of the turns are drawn on torso surface coordinates, so they follow the body as it turns; nothing is drawn on the side facing away
- Kimono patterns are flat motifs scattered over the garment and do not bend with its folds
- Examples: `scene_blossom_walk.py` (furisode and obi), `figure_hanbok.py` (women's hanbok), the check sheet `tools/verify_sheets.py folk`

## Hand-held props

- Props held in the hand that pass behind the body, such as umbrellas, are drawn in two parts around the figure (`scene_rain_night.py`, `scene_blossom_walk.py`)

```python
figure.reach("r", (0.05, 5.55, 0.62), anchor="chest")         # grip in front of the chest
figure.hands["r"] = "fist"
view = character.place(canvas, x, ground_y=foot_y, height=h)
character.build(view)                                           # hand positions are now known
fist = view.group_mask("hand_r") > 0.5
ys, xs = np.nonzero(fist)
grip = (xs.mean() / canvas.scale, ys.mean() / canvas.scale)     # centre of the fist
spec = dict(hand=grip, centre=(head_x - unit * 0.75, head_y - unit * 1.3), radius=unit * 2.6, view=0.42)
props.umbrella(canvas, part="back", **spec)                    # canopy and shaft: behind the figure
character.paint(view, light=light)
props.umbrella(canvas, part="front", clip=1.0 - fist.astype("float32"), **spec)   # handle: under the fist
```

- An umbrella resting on the shoulder and tipped back shows its inside behind the head like a halo (view 0.4-0.55)
- For a parasol, put the canopy centre above the head toward the opposite shoulder so the face stays clear
- The centre of the hand mask locates a held prop more precisely than `view.joint("r_wrist")` (the grip sits a palm's length from the wrist)

## Seated figures and tables

- `pose="sit"` places the feet on the floor with the pelvis at chair height (about 0.45 m)
    + Give `height` as the standing height and set `ground_y` to the floor point under the seated feet
    + Draw the chair before the figure (`Perspective.chair`, back rest on the side of the figure's back)
- Hands resting on a table must lie on top of it and the knees under it, so drawing goes in three steps (`scene_cafe_window.py`)
    + Draw the whole table and what stands on it (laptop, mug) first
    + Draw the figure (hands and forearms lie on the table)
    + Redraw only the table top, covering just the legs with `clip=view.group_mask("pants")`
- Example target for hands on a keyboard: `figure.reach(side, (0.26, 5.78, 1.7), anchor="chest")` (rest-pose coordinates, 1.7 HU in front of the body)
- For a half-length crop with folded arms resting on a table, draw the table after the figure with a clip that cuts out the arm mask (`portrait_candle.py`)
    + `arms = sum(view.group_mask(g) for g in ("arm_l", "arm_r", "hand_l", "hand_r"))`
    + `objects.table(canvas, y, clip=1.0 - arms)`
- A figure sitting sideways (turn -60 to -75) shows the overlaps of hands, legs and table most clearly; sitting front-on, a laptop on the table hides the upper body
- A back view on a bench (turn 180) is drawn as bench legs and seat, then the figures, then the back rest (`doomer_duo.py`)
    + The feet go on the floor point 0.45 m in front of the seat; coats show between the back-rest slats and calves and heels show under the seat
    + With the camera 1.1 m high behind the bench looking down, the distance opens up beyond the two figures

## Several figures (two-shots)

```python
ensemble = Ensemble.from_framing(canvas, compose.framing(canvas, "three_quarter"), man)   # based on the largest figure
ensemble.add(man, W * 0.42, depth=-30)            # depth: shift toward the viewer (design units); negative is back
ensemble.add(woman, W * 0.60, size=0.95)          # size: head size multiplier (0.92-0.96 for a smaller partner)
ensemble.touch(man, "l", woman, "around_shoulder")
with canvas.layer(depth=0.3, group="figure"):
    views = ensemble.draw(light=light)
```

- All figures share one ground line and head size, so one figure's hand can be placed on the other's body
    + To set the ground line yourself, as for full-length two-shots in a landscape, use `Ensemble(canvas, ground_y, unit)` (unit is the height of one head)
- Contact spots of `touch(reacher, side, partner, spot)`

| spot | Action |
|---|---|
| around_shoulder | Arm round the partner's back, hand on the far shoulder |
| shoulder | Hand resting on the front of the near shoulder |
| upper_arm | Holding the partner's upper arm (close to arm in arm) |
| waist | Hand behind the partner's waist |

- `hold_hands(a, side_a, b, side_b)`: the two figures hold hands at hip height between them
- Fix the partner's pose before setting contact (the hand moves to the partner's current body position)
- The return value is how far the wrist misses the target (HU); under 0.1 means contact
- What `draw` handles
    + Builds both figures' relief first, then compares depth and erases what lies behind (an arm passes behind the partner's back)
    + Paints the far figure first and hides long back hair behind the figure in front
    + Computes the shadow one figure casts on the other and the contact shade where a hand touches
    + Prints a `tangent check` warning when one figure's hand lies in front of the other's pelvis on screen (check directly with `ensemble.tangents()`)
- Placement tips
    + Keep at least 1.7 HU between the figures' centres (closer, arms and bodies cut into each other)
    + For an arm over the shoulder, set the embracing figure about depth -30 back; for holding hands, use the same depth and about 2 HU apart
    + For figures facing each other, give opposite turns of about 35
    + When two figures stand close, the inner hand hangs in front of the partner, so place the inner hand with `touch` too (on the partner's waist with an arm over the shoulder)
    + For holding hands seen from behind, see `scene_beach_sunset.py` (same depth, about 2 HU between centres)

## Placement in the frame

- Crop presets: `compose.framing(canvas, kind, x=...)` builds the arguments to pass to `draw`

| kind | Range |
|---|---|
| face | Face close-up |
| bust | Bust |
| half | Waist up |
| three_quarter | Knees up |
| full | Full length |

- Direct placement
    + Full length: `draw(canvas, x, ground_y=y where the feet touch, height=height)`
    + Close-up: `draw(canvas, x, head_top_y=y of the crown, unit=height of one head)`
- To stand a figure in a perspective background, compute foot position and height with `Perspective.point` and `Perspective.scale` (see `scene_anime_film.py`)
- Call `scenery.contact_shadow(canvas, x, y, width)` before the figure for grounding

## Figure checks

- Use the return value of `view = character.draw(...)` for follow-up work
    + `view.joint("l_wrist")`: canvas coordinates of a joint (for putting a prop in the hand)
    + `view.part_mask("head")`: the area where a part is actually visible
    + `view.to_canvas(figure.world("chest", (x, y, z)))`: any point on the body surface
- `qa.check_figure(view)` returns (visible count, defined count) for each hand and foot
    + The defined count is always 5; a lower visible count means the digits are hidden by another part or off canvas (feet in shoes show 0 toes)

## Common adjustments

| Symptom | Adjustment |
|---|---|
| Face split in half by shadow | Switch lighting to soft_front or `draw(face_flatten=0.8)` |
| Head too large or small | Adjust `heads` |
| Shoulders look too wide | `slim=0.92` or a larger `turn` |
| Messy fold shading on clothes | Garment `folds=0` |
| Lines too thick or thin | `draw(line_width=...)` |
| Stiff pose | Opposite side values on pelvis and chest, a slight twist and side on the head |
| Figure study looks like a mannequin | An asymmetric pose such as `allure`, turn 15-35, rembrandt lighting, classic face |
| Bust looks like attached balls | Keep bust 0.9-1.15, three-quarter lighting rather than side lighting |
| Flat body shape | curves 1.1-1.3, heads 7.8-8 |
| Muscle tone too strong or invisible | tone 0.3 or 0.8; tone on back and legs shows best in back or side light |
| A man looks feminine | Check `sex="male"`, jaw 0.5-0.7, `Hair("crop", ...)`, beard 0.2-0.4 |
| A male face looks small (webtoon) | `head_scale=1.05`, heads 7.7 |
| A male top looks puffed up | Top `ease=0.025`, coat `ease=0.04`; avoid an open coat with folded arms |
| An arm pierces the partner's body in a two-shot | Widen the gap between figures or move the embracing figure further back in depth |
| Holding hands seen from behind | Turn both figures 170-190, `hold_hands(left figure, "r", right figure, "l")` (from behind, the right hand is on picture right) |
| Legs poke out behind a long coat on a walking figure | Shorter stride `set_pose(l_hip=(18, 0, 2), r_hip=(-8, 0, 2))`, coat `ease=0.12` |
| A seated figure's hands hidden by the table | Draw the table before the figure, then cover only the legs with a clip (seated figures and tables) |
| The elbow shoots up when resting the chin on a hand | The hand-target IK picks a solution that sends the elbow up; use a stable pose such as folded arms (arms_crossed) or arms on a table |
| The hand of an arm over the shoulder looks awkward | Adjust the wrist angle from the default `touch(..., hand="hold", wrist=(0, -60, -45))` by 10-15 degrees at a time |
