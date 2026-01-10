"""
Buttons

Buttons use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import board
import canid
import irqio
import utime
import asyncio
import sys

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

def find(msg):
    """Find button with ID as 2nd byte of payload"""
    return board.PORTs.find(msg, (Button, ARButton), 0xa1)


STATE_AR_IDLE = const(0)
STATE_AR_ARM = const(1)
STATE_AR_ACTIVE = const(2)

class Button(irqio.IRQIO):
    def __init__(self, portid, pinid, inverted=False, debounce_ms=20):
        # note that we swap inverted here: buttons are usually inputs pulled to low
        super().__init__(portid, pinid, inverted=0 if inverted else 1, debounce_ms=debounce_ms)
        self.makemessage(canid.BUTTON_PRESSED)
        self.pwm = None
        self.state = 0
        self._arevent = asyncio.Event()
        self._arevent.clear()
        self.callback = None
        self.all_off_mode = False
        self.update_payload() # ensure that calls to send_telemetry have a valid status

    def __repr__(self):
        return self._repr('{}, state={}'.format(self.pwm, self.state))

    async def _autorepeat_handler(self):
        while True:
            await self._arevent.wait()

    async def run(self):
        if board.DEBUG > 2:
            print('Button {} updown {} changed to {}'.format(self.portid, self.value(), self.state))

        if self.debounce_ms > 0:
            await asyncio.sleep_ms(self.debounce_ms)
            if self.pinvalue != self.value():
                if board.DEBUG > 0:
                    print("Still debouncing {}".format(self))
                return False

        if self.pinvalue == 1:
            self.pressed()
        else:
            self.released()
        return True

    def set_pwm(self, pwm):
        """Connect a PWM to this button"""
        if self.pwm is not None:
            self.pwm.set_button(None) # disconnect previous
        self.pwm = pwm
        pwm.set_button(self)

    def update_payload(self):
        self.set_changed_status(1)
        self.msg.payload[3] = self.state

    def is_on(self) -> bool:
        return self.state != 0

    def pressed(self):
        """Called when button is pushed down"""
        if board.DEBUG > 1:
            print('Botton pressed {}'.format(self))
        self.toggle()

    def released(self):
        if board.DEBUG > 1:
            print('Botton released {}'.format(self))

    def toggle(self) -> bool:
        """Press button, toggle state. If a PWM is connected the state will be determined from the PWM"""
        if board.DEBUG:
            print('Botton toggle {}'.format(self))
        if self.pwm is None:
            self.state = 1-self.state
        elif self.pwm.toggle():
            self.state = 1
        else:
            self.state = 0
        self.update_payload_and_send_message()
        if board.DEBUG:
            print('{} new state after toggle is {}'.format(self, self.state))
        if self.callback is not None:
            self.callback(self)
        board.MQTT.publish('state/{}'.format(self.portid), self.state)
        return self.state != 0

    def on(self):
        """Press button, afterwards state is on"""
        self.state = 0
        self.pressed()

    def off(self):
        """Press button, afterwards state is off"""
        self.state = 1
        self.pressed()


class ARButton(Button):
    """Button with auto-repeat"""
    def __init__(self, portid, pinid, inverted=False):
        # note that we swap inverted here: buttons are usually inputs pulled to low
        super().__init__(portid, pinid, inverted)

        self.debounce_ms = 20
        self.pwm = None
        self.state = 0
        self._arevent = asyncio.Event()
        self._arevent.clear()
        self.autorepeat_last_action_timestamp = utime.ticks_ms()
        self.autorepeat_arm_ms = 1000
        self.autorepeat_speed_ms = 5
        self.autorepeat_speed_ms = -1
        self.autorepeat_direction = False
        self.autorepeat_state = STATE_AR_IDLE
        self.callback = None

    async def run(self):
        if self.autorepeat_speed_ms <= 0:
            # autorepeat disabled
            return await super().run()

        return False
        # autorepeat mode

        if changed:
            if board.DEBUG:
                print('button {} changed {}'.format(self.portid, self.pinvalue))
            if self.pinvalue == 1:
                # button released
                if self.pwm is not None:
                    self.pwm.enable_dimming()
                return self._pressed()
            # button pressed
            self.autorepeat_last_action_timestamp = utime.ticks_ms()
            return True

        # button did not change, handle autorepeat

        if self.pinvalue == 1:
            # button not pressed
            return False

        now = utime.ticks_ms()
        ms_since_last_update = utime.ticks_diff(now, self.autorepeat_last_action_timestamp)
        if self.autorepeat_state == STATE_AR_IDLE:
            if ms_since_last_update > self.autorepeat_arm_ms:
                self.autorepeat_last_action_timestamp = now
                self.autorepeat_state = STATE_AR_ACTIVE
                # return True
            else:
                return False

        if self.pwm is None:
            return False

        # autorepeat is active, do next step
        self.pwm.disable_dimming()
        ival = self.pwm.current_value()

        # step = max(1, (ival * ival) // 500)
        # step = max(1, ival // 100)
        # step *= step
        step = max(1, ival // 50)
        step += ival // 100
        if ival == 0:
            # always dim up when light is off
            self.autorepeat_direction = True
        if not self.autorepeat_direction:
            step = -step
        # ival = self.pwm.pwm.duty()
        newval = ival + step
        newval = min(1023, max(1, newval))
        # print('dim to {}, iv={}, step={}'.format(newval, ival, step))
        self.pwm.seti_no_can_message(newval)
        self.autorepeat_last_action_timestamp = now
        return True