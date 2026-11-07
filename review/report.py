"""The PR comment of the review agent: the risk, the findings, the screenshots and the test table.

Usage, from the repo root (the agent runs it, review/reviewer.md step 8):

    python3 -m review.report --pr N --change-dir ../kb/work/NNN-slug --out ~/homeautomation/review-out/prN \
        --author LOGIN [--cross-repo] [--post]

--out holds risk.json, findings.json, junit.xml, pytest.txt, flake8.txt, collect-head.txt, collect-base.txt
and, after a dashboard change, preview.json and the PNG files. The command prints the comment, or with
--post uploads the images to a secret gist, writes the one comment of the agent on the PR (it replaces the
last one), sets the label risk:low or risk:high, and prints a JSON summary with the decision.

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.7 and 2.8.
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

from review import risk

MARKER = "<!-- pr-reviewer -->"
GIST_MARK = re.compile(r"<!-- gist:([0-9a-f]+) -->")
REPO = risk.REPO
MAX_BODY = 60000
NEXT = {
    "auto-merge": "Next: the session turns on auto-merge; GitHub merges after `build (3.9)`.",
    "wait-owner": "Next: **the owner merges** (high risk).",
    "fix-findings": "Next: the session fixes the findings or the failed tests and runs the review again.",
    "refuse": "Next: nothing. The agent works only on PRs of the owner from a branch of this repo.",
}
RESULT = {"pass": "✅ pass", "fail": "❌ fail", "not proven": "⚠️ not proven"}


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


def acceptance_checks(spec_md):
    """The numbered items of "## 8. Acceptance checks": [(number, text)]."""
    checks = []
    for line in _section(spec_md, r"^##\s+8\.\s+Acceptance checks").splitlines():
        m = re.match(r"^(\d+)\.\s+(.*)", line)
        if m:
            checks.append((int(m.group(1)), m.group(2).strip()))
        elif checks and line.startswith("   ") and line.strip():
            n, text = checks[-1]
            checks[-1] = (n, text + " " + line.strip())
    return checks


def _test_id(cell):
    name = cell.strip().strip("`").strip()
    return name if name.startswith("tests/") else "tests/" + name


def test_map(test_md):
    """{test id: [check numbers]} from the table "Tests this change adds or extends"."""
    found = {}
    for line in _section(test_md, r"^##\s+Tests this change adds or extends").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or "::" not in cells[0]:
            continue
        found[_test_id(cells[0])] = [int(n) for n in re.findall(r"\d+", cells[-1])]
    return found


def open_checks(test_md):
    """{check: when} from the rows "| <check> | open until <date or run> |" of the Results; a later row wins."""
    found = {}
    for line in _section(test_md, r"^##\s+Results").splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]*)\|", line)
        if not m:
            continue
        n, result = int(m.group(1)), m.group(2).strip()
        date = re.match(r"open until (.+)", result)
        if date:
            found[n] = date.group(1)
        else:
            found.pop(n, None)
    return found


def _junit_id(classname, name):
    parts = classname.split(".")
    files = [p for p in parts if not p[:1].isupper()]
    classes = [p for p in parts if p[:1].isupper()]
    return "/".join(files) + ".py::" + "".join(c + "::" for c in classes) + re.sub(r"\[.*\]$", "", name)


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
    return {re.sub(r"\[.*\]$", "", line.strip()) for line in text.splitlines() if "::" in line}


def _matches(mapped, junit):
    """The JUnit ids of one test of the table. The table may leave out the class."""
    if mapped in junit:
        return [mapped]
    path, name = mapped.split("::")[0], mapped.split("::")[-1]
    return [t for t in junit if t.split("::")[0] == path and t.split("::")[-1] == name]


def _short(text, size=120):
    text = text.replace("|", "\\|")
    return text if len(text) <= size else text[:size - 1].rstrip() + "…"


def table(spec_md, test_md, junit, base_ids, head_ids, risk_result):
    tmap, opened = test_map(test_md), open_checks(test_md)
    lines = ["### What the tests prove", "", "| Check | What | Proven by | Result |", "|---|---|---|---|"]
    not_proven = []
    for n, text in acceptance_checks(spec_md):
        tests = [t for t, refs in tmap.items() if n in refs]
        states = [junit[j] for t in tests for j in _matches(t, junit)]
        if "fail" in states:
            result = RESULT["fail"]
        elif n in opened:
            result = f"⏳ open until {opened[n]}"
        elif states and all(s == "pass" for s in states) and all(_matches(t, junit) for t in tests):
            result = RESULT["pass"]
        else:
            result = RESULT["not proven"]
            not_proven.append(str(n))
        names = [t.split("::")[-1] for t in tests]
        shown = ", ".join(f"`{x}`" for x in names[:3]) + (f" +{len(names) - 3} more" if len(names) > 3 else "")
        lines.append(f"| {n} | {_short(text)} | {shown or '—'} | {result} |")
    passed = sum(1 for s in junit.values() if s == "pass")
    failed = sorted(t for t, s in junit.items() if s == "fail")
    lines += ["", f"**{passed} passed ({len(head_ids) - len(base_ids):+d} vs main)**"]
    if failed:
        lines.append("Failed: " + ", ".join(f"`{t}`" for t in failed))
    for label, key in (("New tests", "new_tests"), ("Edited tests", "edited_tests"),
                       ("Deleted tests", "deleted_tests")):
        names = risk_result.get(key) or []
        if len(names) > 5:
            lines.append(f"<details><summary>{label}: {len(names)}</summary>\n\n"
                         + "\n".join(f"- `{t}`" for t in names) + "\n</details>\n")
        else:
            lines.append(f"{label}: " + (", ".join(f"`{t}`" for t in names) if names else "none"))
    lines.append("Not proven: " + (", ".join(not_proven) if not_proven else "none"))
    return "\n".join(lines)


def _images_md(images):
    if images is None:
        return "No dashboard change."
    out = []
    for panel in images.get("panels", []):
        before = f"![before]({panel['before']})" if panel.get("before") else "_absent_"
        after = f"![after]({panel['after']})" if panel.get("after") else "_absent_"
        out += [f"**Panel {panel['id']}**", "", "| Before | After |", "|---|---|", f"| {before} | {after} |", ""]
    page = images.get("page") or {}
    if page:
        out += ["**Full page**", "", "| Before | After |", "|---|---|",
                f"| ![before]({page.get('before')}) | ![after]({page.get('after')}) |", ""]
    for warning in images.get("warnings", []):
        out.append(f"> ⚠️ {warning}")
    return "\n".join(out).rstrip()


def comment(risk_result, findings, images, table_md, raw, decision=None, gist_id=None):
    level = risk_result.get("level", "high")
    reasons = risk_result.get("reasons") or []
    parts = [MARKER + (f"\n<!-- gist:{gist_id} -->" if gist_id else ""),
             f"## Review — risk: **{level.upper()}**", ""]
    parts += [f"- {r}" for r in reasons] or ["- No rule fired."]
    if decision:
        parts += ["", NEXT.get(decision, decision)]
    parts += ["", "### Findings", ""]
    parts += [f"- `{f.get('file', '?')}:{f.get('line', '?')}` ({f.get('kind', '?')}) {f.get('text', '')}"
              for f in findings] or ["None."]
    parts += ["", "### Screenshots", "", _images_md(images), "", table_md, ""]
    head = "\n".join(parts)
    room = MAX_BODY - len(head) - 200
    raw = raw if len(raw) <= room else raw[:room] + "\n… (cut)"
    return head + "\n<details><summary>Raw output</summary>\n\n````\n" + raw + "\n````\n</details>\n"


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

    risk_result = json.loads(_read(os.path.join(out, "risk.json"), '{"level": "high", "reasons": ["no risk.json"]}'))
    findings = json.loads(_read(os.path.join(out, "findings.json"), "[]"))
    raised = [f for f in findings if f.get("kind") == "risk"]
    open_findings = [f for f in findings if f.get("kind") != "risk"]
    reasons = list(risk_result.get("reasons") or []) + [f"Agent: {f.get('text', '')}" for f in raised]
    preview = json.loads(_read(os.path.join(out, "preview.json"), "null"))
    if preview and preview.get("failed"):
        reasons.append(f"Screenshots: {preview['failed']}")
    level = "high" if reasons else risk_result.get("level", "high")
    risk_result = dict(risk_result, level=level, reasons=reasons)

    junit_text = _read(os.path.join(out, "junit.xml"))
    junit = junit_results(junit_text) if junit_text else {}
    tests_failed = not junit or any(s == "fail" for s in junit.values())
    decision = risk.decide(level, len(open_findings), tests_failed, args.author, args.cross_repo)

    change_dir = os.path.expanduser(args.change_dir) if args.change_dir else None
    spec_md = _read(os.path.join(change_dir, "spec.md")) if change_dir else ""
    test_md = _read(os.path.join(change_dir, "test.md")) if change_dir else ""
    table_md = table(spec_md, test_md, junit, collected(_read(os.path.join(out, "collect-base.txt"))),
                     collected(_read(os.path.join(out, "collect-head.txt"))), risk_result)
    if not change_dir:
        table_md = "No change folder: the table has no acceptance checks.\n\n" + table_md
    raw = "$ pytest\n" + _read(os.path.join(out, "pytest.txt")) + "\n$ flake8\n" + _read(os.path.join(out, "flake8.txt"))

    images, gist_id = None, None
    if preview is not None:
        images = {"panels": preview.get("panels", []), "page": preview.get("page"),
                  "warnings": list(preview.get("warnings", []))}
        pngs = sorted(os.path.join(out, f) for f in os.listdir(out) if f.endswith(".png"))
        if args.post and pngs:
            body_now = _read(os.path.join(out, "comment.md"))
            known = GIST_MARK.search(body_now)
            try:
                gist_id, urls = upload(args.pr, pngs, risk_result.get("head", "0000000"),
                                       gist_id=known.group(1) if known else preview.get("gist_id"))
                for panel in images["panels"]:
                    for side in ("before", "after"):
                        if panel.get(side):
                            panel[side] = urls.get(os.path.basename(panel[side]))
                if images.get("page"):
                    images["page"] = {s: urls.get(os.path.basename(p)) for s, p in images["page"].items()}
            except subprocess.CalledProcessError as exc:
                images["warnings"].append(f"Images not uploaded: {exc.cmd[:3]}")
                risk_result["reasons"].append("Screenshots: images not uploaded")
                risk_result["level"] = level = "high"
                decision = risk.decide(level, len(open_findings), tests_failed, args.author, args.cross_repo)

    body = comment(risk_result, open_findings, images, table_md, raw, decision=decision, gist_id=gist_id)
    with open(os.path.join(out, "comment.md"), "w") as fh:
        fh.write(body)
    if not args.post:
        print(body)
        return 0
    url = post(args.pr, body)
    set_label(args.pr, level)
    print(json.dumps({"level": level, "decision": decision, "open_findings": len(open_findings),
                      "tests_failed": tests_failed, "comment": url, "head": risk_result.get("head")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
