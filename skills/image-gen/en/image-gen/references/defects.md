# Defect checks and responses

Details for the defect handling section of SKILL.md. Read this once generation ends, before the check, because the defect criteria are here. If the upfront workaround answer is optimize or maximum, read it before recording the pre-generation answers, because the first prompt uses the workarounds in this file. postprocess.md covers the post-processing tools.

## Trim-first check

When a defect is found, answer these two questions before regenerating or applying a workaround.

- Does the defect touch or lie close to one of the four edges of the frame?
- Setting that defect aside, is there no other reason to regenerate for the subject, style, color, or framing?

If both answers are yes, act on the `trim` value in preflight.json. With `same`, `free`, or `free-auto`, run edge trimming before regenerating. With `off`, continue with the normal response stages. People differ on how much cropping or ratio change they accept, so the `trim` value is the only criterion.

Trimming comes first because regenerating discards a satisfactory framing and expression. A trim takes seconds and does not count toward the regeneration limit. The defect pixels are removed from the frame, so the fix is certain. Anatomical defects, extra objects, and duplicated subjects are fixed by regenerating or redrawing only by chance.

- Examples: anatomical errors such as the number or shape of fingers, toes, and limbs, more objects than intended, the same subject twice, small warped shapes, cut-off limbs, fake signatures, frames or borders caught at the edge.
- Defects not on this list receive the same treatment if trimming the edge can remove them from the frame. Whether trimming works is decided by running edge_trim.py.
- If edge_trim.py ends with `NOT_APPLICABLE`, consider the free-ratio track when `trim` is `free` or `free-auto`. With `same`, return to the normal response stages.
- If you present the best result after reaching the regeneration limit, apply this check to that result once before presenting it.

## General defects

Defects outside the fragile subjects (next section) are handled in one of two ways. If an instruction in the prompt is not reflected, revise the prompt. If it is reflected but the placement or decoration differs from the intent, change the seed.

| Defect | Response |
|---|---|
| Style not applied | Move the style phrase to the front. Replace abstract style words with a technique name |
| Wrong color | Name the color family, for example `muted blue and beige palette` |
| More objects than requested | Place the count at the front, for example `a single` |
| Unrequested objects | List only the objects that should appear and shorten the description |
| In a scene, an unrequested person occupies the center | Change the style to a technique name such as `watercolor illustration` or `flat vector illustration`. If the person remains, try two more seeds. If the person still remains, change the element combination |
| Paper texture or a cropped rectangle appears | End the prompt with `plain background`. A seed change has the stronger effect, so apply both |
| Halo or circular decoration in the background | Change the seed |
| Framing or subject position unsatisfactory | Change the seed |
| Warped shapes | Change the seed. If it repeats, reduce secondary elements and simplify the description |
| Water reflections or grid patterns are misaligned | Change the seed. If it repeats, remove reflection and grid elements from the prompt |

- A person that belongs to the request, or a small figure mixed into the background, is not an unrequested-person defect. Abstract style words in scene prompts can be interpreted as a photographic portrait, which causes this defect.
- Change one thing in the prompt at a time, so that the effective change can be identified.
- If the same defect remains after up to three prompt edits and up to three seed changes, keep the chosen model and respond by request type.
- When the multiplier in force is 2 or more, add the number of moves to the next candidate in the pool to the count of seed changes, because every candidate has its own seed. For example, if all three candidates of a 3x pool show the same defect, count two seed changes as used and regenerate only once more.
- For message requests and diagram requests, go back to the original message and select another stand-in. A seed change only rearranges the same metaphor, so repeating it has no effect when the metaphor does not fit.
- For named-subject requests, keep the subject, present the best result with its defects, and ask how to proceed.
- For scene requests that went through no substitution, change the element combination.
- If the same defect remains after changing the stand-in or the element combination, present the best result with its defects and ask how to proceed.
- Offer a model change only as an option, following the model lock section of SKILL.md.
- Record the prompt and seed of the adopted result.

## Fragile subjects

