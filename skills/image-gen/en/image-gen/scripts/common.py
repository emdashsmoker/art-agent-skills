"""Shared paths, exit codes, and checks for the image-gen scripts.

WHY: every script must use the same cache root, the same preflight rule, and the same
     output checks, otherwise one script could write where another one deletes.
HOW: import this module first. It points the Hugging Face cache at a folder owned by
     this skill, so deleting skill caches never touches models used by other tools.
"""
import json
import os
import sys
from pathlib import Path

# WHY: one root for everything this skill downloads, overridable for shared machines
CACHE_ROOT = Path(os.environ.get("IMAGE_GEN_HOME", str(Path.home() / ".cache" / "image-gen"))).expanduser()
HF_HOME = CACHE_ROOT / "hf"
# WHY: must be set before huggingface_hub or diffusers is imported, they read it once at import
os.environ.setdefault("HF_HOME", str(HF_HOME))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

PREFLIGHT_FILENAME = "preflight.json"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")

EXIT_OK = 0
EXIT_QUERY_OR_ARGUMENT = 2
EXIT_NETWORK_FAILURE = 3
EXIT_MISSING_DEPENDENCY = 4
EXIT_WRITE_FAILURE = 5
EXIT_RESOURCE_SHORTAGE = 6
EXIT_INVALID_OUTPUT = 7
EXIT_INTEGRITY_FAILURE = 8
EXIT_UNSUPPORTED_PLATFORM = 9

# WHY: a saved file under 10KB or with wrong magic bytes means a failed write or an empty image
MIN_OUTPUT_BYTES = 10 * 1024
MAGIC_BYTES = {"png": b"\x89PNG", "jpg": b"\xff\xd8\xff"}
SIZE_TOLERANCE_PIXELS = 8


# Total RAM (GB) needed per preset in float32 and in bfloat16:
# float32 weight files plus working memory during generation. Shared by generate.py and probe.py.
MEMORY_REQUIREMENTS_GB = {
    "dreamshaper-8-lcm": {"fp32": 6.0, "bf16": 3.5},
    "sdxs": {"fp32": 3.5, "bf16": 2.5},
    "tiny-sd": {"fp32": 4.0, "bf16": 3.0},
}


def log(message):
    """Progress goes to stderr so stdout stays machine readable."""
    print(message, file=sys.stderr, flush=True)


def fail(exit_code, message):
    log("ERROR: " + message)
    sys.exit(exit_code)


def output_directory(out_argument):
    """--out may be a directory or a file path, the preflight record lives in the directory."""
    target = Path(out_argument).expanduser()
    return target.parent if target.suffix.lower() in IMAGE_SUFFIXES else target


def load_preflight(out_argument):
    """Stop when the pre-generation answers were never recorded.

    WHY: post-processing choices are not generation arguments, so a skipped question would
         still produce an image. A missing record file turns the skipped question into an exit code.
    """
    record_path = output_directory(out_argument) / PREFLIGHT_FILENAME
    if not record_path.is_file():
        fail(EXIT_QUERY_OR_ARGUMENT,
             "%s not found. Ask the pre-generation questions, record the answers with "
             "scripts/preflight.py, then generate." % record_path)
    return json.loads(record_path.read_text(encoding="utf-8"))


def verify_image(path, image_format, expected_size):
    """Check file size, magic bytes, and pixel size right after saving."""
    from PIL import Image

    path = Path(path)
    size_bytes = path.stat().st_size
    if size_bytes < MIN_OUTPUT_BYTES:
        fail(EXIT_INVALID_OUTPUT, "%s is %d bytes, below %d" % (path, size_bytes, MIN_OUTPUT_BYTES))
    with open(path, "rb") as handle:
        head = handle.read(8)
    if not head.startswith(MAGIC_BYTES[image_format]):
        fail(EXIT_INVALID_OUTPUT, "%s has magic bytes %s, expected %s"
             % (path, head[:4].hex(), MAGIC_BYTES[image_format].hex()))
    with Image.open(path) as saved:
        actual = saved.size
    if expected_size and max(abs(actual[0] - expected_size[0]), abs(actual[1] - expected_size[1])) > SIZE_TOLERANCE_PIXELS:
        fail(EXIT_INVALID_OUTPUT, "%s is %dx%d, expected %dx%d" % (path, actual[0], actual[1], *expected_size))
    return actual


def parse_size(text):
    """'1024x576' -> (1024, 576)"""
    try:
        width, height = (int(part) for part in text.lower().split("x"))
    except ValueError:
        raise ValueError("size must look like 1024x576")
    if width <= 0 or height <= 0:
        raise ValueError("size must be positive")
    return width, height
