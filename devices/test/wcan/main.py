"""
Test the WCAN package
"""

import time
import sys

try:
    import uasyncio as asyncio
except:
    import asyncio

if sys.platform != 'linux':
    import net
    net.start_wlan()
    net.start_repl() # need for copy

import usocket as socket


import net
net.start_wlan()
net.start_repl() # need for copy

addr_info = socket.getaddrinfo("192.168.178.4", 14711)
addr = addr_info[0][-1]
if sys.platform == 'linux':
    print('# connecting to {}.{}.{}.{}'.format(addr[4], addr[5], addr[6], addr[7]))
else:
    print('# connecting to {}:{}'.format(addr[0], addr[1]))
s = socket.socket()
s.connect(addr)

async def receiver():
    sreader = asyncio.StreamReader(s)
    while True:
        try:
            res = await sreader.read(12)
            canid = (res[0]<<16) | (res[1]<<8) | res[2]
            print('Got message ', canid)
        except:
            sys.exit(1)

sendbuffer = bytearray([0]*12)

def send(canid, buffer):
    sendbuffer[0] = (canid >> 16) & 0xff
    sendbuffer[1] = (canid >>  8) & 0xff
    sendbuffer[2] = (canid >>  0) & 0xff
    sendbuffer[3] = len(buffer)
    sendbuffer[4:4+len(buffer)] = buffer
    print('sending msg 0x{:03x}, len={}, bytes={}'.format(canid, len(buffer), buffer))
    s.write(sendbuffer)

async def sender():
    while True:
        b = bytearray([1, 2, 3])
        send(0x123, b)
        await asyncio.sleep(5)

async def main():
    p1 = asyncio.create_task(receiver())
    p2 = asyncio.create_task(sender())
    while True:
        await asyncio.sleep(100)
    #asyncio.gather(p1, p2)
    #asyncio.gather(receiver(), sender())

asyncio.run(main())
