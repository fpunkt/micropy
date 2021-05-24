"""
Main Module.

Function main is executed after standard inits
"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=unused-import, multiple-statements, redefined-outer-name


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


import machine
import uasyncio as asyncio
import utime

# machine.CAN.callback(None)

CANDevice = None

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


class CAN:
    def __init__(self, id=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL):
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        # c = machine.CAN(0, mode=machine.CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.canid = canid
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=4)
        self.callback = None
        self.subscribed_to = 0
        self.pingtime = 2000
        self._startupmessage()
        # pylint: disable=global-statement
        global CANDevice
        CANDevice = self

    def subscribe(self, id, callback):
        self.subscribed_to = id
        self.callback = callback

    def any(self):
        return self.can.any()

    def recv(self):
        return self.can.recv()

    def send(self, canid, data):
        """Send data. Return None or an exception"""
        #print('CAN send0 {:03x} {}'.format(canid, _payloadstring(data)))
        ex = None
        i = 0
        while i < 3:
            try:
                # print('CAN send {:03x} {}'.format(canid, _payloadstring(data)))
                self.can.send(data, canid)
                return None
            except Exception as e: # pylint: disable=broad-except
                ex = e
                # print('ERROR CAN: cannot send #{}, e={}: {}'.format(i, type(e), e))
                utime.sleep_ms(1)
            i += 1
        # print('ERROR: CAN cannot send message #{:03x} {}'.format(id, _payloadstring(data)))
        return ex

    def ping(self):
        now = utime.time()
        self.send(CANID_PING, [
            self.canid >> 8, self.canid & 0xff,
            (now >> 24) & 0xff, (now >> 16) & 0xff, (now >> 8) & 0xff, (now >> 0) & 0xff])

    def _startupmessage(self):
        if id is not None:
            serial = machine.unique_id()
            self.can.send([self.canid >>8, self.canid & 0xff,
                    machine.reset_cause(), # startup reason
                    2, # HClib Version
                    12, # HW Type -- make this 12 for ESP32 ..
                    0xa0, # Application type and Version - make this the library version
                    serial[-2], serial[-1]], # CPU serial
                CANID_POWER_ON)




async def sendping_task():
    if CANDevice is None:
        return
    while True:
        CANDevice.ping()
        await asyncio.sleep_ms(CANDevice.pingtime)


async def runcallback_task():
    print('CALLBACK running')
    if CANDevice is None:
        return
    while True:
        try:
            packet = CANDevice.can.recv()
            id = packet[0]
            # print('Got {:03x} {}'.format(id, packet[3]))
            if CANDevice.subscribed_to is not True and id != CANDevice.subscribed_to:
                return
            payload = packet[3]
            m = Message(id, payload)
            if CANDevice.callback is None:
                print("got message but no callback", m)
            else:
                CANDevice.callback(m)
        except: # pylint: disable=bare-except
            print('Exception while reading CAN ....')
