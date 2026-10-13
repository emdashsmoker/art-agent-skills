# Drawing standards

## Contents

- Composition
- Value
- Color
- Line
- Finishing by style
- Order of drawing a person
- Drawing two people and a scene
- Defect table
- Varied people
- Drawing group shots
- Drawing objects
- Reference techniques

## Composition

- Choose one focal point and place it near a rule-of-thirds intersection
    + Two or more focal points scatter the eye
- Size the subject to fill 70-85% of the picture height
- Leave space on the side a person looks toward and moves toward
- Place a landscape horizon at 1/3 or 2/3 of the picture height
    + A horizon dead center splits the picture in two
- Build three layers, foreground, middle ground and background, for depth
- Crop at the picture edge away from joints (wrists, knees, ankles)

## Value

- Design the values first in three steps: light, middle, dark
    + A picture whose three-step layout does not read will not read with more detail either
- Fix one key light and apply the same `light` to every shape
- Put the lightest and the darkest values next to each other at the focal point
- Alternate the values of subject and background
    + A dark background behind the lit side of the subject, a light background behind its shadow side
- When the volume looks weak, reduce the z component of the light to turn it into a side light
    + A front light `(-0.3, -0.4, 0.86)` looks flat, a side light `(-0.74, -0.42, 0.52)` looks solid
- Cast shadows (`cast`) express the distance between an upper shape and the one below
    + Use them for the neck under the chin, the forehead under the bangs, the trunk under an arm

## Color

- Limit the palette to one main color, 1-2 supporting colors and one accent color
- Shadows are made by multiplying the local color by the ambient color (`Style.ambient`)
    + Blue shadows on a clear day, violet shadows at sunset, brown shadows under indoor incandescent light
- Contrast temperature: warm light, cool shadow
- The base skin color is a light apricot; its shadow shifts toward red
    + Light skin `#f8e0d2`, medium skin `#eec6ab`, tanned skin `#c99a7a`
- Lower the saturation of distant things and shift them toward the haze color
- Keep the most saturated color around the focal point

| Mood | Sky and background | Shadow ambient | Accent |
|---|---|---|---|
| Clear day | `#3f78c4`, `#a9cdee` | `(0.80, 0.78, 0.92)` | warm yellow |
| Sunset | `#2b3a78`, `#a0629a`, `#f59a5a` | `(0.60, 0.52, 0.70)` | orange |
| Night | `#060a1c`, `#15224a` | `(0.30, 0.32, 0.50)` | yellow window light |
| Classical oil | `#3a312b`, `#54453a` | `(0.56, 0.46, 0.48)` | lit side of the skin |

## Line

- Set the base line weight to 0.2-0.3% of the short side of the picture
- Make the outer silhouette the heaviest and the inner details thinner
- Make lines heavier on the side away from the light (`shade_gain`) and thin at the ends (`taper`)
- Leave out lines where the same material continues
    + Neck and shoulders, arm and trunk, the upper line of the chest connect with shading and no line
- Use the skin's shadow color for creases on skin, never black

## Finishing by style

- (anime) Keep one shading edge and at least 60% of the area on the lit side
    + On faces widen the lit side with `light_bias` and gather the shadows under the chin and under the hair
    + Eye highlights, a shine band in the hair and diffusion glow give density
- (illust) Lay one weak edge over soft shading and use lines in the family of the local color
    + A rim light (`rim`) separates the outline from the background
    + The mottled ground of `backdrop.wash` suits it
- (painterly) Secure enough value contrast in the reference picture before applying the brush pass
    + The brush pass reduces contrast, so a flat reference gives a flat result
    + `scale` 0.5-0.6 for people and architecture, 1.0 for landscapes
    + Give the focal shapes `focus` 0.5-1.0 and leave the background at 0 to keep large strokes
    + A dark background with a side light creates the impression of a classical oil painting
