"""Change 032: the PR comment of the review agent (review/report.py).

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.7 and 2.8. No network: subprocess.run is replaced.

The form of the comment (gates that expand, the owner first, drift from the intent, the checks of a
change.md) is the decision of 2026-11-17 in ../kb/decisions.md.
"""
import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from review import report

SPEC = """# Spec

## 7. Decisions

- D1. Something.

## 8. Acceptance checks

1. The risk script gives high for Telegraf.
2. The risk script gives low for a panel.
3. A live check that waits for spring.
4. A check with no test.
5. A check whose test fails.
"""

TESTS = """# Tests

## Tests this change adds or extends

| Test | New / extended | What it proves | Spec § |
|---|---|---|---|
| `review_risk_unit_test.py::test_telegraf_files_are_high` | new | x | 1 |
| `review_risk_unit_test.py::test_panel_only_change_is_low` | new | x | 2, 3 |
| `tests/other_unit_test.py::TestX::test_broken` | new | x | 5 |

## Change-specific checks

None.

## Results

### Run 1

| Check | Result |
|---|---|
| 3 | open until 2027-04-01 |
"""

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="4">
<testcase classname="tests.review_risk_unit_test.TestPathRules" name="test_telegraf_files_are_high" time="0.1"/>
<testcase classname="tests.review_risk_unit_test.TestSetpoints" name="test_panel_only_change_is_low" time="0.1"/>
<testcase classname="tests.other_unit_test.TestX" name="test_broken" time="0.1"><failure message="boom">x</failure></testcase>
<testcase classname="tests.plain_unit_test" name="test_module_level" time="0.1"/>
<testcase classname="tests.plain_unit_test" name="test_param[a]" time="0.1"/>
<testcase classname="tests.plain_unit_test" name="test_param[b]" time="0.1"/>
</testsuite></testsuites>
"""

RISK = {"level": "low", "reasons": [], "new_tests": ["tests/b_unit_test.py::test_new"],
        "edited_tests": ["tests/a_unit_test.py::A::test_one"], "deleted_tests": ["tests/a_unit_test.py::A::test_two"]}


CHANGE = """# Change

## 1. Problem

Text.

## 2. Outcome and acceptance checks

1. The file says A.
2. The file says B.
3. The file says C.
4. Nothing else changes.
5. A check that waits.

## 5. Tests

| Test | New / extended / existing | What it proves | Check in §2 |
|---|---|---|---|
| `review_risk_unit_test.py::test_telegraf_files_are_high` | existing | x | 4 |
| The `grep` checks below | one-off | x | 1–3 |

## 6. Rollback

Revert.

## 7. Results

### Run 1

| Check in §2 | Command | Output | Verdict |
|---|---|---|---|
| 1–3 | `grep -c x` | `0` | fail |

### Run 2

| Check in §2 | Command | Output | Verdict |
|---|---|---|---|
| 1–3 | `grep -c x` | `6` | pass |
| 5 | — | — | open until the deploy |

## 8. Departures

