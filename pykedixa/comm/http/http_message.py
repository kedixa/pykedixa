import enum
from typing import List, Tuple, Dict, Union

from ..exception import BadMessage
from ..basic import (
    MessageBase,
    CommunicateBase,
    CommFlags,

    StrHelper,
)
from ..read_until_filter import ReadUntilFilter
from .http_code_map import get_http_code_phrase

__all__ = [
    'HttpHeaders',
    'HttpHeaderMap',
    'HttpMethod',
    'HttpMessage',
    'HttpRequest',
    'HttpResponse',
]


class HttpHeaders:
    def __init__(self, name: str, values: List[str]):
        if isinstance(values, str):
            values = [values]

        self.name: str = name
        self.values: List[str] = values

    def add(self, value: str):
        self.values.append(value)

    def add_list(self, values: List[str]):
        self.values.extend(values)

    def set(self, value: str):
        self.values = [value]

    def set_list(self, values: List[str]):
        self.values = values.copy()


class HttpHeaderMap:
    def __init__(self,
            headers: Union[List[Tuple[str, str]], 'HttpHeaderMap'] = None):
        self._hd_map: Dict[str, HttpHeaders] = {}
        if isinstance(headers, HttpHeaderMap):
            for _, hs in headers.get_items():
                self.add_header(hs.name, hs.values.copy())
        elif headers is not None:
            # List[Tuple[str, str]]
            for name, value in headers:
                self.add_header(name, value)

    def __len__(self) -> int:
        return len(self._hd_map)

    def __getitem__(self, name: str) -> Union[List[str], None]:
        return self.get_header(name)

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._hd_map

    def __str__(self) -> str:
        h = StrHelper()
        self._to_str(h)
        return h.join()

    def _to_str(self, str_helper: StrHelper):
        str_helper.append(f'HttpHeaderMap at {hex(id(self))}')

        with str_helper:
            for headers in self._hd_map.values():
                for value in headers.values:
                    str_helper.append(f'{headers.name}: {value}')

    def format_header(self) -> str:
        data = []
        for headers in self._hd_map.values():
            name = headers.name
            for value in headers.values:
                data.extend([name, ': ', value, '\r\n'])
        return str().join(data)

    def add_header(self,
            name: str,
            values: Union[List[str], str],
            *,
            reset: bool = False):

        if isinstance(values, str):
            values = [values]

        lname = name.lower()
        hd = self._hd_map.get(lname)

        if hd is None:
            self._hd_map[lname] = HttpHeaders(name, values)
        elif reset:
            hd.set_list(values)
        else:
            hd.add_list(values)

    def set_header(self, name: str, value: Union[List[str], str]):
        self.add_header(name, value, reset=True)

    def get_header(self, name: str) -> Union[List[str], None]:
        hd = self._hd_map.get(name.lower())
        return None if hd is None else hd.values.copy()

    def del_header(self, name: str):
        del self._hd_map[name.lower()]

    def get_names(self):
        return self._hd_map.keys()

    def get_items(self):
        return self._hd_map.items()


class HttpMethod(enum.IntEnum):
    GET     = 0
    HEAD    = 1
    POST    = 2
    PUT     = 3
    DELETE  = 4
    CONNECT = 5
    OPTIONS = 6


class HttpMessage(MessageBase):
    def __init__(self, *,
            http_version: str,
            headers: List[Tuple[str, str]],
            body: bytes):
        if isinstance(body, str):
            body = body.encode()

        self._http_version: str         = http_version
        self._headers: HttpHeaderMap    = HttpHeaderMap(headers)
        self._body: bytes               = body

        # see set_empty_body
        self._empty_body: bool          = False
        # for decode
        self._status_line: str          = None

    def __str__(self) -> str:
        h = StrHelper()
        self._to_str(h)
        return h.join()

    def _format_status_line(self) -> str:
        # subclasses should implement it for _to_str
        return self._http_version

    def _to_str(self, str_helper: StrHelper):
        name = self.__class__.__name__
        body_len = len(self._body) if self._body else 0

        str_helper.append(f'{name} at {hex(id(self))}')
        with str_helper:
            str_helper.append(self._format_status_line())
            self._headers._to_str(str_helper)
            str_helper.append(f'HttpBody(bytes) at {hex(id(self._body))} with length {body_len}')

    def get_http_version(self) -> str:
        return self._http_version

    def set_http_version(self, http_version: str):
        self._http_version = http_version

    @property
    def headers(self):
        '''
        Return a reference to self._headers,
        make it easier to iterate all headers,
        but do not modify it if you don't really want to.
        '''
        return self._headers

    def is_empty_body(self) -> bool:
        return self._empty_body

    def set_empty_body(self, empty: bool):
        '''
        Tell decoder that the body is always empty,
        even though content-length is not zero;
        tell encoder that dont overwrite content-length header,
        regardless of the value of body.
        For example: the response of HEAD request.
        '''
        self._empty_body = empty

    def _content_length(self) -> int:
        x = self.get_header('Content-Length')
        if x is None or len(x) == 0:
            return 0
        return int(x[0])

    def _chunk_encoding(self) -> bool:
        x = self.get_header('Transfer-Encoding')
        if x is None or len(x) == 0:
            return False

        for v in x:
            if len(v) == 7 and v.casefold() == 'chunked':
                return True
        return False

    async def _decode_header(self, c: ReadUntilFilter):
        '''
        Decode http header from c,
        save parsed header to self._headers.
        '''
        head_end = b'\r\n\r\n'
        data = await c.read_until(head_end)
        head: str = data.decode()
        heads: List[str] = head.split('\r\n')

        while heads and not heads[-1]:
            heads.pop()

        if len(heads) > 0:
            self._status_line = heads[0]

        for line in heads[1:]:
            sp = line.find(':')
            if sp < 0:
                name, value = line.strip(), ''
            else:
                name, value = line[:sp].strip(), line[sp+1:].strip()

            if name:
                self.add_header(name, value)

    async def _decode_chunked_body(self, c: ReadUntilFilter):
        self._body = bytearray()
        line_end = b'\r\n'
        end_len = 2

        while True:
            data: bytes = await c.read_until(line_end)
            data = data[:-2]

            try:
                chunk_len = int(data, 16)
            except ValueError:
                raise BadMessage(f'BadHttpMessage: chunk length {data} isn\'t hex format')

            # read chunk data and trailing \r\n
            if chunk_len > 0:
                self._body.extend(await c.read_exactly(chunk_len))

            eol = await c.read_exactly(end_len)
            if eol != line_end:
                raise BadMessage(f'BadHttpMessage: chunk end with {eol}')

            if chunk_len == 0:
                break

        self._body = bytes(self._body)

    async def decode(self, c: CommunicateBase):
        extra_filter = False
        r: ReadUntilFilter = c

        if not c.support_flags(CommFlags.READ_UNTIL):
            extra_filter = True
            r = ReadUntilFilter()
            r.bind_next(c)
            await r.prepare()

        await self._decode_header(r)

        if not self.is_empty_body():
            if self._chunk_encoding():
                await self._decode_chunked_body(r)
            else:
                content_len = self._content_length()
                self._body = bytes(await r.read_exactly(content_len))

        if extra_filter:
            # make sure no extra data in r, otherwise raise exception
            await r.finish()

    def add_header(self, name: str, value: str):
        self._headers.add_header(name, value)

    def set_header(self, name: str, value: str, *, overwrite: bool = True):
        if overwrite or name not in self._headers:
            self._headers.set_header(name, value)

    def del_header(self, name: str):
        self._headers.del_header(name)

    def get_header(self, name: str) -> List[str]:
        return self._headers.get_header(name)

    def get_header_names(self):
        '''Return all header names'''
        return self._headers.get_names()

    def set_body(self, body: bytes):
        self._body = body

    def append_body(self, buffer: bytes):
        self._body += buffer

    def get_body(self) -> bytes:
        return self._body


