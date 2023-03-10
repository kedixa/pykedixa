import enum
from typing import Union, List

__all__ = [
    'CommFlags',
    'CommException',
    'AdaptorException',
    'AdaptorEofError',
    'FilterException',
    'BadMessage',

    'CommunicateBase',
    'MessageBase',
    'BasicAdaptor',
    'BasicFilter',
    'ReadUntilFilter',
    'LoopbackAdaptor',

    'ReadableBuffer',
    'WritableBuffer',
    'ReadRetType',
    'DEFAULT_MAX_READ_SIZE',
]

ReadableBuffer = Union[bytes, bytearray, memoryview]
WritableBuffer = Union[bytearray, memoryview]
ReadRetType    = Union[ReadableBuffer, int]


DEFAULT_MAX_READ_SIZE: int = 2 ** 24
DEFAULT_LOOPBACK_ADAPTOR_MEMSIZE: int = 2 ** 24


class CommFlags(enum.IntFlag):
    # Support self.read_until, for example ReadUntilFilter
    READ_UNTIL      = 1


class CommException(Exception):
    def __init__(self, what: str, *args):
        self._what: str = what
        self._args      = args

    def __str__(self) -> str:
        return f'{self._what} args:{self._args}'

    def what(self) -> str:
        return self._what


class AdaptorException(CommException):
    pass


class AdaptorEofError(AdaptorException):
    pass


class FilterException(CommException):
    pass


class BadMessage(CommException):
    pass


class CommunicateBase:
    SUPPORTED_FLAGS = 0

    def support_flags(self, flags: int) -> bool:
        '''return True if all the flags are supported by this object'''
        return flags & self.SUPPORTED_FLAGS == flags

    async def __aenter__(self):
        await self.prepare()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.finish()

    async def prepare(self):
        '''Call prepare before use of read/write'''
        pass

    async def finish(self):
        '''Call finish after use of read/write'''
        pass

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        '''
        Read up to max_bytes from this object.
        when buffer is not None,
        read into buffer,
        return int which means the number of bytes;
        else return a copy of data.
        '''
        raise NotImplementedError

    async def read_exactly(self, nbytes: int, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        '''
        Read nbytes exactly from this object.
        when buffer is not None,
        read into buffer and return nbytes,
        else return a copy of data.
        '''
        buf: WritableBuffer = bytearray(nbytes) if buffer is None else buffer
        pos = 0

        with memoryview(buf) as view:
            while pos < nbytes:
                rlen = await self.read(nbytes-pos, buffer=view[pos:nbytes])
                pos += rlen
                assert rlen > 0

        assert pos == nbytes

        return buf if buffer is None else nbytes

    async def write(self, buffer: ReadableBuffer) -> int:
        '''Write data into this object, return the number of bytes write.'''
        raise NotImplementedError

    async def write_all(self, buffer: ReadableBuffer, *, flush=True) -> int:
        '''
        Write all data in buffer into this object,
        return the number of bytes write.
        if flush is True, call self.flush after all write done.
        '''
        tot = len(buffer)
        pos = 0

        with memoryview(buffer) as m:
            while pos < tot:
                wlen = await self.write(m[pos:])
                pos += wlen
                assert wlen  > 0

        if flush:
            await self.flush()
        return tot

    async def flush(self):
        pass


class MessageBase:
    async def encode(self, c: CommunicateBase):
        raise NotImplementedError

    async def decode(self, c: CommunicateBase):
        raise NotImplementedError

    def copy(self) -> 'MessageBase':
        raise NotImplementedError


class BasicAdaptor(CommunicateBase):
    pass


class BasicFilter(CommunicateBase):
    def __init__(self):
        super().__init__()
        self._nxt: CommunicateBase = None

    def bind_next(self, nxt: Union[BasicAdaptor, 'BasicFilter']):
        self._nxt = nxt
        return self

    def prepare_only(self) -> bool:
        '''Whether the filter only need to call prepare'''
        return False

    async def write(self, buffer: ReadableBuffer) -> int:
        return await self._nxt.write(buffer)

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        return await self._nxt.read(max_bytes, buffer=buffer)

    async def flush(self):
        return await self._nxt.flush()


class ReadUntilFilter(BasicFilter):
    SUPPORTED_FLAGS = BasicFilter.SUPPORTED_FLAGS | CommFlags.READ_UNTIL

    def __init__(self):
        super().__init__()
        self._data: bytearray = bytearray()

    async def finish(self):
        if self._data:
            raise FilterException('BadFilterState: data is not empty when finish', self._data)

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


class LoopbackAdaptor(BasicAdaptor):
    def __init__(self, maxsize: int = DEFAULT_LOOPBACK_ADAPTOR_MEMSIZE):
        super().__init__()
        self._lst: List[ReadableBuffer] = []
        self._size: int = 0
        self._maxsize: int = maxsize

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        if max_bytes < 0 or max_bytes > self._size:
            max_bytes = self._size

        if self._size == 0:
            raise AdaptorEofError('LoopbackAdaptor: no more data')

        buf = bytearray(max_bytes) if buffer is None else buffer
        pos = 0

        for i in range(len(self._lst)):
            data = self._lst[i]
            dlen = len(data)

            # < rather than <=, make sure the last read always
            # run into else
            if dlen + pos < max_bytes:
                buf[pos:pos+dlen] = data
                pos += dlen
            else:
                n = max_bytes - pos
                buf[pos:pos+n] = data[:n]
                if n == dlen:
                    self._lst = self._lst[i+1:]
                else:
                    self._lst[i] = data[n:]
                    self._lst = self._lst[i:]
                break

        self._size -= max_bytes
        return buf if buffer is None else max_bytes

    async def write(self, buffer: ReadableBuffer) -> int:
        if self._size >= self._maxsize:
            raise AdaptorException('LoopbackAdaptor: memory limit exceeded',
                                   self._maxsize)

        tot = len(buffer)

        if self._size + tot > self._maxsize:
            tot = self._maxsize - self._size
            buffer = buffer[:tot]

        self._lst.append(buffer)
        self._size += tot

        return tot


class StrHelper:
    def __init__(self, indent: int = 2, level: int = 0):
        self._indent: int = indent
        self._level: int  = level
        self._str_lst: List[str] = []
        self._indent_str: str = str()

        self.change_level(0)

    def __enter__(self):
        self.change_level(1)

    def __exit__(self, exc_type, exc_value, traceback):
        self.change_level(-1)

    def change_level(self, x: int):
        self._level += x
        self._indent_str = ' ' * (self._indent * self._level)

    def append(self, s: str):
        self._str_lst.append(self._indent_str + s)

    def join(self, sep: str = '\n') -> str:
        return sep.join(self._str_lst)

