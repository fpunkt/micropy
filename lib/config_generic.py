"""
Generic ESP board with CAN - no special H/W
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

import board

board.BOARD_ID = 66

# The on-chip LED
board.LED = board.Led(2)


if board.CANID is not None:
    import can
    can.init(board.CANID, rx=35, tx=32)
    board.CAN = can
    can.cancommon.send_poweron()
