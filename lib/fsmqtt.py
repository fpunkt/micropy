"""
MQTT support. Use in main like

from umqttsimple import MQTTClient
import fsmqtt

fsmqtt.connect(MQTTClient(clientid, fsmqtt.secrets.mqtt_server), name="myname", reset_on_error=True)

fsmqtt.connect(MQTTClient(board.LOCATION, fsmqtt.secrets.mqtt_server))

mqttclient = MQTTClient(board.LOCATION, fsmqtt.secrets.mqtt_server)
fsmqtt.connect(board.LOCATION, mqttclient)


This avoids importing the umqttsimple here in this module and small footprint for publish.

The publish function in this module is basically like mqtt.publish() but handles errors (e.g. reset if sending fails)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments, no-member

import secrets
import board
import uasyncio as asyncio
import net
import utime
import machine

class _Mqttoptions:
    def __init__(self) -> None:
        self.reset_on_error = False
        self.name = "undefined"

options = _Mqttoptions()
_callbacks = dict()

def connect(client, name=None, reset_on_error=True):
    options.name = name if name is not None else board.LOCATION
    options.reset_on_error = reset_on_error

    while True:
        try:
            net.start_wlan()
            board.MQTT = client
            board.MQTT.connect()
            if board.DEBUG:
                print('MQTT connected')
            board.MQTT.publish("info", options.name+"/connected")
            return True
        except OSError as e:
            if board.DEBUG:
                print('ERROR: MQTT connect failed: {}'.format(e))
            if not reset_on_error:
                return False
            # give some time to hit ctrl-c on terminal or do something smart via CAN bus
            utime.sleep(60)
            machine.reset()

def publish(topic, message):
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

def _mqtt_callback(topic, message):
    # print("got MQTT message: T='{}, M='{}'".format(topic, message))
    cb = _callbacks.get(topic, None)
    if cb is not None:
        if False:
            print('# MQTT runnning callback for T={}, M={}'.format(topic, message))
        cb(topic, message)

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


def subscribe(topic, callback):
    if not board.MQTT:
        return
    if not isinstance(topic, bytes):
        topic = bytes(topic, 'utf-8')
    _callbacks[topic] = callback
    if board.DEBUG:
        print('MQTT subscribed to {}'.format(topic))
    board.MQTT.set_callback(_mqtt_callback)
    board.MQTT.subscribe(topic)
