import asyncio
import queue
import concurrent.futures as fut
import multiprocessing as mp
from typing import List, Callable
from multiprocessing.synchronize import Event, Barrier

__all__ = [
    'MContext',
    'MProcess'
]

class MContext:
    def __init__(self,
            procid: int,
            que: mp.Queue,
            barrier: Barrier,
            stopevent: Event):
        self._procid: int = procid
        self._que: mp.Queue = que
        self._barrier: Barrier = barrier
        self._stopevent: Event = stopevent
        self._finished: bool = False

        self._pool: fut.ThreadPoolExecutor = None
        self._sem: asyncio.Semaphore = None
        self._loop: asyncio.AbstractEventLoop = None

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            try:
                return self.get_task(timeout=0.05)
            except queue.Empty:
                if self.finished():
                    raise StopIteration

    async def __aiter__(self):
        if self._pool is None:
            self._pool = fut.ThreadPoolExecutor(1)
            self._sem = asyncio.Semaphore(1)
            self._loop = asyncio.get_event_loop()
        return self

    async def __anext__(self):
        try_sync = True
        while True:
            try:
                if try_sync:
                    return self.get_task(False, None)
                async with self._sem:
                    if self._finished:
                        raise StopAsyncIteration
                    return await self._loop.run_in_executor(self._pool, self.get_task, True, 0.05)
            except queue.Empty:
                try_sync = False
                if self.finished():
                    raise StopAsyncIteration

    @property
    def procid(self) -> int:
        return self._procid

    def wait_start(self) -> int:
        self._barrier.wait()

    def get_task(self, block=True, timeout=None):
        return self._que.get(block=block, timeout=timeout)

    def finished(self) -> bool:
        if not self._finished:
            self._finished = self._stopevent.is_set()
        return self._finished

    def shutdown(self):
        if self._pool is not None:
            self._pool.shutdown(True)
            self._pool = None
            self._sem = None
            self._loop = None

def _worker(func: Callable, ctx: MContext, *args, **kwargs):
    ctx.wait_start()
    try:
        ret = func(ctx, *args, **kwargs)
    except KeyboardInterrupt:
        ret = None
    finally:
        ctx.shutdown()
    return ret

class MProcess:
    def __init__(self, nproc: int = 1, max_quesize: int = 256):
        assert nproc >= 1
        self._nproc = nproc
        self._que: mp.Queue = mp.Queue(max_quesize)
        self._barrier: Barrier = mp.Barrier(nproc + 1)
        self._stopevent: Event = mp.Event()
        self._procs: List[mp.Process] = None

    def put_task(self, task, block=True, timeout=None):
        self._que.put(task, block, timeout)

    def create_process(self, func: Callable, *, args = None, kwargs = None):
        if self._procs is not None:
            raise Exception('Process already created')

        if args is None:
            args = []
        args = list(args)
        if kwargs is None:
            kwargs = {}

        self._procs = []
        for i in range(self._nproc):
            ctx = MContext(i, self._que, self._barrier, self._stopevent)
            cur_args = [func, ctx] + args
            self._procs.append(mp.Process(target=_worker, args=cur_args, kwargs=kwargs))

    def start(self):
        for p in self._procs:
            p.start()
        self._barrier.wait()

    def stop(self):
        self._que.close()
        self._que.join_thread()
        self._stopevent.set()
        for p in self._procs:
            p.join()

