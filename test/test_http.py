import asyncio
import socket
import ssl
from typing import List

import pytest
from kedixa.comm import *

async def getaddrinfo(host: str, port: int):
    loop = asyncio.get_event_loop()
    addrs = await loop.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)

    assert len(addrs) > 0
    return addrs[0]

async def do_http(host: str, port: int,
        reqs: List[HttpRequest],
        resps: List[HttpResponse]):
    addr = await getaddrinfo(host, port)
    sock = TcpAdaptor(addr[4],
        family=addr[0],
        proto=addr[2])
    runtil = ReadUntilFilter()

    runtil.bind_next(sock)

    async with sock, runtil as conn:
        for req in reqs:
            await req.encode(conn)
        for resp in resps:
            await resp.decode(conn)

async def do_https(host: str, port: int,
        reqs: List[HttpRequest],
        resps: List[HttpResponse]):
    addr = await getaddrinfo(host, port)
    sock = TcpAdaptor(addr[4],
        family=addr[0],
        proto=addr[2])

    ssl_ctx = ssl.create_default_context()
    ssl_filter = SslFilter(ssl_ctx, server_hostname=host)
    runtil = ReadUntilFilter()

    ssl_filter.bind_next(sock)
    runtil.bind_next(ssl_filter)

    async with sock, ssl_filter, runtil as conn:
        for req in reqs:
            await req.encode(conn)
        for resp in resps:
            await resp.decode(conn)

@pytest.mark.asyncio
async def test_http_head():
    headers = [('Host', 'www.sogou.com')]
    req = HttpRequest(method=HttpMethod.HEAD, headers=headers)
    resp = HttpResponse()
    resp.set_empty_body(True)  # parse head only

    await do_http('www.sogou.com', 80, [req], [resp])
    assert 200 <= resp.get_status_code() <= 400
    assert len(resp.get_body()) == 0

@pytest.mark.asyncio
async def test_http_get():
    headers = [('Host', 'www.sogou.com')]
    req = HttpRequest(method=HttpMethod.GET, headers=headers)
    resp = HttpResponse()

    await do_http('www.sogou.com', 80, [req], [resp])
    assert 200 <= resp.get_status_code() <= 400

@pytest.mark.asyncio
async def test_http_pipe():
    headers = [('Host', 'www.sogou.com')]
    req01 = HttpRequest(method=HttpMethod.HEAD, headers=headers)
    req02 = HttpRequest(method=HttpMethod.GET, headers=headers)
    resp01 = HttpResponse()
    resp01.set_empty_body(True)
    resp02 = HttpResponse()

    await do_http('www.sogou.com', 80,
        [req01, req02], [resp01, resp02])
    assert 200 <= resp01.get_status_code() <= 400
    assert 200 <= resp02.get_status_code() <= 400

@pytest.mark.asyncio
async def test_https_head():
    headers = [('Host', 'www.sogou.com')]
    req = HttpRequest(method=HttpMethod.HEAD, headers=headers)
    resp = HttpResponse()
    resp.set_empty_body(True)  # parse head only

    await do_http('www.sogou.com', 443, [req], [resp])
    assert 200 <= resp.get_status_code() <= 400
    assert len(resp.get_body()) == 0

@pytest.mark.asyncio
async def test_https_get():
    headers = [('Host', 'www.sogou.com')]
    req = HttpRequest(method=HttpMethod.GET, headers=headers)
    resp = HttpResponse()

    await do_http('www.sogou.com', 443, [req], [resp])
    assert 200 <= resp.get_status_code() <= 400

@pytest.mark.asyncio
async def test_https_pipe():
    headers = [('Host', 'www.sogou.com')]
    req01 = HttpRequest(method=HttpMethod.HEAD, headers=headers)
    req02 = HttpRequest(method=HttpMethod.GET, headers=headers)
    resp01 = HttpResponse()
    resp01.set_empty_body(True)
    resp02 = HttpResponse()

    await do_https('www.sogou.com', 443,
        [req01, req02], [resp01, resp02])
    assert 200 <= resp01.get_status_code() <= 400
    assert 200 <= resp02.get_status_code() <= 400
