# Defect checks and responses

Details for the defect handling section of SKILL.md. Read this when you find a defect in an output. postprocess.md covers the post-processing tools.

## Trim-first check

If you find a defect, answer these two questions before regenerating or trying a workaround.

- Does the defect touch or come close to one of the four edges of the frame?
- Setting that defect aside, is there no other reason to redo the subject, style, color, or framing?

If both answers are yes, act on the `trim` value in preflight.json. With `same`, `free`, or `free-auto`, run edge trimming before regenerating. With `off`, continue with the normal response stages. People differ on how much cropping or ratio change they accept, so the `trim` value is the only criterion.

Trimming goes first because regenerating throws away the framing and expression you liked. A trim takes seconds and does not count toward the regeneration limit. The defect pixels leave the frame, so the fix is certain. Anatomical defects, extra objects, and duplicated subjects get fixed by regenerating or redrawing only by chance.

- Examples: anatomical errors such as the number or shape of fingers, toes, and limbs, more objects than intended, the same subject twice, small warped shapes, cut-off limbs, fake signatures, frames or borders caught at the edge.
- Defects not on this list get the same treatment if trimming the edge can push them out of the frame. Whether trimming works is decided by running edge_trim.py.
- If edge_trim.py ends with `NOT_APPLICABLE`, consider the free-ratio track when `trim` is `free` or `free-auto`. With `same`, return to the normal response stages.
- If you present the best result after hitting the regeneration limit, apply this check to that result once before presenting it.

## General defects

Defects outside the fragile subjects (next section) go down one of two paths. If an instruction in the prompt does not show up, fix the prompt. If it shows up but the placement or decoration is not what you want, change the seed.

| Defect | Response |
|---|---|
| Style not applied | Move the style phrase to the front. Replace abstract style words with a technique name |
| Wrong color | Name the color family, for example `muted blue and beige palette` |
| More objects than asked | Put the count up front, for example `a single` |
| Objects nobody asked for | List only the objects that should appear and shorten the description |
| In a scene, a person nobody asked for takes the center | Change the style to a technique name such as `watercolor illustration` or `flat vector illustration`. If the person stays, try two more seeds. If the person still stays, change the element combination |
| Paper texture or a cropped rectangle creeps in | End the prompt with `plain background`. A seed change has the stronger effect, so change it too |
| Halo or circular decoration in the background | Change the seed |
| Framing or subject position not right | Change the seed |
| Warped shapes | Change the seed. If it repeats, drop secondary elements and simplify the description |
| Water reflections or grid patterns go wrong | Change the seed. If it repeats, remove reflection and grid elements from the prompt |

- A person that belongs to the request, or a small figure mixed into the background, is not an unrequested-person defect. Abstract style words in scene prompts can read as a photographic portrait, which causes this defect.
- Change one thing in the prompt at a time, so you can tell which change worked.
- If the same defect remains after up to three prompt edits and up to three seed changes, keep the chosen model and respond by request type.
- When the multiplier in force is 2 or more, add the number of moves to the next candidate in the pool to the count of seed changes, because every candidate has its own seed. For example, if all three candidates of a 3x pool show the same defect, count two seed changes as used and regenerate only once more.
- For message requests and diagram requests, go back to the original message and choose another stand-in. A seed change only rearranges the same metaphor, so repeating it does nothing when the metaphor is wrong.
- For named-subject requests, keep the subject, show the best result with its defects, and ask how to proceed.
- For scene requests that went through no substitution, change the element combination.
- If the same defect remains after changing the stand-in or the element combination, show the best result with its defects and ask how to proceed.
- Offer a model change only as an option, following the model lock section of SKILL.md.
- Record the prompt and seed of the adopted result.

## Fragile subjects

These are people, animals, precise objects, and background crowds. Diffusion models cannot control facial features, the number of limbs, fingers, or how parts connect, so run the procedure on the assumption that defects will occur. A person nobody asked for follows the general defect table above.

Face defects include mushy faces and also unclear features, eyes, nose, or mouth out of place or out of proportion, left-right asymmetry, mismatched gaze or pupils, and broken mouths and teeth. If unsure, treat it as a defect and start the procedure. If it still looks off at the size it will be used, the defect is confirmed. Slight blur on a distant figure is not a defect.

