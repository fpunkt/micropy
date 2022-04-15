"""
pwm.py

Uses Timer(1) for dimming.

All general purpose input output pins can be used to generate PWM except digital input
pins from GPIO pins 34-39. Because these pins cannot be used as digital output pins.
PWM signals are digital output signals. The maximum frequency of these PWM pins is 80 MHz.

Functions are

  seti()

Use like

p = pwm.PWM(1, 14)

p

"""

# pylint: disable=import-error, missing-docstring
# pylint: disable=too-many-instance-attributes, global-statement

import machine
import utime
import uasyncio as asyncio
import board
import can
import canid
import pwmcode


dimdelay_ms = 25
dimdelay_ms = 10

# PWM freq defines the overall frequency of the device in Hz.
# 100 Hz is a good no-flicker number, but dimming is not as smooth as it could be
# the PWM needs some time to settle (change only at end of cycle?), higher frequency allows
# for higher change rates when setting the PWM, e.g. smoother dimming.
# 200 Hz has nicer dimming.
# pwm_freq = 100
pwm_freq = 200

def i16_to_raw(v):
    vv = v >> 6
    if vv == 0 and v > 0:
        return 1
    return vv

def valid(i): return min(1023, max(i, 0))

class PWM:
    """TODO: fix docstring? Wrapper for system PWM, using numbers from 0..1 and provide dimming"""
    def __init__(self, pwmid, pin):
        self.id = pwmid
        self.ival = 0
        self.lastintensity = 100
        self.pwm = None
        if pin is not None:
            self.pwm = machine.PWM(machine.Pin(pin), duty=0, freq=pwm_freq)
        board.SENSORSs.register(pwmid, self)
        if board.PWMs is not None:
            # is still None for ALL pwm list
            board.PWMs.append(self)
        if pin is None:
            return

        # global pwm_freq
#        if pwm_freq > 0:
#            self.pwm.freq(pwm_freq)
#            # pwm_freq = 0
#            utime.sleep_ms(5) # for some strange reason after setting pwm_freq ..
        # print('setting duty for {}/{} to 0'.format(pwmid, pin))
        # self.pwm.duty(0)
        self.seti_no_can_message(0) # power off
        self.dimtovalue = 0
        # self.button = None

        # allocate message once to avoid garbage collection
        self.msg = can.Message(canid.PWM_VALUE, [0, 0, 0, 0, 0, 0, 0])
        self.msg.setsender(self.id)

    def __repr__(self):
        return '<PWM {}.{}>'.format(self.id, self.pwm)

    def disable_dimming(self):
        self.dimtovalue = -99

    def enable_dimming(self):
        self.dimtovalue = self.ival

    # def poll(self):
    #     if self.dimtovalue < 0:
    #         return False
    #     if self.ival == self.dimtovalue:
    #         return False
    #     return self.run_next_dimstep()

    def seti_no_can_message(self, ival):
        """Set PWM value. NOTE: the actual value may not be the one that has been commanded.
        Call wait_until_set() if you need the value to be correct.
        (This is not the case for dimming, because dimming reads the value read back
        from the H/W. Value might be different if commands are send too fast)"""
        ival = valid(ival)
        self.pwm.duty(ival)
        self.ival = ival
        # a direct reading might not return the actual value
        # we use the actual set/reported value to ensure that dimming works fine
        # Call wait_until_set() if you want to ensure that the set value is correct
        # self.ival = self.pwm.duty()

    def wait_until_set(self):
        """Make sure PWM has taken the correct value (can take up to about 1 ms,
        could be an issue when changing PWM speed in short intervalls)"""
        while self.pwm.duty() != self.ival:
            #pass
            self.pwm.duty(self.ival)

    def maxi(self):
        """maximum value currently set (actually useful for lists, to see whether all lights are off)"""
        return self.ival

    def seti(self, ival):
        """Set raw integer duty from 0 .. 1023 and send status to CAN"""
        self.seti_no_can_message(ival)
        self.wait_until_set()
        if ival != 0:
            self.lastintensity = ival
        self.send_status_to_can()

    def seti16(self, i16):
        """Set integer 0..0xffff"""
        self.seti(i16_to_raw(i16))

    def send_status_to_can(self):
        if self.id is None:
            return
        i1 = self.ival
        i16 = i1 << 6
        if board.CAN:
            # self.msg.setsender(self.id)
            payload = self.msg.payload
            # self.msg[0] = board.CAN.canid >> 8
            # self.msg[1] = board.CAN.canid & 0xff
            payload[3] = i1 >> 8
            payload[4] = i1 & 0xff
            if i1 == 1023:
                i16 = 0xffff
            payload[5] = i16 >> 8
            payload[6] = i16 & 0xff
            self.msg.send()

    def run_next_dimstep(self):
        """Set next dimlevel. Return True when more steps are needed"""
        # try smooth dimming
        self.ival = self.pwm.duty()
        # Picking the correct step size is key for smooth dimming
        ds = (2*self.ival) // 7
        #ds = min(50, max(5, ds))
        #ds = min(150, max(5, ds)) # about 350 ms when min step is 5
        ds = min(150, max(10, ds)) # about 200 ms when min step is 10
        remaining_counts = self.dimtovalue - self.ival
        if abs(remaining_counts) <= ds:
            # Accepting the PWM value takes a while, probably until the end of the phase.
            # So in the order of a few milliseconds (up to 10 with 100 Hz pwm frequency)
            # However, simply setting is OK, it will come there sooner or later.
            self.seti(self.dimtovalue)
            self.dimtovalue = -1
            return False
        if remaining_counts > 0:
            self.seti_no_can_message(self.ival + ds)
        else:
            self.seti_no_can_message(self.ival - ds)
        return True

    def dimi(self, value):
        """dim in raw units, return False if value is directly set, return True otherwise (dimming)"""
        value = valid(value)
        #if value == self.ival and value == self.pwm.duty():
        #    # still report value
        #    self.send_status_to_can()
        #    return False
        if self.dimtovalue < -10:
            self.seti(value)
            return False
        self.dimtovalue = value
        if abs(self.ival-value) < 5:
            self.seti(value)
            return False
        return True

    def dimi16(self, value):
        """dim to values from 0..0xffff"""
        return self.dimi(i16_to_raw(value))

    def on(self):
        if self.ival == self.lastintensity:
            return
        self.dimi(self.lastintensity)

    def off(self):
        self.dimi(0)

    def toggle(self):
        """Toggle on/off. Returns True if output is on after toggle, False if off"""
        if self.ival == 0:
            self.on()
            return True
        self.off()
        return False


