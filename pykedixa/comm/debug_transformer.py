import logging
from .basic import (
    BasicTransformer,
    ReadableBuffer,
    WritableBuffer,
    ReadRetType,
)

_logger = logging.getLogger('kedixa.comm.debug_transformer')
__all__ = [
    'DebugTransformer',
]


class DebugTransformer(BasicTransformer):
    def __init__(self, size_limit: int = 128, logger: logging.Logger = _logger):
        super().__init__()
        self._limit: int = size_limit
        self._logger: logging.Logger = logger

    async def write(self, buffer: ReadableBuffer) -> int:
        ret = await self._nxt.write(buffer)
        x = min(ret, self._limit)
        self._logger.debug('write len:%d data:%s', ret, buffer[:x])
        return ret

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        ret = await self._nxt.read(max_bytes, buffer=buffer)

        if buffer is None:
            buf, rlen = ret, len(ret)
        else:
            buf, rlen = buffer, ret

        x = min(rlen, self._limit)
        self._logger.debug('read len:%d data:%s', rlen, buf[:x])
        return ret

    async def flush(self):
        ret = await self._nxt.flush()
        self._logger.debug(f'flush ret:{ret}')
        return ret