Respond in this order.

1. Stage 1, try again: keep the prompt, change only the seed, and regenerate with the original intent.
2. Stage 2, prompt workaround: add an instruction that hides or avoids the defective part.
3. Stage 3, post-processing: redraw only the defective part with face restoration or region redrawing (postprocess.md).
4. Stage 4, composition workaround: change the camera shot, framing, or scene layout.

Enter a stage only when the same defect remains after the previous stage has used all its attempts. Never skip stage 1 to go straight to stage 2 or later. Workarounds give up part of the original intent, such as a bare face, a natural pose, or the original scene. Seed changes alone often fix the defect, so use the free option first.

When the multiplier in force is 2 or more, swapping within the candidate pool replaces stage 1. The candidates are stage 1's seed changes made ahead of time, at generation. When too few candidates can be adopted or an adopted candidate has to be replaced, swap in a remaining candidate. Once the pool runs out, go to stage 2 without a stage 1 regeneration. A candidate adopted at rank 3 of the adoption order in SKILL.md goes straight to stage 3 post-processing without stage 2. The pool has already shown it holds no better candidate, and post-processing keeps the original intent.

Edge trimming needs no installation and loses almost nothing of the original intent, so run it first at any stage. It applies when the defect touches or comes close to an edge, and the trim-first check decides whether to run it.

The answers in preflight.json decide whether to enter stage 3.

- With `postfix` set to `auto`, enter without asking. With `bypass`, skip stage 3. With `ask`, ask about the tool and whether to proceed each time.
- With `face_scope` set to `off`, face defects skip stage 3 and go to stage 4 once stage 2 is used up.
- Finger defects enter stage 3 only when `finger_inpaint` is `on`. With `off`, they go to stage 4 once stage 2 is used up.
- With `face_scope` set to `always`, face restoration runs right after generation as the default step, and face defects are judged on the restored image.
- In candidate mode, `always` follows `spare_finish_resolved`. With `adopted`, judge the originals to adopt, restore only the adopted images, and judge them on the restored versions. With `all`, restore every candidate once and judge on the restored images.

### Regeneration limit

By default each stage allows one regeneration. If the limit is reached, stop regenerating.

| Preset | Stage 1 | Stage 2 | Stage 4 | Total | Total with 2x or more candidates |
|---|---|---|---|---|---|
| Light | 1 | 2 | 1 | 4 | 3 |
| Standard, Flat | 1 | 1 | 1 | 3 | 2 |
| Precise | 1 | 0 | 0 | 1 | 0 |

- When the multiplier in force is 2 or more, swapping within the candidate pool replaces stage 1, so stage 1 has no regeneration. The last column is the total in that case. A pool swap picks an image that already exists, so it does not count as a regeneration.
- Light makes images fast, so it gets one extra round of trial and error for choosing a workaround. The second stage-2 attempt must use a different workaround from the first. Changing only the seed with the same workaround counts as stage 1, not stage 2.
- Precise takes the longest per image, so one regeneration reaches the limit.
- Stage 3 post-processing fixes part of an existing output and does not count as a regeneration. Apply each tool once and compare.
- At the limit, show the best result with the defect marked and ask how to proceed. Without a display path, describe the defect location in words (display path judgment in the delivery section of SKILL.md). The choices are: adopt the best result, try again with a workaround the user picks, switch to a scene without people or an object icon, or change the model (with its download size and estimated time).

### Workarounds

The table holds examples. If another option fits the theme, time of day, or style of the scene better, adapt it on the same principle: hide or avoid the defective part. Scarves and knit hats in a winter scene, a helmet in a space scene, a wide-brimmed hat and sunglasses on a beach, and a hard hat on a construction site all follow that principle.

| Defect | Stage 2 prompt workaround | Stage 4 composition workaround |
|---|---|---|
| Face defect | Closed eyes (`eyes closed`), a hat or hood, helmet, visor, sunglasses, a simple expression (`neutral expression`) | Side or back view, an upper-body close-up that makes the face larger |
| Wrong number of limbs | (Trim first if it touches an edge) a simple pose (`standing, arms at sides`), a coat or cape | An upper-body shot that leaves the legs out of the frame |
| Warped fingers or toes | (Trim first if it touches an edge) gloves, `hands in pockets`, long sleeves, holding a prop | A shot that leaves hands and feet out of the frame |
| Warped animal limbs or face | A sitting pose (`sitting`) | A side silhouette |
| Tangled parts on a precise object | Render as a silhouette | Swap in an object with a simple outline |
| Mushy faces in a background crowd | Crowd silhouettes (`silhouettes of people in the distance`) | Remove the crowd and keep the main subject alone |

