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

import math
import machine
import asyncio
import board
import canid
import pwmcode
import port


# Wakeup dimmer loop when needed
start_dimming = asyncio.Event()

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

_FINISHED_DIMMING = const(-1)
NODIMMING = const(-99)

ALL_ON = 2
ALL_OFF = 0
SOME_ON = 1

# Minimum step size - dimming takes about 350 ms for dimstep_min=5 and 200 ms for dimstep_min = 10
dimstep_min = 20

dimstep_max = 200

# Calculate size for next dimstep to 2*val / dimstep_scale
dimstep_scale = 0.2

def set_dimstep(value: float):
    global dimstep_min
    global dimstep_max
    global dimstep_scale
    value = min(200.0, max(1.0, value))
    dimstep_min = int(max(10, (value * 20) / 100.0))
    dimstep_max = int(max(200, min(16000, (value * 1000) / 100.0)))
    dimstep_scale = max(0.1, (value * 10) / 100.0)
    board.MQTT.publish('info/dimstep', f'min:{dimstep_min:.1f} max:{dimstep_max:.1f} scale:{dimstep_scale:.1f}')

set_dimstep(150.0) # default value

# Micropython does not expose the PWM resolution but sets it depending on the H/W and the
# choosen PWM frequency.
#
# Rule of thumb (ESP32 family)
# | PWM frequency | Effective resolution |
# | ------------- | -------------------- |
# | 500–1 kHz     | ~13–15 bits          |
# | 5 kHz         | ~11–12 bits          |
# | 20 kHz        | ~9–10 bits           |
# | 40 kHz        | ~8 bits              |


# PWM freq defines the overall frequency of the device in Hz.
# 100 Hz is a good no-flicker number, but dimming is not as smooth as it could be
# the PWM needs some time to settle (change only at end of cycle?), higher frequency allows
# for higher change rates when setting the PWM, e.g. smoother dimming.
# 200 Hz has nicer dimming.
# pwm_freq = 100
pwm_freq = 400


# 2.0 is considered a reasonable value for indoor, 2.2 for architectural lighting, 2.4 for stage/film lighting
GAMMA = 1.6
FLOOR = 0.0015

def set_gamma(g: float):
    global GAMMA
    GAMMA = max(1.0, min(3.0, g))

def set_floor(f: float):
    global FLOOR
    FLOOR = max(0.0, min(1.0, f))

board.MQTT.subscribe('set/gamma', lambda _, msg: set_gamma(float(msg)))
board.MQTT.subscribe('set/floor', lambda _, msg: set_floor(float(msg)))
board.MQTT.subscribe('set/dimstep', lambda _, msg: set_dimstep(float(msg)))

def gamma_corrected_float_to_u16(v: float, maxint=0xffff) -> int:
    """
    Apply gamma correction to a normalized brightness value.

    value: float (0.0 to 1.0)
    gamma: float (typically 2.0–2.4)
    Output: 0..1023
    """
    v = min(1.0, max(v, 0.0))
    if v == 0.0:
        return 0
    # return int((v ** gamma) * 0xffff)
    # according to ChatGPT a math.pow() is faster than **, takes about 30 µs vs 40 µs
    p = math.pow(v, GAMMA)
    x = FLOOR + (1-FLOOR)*p
    return int(x * maxint)

def valid_u16(i: int) -> int:
    """Return value in range 0..0xffff"""
    return min(0xffff, max(i, 0))

def valid_f(f: float) -> float:
    """Return value in range 0..1"""
    return min(1.0, max(f, 0.0))

