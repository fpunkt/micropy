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
import uasyncio as asyncio
import board
import can
import canid
import pwmcode
import port
try:
    import fsmqtt
except:
    fsmqtt = None


# Wakeup dimmer loop when needed
start_dimming = asyncio.Event()

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

_FINISHED_DIMMING = const(-1)
NODIMMING = const(-99)

# Minimum step size - dimming takes about 350 ms for dimstep_min=5 and 200 ms for dimstep_min = 10
dimstep_min = 10

dimstep_max = 100

# Calculate size for next dimstep to 2*val / dimstep_scale
dimstep_scale = 7

# PWM freq defines the overall frequency of the device in Hz.
# 100 Hz is a good no-flicker number, but dimming is not as smooth as it could be
# the PWM needs some time to settle (change only at end of cycle?), higher frequency allows
# for higher change rates when setting the PWM, e.g. smoother dimming.
# 200 Hz has nicer dimming.
# pwm_freq = 100
pwm_freq = 200

_nbit_pwm = const(10)
_max_raw_value = const((1 << _nbit_pwm)-1)

def i16_to_raw(v):
    vv = v >> (16-_nbit_pwm)
    if vv == 0 and v > 0:
        return 1
    return vv

def valid(i):
    """Return value in range 0..1023, accepts raw integers (0..1023) or floating point numbers 0.0 .. 1.0"""
    if isinstance(i, float):
        return int(i*_max_raw_value)
    return min(_max_raw_value, max(i, 0))

