# Figures

Read this document when drawing full figures, half figures and hands. It covers the body rig `codepaint.figure` and the workflow for figure pictures.

## Contents

- How the rig works
- Setting a pose
- Verified poses
- Part outlines and paint order
- Body marker coordinates
- Clothes
- Hands and feet
- Painting skin by style
- Figure studies
- Lower body markers
- Male markers
- 3D rig
- Head and hair by angle
- Face and hair templates
- Painting 3D figures
- Outfits
- Two-shots and the stage
- Common defects

## How the Rig Works

- People are sensitive to body proportions, so joint coordinates written by eye look wrong at once
- `figure.Figure` fixes bone lengths to eight-head proportions and takes only the pose as angles
    + Limb lengths and torso proportions hold in any pose
- The unit is the head height and the origin is the pelvis center
    + Standing, the crown is 3.85 above the pelvis center and the ankles 3.85 below
- Left and right follow the screen
    + `_l` is screen left, `_r` is screen right
- The planar rig handles front and back views
    + For 3/4 views, profiles and limbs swung forward and back, use `figure3d.Figure3D` (3D rig below)

```python
from codepaint import figure
from codepaint import geometry as g

BODY = figure.Figure(
    g.Frame(origin=(560, 1010), unit=236),      # screen coordinates of the pelvis center, screen length of the head height
    build=figure.FEMALE,                        # or figure.MALE, figure.Build(...)
    hip_tilt=-12, chest_tilt=9, spine=-5, neck=-4, head=-13,
    arm_l=(140, 290), arm_r=(10, -16), leg_l=(4, -6), leg_r=(-4, 2),
    stretch={"thigh_l": 0.96})
```

## Setting a Pose

| Argument | Meaning | Convention |
|---|---|---|
| `hip_tilt`, `chest_tilt` | Tilt of the hip line and shoulder line | Positive lowers the screen-right side |
| `spine`, `neck`, `head` | Tilt of spine, neck and head | Vertical is 0, positive tilts toward screen right |
| `arm_l`, `arm_r` | (upper arm, forearm) angles | Down is 0, positive points away from the body. 90 is horizontal, 180 overhead |
| `leg_l`, `leg_r` | (thigh, shin) angles | Down is 0, positive points away from the body |
| `stretch` | Bone length factors | Set like `{"upper_arm_r": 0.62}`. Shortens limbs reaching toward the screen |
| `shoulder_drop` | Distance that lowers the shoulder joints (head heights) | Default 0. 0.12 keeps the upper arm caps from rising above the shoulder line. Recommended for new pictures |

- All limb angles are absolute
    + The forearm angle is the screen direction of the forearm, independent of the upper arm
    + Negative values point toward the body. A forearm folded across the chest is about -120
    + Past 180 the arm passes overhead and over to the inside. A forearm swept behind the head is about 290
- Tilting the hip line and shoulder line in opposite directions gives a pose with the weight on one leg
    + The hip on the weight-bearing side rises and the shoulder on that side drops
- After setting the pose, render a mannequin with dots on the joints first to check it
    + `BODY.joint("elbow_l")` returns the screen coordinates of the joint

## Verified Poses

Values verified by rendering the examples. Start new poses from the nearest values and adjust.

| Pose | Arguments | Example |
|---|---|---|
| Weight on one leg (screen-right leg) | `hip_tilt=-12, chest_tilt=9, spine=-5, leg_r=(-4, 2), leg_l=(4, -6)` | `oil_figure_study.py` |
| Walking toward the viewer | `hip_tilt=7, chest_tilt=-5, leg_l=(-3, 1), leg_r=(6, -4), stretch={"shin_r": 0.82}` | `illustration_autumn_walk.py` |
| Arm raised with the hand behind the head | `arm_l=(140, 290)` | `oil_figure_study.py` |
| Hand raised beside the forehead | `arm_r=(52, 203), stretch={"upper_arm_r": 0.62, "forearm_r": 0.92}` | `anime_sky_pilot.py` |
| Holding an object in front of the chest | `arm_r=(14, -128), stretch={"forearm_r": 0.82}` | `illustration_autumn_walk.py` |
| Hanging arm | `arm_l=(13, 6)` | `illustration_autumn_walk.py` |
| Full-body reference stance (front) | `hip_tilt=-6, chest_tilt=4, spine=-1, head=-3, arm_l=(11, 5), arm_r=(13, 3), leg_l=(6, 1), leg_r=(3, -1), stretch={"neck": 0.72}, shoulder_drop=0.12` | `anime_figure_base.py` |
| Lying on the side with the back shown | `g.Frame(..., rotate=-90)`, `hip_tilt=9, chest_tilt=-9, spine=7, leg_r=(-15, -2), leg_l=(7, 22)` | `oil_reclining_figure.py` |

- Reclining poses rotate the Frame of a standing rig by 90 degrees
    + With `rotate=-90` the head points to screen left and the rig's `_r` side becomes the top of the screen
    + The width differences of shoulders, waist and pelvis become the undulations of the upper contour as they are
    + Put the far edge of the couch a little below the body's center line and lay a contact shadow under the body, or the body floats

## Part Outlines and Paint Order

| Call | Returns |
|---|---|
| `BODY.torso()`, `BODY.neck()`, `BODY.head()` | Torso, neck and frontal head outlines |
| `BODY.limb(bone, side, scale=1.0)` | bone is `upper_arm`, `forearm`, `thigh` or `shin`. side is `"l"` or `"r"` |
| `BODY.foot(side, view="front")` | Foot. view is `"front"` (where a shoe goes), `"side"`, `"bare_front"` (bare foot with toes) or `"bare_back"` (heel) |
| `BODY.parts()` | Dict of the parts above by name |
| `figure.shape_of(canvas, paths)` | Merges several overlapping outlines into one shape without holes |