class List(PWM):
    def __init__(self, pwmid, *args):
        super().__init__(pwmid, None)
        self.pwms = list(args)
        self.toggle_mode = 0
        self.dimtovalue = -99

    def __repr__(self):
        return '<pwm.List with {} entries>'.format(len(self.pwms))

    def append(self, pwm):
        self.pwms.append(pwm)

    def seti_no_can_message(self, ival):
        self.ival = ival
        for p in self.pwms:
            p.seti_no_can_message(ival)

    def send_status_to_can(self):
        for p in self.pwms:
            p.send_status_to_can()

    def maxi(self):
        """get max value of all PWMs"""
        return max([p.ival for p in self.pwms])

    def dimi(self, value):
        for p in self.pwms:
            p.dimi(value)

    def seti(self, value):
        for p in self.pwms:
            p.seti(value)

    def enable_dimming(self):
        for p in self.pwms:
            p.enable_dimming()

    def on(self):
        # print('pwm.List #{self.id} on')
        for p in self.pwms:
            p.on()
        return True

    def off(self):
        # print('pwm.List #{self.id} off')
        for p in self.pwms:
            p.off()
        return False

    def toggle_off(self):
        # turn off if at least one is on
        # print('pwm.List #{self.id} toggle')
        if self.maxi() > 0:
            return self.off()
        return self.on()
        # print('pwm.List #{self.id} toggle done')

    def toggle_on(self):
        # turn on if at least one is off
        for p in self.pwms:
            if p.maxi() == 0:
                return self.on()
        return self.off()

    def toggle(self):
        if self.toggle_mode:
            return self.toggle_on()
        return self.toggle_off()


board.PWMs = List(0xff) # Create a (dynamic) list that includes ALL PWMs

eod_callbacks = []


