"""
EG flur
    // 2 PWM connected AUX-1 4P on beta board
    PWM ML-10
        8 PWM connected to ML-10
            5 x Spot
            1 x DC/DC
            2 x 9V spots

    AUX 1
        1 x AC sensor Türklingel
        1 x AC sensor für 12V AC vom Trafo (Licht is an)

    AUX 2
        1 x Motion              - Eingangstür, Kabel liegt unter der Decke

    RJ12 EDGE - Sensoren hängen nah bei der Treppe an der Decke
        1 x Motion Treppe
        1 x Motion WZ Tür

    RJ12 CENTER - Kabel geht auf den Schrank
        1 x I2C light sensor
        1 x I2C temperature sensor
        1 x Motionsensor
    Via ML-10 - ein ML-10 Kabel wird rausgeführt und ein PCB hängt (sichtbar) an der Decke
        1 AM2320                - Unter der Decke wäre blöd ...
        2 I2C for light sensor  - Unter der Decke wäre blöd ...
        2 x Motion              - Richtung Treppe und WZ Tür

"""

# TODO: Motion Door needs pullup (or replace sensor because not OK with 3.3V?)

import board
board.LOCATION = 'eg-flur'
board.DEBUG = True
board.CANID = 0x100

poll_rate_s = None # overwrite if needed

if board.DEBUG is True:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.DEBUG = True
    net.start_wlan(32)
    net.start_repl()

import gc
import bconf
import can
import canerror
import machine
import sensors
import pwm
import uasyncio as asyncio
import i2cdevice
import tsl2561
import motionsensor
import irqio
import canid
import bh1750
import aht
import lightswitchoverwrite
import doorbellsensor
from micropython import const

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()


_pollrate_ms = None if poll_rate_s is None else 1000 * poll_rate_s

i2c = i2cdevice.init(sda=bconf.RJ12_CENTER_4_GREEN_ML10_7, scl=bconf.RJ12_CENTER_5_YELLOW_ML10_3)
# THIS ONE WORKS FINE: sda=bconf.RJ12_CENTER_4_GREEN_ML10_7, scl=bconf.RJ12_CENTER_5_YELLOW_ML10_3
#brightness = tsl2561.TSL2561(0x30, poll_intervall_in_ms=2000)

b2 = bh1750.BH1750(0x31)

try:
    tath = aht.AHT20(0x32, poll_intervall_in_ms=_pollrate_ms)
except:
    can.cancommon.errormessage([canerror.SENSOR_DISABLED, 0x32])



##### under the roof connection - connected via RJ12 to terminal block

# Mitten auf dem Schrank mit I2C devices
m1 = motionsensor.Motionsensor(0x10, bconf.RJ12_CENTER_1_WHITE)

# Richtung Treppe und WZ Tür
m2 = motionsensor.Motionsensor(0x11, bconf.RJ12_EDGE_6_BLUE)
m3 = motionsensor.Motionsensor(0x12, bconf.RJ12_EDGE_5_YELLOW)

# Haustür
m4 = motionsensor.Motionsensor(0x13, bconf.AUX2_WHITE)

doorbell = doorbellsensor.DoorbellSensor(0x20, bconf.AUX1_YELLOW)
lightoverwrite = lightswitchoverwrite.LightswitchOverwrite(0x21, bconf.AUX1_WHITE)

#
#doorbell = irqio.IRQIO(0x17, bconf.RJ12_CENTER_6_BLUE_INPUT_ONLY, canid=canid.SENSOR_DOORBELL_PUSHED)
#lightswitchoverwrite = irqio.IRQIO(0x18, bconf.RJ12_CENTER_6_BLUE_INPUT_ONLY, canid=canid.SENSOR_LIGHTSWITCH_OVERRIDE)


p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
p4 = pwm.PWM(4, bconf.ML10_PWM_4)
p5 = pwm.PWM(5, bconf.ML10_PWM_5)

spots_all = pwm.List(0x0a, p1, p2, p3, p3, p4, p5)
spots_door = pwm.List(0x0b, p4, p5)
spots_stair = pwm.List(0x0c, p1, p2, p3)

# the 9V block - p6 is driving the DC/DC converter for p7 and p8
p6 = pwm.PWM(6, bconf.ML10_PWM_6)
p6.dimtovalue = -99 # don't dim
DCDCON_Value = const(1023)

class xPWM(pwm.PWM):
    """Enable DC/DC converter if one of these PWM is in use"""
    def seti(self, v):
        # print('seti6({})'.format(v))
        if v > 0:
            p6.seti(DCDCON_Value)
        super().seti(v)

p7 = xPWM(7, bconf.ML10_PWM_7)
p8 = xPWM(8, bconf.ML10_PWM_8)


async def poweroff_dcdc():
    """Turn DC/DC of if p7 and p8 are off - check in background every 60 seconds"""
    while True:
        await asyncio.sleep(60)
        newval = 0
        if p7.dimtovalue > 0 or p8.dimtovalue > 0 or p7.pwm.duty() > 0 or p8.pwm.duty() > 0:
            # trust nobody
            newval = DCDCON_Value
        print('Checking duty {} / {}, newval={}'.format(p7.pwm.duty(), p8.pwm.duty(), newval))
        if newval != p6.pwm.duty():
            p6.seti(newval)

board.BACKGROUND_RUNNERS.append(poweroff_dcdc())

def r():
    board.restart()

if 1 != 0: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run  restart   (or board.run()) to start event handler')

## Reste vom Trial and Error

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements



#brightness = tsl2561.TSL2561(0x30, sda=bconf.ML10_3, scl=bconf.ML10_2, poll_intervall_in_ms=2000)
# THIS ONE WORKS FINE: sda=bconf.ML10_4, scl=bconf.ML10_2,
#brightness = tsl2561.TSL2561(0x30, sda=bconf.ML10_4, scl=bconf.ML10_2, poll_intervall_in_ms=2000)


#dht = sensors.DHT(0x20, bconf.ML10_5, poll_intervall_in_ms=5000 if board.DEBUG else sensors.minutes(5))

#m1 = motionsensor.Motionsensor(0x10, bconf.ML10_6)
#m2 = motionsensor.Motionsensor(0x11, bconf.ML10_7)
#m2 = motionsensor.Motionsensor(0x11, bconf.ML10_8_INPUT_ONLY)


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
