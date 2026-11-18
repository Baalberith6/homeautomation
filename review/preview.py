"""The before and after screenshots of a dashboard change, with a copy of the live data for a data change.

Usage, from the repo root, with the review virtualenv (Playwright):

    ~/homeautomation/review-venv/bin/python -m review.preview --pr N --base SHA --head SHA \
        --out ~/homeautomation/review-out/prN [--data-change] [--test-md ../kb/work/NNN-slug/test.md]
    ~/homeautomation/review-venv/bin/python -m review.preview --smoke UID PANEL --out DIR
    ~/homeautomation/review-venv/bin/python -m review.preview --cleanup

For each changed dashboard the script pushes two temporary boards into the Grafana folder "PR previews":
the JSON of the base and the JSON of the head. It takes each changed panel and the full page on both, with
one fixed time range, and deletes both boards. For a data change it first copies the live data that the
changed panels read into the bucket pr_preview, runs the "Preview data" block of the change's test.md, and
points the changed panels of the after board at pr_preview. It never writes to a live board or bucket.

Private data (change 042): the data of the family wiki and of the cars. The script classes each panel from
the data that its queries read (PUBLIC_DATA, PARTLY_PRIVATE). A panel that is private, or that the rule
does not know, is a placeholder on both boards, so its query does not run there. If such a panel changed,
a second pair of boards "…-private" holds the real panels; only the images of the held panels come from
it, and they go to OUT/private/, which review/report.py never uploads. A new measurement holds its panel
until it is in the data table.

The tokens come from secret.py of the main checkout (REVIEW_SECRET_DIR, default ~/homeautomation/code):
grafanaServiceAccountToken and influxPreviewToken. The script never prints a token.

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.5 and 2.6; plan.md, correction 1.
Private data: ../kb/work/042-pr-images-without-private-data/spec.md; plan.md, "How the patterns read a query".
"""
import argparse
import copy
import fcntl
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

FOLDER_UID, FOLDER_TITLE = "pr-previews", "PR previews"
LIVE_UIDS = {"q50mEhf7k", "ai"}
DASHBOARDS = ("spec/grafana/prdikov.json", "spec/grafana/ai.json")
BUCKET, ORG = "pr_preview", "Home"
SOURCE_BUCKETS = ("default", "ai")
MAX_COPY_DAYS = 31        # the longest range in the two dashboards: -30d, month_start, now/M (spec 2.6.2)
WAIT_S = 5                # after the load, so that the afterRender scripts finish (design value, spec 2.5.5)
TIMEOUT_S = 10            # for each API call (design value, spec section 4)
PAGE_TIMEOUT_S = 60       # for a page load in the browser
ROW_PX = 38               # one Grafana grid row: 30 px cell + 8 px margin
LOCK_WAIT_S = 15 * 60
LOCAL = ZoneInfo("Europe/Prague")
LOCK = os.path.expanduser("~/homeautomation/review-out/.preview.lock")
PANEL_SELECTORS = ('[data-panelid="{id}"]', '[data-viz-panel-key="panel-{id}"]')
PREVIEW_MISSING = "Preview data missing: the after image shows today's data only."
TO_BUCKET = re.compile(r'to\(\s*bucket\s*:\s*"([^"]*)"')
FROM_BUCKET = re.compile(r'from\(\s*bucket\s*:\s*"(default|ai)"\s*\)')
UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}

# Private data (change 042, spec 2.2). Every measurement that prdikov.json and ai.json read is here.
# A measurement that is not here is unknown, and its panel is held until somebody adds it.
PUBLIC_DATA = frozenset({
    "Estia", "FVE", "OTE", "RainForecast", "SolarForecast", "TempForecast", "WindForecast", "becka", "cez",
    "command", "estia", "krb", "netatmo", "on", "rehau", "rehau_hum", "rehau_output", "rehau_set", "temp_target",
    "weather", "weatherforecast",                             # the bucket default
    "ai_pushover", "ai_queue", "ai_sync", "ai_usage"})        # the bucket ai
