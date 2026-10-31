---
name: image-gen
description: "Generates images with local models on the CPU of the runtime environment, for hobby, daily, or work use. Two compositions: icons with one centered subject, and mood scenes of two or three elements. Turns abstract messages into drawable objects or scenes. For charts or diagrams that need text, draws a substitute once the user agrees. Fixes defects with edge trimming, face restoration, region redrawing, and final upscaling. Default model: DreamShaper 8 LCM. Use this skill whenever the user asks to make or draw an image, illustration, background, banner, cover, divider, slide background, landscape, portrait, or a picture for a report ('image generation', 'generate an illustration'), and to fix faces, hands, or edges in images it made. Details: references/composition.md (requests, substitution, scenes), references/models.md (presets, time estimates, cache), references/defects.md (defects, trimming), references/postprocess.md (face restoration, region redrawing), references/components.md (external sources)."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE.md
---

# Image Generation with Local Models

> This English edition is a translation of the Korean original. Its behavior may differ from what the original intends.

This skill generates images with local models. Model files are downloaded to the environment that runs the skill (the runtime environment). Generation runs on the runtime environment's CPU. The network is used only to download packages and model files. Prompts are never sent to an outside image generation service. The output is a PNG or JPEG file.

Diffusion models cannot draw text, exact connector lines, numbers, or exact counts. For requests that need them, draw the meaning as an object or a scene instead. The user adds text on top of the finished image in an editing tool.

## Workflow

1. Setup: create the skill's own virtual environment and install dependencies.
2. Environment check: run probe.py to see what can run and how long it will take.
3. Request type and composition: decide what to draw and how to frame it.
4. Preset: choose the model.
5. Pre-generation questions: ask about correction policies once and record the answers in preflight.json.
6. Prompt: write an English prompt.
7. Generate: run generate.py or generate_klein.py.
8. Check and fix: open the output and fix defects.
9. Final upscaling: if chosen, apply it once to the adopted image.
10. Deliver: hand over the file and the reproduction details.

## Command notation

- `PY` is the Python of the skill's virtual environment: `~/.cache/image-gen/venv/bin/python` on Linux and macOS, `%USERPROFILE%\.cache\image-gen\venv\Scripts\python.exe` on Windows.
- Replace `scripts/` with the path of the scripts folder inside this skill's folder.
- Run commands from the user's working folder. Save results to the path the user gives. Without one, use the output folder the environment defines, and without that, save to the working folder and tell the user the absolute path.
- The scripts run with the same commands on Linux, macOS, and Windows. Only the precise preset needs Linux x86_64.
- Every file the skill downloads goes to the cache folder `~/.cache/image-gen`. Set the environment variable `IMAGE_GEN_HOME` to move it.
- Features that fetch files from GitHub: the precise preset engine (`leejet/stable-diffusion.cpp`), final upscaling (`xinntao/Real-ESRGAN`) and face restoration (`TencentARC/GFPGAN`, `xinntao/facexlib`). If the execution environment has a tool that attaches a GitHub repository to the session, call it with the matching repository before each feature's first run. Pass the parts before and after `/` as separate owner and repository name values. Follow any access route the tool's reply names. Skip this step when no such tool exists or the call is refused.

## Setup

Install packages into the skill's own virtual environment and nowhere else. Leave packages already in the user's environment untouched, including GPU builds of torch or CUDA packages. The skill environment gets its own CPU build of torch, so the two never interfere.

```
python3 -m venv ~/.cache/image-gen/venv
PY -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
PY -m pip install --no-cache-dir diffusers transformers accelerate safetensors peft huggingface_hub pillow numpy
```

- If `python3` is missing, use `python`. On Windows create the environment at `%USERPROFILE%\.cache\image-gen\venv`.
- Install torchvision together with torch from the same CPU index. With torch alone, the post-processing packages pull in a CUDA build of torchvision and fail with `operator torchvision::nms does not exist`.
- `--no-cache-dir` keeps downloaded installers out of the shared pip cache, so nothing is left to clean afterwards.
- If a virtual environment cannot be created (for example the venv module is missing), ask the user whether to install into the current Python environment. Install there only with permission. If pip reports externally-managed-environment, add `--break-system-packages`.
- Without permission to install with pip, generation cannot work. Explain why and stop.
- Without a way to run Python, generation cannot work either. Explain why, and hand over the English prompt and the preset settings so the user can generate somewhere Python runs.
- Install post-processing dependencies only when the user chooses post-processing, following the install section of references/postprocess.md.

## Environment check

```
PY scripts/probe.py --estimate
```

probe.py prints one JSON object. Decide the next step from these values.

