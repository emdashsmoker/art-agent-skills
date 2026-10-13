# Drawing people

Values were verified in the figure examples under `examples/` (female: `portrait.py`, `nude.py`, `figure.py` / male: `portrait_male.py`, `nude_male.py`, `figure_male.py` / shared: `hands.py`, `feet.py`). The example people have adult proportions.

## Contents

- Head proportions
- Jawline
- Eyes
- Nose and mouth
- Hair
- Hair and face templates
- Neck and shoulders
- Adjusting apparent age
- Liveliness
- Full-body proportions
- Pose
- Building the body
- Seam handling
- Setting the head on
- Turning the head
- Hands
- Feet
- Joining hands and feet to limbs
- The 3-D mannequin
- Men
- Nude anatomy
- Dressing the 3-D body
- Dressing (2-D)

## Head proportions

Let H be the head height and T the y of the crown. The example has H = 453, T = 215, centre axis x = 500.

| Feature | Position | Example value |
|---|---|---|
| Face width (cheekbones) | 0.64-0.68 H | 290-304 |
| Eye centre | T + 0.52-0.55 H | y 458 |
| Distance between eye centres | 0.35 H | 80 each side of the axis |
| Eye width | 0.20-0.22 H | about 98 |
| Brows | 0.10-0.13 H above the eye centre | y 400-410 |
| Nose tip | T + 0.74-0.76 H | y 556 |
| Mouth | T + 0.85-0.86 H | y 603 |
| Chin tip | T + H | y 668 |

- Leave room for one eye between the two eyes
- Put the nose on the centre axis
- The crown of the hair is 0.08-0.10 H above the skull

## Jawline

Place half the face outline and close it with `symmetric()`.

```python
half = [(500, 215), (590, 232), (640, 300), (652, 400), (645, 480),
        (617, 574, True),      # jaw angle
        (567, 622),
        (520, 662, True),      # chin corner
        (500, 668)]
```

| Impression | Adjustment |
|---|---|
| Sharp jaw | Mark the jaw angle and chin as corners. Keep the run between them nearly straight |
| Slim jaw | Move the jaw angle's x 10-20 toward the axis |
| Round jaw | Remove the corner marks. Move the point between jaw angle and chin 10 outward |
| Square jaw | Widen the chin corner's x to 40 or more from the axis |

The jawline gets crisp only with a shadow cast on the neck.

```python
art.shadow(art.move(face_mask, 6, 40) * neck, skin_shadow)   # apply before drawing the face
```

## Eyes

The eyes are where a picture is looked at longest. Stack them in this order.

1. White: almond shape. Mark inner and outer corners as corners
2. Upper-lid shadow: `white * (1 - art.move(white, 0, 9))`
3. Iris: an ellipse cut by the white mask. The upper 1/5 hidden by the lid gives a calm gaze
4. A dark gradient on the upper iris
5. Iris rim ring: a large ellipse minus a smaller one
6. Pupil
7. Bright reflected light on the lower iris
8. Upper lashes: drawn as a closed shape. Thicker toward the outside, the end flicks up
9. Lower lashes: thin strokes on the outer half only
10. Double-lid line: a thin stroke in the skin-shadow colour
11. Brow: a stroke thick at the inner end and thin at the outer end (`taper="end"`)
12. Highlights: one large dot above on the light side, one small dot below on the opposite side

- Draw both eyes with the same function, passing `side = -1, +1`
    + The eye shape is mirrored
    + The highlight positions are not mirrored, because there is only one light

## Nose and mouth

- The less nose, the better
    + One small triangular shadow on the side away from the light
    + One short stroke under the nose tip
    + One small highlight on the nose tip
- The mouth has 3 layers
    + Upper lip area, lower lip area, the lip line between them
    + A small highlight in the middle of the lower lip
    + A faint shadow under the lower lip
- For cheek blush, cut `art.blob()` with the face mask and paint at 0.2-0.3 opacity

## Hair

Split it into three masses.

| Mass | When to draw | Role |
|---|---|---|
| Back hair | Before the neck and clothes | Silhouette of the whole head |
| Front hair | After the face and eyes | Covers the forehead and the sides of the face |
| Thin strands | Around the front hair | Breaks the monotony of the masses |

