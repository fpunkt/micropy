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
        board.PORTs.register(portid, self)

    def __repr__(self) -> str:
        return self._repr('')

    def _repr(self, more) -> str:
        if isinstance(self.portid, int):
            ids = hex(self.portid)
        else:
            ids = 'None'
        return '<{}:{}.{}{}{}>'.format(self.__class__.__name__, ids, self.pin, ' ' if more else '', more)

    def send_disabled_error(self):
        """Call this when the port has been disabled for some reason"""
        print('Disabled: {}'.format(self))
        if board.CAN is not None:
            board.CAN.cancommon.errormessage([board.CAN.canerror.SENSOR_DISABLED, self.portid])

    def send_exception_during_run_error(self, e):
        """Call this when an exception occured during the run method"""
        if board.DEBUG:
            print('Exception from {}: {}'.format(self, e))
            # sys.print_exception(e)
        if board.CAN is not None:
            board.CAN.cancommon.errormessage([board.CAN.canerror.SENSOR_EXCEPTION_DURING_RUN, self.portid])

    def update_payload(self):
        """Set all payload bytes, overload this."""
        if board.DEBUG:
            print('Called update_payload - not overloaded for {}'.format(self))
        return

    def update_telemetry(self):
        """Update self.msg to the current status.
        Might be called regulary by some background task in order to send telemetry.
        Packages sent by this call should clearly indicate that nothing changed, i.e. no action is required
        """
        if board.DEBUG:
            print('Called update_telemetry - not overloaded for {}'.format(self))
        pass

    def can_is_active(self):
        """Return true when CAN bus is up and running and message sending is enabled"""
        return board.CAN is not None and  self.msg is not None

    def send_message(self):
        """Called this when the port status has changed and you want to send the updated status to the bus"""
        if self.can_is_active():
            self.msg.send()

    def update_payload_and_send_message(self):
        if self.can_is_active():
            self.update_payload()
            self.msg.send()