| Value | Meaning | Action |
|---|---|---|
| `hub_reachable` | The model hub can be reached | If false and the model is not cached, explain why and stop |
| `dependencies` | Installed packages | If torch, diffusers, or transformers is false, go back to setup |
| `free_disk_gb` | Free disk at the cache folder | Compare with the download sizes in the preset table |
| `memory.total_gb` | Total memory | If too small, generate.py stops before running with exit code 6 |
| `cpu.native_bf16` | CPU support for bfloat16 instructions | Used to choose the precision (references/models.md) |
| `precise_tier_supported` | Whether the precise preset can run | If false, leave the precise preset out of the choices |
| `estimate.seconds_per_image` | Estimated seconds per image by preset | Use it to tell the user how long it will take |

### Time estimates

Base time estimates on a measurement of the runtime environment's CPU. `--estimate` measures matrix-multiply speed for a few seconds and divides each preset's workload by that speed. Memory speed, other running programs, and heat make the real time differ, so call it an estimate every time you report it.

- Example: "In this runtime environment, about 40 seconds per image, about 2 minutes for 3 images. This is an estimate, and I will update it after the first image."
- The first run adds download time. Download sizes are in the preset table.
- After the first image, use the `seconds` value from generate.py's output to update the estimate for the rest.
- The method and the workload values are in the time estimate section of references/models.md.

## Request types

Before generating, sort the request into one of three types. The test is whether the user named a concrete thing to draw.

| Type | Test | Handling |
|---|---|---|
| Named subject | The user names something with a visible outline: an object, person, animal, or place | Draw it as named |
| Message request | The user gives only an abstract concept or a message | Replace it once with an object or scene that can be drawn |
| Diagram request | It needs text labels, connectors, exact counts, or numbers (flowchart, concept map, architecture diagram, chart, KPI graphic) | Explain the limits and a substitute, draw after the user agrees |

- If the user named a symbolic object, they already made the choice. Keep it.
- If the user gives both an object and a message, draw the object and carry the message through style and color.
- Substitution rules, example tables, and the consent wording are in references/composition.md.

## Composition

There are two compositions: icon and scene. Follow the user if they name one. Otherwise decide from where the image will go. If that is unknown too, make an icon.

| Composition | Look | Main use | Prompt order |
|---|---|---|---|
| Icon | Subject in the center on a plain background | Body illustrations, slide illustrations, a picture built around one object | subject, style, color, `plain background` |
| Scene | Two or three common elements plus one time of day and one color family | Background images, banners, covers, section dividers, slide backgrounds, landscape pictures | elements, time of day, color, style |

- For icons, adopt a result where the subject is recognizable at a glance.
- For scenes, judge the mood of the whole scene over individual objects.
- Choosing elements, time of day, and color for scenes follows the scene building section of references/composition.md.

## Presets

A preset is a model plus fixed settings. Change style through the prompt and change the model through the preset.

| Preset | Role | Styles it handles well | Generation size | First download |
|---|---|---|---|---|
| `dreamshaper-8-lcm` | Standard, default | Photographic, illustration, painting, watercolor | 512x512 | about 4.3GB |
| `sdxs` | Light, fastest | General styles, simpler detail | 512x512 | about 2.1GB |
| `tiny-sd` | Flat | Flat vector with solid fills, watercolor with paint bleed | 384x384 | about 1.1GB |
| `flux2-klein-4b` | Precise, slowest | Most accurate instruction following and anatomy | 384x512 | about 5.2GB |

- With no style or quality requirement, use Standard.
- Standard breaks shapes apart on flat vector keywords. Use Flat or Light for flat vector requests.
- Flat often cuts off heads or adds picture frames when a person is the main subject. For a person as the main subject, use Standard or Precise.
- Light tends to look like an illustration even when asked for a photographic style.

### Model choice question

Add a model choice to the pre-generation questions when any condition below applies. If none applies, go ahead with Standard without asking. If the user already named a model or said speed or quality comes first, follow that without asking.

| Condition | Choices |
|---|---|
| 10 or more images in one request | Standard, Light |
| A person is the main subject (including full body or visible hands) | Standard, Precise |
| Flat vector or paint-bleed texture requested | Flat, Light |
| The environment check shows too few resources | Only the presets that can run |

- For each choice, give the estimated time per image (marked as an estimate), the first download size, and how quality and style differ.
- Drafts, mockups, and repeated checks are the normal way people use image generation. They are no reason to ask about the model or to pick Light.
- The 10-image threshold is where Standard's total time grows long enough for the gap to Light to matter. For 1 to 9 images the gap is small.

### Model lock

- Change the model used for the first image only with the user's permission within the same conversation. A model change brings gigabytes of downloads, longer time per image, and a different style and look, all outside what the user expected to pay and receive.
- Fix defects within the chosen model: seed changes, edge trimming, prompt workarounds, post-processing, and composition workarounds. Never switch models as an automatic fix.
- If a different model would help, offer it as one option when the regeneration limit is reached, with its download size, estimated time per image, and what would change. If the user picks it, rerun preflight.py with only `--preset` changed, then switch.
- If a preset cannot run, state the cause in one line (not enough disk, the process was killed for lack of memory, download error) and offer the presets that can run. If deleting caches of non-default presets frees enough disk, retry without asking. If no preset can run, explain why and stop.

