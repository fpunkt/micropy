
import board
board.LOCATION = 'eg-wg-katzenklappe'
board.HOSTNAME = 'katzenklappe'
board.VERSION = '2026-07-23'
board.DEBUG = True


DEBUG = 0  # print debug messages to console and MQTT topic 'debug'

import bconf
import machine
import fsmqtt
import time
import net

# import watchdog
import memstat
import asyncio
import time
import am2302

# ── Hardware ─────────────────────────────────────────────

if False: # ESP32C3 super mini
    uart = machine.UART(1, baudrate=9600, rx=6, tx=21)
    # i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9), freq=400000)
    # i2c = machine.I2C(0, scl=machine.Pin(6), sda=machine.Pin(5), freq=400000)
    i2c = machine.I2C(0, scl=machine.Pin(7), sda=machine.Pin(5), freq=400000)
    servo = machine.PWM(machine.Pin(10), freq=50, duty=0)
    dht_pin = machine.Pin(11, machine.Pin.IN)  # DHT22 sensor pin

else: # ESP32 WROOM32
    uart = machine.UART(1, baudrate=9600, rx=16, tx=17)
    #i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
    i2c = machine.I2C(0, scl=machine.Pin(21), sda=machine.Pin(22), freq=400000)
    servo = machine.PWM(machine.Pin(10), freq=50, duty=0)
    dht_pin = machine.Pin(13, machine.Pin.IN)  # DHT22 sensor pin

board.I2C = i2c


board.NET.connect_in_background()


AS5600_ADDR = 0x36
ANGLE_REG = 0x0E  # High-Byte, 2 Bytes lesen

FLAP_ZERO_ANGLE_OFFSET = 270.8  # Winkel, bei dem die Klappe geschlossen ist
FLAP_CLOSE_MAX_ANGLE = 10  # Maximaler Winkel, bei dem die Klappe geschlossen ist
FLAP_ENTERING_ANGLE = 25  # oder größer: Winkel, bei dem die Klappe geöffnet ist, wenn die Katze reingeht

SERVO_OPEN_ANGLE = 80  # Winkel, bei dem die Klappe geöffnet ist
SERVO_CLOSED_ANGLE = 20  # Winkel, bei dem die Klappe geschlossen ist


###############################################################################
### DHT22 Sensor

dht22 = am2302.AM2302(portid=0x11, pin=dht_pin, poll_intervall_in_ms=5*60*1000)  # Poll every 5 minutes




id_check_requested = asyncio.Event()
id_check_requested.clear()
id_is_valid = asyncio.Event()
id_is_valid.clear()


print(i2c.scan())
print("I2C Geräte gefunden:", [hex(a) for a in i2c.scan()])

###############################################################################
### Angular encoder AS5600

# Set to undefined so we trigger a close message after startup.
# Otherwise Homeassisstant does not record subsequent 'connect' messages although
#  the force_update property is set.
flap_status = 'undefined'  # 'closed', 'entering', 'leaving', 'swinging'


known_rfids = {
    '2E01A18A405830110000000000': 'Orange Katze',
    'AD01A18A405830110000000000': 'Stoffkatze',
    '1A249E24614110010000000000': 'Zoe - SW Katze',

    # Chip Reader 1
    # 2026-10-31 21:00:07.955 hcm/eg-wg-katzenklappe/rfid 33B1FC8E512820010000000000
    # 2026-10-31 23:16:23.759 hcm/eg-wg-katzenklappe/rfid 33B1FC8E512820010000000000
    '33B1FC8E512820010000000000': 'Zoe - SW Katze',
}


def read_encoder_angle():
    """Read the angle from the AS5600 angular encoder and return it in degrees."""
    data = i2c.readfrom_mem(AS5600_ADDR, ANGLE_REG, 2)
    raw = (data[0] << 8) | data[1]
    raw &= 0x0FFF  # nur untere 12 Bit sind gültig
    angle = raw / 4096.0 * 360.0
    return angle - FLAP_ZERO_ANGLE_OFFSET

def read_encoder_status():
    """Read the status register from the AS5600 angular encoder and return the magnet
    status (magnet_detected, too_weak, too_strong)."""
    status = i2c.readfrom_mem(AS5600_ADDR, 0x0B, 1)[0]
    magnet_detected = bool(status & 0x20)
    too_weak = bool(status & 0x10)
    too_strong = bool(status & 0x08)
    return magnet_detected, too_weak, too_strong

def print_encoder_status():
    """Read the status of the AS5600 and print it to the console."""
    md, weak, strong = read_encoder_status()
    if not md:
        print("Kein Magnet erkannt!")
    elif weak:
        print("Magnetfeld zu schwach – Magnet näher ranbringen")
    elif strong:
        print("Magnetfeld zu stark – Magnet weiter weg")
    else:
        print("Magnet OK")

def print_encoder_angle():
    """Read the angle from the AS5600 and print it to the console."""
    angle = read_encoder_angle()
    print("Winkel: {:.2f}°".format(angle))

