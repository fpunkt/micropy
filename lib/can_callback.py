"""
CAN version using a callback that is called when a can packet is received
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import machine
import cancommon

class CAN:
    """Wrapper for machine.CAN, providing (some kind of) interrupt and callback"""
    def __init__(self, canid=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL):
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        # c = machine.CAN(0, mode=machine.CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=4)
        self._callback = None
        self._subscribed_to = None
        self._cbrunner = self._run_callback
        self.canid = canid
        cancommon.register(self)

    def subscribe(self, canid, callback):
        self._subscribed_to = canid
        self._callback = callback
        self.can.callback(self._cbrunner)

    def _run_callback(self, candev):
        # print('this is __callback', self, candev)
        if not self.can.any():
            print("ERROR: CAN callback triggered from IRQ but no packet available")
            return
        packet = self.can.recv()
        canid = packet[0]
        if self._subscribed_to is True or self._subscribed_to == canid:
            self._callback(cancommon.Message(canid, packet[3]))

    def any(self):
        return self.can.any()

    def read(self):
        """Read next message from the bus"""
        return cancommon.read(self)

    def write(self, msg):
        """Write message to bus"""
        self.can.send(msg.payload, msg.canid)

    def send(self, canid, payload):
        """Send packet"""
        self.can.send(payload, canid)
