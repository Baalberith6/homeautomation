"""The PR comment of the review agent: the decision first, then one gate per line.

Usage, from the repo root (the agent runs it, review/reviewer.md step 10):

    python3 -m review.report --pr N --change-dir ../kb/work/NNN-slug --out ~/homeautomation/review-out/prN \
        --author LOGIN [--cross-repo] [--post]

--out holds risk.json, findings.json, junit.xml, pytest.txt, flake8.txt, collect-head.txt, collect-base.txt,
and, when the agent wrote them, pr.json (the PR with its body), drift.json and, after a dashboard change,
preview.json and the PNG files. The command prints the comment, or with --post uploads the images to a
secret gist, writes the one comment of the agent on the PR (it replaces the last one), sets the label
risk:low or risk:high, and prints a JSON summary with the decision.

The comment: a heading with the decision, the level, the commit and the round, then the gates Approval,
Drift, Findings, Checks, Tests and, for a dashboard change, Screenshots. Each gate is one <details> line.
A gate that waits for the owner or fails is open; a green gate is closed.

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.7 and 2.8. The form of the comment, the checks of
a change.md (change 035), the drift from the intent and the limit of three rounds: decision 2026-11-17 in
../kb/decisions.md.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from review import body as pr_body
from review import risk

MARKER = "<!-- pr-reviewer -->"
GIST_MARK = re.compile(r"<!-- gist:([0-9a-f]+) -->")
ROUND_MARK = re.compile(r"<!-- round:(\d+) head:([0-9a-f]+) -->")
REPO = risk.REPO
MAX_BODY = 60000
MAX_RAW = 5000    # characters of test output, and only when a test fails
MAX_TEXT = 200    # characters of one finding, reason or drift row
MAX_GAPS = 3
MAX_ROUNDS = 3
OK, WAIT, BAD, WARN = "✅", "⏳", "❌", "⚠️"
HEADS = {"auto-merge": "Ready", "wait-owner": "Waiting for the owner", "fix-findings": "Not ready",
         "refuse": "Refused"}
NEXT = {
    "auto-merge": "Next: the session turns on auto-merge; GitHub merges after CI.",
    "wait-owner": "Next: **the owner merges** this commit.",
    "fix-findings": "Next: the session fixes the findings or the failed tests and runs the review again.",
    "refuse": "Next: nothing. The agent works only on PRs of the owner from a branch of this repo.",
}
STUCK = "Next: **the owner decides on the approach.** Three rounds did not close the findings."
RESULT = {"pass": OK + " pass", "recorded": OK + " recorded pass", "fail": BAD + " fail",
          "not proven": WARN + " not proven"}
CHECKS_HEADING = r"^##\s+\d+\.\s+.*[Aa]cceptance checks"
TESTS_HEADING = r"^##\s+(?:\d+\.\s+)?Tests(?: this change adds or extends)?\s*$"
RESULTS_HEADING = r"^##\s+(?:\d+\.\s+)?Results\s*$"
NUMBERS = re.compile(r"^(\d+(?:\s*[–-]\s*\d+)?(?:\s*,\s*\d+(?:\s*[–-]\s*\d+)?)*)(?:\s+[^\d\s].*)?$")
TEST_ID = re.compile(r"`([^`]*::[^`]*)`")
ANY_FILE = "…"
VERDICT = re.compile(r"(?i)^\**\s*(pass|passed|fail|failed)\b")
OPEN_UNTIL = re.compile(r"(?i)^open until (.+)")
CHECK_TABLE = re.compile(r"(?i)check|§")       # the first header cell of a table of checks
SEPARATOR = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
DRIFT_KINDS = ("outcome", "constraint", "outside")


def _section(md, heading_re):
    """The text under the first heading that matches, up to the next heading of the same level or higher."""
    lines = md.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(#+)\s", line)
        if m and re.match(heading_re, line):
            level, out = len(m.group(1)), []
            for nxt in lines[i + 1:]:
                n = re.match(r"^(#+)\s", nxt)
                if n and len(n.group(1)) <= level:
                    break
                out.append(nxt)
            return "\n".join(out)
    return ""


def acceptance_checks(md):
    """The numbered items of "## 8. Acceptance checks" (spec.md) or "## 2. Outcome and acceptance checks"
    (change.md): [(number, text)]."""
    checks = []
    for line in _section(md, CHECKS_HEADING).splitlines():
        m = re.match(r"^(\d+)\.\s+(.*)", line)
        if m:
            checks.append((int(m.group(1)), m.group(2).strip()))
        elif checks and line.startswith("   ") and line.strip():
            n, text = checks[-1]
            checks[-1] = (n, text + " " + line.strip())
    return checks


def numbers(cell):
    """The check numbers of a table cell: "2, 4-6" gives [2, 4, 5, 6]. A range can use "–"."""
    out = []
    for first, last in re.findall(r"(\d+)(?:\s*[–-]\s*(\d+))?", cell):
        out += list(range(int(first), int(last) + 1)) if last else [int(first)]
    return out


def _cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _test_id(cell):
    """The pytest id of a table cell. The cell can hold a note after the id. An id that starts with "…::"
    or "...::" names no file."""
    m = TEST_ID.search(cell)
    name = (m.group(1) if m else cell.strip().strip("`")).strip()
    if name.startswith(("…", "...")):
        return ANY_FILE + "::" + name.split("::")[-1]
    return name if name.startswith("tests/") else "tests/" + name


def test_map(md):
    """{test id: [check numbers]} from the table "Tests this change adds or extends" (test.md) or
    "5. Tests" (change.md). A row with no pytest id, for example a command, gives nothing."""
    found = {}
    for line in _section(md, TESTS_HEADING).splitlines():
        cells = _cells(line)
        if len(cells) < 2 or "::" not in cells[0]:
            continue
        found[_test_id(cells[0])] = numbers(cells[-1])
    return found


def recorded(md):
    """{check: (state, when)} from the tables of checks in the Results.

    A table of checks has "Check" or "§" in its first header cell; a table of steps or of tests is not
    read. The first cell of a row starts with the check numbers; a word can follow them. The verdict is
    the last cell: it starts with "pass" or "fail", or says "open until <date or run>". A row with other
    words records nothing. In one run a fail stays a fail; a later run ("### ...") wins over an earlier
    run."""
    found = {}
    for block in re.split(r"(?m)^###\s", _section(md, RESULTS_HEADING)):
        run, lines, reading = {}, block.splitlines(), False
        for i, line in enumerate(lines):
            if not line.strip().startswith("|"):
                reading = False
                continue
            if i + 1 < len(lines) and SEPARATOR.match(lines[i + 1]):
                reading = bool(CHECK_TABLE.search(_cells(line)[0]))
                continue
            cells = _cells(line)
            first = NUMBERS.match(cells[0]) if reading and len(cells) > 1 else None
            if not first:
                continue
            until, verdict = OPEN_UNTIL.match(cells[-1]), VERDICT.match(cells[-1])
            if until:
                state = ("open", until.group(1).strip())
            elif verdict:
                state = ("fail" if verdict.group(1).lower().startswith("fail") else "pass", None)
            else:
                state = None
            for n in numbers(first.group(1)):
                if not run.get(n) or run[n][0] != "fail":
                    run[n] = state
        found.update(run)
    return {n: state for n, state in found.items() if state}


def _junit_id(classname, name):
    parts = classname.split(".")
    files = [p for p in parts if not p[:1].isupper()]
    classes = [p for p in parts if p[:1].isupper()]
    return "/".join(files) + ".py::" + "".join(c + "::" for c in classes) + name


def junit_results(xml_text):
    """{test id: "pass" | "fail" | "skip"} from a pytest JUnit file. A test with any failed entry fails."""
    results = {}
    for case in ET.fromstring(xml_text).iter("testcase"):
        tid = _junit_id(case.get("classname", ""), case.get("name", ""))
        if case.find("failure") is not None or case.find("error") is not None:
            state = "fail"
        elif case.find("skipped") is not None:
            state = "skip"
        else:
            state = "pass"
        if results.get(tid) != "fail":
            results[tid] = state
    return results


def collected(text):
    """The test ids of `pytest --collect-only -q`."""
    return {line.strip() for line in text.splitlines() if "::" in line}


def _matches(mapped, junit):
    """The JUnit ids of one test of the table. The table may leave out the class."""
    parts = mapped.split("::")
    if parts[0] == ANY_FILE:
        return [t for t in junit if re.sub(r"\[.*\]$", "", t.split("::")[-1]) == parts[-1]]
    found = [t for t in junit if t == mapped or re.sub(r"\[.*\]$", "", t) == mapped]
    if found or len(parts) > 2:  # an id with a class matches only that class
        return found
    return [t for t in junit if t.split("::")[0] == parts[0] and re.sub(r"\[.*\]$", "", t.split("::")[-1]) == parts[-1]]


def _cut(text, size=MAX_TEXT):
    text = " ".join(str(text).split())
    return text if len(text) <= size else text[:size - 1].rstrip() + "…"


def _short(text, size=120):
    return _cut(text, size).replace("|", "\\|")


def check_rows(spec_md, test_md, junit):
    """One dict per acceptance check: n, text, tests, state, when.

    The state: "fail" (a test of the check fails, or the Results record a fail), "open" (the Results say
    "open until"), "pass" (every test of the check passes in this run), "recorded" (no test of this run
    proves it, and the Results record a pass), or "not proven"."""
    tmap, results = test_map(test_md), recorded(test_md)
    rows = []
    for n, text in acceptance_checks(spec_md):
        tests = [t for t, refs in tmap.items() if n in refs]
        states = [junit[j] for t in tests for j in _matches(t, junit)]
        noted, when = results.get(n, (None, None))
        if "fail" in states or noted == "fail":
            state = "fail"
        elif noted == "open":
            state = "open"
        elif states and all(s == "pass" for s in states) and all(_matches(t, junit) for t in tests):
            state = "pass"
        elif noted == "pass":
            state = "recorded"
        else:
            state = "not proven"
        rows.append({"n": n, "text": text, "tests": tests, "state": state, "when": when})
    return rows


def checks_summary(rows):
    """(icon, text, open) for the Checks gate."""
    if not rows:
        return WARN, "no acceptance checks found", False
    count = {s: sum(1 for r in rows if r["state"] == s) for s in ("pass", "recorded", "open", "fail", "not proven")}
    text = f"{count['pass'] + count['recorded']} of {len(rows)} proven"
    for state, label in (("open", "open"), ("not proven", "not proven"), ("fail", "failed")):
        if count[state]:
            text += f", {count[state]} {label}"
    icon = BAD if count["fail"] else WARN if count["not proven"] else WAIT if count["open"] else OK
    return icon, text, bool(count["fail"])  # "not proven" is a warning in the line; only a fail opens the gate


def checks_md(rows):
    lines = ["| Check | What | Proven by | Result |", "|---|---|---|---|"]
    for row in rows:
        names = [t.split("::")[-1] for t in row["tests"]]
        shown = ", ".join(f"`{x}`" for x in names[:3]) + (f" +{len(names) - 3} more" if len(names) > 3 else "")
        result = f"{WAIT} open until {row['when']}" if row["state"] == "open" else RESULT[row["state"]]
        if row["state"] == "recorded":
            shown = shown or "the Results of the change folder"
        lines.append(f"| {row['n']} | {_short(row['text'])} | {shown or '—'} | {result} |")
    not_proven = [str(r["n"]) for r in rows if r["state"] == "not proven"]
    lines += ["", "Not proven: " + (", ".join(not_proven) if not_proven else "none")]
    if any(r["state"] == "recorded" for r in rows):
        lines.append("A recorded pass is a result that the change folder states. No test of this run proves it.")
    return "\n".join(lines)


def lint_failed(flake8_text):
    """True if the flake8 gate found something. A clean run prints "0" (the --count)."""
    return (flake8_text or "").strip() not in ("", "0")


def tests_summary(junit, base_ids, head_ids, lint=""):
    """(icon, text, open) for the Tests gate."""
    if not junit:
        return BAD, "no test result", True
    passed = sum(1 for s in junit.values() if s == "pass")
    failed = sum(1 for s in junit.values() if s == "fail")
    if failed:
        return BAD, f"{failed} failed, {passed} passed", True
    if lint_failed(lint):
        return BAD, f"{passed} passed, flake8 found errors", True
    return OK, f"{passed} passed ({len(head_ids) - len(base_ids):+d} vs main)", False


def tests_md(junit, base_ids, head_ids, risk_result):
    passed = sum(1 for s in junit.values() if s == "pass")
    failed = sorted(t for t, s in junit.items() if s == "fail")
    lines = [f"**{passed} passed ({len(head_ids) - len(base_ids):+d} vs main)**", ""]
    if failed:
        lines.append("- Failed: " + ", ".join(f"`{t}`" for t in failed))
    for label, key in (("New tests", "new_tests"), ("Edited tests", "edited_tests"),
                       ("Deleted tests", "deleted_tests")):
        names = risk_result.get(key) or []
        lines.append(f"- {label}: " + (", ".join(f"`{t}`" for t in names) if names else "none"))
    return "\n".join(lines)


def _where(item):
    if item.get("file") and item.get("line"):
        return f"`{item['file']}:{item['line']}`"
    return f"`{item['file']}`" if item.get("file") else ""


def _drift_parts(drift):
    drift = [d for d in (drift or []) if isinstance(d, dict)]
    outcomes = [d for d in drift if d.get("kind") == "outcome"]
    constraints = [d for d in drift if d.get("kind") == "constraint"]
    outside = [d for d in drift if d.get("kind") == "outside"]
    not_met = [d for d in outcomes if d.get("state") != "met"]
    broken = [d for d in constraints if d.get("state") != "kept"]
    return outcomes, constraints, outside, not_met, broken, [d for d in outside if not d.get("by_spec")]


def drift_measured(drift):
    """True if drift.json has a row for an outcome. A file with no such row measures nothing."""
    return bool(_drift_parts(drift)[0])


def _drift_unknown(drift):
    return [d for d in (drift or []) if not isinstance(d, dict) or d.get("kind") not in DRIFT_KINDS]


def drift_summary(drift, required=False):
    """(icon, text, open) for the Drift gate. "Not measured" is never a green mark. It opens the gate
    when the PR has a change folder (required), because the PR then waits for the owner."""
    outcomes, _, _, not_met, broken, extra = _drift_parts(drift)
    unknown = _drift_unknown(drift)
    if not outcomes:
        text = "not measured" + (": <code>drift.json</code> has no outcome row" if drift else "")
        if extra:
            text += f", {len(extra)} item{'s' if len(extra) > 1 else ''} outside the intent"
        return WARN, text, bool(required or extra)
    text = f"{len(outcomes) - len(not_met)} of {len(outcomes)} outcomes met"
    if broken:
        text += f", {len(broken)} constraint{'s' if len(broken) > 1 else ''} broken"
    text += (f", {len(extra)} item{'s' if len(extra) > 1 else ''} outside the intent" if extra
             else ", nothing outside the intent")
    if unknown:
        text += f", {len(unknown)} row{'s' if len(unknown) > 1 else ''} of an unknown kind"
    icon = BAD if not_met or broken else WARN if extra or unknown else OK
    return icon, text, bool(not_met or broken or extra)


def drift_md(drift):
    if not drift:
        return "The review wrote no `drift.json`: the PR has no change folder, or the agent did not compare."
    outcomes, constraints, outside, _, _, _ = _drift_parts(drift)
    lines = []
    for d in outcomes:
        state = d.get("state", "not met")
        lines.append(f"- {OK if state == 'met' else BAD} {state} — outcome {d.get('n', '?')}: "
                     f"{_cut(d.get('text', ''))} {_where(d)}".rstrip())
    for d in constraints:
        state = d.get("state", "broken")
        lines.append(f"- {OK if state == 'kept' else BAD} {state} — constraint: {_cut(d.get('text', ''))} "
                     f"{_where(d)}".rstrip())
    for d in outside:
        label = "added by the spec" if d.get("by_spec") else f"{WARN} outside the intent"
        lines.append(f"- {label} — {_cut(d.get('text', ''))} {_where(d)}".rstrip())
    for d in _drift_unknown(drift):
        kind = d.get("kind") if isinstance(d, dict) else d
        lines.append(f"- {WARN} unknown kind `{_cut(kind, 40)}` — the tool did not read this row")
    if not outcomes:
        lines.append(f"- {WARN} no row of kind `outcome`: the drift is not measured")
    return "\n".join(lines)


def _drift_gate(drift, required=False):
    icon, summary, opened = drift_summary(drift, required)
    return _gate(icon, "Drift", summary, drift_md(drift), opened=opened)


def decide(level, open_findings, tests_failed, author, cross_repo, drift=None, round_no=1, failed_checks=0,
           drift_required=False):
    """What the session does with the PR: the rules of review/risk.py, and these.

    A failed acceptance check, an outcome that is not met and a broken constraint count as open findings.
    A PR that would merge by itself waits for the owner when the diff has an item outside the intent, or
    when the PR has a change folder (drift_required) and the drift is not measured. After MAX_ROUNDS
    rounds with open findings the owner decides on the approach."""
    _, _, _, not_met, broken, extra = _drift_parts(drift)
    blocking = open_findings + failed_checks + len(not_met) + len(broken)
    decision = risk.decide(level, blocking, tests_failed, author, cross_repo)
    if decision == "auto-merge" and (extra or (drift_required and not drift_measured(drift))):
        return "wait-owner"
    if decision == "fix-findings" and round_no > MAX_ROUNDS:
        return "wait-owner"
    return decision


def round_number(previous, head):
    """The round of this run. A round is one try to close the findings: the count goes up when the last
    comment said "Not ready" and the head commit is new. A run on the same head, or a new commit after a
    clean review (for example the sync-back of a dashboard), stays in the round."""
    m = ROUND_MARK.search(previous or "")
    if not m:
        return 1
    last = int(m.group(1))
    if m.group(2) == head or not re.search(r"(?m)^## " + re.escape(HEADS["fix-findings"]), previous):
        return last
    return last + 1


def body_findings(text):
    """The problems of the PR body (review/body.py) as findings of kind "rule". None: the body is not known."""
    if text is None:
        return []
    return [{"file": "PR body", "kind": "rule", "text": p} for p in pr_body.problems(text)]


def approval(change_dir):
    """One line: which files of the change folder the owner approved, from their front matter."""
    if not change_dir or not os.path.isdir(change_dir):
        return "no change folder"
    names = ["change.md"] if os.path.exists(os.path.join(change_dir, "change.md")) else \
        ["intent.md", "spec.md", "plan.md", "test.md"]
    parts = []
    for name in names:
        text = _read(os.path.join(change_dir, name), None)
        if text is None:
            parts.append(f"`{name}` is missing")
            continue
        by = re.search(r"(?m)^approved_by:[ \t]*(\S.*)$", text)
        on = re.search(r"(?m)^approved_on:[ \t]*(\S.*)$", text)
        parts.append(f"`{name}` approved by {by.group(1).strip()} on {on.group(1).strip()}" if by and on
                     else f"`{name}` has no approval")
    return "; ".join(parts)


def _images_md(images):
    out = []
    for panel in images.get("panels", []):
        before = f"![before]({panel['before']})" if panel.get("before") else "_absent_"
        after = f"![after]({panel['after']})" if panel.get("after") else "_absent_"
        out += [f"**Panel {panel['id']}**", "", "| Before | After |", "|---|---|", f"| {before} | {after} |", ""]
    for page in images.get("pages") or []:
        out += [f"**Full page — {page.get('label', '')}**", "", "| Before | After |", "|---|---|",
                f"| ![before]({page.get('before')}) | ![after]({page.get('after')}) |", ""]
    for warning in images.get("warnings", []):
        out.append(f"> {WARN} {warning}")
    return "\n".join(out).rstrip()


def _gate(icon, name, summary, inner, opened=False):
    """One gate: a line that expands. The summary is HTML, because GitHub reads no markdown inside it."""
    return (f"<details{' open' if opened else ''}><summary>{icon} <b>{name}</b> — {summary}</summary>\n\n"
            + inner.strip() + "\n\n</details>")


def _stuck(data):
    """True if the decision is "wait-owner" while something still stops the merge: the rounds are used up.
    The owner then decides on the approach; there is nothing to merge."""
    _, _, _, not_met, broken, _ = _drift_parts(data.get("drift"))
    blocked = (any(f.get("kind") != "gap" for f in data["findings"]) or not_met or broken
               or any(r["state"] == "fail" for r in data["rows"])
               or tests_summary(data["junit"], data["base_ids"], data["head_ids"], data.get("lint", ""))[2])
    return data["decision"] == "wait-owner" and bool(blocked)


def _approval_gate(data, level, head, extra):
    decision, fields, number = data["decision"], data.get("body"), data.get("pr", "N")
    stuck = _stuck(data)
    summary = {"auto-merge": (OK, "not needed: low risk"),
               "wait-owner": (WAIT, f"owner: merge <code>{head[:7]}</code>"),
               "fix-findings": (WAIT, "after the findings are closed"),
               "refuse": (BAD, "refused: not a PR of the owner from this repo")}.get(decision, (WARN, decision))
    if stuck:
        summary = (WAIT, "owner: decide on the approach")
    reasons = data["risk"].get("reasons") or []
    rules = [r for r in reasons if not r.startswith("Agent: ")]
    if fields is None:
        action = "not read: `pr.json` is missing or has no body"
    else:
        action = _cut(fields["Owner must do:"], 400) if fields.get("Owner must do:") else "not stated in the PR body"
    lines = ["- **Owner must do:** " + action]
    lines.append(f"- **Why {level}:** " + ("; ".join(_cut(r) for r in rules) if rules else "no rule fired"))
    lines += ["- **Raised by the agent:** " + _cut(r[len("Agent: "):]) for r in reasons if r.startswith("Agent: ")]
    if extra and level == "low":
        lines.append(f"- **Why it waits:** {len(extra)} item{'s' if len(extra) > 1 else ''} outside the intent "
                     "(the Drift gate).")
    if data.get("drift_required") and not drift_measured(data.get("drift")) and level == "low":
        lines.append("- **Why it waits:** the drift from the intent is not measured (the Drift gate).")
    if stuck:
        lines.append(f"- **Three rounds** did not close the findings (round {data.get('round', 1)}). "
                     "The owner decides on the approach. There is nothing to merge.")
    lines.append("- **Change:** " + data.get("approval", "no change folder"))
    if decision == "wait-owner" and not stuck:
        lines.append(f"- **Merge:** `gh pr merge {number} --merge --match-head-commit {head}`. "
                     "A new commit needs a new word of the owner.")
    return _gate(summary[0], "Approval", summary[1], "\n".join(lines), opened=decision == "wait-owner")


def _findings_gate(data):
    number = data.get("pr", "N")
    blocking = [f for f in data["findings"] if f.get("kind") != "gap"]
    gaps = [f for f in data["findings"] if f.get("kind") == "gap"]
    summary = f"{len(blocking)} blocking" if blocking else "none blocking"
    if gaps:
        summary += f", {len(gaps)} gap{'s' if len(gaps) > 1 else ''}"
    lines = [f"- {_where(f)} ({f.get('kind', '?')}) {_cut(f.get('text', ''))}".replace("-  (", "- (")
             for f in blocking]
    if gaps:
        lines += ["", "**The checks do not cover:**", ""] + [f"- {_cut(f.get('text', ''))}" for f in gaps[:MAX_GAPS]]
        if len(gaps) > MAX_GAPS:
            lines.append(f"- {len(gaps) - MAX_GAPS} more in `review-out/pr{number}/findings.json`")
    return _gate(BAD if blocking else OK, "Findings", summary, "\n".join(lines) or "None.", opened=bool(blocking))


def _tests_gate(data):
    lint = data.get("lint", "")
    icon, summary, opened = tests_summary(data["junit"], data["base_ids"], data["head_ids"], lint)
    inner = tests_md(data["junit"], data["base_ids"], data["head_ids"], data["risk"])
    if opened:
        shown = []
        if not data["junit"] or any(s == "fail" for s in data["junit"].values()):
            shown.append(data.get("raw") or "")
        if lint_failed(lint):
            shown.append("$ flake8\n" + lint.strip())
        raw = "\n".join(shown)
        inner += "\n\n````\n" + raw[:MAX_RAW] + "\n````\n"
        if len(raw) > MAX_RAW:
            inner += (f"\nThe output is cut. The full output: `review-out/pr{data.get('pr', 'N')}/pytest.txt` "
                      "and `flake8.txt`.")
    return _gate(icon, "Tests", summary, inner, opened=opened)


def comment(data):
    """The comment. data: risk, findings (no kind "risk"), images, rows, junit, base_ids, head_ids, raw,
    lint (the flake8 output), decision, drift, drift_required, body (the fields of the PR body, or None if
    the body is not known), round, gist_id, pr, approval."""
    risk_result, decision = data["risk"], data["decision"]
    level = risk_result.get("level", "high")
    head = risk_result.get("head") or "0000000"
    round_no = data.get("round", 1)
    extra = _drift_parts(data.get("drift"))[5]
    parts = [MARKER]
    if data.get("gist_id"):
        parts.append(f"<!-- gist:{data['gist_id']} -->")
    parts += [f"<!-- round:{round_no} head:{head} -->",
              f"## {HEADS.get(decision, decision)} — {level.upper()}, `{head[:7]}`, round {round_no} of {MAX_ROUNDS}",
              "", STUCK if _stuck(data) else NEXT.get(decision, decision), "",
              _approval_gate(data, level, head, extra),
              _drift_gate(data.get("drift"), data.get("drift_required", False)),
              _findings_gate(data)]
    icon, summary, opened = checks_summary(data["rows"])
    parts.append(_gate(icon, "Checks", summary, checks_md(data["rows"]) if data["rows"]
                       else "The change folder has no acceptance checks, or the PR has no change folder.",
                       opened=opened))
    parts.append(_tests_gate(data))
    images = data.get("images")
    if images is not None:
        count = f"{len(images.get('panels', []))} panels, {len(images.get('pages') or [])} pages"
        parts.append(_gate(WARN if images.get("warnings") else "🖼️", "Screenshots", count, _images_md(images),
                           opened=True))
    text = "\n".join(parts) + "\n"
    return text if len(text) <= MAX_BODY else text[:MAX_BODY] + "\n… (cut)\n"


def upload(pr, paths, head, gist_id=None, owner="matejpristak", run=subprocess.run):
    """Put the PNG files into the secret gist of the PR. Returns (gist id, {file name: raw URL}).

    The files are named <head sha 7>-<name>, so a new run never shows an image from a cache.
    Nothing is written to this repo.
    """
    tmp = tempfile.mkdtemp(prefix="pr-reviewer-")
    try:
        if gist_id is None:
            readme = os.path.join(tmp, "README.md")
            with open(readme, "w") as fh:
                fh.write(f"Screenshots for {REPO} PR {pr}, written by the pr-reviewer agent (change 032).\n")
            out = run(["gh", "gist", "create", "--desc", f"{REPO} PR {pr} screenshots", readme],
                      cwd=tmp, capture_output=True, text=True, check=True).stdout
            gist_id = out.strip().rstrip("/").split("/")[-1]
        clone = os.path.join(tmp, "gist")
        auth = ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
        run(["git"] + auth + ["clone", "-q", f"https://gist.github.com/{gist_id}.git", clone],
            cwd=tmp, capture_output=True, text=True, check=True)
        for name in os.listdir(clone):
            if name.endswith(".png"):
                os.remove(os.path.join(clone, name))
        urls = {}
        for path in paths:
            name = os.path.basename(path)
            target = f"{head[:7]}-{name}"
            shutil.copyfile(path, os.path.join(clone, target))
            urls[name] = f"https://gist.githubusercontent.com/{owner}/{gist_id}/raw/{target}"
        git = ["git", "-C", clone, "-c", "user.name=pr-reviewer", "-c", "user.email=pr-reviewer@localhost"]
        run(git + ["add", "-A"], cwd=tmp, capture_output=True, text=True, check=True)
        run(git + ["commit", "-q", "-m", f"PR {pr} at {head[:7]}"], cwd=tmp, capture_output=True, text=True,
            check=True)
        run(["git", "-C", clone] + auth + ["push", "-q"], cwd=tmp, capture_output=True, text=True, check=True)
        return gist_id, urls
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def find_comment(pr, run=subprocess.run):
    out = run(["gh", "api", f"repos/{REPO}/issues/{pr}/comments", "--paginate", "--jq",
               f'.[] | select(.body | startswith("{MARKER}")) | .id'],
              capture_output=True, text=True, check=True).stdout.split()
    return out[-1] if out else None


def post(pr, body, run=subprocess.run):
    """Replace the comment of the agent on the PR, or write the first one. Returns its URL."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(body)
        path = fh.name
    try:
        cid = find_comment(pr, run=run)
        if cid:
            cmd = ["gh", "api", "-X", "PATCH", f"repos/{REPO}/issues/comments/{cid}"]
        else:
            cmd = ["gh", "api", "-X", "POST", f"repos/{REPO}/issues/{pr}/comments"]
        return run(cmd + ["-F", f"body=@{path}", "--jq", ".html_url"],
                   capture_output=True, text=True, check=True).stdout.strip()
    finally:
        os.remove(path)


