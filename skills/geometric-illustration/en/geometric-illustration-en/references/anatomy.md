# Body Proportions and Form Design

> Translated from the Korean original. Where the two editions disagree, follow the Korean edition.

Where the numbers in `rig_anatomy.py` come from, and what to check first when changing the body.

## Contents
- Principles
- Proportion data and conversion
- Anime illustration adjustment
- Torso loft table
- Limbs and joints
- Hands and feet
- Male body
- Anatomy marks
- Shading cleanup
- Review procedure
- Sources

## Principles

- The goal is a believable body. Ahead of anatomical precision, measured data sets the points where a viewer feels something is off (shoulder height, waist position, arm length, the S curve of the side line).
- Proportions are 2 base bodies, adult female and adult male, plus 5 named body type variants (`character.sex`, `character.build`). The spec does not expose individual proportion numbers. Variants are added only as factor tables that pass the checks.
- The current 7 body type presets are all variations within real adult body ranges.
- The current body model has no chest mark or pelvic geometry. The area around the pelvis is a zone where no interior lines are drawn.
- The content limit is 1 item, unclothed figures and sexual acts involving minors (figure study section of `SKILL.md`). Fixing body proportions to adult values is its implementation.

## Proportion Data and Conversion

The data is the female sample of the US Army anthropometric survey ANSUR II (2012).

- Of 1,986 subjects, the 281 lean subjects with BMI 19-22 were selected, because they are closest to the build of illustrated figures.
- This subsample has a mean stature of 1,620 mm and a mean head breadth of 146 mm. A real person's stature is 11.1 head breadths.
- The drawn figure measures about 9.07 head breadths from the top of the head to the soles, because anime figures draw the head about 1.2 times larger than life.
- Conversion rules
    + Widths and lengths: drawn value (head breadths) = measurement / stature x 9.07
    + Heights: drawn y = (stature - measured height) / stature x 9.07 - 0.62 (the head center is the origin and the top of the head is y -0.62)
- This attaches real human body proportions unchanged below the large head.

Main converted values (head breadth units):

| Measurement | Drawn value | Used for |
|---|---|---|
| Acromion height | y 1.03 | Shoulder joint y 1.18-1.20 |
| Suprasternal height | y 1.07 | `NECK_BASE_LOCAL` |
| Chest height | y 1.90 | Chest piece position |
| Waist (omphalion) height | y 2.96 | Elbow height, `NAVEL_LEVEL` |
| Trochanterion height | y 3.75 | `HIP_LOCAL` |
| Crotch height | y 4.08 | Wrist height, center of the quiet zone |
| Knee (mid patella) | y 5.96 | `THIGH` 2.25 |
| Lateral malleolus | y 8.10 | `SHIN` 2.15 |
| Upper arm length | 1.86 | `UPPER_ARM` 1.60 (adjusted to the shoulder joint) |
| Forearm length | 1.34 | `FOREARM` 1.32 |
| Hand length | 1.00 | `HAND_SCALE` 1.0, wrist to middle fingertip 0.99 |
| Hand breadth | 0.43 | Maximum palm width 0.40 |
| Foot length | 1.35 | Foot piece 1.20 (anime adjustment 0.88) |

## Anime Illustration Adjustment

Targets are the measured widths multiplied by the factors below. The anime illustration body has a thin waist and narrow shoulders, with a hip width close to life.

| Measurement | Factor | Target (head breadths) |
|---|---|---|
| Bideltoid breadth (shoulder width) | 0.88 | 2.06 |
| Chest breadth | 0.92 | 1.30 |
| Waist breadth (omphalion height, ANSUR definition) | 0.80 | 1.18 |
| Hip breadth | 0.95 | 1.73 |
| Chest depth | 0.95 | 1.16 |
| Waist depth (omphalion height) | 0.80 | 0.81 |
| Buttock depth | 0.95 | 1.09 |
| Foot length | 0.88 | 1.19 |

The narrowest waist (y 2.70, above the navel) has no survey item, so it takes the design value 1.00. The difference from the width at navel height creates the cinched waist of the anime body.

