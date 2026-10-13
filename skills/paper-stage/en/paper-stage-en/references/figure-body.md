# Full figure and hands

The full-body rig and the hand rig in `scripts/codepainter/figure/`. With no 3D model, they dress a flat joint skeleton in tubes with width profiles. The head is the bust rig's head placed on top as it is.

## Call

```python
from codepainter.figure import PortraitSpec, BodySpec, draw_figure, wardrobe
from codepainter.figure.body import make_pose

pose = make_pose("hand_on_hip", root=(0.50, 0.475), unit=0.105)
masks = draw_figure(painting, PortraitSpec(yaw=-0.5), BodySpec(), pose, style, dress=wardrobe.bodycon)
```

- Call it on a Painting whose background is already drawn
- With `dress=None` the body is drawn unclothed
- Returns the `figure`, `skin`, `head`, `trunk`, `limbs`, `clothes`, `hair`, `eyes` and `hands` masks with `skeleton` and `frame`
    + `masks["head"]` is used as the `importance` of the painterly `finish`
    + `masks["skeleton"].joints` is a dict of joint pixel positions, used to place props

## Units and angles

- The unit of length is one head height
    + The default figure is about 7.7 heads tall, 8 heads with `BodySpec.legs=1.0`
- Left and right follow the screen; `l` is the viewer's left
- Angles are in degrees; 0 points straight down, positive toward the screen right, 180 straight up
    + Example : spreading the screen-left arm outward is negative, the screen-right arm outward is positive

## Pose presets

`make_pose(name, **overrides)` returns a Pose with only the fields you name changed from the preset.

| Name | Pose |
|---|---|
| `stand` | upright |
| `contrapposto` | weight on one leg, both arms down |
| `hand_on_hip` | weight on one leg, screen-right hand on the hip |
| `arm_behind_head` | weight on one leg, one arm behind the head, one hand on the hip |
| `arms_up` | both arms raised behind the head |
| `walk` | a step with one leg crossing in front |
| `walk_side` | a walk seen from the side (`yaw=90`), legs apart front to back, arms swinging opposite |
| `stance` | front stance with the feet apart, suits male figures |
| `back` | back view with the weight on one leg |
| `sit`, `sit_side`, `sit_front` | sitting on a chair (three-quarter, profile, front) |
| `kneel`, `kneel_side`, `seiza` | kneeling, sitting back on the heels |
| `lie_back`, `lie_side` | lying on the back, lying on the side |

- Sitting, kneeling, lying with furniture, two-shots and framing presets are in `references/clothing-and-scenes.md`

- Every preset puts the weight on the screen-left leg
    + For the other side flip the signs of `pelvis_tilt`, `chest_tilt`, `waist_shift` and the limb angles
- The framing is set with `root` and `unit`
    + A full figure is `root=(0.50, 0.475), unit=0.105`
    + A cut above the knees is `root=(0.47, 0.715), unit=0.168`

## Pose

| Field | Default | Meaning |
|---|---|---|
| `root` | (0.50, 0.51) | pelvis centre, as shares of the canvas |
| `unit` | 0.120 | head height / canvas height |
| `view` | "front" | `front` or `back` (back view) |
| `lean` | 0 | lean of the whole body |
| `pelvis_tilt` | 0 | tilt of the hip line; positive drops the screen-right hip |
| `chest_tilt` | 0 | tilt of the shoulder line; positive drops the screen-right shoulder |
| `waist_shift` | 0 | how far the ribcage is shifted sideways over the pelvis; positive is to the screen right |
| `yaw` | 0 | body turn in degrees; 45 is three-quarter, 90 profile; positive turns the front of the body toward the screen right |
| `head_yaw` | None | head turn in degrees; None follows the body `yaw` |
| `swing` | {} | swing of each bone forward or back in degrees; positive is forward, it shows from the side |
| `turn` | 0 | slight turn for front views, -1 - 1; leave it at 0 when using `yaw` |
| `arm_l`, `arm_r` | (-10, 3), (10, -3) | (upper arm angle, forearm angle) |
| `leg_l`, `leg_r` | (-3, -1), (3, 1) | (thigh angle, shin angle) |
| `foot_l`, `foot_r` | -18, 18 | foot direction |
| `hand_l`, `hand_r` | None | hand direction; None keeps the forearm direction |
| `head_tilt` | 0 | head tilt |
| `behind` | () | limbs that go behind the trunk, example `("arm_l",)` |
| `front_leg` | None | the leg crossing in front of the other, `"leg_l"` or `"leg_r"` |
| `shorten` | {} | bone length factors, for foreshortened limbs pointing at the viewer |
| `pitch` | 0 | angle the camera looks down at, in degrees; shows the knees of a front sitting pose |
| `ground` | None | screen distance down to the seat or bed the trunk rests on; None is 0.36 for seated poses |

