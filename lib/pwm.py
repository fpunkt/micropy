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

class _DimList:
    def __init__(self):
        self._devices = []
        self._lastdimstep_ref = self._lastdimstep
        self._nextstep_ref = self._next_step_isr
        self._isdimming = False
        self._timer = machine.Timer(1)

    def __repr__(self):
        return '<DimList {} entries, dimming={}>'.format(len(self._devices), self._isdimming)

    def _lastdimstep(self, _):
        # this is called outside the ISR
        to_remove = []
        for device in self._devices:
            if device.dimcount == 0:
                device.iset(device.dimtovalue)
                to_remove.append(device)

        irq_state = machine.disable_irq()
        for device in to_remove:
            self._devices.remove(device)
        if len(self._devices) == 0:
            self._isdimming = False
        machine.enable_irq(irq_state)


    def _next_step_isr(self, _):
        if not self._isdimming:
            return
        for device in self._devices:
            if device.dimcount > 0:
                device.dimcount -= 1
                if device.dimcount == 0:
                    micropython.schedule(self._lastdimstep_ref, device)
                else:
                    device.iset_no_can_message(device.ival + device.dimstep)
        self._timer.init(period=10, mode=machine.Timer.ONE_SHOT, callback=self._nextstep_ref)

    def start_dimming(self, device):
        irq_state = machine.disable_irq()
        try:
            self._devices.remove(device)
        except ValueError:
            pass
        except:
            machine.enable_irq(irq_state)
            raise

        self._devices.append(device)
        if not self._isdimming:
            self._isdimming = True
            self._nextstep_ref(None)
        machine.enable_irq(irq_state)

dimlist = _DimList()


def _toint(value):
    return max(0, min(1023, int(value*1023)))

def _tofloat(value):
    return value / 1023.0

class PWM:
    """Wrapper for system PWM, using numbers from 0..1 and provide dimming"""
    def __init__(self, pin, id):
        sensors.register(id, self)
        self.pwm = machine.PWM(machine.Pin(pin))
        self.ival = 0
        self.id = id
        self.iset_no_can_message(0) # power off
        self.dimtovalue = 0
        self.dimcount = 0
        self.dimstep = 0

    def iset_no_can_message(self, ival):
        self.pwm.duty(ival)
        self.ival = ival

    def iset(self, ival):
        """Set raw integer duty from 0 .. 1023 and send status to CAN"""
        self.iset_no_can_message(ival)
        self.send_status_to_can()

    def send_status_to_can(self):
        i1 = self.ival
        i2 = i1 << 6
        if i1 == 1023:
            i2 = 0xffff
        payload = [i1 >> 8, i1 & 0xff, i2 >> 8, i2 & 0xff]
        sensors.send(cancommon.CANID_PWM_VALUE, self.id, payload)

    def set(self, value):
        """Set values from 0..1"""
        self.iset(_toint(value))

    def get(self):
        """Return current value 0..1"""
        return _tofloat(self.ival)

    def dim(self, value):
        iv = _toint(value)
        steps = 20
        idiff = int((iv-self.ival) / steps)
        if idiff == 0:
            self.set(value)
            return
        self.dimtovalue = iv
        self.dimstep = idiff
        self.dimcount = steps
        dimlist.start_dimming(self)
