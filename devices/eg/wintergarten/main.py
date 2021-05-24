"""
wintergarten main.py

3 buttons
7 PWM
1 temp sensor
"""

# pylint: disable=multiple-statements
#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)
import net; net.start_wlan(); net.start_repl()

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements, no-member
# pylint: disable=wrong-import-order, redefined-outer-name
# pylint: disable=unused-import

# import can
# can.CAN(0x200)

import board

board.LOCATION = 'eg_wintergarten'


import gc
import pwm
import sensors
# import utime
import memstat
import umqttsimple
import fsmqtt
import schedule

board.MQTT = fsmqtt.MQTTClient().connect()


#
p1 = pwm.PWM(1, 18)
p2 = pwm.PWM(2, 14)
p3 = pwm.PWM(3, 26)
p4 = pwm.PWM(4, 23)
p5 = pwm.PWM(5, 22)
p6 = pwm.PWM(6, 12)
p7 = pwm.PWM(7, 5)

p14 = pwm.PWMList(10, p1, p2, p3, p4)
p57 = pwm.PWMList(11, p5, p6, p7)
all = pwm.PWMList(99, p1, p2, p3, p4, p5, p6, p7)

pa = pwm.PWMList(12, p1, p3)

# t1 =

def a(v=.01):
    p14.dimf(v)
def b():
    p14.dimi(0)

pall = pwm.PWMList(13, p1, p2, p3, p4, p5, p6, p7)
#
temperature = sensors.DHT(16, 21, poll_intervall_in_ms=sensors.poll_1_minute)

b = sensors.Brightness(17, 39, poll_intervall_in_ms=5000)

ping = sensors.PingDevice()

sensors.proclaim()

message_counter = 0

def callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")

# board.CAN.subscribe(True, callback)

def dd(a, b):
    p1.dimi(a)
    p2.dimi(b)

def d1(): dd(0, 1000)
def d2(): dd(1000, 0)

running = True
delay_ms = 100
def ddloop():
    while running:
        m1 = gc.mem_free()
        d1()
        pwm.dimlist.wait()
        d2()
        pwm.dimlist.wait()
        m2 = gc.mem_free()
        print('Mem Used: {}'.format(m1-m2))

def alloff():
    pwm.ALL.dimi(0)

def alloff_in(seconds):
    schedule.run_in_ms(1000*seconds, alloff)
