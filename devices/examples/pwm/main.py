"""
Sample PWM

"""

# pylint: disable=multiple-statements
#import time; print('Loading main, giving time to abort ....'); time.sleep(2)

# import time; print('Loading boot, giving time to abort (initializing network) ....'); time.sleep(2)
import net; net.start_wlan(); net.start_repl()

# pylint: disable=import-error, missing-docstring, redefined-builtin, multiple-statements, no-member
# pylint: disable=wrong-import-order
# pylint: disable=unused-import

import can

# Two pins on the left side of the board
can.CAN(0x100, rx=35, tx=32)

import board
import pwm
import sensors
import button
<<<<<<< HEAD
import schedule
=======
>>>>>>> master

board.DEBUG = True

# PMWs on the right side of the board
p0 = pwm.PWM(0, 15)
# PIN 2 is the on-PCB LED
p1 = pwm.PWM(1, 4)
p2 = pwm.PWM(2, 16)
p3 = pwm.PWM(3, 17)
p4 = pwm.PWM(4, 5)
p5 = pwm.PWM(5, 18)
p6 = pwm.PWM(6, 19)
p7 = pwm.PWM(7, 21)
# PIN3 is used for the USB UART
# PIN1 is used for the USB UART

# Adding a 9th PWM raises ValueError: out of PWM channels
# p8 = pwm.PWM(8, 22)

def can_callback(msg):
    """Note: callback is only processed when the evenloop is started"""
    # print("GOT CAN message #{:4d}: {}".format(message_counter, msg))
    if pwm.handle(msg):
        # print('Message handled by PWM')
        return
    msg.unknown_command()


can.subscribe(can_callback)

# Uncomment line below to enable the watchdog
# wd = sensors.WDT()
<<<<<<< HEAD

def r():
    schedule.run()

s = schedule.schedule_list
# r()
=======
def r():
    board.run()

if 1 == 1: # pylint: disable=comparison-with-itself
    r()
else:
    print('# run r() to start event handler')
>>>>>>> master
