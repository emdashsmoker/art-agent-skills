# Full-body figures and hands (paintkit.figure)

Draws adult full-body figures posed by joint angles. Female and male builds use the same rig. The body turns all the way round for front, three-quarter, profile and back views, and seated poses are possible. The body paints its parts (torso, neck, legs, feet, arms, hands) as one continuous skin. Once a full body is built, `framing()` cuts it down to a bust or a face.

```python
from paintkit.figure import ILLUSTRATION, Figure, HairSpec, HandSpec, Physique, Pose, aim, draw_figure, framing
from paintkit.figure import wardrobe

figure = Figure(pelvis=(500, 760), height=1270, pose=Pose(hip_tilt=7, shoulder_tilt=-5))
masks = draw_figure(cv, figure, garments=[wardrobe.dress('#b0344a')])

man = Figure(**framing(cv.size, 'waist'), sex='male', pose=Pose(turn=-25, head_yaw=-20))
```

## Contents

1. Scope
2. Coordinates and angles
3. Figure
4. Pose
5. Physique and the curves of the body
6. Turning the body (turn): front, profile, back
7. Seated poses and foreshortening (aim)
8. Zoom (framing)
9. Men
10. Pose recipes and pose presets (poses)
11. Garments (wardrobe)
12. Figure studies
13. Hands
14. Returned values
15. Placing figures in a scene and composition (fit, thirds, group)
16. Hairstyles (hairstyles)
17. Face styles and expressions (expressions)
18. Limits

## 1. Scope

- The build is fixed at adult proportions of about 8 heads
- Two builds, `sex='female'` (default) and `sex='male'`
- The body turns all the way round (`Pose.turn`, -180..180). 90 is a profile facing screen right, 180 a back view. The head turns separately with `head_yaw`
- Standing poses, seated poses (thighs forward with `aim()`), lying poses seen from above (`roll`)
- The style looks most natural with a soft look such as `ILLUSTRATION` (continuous volume shading). `ANIME` paints with cel shading

## 2. Coordinates and angles

- The length unit is the head unit (half the head height). `figure.unit` = `height / 16.1` px
- Left and right are always screen sides. `left_arm` is the arm seen on the left of the screen when the body faces front
- Angles are screen degrees. 0 is down, positive toward screen right, negative toward screen left, 180 up

| Angle | Direction |
|---|---|
| 0 | Down |
| 90 | Screen right |
| -90 | Screen left |
| 150 | Up and right |
| -150 | Up and left |

- Key heights (from the crown at 0, in head units): chin 2.0, shoulders 3.0, chest 4.1, waist 5.6, pelvis center 7.6, knees 11.5, ankles 15.3, soles 16.1

## 3. Figure

| Argument | Meaning |
|---|---|
| `pelvis` | Pelvis center (middle of the hip-joint line) px. The soles of a figure standing straight are at `pelvis.y + 0.53 * height` |
| `height` | Crown to soles in px (standing straight) |
| `pose` | `Pose` |
| `physique` | `Physique` |
| `sex` | `'female'` or `'male'`. Changes the build tables and the face and hair defaults |
| `face`, `hair` | `FaceSpec`, `HairSpec` as in the bust rig. None gives the defaults per sex (`FEMALE_FACE` with long hair, `MALE_FACE` with `MALE_HAIR`) |
| `look` | Default `ILLUSTRATION` |
| `jaw` | Width scale of the lower face. None gives female 0.93, male 1.06 |
| `body_details` | Chest marks, navel, body creases and muscle marks. False when clothes cover everything |

## 4. Pose

| Argument | Default | Meaning |
|---|---|---|
| `turn` | 0 | Turns the whole body about its vertical axis. -180..180. Positive turns the front of the body toward screen right. 90 profile, 180 back view |
| `lean` | 0 | Tilt of the spine. Positive leans the upper body toward screen right |
| `hip_tilt` | 0 | Positive drops the hip on screen right |
| `shoulder_tilt` | 0 | Positive drops the shoulder on screen right |
| `left_arm`, `right_arm` | (-6,-1), (6,1) | (upper arm, forearm) angles. With 4 values (upper arm angle, forearm angle, upper arm length share, forearm length share) |
| `left_leg`, `right_leg` | (2.5,1), (-2.5,-1) | (thigh, shin) angles. With 4 values the length shares too |
| `left_hand`, `right_hand` | `HandSpec()` | Hand shape. The fingertips follow the forearm direction. `view` sets which way the palm faces (section 13) |
| `left_foot`, `right_foot` | -0.12, 0.12 | 0 toes to the front, -1 profile toward screen left, +1 toward the right. The feet turn with the body |
| `front_leg` | None | The leg in front where the two overlap. None takes the leg nearer to the side the body turns to (`'right'` from the front) |
| `head_yaw`, `head_tilt` | 0 | Head turn, head tilt |
| `neck` | 0 | Tilt of the neck |
| `roll` | 0 | Rotation of the whole trunk. 90 is a lying pose with the head to screen right |

Limb angles are absolute screen angles, independent of `roll` and `turn`. For large body turns, give directions in the body's own frame with `aim()` and the pose holds from any angle (section 6).

