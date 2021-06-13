"""
Kueche main.py

This file is loaded after boot.py

3 buttons
8 PWM
1 temp sensor
"""

# pylint: disable=multiple-statements
#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)
import net; net.start_wlan(); net.start_repl()

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements, no-member
# pylint: disable=wrong-import-order
# pylint: disable=unused-import

import can
can.CAN(0x350, rx=35, tx=32)

import pwm
import sensors
# import utime
import board
import button
import schedule
import motionsensor

board.DEBUG = False

#board.SENSORSs = sensors.RegisteredSensorIDs()
#board.PWMs = pwm.PWMList(-1)

_defi1 = 800
_defi2 = 1000
p0 = pwm.PWM(0, 15) # Dunsthaube warm
p0.lastintensity = _defi1

# PIN 2 is the on-PCB LED
p1 = pwm.PWM(1, 4) # Fenster
p1.lastintensity = _defi1

p2 = pwm.PWM(2, 16) # Arbeitsplatte warm
p2.lastintensity = _defi1

p3 = pwm.PWM(3, 17) # Arbeitsplatte kalt
p3.lastintensity = _defi2

p4 = pwm.PWM(4, 5) # Dunstabzug kalt
p4.lastintensity = _defi2

p5 = pwm.PWM(5, 18) # Brotdose
p5.lastintensity = _defi1

p6 = pwm.PWM(6, 19) # NC

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

m1 = motionsensor.Motionsensor(15, 25)
m1.callback = _motion_callback

m2 = motionsensor.Motionsensor(16, 26)
m2.callback = _motion_callback

def cb(but):
    PRINT('got event from button {}', but)

b1.callback = cb
b2.callback = cb

pl1 = pwm.List(0x20, p0, p1, p4)
pl2 = pwm.List(0x21, p0, p1, p2, p3, p4, p5)
pl3 = pwm.List(0x22, p0, p1, p2, p3, p4, p5, p7)
# pl1.toggle_mode = 1

b1.pwm = pl1
b2.pwm = pl3
b3.pwm = pl2

#
temperature = sensors.DHT(0x30, 33, poll_intervall_in_ms=5*60*1000)

ping = sensors.PingDevice(2*60*1000)

message_counter = 0


def can_callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    # print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if pwm.handle_can_message(msg):
        # print('Message handled by PWM')
        return
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
    schedule.run()

s = schedule.schedule_list
r()
