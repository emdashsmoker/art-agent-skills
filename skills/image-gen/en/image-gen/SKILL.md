---
name: image-gen
description: "Generates images with local models on the runtime environment's CPU, for hobby, daily, or work use. Two compositions: icons with one centered subject, and mood scenes of 2-3 elements. Renders abstract messages as drawable objects or scenes. For charts or diagrams that need text, draws a substitute after the user agrees. Corrects defects with edge trimming, face restoration, region redrawing, and final upscaling. Default model: DreamShaper 8 LCM. Use this skill whenever the user asks to create or draw an image, illustration, background, banner, cover, divider, slide background, landscape, portrait, or a picture for a report ('image generation', 'generate an illustration'), and to correct faces, hands, or edges in its images. Details in references/: composition.md (requests, substitution, scenes), models.md (presets, time estimates, cache), candidates.md (candidate mode), defects.md (defects, upfront workarounds, trimming), postprocess.md (face restoration, region redrawing), components.md (external sources)."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE.md
---

# Image Generation with Local Models

> This English edition is a translation of the Korean original. Its behavior may differ from what the original intends.

This skill generates images with local models. Model files are downloaded to the environment that runs the skill (the runtime environment). Generation runs on the runtime environment's CPU. The network is used only to download packages and model files. Prompts are never sent to an external image generation service. The output is a PNG or JPEG file.

Diffusion models cannot draw text, exact connector lines, numbers, or exact counts. For requests that require them, depict the intended meaning as an object or a scene. Text is added on top of the finished image in an editing tool.

## Workflow

1. Setup: create a dedicated virtual environment for the skill and install the dependencies.
2. Environment check: run probe.py to confirm what can run and the estimated time.
3. Request type and composition: determine the subject and its framing.
4. Preset: select the model.
5. Pre-generation questions: ask about the generation and correction policies in a single message and record the answers in preflight.json. If the candidate generation answer is not 1x (automatic included), read references/candidates.md before recording. If the upfront workaround answer is not off, read references/defects.md before recording.
6. Prompt: write an English prompt.
7. Generate: run generate.py or generate_klein.py.
8. Check and correction: first read the reference files in the reading-before-the-check section. Open the output and correct defects.
9. Final upscaling: if selected, apply it once to the adopted image. Run the post-upscaling recheck on the 4x result before delivery.
10. Delivery: provide the file and the reproduction details.

## Command notation

- `PY` is the Python of the skill's virtual environment: `~/.cache/image-gen/venv/bin/python` on Linux and macOS, `%USERPROFILE%\.cache\image-gen\venv\Scripts\python.exe` on Windows.
- Replace `scripts/` with the path of the scripts folder inside this skill's folder.
- Run commands from the user's working folder. Save results to the path the user specifies. If none is given, use the output folder the environment defines. If that is also absent, save to the working folder and give the user the absolute path.
- The scripts run with the same commands on Linux, macOS, and Windows. Only the precise preset requires Linux x86_64.
- Every file the skill downloads is stored in the cache folder `~/.cache/image-gen`. Set the environment variable `IMAGE_GEN_HOME` to change its location.
- Features that download files from GitHub are the precise preset engine (`leejet/stable-diffusion.cpp`), final upscaling (`xinntao/Real-ESRGAN`) and face restoration (`TencentARC/GFPGAN`, `xinntao/facexlib`). If the runtime environment has a tool that attaches a GitHub repository to the session, call it with the matching repository before each feature's first run. Pass the parts before and after `/` as separate owner and repository name values. Follow any access route the tool's reply specifies. Skip this step when no such tool exists or the call is refused.

## Setup

Install packages only into the skill's dedicated virtual environment. Do not remove or modify packages already in the user's environment, including GPU builds of torch or CUDA packages. The skill environment receives its own CPU build of torch, so the two environments do not interfere.

```
python3 -m venv ~/.cache/image-gen/venv
PY -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
PY -m pip install --no-cache-dir diffusers transformers accelerate safetensors peft huggingface_hub pillow numpy
```

- If `python3` is missing, use `python`. On Windows create the environment at `%USERPROFILE%\.cache\image-gen\venv`.
- Install torchvision together with torch from the same CPU index. If only torch is installed, the post-processing packages install a CUDA build of torchvision and fail with `operator torchvision::nms does not exist`.
- `--no-cache-dir` keeps downloaded installers out of the shared pip cache, so no cache remains to be cleaned afterwards.
- If a virtual environment cannot be created (for example the venv module is missing), ask the user whether to install into the current Python environment. Install there only with permission. If pip reports externally-managed-environment, add `--break-system-packages`.
- Without permission to install with pip, generation is not possible. Explain the reason and stop.
- Generation is also not possible where Python cannot run. Explain the reason, and provide the English prompt and the preset settings so the user can generate in an environment where Python runs.
- Install post-processing dependencies only when the user chooses post-processing, following the install section of references/postprocess.md.

## Environment check

```
PY scripts/probe.py --estimate
```

probe.py prints one JSON object. Determine the next step from the values below.

| Value | Meaning | Action |
|---|---|---|
| `hub_reachable` | Whether the model hub is reachable | If false and the model is not cached, explain the reason and stop |
| `dependencies` | Installed packages | If torch, diffusers, or transformers is false, return to setup |
| `free_disk_gb` | Free disk space at the cache folder | Compare with the download sizes in the preset table |
| `memory.total_gb` | Total memory | If insufficient, generate.py stops with exit code 6 before running |
| `cpu.native_bf16` | CPU support for bfloat16 instructions | Used to choose the precision (references/models.md) |
| `precise_tier_supported` | Whether the precise preset can run | If false, remove the precise preset from the choices |
| `estimate.seconds_per_image` | Estimated seconds per image by preset | Used for the time estimate given to the user |

