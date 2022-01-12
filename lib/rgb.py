"""
RGB colors

RGB is using 3 PWM.
(Note: this is not a Neo pixel)

"""

import machine
import utime
import uasyncio as asyncio
import board
import can
import canid
import pwm
import pwmcode


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
        pwm.eod_callbacks.append(self.send_status_to_can_if_needed)

    def send_status_to_can_if_needed(self):
        if not self.can_message_pending:
            return
        self.send_status_to_can(self.r.ival<<2, self.g.ival<<2, self.b.ival<<2)
        self.can_message_pending = False


    def seti_no_can_message(self, r, g, b):
        self.r.seti_no_can_message(r)
        self.g.seti_no_can_message(g)
        self.b.seti_no_can_message(b)

    def seti12(self, r, g, b):
        """Set raw integer duty from 0 .. 1023 and send status to CAN"""
        self.seti_no_can_message(r>>2, g>>2, b>>2)
        self.can_message_pending = True
        #self.send_status_to_can(r, g, b)

    # def seti16(self, r, g, b):
    #     """Set integer 0..0xffff"""
    #     r, g, b = pwm.i16_to_raw(r), pwm.i16_to_raw(g), pwm.i16_to_raw(b)
    #     self.seti(r, g, b)

    def dimi12(self, r, g, b):
        """dim in raw units"""
        self.r.dimi(r>>2)
        self.g.dimi(g>>2)
        self.b.dimi(b>>2)
        self.can_message_pending = True
        #self.send_status_to_can(r, g, b) # send even the device is still working

    # def dimi16(self, r, g, b):
    #     r, g, b = pwm.i16_to_raw(r), pwm.i16_to_raw(g), pwm.i16_to_raw(b)
    #     self.dimi(r, g, b)

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

        # r, g, b = self.r.ival<<6, self.g.ival<<6, self.b.ival<<6
        # print("r = {}/{:04x}  -->  {}/{:04x}".format(self.r.ival, self.r.ival, r, r))
        payload = self.msg.payload
        payload[3] = r >> 4
        payload[4] = g >> 4
        payload[5] = b >> 4
        payload[6] = r & 0x0f
        payload[7] = ((g & 0xf) << 4) | (b & 0xf)
        self.msg.send()


def _setrgb(msg):
    rgb = board.SENSORSs.find(msg, RGB, 0xa1)
    print('got set RGB, rgb={}'.format(rgb))
    if not rgb:
        return
    print('setting r/g/b {}/{}/{}'.format(msg.u16(2), msg.u16(4), msg.u16(6)))
    rgb.dimi12(msg.u16(2), msg.u16(4), msg.u16(6))

can.register(pwmcode.RGB, 8, 8, lambda msg: _setrgb(msg))
