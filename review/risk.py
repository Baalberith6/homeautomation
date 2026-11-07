"""The risk level of a pull request: low merges by itself after CI, high waits for the owner.

Usage, from the repo root:

    python3 -m review.risk --base SHA --head SHA [--repo DIR]

Prints one JSON object: level, reasons, changed files, new / edited / deleted tests, data_change,
dashboards. Any error prints level "high" with the reason "risk script failed: <type>" and exits 0,
so a broken script never lets a PR merge by itself.

Spec: ../kb/work/032-pr-risk-review/spec.md, sections 2.2, 2.3 and 2.9; plan.md, "Spec corrections"
(the setpoint definitions leave out the values "current" and "selected").
"""
import argparse
import ast
import fnmatch
import json
import re
import subprocess
import sys

RULES = [  # (rule, glob) - spec section 2.2
    ("Telegraf", "telegraf.conf"), ("Telegraf", "telegraf-lxc-scripts.conf"),
    ("Config", "config.py"), ("Config", "systemd/*"), ("Config", "deploy.sh"), ("Config", "requirements.txt"),
    ("Shared module", "common.py"),
    ("Device commands", "wallbox.py"), ("Device commands", "inverter_setter.py"),
    ("Device commands", "estia_optimizer.py"), ("Device commands", "lights.py"),
    ("Harness", ".github/*"), ("Harness", "review/*"), ("Harness", ".claude/agents/pr-reviewer.md"),
    ("Setpoints", "spec/grafana/push_*.py"),  # they write the live dashboards and their setpoints
]
DASHBOARDS = ("spec/grafana/prdikov.json", "spec/grafana/ai.json")
TELEGRAF = ("telegraf.conf", "telegraf-lxc-scripts.conf")
INFLUX_WRITERS = ("cursor.py", "energyestimator.py", "estia_energy.py", "oteforecast.py",
                  "solarforecast.py", "wu.py", "yr.py")
OWNERS = ("matejpristak", "Baalberith6")
REPO = "Baalberith6/homeautomation"
SETPOINT_VALUE_KEYS = ("current", "selected")
DYNAMIC_PUBLISH = re.compile(r"\.publish\(\s*(f[\"']|[A-Za-z_]|[\"'][^\"']*[\"']\s*\+)")
KINDS = (("topics", "topic"), ("influx", "InfluxDB name"), ("payload_keys", "payload key"))


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def _show(repo, sha, path):
    """The text of path at sha, or None if the file does not exist there."""
    r = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=repo, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def changed_files(repo, base, head):
    paths = set()
    for line in _git(repo, "diff", "--name-status", "-M", base, head).splitlines():
        parts = line.split("\t")
        paths.update(parts[1:])
    return paths


def path_reasons(paths):
    reasons = []
    for path in sorted(paths):
        for rule, pattern in RULES:
            if fnmatch.fnmatch(path, pattern):
                reasons.append(f"{rule}: {path}")
                break
    return reasons


def _strip_values(obj):
    if isinstance(obj, dict):
        return {k: _strip_values(v) for k, v in obj.items() if k not in SETPOINT_VALUE_KEYS}
    if isinstance(obj, list):
        return [_strip_values(v) for v in obj]
    return obj


def setpoint_definitions(dashboard_json):
    """The templating block without the setpoint values (keys "current" and "selected", at any depth).

    Takes the JSON text or the parsed object, wrapped in {"dashboard": ...} or not.
    """
    data = json.loads(dashboard_json) if isinstance(dashboard_json, str) else dashboard_json
    if data is None:
        return None
    dashboard = data.get("dashboard", data)
    return _strip_values(dashboard.get("templating", {}))


def _variables(text):
    """The list of setpoint definitions; a missing file or a board with no variables gives []."""
    if text is None:
        return []
    return (setpoint_definitions(text) or {}).get("list", [])


def setpoint_reasons(repo, base, head, paths):
    reasons = []
    for path in DASHBOARDS:
        if path not in paths:
            continue
        old, new = _variables(_show(repo, base, path)), _variables(_show(repo, head, path))
        if old != new:
            reasons.append(f"Setpoints: {path}")
    return reasons


