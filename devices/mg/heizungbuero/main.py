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
import machine
import onewire
import ds18x20
import time
import pwm


if board.CAN and board.DEBUG:
    board.CAN.cancommon.send_wlan_connected()

p = pwm.PWM(1, bconf.AUX2_WHITE)

ds18 = machine.Pin(13)

# create the onewire object
ds = ds18x20.DS18X20(onewire.OneWire(ds18))

# scan for devices on the bus
roms = ds.scan()
print('found devices:', len(roms))

# loop 10 times and print all temperatures
while True:
    print('temperatures:', end=' ')
    ds.convert_temp()
    time.sleep_ms(2000)
    for rom in roms:
        print('{:.2f}'.format(ds.read_temp(rom)), end=' ')
    print()