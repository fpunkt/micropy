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
import uasyncio as asyncio
import net
import utime
import machine
import umqttsimple
import time

after_connect = []

class _Mqttoptions:
    def __init__(self) -> None:
        self.reset_on_error = False
        self.name = "undefined"
        # topic can be either None or a string like "hcm/myname/"
        self.topic = "undefined"


def _config(_, msg):
    """
    CONFIG: uptime, memstat, restart, watchdog, wrestart, repl, repl-disable, repl-enable
    commands exposed by MQTT 
    """
    import net
    board.PRINTF('CONFIG: {}', msg)
    msg = str(msg).lower()
    if msg == "uptime":
        board.PRINTF('UPTIME: {}', time.time())
        board.MQTT_PUBLISH('info/uptime', time.time())
        return
    if msg == "memstat":
        board.PRINTF('MEMSTAT: {}', memstat.get())
        board.MQTT_PUBLISH('info/memstat', memstat.get())
        return
    if msg == "restart":
        board.PRINTF('RESTART')
        board.MQTT_PUBLISH('info/restart', "going to restart board (using reset)")
        board.reset()
        return
    if msg == "watchdog":
        board.PRINTF('WATCHDOG')
        board.MQTT_PUBLISH('info/watchdog', "WATCHDOG started")
        board.watchdog.start()
        return
    if msg == "wrestart":
        board.PRINTF('WATCHDOG restart')
        board.MQTT_PUBLISH('info/watchdog_restart', "WATCHDOG will trigger restart in 20 seconds")
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
    board.PRINTF('CONFIG: unknown command: {}', msg)
    board.MQTT_PUBLISH('info/config', "unknown command: {}".format(msg))


options = _Mqttoptions()

_blessed_topic = ""
"""Topic that has been sent by ourself, do not process it."""

_callbacks = {
    "config": _config,
}

def _safe_decode(value):
    """Convert bytes to utf-8 string if possible, otherwise return repr(value)."""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except Exception:
            return repr(value)
    return value



STATUS = "undefined"

async def _connect_in_background(name=None):
    global STATUS

    STATUS = "connecting"

    options.name = name if name is not None else board.LOCATION


    if 'undefined' in options.topic:
        newname = 'hcm/' + options.name + '/'
        board.PRINTF('MQTT topic: {} -> {}', options.topic, newname)
        options.topic = newname

    clientid = net.get_mac_address()
    # limit client id to 23 characters for compatibility
    if len(clientid) > 23:
        clientid = clientid[-23:]
    board.PRINTF('MQTT client id: {}', clientid)
    board.MQTT = umqttsimple.MQTTClient(clientid, '192.168.178.5')
    board.MQTT.set_last_will("hcm/disconnected", options.name)

    
    while True:
        # board.PRINT('waiting for WLAN to connect, STATUS={} / {}'.format(net.STATUS, STATUS))
        await net.reconnect_if_needed()

        if STATUS == "connected":
            await asyncio.sleep_ms(2 * 60 * 1000)
            try:
                board.MQTT.ping()
                continue
            except Exception:
                board.PRINTF('MQTT ping failed')
                try:
                    board.MQTT.disconnect()
                except Exception:
                    pass
                STATUS = "connecting"

        if STATUS == "connecting":
            board.PRINTF('waiting for MQTT to connect')
            # trust nobody
            try:
                board.MQTT.disconnect()
            except Exception:
                pass
            try:
                board.MQTT.connect()
                cfg = net.wlan_ip()
                board.PRINTF('MQTT connected {}', cfg)
                publish_raw("hcm/connected", options.name)
                board.MQTT.set_callback(_mqtt_callback)
                board.MQTT_PUBLISH = publish
                STATUS = "connected"
                _subscribe_to_all()
                # subscribe to all topics, bad messages will be printed by global callback
                subscribe('#', lambda topic, msg: board.PRINTF('MQTT: {} / {}', topic, msg))
                publish_info()
                publish_all()
                for func in after_connect:
                    try:
                        func()
                    except Exception as e:
                        board.PRINTF('ERROR fsmqtt: after_connect failed: {}', e)

                continue

            except Exception as e:
                board.MQTT = None
                board.PRINTF('ERROR: MQTT connect failed: {}', e)
                STATUS = "undefined"
                await asyncio.sleep_ms(1000)
                continue

        if not board.MQTT:
            # huh? no MQTT connection?
            STATUS = "connecting"
            await asyncio.sleep_ms(1000)
            continue

