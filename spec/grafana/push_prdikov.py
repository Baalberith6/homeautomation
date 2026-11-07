"""Push the Prdikov dashboard (spec/grafana/prdikov.json, UID q50mEhf7k) and keep the owner's live setpoints.

Usage, from the repo root:

    GRAFANA_TOKEN=... python3 spec/grafana/push_prdikov.py --dry-run [--file PATH]
    GRAFANA_TOKEN=... python3 spec/grafana/push_prdikov.py --push [--file PATH] [--message TEXT]
    GRAFANA_TOKEN=... python3 spec/grafana/push_prdikov.py --fetch [--file PATH]

GRAFANA_TOKEN is the service account token (grafanaServiceAccountToken in secret.py). The script reads it
from the environment only and never prints it.

The template variables of Prdikov are the owner's setpoints: grafana_setter.py sends every saved value to
the inverter, the Rehau zones and the wallbox within about 5 s. So the push:

1. fetches the live dashboard and saves it to ~/homeautomation/grafana-backups/ first;
2. compares the setpoint definitions (the templating block without "current" and "selected"). If they
   differ, it stops with exit 3 and sends nothing: a change of the setpoints themselves is for the owner;
3. puts the LIVE templating block into the file's dashboard, so a value that the owner set in the UI is
   kept, and sends the live version with "overwrite": false. On HTTP 412 (a save came in between) it stops
   with exit 4;
4. writes the live JSON back into the file (the sync-back rule).

--dry-run does 1 and 2 and prints the planned call. --fetch does 4 alone. Exit 2: the file is not Prdikov.

Spec: ../kb/work/032-pr-risk-review/spec.md, section 2.10; plan.md, correction 2;
../kb/architecture/grafana.md, "Maintenance workflow".
"""
import argparse
import copy
import json
import os
import sys
from datetime import datetime

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from review.risk import setpoint_definitions  # noqa: E402

UID = "q50mEhf7k"
DEFAULT_FILE = os.path.join(HERE, "prdikov.json")
BACKUP_DIR = os.path.expanduser("~/homeautomation/grafana-backups")


class Api:
    def __init__(self, base, token, session=requests):
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.session = session

    def get_dashboard(self, uid):
        r = self.session.request("GET", f"{self.base}/api/dashboards/uid/{uid}", headers=self.headers, timeout=10)
        if r.status_code >= 400:
            raise RuntimeError(f"GET /api/dashboards/uid/{uid} -> HTTP {r.status_code}")
        return r.json()

    def post_dashboard(self, body):
        r = self.session.request("POST", f"{self.base}/api/dashboards/db", headers=self.headers, json=body,
                                 timeout=10)
        return r.status_code, (r.json() if r.text else {})


def _dash(obj):
    return obj.get("dashboard", obj)


def backup(live):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, f"prdikov-{datetime.now().strftime('%Y%m%d-%H%M%S')}-push.json")
    with open(path, "w") as fh:
        json.dump(live, fh, indent=2, ensure_ascii=False)
    return path


def plan(file_obj, live, message):
    """(setpoint definitions equal, the POST body with the live templating, id and version)."""
    dash, live_dash = copy.deepcopy(_dash(file_obj)), _dash(live)
    equal = setpoint_definitions(dash) == setpoint_definitions(live_dash)
    dash["templating"] = copy.deepcopy(live_dash.get("templating", {}))
    dash["id"] = live_dash.get("id")
    dash["version"] = live_dash.get("version")
    return equal, {"dashboard": dash, "overwrite": False, "message": message}


def fetch(api, path):
    live = api.get_dashboard(UID)
    with open(path, "w") as fh:
        json.dump(live, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"synced back {os.path.basename(path)}: version {_dash(live).get('version')}")
    return live


def push(api, path, message, dry_run=False):
    with open(path) as fh:
        file_obj = json.load(fh)
    if _dash(file_obj).get("uid") != UID:
        print(f"{path} has the uid {_dash(file_obj).get('uid')!r}, not {UID!r}: nothing sent", file=sys.stderr)
        return 2
    live = api.get_dashboard(UID)
    print(f"saved the live dashboard (version {_dash(live).get('version')}): {backup(live)}")
    equal, body = plan(file_obj, live, message)
    if not equal:
        print("templating DIFFERS: the setpoint definitions of the file and of the live dashboard differ. "
              "Nothing sent.")
        return 3
    print("templating EQUAL: the push keeps the live setpoint values")
    print(f"planned: POST /api/dashboards/db (uid {UID}, version {body['dashboard']['version']}, overwrite false)")
    if dry_run:
        return 0
    status, result = api.post_dashboard(body)
    if status == 412:
        print("HTTP 412: the dashboard was saved in between. Fetch and build again.", file=sys.stderr)
        return 4
    if status >= 400:
        print(f"HTTP {status}: {str(result)[:300]}", file=sys.stderr)
        return 1
    print(f"pushed {UID}: {result.get('status')}, version {result.get('version')}")
    fetch(api, path)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Push Prdikov and keep the live setpoints (change 032).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="back up, compare, print the call, send nothing")
    mode.add_argument("--push", action="store_true", help="back up, compare, push with the live setpoints, sync back")
    mode.add_argument("--fetch", action="store_true", help="write the live dashboard to the file")
    parser.add_argument("--file", default=DEFAULT_FILE)
    parser.add_argument("--message", default="push_prdikov.py (change 032)")
    args = parser.parse_args(argv)
    token = os.environ.get("GRAFANA_TOKEN")
    if not token:
        print("GRAFANA_TOKEN is not set.", file=sys.stderr)
        return 2
    from config import grafanaConfig
    api = Api(grafanaConfig["ip_address"], token)
    try:
        if args.fetch:
            fetch(api, args.file)
            return 0
        return push(api, args.file, args.message, dry_run=args.dry_run)
    except (RuntimeError, requests.RequestException) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
