import multiprocessing as mp
from kedixa.mprocess import MContext, MProcess

def test_mprocess():
    def worker(ctx: MContext, d):
        s = 0
        for task in ctx:
            for i in range(task[0], task[1]):
                s += i

        d[ctx.procid] = s

    m = mp.Manager()
    d = m.dict()

    mpr = MProcess(4)
    mpr.create_process(worker, args=(d,))
    mpr.start()

    real_ans = 0
    for _ in range(1000):
        real_ans += (10000 - 1) * 10000 / 2
        mpr.put_task((0, 10000))

    mpr.stop()

    ans = 0
    for _, v in d.items():
        ans += v

    assert real_ans == ans
