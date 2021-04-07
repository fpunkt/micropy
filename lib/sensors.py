"""
Misc Sensors

This file uses Timer(1)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import utime
import machine
import dht
import can
import micropython

class PolledDeviceList:
    def __init__(self):
        self.devices = []
        self.timer = machine.Timer(1)
        self.stopped = False
        self._next_pol_ref = self._next_poll
        self._irq_ref = self._irq

    def append(self, device):
        self.devices.append(device)

    def _next_poll(self, _):
        # print('running next poll')
        if len(self.devices) == 0:
            return
        ticks = utime.ticks_ms()
        for d in self.devices:
            if utime.ticks_diff(d.next_call, ticks) <= 0:
                try:
                    d.measure()
                    d.next_call = utime.ticks_add(ticks, d.poll_intervall_in_ms)
                except: # pylint: disable=bare-except
                    d.next_call = utime.ticks_add(ticks, 1000)
            else:
                break
        # print('handled all sensors')
        if self.stopped:
            return
        self.devices = sorted(self.devices, key=lambda x: x.next_call)

        wait_ms = utime.ticks_diff(self.devices[0].next_call, ticks)
        if wait_ms <= 0:
            wait_ms = 1000
        # print('schedule next for ', wait_ms)
        self.timer.init(period=wait_ms, mode=machine.Timer.ONE_SHOT, callback=self._irq_ref)
        # print('scheduled next for ', wait_ms)
        #machine.idle()

    def next_poll(self):
        self._next_poll(None)

    def _irq(self, _):
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


polled_devices = PolledDeviceList()


class PolledDevice:
    def __init__(self, packetid, sensorid, poll_intervall_in_ms):
        self.packetid = packetid
        self.sensorid = sensorid
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

    def send(self, payload):
        if can.CANDevice is None:
            return
        bytearray = [
            (can.CANDevice.id >> 8) & 0xff, can.CANDevice.id & 0xff,
            self.sensorid] + payload
        can.CANDevice.send(self.packetid, bytearray)

    def poll(self):
        """poll is called in the background. The function should return max 4 bytes payload"""
        # pylint: disable=no-self-use
        return [1, 2]

    def measure(self):
        # print('measure', self)
        try:
            data = self.poll()
        except: # pylint: disable=bare-except
            return
        if data is None:
            return
        self.send(data)

class PingDevice(PolledDevice):
    """Send ping messages"""
    def __init__(self, poll_intervall_in_ms=300*1000):
        super().__init__(can.CANID_PING, 0, poll_intervall_in_ms)

    def send(self, _):
        can.sendping()

class WDT(PolledDevice):
    """Triggers the watchdog. Does not send any message, is simply sharing
    the timer with other polled devices"""
    def __init__(self, poll_intervall_in_ms=4000):
        super().__init__(0, 0, poll_intervall_in_ms)
        self.wdt = machine.WDT(timeout=2*poll_intervall_in_ms)

    def send(self, _):
        self.wdt.feed()

    def trigger(self):
        self.wdt.feed()


class DHT(PolledDevice):
    """Temperature sensor"""
    def __init__(self, pin, sensorid, poll_intervall_in_ms=60000):
        super().__init__(can.CANID_DATALOGGER_AM2302, sensorid, poll_intervall_in_ms)
        self.dht = dht.DHT22(pin)

    def poll(self):
        self.dht.measure()
        t = int(10*self.dht.temperature()+0.5)
        h = int(10*self.dht.humidity()+0.5)
        return [h>>8, h & 0xff, t >>8, t & 0xff]
