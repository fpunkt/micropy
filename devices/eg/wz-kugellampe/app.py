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
import bconf # setup LED
import net

bconf.board.LED.on() # access bconf to avoid warnings

p1 = pwm.PWM(1, machine.Pin(5))
p2 = pwm.PWM(2, machine.Pin(6))
p3 = pwm.PWM(3, machine.Pin(7))
p4 = pwm.PWM(4, machine.Pin(9))

#p5 = pwm.PWM(55, machine.Pin(8))
board.NET.connect()
board.MQTT.connect()

board.MQTT.run_forever(lambda: board.LED.off())
