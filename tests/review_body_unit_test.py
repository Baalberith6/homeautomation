"""The PR body check of the review tool (review/body.py): the change line, then five fields with a bold label.

Each field is its own paragraph, and the owner action is the first field (change 039,
../kb/work/039-pr-body-readable-form/change.md). Decision 2026-11-17 in ../kb/decisions.md ("A short PR body,
and a review comment that starts with the owner").
"""
import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout

from review import body

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

GOOD = """**Change 037** (small path) · `../kb/work/037-security-pins-py39/change.md` · approved 2026-11-17

**Owner must do:** before deploy on .51, save pip freeze, then pip install -r requirements.txt.

**What:** six pins move to versions with no open alert. aiohttp stays for 036.

**Tested:** 398 passed; red at 1026288, green at d1405dc. Results: change.md section 7.

**Not covered:** real TLS handshakes, a real Tuya session, the real Rehau page.

**Revert:** revert the commit, reinstall from the saved freeze, redeploy.

\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)
"""

# The body of PR #50 as the session wrote it by hand on 2026-11-17, in the form that the owner accepted.
PR_50_NEW = """**Change 038** (small path, revision 1) · `../kb/work/038-review-test-venv/change.md` · approved 2026-11-17

**Owner must do:** merge this PR (high risk: `review/`). The `risk.json` check also wants each reason to be a \
text; that is outside the intent, so say if it must go. Nothing is deployed.

**What:** the review agent runs `pytest` and `flake8` in its own Python 3.11 environment, made with `uv`, and \
checks that `node` is there.

**Tested:** 506 passed, no skip, here and in CI. Red at 791c65d and e73f20f, green at 59ec6ea. Results: \
`change.md`, section 7.

**Not covered:** a review run that makes the environment with no help from the session (check 9).

**Revert:** revert the merge commit. `node` stays on the Mac.

\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)
"""

# The body of PR #50 before that: it had the form of the old rule, and the owner could hardly read it.
PR_50_OLD = """Change 038 (small path, revision 1): ../kb/work/038-review-test-venv/change.md, approved 2026-11-17.
What: the review agent makes ~/homeautomation/review-test-venv with uv (Python 3.11, the requirements of the \
PR head), checks that node is there, and runs pytest and flake8 in it. A risk.json needs a head commit. \
CLAUDE.md names four cases in which a low-risk PR waits.
Owner must do: merge this PR (high risk: review/). The form check of risk.json also wants each reason to be a \
text; this is outside the intent, so say if it must go. Nothing is deployed.
Tested: 506 passed, no skip, in the review environment with node (round 1, without node: 479 passed, 26 \
skipped); red at 791c65d and e73f20f, green at 59ec6ea. Results: change.md section 7.
Not covered: a review run that makes the environment with no help from the session (check 9, open until the \
first PR after the merge).
Revert: revert the merge commit. Nothing is deployed. node stays on the Mac (brew uninstall node removes it).

\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)
"""

LONG = """Change 037 (small path): `../kb/work/037-security-pins-py39/change.md`, approved 2026-11-17.

Moves the pins that Python 3.9 permits to versions with no open Dependabot alert:

| Package | Old | New | Alerts |
|---|---|---|---|
| certifi | 2024.7.4 | 2026.10.18 | #104 critical |
| lxml | 5.3.1 | 6.1.0 | #67 |

**Red** at `1026288` (old pins, Python 3.9.25):
```
E           AssertionError: 20 != 0
1 failed, 6 passed in 0.33s
```

**Deploy note:** `deploy.sh` does not install `requirements.txt`.
"""


class TestProblems(unittest.TestCase):

    def test_body_in_the_form_passes(self):
        self.assertEqual(body.problems(GOOD), [])

    def test_long_body_names_each_problem(self):
        found = " ".join(body.problems(LONG))
        for label in body.LABELS:
            self.assertIn(label, found)
        self.assertIn("table", found)
        self.assertIn("code block", found)

    def test_line_limit(self):
        extra = GOOD.replace("**Revert:**", "\n".join("Note %d." % i for i in range(8)) + "\n\n**Revert:**")
        found = body.problems(extra)
        self.assertEqual(len(found), 1)
        self.assertIn(str(body.MAX_LINES), found[0])

    def test_empty_owner_line_is_a_problem(self):
        found = body.problems(GOOD.replace("before deploy on .51, save pip freeze, then pip install -r requirements.txt.",
                                           ""))
        self.assertEqual(len(found), 1)
        self.assertIn("Owner must do:", found[0])

    def test_first_line_names_the_change(self):
        found = body.problems(GOOD.split("\n", 1)[1])
        self.assertEqual(len(found), 1)
        self.assertIn("first line", found[0])
        no_folder = GOOD.replace("**Change 037** (small path)", "No change folder (the owner's override)")
        self.assertEqual(body.problems(no_folder), [])

    def test_blank_lines_and_attribution_do_not_count(self):
        spaced = GOOD.replace("\n", "\n\n")
        self.assertEqual(body.problems(spaced), [])


