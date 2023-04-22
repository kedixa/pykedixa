from typing import Union

from .import (
    CommunicateBase,
    Connection,
)
from .exception import (
    AdaptorEofError,
    TransformerEofError,
)

__all__ = [
    'CommBridge',
]


class CommBridge:
    def __init__(self,
            read_from: Union[CommunicateBase, Connection],
            write_to: Union[CommunicateBase, Connection],
            *,
            max_bytes: int = -1, max_per_read: int = 65536):
        if isinstance(read_from, Connection):
            read_from = read_from.c
        if isinstance(write_to, Connection):
            write_to = write_to.c

        self._from: CommunicateBase = read_from
        self._to: CommunicateBase   = write_to
        self._total_read: int       = 0
        self._max_bytes: int        = max_bytes
        self._max_per_read: int     = max_per_read
        self._stop: bool            = False

    def _next_read_size(self) -> int:
        if self._max_bytes < 0:
            return self._max_per_read

        nleft = self._max_bytes - self._total_read
        return min(nleft, self._max_per_read)

    def stop(self):
        self._stop = True

    async def run(self):
        rlen: int       = self._next_read_size()
        buf: bytearray  = bytearray(rlen)
        buflen: int     = len(buf)

        while rlen > 0 and not self._stop:
            if rlen > buflen:
                buf.extend(bytearray(rlen - buflen))
                buflen = rlen

            try:
                nread: int = await self._from.read(rlen, buffer=buf)
            except (AdaptorEofError, TransformerEofError):
                break

            with memoryview(buf) as view:
                await self._to.write_all(view[:nread], flush=False)

            self._total_read += nread
            rlen = self._next_read_size()
