"""
CAN over WLAN client with some PWMs connected

source ../../../tools/alias.sh



"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'eg/xmasvorne'
# board.DEBUG = True
board.CANID = 0x140

board.LED = board.Led(2, 0)


if board.DEBUG is True:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

import net
net.net()

import gc
def mem(msg):
    m1 = gc.mem_free()
    gc.collect()
    if msg != "":
        print('# loading ', msg, ', free mem: ', gc.mem_free(), ' / ', m1)
    else:
        print("mem: ", gc.mem_free())

mem('asyncio')
import uasyncio as asyncio

# mem('bconf')
# import bconf

mem('sensors')
import sensors

mem('pwm')
import pwm

# mem('button')
# import button

import canoverlan
canoverlan.GLOBALS.brokerip = '192.168.178.5'
import can
board.CAN = can

mem('')

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

#t1 = sensors.DHT(0x30, 5, poll_intervall_in_ms=5000 if board.DEBUG else None)
temperature = sensors.DHT(0x31, 5, poll_intervall_in_ms=7000 if board.DEBUG else None)

can.init()

print('can.canoverlan._sock is {}'.format(can.canoverlan._sock))

if can.canoverlan._sock is None:
    raise RuntimeError("Cannot start CAN")


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
