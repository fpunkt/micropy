"""Relais with Opto-couplers"""


# pylint: disable=import-error, missing-docstring

import machine

class Relais:
    """Relais"""
    def __init__(self, portid, pin):
        self.p = machine.Pin(pin, machine.Pin.OUT)
        self.off()

    def on(self):
        self.p.off()
    def off(self):
        self.p.on()
