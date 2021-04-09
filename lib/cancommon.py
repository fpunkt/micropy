
"""
cancommon.py

Common CAN definitions
"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import utime
import net
import machine

CANDevice = None


if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const

# CANID_POWER_ON message sent to the CAN Bus
CANID_POWER_ON = const(0x3c4)
CANID_DATALOGGER_AM2302 = const(0x6f1)
CANID_PING = const(0x7e0)
CANID_WEBREPL_STARTED = const(0x3c6)

# CAN commands and configuration handled by each device
HARD_RESET = const(0xf0)
SOFT_RESET = const(0xf1)
SEND_PING = const(0xf2)

START_WEBREPL = const(0xfd)
START_WEBREPL_HOTSPOT = const(0xfe)

def _payloadstring(payload):
    return ' '.join('{:02x}'.format(x) for x in payload)

class Message:
    """A CAN message"""
    # pylint: disable=too-few-public-methods
    def __init__(self, canid, payload):
        self.canid = canid
        self.payload = payload

    def payloadstring(self):
        return _payloadstring(self.payload)

    def __repr__(self):
        return '<Message #{:03x} [{}] {}>'.format(self.canid, len(self.payload), self.payloadstring())

    def send(self):
        """Send message"""
        CANDevice.send(self.canid, self.payload)


def read(self):
    """Read a CAN message"""
    packet = self.can.recv()
    return Message(packet[0], packet[3])


def send_ping(self):
    """Send a ping message"""
    # Hack ... this should be a member of class CAN, we treat self like this
    ts = utime.time()
    i = self.canid
    payload = [(i >> 8) & 0xff, i & 0xff, (ts >> 24) & 0xff, (ts >> 16) & 0xff, (ts >> 8) & 0xff, (ts >> 0) & 0xff]
    self.can.send(payload, CANID_PING)

def send_poweron(self):
    """Send a power-on message to the bus"""
    # Hack ... this should be a member of class CAN, we treat self like this
    if self.canid is not None:
        serial = machine.unique_id()
        self.can.send([self.canid >>8, self.canid & 0xff,
                machine.reset_cause(), # startup reason
                2, # HClib Version
                12, # HW Type -- make this 12 for ESP32 ..
                0xa0, # Application type and Version - make this the library version
                serial[-2], serial[-1]], # CPU serial
            CANID_POWER_ON)

def register(self):
    """Register global CAN device to be used by other modules"""
    # pylint: disable=global-statement
    global CANDevice
    CANDevice = self
    send_poweron(self)


def handle_standard_config_command(self, payload):
    """Return True if standard CAN command has been found and processed"""
    # Hack ... this should be a member of class CAN, we treat self like this
    if payload == bytearray([START_WEBREPL]):
        ip = net.connect_to_wlan()
        net.start_repl()
        ipx = ip[0].split('.')
        self.send(CANID_WEBREPL_STARTED, [self.canid >>8, self.canid & 0xff, ipx[0], ipx[1], ipx[2], ipx[3]])
        return True

    if payload == bytearray([START_WEBREPL_HOTSPOT]):
        ip = net.start_hotspot()
        net.start_repl()
        self.send(CANID_WEBREPL_STARTED, [self.canid >>8, self.canid & 0xff, ip[0], ip[1], ip[2], ip[3]])
        return True

    if payload == bytearray([SEND_PING]):
        send_ping(self)
        return True

    if payload == bytearray([SOFT_RESET, 0xaf, 0xfe]):
        machine.soft_reset()

    if payload == bytearray([HARD_RESET, 0xaf, 0xfe]):
        machine.reset()

    return False