None.
"""

BODY = {"What:": "six pins move.", "Owner must do:": "before deploy on .51, run pip install.",
        "Tested:": "398 passed.", "Not covered:": "real TLS.", "Revert:": "revert the commit."}
HEAD = "d1405dc54125aaca433b80631579e4664ee326d1"


def data(**over):
    junit = report.junit_results(JUNIT.replace('<failure message="boom">x</failure>', ""))
    base = {"risk": dict(RISK, level="high", reasons=["Config: requirements.txt"], head=HEAD), "findings": [],
            "images": None, "rows": report.check_rows(CHANGE, CHANGE, junit), "junit": junit,
            "base_ids": set(), "head_ids": set(), "raw": "RAW-OUTPUT", "decision": "wait-owner", "drift": None,
            "body": BODY, "round": 1, "gist_id": None, "pr": 47, "approval": "change.md: approved by the owner"}
    base.update(over)
    return base


def gate(body, name):
    """The <details> block of one gate: (the opening tag, the summary line, the text inside)."""
    m = re.search(r"(<details[^>]*>)<summary>([^\n]*<b>%s</b>[^\n]*)</summary>(.*?)</details>" % name, body, re.S)
    return m.groups() if m else None


class TestTable(unittest.TestCase):

    def setUp(self):
        self.junit = report.junit_results(JUNIT)
        base = {"tests/a.py::t%d" % i for i in range(9)}
        head = {"tests/a.py::t%d" % i for i in range(12)}
        self.rows = report.check_rows(SPEC, TESTS, self.junit)
        self.md = report.checks_md(self.rows) + "\n" + report.tests_md(self.junit, base, head, RISK)

    def test_one_row_per_acceptance_check(self):
        checks = report.acceptance_checks(SPEC)
        self.assertEqual([n for n, _ in checks], [1, 2, 3, 4, 5])
        rows = [line for line in self.md.splitlines() if line.startswith("| ") and line[2:3].isdigit()]
        self.assertEqual([int(r.split("|")[1]) for r in rows], [1, 2, 3, 4, 5])

    def test_check_results(self):
        rows = {int(r.split("|")[1]): r for r in self.md.splitlines() if r.startswith("| ") and r[2:3].isdigit()}
        self.assertIn("pass", rows[1])
        self.assertIn("pass", rows[2])
        self.assertIn("open until 2027-04-01", rows[3])
        self.assertIn("not proven", rows[4])
        self.assertIn("fail", rows[5])

    def test_count_against_main(self):
        self.assertIn("5 passed (+3 vs main)", self.md)
        params = report.collected("tests/p.py::test_x[1]\ntests/p.py::test_x[2]\n")
        self.assertEqual(len(params), 2)
        self.assertIn("tests/other_unit_test.py::TestX::test_broken", self.md)

    def test_test_lists(self):
        self.assertIn("tests/b_unit_test.py::test_new", self.md)
        self.assertIn("tests/a_unit_test.py::A::test_one", self.md)
        self.assertIn("tests/a_unit_test.py::A::test_two", self.md)
        self.assertIn("Not proven: 4", self.md)
        all_proven = report.check_rows(SPEC.replace("4. A check with no test.\n", ""), TESTS, self.junit)
        self.assertIn("Not proven: none", report.checks_md(all_proven))


class TestMatch(unittest.TestCase):

    def test_class_in_id_matches_only_that_class(self):
        junit = {"tests/x.py::TestA::test_x": "pass", "tests/x.py::TestB::test_x": "fail",
                 "tests/x.py::TestC::test_p[1]": "pass"}
        self.assertEqual(report._matches("tests/x.py::TestA::test_x", junit), ["tests/x.py::TestA::test_x"])
        self.assertEqual(sorted(report._matches("tests/x.py::test_x", junit)),
                         ["tests/x.py::TestA::test_x", "tests/x.py::TestB::test_x"])
        self.assertEqual(report._matches("tests/x.py::TestC::test_p", junit), ["tests/x.py::TestC::test_p[1]"])


class TestChangeFile(unittest.TestCase):
    """Change 035: the checks of a small change come from change.md."""

    def setUp(self):
        self.junit = report.junit_results(JUNIT)
        self.rows = {r["n"]: r for r in report.check_rows(CHANGE, CHANGE, self.junit)}

    def test_checks_of_section_2(self):
        self.assertEqual(sorted(self.rows), [1, 2, 3, 4, 5])
        self.assertEqual(self.rows[2]["text"], "The file says B.")

    def test_ranges(self):
        self.assertEqual(report.numbers("1–3"), [1, 2, 3])
        self.assertEqual(report.numbers("2, 4-6"), [2, 4, 5, 6])
        self.assertEqual(report.numbers("7"), [7])

    def test_recorded_pass_of_the_last_run(self):
        for n in (1, 2, 3):
            self.assertEqual(self.rows[n]["state"], "recorded")
        self.assertEqual(self.rows[4]["state"], "pass")
        self.assertEqual(self.rows[5]["state"], "open")
        self.assertEqual(self.rows[5]["when"], "the deploy")

    def test_recorded_fail_stays_a_fail(self):
        only_run_1 = CHANGE[:CHANGE.index("### Run 2")]
        rows = {r["n"]: r for r in report.check_rows(only_run_1, only_run_1, self.junit)}
        self.assertEqual(rows[1]["state"], "fail")

    def test_table_names_the_kind_of_proof(self):
        md = report.checks_md(list(self.rows.values()))
        self.assertIn("recorded pass", md)
        self.assertIn("Not proven: none", md)
        self.assertEqual(report.checks_summary(list(self.rows.values()))[1], "4 of 5 proven, 1 open")

    def test_only_a_fail_opens_the_checks_gate(self):
        rows = report.check_rows(SPEC, TESTS, self.junit)
        self.assertEqual(report.checks_summary(rows), (report.BAD, "2 of 5 proven, 1 open, 1 not proven, 1 failed", True))
        no_fail = [r for r in rows if r["state"] != "fail"]
        self.assertEqual(report.checks_summary(no_fail), (report.WARN, "2 of 4 proven, 1 open, 1 not proven", False))

    def test_an_open_check_is_not_a_green_mark(self):
        self.assertEqual(report.checks_summary(list(self.rows.values())),
                         (report.WAIT, "4 of 5 proven, 1 open", False))


FREE = """# Change

