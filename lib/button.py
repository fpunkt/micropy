"""
Buttons

Buttons use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import machine
import board
import can
import canid
import utime
# import micropython
import uasyncio as asyncio
import schedule

class Button:
    def __init__(self, sensorid, pinid):
        self.sensorid = sensorid
        self.pin = machine.Pin(pinid, machine.Pin.IN, machine.Pin.PULL_UP)
        self.callback = None
        self.msg = can.makemessage(canid.BUTTON_PRESSED, 5)
        self.msg.setsender(self.sensorid)
        self.state = False
        self.last_irq = utime.ticks_ms()
        self.last_run = self.last_irq
        self.last_value = 0
        self.pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=self._irq_handler)
        self.debounce_ms = 200
        self.pwm = None
        self.autorepeat_arm_ms = 1000
        self.autorepeat_speed_ms = 200
        self.autorepeat_direction = True
        self.autorepeat_state = None
        self._irq_pending = False
        self.event = asyncio.Event()
        schedule.add_poller(self.poll)

    def __repr__(self):
        return '<Button #{} {}, {}, state={}>'.format(self.sensorid, self.pin, self.pwm, self.state)

    def poll(self):
        if not self.event.is_set():
            return False
        if self.pin.value() == 1:
            self._released()
        else:
            self._pressed()
        self.event.clear()
        return True

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
        #print('{} pressed'.format(self))
        if self.pwm is not None:
            #print('running toggle')
            self.state = self.pwm.toggle()
            print('running toggle done, new state {}'.format(self.state))
        if self.callback is not None:
            # pylint: disable=not-callable
            self.callback(self)
        if board.CAN is not None:
            self.msg.payload[3] = self.state
            self.msg.payload[4] = 1
            self.msg.send()
        # gc.collect()

    def next_autorepeat(self):
        pass

    def _irq_handler(self, _):
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_irq) < self.debounce_ms:
            return
        self.last_irq = now
        self.event.set()
