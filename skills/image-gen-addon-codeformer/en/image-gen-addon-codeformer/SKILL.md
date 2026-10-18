---
name: image-gen-addon-codeformer
description: "Add-on that brings CodeFormer into the face restoration of the image-gen skill. If installed, it adds a face restoration strength item to image-gen's pre-generation questions and changes image-gen's face restoration so that asymmetric faces and misplaced features get fixed with CodeFormer. Whenever the image-gen skill makes an image with a person, or restores, fixes, or corrects a face, and this add-on is installed, always load it together with image-gen. It does nothing without the image-gen skill. CodeFormer is distributed under a license that allows non-commercial use only (S-Lab License 1.0), so get the user's consent before installing it."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE.md
---

# image-gen add-on: CodeFormer face restoration

> This English edition is a translation of the Korean original. Its behavior may differ from what the original intends.

This add-on extends the face restoration of the image-gen skill. image-gen sharpens soft faces with GFPGAN, but faces with misplaced eyes or left-right asymmetry follow the original and keep part of the defect. CodeFormer rebuilds the face from a learned dictionary of face parts (a codebook), so it also fixes asymmetry and misplaced features. A lower fidelity weight w gives a stronger symmetry fix, and a higher one keeps more of the original look.

If loaded together with image-gen, the rules below replace the matching rules of image-gen. Rules not mentioned here follow image-gen unchanged.

## Terms of use

CodeFormer is distributed under the S-Lab License 1.0. The license allows use and redistribution for non-commercial purposes only and asks anyone with a commercial purpose to contact the authors. Before the first installation, tell the user this condition in one line and ask whether to install. If the user declines or says the purpose is commercial, skip this add-on and continue with image-gen alone.

- License text: https://github.com/sczhou/CodeFormer/blob/master/LICENSE
- Package: codeformer-pip (https://github.com/kadirnar/codeformer-pip), which states the same license.

## Changed rules

### Pre-generation questions

Insert a face restoration strength item right after image-gen's face restoration scope item. The items after it move down by one number.

- Ask when a person appears and face restoration can run. Do not ask when face restoration scope is off. Do not ask when the scope is "only on defects" and defect post-processing is "workarounds only", because restoration never runs in that combination.
- If the user already stated the strength, do not ask.
- In the recommended combination for delegated answers, the recommendation for this item is stepwise.

Example (insert after item 4 of image-gen's example):

> 5. [Face restoration strength] Only when item 4 is not c, and items 3-b and 4-a are not both chosen.
>    a) Aggressive: fix in one pass with w=0.0 from the start. The look of the face may change from the original
>    b) Stepwise: start at w=0.5 and lower to 0.25, then 0.0, while a defect remains

After the user answers, run this add-on's record script right after image-gen's preflight.py. Run it again whenever image-gen's record is rewritten.

```
PY scripts/preflight_codeformer.py --out ./outputs --face-strength stepwise --user-reply "1-b, 2-c, 3-a, 4-b, 5-b, 6-a"
```

- `scripts/` is the scripts folder inside this add-on's folder. `PY` is the Python of image-gen's virtual environment.
- If the combination needs no strength item, run it without `--face-strength` to record an empty value.

### Choosing the face tool

| Face defect | image-gen alone | With this add-on |
|---|---|---|
| Blur (pupils, lashes, teeth) | GFPGAN | GFPGAN |
| Distortion (asymmetry, misplaced features) | GFPGAN, then region redrawing if it remains | CodeFormer (strength per the face restoration strength answer), then region redrawing if it remains |
| Always-on scope | GFPGAN | CodeFormer. w=0.5 when no defect shows, the starting value of the strength answer when a defect shows |

- Stepwise starts at w=0.5 and lowers to 0.25, then 0.0, while a defect remains. A lower w changes the original look more, but fixing the defect comes first, so never leave a defect in place.
- At w=0.0 the face can look like a different person. If the same person appears in several images, compare them.
- CodeFormer shares the problem of restored faces turning photographic in non-photographic styles. Follow image-gen's rule: show before and after side by side and ask whether to adopt.
- On a face that has fallen apart, CodeFormer can fail to rebuild it and change only the texture. If the defect remains even at w=0.0, move on to image-gen's region redrawing.
- Areas outside the face, and hands, stay as in the original. Hand defects are not fixed.

```
PY scripts/face_fix_codeformer.py in.png out_face.png 0.5
```

- The package saves inputs with a short side under 512px at an enlarged size, so the script resizes the result back to the input size. Trimmed working images keep their size and grid coordinates before and after restoration.
- Add the face restoration strength policy and the w used to the adoption record.
- Exit codes follow image-gen's failure table: 2 for an argument error or a missing input file, 4 when codeformer-pip is not installed.

### Installation

If face restoration is chosen and the user has agreed to the terms of use, install right after image-gen's face restoration install.

```
PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu codeformer-pip
PY <image-gen folder>/scripts/patch_basicsr.py
```

- The CPU index is passed for the same reason as in image-gen's face restoration install.
- If image-gen's face restoration cannot be installed, skip this add-on too.
- On import, codeformer-pip downloads weights (about 0.6GB) under the current folder and writes results to `output/out.png`. Its face helper would also download the detection and parsing weights again into the package's install folder. face_fix_codeformer.py moves into a `codeformer` folder inside image-gen's cache folder and points the face helper at the same folder before importing it. All weights stay in that one folder, and no files appear in the user's folders, the skill folder, or the virtual environment.
- The weights come from the releases of the GitHub repository `sczhou/CodeFormer`. If the execution environment has a tool that attaches a GitHub repository to the session, call it before the first run. Pass the owner `sczhou` and the repository name `CodeFormer` as separate values. Follow any access route the tool's reply names. Skip this step when no such tool exists or the call is refused.

### Cleanup

```
PY scripts/face_fix_codeformer.py --cleanup
PY -m pip uninstall codeformer-pip
```

- `--cleanup` deletes only the `codeformer` folder inside image-gen's cache folder. image-gen's `cache.py delete all` also deletes that folder.
