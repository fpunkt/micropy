"""
Main Module.

Function main is executed after standard inits
"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=unused-import, multiple-statements, redefined-outer-name

import can

# start CAN first, otherwise bus is in undefined state
c = can.CAN(0x100)

import sensors
import utime
import machine
import uasyncio as asyncio

message_counter = 0

def callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")

# c.subscribe(True, callback)


print('CAN initialized, dummy callback installed')

t = sensors.DHT(machine.Pin(4), 1, poll_intervall_in_ms=5000)


async def main():
    await asyncio.gather(can.sendping_task(), can.runcallback_task(), t.poll_task())


def r():
    asyncio.run(main())
