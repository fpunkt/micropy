"""
Buttons
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import gc
import machine
import board
import can
import canid
import utime
import micropython
import schedule
import uasyncio as asyncio


class Button(schedule.BackgroundJob):
    def __init__(self, sensorid, pinid):
        super().__init__()
        self.sensorid = sensorid
        self.pin = machine.Pin(pinid, machine.Pin.IN, machine.Pin.PULL_UP)
        self._callback = None
        self.event = asyncio.Event()

        self._schedule_async_runner_ref = self._schedule_async_runner
        self._run_ref = self.run_outside_irq
        self._irq_ref = self._irq_handler
        self._sev_ref = self._schedule_event
        self.msg = can.makemessage(canid.BUTTON_PRESSED, 5)
        self.msg.setsender(self.sensorid)
        self.state = False
        self.last_irq = utime.ticks_ms()
        self.last_run = self.last_irq
        self.pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=self._irq_ref)
        self.debounce_ms = 200
        self.pwm = None
        self.autorepeat_arm_ms = 1000
        self.autorepeat_speed_ms = 200
        self.autorepeat_direction = True
        self.autorepeat_state = None
        self._irq_pending = False

    def __repr__(self):
        return '<Button #{} Pin {}, state={}>'.format(self.sensorid, self.pin, self.state)

    def value(self):
        return self.pin.value()

    def set_callback(self, callback):
        self._callback = callback

    def _released(self):
        if self.autorepeat_state is None:
            # button already handled when it was pressed
            return

        if self.autorepeat_state == 'armed':
            # released before autorepeate kicks in
            self.autorepeat_state = 'idle'
            self._pressed()

    def _pressed(self):
        self.state = not self.state
        # print('{} pressed'.format(self))
        if self.pwm is not None:
            if self.state:
                self.pwm.on()
            else:
                self.pwm.off()
        if self._callback is not None:
            self._callback(self)
        if board.CAN is not None:
            self.msg.payload[3] = self.state
            self.msg.payload[4] = 1
            self.msg.send()
        # gc.collect()

    def next_autorepeat(self):
        pass

    def _run_button(self, _):
        # print('Running {} after schedule'.format(utime.ticks_diff(utime.ticks_ms(), self.last_irq)))

        #self.last_run = utime.ti

        if self.pin.value() == 1:
            self._released()
            return
        # here we have a button pressed
        if self.autorepeat_state is None:
            self._pressed()
            return

    async def run_forever(self):
        while True:
            await self.event.wait()
            print('got event for {}'.format(self))
            self._run_button(None)
            self.event.clear()
            print('event now: {}', self.event.is_set())
            await asyncio.sleep(0)


    async def _async_runner(self):
        self._run_button(None)
        self._irq_pending = False
        await asyncio.sleep(0)

    def run_outside_irq(self, _):
        asyncio.run(self._async_runner())


    def _schedule_async_runner(self, _):
        self.run_outside_irq(None)

    def _schedule_event(self, _):
        #print('irq')
        self.event.set()


    def _irq_handler(self, _):
        irq_state = machine.disable_irq()
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_irq) < self.debounce_ms:
            machine.enable_irq(irq_state)
            return
        self.last_irq = now
        self.event.set()
        machine.enable_irq(irq_state)

    def _xxxirq_handler(self, _):
        irq_state = machine.disable_irq()
        #if self._irq_pending:
        #    machine.enable_irq(irq_state)
        #    return
        #self._irq_pending = True
        # check for extreme short press (e.g. glitch, spike, ...)
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_irq) < self.debounce_ms:
            machine.enable_irq(irq_state)
            return
        self.last_irq = now
        #micropython.schedule(self._run_ref, None)
        machine.enable_irq(irq_state)
        self.run_outside_irq(None)