## 5. Physique and the curves of the body

| Argument | Meaning |
|---|---|
| `bust` | Breast size scale (pectoral size for men) |
| `waist`, `hips`, `shoulders` | Width scales. `hips` also affects the thickness of the thighs |
| `limbs` | Thickness of arms and legs |
| `gloss` | Faint sheen along the edge facing the light (0-1) |

To stress female curves, start around `Physique(bust=1.15, waist=0.93, hips=1.10)`. A muscular man: `Physique(shoulders=1.05, limbs=1.08)`. Beyond 1.25 the forms turn awkward.

The curves of the body come from the structure below. To change the build, use the `Physique` scales first and edit the tables only when a form itself looks wrong.

- Arms and legs have separate outer and inner contours (`_ARM_OUTER`, `_ARM_INNER`, `_LEG_OUTER`, `_LEG_INNER` in `fullbody.py`, prefixed `_MALE_` for men)
    + Thigh: the outer side comes down gently from the hip, the inner side narrows quickly below the lower pelvis
    + Calf: the outer swell sits a little higher than the inner one
    + Arm: the shoulder muscle outside the upper arm, the swell at the top of the forearm
    + Table values are `(t, half-width)` in head units. t runs 0-1 from joint to joint
- Knees and elbows are rounded with the `bend` of `Canvas.contour` (`_JOINT_BEND`)
- The torso joins the chest-waist-pelvis contours (`_CHEST_SIDE`, `_PELVIS_SIDE`), smooths the waist once (`_WAIST_SMOOTHING`) and adds an elliptical mass beside each hip (`_HIP_CAP`). Tilting the pelvis does not kink the waist
- Every contour point has a front and back depth (`_CHEST_DEPTH`, `_PELVIS_DEPTH`). When the body turns, these depths decide the side silhouette
- Skin shading mixes rounding per part with a broad rounding of the whole body (`broad_bulge`). The legs are shaded as one mass down to the feet, so the ankles do not look like balls

## 6. Turning the body (turn): front, profile, back

```python
three_quarter = Pose(turn=35, head_yaw=28, hip_tilt=5, shoulder_tilt=-3)
```

- Each height of the torso is treated as a cross-section (half-width, front depth, back depth), and the turned silhouette is computed from them
    + The side lines of chest and belly show on the silhouette the body faces, the back and buttocks on the other side
    + The far breast becomes a side view whose upper slope continues from the chest wall
- Navel, collarbones, the center line of the belly and chest marks are points on the body surface, so they turn along (`skeleton.chest.surface(x, y)`)
- The far arm hides behind the torso and chest. The far leg is painted behind the near leg
- Turning the head less than the body looks natural: up to three-quarter `head_yaw = turn * 0.6-0.8`, profile and back `head_yaw = turn`
- Profile (90): the front and back depths of the body give the side lines of chest, belly, back and buttocks, and the legs switch to side contours (thigh and knee in front, calf behind). The face becomes a profile with nose, lips and chin breaking the outline, and only the near eye shows. The sleeve of the near arm is drawn separately
- Back view (around 180): chest and face hide (only parts sticking out past the body outline show), and long hair is painted in front of the back. Feet take the shape of heels
- For large body turns, give the arms with `aim()`. Arms given as screen angles gather at the middle of the body in back views

```python
turn = 180
back = Pose(turn=turn, head_yaw=turn,
            left_arm=aim(turn, (-0.15, 1.0, 0.02), (-0.05, 1.0, 0.08)),     # slightly outward in the body's frame
            right_arm=aim(turn, (0.15, 1.0, 0.02), (0.05, 1.0, 0.08)),
            left_hand=HandSpec('relaxed', 'rest'), right_hand=HandSpec('relaxed', 'rest'))   # the hands turn with the body too
```

- 8-direction turnaround sheet: `scripts/examples/figure_turnaround.py [out] [female|male] [clothed|figure_study] [around|front]`
- Back-view scene example: `scripts/examples/figure_back_view.py`

## 7. Seated poses and foreshortening (aim)

Screen angles alone cannot show a thigh reaching toward the viewer. `aim(turn, upper, lower)` turns 3D directions in the body's frame into screen angles and length shares.

- Direction vectors are in the body's frame (x screen right, y down, z out of the front of the body)
- It returns `(upper angle, lower angle, upper length share, lower length share)`. Put it straight into the arms and legs of a Pose
- The result also carries how far each segment comes toward the viewer (`.forward`). When the wrist of the far arm comes more than 1.6 head units forward of its shoulder (folded arms, hugging the knees, holding a cup), the forearm and hand are painted in front of the body. Arms given directly as screen angles lack this, so a far arm hides behind the body

```python
turn = 30
seated = Pose(turn=turn, lean=4, head_yaw=turn * 0.8,
              left_leg=aim(turn, (0.04, 0.12, 1.0), (0.0, 1.0, 0.12)),      # thighs forward, shins down
              right_leg=aim(turn, (0.20, 0.12, 1.0), (0.04, 1.0, 0.08)),
              left_arm=aim(turn, (0.08, 1.0, 0.30), (0.05, 0.75, 1.0)),     # hands on the thighs
              right_arm=aim(turn, (-0.08, 1.0, 0.30), (-0.05, 0.75, 1.0)),
              left_hand=HandSpec('relaxed', 'back'), right_hand=HandSpec('relaxed', 'back'))
seat_y = pelvis_y + 0.80 * figure.unit                   # height of the top of the seat
```