PARTLY_PRIVATE = {                                            # measurement: its public fields
    "Car": frozenset({"car_connected", "charging_wallbox_power"}),   # energy data of the house (042, D1)
    "ai_jobs": frozenset({"run_s", "state"}),                        # the other columns name family files
}
IMPORTS = frozenset({"array", "math", "strings", "date", "timezone"})   # packages that read no data
PLACEHOLDER = {"private": "Private data: not shown (panel {id})", "unknown": "Not classed: not shown (panel {id})"}
WORST = {"public": 0, "unknown": 1, "private": 2}
ANY = None                # in a cube: every measurement, or every field
FROM = re.compile(r"(?<![\w.])from\s*\(")
BUCKET_ARG = re.compile(r'\s*bucket\s*:\s*"([^"\\]*)"\s*')
PIPE_CALL = re.compile(r"\s*\|>\s*([A-Za-z_][\w.]*)\s*\(")
FILTER_FN = re.compile(r"\s*fn\s*:\s*\(\s*r\s*\)\s*=>(.*)", re.S)
MEAS_EQ = re.compile(r'r(?:\._measurement|\["_measurement"\])\s*==\s*"([^"\\]*)"')
FIELD_EQ = re.compile(r'r(?:\._field|\["_field"\])\s*==\s*"([^"\\]*)"')
IMPORT = re.compile(r'^\s*import\s+(?:\w+\s+)?"([^"]*)"', re.M)


class GuardError(Exception):
    """A write outside "PR previews" or pr_preview."""


class NotSignedIn(Exception):
    pass


def _dash(obj):
    return obj.get("dashboard", obj) if obj else {"panels": []}


def _panels(dash):
    for panel in dash.get("panels", []):
        yield panel
        for inner in panel.get("panels", []):
            yield inner


def duplicate_ids(dash):
    """Panel IDs that more than one panel uses. A panel image of such an ID may show the wrong panel."""
    seen, dups = set(), set()
    for panel in _panels(_dash(dash)):
        pid = panel.get("id")
        (dups if pid in seen else seen).add(pid)
    return sorted(dups)


def duplicate_warning(ids, side):
    return (f"Panel id {', '.join(str(i) for i in ids)} is used by more than one panel on the {side} board: "
            "the panel image may show another panel. Give each panel its own id.")


def changed_panels(base, head):
    """The IDs of the panels that differ, are added or are removed."""
    old = {p["id"]: p for p in _panels(_dash(base))}
    new = {p["id"]: p for p in _panels(_dash(head))}
    return sorted(i for i in set(old) | set(new) if old.get(i) != new.get(i))


# ---- The class of a query and of a panel (change 042) ----------------------------------------------------
# The reader is small and fails closed: a form that it does not know lets "any" data through, and "any"
# is never public. A ValueError from a helper makes the query unknown.

def _string_end(text, i):
    """The index after the string that starts at text[i]."""
    j = i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
        elif text[j] == '"':
            return j + 1
        else:
            j += 1
    raise ValueError("a string does not end")


def _strip_comments(text):
    """The Flux text with no // comment. A // inside a string stays."""
    out, i = [], 0
    while i < len(text):
        if text[i] == '"':
            j = _string_end(text, i)
            out.append(text[i:j])
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = len(text) if j < 0 else j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _close(text, i):
    """The index of the bracket that closes the bracket at text[i]."""
    pairs, stack, j = {"(": ")", "[": "]", "{": "}"}, [], i
    while j < len(text):
        ch = text[j]
        if ch == '"':
            j = _string_end(text, j)
            continue
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in ")]}":
            if not stack or stack.pop() != ch:
                raise ValueError("the brackets do not match")
            if not stack:
                return j
        j += 1
    raise ValueError("a bracket does not close")


def _split(expr, word):
    """The parts of an expression between the keyword `word`, outside brackets and strings."""
    parts, depth, start, j = [], 0, 0, 0
    while j < len(expr):
        ch = expr[j]
        if ch == '"':
            j = _string_end(expr, j)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif (depth == 0 and expr.startswith(word, j) and not re.match(r"[\w.]", expr[j - 1:j] or " ")
              and not re.match(r"\w", expr[j + len(word):j + len(word) + 1] or " ")):
            parts.append(expr[start:j])
            j += len(word)
            start = j
            continue
        j += 1
    parts.append(expr[start:])
    return parts


