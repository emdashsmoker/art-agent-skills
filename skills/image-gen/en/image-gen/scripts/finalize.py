"""Final upscaling: 4x super-resolution once, then downscale to the target size.

WHY: generation is 512px or smaller, so trimming and larger target sizes need enlargement.
     Plain enlargement only adds pixels. A 4x super-resolution pass followed by a
     downscale replaces every enlargement step. Run it once on the adopted image,
     after defect handling and trimming, so it never runs twice or on discarded tries.
HOW: Real-ESRGAN compact network defined here (no realesrgan package, it pins an old
     basicsr), weights downloaded once and checked by SHA-256, tiled to bound memory.
"""
import common  # noqa: F401

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

from common import (CACHE_ROOT, EXIT_INTEGRITY_FAILURE, EXIT_MISSING_DEPENDENCY, EXIT_NETWORK_FAILURE,
                    EXIT_QUERY_OR_ARGUMENT, fail, load_preflight, log, parse_size, verify_image)

UPSCALE = 4
NUM_FEAT = 64
WEIGHTS_BASE_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/"
MODES = {
    "general": {"file": "realesr-general-x4v3.pth", "num_conv": 32,
                "sha256": "8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292"},
    # WHY: the file was published for animation frames, it is named by what it does well here, flat colour areas
    "flat": {"file": "realesr-animevideov3.pth", "num_conv": 16,
             "sha256": "b8a8376811077954d82ca3fcf476f1ac3da3e8a68a4f4d71363008000a18b75d"},
}
WEIGHTS_DIR = CACHE_ROOT / "sr"
DOWNLOAD_TIMEOUT_SECONDS = 120
# WHY: tiles bound the activation memory, the pad covers the receptive field so seams disappear
TILE_SIZE = 256
TILE_PAD = 36
DEFAULT_SIZE = (768, 768)


def ensure_weights(mode):
    spec = MODES[mode]
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    path = WEIGHTS_DIR / spec["file"]
    if not path.exists():
        log("downloading %s" % spec["file"])
        request = urllib.request.Request(WEIGHTS_BASE_URL + spec["file"], headers={"User-Agent": "image-gen"})
        try:
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                path.write_bytes(response.read())
        except (urllib.error.URLError, TimeoutError) as error:
            fail(EXIT_NETWORK_FAILURE, "weight download failed (%s)" % error)
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        path.unlink()  # WHY: never reuse a damaged or altered file
        fail(EXIT_INTEGRITY_FAILURE, "SHA-256 mismatch for %s, file removed, rerun to download again" % spec["file"])
    return path


def build_network(mode, torch):
    nn, functional = torch.nn, torch.nn.functional

    class CompactNetwork(nn.Module):
        """Same layers and key names as Real-ESRGAN SRVGGNetCompact."""

        def __init__(self, num_conv):
            super().__init__()
            self.body = nn.ModuleList([nn.Conv2d(3, NUM_FEAT, 3, 1, 1), nn.PReLU(NUM_FEAT)])
            for _ in range(num_conv):
                self.body.append(nn.Conv2d(NUM_FEAT, NUM_FEAT, 3, 1, 1))
                self.body.append(nn.PReLU(NUM_FEAT))
            self.body.append(nn.Conv2d(NUM_FEAT, 3 * UPSCALE ** 2, 3, 1, 1))
            self.upsampler = nn.PixelShuffle(UPSCALE)

        def forward(self, x):
            out = x
            for layer in self.body:
                out = layer(out)
            return self.upsampler(out) + functional.interpolate(x, scale_factor=UPSCALE, mode="nearest")

    network = CompactNetwork(MODES[mode]["num_conv"])
    state = torch.load(ensure_weights(mode), map_location="cpu", weights_only=True)
    network.load_state_dict(state["params_ema"] if "params_ema" in state else state["params"], strict=True)
    return network.eval()


def super_resolve(image, network, torch):
    import numpy
    from PIL import Image

    source = numpy.asarray(image.convert("RGB"), dtype=numpy.float32) / 255.0
    x = torch.from_numpy(source).permute(2, 0, 1).unsqueeze(0)
    height, width = source.shape[:2]
    output = torch.zeros(1, 3, height * UPSCALE, width * UPSCALE)
    with torch.no_grad():
        for top in range(0, height, TILE_SIZE):
            for left in range(0, width, TILE_SIZE):
                bottom, right = min(top + TILE_SIZE, height), min(left + TILE_SIZE, width)
                pad_top, pad_left = max(top - TILE_PAD, 0), max(left - TILE_PAD, 0)
                tile = network(x[:, :, pad_top:min(bottom + TILE_PAD, height), pad_left:min(right + TILE_PAD, width)])
                dy, dx = top - pad_top, left - pad_left
                output[:, :, top * UPSCALE:bottom * UPSCALE, left * UPSCALE:right * UPSCALE] = tile[
                    :, :, dy * UPSCALE:(dy + bottom - top) * UPSCALE, dx * UPSCALE:(dx + right - left) * UPSCALE]
    pixels = output.squeeze(0).permute(1, 2, 0).clamp(0, 1).numpy() * 255.0
    return Image.fromarray(pixels.round().astype(numpy.uint8))


def fit(image, size, anchor_x, anchor_y):
    """Downscale to cover the target, cut the rounding remainder at the anchor."""
    from PIL import Image

    width, height = size
    scale = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = round((resized.width - width) * anchor_x)
    top = round((resized.height - height) * anchor_y)
    return resized.crop((left, top, left + width, top + height))


def main(argv=None):
    parser = argparse.ArgumentParser(description="4x super-resolution then downscale to the target size")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--size", default="%dx%d" % DEFAULT_SIZE, help="target WxH, at most 4x the input")
    parser.add_argument("--mode", choices=sorted(MODES), help="default: the preflight answer")
    parser.add_argument("--anchor-x", dest="anchor_x", type=float, default=0.5)
    parser.add_argument("--anchor-y", dest="anchor_y", type=float, default=0.5)
    parser.add_argument("--threads", type=int, default=0)
    args = parser.parse_args(argv)
    mode = args.mode or load_preflight(args.output).get("enhance")
    if mode not in MODES:
        fail(EXIT_QUERY_OR_ARGUMENT, "final upscaling was not chosen (enhance=%s), keep the image as it is" % mode)
    try:
        size = parse_size(args.size)
    except ValueError as error:
        fail(EXIT_QUERY_OR_ARGUMENT, str(error))
    try:
        import torch
        from PIL import Image
    except ImportError:
        fail(EXIT_MISSING_DEPENDENCY, "torch or Pillow missing in the skill environment")
    torch.set_num_threads(args.threads or os.cpu_count() or 1)
    source = Image.open(args.input)
    if size[0] > source.width * UPSCALE or size[1] > source.height * UPSCALE:
        log("WARNING: target exceeds 4x the input, the extra part is plain enlargement")
    started = time.time()
    result = fit(super_resolve(source, build_network(mode, torch), torch), size, args.anchor_x, args.anchor_y)
    image_format = "jpg" if args.output.lower().endswith((".jpg", ".jpeg")) else "png"
    result.convert("RGB").save(args.output, "JPEG" if image_format == "jpg" else "PNG", **({"quality": 92} if image_format == "jpg" else {}))
    verify_image(args.output, image_format, size)
    print(json.dumps({"path": args.output, "mode": mode, "size": "%dx%d" % size,
                      "seconds": round(time.time() - started, 1)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