- When a thigh swings more than 50 degrees from vertical, the pose counts as seated, and the buttocks and thigh roots are wrapped as one mass. The lower line resting on the seat comes out smooth
- Seated poses read best with the body turned 20-40 degrees. From the front (turn 0) the thighs point at the viewer and almost vanish
- Paint the chair before the figure
- Sitting on the floor with the knees up is `poses.sit_floor(knees_up=True)`. Buttocks and feet rest at the same floor height
- Complete example: `scripts/examples/couple_bench.py`

## 8. Zoom (framing)

One full-body rig makes full body, knee-up, waist-up, bust and face close-ups. What lies below the frame simply falls off the canvas, and the whole body is computed as usual.

```python
figure = Figure(**framing(cv.size, 'bust', center=0.5), pose=pose, sex='female', body_details=False)
```

| shot | Bottom edge of the picture |
|---|---|
| `full` | Margin below the soles |
| `knee` | Below the knees |
| `thigh` | Middle of the thighs |
| `waist` | Below the pelvis |
| `bust` | Below the chest |
| `face` | Below the chin |

- `center`: horizontal position of the body (0-1). `headroom`: room above the crown (head units, default 0.55)
- Based on a standing pose. For seated figures set `pelvis` and `height` yourself
- The closer the shot, the heavier lines and shading get by themselves (the `scale` of the look follows the head size)
- Complete example: `scripts/examples/figure_zoom.py`

## 9. Men

```python
man = Figure(pelvis=(500, 760), height=1330, sex='male', pose=Pose(turn=-30, head_yaw=-24))
```

- Build: broad shoulders and ribcage, straight waist, narrow pelvis, thick neck and limbs. The chest is drawn as pectorals
- Face `MALE_FACE`: small eyes (`eye_half_height` 0.074), light lashes (`lashes` 0.4), thick low brows (`brow_weight` 1.7, `brow_lift` -0.3), thin lips, no blush, broad jaw (`jaw` 1.06)
- Hair `MALE_HAIR`: short hair (`length` 0.62), short bangs combed sideways (`bangs='short'`), ears showing, with sideburns
- An Adam's apple is drawn on the neck
- To modify, pass a changed preset: `face=replace(MALE_FACE, eye_color='#5a4a3a')`, `hair=replace(MALE_HAIR, color='#6b4a3a')`
- 12 male hairstyles in section 16, 4 male face styles and the expressions in section 17
- Build tables and presets per sex are `_BUILDS`, `MALE_FACE`, `MALE_HAIR` in `fullbody.py`

## 10. Pose recipes and pose presets (poses)

Contrapposto (weight on one leg) is the basic way to make a standing figure look alive. Tilt the pelvis and shoulders in opposite directions and lay the spine over slightly.

```python
# weight on the leg on screen left, the right leg relaxed and forward
contrapposto = Pose(lean=-4, hip_tilt=9, shoulder_tilt=-7, head_tilt=7, head_yaw=-16,
                    left_leg=(2, 0), right_leg=(-10, 5), front_leg='right', right_foot=0.55)

# one hand on the hip: spread the upper arm out and bend the forearm in toward the body
hand_on_hip = dict(left_arm=(-30, 48), left_hand=HandSpec('relaxed', 'back'))

# one arm behind the head: upper arm up, forearm toward the head. The hand hides behind head and hair
arm_behind_head = dict(right_arm=(150, -78), right_hand=HandSpec('relaxed', 'palm'))

pose = replace(contrapposto, **hand_on_hip, **arm_behind_head)     # dataclasses.replace

# male contrapposto in three-quarter view: body turned toward the light, one hand at the waist
male_study = Pose(turn=-32, head_yaw=-26, lean=3, hip_tilt=-6, shoulder_tilt=5,
                  left_leg=(6, -2), right_leg=(8, 6), right_arm=(38, -55))

# lying pose seen from above (landscape canvas)
lying = Pose(roll=78, lean=8, left_leg=(-86, -72), right_leg=(-70, -100), left_arm=(40, 100),
             right_arm=(20, -60), head_tilt=-22, left_foot=-0.9, right_foot=-0.9)
```

- The leg under the raised hip carries the weight. That leg stays straight, the other bends at the knee

Pose presets live in `paintkit.figure.poses`. All are built with `aim()`, so the pose holds at any body turn. Each function takes `turn` and overrides the remaining Pose fields by keyword.

