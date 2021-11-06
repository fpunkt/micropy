"""
Kueche main.py

To update run

../../../webrepl/webrepl_cli.py -p x main.py 192.168.178.156:


3 buttons
8 PWM
1 temp sensor
"""

import board
board.LOCATION = 'kueche'
# board.DEBUG = True
board.CANID = 0x350

if board.DEBUG is True:
    print("This is eg/kueche, location {}, CANID {:03x}".format(board.LOCATION, board.CANID))

if board.DEBUG is True:
    import net
    net.start_wlan()
    net.start_repl()

import gc
# import bconf
import can
import machine
import sensors
import pwm
import button
import uasyncio as asyncio
import motionsensor


can.CAN.init(board.CANID, rx=35, tx=32)

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

#board.SENSORSs = sensors.RegisteredSensorIDs()
#board.PWMs = pwm.PWMList(-1)

_defi1 = const(800)
_defi2 = const(1000)

p0 = pwm.PWM(0, 15) # Dunsthaube warm
p0.lastintensity = _defi1

# PIN 2 is the on-PCB LED
p1 = pwm.PWM(1, 4) # Fenster
p1.lastintensity = _defi1

p2 = pwm.PWM(2, 16) # Dunsthaube kalt
p2.lastintensity = _defi1

p3 = pwm.PWM(3, 17) # Arbeitsplatte warm
p3.lastintensity = _defi2

p4 = pwm.PWM(4, 5) # Arbeitsplatte kalt
p4.lastintensity = _defi2

p5 = pwm.PWM(5, 18) # NC

p6 = pwm.PWM(6, 19) # # Brotdose
p6.lastintensity = _defi1

p7 = pwm.PWM(7, 21) # Spüle
p7.lastintensity = _defi1

# PINs on left side (buttons, thermometer and motionsensors)
# 13, 12, 14, 27, 26, 25, 33
b1 = button.Button(10, 13)
b2 = button.Button(11, 12)
b3 = button.Button(12, 14)

def _motion_callback(x):
    if board.DEBUG:
        print('Motion detected on {}'.format(x))

m1 = motionsensor.Motionsensor(15, 25, pullup=None)
m1.callback = _motion_callback

m2 = motionsensor.Motionsensor(16, 26, pullup=None)
m2.callback = _motion_callback

def cb(but):
    board.PRINT('got event from button {}', but)

b1.callback = cb
b2.callback = cb

pl1 = pwm.List(0x20, p0, p1, p4)
pl2 = pwm.List(0x21, p0, p1, p2, p3, p4, p6)
pl3 = pwm.List(0x22, p0, p1, p2, p3, p4, p6, p7)
# pl1.toggle_mode = 1

b1.pwm = pl1
b2.pwm = pl3
b3.pwm = pl2

#
temperature = sensors.DHT(0x30, 33, poll_intervall_in_ms=5*60*1000)

message_counter = 0

def can_callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    # print("GOT CAN message #{:4d}: {}".format(message_counter, msg))

    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")
        return
    msg.unknown_command()


can.subscribe(can_callback)

def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