- (watercolor) Keep the lit areas wide and limit dark local colors (black hair, navy clothes) to 1-2 places
    + Paint areas have wobbling edges and pigment pools at their edges, so compositions built on large areas suit it
    + The picture border is left as white paper; keep people and the focal point at least 5% of the picture width inside it
- (pencil) The value structure becomes the hatching steps directly, so secure at least three value steps in the reference picture
    + White clothes and light walls stay as paper without hatching; hair and dark clothes darken with cross hatching
    + Suits character sheets, scene studies and interior perspective practice
- (poster) Choose clothing and skin hues far apart
    + Close hues, such as a white shirt and light skin or a yellow blouse and skin, merge into one color field and the edge disappears
    + Saturated clothing colors such as brick, teal, navy and mustard strengthen the screen-print look
- (neon) Use it with night scenes, with light sources such as signs, monitors or lamps inside the picture
    + Set the light so the key comes from the signs, and separate the outline on the other side with a cyan rim light
    + On a wet floor lay the person's reflection with `stage.reflection` to tie the floor and the person together

## Order of drawing a person

1. Decide the size and position of the head and lay out the body proportion lines in head heights
2. Add shapes in the order back hair, trunk, neck, face, front hair
3. Give the head direction (`yaw`, `roll`) and the body direction (`turn`) different values to avoid frontal symmetry
4. Adjust the expression values of the eyes, brows and mouth
5. Check the light and the cast shadows
6. Adjust the background values to alternate with the person's outline

- A mature look combines `jaw` 0.85 or more, `eye_size` 1.0 or less, and `bangs="swept"` or `"parted"`
- A soft look combines `jaw` 0.3 or less, `eye_size` 1.1 or more, and `blush` 0.3
- For men, change the form cues along with the body numbers
    + Keep the ratio of shoulder width to hip width at 1.4 or more and minimize the curve from waist to hips
    + Draw only the lower line of the pectorals and leave out the outer line rising to the armpit (a round outer line reads as a breast)
    + Draw the linea alba, the tendinous intersections and the iliac V line on the abdomen with lines in the skin's shadow color
    + Stances with the legs apart (`heroic`, `akimbo`) strengthen a masculine look
- For a clothed person, get the bare body right first, then dress it
    + Clothes are cut from the body form grown by the ease, so wrong body proportions give wrong clothes
    + Set the look with sleeve length, hem position and shoes, and keep to at most three colors for top, bottom and shoes
- Back views are told apart from front views by dorsal anatomy landmarks (spine, shoulder blades, dimples of the pelvis, the backs of the knees)
    + In back views all the hair lies over the body
- Profiles read through the rhythm of the front and back contours
    + Chest and belly forward, the small of the back and the nape hollow, the buttocks and calves out behind
    + Draw the far limbs first and slightly darker to separate front from back
    + In walking, arms and legs swing against each other; the back foot touches the ground with the toes, the front foot with the heel
- A character sheet sets front, three-quarter, profile and back views side by side at the same head height on the same ground line

## Drawing two people and a scene

- For two people, decide first who is in front
    + Draw the person nearer to the camera later; their shoulder and arm hide the overlapping side of the other
    + Turn the bodies and heads slightly toward each other to show the relationship
- Settle each contact in one place
    + Holding hands: one place, where the front person's hand wraps the other's
    + An arm over the shoulder: two places, the forearm seen over the shoulder line behind the neck and the hand resting on the far shoulder
- Show a height difference with the height of the crown and keep both people's feet on the same ground line
- Start a scene with one eye level and one vanishing point
    + The eyes of a standing person lie near the horizon of a standing viewpoint
    + A seated viewpoint (eye level 1.2 m) lets people rise above the horizon and gives a talking scene intimacy
- The camera computes people's sizes from depth; never size them by eye
- When people look small, shrink the stage or lengthen the lens (raise `focal`) to move closer
- Split furniture into what is behind people and what is in front of them and place it on the right side of the people

## Defect table

