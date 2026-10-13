"""Point basicsr at the current torchvision module path so gfpgan can be imported.

WHY: torchvision 0.17 removed transforms.functional_tensor, and basicsr still imports it.
HOW: edits files inside the installed basicsr package only, never other packages.
     Run it with the same Python that runs the skill. Prints every edited file.
"""
import importlib.util
import sys
from pathlib import Path

OLD_MODULE = "torchvision.transforms.functional_tensor"
NEW_MODULE = "torchvision.transforms.functional"


def basicsr_directory():
    # WHY: find_spec locates the package without importing it, importing would fail before the fix
    spec = importlib.util.find_spec("basicsr")
    if spec is None or not spec.submodule_search_locations:
        sys.exit("basicsr is not installed in this Python environment")
    return Path(list(spec.submodule_search_locations)[0])


def main():
    patched = []
    for path in basicsr_directory().rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if OLD_MODULE in text:
            path.write_text(text.replace(OLD_MODULE, NEW_MODULE), encoding="utf-8")
            patched.append(str(path))
    print("patched %d file(s)" % len(patched))
    for item in patched:
        print(item)


if __name__ == "__main__":
    main()
