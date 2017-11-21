import asyncio
import hashlib
import logging
import textwrap
from weakref import WeakValueDictionary

import aiohttp
import aiohttp.web
import jsonrpcserver.config
from jsonrpcserver.aio import methods

from .streambuf import StreamBuffer

__all__ = ['run']

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# jsonrpc client/server logging config (these libs have non=pythonic logging configuration)
jsonrpcserver.config.log_requests = False
jsonrpcserver.config.log_responses = False
logging.getLogger('jsonrpcclient.client.request').setLevel(logging.ERROR)
logging.getLogger('jsonrpcclient.client.response').setLevel(logging.ERROR)


def _hash(text):
    # TODO: we don't use text as text in this app, so json decoder can leave all texts as bytes
    return hashlib.md5(text.encode('utf8')).hexdigest()


def _shorten(text):
    return textwrap.shorten(text, 32)


async def _send_bus_event(event):
    """TODO"""
    log.info('Rabbitmq message: %s', event)


async def run_tts_conversion(tts_api_url, text, streambuf_writer):
    """Coroutine to interact with TTS service

        Requests text to speech conversion, receives data, writes data to streambuf.
    """
    log.debug('TTS conversion of text "%s". Begin', _shorten(text))
    try:
        #### TTS Provider Stub
        # TODO: open external port, connect to TTS service and request text conversion
        ####
        for ch in text:
            await asyncio.sleep(0.3)
            await streambuf_writer.write(ch.encode('utf8'))
            ####
    except:
        log.exception('TTS service streaming error')
        await streambuf_writer.close(inclomplete=True)
    else:
        await streambuf_writer.close()
    log.debug('TTS conversion of text "%s". End', _shorten(text))


async def play(streambuf_reader, client_address, on_completed_event):
    """Coroutine to stream data (result of tts converison) from streambuf to client
    """
    try:
        target_reader, target_writer = await asyncio.open_connection(*client_address)
        try:
            while True:
                data_chunk = await streambuf_reader.read()
                if data_chunk is None:
                    break
                target_writer.write(data_chunk)
        finally:
            target_writer.close()
    except asyncio.CancelledError:
        await _send_bus_event('event: %s, canceled' % on_completed_event)
    except Exception as ex:
        log.exception('tts streambuf play error')
        await _send_bus_event('event: %s, error: %s' % (on_completed_event, ex))
    else:
        await _send_bus_event('event: %s, done' % on_completed_event)


class Api:
    def __init__(self, host, tts_api_url):
        self._service_host = host
        self._tts_api_url = tts_api_url
        self._requests_counter = 0
        self._cache = {}  # key: text hash, value: stream buffer
        self._clients = WeakValueDictionary()  # key: request id, value: future for play

    async def start_speek(self, text, host, port, on_completed_event):
        """Start streaming text converted to speech to given address.

        Streams are cached by text hash.
        'on_completed_event' is used to notify client about process end

        :param str text:
        :param str host:
        :param int port:
        :param on_completed_event:
        :return: request_id
        :rtype: int
        """
        log.debug('on start_speek')
        self._requests_counter += 1
        request_id = self._requests_counter
        text_hash = _hash(text)
        buf = self._cache.get(text_hash)
        if not buf:  # text hasn't been translated to speech before
            log.info('tts from serivce')
            buf = StreamBuffer()
            self._cache[text_hash] = buf
            asyncio.ensure_future(run_tts_conversion(self._tts_api_url, text, buf.make_writer()))
        else:
            log.info('tts from cache')
        self._clients[request_id] = asyncio.ensure_future(play(buf.make_reader(), (host, port), on_completed_event))
        return request_id

    async def stop_speek(self, request_id):
        """ Cancel speech stream play for given request_id

        (tts to cache stream will not be canceled)

        :param str request_id:
        """
        log.debug('on stop_speek')
        fut = self._clients.pop(request_id, None)
        if fut is not None:
            fut.cancel()
        return

    @staticmethod
    async def jsonrpc_dispatch(request):
        request = await request.text()
        response = await methods.dispatch(request)
        if response.is_notification:
            return aiohttp.web.Response()
        else:
            return aiohttp.web.json_response(response, status=response.http_status)


def run(settings):
    api = Api(settings.host, settings.tts_api_url)
    methods.add(api.start_speek)
    methods.add(api.stop_speek)
    app = aiohttp.web.Application()
    app.router.add_post('/api/v1', api.jsonrpc_dispatch)
    aiohttp.web.run_app(app, host=settings.host, port=settings.port)
