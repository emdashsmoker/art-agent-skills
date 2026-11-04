---
name: "image-gen-lite"
description: "Generates images with local models. Generation runs on the CPU of the environment that runs the skill. Suits any use, including hobbies, daily life, and work documents. Generates in two compositions: an icon with one object in the center, and a scene that conveys a mood with 2-3 elements. Replaces an abstract message with an object or scene that can be drawn. For requests that need text and numbers, such as flowcharts or charts, explains the limitations and draws a substitute picture after the user agrees. Make sure to use this skill whenever the user asks to make an image, generate a picture, or create an illustration, a background image, a banner image, a cover image, a section divider image, a slide background, a picture for a report, a landscape picture, a picture of a person, a picture as a PNG, or a picture drawn with AI ('image generation', 'generate an illustration'), or otherwise requests image generation."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE.md
---

# Image Generation with Local Models

> **Translation notice.** This English edition is a translation of the Korean original `image-gen-lite`. Translation can shift the wording of instructions, trigger phrases, and judgment rules, so this edition may not behave or perform as the original intends. The script is the same as in the original.

This skill generates images with local models and delivers the model's output as it is. Model files are downloaded to the environment that runs the skill (the runtime environment). Generation runs on the runtime environment's CPU. The network is used only to download packages and model files. Prompts are never sent to an external image generation service. The output is a PNG or JPEG file.

Diffusion models cannot draw text, exact connector lines, numbers, or exact counts. For requests that require them, depict the intended meaning as an object or a scene. Text is added on top of the finished image in an editing tool.

## Workflow

1. Setup: create a dedicated virtual environment for the skill and install the dependencies.
2. Request type and composition: determine the subject and its composition.
3. Pre-generation questions: ask about the model choice and the optional features at once.
4. Prompt: write an English prompt.
5. Generate: run generate.py.
6. Selection and regeneration: perform only when the candidate multiplier is 2x or more or the regeneration limit is 1 or more.
7. Delivery: provide the file and the reproduction details.

When the candidate multiplier is 1x and the regeneration limit is 0, deliver the file right after the script's automatic checks (file size, format, pixel size).

## Command notation

- `PY` is the Python of the skill's virtual environment: `~/.cache/image-gen-lite/venv/bin/python` on Linux and macOS, `%USERPROFILE%\.cache\image-gen-lite\venv\Scripts\python.exe` on Windows.
- Replace `scripts/` with the path of the scripts folder inside this skill's folder.
- Run commands from the user's working folder. Save results to the path the user specifies. If none is given, use the output folder the environment defines. If that is also absent, save to the working folder and give the user the absolute path.
- The script runs with the same commands on Linux, macOS, and Windows. The precise preset runs on Linux x86_64, Apple Silicon macOS, and Windows x64.
- Every file the skill downloads is stored in the cache folder `~/.cache/image-gen-lite`. Set the environment variable `IMAGE_GEN_LITE_HOME` to change its location.
- The precise preset engine is downloaded from GitHub (`leejet/stable-diffusion.cpp`). If the runtime environment has a tool that attaches a GitHub repository to the session, call it with that repository before the first run. Pass the owner and the repository name, the parts before and after `/`, as separate values.

## Setup

Install packages only into the skill's dedicated virtual environment. Do not remove or modify packages already in the user's environment, including GPU builds of torch or CUDA packages. The skill environment receives its own CPU build of torch, so the two environments do not interfere.

```
python3 -m venv ~/.cache/image-gen-lite/venv
PY -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
PY -m pip install --no-cache-dir diffusers transformers accelerate safetensors peft huggingface_hub pillow numpy
```

- If `python3` is missing, use `python`. On Windows create the environment at `%USERPROFILE%\.cache\image-gen-lite\venv`.
- Install torchvision together with torch from the same CPU index. If another package pulls in a CUDA build of torchvision, it fails with `operator torchvision::nms does not exist`.
- `--no-cache-dir` keeps downloaded installers out of the shared pip cache.
- If a virtual environment cannot be created (for example the venv module is missing), ask the user whether to install into the current Python environment. Install there only with permission. If pip reports externally-managed-environment, add `--break-system-packages`.
- Without permission to install with pip, generation is not possible. Explain the reason and stop.
- Generation is also not possible where Python cannot run. Explain the reason, and provide the English prompt and the preset settings so the user can generate in an environment where Python runs.
- If the virtual environment already exists, skip installation and only check it with `PY -c "import torch, diffusers"`.