def set_label(pr, level, run=subprocess.run):
    other = "risk:high" if level == "low" else "risk:low"
    run(["gh", "api", "-X", "POST", f"repos/{REPO}/issues/{pr}/labels", "-f", f"labels[]=risk:{level}"],
        capture_output=True, text=True, check=True)
    run(["gh", "api", "-X", "DELETE", f"repos/{REPO}/issues/{pr}/labels/{other}"], capture_output=True, text=True)


def _read(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path) as fh:
        return fh.read()


def _json(path, default):
    """The JSON of a file, or the default if the file is missing, empty or not JSON."""
    try:
        return json.loads(_read(path, ""))
    except ValueError:
        return default


def _raw(pytest_text):
    """The test output for a failed run: from the first failure."""
    at = re.search(r"(?m)^=+ (FAILURES|ERRORS) =+$", pytest_text)
    return "$ pytest\n" + (pytest_text[at.start():] if at else pytest_text)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write the PR comment of the review agent (change 032).")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--change-dir", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--cross-repo", action="store_true")
    parser.add_argument("--post", action="store_true")
    args = parser.parse_args(argv)
    out = os.path.expanduser(args.out)

    risk_result = _json(os.path.join(out, "risk.json"), {"level": "high", "reasons": ["no risk.json"]})
    pr = _json(os.path.join(out, "pr.json"), None)
    body_text = pr.get("body") if isinstance(pr, dict) else None
    findings = _json(os.path.join(out, "findings.json"), []) + body_findings(body_text)
    raised = [f for f in findings if f.get("kind") == "risk"]
    shown = [f for f in findings if f.get("kind") != "risk"]
    open_findings = [f for f in shown if f.get("kind") != "gap"]
    reasons = list(risk_result.get("reasons") or []) + [f"Agent: {f.get('text', '')}" for f in raised]
    preview = _json(os.path.join(out, "preview.json"), None)
    if preview and preview.get("failed"):
        reasons.append(f"Screenshots: {preview['failed']}")
    level = "high" if reasons else risk_result.get("level", "high")
    risk_result = dict(risk_result, level=level, reasons=reasons)
    drift = _json(os.path.join(out, "drift.json"), None)
    drift = drift if isinstance(drift, list) else None
    previous = _read(os.path.join(out, "comment.md"))
    round_no = round_number(previous, risk_result.get("head") or "0000000")

    junit_text = _read(os.path.join(out, "junit.xml"))
    junit = junit_results(junit_text) if junit_text else {}
    lint = _read(os.path.join(out, "flake8.txt"))
    tests_failed = not junit or any(s == "fail" for s in junit.values()) or lint_failed(lint)

    change_dir = os.path.expanduser(args.change_dir) if args.change_dir else None
    spec_md = test_md = ""
    if change_dir and os.path.exists(os.path.join(change_dir, "spec.md")):
        spec_md, test_md = _read(os.path.join(change_dir, "spec.md")), _read(os.path.join(change_dir, "test.md"))
    elif change_dir:  # the small path: one file holds the checks, the tests and the results
        spec_md = test_md = _read(os.path.join(change_dir, "change.md"))
    rows = check_rows(spec_md, test_md, junit)
    failed_checks = sum(1 for r in rows if r["state"] == "fail")
    drift_required = bool(change_dir and os.path.isdir(change_dir))

    def decision_now(level_now):
        return decide(level_now, len(open_findings), tests_failed, args.author, args.cross_repo, drift=drift,
                      round_no=round_no, failed_checks=failed_checks, drift_required=drift_required)

    decision = decision_now(level)

    images, gist_id = None, None
    if preview is not None:
        images = {"panels": preview.get("panels", []), "pages": preview.get("pages", []),
                  "warnings": list(preview.get("warnings", []))}
        pngs = sorted(os.path.join(out, f) for f in os.listdir(out) if f.endswith(".png"))
        if args.post and pngs:
            known = GIST_MARK.search(previous)
            try:
                gist_id, urls = upload(args.pr, pngs, risk_result.get("head", "0000000"),
                                       gist_id=known.group(1) if known else preview.get("gist_id"))
                for panel in images["panels"]:
                    for side in ("before", "after"):
                        if panel.get(side):
                            panel[side] = urls.get(os.path.basename(panel[side]))
                for page in images["pages"]:
                    for side in ("before", "after"):
                        page[side] = urls.get(os.path.basename(page[side]))
            except subprocess.CalledProcessError as exc:
                images["warnings"].append(f"Images not uploaded: {exc.cmd[:3]}")
                risk_result["reasons"].append("Screenshots: images not uploaded")
                risk_result["level"] = level = "high"
                decision = decision_now(level)

    body = comment({
        "risk": risk_result, "findings": shown, "images": images, "rows": rows,
        "junit": junit, "base_ids": collected(_read(os.path.join(out, "collect-base.txt"))),
        "head_ids": collected(_read(os.path.join(out, "collect-head.txt"))),
        "raw": _raw(_read(os.path.join(out, "pytest.txt"))), "lint": lint,
        "decision": decision, "drift": drift, "drift_required": drift_required,
        "body": pr_body.fields(body_text) if body_text is not None else None,
        "round": round_no, "gist_id": gist_id, "pr": args.pr, "approval": approval(change_dir)})
    with open(os.path.join(out, "comment.md"), "w") as fh:
        fh.write(body)
    if not args.post:
        print(body)
        return 0
    url = post(args.pr, body)
    set_label(args.pr, level)
    print(json.dumps({"level": level, "decision": decision, "open_findings": len(open_findings),
                      "failed_checks": failed_checks, "tests_failed": tests_failed, "round": round_no,
                      "drift": drift_summary(drift)[1],
                      "comment": url, "head": risk_result.get("head")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
