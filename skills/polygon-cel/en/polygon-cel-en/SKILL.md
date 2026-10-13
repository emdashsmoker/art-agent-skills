---
name: polygon-cel-en
description: Draws illustrations shaped as polygons and painted as cels. Formulas build every form (head-height proportions, 3D hand skeletons, solids of revolution, perspective streets, fractal mountains) with no diffusion model, so one JSON spec always renders the same picture. The base look is bold colored line art, crisp two-tone cel shading, volume shading that rolls off the edges, and a calm muted palette; scenes can also be finished as soft illustration, oil paint, or watercolor. Draws young adult women and men (closeup to wide shot, any view, sitting, lying, holding props, two-shots, groups), still lifes, landscapes, streets, and interiors. Spec fields are in references/spec.md, process principles and the defect table in references/process.md, extension recipes in references/extending.md. Use when the user says '/polygon-cel-en', 'draw with code', 'anime character', 'couple illustration', 'still life', 'cityscape', 'cel shaded', 'watercolor style', or needs a reproducible picture without a GPU or an image model.
license: GPL-3.0-or-later (full text in LICENSE, output permission and dependency notices in THIRD_PARTY_NOTICES.md)
---

# polygon-cel-en

## Translation notice
- This skill is an English translation of the Korean original (polygon-cel)
- The translated instructions may steer the model differently, so performance and logic can differ from the original
- The rendering engine (scripts/) and the example specs (assets/examples/) are the same files as in the original

## Overview
- Illustration engine that implements the drawing process (planning, construction, form, line art, coloring, style, finishing) as one code module per step
- Uses only numpy, OpenCV, and skia-python, with no model weights
- The same spec and seed always produce the same picture
- The operator (a person or an LLM) writes the scene spec and reviews the render
    + Form knowledge (proportions, faces, hair, garment construction) is built into the engine
    + The principles of each step are in references/process.md

## Scope
- Subject: character, still_life, landscape, city (street), interior
- Characters: female or male template with young adult proportions
    + View: front (front up to about 35 degrees to the side), back (seen from behind, looking back over the shoulder), side (profile)
    + Framing: closeup (face), bust, waist, full (full body), wide (establishing shot with a small full-body figure in the scene)
    + Full-body postures: 3 standing stances, walk, lean (against a wall), sit (chair, stool, bed edge), lie (on a bed)
    + 11 arm poses: 7 basic poses, arms crossed, chin rest, hair tuck, hands behind head
    + 6 hand gestures
    + Held props (body.hold): a phone, a canned drink, or a cigarette in one hand (front view)
    + Figures: female slim, balanced (default), curvy; male slim, balanced (default), athletic
    + Male muscle definition: body.muscle 0-1 (defaults slim 0.10, balanced 0.30, athletic 0.50)
    + Bust size: small, medium (default), large, xlarge (female)
    + Face: 4 face shapes, face length, 3 noses, 3 lip types, 4 lash levels, iris size, brow thickness
    + Hair: long, bob, ponytail, short
    + 17 tops: 6 casual (knit, shirt, hoodie, crop top, tank top, tee), 5 swimwear (bikini, one-piece swimsuit, rash guard, beach shirt, shirtless), sportswear (sports bra), 3 party dresses (slip dress, halter dress, off-shoulder dress), 2 homewear (camisole, oversized tee)
    + Office look: shirt with a tie or a bow, combined with slacks or a pencil skirt (shirt tucked in automatically)
    + 11 bottoms: A-line skirt, pencil skirt, jeans, slacks, leggings, joggers, dolphin shorts, bikini bottom, board shorts, swim briefs, boxer briefs
    + Shoes: sneakers, boots, sandals, heels, dress shoes, barefoot
    + One line `"gender": "male"` applies the male face, hair, skeleton, and outfit defaults at once
    + Revealing outfits show adult figures with anatomically plausible skin forms (female bust volume, male pectorals and abs)
    + The bust is expressed with volume and shading; the engine has no layer that draws nipples or genitals
    + The front panel of swim and underwear bottoms renders as a smooth surface
    + Backgrounds: plain, gradient, sky, bokeh, window, beach, bed, 5 interiors, landscape scene, city street scene
    + Head accessories: hairpin, earrings, beanie; body accessory: necklace
