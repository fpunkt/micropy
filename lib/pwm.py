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

dimdelay_ms = 5
#dimdelay_ms = 10

# PWM freq defines the overall frequency of the device in Hz. 100 Hz is a good number
pwm_freq = 100

def _float_to_raw(value):
    return max(0, min(1023, int(value*1023)))

def _tofloat(value):
    return value / 1023.0

def _i16_to_raw(v):
    vv = v >> 6
    if vv == 0 and v > 0:
        return 1
    return vv

class PWM:
    """Wrapper for system PWM, using numbers from 0..1 and provide dimming"""
    def __init__(self, pwmid, pin):
        self.id = pwmid
        self.ival = 0
        self.lastintensity = 100
        self.pwm = None
        if pin is not None:
            self.pwm = machine.PWM(machine.Pin(pin))
        board.SENSORSs.register(pwmid, self)
        if pin is None:
            return

        # global pwm_freq
        if pwm_freq > 0:
            self.pwm.freq(pwm_freq)
            # pwm_freq = 0
            utime.sleep_ms(5) # for some strange reason after setting pwm_freq ..
        # print('setting duty for {}/{} to 0'.format(pwmid, pin))
        # self.pwm.duty(0)
        self.seti_no_can_message(0) # power off
        self.seti_no_can_message(0) # power off
        self.seti_no_can_message(0) # power off
        self.dimtovalue = 0
        # self.button = None

        # allocate message once to avoid garbage collection
        self.msg = can.Message(canid.PWM_VALUE, [0, 0, 0, 0, 0, 0, 0])
        self.msg.setsender(self.id)
        board.PWMs.append(self)

    def __repr__(self):
        return '<PWM {}.{}>'.format(self.id, self.pwm)

    def poll(self):
        if self.ival == self.dimtovalue:
            return False
        return self.run_next_dimstep()

    def seti_no_can_message(self, ival):
        """Set PWM value. NOTE: the actual value may not be the one that has been commanded.
        Call wait_until_set() if you need the value to be correct.
        (This is not the case for dimming, because dimming reads the value read back
        from the H/W. Value might be different if commands are send too fast)"""
        ival = min(1023, max(ival, 0))
        self.pwm.duty(ival)
        # self.ival = ival
        # a direct reading might not return the actual value
        # we use the actual set/reported value to ensure that dimming works fine
        # Call wait_until_set() if you want to ensure that the set value is correct
        self.ival = self.pwm.duty()

    def wait_until_set(self):
        """Make sure PWM has taken the correct value (potential issue when changing PWM speed in short intervalls)"""
        while self.pwm.duty() != self.ival:
            self.seti_no_can_message(self.ival)

    def maxi(self):
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
        self.seti(_i16_to_raw(i16))

    def send_status_to_can(self):
        # self.msg.setsender(self.id)
        i1 = self.ival
        payload = self.msg.payload
        # self.msg[0] = board.CAN.canid >> 8
        # self.msg[1] = board.CAN.canid & 0xff
        payload[3] = i1 >> 8
        payload[4] = i1 & 0xff
        i16 = i1 << 6
        if i1 == 1023:
            i16 = 0xffff
        payload[5] = i16 >> 8
        payload[6] = i16 & 0xff
        self.msg.send()

    def setf(self, value):
        """Set values from 0..1"""
        self.seti(_float_to_raw(value))

    def getf(self):
        """Return current value 0..1"""
        return _tofloat(self.ival)

    def next_dimstep_if_needed(self):
        self.ival = self.pwm.duty()
        if self.ival == self.dimtovalue:
            return False
        return self.run_next_dimstep()

    def run_next_dimstep(self):
        """Set next dimlevel. Return True when more steps are needed"""
        # try smooth dimming
        self.ival = self.pwm.duty()
        ds = self.ival // 4
        #ds = min(50, max(5, ds))
        ds = min(200, max(30, ds))
        remaining_counts = self.dimtovalue - self.ival
        if abs(remaining_counts) <= ds:
            self.seti_no_can_message(self.dimtovalue)
            #if board.DEBUG:
            #    print('{} last step {} is {}'.format(self, self.dimtovalue, self.ival))
            if self.ival == self.dimtovalue:
                # accept value and send message to CAN
                # print('dimming finished')
                self.seti(self.dimtovalue)
                board.good_time_for_gc()
                return False
            return True
        if remaining_counts > 0:
            self.seti_no_can_message(self.ival + ds)
        else:
            self.seti_no_can_message(self.ival - ds)
        return True

    def dimi(self, value):
        """dim in raw units"""
        self.dimtovalue = value
        if abs(self.ival-value) < 5:
            self.seti(value)

    def dimi16(self, value):
        """dim to values from 0..0xffff"""
        self.dimi(_i16_to_raw(value))

    def dimf(self, value):
        self.dimi(_float_to_raw(value))

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


async def _next_dim_step_task():
    while True:
        delay = dimdelay_ms
        isdimming = False
        for p in board.PWMs.pwms:
            if p.poll():
                isdimming = True
                delay = max(1, dimdelay_ms // 5)
        # ask other async tasks to delay their execution to ensure smooth and uniterrupted dimming
        board.PWM_IS_DIMMING = isdimming
        await asyncio.sleep_ms(delay)

board.BACKGROUND_RUNNERS.append(_next_dim_step_task())

board.PWMs = List(0xff) # Create a (dynamic) list that includes ALL PWMs

### Handle PWM callbacks

# return a PWM for the sensorid.
# If sensorid >0x7f a list of PWMs (which bit position is set in sensorid) will be returned
def _getpwm(msg):
    if msg.payload[1] & 0x80 == 0:
        return board.SENSORSs.find(msg, (PWM, List), 0xa0)
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

can.register(pwmcode.SET_INTENSITY, 4, 4, lambda msg: _getpwm(msg).dimi16(msg.u16(2)))
can.register(pwmcode.ON, 2, 2, lambda msg: _getpwm(msg).on())
can.register(pwmcode.OFF, 2, 2, lambda msg: _getpwm(msg).off())
can.register(pwmcode.TOGGLE, 2, 2, lambda msg: _getpwm(msg).toggle())