def _both(left, right):
    """The cubes that both lists let through."""
    out = []
    for names1, fields1 in left:
        for names2, fields2 in right:
            names = names2 if names1 is ANY else names1 if names2 is ANY else names1 & names2
            fields = fields2 if fields1 is ANY else fields1 if fields2 is ANY else fields1 & fields2
            if (names is ANY or names) and (fields is ANY or fields):
                out.append((names, fields))
    return out


def _cubes(expr):
    """What a filter expression lets through: a list of (measurements, fields); ANY means no limit.

    Only `r._measurement == "x"` and `r._field == "x"` narrow. Every other term lets everything through.
    """
    alternatives = _split(expr, "or")
    if len(alternatives) > 1:
        return [cube for part in alternatives for cube in _cubes(part)]
    terms = _split(expr, "and")
    if len(terms) > 1:
        out = [(ANY, ANY)]
        for term in terms:
            out = _both(out, _cubes(term))
        return out
    term = expr.strip()
    if term.startswith("(") and _close(term, 0) == len(term) - 1:
        return _cubes(term[1:-1])
    found = MEAS_EQ.fullmatch(term)
    if found:
        return [(frozenset({found.group(1)}), ANY)]
    found = FIELD_EQ.fullmatch(term)
    if found:
        return [(ANY, frozenset({found.group(1)}))]
    return [(ANY, ANY)]


def _chains(text):
    """[(bucket or None, [the arguments of each filter of the chain])] for each from() of the text.

    Only the filters of the pipe chain of the from() itself count (plan 042, rule 5).
    """
    chains = []
    for start in FROM.finditer(text):
        end = _close(text, start.end() - 1)
        bucket = BUCKET_ARG.fullmatch(text[start.end():end])
        filters, pos = [], end + 1
        while True:
            call = PIPE_CALL.match(text, pos)
            if not call:
                break
            close = _close(text, call.end() - 1)
            if call.group(1) == "filter":
                filters.append(text[call.end():close])
            pos = close + 1
        chains.append((bucket.group(1) if bucket else None, filters))
    return chains


def _cube_class(names, fields):
    if names is ANY:
        return "unknown", "a from() pipeline has no filter on a measurement"
    worst = ("public", "")
    for name in sorted(names):
        if name in PUBLIC_DATA:
            continue
        if name not in PARTLY_PRIVATE:
            found = ("unknown", f"the measurement `{name}` is not in the data table")
        elif fields is ANY or not fields <= PARTLY_PRIVATE[name]:
            found = ("private", f"the query reads private fields of the measurement `{name}`")
        else:
            continue
        if WORST[found[0]] > WORST[worst[0]]:
            worst = found
    return worst


def query_class(query):
    """("public" | "private" | "unknown", the reason) for one Flux query (spec 042, section 2.3)."""
    found = []
    try:
        text = _strip_comments(query or "")
        other = sorted(set(IMPORT.findall(text)) - IMPORTS)
        if other:
            found.append(("unknown", f"the query imports the package `{other[0]}`"))
        chains = _chains(text)
        if not chains:
            found.append(("unknown", "the query has no from()"))
        for bucket, filters in chains:
            if bucket not in SOURCE_BUCKETS:
                found.append(("unknown", "a from() reads a bucket that is not `default` or `ai`"))
                continue
            cubes = [(ANY, ANY)]
            for args in filters:
                fn = FILTER_FN.fullmatch(args)
                cubes = _both(cubes, _cubes(fn.group(1)) if fn else [(ANY, ANY)])
            found += [_cube_class(names, fields) for names, fields in cubes]
    except ValueError as exc:
        return "unknown", f"the tool cannot read the query: {exc}"
    return max(found, key=lambda item: WORST[item[0]]) if found else ("public", "")


