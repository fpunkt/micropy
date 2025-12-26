"""
Print memory usage statistics.
"""

import gc
import board


def print_stats():
    free_before = gc.mem_free()
    alloc_before = gc.mem_alloc()
    gc.collect()
    free_after = gc.mem_free()
    alloc_after = gc.mem_alloc()
    freed = free_after - free_before
    allocated = alloc_after - alloc_before
    board.MQTT_PUBLISH("info/mem", "free_before: {} alloc_before: {} free_after: {} alloc_after: {}, freed: {}, allocated: {}".format(
        free_before, alloc_before, free_after, alloc_after, freed, allocated))
    board.PRINTF("free_before: {} alloc_before: {} free_after: {} alloc_after: {}".format(
        free_before, alloc_before, free_after, alloc_after))
    board.PRINTF("gc.collect() freed {} bytes", freed)
    board.PRINTF("gc.collect() allocated {} bytes", allocated)