| Symptom | Cause | Fix |
|---|---|---|
| Isolated shadow blots at shape edges | the inflation grid is coarse for a large shape | raise `config.POISSON_MAX_SIDE` or lower `bulge` |
| Steps or ledges between two connected shapes | the widths at the junction differ | compute the junction width of both shapes with the same formula |
| A joint bulges like a ball | the start cap of a ribbon shows outside the outline | move the joint inward or widen the base shape to fill the hollow |
| A line crosses inside the same skin | the whole closed outline is inked | give only the needed stretches with `Line.paths` |
| A shape end vanishes transparently into the air | the `fade_t` range lies outside the base shape | shrink the fade range into the overlapping area |
| Small loops at curve corners | duplicated control points make the curve double back | remove duplicates and join two curves |
| The far eye of a turned face is cut off | `yaw` too large | reduce to within 0.45 |
| Details spill outside the base shape | `clip` missing | set `clip` to the base shape's name |
| The face smears in the painterly style | brushes too large, no focus set | lower `scale`, raise `focus` on the face shapes |
| The painterly surface is covered in bumpy patterns | too much paint thickness shading | lower `relief` to 0.10 or less |
| Painterly colors look blotchy | too much color variation per stroke | lower `jitter` to about 3 |
| The whole picture looks hazy | bloom and diffusion glow stacked | lower `bloom` strength or `diffusion` strength |
| Bright areas blow out to white | accumulated glow | lower the glow strength, check `clipped_white` in `review.stats` |
| Window grids of distant buildings look like moire | not enough supersampling | raise `city.SUPERSAMPLE` |
| Vertical stripes on ridge surfaces | shading computed from the horizontal slope only | lower `slope_light` of `ridge_layer` |
| The outline bulges like a lump at a joint | the start cap of a limb shows outside the base outline | set the ribbon's `round_start=False` or move the joint inward |
| A shading band like an underwear line on the lower trunk | edge shading of the trunk shape | give the trunk `shape_with` naming the thigh shapes |
| Skin looks flat like plastic | no gloss and no form shading | `gloss` 0.5-0.7, `modeling` 0.5-0.7, style `rim` 0.4-0.6 |
| A dark wedge on the inner thigh | the shadow side of the near thigh overlaps the form shading | lower `modeling` |
| Clothes cover a hand resting on the hip | the clothes are drawn after the arm | give the clothing shape `under=["arm_left"]` or the key of the arm in front |
| The thigh pokes out beside a dress | the dress side line ends at the pelvis | extend the side line along the outer thigh line (`figure.thigh_outer`) |
| The knee of a sitting leg looks like a circle | the shin is drawn in front of the thigh | for a bent leg, put the thigh in front |
| The shoulder of the arm behind the trunk rises like a lump | the arm's start cap shows above the shoulder line | start the arm behind a little below the shoulder joint |
| Clothing color stains the arm or hand | the `clip` target is the whole body group | limit `clip` to a list of the relevant shape names such as trunk and thighs |
| A line breaks off inside a shape | the start and end tapers are long | set `Line(taper=(False, True))` |
| Two legs read as one lump like a mermaid tail | both thighs were inflated as one mass so the shading between them vanished, and the joint zone covered below the crotch so the line between them was left out | tie each thigh only to the trunk with `shape_with` and shrink `THIGH_JOINT` to end above the crotch |
| A dark band starts on the outer thigh at hip height | different `bulge` between trunk and thigh shades one mass differently | give the shapes tied with `shape_with` the same `bulge` |
| The trunk's armpit outline shows through on the arm | the trunk outline passes inside the arm's joint fade zone | move the trunk's shoulder and armpit outline inside the arm's start point |
| A male chest reads as breasts | the outer line of the pectorals curves round up to the armpit | add `joints` on the outer side to drop that ink, make the lower line straighter |
| Polygon edges show inside shorts | the outlines of several polygons are inked separately | give the shape a `merge` |
| Vertical color bands on sleeves | the shading of a cylinder-shaded sleeve differs from the flat shirt panel | draw the sleeve as `polys` with the same `bulge` as the panel |
| Objects look tilted | several `Desk`s used in one scene | draw every object with one `Desk` |
| Screen content spills outside the screen | `clip` missing on the content shapes | set `clip` to the name of the glass shape made by `screen()` |
| A male face looks too young | wide cheeks, no face plane shading | narrow the cheek width in `WIDTH_KEYS_MALE`, `shading` 0.6 or more |
| Face shadows look like bruises | soft round shading shapes | replace them with crisp plane shadows (`FACE_PLANE`) |
| A painterly figure looks like a mannequin | not enough rounding of the forms | `FigureSpec.form` 1.5-1.8, `modeling` 0.9 or more |
| Short hair looks like a helmet | the hair is as thick at the sides as at the crown | thick on top and thin at the sides (`SHORT_VOL`), add hair tufts on the outline (`SHORT_TUFT`) |
| Trouser or sleeve ends are cut short | the last point is dropped when thinning the tube axis | always keep the end point in the axis samples |
| A sleeve shoulder rises like a lump | the sleeve starts above the shoulder joint | start the sleeve at the shoulder joint (`SLEEVE_ROOT` 0) |
| The arm outline shows inside the sleeve | the body ink is drawn after the sleeve | add the sleeve right after the arm in another group (`outfit`) to hide the earlier ink |
| High heels cross in an X from behind | feet seen from behind are rotated by the toe-out angle | feet seen from behind follow the shin direction only and ignore the toe-out angle |
| The trunk in profile is as thin as a board | not enough trunk depth | `SIDE_DEPTH` 1.1-1.2, stronger hollow of the lower back and projection of the buttocks |
| A V notch in a skirt hem in profile | the ends of two legs spread front and back are joined in the front-view order | draw the cloth between the legs as the convex hull of the leg end points |
| Two trouser legs read as one lump in profile | both leg tubes are filled as one shape | draw the far leg tube first as a separate, darker shape |
| A seated person's buttocks poke out of the trousers | the bottoms are cut from the trunk only and miss the seat mass | include the seat mass (`geo["seat"]`) in the cut of the bottoms |
| Holes in the clothes of two overlapping people, or one person's clothes painted on the other | both people have the same shape names and keys, so `clip` and `under` refer to each other | give each person a `FigureSpec.ident` |
| An arm over the shoulder rises above the head | the elbow was solved on the upper solution | lay the forearm level on the other person's shoulder line and shorten the upper arm to send it back |
| Several circle outlines inside a tree crown | each leaf mass polygon is inked | give the crown shape a `merge` so only the outer outline is inked |
| People look small in an interior | the stage is deep and the angle of view wide | reduce the stage depth, raise `Camera.focal` |
| The hands of a person at a desk catch on the desk's front edge | the arm height of the pose differs from the perspective desk height | adjust the desk height or the forearm angle |
| A V neck in profile looks like a hand gripping the neck | a deep V neck in profile makes a wedge of skin | keep V necks shallow in profile (`SIDE_NECKLINES["v"]`) |
| Clothes merge with the skin into one color in the poster style | clothing and skin hues are close | change the clothing color to a hue far from the skin |
| Pencil lines look doubled | both sides of a thin line are drawn again as outlines | keep the line detection of `pencil`, lower `contour` if needed |
| A person in a night scene looks bright as if cut and pasted | the key light is daytime white | lower `key_tint` and `ambient` as in `neon` and add a rim light |
| The umbrella shaft passes behind the face | the fist is on the body's center line | raise the forearm to bring the fist beside the face above the shoulder |
| Watercolor paint areas look like digital noise | pigment granulation too fine and strong | lower `granulation`, enlarge the large blotches with `pigment` |
| A light wedge at the edge of wavy hair | back hair strand bundles poke out of the wavy mass and the background shows through their transparent start | sample the strand bundles densely from the mass half-width table so they follow the same waves |
| Stubble looks like a brown smudge | the beard color is painted straight onto the skin | mix in a blue-gray, `alpha` about 0.2, `blend="multiply"` |
| A beard in profile looks like a box | the upper line of the beard ends level below the ear | raise the upper line to the sideburn in front of the ear and join it with the hair |
| The outline of curly hair is a tangled polygon | the outer points of the curl circles are joined in creation order | sort them by angle around the head center before joining |
| People in a crowd are hidden by a near tree or cut off by the frame | placed without regard for the scene's near shapes (`Set.front`) and the picture width | compute the screen x with `cam.scale(z)` and place people clear of near shapes and the picture edge |
| A pointing fingertip is buried in another person's body | a nearer person covers the fingertip | move the other person beyond the fingertip or to a deeper z |
| The forearm of an arm raised behind the head ends bluntly beside the ear | the forearm of a `hidden` hand ends at the wrist joint | the engine extends the forearm toward the middle of the skull (`HIDDEN_REACH`) |
| The legs of a person seated facing us are columns without knees | the foreshortened thigh lines up with the shin and is drawn as one shape | thighs shortened below 0.6 are split into two shapes (`FORESHORTENED_THIGH`); clothes get a knee edge line |
| The road of a low angle breaks off at the bottom of the picture | the near ground of the street picture starts at 2 m | start the ground at the depth of the picture's bottom edge (`GROUND_FILL`) |
| Light or green patches on the cheeks in the poster style | soft face highlights cross a step of the print colors | face highlights carry `accent=True` and are left out by styles without highlights |
| A person looks as if standing on furniture behind them | `back` was added whole before the people | place people among the furniture in depth order with `scene.add(s.arrange((z, parts), ...), s.front)` |
| A monitor or coffee machine sinks into the furniture under it | the object on top is sorted at a depth farther than its support | give it the same depth as its support with `stage.placed` |
| The steps of a crowd look duplicated | one walk preset applied to everyone | give each person a different point and length of stride in `walk(phase, stride)` |
| A night interior is as bright as day, or the window shows a blue sky | the day template used as it is | apply `.night()` to the template; strengthen the light on people with the style (`neon`) or the glow of a screen held in the hand |
| The head is cut off at the top in a close shot | a seated eye-level camera looks up at a near person | give the template `eye=1.55` and a `horizon` higher in the picture |