def panel_class(panel):
    """The class of a panel and the reason: the worst class of its queries (spec 042, section 2.4)."""
    if "libraryPanel" in panel:
        return "unknown", "a library panel keeps its queries in Grafana"
    worst = ("public", "")
    for target in panel.get("targets") or []:
        query = target.get("query") if isinstance(target, dict) else None
        if isinstance(query, str) and query.strip():
            found = query_class(query)
        else:
            found = ("unknown", "a target has no Flux query")
        if WORST[found[0]] > WORST[worst[0]]:
            worst = found
    return worst


def held_panels(dash):
    """{panel id: (class, reason)} for each panel that is not public."""
    held = {}
    for panel in _panels(_dash(dash)):
        found = panel_class(panel)
        if found[0] != "public":
            held[panel.get("id")] = found
    return held


def variables_public(dash):
    """False if a variable of the type "query" reads data that is not public (spec 042, section 2.5)."""
    for variable in (_dash(dash).get("templating") or {}).get("list") or []:
        if variable.get("type") != "query":
            continue
        query = variable.get("query")
        if isinstance(query, dict):
            query = query.get("query")
        if not isinstance(query, str) or query_class(query)[0] != "public":
            return False
    return True


def placeholder(panel, cls):
    """The text panel that takes the place of a held panel: the same id and position, no query, no script."""
    tile = {"id": panel.get("id"), "type": "text", "title": "",
            "options": {"mode": "markdown", "content": PLACEHOLDER[cls].format(id=panel.get("id"))}}
    if panel.get("gridPos") is not None:
        tile["gridPos"] = copy.deepcopy(panel["gridPos"])
    return tile


def clear_images(out_dir):
    """Delete the PNG files of an earlier run, so that none of them can go into an upload."""
    for folder in (out_dir, os.path.join(out_dir, "private")):
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                if name.endswith(".png"):
                    os.remove(os.path.join(folder, name))


def _start_of(unit, when):
    local = when.astimezone(LOCAL)
    if unit == "d":
        local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    elif unit == "w":
        local = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif unit == "M":
        local = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif unit == "y":
        local = local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


def _relative(expr, now):
    m = re.fullmatch(r"now(?:-(\d+)([smhdw]))?(?:/([dwMy]))?", expr.strip())
    if not m:
        raise ValueError(f"time expression not supported: {expr!r}")
    when = now
    if m.group(1):
        when = now - timedelta(**{UNITS[m.group(2)]: int(m.group(1))})
    if m.group(3):
        when = _start_of(m.group(3), when)
    return when


def _ms(when):
    return int(when.timestamp() * 1000)


def time_range(dash, now):
    """The default range of the dashboard as fixed milliseconds, the same for both boards (spec 2.5.4)."""
    span = _dash(dash).get("time") or {"from": "now-3h", "to": "now"}
    return _ms(_relative(span.get("from", "now-3h"), now)), _ms(_relative(span.get("to", "now"), now))


def measurements(query):
    return set(re.findall(r'_measurement\s*==\s*"([^"]+)"', query))


def _fixed_starts(query, now):
    starts = []
    for m in re.finditer(r"range\(\s*start\s*:\s*(today\(\)|[^,)\s]+)", query):
        expr = m.group(1).strip()
        rel = re.fullmatch(r"-(\d+)([smhdw])", expr)
        if rel:
            starts.append(now - timedelta(**{UNITS[rel.group(2)]: int(rel.group(1))}))
        elif expr == "today()":
            starts.append(_start_of("d", now))
        elif expr == "month_start":
            starts.append(_start_of("M", now))
    return starts


def copy_window(queries, shot_range, now):
    """The span to copy: the shot range or a longer fixed range of the queries, at most 31 days (spec 2.6.2)."""
    shot_from = datetime.fromtimestamp(shot_range[0] / 1000, tz=timezone.utc)
    shot_to = datetime.fromtimestamp(shot_range[1] / 1000, tz=timezone.utc)
    stop = max(shot_to, now)
    start = min([shot_from] + [s for q in queries for s in _fixed_starts(q, now)])
    return max(start, stop - timedelta(days=MAX_COPY_DAYS)), stop


