"""
WZ Schrank
    // 2 PWM connected AUX-1 4P on beta board
    7 PWM connected to ML-10
        1: Wandlampe
        2: rote Lampe
        3: Weihnachtslämpchen Fensterbank
        4: Vitrine
        5: unused
        6: driving an upconverter (set to 31 V for the xmas tree)
        7: output of the upconverter driving the LEDs for the xmas tree
    1 AM2320 on AUX-2
    2 buttons on AUX-3
        2 buttons are connected to the small handleld to enable the reading light

"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'wz-schrank'
board.DEBUG = True
board.CANID = 0x10

if board.DEBUG is True:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.DEBUG = True
    net.start_wlan(32)
    net.start_repl()

import gc
import bconf
import can
import machine
import sensors
import pwm
import button
import uasyncio as asyncio
import rgb

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

# TODO: change DC/DC driver from PWM to PIN, make it "auto on/off" with PWM

p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
c = rgb.RGB(4, bconf.ML10_PWM_6,  bconf.ML10_PWM_7, bconf.ML10_PWM_8)
print("# c initialized and all components set to 0")
# stop_here()

# p11 = pwm.PWM(0x11, bconf.AUX1_YELLOW)
# p12 = pwm.PWM(0x12, bconf.AUX1_WHITE)
# pl = pwm.List(0x20, p1, p2)


#b1 = button.Button(10, bconf.AUX3_YELLOW)
#b2 = button.Button(11, bconf.AUX3_WHITE)
#
#if board.DEBUG:
#    b1.callback = lambda b: print('Button pressed: {}'.format(b))


# dht = sensors.DHT(20, bconf.AUX2_YELLOW, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(5))

def r():
    board.restart()

if 1 == 1: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run  restart   (or board.run()) to start event handler')
