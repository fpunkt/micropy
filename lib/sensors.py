"""
Misc Sensors

Sensors are polled in the background using the schedule module.

Add sensors simply by defining them. Accquisition starts automatically.

Example:

  temperature = sensors.DHT(16, 21, poll_intervall_in_ms=sensors.poll_1_minute)
  sensors.proclaim()

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods

import machine
import dht
import board
import can
import canid
import schedule

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const

poll_1_minute = const(1 * 60 * 1000)
poll_5_minutes = const(5 * 60 * 1000)

default_poll_time = const(poll_5_minutes)

# external functions (like dimming) can temporarily disable sensor accquisition (looks nicer)

sensors = []

def proclaim():
    for sensor in sensors:
        sensor.proclaim()

# TODO: add schedule.startup(proclaim)

class PolledDevice(schedule.ScheduledItem):
    def __init__(self, label, packetid, sensorid, poll_intervall_in_ms, first_run_after_ms=100):
        if poll_intervall_in_ms < 1000:
            poll_intervall_in_ms = 1000
        super().__init__(label, repeat_ms=poll_intervall_in_ms, first_run_after_ms=first_run_after_ms)
        self.packetid = packetid
        self.sensorid = sensorid
        # if poll_intervall_in_ms is None:
        #     poll_intervall_in_ms = default_poll_time
        board.SENSORSs.register(sensorid, self)

    def proclaim(self):
        """tell others that we are online"""

    def run(self):
        can.Badmessage.send()

class PingDevice(PolledDevice):
    """Send ping messages"""
    def __init__(self, poll_intervall_in_ms=poll_5_minutes):
        super().__init__('ping', 0, 0xf0, poll_intervall_in_ms)

    def run(self):
        if board.CAN is not None:
            board.CAN.send_ping()
        if board.MQTT is not None:
            board.MQTT.publish('info/uptime/{}'.format(board.LOCATION), str(board.uptime_s()))

class WDT(PolledDevice):
    """Triggers the watchdog. Does not send any message, is simply sharing
    the timer with other polled devices"""
    def __init__(self, poll_intervall_in_ms=4000):
        super().__init__('watchdog', 0, 0xf1, poll_intervall_in_ms)
        print('\033[38;5;226mStaring watchdog, {:.1f} seconds\033[0m'.format(poll_intervall_in_ms/1000.0))
        self.wdt = machine.WDT(timeout=2*poll_intervall_in_ms)

    def run(self):
        self.wdt.feed()

    def trigger(self):
        self.wdt.feed()

def _name(name, sensorid, pin):
    return '{}:{}.{}'.format(name, sensorid, pin)

class DHT(PolledDevice):
    """Temperature sensor"""
    def __init__(self, sensorid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__(_name('DHT', sensorid, pin), canid.DATALOGGER_AM2302, sensorid, poll_intervall_in_ms)
        self.dht = dht.DHT22(machine.Pin(pin))
        self.msg = can.makemessage(canid.DATALOGGER_AM2302, 7)
        self.msg.setsender(self.sensorid)

    def proclaim(self):
        if board.MQTT is not None:
            board.MQTT.publish_sensor_status("TempHum", self.sensorid, "ON")

    def run(self):
        # self.msg.setsender(self.sensorid)
        # if board.CAN is None and board.MQTT is None:
        #     return
        self.dht.measure()
        t = int(10*self.dht.temperature()+0.5)
        h = int(10*self.dht.humidity()+0.5)
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = h >> 8
            payload[4] = h & 0xff
            payload[5] = t >> 8
            payload[6] = t & 0xff
            self.msg.send()

        if board.MQTT is not None:
            board.MQTT.publish_sensor_state("TempHum", self.sensorid,
                '{{"temperature": {:.1f}, "humidity": {:.1f}}}'.format(t/10.0, h/10.0))


class Brightness(PolledDevice):
    """Analog brighness sensors, 0 is dark, 0xff is maximum brightness"""
    def __init__(self, sensorid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__(_name('Brightness', sensorid, pin),
            canid.DATALOGGER_BRIGHTNESS_SENSOR_8, sensorid, poll_intervall_in_ms)
        self.adc = machine.ADC(machine.Pin(pin))
        self.adc.width(machine.ADC.WIDTH_9BIT)
        self.last_read = 0
        self.last_read_pwm_off = 0

    def read(self):
        self.last_read = 0xff - (self.adc.read() >> 1) # 8 bit

        if board.PWMs.maxi() == 0:
            self.last_read_pwm_off = self.last_read
        return self.last_read

    def run(self):
        self.read()
        if board.MQTT is not None:
            board.MQTT.publish_sensor_state("bright", self.sensorid,
                '{{"brightess": {}, "dark": {}}}'.format(self.last_read, self.last_read_pwm_off))



class RegisteredSensorIDs:
    def __init__(self):
        self.r = dict()
    def register(self, sensorid, sensor):
        if id in self.r:
            raise RuntimeError("id #{} is already registered as {} ({})".format(sensorid, self.r[sensorid], sensor))
        self.r[sensorid] = sensor

    def dump(self):
        for i, v in self.r:
            print("ID {:2d} = {}".format(i, v))

    def has_sensor(self, sensorid):
        return self.r.get(sensorid, None)

    def find(self, msg, withclass, sensortype=0xfe):
        p = msg.payload
        sensorid = 0xff
        if len(p) > 1:
            sensorid = p[1]
        d = self.r.get(sensorid, None)
        if d is None:
            if board.DEBUG:
                print('Device #{} not found'.format(sensorid))
            msg.bad_sensor_id()
            return None
        if withclass is None:
            return d
        if not isinstance(d, withclass):
            if board.DEBUG:
                print('Found ID #{} but wrong class {} (expected {})'.format(sensorid, d.__class__, withclass))
            msg.bad_sensor_type(sensortype)
            return None
        return d
