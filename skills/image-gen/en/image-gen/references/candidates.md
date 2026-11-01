# Candidate mode

Procedures of candidate mode. Whenever the candidate generation answer is not 1x (automatic included), read this right after the pre-generation answers arrive and before recording them with preflight.py. The automatic decisions must be made before recording, and the candidate handling after generation follows this file too. The question items and the preflight.py arguments are in the pre-generation questions section of SKILL.md. The candidate mode rules of defect handling and post-processing are in defects.md and postprocess.md.

## Automatic candidate multiplier

When the candidate generation answer is automatic, decide the multiplier after the answers arrive and before recording them with preflight.py. The baseline is 1x. Increase it only on the grounds below.

- The main subject is prone to shape defects (a person, an animal, a precise object).
- The framing shows a person's hands or full body.
- The scene has several people or a background crowd.

1x is recommended in the cases below.

- The precise preset is in use. It takes the longest per image and draws shapes most accurately.
- An object icon or a landscape scene with no subject prone to shape defects.

Decide the multiplier by the recommended criteria below.

- With one ground, consider 2x. With several grounds, consider 3x.
- The recommended range is 1x to 3x.
- Before generation starts, report the multiplier, a one-line reason, the total count, and the estimated time. Then proceed without waiting for confirmation, in the same way as the free-ratio automatic trim.

## Automatic spare candidate finishing

When the spare candidate finishing answer is automatic, decide it after the multiplier is set and before recording with preflight.py. The baseline is a) adopted only. Adopted only keeps the generated originals, so spares can be finished individually later and the choice is reversible. All candidates consumes post-processing time in advance and is irreversible.

Choose b) all candidates only in the cases below.

- Candidate selection is user selection and face restoration scope is always. Faces differ significantly before and after restoration, so the contact sheet must show restored images for the user to select by the final look.
- The request shows an intent to receive every alternative.

- When only final upscaling applies, keep a. Final upscaling mostly changes sharpness and size, so it has little effect on comparing framing and expression.
- Before generation starts, report the choice and a one-line reason. Then proceed without waiting for confirmation.

## Candidate pool

When the multiplier in force is 2 or more, generate target count times multiplier candidates. This set of candidates is the candidate pool.

```
# Same prompt, 2 target images, 2x candidates
PY scripts/generate.py --prompt "a red bicycle leaning against a brick wall, side view, watercolor illustration" --out ./outputs --name bicycle --count 4

# Precise preset, 2x candidates, one image per run with a new seed and file name
PY scripts/generate_klein.py "an elderly man reading a newspaper on a park bench, photorealistic" ./outputs/reader-01.png --seed 42
PY scripts/generate_klein.py "an elderly man reading a newspaper on a park bench, photorealistic" ./outputs/reader-02.png --seed 43
```

- For target images that share a prompt, run once with `--count` set to target count times multiplier. When each target image has its own prompt, set `--count` for each prompt to the multiplier.
- The precise preset generates one image per run. Run each candidate separately with the seed increased by 1 and a new file name. Start the next run after the previous one finishes.
- Generate candidates in the output folder. The generation scripts and finalize.py read preflight.json from the output folder, so saving into a subfolder stops them with exit code 2. Spares are moved to the `candidates` folder after adoption (the candidate adoption section below).

## Candidate adoption

When the multiplier in force is 2 or more, check the whole candidate pool, then adopt the target count.

1. Check every candidate on its original file with the items of the visual check section in SKILL.md. When face restoration scope is always, follow the spare candidate finishing value in force. With all candidates, restore every candidate once and check the restored images. With adopted only, check the originals, then restore only the adopted images and judge them on the restored versions.
2. Build the contact sheet from all candidates. If every candidate received face restoration, use the restored images. Otherwise use the generated originals. Final upscaling comes after adoption, so the sheet does not reflect it.
3. Adopt according to the candidate selection answer.
4. If spare candidate finishing is all candidates and final upscaling was selected, apply final upscaling once to each spare. The input is the restored image if there is one, the generated original otherwise. finalize.py reads preflight.json from the output folder, so apply it in the output folder before moving. Skip it if the user asked to delete the spares.
5. Move the spares' generated originals and finished versions to the `candidates` folder inside the output folder. Adopted images remain in the output folder for defect handling, trimming, and final upscaling.

