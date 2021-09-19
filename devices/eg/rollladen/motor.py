# pylint: disable=import-error, missing-docstring


import pwm
import utime

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x


STOPPED = const(0)
MOVING_LEFT = const(1)
MOVING_RIGHT = const(2)
ACCELLERATING = const(3)

LEFT = const(1)
RIGHT = const(2)

DEFAULT_ACCELLERATION_DELAY_MS = 2
DEFAULT_ACCELLERATION_INCREMENT = 10
DEFAULT_STOP_INCREMENT = 50

class Motor:
    def __init__(self, pid, pin1, pin2) -> None:
        self.currentspeed = 0
        self.status = 0
        self.m1 = pwm.PWM(pid, pin1)
        self.m2 = pwm.PWM(pid+1, pin2)
        self.motor = None
        self.fullstop()
        self.set_freq(10000)

    def fullstop(self) -> None:
        self.m1.seti_no_can_message(0)
        self.m2.seti_no_can_message(0)
        self.status = STOPPED
        self.motor = None
        self.currentspeed = 0
        self.m1.wait_until_set()
        self.m2.wait_until_set()

    def set_freq(self, f):
        self.m1.pwm.freq(f)
        self.m2.pwm.freq(f)

    def getmotor(self, direction):
        if direction == LEFT:
            return self.m1
        return self.m2

    def _set(self, speed) -> None:
        # print("{:4d} {}".format(speed, self.motor))
        self.currentspeed = speed
        self.motor.seti_no_can_message(self.currentspeed)

    def _change(self, tospeed, steps, delay_ms=DEFAULT_ACCELLERATION_DELAY_MS) -> None:
        ds = int((tospeed - self.currentspeed) / steps)
        # print("to={:4d}, steps={:4d}, stepsize={:4d} {}".format(tospeed, steps, ds, self.motor))
        while steps > 1:
            self._set(self.currentspeed + ds)
            steps -= 1
            utime.sleep_ms(delay_ms)
        self._set(tospeed)
        # make sure we are there
        self.motor.wait_until_set()
        if tospeed == 0:
            self.status = STOPPED
            self.motor = None

    def change(self, tospeed):
        steps = max(1, abs(int((tospeed - self.currentspeed) / DEFAULT_ACCELLERATION_INCREMENT)))
        self._change(tospeed, steps)

    def stop(self) -> None:
        if self.status != STOPPED:
            steps = max(1, abs(int(self.currentspeed / DEFAULT_STOP_INCREMENT)))
            self._change(0, steps)
        self.fullstop()

    def setspeedanddirection(self, direction, speed=True) -> None:
        if speed is True:
            speed = 0xffff
        if speed > 1023:
            speed = 1023
        m = self.getmotor(direction)
        if m != self.motor:
            self.stop()
        self.motor = m
        if direction == LEFT:
            self.status = MOVING_LEFT
        else:
            self.status = MOVING_RIGHT
        self.change(speed)

    def speed(self, s):
        if s == 0:
            self.change(0) # a softer stop if we change direction
        elif s > 0:
            self.setspeedanddirection(LEFT, s)
        else:
            self.setspeedanddirection(RIGHT, -s)
