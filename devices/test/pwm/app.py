import board
board.LOCATION = 'test'
board.HOSTNAME = 'testc3'
board.DEBUG = True


import net
import fsmqtt
import pwm

p1 = pwm.PWM(0x01, 8)

board.NET.connect_in_background()
board.MQTT.connect_in_background()
