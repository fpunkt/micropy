
import board
board.LOCATION = 'eg-wg-katzenklappe'
board.VERSION = '2026-07-23'
board.DEBUG = True


DEBUG = False  # print debug messages to console and MQTT topic 'debug'

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

PIN_SERVO = 10
servo = machine.PWM(machine.Pin(PIN_SERVO), freq=50, duty=0)

AS5600_ADDR = 0x36
ANGLE_REG = 0x0E  # High-Byte, 2 Bytes lesen

FLAP_ZERO_ANGLE_OFFSET = 306.0  # Winkel, bei dem die Klappe geschlossen ist
FLAP_CLOSE_MIN_ANGLE = -10  # Minimaler Winkel, bei dem die Klappe geschlossen ist
FLAP_CLOSE_MAX_ANGLE = 10  # Maximaler Winkel, bei dem die Klappe geschlossen ist
FLAP_CAT_ENTERING_ANGLE = 25  # oder größer: Winkel, bei dem die Klappe geöffnet ist, wenn die Katze reingeht
FLAP_CAT_LEAVING_ANGLE = -FLAP_CAT_ENTERING_ANGLE  # oder kleiner: Winkel, bei dem die Klappe geöffnet ist, wenn die Katze rausgeht


SERVO_OPEN_ANGLE = 80  # Winkel, bei dem die Klappe geöffnet ist
SERVO_CLOSED_ANGLE = 20  # Winkel, bei dem die Klappe geschlossen ist

id_check_requested = asyncio.Event()
id_check_requested.clear()
id_is_valid = asyncio.Event()
id_is_valid.clear()


print(i2c.scan())
print("I2C Geräte gefunden:", [hex(a) for a in i2c.scan()])

###############################################################################
### Angular encoder AS5600

flap_status = 'closed'  # 'closed', 'cat_entering', 'cat_leaving', 'swinging'


known_rfids = {
    '2E01A18A405830110000000000': 'Orange Katze',
    'AD01A18A405830110000000000': 'Stoffkatze',
    '1A249E24614110010000000000': 'Schwarzeweiße Katze',
}


def read_angle():
    data = i2c.readfrom_mem(AS5600_ADDR, ANGLE_REG, 2)
    raw = (data[0] << 8) | data[1]
    raw &= 0x0FFF  # nur untere 12 Bit sind gültig
    angle = raw / 4096.0 * 360.0
    return angle - FLAP_ZERO_ANGLE_OFFSET

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

async def flap_angle_reader_task():
    global flap_status
    last_error_time = 0
    while True:
        await asyncio.sleep_ms(100)
        try:
            angle = read_angle()
        except Exception as e:
            board.PRINTF("Error reading flap angle: {}", e)
            angle = 0
            await asyncio.sleep_ms(1000)
        now = time.ticks_ms()

        if DEBUG:
            print_status()
            board.PRINTF("Flap prev status = %s, angle: {:.2f}°", flap_status, angle)
            board.MQTT.publish('debug', angle)
            board.MQTT.publish('debug', flap_status)

        if angle > FLAP_CLOSE_MIN_ANGLE and angle < FLAP_CLOSE_MAX_ANGLE:
            if flap_status == 'swinging':
                flap_status = 'closed'
                id_check_requested.clear()  # clear the event if flap is closed
                id_is_valid.set()  # clear the event if flap is closed
                board.PRINTF("Flap closed (angle {:.2f}°)", angle)
                board.MQTT.publish('flap', 'closed')
                continue

            if flap_status == 'closed':
                continue  # flap is closed, no need to check for entering/leaving

            board.PRINTF("Flap swinging")
            flap_status = 'swinging'
            await asyncio.sleep_ms(2000)  # wait for flap to settle
            continue  # ignore swinging flap, wait for it to settle

        if flap_status != 'closed':
            await asyncio.sleep_ms(1000)  # wait for flap to settle
            continue  # flap is swinging, ignore entering/leaving status until it settles

        if angle >= FLAP_CAT_ENTERING_ANGLE:
            if flap_status != 'cat_entering':
                flap_status = 'cat_entering'
                board.PRINTF("Flap cat entering (angle {:.2f}°)", angle)
                board.MQTT.publish('flap', 'cat_entering')
                id_is_valid.clear()
                id_check_requested.set()

                await asyncio.sleep_ms(1000)  # wait for flap to settle
        elif angle <= FLAP_CAT_LEAVING_ANGLE:
            if flap_status != 'cat_leaving':
                flap_status = 'cat_leaving'
                id_check_requested.clear()
                id_is_valid.set()
                board.PRINTF("Flap cat leaving (angle {:.2f}°)", angle)
                board.MQTT.publish('flap', 'cat_leaving')
                await asyncio.sleep_ms(1000)  # wait for flap to settle




