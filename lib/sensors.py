"""
Misc Sensors

Sensors are polled in the background using asyncio.

Add sensors simply by defining them. Accquisition starts automatically.

Example:

  temperature = sensors.DHT(16, 21, poll_intervall_in_ms=sensors.poll_1_minute)

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods

import port
import machine
import dht
import board
import can
import canid
import canerror
import asyncio
import sys
try:
    import fsmqtt
except:
    fsmqtt = None

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

def minutes(n):
    """Convert to milliseconds"""
    return int(n*60000)

poll_30_seconds = const(30 * 1000)
poll_1_minute = const(1 * 60 * 1000)
poll_2_minutes = const(2 * 60 * 1000)
poll_5_minutes = const(5 * 60 * 1000)

default_poll_time = const(poll_5_minutes)


# TODO: background_task is not used? At least not tested. Remove it?

class Sensor(port.Port):
    """Sensor is the baseclass for devices that need regular polling. You should overload functions
    aysnc poll: start a measurement, return when update_payload will do something useful
    update_payload() patch self.msg so it can be send
    """
    def __init__(self, portid, pin, poll_intervall_in_ms, background_task=None) -> None:
        super().__init__(portid, pin)
        if poll_intervall_in_ms is None or poll_intervall_in_ms == 0:
            poll_intervall_in_ms = poll_5_minutes

        self.poll_intervall_in_ms = poll_intervall_in_ms
        # TODO: do we really need fast? Go and write your own async() if needed.
        self.is_fast = False # can interrupt PWM dimming
        if background_task is None:
            background_task = self.sensor_task
        board.BACKGROUND_RUNNERS.append(background_task())

    def __repr__(self) -> str:
        return self._repr('poll_intervall: {} ms'.format(self.poll_intervall_in_ms))

    def proclaim(self): # pylint: disable=no-self-use
        # TODO: remove proclaim
        return None

    def mqtt_setup_and_proclaim(self, topic):
        """setup mqtt state and proclaim on MQTT"""
        board.MQTT.publish("status", "ON")

    async def poll(self): # pylint: disable=no-self-use
        """This function is called periodically. It should prepare a measurement and return
        when a call to self.update_payload() will do something useful."""
        return None

    def read_error(self):
        can.cancommon.errormessage([canerror.SENSOR_READ_ERROR, self.portid])

    # use port.send_disabled_error
    # def disabled_error(self):
    #     can.errormessage([canerror.SENSOR_DISABLED, self.portid])

    async def sensor_task(self):
        self.proclaim()
        while True:
            if board.PWM_IS_DIMMING and not self.is_fast:
                # delay sensor polling to ensure smooth dimming. Used for slow sensors
                await asyncio.sleep_ms(50)
                continue
            else:
                try:
                    await self.poll()
                    self.update_payload()
                    self.send_message()
                except Exception as e:
                    if board.DEBUG:
                        print('Exception from {}: {}'.format(self, e))
                        sys.print_exception(e)
                    await asyncio.sleep_ms(1000)
            if board.DEBUG > 2: 
                board.PRINTF('sensor {} going to sleep for {} ms', self, self.poll_intervall_in_ms)
            await asyncio.sleep_ms(self.poll_intervall_in_ms)
            if board.DEBUG > 2:
                board.PRINTF('sensor {} woke up after {} ms', self, self.poll_intervall_in_ms)


# ================================= DHT temperature sensors

class _DHT(Sensor):
    """Temperature sensor
    3 to 5V power and I/O
    2.5mA max current use during conversion (while requesting data)
    Good for 0-100% humidity readings with 2-5% accuracy
    Good for -40 to 80°C temperature readings ±0.5°C accuracy
    No more than 0.5 Hz sampling rate (once every 2 seconds)
    """
    def __init__(self, portid, pin, dht, poll_intervall_in_ms=poll_5_minutes):
        super().__init__(portid, pin, poll_intervall_in_ms)
        self.dht = dht
        self.msg = can.makemessage(canid.DATALOGGER_AM2302, 7)
        self.msg.setsender(self.portid)

    def proclaim(self):
        super().proclaim()

    def decode(self):
        """Return T10, H10 after calling dht.measure(). T and H have to be divided by 10"""
        raise NotImplemented

    def update_payload(self):
        if board.CAN is not None:
            t, h = self.decode()
            payload = self.msg.payload
            payload[3] = h >> 8
            payload[4] = h & 0xff
            payload[5] = t >> 8
            payload[6] = t & 0xff

    async def poll(self):
        self.dht.measure()
        return True


class DHT(_DHT):
    """Temperature sensor
    3 to 5V power and I/O
    2.5mA max current use during conversion (while requesting data)
    Good for 0-100% humidity readings with 2-5% accuracy
    Good for -40 to 80°C temperature readings ±0.5°C accuracy
    No more than 0.5 Hz sampling rate (once every 2 seconds)
    """
    def __init__(self, portid, pinid, poll_intervall_in_ms=poll_5_minutes):
        pin = machine.Pin(pinid)
        super().__init__(portid, pin, dht.DHT22(pin), poll_intervall_in_ms)

    def decode(self):
        """Return T10, H10 after calling dht.measure(). T and H have to be divided by 10"""
        h = self.dht.buf[0] << 8 | self.dht.buf[1]
        t = (self.dht.buf[2] & 0x7F) << 8 | self.dht.buf[3]
        if self.dht.buf[2] & 0x80:
            t = -t
        return t, h

class DHT11(_DHT):
    """
    3 to 5V power and I/O
    2.5mA max current use during conversion (while requesting data)
    Good for 20-80% humidity readings with 5% accuracy
    Good for 0-50°C temperature readings ±2°C accuracy
    """
    def __init__(self, portid, pinid, poll_intervall_in_ms=poll_5_minutes):
        pin = machine.Pin(pinid)
        super().__init__(portid, pin, dht.DHT11(pin), poll_intervall_in_ms)

    def decode(self):
        """Return T10, H10 after calling dht.measure(). T and H have to be divided by 10"""
        return 10 * self.dht.buf[2], 10 * self.dht.buf[0]


class AnalogBrightness(Sensor):
    """Analog brighness sensors, 0 is dark, 0xff is maximum brightness"""
    def __init__(self, portid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__(portid, pin, poll_intervall_in_ms)
        self.adc = machine.ADC(machine.Pin(pin))
        self.adc.width(machine.ADC.WIDTH_9BIT)
        self.last_read = 0
        self.last_read_pwm_off = 0
        self.msg = can.makemessage(canid.DATALOGGER_BRIGHTNESS_SENSOR_8, 5)

    def read(self):
        self.last_read = 0xff - (self.adc.read() >> 1) # 8 bit
        if board.PWMs.maxi() == 0:
            self.last_read_pwm_off = self.last_read
        return self.last_read

    async def poll(self):
        self.read()
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = self.last_read
            payload[4] = self.last_read_pwm_off
            self.msg.send()
