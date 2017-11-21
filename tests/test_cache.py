import asyncio

import pytest

from speech_pool.cache import DataStreamCache


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def test_write_and_read(event_loop):
    async def producer(input, writer):
        for chunk in input:
            await writer.write(chunk)
        await writer.close()

    async def consumer(output, reader):
        while True:
            chunk = await reader.read()
            if chunk is None:
                break
            output.append(chunk)

    input = [[1, 2, 3], [4, 5, 6]]
    output1 = []
    output2 = []
    cache = DataStreamCache()
    key = 'test'
    writer = cache.writer(key)
    reader1 = cache.reader(key)
    reader2 = cache.reader(key)
    event_loop.run_until_complete(asyncio.gather(
        producer(input, writer),
        consumer(output1, reader1),
        consumer(output2, reader2)
    ))
    assert output1 == input
    assert output1 == output2


def test_write_then_read(event_loop):
    async def producer(input, writer):
        for chunk in input:
            await writer.write(chunk)
        await writer.close()

    async def consumer(output, reader):
        while True:
            chunk = await reader.read()
            if chunk is None:
                break
            output.append(chunk)

    input = [[1, 2, 3], [4, 5, 6]]
    output1 = []
    output2 = []
    cache = DataStreamCache()
    key = 'test'
    writer = cache.writer(key)
    reader1 = cache.reader(key)
    reader2 = cache.reader(key)

    async def run():
        await producer(input, writer)
        await asyncio.gather(
            consumer(output1, reader1),
            consumer(output2, reader2)
        )

    event_loop.run_until_complete(run())
    assert output1 == input
    assert output1 == output2


def test_multiple_writers_error():
    cache = DataStreamCache()
    writer1 = cache.writer('1')
    with pytest.raises(KeyError):
        writer2 = cache.writer('1')


def test_reader_for_unknown_key_error():
    cache = DataStreamCache()
    with pytest.raises(KeyError):
        reader = cache.reader('1')
