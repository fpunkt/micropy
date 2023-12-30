"""CONFIG:

device: eg.kueche.fridge
room: Küche
location: kueche
zone: eg
ESPIP: 192.168.178.162


3 buttons
8 PWM
1 temp sensor
"""

import board
board.CANID = 0x350

if board.DEBUG:
    print("This is eg/kueche, location {}, CANID {:03x}".format(board.LOCATION, board.CANID))

import bconf
print('boncf loaded')
import sensors
print('sensors loaded')
import pwm
print('pwm loaded')
import button
import motionsensor

print('imports loaded')

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

#board.SENSORSs = sensors.RegisteredSensorIDs()
#board.PWMs = pwm.PWMList(-1)

_defi1 = const(800)
_defi2 = const(1000)

p8 = pwm.PWM(8, bconf.ML10_PWM_8)
p8.lastintensity = _defi1

# PIN 2 is the on-PCB LED
p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p1.lastintensity = _defi1

p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p2.lastintensity = _defi1

p3 = pwm.PWM(3, bconf.ML10_PWM_3)
p3.lastintensity = _defi2

p4 = pwm.PWM(4, bconf.ML10_PWM_4)
p4.lastintensity = _defi2

p5 = pwm.PWM(5, bconf.ML10_PWM_5)

p6 = pwm.PWM(6, bconf.ML10_PWM_6)
p6.lastintensity = _defi1

p7 = pwm.PWM(7, bconf.ML10_PWM_7)
p7.lastintensity = _defi1

# PINs on left side (buttons, thermometer and motionsensors)
# 13, 12, 14, 27, 26, 25, 33
b1 = button.Button(0x10, bconf.RJ12_CENTER_1_WHITE_ML10_6)
b2 = button.Button(0x11, bconf.RJ12_CENTER_4_GREEN_ML10_7)
b3 = button.ARButton(0x12, bconf.RJ12_CENTER_5_YELLOW_ML10_3)


# m1 = motionsensor.Motionsensor(0x20, bconf.AUX1_WHITE_ML10_1_CANNOT_WRITE_FLASH)
m2 = motionsensor.Motionsensor(0x21, bconf.AUX1_YELLOW_ML10_2)


pl1 = pwm.List(None, p1, p2, p3, p4, p5)
pl2 = pwm.List(None, p1, p2, p3, p4, p5, p7)
pl3 = pwm.List(None, p1, p2, p3, p4, p5, p6, p7)


b1.pwm = pl1
b2.pwm = pl2
b3.pwm = pl3

temperature = sensors.DHT11(0x30, bconf.AUX2_WHITE_ML10_4, poll_intervall_in_ms=sensors.poll_5_minutes)
