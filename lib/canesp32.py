# Hardware CAN interface from ESP32

import machine
import board
import uasyncio as asyncio
import utime
import cancommon

_hw_interface = None

def read() -> cancommon.Message:
    """Read next message from the bus"""
    packet = _hw_interface.recv()
    return cancommon.Message(packet[0], packet[3])

def reset():
    """Reset CAN bus"""
    if _hw_interface is None:
        return
    _hw_interface.clearfilter()
    if _currentfilter is not None:
        setsimplefilter(_currentfilter)

def init(self, rx=33, tx=32, baudrate=125, mode=machine.CAN.NORMAL):
    # machine.CAN(0, mode=machine.CAN.NORMAL, baudrate=125, rx_io=33, tx_io=32, rx_queue=10, tx_queue=8)
    global _hw_interface
    _hw_interface = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=8)

def _send_without_reset(cid, payload):
    """Send packet"""
    tryagain = 3
    while tryagain > 0:
        try:
            _hw_interface.send(payload, cid, timeout=1)
            board.WD.trigger()
            board.CAN_MESSAGES_SEND += 1
            return True
        except Exception as e: # pylint: disable=bare-except, broad-except
            if board.DEBUG:
                print("Cannot send CAN message, going to reset: ", e)
            # Bus is running at 125 kHz - typical CAN packet (8 bytes payload plus offset) takes less than 1ms
            # 1 ms sleep should be sufficient to send messages. If this fails several times there seems to be an
            # issue with the CAN system
            utime.sleep_ms(1)
            tryagain -= 1

def _send_with_reset_bus_if_needed(cid, payload):
    if _send_without_reset(cid, payload):
        return True
    # try this as a last resort
    _hw_interface.restart()
    # _hw_interface.clear_tx_queue()
    return _send_without_reset(cid, payload)


def write(cid, payload):
    if _send_without_reset(cid, payload):
        return
    # what now? Reset the system?

_currentfilter = None

def setsimplefilter(id):
    """Only pass given ID pass the CAN controller. Removes CPU load if the bus
    is heavy loaded, strongly decreases the risk of dropping packages"""
    # not fully understood how filters work. This works at least somehow ...
    global _currentfilter
    if _hw_interface is None:
        return
    bank = 0
    mode = 0
    value = id << (32-11)
    mask = 0x1fffff
    _hw_interface.setfilter(bank, mode, (value, mask))
    _currentfilter = id

def reset():
    _hw_interface.setfilter(0, 0, 0, 0xfffffff)


_static_message = [0, 0, 0, memoryview(bytearray(8))]
# simply using bytearray does not work, you need a memoryview
#

async def _poll_CAN():
    # CAN initialized ?
    while _hw_interface is None:
        await asyncio.sleep_ms(1000)

    mcount = 0

    while True:
        if  mcount < 5 and _hw_interface.any():
            board.CAN_MESSAGES_RECEIVED += 1
#            print('juhu, got message')

            if False:
                # alloc fresh packets for each call
                packet = _hw_interface.recv()
                cancommon.static_incomming_message.canid = packet[0]
                cancommon.static_incomming_message.payload = packet[3]
            else:
                # use pre-allocated buffer
                _hw_interface.recv(_static_message)
                # print(_static_message, bytes(_static_message[3]))
                cancommon.static_incomming_message.canid = _static_message[0]
                cancommon.static_incomming_message.payload = bytes(_static_message[3])

            cancommon.dispatch_incomming_message()

            # eat more pending messages - ensure that we do not miss one
            # should not result in blocking other tasks because a message
            # takes about 1ms and we are most likely faster in processing
            # the messages. But ensure that we yield anyway from time to time.
            mcount += 1
            continue
        else:
            # no message or messages comming too fast
            if mcount < 3:
                # good time for GC? Bus does not seem too busy
                board.good_time_for_gc()
            mcount = 0
        await asyncio.sleep_ms(board.CANPOLLTIME_MS)

board.BACKGROUND_RUNNERS.append(_poll_CAN())

# Since we can set a CAN input filter it is not obvious that we receive messages on a regular basis.
# Can't use for Watchdog

# async def _monitor_can_bus_activity():
#     global _messages_seen_since_last_check
#     while True:
#         await asyncio.sleep(20)
#         if board.DEBUG:
#             print('# Checking for CAN activity: ')
#         if _hw_interface is None:
#             continue
#         if _messages_seen_since_last_check > 0:
#             _messages_seen_since_last_check = 0
#             continue
#         restart CAN bus here
