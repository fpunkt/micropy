"""
EG flur
    // 2 PWM connected AUX-1 4P on beta board
    7 PWM connected to ML-10
        5 x Spot
        1 x DC/DC ??
        1 x 9V spots

    In der Zwischendecke angeschlossen
        2 x Motion              - Eingangstür und auf dem Schrank, Kabel liegt unter der Decke
        1 x Dindong
        1 x light on            - am PCB

    Via ML-10 - ein ML-10 Kabel wird rausgeführt und ein PCB hängt (sichtbar) an der Decke
        1 AM2320                - Unter der Decke wäre blöd ...
        2 I2C for light sensor  - Unter der Decke wäre blöd ...
        2 x Motion              - Richtung Treppe und WZ Tür

"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'eg-flur'
board.DEBUG = True
board.CANID = 0x100

if board.DEBUG is True:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.DEBUG = True
    net.start_wlan(0)
    net.start_repl()

import gc
import bconf
import can
import machine
import sensors
import pwm
import uasyncio as asyncio
import tsl2561
import motionsensor
import irqio
import canid

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

##### ML10 connector - devices are mounted on a connector board (small PCB with ML10 plug)

#brightness = tsl2561.TSL2561(0x30, sda=bconf.ML10_3, scl=bconf.ML10_2, poll_intervall_in_ms=2000)
brightness = tsl2561.TSL2561(0x30, sda=bconf.ML10_4, scl=bconf.ML10_2, poll_intervall_in_ms=2000)
dht = sensors.DHT(0x20, bconf.ML10_5, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(5))

m1 = motionsensor.Motionsensor(0x10, bconf.ML10_6)
#m2 = motionsensor.Motionsensor(0x11, bconf.ML10_7)
m2 = motionsensor.Motionsensor(0x11, bconf.ML10_8_INPUT_ONLY)


#
# OK, however ML10_1 (pin 12) might prevent from flashing
#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_1, scl=bconf.ML10_2, poll_intervall_in_ms=2000)


#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_4, scl=bconf.ML10_2, poll_intervall_in_ms=2000)
#Read error on TLS2561: [Errno 19] ENODEV
#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_2, scl=bconf.ML10_3, poll_intervall_in_ms=2000)

# Read error on TLS2561: [Errno 19] ENODEV
# t = tsl2561.TSL2561(0x30, sda=bconf.ML10_4, scl=bconf.ML10_3, poll_intervall_in_ms=2000)
# t = tsl2561.TSL2561(0x30, sda=bconf.ML10_3, scl=bconf.ML10_4, poll_intervall_in_ms=2000)

#E ML10_8 (1074903) gpio: io_num=34 can only be input
#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_7, scl=bconf.ML10_8, poll_intervall_in_ms=2000)

# Sensor Read Error on 0x30
#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_3, scl=bconf.ML10_4, poll_intervall_in_ms=2000)

# Read error on TLS2561: [Errno 19] ENODEV
#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_7, scl=bconf.ML10_6, poll_intervall_in_ms=2000)

# GPIO output gpio_num error
#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_8, scl=bconf.ML10_2, poll_intervall_in_ms=2000)

#t = tsl2561.TSL2561(0x30, sda=bconf.ML10_2, scl=bconf.ML10_8, poll_intervall_in_ms=2000)
#
# ML10_4 and 5 are OK for Montionsensor
#m1 = motionsensor.Motionsensor(0x10, bconf.ML10_2_INPUT_ONLY)
# m1 = motionsensor.Motionsensor(0x10, bconf.ML10_4)
# m2 = motionsensor.Motionsensor(0x11, bconf.ML10_5)


##### under the roof connection - connected via RJ12 to terminal block
#m3 = motionsensor.Motionsensor(0x15, bconf.RJ12_CENTER_1_WHITE)
#m4 = motionsensor.Motionsensor(0x16, bconf.RJ12_CENTER_5_YELLOW_ML10_3)
#
#doorbell = irqio.IRQIO(0x17, bconf.RJ12_CENTER_6_BLUE_INPUT_ONLY, canid=canid.SENSOR_DOORBELL_PUSHED)
#lightswitchoverwrite = irqio.IRQIO(0x18, bconf.RJ12_CENTER_6_BLUE_INPUT_ONLY, canid=canid.SENSOR_LIGHTSWITCH_OVERRIDE)


p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
p4 = pwm.PWM(4, bconf.ML10_PWM_4)
p5 = pwm.PWM(5, bconf.ML10_PWM_5)
p6 = pwm.PWM(6, bconf.ML10_PWM_6)
p7 = pwm.PWM(7, bconf.ML10_PWM_7)
#p8 = pwm.PWM(8, bconf.ML10_PWM_8)




#def can_callback(msg):


# can.subscribe(can_callback)


def r():
    board.restart()

if 1 != 0: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run  restart   (or board.run()) to start event handler')
