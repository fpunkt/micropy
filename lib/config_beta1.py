"""
Sample board from EDAC (footprint not correct)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x


import can

AUX1_YELLOW = const(13)
AUX1_WHITE = const(12)

AUX2_YELLOW = const(26)
AUX2_WHITE = const(25)


def CAN(canid):
    return can.CAN(canid, rx=35, tx=32)
