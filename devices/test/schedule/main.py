"""
Test schedule
"""

# pylint: disable=multiple-statements
import net; net.start_wlan(); net.start_repl()

import board
import schedule

board.LOCATION = 'test_schedule'


schedule.run_in_ms(3000, lambda: print('run once'))
schedule.run_in_ms(4000, lambda: print('run every other second'), repeat_ms=2000)