## 2. Outcome and acceptance checks

1. The pins.
2. The install.
3. The smoke test.
4. CI.

## 5. Tests

| Test | New / extended / existing | What it proves | Check |
|---|---|---|---|
| `pip check` in a clean venv | change-specific | no conflict | 2 |
| `…::test_module_level` (a fixed string) | new | x | 3 |
| `tests/plain_unit_test.py::test_param` | new | x | 3 |

## 7. Results

### Run 1 — 2026-11-17

| Check | Result |
|---|---|
| 1 pins | pass (diff: six lines) |
| 2 install, `pip check` | pass on macOS; the install on `.51` is the deploy |
| 4 CI | waits for the PR |

| 2026-11-17 | pass |
"""


class TestFreeForm(unittest.TestCase):
    """The change files of 033 and 037 do not follow one form. The tool reads what is certain."""

    def setUp(self):
        self.junit = report.junit_results(JUNIT)
        self.rows = {r["n"]: r for r in report.check_rows(FREE, FREE, self.junit)}

    def test_a_word_after_the_check_number(self):
        self.assertEqual(self.rows[1]["state"], "recorded")
        self.assertEqual(self.rows[2]["state"], "recorded")

    def test_a_row_with_no_verdict_is_not_proven(self):
        self.assertEqual(self.rows[4]["state"], "not proven")

    def test_a_date_is_not_a_check_number(self):
        self.assertEqual(sorted(report.recorded(FREE)), [1, 2])

    def test_test_id_with_no_file_and_with_a_note(self):
        self.assertEqual(self.rows[3]["state"], "pass")
        self.assertEqual(len(self.rows[3]["tests"]), 2)


class TestComment(unittest.TestCase):

    def test_head_names_the_decision_the_commit_and_the_round(self):
        body = report.comment(data(round=2))
        self.assertTrue(body.startswith(report.MARKER))
        head = [line for line in body.splitlines() if line.startswith("## ")][0]
        self.assertIn("Waiting for the owner", head)
        self.assertIn("HIGH", head)
        self.assertIn("`d1405dc`", head)
        self.assertIn("round 2 of 3", head)
        self.assertIn("<!-- round:2 head:%s -->" % HEAD, body)
        low = report.comment(data(risk=dict(RISK, head=HEAD), decision="auto-merge"))
        self.assertIn("## Ready — LOW", low)

    def test_gates_in_order(self):
        body = report.comment(data())
        order = [body.index("<b>%s</b>" % g) for g in ("Approval", "Drift", "Findings", "Checks", "Tests")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("Screenshots", body)

    def test_owner_gate_is_open_and_holds_the_owner_action(self):
        tag, summary, inner = gate(report.comment(data()), "Approval")
        self.assertIn("open", tag)
        self.assertIn("d1405dc", summary)
        self.assertIn("before deploy on .51, run pip install.", inner)
        self.assertIn("Config: requirements.txt", inner)
        self.assertIn("change.md: approved by the owner", inner)

    def test_green_gates_are_closed(self):
        body = report.comment(data(risk=dict(RISK, head=HEAD), decision="auto-merge",
                                   drift=[{"kind": "outcome", "n": 1, "state": "met", "text": "A"}]))
        for name in ("Approval", "Drift", "Findings", "Checks", "Tests"):
            self.assertNotIn("open", gate(body, name)[0], name)

    def test_no_raw_output_on_a_green_run(self):
        body = report.comment(data())
        self.assertNotIn("RAW-OUTPUT", body)
        self.assertIn("6 passed", gate(body, "Tests")[1])

    def test_failed_tests_open_the_gate_with_cut_output(self):
        junit = report.junit_results(JUNIT)
        body = report.comment(data(junit=junit, raw="X" * 9000, decision="fix-findings"))
        tag, summary, inner = gate(body, "Tests")
        self.assertIn("open", tag)
        self.assertIn("1 failed", summary)
        self.assertIn("X" * report.MAX_RAW, inner)
        self.assertNotIn("X" * (report.MAX_RAW + 1), inner)
        self.assertIn("review-out/pr47/pytest.txt", inner)

    def test_blocking_findings_open_the_gate(self):
        findings = [{"file": "co2.py", "line": 23, "kind": "bug", "text": "swapped values"}]
        tag, summary, inner = gate(report.comment(data(findings=findings, decision="fix-findings")), "Findings")
        self.assertIn("open", tag)
        self.assertIn("1 blocking", summary)
        self.assertIn("`co2.py:23` (bug) swapped values", inner)

    def test_gaps_inform_three_shown_the_rest_counted(self):
        findings = [{"kind": "gap", "text": "gap %d " % i + "y" * 400} for i in range(5)]
        tag, summary, inner = gate(report.comment(data(findings=findings)), "Findings")
        self.assertNotIn("open", tag)
        self.assertIn("none blocking, 5 gaps", summary)
        self.assertIn("gap 2", inner)
        self.assertNotIn("gap 3", inner)
        self.assertIn("2 more in `review-out/pr47/findings.json`", inner)
        longest = max(len(line) for line in inner.splitlines())
        self.assertLess(longest, report.MAX_TEXT + 40)

    def test_screenshots_only_for_a_dashboard_change(self):
        images = {"panels": [{"id": 81, "before": "https://g/b.png", "after": "https://g/a.png"}],
                  "pages": [{"label": "ai", "before": "https://g/ab.png", "after": "https://g/aa.png"}],
                  "warnings": []}
        body = report.comment(data(images=images, gist_id="abc123"))
        self.assertIn("<!-- gist:abc123 -->", body)
        tag, _, inner = gate(body, "Screenshots")
        self.assertIn("open", tag)
        self.assertIn("https://g/a.png", inner)
        self.assertIn("https://g/aa.png", inner)

    def test_no_body_fields(self):
        _, _, inner = gate(report.comment(data(body=None)), "Approval")
        self.assertIn("not read", inner)
        _, _, inner = gate(report.comment(data(body={})), "Approval")
        self.assertIn("not stated in the PR body", inner)


class TestDrift(unittest.TestCase):

    MET = [{"kind": "outcome", "n": 1, "state": "met", "text": "No open alert", "file": "requirements.txt", "line": 3},
           {"kind": "constraint", "state": "kept", "text": "No device write"}]
    OUTSIDE = {"kind": "outside", "text": "flask moves to 3.1.3", "file": "requirements.txt", "line": 14}

    def test_not_measured_is_never_green(self):
        tag, summary, inner = gate(report.comment(data(drift=None)), "Drift")
        self.assertIn("not measured", summary)
        self.assertNotIn("✅", summary)

    def test_all_met(self):
        tag, summary, inner = gate(report.comment(data(drift=self.MET)), "Drift")
        self.assertIn("✅", summary)
        self.assertIn("1 of 1 outcomes met", summary)
        self.assertNotIn("open", tag)
        self.assertIn("`requirements.txt:3`", inner)

    def test_outside_the_intent_opens_the_gate_and_waits_for_the_owner(self):
        drift = self.MET + [self.OUTSIDE]
        tag, summary, inner = gate(report.comment(data(drift=drift)), "Drift")
        self.assertIn("open", tag)
        self.assertIn("1 item outside the intent", summary)
        self.assertIn("flask moves to 3.1.3", inner)
        self.assertEqual(report.decide("low", 0, False, "matejpristak", False, drift=drift), "wait-owner")
        self.assertEqual(report.decide("low", 0, False, "matejpristak", False, drift=self.MET), "auto-merge")

    def test_added_by_the_spec_is_not_drift(self):
        drift = self.MET + [dict(self.OUTSIDE, by_spec=True)]
        self.assertEqual(report.decide("low", 0, False, "matejpristak", False, drift=drift), "auto-merge")
        _, summary, inner = gate(report.comment(data(drift=drift)), "Drift")
        self.assertIn("✅", summary)
        self.assertIn("added by the spec", inner)

    def test_an_outcome_that_is_not_met_blocks(self):
        drift = [{"kind": "outcome", "n": 1, "state": "not met", "text": "No open alert"}]
        self.assertEqual(report.decide("low", 0, False, "matejpristak", False, drift=drift), "fix-findings")
        tag, summary, _ = gate(report.comment(data(drift=drift, decision="fix-findings")), "Drift")
        self.assertIn("open", tag)
        self.assertIn("❌", summary)

    def test_decide_keeps_the_rules_of_risk(self):
        self.assertEqual(report.decide("high", 0, False, "matejpristak", False), "wait-owner")
        self.assertEqual(report.decide("low", 1, False, "matejpristak", False), "fix-findings")
        self.assertEqual(report.decide("low", 0, False, "stranger", False), "refuse")


class TestRound(unittest.TestCase):

    def test_round_counts_new_heads(self):
        self.assertEqual(report.round_number("", HEAD), 1)
        last = "<!-- pr-reviewer -->\n<!-- round:2 head:%s -->\n## Not ready — LOW" % HEAD
        self.assertEqual(report.round_number(last, HEAD), 2)
        self.assertEqual(report.round_number(last, "f" * 40), 3)

    def test_a_new_head_after_a_clean_review_is_not_a_new_round(self):
        clean = "<!-- pr-reviewer -->\n<!-- round:1 head:%s -->\n## Ready — LOW" % HEAD
        self.assertEqual(report.round_number(clean, "f" * 40), 1)

    def test_after_three_rounds_the_owner_decides(self):
        self.assertEqual(report.decide("low", 2, False, "matejpristak", False, round_no=3), "fix-findings")
        self.assertEqual(report.decide("low", 2, False, "matejpristak", False, round_no=4), "wait-owner")
        body = report.comment(data(round=4, findings=[{"file": "a.py", "line": 1, "kind": "bug", "text": "x"}]))
        tag, summary, inner = gate(body, "Approval")
        self.assertIn("Three rounds", inner)
        self.assertIn("open", tag)
        self.assertIn("decide on the approach", summary)
        self.assertNotIn("--match-head-commit", body)
        self.assertNotIn("the owner merges", body)

    def test_three_rounds_line_needs_an_open_finding(self):
        body = report.comment(data(round=4))
        self.assertNotIn("Three rounds", body)
        self.assertIn("--match-head-commit", body)


class TestBodyFindings(unittest.TestCase):

    def test_a_long_pr_body_is_a_rule_finding(self):
        found = report.body_findings("A long text.\n\n| a | b |\n|---|---|\n")
        self.assertTrue(found)
        self.assertTrue(all(f["kind"] == "rule" and f["file"] == "PR body" for f in found))
        self.assertEqual(report.body_findings(None), [])


RESULTS = """## Results

