import machine
import board
import aht
import fsmqtt
import net
import watchdog

board.LOCATION = 'ug-filamentschrank'
board.VERSION = '2025-12-20'
board.DEBUG = True

# Initialize I2C on pins 0 (SDA) and 1 (SCL)
board.I2C = machine.I2C(0, scl=machine.Pin(1), sda=machine.Pin(0))

# Initialize AHT10 Sensor
# Using portid 1. 
# poll_intervall_in_ms defaults to 5 minutes (from lib/aht.py)
board.PRINTF('Initializing AHT10 sensor...')

th = aht.AHT10(10, poll_intervall_in_ms=5000)

# Start Networking and MQTT
net.connect_in_background()
fsmqtt.connect_in_background()

print(fsmqtt._callbacks.keys())

board.PRINTF("AHT10 initialized. Sensor running in background.")

watchdog.start_later(seconds=120)
