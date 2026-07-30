
import board
board.LOCATION = 'eg-wg-katzenklappe'
board.VERSION = '2026-07-23'
board.DEBUG = True

import bconf
import machine
import fsmqtt
import time
import net
# import watchdog
import memstat
import asyncio
import time

# ── Hardware ─────────────────────────────────────────────
uart = machine.UART(1, baudrate=9600, rx=6, tx=21)
# i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9), freq=400000)
# i2c = machine.I2C(0, scl=machine.Pin(6), sda=machine.Pin(5), freq=400000)
i2c = machine.I2C(0, scl=machine.Pin(7), sda=machine.Pin(5), freq=400000)

AS5600_ADDR = 0x36
ANGLE_REG = 0x0E  # High-Byte, 2 Bytes lesen

print(i2c.scan())
print("I2C Geräte gefunden:", [hex(a) for a in i2c.scan()])

def read_angle():
    data = i2c.readfrom_mem(AS5600_ADDR, ANGLE_REG, 2)
    raw = (data[0] << 8) | data[1]
    raw &= 0x0FFF  # nur untere 12 Bit sind gültig
    return raw / 4096.0 * 360.0

def read_status():
    status = i2c.readfrom_mem(AS5600_ADDR, 0x0B, 1)[0]
    magnet_detected = bool(status & 0x20)
    too_weak = bool(status & 0x10)
    too_strong = bool(status & 0x08)
    return magnet_detected, too_weak, too_strong

def print_status():
    md, weak, strong = read_status()
    if not md:
        print("Kein Magnet erkannt!")
    elif weak:
        print("Magnetfeld zu schwach – Magnet näher ranbringen")
    elif strong:
        print("Magnetfeld zu stark – Magnet weiter weg")
    else:
        print("Magnet OK")

def read_loop():
    while True:
        print_status()
        print("Winkel: {:.2f}°".format(read_angle()))
        time.sleep_ms(500)

known_rfids = {
    '2E01A18A405830110000000000': 'Orange Chip',
    'AD01A18A405830110000000000': 'Stoffkatze',
}

def parse_rfid(buf):
    # board.PRINTF("Parsing RFID buffer: {}", buf)
    if len(buf) < 30: return None
    if buf[0] != 0x02 or buf[-1] != 0x03: return None
    payload = buf[1:27]
    xor_val = 0
    for b in payload: xor_val ^= b
    if buf[27] != xor_val or buf[28] != (~xor_val & 0xFF):
        return None
    return payload.decode('ascii')

async def flap_angle_reader():
    while True:
        try:
            angle = read_angle()
        except Exception as e:
            board.PRINTF("Error reading flap angle: {}", e)
            angle = 0
        board.PRINTF("Flap angle: {:.2f}°", angle)
        board.MQTT.publish('flap_angle', angle)
        await asyncio.sleep_ms(1000)


async def uart_reader():
    board.PRINTF("Starting UART reader")
    buf = bytearray()
    while True:
        board.LED.off()
        while uart.any():
            board.LED.on()
            b = uart.read(1)
            if b is not None:
                b = b[0]
                if b == 0x02:
                    buf = bytearray()
                buf.append(b)
                if b == 0x03:
                    rfid = parse_rfid(buf)
                    if rfid is not None:
                        known = known_rfids.get(rfid, "UNKNOWN")
                        board.PRINTF("RFID read: {} --> {}", rfid, known)
                        board.MQTT.publish('rfid', known)
                    else:
                        board.PRINTF("RFID read: {} --> INVALID", buf)
                        board.MQTT.publish('invalid', 'RFID read: {} bytes'.format(len(buf)))
        # the chip is sending with 9600 baud, so about 1 ms per byte
        await asyncio.sleep_ms(10)


def r():
    board.restart()

board.NET.connect_in_background()
board.MQTT.connect_in_background()

asyncio.create_task(uart_reader())
asyncio.create_task(flap_angle_reader())
board.LED.off()

try:
    if 1 == 1: # pylint: disable=comparison-with-itself
        board.run()
    else:
        print('# run board.run() to start event handler')

except Exception as e: # pylint: disable=bare-except, broad-except
    print('Exception in main loop: ', e)
    print("Try to connect to WLAN")
    import net
    net.net()


