"""
Lightswitch Overwrite

Uses IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import irqio
import can
import canid
import canerror

class LightswitchOverwrite(irqio.IRQIO):
    def __init__(self, portid, pinid, pullup=True, inverted=True):
        super().__init__(portid, pinid, pullup=pullup, canid=canid.SENSOR_LIGHTSWITCH_OVERRIDE, inverted=inverted)
        #self.msg = can.makemessage(canid.SENSOR_MOTION, 5, portid=portid)

    def run(self):
        if not super().run():
            # no change
            return False

        self.sendmessage()

        return True
