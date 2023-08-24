"""
Main Code to control the I2C sensor stolen from ...

https://github.com/adafruit/micropython-adafruit-tsl2561/blob/master/tsl2561.py
"""

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

import machine
import time
import ustruct
import board
import can
import canid
import canerror
import sensors



class BrightnessTLS2561(sensors.Sensor):
    def __init__(self, portid, pin, i2c, poll_intervall_in_ms=sensors.poll_5_minutes):
        super().__init__('Brightness', portid, pin, poll_intervall_in_ms)


class TSL2561(sensors.Sensor):
    def __init__(self, portid, poll_intervall_in_ms=2000, tint=101):
        msg = 'Initialize I2C'
        try:
            msg = 'Initialize TSL2561'
            self.t = _TSL2561(i2c=board.I2C)
            msg = 'Setting T_int'
            self.set_tint(101)
            msg = 'Setting gain'
            self.t.gain(16)
        except Exception as e:
            if board.DEBUG:
                print('Cannot initialize TLS2561, failed during {}: {}'.format(msg, e))
            can.errormessage([canerror.SENSOR_DISABLED, portid])
            return
        super().__init__('TLS2561', portid, board.I2C_SDA_PIN, poll_intervall_in_ms)
        self.msg = can.makemessage(canid.DATALOGGER_BRIGHTNESS_SENSOR_TSL2561, 8)
        self.msg.setsender(self.portid)
        self.count = 0

    def set_tint(self, ms):
        valid = (13, 101, 404)
        try:
            i = valid.index(ms)
        except:
            raise ValueError("Bad integration time %s, must be one of %s", ms, valid)
        self.t.integration_time(ms)
        self._tint = i+1

    def run(self):
        try:
            l = self.t.read(raw=False)
            r = self.t.read(raw=True, autogain=True)
            lo = self.t.lux_orig(r)
            la = self.t.lux_ada(r)
        except Exception as e:
            if board.DEBUG:
                print('Read error on TLS2561: {}'.format(e))
            self.read_error()
            return
        self.count += 1
        print('{:5d} L = {} / lo = {} / la = {} --  {} g={}'.format(self.count, l, lo, la, r, self.t._gain))
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = r[0] >> 8
            payload[4] = r[0] & 0xff
            payload[5] = r[1] >> 8
            payload[6] = r[1] & 0xff

            flag = self._tint
            flag |= 0b00000100 if self.t._gain > 1 else 0
            flag |= 0b00001000 if board.PWMs.maxi() > 0 else 0
            payload[7] = flag

            self.msg.send()


_COMMAND_BIT = const(0x80)
_WORD_BIT = const(0x20)

_REGISTER_CONTROL = const(0x00)
_REGISTER_TIMING = const(0x01)
_REGISTER_THRESHHOLD_MIN = const(0x02)
_REGISTER_THRESHHOLD_MAX = const(0x04)
_REGISTER_INTERRUPT = const(0x06)
_REGISTER_ID = const(0x0A)
_REGISTER_CHANNEL0 = const(0x0C)
_REGISTER_CHANNEL1 = const(0x0E)

_CONTROL_POWERON = const(0x03)
_CONTROL_POWEROFF = const(0x00)

_INTERRUPT_NONE = const(0x00)
_INTERRUPT_LEVEL = const(0x10)

_INTEGRATION_TIME = {
#  time     hex     wait    clip    min     max     scale
    13:     (0x00,  15,     4900,   100,    4850,   0x7517),
    101:    (0x01,  120,    37000,  200,    36000,  0x0FE7),
    402:    (0x02,  450,    65000,  500,    63000,  1 << 10),
    0:      (0x03,  0,      0,      0,      0,      0),
}

_TIME_SCALE = {
    13:1 / 0.034,
    101: 1 / 0.252,
    402: 1,
}

