"""The form of a pull request body: six labelled lines, with the owner action in a fixed place.

Usage, from the repo root, before `gh pr create`:

    python3 -m review.body BODY.md        (or "-" for stdin)

It prints each problem and exits 1, or prints "PR body: ok" and exits 0. The review agent runs the same
check (review/report.py); a problem is a finding of kind "rule".

The body:

    Change NNN (<path>): ../kb/work/NNN-<slug>/<file>, approved <date>.
    What: <one or two sentences>
    Owner must do: <the action before the merge or the deploy, or "nothing">
    Tested: <one line with the counts and the commits>. Results: <file and section>
    Not covered: <what the tests do not see, or "nothing">
    Revert: <one line>

No table and no code block: the evidence stays in the change folder. Decision 2026-11-17 in
../kb/decisions.md.
"""
import re
import sys

LABELS = ("What:", "Owner must do:", "Tested:", "Not covered:", "Revert:")
MAX_LINES = 12
ATTRIBUTION = "Generated with [Claude Code]"


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip() and ATTRIBUTION not in line]


def fields(text):
    """{label: text} for each labelled line of the body. A label can be bold."""
    found = {}
    for line in _lines(text):
        for label in LABELS:
            m = re.match(r"^\*{0,2}" + re.escape(label) + r"\*{0,2}\s*(.*)$", line)
            if m and label not in found:
                found[label] = m.group(1).strip()
    return found


def problems(text):
    """The reasons why the body does not have the form. An empty list means that it is correct."""
    lines, found, out = _lines(text), fields(text), []
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
    return out


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
