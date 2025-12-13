"""
Kegellampe Application Module

MQTT client for Kegellampe with neo pixels.

80 LED in der Lampe.
Bei maximaler Helligkeit sind es ca. 1.5A bei 12V.
Der DC/DC Wandler (4A angegeben) wird nicht warm --> kein Kühlkörper nötig.

"""

import board
board.LOCATION = 'eg-wz-kegellampe'
board.VERSION = '2025-11-24'
# board.DEBUG = True

import machine, neopixel
import fsmqtt
import time
import net


NPIXEL = 80
np = neopixel.NeoPixel(machine.Pin(1), NPIXEL) # type: ignore


DARK_Pixels = 140
DARK_Pixels = 141
DARK_Pixels = 0

def _set_color(r: int, g: int, b: int):
    """Set all pixels to given color, internal use only"""
    for index in range(DARK_Pixels, NPIXEL):
        np[index] = (r, g, b)
    np.write()

_set_color(0, 0, 0)
np[0] = (50, 50, 0) # make a green dot to show we are alive
np.write()
time.sleep(0.5)

def set_color(r: int, g: int, b: int):
    """Set all pixels to given color, send status to MQTT"""
    _set_color(r, g, b)
    fsmqtt.publish('status/color', '{} {} {}'.format(r, g, b))

def all_off():
    """Turn off all pixels"""
    set_color(0, 0, 0)


def set_random(max: int = 255):
    """set random colors with max brightness"""
    import urandom
    for i in range(DARK_Pixels, NPIXEL):
        r = urandom.getrandbits(8) % (max + 1)
        g = urandom.getrandbits(8) % (max + 1)
        b = urandom.getrandbits(8) % (max + 1)
        np[i] = (r, g, b)
    np.write()
    fsmqtt.publish('status/color', 'random max={}'.format(max))


def set_gradient(msg=4):
    """set gradient color effect, msg is scale factor"""
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

def set_led(index: int, r: int, g: int, b: int):
    """set single led color"""
    if index < DARK_Pixels or index >= NPIXEL:
        return
    np[index] = (r, g, b)
    np.write()
    fsmqtt.publish('status/led/{}'.format(index), '{} {} {}'.format(r, g, b))

def set_leds(colorstring: str):
    """set multiple leds from string like '0 255 0 0;1 0 255 0;2 0 0 255'"""
    parts = colorstring.split(';')
    for part in parts:
        subparts = part.split(' ')
        if len(subparts) != 4:
            continue
        index = int(subparts[0])
        r = int(subparts[1])
        g = int(subparts[2])
        b = int(subparts[3])
        set_led(index, r, g, b)


def test(topic, msg):
    fsmqtt.publish('status/test', f'got message t={topic} mt={type(msg)}, msg={msg}')
    print(f"Got type: {type(msg)} {msg}")


fsmqtt.subscribe('test', test)
np[0] = (0, 128, 0)
np.write()

fsmqtt.subscribe('set/color', lambda _, msg: set_color_string(msg))
fsmqtt.subscribe('set/random', lambda _, msg: set_random(int(msg)))
fsmqtt.subscribe('set/gradient', lambda _, msg: set_gradient(msg))
fsmqtt.subscribe('set/off', lambda _, msg: all_off())
fsmqtt.subscribe('set/led', lambda _, msg: set_leds(msg))

def _blink_red():
    np[0] = (255, 0, 0)
    np.write()
    time.sleep(0.5)
    np [0] = (0, 0, 0)
    np.write()
    time.sleep(0.5)
    
fsmqtt.after_connect.append(_blink_red)
fsmqtt.after_connect.append(all_off)

net.connect_in_background()
fsmqtt.connect_in_background()


def r():
    board.restart()


try:
    if 0 == 1: # pylint: disable=comparison-with-itself
        board.run()
    else: 
        print('# run  restart   (or board.run()) to start event handler')

except Exception as e: # pylint: disable=bare-except, broad-except
    print('Exception in main loop: ', e)
    print("Try to connect to WLAN")
    import net
    net.net()


