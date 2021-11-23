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
import uasyncio as asyncio

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
    def __init__(self, name, sensorid, pin, poll_intervall_in_ms, background_task=None) -> None:
        # pylint: disable=redefined-outer-name
        self.name = name
        self.sensorid = sensorid
        self.pin = pin
        if poll_intervall_in_ms is None:
            poll_intervall_in_ms = poll_5_minutes
        self.poll_intervall_in_ms = poll_intervall_in_ms
        # TODO: do we really need fast? Go and write your own async() if needed.
        self.is_fast = False # can interrupt PWM dimming
        board.SENSORSs.register(sensorid, self)
        if background_task is None:
            background_task = self.sensor_task()
        board.BACKGROUND_RUNNERS.append(background_task)

    def __repr__(self) -> str:
        if isinstance(self.sensorid, int):
            ids = hex(self.sensorid)
        else:
            ids = 'None'
        return '<{}:{}.{}>'.format(self.__class__.__name__, ids, self.pin)

    def proclaim(self): # pylint: disable=no-self-use
        return None

    def run(self): # pylint: disable=no-self-use
        return None

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
    """Temperature sensor"""
    def __init__(self, sensorid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__('DHT', sensorid, pin, poll_intervall_in_ms)
        self.dht = dht.DHT22(machine.Pin(pin))
        self.msg = can.makemessage(canid.DATALOGGER_AM2302, 7)
        self.msg.setsender(self.sensorid)

    def proclaim(self):
        super().proclaim()

    #async def dht_task(self):
    #    asyncio.run(self.sensor_task())

    def run(self):
        #print('Measure {}'.format(self.sensorid))
        # self.msg.setsender(self.sensorid)
        # if board.CAN is None:
        #     return
        self.dht.measure()
        # t = int(10*self.dht.temperature()+0.5)
        # h = int(10*self.dht.humidity()+0.5)
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


class Brightness(Sensor):
    """Analog brighness sensors, 0 is dark, 0xff is maximum brightness"""
    def __init__(self, sensorid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__('Brightness', sensorid, pin, poll_intervall_in_ms)
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
