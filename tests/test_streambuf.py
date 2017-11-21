import asyncio

import pytest

from speech_pool.streambuf import StreamBuffer


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


async def producer(data_in, writer):
    for chunk in data_in:
        await writer.write(chunk)
    await writer.close()


async def consumer(data_out, reader):
    while True:
        chunk = await reader.read()
        if chunk is None:
            break
        data_out.append(chunk)


def test_write_and_read(event_loop):
    data_in = [[1, 2, 3], [4, 5, 6]]
    data_out1 = []
    data_out2 = []
    buf = StreamBuffer()
    writer = buf.make_writer()
    reader1 = buf.make_reader()
    reader2 = buf.make_reader()
    event_loop.run_until_complete(asyncio.gather(
        producer(data_in, writer),
        consumer(data_out1, reader1),
        consumer(data_out2, reader2)
    ))
    assert data_out1 == data_in
    assert data_out1 == data_out2


def test_write_then_read(event_loop):
    data_in = [[1, 2, 3], [4, 5, 6]]
    data_out1 = []
    data_out2 = []
    buf = StreamBuffer()
    writer = buf.make_writer()
    reader1 = buf.make_reader()
    reader2 = buf.make_reader()

    async def run():
        await producer(data_in, writer)
        await asyncio.gather(
            consumer(data_out1, reader1),
            consumer(data_out2, reader2)
        )

    event_loop.run_until_complete(run())
    assert data_out1 == data_in
    assert data_out1 == data_out2


def test_multiple_writers_error():
    buf = StreamBuffer()
    writer1 = buf.make_writer()
    with pytest.raises(Exception):
        writer2 = buf.make_writer()
