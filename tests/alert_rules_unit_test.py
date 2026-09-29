"""Change 020: the four alert rules, the notification policy, and push_alerts.py.

Spec: ../kb/work/020-failures-visible-automatically/spec.md, section 2 "Alert rules" and "Notification".
The files are read inside the tests, so the old tests still run before they exist.
"""
import importlib.util
import io
import json
import os
import unittest
from unittest.mock import MagicMock, patch

_DIR = os.path.join(os.path.dirname(__file__), '..', 'spec', 'grafana')
_RULES = os.path.join(_DIR, 'alerts', '020-rules.json')
_PUSH = os.path.join(_DIR, 'push_alerts.py')

INFLUX_UID = "ceyru5v6xg3r4b"
LOKI_UID = "fezr2b11231fkd"

# uid: (for, noDataState, execErrState), from spec section 2, "Alert rules".
STATES = {
    "020-unit-down": ("2m", "Alerting", "Alerting"),
    "020-restart-loop": ("0s", "Alerting", "Alerting"),
    "020-error-line": ("0s", "OK", "Alerting"),
    "020-broker-port": ("2m", "Alerting", "Alerting"),
}


def _config():
    with open(_RULES) as fh:
        return json.load(fh)


def _rules():
    return {r["uid"]: r for r in _config()["rule_group"]["rules"]}


def _query(rule):
    model = rule["data"][0]["model"]
    return model.get("query") or model.get("expr")


def _threshold(rule):
    for step in rule["data"]:
        if step["model"].get("type") == "threshold":
            return step["model"]["conditions"][0]["evaluator"]
    raise AssertionError("no threshold step in " + rule["uid"])


def _push_module():
    spec = importlib.util.spec_from_file_location('push_alerts', _PUSH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRules(unittest.TestCase):

    def test_four_rules(self):
        config = _config()
        group = config["rule_group"]
        self.assertEqual(config["folder"], {"uid": "alerts", "title": "Alerts"})
        self.assertEqual(group["title"], "020")
        self.assertEqual(group["folderUid"], "alerts")
        self.assertEqual(group["interval"], 60)
        self.assertEqual(set(_rules()), set(STATES))
        for rule in group["rules"]:
            self.assertEqual(rule["folderUID"], "alerts", rule["uid"])
            self.assertEqual(rule["ruleGroup"], "020", rule["uid"])

    def test_rule_states(self):
        for uid, rule in _rules().items():
            self.assertEqual((rule["for"], rule["noDataState"], rule["execErrState"]), STATES[uid], uid)

    def test_r1_query(self):
        rule = _rules()["020-unit-down"]
        query = _query(rule)
        self.assertIn('r._field == "active_code"', query)
        self.assertIn('telegraf.service', query)
        self.assertIn('influxdb.service', query)
        self.assertEqual(_threshold(rule), {"type": "gt", "params": [0]})

    def test_r3_query(self):
        query = _query(_rules()["020-error-line"])
        self.assertEqual(query.count("[65m]"), 4)
        for needle in ('"^ERROR "', '" E! "', '"lvl=error"', '"Error"'):
            self.assertIn(needle, query)
        self.assertEqual(_threshold(_rules()["020-error-line"]), {"type": "gt", "params": [0]})

    def test_r2_non_negative(self):
        rule = _rules()["020-restart-loop"]
        self.assertIn("difference(nonNegative: true)", _query(rule))
        self.assertIn("range(start: -10m)", _query(rule))
        self.assertEqual(_threshold(rule), {"type": "gt", "params": [3]})

    def test_r4_query(self):
        rule = _rules()["020-broker-port"]
        self.assertIn('r._measurement == "net_response"', _query(rule))
        self.assertIn('"192.168.1.52"', _query(rule))
        self.assertEqual(_threshold(rule), {"type": "gt", "params": [0]})

    def test_datasource_uids(self):
        for uid, rule in _rules().items():
            want = LOKI_UID if uid == "020-error-line" else INFLUX_UID
            self.assertEqual(rule["data"][0]["datasourceUid"], want, uid)

    def test_summary_names_unit(self):
        for uid, rule in _rules().items():
            summary = rule["annotations"]["summary"]
            if uid == "020-broker-port":
                self.assertTrue(summary.startswith("mosquitto: "), summary)
            else:
                self.assertIn("{{ $labels.unit }}", summary, uid)

    def test_policy(self):
        config = _config()
        policy = config["policy"]
        self.assertEqual(policy["receiver"], config["contact_point"])
        self.assertEqual(config["contact_point"], "Pushover")
        self.assertEqual(policy["group_by"], ["alertname", "unit"])
        self.assertEqual(policy["group_wait"], "30s")
        self.assertEqual(policy["group_interval"], "5m")
        self.assertEqual(policy["repeat_interval"], "24h")


class TestPush(unittest.TestCase):

    TOKEN = "secret-token-020-do-not-print"

    def test_push_dry_run_sends_nothing(self):
        push = _push_module()
        with patch.dict(os.environ, {"GRAFANA_TOKEN": self.TOKEN}), \
                patch.object(push, "requests") as requests_mock, \
                patch("sys.stdout", new_callable=io.StringIO) as out:
            code = push.main(["--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(requests_mock.method_calls, [])
        text = out.getvalue()
        self.assertNotIn(self.TOKEN, text)
        self.assertIn("PUT /api/v1/provisioning/folder/alerts/rule-groups/020", text)
        self.assertIn("PUT /api/v1/provisioning/policies", text)

    def test_push_stops_without_contact_point(self):
        push = _push_module()
        points = MagicMock(status_code=200)
        points.json.return_value = [{"name": "email receiver", "type": "email"}]
        with patch.dict(os.environ, {"GRAFANA_TOKEN": self.TOKEN}), \
                patch.object(push, "requests") as requests_mock, \
                patch("sys.stdout", new_callable=io.StringIO) as out, \
                patch("sys.stderr", new_callable=io.StringIO) as err:
            requests_mock.get.return_value = points
            code = push.main(["--push"])
        self.assertNotEqual(code, 0)
        requests_mock.put.assert_not_called()
        requests_mock.post.assert_not_called()
        self.assertNotIn(self.TOKEN, out.getvalue() + err.getvalue())


if __name__ == '__main__':
    unittest.main()
