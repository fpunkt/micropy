"""
IRQ driven IO

Use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import machine
import utime
# import micropython
import uasyncio as asyncio
import schedule

class IRQIO:
    def __init__(self, sensorid, pinid, trigger=None, pullup=True):
        if trigger is None:
            trigger = machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING
        if pullup is True:
            pullupmode = machine.Pin.PULL_UP
        else:
            pullupmode = pullup
        self.sensorid = sensorid
        self.pin = machine.Pin(pinid, machine.Pin.IN, pullupmode)
        self._repr = '{} #{} {}'.format(self.__class__.__name__, self.sensorid, self.pin)
        self.callback = None
        self.state = 0
        self.last_irq = utime.ticks_ms()
        self.last_run = self.last_irq
        self.last_value = 0
        self.pin.irq(trigger=trigger, handler=self._irq_handler)
        self.debounce_ms = 1
        self.event = asyncio.Event()
        schedule.add_poller(self.poll)

    def __repr__(self):
        return '<{}>'.format(self._repr)

    def poll(self):
        if not self.event.is_set():
            return False
        self.state = self.pin.value()
        self.event.clear()
        if self.callback is not None:
            # pylint: disable=not-callable
            self.callback(self)
        return True

    def _irq_handler(self, _):
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_irq) < self.debounce_ms:
            return
        self.last_irq = now
        self.event.set()