- Face defects get worse the fewer pixels the face occupies. The two directions are covering part of the face (helmet, visor, sunglasses, hat) and enlarging the face (close-up). Covering part of it keeps some features and hides only the weak spots, so it looks less out of place.
- Closed eyes help when mismatched gaze or pupils are the main defect. Use them only where closed eyes look natural, such as rest, meditation, or listening to music.
- Turning the main person into a backlit silhouette gives up the facial features, so use it only as the last attempt within the limit. Silhouettes look natural for distant figures and background crowds, so this restriction does not apply to them.
- Add one workaround at a time, so you can tell what caused the effect.
- Check that the adopted workaround (accessory, clothing, framing) fits the scene's time of day, color, and original message before using it.
- Record the stage, seed, and prompt of every attempt to track which stages are used up. Record the adopted result the same way.

## Edge trimming

If a defect sits at an edge, cut that edge as little as possible to push the defect out of the frame. The typical case is a finger caught at the bottom. The cut pixels are gone, so the fix is certain for anatomical and object defects alike. It cannot help when the defect is in the middle of the frame. It uses only Pillow and takes seconds.

- The order is generation (already cropped to the target ratio), edge trimming, then final upscaling.
- In candidate mode, trim only the defects of adopted candidates. Spares are not trimmed even when they have defects.
- If final upscaling is chosen, save with `--no-resize` and skip enlarging. finalize.py produces the target size. If final upscaling is off, run without that option to enlarge back to the original size. The enlargement lowers sharpness by the same factor.

### Measuring coordinates

Read the defect box `x0,y0,x1,y1` from the coordinate grid drawn by grid_measure.py. Guessing coordinates by eye is error-prone, and a trim meant for a finger can spread to the waist or thighs.

- The grid image draws an enlarged copy, so read coordinates from the numbers on the grid lines.
- Look at the full-frame grid first, then at an enlarged grid around the defect. Make the second region generous enough to show nearby parts such as the wrist or elbow.
- Detection models are not used for measuring. They take minutes to install and load, and their boxes cover the whole body part, which makes the cut larger.
- Put only the defect in the defect box. For a finger defect, go from the fingertip to just before the wrist. The cut line adds only a 4px margin to the box edge, so a wide box cuts healthy parts by the same amount.
- For defects on the same edge, repeat `--defect`. Run defects on different edges one run at a time.

### Cut window

edge_trim.py computes, for each of the four edges, the largest window that excludes the defect, and keeps the edge that leaves the most area. The cut depth comes from the measured defect box, so a shallow defect gets a shallow cut and a deep one a deep cut. With a keep box in `--keep`, the window is placed so that it contains that box.

### Same-ratio track

This is the default track. The window keeps the original aspect ratio and is resized back to the original size. The output format does not change, so always try this track first.

- It needs `--keep`. Give a union box around everything the original request must keep. For a person, that is the face, the requested shot range, and props named in the request. For an object, it is the whole subject.
- A box around the head alone still passes when a head-to-thigh shot turns into an upper-body shot. Include the shot range in the keep box to prevent that.
- If the window cannot contain the keep box, the script ends with `NOT_APPLICABLE`.
- Change the 4px margin with `--pad`. Pass `--max-ratio` only when a separate cap on the cut ratio is needed.
- Use the cut ratio and enlargement factor printed by the script as they are.
- The pre-generation answer already allowed it, so adopt the result without asking, and on delivery report the trim, the body part the cut line crosses, and the cut ratio.

### Free-ratio track

Use it with `--ratio`. The window ratio is released, so only the defect's edge is cut deep and the other direction stays wide. A same-ratio window shrinks the other direction by as much as it cuts, so even a defect of modest depth leaves no room for the head or other kept parts. Releasing the ratio can save the same picture as, for example, a wider frame. A window that keeps the whole other direction has an enlargement factor of 1.0 and stays sharper than the same-ratio track.

