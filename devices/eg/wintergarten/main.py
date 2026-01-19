"""
wintergarten main.py

3 buttons
7 PWM
1 temp sensor
"""

# pylint: disable=multiple-statements
#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements, no-member
# pylint: disable=wrong-import-order, redefined-outer-name
# pylint: disable=unused-import

# import can
# can.CAN(0x200)

import board

board.LOCATION = 'eg_wintergarten'
board.DEBUG = True

import net
net.net(32)

import gc
import pwm
import sensors
import fsmqtt
import time

fsmqtt.connect('wg')


#
p1 = pwm.PWM(1, 18)
p2 = pwm.PWM(2, 14)
p3 = pwm.PWM(3, 26)
p4 = pwm.PWM(4, 23)
p5 = pwm.PWM(5, 22)
p6 = pwm.PWM(6, 12)
p7 = pwm.PWM(7, 5)

all = pwm.List(99, p1, p2, p3, p4, p5, p6, p7)

pa = pwm.List(12, p1, p3)

t1 = sensors.DHT(16, 21, poll_intervall_in_ms=sensors.poll_1_minute)
t2 = sensors.DHT(17, 22, poll_intervall_in_ms=sensors.poll_1_minute)

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
    p1.dim_raw(a)
    p2.dim_raw(b)

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
    pwm.ALL.dim_raw(0)

def tmqtt(id, t, h):
    fsmqtt.publish('wg/'+id, '{:.1f} {:.1f}'.format(t/10.0, h/10.0))

def dhtloop():
    while True:
        try:
            t1.measure()
            t, h = t1.decode()
            tmqtt('t1', t, h)
        except:
            pass

        try:
            t2.measure()
            t, h = t2.decode()
            tmqtt('t2', t, h)
        except:
            pass

        time.sleep(10)

dhtloop()

def r():
    board.restart()

if 1 == 1: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run board.run() to start event handler')