- Mark the hair tips as corners to make them pointed
- Apply the shadow the front hair casts on the face over the face
- Draw strands between two guide curves with `strands_between()`
    + Cut each strand at a different length for a natural look
- Add sheen with `sheen()`
    + Lay short strokes along the strand direction on an arc across the head's curve
- Paint a darker colour toward the bottom with `art.ramp()`
- Start 2-3 stray hairs inside the hair mass

`strands_between()` and `sheen()` are in `examples/portrait.py`.

## Hair and face templates

One `HeadLook` from `examples/head_style.py` chooses hair style, hair colour and features. Unset fields take the head module's default (`DEFAULT_LOOK`, the original face).

```python
from head_style import HeadLook
look = HeadLook(hair="bob", hair_colour="chestnut", eyes="round", brows="arched", lips="full", eye_colour="green",
                earrings="none", hat="beanie", cigarette="lit")
portrait.draw("anime", 1024, look)                       # bust
outfits.Look("f", "sundress", "standing", "beach", face=look)              # full body
outfits.Duo(("f", "bikini"), ("m", "swim_trunks"), "facing", "beach", faces=(look, None))
with portrait.styled(look): ...                          # when using a head module directly
```

| Field | Female head (`portrait.py`) | Male head (`portrait_male.py`) |
|---|---|---|
| `hair` | `long_straight` (default), `long_wavy`, `bob`, `ponytail`, `half_up`, `short_cut` | `short` (default), `side_part`, `medium`, `two_block` |
| `eyes` | `sharp` (default), `round`, `soft` | `sharp` |
| `brows` | `natural` (default), `straight`, `arched` | `straight` (default), `soft` |
| `lips` | `natural` (default), `full`, `thin` | `natural` |
| `hair_colour` | Default `navy` | Default `ink` |
| `eye_colour` | Default `amber` | Default `blue` |
| `earrings` | `drop` (default, gold earrings), `earphones`, `none` | `none` (default), `earphones` |
| `hat` | `none` (default), `beanie` | Same |
| `cigarette` | `none` (default), `lit` | Same |

- Hair colour names: `navy`, `ink`, `black`, `dark_brown`, `chestnut`, `honey`, `platinum`, `silver`, `burgundy`
    + Given `"#RRGGBB"`, the deep tone, sheen, shadow tint and brow colour are computed
    + Brows follow the hair colour
- Eye colour names: `amber`, `blue`, `brown`, `green`, `grey`, `violet`. `"#RRGGBB"` works too
- An unknown name stops with a list of the names you can choose

### How a hair style draws

One hair style draws 3 things: `back(art)` (behind the body), `masks(art)` (masks before painting; they cast shadows on the face), `front(art, masks)` (over the face).

| Style | Back hair | Front hair |
|---|---|---|
| `long_straight` | Below the shoulders | Curtain bangs from a side part, right side tucked behind the ear, a side-swept fringe |
| `long_wavy` | The same shape, waving from below the cheeks | Same |
| `bob` | Cut evenly at the jawline | Both sides fall in front of the ears to the jaw, a side-swept fringe |
| `ponytail` | A tie on top and a tail hanging to one side | Swept-back hair, thin strands at the temples |
| `half_up` | Below the shoulders, with a small knot behind the crown | Swept-back hair, a fringe, thin strands |
| `short_cut` | Ends above the ears | A fringe across the forehead, short strands at the temples |
| `short` (male) | Ends at the ears and nape | Pointed locks swept from a side part, one lock between the brows |
| `side_part` (male) | Same | Broad locks swept back from the part, forehead showing |
| `medium` (male) | Pointed ends at the jaw and nape | Locks reaching the brows, side hair covering the ears |
| `two_block` (male) | Sides clipped short so skin shows | Top and front hair only |

- Wavy hair fills the guide points densely, then pushes them sideways by height (`wave()`)
    + When the push depends on height alone, both edges of a lock sway together and its width holds
- On styles that show the forehead, keep the hairline even from the part to the far temple
    + A hairline that sinks at the part looks like the hair is thinning
- Draw thin temple strands as curves. Filled strands look like hairpins
- Hang the ponytail tail clear of the ear and outside the face
    + Next to the ear it looks like side hair or a string
- Gold earrings are not drawn on styles that cover the ear (`bob`) (`shows_ear`). Earphones draw only the cable there
- Cut long male hair to pointed ends at the jaw and nape. Rounded ends make a bowl cut
- Tuck the sides and nape of short hair inside the face outline. Outside it they look like a helmet's ear flaps

