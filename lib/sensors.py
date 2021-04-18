"""
Misc Sensors

This file uses virtual timers (-1)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods

import utime
import machine
import dht
import board
import cancommon
import micropython
import pwm

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const

poll_1_minute = const(1 * 60 * 1000)
poll_5_minutes = const(5 * 60 * 1000)

default_poll_time = const(poll_5_minutes)

# external functions (like dimming) can temporarily disable sensor accquisition (looks nicer)

class PolledDeviceList:
    def __init__(self):
        self.devices = []
        self.timer = machine.Timer(-1)
        self.stopped = False
        self.debug = False
        self._next_pol_ref = self._next_poll
        self._irq_ref = self._timer_irq
        self._count = 0

    def append(self, device):
        self.devices.append(device)

    def proclaim(self):
        for d in self.devices:
            d.proclaim()

    def _next_poll(self, _):
        """Poll device. This code is run outside IRQ context (so save to malloc and floating point)"""
        if pwm.dimlist.isdimming:
            # don't block dimming, doesn't look nice ...
            self.timer.init(period=200, mode=machine.Timer.ONE_SHOT, callback=self._irq_ref)
            return

        if self.stopped:
            return
        if self.debug:
            print('PolledDeviceList: running next poll', self._count)
            self._count += 1
        if len(self.devices) == 0:
            return
        ticks = utime.ticks_ms()
        for d in self.devices:
            if utime.ticks_diff(d.next_call, ticks) <= 0:
                try:
                    if self.debug:
                        print('    Running', d)
                    d.measure_and_send()
                    d.next_call = utime.ticks_add(ticks, d.poll_intervall_in_ms)
                except: # pylint: disable=bare-except
                    d.next_call = utime.ticks_add(ticks, 5000)
            else:
                break
        # print('handled all sensors')
        if self.stopped:
            return
        self.devices = sorted(self.devices, key=lambda x: x.next_call)

        wait_ms = utime.ticks_diff(self.devices[0].next_call, ticks)
        if wait_ms <= 0:
            wait_ms = 1000
        if self.debug:
            print('    schedule next for ', wait_ms)
        self.timer.init(period=wait_ms, mode=machine.Timer.ONE_SHOT, callback=self._irq_ref)
        # print('scheduled next for ', wait_ms)
        #machine.idle()

    def next_poll(self):
        self._next_poll(None)

    def _timer_irq(self, _):
        try:
            micropython.schedule(self._next_pol_ref, 1)
        except: # pylint: disable=bare-except
            # schedule queue is full, try again later
            self.timer.init(period=100, mode=machine.Timer.ONE_SHOT, callback=self._irq_ref)

    def dump(self):
        print('{} entries'.format(len(self.devices)))
        for d in self.devices:
            print('  ', d)

    def stop(self):
        """Stop polling"""
        self.stopped = True

    def start(self):
        self.stopped = False
        self.next_poll()

    def clear(self):
        """Remove all devices from list"""
        self.devices.clear()



polled_devices = PolledDeviceList()

def start():
    polled_devices.start()

def proclaim():
    polled_devices.proclaim()

def stop():
    polled_devices.stop()

class PolledDevice:
    def __init__(self, packetid, sensorid, poll_intervall_in_ms):
        self.packetid = packetid
        self.sensorid = sensorid
        # if poll_intervall_in_ms is None:
        #     poll_intervall_in_ms = default_poll_time
        board.register(sensorid, self)
        if poll_intervall_in_ms < 1000:
            poll_intervall_in_ms = 1000
        self.poll_intervall_in_ms = poll_intervall_in_ms
        self.next_call = utime.ticks_add(utime.ticks_ms(), poll_intervall_in_ms)
        polled_devices.append(self)

    def __repr__(self):
        return '<{} poll interval={} ms, next in {} ms>'.format(
            self.__class__.__name__,
            self.poll_intervall_in_ms,
            utime.ticks_diff(self.next_call, utime.ticks_ms()))

    def proclaim(self):
        """tell others that we are online"""

    # def send(self, payload):
    #     if board.CAN is None:
    #         return
    #     send(self.packetid, self.sensorid, payload)
#
    # def read(self):
    #     """poll is called in the background. The function should return max 4 bytes payload"""
    #     # pylint: disable=no-self-use
    #     return [1, 2]

    def measure_and_send(self):
        cancommon.Badmessage.send()

class PingDevice(PolledDevice):
    """Send ping messages"""
    def __init__(self, poll_intervall_in_ms=poll_5_minutes):
        super().__init__(0, 0, poll_intervall_in_ms)

    def measure_and_send(self):
        cancommon.send_ping(board.CAN)

class WDT(PolledDevice):
    """Triggers the watchdog. Does not send any message, is simply sharing
    the timer with other polled devices"""
    def __init__(self, poll_intervall_in_ms=4000):
        super().__init__(0, 0, poll_intervall_in_ms)
        self.wdt = machine.WDT(timeout=2*poll_intervall_in_ms)

    def measure_and_send(self):
        pass

    def send(self, _):
        self.wdt.feed()

    def trigger(self):
        self.wdt.feed()

class DHT(PolledDevice):
    """Temperature sensor"""
    def __init__(self, sensorid, pin, poll_intervall_in_ms=poll_5_minutes):
        super().__init__(cancommon.CANID_DATALOGGER_AM2302, sensorid, poll_intervall_in_ms)
        self.dht = dht.DHT22(machine.Pin(pin))
        self.msg = cancommon.makemessage(cancommon.CANID_DATALOGGER_AM2302, 7)
        self.msg.setsender(self.sensorid)

    def proclaim(self):
        if board.MQTT is not None:
            board.MQTT.publish_sensor_status("TempHum", self.sensorid, "ON")

    def measure_and_send(self):
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
        super().__init__(cancommon.CANID_DATALOGGER_BRIGHTNESS_SENSOR_8, sensorid, poll_intervall_in_ms)
        self.adc = machine.ADC(machine.Pin(pin))
        self.adc.width(machine.ADC.WIDTH_9BIT)
        self.last_read = 0
        self.last_read_pwm_off = 0

    def read(self):
        self.last_read = 0xff - (self.adc.read() >> 1) # 8 bit

        if pwm.ALL.maxi() == 0:
            self.last_read_pwm_off = self.last_read
        return self.last_read

    def measure_and_send(self):
        self.read()
        if board.MQTT is not None:
            board.MQTT.publish_sensor_state("bright", self.sensorid,
                '{{"brightess": {}, "dark": {}}}'.format(self.last_read, self.last_read_pwm_off))
