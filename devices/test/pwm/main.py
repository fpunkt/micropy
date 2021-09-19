"""
Test module for
    2 PWM connected AUX-1 4P on beta board
    1 AM2320 on AUX-2
    2 buttons on AUX-3

"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'test'
board.DEBUG = True
board.CANID = 0x100


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


p1 = pwm.PWM(1, bconf.AUX1_YELLOW)
p2 = pwm.PWM(2, bconf.AUX1_WHITE)

p = p1

b1 = button.Button(10, bconf.AUX3_WHITE)
b2 = button.Button(11, bconf.AUX3_YELLOW)

message_counter = 0

def can_callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")
        return
    msg.unknown_command()

def button_callback(button): # pylint: disable=redefined-outer-name
    if board.DEBUG:
        print('Button pressed: {}'.format(button))

b1.callback = button_callback
b1.pwm = p1
b1.autorepeat_arm_ms = 0

b2.pwm = p2

can.subscribe(can_callback)

print('CAN initialized, dummy callback installed')


dht = sensors.DHT(20, bconf.AUX2_YELLOW, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(2))

# run once to supress memory messages after startup (because gc will be triggered after initialization ...)
gc.collect()

def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