def _name(func):
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _pattern(node):
    """A topic as text: the literal parts kept, the run-time parts as {}. None if no part is literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = [v.value if isinstance(v, ast.Constant) else "{}" for v in node.values]
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        parts = [_pattern(node.left) or "{}", _pattern(node.right) or "{}"]
    else:
        return None
    text = "".join(parts)
    return text if text.replace("{}", "") else None


def inventory(sources):
    """{path: python text} -> {"topics" | "influx" | "payload_keys": {name: set of paths}}."""
    found = {"topics": {}, "influx": {}, "payload_keys": {}}

    def add(kind, name, path):
        found[kind].setdefault(name, set()).add(path)

    for path, text in sources.items():
        tree = ast.parse(text, filename=path)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        publishes = any(_name(c.func) == "publish" for c in calls)
        for call in calls:
            name = _name(call.func)
            if name in ("publish", "subscribe"):
                if call.args and _pattern(call.args[0]) is not None:
                    add("topics", _pattern(call.args[0]), path)
                for arg in call.args:
                    if isinstance(arg, (ast.List, ast.Tuple)):
                        for elt in arg.elts:
                            if _str(elt) is not None:
                                add("topics", _str(elt), path)
            elif name == "Point" and call.args and _str(call.args[0]) is not None:
                add("influx", "measurement " + _str(call.args[0]), path)
            elif name == "field" and call.args and _str(call.args[0]) is not None:
                add("influx", "field " + _str(call.args[0]), path)
            elif name == "dumps" and publishes:
                for arg in call.args:
                    for node in ast.walk(arg):
                        if isinstance(node, ast.Dict):
                            for key in node.keys:
                                if _str(key) is not None:
                                    add("payload_keys", _str(key), path)
    return found


def _top_level_py(repo, sha):
    names = _git(repo, "ls-tree", "--name-only", sha).splitlines()
    return {n: _show(repo, sha, n) for n in names if n.endswith(".py")}


def dynamic_topic_lines(diff_text):
    """Changed lines of top-level .py files that publish to a topic built at run time."""
    hits, path = [], None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[1]
            continue
        if line.startswith(("+++", "---")) or not line.startswith(("+", "-")):
            continue
        if path and "/" not in path and path.endswith(".py") and DYNAMIC_PUBLISH.search(line):
            hits.append((path, line[1:].strip()))
    return hits


def messaging_reasons(repo, base, head):
    old, new = inventory(_top_level_py(repo, base)), inventory(_top_level_py(repo, head))
    reasons = []
    for kind, label in KINDS:
        for name in sorted(set(new[kind]) - set(old[kind])):
            reasons.append(f"Messaging: {label} {name} added ({', '.join(sorted(new[kind][name]))})")
        for name in sorted(set(old[kind]) - set(new[kind])):
            reasons.append(f"Messaging: {label} {name} removed ({', '.join(sorted(old[kind][name]))})")
    for path, line in dynamic_topic_lines(_git(repo, "diff", "-U0", base, head)):
        reasons.append(f"Messaging: a topic built at run time changed ({path}: {line})")
    return reasons


def _tests(text, path):
    """{test id: source} for the test functions of one file."""
    if text is None:
        return {}
    tree = ast.parse(text, filename=path)
    found = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            found[f"{path}::{node.name}"] = ast.get_source_segment(text, node)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"):
                    found[f"{path}::{node.name}::{item.name}"] = ast.get_source_segment(text, item)
    return found


def test_changes(repo, base, head, paths):
    new, edited, deleted = [], [], []
    for path in sorted(p for p in paths if p.startswith("tests/") and p.endswith(".py")):
        old, cur = _tests(_show(repo, base, path), path), _tests(_show(repo, head, path), path)
        new += [t for t in cur if t not in old]
        deleted += [t for t in old if t not in cur]
        edited += [t for t in cur if t in old and cur[t] != old[t]]
    return sorted(new), sorted(edited), sorted(deleted)


def classify(base, head, repo_dir="."):
    paths = changed_files(repo_dir, base, head)
    messaging = messaging_reasons(repo_dir, base, head)
    reasons = path_reasons(paths) + setpoint_reasons(repo_dir, base, head, paths) + messaging
    new, edited, deleted = test_changes(repo_dir, base, head, paths)
    data_change = bool(messaging) or any(p in TELEGRAF or p in INFLUX_WRITERS for p in paths)
    return {
        "level": "high" if reasons else "low",
        "reasons": reasons,
        "base": base,
        "head": head,
        "changed": sorted(paths),
        "new_tests": new,
        "edited_tests": edited,
        "deleted_tests": deleted,
        "data_change": data_change,
        "dashboards": [p for p in DASHBOARDS if p in paths],
    }


def decide(level, open_findings, tests_failed, author, cross_repo):
    """What the session does with the PR (spec section 2.9)."""
    if cross_repo or author not in OWNERS:
        return "refuse"
    if open_findings > 0 or tests_failed:
        return "fix-findings"
    if level != "low":
        return "wait-owner"
    return "auto-merge"


def main(argv=None):
    parser = argparse.ArgumentParser(description="The risk level of a pull request (change 032).")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    try:
        result = classify(args.base, args.head, repo_dir=args.repo)
    except Exception as exc:  # spec 2.2.4: a failure is high risk
        result = {"level": "high", "reasons": [f"risk script failed: {type(exc).__name__}"],
                  "base": args.base, "head": args.head}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