These are people, animals, precise objects, and background crowds. Diffusion models cannot control facial features, the number of limbs, fingers, or how parts connect, so run the procedure on the assumption that defects will occur. An unrequested person follows the general defect table above. Judge by the definition of a shape problem in the visual check of SKILL.md.

Face defects include a face smeared in part or as a whole and also unclear features, missing features, distorted feature placement, left-right asymmetry, mismatched gaze or pupils, broken mouths and teeth, and the like. If it still looks unnatural at the size it will be used, the defect is confirmed. Slight blur on a distant figure in the background is not a defect.

Compare the position, spacing, size, and left-right balance of the eyes, nose, and mouth with the criteria below. The list holds examples.

- The two eyes have the same height and size, and the gap between them is about one eye wide.
- The nose and mouth sit on the center line between the eyes.
- The eyes, nose, and mouth are arranged in that order from the top, without overlapping or being too far apart.
- The eyes, nose, and mouth are sized to fit the face.

A body count defect is an anatomical shape problem in which the number of a body part differs from the standard count. The standard counts are 5 fingers on each hand, 5 toes on each foot, 2 arms, and 2 legs for a person, 4 legs for a four-legged animal, and the like. The list holds examples, so for animals not on it, use the real count of the species.

- Examples of too many are a sixth finger, a third arm or leg, and two hands on one arm. Examples of too few are a hand showing only 3 fingers with nothing covering it, a limb that stops partway inside the frame, and a finger that melts into the body.
- Fingers or toes fused or clumped so that you cannot count them one by one are a defect. Fingers fused into a wedge, fingers smeared like long brushstrokes, and the like are examples.
- Do not count distant figures in the background so small that their fingers are not drawn separately even when enlarged.

Respond in this order.

1. Stage 1, regeneration with the same prompt: keep the prompt, change only the seed, and regenerate with the original intent.
2. Stage 2, prompt workaround: add an instruction that hides or avoids the defective part.
3. Stage 3, post-processing: redraw only the defective part with face restoration or region redrawing (postprocess.md).
4. Stage 4, composition workaround: change the camera shot, framing, or scene layout.

Enter a stage only when the same defect remains after the previous stage has used all its attempts. Never skip stage 1 to go straight to stage 2 or later. Workarounds give up part of the original intent, such as a bare face, a natural pose, or the original scene. Seed changes alone often fix the defect, so apply the cost-free option first.

When the multiplier in force is 2 or more, swapping within the candidate pool replaces stage 1. The candidates are stage 1's seed changes made ahead of time, at generation. When too few candidates can be adopted or an adopted candidate has to be replaced, swap in a remaining candidate. Once the pool is exhausted, proceed to stage 2 without a stage 1 regeneration. A candidate adopted at rank 3 of the adoption order in candidates.md goes straight to stage 3 post-processing without stage 2. The pool has already been judged to hold no better candidate, and post-processing preserves the original intent.

Edge trimming needs no installation and loses almost nothing of the original intent, so run it first at any stage. It applies when the defect touches or is close to an edge, and the trim-first check decides whether to run it.

The answers in preflight.json decide whether to enter stage 3.

- With `postfix` set to `auto`, enter without asking. With `bypass`, skip stage 3. With `ask`, ask about the tool and whether to proceed each time.
- With `face_scope` set to `off`, face defects skip stage 3 and go to stage 4 once stage 2 is exhausted.
- Finger defects enter stage 3 only when `finger_inpaint` is `on`. With `off`, they go to stage 4 once stage 2 is exhausted.
- With `face_scope` set to `always`, face restoration runs right after generation as the default step, and face defects are judged on the restored image. For a three-quarter view or profile face, adopt whichever of the original and the restored image has fewer defects, following the non-frontal face rule in postprocess.md, and judge on that image. The same rule applies to a profile generated by the stage 4 composition workaround.
- In candidate mode, `always` follows `spare_finish_resolved`. With `adopted`, judge the originals to adopt, restore only the adopted images, and judge them on the restored versions. With `all`, restore every candidate once and judge on the restored images. In both cases, three-quarter view and profile faces follow the comparison above.

### Regeneration limit