```
PY scripts/contact_sheet.py ./outputs/bicycle-01.png ./outputs/bicycle-02.png ./outputs/bicycle-03.png ./outputs/bicycle-04.png --out ./outputs/bicycle_sheet.png
PY scripts/contact_sheet.py "./outputs/reader-0?_face.png" --out ./outputs/reader_sheet.png   # restored images, the script expands the wildcard
```

- The contact sheet numbers its inputs from 1 in the given order. stdout prints the number-to-file mapping as JSON.
- The contact sheet is for choosing framing and expression. Judge small defects on the original candidate files.
- With agent selection, adopt the target count in the adoption order below and continue through to completion. Record the adopted candidates, their ranks, and the reasons.
- With user selection, present the contact sheet right after generation and let the user select by number. Report the defects found in each candidate, one line each. Ask in one line whether to delete the spares, so the same reply can answer it (the spare deletion section below). Run defect handling and finishing on the selected candidates.
- If a candidate the user selected has a defect with no means of repair, report the defect and ask whether to select again from the remaining candidates or proceed to defect handling stage 2.
- Without a display path, do not ask for user selection and proceed with agent selection.

The agent adoption order:

1. Candidates without defects
2. Candidates whose only defects trimming resolves (trim answer other than off). Candidates resolved by same-ratio trimming come before those that need free-ratio trimming.
3. Candidates whose only defects post-processing resolves (defect post-processing answer is automatic or ask each time). Face defects that always-on face restoration resolves fall in this rank regardless of the defect post-processing answer.

- Within a rank, select the candidate closest to the subject, framing, and style of the original request.
- Do not adopt candidates with defects that have no means of repair. General defects that need a new image (style, color, count, and so on) belong here too.
- Fill slots the pool cannot fill with the defect handling procedure. Fragile subjects start at stage 2 without a stage 1 regeneration (defects.md).

## Scope in candidate mode

The answers to the existing items apply in candidate mode as below.

| Existing item | Candidate mode behavior |
|---|---|
| Final upscaling | Applied once to the adopted images only, or to every candidate, according to the spare candidate finishing value in force |
| Edge trim | Applied only to defects of adopted candidates. With off, the adoption order has no rank 2 |
| Defect post-processing | Automatic serves as rank 3 of the adoption order. Workarounds only treats candidates that need post-processing as having no means of repair. Ask each time asks only when the higher ranks fall short |
| Face restoration scope | Always follows the spare candidate finishing value in force. Only on defects follows the defect post-processing rules. Off does not apply |
| Finger redrawing | Applied only to adopted candidates |

- Defect repairs (trimming, face restoration on defects, region redrawing, finger redrawing, and the like) apply to adopted images only, regardless of the answers. Each repair needs its own judgment and user confirmation per candidate, so repairing spares too would multiply questions and time by the number of candidates.
- Always-on face restoration runs once per candidate.
- If the user wants some spares, move each one's generated original to the output folder and run the same repairs and finishing as for adopted images. Final upscaling is applied only once, so start over from the generated original.

## Spare deletion

Spares are kept by default. Deletion cannot be undone, so delete them only when the user, after seeing the candidates, asks to delete them. The question is asked only where the work already waits for the user's reply, so it does not interrupt an automatic run.

- Ask about deletion once, in one line. With user selection, ask when you present the contact sheet. With agent selection, ask on delivery.
- Delete at the delivery step, after defect handling and finishing. Until then, pool swaps may need the spares.
- Delete only the spare files created in this request (generated originals, restored versions, finished versions). Keep the adopted images and the contact sheet. If the candidates folder ends up empty, delete the folder too.
- Report the names of the deleted files on delivery.
