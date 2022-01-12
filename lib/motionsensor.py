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

class Motionsensor(irqio.IRQIO):
    def __init__(self, portid, pinid, pullup=None):
        super().__init__(portid, pinid, pullup=pullup)
        self.msg = can.makemessage(canid.SENSOR_MOTION, 5, portid=portid)

    def __repr__(self):
        return '<{}>'.format(self._repr)

    def run(self):
        if not super().run():
            # no change
            return False
        if board.CAN is not None:
            self.msg.payload[3] = self.pinvalue
            self.msg.payload[4] = 1
            self.msg.send()
        # self.event.clear()
        return True
