"""
CAN bus interface
"""

# pylint: disable=import-error, missing-docstring

import time
import machine
import micropython

# default connects to tx=4, rx=2; BAD, because 2 == LED

# The CAN module does currently not support interrupts on receive.
# We can however attach an IRQ handler to the RX line.
# One an interrupt is triggered we remove the handler and re-activate it like 10ms later

class Message:
    """A CAN message"""
    # pylint: disable=too-few-public-methods
    def __init__(self, lst):
        self.id = lst(0)
        self.payload = lst(3)

class CAN:
    def __init__(self, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL):
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx)
        self.rx = rx
        self.prx = machine.Pin(rx)
        #p0.irq(trigger=Pin.IRQ_FALLING, handler=callback)
        self._callback = None

    def callback(self, func):
        self._callback = func
        self._enable_irq()

    def any(self):
        return self.can.any()

    def recv(self):
        return self.can.recv()

    def send(self, canid, data):
        """Send data"""
        self.can.send(data, canid)

    def _dispatch_input(self, _):
        """Called when IRQ has detected new data. This function is running outside IRQ context"""
        #print("Hier ist dispatch")
        if self._callback is None:
            return
        for _ in range(5):
            if self.can.any():
                # found data
                while self.can.any():
                    # make sure we catch all interrupts so we can re-enable the IRQ
                    try:
                        self._callback(self.can.recv())
                    except: # pylint: disable=bare-except
                        pass
                self._enable_irq()
                # could that happen? Racing condition when we just missed the last bit?
                if self.can.any():
                    try:
                        self._callback(self.can.recv())
                    except: # pylint: disable=bare-except
                        pass
                return
            time.sleep_ms(1)
        self._enable_irq() # trust nobody


    def _enable_irq(self):
        if self._callback is None:
            return
        self.prx.irq(trigger=machine.Pin.IRQ_FALLING, handler=self._irq_handler)

    def _irq_handler(self, _):
        """_irq_handler is the actual interrupt handler. Work is defered
        to _dispatch_input which is running outside IRQ context"""
        # disable IRQ for this PIN
        self.prx.irq(trigger=0)

        try:
            micropython.schedule(self._dispatch_input, 1)
        except: # pylint: disable=bare-except
            # OK to ignore errors here, _dispatch input will process all items in the queue
            pass


def cb(msg):
    print("Got CAN message: ", msg)
