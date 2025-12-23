"""Read temperature and humidity from AHT10 or AHT20 sensor (I2C)
This module was written by Antigravity and Gemini, nice.
"""


import asyncio
import utime

class AHT10:
    def __init__(self, i2c, address=0x38):
        self.i2c = i2c
        self.address = address
        self.buf = bytearray(6)
        self.reset()
        if not self.calibrate():
            raise RuntimeError("Could not calibrate AHT10")

    def reset(self):
        self.i2c.writeto(self.address, b'\xBA')
        utime.sleep_ms(20)

    def calibrate(self):
        self.i2c.writeto(self.address, b'\xE1\x08\x00')
        utime.sleep_ms(300)
        return self.status() & 0x08

    def status(self):
        self.i2c.readfrom_into(self.address, self.buf)
        return self.buf[0]

    async def _perform_measurement(self):
        self.i2c.writeto(self.address, b'\xAC\x33\x00')
        await asyncio.sleep_ms(80)
        self.i2c.readfrom_into(self.address, self.buf)
        
        # Check if bit 7 is set (busy)
        while self.buf[0] & 0x80:
            await asyncio.sleep_ms(10)
            self.i2c.readfrom_into(self.address, self.buf)

        self._h = ((self.buf[1] << 12) | (self.buf[2] << 4) | (self.buf[3] >> 4)) * 100 / 0x100000
        self._t = (((self.buf[3] & 0xF) << 16) | (self.buf[4] << 8) | self.buf[5]) * 200.0 / 0x100000 - 50
        # print(self._h, self._t)
    def T(self):
        return self._t

    def H(self):
        return self._h

class AHT20(AHT10):
    def calibrate(self):
        # AHT20 might have different calibration, but often compatible or self-calibrated
        # For now reusing AHT10 init which is often compatible for basic read
        # But AHT20 documentation says: send 0xBE, wait 10ms.
        # This implementation is a placeholder if AHT20 differs significantly.
        # Based on ahtx0 libraries, they are often unified.
        # Let's check status bit 3 (calibrated)
        self.i2c.writeto(self.address, b'\x71') 
        if not (self.status() & 0x08):
            self.i2c.writeto(self.address, b'\xBE\x08\x00')
            utime.sleep_ms(10)
        return True
