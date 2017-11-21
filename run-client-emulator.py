#!/usr/bin/env python
# coding: utf8
""" speech_pool demo client.

    The client opens TCP port, connects to speech_pool service and call commands 'start_speek'
    and 'stop_speek'. Received data printed to stdout.
 """
import argparse
import logging
import socket
import threading
import time

import jsonrpcclient

logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s [%(levelname)-5s][%(name)s]: %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')
logging.getLogger('jsonrpcclient.client.request').setLevel(logging.ERROR)
logging.getLogger('jsonrpcclient.client.response').setLevel(logging.ERROR)
log = logging.getLogger('speech_pool_client')
log.setLevel(logging.DEBUG)


def call_stop_cmd(delay, api_url, request_id):
    try:
        time.sleep(delay)
        log.info('calling <stop_speek> command')
        ok = jsonrpcclient.request(api_url, 'stop_speek', request_id)
        if ok:
            log.info('data stream was cancelled')
        else:
            log.info('nothing to cancel')
    except:
        log.exception('error')


def main():
    class HelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=HelpFormatter)
    parser.add_argument('--api-url', required=True, help='speech_pool jsonrpc api url')
    parser.add_argument('-t', '--text', required=True, help='text to convert to audio')
    parser.add_argument('-d', '--start-stop-delay', default=5, type=int,
                        help='delay between start_play and stop_play commands, seconds')
    args = parser.parse_args()

    # simple tcp socket server to handle incoming data

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('127.0.0.1', 0))  # random port
        server_socket.listen(1)
        server_address = server_socket.getsockname()
        log.info('waiting data on %s', server_address)

        log.info('calling <start_speek>')
        request_id = jsonrpcclient.request(args.api_url, 'start_speek', args.text,
                                           server_address[0], server_address[1], 'my notification')
        stop_thread = threading.Thread(target=call_stop_cmd, args=(args.start_stop_delay, args.api_url, request_id))
        stop_thread.daemon = True
        stop_thread.start()

        conn, _ = server_socket.accept()
        log.info('incoming connection')
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                log.info('<DATA>: %s', data)
        log.info('incoming connection end')


if __name__ == '__main__':
    main()
