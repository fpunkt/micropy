"""
Start network and webrepl

ampy -p /dev/ttyUSB0 run net.py
"""

# pylint: disable=import-error, missing-docstring


import time

import secrets
import network
import webrepl

# ap = network.WLAN(network.AP_IF)
# print(ap.ifconfig())
# # ('192.168.4.1', '255.255.255.0', '192.168.4.1', '0.0.0.0')
# x = ap.active(True)
# print('network activated: ', x)

def connect_to_wlan():
    wlan = network.WLAN(network.STA_IF) # create station interface
    if wlan.isconnected():
        cfg = wlan.ifconfig()
        print("Already connected to ", cfg)
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
    print("Connected to ", cfg)
    return cfg

def start_repl():
    webrepl.start(password='x')