### Time estimates

Base time estimates on a measurement of the runtime environment's CPU. `--estimate` measures matrix-multiply speed for a few seconds and divides each preset's workload by that speed. Memory speed, other running programs, and heat cause the actual time to differ, so state that it is an estimate every time you report it.

- Example: "The estimated time in this runtime environment is about 40 seconds per image, about 2 minutes for 3 images. This is an estimate, and I will update it after the first image."
- The first run includes download time. Download sizes are listed in the preset table.
- After the first image, use the `seconds` value from generate.py's output to update the estimate for the remaining images.
- The method and the workload values are in the time estimate section of references/models.md.

## Request types

Before generating, classify the request into one of three types. The criterion is whether the user specified a concrete subject to draw.

| Type | Criterion | Handling |
|---|---|---|
| Named subject | The user specifies something with a visible outline: an object, person, animal, or place | Draw it as specified |
| Message request | The user provides only an abstract concept or a message | Replace it once with an object or scene that can be drawn |
| Diagram request | It needs text labels, connectors, exact counts, or numbers (flowchart, concept map, architecture diagram, chart, KPI graphic) | Explain the limitations and a substitute, and draw after the user agrees |

- If the user specified a symbolic object, the choice has already been made. Keep it.
- With the upfront workaround at maximum, a named subject may also be replaced with another object or scene that conveys the same meaning. Present the revised setup and obtain confirmation before replacing it.
- If the user provides both an object and a message, draw the object and convey the message through style and color.
- Substitution rules, example tables, and the consent wording are in references/composition.md.

## Protection of minors

The skill does not generate unclothed figures or sexual depictions (sexual acts included) of minors.

