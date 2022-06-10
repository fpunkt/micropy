"""
Kueche main.py

To update run

../../../webrepl/webrepl_cli.py -p x main.py 192.168.178.161:


3 buttons
8 PWM
1 temp sensor
"""

import board
board.LOCATION = 'kueche'
#board.DEBUG = True
board.CANID = 0x350

if board.DEBUG is True:
    print("This is eg/kueche, location {}, CANID {:03x}".format(board.LOCATION, board.CANID))

if board.DEBUG is True:
    import net
    net.start_wlan(32)
    net.start_repl()

import gc
import bconf
import config_pwmbank_1_0
config_pwmbank_1_0.patch_ml10_1(bconf)
import can
import machine
import sensors
import pwm
import button
# import pbutton as button
import uasyncio as asyncio
import motionsensor

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

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
b1 = button.Button(0x10, bconf.RJ12_2_WHITE)
b2 = button.Button(0x11, bconf.RJ12_2_GREEN)
b3 = button.Button(0x12, bconf.RJ12_2_YELLOW)
# b1 = button.Button(0x10, bconf.RJ12_1_YELLOW)
# b2 = button.Button(0x11, bconf.RJ12_1_BLUE)
# b3 = button.Button(0x12, bconf.RJ12_1_GREEN_INPUT_ONLY_NO_PULLUP)

# async def pbv():
#     while True:
#         print('b1={}, b2={}, b3={}'.format(b1.pin.value(), b2.pin.value(), b3.pin.value()))
#         await asyncio.sleep_ms(500)
#
# board.BACKGROUND_RUNNERS.append(pbv())

def _motion_callback(x):
    if board.DEBUG:
        print('Motion detected on {}'.format(x))

m1 = motionsensor.Motionsensor(0x20, bconf.AUX1_WHITE, pullup=None)
#m1.callback = _motion_callback

m2 = motionsensor.Motionsensor(0x21, bconf.AUX1_YELLOW, pullup=None)
m2.callback = _motion_callback

# def cb(but):
#     board.PRINT('got event from button {}', but)
# 
# b1.callback = cb
# b2.callback = cb

pl1 = pwm.List(None, p1, p2, p3, p4, p5)
pl2 = pwm.List(None, p1, p2, p3, p4, p5, p7)
pl3 = pwm.List(None, p1, p2, p3, p4, p5, p6, p7)
# pl1.toggle_mode = 1

b1.pwm = pl1
b2.pwm = pl2
b3.pwm = pl3

#
temperature = sensors.DHT11(0x30, bconf.AUX2_WHITE, poll_intervall_in_ms=5*60*1000)

message_counter = 0

# def can_callback(msg):
#     # pylint: disable=global-statement
#     global message_counter
#     message_counter += 1
#     # print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
# 
#     if len(msg.payload) > 3 and msg.payload[0] == 0x11:
#         count = 10*((msg.payload[1]<<8) + msg.payload[2])
#         print("DOING SOME STUPID LOOPING", count, msg.payload)
#         while count > 0:
#             count -= 1
#         print("DONE with stupid looping")
#         return
#     msg.unknown_command()
# 
# 
# can.subscribe(can_callback)

def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
