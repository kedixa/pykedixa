import asyncio
import socket

from .. import compat

from .basic import (
    AdaptorEofError,
    BasicAdaptor,

    ReadableBuffer,
    ReadRetType,
    WritableBuffer,
    DEFAULT_MAX_READ_SIZE,
)

__all__ = [
    'SyncTcpAdaptor',
    'TcpAdaptor',
]


class SyncTcpAdaptor(BasicAdaptor):
    def __init__(self, addr, *, family=socket.AF_INET, proto=0):
        self._addr = addr
        self._socket = socket.socket(family, socket.SOCK_STREAM, proto)

    async def prepare(self):
        self._socket.connect(self._addr)

    async def finish(self):
        self._socket.close()

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        if max_bytes < 0:
            max_bytes = DEFAULT_MAX_READ_SIZE

        if buffer:
            ret = self._socket.recv_into(buffer, max_bytes)
            if ret == 0:
                raise AdaptorEofError('SyncTcpAdaptor: connection closed')
        else:
            ret = self._socket.recv(max_bytes)
            if len(ret) == 0:
                raise AdaptorEofError('SyncTcpAdaptor: connection closed')

        return ret

    async def write(self, buffer: ReadableBuffer) -> int:
        return self._socket.send(buffer)

class TcpAdaptor(BasicAdaptor):
    def __init__(self, addr, *, family=socket.AF_INET, proto=0):
        self._addr          = addr
        self._family: int   = family
        self._proto: int    = proto
        self._reader: asyncio.StreamReader = None
        self._writer: asyncio.StreamWriter = None

    async def prepare(self):
        addr = self._addr
        self._reader, self._writer = await asyncio.open_connection(
            host=addr[0], port=addr[1], family=self._family,
            proto=self._proto
        )

    async def finish(self):
        if self._writer.can_write_eof():
            self._writer.write_eof()

        self._writer.close()

        if compat.PY37:
            await self._writer.wait_closed()

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        if max_bytes < 0:
            max_bytes = DEFAULT_MAX_READ_SIZE

        data = await self._reader.read(max_bytes)

        if not data:
            raise AdaptorEofError('TcpAdaptorEof')

        if buffer:
            dlen = len(data)
            buffer[:dlen] = data
            return dlen
        else:
            return data

    async def write(self, buffer: ReadableBuffer) -> int:
        blen = len(buffer)

        self._writer.write(buffer)
        return blen

    async def flush(self):
        await self._writer.drain()
