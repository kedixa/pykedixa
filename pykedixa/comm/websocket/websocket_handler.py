import asyncio
from typing import (
    List,
    Union,

    Callable,
    Awaitable,
)

from .websocket_processor import (
    WebSocketHandlerBase,
    WebSocketProcessor,
)
from .websocket_message import (
    WebSocketFrame,
    WebSocketOpcode,
)

__all__ = [
    'WebSocketHandlerBase',
    'WebSocketBasicHandler',
    'WebSocketFuncHandler',
]


class WebSocketBasicHandler(WebSocketHandlerBase):
    def __init__(self, *, async_process: bool = True):
        super().__init__()

        self._async_process: bool = async_process
        self._frames: List[WebSocketFrame] = []

    async def on_frame(self, cli: 'WebSocketProcessor', frame: WebSocketFrame):
        self._frames.append(frame)
        if frame.fin:
            lst, self._frames = self._frames, []
            if self._async_process:
                asyncio.ensure_future(self.process_frames(cli, lst))
            else:
                await self.process_frames(cli, lst)

    async def process_frames(self, cli: 'WebSocketProcessor', frames: List[WebSocketFrame]):
        assert len(frames) > 0
        opcode = frames[0].opcode
        if opcode == WebSocketOpcode.TextFrame:
            data = bytes().join([m.payload for m in frames])
            try:
                data = data.decode()
            except UnicodeDecodeError:
                pass
            await self.on_text(cli, data)
        elif opcode == WebSocketOpcode.BinaryFrame:
            data = bytes().join([m.payload for m in frames])
            await self.on_binary(cli, data)
        elif opcode == WebSocketOpcode.Ping:
            await self.on_ping(cli)
        elif opcode == WebSocketOpcode.Pong:
            await self.on_pong(cli)
        elif opcode == WebSocketOpcode.ConnectionClose:
            await self.on_close(cli)
        else:
            await self.on_frames(cli, frames)

    async def on_text(self, cli: 'WebSocketProcessor', text: Union[str, bytes]):
        pass

    async def on_binary(self, cli: 'WebSocketProcessor', data: bytes):
        pass

    async def on_frames(self, cli: 'WebSocketProcessor', frames: List[WebSocketFrame]):
        '''Call this function when opcode unknown'''
        pass

    async def on_ping(self, cli: 'WebSocketProcessor'):
        await cli.send_pong()

    async def on_pong(self, cli: 'WebSocketProcessor'):
        pass

    async def on_close(self, cli: 'WebSocketProcessor'):
        await cli.close()

class WsFuncType:
    TEXT    = Callable[['WebSocketProcessor', Union[str, bytes]], Awaitable[None]]
    BINARY  = Callable[['WebSocketProcessor', bytes], Awaitable[None]]
    PING    = Callable[['WebSocketProcessor'], Awaitable[None]]
    PONG    = Callable[['WebSocketProcessor'], Awaitable[None]]
    CLOSE   = Callable[['WebSocketProcessor'], Awaitable[None]]
    FRAMES  = Callable[['WebSocketProcessor', List[WebSocketFrame]], Awaitable[None]]

class WebSocketFuncHandler(WebSocketBasicHandler):
    def __init__(self, *,
            async_process: bool = True,
            on_text: WsFuncType.TEXT        = None,
            on_binary: WsFuncType.BINARY    = None,
            on_ping: WsFuncType.PING        = None,
            on_pong: WsFuncType.PONG        = None,
            on_close: WsFuncType.CLOSE      = None,
            on_frames: WsFuncType.FRAMES    = None):
        super().__init__(async_process=async_process)

        self._on_text: WsFuncType.TEXT      = on_text
        self._on_binary: WsFuncType.BINARY  = on_binary
        self._on_ping: WsFuncType.PING      = on_ping
        self._on_pong: WsFuncType.PONG      = on_pong
        self._on_close: WsFuncType.CLOSE    = on_close
        self._on_frames: WsFuncType.FRAMES  = on_frames

    async def on_text(self, cli: 'WebSocketProcessor', text: Union[str, bytes]):
        if self._on_text:
            await self._on_text(cli, text)
        else:
            await super().on_text(cli, text)

    async def on_binary(self, cli: 'WebSocketProcessor', data: bytes):
        if self._on_binary:
            await self._on_binary(cli, data)
        else:
            await super().on_binary(cli, data)

    async def on_frames(self, cli: 'WebSocketProcessor', frames: List[WebSocketFrame]):
        '''Call this function when opcode unknown'''
        if self._on_frames:
            await self._on_frames(cli, frames)
        else:
            await super().on_frames(cli, frames)

    async def on_ping(self, cli: 'WebSocketProcessor'):
        if self._on_ping:
            await self._on_ping(cli)
        else:
            await super().on_ping(cli)

    async def on_pong(self, cli: 'WebSocketProcessor'):
        if self._on_pong:
            await self._on_pong(cli)
        else:
            await super().on_pong(cli)

    async def on_close(self, cli: 'WebSocketProcessor'):
        if self._on_close:
            await self._on_close(cli)
        else:
            await super().on_close()
