import board
import can
import canid
import sensors
import ahti2c

class _aht(sensors.Sensor):
    def __init__(self, name, portid, aht, poll_intervall_in_ms, background_task) -> None:
        if poll_intervall_in_ms is None:
             poll_intervall_in_ms = 5 * 60 * 1000 # once every 5 minutes
        super().__init__(portid, board.I2C_SDA_PIN, poll_intervall_in_ms, background_task)
        self.name = name
        self.aht = aht
        self.msg = can.makemessage(canid.DATALOGGER_AM2302, 7)
        self.msg.setsender(self.portid)

    async def poll(self):
        try:
            await self.aht._perform_measurement()
        except:
            self.read_error()
            raise

    def update_payload(self):
        t = int(10*self.aht.T())
        h = int(10*self.aht.H())
        # print('T={} ({}), H={} ({})'.format(t, type(t), h, type(h)))
        if board.CAN is not None:
            payload = self.msg.payload
            payload[3] = h >> 8
            payload[4] = h & 0xff
            payload[5] = t >> 8
            payload[6] = t & 0xff

        board.MQTT_PUBLISH("state/" + str(self.portid), f'{self.aht.T():.1f} {self.aht.H():.1f}')

class AHT10(_aht):
    def __init__(self, portid, poll_intervall_in_ms=None, address=0x38, background_task=None) -> None:
        super().__init__('AHT10',
            portid,
            ahti2c.AHT10(board.I2C, address=address),
            poll_intervall_in_ms,
            background_task)


class AHT20(_aht):
    def __init__(self, portid, poll_intervall_in_ms=None, address=0x38, background_task=None) -> None:
        super().__init__('AHT20',
            portid,
            ahti2c.AHT20(board.I2C, address=address),
            poll_intervall_in_ms,
            background_task)
