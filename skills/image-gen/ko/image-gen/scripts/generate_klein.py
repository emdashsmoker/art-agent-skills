"""Precise tier: FLUX.2 [klein] 4B through the stable-diffusion.cpp prebuilt CLI, CPU only.

WHY: the 4B model follows instructions and draws bodies more accurately than the
     SD 1.5 family, but it does not fit small memory through PyTorch. Quantized GGUF
     files with memory mapping keep the weights on disk pages instead of RAM.
HOW: downloads a pinned release binary (SHA-256 checked) and three model files from
     their official repositories at pinned revisions, then runs the CLI with fixed
     arguments. One image per run. Linux x86_64 only, because only that binary is pinned.
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
ENGINE_DIR = CACHE_ROOT / "klein" / ("sdcpp-" + ENGINE_TAG)
# (role, repository, file, pinned revision) from the official publishers of each part
MODEL_FILES = [
    ("diffusion", "unsloth/FLUX.2-klein-4B-GGUF", "flux-2-klein-4b-Q4_0.gguf",
     "0084d1df98e2e2137fe776d55170bc4792ec1d66"),
    ("llm", "unsloth/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf",
     "22c9fc8a8c7700b76a1789366280a6a5a1ad1120"),
    ("vae", "black-forest-labs/FLUX.2-klein-4B", "vae/diffusion_pytorch_model.safetensors",
     "e7b7dc27f91deacad38e78976d1f2b499d76a294"),
]
DOWNLOAD_GB = 5.2
# WHY: distilled model, the upstream example uses 4 steps with cfg 1.0
STEPS = 4
CFG_SCALE = 1.0
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


def ensure_models():
    try:
        from huggingface_hub import hf_hub_download, try_to_load_from_cache
    except ImportError:
        fail(EXIT_MISSING_DEPENDENCY, "huggingface_hub missing in the skill environment")
    cached = all(isinstance(try_to_load_from_cache(repo, name, revision=rev), str) for _, repo, name, rev in MODEL_FILES)
    free_gb = shutil.disk_usage(CACHE_ROOT if CACHE_ROOT.exists() else CACHE_ROOT.parent).free / 1024 ** 3
    if not cached and free_gb < DOWNLOAD_GB + 0.3:
        fail(EXIT_RESOURCE_SHORTAGE, "free disk %.1fGB, the precise tier needs about %.1fGB" % (free_gb, DOWNLOAD_GB))
    return {role: hf_hub_download(repo, name, revision=rev) for role, repo, name, rev in MODEL_FILES}


def check_not_blank(path):
    from PIL import Image, ImageStat

    spread = max(ImageStat.Stat(Image.open(path).convert("RGB")).stddev)
    if spread < MIN_PIXEL_STDDEV:
        fail(EXIT_INVALID_OUTPUT, "output is a flat colour (pixel stddev %.1f), model files may not match" % spread)


def main(argv=None):
    parser = argparse.ArgumentParser(description="FLUX.2 [klein] 4B precise generation")
    parser.add_argument("prompt", help="natural-language English prompt")
    parser.add_argument("out_path", help="PNG file path")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--size", type=parse_size, default=DEFAULT_SIZE, help="default 384x512, at most 512x704 pixels")
    parser.add_argument("--threads", type=int, default=0)
    args = parser.parse_args(argv)
    if not args.out_path.lower().endswith(".png"):
        fail(EXIT_QUERY_OR_ARGUMENT, "out_path must end with .png")
    load_preflight(args.out_path)
    binary = ensure_engine()
    models = ensure_models()
    command = [str(binary), "--diffusion-model", models["diffusion"], "--llm", models["llm"], "--vae", models["vae"],
               "-p", args.prompt, "--cfg-scale", str(CFG_SCALE), "--steps", str(STEPS),
               "-W", str(args.size[0]), "-H", str(args.size[1]), "--seed", str(args.seed),
               # WHY: without --mmap the weights are copied into RAM and small machines run out of memory
               "--mmap", "--diffusion-fa", "--vae-tiling",
               "-t", str(args.threads or os.cpu_count() or 1), "-o", args.out_path]
    environment = dict(os.environ, LD_LIBRARY_PATH=str(ENGINE_DIR) + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
    started = time.time()
    if subprocess.call(command, env=environment) != 0 or not os.path.isfile(args.out_path):
        fail(EXIT_INVALID_OUTPUT, "engine run failed")
    check_not_blank(args.out_path)
    print(json.dumps({"path": args.out_path, "prompt": args.prompt, "seed": args.seed, "preset": "flux2-klein-4b",
                      "size": "%dx%d" % args.size, "seconds": round(time.time() - started, 1)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
