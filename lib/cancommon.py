import board
import canid
import canerror
import canconf
import asyncio
import gc
import machine
import net
import utime

# last upload time
try:
    import lup
    _lastupload = lup.T
except:
    _lastupload = 0


class Message:
    """A CAN message"""
    def __init__(self, cid, payload):
        self.canid = cid
        self.payload = payload

    def payloadstring(self):
        return ' '.join('{:02x}'.format(x) for x in self.payload)
        # return _payloadstring(self.payload)

    def __repr__(self):
        return '<Message #{:03x} [{}] {}>'.format(self.canid, len(self.payload), self.payloadstring())

    def setsender(self, senderid):
        """Fill canid and senderid"""
        if board.CAN is None:
            return
        self.payload[0] = board.CANID >> 8
        self.payload[1] = board.CANID & 0xff
        self.payload[2] = senderid

    def send(self):
        """Send message"""
        if board.CAN is None:
            return
        board.CAN.write(self.canid, self.payload)

    def u16(self, pos):
        return (self.payload[pos] << 8) + self.payload[pos+1]

    def bad_number_of_args(self, min, max=None):
        p = self.payload
        if len(p) < 1:
            errormessage([canerror.INTERNAL_ERROR, 0xa0])
            return
        # fmt.Sprintf("Bad number of parameters for command #%02x: got %d expected %d .. %d", d[0], d[1], d[2], d[3])
        if max is None:
            max = min
        errormessage([canerror.BAD_NUMBER_OF_PARAMETERS, p[0], len(p), min, max])

    # "Command #%02x: bad value for paramenter %d, found %d expected, %d .. %d", d0, d1, d2, d3, d4)
    def bad_parameter_value(self, n, min, max):
        p = self.payload
        pn = 0
        if n >= len(p):
            if board.DEBUG:
                print('want param {} for {}'.format(n, self))
            errormessage([canerror.INTERNAL_ERROR, 0xa1])
        else:
            pn = p[n]
        errormessage([canerror.BAD_PARAMETER_VALUE, p[0], n, pn, min, max])

    def bad_sensor_id(self):
        self.bad_parameter_value(1, 0xff, 0xff)

    def bad_sensor_type(self, expected):
        self.bad_parameter_value(1, 0xff, 0)

    def unknown_command(self):
        if board.DEBUG:
            print('# Error: unknown CAN command {}'.format(self))
        c = 0
        if len(self.payload) > 0:
            c = self.payload[0]
        errormessage([canerror.UNKNOWN_COMMAND, c])


def makemessage(cid, size, portid=None):
    m = Message(cid, [0]*size)
    if portid is not None:
        m.setsender(portid)
    return m


# cached message to avoid mallocs
static_incomming_message = Message(0, bytearray([0, 1, 2, 3, 4, 5, 6, 7]))
Badmessage = Message(0x777, [1, 2, 3, 4])



# cache message, only update payload. OK since with asyncio there will be no raceing
_errormessage = Message(canid.ERROR_MESSAGE, [])

def errormessage(payload):
    if board.CAN is None:
        return
    _errormessage.payload = [(board.CANID >> 8) & 0xff, (board.CANID >> 0) & 0xff] + payload
    _errormessage.send()




# Ping
_pingmessage = None
if board.CANID is not None:
    _pingmessage = Message(canid.PING_MESSAGE, [board.CANID >> 8, board.CANID & 0xff, 0, 0, 0, 0])

def _send_ping():
    """Send a ping message"""
    # Hack ... this should be a member of class CAN, we treat self like this
    uptime = board.uptime_s()
    # use pre-allocated message to avoid garbage collection
    b = _pingmessage.payload
    # b[0] = self.canid >> 8
    # b[1] = self.canid & 0xff
    b[2] = (uptime >> 24) & 0xff
    b[3] = (uptime >> 16) & 0xff
    b[4] = (uptime >>  8) & 0xff
    b[5] = (uptime >>  0) & 0xff
    _pingmessage.send()

async def _ping_job():
    while True:
        if board.CAN is not None:
            try:
                _send_ping()
            except Exception as e:
                if board.DEBUG:
                    print('Cannot send ping: {}'.format(e))
        await asyncio.sleep(board.PINGTIME)