| Group | Function | Content |
|---|---|---|
| Standing | `contrapposto(turn=20)` | Weight on one leg, arms hanging |
| Standing | `arms_crossed(turn=15)` | Arms folded in front of the chest |
| Standing | `hands_on_hips(turn=10)` | Hands on the waist with elbows out |
| Standing | `hands_in_pockets(turn=15, pouch=False)` | Hands in the front trouser pockets. The arms reach the pockets by inverse kinematics. With `pouch=True`, hands in the hoodie's kangaroo pocket |
| Standing | `stretch(turn=0)` | Stretching with both arms above the head |
| Motion | `walk(turn=90, phase=0)` | One step of a walk. `phase` 0-1 is one stride. Reads best in profile (turn 60-90) |
| Motion | `run(turn=90, phase=0)` | Running. Knee lifted high, back foot kicked up, body leaning forward |
| Sitting | `cross_legged_seat(turn=30)` | Seated on a chair with legs crossed |
| Sitting | `squat(turn=40)` | Squatting. Arms on the knees |
| Sitting | `sit_floor(turn=50, knees_up=False)` | Sitting on the floor. Legs stretched out with hands propped behind (`False`), or knees drawn up and hugged (`True`) |
| Leaning | `lean_wall(turn=-25)` | Arms folded, shoulder against a wall. Leans away from the side the body faces |
| Lying | `lie_side()` | Lying on one side, head on the lower arm, upper hand at the waist. Head to screen right. For landscape canvases |

```python
from paintkit.figure import poses
walking = poses.walk(turn=75, phase=0.1)
seated = poses.cross_legged_seat(turn=-30, head_tilt=4)       # other Pose fields are overridden by keyword
hair_up = replace(poses.contrapposto(turn=22), right_arm=(150, -78), right_hand=HandSpec('relaxed', 'palm'))
```

- Sitting and lying presets draw no chair or floor. Paint the background where the buttocks or the underside of the body rest
- Poses with a rolled trunk (`roll`) such as `lie_side()` use screen angles for the limbs. `aim()` does not follow `roll`
- When the head tilts more than 25 degrees (lying poses), the hair stops hanging down and turns with the head, spreading over the pillow
- The bend at an elbow or knee is the difference between the two angles. (upper arm -30, forearm 48) bends 78 degrees
- After changing a pose, check the silhouette first with `cv.save()` and no finish
- To check the same character from several angles, make a turnaround sheet with `scripts/examples/figure_turnaround.py`

## 11. Garments (wardrobe)

Fitted clothes are cut out of the body masks by region, so they fit any pose and angle. Skirts are separate shapes hanging from the pelvis. List `garments` from the innermost layer out.

| Function | Main arguments |
|---|---|
| `top(color, neckline=0.55, hem=-0.90, sleeve=0.0, scoop=0.55)` | `sleeve`: length from the shoulder to the end of the sleeve (head units). 0 sleeveless (straps), 1.2 short sleeves, 4.6-4.9 long sleeves. `hem`: hem height in the pelvis frame (-2 waist, 0 hip joints). For a man's T-shirt `neckline=0.35, scoop=0.25` |
| `bottoms(color, waist=-1.15, length=1.0)` | `length`: share of the legs covered. 1 ankles, 0.5 knees, 0.2 shorts |
| `skirt(color, waist=-1.9, length=2.6, flare=0.45, folds=5)` | `length`: hem height in the pelvis frame (3.9 knees). `flare`: how far the hem spreads |
| `dress(color, neckline=0.60, length=2.4, flare=0.40)` | Top with straps + skirt |
| `swimsuit(color, neckline=0.80, leg_cut=0.5)` | One-piece swimsuit |
| `bikini(color, tie=None, rise=0.0)` | Triangle halter bikini and bottoms tied at the sides. The lower edge of the cups sits at the fold under the breasts, so the breasts do not slip out below the string. The neck string runs from the cup tip past the side of the neck to a bow at the nape, the under-bust string follows the fold linking both cups and runs to a bow on the back. The waistline of the bottoms runs from hip-bone height to the outline of the buttocks, and the side bows sit on the side seam of the hips. `tie`: string color. `rise`: height of the bottoms. Men get swim briefs only |
| `innerwear(color, lace='#f4eef2', bow=None)` | Bra and briefs. The waistline of the briefs runs from hip-bone height to the outline of the buttocks. Lace runs all the way round the waist and leg openings of the briefs, front and back, and along the top edge of the bra cups. A small bow at the front of the waist. `lace=None` for no lace. Men get briefs only |
| `hoodie(color, pocket=True, strings=True)` | Hooded sweatshirt. Long sleeves, ribbed cuffs and hem, kangaroo pocket, drawstrings, hood behind the neck (over the upper back from behind) |
| `crop_top(color, sleeve=1.0, scoop=0.45)` | Top ending above the navel. `sleeve=0` for a strappy crop top |
| `hot_pants(color='#5d7fae', waist=-1.25)` | Denim hot pants. Button, front pocket stitching, frayed hems, back pockets from behind |
| `suit(jacket, shirt='#f2f2ee', tie='#7a2a3a', trousers=None, buttoned=True)` | A full suit. Creased straight trousers, collared shirt, tie, jacket with lapels, pocket flaps and a button. Passed as one garment |
| `shoes(color)` | Simple shoes covering the feet |
| `long_coat(color, length=3.4, buttoned=True, belt=None, lapel=None)` | Knee-length winter coat. Wide lapels, buttons, pocket flaps, back seam. Falls almost straight from the hips and rests over the knees when seated. `buttoned=False` opens the front from below the chest to the hem. `belt`: color of a tied belt |
| `padded_jacket(color, hem=0.40, collar=True)` | Puffer jacket. Bulky body and sleeves divided by horizontal seams, with swelling light in each baffle. Stand-up collar, front zip |
| `scarf(color, stripe=None, tail=True)` | Knitted scarf wound twice round the neck. The wraps sag a little at the front and show knit ribs. One end hangs down the chest on the side nearer the viewer, with a fringe at the tip. `stripe`: color of bands across the end. `tail=False` for the wraps only |
| `beanie(color, cuff=True, pompom=None)` | Knitted beanie. Covers down to above the brows and the tops of the ears, with a folded cuff and vertical ribs. `pompom`: pompom color. Painted after the head and the hair |
| `boots(color, height=0.45, sole='#2a2624')` | Boots over the feet and shins. `height`: share of the shin covered (0.15 ankle boots, 1 knee-high). Passed after the trousers, the trousers go inside the boots |

