from .basic import (
    BasicTransformer,
    CommFlags,

    WritableBuffer,
    ReadableBuffer,
    ReadRetType,
)
from .exception import (
    TransformerException,
    BadMessage,
)

__all__ = ['ReadUntilTransformer']


class ReadUntilTransformer(BasicTransformer):
    SUPPORTED_FLAGS = BasicTransformer.SUPPORTED_FLAGS | CommFlags.READ_UNTIL

    def __init__(self):
        super().__init__()
        self._data: bytearray = bytearray()

    async def finish(self):
        if self._data:
            raise TransformerException('BadTransformerState: data is not empty when finish', self._data)

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        dlen = len(self._data)

        if dlen > 0:
            if max_bytes < 0 or max_bytes >= dlen:
                data, self._data = self._data, bytearray()
            else:
                data = self._data[:max_bytes]
                del self._data[:max_bytes]
                dlen = max_bytes

            if buffer is None:
                return data
            else:
                buffer[:len(data)] = data
                return dlen
        else:
            return await self._nxt.read(max_bytes, buffer=buffer)

    async def read_until(self, delimiter: bytes, max_bytes: int = -1) -> ReadableBuffer:
        end_pos = self._data.find(delimiter)
        end_len = len(delimiter)

        while end_pos < 0:
            old_len = len(self._data)
            if max_bytes >= 0 and old_len > max_bytes:
                raise BadMessage(f'DelimiterNotFound: max_bytes:{max_bytes}')

            mbytes = max_bytes if max_bytes < 0 else max_bytes - old_len
            self._data.extend(await self._nxt.read(mbytes))

            last_pos = max(0, old_len - end_len)
            end_pos = self._data.find(delimiter, last_pos)

        end_pos += end_len
        data = self._data[:end_pos]
        del self._data[:end_pos]
        return data