class PWM(port.Port):
    """TODO: fix docstring? Wrapper for system PWM, using numbers from 0..1 and provide dimming"""
    def __init__(self, portid, pinid, lastintensity=100, maxu16=0xffff):
        super().__init__(portid, pinid)
        self.maxu16 = maxu16
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
        self._fval = 0.0
        self.set_u16_no_telemetry(0) # power off
        self.dimtovalue = 0
        self._dimfvalue = 0.0
        self._dimstepf = 0.0
        self.mqttstate = None # cache to avoid gc

        # allocate message once to avoid garbage collection
        if board.CAN is not None:
            self.msg = board.CAN.Message(canid.PWM_VALUE, [0, 0, 0, 0, 0, 0, 0])
            self.msg.setsender(self.portid)

        board.MQTT.subscribe(f'set/{self.portid}', self.mqtt_set_callback)

    def __repr__(self):
        return '<{} {}.{}>'.format(self.__class__.__name__, self.portid, self.pwm)

    def f_to_u16(self, f: float) -> int:
        """Convert value 0..1 to U16 send to the H/W. This corrects for Gamma and respects clamping"""
        return gamma_corrected_float_to_u16(max(0.0, min(1.0, f)), maxint=self.maxu16)

    def set_button(self, button):
        if self.button is not None:
            # unregister with previously set button
            self.button.set_pwm(None)
        self.button = button

    def current_u16_value(self):
        """Return current pwm value"""
        return self.pwm.duty_u16()

    def current_f(self):
        """Return current float value 0..1"""
        return self._fval

    def disable_dimming(self):
        self.dimtovalue = NODIMMING

    def enable_dimming(self):
        # set a valid value but prevent dimming to it -> use the current value
        self.dimtovalue = self.current_value_u16()

    def set_u16_no_telemetry(self, u16):
        """Set PWM value. NOTE: the actual value may not be the one that has been commanded.
        Call wait_until_set() if you need the value to be correct.
        (This is not the case for dimming, because dimming reads the value read back
        from the H/W. Value might be different if commands are send too fast).
        Function returns the value used (does some error checking for bad input)"""
        self.pwm.duty_u16(u16)
        return u16

    def setf_no_telemetry(self, fval: float):
        """Set PWM to value from 0..1. This intensity will we converted to u16 values using gamma
        and other corrections"""
        self.set_u16_no_telemetry(self.f_to_u16(fval))

    def set_u16(self, u16: int):
        """Set integer duty from 0 .. 0xffff and update telemetry (send status to CAN and MQTT)"""
        u16 = self.set_u16_no_telemetry(u16)
        if u16 != 0:
            self.lastintensity = u16
        self.send_telemetry_u16(u16)
        if self.button is not None:
            self.button.set_state(u16)
        self.wait_until_set_u16(u16)

    def setf(self, fval: float):
        """Set value 0..1"""
        self.set_u16(self.f_to_u16(fval))

    def wait_until_set_u16(self, u16) -> int:
        """Make sure PWM has taken the correct value (can take up to about 1 ms,
        could be an issue when changing PWM speed in short intervalls).
        The function returns the value that was actually choosen by MicroPython. The
        actual value depends on the H/W and the choosen PWM frequency.
        """
        self.pwm.duty_u16(u16)
        maxtry = 10
        while maxtry > 0 and self.pwm.duty_u16() != u16:
            maxtry -= 1
        return self.pwm.duty_u16()

    def max_u16(self):
        """maximum value currently set (actually useful for lists, to see whether at one light is on)"""
        return self.current_u16_value()

    def min_u16(self):
        """minimum value currently set (actually useful for lists, to see whether all lights are on)"""
        return self.current_u16_value()

    def pwm_state(self) -> int:
        """Return on of ALL_ON, ALL_OFF, SOME_ON. The latter value is only interesting for a list of PWM"""
        if self.current_u16_value() == 0:
            return ALL_OFF
        return ALL_ON

    def is_on(self) -> bool:
        """Return True if PWM (list of PWM) is considdered on. For a list of PWM this depends the setting of
        toggle_prefer_off"""
        state = self.pwm_state()
        if state == ALL_ON:
            return True
        if state == ALL_OFF:
            return False
        return self.toggle_prefer_off

    def at_least_one_is_on(self) -> bool:
        """Return True if at least one light is on"""
        return self.max_u16() > 0

    def all_are_on(self) -> bool:
        """Return True if all lights are on"""
        return self.min_u16() > 0

    def all_are_off(self) -> bool:
        """Return True if all lights are off"""
        return self.min_u16() == 0

    def send_telemetry(self):
        self.send_telemetry_u16(self.current_u16_value())

    def send_telemetry_f(self, value: float):
        if self.portid is None:
            return
        self.send_telemetry_u16(int(0xffff * value))

    def send_telemetry_u16(self, u16: int):
        if self.portid is None:
            return
        # TODO - fix resolution
        ival = u16 >> 6 # assume a 10bit PWM for now
        if board.CAN:
            # self.msg.setsender(self.id)
            payload = self.msg.payload
            # self.msg[0] = board.CAN.canid >> 8
            # self.msg[1] = board.CAN.canid & 0xff
            payload[3] = ival >> 8
            payload[4] = ival & 0xff
            payload[5] = u16 >> 8
            payload[6] = u16 & 0xff
            self.msg.send()
        # board.PRINT('Sending status to CAN for PWM {} - {} / {} - {} '.format(self.portid, self, ival, i16))
        # board.MQTT_PUBLISH('light/{}/{}/set'.format(board.LOCATION, self.portid), i16)
        # board.MQTT.publish('state/{}'.format(self.portid), str(u16>>8))
        board.MQTT.publish('state/{}'.format(self.portid), f'{{"state": "{u16 == 0 and "OFF" or "ON"}", "brightness": {u16>>8}}}')

    def run_next_dimstep(self):
        """Set next dimlevel for smooth dimming to finally reach self.dimtovalue."""
        ival = self.pwm.duty_u16()
        # Pick nice step size for smooth dimming
        if self._dimstepf == 0.0:
            ds = int(ival * dimstep_scale)
        else:
            self._dimfvalue += self._dimstepf
            ival = self.f_to_u16(self._dimfvalue)
            ds = ival - self.pwm.duty_u16()

        ds = min(dimstep_max, max(dimstep_min, ds)) # about 200 ms when min step is 10
        remaining_counts = self.dimtovalue - ival
        if board.DEBUG > 3:
            print('pwm: {:2d}, iv: {:4d}, ds: {:3d}, remaining: {:4d}'.format(self.portid, ival, ds, remaining_counts))
        if abs(remaining_counts) <= ds:
            if board.DEBUG > 4:
                print('  end of dimming - remaining = {}, setting to {}'.format(remaining_counts, self.dimtovalue))
            # Accepting the PWM value takes a while, probably until the end of the phase.
            # So in the order of a few milliseconds (up to 10 with 100 Hz pwm frequency)
            # However, simply setting is OK, it will come there sooner or later.
            self.set_u16(self.dimtovalue)
            self.dimtovalue = _FINISHED_DIMMING
            self._dimstepf = 0.0
            # if remaining_counts == 0:
            #     # reached target
            #     self.send_telemetry()
            #     self.dimtovalue = _FINISHED_DIMMING
            return
        if remaining_counts > 0:
            self.set_u16_no_telemetry(ival + ds)
        else:
            self.set_u16_no_telemetry(ival - ds)

    def dim_u16(self, u16: int):
        """dim in u16 units (0..0xffff), return False if value is directly set, return True otherwise (dimming)"""
        value = valid_u16(u16)
        if self.dimtovalue == NODIMMING:
            self.set_u16(value)
            return False
        if abs(self.current_u16_value()-value) < 20: # arbritary number, but less then 1% change of intensity
            self.dimtovalue = _FINISHED_DIMMING
            self._dimstepf = 0.0
            self.set_u16(value)
            return False
        self.dimtovalue = value
        if board.DEBUG > 4:
            print('Start dimming {}'.format(self.portid))
        start_dimming.set()
        return True

    def dim_u8(self, u8: int):
        """dim in u8 units (0..0xff), return False if value is directly set, return True otherwise (dimming)"""
        value = valid_u16(u8 << 8 | u8)
        return self.dim_u16(value)

    def dimf(self, v):
        """dim to values from 0..1"""
        self._dimfvalue = self._fval
        self._fval = v
        self._dimstepf = (v - self._dimfvalue) / 20
        u16 = self.f_to_u16(v)
        board.PRINTF("dimf {:.2f} -> {}", v, u16)
        return self.dim_u16(u16)

    def on(self):
        """Set intensity to lastintensity"""
        self.dim_u16(self.lastintensity)

    def off(self):
        """Set intensity to 0"""
        self.dim_u16(0)

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

    def mqtt_set_callback(self, topic, msg):
        board.PRINTF('MQTT callback for PWM {} got called by MQTT: {} // {} - {}', self.portid, topic, msg, self)
        try:
            value = int(msg)
            value = min(255, max(0, value))
            self.dim_u16(value << 8 | value) # convert to 0..0xffff
            return
        except:
            pass
        try:
            msg = msg.upper()
            if msg == '{"STATE": "OFF"}' or msg == 'OFF':
                self.dim_u16(0)
                return
            if msg == '{"STATE": "ON"}' or msg == 'ON':
                self.on()
                return
        except:
            pass

        # simple JSON parser for  {"state":"ON","brightness":69}
        msg = msg.upper().replace(' ', '')

        statepos = msg.find('"STATE":"')
        if statepos >= 0:
            board.PRINTF('MQTT callback for PWM {} got STATE: {}', self.portid, msg[statepos+9:statepos+12])
            if msg[statepos+9:statepos+12] == 'OFF':
                self.dim_u16(0)
                return

        brightnesspos = msg.find('"BRIGHTNESS":')
        if brightnesspos >= 0:
            try:
                apos = brightnesspos + 13
                epos = apos
                while epos < len(msg) and msg[epos] in '0123456789':
                    epos += 1
                value = int(msg[apos:epos])
                value = min(255, max(0, value))
                self.dim_u8(value)
                return
            except:
                pass

        if statepos >= 0:
            # got STATE != "OFF" but not BRIGHTNESS, so just set the state
            self.on()
            return

        board.PRINTF('MQTT callback ERROR for PWM {}: {} // {}', self.portid, topic, msg)
        board.MQTT.publish('error/{}'.format(self.portid), 'BAD payload for set // {} - {}'.format(self.portid, msg))
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

    def current_u16_value(self):
        """Current value of a PWM List it the maximum of all its PWMs"""
        return self.max_u16()

    def append(self, pwm):
        self.pwms.append(pwm)

    def set_u16_no_telemetry(self, u16):
        for p in self.pwms:
            p.set_u16_no_telemetry(u16)
        return u16

    def send_telemetry(self):
        for p in self.pwms:
            p.send_telemetry()

    def max_u16(self):
        """get max value of all PWMs"""
        return max([p.current_u16_value() for p in self.pwms])

    def min_u16(self):
        """Return min value of all PWMs"""
        return min([p.current_u16_value() for p in self.pwms])

    def pwm_state(self) -> int:
        """Return on of ALL_ON, ALL_OFF, SOME_ON. The latter value is only interesting for a list of PWM"""
        min = self.min_u16()
        if mini > 0:
            return ALL_ON
        max = self.max_u16()
        if max == 0:
            return ALL_OFF
        return SOME_ON


    def dim_u16(self, value):
        ret = False
        for p in self.pwms:
            ret |= p.dim_u16(value)
        return ret

    def set_u16(self, ival):
        for p in self.pwms:
            p.set_u16(ival)

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

