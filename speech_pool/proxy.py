import asyncio

__all__ = ['run_proxy']

_PIPE_BUFFER_SIZE = 4096


async def _pipe(reader, writer):
    try:
        while not reader.at_eof():
            writer.write(await reader.read(_PIPE_BUFFER_SIZE))
    finally:
        writer.close()


async def run_proxy(proxy_address, target_address):
    """ Run TCP proxy.

    Use None for proxy_address port to choose a random free port for proxy.
    Caller can get port from result:
        p = await run_proxy()
        proxy_port = p.sockets[0].getsockname()[1]

    :param tuple proxy_address:  set port to None to choose a random port
    :param tuple target_address:
    :return: The return value is the same as loop.create_server()
    """

    async def _proxy(reader, writer):
        target_reader, target_writer = await asyncio.open_connection(*target_address)
        try:
            await asyncio.gather(_pipe(target_reader, writer), _pipe(reader, target_writer))
        finally:
            target_writer.close()

    return await asyncio.start_server(_proxy, host=proxy_address[0], port=proxy_address[1])