- Every outline method returns a list of paths
    + Joining several parts with `+` and passing them to `figure.shape_of` gives one mass
    + Passing them straight to `canvas.shape(*paths)` cuts holes where they overlap, so use `shape_of`
- The order is back to front
    + Default for the front view: back hair, limbs behind, neck, legs, torso, arms in front, head, bangs
    + An arm crossing in front of the body is drawn behind the torso
- Connected parts are merged and painted as one mass, or seams appear at the joints
    + Group neck, torso and upper arms, thighs and shins
    + At elbows and the lower pelvis, where separately painted parts meet, a soft skin-colored ellipse covers and loosens the seam

## Body Marker Coordinates

`BODY.on_thorax(x, y)` uses thorax coordinates with the middle of the shoulder line as origin, and `BODY.on_pelvis(x, y)` pelvis coordinates with the pelvis center as origin. Markers follow when the body tilts. Values are from the female build example.

| Marker | Coordinates |
|---|---|
| Hollow at the base of the neck | thorax (0, 0) |
| Collarbones | thorax (±0.09, -0.03) to (±0.62, -0.05) |
| Breast center | thorax (±0.35, 0.68), radius 0.3 |
| Rib arch | thorax (±0.06, 1.04) to (±0.5, 1.5) |
| Navel | pelvis (0, -0.72) |
| Hip bone corners | pelvis (±0.52, -0.42) |
| Lower pelvis creases | pelvis (±0.6, -0.3) to (±0.1, 0.34) |
| Spine groove (back) | thorax (0, -0.3) to pelvis (0, -0.2) |
| Shoulder blades (back) | thorax (±0.36, 0.42) |
| Sacral dimples (back) | pelvis (±0.17, -0.27) |
| Buttock center (back) | pelvis (±0.4, 0.16), radius 0.42 |

- The face is drawn on `BODY.head_frame()`. The unit is the head height and the origin the head center
    + Eye centers (±0.165, -0.02), brows y -0.12 to -0.165, under the nose y 0.2, mouth y 0.26 to 0.335
- Anime faces switch to a frame with the skull radius as 1
    + `g.Frame(BODY.head_frame().point(0, -0.08), unit=head_height / 2.37, rotate=head_angle)`
    + Facial part coordinates come from the proportion tables in `references/craft.md`

## Clothes

- Clothes on figures at an angle use the `garment` module (Outfits below). This section covers clothes on frontal planar rig pictures
- Sleeves and trouser legs thicken the limb outlines with `BODY.limb(bone, side, scale=1.25-1.5)`
- Tops, coats and skirts join `on_thorax` and `on_pelvis` points with a spline
    + Shoulders 0.12-0.14 wider than `build.shoulder`, flanks 0.2 wider than `build.ribcage`
    + The frame follows the body tilt, so the clothes tilt with the pose too
- Read build values from `BODY.build.shoulder`, `ribcage`, `waist` and `hip`
- Flowing things such as scarves, long hair and capes use `g.ribbon(center line, width list)`

## Hands and Feet

```python
hand = figure.hand_open(BODY.hand_frame("r", turn=-38), spread=0.45, curl=(0.22, 0.26, 0.3, 0.36), thumb=0.7)
hand = figure.hand_side(BODY.hand_frame("l", flip=True), curl=0.3)
shape = figure.shape_of(cv, hand.paths())          # silhouette of the whole hand
finger = figure.shape_of(cv, hand.parts["index"])  # one part
```

| Call | Use |
|---|---|
| `hand_open(frame, spread=1.0, curl=0.0, thumb=1.0, view="back")` | A hand seen from the back or the palm. Waving, pointing, fists |
| `hand_side(frame, curl=0.25)` | A hand seen from the thumb side. Hanging hands, holding hands |
| `BODY.hand_frame(side, turn=0.0, flip=False)` | Hand frame attached to the wrist. turn bends the wrist, flip switches between left and right hands |

- curl is 0 for an open hand and 1 for a fist
    + The curl of `hand_open` is one value or four values in the order index, middle, ring, pinky
    + A pointing hand is `curl=(0.0, 0.85, 0.9, 0.92)`
    + A hanging hand is `hand_side(curl=0.3)`, a hand holding an object `hand_side(curl=0.6-0.8)`
- Parts are `palm`, `pinky`, `ring`, `middle`, `index` and `thumb`
    + Seen from the back, draw them in this order. Seen from the palm, draw thumb after palm
    + Paint each part separately and outline it with `edge_light`, or the fingers do not separate
- `hand.joints[name]` holds the joint coordinates from root to tip
    + Used for knuckle creases and nails. See `examples/watercolor_hand_studies.py`
- Held objects are drawn between the palm and the fingers
    + Draw the object first and lay the fingers on top
- Covering hands with gloves, cuffs or pockets reduces the detail load
- A hand is three quarters of the head height on screen
    + In compositions enlarged beyond that, the knuckle contours look simple

## Painting Skin by Style

| Style | Method |
|---|---|
| Anime style | On the merged mass: base color, a first shadow with `form_shadow` (soft 0), outer outline with `canvas.contour`. Collarbones, ribs and hip bones are inner lines thin at both ends |
| Oil style | Per mass: base color, soft shade (`form_shadow(soft=0.4)`), deep shade, light side (`form_light(soft=0.5)`), reflected light on the shaded side (`edge_light`) |
| Watercolor style | After a white base wash, lay skin color with MULTIPLY and glaze the shade once more |
| Illustration style | Flat skin color with `form_shadow(soft=0.4)` at `grain=1.0` |