class xxxxSceneEntry:
    def __init__(self, pwm, rawvalue):
        self.pwm = pwm
        self.rawvalue =  rawvalue

class xxxxScene(PWM):
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
            e.pwm.dim_raw(e.rawvalue)

    def off(self):
        """turn scene off"""
        for e in self.entries.values():
            e.pwm.dim_raw(0)

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

    def dim_raw(self, value):
        if value > 0:
            self.on()
        else:
            self.off()

    def set_raw(self, value):
        self.dim_raw(value)

    def current_raw_value(self):
        return self.maxi()

    def maxi(self):
        return max([p.pwm.current_raw_value() for p in self.entries.values()])

    def mini(self):
        """Get min intensity, ignore LEDs that are switched off in this scene"""
        mini = 0xffff
        for p in self.entries.values():
            if p.rawvalue > 0:
                mini = min(mini, p.pwm.current_raw_value())
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
            p.dimtovalue = p.current_u16_value()

    # since we have just set the PWM we can tell how long it will take until the next value
    # will be accepted

    # could use some 10% margin here but there is also the python runtime
    # And if we are slightly faster than the PWM it shouldn't hurt. Worst case
    # we would skip one setting around the end of the dimming process
    # dimdelay = max(1, 1100 // pwm_freq)

    dimdelay_when_dimming = max(1, 1000 // pwm_freq)
    if board.DEBUG > 4:
        print('dimdelay when dimming = {}'.format(dimdelay_when_dimming))

    while True:
        isdimming = False
        for p in board.PWMs.pwms:
            if p.dimtovalue >= 0:
                isdimming = True
                p.run_next_dimstep()
        # ask other async tasks to delay their execution to ensure smooth and uniterrupted dimming
        board.PWM_IS_DIMMING = isdimming

        # if we are not dimming anymore, call the end of dimming callbacks
        if not isdimming:
            for cb in eod_callbacks:
                cb()


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
            # seems that we have finished dimming, wait for next dimming command
            start_dimming.clear()
            if board.DEBUG > 2:
                print('stopped dimming, waiting for start_dimming event()')
            await start_dimming.wait()
            if board.DEBUG > 3:
                print('return from start_dimming waiter')


# board.BACKGROUND_RUNNERS.append(_next_dim_step_task())

asyncio.create_task(_next_dim_step_task())

### Handle PWM callbacks

class _badPWMClass: # used to avoid the need of error catching in CAN callbacks
    def dim_u16(self, _):
        pass
    def on(self):
        pass
    def off(self):
        pass
    def toggle(self):
        pass
    def set_dimstep(self, _):
        pass
    def set_gamma(self, _):
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

if board.CAN is not None:
    board.CAN.register(pwmcode.SET_INTENSITY16, 4, 4, lambda msg: _getpwm(msg).dim_u16(msg.u16(2)))
    board.CAN.register(pwmcode.SET_INTENSITY_NATIVE, 4, 4, lambda msg: _getpwm(msg).dim_raw(msg.u16(2)))
    board.CAN.register(pwmcode.ON, 2, 2, lambda msg: _getpwm(msg).on())
    board.CAN.register(pwmcode.OFF, 2, 2, lambda msg: _getpwm(msg).off())
    board.CAN.register(pwmcode.TOGGLE, 2, 2, lambda msg: _getpwm(msg).toggle())

