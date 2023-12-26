"""
Ports - base class for all sensors, PWMs, buttons, etc.
"""


import board

class Port:
    def __init__(self, portid, pin) -> None:
        self.portid = portid
        self.pin = pin
        # keep a static can message per port to avoid frequent allocs
        self.msg = None
        board.SENSORSs.register(portid, self)

    def __repr__(self) -> str:
        return self._repr('')

    def _repr(self, more) -> str:
        if isinstance(self.portid, int):
            ids = hex(self.portid)
        else:
            ids = 'None'
        return '<{}:{}.{}{}>'.format(self.__class__.__name__, ids, self.pinid, more)


