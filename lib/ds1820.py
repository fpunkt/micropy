import machine
import ds18x20
import onewire
import sensors
import asyncio
import can
import canid

import board

class DS1820(sensors.Sensorxxx):
    """DS18x20 temperature sensors"""
    def __init__(self, portid, pin, poll_intervall_in_ms=sensors.poll_5_minutes):
        super().__init__('DS1820', portid, pin, poll_intervall_in_ms)
        self.mpin = machine.Pin(pin)
        self.onwire = onewire.OneWire(self.mpin)
        self.ds = ds18x20.DS18X20(self.onwire)
        self.roms = None
        self.arun = self._arun
        self.scan()
        self.ndevices = len(self.roms)
        # create list once to avoid gc
        self.data = [0]*self.ndevices
        self.callback = None
        self.msg = can.Message(canid.DATALOGGER_TEMPERATURE_SENSOR, 8*[0])
        self.msg.setsender(board.CANID)

    def scan(self):
        """Scan for DS18x20 devices on the bus"""
        #print('Scanning for devices')
        self.roms = self.ds.scan()

    def _pack(self, pos, val):
        ival = int((max(val, -54.9)+55)*20)
        ival = min(ival, 0xfff)
        if val < -99:
            ival = 1
        #print('** {:d}  val={:5.1f} -> ival={:5d} -> 0x{:02x}'.format(pos, val, ival, ival))
        payload = self.msg.payload
        if pos == 0 or pos == 2:
            offset = 2 if pos == 0 else 5
            payload[offset+0] = ival >> 4
            payload[offset+1] |= (ival&0xf) << 4
        elif pos == 1 or pos == 3:
            offset = 3 if pos == 1 else 6
            payload[offset+0] |= (ival>>8)&0xf
            payload[offset+1] = ival&0xff

    def send_telemetry(self):
        if board.CAN is None:
            return
        for i in range(2, 7):
            self.msg.payload[i] = 0
        i=0
        for d in self.data:
            self._pack(i, d)
            i += 1
        #print(' '.join(map(hex, self.msg.payload)))
        self.msg.send()


    async def _arun(self):
        """Trigger conversion and collect data after about 2 seconds"""
        #print('scanning...')
        try:
            self.ds.convert_temp()
        except Exception as e:
            print('Cannot scan ', e)
            return
        #print('going to sleep')
        await asyncio.sleep_ms(2000)
        #print('reading')
        try:
            for i in range(self.ndevices):
                try:
                    self.data[i] = self.ds.read_temp(self.roms[i])
                except:
                    self.data[i] = -99

            # for r in self.roms:
            #     try:
            #         print('{:.2f}'.format(self.ds.read_temp(r)), end=' ')
            #     except:
            #         print('ERR', end=' ')
            # print()
            #print(self.data)
            self.send_telemetry()
            if self.callback is not None:
                try:
                    self.callback(self.data)
                except Exception as e:
                    print('Error running ds1820 callback: {}'.format(e))
                    pass
        except KeyboardInterrupt:
            raise
        except:
            print('cannot read DS1820')
