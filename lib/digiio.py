"""
Digital IO
"""

import machine
import board

class DigitalOut:
    def __init__(self, portid, pinid):
        self.pin = machine.Pin(pinid, machine.Pin.OUT)
        self.pin.off()
        board.SENSORSs.register(portid, self)

    def on(self): self.pin.on()
    def off(self): self.pin.off()

    def set(self, value):
        if value:
            self.pin.on()
        else:
            self.pin.off()

