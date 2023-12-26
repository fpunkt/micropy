"""Failsafe main file - init network and start app.main()"""

# Connect using   picocom --baud 115420 /dev/tty.usbserial-0001

import board

# Always start up with network on and basic debugging enabled.
# You can overwrite this by providing a main.py for your application
# or you can overwrite it by sending a CAN command after receiving a power on message
if True:
    import net
    net.DEBUG = True
    net.start_wlan(32)
    net.start_repl()
    board.DEBUG = 1

# Init Watchdog

import app
import board

def r():
    board.restart()

# check whether app has defined its own main function. If so: run main()
# Otherwise start the main eventloop which starts all registered services (e.g. sensors, PWM, etc.)
try:
    app.main()
except AttributeError:
    board.run()