## Request types

Before generating, classify the request into one of three types. The criterion is whether the user specified a concrete subject to draw.

| Type | Criterion | Handling |
|---|---|---|
| Named subject | The user specifies something with a visible outline: an object, person, animal, or place | Draw it as specified |
| Message request | The user provides only an abstract concept or a message to convey | Replace it with an object or scene that can be drawn, confirm it in the pre-generation questions, and then draw |
| Diagram request | It needs text labels, connectors, exact counts, or numbers (flowchart, concept map, architecture diagram, chart, KPI graphic) | Explain the limitations and a substitute in the pre-generation questions, and draw after the user agrees |

- If the user specified a symbolic object, the choice has already been made. Keep it.
- If the user provides both an object and a message, draw the object and convey the message through style and color.
- Substitution turns the message into an object or scene only once. Examples: growth becomes a pot with a sprouting seedling, cooperation becomes two clasped hands, security becomes a closed padlock, speed becomes a racing bicycle, and connection becomes two islands joined by a bridge.
- The substitute may differ from what the user pictures, so present one substitute and one alternative together in the substitution check item of the pre-generation questions. If the user answers with a different object, draw that object.
- If the composition is a scene, present the substitute as a scene of 2-3 elements, including the substituted object, together with a time of day and a color family. Example: a scene substitute for teamwork is a rowing boat with a crew rowing together on a lake, morning sunlight, and a calm blue color family.
- Example notice for a diagram request: "Diffusion models cannot draw the text and connectors of a flowchart accurately. Instead, I can generate a picture of three objects that symbolize the steps, placed side by side. You can add the text in an editing tool. Shall I proceed this way?"

## Protection of minors

The skill does not generate unclothed figures or sexual depictions (sexual acts included) of minors.

