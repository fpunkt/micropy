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

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-many-instance-attributes, global-statement

import board
import machine
import can
import canid
import utime
import pwmcode
import uasyncio as asyncio
import schedule

dimdelay_ms = 5

# PWM freq defines the overall frequency of the device in Hz. 100 Hz is a good number
pwm_freq = 100

def _float_to_raw(value):
    return max(0, min(1023, int(value*1023)))

def _tofloat(value):
    return value / 1023.0

def _i16_to_raw(v):
    return v >> 6

class PWM:
    """Wrapper for system PWM, using numbers from 0..1 and provide dimming"""
    def __init__(self, id, pin):
        self.id = id
        self.ival = 0
        self.lastintensity = 100
        board.SENSORSs.register(id, self)
        if pin is None:
            return
        self.pwm = machine.PWM(machine.Pin(pin))
        # global pwm_freq
        if pwm_freq > 0:
            self.pwm.freq(pwm_freq)
            # pwm_freq = 0
            utime.sleep_ms(5) # for some strange reason after setting pwm_freq ..
        # print('setting duty for {}/{} to 0'.format(id, pin))
        # self.pwm.duty(0)
        self.seti_no_can_message(0) # power off
        self.dimtovalue = 0
        self.button = None

        # allocate message once to avoid garbage collection
        self.msg = can.Message(canid.PWM_VALUE, [0, 0, 0, 0, 0, 0, 0])
        self.msg.setsender(self.id)
        board.PWMs.append(self)
        #schedule.add_poller(self.poll)

    def poll(self):
        if self.ival == self.dimtovalue:
            return False
        return self.run_next_dimstep()

    def seti_no_can_message(self, ival):
        self.pwm.duty(ival)
        self.ival = ival

    def forcei_no_can_message(self, ival):
        # for some strange reason sometimes the value is not taken
        while self.pwm.duty() != ival:
            self.pwm.duty(ival)
        self.ival = ival

    def seti(self, ival):
        """Set raw integer duty from 0 .. 1023 and send status to CAN"""
        self.seti_no_can_message(ival)
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
        if self.ival == self.dimtovalue:
            return False
        return self.run_next_dimstep()

    def run_next_dimstep(self):
        """Set next dimlevel. Return True when more steps are needed"""
        # try smooth dimming
        # avoid floating point (and malloc)
        # ds, _ = divmod(device.ival, 10)
        ds, _ = divmod(self.ival, 4)
        ds = min(50, max(5, ds))
        remaining_counts = self.dimtovalue - self.ival
        if abs(remaining_counts) <= ds:
            self.forcei_no_can_message(self.dimtovalue)
            self.seti(self.dimtovalue)
            return False
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

class PWMList(PWM):
    def __init__(self, id, *args):
        super().__init__(id, None)
        self.pwms = list(args)

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


async def _next_dim_step_task():
    while True:
        for p in board.PWMs.pwms:
            p.poll()
        await asyncio.sleep_ms(dimdelay_ms)

schedule.add_task(_next_dim_step_task)

_pwmcommands = {
    pwmcode.ON: (2, lambda p, _: p.on()),
    pwmcode.OFF: (2, lambda p, _: p.off()),
    pwmcode.SET_INTENSITY: (4, lambda p, msg: p.dimi16(msg.u16(2)))
}

def handle(msg):
    """Handle CAN message. Return True if handled"""
    # print('CAN handle {}'.format(msg))
    l = len(msg.payload)
    if l < 1:
        return False
    command = msg.payload[0]

    nargs, callback = _pwmcommands.get(command, (1, None))
    if callback is None:
        return False

    if l != nargs:
        if board.DEBUG:
            print('Bad number of args {}, expected {}'.format(l, nargs))
        msg.bad_number_of_args(nargs)
        return True

    if msg.payload[1] & 0x80:
        # loop over bitmask

        # stupid copy loop, can't assign to byte array
        i = 0
        b = [0] * len(msg.payload)
        for bb in msg.payload:
            b[i] = bb
            i += 1

        msg.payload = b

        i = 0
        bm = msg.payload[1] & 0x7f
        # print('Start looping {:2x}'.format(bm))
        while bm != 0:
            # print('    looping {:2x} -> {}'.format(bm, bm & 1))
            if bm & 1 != 0:
                b[1] = i
                p = board.SENSORSs.find(msg, (PWM, PWMList), 0xa0)
                if p:
                    callback(p, msg)
            i += 1
            bm >>= 1
        return True

    # print('========== single PWM command')
    p = board.SENSORSs.find(msg, (PWM, PWMList), 0xa0)
    if p is None:
        return True
    callback(p, msg)
    return True
