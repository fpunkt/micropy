"""
Basic Hardware functionality of the board.

Loaded modules and defined devices add to global variables in this module
"""

# pylint: disable=import-error, too-few-public-methods, missing-function-docstring

import gc
import machine
import utime
import uasyncio as asyncio

# If DEBUG is set, additinoal messages will be printed. Set in main.py
DEBUG = False

# CANID of the application. Set in main.py
CANID = None

def PRINT(formatstring, *args):
    if not DEBUG:
        return
    print(formatstring.format(*args))

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


class RegisteredSensorIDs:
    """Keep record of registered sensors"""
    def __init__(self):
        self.r = dict()

    def register(self, sensorid, sensor):
        if sensorid is None:
            return
        if self.get_sensor(sensorid):
            raise RuntimeError("id #{} is already registered as {} ({})".format(sensorid, self.r[sensorid], sensor))
        self.r[sensorid] = sensor

    def dump(self):
        for i, v in self.r:
            print("ID {:2d} = {}".format(i, v))

    def get_sensor(self, sensorid):
        return self.r.get(sensorid, None)

    def find(self, msg, withclass, sensortype=0xfe):
        """Find a registered sensor ID that is provided as 2nd value in the CAN payload.
        The sensor should have one of the classes in withclass (or None if you don't care).
        If the sensor is not found the function returns and raises an error on
        CAN/mqtt bus.
        The optional sensortype is used in the errormessage.
        """
        p = msg.payload
        sensorid = 0xff
        if len(p) > 1:
            sensorid = p[1]
        d = self.r.get(sensorid, None)
        if d is None:
            if DEBUG:
                print('Device #{} not found'.format(sensorid))
            msg.bad_sensor_id()
            return None
        if withclass is None:
            return d
        if not isinstance(d, withclass):
            if DEBUG:
                print('Found ID #{} but wrong class {} (expected {})'.format(sensorid, d.__class__, withclass))
            msg.bad_sensor_type(sensortype)
            return None
        return d

# ==================================================================================================
# ==================================================================================================

# Provide global variables that allow functions to access all devices when they have
# included board.py
# This allows e.g. sensors to use serve MQTT and CAN even if one of these backends
# has not been initialized.

# The on-chip LED
LED = Led(2)

# Sensors will be set by sensors.py and will provide funtions
# register and find.
SENSORSs = RegisteredSensorIDs()

# PWMs holds a list of all defined PWMs (initialized by loading pwm.py)
PWMs = None

# external functions (like dimming) can temporarily disable sensor accquisition (looks nicer)
PWM_IS_DIMMING = False

BACKGROUND_RUNNERS = []

last_boot_s = utime.time()

def uptime_s():
    """Return time since last (soft) boot in seconds"""
    return utime.time() - last_boot_s

# Location of the board, overwritten by main.py. Used e.g. by MQTT to construct the message
LOCATION = "unknown"

# Global CAN device. Use board.CAN to access the CAN bus from everywhere.
# The actual value is set when can.py is loaded/initialized
CAN = None

# class _dummyMqtt:
#     def publish_sensor(self, sensortype, sensorid, payload):
#         """publish a sensor message"""

# MQTT connection, set by main.py if applicable
MQTT = None

# the global watchdog
WD = None

run_gc = None

def good_time_for_gc():
    # pylint: disable=no-member
    if run_gc and gc.mem_free() < 6000:
        run_gc() # pylint: disable=not-callable

# Run async processes

async def arun():
    try:
        await asyncio.gather(*BACKGROUND_RUNNERS)
    except asyncio.TimeoutError:
        if DEBUG:
            print('asyncIO timeout!')
    except Exception as e: # pylint: disable=broad-except
        if DEBUG:
            print('**** ERROR in runner')
            print(e)

def run():
    asyncio.run(arun())
