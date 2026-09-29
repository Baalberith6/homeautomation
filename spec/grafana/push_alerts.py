"""Push the change 020 alert rules and the notification policy to Grafana.

Usage, from the repo root:

    GRAFANA_TOKEN=... python3 spec/grafana/push_alerts.py --dry-run
    GRAFANA_TOKEN=... python3 spec/grafana/push_alerts.py --push
    GRAFANA_TOKEN=... python3 spec/grafana/push_alerts.py --delete

GRAFANA_TOKEN is the service account token (grafanaServiceAccountToken in secret.py). The script
reads it from the environment only and never prints it. --dry-run sends nothing.

--push needs the contact point named in 020-rules.json; the owner makes it in the Grafana UI, so
the Pushover keys never pass through this script. --push also sends the notification template
"home"; the contact point uses it through its Title and Message fields, which the owner sets.
Every call sends X-Disable-Provenance, so the rules and the policy stay editable in the UI. The
push does not touch any dashboard.

Spec: ../kb/work/020-failures-visible-automatically/spec.md
"""
import argparse
import json
import os
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from config import grafanaConfig  # noqa: E402

RULES = os.path.join(HERE, "alerts", "020-rules.json")
BACKUP = os.path.expanduser("~/homeautomation/grafana-backups/policies-before-020.json")


def load():
    with open(RULES) as fh:
        return json.load(fh)


def load_template(config):
    """The notification template of the Pushover message (change 020 revision 3)."""
    with open(os.path.join(HERE, "alerts", config["template"]["file"])) as fh:
        return {"template": fh.read()}


def planned_calls(config):
    """The calls of --push, in order: (method, path, body)."""
    folder = config["folder"]
    group = config["rule_group"]
    return [
        ("GET", "/api/v1/provisioning/contact-points", None),
        ("PUT", f"/api/v1/provisioning/templates/{config['template']['name']}", load_template(config)),
        ("POST", "/api/folders", folder),
        ("PUT", f"/api/v1/provisioning/folder/{folder['uid']}/rule-groups/{group['title']}", group),
        ("PUT", "/api/v1/provisioning/policies", config["policy"]),
    ]


class Grafana:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                        "X-Disable-Provenance": "true"}

    def _check(self, method, path, r, allow):
        if r.status_code in allow:
            return None
        if r.status_code >= 400:
            raise SystemExit(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json() if r.text else {}

    def get(self, path, allow=()):
        return self._check("GET", path, requests.get(self.base + path, headers=self.headers, timeout=10), allow)

    def post(self, path, body):
        return self._check("POST", path, requests.post(self.base + path, headers=self.headers, json=body,
                                                       timeout=10), ())

    def put(self, path, body):
        return self._check("PUT", path, requests.put(self.base + path, headers=self.headers, json=body,
                                                     timeout=10), ())

    def delete(self, path, allow=()):
        return self._check("DELETE", path, requests.delete(self.base + path, headers=self.headers, timeout=10),
                           allow)


def push(api, config):
    names = [point.get("name") for point in api.get("/api/v1/provisioning/contact-points")]
    if config["contact_point"] not in names:
        print(f"The contact point {config['contact_point']!r} does not exist. Make it in the Grafana UI first.",
              file=sys.stderr)
        return 3
    name = config["template"]["name"]
    api.put(f"/api/v1/provisioning/templates/{name}", load_template(config))
    print(f"pushed the notification template {name!r}")
    folder = config["folder"]
    if api.get(f"/api/folders/{folder['uid']}", allow=(404,)) is None:
        api.post("/api/folders", folder)
        print(f"created folder {folder['title']!r}")
    if not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        with open(BACKUP, "w") as fh:
            json.dump(api.get("/api/v1/provisioning/policies"), fh, indent=2)
        print(f"saved the policy before the push: {BACKUP}")
    group = config["rule_group"]
    api.put(f"/api/v1/provisioning/folder/{folder['uid']}/rule-groups/{group['title']}", group)
    print(f"pushed rule group {group['title']!r}: {len(group['rules'])} rules")
    api.put("/api/v1/provisioning/policies", config["policy"])
    print(f"pushed the policy: receiver {config['policy']['receiver']!r}")
    return 0


def delete(api, config):
    folder = config["folder"]
    group = config["rule_group"]
    api.delete(f"/api/v1/provisioning/folder/{folder['uid']}/rule-groups/{group['title']}", allow=(404,))
    api.delete(f"/api/folders/{folder['uid']}", allow=(404,))
    # The contact point may still name the template: set its Title and Message back first.
    api.delete(f"/api/v1/provisioning/templates/{config['template']['name']}", allow=(404,))
    if os.path.exists(BACKUP):
        with open(BACKUP) as fh:
            api.put("/api/v1/provisioning/policies", json.load(fh))
        print(f"restored the policy from {BACKUP}")
    else:
        api.delete("/api/v1/provisioning/policies")
        print("reset the policy to the Grafana default")
    print(f"deleted rule group {group['title']!r}, folder {folder['title']!r} and template {config['template']['name']!r}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Push the change 020 alert rules to Grafana.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="print the calls, send nothing")
    mode.add_argument("--push", action="store_true", help="create or update the folder, the rules and the policy")
    mode.add_argument("--delete", action="store_true", help="remove the rules and the folder, restore the policy")
    args = parser.parse_args(argv)
    config = load()
    if args.dry_run:
        for method, path, _ in planned_calls(config):
            print(f"{method} {path}")
        return 0
    token = os.environ.get("GRAFANA_TOKEN")
    if not token:
        print("GRAFANA_TOKEN is not set.", file=sys.stderr)
        return 2
    api = Grafana(grafanaConfig["ip_address"], token)
    return push(api, config) if args.push else delete(api, config)


if __name__ == "__main__":
    sys.exit(main())
