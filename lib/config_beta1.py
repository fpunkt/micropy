"""
Sample board from EDAC (footprint not correct)
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments


import can

AUX1_YELLOW = 13
AUX2_WHITE = 12

AUX2_YELLOW = 26
AUX2_WHITE = 25


def CAN(canid):
    return can.CAN(canid, rx=35, tx=32)
