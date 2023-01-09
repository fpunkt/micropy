"""
Pingmachine
"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'pingmachine'
board.DEBUG = True
board.CANID = 0x666

if board.DEBUG is True:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.DEBUG = True
    net.start_wlan(0)
    net.start_repl()

import gc
import bconf
import can
import machine
import sensors
import pwm
import uasyncio as asyncio
import tsl2561
import motionsensor
import irqio
import canid

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

board.PINGTIME = 2


def r():
    board.restart()

if 1 != 0: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run  restart   (or board.run()) to start event handler')

