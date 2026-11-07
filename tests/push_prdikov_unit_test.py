"""Change 032: the Prdikov push keeps the live setpoints (spec/grafana/push_prdikov.py).

Spec: ../kb/work/032-pr-risk-review/spec.md, section 2.10; plan.md, correction 2: a setpoint value changed
in the UI does not stop the push, and the push keeps it.
"""
import contextlib
import copy
import importlib.util
import io
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("push_prdikov",
                                               os.path.join(HERE, "..", "spec", "grafana", "push_prdikov.py"))
push_prdikov = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(push_prdikov)


def _prdikov(value="8", version=822, options="6,8,10"):
    opts = [{"text": v, "value": v, "selected": v == value} for v in options.split(",")]
    return {"meta": {"slug": "prdikov", "folderUid": ""},
            "dashboard": {"uid": "q50mEhf7k", "id": 7, "version": version, "title": "Prdikov",
                          "panels": [{"id": 81, "options": {"content": "<b>Self-suff.</b>"}}],
                          "templating": {"list": [{"name": "WallboxAmp", "type": "custom", "query": options,
                                                   "current": {"text": value, "value": value},
                                                   "options": opts}]}}}


class FakeApi:
    def __init__(self, live, status=200, backup_dir=None):
        self.live = live
        self.status = status
        self.backup_dir = backup_dir
        self.calls = []
        self.backups_at_post = None

    def get_dashboard(self, uid):
        self.calls.append(("GET", uid))
        return copy.deepcopy(self.live)

    def post_dashboard(self, body):
        self.calls.append(("POST", body))
        self.backups_at_post = os.listdir(self.backup_dir) if self.backup_dir else None
        if self.status == 200:
            pushed = dict(body["dashboard"], version=body["dashboard"]["version"] + 1)
            self.live = {"meta": self.live["meta"], "dashboard": pushed}
        return self.status, {"status": "success" if self.status == 200 else "version-mismatch"}


class Case(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = os.path.join(self.tmp.name, "prdikov.json")
        self.backups = os.path.join(self.tmp.name, "backups")
        push_prdikov.BACKUP_DIR = self.backups

    def tearDown(self):
        self.tmp.cleanup()

    def run_push(self, file_obj, api, dry_run=False):
        with open(self.file, "w") as fh:
            json.dump(file_obj, fh)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = push_prdikov.push(api, self.file, "test 032", dry_run=dry_run)
        self.output = out.getvalue()
        return code

    def posts(self, api):
        return [c[1] for c in api.calls if c[0] == "POST"]


class TestPush(Case):

    def test_backup_before_post(self):
        api = FakeApi(_prdikov(), backup_dir=None)
        os.makedirs(self.backups)
        api.backup_dir = self.backups
        self.assertEqual(self.run_push(_prdikov(), api), 0)
        self.assertEqual(len(api.backups_at_post), 1)
        self.assertTrue(api.backups_at_post[0].startswith("prdikov-"))

    def test_definitions_differ_stops(self):
        api = FakeApi(_prdikov(options="6,8,10,12"))
        self.assertEqual(self.run_push(_prdikov(), api), 3)
        self.assertEqual(self.posts(api), [])
        self.assertIn("templating DIFFERS", self.output)

    def test_live_templating_is_pushed(self):
        live = _prdikov(value="10")
        api = FakeApi(live)
        self.assertEqual(self.run_push(_prdikov(value="8"), api), 0)
        self.assertIn("templating EQUAL", self.output)
        pushed = self.posts(api)[0]["dashboard"]["templating"]
        self.assertEqual(pushed, live["dashboard"]["templating"])
        self.assertEqual(pushed["list"][0]["current"]["value"], "10")

    def test_overwrite_false_with_live_version(self):
        api = FakeApi(_prdikov(version=830))
        file_obj = _prdikov(version=820)
        file_obj["dashboard"]["id"] = 99
        self.assertEqual(self.run_push(file_obj, api), 0)
        body = self.posts(api)[0]
        self.assertIs(body["overwrite"], False)
        self.assertEqual((body["dashboard"]["version"], body["dashboard"]["id"]), (830, 7))
        with open(self.file) as fh:
            synced = json.load(fh)
        self.assertEqual(synced["dashboard"]["version"], 831)
        self.assertIn("meta", synced)

    def test_412_stops(self):
        api = FakeApi(_prdikov(), status=412)
        file_obj = _prdikov(version=820)
        self.assertEqual(self.run_push(file_obj, api), 4)
        with open(self.file) as fh:
            self.assertEqual(json.load(fh), file_obj)

    def test_refuses_other_uid(self):
        api = FakeApi(_prdikov())
        file_obj = _prdikov()
        file_obj["dashboard"]["uid"] = "ai"
        self.assertEqual(self.run_push(file_obj, api), 2)
        self.assertEqual(api.calls, [])

    def test_dry_run_sends_nothing(self):
        api = FakeApi(_prdikov(value="10"))
        self.assertEqual(self.run_push(_prdikov(), api, dry_run=True), 0)
        self.assertEqual(self.posts(api), [])
        self.assertIn("templating EQUAL", self.output)


if __name__ == '__main__':
    unittest.main()
