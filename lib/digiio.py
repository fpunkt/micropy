"""
Digital IO
"""

import machine
import board

class DigitalOut:
    def __init__(self, portid, pinid):
        self.pin = machine.Pin(pinid, machine.Pin.OUT)
        self.pin.off()
        board.PORTs.register(portid, self)

    def on(self): self.pin.on()
    def off(self): self.pin.off()

    def set(self, value):
        if value:
            self.pin.on()
        else:
            self.pin.off()

class DigitalIn:
    def __init__(self, portid, pinid) -> None:
        self.pin = machine.Pin(pinid, machine.Pin.IN)
        board.PORTs.register(portid, self)

    def read(self): self.pin.value()
    def value(self): self.pin.value()
