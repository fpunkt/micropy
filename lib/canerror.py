"""
Constant file generated from canerror.toml
"""
if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const
INTERNAL_ERROR                                     = const(    5) # 0x0005
BAD_PWM_NUMBER                                     = const(    6) # 0x0006
UNKNOWN_CONFIG_COMMAND                             = const(   10) # 0x000a
# Device ID is used more than once
XMULTIPLE_USE_OF_DEVICE_ID                         = const(    4) # 0x0004
BAD_PARAMETER_VALUE                                = const(    4) # 0x0004
CAN_UNKNOWN_COMMAND                                = const(    3) # 0x0003
UNKNOWN_SUBCOMMAND                                 = const(    7) # 0x0007
FUNCTION_NOT_IMPLEMENTED                           = const(    9) # 0x0009
# special value used when indicating NO error (but 0 return value already reserved)
CAN_NO_ERROR                                       = const(  255) # 0x00ff
# Too many devices
XINTERNAL_TOO_MANY_DEVICES                         = const(    3) # 0x0003
BAD_NUMBER_OF_PARAMETERS                           = const(    2) # 0x0002
# Internal error, more PWMs defined as allowed by array dimension on CAN device
TOO_MANY_PWMS                                      = const(   40) # 0x0028
TEST                                               = const(    1) # 0x0001
