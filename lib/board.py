"""
Basic Hardware available to all boards
"""

# pylint: disable=import-error, too-few-public-methods, missing-function-docstring

import machine
import utime
import canid

DEBUG = False

class Led:
    """On/Off LED"""
    def __init__(self, pin):
        self.led = machine.Pin(pin, mode=machine.Pin.OUT)
    def on(self):
        """turn LED on"""
        self.led.value(1)
    def off(self):
        """turn LED off"""
        self.led.value(0)

# The LED on the PCB, if available
LED = Led(2)


# sensors will be set by sensors.py and will provide funtions
# register and find.
# (this forward reference is needed to avoid circular imports)
SENSORSs = None

PWMs = None

last_boot_s = utime.time()

def uptime_s():
    """Return time since last (soft) boot in seconds"""
    return utime.time() - last_boot_s

# Location of the board, overwritten by main.py
LOCATION = "unknown"

# Global CAN device. Use board.CAN to access the CAN bus from everywhere.
# The actual value is set when can.py is loaded/initialized
# (we need this here to avoid circular dependencies in cancommon.py / can.py)
CAN = None

# class _dummyMqtt:
#     def publish_sensor(self, sensortype, sensorid, payload):
#         """publish a sensor message"""

# MQTT connection, set by main.py if applicable
MQTT = None


def error(payload, mqttstring):
    if CAN is not None:
        CAN.send(canid.ERROR_MESSAGE, payload)
    if MQTT is not None:
        pass