Combination examples

| Outfit | `garments` |
|---|---|
| Bikini | `[wardrobe.bikini('#e8505a', tie='#fbf4ea')]` |
| Innerwear | `[wardrobe.innerwear('#7a2a4a', lace='#f4e6ea')]` |
| Hoodie and jeans | `[wardrobe.bottoms('#2f3a52'), wardrobe.hoodie('#c8b48a'), wardrobe.shoes('#f0eee8')]` |
| Crop top and hot pants | `[wardrobe.hot_pants(), wardrobe.crop_top('#f6f2ea'), wardrobe.shoes('#f4f4f4')]` |
| Suit | `[wardrobe.suit('#2b2f3a', tie='#7a2a3a'), wardrobe.shoes('#1e1a18')]` |
| Winter coat | `[wardrobe.bottoms('#2f3138'), wardrobe.top('#d8d2c8', sleeve=4.9, scoop=0.2), wardrobe.long_coat('#5b4a3e'), wardrobe.scarf('#8a2f35', stripe='#e8e0d4'), wardrobe.boots('#2a2420', height=0.5), wardrobe.beanie('#3f4a5a', pompom='#e8e4dc')]` |
| Padded jacket | `[wardrobe.bottoms('#3a3d48'), wardrobe.padded_jacket('#2f3b2f'), wardrobe.boots('#3b3029', 0.2), wardrobe.beanie('#7a2f2f')]` |

```python
garments = [wardrobe.skirt('#2d3350', length=3.0, flare=0.32), wardrobe.top('#d9c8a8', sleeve=4.9, hem=-1.7)]
masks = draw_figure(cv, replace(figure, body_details=False), garments)
```

- Arms and hands lie in front of every garment except sleeves
- When the body turns, necklines and straps turn along the body surface, and the neck lies in front of the collar
- The neckline of a sleeved top is computed as a ring around the neck (low by `scoop` at the front, below the nape at the back). In profile and back views only the part of the ring facing the viewer becomes the collar line
- Straps of a sleeveless top are drawn on the chest side from the front, on the back from behind, and on both from the side
- Trousers fill small enclosed gaps between the legs
- `bottoms(straight=True)` gives straight trousers that fall straight below the knee
- `top(close=True)` fills narrow gaps between a loose sleeve and the body with cloth (suit jackets)
- A number such as `top(close=1.2)` also fills enclosed gaps smaller than that area (square head units) (hoodies). Wide gaps such as the inside of an arm with the hand on the hip stay open
- `top(cut=function)` makes a top cut open at the front. The function takes `(cv, skeleton)` and returns the mask to cut out (the V of the `suit` jacket)
- `top(extend=function)` joins an area outside the body to the top and paints them as one garment. The function takes `(cv, figure, skeleton, masks)` and returns a mask (the skirt of `long_coat`)
- `top(seal=0.05)` fills thin seams left where two heavily inflated parts meet (coats, padded jackets)
- Pass outerwear after the clothes it covers: trousers, top, outerwear, scarf, boots, beanie
- Headwear gets the attribute `over_head = True` on its garment function. `draw_figure` paints it after the head, the hair and tied hair (`beanie`)
- `HandSpec('pocket')` draws no hand and tucks the area around the wrist under the clothes. A hand in a front trouser pocket
    + The arm angles are ignored and recomputed by two-joint inverse kinematics from the shoulder to the pocket opening. The elbow bends out and back
    + `HandSpec('pouch')` puts the hand into the side opening of a hoodie's kangaroo pocket the same way. A sleeve crossing the front of the body is drawn as its own form
    + With a long top that covers the hips (a hoodie), `pocket` makes the hand vanish under the top. Use `pouch` for hoodies
- Small pieces of cloth on the body surface, such as bikinis and innerwear, are drawn separately on the front and back of the body, so they turn with it
    + Bikini and innerwear bottoms split the body surface between waistline and leg openings into narrow strips, project them and cut them with the body mask. So the waistband reaches the outline of the buttocks from any angle
    + When the body turns, the side seam nearer on screen divides the front piece from the back piece
    + A third value (lift) on a string point raises it off the body surface. A string starting from a raised cup tip settles onto the skin
    + Lace on briefs is drawn only along stretches facing the viewer. Lace on stretches turned behind the body would otherwise show over the cloth in front
    + `fullbody.under_bust(figure)` returns the chest-frame y of the fold under the breasts. The reference height for the lower edge of cups and for under-bust strings
