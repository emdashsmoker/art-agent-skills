# Post-processing: face restoration and region redrawing

This covers stage 3 of the fragile-subject procedure and always-on face restoration. When defect post-processing is automatic post-processing or ask each time, or the face restoration scope is always, read this once generation ends, before the check and before always-on face restoration, because it specifies which defects post-processing can and cannot fix. Post-processing redraws only the defective part and keeps the rest of the image unchanged. It preserves the original intent at the cost of installation size and time.

## Tools

| Defect | Tool | Script | Extra download |
|---|---|---|---|
| Blurry face (pupils, lashes, teeth) | GFPGAN v1.3 | face_fix.py | about 0.6GB of packages, about 0.6GB of weights |
| Distorted face (asymmetry, misplaced features) | GFPGAN v1.3, then region redrawing if it remains | face_fix.py, region_fix.py | As above, plus the region redrawing model |
| Small defects in clothing and accessories, precise objects | SD 1.5 inpainting | region_fix.py | about 2.3GB of models |
| Number and shape of fingers (when selected, isolated hands) | SD 1.5 inpainting at strength 0.85 | region_fix.py | As above |

These defects are excluded from post-processing by default.

- Finger defects: redrawing is rarely effective on them in practice. Apply it once, only after edge trimming and the stage 2 workarounds are exhausted, and only if the user selected it in the pre-generation questions.
- Animal faces and background crowds: restoration showed no benefit. Handle them with stages 1, 2, and 4.
- Wrong number of limbs, or a broken connection between upper and lower body: redrawing a region cannot rebuild the pose. Handle them with stages 1 and 4.

## Defect post-processing policy

For requests with a person or a precise object, ask about the policy once before the first image. Apply the answer to later images in the same conversation. If the user changes it, apply the new value from the next defect onward.

- Automatic post-processing (`auto`): once stage 2 is exhausted, enter stage 3 without asking and adopt the corrected result. This answer also counts as consent to install the dependencies.
- Workarounds only (`bypass`): stage 3 is skipped, so the post-processing dependencies are not installed. Edge trimming requires no installation, so it remains available if the trim answer allows it.
- Ask each time (`ask`): ask about the tool and whether to proceed each time stage 3 is reached.

## Face restoration scope

For requests with a person, the same questions offer three choices: only on defects, always, or off. This item is independent of the defect post-processing policy. In 512px outputs, even faces judged defect-free have blurry pupils and teeth, so some users want restoration regardless of defects.

- Only on defects (`defect`): apply at stage 3, following the defect post-processing policy, only when a face defect is found.
- Always (`always`): apply face restoration once to every output with a person right after generation, and perform the visual check on the restored image. Apply it to regenerated results too. Install the face restoration dependencies even when the defect policy is workarounds only. Region redrawing is not installed in that case. The order is generation, face restoration, final upscaling.
- In candidate mode, always (`always`) follows the spare candidate finishing value in force (`spare_finish_resolved`). With `adopted`, apply it to adopted images only. With `all`, apply it once to every candidate.
- Off (`off`): do not install the face restoration dependencies. Handle face defects with stages 1, 2, and 4. Off covers face restoration only, so region redrawing of clothing, accessories, and precise objects still follows the defect post-processing policy.

For non-photographic styles (flat vector, line art, cel shading and so on), mark off as recommended in the questions. Face restoration tools were trained on real photographs of faces, so only the restored area becomes photographic and does not match painted hair. If the user nevertheless selected restoration in such a style, present before and after side by side and ask whether to adopt, even in automatic mode and in always-on scope. In candidate mode, compare adopted images only. Without a display path, select the version that suits the style yourself and give a one-line reason on delivery (display path judgment in the delivery section of SKILL.md).

