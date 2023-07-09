import asyncio
import time

class QpsPool:
    def __init__(self, limit: int = 0):
        self._limit: int = limit
        self._interval: float = 0
        self._last: float = 0.0

        if limit > 0:
            self._interval = 1.0 / limit

    async def acquire(self, n: int = 1):
        wait_sec = self._get_wait_sec(n)
        await asyncio.sleep(wait_sec)

    def sync_acquire(self, n: int = 1):
        wait_sec = self._get_wait_sec(n)
        time.sleep(wait_sec)

    def _get_wait_sec(self, n: int) -> float:
        current = time.monotonic()
        next = self._last + n * self._interval
        if next >= current:
            self._last = next
            return next - current
        else:
            self._last = current
            return 0.0