- Skin shade is red-brown, and the deepest shade dark red-brown
    + A thin red reflected light on the shaded contour turns the skin round
- Bone and muscle markers are elliptical blotches with loosened edges and no outlines
    + `cv.fill(cv.shape(g.ellipse(...), soft=...), color, opacity=0.3-0.6, clip=mass)`

## Figure studies

- Subjects are limited to adults and carry all of the adult markers below
    + Body: eight-head rig and an adult build (`figure.FEMALE`, `figure.MALE` or an equivalent Build)
    + Face: small eyes and a long jaw. Anime style uses the adult female or adult male face table in `references/craft.md`
    + Markers: a defined nose and colored lips, inner lines of collarbones, ribs and hip bones
    + Context: no elements that suggest a minor, such as school uniforms, school bags or children's items
    + If any marker is missing and the figure could read as a minor, unclothed figures and appeal-focused poses are not applied
- All four styles are possible
    + In anime style the face markers above matter most. Large eyes and a short jaw look young at once
- The scope is figure work in painting, illustration and anatomy plates
    + The full-body reference (base) is drawn from head to toe without covering, because it is the reference for clothes and other poses
    + The forms and values of breasts, back, buttocks, pelvis and thighs are drawn
    + The lower pelvis of the full-body base examples is rendered at the level of classical sculpture and anatomy plates. The female has the round form where the lower pelvis creases meet (mons pubis), the male only light and shade on a small round mass without detail
    + Scene pictures may also cover with cloth, pose or a back view
- Appeal comes from the curves of the pose
    + Tilt the hip line and shoulder line strongly in opposite directions for an S-flow in the torso
    + Use a Build with a larger difference between waist and pelvis widths. The example uses `Build(shoulder=0.70, ribcage=0.61, waist=0.50, hip=0.83, ...)`
    + Raised arms, swept hair and falling cloth continue the curves
- Keep the skin the lightest and warmest mass in the frame
    + Dark background, cloth in a cool color on the complementary side of the skin
    + With the lit side of the body against a dark background and the shaded side against a light one, both contours read
- Lower the oil pass to `relief=0.4` and `color_jitter=0.035` to keep the skin smooth
- Anime order: back hair → arm swept behind the head → whole-body merged mass → designed shadows (under the jaw, armpit, under the breasts, the folded side of the waist) → breasts → inner lines → face → bangs → cloth → hands
    + Merge torso and legs into one mass, or a mass border appears below the pelvis
    + The under-jaw shadow uses the face frame so it stays on the jaw when head size and neck length change
    + In compositions with the back to a window or lamp, put a rim light on the contour with `anime.rim_light` to separate the body from the background
- Examples: `examples/oil_figure_study.py` (oil standing front view), `examples/oil_reclining_figure.py` (oil reclining back view), `examples/anime_city_window.py` (anime standing front view), `examples/anime_figure_base.py` (anime full-body base front and back), `examples/anime_figure_base_male.py` (anime male full-body base), `examples/anime_turnaround.py` (male and female five-angle turnaround and pose sheet)

## Lower Body Markers

Values verified in `examples/anime_figure_base.py`. Coordinates are `on_pelvis` (origin at the pelvis center, in head heights) for the adult female build.

| Marker | Front | Treatment |
|---|---|---|
| Hip bone corners | (±0.54, -0.44) | Tall vertical light |
| Lower pelvis creases (V line) | (±0.6, -0.44) to (±0.08, 0.44) | Inner lines thin at both ends. The lower ends meet at the mons pubis |
| Mons pubis | center (0, 0.3) | Light on top with radius 0.16×0.12, soft shade below between (±0.16, 0.4) and (±0.05, 0.58) |
| Between the thighs | Below the lower pelvis | Spread the legs slightly as in `leg_l=(6, 1), leg_r=(3, -1)` to leave a small gap |
| Inner thighs | From the hip joint to the inner knee | Soft shade along the inside of the legs |
| Outer thighs | From 0.3 outside the hip joint to 0.14 outside the knee | A weak line along the muscle border |
| Knees | Knee joint | Kneecap light, a short arc below it, a short line on the inner knee |
| Ankle bones | Ankle | The inner ankle bone is higher than the outer |
| Feet | `foot(view="bare_front")`, `toes(side)` | After the foot mass, paint the 5 toes one at a time from the little toe and add outlines and nails. Tendon lines on the instep |

| Marker | Back | Treatment |
|---|---|---|
| Lower back dimples | (±0.17, -0.27) | Small soft shade dots |
| Buttocks | center (±0.39, 0.18), radius 0.43×0.41 | Only shade and light on top, without repainting the base |
| Buttock cleft | (0, -0.22) to (0, 0.56) | A line that thickens downward |
| Crease under the buttocks | (±0.05, 0.56) to (±0.6, 0.5) | A line with soft shade below it |
| Back of the knees | Knee joint | A horizontal crease and short lines of the tendons on both sides |
| Calves | 0.45 below the knee | Tall vertical light |
| Heels | `foot(view="bare_back")` | Round light and the Achilles tendon line |

- Include palms and feet in the body mass, or the outline breaks at the wrists and ankles
    + Finger and toe separation goes on after the mass, as inner lines and per-finger outlines
- A hanging hand has the palm toward the thigh. `hand_frame(side, flip=(side == "r"))`
- Eight-head check: with `stretch={"neck": 0.72}` and bare feet, crown to toe tip is about 8.04 head heights
- Toes merged into the body mass alone are buried inside the outline and disappear
    + Paint each toe returned by `toes()` separately and outline it with `canvas.contour` to separate them
    + When a toe would be narrower than 5px on screen, omit the toes and simplify to one toe line

## Male Markers