def _iso(when):
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def copy_flux(src_bucket, names, start, stop):
    cond = " or ".join(f'r._measurement == "{n}"' for n in sorted(names)) or "true"
    return (f'from(bucket: "{src_bucket}")\n'
            f"  |> range(start: {_iso(start)}, stop: {_iso(stop)})\n"
            f"  |> filter(fn: (r) => {cond})\n"
            f'  |> to(bucket: "{BUCKET}")\n')  # no org: the preview token cannot read the org by name


def preview_block(test_md):
    """The flux block under "## Preview data" of a test.md, or None."""
    m = re.search(r"^## Preview data\s*$(.*?)(?=^## |\Z)", test_md, re.M | re.S)
    if not m:
        return None
    block = re.search(r"```flux\n(.*?)```", m.group(1), re.S)
    return block.group(1) if block else None


def rewrite_buckets(query):
    return FROM_BUCKET.sub(f'from(bucket: "{BUCKET}")', query)


def board(dash, uid, title, rewrite_ids=()):
    """A copy of a dashboard as a temporary board; the panels in rewrite_ids read pr_preview."""
    out = copy.deepcopy(_dash(dash))
    out.update({"uid": uid, "title": title, "id": None})
    out.pop("version", None)
    for panel in _panels(out):
        if panel.get("id") in rewrite_ids:
            for target in panel.get("targets", []):
                if "query" in target:
                    target["query"] = rewrite_buckets(target["query"])
    return out


def _find(dash, pid):
    return next((p for p in _panels(_dash(dash)) if p.get("id") == pid), None)


def plan_shots(key, ids, before_uid, after_uid, base_dash, head_dash, rng, base_url):
    """One shot of the whole board per side. Each changed panel is cut out of it by its element."""
    base_url = base_url.rstrip("/")
    frm, to = rng
    shots = []
    for side, uid, dash in (("before", before_uid, base_dash), ("after", after_uid, head_dash)):
        present = [i for i in ids if _find(dash, i)]
        rows = max([(p.get("gridPos") or {}).get("y", 0) + (p.get("gridPos") or {}).get("h", 0)
                    for p in _panels(_dash(dash))] or [0])
        # Grafana draws only the panels in the viewport, so the viewport holds the whole grid (no full_page).
        shots.append({"name": f"{key}-page-{side}.png", "width": 1920, "height": max(1080, rows * ROW_PX + 120),
                      "check_ids": present, "panels": {pid: f"{key}-{pid}-{side}.png" for pid in present},
                      "url": f"{base_url}/d/{uid}/x?orgId=1&from={frm}&to={to}&kiosk"})
    return shots


def signed_in(url, api_user_status, login_form_count, panel_counts):
    """Correction 1: the Prdikov panels have no title, so the check uses the page, /api/user and the panels."""
    if "/login" in url:
        return False, "the page is the Grafana sign-in page"
    if api_user_status != 200:
        return False, f"GET /api/user gave HTTP {api_user_status}"
    if login_form_count:
        return False, "the page shows a sign-in form"
    missing = [str(pid) for pid, count in panel_counts.items() if not count]
    if missing:
        return False, "panel " + ", ".join(missing) + " is not on the page"
    return True, ""