When face restoration is applied to a face whose angle the visual check judged as a three-quarter view or profile (a non-frontal face), compare the original and the restored image by the same visual check criteria and adopt the one with fewer defects. Face restoration tools were trained mostly on frontal face photographs and align faces to a frontal reference before restoring them, so a non-frontal face can come out with unnatural features or texture errors. If both show the same defects, adopt the restored image, whose pupils and teeth are sharper. If the original is adopted, use it in place of the restored image in all later steps. Under every answer, including automatic mode and always-on scope, make this comparison yourself without asking the user. Three-quarter views are a common face angle, so asking at each comparison would often interrupt automatic progress. In non-photographic styles, the before-and-after question above takes the place of this comparison. Record the comparison result and the reason for the choice in one line in the adoption record.

Outputs where no face is detected (back views, distant figures) are saved with the same pixels as the input. Use them as normal outputs.

## Using face restoration

GFPGAN v1.3 restores sharp pupils and lashes. On faces with misplaced eyes it follows the original, so part of the asymmetry remains. Areas outside the face, and hands, remain as in the original.

```
PY scripts/face_fix.py in.png out_face.png
```

- If distortion remains after GFPGAN, redraw the face box with region redrawing. Apply it once in this case too and compare before and after.
- The weights download from a GitHub release on first use and are checked by SHA-256. facexlib downloads its helper models (face detection and face parsing) into the cache folder.

## Region redrawing

If the whole image is satisfactory except for one defect, redraw only that part. Examples: a broken glasses frame, a missing strap, tangled bicycle spokes.

- Extending: fixes that continue an existing shape, such as a broken frame or a strap that vanishes halfway, use strength 0.65. At 0.85 the shape is drawn over itself and the result deteriorates.
- Covering: fixes that put another material over skin, such as covering exposed skin with fabric or lengthening a short sleeve, use strength 1.0. Lower strengths follow the original colors and the material does not change.
- Fixing a distorted face starts at strength 0.65. Fit the box to the face outline and exclude hair where possible. Hair and lighting inside the box are redrawn too and can change color from the original.
- Measure box coordinates with the grid from grid_measure.py. For extending, keep the box tight around the defect. For covering, make it wide enough to show the fabric to continue on both sides.
- Parts attached inside the box (a mudguard, an object in a hand) disappear, so exclude them from the box.
- Describe only the desired result in the prompt, for example `thin gold metal sunglasses frame, round lens rim continuing into a straight temple arm, photorealistic`. Do not name what should be removed.
- The model input is a square no larger than the image's short side. If the box is longer than that on a wide trimmed image, region_fix.py stops with `BOX_TOO_LARGE`. Split the box and run each part.

```
PY scripts/region_fix.py in.png out_region.png 387,173,460,267 "thin gold metal sunglasses frame, round lens rim continuing into a straight temple arm, photorealistic" 42           # extending, default strength 0.65
PY scripts/region_fix.py in.png out_region.png 313,260,377,347 "white cotton t-shirt sleeve fabric covering the upper arm, soft fabric folds, photorealistic" 42 1.0      # covering
PY scripts/region_fix.py in.png out_region.png 117,167,227,267 "a natural open human hand with five fingers, palm facing the camera, photorealistic" 42 0.85          # fingers, when selected
```

## Finger redrawing

For requests with a person where the defect policy is automatic or ask each time, the same questions ask whether to use it. The recommendation is off, and the question states that it is rarely effective before listing the choices. In one case with a single open hand, the finger count was corrected but the hand's size and pose changed from the original.

- Even when selected, exhaust stage 1 seed changes, edge trimming, and stage 2 workarounds first. Then apply it once at stage 3.
- If the defect remains, do not repeat it with other strengths or seeds. Go to the stage 4 composition workaround.
- Hand size and pose can change significantly, so even in automatic mode present before and after side by side and ask whether to adopt. This comparison is required, so without a display path remove the on choice from the pre-generation questions (display path judgment in the delivery section of SKILL.md).
- In candidate mode, apply it only to adopted candidates.
- It applies to isolated hands that overlap nothing. A hand holding an object, or two overlapping hands, would lose the object inside the box, so exclude them even when the user selected this tool.
- The strength is 0.85. At 0.65 the wrong finger count stays, and at 1.0 the whole hand changes into another pose and no longer connects to the arm.
- Set the box from the fingertips to just before the wrist. Describe the desired result in the prompt.

