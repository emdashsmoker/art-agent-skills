"""Generate images with a local Stable Diffusion 1.5 family preset on the CPU.

WHY: one command must cover model loading, square generation, cropping to the target
     ratio, and output checks, so every session produces the same result from the same inputs.
HOW: generation is always square (non-square generation stretches subjects). When final
     upscaling is chosen, the output keeps the working size and only the target ratio,
     finalize.py later upscales once. When it is not chosen, the output is resized here.
"""
import common  # noqa: F401  (sets the skill-owned cache before any Hugging Face import)

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from common import (EXIT_MISSING_DEPENDENCY, EXIT_QUERY_OR_ARGUMENT, EXIT_RESOURCE_SHORTAGE, EXIT_WRITE_FAILURE,
                    MEMORY_REQUIREMENTS_GB, fail, load_preflight, log, verify_image)
from probe import pick_dtype, total_ram_gb

DEFAULT_PRESET = "dreamshaper-8-lcm"
DEFAULT_SEED = 42
JPEG_QUALITY = 92
SAFE_NAME_PATTERN = re.compile(r"[^\w.-]+")
# WHY: 384px output is too small for most uses when no final upscaling follows
MIN_EDGE_WITHOUT_UPSCALING = 512

# Values come from each model card or from the author's tuning, see references/models.md.
PRESETS = {
    "dreamshaper-8-lcm": {
        "model_id": "Lykon/dreamshaper-8-lcm",
        "size": 512, "steps": 3, "guidance": 1.5, "scheduler": "lcm",
    },
    "sdxs": {
        # WHY: one-step distilled model, the model card requires 1 step and guidance 0
        "model_id": "IDKiro/sdxs-512-dreamshaper",
        "size": 512, "steps": 1, "guidance": 0.0, "scheduler": None,
    },
    "tiny-sd": {
        # WHY: the LCM scheduler collapses shapes on this model, DPM-Solver keeps them stable
        "model_id": "segmind/tiny-sd",
        "size": 384, "steps": 16, "guidance": 7.5, "scheduler": "dpm",
    },
}


def choose_dtype(preset_name, requested):
    import torch

    fp32_need = MEMORY_REQUIREMENTS_GB[preset_name]["fp32"]
    return {"fp32": torch.float32, "bf16": torch.bfloat16}[pick_dtype(fp32_need, requested)]


def check_memory(preset_name, dtype):
    import torch

    ram = total_ram_gb()
    need = MEMORY_REQUIREMENTS_GB[preset_name]["fp32" if dtype == torch.float32 else "bf16"]
    if ram is not None and ram < need:
        fail(EXIT_RESOURCE_SHORTAGE, "total RAM %.1fGB is below %.1fGB for this preset" % (ram, need))


def load_pipeline(preset, dtype, threads):
    try:
        import torch
        from diffusers import DPMSolverMultistepScheduler, LCMScheduler, StableDiffusionPipeline
    except ImportError:
        fail(EXIT_MISSING_DEPENDENCY, "torch or diffusers missing, install the dependencies in the skill environment")
    torch.set_num_threads(threads or os.cpu_count() or 1)
    # NOTE: newer diffusers also accepts dtype=, torch_dtype is kept for older releases
    pipe = StableDiffusionPipeline.from_pretrained(preset["model_id"], torch_dtype=dtype, safety_checker=None)
    if preset["scheduler"] == "lcm":
        pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    elif preset["scheduler"] == "dpm":
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def warn_if_truncated(pipe, prompt):
    """The CLIP text encoder reads 77 tokens, later text is ignored without an error."""
    token_ids = pipe.tokenizer(prompt).input_ids
    limit = pipe.tokenizer.model_max_length
    if len(token_ids) > limit:
        dropped = pipe.tokenizer.decode(token_ids[limit - 1:-1])
        log("WARNING: prompt has %d tokens, limit %d, ignored text: %s" % (len(token_ids), limit, dropped))


def crop_to_ratio(image, width, height, anchor_x, anchor_y, allow_upscale):
    """Cover the target box, then cut at the anchor (0.0 left or top, 1.0 right or bottom).

    With allow_upscale False the result keeps the target ratio at working scale,
    for example 1024x576 from a 512px square becomes 512x288.
    """
    from PIL import Image

    if not allow_upscale:
        shrink = min(1.0, image.width / width, image.height / height)
        width, height = round(width * shrink), round(height * shrink)
    scale = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = round((resized.width - width) * anchor_x)
    top = round((resized.height - height) * anchor_y)
    return resized.crop((left, top, left + width, top + height))


