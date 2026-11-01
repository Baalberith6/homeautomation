"""Change 028: the AI dashboard (spec/grafana/ai.json) and its push script.

Spec: ../kb/work/028-ai-cost-dashboard/spec.md, section 2.3 "The dashboard" and 2.4 "The push of the dashboard".
The files are read inside the tests, so the other tests still run before they exist.
"""
import importlib.util
import io
import json
import os
from unittest.mock import MagicMock, patch

_DIR = os.path.join(os.path.dirname(__file__), '..', 'spec', 'grafana')
_JSON = os.path.join(_DIR, 'ai.json')
_PUSH = os.path.join(_DIR, 'push_ai_dashboard.py')

INFLUX_UID = "ceyru5v6xg3r4b"     # the data source reads every bucket (plan 028, step 4)
TOKEN = "secret-token-028-do-not-print"

# Title: panel type, from spec section 2.3.
PANELS = {
    "Total cost": "stat",
    "Month-end projection": "stat",
    "Cost per user": "bargauge",
    "Cost by agent": "piechart",
    "Cost per day": "timeseries",
    "Runs": "timeseries",
    "Cost by model": "table",
    "Tokens per day": "timeseries",
    "Cache share": "stat",
    "Calls with no price": "stat",
    "Queue now": "bargauge",
    "Retried jobs": "stat",
    "Most expensive jobs": "table",
    "Answers per day": "timeseries",
    "Cost of one answer": "stat",
    "Pushover sends": "gauge",
    "Space sync": "state-timeline",
    "Data age": "stat",
}
BUILT_IN = {"stat", "timeseries", "bargauge", "piechart", "table", "gauge", "state-timeline", "row"}


def _dashboard():
    with open(_JSON) as fh:
        return json.load(fh)


def _panels():
    return [p for p in _dashboard()["panels"] if p["type"] != "row"]


def _panel(title):
    return next(p for p in _panels() if p["title"] == title)


def _queries(panel):
    return [t["query"] for t in panel["targets"]]


