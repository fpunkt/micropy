"""
Buttons

Buttons use IRQ for debouncing and async polling for event processing.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods, too-many-instance-attributes

import board
import can
import canid
import irqio
import utime
import uasyncio as asyncio

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

STATE_AR_IDLE = const(0)
STATE_AR_ARM = const(1)
STATE_AR_ACTIVE = const(2)

class Button(irqio.IRQIO):
    def __init__(self, portid, pinid, inverted=False):
        # note that we swap inverted here: buttons are usually inputs pulled to low
        super().__init__(portid, pinid, inverted=0 if inverted else 1)
        self.msg = can.makemessage(canid.BUTTON_PRESSED, 5, portid=self.portid)

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

    def __repr__(self):
        return '<{}, {}, state={}>'.format(self._repr, self.pwm, self.state)

    async def _autorepeat_handler(self):
        while True:
            await self._arevent.wait()

    async def run(self):
        # pylint: disable=too-many-return-statements

        if board.DEBUG > 0:
            print('Button {} updown {} changed to {}'.format(self.portid, self.value(), self.state))

        if self.debounce_ms > 0:
            await asyncio.sleep_ms(self.debounce_ms)
            if self.pinvalue != self.value():
                if board.DEBUG > 0:
                    print("Still debouncing {}".format(self))
                return

        if self.autorepeat_speed_ms < 0:
            # autorepeat is disabled
            if self.pinvalue == 1:
                self._pressed()

        if self.pinvalue == 1:
            self.pressed()
        else:
            self.released()
        return


        if self.autorepeat_arm_ms == 0:
            # autorepeat disabled, directly react on button down, don't wait for button up
            if not changed:
                return False
            if self.pinvalue == 1:
                # button released, nothing to do
                return True

            return self._pressed()

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

    def toggle_state(self):
        self.state = 1-self.state

    def pressed(self):
        """Called when a button is pressed (after de-bouncing, handlig auto-repeat, etc)"""
        self.toggle_state()
        print('Botton pressed {}'.format(self))
        self.sendmessage()
        if self.pwm is not None:
            self.pwm.toggle()

    def released(self):
        if board.DEBUG:
            print('Botton released {}'.format(self))


    def _pressed(self):
        self.state = 1 - self.state
        if self.pwm is not None:
            if self.autorepeat_state == STATE_AR_ACTIVE:
                # finished autorepeat
                self.autorepeat_direction = not self.autorepeat_direction
                # send to CAN and update save
                # self.pwm.enable_dimming()
                self.pwm.seti(self.pwm.current_value())
            else:
                self.pwm.toggle()
            self.state = 0 if self.pwm.dimtovalue == 0 else 1
            # print('btn state {}, iv={}'.format(self.state, self.pwm.current_value()))
            self.autorepeat_state = STATE_AR_IDLE

        if self.callback is not None:
            self.callback(self) # pylint: disable=not-callable

        if board.CAN is not None:
            self.msg.payload[3] = self.state
            self.msg.payload[4] = 1
            self.msg.send()

        return True
