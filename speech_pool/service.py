import asyncio
import hashlib
import logging
import textwrap
from lru import LRU
from weakref import WeakValueDictionary, WeakSet

import aiohttp
import aiohttp.web
import jsonrpcserver.config
from jsonrpcserver.aio import methods
from jsonrpcserver.exceptions import ServerError

from .streambuf import StreamBuffer

__all__ = ['run']

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# jsonrpc client/server logging config (these libs have non=pythonic logging configuration)
jsonrpcserver.config.log_requests = False
jsonrpcserver.config.log_responses = False


def _hash(text):
    # TODO: we don't use text as text in this app, so json decoder can leave all texts as bytes
    return hashlib.md5(text.encode('utf8')).hexdigest()


def _shorten(text):
    return textwrap.shorten(text, 32)


async def _send_bus_event(event):
    """TODO: rabbitmq client"""
    logger.info('Rabbitmq message: %s', event)


async def run_tts_conversion(tts_api_url, text, streambuf_writer):
    """Coroutine to interact with TTS service

        Requests text to speech conversion, receives data, writes data to streambuf.
    """
    log = logger.getChild('TTS')
    log.debug('converting text "%s"...', _shorten(text))
    try:
        #### TTS Provider Stub
        # TODO: open external port, connect to TTS service and request text conversion
        ####
        for ch in text:
            await asyncio.sleep(0.3)  # just for demo
            await streambuf_writer.write(ch.upper().encode('utf8'))
            ####
    except:
        log.exception('streaming error')
        await streambuf_writer.close(inclomplete=True)
    else:
        await streambuf_writer.close()
    log.debug('text "%s" conversion done', _shorten(text))


async def play(request_id, streambuf_reader, client_address, on_completed_event):
    """Coroutine to stream data (result of tts converison) from streambuf to client
    """
    log = logger.getChild('play:%d' % request_id)
    try:
        log.debug('connecting...')
        target_reader, target_writer = await asyncio.open_connection(*client_address)
        try:
            log.debug('playing...')
            while True:
                data_chunk = await streambuf_reader.read()
                if data_chunk is None:
                    break
                target_writer.write(data_chunk)
        finally:
            target_writer.close()
    except asyncio.CancelledError:
        log.debug('cancelled')
        await _send_bus_event('event: %s, cancelled' % on_completed_event)
    except Exception as ex:
        log.exception('tts streambuf play error')
        await _send_bus_event('event: %s, error: %s' % (on_completed_event, ex))
    else:
        log.debug('done')
        await _send_bus_event('event: %s, done' % on_completed_event)


class Api:
    def __init__(self, host, tts_api_url, tts_api_limit, max_cache_items):
        self._service_host = host
        self._tts_api_url = tts_api_url
        self._tts_api_limit = tts_api_limit
        self._requests_counter = 0
        self._cache = LRU(max_cache_items)  # key: text hash, value: stream buffer
        self._clients = WeakValueDictionary()  # key: request id, value: future for play
        self._tts_requests = WeakSet()
        self._log = logger.getChild('api')

    async def start_speek(self, text, host, port, on_completed_event):
        """Start streaming text converted to speech to given address.

        Streams are cached by text hash.
        'on_completed_event' is used to notify client about process end

        :param str text: text to convert
        :param str host: client host
        :param int port: client port
        :param on_completed_event:
        :return: request_id
        """
        self._requests_counter += 1
        request_id = self._requests_counter
        self._log.debug('request_id:%d <start_speek("%s", "%s", %d, "%s")>',
                        request_id, _shorten(text), host, port, on_completed_event)
        text_hash = _hash(text)
        buf = self._cache.get(text_hash)

        if buf and buf.corrupted():
            self._log.warn('corrupted streambuf in cache, removed')
            del self._cache[text_hash]
            buf = None

        if not buf:  # text hasn't been translated to speech before
            if len(self._tts_requests) >= self._tts_api_limit:
                self._log.error('TTS requests limit')
                raise ServerError(data='too many requests')
            self._log.debug('request_id:%d new text, requesting TTS service for conversion', request_id)
            buf = StreamBuffer()
            self._cache[text_hash] = buf
            fut = asyncio.ensure_future(run_tts_conversion(self._tts_api_url, text, buf.make_writer()))
            self._tts_requests.add(fut)
        else:
            self._log.debug('request_id:%d playing from cache', request_id)
        self._clients[request_id] = asyncio.ensure_future(
            play(request_id, buf.make_reader(), (host, port), on_completed_event))
        return request_id

    async def stop_speek(self, request_id):
        """ Cancel speech stream play for given request_id

        (tts to cache stream will not be canceled)

        :param str request_id:
        :return: True if speech stream was canceled, False if nothing to cancel
        """
        self._log.debug('request_id:%d, <stop_speek>')
        fut = self._clients.pop(request_id, None)
        if fut is not None:
            fut.cancel()
            return True
        return False

    @staticmethod
    async def jsonrpc_dispatch(request):
        request = await request.text()
        response = await methods.dispatch(request)
        if response.is_notification:
            return aiohttp.web.Response()
        else:
            return aiohttp.web.json_response(response, status=response.http_status)


def run(settings):
    api = Api(settings.host,
              settings.tts_api_url,
              settings.tts_api_limit,
              settings.max_cache_items)
    methods.add(api.start_speek)
    methods.add(api.stop_speek)
    app = aiohttp.web.Application()
    app.router.add_post(settings.api_path, api.jsonrpc_dispatch)
    aiohttp.web.run_app(app, host=settings.host, port=settings.port)
