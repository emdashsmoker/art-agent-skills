"""Engine presets: quantized models through the stable-diffusion.cpp prebuilt CLI, CPU only.

WHY: models with billions of parameters follow instructions and render detail better than the
     SD 1.5 family, but they do not fit small memory through PyTorch. Quantized GGUF files with
     memory mapping keep the weights on disk pages instead of RAM.
HOW: downloads a pinned release binary (SHA-256 checked) and the model files from their official
     repositories at pinned revisions, then runs the CLI with fixed arguments. The engine, the
     text encoder and the run code are shared, a preset holds only the values that differ.
     One image per run. Linux x86_64 only, because only that binary is pinned.
"""
import common  # noqa: F401

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

from common import (CACHE_ROOT, EXIT_INTEGRITY_FAILURE, EXIT_INVALID_OUTPUT, EXIT_MISSING_DEPENDENCY,
                    EXIT_QUERY_OR_ARGUMENT, EXIT_RESOURCE_SHORTAGE, EXIT_UNSUPPORTED_PLATFORM,
                    fail, load_preflight, log)

ENGINE_TAG = "master-881-17860c0"
ENGINE_ASSET = "sd-master-17860c0-bin-Linux-Ubuntu-24.04-x86_64.zip"
ENGINE_URL = "https://github.com/leejet/stable-diffusion.cpp/releases/download/%s/%s" % (ENGINE_TAG, ENGINE_ASSET)
ENGINE_SHA256 = "f57262d5104aa64465b4f1c0b2cc3b2c939b8c9b28db04931821c086eb04d1ef"
ENGINE_BINARY = "sd-cli"
ENGINE_DIR = CACHE_ROOT / "sdcpp" / ENGINE_TAG


def model_file(repository, name, revision, size_gb):
    """One file from its official publisher at a pinned revision, with its download size."""
    return {"repository": repository, "name": name, "revision": revision, "size_gb": size_gb}


# WHY: both presets were trained on the text features of Qwen3-4B, so one file serves both
TEXT_ENCODER = model_file("unsloth/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf",
                          "22c9fc8a8c7700b76a1789366280a6a5a1ad1120", 2.5)
PRESETS = {
    "flux2-klein-4b": {
        "diffusion": model_file("unsloth/FLUX.2-klein-4B-GGUF", "flux-2-klein-4b-Q4_0.gguf",
                                "0084d1df98e2e2137fe776d55170bc4792ec1d66", 2.5),
        "vae": model_file("black-forest-labs/FLUX.2-klein-4B", "vae/diffusion_pytorch_model.safetensors",
                          "e7b7dc27f91deacad38e78976d1f2b499d76a294", 0.2),
        # WHY: distilled model, the upstream example uses 4 steps
        "steps": 4,
    },
    "z-image-turbo": {
        "diffusion": model_file("leejet/Z-Image-Turbo-GGUF", "z_image_turbo-Q4_0.gguf",
                                "c61c0e422dc8b541b7548cf33a4ef8302b0f8085", 3.7),
        "vae": model_file("Tongyi-MAI/Z-Image-Turbo", "vae/diffusion_pytorch_model.safetensors",
                          "f332072aa78be7aecdf3ee76d5c247082da564a6", 0.2),
        # WHY: distilled model, the model card asks for 8 evaluations and the upstream example uses 8 steps
        "steps": 8,
    },
}
# WHY: both presets are distilled to run without guidance, their upstream examples use cfg 1.0
CFG_SCALE = 1.0
DISK_MARGIN_GB = 0.3
# WHY: step time grows with pixel count, the default keeps one image within a practical wait
DEFAULT_SIZE = (384, 512)
MAX_PIXELS = 512 * 704
DEFAULT_SEED = 42
# WHY: mismatched quantized files can silently return a flat single-colour image
MIN_PIXEL_STDDEV = 5.0


