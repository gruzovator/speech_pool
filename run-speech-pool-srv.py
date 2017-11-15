#!/usr/bin/env python
# coding: utf8
""" Speech Pool Application (Service)

    Сервис предоставляет доступ к внешнему провайдеру ф-ции text-to-speech.
    Ф-ции:
        - проксирование потока данных от провайдера ф-ции text-to-speech
        - ограничение кол-ва одновременных подключений к провайдеру ф-ции text-to-speech
        - кэширование результатов text-to-speech


    Упрошения (TODO):
        - ф-ция text-to-speech эмулируется просто tcp соединением (в реальном сервисе нужен RTP)
        - предполагается, что сервер запускается в единственном экземпляре. В противном случае надо добавить
            внешние счётчик и семафор (e.g. на redis)
        - cache примитивный - в памяти сервиса

    Для отладки можно использовать скрипт run-tts-srv-emulator.py, эмулирующий внешний сервис
"""

import argparse
import logging

import speech_pool.service


class HelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


parser = argparse.ArgumentParser(description=__doc__, formatter_class=HelpFormatter)
parser.add_argument('-H', '--host', default='127.0.0.1', help='service host')
parser.add_argument('-P', '--port', type=int, default=8080, help='service port')
parser.add_argument('--tts-host', required=True, help='text-to-speech service host')
parser.add_argument('--tts-port', type=int, default=80, help='text-to-speech service port')
parser.add_argument('--tts-limit', type=int, default=10, help='text-to-speech service connections limit')
# parser.add_argument('--tts-client-key', required=True, help='text-to-speech service customer key')
parser.add_argument('-v', '--verbose', action='store_true', help='switch on debug logging')
args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                    format='%(asctime)s [%(levelname)-5s][%(name)s]: %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')

speech_pool.service.run(settings=args)
