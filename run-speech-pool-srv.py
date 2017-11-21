#!/usr/bin/env python
# coding: utf8
""" Speech Pool Application (Service)

Service implements facade to external Text-to-Speech (TTS) service with following features:
    - caching (caching audio data for given text)
    - limit for simultaneous connections to TTS service

This is a demo application. It has next limitations:
    - TTS service is emulated by stub that converts input text to upper case text
    - counters, limiters and cache are implemented inside this application. In real service that features
    should be implemented externally (e.g. redis)
"""

import argparse
import logging

import speech_pool.service


class HelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


parser = argparse.ArgumentParser(description=__doc__, formatter_class=HelpFormatter)
parser.add_argument('-H', '--host', default='127.0.0.1', help='service host')
parser.add_argument('-P', '--port', type=int, default=8080, help='service port')
parser.add_argument('-A', '--api-path', default='/api/v1', help='service API path')
parser.add_argument('--tts-api-url', required=True, help='text-to-speech service url')
parser.add_argument('--tts-api-limit', type=int, default=10, help='text-to-speech service connections limit')
# parser.add_argument('--tts-client-key', required=True, help='text-to-speech service customer key')
parser.add_argument('-v', '--verbose', action='store_true', help='switch on debug logging')
args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                    format='%(asctime)s [%(levelname)-5s][%(name)s]: %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')

speech_pool.service.run(settings=args)