Values verified in `examples/anime_figure_base_male.py`. The workflow matches the female base, with more muscle markers and crisper lines.

- Build: `Build(shoulder=0.94, ribcage=0.8, waist=0.64, hip=0.7, arm=1.06, leg=1.0, neck=0.46)`, `shoulder_drop=0.14`
    + An inverted triangle with shoulders much wider than the pelvis. The waist curve is small
    + Broad back muscles hold hanging arms farther from the body than on a woman. Upper arm angle 14-15
    + Pelvis and shoulder tilts are smaller than on a woman. `hip_tilt=-4, chest_tilt=3`
- Muscle markers use only lines and lights, without separate shadows per mass
    + Lights loosen their edges in proportion to size, or they look like stains. Use half the radius as soft
    + Lights on limbs away from the light are weakened to 0.4 times

| Marker | Front coordinates | Treatment |
|---|---|---|
| Sternocleidomastoid | From below the ear (face coordinates (±0.72, 1.2)) to thorax (±0.05, -0.02) | Two lines meeting at the hollow at the base of the neck |
| Adam's apple | thorax (0, -0.4) | A short arc and a small light |
| Collarbones | thorax (±0.08, -0.03) to (±0.76, -0.04) | Longer and darker lines than on a woman |
| Pectoralis major | Lower border thorax (±0.04, 0.6), (±0.3, 0.7), (±0.56, 0.62), (±0.72, 0.34) | A shade band below the border, broad light above |
| Chest marks | thorax (±0.42, 0.52) | Small ellipses |
| Serratus | Three rows from thorax (±0.76, 0.82) at 0.16 spacing | Short diagonals |
| Abdominals | Linea alba from thorax (0, 0.78) to pelvis (0, -0.5), segment lines at thorax y 1.0, 1.26 and pelvis y -1.0 | Small lights between segments |
| Obliques | thorax (±0.62, 1.12) to pelvis (±0.58, -0.42) | Flank lines |
| Pelvic V line | pelvis (±0.56, -0.44) to (±0.16, 0.24) | Dark lines. The lower ends meet at the lower pelvis |
| Lower pelvis | pelvis (0, 0.47), radius 0.1×0.14 | A round mass merged into the body mass. Light and shade only, no inner lines |
| Deltoid | Upper arm 0.08 to 0.5 | A diagonal front border and light at the shoulder tip |
| Sartorius | From the outside of the pelvis to the inner knee | A long slanted line |
| Vastus medialis | Thigh 0.82, inside 0.12 | A teardrop light above the inner knee and its border line |

| Marker | Back coordinates | Treatment |
|---|---|---|
| Trapezius | thorax (±0.6, 0.02) to (±0.04, 1.2) | Two lower border lines meeting at the middle of the back |
| Shoulder blades | thorax (±0.24, 0.2) to (±0.46, 0.9) | Inner edge line, spine line, light on the infraspinatus |
| Latissimus | thorax (±0.76, 0.36) to pelvis (±0.36, -0.9) | Lines sweeping down from the armpit to the waist |
| Erector spinae | pelvis (±0.15, -0.95) | Vertical lights on both sides of the spine groove |
| Buttocks | center (±0.34, 0.2), radius 0.36×0.38 | Smaller than on a woman. Hollow shade at the sides (±0.64, 0.1) |
| Back of the thighs | Thigh 0.35 to 0.88 | A vertical center line |
| Calves | Shin 0.3, 0.08 inside and outside | Lights on the two heads and the outer border line |

## 3D Rig

Usage verified in `examples/anime_turnaround.py`. Men and women share the same workflow and change only build, head and colors.

- The planar rig cannot turn the body
    + Joints must sit in 3D and be projected at the requested angle to keep the proportions of 3/4 views and profiles
- `Figure3D` takes the arguments of `figure.Figure` unchanged and adds angle arguments
    + At turn 0 the joints and torso outline match the planar rig
- The torso is built from 11 sections by height
    + Joining the projected left and right end points of each section gives the silhouette at any angle
    + `Depth` sets the front and back depth of chest and buttocks. `FEMALE_DEPTH`, `MALE_DEPTH`
- The foot is a convex hull of a point cloud
    + `toes()` returns the 5 toes only when the toes face the viewer

```python
from codepaint.figure3d import Figure3D, MALE_DEPTH
BODY = Figure3D(g.Frame((x, y), unit), build=figure.MALE, depth=MALE_DEPTH, turn=45, elevation=5,
                stretch={"neck": 0.72}, shoulder_drop=0.14, arm_l=(12, 6), arm_r=(12, 6), leg_l=(4, 0), leg_r=(4, 0))
```

| Argument | Meaning | Convention |
|---|---|---|
| `turn` | Rotation of the whole body | 0 front, 45 3/4 front, 90 profile facing right, 135 3/4 back, 180 back. Negative turns left |
| `elevation` | Downward view | Around 5 shows the insteps and shoulder tops and steadies the full figure |
| `lean` | Forward bend of the upper body | 12-20 for a seated forward lean |
| `swing` | Forward-back swing of limbs | `{"leg_l": (thigh, shin)}`. Positive is toward the front of the body. The shin value is also absolute |
| `head_turn` | Turn of the head alone, apart from the body | About -70 for looking back over the shoulder |
| `foot_pitch` | Angle that lowers the toes and raises the heel | `{"l": 24}`. The back foot of a walk |

