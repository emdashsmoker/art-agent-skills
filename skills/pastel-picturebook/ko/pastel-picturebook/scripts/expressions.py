"""Facial expressions as small, data-driven changes to a character spec (see assets/expressions.json).

A preset nudges existing face settings (mouth corners, lid opening, brow ends) rather than
swapping in new drawings, so an expression works on every face shape, at any strength.
"""
import json
from pathlib import Path

PRESETS_FILE = Path(__file__).resolve().parent.parent / "assets" / "expressions.json"


def get_path(tree, path, default=0.0):
    """Value at a dotted path such as "eyes.near.closed", or `default`."""
    node = tree
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def set_path(tree, path, value):
    """Write a value at a dotted path, creating dicts on the way."""
    keys = path.split(".")
    node = tree
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def apply_ops(spec, style, preset, amount=1.0, keep=None):
    """Apply one preset's operations, blended by `amount`.

    add: added to the value; scale: multiplies it; set: moves it to the target; style_scale: multiplies
    a style value. Paths listed in `keep` (a dict the user wrote) are left as the user set them.
    """
    def free(path):
        return keep is None or get_path(keep, path, None) is None

    for path, delta in preset.get("add", {}).items():
        if free(path):
            set_path(spec, path, get_path(spec, path) + delta * amount)
    for path, factor in preset.get("scale", {}).items():
        if free(path):
            set_path(spec, path, get_path(spec, path) * (1.0 + (factor - 1.0) * amount))
    for path, target in preset.get("set", {}).items():
        if free(path):
            if isinstance(target, str):
                set_path(spec, path, target)
                continue
            start = get_path(spec, path)
            value = start + (target - start) * amount
            # Counts (locks, folds) stay whole numbers.
            set_path(spec, path, int(round(value)) if isinstance(target, int) else value)
    for path, factor in preset.get("style_scale", {}).items():
        set_path(style, path, get_path(style, path) * (1.0 + (factor - 1.0) * amount))


def apply_expression(spec, style):
    """Apply spec["expression"] (a preset name, or {"name", "amount"}) to spec and style in place."""
    setup = spec.get("expression")
    if not setup:
        return
    setup = {"name": setup} if isinstance(setup, str) else dict(setup)
    presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    if setup["name"] not in presets or setup["name"].startswith("_"):
        raise ValueError(f"unknown expression {setup['name']!r}; known: {sorted(k for k in presets if not k.startswith('_'))}")
    preset = presets[setup["name"]]
    # The profile view draws only how far the mouth moved from its resting curve.
    setup["rest_smile"] = spec.get("mouth", {}).get("smile", 0.0)
    apply_ops(spec, style, preset, setup.get("amount", 1.0))
    setup.update(preset.get("flags", {}))
    spec["expression"] = setup