class TestReadableForm(unittest.TestCase):
    """Change 039: the body of PR #50 had the six lines of the old rule, and GitHub showed one block of text."""

    def test_template_in_claude_md_passes_the_check(self):
        with open(os.path.join(ROOT, "CLAUDE.md")) as fh:
            section = fh.read().split("### The PR body", 1)[1].split("\n### ", 1)[0]
        template = section.split("```")[1].strip("\n")
        lines = template.splitlines()
        self.assertEqual(lines[0], "**Change NNN** (<full or small path>) · `../kb/work/NNN-<slug>/<file>` · approved <date>")
        self.assertEqual(lines[1], "")
        labels = [m.group(1) for m in re.finditer(r"^\*\*([A-Z][a-z ]+:)\*\* <", template, re.M)]
        self.assertEqual(labels, ["Owner must do:", "What:", "Tested:", "Not covered:", "Revert:"])
        self.assertEqual(body.problems(re.sub(r"<[^>]+>", "a text", template)), [])
        self.assertIn("one or two short sentences", section)
        self.assertIn("%d characters" % body.MAX_FIELD, section)

    def test_a_plain_label_is_a_problem(self):
        found = body.problems(GOOD.replace("**What:**", "What:"))
        self.assertEqual(len(found), 1)
        self.assertIn("`What:`", found[0])
        self.assertIn("bold", found[0])
        self.assertNotIn("Tested:", found[0])

    def test_fields_need_a_blank_line_between(self):
        found = body.problems(GOOD.replace("\n\n**Tested:**", "\n**Tested:**"))
        self.assertEqual(len(found), 1)
        self.assertIn("blank line", found[0])
        self.assertIn("`Tested:`", found[0])
        self.assertNotIn("Revert:", found[0])
        two_lines = GOOD.replace("aiohttp stays", "\naiohttp stays")  # a field of two lines is one paragraph
        self.assertEqual(body.problems(two_lines), [])

    def test_owner_must_do_is_the_first_field(self):
        parts = GOOD.split("\n\n")
        parts[1], parts[2] = parts[2], parts[1]
        found = body.problems("\n\n".join(parts))
        self.assertEqual(len(found), 1)
        self.assertIn("`What:`", found[0])
        self.assertIn("before `Owner must do:`", found[0])

    def test_field_limit(self):
        self.assertEqual(body.MAX_FIELD, 240)
        text = "six pins move to versions with no open alert. aiohttp stays for 036."
        self.assertEqual(body.problems(GOOD.replace(text, "x" * 240)), [])
        found = body.problems(GOOD.replace(text, "x" * 241))
        self.assertEqual(len(found), 1)
        self.assertIn("`What:`", found[0])
        self.assertIn("241", found[0])
        self.assertIn("240", found[0])

    def test_the_two_bodies_of_pr_50(self):
        self.assertEqual(body.problems(PR_50_NEW), [])
        self.assertEqual(max(len(v) for v in body.fields(PR_50_NEW).values()), 167)
        found = " ".join(body.problems(PR_50_OLD))
        self.assertIn("bold", found)
        self.assertIn("blank line", found)
        self.assertIn("before `Owner must do:`", found)
        self.assertIn("`What:` has 2", found)   # the three long sentences of the old field

    def test_docstring_shows_the_form(self):
        doc = body.__doc__
        self.assertIn("**Change NNN** (", doc)
        self.assertLess(doc.index("**Owner must do:** <"), doc.index("**What:** <"))
        self.assertNotIn("\n    What: <", doc)
        self.assertIn(str(body.MAX_FIELD), doc)


class TestFields(unittest.TestCase):

    def test_fields(self):
        got = body.fields(GOOD)
        self.assertEqual(got["Owner must do:"],
                         "before deploy on .51, save pip freeze, then pip install -r requirements.txt.")
        self.assertEqual(got["Revert:"], "revert the commit, reinstall from the saved freeze, redeploy.")
        self.assertEqual(body.fields(LONG), {})


class TestMain(unittest.TestCase):

    def _run(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "body.md")
            with open(path, "w") as fh:
                fh.write(text)
            out = io.StringIO()
            with redirect_stdout(out):
                code = body.main([path])
            return code, out.getvalue()

    def test_exit_codes(self):
        self.assertEqual(self._run(GOOD)[0], 0)
        code, out = self._run(LONG)
        self.assertEqual(code, 1)
        self.assertIn("Owner must do:", out)


if __name__ == '__main__':
    unittest.main()