| Pose | Arguments | Example |
|---|---|---|
| Turnaround stance | `arm_l=(12, 6), arm_r=(12, 6), leg_l=(4, 0), leg_r=(4, 0), elevation=5`, turn 0, 45, 90, 135, 180 | `anime_turnaround.py` |
| Seated, seen 3/4 front | `turn=35, lean=6, swing={"leg_l": (86, 2), "leg_r": (90, 12), "arm_l": (14, 62), "arm_r": (18, 66)}, arm_l=(10, -14), arm_r=(8, -16)` | `anime_turnaround.py` |
| Walking, seen from the side | `turn=-90, lean=4, swing={"leg_r": (24, 4), "leg_l": (-14, -38), "arm_r": (-20, -6), "arm_l": (22, 44)}, foot_pitch={"l": 24}` | `anime_turnaround.py` |
| Looking back over the shoulder | `turn=155, head_turn=-72, hip_tilt=5, chest_tilt=-3` | `anime_turnaround.py` |
| Seated, seen from the side (hands on knees) | `turn=75, lean=12, swing={"leg_l": (84, 4), "leg_r": (80, 10), "arm_l": (25, 60), "arm_r": (22, 62)}` | `anime_turnaround.py` |

- The sign of turn sets the near side
    + With positive turn `_l` is near, with negative turn `_r` is near
    + In walking and sitting, putting the forward leg on the near side reduces leg overlap
- `groups()` sets the paint order
    + Far limbs, body (a mass merging limbs at a depth similar to the torso), near limbs
    + In front and back views every limb merges into the body, forming the same single mass as the planar rig
    + The near leg merges into the body so it joins the hip. A leg with the thigh raised more than 40 degrees is painted separately, which leaves a line between belly and thigh
- Seams of separately painted masses
    + Near limbs painted over the body erase the outline within radius 0.34 around the shoulder or hip joint
    + The pelvis outline crossing the far leg is erased within 0.75 around the hip joint, keeping the line where the near thigh is
- Surface markers are drawn only where the normal faces the viewer
    + Get point and normal with `surface(part, x, y, side)` and draw when `facing` exceeds 0.12. Up to 0.42 they fade in
    + Lines are drawn only along runs of visible points, and lights take their strength from the angle between the 3D normal and the light source
    + The planar rig marker coordinates (tables above) apply unchanged, with `side="front"` for the front and `side="back"` for the back
- Round masses are ellipsoids from `bulge`
    + Breasts: radius 0.26×0.27×0.2 at thorax (±0.31, 0.72), set 0.17 behind the front surface. The crease under the breasts is the lower edge of the ellipsoid
    + Buttocks: radius 0.42×0.4×0.24 attached to the back of pelvis (±0.39, 0.18). The crease under the buttocks is also the lower edge of the ellipsoid
    + The lowest torso section (pelvis y 0.5) is the crotch and only 0.12 wide. Markers below it attached to the surface get pushed to the flanks
- Hands are chosen by how much the back of the hand or the palm shows
    + If the outward direction faces the viewer by more than 0.75, `hand_open` (thumb toward the body front), otherwise `hand_side` (palm toward the body center)
- The floor is matched to the lowest foot silhouette
    + Find the lowest point of the foot silhouette with a test rig, then set the pelvis height. This works for seated poses and walks with a raised heel too

## Head and Hair by Angle

- `head3d.Head3D` handles the head in 3D
    + The frontal outlines of `FEMALE_HEAD` and `MALE_HEAD` match the adult female and adult male face tables in craft.md
    + `Head3D.on_body(body, spec)` matches the head position on the body and the angle combining the body turn and `head_turn`
- Facial parts are drawn with frontal coordinates as they are
    + Coordinates from craft.md passed into the frame returned by `head.face()` attach to the face surface and distort with the angle
    + Each part is drawn only when `face.facing(x, y)` exceeds 0.12. In profile the far eye drops out by itself
    + The nose bridge line goes on the far side (the shaded side in front view) and lifts off the face surface with the third value (lift)
- The head outline is two convex hulls, skull and face
    + One hull around both would turn the neck space between the back of the head and the chin tip into head
- Hair is a cap and locks
    + The cap `cap(style)` wraps the scalp above the hairline in fan-shaped pieces and keeps the dip above the ears
    + At angles where the face shows, `face_window(style)` is cut out of the cap
    + A `Lock` follows the scalp down, then hangs straight below `hang_from`. Bobs get a taper with blunt tips

| Order | Content |
|---|---|
| 1 | `locks(style)["back"]`: locks facing away from the viewer. Before the body |
| 2 | The jaw mass at angles where the face turns away. Painted before the body so only the part beside the neck shows. Skipped near the back view |
| 3 | Body (in `groups()` order) |
| 4 | Shadow cast on the neck: the head outline lowered by 0.32 skull radii, where it overlaps the body |
| 5 | Ears with a facing value of 0.5 or less |
| 6 | Head skin: base, a soft shadow half the body amount (0.18), outline |
| 7 | Facial parts: bangs shade, a shade band on the cheek that gets less light, nose, mouth, eyes, brows |
| 8 | Ears with a facing value above 0.5 and their helix lines |
| 9 | Cap (with the face area removed), `locks(style)["front"]`, crown light band and strand lines |

- The cheek shade band goes on the side that gets less light
    + The face surface normals and the light source compare the brightness of both cheeks. When the face turns toward the light, the band moves to the other side
- Scope
    + Locks ending above the shoulders are drawn with head coordinates alone. Locks falling below the shoulders need `drape` to avoid the torso (face and hair templates)

## Face and Hair Templates

Templates verified in `examples/anime_face_templates.py` (3 faces × 3 angles), `examples/anime_hair_templates.py` (8 hairstyles × 5 angles) and `examples/anime_hair_colors.py` (12 hair colors). Long hair scenes are `anime_long_hair_platform.py` (full figure 3/4 front), `anime_long_hair_window.py` (backlit 3/4 back view) and `anime_long_hair_walk.py` (two-shot walking hand in hand).

