"""
Kegellampe Application Module

MQTT client for Kegellampe with neo pixels.

80 LED in der Lampe.
Bei maximaler Helligkeit sind es ca. 1.5A bei 12V.
Der DC/DC Wandler (4A angegeben) wird nicht warm --> kein Kühlkörper nötig.

"""

import board
board.LOCATION = 'eg-wz-kegellampe'
board.HOSTNAME = 'kegellampe'
board.VERSION = '2025-12-14'
board.DEBUG = True

import machine, neopixel
import fsmqtt
import time
import net
import watchdog
import memstat


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

def _set_pixel(index: int, r: int, g: int, b: int):
    np[index] = (r, g, b)
    np.write()

_set_pixel(0, 0, 50, 0) # green dot to show we are alive
# show blue dot on WIFI connect
board.NET.after_connect.append(lambda: _set_pixel(0, 0, 0, 50))


def set_color(r: int, g: int, b: int):
    """Set all pixels to given color, send status to MQTT"""
    board.PRINTF('set_color {} {} {}', r, g, b)
    _set_color(r, g, b)
    board.PRINTF('set_color {} {} {} done', r, g, b)
    fsmqtt.publish('state/color', '{} {} {}'.format(r, g, b))
    board.PRINTF('set_color {} {} {} published', r, g, b)

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
    fsmqtt.publish('state/color', 'random max={}'.format(max))


def set_gradient(msg=4):
    """set gradient color effect, msg is scale factor"""
    scale = max(1, min(255, int(msg)))
    for i in range(DARK_Pixels, NPIXEL):
        r = (i - DARK_Pixels) * 255 // (NPIXEL - DARK_Pixels)
        g = 128
        b = int((255 - r)/scale)
        np[i] = (r, g, b)
    np.write()
    fsmqtt.publish('state/gradient', str(scale))


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
    fsmqtt.publish('state/led/{}'.format(index), '{} {} {}'.format(r, g, b))

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
    fsmqtt.publish('info/test', f'got message t={topic} mt={type(msg)}, msg={msg}')
    print(f"Got type: {type(msg)} {msg}")


fsmqtt.subscribe('test', test)
np[0] = (0, 128, 0)
np.write()

fsmqtt.subscribe('set/color', lambda _, msg: set_color_string(msg))
fsmqtt.subscribe('set/random', lambda _, msg: set_random(int(msg)))
fsmqtt.subscribe('set/gradient', lambda _, msg: set_gradient(msg))
fsmqtt.subscribe('set/off', lambda _, msg: all_off())
fsmqtt.subscribe('set/led', lambda _, msg: set_leds(msg))
fsmqtt.subscribe('mem', lambda _, msg: memstat.print_stats())

def _blink_green():
    np[0] = (100, 100, 0)
    np.write()
    time.sleep_ms(500)
    np [0] = (0, 0, 0)
    np.write()
    time.sleep_ms(500)
    all_off() # turn off all pixels and send status to MQTT

board.MQTT.after_connect.append(_blink_green)

net.connect_in_background()
fsmqtt.connect_in_background()

watchdog.start_later()


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