def debug_read_encoder_loop():
    """Debug loop to read the encoder angle and status every 500 ms."""
    while True:
        print_encoder_status()
        print_encoder_angle()
        time.sleep_ms(500)

def flap_send_mqtt(payload):
    board.MQTT.publish('event', payload)

async def flap_angle_reader_task():
    """Task to read the flap angle and update its status.
    This task runs in the background and updates the flap_status variable based on the angle read from the AS5600 encoder.
    It also publishes the flap status and angle to MQTT topics for monitoring.
    The encoder is read every 100 ms, and the flap status is updated based on the angle thresholds defined above.
    It does debounce the flap status to avoid rapid changes due to swinging or noise in the angle readings.
    """
    global flap_status
    last_error_time = 0
    close_debounce_counter = 50  # initialize with non-zero so we get a close message after reboot (or not, if stuck)
    stuck_counter = 0

    while True:
        await asyncio.sleep_ms(100)
        now = time.ticks_ms()

        try:
            angle = read_encoder_angle()
        except Exception as e:
            time_since_last_error = time.ticks_diff(now, last_error_time)
            if time_since_last_error > 60 * 1000:  # only print error every ... seconds
                last_error_time = now
                if DEBUG:
                    board.PRINTF("Error reading flap angle: {}", e)
                board.MQTT.publish('error', 'Error reading flap angle: {}'.format(e))
            angle = 0
            await asyncio.sleep_ms(1000)
            continue  # skip the rest of the loop and try again

        # got valid angle

        if DEBUG > 2:
            print_encoder_status()
            board.PRINTF("Flap prev status = {}, angle: {:.2f}°", flap_status, angle)
            # board.MQTT.publish('debug', angle)
            # board.MQTT.publish('debug', flap_status)

        if abs(angle) < FLAP_CLOSE_MAX_ANGLE:
            if flap_status == 'closed':
                continue  # flap is closed and status unchanged, keep waiting for flap to open

            # keep on debouncing ...
            if DEBUG > 1:
                board.PRINTF("closed angle {} - debounce = {}", angle, close_debounce_counter)

            close_debounce_counter -= 1

            if close_debounce_counter == 0:
                # now we are stable closed
                if DEBUG > 0:
                    board.PRINTF("*** new state: close")
                stuck_counter = 0
                flap_status = 'closed'
                flap_send_mqtt('closed')
                id_check_requested.clear()  # clear the event if flap is closed
                id_is_valid.set()  # clear the event if flap is closed

            continue  # flap at close angle, just closed or keep on debouncing


        # not in closed position check for new status
        close_debounce_counter = 50  # start debouncing, about 50 * 100ms = 5 sec

        if flap_status == 'stuck':
            # stuck status can only be reset by "close"
            continue

        # check whether flap is stuck in a non-closed position
        stuck_counter -= 1
        if stuck_counter == 0:
            if DEBUG > 0:
                board.PRINTF("*** new state: stuck")
            flap_send_mqtt('stuck {:.2f}'.format(angle))
            flap_status = 'stuck'
            continue


        if flap_status not in ('closed', 'in_between'):
            # already reported, wait for close state
            continue

        # Here the flap is not closed and not stuck

        new_status = 'in_between'
        if angle >= FLAP_ENTERING_ANGLE:
            new_status = 'entering'
        elif angle <= -FLAP_ENTERING_ANGLE:
            new_status = 'leaving'

        if DEBUG > 1:
            board.PRINTF("state {} -> {}, debounce={}/{}, angle={}",
            flap_status, new_status, close_debounce_counter, stuck_counter, angle)

        # now flap new state is either entering or leaving, so we can update the flap_status and publish it to MQTT

        if new_status == flap_status:
            # keep on debouncing or stuck detection
            continue

        # New status - arm stuck detection
        flap_status = new_status
        stuck_counter = 10 * 60 # about one minute

        if flap_status == 'in_between':
            # don't report
            continue

        if DEBUG > 0:
            board.PRINTF("*** new state: {}", flap_status)
        flap_send_mqtt(flap_status)
        id_is_valid.clear()
        id_check_requested.set()
        await asyncio.sleep_ms(2000)  # wait for flap to settle




###############################################################################
### RFID Reader

def parse_rfid(buf):
    # board.PRINTF("Parsing RFID buffer: {}", buf)
    if len(buf) < 3: return None
    # if buf[0] != 0x02 or buf[-1] != 0x03: return None
    # payload = buf[1:27]
    # strip off the last two bytes (checksum and inverted checksum)
    payload = buf[0:-2]
    xor_val = 0
    for b in payload: xor_val ^= b
    if buf[-2] != xor_val or buf[-1] != (~xor_val & 0xFF):
        return None
    return payload.decode('ascii')



