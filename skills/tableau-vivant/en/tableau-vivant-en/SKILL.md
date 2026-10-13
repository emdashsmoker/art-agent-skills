---
name: tableau-vivant-en
description: "Draws pictures with code: build a stage, pose people on it, then paint the scene. A parametric human body with correct hands and faces is posed, dressed and placed with props in 3D rooms, cities or landscapes, then painted in many media, from anime cel, manga and watercolor to ukiyo-e, oil, impressionism and charcoal. The results taste of a tableau vivant: smooth skin, crisp silhouettes, poses held as if breath were stopped, stage-like light, deliberate composition; the same spec and seed give the same picture. Use whenever asked to draw or paint people, scenes or still lifes in a style or art movement, on '/tableau-vivant-en' or 'draw with code', or where no image API exists. Not for charts, diagrams, UI mockups, logos or photo editing. References: references/planning.md (brief), references/spec.md (fields), references/figures.md (bodies, poses, outfits, pairs, groups), references/scenes.md (settings, props, camera, light), references/styles.md (styles, fixes), references/extending.md (extending, limits)."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and THIRD_PARTY_NOTICES.md
---

# tableau-vivant-en

> **Translation notice.** This skill is an English translation of the Korean original `tableau-vivant`. Meaning can shift in translation, so the logic, behaviour and performance of this version may differ from what the original intends.

An engine that draws pictures with code, and the procedure for using it

## Principle

- A picture is split into a form layer and a medium layer
    + (Form layer) Bodies, hair, clothing, props and terrain are built as 3D geometry. Five fingers are guaranteed by the mesh topology
    + (Medium layer) The same geometry buffers are redrawn as brushwork, bleeding washes, lines and paper grain. Changing the style is a one-line change of medium
- The model plays the painter's judgement
    + Decide what to draw, with which composition, light and style, and record it as a spec (JSON)
    + Look at the rendered result yourself and fix it. A picture is rarely finished in one pass

## Procedure

Each step's output is the next step's input. Skipping ahead makes rework expensive

### 0. Install (first)

```bash
bash scripts/install.sh        # once. Installs PyTorch CPU, the body model and the rest. The first run builds a model cache in about 1 minute
```

- Run this before anything else. If installation fails, report the error to the user and stop
- In a local environment, follow the user's own virtual-environment rules before running it

### 1. Planning

- Separate what the request already fixes from what it leaves open
- Ask about the open items in one batch, using the option tables in `references/planning.md`
    + Axes: purpose, subject and genre, style, figures, composition, lighting, colour, detail, background
    + Mark a recommended default on each axis. If the user says "you decide", go ahead with the defaults and state the values applied
- If the user has already specified enough, skip the questions and proceed

### 2. Design

- Write the design direction document (`brief.md`) first. The template is at the end of `references/planning.md`
    + Record one core impression, the composition, colour and tone, light, and the reason for the style chosen
- Turn the direction document into a spec file (`spec.json`). Fields are in `references/spec.md`
    + Starting from the nearest example in `examples/` is fastest

### 3. Check the underdrawing

```bash
python scripts/render.py spec.json -o check.png --preview     # seconds. Checks pose, composition and light only
python scripts/pose_sheet.py -o pose.png --spec spec.json     # checks the pose from the front and the side
```

- Open the result image and look at it. Settle pose and composition before painting, or the painting gets redone
- If a hand sinks into the body or floats in the air, fix it with `reach` (a target point for the hand). A hand resting on a body takes `"lay": true` to lie palm flat. See `references/figures.md`
- A person holding a book, cup or phone holds it through the prop's `held_by`. Do not guess coordinates
- For people facing each other, give `facing` the name of the other person or of the table
- Two people touching each other use `pairs`; a row of three or more touching their neighbours uses `groups`. For people in a landscape, frame them with the camera's `fit: "people"`

### 4. Painting

```bash
python scripts/render.py spec.json -o picture.png
python scripts/render.py spec.json -o sheet.png --styles anime,watercolor,oil   # when styles need comparing
```

### 5. Review and fix

Open the finished image and check the items below. If there is a defect, fix the spec and render again

- Is any face hidden by hair, hands or shadow?
- Are hands and feet where they were meant to be, without passing through the body?
- Are garment cut lines and hair ends clean?
- Is the subject large enough in the frame and not cropped?
- Does the light and dark contrast gather toward the subject?
- Can the style's own traits (line, brushwork, bleeding) be read?
- Is every condition the user gave (figure traits, colours, props) reflected?

For how to fix things, see the "Problems and fixes" table in `references/styles.md`

### 6. Delivery

- Deliver the finished image together with the spec file and the design direction document
    + With the spec file the user can re-render with only the seed, style or composition changed
- State plainly whatever was not achieved

## Reference documents

| Document | When to read |
| --- | --- |
| `references/planning.md` | When preparing planning questions, when writing the design direction document |
| `references/spec.md` | When writing a spec file (all fields) |
| `references/figures.md` | When people appear (female and male builds, face stylisation, expressions, poses, hands, held props, pairs and groups, hair, beards, outfits) |
| `references/scenes.md` | When choosing backgrounds, props (from classical still life to computers and modern furniture), camera (including low angle, dutch tilt, over the shoulder) and lighting |
| `references/styles.md` | When choosing or tuning a style, recreating art movements, the doomer family, fixing problems |
| `references/extending.md` | When a form or style is not in the catalogue, checking limits |

Print every option with `python scripts/catalog.py [figures|poses|hair|outfits|props|environments|light|styles|post|shapes]`

## Dependencies and licences

- Runtime: Python 3.10 or later, CPU only. No GPU and no external API calls
- Packages: numpy, scipy, opencv-python-headless, pillow, numba, torch (CPU), anny 0.6.1, roma, safetensors, trimesh, pyyaml
- The body model Anny is Apache-2.0; the MakeHuman meshes it is built on are CC0
    + No further restrictions on using the pictures produced

## Ground rules

- Age is not limited. Children and teenagers can be drawn clothed
- Figures under 18 are never drawn unclothed, in underwear or in a sexual staging
    + The engine refuses outfits that leave the chest or pelvis of an under-18 body bare (unclothed, underwear, bikini, `perizoma`). Swim trunks and shorts on a boy are allowed
    + Age follows the body model's own age calibration (`age` 0.77 is 18 years). A figure the request sets up or introduces as a minor is treated as under 18 as well
    + Adult presets' bust shaping is not applied to an under-18 body
- Figure studies of adults 18 and over are supported. The body model has no pelvic detail, so that area is rendered smooth
    + Anime-style or youthful faces, a small build and a short height are not restricted
    + Male figure studies look natural when composed with the classical `perizoma` or with `briefs`
- The same spec and seed reproduce the same picture. Vary it by changing `canvas.seed`
- Treat the limits honestly. Complex folds, realistic hair strands and photographic texture are currently out of scope. Details in `references/extending.md`