- Templates are picked with `character.restyle`
    + A face template changes the face shape (jaw sections, nose height) together with the features
    + A hairstyle changes the cap, hairline and list of locks
    + A hair color changes the four hair colors of the palette (base, shadow, light band, line), and the brows follow the line color
    + Skin, eye and lip colors and the build stay unchanged, so change those by editing the palette with `dataclasses.replace`

```python
from codepaint import faces, hairstyles
look = ch.restyle(ch.FEMALE, face=faces.FEMALE_SOFT, hair=hairstyles.LONG_STRAIGHT,
                  hair_color=hairstyles.HAIR_COLORS["silver"])
model = ch.place(look, origin, unit, turn, outfit=garment.long_coat())
```

| Face | Impression | Face shape | Eyes and brows | Mouth and cheeks |
|---|---|---|---|---|
| `FEMALE_MATURE` (default) | Mature | Chin tip 1.45 | Almond eyes with a wing, thin arched brows | Colored lower lip, cheek blush |
| `FEMALE_SOFT` | Soft | Wide, round lower jaw, chin tip 1.43 | Round eyes with drooping outer corners, double eyelids, thick arched brows | Full lips, strong cheek blush |
| `FEMALE_SHARP` | Sharp | Narrow V jaw, chin tip 1.47 | Narrow cat eyes with an upswept wing, straight brows | Wide, thin lips, faint cheek blush |
| `MALE_CLEAN` (default) | Clean-cut | Angular jaw corners | Narrow eyes, double eyelids, thick solid brows | Lip line, shade at the chin tip |
| `MALE_GENTLE` | Gentle | Round jaw | Slightly larger drooping eyes, thin arched brows | A line with raised mouth corners |
| `MALE_RUGGED` | Rugged | Wide angular jaw, chin tip 1.54 | Narrow deep-set eyes, low thick straight brows | Wide mouth, stippled stubble |

- To keep the adult markers, the eye half-width stays at 0.25 or less and the chin tip below 1.42. Larger eyes and a shorter jaw look younger

| Hair | Length | Locks |
|---|---|---|
| `BOB` (female default) | Jawline | Side-parted bangs, side hair longer at the front |
| `LONG_STRAIGHT` | Middle of the back | Bangs, 6 side locks flowing in front of the shoulders (`drape="front"`, `spread`), 9 locks down the back (`drape="back"`) |
| `SHOULDER` | Shoulder line | Bangs, 4 side locks in front of the shoulders, 9 behind |
| `PONYTAIL` | Tail on the upper back | A cap that shows the forehead, two thin locks beside the face, the tied knot, a tail hanging down the back (`drape="back"`) |
| `SHORT` (male default) | Ears visible | Bangs falling onto the forehead, ends at the nape |
| `SIDE_PART` | Ears visible | Bangs swept right from a part on the left |
| `CROPPED` | Very short | A thin cap without locks |
| `MALE_LONG` | Covers the nape | Center-parted bangs, locks beside the cheeks, back hair covering the neck (`drape="back"`) |

| Hair color | Names (`HAIR_COLORS`) |
|---|---|
| Natural colors | `black` (blue-tinted black), `dark_brown`, `chestnut`, `blonde`, `silver` |
| Anime primaries | `pink`, `sky_blue`, `navy`, `red`, `purple`, `mint`, `orange` |

- Anime hair colors put the shadow darker and slightly cooler than the base, and the light band brighter with lower saturation. `examples/anime_hair_colors.py`
- Picking a hair color on the complementary side of the background's dominant color makes the figure stand out (pink in a green park, silver against a blue sea)

- Drape of long locks
    + The lock center line in head coordinates moves to body coordinates. Moved points project to the same screen position as when projected with the head
    + Following it from the top, points inside the torso section inflated by a clearance of 0.08 are pushed out past the surface on the drape side (front or back)
    + A pushed lock hangs straight from there, and the push starts 12 points early with cosine weights so the lock curves over the shoulder
    + If the point at two thirds of the center line is nearer the viewer than the torso center, the lock is painted after the body, otherwise before it
    + Locks that flow in front of the body but sit farther than the head center at face height (far side hair at 3/4 view) are painted with the face area removed (tucked). They appear from behind the cheek and flow in front of the body
    + Front locks slant down from the temples toward the ears. Hanging them straight at the same phi lays them on the cheek, where they cover the near eye at 3/4 view
    + Long locks start with a narrow root (first taper value 0.35). A wide root sticks up like horns beside the crown
- Build new faces with `faces.FaceSpec` and new hairstyles with `head3d.HairStyle` and `Lock`, then add them to a template sheet example to check five angles
- Scope
    + Locks avoid only the torso. Check overlaps with arms raised forward, scarf ends and props on the render
    + Hair blowing in the wind and the hair of strongly bent or reclining poses are not verified
    + The pointed lock tips beside the crown of female hairstyles are a shape inherited from the bob

## Painting 3D Figures

- The `character` module handles the whole workflow of painting a `figure3d` body and a `head3d` head
    + `character.place(look, pelvis_screen_xy, head_height, turn, elevation, outfit=..., **pose)` makes a person (Model)
    + `character.paint_figure(canvas, model)` paints in the order cape behind the back, back hair, masses and clothing, front cape, head
    + A Look is build, torso depth, head shape, hair and colors. Change `character.FEMALE` and `character.MALE` with `dataclasses.replace`
- `Ink` switches the style
    + It sets line width and strength, the amount and softness of mass shadows, the strength of the light side and the light direction
    + The default `character.ANIME` is cel painting. Oil and watercolor make lines pale (0.3-0.55) and shadows soft (0.35-0.45), then go through the style pass