board.BACKGROUND_RUNNERS.append(_ping_job())

def _send_ping_or_change_rate(m):
    if len(m.payload) == 1:
        _send_ping()
        return
    t = m.payload[1]
    if len(m.payload) == 3:
        t = (t << 8) + m.payload[2]
    board.PINGTIME = t


if board.CANID is not None:
    _memstat_message = Message(canid.MEMORY_STATUS, [board.CANID >> 8, board.CANID & 0xff, 0, 0, 0, 0, 0, 0])
_gc_counter = 0

def _send_memstat():
    free = gc.mem_free()     # pylint: disable=no-member
    if board.CAN:
        b = _memstat_message.payload
        # b[0] = _memstat_message.canid >> 8
        # b[1] = _memstat_message.canid & 0xff
        b[2] = (_gc_counter >>  8) & 0xff
        b[3] = _gc_counter & 0xff
        b[4] = (free >> 24) & 0xff
        b[5] = (free >> 16) & 0xff
        b[6] = (free >>  8) & 0xff
        b[7] = free & 0xff
        _memstat_message.send()


def send_poweron():
    """Send a power-on message to the bus"""
    _identify(canid.POWER_ON)

def identify():
    _identify(canid.IDENTIFY)

def _identify(packetid):
    if board.CAN and board.CANID:
        serial = machine.unique_id()
        board.CAN.write(packetid, [board.CANID >>8, board.CANID & 0xff,
                machine.reset_cause(), # startup reason
                2, # HClib Version
                12, # HW Type -- make this 12 for ESP32 ..
                0xa0, # Application type and Version - make this the library version
                serial[-2], serial[-1]]) # CPU serial

def sendlup():
    board.CAN.write(canid.CONFIG_INFO, [board.CANID >>8, board.CANID & 0xff,
        1,
        (_lastupload >> 24) & 0xff,
        (_lastupload >> 16) & 0xff,
        (_lastupload >>  8) & 0xff,
        (_lastupload >>  0) & 0xff,
         ])

def sendconfig(m):
    if not (board.CAN and board.CANID):
        return
    l = len(m.payload)
    if l == 1 or (l == 2 and m.payload[1] == 0):
        board.CAN.write(canid.CONFIG_INFO, [board.CANID >>8, board.CANID & 0xff,
            0,
            board.CPU_ID,
            board.BOARD_ID,
            board.PERIPH_ID,
        ])
        return
    c = m.payload[1]
    if c == 1:
        sendlup()
        return

    m.bad_parameter_value(1, 0, 1)


def run_gc():
    global _gc_counter # pylint: disable=global-statement
    _send_memstat()
    _gc_counter += 1
    if not board.DEBUG:
        gc.collect()
    else:
        free = gc.mem_free() # pylint: disable=no-member
        start = utime.ticks_ms()
        gc.collect()
        newfree = gc.mem_free() # pylint: disable=no-member
        if board.DEBUG:
            print('GC run {} collected {} bytes in {} ms, free={}'.format(
                _gc_counter, newfree-free, utime.ticks_diff(utime.ticks_ms(), start), newfree))
    _send_memstat()

board.run_gc = run_gc

async def _memstat_reporter_task():
    while True:
        _send_memstat()
        await asyncio.sleep(board.MEMSTATTIME)

board.BACKGROUND_RUNNERS.append(_memstat_reporter_task())


# Regiser CAN commands known by this device

# dict of list(minargs, maxargs, callback)
_handlers = dict()

def register(commandbyte, minargs, maxargs, callback):
    if _handlers.get(commandbyte, None) is not None:
        raise RuntimeError('CAN callback for {} already defined'.format(commandbyte))

    _handlers[commandbyte] = (minargs, maxargs, callback)

### Common config commands

# Basic configuration commands common to all applications are handled by this layer.
#
# Config commands (assuming CAN address 100)
#
# cansend 100#fd # START WLAN and repl
# cansend 100#fe # STOP WLAN and repl
#
# cansend 200#fd # START WLAN and repl

