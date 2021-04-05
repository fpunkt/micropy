"""
Test LED PWM
"""

# pylint: disable=import-error, missing-docstring

import math
import time
import machine


class FPWM:
    """Wrapper for PMW class. Use float values from 0..1 and provide dimming"""
    def __init__(self, pin):
#        self.pwm = machine.PWM(machine.Pin(pin, machine.Pin.OUT))
        self.pwm = machine.PWM(machine.Pin(pin))

    def set(self, value):
        self.pwm.duty(int(value * 1023))

    def value(self):
        return self.pwm.duty()/1023.0


def pulse(pwm, t):
    for i in range(20):
        pwm.set(int(math.sin(i / 10 * math.pi) * 500 + 500))
        time.sleep_ms(t)

def main():
    print("Welcome to RT-Thread MicroPython!")

    # default is 10 bit PWM
    #led.set(0.5)

    # print(led.value)
    for i in range(10):
        pulse(l, 10)
    l.set(0.1)

if __name__ == '__main__':
    #p = machine.Pin(2)
    l = FPWM(2)
    main()