class PWM(port.Port):
    """TODO: fix docstring? Wrapper for system PWM, using numbers from 0..1 and provide dimming"""
    def __init__(self, portid, pinid, lastintensity=100):
        super().__init__(portid, pinid)
        self.lastintensity = lastintensity
        self.button = None
        self.pwm = None
        self.toggle_prefer_off = False
        if pinid is not None:
            self.pwm = machine.PWM(machine.Pin(pinid), duty=0, freq=pwm_freq)
        if board.PWMs is not None:
            # is still None for ALL pwm list
            board.PWMs.append(self)
        if pinid is None:
            return

        self.seti_no_can_message(0) # power off
        self.dimtovalue = 0
        self.mqttstate = None # cache to avoid gc

        # allocate message once to avoid garbage collection
        self.msg = can.Message(canid.PWM_VALUE, [0, 0, 0, 0, 0, 0, 0])
        self.msg.setsender(self.portid)

    def __repr__(self):
        return '<{} {}.{}>'.format(self.__class__.__name__, self.portid, self.pwm)

    def set_button(self, button):
        if self.button is not None:
            # unregister with previously set button
            self.button.set_pwm(None)
        self.button = button

    def send_telemetry(self):
        pass

    def current_value(self):
        """Return current pwm value"""
        return self.pwm.duty()

    def disable_dimming(self):
        self.dimtovalue = NODIMMING

    def enable_dimming(self):
        # set a valid value but prevent dimming to it -> use the current value
        self.dimtovalue = self.current_value()

    def seti_no_can_message(self, ival):
        """Set PWM value. NOTE: the actual value may not be the one that has been commanded.
        Call wait_until_set() if you need the value to be correct.
        (This is not the case for dimming, because dimming reads the value read back
        from the H/W. Value might be different if commands are send too fast).
        Function returns the value used (does some error checking for bad input)"""
        ival = valid(ival)
        self.pwm.duty(ival)
        return ival

    def wait_until_set(self, value):
        """Make sure PWM has taken the correct value (can take up to about 1 ms,
        could be an issue when changing PWM speed in short intervalls)"""
        maxtry = 10
        while maxtry > 0 and self.pwm.duty() != value:
            maxtry -= 1
            self.pwm.duty(value)

    def maxi(self):
        """maximum value currently set (actually useful for lists, to see whether at one light is on)"""
        return self.current_value()

    def mini(self):
        """minimum value currently set (actually useful for lists, to see whether all lights are on)"""
        return self.current_value()

    def is_on(self):
        """Return if PWM is considered ON.
        May behave differently for Lists and Scence (e.g. one vs all are on)"""
        maxi = self.maxi()
        mini = self.mini()
        if board.DEBUG:
            print('{} is_on maxi={}, mini={}, toggle_prefer_off={}'.format(self, maxi, mini, self.toggle_prefer_off))
        if maxi == 0:
            return False
        if mini > 0:
            return True
        # some are on, some are off
        return self.toggle_prefer_off

    def one_is_on(self) -> bool:
        """Return True if at least one light is on"""
        return self.maxi() > 0

    def all_are_on(self) -> bool:
        """Return True if all lights are on"""
        return self.mini() > 0

    def all_are_off(self) -> bool:
        """Return True if all lights are off"""
        return self.mini() == 0

    def seti(self, ival):
        """Set raw integer duty from 0 .. 1023 and send status to CAN"""
        ival = self.seti_no_can_message(ival)
        if ival != 0:
            self.lastintensity = ival
        self.send_status_to_can_value(ival)
        if self.button is not None:
            self.button.set_state(ival)
        self.wait_until_set(ival)

    def seti16(self, i16):
        """Set integer 0..0xffff"""
        self.seti(i16_to_raw(i16))

    def send_status_to_can(self):
        self.send_status_to_can_value(self.current_value())

    def send_status_to_can_value(self, ival):
        if self.portid is None:
            return
        i16 = ival << 6
        if board.CAN:
            # self.msg.setsender(self.id)
            payload = self.msg.payload
            # self.msg[0] = board.CAN.canid >> 8
            # self.msg[1] = board.CAN.canid & 0xff
            payload[3] = ival >> 8
            payload[4] = ival & 0xff
            if ival == 1023:
                i16 = 0xffff
            payload[5] = i16 >> 8
            payload[6] = i16 & 0xff
            self.msg.send()

    def run_next_dimstep(self):
        """Set next dimlevel for smooth dimming to finally reach self.dimtovalue."""
        ival = self.pwm.duty()
        # Pick nice step size for smooth dimming
        ds = (2*ival) // dimstep_scale
        ds = min(dimstep_max, max(dimstep_min, ds)) # about 200 ms when min step is 10
        remaining_counts = self.dimtovalue - ival
        if board.DEBUG > 2:
            print('pwm: {:2d}, iv: {:4d}, ds: {:3d}, remaining: {:4d}'.format(self.portid, ival, ds, remaining_counts))
        if abs(remaining_counts) <= ds:
            if board.DEBUG > 1:
                print('  end of dimming - remaining = {}, setting to {}'.format(remaining_counts, self.dimtovalue))
            # Accepting the PWM value takes a while, probably until the end of the phase.
            # So in the order of a few milliseconds (up to 10 with 100 Hz pwm frequency)
            # However, simply setting is OK, it will come there sooner or later.
            self.seti_no_can_message(self.dimtovalue)
            if remaining_counts == 0:
                # reached target
                self.send_status_to_can()
                self.dimtovalue = _FINISHED_DIMMING
            return
        if remaining_counts > 0:
            self.seti_no_can_message(ival + ds)
        else:
            self.seti_no_can_message(ival - ds)

    def dimi(self, value):
        """dim in raw units, return False if value is directly set, return True otherwise (dimming)"""
        value = valid(value)
        if self.dimtovalue == NODIMMING:
            self.seti(value)
            return False
        if abs(self.current_value()-value) < 5:
            self.dimtovalue = _FINISHED_DIMMING
            self.seti(value)
            return False
        self.dimtovalue = value
        if board.DEBUG > 2:
            print('Start dimming {}'.format(self.portid))
        start_dimming.set()
        return True

    def dimi16(self, i16):
        """dim to values from 0..0xffff"""
        return self.dimi(i16_to_raw(i16))

    def on(self):
        """Set intensity to lastintensity"""
        self.dimi(self.lastintensity)

    def off(self):
        """Set intensity to 0"""
        self.dimi(0)

    def toggle(self) -> bool:
        """Turn PWM on if it was off or vice versa.
        For PWM List you can set the .toggle_prefer_off to switch all of if at least one was off
        or to switch all on if at least one was on.
        The function returns True when (at least) one light is on after calling toggle, False otherwise.
        """
        t = self.is_on()
        if board.DEBUG:
            print('PWM {} is_on: {}'.format(self, t))
        if t:
            self.off()
        else:
            self.on()
        return not t

    def mqtt_callback(self, _, msg):
        try:
            value = int(msg)
            value = min(255, max(0, value))
            self.dimi16(((value & 0xff) << 8) | value)
            return
        except:
            pass
        # print('PWM {} got called by MQTT: {}'.format(self.id, msg))
        msg = msg.upper()
        if msg == '{"STATE": "OFF"}' or msg == 'OFF':
            self.dimi(0)
            return
        if msg == '{"STATE": "ON"}' or msg == 'ON':
            self.on()
            return
        # {"state": "ON", "brightness": 97}
        l = len(msg) - 1
        if l < 5:
            print('Bad MQTT message {}'.format(msg))
            return
        # search for blank
        while l > 0 and msg[l] != ord(' ') and msg[l] != ord(':'):
            l -= 1
        print('PWM callback got value "{}"'.format(msg[l:-1]))
        value = int(msg[l:-1])
        print('Setting PWM {} to {}'.format(self.portid, value))
        self.dimi16(((value & 0xff) << 8) | value)
        return


