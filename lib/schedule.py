"""
Scheduled tasks.
Callbacks are called async.

All scheduled tasks are callbacks are maintained in a list, they are not called concurrently.

Scheduled tasked can be used to poll sensors in a regular intervall or
to provide timeout for functions (moving motors to arrive) or add actions to motions sensors.

In principle sub-second resolution is possible (functions use milliseconds),
but don't expect too much accuracy.

"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments
# pylint: disable=too-few-public-methods

import gc
import sys
import utime
import board
import uasyncio as asyncio

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const


class ScheduledItem:
    """Basic item for the round robin scheduler. You must overload run() in your subclass"""
    def __init__(self, label, repeat_ms=0, first_run_after_ms=0):
        self.label = label
        self.repeat_ms = repeat_ms
        self.active = True
        self.next_run_ms = utime.ticks_add(utime.ticks_ms(), first_run_after_ms)
        schedule_list.append(self)

    def __repr__(self):
        return '<{}:{} active={}, poll interval={} ms, next in {} ms>'.format(
            self.__class__.__name__, self.label,
            self.active,
            self.repeat_ms,
            utime.ticks_diff(self.next_run_ms, utime.ticks_ms()))

    def run(self):
        pass

    def cancel(self):
        """dont run again"""
        self.active = False
        schedule_list.remove(self)

class ScheduledItemWithCallback(ScheduledItem):
    """Used to run simple callbacks w/o arguments.
Use like
    x = schedule.ScheduledItemWithCallback('myname', my_callback, repeat_ms=5000)
"""
    def __init__(self, label, callback, repeat_ms=0, first_run_after_ms=0):
        self.callback = callback
        super().__init__(label, repeat_ms, first_run_after_ms)

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
        self.items = list()
        self.next_run_in_ms = 0
        self.async_running_task = None
        self.background_tasks = []
        self.fired_background_tasks = False
        self.pollers = []

    def append(self, item):
        self.items.append(item)

    def remove(self, item):
        self.items.remove(item)

    def run_unlocked(self):
        """run all overdue items"""
        now = utime.ticks_ms()
        next_run_in_ms = 10000
        todelete = []
        fired = 0
        for item in self.items:
            # print('running {}'.format(item))
            if not item.active:
                continue
            d = utime.ticks_diff(item.next_run_ms, now)
            if d < 5:
                # this one is due
                try:
                    item.run()
                except Exception as e: # pylint: disable=broad-except
                    if board.DEBUG:
                        print("Error running {}: {}".format(item.label, e))
                fired += 1
                if item.repeat_ms == 0:
                    todelete.append(item)
                    continue
                # pylint: disable=line-too-long
                #print('{}: nr={}, repeat={} -> {}'.format(item.label, next_run_in_ms, item.repeat_ms, min(next_run_in_ms, item.repeat_ms)))
                next_run_in_ms = min(next_run_in_ms, item.repeat_ms)
                rn = utime.ticks_add(now, item.repeat_ms)
                item.next_run_ms = rn
        for item in todelete:
            self.items.remove(item)
        if fired == 0:
            # hm, nothing to do? This happens at startup
            # call earlier than required, otherwise the watch-dog gets fired
            next_run_in_ms = 100
        # print('Schedule list run, {} items fired, next in {} ms'.format(fired, next_run_in_ms))
        self.next_run_in_ms = next_run_in_ms

    # def run(self):
    #     self.run_unlocked()

    async def run_scheduled_tasks(self):
        while True:
            self.run_unlocked()
            mindelay_ms = const(50)
            if self.next_run_in_ms < mindelay_ms:
                print('ups, next run is {}'.format(self.next_run_in_ms))
                self.next_run_in_ms = mindelay_ms
            # pylint: disable=line-too-long
            # print('all tasks run, next schedule in {:.1f} seconds {} ms'.format(self.next_run_in_ms/1000.0, self.next_run_in_ms))
            await asyncio.sleep_ms(self.next_run_in_ms)

    async def run_pollers(self):
        active_pollers = False
        while True:
            active_pollers = False
            for p in self.pollers:
                try:
                    active_pollers |= p()
                except Exception as e: # pylint: disable=broad-except
                    if board.DEBUG:
                        print("Error running poller: {}".format(e))

            next_poll_in = 5
            #await asyncio.sleep(0)
            # pylint: disable=no-member
            if not active_pollers and gc.mem_free() < 6000:
                # print('running GC')
                gc.collect()
                next_poll_in = 0

            # give some time for WLAN stuff and friends
            await asyncio.sleep_ms(next_poll_in)

    async def run_forever(self):
        asyncio.create_task(self.run_scheduled_tasks())
        asyncio.create_task(self.run_pollers())
        for t in self.background_tasks:
            asyncio.create_task(t())
        await asyncio.sleep(0)
        while True:
            await asyncio.sleep(10)




schedule_list = ScheduleList()

def add_poller(item):
    schedule_list.pollers.append(item)

def add_task(item):
    schedule_list.background_tasks.append(item)


def stop():
    if schedule_list.async_running_task is not None:
        schedule_list.async_running_task.cancel()
    schedule_list.async_running_task = None


def _set_global_exception():
    def handle_exception(loop, context):
        # pylint: disable=no-member
        sys.print_exception(context["exception"])
        sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

def run_until_error():
    """Run forever"""
    try:
        asyncio.run(schedule_list.run_forever())
    except asyncio.TimeoutError:
        print('Got timeout error')
    except Exception as e: # pylint: disable=broad-except
        print('exception in run_until_error / run_forever', e)
        return e
    finally:
        asyncio.new_event_loop()  # Clear retained state
    print('UPPS, run terminated.')
    return None

def run():
    result = None
    while True:
        try:
            result = run_until_error()
        except Exception as e: # pylint: disable=broad-except
            print(e)
            raise
        print('run_until_error: {}'.format(result))
