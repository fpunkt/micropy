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
    """Class to manage network connection and webrepl.
    Use board.NET to access the network from everywhere.
    The class will try to connect to the WLAN in background and keep the connection alive.
    You can add functions to be called after the connection is established by appending them
    to board.arun

    To connect manually use board.NET.start_wlan() or
    board.NET.connect() to connect in background and keep the connection alive.
    To stop the connection use board.NET.stop()
    To start the webrepl use board.NET.start_repl() and to stop it use board.NET.stop_repl().

    Manual connection:

        import net
        n = net.NET()
        n.start_wlan()
   """

    def __init__(self, base=32, strongest=False):
        self.after_connect = []
        self.status = "disconnected"
        self.wlan = network.WLAN(network.STA_IF)
        self._base = base
        self._strongest = strongest
        self._isconnected_event = asyncio.Event()
        self._keepalive_task = None
        self._wants_repl = False

    def isconnected(self):
        """Return True if connected to WLAN"""
        return self.wlan.isconnected()

    async def wait_for_connection(self, caller=None):
        """Wait until network is connected"""
        board.PRINTF("wait_for_connection called by {}. Current status: {}", caller, self.status)
        if self.wlan.isconnected():
            return True
        if self._keepalive_task is None:
            self.connect()

        await self._isconnected_event.wait()
        return True

    def connect_in_background(self, timeout=30, repl=True):
        """Connect to WLAN in background and keep connection alive, i.e. reconnect if connection is lost
        The function does not wait for connection and a keepalive task is started."""
        PRINTF("connect_in_background called. Current status: {}", self.status)
        self._wants_repl = repl
        if self.status != "connected":
            self.status = "start-connecting"
        if self._keepalive_task is not None:
            # already connected or connecting, do not start another task
            return
        self._keepalive_task = asyncio.create_task(self._keepalive())

    def xxxconnect(self, timeout=30, repl=True):
        """Connect to WLAN in background and keep connection alive, i.e. reconnect if connection is lost
        The function does not wait for connection and a keepalive task is started."""
        if self._keepalive_task is not None:
            # already connected or connecting, do not start another task
            return
        self._keepalive_task = asyncio.create_task(self._keepalive())
        if repl:
            self.start_repl()

    async def _keepalive(self):
        """Keep WLAN connection alive, reconnect if connection is lost"""
        PRINTF("Starting keepalive task for WLAN connection")
        last_print = utime.ticks_ms()
        while True:
            if self.wlan.isconnected():
                self._isconnected_event.set()
                if self.status != "connected":
                    PRINTF("Connected to {}", self.wlan.ifconfig())
                    PRINTF("Re-enabling default Wi-Fi Power Save mode...")
                    # 1 = PM_MIN_MODEM (MicroPython default power saving)
                    self.wlan.config(pm=1)
                    self.status = "connected"
                    try:
                        sys.modules['cancommon'].send_wlan_connected()
                    except Exception as e:
                        pass
                    if self._wants_repl:
                        try:
                            self.start_repl()
                        except Exception as e:
                            PRINTF("ERROR: cannot start webrepl: {}", e)
                    for func in self.after_connect:
                        try:
                            func()
                        except Exception as e:
                            PRINTF("ERROR: cannot run after_connect function: {}", e)
                # keep alive, check every 1 second
                await asyncio.sleep_ms(1000)
                continue

            self._isconnected_event.clear()

            if self.status == "connected":
                PRINTF("Lost connection to WLAN, trying to reconnect...")
                self.status = "start-connecting"

            if self.status == "start-connecting":
                PRINTF("Starting connection to WLAN...")
                await self._reset_wlan()
                self.status = "connecting"


            if self.status == "connecting":
                if utime.ticks_diff(utime.ticks_ms(), last_print) > 5000:
                    PRINTF("Waiting for connection..., status: {}", self.wlan.status())
                    last_print = utime.ticks_ms()
                await asyncio.sleep_ms(100)
                continue

            if self.status == "disconnected":
                PRINTF("Huh? disconnected?")
                await asyncio.sleep_ms(1000)
                continue

            PRINTF("Huh? unknown status: {}", self.status)
            await asyncio.sleep_ms(100)
            continue

    async def _reset_wlan(self):
        """reset WLAN and start connecting. Note: the function does not wait for connection"""
        self.wlan.active(False)
        await asyncio.sleep_ms(100)
        self.wlan.active(True)
        # !!! CRITICAL: Disable power saving (0 = PM_NONE)
        # This forces the radio to stay on and reliably process the FRITZ!Box handshake
        PRINTF("Disabling Wi-Fi Power Save mode...")
        self.wlan.config(pm=0)
        self._reset_wlan_after_activating()

    def _sync_reset_wlan(self):
        """reset WLAN and start connecting. Note: the function does not wait for connection"""
        self.wlan.active(False)
        time.sleep_ms(100)
        self.wlan.active(True)
        # This forces the radio to stay on and reliably process the FRITZ!Box handshake
        PRINTF("Disabling Wi-Fi Power Save mode...")
        self._reset_wlan_after_activating()

    def _reset_wlan_after_activating(self):
        """reset WLAN and start connecting. Note: the function does not wait for connection"""
        # self.stop_hotspot()

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
        self._sync_reset_wlan()
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
        webrepl.start(password=password)
        try:
            board.MQTT.publish("info/repl", "REPL started")
        except Exception as e:
            PRINTF("Cannot publish REPL started: {}", e)

    def stop_repl(self):
        """Stop REPL"""
        webrepl.stop()
        try:
            board.MQTT.publish("info/repl", "REPL stopped")
        except Exception as e:
            PRINTF("Cannot publish REPL stopped: {}", e)

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


### Troubleshooting

def start_wlan(timeout=30, repl=True, password='x', strongest=False):
    """Connect to WLAN (start task and wait for connection, no background monitoring of connection)"""
    try:
        net = board.NET
    except NameError:
        net = NET(strongest=strongest)
        try:
            board.NET = net
        except NameError:
            pass
    net.start_wlan(timeout=timeout, repl=repl, password=password)
    if net.wlan.isconnected():
        PRINTF("Connected to {}", net.wlan.ifconfig())
        PRINTF("RSSI:", net.wlan.status("rssi"))

    return net


def start_repl(self, password='x'):
    """Start REPL"""
    webrepl.start(password=password)

def net():
    return start_wlan()


def scan_wlan():
    """Scan for WLANs and return list of (ssid, bssid, channel, RSSI, authmode, hidden)"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep_ms(100)
    wlan.active(True)
    time.sleep_ms(100)
    networks = wlan.scan()
    for net in networks:
        ssid = net[0].decode("utf-8")
        rssi = net[3]
        print(f"Network: {ssid}, RSSI: {rssi} dBm")

def status():
    """Print WLAN status"""
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        print("Connected to WLAN")
        print("IP address:", wlan.ifconfig()[0])
        print("RSSI:", wlan.status("rssi"), "dBm")
    else:
        print("Not connected to WLAN")

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


