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

class _Mqttoptions:
    def __init__(self) -> None:
        self.reset_on_error = False
        self.name = "undefined"
        self.topic = "fsmqtt/undefined/"

options = _Mqttoptions()
_callbacks = dict()

def _safe_decode(value):
    """Convert bytes to utf-8 string if possible, otherwise return repr(value)."""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except Exception:
            return repr(value)
    return value

def connect(client, name=None, reset_on_error=True):

    if isinstance(client, str):
        import umqttsimple
        if name is None:
            name = client
        client = umqttsimple.MQTTClient(client, '192.168.178.5')

    options.name = name if name is not None else board.LOCATION
    options.reset_on_error = reset_on_error

    if 'undefined' in options.topic:
        options.topic = 'fsmqtt/' + options.name + '/'

    while True:
        try:
            net.start_wlan(32)
            board.MQTT = client
            board.MQTT.connect()
            if board.DEBUG:
                print('MQTT connected')
            publish("info", "connected")
            return True
        except OSError as e:
            if board.DEBUG:
                print('ERROR: MQTT connect failed: {}'.format(e))
            if not reset_on_error:
                return False
            # give some time to hit ctrl-c on terminal or do something smart via CAN bus
            utime.sleep(60)
            machine.reset()


def publish_raw(topic, message):
    """publish message to topic without prefixing with options.topic"""
    if board.MQTT:
        try:
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

def _mqtt_callback(topic, message):
    # print("got MQTT message: T='{}, M='{}'".format(topic, message))
    # try to decode topic/message to strings for easier handling by callbacks
    m_str = _safe_decode(message)
    # prefer exact bytes-key match, fall back to decoded-string key
    cb = _callbacks.get(topic, None)
    if cb is not None:
        if False:
            print('# MQTT running callback for T={}, M={}'.format(t_str, m_str))
        # call callback with decoded strings
        cb(message, m_str)

async def _mqtt_poller_task():
    while True:
        if not board.MQTT:
            await asyncio.sleep_ms(1000)
            continue
        msg = board.MQTT.check_msg()
        if msg is not None:
            print('Poller got message: M={}'.format(msg))
        await asyncio.sleep_ms(10)

board.BACKGROUND_RUNNERS.append(_mqtt_poller_task())


def subscribe_raw(topic, callback):
    """subscribe to topic without prefixing with options.topic"""
    if not board.MQTT:
        return
    if not isinstance(topic, bytes):
        topic = bytes(topic, 'utf-8')
    _callbacks[topic] = callback
#    # also store the decoded string form for convenience
#    try:
#        _callbacks[_safe_decode(topic)] = callback
#    except Exception:
#        pass
    if board.DEBUG:
        print('MQTT subscribed to {}'.format(topic))
    board.MQTT.set_callback(_mqtt_callback)
    board.MQTT.subscribe(topic)


def subscribe(topic, callback):
    """subscribe to topic, prefixing with options.topic"""
    subscribe_raw(options.topic + topic, callback)
