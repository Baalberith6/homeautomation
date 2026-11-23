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
            "body": BODY, "gist_id": None, "pr": 47}
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

    def test_a_recorded_fail_is_shown_as_a_warning(self):
        only_run_1 = CHANGE[:CHANGE.index("### Run 2")]
        rows = report.check_rows(only_run_1, only_run_1, self.junit)
        self.assertEqual({r["n"]: r["state"] for r in rows}[1], "recorded fail")
        icon, text, opened = report.checks_summary(rows)
        self.assertEqual((icon, opened), (report.WARN, False))
        self.assertIn("3 recorded fail", text)
        self.assertIn("recorded fail", report.checks_md(rows))

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

    def test_head_names_the_decision_and_the_commit(self):
        body = report.comment(data())
        self.assertTrue(body.startswith(report.MARKER))
        head = [line for line in body.splitlines() if line.startswith("## ")][0]
        self.assertIn("Waiting for the owner", head)
        self.assertIn("HIGH", head)
        self.assertIn("`d1405dc`", head)
        self.assertNotIn("round", body)
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
        self.assertIn("--match-head-commit " + HEAD, inner)

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

    def test_decide_has_no_round_and_no_approval(self):
        with self.assertRaises(TypeError):
            report.decide("low", 0, False, "matejpristak", False, round_no=4)
        with self.assertRaises(TypeError):
            report.decide("low", 0, False, "matejpristak", False, approved=False)
        with self.assertRaises(TypeError):
            report.decide("low", 0, False, "matejpristak", False, failed_checks=1)
        for name in ("round_number", "approval", "MAX_ROUNDS"):
            self.assertFalse(hasattr(report, name), name)

    def test_decide_keeps_the_rules_of_risk(self):
        self.assertEqual(report.decide("high", 0, False, "matejpristak", False), "wait-owner")
        self.assertEqual(report.decide("low", 1, False, "matejpristak", False), "fix-findings")
        self.assertEqual(report.decide("low", 0, False, "stranger", False), "refuse")


class TestOwnerAction(unittest.TestCase):
    """Finding 6 of round 3: at low risk the line "Owner must do" had no effect."""

    def test_only_nothing_is_no_action(self):
        for text in ("nothing", "Nothing.", " nothing ", "**nothing.**"):
            self.assertFalse(report.owner_action({"Owner must do:": text}), text)
        for text in ("create the ruleset before the merge", "no", "none", "nothing, but watch CI", ""):
            self.assertTrue(report.owner_action({"Owner must do:": text}), text)
        self.assertFalse(report.owner_action(None))

    def test_an_owner_action_makes_a_low_risk_pr_wait(self):
        args = ("low", 0, False, "matejpristak", False)
        self.assertEqual(report.decide(*args, owner_action=True), "wait-owner")
        self.assertEqual(report.decide(*args, owner_action=False), "auto-merge")
        self.assertEqual(report.decide("low", 1, False, "matejpristak", False, owner_action=True), "fix-findings")
        body = report.comment(data(risk=dict(RISK, head=HEAD)))
        self.assertIn("names an action of the owner", gate(body, "Approval")[2])
        quiet = report.comment(data(risk=dict(RISK, head=HEAD), decision="auto-merge",
                                    body=dict(BODY, **{"Owner must do:": "nothing."})))
        self.assertNotIn("names an action", quiet)


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

    def test_a_failed_run_stops_the_merge(self):
        self.assertTrue(report.run_failed({}))
        self.assertTrue(report.run_failed({"tests/a.py::t": "skip"}))
        self.assertTrue(report.run_failed({"tests/a.py::t": "pass", "tests/a.py::u": "fail"}))
        self.assertFalse(report.run_failed({"tests/a.py::t": "pass", "tests/a.py::u": "skip"}))

    def test_lint_output_is_in_the_tests_gate(self):
        self.assertFalse(report.lint_failed("0\n"))
        self.assertFalse(report.lint_failed(""))
        lint = "./x.py:1:1: F821 undefined name 'y'\n1\n"
        self.assertTrue(report.lint_failed(lint))
        tag, summary, inner = gate(report.comment(data(lint=lint)), "Tests")
        self.assertIn("open", tag)
        self.assertIn(report.WARN, summary)
        self.assertIn("flake8", summary)
        self.assertIn("F821 undefined name", inner)

    def test_drift_with_no_outcome_row_is_not_measured(self):
        only_constraint = [{"kind": "constraint", "state": "kept", "text": "x"}]
        wrong_kind = [{"kind": "result", "n": 1, "state": "met", "text": "x"}]
        for drift in (only_constraint, wrong_kind):
            _, summary, inner = gate(report.comment(data(drift=drift)), "Drift")
            self.assertIn("not measured", summary)
            self.assertNotIn(report.OK, summary)
        self.assertIn("unknown kind", gate(report.comment(data(drift=wrong_kind)), "Drift")[2])

    def test_a_change_folder_with_no_measured_drift_waits_for_the_owner(self):
        met = [{"kind": "outcome", "n": 1, "state": "met", "text": "x"}]
        args = ("low", 0, False, "matejpristak", False)
        self.assertEqual(report.decide(*args, drift=None, drift_required=True), "wait-owner")
        self.assertEqual(report.decide(*args, drift=[{"kind": "result"}], drift_required=True), "wait-owner")
        self.assertEqual(report.decide(*args, drift=[{"kind": "Outcome"}], drift_required=True), "fix-findings")
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


