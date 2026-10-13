"""Add the CodeFormer strength answer to an existing image-gen preflight.json.

WHY: image-gen records its own answers and knows nothing about this add-on. The add-on keeps
     its answer in the same file so later steps read one record.
HOW: run right after image-gen's preflight.py, and again whenever that record is rewritten.
     The item is required only when face restoration can actually run.
"""
import argparse
import json
import sys
from pathlib import Path

PREFLIGHT_FILENAME = "preflight.json"
STRENGTHS = ["aggressive", "stepwise"]
EXIT_OK = 0
EXIT_QUERY_REQUIRED = 2


def strength_required(record):
    """Face restoration runs unless it is off, or unless it only runs on defects while stage 3 is skipped."""
    if record.get("subject") != "person":
        return False
    scope, postfix = record.get("face_scope"), record.get("postfix")
    return not (scope == "off" or (scope == "defect" and postfix == "bypass"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="record the CodeFormer strength answer")
    parser.add_argument("--out", required=True, help="output directory holding image-gen's preflight.json")
    parser.add_argument("--face-strength", dest="face_strength", choices=STRENGTHS)
    parser.add_argument("--user-reply", dest="user_reply", help="the user's reply, verbatim")
    args = parser.parse_args(argv)
    path = Path(args.out).expanduser() / PREFLIGHT_FILENAME
    if not path.is_file():
        sys.stderr.write("%s not found, run image-gen preflight.py first\n" % path)
        return EXIT_QUERY_REQUIRED
    record = json.loads(path.read_text(encoding="utf-8"))
    needed = strength_required(record)
    if needed and args.face_strength is None:
        sys.stderr.write("--face-strength is required: aggressive (start at w=0.0) or stepwise (0.5, 0.25, 0.0)\n")
        return EXIT_QUERY_REQUIRED
    if needed and not (args.user_reply or "").strip():
        sys.stderr.write("--user-reply is required, record the user's reply verbatim\n")
        return EXIT_QUERY_REQUIRED
    record["codeformer_strength"] = args.face_strength if needed else None
    record["codeformer_user_reply"] = args.user_reply if needed else None
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"codeformer_strength": record["codeformer_strength"]}))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
