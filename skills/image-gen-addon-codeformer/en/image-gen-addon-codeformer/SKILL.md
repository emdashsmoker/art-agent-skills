---
name: image-gen-addon-codeformer
description: "Add-on that adds CodeFormer to the face restoration of the image-gen skill. If installed, it adds a face restoration strength item to image-gen's pre-generation questions and changes image-gen's face restoration so that asymmetric faces and misplaced features are corrected with CodeFormer. Whenever the image-gen skill generates an image with a person, or restores, fixes, or corrects a face, and this add-on is installed, always load it together with image-gen. It does not function without the image-gen skill. CodeFormer is distributed under a license that allows non-commercial use only (S-Lab License 1.0), so obtain the user's consent in the pre-generation questions."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE.md
---

# image-gen add-on: CodeFormer face restoration

> This English edition is a translation of the Korean original. Its behavior may differ from what the original intends.

This add-on extends the face restoration of the image-gen skill. image-gen sharpens blurry faces with GFPGAN, but faces with misplaced eyes or left-right asymmetry follow the original and retain part of the defect. CodeFormer reconstructs the face from a learned dictionary of face parts (a codebook), so it also corrects asymmetry judged as a defect and misplaced features. A lower fidelity weight w makes the reconstruction rely more on the dictionary of face parts and gives a stronger correction, and a higher one preserves more of the original look.

If loaded together with image-gen, the rules below replace the matching rules of image-gen. Rules not mentioned here follow image-gen unchanged.

## Terms of use

CodeFormer is distributed under the S-Lab License 1.0. The license allows use and redistribution for non-commercial purposes only and requires anyone with a commercial purpose to contact the authors. Include this condition as one line in the pre-generation questions and obtain consent in the same answer (pre-generation questions section). image-gen completes all questions before generation so that automatic progress is not interrupted, so do not ask again at installation time. If the user declines or states that the purpose is commercial, do not use this add-on and continue with image-gen alone.

- License text: https://github.com/sczhou/CodeFormer/blob/master/LICENSE
- Package: codeformer-pip (https://github.com/kadirnar/codeformer-pip), which states the same license.

## Changed rules

### Pre-generation questions

Insert a face restoration strength item right after image-gen's face restoration scope item. The numbers of the following items increase by one. Item numbers cited in the conditions of other items are adjusted in the same way (for example, candidate selection's "Only if item 6 is not a" becomes "Only if item 7 is not a").

- Ask when a person appears and face restoration can run. Do not ask when face restoration scope is off. Do not ask when the scope is "only on defects" and defect post-processing is "workarounds only", because restoration does not run in that combination.
- Add the one-line terms of use to this item's description. Selecting a or b counts as consent. c) Do not use is the choice for users who decline or have a commercial purpose.
- If the user already stated the strength, do not ask for the strength. Still present the one-line terms of use and confirm consent in the same questions.
- In the recommended combination for delegated answers, the recommendation for this item is stepwise. Write the other numbers of the combination with the adjusted numbers as well. For example, image-gen's "1-b, 2-b, 3-a, 4-a, 5-a, 6-a, 9-a, 10-a" becomes "1-b, 2-b, 3-a, 4-a, 5-b, 6-a, 7-a, 10-a, 11-a". When presenting the recommended combination, include the one-line terms of use and obtain consent in the same confirmation.

Example (insert after item 4 of image-gen's example):

> 5. [Face restoration strength] Only when item 4 is not c, and items 3-b and 4-a are not both chosen. For a person whose face is turned at an angle or to the side, either strength uses w=0.5. CodeFormer, which corrects asymmetric faces, is distributed under a license that allows non-commercial use only (S-Lab License 1.0). Selecting a or b indicates that you agree to this condition.
>    a) Aggressive: corrects in one pass with w=0.0 from the start. The look of the face may change from the original
>    b) Stepwise: starts at w=0.5 and lowers to 0.25, then 0.0, while a defect remains
>    c) Do not use: select this for a commercial purpose or if you do not agree. Face restoration continues with the default tool

After the user answers, run this add-on's record script right after image-gen's preflight.py. Run it again whenever image-gen's record is rewritten.

```
PY scripts/preflight_codeformer.py --out ./outputs --face-strength stepwise --user-reply "1-b, 2-c, 3-a, 4-b, 5-b, 6-a, 7-d, 8-b, 9-c, 10-a, 11-a"
```

- `scripts/` is the scripts folder inside this add-on's folder. `PY` is the Python of image-gen's virtual environment.
- If the combination needs no strength item, run it without `--face-strength` to record an empty value.
- If the user selects c) Do not use or states that the purpose is commercial, do not run the record script. From then on, do not use this add-on and continue with image-gen alone. image-gen's generation scripts work without this add-on's record.

