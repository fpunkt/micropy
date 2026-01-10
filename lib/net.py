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
import sys
import asyncio
import utime
import gc
import c

try:
    import board
    PRINTF = board.PRINTF
except ImportError:
    PRINTF = print

network.country('DE')

class NET:
    def __init__(self, base=32, strongest=False):
        self.after_connect = []
        self.status = "disconnected"
        self.wlan = network.WLAN(network.STA_IF) 
        self._base = base
        self._strongest = strongest
        self._isconnected = None
        self._keepalive_task = None

    def isconnected(self):
        """Return True if connected to WLAN"""
        return self.wlan.isconnected()

    async def wait_for_connection(self):
        """Wait until network is connected"""
        if self.wlan.isconnected():
            return True
        if self._isconnected is None:
            self.connect()

        await self._isconnected.wait()
        return True

    def connect(self, timeout=30, repl=True):
        """Connect to WLAN in background and keep connection alive, i.e. reconnect if connection is lost
        The function does not wait for connection and a keepalive task is started."""
        if self._keepalive_task is not None:
            # already connected
            return
        if self._isconnected is None:
            self._isconnected = asyncio.Event()
        if self._keepalive_task is None:
            self._keepalive_task = asyncio.create_task(self._keepalive())
        if repl:
            self.start_repl()

    async def _keepalive(self):
        last_print = utime.ticks_ms()
        while True:
            if self.wlan.isconnected():
                self._isconnected.set()
                if self.status != "connected":
                    PRINTF("Connected to {}", self.wlan.ifconfig())
                    self.status = "connected"
                    try:
                        sys.modules['cancommon'].send_wlan_connected()
                    except Exception as e:
                        pass
                    for func in self.after_connect:
                        try:
                            func()
                        except Exception as e:
                            PRINTF("ERROR: cannot run after_connect function: {}", e)
                await asyncio.sleep_ms(100)
                continue

            self._isconnected.clear()

            if self.status == "disconnected":
                self._reset_wlan()
                self.status = "connecting"

            if self.status == "connecting":
                if utime.ticks_diff(utime.ticks_ms(), last_print) > 5000:
                    PRINTF("Waiting for connection..., status: {}", self.wlan.status())
                    last_print = utime.ticks_ms()
                await asyncio.sleep_ms(100)
                continue

            if self.status == "connected":
                PRINTF("Huh? connected?")
                await asyncio.sleep_ms(100)
                continue

            PRINTF("Huh? unknown status: {}", self.status)
            await asyncio.sleep_ms(100)
            continue
            

    def _reset_wlan(self):
        """reset WLAN and start connecting. Note: the function does not wait for connection"""
        # self.stop_hotspot()

        self.wlan.active(False)
        utime.sleep_ms(100)
        self.wlan.active(True)       # activate the interface
        self.wlan.disconnect()  # ensure clean start
        utime.sleep_ms(100)
        s, p = c.s(self._base)
        bs = s.encode('utf-8')
        bssid = None
        bssids = None
        if self._strongest: 
            # try to find the strongest AP
            ap = self.wlan.scan()
            # print(f'Found AP: {ap}')
            ap = list(filter(lambda x: x[0] == bs, ap))
            # print(f'Filtered AP: {ap}')
            ap.sort(key=lambda x: x[3], reverse=True)
            if ap:
                bssid = ap[0][1]
                bssids = format_mac(bssid)

        PRINTF('Connecting to SSID: {} BSSID: {} password: "{}..."', s, bssids, p[:1])
        self.wlan.connect(bs, p, bssid=bssid)

    def ipstring(self):
        """Return IP address as string"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None

    def mac_address(self, sep=":"):
        """Return MAC address as string, using sep as separator. If sep is None, return bytes."""
        mac = self.wlan.config('mac')
        if sep is None:
            return mac
        return format_mac(mac, sep)

    def rssi(self):
        """Return RSSI of current connection"""
        return self.wlan.status('rssi')

    def start_wlan(self, timeout=30, repl=True, password='x'):
        """Connect to WLAN (start task and wait for connection, no background monitoring of connection)"""
        self._reset_wlan()
        now = utime.ticks_ms()  
        last_print = now - 5001
        while not self.wlan.isconnected():
            if utime.ticks_diff(utime.ticks_ms(), last_print) > 5000:
                PRINTF("Waiting for connection..., status: {}", self.wlan.status())
                last_print = utime.ticks_ms()
            if utime.ticks_diff(utime.ticks_ms(), now) > timeout * 1000:
                break
            utime.sleep_ms(100)
        PRINTF("Connected to {}", self.wlan.ifconfig())
        if repl:
            webrepl.start(password=password)

    def stop(self):
        """Stop WLAN"""
        self.wlan.disconnect()
        self.wlan.active(False)

    def start_repl(self, password='x'):
        """Start REPL"""
        self.connect()
        webrepl.start(password=password)
        board.MQTT.publish("info/repl", "REPL started")

    def stop_repl(self):
        """Stop REPL"""
        webrepl.stop()
        board.MQTT.publish("info/repl", "REPL stopped")

    def xxx_stop_hotspot(self):
        """Stop hotspot"""
        ap = network.WLAN(network.AP_IF) # create access-point interface
        ap.active(False)

    def xxx_start_hotspot(self):
        """Start hotspot"""
        self.stop()
        self.wlan.active(False)
        self.wlan.active(True)
        ap = network.WLAN(network.AP_IF) # create access-point interface
        ap.config(essid='ESP-AP-{:02x}{:02x}'.format(machine.unique_id()[-2], machine.unique_id()[-1]))
        ap.config(max_clients=3) # set how many clients can connect to the network
        ap.active(True)         # activate the interface
        time.sleep(1)
        return machine.unique_id()


try:
    board.NET = NET()
except NameError:
    pass

def format_mac(mac_bytes, sep=":"):
    """Format bytes/iterable as hex MAC (xx:xx:...)."""
    try:
        return sep.join("{:02X}".format(b) for b in mac_bytes)
    except Exception:
        return str(mac_bytes)