class _TSL2561:
    _LUX_SCALE = (
    #       K       B       M
        (0x0040, 0x01f2, 0x01be),
        (0x0080, 0x0214, 0x02d1),
        (0x00c0, 0x023f, 0x037b),
        (0x0100, 0x0270, 0x03fe),
        (0x0138, 0x016f, 0x01fc),
        (0x019a, 0x00d2, 0x00fb),
        (0x029a, 0x0018, 0x0012),
    )

    def __init__(self, i2c, address=0x39):
        self.i2c = i2c
        self.address = address
        sensor_id = self.sensor_id()
        if not sensor_id & 0x10:
            raise RuntimeError("bad sensor id 0x{:x}".format(sensor_id))
        self._active = False
        self._gain = 1
        self._integration_time = 13
        self._update_gain_and_time()

    def _register16(self, register, value=None):
        register |= _COMMAND_BIT | _WORD_BIT
        if value is None:
            data = self.i2c.readfrom_mem(self.address, register, 2)
            return ustruct.unpack('<H', data)[0]
        data = ustruct.pack('<H', value)
        self.i2c.writeto_mem(self.address, register, data)

    def _register8(self, register, value=None):
        register |= _COMMAND_BIT
        if value is None:
            return self.i2c.readfrom_mem(self.address, register, 1)[0]
        data = ustruct.pack('<B', value)
        self.i2c.writeto_mem(self.address, register, data)

    def active(self, value=None):
        if value is None:
            return self._active
        value = bool(value)
        if value != self._active:
            self._active = value
            self._register8(_REGISTER_CONTROL,
                _CONTROL_POWERON if value else _CONTROL_POWEROFF)

    def gain(self, value=None):
        if value is None:
            return self._gain
        if value not in (1, 16):
            raise ValueError("gain must be either 1x or 16x")
        self._gain = value
        self._update_gain_and_time()

    def integration_time(self, value=None):
        if value is None:
            return self._integration_time
        if value not in _INTEGRATION_TIME:
            raise ValueError("integration time must be 0, 13ms, 101ms or 402ms")
        self._integration_time = value
        self._update_gain_and_time()

    def _update_gain_and_time(self):
        was_active = self.active()
        self.active(True)
        self._register8(_REGISTER_TIMING,
            _INTEGRATION_TIME[self._integration_time][0] |
            {1: 0x00, 16: 0x10}[self._gain]);
        self.active(was_active)

    def sensor_id(self):
        return self._register8(_REGISTER_ID)

    def _read(self):
        was_active = self.active()
        self.active(True)
        if not was_active:
            # if the sensor was off, wait for measurement
            time.sleep_ms(_INTEGRATION_TIME[self._integration_time][1])
        broadband = self._register16(_REGISTER_CHANNEL0)
        ir = self._register16(_REGISTER_CHANNEL1)
        self.active(was_active)
        return broadband, ir

    def lux_orig(self, channels):
        if self._integration_time == 0:
            raise ValueError(
                "can't calculate lux with manual integration time")
        broadband, ir = channels
        clip = _INTEGRATION_TIME[self._integration_time][2]
        if broadband > clip or ir > clip:
            raise ValueError("sensor saturated")
        scale = _INTEGRATION_TIME[self._integration_time][5] / self._gain
        channel0 = (broadband * scale) / 1024
        channel1 = (ir * scale) / 1024
        ratio = (((channel1 * 1024) / channel0 if channel0 else 0) + 1) / 2
        for k, b, m in self._LUX_SCALE:
            if ratio <= k:
                break
        else:
            b = 0
            m = 0
        return (max(0, channel0 * b - channel1 * m) + 8192) / 16384

    def lux_ada(self, channels):
        ch0, ch1 = channels
        if ch0 == 0:
            return None
        clip = _INTEGRATION_TIME[self._integration_time][2]
        if ch0 > clip or ch1 > clip:
            raise ValueError("sensor saturated")
        ratio = ch1 / ch0
        if 0 <= ratio <= 0.50:
            lux = 0.0304 * ch0 - 0.062 * ch0 * ratio**1.4
        elif ratio <= 0.61:
            lux = 0.0224 * ch0 - 0.031 * ch1
        elif ratio <= 0.80:
            lux = 0.0128 * ch0 - 0.0153 * ch1
        elif ratio <= 1.30:
            lux = 0.00146 * ch0 - 0.00112 * ch1
        else:
            lux = 0.0
        # Pretty sure the floating point math formula on pg. 23 of datasheet
        # is based on 16x gain and 402ms integration time. Need to scale
        # result for other settings.
        # Scale for gain.
        scale = _TIME_SCALE[self._integration_time] / self._gain
        print("lux, scale: ", lux, scale)
        # Scale for integration time.
        return lux * scale

    def read(self, autogain=False, raw=False):
        broadband, ir = self._read()
        if autogain:
            if self._integration_time == 0:
                raise ValueError(
                    "can't do autogain with manual integration time")
            new_gain = self._gain
            if broadband < _INTEGRATION_TIME[self._integration_time][3]:
                new_gain = 16
            elif broadband > _INTEGRATION_TIME[self._integration_time][4]:
                new_gain = 1
            if new_gain != self._gain:
                self.gain(new_gain)
                broadband, ir = self._read()
        if raw is True:
            return broadband, ir
        if raw is False:
            return self.lux_orig((broadband, ir))
        return self.lux_ada((broadband, ir))

    def threshold(self, cycles=None, min_value=None, max_value=None):
        if min_value is None and max_value is None and cycles is None:
            min_value = self._register16(_REGISTER_THRESHHOLD_MIN)
            max_value = self._register16(_REGISTER_THRESHHOLD_MAX)
            cycles = self._register8(_REGISTER_INTERRUPT)
            if not cycles & _INTERRUPT_LEVEL:
                cycles = -1
            else:
                cycles &= 0x0f
            return cycles, min_value, max_value
        was_active = self.active()
        self.active(True)
        if min_value is not None:
            self._register16(_REGISTER_THRESHHOLD_MIN, int(min_value))
        if max_value is not None:
            self._register16(_REGISTER_THRESHHOLD_MAX, int(max_value))
        if cycles is not None:
            if cycles == -1:
                self._register8(_REGISTER_INTERRUPT, _INTERRUPT_NONE)
            else:
                self._register8(_REGISTER_INTERRUPT,
                    min(15, max(0, int(cycles))) | _INTERRUPT_LEVEL)
        self.active(was_active)

    def interrupt(self, value):
        if value or value is None:
            raise ValueError("can only clear the interrupt")
        self.i2c.writeto(self.address, b'\x40')


# Those packages are identical.
TSL2561T = TSL2561
TSL2561FN = TSL2561
TSL2561CL = TSL2561


class TSL2561CS(TSL2561):
    # This package has different lux scale.
    _LUX_SCALE = (
    #       K       B       M
        (0x0043, 0x0204, 0x01ad),
        (0x0085, 0x0228, 0x02c1),
        (0x00c8, 0x0253, 0x0363),
        (0x010a, 0x0282, 0x03df),
        (0x014d, 0x0177, 0x01dd),
        (0x019a, 0x0101, 0x0127),
        (0x029a, 0x0037, 0x002b),
    )