### Choosing the face tool

| Face defect | image-gen alone | With this add-on |
|---|---|---|
| Blur (pupils, lashes, teeth) | GFPGAN | GFPGAN |
| Distortion (asymmetry, misplaced features) | GFPGAN, then region redrawing if it remains | CodeFormer (strength per the face restoration strength answer), then region redrawing if it remains |
| Always-on scope | GFPGAN | CodeFormer. w=0.5 when no defect is visible, the starting value of the strength answer when a defect is visible |

- To choose w for the always-on scope, examine the angle of the face and any defect in the generated original before restoration. The face defect judgment after restoration follows image-gen's rules.
- Stepwise starts at w=0.5 and lowers to 0.25, then 0.0, while a defect remains. A lower w changes the original look more, but resolving the defect takes priority.
- Restoring again with a lower w is a defect repair in image-gen's stage 3. In candidate mode, restore again with a lower w on adopted images only. Follow image-gen's stage 3 rules as they are, including the defect post-processing answer. With defect post-processing set to workarounds only, do not lower w, and proceed to image-gen's stages 2 and 4.
- When restoring again with a lower w, do not apply it to an image that was already restored. A result restored again from a restored image cannot be reproduced from the recorded w.
- At w=0.0 the face can look like a different person. If the same person appears in several images, compare them.
- CodeFormer has the same problem of restored faces becoming photographic in non-photographic styles. Follow image-gen's rules for non-photographic styles as they are, such as the before-and-after comparison, the direct choice without a display path, and comparing only the adopted image in candidate mode.
- CodeFormer has the same problem of non-frontal faces coming out with unnatural features or texture errors after restoration. Follow image-gen's non-frontal face rule as it is, such as the comparison of the original and the restored image, adopting the one with fewer defects, and judging without asking the user.
- For a non-frontal face (a face in a three-quarter view or profile), do not lower w below 0.5. Use w=0.5 even when the face restoration strength is aggressive, and if a defect remains at w=0.5, proceed to image-gen's next response stages (region redrawing, composition workaround, and the like). At w=0.0, CodeFormer rebuilds the face only from the dictionary of face parts, learned mostly from frontal photographs, without the features of the input face. CodeFormer's path has a face detection confidence threshold of 0.8, so it restores more ambiguous faces than image-gen's GFPGAN path (0.97).
- Exclude the natural asymmetry that a face angle creates (such as the far eye looking narrower) from correction, and do not treat it as a defect when choosing or lowering w. image-gen's definition of a shape problem does not count differences that the angle of the face explains as defects.
- On a severely broken face, CodeFormer may fail to reconstruct it and change only the texture. If the defect remains even at w=0.0, proceed to image-gen's region redrawing.
- Areas outside the face, and hands, remain as in the original. Hand defects are not corrected.

```
PY scripts/face_fix_codeformer.py in.png out_face.png 0.5
```

- The package saves inputs with a short side under 512px at an enlarged size, so the script resizes the result back to the input size. Trimmed working images keep their size and grid coordinates before and after restoration.
- Add the face restoration strength policy and the w used to the adoption record.
- Exit codes follow image-gen's failure table: 2 for an argument error or a missing input file, 4 when codeformer-pip is not installed.

### Installation

If face restoration is selected and the user agreed to the terms of use in the pre-generation questions, install right after image-gen's face restoration install.

```
PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu codeformer-pip
PY <image-gen folder>/scripts/patch_basicsr.py
```

- The CPU index is passed for the same reason as in image-gen's face restoration install.
- If image-gen's face restoration cannot be installed, skip this add-on too.
- On import, codeformer-pip downloads weights (about 0.6GB) under the current folder and writes results to `output/out.png`. Its face helper would also download the detection and parsing weights again into the package's install folder. face_fix_codeformer.py changes its working folder to a `codeformer` folder inside image-gen's cache folder and points the face helper to the same folder before importing it. All weights are stored in that one folder, and no files are created in the user's folders, the skill folder, or the virtual environment.
- The weights are downloaded from the releases of the GitHub repository `sczhou/CodeFormer`. If the runtime environment has a tool that attaches a GitHub repository to the session, call it before the first run. Pass the owner `sczhou` and the repository name `CodeFormer` as separate values. Follow any access route the tool's reply specifies. Skip this step when no such tool exists or the call is refused.

### Cleanup

```
PY scripts/face_fix_codeformer.py --cleanup
PY -m pip uninstall codeformer-pip
```

- `--cleanup` deletes only the `codeformer` folder inside image-gen's cache folder. image-gen's `cache.py delete all` also deletes that folder.