By default each stage allows one regeneration. If the limit is reached, stop regenerating.

| Preset | Stage 1 | Stage 2 | Stage 4 | Total | Total with 2x or more candidates |
|---|---|---|---|---|---|
| Light | 1 | 2 | 1 | 4 | 3 |
| Standard, Flat | 1 | 1 | 1 | 3 | 2 |
| Precise | 1 | 0 | 0 | 1 | 0 |

- When the multiplier in force is 2 or more, swapping within the candidate pool replaces stage 1, so stage 1 has no regeneration. The last column is the total in that case. A pool swap selects an image that already exists, so it does not count as a regeneration.
- Light generates images quickly, so it allows one extra round of trial and error for choosing a workaround. The second stage-2 attempt must use a different workaround from the first. Changing only the seed with the same workaround counts as stage 1, not stage 2.
- Precise takes the longest per image, so one regeneration reaches the limit.
- Stage 3 post-processing fixes part of an existing output and does not count as a regeneration. Apply each tool once and compare.
- At the limit, present the best result with the defect marked and ask how to proceed. Without a display path, describe the defect location in words (display path judgment in the delivery section of SKILL.md). The choices are: adopt the best result, try again with a workaround the user selects, switch to a scene without people or an object icon, or change the model (with its download size and estimated time).

### Workarounds

The table holds examples. If another option fits the theme, time of day, or style of the scene better, adapt it on the same principle: hide or avoid the defective part. Scarves and knit hats in a winter scene, a helmet in a space scene, a wide-brimmed hat and sunglasses on a beach, and a hard hat on a construction site all follow that principle.

| Defect | Stage 2 prompt workaround | Stage 4 composition workaround |
|---|---|---|
| Face defect | Closed eyes (`eyes closed`), a hat or hood, helmet, visor, sunglasses, a simple expression (`neutral expression`) | Side or back view, an upper-body close-up that makes the face larger |
| Wrong number of limbs | (Trim first if it touches an edge) a simple pose (`standing, arms at sides`), a coat or cape | An upper-body shot that leaves the legs out of the frame |
| Warped fingers or toes | (Trim first if it touches an edge) hands lowered at the sides (`arms at sides`), gloves, `hands in pockets`, long sleeves, holding a prop | A shot that leaves hands and feet out of the frame |
| Warped animal limbs or face | A sitting pose (`sitting`) | A side silhouette |
| Tangled parts on a precise object | Render as a silhouette | Swap in an object with a simple outline |
| Smeared faces in a background crowd | Crowd silhouettes (`silhouettes of people in the distance`) | Remove the crowd and keep the main subject alone |

- Face defects get worse the fewer pixels the face occupies. The two directions are covering part of the face (helmet, visor, sunglasses, hat) and enlarging the face (close-up). Covering part of it keeps some features and hides only the weak spots, so it looks less out of place.
- Closed eyes help when mismatched gaze or pupils are the main defect. Use them only where closed eyes look natural, such as rest, meditation, or listening to music.
- Turning the main person into a backlit silhouette gives up the facial features, so use it only as the last attempt within the limit. Silhouettes look natural for distant figures and background crowds, so this restriction does not apply to them.
- When a workaround sets or changes a pose, choose a static pose over a dynamic one. Diffusion models produce more defects as the joints of a pose grow more complex, with limbs overlapping, bending, touching other parts, and the like. Among static poses, prefer standing upright with the arms lowered at the sides, and the like. Diffusion models draw standing poses far more stably than sitting ones, because sitting bends the knees and hips and brings the legs against a chair or the body.
- Also choose hiding staging that keeps the drawing easy. Hands behind the head, hands in the hair, a hand on the face, crossed arms, and the like seem to hide the hands, but the fingers blend into the hair or other body parts and the arms bend, so defects grow more frequent. Avoid staging with large motion, such as running, jumping, a twisted body, and the like, for the same reason.
- Work around hand defects first with poses such as hands resting at the sides or lowered toward the bottom, and the like. Lowered hands are easy to trim away if a defect remains, because in a framing that ends at the waist or thighs they touch the bottom edge or leave the frame.
- Add one workaround at a time, so you can tell what caused the effect.
- Check that the adopted workaround (accessory, clothing, framing) fits the scene's time of day, color, and original message before using it.
- Record the stage, seed, and prompt of every attempt to track which stages are exhausted. Record the adopted result the same way.

