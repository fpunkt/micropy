"""
Lightswitch Overwrite

Motionsensor use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import irqio
import can
import canid
import canerror

class LightswitchOverwrite(irqio.IRQIO):
    def __init__(self, portid, pinid, pullup=True):
        super().__init__(portid, pinid, pullup=pullup, canid=canid.SENSOR_LIGHTSWITCH_OVERRIDE)
        #self.msg = can.makemessage(canid.SENSOR_MOTION, 5, portid=portid)
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

        if self.last_run_ticks < 50:
            # comming fast ..
            if self.fastcount > 10:
                # events are comming too fast
                self.disable()
                return False
            self.fastcount += 1
            return False

        self.fastcount = 0
        self.sendmessage()

        return True
