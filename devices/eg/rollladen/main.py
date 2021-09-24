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
import uasyncio as asyncio
import utime
import bconf
import can
import irqio

power = relais.Relais(None, bconf.ML10_PWM_8)

m1 = motor.Motor(10, bconf.ML10_PWM_3, bconf.ML10_PWM_4)
m2 = motor.Motor(12, bconf.ML10_PWM_1, bconf.ML10_PWM_2)

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
            m1.speed(0)
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

class Hall(irqio.IRQIO):
    def __init__(self, sensorid, pinid):
        super().__init__(sensorid, pinid, trigger=None, pullup=True)
        self.count = 0
        self.lasttrigger = 0

    def run(self):
        changed = super().run()
        if changed:
            now = utime.ticks_ms()
            self.count += 1
            if 1 == 2:
                print('HALL #{} changed {:4d}  {:5d} ms'.format(
                    self.sensorid, self.count, utime.ticks_diff(now, self.lasttrigger)))
            self.lasttrigger = now


hall1 = Hall(30, bconf.AUX3_WHITE)
hall2 = Hall(31, bconf.AUX3_YELLOW)

async def phall():
    c1, c2 = hall1.count, hall2.count
    mssleep = 1000
    while True:
        print('Hall {:5d} {:5.3f} /s      {:5d} {:5.3f} /s'.format(
            hall1.count, (hall1.count - c1) *1000 / mssleep,
            hall2.count, (hall2.count - c2) *1000 / mssleep))
        c1, c2 = hall1.count, hall2.count
        await asyncio.sleep_ms(mssleep)

board.BACKGROUND_RUNNERS.append(phall())

def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