BODY_TEXT = """**Change 037** (small path) · `../kb/work/037-security-pins-py39/change.md` · approved 2026-11-17

**Owner must do:** nothing.

**What:** six pins move.

**Tested:** 398 passed. Results: change.md section 7.

**Not covered:** nothing.

**Revert:** revert the commit.
"""
MET = [{"kind": "outcome", "n": 1, "state": "met", "text": "x"}]
LOW = ("low", 0, False, "matejpristak", False)


class TestFailClosed(unittest.TestCase):
    """The findings of the review of PR #49, round 2. One class of bug: a broken or missing input must
    never give a greener comment. Each case starts from a clean run that says "Ready"."""

    def run_main(self, change=None, remove=(), **files):
        base = {"risk.json": json.dumps({"level": "low", "reasons": [], "head": HEAD}),
                "pr.json": json.dumps({"number": 9, "body": BODY_TEXT}), "findings.json": "[]",
                "junit.xml": JUNIT.replace('<failure message="boom">x</failure>', ""), "flake8.txt": "0\n"}
        base.update(files)
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in base.items():
                if name not in remove:
                    with open(os.path.join(tmp, name), "w") as fh:
                        fh.write(text)
            args = ["--pr", "9", "--out", tmp, "--author", "matejpristak"]
            if change is not None:
                folder = os.path.join(tmp, "change")
                if change:
                    os.makedirs(folder)
                    with open(os.path.join(folder, "change.md"), "w") as fh:
                        fh.write(change)
                args += ["--change-dir", folder]
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(report.main(args), 0)
            return out.getvalue()

    def test_the_clean_run_is_ready(self):
        self.assertIn("## Ready — LOW", self.run_main())

    def test_the_new_form_reaches_the_approval_gate(self):
        """Change 039: the labels are bold. The gate shows the text of the owner with no bold marks."""
        self.assertIn("**Owner must do:** nothing.", BODY_TEXT)
        action = "create the ruleset `main` before the merge."
        body = self.run_main(**{"pr.json": json.dumps({
            "number": 9, "body": BODY_TEXT.replace("**Owner must do:** nothing.", "**Owner must do:** " + action)})})
        self.assertIn("## Waiting for the owner — LOW", body)
        inside = gate(body, "Approval")[2]
        self.assertIn("- **Owner must do:** " + action + "\n", inside)
        self.assertIn("names an action of the owner", inside)
        self.assertNotIn("PR body", gate(body, "Findings")[2])
        self.assertIn("## Ready — LOW", self.run_main())   # "**Owner must do:** nothing." is no action

    def test_broken_findings_json(self):
        for text in ('[{"kind": "bug", "text": "x"},]', "", '{"kind": "bug"}', '["a text"]'):
            body = self.run_main(**{"findings.json": text})
            self.assertIn("## Not ready", body, text)
            self.assertIn("findings.json", gate(body, "Findings")[2], text)

    def test_missing_findings_json(self):
        body = self.run_main(remove=("findings.json",))
        self.assertIn("## Not ready", body)
        self.assertIn("findings.json", gate(body, "Findings")[2])

    def test_broken_drift_and_preview_json(self):
        for name in ("drift.json", "preview.json"):
            for text in ("[{]", '"a text"'):
                body = self.run_main(**{name: text})
                self.assertIn("## Not ready", body, name)
                self.assertIn(name, gate(body, "Findings")[2], name)

    def test_missing_pr_json(self):
        body = self.run_main(remove=("pr.json",))
        self.assertIn("## Not ready", body)
        self.assertIn("pr.json", gate(body, "Findings")[2])

    def test_a_dashboard_change_with_no_preview_is_high(self):
        risk_json = json.dumps({"level": "low", "reasons": [], "head": HEAD, "dashboards": ["spec/grafana/ai.json"]})
        body = self.run_main(**{"risk.json": risk_json})
        self.assertIn("HIGH", body)
        self.assertNotIn("## Ready", body)

    def test_a_change_dir_that_is_not_a_folder(self):
        body = self.run_main(change="")
        self.assertIn("## Not ready", body)

    def test_a_later_row_with_no_verdict_keeps_a_fail(self):
        md = ((RESULTS % "| 2 | fail |") + "\n### Run 2\n\n| Check | Result |\n|---|---|\n"
              "| 2 | not run: it needs the deploy |\n")
        self.assertEqual(report.recorded(md), {2: ("fail", None)})
        passed = md.replace("| 2 | fail |", "| 2 | pass |")
        self.assertEqual(report.recorded(passed), {})
        fixed = md.replace("| 2 | not run: it needs the deploy |", "| 2 | pass |")
        self.assertEqual(report.recorded(fixed), {2: ("pass", None)})

    def test_drift_kinds_and_states_in_any_case(self):
        broken = MET + [{"kind": "Constraint", "state": "Broken", "text": "x"}]
        self.assertEqual(report.decide(*LOW, drift=broken, drift_required=True), "fix-findings")
        outside = MET + [{"kind": "Outside", "text": "x", "by_spec": False}]
        self.assertEqual(report.decide(*LOW, drift=outside, drift_required=True), "wait-owner")
        upper = [{"kind": "OUTCOME", "n": 1, "state": "Met", "text": "x"}]
        self.assertEqual(report.decide(*LOW, drift=upper, drift_required=True), "auto-merge")

    def test_a_drift_row_that_the_tool_cannot_read_waits_for_the_owner(self):
        for row in ({"kind": "note", "text": "x"}, "a text", {"text": "no kind"}):
            drift = MET + [row]
            self.assertEqual(report.decide(*LOW, drift=drift, drift_required=True), "wait-owner", row)
            body = report.comment(data(risk=dict(RISK, head=HEAD), drift=drift))
            self.assertIn("open", gate(body, "Drift")[0], row)
            self.assertIn("Drift gate", gate(body, "Approval")[2], row)

    def test_by_spec_must_be_true(self):
        for value in ("false", "yes", 1):
            drift = MET + [{"kind": "outside", "text": "x", "by_spec": value}]
            self.assertEqual(report.decide(*LOW, drift=drift), "wait-owner", value)
        drift = MET + [{"kind": "outside", "text": "x", "by_spec": True}]
        self.assertEqual(report.decide(*LOW, drift=drift), "auto-merge")