async def rfid_reader_task():
    """
    Collect RFID encoder data from the UART interface.
    This task runs in the background and reads data from the UART interface connected to the RFID reader.
    It looks for the start byte (0x02) and end byte (0x03) to identify complete RFID messages.
    The data between the start and end bytes is parsed and validated.
    If the RFID cannot be parsed it publishes an 'invalid' message to MQTT.
    Otherwise, it checks if the RFID is known and publishes the result to MQTT.
    The task runs indefinitely. If no data is available, it sleeps briefly to avoid busy-waiting.
    """
    board.PRINTF("Starting UART reader")
    buf = bytearray()
    board.LED.off()
    timeout_counter = 0
    flush_counter = 0
    while True:
        if not uart.any():
            timeout_counter += 1
            if timeout_counter == 50:
                board.LED.off()
                buf = bytearray()  # clear the buffer if no data for a while
            await asyncio.sleep_ms(10)  # wait a bit before checking again
            flush_counter = 0
            continue

        flush_counter += 1
        if flush_counter > 50:
            # give other threads some time to handle their tasks
            await asyncio.sleep_ms(1000)
            flush_counter = 0

        timeout_counter = 0
        board.LED.on()
        b = uart.read(1)
        if b is None:
            # although this should not happen because UART.any() returned True, but just in case
            continue

        b = b[0]
        if b == 0x02:
            # start of RFID message
            buf = bytearray()
            continue

        # keep reading and collecting bytes until we get the end of message byte
        if b != 0x03:
            if len(buf) > 50:  # limit buffer size to avoid overflow
                board.PRINTF("RFID buffer overflow, resyncing...")
                board.MQTT.publish('error', 'RFID buffer overflow, resyncing...')
                buf = bytearray()  # clear the buffer
                await asyncio.sleep_ms(200)
                continue

            buf.append(b)
            continue

        # we got the end of message byte 0x03, now parse the RFID
        board.PRINTF("RFID read: {} bytes", len(buf))
        board.LED.off()

        rfid = parse_rfid(buf)
        if rfid is None:
            board.PRINTF("RFID read: {} --> INVALID", buf)
            board.MQTT.publish('invalid', 'RFID read: {} bytes'.format(len(buf)))
            continue

        known = known_rfids.get(rfid, "unknown")
        flap_send_mqtt("RFID {} // {}".format(rfid, known))
        board.PRINTF("RFID read: {} // {}", rfid, known)
        if known != "unknown":
            id_is_valid.set()
        id_check_requested.clear()




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
        board.MQTT.publish('access', 'id_check_requested')
        # id_check_requested.clear()  # clear the event after handling
        set_angle(SERVO_CLOSED_ANGLE)

        await id_is_valid.wait()  # wait for ID validation
        board.PRINTF("ID is valid or flap closed, opening fence...")
        board.MQTT.publish('access', 'reset')
        set_angle(SERVO_OPEN_ANGLE)
        id_is_valid.clear()  # clear the event after opening the flap
        await asyncio.sleep_ms(500)

def set_barrier_angle(topic, angle):
    """
    Set the barrier angle based on MQTT command.
    :param topic: The MQTT topic (not used here)
    :param angle: The angle in degrees (0-180)
    """
    iangle = int(angle)
    if iangle < 0 or iangle > 180:
        board.PRINTF("Invalid barrier angle: {}. Must be between 0 and 180.", iangle)
        return
    board.PRINTF("Setting barrier angle to {}°", iangle)
    set_angle(iangle)

def set_command(topic, command):
    """
    Set the barrier angle based on MQTT command.
    :param topic: The MQTT topic (not used here)
    :param command: The command string ('open', 'close', 'reset')
    """
    global DEBUG
    if command == 'open':
        board.PRINTF("Opening barrier...")
        set_angle(SERVO_OPEN_ANGLE)
    elif command == 'close':
        board.PRINTF("Closing barrier...")
        set_angle(SERVO_CLOSED_ANGLE)
    elif command == 'reset':
        board.PRINTF("Resetting barrier...")
        set_angle(SERVO_CLOSED_ANGLE)
    elif command == 'DEBUG_ON':
        DEBUG += 1
    elif command == 'DEBUG_OFF':
        DEBUG = 0
    else:
        board.MQTT.publish("error", "unknown value for set: {}".format(command))
        board.PRINTF("Unknown command: {}. Valid commands are 'open', 'close', 'reset'.", command)

def r():
    board.restart()

board.MQTT.subscribe('set', set_command)

# board.NET.connect_in_background()
board.MQTT.connect_in_background()

board.MQTT.after_connect.append(lambda: flap_send_mqtt("connected {}/{}".format(board.MQTT.connection_counter, board.NET.connection_counter)))

board.MQTT.ignore_topics('invalid', 'rfid', 'event', 'access', 'xrfid', 'alert', 'debug', 'hello', 'error')

asyncio.create_task(rfid_reader_task())
asyncio.create_task(flap_angle_reader_task())
# asyncio.create_task(servo_control_task())
board.LED.off()



# No code needed here, the main.py will start the event loop (board.run()) and run the tasks above.