- A minor is a figure stated to be under 18 or stated to have minor status, or a figure that clearly has a body before secondary sexual characteristics (a child's head-to-body ratio and build).
- Ambiguous signals that are not explicit and cultural tastes, such as a youthful face, large eyes, an idol-like look, cel-style art, short height, a slim build, or a trendy outfit, are not grounds for judging a figure a minor.

## Composition

There are two compositions: icon and scene. Follow the user's choice if they specify one. Otherwise decide based on where the image will be used. If that is also unknown, create an icon.

| Composition | Look | Main use | Prompt order |
|---|---|---|---|
| Icon | Subject in the center on a plain background | Body illustrations, slide illustrations, a picture built around one object | subject, style, color, `plain background` |
| Scene | Two or three common elements plus one time of day and one color family | Background images, banners, covers, section dividers, slide backgrounds, landscape pictures | elements, time of day, color, style |

- For icons, adopt a result where the subject is recognizable at a glance.
- For scenes, judge the mood of the whole scene over individual objects.
- Choosing elements, time of day, and color for scenes follows the scene building section of references/composition.md.

## Presets

A preset is a combination of a model and fixed settings. Change the style through the prompt and the model through the preset.

| Preset | Role | Suitable styles | Generation size | First download |
|---|---|---|---|---|
| `dreamshaper-8-lcm` | Standard, default | Photographic, illustration, painting, watercolor | 512x512 | about 4.3GB |
| `sdxs` | Light, fastest | General styles, simpler detail | 512x512 | about 2.1GB |
| `tiny-sd` | Flat | Flat vector with solid fills, watercolor with paint bleed | 384x384 | about 1.1GB |
| `flux2-klein-4b` | Precise, slowest | Most accurate instruction following and anatomy | 384x512 | about 5.2GB |

- With no style or quality requirement, use Standard.
- Standard produces broken shapes with flat vector keywords. Use Flat or Light for flat vector requests.
- Flat often cuts off heads or adds picture frames when a person is the main subject. For a person as the main subject, use Standard or Precise.
- Light tends to produce an illustration-like look even when a photographic style is requested.

### Model choice question

Add a model choice to the pre-generation questions when any condition below applies. If none applies, proceed with Standard without asking. If the user already specified a model or stated that speed or quality comes first, follow that without asking.

| Condition | Choices |
|---|---|
| 10 or more images in one request | Standard, Light |
| A person is the main subject (including full body or visible hands) | Standard, Precise |
| Flat vector or paint-bleed texture requested | Flat, Light |
| The environment check shows insufficient resources | Only the presets that can run |

- For each choice, state the estimated time per image (marked as an estimate), the first download size, and the differences in quality and style.
- Drafts, mockups, and repeated checks are a normal pattern of image generation use. They are not a reason to ask about the model or to select Light.
- The 10-image threshold is where Standard's total time grows long enough for the difference from Light to become noticeable. For 1 to 9 images the difference is small.

### Model lock

- Change the model used for the first image only with the user's permission within the same conversation. A model change involves gigabytes of downloads, a longer time per image, and a different style and look. All of these fall outside the cost and result the user expected.
- Correct defects within the selected model: seed changes, edge trimming, prompt workarounds, post-processing, and composition workarounds. Do not switch models as an automatic fix.
- If a different model would help, offer it as one option when the regeneration limit is reached, with its download size, estimated time per image, and what would change. If the user selects it, rerun preflight.py with only `--preset` changed, then switch.
- If a preset cannot run, state the cause in one line (insufficient disk, the process was terminated for lack of memory, download error) and offer the presets that can run. If deleting caches of non-default presets frees enough disk, retry without asking. If no preset can run, explain the reason and stop.

## Pre-generation questions

Before the first image, ask every applicable item from the table below in one message. Installation size, changes to a person's appearance, texture loss, and how much of the original intent the first prompt concedes depend on personal tolerance, so the user decides. Asking after a defect appears interrupts users who want the work to proceed automatically, so ask before generating.

| Item | Ask when | Skip when |
|---|---|---|
| Final upscaling | Every request | Never |
| Edge trim | Every request | Never |
| Defect post-processing | A person or a precise object appears | Never |
| Face restoration scope | A person appears | Never |
| Finger redrawing | A person appears | Defect post-processing is workarounds only |
| Candidate generation | Every request | Never |
| Candidate selection | A display path exists | Candidate generation is 1x |
| Spare candidate finishing | Every request | Candidate generation is 1x, or final upscaling is none while face restoration scope is other than always |
| Upfront workaround | Every request | Never |
| Regeneration limit multiplier | Every request | Never |
| Model choice | A model choice condition applies | The user specified a model, or stated that speed or quality comes first |

- If even one person appears in the frame, treat the request as one with a person, regardless of size, share of the frame, or style. Small, distant people show the most severe face defects, so a small share is not a reason to skip. If uncertain, treat it as a request with a person.
- A precise object is one recognized by how its parts connect: a bicycle, glasses, a chair, a ladder, a keyboard.
- Omit only the items the user has already answered. Also ask the items that have a recommended option.
- If the user delegates ("you decide", "use the defaults"), present the recommended combination in one line and obtain confirmation. Example: "Shall I proceed with 1-b, 2-b, 3-a, 4-a, 5-a, 6-a, 9-a, 10-a?" For non-photographic styles the recommended combination sets face restoration to off. Example: "Shall I proceed with 1-b, 2-b, 3-a, 4-c, 5-a, 6-a, 9-a, 10-a?" The recommended candidate generation is 1x. The upfront workaround remains at its default, off. The regeneration limit multiplier remains at its default, 1x.
- Ask about final upscaling, edge trimming, candidate generation, the upfront workaround, and the regeneration limit multiplier even when only objects appear.
- Before asking, make the display path judgment from the delivery section. Without a display path, reduce the items and choices as specified in that section's table.
- Candidate generation generates more candidates than the target count at once and selects from them. It performs defect handling step 1 (regenerate with the same prompt and a new seed) in advance, at generation time. The default 1x generates only the target count.
- For fixed multiplier choices, state the total count (target count times multiplier) and the estimated time from probe.py, and note that it is an estimate. For the automatic choice, state the range of total counts and times from 1x up to 3x, the upper end of the recommended range.
- Take a custom answer as a whole-number multiplier. When each target image has its own prompt, a total count alone does not decide how many images each prompt gets.
- In the choices of spare candidate finishing, name only the batch processes the user can select in this question. For objects only, name final upscaling alone.
- Judge the 10-image condition of the model choice question by the target count. The multiplier is answered in the same question, so whether to ask the model question cannot depend on the multiplier answer.
- If automatic resolves to 1x, the answers for candidate selection and spare candidate finishing are not used.
- The upfront workaround avoids the parts where diffusion models often produce defects from the first image, before any defect is seen. It applies to people, animals, objects, buildings, and scene elements alike. The default, off, generates the image as requested first. Once a defect appears, edge trimming and seed changes are applied first, and workarounds start at defect handling stage 2 only if the defect remains. Optimize preserves the subject and scene, and adds only staging that removes, hides, or places defect-prone parts outside the frame. Maximum preserves only the message and where the image will be used, and extends to composition changes, element removal, and subject replacement.
- The regeneration limit multiplier multiplies the regeneration limits of defect handling (references/defects.md). Always call it by this name to keep it apart from the candidate multiplier, and if it is unclear which multiplier the user means, confirm in one line. In the item description, state that the actual number of regenerations is the default limit of the model in use multiplied by the multiplier, and that generating more candidates reduces the number of stage 1 regenerations. The model and the candidate multiplier are answered in the same questions, so the choices state only the multiplier. After the answers arrive, state the resulting maximum number of regenerations and the estimated time (at 3x for unlimited) in one line before generating, and proceed without confirmation. If the request already specifies a multiplier or unlimited, omit the item and record that value.

Question format:

- Number only the applicable items from 1 in order, and write choices as a), b), c). Model choice always takes the last number.
- For a conditional item (finger redrawing, candidate selection, spare candidate finishing), state its condition in the first sentence with the actual item numbers.
- Write a numbered list in plain conversation text. Do not use code blocks or tables.
- Put the answer format and an example answer on the first line.
- Fit the examples in the upfront workaround choices to the parts of the request where defects tend to appear. Example: for a bicycle request, name a futuristic e-bike without spokes for optimize and a replacement with a futuristic vehicle without wheels for maximum.
- For photographic or watercolor requests, add a one-line warning to the final upscaling item. Example: "Upscaling removes skin texture and paper grain from photographic and watercolor styles."
- For non-photographic styles such as flat vector, line art, or cel shading, mark "off" as recommended for face restoration scope and add a one-line reason. Example: "In this style, only the restored face becomes photographic and does not match the drawing." Face restoration tools were trained on real photographs of faces.
- In the description of the face restoration scope item, add one line on how non-frontal faces are handled. Example: "For a person whose face is turned at an angle or to the side, restoration can make the face look unnatural, so I compare it with the original and use the better one." Face restoration tools were trained mostly on frontal photographs and align faces to a frontal reference.

Example for a request with a person:

