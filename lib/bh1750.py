import board
import can
import canid
import sensors
import bh1750fllrth

# Typische Lux Werte von https://www.beleuchtungdirekt.de/blog/lux-definition
#   Küche       	300-400
#   Wohnzimmer     	400-500
#   Schlafzimmer   	300-400
#   Badezimmer     	500-600
#   Arbeitszimmer  	280
#   Kinderzimmer   	140
#   Diele       	300

# https://www.monumentocruzdeltercermilenio.cl/blog/wieviel/wieviel-lumen-pro-qm.html
# Flur und Treppenhaus	        100 bis 150
# Wohnzimmer	                100 bis 150
# Essbereich	                600 bis 800
# Küche	                        250 bis 300
# Kinder- und Schlafzimmer	    100 bis 150
# Badezimmer	                250 bis 300
# Arbeitszimmer	                250 bis 300
# Abstellraum, Keller, Hobbyr	100 bis 300


class BH1750(sensors.Sensor):
    def __init__(self, portid, address=0x23, poll_intervall_in_ms=2000):
        self.bh1750 = bh1750fllrth.BH1750(address, board.I2C)
        super().__init__('BH1750', portid, board.I2C_SDA_PIN, poll_intervall_in_ms)
        self.msg = can.makemessage(canid.DATALOGGER_BRIGHTNESS_SENSOR_8, 6)
        self.msg.setsender(self.portid)

    def run(self):
        x = self.bh1750.measurement
        print('BH1750: {:.2f} lux'.format(x))
        if board.CAN is not None:
            i = int(x)
            payload = self.msg.payload
            payload[3] = 1 # send as LUX
            payload[4] = i >> 8
            payload[5] = i & 0xff
            self.msg.send()

