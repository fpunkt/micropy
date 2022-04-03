"""
First ESP32 board from EasyEDA
2 x ML10 connector
4 x Grove connector
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

import board

# The on-chip LED
board.LED = board.Led(2)

AUX1_YELLOW = const(13)
AUX1_WHITE = const(12)

AUX2_YELLOW = const(26)
AUX2_WHITE = const(25)

AUX3_YELLOW = const(33)
AUX3_WHITE = const(27)

AUX4_YELLOW = const(34)
AUX4_WHITE = const(14)

ML10_PWM_1 = const(15)
ML10_PWM_2 = const(4)
ML10_PWM_3 = const(16)
ML10_PWM_4 = const(17)
ML10_PWM_5 = const(5)
ML10_PWM_6 = const(18)
ML10_PWM_7 = const(19)
ML10_PWM_8 = const(21)


# 2nd ML10 connector
ML10_1 = const(12)
ML10_2 = const(13)
ML10_3 = const(14)
ML10_4 = const(25)
ML10_5 = const(26)
ML10_6 = const(27)
ML10_7 = const(33)
ML10_8 = const(34)


if board.CANID is not None:
    import can
    can.init(board.CANID, rx=35, tx=32)
    board.CAN = can
    can.cancommon.send_poweron()
