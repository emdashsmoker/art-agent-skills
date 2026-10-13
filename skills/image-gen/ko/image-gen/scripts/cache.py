"""List or delete what this skill downloaded. Nothing outside the skill cache root is touched.

WHY: models and post-processing weights take gigabytes. Deleting by hand risks removing
     files that belong to other tools, so deletion goes through this script only.
HOW: model repositories live in the skill's own Hugging Face cache (HF_HOME under the cache
     root) and are removed with the library's cache API, which also frees the shared blob store.
     Folders for weights and the engine binary are removed directly.
"""
import common  # noqa: F401

import argparse
import json
import shutil
import sys

from common import CACHE_ROOT, EXIT_QUERY_OR_ARGUMENT, HF_HOME, fail

TARGETS = {
    "dreamshaper-8-lcm": {"repos": ["Lykon/dreamshaper-8-lcm"], "folders": []},
    "sdxs": {"repos": ["IDKiro/sdxs-512-dreamshaper"], "folders": []},
    "tiny-sd": {"repos": ["segmind/tiny-sd"], "folders": []},
    "flux2-klein-4b": {"repos": ["unsloth/FLUX.2-klein-4B-GGUF", "unsloth/Qwen3-4B-GGUF",
                                 "black-forest-labs/FLUX.2-klein-4B"], "folders": ["klein"]},
    "inpaint": {"repos": ["stable-diffusion-v1-5/stable-diffusion-inpainting",
                          "latent-consistency/lcm-lora-sdv1-5"], "folders": []},
    "face": {"repos": [], "folders": ["face"]},
    "sr": {"repos": [], "folders": ["sr"]},
}
# WHY: the virtual environment is the skill's installation, not a cache, so "all" keeps it
KEPT_FOLDERS = {"venv"}


def folder_size_gb(path):
    if not path.exists():
        return 0.0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink()) / 1024 ** 3


def scan():
    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        return None
    hub = HF_HOME / "hub"
    return scan_cache_dir(hub) if hub.exists() else None


def list_caches():
    report = {"cache_root": str(CACHE_ROOT), "repos": {}, "folders": {}}
    info = scan()
    if info:
        for repo in info.repos:
            report["repos"][repo.repo_id] = round(repo.size_on_disk / 1024 ** 3, 2)
    if CACHE_ROOT.exists():
        for child in CACHE_ROOT.iterdir():
            if child.is_dir() and child.name not in KEPT_FOLDERS | {"hf"}:
                report["folders"][child.name] = round(folder_size_gb(child), 2)
    report["free_disk_gb"] = round(shutil.disk_usage(CACHE_ROOT if CACHE_ROOT.exists() else CACHE_ROOT.parent).free / 1024 ** 3, 1)
    print(json.dumps(report, ensure_ascii=False, indent=1))


def delete_repos(repo_ids):
    info = scan()
    if not info:
        return []
    revisions = [rev.commit_hash for repo in info.repos if repo.repo_id in repo_ids for rev in repo.revisions]
    if revisions:
        info.delete_revisions(*revisions).execute()
    return sorted(repo.repo_id for repo in info.repos if repo.repo_id in repo_ids)


def delete(target):
    if target == "all":
        removed = []
        if CACHE_ROOT.exists():
            for child in CACHE_ROOT.iterdir():
                if child.name not in KEPT_FOLDERS:
                    shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink()
                    removed.append(child.name)
        return removed
    spec = TARGETS[target]
    removed = delete_repos(set(spec["repos"]))
    for name in spec["folders"]:
        path = CACHE_ROOT / name
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            removed.append(str(path))
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(description="skill-owned cache management")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    remove = sub.add_parser("delete")
    remove.add_argument("target", choices=sorted(TARGETS) + ["all"])
    args = parser.parse_args(argv)
    if args.command == "list":
        list_caches()
        return 0
    if not CACHE_ROOT.exists():
        fail(EXIT_QUERY_OR_ARGUMENT, "no cache at %s" % CACHE_ROOT)
    removed = delete(args.target)
    free = shutil.disk_usage(CACHE_ROOT).free / 1024 ** 3
    print(json.dumps({"removed": removed, "free_disk_gb": round(free, 1)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