### Features

- An eye shape changes the white, upper lash band, outer-corner flick, lower lid line, double-lid line and iris radius as one set (`EYE_SHAPES`)
    + `round`: taller, with level outer corners. Raises the brows by 5
    + `soft`: lowers the outer corners. The flick goes downward too
- A brow is a 4-point stroke and a width (`BROWS`). Male brows are filled shapes
- Lips are the shape and paint strength of the upper lip, lower lip and lip line (`LIPS`)
- Jawline and face outline do not change

### Props

Choose a beanie, a cigarette and earphones with `HeadLook` (`examples/head_props.py`).

- `hat="beanie"`: a black knit beanie with a ribbed cuff
    + Its shape is the ellipse round the skull, cut at brim height
    + Put the brim just above the brows. High on the forehead it looks like a small cap perched on top
    + The brim and the fold line dip a little at the middle of the forehead, because the ring is seen a little from above
    + Ribs are spaced by even steps of angle, so they crowd toward the sides. Paint ribs and the fold line only inside the hat mask
- `cigarette="lit"`: a cigarette held at the mouth corner, the ember and its glow, smoke that rises and sways
    + `draw_cigarette(art, tilt, root, droop)` serves still lifes too (a cigarette resting on an ashtray)
- `earrings="earphones"`: white wired earphones
    + An earbud sits in each visible ear. The two cables meet under the chin and one runs on into the clothes
    + For an ear covered by hair, only the cable comes out from under the hair
- Props are laid over the finished head. Leave them unset and the picture does not change
- Positions are written per head module in `PROPS` (`PropPlaces`)
    + Skull ellipse, brim height, mouth corner, where cables start, where they meet, where smoke shows in a back view
- For a figure seen from behind, `draw_head_back()` draws the hat over the back hair and the smoke rising beside the head
- In a bust, merge the hat into the rim-light mask. Leave it out and the hair's rim light stays on the hat

## Neck and shoulders

- Neck width is 0.33-0.38 times the face width
- Shoulder width is 1.9-2.1 times the face width
- Draw the neck narrower than the collar. Wider, skin pokes out beside the collar
- Stack clothes as body panel, collar, seams
    + One shadow the collar casts on the body panel creates the garment's thickness

## Adjusting apparent age

| Element | Adult | Younger-looking |
|---|---|---|
| Eye centre height | T + 0.52 H | T + 0.58 H or more |
| Eye height / width | 0.40 or less | 0.55 or more |
| How much the iris is covered | Upper 1/5 covered | Fully visible |
| Nose to chin | 0.25 H | 0.20 H or less |
| Jawline | Straight with corners | Round curve |
| Neck | Long and distinct | Short |

Adult characters use the values in the left column.

## Liveliness

- Tilt the head 3-6 degrees
    + Apply the same `rotate()` to every curve of the head
    + Do not tilt the body
- Make the hair asymmetric
    + Tuck one side behind the ear and bring the other forward
- One accessory gives the eye a resting point

## Full-body proportions

A full body is 8 head lengths tall. Let one head be 100, the ground y = 0, and up negative.

| Point | y | Half width or thickness |
|---|---|---|
| Crown | -810 | Head width 72 (anime heads 6% larger than life) |
| Chin | -700 | |
| Shoulder line | -650 | Half width 66-74, sloping outward |
| Chest line | -600 | Half width 72-78 |
| Waist | -520 | Half width 50-56 |
| Navel | -497 | |
| Widest hips | -410 | Half width 80-92 |
| Crotch | -390 | Thigh thickness 82-92 |
| Knee | -220 | Thickness 46 |
| Widest calf | -160 | Thickness 50-53 |
| Ankle | -40 | Thickness 25 |

| Arm point | y | Thickness |
|---|---|---|
| Shoulder joint | -625 | 33 |
| Elbow | -520 (waist height) | 25 |
| Wrist | -405 (crotch height) | 19 |
| Fingertips | -330 (mid-thigh) | |

- Hand length is 0.7 head
- Neck length is 1/3 head. Longer, the head looks like it floats
- Women have a narrow waist and hips about as wide as the shoulders
- Keep the outer shoulder width (arms included) at about 1.6 (female) or 1.8 (male) head heights
    + Wider, or with square shoulders, the figure looks muscular even when clothed
    + A small head, thick arms and a low viewpoint add the same impression
