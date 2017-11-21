import asyncio
import hashlib
import logging
from weakref import WeakValueDictionary

import aiohttp
import aiohttp.web
import jsonrpcserver.config
from jsonrpcclient.aiohttp_client import aiohttpClient
from jsonrpcserver.aio import methods

from .proxy import run_proxy
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


def _send_bus_event(event):
    """TODO"""
    log.info('Rabbitmq message: %s', event)


def run_tts_conversion(tts_api_url, text, streambuf_writer):
    pass


def play(streambuf_reader, client_address, on_completed_event):
    pass


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
        fut = play(buf.make_reader(), (host, port), on_completed_event)
        self._clients[request_id] = fut
        asyncio.ensure_future(fut)
        return request_id

    async def stop_speek(self, request_id):
        """ Cancel speech stream play for given request_id

        (tts to cache stream will not be canceled)

        :param str request_id:
        """
        log.debug('on stop_speek')
        fut = self._clients.pop(request_id, None)
        if fut:
            fut.cancel()
        return

    async def _process_request(self, request_id, text, target_address, on_completed_event):
        log.debug('start processing request %d', request_id)
        proxy = None
        try:
            # run proxy on randomly selected port
            proxy = await run_proxy((self._service_host, None), target_address)

            # call TTS service play command
            async with aiohttp.ClientSession() as session:
                client = aiohttpClient(session, self._tts_api_url)
                proxy_host = self._service_host
                proxy_port = proxy.sockets[0].getsockname()[1]
                await client.request('play', text, proxy_host, proxy_port)

        except Exception:
            log.error('error processing request %d', request_id)
        else:
            log.debug('end proceeing request %d', request_id)
        finally:
            if proxy:
                proxy.close()

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
