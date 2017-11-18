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

def send_commands(api_url, text, start_stop_delay):
    log = logging.getLogger('ctrl_thread')
    try:
        log.info('calling <start_play>')
        time.sleep(start_stop_delay)
        log.info('calling <stop_play')
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
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)-5s][%(name)s]: %(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S')

    log = logging.getLogger('recv thread')
    try:
        # simple tcp socket server to handle incoming data
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('127.0.0.1', 0))  # random port
            server_socket.listen(1)
            server_address = server_socket.getsockname()
            log.info('waiting data on %s', server_address)
            ctrl_thread = threading.Thread(target=send_commands, args=(args.api_url, args.text, args.start_stop_delay))
            ctrl_thread.daemon = True
            ctrl_thread.start()
            conn, _ = server_socket.accept()
            log.info('incoming connection')
            with conn:
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    log.info('DATA: %s', data)
            log.info('incoming connection end')
    except:
        log.exception('error')


if __name__ == '__main__':
    main()