- End the lower torso outline inside the hips of the trousers. The top's colour must not show between the legs

## Pose

Stand a figure in contrapposto. Standing symmetric, it becomes a mannequin.

- Put the weight on one leg
    + The hip on the weight side rises and pushes out
    + The shoulder on the weight side drops. Shoulder line and hip line tilt opposite ways
    + The head comes back over the weight-bearing foot
- Bend the other leg's knee slightly inward and set its foot out to the side
- Give the two arms different shapes
    + The clothed example lets one arm hang and puts the other hand on the hip
    + The standing nude raises one arm behind the head and rests the other hand on the thigh
- A body centre line that draws an S brings even a still standing figure to life
    + Push the pelvis centre 10-20 toward the weight side and the rib-cage centre 10 the other way
    + The waist on the weight side bends deeply; the other flank stretches long
    + Overlap the free leg's knee in front of the weight leg and the curve carries on to the toes
- A raised arm hides its hand behind the head. Three control points round the elbow make it bend sharply

## Building the body

- The torso is one closed curve from neck to crotch (`TORSO`, 27 control points)
- Limbs are tubes through the joints: `art.tube([(x, y, thickness), ...])`
    + A leg has 7 control points: hip, mid-thigh, knee, calf, lower shin, 2 at the ankle
    + Do not keep the centre line straight. The thigh curves outward and the calf outward again; that gives the leg its curve
- Merge the masks of torso, legs, feet, hanging arm and the other upper arm with `np.maximum.reduce()` and draw them as one part
    + Drawn without `bulge`, the whole body shades as one continuous mass
    + Drawn as separate parts, each joint gets ball-shaped shading and the figure becomes a jointed doll
- Draw the lines where limbs meet the body separately

```python
inner = art.grow(body, -3)
apart = 1 - art.grow(np.maximum.reduce([torso] + feet), 2)
art.outline(limb, art.line_color(SKIN), clip=inner * apart)
```

## Seam handling

An arm crossing in front of the body cannot be merged, so draw it separately. `add_limb()` in `examples/figure.py` does this.

- Keep the upper arm merged into the body and draw the whole arm tube over it again
- Do not repaint round the shoulder joint
    + Fade the arm mask out within a range made with `art.blob(root, 60)`
    + In that range the body's colour and shading already drawn show through
- Apply the shadow the arm casts on the body before the arm
- A bare hand is merged into the arm mask and painted at once. The method is under 'Joining hands and feet to limbs' below
- With a sleeve the order is reversed. Draw the hand first, then the sleeve over it

## Setting the head on

```python
HEAD_SCALE = 106 / 453            # the bust example's head length 453 as one head
with art.place(at=CHIN, scale=HEAD_SCALE, pivot=(500, 668), angle=-3):
    head = portrait.head_masks(art)
    portrait.draw_back_hair(art)   # before the body
# ... draw the body ...
with art.place(at=CHIN, scale=HEAD_SCALE, pivot=(500, 668), angle=-3):
    art.shadow(art.move(head["face"], 6, 40) * torso, shadow)   # shadow the chin casts on the neck
    portrait.draw_ear(art)
    portrait.draw_head_front(art, head)
```

- Draw the back hair before the body, the face and front hair after it
- Use the bust example's chin tip `(500, 668)` as the reference point and fit it on the neck

## Turning the head

A front-drawn head turns up to 35 degrees either way (`atelier.turn`). On a 3-D body, `nude.draw_figure()` computes the angle from the head direction and the camera and turns it automatically.

- Principle: every point of the face gets a depth, how far it stands forward
    + The depth is a flat ellipsoid plus the height of the nose (`FaceDepth`)
    + A point moves sideways by depth x sin(angle), and widths shrink by cos(angle)
    + The front-most middle of the face moves most. The centre line shifts toward the turn; the far eye and mouth narrow
- Points move in one of 3 ways, depending on the feature

