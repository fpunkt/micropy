"""
Main Module.

Function main is executed after standard inits
"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=unused-import, multiple-statements

# start CAN first, otherwise bus is in undefined state

import time; print('Loading main, giving time to abort ....'); time.sleep(2)

import can
c = can.CAN(0x100)

import machine
import bmp085

i2c = machine.I2C(0, sda=machine.Pin(21), scl=machine.Pin(22))
bmp = bmp085.BMP180(i2c)
bmp.oversample = 2
bmp.sealevel = 101325

temp = bmp.temperature
p = bmp.pressure
altitude = bmp.altitude
print(temp, p, altitude)
