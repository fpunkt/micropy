
import machine
import time
import time

# ── Hardware ─────────────────────────────────────────────
uart    = machine.UART(1, baudrate=9600, rx=6, tx=21)
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
    if weak:
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
