"""
Kueche main.py

This file is loaded after boot.py

3 buttons
7 PWM
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
can.CAN(0x100, rx=35, tx=32)


import pwm
import sensors
# import utime
import board
import button
import schedule

board.DEBUG = True

#board.SENSORSs = sensors.RegisteredSensorIDs()
#board.PWMs = pwm.PWMList(-1)


p0 = pwm.PWM(0, 15)
# PIN 2 is the on-PCB LED
p1 = pwm.PWM(1, 4)
p2 = pwm.PWM(2, 16)
p3 = pwm.PWM(3, 17)
p4 = pwm.PWM(4, 5)
p5 = pwm.PWM(5, 18)
p6 = pwm.PWM(6, 19)
p7 = pwm.PWM(7, 21)

#b1 = button.Button(10, 18)
#b2 = button.Button(11, 19)

# def cb(but):
#     print('got event from button {}'.format(but))
#
# b1.callback = cb
# b2.callback = cb

#b1.pwm = p1
#b2.pwm = p2

p1.lastintensity = 100
p2.lastintensity = 15
#
# temperature = sensors.DHT(16, 16, poll_intervall_in_ms=5000)

ping = sensors.PingDevice(1500)

message_counter = 0


def can_callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    # print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if pwm.handle(msg):
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

# Uncomment line below to enable the watchdog
# wd = sensors.WDT()

def r():
    schedule.run()

s = schedule.schedule_list
r()
