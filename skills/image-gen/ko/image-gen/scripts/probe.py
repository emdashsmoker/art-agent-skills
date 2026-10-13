"""Report what this machine can run, and optionally estimate seconds per image.

WHY: disk, memory, CPU features, and network decide which presets can run and how long
     they take, and these differ on every machine. Measure them here instead of assuming.
HOW: prints one JSON object. --estimate adds a short matrix-multiply benchmark (a few
     seconds) and converts it into per-preset estimates. Estimates are rough, the first
     real image gives the reliable number.
"""
import common  # noqa: F401

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request

from common import CACHE_ROOT, MEMORY_REQUIREMENTS_GB

HUB_URL = "https://huggingface.co"
HUB_TIMEOUT_SECONDS = 10
BENCH_MATRIX = 1024
BENCH_SECONDS = 1.5
# WHY: effective work per image in GFLOP = (seconds per image) x (benchmark GFLOPS) measured on one
#      reference CPU without native bfloat16 instructions. "bf16" is the
#      emulated case, used only when bfloat16 is picked for lack of memory. To recalibrate, run one
#      image and this benchmark on the same machine and multiply the two numbers.
WORK_GFLOP_PER_IMAGE = {
    "dreamshaper-8-lcm": {"fp32": 10600, "bf16": 6400},
    "sdxs": {"fp32": 850, "bf16": 510},
    "tiny-sd": {"fp32": 14500, "bf16": 8760},
    # WHY: runs quantized in its own engine, the float32 benchmark is the closest proxy
    "flux2-klein-4b": {"fp32": 152500},
}
DEPENDENCIES = ["torch", "diffusers", "transformers", "accelerate", "safetensors", "peft",
                "huggingface_hub", "PIL", "numpy", "gfpgan", "facexlib", "basicsr", "cv2"]


def cpu_features():
    """CPU name, core counts, and vector features. Uses torch when available (works on every OS)."""
    info = {"name": platform.processor() or platform.machine(), "logical_cores": os.cpu_count(),
            "physical_cores": None, "features": {}}
    try:
        import torch

        caps = torch.cpu.get_capabilities()
        info["name"] = caps.get("cpu_name") or info["name"]
        info["physical_cores"] = caps.get("num_physical_cores")
        for key in ("avx2", "avx512_f", "avx512_bf16", "amx_bf16"):
            if key in caps:
                info["features"][key] = bool(caps[key])
    except Exception:  # WHY: torch missing or too old, fall back to the Linux flag list
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as handle:
                flags = next((line.split(":", 1)[1].split() for line in handle if line.startswith("flags")), [])
            info["features"] = {"avx2": "avx2" in flags, "avx512_f": "avx512f" in flags,
                                "avx512_bf16": "avx512_bf16" in flags, "amx_bf16": "amx_bf16" in flags}
        except OSError:
            pass
    return info


def native_bf16_supported():
    features = cpu_features()["features"]
    return bool(features.get("avx512_bf16") or features.get("amx_bf16"))


def pick_dtype(fp32_min_ram_gb, requested="auto"):
    """'fp32' or 'bf16' for this CPU and memory.

    WHY: bfloat16 halves weight memory but is emulated, and several times slower, on CPUs
         without native bfloat16 instructions. Use it when the CPU has them, or when float32 does not fit.
    """
    if requested in ("fp32", "bf16"):
        return requested
    if native_bf16_supported():
        return "bf16"
    ram = total_ram_gb()
    return "fp32" if ram is None or ram >= fp32_min_ram_gb else "bf16"


def total_ram_gb():
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024 ** 3
        if sys.platform == "darwin":
            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 1024 ** 3
        if sys.platform == "win32":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                            ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                            ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                            ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                            ("avail_ext", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.total_phys / 1024 ** 3
    except Exception:
        return None
    return None


def available_ram_gb():
    """Linux only, None elsewhere."""
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024 ** 2
    except OSError:
        return None
    return None


def free_disk_gb():
    path = CACHE_ROOT
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free / 1024 ** 3


def hub_reachable():
    try:
        request = urllib.request.Request(HUB_URL, method="HEAD")
        with urllib.request.urlopen(request, timeout=HUB_TIMEOUT_SECONDS) as response:
            return response.status == 200
    except Exception:  # WHY: only reachability matters here
        return False


def installed(module):
    return importlib.util.find_spec(module) is not None


def matmul_gflops(dtype_name):
    """Sustained matrix-multiply throughput for one dtype on all logical cores."""
    import torch

    torch.set_num_threads(os.cpu_count() or 1)
    dtype = {"fp32": torch.float32, "bf16": torch.bfloat16}[dtype_name]
    a = torch.randn(BENCH_MATRIX, BENCH_MATRIX).to(dtype)
    b = torch.randn(BENCH_MATRIX, BENCH_MATRIX).to(dtype)
    torch.matmul(a, b)  # warm-up
    runs, started = 0, time.time()
    while time.time() - started < BENCH_SECONDS:
        torch.matmul(a, b)
        runs += 1
    return 2 * BENCH_MATRIX ** 3 * runs / (time.time() - started) / 1e9


def estimate(report):
    """Seconds per image per preset, for the precision generate.py would pick on this machine."""
    gflops = {name: matmul_gflops(name) for name in ("fp32", "bf16")}
    native = report["cpu"]["native_bf16"]
    result = {"benchmark_gflops": {k: round(v, 1) for k, v in gflops.items()}, "seconds_per_image": {}}
    for preset, work in WORK_GFLOP_PER_IMAGE.items():
        dtype = pick_dtype(MEMORY_REQUIREMENTS_GB[preset]["fp32"]) if preset in MEMORY_REQUIREMENTS_GB else "fp32"
        # WHY: with native bfloat16 only the matrix multiplies speed up, the float32 figure is a safe upper bound
        basis = "fp32" if dtype == "fp32" or native else "bf16"
        result["seconds_per_image"][preset] = {"seconds": round(work[basis] / gflops[basis]), "dtype": dtype}
    result["note"] = ("estimate only, report it as an estimate and replace it with the measured time of the first image"
                      + (", native bfloat16 CPUs usually run faster than shown" if native else ""))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="environment check for image-gen")
    parser.add_argument("--estimate", action="store_true", help="add a few-second CPU benchmark and time estimates")
    args = parser.parse_args(argv)
    cpu = cpu_features()
    cpu["native_bf16"] = bool(cpu["features"].get("avx512_bf16") or cpu["features"].get("amx_bf16"))
    report = {
        "os": platform.system(), "arch": platform.machine(), "python": platform.python_version(),
        "in_virtualenv": sys.prefix != getattr(sys, "base_prefix", sys.prefix),
        "cpu": cpu,
        "memory": {"total_gb": round(total_ram_gb() or 0, 1) or None,
                   "available_gb": round(available_ram_gb(), 1) if available_ram_gb() else None},
        "cache_root": str(CACHE_ROOT), "free_disk_gb": round(free_disk_gb(), 1),
        "hub_reachable": hub_reachable(),
        "dependencies": {name: installed(name) for name in DEPENDENCIES},
        # WHY: the precise tier uses a prebuilt engine that exists for Linux x86_64 only
        "precise_tier_supported": platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"),
    }
    if args.estimate:
        if not report["dependencies"]["torch"]:
            report["estimate"] = "torch not installed, install dependencies first"
        else:
            report["estimate"] = estimate(report)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