### Run 1

| Check | Result |
|---|---|
%s
"""


class TestReviewOfPr49(unittest.TestCase):
    """The findings of the review agent on PR #49, round 1. One test for each."""

    def test_two_rows_for_one_check_the_first_with_no_verdict(self):
        md = RESULTS % "| 3 | waits for the PR |\n| 3 | pass |"
        self.assertEqual(report.recorded(md), {3: ("pass", None)})

    def test_the_verdict_is_the_last_cell(self):
        md = RESULTS.replace("| Check | Result |", "| Check | How | Result |").replace("|---|---|", "|---|---|---|")
        self.assertEqual(report.recorded(md % "| 3 | pass if the log shows X | not run yet |"), {})
        self.assertEqual(report.recorded(md % "| 3 | the log | pass |"), {3: ("pass", None)})

    def test_only_a_table_of_checks_is_read(self):
        for head in ("Step", "Test", "#"):
            md = RESULTS.replace("| Check |", "| %s |" % head) % "| 3 | pass |"
            self.assertEqual(report.recorded(md), {}, head)
        for head in ("Check in §2", "§ 8"):
            md = RESULTS.replace("| Check |", "| %s |" % head) % "| 3 | pass |"
            self.assertEqual(report.recorded(md), {3: ("pass", None)}, head)

    def test_other_spellings_of_the_verdict(self):
        self.assertEqual(report.recorded(RESULTS % "| 5 | **Fail** on the node |")[5][0], "fail")
        self.assertEqual(report.recorded(RESULTS % "| 5 | failed |")[5][0], "fail")
        self.assertEqual(report.recorded(RESULTS % "| 5 | Passed |")[5][0], "pass")
        self.assertEqual(report.recorded(RESULTS % "| 5 | Open until 2026-05-01 |")[5], ("open", "2026-05-01"))

    def test_a_failed_check_stops_the_merge(self):
        self.assertEqual(report.decide("low", 0, False, "matejpristak", False, failed_checks=1), "fix-findings")
        self.assertEqual(report.decide("high", 0, False, "matejpristak", False, failed_checks=1), "fix-findings")

    def test_lint_output_is_in_the_tests_gate(self):
        self.assertFalse(report.lint_failed("0\n"))
        self.assertFalse(report.lint_failed(""))
        lint = "./x.py:1:1: F821 undefined name 'y'\n1\n"
        self.assertTrue(report.lint_failed(lint))
        tag, summary, inner = gate(report.comment(data(lint=lint, decision="fix-findings")), "Tests")
        self.assertIn("open", tag)
        self.assertIn(report.BAD, summary)
        self.assertIn("flake8", summary)
        self.assertIn("F821 undefined name", inner)

    def test_drift_with_no_outcome_row_is_not_measured(self):
        only_constraint = [{"kind": "constraint", "state": "kept", "text": "x"}]
        wrong_kind = [{"kind": "Outcome", "n": 1, "state": "met", "text": "x"}]
        for drift in (only_constraint, wrong_kind):
            _, summary, inner = gate(report.comment(data(drift=drift)), "Drift")
            self.assertIn("not measured", summary)
            self.assertNotIn(report.OK, summary)
        self.assertIn("unknown kind", gate(report.comment(data(drift=wrong_kind)), "Drift")[2])

    def test_a_change_folder_with_no_measured_drift_waits_for_the_owner(self):
        met = [{"kind": "outcome", "n": 1, "state": "met", "text": "x"}]
        args = ("low", 0, False, "matejpristak", False)
        self.assertEqual(report.decide(*args, drift=None, drift_required=True), "wait-owner")
        self.assertEqual(report.decide(*args, drift=[{"kind": "Outcome"}], drift_required=True), "wait-owner")
        self.assertEqual(report.decide(*args, drift=met, drift_required=True), "auto-merge")
        self.assertEqual(report.decide(*args, drift=None, drift_required=False), "auto-merge")
        body = report.comment(data(risk=dict(RISK, head=HEAD), drift=None, drift_required=True))
        self.assertIn("open", gate(body, "Drift")[0])
        self.assertIn("drift", gate(body, "Approval")[2].lower())

    def test_main_with_a_broken_pr_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "risk.json"), "w") as fh:
                json.dump({"level": "low", "reasons": [], "head": HEAD}, fh)
            open(os.path.join(tmp, "pr.json"), "w").close()
            out = io.StringIO()
            with redirect_stdout(out):
                code = report.main(["--pr", "9", "--out", tmp, "--author", "matejpristak"])
            self.assertEqual(code, 0)
            self.assertIn("not read", out.getvalue())


