"""
This finalises some nasty circular dependencies.
Always include this as last file in main.py

In your main program you want to use

# pylint: disable=unused-import

to suppress linter warnings
"""

import board
import pwm
import sensors

board.SENSORSs = sensors.RegisteredSensorIDs()
board.PWMs = pwm.PWMList(-1)
