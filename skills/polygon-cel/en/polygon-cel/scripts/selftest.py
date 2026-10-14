#!/usr/bin/env python3
"""Installation self-test: imports, spec validation, and a tiny render.

Exit code 0 means the engine can render in this environment.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
        import skia  # noqa: F401
    except ImportError as e:
        print(f"missing dependency: {e.name}. install: pip install -r requirements.txt")
        return 1
    from codeillust import pipeline, spec

    try:
        spec.normalize({"style": "not_a_style"})
        print("FAIL: invalid spec was accepted")
        return 1
    except ValueError:
        pass
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "selftest.png")
        info = pipeline.render({"quality": "draft", "canvas": {"width": 384, "height": 480}}, out,
                               log=lambda *_: None)
        ok = os.path.getsize(out) > 10_000
    print(f"{'OK' if ok else 'FAIL'}: test render in {info['seconds']}s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
