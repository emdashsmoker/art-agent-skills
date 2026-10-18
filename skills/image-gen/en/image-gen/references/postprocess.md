# Post-processing: face restoration and region redrawing

Read this for stage 3 of the fragile-subject procedure and for always-on face restoration. Post-processing redraws only the defective part and leaves the rest of the image as it was. It keeps the original intent at the cost of installation size and time.

## Tools

| Defect | Tool | Script | Extra download |
|---|---|---|---|
| Blurry face (pupils, lashes, teeth) | GFPGAN v1.3 | face_fix.py | about 0.6GB of packages, about 0.6GB of weights |
| Distorted face (asymmetry, misplaced features) | GFPGAN v1.3, then region redrawing if it remains | face_fix.py, region_fix.py | As above, plus the region redrawing model |
| Small defects in clothing and accessories, precise objects | SD 1.5 inpainting | region_fix.py | about 2.3GB of models |
| Number and shape of fingers (when chosen, hands shown on their own) | SD 1.5 inpainting at strength 0.85 | region_fix.py | As above |

These defects are left out of post-processing by default.

- Finger defects: redrawing seldom fixes them in practice. Apply it once, only after edge trimming and the stage 2 workarounds are used up, and only if the user chose it in the pre-generation questions.
- Animal faces and background crowds: restoration showed no benefit. Handle them with stages 1, 2, and 4.
- Wrong number of limbs, or a broken connection between upper and lower body: redrawing a region cannot rebuild the pose. Handle them with stages 1 and 4.

## Defect post-processing policy

For requests with a person or a precise object, ask about the policy once before the first image. Apply the answer to later images in the same conversation. If the user changes it, use the new value from the next defect on.

- Automatic post-processing (`auto`): once stage 2 is used up, enter stage 3 without asking and adopt the result with the defect fixed. This answer also counts as consent to install the dependencies.
- Workarounds only (`bypass`): stage 3 is skipped, so the post-processing dependencies are not installed. Edge trimming installs nothing, so it stays available if the trim answer allows it.
- Ask each time (`ask`): ask about the tool and whether to proceed each time stage 3 comes up.

## Face restoration scope

For requests with a person, the same questions offer: only on defects, always, or off. This item is independent of the defect post-processing policy. In 512px outputs, even faces that pass as defect-free have blurry pupils and teeth, so some users want restoration regardless of defects.

- Only on defects (`defect`): apply at stage 3, following the defect post-processing policy, only when a face defect shows.
- Always (`always`): apply face restoration once to every output with a person right after generation, and do the visual check on the restored image. Apply it to regenerated results too. Install the face restoration dependencies even when the defect policy is workarounds only. Region redrawing stays uninstalled in that case. The order is generation, face restoration, final upscaling.
- Off (`off`): do not install the face restoration dependencies. Handle face defects with stages 1, 2, and 4. Off covers face restoration only, so region redrawing of clothing, accessories, and precise objects still follows the defect post-processing policy.

For non-photographic styles (flat vector, line art, cel shading and so on), mark off as recommended in the questions. Face restoration tools were trained on real photographs of faces, so only the restored area turns photographic and clashes with painted hair. If the user chose restoration in such a style anyway, show before and after side by side and ask whether to adopt, even in automatic mode and in always-on scope.

Outputs where no face is detected (back views, distant figures) are saved with the same pixels as the input. Use them as normal outputs.

## Using face restoration

GFPGAN v1.3 brings back sharp pupils and lashes. On faces with misplaced eyes it follows the original, so part of the asymmetry remains. Areas outside the face, and hands, stay as in the original.

```
PY scripts/face_fix.py in.png out_face.png
```

- If distortion remains after GFPGAN, redraw the face box with region redrawing. Apply it once in this case too and compare before and after.
- The weights download from a GitHub release on first use and are checked by SHA-256. facexlib downloads its helper models (face detection and face parsing) into the cache folder.

## Region redrawing

If the whole image works except for one defect, redraw just that part. Examples: a broken glasses frame, a missing strap, unrequested exposure of genitals or female nipples, tangled bicycle spokes.

- Extending: fixes that continue an existing shape, such as a broken frame or a strap that vanishes halfway, use strength 0.65. At 0.85 the shape gets drawn over itself and looks worse.
- Covering: fixes that put another material over skin, such as covering exposed skin with fabric or lengthening a short sleeve, use strength 1.0. Lower strengths follow the original colors and the material does not change.
- Fixing a distorted face starts at strength 0.65. Fit the box to the face outline and leave out hair where possible. Hair and lighting inside the box get redrawn too and can change color from the original.
- Measure box coordinates with the grid from grid_measure.py. For extending, keep the box tight around the defect. For covering, make it wide enough to show the fabric to continue on both sides.
- Parts attached inside the box (a mudguard, an object in a hand) disappear, so keep them out of the box.
- Describe only the desired result in the prompt, for example `thin gold metal sunglasses frame, round lens rim continuing into a straight temple arm, photorealistic`. Never name what should go away.
- The model input is a square no larger than the image's short side. If the box is longer than that on a wide trimmed image, region_fix.py stops with `BOX_TOO_LARGE`. Split the box and run each part.