GOOD_CHANGE = """---
id: 999
status: approved
approved_by: the owner
approved_on: 2026-11-17
---

# Change

## 2. Outcome and acceptance checks

1. The file says A.

## 7. Results

### Run 1

| Check in §2 | Command | Output | Verdict |
|---|---|---|---|
| 1 | `grep` | `1` | pass |
"""
SKIPPED = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="1">
<testcase classname="tests.plain_unit_test" name="test_a" time="0.1"><skipped message="x"/></testcase>
</testsuite></testsuites>
"""
# Each entry: a file of --out and a content that is wrong, missing ("" removes nothing: it writes an empty
# file) or strange. None of them is a clean input, so none of them can give "Ready".
BAD_INPUTS = [
    ("risk.json", ""), ("risk.json", "[]"), ("risk.json", '{"level": "LOW", "reasons": []}'),
    ("risk.json", '{"reasons": []}'), ("risk.json", '{"level": "low", "reasons": "x"}'),
    ("risk.json", "{}"), ("risk.json", '{"level": "low", "reasons": []}'),            # change 038: no head
    ("risk.json", json.dumps({"level": "low", "reasons": [], "head": ""})),
    ("risk.json", json.dumps({"level": "medium", "reasons": [], "head": HEAD})),
    ("risk.json", json.dumps({"level": "low", "reasons": [7], "head": HEAD})),
    ("pr.json", ""), ("pr.json", "{}"), ("pr.json", '{"body": null}'), ("pr.json", '{"body": ""}'),
    ("pr.json", '{"body": 7}'), ("pr.json", '{"body": "A long text with no labels."}'),
    ("findings.json", ""), ("findings.json", "{}"), ("findings.json", "[1]"), ("findings.json", '[{"text": "x"}]'),
    ("findings.json", '[{"kind": "BUG", "text": "x"}]'), ("findings.json", '[{"kind": "note", "text": "x"}]'),
    ("drift.json", ""), ("drift.json", "{}"), ("drift.json", "[]"), ("drift.json", '[{"kind": "outcome"}]'),
    ("drift.json", '[{"kind": "outcome", "state": "partly"}]'), ("drift.json", '[{"kind": "outside"}]'),
    ("drift.json", '[{"kind": "outcome", "state": "met"}, {"kind": "outside", "by_spec": null}]'),
    ("drift.json", '[{"kind": "outcome", "state": "met"}, {"kind": "constraint"}]'),
    ("drift.json", '[{"kind": "outcome", "state": "met"}, 7]'),
    ("junit.xml", ""), ("junit.xml", "<testsuites"), ("junit.xml", "<testsuites></testsuites>"),
    ("junit.xml", SKIPPED), ("junit.xml", JUNIT),
    ("preview.json", ""), ("preview.json", "[]"), ("preview.json", '{"failed": "no board"}'),
    ("pr.json", json.dumps({"body": BODY_TEXT.replace("**Owner must do:** nothing.",
                                                      "**Owner must do:** create the ruleset before the merge.")})),
    ("pr.json", json.dumps({"body": BODY_TEXT.replace("**Owner must do:** nothing.", "**Owner must do:** no")})),
    # change 039: the form of the old rule, and a field that is too long
    ("pr.json", json.dumps({"body": BODY_TEXT.replace("**", "")})),
    ("pr.json", json.dumps({"body": BODY_TEXT.replace("six pins move.", "x" * 241)})),
]


class TestNeverGreenerThanTheInputs(TestFailClosed):
    """The rule behind the findings of rounds 1 and 2: the heading and the gates come from the same
    values, and a wrong input never gives "Ready"."""

    def run_with(self, name=None, text=None):
        files = {"drift.json": json.dumps(MET)}
        change = GOOD_CHANGE
        if name == "change.md":
            change = text
        elif name:
            files[name] = text
        return self.run_main(change=change, **files)

    def icons(self, body):
        return {name: gate(body, name)[1].split(" ")[0] for name in ("Approval", "Drift", "Findings", "Checks", "Tests")}

    def test_the_clean_run_with_a_change_folder_is_ready(self):
        body = self.run_with()
        self.assertIn("## Ready — LOW", body)
        self.assertEqual(set(self.icons(body).values()), {report.OK})

    def test_no_wrong_input_gives_ready(self):
        for name, text in BAD_INPUTS:
            body = self.run_with(name, text)
            self.assertNotIn("## Ready", body, (name, text))

    def test_a_missing_risk_json_gives_no_merge_command(self):
        body = self.run_main(remove=("risk.json",))
        self.assertIn("## Not ready", body)
        self.assertNotIn("gh pr merge", body)
        self.assertIn("risk.json", gate(body, "Findings")[2])

    def test_a_wrong_risk_json_gives_no_merge_command(self):
        """Change 038: a risk.json with no head gave a comment for the commit 0000000."""
        for name, text in BAD_INPUTS:
            if name != "risk.json":
                continue
            body = self.run_with(name, text)
            self.assertIn("## Not ready", body, text)
            self.assertNotIn("gh pr merge", body, text)
            self.assertNotIn("0000000", body.replace("`0000000`", "", 1), text)
            self.assertIn("risk.json", gate(body, "Findings")[2], text)

    def test_the_text_of_the_change_folder_is_shown_and_decides_nothing(self):
        failed = self.run_with("change.md", GOOD_CHANGE.replace("| pass |", "| fail |"))
        self.assertIn("## Ready", failed)
        self.assertIn(report.WARN, gate(failed, "Checks")[1])
        self.assertIn("1 recorded fail", gate(failed, "Checks")[1])
        not_approved = self.run_with("change.md", GOOD_CHANGE.replace("approved_by: the owner", "approved_by:"))
        self.assertIn("## Ready", not_approved)
        self.assertNotIn("approved", not_approved)

    def test_lint_output_is_shown_and_decides_nothing(self):
        body = self.run_with("flake8.txt", "./x.py:1:1: F821 undefined name\n1\n")
        self.assertIn("## Ready", body)
        self.assertIn(report.WARN, gate(body, "Tests")[1])

    def test_ready_means_that_every_gate_is_green(self):
        for name, text in BAD_INPUTS + [(None, None)]:
            body = self.run_with(name, text)
            icons = self.icons(body)
            if "## Ready" in body:
                self.assertEqual(set(icons.values()), {report.OK}, (name, text))
            if report.BAD in icons.values():
                self.assertIn("## Not ready", body, (name, text, icons))


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


# ---- Change 042: only the public images go to the gist -------------------------------------------------------
# Spec: ../kb/work/042-pr-images-without-private-data/spec.md, sections 2.9 and 2.10.

PREVIEW = {
    "panels": [
        {"id": 81, "class": "public", "before": "prdikov-81-before.png", "after": "prdikov-81-after.png"},
        {"id": 86, "class": "private", "before": None, "after": None,
         "local": {"before": "private/prdikov-86-before.png", "after": "private/prdikov-86-after.png"}},
    ],
    "pages": [{"label": "prdikov", "before": "prdikov-page-before.png", "after": "prdikov-page-after.png",
               "held": [{"id": 86, "class": "private"}]}],
    "warnings": [], "leftovers": [], "failed": None,
}


class TestPrivateImages(unittest.TestCase):

    def _folder(self, tmp, names):
        os.makedirs(os.path.join(tmp, "private"), exist_ok=True)
        for name in names:
            with open(os.path.join(tmp, name), "wb") as fh:
                fh.write(b"\x89PNG\r\n")

    def test_only_public_images_are_uploaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._folder(tmp, ["prdikov-81-before.png", "prdikov-81-after.png", "prdikov-page-before.png",
                               "prdikov-page-after.png", "stale-ai-page-after.png",
                               os.path.join("private", "prdikov-86-before.png"),
                               os.path.join("private", "prdikov-86-after.png")])
            found = report.public_images(tmp, PREVIEW)
            self.assertEqual([os.path.relpath(p, tmp) for p in found],
                             ["prdikov-81-after.png", "prdikov-81-before.png", "prdikov-page-after.png",
                              "prdikov-page-before.png"])
            sneaky = json.loads(json.dumps(PREVIEW))
            sneaky["panels"][1]["after"] = "private/prdikov-86-after.png"
            sneaky["pages"][0]["before"] = "../other/prdikov-page-before.png"
            sneaky["panels"][0]["before"] = "missing.png"
            found = report.public_images(tmp, sneaky)
            self.assertEqual([os.path.relpath(p, tmp) for p in found],
                             ["prdikov-81-after.png", "prdikov-page-after.png"])
            self.assertEqual(report.public_images(tmp, {}), [])

    def test_upload_refuses_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._folder(tmp, [os.path.join("private", "prdikov-86-after.png"), "prdikov-page-after.png"])
            run = FakeRun()
            with self.assertRaises(ValueError):
                report.upload(9, [os.path.join(tmp, "prdikov-page-after.png"),
                                  os.path.join(tmp, "private", "prdikov-86-after.png")],
                              head="abcdef1234", owner="matejpristak", run=run)
            self.assertEqual(run.calls, [])

    def _main(self, *flags):
        files = {"risk.json": json.dumps({"level": "low", "reasons": [], "head": HEAD,
                                          "dashboards": ["spec/grafana/prdikov.json"]}),
                 "pr.json": json.dumps({"number": 9, "body": BODY_TEXT}), "findings.json": "[]",
                 "junit.xml": JUNIT.replace('<failure message="boom">x</failure>', ""), "flake8.txt": "0\n",
                 "preview.json": json.dumps(PREVIEW)}
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                with open(os.path.join(tmp, name), "w") as fh:
                    fh.write(text)
            self._folder(tmp, ["prdikov-81-before.png", "prdikov-81-after.png", "prdikov-page-before.png",
                               "prdikov-page-after.png"])
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(report.main(["--pr", "9", "--out", tmp, "--author", "matejpristak", *flags]), 0)
            return out.getvalue()

    def test_no_images_flag(self):
        shown = self._main()
        self.assertIn("## Ready — LOW", shown)
        self.assertIn("![after](prdikov-81-after.png)", shown)
        held = self._main("--no-images")
        self.assertIn("## Waiting for the owner — HIGH", held)
        self.assertIn("the agent held the images", held)
        self.assertNotIn("![", held)
        self.assertNotIn(".png", held)
        _, summary, inner = gate(held, "Screenshots")
        self.assertIn("held", summary)
        self.assertIn("private data", inner)

    def test_comment_private_and_unknown_panels(self):
        images = {
            "panels": [
                {"id": 81, "class": "public", "before": "https://g/81b.png", "after": "https://g/81a.png"},
                {"id": 86, "class": "private", "before": None, "after": None,
                 "local": {"before": "private/prdikov-86-before.png", "after": "private/prdikov-86-after.png"}},
                {"id": "AI 20", "class": "unknown", "before": None, "after": None,
                 "local": {"before": None, "after": "private/ai-20-after.png"},
                 "reason": "the measurement `foo` is not in the data table"},
            ],
            "pages": [{"label": "prdikov", "before": "https://g/pb.png", "after": "https://g/pa.png",
                       "held": [{"id": 86, "class": "private"}, {"id": 90, "class": "unknown"}]},
                      {"label": "ai", "before": None, "after": None, "held": []}],
            "warnings": [], "local_dir": "~/homeautomation/review-out/pr47"}
        body = report.comment(data(images=images, gist_id="abc123"))
        _, summary, inner = gate(body, "Screenshots")
        self.assertIn("3 panels (2 not uploaded), 2 pages", summary)
        self.assertIn("![after](https://g/81a.png)", inner)
        self.assertIn("**Panel 86** — private data, not uploaded. On the Mac: "
                      "`~/homeautomation/review-out/pr47/private/prdikov-86-before.png` (before), "
                      "`~/homeautomation/review-out/pr47/private/prdikov-86-after.png` (after).", inner)
        self.assertIn("**Panel AI 20** — not classed, not uploaded. On the Mac: absent (before), "
                      "`~/homeautomation/review-out/pr47/private/ai-20-after.png` (after).", inner)
        self.assertIn("the measurement `foo` is not in the data table", inner)
        self.assertIn("Add the measurement to the data table in `review/preview.py`.", inner)
        self.assertIn("Not shown: panel 86 (private data), panel 90 (not classed).", inner)
        self.assertNotIn("](private/", inner)
        self.assertNotIn("](None)", inner)
        self.assertEqual(inner.count("!["), 4)   # panel 81 and the page of prdikov, before and after
        self.assertIn("**Full page — ai** — not taken", inner)
        old = {"panels": [{"id": 81, "before": "https://g/b.png", "after": None}],
               "pages": [{"label": "ai", "before": "https://g/ab.png", "after": "https://g/aa.png"}], "warnings": []}
        _, summary, inner = gate(report.comment(data(images=old)), "Screenshots")
        self.assertIn("1 panels, 1 pages", summary)
        self.assertIn("_absent_", inner)


# ---- Change 032, revision 1: mocked data, equal images, the time range ----------------------------------------
# Spec: ../kb/work/032-pr-risk-review/spec.md, section 9.

MOCK = [{"measurement": "krb", "field": "apower", "value": "500.0", "points": 181}]


def _shots(**over):
    images = {"panels": [{"id": 83, "class": "public", "before": "https://g/b.png", "after": "https://g/a.png"}],
              "pages": [{"label": "prdikov", "before": "https://g/pb.png", "after": "https://g/pa.png", "held": []}],
              "warnings": []}
    images.update(over)
    return gate(report.comment(data(images=images, gist_id="abc123")), "Screenshots")


class TestMockedImages(unittest.TestCase):

    def test_mock_line(self):
        _, summary, inner = _shots(state=MOCK)
        self.assertTrue(inner.strip().startswith("Mocked data: `krb.apower` = `500.0` (181 points)."), inner[:200])
        self.assertIn("read a copy of the live data with these values", inner)
        self.assertIn("The live board does not show this state.", inner)
        self.assertTrue(summary.rstrip().endswith("mocked data"), summary)
        two = MOCK + [{"measurement": "estia", "field": "coil_on", "value": "true", "points": 0}]
        _, _, inner = _shots(state=two)
        self.assertIn("`krb.apower` = `500.0` (181 points); `estia.coil_on` = `true` (0 points).", inner)

    def test_no_state_no_mock_line(self):
        plain = _shots()
        for images in (_shots(state=[]), _shots(state=None)):
            self.assertEqual(images, plain)
        self.assertNotIn("Mocked data", plain[2])
        self.assertIn("1 panels, 1 pages", plain[1])
        self.assertNotIn("mocked", plain[1])
        self.assertNotIn("Time range", plain[2])
        self.assertNotIn("are equal", plain[2])

    def test_equal_line(self):
        line = "Before and after are equal. If the change shows only in one data state, add a Preview state"
        public = {"id": 83, "class": "public", "before": "https://g/b.png", "after": "https://g/a.png"}
        held = {"id": 86, "class": "private", "before": None, "after": None,
                "local": {"before": "private/prdikov-86-before.png", "after": "private/prdikov-86-after.png"}}
        _, _, inner = _shots(panels=[dict(public, equal=True), dict(held, equal=True)])
        self.assertEqual(inner.count(line), 2)
        for value in (False, None, "true", 1):
            _, _, inner = _shots(panels=[dict(public, equal=value), dict(held, equal=value)])
            self.assertNotIn(line, inner, value)
        _, _, inner = _shots(panels=[public, held])
        self.assertNotIn(line, inner)

    def test_unreadable_state_is_never_silent(self):
        for broken in ("krb", [1, 2], [{"measurement": "krb", "value": "1"}], {"krb": 1}, [MOCK[0], "x"],
                       [{"measurement": 1, "field": "apower", "value": "1"}], 7):
            _, summary, inner = _shots(state=broken)
            self.assertIn("Mocked data: the tool cannot read the values.", inner, broken)
            self.assertTrue(summary.rstrip().endswith("mocked data"), broken)

    def test_range_line(self):
        _, _, inner = _shots(range="now-24h")
        self.assertIn("Time range: `now-24h` to now, not the default range of the dashboard.", inner)
        _, _, inner = _shots(state=MOCK, range="now-7d")
        self.assertLess(inner.index("Mocked data"), inner.index("Time range: `now-7d` to now"))
        _, _, inner = _shots(range=None)
        self.assertNotIn("Time range", inner)
        for broken in (7, ["now-24h"], {"from": "now-24h"}):
            _, _, inner = _shots(range=broken)
            self.assertIn("Time range: not the default range of the dashboard.", inner, broken)

    def test_main_passes_the_state(self):
        files = {"risk.json": json.dumps({"level": "low", "reasons": [], "head": HEAD,
                                          "dashboards": ["spec/grafana/prdikov.json"]}),
                 "pr.json": json.dumps({"number": 9, "body": BODY_TEXT}), "findings.json": "[]",
                 "junit.xml": JUNIT.replace('<failure message="boom">x</failure>', ""), "flake8.txt": "0\n",
                 "preview.json": json.dumps(dict(PREVIEW, state=MOCK, range="now-24h"))}
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                with open(os.path.join(tmp, name), "w") as fh:
                    fh.write(text)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(report.main(["--pr", "9", "--out", tmp, "--author", "matejpristak"]), 0)
        shown = out.getvalue()
        self.assertIn("Mocked data: `krb.apower` = `500.0` (181 points).", shown)
        self.assertIn("Time range: `now-24h` to now", shown)
        self.assertIn("## Ready — LOW", shown)       # mocked data and a range decide nothing (D18)


if __name__ == '__main__':
    unittest.main()