Limb girths are also thinned to about 0.85-0.9 of the measurements. Ankles and wrists are thinner still (about 0.7) so the extremities look light.

## Torso Loft Table

The torso is a single chain of elliptical section cones joining the rows of `TORSO_LOFT`. Each row gives the front width, the side depth and the depth center z at height y of the standing pose.

- Read top to bottom, the table becomes the two outlines a painter draws first.
    + Front: armpit 1.20, chest 1.26, waist 1.00 (narrowest, y 2.70), iliac crest 1.16, hips 1.64 (the torso carries the whole hip curve)
    + Side: rounded back (z center -0.07), the hollow behind the waist (z center +0.02), full buttocks, soft lower belly
- The rib cage frame and the pelvis frame turn separately. Rows between y 2.25 and 2.95 blend the two frames smoothly (`_torso_point`), so the waist takes the twist.
- Building the width from several chains of round sections makes the creases between chains show as shading stripes. That is why a single chain of elliptical sections replaced them.
- Between table rows the curve is C1 (Catmull-Rom), divided into 10 (`LOFT_SUBDIV`). Joining rows with straight lines puts a corner in the outline at every row.
- Section end caps are kept short (`CAP_LENGTH`, 25% of the half-width). A round end cap as long as the half-width makes the wide hip section bulge up toward the waist and ruins the hourglass outline.
- The seam with a neighboring section is cut on the bisector (mitre). In poses with a bent waist (seated and others) a gap on the outer side of the bend shows as a groove in the back outline and as jags in the shading.
- The shoulder girdle (clavicles, trapezius, scapulae), the neck, the lower belly and the crotch fill are `torso_soft` pieces blended broadly into the torso, and they draw no outlines of their own.
- The chest and buttocks have a large `contour_eps`, so there is no line where they rise from the torso on top and only the lower curve is drawn.

## Limbs and Joints

- Arms and legs are made by sweeping sections along the bone (`limb_sweep`). This matches the way an illustrator draws a leg with two long curves.
- Adding one sphere per muscle (v3) made each sphere put a bump in the outline and a crease in the shading.
    + Radius profile: radii at 9 points along the bone (`THIGH_PROFILE`, `SHIN_PROFILE`, `UPPER_ARM_PROFILE`, `FOREARM_PROFILE`)
    + Center shift: the section center moves toward the side where the muscle rises. The calf moves back, the quadriceps forward, the deltoid outward
    + Result: the front line of the shin is straight and only the back line of the calf swells
- One arm and one leg are each one continuous tube through the joints. Centers and radii are smoothed with a Gaussian (`JOINT_SMOOTH`), so elbows and knees bend in a rounded way.
- Each bone is divided into 40 cones (`LIMB_SEGMENTS`). With fewer, an oblique self shadow shows jags at every seam.
- The cone height comes from the sphere on the axis that rises highest above that pixel (closed form plus one Newton step). Approximating with the sphere at the axis projection point leaves ripples at every seam of a long chain.
- The shoulder joint sits 0.17 below the acromion. The trapezius runs down from high beside the neck to the shoulder.
- Upper arm length is set so that, standing, the elbow is at navel height and the wrist at crotch height.
- Leg radii: thigh root 0.40, knee 0.215, calf maximum 0.235, ankle 0.105, heel 0.12. The thigh root hides inside the torso's hip curve, so it makes no bump beside the pelvis.
- Pose positions are written relative to origins, as in `_at(A.CHEST_ORIGIN, ...)`. Changing the proportions does not require editing the pose files.

## Hands and Feet

Hands and feet are where awkwardness shows first in a drawing. Both start with the mass (palm, foot body) and attach tapering tubes (fingers, toes) at its end.

### Hand (`rig_hand.py`)

- Proportions (head breadth units)
    + Hand length 0.99, palm 0.52 (52% of hand length), hand breadth 0.40
    + Finger length ratios: index/middle 0.89, ring/middle 0.93, little/middle 0.73
    + Phalanx ratios: proximal 45%, middle 30%, distal 25% (`SEGMENT_SPLIT`)
    + The row of knuckles forms an arc. The middle finger knuckle is farthest, the little finger nearest (`FINGER_MCP_U`)
