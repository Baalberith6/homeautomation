"""Change 032: the before and after screenshots of a dashboard change (review/preview.py).

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.5 and 2.6; plan.md, correction 1 (the sign-in check).
No network and no browser: requests and Playwright are replaced by fakes.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from review import preview

NOW = datetime(2026, 11, 7, 10, 0, 0, tzinfo=timezone.utc)

Q70 = 'from(bucket: "default")\n  |> range(start: v.timeRangeStart)\n  |> filter(fn: (r) => r._measurement == "weather")'
Q81 = ('month_start = date.truncate(t: now(), unit: 1mo)\nfrom(bucket: "default")\n  |> range(start: month_start)\n'
       '  |> filter(fn: (r) => r._measurement == "estia" or r._measurement == "FVE")')


def _dash(q81=Q81, extra=None):
    panels = [{"id": 70, "gridPos": {"h": 8, "w": 14, "x": 0, "y": 0}, "targets": [{"query": Q70}]},
              {"id": 81, "gridPos": {"h": 10, "w": 14, "x": 0, "y": 16}, "targets": [{"query": q81}]}]
    if extra:
        panels.append(extra)
    return {"uid": "q50mEhf7k", "title": "Prdikov", "version": 820, "id": 7, "time": {"from": "now-3h", "to": "now"},
            "panels": panels}


class TestPure(unittest.TestCase):

    def test_changed_panels(self):
        head = _dash(q81=Q81 + "\n  |> last()", extra={"id": 90, "targets": []})
        self.assertEqual(preview.changed_panels(_dash(), head), [81, 90])
        self.assertEqual(preview.changed_panels(_dash(), _dash()), [])
        self.assertEqual(preview.changed_panels({"dashboard": _dash()}, {"dashboard": _dash()}), [])

    def test_time_range(self):
        frm, to = preview.time_range(_dash(), NOW)
        self.assertEqual(to, int(NOW.timestamp() * 1000))
        self.assertEqual(frm, int((NOW - timedelta(hours=3)).timestamp() * 1000))
        month = dict(_dash(), time={"from": "now/M", "to": "now"})
        frm, _ = preview.time_range(month, NOW)
        self.assertEqual(frm, int(datetime(2026, 10, 31, 23, 0, tzinfo=timezone.utc).timestamp() * 1000))
        shots = preview.plan_shots("prdikov", [81], "pr9-prdikov-before", "pr9-prdikov-after", _dash(), _dash(),
                                   (1, 2), "http://g:3000")
        self.assertTrue(shots)
        for shot in shots:
            self.assertIn("from=1&to=2", shot["url"])

    def test_measurements(self):
        self.assertEqual(preview.measurements(Q81), {"estia", "FVE"})
        self.assertEqual(preview.measurements('from(bucket: "ai") |> range(start: -1d)'), set())

    def test_copy_window(self):
        shot = (int((NOW - timedelta(hours=3)).timestamp() * 1000), int(NOW.timestamp() * 1000))
        start, stop = preview.copy_window([Q70], shot, NOW)
        self.assertEqual(start, NOW - timedelta(hours=3))
        self.assertEqual(stop, NOW)
        start, _ = preview.copy_window([Q70, 'range(start: -30d)'], shot, NOW)
        self.assertEqual(start, NOW - timedelta(days=30))
        start, _ = preview.copy_window([Q81], shot, NOW)
        self.assertEqual(start, datetime(2026, 10, 31, 23, 0, tzinfo=timezone.utc))
        start, _ = preview.copy_window(['range(start: today())'], shot, NOW)
        self.assertEqual(start, datetime(2026, 11, 6, 23, 0, tzinfo=timezone.utc))  # midnight in Prague
        start, _ = preview.copy_window(['range(start: -40d)'], shot, NOW)
        self.assertEqual(start, NOW - timedelta(days=31))

    def test_copy_plan_mixed_queries(self):
        shot = (int((NOW - timedelta(hours=3)).timestamp() * 1000), int(NOW.timestamp() * 1000))
        panels = [{"id": 81, "targets": [{"query": Q81}]},
                  {"id": 90, "targets": [{"query": 'from(bucket: "default") |> range(start: v.timeRangeStart)'}]}]
        plan = preview.copy_plan(panels, shot, NOW)
        named = [p for p in plan if p[1]]
        whole = [p for p in plan if not p[1]]
        self.assertEqual([(p[0], p[1]) for p in named], [("default", {"estia", "FVE"})])
        self.assertEqual(len(whole), 1)
        self.assertEqual((whole[0][0], whole[0][2], whole[0][3]), ("default", NOW - timedelta(hours=3), NOW))

    def test_duplicate_panel_ids(self):
        self.assertEqual(preview.duplicate_ids(_dash(extra={"id": 81, "targets": []})), [81])
        self.assertEqual(preview.duplicate_ids(_dash()), [])
        self.assertIn("81", preview.duplicate_warning([81], "after"))

    def test_rewrite_only_changed_panels(self):
        head = _dash()
        after = preview.board(head, "pr9-prdikov-after", "PR 9 after", rewrite_ids={81})
        before = preview.board(_dash(), "pr9-prdikov-before", "PR 9 before")
        self.assertIn('from(bucket: "pr_preview")', after["panels"][1]["targets"][0]["query"])
        self.assertIn('from(bucket: "default")', after["panels"][0]["targets"][0]["query"])
        self.assertIn('from(bucket: "default")', before["panels"][1]["targets"][0]["query"])
        self.assertEqual((after["uid"], after["title"], after["id"]), ("pr9-prdikov-after", "PR 9 after", None))
        self.assertNotIn("version", after)
        self.assertIn('from(bucket: "default")', head["panels"][1]["targets"][0]["query"])
        self.assertEqual(preview.rewrite_buckets('from(bucket: "ai")'), 'from(bucket: "pr_preview")')

    def test_preview_block(self):
        md = "# T\n\n## Preview data\n\nText.\n\n```flux\nfrom(bucket: \"pr_preview\")\n```\n\n## Bug fixes\n"
        self.assertEqual(preview.preview_block(md), 'from(bucket: "pr_preview")\n')
        self.assertIsNone(preview.preview_block("# T\n\n## Results\n"))
        self.assertIn("Preview data missing", preview.PREVIEW_MISSING)

    def test_copy_flux_targets_pr_preview(self):
        flux = preview.copy_flux("default", {"weather"}, NOW - timedelta(hours=3), NOW)
        self.assertTrue(flux.rstrip().endswith('|> to(bucket: "pr_preview")'))
        self.assertIn('r._measurement == "weather"', flux)
        self.assertIn('from(bucket: "default")', flux)
        db = preview.Influx("http://i:8086", "t", session=FakeSession())
        with self.assertRaises(preview.GuardError):
            db.query('from(bucket: "ai") |> to(bucket: "default", org: "Home")')
        with self.assertRaises(preview.GuardError):
            db.query('from(bucket: "pr_preview") |> to(bucket: "ai")')
        db.query(flux)


class TestSignedIn(unittest.TestCase):

    def test_signed_in(self):
        ok = dict(url="http://g:3000/d/pr9-prdikov-before/x?kiosk", api_user_status=200, login_form_count=0,
                  panel_counts={81: 1})
        self.assertTrue(preview.signed_in(**ok)[0])
        for change in ({"url": "http://g:3000/login?redirectTo=%2Fd%2Fx"}, {"api_user_status": 401},
                       {"login_form_count": 1}, {"panel_counts": {81: 0}}):
            bad = dict(ok, **change)
            result, reason = preview.signed_in(**bad)
            self.assertFalse(result, change)
            self.assertTrue(reason)


class FakeSession:
    """Answers like Grafana and InfluxDB; records the calls."""

    def __init__(self, folder=(), folder_of=None):
        self.calls = []
        self.folder = list(folder)
        self.folder_of = folder_of or {}

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        body, status = {}, 200
        if "/api/search" in url:
            body = [{"uid": u} for u in self.folder]
        elif method == "GET" and "/api/dashboards/uid/" in url:
            uid = url.rsplit("/", 1)[1]
            body = {"meta": {"folderUid": self.folder_of.get(uid, preview.FOLDER_UID)}, "dashboard": {"uid": uid}}
        return SimpleNamespace(status_code=status, text="x", json=lambda: body, ok=True)


class TestGuard(unittest.TestCase):

    def test_guard(self):
        session = FakeSession()
        api = preview.GuardedGrafana("http://g:3000/", "t", session=session)
        for uid in ("q50mEhf7k", "ai", "x-board"):
            with self.assertRaises(preview.GuardError):
                api.put({"uid": uid, "panels": []})
            with self.assertRaises(preview.GuardError):
                api.delete(uid)
        self.assertEqual([c for c in session.calls if c[0] in ("POST", "DELETE")], [])
        api.put({"uid": "pr12-after", "panels": []})
        posts = [c for c in session.calls if c[0] == "POST"]
        self.assertEqual(posts[-1][2]["json"]["folderUid"], preview.FOLDER_UID)
        moved = FakeSession(folder_of={"pr12-after": "general"})
        with self.assertRaises(preview.GuardError):
            preview.GuardedGrafana("http://g:3000/", "t", session=moved).delete("pr12-after")

    def test_cleanup(self):
        session = FakeSession(folder=["pr3-prdikov-before", "pr3-prdikov-after"])
        api = preview.GuardedGrafana("http://g:3000/", "t", session=session)
        db_session = FakeSession()
        db = preview.Influx("http://i:8086", "t", session=db_session)
        left = preview.cleanup(api, db, now=NOW)
        self.assertEqual(left, ["pr3-prdikov-before", "pr3-prdikov-after"])
        deletes = [c[1] for c in session.calls if c[0] == "DELETE"]
        self.assertEqual(len(deletes), 2)
        influx_deletes = [c for c in db_session.calls if "/api/v2/delete" in c[1]]
        self.assertEqual(len(influx_deletes), 1)
        self.assertIn("bucket=pr_preview", influx_deletes[0][1])


# ---- Change 042: the images show no private data -------------------------------------------------------------
# Spec: ../kb/work/042-pr-images-without-private-data/spec.md; plan.md, "How the patterns read a query".

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POS = {"h": 8, "w": 10, "x": 14, "y": 8}


def _chain(cond, bucket="default"):
    return (f'from(bucket: "{bucket}")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n'
            f"  |> filter(fn: (r) => {cond})\n  |> last()")


CAR_ADDRESS = _chain('r._measurement == "Car" and r._field == "address_vw"')
CAR_PLUG = _chain('r._measurement == "Car" and r._field == "car_connected"')


def _real(name):
    with open(os.path.join(ROOT, "spec", "grafana", name + ".json")) as fh:
        return preview._dash(json.load(fh))


def _car_dash(q86=CAR_ADDRESS, variables=None):
    dash = _dash(extra={"id": 86, "type": "marcusolsson-dynamictext-panel", "gridPos": POS,
                        "targets": [{"query": q86}], "options": {"afterRender": "draw()"}})
    if variables is not None:
        dash["templating"] = {"list": variables}
    return dash


class FakeShooter:
    """Records the shots; can fail at one call."""

    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def __call__(self, token, shots, out_dir, api_user_url):
        self.calls.append(shots)
        if self.fail_at == len(self.calls):
            raise RuntimeError("no browser")


class _NoLock:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _result():
    return {"panels": [], "pages": [], "warnings": [], "leftovers": [], "failed": None}


def _posted(session):
    return [c[2]["json"]["dashboard"] for c in session.calls if c[0] == "POST" and "/api/dashboards/db" in c[1]]


def _deleted(session):
    return [c[1].rsplit("/", 1)[1] for c in session.calls if c[0] == "DELETE"]


class TestPrivate(unittest.TestCase):

    def test_classes_of_the_two_dashboards(self):
        expected = {"prdikov": ({67, 70, 80, 81, 83}, {86}), "ai": (set(range(1, 18)) | {19}, {18})}
        for name, (public, private) in expected.items():
            classes = {p["id"]: preview.panel_class(p)[0] for p in preview._panels(_real(name))}
            self.assertEqual({i for i, c in classes.items() if c == "public"}, public, name)
            self.assertEqual({i for i, c in classes.items() if c == "private"}, private, name)
            self.assertEqual([i for i, c in classes.items() if c == "unknown"], [], name)
            self.assertEqual(set(preview.held_panels(_real(name))), private, name)

    def test_query_classes(self):
        cases = [
            ('r._measurement == "Car"', "private"),
            ('r._measurement == "Car" and r._field == "car_connected"', "public"),
            ('r._measurement == "Car" and r._field == "charging_wallbox_power"', "public"),
            ('r._measurement == "Car" and r._field == "address_vw"', "private"),
            ('r._measurement == "Car" and (r._field == "car_connected" or r._field == "address_vw")', "private"),
            ('r._measurement == "ai_jobs" and (r._field == "run_s" or r._field == "state")', "public"),
            ('r._measurement == "ai_jobs"', "private"),
            ('r._measurement == "FVE" and r._field == "power" and r.string == "all"', "public"),
            ('r._measurement == "estia" or r._measurement == "FVE"', "public"),
            ('r._measurement == "foo"', "unknown"),
            ('r._field == "power"', "unknown"),
            ('r._measurement =~ /Car|FVE/', "unknown"),
            ('r._measurement != "Car"', "unknown"),
        ]
        for cond, expected in cases:
            self.assertEqual(preview.query_class(_chain(cond))[0], expected, cond)
            bracket = cond.replace("r._measurement", 'r["_measurement"]').replace("r._field", 'r["_field"]')
            self.assertEqual(preview.query_class(_chain(bracket))[0], expected, bracket)
        self.assertEqual(preview.query_class(_chain('r._measurement == "ai_usage"', bucket="ai"))[0], "public")
        cls, reason = preview.query_class(_chain('r._measurement == "foo"'))
        self.assertIn("`foo`", reason)
        self.assertIn("data table", reason)
        two = _chain('r._measurement == "weather"') + "\n" + CAR_ADDRESS
        self.assertEqual(preview.query_class(two)[0], "private")
        split = ('from(bucket: "default")\n  |> range(start: -1h)\n  |> filter(fn: (r) => r._measurement == "Car")\n'
                 '  |> filter(fn: (r) => r._field == "car_connected")')
        self.assertEqual(preview.query_class(split)[0], "public")

    def test_open_filters_fail_closed(self):
        self.assertEqual(preview.query_class(
            _chain('r._measurement == "Car" or r._field == "car_connected"'))[0], "private")
        self.assertEqual(preview.query_class(
            _chain('r._measurement == "FVE" or r._field == "power"'))[0], "unknown")
        self.assertEqual(preview.query_class(
            _chain('(r._measurement == "FVE" or r._field == "power") and r.string == "all"'))[0], "unknown")
        self.assertEqual(preview.query_class(
            _chain('(r._measurement == "Car" or r._measurement == "FVE") and r._field == "car_connected"'))[0],
            "public")
        reused = ('data = from(bucket: "default")\n  |> range(start: -1h)\n'
                  'data |> filter(fn: (r) => r._measurement == "weather")')
        self.assertEqual(preview.query_class(reused)[0], "unknown")
        self.assertEqual(preview.query_class(_chain('r._measurement == "weather"', bucket="other"))[0], "unknown")
        self.assertEqual(preview.query_class('from(bucket: v.bucket) |> range(start: -1h)')[0], "unknown")
        self.assertEqual(preview.query_class('import "sql"\n' + _chain('r._measurement == "weather"'))[0], "unknown")
        self.assertEqual(preview.query_class('buckets()')[0], "unknown")
        self.assertEqual(preview.query_class("")[0], "unknown")
        ok = ('import "array"\nimport "math"\n// from(bucket: "secret") is only a comment\n'
              + _chain('r._measurement == "weather"') + '\narray.from(rows: [{a: 1}]) |> yield(name: "x")')
        self.assertEqual(preview.query_class(ok)[0], "public")
        block = _chain('r._measurement == "weather"').replace(
            'fn: (r) => r._measurement == "weather"', 'fn: (r) => { return r._measurement == "weather" }')
        self.assertEqual(preview.query_class(block)[0], "unknown")
        text = _chain('r._measurement == "weather" and r.note == "a ) or ( b // c"')
        self.assertEqual(preview.query_class(text)[0], "public")

    def test_panel_classes(self):
        self.assertEqual(preview.panel_class({"id": 1, "type": "row"})[0], "public")
        self.assertEqual(preview.panel_class({"id": 1, "type": "text", "targets": []})[0], "public")
        self.assertEqual(preview.panel_class({"id": 1, "targets": [{"expr": "up"}]})[0], "unknown")
        self.assertEqual(preview.panel_class({"id": 1, "targets": [{"query": Q70}, {"query": CAR_ADDRESS}]})[0],
                         "private")
        self.assertEqual(preview.panel_class({"id": 1, "targets": [{"query": Q70}, {"query": CAR_PLUG}]})[0],
                         "public")
        self.assertEqual(preview.panel_class({"id": 1, "libraryPanel": {"uid": "x"}})[0], "unknown")
        self.assertEqual(preview.panel_class({"id": 1, "targets": [{"query": Q70}, {"panelId": 3}]})[0], "unknown")

    def test_public_board_has_placeholders(self):
        for name, pid, secret in (("prdikov", 86, "address_"), ("ai", 18, "raw_path")):
            dash = _real(name)
            self.assertIn(secret, json.dumps(dash))
            held = {i: c for i, (c, _) in preview.held_panels(dash).items()}
            out = preview.board(dash, f"pr9-{name}-after", "PR 9 after", held=held)
            self.assertNotIn(secret, json.dumps(out), name)
            tile = next(p for p in preview._panels(out) if p["id"] == pid)
            real = next(p for p in preview._panels(dash) if p["id"] == pid)
            self.assertEqual(tile["type"], "text")
            self.assertEqual(tile["gridPos"], real["gridPos"])
            self.assertNotIn("targets", tile)
            self.assertEqual(tile["options"]["content"], f"Private data: not shown (panel {pid})")
            self.assertEqual(len(list(preview._panels(out))), len(list(preview._panels(dash))))
            self.assertIn(secret, json.dumps(dash), "the source is not changed")
        row = {"id": 5, "type": "row", "panels": [{"id": 6, "gridPos": POS, "targets": [{"query": CAR_ADDRESS}]}]}
        nested = {"panels": [row, {"id": 7, "gridPos": POS, "targets": [{"query": _chain('r._measurement == "x"')}]}]}
        held = {i: c for i, (c, _) in preview.held_panels(nested).items()}
        self.assertEqual(held, {6: "private", 7: "unknown"})
        out = preview.board(nested, "pr9-x-after", "x", held=held)
        self.assertEqual(out["panels"][0]["panels"][0]["type"], "text")
        self.assertEqual(out["panels"][1]["options"]["content"], "Not classed: not shown (panel 7)")

    def _one(self, base, head, shooter, tmp, path="spec/grafana/prdikov.json"):
        session = FakeSession()
        api = preview.GuardedGrafana("http://g:3000/", "t", session=session)
        result = _result()
        preview._one(9, path, base, head, tmp, False, None, api, None, "t", NOW, shooter, result)
        return session, result

    def test_changed_panel_is_held_on_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            session, result = self._one(_car_dash(q86=CAR_PLUG), _car_dash(q86=CAR_ADDRESS), FakeShooter(), tmp)
        boards = {b["uid"]: b for b in _posted(session)}
        for uid in ("pr9-prdikov-before", "pr9-prdikov-after"):
            tile = next(p for p in boards[uid]["panels"] if p["id"] == 86)
            self.assertEqual(tile["type"], "text", uid)
            self.assertNotIn("Car", json.dumps(boards[uid]), uid)
        panel = result["panels"][0]
        self.assertEqual((panel["id"], panel["class"], panel["before"], panel["after"]), (86, "private", None, None))

    def test_second_pair_for_a_held_panel(self):
        head = _car_dash(q86=CAR_ADDRESS + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            shooter = FakeShooter()
            session, result = self._one(_car_dash(), head, shooter, tmp)
            self.assertTrue(os.path.isdir(os.path.join(tmp, "private")))
        uids = [b["uid"] for b in _posted(session)]
        self.assertEqual(uids, ["pr9-prdikov-before", "pr9-prdikov-after",
                                "pr9-prdikov-before-private", "pr9-prdikov-after-private"])
        self.assertEqual(sorted(_deleted(session)), sorted(uids))
        private = _posted(session)[3]
        self.assertEqual(next(p for p in private["panels"] if p["id"] == 86)["type"],
                         "marcusolsson-dynamictext-panel")
        self.assertEqual(len(shooter.calls), 2)
        public_shots, private_shots = shooter.calls
        self.assertEqual([s["name"] for s in public_shots], ["prdikov-page-before.png", "prdikov-page-after.png"])
        self.assertEqual([s["panels"] for s in public_shots], [{}, {}])
        self.assertEqual([s.get("page") for s in private_shots], [False, False])
        self.assertEqual([s["panels"] for s in private_shots],
                         [{86: "private/prdikov-86-before.png"}, {86: "private/prdikov-86-after.png"}])
        for shot in private_shots:
            self.assertIn("-private/", shot["url"])
        panel = result["panels"][0]
        self.assertEqual((panel["id"], panel["class"], panel["before"], panel["after"]), (86, "private", None, None))
        self.assertEqual(panel["local"], {"before": "private/prdikov-86-before.png",
                                          "after": "private/prdikov-86-after.png"})
        page = result["pages"][0]
        self.assertEqual((page["before"], page["after"]), ("prdikov-page-before.png", "prdikov-page-after.png"))
        self.assertEqual(page["held"], [{"id": 86, "class": "private"}])
        self.assertIsNone(result["failed"])
        with tempfile.TemporaryDirectory() as tmp:
            session, result = self._one(_car_dash(), head, FakeShooter(fail_at=2), tmp)
        self.assertEqual(len(_deleted(session)), 4)
        self.assertIn("Local image", result["failed"])
        self.assertEqual(result["panels"][0]["local"], {"before": None, "after": None})
        self.assertEqual(result["pages"][0]["before"], "prdikov-page-before.png")

    def test_no_second_pair_without_a_held_change(self):
        head = _car_dash()
        head["panels"][1]["targets"][0]["query"] = Q81 + "\n  |> last()"
        with tempfile.TemporaryDirectory() as tmp:
            shooter = FakeShooter()
            session, result = self._one(_car_dash(), head, shooter, tmp)
            self.assertEqual(os.listdir(tmp), [])
        self.assertEqual([b["uid"] for b in _posted(session)], ["pr9-prdikov-before", "pr9-prdikov-after"])
        self.assertEqual(len(shooter.calls), 1)
        self.assertEqual(shooter.calls[0][1]["panels"], {81: "prdikov-81-after.png"})
        panel = result["panels"][0]
        self.assertEqual((panel["id"], panel["class"], panel["before"], panel["after"]),
                         (81, "public", "prdikov-81-before.png", "prdikov-81-after.png"))
        self.assertNotIn("local", panel)
        self.assertEqual(result["pages"][0]["held"], [{"id": 86, "class": "private"}])

    def test_old_images_are_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "private"))
            for name in ("old-page-after.png", "risk.json", os.path.join("private", "old-86-after.png"),
                         os.path.join("private", "note.txt")):
                with open(os.path.join(tmp, name), "w") as fh:
                    fh.write("x")
            preview.clear_images(tmp)
            self.assertEqual(sorted(os.listdir(tmp)), ["private", "risk.json"])
            self.assertEqual(os.listdir(os.path.join(tmp, "private")), ["note.txt"])
            preview.clear_images(os.path.join(tmp, "missing"))

    def test_class_error_gives_failed(self):
        session = FakeSession()
        api = preview.GuardedGrafana("http://g:3000/", "t", session=session)
        shooter = FakeShooter()
        dashes = {"b": _car_dash(), "h": _car_dash(q86=CAR_PLUG)}
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "stale-page-after.png"), "w") as fh:
                fh.write("x")
            with mock.patch.object(preview, "_Lock", _NoLock), \
                    mock.patch.object(preview, "_show", lambda repo, sha, path: dashes[sha]), \
                    mock.patch.object(preview, "held_panels", side_effect=ValueError("boom")):
                result = preview.run(9, "b", "h", tmp, False, None, api, None, "t", now=NOW, shooter=shooter)
            self.assertEqual([f for f in os.listdir(tmp) if f.endswith(".png")], [])
        self.assertIn("ValueError", result["failed"])
        self.assertEqual(_posted(session), [])
        self.assertEqual(shooter.calls, [])
        self.assertEqual((result["panels"], result["pages"]), ([], []))

    def test_guard_accepts_private_uids(self):
        session = FakeSession()
        api = preview.GuardedGrafana("http://g:3000/", "t", session=session)
        for uid in ("pr9-prdikov-before-private", "pr9-ai-after-private"):
            api.put({"uid": uid, "panels": []})
            api.delete(uid)
        for uid in preview.LIVE_UIDS:
            with self.assertRaises(preview.GuardError):
                api.put({"uid": uid, "panels": []})
        self.assertEqual(len(_posted(session)), 2)

    def test_query_variable(self):
        custom = [{"type": "custom", "name": "DoD", "query": "60,70"}]
        self.assertTrue(preview.variables_public(_car_dash(variables=custom)))
        self.assertTrue(preview.variables_public(_car_dash()))
        for query in (CAR_ADDRESS, {"query": CAR_ADDRESS}, None):
            self.assertFalse(preview.variables_public(_car_dash(variables=[{"type": "query", "query": query}])))
        self.assertTrue(preview.variables_public(_car_dash(variables=[{"type": "query", "query": Q70}])))
        head = _car_dash(variables=[{"type": "query", "query": CAR_ADDRESS}])
        head["panels"][1]["targets"][0]["query"] = Q81 + "\n  |> last()"
        with tempfile.TemporaryDirectory() as tmp:
            shooter = FakeShooter()
            _, result = self._one(_car_dash(), head, shooter, tmp)
        self.assertEqual([s.get("page") for s in shooter.calls[0]], [False, False])
        self.assertEqual((result["pages"][0]["before"], result["pages"][0]["after"]), (None, None))
        self.assertTrue(any("variable" in w for w in result["warnings"]))
        self.assertEqual(result["panels"][0]["after"], "prdikov-81-after.png")


# ---- Change 032, revision 1: the Preview state ---------------------------------------------------------------
# Spec: ../kb/work/032-pr-risk-review/spec.md, section 9; plan.md, "Revision 1".

KRB = _chain('r._measurement == "krb" and r._field == "apower"')
STATE = [("krb", "apower", "500.0")]


def _state_md(*rows, heading="## Preview state"):
    lines = [heading, "", "| Measurement | Field | Value |", "|---|---|---|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "# T\n\n## Preview data\n\nNo data change.\n\n" + "\n".join(lines) + "\n\n## Bug fixes\n\nNone.\n"


def _krb_dash(query=KRB):
    return _dash(extra={"id": 83, "type": "marcusolsson-dynamictext-panel", "gridPos": POS,
                        "targets": [{"query": query}], "options": {"content": "x"}})


def _flux(session):
    return [c[2]["data"] for c in session.calls if "/api/v2/query" in c[1]]


def _query_of(dash, pid):
    return next(p for p in dash["panels"] if p["id"] == pid)["targets"][0]["query"]


class StateSession(FakeSession):
    """A FakeSession that answers a count query of InfluxDB with a number of points."""

    def __init__(self, points=181, **kwargs):
        super().__init__(**kwargs)
        self.points = points

    def request(self, method, url, **kwargs):
        answer = super().request(method, url, **kwargs)
        if "/api/v2/query" in url and "count()" in kwargs.get("data", ""):
            answer.text = f",result,table,_value\n,_result,0,{self.points}\n"
        return answer


class WritingShooter(FakeShooter):
    """Writes each image file. `content` maps a part of a file name to the bytes of that file."""

    def __init__(self, content=None, skip=()):
        super().__init__()
        self.content, self.skip = content or {}, skip

    def __call__(self, token, shots, out_dir, api_user_url):
        super().__call__(token, shots, out_dir, api_user_url)
        for shot in shots:
            names = list(shot["panels"].values()) + ([shot["name"]] if shot.get("page", True) else [])
            for name in names:
                if any(part in name for part in self.skip):
                    continue
                data = next((b for part, b in self.content.items() if part in name), b"same")
                with open(os.path.join(out_dir, name), "wb") as fh:
                    fh.write(data)


class TestState(unittest.TestCase):

    def _one(self, base, head, tmp, state=(), data_change=False, test_md=None, points=181, shooter=None, **more):
        session = StateSession(points=points)
        api = preview.GuardedGrafana("http://g:3000/", "t", session=session)
        influx = preview.Influx("http://i:8086", "t", session=session)
        result = _result()
        shooter = shooter or FakeShooter()
        preview._one(9, "spec/grafana/prdikov.json", base, head, tmp, data_change, test_md, api, influx, "t", NOW,
                     shooter, result, state=state, **more)
        return session, result, shooter

    def _run(self, tmp, test_md, dashes, data_change=False, **more):
        session = StateSession()
        api = preview.GuardedGrafana("http://g:3000/", "t", session=session)
        influx = preview.Influx("http://i:8086", "t", session=session)
        shooter = FakeShooter()
        with mock.patch.object(preview, "_Lock", _NoLock), \
                mock.patch.object(preview, "_show", lambda repo, sha, path: dashes[sha] if "prdikov" in path else None):
            result = preview.run(9, "b", "h", os.path.join(tmp, "out"), data_change, test_md, api, influx, "t",
                                 now=NOW, shooter=shooter, **more)
        return session, result, shooter

    def test_state_rows(self):
        self.assertEqual(preview.state_rows(_state_md(("`krb`", "`apower`", "`500.0`"))), STATE)
        small = _state_md(("krb", "apower", "500"), ("estia", "coil_on", "true"), ("ai_sync", "state", '"diverged"'),
                          ("weather", " temperature ", "-3.5"), heading="### Preview state")
        self.assertEqual(preview.state_rows(small),
                         [("krb", "apower", "500"), ("estia", "coil_on", "true"), ("ai_sync", "state", '"diverged"'),
                          ("weather", "temperature", "-3.5")])
        self.assertEqual(preview.state_rows(_state_md(("krb", "apower", "1"), heading="#### Preview state")),
                         [("krb", "apower", "1")])
        for none in ("# T\n\n## Preview state\n\nNone.\n\n## Results\n", "# T\n\n## Preview data\n\nNo data change.\n",
                     "# T\n\n## Preview state\n\nText with no table.\n", ""):
            self.assertEqual(preview.state_rows(none), [], none)
        other = ("## Preview state\n\nNone.\n\n## Results\n\n| Measurement | Field | Value |\n|---|---|---|\n"
                 "| a | b | 1 |\n")
        self.assertEqual(preview.state_rows(other), [])

    def test_state_rows_refuse(self):
        bad = [('kr"b', "apower", "1"), ("krb x", "apower", "1"), ("krb", "apower", "500.0)"), ("krb", "apower", "on"),
               ("krb", "apower", '"a"b"'), ("krb", "apower", '"a\\b"'), ("krb", "", "1"), ("krb", "apower", ""),
               ("krb", "apower) |> to(bucket: \"default\"", "1")]
        for row in bad:
            with self.assertRaises(ValueError, msg=row) as caught:
                preview.state_rows(_state_md(("krb", "apower", "1"), row))
            self.assertIn("Preview state: row 2 is not valid", str(caught.exception), row)
        with self.assertRaises(ValueError) as caught:
            preview.state_rows("## Preview state\n\n| Measurement | Field | Value |\n|---|---|---|\n| krb | apower |\n")
        self.assertIn("Preview state: row 1 is not valid", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            preview.state_rows(_state_md(*[("krb", f"f{i}", "1") for i in range(11)]))
        self.assertIn("more than 10 rows", str(caught.exception))
        self.assertEqual(len(preview.state_rows(_state_md(*[("krb", f"f{i}", "1") for i in range(10)]))), 10)

    def test_bad_state_gives_failed(self):
        dashes = {"b": _krb_dash(), "h": _krb_dash(KRB + "\n  |> yield()")}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "change.md")
            with open(path, "w") as fh:
                fh.write(_state_md(("krb", "apower", "lots"), heading="### Preview state"))
            session, result, shooter = self._run(tmp, path, dashes)
            with open(os.path.join(tmp, "out", "preview.json")) as fh:
                self.assertEqual(json.load(fh)["failed"], result["failed"])
        self.assertIn("Preview state: row 1 is not valid", result["failed"])
        self.assertEqual(_posted(session), [])
        self.assertEqual(shooter.calls, [])

    def test_state_flux_only_pr_preview(self):
        flux = preview.state_flux("krb", "apower", "500.0")
        self.assertEqual(flux, ('from(bucket: "pr_preview")\n'
                                "  |> range(start: 0)\n"
                                '  |> filter(fn: (r) => r._measurement == "krb" and r._field == "apower")\n'
                                "  |> map(fn: (r) => ({r with _value: 500.0}))\n"
                                '  |> to(bucket: "pr_preview")\n'))
        self.assertIn('_value: "diverged"', preview.state_flux("ai_sync", "state", '"diverged"'))
        session = FakeSession()
        db = preview.Influx("http://i:8086", "t", session=session)
        db.query(flux)
        self.assertEqual(len(session.calls), 1)
        for target in ("default", "ai"):
            with self.assertRaises(preview.GuardError):
                db.query(flux.replace('to(bucket: "pr_preview")', f'to(bucket: "{target}")'))
        self.assertEqual(len(session.calls), 1)

    def test_state_both_boards_read_the_copy(self):
        head = _krb_dash(KRB + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            session, result, shooter = self._one(_krb_dash(), head, tmp, state=STATE)
        flux = _flux(session)
        self.assertEqual(len(flux), 3)
        self.assertIn('from(bucket: "default")', flux[0])
        self.assertIn('r._measurement == "krb"', flux[0])
        self.assertTrue(flux[0].rstrip().endswith('|> to(bucket: "pr_preview")'))
        self.assertEqual(flux[1], preview.state_flux(*STATE[0]))
        self.assertIn("count()", flux[2])
        boards = {b["uid"]: b for b in _posted(session)}
        self.assertEqual(sorted(boards), ["pr9-prdikov-after", "pr9-prdikov-before"])
        for uid, board in boards.items():
            self.assertIn('from(bucket: "pr_preview")', _query_of(board, 83), uid)
            self.assertNotIn('from(bucket: "default")', _query_of(board, 83), uid)
            self.assertIn('from(bucket: "default")', _query_of(board, 70), uid)
            self.assertIn('from(bucket: "default")', _query_of(board, 81), uid)
        self.assertEqual(result["state"], [{"measurement": "krb", "field": "apower", "value": "500.0", "points": 181}])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(len(shooter.calls), 1)

    def test_state_copies_base_and_head_queries(self):
        base = _krb_dash(_chain('r._measurement == "aaa"'))
        head = _krb_dash(_chain('r._measurement == "bbb"'))
        with tempfile.TemporaryDirectory() as tmp:
            session, _, _ = self._one(base, head, tmp, state=[("aaa", "x", "1")])
        copy = _flux(session)[0]
        self.assertIn('r._measurement == "aaa"', copy)
        self.assertIn('r._measurement == "bbb"', copy)
        with tempfile.TemporaryDirectory() as tmp:    # with a data change and no state: the head only, as before
            session, _, _ = self._one(base, head, tmp, data_change=True)
        self.assertNotIn('"aaa"', _flux(session)[0])

    def test_state_run_empties_the_bucket(self):
        dashes = {"b": _krb_dash(), "h": _krb_dash(KRB + "\n  |> yield()")}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.md")
            with open(path, "w") as fh:
                fh.write(_state_md(("krb", "apower", "500.0")))
            session, result, _ = self._run(tmp, path, dashes)
        self.assertIsNone(result["failed"])
        kinds = [("delete" if "/api/v2/delete" in c[1] else "query") for c in session.calls if "/api/v2/" in c[1]]
        self.assertEqual(kinds, ["delete", "query", "query", "query", "delete"])
        for call in session.calls:
            if "/api/v2/delete" in call[1]:
                self.assertIn("bucket=pr_preview", call[1])
        self.assertEqual(result["state"][0]["points"], 181)

    def test_state_held_panel(self):
        head = _car_dash(q86=CAR_ADDRESS + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            session, result, _ = self._one(_car_dash(), head, tmp, state=[("Car", "address_vw", '"Nowhere"')])
        boards = {b["uid"]: b for b in _posted(session)}
        self.assertEqual(len(boards), 4)
        for uid in ("pr9-prdikov-before", "pr9-prdikov-after"):
            tile = next(p for p in boards[uid]["panels"] if p["id"] == 86)
            self.assertEqual(tile["type"], "text", uid)
            self.assertNotIn("Car", json.dumps(boards[uid]), uid)
        for uid in ("pr9-prdikov-before-private", "pr9-prdikov-after-private"):
            self.assertIn('from(bucket: "pr_preview")', _query_of(boards[uid], 86), uid)
            self.assertIn('from(bucket: "default")', _query_of(boards[uid], 81), uid)
        self.assertEqual(result["panels"][0]["class"], "private")

    def test_state_with_preview_data(self):
        head = _krb_dash(KRB + "\n  |> yield()")
        block = 'from(bucket: "pr_preview")\n  |> range(start: -3h)\n  |> to(bucket: "pr_preview")\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.md")
            with open(path, "w") as fh:
                fh.write("# T\n\n## Preview data\n\n```flux\n" + block + "```\n\n## Bug fixes\n")
            session, result, _ = self._one(_krb_dash(), head, tmp, state=STATE, data_change=True, test_md=path)
        flux = _flux(session)
        self.assertEqual([flux.index(preview.state_flux(*STATE[0])), flux.index(block)], [1, 3])
        self.assertIn("The before image also reads the preview data.", result["warnings"])
        self.assertNotIn(preview.PREVIEW_MISSING, result["warnings"])

    def test_no_state_is_the_run_of_today(self):
        head = _krb_dash(KRB + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            session, result, _ = self._one(_krb_dash(), head, tmp)
        self.assertEqual(_flux(session), [])
        self.assertNotIn("pr_preview", json.dumps(_posted(session)))
        self.assertEqual(result["state"], [])
        with tempfile.TemporaryDirectory() as tmp:
            session, result, _ = self._one(_krb_dash(), head, tmp, data_change=True)
        boards = {b["uid"]: b for b in _posted(session)}
        self.assertIn('from(bucket: "default")', _query_of(boards["pr9-prdikov-before"], 83))
        self.assertIn('from(bucket: "pr_preview")', _query_of(boards["pr9-prdikov-after"], 83))
        self.assertEqual(len(_flux(session)), 1)
        self.assertEqual(result["state"], [])
        self.assertEqual(result["warnings"], [preview.PREVIEW_MISSING])
        dashes = {"b": _krb_dash(), "h": head}
        with tempfile.TemporaryDirectory() as tmp:       # run with no file and no data change: no InfluxDB call
            session, result, _ = self._run(tmp, None, dashes)
        self.assertEqual([c for c in session.calls if "/api/v2/" in c[1]], [])
        self.assertEqual((result["state"], result["range"], result["failed"]), ([], None, None))

    def test_equal_images(self):
        head = _krb_dash(KRB + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            _, result, _ = self._one(_krb_dash(), head, tmp, shooter=WritingShooter())
        self.assertIs(result["panels"][0]["equal"], True)
        with tempfile.TemporaryDirectory() as tmp:
            _, result, _ = self._one(_krb_dash(), head, tmp, shooter=WritingShooter({"83-after": b"green"}))
        self.assertIs(result["panels"][0]["equal"], False)
        with tempfile.TemporaryDirectory() as tmp:
            _, result, _ = self._one(_krb_dash(), head, tmp, shooter=WritingShooter(skip=("83-after",)))
        self.assertIs(result["panels"][0]["equal"], False)
        with tempfile.TemporaryDirectory() as tmp:
            _, result, _ = self._one(_krb_dash(), head, tmp)                 # no file at all
        self.assertIs(result["panels"][0]["equal"], False)
        held = _car_dash(q86=CAR_ADDRESS + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            _, result, _ = self._one(_car_dash(), held, tmp, shooter=WritingShooter())
        self.assertEqual((result["panels"][0]["class"], result["panels"][0]["equal"]), ("private", True))
        with tempfile.TemporaryDirectory() as tmp:
            _, result, _ = self._one(_car_dash(), held, tmp, shooter=WritingShooter({"private/prdikov-86-after": b"n"}))
        self.assertIs(result["panels"][0]["equal"], False)

    def test_state_zero_points_warns(self):
        head = _krb_dash(KRB + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            _, result, shooter = self._one(_krb_dash(), head, tmp, state=[("krb", "nope", "1.0")], points=0)
        self.assertIn("Preview state not applied: the copy has no point of `krb.nope`.", result["warnings"])
        self.assertIsNone(result["failed"])
        self.assertEqual(result["state"], [{"measurement": "krb", "field": "nope", "value": "1.0", "points": 0}])
        self.assertEqual(len(shooter.calls), 1)

    def test_range_option(self):
        head = _krb_dash(KRB + "\n  |> yield()")
        with tempfile.TemporaryDirectory() as tmp:
            session, result, shooter = self._one(_krb_dash(), head, tmp, state=STATE, range_from="now-24h")
        self.assertEqual(result["range"], "now-24h")
        day_ago = int((NOW - timedelta(hours=24)).timestamp() * 1000)
        for shot in shooter.calls[0]:
            self.assertIn(f"from={day_ago}&to={int(NOW.timestamp() * 1000)}", shot["url"])
        self.assertIn("range(start: 2026-11-06T10:00:00Z, stop: 2026-11-07T10:00:00Z)", _flux(session)[0])
        with tempfile.TemporaryDirectory() as tmp:
            _, result, shooter = self._one(_krb_dash(), head, tmp)
        self.assertIsNone(result["range"])
        three_hours = int((NOW - timedelta(hours=3)).timestamp() * 1000)
        self.assertIn(f"from={three_hours}&", shooter.calls[0][0]["url"])
        dashes = {"b": _krb_dash(), "h": head}
        with tempfile.TemporaryDirectory() as tmp:
            session, result, shooter = self._run(tmp, None, dashes, range_from="now-40d")
        self.assertIn("more than 31 days", result["failed"])
        self.assertEqual(shooter.calls, [])
        with tempfile.TemporaryDirectory() as tmp:
            _, result, _ = self._run(tmp, None, dashes, range_from="now-7d")
        self.assertEqual((result["range"], result["failed"]), ("now-7d", None))


if __name__ == '__main__':
    unittest.main()
