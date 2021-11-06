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


addr_info = socket.getaddrinfo("192.168.178.4", 14711)
addr = addr_info[0][-1]
print('connecting to ', addr)
s = socket.socket()
s.connect(addr)

while True:
    s.write(b'test')
    time.sleep(1)
    # data = s.recv(500)
    # print(str(data, 'utf8'), end='')
