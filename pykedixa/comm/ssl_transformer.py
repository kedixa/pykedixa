import ssl
# import logging

from .basic import (
    BasicTransformer,
    ReadableBuffer,
    ReadRetType,
    WritableBuffer,
    DEFAULT_MAX_READ_SIZE,
)

from .exception import (
    TransformerEofError,
)

__all__ = [
    'SslTransformer',
]

# _logger = logging.getLogger('kedixa.comm')


class SslTransformer(BasicTransformer):
    def __init__(self, ssl_ctx: ssl.SSLContext, server_hostname=None):
        self._ssl_ctx: ssl.SSLContext   = ssl_ctx
        self._server_hostname: str      = server_hostname
        self._in: ssl.MemoryBIO         = ssl.MemoryBIO()
        self._out: ssl.MemoryBIO        = ssl.MemoryBIO()
        self._ssl_obj: ssl.SSLObject    = None

    async def _do_want_read(self):
        if self._out.pending > 0:
            data = self._out.read()
            await self._nxt.write_all(data)

        data = await self._nxt.read(-1)
        self._in.write(data)

    async def _do_want_write(self):
        if self._out.pending > 0:
            await self._nxt.write_all(self._out.read())

    async def prepare(self):
        self._ssl_obj = self._ssl_ctx.wrap_bio(self._in, self._out,
            server_hostname=self._server_hostname)

        while True:
            try:
                self._ssl_obj.do_handshake()
            except ssl.SSLWantReadError:
                await self._do_want_read()
            except ssl.SSLWantWriteError:
                await self._do_want_write()
            else:
                break
        await self._do_want_write()

    async def read(self, max_bytes: int = -1, *,
            buffer: WritableBuffer = None) -> ReadRetType:
        if max_bytes < 0:
            max_bytes = DEFAULT_MAX_READ_SIZE

        ret = None

        while True:
            try:
                ret = self._ssl_obj.read(max_bytes, buffer)
            except ssl.SSLWantReadError:
                await self._do_want_read()
            except ssl.SSLWantWriteError:
                await self._do_want_write()
            else:
                break

        await self._do_want_write()

        if not ret:
            # the ssl is shutdown by remote
            raise TransformerEofError('SslTransformerEof')
        return ret

    async def write(self, buffer: ReadableBuffer) -> int:
        wsz = self._ssl_obj.write(buffer)
        await self._do_want_write()
        return wsz
