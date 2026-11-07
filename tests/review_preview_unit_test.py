"""Change 032: the before and after screenshots of a dashboard change (review/preview.py).

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.5 and 2.6; plan.md, correction 1 (the sign-in check).
No network and no browser: requests and Playwright are replaced by fakes.
"""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

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


if __name__ == '__main__':
    unittest.main()
