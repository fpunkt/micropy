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

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    # pylint: disable=used-before-assignment, undefined-variable, self-assigning-variable
    const = const


class OutOfIRQRunnerClass:
    def __init__(self):
        self.stack = [None, None, None, None, None]
        self.scheduled = False
        self._run_ref = self._runlist

    def _runlist(self, _):
        # print('Running {}'.format(self.stack))
        i = 0
        l = []
        irq_state = machine.disable_irq()

        # keep blocked IRQ as short as possible
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

    def run_outside_irq(self, callback):
        i = 0
        irq_state = machine.disable_irq()
        while i < len(self.stack):
            if self.stack[i] is None:
                self.stack[i] = callback
                break
            i += 1
        if not self.scheduled:
            self.scheduled = True
            micropython.schedule(self._run_ref, None)
        machine.enable_irq(irq_state)


outside_irq = OutOfIRQRunnerClass()


# schedule_1_minute = const(1 * 60 * 1000)
# schedule_5_minutes = const(5 * 60 * 1000)

class ScheduledItem:
    def __init__(self):
        self.next_run_ticks = 0
        self.repeat_ms = 0

    def __repr__(self):
        return '<{} poll interval={} ms, next in {} ms>'.format(
            self.__class__.__name__,
            self.repeat_ms,
            utime.ticks_diff(self.next_run_ticks, utime.ticks_ms()))

    def run(self):
        pass

    def cancel(self):
        """dont run again"""
        schedule_list.remove(self)

class ScheduledItemWithCallback(ScheduledItem):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def run(self):
        if self.callback is not None:
            self.callback()

    def cancel(self):
        self.repeat_ms = 0
        self.callback = None

class ScheduledItemWithData(ScheduledItemWithCallback):
    def __init__(self, callback, data):
        super().__init__(callback)
        self.data = data

    def run(self):
        if self.callback is not None:
            self.callback(self.data)

class ScheduleList:
    """A list of all scheduled items"""
    def __init__(self):
        # use a pre-alloced list to avoid GC
        self.items = [None, None, None, None, None, None, None, None, None, None]
        self.last = 0
        # self.next_run_ticks = 0
        self._irq_ref = self._irq_handler
        self._run_ref = self.run_outside_isr
        self.timer = machine.Timer(2)
        self.stopped = False

    def append(self, item):
        if self.last >= len(self.items):
            self.items.append(item)
        else:
            self.items[self.last] = item
        self.last += 1

        # print('Added item {}, last={} -> {}'.format(item, self.last, self.items))

        #if utime.tiks_diff(self.next_run_ticks, item.next_run_ticks) < 0:
            # start now
        self.run_outside_isr(None)

    def run_outside_isr(self, _):
        # print('running schedule outside ISR with {} items, seconds: {}'.format(self.last, utime.time()))
        if self.stopped:
            return

        # don't block dimming, doesn't look nice ...
        if pwm.dimlist.isdimming:
            self.timer.init(period=200, mode=machine.Timer.ONE_SHOT, callback=self._irq_ref)

        i = 0
        not_none = 0 # used to compress list on the fly

        now = utime.ticks_ms()
        next_run = utime.ticks_add(now, 25000) # if there is nothing else to do ...

        while i < self.last:
            item = self.items[i]
            # print('checking item {}: {}'.format(i, item))
            i += 1

            if item is None:
                print('huh? item is None')
                continue

            # pylint: disable=line-too-long
            #print('now={}, next={}, diff={}'.format(now, item.next_run_ticks, utime.ticks_diff(item.next_run_ticks, now)))
            #print('i={}, lasti={}, last_none={}, item={}'.format(i, lasti, last_none, item))
            # we leave some margin here not to fiere the timer again immediately
            if utime.ticks_diff(item.next_run_ticks, now) < 5:
                try:
                    # print('going to run callback')
                    item.run()
                except: # pylint: disable=bare-except
                    pass

                if item.repeat_ms == 0:
                    # run and done
                    continue

                # schedule next run
                # we could use item.next_run_ticks -> overall error remains smaller, jitter is larger
                # or use 'now'
                # reference_time = item.next_run_ticks
                item.next_run_ticks = utime.ticks_add(now, item.repeat_ms)

            self.items[not_none] = item
            not_none += 1

            if utime.ticks_diff(item.next_run_ticks, next_run) < 0:
                next_run = item.next_run_ticks
                # print('set next run to', next_run)

        # here we have run all overdue entries. Cleanup list if needed

        # print('All callbacks done, nn={}'.format(not_none))
        self.last = not_none

        # schedule next run
        next_in = utime.ticks_diff(next_run, now)
        self.timer.init(period=next_in, mode=machine.Timer.ONE_SHOT, callback=self._irq_ref)

    def remove(self, item):
        i = 0
        nn = 0
        while i < self.last:
            if self.items[i] is not None and self.items[i] != item:
                self.items[nn] = self.items[i]
                nn += 1
            i += 1
        self.last = nn

    def _irq_handler(self, _):
        outside_irq.run_outside_irq(self._run_ref)


schedule_list = ScheduleList()

_no_data = "const(0xaffedead)"

def stop():
    schedule_list.stopped = True

def run():
    schedule_list.stopped = False
    schedule_list.run_outside_isr(None)

def reschedule(self):
    """Run if something in the to-be-run list changed"""
    run()

def run_in_ms(ms, callback, data=_no_data, repeat_ms=0):
    if isinstance(callback, ScheduledItem):
        item = callback
    elif data == _no_data:
        item = ScheduledItemWithCallback(callback)
    else:
        item = ScheduledItemWithData(callback, data)
    if repeat_ms is not None and repeat_ms > 0:
        item.repeat_ms = repeat_ms
    item.next_run_ticks = utime.ticks_add(utime.ticks_ms(), ms)
    # print('new item callback scheduled for', item.next_run_ticks)
    schedule_list.append(item)
    return item
