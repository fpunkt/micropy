# This file is executed on every boot (including wake-boot from deepsleep)
"""
Buero

webrepl_cli.py -p x can.py 192.168.179.12:

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=unused-import, multiple-statements

#import esp
#esp.osdebug(None)

import time; print('Giving time to abort ....'); time.sleep(2)

# start CAN first, otherwise bus is in
import can
#c = can.CAN(0x100)

import machine # for debugging

import sensors

import sn


message_counter = 0

def callback(msg):
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

c.subscribe(True, callback)

print('CAN initialized, dummy callback installed')

p = sensors.PingDevice(poll_intervall_in_ms=2500)
t1 = sensors.DHT(machine.Pin(4), 1, poll_intervall_in_ms=5000)

w = None

def s(id=0x111):
    can.CANDevice.send(id, [1, 2, 3])

def watchdog():
    # pylint: disable=global-statement
    global w
    w = sensors.WDT()

sensors.polled_devices.next_poll()
