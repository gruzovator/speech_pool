import logging

import jsonrpcserver.config
from aiohttp import web
from jsonrpcserver.aio import methods

__all__ = ['run']

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
jsonrpcserver.config.log_requests = False
jsonrpcserver.config.log_responses = False


class Api:
    def __init__(self):
        self._requests_counter = 0

    async def start_speek(self, text, host, port, on_completed_event):
        log.debug('on start_speek')
        self._requests_counter += 1
        request_id = self._requests_counter
        return request_id

    async def stop_speek(self, request_id):
        log.debug('on stop_speek')
        return

    @staticmethod
    async def dispatch(request):
        """Convert raw request to API method call"""
        request = await request.text()
        response = await methods.dispatch(request)
        if response.is_notification:
            return web.Response()
        else:
            return web.json_response(response, status=response.http_status)


def run(settings):
    api = Api()
    methods.add(api.start_speek)
    methods.add(api.stop_speek)
    app = web.Application()
    app.router.add_post('/api/v1', api.dispatch)
    web.run_app(app, host=settings.host, port=settings.port)
