import time

import pytest
from kedixa.comm import *

BUF_SIZE = 4 * 1024 * 1024
BUF = bytearray([i%256 for i in range(BUF_SIZE)])

def abs(f: float):
    return f if f >= 0.0 else -f

@pytest.mark.asyncio
async def test_speed_limit():
    lo = LoopbackAdaptor(maxsize=BUF_SIZE+1)
    sl = SpeedLimitTransformer(w_mbytes=16, r_mbytes=8)
    sl.bind_next(lo)

    async with lo, sl as c:
        start = time.time()
        await c.write_all(BUF)
        await c.write_all(b'\n')
        cost = time.time() - start
        assert abs(cost-0.25) < 0.01

        start = time.time()
        data = b''
        nleft = BUF_SIZE
        while nleft > 0:
            d = await c.read(nleft)
            nleft -= len(d)
            data += d

        await c.read(1)
        cost = time.time() - start
        assert abs(cost-0.5) < 0.01

        assert BUF == data
