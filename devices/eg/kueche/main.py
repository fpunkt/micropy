"""
Kueche main.py

This file is loaded after boot.py

3 buttons
7 PWM
1 temp sensor
"""

# pylint: disable=multiple-statements
#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)
import net; net.start_wlan(); net.start_repl()

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements, no-member
# pylint: disable=wrong-import-order
# pylint: disable=unused-import

import can
can.CAN(0x200)


import gc
import pwm
import sensors
# import utime
import memstat
import board
import button

#
p1 = pwm.PWM(0, 4)
p2 = pwm.PWM(1, 16)
b1 = button.Button(10, 13)
b2 = button.Button(11, 12)

b1.pwm = p1
b2.pwm = p2

p1.lastintensity = 100
p2.lastintensity = 15
#
temperature = sensors.DHT(16, 27, poll_intervall_in_ms=5000)

wd = sensors.WDT()

sensors.proclaim()

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

# board.CAN.subscribe(True, callback)

def dd(a1, a2):
    p1.dimi(a1)
    p2.dimi(a2)

def d1(): dd(0, 1000)
def d2(): dd(1000, 0)

running = True
delay_ms = 100
def ddloop():
    while running:
        m1 = gc.mem_free()
        d1()
        pwm.dimlist.wait()
        d2()
        pwm.dimlist.wait()
        m2 = gc.mem_free()
        print('Mem Used: {}'.format(m1-m2))