- Two-shots and groups: 2 or more characters in characters (no limit on head count or gender mix)
    + Framing: waist, full, wide
    + Contact (2 characters only): hand holding (hand_hold, front and back views), arm over the shoulder (shoulder_arm, front view)
    + 3 or more stand or sit side by side, heads turn toward the group center
    + Multiple rows (pair.rows): back rows stand smaller and higher, so their faces show between the heads of the front row
    + More people widen the canvas automatically; past 4096px the figures shrink to fit
    + Two profiles face each other automatically
    + View, pose, outfit, and height scale (place.scale) per character
- Still life: 9 classic objects (vase, bottle, cup, mug, jar, 4 fruits), 9 modern objects (laptop, monitor, keyboard, mouse, smartphone, headphones, desk lamp, books, potted plant)
- Interiors: bedroom, office, cafe, pool, gym (as a scene of their own or as a character background)
- Styles: anime_cel, soft_illust, painterly, watercolor (shared by every subject)
- Mood: 1 preset, doomer (late-night solitude)
    + Bundles a cold desaturated grade, film grain, vignette, a night street with power lines, and a blank face with tired eyes as defaults
    + Also applies to landscapes and cityscapes (night time, moon and stars, power lines)
- The skill does not depict minors in nudity or in sexual content, including sexual acts
    + (Stated minor) a character whose age under 18 or status as a minor is stated in the spec or the request
    + (Child body) a character requested to be drawn with a prepubescent child body
- Tell the user up front that photorealism is out of scope

## Setup
- Paths are relative to the skill folder: `scripts/render.py`, `scripts/selftest.py`
- Run the installation check first when work starts
```bash
python scripts/selftest.py || pip install -r scripts/requirements.txt
```
- If the environment policy requires it, choose pip options (virtual environment, `--break-system-packages`, and so on) to suit the environment

## Workflow

### 1. Read the request and write a design brief
- Before rendering, write a 5-line brief and share it with the user
    + (Key message) one sentence on the mood the picture conveys
    + (Style) the chosen style and why
    + (Composition) for characters the framing, head direction (yaw), and pose; for scenes the subject, time of day, and object layout
    + (Palette) one main color and supporting colors
    + (Lighting) key light direction and whether there is a rim light
- Fill items the user left open with the defaults below and state them in the brief
    + A character-centered request uses bust; waist when hands or outfits matter; full for full-body styling
    + Show the hands with the wave or hand_on_hip pose; hide them with the behind or pocket pose
    + A request about the expression uses closeup; everyday scenes use an interior background with the sit or lean pose; resting scenes use the lie pose
    + A back-view request uses view back with head.yaw 25-35 (face looking back over the shoulder); a profile request uses view side
    + A request for two people uses 2 characters; close relationships use hand_hold or shoulder_arm; waist for the upper body, full for walking and styling
    + In a two-shot the man gets place.scale 1.06; leave out head directions (the default turns them toward each other)
    + For 3 or more people list that many entries in characters and leave out pair.contact
    + Keep the default male muscles; use body.muscle 0.7-1.0 only when the request stresses muscles
    + A lonely night or doomer-mood request uses mood doomer, a dark hoodie and a beanie, and one of a phone, a canned drink, or a cigarette in hand
    + An establishing shot where the scene leads and the figure stays small uses framing wide with place.x 0.3-0.4
    + Groups of 7 or more, or class-photo compositions, use pair.rows 2
    + When a seated figure must read clearly use view side with pose sit; a closeup needs a top with a high neckline
    + Without a requested style use anime_cel for characters, painterly or watercolor for still lifes and landscapes, anime_cel for cities
    + For color apply the palette guidelines in references/spec.md
- If an ambiguous key element (style, framing) would change the result a lot, ask once before rendering

### 2. Write the spec
- Check fields and allowed values in references/spec.md
- Copy an example spec from assets/examples/ as a starting point and edit it
- Save the spec file in the working folder as the basis for reproduction

