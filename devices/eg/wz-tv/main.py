"""
WZ close to TV

handles

ML10 (PWM )
- 3 x spots in roof (dimmable, change color temp with intensity)
- 2 x spares in front of the window (xmas stars)
- 1 x TV lamp
- 2 x for really warm 24V LEDs

RJ12
- 2 x button - main button close to the door

Groove
- 1 x am2320
- 1 x motion

Groove
- drive 24V DC/DC for upper two PWM channels

"""

#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

import board
board.LOCATION = 'wztv'
board.DEBUG = True
board.CANID = 0x358

if board.DEBUG is True:
    # board.CANID = 0x10
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))

if board.DEBUG is True:
    import net
    net.DEBUG = True
    net.start_wlan(32)
    net.start_repl()

import gc
import bconf
import can
import machine
import sensors
import pwm
import button
import uasyncio as asyncio
import motionsensor

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

# BAD PWM backplane
# p0 = pwm.PWM(1, bconf.ML10_PWM_1)
# p1 = pwm.PWM(2, bconf.ML10_PWM_2)
# p2 = pwm.PWM(3, bconf.ML10_PWM_3)
# p3 = pwm.PWM(4, bconf.ML10_PWM_4)
# p4 = pwm.PWM(5, bconf.ML10_PWM_5)
# p5 = pwm.PWM(6, bconf.ML10_PWM_6)
# p6 = pwm.PWM(7, bconf.ML10_PWM_7)
# p7 = pwm.PWM(8, bconf.ML10_PWM_8)

p4 = pwm.PWM(4, bconf.ML10_PWM_1)
p5 = pwm.PWM(5, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
p6 = pwm.PWM(6, bconf.ML10_PWM_4)
p2 = pwm.PWM(2, bconf.ML10_PWM_5)
p7 = pwm.PWM(7, bconf.ML10_PWM_6)
p1 = pwm.PWM(1, bconf.ML10_PWM_7)
p8 = pwm.PWM(8, bconf.ML10_PWM_8)

proof = pwm.List(9, p1, p2, p3)


# PINs on left side (buttons, thermometer and motionsensors)
# 13, 12, 14, 27, 26, 25, 33
# b1 = button.Button(0x20, bconf.RJ12_1_WHITE_INPUT_ONLY)
# b2 = button.Button(0x21, bconf.RJ12_1_GREEN_INPUT_ONLY)
#b1 = button.Button(0x20, bconf.RJ12_EDGE_5_YELLOW)
#b2 = button.Button(0x21, bconf.RJ12_EDGE_6_BLUE)
b1 = button.Button(0x20, bconf.RJ12_CENTER_5_YELLOW_ML10_3)
b2 = button.Button(0x21, bconf.RJ12_CENTER_6_BLUE_INPUT_ONLY_NO_PULLUP)



b1.pwm = proof

#def _motion_callback(x):
#    if board.DEBUG:
#        print('Motion detected on {}'.format(x))

# temperature = sensors.DHT(0x40, bconf.AUX1_YELLOW, poll_intervall_in_ms=1*30*1000)
# m1 = motionsensor.Motionsensor(0x30, bconf.AUX1_WHITE)
# m1.callback = _motion_callback


#def cb(but):
#    board.PRINT('got event from button {}', but)

# b1.callback = cb
# b2.callback = cb


message_counter = 0

def can_callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")
        return
    print('Got CAN message: {}'.format(msg))
    msg.unknown_command()


can.subscribe(can_callback)
can.simplefilter(board.CANID)

import time
c = board.CAN.canesp32._hw_interface

def sf(bank, mode, value, mask):
    c.setfilter(bank, mode, (value, mask))
    m0 = None
    lastprint = time.time()
    nextprint = 2
    while True:
        if c.any():
            print('{}: {}'.format(now, c.recv()))
            lastprint = time.time()
            continue

        now = time.time()
        if now-lastprint > 5:
            m = c.info()
            print('{}: {}'.format(now, m))
            lastprint = now

        time.sleep(.1)



def r():
    board.restart()

if 1 == 1: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run board.run() to start event handler')