## Pre-generation questions

Before the first image, ask every applicable item from the table below in one message. Installation size, changes to a person's look, and texture loss are matters of taste, so the user chooses. Asking after a defect appears interrupts users who want the work to run on its own, so ask before generating.

| Item | Ask when | Skip when |
|---|---|---|
| Final upscaling | Every request | Never |
| Edge trim | Every request | Never |
| Defect post-processing | A person or a precise object appears | Never |
| Face restoration scope | A person appears | Never |
| Finger redrawing | A person appears | Defect post-processing is workarounds only |
| Candidate generation | Every request | Never |
| Candidate pick | A display path exists | Candidate generation is 1x |
| Spare candidate finishing | Every request | Candidate generation is 1x, or final upscaling is none while face restoration scope is other than always |
| Model choice | A model choice condition applies | The user named a model, or said speed or quality comes first |

- If even one person appears in the frame, treat the request as one with a person, whatever the size, share of the frame, or style. Small, distant people have the worst face defects, so a small share is no reason to skip. If unsure, treat it as a request with a person.
- A precise object is one recognized by how its parts connect: a bicycle, glasses, a chair, a ladder, a keyboard.
- Skip only the items the user already answered. Ask items that have a recommended option too.
- If the user delegates ("you decide", "use the defaults"), show the recommended combination in one line and get a confirmation. Example: "Shall I go with 1-b, 2-b, 3-a, 4-a, 5-a, 6-a?" For non-photographic styles the recommendation turns face restoration off. Example: "Shall I go with 1-b, 2-b, 3-a, 4-c, 5-a, 6-a?" The recommended candidate generation is 1x.
- Ask about final upscaling, edge trimming, and candidate generation even when only objects appear.
- Before asking, make the display path judgment from the delivery section. Without a display path, reduce the items and choices as that section's table says.
- Candidate generation makes more candidates than the target count at once and picks from them. It runs defect handling step 1 (regenerate with the same prompt and a new seed) ahead of time, at generation. The default 1x makes only the target count.
- For fixed multiplier choices, write the total count (target count times multiplier) and the estimated time from probe.py, and say it is an estimate. For the automatic choice, write the range of total counts and times from 1x up to the cap of the automatic judgment.
- Take a custom answer as a whole-number multiplier. When each target image has its own prompt, a total count alone does not decide how many images each prompt gets.
- In the choices of spare candidate finishing, name only the batch processes the user can pick in this question. For objects only, name final upscaling alone.
- Judge the 10-image condition of the model choice question by the target count. The multiplier comes in the same question, so whether to ask the model question cannot follow the multiplier answer.
- If automatic resolves to 1x, the answers for candidate pick and spare candidate finishing go unused.

Question format:

- Number only the applicable items from 1 in order, and write choices as a), b), c). Model choice is always the last number.
- For a conditional item (finger redrawing, candidate pick, spare candidate finishing), state its condition in the first sentence with the actual item numbers.
- Write a numbered list in plain conversation text. Do not use code blocks or tables.
- Put the answer format and an example answer on the first line.
- For photographic or watercolor requests, add a one-line warning to the final upscaling item. Example: "Upscaling a photo or watercolor style wipes out skin texture and paper grain."
- For non-photographic styles such as flat vector, line art, or cel shading, mark "off" as recommended for face restoration scope and add a one-line reason. Example: "In this style only the restored face turns photographic and clashes with the drawing." Face restoration tools were trained on real photographs of faces.

Example for a request with a person:

