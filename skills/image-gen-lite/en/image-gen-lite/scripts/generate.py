"""image-gen-lite: local CPU text-to-image in one script, raw model output.

WHY: the skill promises the model's own result with no repair pass, so the script does
     exactly one job per image: load the preset, render, fit the requested size, save, check.
HOW: SD 1.5 family presets run through diffusers. The precise preset runs FLUX.2 [klein] 4B
     through a pinned stable-diffusion.cpp binary (one prebuilt archive per supported platform).
     Both backends yield plain PIL images, so size fitting, saving and checks are shared.
     Generation uses the preset's native size; a different --width/--height is met by cropping
     to that ratio and resizing, which adds no detail.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

# WHY: one root for every download, overridable for shared machines
CACHE_ROOT = Path(os.environ.get("IMAGE_GEN_LITE_HOME", str(Path.home() / ".cache" / "image-gen-lite"))).expanduser()
# WHY: must be set before huggingface_hub or diffusers is imported, they read it once at import
os.environ.setdefault("HF_HOME", str(CACHE_ROOT / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

EXIT_ARGUMENT = 2
EXIT_DOWNLOAD = 3
EXIT_DEPENDENCY = 4
EXIT_WRITE = 5
EXIT_RESOURCE = 6
EXIT_INVALID_OUTPUT = 7
EXIT_INTEGRITY = 8
EXIT_PLATFORM = 9

DEFAULT_PRESET = "dreamshaper-8-lcm"
DEFAULT_SEED = 42
JPEG_QUALITY = 92
SAFE_NAME_PATTERN = re.compile(r"[^a-z0-9]+")

# Values come from each model card or from tuning on the CPU, see the preset section of SKILL.md.
PRESETS = {
    "dreamshaper-8-lcm": {
        "backend": "diffusers", "model_id": "Lykon/dreamshaper-8-lcm",
        "width": 512, "height": 512, "steps": 3, "guidance": 1.5, "scheduler": "lcm",
        "ram_gb": {"fp32": 6.0, "bf16": 3.5},
    },
    "sdxs": {
        # WHY: one-step distilled model, the model card requires 1 step and guidance 0
        "backend": "diffusers", "model_id": "IDKiro/sdxs-512-dreamshaper",
        "width": 512, "height": 512, "steps": 1, "guidance": 0.0, "scheduler": None,
        "ram_gb": {"fp32": 3.5, "bf16": 2.5},
    },
    "tiny-sd": {
        # WHY: the LCM scheduler collapses shapes on this model, DPM-Solver keeps them stable
        "backend": "diffusers", "model_id": "segmind/tiny-sd",
        "width": 384, "height": 384, "steps": 16, "guidance": 7.5, "scheduler": "dpm",
        "ram_gb": {"fp32": 4.0, "bf16": 3.0},
    },
    "flux2-klein-4b": {
        # WHY: distilled model, the upstream example uses 4 steps with cfg 1.0; step time grows
        #      with pixel count, so the default size keeps one image within a practical wait
        "backend": "sdcpp", "width": 384, "height": 512, "steps": 4, "guidance": 1.0,
        "download_gb": 5.2,
    },
}

# Pinned stable-diffusion.cpp release for the precise preset, one prebuilt CPU archive per
# platform, each checked by SHA-256 before use. Keys are (platform.system(), platform.machine()).
ENGINE_TAG = "master-881-17860c0"
ENGINE_RELEASE_URL = "https://github.com/leejet/stable-diffusion.cpp/releases/download/" + ENGINE_TAG + "/"
ENGINE_DIR = CACHE_ROOT / "klein" / ("sdcpp-" + ENGINE_TAG)
ENGINE_ASSETS = {
    ("Linux", "x86_64"): {
        "asset": "sd-master-17860c0-bin-Linux-Ubuntu-24.04-x86_64.zip",
        "sha256": "f57262d5104aa64465b4f1c0b2cc3b2c939b8c9b28db04931821c086eb04d1ef",
        "binary": "sd-cli", "library_path_variable": "LD_LIBRARY_PATH",
    },
    ("Darwin", "arm64"): {
        "asset": "sd-master-17860c0-bin-Darwin-macOS-26.6.2-arm64.zip",
        "sha256": "90472eb78c553974d568c0e9a2aa33566e6e0eb0fc495a963e9838afc6a07aae",
        "binary": "sd-cli", "library_path_variable": "DYLD_LIBRARY_PATH",
    },
    ("Windows", "AMD64"): {
        "asset": "sd-master-17860c0-bin-win-cpu-x64.zip",
        "sha256": "29a946446361f697ab29d2d9183e78ed726785cf2511034a7dd1da0b090e65c8",
        # WHY: Windows resolves the DLLs next to the executable through PATH
        "binary": "sd-cli.exe", "library_path_variable": "PATH",
    },
}
# (role, repository, file, pinned revision) from the official publisher of each part
KLEIN_MODEL_FILES = [
    ("diffusion", "unsloth/FLUX.2-klein-4B-GGUF", "flux-2-klein-4b-Q4_0.gguf",
     "0084d1df98e2e2137fe776d55170bc4792ec1d66"),
    ("llm", "unsloth/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf",
     "22c9fc8a8c7700b76a1789366280a6a5a1ad1120"),
    ("vae", "black-forest-labs/FLUX.2-klein-4B", "vae/diffusion_pytorch_model.safetensors",
     "e7b7dc27f91deacad38e78976d1f2b499d76a294"),
]
DISK_MARGIN_GB = 0.3

# WHY: a saved file under 10KB or with wrong magic bytes means a failed write or an empty image
MIN_OUTPUT_BYTES = 10 * 1024
MAGIC_BYTES = {"png": b"\x89PNG", "jpg": b"\xff\xd8\xff"}
SIZE_TOLERANCE_PIXELS = 8
# WHY: mismatched quantized files can silently return a flat single-colour image
MIN_PIXEL_STDDEV = 5.0


def log(message):
    """Progress goes to stderr so stdout stays machine readable."""
    print(message, file=sys.stderr, flush=True)


def fail(exit_code, message):
    log("ERROR: " + message)
    sys.exit(exit_code)


# ---- environment -----------------------------------------------------------------------------

def total_ram_gb():
    """Total memory in GB, or None where the platform does not expose it this way."""
    if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
        return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024 ** 3
    if sys.platform == "darwin":
        return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 1024 ** 3
    return None


def native_bf16_supported():
    """True when the CPU executes bfloat16 matrix multiplies in hardware (AVX512_BF16 or AMX)."""
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.is_file():
        return False
    flags = cpuinfo.read_text(errors="ignore")
    return "avx512_bf16" in flags or "amx_bf16" in flags


def pick_dtype(preset, requested):
    """bfloat16 halves weight memory but is emulated, and several times slower, on CPUs without
    native bfloat16 instructions. Use it when the CPU has them, or when float32 does not fit."""
    if requested in ("fp32", "bf16"):
        return requested
    if native_bf16_supported():
        return "bf16"
    ram = total_ram_gb()
    return "fp32" if ram is None or ram >= preset["ram_gb"]["fp32"] else "bf16"


def check_memory(preset, dtype):
    ram = total_ram_gb()
    need = preset["ram_gb"][dtype]
    if ram is not None and ram < need:
        fail(EXIT_RESOURCE, "total RAM %.1fGB is below %.1fGB for this preset" % (ram, need))


def free_disk_gb():
    root = CACHE_ROOT if CACHE_ROOT.exists() else CACHE_ROOT.parent
    root.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(root).free / 1024 ** 3


# ---- diffusers backend -----------------------------------------------------------------------

def load_pipeline(preset, dtype, threads):
    try:
        import torch
        from diffusers import DPMSolverMultistepScheduler, LCMScheduler, StableDiffusionPipeline
    except ImportError:
        fail(EXIT_DEPENDENCY, "torch or diffusers missing, install the dependencies in the skill environment")
    torch.set_num_threads(threads or os.cpu_count() or 1)
    torch_dtype = {"fp32": torch.float32, "bf16": torch.bfloat16}[dtype]
    try:
        pipe = StableDiffusionPipeline.from_pretrained(preset["model_id"], torch_dtype=torch_dtype, safety_checker=None)
    except OSError as error:
        fail(EXIT_DOWNLOAD, "could not load %s (%s)" % (preset["model_id"], error))
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


def render_with_diffusers(preset, args):
    """Yield (seed, image, seconds) for each requested image from one model load."""
    dtype = pick_dtype(preset, args.dtype)
    check_memory(preset, dtype)
    started = time.time()
    pipe = load_pipeline(preset, dtype, args.threads)
    log("preset=%s dtype=%s loaded in %.1fs, prompts stay on this machine" % (args.preset, dtype, time.time() - started))
    warn_if_truncated(pipe, args.prompt)
    import torch

    for index in range(args.count):
        seed = args.seed + index
        started = time.time()
        image = pipe(args.prompt, num_inference_steps=preset["steps"], guidance_scale=preset["guidance"],
                     width=preset["width"], height=preset["height"],
                     generator=torch.Generator().manual_seed(seed)).images[0]
        yield seed, image, time.time() - started


# ---- stable-diffusion.cpp backend ------------------------------------------------------------

def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def engine_for_this_platform():
    engine = ENGINE_ASSETS.get((platform.system(), platform.machine()))
    if engine is None:
        supported = ", ".join("%s %s" % key for key in ENGINE_ASSETS)
        fail(EXIT_PLATFORM, "no pinned engine for %s %s (supported: %s), choose another preset"
             % (platform.system(), platform.machine(), supported))
    return engine


def ensure_engine(engine):
    binary = ENGINE_DIR / engine["binary"]
    if binary.is_file():
        return binary
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    archive = ENGINE_DIR / engine["asset"]
    log("downloading engine %s" % engine["asset"])
    try:
        urllib.request.urlretrieve(ENGINE_RELEASE_URL + engine["asset"], archive)
    except OSError as error:
        fail(EXIT_DOWNLOAD, "engine download failed (%s)" % error)
    if sha256_of(archive) != engine["sha256"]:
        archive.unlink()
        fail(EXIT_INTEGRITY, "engine archive SHA-256 mismatch, file removed")
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(ENGINE_DIR)
    archive.unlink()
    binary.chmod(0o755)
    return binary


def ensure_klein_models(preset):
    try:
        from huggingface_hub import hf_hub_download, try_to_load_from_cache
    except ImportError:
        fail(EXIT_DEPENDENCY, "huggingface_hub missing in the skill environment")
    cached = all(isinstance(try_to_load_from_cache(repo, name, revision=rev), str)
                 for _, repo, name, rev in KLEIN_MODEL_FILES)
    if not cached and free_disk_gb() < preset["download_gb"] + DISK_MARGIN_GB:
        fail(EXIT_RESOURCE, "free disk %.1fGB, the precise preset needs about %.1fGB" % (free_disk_gb(), preset["download_gb"]))
    try:
        return {role: hf_hub_download(repo, name, revision=rev) for role, repo, name, rev in KLEIN_MODEL_FILES}
    except OSError as error:
        fail(EXIT_DOWNLOAD, "model download failed (%s)" % error)


def check_not_blank(image):
    from PIL import ImageStat

    spread = max(ImageStat.Stat(image.convert("RGB")).stddev)
    if spread < MIN_PIXEL_STDDEV:
        fail(EXIT_INVALID_OUTPUT, "output is a flat colour (pixel stddev %.1f), model files may not match" % spread)


def render_with_sdcpp(preset, args):
    """Yield (seed, image, seconds); the engine renders one image per process."""
    from PIL import Image

    engine = engine_for_this_platform()
    binary = ensure_engine(engine)
    models = ensure_klein_models(preset)
    variable = engine["library_path_variable"]
    environment = dict(os.environ)
    environment[variable] = str(ENGINE_DIR) + os.pathsep + os.environ.get(variable, "")
    scratch = output_directory(args.out) / (".klein-%d.png" % os.getpid())
    for index in range(args.count):
        seed = args.seed + index
        command = [str(binary), "--diffusion-model", models["diffusion"], "--llm", models["llm"], "--vae", models["vae"],
                   "-p", args.prompt, "--cfg-scale", str(preset["guidance"]), "--steps", str(preset["steps"]),
                   "-W", str(preset["width"]), "-H", str(preset["height"]), "--seed", str(seed),
                   # WHY: without --mmap the weights are copied into RAM and small machines run out of memory
                   "--mmap", "--diffusion-fa", "--vae-tiling",
                   "-t", str(args.threads or os.cpu_count() or 1), "-o", str(scratch)]
        started = time.time()
        if subprocess.call(command, env=environment) != 0 or not scratch.is_file():
            fail(EXIT_INVALID_OUTPUT, "engine run failed")
        with Image.open(scratch) as rendered:
            image = rendered.convert("RGB")
        scratch.unlink()
        check_not_blank(image)
        yield seed, image, time.time() - started


# ---- output ----------------------------------------------------------------------------------

def fit_to_size(image, width, height, anchor_x, anchor_y):
    """Cover the target box, cut at the anchor (0.0 left or top, 1.0 right or bottom), resize to the exact size."""
    from PIL import Image

    scale = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = round((resized.width - width) * anchor_x)
    top = round((resized.height - height) * anchor_y)
    return resized.crop((left, top, left + width, top + height))


def output_directory(out_argument):
    target = Path(out_argument).expanduser()
    return target.parent if target.suffix.lower() in (".png", ".jpg", ".jpeg") else target


def output_path(out_argument, basename, image_format, index, count, overwrite):
    target = Path(out_argument).expanduser()
    if target.suffix.lower() in (".png", ".jpg", ".jpeg"):
        directory, stem = target.parent, target.stem
    else:
        directory, stem = target, basename
    directory.mkdir(parents=True, exist_ok=True)
    suffix = "" if count == 1 else "_%02d" % (index + 1)
    candidate = directory / ("%s%s.%s" % (stem, suffix, image_format))
    serial = 2
    # WHY: never overwrite an earlier result unless asked
    while candidate.exists() and not overwrite:
        candidate = directory / ("%s%s_%d.%s" % (stem, suffix, serial, image_format))
        serial += 1
    return candidate


def save(image, destination, image_format):
    try:
        if image_format == "jpg":
            image.convert("RGB").save(destination, "JPEG", quality=JPEG_QUALITY)
        else:
            image.convert("RGB").save(destination, "PNG")
    except OSError as error:
        fail(EXIT_WRITE, "could not save %s (%s)" % (destination, error))


def verify_image(path, image_format, expected_size):
    """Check file size, magic bytes, and pixel size right after saving."""
    from PIL import Image

    size_bytes = path.stat().st_size
    if size_bytes < MIN_OUTPUT_BYTES:
        fail(EXIT_INVALID_OUTPUT, "%s is %d bytes, below %d" % (path, size_bytes, MIN_OUTPUT_BYTES))
    with open(path, "rb") as handle:
        head = handle.read(8)
    if not head.startswith(MAGIC_BYTES[image_format]):
        fail(EXIT_INVALID_OUTPUT, "%s has magic bytes %s, expected %s" % (path, head[:4].hex(), MAGIC_BYTES[image_format].hex()))
    with Image.open(path) as saved:
        actual = saved.size
    if max(abs(actual[0] - expected_size[0]), abs(actual[1] - expected_size[1])) > SIZE_TOLERANCE_PIXELS:
        fail(EXIT_INVALID_OUTPUT, "%s is %dx%d, expected %dx%d" % (path, actual[0], actual[1], *expected_size))


# ---- entry point -----------------------------------------------------------------------------

def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="local CPU text-to-image, raw model output")
    parser.add_argument("--prompt", required=True, help="English prompt")
    parser.add_argument("--out", required=True, help="output directory or file path")
    parser.add_argument("--name", help="base file name (default: first words of the prompt)")
    parser.add_argument("--format", default="png", choices=["png", "jpg"])
    parser.add_argument("--width", type=int, help="final width; with --height, crops to the ratio then resizes")
    parser.add_argument("--height", type=int)
    parser.add_argument("--anchor-x", dest="anchor_x", type=float, default=0.5, help="crop anchor 0.0 left to 1.0 right")
    parser.add_argument("--anchor-y", dest="anchor_y", type=float, default=0.5, help="crop anchor 0.0 top to 1.0 bottom")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--count", type=int, default=1, help="images from one model load, seed +1 each")
    parser.add_argument("--preset", default=DEFAULT_PRESET, choices=sorted(PRESETS))
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "bf16"], help="diffusers presets only")
    parser.add_argument("--threads", type=int, default=0, help="0 uses all logical cores")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def validate(args):
    if bool(args.width) != bool(args.height):
        fail(EXIT_ARGUMENT, "--width and --height go together")
    if args.width and (args.width <= 0 or args.height <= 0):
        fail(EXIT_ARGUMENT, "--width and --height must be positive")
    if args.count < 1:
        fail(EXIT_ARGUMENT, "--count must be 1 or more")
    if not (0.0 <= args.anchor_x <= 1.0 and 0.0 <= args.anchor_y <= 1.0):
        fail(EXIT_ARGUMENT, "--anchor-x and --anchor-y must be within 0.0-1.0")


def main(argv=None):
    args = parse_arguments(argv)
    validate(args)
    preset = PRESETS[args.preset]
    render = render_with_sdcpp if preset["backend"] == "sdcpp" else render_with_diffusers
    basename = args.name or SAFE_NAME_PATTERN.sub("_", " ".join(args.prompt.split()[:6]).lower()).strip("_")[:60] or "image"
    for index, (seed, image, seconds) in enumerate(render(preset, args)):
        if args.width:
            image = fit_to_size(image, args.width, args.height, args.anchor_x, args.anchor_y)
        destination = output_path(args.out, basename, args.format, index, args.count, args.overwrite)
        save(image, destination, args.format)
        verify_image(destination, args.format, image.size)
        print(json.dumps({"path": str(destination), "prompt": args.prompt, "seed": seed, "preset": args.preset,
                          "size": "%dx%d" % image.size, "seconds": round(seconds, 1)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
