"""Change 022: venv/ and data/ at the repo root are ignored, so a deploy on .51 keeps them.

deploy.sh stashed the untracked venv/ and data/ on each deploy, and the running services lost
their virtualenv for some seconds (0-co2, 2026-09-29 23:10:55).
Spec: ../kb/work/022-deploy-keeps-venv/spec.md, section 8, check 2.
"""
import os
import subprocess
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _in_git():
    try:
        return subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT,
                              capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def _ignored(path):
    # Only the repo's own .gitignore counts: no global excludes file, and no look at the index.
    return subprocess.run(["git", "-c", "core.excludesFile=", "check-ignore", "-q", "--no-index", path],
                          cwd=ROOT).returncode == 0


@unittest.skipUnless(_in_git(), "not a git checkout")
class TestIgnore(unittest.TestCase):

    def test_host_dirs_ignored(self):
        for path in ("venv/x", "venv_new/x", "data/x"):
            self.assertTrue(_ignored(path), path)

    def test_tracked_paths_not_ignored(self):
        for path in ("tests/data/x.json", "common.py", "spec/grafana/alerts/020-rules.json"):
            self.assertFalse(_ignored(path), path)


if __name__ == '__main__':
    unittest.main()