async def _next_dim_step_task():
    # set all dimto values to current values, otherwise we can't initialize PWM values for poweron
    for p in board.PWMs.pwms:
        if p.dimtovalue >= 0:
            p.dimtovalue = p.ival

    #isdimming = False
    #dimsteps = 0
    #starttime = 0

    # since we have just set the PWM we can tell how long it will take until the next value
    # will be accepted

    # could use some 10% margin here but there is also the python runtime
    # And if we are slightly faster than the PWM it shouldn't hurt. Worst case
    # we would skip one setting around the end of the dimming process
    # dimdelay = max(1, 1100 // pwm_freq)

    dimdelay_when_dimming = max(1, 1000 // pwm_freq)
    was_dimming = False

    while True:
        isdimming = False
        for p in board.PWMs.pwms:
#            if p.dimtovalue >= 0  and  p.pwm.duty() != p.dimtovalue:
            if p.dimtovalue >= 0  and  p.pwm.duty() != p.dimtovalue:
                isdimming = True
                p.run_next_dimstep()
        # ask other async tasks to delay their execution to ensure smooth and uniterrupted dimming
        board.PWM_IS_DIMMING = isdimming
        if isdimming:
            was_dimming = True
        else:
            if was_dimming:
                for cb in eod_callbacks:
                    cb()
                was_dimming = False


        #if not isdimming and dimsteps > 1:
        #    # finished dimming
        #    print("finished dimming with {} steps in {} ms".format(dimsteps, utime.ticks_diff(utime.ticks_ms(), starttime)))
        #    print("sleep time should have been {} ms".format(max(1, dimdelay_ms // 5)))
        #    dimsteps = 0

        # NOTE: numbers below are strongly depending on the (min/max) stepsize chosen in
        # run_next_dimstep() -> there is the real lever for smooth dimming.
        #
        # Calling this faster than about 1ms does not help since the PWM needs some time to settle
        # Using 200Hz PWM frequency:
        #  delay of     0 us -> about 150 steps in about 140 ms
        #  delay of   500 us -> about  90 steps in about 140 ms
        #  delay of  1000 us -> about  65 steps in about 140 ms
        #
        # Using 100Hz PWM frequency:
        #  delay of  1000 us -> about 130 steps in about 270 ms

        # If control is given back to the scheduler with 2ms sleep time
        # then dimming takes about 160 ms with about 25 steps. But still looks smooth

        # If control is given back to the scheduler with 1ms sleep time
        # then dimming takes about 160 ms with about 30 steps. But still looks smooth

        # don't yield to other tasks while we are dimming.
        # OK since dimming takes less than 200 ms
        #if isdimming:
        #    utime.sleep_ms(dimdelay_when_dimming)
        #    continue
        await asyncio.sleep_ms(dimdelay_when_dimming if isdimming else dimdelay_ms)

board.BACKGROUND_RUNNERS.append(_next_dim_step_task())


### Handle PWM callbacks

class _badPWMClass: # used to avoid the need of error catching in CAN callbacks
    def dimi16(self, _):
        pass
    def on(self):
        pass
    def off(self):
        pass
    def toggle(self):
        pass

_dummyPWM = _badPWMClass()

# return a PWM for the portid.
# If portid >0x7f a list of PWMs (which bit position is set in portid) will be returned
def _getpwm(msg):
    if msg.payload[1] & 0x80 == 0:
        sensor = board.SENSORSs.find(msg, (PWM, List), 0xa0)
        return sensor and sensor or _dummyPWM
    # create a list of PWMs
    pwms = List(None)
    i = 0
    bm = msg.payload[1] & 0x7f
    while bm != 0:
        if bm & 1 == 1:
            p = board.SENSORSs.get_sensor(i)
            if isinstance(p, (PWM, List)):
                pwms.append(p)
        bm >>= 1
        i += 1
    return pwms

can.register(pwmcode.SET_INTENSITY16, 4, 4, lambda msg: _getpwm(msg).dimi16(msg.u16(2)))
can.register(pwmcode.SET_INTENSITY_NATIVE, 4, 4, lambda msg: _getpwm(msg).dimi(msg.u16(2)))
can.register(pwmcode.ON, 2, 2, lambda msg: _getpwm(msg).on())
can.register(pwmcode.OFF, 2, 2, lambda msg: _getpwm(msg).off())
can.register(pwmcode.TOGGLE, 2, 2, lambda msg: _getpwm(msg).toggle())
