"""
MQTT support. Use in main like

from umqttsimple import MQTTClient
import fsmqtt

fsmqtt.connect('kegellampe')


fsmqtt.connect(MQTTClient(clientid, fsmqtt.secrets.mqtt_server), name="myname", reset_on_error=True)

fsmqtt.connect(MQTTClient(board.LOCATION, fsmqtt.secrets.mqtt_server))

mqttclient = MQTTClient(board.LOCATION, fsmqtt.secrets.mqtt_server)
fsmqtt.connect(board.LOCATION, mqttclient)


This avoids importing the umqttsimple here in this module and small footprint for publish.

The publish function in this module is basically like mqtt.publish() but handles errors (e.g. reset if sending fails)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments, no-member

import board
#import asyncio
import asyncio
import net
import utime
import machine
import umqttsimple
import time
import sys

class _MQTT:
    """MQTT client wrapper"""

    def __init__(self):
        self.status = "disconnected"
        self.client = None
        self.topic = None
        self.reset_on_error = False
        self._is_connected_event = asyncio.Event()

        self.blessed_topic = ""
        """Topic that has been sent by ourself, do not process it."""

        self.ignored_topics = set()
        """Topics to ignore, do not pass them to callbacks or raise errors."""

        self.callbacks = {
            "config": self._config_command,
        }

        """Registered callbacks for topics."""

        self.after_connect = []
        """Functions to run after connect."""

        self._rssi_task = None
        self._keepalive_task = None

    def run_after_connect(self, *callbacks):
        self.after_connect.extend(callbacks)

    def connected(self):
        return self.status == "connected"

    async def wait_for_connection(self):
        while not self.connected():
            await asyncio.sleep_ms(100)

    def subscribe(self, topic: str, callback):
        # if not isinstance(topic, bytes):
        #     topic = bytes(topic, 'utf-8')
        # self.client.subscribe(self.topic + topic)
        board.PRINTF('MQTT subscribed to {}', topic)
        self.callbacks[topic] = callback

    def publish(self, topic: str, message):
        """publish message to topic, prefixing with self.topic"""
        if not self.connected():
            return False
        return self.publish_raw(self.topic + topic, message)

    def publish_raw(self, topic: str, message):
        """publish message to topic without prefixing with self.topic"""
        if not self.connected():
            return False
        self.blessed_topic = topic
        try:
            if isinstance(message, int):
                message = str(message)
            if isinstance(message, float):
                message = str(message)
            self.client.publish(topic, message)
            return True
        except OSError as e:
            if board.DEBUG:
                print('ERROR: MQTT send T="{}" M="{}" failed: {}'.format(topic, message, e))
            try:
                self.client.ping()
                # hm, ping worked but publish failed --> strange error
                print('ERROR: MQTT send but ping still working')
                return False
            except Exception:
                board.PRINTF('MQTT ping failed, reconnecting')
                self.status = "connecting"
            if self.reset_on_error:
                machine.reset()
        return False

    def ignore_topics(self, *topics):
        """ignore topics, do not pass them to callbacks or raise errors"""
        for topic in topics:
            self.ignored_topics.add(topic)

    def _mqtt_callback(self, topic, message):
        """Handle messages received from MQTT - dispatch to registered callbacks"""
        # board.PRINTF("got MQTT message: T='{}, M='{}'", topic, message)
        # try to decode topic/message to strings for easier handling by callbacks
        m_str = _safe_decode(message)
        # prefer exact bytes-key match, fall back to decoded-string key
        t_str_full = _safe_decode(topic)
        if t_str_full == self.blessed_topic:
            self.blessed_topic = ""
            return
        t_str = t_str_full[len(self.topic):]

        if t_str in self.ignored_topics:
            return

        cb = self.callbacks.get(t_str, None)
        if cb is not None:
            board.PRINTF('# MQTT running callback for T={}, M={}', topic, m_str)
            # call callback with decoded strings
            try:
                cb(t_str, m_str)
            except Exception as e:
                board.PRINTF('MQTT callback failed: {}', e)
            return

        # catch all system topics, should be done by _blessed_topic
        if t_str == "info" or t_str == "error":
            return
        if t_str.startswith("info/") or t_str.startswith("error/"):
            return
        if t_str.startswith("state/") or t_str.startswith("status/"):
            return

        board.PRINTF('MQTT unknown topic: T={}, M={}, full topic: {}, blessed: {}, known topics: {}',
            t_str, m_str, t_str_full, self.blessed_topic, self.callbacks.keys())

        self.publish("error", "no callback for T='{}', M='{}'".format(t_str, m_str))


    def _config_command(self, topic, msg):
        """
        CONFIG: uptime, memstat, restart, watchdog, reset, repl, repl-disable, repl-enable
        commands exposed by MQTT
        """
        board.PRINTF('CONFIG: {}', msg)
        msg = str(msg).lower()
        if msg == "uptime":
            board.PRINTF('UPTIME: {}', time.time())
            self.publish('info/uptime', time.time())
            return
        if msg == "memstat":
            board.PRINTF('MEMSTAT: {}', memstat.get())
            self.publish('info/memstat', memstat.get())
            return
        if msg == "restart" or msg == "reboot" or msg == "soft-reset":
            board.PRINTF('RESTART')
            self.publish('info/restart', "going to restart board (using soft reset)")
            board.restart()
            return
        if msg == "reset" or msg == "hard-reset":
            board.PRINTF('RESET')
            self.publish('info/reset', "going to reset board (using hard reset)")
            board.reset()
            return
        if msg == "watchdog":
            board.PRINTF('WATCHDOG')
            self.publish('info/watchdog', "WATCHDOG started")
            board.watchdog.start()
            return
        if msg == "wrestart":
            board.PRINTF('WATCHDOG restart')
            self.publish('info/watchdog_restart', "WATCHDOG will trigger restart in 20 seconds")
            utime.sleep(20)
            return
        if msg == "repl":
            net.start_repl()
            return
        if msg == "repl-disable":
            net.stop_repl()
            return
        if msg == "repl-enable":
            net.start_repl()
            return

        if msg == "rssi-off":
            self.stop_rssi_reporting()
            return

        if msg.startswith("rssi"):
            mx = str(msg).split(" ")
            if len(mx) < 2:
                self.print_rssi()
                return
            try:
                period_ms = min(500, int(mx[1]))
            except Exception:
                self.publish('error', "Bad RSSI period {}".format(str(msg)))
                return
            board.PRINTF('RSSI period: {} ms', period_ms)
            self.publish('info/rssi_period', period_ms)
            self.start_rssi_reporting(period_ms)
            return

        board.PRINTF('CONFIG: unknown command: {}', msg)
        self.publish('info/config', "unknown command: {}".format(msg))

    def print_rssi(self):
        board.PRINTF('RSSI: {}', board.NET.rssi())
        self.publish('info/rssi', board.NET.rssi())

    async def print_rssi_task(self, period_ms):
        while True:
            self.print_rssi()
            await asyncio.sleep_ms(period_ms)

    def start_rssi_reporting(self, period_ms):
        self.stop_rssi_reporting()
        self._rssi_task = asyncio.create_task(self.print_rssi_task(period_ms))

    def stop_rssi_reporting(self):
        if self._rssi_task:
            self._rssi_task.cancel()
            self._rssi_task = None

    def connect_in_background(self, topic=None, reset_on_error=False, name=None, repl=True):
        """Connect to MQTT in background, keep connection alive and publish info/status topics."""
        if self.client:
            board.PRINTF('WARNING: MQTT already connected')
            return
        board.NET.connect_in_background(repl=repl)
        self.reset_on_error = reset_on_error
        self.name = name if name is not None else board.LOCATION
        self.topic = topic if topic is not None else 'hcm/' + self.name + '/'
        board.PRINTF('MQTT topic: {}', self.topic)
        clientid = board.NET.mac_address()
        # limit client id to 23 characters for compatibility
        if len(clientid) > 23:
            clientid = clientid[-23:]
        board.PRINTF('MQTT client id: {}', clientid)
        self.client = umqttsimple.MQTTClient(clientid, '192.168.178.5')
        self.client.set_last_will(self.topic + "disconnected", self.name)

        self._keepalive_task = asyncio.create_task(self._keepalive())
        asyncio.create_task(self._poll_for_new_messages())

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            # self.client = None

    async def _keepalive(self):
        self.status = "connecting"

        # endless loop to keep the connection alive
        while True:
            if not board.NET.isconnected():
                await board.NET.wait_for_connection("fsmqtt._keepalive")
                continue

            if self.status == "connected":
                # check regularily if we are still connected
                await asyncio.sleep_ms(20 * 1000)
                try:
                    self.client.ping()
                    continue # all good
                except Exception:
                    board.PRINTF('MQTT ping failed, reconnecting')
                    self.status = "connecting"
                    self._is_connected_event.clear()
                    # fall through to reconnect

            # connection down, try to reconnect
            if self.status == "connecting":
                board.PRINTF('waiting for MQTT to connect')
                # trust nobody
                try:
                    self.client.disconnect()
                except Exception:
                    pass

            try:
                # an async function would be nice here
                self.client.connect()
                self.status = "connected"
                ipstring = board.NET.ipstring()
                board.PRINTF('MQTT connected {}', ipstring)
                self.publish_raw("hcm/connected", self.name) # IP address is published by info topic below
                # TODO: check which of the calls below should be called after each reconnect (e.g. set_callback or subscribe)
                self.client.set_callback(self._mqtt_callback)
                self.client.subscribe(self.topic + "#")
                # self._subscribe_to_all()
                # subscribe to all topics, bad messages will be printed by global callback
                # self.subscribe('#', lambda topic, msg: board.PRINTF('MQTT: {} / {}', topic, msg))
                self.publish_info()
                self.publish_all()
                self._is_connected_event.set()
                for func in self.after_connect:
                    try:
                        func()
                    except Exception as e:
                        board.PRINTF('ERROR fsmqtt: after_connect failed: {}', e)

                continue

            except Exception as e:
                board.PRINTF('ERROR: MQTT connect failed: {}', e)
                self.status = "undefined"
                await asyncio.sleep_ms(1000)
                continue

            # huh? undefined status? try to reconnect
            self._is_connected_event.clear()
            self.status = "connecting"
            await asyncio.sleep_ms(1000)
            continue

    def _subscribe_to_all(self):
        # We could subscribe to all callbacks that have been registered by the user before MQTT was loaded.
        # This can be done e.g. by the pwm module, which itself does not load fsmqtt but registers callbacks.
        # This would keep the import order flexible.
        # However, this is not done, this allows to prevent exposing some callbacks to the user (e.g. pwm callbacks if pwm is imported before fsmqtt).
        if board.MQTT.callbacks:
            board.PRINTF('MQTT: warning: callbacks registered before MQTT was loaded')
            # for topic, callback in board.MQTT.callbacks.items():
            #     self.subscribe(topic, callback)
        # TODO: PWMs - this should go into the pwm module
        # if board.PWMs:
        #     for p in board.PWMs.pwms:
        #         # ha/light/led_mg_buero_dimm_spotwand/set
        #         # subscribe_raw('light/{}/{}/set'.format(board.LOCATION, p.portid), p.mqtt_callback)
        #         self.subscribe('set/{}'.format(p.portid), p.mqtt_callback)

    def publish_info(self):
        """Publish info topic with board information."""
        mac = board.NET.mac_address()
        ip = board.NET.ipstring()
        rssi = board.NET.rssi()
        if board.PWMs:
            pwms = ','.join([str(p.portid) for p in board.PWMs.pwms])
        else:
            pwms = 'none'
        info = 'version={}; mac={}; IP={}; rssi={}; pwms={}'.format(
            board.VERSION, mac, ip, rssi, pwms)
        try:
            mpy = sys.implementation._mpy
            info += "; mpy=" + str(mpy)
        except Exception:
            pass
        compiled = "0000-00-00 00:00:00"
        try:
            # try to get compile time from lup module (if available)
            import lup
            # microPython uses 2000-01-01 00:00:00 as epoch - magic conversion
            t = time.localtime(lup.T - 30*31556926 + 8*3600 - 60*35 - 120)
            compiled = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
            info += "; compiled=" + compiled
        except Exception:
            pass
        board.PRINTF('publishing info: {}', info)
        self.publish("info", info)

    def publish_all(self):
        """publish status of all registered devices"""
        pass

    async def _poll_for_new_messages(self):
        board.PRINTF('MQTT poller started')
        while True:
            if self.client is None:
                await self._is_connected_event.wait()
                board.PRINTF('MQTT poller: client is now available')
                continue
            if self.client.sock is None:
                # still waiting for network connection
                await self._is_connected_event.wait()
                board.PRINTF('MQTT poller: still waiting for MQTT client to open socket')
                continue
            if self.status == "connected":
                try:
                    # check for incoming messages
                    # this will call the callback for each message
                    self.client.check_msg()
                except Exception as e:
                    board.PRINTF('ERROR: MQTT poller failed: {}', e)
                    self.status = "connecting"
                    await asyncio.sleep_ms(2000)
            else:
                #
                await asyncio.sleep_ms(1000)

            # always sleep a bit to avoid busy loop if no messages are coming in
            await asyncio.sleep_ms(10)


def _print_rssi():
    try:
        rssi = net.wlan.status('rssi')
    except Exception:
        return
    board.PRINTF('RSSI: {} dBm', rssi)
    board.MQTT.publish('info/rssi', rssi)


async def _print_rssi_task(period_ms):
    while True:
        await asyncio.sleep_ms(period_ms)
        _print_rssi()

def register_mqtt_client(client):
    board.MQTT = client

register_mqtt_client(_MQTT())

def connect():
    """Connect to MQTT and setup async functions that keep the connection alive and report RSSI, etc."""
    global _CLIENT
    global _rssi_task
    if _CLIENT:
        return
    _CLIENT = _MQTTClient()
    # copy callbacks from dummy mqtt
    _CLIENT.callbacks.update(board.MQTT.callbacks)
    _CLIENT.after_connect.extend(board.MQTT.after_connect)
    asyncio.create_task(_CLIENT.connect_in_background())
    asyncio.create_task(_CLIENT._poll_for_new_messages())
    _rssi_task = asyncio.create_task(_print_rssi_task(5 * 60 * 1000))
    board.MQTT = _CLIENT


def _safe_decode(value):
    """Convert bytes to utf-8 string if possible, otherwise return repr(value)."""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except Exception:
            return repr(value)
    return value

# TODO: PWMs should register their callbacks with board.MQTT.after_connect
# def publish_all():
#     if board.PWMs:
#         for p in board.PWMs.pwms:
#             p.send_telemetry()

def connect_in_background(name=None):
    if False:
        asyncio.create_task(_connect_in_background(name))
        asyncio.create_task(_mqtt_poller_task())
    else:
        board.BACKGROUND_RUNNERS.append(_connect_in_background(name))
        board.BACKGROUND_RUNNERS.append(_mqtt_poller_task())




def xxpublish_raw(topic, message):
    """publish message to topic without prefixing with options.topic"""
    if board.MQTT and board.MQTT.sock != None:
        global _blessed_topic
        _blessed_topic = topic
        try:
            if isinstance(message, int):
                message = str(message)
            if isinstance(message, float):
                message = str(message)
            board.MQTT.publish(topic, message)
            return True
        except OSError as e:
            if board.DEBUG:
                print('ERROR: MQTT send T="{}" M="{}" failed: {}'.format(topic, message, e))
            if options.reset_on_error:
                machine.reset()
    return False

def xxpublish(topic, message):
    """publish message to topic, prefixing with options.topic"""
    return publish_raw(options.topic + topic, message)


xxx_ignored_topics = dict()

def xxxignore_topics(*topics):
    """ignore topics, do not pass them to callbacks or raise errors"""
    for topic in topics:
        _ignored_topics[topic] = True

def _mqtt_callback(topic, message):
    # board.PRINTF("got MQTT message: T='{}, M='{}'", topic, message)
    # try to decode topic/message to strings for easier handling by callbacks
    global _blessed_topic
    m_str = _safe_decode(message)
    # prefer exact bytes-key match, fall back to decoded-string key
    t_str_full = _safe_decode(topic)
    if t_str_full == _blessed_topic:
        _blessed_topic = ""
        return
    t_str = t_str_full[len(options.topic):]

    if t_str in _ignored_topics:
        return

    cb = _callbacks.get(t_str, None)
    if cb is not None:
        board.PRINTF('# MQTT running callback for T={}, M={}', topic, m_str)
        # call callback with decoded strings
        cb(message, m_str)
    else:
        # catch all unknown topics
        global _blessed_topic
        if t_str == _blessed_topic:
            return

        # catch all system topics, should be done by _blessed_topic
        if t_str == "info" or t_str == "error":
            return
        if t_str.startswith("info/") or t_str.startswith("error/"):
            return
        if t_str.startswith("state/") or t_str.startswith("status/"):
            return

        board.PRINTF('MQTT unknown topic: T={}, M={}, full topic: {}, blessed: {}, known topics: {}',
            t_str, m_str, t_str_full, _blessed_topic, _callbacks.keys())

        publish("error", "no callback for T='{}', M='{}'".format(t_str, m_str))

    board.PRINTF('MQTT done: T={}, M={}', topic, message)

def _subscribe(topic, register, callback):
    if not isinstance(topic, bytes):
        topic = bytes(topic, 'utf-8')
    _callbacks[register] = callback
    if board.DEBUG:
        board.PRINTF('MQTT subscribed to {}', topic)
    if not board.MQTT:
        return
    board.MQTT.subscribe(topic)

def subscribe_raw(topic, callback):
    """subscribe to topic without prefixing with options.topic"""
    _subscribe(topic, topic, callback)

def subscribe(topic, callback):
    """subscribe to topic, prefixing with options.topic"""
    _subscribe(options.topic + topic, topic, callback)
