"""
Start network and webrepl

ampy -p /dev/ttyUSB0 run net.py

When network is up you can use

    webrepl_cli.py -p x file $ip:

to copy files or you can point your web-browser to

/home/frank/Projects/fpunkts/micropy/webrepl/webrepl.html

to open a command terminal

To get the MAC address of the chip run

import network
':'.join(map('{:02x}'.format, wlan.config('mac')))

"""

# pylint: disable=import-error, missing-docstring, wrong-import-order


import time

# import secrets
import machine
import network
import webrepl
import gc
import c

LED = None # filled in later, avoid import of board.py (easier bootstep on 1M boards)
DEBUG = None

# import board

# ap = network.WLAN(network.AP_IF)
# print(ap.ifconfig())
# # ('192.168.4.1', '255.255.255.0', '192.168.4.1', '0.0.0.0')
# x = ap.active(True)
# print('network activated: ', x)

def start_wlan(base=0):
    gc.collect()
    stop_hotspot()
    wlan = network.WLAN(network.STA_IF) # create station interface
    if wlan.isconnected():
        cfg = wlan.ifconfig()
        #print("Already connected to ", cfg)
        return cfg
    # need some sleep, otherwise screen disconnects right away (gets reset??)
    wlan.active(True)       # activate the interface
    time.sleep(1)
    # TODO: why do we scan for access points?
    #wlan.scan()             # scan for access points
    #time.sleep(1)
    # pylint: disable=no-member
    s, p = c.s(base)
#    if DEBUG:
#        print('Connect to {} / {}'.format(s, p))
    wlan.connect(s, p) # connect to an AP
    for i in range(30):
        if wlan.isconnected():
            break      # check if the station is connected to an AP
        print('Trying to connect ...', i)
        time.sleep(1)
    if not wlan.isconnected():
        print('ERROR: cannot connect to WLAN.')
        return None
    cfg = wlan.ifconfig()
    if LED:
        LED.on()
    print("Connected to ", cfg)
    return cfg

def wlan_ip(ipstring=None):
    if ipstring is None:
        wlan = network.WLAN(network.STA_IF) # create station interface
        if wlan.isconnected():
            return wlan.ifconfig()
    return None

def start_hotspot():
    serial = machine.unique_id()
    ap = network.WLAN(network.AP_IF) # create access-point interface
    ap.config(essid='ESP-AP-{:02x}{:02x}'.format(serial[-2], serial[-1]))
    ap.config(max_clients=3) # set how many clients can connect to the network
    ap.active(True)         # activate the interface
    time.sleep(1)
    if LED:
        LED.on()
    return serial

def stop_hotspot():
    ap = network.WLAN(network.AP_IF) # create access-point interface
    ap.active(False)

def stop_wlan():
    try:
        webrepl.stop()
    except: # pylint: disable=bare-except
        pass
    network.WLAN().disconnect()
    network.WLAN().active(False)
    if LED:
        LED.off()

def start_repl(password='x'):
    webrepl.start(password=password)

def stop_repl():
    webrepl.stop()

