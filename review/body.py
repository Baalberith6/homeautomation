"""The form of a pull request body: the change line, then five fields that the owner reads at a glance.

Usage, from the repo root, before `gh pr create`:

    python3 -m review.body BODY.md        (or "-" for stdin)

It prints each problem and exits 1, or prints "PR body: ok" and exits 0. The review agent runs the same
check (review/report.py); a problem is a finding of kind "rule".

The body:

    **Change NNN** (<path>) · `../kb/work/NNN-<slug>/<file>` · approved <date>

    **Owner must do:** <the action before the merge or the deploy, or "nothing">

    **What:** <what the PR changes>

    **Tested:** <the counts and the commits>. Results: <file and section>

    **Not covered:** <what the tests do not see, or "nothing">

    **Revert:** <one line>

Each label is bold, and each field is its own paragraph: GitHub shows plain lines with no blank line between
them as one block of text. `Owner must do` is the first field. A field has one or two short sentences, 240
characters at most. No table and no code block: the evidence stays in the change folder. Decision 2026-11-17
in ../kb/decisions.md; the form is change 039 (../kb/work/039-pr-body-readable-form/change.md).
"""
import re
import sys

LABELS = ("What:", "Owner must do:", "Tested:", "Not covered:", "Revert:")
FIRST = ("Change ", "No change folder")  # the first line names the change, or says that there is none
MAX_LINES = 12
MAX_FIELD = 240   # characters of one field, without the label
OWNER = "Owner must do:"
ATTRIBUTION = "Generated with [Claude Code]"


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip() and ATTRIBUTION not in line]


def _labelled(text):
    """[(line number, label, bold, text)] for the first line of each label, in the order of the body."""
    found = []
    for number, raw in enumerate((text or "").splitlines()):
        line = raw.strip()
        if ATTRIBUTION in line:
            continue
        for label in LABELS:
            m = re.match(r"^(\*{0,2})" + re.escape(label) + r"(\*{0,2})\s*(.*)$", line)
            if m and label not in [row[1] for row in found]:
                found.append((number, label, m.group(1) == m.group(2) == "**", m.group(3).strip()))
    return found


def fields(text):
    """{label: text} for each labelled line of the body, without the bold marks of the label."""
    return {label: value for _, label, _, value in _labelled(text)}


def _names(labels):
    return ", ".join(f"`{label}`" for label in labels)


def _form(text):
    """The problems of the readable form (change 039): bold labels, one paragraph for each field, the
    owner action first, short fields."""
    rows, raw, out = _labelled(text), (text or "").splitlines(), []
    plain = [label for _, label, bold, _ in rows if not bold]
    if plain:
        out.append(f"Not bold: {_names(plain)}. Write each label as `**{plain[0]}**`.")
    joined = [after[1] for before, after in zip(rows, rows[1:])
              if all(line.strip() for line in raw[before[0] + 1:after[0]])]
    if joined:
        out.append(f"No blank line before {_names(joined)}. Each field is its own paragraph.")
    order = [label for _, label, _, _ in rows]
    if OWNER in order and order[0] != OWNER:
        out.append(f"The owner action is the first field. Found before `{OWNER}`: {_names(order[:order.index(OWNER)])}.")
    for _, label, _, value in rows:
        if len(value) > MAX_FIELD:
            out.append(f"The field `{label}` has {len(value)} characters; the limit is {MAX_FIELD}. "
                       "Write one or two short sentences.")
    return out


def problems(text):
    """The reasons why the body does not have the form. An empty list means that it is correct."""
    lines, found, out = _lines(text), fields(text), []
    if not lines or not lines[0].lstrip("*").startswith(FIRST):
        out.append("The first line must name the change: \"**Change NNN** (<path>) · <file> · approved <date>\", "
                   "or start with \"No change folder\".")
    for label in LABELS:
        if label not in found:
            out.append(f"The line `{label}` is missing.")
        elif not found[label]:
            out.append(f"The line `{label}` is empty. Write the text, or \"nothing\".")
    if len(lines) > MAX_LINES:
        out.append(f"The body has {len(lines)} lines; the limit is {MAX_LINES}.")
    if any(line.startswith("|") for line in lines):
        out.append("The body has a table. Keep it in the change folder and point to it.")
    if any(line.startswith("```") for line in lines):
        out.append("The body has a code block. Keep the output in the Results of the change folder.")
    return out + _form(text)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__)
        return 2
    if args[0] == "-":
        text = sys.stdin.read()
    else:
        with open(args[0]) as fh:
            text = fh.read()
    found = problems(text)
    for problem in found:
        print(problem)
    if not found:
        print("PR body: ok")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