- Fingers are continuous tubes that taper toward the tip (`mannequin.tube`)
    + Each span between joints is divided into 4 and centers and radii are smoothed, so bent joints turn in a rounded way
    + Joining cones of the same thickness looked like sausages
    + Only the first 4 cones blend into the palm; the rest draw their own outlines
- Thumb
    + Its root (`THUMB_BASE`) sits inside the wrist outline. Outside the wrist it makes a round bump beside the wrist seen from the thumb side
    + The thenar eminence (`THENAR`) is 2 spheres on the palm side
    + The thumb is placed on an arc of constant curvature to its tip target (`thumb_joints`)
- Fist gestures (`chin`, `clasp`) bend the proximal phalanx less and the middle phalanx more. Knuckles must show from the back of the hand for it to read as a fist
- Fingernails
    + The rig builds the dorsal outline of the distal phalanx (`nail_outline`, `HandSpace.nails`)
    + They are drawn with a faint gloss and a thin line only when 6 px or more on screen, the back of the fingertip faces the viewer, and the nail lies on a visible surface (`marks.nails`)
    + They are not drawn on the small hands of full-body framing

### Foot (`rig_anatomy.foot_pieces`)

- The foot body is a single sweep of closely spaced ellipsoids (`mannequin.ellipsoid_sweep`)
    + Section table `FOOT_SECTIONS`: heel, below the ankle, instep, ball, toe roots
    + The sole is flat (0.325 below the ankle, `SOLE`). The top surface descends from the ankle over the instep toward the toes
    + With a chain of elliptical section cones, a foot facing the viewer had short end caps and seam cuts that did not match, leaving empty wedges and broken lines in the outline. Ellipsoids give an exact silhouette and depth from any view
- Toes
    + The big toe (`BIG_TOE`) and the other 4 (`SMALL_TOES`) are separate tubes
    + The farther out the toe, the farther back its tip, so the toe line reads as oblique
    + The toes' own outlines separate them. The drawn mark for the big toe split was removed
- The front of the ankle blends broadly (`FOOT_ATTACH_K`). The inner ankle bone sits higher than the outer one (`ANKLE_BONES`)
- Posture
    + A standing foot is level (y component of `foot_dir` 0). A y component tilts the flat sole like a ski
    + Tiptoe (`hand='point'`) raises the foot and bends the toes at the ball (`BALL`) to lie flat on the floor. High heels work the same way
- Proportions: foot length 1.20 (ANSUR 1.35 x 0.88), foot breadth/length 0.33. Slightly slimmer than the measured mean (about 0.38)
- Shoes (`rig_figure.shoe_pieces`) are built in the same foot coordinate system (`foot_frame`)
    + A pointed toe box longer than the toes, low side walls that follow the sole, a heel cup, a stiletto down to the floor
    + The instep stays bare

## Male Body

This is `rig_anatomy.BUILDS['male']`. During one render, `use_build('male')` swaps the body table, so the body, clothes and checks read the same table.

### Data and conversion

- The male raw data CSV could not be obtained. The summary statistics of the full male sample (n = 4,082) in the analysis notebook of a public copy were used.
- This summary is the mean without filtering for lean builds. So each measurement was multiplied by the female ratio "lean subsample mean / full mean" to estimate the lean value.
- The summary has no measured male stature. It was estimated at about 1,771 mm by multiplying the cervicale height (1,517 mm) by the female stature/cervicale height ratio (1.167).
- The same conversion rule as for women fits the stature to 9.07 units. Vertical reference heights (neck, waist, crotch, knee, ankle) are the same as for women, so women and men share the garment cut lines.

