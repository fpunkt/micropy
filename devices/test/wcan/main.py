"""
Test the WCAN package
"""

try:
    import uasyncio as asyncio
except:
    import asyncio

import sys
if sys.platform != 'linux':
    import net
    net.start_wlan()
    net.start_repl() # need for copy



