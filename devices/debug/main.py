"""
Kueche main.py

This file is loaded after boot.py

3 buttons
8 PWM
1 temp sensor
"""

# pylint: disable=multiple-statements
#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements, no-member
# pylint: disable=wrong-import-order
# pylint: disable=unused-import

import board

board.LOCATION = 'debug'
board.DEBUG = True
board.CANID = 0x120

if board.DEBUG is True:
    # board.CANID = 0x10
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.DEBUG = True
    net.start_wlan(32)
    net.start_repl()

import gc
import bconf
import can
import machine
import sensors
import pwm
import button
import asyncio
import motionsensor

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

p0 = pwm.PWM(0, bconf.ML10_PWM_1) # Dunsthaube warm

# PINs on left side (buttons, thermometer and motionsensors)
# 13, 12, 14, 27, 26, 25, 33
b1 = button.Button(0x20, 13)
b2 = button.Button(0x21, 12)
b3 = button.Button(0x22, 14)

def _motion_callback(x):
    if board.DEBUG:
        print('Motion detected on {}'.format(x))

m1 = motionsensor.Motionsensor(0x30, 25)
m1.callback = _motion_callback

m2 = motionsensor.Motionsensor(0x31, 26)
m2.callback = _motion_callback

def cb(but):
    board.PRINTF('got event from button {}', but)

b1.callback = cb
b2.callback = cb

# pl1.toggle_mode = 1


#
# temperature = sensors.DHT(0x30, 33, poll_intervall_in_ms=5*60*1000)
temperature = sensors.DHT(0x40, 33, poll_intervall_in_ms=1*30*1000)

message_counter = 0


def can_callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    # print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")
        return
    msg.unknown_command()


can.subscribe(can_callback)

def r():
    board.restart()

if 1 == 1: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run r() to start event handler')