> Before generating, I would like to confirm the items below. Please answer with the item number and choice letter. (Example: 1-b, 2-c, 3-a, 4-b, 5-a, 6-d, 7-b, 8-c, 9-a, 10-a)
> 1. [Final upscaling] Applied once at the end, after defect fixes and trimming.
>    a) None: trimming and enlargement to the target size leave some blur
>    b) general: suitable for most styles
>    c) flat: for flat vector art only
> 2. [Edge trim] When a defect such as a finger touches or is close to the frame edge, I trim a small strip from that edge before regenerating. The trimmed defect is removed from the frame entirely, so this is the most reliable fix in that case.
>    a) Off: edge defects go through the same handling stages as any other defect
>    b) Same ratio only: trims as much as needed while keeping the aspect ratio, then restores the original size. Applied without confirmation and reported on delivery
>    c) Free ratio allowed: when b does not resolve it, I present preview candidates with other ratios (for example a wider frame) and apply the ratio you select
>    d) Free ratio, automatic: when b does not resolve it, I select the candidate closest to the original framing, apply it, and let you know. The aspect ratio may change
> 3. [Defect post-processing] People's faces, clothing, and accessories may show shape defects.
>    a) Automatic post-processing: defects remaining after seed changes and prompt workarounds are corrected automatically with face restoration and region redrawing (about 1.2GB to install, about 2.3GB more for region redrawing)
>    b) Workarounds only: proceeds without installation, using seed changes, prompt workarounds, and composition workarounds
>    c) Ask each time: I will ask each time post-processing is needed
> 4. [Face restoration scope] For a person whose face is turned at an angle or to the side, restoration can make the face look unnatural, so I compare it with the original and use the better one.
>    a) Only on defects: applied according to item 3 when a face defect is found
>    b) Always: applies face restoration to every image with a person, regardless of defects. Eyes and teeth become sharper (applies even if item 3 is b, about 1.2GB to install)
>    c) Off: face restoration is neither installed nor used. Face defects are handled with seed changes and workarounds, and the clothing and accessory redrawing selected in item 3 remains as chosen
> 5. [Finger redrawing] Only if item 3 is a or c. It is rarely effective on fingers, so edge trimming, seed changes, and prompt workarounds are always tried first.
>    a) Off (recommended): remaining finger defects are handled with a composition that places the hands outside the frame
>    b) On: applied once to remaining defects, with a before and after comparison. Used only on hands that do not overlap other objects. Hand size and pose may change
> 6. [Candidate generation] I generate more candidates than the target count at once and select from them. This reduces the wait for regeneration after a defect. Counts and times are for a target of 1 image and are estimates for this runtime environment.
>    a) 1x: 1 image, about 40 seconds
>    b) 2x: 2 images, about 1 minute 20 seconds
>    c) 3x: 3 images, about 2 minutes
>    d) Automatic: 1-3 images, about 40 seconds to 2 minutes. I increase the multiplier only for defect-prone requests such as people, hands, or crowds, and inform you of it before generating
>    e) Custom: enter a whole-number multiplier (example: 6-e 4)
> 7. [Candidate selection] Only if item 6 is not a.
>    a) Agent selection: I select the target count, starting from candidates without defects, and continue through to completion
>    b) User selection: right after generation I present one numbered contact sheet, and finish the candidates you select by number
> 8. [Spare candidate finishing] Only if item 6 is not a, and item 1 is not a or item 4 is b. Determines whether the candidates you do not select (spares) receive final upscaling and always-on face restoration. Defect repairs apply to adopted images only.
>    a) Adopted only: spares are delivered as generated. Any spare can be finished later on request
>    b) All candidates: spares are delivered finished as well. Post-processing time increases with the number of candidates
>    c) Automatic: I choose a or b to suit the task and inform you before generating
> 9. [Upfront workaround] Diffusion models often produce defects in complex parts such as people's faces and fingers, the joints of objects, and building structures. Determines whether the first image already avoids such parts. A stronger workaround reduces defects and increases the departure from your request.
>    a) Off (default): I first generate the image as you requested. If a defect appears, I try trimming and a new seed first, and apply workarounds step by step only if the defect remains
>    b) Optimize: the subject and scene remain as requested, and the first prompt adds staging that removes, hides, or places defect-prone parts outside the frame. For this request, this means staging such as hands lowered at the sides, a shot that places the hands outside the frame, sunglasses, or gloves
>    c) Maximum: only the message you want to convey and where the image will be used are preserved, and defect-prone elements are avoided as much as possible. I may change the framing to a side view or a silhouette or remove elements such as a background crowd, and if needed replace the subject with another object or scene of the same meaning. I ask for confirmation before replacing a subject you specified, and inform you before generating when I change the framing or remove elements
> 10. [Regeneration limit multiplier] Determines the maximum number of regenerations while a defect remains. The actual count is the default limit of the model in use multiplied by this multiplier, and generating more candidates reduces the regenerations with the same prompt and a new seed by as much. When the limit is reached, I present the best result and ask how to proceed.
>    a) 1x (default)
>    b) 2x
>    c) 3x
>    d) Custom: enter a whole-number multiplier (example: 10-d 5)
>    e) Unlimited (not recommended): if a defect remains after 3x, I keep generating with the best result's prompt and a new seed without asking. I report progress in one line each time the attempts reach the default limit count. If you chose ask each time for defect post-processing, free ratio previews for edge trim, or user selection for candidates, I still wait for your answer at those questions

If a model choice condition applies, continue with the last number. Example:

