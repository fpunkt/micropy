"""
Simple PWM device controlled by MQTT.
"""

import board
board.LOCATION = 'mqttpwm'
board.VERSION = '2026-01-18'
board.DEBUG = 2
import fsmqtt

import machine
import net
import watchdog
import memstat
import asyncio
import pwm

p1 = pwm.PWM(0x01, 1, maxu16=0x7fff)
p2 = pwm.PWM(0x02, 2)
p3 = pwm.PWM(0x03, 3)
p4 = pwm.PWM(0x04, 4)


board.MQTT.connect()