| Style | Ink values | Example |
|---|---|---|
| Anime style | Defaults | `anime_cafe_talk.py` |
| Watercolor style | `line_width=1.7, line_scale=0.75, line_opacity=0.55, shadow_soft=0.35, light_opacity=0.35` | `watercolor_street_walk.py` |
| Illustration style | `line_width=2.4, line_opacity=0.9, body_shadow=0.32, light_opacity=0.35` | `illustration_fantasy_walk.py` |
| Oil style | `line_width=1.5, line_scale=0.7, line_opacity=0.28, body_shadow=0.42, shadow_soft=0.45` | `oil_evening_dance.py` |

- Closed hands are set with `grips=("l",)`
    + Drawn as a fist seen from the thumb side. A rod (umbrella shaft, staff) passes through the fist center and is painted with the hand silhouette removed so it passes behind the fingers
- The thumb line is drawn faintly only inside the palm (`THUMB_LINE_ON_PALM` 0.35). With the whole contour drawn dark, the thumb looks like a separate mass sitting on the palm
- A far arm crossing in front of the body is painted after the body with `in_front=("arm_l",)`
- When part of the figure leaves the frame, as in a knee-up composition, it is painted as is (`oil_doomer_overpass.py`)

## Outfits

- Clothes follow the body at any turn angle
    + Torso garments use torso sections inflated by ease, joining the projected left and right end points of each section
    + Hems of skirts, coats, robes and capes stack more sections below the pelvis to flare. When walking or sitting pushes a leg out of a section, the section widens to cover it
    + Sleeves and trouser legs are thick bands around the limbs, and shoes are convex hulls of the inflated foot point cloud
- An outfit function takes colors and returns a function that takes the body
    + `character.place(..., outfit=garment.casual_knit(knit="#a9bf9a"))`
    + Clothing outlines depend on pose and angle, so they are computed after the body is built

| Outfit | Pieces | Example |
|---|---|---|
| `casual_knit` | Crew-neck knit, long trousers, flats | `anime_cafe_talk.py`, `anime_outfit_sheet.py` |
| `casual_shirt` | Collared short-sleeve shirt, trousers, sneakers | `anime_cafe_talk.py` |
| `formal_dress` | Long dress (hem ripples and spin), short sleeves, heeled shoes | `oil_evening_dance.py` |
| `formal_suit` | Jacket, shirt front and necktie, slacks, dress shoes | `oil_evening_dance.py` |
| `long_coat` | Knee-length coat, belt, scarf, boots. length 1.5 gives thigh length | `watercolor_street_walk.py` |
| `mage_robe` | Ankle-length robe, bell sleeves, belt, cape | `illustration_fantasy_walk.py` |
| `light_armor` | Tunic, breastplate, pauldrons, bracers, cape | `illustration_fantasy_walk.py` |

- Each piece (Garment) has a mass (group) to paint on
    + Sleeves go on the `arm_l` mass, trouser legs and shoes on the `leg_l` mass. At angles where the limbs merge with the body, they go on the body mass
    + Pieces with the same merge value in the same mass merge into one shape. No line forms between trouser waist and legs
    + Capes (group cape) are painted over the body only when their back faces the viewer, otherwise before the body
- Build new clothes from pieces made with `garment.loft`, `limb_span`, `shoe`, `neck_band` and `bulge`, wrapped in `Garment`
    + `loft(body, top, bottom, ease, hem=Hem(...), half="back", loose=0.6)`. loose is the slack that fills concave places such as the waist
    + Inner lines are `surface_curve` (curves on the torso surface), `limb_marks` (sleeve and trouser folds), `Loft.line_at` (skirt folds) and `surface_dots` (buttons)
- Scope
    + Skirts and dresses in seated poses are not handled. There is no computation of cloth draping over the thighs
    + Clothing folds are lines at preset places, with no cloth physics

## Two-shots and the Stage

- `stage.Stage` builds a stage where two people and props share one view
    + World coordinates: x screen right, y down (floor 0), z away. The unit is the head height
    + `stage.place(look, x, z, turn, ...)` puts a person with feet on the floor at a world position
    + `stage.box`, `stage.cylinder` and `stage.ellipse` project chairs, tables, cups and floor shadows with the same view
- Where hands reach is set with `reach` or `fists`
    + With `reach={"arm_r": world coordinates}`, arm angles are computed so that wrist meets the target (two-bone inverse kinematics)
    + With `fists={"arm_r": world coordinates}`, the center of the closed fist meets the target. Used for hands gripping rods
    + For held hands, put both people's targets 0.12 to either side of one point. For a hand touching another person's joint, get the target from `stage.joint_world`
    + The center of a closed fist is `stage.fist_world(model, side)`. Rods are drawn through this point
- The elbow direction is set with `poles`
    + The default `ELBOW_POLE` (outward 0.45, down 1.0, back 0.35) suits a person standing alone
    + For two people shoulder to shoulder, the outward side of the inner arm faces the partner, so the default drives the elbow into the partner's body. Reduce the outward component to 0 or below
- Check for penetration with `stage.collisions([a, b])` before painting
    + An arm bone center line inside the other torso, or two arm bones closer than the sum of their thicknesses, counts as penetration
    + Visible penetration makes the arm look cut whatever the paint order, so fix poles, hand targets or spacing first
    + Penetration that the other body hides, or that does not look wrong in the picture, can stay after checking the render
- Paint order
    + Far person first (`stage.far_first`). Where two people overlap, the near person covers the far one's body
    + Limbs that interleave with props are deferred with `paint_figure(..., defer=("arm_l",))` and painted with `paint_deferred` after the props
