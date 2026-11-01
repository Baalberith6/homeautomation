"""Push the AI dashboard (spec/grafana/ai.json, UID "ai") to Grafana, then sync the live JSON back.

Usage, from the repo root:

    GRAFANA_TOKEN=... python3 spec/grafana/push_ai_dashboard.py --dry-run
    GRAFANA_TOKEN=... python3 spec/grafana/push_ai_dashboard.py --push
    GRAFANA_TOKEN=... python3 spec/grafana/push_ai_dashboard.py --fetch

GRAFANA_TOKEN is the service account token (grafanaServiceAccountToken in secret.py). The script
reads it from the environment only and never prints it. --dry-run sends nothing. --push saves the
live dashboard to ~/homeautomation/grafana-backups/ first (an edit made in the UI is never lost),
pushes ai.json with overwrite, and writes the live JSON back to ai.json (the sync-back rule).
--fetch does the sync-back alone. The script touches only the dashboard "ai": never Prdikov
(q50mEhf7k), never the alert rules. The data comes from the librarian of ../ai (change 028).

Spec: ../kb/work/028-ai-cost-dashboard/spec.md, section 2.4
"""
import argparse
import json
import os
import sys
from datetime import datetime

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from config import grafanaConfig  # noqa: E402

UID = "ai"
DASHBOARD = os.path.join(HERE, "ai.json")
BACKUP_DIR = os.path.expanduser("~/homeautomation/grafana-backups")


class GrafanaError(Exception):
    pass


class Grafana:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _check(self, method, path, r, allow):
        if r.status_code in allow:
            return None
        if r.status_code >= 400:
            raise GrafanaError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json() if r.text else {}

    def get(self, path, allow=()):
        return self._check("GET", path, requests.get(self.base + path, headers=self.headers, timeout=10), allow)

    def post(self, path, body):
        return self._check("POST", path, requests.post(self.base + path, headers=self.headers, json=body,
                                                       timeout=10), ())


def planned_calls():
    """The calls of --push, in order."""
    return [("GET", f"/api/dashboards/uid/{UID}"), ("POST", "/api/dashboards/db"),
            ("GET", f"/api/dashboards/uid/{UID}")]


def fetch(api):
    """Write the live dashboard to ai.json. Returns its version."""
    live = api.get(f"/api/dashboards/uid/{UID}")["dashboard"]
    with open(DASHBOARD, "w") as fh:
        json.dump(live, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"synced back ai.json: version {live.get('version')}")
    return live.get("version")


def push(api):
    live = api.get(f"/api/dashboards/uid/{UID}", allow=(404,))
    if live is not None:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        path = os.path.join(BACKUP_DIR, f"ai-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
        with open(path, "w") as fh:
            json.dump(live["dashboard"], fh, indent=2, ensure_ascii=False)
        print(f"saved the live dashboard (version {live['dashboard'].get('version')}): {path}")
    with open(DASHBOARD) as fh:
        dashboard = json.load(fh)
    if dashboard.get("uid") != UID:
        raise GrafanaError(f"ai.json has the uid {dashboard.get('uid')!r}, not {UID!r}")
    dashboard["id"] = None
    result = api.post("/api/dashboards/db", {"dashboard": dashboard, "overwrite": True, "message": "028 push"})
    print(f"pushed the dashboard {UID!r}: {result.get('status')}, version {result.get('version')}")
    fetch(api)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Push the AI dashboard (change 028) to Grafana.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="print the calls, send nothing")
    mode.add_argument("--push", action="store_true", help="back up the live dashboard, push ai.json, sync back")
    mode.add_argument("--fetch", action="store_true", help="write the live dashboard to ai.json")
    args = parser.parse_args(argv)
    if args.dry_run:
        for method, path in planned_calls():
            print(f"{method} {path}")
        return 0
    token = os.environ.get("GRAFANA_TOKEN")
    if not token:
        print("GRAFANA_TOKEN is not set.", file=sys.stderr)
        return 2
    api = Grafana(grafanaConfig["ip_address"], token)
    try:
        if args.push:
            return push(api)
        fetch(api)
        return 0
    except GrafanaError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
