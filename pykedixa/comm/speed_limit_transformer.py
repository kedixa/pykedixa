import asyncio
import time
import math

from .basic import (
    BasicTransformer,

    ReadableBuffer,
    WritableBuffer,
    ReadRetType,
)
from .exception import (
    AdaptorEofError,
)

__all__ = [
    'SpeedLimitTransformer',
]


DEFAULT_WRITE_SPEED     = 256.0 * 1024
DEFAULT_READ_SPEED      = 256.0 * 1024
SPEED_LIMIT_MAX_HINT    = 16 * 1024 * 1204


def _get_bps(b: float, kb: float, mb: float, dft: float) -> float:
    bps = None
    if b:
        bps = float(b)
    elif kb:
        bps = float(kb) * 1024
    elif mb:
        bps = float(mb) * 1024 * 1024
    else:
        bps = dft
    return bps if bps >= 1.0 else 1.0


def _get_hint(bps: float) -> int:
    hint = bps / 8.0
    hint = math.log2(hint)
    hint = 2 ** int(hint)
    if hint > SPEED_LIMIT_MAX_HINT:
        hint = SPEED_LIMIT_MAX_HINT
    return hint


class SpeedLimitTransformer(BasicTransformer):
    def __init__(self, *,
            r_bytes: float = None, r_kbytes: float = None, r_mbytes: float = None,
            w_bytes: float = None, w_kbytes: float = None, w_mbytes: float = None):
        '''
        Set atmost one of r_(bytes/kbytes/mbytes),
        indicate how many bytes to read per second,
        if none of them is set, the default value DEFAULT_READ_SPEED is used.
        It is the same for w_(bytes/kbytes/mbytes),
        if none of them is set, the default value DEFAULT_WRITE_SPEED is used.
        '''
        super().__init__()

        self._rnext: float = 0.0
        self._rbps:  float = _get_bps(r_bytes, r_kbytes, r_mbytes, DEFAULT_READ_SPEED)
        self._rhint: int   = _get_hint(self._rbps)

        self._wnext: float = 0.0
        self._wbps:  float = _get_bps(w_bytes, w_kbytes, w_mbytes, DEFAULT_WRITE_SPEED)
        self._whint: int   = _get_hint(self._wbps)

    async def write(self, buffer: ReadableBuffer) -> int:
        blen = len(buffer)
        pos, iter = 0, 0

        with memoryview(buffer) as view:
            # try max 10 iter
            while iter < 10 and pos < blen:
                iter += 1

                cur = time.monotonic()
                delay = self._wnext - cur
                if delay > 0.0:
                    await asyncio.sleep(delay)
                else:
                    self._wnext = cur

                wmax = min(self._whint, blen-pos)
                wlen = await self._nxt.write(view[pos:pos+wmax])

                pos += wlen
                self._wnext += float(wlen) / self._wbps

        return pos

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        if max_bytes < 0:
            max_bytes = self._rhint * 10

        pos, iter = 0, 0
        buf = bytearray(max_bytes) if buffer is None else buffer

        with memoryview(buf) as view:
            while iter < 10 and pos < max_bytes:
                iter += 1

                cur = time.monotonic()
                delay = self._rnext - cur
                if delay > 0.0:
                    await asyncio.sleep(delay)
                else:
                    self._rnext = cur

                rmax = min(self._rhint, max_bytes-pos)

                try:
                    rlen = await self._nxt.read(rmax, buffer=view[pos:pos+rmax])
                except AdaptorEofError:
                    if pos == 0:
                        raise
                    break

                pos += rlen
                self._rnext += float(rlen) / self._rbps

        return buf[:pos] if buffer is None else pos