- For held hands, both people close their fists with `grips` and one side gets `palm_out`
    + With `fists` putting the two fist centers 0.1 to either side of the clasp point, the fingers interlock in the middle
    + An arm at a depth similar to the body merges into the body mass, so it needs `in_front` to separate it and show the hand over the coat

| Situation | Placement | Example |
|---|---|---|
| Seated face to face in a cafe | 3.0 on each side of the table center, turn 78 and -80 (each turned 10 degrees toward the viewer to show both faces). Near arms to the cups, far arms on the thighs | `anime_cafe_talk.py` |
| Walking toward the viewer hand in hand | Two people at turn -20, 2.1 apart sideways, walking in step. Hands held slightly forward at hip height between them (`fists`, her `palm_out`), with her held arm deferred and painted after him | `watercolor_street_walk.py` |
| Walking side by side | 1.9 apart along the body's side direction, in step. Inner hands held between them at hip height | `illustration_fantasy_walk.py` |
| Dance | Her at turn 28, him at turn -62 a little behind. Hands held at one point above both heads, she stands on her toes | `oil_evening_dance.py` |
| Standing side by side in back view holding hands | turn 186 and 174, 2.3 apart sideways. Back views swap front and sides, so the inner hand of the person on screen left is `arm_l` and that of the person on the right is `arm_r` | `illustration_doomer_rooftop.py` |

- Scope
    + The projection is orthographic, so size does not change with depth. Keep the two people at similar depths and draw distant backgrounds separately with `Perspective`
    + Poses where two bodies interleave deeply, such as hugging or embracing, cannot be resolved by a single paint order and are not verified
    + The two arms in `illustration_fantasy_walk.py` and `oil_evening_dance.py` show up in collisions as penetrations, yet they are hidden or do not look wrong, so they stay as they are

## Common Defects

| Symptom | Remedy |
|---|---|
| Joints look like a ball-jointed doll | Merge connected parts with `shape_of`, paint them at once and cover the seams with skin-colored blotches |
| A raised arm leaves the frame or looks too long | Give `stretch` 0.6-0.8 to bones coming toward the screen and reduce the angle |
| A reclining body floats over the couch | Raise the couch edge near the body's center line and lay a contact shadow along the contact line |
| Sleeves or trousers cling to the body | Raise the scale of `limb` to 1.3 or more |
| A hand looks like a bundle of fingers | Paint each part separately with outlines, and keep spread at 0.5 or less so the fingers stay together |
| Male muscles look like stains | Increase the soft of lights in proportion to size and weaken lights on the side away from the light |
| A male face looks flat | Break the jaw corners and chin tip, add shade on both cheeks, thick brows and a nose bridge line |
| The face looks young | Shrink the eyes and lengthen the jaw. Adult anime faces use an eye unit of 0.24, chin tip y 1.45, cheek shadows and a nose bridge line |
| The neck looks too long | `stretch={"neck": 0.7-0.75}`. Especially needed when drawing larger anime heads |
| The shoulders look raised | Thin the upper arm of a lowered arm or loosen the shoulder contour with skin color |
| The skin looks flat | Raise the shade ratio to 0.45 or more and add deep shade and reflected light |
| At 3/4 front the pelvis outline crosses the far thigh | Erase the body outline around the hip joint over the far leg and keep only the line where the near thigh is |
| A ring-shaped line appears at the shoulder of the near arm | Erase the outline around the joint of separately painted limbs to join them to the body |
| The jaw shows above the neck in back view | At angles where the face turns away, paint the jaw mass before the body |
| The face looks split in half | Halve the head mass shadow relative to the body and give the shading through the cheek shade band |
| The crease under the buttocks gets pushed to the flanks | Draw the crease along the lower edge of the buttock ellipsoid |
| In seated poses the lower pelvis mass shows below the thighs | With the thigh raised more than 40 degrees it hides between the thighs, so it is not drawn |
| Hair locks look spiky | Bob locks get a taper with an end value above 0 and a width of 0.5 or more |
| Clothing outline corners stick out like ears | A curve joining only section end points bulges at the corners. Loft closes the top and bottom with ring arcs |
| The trouser waist pokes out beside the top | Give the top loose 0.5-0.7 to fill the concave waist |
| Sleeve shoulders rise like pads | Keep the sleeve root width close to the skin (ROOT_EASE) and widen it along the upper arm |
| A closed hand hides behind the body | Give `in_front` to a far arm crossing in front of the body |
| An arm looks cut in the middle in a two-shot | Find the penetration with `stage.collisions` and reduce the outward pole component of the inner arm or widen the spacing |
| The sleeve of an arm bent forward looks like a square lump and the hand pokes out | Avoid poses with the forearm toward the viewer, and lower the arm or reach it sideways |
| Only one of the held hands shows | `palm_out` on one side, `in_front` on an arm merged with the body |
| The thumb looks like a separate mass on the palm | Draw the thumb line faintly inside the palm (character does it automatically) |
| An arm on a table is covered by the table top | Defer that arm and paint it after the table top |
| Long hair locks pierce the shoulders and chest | Give `drape` (front or back) to locks that fall below the shoulders |
| The neck shows through the middle of a back view | Set the root phi of back locks equal to their tip phi so they gather in the middle |
| Locks bend like steps over the shoulder | Increase the number of points that take the drape push early (`DRAPE_EASE`) |
| Faces from different templates look alike | Change the face shape (jaw sections), brows and mouth corners before the eye shape |
| At 3/4 view long hair covers the far eye | lock_layers splits far-side locks into tucked and removes the face area. For hand-drawn locks, paint them with the face silhouette removed |
| The sides of the crown stick up like horns on long hair | Narrow the first taper value of long locks to about 0.35 |
