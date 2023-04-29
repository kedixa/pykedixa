import asyncio
import socket
from typing import List

__all__ = [
    'SocketAddress',
    'getaddrinfo',
]


class SocketAddress:
    def __init__(self, ip: str, port: int, *,
            family: int = socket.AF_INET,
            socktype: int = socket.SOCK_STREAM,
            proto: int = 0):
        self._ip: str       = ip
        self._port: int     = port
        self._family: int   = family
        self._socktype: int = socktype
        self._proto: int    = proto

        self._info: str     = None
        self._update_info()

    @property
    def info(self) -> str:
        return self._info

    @property
    def ip(self) -> str:
        return self._ip

    @property
    def port(self) -> int:
        return self._port

    @property
    def family(self) -> int:
        return self._family

    @property
    def socktype(self) -> int:
        return self._socktype

    @property
    def proto(self) -> int:
        return self._proto

    def __str__(self) -> str:
        return f'SocketAddress ip:{self._ip} port:{self._port}'

    def _update_info(self):
        self._info = f'{self.ip}:{self.port},{self.family},{self.socktype}'

async def getaddrinfo(host: str, port: int, *,
        family: int = socket.AF_INET,
        socktype: int = socket.SOCK_STREAM,
        proto: int = 0) -> List[SocketAddress]:
    if len(host) > 0 and host[0] == '[' and host[-1] == ']':
        host = host[1:-1]

    loop = asyncio.get_event_loop()
    addrs = await loop.getaddrinfo(host, port,
        family=family, type=socktype, proto=proto)

    return [
        SocketAddress(addr[4][0], addr[4][1],
            family=addr[0], socktype=addr[1], proto=addr[2])
        for addr in addrs
    ]
