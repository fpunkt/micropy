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
        # store the current value in pinvalue to ensure a consistant behaviour while callbacks
        # are running (might be confusing if value changes ...)
        self.pinvalue = self.value()
        self.enable()
        board.BACKGROUND_RUNNERS.append(self._runner())

    def makemessage(self, canid):
        """Create CAN message for use and store in self.msg"""
        self.msg = can.makemessage(canid, 5, portid=self.portid)

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

    def set_changed_status(self, status):
        self.msg.payload[4] = 1 if status else 0

    def update_telemetry(self):
        self.set_changed_status(0)

    def update_payload(self):
        self.set_changed_status(1)
        self.msg.payload[3] = self.pinvalue

    async def run(self):
        """This function is run when an interrupt is received. It returns true if something has been
        done, False when the event is ignored for whatever reason.
        You might want to overload this by your for your sensor"""
        if board.DEBUG > 0:
            print('{} got interrupt {}/{}'.format(self, self.pinvalue, self.value()))
        self.update_payload()
        self.send_message()

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
                if board.DEBUG:
                    print('Raised error in irqio.run(), disabling: {}'.format(e))
                self.send_exception_during_run_error(e)
                await asyncio.sleep(10)

    def _irq_handler(self, _):
        self.triggerevent.set()