## Upfront workaround

With `upfront_workaround` in preflight.json set to `optimize` or `max`, the first prompt already includes workaround staging. This choice is for users who want fewer defects in the first result instead of waiting for regeneration after a defect. Diffusion models often produce defects in the complex parts of animals, objects, buildings, and scene elements as well as people, so apply it regardless of the subject. Workarounds give up part of the original intent, so each answer defines what it preserves. With `off`, this section does not apply.

| Answer | Preserves | Uses |
|---|---|---|
| `optimize` (Optimize) | The subject, scene layout, and any look or shot range the user specified | Staging that removes, hides, or places defect-prone parts outside the frame, among options that keep the subject |
| `max` (Maximum) | The message and where the image will be used | The optimize options, all stage 2 and stage 4 options of the workaround table, removing defect-prone elements, and subject replacement |

The table below gives examples by target. The table holds examples, so choose options that suit the scene on the same principle: prevent the defect-prone parts from showing.

| Target | Defect-prone parts | Optimize examples | Maximum examples |
|---|---|---|---|
| People | Small faces, exposed hands | Hands lowered at the sides, a shot that places the hands outside the frame, a hat, sunglasses, gloves, hands in pockets | A back view, a backlit silhouette |
| Animals | Legs, face | An upper-body framing that places the legs outside the frame | A replacement with things that suggest the animal's presence (an empty doghouse, a food bowl, and the like) |
| Precise objects and machines | Spokes, joints between parts | A futuristic e-bike without spokes | A replacement with a futuristic vehicle without wheels |
| Buildings | Joints of pillars and roofs, repeated windows | A smooth facade with few windows and ornaments | A distant silhouette |
| Background crowds | Faces | Crowd silhouettes | Removing the crowd |

- Add workaround staging only to the parts that the requested framing makes defect-prone. For the same person, a full-body framing makes the small face and the hands defect-prone, and an upper-body framing makes the hands defect-prone.
- Within what the answer allows, choose in this order: a form that lacks the defect-prone part altogether, a framing that places that part outside the frame, then staging that hides it. The more completely the cause of the defect is removed from the frame, the stronger the effect. An object that is hard to draw itself (such as heavily folded cloth) brings new defects, so hide parts only with simple objects.
- Choose poses by the rules of the workarounds section (static poses, hiding that keeps the drawing easy, lowered hands, and the like). Workaround staging does not make the pose more dynamic than the original request.
- Choose only options that pass the fit check of the workarounds section and suit the scene's theme, time of day, and style. Leave a part without a workaround if nothing fits. Staging that clashes with the scene, such as wool gloves on a summer beach, stands out as much as a defect.
- Optimize does not use an option that conflicts with a look the user specified. For example, hands in pockets are not applied to a person waving a hand.
- The first prompt may hold one option per part. The rule of adding one workaround at a time applies to the attempts of the defect handling stages.
- Put the subject and style first in the prompt, and add the workaround phrases briefly after them.

### Maximum workaround

Maximum combines the options in the examples by target to remove defect-prone elements as far as possible. A backlit silhouette of the main subject may also be used in the first prompt, because the user has already chosen to keep only the message.

Subject replacement carries the same message with an object or scene that has fewer defect-prone elements. Choose the stand-in from the message of the original request, following the substitution rules of composition.md. For example, "a person working by a window with a coffee" can be replaced with "a desk by a window with a steaming coffee cup".