- A minor is a figure stated to be under 18 or stated to have minor status, or a figure that clearly has a body before secondary sexual characteristics (a child's head-to-body ratio and build).
- Ambiguous signals that are not explicit and cultural tastes, such as a youthful face, large eyes, an idol-like look, cel-style art, short height, a slim build, or a trendy outfit, are not grounds for judging a figure a minor.

## Composition

There are two compositions: icon and scene. Follow the user's choice if they specify one. Otherwise decide based on where the image will be used. If that is also unknown, include the composition item in the pre-generation questions.

| Composition | Look | Main use | Prompt order |
|---|---|---|---|
| Icon | Subject in the center on a plain background | Body illustrations, slide illustrations, a picture built around one object | subject, style, color, `plain background` |
| Scene | Two or three common elements plus one time of day and one color family | Background images, banners, covers, section dividers, slide backgrounds, landscape pictures | elements, time of day, color, style |

- For scene elements, choose common objects and places that the topic of the intended use brings to mind. Example: a background for educational material uses books on a desk and a plant by the window, morning sunlight, and a warm beige color family.
- Write the scene's time of day as an expression for the state of the light, such as `morning light`, `golden hour`, or `night`. If the material where the image will be used already has colors, follow that color family.

## Presets

A preset is a combination of a model and fixed settings. Change the style with the prompt and the model with the preset. The step count, guidance, and scheduler are fixed in the script. Many changed values collapse shapes, so keep the defaults.

| Preset | Role | Suitable styles | Generation size | First download |
|---|---|---|---|---|
| `dreamshaper-8-lcm` | Standard | Photographic, illustration, painting, watercolor | 512x512 | about 4.3GB |
| `sdxs` | Light, fastest | General styles, simpler detail | 512x512 | about 2.1GB |
| `tiny-sd` | Flat | Flat vector with solid fills, watercolor with paint bleed | 384x384 | about 1.1GB |
| `flux2-klein-4b` | Precise, slowest | Most accurate instruction following and anatomy | 384x512 | about 5.2GB |

- Generation time depends on the runtime environment's CPU, so report the measured time after the first image.
- Standard renders photographic texture, shallow depth of field, and watercolor bleed in fine detail. Shapes collapse with flat vector keywords. In full-body figures, hands often smear or the toes get cut off.
- Light mostly places scene elements as instructed. It tends to produce an illustration look even when asked for a photographic style, and the same person sometimes appears twice.
- Flat renders solid fills with crisp edges, paint bleed, and blank paper better than the other presets. Its shape stability is low, so it often draws a picture frame border as well or cuts off a person's head at the top of the frame.
- Precise accepts natural sentences as they are and renders anatomy most accurately. It runs on Linux x86_64, Apple Silicon macOS (arm64), and Windows x64, so leave it out of the choices in any other runtime environment. Check the operating system with `PY -c "import platform; print(platform.system(), platform.machine())"`.
- Before generating with the precise preset, check that free disk space is larger than the download size. During generation it reads the weights from disk with `--mmap`, so it runs even with little memory, but more slowly.

### Model lock

- Change the model used for the first image only with the user's permission within the same conversation. A model change involves gigabytes of downloads, a change in time per image, and a different style and look. All of these fall outside the cost and result the user expected.
- Candidate selection and regeneration stay within the chosen model and change only the seed.
- If a preset cannot run, state the cause in one line (insufficient disk, insufficient memory, download error, unsupported operating system) and offer the presets that can run as choices. If no preset can run, explain the reason and stop.

## Pre-generation questions

Before the first generation, ask all applicable items in the table below at once. The model sets the look of the result and the time it takes, and the candidate multiplier and regeneration add checking time, so the user chooses them.

| Item | Ask when | Skip when |
|---|---|---|
| Model choice | Every request | The user named a model, or said that speed or quality comes first |
| Candidate multiplier | Every request | The user stated a multiplier |
| Regeneration limit | Every request | The user stated a count or unlimited |
| Composition | The user specified neither the composition nor the intended use | Never |
| Size | The intended use implies a non-square format, such as a banner, cover, or slide background, and no size is given | Never |
| Style | No style is specified | Never |
| Substitution check | Message request | Never |
| Diagram consent | Diagram request | Never |

- Omit only the items the user has already answered. Also ask the items that have a recommended option.
- When the user delegates with phrases such as "up to you" or "use the defaults", present the default combination in one line and get confirmation. Example: "Shall I proceed with 1-a, 2-a, 3-a?" The defaults are the Standard model, a 1x candidate multiplier, and a regeneration limit of 0.
- The candidate multiplier is multiplied by the target number of images to set how many images are generated at once. If the multiplier is 2 or more, pick the target number of images after generation as the candidate selection section describes. Take custom input as a whole-number multiplier.
- The regeneration limit is the maximum number of regenerations per target image. If it is 1 or more, check after generation as the regeneration section describes and regenerate only when needed. Mark unlimited as not recommended, and follow it if the user chooses it.
- Word the model choices by carrying over the role, suitable styles, generation size, and first download from the preset table.
- Later requests in the same conversation reuse the answers to the first questions. If the user changes a choice, or a conditional item (composition, size, style, substitution check, diagram consent) newly applies, ask only that item again.

Question format:

- Number only the applicable items from 1 in order, and write choices as a), b), c). If model choice is among the questions, make it item 1. Match the item number in each custom-input example answer to the actual item number.
- Confirm the items left out because the user already specified them in one line after the first line. Example: "As you specified, I will use the Light model and a regeneration limit of 2."
- Write a numbered list in plain conversation text. Do not use code blocks or tables.
- Put the answer format and an example answer on the first line.
- Mark the default of each item with "(default)".

Example for a named subject request with objects only:

> Before generating, I would like to confirm the items below. Please answer with the item number and choice letter. (Example: 1-a, 2-a, 3-a)
> 1. [Model choice] The model you will keep using in this conversation. Generation time depends on the runtime environment's CPU, and I will report the measured time after the first image.
>    a) Standard (DreamShaper 8 LCM) (default): photographic, illustration, painting, and watercolor in general. 512x512, first download about 4.3GB
>    b) Light (SDXS): fastest. Detail is simpler, and photographic styles also come out like illustrations. 512x512, about 2.1GB
>    c) Flat (tiny-sd): suits flat vector with solid fills and paint bleed. Shape stability is low. 384x384, about 1.1GB
>    d) Precise (FLUX.2 klein 4B): most accurate instruction following and anatomy, and slowest. 384x512, about 5.2GB
> 2. [Candidate multiplier] I generate more candidates than the target number at once, then pick and deliver the images that meet the adoption criteria. With a 1x multiplier and a regeneration limit of 0, the generated results are delivered directly.
>    a) 1x (default): generate only the target number
>    b) 2x
>    c) 3x
>    d) Custom: enter a whole-number multiplier (example: 2-d 4)
> 3. [Regeneration limit] If the check before delivery finds a result that differs from the request or shows defects typical of diffusion models, I regenerate with the same prompt and only a new seed. This is the maximum count per image.
>    a) 0 (default): deliver the generated result as it is
>    b) 1
>    c) 3
>    d) Custom: enter a whole-number count (example: 3-d 5)
>    e) Unlimited (not recommended): keep generating until the adoption criteria are met, with a one-line progress update every 3 rounds

