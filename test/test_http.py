import ssl
from typing import List

import pytest
from kedixa.comm import *
from kedixa.comm.http import *

async def do_http(host: str, port: int,
        reqs: List[HttpRequest],
        resps: List[HttpResponse]):
    addrs = await getaddrinfo(host, port)
    assert len(addrs) > 0
    sock = TcpAdaptor(addrs[0])
    runtil = ReadUntilTransformer()

    runtil.bind_next(sock)

    async with sock, runtil as conn:
        for req in reqs:
            await req.encode(conn)
        for resp in resps:
            await resp.decode(conn)

async def do_https(host: str, port: int,
        reqs: List[HttpRequest],
        resps: List[HttpResponse]):
    addrs = await getaddrinfo(host, port)
    assert len(addrs) > 0
    sock = TcpAdaptor(addrs[0])

    ssl_ctx = ssl.create_default_context()
    ssl_tx = SslTransformer(ssl_ctx, server_hostname=host)
    runtil = ReadUntilTransformer()

    ssl_tx.bind_next(sock)
    runtil.bind_next(ssl_tx)

    async with sock, ssl_tx, runtil as conn:
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
