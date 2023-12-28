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
import uasyncio as asyncio
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
    def __init__(self, portid, pinid, inverted=False):
        # note that we swap inverted here: buttons are usually inputs pulled to low
        super().__init__(portid, pinid, inverted=0 if inverted else 1)
        self._makemessage(canid.BUTTON_PRESSED)
        self.pwm = None
        self.state = 0
        self._arevent = asyncio.Event()
        self._arevent.clear()
        self.callback = None
        self.update_payload() # ensure that calls to send_telemetry have a valid status

    def __repr__(self):
        return self._repr('{}, state={}'.format(self.pwm, self.state))

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
                return False

        if self.pinvalue == 1:
            self.pressed()
        else:
            self.released()
        return True

    def send_telemetry(self):
        self.set_changed_status(0)

    def update_payload(self):
        self.set_changed_status(1)
        self.msg.payload[3] = self.state

    def is_on(self):
        return self.state != 0

    def is_off(self):
        return self.state == 0

    def toggle_state(self):
        """Toggle button status, update connected PWM, send status to CAN"""
        self.set_state(1-self.state)

    def set_state(self, on_or_off):
        """Set button status, update connected PWM, send status to CAN"""
        self.state = 1 if on_or_off else 0
        if self.callback:
            try:
                self.callback(self)
            except Exception as e:
                print('{} callback raised error'.format(self))
                sys.print_exception(e)
                # don't update CAN message and PWM stuff
                # You could use this as behaviour of some special button action:
                #  simply raise an error if you want to stop the normal button handling
                return
        self.update_payload_and_send_message()
        if self.pwm is not None:
            if self.is_on():
                self.pwm.on()
            else:
                self.pwm.off()

    def pressed(self):
        """Called when button is pushed down"""
        if board.DEBUG:
            print('Botton pressed {}'.format(self))
        self.toggle_state()

    def released(self):
        if board.DEBUG:
            print('Botton released {}'.format(self))


class ARButton(Button):
    """Button with auto-repeat"""
    def __init__(self, portid, pinid, inverted=False):
        # note that we swap inverted here: buttons are usually inputs pulled to low
        super().__init__(portid, pinid, inverted=0 if inverted else 1)
        self._makemessage(canid.BUTTON_PRESSED)

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