List the conditional items after these. The numbers in the example below continue from the three items above. If earlier items are skipped, start numbering from 1 again. Example:

> 4. [Composition] The intended use is not set, so I am asking about the composition. If you tell me the intended use, I will decide based on it.
>    a) Icon: one subject in the center on a plain background. Suits body illustrations and slide illustrations
>    b) Scene: a scene built from 2-3 elements. Suits background images, banners, and covers
> 5. [Size] Slide covers usually use a 16:9 ratio. The generation size is 512x512, and a larger size can add blur from enlargement.
>    a) Generation size as is (default): delivered at 512x512
>    b) 1920x1080 (16:9): cropped to the ratio, then enlarged
>    c) Custom: enter width x height (example: 5-c 1600x900)
> 6. [Style] No style was specified, so I am asking.
>    a) Digital painting (default): works for most uses
>    b) Photographic
>    c) Watercolor
>    d) Flat vector: suits the Flat model. Shapes collapse with the Standard model
>    e) Custom: describe the style you want
> 7. [Substitution check] Diffusion models cannot draw "growth" directly, so I will draw it as an object.
>    a) A pot with a sprouting seedling
>    b) A person seen from behind, climbing stairs
>    c) Custom: describe the object or scene to draw

- In a runtime environment where the precise preset does not run, leave out the Precise choice and reletter the remaining choices from a) in order.
- If the precise preset was left out, add "The Precise model cannot run on this operating system, so it is not among the choices" to the first line of the questions.

## Time estimates

After the first image, report the estimated time for the remaining images from the `seconds` value in generate.py's output.

- The first run adds model download and loading time. Download sizes are listed in the preset table.
- Example: "The first image took 38 seconds. The remaining 2 images should take about 1 minute 20 seconds."
- If one call generated all images, state the model loading time (the `loaded in` line in stderr) and the measured time per image (`seconds` in the stdout JSON) at delivery.
- The precise preset can take from several minutes to tens of minutes per image, so run generation in the background and follow progress in the log. If the agent's runtime environment can be reset between conversation turns, finish running and waiting within the same turn.

## Prompt

