"""
RGB colors

RGB is using 3 PWM.
(Note: this is not a Neo pixel)

"""

import machine
from net import DEBUG
import utime
import asyncio
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
        self.off_no_telemetry(0, 0, 0) # poweroff
        board.PORTs.register(portid, self)
        # allocate message once to avoid garbage collection
        self.msg = can.Message(canid.PWM_RGB_VALUE, [0, 0, 0, 0, 0, 0, 0, 0])
        self.msg.setsender(self.id)
        # hash values, we can't rely on PWM since this is relies on dimming finished
        # self.rv = 0
        # self.bv = 0
        # self.gv = 0
        # self.can_message_pending = False
       #  pwm.eod_callbacks.append(self.send_telemetry())

    #def send_telemetry_if_needed(self):
    #    if not self.can_message_pending:
    #        return
    #    self._send_to_can()
    #    # just to make sure dimming didn't screw up
    #    print('fixing to {}, {}, {}'.format(self.r.current_raw_value(), self.g.current_raw_value(), self.b.current_raw_value()))
    #    self.set_raw_no_telemetry(self.r.current_raw_value(), self.g.current_raw_value(), self.b.current_raw_value())
    #    self.can_message_pending = False

    def off_no_telemetry(self):
        """turn device off"""
        self.r.off_no_telemetry()
        self.g.off_no_telemetry()
        self.b.off_no_telemetry()

    def setf_no_telemetry(self, r: float, g: float, b: float):
        self.r.setf_no_telemetry(r)
        self.g.setf_no_telemetry(g)
        self.b.setf_no_telemetry(b)

    def setf(self, r, g, b):
        """Set float duty from 0 .. 1 and send status to CAN"""
        if board.DEBUG:
            print('setf {}, {}, {}'.format(r, g, b))
        self.setf_no_telemetry(r, g, b)
        self.send_telemetry(r, g, b)
        #self._send_to_can()

    def dimf(self, r, g, b):
        """dim in raw units"""
        if board.DEBUG:
            print('dim10 {}, {}, {}'.format(r, g, b))
        self.r.dimf(r)
        self.g.dimf(g)
        self.b.dimf(b)
        self.send_telemetry(r, g, b)

    #def dimi16(self, r, g, b):
    #    """dim in 16-bit units"""
    #    #self.send_status_to_can(r, g, b) # send even the device is still working
    #    self.dimi10(_rshift(r), _rshift(g), _rshift(b))

    def _telemetry(self):
        self.send_telemetry(self.r.currentf_raw(), self.g.current_raw(), self.b.current_raw())

    def send_telemetry(self, r, g, b):
        # Message format is
        #  senderid/16
        #  portid/8
        #  r/8      high 8 bit, actually (r>>4)
        #  g/8
        #  b/8
        #  rgb-lower-4-bit/16    0x0rgb  where r, g, b are the lower 4 bits of r/g/b
        if self.id is None or not board.CAN:
            return

        # r, g, b = self.r.current_raw_value()<<6, self.g.current_raw_value()<<6, self.b.current_raw_value()<<6
        # print("r = {}/{:04x}  -->  {}/{:04x}".format(self.r.current_raw_value(), self.r.current_raw_value(), r, r))
        payload = self.msg.payload
        payload[3] = r >> 2
        payload[4] = g >> 2
        payload[5] = b >> 2
        payload[6] = r & 0x03
        payload[7] = ((g & 0x3) << 4) | (b & 0x3)
        self.msg.send()


def _dimrgb16(msg):
    rgb = board.PORTs.find(msg, RGB, 0xa1)
    if board.DEBUG:
        print('got set RGB, rgb={}'.format(rgb))
    if not rgb:
        return
    if board.DEBUG:
        print('setting r/g/b {}/{}/{}'.format(msg.u16(2), msg.u16(4), msg.u16(6)))
    rgb.dimi16(msg.u16(2), msg.u16(4), msg.u16(6))

def _dimrgb10(msg):
    rgb = board.PORTs.find(msg, RGB, 0xa1)
    if not rgb:
        return
    rgb.dimi10(msg.u16(2), msg.u16(4), msg.u16(6))

def _setrgb10(msg):
    rgb = board.PORTs.find(msg, RGB, 0xa1)
    if not rgb:
        return
    rgb.seti10(msg.u16(2), msg.u16(4), msg.u16(6))

can.register(pwmcode.DIM_RGB16, 8, 8, lambda msg: _dimrgb16(msg))
can.register(pwmcode.DIM_RGBNATIVE, 8, 8, lambda msg: _dimrgb10(msg))
can.register(pwmcode.SET_RGBNATIVE, 8, 8, lambda msg: _setrgb10(msg))