## Varied people

- Sample sheets change one `HeadSpec` field per cell from one base face so the differences read
- In a crowd, vary at least three of age, hair style, skin color, expression and pose per person
- For old age raise `age` and `gray` together and support it with pose and props (a mug, glasses)
- At a head height of about 60 px or less, wrinkles and freckles hardly read, so tell people apart with large differences such as hair style, facial hair, glasses and skin color

## Drawing group shots

- With more than 4 people, split the depth into 2-3 rows and sort them by depth together with the furniture using `Set.arrange`
- Keep at least 0.6 m between people at the same depth; where they overlap, stagger x so faces are not covered
- For two people facing each other in `pair.conversation`, the listener is on screen-left (`TALK_LISTEN`) and the talker on the right
- A pointing arm passes at the height of other people's heads, so keep at least 1 m from them
- Put a table in front of a seated person between the body and the arms with `inserts`, and seat the person about 0.8 times the table depth behind the table's front edge so the hands land on the table

## Drawing objects

- A desk scene must share one `Desk` so the obliques of all objects are parallel
- Add objects from the back (larger z) so front objects hide those behind
- In a night scene keep the desk and walls dark and add light with `glow` (screens) and `light` (lamps)
- Small objects (mouse, phone, game pad) must keep their real size ratios for the scale of a desk scene to read
- Edges that tend to vanish in brushwork styles (windows, frames) are separated with a light border shape instead of a line

## Reference techniques

- Brush repainting: Hertzmann (1998), Painterly Rendering with Curved Brush Strokes of Multiple Sizes
- Silhouette inflation shading: Johnston (2002), Lumo: Illumination for Cel Animation
- Head construction: Loomis-style three-quarter face drawing rules (shifting the center line, compressing the far side, showing the back of the skull)