> 11. [Model choice] A person is the main subject, so the rate of shape defects depends on the model. Times are estimates for this runtime environment.
>    a) Standard (DreamShaper 8 LCM): about 40 seconds per image, 512px, frequent hand and clothing defects
>    b) Precise (FLUX.2 klein 4B): about 15 minutes per image, 384x512, the most accurate shapes. Downloads about 5.2GB on the first run

The times in the example illustrate the format only. Use probe.py's estimates in actual questions.

### Reading before recording

If the candidate generation answer is not 1x (automatic included), read references/candidates.md right after the answers arrive and before recording them with preflight.py. It covers the automatic decisions on the candidate multiplier and spare candidate finishing, the candidate pool, candidate adoption, the scope in candidate mode, and spare deletion. With 1x, proceed without it.

If the upfront workaround answer is optimize or maximum, read references/defects.md right after the answers arrive and before recording them with preflight.py. Its upfront workaround section specifies what each answer preserves and which workarounds it uses. The confirmation procedure for a subject replacement under maximum is also in that section. A subject replacement can change `--subject` and the automatic candidate multiplier, so complete the confirmation before recording. With off, read the file after generation, before the check.

### Recording answers

After the user answers, write preflight.json to the output folder with preflight.py. The generation scripts stop with exit code 2 when this file is missing, and preflight.py stops with exit code 2 and lists missing items when a required answer is absent. Do not record values filled in without asking.

```
# A person appears, answer "1-b, 2-c, 3-a, 4-b, 5-a, 6-d, 7-b, 8-c, 9-b, 10-b", automatic judgment chose 3x and all candidates
PY scripts/preflight.py --out ./outputs --subject person --display available --enhance general --trim free --postfix auto --face-scope always --finger-inpaint off --candidates auto --candidates-resolved 3 --candidates-reason "full body framing with hands visible" --candidate-pick user --spare-finish auto --spare-finish-resolved all --spare-finish-reason "user selection with always-on face restoration" --upfront-workaround optimize --regen-scale 2 --user-reply "1-b, 2-c, 3-a, 4-b, 5-a, 6-d, 7-b, 8-c, 9-b, 10-b"

# Objects only, with a model choice, answer "1-b, 2-b, 3-a, 6-a, 7-a, 8-b"
PY scripts/preflight.py --out ./outputs --subject other --display available --enhance general --trim same --candidates 1 --upfront-workaround off --regen-scale 1 --preset sdxs --user-reply "1-b, 2-b, 3-a, 6-a, 7-a, 8-b"
```

- `--subject` is `person` when a person appears, `precise-object` when a precise object appears without a person, and `other` otherwise.
- `--display` is the result of the display path judgment in the delivery section: `available` with a display path, `none` without one. With `none`, `--trim free`, `--finger-inpaint on`, and `--candidate-pick user` are refused with exit code 2.
- `--candidates` is a whole-number multiplier or `auto`. With `auto`, enter the decided multiplier (a whole number of 1 or more) in `--candidates-resolved` and a one-line reason in `--candidates-reason`.
- `--candidate-pick` is `auto` for agent selection and `user` for user selection.
- `--spare-finish` is `adopted` for adopted only, `all` for all candidates, and `auto` for automatic. With `auto`, enter the decided value in `--spare-finish-resolved` and a one-line reason in `--spare-finish-reason`.
- `--upfront-workaround` is `off` for off, `optimize` for optimize, and `max` for maximum.
- `--regen-scale` is the regeneration limit multiplier: `1` to `3` for 1x to 3x, the entered whole number for custom, and `unlimited` for unlimited.
- Candidate selection and spare candidate finishing are needed only when the multiplier in force is 2 or more. Unused items are recorded as null. Later steps use the values recorded in `candidates_resolved` and `spare_finish_resolved`.
- `--user-reply` contains the user's answer verbatim.
- Later images in the same conversation reuse the record in the same output folder. If the user changes a choice or the presence of a person changes, rerun preflight.py.
- If the style newly changes to photographic or watercolor, ask only the final upscaling item again. If the style switches between photographic and non-photographic, ask only the face restoration scope item again.

## Prompt