```
PY scripts/region_fix.py in.png out_region.png 387,173,460,267 "thin gold metal sunglasses frame, round lens rim continuing into a straight temple arm, photorealistic" 42           # extending, default strength 0.65
PY scripts/region_fix.py in.png out_region.png 313,260,377,347 "white cotton t-shirt sleeve fabric covering the upper arm, soft fabric folds, photorealistic" 42 1.0      # covering
PY scripts/region_fix.py in.png out_region.png 117,167,227,267 "a natural open human hand with five fingers, palm facing the camera, photorealistic" 42 0.85          # fingers, when chosen
```

## Finger redrawing

For requests with a person where the defect policy is automatic or ask each time, the same questions ask whether to use it. The recommendation is off, and the question says it seldom works before listing the choices. In one case with a single open hand, the finger count got fixed but the hand's size and pose changed from the original.

- Even when chosen, use up stage 1 seed changes, edge trimming, and stage 2 workarounds first. Then apply it once at stage 3.
- If the defect remains, do not repeat it with other strengths or seeds. Go to the stage 4 composition workaround.
- Hand size and pose can change a lot, so even in automatic mode show before and after side by side and ask whether to adopt.
- It applies to hands shown on their own, overlapping nothing. A hand holding an object, or two overlapping hands, would lose the object inside the box, so skip them even when the user chose this tool.
- The strength is 0.85. At 0.65 the wrong finger count stays, and at 1.0 the whole hand turns into another pose and no longer connects to the arm.
- Draw the box from the fingertips to just before the wrist. Describe the desired result in the prompt.

## Checking and recording

- Open the post-processed result next to the original and check that the defect is gone, that the texture at the boundary matches, and that the style has not shifted. Then adopt it.
- The strengths and settings in the scripts are recommended values. If you change one, record the new value and the reason in the adoption record.
- Add the defect post-processing policy, face restoration scope, finger redrawing choice, tool, strength, box coordinates, and seed to the adoption record.

## Installation

Install only when post-processing is chosen, and before any other post-processing work.

```
PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu gfpgan   # face restoration
PY scripts/patch_basicsr.py                                                                      # once, right after installing
```

- Region redrawing uses the same packages as generation (diffusers, transformers, accelerate, peft, huggingface_hub), so it needs no extra install. Only the model downloads on first use.
- Pass the CPU index with `--extra-index-url` when installing the face restoration packages. basicsr builds from source during installation and downloads torch again into a separate build environment. Without the index it pulls a CUDA build of torch and related packages worth several GB, which can fill the disk. The same option keeps the torchvision that gfpgan requires on the CPU build.
- patch_basicsr.py replaces a module path that torchvision removed, only inside the basicsr package. It touches no other package.
- If the gfpgan install fails with `KeyError: '__version__'`, the version reader in basicsr's setup.py is at fault (seen on Python 3.13 with basicsr 1.4.2). Apply the steps below only in that case.
  - `pip download` runs the same setup.py, so download the basicsr source archive (.tar.gz) straight from PyPI. `https://pypi.org/pypi/basicsr/json` lists its URL. Unpack it in a temporary folder.
  - In `get_version()` of setup.py, pass a new empty dict to `exec` as its globals, and read `__version__` from that dict instead of `locals()`.
  - Install from the unpacked folder with `PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu <folder>`, then run the gfpgan install again.
  - Delete the temporary folder afterwards.
  - If the install still fails, try once more with an earlier Python (3.12 or 3.11, both confirmed to install). Recreating the virtual environment deletes it, so ask the user first. If no earlier Python exists or it fails too, turn face restoration off and tell the user.

## Cleanup

If post-processing is no longer needed, delete its caches.

```
PY scripts/cache.py delete face
PY scripts/cache.py delete inpaint
```

To remove the packages as well, run `PY -m pip uninstall gfpgan basicsr facexlib`. Only packages inside the virtual environment are removed.

## Validation

After upgrading a tool or package, produce defects on purpose with the prompts below, apply the tool, and compare before and after. Defects differ between model and package versions even with the same prompt and seed, so if no defect appears, change the seed until you find a sample with one.

| Tool to check | Prompt | Check for |
|---|---|---|
| Face restoration (distortion) | a businessman pointing his finger toward the camera, arm extended forward, waist up shot, office at night, photorealistic | Less asymmetry with the look preserved |
| Face restoration (blur) | a young woman smiling, waist up portrait, office daylight, photorealistic | Sharper pupils and teeth |
| Small faces and hands | a construction worker in a safety vest holding a power drill, building site, full body, hands visible, photorealistic | Whether a small face gets restored, the hands and the tool |
| Broken limb connections | a gymnast in a handstand pose, one leg extended, gymnasium floor, full body, hands and feet visible, photorealistic | Confirms a defect post-processing cannot fix |
| Finger redrawing | a woman waving her open hand at the camera, waist up, bare hands visible, park daylight, photorealistic | Finger count, changes in hand size and pose |
| Extending | close up portrait of a woman wearing thin metal frame sunglasses, three quarter view, daylight street, photorealistic | The broken frame joins without being drawn twice |
| Covering | a young woman in a plain white t-shirt standing on a daylight street, waist up, photorealistic | The sleeve extends as fabric, visible seams |
| Precise objects | a bicycle leaning against a brick wall, side view, full wheels visible, daylight, photorealistic | Rims and spokes come out clean |
