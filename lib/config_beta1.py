"""
Sample board from EDAC (footprint not correct)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x

import board
import can

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


if board.CANID is not None:
    can.CAN(board.CANID, rx=35, tx=32)
