"""
Anschlusskeller

MQTT Client for Anschlusskeller, Gas- und Wasserzähler, ggf Licht.
"""

import board
board.LOCATION = 'ug-anschlusskeller'
board.HOSTNAME = 'gaszaehler'
board.VERSION = '2026-08-31'
board.DEBUG = 2
import fsmqtt

import machine
import net
import watchdog
import memstat
import asyncio
import irqio
import utime
import pwm

p1 = pwm.PWM(0x01, 22)
p2 = pwm.PWM(0x02, 23)

PIN_GAS = 32        # corner PIN upper row towards 5V supply
PIN_WASSER = 34     # 2nd to corner
PIN_DOOR = 35       # 2 FREE (RX/TX) then 4th to corner

counter_offset = 0   # offset used to calculate the current value of the counter, since the counter is reset to 0 on each boot

class Anschlusskeller:
    def __init__(self):
        self.last_gas_value = 0
        self.last_wasser_value = 0
        # throttle messages
        self.last_gas_timestamp = 0
        self.last_wasser_timestamp = 0

        #self.gas = IRQIO(0x11, machine.Pin(PIN_GAS, machine.Pin.IN), pullup=None)
        #self.wasser = IRQIO(0x12, machine.Pin(PIN_WASSER, machine.Pin.IN), pullup=True)
        #self.door = DoorSensor(0x13, machine.Pin(PIN_DOOR, machine.Pin.IN))
        self.gas = IRQIO(0x11, PIN_GAS, pullup=None)
        self.wasser = IRQIO(0x12, PIN_WASSER, pullup=True)
        self.door = DoorSensor(0x13, PIN_DOOR, debounce_ms=150)

        self.auto_off_task = None
        self.auto_off_delay_s = 1800

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
        if counter_offset != 0:
            m3 = counter_offset + 0.01 * self.gas.counter
            board.PRINTF('Gas: {} m3', m3)
            board.MQTT.publish('m3', m3)

    def send_wasser_value(self):
        self.last_wasser_timestamp = utime.ticks_ms()
        self.last_wasser_value = self.wasser.counter
        board.MQTT.publish('wasser', self.wasser.counter)
        board.PRINTF('Wasser: {}', self.wasser.counter)

    def light_on(self):
        p1.dim_u16(0xffff)
        p2.dim_u16(0xffff)
        board.MQTT.publish('info/light', 'on')

    def light_off(self):
        p1.off()
        p2.off()
        board.MQTT.publish('info/light', 'off')

    def door_open(self):
        if self.auto_off_task is not None:
            self.auto_off_task.cancel()
            self.auto_off_task = None
        self.auto_off_task = asyncio.create_task(self.auto_off())
        self.light_on()
        board.MQTT.publish('info/door', 'open')

    def door_closed(self):
        if self.auto_off_task is not None:
            self.auto_off_task.cancel()
            self.auto_off_task = None
        self.light_off()
        board.MQTT.publish('info/door', 'closed')

    async def auto_off(self):
        await asyncio.sleep(self.auto_off_delay_s)
        self.light_off()
        self.auto_off_task = None

class IRQIO(irqio.IRQIO):
    def __init__(self, portid, pinid, inverted=False, debounce_ms=20, pullup=True):
        super().__init__(portid, pinid, inverted=inverted, debounce_ms=debounce_ms, pullup=pullup)
        self.counter = 0

    async def run(self):
        board.PRINTF('IRQIO {} {}', self.portid, self.pinvalue)
        if self.pinvalue == 1:
            self.counter += 1
        return True

class DoorSensor(irqio.IRQIO):
    def __init__(self, portid, pinid, inverted=False, debounce_ms=50):
        super().__init__(portid, pinid, inverted=inverted, debounce_ms=debounce_ms, pullup=True)

    async def run(self):
        board.PRINTF('DoorSensor {} {}', self.portid, self.pinvalue)
        if self.pinvalue == 1:
            keller.door_open()
        else:
            keller.door_closed()
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

def _door_autooff(_, msg):
    """set door autooff delay in seconds"""
    value = _getvalue(_, msg, min=10, max=3600)
    board.PRINTF('Door autooff: {}', value)
    keller.auto_off_delay_s = value
    board.MQTT.publish('info/door_autooff', value)

def _light_on_off(_, msg):
    """set light on or off"""
    if msg.lower() == 'on':
        keller.light_on()
    elif msg.lower() == 'off':
        keller.light_off()
    else:
        board.PRINTF('Light: {}', msg)
        board.MQTT.publish('error/light', 'Invalid value: ' + msg)

def _door_open_close(_, msg):
    if msg.lower() == 'open':
        keller.door_open()
    elif msg.lower() == 'close':
        keller.door_closed()
    else:
        board.PRINTF('Door: {}', msg)
        board.MQTT.publish('error/door', 'Invalid value: ' + msg)

def _set_offset(_, msg):
    global counter_offset
    counter_offset = float(msg)
    board.PRINTF('Offset: {}', counter_offset)
    keller.send_gas_value()

board.MQTT.subscribe('set/interval', _interval)
board.MQTT.subscribe('set/heartbeat', _heartbeat)
board.MQTT.subscribe('set/door_autooff', _door_autooff)
board.MQTT.subscribe('set/light', _light_on_off)
board.MQTT.subscribe('set/door_open', _door_open_close)
board.MQTT.subscribe('set/offset', _set_offset)

print("going to connect to network")
net.connect_in_background()
fsmqtt.connect_in_background()

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
