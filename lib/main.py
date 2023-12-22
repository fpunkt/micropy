"""Failsafe main file - init network and start app.main()"""

# Connect using   picocom --baud 115420 /dev/tty.usbserial-0001

# Init network
if True:
    import net
    net.DEBUG = True
    net.start_wlan(32)
    net.start_repl()

# Init Watchdog

import app
app.main()
