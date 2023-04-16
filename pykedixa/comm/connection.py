import asyncio
from typing import List

from .basic import (
    CommunicateBase,
    BasicAdaptor,
    BasicTransformer,
    MessageBase,
)

__all__ = [
    'Connection',
]


class Connection:
    def __init__(self, adaptor: BasicAdaptor, *,
            prepared: bool = False):
        self._adaptor: BasicAdaptor = adaptor
        self._comms: List[CommunicateBase] = []
        self._closed: bool = not prepared

        self._c: CommunicateBase = self._adaptor
        self._lock: asyncio.Lock = asyncio.Lock()
        self._context = None

    @property
    def c(self) -> CommunicateBase:
        return self._c

    @property
    def adaptor(self) -> BasicAdaptor:
        return self._adaptor

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    @property
    def info(self) -> str:
        return 'TODO'

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, context):
        self._context = context

    def closed(self) -> bool:
        return self._closed

    async def open(self):
        if self._closed:
            await self._adaptor.prepare()
            self._closed = False

    async def close(self):
        if not self._closed:
            self._closed = True
            try:
                for comm in self._comms[::-1]:
                    await comm.finish()
                self._comms.clear()
            except:
                # force close if gracefully finish failed
                self._comms.clear()
                self._c = self._adaptor
                await self._adaptor.finish()
                raise
            else:
                self._c = self._adaptor
                await self._adaptor.finish()

    async def bind(self, next: BasicTransformer):
        if len(self._comms) == 0:
            next.bind_next(self._adaptor)
        else:
            next.bind_next(self._comms[-1])

        await next.prepare()
        self._comms.append(next)
        self._c = next

    async def request(self, req: MessageBase, resp: MessageBase):
        '''
        Use Connection.request to send req and receive resp,
        or use Connection.c directly.
        '''
        if req is not None:
            await req.encode(self.c)

        if resp is not None:
            await resp.decode(self.c)