- Write prompts in English. Korean and other non-English prompts are interpreted as a list of nouns, and style and place instructions are barely reflected.
- Place the subject and style keywords first. Do not lengthen the prompt with lists of modifiers.
- Name the style by its technique. Keywords such as `watercolor illustration`, `flat vector illustration`, `digital painting`, and `photorealistic` are reflected better than abstract phrases such as `minimal editorial style`.
- Name the color family, for example `muted blue and beige palette`.
- Proper nouns, technical terms, and words that are not widely used may not be recognized by the model. Diffusion models associate a word with a shape only when it appeared frequently in the captions of their training images. The criterion is whether the word would commonly appear in an everyday English photo caption.
- Replace such a word with a similar common object, or describe its appearance through its components. Replace it when the exact appearance is not essential to the request, and describe it when its particular appearance is essential. Examples: a little-known car model name becomes `a small white electric car`, and the name of a piece of armor from a game becomes `golden plate armor`.
- List only the 2 or 3 shapes, materials, or colors needed to recognize it, and keep them simple. More decorative detail makes the shape more likely to break down. A long description exceeds the 77-token limit of the SD 1.5 family presets and increases missing elements.
- Do not request text inside the image.
- Do not use single quotes ('). They conflict with command-line quoting.
- Standard, Light, and Flat belong to the SD 1.5 family. They respond well to short keyword-style English and reflect long natural sentences poorly. Their text window is 77 tokens, and anything beyond it is ignored without an error. The 75 tokens remaining after the start and end markers are about 50 English words. If generate.py prints a warning with the ignored text, shorten the prompt and run again.
- Precise accepts natural sentences as they are and has no 77-token limit. It does not use a negative prompt.
- Fix the seed to reproduce a result. Change it for variety.
- With the upfront workaround off, do not include workaround instructions (hats, sunglasses, gloves) in the first prompt. Use them only after defect handling reaches stage 2. Accessories the user requested from the start are part of the original intent, so include them.
- With the upfront workaround at optimize or maximum, include workaround staging in the first prompt as specified in the upfront workaround section of references/defects.md.

## Generate

```
# Icon, default preset
PY scripts/generate.py --prompt "a brass compass on a desk, watercolor illustration, plain background" --out ./outputs --name compass

# Scene banner 1024x576, keep the top of an upright subject
PY scripts/generate.py --prompt "a lighthouse on a rocky coast at sunrise, muted blue palette, watercolor illustration" --out ./outputs --name banner --width 1024 --height 576 --anchor-y 0.0

# Four images of one prompt, the model loads once and the seed increases by 1
PY scripts/generate.py --prompt "a stone staircase, digital painting, soft light, plain background" --out ./outputs --count 4

# Flat preset
PY scripts/generate.py --preset tiny-sd --prompt "flat vector illustration of a single lighthouse, muted blue palette, plain background" --out ./outputs --name lighthouse_flat
```

- Always generate square images. Rectangular generation stretches or squashes the subject along the long side. Other ratios are obtained by cropping after generation.
- `--width` and `--height` must be given together. `--anchor-x` and `--anchor-y` set the crop anchor: 0.0 is left or top, 0.5 is the center, 1.0 is right or bottom. For upright subjects such as people, towers, and lighthouses, keep the top with `--anchor-y 0.0`. For sky and horizon scenes, place the horizon in the lower third.
- If final upscaling is chosen, outputs are saved at working size with only the target ratio (a 1024x576 target from a 512px square becomes 512x288). finalize.py produces the target size at the end.
- If final upscaling is off, outputs are enlarged to the target size at this step. Plain enlargement adds pixels without adding detail. Flat's 384px outputs are enlarged to 512px.
- Generate several images with `--count`. Each additional call of the script adds model loading time.
- If a file exists at the same path, the new file is saved with a number appended. Use `--overwrite` only when overwriting is intended.
- stdout prints one JSON line per image with the path, prompt, seed, preset, precision, size, and seconds.
- Open any result cropped to another ratio and check that the subject is not cut off. If it is, run again with the same seed and only the anchor changed. If no anchor fits the whole subject, add a framing that suits the target ratio (distant placement, upper body) to the prompt and regenerate.
- Run the precise preset with generate_klein.py following the precise preset section of references/models.md.

When the multiplier in force is 2 or more, generate the candidates as described in the candidate pool section of references/candidates.md.

## Check

generate.py checks each file right after saving: size over 10KB, magic bytes (JPEG `FFD8FF`, PNG `89504E47`), and pixel size. On exit code 7, regenerate before the visual check.

### Reading before the check

Once generation ends, read references/defects.md before the check and before always-on face restoration. It contains the defect criteria and the scope of the fixes that the trim-first check and the candidate adoption order rely on. Reading it only after a defect is found means checking without those criteria.

When defect post-processing is automatic post-processing or ask each time, or the face restoration scope is always, read references/postprocess.md as well. It specifies which defects post-processing can and cannot fix. With any other answers, no post-processing tool is used.

- If what you read is still in the conversation, do not read it again.

### Visual check

Once the machine check passes, open the file and inspect it.

- Does the subject the user specified appear as specified?
- Are the prompt's style and color reflected?
- Is the shape still recognizable at the size it will be used?
- Does an unrequested person occupy the center of the frame?
- Is there a count defect (more objects than intended, the same subject twice, and the like)?
- Does the body count of people and animals match the standard count (5 fingers on each hand, 5 toes on each foot, 2 arms, and 2 legs for a person, 4 legs for a four-legged animal, and the like)?
- Does a person's face show a face defect (eyes of different sizes, features out of place or unevenly spaced, a face smeared as a whole, a missing eye, nose, or mouth, and the like)?
- Do people and animals show any other anatomical defect (distorted animal facial features, the shape of hands and feet, body distortion, and the like)?
- Do clothing, accessories, objects, and buildings show a connection or structure defect (broken glasses frames, missing straps, tangled spokes, a distorted complex machine, a building with a distorted form such as a roof floating without pillars, and the like)?
- Is there an unclothed figure or a sexual depiction that falls under the protection of minors section?
- Does each defect touch or come close to one of the four edges?
- For a substituted diagram request, or a framing or subject changed under the maximum upfront workaround, does the picture carry the original message?
- Even outside this list, is there any area that looks like a typical diffusion model defect or looks visually unnatural, or any staging the user asked for that was not reflected?
- If the subject looks squashed horizontally or vertically, regenerate as a square.

The items in parentheses are examples. A shape problem is a shape that differs from the real appearance or from the requested style and that nothing visible in the frame explains. Visible causes are occlusion (something visibly covering the front of the part), the frame edge, the angle of the face and the pose, and omissions and exaggerations the style intends. Darkness, blur, out-of-focus areas, and the like that were not meant to hide that part do not count as occlusion. Treat any other shape problem as a defect by the same standard. If uncertain, treat it as a defect. If final upscaling is chosen, run these checks on the working-size output. After final upscaling, apply these checks again to the 4x result as described in the post-upscaling recheck section of references/defects.md.

For fragile subjects, inspect the full frame first, then enlarge the parts where defects tend to appear (faces, hands and feet, joints between parts, and the like) and inspect them again. A part drawn small rarely shows its defects in the full frame.

- Create the enlarged view by giving grid_measure.py a region. Enlarge each defect-prone part separately, with a region that the part nearly fills. An approximate region is sufficient. A region that contains several parts has a low zoom, so small defects such as fingers appear as small as in the full frame.
- Count arms and legs in the full frame. Count fingers and toes one by one on the enlarged view, for each hand and foot. Hands touching or pressed against the floor, the waist, the back, a thigh, clothing, hair, and the like are easy to miss, because the finger edges blend into the surface they touch. Fingers and toes are hard to judge, so when hands or feet are exposed, the ideal result shows all five clearly and correctly.
- On the enlarged view of a face, check that the eyes, nose, and mouth are all there. Compare their position, spacing, size, and left-right balance with the placement criteria in defects.md.
- Follow the outline of large parts such as the belly, waist, thighs, and chest in the full frame. A part whose outline breaks off, melts into clothing, the background, or another body part, or twists in a way the pose does not explain is body distortion.
- If you find a defect, use the enlarged grid for the trim and region-redrawing coordinates as well.
- Do not enlarge an image you have already decided not to adopt.

Record the check result in one line per image. Write the parts you inspected and what you observed, and for items without a defect, write the basis for that judgment. Write the body count as the number you counted for each part. For a face, write the angle of the face, whether the eyes, nose, and mouth are there, and how they compare with the placement criteria. For fragile subjects, list the enlarged files in an enlarged item at the start of the record. If the record of an image to adopt has no such item, the check is not finished, so enlarge first. In candidate mode, the adoption ranking and the defects reported in user selection are based on this record.

- Example: `reader-01: enlarged (reader-01_face.png, reader-01_hand_l.png, reader-01_hand_r.png), body count wrong (right hand 6 fingers, touching the bottom edge), no face defect (three-quarter view, all features there, far eye narrower by the angle, both eyes level, nose and mouth on the turned center line), no anatomical defect (elbows and knees bend naturally), no count defect, no connection defect (glasses frame intact)`
- Example: `reader-02: enlarged (reader-02_face.png, reader-02_hand_l.png, reader-02_hand_r.png), body count right (2 arms, 2 legs, left hand 5 fingers, right hand 3 fingers plus 2 behind the newspaper, toes covered by shoes), no face defect (profile, far eye hidden by the head, visible eye, nose, and mouth in natural order and spacing), no anatomical defect (hands holding the newspaper look natural), no count defect, connection defect (left glasses frame broken, far from the edges)`
- Omit items that do not apply (such as body count, face, and anatomical defects in an image with objects only).

When the multiplier in force is 2 or more, adopt the target count as described in the candidate adoption section of references/candidates.md. Apply the answers to the existing items as described in the scope in candidate mode section of the same file.

## Defect handling

If you find a defect, follow the order in references/defects.md. The overall order is as follows:

1. Trim-first check: if the defect touches or is close to an edge and nothing else requires a new image, trim the edge before regenerating whenever the trim answer is same ratio only, free ratio allowed, or free ratio automatic.
2. General defects: correct style, color, count, background, and framing problems with prompt edits and seed changes.
3. Fragile subjects (people, animals, precise objects, background crowds): go through stage 1 seed change, stage 2 prompt workaround, stage 3 post-processing, stage 4 composition workaround.
4. If the limit scaled by the regeneration limit multiplier is reached, present the best result with the defect marked and ask how to proceed. With unlimited, switch to the repeat phase without asking. The definition of the best result, the multiplier calculation, and unlimited operation are in the regeneration limit section of references/defects.md.

Stages 2 and 4 choose from workarounds the upfront workaround did not use. The detailed rules are in the upfront workaround section of references/defects.md.

When the multiplier in force is 2 or more, subtract the number of pool swaps from the stage 1 limit for fragile subjects. Once the pool is exhausted, regenerate only as many times as stage 1 has left, then proceed to stage 2. For general defects, subtract the number of pool swaps from the seed change limit. The detailed rules and the regeneration limits are in references/defects.md.

Choosing, tuning, installing, and cleaning up the post-processing tools (face restoration, region redrawing, finger redrawing) is covered in references/postprocess.md.

## Final upscaling

Final upscaling enlarges 4x with super-resolution and then scales down to the target size. Generation is 512px or smaller, so trimming, non-square formats, and target sizes all require enlargement. Plain enlargement blurs the image, so this step replaces every enlargement.

| Choice | Suitable for | Side effect |
|---|---|---|
| None | Requests where texture matters most | The original blur remains |
| general | Most styles, including people | Removes skin texture and paper grain in photographic and watercolor styles |
| flat | Flat vector backgrounds | Waxy skin, exaggerated nostril edges, and clumped hair on people |

- Apply it once, to the adopted image, after all defect fixes and trimming. Applying it right after generation means enlarging again after a trim or running it twice, and the waxy look accumulates. Face restoration and region redrawing are tuned for the pre-upscaling size too. Discarded attempts do not receive it, so the extra time covers one adopted image. If the post-upscaling recheck leads to a fix of the adopted image, run it once more with the fixed adopted image as the input.
- In candidate mode, follow the spare candidate finishing value in force. With all candidates, each spare also receives it once, so the extra time increases with the number of candidates. Spares receive no defect repairs, so apply it in the output folder right after adoption.
- Texture loss is inherent to the post-processing, so no prompt or seed can restore it.
- Super-resolution does not repair facial features. Face defects go through defect handling.
- On first use it downloads weights of a few MB from GitHub and checks their SHA-256. No additional installation is needed.
- Keep the target within 4x of the input. Any excess is handled as plain enlargement.
- It runs as a separate command after generation has exited, so memory use does not overlap.

```
PY scripts/finalize.py ./outputs/banner_trim.png ./outputs/banner_final.png --size 1024x576 --x4-out ./outputs/banner_x4.png
```

- Without `--size` the result is 768x768. The mode follows the answer in preflight.json.
- If trimming changed the ratio, pass the `target=WxH` printed by edge_trim.py to `--size` unchanged. Passing the original target crops back to the original ratio and cuts off the parts you preserved.
- `--x4-out` saves the 4x result before the downscale for the post-upscaling recheck. The recheck covers adopted images, so pass it for adopted images only.
- Right after the run and before delivery, inspect the 4x result as described in the post-upscaling recheck section of references/defects.md.

## Delivery

- Name files in lowercase English with underscores that describe the content, for example `lighthouse_flat_vector.png`.
- If the environment has a way to present files, use it. Otherwise give the absolute path.
- Record the reproduction details: prompt, seed, preset, size, and the final upscaling choice.
- If the upfront workaround was used, add the choice to the reproduction details, and report the workaround staging you added and the elements that differ from the original request.
- In candidate mode, present the candidates folder path and the contact sheet along with the adopted images. Add each candidate's seed, the multiplier in force, and the spare candidate finishing choice to the reproduction details. For a multiplier or spare candidate finishing choice decided automatically, include the reason.
- For trimmed results, report the trim, the body part the cut line crosses, and the cut ratio (for free ratio, the adopted ratio and the remaining area).
- If the prompt replaced or described a word the model may not recognize, report the original word with the expression used.
- For JPEG, generate with `--format jpg` or convert the PNG.

When the multiplier in force is 2 or more, spare deletion follows the spare deletion section of references/candidates.md.

### Display path judgment

Every point that presents images to the user follows this judgment. Make it once, at the pre-generation question stage. Check the tools available to you and where you run, and select one of the three below.

| Display path | Criterion | `--display` |
|---|---|---|
| File presentation tool | The runtime environment has a tool that shows files on the user's screen | `available` |
| Shared file system | The agent runs on the user's computer, so the user can open an absolute path you give | `available` |
| No display path | As in a remote runtime environment without a presentation tool, the user cannot open an absolute path you give | `none` |

Without a display path, handle each point as below.

| Point that shows images | Without a display path |
|---|---|
| User selection in candidate selection | Do not ask the item. Proceed with agent selection |
| Free ratio allowed in edge trim | Remove the choice |
| On in finger redrawing | Remove the choice, because it needs a before and after comparison |
| Before and after comparison of face restoration in non-photographic styles | Select the version that suits the style yourself and give a one-line reason on delivery |
| Regeneration limit reached | Describe the defect location in words and ask how to proceed |

- After removing a choice, relabel the remaining choices from a) in order. Ask the finger redrawing item and record the answer even when only off remains.

