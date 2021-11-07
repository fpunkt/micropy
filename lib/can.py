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
import uasyncio as asyncio
import cancommon
import sys

### Provide convenient access to global CAN instance (stored in board.CAN)

register = cancommon.register
subscribe = cancommon.subscribe
Message = cancommon.Message
makemessage = cancommon.makemessage

def read():
    raise RuntimeError('CAN backend not loaded')

def write(message):
    raise RuntimeError('CAN backend not loaded')

def init(*args):
    raise RuntimeError('CAN backend not loaded')

if sys.platform == 'esp32':
    # print('# loading ESP32 CAN')
    import canesp32
    read = canesp32.read
    write = canesp32.write
    init = canesp32.init

if sys.platform == 'esp8266':
    import canoverlan
    write = canoverlan.write
    init = canoverlan.init
