"""The light zones follow a daily schedule through a local connection (change 023).

Spec: ../kb/work/023-light-zones-local-schedule/spec.md.
The MiBoxer WL-Box2 drives all 2.4 GHz zones. A command acts on the selected zone, so each
try selects the zone (DP 106 and 107), writes the action, and reads the status back.
The Tuya cloud is not used: its schedule ignores the zone.
"""
import datetime
import re
import sys
import time

import tinytuya

from common import get_logger, setup_logging
from config import lightsConfig
from secret import wlBox2LocalKey

log = get_logger("lights")

ACTIONS_POWER = {"on": True, "off": False}
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def now():
    return datetime.datetime.now()


def colour_hex(h, s, v):
    """DP 24: hue 0-360, saturation 0-1000, value 0-1000, four hex digits each."""
    return "%04x%04x%04x" % (h, s, v)


def check_config(cfg):
    """Raise ValueError for an entry that the box cannot do (spec section 4)."""
    for entry in cfg["schedule"]:
        at, zones, action = entry
        if not TIME_RE.match(at):
            raise ValueError("bad time %r in %r" % (at, entry))
        if not zones or any(not isinstance(z, int) or not 1 <= z <= 16 for z in zones):
            raise ValueError("bad zones in %r" % (entry,))
        if action not in ACTIONS_POWER and action not in cfg["colours"]:
            raise ValueError("unknown action in %r" % (entry,))
        if action in cfg["colours"] and any(z not in cfg["colour_zones"] for z in zones):
            raise ValueError("colour on a zone that is not a colour zone in %r" % (entry,))


def action_dps(action, cfg):
    """The DPs that an action writes after the zone select (spec section 2.3)."""
    if action in ACTIONS_POWER:
        return {"20": ACTIONS_POWER[action]}
    return {"20": True, "21": "colour", "24": colour_hex(*cfg["colours"][action])}


def due(schedule, at, done, catch_up_min):
    """The (index, occurrence) pairs to run now, in time order (spec section 2.5).

    An occurrence today or yesterday is due if it is at most catch_up_min in the past
    and not in done. Yesterday covers the 23:59 entry after midnight.
    """
    window = datetime.timedelta(minutes=catch_up_min)
    result = []
    for index, (hhmm, _zones, _action) in enumerate(schedule):
        t = datetime.datetime.strptime(hhmm, "%H:%M").time()
        for day in (at.date(), at.date() - datetime.timedelta(days=1)):
            occurrence = datetime.datetime.combine(day, t)
            if occurrence <= at and at - occurrence <= window and (index, occurrence) not in done:
                result.append((index, occurrence))
    return sorted(result, key=lambda item: item[1])


def _error(reply):
    if isinstance(reply, dict) and "Error" in reply:
        return reply["Error"]
    return None


def try_zone(device, zone, dps, cfg):
    """One try: select, act, read back. None if good, else the reason (spec section 2.4).

    The check uses DP 106 and DP 20 only. The box can report an old DP 24 after a good colour change.
    """
    reason = _error(device.set_multiple_values({"106": zone, "107": zone}))
    if reason:
        return reason
    time.sleep(cfg["select_wait_s"])
    reason = _error(device.set_multiple_values(dps))
    if reason:
        return reason
    time.sleep(cfg["select_wait_s"])
    status = device.status()
    reason = _error(status)
    if reason:
        return reason
    state = (status or {}).get("dps", {})
    if state.get("106") != zone:
        return "zone %s selected, not %s" % (state.get("106"), zone)
    if state.get("20") != dps["20"]:
        return "power is %s, not %s" % (state.get("20"), dps["20"])
    return None


def run_zone(make_device, zone, action, cfg):
    """Up to cfg["tries"] tries, a new connection for each. One ERROR line if all fail."""
    dps = action_dps(action, cfg)
    reason = None
    for attempt in range(1, cfg["tries"] + 1):
        if attempt > 1:
            log.warning("zone %d %s try %d bad: %s", zone, action, attempt - 1, reason)
            time.sleep(cfg["retry_wait_s"])
        device = None
        try:
            device = make_device()
            reason = try_zone(device, zone, dps, cfg)
        except Exception as e:
            reason = str(e) or type(e).__name__
        finally:
            if device is not None:
                try:
                    device.close()
                except Exception:
                    pass
        if reason is None:
            log.info("zone %d %s ok (try %d)", zone, action, attempt)
            return True
    log.error("zone %d %s failed: %s", zone, action, reason)
    return False


def run_entry(make_device, zones, action, cfg):
    """Each zone in order. A failed zone does not stop the next."""
    for i, zone in enumerate(zones):
        if i:
            time.sleep(cfg["zone_wait_s"])
        run_zone(make_device, zone, action, cfg)


def box(cfg=lightsConfig):
    """A new local connection to the box. Our own tries replace the retries of tinytuya."""
    device = tinytuya.Device(cfg["device_id"], cfg["ip"], wlBox2LocalKey, version=cfg["version"],
                             connection_timeout=5, connection_retry_limit=1)
    device.set_socketTimeout(5)
    return device


def _next_time(schedule, at):
    hhmm = at.strftime("%H:%M")
    times = sorted(entry[0] for entry in schedule)
    return next((t for t in times if t > hhmm), times[0])


def main(cfg=lightsConfig, make_device=None):
    setup_logging()
    try:
        check_config(cfg)
    except (ValueError, KeyError, TypeError) as e:
        log.error("bad lightsConfig: %s", e)
        sys.exit(1)
    make_device = make_device or (lambda: box(cfg))
    if not cfg["enabled"]:
        log.info("schedule disabled")
        while True:
            time.sleep(3600)
    schedule = cfg["schedule"]
    log.info("started, %d entries, next %s", len(schedule), _next_time(schedule, now()))
    done = set()
    while True:
        at = now()
        for index, occurrence in due(schedule, at, done, cfg["catch_up_min"]):
            done.add((index, occurrence))
            _hhmm, zones, action = schedule[index]
            run_entry(make_device, zones, action, cfg)
        done = {item for item in done if at - item[1] < datetime.timedelta(days=2)}
        time.sleep(cfg["loop_s"])


if __name__ == '__main__':
    main()
