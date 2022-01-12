"""
IRQ driven IO

Use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import machine
import utime
# import micropython
# import uasyncio as asyncio
import sensors

class IRQIO(sensors.Sensor):
    def __init__(self, portid, pinid, trigger=None, pullup=True):
        super().__init__(self, portid, pinid, poll_intervall_in_ms=10)
        # typically buttons or motions sensors have very short running handlers
        self.is_fast = True
        if trigger is None:
            trigger = machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING
        elif trigger == 'rise':
            trigger = machine.Pin.IRQ_RISING
        elif trigger == 'fall':
            trigger = machine.Pin.IRQ_FALLING
        else:
            raise ValueError('trigger needs to be one of None, rise or fall, found {}'.format(trigger))
        if pullup is True:
            pullupmode = machine.Pin.PULL_UP
        else:
            pullupmode = pullup
        self.portid = portid
        self.pin = machine.Pin(pinid, machine.Pin.IN, pullupmode)
        self._repr = '{} #{} {}'.format(self.__class__.__name__, self.portid, self.pin)
        self.callback = None
        self.pinvalue = self.pin.value()
        self.last_irq = utime.ticks_ms()
        self.last_run = self.last_irq
        self.last_value = 0
        self.pin.irq(trigger=trigger, handler=self._irq_handler)
        self.debounce_ms = 1

    def run(self):
        now = utime.ticks_ms()
        # print('time since last IRQ: {} ms'.format(utime.ticks_diff(now, self.last_irq)))
        if utime.ticks_diff(now, self.last_irq) < self.debounce_ms:
            # keep on debouncing
            return False
        pv = self.pin.value()
        if pv == self.pinvalue:
            # no change
            return False
        self.pinvalue = pv
        if self.callback is not None:
            self.callback(self) # pylint: disable=not-callable
        return True

    def _irq_handler(self, _):
        self.last_irq = utime.ticks_ms()