- The keys of `shorten` and `swing` are `upper_arm_l`, `forearm_l`, `thigh_l`, `shin_l`, `foot_l` and their `_r` pairs
    + When `swing` holds `foot_x`, the foot direction is worked out from that swing (the instep of a kneel)

## Turned body (three-quarter, profile)

```python
pose = make_pose("contrapposto", root=(0.50, 0.475), unit=0.105, yaw=45)     # three-quarter
pose = make_pose("walk_side", root=(0.50, 0.475), unit=0.105)               # walking side-on
pose = make_pose("stand", yaw=-90, head_yaw=-60)                           # profile facing left, head turned less
```

- Joints and trunk sections carry depth values, turn about the vertical axis, then project flat (2.5D)
    + No 3D model or 3D engine is used
    + `yaw=0` gives exactly the same pixels as the front rig
- The trunk is a run of elliptical sections by height
    + The front silhouette is the existing width function; the side silhouette is the front and back depth of `body.TRUNK_DEPTH`
    + The side S-curve is the chest in front, the hollow of the lower back, the buttocks standing out behind, the front of the thighs and the back of the calves
- Breasts and buttocks are volumes set on the sections
    + On a turned body they are teardrops whose upper slope runs straight
    + The far breast leaves out the marks of the part hidden by the near one
- Past 22 degrees the far arm goes behind the trunk and the near leg in front, on their own
    + Once the far arm hides, the round far shoulder of the trunk is removed with it
- Front anatomy marks fade with the turn and vanish on the faces out of view
- Clothes are placed by wrapping front-view coordinates round the body
    + x past the trunk half width carries on round the side to the back; `hip * (1 + pi/2)` is the middle of the back
    + Swimsuit and bikini bottoms cover to under the buttocks on a turned body
    + On a turned body a skirt is redrawn as a cone-shaped shell round the hips and thighs
    + For a new outfit's skirt see `wardrobe._turned_skirt`, for a shell wrapping the body see `body.wrapped_outline`
- The head turns with the body and passes to the profile key past 25 degrees (`references/figure-rig.md`)
- A back view (`view="back"`) ignores the turn and is drawn square-on from behind

### Posing tips

- In a contrapposto the hip line and the shoulder line tilt opposite ways
    + The hip over the weight leg rises and the shoulder on the same side drops
    + The weight leg stays near vertical, the other leg bends a little at the knee
    + The pelvis shifts over the standing foot, so the ribcage moves toward the free leg (`waist_shift` 0.04-0.06)
    + As a result the hip over the standing foot juts out and the waist above it folds short
- A hand on the hip is the upper arm 40 degrees outward, the forearm -46 degrees inward, `hand_r=-6`
- An arm raised behind the head is about -150 degrees for the upper arm and about 60 for the forearm, with that arm listed in `behind`
- Tune poses in steps of 5-10 degrees while checking renders
    + If the wrist ends up somewhere odd, adjust the upper arm and forearm angles in turn

## BodySpec

| Field | Default | Meaning |
|---|---|---|
| `shoulder` | 0.56 | half the distance between the shoulder joints |
| `chest` | 0.47 | ribcage half width |
| `waist` | 0.385 | waist half width |
| `hip` | 0.70 | pelvis half width; near the shoulder width for an hourglass silhouette |
| `bust` | 1.45 | bust size; 0 is flat, 1 small, 1.45 full, 1.8 very full |
| `limb` | 1.0 | limb thickness factor |
| `legs` | 0.95 | leg length factor |
| `head` | 1.08 | head size factor |
| `build` | "female" | `female` or `male`, picks the anatomy marks and thigh shape |
| `arms` | 1.0 | extra arm thickness factor |
| `neck` | 1.0 | neck width factor |

- The default is a curvy build with a narrow waist and wide hips
- A fuller build is `BodySpec(bust=1.75, hip=0.74, limb=1.08)`
- A slim fashion build is `BodySpec(bust=1.0, hip=0.62, chest=0.46, limb=0.92, legs=1.0, head=1.0)`
- The hip joints are placed in proportion to `hip`, so changing the pelvis width moves the thighs too

## Male figures

```python
from codepainter.figure.body import MALE_BODY, make_pose
from codepainter.figure.frame import MASCULINE

spec = PortraitSpec(**MASCULINE, yaw=-0.45, skin="#e6bf9f", hair="#2a2022", cloth="#2c3a52", cloth_second="#d8d2c6")
draw_figure(painting, spec, MALE_BODY, make_pose("stance", root=(0.50, 0.475), unit=0.105), style, dress=wardrobe.trunks)
```

