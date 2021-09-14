"""
Rollladen WZ

Motor w/o load is going at about 0.5 Hz @ 12V

"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=unused-import, multiple-statements

# start CAN first, otherwise bus is in undefined state

# import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)
import net; net.start_wlan(); net.start_repl()

# import time; print('Loading main, giving time to abort ....'); time.sleep(2)

import can
import bconf
c = bconf.CAN(0x100)

import board

board.LOCATION = 'wz'
board.DEBUG = True

import machine
import sensors
import pwm
import schedule
import motor
import relais
import uasyncio as asyncio
import utime


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
    if pwm.handle_can_message(msg):
        print('Message handled by PWM')
        return
    if len(msg.payload) > 3 and msg.payload[0] == 0x11:
        count = 100*(msg.payload[1]<<8 + msg.payload[2])
        print("DOING SOME STUPID LOOPING", count)
        while count > 0:
            count -= 1
        print("DONE with stupid looping")
        return
    msg.unknown_command()


can.subscribe(can_callback)

print('CAN initialized, dummy callback installed')

ping = sensors.PingDevice(poll_intervall_in_ms=2500)
# t1 = sensors.DHT(1, machine.Pin(4), poll_intervall_in_ms=5000)

w = None

# def s(id=0x111):
#     can.CANDevice.send(id, [1, 2, 3])

def watchdog():
    # pylint: disable=global-statement
    global w
    w = sensors.WDT()

def r():
    schedule.run()

s = schedule.schedule_list
if 1 == 0:
    r()
else:
    print('# run r() to start event handler')