###############################################################################
### RFID Reader

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



async def uart_reader_task():
    """
    Read RFID encoder data from the UART interface.
    """
    board.PRINTF("Starting UART reader")
    buf = bytearray()
    while True:
        board.LED.off()
        while uart.any():
            board.LED.on()
            b = uart.read(1)
            if b is None:
                # timeout on uart.read(), wait a bit and try again
                # although this should not happen because UART.any() returned True, but just in case
                await asyncio.sleep_ms(1)
                continue

            b = b[0]
            if b == 0x02:
                # start of RFID message
                buf = bytearray()
            buf.append(b)
            if b != 0x03:
                # keep reading until we get the end of message byte
                # the chip is sending with 9600 baud, so about 1 ms per byte
                asyncio.sleep_ms(2)  # wait a bit for the next byte
                continue  # wait for end of message

            rfid = parse_rfid(buf)
            if rfid is None:
                board.PRINTF("RFID read: {} --> INVALID", buf)
                board.MQTT.publish('invalid', 'RFID read: {} bytes'.format(len(buf)))
                # await asyncio.sleep_ms(10)  # wait a bit before reading the next RFID
                break

            board.MQTT.publish('rfid', rfid)
            known = known_rfids.get(rfid, None)
            if known is None:
                board.MQTT.publish('alert', 'ALERT: Alien Cat Invader!')
                break

            id_is_valid.set()
            id_check_requested.clear()
            board.PRINTF("RFID read: {} --> {}", rfid, known)
            board.MQTT.publish('hello', known)

        # waiting for the next byte to arrive, but don't block the event loop
        await asyncio.sleep_ms(10)  # wait a bit before reading the next byte



###############################################################################
### Servo control

def set_angle(angle):
    """
    Set the angle of the servo motor.
    :param angle: The angle in degrees (0-180)
    """
    # Winkel (0-180) in Duty-Cycle umrechnen
    # duty_ns: 500000 ns (0°) bis 2500000 ns (180°)
    min_ns = 500000
    max_ns = 2500000
    ns = min_ns + (max_ns - min_ns) * angle // 180
    servo.duty_ns(ns)

async def servo_control_task():
    """
    Control the servo motor based on flap status.
    """
    while True:
        await id_check_requested.wait()  # wait for ID check request
        board.PRINTF("ID check requested, waiting for validation...")
        board.MQTT.publish('flap', 'id_check_requested')
        # id_check_requested.clear()  # clear the event after handling
        set_angle(SERVO_CLOSED_ANGLE)

        await id_is_valid.wait()  # wait for ID validation
        board.PRINTF("ID is valid or flap closed, opening fence...")
        board.MQTT.publish('flap', 'open fence')
        set_angle(SERVO_OPEN_ANGLE)
        id_is_valid.clear()  # clear the event after opening the flap

def r():
    board.restart()

board.NET.connect_in_background()
board.MQTT.connect_in_background()

board.MQTT.ignore_topics('invalid', 'rfid', 'flap', 'xrfid', 'alert', 'debug', 'hello')

asyncio.create_task(uart_reader_task())
asyncio.create_task(flap_angle_reader_task())
asyncio.create_task(servo_control_task())
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


