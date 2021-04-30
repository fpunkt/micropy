"""
cancodes.py

cansend 100#fd # START WLAN and repl
cansend 100#fe # STOP WLAN and repl

"""
# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const

# CANID_POWER_ON message sent to the CAN Bus
CANID_POWER_ON = const(0x3c4)
CANID_IDENTIFY = const(0x3c5)
CANID_DATALOGGER_AM2302 = const(0x6f1)
CANID_PING = const(0x7e0)
CANID_WLAN_CONNECTED = const(0x3c6)
CANID_PWM_VALUE = const(0x03c8)
CANID_DATALOGGER_BRIGHTNESS_SENSOR_8 = const(0x6f6) #

# CAN commands and configuration handled by each device
# All general config commands must be >= 0xe8

CONFIG_BEGIN = const(0xf0)

CONFIG_HARD_RESET = const(0xf0)
CONFIG_SOFT_RESET = const(0xf1)
CONFIG_SEND_PING = const(0xf2)
CONFIG_INDENTIFY = const(0xf3)

# Network config
CONFIG_WLAN_CONNECT = const(0xfa)
CONFIG_WLAN_HOTSPOT = const(0xfb)
CONFIG_WLAN_STOP = const(0xfc)
CONFIG_WEBREPL_START = const(0xfd)
CONFIG_WEBREPL_STOP = const(0xfe)