- Before replacing a named subject, present the revised setup in one line and obtain confirmation before recording the pre-generation answers. The user already chose that subject, and replacing it discards that choice.
- If the user disagrees, keep the subject and go no further than composition workarounds. If the user wants another stand-in, choose again from the message of the original request.
- For message requests, choose a stand-in with fewer defect-prone elements and ask for no separate confirmation, because the agent selects the stand-in in any case. For diagram requests, choose the substitute in the consent step by the same standard.
- When the subject stays and only the framing changes or elements are removed, state the changed elements in one line before generation starts and proceed without confirmation. Include any change to a look the user specified in that notice.
- If the subject changes, decide preflight.py's `--subject` and the automatic candidate multiplier from the changed setup.

### Handling after the first image

- Treat the workaround staging in the first prompt as part of the original intent from then on. Stage 1 keeps this prompt and changes only the seed.
- Stages 2 and 4 choose from options the first prompt did not use. Skip a stage with no options left, without counting it as a regeneration.
- The trim-first check, the stage order, and the regeneration limits stay the same as with `off`.

## Edge trimming

If a defect lies at an edge, trim that edge as little as possible to remove the defect from the frame. The typical case is a finger caught at the bottom. The trimmed pixels are removed, so the fix is certain for anatomical and object defects alike. It cannot help when the defect is in the middle of the frame. It uses only Pillow and takes seconds.

- The order is generation (already cropped to the target ratio), edge trimming, then final upscaling.
- In candidate mode, trim only the defects of adopted candidates. Spares are not trimmed even when they have defects.
- If final upscaling is chosen, save with `--no-resize` without enlarging. finalize.py produces the target size. If final upscaling is off, run without that option to enlarge back to the original size. The enlargement lowers sharpness by the same factor.

### Measuring coordinates

Read the defect box `x0,y0,x1,y1` from the coordinate grid drawn by grid_measure.py. Estimating coordinates by eye is error-prone, and a trim meant for a finger can extend to the waist or thighs.

- The grid image draws an enlarged copy, so read coordinates from the numbers on the grid lines.
- Check the full-frame grid first, then an enlarged grid around the defect. Make the second region generous enough to show nearby parts such as the wrist or elbow.
- Detection models are not used for measuring. They take minutes to install and load, and their boxes cover the whole body part, which makes the cut larger.
- Put only the defect in the defect box. For a finger defect, go from the fingertip to just before the wrist. The cut line adds only a 4px margin to the box edge, so a wide box cuts intact parts by the same amount.
- For defects on the same edge, repeat `--defect`. Run defects on different edges one run at a time.

### Cut window

edge_trim.py computes, for each of the four edges, the largest window that excludes the defect, and keeps the edge that leaves the most area. The cut depth comes from the measured defect box, so a shallow defect gets a shallow cut and a deep one a deep cut. With a keep box in `--keep`, the window is placed so that it contains that box.

### Same-ratio track

This is the default track. The window keeps the original aspect ratio and is resized back to the original size. The output format does not change, so always try this track first.

- It needs `--keep`. Give a union box around everything the original request must keep. For a person, that is the face, the requested shot range, and props named in the request. For an object, it is the whole subject.
- A box around the head alone still passes when a head-to-thigh shot turns into an upper-body shot. Include the shot range in the keep box to prevent that.
- If the window cannot contain the keep box, the script exits with `NOT_APPLICABLE`.
- Change the 4px margin with `--pad`. Pass `--max-ratio` only when a separate cap on the cut ratio is needed.
- Use the cut ratio and enlargement factor printed by the script as they are.
- The pre-generation answer already allowed it, so adopt the result without asking, and on delivery report the trim, the body part the cut line crosses, and the cut ratio.

### Free-ratio track

Run it with `--ratio`. The window ratio is released, so only the defect's edge is cut deep and the other direction stays wide. A same-ratio window shrinks the other direction by as much as it cuts, so even a defect of modest depth leaves no room for the head or other kept parts. Releasing the ratio can preserve the same picture as, for example, a wider frame. A window that keeps the whole other direction has an enlargement factor of 1.0 and stays sharper than the same-ratio track.

