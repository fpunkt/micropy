"""
Misc Sensors

This file uses Timer(1)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import uasyncio as asyncio
import machine
import dht
import can

class PolledDeviceList:
    def __init__(self):
        self.devices = []

    def append(self, device):
        self.devices.append(device)

    def dump(self):
        print('{} entries'.format(len(self.devices)))
        for d in self.devices:
            print('  ', d)


polled_devices = PolledDeviceList()


class PolledDevice:
    def __init__(self, packetid, sensorid, poll_intervall_in_ms):
        self.packetid = packetid
        self.sensorid = sensorid
        if poll_intervall_in_ms < 1000:
            poll_intervall_in_ms = 1000
        self.poll_intervall_in_ms = poll_intervall_in_ms
        polled_devices.append(self)

    def __repr__(self):
        return '<{} poll interval={} ms>'.format(
            self.__class__.__name__,
            self.poll_intervall_in_ms)

    def send(self, payload):
        if can.CANDevice is None:
            return
        bytearray = [
            (can.CANDevice.canid >> 8) & 0xff, can.CANDevice.canid & 0xff,
            self.sensorid] + payload
        can.CANDevice.send(self.packetid, bytearray)

    def read(self):
        """poll is called in the background. The function should return max 4 bytes payload"""
        # pylint: disable=no-self-use
        return [1, 2]

    def measure(self):
        # print('measure', self)
        try:
            data = self.read()
        except: # pylint: disable=bare-except
            return
        if data is None:
            return
        self.send(data)

    async def poll_task(self):
        while True:
            self.measure()
            asyncio.sleep_ms(self.poll_intervall_in_ms)


class WDT(PolledDevice):
    """Triggers the watchdog. Does not send any message, is simply sharing
    the timer with other polled devices"""
    def __init__(self, poll_intervall_in_ms=2000):
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

    def read(self):
        self.dht.measure()
        t = int(10*self.dht.temperature()+0.5)
        h = int(10*self.dht.humidity()+0.5)
        return [h>>8, h & 0xff, t >>8, t & 0xff]
