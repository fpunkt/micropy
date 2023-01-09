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
import can
import board

class IRQIO(sensors.Sensor):
    def __init__(self, portid, pinid, trigger=None, pullup=True, canid=0, debounce_ms=1):
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
        # TODO: should have been initialized by super()
        self.portid = portid
        self.pin = machine.Pin(pinid, machine.Pin.IN, pullupmode)
        self._repr = '{} #{} {}'.format(self.__class__.__name__, self.portid, self.pin)
        self.callback = None
        self.pinvalue = self.pin.value()
        self.last_irq = utime.ticks_ms()
        self.last_run_ticks = self.last_irq
        self.last_run_before_ms = 0
        self.last_value = 0
        self.pin.irq(trigger=trigger, handler=self._irq_handler)
        self.debounce_ms = debounce_ms
        self.msg = None
        if canid != 0:
            self.msg = can.makemessage(canid, 5, portid=portid)

    def sendmessage(self):
        if board.CAN is not None and self.msg is not None:
            self.msg.payload[3] = self.pinvalue
            self.msg.payload[4] = 1
            self.msg.send()

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
        self.last_run_before_ms = utime.ticks_diff(now, self.last_run_ticks)
        self.last_run_ticks = now
        self.pinvalue = pv
        if self.callback is not None:
            self.callback(self) # pylint: disable=not-callable
        return True

    def _irq_handler(self, _):
        self.last_irq = utime.ticks_ms()
