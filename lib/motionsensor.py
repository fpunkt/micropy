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
        self.msg = can.makemessage(canid.SENSOR_MOTION, 5, portid=portid)

    def run(self):
        # print('id {}, ticks: {}, fc: {}'.format(self.portid, self.last_run_before_ms, self.fastcount))
        if not super().run():
            # no change
            return False
        #print('     ticks: {}, fc: {}'.format(self.last_run_before_ms, self.fastcount))
        self.sendmessage()

        #if board.CAN is not None:
        #    self.msg.payload[3] = self.pinvalue
        #    self.msg.payload[4] = 1
        #    self.msg.send()
        # self.event.clear()
        return True