- Skirts and dresses follow seated poses by themselves. When the thighs swing far from straight down, the skirt rests over the thighs
    + Seated, `length` is measured along the thighs. Longer than 3.9 (knees), the rest hangs down from the knees
    + Example: `scripts/examples/couple_bench.py [out] [illustration|anime] skirt`
- For a new garment, build regions from the part masks in `masks` and `skeleton.chest.pt(x, y)`, `skeleton.chest.surface(x, y)`, `skeleton.pelvis.round_pts(points)`, and cut them the same way
- Chest frame y: 0 the pit of the neck, 1.4 the center of the chest. Pelvis frame y: -2.05 waist, -1.3 navel, 0 hip joints, 0.7 crotch

## 12. Figure studies

- The rig draws the surface forms of the body. The crotch is treated as a soft shadow. It has no function for drawing pelvic forms
    + Women: collarbones, breasts, chest marks, center line of the belly, navel, lower pelvis creases, knees, toes
    + Men: collarbones, lower line of the pectorals, small chest marks, horizontal segments and edges of the rectus abdominis, iliac furrows (stopping above the crotch), serratus, Adam's apple
    + Back views (both): spinal groove with the muscles beside it, shoulder blades, lower-back dimples, the cleft and lower folds of the buttocks, creases behind the knees
    + Surface marks fade as they turn from the viewer and vanish beyond the outline
- Do not draw unclothed figures or sexual acts involving minors
    + Two grounds decide it: a character stated to be a minor (an age set under 18, or designated as a child), and a depiction of a body before secondary sexual characteristics (child build and proportions)
- Elements that make it convincing, in order
    + Pose: contrapposto and an S-shaped flow, three-quarter view (`turn` 25-35)
    + Light: `replace(ILLUSTRATION, light=(-0.65, -0.75), light_height=0.55, shade_depth=1.25)`. A lower `light_height` brings out the curves and muscles of the body more deeply
    + Background: dark and simple. A large value difference from the body
    + Rim light: a cool `add_rim_light` on the shadow side
- Long hair (`side_length` 2.0 or more), cloth or the position of the arms can be used to cover
- Complete example: `scripts/examples/figure_study.py [out] [illustration|oil] [female|male]`

## 13. Hands

```python
from paintkit.figure import HandSpec, draw_hand
draw_hand(cv, wrist=(400, 600), direction_deg=180, length=260, skin='#f3cdb6', look=look,
          spec=HandSpec('peace', 'back'), thumb_side=1, forearm=0.5)
```

| Argument | Meaning |
|---|---|
| `wrist` | Center of the wrist px |
| `direction_deg` | Direction the fingertips point (0 down, 180 up) |
| `length` | Wrist to the tip of the middle finger px |
| `spec.pose` | `open`, `relaxed`, `fist`, `point`, `peace`, `thumbs_up` |
| `spec.view` | `back` back of the hand (nails, knuckles), `palm` palm (palm lines) |
| `spec.roll` | Angle the hand is turned about its length axis. 0 flat, 90 a hand seen from the side. Positive turns the thumb side toward the viewer |
| `spec.nails` | Nail polish color. An empty string for natural nails |
| `thumb_side` | +1 when the thumb is on screen right with the fingertips pointing down, -1 otherwise |
| `forearm` | Length of forearm drawn behind the wrist (multiple of the hand length). For hand studies |

- Turning the hand reveals the thickness of the palm, the bent fingers and the front-back depth of the thumb from the side. Seen from the side, the fingers curl toward the palm over a thin palm
    + A relaxed thumb gathers in front of the palm along the index finger as the hand turns
    + The gaps between the fingers narrow as the hand turns
    + Folded fingers, seen from the side, curl into the palm as loops
- In the full-body rig, do not give `roll` directly. The hand turns by itself from the body direction and `view`
    + `back`: a hand placed to show its back from the front. When the body turns, its edge shows from the side and its palm from behind
    + `palm`: a hand placed to show its palm from the front
    + `rest`: the natural hand of a hanging arm. The palm faces the thigh. From the front and back an oblique side view, from the side the back of the hand. Recommended for hanging hands in pictures where the body turns
- New hand shapes are added to `paintkit.figure.hand.POSES` as `(thumb, index, middle, ring, little bend 0-1), spread 0-1, thumb reach 0-1`. Bends above 0.7 are drawn as folded fingers
- Match the look's `scale` to the hand size: `replace(look, scale=length / 260)`
- Complete example: `scripts/examples/hand_study.py`

## 14. Returned values

The dict returned by `draw_figure`.

| Key | Content |
|---|---|
| `all` | Mask of the whole figure |
| `skin` | All skin |
| `torso`, `neck`, `left_leg`, `right_leg`, `left_foot`, `right_foot`, `left_arm`, `right_arm`, `left_hand`, `right_hand`, `left_breast`, `right_breast` | Part masks (for men `_breast` is the pectoral). The far arm and hand masks leave out the parts the body hides |
| `garment_0`, `garment_1`, ... | Garment masks (in list order) |
| `face`, `eyes`, `front_hair`, `back_hair` | Head parts |
| `tie` | Tied hair (ponytail, braid, bun). None or an empty mask without one |
| `skeleton` | Joint positions such as `skeleton.joints['left_wrist']`, the `chest` and `pelvis` frames, `head` |

