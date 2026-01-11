"""Failsafe main file - init network and start app.main()"""

# Connect using   picocom --baud 115420 /dev/tty.usbserial-0001

import board
import machine
import asyncio

def run():
    """Run the main event loop forever"""
    asyncio.get_event_loop().run_forever()

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
# For conveniece debugging: Set net and mqtt as global variables
NET = board.NET
MQTT = board.MQTT

def restart():
    """Restart the board"""
    machine.reset()

# check whether app has defined its own main function. If so: run main()
# Otherwise start the main eventloop which starts all registered services (e.g. sensors, PWM, etc.)
try:
    board.PRINTF('run app.main()')
    app.main()
except AttributeError:
    board.PRINTF('run board.run()')
    board.run()
except Exception as e:
    board.PRINTF('Exception in main loop: {}', e)
    board.PRINTF('Try to connect to WLAN')
    board.NET.start_wlan()
    
 