- `MALE_BODY` is a lean muscular build with shoulders wider than the hips and a straight waist
    + Arm thickness `arms=1.22`, a value that keeps the upper arm from ballooning in sleeves
    + Adjust the build by changing only some fields, as in `dataclasses.replace(MALE_BODY, arms=1.4, shoulder=0.72)`; keep thick arms for bare-body studies
- `MASCULINE` is a dict of face overrides
    + Wide jaw (`jaw=0.40`), small narrow eyes, low straight thick brows (`brow=1.55`), light lashes (`lashes=0.35`), neutral lips, short hair
    + The short hair is `hair_style="short"`, the fringe `bangs="textured"`
- Anatomy marks are the collarbones, the chest plates and their lower edge, three rows of abdominal segments, the outer groove of the abdominals, the serratus and the V line above the pelvis
- In back views the buttocks get smaller and sit higher in proportion to `hip`, with a hollow added at the side
- The rig draws no genital forms
    + A man seen naked from the front reads as a smooth-groined mannequin, so `wardrobe.trunks` looks more natural
    + An example with short trunks is `examples/figure.py --build male --outfit trunks`

## What makes a body appealing

- Give the silhouette an S-shaped flow
    + Use a contrapposto preset with `pelvis_tilt` 7-9, `chest_tilt` -5 - -7, `waist_shift` 0.04-0.06
- A slight three-quarter turn adds volume
    + `turn` 0.3 - 0.5 (or negative), with the head `yaw` a little to the same side as the body
- Keep the width difference between waist and hips
    + For women `waist / hip` in the 0.52 - 0.60 range
    + For men `shoulder` at least 0.12 wider than `hip`
- Keep the neck long; the shoulder runs from the trapezius slope round into the deltoid
    + See `NECK`, `SHOULDER_DROP` and `torso_curve` in `body.py`
- The side contour of the trunk comes from one width-by-height function
    + The width stations are `FLANK_STATIONS` (pelvis to waist) and `RIB_STATIONS` (waist to ribcage)
    + Monotone interpolation keeps the width from wobbling between stations and the narrowest waist point smooth
    + It passes smoothly from the pelvis frame to the ribcage frame over the `TRUNK_BLEND` span
    + Plotting side contour points separately per frame makes frames with different tilt disagree, leaving bumps and dents at the waist
    + The width function carries on below the widest point of the pelvis and rounds into the outer thighs
- The gap between the thighs is filled in for shading (`bridged_height`)
    + If the top of the gap counts as a deep edge, a round tongue of shadow appears above the crotch and reads as a dent
    + The filling starts at the top of the gap and eases off below `BRIDGE_DEPTH`, so the inner thigh shadow grows naturally
- The buttocks are drawn with a blurred mask and a wide, soft shading edge
    + A sharp cel edge inside the silhouette reads as a crumpled mark
    + The fold under the buttocks is drawn short, on its inner half only
- Light from the side
    + A whole side of the body has to sink into shade for the curves to show
- Keep the arms off the trunk so the silhouette has gaps
    + A hand on the hip or an arm raised behind the head does not hide the waist line
- Set the skin colour to a mid value around `#f2d2b8`
    + With a base colour close to white, the sheen highlights get lost

## Outfits

| Name | Contents | Colours used |
|---|---|---|
| `wardrobe.bikini` | triangle cups and strings, low-rise bottoms | `cloth` |
| `wardrobe.swimsuit` | one-piece swimsuit | `cloth` |
| `wardrobe.bodycon` | close-fitting strap dress, thigh length | `cloth` |
| `wardrobe.slip_dress` | strap dress with a skirt flaring from the hips | `cloth` |
| `wardrobe.top_and_jeans` | sleeveless top and close-fitting trousers | `cloth`, `cloth_second` |
| `wardrobe.trunks` | short square-cut trunks with a waistband, for male studies | `cloth`, `cloth_second` |
| `wardrobe.shirtless_jeans` | no top, straight jeans sitting on the hips | `cloth_second` |
| `wardrobe.jeans` | trousers alone, with `rise` (waist line position) and `ease` (looseness) | `cloth_second` |
| `lingerie`, `lingerie_stockings` | lace bra and briefs, stockings | `cloth` |
| `crop_top_shorts` | crop top, hot pants, trainers | `cloth`, `cloth_second` |
| `hoodie`, `hoodie_shorts` | hoodie with jeans or hot pants, trainers | `cloth`, `cloth_second` |
| `suit` | shirt, tie, jacket, suit trousers, shoes | `cloth` |

- The last four are used as `wardrobe.WARDROBE[name]`; sleeves and layered structure are in `references/clothing-and-scenes.md`

- Close-fitting clothes are cut out of the body mask
    + Pass only the region curve to `wardrobe.fitted(painting, skeleton, body_mask, region, color, style, light)`
    + Design only the neckline and hem of the region; let the sides reach far outside the body
    + Loose clothes stand off the body by `ease` (in head heights); straight jeans use 0.05-0.06
