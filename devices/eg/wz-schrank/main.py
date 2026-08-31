"""
WZ Schrank

    PWM connected to ML-10
        1: Wandlampe
        2: Salzlampe
        3: Weihnachtslämpchen
        4:
        5: Ding-Dong Klingel
        6, 7, 8: RGB Lichterkette

    1 AM2320 on AUX-2
    2 Motionsensor on AUX-1

        2 buttons are connected to the small handleld to enable the reading light

"""

# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'wz-schrank'
#board.DEBUG = True
board.CANID = 0x338

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
import asyncio
import rgb
import digiio
import motionsensor

if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

# TODO: change DC/DC driver from PWM to PIN, make it "auto on/off" with PWM

p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
p4 = pwm.PWM(4, bconf.ML10_PWM_4)

dindongping = digiio.DigitalOut(0x30, bconf.ML10_PWM_5)

rgbkette = rgb.RGB(9, bconf.ML10_PWM_6,  bconf.ML10_PWM_7, bconf.ML10_PWM_8)
if board.DEBUG:
    print("# rgbkette initialized")

temp = sensors.DHT(0x20, bconf.AUX2_WHITE, poll_intervall_in_ms=50000 if board.DEBUG else sensors.minutes(5))

m1 = motionsensor.Motionsensor(0x10, bconf.AUX1_WHITE)
m2 = motionsensor.Motionsensor(0x11, bconf.AUX1_YELLOW)


# stop_here()

ddTrigger = asyncio.Event()
ddMS = 1000

async def dingdongtask():
    if board.DEBUG:
        print('DingDongTask started')
    while True:
        await ddTrigger.wait()
        ddTrigger.clear()
        print('DD got trigger')
        dindongping.on()
        await asyncio.sleep_ms(ddMS)
        dindongping.off()

asyncio.create_task(dingdongtask())

def dingdonghandler(msg):
    global ddMS
    #print('ddh: len={}, m={}'.format(len(msg.payload), msg.payload))
    ddMS = 50 + 10*msg.payload[1] if len(msg.payload) == 2 else 500
    ddTrigger.set()

can.register(0x30, 1, 2, dingdonghandler)

# TODO: install default can-handler that - if not overwritten - raises an error if no other handler
# was called


def r():
    board.restart()

if 1 == 1: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run  restart   (or board.run()) to start event handler')
