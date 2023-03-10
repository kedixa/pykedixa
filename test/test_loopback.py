import pytest
from kedixa.comm import LoopbackAdaptor, AdaptorEofError

@pytest.mark.asyncio
async def test_loopback01():
    async with LoopbackAdaptor() as lo:
        data = b'12345678'
        assert await lo.write_all(data[:3], flush=False) == 3
        assert await lo.write_all(data[3:]) == 5
        assert await lo.read(8) == data

@pytest.mark.asyncio
async def test_loopback02():
    async with LoopbackAdaptor() as lo:
        data = b'12345678'
        assert await lo.write_all(data[:3], flush=False) == 3
        assert await lo.write_all(data[3:]) == 5
        buf = bytearray(8)
        await lo.read(8, buffer=buf)
        assert buf == data

@pytest.mark.asyncio
async def test_loopback03():
    async with LoopbackAdaptor() as lo:
        tmp = bytearray([i for i in range(128)])
        data = bytearray()
        for i in range(1, 128):
            await lo.write(tmp[:i])
            data.extend(tmp[:i])

        buf = bytearray(len(data))
        await lo.read_exactly(len(buf), buffer=buf)
        assert buf == data

        with pytest.raises(AdaptorEofError):
            await lo.read(1)
