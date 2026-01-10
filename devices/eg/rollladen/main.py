"""
Rollladen WZ

Motor w/o load is going at about 0.5 Hz @ 12V

"""
# pylint: disable=import-error, wrong-import-order
# pylint: disable=missing-docstring
# pylint: disable=unused-import, multiple-statements

import board
board.LOCATION = 'wz'
board.DEBUG = True
board.CANID = 0x100


if board.DEBUG is True:
    import net
    net.start_wlan()
    net.start_repl()

import machine
import sensors
import pwm
import motor
import relais
import asyncio
import utime
import bconf
import can
import irqio

power = relais.Relais(None, bconf.ML10_PWM_8)

m1 = motor.Motor(10, bconf.ML10_PWM_3, bconf.ML10_PWM_4, bconf.AUX3_YELLOW)
# m2 = motor.Motor(12, bconf.ML10_PWM_1, bconf.ML10_PWM_2)

m = m1


message_counter = 0

def can_callback(msg):
    # pylint: disable=global-statement
    global message_counter
    message_counter += 1
    print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")
        return
    if len(msg.payload) >= 1:
        command = msg.payload[0]

    if len(msg.payload) == 1:
        if command == 0:
            power.off()
            return
        if command == 1:
            power.on()
            return
        if command == 2:
            m1.fullstop()
            return
        if command == 3:
            m1.speed(19999)
            return

    if len(msg.payload) == 2:
        if command == 4:
            m1.speed(10 * msg.payload[1])
        return

    msg.unknown_command()


can.subscribe(can_callback)


async def phall():
    c = m1.sensorcount
    mssleep = 1000
    loopcounter = 0
    while True:
        loopcounter += 1
        print('Hall {:6d} {:5d} {:4d} /s'.format(
            loopcounter,
            m1.sensorcount, (m1.sensorcount - c) *1000 // mssleep))
        c = m1.sensorcount
        await asyncio.sleep_ms(mssleep)

board.BACKGROUND_RUNNERS.append(phall())

def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
