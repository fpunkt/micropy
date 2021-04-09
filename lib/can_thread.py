"""
CAN bus interface

See https://github.com/nos86/micropython/blob/esp32-can-driver/examples/esp32_can.py
for driver details.
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import _thread
import utime
import machine
import net

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


# default connects to tx=4, rx=2; BAD, because 2 == LED

# The CAN module does currently not support interrupts on receive.
# We can however attach an IRQ handler to the RX line.
# One an interrupt is triggered we remove the handler and re-activate it like 10ms later

def _payloadstring(payload):
    return ' '.join('{:02x}'.format(x) for x in payload)

class Message:
    """A CAN message"""
    # pylint: disable=too-few-public-methods
    def __init__(self, id, payload):
        self.id = id
        self.payload = payload

    def payloadstring(self):
        return _payloadstring(self.payload)

    def __repr__(self):
        return '<Message #{:03x} [{}] {}>'.format(self.id, len(self.payload), self.payloadstring())

CANDevice = None

class CAN:
    """Wrapper for machine.CAN, providing (some kind of) interrupt and callback"""
    # pylint: disable=too-many-instance-attributes
    def __init__(self, id=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL):
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=4)
        self._callback = None
        self._subscribed_to = 0
        self._reading_thread = None
        self.id = id
        if id is not None:
            serial = machine.unique_id()
            self.can.send([self.id >>8, self.id & 0xff,
                    machine.reset_cause(), # startup reason
                    2, # HClib Version
                    12, # HW Type -- make this 12 for ESP32 ..
                    0xa0, # Application type and Version - make this the library version
                    serial[-2], serial[-1]], # CPU serial
                CANID_POWER_ON)
        # pylint: disable=global-statement
        global CANDevice
        CANDevice = self

    def subscribe(self, id, callback):
        self._subscribed_to = id
        self._callback = callback
        self._reading_thread = _thread.start_new_thread(self._read_and_process_all, ())

    def any(self):
        return self.can.any()

    def recv(self, timeout=1000):
        return self.can.recv(timeout=timeout/10)

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

    def _read_and_process_single(self):
        try:
            packet = self.can.recv()
            id = packet[0]
            # print('Got {:03x} {}'.format(id, packet[3]))
            if self._subscribed_to is not True and id != self._subscribed_to:
                return
            payload = packet[3]
            if self._handle_config_command(payload):
                return
            self._callback(Message(id, payload))
        except: # pylint: disable=bare-except
            # print('CAN: cannot read ...')
            pass

    def _read_and_process_all(self):
        while True:
            self._read_and_process_single()

    def _handle_config_command(self, payload):
        if payload == bytearray([START_WEBREPL]):
            ip = net.connect_to_wlan()
            net.start_repl()
            ipx = ip[0].split('.')
            self.send(CANID_WEBREPL_STARTED, [self.id >>8, self.id & 0xff, ipx[0], ipx[1], ipx[2], ipx[3]])
            return True

        if payload == bytearray([START_WEBREPL_HOTSPOT]):
            ip = net.start_hotspot()
            net.start_repl()
            self.send(CANID_WEBREPL_STARTED, [self.id >>8, self.id & 0xff, ip[0], ip[1], ip[2], ip[3]])
            return True

        if payload == bytearray([SEND_PING]):
            sendping()
            return True

        if payload == bytearray([SOFT_RESET, 0xaf, 0xfe]):
            machine.soft_reset()

        if payload == bytearray([HARD_RESET, 0xaf, 0xfe]):
            machine.reset()

        return False

def sendping():
    now = utime.time()
    CANDevice.send(CANID_PING, [
        CANDevice.id >> 8, CANDevice.id & 0xff,
        (now >> 24) & 0xff, (now >> 16) & 0xff, (now >> 8) & 0xff, (now >> 0) & 0xff])
