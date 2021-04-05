# This file is executed on every boot (including wake-boot from deepsleep)
"""
Buero
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=unused-import

#import esp
#esp.osdebug(None)

import machine # for debugging
import sn # start network

import can
import sensors

c = can.CAN(0x100)

def callback(msg):
    print("GOT CAN message ", msg)
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")

c.subscribe(0x100, callback)

print('CAN initialized, dummy callback installed')

p = sensors.PingDevice(poll_intervall_in_ms=2500)

t1 = sensors.DHT(machine.Pin(4), 1, poll_intervall_in_ms=5000)

w = None

def watchdog():
    # pylint: disable=global-statement
    global w
    w = sensors.WDT()

sensors.polled_devices.next_poll()
