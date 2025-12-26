from machine import WDT
import board
import asyncio


def start_later(seconds=120, timeout=5000, interval=4000):
    """Start watchdog after given seconds with given timeout and interval in ms.
    """
    asyncio.create_task(_start_after_seconds(seconds, timeout, interval))


def start(timeout=5000, interval=4000):
    """Start watchdog with given timeout and interval in ms. Interval is the time between feed() calls.
    If interval is None or 0, the feed() function will not automatically be called in a separate task.

    Note: your main-app should probably not call start() but instead start via CAN or MQTT or 
    a few minutes after reboot. This is to avoid false positives and gives the app time to initialize 
    or allow to connect via a terminal or repl for debugging.
    """
    if board.WDT is None:
        board.WDT = WDT(timeout=timeout)
        board.WDT.feed()
        if interval is not None and interval > 0:
            asyncio.create_task(feed(interval))
            board.MQTT_PUBLISH("info", "watchdog enabled")

async def feed(interval=4000):
    """Feed the watchdog with the given interval in ms."""
    while True:
        board.WDT.feed()
        await asyncio.sleep_ms(interval)

async def _start_after_seconds(seconds=120, timeout=5000, interval=4000):
    await asyncio.sleep(seconds)
    start(timeout, interval)


