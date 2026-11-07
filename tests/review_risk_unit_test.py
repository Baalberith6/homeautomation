"""Change 032: the risk level of a pull request (review/risk.py).

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.2, 2.3 and 2.9; plan.md, "Spec corrections".
Each test builds a small git repo in a temporary folder with two commits: no network.
"""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest

from review import risk

PRDIKOV = {
    "meta": {"slug": "prdikov"},
    "dashboard": {
        "uid": "q50mEhf7k",
        "panels": [{"id": 81, "type": "marcusolsson-dynamictext-panel", "options": {"content": "<b>Self-suff.</b>"}}],
        "templating": {"list": [{
            "name": "WallboxAmp", "type": "custom", "query": "6,8,10",
            "current": {"text": "8", "value": "8"},
            "options": [{"text": "6", "value": "6", "selected": False},
                        {"text": "8", "value": "8", "selected": True},
                        {"text": "10", "value": "10", "selected": False}],
        }]},
    },
}


def _git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=repo,
                          check=True, capture_output=True, text=True).stdout.strip()


def _write(repo, files):
    for path, text in files.items():
        full = os.path.join(repo, path)
        if text is None:
            if os.path.exists(full):
                os.remove(full)
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(text)


class RepoCase(unittest.TestCase):
    """A repo with a base commit and a head commit."""

    BASE = {"co2.py": 'client.publish("home/weather/sensors/co2", 1)\n', "README.md": "x\n"}

    def setUp(self):
        self.tmps = []

    def tearDown(self):
        for tmp in self.tmps:
            tmp.cleanup()

    def classify(self, head_files, base_files=None):
        """A new repo for each call: base = BASE + base_files, head = base + head_files."""
        tmp = tempfile.TemporaryDirectory()
        self.tmps.append(tmp)
        self.repo = tmp.name
        _git(self.repo, "init", "-q")
        files = dict(self.BASE)
        files.update(base_files or {})
        _write(self.repo, files)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "base")
        base = _git(self.repo, "rev-parse", "HEAD")
        _write(self.repo, head_files)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "--allow-empty", "-m", "head")
        head = _git(self.repo, "rev-parse", "HEAD")
        return risk.classify(base, head, repo_dir=self.repo)

    def assertHigh(self, result, rule):
        self.assertEqual(result["level"], "high", result)
        self.assertTrue(any(r.startswith(rule + ":") for r in result["reasons"]), result["reasons"])


class TestPathRules(RepoCase):

    def test_telegraf_files_are_high(self):
        for path in ("telegraf.conf", "telegraf-lxc-scripts.conf"):
            with self.subTest(path=path):
                self.assertHigh(self.classify({path: "[agent]\n"}), "Telegraf")

    def test_config_files_are_high(self):
        for path in ("config.py", "systemd/0-co2.service", "deploy.sh", "requirements.txt"):
            with self.subTest(path=path):
                self.assertHigh(self.classify({path: "x = 1\n"}), "Config")

    def test_common_is_high(self):
        self.assertHigh(self.classify({"common.py": "QOS = 2\n"}), "Shared module")

    def test_device_services_are_high(self):
        for path in ("wallbox.py", "inverter_setter.py", "estia_optimizer.py", "lights.py"):
            with self.subTest(path=path):
                self.assertHigh(self.classify({path: "x = 1\n"}), "Device commands")

    def test_harness_is_high(self):
        for path in (".github/workflows/x.yaml", "review/x.py", ".claude/agents/pr-reviewer.md"):
            with self.subTest(path=path):
                self.assertHigh(self.classify({path: "x\n"}), "Harness")

    def test_push_scripts_are_high(self):
        for path in ("spec/grafana/push_prdikov.py", "spec/grafana/push_ai_dashboard.py"):
            with self.subTest(path=path):
                self.assertHigh(self.classify({path: "x = 1\n"}), "Setpoints")


class TestSetpoints(RepoCase):

    def _with(self, change):
        head = json.loads(json.dumps(PRDIKOV))
        change(head["dashboard"]["templating"]["list"][0])
        return self.classify({"spec/grafana/prdikov.json": json.dumps(head, indent=2)},
                             {"spec/grafana/prdikov.json": json.dumps(PRDIKOV, indent=2)})

    def test_setpoint_definition_change_is_high(self):
        def add_option(var):
            var["query"] = "6,8,10,12"
            var["options"].append({"text": "12", "value": "12", "selected": False})
        self.assertHigh(self._with(add_option), "Setpoints")

    def test_setpoint_value_change_is_low(self):
        def new_value(var):
            var["current"] = {"text": "10", "value": "10"}
            for opt in var["options"]:
                opt["selected"] = opt["value"] == "10"
        result = self._with(new_value)
        self.assertEqual(result["level"], "low", result["reasons"])

    def test_new_dashboard_without_variables_is_low(self):
        result = self.classify({"spec/grafana/ai.json": json.dumps({"uid": "ai", "panels": [],
                                                                    "templating": {"list": []}})})
        self.assertEqual(result["level"], "low", result["reasons"])

    def test_panel_only_change_is_low(self):
        head = json.loads(json.dumps(PRDIKOV))
        head["dashboard"]["panels"][0]["options"]["content"] = "<b>Self-suff. (test 032)</b>"
        result = self.classify({"spec/grafana/prdikov.json": json.dumps(head, indent=2)},
                               {"spec/grafana/prdikov.json": json.dumps(PRDIKOV, indent=2)})
        self.assertEqual(result["level"], "low", result["reasons"])
        self.assertEqual(result["dashboards"], ["spec/grafana/prdikov.json"])
        self.assertFalse(result["data_change"])


