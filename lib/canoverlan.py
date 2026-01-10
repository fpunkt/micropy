"""
CAN bus over [W]LAN
"""

import board
import sys
import net
import cancommon

try:
    import asyncio
except:
    import asyncio

try:
    import usocket as socket
except:
    import socket

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

_packetsize = const(22)
_canid_offset = const(8)
_dld_offset = const(13)
_payload_offset = const(14)

class _gobalvalc:
    def __init__(self):
        self.sock = None
        self.brokerip = '192.168.178.5'
        self.port = 14711

GLOBALS = _gobalvalc()

def init():
    cfg = net.start_wlan()
    if cfg is None:
        if board.DEBUG:
            print('# cannot read config from start_wlan')
        net.stop_hotspot()
        net.stop_repl()
        net.stop_wlan()
        return

    addr_info = socket.getaddrinfo(GLOBALS.brokerip, GLOBALS.port)
    addr = addr_info[0][-1]
    if sys.platform == 'linux':
        print('# connecting to {}.{}.{}.{}'.format(addr[4], addr[5], addr[6], addr[7]))
    else:
        if board.DEBUG:
            print('# connecting to {}:{}'.format(addr[0], addr[1]))
    sock = socket.socket()
    sock.connect(addr)
    GLOBALS.sock = sock
    cancommon.send_poweron()

def reconnect_if_needed():
    if GLOBALS.sock is not None:
        return
    init(GLOBALS.brokerip, GLOBALS.port)

async def reconnect_if_needed_loop():
    while True:
        reconnect_if_needed()
        await asyncio.sleep(60)


async def can_receiver():
    while True:
        if GLOBALS.sock is None:
            await asyncio.sleep(2)
            continue
        try:
            #print('# CAN going to wait for message')
            res = await asyncio.StreamReader(GLOBALS.sock).read(_packetsize)
            cancommon.static_incomming_message.canid = (res[_canid_offset]<<0) | (res[_canid_offset+1]<<8)
            cancommon.static_incomming_message.payload = res[_payload_offset:] # :len(res)-4
            print('Got message {}'.format(cancommon.static_incomming_message))
            cancommon.dispatch_incomming_message()
        except:
            sys.exit(1)

board.BACKGROUND_RUNNERS.append(can_receiver())


sendbuffer = bytearray([0]*22)

def write(canid, buffer):
    if GLOBALS.sock is None:
        return
    sendbuffer[_canid_offset+0] = (canid >>  0) & 0xff
    sendbuffer[_canid_offset+1] = (canid >>  8) & 0xff
    sendbuffer[_dld_offset] = len(buffer)
    # print('# CAN sending buffer {} --> {}'.format(buffer, type(buffer)))
    if isinstance(buffer, (list, tuple)):
        buffer = bytearray(buffer)
    try:
        sendbuffer[_payload_offset:_payload_offset+len(buffer)] = buffer
        # print('sending msg 0x{:03x}, len={}, bytes={}'.format(canid, len(buffer), buffer))
        GLOBALS.sock.write(sendbuffer)
    except Exception as e:
        print('# ** ERROR: cannot sent 0x{:03x} {}: {}'.format(canid, buffer, e))
