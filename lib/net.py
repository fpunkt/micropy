"""
Start network and webrepl

ampy -p /dev/ttyUSB0 run net.py

When network is up you can use

    webrepl_cli.py -p x file $ip:

to copy files or you can point your web-browser to

/home/frank/Projects/fpunkts/micropy/webrepl/webrepl.html

to open a command terminal

"""

# pylint: disable=import-error, missing-docstring, wrong-import-order


import time

import secrets
import machine
import network
import webrepl

import board

# ap = network.WLAN(network.AP_IF)
# print(ap.ifconfig())
# # ('192.168.4.1', '255.255.255.0', '192.168.4.1', '0.0.0.0')
# x = ap.active(True)
# print('network activated: ', x)

def start_wlan():
    wlan = network.WLAN(network.STA_IF) # create station interface
    if wlan.isconnected():
        cfg = wlan.ifconfig()
        #print("Already connected to ", cfg)
        return cfg
    # need some sleep, otherwise screen disconnects right away (gets reset??)
    wlan.active(True)       # activate the interface
    time.sleep(1)
    wlan.scan()             # scan for access points
    time.sleep(1)
    # pylint: disable=no-member
    wlan.connect(secrets.network, secrets.password) # connect to an AP
    for i in range(30):
        if wlan.isconnected():
            break      # check if the station is connected to an AP
        print('Trying to connect ...', i)
        time.sleep(1)
    if not wlan.isconnected():
        print('ERROR: cannot connect to WLAN.')
        return None
    cfg = wlan.ifconfig()
    board.LED.on()
    print("Connected to ", cfg)
    return cfg

def start_hotspot():
    serial = machine.unique_id()
    ap = network.WLAN(network.AP_IF) # create access-point interface
    ap.config(essid='ESP-AP-{:02x}{:02x}'.format(serial[-2], serial[-1]))
    ap.config(max_clients=3) # set how many clients can connect to the network
    ap.active(True)         # activate the interface
    time.sleep(1)
    board.LED.on()
    return serial

def stop_wlan():
    try:
        webrepl.stop()
    except: # pylint: disable=bare-except
        pass
    network.WLAN().disconnect()
    board.LED.off()

def start_repl(password='x'):
    webrepl.start(password=password)

def stop_repl():
    webrepl.stop()