class TestMessaging(RepoCase):

    def test_added_topic_is_high(self):
        result = self.classify({"co2.py": 'client.publish("home/weather/sensors/co2", 1)\n'
                                          'client.publish("home/weather/sensors/co2_test", 2)\n'})
        self.assertHigh(result, "Messaging")
        self.assertTrue(any("home/weather/sensors/co2_test" in r and "co2.py" in r for r in result["reasons"]))

    def test_subscribe_list_topic_counts(self):
        base = {"yr.py": 'subscribe(client, ["home/a", "home/b"])\n'}
        result = self.classify({"yr.py": 'subscribe(client, ["home/a"])\n'}, base)
        self.assertHigh(result, "Messaging")
        self.assertTrue(any("home/b" in r for r in result["reasons"]))

    def test_removed_influx_field_is_high(self):
        base = {"yr.py": 'w(Point("TempForecast").field("temperature", 1.0))\n'
                         'w(Point("TempForecast").field("wind_gust", 2.0))\n'}
        result = self.classify({"yr.py": 'w(Point("TempForecast").field("temperature", 1.0))\n'}, base)
        self.assertHigh(result, "Messaging")
        self.assertTrue(any("wind_gust" in r for r in result["reasons"]))

    def test_removed_payload_key_is_high(self):
        base = {"estia.py": 'client.publish("jsons/estia", json.dumps({"in": 1, "out": 2}))\n'}
        result = self.classify({"estia.py": 'client.publish("jsons/estia", json.dumps({"in": 1}))\n'}, base)
        self.assertHigh(result, "Messaging")
        self.assertTrue(any("out" in r for r in result["reasons"]))

    def test_changed_fstring_topic_is_high(self):
        base = {"skoda.py": 'client.publish(f"home/car/{name}", 1)\n'}
        result = self.classify({"skoda.py": 'client.publish(f"home/car/{name}/soc", 1)\n'}, base)
        self.assertHigh(result, "Messaging")

    def test_concatenated_topic_prefix_change_is_high(self):
        base = {"grafana_setter.py": 'client.publish("command/" + item["name"], value)\n'}
        result = self.classify({"grafana_setter.py": 'client.publish("cmd/" + item["name"], value)\n'}, base)
        self.assertHigh(result, "Messaging")
        self.assertTrue(any("command/{}" in r for r in result["reasons"]), result["reasons"])
        self.assertTrue(result["data_change"])

    def test_moved_publish_is_low(self):
        base = {"co2.py": 'def a(client):\n    client.publish("home/weather/sensors/co2", 1)\n\n\n'
                          'def b(client):\n    pass\n'}
        head = {"co2.py": 'def a(client):\n    pass\n\n\n'
                          'def b(client):\n    client.publish("home/weather/sensors/co2", 1)\n'}
        result = self.classify(head, base)
        self.assertEqual(result["level"], "low", result["reasons"])

    def test_data_change_flag(self):
        self.assertTrue(self.classify({"co2.py": 'client.publish("home/x", 1)\n'})["data_change"])
        self.assertTrue(self.classify({"telegraf.conf": "[agent]\n"})["data_change"])
        self.assertTrue(self.classify({"yr.py": "x = 2\n"}, {"yr.py": "x = 1\n"})["data_change"])


class TestTests(RepoCase):

    BASE = dict(RepoCase.BASE)
    BASE["tests/a_unit_test.py"] = ("import unittest\n\n\nclass A(unittest.TestCase):\n\n"
                                    "    def test_one(self):\n        self.assertTrue(True)\n\n"
                                    "    def test_two(self):\n        self.assertTrue(True)\n")

    def test_new_test_is_low_and_listed(self):
        result = self.classify({"tests/b_unit_test.py": "def test_new():\n    assert 1\n"})
        self.assertEqual(result["level"], "low", result["reasons"])
        self.assertEqual(result["new_tests"], ["tests/b_unit_test.py::test_new"])

    def test_edited_test_is_low_and_listed(self):
        head = ("import unittest\n\n\nclass A(unittest.TestCase):\n\n"
                "    def test_one(self):\n        self.assertEqual(1, 1)\n")
        result = self.classify({"tests/a_unit_test.py": head})
        self.assertEqual(result["level"], "low", result["reasons"])
        self.assertEqual(result["edited_tests"], ["tests/a_unit_test.py::A::test_one"])
        self.assertEqual(result["deleted_tests"], ["tests/a_unit_test.py::A::test_two"])


class TestMain(unittest.TestCase):

    def test_script_error_gives_high(self):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(out):
            code = risk.main(["--base", "nosuchsha", "--head", "nosuchsha2", "--repo", tmp])
        self.assertEqual(code, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["level"], "high")
        self.assertTrue(result["reasons"][0].startswith("risk script failed: "), result)

    def test_decide(self):
        self.assertEqual(risk.decide("low", 0, False, "matejpristak", False), "auto-merge")
        self.assertEqual(risk.decide("low", 1, False, "matejpristak", False), "fix-findings")
        self.assertEqual(risk.decide("low", 0, True, "Baalberith6", False), "fix-findings")
        self.assertEqual(risk.decide("high", 0, False, "matejpristak", False), "wait-owner")
        self.assertEqual(risk.decide("low", 0, False, "someone", False), "refuse")
        self.assertEqual(risk.decide("low", 0, False, "matejpristak", True), "refuse")


if __name__ == '__main__':
    unittest.main()
