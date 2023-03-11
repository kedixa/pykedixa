import asyncio
import os

import pytest
from kedixa.comm import *

@pytest.mark.asyncio
async def test_file_adaptor():
    tmp_fn = 'files/fileadaptor.tmp'
    body = b'http body'
    x = HttpRequest(method=HttpMethod.POST, body=body)
    x.add_header('name', 'value')
    y = HttpRequest()

    fa = FileAdaptor(tmp_fn, 'wb')
    fb = FileAdaptor(tmp_fn, 'rb')

    async with fa:
        await x.encode(fa)

    async with fb:
        await y.decode(fb)

    os.remove(tmp_fn)

    assert x.get_method() == y.get_method()
    assert x.get_body() == y.get_body()
    assert y.get_header('name') == ['value']
