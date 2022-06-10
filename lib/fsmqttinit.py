"""
Init MQTT functions
"""

import board
try:
    import fsmqtt
except: #pylint: disable=bare-except
    fsmqtt = None


def _setup_mqtt_callbacks():
    if not board.MQTT:
        return
    if not fsmqtt:
        return
    for p in board.PWMs.pwms:
        # ha/light/led_mg_buero_dimm_spotwand/set
        fsmqtt.subscribe('light/{}/{}/set'.format(board.LOCATION, p.id), p.mqtt_callback)

if fsmqtt is not None:
    board.STARTUP_FUNCTIONS.append(_setup_mqtt_callbacks)
