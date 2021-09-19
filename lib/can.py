"""
CAN version using constant polling from the even loop.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import gc
import machine
import canid
import canconf
import board
import canerror
import net
import uasyncio as asyncio


class Message:
    """A CAN message"""
    # pylint: disable=too-few-public-methods
    def __init__(self, cid, payload):
        self.canid = cid
        self.payload = payload

    def payloadstring(self):
        return ' '.join('{:02x}'.format(x) for x in self.payload)
        # return _payloadstring(self.payload)

    def __repr__(self):
        return '<Message #{:03x} [{}] {}>'.format(self.canid, len(self.payload), self.payloadstring())

    def setsender(self, senderid):
        """Fill canid and senderid"""
        if board.CAN is None:
            return
        self.payload[0] = board.CAN.canid >> 8
        self.payload[1] = board.CAN.canid & 0xff
        self.payload[2] = senderid

    def send(self):
        """Send message"""
        if board.CAN is None:
            return
        # board.CAN.can.send(self.payload, self.canid)
        board.CAN.send(self.canid, self.payload)

    def u16(self, pos):
        return (self.payload[pos] << 8) + self.payload[pos+1]


    def bad_number_of_args(self, min, max=None):
        p = self.payload
        if len(p) < 1:
            errormessage([canerror.INTERNAL_ERROR, 0xa0])
            return
        # fmt.Sprintf("Bad number of parameters for command #%02x: got %d expected %d .. %d", d[0], d[1], d[2], d[3])
        if max is None:
            max = min
        errormessage([canerror.BAD_NUMBER_OF_PARAMETERS, p[0], len(p), min, max])

    # "Command #%02x: bad value for paramenter %d, found %d expected, %d .. %d", d0, d1, d2, d3, d4)
    def bad_parameter_value(self, n, min, max):
        p = self.payload
        pn = 0
        if n >= len(p):
            if board.DEBUG:
                print('want param {} for {}'.format(n, self))
            errormessage([canerror.INTERNAL_ERROR, 0xa1])
        else:
            pn = p[n]
        errormessage([canerror.BAD_PARAMETER_VALUE, p[0], n, pn, min, max])

    def bad_sensor_id(self):
        self.bad_parameter_value(1, 0xff, 0xff)

    def bad_sensor_type(self, expected):
        self.bad_parameter_value(1, 0xff, 0)

    def unknown_command(self):
        c = 0
        if len(self.payload) > 0:
            c = self.payload[0]
        errormessage([canerror.CAN_UNKNOWN_COMMAND, c])


def makemessage(cid, size, sensorid=None):
    m = Message(cid, [0]*size)
    if sensorid is not None:
        m.setsender(sensorid)
    return m

Badmessage = Message(0x777, [1, 2, 3, 4])


# dict of list(minargs, maxargs, callback)
_handlers = dict()

def register(commandbyte, minargs, maxargs, callback):
    if _handlers.get(commandbyte, None) is not None:
        raise RuntimeError('CAN callback for {} already defined'.format(commandbyte))

    _handlers[commandbyte] = (minargs, maxargs, callback)


# cached message to avoid mallocs
_message = Message(0, [])

class CAN:
    """Wrapper for machine.CAN, providing (some kind of) interrupt and callback"""
    def __init__(self, cid=None, rx=33, tx=32, baudrate=125, mode=machine.CAN.NORMAL):
        # self, canid=None, rx=35, tx=34, baudrate=125, mode=machine.CAN.NORMAL
        # self, canid=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        # c = machine.CAN(0, mode=machine.CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self._can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=8)
        self._callback = None
        self._subscribed_to = None
        #self._cbrunner = self._run_callback
        self.canid = cid
        self.canid_bytes = [cid >> 8, cid & 0xff]
        board.CAN = self
        self.send_poweron()
        # subscribe to standard commands so we can still switch on/off WLAN in case booting fails for whatever reason
        # self.can.callback(self._cbrunner)

    def poll(self):
        if not self._can.any():
            return False
        packet = self._can.recv()
        cid = packet[0]
        payload = packet[3]
        _message.canid = cid
        _message.payload = payload

        # check for installed handler for that message
        if cid == self.canid and len(payload) > 0:
            handler = _handlers.get(payload[0], None)
            if handler is not None:
                minargs, maxargs, callback = handler
                if len(payload) < minargs or len(payload) > maxargs:
                    if board.DEBUG:
                        print('Bad number of args {}, expected {}..{}'.format(len(payload), minargs, maxargs))
                    _message.bad_number_of_args(minargs, maxargs)
                # run the callback
                try:
                    callback(_message)
                except Exception as e: # pylint: disable=broad-except
                    if board.DEBUG:
                        print('Callback raised error: {}'.format(e))
                return True

        if self._callback is None:
            return False
        if self._subscribed_to is True or self._subscribed_to == cid:
            self._callback(Message(cid, payload))
        return True

    def subscribe(self, callback, cid=None):
        """Subscribe to packages on the CAN bus.
        cid==True subscribes to all messages
        cid==None subscribes to the own CAN ID
        cid==id subscribes to messages with the given ID"""
        if cid is None or cid is False:
            cid = self.canid
        self._subscribed_to = cid
        self._callback = callback

    def any(self):
        return self._can.any()

    def read(self):
        """Read next message from the bus"""
        packet = self._can.recv()
        return Message(packet[0], packet[3])

    def write(self, msg):
        """Write message to bus"""
        self.send(msg.canid, msg.payload)

    def _send(self, cid, payload):
        """Send packet"""
        try:
            self._can.send(payload, cid, timeout=1)
            return True

        except Exception as e: # pylint: disable=bare-except, broad-except
            if board.DEBUG:
                print("Cannot send CAN message: ", e)
            # somehow this seems to be needed to allow going on
            self._can.clear_tx_queue()
            return False

    def send(self, cid, payload):
        tryagain = 3
        while tryagain > 0:
            if self._send(cid, payload):
                return
            tryagain -= 1

    def send_poweron(self):
        """Send a power-on message to the bus"""
        self._identify(canid.POWER_ON)

    def identify(self):
        self._identify(canid.IDENTIFY)

    def send_wlan_connected(self, ip):
        """Send a WLAN connected packet with IP."""
        self.send(canid.WLAN_CONNECTED, [self.canid >>8, self.canid & 0xff, ip[0], ip[1], ip[2], ip[3]])

    def send_ping(self):
        """Send a ping message"""
        # Hack ... this should be a member of class CAN, we treat self like this
        uptime = board.uptime_s()
        # use pre-allocated message to avoid garbage collection
        b = _pingmessage.payload
        b[0] = self.canid >> 8
        b[1] = self.canid & 0xff
        b[2] = (uptime >> 24) & 0xff
        b[3] = (uptime >> 16) & 0xff
        b[4] = (uptime >>  8) & 0xff
        b[5] = (uptime >>  0) & 0xff
        _pingmessage.send()

    def _identify(self, packetid):
        if self.canid is not None:
            serial = machine.unique_id()
            self.send(packetid, [self.canid >>8, self.canid & 0xff,
                    machine.reset_cause(), # startup reason
                    2, # HClib Version
                    12, # HW Type -- make this 12 for ESP32 ..
                    0xa0, # Application type and Version - make this the library version
                    serial[-2], serial[-1]]) # CPU serial

# allocate once
_pingmessage = Message(canid.PING_MESSAGE, [0, 0, 0, 0, 0, 0])
Badmessage = Message(0x777, [1, 2, 3, 4])

# cache message, only update payload. OK since with asyncio the will be no raceing
_errormessage = Message(canid.ERROR_MESSAGE, [])

def errormessage(payload):
    if board.CAN is None:
        return
    _errormessage.payload = board.CAN.canid_bytes + payload
    _errormessage.send()

# setup standard tasks

async def _poll_CAN():
    # CAN initialized ?
    while board.CAN is None:
        await asyncio.sleep_ms(500)

    while True:
        board.CAN.poll()
        await asyncio.sleep_ms(1)

board.BACKGROUND_RUNNERS.append(_poll_CAN())


async def _ping_job():
    while True:
        if board.CAN is not None:
            board.CAN.send_ping()
        if board.MQTT is not None:
            board.MQTT.publish('info/uptime/{}'.format(board.LOCATION), str(board.uptime_s()))
        await asyncio.sleep(2)

board.BACKGROUND_RUNNERS.append(_ping_job())

_memstat_message = Message(0x765, [0, 0, 0, 0])
def _send_memstat():
    b = _memstat_message.payload
    b[0] = _memstat_message.canid >> 8
    b[1] = _memstat_message.canid & 0xff
    free = gc.mem_free()     # pylint: disable=no-member
    b[2] = free >> 8
    b[3] = free & 0xff
    _memstat_message.send()

async def _memstat_jop():
    while True:
        _send_memstat()
        await asyncio.sleep(2)

board.BACKGROUND_RUNNERS.append(_memstat_jop())


### Common config commands

# Basic configuration commands common to all applications are handled by this layer.
#
# Config commands (assuming CAN address 100)
#
# cansend 100#fd # START WLAN and repl
# cansend 100#fe # STOP WLAN and repl
#
# cansend 200#fd # START WLAN and repl

def _connect(ip):
    board.LED.on()
    ipx = list(map(int, ip[0].split('.')))
    #print('ipx', ipx)
    board.CAN.send_wlan_connected(ipx)

register(canconf.WLAN_CONNECT, 1, 1, lambda _: _connect(net.start_wlan()))
register(canconf.WLAN_HOTSPOT, 1, 1, lambda _: _connect(net.start_hotspot()))
register(canconf.WLAN_STOP, 1, 1, lambda _: net.stop_wlan())
register(canconf.SEND_PING, 1, 1, lambda _: board.CAN.send_ping())
register(canconf.SOFT_RESET, 1, 1, lambda _: machine.soft_reset())
register(canconf.HARD_RESET, 1, 1, lambda _: machine.reset())
register(canconf.INDENTIFY, 1, 1, lambda _: board.CAN.identify())
register(canconf.WEBREPL_START, 1, 1, lambda _: net.start_repl())
register(canconf.WEBREPL_STOP, 1, 1, lambda _: net.stop_repl())

### Provide convenient access to global CAN instance (stored in board.CAN)

def subscribe(callback, cid=None):
    board.CAN.subscribe(callback, cid)

def read():
    return board.CAN.read()

def any():
    return board.CAN.any()