def send_wlan_connected(ip=None):
    if not board.CAN:
        return
    # board.LED.on()
    if ip is None:
        ip = net.wlan_ip(ip)
    try:
        ip = list(map(int, ip[0].split('.')))
        #print('ipx', ipx)
        board.CAN.write(canid.WLAN_CONNECTED, [board.CANID >>8, board.CANID & 0xff, ip[0], ip[1], ip[2], ip[3]])
    except:
        if board.DEBUG:
            print('** ERROR: Cannot send WLAN IP for {}'.format(ip))

# Send wlan status at startup
send_wlan_connected()


async def _report_net_status():
    while True:
        await asyncio.sleep(600) # report each 10 minutes
        try:
            ip = net.wlan_ip()
            if ip is not None:
                send_wlan_connected(ip)
        except:
            pass

board.BACKGROUND_RUNNERS.append(_report_net_status())

def _connect_to_wlan(m):
    if len(m.payload) == 2:
        b = m.payload[1]
    else:
        b = 0
    send_wlan_connected(net.start_wlan(b))

def _disconnect_wlan(_):
    if board.DEBUG:
        print('DEBUGGING turned off with WLAN - to turn on again run  cansend {:03x}#7e'.format(board.CANID))
        board.DEBUG = False
    net.stop_wlan()
    send_wlan_connected(("0.0.0.0", None))

def _debug_on_off(m):
    board.DEBUG = len(m.payload) > 1 and m.payload[1] != 0
    print('board.DEBUG now is {}'.format(board.DEBUG))


register(canconf.WLAN_CONNECT, 1, 2, lambda m: _connect_to_wlan(m))
register(canconf.WLAN_HOTSPOT, 1, 1, lambda _: send_wlan_connected(net.start_hotspot()))
register(canconf.WLAN_STOP, 1, 1, _disconnect_wlan)
register(canconf.REQUEST_PING_FROM_DEVICE, 1, 3, lambda m: _send_ping_or_change_rate(m))
register(canconf.SOFT_RESET, 1, 1, lambda _: machine.soft_reset())
register(canconf.HARD_RESET, 1, 1, lambda _: machine.reset())
register(canconf.INDENTIFY, 1, 1, lambda _: board.CAN.identify())
register(canconf.WEBREPL_START, 1, 1, lambda _: net.start_repl())
register(canconf.WEBREPL_STOP, 1, 1, lambda _: net.stop_repl())
register(canconf.SEND_FREEMEM, 1, 1, lambda _: _send_memstat())
register(canconf.ENABLE_WATCHDOG, 1, 1, lambda _: board.WD.enable())
register(canconf.SEND_INFO, 1, 2, sendconfig)
register(canconf.DEBUG_ON_OFF, 1, 2, _debug_on_off)


_callback = None
_subscribed_to_canid = None

def subscribe(callback, canid=None):
    """Subscribe to packages on the CAN bus.
    cid==True subscribes to all messages
    cid==None subscribes to the own CAN ID
    cid==id subscribes to messages with the given ID"""
    global _callback, _subscribed_to_canid
    _callback = callback
    if canid is None:
        _subscribed_to_canid = board.CANID
    else:
        _subscribed_to_canid = canid


def dispatch_incomming_message():
    # check for installed handler for that message
    payload = static_incomming_message.payload
    # print('# Dispatching {:03x} for board {:03x}'.format(static_incomming_message.canid, board.CANID))
    if board.CANID != static_incomming_message.canid:
        if board.DEBUG:
            print('Got Message for id {:03x} - check filter'.format(static_incomming_message.canid))
        return

    if len(payload) > 0:
        handler = _handlers.get(payload[0], None)
        if handler is not None:
            minargs, maxargs, callback = handler
            if len(payload) < minargs or len(payload) > maxargs:
                if board.DEBUG:
                    print('Bad number of args {}, expected {}..{}'.format(len(payload), minargs, maxargs))
                static_incomming_message.bad_number_of_args(minargs, maxargs)
                return
            # run the callback
            try:
                callback(static_incomming_message)
            except Exception as e: # pylint: disable=broad-except
                if board.DEBUG:
                    print('Callback raised error: {}'.format(e))
            return True
    if _callback is None:
        return False
    if _subscribed_to_canid is True or _subscribed_to_canid == static_incomming_message.canid:
        _callback(static_incomming_message)
        return True
    return False
