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
    net.LED = board.LED
    net.start_wlan()
    net.start_repl()

import gc
gc.collect()

print('# loading bconf')
#import bconf
print('# loading sensors')
import sensors
print('# loading pwm')
import pwm
print('# loading button')
import button
print('# loading asyncio')
import uasyncio as asyncio
print('# loading fsmqtt')
import fsmqtt

import machine

from umqttsimple import MQTTClient
mqttclient = MQTTClient(board.LOCATION, fsmqtt.secrets.mqtt_server)
import fsmqtt
fsmqtt.connect(mqttclient, board.LOCATION)


print("mem: ", gc.mem_free())
gc.collect()
print("mem: ", gc.mem_free())

#p1 = pwm.PWM(1, 14)
#p2 = pwm.PWM(2, 12)
#pl = pwm.List(0x20, p1, p2)
#
#p = p1

p1 = pwm.PWM(1, 14)
p2 = pwm.PWM(2, 12)
p3 = pwm.PWM(3, 13)

p1.seti(1023)
p2.seti(1023)
p3.seti(1023)


if False: # some buttons for debugging
    b1 = button.Button(10, bconf.AUX3_WHITE)
    b2 = button.Button(11, bconf.AUX3_YELLOW)
    def button_callback(button): # pylint: disable=redefined-outer-name
        if board.DEBUG:
            print('Button pressed: {}'.format(button))
    b1.callback = button_callback
    b1.pwm = p1
    b1.autorepeat_arm_ms = 0
    b2.pwm = p2

#dht = sensors.DHT(20, bconf.AUX2_YELLOW, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(2))


def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
