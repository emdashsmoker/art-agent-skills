"""Redraw one measured rectangle with SD 1.5 inpainting, everything outside stays as it was.

WHY: one small flaw (a broken glasses rim, a missing strap, unrequested exposure) should not
     force the user to throw away an image they otherwise like.
HOW: a square area around the box goes through inpainting with LCM-LoRA (6 steps), the
     result is pasted back through a feathered mask. Box coordinates come from grid_measure.py.
"""
import common  # noqa: F401

import os
import sys
import time

from common import EXIT_MISSING_DEPENDENCY, EXIT_QUERY_OR_ARGUMENT, fail, log
from probe import pick_dtype

INPAINT_MODEL = "stable-diffusion-v1-5/stable-diffusion-inpainting"
LCM_LORA = "latent-consistency/lcm-lora-sdv1-5"
STEPS, GUIDANCE = 6, 1.5
# WHY: 0.65 extends existing shapes without redrawing them over each other,
#      covering skin with another material needs 1.0 because lower strength keeps the original colours
DEFAULT_STRENGTH = 0.65
CROP_SIZE = 512
# WHY: a wider square lets the model see surrounding colours and folds
BOX_PAD_RATIO = 0.6
MASK_PAD_RATIO = 0.15
MASK_BLUR = 8
NEGATIVE = "deformed, tangled, broken, blurry"
DEFAULT_SEED = 42
# WHY: fp16 weight files are expanded in RAM when run in float32
FP32_MIN_RAM_GB = 6.0


def parse_box(text):
    try:
        box = [int(v) for v in text.split(",")]
    except ValueError:
        box = []
    if len(box) != 4 or box[0] >= box[2] or box[1] >= box[3]:
        fail(EXIT_QUERY_OR_ARGUMENT, "box must be x0,y0,x1,y1 with x0<x1 and y0<y1")
    return box


def square_crop_box(box, width, height):
    x0, y0, x1, y1 = box
    side = min(int(max(x1 - x0, y1 - y0) * (1 + BOX_PAD_RATIO)), width, height)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    left = min(max(cx - side // 2, 0), width - side)
    top = min(max(cy - side // 2, 0), height - side)
    return left, top, left + side, top + side


def ensure_box_fits(box, crop):
    """WHY: the square input cannot exceed the short side of the image. On a wide trimmed image a
    longer box would be redrawn only in part while the run still succeeds, so stop before loading."""
    if box[0] < crop[0] or box[1] < crop[1] or box[2] > crop[2] or box[3] > crop[3]:
        fail(EXIT_QUERY_OR_ARGUMENT, "BOX_TOO_LARGE: box %s does not fit the square input %s, split it into parts "
             "shorter than the image short side" % (box, list(crop)))


def build_mask(box, crop):
    from PIL import Image, ImageDraw, ImageFilter

    left, top, right, _ = crop
    scale = CROP_SIZE / (right - left)
    pad = int((box[2] - box[0]) * MASK_PAD_RATIO)
    mask = Image.new("L", (CROP_SIZE, CROP_SIZE), 0)
    ImageDraw.Draw(mask).rectangle([(box[0] - pad - left) * scale, (box[1] - pad - top) * scale,
                                    (box[2] + pad - left) * scale, (box[3] + pad - top) * scale], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(MASK_BLUR))


def load_pipeline():
    try:
        import torch
        from diffusers import AutoPipelineForInpainting, LCMScheduler
    except ImportError:
        fail(EXIT_MISSING_DEPENDENCY, "torch, diffusers, or peft missing in the skill environment")
    torch.set_num_threads(os.cpu_count() or 1)
    dtype = {"fp32": torch.float32, "bf16": torch.bfloat16}[pick_dtype(FP32_MIN_RAM_GB)]
    pipe = AutoPipelineForInpainting.from_pretrained(INPAINT_MODEL, torch_dtype=dtype, variant="fp16",
                                                     safety_checker=None)
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    pipe.load_lora_weights(LCM_LORA)
    pipe.fuse_lora()
    pipe.set_progress_bar_config(disable=True)
    log("inpainting dtype=%s" % str(dtype).replace("torch.", ""))
    return pipe, torch


def inpaint(pipe, torch, image, box, prompt, seed, strength):
    from PIL import Image

    crop = square_crop_box(box, image.width, image.height)
    crop_image = image.crop(crop).resize((CROP_SIZE, CROP_SIZE), Image.LANCZOS)
    mask = build_mask(box, crop)
    out = pipe(prompt=prompt, negative_prompt=NEGATIVE, image=crop_image, mask_image=mask,
               num_inference_steps=STEPS, guidance_scale=GUIDANCE, strength=strength,
               generator=torch.Generator().manual_seed(seed)).images[0]
    side = crop[2] - crop[0]
    patched = image.copy()
    patched.paste(out.resize((side, side), Image.LANCZOS), crop[:2], mask.resize((side, side)))
    return patched


def main():
    if len(sys.argv) < 5:
        sys.exit('usage: region_fix.py IN_PATH OUT_PATH x0,y0,x1,y1 "PROMPT" [SEED] [STRENGTH]')
    from PIL import Image

    in_path, out_path, box, prompt = sys.argv[1], sys.argv[2], parse_box(sys.argv[3]), sys.argv[4]
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else DEFAULT_SEED
    strength = float(sys.argv[6]) if len(sys.argv) > 6 else DEFAULT_STRENGTH
    started = time.time()
    image = Image.open(in_path).convert("RGB")
    ensure_box_fits(box, square_crop_box(box, image.width, image.height))
    pipe, torch = load_pipeline()
    inpaint(pipe, torch, image, box, prompt, seed, strength).save(out_path)
    print("%s strength=%.2f %.1f sec" % (out_path, strength, time.time() - started))


if __name__ == "__main__":
    main()
