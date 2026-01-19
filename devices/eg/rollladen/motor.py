# pylint: disable=import-error, missing-docstring


import pwm
import board
import asyncio
import machine


if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x


STOPPED = const(0)
MOVING_LEFT = const(1)
MOVING_RIGHT = const(2)
ACCELLERATING = const(3)

LEFT = const(1)
RIGHT = const(2)

_motors = []

class Motor:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, pid, pin1, pin2, sensorpin) -> None:
        self.currentspeed = 0
        self.targetspeed = 0
        self.position = 0
        self.status = 0
        self.m1 = pwm.PWM(pid, pin1)
        self.m2 = pwm.PWM(pid+1, pin2)
        self.m1.disable_dimming()
        self.m2.disable_dimming()
        # motor will be one of m1 or m2, depending the direction. That is then the output
        # where the PWM will change the speed (the other one is pulled low)
        self.motor = None
        self.fullstop()
        self.set_freq(10000)

        self._sensorpin = None
        self.sensorcount = 0

        if sensorpin is not None:
            self._sensorpin = machine.Pin(sensorpin, machine.Pin.IN, machine.Pin.PULL_UP)
            self._sensorpin.irq(trigger=machine.Pin.IRQ_RISING, handler=self._sensor_irq_handler)

        _motors.append(self)

    def _sensor_irq_handler(self, _):
        # note: in practice this always remains a short integer number so we don't have to do
        # special casting here
        self.sensorcount += 1

    def fullstop(self) -> None:
        self.m1.off_no_telemetry()
        self.m2.off_no_telemetry()
        self.status = STOPPED
        self.motor = None
        self.currentspeed = 0
        self.targetspeed = 0
        self.m1.wait_until_set(0)
        self.m2.wait_until_set(0)

    def set_freq(self, f):
        self.m1.pwm.freq(f)
        self.m2.pwm.freq(f)

    def getmotor(self, direction):
        if direction == LEFT:
            return self.m1
        return self.m2

    def setspeed(self, speed) -> None:
        """Set speed of current motor immediately. Motor must already be set (choose direction) """
        self.currentspeed = speed
        self.motor.set_raw_no_telemetry(speed)
        if speed == 0:
            self.fullstop()

    def next_speedup_step_or_monitor(self) -> None:
        """Helper function for smooth accelleration. Called in the background every x millisecond"""
        if not self.motor:
            return
        ds = self.targetspeed - self.currentspeed
        if ds == 0:
            # moving a target speed. Monitor motionsensor
            return
        minstep = max(1, self.currentspeed // 10)
        if ds > 0:
            diff = min(ds, minstep)
        else:
            diff = -min(-ds, minstep)
        # print('ds={:6d} min={:4d} tar={:4d} cur={:4d} diff={:4d}'.format(
        #     ds, minstep, self.targetspeed, self.currentspeed, diff))
        self.setspeed(self.currentspeed + diff)

    def smooth_change_speed(self, tospeed):
        """Change speed of motor (but keep direction). Speed is smoothly updated in the background"""
        self.targetspeed = tospeed

    def stop(self) -> None:
        if self.status != STOPPED:
            self.setspeed(0)

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
        self.smooth_change_speed(speed)

    def speed(self, s):
        if s == 0:
            self.smooth_change_speed(0) # a softer stop if we change direction
        elif s > 0:
            self.setspeedanddirection(LEFT, s)
        else:
            self.setspeedanddirection(RIGHT, -s)

async def _motor_accellerator():
    while True:
        for m in _motors:
            m.next_speedup_step_or_monitor()
        await asyncio.sleep_ms(10)

board.BACKGROUND_RUNNERS.append(_motor_accellerator())
