import asyncio
import random
import ssl
from urllib.parse import urlparse
from typing import (
    List,
    Tuple,
)

from .. import (
    Connection,
    TcpAdaptor,
    SslTransformer,
    ReadUntilTransformer,

    CommException,

    getaddrinfo,
)
from .websocket_message import (
    WebSocketFrame,
    WebSocketOpcode,
)
from .websocket_upgrader import WebSocketUpgrader

__all__ = [
    'WebSocketProcessor',
    'WebSocketClient',
    'WebSocketService',
]

def _ws_parse_url(url: str):
    u = urlparse(url)
    scheme = u.scheme.lower()
    assert scheme in ['ws', 'wss']

    host, port = u.hostname, u.port
    assert host is not None

    if port is None:
        if scheme == 'wss':
            port = 443
        else:
            port = 80

    req_url: str = '/' if len(u.path) == 0 else u.path
    if len(u.query) > 0:
        req_url += '?' + u.query

    return scheme, host, port, req_url


class WebSocketHandlerBase:
    async def on_frame(self, cli: 'WebSocketProcessor', frame: WebSocketFrame):
        pass


class WebSocketProcessorError(CommException):
    pass


class WebSocketProcessor:
    def __init__(self, *,
            frame_handler: WebSocketHandlerBase):
        self._hdl: WebSocketHandlerBase = frame_handler

        if self._hdl is None:
            self._hdl = WebSocketHandlerBase()

        self._conn: Connection = None
        self._closed: bool = True
        self._recv_task: asyncio.Task = None
        self._context = None
        self._lock = asyncio.Lock()

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, context):
        self._context = context

    async def start_with_conn(self, conn: Connection):
        self._conn = conn
        proc = self._process_msg()
        self._recv_task = asyncio.ensure_future(proc)

    async def _close(self,
            conn: Connection,
            recv_task: asyncio.Task):
        if recv_task:
            recv_task.cancel()
        if conn:
            await conn.close()

    async def close(self):
        if not self._closed:
            self._closed = True

            conn, recv_task = self._conn, self._recv_task
            self._conn, self._recv_task = None, None
            asyncio.ensure_future(self._close(conn, recv_task))

    def closed(self) -> bool:
        return self._closed

    async def _process_msg(self):
        try:
            while not self.closed():
                msg = WebSocketFrame()
                await self._conn.request(None, msg)
                await self._hdl.on_frame(self, msg)
        except asyncio.CancelledError:
            return
        except Exception as e:
            # TODO log the error

            # close when unknown exception, the connection may under invalid status
            await self.close()

    async def send(self, type: int, data: bytes):
        mask = random.randint(0, 2**32-1)
        msg = WebSocketFrame(opcode=type, mask=mask, payload=data)
        async with self._lock:
            if self.closed():
                raise WebSocketProcessorError('Send on closed connection')
            await self._conn.request(msg, None)

    async def send_text(self, text: str):
        await self.send(WebSocketOpcode.TextFrame, text.encode())

    async def send_binary(self, data: bytes):
        await self.send(WebSocketOpcode.BinaryFrame, data)

    async def send_ping(self):
        await self.send(WebSocketOpcode.Ping, bytes())

    async def send_pong(self):
        await self.send(WebSocketOpcode.Pong, bytes())


class WebSocketClient(WebSocketProcessor):
    def __init__(self, url: str, *,
            ssl_ctx: ssl.SSLContext = None,
            upgrade_headers: List[Tuple[str, str]] = None,
            frame_handler: WebSocketHandlerBase):
        super().__init__(frame_handler=frame_handler)

        self._url : str = url
        self._ssl_ctx: ssl.SSLContext = ssl_ctx

        self._ex_hdrs: List[Tuple[str, str]] = upgrade_headers
        if self._ex_hdrs is None:
            self._ex_hdrs = []

    async def _open(self):
        scheme, host, port, req_url = _ws_parse_url(self._url)
        addrs = await getaddrinfo(host, port)

        if len(addrs) == 0:
            what = 'Cannot resolve host'
            raise WebSocketProcessorError(what, host=host, port=port)

        conn = Connection(TcpAdaptor(addrs[0]))

        try:
            await conn.open()

            if scheme == 'wss':
                if self._ssl_ctx is None:
                    self._ssl_ctx = ssl.create_default_context()
                s = SslTransformer(self._ssl_ctx, host)
                await conn.bind(s)

            await conn.bind(ReadUntilTransformer())
            up = WebSocketUpgrader(host, req_url, upgrade_headers=self._ex_hdrs)
            await conn.bind(up)

            await self.start_with_conn(conn)
        except:
            await conn.close()
            raise

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def open(self):
        if self._closed:
            await self._open()
            self._closed = False


class WebSocketService(WebSocketProcessor):
    def __init__(self, conn: Connection, *
            frame_handler: WebSocketHandlerBase):
        super().__init__(frame_handler=frame_handler)
        self._srv_conn = conn

    async def _open(self):
        if self._srv_conn is None:
            raise WebSocketProcessorError('Cannot open service without connection')

        conn, self._srv_conn = self._srv_conn, None
        await self.start_with_conn(conn)

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def open(self):
        if self._closed:
            await self._open()
            self._closed = False
