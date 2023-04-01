from ..basic import (
    BasicFilter,

    WritableBuffer,
    ReadableBuffer,
    ReadRetType,
)
from ..exception import (
    BadMessage,
    FilterEofError,
)
from ..read_until_filter import ReadUntilFilter

__all__ = ['HttpChunkFilter']

class HttpChunkFilter(BasicFilter):
    def __init__(self):
        self._buf: bytearray    = bytearray()
        self._buflen: int       = 0

    async def _next_chunk(self):
        line_end = b'\r\n'
        end_len = len(line_end)
        r: ReadUntilFilter = self._nxt

        data: bytes = await r.read_until(line_end)
        data = data[:-2]

        try:
            chunk_len = int(data, 16)
        except ValueError:
            raise BadMessage(f'BadChunk: chunk length {data} isn\'t hex format')

        if chunk_len > 0:
            self._buf.extend(await r.read_exactly(chunk_len))
            self._buflen = len(self._buf)

        eol = await r.read_exactly(end_len)
        if eol != line_end:
            raise BadMessage(f'BadHttpMessage: chunk end with {eol}')

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        if self._buflen == 0:
            await self._next_chunk()
            if self._buflen == 0:
                raise FilterEofError('HttpChunkFilterEof')

        if max_bytes < 0 or self._buflen <= max_bytes:
            nread = self._buflen
        else:
            nread = max_bytes

        buf = bytearray(nread) if buffer is None else buffer
        buf[:nread] = self._buf[:nread]
        del self._buf[:nread]
        self._buflen -= nread
        return buf if buffer is None else nread

    async def write(self, buffer: ReadableBuffer) -> int:
        blen = len(buffer)
        buf = bytearray(str(blen).encode())
        buf.extend(b'\r\n')
        buf.extend(buffer)
        buf.extend(b'\r\n')
        await self._nxt.write_all(buf)

    async def flush(self):
        await self._nxt.write(b'0\r\n\r\n')
        await self._nxt.flush()
