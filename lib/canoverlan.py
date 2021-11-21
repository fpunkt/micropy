"""
CAN bus over [W]LAN
"""

import board
import sys
import net
import cancommon

try:
    import uasyncio as asyncio
except:
    import asyncio

try:
    import usocket as socket
except:
    import socket

_sock = None

def init(brokerip=None, port=14711):
    global _sock
    cfg = net.start_wlan()
    # ipx = list(map(int, cfg[0].split('.')))
    if brokerip is None:
        if cfg[0][0] == '10':
            brokerip = '10.10.4.2'
        else:
            brokerip = '192.168.178.4'

    addr_info = socket.getaddrinfo(brokerip, port)
    addr = addr_info[0][-1]
    if sys.platform == 'linux':
        print('# connecting to {}.{}.{}.{}'.format(addr[4], addr[5], addr[6], addr[7]))
    else:
        if board.DEBUG:
            print('# connecting to {}:{}'.format(addr[0], addr[1]))
    _sock = socket.socket()
    _sock.connect(addr)
    cancommon.send_poweron()

async def can_receiver():
    while True:
        if _sock is None:
            await asyncio.sleep(2)
            continue
        try:
            print('# CAN going to wait for message')
            res = await asyncio.StreamReader(_sock).read(12)
            cancommon.static_incomming_message.canid = (res[0]<<8) | res[1]
            cancommon.static_incomming_message.payload = res[4:len(res)-4]
            print('Got message {}'.format(cancommon.static_incomming_message))
            cancommon.dispatch_incomming_message()
        except:
            sys.exit(1)

board.BACKGROUND_RUNNERS.append(can_receiver())


sendbuffer = bytearray([0]*12)

def write(canid, buffer):
    if _sock is None:
        return
    sendbuffer[0] = (canid >>  8) & 0xff
    sendbuffer[1] = (canid >>  0) & 0xff
    sendbuffer[3] = len(buffer)
    # print('# CAN sending buffer {} --> {}'.format(buffer, type(buffer)))
    if isinstance(buffer, (list, tuple)):
        buffer = bytearray(buffer)
    try:
        sendbuffer[4:4+len(buffer)] = buffer
        # print('sending msg 0x{:03x}, len={}, bytes={}'.format(canid, len(buffer), buffer))
        _sock.write(sendbuffer)
    except Exception as e:
        print('# ** ERROR: cannot sent 0x{:03x} {}: {}'.format(canid, buffer, e))

# async def sender():
#     while True:
#         b = bytearray([1, 2, 3])
#         send(0x123, b)
#         await asyncio.sleep(5)
#
# async def main():
#     p1 = asyncio.create_task(receiver())
#     p2 = asyncio.create_task(sender())
#     while True:
#         await asyncio.sleep(100)
#     #asyncio.gather(p1, p2)
#     #asyncio.gather(receiver(), sender())
#
# asyncio.run(main())
