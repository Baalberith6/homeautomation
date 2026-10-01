import functools
import logging
import sys
import time

from paho.mqtt import client as mqtt_client
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from config import mqttConfig
from secret import mqttUsername, mqttPassword
from config import generalConfig as c

publishProperties=Properties(PacketTypes.PUBLISH)
publishProperties.MessageExpiryInterval = 86400  # in seconds

# Change 020: every log line starts with its level, so an alert rule can match "^ERROR ".
LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


class StdoutHandler(logging.StreamHandler):
    """Writes each record to the sys.stdout of the moment and flushes it (change 020).

    The flush after each record puts the line in the journal at once, also when
    stdout is block-buffered. A test that patches sys.stdout sees the line.
    """

    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter(LOG_FORMAT))

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value):
        pass


def get_logger(name):
    """The logger of a service: `LEVEL name: message` on stdout, INFO and up, DEBUG if debug is on."""
    logger = logging.getLogger(name)
    if not any(isinstance(h, StdoutHandler) for h in logger.handlers):
        logger.addHandler(StdoutHandler())
    logger.setLevel(logging.DEBUG if c["debug"] else logging.INFO)
    logger.propagate = False
    return logger


def setup_logging():
    """Library log records get the same format, WARNING and up. Call once, in the main guard.

    The root stays at WARNING also in debug mode: netatmo.py writes the refresh token at DEBUG.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, StdoutHandler):
            root.removeHandler(handler)
    handler = StdoutHandler()
    handler.setLevel(logging.WARNING)
    root.addHandler(handler)
    root.setLevel(logging.WARNING)


def default_requests_timeout(seconds):
    """Give each requests call of this process that has no timeout this one (change 020).

    For the services whose libraries call requests with no timeout and take no
    parameter for it (metno_locationforecast in yr.py, tinytuya in moes_co2.py).
    socket.setdefaulttimeout() does not reach them: requests passes timeout=None
    down to the socket, and the socket then blocks.
    """
    import requests
    request = requests.Session.request
    if getattr(request, "default_timeout", None) is not None:
        request = request.__wrapped__

    @functools.wraps(request)
    def with_timeout(self, method, url, *args, **kwargs):
        if len(args) < 7 and kwargs.get("timeout") is None:
            kwargs["timeout"] = seconds
        return request(self, method, url, *args, **kwargs)

    with_timeout.default_timeout = seconds
    requests.Session.request = with_timeout


# An HTTP poll alerts on the third failure in a row (change 020 revision 9).
HTTP_ALERT_AFTER = 3


class ConnectionLog:
    """At most one line per interval while a connection is down, one INFO when it is back (change 020).

    The line is an ERROR, which fires the alert R3. With a grace time (revision 4), a connection
    that has been down for less than grace seconds writes a WARNING instead, so a short outage of
    a cloud API sends no message. With alert_after (revision 9), the line is a WARNING until that
    many failures in a row; both conditions must hold for an ERROR.
    """

    def __init__(self, logger, name, interval=60, grace=0, alert_after=1):
        self.logger = logger
        self.name = name
        self.interval = interval
        self.grace = grace
        self.alert_after = alert_after
        self.failures = 0
        self.down = False
        self.down_since = None
        self.last_line = None

    def failed(self, err, exc_info=False):
        now = time.monotonic()
        self.failures += 1
        if not self.down:
            self.down = True
            self.down_since = now
        if self.last_line is None or now - self.last_line >= self.interval:
            self.last_line = now
            if now - self.down_since >= self.grace and self.failures >= self.alert_after:
                self.logger.error("%s failed: %s", self.name, err, exc_info=exc_info)
            else:
                self.logger.warning("%s failed: %s", self.name, err)

    def ok(self):
        self.failures = 0
        if self.down:
            self.down = False
            self.down_since = None
            self.last_line = None
            self.logger.info("%s restored", self.name)


mqtt_log = get_logger("mqtt")


class DefaultPublishClient(mqtt_client.Client):
    """paho Client whose publish() uses QoS 2 and publishProperties by default (change 013, D7)."""

    # The topics that on_connect subscribes to on each connect (change 020, D9).
    resubscribe_topics = ()

    def publish(self, topic, payload=None, qos=2, retain=False, properties=publishProperties):
        return super().publish(topic, payload, qos, retain, properties)


def _reason_text(reason):
    if isinstance(reason, ReasonCode):
        return str(reason)
    try:
        return mqtt_client.error_string(int(reason))
    except (TypeError, ValueError):
        return str(reason)


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        mqtt_log.info("connected")
        for topic in client.resubscribe_topics:
            client.subscribe(topic)
    else:
        mqtt_log.error("connect failed: %s", _reason_text(reason_code))


def _on_disconnect(client, userdata, reason_code, properties=None):
    if reason_code == 0:
        mqtt_log.info("disconnected")
    else:
        mqtt_log.error("disconnected: %s", _reason_text(reason_code))


def subscribe_on_connect(client, topics):
    """Subscribe now if connected, and again on each connect (change 020, D9).

    The broker starts a new session after a reconnect, so a subscription made only once is lost.
    """
    client.resubscribe_topics = list(topics)
    if client.is_connected():
        for topic in client.resubscribe_topics:
            client.subscribe(topic)


def new_client(client_id):
    """A client with the log and resubscribe callbacks, not connected yet."""
    if c["debug"]:
        client_id = client_id + "-dev"
    client = DefaultPublishClient(client_id=client_id, protocol=mqtt_client.MQTTv5)
    client.username_pw_set(mqttUsername, mqttPassword)
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    return client


def connect_mqtt(client_id):
    client = new_client(client_id)
    try:
        client.connect(mqttConfig["broker"], mqttConfig["port"])
    except Exception as e:
        mqtt_log.error("connect to %s:%s failed: %s", mqttConfig["broker"], mqttConfig["port"], e)
        raise
    return client
