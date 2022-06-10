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
    def __init__(self, portid, pinid, pullup=None):
        super().__init__(portid, pinid, pullup=pullup)
        self.msg = can.makemessage(canid.SENSOR_MOTION, 5, portid=portid)
        self.last_run = utime.ticks_ms()
        self.fastcount = 0

    def __repr__(self):
        return '<{}>'.format(self._repr)

    def disable(self):
        self.fastcount = -1
        self.poll_intervall_in_ms = 1000
        can.cancommon.errormessage([canerror.SENSOR_DISABLED, self.portid])

    def enable(self):
        self.fastcount = 0
        self.poll_intervall_in_ms = 10


    def run(self):
        if self.fastcount < 0:
            return  # disabled
        if not super().run():
            # no change
            return False

        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_run) < 50:
            # comming fast ..
            if self.fastcount > 10:
                # events are comming too fast
                self.disable()
                return False
            self.fastcount += 1
            self.last_run = now
            return False

        self.last_run = now
        self.fastcount = 0

        if board.CAN is not None:
            self.msg.payload[3] = self.pinvalue
            self.msg.payload[4] = 1
            self.msg.send()
        # self.event.clear()
        return True