| Way | Function | Features |
|---|---|---|
| Surface | `surface()` (the head module's `head()`) | Eyes, brows, nose, mouth, front hair, cheek shadows |
| Shell | No transform (the head module's `shell()`) | Back hair, ears, earrings. The outline of a round skull looks the same from any side |
| Outline | `outline()` | Face outline. The near side stays put down to the jaw corner; the far side and the chin move like the surface |

- Past 10 degrees the far ear is not drawn. It hides behind the cheek
- The iris narrows sideways by the local narrowing ratio (`squeeze()`)
- Past 8 degrees the line of the nose bridge is drawn
- On a 3-D body, the head's anchor is the turned chin position
- A head module provides a `turned(angle)` context and a `FACE_DEPTH` constant (`portrait.py`, `portrait_male.py`)
- Profiles and turns beyond 35 degrees cannot be drawn
- When the head is turned more than 110 degrees from the camera, only the hair is drawn, without a face (`nude.BACK_VIEW`)
    + From behind, the back-hair drawing is laid over the body and clothes, because long hair covers the back
    + Without this the face is drawn on the back of the head
    + Between 35 and 110 degrees the face turned at 35 degrees shows together with the hair mass at the back of the head

## Hands

A hand in `examples/hands.py` has the wrist centre at the origin, fingers pointing up (-y), length 100.

| Proportion | Value |
|---|---|
| Palm width | 0.45 of the hand length |
| Middle finger | 0.44 of the hand length |
| Finger length ratio (index : middle : ring : little) | 0.91 : 1 : 0.93 : 0.73 |
| Phalanx length ratio (first : second : third) | 0.46 : 0.30 : 0.24 |
| Finger thickness | 0.09-0.11 of the hand length |

- `draw_hand(art, pose, palm_side)`: a hand showing the back or the palm
    + In `Pose`, `spread` is finger spread, `curl` is joint bend, `stretch` is foreshortening of fingers pointing toward or away from the viewer
    + With `stretch` at 0.3 only the knuckles of folded fingers remain
    + Ready poses: `OPEN`, `RELAXED`, `POINTING`, `VICTORY`
- `draw_hand_side(art)`: a relaxed hand seen from the thumb side. Use it at the end of a hanging arm
- Fingers are tubes. Merge them with the palm, draw them as one part, and line only where fingers touch
- Put nails and knuckle creases on the back of the hand; 3 palm lines and joint creases on the palm
- Make a left hand with `flip=True`
- `separate()` puts dark gaps between touching fingers
    + Fingers stay countable even in styles without line art

## Feet

A foot in `examples/feet.py` is seen from the front. The ankle centre is the origin, toes point down (+y), the big toe is on the +x side. Units are the same as the full body (one head = 100).

- `draw_foot(art, instep, join)`: one instep wedge and 5 toe ellipses
    + `instep` is the length from ankle to toe roots. 24 for a foot flat on the ground, 44 for a raised heel
    + Make the other foot with `flip=True`
- Toes get smaller and step back from big toe to little toe
    + Half widths 7.0, 4.4, 4.0, 3.7, 3.3. Step back 0, 0.5, 2, 4, 6.5
    + The widths must leave gaps between toe tips so all 5 can be counted in any style
- Draw the little toe first and the big toe last. Front toes cover the ones behind
- Toenails are small ellipses on top of the toes; 3 lines of tendon light on the instep spreading to the toes; ankle-bone light on both sides of the ankle
- A foot seen from the front looks small, so draw it 1.2 times larger in a full body

## Joining hands and feet to limbs

Painting hands and feet apart from the limbs breaks the shading at wrists and ankles; they look like gloves or socks.

```python
with hand_placement(art):
    hand = hands.hand_parts(art, pose)             # masks only
arm = np.maximum(art.tube(ARM), hands.hand_mask(hand))
add_limb(art, arm, SKIN, SHOULDER, trunk, shadow)  # paint arm and hand as one mass
with hand_placement(art):
    hands.finish_hand(art, hand, pose)             # add only finger gaps, nails, creases
```

- Feet work the same way: make masks with `feet.foot_parts()`, merge them with the leg, add detail with `feet.finish_foot()`
- The same `art.place()` is used twice, so make the placement a function

## The 3-D mannequin

Build full bodies, especially seated or reclining poses, from the 3-D body in `atelier.mannequin`. Limbs placed in 2-D drift in length and overlap as the pose gets complex, and the body twists.

```python
from atelier import Camera, sculpt
from atelier.mannequin import FEMALE, MALE, Pose, Reach, build, add_skull
from atelier.sculpt import Scene, RoundBox, rotation, facing

pose = Pose(pelvis=(x, y, z), pelvis_frame=rotation(turn, lean, tilt),
            chest_frame=..., head_frame=...,
            left_hand=Reach(target, bend, forward, back, curl), right_hand=..., left_foot=..., right_foot=...)
scene = Scene()
scene.add(RoundBox(...), "floor")                  # props go into the same scene
marks = build(scene, pose, physique=FEMALE)         # adds the body and returns landmarks. MALE for a man
add_skull(scene, marks)                             # the place for the drawn head
result = sculpt.render(art, camera, scene)
sculpt.paint(art, result, "skin", skin, shadow, deep, sheen=0.28)
```

- Coordinates are in metres. x to the right, y away from the viewer, z up
- There are 2 builds, `FEMALE` (1.68 m tall) and `MALE` (1.80 m tall). Both are 8 heads tall
- A pose is data

| Field | Meaning |
|---|---|
| `pelvis` | Position of the point between the two hip joints. Standing, about 0.87 high for a woman and 0.935 for a man. Seated, chair height + 0.08 |
| `pelvis_frame`, `chest_frame`, `head_frame` | Directions of pelvis, chest and head. `rotation(turn, lean, tilt)` or `facing(up, front)` |
| `Reach.target` | Where the wrist or ankle goes |
| `Reach.bend` | Direction the elbow or knee points |
| `Reach.forward`, `Reach.back` | Direction the fingers or toes point; direction the back of the hand or the instep faces |
| `Reach.curl` | Hand: 0 open to 1 fist. Foot: 0 flat to 1 pointed toes |

- Elbows and knees are solved by inverse kinematics. Bone lengths hold in any pose
    + An unreachable target is reached as far as possible, and the shortfall is recorded in `marks["strain"]`
    + If it falls short by more than 2 cm, move the target toward the body
- To put a hand behind the head or on a knee, `build()` once to get landmarks and use them as targets (`nude.resolve()`, `Setting.hand_behind_head`, `Setting.hand_at`)
- The ankle of a foot flat on the floor is about 0.081 high for a woman and 0.088 for a man. With a raised heel, 0.115-0.125
    + Lower, the foot sinks into the floor; higher, it floats. Check that the lowest point of the sole meets the floor
- How the angles of `rotation(turn, lean, tilt)` feel
    + turn: positive turns the front of the body toward the viewer's right
    + lean: positive tips the top toward the viewer
    + tilt: positive tips the top toward the viewer's right
- For contrapposto give the pelvis tilt and chest tilt opposite signs. The standing example uses pelvis 7, chest -5
- For reclining poses lay the torso down with `facing(up=spine direction, front=direction the belly faces)`

### What rendering does

`sculpt.render()` casts a ray per pixel to find forms and returns what painting needs.

| Result | Use |
|---|---|
| `masks[group]` | Coverage mask per group. Outlines are smooth to sub-pixel precision |
| `lit` | Light computed from the real surface direction. `art.shade_by()` turns it into shading in the style's manner |
| `shadow` | Shadows cast by other forms. An arm on the body, the body on the floor |
| `ao` | Creases where less light reaches: armpits, under the breasts, between fingers |
| `sheen` | Where a wet-looking gloss falls |
| `contours` | Borders where a front form hides a form behind |
| `at(point)`, `visible(point)`, `disc(center, normal, radius)` | Mark a 3-D point on screen, check whether it is hidden, draw a small disc on the surface |

- Forms of the same group melt together where they meet. Different groups only touch
- `blend` is the melt width; `anchor` and `reach` are the range the melt reaches
    + Limbs melt only into their root joint; elsewhere where they touch the body a border remains
- `step=2` (default) casts a ray every two pixels. The result barely differs and it is 4 times faster

### Rules for changing mannequin forms

- Melting several forms into one joint adds volume and the joint swells like a ball
    + At a joint, butt the ends of two forms with similar radii and keep the melt width about 1 cm
- A melt edge that ends near a joint leaves a ring-shaped crease
    + Set `reach` to 10 times the melt width or more
- Attach muscle masses (calves, the sides of the hips) by melting long ellipsoids broadly. Joining two short rods leaves a kink
- A round arm start that pokes above the shoulder line makes square shoulders. Match the shoulder joint height to the shoulder line
- The toe row is wider than the instep. Widen the forefoot with a flat ellipsoid to support it (`FOREFOOT`)
    + With a narrow forefoot the outer toes stick out of the foot and look cut off, especially when the toes are seen head-on

## Men

The same procedure as for women: bust, 3-D mannequin, nude, clothed.

### Face (`examples/portrait_male.py`)

It uses the same function names as the bust example (`head_masks`, `draw_back_hair`, `draw_ear`, `draw_head_front`), so it sits on the mannequin as is.

| Element | Female bust | Male bust |
|---|---|---|
| Face width (cheekbones) | Reference | The same as the woman's or narrower. Wider, the face looks empty |
| Jaw | Narrow and pointed | Jaw angle lower; the chin flat and broad between two corners |
| Cheekbone to jaw | Smooth | One cel shadow on the side away from the light. Half strength in the painterly style |
| Eyes | Large and round, many lashes | Long almond. One heavy upper line runs past the outer corner and lifts slightly. The iris touches the upper line |
| Brows | Thin and arched, far from the eyes | Thick and straight, close to the eyes, angling down toward the nose |
| Nose | Only the shadow under the tip | A long bridge line on the shadow side |
| Mouth | Painted lip colour | One line and a shadow under the lower lip |
| Cheeks | Light blush | No blush |
| Hair | Long, covering the ears | Short but with volume. The crown is larger than the skull. Pointed locks swept from a side part, one lock falling between the brows, side hair in front of the ears. Sides and back end at ear height |
| Neck | Thin and long | Thick, with an Adam's apple |

- Make hair locks with `portrait.lock_points(root, tip, width, bend)`
    + Put the roots inside the crown mass, overlapping the neighbouring locks. Gaps between them make the forehead skin look like saw teeth
    + Draw a line that tapers at its end down the middle of each lock (`lock_centre_points`)
- The main cause of a bland male face is a wide face with small eyes. Narrow the face and enlarge the eyes

### Body (`MALE` build)

| Part | Female | Male |
|---|---|---|
| Shoulder width (between shoulder joints) | 0.30 | 0.36 |
| Hips | Spread much wider than the waist | A little wider than the waist |
| Chest | 2 breasts, hanging down | 2 flat pectorals with a groove along the lower edge |
| Belly | Smooth | Abdominals in 2 columns of 3, a V-shaped ridge above the hip bones |
| Back | Narrow | Broad back muscles under the armpits narrowing to the waist |
| Limbs | Smooth cylinders | Biceps, triceps and front thigh muscles as long ellipsoids melted on |
| Hands and feet | Reference | Hands 1.10 times, feet 1.08 times |

- Build the clothed full body thinner than the nude study (`figure_male.LEAN`)
    + Shoulder joint 0.157; deltoids and limbs thinner. The outer shoulder width comes to about 1.8 head heights
    + Change only the needed values with `dataclasses.replace(MALE, ...)`
- Keep the shoulder band and trapezius lower than the neck root. Higher, they climb the neck and the head looks set on the shoulders
- Attach muscles with `Body.muscle()`. It pushes a long ellipsoid along the bone axis to one side and melts it broadly
- Where grooves must remain, as in the abdominals, give a narrow melt (1.4 cm); where a mass must read, a wide one (3 cm)

## Finishing touches that make a face attractive

Items applied to the female bust (`portrait.py`). The same principles work on men.

| Item | Method |
|---|---|
| Fringe | 2-3 broad locks from the part, slanting across the forehead. Ends at brow height. Thin locks look like antennae |
| Fringe outline | Line only the part lying on the forehead. Lining the roots over other hair shows a seam |
| Lower face | Raising nose and mouth by 5-7 units looks younger and softer |
| Eyes | Pink in the inner corner, 2 lower lashes (downward from the lower lid), 3 highlights (large, small, tiny) |
| Cheeks | One light blush circle. Diagonal hatching over it looks like dated manga |
| Mouth | A short stroke lifting the mouth corners slightly. Drawn downward it looks like a fang |

## Nude anatomy

The aim is plausibility over detailed rendering. `examples/nude.py` holds 3 poses drawn on the mannequin: standing, seated, reclining.

- The 3-D body gets proportion, overlap, shadow and crease darkness right. Little needs adding by hand
    + Areolae, nipples and navel: stamp small discs on the surface with `result.disc()`. Skip hidden ones with `result.visible()`
    + Warm flush on knees and elbows: lay a thin `art.blob()`
    + Warm reflected light and key light
- The mannequin has no genital forms. The examples leave the place where the legs meet as a smooth form with shadow
    + The female example reads as a classical nude from the smooth form alone
    + On the male example the smooth form looks odd, so the groin is covered by pose or cloth, as in classical sculpture
    + Standing: a cloth held at the hip by one hand hangs in front (`sculpt.hanging_cloth()`)
    + Seated: one foot rests on a support, so the raised thigh crosses the middle of the body
    + Reclining: the upper leg bends forward and overlaps
- Sensuality comes from pose and light more than from the amount of detail
    + Put the weight on one leg and tilt pelvis and chest opposite ways
    + Raising one arm behind the head stretches the torso long
    + In a reclining pose overlap the upper leg forward and rest the upper arm on the hip
    + A dark background, a key light from one side, warm reflected light on the opposite edge
- The painterly style suits it best. In the anime style the shadow edges simplify and it reads as a manga body
- The same machinery draws both sexes: `nude.draw_figure(style, width, setting, sitter)`
    + `Sitter` bundles the build, the head to set on and the skin colours (`nude.WOMAN`, `nude_male.MAN`)
    + `Setting` bundles camera, pose, props, room and things to add (`extras`)

## Dressing the 3-D body

The method of `examples/figure_male.py`. It holds up to pose changes better than the 2-D mask method below. Clothes such as bikini, lingerie, suit, hoodie, skirts, dresses and scarves, plus wind, pose presets, two-shots and places, are in `references/wardrobe.md`.

```python
from atelier.mannequin import TROUSERS, dress
dress(scene, marks, "shirt", ("chest", "abdomen"), 0.012, smooth=0.012)  # shirt body
sleeves(scene, marks)                                                    # straight cylinder sleeves (figure_male.py)
dress(scene, marks, "trousers", TROUSERS, 0.012, smooth=0.012)           # pelvis, thighs, shins
dress(scene, marks, "shoes", ("foot",), 0.006, smooth=0.012)             # thin film over the foot inside the shoe box
```

- `dress()` makes clothes by growing the body forms as they are. They follow the body's curves and joints
    + `smooth` lets the cloth bridge the grooves between muscles. At 0 the abdominals show through the clothes
    + Keep `smooth` at about 0.012. Each melt adds a little volume, so large values puff up the whole garment
- A shirt grown from the body covers the neck root and the tops of the shoulders. Carve the neckline with `scene.carve()`
    + Carve once round the neck root and once with a long ellipse in front for an unbuttoned V neckline
    + Lay the collar down with short rods chained along the carved edge (`figure_male.open_collar()`)
- Do not grow sleeves from the body. Make them as 2 straight rods, shoulder to elbow and elbow to above the wrist
    + A sleeve grown from the arm shows the biceps and deltoid and looks like a bodybuilder's
- Add what the body lacks with simple forms
    + Straight trousers: one thick rod from 7 cm above the knee to the ankle. Starting at the knee, the cloth wraps the kneecap and looks like a lump
    + Collar: short rods standing in a ring round the neck
    + Belt: short rods chained densely round the pelvis
    + Shoes: a rounded box wrapping the whole foot. An ellipsoid thins at the toes and the toes poke through
    + Slim the box and the foot shows through. Add a film of the foot grown by 6 mm to the shoe group to block it
- Keep the camera for a clothed full body near eye level. Looking up from hip height makes anyone look large and strong
- For a hand in a pocket, push the hand into the trousers. The cloth in front hides the fingers
- Body region names: `neck`, `chest`, `abdomen`, `pelvis`, `upper_arm`, `forearm`, `hand`, `thigh`, `shin`, `foot`

## Dressing (2-D)

- Clothes start from the body's mask
    + For close-fitting clothes, paint the clothes colour on the torso and arm masks
    + For loose clothes, use thicker tubes on the same joint coordinates (`TROUSER_LEGS`)
- Cut hems flat by multiplying with a rectangle mask
- Give clothes form shadows as a flat volume with `bulge=30-40`
- 2-3 curves running from the joints are enough for folds
- Suggest the curve of the chest with one crescent shadow underneath
