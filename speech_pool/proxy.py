import asyncio
import logging

__all__ = ['run_proxy']

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

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
        # get real port value, cause proxy_address[1] may be None
        proxy_port = writer.transport.get_extra_info('sockname')[1]
        proxy_name = 'proxy (%s:%d->%s:%d)' % (proxy_address[0], proxy_port, *target_address)
        log.debug('%s start', proxy_name)
        target_reader, target_writer = await asyncio.open_connection(*target_address)
        try:
            await asyncio.gather(_pipe(target_reader, writer), _pipe(reader, target_writer))
        except:
            log.exception('%s', proxy_name)
        else:
            log.debug('%s end', proxy_name)
        finally:
            target_writer.close()

    return await asyncio.start_server(_proxy, host=proxy_address[0], port=proxy_address[1])
