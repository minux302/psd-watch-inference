import asyncio


_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)


async def sleep(interval):
    await asyncio.sleep(interval)


def run(future):
    task = None

    def schedule():
        nonlocal task
        task = _loop.create_task(future)
        _loop.stop()

    if not _loop.is_running():
        _loop.call_soon(schedule)
        _loop.run_forever()
    else:
        task = _loop.create_task(future)
    assert task, "Task was not scheduled"
    return task


def stop():
    global _loop
    try:
        _loop.stop()
        _loop.close()
    except Exception:
        pass


class AsyncApp:
    def __init__(self):
        pass

    def run(self, coro):
        task = run(coro)
        while not task.done():
            _loop.run_until_complete(sleep(0.02))
        return task.result()
