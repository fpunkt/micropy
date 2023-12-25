"""
RGB colors

RGB is using 3 PWM.
(Note: this is not a Neo pixel)

"""

import machine
from net import DEBUG
import utime
import uasyncio as asyncio
import board
import can
import canid
import pwm
import pwmcode

# make sure we don't use 0 for low numbers != 0
def _rshift(v):
    if v == 0:
        return 0
    if v < 64:
        return 1
    return v >> 6

# return reasonable 12 bit value for given 10 bit value
# def _lshift(v):
#     if v == 0:
#         return 0
#     if v < 4:
#         return 1
#     return v << 2

class RGB:
    """Bundle 3 PWM"""
    def __init__(self, portid, rpin, gpin, bpin) -> None:
        self.id = portid
        self.r, self.g, self.b = pwm.PWM(None, rpin), pwm.PWM(None, gpin), pwm.PWM(None, bpin)
        self.seti_no_can_message(0, 0, 0) # poweroff
        board.SENSORSs.register(portid, self)
        # allocate message once to avoid garbage collection
        self.msg = can.Message(canid.PWM_RGB_VALUE, [0, 0, 0, 0, 0, 0, 0, 0])
        self.msg.setsender(self.id)
        # hash values, we can't rely on PWM since this is relies on dimming finished
        # self.rv = 0
        # self.bv = 0
        # self.gv = 0
        self.can_message_pending = False
       #  pwm.eod_callbacks.append(self.send_status_to_can_if_needed)

    def send_status_to_can_if_needed(self):
        if not self.can_message_pending:
            return
        self._send_to_can()
        # just to make sure dimming didn't screw up
        print('fixing to {}, {}, {}'.format(self.r.current_value(), self.g.current_value(), self.b.current_value()))
        self.seti_no_can_message(self.r.current_value(), self.g.current_value(), self.b.current_value())
        self.can_message_pending = False

    def seti_no_can_message(self, r, g, b):
        self.r.seti_no_can_message(r)
        self.g.seti_no_can_message(g)
        self.b.seti_no_can_message(b)

    def seti10(self, r, g, b):
        """Set raw integer duty from 0 .. 1023 and send status to CAN"""
        if board.DEBUG:
            print('seti10 {}, {}, {}'.format(r, g, b))
        self.seti_no_can_message(r, g, b)
        self.send_status_to_can(r, g, b)
        #self._send_to_can()

    # def seti16(self, r, g, b):
    #     """Set raw integer duty from 0 .. 0xffff and send status to CAN"""
    #     self.seti10(_rshift(r), _rshift(g), _rshift(b))

    def dimi10xxx(self, r, g, b):
        """dim in raw units"""
        if board.DEBUG:
            print('dim10 {}, {}, {}'.format(r, g, b))
        if self.r.dimi(r) or self.g.dimi(g) or self.b.dimi(b):
            if board.DEBUG:
                print('schedule CAN message')
            self.can_message_pending = True
        else:
            self._send_to_can()

    def dimi10(self, r, g, b):
        """dim in raw units"""
        if board.DEBUG:
            print('dim10 {}, {}, {}'.format(r, g, b))
        self.r.dimi(r)
        self.g.dimi(g)
        self.b.dimi(b)
        self.send_status_to_can(r, g, b)

    def dimi16(self, r, g, b):
        """dim in 16-bit units"""
        #self.send_status_to_can(r, g, b) # send even the device is still working
        self.dimi10(_rshift(r), _rshift(g), _rshift(b))

    def _send_to_can(self):
        self.send_status_to_can(self.r.current_value(), self.g.current_value(), self.b.current_value())

    def send_status_to_can(self, r, g, b):
        # Message format is
        #  senderid/16
        #  portid/8
        #  r/8      high 8 bit, actually (r>>4)
        #  g/8
        #  b/8
        #  rgb-lower-4-bit/16    0x0rgb  where r, g, b are the lower 4 bits of r/g/b
        if self.id is None or not board.CAN:
            return

        # r, g, b = self.r.current_value()<<6, self.g.current_value()<<6, self.b.current_value()<<6
        # print("r = {}/{:04x}  -->  {}/{:04x}".format(self.r.current_value(), self.r.current_value(), r, r))
        payload = self.msg.payload
        payload[3] = r >> 2
        payload[4] = g >> 2
        payload[5] = b >> 2
        payload[6] = r & 0x03
        payload[7] = ((g & 0x3) << 4) | (b & 0x3)
        self.msg.send()


def _dimrgb16(msg):
    rgb = board.SENSORSs.find(msg, RGB, 0xa1)
    if board.DEBUG:
        print('got set RGB, rgb={}'.format(rgb))
    if not rgb:
        return
    if board.DEBUG:
        print('setting r/g/b {}/{}/{}'.format(msg.u16(2), msg.u16(4), msg.u16(6)))
    rgb.dimi16(msg.u16(2), msg.u16(4), msg.u16(6))

def _dimrgb10(msg):
    rgb = board.SENSORSs.find(msg, RGB, 0xa1)
    if not rgb:
        return
    rgb.dimi10(msg.u16(2), msg.u16(4), msg.u16(6))

def _setrgb10(msg):
    rgb = board.SENSORSs.find(msg, RGB, 0xa1)
    if not rgb:
        return
    rgb.seti10(msg.u16(2), msg.u16(4), msg.u16(6))

can.register(pwmcode.DIM_RGB16, 8, 8, lambda msg: _dimrgb16(msg))
can.register(pwmcode.DIM_RGBNATIVE, 8, 8, lambda msg: _dimrgb10(msg))
can.register(pwmcode.SET_RGBNATIVE, 8, 8, lambda msg: _setrgb10(msg))