| Measurement | Male estimate (drawn value) | Relative to female | Target (adjustment factor) |
|---|---|---|---|
| Bideltoid breadth | 2.43 | 1.04x | 2.43 (1.00) |
| Chest breadth | 1.39 | 0.98x | 1.39 (1.00) |
| Waist breadth (navel) | 1.47 | 1.00x | 1.21 (0.82) |
| Hip breadth | 1.63 | 0.89x | 1.50 (0.92) |
| Chest depth | 1.14 | 0.94x | 1.08 (0.95) |
| Waist depth | 1.03 | 1.02x | 0.87 (0.85) |
| Upper arm, forearm, neck girth | | 1.07x | Applied to the radius ratios |

### Form

- Torso loft: wide and deep at the armpits and chest. The waist narrows almost straight (narrowest 1.14). Hips 1.38, narrower than the shoulders
- Chest: 2 flat, wide ellipsoids (`pecs`) take the place of the chest piece. They have no outline of their own; a short horizontal mark line suggests the lower edge
- Shoulders: the joint is farther out (0.96). The trapezius and clavicles reach the shoulder (`GIRDLE_REACH`), and the trapezius end matches the height of the deltoid top (`GIRDLE_TOP`). The arm blends in broadly (`ARM_ATTACH_K`), so the shoulder does not stick out like a bump
- Pelvis: the hip joints are farther in (0.35) and the thigh root ball (`THIGH_ROOT_R`) is small. If it is large, a bump appears beside the hips
- Neck radius 0.31/0.28, hands 1.05x, arm girth 1.08x
- The head is drawn at 0.93 of the body unit (`HEAD_DRAW`). This follows the convention that male anime figures look taller relative to the head than female figures

### Face and hair

- Preset (`config.SEX_PRESETS['male']`): small narrow eyes, light lashes, thick low brows, long angular jaw, light lips, no blush
- Hair style `short`: back hair ending above the nape, short side hair that leaves the ears uncovered, short bangs

## Body Type Variants

`rig_anatomy.VARIANTS` is a table of factors on top of the base bodies (`BUILDS['female']`, `BUILDS['male']`). `_variant` turns a table into a body and registers it, as in `BUILDS['female_fuller']`, and `character.build` picks it through `build_key(sex, build)`.

| Factor | Applies to |
|---|---|
| `width`, `depth` | Width and depth of the 10 torso loft rows (neck, armpit, chest, under chest, ribs, waist, navel, lower belly, hips, crotch) |
| `shoulder` | Shoulder joint x, girdle length (`GIRDLE_REACH`) |
| `hip` | Hip joint x |
| `thigh`, `thigh_root`, `shin`, `upper_arm`, `forearm` | Limb radius profiles, thigh root ball |
| `neck` | Neck radius |
| `chest`, `chest_drop` | Chest form radius (pectoral depth for men), chest position drop |
| `glute` | Buttock radius |

| Body type | Design intent |
|---|---|
| `female_slender` | A long-lined body with reduced overall width and girth |
| `female_fuller` | An hourglass body with full chest and hips and a cinched waist. Factors within 1.3 |
| `female_athletic` | A body with muscle on the shoulders, arms and calves. The thigh root is left unchanged so no bump forms on the pelvis line |
| `male_slim` | Thin limbs and a narrow torso |
| `male_athletic` | Broad shoulders and chest, thick pectorals and upper arms, a tapering waist (inverted triangle). The trapezius is not raised, so clothed shoulders do not peak |

- Vertical reference heights do not change. Pose wrist targets and garment cut lines still match
- Check targets are the base targets multiplied by the same factors (loft factors interpolated at the measurement height) (`check_proportions._variant_targets`). It is a construction check that confirms the factors actually reached the form and that the outline has no bumps
- More inflections on the pelvis line mean the thigh factor exceeds the pelvis width factor. Keep `thigh_root` near 1.0 or raise the `width` of the hip rows

## Anatomy Marks

Illustrators suggest anatomy with a few short lines. Those points are kept as marks (`anatomy_marks`, `leg_marks`).

