"""Record the user's pre-generation answers, refuse when a required answer is missing.

WHY: an instruction alone can be skipped silently because generation still succeeds.
     Generation scripts require this record, so a skipped question shows up as exit code 2.
HOW: writes preflight.json into the output directory. Rerun it whenever an answer changes.
     An answer of auto is recorded with the value the agent decided and a one-line reason.
     Later steps read the *_resolved fields, which hold the value in force for both kinds of answer.
"""
import argparse
import enum
import json
import os
import sys

from common import EXIT_OK, EXIT_QUERY_OR_ARGUMENT, PREFLIGHT_FILENAME

AUTO = "auto"
# WHY: the automatic multiplier stays within the fixed choices of the question (1x to 3x)
AUTO_MULTIPLIERS = [1, 2, 3]
SPARE_FINISH_DECISIONS = ["adopted", "all"]


class Subject(str, enum.Enum):
    PERSON = "person"                  # at least one person in the frame, any size
    PRECISE_OBJECT = "precise-object"  # no person, but an object whose part connections identify it
    OTHER = "other"


class Display(str, enum.Enum):
    AVAILABLE = "available"  # a file presentation tool, or a file system the user shares with the agent
    NONE = "none"            # the user cannot open images from this environment


CHOICES = {
    "enhance": ["none", "general", "flat"],
    "trim": ["off", "same", "free", "free-auto"],
    "postfix": ["auto", "bypass", "ask"],
    "face_scope": ["defect", "always", "off"],
    "finger_inpaint": ["off", "on"],
    "candidate_pick": ["auto", "user"],
    "spare_finish": SPARE_FINISH_DECISIONS + [AUTO],
}

QUERY_LABELS = {
    "enhance": "final upscaling (none, general, flat)",
    "trim": "edge trim (off, same = same ratio only, free = free ratio with preview, free-auto = free ratio chosen automatically)",
    "postfix": "defect post-processing (auto, bypass = seed and prompt changes only, ask = ask each time)",
    "face_scope": "face restoration scope (defect = only on face defects, always, off)",
    "finger_inpaint": "finger inpainting (off, on)",
    "candidates": "candidate multiplier (a whole number of 1 or more, or auto)",
    "candidate_pick": "candidate pick (auto = the agent picks, user = the user picks from the contact sheet)",
    "spare_finish": "spare candidate finishing (adopted = adopted images only, all = every candidate, auto)",
}

# WHY: these answers show images to the user and wait for a choice, which needs a way to display images
NEEDS_DISPLAY = {"trim": "free", "finger_inpaint": "on", "candidate_pick": "user"}


def multiplier_answer(text):
    """The candidate multiplier answer: auto or a whole number of 1 or more."""
    if text == AUTO:
        return AUTO
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("use auto or a whole number of 1 or more")
    if value < 1:
        raise argparse.ArgumentTypeError("the multiplier must be 1 or more")
    return value


def flag(name):
    return "--" + name.replace("_", "-")


def display_conflicts(args):
    """Answers that need the user to see images, given while no image can be shown."""
    if args.display != Display.NONE.value:
        return []
    return ["%s %s needs a way to show images, --display is none" % (flag(name), value)
            for name, value in NEEDS_DISPLAY.items() if getattr(args, name) == value]


def auto_problems(args, name):
    """An auto answer must carry the decided value and its reason, a fixed answer carries neither."""
    resolved, reason = getattr(args, name + "_resolved"), getattr(args, name + "_reason")
    if getattr(args, name) != AUTO:
        if resolved is not None or reason is not None:
            return ["%s-resolved and %s-reason go only with %s auto" % (flag(name), flag(name), flag(name))]
        return []
    problems = []
    if resolved is None:
        problems.append("%s auto needs %s-resolved, the value the agent decided" % (flag(name), flag(name)))
    if not (reason or "").strip():
        problems.append("%s auto needs %s-reason, a one-line reason for that value" % (flag(name), flag(name)))
    return problems


def resolved_value(args, name):
    """The value later steps act on: the decided value for auto, the answer itself otherwise."""
    answer = getattr(args, name)
    return getattr(args, name + "_resolved") if answer == AUTO else answer