class GuardedGrafana:
    """Grafana API calls. A write or a delete goes only to a board "pr…" in the folder "PR previews"."""

    def __init__(self, base, token, session=requests):
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.session = session

    def _call(self, method, path, allow=(), **kwargs):
        r = self.session.request(method, self.base + path, headers=self.headers, timeout=TIMEOUT_S, **kwargs)
        if r.status_code in allow:
            return None
        if r.status_code >= 400:
            raise RuntimeError(f"Grafana {method} {path} -> HTTP {r.status_code}")
        return r.json() if r.text else {}

    @staticmethod
    def _check(uid):
        if not uid or uid in LIVE_UIDS or not uid.startswith("pr"):
            raise GuardError(f"refused: the board {uid!r} is not a preview board")

    def get(self, uid):
        return self._call("GET", f"/api/dashboards/uid/{uid}")

    def user_status(self):
        r = self.session.request("GET", self.base + "/api/user", headers=self.headers, timeout=TIMEOUT_S)
        return r.status_code

    def ensure_folder(self):
        if self._call("GET", f"/api/folders/{FOLDER_UID}", allow=(404,)) is None:
            self._call("POST", "/api/folders", json={"uid": FOLDER_UID, "title": FOLDER_TITLE})

    def list_folder(self):
        found = self._call("GET", f"/api/search?folderUIDs={FOLDER_UID}&type=dash-db") or []
        return [d["uid"] for d in found]

    def put(self, dashboard):
        self._check(dashboard.get("uid"))
        return self._call("POST", "/api/dashboards/db",
                          json={"dashboard": dashboard, "folderUid": FOLDER_UID, "overwrite": True,
                                "message": "pr-reviewer preview (change 032)"})

    def delete(self, uid):
        self._check(uid)
        meta = (self.get(uid) or {}).get("meta", {})
        if meta.get("folderUid") != FOLDER_UID:
            raise GuardError(f"refused: the board {uid!r} is not in the folder {FOLDER_TITLE!r}")
        return self._call("DELETE", f"/api/dashboards/uid/{uid}")


class Influx:
    """InfluxDB calls. A Flux that writes goes only to pr_preview; the delete empties only pr_preview."""

    def __init__(self, url, token, session=requests):
        self.url = url.rstrip("/")
        self.token = token
        self.session = session

    def query(self, flux):
        targets = TO_BUCKET.findall(flux)
        if any(t != BUCKET for t in targets) or re.search(r"\bto\(\s*\)", flux):
            raise GuardError(f"refused: a Flux write to {targets}")
        headers = {"Authorization": f"Token {self.token}", "Content-Type": "application/vnd.flux",
                   "Accept": "application/csv"}
        r = self.session.request("POST", f"{self.url}/api/v2/query?org={ORG}", headers=headers, data=flux,
                                 timeout=TIMEOUT_S * 6)
        if r.status_code >= 400:
            raise RuntimeError(f"InfluxDB query -> HTTP {r.status_code}: {r.text[:200]}")
        return r.text

    def empty_bucket(self, now):
        headers = {"Authorization": f"Token {self.token}", "Content-Type": "application/json"}
        body = {"start": "1970-01-01T00:00:00Z", "stop": _iso(now + timedelta(days=1))}
        r = self.session.request("POST", f"{self.url}/api/v2/delete?org={ORG}&bucket={BUCKET}", headers=headers,
                                 json=body, timeout=TIMEOUT_S * 6)
        if r.status_code >= 400:
            raise RuntimeError(f"InfluxDB delete -> HTTP {r.status_code}: {r.text[:200]}")

    def count(self, measurement=None, field=None):
        cond = []
        if measurement:
            cond.append(f'r._measurement == "{measurement}"')
        if field:
            cond.append(f'r._field == "{field}"')
        flux = (f'from(bucket: "{BUCKET}") |> range(start: 0) |> filter(fn: (r) => {" and ".join(cond) or "true"})'
                ' |> group() |> count()')
        rows = [line for line in self.query(flux).splitlines() if line.strip()]
        return int(rows[-1].split(",")[-1]) if len(rows) > 1 else 0


def cleanup(grafana, influx, now=None):
    """Delete every board in "PR previews" and empty pr_preview. Returns the deleted UIDs."""
    left = grafana.list_folder()
    for uid in left:
        grafana.delete(uid)
    if influx is not None:
        influx.empty_bucket(now or datetime.now(timezone.utc))
    return left


