
"""
cancommon.py

Common CAN definitions

Basic configuration commands common to all applications are handled by this layer.

Config commands (assuming CAN address 100)

cansend 100#fd # START WLAN and repl
cansend 100#fe # STOP WLAN and repl

cansend 200#fd # START WLAN and repl

"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

#import utime
import net
import machine
import board
import canconf

# if 0 == 1:
#     # make pylint think that it knows about 'const' variable
#     # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
#     const = const
#
# # CANID_POWER_ON message sent to the CAN Bus
# CANID_POWER_ON = const(0x3c4)
# CANID_IDENTIFY = const(0x3c5)
# CANID_DATALOGGER_AM2302 = const(0x6f1)
# CANID_PING = const(0x7e0)
# CANID_WLAN_CONNECTED = const(0x3c6)
# CANID_PWM_VALUE = const(0x03c8)
# CANID_DATALOGGER_BRIGHTNESS_SENSOR_8 = const(0x6f6) #
#
# # CAN commands and configuration handled by each device
# # All general config commands must be >= 0xe8
#
# CONFIG_BEGIN = const(0xf0)
#
# CONFIG_HARD_RESET = const(0xf0)
# CONFIG_SOFT_RESET = const(0xf1)
# CONFIG_SEND_PING = const(0xf2)
# CONFIG_INDENTIFY = const(0xf3)
#
# # Network config
# CONFIG_WLAN_CONNECT = const(0xfa)
# CONFIG_WLAN_HOTSPOT = const(0xfb)
# CONFIG_WLAN_STOP = const(0xfc)
# CONFIG_WEBREPL_START = const(0xfd)
# CONFIG_WEBREPL_STOP = const(0xfe)
#
#
#
# def _payloadstring(payload):
#     return ' '.join('{:02x}'.format(x) for x in payload)
#
# class Message:
#     """A CAN message"""
#     # pylint: disable=too-few-public-methods
#     def __init__(self, canid, payload):
#         self.canid = canid
#         self.payload = payload
#
#     def payloadstring(self):
#         return _payloadstring(self.payload)
#
#     def __repr__(self):
#         return '<Message #{:03x} [{}] {}>'.format(self.canid, len(self.payload), self.payloadstring())
#
#     def setsender(self, senderid):
#         """Fill canid and senderid"""
#         if board.CAN is None:
#             return
#         self.payload[0] = board.CAN.canid >> 8
#         self.payload[1] = board.CAN.canid & 0xff
#         self.payload[2] = senderid
#
#     def send(self):
#         """Send message"""
#         if board.CAN is None:
#             return
#         board.CAN.can.send(self.payload, self.canid)
#
# def makemessage(canid, size):
#     return Message(canid, [0]*size)
#
# Badmessage = Message(0x777, [1, 2, 3, 4])


# def read(self):
#     """Read a CAN message"""
#     packet = self.can.recv()
#     return Message(packet[0], packet[3])
#
#
# _pingmessage = Message(CANID_PING, [0, 0, 0, 0, 0, 0])
# def send_ping(self):
#     """Send a ping message"""
#     # Hack ... this should be a member of class CAN, we treat self like this
#     now = utime.time()
#     # use pre-allocated message to avoid garbage collection
#     b = _pingmessage.payload
#     b[0] = self.canid >> 8
#     b[1] = self.canid & 0xff
#     b[2] = (now >> 24) & 0xff
#     b[3] = (now >> 16) & 0xff
#     b[4] = (now >>  8) & 0xff
#     b[5] = (now >>  0) & 0xff
#     _pingmessage.send()
#
# # power-on or identify token
# def _identify(self, packetid):
#     if self.canid is not None:
#         serial = machine.unique_id()
#         self.can.send([self.canid >>8, self.canid & 0xff,
#                 machine.reset_cause(), # startup reason
#                 2, # HClib Version
#                 12, # HW Type -- make this 12 for ESP32 ..
#                 0xa0, # Application type and Version - make this the library version
#                 serial[-2], serial[-1]], # CPU serial
#             packetid)
#
#
# def send_poweron(self):
#     """Send a power-on message to the bus"""
#     # Hack ... this should be a member of class CAN, we treat self like this
#     _identify(self, CANID_POWER_ON)
#
# def register(self):
#     """Register global CAN device to be used by other modules"""
#     board.CAN = self
#     send_poweron(self)



# Compile once to save mallocs with every CAN package

_CONFIG_SOFT_RESET = bytearray([canconf.SOFT_RESET])
_CONFIG_HARD_RESET = bytearray([canconf.HARD_RESET])
_CONFIG_SEND_PING = bytearray([canconf.SEND_PING])
_CONFIG_WLAN_CONNECT = bytearray([canconf.WLAN_CONNECT])
_CONFIG_WLAN_HOTSPOT = bytearray([canconf.WLAN_HOTSPOT])
_CONFIG_WLAN_STOP = bytearray([canconf.WLAN_STOP])
_CONFIG_WEBREPL_START = bytearray([canconf.WEBREPL_START])
_CONFIG_WEBREPL_STOP = bytearray([canconf.WEBREPL_STOP])
_CONFIG_INDENTIFY = bytearray([canconf.INDENTIFY])

def handle_standard_config_command(self, payload):
    """Return True if standard CAN command has been found and processed"""
    # Hack ... this should be a member of class CAN, we treat self like this
    # pylint: disable=too-many-return-statements
    if len(payload) < 1 or payload[0] < canconf.CONFIG_BEGIN:
        return False

    if payload in (_CONFIG_WLAN_CONNECT, _CONFIG_WLAN_HOTSPOT):
        if payload == _CONFIG_WLAN_CONNECT:
            ip = net.start_wlan()
        else:
            ip = net.start_hotspot()
        board.LED.on()
        ipx = list(map(int, ip[0].split('.')))
        #print('ipx', ipx)
        self.send_wlan_connected(ipx)
        #self.send(CANID_WLAN_CONNECTED, [self.canid >>8, self.canid & 0xff, ipx[0], ipx[1], ipx[2], ipx[3]])
        return True

    if payload == _CONFIG_INDENTIFY:
        self.identify()
        return True

    if payload == _CONFIG_WLAN_STOP:
        net.stop_wlan()
        return True

    if payload == _CONFIG_WEBREPL_START:
        net.start_repl()
        return True

    if payload == _CONFIG_WEBREPL_STOP:
        net.stop_repl()
        return True

    if payload == _CONFIG_SEND_PING:
        self.send_ping()
        return True

    if payload == _CONFIG_SOFT_RESET:
        machine.soft_reset()

    if payload == _CONFIG_HARD_RESET:
        machine.reset()

    return False
