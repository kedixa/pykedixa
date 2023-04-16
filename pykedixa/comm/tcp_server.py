import asyncio
import logging
import socket
from typing import Callable, Awaitable

from . import Connection, TcpAdaptor, SocketAddress

__all__ = [
    'ProcessorType',
    'TcpServer',
]

ProcessorType = Callable[[Connection], Awaitable[None]]
_logger = logging.getLogger('kedixa.comm.tcp_server')


def _wrap_processor(proc: ProcessorType):
    async def wrapper(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        ip, port, family = None, None, None
        peer = w.get_extra_info('peername')
        if isinstance(peer, tuple):
            if len(peer) >= 2:
                ip, port = peer[:2]
                if len(peer) == 2:
                    family = socket.AF_INET
                elif len(peer) == 4:
                    family = socket.AF_INET6

        addr = SocketAddress(ip, port, family=family)
        adaptor = TcpAdaptor(addr=addr, reader=r, writer=w)
        conn = Connection(adaptor, prepared=True)

        await conn.open()
        try:
            ret = await proc(conn)
        except Exception:
            _logger.exception("")
            ret = None
        finally:
            await conn.close()
        return ret
    return wrapper


async def _forever():
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass


class TcpServer:
    def __init__(self, *,
            local_ip: str = '0.0.0.0',
            listen_port: int = 0,
            processor: Callable[[Connection], None]):
        self._ip: str           = local_ip
        self._port: int         = listen_port
        self._proc: Callable    = processor
        self._stopped: bool     = True
        self._port_zero: bool   = self._port == 0
        self._server: asyncio.AbstractServer = None
        self._forever: asyncio.Task = None

    @property
    def port(self) -> int:
        '''
        If listen_port is zero, it is decided by OS when start server,
        this function returns the real listen port after start.
        '''
        return self._port

    async def start(self):
        assert self._stopped is True
        self._stopped = False
        proc = _wrap_processor(self._proc)
        self._server = await asyncio.start_server(proc, self._ip, self._port)

        if self._port == 0:
            for sock in self._server.sockets:
                s = sock.getsockname()
                if isinstance(s, tuple) and len(s) >= 2 and isinstance(s[1], int):
                    self._port = s[1]
                    break

    def stop(self):
        if not self._stopped:
            self._stopped = True

            if self._port_zero:
                self._port = 0

            self._server.close()

            if self._forever:
                self._forever.cancel()

    async def run_forever(self):
        assert self._forever is None
        self._forever = asyncio.ensure_future(_forever())
        await self._forever
        self._forever = None

    async def wait_finish(self):
        if not self._stopped:
            self.stop()
        await self._server.wait_closed()
