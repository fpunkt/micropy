"""
"""

import board
board.LOCATION = 'eg-wz-kugellampe'
board.VERSION = '2025-12-12'
# board.DEBUG = True

# if board.DEBUG is True:
#     import net
#     net.start_wlan()
#     net.start_repl()

import fsmqtt
import pwm
import machine
import bconf
import net

bconf.board.LED.on() # access bconf to avoid warnings

p1 = pwm.PWM(1, machine.Pin(5))
p2 = pwm.PWM(2, machine.Pin(6))
p3 = pwm.PWM(3, machine.Pin(7))
p4 = pwm.PWM(4, machine.Pin(9))

#p5 = pwm.PWM(55, machine.Pin(8))

net.connect_in_background()
fsmqtt.connect_in_background()


def r():
    board.restart()

try:
    if 1 == 1: # pylint: disable=comparison-with-itself
        board.run()
    else:
        print('# run  restart   (or board.run()) to start event handler')

except Exception as e: # pylint: disable=bare-except, broad-except
    print('Exception in main loop: ', e)
    print("Try to connect to WLAN")
    import net
    net.net()

