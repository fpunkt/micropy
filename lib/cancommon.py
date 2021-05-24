
"""
cancommon.py

Common CAN definitions

Basic configuration commands common to all applications are handled by this layer.

Config commands (assuming CAN address 100)

cansend 100#fd # START WLAN and repl
cansend 100#fe # STOP WLAN and repl

cansend 200#fd # START WLAN and repl

"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

#import utime
import net
import machine
import board
import canconf


# Compile once to save mallocs with every CAN package

_CONFIG_SOFT_RESET = bytearray([canconf.SOFT_RESET])
_CONFIG_HARD_RESET = bytearray([canconf.HARD_RESET])
_CONFIG_SEND_PING = bytearray([canconf.SEND_PING])
_CONFIG_WLAN_CONNECT = bytearray([canconf.WLAN_CONNECT])
_CONFIG_WLAN_HOTSPOT = bytearray([canconf.WLAN_HOTSPOT])
_CONFIG_WLAN_STOP = bytearray([canconf.WLAN_STOP])
_CONFIG_WEBREPL_START = bytearray([canconf.WEBREPL_START])
_CONFIG_WEBREPL_STOP = bytearray([canconf.WEBREPL_STOP])
_CONFIG_INDENTIFY = bytearray([canconf.INDENTIFY])

def handle_standard_config_command(self, payload):
    """Return True if standard CAN command has been found and processed"""
    # Hack ... this should be a member of class CAN, we treat self like this
    # pylint: disable=too-many-return-statements
    if len(payload) < 1 or payload[0] < canconf.CONFIG_BEGIN:
        return False

    if payload in (_CONFIG_WLAN_CONNECT, _CONFIG_WLAN_HOTSPOT):
        if payload == _CONFIG_WLAN_CONNECT:
            ip = net.start_wlan()
        else:
            ip = net.start_hotspot()
        board.LED.on()
        ipx = list(map(int, ip[0].split('.')))
        #print('ipx', ipx)
        self.send_wlan_connected(ipx)
        #self.send(CANID_WLAN_CONNECTED, [self.canid >>8, self.canid & 0xff, ipx[0], ipx[1], ipx[2], ipx[3]])
        return True

    if payload == _CONFIG_INDENTIFY:
        self.identify()
        return True

    if payload == _CONFIG_WLAN_STOP:
        net.stop_wlan()
        return True

    if payload == _CONFIG_WEBREPL_START:
        net.start_repl()
        return True

    if payload == _CONFIG_WEBREPL_STOP:
        net.stop_repl()
        return True

    if payload == _CONFIG_SEND_PING:
        self.send_ping()
        return True

    if payload == _CONFIG_SOFT_RESET:
        machine.soft_reset()

    if payload == _CONFIG_HARD_RESET:
        machine.reset()

    return False