Joint names: `pit`, `neck_base`, `neck_top`, and `left_`/`right_` + `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle`.
To put a prop in a hand, draw it near `skeleton.joints['right_wrist']`. `fullbody.far_side(pose)` tells the far side when the body is turned (`'left'`, `'right'`, None). `fullbody.in_pocket(pose, name)` tells whether that hand is in a pocket (`pocket`, `pouch`).

## 15. Placing figures in a scene and composition (fit, thirds, group)

- Lay the floor shadow first: `cv.tint(blur(cv.ellipse(x, floor_y, 300, 30), 18), '#120e12', 'multiply', 0.75)`
- In perspective scenes the camera sets the size (`references/city.md`)

```python
scale = view.scale_at(x_m, 0.0, z_m)                  # how many px 1 m is at that spot
figure = Figure(pelvis=view.project(x_m, 0.90, z_m), height=1.70 * scale, ...)
```

- In two-point scenes (`city.Camera`) match how far the figure faces the camera with `turn`

Scenes without perspective place figures with the layout helpers. All three return `pelvis`, `height` to pass straight into `Figure(**...)`.

| Function | Content |
|---|---|
| `fit(box, pose, sex='female', align='bottom', scale=1.0)` | Fits a posed figure into the box `(x0, y0, x1, y1)` as large as possible. Centered across, aligned to the bottom (`bottom`) or the middle (`center`) vertically |
| `thirds(size, column='left', margin=0.06)` | Box centered on a rule-of-thirds line (`left`, `center`, `right`). Pass it to `fit` |
| `group(box, poses, sexes, scales, gap=0.04, shot=None, headroom=0.55)` | Places several figures side by side on one floor line at one scale. `scales`: relative heights (men 1.0, women 0.94). A negative `gap` overlaps them. With `shot` (`waist`, `thigh`, `bust` and so on) the largest figure fills the box height at that shot and the floor line falls below the picture. When the row is wider than the box, the shot loosens accordingly |
| `pose_bounds(figure)` | Screen box a figure occupies. Includes hair, hands and feet |

```python
from paintkit.figure import fit, group, thirds
pose = poses.contrapposto(turn=22)
x0, _, x1, _ = thirds(cv.size, 'left')                          # standing on the left third line
figure = Figure(**fit((x0, 120, x1, 1330), pose), pose=pose, body_details=False)

man, woman = poses.arms_crossed(turn=30), poses.hands_on_hips(turn=-35)
places = group((260, 80, 1300, 1050), [man, woman], sexes=['male', 'female'], scales=[1.0, 0.94], gap=0.10)
pair = [Figure(**places[0], pose=man, sex='male'), Figure(**places[1], pose=woman)]

trio = [poses.contrapposto(turn=30), poses.hands_in_pockets(turn=5), poses.arms_crossed(turn=-30)]
places = group((40, 60, 1160, 1500), trio, sexes=['female', 'male', 'male'], scales=[0.95, 1.0, 1.02],
               gap=-0.10, shot='waist', headroom=0.6)   # aims at a waist shot. Three on a portrait canvas loosen to a knee shot to fit the width
```
- In an overlapping group picture, paint the middle figure last to stand it in front

- The bottom of the box is the floor line the feet stand on. Lay floor shadows on the floor line below `figure.pelvis[0]`
- For lying figures put the bottom of the `fit` box 0.4-0.5 head units below the surface. It includes room for standing feet
- Scene examples per outfit: `beach_bikini.py`, `bedroom_innerwear.py`, `hoodie_street.py`, `summer_street.py`, `office_suits.py`
- Scene examples per cast size and framing: `station_platform.py` (two-shot), `park_group.py` (5 people, standing and seated), `picnic.py` (two-shot seated on the ground), `group_portrait_oil.py` (overlapping waist shot of three)

## 16. Hairstyles (hairstyles)

```python
from paintkit.figure import hairstyle

figure = Figure(**framing(cv.size, 'bust'), hair=hairstyle('ponytail', color='#3a2a24'))
man = Figure(**framing(cv.size, 'bust'), sex='male', hair=hairstyle('two_block'))
```

- `hairstyle(name, **changes)` returns a copy of a named `HairSpec`. Pass any argument to change it: color, `seed`, length and so on
- The tables are `FEMALE_STYLES`, `MALE_STYLES` and both combined in `HAIRSTYLES`. The names describe only the cut, so they work regardless of sex
- Sheet: `scripts/examples/hairstyle_catalog.py [out] [female|male]` (in the order of the tables below, front three-quarter on top, back three-quarter below)