class FakeRun:
    """Records the commands; answers gh calls."""

    def __init__(self, comment_ids=""):
        self.calls = []
        self.comment_ids = comment_ids

    def __call__(self, cmd, **kwargs):
        self.calls.append((list(cmd), kwargs))
        out = ""
        if cmd[:3] == ["gh", "gist", "create"]:
            out = "https://gist.github.com/matejpristak/f00d\n"
        elif cmd[:2] == ["gh", "api"] and "--jq" in cmd and cmd[-1].startswith(".[]"):
            out = self.comment_ids
        elif cmd[:2] == ["gh", "api"]:
            out = "https://github.com/Baalberith6/homeautomation/pull/9#issuecomment-1\n"
        elif cmd[:1] == ["git"] and "clone" in cmd:
            os.makedirs(cmd[-1], exist_ok=True)
        return SimpleNamespace(returncode=0, stdout=out, stderr="")


class TestPost(unittest.TestCase):

    def test_post_patches_existing_comment(self):
        run = FakeRun(comment_ids="555\n")
        report.post(9, "body", run=run)
        methods = [c for c, _ in run.calls if "-X" in c]
        self.assertEqual(len(methods), 1)
        self.assertIn("PATCH", methods[0])
        self.assertTrue(any("issues/comments/555" in part for part in methods[0]))

    def test_post_creates_first_comment(self):
        run = FakeRun(comment_ids="")
        report.post(9, "body", run=run)
        methods = [c for c, _ in run.calls if "-X" in c]
        self.assertIn("POST", methods[0])
        self.assertTrue(any("issues/9/comments" in part for part in methods[0]))


