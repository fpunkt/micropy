"""EXPORT:

device: eg.kueche.fridge
room: Küche
location: kueche
zone: EG
ESPIP: 192.168.178.162


3 buttons
8 PWM
1 temp sensor

To Debug you can try

        canemu -p=8 -c 0x350 -C b -vv
"""

import board
board.CANID = 0x350

if board.DEBUG:
    print("This is eg/kueche, location {}, CANID {:03x}".format(board.LOCATION, board.CANID))

import bconf
import sensors
import pwm
import button
import motionsensor

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

#board.SENSORSs = sensors.RegisteredSensorIDs()
#board.PWMs = pwm.PWMList(-1)

_last_intensity = const(800)

xmas = pwm.PWM(8, bconf.ML10_PWM_8, lastintensity=_last_intensity)
"""EXPORT:
"""

# PIN 2 is the on-PCB LED
p1 = pwm.PWM(1, bconf.ML10_PWM_1, lastintensity=_last_intensity)
"""EXPORT:
name: Arbeitsplatte (kalt)
id: worktopcold
"""

p2 = pwm.PWM(2, bconf.ML10_PWM_2, lastintensity=_last_intensity)
"""EXPORT:
name: Abzugshaube (warm)
id: hoodwarm
"""

p3 = pwm.PWM(3, bconf.ML10_PWM_3, lastintensity=_last_intensity)
"""EXPORT:
name: Abzugshaube (kalt)
id: hoodcold
"""

p4 = pwm.PWM(4, bconf.ML10_PWM_4, lastintensity=_last_intensity)
"""EXPORT:
name: Kaffeemühle
id: coffee
"""

p5 = pwm.PWM(5, bconf.ML10_PWM_5, lastintensity=_last_intensity)
"""EXPORT:
name: Arbeitsplatte (warm)
id: worktopwarm
"""

p6 = pwm.PWM(6, bconf.ML10_PWM_6, lastintensity=_last_intensity)
"""EXPORT:
name: Eckschrank
id: corner
"""

p7 = pwm.PWM(7, bconf.ML10_PWM_7, lastintensity=_last_intensity)
"""EXPORT:
name: Spüle
id: sink
"""

# PINs on left side (buttons, thermometer and motionsensors)
# 13, 12, 14, 27, 26, 25, 33
b1 = button.Button(0x10, bconf.RJ12_CENTER_1_WHITE_ML10_6)
"""EXPORT:
"""

b2 = button.Button(0x11, bconf.RJ12_CENTER_4_GREEN_ML10_7)
"""EXPORT:
"""

b3 = button.ARButton(0x12, bconf.RJ12_CENTER_5_YELLOW_ML10_3)
"""EXPORT:
"""


# m1 = motionsensor.Motionsensor(0x20, bconf.AUX1_WHITE_ML10_1_CANNOT_WRITE_FLASH)
m2 = motionsensor.Motionsensor(0x21, bconf.AUX1_YELLOW_ML10_2)
"""EXPORT:
"""

pl1 = pwm.Scene(0xa, (p1, 0.8), (p2, 0.8), (p3, 0.7), (p4, 0.7), (p5, 0.7), (p6, 0.0), (p7, 0.0))
"""EXPORT:
name: Aribeitsplatte
"""
pl2 = pwm.Scene(0xb, (p1, 0.8), (p2, 0.8), (p3, 0.7), (p4, 0.7), (p5, 0.7), (p6, 0.0), (p7, 0.7))
"""EXPORT:
"""
pl3 = pwm.Scene(0xc, (p1, 0.8), (p2, 0.8), (p3, 0.7), (p4, 0.7), (p5, 0.7), (p6, 0.7), (p7, 0.7))
"""EXPORT:
name: Alle
"""
pl3.toggle_prefer_off = True

b1.pwm = pl1
b2.pwm = pl2
b3.pwm = pl3

temperature = sensors.DHT11(0x30, bconf.AUX2_WHITE_ML10_4, poll_intervall_in_ms=sensors.poll_5_minutes)
"""EXPORT:
"""