def _push_module():
    spec = importlib.util.spec_from_file_location('push_ai_dashboard', _PUSH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_header():
    d = _dashboard()
    assert (d["uid"], d["title"], d["refresh"]) == ("ai", "AI", "5m")
    assert d["time"] == {"from": "now/M", "to": "now"}


def test_only_built_in_panel_types():
    types = {p["type"] for p in _dashboard()["panels"]}
    assert types <= BUILT_IN, types - BUILT_IN
    assert "marcusolsson-dynamictext-panel" not in types


def test_the_eighteen_panels():
    titles = [p["title"] for p in _panels()]
    assert sorted(titles) == sorted(PANELS)
    for p in _panels():
        assert p["type"] == PANELS[p["title"]], p["title"]


def test_every_query_reads_bucket_ai():
    for p in _panels():
        assert p["datasource"]["uid"] == INFLUX_UID, p["title"]
        assert p["targets"], p["title"]
        for t in p["targets"]:
            assert t["datasource"]["uid"] == INFLUX_UID, p["title"]
            assert 'from(bucket: "ai")' in t["query"], p["title"]
            assert "@" not in t["query"], p["title"]


def test_daily_windows_use_prague_time():
    for p in _panels():
        for q in _queries(p):
            if "aggregateWindow(every: 1d" in q:
                assert 'timezone.location(name: "Europe/Prague")' in q, p["title"]


def test_group_by_tag():
    for title, tag in (("Cost per user", "user"), ("Cost by agent", "kind"), ("Cost by model", "model"),
                       ("Cost per day", "user"), ("Answers per day", "user"), ("Space sync", "space")):
        assert any(f'group(columns: ["{tag}"])' in q for q in _queries(_panel(title))), title


def _overrides(panel):
    out = {}
    for o in panel["fieldConfig"]["overrides"]:
        if o["matcher"]["id"] == "byName":
            for prop in o["properties"]:
                if prop["id"] == "color":
                    out[o["matcher"]["options"]] = prop["value"]["fixedColor"]
    return out


def test_state_colours():
    assert _overrides(_panel("Runs")) == {"done": "#73BF69", "failed": "#F2495C", "pending": "#FF9830"}
    mapped = set()
    for m in _panel("Space sync")["fieldConfig"]["defaults"]["mappings"]:
        mapped |= set(m["options"])
    assert mapped == {"in-sync", "unpushed", "unreachable", "diverged", "dirty", "off", "unknown"}


def _response(status, body=None):
    r = MagicMock(status_code=status)
    r.json.return_value = body or {}
    r.text = json.dumps(body or {})
    return r


def test_push_calls(tmp_path):
    push = _push_module()
    local = tmp_path / "ai.json"
    local.write_text(json.dumps({"uid": "ai", "title": "AI", "id": 17, "version": 3, "panels": []}))
    live_before = {"dashboard": {"uid": "ai", "title": "AI", "id": 17, "version": 3, "panels": []}, "meta": {}}
    live_after = {"dashboard": {"uid": "ai", "title": "AI", "id": 17, "version": 4, "panels": []}, "meta": {}}
    with patch.dict(os.environ, {"GRAFANA_TOKEN": TOKEN}), \
            patch.object(push, "requests") as requests_mock, \
            patch.object(push, "DASHBOARD", str(local)), \
            patch.object(push, "BACKUP_DIR", str(tmp_path / "backups")), \
            patch("sys.stdout", new_callable=io.StringIO) as out, \
            patch("sys.stderr", new_callable=io.StringIO) as err:
        requests_mock.get.side_effect = [_response(200, live_before), _response(200, live_after)]
        requests_mock.post.return_value = _response(200, {"status": "success", "version": 4})
        code = push.main(["--push"])
    assert code == 0
    urls = [c.args[0] for c in requests_mock.get.call_args_list + requests_mock.post.call_args_list]
    assert [c.args[0].endswith("/api/dashboards/uid/ai") for c in requests_mock.get.call_args_list] == [True, True]
    post = requests_mock.post.call_args
    assert post.args[0].endswith("/api/dashboards/db")
    assert post.kwargs["json"]["overwrite"] is True and post.kwargs["json"]["dashboard"]["id"] is None
    assert not any("q50mEhf7k" in u or "/api/v1/provisioning" in u for u in urls)
    backups = list((tmp_path / "backups").iterdir())
    assert len(backups) == 1 and backups[0].name.startswith("ai-")
    assert json.loads(backups[0].read_text())["version"] == 3
    assert json.loads(local.read_text())["version"] == 4
    assert TOKEN not in out.getvalue() + err.getvalue()


def test_push_dry_run_sends_nothing():
    push = _push_module()
    with patch.dict(os.environ, {"GRAFANA_TOKEN": TOKEN}), \
            patch.object(push, "requests") as requests_mock, \
            patch("sys.stdout", new_callable=io.StringIO) as out:
        code = push.main(["--dry-run"])
    assert code == 0 and requests_mock.method_calls == []
    assert "POST /api/dashboards/db" in out.getvalue()
    assert TOKEN not in out.getvalue()


def test_token_is_never_printed(tmp_path):
    push = _push_module()
    local = tmp_path / "ai.json"
    local.write_text(json.dumps({"uid": "ai", "title": "AI", "panels": []}))
    with patch.dict(os.environ, {"GRAFANA_TOKEN": TOKEN}), \
            patch.object(push, "requests") as requests_mock, \
            patch.object(push, "DASHBOARD", str(local)), \
            patch.object(push, "BACKUP_DIR", str(tmp_path / "backups")), \
            patch("sys.stdout", new_callable=io.StringIO) as out, \
            patch("sys.stderr", new_callable=io.StringIO) as err:
        requests_mock.get.return_value = _response(500, {"message": "boom"})
        code = push.main(["--push"])
    assert code != 0
    assert TOKEN not in out.getvalue() + err.getvalue()