def required_items(args, multiplier):
    """Items the user must answer for this request."""
    # WHY: generation is 512px or smaller, so enlargement loss always happens, ask upscaling every time
    # WHY: cropping and ratio changes are a matter of taste, ask trimming every time
    # WHY: whether to spend time on extra candidates is a matter of taste, ask the multiplier every time
    items = ["enhance", "trim", "candidates"]
    face_scope = None
    if args.subject in (Subject.PERSON.value, Subject.PRECISE_OBJECT.value):
        items.append("postfix")
    if args.subject == Subject.PERSON.value:
        items.append("face_scope")
        face_scope = args.face_scope
        if args.postfix != "bypass":
            items.append("finger_inpaint")
    # WHY: with one image per target there is nothing to pick from and no spare to finish
    if multiplier is not None and multiplier >= 2:
        if args.display == Display.AVAILABLE.value:
            items.append("candidate_pick")
        if args.enhance != "none" or face_scope == "always":
            items.append("spare_finish")
    return items


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="record pre-generation answers")
    parser.add_argument("--out", required=True, help="output directory that will hold preflight.json")
    parser.add_argument("--subject", required=True, choices=[s.value for s in Subject])
    parser.add_argument("--display", required=True, choices=[d.value for d in Display],
                        help="whether the user can see images from this environment, judged by the agent")
    parser.add_argument("--user-reply", dest="user_reply", help="the user's reply, verbatim")
    # WHY: model choice is a conditional question, record the chosen preset name as given
    parser.add_argument("--preset", help="preset the user chose in the model question, omit when not asked")
    for name, values in CHOICES.items():
        parser.add_argument(flag(name), dest=name, choices=values)
    parser.add_argument("--candidates", type=multiplier_answer, help="candidate multiplier: 1 or more, or auto")
    parser.add_argument("--candidates-resolved", dest="candidates_resolved", type=int, choices=AUTO_MULTIPLIERS,
                        help="with --candidates auto: the multiplier the agent decided")
    parser.add_argument("--candidates-reason", dest="candidates_reason",
                        help="with --candidates auto: one-line reason for the decided multiplier")
    parser.add_argument("--spare-finish-resolved", dest="spare_finish_resolved", choices=SPARE_FINISH_DECISIONS,
                        help="with --spare-finish auto: the choice the agent decided")
    parser.add_argument("--spare-finish-reason", dest="spare_finish_reason",
                        help="with --spare-finish auto: one-line reason for the decided choice")
    return parser.parse_args(argv)


def refuse(header, lines):
    sys.stderr.write(header + "\n")
    for line in lines:
        sys.stderr.write("  %s\n" % line)
    return EXIT_QUERY_OR_ARGUMENT


def main(argv=None):
    args = parse_arguments(argv)
    conflicts = display_conflicts(args)
    if conflicts:
        return refuse("Answers that need images on screen, ask again without them:", conflicts)
    problems = auto_problems(args, "candidates")
    if problems:
        return refuse("Incomplete candidate multiplier record:", problems)
    multiplier = resolved_value(args, "candidates")
    needed = required_items(args, multiplier)
    missing = [name for name in needed if getattr(args, name) is None]
    if missing:
        return refuse("Missing answers, ask the user and rerun:",
                      ["%s: %s" % (flag(name), QUERY_LABELS[name]) for name in missing])
    spare_needed = "spare_finish" in needed
    problems = auto_problems(args, "spare_finish") if spare_needed else []
    if problems:
        return refuse("Incomplete spare candidate finishing record:", problems)
    if not (args.user_reply or "").strip():
        sys.stderr.write("--user-reply is required, record the user's reply verbatim\n")
        return EXIT_QUERY_OR_ARGUMENT
    record = {"subject": args.subject, "display": args.display, "preset": args.preset, "user_reply": args.user_reply}
    # WHY: items outside this request stay null so later steps never act on values nobody chose
    record.update({name: getattr(args, name) if name in needed else None for name in CHOICES})
    record.update({
        "candidates": args.candidates,
        "candidates_resolved": multiplier,
        "candidates_reason": args.candidates_reason,
        "spare_finish_resolved": resolved_value(args, "spare_finish") if spare_needed else None,
        "spare_finish_reason": args.spare_finish_reason if spare_needed else None,
    })
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, PREFLIGHT_FILENAME), "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
