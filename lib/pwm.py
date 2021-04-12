"""
pwm.py

Uses Timer(1)

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-many-instance-attributes

import machine
import sensors
import micropython
import cancommon
import utime

dimdelay_ms = 8

class _DimList:
    def __init__(self):
        self._ndevices = 0
        self._devices = [None] * 8
        self._lastdimstep_ref = self._lastdimstep
        self._nextstep_ref = self._next_step_isr
        self.isdimming = False
        self._timer = machine.Timer(1)

    def __repr__(self):
        return '<DimList {} entries, dimming={}>'.format(len(self._devices), self.isdimming)

    def _lastdimstep(self, _):
        # this is called outside the ISR
        i = 0
        while i < self._ndevices:
            device = self._devices[i]
            if device is not None:
                i += 1
                if device.ival == device.dimtovalue:
                    device.send_status_to_can()
                    self._devices[i] = None
        # update _ndevices to avoid looping
        i = self._ndevices-1
        while i >= 0:
            if self._devices[i] is not None:
                break
            i += 1
        self._ndevices = i
        if self._ndevices == 0:
            self.isdimming = False

    def _next_step_isr(self, _):
        if not self.isdimming:
            return
        i = 0
        while i < self._ndevices:
            device = self._devices[i]
            i += 1
            if device is None:
                continue
            # try smooth dimming
            # avoid floating point (and malloc)
            # ds, _ = divmod(device.ival, 10)
            ds = device.ival >> 1
            # ds = int(device.ival / 10)
            ds = min(100, max(1, ds))
            remaining_counts = device.dimtovalue - device.ival
            if abs(remaining_counts) <= ds:
                device.seti_no_can_message(device.dimtovalue)
                micropython.schedule(self._lastdimstep_ref, device)
            elif remaining_counts > 0:
                device.seti_no_can_message(device.ival + ds)
            else:
                device.seti_no_can_message(device.ival - ds)
        self._timer.init(period=dimdelay_ms, mode=machine.Timer.ONE_SHOT, callback=self._nextstep_ref)

    def append(self, pwm):
        # check if entry is already in list
        i = 0
        while i < self._ndevices:
            if self._devices[i] == pwm:
                return # keep on running ...
        if self._ndevices >= len(self._devices)-1:
            raise RuntimeError('Too many PWMs')
        irq_state = machine.disable_irq()
        self._devices[self._ndevices] = pwm
        self._ndevices += 1
        if not self.isdimming:
            self.isdimming = True
            self._nextstep_ref(None)
        machine.enable_irq(irq_state)

    def wait(self):
        """Wait till all dimming is done"""
        while self.isdimming:
            utime.sleep_ms(50)

dimlist = _DimList()


def _float_to_raw(value):
    return max(0, min(1023, int(value*1023)))

def _tofloat(value):
    return value / 1023.0

def _i16_to_raw(v):
    return v >> 6

class PWM:
    """Wrapper for system PWM, using numbers from 0..1 and provide dimming"""
    def __init__(self, pin, id):
        sensors.register(id, self)
        self.pwm = machine.PWM(machine.Pin(pin))
        self.ival = 0
        self.id = id
        self.seti_no_can_message(0) # power off
        self.dimtovalue = 0

        # allocate message once to avoid garbage collection
        self.msg = cancommon.Message(cancommon.CANID_PWM_VALUE, [0, 0, 0, 0, 0, 0, 0])
        self.msg.setsender(self.id)

    def seti_no_can_message(self, ival):
        self.pwm.duty(ival)
        self.ival = ival

    def seti(self, ival):
        """Set raw integer duty from 0 .. 1023 and send status to CAN"""
        self.seti_no_can_message(ival)
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

    def dimi(self, value):
        """dim in raw units"""
        if abs(self.ival-value) < 5:
            self.seti(value)
            return
        self.dimtovalue = value
        dimlist.append(self)

    def dimi16(self, value):
        """dim to values from 0..0xffff"""
        self.dimi(_i16_to_raw(value))

    def dimf(self, value):
        self.dimi(_float_to_raw(value))
