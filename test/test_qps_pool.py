import time

import pytest
from kedixa.qps_pool import QpsPool

def test_sync():
    pool = QpsPool(10)

    start = time.time()
    for _ in range(6):
        pool.sync_acquire()
    cost = time.time() - start
    assert 0.5 <= cost <= 0.55

@pytest.mark.asyncio
async def test_async():
    pool = QpsPool(10)

    start = time.time()
    for _ in range(6):
        await pool.acquire()
    cost = time.time() - start
    assert 0.5 <= cost <= 0.55
