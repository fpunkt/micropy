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

class Button(irqio.IRQIO):
    def __init__(self, sensorid, pinid):
        super().__init__(sensorid, pinid)
        self.msg = can.makemessage(canid.BUTTON_PRESSED, 5, sensorid=self.sensorid)
        self.debounce_ms = 200
        self.pwm = None
        self.autorepeat_arm_ms = 1000
        self.autorepeat_speed_ms = 200
        self.autorepeat_direction = True
        self.autorepeat_state = None

    def __repr__(self):
        return '<{}, {}, state={}>'.format(self._repr, self.pwm, self.state)

    def poll(self):
        if not super().poll():
            return False
        if self.state == 1:
            self._released()
        else:
            self._pressed()
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
            #print('running toggle done, new state {}'.format(self.state))
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
