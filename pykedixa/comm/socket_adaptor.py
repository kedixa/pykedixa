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
from .address import SocketAddress

__all__ = [
    'SyncTcpAdaptor',
    'TcpAdaptor',
]


class SyncTcpAdaptor(BasicAdaptor):
    def __init__(self, addr: SocketAddress):
        self._addr: SocketAddress = addr
        self._socket = socket.socket(addr.family, socket.SOCK_STREAM, addr.proto)

    async def prepare(self):
        self._socket.connect((self._addr.ip, self._addr.port))

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
    def __init__(self, addr: SocketAddress, *,
            reader: asyncio.StreamReader = None,
            writer: asyncio.StreamWriter = None,
            close_on_finish: bool = True):
        '''
        If both reader and writer is not None,
        adaptor will use them without create a new one;
        and they will be closed when self.finish if close_on_finish.
        '''
        self._addr: SocketAddress = addr

        self._server_side: bool
        self._close_on_finish: bool = close_on_finish
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer

        if reader is not None and writer is not None:
            self._server_side = True
        else:
            assert reader is None and writer is None
            self._server_side = False

    @property
    def addr(self) -> SocketAddress:
        return self._addr

    async def prepare(self):
        if not self._server_side:
            addr = self._addr
            self._reader, self._writer = await asyncio.open_connection(
                host=addr.ip, port=addr.port, family=addr.family,
                proto=addr.proto
            )

    async def finish(self):
        if self._server_side and not self._close_on_finish:
            return

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
