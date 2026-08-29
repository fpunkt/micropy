import board
board.DEBUG = 2
board.LOCATION = 'rssi_display'
board.HOSTNAME = 'rssi_display'
board.VERSION = '1.0'

from machine import Pin, I2C
from time import sleep
from sh1106 import SH1106_I2C # Install SH1106 driver.
from random import randint
import asyncio

import net
import fsmqtt

board.PRINTF("Starting network in background")

net.connect_in_background()
fsmqtt.connect_in_background()

import oledi2c
oled = oledi2c.oled
#oled.fill(0)
#oled.text("Hallo Frank", 0, 0, 1)
#oled.show()

async def rssi_loop():
    i = 0
    while True:
        try:
            rssi = board.NET.rssi()
            board.PRINTF("rssi: {}", rssi)
            msg = 'RSSI {}'.format(rssi)
            board.MQTT.publish("rssi", rssi)
        except:
            msg = 'wait {}'.format(i)
            i += 1
        oled.fill(0)
        oled.text(msg, 0, 0, 1)
        oled.show()
        await asyncio.sleep_ms(500)


board.PRINTF("Starting RSSI loop")
board.MQTT.ignore_topics('rssi')

asyncio.create_task(rssi_loop())