## Resources and cache

- Check disk and memory again right before each download and each run. The models, face restoration, region redrawing, and final upscaling each download weights, so free space keeps changing within one conversation.
- Run generation, face restoration, region redrawing, and final upscaling as separate processes, one at a time. Confirm the previous process has exited before starting the next. Running two at once can exhaust memory and cause termination.
- If a process is terminated for lack of memory, clean up leftover processes and retry once. If memory is still insufficient, offer the lighter presets that can run.
- The skill deletes only files inside its cache folder. It does not modify files outside it or the model caches of other programs. The one exception is candidate mode spare files that the user asked to delete (the spare deletion section of references/candidates.md).
- If disk space runs low, delete post-processing weights that are no longer needed first, then presets other than the default. Keep files you will use again in the same conversation, because downloading them again takes time.
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
| Exit code 2, argument error | Missing argument or value out of range | Correct the argument as the message indicates. For BOX_TOO_LARGE, split the box |
| Exit code 3 | Weight download failed | Run again. If it fails repeatedly, disable final upscaling and inform the user |
| Exit code 4 | Missing dependency | Return to setup or the post-processing install |
| Exit code 6 | Not enough memory or disk | For disk, delete non-default preset caches with cache.py and retry. For memory, follow the steps in the model lock section |
| Exit code 7 | Output check failed | Regenerate with another seed |
| Exit code 8 | Weight hash mismatch, the damaged file was deleted | Run again to download a fresh copy. If it fails repeatedly, disable that feature and inform the user |
| Exit code 9 | The operating system cannot run the precise preset | Offer other presets |
| Style ignored | Non-English prompt or abstract style words | Rewrite in English and place a technique name first |
| Smeared shapes | Preset settings were changed | Restore the script's default steps, guidance, and scheduler |
| Text, counts, or states ignored | A limit of diffusion models | Remove those instructions and add the content in an editing tool |
| The object the user specified is missing | A named subject was classified as a message request | Reclassify it as a named subject and regenerate with that object |
| The object the user specified appears as something else | The model does not recognize the name (proper noun, technical term, rare word) | Replace it with a similar common object or describe its components, as the prompt section specifies |
| `KeyError: '__version__'` while installing gfpgan | basicsr's setup.py fails on newer Python (seen on Python 3.13 with basicsr 1.4.2) | Follow the workaround in the install section of references/postprocess.md |
| functional_tensor error when importing gfpgan | basicsr imports a module torchvision removed | Run `PY scripts/patch_basicsr.py` and try again |
