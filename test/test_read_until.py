import pytest

from kedixa.comm import (
    ReadUntilTransformer,
    LoopbackAdaptor,
    TransformerException,
)

@pytest.mark.asyncio
async def test_read_until01():
    lo = LoopbackAdaptor()
    runtil = ReadUntilTransformer()
    runtil.bind_next(lo)
    async with lo, runtil:
        await runtil.write_all(b'abcd')
        assert await runtil.read_until(b'c') == b'abc'
        await runtil.read_exactly(1) == b'd'

@pytest.mark.asyncio
async def test_read_until01():
    lo = LoopbackAdaptor()
    async with lo:
        await lo.write_all(b'abcd')
        runtil = ReadUntilTransformer()
        runtil.bind_next(lo)
        await runtil.prepare()
        await runtil.read_until(b'a')

        with pytest.raises(TransformerException):
            await runtil.finish()
