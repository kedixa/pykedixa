import socket

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
