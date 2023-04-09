import base64
import hashlib
import random

from typing import (
    List,
    Tuple,
)

from ..http import (
    HttpRequest,
    HttpResponse,
)
from .. import (
    BasicTransformer,
    TransformerException,
)

__all__ = [
    'SEC_WS_APPEND',
    'get_sec_ws_accept',
    'get_sec_ws_pair',
]

SEC_WS_APPEND = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

def get_sec_ws_accept(key: str) -> str:
    accept = key + SEC_WS_APPEND
    accept = hashlib.sha1(accept.encode()).digest()
    accept = base64.b64encode(accept).decode()
    return accept


def get_sec_ws_pair() -> Tuple[str, str]:
    key = bytes(random.choices(range(0, 256), k=16))
    key: str = base64.b64encode(key).decode()
    return key, get_sec_ws_accept(key)


class WebSocketUpgradeError(TransformerException):
    pass


class WebSocketUpgrader(BasicTransformer):
    def __init__(self, host: str, req_url: str = '/', *,
            upgrade_headers: List[Tuple[str, str]] = None,
            sec_key: str = None):
        self._req_url: str = req_url
        self._host: str = host
        self._ex_hdrs: List[Tuple[str, str]] = upgrade_headers
        self._sec_key: str = sec_key

        if self._ex_hdrs is None:
            self._ex_hdrs = []

    def prepare_only(self) -> bool:
        return True

    async def prepare(self):
        if self._sec_key is None:
            sec_key, sec_accept = get_sec_ws_pair()
        else:
            sec_key = self._sec_key
            sec_accept = get_sec_ws_accept(sec_key)

        http_req = HttpRequest(req_url=self._req_url)
        http_resp = HttpResponse()

        for exhdr in self._ex_hdrs:
            http_req.set_header(exhdr[0], exhdr[1])

        http_req.set_header('Host', self._host, overwrite=False)
        http_req.set_header('Connection', 'Upgrade')
        http_req.set_header('Upgrade', 'websocket')
        http_req.set_header('Sec-WebSocket-Version', '13')
        http_req.set_header('Sec-WebSocket-Key', sec_key)

        await http_req.encode(self._nxt)
        await http_resp.decode(self._nxt)

        code = http_resp.get_status_code()
        if code != 101:
            what = f'Upgrade bad http status code {code}'
            raise WebSocketUpgradeError(what, code=code, http_resp=http_resp)

        resp_accept = http_resp.get_header('Sec-WebSocket-Accept')
        if len(resp_accept) != 1 or sec_accept != resp_accept[0]:
            what = f'Upgrade bad Sec-WebSocket-Accept'
            raise WebSocketUpgradeError(what,
                expect_accept=sec_accept,
                resp_accept=resp_accept,
                http_resp=http_resp)
