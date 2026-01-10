"""
Anschlusskeller

MQTT Client for Anschlusskeller, Gas- und Wasserzähler, ggf Licht.
"""

import board
board.LOCATION = 'ug-anschlusskeller'
board.VERSION = '2025-12-14'
board.DEBUG = 2
import fsmqtt

import machine
import net
import watchdog
import memstat
import asyncio
import irqio
import utime

class Anschlusskeller:
    def __init__(self):
        self.last_gas_value = 0
        self.last_wasser_value = 0
        # throttle messages
        self.last_gas_timestamp = 0
        self.last_wasser_timestamp = 0

        self.gas = IRQIO(0x01, machine.Pin(22, machine.Pin.IN), pullup=None)
        self.wasser = IRQIO(0x02, machine.Pin(23, machine.Pin.IN), pullup=True)

        # send a heartbeat every 5 minutes
        self.heartbeat = 5 * 60 * 1000
        self.interval = 5000
        
    async def run(self):
        # say hello
        board.PRINTF('Anschlusskeller started')
        lastprint = utime.ticks_ms()
        while True:
            await asyncio.sleep_ms(1000)
            now = utime.ticks_ms()
            if utime.ticks_diff(now, lastprint) < self.interval:
                continue
            lastprint = now
            if self.gas.counter != self.last_gas_value:
                self.send_gas_value()
            elif utime.ticks_diff(now, self.last_gas_timestamp) > self.heartbeat:
                self.send_gas_value()
            if self.wasser.counter != self.last_wasser_value:
                self.send_wasser_value()
            elif utime.ticks_diff(now, self.last_wasser_timestamp) > self.heartbeat:
                self.send_wasser_value()

    def send_gas_value(self):
        self.last_gas_timestamp = utime.ticks_ms()
        self.last_gas_value = self.gas.counter
        board.MQTT.publish('gas', self.gas.counter)
        board.PRINTF('Gas: {}', self.gas.counter)

    def send_wasser_value(self):
        self.last_wasser_timestamp = utime.ticks_ms()
        self.last_wasser_value = self.wasser.counter
        board.MQTT.publish('wasser', self.wasser.counter)
        board.PRINTF('Wasser: {}', self.wasser.counter)
        

class IRQIO(irqio.IRQIO):
    def __init__(self, portid, pinid, inverted=False, debounce_ms=20, pullup=True):
        super().__init__(portid, pinid, inverted=inverted, debounce_ms=debounce_ms, pullup=pullup)
        self.counter = 0

    async def run(self):
        board.PRINTF('IRQIO {} {}', self.portid, self.pinvalue)
        if self.pinvalue == 1:
            self.counter += 1
        return True

print("going to create anschlusskeller")
keller = Anschlusskeller()
print("created anschlusskeller")
asyncio.create_task(keller.run())

board.MQTT.ignore_topics('gas', 'wasser')

def _getvalue(_, msg, min=1, max=3600):
    """get value"""
    value = int(msg)
    board.PRINTF('Value: {}', value)
    if value < min:
        value = min
    if value > max:
        value = max
    return value

def _heartbeat(_, msg):
    """set heartbeat interval in seconds"""
    value = _getvalue(_, msg)
    board.PRINTF('Heartbeat: {}', value, min=5)
    keller.heartbeat = value * 1000
    board.MQTT.publish('info/heartbeat', value)

def _interval(_, msg):
    """set interval in seconds"""
    value = _getvalue(_, msg)
    board.PRINTF('Interval: {}', value)
    keller.interval = value * 1000
    board.MQTT.publish('info/interval', value)

board.MQTT.subscribe('set/interval', _interval)
board.MQTT.subscribe('set/heartbeat', _heartbeat)

print("going to connect to network")
board.NET.connect()
print("connected to network")
board.MQTT.connect()
print("connected to mqtt")

async def blue_led():
    last = 0
    while True:
        await asyncio.sleep(0.5)
        if board.MQTT.connected():
            blink = 500
        else:
            blink = 2000
        now = utime.ticks_ms()
        if utime.ticks_diff(now, last) < blink:
            continue
        last = now
        board.LED.toggle()


async def _mqtt_connected():
    keller.send_gas_value()
    keller.send_wasser_value()

board.MQTT.run_after_connect(_mqtt_connected)

# watchdog.start_later()