> Before I generate, please answer the items below with the item number and letter. (Example: 1-b, 2-c, 3-a, 4-b, 5-a, 6-d, 7-b, 8-c)
> 1. [Final upscaling] Applied once at the end, after defect fixes and trimming.
>    a) None: trimming and enlargement to the target size leave some blur
>    b) general: works for most styles
>    c) flat: for flat vector art only
> 2. [Edge trim] When a defect such as a finger touches the frame edge, I cut a little off that edge before regenerating. The cut defect leaves the frame for good, so this is the surest fix in that case.
>    a) Off: fix only by regenerating and workarounds
>    b) Same ratio only: cut as much as needed while keeping the aspect ratio, then restore the original size. Applied without asking and reported on delivery
>    c) Free ratio too: when b cannot work, show preview candidates with other ratios (for example a wider frame) and apply the ratio you pick
>    d) Free ratio, automatic: when b cannot work, I pick the candidate closest to the original framing, apply it, and tell you. The aspect ratio may change
> 3. [Defect post-processing] Faces, clothing, and accessories of people can come out misshapen.
>    a) Automatic post-processing: defects left after seed changes and prompt workarounds get fixed without asking, with face restoration and region redrawing (about 1.2GB to install, about 2.3GB more for region redrawing)
>    b) Workarounds only: no installation, just seed changes, prompt workarounds, and composition workarounds
>    c) Ask each time: I ask whenever post-processing is needed
> 4. [Face restoration scope]
>    a) Only on defects: apply per item 3 when a face defect shows
>    b) Always: apply face restoration to every image with a person, defect or not. Eyes and teeth get sharper (applies even if item 3 is b, about 1.2GB to install)
>    c) Off: do not install or use face restoration. Face defects get seed changes and workarounds, and item 3's clothing and accessory redrawing stays as chosen
> 5. [Finger redrawing] Only if item 3 is a or c. It seldom fixes fingers, so seed changes, edge trimming, and prompt workarounds always come first.
>    a) Off (recommended): remaining finger defects get a composition that keeps hands out of the frame
>    b) On: one attempt on remaining defects, with a before and after comparison. Used only on hands shown on their own. Hand size and pose may change
> 6. [Candidate generation] I make more candidates than the target count at once and pick from them. You wait less for regeneration after a defect. Counts and times are for a target of 1 image and are estimates for this runtime environment.
>    a) 1x: 1 image, about 40 seconds
>    b) 2x: 2 images, about 1 minute 20 seconds
>    c) 3x: 3 images, about 2 minutes
>    d) Automatic: 1-3 images, about 40 seconds to 2 minutes. I raise it only for defect-prone requests such as people, hands, or crowds, and tell you the multiplier before generating
>    e) Custom: write a whole-number multiplier (example: 6-e 4)
> 7. [Candidate pick] Only if item 6 is not a.
>    a) Agent pick: I pick the target count, starting from candidates without defects, and carry on to the end
>    b) User pick: right after generation I show one contact sheet with numbers, and finish the candidates you pick by number
> 8. [Spare candidate finishing] Only if item 6 is not a, and item 1 is not a or item 4 is b. Decides whether the candidates you do not pick (spares) get final upscaling and always-on face restoration. Defect repairs go to adopted images only.
>    a) Adopted only: spares come as generated. You can have any spare finished later
>    b) All candidates: spares come finished too. Post-processing time grows with the number of candidates
>    c) Automatic: I choose a or b for the task and tell you before generating

If a model choice condition applies, continue with the last number. Example:

> 9. [Model choice] A person is the main subject, so the rate of shape defects depends on the model. Times are estimates for this runtime environment.
>    a) Standard (DreamShaper 8 LCM): about 40 seconds per image, 512px, frequent hand and clothing defects
>    b) Precise (FLUX.2 klein 4B): about 15 minutes per image, 384x512, the most accurate shapes. Downloads about 5.2GB on first run

The times in the example only show the format. Use probe.py's estimates in real questions.

### Automatic candidate multiplier

When the candidate generation answer is automatic, decide the multiplier after the answers arrive and before recording them with preflight.py. The baseline is 1x. Raise it only on the grounds below.

- The main subject is prone to shape defects (a person, an animal, a precise object).
- The framing shows a person's hands or full body.
- The scene has several people or a background crowd.

Keep 1x in the cases below.

- The precise preset is in use. It takes the longest per image and draws shapes most accurately.
- An object icon or a landscape scene with no subject prone to shape defects.

Decide the multiplier within these limits.

- With one ground, consider 2x. With overlapping grounds, consider up to 3x.
- The cap is 3x.
- Keep the total count (target count times multiplier) under 10. The model choice question is skipped by the target count, so the automatic multiplier must not push the total time past the model choice threshold. The cap is 2x for 4 target images and 1x for 5 or more.
- Before generation starts, report the multiplier, a one-line reason, the total count, and the estimated time. Then go on without waiting for a confirmation, the same way as the free-ratio automatic trim.

### Automatic spare candidate finishing

When the spare candidate finishing answer is automatic, decide it after the multiplier is set and before recording with preflight.py. The baseline is a) adopted only. Adopted only keeps the generated originals, so spares can be finished one by one later and the choice can be undone. All candidates spends post-processing time up front and cannot be undone.

Choose b) all candidates only in the cases below.

- Candidate pick is user pick and face restoration scope is always. Faces differ a lot before and after restoration, so the contact sheet must show restored images for the user to pick by the final look.
- The request shows an intent to receive every alternative.

- When only final upscaling applies, keep a. Final upscaling mostly changes sharpness and size, so it hardly affects comparing framing and expression.
- Before generation starts, report the choice and a one-line reason. Then go on without waiting for a confirmation.

### Recording answers

After the user answers, write preflight.json to the output folder with preflight.py. The generation scripts stop with exit code 2 when this file is missing, and preflight.py stops with exit code 2 and lists missing items when a required answer is absent. Never record values you filled in without asking.

