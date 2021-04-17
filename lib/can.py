"""
CAN version using a callback that is called when a can packet is received
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import machine
import cancommon

class CAN:
    """Wrapper for machine.CAN, providing (some kind of) interrupt and callback"""
    def __init__(self, canid=None, rx=33, tx=32, baudrate=125, mode=machine.CAN.NORMAL):
        # self, canid=None, rx=35, tx=34, baudrate=125, mode=machine.CAN.NORMAL
        # self, canid=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        # c = machine.CAN(0, mode=machine.CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=8)
        self._callback = None
        self._subscribed_to = None
        self._cbrunner = self._run_callback
        self.canid = canid
        cancommon.register(self)
        # subscribe to standard commands so we can still switch on/off WLAN in case booting fails for whatever reason
        self.can.callback(self._cbrunner)

    def subscribe(self, canid, callback):
        self._subscribed_to = canid
        self._callback = callback
        if callback is None:
            self.can.callback(None)
        else:
            self.can.callback(self._cbrunner)

    def _run_callback(self, candev):
        # print('this is __callback', self, candev)
        if not self.can.any():
            print("ERROR: CAN callback triggered from IRQ but no packet available")
            return
        packet = self.can.recv()
        canid = packet[0]
        payload = packet[3]
        if cancommon.handle_standard_config_command(self, payload):
            return
        if self._subscribed_to is True or self._subscribed_to == canid:
            self._callback(cancommon.Message(canid, payload))

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
