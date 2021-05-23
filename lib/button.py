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
import schedule



class Button:
    def __init__(self, sensorid, pinid):
        self.sensorid = sensorid
        self.pin = machine.Pin(pinid, machine.Pin.IN, machine.Pin.PULL_UP)
        self._callback = None
        self._run_ref = self.run_outside_irq
        self._irq_ref = self._irq_handler
        self.msg = can.makemessage(canid.BUTTON_PRESSED, 5)
        self.msg.setsender(self.sensorid)
        self.state = False
        self.lastcall = utime.ticks_ms()
        self.pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=self._irq_ref)
        self.debounce_ms = 200
        self.pwm = None
        self.autorepeat_arm_ms = 1000
        self.autorepeat_speed_ms = 200
        self.autorepeat_direction = True
        self.autorepeat_state = None

    def __repr__(self):
        return '<Button #{} Pin {}, state={}>'.format(self.sensorid, self.pin, self.state)

    def value(self):
        return self.pin.value()

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
        gc.collect()

    def next_autorepeat(self):
        pass

    def run_outside_irq(self, _):
        if self.pin.value() == 1:
            self._released()
            return
        # here we have a button pressed
        if self.autorepeat_state is None:
            self._pressed()
            return


    def set_callback(self, callback):
        self._callback = callback

    def _irq_handler(self, _):
        # check for extreme short press (e.g. glitch, spike, ...)
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.lastcall) < self.debounce_ms:
            return
        irq_state = machine.disable_irq()
        schedule.outside_irq.run_outside_irq_disable_irq_around_me(self._run_ref)
        machine.enable_irq(irq_state)

        self.lastcall = now
