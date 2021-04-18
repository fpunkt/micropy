"""
CAN bus interface

See https://github.com/nos86/micropython/blob/esp32-can-driver/examples/esp32_can.py
for driver details.
"""
import cancommon
import machine


class CAN:
    """Wrapper for machine.CAN, providing (some kind of) interrupt and callback"""
    # pylint: disable=too-many-instance-attributes
    def __init__(self, canid=None, rx=13, tx=12, baudrate=125, mode=machine.CAN.NORMAL):
        # bus = CAN(0, mode=CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        # c = machine.CAN(0, mode=machine.CAN.NORMAL, baudrate=125, rx_io=13, tx_io=12)
        self.can = machine.CAN(0, mode=mode, baudrate=baudrate, rx_io=rx, tx_io=tx, rx_queue=10, tx_queue=4)
        # prevend allocation in IRQ
        self._outside_irq_handler_ref = self._outside_irq_handler
        self._irq_handler_ref = self._irq_handler
        self.rx = rx
        self.prx = machine.Pin(rx)
        self._callback = None
        self._subscribed_to = 0
        self._out_of_irq_processing_scheduled = False
        self.timer = None
        self.canid = canid
        if canid is not None:
            serial = machine.unique_id()
            self.can.send([self.canid >>8, self.canid & 0xff,
                    machine.reset_cause(), # startup reason
                    2, # HClib Version
                    12, # HW Type -- make this 12 for ESP32 ..
                    0xa0, # Application type and Version - make this the library version
                    serial[-2], serial[-1]], # CPU serial
                CANID_POWER_ON)
        self._poll_period_ms = 5
        if self._poll_period_ms > 0:
            self.timer = machine.Timer(2)
        self._enable_irq()
        cancommon.CANDevice = self

    def subscribe(self, id, callback):
        self._subscribed_to = id
        self._callback = callback
        self._outside_irq_handler(None)

    def any(self):
        return self.can.any()

    def recv(self):
        return self.can.recv()

    def send(self, canid, data):
        """Send data. Return None or an exception"""
        #print('CAN send0 {:03x} {}'.format(canid, _payloadstring(data)))
        self._disable_irq() # we see the rx line trigger while sending
        self._enable_irq_soon()
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
            pass

    def _read_and_process_all(self):
        while self.can.any():
            self._read_and_process_single()

    def _outside_irq_handler(self, triggered_by_pin):
        """Called after IRQ has detected new data. This function is running outside IRQ context"""
        # print('Triggered by pin:', triggered_by_pin, self.can.any())
        if triggered_by_pin:
            # interrupt is raised with first bit of a CAN package
            # wait for packet to be finished. This also happens during power-up
            i = 0
            while not self.can.any() and i < 3:
                # print('waiting ...')
                utime.sleep_ms(1)
                i += 1

        self._read_and_process_all()
        self._enable_irq()
        self._out_of_irq_processing_scheduled = False
        # check for pending messages that came while IRQ was disabled
        # self._read_and_process_all()
        self._read_and_process_all()
        machine.idle()

    def _disable_irq(self):
        self.prx.irq(trigger=0)

    def _enable_irq(self):
        #print('enable IRQ')
        self.prx.irq(trigger=machine.Pin.IRQ_FALLING, handler=self._irq_handler)
        # print('ENABLE IRQ')
        # self.prx.irq(trigger=machine.Pin.IRQ_RISING, handler=self._irq_handler)

    def _enable_irq_soon(self):
        if self._poll_period_ms > 0:
            self.timer.init(period=self._poll_period_ms,
                mode=machine.Timer.ONE_SHOT,
                callback=self._irq_handler_ref)
            return
        self._enable_irq()

    def _irq_handler(self, irq_source):
        """_irq_handler is the actual interrupt handler. Work is defered
        to outside IRQ context"""
        # disable IRQ for this PIN, dosn't seem to work 100% though
        self.prx.irq(trigger=0)
        if self._out_of_irq_processing_scheduled:
            # print('OOIQR already scheduled', irq_source)
            return

        # schedule out-of-irq processing
        try:
            micropython.schedule(self._outside_irq_handler_ref, irq_source == self.prx)
            self._out_of_irq_processing_scheduled = True
        # except Exception as e: # pylint: disable=bare-except, broad-except
        except:
            # print('AUTSCH', e)
            #utime.sleep_ms(1000)
            # try again later
            self._enable_irq_soon()