def shoot(token, shots, out_dir, api_user_url):
    """Take the screenshots with headless Chromium. Raises NotSignedIn if a page check fails."""
    from playwright.sync_api import sync_playwright  # only on the Mac: CI has no Playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            context = browser.new_context(extra_http_headers={"Authorization": f"Bearer {token}"})
            page = context.new_page()
            for shot in shots:
                page.set_viewport_size({"width": shot["width"], "height": shot["height"]})
                page.goto(shot["url"], wait_until="networkidle", timeout=PAGE_TIMEOUT_S * 1000)
                page.wait_for_timeout(WAIT_S * 1000)
                if "check_ids" in shot:
                    counts = {pid: sum(page.locator(sel.format(id=pid)).count() for sel in PANEL_SELECTORS)
                              for pid in shot["check_ids"]}
                    ok, reason = signed_in(page.url, page.request.get(api_user_url).status,
                                           page.locator('input[name="user"]').count(), counts)
                    if not ok:
                        raise NotSignedIn(reason)
                page.screenshot(path=os.path.join(out_dir, shot["name"]))
                for pid, name in shot.get("panels", {}).items():
                    for sel in PANEL_SELECTORS:
                        element = page.locator(sel.format(id=pid))
                        if element.count():
                            element.first.screenshot(path=os.path.join(out_dir, name))
                            break
        finally:
            browser.close()


class _Lock:
    def __enter__(self):
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        self.fh = open(LOCK, "w")
        deadline = time.monotonic() + LOCK_WAIT_S
        while True:
            try:
                fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() > deadline:
                    raise RuntimeError("another preview runs")
                time.sleep(5)

    def __exit__(self, *exc):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


def _show(repo, sha, path):
    r = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=repo, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def _source_buckets(panels):
    found = {}
    for panel in panels:
        for target in panel.get("targets", []):
            query = target.get("query", "")
            m = re.search(r'from\(\s*bucket\s*:\s*"([^"]+)"', query)
            if m and m.group(1) in SOURCE_BUCKETS:
                found.setdefault(m.group(1), []).append(query)
    return found


def copy_plan(panels, shot_range, now):
    """[(source bucket, measurements, start, stop)] to copy for the changed panels (spec 2.6.2, 2.6.3).

    The named measurements over their window; a query that names none: the whole bucket over the shot range.
    """
    plan = []
    shot_to = datetime.fromtimestamp(shot_range[1] / 1000, tz=timezone.utc)
    shot_from = datetime.fromtimestamp(shot_range[0] / 1000, tz=timezone.utc)
    for src, queries in sorted(_source_buckets(panels).items()):
        named = [q for q in queries if measurements(q)]
        if named:
            start, stop = copy_window(named, shot_range, now)
            plan.append((src, set().union(*(measurements(q) for q in named)), start, stop))
        if len(named) < len(queries):
            plan.append((src, set(), shot_from, max(shot_to, now)))
    return plan