- Place coordinates with `skeleton.on_chest`, `skeleton.on_waist`, `skeleton.on_pelvis`
    + In chest coordinates the shoulder line is y=0, positive downward, bust centre 0.66, bottom of the ribcage 1.05
    + In pelvis coordinates the hip joints are y=0, waist -0.78, navel -0.50, crotch 0.45
- A new outfit function has the form `f(painting, skeleton, masks, spec, style, light)` and returns the mask it drew
    + `masks["skin"]` is the body drawn so far, `masks["trunk"]` the trunk alone

```python
def tunic(painting, skeleton, masks, spec, style, light):
    top = skeleton.on_chest([(-3, 0.40), (-0.2, 0.46), (0.2, 0.46), (3, 0.40)])      # neckline
    hem = skeleton.on_pelvis([(3, 0.62), (-3, 0.62)])                                 # hem
    region = np.vstack([geo.smooth(top), hem])
    return wardrobe.fitted(painting, skeleton, masks["skin"], region, spec.cloth, style, light)
```

- For a skirt spanning the gap between the legs, fill the body mask row by row before passing it to `fitted`
    + See how `wardrobe.bodycon` uses `_span_rows`

## Figure studies

- With `dress=None` the anatomy marks are drawn
    + Female front : collarbones, breasts, the centre and side lines of the abdomen, navel, hip bones, groin folds, knees, toes
    + Male front : see "Male figures" above
    + Back view : spine line, shoulder blades, dimples of the lower back, buttocks and the fold under them, backs of the knees
    + The marks are split into one function per body part in `figure/anatomy.py`
- Three things decide whether a body looks convincing
    + Opposite tilts of hips and shoulders
    + Contours thin at the joints and full over the muscles
    + Shading in which the whole side away from the light darkens as one mass
- Nudity and sexual depiction of minors are never drawn (the rule in `SKILL.md`)
- A half-length framing hides the weak spots of feet and hands
- For painterly, `finish(..., importance=masks["head"], detail=0.85)` is recommended
    + If the skin gets too many small strokes, lower `detail`

## Hands

```python
from codepainter.figure import hand
hand.draw_hand(painting, wrist=(400, 700), angle=180, length=300, skin="#f4d6c0", style=style,
               pose=hand.HAND_POSES["point"], thumb_side=-1.0, view="back", forearm=0.6)
```

| Field | Meaning |
|---|---|
| `angle` | direction of the fingertips; 0 is down, 180 up |
| `length` | pixel length from the wrist to the tip of the middle finger |
| `thumb_side` | 1.0 puts the thumb on the screen left of a downward hand, -1.0 the other side |
| `view` | `back` is the back of the hand (nails, knuckles), `palm` the palm (palm lines) |
| `forearm` | length of forearm drawn with it, relative to the hand length |

- Ready-made poses are `relaxed`, `open`, `fist`, `point`, `peace`
- Set one directly with `hand.HandPose(curl=(index, middle, ring, little), spread, thumb, thumb_curl)`
    + A `curl` of 0 is a straight finger, 1 a finger folded fully onto the palm
- On a full figure, set hand poses with `draw_figure(..., hands={"l": hand.FIST, "r": hand.OPEN})`

## Limits

- Views run from the front to profile (90 degrees), plus the square-on back view
    + A three-quarter back view (turns past 90 degrees) is not supported
    + Sitting, kneeling and lying are supported within the presets (`references/clothing-and-scenes.md`)
- In a back view the head shows only the back of the skull
    + A face looking back over the shoulder is not supported
- Hands are the flat hand rig drawn along the direction of the arm's end
    + Even in profile the palm and fingers look front-on; a hand holding an object seen from the side is not supported
    + A hand reaching toward the viewer gets shorter only, its width is kept
    + Hands raised behind the head (`arm_behind_head`, `arms_up`) are hidden by the head, neck and back hair
- Turned bodies are orthographic; looking down is limited to `pitch` of about 20 degrees
    + Looking up and vanishing-point perspective are not supported
    + The head rig does not follow `pitch`
- Clothes cover fitted clothes, skirts, sleeves and layers (shirt and jacket); pull folds that follow the pose are not supported
- Feet read as heel, instep and rounded toes from the side, at a set length (`FOOT_LENGTH_3D` 0.74)
    + Separate toes and the arch of the sole are not shown
- There is one male build, lean and muscular
    + Large, elderly or heavy builds are handled by changing `BodySpec` values and the width profiles at the top of `body.py`
- In full-figure framing the face is small, so painterly smears the features
    + When the face matters, use a half-length framing or a high `importance`
