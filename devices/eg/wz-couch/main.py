"""
WZ couch
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
board.LOCATION = 'wz-couch'
# board.DEBUG = True
board.CANID = 0x368

if board.DEBUG is True:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.start_wlan()
    net.start_repl()

import gc
import bconf
import can
import machine
import sensors
import pwm
import button
import asyncio

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

# TODO: change DC/DC driver from PWM to PIN, make it "auto on/off" with PWM

p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
p4 = pwm.PWM(4, bconf.ML10_PWM_4)
p5 = pwm.PWM(5, bconf.ML10_PWM_5)
p6 = pwm.PWM(6, bconf.ML10_PWM_6)
p7 = pwm.PWM(7, bconf.ML10_PWM_7)
p8 = pwm.PWM(8, bconf.ML10_PWM_8)

# p11 = pwm.PWM(0x11, bconf.AUX1_YELLOW)
# p12 = pwm.PWM(0x12, bconf.AUX1_WHITE)
# pl = pwm.List(0x20, p1, p2)


b1 = button.Button(10, bconf.AUX3_YELLOW)
b2 = button.Button(11, bconf.AUX3_WHITE)

if board.DEBUG:
    b1.callback = lambda b: print('Button pressed: {}'.format(b))

#message_counter = 0
#
#def can_callback(msg):
#    # pylint: disable=global-statement
#    global message_counter
#    message_counter += 1
#    print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
#    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
#        count = 100*(msg.payload[1]<<8 + msg.payload[2])
#        print("DOING SOME STUPID LOOPING", count)
#        while count > 0:
#            count -= 1
#        print("DONE with stupid looping")
#        return
#    msg.unknown_command()

# def button_callback(button): # pylint: disable=redefined-outer-name
#     if board.DEBUG:
#         print('Button pressed: {}'.format(button))
#
# b1.callback = button_callback
b1.pwm = p5
b1.autorepeat_arm_ms = 0

b2.pwm = p4

# can.subscribe(can_callback)

dht = sensors.DHT(20, bconf.AUX2_YELLOW, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(5))

def r():
    board.restart()

if 1 == 1: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run  restart   (or board.run()) to start event handler')
