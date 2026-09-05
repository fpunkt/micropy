"""
AM2302 sensor interface, sensor connected via GPIO pin.
This module uses the micropython built-in dht module and sends the data via CAN bus to the datalogger.
"""

import board
import can
import canid
import sensors
import dht
import asyncio

class AM2302(sensors.Sensor):
    def __init__(self, portid, pin, poll_intervall_in_ms=None, background_task=None) -> None:
        if poll_intervall_in_ms is None:
             poll_intervall_in_ms = 5 * 60 * 1000 # once every 5 minutes
        super().__init__(portid, pin, poll_intervall_in_ms, background_task)
        self.name = 'AM2302'
        self.dht = dht.DHT22(pin)
        self.msg = can.makemessage(canid.DATALOGGER_AM2302, 7)
        self.msg.setsender(self.portid)

    async def poll(self):
        try:
            self.dht.measure()
            await asyncio.sleep_ms(2000)  # wait for the sensor to finish measuring
        except:
            self.read_error()
            raise

    def update_payload(self):
        t = int(10*self.dht.temperature())
        h = int(10*self.dht.humidity())
        # print('T={} ({}), H={} ({})'.format(t, type(t), h, type(h)))
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = h >> 8
            payload[4] = h & 0xff
            payload[5] = t >> 8
            payload[6] = t & 0xff

        board.MQTT.publish("state/" + str(self.portid), f'{{t={self.dht.temperature():.1f}, h={self.dht.humidity():.1f}}}')
