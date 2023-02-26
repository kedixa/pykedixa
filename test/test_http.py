import asyncio
import socket
import pytest

from kedixa.comm import *

async def getaddrinfo(host: str, port):
    loop = asyncio.get_event_loop()
    addrs = await loop.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)

    assert len(addrs) > 0
    return addrs[0]

async def do_http(host, port):
    addr = await getaddrinfo(host, port)
    sock = SyncTcpAdaptor(addr[4],
        family=addr[0],
        proto=addr[2])
    runtil = ReadUntilFilter()

    runtil.bind_next(sock)

    req = HttpRequest(req_url='/')
    resp = HttpResponse()

    req.add_header('Host', host)

    async with sock, runtil as conn:
        await req.encode(conn)
        await resp.decode(conn)

    return resp

@pytest.mark.asyncio
async def test_http_normal01():
    resp = await do_http('www.sogou.com', 80)

    assert 200 <= resp.get_status_code() <= 400

