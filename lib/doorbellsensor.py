"""
doorbell sensor

uses IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import irqio
import can
import canid
import canerror

class DoorbellSensor(irqio.IRQIO):
    def __init__(self, portid, pinid, pullup=True, inverted=True):
        super().__init__(portid, pinid, pullup=pullup, inverted=inverted)
        self.msg = can.makemessage(canid.SENSOR_DOORBELL_PUSHED, 5, portid=portid)
        #self.msg = can.makemessage(canid.SENSOR_MOTION, 5, portid=portid)

    # run is handled by the parent class irqio.IRQIO
    # async def run(self):
    #     self.set_changed_status(1)
    #     self.send_message()
    #     return True
