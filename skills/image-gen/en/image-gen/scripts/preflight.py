"""Record the user's pre-generation answers, refuse when a required answer is missing.

WHY: an instruction alone can be skipped silently because generation still succeeds.
     Generation scripts require this record, so a skipped question shows up as exit code 2.
HOW: writes preflight.json into the output directory. Rerun it whenever an answer changes.
"""
import argparse
import enum
import json
import os
import sys

from common import EXIT_OK, EXIT_QUERY_OR_ARGUMENT, PREFLIGHT_FILENAME


class Subject(str, enum.Enum):
    PERSON = "person"                  # at least one person in the frame, any size
    PRECISE_OBJECT = "precise-object"  # no person, but an object whose part connections identify it
    OTHER = "other"


CHOICES = {
    "enhance": ["none", "general", "flat"],
    "trim": ["off", "same", "free", "free-auto"],
    "postfix": ["auto", "bypass", "ask"],
    "face_scope": ["defect", "always", "off"],
    "finger_inpaint": ["off", "on"],
}

QUERY_LABELS = {
    "enhance": "final upscaling (none, general, flat)",
    "trim": "edge trim (off, same = same ratio only, free = free ratio with preview, free-auto = free ratio chosen automatically)",
    "postfix": "defect post-processing (auto, bypass = seed and prompt changes only, ask = ask each time)",
    "face_scope": "face restoration scope (defect = only on face defects, always, off)",
    "finger_inpaint": "finger inpainting (off, on)",
}


def required_items(subject, postfix):
    """Items the user must answer for this request."""
    # WHY: generation is 512px or smaller, so enlargement loss always happens, ask upscaling every time
    # WHY: cropping and ratio changes are a matter of taste, ask trimming every time
    items = ["enhance", "trim"]
    if subject in (Subject.PERSON.value, Subject.PRECISE_OBJECT.value):
        items.append("postfix")
    if subject == Subject.PERSON.value:
        items.append("face_scope")
        if postfix != "bypass":
            items.append("finger_inpaint")
    return items


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="record pre-generation answers")
    parser.add_argument("--out", required=True, help="output directory that will hold preflight.json")
    parser.add_argument("--subject", required=True, choices=[s.value for s in Subject])
    parser.add_argument("--user-reply", dest="user_reply", help="the user's reply, verbatim")
    # WHY: model choice is a conditional question, record the chosen preset name as given
    parser.add_argument("--preset", help="preset the user chose in the model question, omit when not asked")
    for name, values in CHOICES.items():
        parser.add_argument("--" + name.replace("_", "-"), dest=name, choices=values)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_arguments(argv)
    needed = required_items(args.subject, args.postfix)
    missing = [name for name in needed if getattr(args, name) is None]
    if missing:
        sys.stderr.write("Missing answers, ask the user and rerun:\n")
        for name in missing:
            sys.stderr.write("  --%s: %s\n" % (name.replace("_", "-"), QUERY_LABELS[name]))
        return EXIT_QUERY_OR_ARGUMENT
    if not (args.user_reply or "").strip():
        sys.stderr.write("--user-reply is required, record the user's reply verbatim\n")
        return EXIT_QUERY_OR_ARGUMENT
    record = {"subject": args.subject, "preset": args.preset, "user_reply": args.user_reply}
    # WHY: items outside this request stay null so later steps never act on values nobody chose
    record.update({name: getattr(args, name) if name in needed else None for name in CHOICES})
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, PREFLIGHT_FILENAME), "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