```
# A person appears, answer "1-b, 2-c, 3-a, 4-b, 5-a, 6-d, 7-b, 8-c", automatic judgment chose 3x and all candidates
PY scripts/preflight.py --out ./outputs --subject person --display available --enhance general --trim free --postfix auto --face-scope always --finger-inpaint off --candidates auto --candidates-resolved 3 --candidates-reason "full body framing with hands visible" --candidate-pick user --spare-finish auto --spare-finish-resolved all --spare-finish-reason "user pick with always-on face restoration" --user-reply "1-b, 2-c, 3-a, 4-b, 5-a, 6-d, 7-b, 8-c"

# Objects only, with a model choice, answer "1-b, 2-b, 3-a, 6-b"
PY scripts/preflight.py --out ./outputs --subject other --display available --enhance general --trim same --candidates 1 --preset sdxs --user-reply "1-b, 2-b, 3-a, 6-b"
```

- `--subject` is `person` when a person appears, `precise-object` when a precise object appears without a person, and `other` otherwise.
- `--display` is the result of the display path judgment in the delivery section: `available` with a display path, `none` without one. With `none`, `--trim free`, `--finger-inpaint on`, and `--candidate-pick user` are refused with exit code 2.
- `--candidates` is a whole-number multiplier or `auto`. With `auto`, put the decided multiplier (1-3) in `--candidates-resolved` and a one-line reason in `--candidates-reason`.
- `--candidate-pick` is `auto` for agent pick and `user` for user pick.
- `--spare-finish` is `adopted` for adopted only, `all` for all candidates, and `auto` for automatic. With `auto`, put the decided value in `--spare-finish-resolved` and a one-line reason in `--spare-finish-reason`.
- Candidate pick and spare candidate finishing are needed only when the multiplier in force is 2 or more. Unused items are recorded as null. Later steps use the values recorded in `candidates_resolved` and `spare_finish_resolved`.
- `--user-reply` holds the user's answer word for word.
- Later images in the same conversation reuse the record in the same output folder. If the user changes a choice or whether a person appears, rerun preflight.py.
- If the style changes into photographic or watercolor, ask only the final upscaling item again. If the style moves between photographic and non-photographic, ask only the face restoration scope item again.

## Prompt

