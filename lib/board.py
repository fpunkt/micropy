"""
Basic Hardware available to all boards
"""

# pylint: disable=import-error

import machine

class Led:
    """On/Off LED"""
    def __init__(self, pin):
        self.led = machine.Pin(pin, mode=machine.Pin.OUT)
    def on(self):
        """turn LED on"""
        self.led.value(1)
    def off(self):
        """turn LED off"""
        self.led.value(0)


LED = Led(2)
"""LED on the PCB"""

# Global CAN device. Use board.CAN to access the CAN bus from everywhere.
# The actual value is set when can.py is loaded/initialized
# (we need this here to avoid circular dependencies in cancommon.py / can.py)
CAN = None