## Checking and recording

- Open the post-processed result next to the original and check that the defect is resolved, that the texture at the boundary matches, and that the style has not changed. Then adopt it.
- The strengths and settings in the scripts are recommended values. If you change one, record the new value and the reason in the adoption record.
- Add the defect post-processing policy, face restoration scope, finger redrawing choice, tool, strength, box coordinates, and seed to the adoption record.

## Installation

Install only when post-processing is selected, and before any other post-processing work.

```
PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu gfpgan   # face restoration
PY scripts/patch_basicsr.py                                                                      # once, right after installing
```

- Region redrawing uses the same packages as generation (diffusers, transformers, accelerate, peft, huggingface_hub), so no extra installation is needed. Only the model is downloaded on first use.
- Pass the CPU index with `--extra-index-url` when installing the face restoration packages. basicsr builds from source during installation and downloads torch again into a separate build environment. Without the index it downloads a CUDA build of torch and related packages totaling several GB, which can exhaust the disk. The same option keeps the torchvision that gfpgan requires on the CPU build.
- patch_basicsr.py replaces a module path that torchvision removed, only inside the basicsr package. It modifies no other package.
- If the gfpgan install fails with `KeyError: '__version__'`, the version reader in basicsr's setup.py is at fault (seen on Python 3.13 with basicsr 1.4.2). Apply the steps below only in that case.
  - `pip download` runs the same setup.py, so download the basicsr source archive (.tar.gz) directly from PyPI. `https://pypi.org/pypi/basicsr/json` lists its URL. Extract it into a temporary folder.
  - In `get_version()` of setup.py, pass a new empty dict to `exec` as its globals, and read `__version__` from that dict instead of `locals()`.
  - Install from the extracted folder with `PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu <folder>`, then run the gfpgan install again.
  - Delete the temporary folder afterwards.
  - If the install still fails, try once more with an earlier Python (3.12 or 3.11, both confirmed to install). Recreating the virtual environment deletes it, so ask the user first. If no earlier Python exists or the install fails again, disable face restoration and inform the user.

## Cleanup

If post-processing is no longer needed, delete its caches.

```
PY scripts/cache.py delete face
PY scripts/cache.py delete inpaint
```

To remove the packages as well, run `PY -m pip uninstall gfpgan basicsr facexlib`. Only packages inside the virtual environment are removed.

## Validation

After upgrading a tool or package, produce defects intentionally with the prompts below, apply the tool, and compare before and after. Defects differ between model and package versions even with the same prompt and seed, so if no defect appears, change the seed until you find a sample with one.

| Tool to check | Prompt | Check for |
|---|---|---|
| Face restoration (distortion) | a businessman pointing his finger toward the camera, arm extended forward, waist up shot, office at night, photorealistic | Less asymmetry with the look preserved |
| Face restoration (blur) | a young woman smiling, waist up portrait, office daylight, photorealistic | Sharper pupils and teeth |
| Face restoration (non-frontal) | a middle aged man in three quarter view, waist up portrait, city street daylight, photorealistic | Whether the features shift toward a frontal look, texture errors |
| Small faces and hands | a construction worker in a safety vest holding a power drill, building site, full body, hands visible, photorealistic | Whether a small face gets restored, the hands and the tool |
| Broken limb connections | a gymnast in a handstand pose, one leg extended, gymnasium floor, full body, hands and feet visible, photorealistic | Confirms a defect post-processing cannot fix |
| Finger redrawing | a woman waving her open hand at the camera, waist up, bare hands visible, park daylight, photorealistic | Finger count, changes in hand size and pose |
| Extending | close up portrait of a woman wearing thin metal frame sunglasses, three quarter view, daylight street, photorealistic | The broken frame joins without being drawn twice |
| Covering | a young woman in a plain white t-shirt standing on a daylight street, waist up, photorealistic | The sleeve extends as fabric, visible seams |
| Precise objects | a bicycle leaning against a brick wall, side view, full wheels visible, daylight, photorealistic | Rims and spokes are rendered cleanly |
