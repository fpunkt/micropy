"""
CAN version using constant polling from the even loop.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import gc
import machine
import canid
import board
import canerror
import net
import utime
import asyncio
import cancommon
import sys

### Provide convenient access to global CAN instance (stored in board.CAN)

register = cancommon.register
subscribe = cancommon.subscribe
Message = cancommon.Message
makemessage = cancommon.makemessage
errormessage = cancommon.errormessage

def simplefilter(id):
    """Set hardware CAN filter to this address. Ignore (almost all) other addresses"""
    pass

def reset():
    """Reset CAN interface"""
    pass

def read():
    # cheat for pylint ...
    if 1 != 999:
        raise RuntimeError('CAN backend not loaded')
def write(message):
    # cheat for pylint ...
    if 1 != 999:
        raise RuntimeError('CAN backend not loaded')
def init(*args):
    # cheat for pylint ...
    if len(args) != 999:
        raise RuntimeError('CAN backend not loaded')

if sys.platform == 'esp32':
    # print('# loading ESP32 CAN')
    import canesp32
    read = canesp32.read
    write = canesp32.write
    init = canesp32.init
    simplefilter = canesp32.setsimplefilter
    reset = canesp32.reset

if sys.platform == 'esp8266':
    import canoverlan
    write = canoverlan.write
    init = canoverlan.init