### 3. Draft render and review
```bash
python scripts/render.py spec.json -o draft.png --quality draft
```
- Open the rendered image itself and go through the review checklist
- Find the cause of a defect in the defect table of references/process.md, then fix the spec
- Keep draft iterations to 3 or fewer

### 4. Final render and delivery
```bash
python scripts/render.py spec.json -o final.png --quality final
```
- final renders at 2x resolution and downsamples, so lines are smoother (takes about 3 times as long)
- Deliver the final PNG and the spec JSON used
- To inspect the process, `--passes DIR` saves the color pass, the line pass, and the character masks

### 5. Requests the spec cannot express
- Extend the engine for new outfits, hairstyles, backgrounds, or styles with the recipes in references/extending.md
- Before extending, tell the user the added scope and the expected limits, then confirm whether to proceed

## Review checklist
- Face: both eyes balanced in size and height, iris highlights on the side of the light source
- Hair: bang tips do not cut the face outline awkwardly, back hair does not look like a flat board
- Body: shoulder to neck connection, sleeve to bodice seams, fingers not tangled
- Male: collar and neckline fit the thick neck, shorts split into two legs, crown locks do not stick out like spikes
- Back view: hands do not rest on the buttocks, back hair over the back does not clump into a dark mass
- Profile: the bust joins the body silhouette, bang tips end in a point in front of the forehead
- Two-shots and groups: feet on the same ground, lines of a back figure do not show through a front figure, no figure touches the canvas edge
- Multi-row groups: back-row faces show between front-row heads, the back row is smaller than the front row
- Held props: the held object goes under the fingers and reads as gripped, fingers around a can or a phone end in rounded knuckles at its edge, hoodie drawstrings do not run over the holding hand, cigarette smoke does not ride up the sleeve
- Wide shot: the small figure's head, hands, and feet do not sink into the scene
- Two-shot contact: the held hands meet between the two figures, the forearm over the shoulder comes out from behind the partner's neck and rests on the far shoulder
- Posture: seated thighs rest on the chair, a lying figure fits entirely in the canvas, the sleeve of a raised arm follows the arm
- Still life: objects do not sink into each other, shadow directions match the light source
- Interiors and modern objects: furniture and object tops share the same viewing slant, screen content stays inside the screen frame
- Landscapes and cities: the distance is hazier and lighter than the foreground (aerial perspective), lines converge on the vanishing point
- Color: one main color, a background with lower contrast than the subject
- Style: check for smudged faces in oil and the shape of the paper fade in watercolor; a watercolor night picture does not wash out white like daytime
- Canvas: margin around the subject

## Request to spec examples
- Request: "Rainy afternoon, a bob-haired woman smiling by the window, watercolor"
```json
{"style": "watercolor", "framing": "bust",
 "character": {"head": {"yaw": -14, "roll": 3},
   "hair": {"color": "#3A2E30", "style": "bob", "bangs": "full"},
   "eyes": {"color": "#6B7FA8", "shape": "droopy"},
   "expression": {"mouth": "soft", "blush": 0.3, "eye_smile": 0.2},
   "outfit": {"type": "knit_sweater", "variant": "crew", "color": "#D9CFC2"}},
 "lighting": {"key": "upper_right"},
 "background": {"type": "window", "colors": ["#DDE3EA", "#B9C3CF", "#F2F5F8"]}}
```
- Request: "Autumn walk, full body, off-shoulder dress, hands behind the back, soft illustration"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"head": {"yaw": 12}, "body": {"pose": "behind"},
   "hair": {"color": "#6B3F2E", "style": "long", "bangs": "parted", "wave": 0.4},
   "outfit": {"type": "offshoulder_dress", "color": "#B8866B", "shoes": "boots"},
   "accessories": ["necklace"]},
 "background": {"type": "gradient", "colors": ["#F6E3C8", "#D9B48F"]},
 "post": {"grade": "sunset"}}
```

- Request: "Bob-haired woman laughing and waving, shirt, waist-up"
```json
{"style": "anime_cel", "framing": "waist",
 "character": {"head": {"yaw": -12, "roll": 4}, "body": {"pose": "wave"},
   "expression": {"mouth": "open_smile", "eye_smile": 0.2},
   "hair": {"style": "bob", "bangs": "full"}, "outfit": {"type": "shirt", "bottom": "a_line_skirt"}},
 "background": {"type": "window"}}
