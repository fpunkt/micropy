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
import uasyncio as asyncio
import gc
import c

try:
    import board
    PRINTF = board.PRINTF
    LED = board.LED
except:
    board = None
    def PRINTF(formatstring: str, *args):
        print(formatstring.format(*args))
    LED = None


wlan = network.WLAN(network.STA_IF) 

after_connect = []

# ap = network.WLAN(network.AP_IF)
# print(ap.ifconfig())
# # ('192.168.4.1', '255.255.255.0', '192.168.4.1', '0.0.0.0')
# x = ap.active(True)
# print('network activated: ', x)

def start_wlan(base=0, timeout=30):
    """Connect to WLAN using secrets.py for ssid and password"""
    global STATUS

    if wlan.isconnected():
        cfg = wlan.ifconfig()
        #print("Already connected to ", cfg)
        return cfg
    gc.collect()
    stop_hotspot()
    # need some sleep, otherwise screen disconnects right away (gets reset??)
    wlan.active(False)
    time.sleep(0.1)
    wlan.active(True)       # activate the interface
    wlan.disconnect()  # ensure clean start
    time.sleep(0.1)
    # pylint: disable=no-member
    s, p = c.s(base)
    PRINTF(f'Connecting to SSID: {s}, password: "{p}"')
    wlan.connect(s, p) # connect to an AP
    for i in range(timeout):
        s = wlan.status()
        PRINTF(f'Waiting for connection ... {i}, status={s}/{hex(s)}, connected={wlan.isconnected()}')
        if wlan.isconnected():
            break      # check if the station is connected to an AP
        time.sleep(1)
    if not wlan.isconnected():
        PRINTF('ERROR: cannot connect to WLAN.')
        wlan.active(False)
        time.sleep(0.5)
        return None
    cfg = wlan.ifconfig()
    STATUS = "connected"
    set_status_led()
    PRINTF("Connected to {}", cfg)
    return cfg

def wlan_ip(ipstring=None):
    if ipstring is None:
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
    set_status_led()
    return serial

def set_status_led():
    """Turn on LED when network is active"""
    try:
        if LED:
            if wlan_ip() != None:
                LED.on()
            else:
                LED.off()
    except:
        PRINT('net: cannot import board - OK during initial setup')


def stop_hotspot():
    ap = network.WLAN(network.AP_IF) # create access-point interface
    ap.active(False)

def stop_wlan():
    global STATUS
    try:
        webrepl.stop()
    except: # pylint: disable=bare-except
        pass
    network.WLAN().disconnect()
    network.WLAN().active(False)
    set_status_led()
    STATUS = "off"


STATUS = "undefined"

async def _connect_in_background(base=32):
    """Connect to WLAN in background"""
    global STATUS
    connect_count = 0
    while True:
        if STATUS == "undefined" or STATUS == "off":
            await asyncio.sleep_ms(500)
            continue

        if STATUS == "connected": 
            if not wlan.isconnected():
                STATUS = "connecting"
                connect_count = 0
                continue
            await asyncio.sleep_ms(5000)
            continue

        PRINTF('WLANconnect_in_background: {}', STATUS)
        if STATUS == "init_wlan":
            # initialize WLAN and try to connect
            set_status_led()
            stop_hotspot()
            wlan.active(False)
            time.sleep_ms(100)
            wlan.active(True)
            time.sleep_ms(100)
            time.sleep_ms(100)
            wlan.disconnect()
            time.sleep_ms(100)
            s, p = c.s(base)
            PRINTF('Connecting to SSID: {} password: "{}"', s, p)
            wlan.connect(s, p)
            STATUS = "connecting"
            connect_count = 0

        if STATUS == "connecting":
            # wait for connection
            if wlan.isconnected():
                STATUS = "connected"
                set_status_led()
                start_repl()
                for func in after_connect:
                    try:
                        func()
                    except Exception as e:
                        board.PRINTF('ERROR net: after_connect failed: {}', e)
                await asyncio.sleep_ms(5000)
                continue

            await asyncio.sleep_ms(500)
            connect_count += 1
            if connect_count > 30:
                PRINTF('Cannot connect to WLAN')
                # reset and try again
                STATUS = "init_wlan"
                if LED:
                    for i in range(5):
                        LED.off()
                        await asyncio.sleep_ms(100)
                        LED.on()
                        await asyncio.sleep_ms(100)
            continue

        PRINTF('connect_in_background: unknown status: {}', STATUS)
        await asyncio.sleep(1)


def connect_in_background(base=32):
    global STATUS
    start_task = STATUS == "undefined"
    STATUS = "init_wlan"
    if start_task:
        asyncio.create_task(_connect_in_background(base))

async def reconnect_if_needed():
    global STATUS
    PRINTF("reconnect_if_needed: {}", STATUS)
    while True:
        if wlan.isconnected():
            STATUS = "connected"
            return

        if STATUS == "undefined":
            STATUS = "init_wlan"
            asyncio.create_task(_connect_in_background())

        if STATUS == "off":
            STATUS = "init_wlan"

        if STATUS == "connecting" or STATUS == "init_wlan":
            await asyncio.sleep_ms(500)
            continue

        PRINTF("reconnect_if_needed: unknown status: {}", STATUS)
        await asyncio.sleep_ms(500)
    

def start_repl(password='x'):
    webrepl.start(password=password)

def stop_repl():
    webrepl.stop()

def net(base=32, timeout=30):
    """Start network and repl"""
    ip = start_wlan(base, timeout=timeout)
    # print("# Connected to ", ip[0])
    start_repl()


def format_mac(mac_bytes, sep=":"):
    """Format bytes/iterable as hex MAC (xx:xx:...)."""
    try:
        return sep.join("{:02X}".format(b) for b in mac_bytes)
    except Exception:
        return str(mac_bytes)

def get_ip_address():
    if wlan.isconnected():
        return wlan.ifconfig()[0]
    return None

def get_mac_address(sep=":"):
    """
    Try to return the device MAC address.
    - First attempt: network.WLAN(network.STA_IF).config('mac') (returns bytes).
    - Fallback: machine.unique_id() (often the same/hardware id).
    Returns bytes (if as_str=False) or formatted string (if as_str=True).
    Usage: mac = get_mac_address(); print(mac)  # 'aa:bb:cc:...'
    """
    # try network WLAN MAC
    try:
        m = wlan.config('mac')
        return format_mac(m, sep)
    except Exception:
        pass
    # fallback to machine.unique_id()
    try:
        uid = machine.unique_id()
        return format_mac(uid, sep)
    except Exception:
        return "un:de:fi:ne:d0"

