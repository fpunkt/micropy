"""
Button press emulator controlled by CAN messages
"""

from cancommon import register
from canconf import EMULATE_BUTTON_PRESSED
import button

def _button_press(m):
    b = button.find(m)
    if b:
        p = m.payload[2] if len(m.payload) > 2 else 2
        if p == 0:
            b.pressed()

register(EMULATE_BUTTON_PRESSED, 2, 3, _button_press)