- Write prompts in English. Korean and other non-English prompts get read as a list of nouns, and style and place instructions hardly register.
- Put the subject and the style keywords first. Do not pad the prompt with strings of modifiers.
- Name the style by its technique. Keywords such as `watercolor illustration`, `flat vector illustration`, `digital painting`, and `photorealistic` register better than abstract phrases such as `minimal editorial style`.
- Name the color family, for example `muted blue and beige palette`.
- Never ask for text inside the image.
- Leave out single quotes ('). They clash with command-line quoting.
- Standard, Light, and Flat belong to the SD 1.5 family. They respond to short keyword-style English and lose track of long natural sentences. Their text window is 77 tokens, and anything beyond it is ignored without an error. The 75 tokens left after the start and end markers are about 50 English words. If generate.py prints a warning with the ignored text, shorten the prompt and run again.
- Precise takes natural sentences as they are and has no 77-token limit. It uses no negative prompt.
- Fix the seed to reproduce a result. Change it for variety.
- Leave workaround instructions (hats, sunglasses, gloves) out of the first prompt. Use them only after a defect shows. Accessories the user asked for from the start belong to the original intent, so include them.

## Generate

```
# Icon, default preset
PY scripts/generate.py --prompt "a brass compass on a desk, watercolor illustration, plain background" --out ./outputs --name compass

# Scene banner 1024x576, keep the top of an upright subject
PY scripts/generate.py --prompt "a lighthouse on a rocky coast at sunrise, muted blue palette, watercolor illustration" --out ./outputs --name banner --width 1024 --height 576 --anchor-y 0.0

# Four images of one prompt, the model loads once and the seed goes up by 1
PY scripts/generate.py --prompt "a stone staircase, digital painting, soft light, plain background" --out ./outputs --count 4

# Flat preset
PY scripts/generate.py --preset tiny-sd --prompt "flat vector illustration of a single lighthouse, muted blue palette, plain background" --out ./outputs --name lighthouse_flat
```

- Always generate square images. Rectangular generation stretches or squashes the subject along the long side. Other ratios come from cropping after generation.
- `--width` and `--height` go together. `--anchor-x` and `--anchor-y` set the crop anchor: 0.0 is left or top, 0.5 is the center, 1.0 is right or bottom. For upright subjects such as people, towers, and lighthouses, keep the top with `--anchor-y 0.0`. For sky and horizon scenes, place the horizon in the lower third.
- If final upscaling is chosen, outputs are saved at working size with only the target ratio (a 1024x576 target from a 512px square becomes 512x288). finalize.py produces the target size at the end.
- If final upscaling is off, outputs are enlarged to the target size at this step. Enlargement adds pixels and no detail. Flat's 384px outputs are enlarged to 512px.
- Make several images with `--count`. Each extra call of the script adds model loading time.
- An existing file at the same path gets a numbered name instead. Use `--overwrite` only when overwriting is wanted.
- stdout prints one JSON line per image with the path, prompt, seed, preset, precision, size, and seconds.
- Open any result cropped to another ratio and check that the subject is not cut off. If it is, run again with the same seed and only the anchor changed. If no anchor fits the whole subject, add a framing that suits the target ratio (distant placement, upper body) to the prompt and regenerate.
- Run the precise preset with generate_klein.py following the precise preset section of references/models.md.

When the multiplier in force is 2 or more, make target count times multiplier candidates. This set of candidates is the candidate pool.

```
# Same prompt, 2 target images, 2x candidates
PY scripts/generate.py --prompt "a red bicycle leaning against a brick wall, side view, watercolor illustration" --out ./outputs --name bicycle --count 4

# Precise preset, 2x candidates, one image per run with a new seed and file name
PY scripts/generate_klein.py "an elderly man reading a newspaper on a park bench, photorealistic" ./outputs/reader-01.png --seed 42
PY scripts/generate_klein.py "an elderly man reading a newspaper on a park bench, photorealistic" ./outputs/reader-02.png --seed 43
```

- For target images that share a prompt, run once with `--count` set to target count times multiplier. When each target image has its own prompt, give each prompt `--count` equal to the multiplier.
- The precise preset makes one image per run. Run each candidate separately with the seed raised by 1 and a new file name. Start the next run after the previous one finishes.
- Make candidates in the output folder. The generation scripts and finalize.py read preflight.json from the output folder, so saving into a subfolder stops them with exit code 2. Spares move to the `candidates` folder after adoption (candidate adoption in the check section).

## Check

generate.py checks each file right after saving: size over 10KB, magic bytes (JPEG `FFD8FF`, PNG `89504E47`), and pixel size. On exit code 7, regenerate before looking.

Once the machine check passes, open the file and look.

- Did the subject the user named appear as named?
- Did the prompt's style and color come through?
- Can you still read the shape at the size it will be used?
- Does a person nobody asked for take the center of the frame?
- Are there more objects than intended, or the same subject twice?
- Are the facial features, number of limbs, and hands and feet of people and animals right?
- Do clothing and accessories show broken glasses frames, missing straps, or unrequested exposure of genitals or female nipples?
- Does each defect touch or come close to one of the four edges?
- For a substituted diagram request, does the picture carry the original message?
- If the subject looks squashed horizontally or vertically, regenerate as a square.

If final upscaling is chosen, run these checks on the working-size output.

### Candidate adoption

When the multiplier in force is 2 or more, check the whole candidate pool, then adopt the target count.

1. Check every candidate on its original file with the items above. When face restoration scope is always, follow the spare candidate finishing value in force. With all candidates, restore every candidate once and check the restored images. With adopted only, check the originals, then restore only the adopted images and judge them on the restored versions.
2. Build the contact sheet from all candidates. If every candidate got face restoration, use the restored images. Otherwise use the generated originals. Final upscaling comes after adoption, so the sheet does not reflect it.
3. Adopt as the candidate pick answer says.
4. If spare candidate finishing is all candidates and final upscaling was chosen, apply final upscaling once to each spare. The input is the restored image if there is one, the generated original otherwise. finalize.py reads preflight.json from the output folder, so apply it in the output folder before moving.
5. Move the spares' generated originals and finished versions to the `candidates` folder inside the output folder. Adopted images stay in the output folder for defect handling, trimming, and final upscaling.

```
PY scripts/contact_sheet.py ./outputs/bicycle-01.png ./outputs/bicycle-02.png ./outputs/bicycle-03.png ./outputs/bicycle-04.png --out ./outputs/bicycle_sheet.png
PY scripts/contact_sheet.py "./outputs/reader-0?_face.png" --out ./outputs/reader_sheet.png   # restored images, the script expands the wildcard
```

- The contact sheet numbers its inputs from 1 in the given order. stdout prints the number-to-file mapping as JSON.
- The contact sheet is for choosing framing and expression. Judge small defects on the original candidate files.
- With agent pick, adopt the target count in the adoption order below and carry on to the end. Record the adopted candidates, their ranks, and the reasons.
- With user pick, show the contact sheet right after generation and let the user pick by number. Report the defects found in each candidate, one line each. Run defect handling and finishing on the picked candidates.
- If a candidate the user picked has a defect with no means of repair, report the defect and ask whether to pick again from the remaining candidates or go to defect handling stage 2.
- Without a display path, do not ask for user pick and go on with agent pick.

The agent adoption order:

1. Candidates without defects
2. Candidates whose only defects trimming resolves (trim answer other than off). Candidates resolved by same-ratio trimming come before those that need free-ratio trimming.
3. Candidates whose only defects post-processing resolves (defect post-processing answer is automatic or ask each time). Face defects that always-on face restoration resolves fall in this rank whatever the defect post-processing answer.

- Within a rank, pick the candidate closest to the subject, framing, and style of the original request.
- Do not adopt candidates with defects that have no means of repair. General defects that need a new image (style, color, count, and so on) belong here too.
- Fill slots the pool cannot fill with the defect handling procedure. Fragile subjects start at stage 2 without a stage 1 regeneration (references/defects.md).

### Scope in candidate mode

The answers to the existing items apply in candidate mode as below.

| Existing item | Candidate mode behavior |
|---|---|
| Final upscaling | Applied once to the adopted images only, or to every candidate, as the spare candidate finishing value in force says |
| Edge trim | Applied only to defects of adopted candidates. With off, the adoption order has no rank 2 |
| Defect post-processing | Automatic serves as rank 3 of the adoption order. Workarounds only treats candidates that need post-processing as having no means of repair. Ask each time asks only when the higher ranks fall short |
| Face restoration scope | Always follows the spare candidate finishing value in force. Only on defects follows the defect post-processing rules. Off does not apply |
| Finger redrawing | Applied only to adopted candidates |

- Defect repairs (trimming, face restoration on defects, face restoration again at a lower strength, region redrawing, finger redrawing) go to adopted images only, whatever the answers. Each repair needs its own judgment and user confirmation per candidate, so repairing spares too would multiply questions and time by the number of candidates.
- Always-on face restoration runs once per candidate. Running it again at a lower strength is a defect repair, so only adopted images get it.
- If the user wants some spares, move each one's generated original to the output folder and run the same repairs and finishing as for adopted images. Final upscaling is applied only once, so start over from the generated original.

## Defect handling

If you find a defect, follow the order in references/defects.md. In short:

1. Trim-first check: if the defect touches an edge and nothing else calls for a new image, trim the edge before regenerating whenever the trim answer is same ratio only, free ratio too, or free ratio automatic.
2. General defects: fix style, color, count, background, and framing problems with prompt edits and seed changes.
3. Fragile subjects (people, animals, precise objects, background crowds): go through stage 1 seed change, stage 2 prompt workaround, stage 3 post-processing, stage 4 composition workaround.
4. If the regeneration limit is reached, show the best result with the defect marked and ask how to proceed.

When the multiplier in force is 2 or more, swapping within the candidate pool replaces stage 1 for fragile subjects. Once the pool runs out, go to stage 2 without a stage 1 regeneration. For general defects, add the number of pool swaps to the count of seed changes. The detailed rules and the regeneration limits are in references/defects.md.

Choosing, tuning, installing, and cleaning up the post-processing tools (face restoration, region redrawing, finger redrawing) is covered in references/postprocess.md.

## Final upscaling

Final upscaling enlarges 4x with super-resolution and then scales down to the target size. Generation is 512px or smaller, so trimming, non-square formats, and target sizes all need enlargement. Plain enlargement blurs, so this step replaces every enlargement.

| Choice | Fits | Cost |
|---|---|---|
| None | Requests where texture matters most | The original blur remains |
| general | Most styles, including people | Wipes out skin texture and paper grain in photographic and watercolor styles |
| flat | Flat vector backgrounds | Waxy skin, exaggerated nostril edges, and clumped hair on people |

- Apply it once, to the adopted image, after all defect fixes and trimming. Applying it right after generation means enlarging again after a trim or running it twice, and the waxy look builds up. Face restoration and region redrawing are tuned for the pre-upscaling size too. Discarded attempts never get it, so the extra time covers one adopted image.
- In candidate mode, follow the spare candidate finishing value in force. With all candidates, each spare gets it once too, so the extra time grows with the number of candidates. Spares get no defect repairs, so apply it in the output folder right after adoption.
- Texture loss comes from the post-processing itself, so no prompt or seed brings it back.
- Super-resolution does not repair facial features. Face defects go through defect handling.
- On first use it downloads weights of a few MB from GitHub and checks their SHA-256. Nothing else needs installing.
- Keep the target within 4x of the input. Anything beyond becomes plain enlargement.
- It runs as a separate command after generation has exited, so memory is never used twice over.

```
PY scripts/finalize.py ./outputs/banner_trim.png ./outputs/banner_final.png --size 1024x576
```

- Without `--size` the result is 768x768. The mode follows the answer in preflight.json.
- If trimming changed the ratio, pass the `target=WxH` printed by edge_trim.py to `--size` unchanged. Passing the original target crops back to the original ratio and cuts off the parts you kept.
- Open the result and check for a waxy look, exaggerated nostril and lip edges, clumped hair, and lost texture. If you see side effects, show it next to the adopted image enlarged to the same size, and let the user choose.
- Compare side effects on adopted images only. Without a display path, pick the version with fewer side effects yourself and give a one-line reason on delivery.

## Delivery

- Name files in lowercase English with underscores that describe the content, for example `lighthouse_flat_vector.png`.
- If the environment has a way to present files, use it. Otherwise give the absolute path.
- Keep the reproduction details: prompt, seed, preset, size, and the final upscaling choice.
- In candidate mode, present the candidates folder path and the contact sheet along with the adopted images. Add each candidate's seed, the multiplier in force, and the spare candidate finishing choice to the reproduction details. For a multiplier or spare candidate finishing choice decided automatically, include the reason.
- For trimmed results, report the trim, the body part the cut line crosses, and the cut ratio (for free ratio, the adopted ratio and the remaining area).
- For JPEG, generate with `--format jpg` or convert the PNG.

### Display path judgment

Every point that shows images to the user follows this judgment. Make it once, at the pre-generation question stage. Look at the tools you have and where you run, and pick one of the three below.

| Display path | Criterion | `--display` |
|---|---|---|
| File presentation tool | The runtime environment has a tool that shows files on the user's screen | `available` |
| Shared file system | The agent runs on the user's computer, so the user can open an absolute path you give | `available` |
| No display path | As in a remote runtime environment without a presentation tool, the user cannot open an absolute path you give | `none` |

Without a display path, handle each point as below.

| Point that shows images | Without a display path |
|---|---|
| User pick in candidate pick | Do not ask the item. Go on with agent pick |
| Free ratio too in edge trim | Remove the choice |
| On in finger redrawing | Remove the choice, because it needs a before and after comparison |
| Before and after comparison of face restoration in non-photographic styles | Pick the version that suits the style yourself and give a one-line reason on delivery |
| Side effect comparison of final upscaling | Pick the version with fewer side effects yourself and give a one-line reason on delivery |
| Regeneration limit reached | Describe the defect location in words and ask how to proceed |

- After removing a choice, relabel the remaining choices from a) in order. Ask finger redrawing and record the answer even when only off remains.

