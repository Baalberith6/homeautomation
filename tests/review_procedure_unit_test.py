"""Change 038: the procedure of the review agent names a test environment that matches CI.

The agent runs pytest and flake8 in ~/homeautomation/review-test-venv (Python 3.11, made with uv, with the
requirements.txt of the PR head), not with the python3 of the Mac. These tests read the texts that the agent
and the sessions follow; they run no command.

Change: ../kb/work/038-review-test-venv/change.md.
"""
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read(*parts):
    with open(os.path.join(ROOT, *parts)) as fh:
        return fh.read()


class TestProcedure(unittest.TestCase):

    def setUp(self):
        self.md = read("review", "reviewer.md")

    def test_step_6_uses_the_test_environment(self):
        self.assertIn("| `T` | `~/homeautomation/review-test-venv/bin/python`", self.md)
        self.assertIn("uv venv --python 3.11 --allow-existing ~/homeautomation/review-test-venv", self.md)
        self.assertIn("uv pip install --python T -r WT/requirements.txt pytest flake8", self.md)
        self.assertNotIn("python3 -m pytest", self.md)
        self.assertNotIn("python3 -m flake8", self.md)
        self.assertEqual(self.md.count("`T -m pytest "), 3)   # the run and the two --collect-only runs
        self.assertEqual(self.md.count("`T -m flake8 "), 1)

    def test_a_failed_install_is_a_finding(self):
        self.assertIn("`requirements.txt` does not install on Python 3.11", self.md)
        step = self.md[self.md.index("**The test environment.**"):]
        self.assertIn("`bug`", step[:step.index("\n")])

    def test_node_is_checked(self):
        """Revision 1: the dashboard tests run panel JavaScript in node and skip without it."""
        line = [x for x in self.md.splitlines() if "`command -v node`" in x]
        self.assertEqual(len(line), 1)
        self.assertIn("`rule`", line[0])
        self.assertIn("`node` is not installed", line[0])
        self.assertIn("`node`", read("CLAUDE.md"))

    def test_python_version_matches_ci(self):
        ci = re.findall(r'python-version: \["([\d.]+)"\]', read(".github", "workflows", "test.yaml"))
        self.assertEqual(len(ci), 1)
        mine = set(re.findall(r"uv venv --python ([\d.]+)", self.md)) | set(re.findall(r"on Python ([\d.]+)", self.md))
        self.assertEqual(mine, {ci[0]})

    def test_claude_md_names_the_four_cases_and_the_environment(self):
        text = read("CLAUDE.md")
        self.assertIn("in four cases", text)
        self.assertNotIn("in three cases", text)
        self.assertIn("a row of `drift.json` that the tool cannot read", text)
        self.assertIn("`uv`", text)
        self.assertIn("~/homeautomation/review-test-venv", text)

    def test_requirements_header_names_the_second_venv(self):
        head = read("review", "requirements.txt")
        self.assertIn("review-test-venv", head)
        self.assertIn("reviewer.md", head)

    def test_step_9_private_images(self):
        """Change 042: the agent does not open the held images, and it checks the public ones."""
        step = [x for x in self.md.splitlines() if x.startswith("9. **Screenshots.**")]
        self.assertEqual(len(step), 1)
        self.assertIn("Do not open a file in `OUT/private/`", step[0])
        self.assertIn("no file name and no page path of the family wiki", step[0])
        self.assertIn("no data of a car", step[0])
        self.assertIn("`--no-images`", step[0])
        report = [x for x in self.md.splitlines() if x.startswith("10. **Report.**")]
        self.assertEqual(len(report), 1)
        self.assertIn("`--no-images`", report[0])
        self.assertIn("only the public images", report[0])
        self.assertIn("`private/`", read("CLAUDE.md"))


if __name__ == '__main__':
    unittest.main()
