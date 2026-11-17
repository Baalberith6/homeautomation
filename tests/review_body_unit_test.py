"""The PR body check of the review tool (review/body.py): six labelled lines, the owner action in a fixed place.

Decision 2026-11-17 in ../kb/decisions.md ("A short PR body, and a review comment that starts with the owner").
"""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from review import body

GOOD = """Change 037 (small path): ../kb/work/037-security-pins-py39/change.md, approved 2026-11-17.
What: six pins move to versions with no open alert. aiohttp stays for 036.
Owner must do: before deploy on .51, save pip freeze, then pip install -r requirements.txt.
Tested: 398 passed; red at 1026288, green at d1405dc. Results: change.md section 7.
Not covered: real TLS handshakes, a real Tuya session, the real Rehau page.
Revert: revert the commit, reinstall from the saved freeze, redeploy.

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

    def test_six_line_body_passes(self):
        self.assertEqual(body.problems(GOOD), [])

    def test_bold_labels_pass(self):
        bold = GOOD
        for label in body.LABELS:
            bold = bold.replace(label, "**" + label + "**")
        self.assertEqual(body.problems(bold), [])

    def test_long_body_names_each_problem(self):
        found = " ".join(body.problems(LONG))
        for label in body.LABELS:
            self.assertIn(label, found)
        self.assertIn("table", found)
        self.assertIn("code block", found)

    def test_line_limit(self):
        extra = GOOD.replace("Revert:", "\n".join("Note %d." % i for i in range(8)) + "\nRevert:")
        found = body.problems(extra)
        self.assertEqual(len(found), 1)
        self.assertIn(str(body.MAX_LINES), found[0])

    def test_empty_owner_line_is_a_problem(self):
        found = body.problems(GOOD.replace("before deploy on .51, save pip freeze, then pip install -r requirements.txt.",
                                           ""))
        self.assertEqual(len(found), 1)
        self.assertIn("Owner must do:", found[0])

    def test_blank_lines_and_attribution_do_not_count(self):
        spaced = GOOD.replace("\n", "\n\n")
        self.assertEqual(body.problems(spaced), [])


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