class HttpRequest(HttpMessage):
    def __init__(self, *,
            method: HttpMethod = HttpMethod.GET,
            req_url: str = '/',
            http_version: str = 'HTTP/1.1',
            headers: List[Tuple[str, str]] = None,
            body: bytes = bytes()):
        super().__init__(http_version=http_version,
                headers=headers,
                body=body)

        self._method: HttpMethod    = method
        self._req_url: str          = req_url

    def _format_status_line(self) -> str:
        return f'{self._method.name} {self._req_url} {self._http_version}'

    def set_method(self, method: HttpMethod):
        self._method = method

    def get_method(self) -> HttpMethod:
        return self._method

    def set_req_url(self, url: str):
        self._req_url = url

    def get_req_url(self) -> str:
        return self._req_url

    async def encode(self, c: CommunicateBase):
        if not self.is_empty_body():
            self.set_header('Content-Length', str(len(self._body)))

            if self._chunk_encoding():
                self.del_header('Transfer-Encoding')

        data = f'{self._method.name} {self._req_url} {self._http_version}\r\n'
        data = data + self._headers.format_header() + '\r\n'
        data = data.encode()

        if not self.is_empty_body():
            data += self._body

        await c.write_all(data)

    async def decode(self, c: CommunicateBase):
        await super().decode(c)

        st = self._status_line.split(maxsplit=2)
        while len(st) < 3:
            st.append('')

        method, self._req_url, self._http_version = st
        method = method.upper()
        self._method = method

        for m in HttpMethod:
            if m.name == method:
                self._method = m
                break


class HttpResponse(HttpMessage):
    def __init__(self, *,
            http_version: str = 'HTTP/1.1',
            status_code: int = 200,
            reason_phrase: str = 'OK',
            headers: List[Tuple[str, str]] = None,
            body: bytes = bytes()):
        super().__init__(http_version=http_version,
                headers=headers,
                body=body)

        self._status_code: int = status_code
        self._reason_phrase: str = reason_phrase

    def _format_status_line(self) -> str:
        return f'{self._http_version} {self._status_code} {self._reason_phrase}'

    def set_http_status(self, status_code: int, reason_phrase: str = None):
        if reason_phrase is None:
            reason_phrase = get_http_code_phrase(status_code)

        self._status_code = status_code
        self._reason_phrase = reason_phrase

    def get_status_code(self) -> int:
        return self._status_code

    def get_reason_phrase(self) -> str:
        return self._reason_phrase

    async def encode(self, c: CommunicateBase):
        if not self.is_empty_body():
            self.set_header('Content-Length', str(len(self._body)))

            if self._chunk_encoding():
                self.del_header('Transfer-Encoding')

        data = f'{self._http_version} {self._status_code} {self._reason_phrase}\r\n'
        data = data + self._headers.format_header() + '\r\n'
        data = data.encode()

        if not self.is_empty_body():
            data += self._body

        await c.write_all(data)

    async def decode(self, c: CommunicateBase):
        await super().decode(c)

        st = self._status_line.split(maxsplit=2)
        while len(st) < 3:
            st.append('')

        self._http_version, code, self._reason_phrase = st
        if not code.isdecimal():
            raise BadMessage(f'BadHttpMessage: bad status code {code}')

        self._status_code = int(code)

