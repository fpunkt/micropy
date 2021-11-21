# Hardware CAN interface from ESP32

import machine
import board
import uasyncio as asyncio
import cancommon

_hw_interface = None

def read() -> cancommon.Message:
    """Read next message from the bus"""
    packet = _hw_interface.recv()
    return cancommon.Message(packet[0], packet[3])

def init(self, rx=33, tx=32, baudrate=125, mode=machine.CAN.NORMAL):
    global _hw_interface
    _hw_interface = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=8)
    cancommon.send_poweron()


def _send(cid, payload):
    """Send packet"""
    try:
        _hw_interface.send(payload, cid, timeout=1)
        return True

    except Exception as e: # pylint: disable=bare-except, broad-except
        if board.DEBUG:
            print("Cannot send CAN message: ", e)
        # somehow this seems to be needed to allow going on
        _hw_interface.clear_tx_queue()
        return False

def write(cid, payload):
    tryagain = 3
    while tryagain > 0:
        if _send(cid, payload):
            return
        tryagain -= 1


async def _poll_CAN():
    # CAN initialized ?
    while _hw_interface is None:
        await asyncio.sleep_ms(5000)

    while True:
        if  _hw_interface.any():
            # TODO: use pre-allocated buffer
            packet = _hw_interface.recv()
            cid = packet[0]
            payload = packet[3]
            cancommon.static_incomming_message.canid = cid
            cancommon.static_incomming_message.payload = payload
            cancommon.dispatch_incomming_message()
        else:
            # good time for GC?
            pass
        await asyncio.sleep_ms(board.CANPOLLTIME_MS)

board.BACKGROUND_RUNNERS.append(_poll_CAN())
