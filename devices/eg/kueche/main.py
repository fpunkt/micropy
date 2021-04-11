"""
Kueche main.py

This file is loaded after boot.py

3 buttons
7 PWM
1 temp sensor
"""

import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements

import can
can.CAN(0x200)

import pwm
import sensors
#
p1 = pwm.PWM(4, 0)
p2 = pwm.PWM(16, 1)
#
temperature = sensors.DHT(27, 16, poll_intervall_in_ms=5000)

sensors.start()

def dd(a, b):
    p1.dim(a)
    p2.dim(b)

def d1(): dd(0, 1)
def d2(): dd(1, 0)