def run(pr, base, head, out_dir, data_change, test_md, grafana, influx, token, repo=".", now=None, shooter=shoot):
    """Spec 2.5 and 2.6 for one PR. Writes the PNG files and preview.json into out_dir."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    os.makedirs(out_dir, exist_ok=True)
    result = {"panels": [], "pages": [], "warnings": [], "leftovers": [], "failed": None}
    try:
        with _Lock():
            try:
                result["leftovers"] = cleanup(grafana, influx if data_change else None, now)
                for uid in result["leftovers"]:
                    result["warnings"].append(f"Deleted a board left by an earlier run: {uid}")
                grafana.ensure_folder()
                for path in DASHBOARDS:
                    old, new = _show(repo, base, path), _show(repo, head, path)
                    if old == new:
                        continue
                    _one(pr, path, _dash(old), _dash(new), out_dir, data_change, test_md, grafana, influx,
                         token, now, shooter, result)
            finally:
                if data_change:
                    influx.empty_bucket(now)
    except Exception as exc:  # spec section 4: a failure makes the PR high risk, the report says why
        result["failed"] = f"Screenshots failed: {type(exc).__name__}: {exc}"
    with open(os.path.join(out_dir, "preview.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    return result


def _one(pr, path, base_dash, head_dash, out_dir, data_change, test_md, grafana, influx, token, now, shooter,
         result):
    key = "prdikov" if "prdikov" in path else "ai"
    ids = changed_panels(base_dash, head_dash)
    for side, dash in (("before", base_dash), ("after", head_dash)):
        dups = duplicate_ids(dash)
        if dups:
            result["warnings"].append(duplicate_warning(dups, side))
    rng = time_range(head_dash, now)
    rewrite = set()
    if data_change:
        changed = [p for p in _panels(head_dash) if p.get("id") in ids]
        for src, names, start, stop in copy_plan(changed, rng, now):
            influx.query(copy_flux(src, names, start, stop))
        block = None
        if test_md and os.path.exists(test_md):
            with open(test_md) as fh:
                block = preview_block(fh.read())
        if block:
            influx.query(block)
        else:
            result["warnings"].append(PREVIEW_MISSING)
        rewrite = set(ids)
    before_uid, after_uid = f"pr{pr}-{key}-before", f"pr{pr}-{key}-after"
    grafana.put(board(base_dash, before_uid, f"PR {pr} {key} before"))
    grafana.put(board(head_dash, after_uid, f"PR {pr} {key} after", rewrite_ids=rewrite))
    try:
        shots = plan_shots(key, ids, before_uid, after_uid, base_dash, head_dash, rng, grafana.base)
        shooter(token, shots, out_dir, grafana.base + "/api/user")
    finally:
        grafana.delete(before_uid)
        grafana.delete(after_uid)
    names = {s["name"] for s in shots} | {n for s in shots for n in s.get("panels", {}).values()}
    for pid in ids:
        result["panels"].append({"id": pid if key == "prdikov" else f"AI {pid}",
                                 "before": f"{key}-{pid}-before.png" if f"{key}-{pid}-before.png" in names else None,
                                 "after": f"{key}-{pid}-after.png" if f"{key}-{pid}-after.png" in names else None})
    result["pages"].append({"label": key, "before": f"{key}-page-before.png", "after": f"{key}-page-after.png"})


def smoke(uid, panel_id, out_dir, grafana, token, now=None, shooter=shoot):
    """Copy a live board twice into "PR previews", take one panel and the page on each, delete both."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    os.makedirs(out_dir, exist_ok=True)
    live = grafana.get(uid)["dashboard"]
    grafana.ensure_folder()
    grafana.put(board(live, "pr0-before", "PR 0 before"))
    grafana.put(board(live, "pr0-after", "PR 0 after"))
    try:
        shots = plan_shots("smoke", [panel_id], "pr0-before", "pr0-after", live, live, time_range(live, now),
                           grafana.base)
        shooter(token, shots, out_dir, grafana.base + "/api/user")
    finally:
        grafana.delete("pr0-before")
        grafana.delete("pr0-after")
    return [n for s in shots for n in [s["name"]] + list(s.get("panels", {}).values())]


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _clients():
    folder = os.path.expanduser(os.environ.get("REVIEW_SECRET_DIR", "~/homeautomation/code"))
    secret = _module("review_secret", os.path.join(folder, "secret.py"))
    config = _module("review_config", os.path.join(folder, "config.py"))
    gtoken = getattr(secret, "grafanaServiceAccountToken", None)
    itoken = getattr(secret, "influxPreviewToken", None)
    if not gtoken or not itoken:
        raise SystemExit("grafanaServiceAccountToken or influxPreviewToken is missing in " + folder + "/secret.py")
    grafana = GuardedGrafana(config.grafanaConfig["ip_address"], gtoken)
    influx = Influx(config.influxConfig["url"], itoken)
    return grafana, influx, gtoken


def main(argv=None):
    parser = argparse.ArgumentParser(description="Before and after screenshots of a dashboard change (032).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pr", type=int)
    mode.add_argument("--smoke", nargs=2, metavar=("UID", "PANEL"))
    mode.add_argument("--cleanup", action="store_true")
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--out", default="~/homeautomation/review-out/pr0")
    parser.add_argument("--data-change", action="store_true")
    parser.add_argument("--test-md")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    grafana, influx, token = _clients()
    out = os.path.expanduser(args.out)
    if args.cleanup:
        print(json.dumps({"deleted": cleanup(grafana, influx)}))
        return 0
    if args.smoke:
        print(json.dumps({"images": smoke(args.smoke[0], int(args.smoke[1]), out, grafana, token)}))
        return 0
    if not (args.base and args.head):
        parser.error("--pr needs --base and --head")
    result = run(args.pr, args.base, args.head, out, args.data_change,
                 os.path.expanduser(args.test_md) if args.test_md else None, grafana, influx, token, repo=args.repo)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