- Write prompts in English. Korean and other non-English prompts are interpreted as a list of nouns, and style and place instructions are barely reflected.
- Place the subject and style keywords first. Do not lengthen the prompt with lists of modifiers.
- Name the style by its technique. Keywords such as `watercolor illustration`, `flat vector illustration`, `digital painting`, and `photorealistic` are reflected better than abstract phrases such as `minimal editorial style`.
- Name the color family, for example `muted blue and beige palette`.
- The model may not recognize proper nouns, technical terms, or uncommon words, because a diffusion model links only the words that appeared often in its training image captions to shapes. If the exact appearance is not essential to the request, replace the word with a similar common object. If its particular appearance is essential, describe it with 2-3 traits of shape, material, and color. Examples: a little-known car model name becomes `a small white electric car`, and the name of a piece of armor from a game becomes `golden plate armor`.
- Do not request text inside the image.
- Do not use single quotes ('). They conflict with command-line quoting.
- The Standard, Light, and Flat presets belong to the SD 1.5 family. They respond well to short keyword-style English and reflect long natural sentences poorly. Their text window is 77 tokens, and anything beyond it is ignored without an error. If generate.py prints a warning that starts with `WARNING: prompt has` together with the ignored text, shorten the prompt and run again.
- Precise accepts natural sentences as they are and has no 77-token limit. It does not use a negative prompt.
- Fix the seed to reproduce a result. Change it for variety.

## Generate

```
# Icon, Standard preset
PY scripts/generate.py --prompt "a brass compass on a desk, watercolor illustration, plain background" --out ./outputs --name compass

# Scene banner 1024x576, a wide format, so the subject stays small and anchor 0.4 puts the horizon slightly below the middle
PY scripts/generate.py --prompt "a small lighthouse on a rocky coast at sunrise, wide shot, muted blue palette, watercolor illustration" --out ./outputs --name banner --width 1024 --height 576 --anchor-y 0.4

# Portrait cover 600x800, keeps the top of an upright subject
PY scripts/generate.py --prompt "an adult man in a gray coat standing in a snowy street, digital painting" --out ./outputs --name cover --width 600 --height 800 --anchor-y 0.0

# Three images of one prompt (target 1, candidate multiplier 3x), the model loads once and the seed increases by 1
PY scripts/generate.py --preset sdxs --prompt "a stone staircase, digital painting, soft light, plain background" --out ./outputs --name stairs --count 3

# Precise preset, background run
setsid nohup PY scripts/generate.py --preset flux2-klein-4b --prompt "an adult woman in a black coat standing on a city street at night, photorealistic" --out ./outputs --name street > ./outputs/street.log 2>&1 < /dev/null &
```

- Generation always uses the preset's fixed size. Generating at another size stretches or squashes the subject along the long side.
- When `--width` and `--height` are given together, the result is cropped to that ratio and then resized to that size. Enlarging adds only pixels and no detail, so when delivering at a size larger than the generation size, also mention at delivery that blur may appear.
- `--anchor-x` and `--anchor-y` set the crop anchor: 0.0 is left and top, 0.5 is the center, and 1.0 is right and bottom. Choose the anchor by the target ratio. In tall or near-square formats, keep the top of an upright subject such as a person, a tower, or a lighthouse with `--anchor-y 0.0`. In formats at least twice as wide as they are tall, half or more of the height is cut away, so an upright subject cannot fit whole. In that case, add an expression that keeps the subject small, such as `wide shot` or `in the distance`, to the prompt and start from `--anchor-y 0.4`. The model often places the horizon near the middle of the frame, so at this value the horizon lands slightly below the middle of the cropped frame. The actual horizon position is unknown before generation, so in settings where results are opened, adjust after viewing the result.
- Open a cropped result only when candidate selection or regeneration is on. If the subject was cut off, run again with the same seed and only a different anchor, writing to the same file with `--overwrite`. The model output stays the same and only the crop position changes, so count this separately from regenerations.
- Without a size, the image is saved at the preset's generation size.
- Generate several images with `--count`. Calling the script repeatedly adds model loading time to each call. If each target image has a different prompt, run once per prompt and set `--count` to the candidate multiplier.
- If a file exists at the same path, the new file is saved with a number appended. Use `--overwrite` only when overwriting is intended.
- stdout prints one JSON line per image with the path, prompt, seed, preset, size, and seconds taken. Progress messages and warnings go to stderr. The warning that needs action is the 77-token overflow warning that starts with `WARNING: prompt has`.
- If the script exits with code 7 (automatic check failed), raise the seed by 1 and run again. No result image exists in this case, so count it separately from regenerations.
- For a background run of the precise preset, confirm completion from the progress display in the log (`1/4` to `4/4`) and the JSON on the last line. Do not run it at the same time as another generation process. Running them together can end in termination for lack of memory.

## Adoption criteria

Candidate selection and regeneration compare images by the criteria below. Open images only when at least one of the two procedures is on. The criteria are in priority order from the top. If no image meets every criterion, pick the image that meets more of the upper criteria.

1. The specified subject or scene elements are recognizable in the frame at a glance.
2. The requested style and color family are reflected.
3. No typical diffusion model defects are visible (wrong numbers of fingers or limbs, smeared or missing eyes, nose, or mouth, broken or tangled structures, duplicates of the same subject, unintended text-like shapes, and so on).
4. No unrequested person or object occupies the center of the frame.

- Treat a criterion with an unclear judgment as not met.
- Record the comparison in one line per image. Example: `stairs_02: 1 met, 2 met, 3 not met (the stair railing breaks off midway), 4 met`

## Candidate selection

If the candidate multiplier is 2 or more, compare all generated candidates by the adoption criteria and adopt the target number of images.

- Deliver the adopted images as the delivery section describes. Leave the spares in the folder where they were generated, and report their paths and seeds.
- State the reason for adoption in one line with the criterion numbers. Example: "I adopted stairs_01. It is the only candidate that meets all of criteria 1-4. stairs_02 has a broken railing, and stairs_03 has two overlapping staircases."
- If no candidate meets criterion 1 (subject recognition) and the regeneration limit is 0, deliver the best of them and report what was not met.

## Regeneration

If the regeneration limit is 1 or more, check by the adoption criteria before delivery. If the target image meets every criterion, do not regenerate. Otherwise, generate again with the same prompt and the same preset, changing only the seed.

- One regeneration is one new batch the size of the candidate multiplier. A multiplier of 1 generates 1 new image, and a multiplier of 3 generates 3.
- Start new seeds from the value after the last seed used, so that results already seen do not come back.
- If the user changes the request, treat it as a new request and count regenerations from the start.
- After each regeneration, compare all results so far and keep the best one. If a regenerated result is worse than the earlier one, keep the earlier one.
- If the limit is reached and no result meets every criterion, deliver the best result and report the unmet criteria in one line. The user decides whether to regenerate further.
- With unlimited, keep generating until every criterion is met. Every 3 rounds, report progress in one line (attempts, total time, criteria still unmet) and continue. If the user asks to stop, deliver the best result at that point.

## Delivery

- Name files in lowercase English with underscores that describe the content, for example `lighthouse_watercolor.png`.
- If the environment has a way to present files, use it. Otherwise give the absolute path.
- Record the reproduction details: prompt, seed, preset, and size.
- If the prompt replaced or described a word the model may not recognize, report the original word with the expression used.
- If a message request was drawn through substitution, report the substituted object.
- If the image was cropped to a requested size, report the crop direction and the anchor.
- If the candidate multiplier or regeneration was used, report the reason for adoption, the spare paths, and the regeneration count.
- For JPEG, generate with `--format jpg` or convert the PNG.
- For a result delivered directly, add one line: "This is the model's output, delivered as is without review."

## Resources and cache

- Check free disk space right before downloading. If it is smaller than the download size in the preset table, say so and offer smaller presets as choices.
- Run generation processes one at a time. Running two at once can end in termination for lack of memory.
- If a process is terminated for lack of memory, clean up leftover processes and retry once. If memory is still insufficient, offer the lighter presets that can run.
- The skill deletes only files inside its cache folder. It does not modify files outside it or the model caches of other programs.
- Models are downloaded to a dedicated Hugging Face cache (`hf`) inside the cache folder. To delete the model of another preset, delete its `models--<owner>--<name>` folder under `hf/hub`. Get the user's confirmation before deleting.
- When the skill is no longer used, deleting the whole cache folder removes every file the skill installed. Delete it only after the user confirms.
- In environments that wipe files when the session ends, set up the virtual environment and models again in the next session.

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Exit code 2 | Missing argument or value out of range | Correct the argument as the message indicates |
| Exit code 3 | Model or engine download failed | Check the network and run again. If it fails repeatedly, explain the reason and stop |
| Exit code 4 | Missing dependency | Return to setup |
| Exit code 5 | Saving the result file failed (no write permission, insufficient disk space) | Check write permission and free disk space at the save path, then run again |
| Exit code 6 | Insufficient memory or disk | Clean up as the resources and cache section describes, or offer a lighter preset |
| Exit code 7 | Output check failed | Raise the seed by 1 and run again |
| Exit code 8 | Engine file hash mismatch, the damaged file is deleted automatically | Run again to download a fresh copy. If it fails repeatedly, leave the precise preset out of the choices |
| Exit code 9 | The operating system cannot run the precise preset | Offer other presets |
| Style ignored | Non-English prompt or abstract style words | Rewrite in English and place a technique name first |
| Text, counts, or states ignored | A limit of diffusion models | Remove those instructions and suggest adding the content in an editing tool |
| The object the user specified is missing | A named subject was classified as a message request | Reclassify it as a named subject and regenerate with that object |
| The object the user specified appears as something else | The model does not recognize the name (proper noun, technical term, rare word) | Replace it with a similar common object or describe its components, as the prompt section specifies |
| Blurry result | Enlarged beyond the generation size | Deliver at the generation size without enlarging |