class List(PWM):
    def __init__(self, pwmid, *args) -> None:
        self.pwms = list(args) # need to initialize here in case __repr__() is called
        super().__init__(pwmid, None)
        self.toggle_mode = 0
        self.dimtovalue = NODIMMING

    def __len__(self): return len(self.pwms)
    def __getitem__(self, key): return self.pwms[key]

    def __repr__(self):
        return '<pwm.List with {} entries>'.format(len(self.pwms))

    def current_value(self):
        """Current value of a PWM List it the maximum of all its PWMs"""
        return self.maxi()

    def append(self, pwm):
        self.pwms.append(pwm)

    def seti_no_can_message(self, ival):
        for p in self.pwms:
            p.seti_no_can_message(ival)
        return ival

    def send_status_to_can(self):
        for p in self.pwms:
            p.send_status_to_can()

    def maxi(self):
        """get max value of all PWMs"""
        return max([p.current_value() for p in self.pwms])

    def mini(self):
        """Return min value of all PWMs"""
        return min([p.current_value() for p in self.pwms])

    def dimi(self, value):
        ret = False
        for p in self.pwms:
            ret |= p.dimi(value)
        return ret

    def dimi16(self, i16):
        ret = False
        for p in self.pwms:
            ret |= p.dimi16(i16)
        return ret

    def seti(self, ival):
        for p in self.pwms:
            p.seti(ival)

    def seti16(self, i16):
        for p in self.pwms:
            p.seti16(i16)

    def enable_dimming(self):
        for p in self.pwms:
            p.enable_dimming()

    def disable_dimming(self):
        for p in self.pwms:
            p.disable_dimming()

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

    def mqtt_callback(self, topic, msg):
        for p in self.pwms:
            p.mqtt_callback(topic, msg)

class SceneEntry:
    def __init__(self, pwm, rawvalue):
        self.pwm = pwm
        self.rawvalue =  rawvalue

