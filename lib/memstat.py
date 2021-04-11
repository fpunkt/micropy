"""
Check memory allocation
"""

# pylint: disable=import-error
# pylint: disable=no-member
# pylint: disable=missing-docstring

import gc
import board
import cancommon
import pwm
import utime

pp = pwm.PWM(2, 0x66)

def delay_between_loops():
    utime.sleep_ms(10)

def pwmmessage(count=100):
    """check GC usage for PWM messages"""
    for _ in range(count):
        m1 = gc.mem_free()
        pp.send_status_to_can()
        pp.send_status_to_can()
        pp.send_status_to_can()
        pp.send_status_to_can()
        m2 = gc.mem_free()
        delay_between_loops()
        print('Mem Used: {}'.format(m1-m2))

def pingmessage(count=100):
    """check GC usage for ping messages"""
    for _ in range(count):
        m1 = gc.mem_free()
        cancommon.send_ping(board.CAN)
        cancommon.send_ping(board.CAN)
        cancommon.send_ping(board.CAN)
        m2 = gc.mem_free()
        delay_between_loops()
        print('Mem Used: {}'.format(m1-m2))

def pwmset(count=100):
    for _ in range(count):
        m1 = gc.mem_free()
        pp.iset_no_can_message(0)
        pp.iset_no_can_message(100)
        pp.iset_no_can_message(0)
        pp.iset_no_can_message(100)
        m2 = gc.mem_free()
        delay_between_loops()
        print('Mem Used: {}'.format(m1-m2))
    pp.iset_no_can_message(0)