- Entry conditions: `trim` is `free` or `free-auto`, and the same-ratio track ended with `NOT_APPLICABLE` or its preview shows the cut line crossing the head or another kept part. With `same`, skip this track.
- If the conditions hold, consider this track before discarding the picture and moving to the next response stage.
- Candidates: run `--ratio free` (the maximum-keep window that cuts only the defect's edge) and one or two standard ratios that suit where the image will go (16:9, 3:2, 4:3, 1:1, 3:4 and so on), each with a preview. If a person appears, give a keep box that includes the head in `--keep`. Without a keep box, the window sticks to the top.
- The restored size keeps the window ratio with its long side matched to the input's long side. Change it with `--long-side`. The script prints it as `target=WxH`. If final upscaling is chosen, run with `--no-resize` and pass the printed target to finalize.py's `--size` unchanged.

Build candidates to find the window closest to the staging and framing of the original request. Releasing the ratio means composing anew, so a window that only avoids the defect can turn into a different picture without the requested shot, props, or background. Before running candidates, list what the original request must keep: the shot range (for example head to thigh), the subject's position in the frame and the space in the direction of the gaze, the props and background elements named in the request, and where the image will go.

- There is one keep box, so measure a union box that holds the head and the props together. The window is centered on the keep box. If the subject sat off to one side or had space in the direction of the gaze, widen the keep box toward that space to preserve the same balance.
- For each candidate, report what stays and what is lost compared with the original request, the remaining area (`area_kept`), the enlargement factor (`upscale`), and the body part the cut line crosses. The wider the ratio, the higher the cut line and the more the shot changes (for example a head-to-thigh shot becomes an upper-body shot at 16:9).
- Mark the candidate closest to the original intent as recommended. `free` tends to keep the most of the shot range.
- With `free`: even though the answer allowed it, always show the candidate previews and confirm with the ratio the user picks. The aspect ratio decides where the image fits, so the user chooses. The user can also specify another ratio as W:H, in which case you run again and show a new preview. Never drop candidates by a loss cap without showing them.
- With `free-auto`: open and compare all candidate previews, pick one yourself, and adopt it without asking. Pick the candidate that keeps the most of the original shot range, subject position and gaze space, props and background elements, and fit for where the image goes. If candidates tie, pick the standard ratio that suits where the image goes. Never pick a candidate that leaves the defect in the frame or whose cut line crosses the face. On delivery, report the trim, the adopted ratio, a one-line reason, the remaining area, the body part the cut line crosses, and what was lost. If the user wants another ratio, rerun on the same working image with the ratio they give.
- If neither track fits, or the user rejects every candidate, drop the trim and continue with the normal response stages.

```
PY scripts/grid_measure.py in.png grid.png                        # full-frame grid
PY scripts/grid_measure.py in.png grid_zoom.png 100,373,300,512   # enlarged grid around the defect
PY scripts/edge_trim.py in.png out_trim.png --defect 155,461,177,507 --keep 200,40,320,500 --preview trim_preview.png
PY scripts/edge_trim.py in.png out_trim.png --defect 155,461,177,507 --keep 200,40,320,500 --no-resize --preview trim_preview.png   # with final upscaling
PY scripts/edge_trim.py in.png out_free.png --defect 140,340,205,430 --keep 215,30,305,330 --ratio free --preview free_preview.png   # free ratio, maximum-keep window
PY scripts/edge_trim.py in.png out_wide.png --defect 140,340,205,430 --keep 215,30,305,330 --ratio 16:9 --preview wide_preview.png   # free ratio, standard-ratio candidate
PY scripts/edge_trim.py in.png out_wide.png --defect 140,340,205,430 --keep 215,30,305,330 --ratio 16:9 --no-resize --long-side 1024   # with final upscaling, pass the printed target to finalize.py
```

- Open the preview and check that the defect left the frame and which body part the cut line crosses. Adjust the cut line only by measuring the defect box again.
- For the same-ratio track, add the track, defect box, keep box, chosen edge, and cut ratio to the adoption record. For the free-ratio track, add the track, defect box, keep box, chosen edge, adopted ratio, remaining area, and restored size.
