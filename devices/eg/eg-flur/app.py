"""EXPORT:

device: eg.flur.roof
room: Flur EG
location: eg-flur
zone: EG
ESPIP: 192.168.178.164


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

"""CONFIG:
path = "eg.flur.roof"
room = "Flur EG"


"""

# Connect using   picocom --baud 115420 /dev/tty.usbserial-0001

import board
# import net

board.LOCATION = 'eg-flur'
board.CANID = 0x344

poll_rate_s = None # overwrite if needed
"""Poll rate in seconds for sensors. Use system default if set to None"""

if board.DEBUG:
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

import bconf
import can
import canerror
# import machine
# import sensors
import pwm
import asyncio
import i2cdevice
# import tsl2561
import motionsensor
# import irqio
# import canid
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

try:
    # CONFIG: name = "Lichtsensor"
    b2 = bh1750.BH1750(0x31)
    """EXPORT:
    name: Lichtsensor
    """
except:
    can.cancommon.errormessage([canerror.SENSOR_DISABLED, 0x31])

try:
    # CONFIG: name = "Temperatur"
    tath = aht.AHT20(0x32, poll_intervall_in_ms=_pollrate_ms)
    """EXPORT:
    name: Temperatur
    """
except:
    can.cancommon.errormessage([canerror.SENSOR_DISABLED, 0x32])



##### under the roof connection - connected via RJ12 to terminal block

# Mitten auf dem Schrank mit I2C devices
# CONFIG: name = "Schrank"
# CONFIG: id = "schrank"
m1 = motionsensor.Motionsensor(0x10, bconf.RJ12_CENTER_1_WHITE_ML10_6, pullup=True)
"""EXPORT:
name: Schrank
id: schrank
"""


# Richtung Treppe und WZ Tür

stairs = motionsensor.Motionsensor(0x11, bconf.RJ12_EDGE_6_BLUE)
"""EXPORT:
name: Treppe
"""

doorwz = motionsensor.Motionsensor(0x12, bconf.RJ12_EDGE_5_YELLOW)
"""EXPORT:
name: WZ Tür
"""



# Haustür
m4 = motionsensor.Motionsensor(0x13, bconf.AUX2_WHITE_ML10_4)
"""EXPORT:
name: Tür
id: door
"""

ding = doorbellsensor.DoorbellSensor(0x20, bconf.AUX1_YELLOW_ML10_2)
"""EXPORT:
name: Türklingel
"""

lightoverwrite = lightswitchoverwrite.LightswitchOverwrite(0x21, bconf.AUX1_WHITE_ML10_1_CANNOT_WRITE_FLASH)
"""EXPORT:
name: Lichtschalter
"""


p1 = pwm.PWM(1, bconf.ML10_PWM_1)
"""EXPORT:
name: Spot Treppe
"""

p2 = pwm.PWM(2, bconf.ML10_PWM_2)
"""EXPORT:
name: Spot WZ Tür
"""

p3 = pwm.PWM(3, bconf.ML10_PWM_3)
"""EXPORT:
name: Spot Mitte (WZ)
"""

p4 = pwm.PWM(4, bconf.ML10_PWM_4)
"""EXPORT:
name: Spot Mitte (Tür)
"""

p5 = pwm.PWM(5, bconf.ML10_PWM_5)
"""EXPORT:
name: Spot Tür
"""


spots_all = pwm.List(0x0a, p1, p2, p3, p3, p4, p5)

spots_door = pwm.List(0x0b, p4, p5)

spots_stair = pwm.List(0x0c, p1, p2, p3)


# the 9V block - p6 is driving the DC/DC converter for p7 and p8
p6 = pwm.PWM(6, bconf.ML10_PWM_6)
p6.dimtovalue = pwm.NODIMMING
DCDCON_Value = const(1023)

class xPWM(pwm.PWM):
    """Enable DC/DC converter if one of these PWM is in use"""
    def _dbg(self, name, val):
        if board.DEBUG > 2:
            print('egflur: PWM #{}: {} to {}'.format(self.portid, name, val))

    def _dcdcon(self, v):
        if v > 0:
            if board.DEBUG > 2:
                print('egflur:  ** switching DCDC on')
            p6.set_raw(DCDCON_Value)

    def set_raw(self, ival):
        self._dbg('set_raw', ival)
        self._dcdcon(ival)
        return super().set_raw(ival)

    def seti16(self, i16):
        self._dbg('seti16', i16)
        self._dcdcon(i16)
        return super().seti16(i16)

    def dim_raw(self, value):
        self._dbg('dim_raw', value)
        self._dcdcon(value)
        return super().dim_raw(value)

    def dim_u16(self, i16):
        self._dbg('dim_u16', i16)
        self._dcdcon(i16)
        return super().dim_u16(i16)

p7 = xPWM(7, bconf.ML10_PWM_7)
"""EXPORT:
IGNORE: true
name: 9V spot not connected
"""

p8 = xPWM(8, bconf.ML10_PWM_8)
"""EXPORT:
name: Kleiner Spot Treppe
class: pwm.PWM
"""

async def send_pwm_status():
    await asyncio.sleep(2)
    all = list(spots_all) + list([p6, p7, p8])
    m = can.Message(0x777, [0, 0, 0])
    while True:
        for p in all:
            d = p.pwm.duty()
            m.payload[0] = p.id
            m.payload[1] = d >> 8
            m.payload[2] = d & 0xff
            m.send()
            await asyncio.sleep_ms(100)
        await asyncio.sleep(30 * 60)

# send status every 30 minutes
# asyncio.create_task(send_pwm_status())



async def poweroff_dcdc():
    """Turn DC/DC of if p7 and p8 are off - check in background every 60 seconds"""
    while True:
        await asyncio.sleep(60)
        newval = 0
        if p7.dimtovalue > 0 or p8.dimtovalue > 0 or p7.pwm.duty() > 0 or p8.pwm.duty() > 0:
            # trust nobody
            newval = DCDCON_Value
        if board.DEBUG > 2:
            print('egflur: checking DCDC duty {} / {}, newval={}'.format(p7.pwm.duty(), p8.pwm.duty(), newval))
        if newval != p6.pwm.duty():
            p6.set_raw(newval)

asyncio.create_task(poweroff_dcdc())

def main():
    if 1 != 0: # pylint: disable=comparison-with-itself
        board.run()
    else:
        print('# run  restart   (or board.run()) to start event handler')

## DEBUGGING STUFF
# import can, board, pwm
# msg = can.Message(0x344, [0x1a, 0x08, 0x7f, 0xff])
# board.SENSORSs.find(msg, (PWM, List), 0xa0)

