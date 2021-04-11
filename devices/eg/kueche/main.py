"""
Kueche main.py

This file is loaded after boot.py

3 buttons
7 PWM
1 temp sensor
"""

# pylint: disable=multiple-statements
import time; print('Loading main, giving time to abort ....'); time.sleep(2)

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

#
p1 = pwm.PWM(4, 0)
p2 = pwm.PWM(16, 1)
#
temperature = sensors.DHT(27, 16, poll_intervall_in_ms=5000)

sensors.start()

def dd(a, b):
    p1.idim(a)
    p2.idim(b)

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
