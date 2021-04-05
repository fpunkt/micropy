"""
CAN bus interface
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

import utime
import machine
import micropython
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


# CAN command to start up WEBREPL
START_WEBREPL = const(0xfe)
SOFT_RESET = const(0xfd)
HARD_RESET = const(0xfc)


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
    def __init__(self, id=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL):
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx)
        self.rx = rx
        self.prx = machine.Pin(rx)
        #p0.irq(trigger=Pin.IRQ_FALLING, handler=callback)
        self._callback = None
        self._subscribed_to = 0
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
        self._enable_irq() # handle configuration commands
        # pylint: disable=global-statement
        global CANDevice
        CANDevice = self

    def subscribe(self, id, callback):
        self._subscribed_to = id
        self._callback = callback
        self._enable_irq()

    def any(self):
        return self.can.any()

    def recv(self):
        return self.can.recv()

    def send(self, canid, data):
        """Send data"""
        for _ in range(5):
            try:
                self.can.send(data, canid)
                return
            except: # pylint: disable=bare-except
                # print('ERROR CAN: cannot send #', i)
                utime.sleep_ms(1)
        print('ERROR: CAN cannot send message #{:03x} {}'.format(id, _payloadstring(data)))

    def _dispatch_input(self, _):
        """Called when IRQ has detected new data. This function is running outside IRQ context"""
        #print("Hier ist dispatch")
        for _ in range(5):
            if self.can.any():
                # found data
                while self.can.any():
                    # catch errors to sure we catch all interrupts so we can re-enable the IRQ
                    try:
                        packet = self.can.recv()
                        id = packet[0]
                        if id != self._subscribed_to:
                            continue
                        payload = packet[3]
                        if self._handle_config_command(payload):
                            continue
                        self._callback(Message(id, payload))
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
            utime.sleep_ms(1)
        self._enable_irq() # trust nobody
        machine.idle()

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

    def _handle_config_command(self, payload):
        if len(payload) == 1 and payload[0] == START_WEBREPL:
            ip = net.connect_to_wlan()
            print('GOT IP: ', ip)
            net.start_repl()
            ipx = ip[0].split('.')
            print('GOT IPx: ', ipx)
            self.send(CANID_WEBREPL_STARTED, [self.id >>8, self.id & 0xff, ipx[0], ipx[1], ipx[2], ipx[3]])
            return True
        if len(payload) == 3:
            if payload[1] != 0xaf or payload[2] != 0xfe:
                return False
            if payload[0] == SOFT_RESET:
                machine.soft_reset()
            if payload[0] == HARD_RESET:
                machine.reset()
        return False
