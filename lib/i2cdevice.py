"""
Provide a global I2C device
"""

import machine
import board

def init(sda=None, scl=None):
    if board.I2C is not None:
        raise RuntimeError("I2C is defined multiple times")
    if sda is None or scl is None:
        raise ValueError("You must provide sda and scl")
    board.I2C = machine.SoftI2C(sda=machine.Pin(sda), scl=machine.Pin(scl))
    board.I2C_SDA_PIN = sda
    return board.I2C

class I2CDevice():
    def __init__(self, address):
        self.address = address

    # provide exit/enter to allow with xxx as yyy syntax
    def __exit__(self):
        pass

    def __enter__(self):
        pass

    def write(self, whatever):
        board.I2C.writeto(self.address, whatever)

    def readinto(self, buffer):
        board.I2C.readinto(buffer)