class TestUpload(unittest.TestCase):

    def test_upload_uses_gist_only(self):
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "81-after.png")
            with open(png, "wb") as fh:
                fh.write(b"\x89PNG\r\n")
            run = FakeRun()
            gist, urls = report.upload(9, [png], head="abcdef1234", owner="matejpristak", run=run)
            self.assertEqual(gist, "f00d")
            self.assertEqual(urls["81-after.png"],
                             "https://gist.githubusercontent.com/matejpristak/f00d/raw/abcdef1-81-after.png")
            creates = [c for c, _ in run.calls if c[:3] == ["gh", "gist", "create"]]
            self.assertEqual(len(creates), 1)
            pushes = [c for c, _ in run.calls if c[:1] == ["git"] and "push" in c]
            self.assertEqual(len(pushes), 1)
            self.assertIn("credential.helper=!gh auth git-credential", pushes[0])
            for cmd, kwargs in run.calls:
                self.assertNotEqual(os.path.abspath(kwargs.get("cwd") or tmp), repo, cmd)
                self.assertFalse(cmd[:1] == ["git"] and "clone" not in cmd and "-C" not in cmd, cmd)
            run2 = FakeRun()
            gist2, _ = report.upload(9, [png], head="abcdef1234", gist_id="f00d", owner="matejpristak", run=run2)
            self.assertEqual(gist2, "f00d")
            self.assertFalse([c for c, _ in run2.calls if c[:3] == ["gh", "gist", "create"]])


if __name__ == '__main__':
    unittest.main()
