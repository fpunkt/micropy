"""
Motionsensor

Motionsensor use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import irqio
import board
import can
import canid
import canerror
import utime

class Motionsensor(irqio.IRQIO):
    def __init__(self, portid, pinid, pullup=True):
        super().__init__(portid, pinid, pullup=pullup)
        self.makemessage(canid.SENSOR_MOTION)