def _subscribe_to_all():
    # board.PRINT('subscribing to topics')
    # subscribe to all topics
    # fix undefined topic
    for topic in _callbacks:
        if 'undefined' in topic:
            cb = _callbacks[topic]
            del _callbacks[topic]
            # topic = topic.replace(b'undefined', options.topic.encode('utf-8'))
            topic = topic.replace('undefined', options.topic)
            _callbacks[topic] = cb
    for topic in _callbacks:
        board.MQTT.subscribe(topic)
    if board.PWMs:
        for p in board.PWMs.pwms:
            # ha/light/led_mg_buero_dimm_spotwand/set
            # subscribe_raw('light/{}/{}/set'.format(board.LOCATION, p.portid), p.mqtt_callback)
            subscribe('set/{}'.format(p.portid), p.mqtt_callback)

def publish_all():
    if board.PWMs:
        for p in board.PWMs.pwms:
            p.send_status_to_can()

def publish_info():
    mac = net.get_mac_address()
    ip = net.get_ip_address()
    if board.PWMs:
        pwms = ','.join([str(p.portid) for p in board.PWMs.pwms])
    else:
        pwms = 'none'
    # board.PRINT(pwms)
    info = "version=" + board.VERSION + "; mac=" + mac + "; IP=" + ip + "; pwms=" + pwms
    compiled = "0000-00-00 00:00:00"
    try:
        import lup
        # microPython uses 2000-01-01 00:00:00 as epoch - magic conversion
        t = time.localtime(lup.T - 30*31556926 + 8*3600 - 60*35 - 120)
        compiled = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
    except Exception:
        pass
    info += "; compiled=" + compiled
    board.PRINTF('publishing info: {}', info)
    publish("info", info)

def connect_in_background(name=None):
    if False:
        asyncio.create_task(_connect_in_background(name))
        asyncio.create_task(_mqtt_poller_task())
    else:  
        board.BACKGROUND_RUNNERS.append(_connect_in_background(name))
        board.BACKGROUND_RUNNERS.append(_mqtt_poller_task())


def xxxconnect(client, name=None, reset_on_error=True, timeout=60):
    """Connect to MQTT server using given client (or client id string).
    If name is given, use that as the name of this client, otherwise use board.LOCATION.
    If reset_on_error is True, reset the machine on connection errors.
    timeout specifies how long to retry connecting to WLAN before giving up.
    """
    global _mqtt_connect_count
    options.name = name if name is not None else board.LOCATION
    options.reset_on_error = reset_on_error

    if 'undefined' in options.topic:
        options.topic = 'hcm/' + options.name + '/'

    while True:
        try:
            cfg = net.start_wlan(32, timeout=timeout)
            if cfg is None:
                raise OSError('cannot connect to WLAN')
            if isinstance(client, str):
                import umqttsimple
                if name is None:
                    name = client
                clientid = net.get_mac_address()+"-"+str(_mqtt_connect_count)
                # limit client id to 23 characters for compatibility
                if len(clientid) > 23:
                    clientid = clientid[-23:]
                print('MQTT client id: {}'.format(clientid))
                board.MQTT = umqttsimple.MQTTClient(clientid, '192.168.178.5')
                _mqtt_connect_count += 1
            else:
                board.MQTT = client

            board.MQTT.connect()
            board.MQTT.set_callback(_mqtt_callback)
            if board.DEBUG:
                print('MQTT connected ', cfg)
            publish("info", "connected, version=" + board.VERSION + " mac=" + net.get_mac_address() + " IP=" + str(cfg))
            board.MQTT_PUBLISH = publish
            return True
        except OSError as e:
            if board.DEBUG:
                print('ERROR: MQTT connect failed: {}'.format(e))
            if not reset_on_error:
                raise e
            # give some time to hit ctrl-c on terminal or do something smart via CAN bus
            utime.sleep(60)
            machine.reset()


def publish_raw(topic, message):
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

def publish(topic, message):
    """publish message to topic, prefixing with options.topic"""
    return publish_raw(options.topic + topic, message)

board.MQTT_PUBLISH = publish

_ignored_topics = dict()

def ignore_topics(*topics):  
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

async def _mqtt_poller_task():
    board.PRINTF('MQTT poller started')
    while True:
        if board.MQTT is None  or  STATUS != "connected":
            # board.PRINT('MQTT poller: no MQTT connection')
            await asyncio.sleep_ms(1000)
            continue

        try:
            # check for incoming messages
            # this will call the callback for each message
            board.MQTT.check_msg()

        except Exception as e:
            board.PRINTF('ERROR: MQTT poller failed: {}', e)
            await asyncio.sleep_ms(1000)
            continue
        await asyncio.sleep_ms(10)

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
