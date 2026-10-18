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
| Model choice | A model choice condition applies | The user named a model, or said speed or quality comes first |

- If even one person appears in the frame, treat the request as one with a person, whatever the size, share of the frame, or style. Small, distant people have the worst face defects, so a small share is no reason to skip. If unsure, treat it as a request with a person.
- A precise object is one recognized by how its parts connect: a bicycle, glasses, a chair, a ladder, a keyboard.
- Skip only the items the user already answered. Ask items that have a recommended option too.
- If the user delegates ("you decide", "use the defaults"), show the recommended combination in one line and get a confirmation. Example: "Shall I go with 1-b, 2-b, 3-a, 4-a, 5-a?" For non-photographic styles the recommendation turns face restoration off. Example: "Shall I go with 1-b, 2-b, 3-a, 4-c, 5-a?"
- Ask about final upscaling and edge trimming even when only objects appear.

Question format:

- Number only the applicable items from 1 in order, and write choices as a), b), c). Model choice is always the last number.
- Write a numbered list in plain conversation text. Do not use code blocks or tables.
- Put the answer format and an example answer on the first line.
- For photographic or watercolor requests, add a one-line warning to the final upscaling item. Example: "Upscaling a photo or watercolor style wipes out skin texture and paper grain."
- For non-photographic styles such as flat vector, line art, or cel shading, mark "off" as recommended for face restoration scope and add a one-line reason. Example: "In this style only the restored face turns photographic and clashes with the drawing." Face restoration tools were trained on real photographs of faces.

Example for a request with a person:

> Before I generate, please answer the items below with the item number and letter. (Example: 1-b, 2-c, 3-a, 4-b, 5-a)
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

If a model choice condition applies, continue with the last number. Example:

> 6. [Model choice] A person is the main subject, so the rate of shape defects depends on the model. Times are estimates for this runtime environment.
>    a) Standard (DreamShaper 8 LCM): about 40 seconds per image, 512px, frequent hand and clothing defects
>    b) Precise (FLUX.2 klein 4B): about 15 minutes per image, 384x512, the most accurate shapes. Downloads about 5.2GB on first run

The times in the example only show the format. Use probe.py's estimates in real questions.

### Recording answers

After the user answers, write preflight.json to the output folder with preflight.py. The generation scripts stop with exit code 2 when this file is missing, and preflight.py stops with exit code 2 and lists missing items when a required answer is absent. Never record values you filled in without asking.

```
# A person appears, answer "1-b, 2-c, 3-a, 4-b, 5-a"
PY scripts/preflight.py --out ./outputs --subject person --enhance general --trim free --postfix auto --face-scope always --finger-inpaint off --user-reply "1-b, 2-c, 3-a, 4-b, 5-a"

# Objects only, with a model choice, answer "1-b, 2-b, 3-b"
PY scripts/preflight.py --out ./outputs --subject other --enhance general --trim same --preset sdxs --user-reply "1-b, 2-b, 3-b"
```

- `--subject` is `person` when a person appears, `precise-object` when a precise object appears without a person, and `other` otherwise.
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

## Defect handling

If you find a defect, follow the order in references/defects.md. In short:

1. Trim-first check: if the defect touches an edge and nothing else calls for a new image, trim the edge before regenerating whenever the trim answer is same ratio only, free ratio too, or free ratio automatic.
2. General defects: fix style, color, count, background, and framing problems with prompt edits and seed changes.
3. Fragile subjects (people, animals, precise objects, background crowds): go through stage 1 seed change, stage 2 prompt workaround, stage 3 post-processing, stage 4 composition workaround.
4. If the regeneration limit is reached, show the best result with the defect marked and ask how to proceed.

Choosing, tuning, installing, and cleaning up the post-processing tools (face restoration, region redrawing, finger redrawing) is covered in references/postprocess.md.

## Final upscaling

Final upscaling enlarges 4x with super-resolution and then scales down to the target size. Generation is 512px or smaller, so trimming, non-square formats, and target sizes all need enlargement. Plain enlargement blurs, so this step replaces every enlargement.

| Choice | Fits | Cost |
|---|---|---|
| None | Requests where texture matters most | The original blur remains |
| general | Most styles, including people | Wipes out skin texture and paper grain in photographic and watercolor styles |
| flat | Flat vector backgrounds | Waxy skin, exaggerated nostril edges, and clumped hair on people |

- Apply it once, to the adopted image, after all defect fixes and trimming. Applying it right after generation means enlarging again after a trim or running it twice, and the waxy look builds up. Face restoration and region redrawing are tuned for the pre-upscaling size too. Discarded attempts never get it, so the extra time covers one adopted image.
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

## Delivery

- Name files in lowercase English with underscores that describe the content, for example `lighthouse_flat_vector.png`.
- If the environment has a way to present files, use it. Otherwise give the absolute path.
- Keep the reproduction details: prompt, seed, preset, size, and the final upscaling choice.
- For trimmed results, report the trim, the body part the cut line crosses, and the cut ratio (for free ratio, the adopted ratio and the remaining area).
- For JPEG, generate with `--format jpg` or convert the PNG.

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
