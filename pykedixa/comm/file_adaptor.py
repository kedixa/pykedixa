import io

from .basic import (
    AdaptorEofError,
    BasicAdaptor,

    ReadableBuffer,
    ReadRetType,
    WritableBuffer,
)

__all__ = [
    'FileAdaptor',
]


class FileAdaptor(BasicAdaptor):
    def __init__(self, filepath: str, mode: str = 'rb'):
        self._filepath: str = filepath
        self._mode: str     = mode
        self._file: io.RawIOBase = None

    async def prepare(self):
        self._file = open(self._filepath, self._mode)

    async def finish(self):
        self._file.close()

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        if buffer:
            if max_bytes < 0:
                max_bytes = len(buffer)

            with memoryview(buffer) as view:
                ret = self._file.readinto(view[:max_bytes])

            if ret == 0:
                raise AdaptorEofError('FileAdaptorEof')
        else:
            ret = self._file.read(max_bytes)
            if len(ret) == 0:
                raise AdaptorEofError('FileAdaptorEof')

        return ret

    async def write(self, buffer: ReadableBuffer) -> int:
        return self._file.write(buffer)

