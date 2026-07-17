"""
#52 Random Delays
Wait 5-20 seconds between each business to avoid detection.
"""

import asyncio
import random
import time
from typing import Dict


class RandomDelays:
    """Manages random delays between requests."""

    def __init__(self, min_delay: float = 5.0, max_delay: float = 20.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.total_delays = 0
        self.total_wait_time = 0.0
        self.last_delay = 0.0

    async def wait(self, custom_min: float = None, custom_max: float = None):
        """Wait a random amount of time."""
        mn = custom_min or self.min_delay
        mx = custom_max or self.max_delay
        delay = random.uniform(mn, mx)

        jitter = random.uniform(-0.5, 0.5)
        delay = max(0.1, delay + jitter)

        await asyncio.sleep(delay)

        self.total_delays += 1
        self.total_wait_time += delay
        self.last_delay = delay
        return delay

    async def wait_before_search(self):
        """Wait before a search query."""
        delay = random.uniform(3.0, 8.0)
        await asyncio.sleep(delay)
        self.total_delays += 1
        self.total_wait_time += delay
        return delay

    async def wait_after_search(self):
        """Wait after a search query."""
        delay = random.uniform(5.0, 15.0)
        await asyncio.sleep(delay)
        self.total_delays += 1
        self.total_wait_time += delay
        return delay

    async def wait_between_pages(self):
        """Wait between page navigations."""
        delay = random.uniform(2.0, 6.0)
        await asyncio.sleep(delay)
        self.total_delays += 1
        self.total_wait_time += delay
        return delay

    def wait_sync(self, min_sec: float = None, max_sec: float = None):
        """Synchronous wait (for non-async contexts)."""
        mn = min_sec or self.min_delay
        mx = max_sec or self.max_delay
        delay = random.uniform(mn, mx)
        time.sleep(delay)
        self.total_delays += 1
        self.total_wait_time += delay
        self.last_delay = delay
        return delay

    def get_stats(self) -> Dict:
        """Get delay statistics."""
        return {
            "total_delays": self.total_delays,
            "total_wait_seconds": round(self.total_wait_time, 1),
            "avg_delay": round(self.total_wait_time / max(self.total_delays, 1), 1),
            "last_delay": round(self.last_delay, 1),
            "config": {"min": self.min_delay, "max": self.max_delay},
        }


if __name__ == "__main__":
    rd = RandomDelays()
    for _ in range(5):
        d = rd.wait_sync(0.1, 0.3)
        print(f"  Waited: {d:.1f}s")
    print(f"Stats: {rd.get_stats()}")
