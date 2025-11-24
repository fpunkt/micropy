"""
Basic Hardware functionality of the board.

Loaded modules and defined devices add to global variables in this module
"""

# pylint: disable=import-error, too-few-public-methods, missing-function-docstring

import gc
import sys
import machine
import utime
import uasyncio as asyncio

# If DEBUG is set, additinoal messages will be printed. Set in main.py
DEBUG = False

# CANID of the application. Set in main.py
CANID = None

CPU_ID = 1              # ESP32 per default
BOARD_ID = 0            # PCB version, overwritten in bconf
PERIPH_ID = 0           # PCB version, overwritten in main.py (or by including other .py files)

LED = None              # overwritten in bconf

MQTT = None             # Set when MQTT is connected

RESET_ON_HARD_ERRORS = False # mainly CAN Errors
ENABLE_WATCHDOG_AFTER_SECONDS = 120

PINGTIME = 300
MEMSTATTIME = 300
CANPOLLTIME_MS = 5

CAN_MESSAGES_RECEIVED = 0
CAN_MESSAGES_SEND = 0

def PRINT(formatstring, *args):
    if not DEBUG:
        return
    print(formatstring.format(*args))


class Led:
    """On/Off LED"""
    def __init__(self, pin, onvalue=1):
        self.led = machine.Pin(pin, mode=machine.Pin.OUT)
        self.onvalue = onvalue
    def on(self):
        """turn LED on"""
        self.led.value(self.onvalue)
    def off(self):
        """turn LED off"""
        self.led.value(1-self.onvalue)


class RegisteredPortIDs:
    """Keep record of registered sensors"""
    def __init__(self):
        self.r = dict()

    def register(self, portid, sensor):
        if portid is None:
            return
        if self.get_sensor(portid):
            raise RuntimeError("id #{} is already registered as {} ({})".format(portid, self.r[portid], sensor))
        self.r[portid] = sensor

    def dump(self):
        for i, v in self.r:
            print("ID {:2d} = {}".format(i, v))

    def get_sensor(self, portid):
        return self.r.get(portid, None)

    def find(self, msg, withclass, sensortype=0xfe):
        """Find a registered sensor ID that is provided as 2nd value in the CAN payload.
        The port should have one of the classes in withclass (or None if you don't care).
        If the port is not found the function returns and sends an error message on
        CAN bus.
        The optional sensortype is used in the errormessage.
        """
        p = msg.payload
        portid = 0xff
        if len(p) > 1:
            portid = p[1]
        d = self.r.get(portid, None)
        if d is None:
            if DEBUG:
                print('Device #{} not found'.format(portid))
            msg.bad_sensor_id()
            return None
        if withclass is None:
            return d
        if not isinstance(d, withclass):
            if DEBUG:
                print('Found ID #{} but wrong class {} (expected {})'.format(portid, d.__class__, withclass))
            msg.bad_sensor_type(sensortype)
            return None
        return d

# ==================================================================================================
# ==================================================================================================

# Provide global variables that allow functions to access all devices when they have
# included board.py
# This allows e.g. sensors to use serve CAN even if the backend
# has not been initialized.



# Sensors will be set by sensors.py and will provide funtions
# register and find.
PORTs = RegisteredPortIDs()

# PWMs holds a list of all defined PWMs (initialized by loading pwm.py)
PWMs = None

# external functions (like dimming) can temporarily disable sensor accquisition (looks nicer)
PWM_IS_DIMMING = False

# modules can register STARTUP_FUNCTIONS that are called at the beginning of the run loop
STARTUP_FUNCTIONS = []

# BACKGROUND_RUNNERS is a list of all tasks that run (indefinitely) as independent async task
BACKGROUND_RUNNERS = []

# I2C holds the globally initialized I2C device
I2C = None
I2C_SDA_PIN = 0

last_boot_s = utime.time()

def uptime_s():
    """Return time since last (soft) boot in seconds"""
    return utime.time() - last_boot_s

def uptime_hms():
    h, ms = divmod(uptime_s(), 3600)
    m, s = divmod(ms, 60)
    return '{:03d}:{:02d}:{:02d}'.format(h, m, s)

# Location of the board, overwritten by main.py. Used e.g. by MQTT to construct the message
LOCATION = "unknown"

# Version of the board firmware, overwritten by main.py or app.py
VERSION = "unknown"

# Global CAN device. Use board.CAN to access the CAN bus from everywhere.
# The actual value is set when can.py is loaded/initialized
CAN = None

# the global watchdog
class _dummy_watchdoc():
    def enable(self): pass
    def trigger(self): pass

WD = _dummy_watchdoc()

run_gc = None

def good_time_for_gc():
    # pylint: disable=no-member
    if run_gc and gc.mem_free() < 6000:
        run_gc() # pylint: disable=not-callable

async def _enable_watchdog():
    await asyncio.sleep(ENABLE_WATCHDOG_AFTER_SECONDS)
    if ENABLE_WATCHDOG_AFTER_SECONDS == 0:
        return
    WD.enable()


# Run async processes

async def arun():
    try:
        await asyncio.gather(*BACKGROUND_RUNNERS)
    except asyncio.TimeoutError:
        if DEBUG:
            print('asyncIO timeout!')
    except Exception as e:
        if DEBUG:
            print('**** ERROR in runner: {}'.format(e))
            sys.print_exception(e)

def run():
    print('start running')
    for f in STARTUP_FUNCTIONS:
        f()
    # run GC once to supress memory messages after startup (because gc will be triggered after initialization ...)
    gc.collect()
    print('start main loop')
    asyncio.run(arun())

def restart():
    gc.collect()
    asyncio.get_event_loop().run_forever()


def reload_module(module_name, run_main=False):
	"""
	Reload a module by name in MicroPython.
	- Versucht importlib.reload(mod) falls verfügbar.
	- Falls nicht, entfernt den Eintrag aus sys.modules und importiert neu.
	- Wenn run_main=True und das Modul hat eine main()-Funktion, wird diese aufgerufen.
	Usage: reload_module('sensors') or reload_module('mypkg.modul', run_main=True)
	"""
	import sys
	try:
		# try importlib.reload if available
		import importlib  # may not exist on some MicroPython builds
		mod = sys.modules.get(module_name)
		if mod is None:
			# not loaded yet, import fresh
			mod = __import__(module_name)
		else:
			mod = importlib.reload(mod)
	except Exception:
		# fallback: remove from sys.modules and import again
		if module_name in sys.modules:
			del sys.modules[module_name]
		# __import__ returns top-level package for dotted names; walk attributes
		mod = __import__(module_name)
		parts = module_name.split('.')
		for p in parts[1:]:
			mod = getattr(mod, p)
	# optional: run main() if present
	if run_main and hasattr(mod, 'main'):
		try:
			mod.main()
		except Exception as e:
			if board.DEBUG:
				print('reload_module: Fehler beim Aufruf von main():', e)
	return mod
