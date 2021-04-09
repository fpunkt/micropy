# This file is executed on every boot (including wake-boot from deepsleep)
"""
Buero

webrepl_cli.py -p x can.py 192.168.179.12:

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=unused-import, multiple-statements, wrong-import-order

# disable the interrupt catcher
import machine
machine.CAN(0xff)

#import esp
#esp.osdebug(None)

import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)
import sn

# main is loaded automatically after boot
