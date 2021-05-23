"""
CAN version using a callback that is called when a can packet is received
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import machine
import canid
import cancommon
import board
import utime


# def _payloadstring(payload):
#     return ' '.join('{:02x}'.format(x) for x in payload)

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
        board.CAN.can.send(self.payload, self.canid)

def makemessage(cid, size):
    return Message(cid, [0]*size)

Badmessage = Message(0x777, [1, 2, 3, 4])


def read(self):
    """Read a CAN message"""
    packet = self.can.recv()
    return Message(packet[0], packet[3])

class CAN:
    """Wrapper for machine.CAN, providing (some kind of) interrupt and callback"""
    def __init__(self, cid=None, rx=33, tx=32, baudrate=125, mode=machine.CAN.NORMAL):
        # self, canid=None, rx=35, tx=34, baudrate=125, mode=machine.CAN.NORMAL
        # self, canid=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        # c = machine.CAN(0, mode=machine.CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=8)
        self._callback = None
        self._subscribed_to = None
        self._cbrunner = self._run_callback
        self.canid = cid
        board.CAN = self
        self.send_poweron()
        # subscribe to standard commands so we can still switch on/off WLAN in case booting fails for whatever reason
        self.can.callback(self._cbrunner)

    def subscribe(self, cid, callback):
        """Subscribe to packages on the CAN bus.
        cid==True subscribes to all messages
        cid==None subscribes to the own CAN ID
        cid==id subscribes to messages with the given ID"""
        if cid is None or cid is False:
            cid = self.canid
        self._subscribed_to = cid
        self._callback = callback
        if callback is None:
            self.can.callback(None)
        else:
            self.can.callback(self._cbrunner)

    def _run_callback(self, candev):
        # print('this is __callback', self, candev)
        if not self.can.any():
            print("ERROR: CAN callback triggered from IRQ but no packet available")
            return
        packet = self.can.recv()
        cid = packet[0]
        payload = packet[3]
        if cancommon.handle_standard_config_command(self, payload):
            return
        if self._subscribed_to is True or self._subscribed_to == cid:
            self._callback(Message(cid, payload))

    def any(self):
        return self.can.any()

    def read(self):
        """Read next message from the bus"""
        packet = self.can.recv()
        return Message(packet[0], packet[3])

    def write(self, msg):
        """Write message to bus"""
        self.can.send(msg.payload, msg.canid)

    def send(self, cid, payload):
        """Send packet"""
        self.can.send(payload, cid)

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
        now = utime.time()
        # use pre-allocated message to avoid garbage collection
        b = _pingmessage.payload
        b[0] = self.canid >> 8
        b[1] = self.canid & 0xff
        b[2] = (now >> 24) & 0xff
        b[3] = (now >> 16) & 0xff
        b[4] = (now >>  8) & 0xff
        b[5] = (now >>  0) & 0xff
        _pingmessage.send()

    def _identify(self, packetid):
        if self.canid is not None:
            serial = machine.unique_id()
            self.can.send([self.canid >>8, self.canid & 0xff,
                    machine.reset_cause(), # startup reason
                    2, # HClib Version
                    12, # HW Type -- make this 12 for ESP32 ..
                    0xa0, # Application type and Version - make this the library version
                    serial[-2], serial[-1]], # CPU serial
                packetid)

# allocate once
_pingmessage = Message(canid.PING_MESSAGE, [0, 0, 0, 0, 0, 0])
Badmessage = Message(0x777, [1, 2, 3, 4])