```
- Request: "Woman in a bikini waving on the beach, full body"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"head": {"yaw": -10}, "body": {"pose": "wave", "stance": "contrapposto"},
   "expression": {"mouth": "open_smile"}, "hair": {"style": "ponytail", "bangs": "full"},
   "outfit": {"type": "bikini", "variant": "triangle", "bottom_style": "high_leg", "shoes": "sandals"}},
 "background": {"type": "beach"}}
```
- Request: "Muscular man standing on the beach, board shorts, full body"
```json
{"style": "anime_cel", "framing": "full",
 "character": {"gender": "male", "head": {"yaw": -10},
   "body": {"figure": "athletic", "stance": "contrapposto", "pose": "hand_on_hip"},
   "expression": {"mouth": "smile"}, "outfit": {"type": "shirtless", "bottom": "board_shorts"}},
 "background": {"type": "beach"}}
```
- Request: "Woman with a bob, a round face, full lips, and heavy lashes"
```json
{"style": "anime_cel", "framing": "bust",
 "character": {"face_shape": "round", "face": {"length": 0.94, "nose": "button", "lips": "full"},
   "eyes": {"shape": "round", "iris": 1.12, "lashes": "heavy"},
   "hair": {"style": "bob", "bangs": "full"}, "outfit": {"type": "shirt"}},
 "background": {"type": "bokeh"}}
```
- Request: "Woman in a hoodie standing on a night street"
```json
{"style": "anime_cel", "framing": "waist",
 "character": {"head": {"yaw": -12}, "body": {"pose": "pocket"},
   "hair": {"style": "bob", "bangs": "full"}, "outfit": {"type": "hoodie", "color": "#B7A8D6"}},
 "background": {"type": "city", "city": {"time": "night"}}}
```
- Request: "Woman in an office look sitting on an office chair, full body"
```json
{"style": "anime_cel", "framing": "full",
 "character": {"head": {"yaw": 10}, "body": {"pose": "sit", "bust": "large"},
   "outfit": {"type": "shirt", "variant": "bow", "bottom": "pencil_skirt"}},
 "background": {"type": "office"}}
```
- Request: "Bikini back view on the beach, looking back over the shoulder"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"view": "back", "head": {"yaw": 32, "roll": -3},
   "body": {"figure": "curvy", "stance": "contrapposto"},
   "outfit": {"type": "bikini", "bottom_style": "high_leg"}},
 "background": {"type": "beach"}}
