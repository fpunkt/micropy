"""
Lüfter an der Heizung

"""

import board

board.LOCATION = 'officeheizung'
board.DEBUG = True
board.CANID = 0x100


if board.DEBUG is True:
    # board.CANID = 0x10
    print("This is {}, CANID {:03x}".format(board.LOCATION, 0 if board.CANID is None else board.CANID))
    import net
    net.DEBUG = True
    net.net(32)

import bconf
import can
import time
import pwm
import digiio
import ds1820
import sys


if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

#px = pwm.PWM(29, bconf.AUX2_WHITE)

p1 = pwm.PWM(1, bconf.ML10_PWM_1)
p2 = pwm.PWM(2, bconf.ML10_PWM_2)
p3 = pwm.PWM(3, bconf.ML10_PWM_3)
pall = pwm.List(0x0f, p1, p2, p3)
pall.disable_dimming()

# control motors
pp = digiio.DigitalOut(0x0e, bconf.ML10_PWM_5)


ds = ds1820.DS1820(0x10, bconf.ML10_PWM_8, poll_intervall_in_ms=10000)

prevspeed = -99

tt = ( 30,  33,  35,  38,  40,  45,  50,   55)
sp = ( -1,   0, 100, 150, 200, 300, 500, 1023)
def getspeed(t):
    if t < tt[0]:
        return -1
    for i in range(len(tt)):
        if t < tt[i]:
            return sp[i]
    return tt[-1]

def dscallback(t):
    global prevspeed
    # print('ds callback: ', t)
    # pick the 2nd highest temperature
    t.sort(reverse=True)
    m = t[1]
    speed = getspeed(m)
    #print('ds callback, max={:4.1f}, speed={:4d}({:4d}), {}'.format(m, speed, prevspeed, t))
    if prevspeed == speed:
        return
    prevspeed = speed
    if speed >= 0:
        print('Fan on, speed {:4d}'.format(speed))
        pall.seti(speed)
        pp.on()
    else:
        print('Fan OFF')
        pp.off()


ds.callback = dscallback


def setspeed(msg):
    if msg.payload[1] >= len(pall):
        msg.bad_sensor_id()
        return
    power = int(1023*msg.payload[2]/255)
    pall[msg.payload[1]].seti(power)

can.register(0, 1, 1, lambda msg: pp.off())
can.register(1, 1, 1, lambda msg: pp.on())
can.register(2, 3, 3, setspeed)

# do a soft reset
can.register(0xaf, 1, 1, lambda msg: sys.exit())


# ds18 = machine.Pin(13)
#ds18 = machine.Pin(bconf.AUX1_YELLOW)
#ds18 = machine.Pin(bconf.ML10_PWM_8)

# create the onewire object
#ds = ds18x20.DS18X20(onewire.OneWire(ds18))

def manual_scan():
    # scan for devices on the bus
    ds.ds.scan()
    print('found devices:', len(ds.roms))
    for r in ds.roms:
        print(r)

    # loop 10 times and print all temperatures
    while True:
        print('temperatures:', end=' ')
        try:
            ds.ds.convert_temp()
            time.sleep_ms(2000)
            for r in ds.roms:
                try:
                    print('{:.2f}'.format(ds.ds.read_temp(r)), end=' ')
                except:
                    print('ERR', end=' ')
            print()
        except KeyboardInterrupt:
            break
        except:
            print('cannot read DS1820')
            pass




def r():
    board.restart()

if 1 == 1: # pylint: disable=comparison-with-itself
    board.run()
else:
    print('# run board.run() to start event handler')