- Entry conditions: `trim` is `free` or `free-auto`, and the same-ratio track ended with `NOT_APPLICABLE` or its preview shows the cut line crossing the head or another kept part. With `same`, skip this track.
- If the conditions hold, consider this track before discarding the picture and moving to the next response stage.
- Candidates: run `--ratio free` (the maximum-keep window that cuts only the defect's edge) and one or two standard ratios that suit where the image will be used (16:9, 3:2, 4:3, 1:1, 3:4 and so on), each with a preview. If a person appears, give a keep box that includes the head in `--keep`. Without a keep box, the window is placed at the top.
- The restored size keeps the window ratio with its long side matched to the input's long side. Change it with `--long-side`. The script prints it as `target=WxH`. If final upscaling is chosen, run with `--no-resize` and pass the printed target to finalize.py's `--size` unchanged.

Build candidates to find the window closest to the staging and framing of the original request. Releasing the ratio means recomposing the image, so a window that only avoids the defect can turn into a different picture without the requested shot, props, or background. Before running candidates, list what the original request must keep: the shot range (for example head to thigh), the subject's position in the frame and the space in the direction of the gaze, the props and background elements named in the request, and where the image will be used.

- There is one keep box, so measure a union box that holds the head and the props together. The window is centered on the keep box. If the subject sat off to one side or had space in the direction of the gaze, widen the keep box toward that space to preserve the same balance.
- For each candidate, report what stays and what is lost compared with the original request, the remaining area (`area_kept`), the enlargement factor (`upscale`), and the body part the cut line crosses. The wider the ratio, the higher the cut line and the more the shot changes (for example a head-to-thigh shot becomes an upper-body shot at 16:9).
- Mark the candidate closest to the original intent as recommended. `free` tends to keep the most of the shot range.
- With `free`: even though the answer allowed it, always present the candidate previews and finalize with the ratio the user selects. The aspect ratio decides where the image fits, so the user chooses. The user can also specify another ratio as W:H, in which case run again and present a new preview. Do not discard candidates by a loss cap without presenting them.
- With `free-auto`: open and compare all candidate previews, select one yourself, and adopt it without asking. Select the candidate that keeps the most of the original shot range, subject position and gaze space, props and background elements, and fit for where the image will be used. If candidates tie, select the standard ratio that suits where the image will be used. Do not select a candidate that leaves the defect in the frame or whose cut line crosses the face. On delivery, report the trim, the adopted ratio, a one-line reason, the remaining area, the body part the cut line crosses, and what was lost. If the user wants another ratio, rerun on the same working image with the ratio they give.
- If neither track fits, or the user rejects every candidate, abandon the trim and continue with the normal response stages.

```
PY scripts/grid_measure.py in.png grid.png                        # full-frame grid
PY scripts/grid_measure.py in.png grid_zoom.png 100,373,300,512   # enlarged grid around the defect
PY scripts/edge_trim.py in.png out_trim.png --defect 155,461,177,507 --keep 200,40,320,500 --preview trim_preview.png
PY scripts/edge_trim.py in.png out_trim.png --defect 155,461,177,507 --keep 200,40,320,500 --no-resize --preview trim_preview.png   # with final upscaling
PY scripts/edge_trim.py in.png out_free.png --defect 140,340,205,430 --keep 215,30,305,330 --ratio free --preview free_preview.png   # free ratio, maximum-keep window
PY scripts/edge_trim.py in.png out_wide.png --defect 140,340,205,430 --keep 215,30,305,330 --ratio 16:9 --preview wide_preview.png   # free ratio, standard-ratio candidate
PY scripts/edge_trim.py in.png out_wide.png --defect 140,340,205,430 --keep 215,30,305,330 --ratio 16:9 --no-resize --long-side 1024   # with final upscaling, pass the printed target to finalize.py
```

- Open the preview and check that the defect was removed from the frame and which body part the cut line crosses. Adjust the cut line only by measuring the defect box again.
- For the same-ratio track, add the track, defect box, keep box, chosen edge, and cut ratio to the adoption record. For the free-ratio track, add the track, defect box, keep box, chosen edge, adopted ratio, remaining area, and restored size.

## Post-upscaling recheck

The post-upscaling recheck inspects the adopted image again on its 4x result after final upscaling. Defects drawn small rarely show at working size. Final upscaling sharpens edges and bright points, and in doing so it can leave anomalies that were absent before upscaling. The recheck looks on the 4x view for defects that the working-size check missed and for side effects that final upscaling left. The recheck only identifies defects. Responses and adoption follow the pre-generation answers and the existing rules unchanged, because the pre-generation answers reflect the user's intent most accurately.

- Apply it when `enhance` in preflight.json is `general` or `flat`. With `off`, this section does not apply.
- Run it right after finalize.py and before delivery.
- The target is the 4x result of the adopted image. Save the 4x result with `--x4-out` of finalize.py. Spares in candidate mode receive no defect repairs, so they are not rechecked.
- Enlarge each defect-prone part separately with grid_measure.py on the 4x result as well, following the enlargement rules in the visual check section of SKILL.md.
- When you find an anomaly on the 4x view, enlarge the same region of the adopted image before upscaling (the input of finalize.py) with grid_measure.py and compare. The region coordinates are the 4x coordinates divided by 4. If the same shape appears there, even blurred, the anomaly existed before upscaling. An enlarged view at working size shows small shapes blurred.
- Judge an anomaly that existed before upscaling by the visual check items section below. Judge an anomaly that was absent from the adopted image before upscaling by the final upscaling side effects section below.
- Record the recheck result in one line per image, in the record format of the visual check section, with a final upscaling side effect item added.

### Visual check items

Apply every item of the visual check section of SKILL.md to the 4x result again, without omission. The "Even outside this list" item, the rule that items in parentheses are examples, and the definition of a shape problem also apply unchanged. Judge again the items that the working-size check recorded as free of defects, because defects drawn small may not show at working size.

- Use the judgment on the 4x view as it is for shape defects, because these defects were in the adopted image before final upscaling. Examples include the position and gaze of the eyes, a difference between the left and right eyebrows, the shape of fingers, etc.
- Parts that generation drew blurred or dark gain no new edges on the 4x view. For such parts, apply the judgment rules of the visual check section unchanged (darkness and blur not meant to hide the part are not occlusion, and an uncertain judgment counts as a defect).
- Inspect adopted images that went through face restoration by the same criteria. The restored result was also inspected only at working size.

### Final upscaling side effects

A final upscaling side effect is an anomaly that was absent from the adopted image before upscaling and appeared after final upscaling. Examples include a waxy look, exaggerated nostril and lip edges, clumped hair, lost texture, exaggerated highlights, exaggerated eyebrow edges, etc. Judge an anomaly outside this list by the same principle if it was absent from the adopted image before upscaling.

- Classify an anomaly that arises when super-resolution inflates a bright point or an edge as a final upscaling side effect, even if it looks like a change of shape. A catchlight in the pupil enlarged into a white patch is one such example. Its cause is absent from the adopted image before upscaling, so the responses to shape defects do not resolve it.
- Look for side effects on the 4x view. Confirm a side effect if it also shows on the target-size result, because the delivered file is the target-size result. This follows the same principle as the rule that confirms a face defect at the size it will be used (fragile subjects section).

### Responses after the recheck

- Divide coordinates measured on the 4x result by 4 to convert them into coordinates of the adopted image before upscaling, because trimming, face restoration, and region redrawing run at the pre-upscaling size.
- For defects under the visual check items, apply the order of the defect handling section of SKILL.md (trim-first check, response stages, defect post-processing policy, regeneration limit) to the adopted image before upscaling unchanged.
- Within that order, face defects follow the existing face rules and the pre-generation answers (face restoration scope, defect post-processing policy, etc.) unchanged.
- Final upscaling side effects follow the side effect comparison rule in the final upscaling section of SKILL.md.
- If you fix the adopted image, run finalize.py again on the fixed adopted image. Do not apply final upscaling again to an upscaled result, because applying it twice to the same pixels accumulates the waxy look.
- Limit fixes that come from the recheck to one round, because every fix repeats final upscaling and the recheck, and each repetition adds waiting time.
- Recheck the result upscaled after the fix by the same criteria. If defects remain, follow the presentation procedure in the regeneration limit section.
