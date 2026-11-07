"""Change 032: the PR comment of the review agent (review/report.py).

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.7 and 2.8. No network: subprocess.run is replaced.
"""
import os
import subprocess
import tempfile
import unittest
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
</testsuite></testsuites>
"""

RISK = {"level": "low", "reasons": [], "new_tests": ["tests/b_unit_test.py::test_new"],
        "edited_tests": ["tests/a_unit_test.py::A::test_one"], "deleted_tests": ["tests/a_unit_test.py::A::test_two"]}


class TestTable(unittest.TestCase):

    def setUp(self):
        self.junit = report.junit_results(JUNIT)
        base = {"tests/a.py::t%d" % i for i in range(9)}
        head = {"tests/a.py::t%d" % i for i in range(12)}
        self.md = report.table(SPEC, TESTS, self.junit, base, head, RISK)

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
        self.assertIn("3 passed (+3 vs main)", self.md)
        self.assertIn("tests/other_unit_test.py::TestX::test_broken", self.md)

    def test_test_lists(self):
        self.assertIn("tests/b_unit_test.py::test_new", self.md)
        self.assertIn("tests/a_unit_test.py::A::test_one", self.md)
        self.assertIn("tests/a_unit_test.py::A::test_two", self.md)
        self.assertIn("Not proven: 4", self.md)
        all_proven = report.table(SPEC.replace("4. A check with no test.\n", ""), TESTS, self.junit, set(), set(), RISK)
        self.assertIn("Not proven: none", all_proven)


class TestComment(unittest.TestCase):

    def test_comment_order(self):
        images = {"panels": [{"id": 81, "before": "https://g/b.png", "after": "https://g/a.png"}],
                  "page": {"before": "https://g/pb.png", "after": "https://g/pa.png"}, "warnings": []}
        findings = [{"file": "co2.py", "line": 23, "kind": "bug", "text": "swapped values"}]
        body = report.comment(dict(RISK, level="high", reasons=["Telegraf: telegraf.conf"]), findings, images,
                              "TABLE-HERE", "RAW-OUTPUT", decision="wait-owner", gist_id="abc123")
        self.assertTrue(body.startswith(report.MARKER))
        self.assertIn("<!-- gist:abc123 -->", body)
        order = [body.index(s) for s in ("Telegraf: telegraf.conf", "swapped values", "https://g/a.png",
                                          "TABLE-HERE", "<details>", "RAW-OUTPUT")]
        self.assertEqual(order, sorted(order))
        self.assertLess(len(body), 65536)

    def test_no_dashboard_change(self):
        body = report.comment(RISK, [], None, "T", "R", decision="auto-merge")
        self.assertIn("No dashboard change", body)


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
        elif cmd[:2] == ["git", "clone"]:
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
            for cmd, kwargs in run.calls:
                self.assertNotEqual(os.path.abspath(kwargs.get("cwd") or tmp), repo, cmd)
                self.assertFalse(cmd[:1] == ["git"] and "clone" not in cmd and "-C" not in cmd, cmd)
            run2 = FakeRun()
            gist2, _ = report.upload(9, [png], head="abcdef1234", gist_id="f00d", owner="matejpristak", run=run2)
            self.assertEqual(gist2, "f00d")
            self.assertFalse([c for c, _ in run2.calls if c[:3] == ["gh", "gist", "create"]])


if __name__ == '__main__':
    unittest.main()
