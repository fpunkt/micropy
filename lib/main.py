"""Failsafe main file - init network and start app.main()"""

# Connect using   picocom --baud 115420 /dev/tty.usbserial-0001

import board

# Always start up with network on and basic debugging enabled.
# You can overwrite this by providing a main.py for your application
# or you can overwrite it by sending a CAN command after receiving a power on message
if False:
    try:
        import net
        net.start_wlan(32, timeout=5)
        net.start_repl()
        board.DEBUG = 1
    except Exception as e:
        print('Failed to start network: {}'.format(e))
        board.DEBUG = 0

# Init Watchdog

import app
import board

# Set network status LED if net module has been loaded, send network status to CAN
try:
    import sys
    sys.modules['net'].set_status_led()
    sys.modules['cancommon'].send_wlan_connected()
except:
    pass

def r():
    board.restart()

# check whether app has defined its own main function. If so: run main()
# Otherwise start the main eventloop which starts all registered services (e.g. sensors, PWM, etc.)
try:
    app.main()
except AttributeError:
    board.run()
 