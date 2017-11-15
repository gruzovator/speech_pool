#!/usr/bin/env python
# coding: utf8
"""Text to Speech Service Emulator.

Сервис управляется по jsonrpc. По команде
    play(text, target_host, target_port)
открывает TCP соединение к (target_host, target_port) и посылает text преобразованный в верхний регистр

Пример использования:

    Запускаем nc -l 1234 -k в кач-ве тестового потребителя

    Затем из python

        import jsonrpcclient
        jsonrpcclient.request('http://localhost:8080', 'play', 'welcome!', 'localhost', 1234)
"""
import argparse
import asyncio
import asyncio.futures
import logging

import jsonrpcserver.config
from aiohttp import web
from jsonrpcserver.aio import methods
from jsonrpcserver.exceptions import ServerError

jsonrpcserver.config.log_requests = False
jsonrpcserver.config.log_responses = False


async def _play(text, writer):
    """ Playing coroutine """
    target = writer.transport.get_extra_info('peername')
    log = logging.getLogger('player')
    log.debug('start playing, target: %s', target)
    try:
        text = text.upper()
        for c in text:
            await asyncio.sleep(1)
            writer.write(c.encode('utf8'))
            await writer.drain()
    except Exception:
        log.exception('error playing, target: %s', target)
    else:
        log.debug('stop playing, target: %s', target)
    finally:
        writer.close()


class Api:
    async def play(self, text, target_host, target_port):
        try:
            _, writer = await asyncio.open_connection(target_host, target_port)
        except ConnectionError:
            err = ServerError()
            err.message = "can't connect to target"
            raise err
        asyncio.ensure_future(_play(text, writer))
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


def main():
    class HelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter): pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=HelpFormatter)
    parser.add_argument('-H', '--host', default='127.0.0.1', help='server host')
    parser.add_argument('-P', '--port', type=int, default=8080, help='server port')
    parser.add_argument('-v', '--verbose', action='store_true', help='switch on debug logging')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s [%(levelname)-5s][%(name)s]: %(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S')
    api = Api()
    methods.add(api.play)
    app = web.Application()
    app.router.add_post('/', api.dispatch)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
