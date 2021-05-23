"""
Scheduled tasks.
Callbacks are called outside IRQ context at earliest convenience.

Scheduled tasked can be used to poll sensors in a regular intervall or
to provide timeout for functions (moving motors to arrive) or add actions to motions sensors.

In principle sub-second resolution is possible (functions use milliseconds),
but don't expect too much accuracy.

This file uses timer 2

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods

import micropython
import utime
import machine
import pwm
import uasyncio as asyncio

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const

micropython.alloc_emergency_exception_buf(100)

class OutOfIRQRunnerClass:
    def __init__(self):
        self.stack = [None, None, None, None, None]
        self.scheduled = False
        self._run_ref = self._runlist

    def _runlist(self, _):
        # print('Running {}'.format(self.stack))
        i = 0
        l = []

        # keep blocked IRQ as short as possible
        irq_state = machine.disable_irq()
        while i < len(self.stack):
            cb = self.stack[i]
            if cb is not None:
                l.append(self.stack[i])
                self.stack[i] = None
            i += 1
        self.scheduled = False
        machine.enable_irq(irq_state)

        while l:
            cb = l.pop(0)
            try:
                # pylint: disable=not-callable
                cb(None)
            except: # pylint: disable=bare-except
                pass

    def run_outside_irq_disable_irq_around_me(self, callback):
        i = 0
        while i < len(self.stack):
            if self.stack[i] is None:
                self.stack[i] = callback
                break
            i += 1
        # silently ignore if no slot is free
        if not self.scheduled:
            self.scheduled = True
            micropython.schedule(self._run_ref, None)

    def xxrun_outside_irq(self, callback):
        irq_state = machine.disable_irq()
        self.run_outside_irq_disable_irq_around_me(callback)
        machine.enable_irq(irq_state)

outside_irq = OutOfIRQRunnerClass()


# schedule_1_minute = const(1 * 60 * 1000)
# schedule_5_minutes = const(5 * 60 * 1000)

class ScheduledItem:
    def __init__(self, label=None):
        if label is None:
            label = 'undefined task'
        self.label = label
        self.sleep_before_ms = 0
        self.repeat_ms = 0
        self.active = True

    async def run_in_background(self):
        await asyncio.sleep_ms(self.sleep_before_ms)
        self.run()
        while self.active and self.repeat_ms > 0:
            await asyncio.sleep_ms(self.repeat_ms)
            self.run()
        self.active = False

    def __repr__(self):
        return '<{}:{} poll interval={} ms, next in {} ms>'.format(
            self.__class__.__name__, self.label,
            self.repeat_ms,
            utime.ticks_diff(self.sleep_before_ms, utime.ticks_ms()))

    def run(self):
        pass

    def cancel(self):
        """dont run again"""
        self.active = False
        schedule_list.remove(self)

class ScheduledItemWithCallback(ScheduledItem):
    def __init__(self, label, callback):
        super().__init__(label)
        self.callback = callback

    def run(self):
        if self.callback is not None:
            self.callback()

    def cancel(self):
        self.repeat_ms = 0
        self.callback = None

class ScheduledItemWithData(ScheduledItemWithCallback):
    def __init__(self, label, callback, data):
        super().__init__(label, callback)
        self.data = data

    def run(self):
        if self.callback is not None:
            self.callback(self.data)


class ScheduleList:
    """A list of all scheduled items"""
    def __init__(self):
        # use a pre-alloced list to avoid GC
        self.items = [None, None, None, None, None, None, None, None, None, None]
        self.running = []
        self.last = 0

    def append(self, item):
        if self.last >= len(self.items):
            self.items.append(item)
        else:
            self.items[self.last] = item
        self.last += 1

    async def astart(self):
        count = 0
        for item in self.items:
            if item is not None:
                count += 1
                task = asyncio.create_task(item.run_in_background())
                self.running.append(task)
        print('   .. done, fired {} tasks'.format(count))
        await asyncio.sleep(0)
        # print('done waiting 0')
        # await asyncio.sleep(10)
        # print('done waiting 10')



    def remove(self, item):
        i = 0
        nn = 0
        while i < self.last:
            if self.items[i] is not None and self.items[i] != item:
                self.items[nn] = self.items[i]
                nn += 1
            i += 1
        self.last = nn
        item.active = False


schedule_list = ScheduleList()

_no_data = "const(0xaffedead)"

def stop():
    pass

async def arun():
    """Run forever"""
    asyncio.create_task(schedule_list.astart())
    await asyncio.sleep(0)
    while True:
        await asyncio.sleep(60)

def run():
    """Run forever"""
    asyncio.run(arun())

def run_in_ms(ms, label, callback, data=_no_data, repeat_ms=0):
    if isinstance(callback, ScheduledItem):
        item = callback
    elif data == _no_data:
        item = ScheduledItemWithCallback(label, callback)
    else:
        item = ScheduledItemWithData(label, callback, data)
    if repeat_ms is not None and repeat_ms > 0:
        item.repeat_ms = repeat_ms
    item.sleep_before_ms = ms
    schedule_list.append(item)
    return item
