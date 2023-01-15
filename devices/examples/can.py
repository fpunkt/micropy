"""
Sample PWM

"""

# pylint: disable=multiple-statements
#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)
import net; net.start_wlan(); net.start_repl()

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements, no-member
# pylint: disable=wrong-import-order
# pylint: disable=unused-import

import can
# You might need to reset the chip after you changed the PIN configuration
# RX blue, TX green
# can.CAN(0x100, rx=33, tx=32)
# can.CAN(0x100, rx=36, tx=32)
# GEHT NICHT can.CAN(0x100, rx=36, tx=39)
# GEHT NICHT can.CAN(0x100, rx=39, tx=36)
# GEHT NICHT can.CAN(0x100, rx=36, tx=35)

# Two pins more or less on the side
can.CAN(0x100, rx=35, tx=32)

import board
import pwm
import sensors
import button

import setup

board.DEBUG = True

p1 = pwm.PWM(2, 13)
p3 = pwm.PWM(0, 14)
p2 = pwm.PWM(1, 12)
p6 = pwm.PWM(3, 17)
p5 = pwm.PWM(4, 26)
p4 = pwm.PWM(5, 25)
#p7 = pwm.PWM(6, 5)

b1 = button.Button(10, 18)
b2 = button.Button(11, 19)

# def cb(but):
#     print('got event from button {}'.format(but))
#
# b1.callback = cb
# b2.callback = cb

b1.pwm = p1
b2.pwm = p2

p1.lastintensity = 100
p2.lastintensity = 15


ping = sensors.PingDevice(1500)


def can_callback(msg):
    # print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if pwm.handle(msg):
        # print('Message handled by PWM')
        return
    msg.unknown_command()


board.CAN.subscribe(False, can_callback)

# Uncomment line below to enable the watchdog
board.WD.enable()

def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
