# Workflow details

> Translated from the Korean original. See the translation notice in `SKILL.md`.

## Contents
- How to ask planning questions
- What each option decides
- Art-direction note
- Rough checklist
- Revision loop
- Result report format

## How to ask planning questions

- Before asking, pull out the items the request already settles
    + Example: "a watercolour of a lake at sunset" settles subject=landscape, style=watercolor, lighting=golden_hour
- Ask only about the remaining items that change the result a lot
    + Priority: style, aspect ratio (purpose), composition and crop, lighting, colour mood
    + For details such as hair colour and eye colour, apply the defaults and state them in the report
- Offer 3-5 choices with the default marked
    + Print the full list with `python scripts/brief_menu.py`
- If the user answers "up to you" or "defaults are fine", go on without further questions
- If the style is undecided, render candidates with `--styles` after the rough and let the user pick

## What each option decides

| Option | Key | Decides |
|---|---|---|
| Subject | subject | Modules to use and the default aspect ratio |
| Style | style | Medium, face drawing mode, finishing passes |
| Purpose | purpose | Aspect ratio (icon, poster, book_cover, wallpaper and so on) |
| Aspect ratio | format | Canvas size; auto derives it from purpose and subject |
| Figure crop | framing | face, bust, half, three_quarter, full |
| Composition | composition | Position of the subject and height of the horizon |
| Figure angle | view | front, three_quarter, profile, back |
| Detail | detail | 1-5, resolution scale and density of elements |
| Palette | palette | Colour-wheel scheme or a named palette |
| Colour temperature, saturation, value key | temperature, saturation, key | Colour grading in the finishing stage |
| Lighting | lighting | Light direction, colour, shadow colour, atmosphere |
| Mood | mood | Yardstick for expression, colour scheme and lighting |
| Background | background | plain, simple, landscape, city, interior, abstract |
| Character settings | sex, jaw, hair_style, fringe, hair_color, eye_color, beard, skin, expression, pose, outfit | Character appearance |
| Finish | finish | style_default, clean, film, glow, aged |

- Items `Brief` handles itself: aspect ratio, detail scale, lighting, face drawing mode, character creation (`brief.character()`), colour grading and finish (`brief.finish_passes()`)
    + With `sex="male"` the figure gets 0.15 extra heads of height; without a hair choice it gets `crop` with `side_part`, and the beard value adds stubble
    + With `hair_style="beanie"` the fringe becomes none unless one is given; the hoodie and turtleneck outfits are the basic doomer sets
- Items the scene script carries out: composition, background, palette, mood
    + For the palette, draw colours with `palette.harmony(key, scheme)` or `palette.NAMED[name]` and use them for the background and clothing
    + For the composition, place the subject on the coordinates from `compose.thirds(canvas)` or `compose.golden(canvas)`

## Art-direction note

- Save the output of `brief.to_markdown()` as `brief.md`
- Sections: key message, space and structure, colour and tone, character, finish
- Items that took a default are marked "(default)"
- Add these to the note yourself
    + The one point where the eye should rest
    + Value plan: the lightest and the darkest place in the picture
    + Colour plan: one dominant colour, one or two secondary colours, one accent colour

## Rough checklist

- Composition: is the subject where it was meant to be (centre or a thirds intersection)?
- Crop: does the frame avoid cutting the figure at a joint (wrist, knee, ankle)?
- Three values: do subject and background separate into different value masses?
- Focal point: is the strongest value contrast at the focal point?
- Breathing room: is there space around the subject and along the edges?

## Revision loop

- Pin down one defect at a time and fix it (changing several values at once hides the cause)
- Decide which stage to revise
    + Shape, position and proportion problems: the structure code in `build`
    + Value-mass problems: the lighting (`--light`, `Light` arguments)
    + Texture, bleeding and brushwork problems: the style parameters (`paint(..., params=...)`, or `style_params` in the dictionary a scene's `build` returns)
    + Colour and contrast problems: the finishing passes
- After fixing the structure, check the rough again
- Loop limit: if three rounds of review and revision do not converge, share the current result and the remaining defects with the user and ask for direction

## Result report format

- The final image file
- The choices: separate what the user specified from what took a default
- How to reproduce: scene script path, run command, seed
- Any remaining limitation in one or two lines