def parse_size(text):
    width, height = (int(part) for part in text.lower().split("x"))
    if width % 16 or height % 16 or width * height > MAX_PIXELS:
        raise argparse.ArgumentTypeError("width and height must be multiples of 16, at most 512x704 pixels in total")
    return width, height


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_engine():
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        fail(EXIT_UNSUPPORTED_PLATFORM, "the pinned engine binary is Linux x86_64 only, offer another tier")
    binary = ENGINE_DIR / ENGINE_BINARY
    if binary.is_file():
        return binary
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    archive = ENGINE_DIR / ENGINE_ASSET
    log("downloading engine %s" % ENGINE_ASSET)
    urllib.request.urlretrieve(ENGINE_URL, archive)
    if sha256_of(archive) != ENGINE_SHA256:
        archive.unlink()
        fail(EXIT_INTEGRITY_FAILURE, "engine archive SHA-256 mismatch, file removed")
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(ENGINE_DIR)
    archive.unlink()
    binary.chmod(0o755)
    return binary


def ensure_models(preset_name):
    """Paths of the three model files by engine role, downloaded when missing."""
    try:
        from huggingface_hub import hf_hub_download, try_to_load_from_cache
    except ImportError:
        fail(EXIT_MISSING_DEPENDENCY, "huggingface_hub missing in the skill environment")
    preset = PRESETS[preset_name]
    files = {"diffusion": preset["diffusion"], "llm": TEXT_ENCODER, "vae": preset["vae"]}
    # WHY: a file shared with another preset may be cached already, only missing files need disk space
    missing_gb = sum(item["size_gb"] for item in files.values()
                     if not isinstance(try_to_load_from_cache(item["repository"], item["name"],
                                                              revision=item["revision"]), str))
    free_gb = shutil.disk_usage(CACHE_ROOT if CACHE_ROOT.exists() else CACHE_ROOT.parent).free / 1024 ** 3
    if missing_gb and free_gb < missing_gb + DISK_MARGIN_GB:
        fail(EXIT_RESOURCE_SHORTAGE, "free disk %.1fGB, %s still needs about %.1fGB" % (free_gb, preset_name, missing_gb))
    return {role: hf_hub_download(item["repository"], item["name"], revision=item["revision"])
            for role, item in files.items()}


def check_not_blank(path):
    from PIL import Image, ImageStat

    spread = max(ImageStat.Stat(Image.open(path).convert("RGB")).stddev)
    if spread < MIN_PIXEL_STDDEV:
        fail(EXIT_INVALID_OUTPUT, "output is a flat colour (pixel stddev %.1f), model files may not match" % spread)


def main(argv=None):
    parser = argparse.ArgumentParser(description="engine preset generation, one image per run")
    parser.add_argument("prompt", help="natural-language English prompt")
    parser.add_argument("out_path", help="PNG file path")
    parser.add_argument("--preset", required=True, choices=sorted(PRESETS))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--size", type=parse_size, default=DEFAULT_SIZE, help="default 384x512, at most 512x704 pixels")
    parser.add_argument("--threads", type=int, default=0)
    args = parser.parse_args(argv)
    if not args.out_path.lower().endswith(".png"):
        fail(EXIT_QUERY_OR_ARGUMENT, "out_path must end with .png")
    load_preflight(args.out_path)
    binary = ensure_engine()
    models = ensure_models(args.preset)
    command = [str(binary), "--diffusion-model", models["diffusion"], "--llm", models["llm"], "--vae", models["vae"],
               "-p", args.prompt, "--cfg-scale", str(CFG_SCALE), "--steps", str(PRESETS[args.preset]["steps"]),
               "-W", str(args.size[0]), "-H", str(args.size[1]), "--seed", str(args.seed),
               # WHY: without --mmap the weights are copied into RAM and small machines run out of memory
               "--mmap", "--diffusion-fa", "--vae-tiling",
               "-t", str(args.threads or os.cpu_count() or 1), "-o", args.out_path]
    environment = dict(os.environ, LD_LIBRARY_PATH=str(ENGINE_DIR) + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
    started = time.time()
    if subprocess.call(command, env=environment) != 0 or not os.path.isfile(args.out_path):
        fail(EXIT_INVALID_OUTPUT, "engine run failed")
    check_not_blank(args.out_path)
    print(json.dumps({"path": args.out_path, "prompt": args.prompt, "seed": args.seed, "preset": args.preset,
                      "size": "%dx%d" % args.size, "seconds": round(time.time() - started, 1)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