| Mark | Kind | Visible when |
|---|---|---|
| Clavicle | Faint line | The chest faces the viewer |
| Navel | Dot | The pelvis faces the viewer |
| Spine groove | Shadow groove | The back faces the viewer |
| Medial border of the scapula | Shadow groove | The back faces the viewer and that arm hangs down |
| Sacral dimples | 2 dots | The back faces the viewer |
| Gluteal fold, top of the gluteal cleft | Faint line | The back faces the viewer |
| Curve below the kneecap | Faint line | The knee faces the viewer |
| Lower edge of the pectorals (male) | Faint line | The chest faces the viewer |

- Each point is drawn only within `MARK_SURFACE_TOL` (0.12) of the actually visible surface. Parts hidden by a hand or arm drop out automatically.
- Faint lines mix the skin line color 35% toward the skin color, so they are weaker than outlines.

## Shading Cleanup

- Normals are computed after smoothing the depth field by 2% of the head breadth. This keeps solid seams from smearing into stripes.
- Self shadow length is capped at 16% of the head breadth (`SHADOW_REACH`) and blurred by 2% before the cel edge is set. The body's shadow edge is cut with a narrower width than designed shadows (`BODY_SHAPE_EDGE`).
- Before style compositing, the shadows of group `body` are cleaned up.
    + Narrow light gaps are filled
    + Small light islands enclosed by shadow are found by their bright core and merged into the shadow together with their semi-transparent rim
    + Thin terminator bands that follow the silhouette are kept
- Knit tops take the body's normals blurred by 16% of the head breadth (`rig_figure.TOP_NORMAL_BLUR`). Only the large masses of the torso remain, so no hard crescent shadow forms under the chest.

## Review Procedure

1. Measure proportions and smoothness: `python scripts/check_proportions.py`
    + Proportions: compares silhouette widths and joint heights of the standing pose with the targets above. Width error of 12% or more fails. Current maximum error 7%
    + Smoothness: counts outline inflections of the arm, the leg (front, side) and waist to thigh. One bump adds 2 inflections. More than 4 fails. Current maximum 3 (v3 had up to 11)
    + Both female and male bodies are checked. `--build male` checks a single body
    + Hands and feet: hand length, hand breadth and foot length must be within 12% of the target. Outside palm/hand length 0.50-0.58, index/middle 0.86-0.96, ring/middle 0.90-1.00, little/middle 0.70-0.82, foot breadth/length 0.32-0.42 fails
2. Turn sheet: `python scripts/check_proportions.py --sheet turn.png`. Renders the same standing pose front, 3/4, side and back on one sheet. As a quality review sheet, it keeps the chest form only in the side outline.
    + Front: hourglass outline, shoulder slope, gap between the thighs
    + Side: S curve of the back, buttocks and lower belly
    + Back: whether the spine, scapulae and gluteal folds read
3. Hand and foot sheet: `python scripts/check_proportions.py --hands hands.png`. Renders each gesture in one row from 3 directions (back of the hand, thumb side, palm), then a flat foot and tiptoe from the front, 3/4, side and back.
    + Hands: whether the fingers taper, whether there is no bump beside the wrist from the thumb side, whether the knuckles show in a fist
    + Feet: whether the sole is level, whether the front view of the toes has no broken lines or empty wedges, whether the toes lie on the floor in tiptoe
4. Re-render the 4 poses and 4 clothed figures and confirm that hand positions and coverage hold. In the Venus pose in particular, the lower hand must cover the front of the pelvis.

## Sources

- ANSUR II raw data: Penn State OpenLab, ANSUR II dataset (https://www.openlab.psu.edu/ansur2/)
- ANSUR II measurement definitions: Gordon, C. C. et al. (2014). 2012 Anthropometric Survey of U.S. Army Personnel: Methods and Summary Statistics. Technical Report NATICK/TR-15/007 (http://tools.openlab.psu.edu/publicData/ANSURII-MFR.pdf)
- The female sample CSV used for the work came from a public GitHub copy (sharad18/Adidas-Data-Challenge).
- The male summary statistics were read from the `Male.ipynb` output (`df.describe()`, 30 items) of the same copy. The male CSV file of that copy is not measurement data.
