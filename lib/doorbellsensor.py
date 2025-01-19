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
import time

class DoorbellSensor(irqio.IRQIO):
    def __init__(self, portid, pinid, pullup=True, inverted=True):
        super().__init__(portid, pinid, pullup=pullup, inverted=inverted)
        self.msg = can.makemessage(canid.SENSOR_DOORBELL_PUSHED, 5, portid=portid)
        self.last_run_at = 0
        self.set_changed_status(0)


    async def run(self):
        # be nice, don't flood messages
        t = time.time()
        print('DoorbellSensor.run() lrb = {}, diff={}'.format(self.last_run_before_ms, t - self.last_run_at))
        if t - self.last_run_at <= 2:
            return False
        self.last_run_at = t
        self.update_payload()
        self.send_message()
        print('DoorbellSensor.run() sent message {}'.format(self.msg))
        self.set_changed_status(0)
        return True