def output_path(out_argument, basename, image_format, index, count, overwrite):
    target = Path(out_argument).expanduser()
    if target.suffix.lower() in (".png", ".jpg", ".jpeg"):
        directory, stem = target.parent, target.stem
    else:
        directory, stem = target, basename
    directory.mkdir(parents=True, exist_ok=True)
    suffix = "" if count == 1 else "-%02d" % (index + 1)
    candidate = directory / ("%s%s.%s" % (stem, suffix, image_format))
    serial = 2
    # WHY: never overwrite an earlier result unless asked
    while candidate.exists() and not overwrite:
        candidate = directory / ("%s%s-%d.%s" % (stem, suffix, serial, image_format))
        serial += 1
    return candidate


def save(image, destination, image_format):
    try:
        if image_format == "jpg":
            image.convert("RGB").save(destination, "JPEG", quality=JPEG_QUALITY)
        else:
            image.convert("RGB").save(destination, "PNG")
    except OSError as error:
        fail(EXIT_WRITE_FAILURE, "could not save %s (%s)" % (destination, error))


def shape_output(image, args, preset, defer_upscaling):
    """Apply the target size rule and return the image with its expected size."""
    from PIL import Image

    if args.width:
        shaped = crop_to_ratio(image, args.width, args.height, args.anchor_x, args.anchor_y,
                               allow_upscale=not defer_upscaling)
        return shaped, shaped.size
    if not defer_upscaling and preset["size"] < MIN_EDGE_WITHOUT_UPSCALING:
        edge = MIN_EDGE_WITHOUT_UPSCALING
        return image.resize((edge, edge), Image.LANCZOS), (edge, edge)
    return image, image.size


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="local CPU text-to-image")
    parser.add_argument("--prompt", required=True, help="English prompt")
    parser.add_argument("--out", required=True, help="output directory or file path")
    parser.add_argument("--name", help="base file name")
    parser.add_argument("--format", default="png", choices=["png", "jpg"])
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--anchor-x", dest="anchor_x", type=float, default=0.5)
    parser.add_argument("--anchor-y", dest="anchor_y", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--count", type=int, default=1, help="images from one model load, seed +1 each")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="default: preflight record, then %s" % DEFAULT_PRESET)
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "bf16"])
    parser.add_argument("--threads", type=int, default=0, help="0 uses all logical cores")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def validate(args):
    if bool(args.width) != bool(args.height):
        fail(EXIT_QUERY_OR_ARGUMENT, "--width and --height go together")
    if args.count < 1:
        fail(EXIT_QUERY_OR_ARGUMENT, "--count must be 1 or more")
    if not (0.0 <= args.anchor_x <= 1.0 and 0.0 <= args.anchor_y <= 1.0):
        fail(EXIT_QUERY_OR_ARGUMENT, "--anchor-x and --anchor-y must be within 0.0-1.0")


def main(argv=None):
    args = parse_arguments(argv)
    validate(args)
    record = load_preflight(args.out)
    if record.get("enhance") is None:
        fail(EXIT_QUERY_OR_ARGUMENT, "preflight.json has no upscaling answer, ask the user and rerun preflight.py")
    recorded = record.get("preset")
    preset_name = args.preset or (recorded if recorded in PRESETS else DEFAULT_PRESET)
    preset = PRESETS[preset_name]
    dtype = choose_dtype(preset_name, args.dtype)
    check_memory(preset_name, dtype)
    defer_upscaling = record["enhance"] != "none"
    started = time.time()
    pipe = load_pipeline(preset, dtype, args.threads)
    log("preset=%s dtype=%s loaded in %.1fs, prompts stay on this machine"
        % (preset_name, str(dtype).replace("torch.", ""), time.time() - started))
    warn_if_truncated(pipe, args.prompt)
    import torch

    basename = args.name or SAFE_NAME_PATTERN.sub("-", "-".join(args.prompt.split()[:6]).lower()).strip("-.")[:60] or "image"
    for index in range(args.count):
        seed = args.seed + index
        started = time.time()
        image = pipe(args.prompt, num_inference_steps=preset["steps"], guidance_scale=preset["guidance"],
                     height=preset["size"], width=preset["size"],
                     generator=torch.Generator().manual_seed(seed)).images[0]
        seconds = time.time() - started
        image, expected = shape_output(image, args, preset, defer_upscaling)
        destination = output_path(args.out, basename, args.format, index, args.count, args.overwrite)
        save(image, destination, args.format)
        verify_image(destination, args.format, expected)
        print(json.dumps({"path": str(destination), "prompt": args.prompt, "seed": seed, "preset": preset_name,
                          "dtype": str(dtype).replace("torch.", ""), "size": "%dx%d" % expected,
                          "seconds": round(seconds, 1), "final_upscaling": record["enhance"]}, ensure_ascii=False))
    if defer_upscaling:
        log("Outputs are working size. After defect handling and trimming, run finalize.py once on the adopted image.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
