"""
IRQ driven IO

Use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import port
import machine
import utime
import sensors
import can
import canerror
import board
import uasyncio as asyncio
import sys

class IRQIO(port.Port):
    def __init__(self, portid, pinid, trigger=None, pullup=True, debounce_ms=0, inverted=False):
        # initialize this first so we get error messages during initialization
        # self._repr = '{} #{} {}'.format(self.__class__.__name__, portid, pinid)
        pullupmode = machine.Pin.PULL_UP if pullup is True else pullup
        super().__init__(portid, machine.Pin(pinid, machine.Pin.IN, pullupmode))

        # typically buttons or motions sensors have very short running handlers
        if trigger is None:
            trigger = machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING
        elif trigger == 'rise':
            trigger = machine.Pin.IRQ_RISING
        elif trigger == 'fall':
            trigger = machine.Pin.IRQ_FALLING
        else:
            raise ValueError('trigger needs to be one of None, rise or fall, found {}'.format(trigger))
        self.trigger = trigger

        self.inverted = inverted
        self.debounce_ms = debounce_ms
        self.last_irq = utime.ticks_ms()
        self.last_run_before_ms = 0
        self.is_disabled = False
        self.triggerevent = asyncio.Event()
        self.pinvalue = self.value()
        self.enable()
        board.BACKGROUND_RUNNERS.append(self._runner())

    def value(self):
        """Return pin value (respecting the value of self.inverted)"""
        if self.inverted:
            return 1-self.pin.value()
        return self.pin.value()

    def disable(self):
        """Disable events from this input"""
        self.is_disabled = True
        self.pin.irq(trigger=None, handler=None)
        self.send_disabled_error()

    def enable(self):
        """Enable events from this input"""
        self.is_disabled = False
        self.pin.irq(trigger=self.trigger, handler=self._irq_handler)

    def _sendmessage(self, changed):
        if board.CAN is not None and self.msg is not None:
            self.msg.payload[3] = self.pinvalue
            self.msg.payload[4] = changed
            self.msg.send()

    def send_disabled_error(self):
        print('Disabled: {}'.format(self))
        can.cancommon.errormessage([canerror.SENSOR_DISABLED, self.portid])

    def sendmessage(self):
        """Called when status has changed"""
        self._sendmessage(1)

    def statusmessage(self):
        """Regularily report status with changed flag cleared"""
        self._sendmessage(0)

    async def run(self):
        """Overload this by your function"""
        print('calling IRQIO.run for port {:02x}, you should overload this'.format(self.portid))

    async def _runner(self):
        while True:
            await self.triggerevent.wait()
            if self.is_disabled:
                print('port {:02c} is disabled but still receiving events'.format(self.portid))
                await asyncio.sleep_ms(50)
                self.triggerevent.clear()
                continue

            # some basic debounding is already done by the scheduler
            now = utime.ticks_ms()
            self.last_run_before_ms = utime.ticks_diff(now, self.last_irq)
            self.last_irq = now

            if board.DEBUG > 1:
                print('IRQ triggered for {:02x} (now: {}, prev: {})'.format(self.portid, self.last_run_before_ms, utime.ticks_ms(), self.last_irq))
            try:
                self.triggerevent.clear()
                self.pinvalue = self.value()
                await self.run()
            except Exception as e:
                print('Raised error in irqio.run(), disabling: {}'.format(e))
                sys.print_exception(e)
                self.send_disabled_error()
                await asyncio.sleep(10)

    def _irq_handler(self, _):
        self.triggerevent.set()

