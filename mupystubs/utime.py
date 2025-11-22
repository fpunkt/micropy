"""
Prototypes for utime package
"""

def ticks_ms():
    """Return integer ticks in ms"""

def ticks_diff(now: int, previous: int) -> int:
    """Calculate difference of ticks (handles integer overflow correctly"""
    return 0

def sleep(seconds: int) -> None:
    """Sleep for given number of seconds"""
