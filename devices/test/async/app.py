"""
async app
"""

import board
board.DEBUG = 2
import fsmqtt
import pwm
# import net

p1 = pwm.PWM(1, 2)

board.set_global('p1', p1)

board.LOCATION = "test"

# board.NET.connect()

board.MQTT.connect()

