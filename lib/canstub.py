"""
CAN dummys for CPU without CAN bus
"""

import gc
import board
import utime


class Message:
    """A CAN message"""
    def __init__(self, *args):
        pass
    def setsender(self, _):
        pass
    def send(self):
        pass
    def u16(self, _):
        return 0
    def bad_number_of_args(self, min, max=None):
        pass
    # "Command #%02x: bad value for paramenter %d, found %d expected, %d .. %d", d0, d1, d2, d3, d4)
    def bad_parameter_value(self, n, min, max):
        pass
    def bad_sensor_id(self):
        self.bad_parameter_value(1, 0xff, 0xff)
    def bad_sensor_type(self, expected):
        self.bad_parameter_value(1, 0xff, 0)
    def unknown_command(self):
        pass

def makemessage(cid, size, sensorid=None):
    m = Message(cid, [0]*size)
    if sensorid is not None:
        m.setsender(sensorid)
    return m

Badmessage = Message(0x777, [1, 2, 3, 4])


def register(commandbyte, minargs, maxargs, callback):
    pass


# cached message to avoid mallocs
_message = Message(0, bytearray([0, 1, 2, 3, 4, 5, 6, 7]))

class CAN:
    """Wrapper for machine.CAN, providing (some kind of) interrupt and callback"""
    def __init__(self, cid=None, rx=33, tx=32, baudrate=125, mode=None):
        pass
    def poll(self):
        return False
    def subscribe(self, callback, cid=None):
        pass
    def any(self):
        return False
    def read(self) -> Message:
        return Message(0, 0)
    def write(self, msg):
        pass
    def send(self, cid, payload):
        pass
    def send_poweron(self):
        pass
    def identify(self):
        pass
    def send_wlan_connected(self, ip):
        pass

board.CAN = CAN()
board.CAN = None

Badmessage = Message(0x777, [1, 2, 3, 4])

def errormessage(payload):
    pass

def run_gc():
    global _gc_counter # pylint: disable=global-statement
    if not board.DEBUG:
        gc.collect()
    else:
        free = gc.mem_free() # pylint: disable=no-member
        start = utime.ticks_ms()
        gc.collect()
        newfree = gc.mem_free() # pylint: disable=no-member
        print('GC collected {} bytes in {} ms, free={}'.format(
            newfree-free, utime.ticks_diff(utime.ticks_ms(), start), newfree))
    #_send_memstat()

board.run_gc = run_gc


### Common config commands

# Basic configuration commands common to all applications are handled by this layer.
#
# Config commands (assuming CAN address 100)
#
# cansend 100#fd # START WLAN and repl
# cansend 100#fe # STOP WLAN and repl
#
# cansend 200#fd # START WLAN and repl

### Provide convenient access to global CAN instance (stored in board.CAN)

def subscribe(callback, cid=None):
    pass

def read():
    return None

def any():
    return False