| Women | Shape |
|---|---|
| `long` | Long straight hair with light bangs (the default `HairSpec`) |
| `long_wavy` | Bangs swept to the side, long wavy hair |
| `center_long` | Center parting, curtain bangs, long hair |
| `hime` | Straight-cut bangs, side locks cut at the cheeks, long hair |
| `bob` | Bob with straight-cut bangs |
| `pixie` | Very short hair with bangs swept to the side |
| `ponytail` | High ponytail, locks framing the face |
| `low_ponytail` | Low ponytail tied at the nape |
| `braid` | A single braid falling from the nape |
| `bun` | High bun behind the crown, open forehead |
| `low_bun` | Center parting, chignon at the nape |
| `half_up` | Half-up with only the top hair tied small |

| Men | Shape |
|---|---|
| `buzz` | Buzz cut. The whole head clipped short, the scalp showing through |
| `crew` | Crew cut. Short top, sides and back tapering shorter |
| `side_part` | Short hair with a side parting (same as `MALE_HAIR`) |
| `fringe` | Light bangs covering the forehead (dandy cut) |
| `two_block` | Two-block cut. Sides and back clipped short under a full top |
| `comma` | Bangs swept to the side, curving above the brows (comma hair) |
| `center_part` | Bangs with a center parting |
| `slicked_back` | Slicked back from an open forehead |
| `spiky` | Hair standing up with pointed bangs |
| `shoulder` | Shoulder-length long hair with a center parting |
| `man_bun` | Combed back and tied in a bun behind the crown |
| `low_tail` | Combed back and tied in a short tail at the nape |

- Ponytails and braids hang under gravity, swing a little to one side and rest on the back. When the head tilts a lot (more than 25 degrees), they turn along by the remaining angle
- For running or wind, `hairstyle('ponytail', flow=0.7)`. Tails and braids stream back behind the head, the ends drooping a little and rippling (0 hangs .. 1 level)
- Buns are fixed to the head and turn with it
- From the front a high ponytail shows only a little beside the neck. To show the tail, turn the head or the body 30 degrees or more

## 17. Face styles and expressions (expressions)

```python
from paintkit.figure import expression, face_style

face = expression(face_style('female', 'sharp', eye_color='#5a4a3a'), 'tired')
figure = Figure(**framing(cv.size, 'face'), face=face)
calm = expression(face_style('male', 'plain'), 'smile', amount=0.5)
```

| Sex | Style | Impression |
|---|---|---|
| Women | `soft` | Default (`FEMALE_FACE`) |
| Women | `sharp` | Narrow eyes with lifted outer corners, light blush |
| Women | `mature` | Slightly smaller eyes, deeper lips, lower brows |
| Women | `bright` | Large eyes, level outer corners, a bright smile |
| Men | `plain` | Default (`MALE_FACE`) |
| Men | `sharp` | Narrow eyes, lifted outer corners, low brows |
| Men | `gentle` | Slightly larger eyes, higher brows, a faint smile |
| Men | `rugged` | Small eyes, very thick low brows, slightly deeper skin |

| Expression | What changes |
|---|---|
| `neutral` | Level mouth corners |
| `smile` | Raised mouth corners, lower lids raised a little |
| `grin` | Wide open mouth with upper teeth, smiling eyes |
| `sad` | Brows raised at the inner ends, drooping mouth corners, lowered gaze |
| `angry` | Brows lowered at the inner ends, drooping mouth corners, lids lowered a little |
| `surprised` | Raised brows, wide open eyes, mouth open in a round shape |
| `tired` | Half-lowered lids, lowered gaze |
| `pensive` | Lowered lids, gaze down to the side, no eye contact |

- `expression(face, name, amount)`: mouth, lids, gaze and brow tilt change to target values, and the brow height is added to the face's own value. So a man's low brows stay low in every expression
- `amount` 0 .. 1 blends from the original face to the expression. On/off values such as `eye_contact` switch at 0.5
- Straight-cut bangs hide the brows. To keep brow expressions visible, use a hairstyle that shows the forehead, such as `center_long` or `side_part`
- Sheet: `scripts/examples/expression_sheet.py [out]` (rows: the order of the table above, columns: female soft, female sharp, male plain, male rugged)
- `tired`, `pensive`, `neutral` suit doomer mood scenes

## 18. Limits

- There are no poses bending forward or backward (bending at the waist). `lean` only tilts within the picture plane
- Clothes are fitted forms. Cloth blowing in the wind or folding deeply, and the tails of an unbuttoned shirt, are not available
- Hot pants seen from the side join between the legs with cloth and look like a short skirt
- Strong foreshortening (an arm reaching at the camera and the like) is imitated by the length shares of `aim()`, with no change in size toward the end
- In poses with an arm behind the body, only the far arm is hidden by the body. There is no pose bringing the near arm behind the back
- Hands support rotation about the wrist axis. Foreshortening with the fingertips pointing at the viewer is not available. A hand holding an object is shown as `fist` with the prop layered over it
- Seated skirts are convex forms wrapping thighs and knees. Cloth sagging from crossed or spread legs is not available
- Tails of tied hair do not compute collisions with arms, clothes or chair backs. In poses leaning back, check the position of the tail by eye
- The figure size computed by `fit()`, `group()` leaves out the height of a high bun. When the bun is cut off, increase `headroom` or the room above the box
- Only one end of the scarf hangs in front. Both ends hanging, or an end thrown over the shoulder, are not available