```
- Request: "Woman in a slip dress, side profile"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"view": "side", "body": {"figure": "curvy", "bust": "large"}, "outfit": {"type": "slip_dress"}},
 "background": {"type": "gradient"}}
```
- Request: "Couple holding hands on a sunset street, full body"
```json
{"style": "soft_illust", "framing": "full", "pair": {"contact": "hand_hold"},
 "characters": [
   {"hair": {"style": "long", "wave": 0.3}, "outfit": {"type": "offshoulder_dress", "shoes": "heels"}},
   {"gender": "male", "place": {"scale": 1.06}, "outfit": {"type": "shirt", "bottom": "slacks"}}],
 "background": {"type": "city", "city": {"time": "dusk"}}}
```
- Request: "Two men with arms over each other's shoulders at the gym"
```json
{"style": "anime_cel", "framing": "full", "pair": {"contact": "shoulder_arm", "lead": 1},
 "characters": [
   {"gender": "male", "outfit": {"type": "tank_top", "bottom": "joggers", "shoes": "sneakers"}},
   {"gender": "male", "body": {"figure": "athletic", "pose": "hand_on_hip"},
    "outfit": {"type": "tee", "bottom": "joggers", "shoes": "sneakers"}}],
 "background": {"type": "gym"}}
```
- Request: "Man and woman facing each other in profile on a night street"
```json
{"style": "soft_illust", "framing": "full",
 "characters": [
   {"view": "side", "head": {"yaw": 0, "roll": 0}, "outfit": {"type": "slip_dress", "shoes": "heels"}},
   {"gender": "male", "view": "side", "head": {"yaw": 0, "roll": 0}, "place": {"scale": 1.06}}],
 "background": {"type": "city", "city": {"time": "night"}}}
```
- Request: "Three friends standing in a cafe, waist-up"
```json
{"style": "anime_cel", "framing": "waist",
 "characters": [
   {"body": {"pose": "wave"}, "expression": {"mouth": "open_smile"}, "outfit": {"type": "knit_sweater"}},
   {"hair": {"style": "bob", "bangs": "full"}, "body": {"pose": "chin_rest"}, "outfit": {"type": "shirt"}},
   {"hair": {"style": "ponytail"}, "body": {"pose": "pocket"}, "outfit": {"type": "hoodie"}}],
 "background": {"type": "cafe"}}
```
- Request: "Desk still life with a monitor and a keyboard"
```json
{"subject": "still_life", "style": "anime_cel",
 "still_life": {"table": "#D8D2C8", "wall": "#DCE2E8", "cloth": null, "objects": [
   {"type": "monitor", "x": 0.42, "depth": 0.05}, {"type": "keyboard", "x": 0.42, "depth": 0.55},
   {"type": "mouse", "x": 0.66, "depth": 0.58}, {"type": "mug", "x": 0.82, "depth": 0.5}]}}
```
- Request: "Mountains and a lake at sunset, oil painting"
```json
{"subject": "landscape", "style": "painterly", "landscape": {"time": "sunset", "clouds": 3}}
```
- Request: "Still life of a lemon, an apple, and a jar with yellow flowers, watercolor"
```json
{"subject": "still_life", "style": "watercolor",
 "still_life": {"cloth": null, "objects": [
   {"type": "jar", "x": 0.32, "depth": 0.2, "flowers": "#F2D35A"},
   {"type": "lemon", "x": 0.52, "depth": 0.7}, {"type": "apple", "x": 0.66, "depth": 0.6}]}}
```
- Request: "Night alley after the rain"
```json
{"subject": "city", "style": "anime_cel", "city": {"time": "night"}}
```
- Request: "Doomer mood, a man in a beanie holding a cigarette on a night street"
```json
{"style": "anime_cel", "framing": "waist", "mood": "doomer",
 "character": {"gender": "male", "head": {"yaw": -12, "pitch": 4}, "eyes": {"openness": 0.72},
   "accessories": ["beanie"], "body": {"hold": {"item": "cigarette", "side": "left"}},
   "outfit": {"type": "hoodie", "color": "#2A2C34", "bottom": "jeans"}}}
```
- Request: "A lone person walking down an empty night street, wide shot, oil painting"
```json
{"style": "painterly", "framing": "wide", "mood": "doomer",
 "character": {"gender": "male", "view": "side", "facing": "right", "place": {"x": 0.36},
   "head": {"yaw": 0, "roll": 0}, "body": {"pose": "walk"}, "accessories": ["beanie"],
   "outfit": {"type": "hoodie", "color": "#2A2C34", "bottom": "jeans", "shoes": "sneakers"}}}
```
- Request: "Office group photo, 7 people, two rows"
```json
{"style": "soft_illust", "framing": "waist", "pair": {"rows": 2}, "background": {"type": "office"},
 "characters": [{}, {"hair": {"style": "bob"}}, {"hair": {"style": "ponytail"}}, {},
   {"gender": "male"}, {"gender": "male"}, {"gender": "male"}]}
```

## Reference files
- references/spec.md: every spec field, allowed values, defaults, palette guidelines (read whenever writing a spec)
- references/process.md: principles of each step, proportion canon, style algorithms, defect table, limits (read when reviewing and debugging)
- references/extending.md: layer model, coordinate systems, stack order, extension recipes (read when modifying the engine)
- assets/examples/*.json: 66 example specs by subject, framing, view, posture, style, gender, outfit, background, two-shot, group, and mood (the 9 starting with duo_ are two-shots, the 4 starting with group_ are groups, the 7 starting with doomer_ use the doomer mood)
