"""
Misc Sensors

Sensors are polled in the background using asyncio.

Add sensors simply by defining them. Accquisition starts automatically.

Example:

  temperature = sensors.DHT(16, 21, poll_intervall_in_ms=sensors.poll_1_minute)

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods

import machine
import dht
import board
import can
import canid
import canerror
import uasyncio as asyncio
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

poll_1_minute = const(1 * 60 * 1000)
poll_2_minutes = const(2 * 60 * 1000)
poll_5_minutes = const(5 * 60 * 1000)

default_poll_time = const(poll_5_minutes)

class WDT:
    """Triggers the watchdog. Does not send any message, is simply sharing
    the timer with other polled devices"""
    def __init__(self, poll_intervall_in_ms=2000):
        self.repeat_ms = poll_intervall_in_ms
        self.wdt = None

    def enable(self):
        if board.DEBUG:
            print('\033[38;5;226mStaring watchdog, {:.1f} seconds\033[0m'.format(self.repeat_ms/1000.0))
        self.wdt = machine.WDT(timeout=2*self.repeat_ms)

    async def watchdog_task(self):
        while True:
            if self.wdt:
                self.wdt.feed()
            await asyncio.sleep_ms(self.repeat_ms)

    def trigger(self):
        if self.wdt:
            self.wdt.feed()

board.WD = WDT()
board.BACKGROUND_RUNNERS.append(board.WD.watchdog_task())


class Sensor:
    def __init__(self, name, portid, pin, poll_intervall_in_ms, background_task=None) -> None:
        # pylint: disable=redefined-outer-name
        self.name = name
        self.portid = portid
        self.pin = pin
        if poll_intervall_in_ms is None:
            poll_intervall_in_ms = poll_5_minutes
        self.poll_intervall_in_ms = poll_intervall_in_ms
        # TODO: do we really need fast? Go and write your own async() if needed.
        self.is_fast = False # can interrupt PWM dimming
        board.SENSORSs.register(portid, self)
        if background_task is None:
            background_task = self.sensor_task()
        board.BACKGROUND_RUNNERS.append(background_task)

    def __repr__(self) -> str:
        if isinstance(self.portid, int):
            ids = hex(self.portid)
        else:
            ids = 'None'
        return '<{}:{}.{}>'.format(self.__class__.__name__, ids, self.pin)

    def proclaim(self): # pylint: disable=no-self-use
        return None

    def mqtt_setup_and_proclaim(self, topic):
        """setup mqtt state and proclaim on MQTT"""
        if board.MQTT:
            s = '{}/{}/{}/'.format(topic, board.LOCATION, self.sensorid)
            self._mqtt_state_topic = s + 'state'
            fsmqtt.publish(s + "status", "ON")

    def run(self): # pylint: disable=no-self-use
        return None

    def read_error(self):
        can.cancommon.errormessage([canerror.SENSOR_READ_ERROR, self.portid])

    def disabled_error(self):
        can.errormessage([canerror.SENSOR_DISABLED, self.portid])

    async def sensor_task(self):
        self.proclaim()
        while True:
            nextrun_in_ms = self.poll_intervall_in_ms
            if board.PWM_IS_DIMMING and not self.is_fast:
                # minor delay in order to have smooth dimming. Used for slow sensors
                nextrun_in_ms = 2
            else:
                try:
                    self.run()
                except Exception as e: # pylint: disable=bare-except, broad-except
                    if board.DEBUG:
                        print('Exception from {}: {}'.format(self, e))
            await asyncio.sleep_ms(nextrun_in_ms)


class DHT(Sensor):
    """Temperature sensor
    3 to 5V power and I/O
    2.5mA max current use during conversion (while requesting data)
    Good for 0-100% humidity readings with 2-5% accuracy
    Good for -40 to 80°C temperature readings ±0.5°C accuracy
    No more than 0.5 Hz sampling rate (once every 2 seconds)
    """
    def __init__(self, portid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__('DHT', portid, pin, poll_intervall_in_ms)
        self.dht = dht.DHT22(machine.Pin(pin))
        self.msg = can.makemessage(canid.DATALOGGER_AM2302, 7)
        self.msg.setsender(self.portid)

    def proclaim(self):
        super().proclaim()

    def measure(self):
        return self.dht.measure()

    def decode(self):
        """Return T10, H10 after calling dht.measure(). T and H have to be divided by 10"""
        h = self.dht.buf[0] << 8 | self.dht.buf[1]
        t = (self.dht.buf[2] & 0x7F) << 8 | self.dht.buf[3]
        if self.dht.buf[2] & 0x80:
            t = -t
        return t, h

    def run(self):
        try:
            self.dht.measure()
        except:
            self.read_error()
            raise
        # decode ourself to avoid malloc
        h = self.dht.buf[0] << 8 | self.dht.buf[1]
        t = (self.dht.buf[2] & 0x7F) << 8 | self.dht.buf[3]
        if self.dht.buf[2] & 0x80:
            t = -t
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = h >> 8
            payload[4] = h & 0xff
            payload[5] = t >> 8
            payload[6] = t & 0xff
            self.msg.send()

class DHT11(Sensor):
    """
    3 to 5V power and I/O
    2.5mA max current use during conversion (while requesting data)
    Good for 20-80% humidity readings with 5% accuracy
    Good for 0-50°C temperature readings ±2°C accuracy
    """
    def __init__(self, portid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__('DHT11', portid, pin, poll_intervall_in_ms)
        self.dht = dht.DHT11(machine.Pin(pin))
        self.msg = can.makemessage(canid.DATALOGGER_AM2302, 7)
        self.msg.setsender(self.portid)

    def proclaim(self):
        super().proclaim()

    def decode(self):
        """Return T10, H10 after calling dht.measure(). T and H have to be divided by 10"""
        return 10 * self.dht.buf[2], 10 * self.dht.buf[0]

    def run(self):
        try:
            self.dht.measure()
        except:
            self.read_error()
            raise
        # decode ourself to avoid malloc
        h = 10 * self.dht.buf[0]
        t = 10 * self.dht.buf[2]
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = h >> 8
            payload[4] = h & 0xff
            payload[5] = t >> 8
            payload[6] = t & 0xff
            self.msg.send()


class AnalogBrightness(Sensor):
    """Analog brighness sensors, 0 is dark, 0xff is maximum brightness"""
    def __init__(self, portid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__('Brightness', portid, pin, poll_intervall_in_ms)
        self.adc = machine.ADC(machine.Pin(pin))
        self.adc.width(machine.ADC.WIDTH_9BIT)
        self.last_read = 0
        self.last_read_pwm_off = 0
        self.msg = can.makemessage(canid.DATALOGGER_BRIGHTNESS_SENSOR_8, 5)

    def proclaim(self):
        super().proclaim()

    def read(self):
        self.last_read = 0xff - (self.adc.read() >> 1) # 8 bit
        if board.PWMs.maxi() == 0:
            self.last_read_pwm_off = self.last_read
        return self.last_read

    def run(self):
        self.read()
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = self.last_read
            payload[4] = self.last_read_pwm_off
            self.msg.send()
