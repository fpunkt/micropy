"""
EG flur
    // 2 PWM connected AUX-1 4P on beta board
    7 PWM connected to ML-10
        5 x Spot
        1 x DC/DC ??
        1 x 9V spots

    Under Roof Connected
        2 x Motion
        1 x Dindong
        1 x light on

    Via ML-10
        1 AM2320
        2 I2C lines for light sensor
        2 x Motion

"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'eg-flur'
board.DEBUG = True
board.CANID = 0x100

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

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

t = tsl2561.TSL2561(0x30, bconf.ML10_2, bconf.ML10_3, 2000)

p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
p4 = pwm.PWM(4, bconf.ML10_PWM_4)
p5 = pwm.PWM(5, bconf.ML10_PWM_5)
p6 = pwm.PWM(6, bconf.ML10_PWM_6)
p7 = pwm.PWM(7, bconf.ML10_PWM_7)
p8 = pwm.PWM(8, bconf.ML10_PWM_8)


#def can_callback(msg):


# can.subscribe(can_callback)

dht = sensors.DHT(20, bconf.ML10_1, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(5))

def r():
    board.restart()

if 1 != 0: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run  restart   (or board.run()) to start event handler')