## Resources and cache

- Check disk and memory again right before each download and each run. The models, face restoration, region redrawing, and final upscaling each download weights, so free space keeps changing within one conversation.
- Run generation, face restoration, region redrawing, and final upscaling as separate processes, one at a time. Confirm the previous process has exited before starting the next. Two at once can run out of memory and get killed.
- If a process is killed for lack of memory, clean up leftover processes and retry once. If memory is still short, offer the lighter presets that can run.
- The skill deletes only files inside its cache folder. It never touches files outside it or the model caches of other programs.
- If disk runs short, delete finished post-processing weights first, then presets other than the default. Keep files you will use again in the same conversation, because downloading them again takes time.
- Record what you deleted and the free space afterwards.
- In environments that wipe files when the session ends, set up the virtual environment and models again in the next session.

```
PY scripts/cache.py list
PY scripts/cache.py delete sdxs
PY scripts/cache.py delete all    # the whole cache except the virtual environment
```

## Failures

| Symptom | Cause | Action |
|---|---|---|
| Exit code 2, no preflight.json | Pre-generation questions were skipped | Ask the items and record them with preflight.py |
| Exit code 2, argument error | Missing argument or value out of range | Fix the argument as the message says. For BOX_TOO_LARGE, split the box |
| Exit code 3 | Weight download failed | Run again. If it keeps failing, turn final upscaling off and tell the user |
| Exit code 4 | Missing dependency | Go back to setup or the post-processing install |
| Exit code 6 | Not enough memory or disk | For disk, delete non-default preset caches with cache.py and retry. For memory, follow the steps in the model lock section |
| Exit code 7 | Output check failed | Regenerate with another seed |
| Exit code 8 | Weight hash mismatch, the damaged file was deleted | Run again to download a fresh copy. If it keeps failing, turn that feature off and tell the user |
| Exit code 9 | The operating system cannot run the precise preset | Offer other presets |
| Style ignored | Non-English prompt or abstract style words | Rewrite in English and lead with a technique name |
| Mushy shapes | Preset settings were changed | Keep the script's steps, guidance, and scheduler |
| Text, counts, or states ignored | A limit of diffusion models | Drop those instructions and add them in an editing tool |
| The object the user named is missing | A named subject was sorted as a message request | Sort it as a named subject and regenerate with that object |
| `KeyError: '__version__'` while installing gfpgan | basicsr's setup.py fails on newer Python (seen on Python 3.13 with basicsr 1.4.2) | Follow the workaround in the install section of references/postprocess.md |
| functional_tensor error when importing gfpgan | basicsr imports a module torchvision removed | Run `PY scripts/patch_basicsr.py` and try again |
