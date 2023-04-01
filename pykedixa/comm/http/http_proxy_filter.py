from typing import List, Tuple

from ..basic import BasicFilter
from ..exception import FilterException
from .http_message import HttpRequest, HttpResponse, HttpMethod

__all__ = [
    'HttpProxyFilter',
    'HttpProxyConnectError',
]

def _proxy_auth(user: str, passwd: str) -> str:
    import base64
    auth = f'{user}:{passwd}'.encode()
    auth = base64.b64encode(auth).decode()
    return f'Basic {auth}'


class HttpProxyConnectError(FilterException):
    def __init__(self, host: str, port: int, resp: HttpResponse):
        what = f'host:{host} port:{port} http_status:{resp.get_status_code()}'
        super().__init__(what)
        self._host: str = host
        self._port: int = port
        self._resp: HttpResponse = resp

    def __str__(self) -> str:
        return f'HttpProxyConnectError {self.what()}'

    @property
    def status_code(self) -> int:
        return self._resp.get_status_code()

    @property
    def reason_phrase(self) -> str:
        return self._resp.get_reason_phrase()

    @property
    def resp(self) -> HttpResponse:
        return self._resp


class HttpProxyFilter(BasicFilter):
    def __init__(self,
            host: str,
            port: int,
            username: str = None,
            password: str = None,
            headers: List[Tuple[str, str]] = None):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._headers = headers if headers is not None else []

    async def prepare(self):
        host_hd = f'{self._host}:{self._port}'
        req = HttpRequest(
            method=HttpMethod.CONNECT,
            req_url=host_hd,
            headers=self._headers)
        resp = HttpResponse()

        if (self._username is not None and
                self._password is not None):
            auth = _proxy_auth(self._username, self._password)
            req.set_header('Proxy-Authorization', auth, overwrite=False)

        req.set_header('User-Agent', 'python3', overwrite=False)
        req.set_header('Host', host_hd, overwrite=False)
        req.set_header('Proxy-Connection', 'Keep-Alive', overwrite=False)

        await req.encode(self)
        await resp.decode(self)

        code = resp.get_status_code()
        if code != 200:
            raise HttpProxyConnectError(self._host, self._port, resp)

