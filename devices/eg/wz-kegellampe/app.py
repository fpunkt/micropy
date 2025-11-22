"""
Kegellampe Application Module

MQTT client for Kegellampe with neo pixels.
"""

import board
board.LOCATION = 'eg-wz-kegellampe'

import machine, neopixel
import fsmqtt


NPIXEL = 180
np = neopixel.NeoPixel(machine.Pin(4), NPIXEL) # type: ignore

fsmqtt.connect('kegellampe')

DARK_Pixels = 140
DARK_Pixels = 141


def set_color(r: int, g: int, b: int):
    for index in range(DARK_Pixels, NPIXEL):
        np[index] = (r, g, b)
    np.write()
    fsmqtt.publish('status/color', '{} {} {}'.format(r, g, b))

def all_off():
    set_color(0, 0, 0)


def set_random(max: int = 255):
    import urandom
    for i in range(DARK_Pixels, NPIXEL):
        r = urandom.getrandbits(8) % (max + 1)
        g = urandom.getrandbits(8) % (max + 1)
        b = urandom.getrandbits(8) % (max + 1)
        np[i] = (r, g, b)
    np.write()
    fsmqtt.publish('status/color', 'random max={}'.format(max))


def set_gradient(msg=4):
    scale = max(1, min(255, int(msg)))
    for i in range(DARK_Pixels, NPIXEL):
        r = (i - DARK_Pixels) * 255 // (NPIXEL - DARK_Pixels)
        g = 128
        b = int((255 - r)/scale)
        np[i] = (r, g, b)
    np.write()
    fsmqtt.publish('status/color', 'gradient')


def set_color_string(colorstring: str):
    """set color from string like '255 0 128'"""
    parts = colorstring.split(' ')
    if len(parts) != 3:
        return
    r = int(parts[0])
    g = int(parts[1])
    b = int(parts[2])
    set_color(r, g, b)

def test(topic, msg):
    fsmqtt.publish('status/test', f'got message t={topic} mt={type(msg)}, msg={msg}')
    print(f"Got type: {type(msg)} {msg}")

fsmqtt.subscribe('test', test)

fsmqtt.subscribe('set/color', lambda _, msg: set_color_string(msg))
fsmqtt.subscribe('set/random', lambda _, msg: set_random(int(msg)))
fsmqtt.subscribe('set/gradient', lambda _, msg: set_gradient(msg))
fsmqtt.subscribe('set/off', lambda _, msg: all_off())

set_random(100)

def r():
    board.restart()

#def main():
#    board.run()