class Scene(PWM):
    """A scene is a collection of PWMs that will be set to predefined levels.
    A scene itself can be on or off"""
    def __init__(self, portid, *values) -> None:
        super().__init__(portid, None)
        self.dimtovalue = NODIMMING
        self.entries = dict()
        self.define_values(*values)

    def on(self):
        """turn scene on"""
        for e in self.entries.values():
            e.pwm.dimi(e.rawvalue)

    def off(self):
        """turn scene off"""
        for e in self.entries.values():
            e.pwm.dimi(0)

    def is_on(self) -> bool:
        """Return true when each PWM matches its predefined value"""
        allzero = True
        for p in self.entries.values():
            d = p.pwm.pwm.duty()
            if allzero and d == 0:
                continue
            if p.rawvalue != d:
                return self.toggle_prefer_off
            allzero = False
        return not allzero

    def toggle(self):
        """Toggle Scene, return True when light is on after toggle"""
        state = self.is_on()
        if board.DEBUG:
            print('PWM toggle, old state is {} {}'.format(self, state))
        if state:
            self.off()
        else:
            self.on()
        return not state

    def dimi(self, value):
        if value > 0:
            self.on()
        else:
            self.off()

    def seti(self, value):
        self.dimi(value)

    def current_value(self):
        return self.maxi()

    def maxi(self):
        return max([p.pwm.current_value() for p in self.entries.values()])

    def mini(self):
        """Get min intensity, ignore LEDs that are switched off in this scene"""
        mini = 0xffff
        for p in self.entries.values():
            if p.rawvalue > 0:
                mini = min(mini, p.pwm.current_value())
        return mini

    def define_value(self, pwm, value):
        """Define the scene-on-value for given PWM. Use None or -1 to remove the PWM from this scene.
        pwm can be a PWM or a port-id"""
        pid = pwm.portid
        if value is None or value < 0:
            # do not use the PWM in this scene
            del self.entries[pid]
            return
        self.entries[pid] = SceneEntry(pwm, valid(value))

    def define_values(self, *values):
        for v in values:
            if isinstance(v, SceneEntry):
                self.define_value(v.pwm, v.value)
            else:
                try:
                    p, val = v
                    self.define_value(p, val)
                except:
                    raise



board.PWMs = List(0xff) # Create a (dynamic) list that includes ALL PWMs

eod_callbacks = []


async def _next_dim_step_task():
    # set all dimto values to current values, otherwise we can't initialize PWM values for poweron
    for p in board.PWMs.pwms:
        if p.dimtovalue >= 0:
            p.dimtovalue = p.current_value()

    # since we have just set the PWM we can tell how long it will take until the next value
    # will be accepted

    # could use some 10% margin here but there is also the python runtime
    # And if we are slightly faster than the PWM it shouldn't hurt. Worst case
    # we would skip one setting around the end of the dimming process
    # dimdelay = max(1, 1100 // pwm_freq)

    dimdelay_when_dimming = max(1, 1000 // pwm_freq)
    if board.DEBUG:
        print('dimdelay when dimming = {}'.format(dimdelay_when_dimming))
    was_dimming = False

    while True:
        isdimming = False
        for p in board.PWMs.pwms:
            if p.dimtovalue >= 0:
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
        if isdimming:
            await asyncio.sleep_ms(dimdelay_when_dimming)
        else:
            start_dimming.clear()
            if board.DEBUG > 2:
                print('stopped dimming, waiting for start_dimming event()')
            await start_dimming.wait()
            if board.DEBUG > 3:
                print('return from start_dimming waiter')


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

def find(msg):
    """Find pwm with ID in 2nd byte of payload"""
    return board.PORTs.find(msg, (PWM, List), 0xa0)

# return a PWM for the portid.
# If portid >0x7f a list of PWMs (which bit position is set in portid) will be returned
def _getpwm(msg):
    if msg.payload[1] & 0x80 == 0:
        pwm = find(msg)
        return pwm and pwm or _dummyPWM
    # create a list of PWMs
    pwms = List(None)
    i = 0
    bm = msg.payload[1] & 0x7f
    while bm != 0:
        if bm & 1 == 1:
            p = board.PORTs.get_sensor(i)
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

