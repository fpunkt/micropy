"""
MQTT client with some PWMs connected
"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'eg/xmasvorne'
board.DEBUG = True
board.CANID = 0x140

if board.DEBUG is True:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.start_wlan()
    net.start_repl()

import gc
import bconf
import can
import machine
import sensors
import pwm
import button
import uasyncio as asyncio
import fsmqtt
from umqttsimple import MQTTClient

p1 = pwm.PWM(1, bconf.AUX1_YELLOW)
p2 = pwm.PWM(2, bconf.AUX1_WHITE)
pl = pwm.List(0x20, p1, p2)

p = p1

if True: # some buttons for debugging
    b1 = button.Button(10, bconf.AUX3_WHITE)
    b2 = button.Button(11, bconf.AUX3_YELLOW)
    def button_callback(button): # pylint: disable=redefined-outer-name
        if board.DEBUG:
            print('Button pressed: {}'.format(button))
    b1.callback = button_callback
    b1.pwm = p1
    b1.autorepeat_arm_ms = 0
    b2.pwm = p2

dht = sensors.DHT(20, bconf.AUX2_YELLOW, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(2))

mqttclient = MQTTClient(board.LOCATION, fsmqtt.secrets.mqtt_server)
fsmqtt.connect(mqttclient, board.LOCATION)

def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
